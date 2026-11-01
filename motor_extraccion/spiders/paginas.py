"""Araña genérica que lanzan los disparadores (g7b_ingesta/vigilar.py).

Guarda la página tal como llegó (zona bronce del lago, vía zyte_a_lago); el embudo filtra después.

    scrapy crawl paginas -a fuente=blender-manual -a urls='["https://docs.blender.org/manual/en/latest/"]' \
        -a seguir=1 -a prefijo=https://docs.blender.org/manual/en/latest/ -a max_paginas=50

Argumentos (todos texto, como los pasa Zyte):
    fuente       id del catálogo (fuentes/catalogo.yml)
    urls         lista JSON de URLs de inicio
    modo         texto_completo | solo_metadatos (con derechos reservados no se guarda el HTML)
    dominios     lista JSON de dominios permitidos
    seguir       "1" para seguir los enlaces que empiezan con prefijo
    prefijo      solo se siguen enlaces que empiezan así
    max_paginas  tope de páginas por trabajo
"""
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy


class PaginasSpider(scrapy.Spider):
    name = "paginas"
    guardar_en_mongo = False  # el crudo va al lago, no a MongoDB (512 MB en la capa gratuita)
    custom_settings = {"DEPTH_LIMIT": 8}

    def __init__(self, fuente="", urls="[]", modo="texto_completo", dominios="[]", seguir="0", prefijo="",
                 max_paginas="200", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fuente = fuente
        self.start_urls = json.loads(urls)
        self.modo = modo
        self.allowed_domains = json.loads(dominios) or sorted({urlparse(u).hostname for u in self.start_urls})
        self.seguir = seguir == "1"
        self.prefijo = prefijo
        self.max_paginas = int(max_paginas)
        self.paginas = 0

    def parse(self, response):
        tipo = response.headers.get("Content-Type", b"").decode("latin-1")
        if "html" not in tipo or self.paginas >= self.max_paginas:
            return
        self.paginas += 1
        base = {
            "fuente": self.fuente,
            "url": response.url,
            "estado_http": response.status,
            "tipo": tipo,
            "ultima_modificacion": response.headers.get("Last-Modified", b"").decode("latin-1") or None,
            "extraido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "titulo": (response.css("title::text").get() or "").strip(),
        }
        if self.modo == "solo_metadatos":
            yield {**base, "descripcion": response.css('meta[name="description"]::attr(content)').get()}
        else:
            yield {**base, "html": response.text}
        if self.seguir:
            for href in response.css("a::attr(href)").getall():
                url = response.urljoin(href).split("#", 1)[0]
                if url.startswith(self.prefijo) and self.paginas < self.max_paginas:
                    yield scrapy.Request(url, callback=self.parse)
