"""Piloto de integración con un navegador real. Uso: piloto_aframe.py biblioteca.js salida.json."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


def medir(biblioteca, salida):
    with TemporaryDirectory() as carpeta:
        raiz = Path(carpeta)
        shutil.copyfile(biblioteca, raiz / "aframe.js")
        sonda = Path(__file__).resolve().parents[1] / "sonda/amatista_aframe.js"
        shutil.copyfile(sonda, raiz / "sonda.js")
        (raiz / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><script src="aframe.js"></script>'
            '<script src="sonda.js"></script><a-scene vr-mode-ui="enabled: false">'
            '<a-box position="0 0 -3" color="#876ccc"></a-box></a-scene>', encoding="utf-8")
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=raiz))
        Thread(target=servidor.serve_forever, daemon=True).start()
        opciones = Options()
        for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--enable-webgl",
                    "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                    "--window-size=800,600"):
            opciones.add_argument(arg)
        try:
            with webdriver.Chrome(options=opciones) as navegador:
                navegador.get(f"http://127.0.0.1:{servidor.server_port}/")
                WebDriverWait(navegador, 30).until(lambda n: n.execute_script(
                    "return (document.querySelector('a-scene')?.renderer?.info?.render.frame || 0) > 3"))
                registro = navegador.execute_async_script("""
                    const done = arguments[arguments.length - 1];
                    AmatistaTelemetria.medir({entorno: 'github_actions', carga: 'cubo_basico'})
                      .then(done, e => done({error: String(e)}));
                """)
                if "error" in registro:
                    raise RuntimeError(registro["error"])
                salida.write_text(json.dumps(registro), encoding="utf-8")
        finally:
            servidor.shutdown()
            servidor.server_close()


if __name__ == "__main__":
    medir(Path(sys.argv[1]), Path(sys.argv[2]))
