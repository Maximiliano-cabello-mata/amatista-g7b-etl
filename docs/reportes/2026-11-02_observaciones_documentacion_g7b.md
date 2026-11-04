# G7B — Resultados y observaciones de la documentación recopilada

**Fecha del lote y de la revisión:** 2 de noviembre de 2026 (México).  
**Objeto:** documentar qué obtuvimos, qué se examinó y qué se puede concluir del lote aceptado.  
**Estado:** ingesta documental demostrada; calidad del contenido evaluada parcialmente; telemetría y producción continua no validadas por esta revisión.

## 1. Qué logramos y qué recibimos

La prueba de integración registrada en la bitácora del proyecto recuperó un trabajo terminado de Zyte y completó el recorrido:

Zyte → Azure Bronce → embudo de calidad → Azure Plata → MongoDB.

Los logs revisados durante la integración reportaron 2,353 registros importados: 987 aceptados, 52 en revisión y 1,314 rechazados. La publicación reportó 987 documentos nuevos en MongoDB, cero actualizados y un archivo procesado. Esa cifra no equivale a un conteo actual comprobado directamente en la base.

Para esta auditoría se recibió el archivo **883618-1-13.jsonl.gz**, con los **987 registros aceptados**. No se recibió el conjunto completo de bronce ni los archivos de revisión y rechazo. Por tanto, las observaciones de calidad de este informe se refieren al lote aceptado.

El contenido recibido es documentación técnica en inglés atribuida al manual de Blender. Contiene descripciones de herramientas, parámetros, advertencias e instrucciones. No contiene resultados de una campaña de medición de computadoras y no debe presentarse como telemetría.

## 2. Qué se examinó

- Estructura y campos de los 987 registros.
- Presencia de fuente, URL, versión, licencia declarada y origen.
- Duplicados exactos de URL y texto.
- Distribución por versión y tema.
- Lectura cualitativa de 28 documentos: 20 seleccionados de forma reproducible y 8 elegidos para examinar casos concretos.
- Posibles causas de los problemas, contrastadas con el extractor y la clasificación del repositorio.

La revisión de campos cubre todo el lote; la lectura de contenido es una muestra. No se asignó una calificación universal ni un porcentaje de exactitud a los 987 documentos.

## 3. Qué obtuvimos de utilidad

El lote permite preparar respuestas documentadas sobre operaciones concretas de Blender. Por ejemplo:

| Contenido observado | Utilidad para G7B | Límite |
|---|---|---|
| GPU Rendering | Explicar la configuración de render GPU y sus restricciones declaradas | Los requisitos deben contrastarse para la versión y hardware del usuario |
| Simplify | Identificar ajustes que afectan geometría, texturas y memoria | No determina cuánto mejorará una computadora concreta |
| Decimate | Explicar modos de reducción de geometría y sus parámetros | No demuestra una reducción de tiempo o mejora visual medida |
| Grid y otros nodos | Consultar entradas, salidas y límites de funcionamiento | Algunos ejemplos necesitan imágenes o enlaces que no se conservaron |
| Fill y herramientas de modelado | Recuperar instrucciones, menús y atajos concretos | Deben consultarse dentro de su versión |

Esto justifica conservar el material. El valor para G7B está en organizarlo, recuperarlo por versión y responder con evidencia; la cantidad de documentos por sí sola no demuestra ese valor.

## 4. Qué observamos que debe corregirse

**Integridad de la extracción.** Hay páginas aceptadas que conservan encabezados pero pierden información principal. El caso más claro es Industry Compatible Keymap: faltan los datos de los atajos. Common Shortcuts presenta un problema semejante. El extractor no contempla filas y celdas de tablas en su selección principal.

**Contexto de consulta.** Se conservan referencias textuales a otras páginas e imágenes, pero no sus destinos o recursos. Esto limita las explicaciones que dependen de diagramas de nodos y ejemplos visuales.

**Repetición interna.** Algunas descripciones incluyen opciones hijas y después vuelven a presentarlas por separado. No se detectaron textos completos duplicados, pero sí repetición dentro de documentos leídos.

