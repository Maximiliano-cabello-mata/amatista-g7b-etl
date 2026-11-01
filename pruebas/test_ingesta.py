"""Pruebas del catálogo, los sensores, el embudo y la araña genérica. Sin red ni nube."""
import json

import pytest

from g7b_ingesta import catalogo as cat
from g7b_ingesta import texto as tx
from g7b_ingesta.embudo import ACEPTADO, RECHAZADO, REVISION, Indice, evaluar
from g7b_ingesta.red import Respuesta
from g7b_ingesta.sensores import sensor_feed, sensor_pagina, sensor_sitemap, sensor_stackexchange

TAXONOMIA = cat.cargar_taxonomia()

FUENTE_FORO = {"id": "foro", "activa": True, "licencia_verificada": True, "licencia": "CC-BY-SA-4.0",
               "modo": "texto_completo", "preguntas": ["P1", "P6"], "dominios": ["blender.stackexchange.com"]}

TEXTO_VALIOSO = (
    "In Blender 4.2 the viewport is slow on my Intel UHD 620 laptop with 8 GB of RAM. "
    "With Simplify enabled and subdivision levels set to 1 the viewport goes from 9 fps to 24 fps. "
    "Rendering with Cycles at 64 samples took 3 min, while EEVEE took 12 s for the same frame. "
    "The performance is much better compared to the default settings, and memory usage dropped to 2.1 GB. "
    "If you also use the denoiser you can lower the samples further without visible noise in the render."
)


def doc(texto, url="https://blender.stackexchange.com/q/1", titulo="Slow viewport", **metadatos):
    return {"url": url, "titulo": titulo, "texto": texto, "metadatos": metadatos}


# ---------------------------------------------------------------- catálogo

def test_catalogo_real_es_valido():
    catalogo = cat.cargar()
    ids = [f["id"] for f in cat.vigilables(catalogo)]
    assert "arxiv-cs-gr" in ids and "blender-stackexchange" in ids
    # Nada con licencia por confirmar se vigila.
    assert all(f["licencia"] != "por_confirmar" for f in cat.vigilables(catalogo))


def test_catalogo_rechaza_licencia_mal_marcada():
    malo = {"fuentes": [{**FUENTE_FORO, "nombre": "x", "tipo": "foro", "licencia": "por_confirmar",
                         "sensor": {"tipo": "atom", "url": "u"}, "extractor": "directo", "frecuencia_horas": 1}]}
    assert any("por confirmar" in e for e in cat.validar(malo))


def test_catalogo_impide_texto_completo_con_derechos_reservados():
    malo = {"fuentes": [{**FUENTE_FORO, "nombre": "x", "tipo": "foro", "licencia": "derechos_reservados",
                         "sensor": {"tipo": "atom", "url": "u"}, "extractor": "directo", "frecuencia_horas": 1}]}
    assert any("derechos reservados" in e for e in cat.validar(malo))


# ---------------------------------------------------------------- embudo

def test_acepta_texto_especifico_y_relevante():
    r = evaluar(doc(TEXTO_VALIOSO), FUENTE_FORO, TAXONOMIA, Indice())
    assert r.estado == ACEPTADO, r.motivos
    assert "P1" in r.preguntas
    assert {"medida", "hardware", "ajuste"} <= set(r.puntajes["senales"])


def test_rechaza_fuente_sin_licencia_confirmada():
    r = evaluar(doc(TEXTO_VALIOSO), {**FUENTE_FORO, "licencia_verificada": False}, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "entrada")


def test_rechaza_dominio_ajeno():
    r = evaluar(doc(TEXTO_VALIOSO, url="https://otro.com/x"), FUENTE_FORO, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "entrada")


def test_rechaza_texto_corto():
    r = evaluar(doc("Blender is slow, help."), FUENTE_FORO, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "calidad")


def test_rechaza_menus_repetidos():
    menu = "\n".join(["Home", "Docs", "Download", "Community", "About"] * 6) + "\n" + TEXTO_VALIOSO
    r = evaluar(doc(menu), FUENTE_FORO, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "calidad")


def test_rechaza_duplicado_exacto_y_casi_duplicado():
    indice = Indice()
    primero = evaluar(doc(TEXTO_VALIOSO), FUENTE_FORO, TAXONOMIA, indice)
    indice.agregar(primero.huella, primero.simhash)
    exacto = evaluar(doc(TEXTO_VALIOSO), FUENTE_FORO, TAXONOMIA, indice)
    assert (exacto.estado, exacto.etapa) == (RECHAZADO, "duplicados")
    casi = evaluar(doc(TEXTO_VALIOSO + " Thanks!"), FUENTE_FORO, TAXONOMIA, indice)
    assert (casi.estado, casi.etapa) == (RECHAZADO, "duplicados")


