"""Radar de telemetría: estándar g7b.hardware/1, Open Data por tandas, reportes de error y la separación
de responsabilidades con las arañas de documentación. Sin red."""
import json
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from g7b_ingesta import catalogo as cat
from g7b_ingesta.red import Respuesta
from g7b_ingesta.sensores import sensor_gitea_issues, sistema_de_reporte
from g7b_telemetria import hardware
from g7b_telemetria.capturar import capturar_incremental, opendata, seleccionar_opendata


# --- Estándar de hardware ----------------------------------------------------------------------

@pytest.mark.parametrize("nombre,clase,vram,fabricante", [
    ("Intel(R) UHD Graphics 620", "integrada", None, "intel"),
    ("Mesa Intel(R) HD Graphics 520 (SKL GT2)", "integrada", None, "intel"),
    ("Intel(R) Arc(TM) Graphics", "integrada", None, "intel"),
    ("Intel(R) Arc(TM) A770 Graphics", "dedicada", None, "intel"),
    ("AMD Radeon 780M", "integrada", None, "amd"),
    ("AMD Radeon(TM) Graphics", "integrada", None, "amd"),
    ("Apple M1", "integrada", None, "apple"),
    ("NVIDIA GeForce RTX 3060 Laptop GPU", "dedicada", 6, "nvidia"),
    ("NVIDIA GeForce RTX 3060", "dedicada", None, "nvidia"),   # 8 o 12 GB: no se adivina
    ("NVIDIA GeForce RTX 4090", "dedicada", 24, "nvidia"),
    ("NVIDIA GeForce GTX 1650", "dedicada", 4, "nvidia"),
    ("NVIDIA GeForce MX450", "dedicada", 2, "nvidia"),
    ("AMD Radeon RX 6600", "dedicada", 8, "amd"),
    ("Tarjeta Inventada 9000", "desconocida", None, "desconocido"),
])
def test_gpu_se_lee_igual_venga_de_donde_venga(nombre, clase, vram, fabricante):
    g = hardware.gpu(nombre)
    assert (g["clase"], g["vram_gb"], g["fabricante"]) == (clase, vram, fabricante)
    assert "(R)" not in g["nombre"] and "(TM)" not in g["nombre"]


def test_nivel_con_las_reglas_de_geoda():
    assert hardware.de_benchmark(["Intel(R) UHD Graphics 620"], "ONEAPI")["nivel"] == "N2"
    assert hardware.de_benchmark(["NVIDIA GeForce RTX 4090"], "OPTIX")["nivel"] == "N4"
    assert hardware.de_benchmark(["NVIDIA GeForce RTX 3060 Laptop GPU"], "OPTIX")["nivel"] == "N3"
    sin_vram = hardware.de_benchmark(["NVIDIA GeForce RTX 3060"], "CUDA")
    assert sin_vram["nivel"] == "N3" and sin_vram["confianza"] == "baja"  # lo dice, no lo esconde
    # Una integrada con OpenGL viejo (dato de un reporte de error) baja a N1.
    assert hardware.nivel([hardware.gpu("Intel HD Graphics 3000")], opengl=3.3)["nivel"] == "N1"


def test_benchmark_de_cpu_no_inventa_la_gpu():
    b = hardware.de_benchmark(["AMD Ryzen 9 5950X 16-Core Processor"], "CPU", "Linux")
    assert b["mide"] == "cpu" and b["nivel"] is None and b["cpus"][0]["familia"] == "Ryzen"
    desconocida = hardware.de_benchmark(["Tarjeta Inventada 9000"], "OPTIX")
    assert desconocida["nivel"] is None and "no se adivina" in desconocida["motivos"][0]


def test_opendata_lleva_el_bloque_hardware():
    fila = opendata(registro(1, "2026-11-01T00:00:00Z", gpu="NVIDIA GeForce RTX 3060 Laptop GPU"))[0]
    assert fila["hardware"]["estandar"] == "g7b.hardware/1" and fila["hardware"]["nivel"] == "N3"


# --- Open Data completo, por tandas -------------------------------------------------------------

def registro(i, creado, gpu="NVIDIA GeForce RTX 4060"):
    return {"schema_version": "v4", "id": f"00000000-0000-0000-0000-{i:012d}", "created_at": creado,
            "data": [{"blender_version": {"version": "4.2.0"}, "scene": {"label": "monster"},
                      "system_info": {"system": "Windows"},
                      "device_info": {"device_type": "OPTIX", "compute_devices": [{"name": gpu}]},
                      "stats": {"samples_per_minute": 100 + i}}]}


