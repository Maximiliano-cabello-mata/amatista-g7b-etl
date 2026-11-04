"""Detectar: de la huella técnica al nivel del equipo (N0 a N4), con sus motivos.

Reglas de FICHAS_TECNICAS 3.1 (iniciales; el cubo las corregirá):

    N0  celular, tableta o Chromebook: solo navegador con WebGL 2          → editor web
    N1  GPU sin OpenGL 4.3, o RAM < 8 GB                                    → Blender 3.6 LTS, perfil mínimo
    N2  GPU integrada con OpenGL 4.3 o Vulkan; RAM de 8 a 16 GB             → Blender actual, perfil ligero
    N3  GPU dedicada de 4 a 8 GB de VRAM (aquí: de 4 a menos de 12)          → Blender completo, EEVEE fluido
    N4  GPU dedicada de 12 GB o más de VRAM                                 → Cycles en GPU, escenas pesadas

Si la RAM y la GPU dan niveles distintos, cuenta el más bajo. Cuando falta un dato, Geoda no
inventa: asume lo prudente y baja la confianza, y lo dice en los motivos.
"""
from dataclasses import dataclass, field

from .contratos import NIVELES, Huella

OPENGL_BLENDER_ACTUAL = 4.3   # mínimo desde Blender 4.0 (antes 3.3)
SO_MOVILES = {"android", "ios", "ipados", "chromeos", "chrome os"}


@dataclass
class Clasificacion:
    nivel: str
    confianza: str                     # alta | media | baja
    motivos: list = field(default_factory=list)

    def como_dict(self):
        return {"nivel": self.nivel, "confianza": self.confianza, "motivos": list(self.motivos)}


def _menor(*niveles):
    return min(niveles, key=NIVELES.index)


def _por_gpu(h, motivos):
    """Nivel que permite la GPU, y si el dato era completo."""
    dedicadas = [g for g in h.gpus if g.tipo == "dedicada"]
    if dedicadas:
        vram = max((g.vram_gb or 0) for g in dedicadas)
        if not vram:
            motivos.append("GPU dedicada sin dato de memoria de video: se asume N3")
            return "N3", False
        if vram >= 12:
            motivos.append(f"GPU dedicada con {vram:g} GB de VRAM")
            return "N4", True
        if vram >= 4:
            motivos.append(f"GPU dedicada con {vram:g} GB de VRAM")
            return "N3", True
        motivos.append(f"GPU dedicada con solo {vram:g} GB de VRAM")
        return ("N2", True) if (h.opengl or 0) >= OPENGL_BLENDER_ACTUAL or h.vulkan else ("N1", h.opengl is not None)
    if h.opengl is not None:
        if h.opengl >= OPENGL_BLENDER_ACTUAL or h.vulkan:
            motivos.append(f"GPU integrada con OpenGL {h.opengl:g}")
            return "N2", True
        motivos.append(f"OpenGL {h.opengl:g}: no alcanza el {OPENGL_BLENDER_ACTUAL} que pide el Blender actual")
        return "N1", True
    if h.vulkan:
        motivos.append("GPU con Vulkan")
        return "N2", True
    motivos.append("sin dato de OpenGL: se asume GPU integrada capaz (N2); medir con la sonda para confirmar")
    return "N2", False


def _por_ram(h, motivos):
    if h.ram_gb is None:
        motivos.append("sin dato de RAM")
        return "N4", False
    if h.ram_gb < 8:
        motivos.append(f"{h.ram_gb:g} GB de RAM: menos de 8")
        return "N1", True
    return "N4", True   # con 8 GB o más, la RAM no limita: decide la GPU


def clasificar(huella):
    """Huella (o dict g7b.huella/1, o el «equipo» de la sonda) → Clasificacion."""
    h = huella if isinstance(huella, Huella) else Huella.desde_dict(huella)
    if h.movil or h.so.strip().lower() in SO_MOVILES:
        return Clasificacion("N0", "alta", ["celular, tableta o Chromebook: Blender de escritorio no corre ahí"])
    motivos = []
    nivel_gpu, gpu_completo = _por_gpu(h, motivos)
    nivel_ram, ram_completo = _por_ram(h, motivos)
    nivel = _menor(nivel_gpu, nivel_ram)
    if nivel_gpu != nivel_ram and nivel == nivel_ram:
        motivos.append("cuenta el más bajo: la RAM limita")
    faltan = [not gpu_completo, not ram_completo].count(True)
    confianza = "alta" if faltan == 0 else ("media" if faltan == 1 else "baja")
    return Clasificacion(nivel, confianza, motivos)
