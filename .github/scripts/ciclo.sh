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
  local id
  # La respuesta pertenece a este despacho, incluso si hay dos operadores.
  id="$(gh api -X POST -H 'X-GitHub-Api-Version: 2026-03-10' \
    "repos/$GH_REPO/actions/workflows/$wf/dispatches" -f ref="$REF" "$@" --jq '.workflow_run_id')" || id=""
  if ! [[ "$id" =~ ^[0-9]+$ ]]; then
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
lanzar vigilar.yml -F 'inputs[simulacro]=false'
lanzar zyte_a_lago.yml -F 'inputs[simulacro]=false'

# 2. Análisis: lo nuevo y lo que se evaluó con reglas distintas.
lanzar procesar.yml -F 'inputs[simulacro]=false'

# 3. Cada período empieza el martes a medianoche UTC. Una vuelta tardía recupera el pendiente.
hoy=$(date -u +%F)
dia=$(date -u -d "$hoy" +%u)
semana=$(date -u -d "$hoy -$(((dia + 5) % 7)) days" +%F)
titulo="Cubo semanal G7B $semana"
if ! completadas=$(gh run list --repo "$GH_REPO" --branch "$REF" --workflow cubo.yml \
    --event workflow_dispatch --status success --created ">=$semana" --limit 1000 --json displayTitle \
    --jq '.[].displayTitle'); then
  fallas+=("no se pudo consultar el cierre semanal")
elif [ "${COMPLETO:-false}" = true ] || ! grep -Fxq "$titulo" <<<"$completadas"; then
  if lanzar telemetria.yml -F 'inputs[publicar_azure]=true'; then
    lanzar cubo.yml -f "inputs[semana]=$semana"
  else
    saltar cubo.yml "sin telemetría; se reintenta la siguiente vuelta"
  fi
else
  saltar "telemetria.yml y cubo.yml (con Geoda)" "semana $semana ya completada"
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
