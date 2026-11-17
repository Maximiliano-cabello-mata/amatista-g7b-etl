"""Reprocesamiento: bronce se vuelve a evaluar cuando cambian las reglas, sin duplicar nada."""
import copy
import gzip
import io
import json

from g7b_ingesta import catalogo as cat
from g7b_ingesta.embudo import ACEPTADO, Indice, evaluar
from g7b_ingesta.procesar import CONTEOS, INDICE, PROCESADOS, PUBLICADOS, huella_reglas, procesar
from g7b_lago import LagoMemoria

PREGUNTA = {
    "fuente": "blender-stackexchange",
    "url": "https://blender.stackexchange.com/q/9",
    "titulo": "Viewport slow on Intel UHD 620",
    "texto_html": "<p>In Blender 4.2 the viewport runs at 9 fps on my Intel UHD 620 laptop with 8 GB of RAM when I "
                  "add a subdivision modifier. Enable Simplify and set the viewport subdivision levels to 1: on the "
                  "same UHD 620 this went from 9 fps to 24 fps. Use Workbench while modeling and render with EEVEE "
                  "at 16 samples; Cycles at 64 samples took 3 min versus 12 s in EEVEE.</p>",
    "puntaje": 14,
}
# Habla de animación, que el plan todavía no pregunta: hoy se rechaza por relevancia.
ANIMACION = {
    "fuente": "blender-stackexchange",
    "url": "https://blender.stackexchange.com/q/10",
    "titulo": "Squash and stretch with shape keys",
    "texto_html": "<p>In Blender 4.2, for a clay style animation I keyframe shape keys every two frames. "
                  "The squash pose scales the ball to 0.8x on Z and 1.2x on X and Y, and the stretch pose does the "
                  "opposite. I use the graph editor with constant interpolation so the timing reads as stop "
                  "motion, and I add a bit of noise to the keyframes so each frame looks hand made.</p>",
    "puntaje": 5,
}
RUTA = "bronce/blender-stackexchange/2026-11-11/1.jsonl.gz"


def _gz(registros):
    bufer = io.BytesIO()
    with gzip.GzipFile(fileobj=bufer, mode="wb", mtime=0) as gz:
        for r in registros:
            gz.write((json.dumps(r) + "\n").encode("utf-8"))
    return bufer.getvalue()


def _entorno(*registros, ruta=RUTA):
    lago = LagoMemoria()
    lago.archivos[ruta] = _gz(registros)
    catalogo = {"fuentes": [f for f in cat.cargar()["fuentes"] if f["id"] in ("blender-stackexchange", "blender-manual")]}
    return lago, catalogo, cat.cargar_taxonomia()


def _correr(lago, catalogo, taxonomia, **kw):
    return procesar(lago, catalogo, taxonomia, salida=lambda *_: None, **kw)


def _con_animacion(taxonomia):
    nueva = copy.deepcopy(taxonomia)
    nueva["preguntas"]["P9"] = {"nombre": "Animación stop motion", "claves": [["animation", 2], ["keyframe", 2]]}
    return nueva


def test_una_segunda_pasada_no_hace_nada():
    lago, catalogo, taxonomia = _entorno(PREGUNTA, ANIMACION)
    assert _correr(lago, catalogo, taxonomia) == {"aceptado": 1, "rechazado": 1}
    assert _correr(lago, catalogo, taxonomia) == {}
    entrada = lago.leer_json(PROCESADOS)[RUTA]
    assert entrada["reglas"] == huella_reglas(cat.por_id(catalogo)["blender-stackexchange"], taxonomia)


