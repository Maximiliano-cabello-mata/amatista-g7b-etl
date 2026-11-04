"""Consultar: perfiles de ajustes por nivel y versión de Blender (contrato g7b.perfil/1).

Dos fuentes, en este orden:
  1. el CUBO (mediciones reales de la sonda): el perfil más completo que mantiene la vista 3D
     «fluida» (30 fps o más de mediana) en ese nivel y versión;
  2. las REGLAS BASE de FICHAS_TECNICAS, para lo que todavía no tiene mediciones.

Cada perfil dice de dónde salió (estado) y con qué evidencia:
  confiable    5 mediciones o más de 3 equipos o más (meta H1)
  provisional  hay mediciones, pero aún no alcanzan
  base         regla inicial, sin mediciones: Amatista lo muestra como «sugerido»
"""
import json
from datetime import datetime, timezone

from . import VERSION
from .contratos import NIVELES, PERFIL, Huella, validar_perfiles
from .niveles import clasificar

# Los ajustes de la sonda (sonda/g7b_sonda.py, PERFILES), del más ligero al más completo.
AJUSTES = {
    "minimo": {"subdivision_vista": 0, "simplify": True, "muestras": 4, "resolucion_pct": 50},
    "ligero": {"subdivision_vista": 1, "simplify": False, "muestras": 16, "resolucion_pct": 75},
    "completo": {"subdivision_vista": 2, "simplify": False, "muestras": 64, "resolucion_pct": 100},
}
ORDEN = ("minimo", "ligero", "completo")
FLUIDO_FPS = 30.0
CONFIABLE = {"mediciones": 5, "equipos": 3}
METRICA_VISTA = "cuadros_por_segundo_vista3d"

# Reglas base (FICHAS_TECNICAS 3.1): qué corre en cada nivel cuando aún no hay mediciones.
BASE = {
    "N0": {"programa": "editor_web", "version": None, "perfil": "minimo", "motor": "webgl2",
           "nota": "Blender de escritorio no corre en este equipo: editor web de Amatista y A-Frame"},
    "N1": {"programa": "blender", "version": "3.6", "perfil": "minimo", "motor": "workbench",
           "nota": "Blender 3.6 LTS: el actual pide OpenGL 4.3"},
    "N2": {"programa": "blender", "version": "4.5", "perfil": "ligero", "motor": "eevee",
           "nota": "Blender LTS actual con perfil ligero"},
    "N3": {"programa": "blender", "version": "4.5", "perfil": "completo", "motor": "eevee",
           "nota": "Blender completo; EEVEE fluido"},
    "N4": {"programa": "blender", "version": "4.5", "perfil": "completo", "motor": "cycles_gpu",
           "nota": "Cycles en GPU, simulación y escenas pesadas"},
}


def _serie(version):
    """'4.5.3' → '4.5' (los perfiles se dan por serie de Blender)."""
    partes = str(version or "").split(".")
    return ".".join(partes[:2]) if len(partes) >= 2 else str(version or "")


def _perfil_base(nivel):
    b = BASE[nivel]
    return {"nivel": nivel, "programa": b["programa"], "version": b["version"], "perfil": b["perfil"],
            "motor": b["motor"], "ajustes": dict(AJUSTES[b["perfil"]]), "estado": "base",
            "evidencia": {"mediciones": 0, "equipos": 0, "fuente": "FICHAS_TECNICAS 3.1"}, "nota": b["nota"]}


