"""La cadena completa contra Azurite: sensores → bronce → embudo → plata, y el disparo de Zyte."""
import json
import os
import uuid
from datetime import datetime, timezone

import pytest

from g7b_ingesta import catalogo as cat
from g7b_ingesta.red import Respuesta

CONEXION = os.environ.get("AZURE_PRUEBAS_CONEXION")
pytestmark = pytest.mark.skipif(not CONEXION, reason="sin Azurite (AZURE_PRUEBAS_CONEXION)")

AHORA = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2611.00001v1</id><title>Level of detail for real-time rendering of large meshes</title>
    <link href="http://arxiv.org/abs/2611.00001v1"/>
    <summary>We present a level of detail method for real-time rendering of very large meshes on modest GPUs,
    combining mesh simplification with culling, and evaluate it against existing techniques.</summary></entry>
  <entry><id>http://arxiv.org/abs/2611.00002v1</id><title>Short</title>
    <link href="http://arxiv.org/abs/2611.00002v1"/><summary>Tiny.</summary></entry>
</feed>""".encode("utf-8")

PREGUNTAS = {"items": [{
    "question_id": 9, "link": "https://blender.stackexchange.com/q/9", "title": "Viewport slow on Intel UHD 620",
    "body": "<p>In Blender 4.2 the viewport runs at 9 fps on my Intel UHD 620 laptop with 8 GB of RAM when I "
            "add a subdivision modifier. What settings help performance on integrated graphics?</p>",
    "score": 14, "tags": ["performance", "viewport"], "creation_date": 1790000000,
    "owner": {"display_name": "Luis"}}], "quota_remaining": 280}
RESPUESTAS = {"items": [{
    "question_id": 9, "score": 20, "is_accepted": True, "owner": {"display_name": "Eva"},
    "body": "<p>Enable Simplify and set the viewport subdivision levels to 1. On the same UHD 620 this went from "
            "9 fps to 24 fps. Use Workbench or solid shading while modeling, and render with EEVEE at 16 samples; "
            "Cycles at 64 samples took 3 min versus 12 s in EEVEE.</p>"}]}


def obtener_falso(url, _cabeceras):
    if "arxiv" in url:
        return Respuesta(200, {"etag": "a1"}, ATOM)
    if "/answers" in url:
        return Respuesta(200, {}, json.dumps(RESPUESTAS).encode())
    if "stackexchange" in url:
        return Respuesta(200, {}, json.dumps(PREGUNTAS).encode())
    if "docs.blender.org" in url:
        return Respuesta(200, {}, b"<html>manual v1</html>")
    return Respuesta(404)


class ZyteFalso:
    def __init__(self):
        self.lanzados = []

    def get_project(self, _id):
        lanzados = self.lanzados

        class Jobs:
            def run(self, arana, job_args):
                lanzados.append((arana, job_args))
                return type("Trabajo", (), {"key": f"883618/2/{len(lanzados)}"})()

        return type("Proyecto", (), {"jobs": Jobs()})()


@pytest.fixture
def lago():
    from azure.storage.blob import BlobServiceClient

    from g7b_lago import Lago

    contenedor = BlobServiceClient.from_connection_string(CONEXION).create_container(f"ing{uuid.uuid4().hex[:12]}")
    yield Lago(contenedor)
    contenedor.delete_container()


def test_cadena_completa(lago):
    from g7b_ingesta.procesar import CONTEOS, procesar
    from g7b_ingesta.vigilar import ESTADO, vigilar

    # Las fuentes de esta prueba (Geodar agregó más; tienen sus pruebas en test_geodar.py).
    originales = {"arxiv-cs-gr", "blender-stackexchange", "blender-manual"}
    catalogo = {"fuentes": [f for f in cat.cargar()["fuentes"] if f["id"] in originales]}
    zyte = ZyteFalso()
    bitacora = vigilar(catalogo, lago, obtener=obtener_falso, zyte=zyte, proyecto_id="883618",
                       ahora=AHORA, salida=lambda *_: None)
    por_fuente = {b["fuente"]: b for b in bitacora}
    assert set(por_fuente) == {f["id"] for f in cat.vigilables(catalogo)}
    assert not any("error" in b for b in bitacora), bitacora
    assert por_fuente["blender-manual"]["accion"].startswith("zyte: trabajo 883618/2/")
    arana, argumentos = zyte.lanzados[0]
    assert arana == "blender_docs" and argumentos == {"fuente": "blender-manual", "max_paginas": "3000"}

    # Recién revisadas: no se vuelven a revisar hasta que les toque.
    assert vigilar(catalogo, lago, obtener=obtener_falso, zyte=zyte, ahora=AHORA, salida=lambda *_: None) == []
    assert lago.leer_json(ESTADO)["arxiv-cs-gr"]["etag"] == "a1"

    total = procesar(lago, catalogo, cat.cargar_taxonomia(), salida=lambda *_: None)
    assert total == {"aceptado": 2, "rechazado": 1}

    aceptados = [d for ruta in lago.listar("plata/aceptados/") for d in lago.leer_jsonl_gz(ruta)]
    por_url = {d["url"]: d for d in aceptados}
    foro = por_url["https://blender.stackexchange.com/q/9"]
    assert "P1" in foro["embudo"]["preguntas"] and foro["licencia"] == "CC-BY-SA-4.0"
    assert foro["metadatos"]["autor_respuesta"] == "Eva"  # atribución para CC BY-SA
    assert "P5" in por_url["http://arxiv.org/abs/2611.00001v1"]["embudo"]["preguntas"]

    rechazados = [d for ruta in lago.listar("plata/rechazados/") for d in lago.leer_jsonl_gz(ruta)]
    assert rechazados[0]["embudo"]["etapa"] == "calidad" and "texto" not in rechazados[0]
    assert lago.leer_json(CONTEOS)["arxiv-cs-gr"] == {"aceptado:valor": 1, "rechazado:calidad": 1}

    # Lo ya procesado no se vuelve a procesar.
    assert procesar(lago, catalogo, cat.cargar_taxonomia(), salida=lambda *_: None) == {}


def test_publicar_aceptados_en_mongo(lago):
    import mongomock

    from g7b_ingesta.procesar import procesar
    from g7b_ingesta.publicar import COLECCION, publicar
    from g7b_ingesta.vigilar import vigilar

    catalogo = cat.cargar()
    vigilar(catalogo, lago, obtener=obtener_falso, zyte=ZyteFalso(), proyecto_id="883618", ahora=AHORA,
            salida=lambda *_: None)
    procesar(lago, catalogo, cat.cargar_taxonomia(), salida=lambda *_: None)
    base = mongomock.MongoClient()["conocimiento_3d"]
    total = publicar(lago, base, salida=lambda *_: None)
    assert (total["nuevo"], total["actualizado"]) == (2, 0)
    foro = base[COLECCION].find_one({"url": "https://blender.stackexchange.com/q/9"})
    assert foro["licencia"] == "CC-BY-SA-4.0" and "P1" in foro["preguntas"] and foro["creado_en"]
    # Lo ya publicado no se vuelve a leer, y sin cambios no se reescribe.
    assert publicar(lago, base, salida=lambda *_: None)["archivos"] == 0
    assert base[COLECCION].count_documents({}) == 2


def test_publicar_se_detiene_al_limite(lago):
    from g7b_ingesta.publicar import publicar

    class BaseLlena(dict):
        def __missing__(self, nombre):
            import mongomock

            return mongomock.MongoClient()["x"][nombre]

        def command(self, _):
            return {"dataSize": 450 * 1024 * 1024}

    lago.subir_jsonl_gz("bronce/x/2026-11-01/a.jsonl.gz", [{"a": 1}])
    lago.subir_bytes("plata/aceptados/x/2026-11-01/a.jsonl.gz", lago.contenedor.download_blob(
        "bronce/x/2026-11-01/a.jsonl.gz").readall())
    assert publicar(lago, BaseLlena(), salida=lambda *_: None).get("detenido_por_tamano")
