"""Araña estructurada para manuales hechos con Sphinx (Blender, Godot y otros), en varias versiones.

Recorre cada sección completa (todas sus páginas, no solo el índice) y por página guarda, en orden:
títulos, párrafos, listas, cada propiedad con su nombre y descripción (<dt>/<dd>) y los bloques de
código, más las llamadas bpy.* encontradas. No escribe en MongoDB: lo crudo va al lago (zyte_a_lago)
y el embudo filtra después.

    scrapy crawl manual_sphinx -a fuente=blender-manual -a base=https://docs.blender.org/manual/en/ \
        -a versiones='["5.2"]' -a secciones='["render/cycles/index.html"]' -a max_paginas=50

Las páginas sin contenido se descartan aquí mismo y se cuentan en las estadísticas del trabajo
(g7b/descartadas_sin_contenido), para que se vea cuántas fueron.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy

_ESPACIOS = re.compile(r"\s+")
_BPY = re.compile(r"\bbpy\.[A-Za-z_][A-Za-z0-9_.]*")
_CONTENEDORES = ("article[role='main']", "div[role='main']", "div.body", "div.document")
_BLOQUES = (".//h2 | .//h3 | .//p[not(ancestor::li or ancestor::dd or ancestor::table or ancestor::dt)]"
            " | .//li[not(ancestor::dd) and not(ancestor::nav)] | .//dl/dt | .//dl/dd | .//pre")


def limpio(texto):
    return _ESPACIOS.sub(" ", (texto or "").replace("¶", "")).strip()


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
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fuente = fuente or self.fuente_por_omision
        self.base = (base or self.base).rstrip("/") + "/"
        self.versiones = json.loads(versiones) if versiones else list(self.versiones)
        self.secciones = json.loads(secciones) if secciones else list(self.secciones)
        self.max_paginas = int(max_paginas)
        self.paginas = 0
        self.allowed_domains = [urlparse(self.base).hostname]

    async def start(self):  # Scrapy 2.13 o más nuevo
        for peticion in self.start_requests():
            yield peticion

    def start_requests(self):  # Scrapy 2.11 (el stack de Zyte)
        for version in self.versiones:
            raiz = f"{self.base}{version}/"
            for seccion in self.secciones:
                carpeta = seccion.rsplit("/", 1)[0] + "/" if "/" in seccion else ""
                yield scrapy.Request(raiz + seccion, callback=self.parse_pagina, cb_kwargs={
                    "version": version, "seccion": carpeta.rstrip("/") or seccion, "prefijo": raiz + carpeta})

    def parse_pagina(self, response, version, seccion, prefijo):
        if "html" not in response.headers.get("Content-Type", b"").decode("latin-1"):
            return
        if self.paginas >= self.max_paginas:
            return
        self.paginas += 1
        documento = self.extraer(response, version, seccion)
        if documento:
            yield documento
        elif getattr(self, "crawler", None):
            self.crawler.stats.inc_value("g7b/descartadas_sin_contenido")
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
            limpio((response.css("title::text").get() or "").split("—")[0])
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
        if not prosa.strip():
            return None
        url = response.url.split("#", 1)[0]
        return {
            "doc_id": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "fuente": self.fuente,
            "url": url,
            "programa": self.programa,
            "version": version,
            "seccion": seccion,
            "titulo": titulo,
            "jerarquia": jerarquia,
            "contenido": contenido,
            "propiedades": propiedades,
            "bloques_codigo": codigos,
            "operadores_bpy": sorted(set(_BPY.findall(contenido))),
            "conteo_palabras": len(prosa.split()),
            "hash_contenido": hashlib.sha256(contenido.encode("utf-8")).hexdigest(),
            "extraido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