def leer_cubo(con):
    """Mediciones aceptadas de vista 3D de la sonda, con el nivel de su equipo.

    Usa la vista v_mediciones_aceptadas del cubo (g7b_almacen/cubo.py). Si el equipo trae su nivel
    (sonda con --nivel o con la captura que lo conserva) se usa; si no, Geoda lo clasifica con su
    huella; si ni así se puede, la medición no cuenta (no se adivina).
    """
    filas = con.execute(
        "SELECT valor, version, perfil, dispositivo FROM v_mediciones_aceptadas "
        "WHERE fuente = 'sonda' AND prueba = 'vista3d' AND unidad = 'fps' AND sin_ventana IS FALSE "
        "AND metrica = ? AND perfil IS NOT NULL AND perfil <> 'no_aplica'",
        [METRICA_VISTA]).fetchall()
    salida, sin_nivel = [], 0
    for valor, version, perfil, dispositivo in filas:
        equipo = (json.loads(dispositivo) if isinstance(dispositivo, str) else dispositivo or {}).get("equipo", {})
        nivel = equipo.get("nivel")
        if nivel not in NIVELES:
            try:
                nivel = clasificar(Huella.desde_dict(equipo)).nivel if equipo.get("gpu_cycles") or equipo.get(
                    "gpu_vista") else None
            except ValueError:
                nivel = None
        if nivel is None:
            sin_nivel += 1
            continue
        salida.append({"nivel": nivel, "version": _serie(version), "perfil": perfil, "fps": float(valor),
                       "equipo": equipo.get("huella") or "sin_huella"})
    return salida, sin_nivel


def _mediana(valores):
    v = sorted(valores)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def desde_mediciones(mediciones):
    """Para cada (nivel, versión): el perfil más completo que es fluido; si ninguno lo es, el mínimo."""
    celdas = {}
    for m in mediciones:
        celdas.setdefault((m["nivel"], m["version"]), {}).setdefault(m["perfil"], []).append(m)
    perfiles = []
    for (nivel, version), por_perfil in sorted(celdas.items()):
        elegido, fluido = None, False
        for nombre in reversed(ORDEN):  # del más completo al más ligero
            if nombre in por_perfil and _mediana([m["fps"] for m in por_perfil[nombre]]) >= FLUIDO_FPS:
                elegido, fluido = nombre, True
                break
        if elegido is None:
            elegido = next((n for n in ORDEN if n in por_perfil), None)
        if elegido is None:
            continue
        datos = por_perfil[elegido]
        n, equipos = len(datos), len({m["equipo"] for m in datos if m["equipo"] != "sin_huella"})
        confiable = fluido and n >= CONFIABLE["mediciones"] and equipos >= CONFIABLE["equipos"]
        perfiles.append({
            "nivel": nivel, "programa": "blender", "version": version, "perfil": elegido,
            "motor": BASE[nivel]["motor"], "ajustes": dict(AJUSTES.get(elegido, {})),
            "estado": "confiable" if confiable else "provisional",
            "evidencia": {"mediciones": n, "equipos": equipos, "fps_mediana": round(_mediana([m["fps"] for m in datos]), 1),
                          "fluido": fluido, "fuente": "cubo"},
            "nota": "" if fluido else "ningún perfil medido alcanza 30 fps: se recomienda el más ligero",
        })
    return perfiles


def generar(mediciones=(), sin_nivel=0, cubo_version=None, ahora=None):
    """Documento g7b.perfil/1: lo medido manda; las reglas base cubren lo que falta."""
    medidos = desde_mediciones(mediciones)
    con_datos = {p["nivel"] for p in medidos}
    perfiles = medidos + [_perfil_base(n) for n in NIVELES if n not in con_datos]
    perfiles.sort(key=lambda p: (NIVELES.index(p["nivel"]), str(p["version"])))
    documento = {
        "contrato": PERFIL,
        "generado": (ahora or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "geoda": VERSION,
        "cubo": cubo_version,
        "fluidez_fps": FLUIDO_FPS,
        "regla_confiable": CONFIABLE,
        "mediciones_sin_nivel": sin_nivel,
        "perfiles": perfiles,
    }
    errores = validar_perfiles(documento)
    if errores:
        raise ValueError("perfiles inválidos: " + "; ".join(errores))
    return documento


def elegir(documento, nivel, version=None):
    """El perfil para un nivel (y versión si se pide): primero lo medido, luego la regla base."""
    candidatos = [p for p in documento["perfiles"] if p["nivel"] == nivel]
    if version:
        exactos = [p for p in candidatos if p.get("version") == _serie(version)]
        candidatos = exactos or candidatos
    rango = {"confiable": 0, "provisional": 1, "base": 2}
    candidatos.sort(key=lambda p: (rango[p["estado"]], -(p.get("evidencia") or {}).get("mediciones", 0)))
    return candidatos[0] if candidatos else _perfil_base(nivel)
