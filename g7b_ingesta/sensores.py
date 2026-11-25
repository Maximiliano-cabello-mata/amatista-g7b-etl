"""Sensores: cada uno revisa una fuente con el menor costo posible y dice qué hay de nuevo.

Firma común:  sensor(fuente, estado, obtener) -> (salida, estado_nuevo)
    salida = {"urls": [...], "registros": [...], "nota": str}
      urls       lo que hay que extraer (para los extractores zyte o descarga)
      registros  contenido que el sensor ya trae (extractor directo: feeds y API)
    estado     lo que el sensor recuerda entre corridas (ETag, huellas, ids vistos...)
"""
import hashlib
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

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
    dias_desde = int(cfg.get("dias_desde", 30))
    dias_hasta = int(cfg.get("dias_hasta", 7))
    consulta = {**comunes, "sort": "votes", "order": "desc", "min": cfg.get("puntaje_minimo", 3),
                "fromdate": ahora - dias_desde * 86400, "todate": ahora - dias_hasta * 86400}
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


def sensor_sphinx(fuente, estado, obtener, ahora=None):
    """Un manual hecho con Sphinx, versión por versión, mirando su inventario (objects.inv).

    Las páginas del manual de Blender se reconstruyen a diario («Last updated on ...»), así que la
    huella de una página cambia aunque el texto no cambie: con el sensor «pagina» la araña volvía a
    recorrer el manual entero cada vez. El inventario solo cambia cuando se agregan, quitan o
    renombran páginas o apartados. Una versión se vuelve a recorrer cuando su inventario cambia o
    cuando pasaron `refresco_dias` desde su último recorrido (para ediciones de texto).

    Devuelve en «argumentos» las versiones que tocan, para que la araña recorra solo esas.
    """
    from motor_extraccion.inventario_sphinx import SECCIONES_BLENDER, leer

    cfg = fuente["sensor"]
    ahora = ahora or datetime.now(timezone.utc)
    base = cfg["base"].rstrip("/") + "/"
    refresco = timedelta(days=int(cfg.get("refresco_dias", 30)))
    anteriores = estado.get("versiones", {})
    zyte_cfg = fuente.get("zyte")
    alcance = None
    if zyte_cfg:
        extra_secciones = list(SECCIONES_BLENDER) if zyte_cfg.get("arana") == "blender_docs" else []
        alcance = _huella_corta({"zyte": zyte_cfg, "secciones": extra_secciones})
    versiones, tocan, notas = {}, [], []
    for version in cfg["versiones"]:
        previo = dict(anteriores.get(version, {}))
        respuesta = obtener(f"{base}{version}/objects.inv", _condicionales(previo))
        if respuesta.estado == 304:
            actual = dict(previo)
        elif respuesta.estado == 200:
            datos = leer(respuesta.contenido)
            actual = {**_recordar(previo, respuesta), "huella": datos["huella"], "paginas": len(datos["paginas"])}
        else:
            raise RuntimeError(f"HTTP {respuesta.estado} en el inventario de {version}")
        if alcance is not None:
            actual["alcance"] = alcance
        recorrido = actual.get("recorrido")
        if actual.get("huella") != previo.get("huella") or not recorrido:
            motivo = "primera vez" if not previo.get("huella") else "inventario cambió"
        elif alcance is not None and previo.get("alcance") != alcance:
            motivo = "alcance ampliado"
        elif ahora - datetime.fromisoformat(recorrido) >= refresco:
            motivo = f"refresco de {refresco.days} días"
        else:
            motivo = None
        if motivo:
            tocan.append(version)
            actual["recorrido"] = ahora.isoformat(timespec="seconds")
            notas.append(f"{version}: {motivo} ({actual.get('paginas', '?')} páginas)")
        versiones[version] = actual
    nuevo = {**estado, "versiones": versiones}
    if not tocan:
        return {"urls": [], "registros": [], "nota": "sin cambios en los inventarios"}, nuevo
    return {"urls": [f"{base}{v}/" for v in tocan], "registros": [], "nota": "; ".join(notas),
            "argumentos": {"versiones": tocan}}, nuevo


# ---------------------------------------------------------------- reportes de error (telemetría de fallas)

_CAMPO = {
    "so": re.compile(r"operating system:\s*(.+)", re.I),
    "gpu": re.compile(r"graphics card:\s*(.+)", re.I),
    "rota": re.compile(r"broken:\s*(.+)", re.I),
    "funcionaba": re.compile(r"worked:\s*(.+)", re.I),
}
_VERSION = re.compile(r"\b(\d+\.\d+(?:\.\d+)?)\b")
_OPENGL = re.compile(r"\s(\d\.\d)(?:\.\d+)?\b")


