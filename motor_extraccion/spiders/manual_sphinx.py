"""Araña estructurada para manuales hechos con Sphinx (Blender, Godot y otros), en varias versiones.

Recorre cada sección completa (todas sus páginas, no solo el índice) y por página guarda, en orden:
títulos, párrafos, listas, cada propiedad con su nombre y descripción (<dt>/<dd>) y los bloques de
código, más las llamadas bpy.* encontradas. No escribe en MongoDB: lo crudo va al lago (zyte_a_lago)
y el embudo filtra después.

    scrapy crawl manual_sphinx -a fuente=blender-manual -a base=https://docs.blender.org/manual/en/ \
        -a versiones='["5.2"]' -a secciones='["render/cycles/index.html"]' -a max_paginas=50

Las páginas sin contenido se descartan aquí mismo y se cuentan en las estadísticas del trabajo
(g7b/descartadas_sin_contenido), para que se vea cuántas fueron.

Qué recorre (modo «inventario», el de siempre desde el 16 de noviembre de 2026): por cada versión
lee el objects.inv del manual, la lista oficial de sus páginas (motor_extraccion/inventario_sphinx.py),
y pide solo las que caen en las secciones, cada una una vez y en orden. No sigue enlaces, así que
no se sale del manual ni repite páginas. Si una versión no publica objects.inv, esa versión se
recorre como antes, siguiendo los enlaces de cada sección (modo «enlaces»).

Una página con el mismo contenido que otra ya extraída de la misma versión (Sphinx publica algunas
en dos rutas) sale como registro corto con «duplicado_de», sin repetir el texto. Al cerrar, el
trabajo deja en sus estadísticas cuántas páginas esperaba y cuántas extrajo por versión
(g7b/esperadas/<versión>, g7b/extraidas/<versión>, g7b/repetidas/<versión>, g7b/fallidas/<versión>).
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy
from scrapy.exceptions import CloseSpider

from ..inventario_sphinx import filtrar, leer
from .fragmentos_sphinx import extraer_fragmentos

_ESPACIOS = re.compile(r"\s+")
_BPY = re.compile(r"\bbpy\.[A-Za-z_][A-Za-z0-9_.]*")
_CONTENEDORES = ("article[role='main']", "div[role='main']", "div.body", "div.document")
_BLOQUES = (".//h2 | .//h3 | .//p[not(ancestor::li or ancestor::dd or ancestor::table or ancestor::dt)]"
            " | .//li[not(ancestor::dd) and not(ancestor::nav)] | .//dl/dt | .//dl/dd | .//pre")


def limpio(texto):
    return _ESPACIOS.sub(" ", (texto or "").replace("¶", "").replace("\uf0c1", "")).strip()


def texto_de(selector, sin_pre=True):
    partes = selector.xpath(".//text()[not(ancestor::pre)]" if sin_pre else ".//text()").getall()
    return limpio(" ".join(partes))


class ManualSphinxSpider(scrapy.Spider):
    name = "manual_sphinx"
    guardar_en_mongo = False

    # Valores por omisión; las subclases (como blender_docs) los cambian.
    fuente_por_omision = ""
    programa = ""
    base = ""
    versiones = []
    secciones = []

    def __init__(self, fuente=None, base=None, versiones=None, secciones=None, max_paginas="3000",
                 anclas_objetivo=None, modo="inventario", max_por_version="0",
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fuente = fuente or self.fuente_por_omision
        self.base = (base or self.base).rstrip("/") + "/"
        self.versiones = json.loads(versiones) if versiones else list(self.versiones)
        self.secciones = json.loads(secciones) if secciones else list(self.secciones)
        self.max_paginas = int(max_paginas)
        self.paginas = 0
        self.anclas_objetivo = json.loads(anclas_objetivo) if anclas_objetivo else []
        if not isinstance(self.anclas_objetivo, list) or any(
                not isinstance(a, str) or not a for a in self.anclas_objetivo):
            raise ValueError("anclas_objetivo debe ser una lista JSON de anclas no vacias")
        self.allowed_domains = [urlparse(self.base).hostname]
        if modo not in ("inventario", "enlaces"):
            raise ValueError("modo debe ser «inventario» o «enlaces»")
        self.modo = modo
        self.max_por_version = int(max_por_version)  # 0: sin tope por versión (solo el global)
        self.esperadas, self.extraidas = {}, {}
        self._contenidos = {}  # (versión, hash_contenido) -> primera url con ese contenido

    async def start(self):  # Scrapy 2.13 o más nuevo
        for peticion in self.start_requests():
            yield peticion

    def start_requests(self):  # Scrapy 2.11 (el stack de Zyte)
        for orden, version in enumerate(self.versiones):
            if self.modo == "inventario":
                # Prioridad decreciente: las versiones se recorren en el orden pedido, no mezcladas.
                yield scrapy.Request(f"{self.base}{version}/objects.inv", callback=self.parse_inventario,
                                     errback=self.sin_inventario, priority=100 - orden,
                                     cb_kwargs={"version": version}, meta={"version": version})
            else:
                yield from self.por_enlaces(version)

    def por_enlaces(self, version):
        raiz = f"{self.base}{version}/"
        for seccion in self.secciones:
            carpeta = seccion.rsplit("/", 1)[0] + "/" if "/" in seccion else ""
            yield scrapy.Request(raiz + seccion, callback=self.parse_pagina, cb_kwargs={
                "version": version, "seccion": carpeta.rstrip("/") or seccion, "prefijo": raiz + carpeta})

    def _estadistica(self, clave, valor=1, fijar=False):
        if getattr(self, "crawler", None):
            stats = self.crawler.stats
            stats.set_value(clave, valor) if fijar else stats.inc_value(clave, valor)

    def parse_inventario(self, response, version):
        try:
            inventario = leer(response.body)
        except Exception as error:  # ValueError o zlib.error: archivo que no es un inventario válido
            self.logger.warning("objects.inv de %s ilegible (%s): se recorre por enlaces", version, error)
            yield from self.por_enlaces(version)
            return
        paginas = filtrar(inventario["paginas"], self.secciones)
        if self.max_por_version:
            paginas = paginas[:self.max_por_version]
        self.esperadas[version] = len(paginas)
        self._estadistica(f"g7b/esperadas/{version}", len(paginas), fijar=True)
        self._estadistica(f"g7b/inventario/{version}", inventario["huella"][:16], fijar=True)
        raiz = f"{self.base}{version}/"
        for orden, (pagina, seccion) in enumerate(paginas):
            yield scrapy.Request(raiz + pagina, callback=self.parse_pagina, errback=self.pagina_fallida,
                                 priority=-orden, meta={"version": version},
                                 cb_kwargs={"version": version, "seccion": seccion, "prefijo": None})

    def sin_inventario(self, failure):
        version = failure.request.meta["version"]
        self.logger.warning("sin objects.inv para %s (%s): se recorre por enlaces", version, failure.value)
        self._estadistica("g7b/sin_inventario")
        yield from self.por_enlaces(version)

    def pagina_fallida(self, failure):
        self._estadistica(f"g7b/fallidas/{failure.request.meta.get('version', '?')}")

    def closed(self, reason):
        for version, esperadas in self.esperadas.items():
            extraidas = self.extraidas.get(version, 0)
            self.logger.info("cobertura %s: %s de %s páginas del inventario (%s)", version, extraidas, esperadas,
                             reason)

    def parse_pagina(self, response, version, seccion, prefijo):
        if "html" not in response.headers.get("Content-Type", b"").decode("latin-1"):
            return
        if self.paginas >= self.max_paginas:
            # Cerrar el trabajo y descartar la cola: sin esto, al llegar al tope seguía descargando
            # lo encolado (una prueba con max_paginas=20 bajó 370 páginas).
            raise CloseSpider("max_paginas")
        self.paginas += 1
        self.extraidas[version] = self.extraidas.get(version, 0) + 1
        self._estadistica(f"g7b/extraidas/{version}")
        documento = self.extraer(response, version, seccion)
        if documento:
            # Solo el texto: hash_contenido incluye los fragmentos, que llevan la URL de cada apartado.
            clave = (version, hashlib.sha256(documento["contenido"].encode("utf-8")).hexdigest())
            primera = self._contenidos.setdefault(clave, documento["url"])
            if primera != documento["url"]:
                # La misma página publicada en otra ruta: se anota la ruta, sin repetir el texto.
                self._estadistica(f"g7b/repetidas/{version}")
                documento = {k: documento[k] for k in (
                    "schema_version", "extractor_version", "doc_id", "fuente", "url", "programa", "version",
                    "seccion", "titulo", "hash_contenido", "canonica", "ruta", "extraido_en")}
                documento["duplicado_de"] = primera
            yield documento
        else:
            self._estadistica("g7b/descartadas_sin_contenido")
        if prefijo is None:  # modo inventario: la lista ya está completa, no se siguen enlaces
            return
        # Toda la sección: cualquier enlace dentro de su carpeta, a cualquier profundidad.
        for href in response.css("a::attr(href)").getall():
            url = response.urljoin(href).split("#", 1)[0]
            if url.startswith(prefijo) and url.endswith(".html") and self.paginas < self.max_paginas:
                yield scrapy.Request(url, callback=self.parse_pagina,
                                     cb_kwargs={"version": version, "seccion": seccion, "prefijo": prefijo})

    def extraer(self, response, version, seccion):
        contenedor = None
        for css in _CONTENEDORES:
            encontrado = response.css(css)
            if encontrado:
                contenedor = encontrado[0]
                break
        if contenedor is None:
            return None
        titulo = limpio(" ".join(contenedor.css("h1 ::text").getall())) or \
            limpio((response.css("title::text").get() or "").split("-")[0])
        fragmentos = extraer_fragmentos(contenedor, response, self.fuente, self.programa, version, titulo)
        if self.anclas_objetivo:
            fragmentos = [f for f in fragmentos if f["ancla"] in self.anclas_objetivo]
            if not fragmentos:
                if getattr(self, "crawler", None):
                    self.crawler.stats.inc_value("g7b/sin_anclas_objetivo")
                return None
        lineas, jerarquia, propiedades, codigos = [], [], [], []
        nombre_pendiente = None
        for nodo in contenedor.xpath(_BLOQUES):
            etiqueta = nodo.root.tag
            if etiqueta in ("h2", "h3"):
                texto = texto_de(nodo)
                if texto:
                    jerarquia.append(texto)
                    lineas.append(("## " if etiqueta == "h2" else "### ") + texto)
            elif etiqueta == "pre":
                codigo = "".join(nodo.xpath(".//text()").getall()).strip("\n")
                if codigo.strip() and codigo not in codigos:
                    codigos.append(codigo)
                    lineas.append(f"```\n{codigo}\n```")
            elif etiqueta == "dt":
                nombre_pendiente = texto_de(nodo)
            elif etiqueta == "dd":
                descripcion = texto_de(nodo)
                if nombre_pendiente:
                    propiedades.append({"nombre": nombre_pendiente, "descripcion": descripcion})
                    lineas.append(f"**{nombre_pendiente}**: {descripcion}")
                    nombre_pendiente = None
                elif descripcion:
                    lineas.append(descripcion)
            elif etiqueta == "li":
                texto = texto_de(nodo)
                if texto:
                    lineas.append("- " + texto)
            else:  # p
                texto = texto_de(nodo)
                if texto:
                    lineas.append(texto)
        contenido = "\n\n".join(lineas).strip()
        prosa = "\n".join(l for l in lineas if not l.startswith("```"))
        if not prosa.strip() and not fragmentos:
            return None
        url = response.url.split("#", 1)[0]
        raiz = f"{self.base}{version}/"
        return {
            "schema_version": 2,
            "extractor_version": "manual_sphinx/2",
            "fragmentos": fragmentos,
            "doc_id": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "fuente": self.fuente,
            "url": url,
            "programa": self.programa,
            "version": version,
            "seccion": seccion,
            # Ruta dentro de la versión y URL canónica que declara la página (en Blender, la de
            # «latest»): juntan la misma página de distintas versiones sin compararlas por texto.
            "ruta": url[len(raiz):] if url.startswith(raiz) else url,
            "canonica": response.css("link[rel='canonical']::attr(href)").get(),
            "titulo": titulo,
            "jerarquia": jerarquia,
            "contenido": contenido,
            "propiedades": propiedades,
            "bloques_codigo": codigos,
            "operadores_bpy": sorted(set(_BPY.findall(contenido))),
            "conteo_palabras": len(prosa.split()),
            "hash_contenido": hashlib.sha256(json.dumps(
                {"contenido": contenido, "fragmentos": fragmentos, "schema_version": 2},
                ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
            "extraido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


