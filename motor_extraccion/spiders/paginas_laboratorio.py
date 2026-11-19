"""Variante experimental, de ejecución manual, de la araña documental paginas."""
import json
import posixpath
from urllib.parse import unquote, urlsplit, urlunsplit

import scrapy

from ..frontera_documental import Frontera, calificar, palabras
from .fragmentos_sphinx import extraer_fragmentos
from .paginas import PaginasSpider


def direccion(url):
    """Ignora fragmentos; conserva los parámetros, idioma y versión de la ruta."""
    try:
        partes = urlsplit(url)
        if partes.scheme not in {"http", "https"} or not partes.hostname or partes.username is not None:
            return None
        puerto = partes.port
    except ValueError:
        return None
    host = partes.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if puerto is not None and (partes.scheme, puerto) not in {("http", 80), ("https", 443)}:
        host += f":{puerto}"
    return urlunsplit((partes.scheme, host, partes.path or "/", partes.query, ""))


class PaginasLaboratorioSpider(PaginasSpider):
    name = "paginas_laboratorio"
    # La profundidad de Scrapy contaría callbacks sucesivos; el grafo usa su propia distancia.
    custom_settings = {**PaginasSpider.custom_settings, "DEPTH_LIMIT": 0}

    def __init__(self, estrategia="foco_puentes", temas='["render", "memoria"]',
                 profundidad="8", seguir="1", programa="", version="", **kwargs):
        super().__init__(seguir="0", **kwargs)  # Se reutiliza la salida de paginas, no su cola.
        if self.modo not in {"texto_completo", "solo_metadatos"} or seguir not in {"0", "1"}:
            raise ValueError("modo o seguir inválido")
        self.explorar = seguir == "1"
        self.programa, self.version = programa, version
        self.profundidad_max = int(profundidad)
        terminos = json.loads(temas)
        if not isinstance(terminos, list) or not all(isinstance(t, str) for t in terminos):
            raise ValueError("temas debe ser una lista JSON de cadenas")
        self.temas = palabras(" ".join(terminos))
        if self.profundidad_max < 0 or not self.temas:
            raise ValueError("Se requiere profundidad no negativa y al menos un término")
        self.frontera = Frontera(estrategia, self.max_paginas)
        self.dominios_lab = {d.lower() for d in self.allowed_domains}
        self.limite = None
        if self.prefijo:
            prefijo = direccion(self.prefijo)
            if not prefijo or urlsplit(prefijo).query:
                raise ValueError("prefijo debe ser una URL HTTP(S) sin consulta")
            self.limite = urlsplit(prefijo)
        if not self.start_urls:
            raise ValueError("Se requiere al menos una URL de inicio")
        for semilla in self.start_urls:
            url = self.en_alcance(semilla)
            if not url:
                raise ValueError(f"Semilla fuera del alcance: {semilla}")
            self.frontera.ofrecer(url)

    def en_alcance(self, url):
        url = direccion(url)
        if not url:
            return None
        partes = urlsplit(url)
        if partes.hostname not in self.dominios_lab:
            return None
        if self.limite:
            if (partes.scheme, partes.netloc) != (self.limite.scheme, self.limite.netloc):
                return None
            base = posixpath.normpath(unquote(self.limite.path)).rstrip("/")
            ruta = posixpath.normpath(unquote(partes.path).replace("\\", "/"))
            if ruta != base and not ruta.startswith(base + "/"):
                return None
        return url

    def resolver(self, response, href):
        try:
            return self.en_alcance(response.urljoin(href))
        except ValueError:  # Por ejemplo, un enlace malformado dentro de una página válida.
            return None

    def proxima(self):
        candidato = self.frontera.siguiente()
        if candidato:
            self.crawler.stats.inc_value("g7b/lab/intentos")
            # Una única petición activa. La frontera ya filtró URL, alcance y duplicados.
            yield scrapy.Request(
                candidato.url, callback=self.parse, errback=self.fallo, dont_filter=True,
                meta={"lab_profundidad": candidato.profundidad, "lab_puntuacion": candidato.puntuacion,
                      "dont_redirect": True, "dont_retry": True, "handle_httpstatus_all": True})

    def start_requests(self):  # Scrapy 2.11–2.12
        yield from self.proxima()

    async def start(self):  # Scrapy 2.13+
        for peticion in self.proxima():
            yield peticion

    def fallo(self, failure):
        self.crawler.stats.inc_value("g7b/lab/fallos")
        yield from self.proxima()

    def parse(self, response):
        nivel = response.meta["lab_profundidad"]
        if response.status in {301, 302, 303, 307, 308}:
            destino = response.headers.get("Location")
            if destino:
                url = self.resolver(response, destino.decode("latin-1"))
                if url:
                    self.frontera.ofrecer(url, nivel, response.meta["lab_puntuacion"])
            self.crawler.stats.inc_value("g7b/lab/redirecciones")
        elif 200 <= response.status < 300 and "html" in response.headers.get(
                "Content-Type", b"").decode("latin-1").lower():
            yield from self.procesar_html(response, nivel)
        else:
            self.crawler.stats.inc_value("g7b/lab/http_o_tipo_descartado")
        yield from self.proxima()

    def procesar_html(self, response, nivel):
        self.crawler.stats.inc_value("g7b/lab/html")
        for item in super().parse(response):
            if self.modo == "texto_completo":
                contenedor = response.css("main, [role=main]")
                if not contenedor:
                    articulos = response.css("article")
                    contenedor = articulos if len(articulos) == 1 else response.css("body")
                item["fragmentos"] = extraer_fragmentos(
                    contenedor[0], response, self.fuente, self.programa, self.version,
                    item["titulo"]) if contenedor else []
                self.crawler.stats.inc_value("g7b/lab/fragmentos", len(item["fragmentos"]))
            yield item
        if self.explorar and nivel < self.profundidad_max:
            for enlace in response.css("a[href]"):
                url = self.resolver(response, enlace.attrib["href"])
                if url:
                    ancla = enlace.xpath("string(.)").get() or ""
                    encabezado = enlace.xpath(
                        "string(preceding::*[self::h1 or self::h2 or self::h3][1])").get() or ""
                    nota, puente = calificar(url, ancla, encabezado, self.temas, nivel + 1)
                    self.frontera.ofrecer(url, nivel + 1, nota, puente)
