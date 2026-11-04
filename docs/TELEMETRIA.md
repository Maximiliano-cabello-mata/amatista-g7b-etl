# Captura de telemetría G7B — 2026-11-03

Implementa la prioridad de mediciones del PLAN. Por instrucción del propietario,
el orden de esta entrega es captura y validación → cubo → Geoda. No implementa
todavía Parquet, DuckDB, perfiles recomendados ni el kernel.

## Dos recorridos

- Documentación: Zyte → bronce → embudo documental → plata → MongoDB. Se conserva.
- Mediciones: sonda / snapshot oficial → validación numérica →
  `bronce/telemetria/<fuente>/<hash>.jsonl.gz` →
  `plata/telemetria/<aceptado|revision>/<fuente>/<hash>.jsonl.gz`.

El embudo documental excluye ambos prefijos de mediciones (`bronce/sonda/` y
`bronce/telemetria/`). El cargador antiguo sigue disponible para archivos crudos;
la nueva ruta usa `python -m g7b_telemetria.capturar`.

## Fuente pública

[Blender Open Data](https://opendata.blender.org/download/) publica un
[snapshot diario](https://opendata.blender.org/snapshots/opendata-latest.zip),
con licencia CC0; el importador comprueba también LICENSE.txt dentro del ZIP.
Se verificó el formato contra el código oficial:
[dump_snapshot.py](https://projects.blender.org/infrastructure/blender-open-data/src/branch/main/website/opendata_main/management/commands/dump_snapshot.py)
y [normalizing.py](https://projects.blender.org/infrastructure/blender-open-data/src/branch/main/website/opendata_main/normalizing.py).

Solo se normaliza v4: muestras/minuto por escena, versión, dispositivo y backend.
No son FPS de la vista 3D ni una encuesta representativa de hardware. No responden
P3. Se conservan como revisión porque G7B no reprodujo esos benchmarks.
Los esquemas v1–v3 se cuentan como no soportados; no se inventa una conversión.

Esta primera captura toma los primeros 1,000 registros v4 válidos, con tope de
100,000 leídos. Es una muestra de integración, no un recolector exhaustivo ni
incremental: las siguientes ejecuciones pueden traer el mismo lote. La deduplicación
del mismo lote usa SHA-256; entre lotes distintos el futuro cubo deberá deduplicar
por el campo `id` estable. Límites: ZIP 256 MiB, contenido expandido 2 GiB,
línea 2 MiB. El ZIP se lee sin extraer rutas al disco.

## Sonda

Ejecutar en un proceso independiente de Blender, sin proyectos personales:

```sh
blender -b --factory-startup --python sonda/g7b_sonda.py -- --salida resultados --escena ligera --perfiles ligero --repeticiones 3 --sin-render
python -m g7b_telemetria.capturar sonda --entrada resultados --salida captura/sonda
python -m g7b_telemetria.capturar blender-open-data --salida captura/opendata --limite 1000
```

Agregar `--azure` usa AZURE_LAGO_URL o la conexión admitida por Lago, desde el
entorno; nunca introducir secretos en código, argumentos ni cuadernos compartidos.
Para un ZIP ya descargado, agregar `--entrada ruta/opendata.zip`.

La validación recalcula mediana y variación; rechaza valores no finitos, negativos,
cero, unidades inválidas y marcas sintéticas. Menos de tres repeticiones, falta de
calentamiento, corrida incompleta o variación superior al 10 % pasan a revisión.
Una prueba no disponible se omite, nunca se transforma en cero. Una escena de
benchmark generada es una carga artificial, pero los tiempos observados son reales.
El campo `sintetico=false` describe la medición, no una escena de trabajo humana.

## Evidencia local

Blender 5.2.3 LTS, escena ligera, perfil ligero, tres repeticiones:

| Prueba | Mediana | Variación | Resultado |
|---|---:|---:|---|
| Edición | 0.3425 s | 46.98 % | revisión |
| Modificadores | 0.0627 s | 12.60 % | revisión |
| Animación interna | 281.4825 fps | 26.43 % | revisión |

La variación se recalcula con los valores redondeados conservados por la sonda,
por eso puede diferir ligeramente del valor calculado antes del redondeo.
Vista 3D no disponible sin ventana. Render omitido. No certifica rendimiento
interactivo ni permite fijar perfiles todavía.

Snapshot consultado: 31,139 registros leídos, 30,139 de esquema no soportado,
1,000 benchmarks válidos, 3,000 mediciones en revisión. Lote:
`cb2ad750d439b0b982bd51308c45fda154ef34f8d8fb6fcda6ff82bcf3cbcf3f`.
La captura local no solicitó Azure. No constituye evidencia de subida cloud.

## Automatización

`Telemetría G7B` se ejecuta al integrar cambios de su código/workflow en main,
los martes a las 10:23 UTC y manualmente. Usa el entorno `amatista1`,
AZURE_LAGO_URL, un runner Ubuntu con Blender de su distribución y máximo
20 minutos. La sonda mide CPU; no presume GPU, cuatro arquitecturas ni equipos
personales. Los artefactos de informes/mediciones se retienen 14 días.

La publicación verifica por lectura y hash tanto bronce como plata. Credencial
ausente, datos vacíos o discrepancia fallan la ejecución. Las rutas son deterministas
y permiten reintentar una subida parcial. Los informes distinguen captura local de
`subida_y_lectura_verificadas`. No se habilitan máquinas de pago de Camber/Deepnote.

## Criterios pendientes antes del cubo

1. Comprobar recurrencia y continuidad de autenticación; primera ejecución cloud completa verificada abajo.
2. Reducir variación local; ampliar equipos y versiones con consentimiento.
3. Soportar snapshot completo/incremental y revisar anomalías de benchmarks públicos.
4. Crear tablas Parquet, hechos/dimensiones y deduplicación global; no combinar
   muestras/minuto, FPS internos y fluidez de vista como si fueran equivalentes.
5. Usar Deepnote para análisis reproducible y Camber para trabajos necesarios;
   activar una oferta no demuestra una integración. Geoda consumirá contratos
   y perfiles validados posteriormente.

## Activación verificada

El [PR #14](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/14)
se integró en main (`ec4335bd2a1602ccc636906ca036f198f8393499`) después de
dos ejecuciones de Pruebas correctas: 41707674079 y 41707694154.

La [corrida 41707925151](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41707925151)
terminó con éxito el 2026-11-03. Los logs confirman:

- Sonda del runner: una corrida, tres mediciones aceptadas por los controles
  de esta versión, `subida_y_lectura_verificadas`.
  Lote `776ae8990714ab31c8d60f9e876b3f1d0eec10c775521777e8190ce4ddc798c1`.
- Open Data: 1,000 benchmarks, 3,000 mediciones en revisión,
  `subida_y_lectura_verificadas`; mismo hash que la muestra local.
- Artefacto `telemetria-41707925151`, ID 13267960117, con informes y mediciones.
  Su retención termina el 2026-11-17; las copias del lago son independientes.

La sonda del runner tuvo medianas 0.173 s en edición, 0.0469 s en modificadores
y 271.1818 fps de animación interna. No son mediciones de la computadora del
propietario ni certifican fluidez de ventana. La sonda local anterior continúa
en revisión y no fue subida por esta corrida. Aceptación de esquema y estabilidad
no equivale a recomendación validada. Primera ejecución correcta no demuestra
todavía semanas de operación continua.
