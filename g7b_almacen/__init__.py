"""El warehouse de G7B: bronce → plata (Parquet) → cubo en DuckDB (oro) → perfiles y tablero.

Ver docs/WAREHOUSE.md. Los módulos:

    almacen     dónde se leen y escriben los archivos: una carpeta local o el lago de Azure
    opendata    descarga y lectura de Blender Open Data (CC0)
    plata       filas limpias de Open Data y de la sonda (contrato g7b.medicion/1)
    cubo        el modelo en estrella en DuckDB y sus exportaciones (Parquet, CSV, resumen)
    perfiles    perfiles.json v0 (contrato g7b.perfil/1) a partir de las mediciones
    vigia       monitores de Sentry para las tareas programadas (opcional)
"""
