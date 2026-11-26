"""Informe de solo lectura. Se ejecuta en cada repositorio con su propio GITHUB_TOKEN."""
import base64
import html
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

OWNER = "Maximiliano-cabello-mata"
G7B = "amatista-g7b-etl"
WEB = "amatista-recuperada-20261106"
API = "amatista-api-"
MOTOR = "amatista-motor-"
IA = "AMATISTA-IA-"
PUBLICOS = (G7B, MOTOR, API, IA)
CENTRAL = f"https://github.com/{OWNER}/{WEB}/actions/workflows/coordinacion.yml"


def api(repo, endpoint="", paginas=False):
    comando = ["gh", "api"]
    if paginas:
        comando += ["--paginate", "--slurp"]
    comando.append(f"repos/{OWNER}/{repo}{endpoint}")
    datos = json.loads(subprocess.check_output(comando, text=True))
    return [fila for pagina in datos for fila in pagina] if paginas else datos


def texto(valor):
    valor = " ".join(valor.split())
    return re.sub(r"([^\w\s])", r"\\\1", html.escape(valor[:160]))


def version(contenido):
    lineas = [linea.split("#", 1)[0].strip() for linea in contenido.splitlines()]
    lineas = [linea for linea in lineas if linea]
    if len(lineas) != 1 or not re.fullmatch(r"[0-9a-f]{40}", lineas[0]):
        raise ValueError("se esperaba un solo SHA completo")
    return lineas[0]


def cruces(propuestas):
    for a, b in itertools.combinations(propuestas, 2):
        if a["base"] == b["base"]:
            comunes = sorted(a["rutas"] & b["rutas"])
            if comunes:
                yield a["n"], b["n"], comunes


def informar(repo, lineas):
    url = f"https://github.com/{OWNER}/{repo}"
    rama = api(repo)["default_branch"]
    punta = api(repo, "/commits/" + quote(rama, safe=""))
    sha = punta["sha"]
    mensaje = punta["commit"]["message"].splitlines()[0]
    fecha = punta["commit"]["committer"]["date"][:10]
    lineas.extend([f"### [{repo}]({url})", "", f"Rama `{rama}` · {fecha} · "
                   f"[{sha[:9]}]({url}/commit/{sha}) {texto(mensaje)}", ""])
    propuestas = []
    for breve in api(repo, "/pulls?state=open&per_page=100", paginas=True):
        n = breve["number"]
        pr = api(repo, f"/pulls/{n}")
        estado = {False: "CONFLICTO DE FUSIÓN", True: "fusionable por Git", None: "GitHub está calculando"}[pr["mergeable"]]
        lineas.append(f"- [#{n}]({url}/pull/{n}) {texto(pr['title'])} → `{pr['base']['ref']}` · {estado}")
        if pr["mergeable"] is False:
            print(f"::warning::{repo} #{n} tiene conflicto de fusión")
        archivos = api(repo, f"/pulls/{n}/files?per_page=100", paginas=True)
        if len(archivos) < pr["changed_files"]:
            raise ValueError(f"GitHub devolvió una lista incompleta de archivos para #{n}")
        rutas = {ruta for archivo in archivos for ruta in (archivo["filename"], archivo.get("previous_filename")) if ruta}
        propuestas.append({"n": n, "base": pr["base"]["ref"], "rutas": rutas})
    if not propuestas:
        lineas.append("Sin propuestas abiertas.")
    for a, b, rutas in cruces(propuestas):
        muestra = ", ".join(texto(ruta) for ruta in rutas[:6])
        lineas.append(f"- Revisar juntos [#{a}]({url}/pull/{a}) y [#{b}]({url}/pull/{b}): "
                      f"{len(rutas)} archivos en común. {muestra}")
    lineas.append("")
    return rama, sha


def fijadas(repo, propio, sha):
    resultado = {}
    for archivo, proveedor in (("MOTOR_VERSION", MOTOR), ("GEODA_VERSION", G7B)):
        if repo == propio:
            contenido = Path(archivo).read_text(encoding="utf-8")
        else:
            ficha = api(repo, f"/contents/{archivo}?ref={sha}")
            contenido = base64.b64decode(ficha["content"]).decode("utf-8")
        resultado[proveedor] = version(contenido)
    return resultado


def main():
    propio = os.environ["GITHUB_REPOSITORY"].split("/", 1)[1]
    repos = (*PUBLICOS, WEB) if propio == WEB else PUBLICOS
    lineas = ["## Coordinación entre repositorios", "",
              "Última integración de cada rama predeterminada y propuestas abiertas. "
              "Un cruce de archivos requiere revisión. La columna de fusión describe el estado de Git.", ""]
    errores, puntas, pins = [], {}, {}
    for repo in repos:
        try:
            _, puntas[repo] = informar(repo, lineas)
        except (subprocess.CalledProcessError, ValueError, KeyError) as error:
            errores.append(f"{repo}: lectura incompleta ({type(error).__name__})")
    lineas.extend(["### Revisiones fijadas por los consumidores", "",
                   "Para el repositorio de esta ejecución se leen los archivos del checkout. "
                   "Para los demás se usa la revisión oficial indicada arriba.", ""])
    for repo in (API, WEB):
        if repo not in puntas:
            continue
        try:
            pins[repo] = fijadas(repo, propio, puntas[repo])
            for proveedor, sha in pins[repo].items():
                url = f"https://github.com/{OWNER}/{proveedor}/commit/{sha}"
                lineas.append(f"- {repo} → {proveedor}: [{sha[:9]}]({url})")
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
            errores.append(f"{repo}: versión ilegible ({type(error).__name__})")
    for proveedor in (MOTOR, G7B):
        for sha in {valores[proveedor] for valores in pins.values()}:
            if proveedor not in puntas:
                continue
            try:
                comparacion = api(proveedor, f"/compare/{sha}...{puntas[proveedor]}?per_page=1")
                if comparacion["status"] not in ("ahead", "identical"):
                    errores.append(f"{proveedor}: {sha[:9]} está fuera de la historia de la rama oficial")
            except (KeyError, ValueError, subprocess.CalledProcessError):
                errores.append(f"{proveedor}: revisión {sha[:9]} sin verificar")
        if WEB in pins and API in pins and pins[WEB][proveedor] != pins[API][proveedor]:
            errores.append(f"Web y API fijan versiones distintas de {proveedor}")
    lineas.extend(["", f"[Informe de los cinco repositorios, con acceso a la web]({CENTRAL}).", ""])
    if errores:
        lineas += ["### Requiere atención", ""] + ["- " + error for error in errores]
    informe = "\n".join(lineas) + "\n"
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as salida:
        salida.write(informe)
    print(informe)
    return bool(errores)


if __name__ == "__main__":
    raise SystemExit(main())
