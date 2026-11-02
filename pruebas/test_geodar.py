"""Pruebas de Geodar Radar: sensores nuevos, enrutamiento por destino, catálogo en Mongo, señales y la orden.

Sin red ni nube: un lago en memoria, MongoDB simulado (mongomock) y respuestas HTTP falsas.
"""
import json
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from g7b_ingesta import catalogo as cat
from g7b_ingesta import red
from g7b_ingesta.red import Respuesta
from g7b_ingesta.sensores import sensor_discourse, sensor_github_releases, sensor_json_api
from g7b_lago import LagoMemoria

AHORA = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def responder(rutas):
    """obtener falso: la primera clave contenida en la URL decide la respuesta."""
    pedidas = []

    def obtener(url, _cabeceras=None):
        pedidas.append(url)
        for clave, cuerpo in rutas.items():
            if clave in url:
                if isinstance(cuerpo, Respuesta):
                    return cuerpo
                return Respuesta(200, {}, json.dumps(cuerpo).encode("utf-8"))
        return Respuesta(404)

    obtener.pedidas = pedidas
    return obtener


FORO = {"id": "foro", "sensor": {"tipo": "discourse", "base": "https://foro.example", "rutas": ["/latest.json"]}}
TEMAS = {"topic_list": {"topics": [
    {"id": 1, "slug": "bienvenida", "title": "Bienvenida", "pinned": True},
    {"id": 7, "slug": "viewport-lento", "title": "Viewport lento en Intel UHD", "created_at": "2026-11-02T08:00:00Z",
     "views": 120, "like_count": 4, "posts_count": 6, "reply_count": 5, "has_accepted_answer": True,
     "tags": ["performance", {"name": "viewport", "slug": "viewport"}], "category_id": 3},
    {"id": 8, "slug": "uv", "title": "UV que se estiran", "created_at": "2026-10-27T08:00:00Z", "views": 30,
     "tags": []}]}}


# ---------------------------------------------------------------- catálogo

def test_catalogo_real_tiene_familia_y_destino_explicitos():
    catalogo = cat.cargar()
    for f in catalogo["fuentes"]:
        assert f.get("familia") in cat.FAMILIAS and f.get("destino") in cat.DESTINOS, f["id"]
    # Lo que dijo el plan: MongoDB para documentos y catálogos, Azure para telemetría y señales.
    assert {f["id"] for f in cat.por_destino(catalogo, "senales")} >= {"blender-artists", "blender-devtalk"}
    assert all(f.get("coleccion") for f in cat.por_destino(catalogo, "catalogo"))
    assert all(f["extractor"] != "externo" for f in cat.vigilables(catalogo))


def test_catalogo_valida_destino_y_sensor():
    base = {"id": "x", "nombre": "x", "tipo": "foro", "licencia": "CC0-1.0", "licencia_verificada": True,
            "modo": "texto_completo", "preguntas": ["P1"], "extractor": "directo", "frecuencia_horas": 1,
            "dominios": [], "activa": True}
    errores = cat.validar({"fuentes": [{**base, "destino": "senales", "sensor": {"tipo": "discourse"}}]})
    assert any("texto_completo" in e for e in errores) and any("necesita base" in e for e in errores)
    errores = cat.validar({"fuentes": [{**base, "destino": "catalogo", "sensor": {"tipo": "json_api", "url": "u"}}]})
    assert any("coleccion" in e for e in errores)


# ---------------------------------------------------------------- sensores

def test_discourse_solo_temas_nuevos_y_sin_fijados():
    obtener = responder({"latest.json": TEMAS})
    salida, estado = sensor_discourse(FORO, {}, obtener)
    assert [r["id"] for r in salida["registros"]] == ["7", "8"]
    tema = salida["registros"][0]
    assert tema["url"] == "https://foro.example/t/viewport-lento/7"
    assert tema["etiquetas"] == ["performance", "viewport"]
    assert tema["datos"]["vistas"] == 120 and tema["datos"]["respuesta_aceptada"] is True
    assert "texto" not in tema and "texto_html" not in tema  # solo metadatos
    salida, _ = sensor_discourse(FORO, estado, obtener)
    assert salida["registros"] == []


