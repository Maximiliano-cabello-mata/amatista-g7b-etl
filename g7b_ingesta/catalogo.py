"""Catálogo de fuentes (fuentes/catalogo.yml) y taxonomía de preguntas (fuentes/taxonomia.yml)."""
import os

import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CATALOGO = os.path.join(RAIZ, "fuentes", "catalogo.yml")
RUTA_TAXONOMIA = os.path.join(RAIZ, "fuentes", "taxonomia.yml")

OBLIGATORIOS = ("id", "nombre", "tipo", "licencia", "licencia_verificada", "modo", "preguntas",
                "sensor", "extractor", "frecuencia_horas", "dominios", "activa")
MODOS = {"texto_completo", "solo_metadatos", "agregados"}
SENSORES = {"atom", "rss", "pagina", "sitemap", "stackexchange", "discourse", "github_releases", "json_api",
            "externo"}
EXTRACTORES = {"directo", "zyte", "descarga", "externo"}
PREGUNTAS = {"P1", "P2", "P3", "P4", "P5", "P6", "P7"}

# Las siete familias de datos del plan maestro (docs/PLAN_MAESTRO.md, sección 2).
FAMILIAS = {
    "F1": "Telemetría de equipos",
    "F2": "Formas optimizadas (costo por operación)",
    "F3": "Texturas y materiales",
    "F4": "Herramientas",
    "F5": "Técnicas y conocimiento",
    "F6": "Aprendizaje",
    "F7": "Modelos 3D",
}

# A dónde va cada cosa. Todo entra primero crudo a Azure (bronce): así nada se pierde.
# Después, MongoDB guarda documentos y catálogos; Azure guarda telemetría y señales para el cubo.
DESTINOS = {
    "documentos": "MongoDB conocimiento_3d.documentos, después del embudo de calidad (procesar + publicar)",
    "catalogo": "MongoDB g7b_catalogo.<coleccion> (catalogar)",
    "telemetria": "Azure: bronce → cubo DuckDB del warehouse (g7b_almacen)",
    "senales": "Azure: oro/senales/ con el resumen semanal (senales) → cubo y panel",
}
REQUIERE_RESPETO = {"senales", "telemetria"}  # cifras: nunca texto completo ajeno


def familia(f):
    return f.get("familia", "F5")


def destino(f):
    return f.get("destino", "documentos")


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
        if familia(f) not in FAMILIAS:
            errores.append(f"{nombre}: familia desconocida {familia(f)!r}")
        if destino(f) not in DESTINOS:
            errores.append(f"{nombre}: destino desconocido {destino(f)!r}")
        if destino(f) == "catalogo" and not f.get("coleccion"):
            errores.append(f"{nombre}: un destino catalogo necesita coleccion")
        if destino(f) in REQUIERE_RESPETO and f["modo"] == "texto_completo":
            errores.append(f"{nombre}: telemetría y señales guardan cifras y metadatos, no texto_completo")
        necesita = {"discourse": "base", "github_releases": "repos", "json_api": "url",
                    "atom": "url", "rss": "url"}.get(f["sensor"].get("tipo"))
        if necesita and necesita not in f["sensor"]:
            errores.append(f"{nombre}: el sensor {f['sensor']['tipo']} necesita {necesita}")
        if f["extractor"] == "externo" and not f.get("gestor"):
            errores.append(f"{nombre}: un extractor externo necesita gestor (quién lo trae)")
    return errores


def cargar(ruta=RUTA_CATALOGO):
    with open(ruta, encoding="utf-8") as archivo:
        catalogo = yaml.safe_load(archivo)
    errores = validar(catalogo)
    if errores:
        raise ValueError("Catálogo inválido:\n  " + "\n  ".join(errores))
    return catalogo


def vigilables(catalogo):
    """Lo que revisa «vigilar»: activa, con licencia confirmada y sin un gestor externo que la traiga."""
    return [f for f in catalogo["fuentes"]
            if f["activa"] and f["licencia_verificada"] and f["extractor"] != "externo"]


def por_destino(catalogo, nombre):
    return [f for f in catalogo["fuentes"] if destino(f) == nombre]


def por_id(catalogo):
    return {f["id"]: f for f in catalogo["fuentes"]}


def cargar_taxonomia(ruta=RUTA_TAXONOMIA):
    with open(ruta, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)