def sistema_de_reporte(cuerpo):
    """Los campos de la plantilla de reportes de Blender («System Information», «Blender Version»).

    Solo cifras y nombres de hardware, con el estándar g7b.hardware/1: el texto del reporte es de su
    autor y no se guarda. Lo que la plantilla no trae queda en None.
    """
    from g7b_telemetria import hardware

    cuerpo = cuerpo or ""
    crudo = {k: (m.group(1).strip()[:300] if (m := r.search(cuerpo)) else None) for k, r in _CAMPO.items()}
    salida = {"so": crudo["so"], "gpu_texto": crudo["gpu"], "opengl": None,
              "version_rota": None, "version_funcionaba": None, "hardware": None}
    for campo in ("rota", "funcionaba"):
        texto = crudo[campo] or ""
        v = re.search(r"version:\s*(\d+\.\d+(?:\.\d+)?)", texto, re.I) or _VERSION.search(texto)
        salida["version_" + campo] = v.group(1) if v else None
    if crudo["gpu"]:
        gl = _OPENGL.search(crudo["gpu"])
        salida["opengl"] = float(gl.group(1)) if gl else None
        nombre = crudo["gpu"][:gl.start()] if gl else crudo["gpu"]
        g = hardware.gpu(nombre)
        bloque = {"estandar": hardware.ESTANDAR, "mide": "falla", "so": crudo["so"], "gpus": [g]}
        if g["clase"] != "desconocida":
            bloque.update(hardware.nivel([g], opengl=salida["opengl"]))
        else:
            bloque.update(nivel=None, confianza=None, motivos=["GPU no reconocida por fuentes/hardware.yml"])
        salida["hardware"] = bloque
    return salida


def sensor_gitea_issues(fuente, estado, obtener, ahora=None):
    """Reportes de error de un Gitea (projects.blender.org): qué falla, en qué GPU, sistema y versión.

    Es telemetría de fallas para P2 («qué versión conviene en cada equipo»). Pide por la API, poco y
    despacio (la infraestructura de Blender ya tuvo incidentes por carga de arañas).

    No depende del orden en que la API devuelve los reportes: avanza por **ventanas de tiempo**
    («actualizados entre desde y desde + ventana», parámetros since y before). Una ventana solo se da
    por terminada cuando su última página viene incompleta; si se llena, la siguiente vez la ventana
    se parte a la mitad. La primera vez empieza `dias_iniciales` atrás.
    """
    import json
    from urllib.parse import urlencode

    cfg = fuente["sensor"]
    ahora = (ahora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    base = cfg["base"].rstrip("/")
    limite = int(cfg.get("por_pagina", 50))
    presupuesto = int(cfg.get("peticiones", 6))
    consulta = {"state": "all", "type": "issues", "limit": limite}
    if cfg.get("etiquetas"):
        consulta["labels"] = ",".join(cfg["etiquetas"])
    inicio = ahora - timedelta(days=int(cfg.get("dias_iniciales", 14)))
    desde = datetime.fromisoformat(estado["desde"]) if estado.get("desde") else inicio
    ventana = timedelta(hours=float(estado.get("ventana_horas") or cfg.get("ventana_horas", 24)))
    vistas = dict(estado.get("huellas", {}))
    registros, revisados, peticiones, ventanas = [], 0, 0, 0

    def iso(t):
        return t.isoformat(timespec="seconds").replace("+00:00", "Z")

    while peticiones < presupuesto and desde < ahora:
        hasta = min(desde + ventana, ahora)
        completa = False
        for pagina in range(1, presupuesto - peticiones + 1):
            url = f"{base}/api/v1/repos/{cfg['repo']}/issues?" + urlencode(
                {**consulta, "since": iso(desde), "before": iso(hasta), "page": pagina})
            lote = _json(obtener(url, {"Accept": "application/json"}))
            peticiones += 1
            lote = lote if isinstance(lote, list) else []
            revisados += len(lote)
            for r in lote:
                if r.get("pull_request") is not None:  # Gitea marca los pull requests con este campo
                    continue
                clave = str(r.get("number") or r.get("id"))
                actualizado = r.get("updated_at") or r.get("created_at")
                if not clave or vistas.get(clave) == actualizado:
                    continue
                vistas[clave] = actualizado
                registros.append({
                    "id": clave, "url": r.get("html_url") or f"{base}/{cfg['repo']}/issues/{clave}",
                    "titulo": (r.get("title") or "").strip()[:200], "fecha": r.get("created_at"),
                    "etiquetas": [e.get("name") for e in r.get("labels") or [] if e.get("name")],
                    "datos": {"estado": r.get("state"), "actualizado": actualizado, "cerrado": r.get("closed_at"),
                              "comentarios": r.get("comments", 0), **sistema_de_reporte(r.get("body"))},
                })
            if len(lote) < limite:
                completa = True
                break
        if not completa:  # se acabó el presupuesto dentro de la ventana: la próxima vez, más chica
            ventana = max(ventana / 2, timedelta(hours=1))
            break
        ventanas += 1
        desde = hasta
    nuevo = dict(estado)
    nuevo.update(desde=desde.isoformat(), ventana_horas=ventana.total_seconds() / 3600,
                 huellas=dict(list(vistas.items())[-VISTOS_MAX:]))
    con_gpu = sum(1 for r in registros if r["datos"].get("gpu_texto"))
    return {"urls": [], "registros": registros,
            "nota": (f"{len(registros)} reportes nuevos o cambiados de {revisados} ({con_gpu} con GPU); "
                     f"{ventanas} ventanas completas, al día hasta {iso(desde)}")}, nuevo


SENSORES = {"sphinx": sensor_sphinx, "gitea_issues": sensor_gitea_issues, "atom": sensor_feed, "rss": sensor_feed, "pagina": sensor_pagina,
            "sitemap": sensor_sitemap, "stackexchange": sensor_stackexchange,
            "discourse": sensor_discourse, "github_releases": sensor_github_releases,
            "json_api": sensor_json_api}
