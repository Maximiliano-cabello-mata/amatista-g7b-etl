"""Resume la integridad y los estados de una copia local del cubo de telemetría."""
import argparse
import json
from pathlib import Path

import duckdb


def revisar(ruta):
    if not ruta.is_file():
        raise FileNotFoundError(ruta)
    with duckdb.connect(str(ruta), read_only=True) as con:
        datos = con.execute("""
            SELECT count(*) AS filas,
                   count(DISTINCT nullif(trim(id), '')) AS ids_distintos,
                   count(*) FILTER (WHERE nullif(trim(id), '') IS NULL) AS sin_id,
                   count(*) FILTER (WHERE nullif(trim(unidad), '') IS NULL) AS sin_unidad,
                   count(*) FILTER (WHERE valor IS NULL OR NOT isfinite(valor)) AS sin_valor_finito
            FROM mediciones
        """)
        resumen = dict(zip([c[0] for c in datos.description], datos.fetchone()))
        grupos = con.execute("""
            SELECT fuente, estado, count(*) FROM mediciones
            GROUP BY fuente, estado ORDER BY fuente, estado
        """).fetchall()
    resumen["repeticiones_de_id"] = resumen["filas"] - resumen["sin_id"] - resumen["ids_distintos"]
    resumen["por_fuente_y_estado"] = [
        {"fuente": fuente, "estado": estado, "filas": n} for fuente, estado, n in grupos
    ]
    return resumen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cubo", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(revisar(args.cubo), ensure_ascii=False, indent=2))
    except (OSError, duckdb.Error) as exc:
        parser.exit(1, f"No se pudo leer el cubo: {exc}\n")
