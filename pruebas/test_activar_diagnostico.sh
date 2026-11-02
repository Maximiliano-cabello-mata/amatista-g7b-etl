#!/usr/bin/env bash
# Simula Azure: ninguna llamada externa ni credencial.
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$RAIZ/infra/azure/activar_diagnostico.sh"
TEMP_PRUEBA=$(mktemp -d)
trap 'rm -rf -- "$TEMP_PRUEBA"' EXIT
export REGISTRO="$TEMP_PRUEBA/llamadas"
az() {
  printf '%s\n' "$*" >> "$REGISTRO"
  case "$*" in
    'account show --query id -o tsv') echo suscripcion-prueba;;
    'containerapp env show '*'--query properties.environmentMode'*) :;; # Reproduce CLI que omite el campo.
    'rest --method get --url https://management.azure.com/entorno/v3?api-version=2026-07-01 --query properties.environmentMode -o tsv') printf '%s\n' "${MODO_ENV_SIMULADO-WorkloadProfiles}";;
    *'--query properties.environmentId'*) echo "${ENTORNO_SIMULADO:-/entorno/v3}";;
    'containerapp env show '*'--query id'*) echo /entorno/v3;;
    *'--query properties.configuration.triggerType'*) echo Manual;;
    *'--query identity.principalId'*) echo identidad-prueba;;
    *'--query properties.template.containers[0].name'*) echo smoke;;
    *'--query length(properties.template.containers)'*) echo 1;;
    *'--query properties.template.containers[0].image'*) echo "${IMAGEN_SIMULADA:-mcr.microsoft.com/k8se/quickstart-jobs:latest}";;
    'acr show '*'--query id'*) echo /acr/prueba;;
    'acr show '*'--query loginServer'*) echo prueba.azurecr.io;;
    'acr show '*'--query roleAssignmentMode'*) echo LegacyRegistryPermissions;;
    'acr config authentication-as-arm show '*) echo enabled;;
    'acr repository show '*) printf 'sha256:%064d\n' 0;;
    'acr build '*)
      [[ -f Dockerfile && -f g7b_ops/auditoria.py && ! -e .git && ! -e .env ]] || { echo 'Contexto o Dockerfile incorrecto' >&2; return 98; }
      [[ "$*" == *'--file Dockerfile . --no-logs -o none'* ]] || return 98
      [[ "${BUILD_FALLA:-no}" != si ]] || { echo 'Build simulado fallido' >&2; return 97; }
      ;;
    'role assignment create '*|'containerapp job registry set '*|'containerapp job update '*) :;;
    'containerapp job start '*) echo ejecucion-prueba;;
    'containerapp job execution show '*) echo "${ESTADO_SIMULADO:-Succeeded}";;
    'account show '*|'storage account show '*|'acr list '*) :;;
    *) echo "Llamada inesperada: $*" >&2; return 99;;
  esac
}
export -f az
bash "$SCRIPT" --revisar > "$TEMP_PRUEBA/salida"
grep -q 'REVISION COMPLETA' "$TEMP_PRUEBA/salida"
if grep -Eq ' build | update | start | create | set ' "$REGISTRO"; then
  echo 'La revision intento modificar Azure'; exit 1
fi
for modo_invalido in '' Express; do
  if MODO_ENV_SIMULADO="$modo_invalido" bash "$SCRIPT" --revisar > "$TEMP_PRUEBA/salida" 2>&1; then
    echo 'Acepto modo ausente o Express'; exit 1
  fi
  if [[ -z "$modo_invalido" ]]; then
    grep -q 'no devolvio environmentMode' "$TEMP_PRUEBA/salida"
  else
    grep -q 'Modo del entorno no compatible: Express' "$TEMP_PRUEBA/salida"
  fi
done
if ENTORNO_SIMULADO=/otro bash "$SCRIPT" --revisar > "$TEMP_PRUEBA/salida" 2>&1; then
  echo 'No rechazo entorno incorrecto'; exit 1
fi
grep -q 'no apunta al entorno v3' "$TEMP_PRUEBA/salida"
if G7B_ACR=prueba G7B_SUSCRIPCION=otra bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida" 2>&1; then
  echo 'No rechazo suscripcion incorrecta'; exit 1
fi
grep -q 'suscripcion activa no coincide' "$TEMP_PRUEBA/salida"
if G7B_ACR=prueba G7B_SUSCRIPCION=suscripcion-prueba G7B_PRESUPUESTO_REVISADO=no bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida" 2>&1; then
  echo 'No rechazo presupuesto no revisado'; exit 1
fi
grep -q 'Revisar presupuesto' "$TEMP_PRUEBA/salida"
# Simular checkout limpio para probar la secuencia sin depender de Git remoto.
git() {
  case "$*" in *'status --porcelain'*) :;; *'rev-parse HEAD'*) printf '%040d\n' 1;; *) return 99;; esac
}
export -f git
export G7B_ACR=prueba G7B_SUSCRIPCION=suscripcion-prueba G7B_PRESUPUESTO_REVISADO=si G7B_ROTACION_CONFIRMADA=si
: > "$REGISTRO"
if BUILD_FALLA=si bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida" 2>&1; then
  echo 'Ignoro fallo de build'; exit 1
fi
grep -q 'Build simulado fallido' "$TEMP_PRUEBA/salida"
if grep -Eq 'role assignment create|containerapp job (registry set|update|start)' "$REGISTRO"; then
  echo 'Modifico permisos o Job despues de fallo de build'; exit 1
fi
: > "$REGISTRO"
bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida"
grep -q 'CONFIGURADO: prueba.azurecr.io/g7b/auditoria@sha256:' "$TEMP_PRUEBA/salida"
grep -q 'role assignment create .*--role AcrPull --scope /acr/prueba' "$REGISTRO"
if grep -q 'containerapp job start' "$REGISTRO"; then echo 'Aplicar inicio un Job'; exit 1; fi
if bash "$SCRIPT" --ejecutar > "$TEMP_PRUEBA/salida" 2>&1; then echo 'Acepto imagen smoke'; exit 1; fi
grep -q 'Primero aplicar' "$TEMP_PRUEBA/salida"
export IMAGEN_SIMULADA="prueba.azurecr.io/g7b/auditoria@sha256:$(printf '%064d' 0)"
bash "$SCRIPT" --ejecutar > "$TEMP_PRUEBA/salida"
grep -q 'Succeeded: recuperar' "$TEMP_PRUEBA/salida"
if ESTADO_SIMULADO=Failed bash "$SCRIPT" --ejecutar > "$TEMP_PRUEBA/salida" 2>&1; then echo 'Acepto ejecucion fallida'; exit 1; fi
grep -q 'termino: Failed' "$TEMP_PRUEBA/salida"
unset IMAGEN_SIMULADA
: > "$REGISTRO"
G7B_IMAGEN_EXISTENTE="g7b/auditoria:$(printf '%040d' 2)" bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida"
grep -q CONFIGURADO "$TEMP_PRUEBA/salida"
if grep -q 'acr build' "$REGISTRO"; then echo 'Reconstruyo una imagen existente'; exit 1; fi
if G7B_IMAGEN_EXISTENTE='otro:latest' bash "$SCRIPT" --aplicar > "$TEMP_PRUEBA/salida" 2>&1; then
  echo 'Acepto etiqueta no aprobada'; exit 1
fi
echo '13 pruebas correctas (incluyen contexto Dockerfile, fallo de build y API explicita): revision, entorno, suscripcion, presupuesto, aplicar, imagen, exito y fallo.'
