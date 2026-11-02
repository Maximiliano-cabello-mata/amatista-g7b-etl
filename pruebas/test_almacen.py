"""Pruebas del warehouse (g7b_almacen) en una carpeta local: Open Data, sonda, cubo y perfiles."""
import ast
import io
import json
import os
import zipfile
from datetime import datetime, timezone

import duckdb
import pytest

from g7b_almacen import almacen as alm
from g7b_almacen import cubo, opendata, perfiles
from g7b_almacen.__main__ import agregar_sonda

AHORA = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resultado(escena, tipo, nombre, version, muestras, fecha="2026-10-01T10:00:00"):
    return {"timestamp": fecha, "scene": {"label": escena}, "blender_version": {"version": version},
            "device_info": {"device_type": tipo, "compute_devices": [{"type": tipo, "name": nombre}],
                            "num_cpu_threads": 8},
            "system_info": {"system": "Windows", "machine": "AMD64"},
            "stats": {"samples_per_minute": muestras, "total_render_time": 60.0, "device_peak_memory": 512},
            "benchmark_launcher": {"label": "3.1.0"}}


def copia_opendata():
    lineas = [
        # Esquema reciente: data es una lista de resultados.
        {"id": "a1", "schema_version": "v4", "data": [
            _resultado("monster", "OPTIX", "NVIDIA GeForce RTX 3060", "4.2.3", 1500.0),
            _resultado("junkshop", "OPTIX", "NVIDIA GeForce RTX 3060", "4.2.3", 700.0)]},
        # data como objeto suelto, GPU integrada.
        {"id": "a2", "data": _resultado("monster", "ONEAPI", "Intel(R) Iris(R) Xe Graphics", "4.2.0", 90.0)},
        # Esquema viejo: compute_devices como lista de textos.
        {"id": "a3", "data": [{"scene": "classroom", "blender_version": "2.93.1",
                               "device_info": {"device_type": "CPU", "compute_devices": ["AMD Ryzen 5 3600"]},
                               "stats": {"render_time_no_sync": 300.5}}]},
        # Sin estadísticas: se descarta.
        {"id": "a4", "data": [{"scene": {"label": "monster"}, "stats": {}}]},
    ]
    bufer = io.BytesIO()
    with zipfile.ZipFile(bufer, "w") as zf:
        zf.writestr("opendata-20261101.jsonl", "\n".join(json.dumps(x) for x in lineas) + "\nno es json\n")
    return bufer.getvalue()


def medicion(huella, nivel, fps_vista, fecha="2026-11-01T10:00:00+00:00", version="5.2.3", sintetico=False,
             variacion=0.02):
    resultados = [{"prueba": "edicion", "perfil": None, "metrica": "segundos", "unidad": "s",
                   "valores": [1.0, 1.01, 1.02], "mediana": 1.01, "variacion": 0.02}]
    for perfil, fps in fps_vista.items():
        resultados.append({"prueba": "vista3d", "perfil": perfil, "metrica": "cuadros_por_segundo_vista3d",
                           "unidad": "fps", "valores": [fps] * 3, "mediana": fps, "variacion": variacion})
    resultados.append({"prueba": "render_cycles_gpu", "perfil": "ligero", "no_disponible": "RuntimeError: sin GPU"})
    return {"contrato": "g7b.medicion/1", "sonda": "0.2.0", "fecha": fecha, "sintetico": sintetico,
            "completa": True, "origen": "pc", "blender": {"version": version, "sin_ventana": False},
            "equipo": {"huella": huella, "nivel": nivel, "so": "Windows", "arquitectura": "AMD64",
                       "cpu": "AMD Ryzen 5 5600G", "nucleos_logicos": 12, "ram_gb": 16, "gpu_vista": "AMD Radeon",
                       "gpu_cycles": []},
            "escena": {"nombre": "media"}, "resultados": resultados}