def test_github_releases_con_licencia_y_sin_borradores(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    fuente = {"id": "h", "sensor": {"tipo": "github_releases", "repos": ["zeux/meshoptimizer", "otro/roto"]}}
    obtener = responder({
        "meshoptimizer/releases": [{"tag_name": "v0.22", "name": "v0.22", "html_url": "https://github.com/x",
                                    "published_at": "2026-10-30T00:00:00Z", "body": "Notas"},
                                   {"tag_name": "v0.23-borrador", "draft": True}],
        "repos/zeux/meshoptimizer": {"license": {"spdx_id": "MIT"}, "stargazers_count": 6000, "topics": ["mesh"]},
    })
    salida, estado = sensor_github_releases(fuente, {}, obtener)
    assert [r["id"] for r in salida["registros"]] == ["zeux/meshoptimizer@v0.22"]
    datos = salida["registros"][0]["datos"]
    assert datos["licencia"] == "MIT" and datos["estrellas"] == 6000
    assert "1 repos con error" in salida["nota"]
    assert sensor_github_releases(fuente, estado, obtener)[0]["registros"] == []
    with pytest.raises(RuntimeError):
        sensor_github_releases({"id": "h", "sensor": {"repos": ["otro/roto"]}}, {}, obtener)


def test_json_api_diccionario_con_huella_sin_descargas():
    fuente = {"id": "ph", "sensor": {"tipo": "json_api", "url": "https://api.polyhaven.com/assets?type=textures",
                                     "id": "@clave", "titulo": "name", "url_item": "https://polyhaven.com/a/{id}",
                                     "campos": ["name", "tags", "download_count"], "huella_sin": ["download_count"]}}
    datos = {"rock_01": {"name": "Rock 01", "tags": ["rock"], "download_count": 10, "otro": "x"}}
    salida, estado = sensor_json_api(fuente, {}, responder({"polyhaven": datos}))
    registro = salida["registros"][0]
    assert registro["url"] == "https://polyhaven.com/a/rock_01" and "otro" not in registro["datos"]
    datos["rock_01"]["download_count"] = 99  # cambia a diario: no es un cambio
    assert sensor_json_api(fuente, estado, responder({"polyhaven": datos}))[0]["registros"] == []
    datos["rock_01"]["tags"] = ["rock", "moss"]
    assert len(sensor_json_api(fuente, estado, responder({"polyhaven": datos}))[0]["registros"]) == 1


def test_json_api_lista_ruta_campo_url_y_solo_ids():
    lista = {"id": "a", "sensor": {"tipo": "json_api", "url": "https://ambientcg.com/api", "items": "foundAssets",
                                   "id": "assetId", "titulo": "displayName", "campo_url": "web"}}
    salida, _ = sensor_json_api(lista, {}, responder({"ambientcg": {"foundAssets": [
        {"assetId": "Wood051", "displayName": "Wood 051", "web": "https://ambientcg.com/view?id=Wood051"}]}}))
    assert salida["registros"][0]["url"].endswith("Wood051") and salida["registros"][0]["titulo"] == "Wood 051"
    caniuse = {"id": "c", "sensor": {"tipo": "json_api", "url": "https://raw.githubusercontent.com/x", "items": "data",
                                     "id": "@clave", "titulo": "title", "solo_ids": ["webgl2"],
                                     "campos": ["title", "usage_perc_y"]}}
    salida, _ = sensor_json_api(caniuse, {}, responder({"raw": {"data": {
        "webgl2": {"title": "WebGL 2.0", "usage_perc_y": 96.1}, "css-grid": {"title": "Grid"}}}}))
    assert [(r["id"], r["datos"]["usage_perc_y"]) for r in salida["registros"]] == [("webgl2", 96.1)]


def test_apis_oficiales_no_dependen_de_robots(monkeypatch):
    def no_leer(*_):
        raise AssertionError("no debe leer robots.txt de una API oficial")

    monkeypatch.setattr(red.urllib.robotparser.RobotFileParser, "read", no_leer)
    assert red.permitido("https://api.github.com/repos/x/y/releases")


# ---------------------------------------------------------------- de punta a punta

def _catalogo(*ids):
    return {"fuentes": [f for f in cat.cargar()["fuentes"] if f["id"] in ids]}


def test_radar_de_punta_a_punta_enruta_por_destino():
    from g7b_ingesta.catalogar import CATALOGADOS, catalogar
    from g7b_ingesta.procesar import procesar
    from g7b_ingesta.senales import RESUMEN, al_panel, resumir
    from g7b_ingesta.vigilar import vigilar

    lago, catalogo = LagoMemoria(), _catalogo("polyhaven-texturas", "blender-artists")
    obtener = responder({
        "api.polyhaven.com": {"rock_01": {"name": "Rock 01", "tags": ["rock"], "max_resolution": [8192, 4096]}},
        "blenderartists.org/latest.json": TEMAS,
        "blenderartists.org/top.json": {"topic_list": {"topics": []}},
    })
    bitacora = vigilar(catalogo, lago, obtener=obtener, ahora=AHORA, salida=lambda *_: None)
    assert not any("error" in b for b in bitacora), bitacora
    assert {b["fuente"] for b in bitacora} == {"polyhaven-texturas", "blender-artists"}

    # El embudo de documentos no toca catálogos ni señales.
    assert procesar(lago, catalogo, cat.cargar_taxonomia(), salida=lambda *_: None) == {}

    base = mongomock.MongoClient()["g7b_catalogo"]
    total = catalogar(lago, base, catalogo, salida=lambda *_: None)
    assert total["nuevo"] == 1
    ficha = base["texturas"].find_one({"doc_id": "polyhaven-texturas:rock_01"})
    assert ficha["licencia"] == "CC0-1.0" and ficha["familia"] == "F3" and "Amatista" in ficha["condiciones"]
    assert ficha["etiquetas"] == ["rock"]
    assert catalogar(lago, base, catalogo, salida=lambda *_: None)["archivos"] == 0  # ya catalogado
    assert lago.leer_json(CATALOGADOS)

    resultado = resumir(lago, catalogo, salida=lambda *_: None)
    semanas = lago.leer_json(RESUMEN)["blender-artists"]
    assert resultado["temas"] == 2 and set(semanas) == {"2026-W44", "2026-W45"}
    assert semanas["2026-W45"]["vistas"] == 120 and semanas["2026-W45"]["etiquetas"]["viewport"] == 1
    panel = mongomock.MongoClient()["g7b_panel"]
    al_panel(panel, resultado["resumen"])
    assert panel["senales"].count_documents({"fuente": "blender-artists"}) == 2
    assert resumir(lago, catalogo, salida=lambda *_: None)["temas"] == 0  # ya resumido


def test_vigilar_olvida_el_error_cuando_la_fuente_vuelve():
    from g7b_ingesta.vigilar import ESTADO, vigilar

    lago, catalogo = LagoMemoria(), _catalogo("blender-devtalk")
    vigilar(catalogo, lago, obtener=responder({}), ahora=AHORA, salida=lambda *_: None)
    assert "HTTP 404" in lago.leer_json(ESTADO)["blender-devtalk"]["ultimo_error"]
    vigilar(catalogo, lago, obtener=responder({"latest.json": TEMAS}), forzar=True,
            ahora=AHORA + timedelta(days=1), salida=lambda *_: None)
    assert "ultimo_error" not in lago.leer_json(ESTADO)["blender-devtalk"]


# ---------------------------------------------------------------- la orden geodar

def test_mapa_markdown_lista_todo_por_familia():
    from geodar.__main__ import mapa_markdown

    catalogo = cat.cargar()
    texto = mapa_markdown(catalogo, hoy="2026-11-02")
    assert all(f["id"] in texto for f in catalogo["fuentes"])
    assert "## F3 · Texturas y materiales" in texto and "| `senales` |" in texto


def test_probar_no_escribe_y_reporta_errores():
    from geodar.__main__ import probar

    resultados = probar(_catalogo("blender-artists", "blender-devtalk", "blender-open-data"),
                        obtener=responder({"blenderartists.org/latest.json": TEMAS,
                                           "blenderartists.org/top.json": {"topic_list": {"topics": []}}}),
                        salida=lambda *_: None)
    por_id = {r["fuente"]: r for r in resultados}
    assert por_id["blender-artists"]["ok"] and por_id["blender-artists"]["registros"] == 2
    assert not por_id["blender-devtalk"]["ok"]
    assert "blender-open-data" not in por_id  # externa: la trae otra tarea


def test_salud_distingue_ok_atrasada_error_y_nunca():
    from geodar.__main__ import salud

    catalogo = _catalogo("arxiv-cs-gr", "blender-stackexchange", "blender-artists", "godot-foro")
    estados = {
        "arxiv-cs-gr": {"ultima_revision": (AHORA - timedelta(hours=5)).isoformat()},
        "blender-stackexchange": {"ultima_revision": (AHORA - timedelta(days=5)).isoformat()},
        "blender-artists": {"ultima_revision": AHORA.isoformat(), "ultimo_error": "HTTP 999"},
    }
    veredictos = {f["fuente"]: f["veredicto"] for f in salud(catalogo, estados, ahora=AHORA)}
    assert veredictos == {"arxiv-cs-gr": "ok", "blender-stackexchange": "atrasada",
                          "blender-artists": "error", "godot-foro": "nunca_revisada"}


def test_ordenes_delegadas_salen_con_cero(monkeypatch):
    import geodar.__main__ as geodar
    from g7b_ingesta import procesar

    monkeypatch.setattr(procesar, "main", lambda argv: {"aceptado": 3})  # devuelve un total, no un código
    assert geodar.main(["procesar", "--simulacro"]) == 0
