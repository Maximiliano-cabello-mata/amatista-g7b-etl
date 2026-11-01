"""Sube al lago las mediciones de la sonda (``g7b.medicion/1``) que estén en una carpeta.

    python -m g7b_lago.subir_mediciones resultados

Las reales van a bronce/sonda/; las marcadas como sintéticas, a sintetico/sonda/ (PLAN 5.7).
Las incompletas se suben igual, porque lo medido sirve, pero el reporte lo dice.
Un archivo ya subido no se vuelve a subir.
"""
import argparse
import glob
import json
import os
import sys
from datetime import date

from .lago import Lago

CONTRATO = "g7b.medicion/1"


def subir(carpeta, lago, salida=print):
    resumen = {"subidas": 0, "ya_existian": 0, "rechazadas": 0, "incompletas": 0}
    for archivo in sorted(glob.glob(os.path.join(carpeta, "*.json"))):
        nombre = os.path.basename(archivo)
        try:
            with open(archivo, encoding="utf-8") as f:
                medicion = json.load(f)
        except (OSError, json.JSONDecodeError) as error:
            salida(f"rechazada {nombre}: no es JSON válido ({error})")
            resumen["rechazadas"] += 1
            continue
        if medicion.get("contrato") != CONTRATO:
            salida(f"rechazada {nombre}: contrato {medicion.get('contrato')!r}, se esperaba {CONTRATO}")
            resumen["rechazadas"] += 1
            continue
        dia = (medicion.get("fecha") or date.today().isoformat())[:10]
        zona = "sintetico" if medicion.get("sintetico", True) else "bronce"  # sin la marca, se trata como sintética
        ruta = f"{zona}/sonda/{dia}/{nombre}"
        if not medicion.get("completa"):
            resumen["incompletas"] += 1
        with open(archivo, "rb") as f:
            subido = lago.subir_bytes(ruta, f.read(), tipo="application/json", metadatos={
                "contrato": CONTRATO, "huella_equipo": medicion.get("equipo", {}).get("huella", ""),
                "nivel": medicion.get("equipo", {}).get("nivel", ""), "completa": medicion.get("completa", False)})
        resumen["subidas" if subido else "ya_existian"] += 1
        salida(f"{'subida' if subido else 'ya existía'} {nombre} -> {ruta}")
    return resumen


def main(argv=None):
    p = argparse.ArgumentParser(prog="subir_mediciones")
    p.add_argument("carpeta", nargs="?", default="resultados")
    opciones = p.parse_args(argv)
    if not os.path.isdir(opciones.carpeta):
        sys.exit(f"No existe la carpeta {opciones.carpeta}")
    resumen = subir(opciones.carpeta, Lago.desde_entorno())
    print(json.dumps(resumen, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main()
