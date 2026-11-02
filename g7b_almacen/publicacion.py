"""Publicación versionada de resultados aprobados por la compuerta de calidad.

`oro/` contiene el candidato del pipeline (puede estar incompleto).
Los consumidores, incluido Amatista, SOLO deben leer el manifiesto
`publicado/actual.json` y los archivos versionados a los que apunta.

El puntero se escribe en último lugar: una validación fallida no reemplaza
la publicación anterior. No se envían datos de estudiantes a G7B.
"""
import hashlib
import json
from datetime import datetime, timezone

PUNTERO = "publicado/actual.json"
ORIGENES = {
    "perfiles": "oro/perfiles.json",
    "resumen": "oro/resumen.json",
    "calidad": "oro/calidad.json",
}


def _hash(datos):
    return hashlib.sha256(datos).hexdigest()


def publicar(almacen, reporte):
    """Publica un snapshot solo si pasó calidad. Devuelve el manifiesto."""
    if not reporte.get("aprobado") or any(
        c.get("estado") == "falla" for c in reporte.get("checks", [])
    ):
        raise ValueError("La compuerta de calidad no aprobó la publicación")
    contenidos = {}
    for nombre, ruta in ORIGENES.items():
        if not almacen.existe(ruta):
            raise ValueError(f"Falta el archivo obligatorio {ruta}")
        contenidos[nombre] = almacen.leer(ruta)
    calidad = json.loads(contenidos["calidad"])
    if not calidad.get("aprobado"):
        raise ValueError("El reporte de calidad almacenado no está aprobado")
    if calidad.get("generado") != reporte.get("generado"):
        raise ValueError("El reporte de calidad cambió antes de publicar")

    # ID de contenido: repetir la operación con los mismos bytes es idempotente.
    firma = _hash(b"".join(
        nombre.encode() + b"\0" + contenidos[nombre] + b"\0"
        for nombre in sorted(contenidos)
    ))[:24]
    raiz = f"publicado/versiones/{firma}"
    archivos = {}
    for nombre, datos in contenidos.items():
        ruta = f"{raiz}/{nombre}.json"
        if almacen.existe(ruta):
            if almacen.leer(ruta) != datos:
                raise ValueError(f"Conflicto en snapshot {ruta}")
        else:
            almacen.escribir(ruta, datos, sobrescribir=False)
        # Verificación antes de cambiar el puntero al snapshot.
        if almacen.leer(ruta) != datos:
            raise IOError(f"No se pudo verificar {ruta}")
        archivos[nombre] = {"ruta": ruta, "sha256": _hash(datos)}

    manifiesto = {
        "contrato": "g7b.publicacion/1",
        "version": firma,
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archivos": archivos,
        "calidad_aprobada": True,
    }
    almacen.escribir(PUNTERO, json.dumps(
        manifiesto, ensure_ascii=False, indent=2
    ).encode("utf-8"))
    return manifiesto


def leer_actual(almacen):
    """Lee el snapshot vigente; falla si sus archivos no coinciden con los hashes."""
    if not almacen.existe(PUNTERO):
        return None
    m = json.loads(almacen.leer(PUNTERO))
    if m.get("contrato") != "g7b.publicacion/1" or not m.get("calidad_aprobada"):
        raise ValueError("Manifiesto inválido o no aprobado")
    for nombre in ORIGENES:
        archivo = m.get("archivos", {}).get(nombre, {})
        ruta = archivo.get("ruta", "")
        if not ruta.startswith(f"publicado/versiones/{m['version']}/"):
            raise ValueError(f"Ruta inválida de {nombre}")
        if not almacen.existe(ruta) or _hash(almacen.leer(ruta)) != archivo.get("sha256"):
            raise ValueError(f"Integridad inválida de {nombre}")
    return m
