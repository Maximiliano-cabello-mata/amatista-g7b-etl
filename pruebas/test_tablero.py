"""Verificación del tablero HTML sin servidor ni fuga de identificadores de máquinas."""
import json

import duckdb
import pytest

from g7b_almacen.tablero import extraer, generar


@pytest.fixture
def piezas(tmp_path):
    cubo = tmp_path / "cubo.duckdb"
    con = duckdb.connect(str(cubo))
    con.execute("""
        CREATE TABLE hechos_medicion (
            medicion_id VARCHAR, clave_dispositivo VARCHAR, fecha DATE,
            origen VARCHAR, nivel_medido VARCHAR, escena VARCHAR, prueba VARCHAR,
            perfil VARCHAR, metrica VARCHAR, unidad VARCHAR, mediana DOUBLE,
            variacion DOUBLE, repeticiones INTEGER, calidad VARCHAR,
            motivo VARCHAR, sin_ventana BOOLEAN
        )
    """)
    con.execute("""
        INSERT INTO hechos_medicion VALUES
        ('m1','HIDDEN_FINGERPRINT','2026-11-02','actions','N2','ligera','animacion',
         'ligero','fps','fps',534.5414,0.03,3,'ok',NULL,true),
        ('m1','HIDDEN_FINGERPRINT','2026-11-02','actions','N2','ligera','vista3d',
         'ligero','fps','fps',NULL,NULL,3,'no_disponible','requiere ventana',true)
    """)
    con.execute("CREATE TABLE hechos_render AS SELECT 1 AS render_id WHERE false")
    con.execute("CREATE VIEW v_salud AS SELECT 'sonda' AS fuente, calidad, count(*) AS filas FROM hechos_medicion GROUP BY calidad")
    con.execute("""
        CREATE VIEW v_medicion_por_nivel AS SELECT nivel_medido AS nivel, prueba,
         perfil, median(mediana) AS mediana FROM hechos_medicion GROUP BY ALL
    """)
    con.close()
    ruta_resumen = tmp_path / "resumen.json"
    ruta_resumen.write_text(json.dumps({"conteos": {"corridas_sonda": 1}}))
    ruta_perfiles = tmp_path / "perfiles.json"
    ruta_perfiles.write_text(json.dumps({
        "contrato": "g7b.perfil/1",
        "perfiles": [{
            "nivel": "N2", "blender": "4.5", "perfil": "ligero",
            "ajustes": {"subsurf": 1, "simplify": False, "muestras": 16, "res_pct": 75},
            "estado": "provisional", "criterio": "animacion", "fps_esperados": 534.54,
            "evidencia": {"mediciones": 1, "equipos": 1},
            "nota": "</script><script>alert(1)</script>"
        }]
    }))
    ruta_calidad = tmp_path / "calidad.json"
    ruta_calidad.write_text(json.dumps({
        "aprobado": True, "generado": "2026-11-02T03:03:05+00:00",
        "revisadas": 1, "avisos": 0, "fallas": 0,
        "checks": [{"nombre": "volumen", "estado": "ok", "detalle": "1 corrida"}]
    }))
    return cubo, ruta_resumen, ruta_perfiles, ruta_calidad


def test_vista_real_de_duckdb(piezas):
    d = extraer(*piezas)
    assert d["conteos"] == {
        "filas": 2, "corridas": 1, "equipos": 1, "renders": 0,
        "validas": 1, "no_disponibles": 1
    }
    assert len(d["mediciones"]) == 2
    assert d["mediciones"][0]["origen"] == "actions"
    assert d["perfiles"][0]["estado"] == "provisional"
    assert "HIDDEN_FINGERPRINT" not in json.dumps(d)


def test_html_autonomo_seguro_y_exportable(piezas, tmp_path):
    salida = tmp_path / "tablero.html"
    generar(*piezas, salida)
    texto = salida.read_text(encoding="utf-8")
    assert "<!doctype html>" in texto
    assert 'const D = {"version_tablero":' in texto
    assert "__G7B_DATOS_JSON__" not in texto
    assert "HIDDEN_FINGERPRINT" not in texto
    assert "</script><script>alert(1)</script>" not in texto
    assert r"\u003c/script\u003e" in texto
    for identificador in ("k-filas", "chart", "download-csv", "view-perfiles", "checks-all"):
        assert identificador in texto


def test_tablero_exige_calidad_aprobada(piezas):
    cubo, resumen, perfiles, calidad = piezas
    calidad.write_text(json.dumps({"aprobado": False, "checks": []}))
    with pytest.raises(ValueError, match="calidad rechazada"):
        extraer(cubo, resumen, perfiles, calidad)
