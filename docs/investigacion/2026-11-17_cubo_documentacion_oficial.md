# Cubo Geoda: documentación oficial y propuesta de mejora

Fecha: 2026-11-17. Estado: investigación y propuesta, no implementación.
Código contrastado: [main en 2eb8f30](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/tree/2eb8f30b6cd3289d905d0a2792140873c62a7d8e).
Lectura operativa: [CUBO.md](../CUBO.md), [TELEMETRIA.md](../TELEMETRIA.md).
Este documento no sustituye el plan maestro ni modifica los contratos vigentes.

## Conclusión

Conviene mejorar primero la identidad de las observaciones y el contrato de llegada,
después simplificar las representaciones físicas y finalmente facilitar el consumo.
Los hashes largos no demuestran un mal modelo; el riesgo es confundir identidad,
contenido y etiqueta visible. Tampoco toda repetición significa doble contabilización.

No se propone migrar a un servidor relacional nuevo. Parquet puede seguir siendo la
publicación portable y DuckDB una copia reconstruible para consultar. DuckDB sí es
un motor relacional [R3]; mantenerlo no equivale a una arquitectura sin relaciones.
MongoDB y la ingesta documental tienen reglas propias: sus índices no protegen
automáticamente los JSONL del lago ni los Parquet.

## 1. Biblioteca de fuentes primarias

Los enlaces siguientes son manuales de los creadores y un estándar técnico.
Las explicaciones son síntesis originales; no se reproducen manuales completos.
Los enlaces son documentación viva, consultada para esta revisión.
No se presentan opiniones de foros como requisitos oficiales.

