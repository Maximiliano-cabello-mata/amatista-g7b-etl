# Site 4.1 · selección de documentación técnica

La araña ocupa el nombre `paginas` en Zyte. `blender_docs` recorre su inventario Sphinx. Site tiene asignado el capítulo de composición del manual de Blender 4.5, fuera de las secciones de esa otra araña. Geodar revisa el índice de composición cada 168 horas y, si observa un cambio, envía un trabajo de hasta 64 intentos. Una modificación exclusiva de una página interior puede pasar inadvertida al sensor del índice.

## Eventos y gradiente

Cada semilla, respuesta HTML, redirección y error consume o alimenta una sola frontera. Cada petición, incluidas las redirecciones, reserva su intento antes de salir. En metadatos se omite el cuerpo. En texto completo se conservan el original en bronce, la cita por apartado y las decisiones por bloque.

Sea $D_l$ la fracción de palabras incluidas en enlaces. Un bloque con enlaces y $D_l\geq0.80$, o una lista de al menos tres enlaces con $D_l\geq0.55$, se marca como navegación antes de evaluar palabras técnicas. El índice sigue aportando destinos. El resto pasa por [las reglas de evidencia v3](README.md). Site reconoce también un parámetro de composición y una expresión de efecto con condición o versión explícita. Un foro aporta hipótesis. Las palabras coincidentes por sí solas pueden producir falsos positivos.

Para la página $t$, $y_t$ es la fracción de candidatos entre los bloques nuevos evaluables. El gradiente de la pérdida $(m-y_t)^2/2$ respecto de $m$ es $m-y_t$. Después de cada respuesta evaluable se aplica $m_t=m_{t-1}+0.25(y_t-m_{t-1})$ desde $m_0=0.5$. Referencias y navegación se excluyen del denominador.

## Prioridad de la frontera

Para cada página padre se agrupan los enlaces elegibles y se consideran por separado ruta, ancla y contexto local (encabezado y hasta 400 caracteres del bloque). Cada campo usa BM25 sobre ese grupo. Con $N$ enlaces, $n_t$ campos que contienen el término y $f_t$ apariciones, la contribución de un término es

$$\log(1+(N-n_t+0.5)/(n_t+0.5))\frac{2.2 f_t}{f_t+1.2(0.25+0.75 L/\bar L)}.$$

Se suman las contribuciones de los términos del catálogo y se normaliza cada suma $B$ con $b=B/(1+B)$. La nota $S=0.25 b_{ruta}+0.40 b_{ancla}+0.20 b_{contexto}+0.15 m_t$ determina la prioridad $S\,0.85^{d-1}\,0.5^k$, con profundidad nueva $d$ y saltos consecutivos fuera de prefijo $k$. Solo se admiten puentes hacia prefijos HTTPS autorizados explícitamente en el catálogo, con $S\geq0.28$ y hasta dos saltos. Al regresar al prefijo principal se reinicia $k$. El piloto opera enteramente dentro del capítulo. Robots, versiones, presupuesto y dominios de la fuente siguen rigiendo.

La frontera canoniza URLs, elimina fragmentos y reserva una única visita por URL. La deduplicación aproximada entre documentos continúa en el embudo de plata con SimHash. Los pesos y cortes iniciales son parámetros de diseño. El histórico conserva la versión anterior y permite reproducir una comparación.

## Evaluación del 80 %

La población operativa de este piloto son las páginas seleccionadas en el recorrido acotado de composición 4.5. Antes de conocer etiquetas, se toma un candidato por página con el menor SHA-256 de `piloto-site-41/` seguido del identificador de bloque. La rúbrica exige una acción o parámetro con un efecto o comprobación útil y correctamente atribuida. Un índice, una coincidencia léxica o un texto insuficiente cuentan como fallo. La traza registra la fracción de páginas que produjeron candidatos por separado.

El auditor cuenta $k$ muestras útiles entre $n$ revisadas. Se informa $k/n$ y el [límite inferior unilateral de Wilson al 95 %](README.md). Con $n=0$ o límite inferior por debajo de 0.80, los candidatos quedan pendientes de calibración. Las etiquetas se aíslan por fuente y versión del modelo. Un resultado solo cubre las condiciones y la unidad de muestreo evaluadas.

## Operación