def test_si_el_plan_crece_lo_rechazado_se_recupera_sin_duplicar():
    lago, catalogo, taxonomia = _entorno(PREGUNTA, ANIMACION)
    _correr(lago, catalogo, taxonomia)
    assert lago.leer_json(CONTEOS)["blender-stackexchange"] == {"aceptado:valor": 1, "rechazado:relevancia": 1}

    # El proyecto agrega una pregunta sobre animación: el archivo se reevalúa solo.
    ampliada = _con_animacion(taxonomia)
    total = _correr(lago, catalogo, ampliada)
    assert total.get("rechazado", 0) == 0 and sum(total.values()) == 2
    conteos = lago.leer_json(CONTEOS)["blender-stackexchange"]
    assert sum(conteos.values()) == 2, conteos  # los conteos de la pasada anterior se descontaron
    assert "rechazado:relevancia" not in conteos
    # El documento ya aceptado no chocó consigo mismo en el índice de repetidos.
    salida = "plata/aceptados/blender-stackexchange/2026-11-11/1.jsonl.gz"
    urls = {d["url"] for d in lago.leer_jsonl_gz(salida)}
    assert PREGUNTA["url"] in urls
    assert len(Indice.desde_dict(lago.leer_json(INDICE)).exactas) == len(urls)
    # La salida de rechazados quedó vacía (no se borra: se reemplaza).
    assert lago.leer_jsonl_gz("plata/rechazados/blender-stackexchange/2026-11-11/1.jsonl.gz") == []
    assert lago.leer_json(PROCESADOS)[RUTA]["evaluaciones"] == 2


def test_lo_reevaluado_se_vuelve_a_publicar():
    lago, catalogo, taxonomia = _entorno(PREGUNTA, ANIMACION)
    _correr(lago, catalogo, taxonomia)
    salida = "plata/aceptados/blender-stackexchange/2026-11-11/1.jsonl.gz"
    lago.escribir_json(PUBLICADOS, {salida: {"cuando": "ayer"}})
    _correr(lago, catalogo, _con_animacion(taxonomia))
    assert salida not in lago.leer_json(PUBLICADOS)


def test_reevaluar_a_mano_una_fuente_o_un_lote():
    lago, catalogo, taxonomia = _entorno(PREGUNTA)
    _correr(lago, catalogo, taxonomia)
    assert _correr(lago, catalogo, taxonomia, solo_fuente="blender-manual", forzar=True) == {}
    assert _correr(lago, catalogo, taxonomia, solo_fuente="blender-stackexchange", forzar=True) == {"aceptado": 1}
    assert _correr(lago, catalogo, taxonomia, lote="bronce/blender-stackexchange/2026-11-11/", forzar=True) == {"aceptado": 1}
    assert lago.leer_json(CONTEOS)["blender-stackexchange"] == {"aceptado:valor": 1}


def test_sin_reevaluar_ignora_reglas_nuevas():
    lago, catalogo, taxonomia = _entorno(PREGUNTA, ANIMACION)
    _correr(lago, catalogo, taxonomia)
    assert _correr(lago, catalogo, _con_animacion(taxonomia), reevaluar=False) == {}


def test_lo_procesado_antes_del_reprocesamiento_se_reevalua_una_vez():
    # Entradas viejas de control/procesados.json no tienen «reglas»: se evalúan de nuevo, una sola vez.
    lago, catalogo, taxonomia = _entorno(PREGUNTA)
    lago.escribir_json(PROCESADOS, {RUTA: {"cuando": "2026-11-11T00:00:00+00:00", "aceptado": 0}})
    assert _correr(lago, catalogo, taxonomia) == {"aceptado": 1}
    assert _correr(lago, catalogo, taxonomia) == {}


def test_una_fuente_que_entra_al_catalogo_despues_se_recupera():
    # Pasó con krita-noticias: llegó a bronce antes de estar en el catálogo del procesador.
    lago, catalogo, taxonomia = _entorno(PREGUNTA)
    vacio = {"fuentes": [f for f in catalogo["fuentes"] if f["id"] != "blender-stackexchange"]}
    assert _correr(lago, vacio, taxonomia) == {"rechazado": 1}
    assert _correr(lago, catalogo, taxonomia) == {"aceptado": 1}
    assert lago.leer_json(CONTEOS)["blender-stackexchange"] == {"aceptado:valor": 1}


