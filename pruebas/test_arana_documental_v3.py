import pytest
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.project import get_project_settings

from g7b_ingesta.calidad_documental import calibraciones, inferior
from g7b_ingesta.procesar import a_documento
from motor_extraccion.documental import MODELO, ModeloDocumental
from motor_extraccion.spiders.paginas import PaginasSpider


def pagina(textos, fuente="manual"):
    url = "https://example.org/docs/sampling"
    frag = {"url": url + "#ajustes", "fragmento_id": "f", "jerarquia": ["Ajustes"],
            "titulo": "Ajustes", "version": "4.5", "programa": "blender",
            "bloques": [{"tipo": "parrafo", "texto": t} for t in textos]}
    return {"fragmentos": [frag], "url": url, "fuente": fuente, "html": "HTML CRUDO"}


def test_arana_registro_exacto_y_nombre_publico():
    loader = SpiderLoader(get_project_settings())
    assert set(loader.list()) == {"paginas", "blender_docs"}
    assert loader.load("paginas") is PaginasSpider


def test_arana_eventos_y_gradiente_no_mezclan_bruto():
    modelo = ModeloDocumental()
    item = pagina(["When enabled, this setting reduces memory usage.",
                   "Renombra el objeto Mesa y verifica el nombre en el Outliner.",
                   "Blender es un programa de modelado 3D.", "Un término recién acuñado."])
    modelo.anotar(item)
    assert item["documental"]["conteos"] == {"candidato": 2, "descartado": 1, "revision": 1}
    assert item["documental"]["gradiente"] == 0
    doc = a_documento(item, None, {"modo": "texto_completo"})
    assert "HTML CRUDO" not in doc["texto"] and "modelado 3D" not in doc["texto"]
    assert [c["destinos"] for c in doc["metadatos"]["citas"]] == [["geoda"], ["amatista"]]
    modelo.anotar(item)
    assert item["documental"]["conteos"] == {"referencia": 4}
    nuevo = pagina(["When enabled, this option limits samples."])
    modelo.anotar(nuevo, foro=True)
    assert nuevo["documental"]["conteos"] == {"hipotesis": 1}
    assert modelo.rendimiento == 0.375


def test_arana_conflicto_entre_valores_de_tabla():
    modelo = ModeloDocumental()
    for valor, esperado in [("8", "revision"), ("16", "conflicto")]:
        item = pagina([])
        item["fragmentos"][0]["bloques"] = [{"tipo": "tabla", "texto": valor,
                                             "filas": [["propiedad", "valor"], ["muestras", valor]]}]
        modelo.anotar(item)
        assert item["documental"]["eventos"][0]["decision"] == esperado


def test_arana_puerta_80_y_unidad_de_muestreo():
    def fila(i, util):
        return {"url": f"https://docs.blender.org/{i}", "modelo": MODELO, "fuente": "manual",
                "id": str(i), "revisor": "prueba", "util": util}
    filas = [fila(i, i != 0) for i in range(20)]
    assert inferior(8, 10) < 0.80
    assert calibraciones(filas)["manual"]["habilitada"]
    with pytest.raises(ValueError):
        calibraciones([filas[0], {**filas[0], "url": filas[0]["url"] + "#otra"}])
