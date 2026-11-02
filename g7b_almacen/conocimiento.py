"""Une al warehouse lo que ya produce el lado del conocimiento (texto), que ya funcionaba.

El embudo (``g7b_ingesta/procesar.py``) deja en el lago ``control/embudo.json`` (conteos por fuente y
etapa) y ``control/procesados.json`` (qué se procesó). Aquí se leen tal como están y se resumen, para
que el tablero muestre UNA sola foto: conocimiento (documentos) y mediciones (sonda y Open Data).

No se re-procesa nada ni se toca MongoDB: solo se lee lo que el embudo ya escribió. Si esos archivos
todavía no existen (ingesta apagada), devuelve ceros, sin fallar.
"""
import json

CONTEOS = "control/embudo.json"
PROCESADOS = "control/procesados.json"


def _leer(almacen, ruta, por_omision):
    if not almacen.existe(ruta):
        return por_omision
    try:
        return json.loads(almacen.leer(ruta))
    except (ValueError, OSError):
        return por_omision


def resumen(almacen):
    """{estados, por_fuente, archivos_procesados} a partir de lo que el embudo dejó en control/."""
    conteos = _leer(almacen, CONTEOS, {})          # {fuente: {"aceptado:valor": n, ...}}
    procesados = _leer(almacen, PROCESADOS, {})
    estados = {"aceptado": 0, "revision": 0, "rechazado": 0}
    por_fuente = {}
    for fuente, claves in (conteos or {}).items():
        fila = {"aceptado": 0, "revision": 0, "rechazado": 0}
        for clave, n in (claves or {}).items():
            estado = clave.split(":", 1)[0]
            if estado in fila:
                fila[estado] += n
                estados[estado] += n
        por_fuente[fuente] = fila
    return {
        "estados": estados,
        "documentos_aceptados": estados["aceptado"],
        "por_fuente": [{"fuente": f, **fila} for f, fila in sorted(por_fuente.items())],
        "archivos_bronce_procesados": len(procesados or {}),
        "ingesta_activa": bool(conteos),
    }
