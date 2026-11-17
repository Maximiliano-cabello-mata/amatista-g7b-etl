# Auditoría del flujo y de los datos (17 de noviembre de 2026, 08:30 UTC)

Revisión de solo lectura del historial de GitHub Actions desde el 10 de noviembre, del inventario completo del lago en Azure (contenedor `lago`) y de los archivos de control. El cubo se construyó **en local** con todas las mediciones de plata, sin publicar nada, para ver qué dirá cuando se reconstruya. No se cambió nada en el lago ni en MongoDB.

## 1. Resumen

| Pregunta | Respuesta |
|---|---|
| ¿El flujo corre solo? | **Sí, desde el 17 de noviembre.** El relevo lanzó el ciclo a las 06:11 y ya espera la vuelta de las 12:11. Las 5 vueltas del ciclo de estos días terminaron en verde |
| ¿Cuánta información hay? | **85,5 MB en 221 archivos.** En bronce hay **35.201 registros crudos**; en plata, **1.029 documentos aceptados** y **63.019 mediciones**; en MongoDB, 1.029 documentos (3,26 MB) |
| ¿Cuántas mediciones? | **63.019**: 62.998 de Blender Open Data y 21 de la sonda. El cubo publicado todavía tiene solo **3.018**, porque no se ha reconstruido desde la primera tanda real |
| ¿La telemetría es útil ahora? | **Mucho más que ayer.** Hay 59.998 mediciones recientes (del 15 de junio al 16 de noviembre de 2026), casi todas de Blender 5.x. Pero la clasificación por nivel tiene **dos sesgos que hay que corregir antes de usarla** (sección 5) |
| ¿Las arañas trabajan bien? | La de documentación, sí: desde el 17 de noviembre no repite recorridos. Su problema está en el embudo, que rechaza lo que vuelve a extraer (tarea D1). El radar de telemetría trajo su primera tanda sin errores |

## 2. El flujo de trabajo (GitHub Actions, desde el 10 de noviembre)

**92 ejecuciones** en total:

| Flujo | Correctas | Fallidas | Comentario |
|---|---|---|---|
| Ciclo G7B (24/7) | 5 | 0 | 2 por horario (una con 1 h 38 min de retraso), 2 lanzadas a mano y 1 por el relevo |
| Relevo del ciclo | 1 (más 1 esperando) | 0 | 1 cancelado, que es lo normal: el relevo nuevo reemplaza al que esperaba |
| Vigilar fuentes | 7 | 2 | Las dos fallas son del 11 de noviembre, con la firma de Azure vencida |
| Zyte al lago | 6 | 0 | — |
| Procesar bronce | 6 | 0 | — |
| Telemetría G7B | 7 | 1 | La falla fue una prueba en la rama, corregida (faltaba crear la carpeta de salida) |
| Cubo G7B, kernel y Publicar estado para Geoda | 17 | 0 | — |
| Desplegar a Zyte | 1 | 1 | La falla la causó el PR #21, corregido por el PR #23 |
| Pruebas | 29 | 2 | Las dos fallas son del PR #21 |
| Geodar (probar) | 2 | 1 | — |

**Riesgo vigente:** el horario de GitHub sigue sin ser confiable; el 16 de noviembre se saltó 3 de 4 vueltas. Hoy la continuidad depende del relevo. Si el relevo se corta, su horario de respaldo cada 3 horas lo retoma, y si pasan 8 horas sin una vuelta buena se abre el aviso `g7b-alerta`.

## 3. Cuánta información hay

### Lago por capa