El radar y el despliegue comparten el grupo de concurrencia de ingesta. Antes del relevo se espera a que concluya cualquier trabajo de Site o histórico. El registro de la release admite exactamente `paginas` y `blender_docs`. El piloto comprueba la firma `site/4.1`, el número de páginas, las decisiones y la cola del proyecto. La muestra y la clave de trabajo están en el registro de GitHub Actions.

## Ajuste después del primer piloto

Site 4.0 produjo 44 candidatos en 25 de 64 páginas. La revisión previa al ajuste valoró como útiles 19 de 25 (76 %). Quedaron identificados cuatro bloques de interfaz genérica, un ejemplo impreciso y un pasaje repetido entre nodos. [Despliegue 4.0](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44616678446).

Site 4.1 envía a revisión las descripciones de interfaz estandarizadas que carecen de explicación adicional y los usos nominales de «control» que antes simulaban una relación de efecto. Para bloques de prosa candidatos de al menos 30 palabras, conserva como referencia la repetición del mismo texto normalizado dentro de la misma fuente, programa y versión. Un cambio de valor, operador o contenido conserva su propia evidencia. En bronce se mantiene cada aparición con su cita.

El segundo piloto duplica el presupuesto solo para esta evaluación (hasta 128 intentos en un mismo trabajo). El radar ordinario conserva 64. Se contrasta cada URL con todas las páginas del trabajo 4.0 antes de seleccionar etiquetas. Se reportan por separado el recorrido operativo y las páginas nunca descargadas por 4.0. La habilitación utiliza únicamente muestras de páginas inéditas, revisadas con la rúbrica fijada antes de la corrida. El resultado también se contrasta con los primeros 64 intentos. Esta prueba valida la precisión de una muestra por página con candidatos en este capítulo. El rendimiento de captura y la cobertura de otras fuentes requieren mediciones propias.

[Compendio de modelos matemáticos del proyecto](compendio-2026-11-19.txt) · [Etiquetas por versión](auditoria.json). El compendio conserva las alternativas de investigación; esta ficha delimita las ecuaciones que ejecuta el código.

## Comprobación del inventario con el modelo congelado

El trabajo `883618/3/3` entregó 67 candidatos en 43 de 128 páginas. La primera reserva aportó 17 útiles de 21 muestras. Antes de extraer más páginas se fijó el segundo conjunto: todas las páginas `std:doc` del capítulo oficial ausentes de ambos trabajos anteriores, ordenadas por URL, hasta un máximo de 128. El auditor reutiliza el trabajo ya terminado al repetir la operación. El recorrido ordinario mantiene su presupuesto. [Dictámenes del piloto](revision-piloto-4.1.json) · [Plan de validación](validacion-site.json).

## Resultado verificado el 19 de noviembre de 2026

| Medición | Resultado |
|---|---:|
| Páginas del inventario de composición 4.5 visitadas con Site 4.1 | 131 de 131 |
| Páginas que produjeron candidatos | 46 de 131 (35,1 %) |
| Bloques útiles tras revisar todos los candidatos del lote | 64 de 70 (91,4 %) |
| Muestras útiles en páginas inéditas para el ajuste, una por página con candidatos | 20 de 24 (83,3 %) |
| Límite inferior unilateral de Wilson al 95 % sobre esas 24 páginas | 67,6 % |
| Umbral de habilitación automática de la fuente y el modelo | 80,0 % |

El piloto entregó 67 candidatos y la reserva final aportó otros 3. Codex revisó cada bloque con la rúbrica de utilidad técnica. La evaluación carece de segunda lectura humana. Los seis fallos fueron descripciones genéricas de mezcla o influencia, un parámetro que reformulaba su nombre y un pie de figura sin ajustes reproducibles. El censo mide este lote completo. **La publicación automática de candidatos de esta fuente y modelo queda pendiente de calibración.** Se agotó la reserva de páginas inéditas de esta edición.

El máximo observado en las verificaciones de Zyte fue un trabajo a la vez. La cola estaba vacía al cierre. En Azure quedaron `883618-3-3.jsonl.gz` (128 registros) y `883618-3-4.jsonl.gz` (3 registros), bajo `bronce/zyte/paginas/2026-11-19/`.

[Censo y dictamen por bloque](resultados-site-4.1.json) · [Despliegue y piloto](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44617738668) · [Inventario](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44619074242) · [Copia de las 128 páginas](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44585217011/attempts/3) · [Copia de las 3 restantes](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44585217011/attempts/4).
