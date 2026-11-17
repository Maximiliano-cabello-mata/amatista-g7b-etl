"""Estándar de hardware de G7B (g7b.hardware/1): un mismo formato de equipo para todas las fuentes.

Cada fuente de telemetría nombra los dispositivos a su manera: «NVIDIA GeForce RTX 3060 Laptop GPU»,
«Intel(R) UHD Graphics 620», «Graphics card: Mesa Intel(R) HD Graphics 520 (SKL GT2)». Aquí se
traducen a {fabricante, clase, vram_gb} con la tabla propia fuentes/hardware.yml, y se les da un
nivel con las mismas reglas de Geoda (geoda/niveles.py), para que el cubo compare peras con peras.

Sin adivinar: lo que la tabla no reconoce queda «desconocida», y el nivel dice su confianza y por qué.
"""
import os
import re
from functools import lru_cache

import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA = os.path.join(RAIZ, "fuentes", "hardware.yml")
ESTANDAR = "g7b.hardware/1"
CLASES = {"integrada", "dedicada", "desconocida"}
# Backends de Blender Open Data que miden la GPU; CPU mide el procesador.
BACKENDS_GPU = {"OPTIX", "CUDA", "HIP", "METAL", "ONEAPI", "OPENCL"}


@lru_cache(maxsize=1)
def tabla(ruta=RUTA):
    with open(ruta, encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)
    for tipo in ("gpus", "cpus"):
        for regla in datos.get(tipo, []):
            regla["_re"] = re.compile(regla["patron"], re.I)
            if tipo == "gpus" and regla.get("clase") not in CLASES:
                raise ValueError(f"clase desconocida en {RUTA}: {regla}")
    return datos


def limpiar(nombre):
    """«NVIDIA GeForce RTX 3060/PCIe/SSE2» → «NVIDIA GeForce RTX 3060»."""
    texto = re.sub(r"\((r|tm)\)", "", str(nombre or ""), flags=re.I)
    texto = re.sub(r"/pcie/sse2.*$", "", texto, flags=re.I)
    texto = re.sub(r"^\s*graphics card:\s*", "", texto, flags=re.I)
    return " ".join(texto.split())[:200]


def gpu(nombre):
    """Nombre de GPU → {nombre, nombre_original, fabricante, clase, vram_gb, regla}."""
    limpio = limpiar(nombre)
    for regla in tabla()["gpus"]:
        if regla["_re"].search(limpio):
            return {"nombre": limpio, "nombre_original": str(nombre), "fabricante": regla["fabricante"],
                    "clase": regla["clase"], "vram_gb": regla.get("vram_gb"), "regla": regla["patron"]}
    return {"nombre": limpio, "nombre_original": str(nombre), "fabricante": "desconocido",
            "clase": "desconocida", "vram_gb": None, "regla": None}


def cpu(nombre):
    limpio = limpiar(nombre)
    for regla in tabla()["cpus"]:
        if regla["_re"].search(limpio):
            return {"nombre": limpio, "fabricante": regla["fabricante"], "familia": regla["familia"]}
    return {"nombre": limpio, "fabricante": "desconocido", "familia": "desconocida"}


def nivel(gpus, ram_gb=None, opengl=None):
    """Nivel N0–N4 con las reglas de Geoda. Sin RAM, decide la GPU y la confianza baja.

    opengl: la versión que reporta el equipo, si se sabe (los reportes de error la traen).
    """
    from geoda.contratos import Gpu, Huella
    from geoda.niveles import clasificar

    tipos = {"integrada": "integrada", "dedicada": "dedicada"}
    lista = [Gpu(nombre=g["nombre"], tipo=tipos.get(g["clase"], "desconocida"), vram_gb=g.get("vram_gb"))
             for g in gpus]
    # Una integrada que corre Cycles en GPU (Open Data) o Blender actual tiene OpenGL 4.3: se declara.
    if opengl is None and any(g["clase"] == "integrada" for g in gpus):
        opengl = 4.3
    c = clasificar(Huella(gpus=lista, ram_gb=ram_gb, opengl=opengl))
    return {"nivel": c.nivel, "confianza": c.confianza, "motivos": c.motivos}


def de_benchmark(dispositivos, backend, so=None):
    """El bloque «hardware» de una medición de Blender Open Data."""
    gpu_mide = str(backend or "").upper() in BACKENDS_GPU
    bloque = {"estandar": ESTANDAR, "mide": "gpu" if gpu_mide else "cpu", "so": so}
    if gpu_mide:
        bloque["gpus"] = [gpu(d) for d in dispositivos]
        if all(g["clase"] == "desconocida" for g in bloque["gpus"]):
            bloque.update({"nivel": None, "confianza": None,
                           "motivos": ["GPU no reconocida por fuentes/hardware.yml: no se adivina el nivel"]})
        else:
            bloque.update(nivel(bloque["gpus"]))
    else:
        bloque["cpus"] = [cpu(d) for d in dispositivos]
        bloque.update({"nivel": None, "confianza": None,
                       "motivos": ["benchmark de CPU: no dice qué GPU tiene el equipo"]})
    return bloque
