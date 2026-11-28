"""Comprueba las unidades que declaran los productores de g7b.telemetria/1."""
import argparse
import json
from pathlib import Path

import duckdb


# Nombres publicados por sonda/g7b_sonda.py y g7b_telemetria/capturar.py.
UNIDADES = {
    "sonda": {
        "tiempo_edicion": "s",
        "tiempo_primera_evaluacion": "s",
        "tiempo_render_cycles_cpu": "s",
        "tiempo_render_cycles_gpu": "s",
        "tiempo_render_eevee": "s",
        "tiempo_render_workbench": "s",
        "cuadros_por_segundo_animacion": "fps",
        "cuadros_por_segundo_vista3d": "fps",
    },
    "blender-open-data": {"samples_per_minute": "samples/min"},
}


def revisar(ruta):
    with duckdb.connect(str(ruta), read_only=True) as con:
        grupos = con.execute("""
            SELECT fuente, metrica, unidad, count(*)
            FROM mediciones
            GROUP BY fuente, metrica, unidad
            ORDER BY fuente, metrica, unidad
        """).fetchall()

    informe = {"filas": 0, "conformes": 0, "incompatibles": 0, "sin_regla": 0, "hallazgos": []}
    for fuente, metrica, unidad, filas in grupos:
        informe["filas"] += filas
        esperada = UNIDADES.get(fuente, {}).get(metrica)
        if esperada is not None and esperada == unidad:
            informe["conformes"] += filas
            continue
        estado = "sin_regla" if esperada is None else "incompatibles"
        informe[estado] += filas
        informe["hallazgos"].append({"fuente": fuente, "metrica": metrica, "observada": unidad,
                                     "esperada": esperada, "filas": filas, "resultado": estado})
    return informe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cubo", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(revisar(args.cubo), ensure_ascii=False, indent=2))
    except (OSError, duckdb.Error) as exc:
        parser.exit(1, f"No se pudo revisar el contrato: {exc}\n")
