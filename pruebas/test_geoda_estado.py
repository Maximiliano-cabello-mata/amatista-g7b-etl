"""Pruebas aisladas del puente: no necesitan Azure ni MongoDB reales."""
import json

import pytest

from g7b_almacen.cubo import ACTUAL, CONTRATO, sha
from g7b_almacen.geoda_estado import generar, estado_del_cubo


class LagoFalso:
    def __init__(self, **cambios):
        self.version = "20261103T202349Z-prueba"
        self.manifiesto = {
            "contrato": CONTRATO, "estado": "verificado", "version": self.version,
            "mediciones": 3003, "calidad": {"aceptado": 3, "revision": 3000},
            "recomendaciones_habilitadas": False,
            "archivos": {"oro/cubo.duckdb": {
                "ruta": f"oro/cubos/{self.version}/cubo.duckdb", "sha256": "a" * 64,
            }},
        }
        self.manifiesto.update(cambios)
        self.datos = json.dumps(self.manifiesto).encode()
        self.puntero = {
            "contrato": CONTRATO, "version": self.version,
            "manifiesto": f"oro/cubos/{self.version}/manifiesto.json",
            "cubo": f"oro/cubos/{self.version}/cubo.duckdb",
            "sha256": sha(self.datos),
        }
        self.contenedor = self

    def leer_json(self, ruta):
        assert ruta == ACTUAL
        return self.puntero

    def download_blob(self, ruta):
        assert ruta == self.puntero["manifiesto"]
        return type("Respuesta", (), {"readall": lambda _self: self.datos})()


def test_publicacion_usa_solo_conteos_y_no_inventa_perfiles():
    feed = generar(LagoFalso(), 992)
    assert feed["contrato"] == "g7b.geoda.estado/1"
    assert feed["cubo"] == {
        "version": "20261103T202349Z-prueba", "mediciones": 3003,
        "aceptadas": 3, "revision": 3000, "recomendaciones_habilitadas": False,
    }
    assert feed["conocimiento"]["documentos"] == 992
    assert feed["perfiles"] == []
    assert "huella" not in json.dumps(feed).lower()


def test_no_publica_cuando_el_manifiesto_cambia():
    lago = LagoFalso()
    lago.datos += b" "
    with pytest.raises(ValueError, match="integridad"):
        generar(lago, 900)


@pytest.mark.parametrize("cambios", [
    {"estado": "pendiente"},
    {"version": "otra"},
    {"mediciones": 500},
    {"recomendaciones_habilitadas": True},
])
def test_no_publica_cubo_no_verificado_o_inconsistente(cambios):
    with pytest.raises(ValueError):
        generar(LagoFalso(**cambios), 992)


def test_no_publica_conteos_falsos():
    with pytest.raises(ValueError):
        generar(LagoFalso(), -1)
    with pytest.raises(ValueError):
        generar(LagoFalso(), True)


def test_no_publica_si_se_desvia_puntero():
    lago = LagoFalso()
    lago.puntero["manifiesto"] = "../secreto"
    with pytest.raises(ValueError, match="ruta"):
        estado_del_cubo(lago)
