#!/usr/bin/env bash
# Una vuelta del flujo de G7B: lanza cada tarea con workflow_dispatch y espera su resultado.
#
# No se detiene en la primera falla: con lo que haya, lo siguiente puede servir igual (publicar lo
# que el embudo ya aceptó). Solo se salta lo que depende de algo que falló (el cubo sin telemetría,
# el kernel sin cubo). Deja una tabla en el resumen de la ejecución y las fallas en «fallas».
#
# Variables: GH_TOKEN y GH_REPO (gh), COMPLETO=true para la parte semanal, REF (por omisión main).
set -uo pipefail

REF="${REF:-main}"
RESUMEN="${GITHUB_STEP_SUMMARY:-/dev/stdout}"
fallas=()

echo "| Tarea | Resultado | Ejecución |" >> "$RESUMEN"
echo "|---|---|---|" >> "$RESUMEN"

lanzar() {
  local wf="$1"; shift
  local antes id=""
  antes="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if ! gh workflow run "$wf" --ref "$REF" "$@"; then
    echo "| $wf | ❌ no se pudo lanzar | |" >> "$RESUMEN"
    fallas+=("$wf (no se pudo lanzar)")
    return 1
  fi
  # La ejecución tarda unos segundos en aparecer en la lista.
  for _ in $(seq 1 36); do
    sleep 5
    id="$(gh run list --workflow "$wf" --event workflow_dispatch --limit 10 --json databaseId,createdAt \
          --jq "[.[] | select(.createdAt >= \"$antes\")] | sort_by(.createdAt) | .[0].databaseId // empty")"
    [ -n "$id" ] && break
  done
  if [ -z "$id" ]; then
    echo "| $wf | ❌ no apareció la ejecución | |" >> "$RESUMEN"
    fallas+=("$wf (no apareció la ejecución)")
    return 1
  fi
  local enlace="https://github.com/$GH_REPO/actions/runs/$id"
  echo "$wf → $enlace"
  if gh run watch "$id" --exit-status --interval 30 > /dev/null; then
    echo "| $wf | ✅ | [ver]($enlace) |" >> "$RESUMEN"
    return 0
  fi
  echo "| $wf | ❌ | [ver]($enlace) |" >> "$RESUMEN"
  fallas+=("$wf ($enlace)")
  return 1
}

saltar() {
  echo "| $1 | ⏭️ $2 | |" >> "$RESUMEN"
}

# 1. Extracción
lanzar vigilar.yml -f simulacro=false
lanzar zyte_a_lago.yml -f simulacro=false

# 2. Análisis: lo nuevo y lo que se evaluó con reglas distintas.
lanzar procesar.yml -f simulacro=false

# 3. Semanal: telemetría, cubo y kernel de Geoda.
semanal=false
if [ "${COMPLETO:-false}" = "true" ]; then
  semanal=true
elif [ "$(date -u +%u)" = "2" ] && [ "$(date -u +%H)" -lt 6 ]; then
  semanal=true  # martes, primera vuelta del día (UTC)
fi
if [ "$semanal" = "true" ]; then
  if lanzar telemetria.yml -f publicar_azure=true; then
    if lanzar cubo.yml; then
      lanzar geoda_kernel.yml
    else
      saltar geoda_kernel.yml "sin cubo nuevo"
    fi
  else
    saltar cubo.yml "sin telemetría"
    saltar geoda_kernel.yml "sin telemetría"
  fi
else
  saltar "telemetria.yml, cubo.yml, geoda_kernel.yml" "no es la vuelta semanal"
fi

# 4. Entrega a Geoda y a la API de Amatista.
lanzar geoda_publicar.yml

if [ ${#fallas[@]} -gt 0 ]; then
  lista="$(printf '%s; ' "${fallas[@]}")"
  echo "fallas=${lista%; }" >> "${GITHUB_OUTPUT:-/dev/null}"
  echo "Fallaron: ${lista%; }"
else
  echo "fallas=" >> "${GITHUB_OUTPUT:-/dev/null}"
fi
exit 0  # el aviso decide; así siempre se revisa la frescura
