"""Consultas de ejemplo sobre el cubo de G7B (oro/cubo.duckdb).

Punto de entrada de ciencia de datos: abre el cubo en modo solo lectura y corre unas consultas
útiles. Sirve en tu PC, en Deepnote o en Camber. No escribe nada.

    python analisis/consulta.py ruta/al/cubo.duckdb
"""
import sys

import duckdb

CONSULTAS = {
    "Salud de los datos (cuántas filas por calidad)":
        "SELECT * FROM v_salud",
    "Render de Open Data por clase de equipo y versión LTS":
        "SELECT clase, version_corta, escena, dispositivos, muestras_min_mediana "
        "FROM v_render_por_clase WHERE es_lts AND renders >= 20 "
        "ORDER BY version_corta DESC, muestras_min_mediana DESC LIMIT 20",
    "Mediciones de la sonda por nivel (solo calidad ok)":
        "SELECT nivel, version_corta, prueba, perfil, equipos, mediana "
        "FROM v_medicion_por_nivel ORDER BY nivel, prueba, perfil",
    "Equipos que ha medido la sonda":
        "SELECT nivel, nombre, so, corridas, origenes FROM v_equipos_sonda ORDER BY nivel",
    "Cobertura: niveles y versiones con datos suficientes para un perfil confiable (>=5 medidas, >=3 equipos)":
        "SELECT d.nivel, v.version_corta, count(*) AS medidas, count(DISTINCT h.clave_dispositivo) AS equipos "
        "FROM hechos_medicion h JOIN dim_dispositivo d USING (clave_dispositivo) "
        "JOIN dim_version v USING (clave_version) "
        "WHERE h.calidad = 'ok' AND h.unidad = 'fps' GROUP BY ALL "
        "HAVING medidas >= 5 AND equipos >= 3 ORDER BY d.nivel",
}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        sys.exit("Uso: python analisis/consulta.py ruta/al/cubo.duckdb")
    con = duckdb.connect(argv[0], read_only=True)
    try:
        for titulo, sql in CONSULTAS.items():
            print(f"\n=== {titulo} ===")
            print(con.sql(sql))
    finally:
        con.close()


if __name__ == "__main__":
    main()
