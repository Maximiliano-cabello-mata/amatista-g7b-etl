"""Lee la salida de «geodar salud» (una línea JSON por fuente) e imprime las que tienen error o están atrasadas."""
import json
import sys

malas = []
for linea in sys.stdin:
    linea = linea.strip()
    if linea.startswith("{"):
        fila = json.loads(linea)
        if fila.get("veredicto") in ("error", "atrasada"):
            malas.append(f"{fila['fuente']} ({fila['veredicto']})")
print(", ".join(malas))