def archivo(n, inicio=datetime(2022, 3, 1, tzinfo=timezone.utc)):
    # Como el snapshot real: del más viejo al más nuevo, más un registro de esquema viejo.
    filas = [registro(i, (inicio + timedelta(days=i)).isoformat()) for i in range(n)]
    return filas + [{"schema_version": "v3", "id": "x"}]


def ids(seleccion):
    return [int(d["id"][-12:]) for d in seleccion]


def test_primera_tanda_trae_lo_mas_reciente_no_lo_mas_viejo():
    seleccion, estado, conteos = seleccionar_opendata(archivo(10), {}, limite=3)
    assert ids(seleccion) == [9, 8, 7]                      # antes: [0, 1, 2], marzo de 2022
    assert conteos["esquema_no_soportado"] == 1 and estado["completo_hacia_atras"] is False
    assert estado["hasta"].startswith("2022-03-10") and estado["desde"].startswith("2022-03-08")


def test_tandas_siguientes_traen_lo_nuevo_y_siguen_hacia_atras_sin_huecos():
    _, estado, _ = seleccionar_opendata(archivo(10), {}, limite=3)          # 9, 8, 7
    seleccion, estado, conteos = seleccionar_opendata(archivo(12), estado, limite=4)
    assert ids(seleccion) == [10, 11, 6, 5]                 # lo nuevo primero, luego hacia atrás
    assert conteos["ya_capturados"] == 3
    vistos = {5, 6, 7, 8, 9, 10, 11}
    while not estado["completo_hacia_atras"]:
        seleccion, estado, _ = seleccionar_opendata(archivo(12), estado, limite=2)
        assert not vistos & set(ids(seleccion))             # nunca dos veces lo mismo
        vistos |= set(ids(seleccion))
    assert vistos == set(range(12))                         # y al final, todo el archivo
    assert seleccionar_opendata(archivo(12), estado, limite=5)[0] == []


def test_registros_con_la_misma_fecha_en_el_borde_no_se_pierden():
    misma = "2026-01-01T00:00:00+00:00"
    filas = [registro(i, misma) for i in range(5)]
    vistos = set()
    estado = {}
    for _ in range(5):
        seleccion, estado, _ = seleccionar_opendata(filas, estado, limite=2)
        vistos |= set(ids(seleccion))
    assert vistos == set(range(5))


class LagoMemoria:
    def __init__(self):
        self.archivos, self.json = {}, {}

    def subir_jsonl_gz(self, ruta, registros, **_):
        self.archivos[ruta] = list(registros)

    def leer_jsonl_gz(self, ruta):
        return self.archivos[ruta]

    def leer_json(self, ruta, por_omision=None):
        return self.json.get(ruta, por_omision)

    def escribir_json(self, ruta, datos):
        self.json[ruta] = datos


def test_captura_incremental_guarda_el_estado_al_final(tmp_path):
    lago = LagoMemoria()
    informe = capturar_incremental(archivo(6), lago, tmp_path, limite=4)
    assert informe["conteos"]["registros_validos"] == 4 and informe["tramo"]["completo_hacia_atras"] is False
    estado = lago.json["control/telemetria/blender-open-data.json"]
    assert estado["capturados"] == 4 and estado["ultima_captura"]
    filas = [f for ruta, fs in lago.archivos.items() if ruta.startswith("plata/") for f in fs]
    assert all(f["hardware"]["nivel"] == "N3" for f in filas)
    informe = capturar_incremental(archivo(6), lago, tmp_path, limite=4)
    assert informe["conteos"]["registros_validos"] == 2
    assert capturar_incremental(archivo(6), lago, tmp_path, limite=4)["nada_nuevo"] is True


def test_el_cubo_agrupa_el_render_por_nivel(tmp_path):
    from g7b_almacen.cubo import construir

    lago = LagoMemoria()
    capturar_incremental(archivo(3) + [registro(50, "2026-11-01T00:00:00Z", gpu="Intel(R) UHD Graphics 620")],
                         lago, tmp_path / "cap", limite=10)
    entradas = [(ruta, f) for ruta, fs in lago.archivos.items() if ruta.startswith("plata/") for f in fs]
    construir(entradas, tmp_path / "cubo")
    with duckdb.connect(str(tmp_path / "cubo/oro/cubo.duckdb"), read_only=True) as con:
        niveles = dict(con.execute("SELECT nivel, sum(mediciones) FROM v_render_por_nivel GROUP BY 1").fetchall())
    assert niveles == {"N3": 3, "N2": 1}


