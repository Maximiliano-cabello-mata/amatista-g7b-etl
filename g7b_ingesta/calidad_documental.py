"""Precisión de candidatos por fuente y versión del modelo, sobre páginas revisadas."""
import argparse
import json
from math import sqrt
from pathlib import Path
from urllib.parse import urldefrag

from motor_extraccion.documental import MODELO

AUDITORIA = Path(__file__).resolve().parents[1] / "algoritmos/documentacion/auditoria.json"
Z = 1.6448536269514722  # límite inferior unilateral del 95 %


def inferior(k, n):
    if not n:
        return 0.0
    p = k / n
    return (p + Z**2 / (2*n) - Z*sqrt(p*(1-p)/n + Z**2/(4*n*n))) / (1 + Z**2/n)


def calibraciones(filas):
    grupos = {}
    for f in filas:
        if f["modelo"] != MODELO:
            continue
        if (type(f["util"]) is not bool or not f.get("revisor") or not f.get("id")
                or not str(f.get("url", "")).startswith(("https://", "http://"))):
            raise ValueError("Etiqueta incompleta de auditoría documental")
        pagina = urldefrag(f["url"])[0]
        grupo = grupos.setdefault(f["fuente"], {})
        if pagina in grupo:
            raise ValueError("La muestra admite un candidato por página y fuente")
        grupo[pagina] = f["util"]
    return {fuente: {"n": len(g), "k": sum(g.values()), "inferior95": inferior(sum(g.values()), len(g)),
                     "habilitada": inferior(sum(g.values()), len(g)) >= 0.80}
            for fuente, g in grupos.items()}


def cargar(ruta=AUDITORIA):
    return calibraciones(json.loads(Path(ruta).read_text(encoding="utf-8")))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archivo", default=AUDITORIA)
    print(json.dumps(cargar(p.parse_args().archivo), ensure_ascii=False, indent=2))
