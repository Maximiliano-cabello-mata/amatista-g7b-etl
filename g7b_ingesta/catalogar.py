"""Bronce → MongoDB para las fuentes de destino «catalogo» (texturas, HDRI, modelos, herramientas, extensiones).

    python -m g7b_ingesta.catalogar
    python -m g7b_ingesta.catalogar --simulacro

- Base: MONGO_DATABASE_CATALOGO (por omisión g7b_catalogo); una colección por «coleccion» del catálogo.
- Una ficha por elemento (doc_id = "<fuente>:<id>"); solo se escribe si su huella cambió.
- Solo metadatos: nombre, enlace, licencia, etiquetas y cifras. Los archivos (texturas, modelos) no se copian.
- Se detiene antes de llenar la capa gratuita de Atlas (LIMITE_MB).
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from g7b_lago import Lago
from motor_extraccion.pipelines import guardar

from . import catalogo as cat

CATALOGADOS = "control/catalogados.json"
LIMITE_MB = 400


def a_ficha(registro, fuente):
    contenido = {k: v for k, v in registro.items() if k not in ("_g7b", "fuente")}
    huella = hashlib.sha256(json.dumps(contenido, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "doc_id": f"{fuente['id']}:{registro.get('id')}",
        "fuente": fuente["id"],
        "familia": cat.familia(fuente),
        "licencia": fuente["licencia"],
        "condiciones": fuente.get("condiciones"),
        "modo": fuente["modo"],
        "id": registro.get("id"),
        "url": registro.get("url"),
        "titulo": registro.get("titulo"),
        "fecha": registro.get("fecha"),
        "etiquetas": registro.get("etiquetas") or (registro.get("datos") or {}).get("tags") or [],
        "datos": registro.get("datos") or {},
        "hash_contenido": huella,
        "extraido_en": (registro.get("_g7b") or {}).get("extraido_en"),
    }


def catalogar(lago, base, catalogo, simulacro=False, limite_mb=LIMITE_MB, salida=print):
    from .publicar import tamano_mb

    hechos = lago.leer_json(CATALOGADOS, por_omision={}) or {}
    total = {"nuevo": 0, "actualizado": 0, "sin_cambios": 0, "archivos": 0}
    for fuente in cat.por_destino(catalogo, "catalogo"):
        coleccion = base[fuente["coleccion"]]
        if not simulacro:
            coleccion.create_index("doc_id", unique=True)
            coleccion.create_index([("familia", 1), ("etiquetas", 1)])
        for ruta in lago.listar(f"bronce/{fuente['id']}/"):
            if not ruta.endswith(".jsonl.gz") or ruta in hechos:
                continue
            if tamano_mb(base) > limite_mb:
                salida(f"ALTO: la base pasa de {limite_mb} MB. Revisa el plan (créditos de MongoDB) antes de seguir.")
                total["detenido_por_tamano"] = True
                return total
            conteo = {"nuevo": 0, "actualizado": 0, "sin_cambios": 0}
            for registro in lago.leer_jsonl_gz(ruta):
                if registro.get("id") is None:
                    continue
                resultado = "simulacro" if simulacro else guardar(coleccion, a_ficha(registro, fuente))
                if resultado in conteo:
                    conteo[resultado] += 1
            for k, v in conteo.items():
                total[k] += v
            total["archivos"] += 1
            salida(f"{ruta} → {base.name}.{fuente['coleccion']}: " + ", ".join(f"{k} {v}" for k, v in conteo.items()))
            if not simulacro:
                hechos[ruta] = {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"), **conteo}
                lago.escribir_json(CATALOGADOS, hechos)
    return total


def main(argv=None):
    p = argparse.ArgumentParser(prog="catalogar")
    p.add_argument("--simulacro", action="store_true")
    o = p.parse_args(argv)
    if not os.environ.get("MONGO_URI"):
        sys.exit("Falta MONGO_URI.")
    import pymongo

    cliente = pymongo.MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=15000)
    try:
        base = cliente[os.environ.get("MONGO_DATABASE_CATALOGO", "g7b_catalogo")]
        total = catalogar(Lago.desde_entorno(), base, cat.cargar(), simulacro=o.simulacro)
    finally:
        cliente.close()
    print(json.dumps(total, ensure_ascii=False))
    return total


if __name__ == "__main__":
    main()
