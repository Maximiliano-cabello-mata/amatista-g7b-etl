"""Validaciones de seguridad y catálogo de ofertas (sin acceso a Azure)."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from g7b_ops.auditoria import auditar, validar_configuracion
from herramientas.validar_catalogo import validar

RAIZ = Path(__file__).resolve().parents[1]


def test_catalogo_cubre_pack_y_no_inventa_conexiones():
    datos = json.loads((RAIZ / "infra/ofertas/catalogo.json").read_text())
    assert len(datos["ofertas"]) >= 80
    assert validar(datos) == []
    assert not any(x["conectado"] for x in datos["ofertas"])
    assert all(x["responsable"] == "administrador_g7b" for x in datos["ofertas"])


def test_catalogo_no_permite_falsa_conexion():
    datos = json.loads((RAIZ / "infra/ofertas/catalogo.json").read_text())
    datos["ofertas"][0]["conectado"] = True
    assert any("Conexión no comprobada" in x for x in validar(datos))


def test_auditoria_usa_solo_url_sin_sas():
    assert validar_configuracion({
        "AZURE_STORAGE_ACCOUNT_URL": "https://g7blagoejemplo.blob.core.windows.net",
        "AZURE_CONTAINER_NAME": "lago",
    }) == ("https://g7blagoejemplo.blob.core.windows.net", "lago")


@pytest.mark.parametrize("variables", [
    {"AZURE_STORAGE_ACCOUNT_URL": "http://lago.blob.core.windows.net"},
    {"AZURE_STORAGE_ACCOUNT_URL": "https://lago.blob.core.windows.net/lago?sig=xx"},
    {"AZURE_STORAGE_ACCOUNT_URL": "https://lago.blob.core.windows.net", "AZURE_LAGO_URL": "secreto"},
    {"AZURE_STORAGE_ACCOUNT_URL": "https://lago.blob.core.windows.net", "AZURE_STORAGE_KEY": "secreto"},
    {"AZURE_STORAGE_ACCOUNT_URL": "https://sitio-no-azure.invalid"},
])
def test_auditoria_rechaza_urls_y_secretos(variables):
    with pytest.raises(ValueError):
        validar_configuracion(variables)


def test_auditoria_no_lee_cuerpos_de_blobs():
    clase = MagicMock()
    clase.get_container_client.return_value.list_blobs.return_value = [
        type("Blob", (), {"name": "bronce/sonda/a.json", "size": 100})(),
        type("Blob", (), {"name": "oro/cubo.duckdb", "size": 4096})(),
        type("Blob", (), {"name": "tmp/exp/medicion.json", "size": 80})(),
    ]
    result = auditar(clase, "lago")
    assert result["objetos_inspeccionados"] == 3
    by = {x["zona"]: x for x in result["por_zona"]}
    assert by["bronce"]["objetos"] == 1
    assert by["oro"]["bytes"] == 4096
    assert by["tmp"]["objetos"] == 1
    clase.get_container_client.return_value.download_blob.assert_not_called()


def test_bicep_despliegue_guardado_y_sin_acceso_publico():
    bicep = (RAIZ / "infra/azure/g7b-control-privado.bicep").read_text()
    assert "provisionCompute bool = false" in bicep
    assert "triggerType: 'Manual'" in bicep
    assert "SystemAssigned" in bicep
    assert "Microsoft.Authorization/roleAssignments" in bicep
    assert "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1" in bicep
    assert "ingress:" not in bicep
    bash = (RAIZ / "infra/azure/validar_y_aprovisionar.sh").read_text()
    assert "G7B_ROTACION_CONFIRMADA" in bash
    assert "G7B_PRESUPUESTO_REVISADO" in bash
    assert "az deployment group what-if" in bash
