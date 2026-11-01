"""Sensores: cada uno revisa una fuente con el menor costo posible y dice qué hay de nuevo.

Firma común:  sensor(fuente, estado, obtener) -> (salida, estado_nuevo)
    salida = {"urls": [...], "registros": [...], "nota": str}
      urls       lo que hay que extraer (para los extractores zyte o descarga)
      registros  contenido que el sensor ya trae (extractor directo: feeds y API)
    estado     lo que el sensor recuerda entre corridas (ETag, huellas, ids vistos...)
"""
import hashlib
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

VISTOS_MAX = 5000


def _condicionales(estado):
    cabeceras = {}
    if estado.get("etag"):
        cabeceras["If-None-Match"] = estado["etag"]
    if estado.get("last_modified"):
        cabeceras["If-Modified-Since"] = estado["last_modified"]
    return cabeceras


def _recordar(estado, respuesta):
    nuevo = dict(estado)
    if respuesta.cabeceras.get("etag"):
        nuevo["etag"] = respuesta.cabeceras["etag"]
    if respuesta.cabeceras.get("last-modified"):
        nuevo["last_modified"] = respuesta.cabeceras["last-modified"]
    return nuevo


def _vistos(estado, nuevos):
    return (list(estado.get("vistos", [])) + list(nuevos))[-VISTOS_MAX:]


def _sin_cambios(estado, motivo):
    return {"urls": [], "registros": [], "nota": motivo}, estado


def sensor_feed(fuente, estado, obtener):
    """Atom o RSS: devuelve las entradas que no se habían visto."""
    import feedparser

    respuesta = obtener(fuente["sensor"]["url"], _condicionales(estado))
    if respuesta.estado == 304:
        return _sin_cambios(estado, "sin cambios (304)")
    if respuesta.estado != 200:
        raise RuntimeError(f"HTTP {respuesta.estado}")
    feed = feedparser.parse(respuesta.contenido)
    vistos = set(estado.get("vistos", []))
    registros = []
    for entrada in feed.entries:
        clave = entrada.get("id") or entrada.get("link")
        if not clave or clave in vistos:
            continue
        registros.append({
            "id": clave,
            "url": entrada.get("link"),
            "titulo": (entrada.get("title") or "").strip(),
            "resumen": (entrada.get("summary") or "").strip(),
            "fecha": entrada.get("published") or entrada.get("updated"),
            "autores": [a.get("name") for a in entrada.get("authors", []) if a.get("name")],
            "categorias": [t.get("term") for t in entrada.get("tags", []) if t.get("term")],
        })
    nuevo = _recordar(estado, respuesta)
    nuevo["vistos"] = _vistos(estado, [r["id"] for r in registros])
    return {"urls": [r["url"] for r in registros if r["url"]], "registros": registros,
            "nota": f"{len(registros)} entradas nuevas de {len(feed.entries)}"}, nuevo


def sensor_pagina(fuente, estado, obtener):
    """Una página: avisa si cambió (ETag, Last-Modified o huella del contenido)."""
    url = fuente["sensor"]["url"]
    respuesta = obtener(url, _condicionales(estado))
    if respuesta.estado == 304:
        return _sin_cambios(estado, "sin cambios (304)")
    if respuesta.estado != 200:
        raise RuntimeError(f"HTTP {respuesta.estado}")
    huella = hashlib.sha256(respuesta.contenido).hexdigest()
    nuevo = _recordar(estado, respuesta)
    nuevo["huella"] = huella
    if huella == estado.get("huella"):
        return {"urls": [], "registros": [], "nota": "sin cambios (misma huella)"}, nuevo
    return {"urls": [url], "registros": [], "nota": "cambió" if estado.get("huella") else "primera vez"}, nuevo