**Clasificación.** Las etiquetas de preguntas se asignan por palabras clave. Encontramos asociaciones débiles, como una página de frecuencias de audio clasificada en rendimiento del equipo. Una etiqueta indica una coincidencia del clasificador, no una respuesta comprobada.

**Interpretación del puntaje.** 656 documentos tienen valor cero y fueron aceptados porque el catálogo permite ese umbral para el manual. Algunos son útiles. No corresponde eliminarlos automáticamente: hay que separar autoridad de la fuente, integridad de extracción, relevancia y utilidad.

**Metadatos y limpieza.** Se conservan versión y origen, pero faltan datos útiles para reconstruir el contexto, como el instante individual de extracción y enlaces estructurados. Los títulos de los 262 registros de 3.6 conservan un icono residual de enlace.

## 5. Qué podemos afirmar y qué no

| Afirmación | Resultado de la revisión |
|---|---|
| El archivo contiene 987 registros aceptados y legibles como JSON | Comprobado |
| Hay información técnica aprovechable para consultas de Blender | Observado en los documentos leídos |
| Todos los documentos aceptados están completos | No; se observaron omisiones |
| Todos los documentos son fieles a la página original | No certificado; el contraste web intentado no estuvo disponible |
| No existen duplicados de ningún tipo | Solo se descartaron duplicados exactos de texto y URL |
| Los rechazados eran inútiles | No evaluado; no se recibieron |
| El lote permite recomendar un perfil de hardware con mejora medida | No; faltan mediciones |
| El servicio de búsqueda/API/MCP ya responde correctamente usando este lote | No probado en esta auditoría |

## 6. Trabajo derivado y criterios de aceptación

Estas son propuestas de trabajo; este informe no implementa cambios.

| Prioridad | Acción | Cómo comprobar que quedó resuelta |
|---|---|---|
| Alta | Conservar tablas y relaciones entre teclas y acciones | Los casos Keymap y Common Shortcuts recuperan sus datos y permiten contestar preguntas sobre atajos |
| Alta | Conservar enlaces y referencias visuales | Cada referencia relevante tiene destino, descripción y relación con su sección |
| Alta | Evitar duplicación de descripciones anidadas | Las opciones padre/hija aparecen una vez, manteniendo su relación |
| Alta | Separar calidad de extracción y relevancia temática | Una página vacía de contenido sustantivo no se acepta solo por título o autoridad |
| Media | Preservar fecha, versión, jerarquía y propiedades | Los campos se mantienen desde la extracción hasta la publicación |
| Media | Etiquetar contenido obsoleto y limpiar iconos | Las consultas distinguen versiones y advertencias; títulos sin residuos |
| Media | Evaluar respuestas con preguntas reales | Registrar 20 preguntas versionadas, respuesta esperada, documento de apoyo y resultado |
| Media | Auditar revisión y rechazados | Leer muestras antes de cambiar umbrales; registrar falsos rechazos y aceptaciones |

Si las tablas o los enlaces ya se perdieron en bronce, reprocesar plata no puede recuperarlos. Se debe comprobar primero qué conserva el original y, cuando sea necesario, reextraer únicamente las páginas afectadas. No hace falta ampliar las fuentes para resolver estos defectos.

## 7. Conclusión documental

G7B obtuvo una base documental con utilidad concreta para explicar herramientas y ajustes de Blender. La revisión no respalda descartarla como material inútil, pero tampoco respalda tratar todos sus registros aceptados como contenido completo y validado.

El siguiente avance de esta división consiste en mejorar la fidelidad de extracción y demostrar respuestas correctas con fuentes y versiones. La telemetría permanece como una línea distinta que necesita sus propios datos y validaciones.

## Anexo técnico: evidencia, métricas y muestra

El anexo conserva los detalles de la auditoría para que las observaciones puedan revisarse por registro. Las líneas citadas corresponden al JSONL recibido, empezando en uno.


Archivo recibido: 883618-1-13.jsonl.gz. Revisión: 2 de noviembre de 2026, México.

### Dictamen

