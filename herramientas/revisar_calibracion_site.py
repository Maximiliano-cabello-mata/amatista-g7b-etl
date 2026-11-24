"""Contrasta el informe de Site con las etiquetas de calibración archivadas."""
import argparse
import json
from math import isclose
from pathlib import Path
from urllib.parse import urldefrag

from g7b_ingesta.calidad_documental import MODELOS, calibraciones, clave


def revisar(informe, etiquetas):
    fuente, modelo = informe["fuente"], informe["modelo"]
    if not fuente or modelo not in MODELOS or not modelo.startswith("site/"):
        raise ValueError("Fuente o versión de Site sin soporte")

    bloques = {}
    paginas, paginas_con_muestra = set(), set()
    for fila in informe["evidencia"]:
        ident = fila["id"]
        if not isinstance(ident, str) or not ident.strip() or ident in bloques:
            raise ValueError("ID de bloque vacío o repetido")
        if any(type(fila[campo]) is not bool for campo in ("util", "muestra")):
            raise ValueError("Las etiquetas util y muestra deben ser booleanas")
        if not fila["url"].startswith(("http://", "https://")):
            raise ValueError("Falta la URL de la evidencia")
        pagina = urldefrag(fila["url"])[0]
        paginas.add(pagina)
        if fila["muestra"]:
            if pagina in paginas_con_muestra:
                raise ValueError("Más de una muestra por página")
            paginas_con_muestra.add(pagina)
        bloques[ident] = fila

    visitadas = informe["paginas_visitadas"]
    if (type(visitadas) is not int or visitadas < len(paginas)
            or len(paginas) != informe["paginas_con_candidatos"] or paginas != paginas_con_muestra):
        raise ValueError("La cobertura declarada o la selección por página no coincide")

    reserva = [f for f in etiquetas if (f["fuente"], f["modelo"]) == (fuente, modelo)]
    for f in reserva:
        bloque = bloques.get(f["id"])
        if not bloque or not bloque["muestra"] or (f["url"], f["util"]) != (bloque["url"], bloque["util"]):
            raise ValueError("La etiqueta de reserva no coincide con la muestra archivada")

    resultado = calibraciones(reserva).get(clave(fuente, modelo),
                                          {"k": 0, "n": 0, "inferior95": 0.0, "habilitada": False})
    censo = informe["censo_de_bloques"]
    k, n = sum(f["util"] for f in bloques.values()), len(bloques)
    if (k, n) != (censo["k"], censo["n"]) or (n and not isclose(censo["utilidad"], k / n)):
        raise ValueError("El censo declarado difiere de los bloques etiquetados")
    r = informe["calibracion_paginas_ineditas"]
    if ((r["k"], r["n"]) != (resultado["k"], resultado["n"])
            or r["habilitada"] is not resultado["habilitada"] or r["umbral"] != 0.80
            or not isclose(r["inferior_95_unilateral"], resultado["inferior95"], abs_tol=1e-9)
            or (reserva and not isclose(r["precision"], resultado["k"] / resultado["n"]))):
        raise ValueError("La calibración declarada difiere de las etiquetas de reserva")

    return {"fuente": fuente, "modelo": modelo, "paginas_visitadas": visitadas,
            "paginas_con_candidatos": len(paginas), "bloques_utiles": k, "bloques_revisados": n,
            "reserva": resultado, "umbral": r["umbral"], "revisor": informe["revisor"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("informe", type=Path)
    parser.add_argument("etiquetas", type=Path)
    args = parser.parse_args()
    try:
        informe, etiquetas = (p.read_text(encoding="utf-8") for p in (args.informe, args.etiquetas))
        resultado = revisar(json.loads(informe), json.loads(etiquetas))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f"No se pudo verificar el informe: {exc}\n")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
