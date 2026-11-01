"""Pruebas del lago contra Azurite (el emulador oficial de Azure Storage).

    npx azurite-blob --silent --inMemoryPersistence &
    AZURE_PRUEBAS_CONEXION="UseDevelopmentStorage=true" python -m pytest pruebas -q

Sin AZURE_PRUEBAS_CONEXION, estas pruebas se saltan.
"""
import json
import os
import uuid

import pytest

CONEXION = os.environ.get("AZURE_PRUEBAS_CONEXION")
pytestmark = pytest.mark.skipif(not CONEXION, reason="sin Azurite (AZURE_PRUEBAS_CONEXION)")


@pytest.fixture
def lago():
    from azure.storage.blob import BlobServiceClient

    from g7b_lago import Lago

    servicio = BlobServiceClient.from_connection_string(CONEXION)
    contenedor = servicio.create_container(f"prueba{uuid.uuid4().hex[:12]}")
    yield Lago(contenedor)
    contenedor.delete_container()


class TrabajoFalso:
    def __init__(self, registros):
        self.items = type("Items", (), {"iter": lambda _self: iter(registros)})()


class ClienteZyteFalso:
    """Imita lo que usa zyte_a_lago de python-scrapinghub."""

    def __init__(self, trabajos):
        self.trabajos = trabajos  # clave -> (meta, registros)

    def get_project(self, _id):
        trabajos = self.trabajos
        return type("Proyecto", (), {"jobs": type("Jobs", (), {
            "iter": lambda _self, **_kw: iter([meta for meta, _ in trabajos.values()])})()})()

    def get_job(self, clave):
        return TrabajoFalso(self.trabajos[clave][1])


def _trabajo(clave, registros, terminado=1793500000000):
    return clave, ({"key": clave, "spider": "blender_docs", "finished_time": terminado, "close_reason": "finished"},
                   registros)


def test_bronce_no_se_sobrescribe(lago):
    assert lago.subir_bytes("bronce/x/2026-11-01/a.txt", b"uno")
    assert not lago.subir_bytes("bronce/x/2026-11-01/a.txt", b"dos", sobrescribir=True)
    assert lago.contenedor.download_blob("bronce/x/2026-11-01/a.txt").readall() == b"uno"


def test_zona_obligatoria(lago):
    with pytest.raises(ValueError):
        lago.subir_bytes("cualquier/cosa.txt", b"x")


def test_zyte_copia_una_vez_con_procedencia(lago):
    from g7b_lago.zyte_a_lago import CONTROL, copiar

    registros = [{"titulo": "Python API", "enlace": "https://docs.blender.org/a"},
                 {"titulo": "Add-ons", "enlace": "https://docs.blender.org/b"}]
    cliente = ClienteZyteFalso(dict([_trabajo("883618/1/7", registros)]))

    primero = copiar(cliente, "883618", lago, salida=lambda *_: None)
    assert primero == {"pendientes": 1, "copiados": 1, "registros": 2, "ya_existian": 0}
    ruta = "bronce/zyte/blender_docs/2026-11-01/883618-1-7.jsonl.gz"
    copia = lago.leer_jsonl_gz(ruta)
    assert [r["titulo"] for r in copia] == ["Python API", "Add-ons"]
    assert copia[0]["_g7b"]["trabajo"] == "883618/1/7" and len(copia[0]["_g7b"]["huella"]) == 64
    assert "883618/1/7" in lago.leer_json(CONTROL)["copiados"]

    segundo = copiar(cliente, "883618", lago, salida=lambda *_: None)
    assert segundo["pendientes"] == 0 and segundo["copiados"] == 0


def test_zyte_simulacro_no_escribe(lago):
    from g7b_lago.zyte_a_lago import copiar

    cliente = ClienteZyteFalso(dict([_trabajo("883618/1/8", [{"a": 1}])]))
    resumen = copiar(cliente, "883618", lago, simulacro=True, salida=lambda *_: None)
    assert resumen["pendientes"] == 1 and lago.listar() == []


def test_mediciones_reales_y_sinteticas(lago, tmp_path):
    from g7b_lago.subir_mediciones import subir

    real = {"contrato": "g7b.medicion/1", "fecha": "2026-11-01T05:00:00+00:00", "sintetico": False,
            "completa": True, "equipo": {"huella": "abc", "nivel": "N2"}}
    falsa = {**real, "sintetico": True}
    (tmp_path / "real.json").write_text(json.dumps(real))
    (tmp_path / "falsa.json").write_text(json.dumps(falsa))
    (tmp_path / "otra.json").write_text(json.dumps({"contrato": "otro/1"}))

    resumen = subir(str(tmp_path), lago, salida=lambda *_: None)
    assert resumen == {"subidas": 2, "ya_existian": 0, "rechazadas": 1, "incompletas": 0}
    assert lago.listar("bronce/sonda/2026-11-01/") == ["bronce/sonda/2026-11-01/real.json"]
    assert lago.listar("sintetico/sonda/2026-11-01/") == ["sintetico/sonda/2026-11-01/falsa.json"]
    assert subir(str(tmp_path), lago, salida=lambda *_: None)["ya_existian"] == 2
