"""Línea de comandos del warehouse.

    python -m g7b_almacen opendata            baja la copia más reciente de Blender Open Data a bronce
    python -m g7b_almacen construir           plata y oro (cubo, CSV, resumen, perfiles.json)
    python -m g7b_almacen todo                las dos cosas, en ese orden
    python -m g7b_almacen sonda RESULTADOS    agrega mediciones de la sonda a bronce/sonda/

Sin ``--carpeta`` trabaja contra el lago de Azure (AZURE_LAGO_URL). Con ``--carpeta datos`` trabaja
en una carpeta local con la misma estructura: sirve en tu PC y en Deepnote, sin nube.
"""
import argparse
import glob
import json
import os
import sys

from . import almacen as alm
from . import cubo, opendata, plata, vigia


def agregar_sonda(almacen, carpeta, salida=print):
    """Copia a bronce/sonda/<día>/ las mediciones reales; las sintéticas, a sintetico/sonda/."""
    resumen = {"agregadas": 0, "ya_existian": 0, "rechazadas": 0}
    for archivo in sorted(glob.glob(os.path.join(carpeta, "**", "*.json"), recursive=True)):
        with open(archivo, "rb") as f:
            datos = f.read()
        try:
            medicion = plata.leer_medicion(datos)
        except (ValueError, json.JSONDecodeError) as error:
            salida(f"rechazada {archivo}: {error}")
            resumen["rechazadas"] += 1
            continue
        zona = "sintetico" if medicion.get("sintetico", True) else "bronce"
        ruta = f"{zona}/sonda/{str(medicion.get('fecha') or '')[:10] or 'sin-fecha'}/{os.path.basename(archivo)}"
        if almacen.existe(ruta):
            resumen["ya_existian"] += 1
            continue
        almacen.escribir(ruta, datos, sobrescribir=False)
        resumen["agregadas"] += 1
        salida(f"agregada {os.path.basename(archivo)} -> {ruta}")
    return resumen


def main(argv=None):
    p = argparse.ArgumentParser(prog="g7b_almacen", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("orden", choices=["opendata", "construir", "todo", "sonda"])
    p.add_argument("resultados", nargs="?", default="resultados", help="carpeta con JSON de la sonda (orden sonda)")
    p.add_argument("--carpeta", help="almacén local en lugar del lago de Azure")
    p.add_argument("--url", help="enlace directo a la copia de Open Data (si la página cambia)")
    opciones = p.parse_args(argv)
    almacen = alm.desde_entorno(opciones.carpeta)

    if opciones.orden == "sonda":
        if not os.path.isdir(opciones.resultados):
            sys.exit(f"No existe la carpeta {opciones.resultados}")
        print(json.dumps(agregar_sonda(almacen, opciones.resultados), ensure_ascii=False))
        return
    if opciones.orden in ("opendata", "todo"):
        with vigia.monitor("g7b-opendata"):
            opendata.descargar(almacen, url=opciones.url)
    if opciones.orden in ("construir", "todo"):
        with vigia.monitor("g7b-cubo"):
            datos = cubo.construir(almacen)
        print(json.dumps(datos["conteos"], ensure_ascii=False))


if __name__ == "__main__":
    main()
