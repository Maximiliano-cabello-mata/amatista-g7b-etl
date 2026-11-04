"""Geoda desde la terminal.

    python -m geoda nivel --huella equipo.json            # N0..N4 con motivos y confianza
    python -m geoda perfiles [--cubo cubo.duckdb] [--salida perfiles.json]
    python -m geoda decidir --huella equipo.json [--blender 4.5] [--perfiles perfiles.json] [--cubo cubo.duckdb]
    python -m geoda operaciones                           # catálogo de operaciones del kernel

«equipo.json» puede ser un g7b.huella/1 o el bloque «equipo» de una medición de la sonda.
Sin --cubo, los perfiles salen de las reglas base (estado «base»).
"""
import argparse
import json
import sys

from .contratos import Huella


def _leer(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos.get("equipo", datos) if datos.get("contrato") == "g7b.medicion/1" else datos


def _cubo(ruta):
    import duckdb

    return duckdb.connect(ruta, read_only=True)


def _imprimir(datos, salida=None):
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    if salida:
        with open(salida, "w", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
        print(f"Escrito en {salida}")
    else:
        print(texto)


def main(argv=None):
    p = argparse.ArgumentParser(prog="geoda", description="Geoda: adapta el trabajo 3D a cada equipo.")
    sub = p.add_subparsers(dest="orden", required=True)
    n = sub.add_parser("nivel", help="clasificar un equipo (N0 a N4)")
    n.add_argument("--huella", required=True)
    pe = sub.add_parser("perfiles", help="generar perfiles.json (g7b.perfil/1)")
    pe.add_argument("--cubo", help="cubo.duckdb del warehouse; sin él, reglas base")
    pe.add_argument("--salida")
    d = sub.add_parser("decidir", help="el plan para un equipo (g7b.plan/1)")
    d.add_argument("--huella", required=True)
    d.add_argument("--blender", help="versión que pide la práctica")
    d.add_argument("--perfiles", help="perfiles.json publicado")
    d.add_argument("--cubo", help="cubo.duckdb para estimar costos")
    sub.add_parser("operaciones", help="catálogo de operaciones del kernel")
    o = p.parse_args(argv)

    from . import costos, niveles, perfiles, planificador

    if o.orden == "nivel":
        _imprimir(niveles.clasificar(Huella.desde_dict(_leer(o.huella))).como_dict())
    elif o.orden == "perfiles":
        if o.cubo:
            con = _cubo(o.cubo)
            mediciones, sin_nivel = perfiles.leer_cubo(con)
            documento = perfiles.generar(mediciones, sin_nivel, cubo_version=o.cubo)
        else:
            documento = perfiles.generar()
        _imprimir(documento, o.salida)
    elif o.orden == "decidir":
        documento = None
        if o.perfiles:
            with open(o.perfiles, encoding="utf-8") as archivo:
                documento = json.load(archivo)
        tabla = costos.TablaCostos.desde_cubo(_cubo(o.cubo)) if o.cubo else None
        tarea = {"tipo": "practica", **({"blender": o.blender} if o.blender else {})}
        _imprimir(planificador.decidir(_leer(o.huella), tarea, documento, tabla))
    elif o.orden == "operaciones":
        _imprimir(costos.catalogo())
    return 0


if __name__ == "__main__":
    sys.exit(main())
