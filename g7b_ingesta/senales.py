"""Señales de la comunidad: de los foros (destino «senales») a un resumen semanal en oro/senales/.

    python -m g7b_ingesta.senales
    python -m g7b_ingesta.senales --simulacro

Por fuente y semana ISO: temas nuevos, vistas, «me gusta», respuestas, cuántos tienen respuesta
aceptada y las etiquetas más usadas. Son cifras: dicen qué pregunta la gente y qué le importa, sin
guardar lo que escribió. Si existe MONGO_URI, el resumen también va a g7b_panel.senales (Atlas Charts).
"""
import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone

from g7b_lago import Lago

from . import catalogo as cat

HECHOS = "control/senales.json"
RESUMEN = "oro/senales/semanal.json"
ETIQUETAS_MAX = 30


def semana(registro):
    fecha = registro.get("fecha") or (registro.get("_g7b") or {}).get("extraido_en")
    try:
        dia = datetime.fromisoformat(str(fecha).replace("Z", "+00:00"))
    except ValueError:
        dia = datetime.now(timezone.utc)
    anio, numero, _ = dia.isocalendar()
    return f"{anio}-W{numero:02d}"


def _sumar(celda, registro):
    datos = registro.get("datos") or {}
    celda["temas"] += 1
    celda["vistas"] += int(datos.get("vistas") or 0)
    celda["me_gusta"] += int(datos.get("me_gusta") or 0)
    celda["respuestas"] += int(datos.get("respuestas") or 0)
    celda["con_respuesta_aceptada"] += 1 if datos.get("respuesta_aceptada") else 0
    etiquetas = Counter(celda.get("etiquetas") or {})
    etiquetas.update(registro.get("etiquetas") or [])
    celda["etiquetas"] = dict(etiquetas.most_common(ETIQUETAS_MAX))


def resumir(lago, catalogo, simulacro=False, salida=print):
    hechos = lago.leer_json(HECHOS, por_omision={}) or {}
    resumen = lago.leer_json(RESUMEN, por_omision={}) or {}
    nuevos = 0
    for fuente in cat.por_destino(catalogo, "senales"):
        for ruta in lago.listar(f"bronce/{fuente['id']}/"):
            if not ruta.endswith(".jsonl.gz") or ruta in hechos:
                continue
            registros = lago.leer_jsonl_gz(ruta)
            for registro in registros:
                celda = resumen.setdefault(fuente["id"], {}).setdefault(semana(registro), {
                    "temas": 0, "vistas": 0, "me_gusta": 0, "respuestas": 0,
                    "con_respuesta_aceptada": 0, "etiquetas": {}})
                _sumar(celda, registro)
            nuevos += len(registros)
            hechos[ruta] = {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "temas": len(registros)}
            salida(f"{ruta}: {len(registros)} temas")
    if not simulacro and nuevos:
        lago.escribir_json(RESUMEN, resumen)
        lago.escribir_json(HECHOS, hechos)
    return {"temas": nuevos, "resumen": resumen}


def al_panel(base, resumen):
    """Una fila por fuente y semana en g7b_panel.senales, para Atlas Charts."""
    coleccion = base["senales"]
    for fuente, semanas in resumen.items():
        for clave, celda in semanas.items():
            fila = {"fuente": fuente, "semana": clave, **{k: v for k, v in celda.items() if k != "etiquetas"},
                    "etiquetas": [{"etiqueta": e, "temas": n} for e, n in celda.get("etiquetas", {}).items()]}
            coleccion.update_one({"fuente": fuente, "semana": clave}, {"$set": fila}, upsert=True)


def main(argv=None):
    p = argparse.ArgumentParser(prog="senales")
    p.add_argument("--simulacro", action="store_true")
    o = p.parse_args(argv)
    resultado = resumir(Lago.desde_entorno(), cat.cargar(), simulacro=o.simulacro)
    if os.environ.get("MONGO_URI") and not o.simulacro and resultado["temas"]:
        import pymongo

        cliente = pymongo.MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=15000)
        try:
            al_panel(cliente[os.environ.get("MONGO_DATABASE_PANEL", "g7b_panel")], resultado["resumen"])
        finally:
            cliente.close()
    print(json.dumps({"temas": resultado["temas"], "fuentes": len(resultado["resumen"])}, ensure_ascii=False))
    return resultado


if __name__ == "__main__":
    main()
