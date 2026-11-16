#!/usr/bin/env bash
# Aviso del ciclo: abre o actualiza un issue «g7b-alerta» si algo falló o hay fuentes atrasadas;
# lo cierra cuando una vuelta sale bien. Termina en error si hubo problemas, para que la vuelta
# también se vea en rojo en la pestaña Actions.
#
# Variables: GH_TOKEN, GH_REPO, FALLAS, ATRASADAS, VUELTA (enlace a esta ejecución).
set -uo pipefail

ETIQUETA="g7b-alerta"
TITULO="G7B: el flujo de datos necesita atención"
cuando="$(date -u '+%Y-%m-%d %H:%M UTC')"

gh label create "$ETIQUETA" --color B60205 \
  --description "El ciclo de G7B falló o sus datos están viejos" --force > /dev/null 2>&1 || true
abierto="$(gh issue list --label "$ETIQUETA" --state open --limit 1 --json number --jq '.[0].number // empty' 2>/dev/null || true)"

if [ -n "${FALLAS:-}" ] || [ -n "${ATRASADAS:-}" ]; then
  cuerpo="**Vuelta del $cuando:** $VUELTA

- **Tareas que fallaron:** ${FALLAS:-ninguna}
- **Fuentes con error o atrasadas:** ${ATRASADAS:-ninguna}

Qué revisar: el enlace de cada tarea en el resumen de la vuelta. Si fallan todas las que tocan Azure, lo
primero es la firma \`AZURE_LAGO_URL\` (docs/OPERACION_24_7.md). Este aviso se cierra solo cuando una
vuelta sale bien."
  if [ -n "$abierto" ]; then
    gh issue comment "$abierto" --body "$cuerpo" || echo "::warning::no se pudo comentar el aviso #$abierto"
  else
    gh issue create --title "$TITULO" --label "$ETIQUETA" --body "$cuerpo" || echo "::warning::no se pudo abrir el aviso"
  fi
  echo "::error::Problemas en la vuelta. Tareas: ${FALLAS:-ninguna}. Fuentes: ${ATRASADAS:-ninguna}."
  exit 1
fi

if [ -n "$abierto" ]; then
  gh issue close "$abierto" --comment "La vuelta del $cuando salió bien: $VUELTA" || true
fi
echo "Vuelta sin problemas."
