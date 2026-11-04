"""Decidir: el plan de ejecución para un equipo y una tarea (contrato g7b.plan/1).

Primera versión (FICHAS_TECNICAS 2.3, "más simple"): elegir el perfil de ajustes para la escena
completa, dónde trabajar (este equipo o el editor web) y qué versión de Blender usar. El plan trae
las ACCIONES como datos (ruta de la propiedad de Blender y valor); el cliente (add-on de Amatista)
guarda el valor anterior de cada una antes de aplicarla, y así «deshacer» es exacto.
"""
from .contratos import PLAN, Huella
from .niveles import clasificar
from .perfiles import elegir, generar

# El identificador del motor cambia entre versiones: el cliente usa el primero que exista en su Blender.
MOTORES = {
    "workbench": ["BLENDER_WORKBENCH"],
    "eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
    "cycles_gpu": ["CYCLES"],
    "cycles_cpu": ["CYCLES"],
}


def acciones_blender(perfil):
    """Ajustes del perfil → acciones sobre propiedades de la escena (sin importar bpy)."""
    a = perfil["ajustes"]
    motor = perfil.get("motor", "eevee")
    acciones = [{"ruta": "scene.render.engine", "valores_posibles": MOTORES.get(motor, MOTORES["eevee"]),
                 "por_que": f"motor {motor}"}]
    simplificar = perfil["perfil"] != "completo"
    acciones.append({"ruta": "scene.render.use_simplify", "valor": simplificar,
                     "por_que": "limita la subdivisión en la vista 3D" if simplificar else "sin límites"})
    if simplificar:
        acciones.append({"ruta": "scene.render.simplify_subdivision", "valor": a["subdivision_vista"],
                         "por_que": "nivel máximo de subdivisión en la vista"})
    acciones.append({"ruta": "scene.render.resolution_percentage", "valor": a["resolucion_pct"],
                     "por_que": "tamaño del render"})
    if motor.startswith("cycles"):
        acciones.append({"ruta": "scene.cycles.samples", "valor": a["muestras"], "por_que": "muestras de Cycles"})
        acciones.append({"ruta": "scene.cycles.device", "valor": "GPU" if motor == "cycles_gpu" else "CPU",
                         "por_que": "dónde renderiza Cycles"})
    elif motor == "eevee":
        acciones.append({"ruta": "scene.eevee.taa_render_samples", "valor": a["muestras"],
                         "por_que": "muestras de EEVEE"})
    return acciones


def _explicar(clasificacion, perfil):
    sugerencia = {"confiable": "medido en varios equipos como el tuyo",
                  "provisional": "medido, aún con pocas mediciones",
                  "base": "sugerido: todavía sin mediciones de equipos como el tuyo"}[perfil["estado"]]
    motivos = "; ".join(clasificacion.motivos[:2])
    if perfil["programa"] == "editor_web":
        return (f"Tu equipo es {clasificacion.nivel} ({motivos}). Blender de escritorio no corre aquí: "
                f"trabaja en el editor web de Amatista ({sugerencia}).")
    return (f"Tu equipo es {clasificacion.nivel} ({motivos}). Te recomendamos Blender {perfil['version']} "
            f"con el perfil {perfil['perfil']} ({sugerencia}). Puedes deshacerlo con un clic.")


def decidir(huella, tarea=None, perfiles=None, costos=None):
    """huella (Huella o dict) + tarea {"tipo": "practica", "blender": "4.5"} → plan g7b.plan/1."""
    tarea = tarea or {"tipo": "practica"}
    h = huella if isinstance(huella, Huella) else Huella.desde_dict(huella)
    clasificacion = clasificar(h)
    documento = perfiles or generar()
    perfil = elegir(documento, clasificacion.nivel, tarea.get("blender"))
    advertencias = []
    if clasificacion.confianza != "alta":
        advertencias.append("nivel estimado con datos incompletos: correr la sonda lo confirma")
    if tarea.get("blender") and perfil.get("version") and str(tarea["blender"]).split(".")[:2] != str(
            perfil["version"]).split("."):
        advertencias.append(f"la práctica pide Blender {tarea['blender']}; para este equipo se recomienda "
                            f"{perfil['version']}")
    plan = {
        "contrato": PLAN,
        "huella": h.id(),
        "clasificacion": clasificacion.como_dict(),
        "tarea": tarea,
        "donde": "editor_web" if perfil["programa"] == "editor_web" else "este_equipo",
        "programa": perfil["programa"],
        "version": perfil["version"],
        "perfil": {k: perfil[k] for k in ("perfil", "estado", "evidencia", "ajustes", "motor")},
        "acciones": [] if perfil["programa"] == "editor_web" else acciones_blender(perfil),
        "deshacer": "el cliente guarda el valor anterior de cada ruta antes de cambiarla y lo restaura",
        "advertencias": advertencias,
        "explicacion": _explicar(clasificacion, perfil),
        "perfiles_generados": documento.get("generado"),
    }
    if costos is not None and plan["programa"] == "blender":
        plan["estimaciones"] = [costos.estimar(op, clasificacion.nivel, perfil["perfil"]).como_dict()
                                for op in ("vista3d", "editar", "renderizar_eevee")]
    return plan