| Capa | Archivos | Tamaño | Contenido |
|---|---|---|---|
| Bronce | 54 | 14,8 MB | 35.201 registros crudos (detalle abajo) |
| Plata, documentos | 40 | 1,3 MB | 1.029 aceptados, 67 en revisión (33 URL distintas) y 8.563 rechazados (2.448 URL distintas) |
| Plata, telemetría | 13 | 6,1 MB | 63.019 mediciones distintas |
| Plata, cubo | 7 | 1,5 MB | Parquet del cubo |
| Oro, cubos | 91 | **61,4 MB** | **7 versiones del cubo** guardadas, del 3 al 17 de noviembre |
| Oro, señales | 1 | 0,02 MB | Resumen semanal de los foros |
| Control | 16 | 0,3 MB | Estado de sensores, radar, embudo y publicaciones |

**Observación:** el 72 % del lago son versiones viejas del cubo. Con mediciones que crecen 20.000 por semana, cada versión pesará más. Hace falta una política para conservar, por ejemplo, las últimas 3 versiones (tarea T13).

### Bronce por fuente

| Fuente | Registros | Qué es |
|---|---|---|
| Blender Open Data | 21.000 | 1.000 de la captura vieja (marzo de 2022) y 20.000 de la primera tanda nueva |
| Manual de Blender (Zyte) | 9.561 | 16 trabajos (sección 4) |
| Extensiones de Blender | 1.632 | Catálogo |
| Poly Haven: HDRI, texturas y modelos | 997, 869 y 521 | Catálogo CC0 |
| Blender Artists, Godot, Three.js y DevTalk | 173, 58, 57 y 41 | Temas de foro, usados como señales |
| ambientCG | 100 | Catálogo CC0 |
| Herramientas libres (GitHub) | 81 | Versiones publicadas |
| arXiv, Krita, Stack Exchange, FreeCAD, blog de desarrollo, noticias de Blender | 30, 20, 16, 12, 11 y 9 | Documentos |
| Sonda y caniuse | 7 y 6 | Telemetría |

### MongoDB (de la última publicación)

`conocimiento_3d.documentos` tiene 1.029 documentos y `foros_crudos`, 56, con 3,26 MB de 512 MB. Los catálogos están en `g7b_catalogo` (7 archivos de bronce catalogados).

## 4. Las arañas

### Araña de documentación (Zyte, `blender_docs`)

| Trabajo | Fecha | Páginas | Qué fue |
|---|---|---|---|
| `1/1` a `1/12` | 1 de noviembre | 160 en total | Pruebas pequeñas; 7 trabajos vinieron vacíos |
| `1/13` | 3 de noviembre | 2.353 | Primer recorrido completo (araña anterior) |
| `1/14` y `1/15` | 16 de noviembre | 2.353 cada uno | **Recorridos repetidos**: la portada cambiaba a diario y el sensor relanzaba todo |
| `1/16` | 17 de noviembre | 2.370 | **Primero con `objects.inv`**: 930 de 5.2, 775 de 4.5 y 665 de 3.6, sin URL repetidas y con 86 alias |

- **Desde el `1/16` no se ha vuelto a lanzar ningún recorrido.** El sensor `sphinx` guarda el inventario de cada versión (5.2: 2.358 páginas, 4.5: 2.072, 3.6: 1.995) y no relanza nada mientras el inventario no cambie o pasen 30 días.
- **El problema está en el embudo, no en la araña.** De las 2.370 páginas del `1/16` solo se aceptaron 8, porque 1.014 que ya estaban aceptadas se rechazaron como duplicadas de sí mismas (tarea D1).
- **Hallazgo nuevo:** en Open Data ya hay mediciones de **Blender 5.3** (2.433). El sensor del manual vigila 5.2, 4.5 y 3.6. Hay que revisar si ya existe el manual 5.3 y agregarlo (tarea D12).

### Radar de telemetría

| Fuente | Estado |
|---|---|
| Blender Open Data | **Primera tanda real el 17 de noviembre a las 07:56**: 20.000 registros y 59.998 mediciones, verificadas en Azure. El tramo cubierto va del 15 de junio al 16 de noviembre de 2026. Quedan unos 330.000 registros hacia atrás (`completo_hacia_atras: false`) |
| Reportes de error de Blender | Inactivo; en la prueba en vivo encontró pocos reportes (tareas T4 y T5) |
| caniuse | Al día (11 de noviembre, revisión semanal) |
| Sonda | 21 mediciones, todas en servidores de GitHub: no representan equipos reales |

