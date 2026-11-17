"""Núcleo de Geoda (API pública geoda.nucleo/1): del equipo y la tarea al plan, sin red.

Es la cara pública del kernel. Todo lo que sabe viene de UN paquete de conocimiento
(g7b.geoda.paquete/1, geoda/paquete.py): no lee el cubo, ni el lago, ni internet. Por eso es
determinista (mismo paquete y misma entrada, mismo plan) y se puede envolver igual en:

    - una biblioteca (este módulo),
    - la API HTTP del kernel en la nube de Oracle, junto a las APIs de Amatista (POST /api/geoda/v1/plan),
    - una implementación portable futura (Rust o C++ a WebAssembly), que debe pasar los mismos
      casos de conformidad (geoda/conformidad.json).

Cada plan dice de dónde sale su recomendación (escalera de evidencia):

    medido        perfil de mediciones DIRECTAS en suficientes equipos como el tuyo
    provisional   perfil de mediciones directas, todavía pocas
    regla_base    regla de las fichas técnicas: todavía sin mediciones de equipos como el tuyo

y aparte, si hay datos públicos, una «estimación relativa» (Blender Open Data, clase relativa) que
nunca se presenta como medición de tu equipo. Cada acción enlaza la página del manual que la explica.
"""
import json
import re

from . import VERSION, paquete as paq
from .contratos import Gpu, Huella
from .niveles import clasificar
from .planificador import decidir as _decidir

API = "geoda.nucleo/1"
ESCALERA = {"confiable": "medido", "provisional": "provisional", "base": "regla_base"}
ESCENA_REFERENCIA = "classroom"


