"""Paquete de conocimiento (g7b.geoda.paquete/1) y núcleo público de Geoda (geoda.nucleo/1)."""
import json
from datetime import datetime, timezone

import duckdb
import pytest

from geoda import conformidad, paquete as paq
from geoda.__main__ import main as cli
from geoda.nucleo import Nucleo

AHORA = datetime(2026, 11, 17, tzinfo=timezone.utc)


def _cubo_relativo():
    """Un v_relativas mínimo: 40 N2 integradas a 100 y 40 N4 dedicadas a 1300 (5.2, classroom)."""
    con = duckdb.connect()
    con.execute("""CREATE TABLE v_relativas (fuente VARCHAR, mide VARCHAR, nivel VARCHAR, serie VARCHAR,
                   escena VARCHAR, gpu_clase VARCHAR, nivel_confianza VARCHAR, valor DOUBLE)""")
    filas = [("blender-open-data", "gpu", "N2", "5.2", "classroom", "integrada", "alta", 100.0)] * 40 + \
            [("blender-open-data", "gpu", "N4", "5.2", "classroom", "dedicada", "alta", 1300.0)] * 40 + \
            [("blender-open-data", "gpu", "N4", "5.2", "classroom", "servidor", "alta", 9999.0)] * 40 + \
            [("blender-open-data", "gpu", "N3", "5.2", "classroom", "dedicada", "alta", 500.0)] * 5
    con.executemany("INSERT INTO v_relativas VALUES (?,?,?,?,?,?,?,?)", filas)
    return con


def test_paquete_de_solo_reglas_es_valido_y_determinista():
    a, b = paq.construir(ahora=AHORA), paq.construir(ahora=AHORA)
    assert a == b and a["contrato"] == paq.CONTRATO
    assert {p["estado"] for p in a["perfiles"]["perfiles"]} == {"base"}
    assert a["factores"] == [] and a["evidencia"]["citas_verificadas"] == 0


def test_factores_relativos_sin_servidores_ni_celdas_chicas():
    factores = paq.factores_relativos(_cubo_relativo())
    assert [(f["nivel"], f["factor_frente_a_N2"]) for f in factores] == [("N2", 1.0), ("N4", 13.0)]
    assert all(f["clase_dato"] == "relativa" for f in factores)


def test_paquete_alterado_o_con_datos_de_equipos_se_rechaza():
    p = paq.construir(ahora=AHORA)
    p["factores"] = [{"nivel": "N4", "clase_dato": "relativa"}]
    assert "la sección factores no coincide con su huella" in paq.validar(p)
    p = paq.construir(ahora=AHORA)
    p["perfiles"]["perfiles"][0]["nota"] = "hostname pc-01"
    p["huellas"]["perfiles"] = paq.huella(p["perfiles"])
    assert any("hostname" in e for e in paq.validar(p))
    with pytest.raises(ValueError):
        Nucleo(p)


def test_citas_verificadas_con_el_inventario():
    rutas = {"render/eevee/index.html", "render/cycles/render_settings/simplify.html"}
    citas = paq.citas({"4.5": rutas})
    enlace = citas["acciones"]["scene.render.engine"][0]["enlaces"]
    assert {(e["version"], e["verificada"]) for e in enlace if e["idioma"] == "es"} == {
        ("5.2", "sin_verificar"), ("4.5", "inventario"), ("3.6", "sin_verificar")}


def test_inventarios_del_manual_sin_red_no_inventan():
    def abrir(url):
        raise OSError("sin red")
    assert paq.inventarios_manual(abrir=abrir) == {}


def test_nucleo_decide_con_evidencia_citas_y_estimacion_relativa():
    nucleo = Nucleo(paq.construir(_cubo_relativo(), ahora=AHORA))
    plan = nucleo.decidir(nucleo.huella(gpu="NVIDIA GeForce RTX 4070", ram_gb=32, opengl=4.6))
    assert plan["clasificacion"]["nivel"] == "N4"
    assert plan["evidencia"]["escalera"] == "regla_base"
    relativa = plan["evidencia"]["estimacion_relativa"]
    assert relativa["clase_dato"] == "relativa" and relativa["factor_frente_a_N2"] == 13.0
    assert "no una medición de tu equipo" in relativa["texto"]
    engine = next(a for a in plan["acciones"] if a["ruta"] == "scene.render.engine")
    assert engine["citas"][0]["url"] == "https://docs.blender.org/manual/es/4.5/render/cycles/index.html"
    assert plan["kernel"]["api"] == "geoda.nucleo/1"


def test_nucleo_gpu_con_la_tabla_del_paquete():
    nucleo = Nucleo(paq.construir(ahora=AHORA))
    assert nucleo.gpu("Intel(R) UHD Graphics 620")["clase"] == "integrada"
    assert nucleo.gpu("NVIDIA GeForce RTX 3060 Laptop GPU")["vram_gb"] == 6
    assert nucleo.gpu("Algo raro")["clase"] == "desconocida"


def test_conformidad_pasa_con_reglas_y_con_datos():
    assert conformidad.correr()["fallas"] == 0
    assert conformidad.correr(paq.construir(_cubo_relativo(), ahora=AHORA))["fallas"] == 0


def test_cli_paquete_plan_y_conformidad(tmp_path, capsys):
    ruta, equipo = tmp_path / "paquete.json", tmp_path / "equipo.json"
    assert cli(["paquete", "--salida", str(ruta)]) == 0
    equipo.write_text(json.dumps({"ram_gb": 8, "opengl": 4.6,
                                  "gpus": [{"nombre": "Intel UHD 620", "tipo": "integrada"}]}))
    capsys.readouterr()
    assert cli(["plan", "--paquete", str(ruta), "--huella", str(equipo), "--idioma", "en"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["clasificacion"]["nivel"] == "N2" and plan["ayuda"][0]["idioma"] == "en"
    assert cli(["conformidad", "--paquete", str(ruta)]) == 0


def test_publicar_paquete_en_el_lago_solo_si_cambia(tmp_path):
    from g7b_almacen.paquete_geoda import PUNTERO, publicar
    from g7b_lago.memoria import LagoMemoria

    lago, publico = LagoMemoria(), tmp_path / "publicacion" / "geoda_paquete.json"
    documento = paq.construir(ahora=AHORA)
    puntero = publicar(lago, documento, publico)
    assert puntero["ruta"] == f"oro/geoda/{documento['version']}/paquete.json"
    assert lago.leer_json(PUNTERO)["sha256"] == puntero["sha256"]
    assert Nucleo.desde_archivo(publico).info()["paquete"] == documento["version"]
    assert publicar(lago, paq.construir(ahora=datetime(2026, 11, 18, tzinfo=timezone.utc))) is None
