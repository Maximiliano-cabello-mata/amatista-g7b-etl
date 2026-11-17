"""Corre los casos de conformidad (geoda/conformidad.json) contra el núcleo de Geoda.

Cualquier implementación del núcleo (esta en Python, o una portable futura) debe pasarlos con
cualquier paquete válido. Sin paquete, se usa uno de solo reglas base (sin cubo ni red).
"""
import json
import os

from . import paquete as paq
from .nucleo import Nucleo

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conformidad.json")


def casos(ruta=RUTA):
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)["casos"]


def plan_de(nucleo, entrada):
    """La entrada de un caso → plan. «huella» va tal cual; si no, se arma desde datos sueltos."""
    if "huella" in entrada:
        huella = entrada["huella"]
    else:
        huella = nucleo.huella(**{k: entrada[k] for k in ("gpu", "ram_gb", "so", "opengl", "vulkan", "movil", "cpu")
                                  if k in entrada})
    tarea = {"tipo": "practica", **({"blender": entrada["blender"]} if entrada.get("blender") else {})}
    return nucleo.decidir(huella, tarea, entrada.get("idioma", "es"))


def revisar(plan, espera):
    """Lista de diferencias entre el plan y lo esperado (vacía si cumple)."""
    fallas = []
    c, rutas = plan["clasificacion"], [a["ruta"] for a in plan["acciones"]]
    citas = [x for a in plan["acciones"] for x in a["citas"]] + plan["ayuda"]

    def falla(texto):
        fallas.append(texto)

    if "nivel" in espera and c["nivel"] != espera["nivel"]:
        falla(f"nivel {c['nivel']} y se esperaba {espera['nivel']}")
    if espera.get("confianza_no_alta") and c["confianza"] == "alta":
        falla("confianza alta con datos incompletos")
    if "programa" in espera and plan.get("programa") != espera["programa"]:
        falla(f"programa {plan.get('programa')} y se esperaba {espera['programa']}")
    if "version_base" in espera and plan["perfil"]["estado"] == "base" and str(plan["version"]) != espera["version_base"]:
        falla(f"versión {plan['version']} y se esperaba {espera['version_base']} (regla base)")
    if "acciones" in espera and rutas != espera["acciones"]:
        falla(f"acciones {rutas} y se esperaba {espera['acciones']}")
    for ruta in espera.get("acciones_incluyen", []):
        if ruta not in rutas:
            falla(f"falta la acción {ruta}")
    if espera.get("acciones_con_cita"):
        for a in plan["acciones"]:
            if not a["citas"]:
                falla(f"la acción {a['ruta']} no cita el manual")
    if len(plan["ayuda"]) < espera.get("ayuda_minima", 0):
        falla("falta la ayuda general del nivel")
    if "citas_version" in espera and any(x["version"] != espera["citas_version"] for x in citas):
        falla(f"hay citas de otra versión que {espera['citas_version']}")
    if espera.get("citas_siguen_al_plan") and any(x["version"] != str(plan["version"]) for x in citas):
        falla("las citas no son de la versión que recomienda el plan")
    if espera.get("con_advertencia") and not plan["advertencias"]:
        falla("falta la advertencia")
    if "citas_idioma" in espera and any(x["idioma"] != espera["citas_idioma"] for x in citas):
        falla(f"hay citas en otro idioma que {espera['citas_idioma']}")
    relativa = plan["evidencia"]["estimacion_relativa"]
    if "estimacion_relativa" in espera and relativa != espera["estimacion_relativa"]:
        falla("estimación relativa distinta de la esperada")
    # Reglas que valen para todos los casos:
    if plan["evidencia"]["escalera"] not in ("medido", "provisional", "regla_base"):
        falla("escalera de evidencia desconocida")
    if relativa is not None and relativa.get("clase_dato") != "relativa":
        falla("una estimación pública no está marcada como relativa")
    if plan["evidencia"]["escalera"] == "medido" and plan["perfil"]["estado"] != "confiable":
        falla("se dice medido sin perfil confiable")
    return fallas


def correr(paquete=None, ruta=RUTA):
    nucleo = Nucleo(paq.leer(paquete) if paquete else paq.construir())
    resultados, fallas = [], 0
    for caso in casos(ruta):
        try:
            plan = plan_de(nucleo, caso["entrada"])
            problemas = ["se esperaba un error y hubo plan"] if caso["espera"].get("error") else revisar(plan, caso["espera"])
        except ValueError as error:
            problemas = [] if caso["espera"].get("error") else [f"error: {error}"]
        fallas += bool(problemas)
        resultados.append({"id": caso["id"], "ok": not problemas, **({"problemas": problemas} if problemas else {})})
    return {"api": "geoda.nucleo/1", "paquete": nucleo.paquete["version"], "casos": len(resultados),
            "fallas": fallas, "resultados": resultados}
