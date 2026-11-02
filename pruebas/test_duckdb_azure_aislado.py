"""Pruebas de integración real de DuckDB y límites de aislamiento de Azure."""
import hashlib
import json

import pytest

from g7b_lago.prueba_duckdb_aislada import construir_y_subir, ORIGEN


class _Respuesta:
    def __init__(self, datos):
        self.datos = datos

    def readall(self):
        return self.datos


class _Contenedor:
    def __init__(self, almacen):
        self.almacen = almacen

    def download_blob(self, ruta):
        return _Respuesta(self.almacen[ruta])


class _LagoFalso:
    def __init__(self, datos):
        self.blobs = dict(datos)
        self.escrituras = []
        self.contenedor = _Contenedor(self.blobs)

    def subir_bytes(self, ruta, datos, tipo, sobrescribir=False):
        assert ruta.startswith("tmp/pruebas-duckdb/"), ruta
        assert not sobrescribir
        self.escrituras.append(ruta)
        if ruta in self.blobs:
            return False
        self.blobs[ruta] = datos
        return True


def _entrada():
    medicion = {
        "contrato": "g7b.medicion/1",
        "sonda": "0.2.0",
        "origen": "actions",
        "sintetico": False,
        "completa": True,
        "fecha": "2026-11-02T02:51:41+00:00",
        "blender": {"version": "4.5.15 LTS", "sin_ventana": True},
        "equipo": {
            "huella": "test-runner-1", "nivel": "N2", "nivel_estimado": True,
            "cpu": "Prueba x64", "so": "Linux", "arquitectura": "x86_64",
            "nucleos_logicos": 4, "ram_gb": 16, "gpu_vista": {}, "gpu_cycles": []
        },
        "escena": {"nombre": "ligera"},
        "resultados": [
            {"prueba": "edicion", "perfil": None, "metrica": "tiempo_edicion",
             "unidad": "s", "valores": [0.09, 0.10, 0.10],
             "mediana": 0.10, "variacion": 0.10},
            {"prueba": "animacion", "perfil": "ligero",
             "metrica": "cuadros_por_segundo_animacion", "unidad": "fps",
             "valores": [520, 531, 534], "mediana": 531, "variacion": 0.026},
            {"prueba": "vista3d", "perfil": "ligero",
             "no_disponible": "RuntimeError: requiere ventana"}
        ]
    }
    datos = json.dumps(medicion).encode()
    carpeta = ORIGEN
    control = {
        "estado": "verificado", "archivo": carpeta + "/medicion.json",
        "sha256": hashlib.sha256(datos).hexdigest(),
    }
    return {
        carpeta + "/medicion.json": datos,
        carpeta + "/verificacion.json": json.dumps(control).encode(),
    }


def test_de_blender_real_a_duckdb_y_parquet_en_tmp():
    lago = _LagoFalso(_entrada())
    reporte = construir_y_subir(lago, "987654", "1")
    assert reporte["estado"] == "verificado"
    assert reporte["corridas"] == 1
    assert reporte["hechos_medicion"] == 3
    assert reporte["calidad"]["aprobado"] is True
    assert reporte["perfiles"][0]["estado"] == "provisional"
    assert reporte["conteos"]["renders_opendata"] == 0
    prefijo = "tmp/pruebas-duckdb/987654-intento1/"
    for ruta in [
        "oro/cubo.duckdb",
        "plata/sonda/medicion.parquet",
        "oro/perfiles.json",
        "oro/resumen.json",
        "oro/calidad.json",
        "publicado/actual.json",
        "verificacion_duckdb.json",
    ]:
        assert prefijo + ruta in lago.blobs
    assert all(x.startswith(prefijo) for x in lago.escrituras)
    assert len(lago.blobs[prefijo + "oro/cubo.duckdb"]) > 1024
    assert lago.blobs[prefijo + "plata/sonda/medicion.parquet"][:4] == b"PAR1"


def test_cambio_de_sha_rechazado_sin_subidas():
    blobs = _entrada()
    blobs[ORIGEN + "/medicion.json"] += b" "
    lago = _LagoFalso(blobs)
    with pytest.raises(ValueError, match="ha cambiado"):
        construir_y_subir(lago, "987654", "1")
    assert lago.escrituras == []


@pytest.mark.parametrize("run_id,intento", [
    ("../oro", "1"), ("123", "../../oro"), ("0", "1"), ("", "1")
])
def test_no_puede_escribir_en_zonas_productivas(run_id, intento):
    lago = _LagoFalso(_entrada())
    with pytest.raises(ValueError):
        construir_y_subir(lago, run_id, intento)
    assert lago.escrituras == []
