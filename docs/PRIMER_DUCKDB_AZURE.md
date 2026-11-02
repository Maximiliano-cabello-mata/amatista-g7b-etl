# Primera construcción de DuckDB con la medición real de Blender

**Estado:** experimentación aislada, ejecutada y verificada en GitHub Actions.

## Evidencia de la ejecución

- [Workflow completado](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41380886305).
- La prueba obtuvo el JSON de la sonda del experimento anterior, cuya subida y SHA-256 ya habían sido verificados en Azure.
- **Origen en Azure:** `lago/tmp/pruebas-blender/41379915232-intento1/medicion.json`.
- **Destino aislado:** `lago/tmp/pruebas-duckdb/41380886305-intento1/`.
- **7 hechos de medición** de **1 corrida** de Blender 4.5.15 LTS.
- **Compuerta de calidad: aprobada**; la ausencia de Open Data se trata como aviso, no como datos ficticios.
- **23 objetos subidos y verificados** mediante lectura de vuelta y SHA-256.
- 6 pruebas específicas del paso superadas y 80 pruebas de la suite general superadas.

## Localización exacta de los archivos

Abre [Azure Portal](https://portal.azure.com/) → cuenta de almacenamiento de G7B → contenedor `lago` → `tmp/pruebas-duckdb/41380886305-intento1/`.

Entre los archivos encontrarás:

```text
oro/
  cubo.duckdb                     # Archivo real de la base analítica DuckDB
  perfiles.json                  # Resultados provisionales por nivel
  resumen.json
  calidad.json
  parquet/
    hechos_medicion.parquet
    dim_dispositivo.parquet
    ... (hechos y dimensiones)
  csv/
    v_medicion_por_nivel.csv
    ... (vistas para Excel)
plata/
  sonda/medicion.parquet
publicado/
  actual.json                    # Snapshot aprobado en ESTE laboratorio
  versiones/<hash>/*.json
verificacion_duckdb.json          # Rutas, hashes y conteos del experimento
```

El manifiesto `publicado/actual.json` fue generado en el almacén local aislado;
sus rutas son **relativas a esta carpeta de experimento**, no a la raíz del lago
productivo. Amatista no debe usarlo como un perfil publicado en producción.

## Consultar la base

Descarga únicamente `oro/cubo.duckdb` desde la carpeta de prueba al equipo local.
Con `pip install duckdb`, puedes inspeccionarlo sin instalar un servidor:

```python
import duckdb

db = duckdb.connect("cubo.duckdb", read_only=True)
print(db.sql("SELECT prueba, perfil, mediana, unidad, calidad FROM hechos_medicion ORDER BY prueba, perfil"))
print(db.sql("SELECT * FROM v_salud"))
db.close()
```

**Interpretación:** 7 hechos no son 7 computadoras. Son pruebas realizadas en una
sola máquina temporal de GitHub Actions (5 medidas y 2 indisponibles por
ejecutarse sin ventana). Aunque la compuerta de integridad apruebe los datos,
las recomendaciones de rendimiento siguen siendo provisionales y no se pueden
generalizar a equipos de estudiantes.

## Cómo se construyó

`g7b_lago/prueba_duckdb_aislada.py` descarga y valida el JSON original,
construye el warehouse usando `g7b_almacen` en un directorio temporal, comprueba
las tablas por SQL, aplica la compuerta y copia exclusivamente a `tmp/pruebas-duckdb`.

El workflow `.github/workflows/construir_duckdb_aislado.yml` utiliza el secreto
`AZURE_LAGO_URL` del environment `amatista1`. No crea servidor SQL, no
escribe en `bronce/`, `plata/`, `oro/`, `publicado/` o `control/` de
producción, y no usa MongoDB. No imprimir el valor de `AZURE_LAGO_URL`.

La política actual de Azure elimina `tmp/` a los 7 días: este primer resultado
es deliberadamente efímero. Para conservarlo habrá que incorporar después el
pipeline definitivo y su validación en las rutas persistentes.

## Siguiente hito

Ejecutar mediciones en varios equipos reales con ventana, importar una muestra
auténtica de Blender Open Data, revisar calidad y cobertura antes de publicar
el warehouse definitivo y conectarlo a Amatista.