@pytest.fixture
def almacen(tmp_path):
    a = alm.Carpeta(tmp_path / "datos")
    a.escribir("bronce/opendata/2026-11-01/opendata-20261101.zip", copia_opendata())
    # N2: cinco corridas de tres equipos; con perfil ligero la vista 3D pasa de 30 fps.
    for i, huella in enumerate(["e1", "e1", "e2", "e2", "e3"]):
        datos = medicion(huella, "N2", {"completo": 18.0 + i, "ligero": 34.0 + i, "minimo": 61.0})
        a.escribir(f"bronce/sonda/2026-11-01/m{i}.json", json.dumps(datos).encode())
    # N1: un solo equipo y ni el mínimo es fluido.
    a.escribir("bronce/sonda/2026-11-01/n1.json",
               json.dumps(medicion("v1", "N1", {"ligero": 8.0, "minimo": 14.0})).encode())
    # Variable (> 10 %): no cuenta para perfiles.
    a.escribir("bronce/sonda/2026-11-01/var.json",
               json.dumps(medicion("v2", "N3", {"completo": 90.0}, variacion=0.4)).encode())
    # Sintética: nunca entra, aunque por error esté en bronce.
    a.escribir("bronce/sonda/2026-11-01/sin.json",
               json.dumps(medicion("s1", "N4", {"completo": 500.0}, sintetico=True)).encode())
    a.escribir("bronce/sonda/2026-11-01/roto.json", b"{")
    return a


def test_enlace_mas_reciente():
    html = '<a href="/snapshots/opendata-20261030.zip">x</a> <a href="opendata-20261101.zip">y</a>'
    assert opendata.encontrar_enlace(html, "https://opendata.blender.org/download/") == \
        "https://opendata.blender.org/download/opendata-20261101.zip"
    assert opendata.encontrar_enlace('<a href="/s/opendata-latest.zip">') == "https://opendata.blender.org/s/opendata-latest.zip"
    with pytest.raises(RuntimeError):
        opendata.encontrar_enlace("<html></html>")


def test_lectura_tolerante_de_open_data():
    filas = list(opendata.filas_render(opendata.leer_registros(copia_opendata())))
    assert len(filas) == 4
    por_escena = {(f["escena"], f["dispositivo"]): f for f in filas}
    rtx = por_escena[("monster", "NVIDIA GeForce RTX 3060")]
    assert rtx["clase_dispositivo"] == "gpu_dedicada" and rtx["version_corta"] == "4.2"
    assert por_escena[("monster", "Intel(R) Iris(R) Xe Graphics")]["clase_dispositivo"] == "gpu_integrada"
    viejo = por_escena[("classroom", "AMD Ryzen 5 3600")]
    assert viejo["clase_dispositivo"] == "cpu" and viejo["tiempo_render_s"] == 300.5
    assert viejo["version_corta"] == "2.93" and viejo["muestras_por_minuto"] is None


def test_clase_de_dispositivo():
    assert opendata.clase_dispositivo("METAL", "Apple M2") == "gpu_integrada"
    assert opendata.clase_dispositivo("METAL", "Apple M2 Max") == "gpu_dedicada"
    assert opendata.clase_dispositivo("HIP", "AMD Radeon RX 6600") == "gpu_dedicada"
    assert opendata.clase_dispositivo("HIP", "AMD Radeon(TM) Graphics") == "gpu_integrada"
    assert opendata.clase_dispositivo("CPU", "Intel Core i5") == "cpu"


