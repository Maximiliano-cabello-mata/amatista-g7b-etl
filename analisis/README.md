# Análisis del cubo (Deepnote, Excel, tu PC)

El oro del warehouse es un archivo DuckDB (`oro/cubo.duckdb`) y sus Parquet. Se analiza sin servidor
de base de datos, desde tres lados, con el mismo cubo:

- **Tu PC o Deepnote:** `consulta.py` abre el cubo y corre SQL. En Deepnote, sube `oro/cubo.duckdb`
  (o conéctalo al lago) y pega las consultas en una celda.
- **Excel:** abre los CSV de `oro/csv/` (ya son tablas listas para tablas dinámicas).
- **Camber:** para lo pesado (vectores, lotes con GPU), lee los Parquet de `oro/parquet/` desde su
  cuaderno; el cubo no cambia, solo se lee.

El cubo es un **modelo en estrella**: hechos (`hechos_render`, `hechos_medicion`) y dimensiones
(`dim_dispositivo`, `dim_version`, `dim_escena`, `dim_perfil`, `dim_origen`, `dim_tiempo`). Ver
[docs/WAREHOUSE.md](../docs/WAREHOUSE.md).

## Correr las consultas de ejemplo

```bash
pip install duckdb
python analisis/consulta.py datos/oro/cubo.duckdb    # o la ruta donde tengas el cubo
```
