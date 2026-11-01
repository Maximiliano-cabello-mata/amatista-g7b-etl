#!/bin/sh
# Sonda de rendimiento de G7B en Linux o macOS.
# Uso: ./medir.sh            (sin ventana: edición, animación y render)
#      ./medir.sh ventana    (abre Blender para medir también la vista 3D)
# Si blender no está en el PATH: BLENDER=/ruta/a/blender ./medir.sh
set -e
BLENDER="${BLENDER:-blender}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = "ventana" ]; then
  "$BLENDER" --factory-startup --python "$AQUI/g7b_sonda.py" -- --salida "$AQUI/../resultados" --salir
else
  "$BLENDER" -b --factory-startup --python "$AQUI/g7b_sonda.py" -- --salida "$AQUI/../resultados"
fi
