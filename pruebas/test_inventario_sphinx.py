"""La araña guiada por el inventario de Sphinx: cada página una vez, en orden y con cobertura. Sin red."""
import json
import zlib

from scrapy.http import HtmlResponse, Request, Response

from motor_extraccion import inventario_sphinx as inv
from motor_extraccion.spiders.blender_docs import BlenderDocsSpider

BASE = "https://docs.blender.org/manual/en/"


def objects_inv(paginas, extra=()):
    cuerpo = "".join(f"{p.removesuffix('.html')} std:doc -1 {p} {p}\n" for p in paginas)
    cuerpo += "".join(extra)
    return (b"# Sphinx inventory version 2\n# Project: Blender 5.2 LTS Manual\n# Version: 5.2\n"
            b"# The remainder of this file is compressed using zlib.\n" + zlib.compress(cuerpo.encode()))


def html(texto, canonica="https://docs.blender.org/manual/en/latest/x.html"):
    return (f"<html><head><link rel='canonical' href='{canonica}'/></head><body><article role='main'>"
            f"<h1>Título</h1><p>{texto}</p><a href='otra.html'>enlace</a></article></body></html>")


def pagina(url, texto):
    return HtmlResponse(url=url, body=html(texto).encode(), headers={"Content-Type": "text/html"},
                        request=Request(url))


def test_leer_inventario_real_en_miniatura():
    datos = inv.leer(objects_inv(["render/cycles/index.html", "addons/index.html"],
                                 extra=["Max std:label -1 render/cycles/index.html#$ Max\n",
                                        "render/eevee/index std:doc -1 render/eevee/$ -\n"]))
    assert datos["proyecto"] == "Blender 5.2 LTS Manual" and datos["version"] == "5.2"
    # Solo std:doc; el «$» final se reemplaza por el nombre; sin repetidos y ordenado.
    assert datos["paginas"] == ["addons/index.html", "render/cycles/index.html", "render/eevee/render/eevee/index"]
    assert len(datos["huella"]) == 64


def test_huella_solo_cambia_con_la_estructura():
    a = inv.leer(objects_inv(["a.html", "b.html"]))["huella"]
    assert a == inv.leer(objects_inv(["a.html", "b.html"]))["huella"]
    assert a != inv.leer(objects_inv(["a.html", "b.html", "c.html"]))["huella"]


def test_filtrar_asigna_cada_pagina_a_una_sola_seccion():
    paginas = ["render/cycles/index.html", "render/cycles/baking.html", "render/eevee/index.html",
               "editors/preferences/system.html", "editors/preferences/input.html", "modeling/x.html"]
    secciones = ["render/index.html", "render/cycles/index.html", "editors/preferences/system.html"]
    assert inv.filtrar(paginas, secciones) == [
        ("render/cycles/index.html", "render/cycles"), ("render/cycles/baking.html", "render/cycles"),
        ("render/eevee/index.html", "render"),
        ("editors/preferences/system.html", "editors/preferences"),
        ("editors/preferences/input.html", "editors/preferences")]
    assert len(inv.filtrar(paginas, [])) == len(paginas)  # sin secciones: todo el manual


def _inventario(arana, version, paginas):
    url = f"{BASE}{version}/objects.inv"
    return list(arana.parse_inventario(Response(url, body=objects_inv(paginas), request=Request(url)),
                                       version=version))


def test_arana_pide_cada_pagina_del_inventario_una_vez_y_en_orden():
    arana = BlenderDocsSpider(versiones=json.dumps(["5.2"]),
                              secciones=json.dumps(["render/cycles/index.html", "render/index.html"]))
    peticiones = _inventario(arana, "5.2", ["render/cycles/b.html", "render/cycles/a.html", "addons/x.html"])
    assert [r.url for r in peticiones] == [f"{BASE}5.2/render/cycles/a.html", f"{BASE}5.2/render/cycles/b.html"]
    assert [r.priority for r in peticiones] == [0, -1]
    assert arana.esperadas == {"5.2": 2}
    # En modo inventario la página no agrega enlaces: la lista ya está completa.
    salida = list(arana.parse_pagina(pagina(peticiones[0].url, "Texto de Cycles"), **peticiones[0].cb_kwargs))
    assert len(salida) == 1 and salida[0]["ruta"] == "render/cycles/a.html"
    assert salida[0]["canonica"] == "https://docs.blender.org/manual/en/latest/x.html"
    assert arana.extraidas == {"5.2": 1}


