"""La prueba de Blender no escribe en las zonas de producción de Azure."""
import hashlib
import json

import pytest

from g7b_lago.prueba_blender_aislada import subir_prueba


class _Descarga:
    def __init__(self, datos):
        self.datos = datos

    def readall(self):
        return self.datos


class _Contenedor:
    def __init__(self, blobs):
        self.blobs = blobs

    def download_blob(self, ruta):
        return _Descarga(self.blobs[ruta])


class _LagoFalso:
    def __init__(self):
        self.blobs = {}
        self.contenedor = _Contenedor(self.blobs)

    def subir_bytes(self, ruta, datos, tipo, sobrescribir):
        assert ruta.startswith("tmp/pruebas-blender/")
        assert not sobrescribir
        if ruta in self.blobs:
            return False
        self.blobs[ruta] = datos
        return True


def _medicion():
    return {
        "contrato": "g7b.medicion/1", "origen": "actions",
        "sintetico": False, "completa": True,
        "blender": {"version": "4.5.15"}, "escena": {"nombre": "ligera"},
        "resultados": [
            {"prueba": "edicion", "mediana": 0.25, "unidad": "s"},
            {"prueba": "vista3d", "no_disponible": "requiere ventana"},
        ],
    }


def test_subida_aislada_verifica_bytes_y_no_toca_oro(tmp_path):
    f = tmp_path / "medicion.json"
    f.write_text(json.dumps(_medicion()))
    lago = _LagoFalso()
    reporte = subir_prueba(lago, f, "12345", "1")
    assert reporte["estado"] == "verificado"
    assert reporte["pruebas_medidas"] == 1
    assert reporte["pruebas_no_disponibles"] == 1
    assert sorted(lago.blobs) == [
        "tmp/pruebas-blender/12345-intento1/medicion.json",
        "tmp/pruebas-blender/12345-intento1/verificacion.json",
    ]
    assert reporte["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    assert subir_prueba(lago, f, "12345", "1")["estado"] == "verificado"


@pytest.mark.parametrize("cambio", [
    {"contrato": "otro"},
    {"origen": "pc"},
    {"sintetico": True},
    {"completa": False},
    {"resultados": []},
    {"resultados": [{"no_disponible": "sin GPU"}]},
])
def test_rechaza_mediciones_invalidas_antes_de_subir(tmp_path, cambio):
    m = {**_medicion(), **cambio}
    f = tmp_path / "medicion.json"
    f.write_text(json.dumps(m))
    lago = _LagoFalso()
    with pytest.raises(ValueError):
        subir_prueba(lago, f, "123", "1")
    assert lago.blobs == {}


@pytest.mark.parametrize("run_id,intento", [
    ("../oro", "1"),
    ("123", "../../publicado"),
    ("", "1"),
    ("abcd", "1"),
])
def test_no_admite_rutas_fuera_de_la_prueba(tmp_path, run_id, intento):
    f = tmp_path / "medicion.json"
    f.write_text(json.dumps(_medicion()))
    lago = _LagoFalso()
    with pytest.raises(ValueError):
        subir_prueba(lago, f, run_id, intento)
    assert lago.blobs == {}
