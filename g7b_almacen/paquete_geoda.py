"""Construye y publica el paquete de conocimiento de Geoda (g7b.geoda.paquete/1) desde el cubo del lago.

    python -m g7b_almacen.paquete_geoda --trabajo /tmp/geoda --publico publicacion/geoda_paquete.json

1. Descarga el cubo vigente (control/cubo_actual.json) y verifica sus huellas (descargar.py).
2. Construye el paquete con el cubo y comprueba cada cita del manual contra los objects.inv.
3. Lo publica en el lago, inmutable (oro/geoda/<versión>/paquete.json), y mueve el puntero
   control/geoda_paquete_actual.json; y deja la copia pública en el repositorio (--publico).

Si el contenido no cambió (mismas huellas de sección), no publica una versión nueva.
"""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb

from geoda import paquete as paq

from .cubo import ACTUAL
from .descargar import descargar

PUNTERO = "control/geoda_paquete_actual.json"


def publicar(lago, documento, publico=None):
    """Sube el paquete y mueve el puntero. Devuelve el puntero, o None si no cambió nada."""
    errores = paq.validar(documento)
    if errores:
        raise ValueError("paquete inválido: " + "; ".join(errores))
    anterior = lago.leer_json(PUNTERO)
    if anterior and anterior.get("huellas") == documento["huellas"]:
        return None
    datos = (json.dumps(documento, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    ruta = f"oro/geoda/{documento['version']}/paquete.json"
    lago.subir_bytes(ruta, datos, tipo="application/json")
    puntero = {"contrato": paq.CONTRATO, "version": documento["version"], "ruta": ruta,
               "sha256": hashlib.sha256(datos).hexdigest(), "bytes": len(datos),
               "generado": documento["generado"], "huellas": documento["huellas"],
               "evidencia": documento["evidencia"]}
    lago.escribir_json(PUNTERO, puntero)
    if publico:
        Path(publico).parent.mkdir(parents=True, exist_ok=True)
        Path(publico).write_bytes(datos)
    return puntero


def construir_desde_lago(lago, trabajo, verificar_manual=True):
    trabajo = Path(trabajo)
    trabajo.mkdir(parents=True, exist_ok=True)
    base = trabajo / "cubo.duckdb"
    if base.exists():
        base.unlink()
    descarga = descargar(lago, base)
    puntero = lago.leer_json(ACTUAL)
    manifiesto = json.loads(lago.contenedor.download_blob(puntero["manifiesto"]).readall())
    cubo = {"contrato": manifiesto.get("contrato"), "version": descarga["version"], "sha256": descarga["sha256"],
            **{k: manifiesto.get(k) for k in ("generado", "mediciones", "directas", "relativas")}}
    inventarios = paq.inventarios_manual() if verificar_manual else None
    with duckdb.connect(str(base), read_only=True) as con:
        return paq.construir(con, cubo, inventarios)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--trabajo", required=True, help="carpeta temporal para el cubo")
    p.add_argument("--publico", help="dónde dejar la copia pública (p. ej. publicacion/geoda_paquete.json)")
    p.add_argument("--sin-manual", action="store_true", help="no descargar los objects.inv")
    a = p.parse_args(argv)
    from g7b_lago import Lago

    lago = Lago.desde_entorno()
    documento = construir_desde_lago(lago, a.trabajo, verificar_manual=not a.sin_manual)
    puntero = publicar(lago, documento, a.publico)
    print("GEODA_PAQUETE", json.dumps({"version": documento["version"], "publicado": puntero is not None,
                                        **documento["evidencia"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
