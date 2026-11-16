"""Contrato de fragmentos: fixtures locales, sin Mongo, Azure ni tr�fico HTTP."""
import json

import pytest
from scrapy.http import HtmlResponse

from motor_extraccion.spiders.blender_docs import BlenderDocsSpider

URL = "https://docs.blender.org/manual/en/4.5/modeling/modifiers/bevel.html"
HTML = """<article role="main"><section id="bevel">
<h1>Bevel<a class="headerlink" href="#bevel">�</a></h1><p>Round edges.</p>
<section id="options"><h2>Options</h2>
<div class="admonition warning"><p>Warning</p><p>Apply scale first.</p></div>
<table><tr><th>Setting</th><th>Value</th></tr><tr><td>Segments</td><td>2</td></tr></table>
<section id="width"><h3>Width</h3><p>Size of the bevel.</p>
<ul><li>Parent<ul><li>Child</li></ul></li></ul>
<pre>if True:
    bpy.ops.object.modifier_add(type='BEVEL')</pre>
<p><a href="../index.html">Modeling</a><img src="bevel.png" alt="Edge"/></p>
</section></section>
<section id="limits"><h2>Limits</h2><p>Clamp overlapping geometry.</p></section>
</section></article>"""


def extraer(html=HTML, version="4.5", **kwargs):
    response = HtmlResponse(url=URL.replace("4.5", version), body=html.encode(), encoding="utf-8")
    return BlenderDocsSpider(**kwargs).extraer(response, version, "modeling/modifiers")


def test_jerarquia_anclas_y_no_mezclar_apartados():
    doc = extraer()
    fragmentos = {f["ancla"]: f for f in doc["fragmentos"]}
    assert fragmentos["width"]["jerarquia"] == ["Bevel", "Options", "Width"]
    assert fragmentos["limits"]["jerarquia"] == ["Bevel", "Limits"]
    assert fragmentos["width"]["url"] == URL + "#width"
    assert "Size of the bevel" not in fragmentos["options"]["contenido"]
    assert fragmentos["width"]["contenido"].count("Child") == 1
    assert "�" not in fragmentos["bevel"]["titulo"]
    assert doc["schema_version"] == 2
    assert doc["doc_id"] and doc["contenido"]  # contrato anterior sigue disponible


def test_tablas_avisos_codigo_y_referencias():
    fragmentos = {f["ancla"]: f for f in extraer()["fragmentos"]}
    bloques = fragmentos["options"]["bloques"]
    assert bloques[0]["tipo"] == "aviso" and "Apply scale first." in bloques[0]["texto"]
    assert bloques[1]["filas"] == [["Setting", "Value"], ["Segments", "2"]]
    width = fragmentos["width"]["bloques"]
    assert any("    bpy.ops" in b["texto"] for b in width if b["tipo"] == "codigo")
    assert width[-1]["imagenes"][0]["alt"] == "Edge"
    assert width[-1]["enlaces"][0]["url"].endswith("/modeling/index.html")


def test_ids_estables_versionados_y_huellas_sensibles():
    a, b = extraer(), extraer()
    c = extraer(HTML.replace("Apply scale first.", "Apply scale before bevel."))
    d = extraer(version="3.6")
    assert a["fragmentos"] == b["fragmentos"]
    assert a["fragmentos"][1]["fragmento_id"] == c["fragmentos"][1]["fragmento_id"]
    assert a["fragmentos"][1]["hash_contenido"] != c["fragmentos"][1]["hash_contenido"]
    assert a["fragmentos"][1]["fragmento_id"] != d["fragmentos"][1]["fragmento_id"]
    assert a["hash_contenido"] != extraer(HTML.replace("<td>2", "<td>3"))["hash_contenido"]


def test_seleccion_exacta_sin_inventar_anclas():
    doc = extraer(anclas_objetivo=json.dumps(["width"]))
    assert [f["ancla"] for f in doc["fragmentos"]] == ["width"]
    assert extraer(anclas_objetivo='["inexistente"]') is None
    sin_ancla = extraer('<article role="main"><h1>Title</h1><p>Body.</p></article>')
    assert sin_ancla["fragmentos"][0]["url"] == URL
    assert sin_ancla["fragmentos"][0]["ancla"] == ""
    with pytest.raises(ValueError):
        BlenderDocsSpider(anclas_objetivo='"width"')


def test_codigo_solo_y_sphinx_antiguo():
    html = """<div class="body"><div class="section" id="code"><h1>Code</h1>
    <pre>print('hello')</pre></div></div>"""
    doc = extraer(html)
    assert doc["fragmentos"][0]["url"] == URL + "#code"
    assert doc["fragmentos"][0]["bloques"][0]["tipo"] == "codigo"

