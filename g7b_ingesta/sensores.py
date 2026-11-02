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


# ---------------------------------------------------------------- Geodar Radar: sensores nuevos

HUELLAS_MAX = 20000


def _json(respuesta):
    import json

    if respuesta.estado != 200:
        raise RuntimeError(f"HTTP {respuesta.estado}")
    return json.loads(respuesta.contenido)


def _huella_corta(datos):
    import json

    return hashlib.sha256(json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def sensor_discourse(fuente, estado, obtener):
    """Un foro Discourse (Blender Artists, devtalk, Godot, three.js): temas nuevos con sus cifras.

    Solo metadatos: título, etiquetas, categoría, vistas, «me gusta», respuestas y si tiene respuesta
    aceptada. Los mensajes son de sus autores; no se copian. Las cifras son señales de lo que la
    comunidad pregunta y le importa.
    """
    cfg = fuente["sensor"]
    base = cfg["base"].rstrip("/")
    vistos = set(estado.get("vistos", []))
    registros, revisados = [], 0
    for ruta in cfg.get("rutas", ["/latest.json"]):
        for pagina in range(int(cfg.get("paginas", 1))):
            separador = "&" if "?" in ruta else "?"
            url = f"{base}{ruta}" + (f"{separador}page={pagina}" if pagina else "")
            datos = _json(obtener(url, {"Accept": "application/json"}))
            temas = (datos.get("topic_list") or {}).get("topics", [])
            revisados += len(temas)
            for t in temas:
                clave = str(t.get("id"))
                if not t.get("id") or clave in vistos or t.get("pinned") or t.get("pinned_globally"):
                    continue
                vistos.add(clave)
                etiquetas = [e if isinstance(e, str) else (e.get("name") or e.get("slug")) for e in t.get("tags", [])]
                registros.append({
                    "id": clave,
                    "url": f"{base}/t/{t.get('slug', 'tema')}/{t['id']}",
                    "titulo": (t.get("title") or "").strip(),
                    "fecha": t.get("created_at"),
                    "etiquetas": [e for e in etiquetas if e],
                    "datos": {"categoria": t.get("category_id"), "vistas": t.get("views", 0),
                              "me_gusta": t.get("like_count", 0), "mensajes": t.get("posts_count", 0),
                              "respuestas": t.get("reply_count", 0),
                              "respuesta_aceptada": bool(t.get("has_accepted_answer")),
                              "ultimo_mensaje": t.get("last_posted_at")},
                })
            if not temas:
                break
    nuevo = dict(estado)
    nuevo["vistos"] = _vistos(estado, [r["id"] for r in registros])
    return {"urls": [], "registros": registros, "nota": f"{len(registros)} temas nuevos de {revisados}"}, nuevo


def sensor_github_releases(fuente, estado, obtener):
    """Versiones nuevas de herramientas libres en GitHub, con la licencia y las cifras del repo.

    Usa GITHUB_TOKEN si existe (en Actions siempre existe) para tener más cuota.
    """
    import os

    cabeceras = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        cabeceras["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    vistos = set(estado.get("vistos", []))
    registros, errores = [], []
    for repo in fuente["sensor"]["repos"]:
        try:
            versiones = _json(obtener(f"https://api.github.com/repos/{repo}/releases?per_page=5", cabeceras))
        except RuntimeError as error:
            errores.append(f"{repo}: {error}")
            continue
        nuevas = [v for v in versiones if not v.get("draft") and f"{repo}@{v.get('tag_name')}" not in vistos]
        if not nuevas:
            continue
        info = _json(obtener(f"https://api.github.com/repos/{repo}", cabeceras))
        for v in nuevas:
            clave = f"{repo}@{v.get('tag_name')}"
            vistos.add(clave)
            registros.append({
                "id": clave,
                "url": v.get("html_url"),
                "titulo": f"{repo} {v.get('name') or v.get('tag_name')}",
                "fecha": v.get("published_at"),
                "etiquetas": info.get("topics", []),
                "datos": {"repo": repo, "version": v.get("tag_name"), "previa": bool(v.get("prerelease")),
                          "notas": (v.get("body") or "")[:1500],
                          "licencia": ((info.get("license") or {}).get("spdx_id")),
                          "estrellas": info.get("stargazers_count"), "descripcion": info.get("description"),
                          "sitio": info.get("homepage")},
            })
    if errores and len(errores) == len(fuente["sensor"]["repos"]):
        raise RuntimeError("; ".join(errores)[:300])
    nuevo = dict(estado)
    nuevo["vistos"] = _vistos(estado, [r["id"] for r in registros])
    nota = f"{len(registros)} versiones nuevas en {len(fuente['sensor']['repos'])} repos"
    if errores:
        nota += f" ({len(errores)} repos con error: {errores[0][:80]})"
    return {"urls": [], "registros": registros, "nota": nota}, nuevo


def _ruta(datos, ruta):
    for parte in [p for p in (ruta or "").split(".") if p]:
        datos = datos.get(parte, {}) if isinstance(datos, dict) else {}
    return datos


def sensor_json_api(fuente, estado, obtener):
    """Una API JSON que devuelve una lista (o un diccionario) de elementos: avisa de los nuevos o cambiados.

    sensor:
      url:          dirección de la API
      items:        ruta hasta la lista o el diccionario ("data", "foundAssets"; vacío = la raíz)
      id:           campo con el identificador; "@clave" si los elementos son un diccionario por id
      titulo:       campo con el nombre
      campos:       qué campos guardar (vacío = todos)
      solo_ids:     guardar solo estos ids (p. ej. unas pocas funciones de caniuse)
      url_item:     plantilla del enlace de cada elemento, con {id}
      campo_url:    o el campo del elemento que ya trae su enlace
      huella_sin:   campos que no cuentan como cambio (p. ej. descargas, que cambian a diario)
    """
    cfg = fuente["sensor"]
    respuesta = obtener(cfg["url"], {"Accept": "application/json", **_condicionales(estado)})
    if respuesta.estado == 304:
        return _sin_cambios(estado, "sin cambios (304)")
    datos = _ruta(_json(respuesta), cfg.get("items", ""))
    if isinstance(datos, dict):
        pares = list(datos.items())
    elif isinstance(datos, list):
        pares = [(str(e.get(cfg.get("id", "id"), "")), e) for e in datos if isinstance(e, dict)]
    else:
        raise RuntimeError("la API no devolvió una lista ni un diccionario en la ruta indicada")
    solo = set(cfg.get("solo_ids") or [])
    campos = cfg.get("campos") or []
    sin = set(cfg.get("huella_sin") or [])
    huellas = dict(estado.get("huellas", {}))
    registros = []
    for clave, elemento in pares:
        clave = str(clave)
        if not clave or not isinstance(elemento, dict) or (solo and clave not in solo):
            continue
        guardado = {k: elemento[k] for k in campos if k in elemento} if campos else dict(elemento)
        huella = _huella_corta({k: v for k, v in guardado.items() if k not in sin})
        if huellas.get(clave) == huella:
            continue
        huellas[clave] = huella
        registros.append({
            "id": clave,
            "url": (elemento.get(cfg["campo_url"]) if cfg.get("campo_url") else None)
                   or (cfg["url_item"].format(id=clave) if cfg.get("url_item") else cfg["url"]),
            "titulo": str(elemento.get(cfg.get("titulo", "name"), clave)),
            "datos": guardado,
        })
    if len(huellas) > HUELLAS_MAX:
        huellas = dict(list(huellas.items())[-HUELLAS_MAX:])
    nuevo = _recordar(estado, respuesta)
    nuevo["huellas"] = huellas
    return {"urls": [], "registros": registros,
            "nota": f"{len(registros)} nuevos o cambiados de {len(pares)}"}, nuevo


SENSORES = {"atom": sensor_feed, "rss": sensor_feed, "pagina": sensor_pagina,
            "sitemap": sensor_sitemap, "stackexchange": sensor_stackexchange,
            "discourse": sensor_discourse, "github_releases": sensor_github_releases,
            "json_api": sensor_json_api}