def test_tope_por_version_no_deja_versiones_vacias():
    arana = BlenderDocsSpider(versiones=json.dumps(["5.2", "2.79"]), secciones=json.dumps([]), max_por_version="2")
    assert len(_inventario(arana, "5.2", [f"p{i}.html" for i in range(10)])) == 2
    assert len(_inventario(arana, "2.79", [f"p{i}.html" for i in range(10)])) == 2
    assert arana.esperadas == {"5.2": 2, "2.79": 2}


def test_misma_pagina_en_dos_rutas_sale_una_vez_con_su_alias():
    arana = BlenderDocsSpider(versiones=json.dumps(["4.5"]), secciones=json.dumps([]))
    kw = {"version": "4.5", "seccion": "render", "prefijo": None}
    a = list(arana.parse_pagina(pagina(f"{BASE}4.5/render/eevee/gp.html", "Grease Pencil igual"), **kw))[0]
    b = list(arana.parse_pagina(pagina(f"{BASE}4.5/render/cycles/gp.html", "Grease Pencil igual"), **kw))[0]
    assert "contenido" in a and "duplicado_de" not in a
    assert b["duplicado_de"] == a["url"] and "contenido" not in b
    # En otra versión el mismo texto no es alias: es otra versión de la página.
    c = list(arana.parse_pagina(pagina(f"{BASE}3.6/render/eevee/gp.html", "Grease Pencil igual"),
                                **{**kw, "version": "3.6"}))[0]
    assert "duplicado_de" not in c


def test_sin_inventario_vuelve_a_seguir_enlaces():
    arana = BlenderDocsSpider(versiones=json.dumps(["2.79"]), secciones=json.dumps(["render/index.html"]))
    url = f"{BASE}2.79/objects.inv"
    peticiones = list(arana.parse_inventario(Response(url, body=b"<html>404</html>", request=Request(url)),
                                             version="2.79"))
    assert [r.url for r in peticiones] == [f"{BASE}2.79/render/index.html"]
    assert peticiones[0].cb_kwargs["prefijo"] == f"{BASE}2.79/render/"


# --- El sensor del radar y el candado de Zyte -------------------------------------------------

from datetime import datetime, timedelta, timezone  # noqa: E402

from g7b_ingesta.red import Respuesta  # noqa: E402
from g7b_ingesta.sensores import sensor_sphinx  # noqa: E402

FUENTE = {"id": "blender-manual", "sensor": {"tipo": "sphinx", "base": BASE, "versiones": ["5.2", "4.5"],
                                              "refresco_dias": 30}}
HOY = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def servidor(inventarios, vistos=None):
    def obtener(url, cabeceras):
        if vistos is not None:
            vistos.append((url, cabeceras))
        version = url.rsplit("/", 2)[1]
        etag = f'"{version}-{len(inventarios[version])}"'
        if cabeceras.get("If-None-Match") == etag:
            return Respuesta(304)
        return Respuesta(200, {"etag": etag}, objects_inv(inventarios[version]))
    return obtener


def test_sensor_sphinx_relanza_solo_la_version_que_cambio():
    inventarios = {"5.2": ["a.html", "b.html"], "4.5": ["a.html"]}
    primera, estado = sensor_sphinx(FUENTE, {}, servidor(inventarios), ahora=HOY)
    assert primera["argumentos"] == {"versiones": ["5.2", "4.5"]} and "primera vez" in primera["nota"]
    # Al día siguiente nada cambió: no se lanza nada (y se pregunta con ETag, sin bajar el inventario).
    vistos = []
    igual, estado = sensor_sphinx(FUENTE, estado, servidor(inventarios, vistos), ahora=HOY + timedelta(days=1))
    assert igual["urls"] == [] and "argumentos" not in igual
    assert all("If-None-Match" in c for _, c in vistos)
    # Se agrega una página a 5.2: solo 5.2 vuelve a recorrerse.
    inventarios["5.2"] = inventarios["5.2"] + ["c.html"]
    cambio, estado = sensor_sphinx(FUENTE, estado, servidor(inventarios), ahora=HOY + timedelta(days=2))
    assert cambio["argumentos"] == {"versiones": ["5.2"]} and "inventario cambió" in cambio["nota"]
    # Pasado el refresco, la versión que no cambió también se repasa (ediciones de texto).
    tarde, _ = sensor_sphinx(FUENTE, estado, servidor(inventarios), ahora=HOY + timedelta(days=31))
    assert tarde["argumentos"] == {"versiones": ["4.5"]} and "refresco de 30 días" in tarde["nota"]


