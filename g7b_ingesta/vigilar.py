"""Disparadores: revisa cada fuente vigilable cuando le toca y lanza su extracción solo si hay algo nuevo.

    python -m g7b_ingesta.vigilar                 # lo que toca según frecuencia_horas
    python -m g7b_ingesta.vigilar --fuente arxiv-cs-gr --forzar
    python -m g7b_ingesta.vigilar --simulacro     # revisa, pero no escribe ni lanza nada

Extractor por fuente:
    directo   lo que trae el sensor va a bronce/<fuente>/<fecha>/ (feeds y API)
    zyte      lanza la araña "paginas" en Zyte con las URLs (sus resultados llegan a bronce con zyte_a_lago)
    descarga  descarga cada URL (PDF) a bronce/<fuente>/<fecha>/

Estado en control/sensores.json; bitácora de cada corrida en control/vigilancia/<fecha>.jsonl.gz.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from g7b_lago import Lago, ruta_bronce

from . import catalogo as cat
from . import red
from .sensores import SENSORES

ESTADO = "control/sensores.json"
DESCARGA_MAX_MB = 50


def _ahora():
    return datetime.now(timezone.utc)


def toca(fuente, estado, ahora):
    ultimo = estado.get("ultima_revision")
    if not ultimo:
        return True
    return ahora - datetime.fromisoformat(ultimo) >= timedelta(hours=fuente["frecuencia_horas"])


def _procedencia(registro, fuente, detectado):
    return {**registro, "fuente": fuente["id"], "_g7b": {
        "fuente": fuente["id"], "licencia": fuente["licencia"], "modo": fuente["modo"],
        "extraido_en": detectado, "huella": hashlib.sha256(
            json.dumps(registro, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()}}


def lanzar_zyte(cliente, proyecto_id, fuente, urls):
    zyte = fuente.get("zyte") or {}
    argumentos = {"fuente": fuente["id"], "urls": json.dumps(urls), "modo": fuente["modo"],
                  "dominios": json.dumps(fuente["dominios"]), "seguir": "1" if zyte.get("seguir") else "0",
                  "prefijo": zyte.get("prefijo", ""), "max_paginas": str(zyte.get("max_paginas", 200))}
    trabajo = cliente.get_project(int(proyecto_id)).jobs.run("paginas", job_args=argumentos)
    return getattr(trabajo, "key", str(trabajo))


def descargar(lago, fuente, urls, obtener, dia, detectado):
    guardados = []
    for url in urls:
        r = obtener(url, {})
        if r.estado != 200:
            continue
        if len(r.contenido) > DESCARGA_MAX_MB * 1024 * 1024:
            continue
        huella = hashlib.sha256(r.contenido).hexdigest()
        tipo = r.cabeceras.get("content-type", "application/octet-stream").split(";")[0]
        extension = ".pdf" if "pdf" in tipo or url.lower().endswith(".pdf") else ".bin"
        ruta = ruta_bronce(fuente["id"], huella[:16] + extension, dia)
        lago.subir_bytes(ruta, r.contenido, tipo=tipo, metadatos={"url": url, "fuente": fuente["id"]})
        guardados.append({"url": url, "archivo": ruta, "tipo": tipo, "huella": huella})
    if guardados:
        lago.subir_jsonl_gz(ruta_bronce(fuente["id"], f"descargas-{int(_ahora().timestamp())}.jsonl.gz", dia),
                            (_procedencia(g, fuente, detectado) for g in guardados))
    return guardados


def vigilar(catalogo, lago, obtener=red.obtener, zyte=None, proyecto_id=None, solo=None, forzar=False,
            simulacro=False, ahora=None, salida=print):
    ahora = ahora or _ahora()
    estados = lago.leer_json(ESTADO, por_omision={}) or {}
    bitacora = []
    fuentes = [f for f in cat.vigilables(catalogo) if not solo or f["id"] == solo]
    if solo and not fuentes:
        raise ValueError(f"La fuente {solo} no existe o no es vigilable (activa y con licencia confirmada)")
    for fuente in fuentes:
        estado = estados.get(fuente["id"], {})
        if not forzar and not toca(fuente, estado, ahora):
            continue
        registro = {"fuente": fuente["id"], "cuando": ahora.isoformat(timespec="seconds")}
        try:
            resultado, estado_nuevo = SENSORES[fuente["sensor"]["tipo"]](fuente, estado, obtener)
            registro.update({"nota": resultado["nota"], "urls": len(resultado["urls"]),
                             "registros": len(resultado["registros"])})
            detectado = ahora.isoformat(timespec="seconds")
            if simulacro:
                registro["accion"] = "simulacro"
            elif fuente["extractor"] == "directo" and resultado["registros"]:
                ruta = ruta_bronce(fuente["id"], f"{int(ahora.timestamp())}.jsonl.gz", ahora.date())
                lago.subir_jsonl_gz(ruta, (_procedencia(r, fuente, detectado) for r in resultado["registros"]),
                                    metadatos={"fuente": fuente["id"]})
                registro["accion"] = f"bronce: {ruta}"
            elif fuente["extractor"] == "zyte" and resultado["urls"]:
                if zyte is None:
                    raise RuntimeError("hay URLs para Zyte pero falta ZYTE_API_KEY")
                registro["accion"] = f"zyte: trabajo {lanzar_zyte(zyte, proyecto_id, fuente, resultado['urls'])}"
            elif fuente["extractor"] == "descarga" and resultado["urls"]:
                guardados = descargar(lago, fuente, resultado["urls"], obtener, ahora.date(), detectado)
                registro["accion"] = f"descarga: {len(guardados)} archivos"
            else:
                registro["accion"] = "nada nuevo"
            if not simulacro:
                estado_nuevo["ultima_revision"] = ahora.isoformat(timespec="seconds")
                estados[fuente["id"]] = estado_nuevo
        except Exception as error:  # una fuente rota no detiene a las demás
            registro["error"] = f"{type(error).__name__}: {str(error)[:200]}"
            if not simulacro:
                estado["ultimo_error"] = registro["error"]
                estados[fuente["id"]] = estado
        bitacora.append(registro)
        salida(json.dumps(registro, ensure_ascii=False))
    if not simulacro and bitacora:
        lago.escribir_json(ESTADO, estados)
        lago.subir_jsonl_gz(f"control/vigilancia/{ahora.date().isoformat()}/{int(ahora.timestamp())}.jsonl.gz",
                            bitacora)
    return bitacora


def main(argv=None):
    p = argparse.ArgumentParser(prog="vigilar")
    p.add_argument("--fuente", help="solo esta fuente")
    p.add_argument("--forzar", action="store_true", help="aunque no le toque por frecuencia")
    p.add_argument("--simulacro", action="store_true")
    o = p.parse_args(argv)
    zyte = None
    if os.environ.get("ZYTE_API_KEY"):
        from scrapinghub import ScrapinghubClient

        zyte = ScrapinghubClient(os.environ["ZYTE_API_KEY"])
    bitacora = vigilar(cat.cargar(), Lago.desde_entorno(), zyte=zyte,
                       proyecto_id=os.environ.get("ZYTE_PROJECT_ID", "883618"),
                       solo=o.fuente, forzar=o.forzar, simulacro=o.simulacro)
    if any("error" in b for b in bitacora):
        sys.exit(1)  # que la tarea programada se marque en rojo y avise


if __name__ == "__main__":
    main()