# --- Reportes de error de Blender (telemetría de fallas) ----------------------------------------

PLANTILLA = """**System Information**
Operating system: Windows-11-10.0.22631-SP0 64 Bits
Graphics card: Intel(R) UHD Graphics 620 Intel 4.6.0 - Build 31.0.101.2111

**Blender Version**
Broken: version: 4.2.0, branch: blender-v4.2-release, commit date: 2024-07-16 06:20, hash: `a51f293548ad`
Worked: 3.6.5

Short description of error: el viewport parpadea al entrar a modo edición.
"""


def test_plantilla_de_reporte_a_campos_estructurados():
    s = sistema_de_reporte(PLANTILLA)
    assert (s["version_rota"], s["version_funcionaba"], s["opengl"]) == ("4.2.0", "3.6.5", 4.6)
    assert s["hardware"]["gpus"][0]["clase"] == "integrada" and s["hardware"]["nivel"] == "N2"
    assert "parpadea" not in json.dumps(s)                  # el texto del autor no se guarda
    vacio = sistema_de_reporte("Sin plantilla")
    assert vacio["hardware"] is None and vacio["version_rota"] is None


FUENTE = {"id": "blender-reportes", "sensor": {"tipo": "gitea_issues", "base": "https://projects.blender.org",
                                               "repo": "blender/blender", "etiquetas": ["Type/Report"],
                                               "por_pagina": 2, "peticiones": 6, "ventana_horas": 24,
                                               "dias_iniciales": 2}}
AHORA = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def reporte(n, actualizado, cuerpo=PLANTILLA, pr=False):
    return {"number": n, "title": f"Falla {n}", "html_url": f"https://projects.blender.org/blender/blender/issues/{n}",
            "created_at": "2026-11-01T00:00:00Z", "updated_at": actualizado, "state": "open",
            "labels": [{"name": "Type/Report"}, {"name": "Module/Viewport & EEVEE"}], "comments": 2,
            "body": cuerpo, "pull_request": {} if pr else None}


def servidor(por_ventana, vistas, lleno=False):
    """Responde según la ventana pedida (since); con lleno=True, toda página viene completa."""
    from urllib.parse import parse_qs, urlparse

    def obtener(url, _cabeceras):
        q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        vistas.append(q)
        if lleno:
            base = int(q["page"]) * 10
            return Respuesta(200, {}, json.dumps([reporte(base, q["since"]), reporte(base + 1, q["since"])]).encode())
        lote = por_ventana.get(q["since"], []) if q["page"] == "1" else []
        return Respuesta(200, {}, json.dumps(lote).encode())
    return obtener


def test_sensor_de_reportes_avanza_por_ventanas_de_tiempo():
    vistas = []
    por_ventana = {"2026-11-15T12:00:00Z": [reporte(1, "2026-11-15T13:00:00Z")],
                   "2026-11-16T12:00:00Z": [reporte(2, "2026-11-16T13:00:00Z", pr=True),
                                            reporte(3, "2026-11-16T14:00:00Z", cuerpo="sin plantilla")]}
    salida, estado = sensor_gitea_issues(FUENTE, {}, servidor(por_ventana, vistas), ahora=AHORA)
    assert [r["id"] for r in salida["registros"]] == ["1", "3"]           # sin pull requests
    # La segunda ventana trajo una página llena (2 de 2): pide la página 2 antes de darla por terminada.
    assert [(v["since"], v["before"], v["page"]) for v in vistas] == [
        ("2026-11-15T12:00:00Z", "2026-11-16T12:00:00Z", "1"),
        ("2026-11-16T12:00:00Z", "2026-11-17T12:00:00Z", "1"), ("2026-11-16T12:00:00Z", "2026-11-17T12:00:00Z", "2")]
    assert vistas[0]["labels"] == "Type/Report" and "2 ventanas completas" in salida["nota"]
    assert salida["registros"][0]["datos"]["hardware"]["nivel"] == "N2" and "1 con GPU" in salida["nota"]
    assert estado["desde"].startswith("2026-11-17T12:00")
    # Una hora después: solo esa hora, y lo que no cambió no se repite.
    vistas.clear()
    por_ventana = {"2026-11-17T12:00:00Z": [reporte(1, "2026-11-15T13:00:00Z")]}
    salida, _ = sensor_gitea_issues(FUENTE, estado, servidor(por_ventana, vistas), ahora=AHORA + timedelta(hours=1))
    assert len(vistas) == 1 and salida["registros"] == []


