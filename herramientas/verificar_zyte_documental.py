"""Relevo en el proyecto de scrapinghub.yml y prueba end-to-end del código recién desplegado."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from scrapinghub import ScrapinghubClient

from g7b_ingesta import catalogo
from g7b_ingesta.vigilar import argumentos_zyte
from motor_extraccion.site import MODELO_SITE as MODELO

NOMBRES = {"paginas", "blender_docs"}
FUENTE = "blender-compositor-45"
TAG = "g7b-site-v41-piloto"


def activos(proyecto):
    return list(proyecto.jobs.iter(state=["pending", "running"], meta=["spider", "state"]))


def comprobar_trabajos(proyecto, esperar):
    fin = time.monotonic() + esperar
    while True:
        trabajos = activos(proyecto)
        nombres = [j["spider"] for j in trabajos]
        print("Trabajos pendientes o en ejecución:", [(j["key"], j["spider"]) for j in trabajos], flush=True)
        if len(nombres) < 2 and set(nombres) <= {"blender_docs"}:
            return
        if time.monotonic() >= fin:
            raise RuntimeError("El proyecto todavía tiene trabajos que se solaparían con el relevo")
        time.sleep(10)


def ejecutar(proyecto):
    remotas = proyecto.spiders.list()
    actual = next(s["version"] for s in remotas if s["id"] == "paginas")
    disponibles = {s["id"] for s in remotas if s.get("version") == actual}
    print("Arañas en la versión desplegada:", actual, sorted(disponibles), flush=True)
    if disponibles != NOMBRES:
        raise RuntimeError("El inventario remoto de la versión no coincide con la release")
    comprobar_trabajos(proyecto, 120)
    ruta_cert = Path(__file__).resolve().parents[1] / "algoritmos" / "documentacion" / "resultados-site-4.1.json"
    ya_calibrado_repo = ruta_cert.is_file() and json.loads(ruta_cert.read_text(encoding="utf-8")).get("modelo") == MODELO
    previo = next(iter(proyecto.jobs.iter(spider="paginas", state="finished", has_tag=TAG,
                                         meta=["close_reason", "items"], count=1)), {})
    piloto = not (ya_calibrado_repo or (previo.get("close_reason") == "finished" and previo.get("items", 0)))
    fuente = catalogo.por_id(catalogo.cargar())[FUENTE]
    semilla = fuente["sensor"]["url"]
    if not piloto:
        if previo.get("key"):
            anterior = proyecto.jobs.get(previo["key"])
            semilla = next((i["url"] for i in anterior.items.iter()
                            if i.get("documental", {}).get("conteos", {}).get("candidato")), semilla)
        elif ya_calibrado_repo:
            evid = json.loads(ruta_cert.read_text(encoding="utf-8")).get("evidencia") or []
            semilla = next((e["url"].split("#", 1)[0] for e in evid if e.get("url")), semilla)
    vistas_40 = set()
    if piloto:
        anterior_40 = next(iter(proyecto.jobs.iter(spider="paginas", state="finished",
                           has_tag="g7b-site-v4-piloto", meta=["close_reason", "items"], count=1)), {})
        if anterior_40.get("close_reason") != "finished" or not anterior_40.get("items"):
            raise RuntimeError("Falta el recorrido de referencia 4.0 para identificar la reserva")
        vistas_40 = {i["url"] for i in proyecto.jobs.get(anterior_40["key"]).items.iter()}
    _, args = argumentos_zyte(fuente, [semilla])
    presupuesto_operativo = int(args["max_paginas"])
    limite = 2 * presupuesto_operativo if piloto else 1
    args.update(max_paginas=str(limite), seguir="1" if piloto else "0")
    job = proyecto.jobs.run("paginas", job_args=args, add_tag=[TAG] if piloto else ["g7b-site-v41-smoke"])
    print("Prueba real en Zyte:", job.key, "máximo de páginas:", limite, flush=True)
    fin = time.monotonic() + 600
    max_activos = 0
    while job.metadata.get("state") != "finished":
        trabajos = activos(proyecto)
        nombres = [j["spider"] for j in trabajos]
        max_activos = max(max_activos, len(nombres))
        if len(nombres) != len(set(nombres)) or not set(nombres) <= NOMBRES:
            raise RuntimeError(f"Solapamiento en Zyte: {nombres}")
        if time.monotonic() >= fin:
            raise RuntimeError(f"Tiempo agotado esperando el trabajo {job.key}")
        time.sleep(8)
    razon = job.metadata.get("close_reason")
    paginas, candidatos, con_candidatos = 0, 0, 0
    for item in job.items.iter():
        if item.get("documental", {}).get("modelo") != MODELO:
            raise RuntimeError("Zyte devolvió una salida sin la firma del modelo desplegado")
        paginas += 1
        eventos = [e for e in item["documental"]["eventos"] if e["decision"] == "candidato"]
        candidatos += len(eventos)
        if eventos:
            con_candidatos += 1
            # Elegir un candidato reproducible por página antes de conocer su etiqueta.
            e = min(eventos, key=lambda x: hashlib.sha256(("piloto-site-41/" + x["id"]).encode()).digest())
            f = next(f for f in item["fragmentos"] if f["fragmento_id"] == e["fragmento"])
            bloque = f["bloques"][e["bloque"]]
            print("MUESTRA " + json.dumps({"url": e["url"], "id": e["id"], "titulo": f["titulo"],
                  "destinos": e["destinos"], "orden": paginas,
                  "tramo": "operativo" if paginas <= presupuesto_operativo else "reserva",
                  "inedita_40": item["url"] not in vistas_40 if piloto else None,
                  "texto": bloque["texto"][:1800],
                  "truncado": len(bloque["texto"]) > 1800}, ensure_ascii=False), flush=True)
    print(f"RESULTADO job={job.key} modelo={MODELO} cierre={razon} paginas={paginas} candidatos={candidatos} "
          f"paginas_con_candidatos={con_candidatos} max_activos_observados={max_activos}",
          flush=True)
    if razon != "finished" or not 0 < paginas <= limite or not candidatos:
        raise RuntimeError("El trabajo remoto no entregó evidencia clasificada")
    comprobar_trabajos(proyecto, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fase", choices=["antes", "despues"])
    fase = parser.parse_args().fase
    proyecto = ScrapinghubClient(os.environ["SHUB_APIKEY"]).get_project(883618)
    if fase == "antes":
        comprobar_trabajos(proyecto, 240)
    else:
        ejecutar(proyecto)
