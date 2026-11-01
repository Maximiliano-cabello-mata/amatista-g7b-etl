"""Copia al lago (zona bronce) los resultados de los trabajos terminados en Zyte Scrapy Cloud.

Zyte guarda los resultados 120 días; el lago los guarda para siempre y sin tocar.
Cada trabajo se copia una sola vez: los ya copiados se anotan en control/zyte_trabajos.json.

    python -m g7b_lago.zyte_a_lago                 # copia lo nuevo
    python -m g7b_lago.zyte_a_lago --simulacro     # solo dice qué copiaría

Variables: ZYTE_API_KEY, ZYTE_PROJECT_ID (por omisión, el de scrapinghub.yml) y las del lago (lago.py).
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

from .lago import Lago, ruta_bronce

CONTROL = "control/zyte_trabajos.json"
PROYECTO_POR_OMISION = "883618"


def huella(registro):
    return hashlib.sha256(json.dumps(registro, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _fecha_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc) if ms else datetime.now(timezone.utc)


def con_procedencia(registro, trabajo, arana, extraido):
    """Agrega de dónde vino cada registro (regla 5 de calidad) sin tocar sus campos."""
    return {**registro, "_g7b": {"fuente": "zyte", "trabajo": trabajo, "arana": arana,
                                 "extraido_en": extraido, "huella": huella(registro)}}


def copiar(cliente, proyecto_id, lago, simulacro=False, maximo=None, salida=print):
    control = lago.leer_json(CONTROL, por_omision={"copiados": {}})
    copiados = control["copiados"]
    proyecto = cliente.get_project(int(proyecto_id))
    pendientes = [t for t in proyecto.jobs.iter(state="finished", meta=["spider", "finished_time", "close_reason"])
                  if t["key"] not in copiados]
    pendientes.sort(key=lambda t: t.get("finished_time") or 0)
    if maximo:
        pendientes = pendientes[:maximo]
    resumen = {"pendientes": len(pendientes), "copiados": 0, "registros": 0, "ya_existian": 0}
    for trabajo in pendientes:
        clave, arana = trabajo["key"], trabajo.get("spider", "desconocida")
        terminado = _fecha_ms(trabajo.get("finished_time"))
        ruta = ruta_bronce(f"zyte/{arana}", clave.replace("/", "-") + ".jsonl.gz", terminado.date())
        if simulacro:
            salida(f"[simulacro] {clave} ({arana}, {trabajo.get('close_reason')}) -> {ruta}")
            continue
        extraido = terminado.isoformat(timespec="seconds")
        registros = (con_procedencia(r, clave, arana, extraido) for r in cliente.get_job(clave).items.iter())
        subido, cantidad = lago.subir_jsonl_gz(ruta, registros, metadatos={
            "fuente": "zyte", "trabajo": clave, "arana": arana, "motivo_cierre": trabajo.get("close_reason")})
        if subido:
            resumen["copiados"] += 1
            resumen["registros"] += cantidad
        else:
            resumen["ya_existian"] += 1
        copiados[clave] = {"ruta": ruta, "registros": cantidad, "arana": arana,
                           "copiado_en": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        lago.escribir_json(CONTROL, control)  # tras cada trabajo: si algo falla, no se repite lo hecho
        salida(f"{clave} ({arana}): {cantidad} registros -> {ruta}" + ("" if subido else " (ya existía)"))
    return resumen


def main(argv=None):
    p = argparse.ArgumentParser(prog="zyte_a_lago")
    p.add_argument("--simulacro", action="store_true", help="no copia nada, solo lista")
    p.add_argument("--maximo", type=int, help="cuántos trabajos copiar como máximo")
    opciones = p.parse_args(argv)
    clave = os.environ.get("ZYTE_API_KEY")
    if not clave:
        sys.exit("Falta ZYTE_API_KEY.")
    from scrapinghub import ScrapinghubClient

    resumen = copiar(ScrapinghubClient(clave), os.environ.get("ZYTE_PROJECT_ID", PROYECTO_POR_OMISION),
                     Lago.desde_entorno(), simulacro=opciones.simulacro, maximo=opciones.maximo)
    print(json.dumps(resumen, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    main()
