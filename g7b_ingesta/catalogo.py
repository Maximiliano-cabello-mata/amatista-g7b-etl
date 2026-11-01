"""Catálogo de fuentes (fuentes/catalogo.yml) y taxonomía de preguntas (fuentes/taxonomia.yml)."""
import os

import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CATALOGO = os.path.join(RAIZ, "fuentes", "catalogo.yml")
RUTA_TAXONOMIA = os.path.join(RAIZ, "fuentes", "taxonomia.yml")

OBLIGATORIOS = ("id", "nombre", "tipo", "licencia", "licencia_verificada", "modo", "preguntas",
                "sensor", "extractor", "frecuencia_horas", "dominios", "activa")
MODOS = {"texto_completo", "solo_metadatos", "agregados"}
SENSORES = {"atom", "rss", "pagina", "sitemap", "stackexchange"}
EXTRACTORES = {"directo", "zyte", "descarga"}
PREGUNTAS = {"P1", "P2", "P3", "P4", "P5", "P6", "P7"}


def validar(catalogo):
    """Devuelve la lista de errores; vacía si el catálogo es válido."""
    errores, ids = [], set()
    for i, f in enumerate(catalogo.get("fuentes", [])):
        nombre = f.get("id", f"#{i}")
        faltan = [c for c in OBLIGATORIOS if c not in f]
        if faltan:
            errores.append(f"{nombre}: faltan {', '.join(faltan)}")
            continue
        if f["id"] in ids:
            errores.append(f"{nombre}: id repetido")
        ids.add(f["id"])
        if f["modo"] not in MODOS:
            errores.append(f"{nombre}: modo desconocido {f['modo']!r}")
        if f["sensor"].get("tipo") not in SENSORES:
            errores.append(f"{nombre}: sensor desconocido {f['sensor'].get('tipo')!r}")
        if f["extractor"] not in EXTRACTORES:
            errores.append(f"{nombre}: extractor desconocido {f['extractor']!r}")
        if not set(f["preguntas"]) <= PREGUNTAS:
            errores.append(f"{nombre}: preguntas fuera del plan {sorted(set(f['preguntas']) - PREGUNTAS)}")
        if f["licencia_verificada"] and f["licencia"] == "por_confirmar":
            errores.append(f"{nombre}: licencia_verificada es true pero la licencia está por confirmar")
        if f["modo"] == "texto_completo" and f["licencia"] == "derechos_reservados":
            errores.append(f"{nombre}: con derechos reservados solo se permite solo_metadatos o agregados")
        if f["extractor"] == "zyte" and f["sensor"]["tipo"] in ("pagina", "sitemap") and "url" not in f["sensor"]:
            errores.append(f"{nombre}: el sensor necesita url")
    return errores


def cargar(ruta=RUTA_CATALOGO):
    with open(ruta, encoding="utf-8") as archivo:
        catalogo = yaml.safe_load(archivo)
    errores = validar(catalogo)
    if errores:
        raise ValueError("Catálogo inválido:\n  " + "\n  ".join(errores))
    return catalogo


def vigilables(catalogo):
    return [f for f in catalogo["fuentes"] if f["activa"] and f["licencia_verificada"]]


def por_id(catalogo):
    return {f["id"]: f for f in catalogo["fuentes"]}


def cargar_taxonomia(ruta=RUTA_TAXONOMIA):
    with open(ruta, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)
