"""Araña documental de sitios; mantiene el nombre de trabajo paginas en Zyte."""
import json
import posixpath
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit, urlunsplit

import scrapy

from ..frontera_documental import Frontera, palabras
from .fragmentos_sphinx import extraer_fragmentos
from ..site import ModeloSite, puntuar_enlaces


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


class PaginasSpider(scrapy.Spider):
    name = "paginas"
    guardar_en_mongo = False
    # La profundidad de Scrapy contaría callbacks sucesivos; el grafo usa su propia distancia.
    custom_settings = {"DEPTH_LIMIT": 0}

    def __init__(self, estrategia="foco", temas='["render", "memory", "memoria", "sampling", "muestras"]',
                 profundidad="8", seguir="0", programa="", version="", fuente="", urls="[]",
                 modo="texto_completo", dominios="[]", prefijo="", max_paginas="200", tipo_fuente="",
                 prefijos_puente="[]", **kwargs):
        super().__init__(**kwargs)
        self.fuente, self.modo, self.prefijo = fuente, modo, prefijo
        self.start_urls = json.loads(urls)
        self.allowed_domains = json.loads(dominios) or sorted({urlsplit(u).hostname for u in self.start_urls})
        self.max_paginas = int(max_paginas)
        self.modelo = ModeloSite()
        self.foro = tipo_fuente in {"foro", "comunidad"}
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
        self.dominios_permitidos = {d.lower() for d in self.allowed_domains}
        self.limite = None
        if self.prefijo:
            prefijo = direccion(self.prefijo)
            if not prefijo or urlsplit(prefijo).query:
                raise ValueError("prefijo debe ser una URL HTTP(S) sin consulta")
            self.limite = urlsplit(prefijo)
        puentes = json.loads(prefijos_puente)
        if not isinstance(puentes, list) or not all(isinstance(x, str) for x in puentes):
            raise ValueError("prefijos_puente debe ser una lista de URLs")
        self.puentes = []
        for raw in puentes:
            canonica = direccion(raw)
            if not self.limite or not canonica:
                raise ValueError("El túnel requiere un prefijo principal y URLs válidas")
            parte = urlsplit(canonica)
            if parte.query or parte.hostname not in self.dominios_permitidos or parte.scheme != "https":
                raise ValueError("Prefijo de túnel fuera de los dominios configurados")
            self.puentes.append(parte)
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
        if partes.hostname not in self.dominios_permitidos:
            return None
        return url if not self.limite or self.bajo(partes, self.limite) else None

    @staticmethod
    def bajo(partes, prefijo):
        if (partes.scheme, partes.netloc) != (prefijo.scheme, prefijo.netloc):
            return False
        base = posixpath.normpath(unquote(prefijo.path)).rstrip("/")
        ruta = posixpath.normpath(unquote(partes.path).replace("\\", "/"))
        return ruta == base or ruta.startswith(base + "/")

    def destino(self, url, saltos):
        if self.en_alcance(url):
            return 0
        if saltos < 2 and any(self.bajo(urlsplit(url), prefijo) for prefijo in self.puentes):
            return saltos + 1
        return None

    def resolver(self, response, href):
        try:
            return direccion(response.urljoin(href))
        except ValueError:
            return None

    def proxima(self):
        candidato = self.frontera.siguiente()
        if candidato:
            self.crawler.stats.inc_value("g7b/documental/intentos")
            # Una única petición activa. La frontera ya filtró URL, alcance y duplicados.
            yield scrapy.Request(
                candidato.url, callback=self.parse, errback=self.fallo, dont_filter=True,
                meta={"nivel_documental": candidato.profundidad, "prioridad_documental": candidato.puntuacion,
                      "saltos_fuera": candidato.saltos_fuera,
                      "dont_redirect": True, "dont_retry": True, "handle_httpstatus_all": True})

    def start_requests(self):  # Scrapy 2.11–2.12
        yield from self.proxima()

    async def start(self):  # Scrapy 2.13+
        for peticion in self.proxima():
            yield peticion

    def fallo(self, failure):
        self.crawler.stats.inc_value("g7b/documental/fallos")
        yield from self.proxima()

    def parse(self, response):
        nivel = response.meta["nivel_documental"]
        if response.status in {301, 302, 303, 307, 308}:
            destino = response.headers.get("Location")
            if destino:
                url = self.resolver(response, destino.decode("latin-1"))
                if url:
                    k = self.destino(url, response.meta["saltos_fuera"])
                    # Una redirección no puede abrir un túnel sin ancla evaluada.
                    if k == 0 or (k is not None and response.meta["saltos_fuera"] > 0):
                        self.frontera.ofrecer(url, nivel, response.meta["prioridad_documental"], saltos_fuera=k)
            self.crawler.stats.inc_value("g7b/documental/redirecciones")
        elif 200 <= response.status < 300 and "html" in response.headers.get(
                "Content-Type", b"").decode("latin-1").lower():
            yield from self.procesar_html(response, nivel)
        else:
            self.crawler.stats.inc_value("g7b/documental/http_o_tipo_descartado")
        yield from self.proxima()

    def procesar_html(self, response, nivel):
        self.crawler.stats.inc_value("g7b/documental/html")
        item = {"fuente": self.fuente, "url": response.url, "estado_http": response.status,
                "tipo": response.headers.get("Content-Type", b"").decode("latin-1"),
                "ultima_modificacion": response.headers.get("Last-Modified", b"").decode("latin-1") or None,
                "extraido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "programa": self.programa, "version": self.version,
                "titulo": (response.css("title::text").get() or "").strip()}
        if self.modo == "solo_metadatos":
            item["descripcion"] = response.css('meta[name="description"]::attr(content)').get()
        else:
            item["html"] = response.text
            contenedor = response.css("main, [role=main]")
            if not contenedor:
                articulos = response.css("article")
                contenedor = articulos if len(articulos) == 1 else response.css("body")
            item["fragmentos"] = extraer_fragmentos(
                contenedor[0], response, self.fuente, self.programa, self.version,
                item["titulo"]) if contenedor else []
            self.modelo.anotar(item, self.foro)
            for estado, n in item["documental"]["conteos"].items():
                self.crawler.stats.inc_value("g7b/documental/" + estado, n)
        yield item
        if self.explorar and nivel < self.profundidad_max:
            raiz = response.css("main, [role=main]") or response.css("article") or response.css("body")
            enlaces, destinos = [], {}
            for enlace in raiz.xpath(".//a[@href][not(ancestor::nav or ancestor::footer or ancestor::header)]"):
                url = self.resolver(response, enlace.attrib["href"])
                if not url or "headerlink" in (enlace.attrib.get("class") or "").split():
                    continue
                k = self.destino(url, response.meta["saltos_fuera"])
                if k is None or url in self.frontera.visitadas:
                    continue
                ancla = enlace.xpath("string(.)").get() or ""
                bloque = enlace.xpath("string(ancestor::*[self::p or self::li or self::dt][1])").get() or ""
                encabezado = enlace.xpath("string(preceding::*[self::h1 or self::h2 or self::h3][1])").get() or ""
                enlaces.append((url, ancla, encabezado + " " + bloque[:400]))
                destinos[url] = k
            for url, nota, puente in puntuar_enlaces(enlaces, self.temas, self.modelo.rendimiento):
                k = destinos[url]
                if k and nota < 0.28:
                    continue
                prioridad = nota * 0.85 ** nivel * 0.5 ** k
                self.frontera.ofrecer(url, nivel + 1, prioridad, puente, k)
