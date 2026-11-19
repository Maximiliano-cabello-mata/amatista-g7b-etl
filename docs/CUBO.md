# Cubo G7B: Parquet + DuckDB en Azure (contrato `g7b.cubo/3`)

## Qué se integra

Esta entrega continúa el diseño de hechos/dimensiones del [PR #4](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/4)
y la verificación de escritura/lectura del [experimento del PR #7](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/7).
Esas propuestas no estaban integradas en main. La implementación actual adapta el
modelo al contrato `g7b.telemetria/1` que ya produce la captura real. No fusiona sus
workflows, estimaciones de perfiles ni otras modificaciones pendientes.

El análisis documental de Deepnote del PR #13 es distinto: sus conteos de texto no
se convierten en rendimiento. La documentación sigue en su recorrido actual.

## 1. Dos clases de dato que nunca se mezclan (`g7b.cubo/2`, 17 de noviembre de 2026)

| Clase | Qué es | Para qué sirve | Dónde vive |
|---|---|---|---|
| **Directa** | Medida por G7B o Amatista en el **equipo real de un estudiante** (`equipo_estudiante`) o de un **laboratorio escolar** (`laboratorio_escolar`), **con consentimiento registrado** | Es la única que alimenta a Geoda: perfiles, costos y recomendaciones | `hechos_directos`, `v_directas`, `v_mediciones_aceptadas` |
| **Relativa** | Todo lo demás: benchmarks públicos (Blender Open Data), la sonda en servidores de GitHub (`ci`) o en la nube, y cualquier medición sin entorno o sin consentimiento declarado | Comparar niveles entre sí (cuánto más rinde un N3 que un N2 en la misma escena y versión). **Nunca** para fijar ajustes | `hechos_relativos`, `v_relativas`, `v_relativas_por_nivel` |

**Reglas:**
- **La clase la decide una sola función,** `clase_de` en `g7b_almacen/cubo.py`. Cada medición guarda el motivo en `motivo_clase`.
- **La duda nunca sube de clase.** Lo que no declara entorno y consentimiento es relativo. Para que una medición sea directa, la sonda tiene que correr con `--entorno equipo_estudiante --consentimiento` o `--entorno laboratorio_escolar --consentimiento`.
- **Ninguna tabla ni vista mezcla las dos clases,** salvo `v_calidad`, que solo cuenta filas.
- **«Sintético» no es «relativo».** En el contrato, `sintetico: true` significa datos inventados para pruebas, que **nunca** entran al cubo. Una medición relativa es real, pero poco fiable para decidir por un estudiante.
- **El estado de calidad sigue aparte.** `aceptado` o `revision` dice si la medición está bien tomada; la clase dice si representa a un estudiante. Geoda pide las dos cosas: directa **y** aceptada.

**Cubo al 17 de noviembre** (construido en local con todo el lago): **63.019 mediciones, todas relativas.** Son 62.998 de Open Data y 21 de la sonda en servidores; **directas, 0**. Las directas llegarán con la sonda en equipos de estudiantes y con Amatista ([TAREAS_ARANAS.md](TAREAS_ARANAS.md), T8 y T9).

## 1 bis. Velocidad y rendimiento (`g7b.cubo/3`, 17 de noviembre de 2026)

La clase de dato dice **quién** midió y si representa a un estudiante. La **naturaleza** dice **qué** se midió. Son dos ejes independientes:

| Naturaleza | Qué mide | Métricas | De dónde llega hoy |
|---|---|---|---|
| **Velocidad** | Cuánto tarda o cuánto produce un trabajo por lotes | `samples_per_minute` y `tiempo_render_cycles_cpu`, `tiempo_render_cycles_gpu`, `tiempo_render_eevee`, `tiempo_render_workbench` | Blender Open Data (API de benchmarks) y las pruebas de render de la sonda |
| **Rendimiento** | Cómo se siente trabajar: la fluidez y la respuesta mientras el estudiante usa Blender | `cuadros_por_segundo_vista3d`, `cuadros_por_segundo_animacion`, `tiempo_edicion`, `tiempo_primera_evaluacion` | La sonda: en equipos de estudiantes y laboratorios es la telemetría de rendimiento real |

**La naturaleza depende de la métrica, no de la fuente.** La sonda mide las dos cosas, porque también renderiza, y Open Data solo mide velocidad. El diccionario vive en `NATURALEZA` (`g7b_almacen/cubo.py`), y cada métrica queda con su naturaleza en `dim_prueba.naturaleza`. Una métrica nueva sin entrada queda `sin_clasificar` y sin índice: aparece en el manifiesto, pero no entra en ninguna comparación hasta que se clasifique.

**Normalización: el índice sin unidades.** Para comparar segundos, fps y muestras por minuto en una misma escala, cada medición lleva tres columnas:

- `valor_orientado`: más es mejor. Los tiempos se invierten (`1/s`).
- `indice`: el valor orientado entre la mediana geométrica de su grupo. **1.0** es lo típico del grupo y **2.0**, el doble de bueno.
- `n_grupo`: cuántas mediciones forman la referencia de ese grupo.

El grupo de comparación es la misma naturaleza, fuente, prueba, escena, métrica, serie de Blender y perfil.

**Reglas de la normalización:**
- **La referencia sale solo de mediciones fiables:** las aceptadas. En Open Data, que nunca se acepta una por una, sale de todas las de su grupo. Una medición en revisión recibe su índice, pero no mueve la referencia.
- **Las clases se normalizan por separado.** El índice de una directa se calcula solo con directas, y el de una relativa, solo con relativas. La separación directa/relativa no se rompe.
- **La escala logarítmica** (mediana de los logaritmos) es la que corresponde al rendimiento de las GPU, que es multiplicativo: «el doble de rápido» se mantiene parecido entre escenas.

**Velocidad y rendimiento juntos.** `v_equipos_directas` y `v_equipos_relativas` dan una fila por equipo, con su índice de velocidad y su índice de rendimiento lado a lado (media geométrica de sus índices). Los equipos que tienen las dos son la base para **calibrar** cuánto predice la velocidad (Open Data) el rendimiento real (la sonda). Esa calibración la hará Geoda cuando haya mediciones directas.

`v_naturaleza_por_nivel_directas` y `v_naturaleza_por_nivel_relativas` dan el índice por naturaleza, nivel y clase de GPU, con mediana, cuartiles y número de equipos.

**Cubo 3 con los datos reales** (construido en local):

| | Velocidad | Rendimiento |
|---|---|---|
| Directas | 0 | 0 |
| Relativas | 62.998 (Open Data) | 21 (sonda en CI) |

Índice de velocidad de Open Data por nivel (mediana entre equipos públicos):

| Nivel y clase de GPU | Índice |
|---|---|
| N2 integrada | 0,51 |
| N2 Apple | 3,52 |
| N3 dedicada | 3,18 |
| N4 dedicada | 8,07 |

Por ahora no hay ningún equipo con las dos naturalezas: la calibración espera a la sonda en laboratorios.

```sql
SELECT naturaleza, nivel, gpu_clase, equipos, indice_mediana
FROM v_naturaleza_por_nivel_relativas WHERE fuente = 'blender-open-data' ORDER BY naturaleza, nivel;
SELECT * FROM v_equipos_directas WHERE mediciones_velocidad > 0 AND mediciones_rendimiento > 0;
```

**El kernel:** el paquete de Geoda toma sus factores relativos solo de la **velocidad**, y `geoda/paquete.py` rechaza un factor de otra naturaleza. El rendimiento que fija los perfiles sale únicamente de las directas.

## 2. Almacenamiento y consulta

Azure guarda versiones de archivos; DuckDB ejecuta las consultas en Actions,
Deepnote o una computadora. No se comparte un archivo abierto para múltiples
escritores. Los datos portables están en Parquet y la copia DuckDB es reconstruible.

- Entrada: `plata/telemetria/{aceptado,revision}/<fuente>/*.jsonl.gz`.
- Plata portable: `plata/cubo/<version>/hechos_directos.parquet` y `hechos_relativos.parquet`.
- Oro: `oro/cubos/<version>/cubo.duckdb`, `parquet/*.parquet` (dimensiones y procedencia),
  `resumen_directas.csv`, `resumen_relativas.csv`, `resumen.json` y `manifiesto.json`.
- Puntero vigente: `control/cubo_actual.json`.

La versión publicada no se sobrescribe. Se verifica SHA-256 de todos los archivos
descargándolos de Azure, luego el manifiesto, y solo entonces se cambia el puntero.
Una falla previa conserva la versión vigente; puede dejar una versión parcial no
referenciada. El workflow serializa publicaciones. Falta una política de retención:
hoy hay 7 versiones, que suman el 72 % del lago (tarea T13).

## 3. Modelo normalizado

El grano es una **observación**: una métrica de una prueba o escena, en una corrida (de la sonda) o en un registro (de Open Data), con una configuración declarada. No es un equipo físico.

| Tabla | Contenido |
|---|---|
| `hechos_directos` | Observaciones directas, con id, `id_fuente`, las seis claves de dimensión, fecha, valor, estado, motivos, `motivo_clase`, variación, repeticiones, `sin_ventana` y `huella_origen` |
| `hechos_relativos` | Las mismas columnas, para las observaciones relativas |
| `dim_fuente` | Fuente, licencia, entorno declarado y **clase de dato** |
| `dim_equipo` | El equipo **en columnas tipadas** (estándar `g7b.hardware/1`): qué se mide, GPU, fabricante, clase de GPU, VRAM, CPU y familia, sistema, backend, nivel y su confianza. Conserva además el JSON original (`equipo_json`) |
| `dim_version` | Programa, versión completa y serie (`5.2`) |
| `dim_prueba` | El **diccionario de métricas**: fuente, prueba, escena, métrica, unidad, si es mejor «mayor» o «menor» y su **naturaleza** (velocidad o rendimiento). Las unidades sin entrada se rechazan |
| `dim_perfil` | Perfil de la sonda y su versión; `no_aplica` cuando falta |
| `dim_tiempo` | Día UTC, año, mes y día |
| `procedencia` | Archivos de entrada de cada observación |

**Identidad:**
- **Sonda:** su id ya no depende de la posición en la lista. Se forma con el registro, la prueba, la métrica y el perfil.
- **Open Data:** conserva su id para no duplicar lo ya capturado. Además, el cubo deduplica por **identidad semántica**: fuente, `id_fuente`, escena, prueba, métrica y perfil. Si la misma observación llega con otro id, se cuenta en `duplicados_semanticos`. Si llega con otro valor, la construcción falla.

**Carga:** las tablas se cargan en bloque, escribiendo JSONL que lee DuckDB. Las 63.019 mediciones del lago se construyen en unos 9 segundos; insertar fila por fila tardaba varios minutos.

## 4. Vistas

| Vista | Qué tiene | Quién la usa |
|---|---|---|
| `v_directas` y `v_relativas` | Los hechos unidos a todas sus dimensiones, con columnas legibles, la naturaleza, `valor_orientado` e `indice` | Análisis |
| `v_equipos_directas` y `v_equipos_relativas` | Velocidad y rendimiento juntos, por equipo | La calibración de Geoda |
| `v_naturaleza_por_nivel_directas` y `v_naturaleza_por_nivel_relativas` | El índice por naturaleza, nivel y clase de GPU | Comparaciones |
| `v_mediciones_aceptadas` | **Solo directas y aceptadas** | Geoda (perfiles, costos y ejecución) |
| `v_relativas_por_nivel` | Open Data por nivel, clase de GPU, backend, serie y escena, con mediana y cuartiles | Comparaciones entre niveles |
| `v_resumen_directas` y `v_resumen_relativas` | Agregados con mediana, cuartiles, mínimo y máximo, nunca mezclando unidades | Cuadernos y CSV |
| `v_calidad` | Conteos por clase, fuente y estado | Auditoría |

```sql
SELECT * FROM v_calidad ORDER BY clase_dato, fuente, estado;
SELECT nivel, gpu_clase, serie, escena, mediciones, mediana
FROM v_relativas_por_nivel WHERE nivel IS NOT NULL ORDER BY escena, nivel;
SELECT version, prueba, unidad, valor FROM v_mediciones_aceptadas;   -- solo directas
```

El constructor conserva los controles anteriores:
- elimina duplicados exactos por `id` y guarda todas sus rutas de procedencia;
- falla si un mismo id cambia de contenido;
- rechaza datos sintéticos, valores inválidos y contratos desconocidos;
- compara cada tabla de hechos en Parquet contra DuckDB y reabre el archivo cerrado.

**Esta validación técnica no certifica representatividad ni recomendaciones**: `recomendaciones_habilitadas` sigue en `false`.

## 5. Lectores y migración

- **Contrato:** `g7b.cubo/3`, que agrega la naturaleza y el índice, sin cambiar las tablas de hechos. Los lectores aceptan `g7b.cubo/2` y `g7b.cubo/1`. La descarga (`g7b_almacen/descargar.py`) y el estado de Geoda (`geoda_estado.py`) leen también `g7b.cubo/1` mientras siga vigente la versión publicada anterior.
- **Estado de Geoda:** con el cubo 2, `publicacion/geoda.json` publica además las directas, las directas aceptadas y las relativas.
- **Geoda (`ejecutar`):** exige `g7b.cubo/2` o `/3` y comprueba los conteos de las dos clases contra el manifiesto.
- **Manifiesto:** `mediciones`, `directas` y `relativas` (conteos por estado), `naturaleza` (conteos por clase y naturaleza), `calidad` (la suma, por compatibilidad), `duplicados_exactos` y `duplicados_semanticos`.
- **Cuadernos** (Deepnote y Camber): consultan `v_relativas` y `v_resumen_relativas`.

## Ejecutar

```sh
pip install -r requirements-cubo.txt
# Reconstrucción local; salida nueva/vacía, JSONL normalizados en entrada:
python -m g7b_almacen.cubo --entrada captura --salida resultado-cubo
# Leer el lago y publicar una versión (credenciales en el entorno):
python -m g7b_almacen.cubo --azure --salida resultado-azure
# Descargar la versión vigente; verifica hash y conteo:
python -m g7b_almacen.descargar cubo-local.duckdb
```

Configurar AZURE_LAGO_URL como secreto, nunca en código. Para consumo de Deepnote,
usar una credencial de solo lectura. Abrir siempre la copia con
`duckdb.connect('cubo-local.duckdb', read_only=True)` y cerrar antes de reemplazarla.
El [cuaderno](../analisis/cubo/Deepnote_G7B.ipynb) descarga una copia nueva y muestra
las consultas. Se entrega preparado; ejecutarlo dentro de Deepnote requiere la
integración de credenciales de ese workspace.

## Operación

`Cubo G7B` corre al integrar su código en main, manualmente, y cada semana en el ciclo después de `Telemetría G7B`. Usa `amatista1`, 20 minutos de
límite y guarda artefactos por 14 días. Después de publicar descarga nuevamente
el cubo mediante el puntero vigente, verifica su hash y lo abre en solo lectura.

Se reconstruye completo con un máximo de un millón de filas de entrada; no es
incremental. Con la carga en bloque, 63.019 mediciones tardan unos 9 segundos. Al
crecer hay que revisar memoria, retención (T13) y particionado.

## Historia: primera publicación verificada (cubo 1, 3 de noviembre de 2026)

El [PR #15](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/15)
se integró tras 62 pruebas aprobadas, incluida la publicación/descarga con Azurite.
La [ejecución 41712113585](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41712113585)
construyó y publicó el cubo usando los datos reales del lago, y completó una
descarga independiente mediante el puntero vigente:

- Versión: `20261103T202349Z-529801f82baa`.
- Archivo: `oro/cubos/20261103T202349Z-529801f82baa/cubo.duckdb`.
- SHA-256 del DuckDB descargado: `0340fa1346428b3846c60b3df670bf74d2adc5a8189416eaf9b3e1ac18cacc78`.
- 3,003 mediciones únicas: tres de sonda aceptadas y 3,000 de render en revisión.
- Cero duplicados en esta entrada; la deduplicación fue probada con duplicados
  deliberados en las pruebas automatizadas.
- Parquet comparado con DuckDB; todos los artefactos publicados verificados por
  lectura y hash; archivo vigente reabierto en solo lectura con 3,003 filas.

Esta evidencia corresponde al cubo cloud. La prueba local anterior también tiene
3,003 filas pero usa la sonda local variable: sus tres mediciones están en revisión.
Son conjuntos distintos y sus hashes no deben coincidir. El cuaderno de Deepnote
se entrega sin credenciales ni salidas; todavía no fue ejecutado en ese workspace.

## Documentación oficial y revisión del diseño

La [investigación del 17 de noviembre de 2026](investigacion/2026-11-17_cubo_documentacion_oficial.md)
reúne diez fuentes primarias de Microsoft, DuckDB, Apache Parquet, MongoDB e IETF.
Distingue el comportamiento actual de las propuestas sobre identidad estable,
redundancia y consumo analítico. Incluye prioridades y pruebas de aceptación para
una futura versión; no cambia el contrato ni acredita una migración implementada.