def test_rechaza_lo_que_no_responde_ninguna_pregunta():
    receta = ("Mix the flour with two eggs and a cup of milk, then let the dough rest for an hour before "
              "baking it in the oven. Serve warm with butter and honey, or with fresh fruit on top. "
              "This is my grandmother's recipe and the family loves it on Sunday mornings with coffee.")
    r = evaluar(doc(receta, titulo="Pan de la abuela"), FUENTE_FORO, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "relevancia")


def test_rechaza_lo_generico():
    generico = ("Performance matters a lot when you work with this program. Optimization is important and "
                "a slow viewport is annoying. You should always try to optimize your scenes and think about "
                "performance, because a fast workflow is a happy workflow. Performance is the key to success "
                "and everybody wants better performance in the end, so remember to optimize everything.")
    r = evaluar(doc(generico), FUENTE_FORO, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "valor")


def test_version_vieja_va_a_revision():
    viejo = TEXTO_VALIOSO.replace("Blender 4.2", "Blender 2.79")
    r = evaluar(doc(viejo), FUENTE_FORO, TAXONOMIA, Indice())
    assert r.estado == REVISION and any("2.80" in m for m in r.motivos)


def test_votos_del_foro_suman_valor():
    sin = evaluar(doc(TEXTO_VALIOSO), FUENTE_FORO, TAXONOMIA, Indice())
    con = evaluar(doc(TEXTO_VALIOSO, puntaje_foro=15, respuesta_aceptada=True), FUENTE_FORO, TAXONOMIA, Indice())
    assert con.puntajes["valor"] == pytest.approx(sin.puntajes["valor"] + 1.5 + 1.0)


def test_solo_metadatos_no_admite_texto_largo():
    fuente = {**FUENTE_FORO, "modo": "solo_metadatos"}
    r = evaluar(doc(TEXTO_VALIOSO * 5), fuente, TAXONOMIA, Indice())
    assert (r.estado, r.etapa) == (RECHAZADO, "entrada")


def test_texto_utilidades():
    assert tx.idioma("El modificador de la malla se aplica con el botón de la barra") == "es"
    assert tx.versiones_blender("Blender 2.79 and blender 4.2 LTS") == [(2, 79), (4, 2)]
    assert tx.distancia_hamming(tx.simhash(TEXTO_VALIOSO), tx.simhash(TEXTO_VALIOSO + " ok")) <= 3


# ---------------------------------------------------------------- sensores

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2611.00001v1</id><title>Fast LOD for meshes</title>
    <link href="http://arxiv.org/abs/2611.00001v1"/><summary>We present a level of detail method.</summary>
    <published>2026-10-30T00:00:00Z</published><author><name>Ana Pérez</name></author></entry>
  <entry><id>http://arxiv.org/abs/2611.00002v1</id><title>Neural denoising</title>
    <link href="http://arxiv.org/abs/2611.00002v1"/><summary>A denoising approach.</summary></entry>