| Ref. | Documentación oficial | Qué aporta y dónde aplica |
|---|---|---|
| R1 | [Microsoft — Cubes in Multidimensional Models](https://learn.microsoft.com/en-us/analysis-services/multidimensional-models/cubes-in-multidimensional-models) | Un cubo es una estructura lógica de dimensiones y medidas. Tener un archivo llamado cubo no define por sí solo su semántica. |
| R2 | [Microsoft — Understand star schema](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) | Hechos, dimensiones, granularidad consistente y claves sustitutas. Las dimensiones pueden simplificarse; no hace falta fragmentar todo. Orientado a modelos de Power BI, no obligación de adoptar Fabric. |
| R3 | [DuckDB 2.0 — SQL Introduction](https://duckdb.org/docs/2.0/sql/introduction) | Define DuckDB como sistema relacional. Aclara qué motor ya utiliza el proyecto. |
| R4 | [Apache Parquet — Overview](https://parquet.apache.org/docs/overview/) | Formato columnar, compresión e interoperabilidad. No establece la identidad de las observaciones ni las reglas de negocio. |
| R5 | [MongoDB — Handle Duplicate Data](https://www.mongodb.com/docs/manual/data-modeling/handle-duplicate-data/) | La duplicación deliberada puede favorecer lecturas; hay que considerar frecuencia de actualización y consistencia. No justifica copias sin propósito. |
| R6 | [MongoDB — Schema Validation](https://www.mongodb.com/docs/manual/core/schema-validation/) | Reglas para tipos y valores de documentos. Esquema flexible no significa ausencia de validación. |
| R7 | [MongoDB — Schema Versioning](https://www.mongodb.com/docs/manual/data-modeling/design-patterns/data-versioning/schema-versioning/) | Versionar el esquema y adaptar lectores y actualizaciones. No confundir versión del contrato con versión de Blender. |
| R8 | [MongoDB — Unique Indexes and Schema Validation](https://www.mongodb.com/docs/manual/tutorial/unique-indexes-schema-validation/) | Unicidad y validación son controles complementarios. Un índice único entre documentos no resuelve todas las duplicidades internas de arrays. |
| R9 | [MongoDB — updateOne / upsert](https://www.mongodb.com/docs/manual/reference/method/db.collection.updateOne/) | Insertar o actualizar según un filtro; los campos del filtro deben estar indexados de forma única para evitar múltiples upserts. La operación debe además diseñarse para ser idempotente. |
| R10 | [IETF — RFC 9562, UUID](https://www.rfc-editor.org/rfc/rfc9562.html) | Estándar de identificadores de 128 bits, versiones y consideraciones de unicidad. Generar un UUID nuevo en cada relectura no deduplica una observación. |

Orden de lectura recomendado: R1 y R2 para el significado del cubo; R3 y R4 para
almacenamiento; R6–R9 para contratos e ingreso documental; R10 para alternativas
de identificación. R5 permite evaluar qué redundancia tiene una razón explícita.

## 2. Alcance y evidencia

Se revisaron:
- [g7b_almacen/cubo.py](../../g7b_almacen/cubo.py): validar, preparar, modelo, construir y publicar.
- [g7b_telemetria/capturar.py](../../g7b_telemetria/capturar.py): sonda, opendata y capturar.
- [geoda/contratos.py](../../geoda/contratos.py): Huella.id y contratos.
- El manifiesto del artefacto [ejecución 43793507202](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/43793507202), descargado previamente.

El manifiesto de ese corte, generado el 2026-11-16 a las 02:40 UTC, declara:
3,006 mediciones, 6 de sonda, 3,000 públicas, 5 aceptadas, 3,001 en revisión,
0 duplicados eliminados y recomendaciones deshabilitadas.
Son cifras de ese corte, no del lago actual ni de todo MongoDB.
Cero duplicados eliminados por ID no prueba ausencia de duplicidad semántica.

Esta revisión no ejecutó una auditoría completa del lago ni nuevas pruebas del ETL.
Los riesgos del código se distinguen de incidentes observados.

## 3. Hallazgos y diagnóstico

| Hallazgo comprobado | Consecuencia o riesgo | Propuesta |
|---|---|---|
| modelo crea mediciones y copia sus subconjuntos con CREATE TABLE AS a hechos_medicion y hechos_render. | Redundancia física real; no son eventos adicionales. | Elegir una representación canónica. Evaluar vistas para subconjuntos si los consumidores no requieren materialización. |
| v_exploracion y v_resumen son vistas; el Excel exportó varias representaciones. | Sumar filas de hojas distintas produciría conteos incorrectos. | Una vista de entrada claramente documentada para cada consumidor. |
| capturar calcula el ID con fuente, identidad e índice i de la lista. | Reordenar escenas o resultados puede reasignar un ID a otro significado y provocar conflictos. | Clave semántica estable, independiente de la posición. |
| Para sonda, identidad es la huella del documento completo. | Cambiar metadatos accesorios puede crear IDs nuevos aunque se trate de la misma observación. | Identidad de corrida persistente, separada del hash del contenido. |
| id_fuente de Open Data no se proyecta como columna del cubo. | La trazabilidad directa al proveedor exige volver a las etapas previas. | Conservar fuente e id_fuente, además de huella y ruta de procedencia. |
| dim_dispositivo usa atributos serializados e incluye fuente y contexto. | Representa una configuración declarada; no identifica necesariamente un equipo físico. Variaciones de atributos crean claves distintas. | Definir qué entidad se pretende agrupar y distinguir equipo, configuración y dispositivo declarado. |
| Huella.id usa 16 caracteres de SHA-256; el cubo usa 64. | Son funciones diferentes; no deben tratarse como claves intercambiables. | Documentar ámbito y versión de cada identidad y una correspondencia explícita si hace falta. |
| valor contiene métricas en segundos, fps y samples/min. | Un consumidor puede agregarlas incorrectamente. | Diccionario de métricas y medidas de consumo explícitas. El resumen actual ya agrupa por métrica y unidad. |

### Controles existentes que deben conservarse

- Validación de contrato, fuente, calidad, valores y fechas con zona horaria.
- Deduplicación exacta por ID y rechazo de contenido contradictorio bajo el mismo ID.
- Comprobación de que los joins no cambian la cantidad de mediciones.
- Comparación de contenido de Parquet y DuckDB y reapertura del archivo.
- Versiones publicadas y verificación por hash antes de cambiar el puntero vigente.
- Distinción entre benchmarks públicos en revisión y mediciones aceptadas.
- Ausencia de recomendaciones habilitadas por el mero hecho de tener datos.

No hay razón para eliminar esos controles al simplificar el modelo.

## 4. Propuesta de contrato e identidad

Esta sección es criterio de diseño para G7B, no texto normativo de un fabricante.

Primero declarar el grano: una observación de una métrica para una
corrida/prueba, escena y configuración concretas. La sonda publica una mediana
de repeticiones por resultado; un benchmark externo publica otro tipo de resultado.
No asumir que ambas filas representan una repetición individual.

| Concepto | Regla propuesta |
|---|---|
| fuente + id_fuente | Identidad original y su ámbito; conservarla cuando exista. |
| id_corrida | Identidad persistente de la ejecución; no generarla nuevamente al reimportar. |
| id_observacion | Identidad estable del resultado dentro de la ejecución, con campos semánticos suficientes para distinguir resultados reales. |
| hash_contenido | Detecta cambios; no sustituye la identidad lógica. |
| codigo_visible | Referencia legible para personas; unicidad dentro de un ámbito explícito si se usa para buscar. |
| version_contrato | Define tipos, obligatoriedad y significado de campos. |
| version_transformacion | Permite saber qué normalizador produjo la representación. |
| fecha_observacion / fecha_ingesta | Distinguir cuándo ocurrió de cuándo llegó. |
| lote / procedencia | Permite auditar y reprocesar sin perder el vínculo con el original. |

No usar solamente dispositivo y escena para deduplicar: dos corridas legítimas
pueden coincidir en ambos. No incluir estado de calidad ni etiquetas editables en
la identidad de la observación. Si dos resultados comparten la clave propuesta,
primero determinar si son repeticiones, versiones o conflictos; no descartarlos silenciosamente.

No truncar todos los hashes para hacerlos legibles. Mantener la huella completa
para integridad y ocultarla en la interfaz. Claves numéricas internas son una opción,
pero necesitarían un mapeo persistente si deben conservarse entre reconstrucciones.
Una posición de fila recalculada no es una identidad estable.

### Llegada de información

1. Conservar el original y su procedencia en bronce.
2. Validar y transformar según contrato explícito.
3. Resolver identidad y distinguir repetición exacta, revisión del contenido y conflicto.
4. Publicar la representación validada; registrar rechazos con motivo y trazabilidad.
5. Construir dimensiones, vistas y medidas desde esa representación.
6. Verificar la versión completa antes de hacerla vigente.

Definir aparte el comportamiento ante entradas inválidas: rechazo del lote o
cuarentena controlada, con conteos reconciliados y alertas. No convertir una
publicación parcial en éxito silencioso. MongoDB puede aplicar validadores e índices
donde almacena documentos [R6–R9]; el constructor de archivos debe comprobar sus
propias invariantes.

## 5. Prioridades recomendadas

### P0 — Identidad y contrato

- Sustituir la dependencia del índice de lista en la identidad.
- Conservar id_fuente e introducir identidad persistente de corrida donde proceda.
- Definir cómo se representa una corrección sin perder el historial.
- Precisar el grano por familia de mediciones.
- Versionar el cambio y diseñar la correspondencia entre IDs antiguos y nuevos.

### P1 — Modelo y consumo

- Evaluar una tabla canónica y vistas para subconjuntos, preservando los contratos de exportación.
- Exponer atributos útiles de hardware como campos tipados; conservar el JSON original.
- No agrupar equipos por nombres parecidos sin evidencia.
- Publicar un diccionario: métrica, unidad, significado, operación válida,
  dirección de mejora y condiciones mínimas de comparación.
- Ocultar claves técnicas en paneles y mostrar nombres descriptivos.
- Mantener documentación extraída y mediciones como conjuntos distintos, enlazados
  mediante evidencia explícita; un párrafo de manual no es una medición de rendimiento.
- Para medianas globales, partir de observaciones comparables; no calcular sin más
  la mediana de medianas ni sumar fps y tiempos.

### P2 — Operación y crecimiento

- Registrar conteos recibidos, válidos, repetidos, conflictivos y rechazados por lote.
- Medir tiempos, memoria y bytes antes de introducir particionado o cargas incrementales.
- Definir retención y limpieza de publicaciones parciales sin borrar la versión vigente.
- Ampliar cobertura y representatividad de muestras antes de habilitar recomendaciones.
- No incorporar otro motor o una plataforma de cubos solo por el nombre del problema.

## 6. Pruebas de aceptación para una futura implementación

| Caso | Resultado requerido |
|---|---|
| Reprocesar el mismo lote | Mismas identidades y cantidad de observaciones; procedencia conservada. |
| Reordenar resultados o escenas | Cada observación conserva su identidad. |
| Cambiar metadatos accesorios | No crea otra observación por accidente. |
| Dos corridas reales con valores iguales | Ambas se conservan. |
| Misma identidad con contenido distinto | Conflicto o revisión versionada explícita, nunca sobrescritura silenciosa. |
| Misma configuración declarada por fuentes distintas | Se mantiene la procedencia; no se afirma que sea el mismo equipo físico. |
| Unidad incompatible con métrica | Rechazo o cuarentena documentada. |
| Dimensión faltante o duplicada | No se pierden ni multiplican hechos en joins. |
| Reconstruir DuckDB desde publicación portable | Contenido equivalente según contrato y conteos reconciliados. |
| Migrar IDs v1 a una versión nueva | Mapeo auditable, consumidores verificados y posibilidad de volver a la publicación anterior. |

Estas pruebas se proponen; este cambio documental no afirma haberlas ejecutado.

## 7. Decisión recomendada

Mantener el almacenamiento actual mientras se corrige el contrato de identidad.
Preparar una versión nueva de forma paralela, comparar resultados con el corte
anterior y migrar consumidores de manera explícita. La mejora principal buscada es
que cada dato conserve su significado y procedencia al llegar, repetirse y corregirse;
la reducción de copias y la presentación de claves cortas vienen después.
