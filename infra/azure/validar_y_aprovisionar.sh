#!/usr/bin/env bash
# PREVISUALIZACION SEGURA EN AZURE CLOUD SHELL.
# No crea ni modifica recursos a menos que G7B_APROVISIONAR=si.
# Requiere rotar primero la clave utilizada para firmar la SAS expuesta.
set -euo pipefail

: "${STORAGE_ACCOUNT_NAME:?Escribe solo el NOMBRE de tu cuenta de almacenamiento (sin URL ni SAS)}"
GRUPO="${G7B_GRUPO:-g7b}"
FASE="${G7B_FASE:-laboratorio}"
ARCHIVO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/g7b-control-privado.bicep"

if [[ "${G7B_ROTACION_CONFIRMADA:-no}" != "si" ]]; then
  echo "BLOQUEADO: primero revoca la SAS expuesta y registra la nueva credencial fuera del repositorio." >&2
  exit 2
fi
if [[ "$FASE" != "laboratorio" && "$FASE" != "validacion" ]]; then
  echo "Fase no permitida. Nunca despliegues directamente a produccion." >&2
  exit 2
fi

echo "== Azure: suscripcion activa (sin imprimir identificadores ni credenciales)"
az account show --query name -o tsv
echo "== Verificar cuenta de almacenamiento existente"
az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$GRUPO" \
  --query "{nombre:name,region:primaryLocation}" --output table
echo "== Validar sintaxis Bicep"
az bicep build --file "$ARCHIVO" --stdout >/dev/null

echo "== Plan de cambios en Azure, SIN crear recursos"
az deployment group what-if --resource-group "$GRUPO" --template-file "$ARCHIVO" \
  --parameters storageAccountName="$STORAGE_ACCOUNT_NAME" stage="$FASE" provisionCompute=true

if [[ "${G7B_APROVISIONAR:-no}" != "si" ]]; then
  echo "NO SE HA DESPLEGADO. Revisa el plan y los costos; habilita G7B_APROVISIONAR=si cuando corresponda."
  exit 0
fi

if [[ "${G7B_PRESUPUESTO_REVISADO:-no}" != "si" ]]; then
  echo "BLOQUEADO: confirma presupuesto, cuotas y permisos RBAC antes de aprovisionar." >&2
  exit 2
fi

echo "== Creando SOLO entorno manual de laboratorio y permiso de lectura"
az deployment group create --resource-group "$GRUPO" --template-file "$ARCHIVO" \
  --parameters storageAccountName="$STORAGE_ACCOUNT_NAME" stage="$FASE" provisionCompute=true \
  --query "{estado:properties.provisioningState}" --output json

echo "Infraestructura creada; el job NO se ejecuta automaticamente."
echo "El job inicial es smoke de Microsoft: para operar con datos, publica primero la imagen G7B en un ACR privado."
