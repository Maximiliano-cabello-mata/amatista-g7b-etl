import json
from pathlib import Path

import duckdb
import pytest

from herramientas.revisar_calibracion_site import revisar as revisar_site
from herramientas.revisar_lote_telemetria import revisar as revisar_cubo


DATOS = Path(__file__).resolve().parents[1] / "algoritmos/documentacion"


@pytest.fixture
def piloto():
    return tuple(json.loads((DATOS / nombre).read_text(encoding="utf-8")) for nombre in
                 ("resultados-site-4.1.json", "auditoria.json"))


def test_piloto_versionado(piloto):
    r = revisar_site(*piloto)
    assert (r["bloques_utiles"], r["bloques_revisados"]) == (64, 70)
    assert (r["paginas_con_candidatos"], r["paginas_visitadas"]) == (46, 131)
    assert (r["reserva"]["k"], r["reserva"]["n"]) == (20, 24)
    assert r["reserva"]["inferior95"] == pytest.approx(0.676229273)
    assert r["reserva"]["habilitada"] is False


@pytest.mark.parametrize("cambio", ["etiqueta", "id", "reserva", "censo", "decision"])
def test_evidencia_incoherente(piloto, cambio):
    informe, etiquetas = piloto
    if cambio == "etiqueta":
        informe["evidencia"][0]["util"] = "false"
    elif cambio == "id":
        informe["evidencia"].append(informe["evidencia"][0])
    elif cambio == "reserva":
        seleccion = next(f for f in etiquetas if f["modelo"] == informe["modelo"])
        seleccion["util"] = not seleccion["util"]
    elif cambio == "censo":
        informe["censo_de_bloques"]["k"] -= 1
    else:
        informe["calibracion_paginas_ineditas"]["habilitada"] = True
    with pytest.raises(ValueError):
        revisar_site(informe, etiquetas)


def test_sin_reserva(piloto):
    informe, _ = piloto
    informe["calibracion_paginas_ineditas"].update(
        k=0, n=0, precision=None, inferior_95_unilateral=0, habilitada=False)
    assert revisar_site(informe, [])["reserva"] == {
        "n": 0, "k": 0, "inferior95": 0.0, "habilitada": False}


def test_reserva_supera_umbral(piloto):
    informe, etiquetas = piloto
    for f in informe["evidencia"]:
        f["util"] = True
    for f in etiquetas:
        f["util"] = True
    informe["censo_de_bloques"].update(k=70, utilidad=1.0)
    informe["calibracion_paginas_ineditas"].update(
        k=24, precision=1.0, inferior_95_unilateral=0.8986898185110513, habilitada=True)
    assert revisar_site(informe, etiquetas)["reserva"]["habilitada"] is True


def test_cubo_vacio_y_mediciones_defectuosas(tmp_path):
    ruta = tmp_path / "cubo.duckdb"
    with duckdb.connect(str(ruta)) as con:
        con.execute("CREATE TABLE mediciones (id VARCHAR, unidad VARCHAR, valor DOUBLE, fuente VARCHAR, estado VARCHAR)")
    assert revisar_cubo(ruta)["filas"] == 0
    with duckdb.connect(str(ruta)) as con:
        con.executemany("INSERT INTO mediciones VALUES (?, ?, ?, ?, ?)", [
            ("a", "s", 1, "sonda", "aceptado"), ("a", " ", None, "sonda", "revision"),
            ("", "s", float("inf"), "sonda", "revision")])
    assert revisar_cubo(ruta) == {
        "filas": 3, "ids_distintos": 1, "sin_id": 1, "repeticiones_de_id": 1,
        "sin_unidad": 1, "sin_valor_finito": 2, "por_fuente_y_estado": [
            {"fuente": "sonda", "estado": "aceptado", "filas": 1},
            {"fuente": "sonda", "estado": "revision", "filas": 2}]}


def test_cubo_ausente_o_incompatible(tmp_path):
    ruta = tmp_path / "ausente.duckdb"
    with pytest.raises(FileNotFoundError):
        revisar_cubo(ruta)
    assert not ruta.exists()
    with duckdb.connect(str(ruta)) as con:
        con.execute("CREATE TABLE otro (id VARCHAR)")
    with pytest.raises(duckdb.Error):
        revisar_cubo(ruta)
