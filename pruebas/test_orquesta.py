"""Pruebas de la compuerta de calidad (calidad.py) y del orquestador por fases (orquesta.py)."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from g7b_almacen import almacen as alm
from g7b_almacen import calidad, orquesta

sys.path.insert(0, os.path.dirname(__file__))
from test_almacen import copia_opendata, medicion  # noqa: E402  reutiliza los generadores de datos

AHORA = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def _poblar(a, con_opendata=True):
    if con_opendata:
        a.escribir("bronce/opendata/2026-11-01/od.zip", copia_opendata())
        a.escribir("control/opendata.json",
                   json.dumps({"url": "x", "firma": "1", "ruta": "bronce/opendata/2026-11-01/od.zip",
                               "descargado": AHORA.isoformat()}).encode())
    for i, h in enumerate(["e1", "e1", "e2", "e2", "e3"]):
        a.escribir(f"bronce/sonda/2026-11-01/m{i}.json",
                   json.dumps(medicion(h, "N2", {"completo": 18.0 + i, "ligero": 34.0 + i, "minimo": 61.0})).encode())


class _Sesion:
    """Open Data falso para la fase de ingesta."""
    def __init__(self):
        self.descargas = 0

    def get(self, url, **_):
        if url.endswith("/download/"):
            class R:
                text = '<a href="https://x.org/opendata-20261101.zip">'
                def raise_for_status(self): pass
            return R()
        self.descargas += 1
        class R:
            content = copia_opendata()
            def raise_for_status(self): pass
        return R()

    def head(self, url, **_):
        class R:
            headers = {"ETag": '"abc"'}
            def raise_for_status(self): pass
        return R()


def test_compuerta_aprueba_datos_buenos(tmp_path):
    a = alm.Carpeta(tmp_path)
    _poblar(a)
    from g7b_almacen import cubo
    cubo.construir(a, salida=lambda *_: None, ahora=AHORA)
    reporte = calidad.evaluar(a, ahora=AHORA)
    assert reporte["aprobado"] is True and reporte["fallas"] == 0
    nombres = {c["nombre"]: c["estado"] for c in reporte["checks"]}
    assert nombres["sin_duplicados_render"] == "ok" and nombres["sintetico_excluido"] == "ok"
    assert nombres["contrato_perfiles"] == "ok" and nombres["frescura_opendata"] == "ok"
    assert json.loads(a.leer("oro/calidad.json"))["aprobado"] is True


def test_compuerta_sin_cubo_no_aprueba(tmp_path):
    a = alm.Carpeta(tmp_path)
    reporte = calidad.evaluar(a, ahora=AHORA)
    assert reporte["aprobado"] is False
    assert reporte["checks"][0]["nombre"] == "cubo_existe"


def test_compuerta_avisa_open_data_viejo(tmp_path):
    a = alm.Carpeta(tmp_path)
    _poblar(a, con_opendata=True)
    viejo = (AHORA - timedelta(days=40)).isoformat()
    a.escribir("control/opendata.json", json.dumps({"descargado": viejo}).encode())
    from g7b_almacen import cubo
    cubo.construir(a, salida=lambda *_: None, ahora=AHORA)
    reporte = calidad.evaluar(a, ahora=AHORA)
    frescura = next(c for c in reporte["checks"] if c["nombre"] == "frescura_opendata")
    assert frescura["estado"] == "aviso" and reporte["aprobado"] is True  # aviso no reprueba


def test_latido_avanza_una_fase_por_vez(tmp_path):
    a = alm.Carpeta(tmp_path)
    # Solo mediciones de la sonda; Open Data entra por la fase de ingesta.
    for i, h in enumerate(["e1", "e1", "e2", "e2", "e3"]):
        a.escribir(f"bronce/sonda/2026-11-01/m{i}.json",
                   json.dumps(medicion(h, "N2", {"ligero": 34.0 + i, "completo": 18.0 + i, "minimo": 61.0})).encode())
    sesion = _Sesion()

    # Latido 1: ingesta (descarga Open Data).
    r1 = orquesta.paso(a, sesion=sesion, ahora=AHORA, salida=lambda *_: None)
    assert r1["fase"] == "ingesta" and r1["resultado"]["descargado"] is True
    assert a.existe("control/opendata.json") and not a.existe("oro/resumen.json")

    # Latido 2: cubo (bronce sucio → reconstruye). Todavía no hay compuerta.
    r2 = orquesta.paso(a, sesion=sesion, ahora=AHORA, salida=lambda *_: None)
    assert r2["fase"] == "cubo" and a.existe("oro/resumen.json") and not a.existe("oro/calidad.json")

    # Latido 3: calidad (compuerta). Aprueba y marca el oro confiable.
    r3 = orquesta.paso(a, sesion=sesion, ahora=AHORA, salida=lambda *_: None)
    assert r3["fase"] == "calidad" and r3["resultado"]["aprobado"] is True
    assert r3["oro_confiable"] is True and a.existe("oro/calidad.json")

    # Latido 4: nada pendiente (Open Data fresco, bronce limpio, oro revisado).
    r4 = orquesta.paso(a, sesion=sesion, ahora=AHORA, salida=lambda *_: None)
    assert r4["fase"] == "al_dia" and r4["hizo"] is False
    assert sesion.descargas == 1  # no volvió a descargar Open Data


def test_marcar_bronce_reactiva_el_cubo(tmp_path):
    a = alm.Carpeta(tmp_path)
    _poblar(a)
    from g7b_almacen import cubo
    cubo.construir(a, salida=lambda *_: None, ahora=AHORA)
    calidad.evaluar(a, ahora=AHORA)
    # Todo al día: el latido no hace nada.
    assert orquesta.paso(a, ahora=AHORA, salida=lambda *_: None)["fase"] == "al_dia"
    # Llega una medición nueva (la sonda la marca): el siguiente latido reconstruye el cubo.
    a.escribir("bronce/sonda/2026-11-02/nueva.json",
               json.dumps(medicion("e9", "N3", {"completo": 70.0})).encode())
    orquesta.marcar_bronce(a, ahora=AHORA)
    assert orquesta.paso(a, ahora=AHORA, salida=lambda *_: None)["fase"] == "cubo"


def test_ingesta_tolera_fallo_de_red(tmp_path):
    a = alm.Carpeta(tmp_path)

    class Caida:
        def get(self, *_a, **_k):
            raise ConnectionError("sin red")
        def head(self, *_a, **_k):
            raise ConnectionError("sin red")

    r = orquesta.paso(a, sesion=Caida(), ahora=AHORA, salida=lambda *_: None)
    assert r["fase"] == "ingesta" and r["resultado"]["descargado"] is False
    assert "error" in r["resultado"]  # el latido no se cayó


def test_ingesta_caida_no_frena_el_cubo(tmp_path):
    """Si Open Data no se puede bajar, el siguiente latido igual construye el cubo con la sonda."""
    a = alm.Carpeta(tmp_path)
    for i, h in enumerate(["e1", "e1", "e2", "e2", "e3"]):
        a.escribir(f"bronce/sonda/2026-11-01/m{i}.json",
                   json.dumps(medicion(h, "N2", {"ligero": 34.0 + i, "completo": 18.0 + i, "minimo": 61.0})).encode())

    class Caida:
        def get(self, *_a, **_k):
            raise ConnectionError("sin red")
        def head(self, *_a, **_k):
            raise ConnectionError("sin red")

    assert orquesta.paso(a, sesion=Caida(), ahora=AHORA, salida=lambda *_: None)["fase"] == "ingesta"
    # Mismo instante: la ingesta está en su ventana de espera, así que corre el cubo.
    assert orquesta.paso(a, sesion=Caida(), ahora=AHORA, salida=lambda *_: None)["fase"] == "cubo"
    assert orquesta.paso(a, sesion=Caida(), ahora=AHORA, salida=lambda *_: None)["fase"] == "calidad"
    assert a.existe("oro/resumen.json") and a.existe("oro/calidad.json")
