"""Tablero HTML autónomo y de solo lectura para el warehouse DuckDB de G7B.

No instala servidor, no llama Azure desde el navegador y no incluye secretos.
El proceso de generación lee DuckDB y los JSON aprobados de la carpeta de
experimento, prepara filas seguras y las incrusta en un HTML que abre offline.

Ejemplo:
    python -m g7b_almacen.tablero \
      --cubo datos/oro/cubo.duckdb \
      --resumen datos/oro/resumen.json \
      --perfiles datos/oro/perfiles.json \
      --calidad datos/oro/calidad.json \
      --salida tablero.html
"""
import argparse
import json
from pathlib import Path

import duckdb

PLANTILLA = Path(__file__).with_name("tablero.html")
MARCADOR = "__G7B_DATOS_JSON__"


def _filas(con, consulta):
    cursor = con.execute(consulta)
    nombres = [c[0] for c in cursor.description]
    return [
        {k: (v.isoformat() if hasattr(v, "isoformat") else v)
         for k, v in zip(nombres, valores)}
        for valores in cursor.fetchall()
    ]


def _leer_json(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def extraer(cubo, resumen, perfiles, calidad):
    """Vista de consulta: elimina huellas y nombres de equipo del HTML exportado."""
    con = duckdb.connect(str(cubo), read_only=True)
    try:
        mediciones = _filas(con, """
            SELECT fecha, origen, nivel_medido AS nivel, escena, prueba, perfil,
                   metrica, unidad, mediana, variacion, repeticiones, calidad, motivo,
                   sin_ventana
            FROM hechos_medicion
            ORDER BY fecha DESC, prueba, perfil
            LIMIT 5000
        """)
        total = con.execute("SELECT count(*) FROM hechos_medicion").fetchone()[0]
        corridas = con.execute(
            "SELECT count(DISTINCT medicion_id) FROM hechos_medicion"
        ).fetchone()[0]
        equipos = con.execute(
            "SELECT count(DISTINCT clave_dispositivo) FROM hechos_medicion"
        ).fetchone()[0]
        renders = con.execute("SELECT count(*) FROM hechos_render").fetchone()[0]
        calidad_sonda = _filas(con, "SELECT * FROM v_salud")
        por_nivel = _filas(con, "SELECT * FROM v_medicion_por_nivel LIMIT 1000")
    finally:
        con.close()
    if total > 5000:
        # No truncar silenciosamente: la interfaz es una inspección, no una consulta total.
        advertencia = "Vista limitada a las 5000 filas más recientes."
    else:
        advertencia = ""
    doc_resumen = _leer_json(resumen)
    doc_perfiles = _leer_json(perfiles)
    doc_calidad = _leer_json(calidad)
    if not doc_calidad.get("aprobado"):
        raise ValueError("No se genera un tablero con calidad rechazada")
    if doc_perfiles.get("contrato") != "g7b.perfil/1":
        raise ValueError("El JSON de perfiles no cumple el contrato")
    return {
        "version_tablero": "g7b.tablero/1",
        "generado": doc_calidad.get("generado"),
        "alcance": "Experimento aislado. No representa todavía a los alumnos.",
        "advertencia": advertencia,
        "conteos": {
            "filas": total, "corridas": corridas, "equipos": equipos,
            "renders": renders,
            "validas": sum(r["calidad"] == "ok" for r in mediciones),
            "no_disponibles": sum(r["calidad"] == "no_disponible" for r in mediciones),
        },
        "mediciones": mediciones,
        "por_nivel": por_nivel,
        "salud": calidad_sonda,
        "calidad": doc_calidad,
        "perfiles": doc_perfiles.get("perfiles", []),
        "resumen": {
            "conteos": doc_resumen.get("conteos", {}),
            "conocimiento": doc_resumen.get("conocimiento", {}),
        },
    }


def generar(cubo, resumen, perfiles, calidad, salida):
    datos = extraer(cubo, resumen, perfiles, calidad)
    origen = PLANTILLA.read_text(encoding="utf-8")
    if origen.count(MARCADOR) != 1:
        raise RuntimeError("La plantilla debe tener exactamente un marcador de datos")
    # Evita que cualquier campo externo rompa el script con HTML inyectado.
    contenido = json.dumps(datos, ensure_ascii=False, allow_nan=False).replace(
        "<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026"
    )
    destino = Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(origen.replace(MARCADOR, contenido), encoding="utf-8")
    return datos


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for nombre in ("cubo", "resumen", "perfiles", "calidad", "salida"):
        p.add_argument("--" + nombre, required=True)
    a = p.parse_args(argv)
    datos = generar(a.cubo, a.resumen, a.perfiles, a.calidad, a.salida)
    print(json.dumps({
        "estado": "G7B_TABLERO_GENERADO",
        "salida": str(Path(a.salida).resolve()),
        "filas": datos["conteos"]["filas"],
        "corridas": datos["conteos"]["corridas"],
        "equipos": datos["conteos"]["equipos"],
        "calidad_aprobada": datos["calidad"]["aprobado"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
