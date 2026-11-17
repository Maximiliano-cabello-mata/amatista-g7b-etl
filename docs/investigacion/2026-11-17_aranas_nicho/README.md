# Arañas para conocimiento de nicho de Blender (17 de noviembre de 2026)

Investigación sin código: cómo sacarle todo el potencial a las arañas de G7B para llegar a conocimiento que no está en el manual. Cubre pipelines de producción, ajustes de hardware para equipos modestos, migración desde Maya y 3ds Max y conocimiento de la comunidad.

| Archivo | Qué contiene |
|---|---|
| [REPORTE.md](REPORTE.md) | **Empieza aquí.** El reporte completo, con 12 decisiones priorizadas. Cada afirmación va marcada como [PROBADO], [TEÓRICO] o [DISEÑO] |
| [notas_fuentes_de_nicho.md](notas_fuentes_de_nicho.md) | Dónde vive el conocimiento de nicho, con licencia, robots.txt y términos de cada fuente |
| [notas_crawling_enfocado.md](notas_crawling_enfocado.md) | Estado del arte en arañas enfocadas y guiadas por IA, descubrimiento de fuentes y rastreo incremental |
| [notas_errores_y_aciertos.md](notas_errores_y_aciertos.md) | Errores y aciertos documentados en proyectos reales: legales, técnicos, de deduplicación, de costo y de RAG |
| [notas_extraccion_conocimiento.md](notas_extraccion_conocimiento.md) | Cómo extraer conocimiento procedimental y tácito con IA, y cómo validarlo |

**Conclusión en una línea:** el cuello de botella no es la fuerza de rastreo sino el manejo de los datos. Hay que saber qué se puede usar, a qué versión de Blender aplica y cómo se atribuye. Las mejores fuentes de nicho tienen canales estructurados (Git, copias completas, APIs JSON) y no necesitan una araña más agresiva.

**Limitación:** la red de la sesión bloqueó casi todos los sitios. Solo el robots.txt de docs.blender.org se verificó directamente; lo demás hay que confirmarlo desde Zyte o Azure antes de rastrear.

Relacionado: [el nicho, fuentes y metodología](../2026-11-17_nicho_fuentes_y_metodologia.md) · [qué IA usar](../2026-11-17_decision_ia.md).