El lote contiene información técnica aprovechable, especialmente para preguntas sobre uso de Blender. No es una colección vacía ni indiscriminada. Sin embargo, «aceptado» no equivale a extracción completa, respuesta validada ni medición de rendimiento. Debe conservarse el lote y corregir la extracción antes de ampliar volumen o tratarlo como conocimiento listo para recomendaciones automáticas.

### Método y límites

Se analizaron automáticamente los 987 registros y se leyó una muestra reproducible de 20 registros sin reemplazo, más 8 registros dirigidos (índices 0, 115, 118, 153, 163, 485, 540 y 986). Los índices de la muestra son base cero; la tabla usa líneas base uno. Selección: Fisher–Yates con LCG de 32 bits, semilla 20261102, multiplicador 1664525 e incremento 1013904223. La muestra se usa para diagnóstico cualitativo; no se calcula un porcentaje poblacional de documentos correctos.

El archivo tiene extensión .gz pero sus bytes son JSONL sin compresión (comienza con un objeto JSON). Se leyó como texto UTF-8 sin modificar el original. Puede haber sido descomprimido durante la descarga; no se determinó la causa.

SHA-256 del contenido recibido: f00c19745d1e3f5c7e42058b085c11aca51be87daece06e6b3f34ce051fecdaf.

Solo se recibió el lote aceptado: no permite auditar los 52 documentos en revisión ni los 1,314 rechazados. Tampoco demuestra por sí solo que MongoDB conserve exactamente estos bytes. Se intentó contrastar dos URLs con el manual en línea, pero el acceso falló; no se certifica fidelidad página por página ni vigencia actual de los requisitos técnicos. Las URLs y versiones son las declaradas en el archivo.

### Comprobaciones del lote completo

| Control | Resultado |
|---|---:|
| Registros JSON válidos y marcados aceptados | 987 |
| URL, título, texto, licencia y origen presentes | 987 |
| URLs con host docs.blender.org | 987 |
| Versiones coincidentes entre metadatos y ruta URL | 987 |
| URLs repetidas exactas | 0 |
| Textos repetidos exactos | 0 |
| Versión 5.2 declarada | 499 |
| Versión 4.5 declarada | 226 |
| Versión 3.6 declarada | 262 |
| Puntuación valor = 0 | 656 (66.5 %) |
| Menos de 100 palabras según el embudo | 164 |
| Mediana de palabras según el embudo | 242 |
| Textos con bloques de código Markdown | 11 |
| Textos que contienen bpy. | 3 |
| Títulos con el icono residual de enlace | 262 |
| Textos que contienen URLs http/https explícitas | 0 |
| Registros con metadatos.fecha | 0 |

Ausencia de duplicados exactos no descarta similitud entre versiones ni repeticiones dentro de un documento. Presencia de licencia es trazabilidad declarada, no auditoría legal. La fecha puede inferirse de la ruta de origen, pero no sustituye un campo de extracción individual.

### Cobertura temática

Geometry Nodes: 395; mallas: 236; nodos de sombreado: 137; modificadores: 86; EEVEE: 48; Cycles: 40; preferencias: 32; solución de problemas: 8; mapas de teclas: 4; scripting: 1.

El 77.8 % pertenece a Geometry Nodes, mallas o nodos de sombreado. Es coherente con un manual para consulta y aprendizaje; no es una base completa de API Python, equivalencias con Maya/3ds Max ni benchmarks. La ausencia de 2.79 entre aceptados no demuestra que nunca se extrajera.

### Utilidad demostrable a partir del contenido

| Pregunta de prueba | Evidencia local | Evaluación |
|---|---|---|
| ¿Cómo habilitar render GPU? | Línea 154, GPU Rendering, 4.5 | Conserva ruta de preferencias y selección por escena. Los requisitos de hardware necesitan comprobación de vigencia. |
| ¿Qué ajustes de Simplify pueden reducir memoria? | Línea 164, Simplify, 4.5 | Conserva Texture Limit, Max Subdivision y Volume Resolution, con sus descripciones. |
| ¿Cómo reducir geometría con Decimate? | Línea 541, Decimate Modifier, 5.2 | Conserva modos, parámetros y advertencias sobre topología. |
| ¿Qué hace Grid y cuándo no produce malla? | Línea 346, Grid Node, 5.2 | Conserva entradas y el límite mínimo de vértices. |
| ¿Cómo rellenar un perímetro y qué ocurre con agujeros? | Línea 33, Fill, 4.5 | Conserva modo, menú, atajo y comportamiento. |
| ¿Qué teclas usa Industry Compatible? | Línea 1 | Insuficiente: conserva encabezados pero faltan los mapas de teclas. |
| ¿Cuántos FPS dará un perfil en una computadora concreta? | No hay observaciones de benchmark en este lote | No respondible con este archivo. |

