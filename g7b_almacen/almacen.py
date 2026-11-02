"""Dónde viven los archivos del warehouse.

Las dos implementaciones tienen la misma forma de rutas que el lago (``bronce/...``, ``plata/...``,
``oro/...``), así que el mismo código corre en tu PC, en Deepnote o en GitHub Actions contra Azure.

    Carpeta("datos")          una carpeta local; sirve sin nube y para las pruebas
    EnLago(Lago.desde_entorno())   el contenedor de Azure (g7b_lago)
"""
import os


class Carpeta:
    def __init__(self, raiz):
        self.raiz = os.path.abspath(raiz)

    def _ruta(self, ruta):
        completa = os.path.abspath(os.path.join(self.raiz, ruta))
        if not completa.startswith(self.raiz + os.sep):
            raise ValueError(f"Ruta fuera del almacén: {ruta}")
        return completa

    def listar(self, prefijo=""):
        base = self._ruta(prefijo) if prefijo else self.raiz
        if os.path.isfile(base):
            return [prefijo]
        carpeta = base if os.path.isdir(base) else os.path.dirname(base)
        if not os.path.isdir(carpeta):
            return []
        nombres = []
        for actual, _dirs, archivos in os.walk(carpeta):
            for archivo in archivos:
                relativa = os.path.relpath(os.path.join(actual, archivo), self.raiz).replace(os.sep, "/")
                if relativa.startswith(prefijo):
                    nombres.append(relativa)
        return sorted(nombres)

    def existe(self, ruta):
        return os.path.exists(self._ruta(ruta))

    def leer(self, ruta):
        with open(self._ruta(ruta), "rb") as f:
            return f.read()

    def escribir(self, ruta, datos, sobrescribir=True, tipo=None):
        destino = self._ruta(ruta)
        if ruta.startswith("bronce/"):
            sobrescribir = False  # bronce es crudo: nunca se modifica (ELT)
        if os.path.exists(destino) and not sobrescribir:
            return False
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        temporal = destino + ".tmp"
        with open(temporal, "wb") as f:
            f.write(datos)
        os.replace(temporal, destino)
        return True

    def descargar(self, ruta, destino):
        """Copia un archivo a una ruta local (para DuckDB, que lee archivos)."""
        with open(destino, "wb") as f:
            f.write(self.leer(ruta))


class EnLago:
    """Adaptador del lago de Azure (g7b_lago.Lago) a la misma interfaz que Carpeta."""

    def __init__(self, lago):
        self.lago = lago

    def listar(self, prefijo=""):
        return sorted(self.lago.listar(prefijo))

    def existe(self, ruta):
        return self.lago.existe(ruta)

    def leer(self, ruta):
        return self.lago.contenedor.download_blob(ruta).readall()

    def escribir(self, ruta, datos, sobrescribir=True, tipo=None):
        return self.lago.subir_bytes(ruta, datos, tipo=tipo or _tipo(ruta), sobrescribir=sobrescribir)

    def descargar(self, ruta, destino):
        with open(destino, "wb") as f:
            self.lago.contenedor.download_blob(ruta).readinto(f)


def _tipo(ruta):
    extension = ruta.rsplit(".", 1)[-1].lower()
    return {
        "json": "application/json", "csv": "text/csv", "parquet": "application/vnd.apache.parquet",
        "zip": "application/zip", "jsonl": "application/x-ndjson", "duckdb": "application/octet-stream",
        "html": "text/html",
    }.get(extension, "application/octet-stream")


def desde_entorno(carpeta=None):
    """Una carpeta si se indica; si no, el lago (AZURE_LAGO_URL)."""
    if carpeta:
        return Carpeta(carpeta)
    from g7b_lago import Lago  # importa el SDK de Azure solo si hace falta

    return EnLago(Lago.desde_entorno())
