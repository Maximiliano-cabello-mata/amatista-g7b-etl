"""Un lago en memoria con la misma interfaz que Lago: para pruebas y para «geodar probar».

Respeta las mismas reglas que el lago real: zonas válidas y bronce sin sobrescribir.
"""
import gzip
import io
import json

from .lago import ZONAS


class LagoMemoria:
    def __init__(self):
        self.archivos = {}

    @staticmethod
    def _validar(ruta):
        if ruta.split("/", 1)[0] not in ZONAS:
            raise ValueError(f"La ruta debe empezar con una zona {ZONAS}: {ruta}")

    def existe(self, ruta):
        return ruta in self.archivos

    def subir_bytes(self, ruta, datos, tipo="application/octet-stream", codificacion=None,
                    metadatos=None, sobrescribir=False):
        self._validar(ruta)
        if ruta.startswith("bronce/"):
            sobrescribir = False
        if ruta in self.archivos and not sobrescribir:
            return False
        self.archivos[ruta] = bytes(datos)
        return True

    def subir_jsonl_gz(self, ruta, registros, metadatos=None):
        bufer = io.BytesIO()
        cantidad = 0
        with gzip.GzipFile(fileobj=bufer, mode="wb", mtime=0) as gz:
            for registro in registros:
                gz.write((json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
                cantidad += 1
        return self.subir_bytes(ruta, bufer.getvalue()), cantidad

    def leer_jsonl_gz(self, ruta):
        crudo = self.archivos[ruta]
        if crudo[:2] == b"\x1f\x8b":
            crudo = gzip.decompress(crudo)
        return [json.loads(linea) for linea in crudo.decode("utf-8").splitlines() if linea.strip()]

    def leer_json(self, ruta, por_omision=None):
        if ruta not in self.archivos:
            return por_omision
        return json.loads(self.archivos[ruta])

    def escribir_json(self, ruta, datos):
        self.subir_bytes(ruta, json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"), sobrescribir=True)

    def listar(self, prefijo=""):
        return sorted(r for r in self.archivos if r.startswith(prefijo))
