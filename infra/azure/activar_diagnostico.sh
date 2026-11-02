#!/usr/bin/env bash
# Cloud Shell: inspeccionar por defecto; --aplicar publica y configura, --ejecutar inicia.
set -euo pipefail
MODO="${1:---revisar}"
case "$MODO" in --revisar|--aplicar|--ejecutar) ;; *) echo 'Uso: bash infra/azure/activar_diagnostico.sh [--revisar|--aplicar|--ejecutar]' >&2; exit 2;; esac
GRUPO=g7b
JOB=g7b-smoke-laboratorio
ENTORNO=g7b-env-laboratorio-jobs-v3
STORAGE=g7blago09b52a0e
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fallar() { echo "$*" >&2; exit 2; }
command -v az >/dev/null || fallar 'Ejecutar en Azure Cloud Shell (Bash), con sesion iniciada.'
az account show --query '{suscripcion:name,estado:state}' -o table
az storage account show -g "$GRUPO" -n "$STORAGE" --query '{nombre:name,region:primaryLocation}' -o table
ENV_ID=$(az containerapp env show -g "$GRUPO" -n "$ENTORNO" --query id -o tsv)
[[ -n "$ENV_ID" && "$ENV_ID" != None ]] || fallar 'No se pudo obtener el ID del entorno.'
# La API usada internamente por az containerapp env show puede omitir environmentMode.
# Consultar la misma version que la plantilla v3; un campo ausente no prueba modo Express.
MODO_ENV=$(az rest --method get --url "https://management.azure.com${ENV_ID}?api-version=2026-07-01" --query properties.environmentMode -o tsv)
[[ -n "$MODO_ENV" && "$MODO_ENV" != None && "$MODO_ENV" != null ]] || fallar 'La API 2026-07-01 no devolvio environmentMode; no se puede validar el modo.'
[[ "$MODO_ENV" == WorkloadProfiles ]] || fallar "Modo del entorno no compatible: $MODO_ENV; se requiere WorkloadProfiles."
JOB_ENV=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query properties.environmentId -o tsv)
[[ "${ENV_ID,,}" == "${JOB_ENV,,}" ]] || fallar 'El Job no apunta al entorno v3 esperado.'
TRIGGER=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query properties.configuration.triggerType -o tsv)
[[ "$TRIGGER" == Manual ]] || fallar 'Se requiere un Job Manual.'
PRINCIPAL=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query identity.principalId -o tsv)
[[ -n "$PRINCIPAL" && "$PRINCIPAL" != None ]] || fallar 'Falta identidad de sistema en el Job.'
CONTENEDOR=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query 'properties.template.containers[0].name' -o tsv)
NUM=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query 'length(properties.template.containers)' -o tsv)
[[ "$NUM" == 1 && "$CONTENEDOR" == smoke ]] || fallar 'La plantilla del Job cambio; revisar antes de actualizar.'
IMAGEN_ANTERIOR=$(az containerapp job show -g "$GRUPO" -n "$JOB" --query 'properties.template.containers[0].image' -o tsv)
echo "Job: $JOB; imagen actual: $IMAGEN_ANTERIOR"
az acr list --query '[].{nombre:name,grupo:resourceGroup,sku:sku.name}' -o table
if [[ "$MODO" == --revisar ]]; then
  echo 'REVISION COMPLETA: no se modificaron recursos. Si no hay ACR, seguir docs/WORKER_AZURE.md.'
  exit 0