def sensor_sitemap(fuente, estado, obtener):
    """Un sitemap: URLs nuevas o con lastmod más reciente que la última vez."""
    respuesta = obtener(fuente["sensor"]["url"], _condicionales(estado))
    if respuesta.estado == 304:
        return _sin_cambios(estado, "sin cambios (304)")
    if respuesta.estado != 200:
        raise RuntimeError(f"HTTP {respuesta.estado}")
    raiz = ET.fromstring(respuesta.contenido)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    conocidas = dict(estado.get("lastmod", {}))
    cambiadas = []
    for nodo in raiz.findall("s:url", ns):
        loc = (nodo.findtext("s:loc", default="", namespaces=ns) or "").strip()
        lastmod = (nodo.findtext("s:lastmod", default="", namespaces=ns) or "").strip()
        if loc and (loc not in conocidas or (lastmod and lastmod > conocidas[loc])):
            cambiadas.append(loc)
        if loc:
            conocidas[loc] = lastmod
    nuevo = _recordar(estado, respuesta)
    nuevo["lastmod"] = conocidas
    return {"urls": cambiadas, "registros": [], "nota": f"{len(cambiadas)} URLs nuevas o cambiadas"}, nuevo


def sensor_stackexchange(fuente, estado, obtener, ahora=None):
    """Preguntas con votos de un sitio de Stack Exchange, con su mejor respuesta.

    Se miran las preguntas creadas hace entre 7 y 30 días: los votos ya se asentaron y el filtro
    de puntaje mínimo tiene sentido. Las ya vistas no se repiten.
    """
    import json
    import os
    from urllib.parse import urlencode

    cfg = fuente["sensor"]
    ahora = int(ahora or time.time())
    base = "https://api.stackexchange.com/2.3"
    comunes = {"site": cfg.get("sitio", "blender"), "filter": "withbody", "pagesize": 100}
    if os.environ.get("STACKEXCHANGE_KEY"):
        comunes["key"] = os.environ["STACKEXCHANGE_KEY"]
    consulta = {**comunes, "sort": "votes", "order": "desc", "min": cfg.get("puntaje_minimo", 3),
                "fromdate": ahora - 30 * 86400, "todate": ahora - 7 * 86400}
    respuesta = obtener(f"{base}/questions?{urlencode(consulta)}", {})
    if respuesta.estado != 200:
        raise RuntimeError(f"HTTP {respuesta.estado}")
    datos = json.loads(respuesta.contenido)
    vistos = set(estado.get("vistos", []))
    preguntas = [p for p in datos.get("items", []) if str(p["question_id"]) not in vistos]
    mejores = {}
    if preguntas:
        ids = ";".join(str(p["question_id"]) for p in preguntas)
        r2 = obtener(f"{base}/questions/{ids}/answers?{urlencode({**comunes, 'sort': 'votes', 'order': 'desc'})}", {})
        if r2.estado == 200:
            for a in json.loads(r2.contenido).get("items", []):
                previa = mejores.get(a["question_id"])
                if previa is None or a.get("is_accepted") or (not previa.get("is_accepted") and a["score"] > previa["score"]):
                    mejores[a["question_id"]] = a
    registros = []
    for p in preguntas:
        respuesta_mejor = mejores.get(p["question_id"])
        registros.append({
            "id": str(p["question_id"]),
            "url": p.get("link"),
            "titulo": p.get("title", ""),
            "texto_html": p.get("body", "") + ("\n<hr/>\n" + respuesta_mejor.get("body", "") if respuesta_mejor else ""),
            "puntaje": p.get("score", 0),
            "respuesta_aceptada": bool(respuesta_mejor and respuesta_mejor.get("is_accepted")),
            "etiquetas": p.get("tags", []),
            "fecha": datetime.fromtimestamp(p.get("creation_date", ahora), tz=timezone.utc).isoformat(),
            # CC BY-SA pide atribución: se guarda el nombre público del autor y el enlace.
            "autor": (p.get("owner") or {}).get("display_name"),
            "autor_respuesta": ((respuesta_mejor or {}).get("owner") or {}).get("display_name"),
        })
    nuevo = dict(estado)
    nuevo["vistos"] = _vistos(estado, [r["id"] for r in registros])
    nuevo["cuota_restante"] = datos.get("quota_remaining")
    return {"urls": [r["url"] for r in registros], "registros": registros,
            "nota": f"{len(registros)} preguntas nuevas (cuota restante {datos.get('quota_remaining')})"}, nuevo


SENSORES = {"atom": sensor_feed, "rss": sensor_feed, "pagina": sensor_pagina,
            "sitemap": sensor_sitemap, "stackexchange": sensor_stackexchange}