def test_si_una_ventana_se_llena_no_avanza_y_la_parte_a_la_mitad():
    vistas = []
    salida, estado = sensor_gitea_issues(FUENTE, {}, servidor({}, vistas, lleno=True), ahora=AHORA)
    assert len(vistas) == 6                                                 # nunca más que el tope
    assert estado["desde"].startswith("2026-11-15T12:00") and estado["ventana_horas"] == 12
    assert len(salida["registros"]) == 12


# --- Separación de responsabilidades -------------------------------------------------------------

def base(**cambios):
    f = {"id": "x", "nombre": "x", "tipo": "mediciones", "licencia": "CC0-1.0", "licencia_verificada": True,
         "modo": "agregados", "preguntas": ["P1"], "sensor": {"tipo": "externo"}, "extractor": "telemetria",
         "colector": "blender_open_data", "frecuencia_horas": 168, "dominios": [], "activa": True,
         "familia": "F1", "destino": "telemetria"}
    return {**f, **cambios}


@pytest.mark.parametrize("cambios,error", [
    ({"extractor": "zyte", "zyte": {}, "sensor": {"tipo": "pagina", "url": "https://x"}},
     "las arañas de Zyte son solo para documentación"),
    ({"colector": None}, "necesita colector"),
    ({"colector": "pendiente"}, "no puede estar activa sin colector"),
    ({"extractor": "descarga"}, "la telemetría la trae el radar"),
])
def test_el_catalogo_obliga_la_separacion(cambios, error):
    errores = cat.validar({"fuentes": [base(**cambios)]})
    assert any(error in e for e in errores), errores


def test_catalogo_real_respeta_la_separacion():
    catalogo = cat.cargar()
    for f in catalogo["fuentes"]:
        if f["extractor"] == "zyte":
            assert cat.destino(f) == "documentos", f["id"]
    radar = {f["id"] for f in cat.de_telemetria(catalogo)}
    assert "blender-open-data" in radar and not radar & {f["id"] for f in cat.vigilables(catalogo)}


def test_geodar_telemetria_aisla_fallas_y_salud_las_ve(monkeypatch, tmp_path):
    import geodar.__main__ as g

    lago = LagoMemoria()
    monkeypatch.setitem(g.COLECTORES, "blender_open_data",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("HTTP 403")))
    resultados = g.telemetria(cat.cargar(), lago, str(tmp_path), imprimir=lambda *_: None)
    assert resultados[0]["ok"] is False
    estado = lago.json["control/telemetria/blender-open-data.json"]
    assert "HTTP 403" in estado["ultimo_error"]
    informe = g.salud(cat.cargar(), {}, telemetria={"blender-open-data": estado})
    assert {"fuente": "blender-open-data", "veredicto": "error"}.items() <= next(
        f for f in informe if f["fuente"] == "blender-open-data").items()


def test_mapa_dice_quien_hace_que():
    import geodar.__main__ as g

    texto = g.mapa_markdown(cat.cargar(), hoy="2026-11-17")
    assert "## Quién hace qué" in texto and "radar de telemetría" in texto
    assert "araña de documentación (Zyte)" in texto


def test_colector_de_open_data_crea_su_carpeta_y_lee_el_zip(tmp_path, monkeypatch):
    import zipfile

    import geodar.__main__ as g
    from g7b_telemetria import capturar as cap

    def descargar(destino):  # como la descarga real, escribe dentro de la carpeta de salida
        with zipfile.ZipFile(destino, "w") as z:
            z.writestr("LICENSE.txt", "CC0 1.0 Universal")
            z.writestr("data.jsonl", "\n".join(json.dumps(r) for r in archivo(4)) + "\n")

    monkeypatch.setattr(cap, "descargar", descargar)
    salida = tmp_path / "no" / "existe"
    informe = g.colector_blender_open_data({}, None, str(salida), 3, simulacro=True)
    assert informe["conteos"]["registros_validos"] == 3 and informe["simulacro"] is True