Esto prueba que el contenido permite algunas respuestas fundamentadas; no es una evaluación de un buscador o modelo, que no se ejecutó.

### Hallazgos y causas

1. **Pérdida de tablas: prioridad alta.** Industry Compatible Keymap (línea 1) y Common Shortcuts (línea 116) conservan secciones sin los datos que deberían explicar. El selector _BLOQUES de manual_sphinx.py no extrae filas/celdas y excluye párrafos bajo table. Es una causa de extracción concreta, no falta de interés del tema. Un detector de tres o más transiciones entre encabezados consecutivos marca 10 páginas; son candidatas a revisar, no 10 fallos confirmados.
2. **Enlaces y recursos visuales ausentes.** Las referencias quedan como texto sin destino; no hay URLs dentro de texto. Los ejemplos de Mix y Gizmos mencionan esquemas que no están disponibles en el registro. Mantener el enlace raíz permite acudir a la página, pero no reconstruye una guía autosuficiente.
3. **Repetición dentro de documentos.** En Vertex Groups, Multiresolution, Viewport y otros, la descripción de una propiedad padre incorpora las hijas y estas vuelven a emitirse por separado. El extractor toma todo el texto descendiente de dd y luego procesa los dd anidados. Esto encarece búsqueda/contexto y puede sesgar puntajes.
4. **Etiquetas de relevancia demasiado amplias.** La primera página recibe P2 aunque trata un mapa de teclas, no elección de versión por hardware. Sample Sound Frequencies recibe P1 aunque su tema principal es análisis de audio. La taxonomía usa raíces como compatib y samples: el puntaje es coincidencia léxica, no verificación de que se responda la pregunta.
5. **Valor cero no equivale a basura.** 656 aceptados tienen valor cero. El catálogo permite valor_min=0 y valor_revision=0 para el manual. Fill y Grid muestran por qué documentación corta puede ser útil. La mejora es medir integridad y capacidad de responder, no eliminar automáticamente esos 656 registros.
6. **Metadatos incompletos para reutilización.** El transformador conserva versión y sección, pero no conserva extraido_en ni la estructura completa de propiedades de la araña: deja el número de propiedades. Conviene preservar fechas, enlaces, jerarquía y propiedades estructuradas.
7. **Contenido antiguo/deprecado necesita contexto.** Rotate Euler conserva la advertencia de obsolescencia. Debe indexarse con versión y estado de deprecación para evitar presentarlo como recomendación actual. Los 262 títulos de 3.6 conservan un icono residual que debe limpiarse.

### Muestra cualitativa reproducible

