#!/usr/bin/env bash
# Relevo del ciclo G7B: espera a la siguiente hora del ciclo y lo lanza.
#
# Por qué existe: GitHub atrasa o se salta los horarios (schedule) de este repositorio. El 16 de
# noviembre de 2026 el ciclo solo corrió en una de sus cuatro horas, y otro flujo corrió casi 10
# horas tarde. Lanzar con workflow_dispatch sí es inmediato. Así que la cadena es:
#
#   ciclo (al terminar) ──lanza──▶ relevo (espera hasta la hora) ──lanza──▶ ciclo ...
#
# El relevo tiene su propio horario de respaldo: si la cadena se corta, el siguiente relevo que llegue
# la retoma, y si el ciclo lleva mucho sin correr, lo lanza enseguida.
#
# Variables: GH_TOKEN, GH_REPO (gh), REF (por omisión main).
# Para las pruebas: AHORA (época en segundos), DORMIR (comando para esperar, por omisión sleep).
set -uo pipefail

REF="${REF:-main}"
HORAS=(0 6 12 18)       # horas UTC del ciclo, minuto 11 (las mismas que su schedule)
MINUTO=11
MAX_ESPERA=$((354 * 60)) # el trabajo tiene 360 minutos de tope (el máximo de GitHub)
ATRASO=$((6 * 3600 + 15 * 60))  # sin ciclo en más de 6 h 15 min: se lanza ya
ALERTA=$((8 * 3600))             # sin una vuelta buena en 8 h: aviso
DORMIR="${DORMIR:-sleep}"
RESUMEN="${GITHUB_STEP_SUMMARY:-/dev/stdout}"

ahora() { echo "${AHORA:-$(date -u +%s)}"; }
epoca() { date -u -d "$1" +%s; }

siguiente_hora() {  # época de la próxima hora del ciclo, al menos 2 minutos en el futuro
  local t="$1" dia h cand
  dia="$(date -u -d "@$t" +%Y-%m-%d)"
  for desfase in 0 1; do
    for h in "${HORAS[@]}"; do
      cand="$(epoca "$dia $h:$MINUTO:00 UTC + $desfase day")"
      if [ "$cand" -gt $((t + 120)) ]; then echo "$cand"; return; fi
    done
  done
}

# Últimas vueltas del ciclo: «estado conclusión creado» por línea, la más nueva primero.
vueltas() {
  gh run list --workflow ciclo.yml --limit 20 --json status,conclusion,createdAt \
    --jq '.[] | "\(.status) \(.conclusion // "-") \(.createdAt)"' 2>/dev/null
}

en_curso() { vueltas | awk '$1!="completed"{found=1} END{exit !found}'; }

edad_ultima() {  # segundos desde la última vuelta (cualquiera); muy grande si no hay
  local c; c="$(vueltas | head -1 | awk '{print $3}')"
  if [ -z "$c" ]; then echo 999999999; else echo $(( $(ahora) - $(epoca "$c") )); fi
}

edad_buena() {  # segundos desde la última vuelta que salió bien
  local c; c="$(vueltas | awk '$2=="success"{print $3; exit}')"
  if [ -z "$c" ]; then echo 999999999; else echo $(( $(ahora) - $(epoca "$c") )); fi
}

lanzar_ciclo() {
  if gh workflow run ciclo.yml --ref "$REF"; then
    echo "- $(date -u -d "@$(ahora)" '+%H:%M UTC'): lancé el ciclo ($1)." >> "$RESUMEN"
  else
    echo "::error::no se pudo lanzar el ciclo"
    exit 1
  fi
}

avisar_atraso() {
  local horas=$(( $1 / 3600 )) etiqueta="g7b-alerta" abierto cuerpo
  gh label create "$etiqueta" --color B60205 \
    --description "El ciclo de G7B falló o sus datos están viejos" --force > /dev/null 2>&1 || true
  abierto="$(gh issue list --label "$etiqueta" --state open --limit 1 --json number \
    --jq '.[0].number // empty' 2>/dev/null || true)"
  cuerpo="**El ciclo no ha tenido una vuelta buena en ${horas} horas** (revisado por el relevo, $(date -u -d "@$(ahora)" '+%Y-%m-%d %H:%M UTC')).

El relevo lo lanza igual; si este aviso sigue abierto, mira la última vuelta del ciclo en Actions. Se
cierra solo cuando una vuelta sale bien (docs/OPERACION_24_7.md)."
  if [ "$horas" -gt 9000 ]; then
    cuerpo="${cuerpo/en ${horas} horas/nunca}"
  fi
  if [ -n "$abierto" ]; then
    gh issue comment "$abierto" --body "$cuerpo" > /dev/null || true
  else
    gh issue create --title "G7B: el flujo de datos necesita atención" --label "$etiqueta" --body "$cuerpo" > /dev/null || true
  fi
  echo "::warning::el ciclo no tiene una vuelta buena en ${horas} h"
}

# 1. ¿El ciclo dejó de correr bien? Se avisa (una vuelta buena lo cierra desde el ciclo).
buena="$(edad_buena)"
if [ "$buena" -ge "$ALERTA" ] && ! en_curso; then
  avisar_atraso "$buena"
fi

# 2. ¿Se saltó una hora? Se pone al día ahora mismo.
if ! en_curso && [ "$(edad_ultima)" -ge "$ATRASO" ]; then
  lanzar_ciclo "ponerse al día: la última vuelta tiene más de 6 horas"
  exit 0
fi

# 3. Esperar a la siguiente hora y lanzarlo, salvo que ya haya corrido o esté corriendo.
destino="$(siguiente_hora "$(ahora)")"
espera=$(( destino - $(ahora) ))
[ "$espera" -gt "$MAX_ESPERA" ] && espera="$MAX_ESPERA"
echo "Siguiente vuelta: $(date -u -d "@$destino" '+%Y-%m-%d %H:%M UTC'); espero $((espera / 60)) min." >> "$RESUMEN"
$DORMIR "$espera"
if [ -n "${AHORA:-}" ]; then AHORA=$((AHORA + espera)); fi

if en_curso; then
  echo "- El ciclo ya está corriendo: no lanzo otro." >> "$RESUMEN"
elif [ "$(edad_ultima)" -lt $((30 * 60)) ]; then
  echo "- El ciclo ya corrió hace menos de 30 minutos: no lanzo otro." >> "$RESUMEN"
else
  lanzar_ciclo "hora programada"
fi
