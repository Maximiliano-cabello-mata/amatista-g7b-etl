"""Regresiones observadas en el relevo de la araña de sitios."""
import json
from unittest.mock import Mock

import pytest
from scrapy import Request
from scrapy.http import HtmlResponse

from g7b_ingesta import catalogo
from g7b_ingesta.calidad_documental import calibraciones, clave
from g7b_ingesta.procesar import a_documento
from g7b_ingesta.vigilar import argumentos_zyte, en_curso
from motor_extraccion.documental import MODELO
from motor_extraccion.site import MODELO_SITE, puntuar_enlaces
from motor_extraccion.spiders.paginas import PaginasSpider


def test_arana_site_indice_y_cita():
    url = "https://test.invalid/docs/index.html"
    arana = PaginasSpider(urls=json.dumps([url]), version="4.5", seguir="1", fuente="f")
    arana.crawler = Mock()
    req, = arana.start_requests()
    html = """<main><h1>Render settings</h1><ul><li><a href='samples'>Sampling</a></li>
    <li><a href='threshold'>Noise Threshold</a></li><li><a href='options'>Viewport Controls</a></li></ul>
    <p>When enabled, denoising reduces memory usage.</p></main>"""
    resp = HtmlResponse(url, request=req, body=html.encode(), headers={"Content-Type": "text/html"})
    item, siguiente = list(arana.parse(resp))
    assert isinstance(siguiente, Request)
    modelo = item["documental"]
    assert modelo["modelo"] == MODELO_SITE
    assert modelo["conteos"] == {"navegacion": 1, "candidato": 1}
    assert modelo["rendimiento"] == 0.625
    doc = a_documento(item, None, {"modo": "texto_completo"})
    assert "Viewport Controls" not in doc["texto"] and "denoising reduces" in doc["texto"]
    assert doc["metadatos"]["modelo_documental"] == MODELO_SITE


def test_arana_site_frontera_y_tunel():
    filas = [("https://host.test/b/blur", "blur threshold", "blur sampling"),
             ("https://host.test/b/about", "About", "other")]
    notas = list(puntuar_enlaces(filas, {"blur", "threshold"}, 0.5))
    assert notas == list(puntuar_enlaces(filas, {"blur", "threshold"}, 0.5))
    assert notas[0][1] >= 0.28 > notas[1][1]
    base = "https://host.test/docs/"
    arana = PaginasSpider(urls=json.dumps([base]), prefijo=base,
                          prefijos_puente='["https://host.test/b/"]', seguir="1",
                          temas='["blur","threshold"]')
    assert arana.destino(filas[0][0], 0) == 1
    assert arana.destino(filas[0][0], 1) == 2
    assert arana.destino(filas[0][0], 2) is None
    assert arana.destino(base, 2) == 0
    assert arana.destino("https://host.test/b/../private/a", 0) is None
    assert arana.destino("https://another.test/b/blur", 0) is None
    arana.crawler = Mock()
    req, = arana.start_requests()
    html = "<main><p><a href='/b/blur'>blur threshold</a></p><p><a href='/b/about'>about</a></p></main>"
    resp = HtmlResponse(base, request=req, body=html.encode(), headers={"Content-Type": "text/html"})
    _, salto = list(arana.parse(resp))
    assert salto.url == filas[0][0] and salto.meta["saltos_fuera"] == 1
    assert not arana.frontera.pendientes


def test_arana_site_calibraciones_independientes():
    filas = [{"modelo": MODELO, "fuente": "manual", "revisor": "test", "id": str(i),
              "url": f"https://host.test/{i}", "util": True} for i in range(20)]
    filas.append({**filas[0], "modelo": MODELO_SITE, "util": False})
    grupos = calibraciones(filas)
    assert grupos[clave("manual", MODELO)]["habilitada"]
    assert not grupos[clave("manual", MODELO_SITE)]["habilitada"]


@pytest.mark.parametrize("activos,bloquear", [
    ([], False), (["blender_docs"], False), (["paginas"], True),
    (["paginas_laboratorio"], True), (["blender_docs", "blender_docs"], True),
])
def test_arana_site_cupo_del_proyecto(activos, bloquear):
    proyecto = Mock()
    proyecto.jobs.iter.return_value = [{"key": str(i), "spider": a} for i, a in enumerate(activos)]
    assert bool(en_curso(proyecto, "paginas")) == bloquear


def test_arana_site_catalogo_operativo():
    fuente = catalogo.por_id(catalogo.cargar())["blender-compositor-45"]
    arana, argumentos = argumentos_zyte(fuente, [fuente["sensor"]["url"]])
    assert fuente["activa"] and arana == "paginas"
    spider = PaginasSpider(**argumentos)
    assert spider.explorar and spider.version == "4.5" and "blur" in spider.temas
    assert spider.max_paginas == 64

def test_arana_site_quita_plantilla_y_repite_con_referencia():
    from motor_extraccion.site import ModeloSite

    modelo = ModeloSite()
    def evaluar(texto, titulo, url):
        frag = {"fragmento_id": "f", "url": url, "programa": "blender", "version": "4.5",
                "titulo": titulo, "jerarquia": [titulo], "bloques": [{"tipo": "parrafo", "texto": texto}]}
        item = modelo.anotar({"fuente": "f", "fragmentos": [frag]})
        return item["documental"]["eventos"][0]

    plantilla = "Factor Controls the amount of influence the node exerts on the output image. Image Standard color input."
    assert evaluar(plantilla, "Inputs", "a")["decision"] == "revision"
    cita = ("Filter determines how pixel values are interpolated. When applied to a photograph, "
            "a larger neighborhood preserves gradients and reduces the jagged edges; nearest sampling "
            "is faster at the cost of visible steps in motion.")
    assert evaluar(cita, "Rotate", "a")["decision"] == "candidato"
    repetido = evaluar(cita, "Transform", "b")
    assert repetido["decision"] == "referencia" and repetido["referencia"] == "a"
    assert evaluar(cita.replace("faster", "slower"), "Transform", "c")["decision"] == "candidato"
