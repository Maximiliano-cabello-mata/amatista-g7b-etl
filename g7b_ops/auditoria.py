"""Diagnóstico G7B en Azure: únicamente metadatos, nunca contenido ni SAS.

Se ejecuta dentro de Azure Container Apps Jobs con identidad administrada
y el rol Storage Blob Data Reader limitado al contenedor lago.
No intenta cambiar blobs ni publicar nada.
"""
import json
import os
import sys
from collections import Counter
from urllib.parse import urlsplit

ZONAS = ("bronce", "plata", "oro", "sintetico", "control", "tmp")


def validar_configuracion(entorno):
    url = (entorno.get("AZURE_STORAGE_ACCOUNT_URL") or "").strip()
    contenedor = (entorno.get("AZURE_CONTAINER_NAME") or "lago").strip()
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not parsed.hostname.endswith(".blob.core.windows.net")):
        raise ValueError("AZURE_STORAGE_ACCOUNT_URL debe ser la URL HTTPS pública de la cuenta, SIN firma SAS")
    if not contenedor or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in contenedor):
        raise ValueError("Nombre de contenedor no válido")
    if any(entorno.get(k) for k in ("AZURE_LAGO_URL", "AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_KEY")):
        raise ValueError("No se aceptan llaves ni SAS en el proceso de diagnóstico")
    return url, contenedor


def auditar(cliente, contenedor, max_blobs=10000):
    """Solo enumera rutas y tamaños; no recupera cuerpos ni metadatos privados."""
    conteo = Counter()
    bytes_zonas = Counter()
    listado = cliente.get_container_client(contenedor)
    total = 0
    limite = False
    for blob in listado.list_blobs():
        total += 1
        if total > max_blobs:
            limite = True
            break
        nombre = blob.name
        zona = nombre.split("/", 1)[0]
        if zona not in ZONAS:
            zona = "no_clasificada"
        conteo[zona] += 1
        bytes_zonas[zona] += int(blob.size or 0)
    return {
        "contrato": "g7b.auditoria/1",
        "alcance": "solo_metadatos",
        "contenedor": contenedor,
        "objetos_inspeccionados": min(total, max_blobs),
        "limite_alcanzado": limite,
        "por_zona": [
            {"zona": zona, "objetos": conteo[zona], "bytes": bytes_zonas[zona]}
            for zona in (*ZONAS, "no_clasificada")
        ],
    }


def main():
    try:
        url, contenedor = validar_configuracion(os.environ)
    except ValueError as exc:
        print(f"Configuración inválida: {exc}", file=sys.stderr)
        return 2
    from azure.identity import ManagedIdentityCredential
    from azure.storage.blob import BlobServiceClient
    # La prueba debe acreditar la identidad del Job, no otra credencial ambiental.
    identidad = ManagedIdentityCredential()
    cliente = BlobServiceClient(account_url=url, credential=identidad)
    resultado = auditar(cliente, contenedor)
    print("G7B_AZURE_DIAGNOSTICO", json.dumps(resultado, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
