"""Grupo de rendimiento de un procesador: marca, gama, generación y segmento (portátil o escritorio).

Sirve para comparar equipos con gráficos integrados básicos, que no pueden renderizar con Cycles en
la GPU: ahí lo que cuenta es el procesador. «Intel Core i3-10110U» → «intel-core-i3-g10-portatil».

Es parte del kernel (no de la tabla de hardware) porque el núcleo lo necesita para leer la sección
render_cpu del paquete; una implementación portable debe reproducirlo (geoda/conformidad.json).
Sin adivinar: lo que no sigue la nomenclatura de Intel Core iN o AMD Ryzen N devuelve None.
"""
import re

_INTEL = re.compile(r"\bi([3579])-(\d{4,5})([a-z]{0,2}\d?)\b", re.I)
_RYZEN = re.compile(r"\bryzen ([3579]) (\d)(\d{3})([a-z0-9]{0,3})\b", re.I)
# Sufijos de portátil. El resto (sin sufijo, K, F, KF, T, E) es de escritorio.
_PORTATIL_INTEL = re.compile(r"^(u|y|h|hk|hs|hx|p|g\d|ng\d|m)$", re.I)
_PORTATIL_RYZEN = re.compile(r"^(u|h|hs|hx|c)$", re.I)


def grupo(nombre):
    texto = " ".join(str(nombre or "").replace("(R)", "").replace("(TM)", "").replace("(tm)", "").split())
    m = _INTEL.search(texto)
    if m:
        gama, numero, sufijo = m.group(1), m.group(2), m.group(3) or ""
        if len(numero) == 5 or numero[0] == "1":  # i3-10110U, i5-12450H; i3-1005G1, i5-1135G7, i3-1215U
            generacion = numero[:2]
        else:                                     # i3-8100, i7-9750H
            generacion = numero[0]
        segmento = "portatil" if _PORTATIL_INTEL.match(sufijo) else "escritorio"
        return f"intel-core-i{gama}-g{generacion}-{segmento}"
    m = _RYZEN.search(texto)
    if m:
        segmento = "portatil" if _PORTATIL_RYZEN.match(m.group(4) or "") else "escritorio"
        return f"amd-ryzen-{m.group(1)}-g{m.group(2)}-{segmento}"
    return None


def legible(clave):
    """«intel-core-i3-g10-portatil» → «Intel Core i3 de 10.ª generación (portátil)»."""
    if not clave:
        return None
    partes = clave.split("-")
    segmento = "portátil" if partes[-1] == "portatil" else "escritorio"
    generacion = partes[-2][1:]
    if partes[0] == "intel":
        return f"Intel Core {partes[2]} de {generacion}.ª generación ({segmento})"
    return f"AMD Ryzen {partes[2]} serie {generacion}000 ({segmento})"
