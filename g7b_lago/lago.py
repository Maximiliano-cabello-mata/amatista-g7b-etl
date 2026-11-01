"""Acceso al lago: un contenedor de Azure Blob Storage con zonas por prefijo.

    bronce/<fuente>/<AAAA-MM-DD>/<nombre>   crudo, tal como llegó (ELT: nunca se modifica)
    plata/...                               validado
    oro/...                                 curado
    sintetico/...                           datos generados, nunca se mezclan (PLAN 5.7)
    control/...                             estado de los trabajos (qué ya se procesó)
    tmp/...                                 se borra solo a los 7 días

Credenciales, en este orden:
    AZURE_LAGO_URL                URL del contenedor con su firma SAS (lo que imprime infra/azure/crear_lago.sh)
    AZURE_STORAGE_CONNECTION_STRING + AZURE_LAGO_CONTENEDOR (por omisión "lago"); sirve para Azurite en pruebas
"""
import gzip
import io
import json
import os
from datetime import date

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import ContainerClient, ContentSettings

ZONAS = ("bronce", "plata", "oro", "sintetico", "control", "tmp")


def ruta_bronce(fuente, nombre, dia=None):
    dia = dia or date.today()
    return f"bronce/{fuente}/{dia.isoformat()}/{nombre}"


class Lago:
    def __init__(self, contenedor: ContainerClient):
        self.contenedor = contenedor

    @classmethod
    def desde_entorno(cls):
        url = os.environ.get("AZURE_LAGO_URL")
        if url:
            return cls(ContainerClient.from_container_url(url))
        conexion = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if conexion:
            nombre = os.environ.get("AZURE_LAGO_CONTENEDOR", "lago")
            return cls(ContainerClient.from_connection_string(conexion, nombre))
        raise RuntimeError("Falta AZURE_LAGO_URL (o AZURE_STORAGE_CONNECTION_STRING para pruebas).")

    @staticmethod
    def _validar(ruta):
        zona = ruta.split("/", 1)[0]
        if zona not in ZONAS:
            raise ValueError(f"La ruta debe empezar con una zona {ZONAS}: {ruta}")

    def existe(self, ruta):
        return self.contenedor.get_blob_client(ruta).exists()

    def subir_bytes(self, ruta, datos, tipo="application/octet-stream", codificacion=None,
                    metadatos=None, sobrescribir=False):
        """Sube un archivo. En bronce no se sobrescribe nunca: si ya existe, devuelve False."""
        self._validar(ruta)
        if ruta.startswith("bronce/"):
            sobrescribir = False
        ajustes = ContentSettings(content_type=tipo, content_encoding=codificacion)
        try:
            self.contenedor.upload_blob(ruta, datos, overwrite=sobrescribir, content_settings=ajustes,
                                        metadata={k: str(v) for k, v in (metadatos or {}).items()})
            return True
        except ResourceExistsError:
            return False

    def subir_jsonl_gz(self, ruta, registros, metadatos=None):
        """Sube registros como JSON Lines comprimido. Devuelve (subido, cantidad)."""
        bufer = io.BytesIO()
        cantidad = 0
        with gzip.GzipFile(fileobj=bufer, mode="wb", mtime=0) as gz:
            for registro in registros:
                gz.write((json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
                cantidad += 1
        datos = {**(metadatos or {}), "registros": cantidad}
        subido = self.subir_bytes(ruta, bufer.getvalue(), tipo="application/x-ndjson",
                                  codificacion="gzip", metadatos=datos)
        return subido, cantidad

    def leer_jsonl_gz(self, ruta):
        crudo = self.contenedor.download_blob(ruta).readall()
        # El SDK puede descomprimir solo (el archivo se guarda con Content-Encoding: gzip).
        if crudo[:2] == b"\x1f\x8b":
            crudo = gzip.decompress(crudo)
        texto = crudo.decode("utf-8")
        return [json.loads(linea) for linea in texto.splitlines() if linea.strip()]

    def leer_json(self, ruta, por_omision=None):
        try:
            return json.loads(self.contenedor.download_blob(ruta).readall())
        except ResourceNotFoundError:
            return por_omision

    def escribir_json(self, ruta, datos):
        self.subir_bytes(ruta, json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"),
                         tipo="application/json", sobrescribir=True)

    def listar(self, prefijo=""):
        return [b.name for b in self.contenedor.list_blobs(name_starts_with=prefijo)]
