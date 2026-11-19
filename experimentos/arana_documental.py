"""Banco reproducible: python -m experimentos.arana_documental [--solo-orden]."""
import argparse
import json
import subprocess
import sys
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlsplit

from motor_extraccion.frontera_documental import Frontera, calificar, palabras

PRESUPUESTO = 6
TEMAS = ["render", "memoria"]
ESTRATEGIAS = ["amplitud", "foco", "foco_puentes"]
# Etiquetas del evaluador, independientes de las señales disponibles en los enlaces.
# El orden columna->valor importa. Los números son ejemplos, no mediciones de Blender.
VERDAD = {"parametros": ("Umbral", "Automático"), "ajuste": ("Mínimo", "2"),
          "resumen": ("Memoria", "512 MiB")}


def grafo(escenario):
    if escenario == "descriptivo":
        inicio = [("boletin", "Noticias"), ("interfaz", "Colores"), ("parametros", "Render memoria"),
                  ("sesiones", "Render"), ("directorio", "Índice"), ("resumen", "Memoria"),
                  ("ruido", "Render")]
        indice = [("ajuste", "Render memoria")]
    elif escenario == "ambiguo":
        inicio = [("parametros", "Notas"), ("ajuste", "Guía"), ("resumen", "Inicio"),
                  ("sesiones", "Render"), ("ruido", "Render memoria"), ("boletin", "Memoria"),
                  ("directorio", "Índice")]
        indice = [("ajuste", "Guía")]
    else:
        raise ValueError(escenario)
    return {"inicio": inicio, "directorio": indice}


def pagina(nombre, enlaces):
    tabla = ""
    if nombre in VERDAD:
        propiedad, valor = VERDAD[nombre]
        tabla = (f'<section id="ajustes"><h2>Ajustes</h2><table><tr><th>Propiedad</th>'
                 f'<th>Valor</th></tr><tr><td>{propiedad}</td><td>{valor}</td></tr></table></section>')
    lista = "".join(f'<a href="{ruta}">{escape(ancla)}</a> ' for ruta, ancla in enlaces)
    return f"<html><title>Ficha</title><main><h1>Guía</h1>{lista}{tabla}</main></html>"


def orden_grafo(escenario, estrategia):
    """Control sin red: prueba la selección; no mide extracción ni tráfico HTTP."""
    enlaces = grafo(escenario)
    frontera = Frontera(estrategia, PRESUPUESTO)
    frontera.ofrecer("inicio")
    orden = []
    while (actual := frontera.siguiente()) is not None:
        orden.append(actual.url)
        for ruta, ancla in enlaces.get(actual.url, []):
            nota, puente = calificar(ruta, ancla, "Guía", palabras(" ".join(TEMAS)), actual.profundidad + 1)
            frontera.ofrecer(ruta, actual.profundidad + 1, nota, puente)
    return orden


def recuperadas(items):
    # Para el control paginas se evalúa su HTML con el mismo extractor que las tres variantes.
    from scrapy.http import HtmlResponse
    from motor_extraccion.spiders.fragmentos_sphinx import extraer_fragmentos

    aciertos = set()
    for item in items:
        ruta = urlsplit(item["url"]).path.rsplit("/", 1)[-1]
        if ruta not in VERDAD:
            continue
        if "fragmentos" in item:
            fragmentos = item["fragmentos"]
        else:
            resp = HtmlResponse(item["url"], body=item["html"].encode(), encoding="utf-8")
            fragmentos = extraer_fragmentos(resp.css("main")[0], resp, "prueba", "", "", item["titulo"])
        for fragmento in fragmentos:
            if fragmento["url"] != item["url"] + "#ajustes":
                continue
            for bloque in fragmento["bloques"]:
                if (bloque["tipo"] == "tabla" and bloque["filas"] ==
                        [["Propiedad", "Valor"], list(VERDAD[ruta])]):
                    aciertos.add(ruta)
    return aciertos


def ejecutar(escenario, estrategia):
    enlaces = grafo(escenario)
    conocidas = {"inicio", *(ruta for lista in enlaces.values() for ruta, _ in lista)}
    peticiones = []

    class Servidor(BaseHTTPRequestHandler):
        def do_GET(self):
            peticiones.append(self.path)
            ruta = self.path.removeprefix("/docs/")
            if self.path == "/robots.txt":
                tipo, cuerpo = "text/plain", "User-agent: *\nAllow: /\n"
            elif self.path.startswith("/docs/") and ruta in conocidas:
                tipo, cuerpo = "text/html", pagina(ruta, enlaces.get(ruta, []))
            else:
                self.send_error(404)
                return
            datos = cuerpo.encode()
            self.send_response(200)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Servidor) as servidor, TemporaryDirectory() as carpeta:
        hilo = Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        hilo.start()
        base = f"http://127.0.0.1:{servidor.server_port}/docs/"
        spider = "paginas" if estrategia == "paginas" else "paginas_laboratorio"
        archivo = Path(carpeta) / "items.jsonl"
        args = [sys.executable, "-m", "scrapy", "crawl", spider, "-O", str(archivo),
                "-a", 'urls=' + json.dumps([base + "inicio"]), "-a", "prefijo=" + base,
                "-a", "fuente=prueba", "-a", "seguir=1", "-a", f"max_paginas={PRESUPUESTO}",
                "-s", "CONCURRENT_REQUESTS=1", "-s", "DOWNLOAD_DELAY=0", "-s", "AUTOTHROTTLE_ENABLED=False",
                "-s", "HTTPPROXY_ENABLED=False", "-s", "LOG_LEVEL=ERROR"]
        if estrategia != "paginas":
            args.extend(["-a", "estrategia=" + estrategia, "-a", "temas=" + json.dumps(TEMAS)])
        try:
            proceso = subprocess.run(args, cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                     text=True, timeout=45)
            if proceso.returncode or "ERROR" in proceso.stderr:
                raise RuntimeError(proceso.stderr)
            items = [json.loads(linea) for linea in archivo.read_text(encoding="utf-8").splitlines()]
        finally:
            servidor.shutdown()
            hilo.join()
    aciertos = recuperadas(items)
    q = len(peticiones)
    objetivos_visitados = {ruta.removeprefix("/docs/") for ruta in peticiones} & VERDAD.keys()
    return {"escenario": escenario, "estrategia": estrategia, "Q": q,
            "paginas_solicitadas": sum(p != "/robots.txt" for p in peticiones),
            "orden_http": peticiones, "U": len(aciertos), "evidencia": sorted(aciertos),
            "F": len(aciertos) / len(VERDAD),
            "F_visitadas": len(aciertos) / len(objetivos_visitados) if objetivos_visitados else None,
            "Y100": round(100 * len(aciertos) / q, 2) if q else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo-orden", action="store_true")
    args = parser.parse_args()
    for caso in ("descriptivo", "ambiguo"):
        for metodo in (ESTRATEGIAS if args.solo_orden else ["paginas", *ESTRATEGIAS]):
            if args.solo_orden:
                print(caso, metodo, orden_grafo(caso, metodo))
            else:
                print(json.dumps(ejecutar(caso, metodo), ensure_ascii=False), flush=True)
