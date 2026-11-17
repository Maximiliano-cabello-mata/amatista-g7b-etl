# Cubo v2: contrato analítico para Geoda

## Decisión y alcance

El contrato `g7b.cubo/2` reorganiza el archivo analítico reconstruible a partir de
`g7b.telemetria/1`. Conserva Azure Blob, Parquet y DuckDB; no introduce un servidor
relacional ni migra MongoDB. El conocimiento documental sigue separado del rendimiento.

El grano es **una observación agregada por ID de telemetría**: una prueba, escena,
perfil, versión de software, configuración declarada y métrica. Las repeticiones de
una prueba no cuentan como computadoras ni como observaciones independientes.

## Modelo de consumo

| Objeto | Responsabilidad |
|---|---|
| `mediciones` | Única tabla física de observaciones; conserva IDs y huellas de entrada |
| `hechos_medicion`, `hechos_render` | Vistas compatibles por fuente; ya no son copias físicas |
| `dim_dispositivo` | Configuración declarada, CPU, RAM numérica, SO, arquitectura, backend y etiqueta; JSON original conservado |
| `dim_metrica` | Métrica, unidad, dirección de mejora y carácter no aditivo |
| `dim_version`, `dim_escena`, `dim_perfil`, `dim_tiempo`, `dim_origen` | Contexto de comparación, procedencia y tiempo UTC |
| `repeticiones` | Valores individuales por ID y ordinal, sin multiplicar la tabla de observaciones |
| `linaje` | ID externo de la fuente cuando existe y estrategia de identidad heredada |
| `procedencia` | Todas las rutas que aportaron una observación |
| `v_geoda_mediciones` | Entrada legible para Geoda/BI con hardware, GPU de vista declarada, métrica y calidad |
| `v_resumen` | Mediana, mínimo, máximo y número de observaciones por contexto comparable |

Los valores desconocidos son NULL; no se inventan RAM, GPU ni repeticiones para
Blender Open Data. La GPU de vista no equivale necesariamente al dispositivo usado
para Cycles; su lista completa permanece en el JSON de configuración.

Las claves de dimensiones usan UUIDv5 con namespace fijo y atributos completos.
Son reproducibles al cambiar el orden de entrada, no son hashes recortados.
Los IDs históricos de medición y SHA-256 de integridad se conservan íntegros.
La etiqueta del equipo es de presentación, no una clave única.

**Límite de identidad:** la captura v1 genera IDs a partir del registro y de la
posición del resultado. Este cambio no promete deduplicación semántica cuando la
fuente cambia el orden interno o el contenido. Tampoco identifica computadoras
físicas. Corregirlo requiere versionar la captura, emitir un ID persistente de
corrida y una clave de resultado, y mantener equivalencias con el histórico.
No se fusionan observaciones parecidas porque podrían ser ejecuciones distintas.

## Reglas de calidad

- Catálogo explícito de métricas de la sonda y `samples_per_minute`; una métrica
  nueva requiere actualizar el catálogo y sus pruebas. Segundos, FPS y muestras/min
  no son intercambiables. Todas son no aditivas: no se suman para puntuar un equipo.
- En sondas se recalculan mediana y variación desde las repeticiones; se rechazan
  contradicciones, valores no finitos, RAM inválida y motivos mal formados.
- El estado aceptado exige al menos tres repeticiones, variación hasta 10 % y
  ausencia de motivos. Los benchmarks públicos siguen en revisión.
- Un ID repetido con contenido distinto interrumpe la construcción. La versión
  vigente no se reemplaza si falla la construcción o la verificación de archivos.
- Se reabre DuckDB y se compara cada tabla exportada con su Parquet, en ambos sentidos.

La dirección `menor`/`mayor` solo describe la métrica dentro del mismo contexto;
no establece causalidad ni convierte el cubo en un recomendador validado.

## Consultas

