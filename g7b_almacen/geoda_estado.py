"""Puente público G7B → Geoda: publica SOLO agregados verificados, nunca huellas.

El texto extraído por Zyte es conocimiento, NO rendimiento. No se generan
perfiles de hardware hasta que exista una compuerta específica de evidencia.
El JSON publicado por GitHub Actions contiene conteos, no equipos ni alumnos.
"""
import argparse
import json
import os
from pathlib import Path

from .cubo import ACTUAL, CONTRATO, sha

CONTRATO_GEODA = "g7b.geoda.estado/1"
LIMITE_MANIFIESTO = 256_000


def entero(valor):
    return type(valor) is int and valor >= 0


def estado_del_cubo(lago):
    puntero = lago.leer_json(ACTUAL)
    if not isinstance(puntero, dict) or puntero.get("contrato") != CONTRATO:
        raise ValueError("G7B: no hay cubo vigente verificado")
    version = puntero.get("version")
    if not isinstance(version, str) or not version or len(version) > 100:
        raise ValueError("G7B: versión del cubo inválida")
    ruta = f"oro/cubos/{version}/manifiesto.json"
    if puntero.get("manifiesto") != ruta:
        raise ValueError("G7B: ruta de manifiesto no coincide")
    contenido = lago.contenedor.download_blob(ruta).readall()
    if len(contenido) > LIMITE_MANIFIESTO or sha(contenido) != puntero.get("sha256"):
        raise ValueError("G7B: integridad del manifiesto fallida")
    manifiesto = json.loads(contenido)
    if (manifiesto.get("contrato") != CONTRATO or manifiesto.get("estado") != "verificado"
            or manifiesto.get("version") != version):
        raise ValueError("G7B: versión del manifiesto no verificada")
    cubo = manifiesto.get("archivos", {}).get("oro/cubo.duckdb", {})
    if cubo.get("ruta") != puntero.get("cubo") or not cubo.get("sha256"):
        raise ValueError("G7B: cubo y manifiesto incompatibles")
    total = manifiesto.get("mediciones")
    calidad = manifiesto.get("calidad", {})
    aceptadas, revision = calidad.get("aceptado", 0), calidad.get("revision", 0)
    if not all(entero(n) for n in (total, aceptadas, revision)) or aceptadas + revision != total:
        raise ValueError("G7B: conteos del cubo inconsistentes")
    # La versión actual del cubo declara recomendaciones_habilitadas=False.
    # Publicarlas sin un validador de perfiles sería científicamente incorrecto.
    if manifiesto.get("recomendaciones_habilitadas") is not False:
        raise ValueError("G7B: estado de recomendaciones desconocido; revisar contrato")
    return {"version": version, "mediciones": total, "aceptadas": aceptadas,
            "revision": revision, "recomendaciones_habilitadas": False}


def generar(lago, documentos):
    if not entero(documentos):
        raise ValueError("G7B: conteo de documentos inválido")
    cubo = estado_del_cubo(lago)
    return {
        "contrato": CONTRATO_GEODA,
        "version": cubo["version"],
        "cubo": cubo,
        "conocimiento": {"documentos": documentos, "origen": "mongo_conocimiento_3d"},
        "perfiles": [],
        "nota": "El conocimiento extraído no equivale a mediciones; se usan perfiles locales base.",
    }


def total_documentos(uri):
    if not uri:
        raise ValueError("G7B: falta MONGO_URI para publicar el estado completo")
    from pymongo import MongoClient
    with MongoClient(uri, serverSelectionTimeoutMS=7000) as cliente:
        return cliente["conocimiento_3d"]["documentos"].count_documents({})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, required=True)
    a = p.parse_args()
    from g7b_lago import Lago

    documento = generar(Lago.desde_entorno(), total_documentos(os.getenv("MONGO_URI")))
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    # Escritura local; GitHub Actions solo la publicará después de validar ambos servicios.
    a.salida.write_text(json.dumps(documento, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("G7B_GEODA_PUBLICACION_VERIFICADA", json.dumps({
        "version": documento["version"], "mediciones": documento["cubo"]["mediciones"],
        "documentos": documento["conocimiento"]["documentos"], "perfiles": len(documento["perfiles"]),
    }))


if __name__ == "__main__":
    main()
