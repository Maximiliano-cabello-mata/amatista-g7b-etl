"""Repite versiones fijadas de la araña sobre las mismas respuestas HTML archivadas."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urldefrag

BASE = "https://docs.blender.org/manual/en/4.5/compositing/"
FUENTE = "blender-compositor-45"
DIR = Path(os.environ["RUNNER_TEMP"]) / "comparacion-site"
RESULTADOS = Path("resultados-comparacion/site")


def guardar(ruta, dato):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def preparar():
    from g7b_lago import Lago
    lago = Lago.desde_entorno()
    manifiesto = {}
    for trabajo in (3, 4):
        ruta = f"bronce/zyte/paginas/2026-11-19/883618-3-{trabajo}.jsonl.gz"
        for fila in lago.leer_jsonl_gz(ruta):
            url = fila["url"]
            cuerpo = fila["html"].encode("utf-8")
            assert url.startswith(BASE) and url not in manifiesto and cuerpo
            assert fila["fuente"] == FUENTE and fila["documental"]["modelo"] == "site/4.1"
            digest = hashlib.sha256(cuerpo).hexdigest()
            DIR.mkdir(exist_ok=True)
            (DIR / digest).write_bytes(cuerpo)
            manifiesto[url] = digest
    assert len(manifiesto) == 131 and BASE + "index.html" in manifiesto
    guardar(DIR / "manifest.json", manifiesto)
    guardar(RESULTADOS / "manifest.json", manifiesto)


def repetir(nombre):
    from types import SimpleNamespace
    from scrapy import Request
    from scrapy.http import HtmlResponse
    from motor_extraccion.spiders.paginas import PaginasSpider

    class Estadisticas:
        def __init__(self):
            self.conteos = Counter()

        def inc_value(self, clave, valor=1):
            self.conteos[clave] += valor

    corpus = json.loads((DIR / "manifest.json").read_text())
    for modo in ("completo", "presupuesto64"):
        completo = modo == "completo"
        semillas = sorted(corpus) if completo else [BASE + "index.html"]
        temas = "compositor node blur denoise sampling mask performance filter color alpha precision".split()
        arana = PaginasSpider(fuente=FUENTE, programa="blender", version="4.5", prefijo=BASE,
                              urls=json.dumps(semillas), temas=json.dumps(temas),
                              dominios='["docs.blender.org"]', max_paginas=str(131 if completo else 64),
                              seguir="0" if completo else "1")
        stats = Estadisticas()
        arana.crawler = SimpleNamespace(stats=stats)
        siguiente, = arana.start_requests()
        paginas, candidatos, ausentes = [], [], []
        while siguiente is not None:
            req = siguiente
            siguiente = None
            digest = corpus.get(req.url)
            if digest is None:
                ausentes.append(req.url)
            resp = HtmlResponse(req.url, request=req, status=200 if digest else 404,
                                headers={"Content-Type": "text/html"}, encoding="utf-8",
                                body=(DIR / digest).read_bytes() if digest else b"")
            for obj in arana.parse(resp):
                if isinstance(obj, Request):
                    assert siguiente is None
                    siguiente = obj
                    continue
                paginas.append(obj["url"])
                frags = {f["fragmento_id"]: f for f in obj["fragmentos"]}
                for evento in obj["documental"]["eventos"]:
                    if evento["decision"] != "candidato":
                        continue
                    frag = frags[evento["fragmento"]]
                    candidatos.append({"id": evento["id"], "url": evento["url"], "titulo": frag["titulo"],
                                       "texto": frag["bloques"][evento["bloque"]]["texto"]})
        if completo:
            assert len(paginas) == len(set(paginas)) == len(corpus) and not ausentes
        guardar(RESULTADOS / f"{nombre}-{modo}.json",
                {"paginas": paginas, "candidatos": candidatos, "ausentes": ausentes, "conteos": stats.conteos})


def consolidar():
    raiz = Path("algoritmos/documentacion")
    previo = json.loads((raiz / "auditoria.json").read_text())
    censo = json.loads((raiz / "resultados-site-4.1.json").read_text())["evidencia"]
    etiquetas = {}
    for fila in previo + censo:
        etiquetas.setdefault((fila["id"], fila["url"]), set()).add(fila["util"])
    union = {}
    orden = None
    for modo in ("completo", "presupuesto64"):
        for modelo in ("v3", "v40", "v41"):
            prueba = json.loads((RESULTADOS / f"{modelo}-{modo}.json").read_text())
            if modo == "completo":
                if orden is None:
                    orden = prueba["paginas"]
                assert orden == prueba["paginas"]
            for fila in prueba["candidatos"]:
                clave = (fila["id"], fila["url"])
                assert clave not in union or union[clave]["texto"] == fila["texto"]
                union[clave] = fila
    # Emitir primero solo las citas pendientes. El resultado por modelo se consulta después del dictamen.
    for clave, fila in sorted(union.items()):
        if len(etiquetas.get(clave, ())) != 1:
            print("REVISAR " + json.dumps(fila, ensure_ascii=False))
    claves = {k: i for i, k in enumerate(sorted(union))}
    guardar(RESULTADOS / "claves.json", [[i, *clave] for clave, i in claves.items()])
    todas = [[indice, clave[0], clave[1], next(iter(etiquetas[clave])) if len(etiquetas.get(clave, ())) == 1 else None]
             for clave, indice in claves.items()]
    print("CLAVES " + json.dumps(todas, ensure_ascii=False))
    for modo in ("completo", "presupuesto64"):
        for modelo in ("v3", "v40", "v41"):
            prueba = json.loads((RESULTADOS / f"{modelo}-{modo}.json").read_text())
            candidatos = prueba["candidatos"]
            grupos = {}
            for c in candidatos:
                grupos.setdefault(urldefrag(c["url"]).url, []).append(c)
            seleccion = [min(grupo, key=lambda c: hashlib.sha256(("piloto-site-41/" + c["id"]).encode()).digest())
                         for grupo in grupos.values()]
            print("SERIE " + json.dumps({"modo": modo, "modelo": modelo, "paginas": len(prueba["paginas"]),
                  "ausentes": len(prueba["ausentes"]), "conteos": prueba["conteos"],
                  "candidatos": [claves[(c["id"], c["url"])] for c in candidatos],
                  "muestra": [claves[(c["id"], c["url"])] for c in seleccion]}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("accion", choices=["preparar", "v3", "v40", "v41", "consolidar"])
    accion = p.parse_args().accion
    if accion == "preparar":
        preparar()
    elif accion == "consolidar":
        consolidar()
    else:
        repetir(accion)
