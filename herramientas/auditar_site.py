"""Audita candidatos archivados y visita una vez el resto del inventario de la fuente."""
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urljoin

from scrapinghub import ScrapinghubClient

from g7b_ingesta import catalogo, red
from g7b_ingesta.vigilar import argumentos_zyte
from herramientas.verificar_zyte_documental import NOMBRES, activos, comprobar_trabajos
from motor_extraccion.inventario_sphinx import leer
from motor_extraccion.site import MODELO_SITE

CONFIG = Path(__file__).resolve().parents[1] / "algoritmos/documentacion/validacion-site.json"


def examinar(trabajo, cfg, anteriores, censo):
    urls, ids = set(), set()
    candidatos = 0
    for item in trabajo.items.iter():
        if item["fuente"] != cfg["fuente"] or item["documental"]["modelo"] != cfg["modelo"]:
            raise ValueError("El modelo o la fuente del trabajo no coincide con la solicitud")
        url = item["url"]
        if url in urls or (not censo and url in anteriores):
            raise ValueError("Página duplicada o ya incluida en la reserva anterior")
        urls.add(url)
        eventos = [e for e in item["documental"]["eventos"] if e["decision"] == "candidato"]
        if not eventos:
            continue
        elegido = min(eventos, key=lambda e: hashlib.sha256(("piloto-site-41/" + e["id"]).encode()).digest())
        fragmentos = {f["fragmento_id"]: f for f in item["fragmentos"]}
        for e in eventos:
            if e["id"] in ids:
                raise ValueError("ID duplicado en candidatos")
            ids.add(e["id"])
            candidatos += 1
            f = fragmentos[e["fragmento"]]
            texto = f["bloques"][e["bloque"]]["texto"]
            print("CITA " + json.dumps({"trabajo": trabajo.key, "url": e["url"], "id": e["id"],
                  "muestra": e["id"] == elegido["id"], "titulo": f["titulo"],
                  "destinos": e["destinos"], "texto": texto[:1600],
                  "truncado": len(texto) > 1600}, ensure_ascii=False), flush=True)
    print(f"CENSO trabajo={trabajo.key} paginas={len(urls)} candidatos={candidatos}", flush=True)
    return urls


def ejecutar():
    cfg = json.loads(CONFIG.read_text(encoding="utf8"))
    proyecto = ScrapinghubClient(os.environ["SHUB_APIKEY"]).get_project(883618)
    fuente = catalogo.por_id(catalogo.cargar())[cfg["fuente"]]
    if cfg["modelo"] != MODELO_SITE or not fuente["licencia_verificada"] or not fuente["activa"]:
        raise ValueError("Solicitud de auditoría incompatible con el catálogo o el modelo")
    previo = proyecto.jobs.get(cfg["previo"])
    vistas = {i["url"] for i in previo.items.iter()}
    piloto = proyecto.jobs.get(cfg["piloto"])
    vistas.update(examinar(piloto, cfg, vistas, censo=True))
    inventario = red.obtener(cfg["inventario"], {})
    if inventario.estado != 200:
        raise RuntimeError(f"Inventario no disponible: HTTP {inventario.estado}")
    prefijo = fuente["zyte"]["prefijo"]
    universo = {urljoin(cfg["inventario"], uri) for uri in leer(inventario.contenido)["paginas"]}
    universo = {url for url in universo if url.startswith(prefijo)}
    if not universo:
        raise ValueError("Inventario vacío para el prefijo solicitado")
    faltan = sorted(universo - vistas)
    urls = faltan[:cfg["limite"]]
    print(f"INVENTARIO total={len(universo)} previas={len(universo & vistas)} pendientes={len(faltan)} "
          f"presupuesto={len(urls)}", flush=True)
    if not urls:
        return
    existentes = list(proyecto.jobs.iter(spider="paginas", has_tag=cfg["etiqueta"], count=1,
                                         state=["running", "pending", "finished"]))
    if existentes:
        trabajo = proyecto.jobs.get(existentes[0]["key"])
    else:
        comprobar_trabajos(proyecto, 240)
        _, args = argumentos_zyte(fuente, urls)
        args.update(seguir="0", max_paginas=str(len(urls)))
        trabajo = proyecto.jobs.run("paginas", job_args=args, add_tag=[cfg["etiqueta"]])
    print(f"RESERVA trabajo={trabajo.key}", flush=True)
    limite = time.monotonic() + 650
    max_activos = 0
    while trabajo.metadata.get("state") != "finished":
        nombres = [j["spider"] for j in activos(proyecto)]
        max_activos = max(max_activos, len(nombres))
        if len(nombres) != len(set(nombres)) or not set(nombres) <= NOMBRES:
            raise RuntimeError(f"Hay trabajos simultáneos incompatibles: {nombres}")
        if time.monotonic() >= limite:
            raise RuntimeError(f"Tiempo agotado esperando {trabajo.key}")
        time.sleep(8)
    if trabajo.metadata.get("close_reason") != "finished":
        raise RuntimeError(f"El trabajo {trabajo.key} terminó con {trabajo.metadata.get('close_reason')}")
    nuevas = examinar(trabajo, cfg, vistas, censo=False)
    print(f"COBERTURA inventario={len(universo)} visitadas={len(universo & (vistas | nuevas))} "
          f"max_activos_observados={max_activos}", flush=True)
    comprobar_trabajos(proyecto, 0)


if __name__ == "__main__":
    ejecutar()
