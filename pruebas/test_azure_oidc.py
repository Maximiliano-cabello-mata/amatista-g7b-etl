"""Identidad OIDC en Actions, retrocompatibilidad SAS y defensa ante URL mal formada."""
import pytest

from g7b_lago import lago as modulo


class ClienteFalso:
    llamadas = []

    def __init__(self, **kwargs):
        self.llamadas.append(("oidc", kwargs))

    @classmethod
    def from_container_url(cls, url):
        cls.llamadas.append(("sas", url))
        return object()

    @classmethod
    def from_connection_string(cls, cadena, contenedor):
        cls.llamadas.append(("conexion", cadena, contenedor))
        return object()


def _preparar(monkeypatch):
    ClienteFalso.llamadas = []
    monkeypatch.setattr(modulo, "ContainerClient", ClienteFalso)
    monkeypatch.setattr(modulo, "credencial_azure", lambda: "identidad-oidc")
    for nombre in ("AZURE_STORAGE_ACCOUNT_URL", "AZURE_LAGO_CONTENEDOR",
                   "AZURE_LAGO_URL", "AZURE_STORAGE_CONNECTION_STRING"):
        monkeypatch.delenv(nombre, raising=False)


def test_oidc_gana_a_sas_caducada(monkeypatch):
    _preparar(monkeypatch)
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "https://g7blago09b52a0e.blob.core.windows.net")
    monkeypatch.setenv("AZURE_LAGO_URL", "https://caducada?sig=vieja")
    modulo.Lago.desde_entorno()
    assert ClienteFalso.llamadas == [("oidc", {
        "account_url": "https://g7blago09b52a0e.blob.core.windows.net",
        "container_name": "lago", "credential": "identidad-oidc",
    })]


@pytest.mark.parametrize("url", [
    "http://g7blago09b52a0e.blob.core.windows.net",
    "https://g7blago09b52a0e.ejemplo.net",
    "https://g7blago09b52a0e.blob.core.windows.net/ruta",
    "https://g7blago09b52a0e.blob.core.windows.net?token=1",
])
def test_rechaza_cuentas_mal_configuradas(monkeypatch, url):
    _preparar(monkeypatch)
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", url)
    with pytest.raises(ValueError, match="Blob HTTPS"):
        modulo.Lago.desde_entorno()
    assert ClienteFalso.llamadas == []


def test_sas_de_legacy_y_azurite_siguen_funcionando(monkeypatch):
    _preparar(monkeypatch)
    monkeypatch.setenv("AZURE_LAGO_URL", "https://storage.blob.core.windows.net/lago?sig=falsa")
    modulo.Lago.desde_entorno()
    assert ClienteFalso.llamadas[0][0] == "sas"
    _preparar(monkeypatch)
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
    modulo.Lago.desde_entorno()
    assert ClienteFalso.llamadas[0] == ("conexion", "UseDevelopmentStorage=true", "lago")