def test_alias_de_la_arana_antigua():
    registro = {"fuente": "Blender Docs", "url": "https://docs.blender.org/manual/en/5.2/x.html",
                "titulo": "Simplify", "contenido": "corto"}
    lago, catalogo, taxonomia = _entorno(registro, ruta="bronce/zyte/blender_docs/2026-11-01/1.jsonl.gz")
    _correr(lago, catalogo, taxonomia)
    conteos = lago.leer_json(CONTEOS)
    assert "Blender Docs" not in conteos and "blender-manual" in conteos


# --------------------------------------------------------------- filtros corregidos (VERSION_EMBUDO 2)

def _fuente(id_):
    return cat.por_id(cat.cargar())[id_]


def test_mixto_es_un_idioma_admitido():
    texto = ("Para mejorar el rendimiento del viewport activa Simplify y baja las muestras. "
             "Enable Simplify in the render settings and set samples to 16 for better performance. "
             "En Blender 4.2 con una Intel UHD 620 pasa de 9 fps a 24 fps. The viewport is faster this way.")
    r = evaluar({"url": "https://blender.stackexchange.com/q/1", "titulo": "Viewport lento", "texto": texto,
                 "metadatos": {}}, _fuente("blender-stackexchange"), cat.cargar_taxonomia(), Indice())
    assert "idioma" not in " ".join(r.motivos)


def test_un_resumen_corto_sin_palabras_vacias_no_se_rechaza_por_idioma():
    doc = {"url": "https://www.blender.org/press/x/", "titulo": "Blender 5.3 Release",
           "texto": "Cycles GPU rendering performance improvements, viewport optimization, Vulkan backend, "
                    "EEVEE shadows, Geometry Nodes bundles, sculpt brushes, compositor nodes",
           "metadatos": {}}
    r = evaluar(doc, _fuente("blender-noticias"), cat.cargar_taxonomia(), Indice())
    assert not any("idioma" in m for m in r.motivos)


def test_el_manual_279_no_se_marca_como_desactualizado():
    texto = ("In Blender 2.79 the viewport performance depends on the Simplify settings. Lower the subdivision "
             "levels and the samples to keep 30 fps on integrated graphics. The render time with Cycles drops "
             "when you use fewer samples and a smaller tile size; Blender Internal is faster on old computers. ") * 2
    doc = {"url": "https://docs.blender.org/manual/en/2.79/render/x.html", "titulo": "Simplify", "texto": texto,
           "metadatos": {"version": "2.79"}}
    r = evaluar(doc, _fuente("blender-manual"), cat.cargar_taxonomia(), Indice())
    assert not any("desactualizado" in m for m in r.motivos)
    sin_version = evaluar({**doc, "metadatos": {}}, _fuente("blender-manual"), cat.cargar_taxonomia(), Indice())
    assert any("desactualizado" in m for m in sin_version.motivos)
    assert r.estado == ACEPTADO


def test_cambiar_la_operacion_de_una_fuente_no_reevalua_lo_ya_traido():
    from g7b_ingesta.procesar import huella_reglas

    fuente = {"id": "x", "activa": True, "modo": "texto_completo", "umbrales": {"valor_min": 0},
              "sensor": {"tipo": "pagina"}, "frecuencia_horas": 168, "zyte": {"argumentos": {"max_paginas": 3000}}}
    antes = huella_reglas(fuente, {"P1": []})
    operativo = {**fuente, "sensor": {"tipo": "sphinx"}, "frecuencia_horas": 24, "zyte": {"argumentos": {}}}
    assert huella_reglas(operativo, {"P1": []}) == antes
    assert huella_reglas({**fuente, "umbrales": {"valor_min": 1}}, {"P1": []}) != antes
