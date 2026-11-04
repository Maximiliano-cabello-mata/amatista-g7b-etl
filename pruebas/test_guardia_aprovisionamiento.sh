#!/usr/bin/env bash
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_PRUEBA=$(mktemp -d)
trap 'rm -rf -- "$TEMP_PRUEBA"' EXIT
export REGISTRO_GUARDIA="$TEMP_PRUEBA/llamadas"
az() {
  echo "$*" >> "$REGISTRO_GUARDIA"
  case "$*" in
    'resource list '*)
      if [[ "${SIMULAR_ERROR:-no}" == si ]]; then return 17; fi
      echo g7b-env-laboratorio-jobs-v3;;
    *) echo 'No debe llegar a despliegues ni what-if'; return 99;;
  esac
}
export -f az
for caso in existe error; do
  : > "$REGISTRO_GUARDIA"
  export SIMULAR_ERROR=no
  [[ "$caso" != error ]] || export SIMULAR_ERROR=si
  if STORAGE_ACCOUNT_NAME=prueba G7B_APROVISIONAR=si G7B_ROTACION_CONFIRMADA=si G7B_PRESUPUESTO_REVISADO=si \
    bash "$RAIZ/infra/azure/validar_y_aprovisionar.sh" > "$TEMP_PRUEBA/salida" 2>&1; then
    echo 'No bloqueo entorno existente o error de consulta'; exit 1
  fi
  if grep -q 'deployment group' "$REGISTRO_GUARDIA"; then exit 1; fi
done
echo '2 pruebas: entorno existente y consulta fallida bloquean aprovisionamiento.'