```sql
SELECT equipo_etiqueta, cpu, ram_gb, gpu_vista_modelo, version, escena,
       prueba, metrica, unidad, valor, estado, motivos_json
FROM v_geoda_mediciones
ORDER BY fecha, id;

-- Comparación conservadora: mantiene todas las dimensiones del resumen.
SELECT * FROM v_resumen WHERE estado = 'aceptado';

-- Distribución de las repeticiones de cada observación, sin sumar rendimiento.
SELECT id, count(*) AS n, median(valor) AS mediana,
       min(valor) AS minimo, max(valor) AS maximo
FROM repeticiones GROUP BY id;
```

Geoda debe filtrar calidad y contexto antes de comparar. Evitar contar filas tras
unir `repeticiones` o `procedencia`: son relaciones uno-a-muchos. El número de
observaciones se obtiene de `mediciones`. Power BI debe desactivar la suma
automática de `valor`; conectar al archivo requiere un conector compatible, no
se entrega un PBIX en este cambio.

## Compatibilidad, publicación y reversión

Los lectores Python de descarga y estado admiten v1 y v2 y exigen coincidencia de
contrato entre puntero y manifiesto. Las vistas históricas conservan sus nombres.
Las claves dimensionales cambian: no cruzar dimensiones v1 con hechos v2.
En v2 no se exportan `hechos_medicion.parquet` ni `hechos_render.parquet`;
los consumidores de esos archivos deben filtrar `plata/mediciones.parquet` por
`fuente`. Se añaden Parquet para `dim_metrica`, `repeticiones` y `linaje`.

1. Instalar `requirements-cubo.txt` y pytest. Ejecutar
   `python -m pytest pruebas/test_cubo.py pruebas/test_cubo_v2.py pruebas/test_telemetria.py pruebas/test_geoda_estado.py -q`.
2. Reconstruir en carpeta nueva con una copia de los JSONL normalizados:
   `python -m g7b_almacen.cubo --entrada captura --salida resultado-v2`.
   Comparar conteos, calidad y muestras con el manifiesto anterior. No reconstruir
   desde el cubo v1: ese archivo no conserva las repeticiones ni todo el linaje.
3. Revisar consumidores de Parquet antes de integrar. El workflow `Cubo G7B` se
   dispara al modificar `g7b_almacen` en main y publica usando el puntero vigente;
   fusionar este cambio puede iniciar esa reconstrucción automáticamente.
4. La publicación mantiene versiones inmutables y verifica hashes antes de mover
   `control/cubo_actual.json`. Guardar el puntero previo. Para revertir, restaurar
   ese JSON exacto a una versión verificada, con publicaciones concurrentes detenidas;
   no eliminar bronce/plata ni las versiones antiguas.

Las pruebas locales usan datos controlados y un lago simulado. No equivalen a una
validación del lago de producción, de Azure real o de todos los consumidores externos.

## Fundamento oficial

La investigación y sus límites están en
[documentación oficial aplicada](investigacion/2026-11-17_cubo_documentacion_oficial.md).
Decisiones basadas en:

- [Microsoft: esquema en estrella](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema): grano, hechos, dimensiones y medidas.
- [Apache Parquet](https://parquet.apache.org/docs/overview/): formato columnar portable.
- [DuckDB SQL](https://duckdb.org/docs/stable/sql/introduction): tablas y vistas consultables.
- [RFC 9562, UUIDv5](https://www.rfc-editor.org/rfc/rfc9562.html#section-5.5): identidad determinista basada en nombres; no mecanismo de integridad criptográfica.
- [MongoDB: versionado de esquema](https://www.mongodb.com/docs/manual/data-modeling/design-patterns/data-versioning/schema-versioning/): contratos explícitos y coexistencia de versiones. Aquí se aplica como criterio de evolución, no como obligación de almacenar el cubo en MongoDB.

Próximas mejoras separadas: identidad de corrida en captura; normalizar inventario
GPU multivaluado sin duplicar observaciones; contratos de entorno y configuración
completa de pruebas; evaluación de representatividad y validación de recomendaciones.