def test_construir_cubo_y_perfiles(almacen):
    datos = cubo.construir(almacen, salida=lambda *_: None, ahora=AHORA)
    assert datos["conteos"]["renders_opendata"] == 4
    assert datos["conteos"]["corridas_sonda"] == 7  # la sintética no entra; la rota tampoco
    for ruta in ("plata/opendata/render.parquet", "plata/sonda/medicion.parquet", "oro/cubo.duckdb",
                 "oro/parquet/hechos_medicion.parquet", "oro/csv/v_render_por_clase.csv",
                 "oro/resumen.json", "oro/perfiles.json"):
        assert almacen.existe(ruta), ruta

    con = duckdb.connect(os.path.join(almacen.raiz, "oro/cubo.duckdb"), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM hechos_render").fetchone()[0] == 4
        assert con.execute("SELECT count(*) FROM dim_dispositivo WHERE fuente = 'sonda'").fetchone()[0] == 5
        assert con.execute("SELECT count(*) FROM hechos_medicion WHERE calidad = 'no_disponible'").fetchone()[0] == 7
        assert con.execute("SELECT es_lts FROM dim_version WHERE clave_version = '4.2'").fetchone()[0] is True
        tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
        assert "plata_render" not in tablas and {"v_salud", "v_render_por_clase"} <= tablas
    finally:
        con.close()

    documento = json.loads(almacen.leer("oro/perfiles.json"))
    assert perfiles.validar(documento) == []
    por_nivel = {p["nivel"]: p for p in documento["perfiles"]}
    assert set(por_nivel) == {"N1", "N2"}  # N3 era variable y N4 sintética
    n2 = por_nivel["N2"]
    assert n2["perfil"] == "ligero" and n2["estado"] == "confiable" and n2["criterio"] == "vista3d"
    assert n2["evidencia"] == {"mediciones": 5, "equipos": 3} and n2["fps_esperados"] == 36.0
    assert n2["ajustes"] == perfiles.AJUSTES["ligero"]
    n1 = por_nivel["N1"]
    assert n1["perfil"] == "minimo" and n1["estado"] == "provisional" and n1["nota"] == "ni el perfil mínimo es fluido"

    resumen = json.loads(almacen.leer("oro/resumen.json"))
    assert resumen["perfiles"] == 2 and resumen["render_por_clase"] == []  # menos de 20 renders por celda
    assert any(e["nivel"] == "N2" for e in resumen["equipos_sonda"])


def test_construir_sin_datos(tmp_path):
    a = alm.Carpeta(tmp_path)
    datos = cubo.construir(a, salida=lambda *_: None, ahora=AHORA)
    assert datos["conteos"]["renders_opendata"] == 0 and datos["perfiles"] == 0
    assert json.loads(a.leer("oro/perfiles.json"))["perfiles"] == []


def test_ajustes_iguales_a_la_sonda():
    arbol = ast.parse(open(os.path.join(RAIZ, "sonda", "g7b_sonda.py"), encoding="utf-8").read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", "") == "PERFILES":
            assert ast.literal_eval(nodo.value) == perfiles.AJUSTES
            return
    pytest.fail("la sonda ya no define PERFILES")


class _Respuesta:
    def __init__(self, contenido=b"", texto="", cabeceras=None):
        self.content, self.text, self.headers = contenido, texto, cabeceras or {}

    def raise_for_status(self):
        pass


class _Sesion:
    def __init__(self):
        self.descargas = 0

    def get(self, url, **_):
        if url.endswith("/download/"):
            return _Respuesta(texto='<a href="https://x.org/opendata-20261101.zip">')
        self.descargas += 1
        return _Respuesta(contenido=copia_opendata())

    def head(self, url, **_):
        return _Respuesta(cabeceras={"ETag": '"abc"'})


def test_descarga_y_sin_cambios(tmp_path):
    a = alm.Carpeta(tmp_path)
    sesion = _Sesion()
    ruta = opendata.descargar(a, sesion=sesion, salida=lambda *_: None)
    assert ruta.startswith("bronce/opendata/") and ruta.endswith("opendata-20261101.zip")
    assert opendata.descargar(a, sesion=sesion, salida=lambda *_: None) is None
    assert sesion.descargas == 1
    assert opendata.ultima_copia(a) == ruta


def test_agregar_sonda(tmp_path):
    resultados = tmp_path / "resultados"
    resultados.mkdir()
    (resultados / "real.json").write_text(json.dumps(medicion("e1", "N2", {"ligero": 40.0})))
    (resultados / "sint.json").write_text(json.dumps(medicion("s", "N2", {"ligero": 40.0}, sintetico=True)))
    (resultados / "otra.json").write_text(json.dumps({"contrato": "otro"}))
    a = alm.Carpeta(tmp_path / "datos")
    assert agregar_sonda(a, str(resultados), salida=lambda *_: None) == \
        {"agregadas": 2, "ya_existian": 0, "rechazadas": 1}
    assert a.existe("bronce/sonda/2026-11-01/real.json") and a.existe("sintetico/sonda/2026-11-01/sint.json")
    assert agregar_sonda(a, str(resultados), salida=lambda *_: None)["ya_existian"] == 2


def test_carpeta_no_sale_de_su_raiz(tmp_path):
    a = alm.Carpeta(tmp_path)
    with pytest.raises(ValueError):
        a.escribir("../fuera.txt", b"x")
    assert a.escribir("bronce/x/a.txt", b"1") and not a.escribir("bronce/x/a.txt", b"2")
    assert a.leer("bronce/x/a.txt") == b"1"
