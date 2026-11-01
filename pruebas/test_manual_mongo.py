"""La araña estructurada de manuales y el guardado idempotente en MongoDB. Sin red."""
import json

import mongomock
from scrapy.http import HtmlResponse, Request

from motor_extraccion.pipelines import guardar
from motor_extraccion.spiders.blender_docs import BlenderDocsSpider
from motor_extraccion.spiders.manual_sphinx import ManualSphinxSpider

PAGINA = """<html><head><title>Simplify — Blender Manual</title></head><body>
<nav><ul><li><a href="../../index.html">Inicio</a></li></ul></nav>
<article role="main">
  <h1>Simplify<a class="headerlink">¶</a></h1>
  <p>Global settings to make working with heavy scenes faster on modest hardware.</p>
  <h2>Viewport</h2>
  <dl class="simple">
    <dt>Max Subdivision</dt><dd><p>Global maximum subdivision level in the viewport.</p></dd>
    <dt>Child Particles</dt><dd><p>Fraction of child particles shown in the viewport.</p></dd>
  </dl>
  <ul><li><p>Use it while modeling on integrated graphics.</p></li></ul>
  <div class="highlight"><pre>bpy.context.scene.render.use_simplify = True</pre></div>
  <a href="subpagina.html#ancla">Más</a> <a href="../../../modeling/fuera.html">Fuera</a>
</article></body></html>"""

URL = "https://docs.blender.org/manual/en/5.2/render/cycles/render_settings/simplify.html"


def respuesta(html=PAGINA, url=URL):
    return HtmlResponse(url=url, body=html.encode("utf-8"), headers={"Content-Type": "text/html"},
                        request=Request(url))


def correr(arana, resp, prefijo="https://docs.blender.org/manual/en/5.2/render/cycles/"):
    return list(arana.parse_pagina(resp, version="5.2", seccion="render/cycles", prefijo=prefijo))


def test_manual_extrae_propiedades_codigo_y_jerarquia():
    salida = correr(BlenderDocsSpider(), respuesta())
    doc, peticiones = salida[0], salida[1:]
    assert doc["titulo"] == "Simplify" and doc["jerarquia"] == ["Viewport"]
    assert doc["propiedades"][0] == {"nombre": "Max Subdivision",
                                     "descripcion": "Global maximum subdivision level in the viewport."}
    assert "**Max Subdivision**: Global maximum" in doc["contenido"]
    assert doc["bloques_codigo"] == ["bpy.context.scene.render.use_simplify = True"]
    assert doc["operadores_bpy"] == ["bpy.context.scene.render.use_simplify"]
    assert "- Use it while modeling" in doc["contenido"] and "Inicio" not in doc["contenido"]
    assert doc["version"] == "5.2" and doc["fuente"] == "blender-manual" and len(doc["doc_id"]) == 64
    # Sigue la sección completa (sin anclas) y no sale de ella.
    assert [p.url for p in peticiones] == [URL.rsplit("/", 1)[0] + "/subpagina.html"]


def test_manual_huella_estable_y_sensible_al_cambio():
    a = correr(BlenderDocsSpider(), respuesta())[0]
    b = correr(BlenderDocsSpider(), respuesta())[0]
    c = correr(BlenderDocsSpider(), respuesta(PAGINA.replace("faster", "much faster")))[0]
    assert a["hash_contenido"] == b["hash_contenido"] != c["hash_contenido"]


def test_manual_descarta_paginas_sin_contenido():
    vacia = "<html><body><article role='main'><h1>Índice</h1></article></body></html>"
    assert [x for x in correr(BlenderDocsSpider(), respuesta(vacia)) if isinstance(x, dict)] == []


def test_manual_semillas_por_version_y_seccion():
    arana = ManualSphinxSpider(fuente="godot-docs", base="https://docs.godotengine.org/en",
                               versiones=json.dumps(["stable"]), secciones=json.dumps(["tutorials/3d/index.html"]))
    semilla = next(iter(arana.start_requests()))
    assert semilla.url == "https://docs.godotengine.org/en/stable/tutorials/3d/index.html"
    assert semilla.cb_kwargs["prefijo"] == "https://docs.godotengine.org/en/stable/tutorials/3d/"
    blender = list(BlenderDocsSpider().start_requests())
    assert len(blender) == 4 * 10 and blender[0].url.startswith("https://docs.blender.org/manual/en/5.2/")


def test_mongo_guardar_solo_si_cambia():
    coleccion = mongomock.MongoClient()["conocimiento_3d"]["documentos"]
    coleccion.create_index("doc_id", unique=True)
    doc = {"doc_id": "a", "hash_contenido": "h1", "texto": "uno"}
    assert guardar(coleccion, doc) == "nuevo"
    creado = coleccion.find_one({"doc_id": "a"})["creado_en"]
    assert guardar(coleccion, {**doc, "extraido_en": "otra fecha"}) == "sin_cambios"
    assert guardar(coleccion, {**doc, "hash_contenido": "h2", "texto": "dos"}) == "actualizado"
    final = coleccion.find_one({"doc_id": "a"})
    assert final["texto"] == "dos" and final["creado_en"] == creado and coleccion.count_documents({}) == 1


def test_pipeline_no_conecta_si_la_arana_no_lo_pide():
    from motor_extraccion.pipelines import MongoPipeline

    pipeline = MongoPipeline(None, "conocimiento_3d", "documentos")
    pipeline.open_spider(BlenderDocsSpider())  # sin MONGO_URI y sin error: no lo necesita
    item = {"doc_id": "x"}
    assert pipeline.process_item(item, BlenderDocsSpider()) is item and pipeline.cliente is None
