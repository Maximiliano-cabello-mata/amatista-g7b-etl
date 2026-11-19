"""Comparación por HTTP local y casos que pueden interrumpir o sesgar el recorrido."""
import json
import os
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
from scrapy.http import HtmlResponse

from experimentos.arana_documental import ESTRATEGIAS, PRESUPUESTO, VERDAD, ejecutar, orden_grafo
from motor_extraccion.frontera_documental import Frontera, calificar, palabras
from motor_extraccion.spiders.paginas_laboratorio import PaginasLaboratorioSpider

BASE = "https://ejemplo.test/docs/"


class Estadisticas(Counter):
    def inc_value(self, nombre, count=1):
        self[nombre] += count


def arana(**opciones):
    ara = PaginasLaboratorioSpider(urls=json.dumps([BASE + "inicio"]), prefijo=BASE, **opciones)
    ara.crawler = SimpleNamespace(stats=Estadisticas())
    return ara


def respuesta(peticion, cuerpo="", estado=200, cabeceras=None):
    return HtmlResponse(peticion.url, body=cuerpo.encode(), encoding="utf-8", request=peticion,
                        status=estado, headers=cabeceras or {"Content-Type": "text/html"})


def test_frontera_revaloriza_sin_repetir_y_cobra_al_despachar():
    f = Frontera("foco", 2)
    for url, nota in [("uno", 0.2), ("dos", 0.1), ("dos", 0.9)]:
        f.ofrecer(url, 1, nota)
    assert f.siguiente().url == "dos"
    f.ofrecer("dos", 0, 1)
    assert f.siguiente().url == "uno"
    f.ofrecer("tres", 1, 1)
    assert f.siguiente() is None
    assert palabras("ÍNDICE") == {"indice"}
    assert calificar("/render", "render", "render", {"render"}, 2)[0] == pytest.approx(0.85)


def test_metadata_no_exporta_fragmentos_ni_html_y_respeta_alcance():
    ara = arana(modo="solo_metadatos")
    inicial, = ara.proxima()
    html = ('<title>T</title><meta name="description" content="D"><main><p>Contenido privado</p>'
            '<a href="/docs-otro/fuera">falso prefijo</a><a href="https://otro.test/docs/x">otro</a>'
            '<a href="/docs/%2e%2e/fuera">ascenso</a><a href="mailto:a@b.com">correo</a>'
            '<a href="/docs/segunda#uno">Índice</a><a href="/docs/segunda#dos">otra ancla</a></main>')
    item, segunda = list(ara.parse(respuesta(inicial, html)))
    assert item["descripcion"] == "D" and "html" not in item and "fragmentos" not in item
    assert segunda.url == BASE + "segunda" and not ara.frontera.pendientes
    assert list(ara.fallo(None)) == []
    assert ara.crawler.stats["g7b/lab/intentos"] == 2


def test_redirecciones_y_errores_consumen_presupuesto_y_continuan():
    ara = arana(max_paginas="4")
    primera, = ara.proxima()
    html = '<main><a href="r">r</a><a href="s">s</a></main>'
    item, r = list(ara.parse(respuesta(primera, html)))
    siguiente, = ara.parse(respuesta(r, estado=302, cabeceras={"Location": "https://otro.test/"}))
    local, = ara.parse(respuesta(siguiente, estado=301, cabeceras={"Location": "fin"}))
    assert local.url == BASE + "fin"
    assert list(ara.parse(respuesta(local, estado=503))) == []
    assert len(ara.frontera.visitadas) == 4 and ara.crawler.stats["g7b/lab/html"] == 1


def test_profundidad_y_seguir_cero():
    for opciones in ({"seguir": "0"}, {"profundidad": "0"}):
        ara = arana(**opciones)
        primera, = ara.proxima()
        item, = ara.parse(respuesta(primera, '<main><p>Hola</p><a href="otra">más</a></main>'))
        assert item["fragmentos"] and not ara.frontera.pendientes


@pytest.mark.parametrize("escenario", ["descriptivo", "ambiguo"])
@pytest.mark.parametrize("estrategia", ["paginas", *ESTRATEGIAS])
def test_experimento_http(escenario, estrategia, capsys):
    medida = ejecutar(escenario, estrategia)
    assert "/robots.txt" in medida["orden_http"]
    assert medida["paginas_solicitadas"] >= 1
    assert 0 <= medida["U"] <= len(VERDAD)
    if estrategia != "paginas":
        assert medida["F_visitadas"] == 1.0
    assert medida["Y100"] == round(100 * medida["U"] / medida["Q"], 2)
    if estrategia != "paginas":
        orden = orden_grafo(escenario, estrategia)
        assert medida["paginas_solicitadas"] == PRESUPUESTO
        assert [ruta.removeprefix("/docs/") for ruta in medida["orden_http"] if ruta != "/robots.txt"] == orden
        assert set(medida["evidencia"]) == set(orden) & VERDAD.keys()
        esperadas = {"descriptivo": [1, 2, 3], "ambiguo": [3, 2, 1]}
        assert medida["U"] == esperadas[escenario][ESTRATEGIAS.index(estrategia)]
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with capsys.disabled():
            print("G7B experimento HTTP", json.dumps(medida, ensure_ascii=False), flush=True)
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as archivo:
            archivo.write(f"- {escenario} / {estrategia}: {medida['U']} relaciones, "
                          f"{medida['Q']} peticiones HTTP, Y100={medida['Y100']}.\n")