### Sensores directos (`control/sensores.json`)

**19 de 19 sin errores.** Las fuentes diarias y de 6 horas se revisaron el 16 y el 17 de noviembre. Las semanales (Poly Haven, ambientCG, extensiones y caniuse) se revisaron el 11 y les toca el 18.

## 5. Qué dicen las 63.019 mediciones (cubo construido en local)

| Nivel | Qué mide | Clase de GPU | Mediciones |
|---|---|---|---|
| — | CPU | — | 27.580 |
| N3 | GPU | dedicada | 23.064 |
| N4 | GPU | dedicada | 5.145 |
| N2 | GPU | integrada | 3.552 |
| — | — | captura vieja, sin `hardware` | 3.000 |
| — | GPU | desconocida | 603 |
| N1 | GPU | dedicada | 54 |

Versiones medidas: **5.2 (38.964)**, 5.1 (14.457), 5.3 (2.433), 4.5 (1.854), 5.0 (657) y otras menores, más 3.000 de la 3.0 vieja.

**Lo bueno:** la tabla de hardware reconoce el **98,1 %** de las GPUs; solo el 1,9 % queda como desconocida.

**Lo que hay que corregir antes de usar los niveles** (tareas T14 a T16):

1. **Las GPU nuevas no tienen VRAM en la tabla.** Las RTX serie 50 (5090, 5080, 5070 Ti, 5070, 5060 Ti y sus versiones para laptop) y las Radeon RX 9070 suman **18.282 mediciones** que quedan en N3 con confianza baja. Una RTX 5090 de 32 GB debería ser N4.
2. **Apple Silicon infla el N2.** Casi todas las «integradas» son Apple M de gama alta: M5 Max (486), M4 (228), M5 Pro (216), M5 (207), M1 Max (165), M4 Max (147). Por eso la mediana de N2 en Cycles (605 muestras por minuto en *classroom*) casi iguala a la de N3 (630). **El N2 que nos importa, una laptop con Intel o AMD integrada, casi no aparece:** «AMD Radeon Graphics» suma 198 mediciones, e «Intel Graphics», otras 198, sin reconocer. Apple necesita su propia clase.
3. **Faltan reglas para varios modelos.** «Intel Graphics» (los Core Ultra recientes), «Radeon 8060S» y las GPU de servidor (Tesla V100, P100, P4) deben clasificarse. Las de servidor, además, se excluyen del análisis de estudiantes.

**Conclusión de esta sección:** por primera vez hay datos reales y recientes, pero **todavía no responden P1 para laptops modestas**. Hay muy pocas mediciones de Intel y AMD integradas, y el nivel N2 está contaminado por Apple. Esto confirma que la telemetría de equipos modestos tiene que venir de los estudiantes, con la sonda y el censo (tareas T8 y T9).

## 6. Otros hallazgos

- **Construir el cubo con 63.000 mediciones tardó varios minutos en local**, porque inserta las filas una por una. El límite es 1.000.000; antes de llegar ahí hay que cargar los Parquet o los JSONL directamente con DuckDB (tarea T17).
- **El cubo publicado tiene 3.018 mediciones.** Falta reconstruirlo con la tanda nueva (tarea T1).
- **El aviso `g7b-alerta` no se ha abierto**, porque no hubo fallas en las vueltas.

## 7. Tareas que salen de esta auditoría

Se agregaron a [TAREAS_ARANAS.md](../TAREAS_ARANAS.md): T13 (conservar solo algunas versiones del cubo), T14 (VRAM de la RTX 50 y la RX 9000), T15 (Apple Silicon como clase propia), T16 (Intel Graphics, Radeon 8060S y GPU de servidor), T17 (carga del cubo con DuckDB) y D12 (manual 5.3).