class Nucleo:
    """El kernel listo para decidir. Se crea una vez con un paquete y se usa muchas veces."""

    def __init__(self, paquete):
        self.paquete = paq.leer(paquete)
        self._gpus = [(re.compile(r["patron"], re.I), r) for r in self.paquete["hardware"]["gpus"]]

    @classmethod
    def desde_archivo(cls, ruta):
        with open(ruta, encoding="utf-8") as archivo:
            return cls(json.load(archivo))

    # ------------------------------------------------------------------ consultas

    def info(self):
        p = self.paquete
        return {"api": API, "geoda": VERSION, "paquete": p["version"], "generado": p["generado"],
                "evidencia": p["evidencia"], "cubo": p["cubo"].get("contrato")}

    def gpu(self, nombre):
        """Nombre de GPU (de la sonda, de WebGL, de un reporte) → clase y VRAM con la tabla del paquete."""
        limpio = " ".join(re.sub(r"\((r|tm)\)|/pcie/sse2.*$", "", str(nombre or ""), flags=re.I).split())
        for patron, regla in self._gpus:
            if patron.search(limpio):
                return {"nombre": limpio, "fabricante": regla["fabricante"], "clase": regla["clase"],
                        "vram_gb": regla.get("vram_gb")}
        return {"nombre": limpio, "fabricante": "desconocido", "clase": "desconocida", "vram_gb": None}

    def huella(self, gpu=None, ram_gb=None, so="", opengl=None, vulkan=None, movil=False, cpu=""):
        """Arma una huella g7b.huella/1 desde datos sueltos del cliente (sin datos personales)."""
        tipos = {"integrada": "integrada", "apple": "integrada", "dedicada": "dedicada", "servidor": "dedicada"}
        gpus = []
        for nombre in ([gpu] if isinstance(gpu, str) else (gpu or [])):
            g = self.gpu(nombre)
            gpus.append(Gpu(nombre=g["nombre"], tipo=tipos.get(g["clase"], "desconocida"), vram_gb=g["vram_gb"]))
        return Huella(cpu=cpu, ram_gb=ram_gb, gpus=gpus, opengl=opengl, vulkan=vulkan, so=so, movil=movil)

    def clasificar(self, huella):
        h = huella if isinstance(huella, Huella) else Huella.desde_dict(huella)
        return clasificar(h).como_dict()

    # ------------------------------------------------------------------ decidir

    def decidir(self, huella, tarea=None, idioma="es"):
        """Huella (Huella o dict g7b.huella/1) + tarea → plan g7b.plan/1 con evidencia y citas."""
        plan = _decidir(huella, tarea, perfiles=self.paquete["perfiles"])
        version = _version_manual(plan.get("version"))
        motor = plan.get("perfil", {}).get("motor") or ""
        for accion in plan["acciones"]:
            accion["citas"] = self._citas(self.paquete["citas"]["acciones"].get(accion["ruta"], []),
                                          version, idioma, motor)
        nivel = plan["clasificacion"]["nivel"]
        estado = plan["perfil"]["estado"]
        plan["evidencia"] = {
            "escalera": ESCALERA[estado],
            "texto": {"medido": "medido en varios equipos como el tuyo",
                      "provisional": "medido en pocos equipos como el tuyo: todavía provisional",
                      "regla_base": "regla base: todavía no hay mediciones de equipos como el tuyo"}[ESCALERA[estado]],
            "estimacion_relativa": self._relativa(nivel, plan.get("version")),
        }
        plan["ayuda"] = self._citas(self.paquete["citas"]["generales"].get(nivel, []), version, idioma, motor)
        plan["kernel"] = {"api": API, "geoda": VERSION, "paquete": self.paquete["version"]}
        return plan

    def _citas(self, entradas, version, idioma, motor):
        salida = []
        for e in entradas:
            if e.get("cuando") and not motor.startswith(e["cuando"]):
                continue
            enlaces = [x for x in e["enlaces"] if x["version"] == version]
            elegido = next((x for x in enlaces if x["idioma"] == idioma), None) or next(
                (x for x in enlaces if x["idioma"] == "en"), None)
            if elegido:
                salida.append({"titulo": e["titulo"], "url": elegido["url"], "version": version,
                               "idioma": elegido["idioma"], "verificada": elegido["verificada"]})
        return salida

    def _relativa(self, nivel, version):
        """Factor público del nivel frente al N2 (render de Cycles), o None si no hay datos."""
        if nivel in (None, "N0"):
            return None
        factores = [f for f in self.paquete["factores"] if f["nivel"] == nivel and f["escena"] == ESCENA_REFERENCIA]
        if not factores:
            return None
        serie = _version_manual(version)
        f = next((x for x in factores if x["serie"] == serie), None) or max(factores, key=lambda x: _serie(x["serie"]))
        if nivel == paq.NIVEL_REFERENCIA:
            texto = (f"Tu nivel es la referencia de la comparación pública: en render de Cycles ({f['escena']}, "
                     f"Blender {f['serie']}), un N2 con gráficos integrados hace unas {f['mediana_samples_min']:g} "
                     "muestras por minuto. Es un dato público (Blender Open Data), no una medición de tu equipo.")
        else:
            texto = (f"En render de Cycles ({f['escena']}, Blender {f['serie']}), los equipos públicos de nivel "
                     f"{nivel} rinden {f['factor_frente_a_N2']:g} veces lo de un N2 con gráficos integrados. "
                     "Es una comparación con datos públicos (Blender Open Data), no una medición de tu equipo.")
        return {
            "clase_dato": "relativa", "naturaleza": f.get("naturaleza", "velocidad"), "fuente": f["fuente"], "serie": f["serie"], "escena": f["escena"],
            "factor_frente_a_N2": f["factor_frente_a_N2"], "mediciones": f["mediciones"],
            "texto": texto,
        }


def _version_manual(version):
    """La serie de Blender cuyo manual se cita: la del plan si existe, si no la más nueva."""
    serie = ".".join(str(version or "").split(".")[:2])
    return serie if serie in paq.VERSIONES_MANUAL else paq.VERSIONES_MANUAL[0]


def _serie(texto):
    try:
        return tuple(int(x) for x in str(texto).split("."))
    except ValueError:
        return (0,)
