"""Modelo de costos: cuánto le cuesta a un equipo una operación 3D (FICHAS_TECNICAS 2.4).

v0, honesto: una TABLA de medianas del cubo por (nivel, prueba, perfil). Si una celda no tiene
mediciones, responde «sin_datos» en lugar de inventar. La versión aprendida (gradient boosting,
menos de 1 MB, entrenada en Colab/Camber) implementará la misma interfaz: estimar().
"""
import json
from dataclasses import dataclass

from .contratos import NIVELES, OPERACION, Huella
from .niveles import clasificar

# Catálogo inicial de operaciones del kernel (FICHAS_TECNICAS 2.1) y la prueba de la sonda que hoy las mide.
OPERACIONES = {
    "vista3d": {"prueba_sonda": "vista3d", "unidad": "fps", "controladores": ["Blender (viewport)"]},
    "editar": {"prueba_sonda": "edicion", "unidad": "s", "controladores": ["Blender (bmesh)"]},
    "subdividir": {"prueba_sonda": "modificadores", "unidad": "s", "controladores": ["OpenSubdiv (vía Blender)"]},
    "animar": {"prueba_sonda": "animacion", "unidad": "fps", "controladores": ["Blender"]},
    "renderizar_eevee": {"prueba_sonda": "render_eevee", "unidad": "s", "controladores": ["EEVEE (Blender)"]},
    "renderizar_cycles_cpu": {"prueba_sonda": "render_cycles_cpu", "unidad": "s", "controladores": ["Cycles", "Embree"]},
    "renderizar_cycles_gpu": {"prueba_sonda": "render_cycles_gpu", "unidad": "s", "controladores": ["Cycles"]},
    "simplificar": {"prueba_sonda": None, "unidad": "s", "controladores": ["meshoptimizer"]},
    "booleana": {"prueba_sonda": None, "unidad": "s", "controladores": ["Manifold"]},
    "desenvolver_uv": {"prueba_sonda": None, "unidad": "s", "controladores": ["xatlas"]},
    "quitar_ruido": {"prueba_sonda": None, "unidad": "s", "controladores": ["Open Image Denoise"]},
}


def catalogo():
    return {"contrato": OPERACION, "operaciones": OPERACIONES}


@dataclass
class Estimacion:
    operacion: str
    nivel: str
    perfil: str | None
    valor: float | None
    unidad: str
    mediciones: int
    fuente: str                 # cubo | sin_datos

    def como_dict(self):
        return self.__dict__.copy()


class TablaCostos:
    """Medianas medidas por (nivel, prueba, perfil)."""

    def __init__(self, celdas=None):
        self.celdas = celdas or {}     # (nivel, prueba, perfil) → (mediana, n, unidad)

    @classmethod
    def desde_cubo(cls, con):
        filas = con.execute(
            "SELECT prueba, perfil, unidad, valor, dispositivo FROM v_mediciones_aceptadas WHERE fuente = 'sonda'"
        ).fetchall()
        grupos = {}
        for prueba, perfil, unidad, valor, dispositivo in filas:
            equipo = (json.loads(dispositivo) if isinstance(dispositivo, str) else dispositivo or {}).get("equipo", {})
            nivel = equipo.get("nivel")
            if nivel not in NIVELES:
                continue
            clave = (nivel, prueba, None if perfil in (None, "no_aplica") else perfil)
            grupos.setdefault(clave, {"unidad": unidad, "valores": []})["valores"].append(float(valor))
        celdas = {}
        for clave, g in grupos.items():
            v = sorted(g["valores"])
            n = len(v)
            celdas[clave] = ((v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2), n, g["unidad"])
        return cls(celdas)

    def estimar(self, operacion, equipo, perfil=None):
        if operacion not in OPERACIONES:
            raise KeyError(f"operación desconocida: {operacion}")
        nivel = equipo if equipo in NIVELES else clasificar(
            equipo if isinstance(equipo, Huella) else Huella.desde_dict(equipo)).nivel
        info = OPERACIONES[operacion]
        celda = self.celdas.get((nivel, info["prueba_sonda"], perfil)) if info["prueba_sonda"] else None
        if celda is None:
            return Estimacion(operacion, nivel, perfil, None, info["unidad"], 0, "sin_datos")
        mediana, n, unidad = celda
        return Estimacion(operacion, nivel, perfil, round(mediana, 3), unidad, n, "cubo")
