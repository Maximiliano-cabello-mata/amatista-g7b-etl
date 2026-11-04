"""Prueba aislada de Blender: sube UN JSON real y su manifiesto a tmp/.

NUNCA escribe en bronce/, plata/, oro/, control/ o publicado/.
Se ejecuta en GitHub Actions con el secret AZURE_LAGO_URL del environment amatista1.

Uso:
    python -m g7b_lago.prueba_blender_aislada resultados

Las ejecuciones quedan en:
    tmp/pruebas-blender/<GITHUB_RUN_ID>-intento<GITHUB_RUN_ATTEMPT>/
"""
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .lago import Lago

RAIZ = "tmp/pruebas-blender"


def _identificador(valor, nombre):
    valor = str(valor or "")
    if not re.fullmatch(r"[1-9][0-9]{0,18}", valor):
        raise ValueError(f"{nombre} debe ser un entero positivo de GitHub Actions")
    return valor


def subir_prueba(lago, archivo, run_id, intento):
    """Sube archivos sin sobrescribir y verifica bytes descargados de Azure."""
    run_id = _identificador(run_id, "GITHUB_RUN_ID")
    intento = _identificador(intento, "GITHUB_RUN_ATTEMPT")
    raiz = f"{RAIZ}/{run_id}-intento{intento}"
    datos = Path(archivo).read_bytes()
    medicion = json.loads(datos)
    if medicion.get("contrato") != "g7b.medicion/1":
        raise ValueError("No es una medición G7B")
    if medicion.get("sintetico") is not False or medicion.get("origen") != "actions":
        raise ValueError("La prueba requiere una medición real de un runner de Actions")
    if not medicion.get("completa"):
        raise ValueError("La medición no está completa")
    resultados = medicion.get("resultados")
    if not isinstance(resultados, list) or not resultados:
        raise ValueError("No se encontraron resultados de rendimiento")
    medidos = [x for x in resultados if x.get("mediana") is not None and not x.get("no_disponible")]
    if not medidos:
        raise ValueError("Ninguna prueba consiguió medir rendimiento")
    ruta = f"{raiz}/medicion.json"
    lago.subir_bytes(ruta, datos, tipo="application/json", sobrescribir=False)
    remoto = lago.contenedor.download_blob(ruta).readall()
    if remoto != datos:
        raise IOError("El archivo descargado de Azure no coincide con el original")

    resumen = {
        "contrato": "g7b.prueba_aislada/1",
        "estado": "verificado",
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origen": "github_actions",
        "carpeta_azure": raiz,
        "archivo": ruta,
        "sha256": hashlib.sha256(datos).hexdigest(),
        "blender": medicion.get("blender", {}).get("version"),
        "escena": medicion.get("escena", {}).get("nombre"),
        "completa": True,
        "pruebas_total": len(resultados),
        "pruebas_medidas": len(medidos),
        "pruebas_no_disponibles": len(resultados) - len(medidos),
        "duracion_sonda_s": medicion.get("duracion_total_s"),
    }
    manifiesto = f"{raiz}/verificacion.json"
    contenido = json.dumps(resumen, ensure_ascii=False, indent=2).encode()
    lago.subir_bytes(manifiesto, contenido, tipo="application/json", sobrescribir=False)
    if lago.contenedor.download_blob(manifiesto).readall() != contenido:
        raise IOError("No se pudo verificar el manifiesto en Azure")
    return resumen


def main():
    archivos = sorted(glob.glob("resultados/medicion_*.json"))
    if len(archivos) != 1:
        sys.exit(f"Se esperaba un JSON de Blender, se encontraron {len(archivos)}")
    if not os.environ.get("AZURE_LAGO_URL"):
        sys.exit("Falta el secreto AZURE_LAGO_URL en el environment amatista1")
    resumen = subir_prueba(
        Lago.desde_entorno(),
        archivos[0],
        os.environ.get("GITHUB_RUN_ID"),
        os.environ.get("GITHUB_RUN_ATTEMPT"),
    )
    print("AZURE_PRUEBA_VERIFICADA", json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    main()
