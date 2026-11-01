"""Plata → MongoDB: lo aceptado por el embudo se publica en conocimiento_3d.documentos (zona oro).

    python -m g7b_ingesta.publicar
    python -m g7b_ingesta.publicar --simulacro

- Un documento por doc_id (SHA-256 de la URL), con índice único.
- Solo se escribe si su huella de contenido cambió (motor_extraccion.pipelines.guardar).
- Se detiene antes de llenar la capa gratuita: si la base pasa de LIMITE_MB, avisa y no escribe más
  (plan 7.2: los $50 de créditos se activan al acercarse a ese límite).

Variables: MONGO_URI (el usuario que solo escribe), MONGO_DATABASE (por omisión conocimiento_3d)
y las del lago.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from g7b_lago import Lago
from motor_extraccion.pipelines import guardar

PUBLICADOS = "control/publicados.json"
COLECCION = "documentos"
LIMITE_MB = 400


def a_registro(doc):
    embudo = doc.get("embudo", {})
    return {
        "doc_id": hashlib.sha256((doc.get("url") or "").encode("utf-8")).hexdigest(),
        "url": doc.get("url"),
        "fuente": doc.get("fuente"),
        "titulo": doc.get("titulo"),
        "texto": doc.get("texto"),
        "licencia": doc.get("licencia"),
        "modo": doc.get("modo"),
        "metadatos": doc.get("metadatos") or {},
        "preguntas": embudo.get("preguntas", []),
        "puntajes": embudo.get("puntajes", {}),
        "hash_contenido": embudo.get("huella"),
        "origen": doc.get("origen"),
    }


def tamano_mb(base):
    try:
        return base.command("dbstats").get("dataSize", 0) / 1024 / 1024
    except Exception:
        return 0.0


def publicar(lago, base, simulacro=False, limite_mb=LIMITE_MB, salida=print):
    publicados = lago.leer_json(PUBLICADOS, por_omision={}) or {}
    coleccion = base[COLECCION]
    if not simulacro:
        coleccion.create_index("doc_id", unique=True)
        coleccion.create_index([("fuente", 1), ("preguntas", 1)])
    total = {"nuevo": 0, "actualizado": 0, "sin_cambios": 0, "archivos": 0}
    for ruta in sorted(r for r in lago.listar("plata/aceptados/") if r not in publicados):
        if tamano_mb(base) > limite_mb:
            salida(f"ALTO: la base pasa de {limite_mb} MB. Revisa el plan (créditos de MongoDB) antes de seguir.")
            total["detenido_por_tamano"] = True
            break
        conteo = {"nuevo": 0, "actualizado": 0, "sin_cambios": 0}
        for doc in lago.leer_jsonl_gz(ruta):
            registro = a_registro(doc)
            if not registro["url"]:
                continue
            resultado = "simulacro" if simulacro else guardar(coleccion, registro)
            if resultado in conteo:
                conteo[resultado] += 1
        for k, v in conteo.items():
            total[k] += v
        total["archivos"] += 1
        salida(f"{ruta}: " + ", ".join(f"{k} {v}" for k, v in conteo.items()))
        if not simulacro:
            publicados[ruta] = {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"), **conteo}
            lago.escribir_json(PUBLICADOS, publicados)
    return total


def main(argv=None):
    p = argparse.ArgumentParser(prog="publicar")
    p.add_argument("--simulacro", action="store_true")
    o = p.parse_args(argv)
    if not os.environ.get("MONGO_URI"):
        sys.exit("Falta MONGO_URI.")
    import pymongo

    cliente = pymongo.MongoClient(os.environ["MONGO_URI"])
    try:
        total = publicar(Lago.desde_entorno(), cliente[os.environ.get("MONGO_DATABASE", "conocimiento_3d")],
                         simulacro=o.simulacro)
    finally:
        cliente.close()
    print(json.dumps(total, ensure_ascii=False))
    return total


if __name__ == "__main__":
    main()