| Línea | Documento | Observación |
|---:|---|---|
| 615 | [Push/Pull](https://docs.blender.org/manual/en/5.2/modeling/meshes/editing/mesh/transform/push_pull.html) | Instrucciones operativas utilizables; el ejemplo visual no se conserva. |
| 931 | [Mix Color Node](https://docs.blender.org/manual/en/4.5/render/shader_nodes/color/mix.html) | Explica entradas y mezcla; los ejemplos de nodos dependen de imágenes ausentes. |
| 271 | [Rotate Euler Node](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/utilities/deprecated/rotate_euler.html) | Conserva aviso de obsolescencia y alternativa; repite propiedades anidadas. |
| 346 | [Grid Node](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/mesh/primitives/grid.html) | Entradas, límites y salida UV concretos y utilizables. |
| 293 | [White Noise Texture Node](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/texture/white_noise.html) | Semilla, dimensiones y limitaciones útiles; repetición interna. |
| 606 | [Extrude](https://docs.blender.org/manual/en/5.2/modeling/meshes/editing/mesh/extrude.html) | Menú y Extrude Repeat útiles; referencias a otras extrusiones sin enlaces. |
| 174 | [Combine Bundle Node](https://docs.blender.org/manual/en/5.2/render/shader_nodes/utilities/bundle/combine_bundle.html) | Entradas y configuración útiles; frase introductoria aparentemente incompleta y repetición. |
| 977 | [Import STL Node](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/input/import/stl.html) | Descripción, alcance y entrada/salida suficientes para consulta básica. |
| 761 | [Sample Nearest Surface Node](https://docs.blender.org/manual/en/3.6/modeling/geometry_nodes/mesh/sample/sample_nearest_surface.html) | Conserva limitaciones importantes; ruido de iconos en encabezados. |
| 17 | [Toolbar](https://docs.blender.org/manual/en/4.5/modeling/meshes/uv/tools/toolbar.html) | Catálogo de herramientas útil; repetición de grupos y subopciones. |
| 951 | [Instance Bounds Node](https://docs.blender.org/manual/en/4.5/modeling/geometry_nodes/instances/instance_bounds.html) | Explica límites de instancias anidadas y salidas; útil. |
| 536 | [Multiresolution Modifier](https://docs.blender.org/manual/en/5.2/modeling/modifiers/generate/multiresolution.html) | Opciones y procedimiento de baking detallados; duplicación de subpropiedades. |
| 701 | [Light Node](https://docs.blender.org/manual/en/3.6/render/shader_nodes/output/light.html) | Ficha corta pero concreta; no se debe rechazar solo por brevedad. |
| 33 | [Fill](https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/face/fill.html) | Acción, menú, atajo y limitación concretos; útil pese a su brevedad. |
| 487 | [Gizmos](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/gizmos.html) | Explicación útil; ejemplos de construcción requieren imágenes no conservadas. |
| 445 | [Set Material Index Node](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/geometry/material/set_material_index.html) | Ficha corta con selección, índice y salida concretos. |
| 276 | [Sample Sound Frequencies Node](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/utilities/sound/sample_sound_frequencies.html) | Contenido útil para audio, pero etiqueta P1 de rendimiento de equipo poco justificada; duplicación. |
| 24 | [Vertex Groups Panel](https://docs.blender.org/manual/en/4.5/modeling/meshes/properties/vertex_groups/vertex_groups.html) | Operaciones útiles; duplicación extensa y marcador TODO sin resolver. |
| 901 | [Viewport](https://docs.blender.org/manual/en/3.6/editors/preferences/viewport.html) | Ajustes relacionados con memoria/calidad; duplicación y ruido de iconos. |
| 68 | [Shading](https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/mesh/shading.html) | Instrucciones utilizables; la etiqueta P5 no demuestra una técnica industrial documentada. |

### Orden recomendado de corrección

1. Conservar este lote y el bronce original. No borrar los documentos por su puntaje.
2. Corregir tablas, enlaces, recursos visuales y descripciones anidadas. Añadir pruebas con estos fallos reales.
3. Conservar metadatos de extracción y versión; añadir control de secciones vacías y marcador de deprecación.
4. Reprocesar primero una muestra del bronce disponible. Si bronce tampoco conserva tablas/enlaces, hace falta recuperar HTML o reextraer únicamente páginas afectadas: cambiar solo el embudo no recupera contenido perdido.
5. Evaluar 20 preguntas versionadas con respuesta esperada y documento de respaldo antes de ampliar la ingesta. Separar clasificación temática de calidad de extracción.
6. Auditar también revisión y rechazados antes de cambiar los umbrales de aceptación.

### Código consultado

- [Extractor Sphinx](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/motor_extraccion/spiders/manual_sphinx.py)
- [Transformación bronce a plata](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/g7b_ingesta/procesar.py)
- [Taxonomía](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/fuentes/taxonomia.yml)
- [Catálogo y umbrales](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/blob/main/fuentes/catalogo.yml)

Durante la auditoría no se modificaron el archivo original ni los datos en Azure/MongoDB. La publicación de este informe incorpora únicamente documentación al repositorio.
