"""Geoda desde la terminal.

    python -m geoda nivel --huella equipo.json            # N0..N4 con motivos y confianza
    python -m geoda perfiles [--cubo cubo.duckdb] [--salida perfiles.json]
    python -m geoda decidir --huella equipo.json [--blender 4.5] [--perfiles perfiles.json] [--cubo cubo.duckdb]
    python -m geoda operaciones                           # catálogo de operaciones del kernel

    El núcleo público (geoda.nucleo/1), que solo lee el paquete de conocimiento:
    python -m geoda paquete [--cubo cubo.duckdb] [--verificar-manual] --salida paquete.json
    python -m geoda plan --paquete paquete.json --huella equipo.json [--blender 4.5] [--idioma es]
    python -m geoda conformidad [--paquete paquete.json]  # los casos que toda implementación debe pasar

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
    pq = sub.add_parser("paquete", help="construir el paquete de conocimiento (g7b.geoda.paquete/1)")
    pq.add_argument("--cubo", help="oro/cubo.duckdb (g7b.cubo/2 o /3); sin él, solo reglas base")
    pq.add_argument("--manifiesto", help="manifiesto.json del cubo, para citar su versión")
    pq.add_argument("--verificar-manual", action="store_true",
                    help="descargar los objects.inv del manual y comprobar cada cita")
    pq.add_argument("--salida", required=True)
    pl = sub.add_parser("plan", help="el plan del núcleo público, con evidencia y citas")
    pl.add_argument("--paquete", required=True)
    pl.add_argument("--huella", required=True)
    pl.add_argument("--blender")
    pl.add_argument("--idioma", default="es")
    co = sub.add_parser("conformidad", help="correr geoda/conformidad.json contra el núcleo")
    co.add_argument("--paquete", help="sin él, un paquete de solo reglas base")
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
    elif o.orden == "paquete":
        from . import paquete

        con = _cubo(o.cubo) if o.cubo else None
        cubo = None
        if o.manifiesto:
            with open(o.manifiesto, encoding="utf-8") as archivo:
                m = json.load(archivo)
            cubo = {k: m.get(k) for k in ("contrato", "generado", "mediciones", "directas", "relativas")}
        inventarios = paquete.inventarios_manual() if o.verificar_manual else None
        documento = paquete.construir(con, cubo, inventarios)
        with open(o.salida, "w", encoding="utf-8") as archivo:
            json.dump(documento, archivo, ensure_ascii=False, indent=1)
            archivo.write("\n")
        print(json.dumps({"paquete": documento["version"], **documento["evidencia"]}, ensure_ascii=False))
    elif o.orden == "plan":
        from .nucleo import Nucleo

        tarea = {"tipo": "practica", **({"blender": o.blender} if o.blender else {})}
        _imprimir(Nucleo.desde_archivo(o.paquete).decidir(_leer(o.huella), tarea, o.idioma))
    elif o.orden == "conformidad":
        from . import conformidad

        resultado = conformidad.correr(o.paquete)
        _imprimir(resultado)
        return 0 if not resultado["fallas"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