</feed>""".encode("utf-8")


def test_sensor_feed_solo_lo_nuevo():
    fuente = {"sensor": {"tipo": "atom", "url": "https://export.arxiv.org/api/query"}}
    salida, estado = sensor_feed(fuente, {}, lambda u, c: Respuesta(200, {"etag": "abc"}, ATOM))
    assert [r["titulo"] for r in salida["registros"]] == ["Fast LOD for meshes", "Neural denoising"]
    assert salida["registros"][0]["autores"] == ["Ana Pérez"] and estado["etag"] == "abc"
    otra, _ = sensor_feed(fuente, estado, lambda u, c: Respuesta(200, {}, ATOM))
    assert otra["registros"] == []
    nada, _ = sensor_feed(fuente, estado, lambda u, c: Respuesta(304))
    assert nada["nota"].startswith("sin cambios")


def test_sensor_pagina_detecta_cambio():
    fuente = {"sensor": {"tipo": "pagina", "url": "https://docs.blender.org/manual/en/latest/"}}
    primera, estado = sensor_pagina(fuente, {}, lambda u, c: Respuesta(200, {}, b"<html>v1</html>"))
    igual, estado = sensor_pagina(fuente, estado, lambda u, c: Respuesta(200, {}, b"<html>v1</html>"))
    cambio, _ = sensor_pagina(fuente, estado, lambda u, c: Respuesta(200, {}, b"<html>v2</html>"))
    assert primera["urls"] and not igual["urls"] and cambio["urls"]


def test_sensor_sitemap():
    def mapa(fecha_b):
        return (f'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://d.org/a</loc><lastmod>2026-10-01</lastmod></url>
          <url><loc>https://d.org/b</loc><lastmod>{fecha_b}</lastmod></url></urlset>''').encode()

    fuente = {"sensor": {"tipo": "sitemap", "url": "https://d.org/sitemap.xml"}}
    s1, estado = sensor_sitemap(fuente, {}, lambda u, c: Respuesta(200, {}, mapa("2026-10-01")))
    s2, _ = sensor_sitemap(fuente, estado, lambda u, c: Respuesta(200, {}, mapa("2026-10-20")))
    assert s1["urls"] == ["https://d.org/a", "https://d.org/b"] and s2["urls"] == ["https://d.org/b"]


def test_sensor_stackexchange_con_mejor_respuesta():
    preguntas = {"items": [{"question_id": 7, "link": "https://blender.stackexchange.com/q/7", "title": "Slow viewport",
                            "body": "<p>Help</p>", "score": 12, "tags": ["performance"], "creation_date": 1790000000,
                            "owner": {"display_name": "Luis"}}], "quota_remaining": 290}
    respuestas = {"items": [{"question_id": 7, "score": 3, "is_accepted": False, "body": "<p>meh</p>"},
                            {"question_id": 7, "score": 1, "is_accepted": True, "body": "<p>Use Simplify</p>",
                             "owner": {"display_name": "Eva"}}]}

    def obtener(url, _c):
        return Respuesta(200, {}, json.dumps(respuestas if "/answers" in url else preguntas).encode())

    fuente = {"sensor": {"tipo": "stackexchange", "sitio": "blender", "puntaje_minimo": 3}}
    salida, estado = sensor_stackexchange(fuente, {}, obtener, ahora=1790900000)
    r = salida["registros"][0]
    assert "Use Simplify" in r["texto_html"] and r["respuesta_aceptada"] and r["autor_respuesta"] == "Eva"
    assert sensor_stackexchange(fuente, estado, obtener, ahora=1790900000)[0]["registros"] == []


# ---------------------------------------------------------------- araña

def test_arana_paginas_sigue_prefijo_y_respeta_modo():
    from scrapy.http import HtmlResponse, Request

    from motor_extraccion.spiders.paginas import PaginasSpider

    html = (b"<html><head><title>Manual</title><meta name='description' content='desc'></head><body>"
            b"<a href='/manual/en/latest/a.html'>a</a><a href='/otra/b.html'>b</a></body></html>")
    url = "https://docs.blender.org/manual/en/latest/index.html"
    respuesta = HtmlResponse(url=url, body=html, headers={"Content-Type": "text/html"}, request=Request(url))
    arana = PaginasSpider(fuente="blender-manual", urls=json.dumps([url]), seguir="1",
                          prefijo="https://docs.blender.org/manual/en/latest/")
    salida = list(arana.parse(respuesta))
    item, peticiones = salida[0], salida[1:]
    assert item["fuente"] == "blender-manual" and "html" in item and item["titulo"] == "Manual"
    assert [p.url for p in peticiones] == ["https://docs.blender.org/manual/en/latest/a.html"]
    solo = PaginasSpider(urls=json.dumps([url]), modo="solo_metadatos")
    item2 = next(iter(solo.parse(respuesta)))
    assert "html" not in item2 and item2["descripcion"] == "desc"
    assert PaginasSpider.guardar_en_mongo is False


def test_arana_paginas_cierra_al_llegar_al_tope():
    from scrapy.exceptions import CloseSpider
    from scrapy.http import HtmlResponse, Request

    from motor_extraccion.spiders.paginas import PaginasSpider

    url = "https://docs.blender.org/manual/en/latest/index.html"
    r = HtmlResponse(url=url, body=b"<html><title>x</title></html>", headers={"Content-Type": "text/html"},
                     request=Request(url))
    arana = PaginasSpider(urls=json.dumps([url]), max_paginas="1")
    assert list(arana.parse(r))
    with pytest.raises(CloseSpider):
        list(arana.parse(r))