fi
: "${G7B_ACR:?Indica el nombre de un ACR existente y aprobado}"
: "${G7B_SUSCRIPCION:?Indica el ID de la suscripcion verificada}"
ACTUAL=$(az account show --query id -o tsv)
[[ "$ACTUAL" == "$G7B_SUSCRIPCION" ]] || fallar 'La suscripcion activa no coincide con la prevista.'
[[ "${G7B_PRESUPUESTO_REVISADO:-no}" == si ]] || fallar 'Revisar presupuesto y costos antes de aplicar o ejecutar.'
[[ "${G7B_ROTACION_CONFIRMADA:-no}" == si ]] || fallar 'Registrar evidencia de remediacion SAS; no repetir rotacion sin comprobarla.'
ACR_ID=$(az acr show -n "$G7B_ACR" --query id -o tsv)
SERVIDOR=$(az acr show -n "$G7B_ACR" --query loginServer -o tsv)
PERMISOS=$(az acr show -n "$G7B_ACR" --query roleAssignmentMode -o tsv)
[[ "$PERMISOS" == LegacyRegistryPermissions ]] || fallar 'Este procedimiento requiere ACR RBAC clasico; no cambia permisos ABAC automaticamente.'
ARM=$(az acr config authentication-as-arm show -r "$G7B_ACR" --query status -o tsv)
[[ "$ARM" == enabled ]] || fallar 'ACR no admite tokens ARM; revisar su politica antes de continuar.'
if [[ "$MODO" == --aplicar ]]; then
  [[ -z "$(git -C "$RAIZ" status --porcelain --untracked-files=normal)" ]] || fallar 'Usa un checkout limpio; conserva copias .bak fuera del repositorio.'
  REV=$(git -C "$RAIZ" rev-parse HEAD)
  TAG="g7b/auditoria:$REV"
  # Contexto minimo: nunca enviar .git, .env, backups ni archivos del lago a ACR.
  CONTEXTO=$(mktemp -d)
  trap 'rm -rf -- "$CONTEXTO"' EXIT
  mkdir -p "$CONTEXTO/g7b_ops"
  cp "$RAIZ"/g7b_ops/*.py "$CONTEXTO/g7b_ops/"
  cp "$RAIZ/infra/azure/worker/Dockerfile" "$CONTEXTO/Dockerfile"
  az acr build -r "$G7B_ACR" --image "$TAG" --file Dockerfile "$CONTEXTO" --no-logs -o none
  DIGEST=$(az acr repository show -n "$G7B_ACR" --image "$TAG" --query digest -o tsv)
  [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]] || fallar 'No se pudo resolver el digest de la imagen.'
  IMAGEN="$SERVIDOR/g7b/auditoria@$DIGEST"
  az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal --role AcrPull --scope "$ACR_ID" -o none
  az containerapp job registry set -g "$GRUPO" -n "$JOB" --server "$SERVIDOR" --identity system -o none
  az containerapp job update -g "$GRUPO" -n "$JOB" --container-name smoke --image "$IMAGEN" \
    --command '' --args '' \
    --replace-env-vars "AZURE_STORAGE_ACCOUNT_URL=https://$STORAGE.blob.core.windows.net" 'AZURE_CONTAINER_NAME=lago' -o none
  echo "CONFIGURADO: $IMAGEN"
  echo "Imagen anterior para restauracion: $IMAGEN_ANTERIOR"
  echo 'No se inicio ninguna ejecucion. Continuar con --ejecutar cuando RBAC se haya propagado.'
  exit 0
fi
[[ "$IMAGEN_ANTERIOR" == "$SERVIDOR/g7b/auditoria@sha256:"* ]] || fallar 'Primero aplicar la imagen del worker fijada por digest.'
EJECUCION=$(az containerapp job start -g "$GRUPO" -n "$JOB" --query name -o tsv)
[[ -n "$EJECUCION" ]] || fallar 'Azure no devolvio el nombre de ejecucion.'
echo "Ejecucion iniciada: $EJECUCION"
for ((intento=0; intento<72; intento++)); do
  ESTADO=$(az containerapp job execution show -g "$GRUPO" -n "$JOB" --job-execution-name "$EJECUCION" --query properties.status -o tsv)
  case "$ESTADO" in
    Succeeded) echo 'Succeeded: recuperar G7B_AZURE_DIAGNOSTICO de esta ejecucion para acreditar lectura del lago.'; exit 0;;
    Failed|Stopped|Degraded) echo "La ejecucion termino: $ESTADO. Revisar logs; no se reintenta automaticamente." >&2; exit 1;;
  esac
  sleep 10
done
echo 'Tiempo de observacion agotado: la ejecucion puede seguir activa. Consultar antes de iniciar otra.' >&2
exit 1