def test_sensor_sphinx_falla_si_no_hay_inventario():
    import pytest

    with pytest.raises(RuntimeError, match="HTTP 404"):
        sensor_sphinx(FUENTE, {}, lambda u, c: Respuesta(404), ahora=HOY)


class ZyteConTrabajos:
    def __init__(self, activos=()):
        self.activos, self.lanzados = list(activos), []

    def get_project(self, _id):
        zyte = self

        class Jobs:
            def iter(self, spider, state):
                assert state == ["pending", "running"]
                return [{"key": k} for a, k in zyte.activos if a == spider]

            def run(self, arana, job_args):
                zyte.lanzados.append((arana, job_args))
                return type("Trabajo", (), {"key": f"883618/2/{len(zyte.lanzados)}"})()

        return type("Proyecto", (), {"jobs": Jobs()})()


class LagoMinimo:
    def __init__(self):
        self.json = {}

    def leer_json(self, ruta, por_omision=None):
        return self.json.get(ruta, por_omision)

    def escribir_json(self, ruta, datos):
        self.json[ruta] = datos

    def subir_jsonl_gz(self, ruta, registros, **_):
        list(registros)


def _catalogo():
    from g7b_ingesta import catalogo as cat

    return {"fuentes": [f for f in cat.cargar()["fuentes"] if f["id"] == "blender-manual"]}


def test_vigilar_pasa_las_versiones_y_no_lanza_dos_recorridos():
    from g7b_ingesta.vigilar import ESTADO, vigilar

    inventarios = {"5.2": ["a.html"], "4.5": ["a.html"], "3.6": ["a.html"]}
    lago, zyte = LagoMinimo(), ZyteConTrabajos(activos=[("blender_docs", "883618/2/9")])
    # Hay un recorrido en curso: no se lanza otro y el cambio queda pendiente para la próxima vuelta.
    bitacora = vigilar(_catalogo(), lago, obtener=servidor(inventarios), zyte=zyte, proyecto_id="883618",
                       ahora=HOY, salida=lambda *_: None)
    assert "ya hay un trabajo en curso (883618/2/9)" in bitacora[0]["accion"] and zyte.lanzados == []
    assert "versiones" not in lago.json[ESTADO]["blender-manual"]
    # Terminó el anterior: al día siguiente se lanza uno, solo con las versiones que tocan.
    zyte.activos = []
    bitacora = vigilar(_catalogo(), lago, obtener=servidor(inventarios), zyte=zyte, proyecto_id="883618",
                       ahora=HOY + timedelta(days=1), salida=lambda *_: None)
    assert bitacora[0]["accion"] == "zyte: trabajo 883618/2/1"
    arana, argumentos = zyte.lanzados[0]
    assert arana == "blender_docs" and json.loads(argumentos["versiones"]) == ["5.2", "4.5", "3.6"]
    assert argumentos["max_por_version"] == "1200"
    # Y al otro día, sin cambios, nada.
    assert vigilar(_catalogo(), lago, obtener=servidor(inventarios), zyte=zyte, proyecto_id="883618",
                   ahora=HOY + timedelta(days=2), salida=lambda *_: None)[0]["accion"] == "nada nuevo"


def test_el_embudo_anota_el_alias_sin_evaluar_texto():
    from g7b_ingesta import catalogo as cat
    from g7b_ingesta.embudo import Indice, evaluar
    from g7b_ingesta.procesar import a_documento

    fuente = _catalogo()["fuentes"][0]
    doc = a_documento({"url": f"{BASE}4.5/render/cycles/gp.html", "titulo": "GP", "version": "4.5",
                       "duplicado_de": f"{BASE}4.5/render/eevee/gp.html"}, None, fuente)
    r = evaluar(doc, fuente, cat.cargar_taxonomia(), Indice())
    assert (r.estado, r.etapa) == ("rechazado", "duplicados")
    assert r.motivos == ["la misma página ya se extrajo en otra ruta del manual"]
