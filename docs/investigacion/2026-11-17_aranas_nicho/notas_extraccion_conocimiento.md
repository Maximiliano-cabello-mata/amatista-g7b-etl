# Extracción y validación de conocimiento procedimental/tácito desde texto comunitario con LLMs (para G7B)

Notas de investigación. Etiquetas: **[PRÁCTICA]** = desplegado o probado en producción o por practicantes; **[PAPER]** = solo resultados de papers/benchmarks; **[VENDOR]** = cifra reportada por el propio proveedor sin verificación independiente. Nota de método: arxiv.org no se podía abrir desde esta sesión (bloqueo de red), así que las cifras de papers vienen de abstracts, fichas de Hugging Face y resúmenes secundarios; conviene verificarlas contra el PDF antes de citarlas en público.

## 1. Extracción con LLM hacia esquemas (structured outputs, documento vs claim), precisión y alucinación, papers 2023–2026

### Takeaway
La conformidad con el esquema (JSON válido) ya está resuelta en la práctica con constrained decoding (APIs y Ollama/llama.cpp en local). La exactitud del contenido no está resuelta: los errores típicos son valores alucinados o mal asociados (número ↔ entidad), unidades equivocadas y baja recall en esquemas complejos. Los esquemas simples y planos rinden mejor que los grandes y anidados. La extracción procedimental desde texto tipo wikiHow o manuales funciona razonablemente con GPT-4/4o, pero la validación humana sigue siendo necesaria.

### Cited Findings
- **[VENDOR]** OpenAI Structured Outputs (`response_format` con `strict: true`): en sus evals internas de "complex JSON schema following", gpt-4o-2024-08-06 saca 100% frente a <40% de gpt-4-0613 — [OpenAI](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- **[PRÁCTICA, anecdótico]** Hay desarrolladores que reportan fallos aun así; un hilo describe una tasa de fallo del 75% en tool calls que omitían una clave requerida — [OpenAI Community](https://community.openai.com/t/structured-outputs-not-reliable-with-gpt-4o-mini-and-gpt-4o/918735). Conclusión: validar siempre con Pydantic/JSON Schema después de la llamada.
- **[PRÁCTICA]** Ollama soporta structured outputs desde diciembre de 2024. El esquema JSON va en el campo `format` (dict o `model_json_schema()` de Pydantic) y también funciona vía el endpoint compatible con OpenAI (`response_format`) — [Ollama blog](https://registry.ollama.ai/blog/structured-outputs); [Ollama docs](https://docs.ollama.com/capabilities/structured-outputs)
- **[PRÁCTICA, blog secundario]** Ollama convierte el esquema a gramática GBNF de llama.cpp. Aun con `format`, algunos modelos meten preámbulo ("Sure! Here is the JSON") o inventan campos, así que hace falta un paso parse-and-repair — [insiderllm](https://insiderllm.com/guides/structured-output-local-llms/); [dev.to](https://dev.to/jangwook_kim_e31e7291ad98/ollama-structured-outputs-in-practice-getting-type-safe-json-from-local-llms-with-pydantic-m38)
- **[PAPER]** Ghosh et al. (ACL 2024, arXiv 2406.05348), extracción ad-hoc con esquema usando GPT-4 sobre dos datasets de materiales: los esquemas más simples dan mayor recall y menos alucinación. Los errores observados incluyen errores de parsing, de figuras, de comprensión y de conversión de unidades. Su Tabla 2 da los porcentajes match/missed/hallucinated, que no pude obtener — [resumen liner](https://liner.com/review/toward-reliable-adhoc-scientific-information-extraction-case-study-on-two)
- **[PAPER]** Tan & D'Souza (2026), extracción de evidencia para meta-análisis: los errores de "numerical grounding" producen valores o asociaciones número-entidad incorrectos, y la recall cae a valores cercanos a cero en tareas complejas — [alphaxiv 2602.10881](https://www.alphaxiv.org/abs/2602.10881.md)
- **[PAPER]** Se cita que GPT-4 extrae propiedades de materiales con ~90.8% de precisión y 87.7% de recall usando prompts. La atribución a Dagdelen et al. 2024 no está confirmada — [ceur-ws Vol-4240](https://ceur-ws.org/Vol-4240/paper52.pdf)
- **[PRÁCTICA, patrón]** Un pipeline de materiales (2026) usa validadores Pydantic que rechazan salidas fuera de límites físicos predefinidos — [ACL wasp 2026](https://aclanthology.org/2026.wasp-1.10.pdf). Es aplicable a G7B: rechazar VRAM > 200 GB, fps negativos, versiones de Blender inexistentes, etc.
- **[PAPER] Conocimiento procedimental:** Carriero et al. (arXiv 2412.03589, nov 2024) extraen pasos, acciones, objetos, equipo y tiempos de wikiHow hacia un KG procedimental, con ontologías P-Plan/K-Hub/Time. En evaluación humana (crowdsourcing), la salida del LLM iguala a la manual en exactitud, pero hay escepticismo sobre su aplicabilidad práctica. El repo cefriel/procedural-kg-llm usa GPT-4o, temperatura 0, LangChain y dos prompts — [resumen](https://sotaverified.org/papers/human-evaluation-of-procedural-knowledge); [aitopics](https://aitopics.org/doc/arxivorg:BFC9C22C)
- **[PAPER]** Rula & D'Souza (SEBD 2024): GPT-4 extrae pasos y subpasos de manuales en PDF con ROUGE >70% usando in-context learning — [ceur-ws Vol-3741](https://ceur-ws.org/Vol-3741/paper71.pdf); [arXiv 2310.03376](https://arxiv.org/html/2310.03376v1)
- **[PAPER]** Hay trabajo de 2026 sobre extracción procedimental de guías de troubleshooting industriales con modelos visión-lenguaje — [arXiv 2601.22754](https://arxiv.org/pdf/2601.22754) (no leído en detalle)
- **[PAPER] KG con LLM:** EDC (Extract-Define-Canonicalize, EMNLP 2024) hace extracción abierta, luego definición de esquema, luego canonicalización contra el esquema (con un retriever entrenado) — [arXiv 2404.03868](https://arxiv.org/abs/2404.03868v2). Zhu et al. encuentran que GPT-4 es mejor como asistente de inferencia que como extractor few-shot de entidades/relaciones — [arXiv 2305.13168](https://arxiv.org/abs/2305.13168v4). Hay construcción de KG anclada en el esquema de Wikidata para evitar hechos redundantes o inconsistentes — [arXiv 2412.20942](https://arxiv.org/html/2412.20942v1)
- **[PRÁCTICA] Caso real de tickets → KG:** LinkedIn (SIGIR 2024) convirtió tickets Jira históricos en un KG de dos niveles: estructura intra-ticket (secciones del issue) y relaciones entre tickets. Reportan +77.6% relativo en MRR, +0.32 BLEU, y la mediana del tiempo de resolución bajó de 7 h a 5 h (−28.6%) tras unos 6 meses en el equipo de soporte. La media bajó de 40 h a 15 h — [arXiv 2404.17723](https://arxiv.org/abs/2404.17723v1); [ZenML LLMOps DB](https://www.zenml.io/llmops-database/knowledge-graph-enhanced-rag-for-customer-service-question-answering)
- **[VENDOR]** Hay modelos pequeños especializados en extracción. NuExtract 1.5 (oct 2024) dice superar ligeramente a GPT-4o zero-shot en su benchmark interno de 600 ejemplos — [NuMind blog](https://numind.ai/blog/nuextract-1-5---multilingual-infinite-context-still-small-and-better-than-gpt-4o). NuExtract3 es un VLM de 4B, Apache-2.0, multilingüe; en su benchmark interno da 0.701 frente a 0.662 de Qwen3.5-4B, aunque las tablas del repo y de la ficha de HF no coinciden. NuMind advierte que el modo "reasoning" empeora a los modelos pequeños por bucles de repetición — [GitHub](https://github.com/numindai/nuextract); [HF](https://huggingface.co/numind/NuExtract3)

### Inferences
- Documento vs claim: la evidencia (esquemas simples con más recall y menos alucinación; recall que colapsa en tareas complejas) apunta a un diseño en dos pasos. Primero, extracción a nivel de claim con un esquema plano y pequeño por tipo de hecho (p. ej. `perf_claim`, `fix`, `procedure`), cada uno con una cita textual obligatoria (`evidence_quote`) y la URL más un ancla de post o comentario. Después, agregación a nivel de documento o hilo. Un único esquema gigante por hilo es lo que peor rinde según Ghosh et al.
- El campo de cita literal permite verificar de forma barata que el string aparece en la fuente (match exacto o difuso), lo que elimina una clase entera de alucinación sin necesitar un LLM juez.
- Para hilos de foro, la estructura de LinkedIn (separar estructura intra-hilo de relaciones entre hilos: duplicado-de, misma-solución) se puede trasladar casi directamente a Discourse + Gitea.

### Gaps
- No encontré tasas de alucinación publicadas para IE con LLM sobre texto de troubleshooting o foros (sí para ciencia de materiales y médica). No hay ningún benchmark específico de foros técnicos.
- No pude obtener las cifras exactas de alucinación de Ghosh et al. (Tabla 2) porque arxiv.org estaba bloqueado.
- No hay resultados comparativos independientes de NuExtract frente a Qwen/Gemma en español.

## 2. Minería de Q&A y bug trackers (soluciones, respuesta aceptada, entorno, duplicados, triage, votos como supervisión débil)

### Takeaway
La aceptación y los votos son señales útiles pero sesgadas por el tiempo: una gran parte de las respuestas obsoletas ya lo eran al publicarse y casi nunca se actualizan, así que la versión de Blender debe ser un campo obligatorio y servir como filtro. En bug reports, el LLM sirve como "extractor de información esencial" antes de un detector de duplicados clásico (Cupid). Blender ya estructura OS, GPU y versión en su plantilla, lo que hace que extraer el entorno sea casi determinista.

### Cited Findings
- **[PAPER]** Zhang et al. (TSE; ICSE 2020 journal-first), 52,177 hilos de respuestas de SO: el 58.4% de las respuestas obsoletas probablemente ya lo eran al publicarse, y solo el 20.5% de las observadas como obsoletas se actualizan. La reacción tarda en promedio 118 días (101 en otra versión del paper). Las causas principales son la evolución del lenguaje, referencias desactualizadas y cambios en herramientas — [arXiv 1903.12282](https://arxiv.org/pdf/1903.12282.pdf); [neverworkintheory](https://neverworkintheory.org/2022/03/08/obsolete-answers-on-stack-overflow.html); [replicación](https://github.com/SAILResearch/replication-obsolete_answers_SO/)
- **[PAPER]** El 11% de los enlaces en respuestas de SO están rotos (estudio de 2020), y solo el 6.91% de las respuestas Java aceptadas tienen más de una revisión — mismas fuentes ([arXiv 2010.04892](https://arxiv.org/pdf/2010.04892))
- **[PAPER, relevante para validar]** Kabir et al. (CHI 2024): de 517 preguntas de SO respondidas por ChatGPT, el 52% de las respuestas contiene información incorrecta, el 77% es verbosa y el 78% es inconsistente con las respuestas humanas. Los usuarios prefirieron ChatGPT el 35% de las veces y no detectaron la desinformación el 39% de las veces — [arXiv 2308.02312](https://arxiv.org/html/2308.02312v4). Implicación: nunca dejar que el LLM "complete" una solución; solo extraer lo que está en la fuente.
- **[PAPER]** Cupid (2023, rev. 2024) usa ChatGPT zero-shot para extraer la información esencial del bug report y la pasa al método clásico REP de detección de duplicados. Reporta estado del arte en 3 datasets frente a 3 baselines (no obtuve las cifras exactas de Recall@k) — [arXiv 2308.10022](https://arxiv.org/html/2308.10022v3)
- **[PAPER]** En un estudio pequeño, ChatGPT acertó 6 de 10 pares de duplicados de VSCode; los autores concluyen que no es del todo adecuado para esa tarea por sí solo — [arXiv 2305.16837](https://arxiv.org/pdf/2305.16837)
- **[PAPER]** GPTrace (ICSE '26) deduplica crashes con embeddings LLM de stack traces — [arXiv 2512.01609](https://arxiv.org/pdf/2512.01609v1.pdf). Un estudio de fine-tuning critica que muchos enfoques usan solo título y descripción e ignoran pasos de reproducción y comentarios de mantenedores — [SBC](https://sol.sbc.org.br/index.php/sbes/article/download/36991/36776)
- **[PRÁCTICA] Plantilla de bugs de Blender** (`.gitea/issue_template/bug.yaml`): la sección System Information tiene Operating system y Graphics card, y la sección Blender Version tiene Broken y Worked. Help > Report a Bug rellena el sistema y la versión automáticamente. La guía de triage exige OS, GPU y versión del driver, versión rota y opcionalmente la última que funcionaba — [plantilla](https://projects.blender.org/archive/blender-archive/src/commit/d7043a5aea4ad4affc6c302058a3e0e1cf9fa919/.gitea/issue_template/bug.yaml); [guía de triage](https://julianeisel.github.io/wiki.blender.org-dump/wiki/User:Rjg/HowToHelpTriagingBugs.html). Hay variantes de etiqueta ("Working", "Software Version") — [ejemplo](https://projects.blender.org/Alaska/bug-report-testing/issues/3)

### Inferences
- En Gitea conviene extraer el entorno con regex o un parser de la plantilla (determinista, sin coste) y reservar el LLM para síntoma, causa, workaround y estado (fixed in X.Y, won't fix). El par Broken/Worked da directamente una regresión con rango de versiones.
- Como supervisión débil, una respuesta aceptada con muchos votos en una versión de Blender cercana a la actual es un buen positivo. El cierre como "Resolved" con commit en Gitea es otra señal fuerte. Los votos antiguos sin versión deben ponderarse a la baja, por los datos de obsolescencia. No encontré un paper que cuantifique votos como etiqueta débil específicamente para LLM IE.

### Gaps
- No obtuve las métricas exactas de Cupid ni de otros papers de triage con LLM (arXiv bloqueado).
- No encontré estudios de minería de Discourse (Blender Artists / devtalk) en particular.

## 3. Claims de rendimiento (fps, tiempo de render, VRAM) con contexto de hardware, normalización de nombres de GPU, validación cruzada con Blender Open Data

### Takeaway
Hay una referencia natural para validar claims de rendimiento: Blender Open Data publica descargas JSON/CSV y snapshots diarios crudos, con el score Cycles por dispositivo. Para normalizar nombres de GPU existe dbgpu (TechPowerUp, más de 2000 GPUs, con búsqueda difusa). No encontré literatura académica específica sobre extracción de claims de rendimiento de hardware desde foros; esa parte es diseño propio.

### Cited Findings
- **[PRÁCTICA]** Blender Open Data permite consultar, ordenar y descargar datos en JSON y CSV, y ofrece un snapshot diario del JSON crudo. El score mide qué tan rápido Cycles renderiza muestras de path tracing en un dispositivo CPU o GPU (más alto es mejor) — [About Open Data](https://opendata.blender.org/about/); [sitio](https://opendata.blender.org/)
- **[PRÁCTICA]** Según una discusión de desarrolladores, el valor de la portada es la mediana de todos los benchmarks de ese par (dispositivo, escena), pero es la mediana de tiempos, no de scores: hay que verificarlo en los datos crudos. El raw es "schema v4" — [devtalk](https://devtalk.blender.org/t/blender-benchmark-and-open-data-website-feedback/1759?page=6); [ejemplo de benchmark](https://opendata.blender.org/benchmarks/ce26a30b-019d-4f3a-a67b-6abb67f56eb1). Ejemplo de JSON — [benchmark.json](https://projects.blender.org/archive/blender-my-data/src/commit/dd355c1fc32c4b018fe8f37c3a3fb3af8538d7a2/examples/benchmark.json)
- **[PRÁCTICA]** dbgpu (PyPI, painebenjamin): datos de TechPowerUp para más de 2000 GPUs (arquitectura, fabricación, APIs, rendimiento), unos 170 KB comprimido, exporta a JSON/CSV/PKL, CLI con `lookup ... --fuzzy`, builds mensuales (última dic 2025) y IDs/URLs de TechPowerUp — [PyPI](https://pypi.org/project/dbgpu/); [changelog](https://data.safetycli.com/changelogs/dbgpu)
- **[PRÁCTICA]** Hay un dataset crudo de TechPowerUp en HF, sin capa de normalización — [Jr23xd23/gpu-database](https://huggingface.co/datasets/Jr23xd23/gpu-database/viewer/default/train?p=1)
- **[PAPER]** Riesgo conocido: los errores de "numerical grounding" (número asignado a la entidad equivocada) y de conversión de unidades son los más frecuentes en extracción numérica — [Tan & D'Souza](https://www.alphaxiv.org/abs/2602.10881.md); [Ghosh et al.](https://liner.com/review/toward-reliable-adhoc-scientific-information-extraction-case-study-on-two)

### Inferences
- Esquema sugerido para `perf_claim`: blender_version, render_engine (Cycles/EEVEE/Workbench), backend (CUDA/OptiX/HIP/Metal/oneAPI), device_raw, device_norm (ID de dbgpu), cpu, ram_gb, os, driver, scene_desc, metric (render_time_s, fps, vram_gb, samples/min), value, unit, baseline_value (si es un antes/después), setting_changed, evidence_quote, url+anchor, date.
- Validación cruzada: normalizar el dispositivo y comparar el orden de magnitud contra la mediana de Open Data para el mismo dispositivo y versión. Los claims absolutos (segundos por frame) dependen de la escena y no son comparables, así que conviene validar sobre todo los ratios ("OptiX ×1.5 frente a CUDA en la misma GPU") y la jerarquía entre GPUs. Marcar como outlier si contradice el orden relativo de Open Data.
- La concordancia entre varias fuentes independientes para el mismo claim normalizado (mismo device_norm, setting y signo del efecto) es una señal de confianza barata.

### Gaps
- No hay documentación oficial de un endpoint API de Open Data ni de los nombres exactos de campos; hay que inspeccionar el snapshot.
- No encontré papers sobre extracción de benchmarks de hardware desde foros ni sobre normalización de nombres de GPU con LLM.

## 4. Validación: muestreo humano, acuerdo inter-anotador, LLM-as-judge, consistencia entre extracciones, procedencia, confianza; patrón FineWeb-Edu

### Takeaway
El patrón "un LLM etiqueta una muestra y un clasificador pequeño escala" está probado a gran escala: FineWeb-Edu obtuvo un F1 binario del 82% replicando las etiquetas de Llama-3-70B. Los LLM etiquetan con alta consistencia y suelen superar a crowdworkers, pero la consistencia no es exactitud, y los clasificadores destilados recuperan solo una parte del gap respecto a etiquetas de oro, con peor rendimiento en clases minoritarias. Como juez, GPT-4 alcanza más del 80% de acuerdo con humanos en preferencias (similar al acuerdo entre humanos), con sesgos de posición, verbosidad y autopreferencia. La consistencia entre muestras es mejor señal de confianza que la confianza verbalizada.

### Cited Findings
- **[PRÁCTICA] FineWeb-Edu:** Llama-3-70B-Instruct puntuó unas 450–460k páginas (0–5) por valor educativo. Se entrenó un clasificador sobre 410k anotaciones con 50k de validación (las etiquetas del LLM se tratan como verdad). Con umbral 3 logra un F1 binario del 82%. Puede sobreajustarse a contenido de "aspecto académico" en los scores altos. El resultado son 1.3T tokens, y con ~10× menos tokens iguala en MMLU a otros datasets — [ficha HF](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier); [paper FineWeb](https://arxiv.org/pdf/2406.17557); [dataset README](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu/blob/main/README.md)
- **[PAPER]** Gilardi et al. (PNAS 2023): ChatGPT zero-shot supera a MTurk en unos 25 puntos de exactitud de media. El acuerdo intercodificador es ~56% en MTurk, ~79% en anotadores entrenados, 91% en ChatGPT con temperatura 1 y 97% con temperatura 0.2. Es unas 20–30 veces más barato que MTurk (la cifra varía entre versiones). La exactitud se midió contra anotadores de los propios autores — [arXiv 2303.15056](https://arxiv.org/abs/2303.15056v1); [HF papers](https://huggingface.co/papers/2303.15056.md)
- **[PAPER]** Clasificadores tipo BERT entrenados con etiquetas de LLM recuperan solo el 60–75% del gap respecto a etiquetas de oro, y tanto el LLM como el RoBERTa rinden peor en clases minoritarias — [promptlayer resumen](https://www.promptlayer.com/research-papers/knowledge-distillation-in-automated-annotation-supervised-text-classification-with-llm-generated-training-labels); [arXiv 2504.15432](https://arxiv.org/pdf/2504.15432v1.pdf)
- **[PAPER, Amazon]** PGKD: los modelos destilados son hasta 130× más rápidos y 25× más baratos que el LLM en inferencia para la misma clasificación — [arXiv 2411.05045](https://arxiv.org/html/2411.05045v1); [EMNLP 2024](https://preview.aclanthology.org/setup/2024.emnlp-main.215)
- **[PRÁCTICA]** Tutorial de HF: auto-etiquetado con LLM, revisión humana y luego SetFit. Reportan que SetFit supera al Llama-3.1-8B zero-shot — [HF blog](https://huggingface.co/blog/sdiazlor/custom-text-classifier-ai-human-feedback). SetFit con MiniLM es ~123× más rápido en inferencia que T-Few 3B, con una pequeña caída de score — [arXiv 2209.11055](https://arxiv.org/pdf/2209.11055). Un practicante sustituyó un etiquetador LLM por SetFit y obtuvo resultados deterministas con coste marginal casi nulo — [dev.to](https://dev.to/maksim_g_5e9b4b7a29285350/machinelearning-nlp-python-onnx-51kp)
- **[PAPER]** LLM-as-judge (Zheng et al., NeurIPS 2023): GPT-4 tiene más del 80% de acuerdo con preferencias humanas, el mismo nivel que entre humanos. Hay sesgos de posición, verbosidad, autopreferencia y razonamiento limitado, parcialmente mitigables — [arXiv 2306.05685](https://arxiv.org/html/2306.05685v4); [NeurIPS](https://neurips.cc/virtual/2023/poster/73434)
- **[PAPER]** Confianza: las respuestas consistentes entre muestras repetidas tienden a ser correctas, y los métodos de consistencia superan a la confianza verbalizada, que suele ser sobreconfiada. DINCO (ICLR 2026) combina ambas y supera a la self-consistency escalada. La consistencia cae con la temperatura (66% con T=0.2 frente a 30% con T=2.0, preprint) — [arXiv 2411.02454](https://arxiv.org/pdf/2411.02454.pdf); [arXiv 2509.25532](https://arxiv.org/pdf/2509.25532v2); [arXiv 2503.00031](https://arxiv.org/html/2503.00031v1)
- **[PAPER]** Validación humana de extracción procedimental vía crowdsourcing: la exactitud es comparable a la manual, pero los evaluadores son escépticos sobre su uso práctico — [Carriero et al.](https://sotaverified.org/papers/human-evaluation-of-procedural-knowledge)

### Inferences
- Pipeline de validación barata para G7B:
  1. Validación de esquema (Pydantic) más reglas de dominio (rangos, versiones válidas, nombres de GPU resolubles con dbgpu).
  2. Verificación de la cita literal contra el HTML fuente.
  3. Dos extracciones (dos modelos, o el mismo modelo con otra semilla) y comparación campo a campo: el acuerdo da confianza y el desacuerdo manda el caso a revisión humana.
  4. Muestreo humano estratificado por tipo de fuente y por confianza, p. ej. 50–100 ítems por ronda, midiendo precisión por campo. Con dos revisores en una submuestra se calcula Cohen's kappa. Este es el estándar metodológico; no encontré cifras específicas del dominio.
  5. Un LLM juez solo para criterios difíciles (¿la solución realmente resolvió el problema según el hilo?), sabiendo que tiene sesgos.
- Para sustituir el filtro de palabras clave: aplicar el patrón FineWeb-Edu a escala pequeña. Etiquetar unos 2–5k documentos con un LLM barato (o local) usando una rúbrica 0–5 de "contiene conocimiento procedimental o de rendimiento útil para Blender", revisar unos 200 a mano, y entrenar SetFit o un encoder multilingüe pequeño. Hay que vigilar las clases minoritarias (p. ej. claims de rendimiento), que son donde la destilación pierde más.

### Gaps
- No encontré tasas de error de LLM-as-judge específicamente para verificar extracciones (fidelidad a la fuente) en lugar de preferencias de chat.
- No hay estudios de calibración de self-consistency campo a campo en IE.

## 5. Traducción y localización al español conservando citas y licencias (CC BY-SA)

### Takeaway
Traducir contenido CC BY-SA crea una adaptación: el resultado debe licenciarse como BY-SA (o compatible) y atribuir enlazando al post original y a los autores. El contenido de Stack Exchange tiene versión de licencia según la fecha (2.5/3.0/4.0). Lo más seguro es almacenar los hechos con la URL original, el autor y la licencia por ítem, y publicar las fichas traducidas bajo CC BY-SA 4.0.

### Cited Findings
- **[PRÁCTICA/legal]** Wiki de CC: una traducción de una obra SA se trata como adaptación y debe licenciarse de forma compatible; el aporte del traductor también va bajo SA. Excepción: el uso interno sin compartir. Lo que cuenta como adaptación depende de la jurisdicción (la página es informativa, no asesoría legal) — [CC ShareAlike interpretation](https://wiki.creativecommons.org/ShareAlike_interpretation)
- **[PRÁCTICA]** Atribución en Stack Exchange: hipervínculo a la pregunta original y a los perfiles de todos los participantes — [SO blog 2009](https://stackoverflow.blog/2009/06/04/stack-overflow-creative-commons-data-dump/); [Defending Attribution Required](https://stackoverflow.blog/2010/08/11/defending-attribution-required). Permite "remix" y construir encima respetando la atribución — [SO blog 2014](https://stackoverflow.blog/2014/01/23/stack-exchange-cc-data-now-hosted-by-the-internet-archive/)
- **[PRÁCTICA]** Versiones de licencia de SE por fecha: antes del 2011-04-08 es CC BY-SA 2.5; entre 2011-04-08 y 2018-05-01 es 3.0; después es 4.0 — [HF dataset card](https://huggingface.co/datasets/flymin/stackexchange_20260331)
- **[PRÁCTICA]** En 2024 Stack Exchange restringió el acceso al dump, y los críticos dicen que contradice la licencia CC BY-SA — [DevClass](https://www.devclass.com/development/2024/07/30/stack-exchange-restricts-access-to-dump-of-user-contributed-data-critics-complain-this-contradicts-license/1625192); [Archive Team](https://wiki.archiveteam.org/index.php/Stack_Overflow). Los dumps siguen circulando vía Academic Torrents (p. ej. 2025-12-31) — [Academic Torrents](https://academictorrents.com/details/0d1d597fa7809f0e85f127b5eb3088219ddbad39)

### Inferences
- Extraer en inglés (los esquemas y los valores numéricos son agnósticos del idioma) y traducir solo los campos textuales (goal, steps, symptom), manteniendo `evidence_quote` en el idioma original. Así la verificación contra la fuente sigue funcionando y la traducción queda como capa separada y regenerable.
- Mantener los nombres de UI de Blender en inglés con la traducción oficial española entre paréntesis, porque los usuarios pueden tener la UI en cualquiera de los dos idiomas. Que exista un glosario oficial es una suposición: hay que verificarlo en los archivos .po de la traducción de Blender.
- Licencias mezcladas: los hilos de foros Discourse y los blogs pueden no ser CC. Hay que guardar `license` por fuente, y los hechos (no expresivos) más un enlace son menos problemáticos que copiar texto. No es asesoría legal.

### Gaps
- No encontré guía oficial de CC sobre si un "hecho extraído y parafraseado" constituye adaptación. Tampoco encontré las licencias de Blender Artists, devtalk y el manual de Blender (el manual se suele citar como CC BY-SA 4.0; no lo verifiqué en esta sesión).
- No encontré benchmarks de calidad de traducción técnica EN→ES con modelos pequeños.

## 6. Herramientas baratas: modelos open-weight pequeños, batch APIs, embeddings para agrupar soluciones duplicadas

### Takeaway
Las tres APIs principales ofrecen un 50% de descuento en batch (ventana de 24 h); Anthropic además combina batch con prompt caching. En local, Ollama con esquema JSON y un modelo de 4–8B (Qwen, Gemma, NuExtract) es la opción de coste cero, con parse-and-repair. Para duplicados, la similitud coseno sobre embeddings multilingües (bge-m3) con umbral calibrado es más simple que BERTopic; BERTopic sirve para descubrir temas.

### Cited Findings
- **[PRÁCTICA]** Las Batch APIs de OpenAI, Gemini y Anthropic tienen un 50% de descuento, con ventana de 24 h (OpenAI la garantiza; Anthropic suele completar en minutos u horas sin SLA formal). El batch de Anthropic se puede combinar con prompt caching. El límite de Anthropic era de 10k peticiones por batch en el lanzamiento y fuentes posteriores citan 100k — [Anthropic](https://anthropic.com/news/message-batches-api); [Simon Willison](https://feeds.simonwillison.net/2024/Oct/8/anthropic-batch-mode/); [tracker 2026](https://www.digitalapplied.com/blog/llm-batch-api-pricing-landscape-2026). xAI solo ofrece un 20% de descuento — mismo tracker
- **[PRÁCTICA]** Ollama structured outputs funciona en local, pero no en Ollama Cloud (según las docs en el momento de la búsqueda) — [Ollama docs](https://docs.ollama.com/capabilities/structured-outputs)
- **[VENDOR]** NuExtract (4B, Apache-2.0, multilingüe): conviene usar el modo sin razonamiento por defecto — [HF](https://huggingface.co/numind/NuExtract3)
- **[PRÁCTICA]** bge-m3 se basa en XLM-RoBERTa-large, cubre más de 100 idiomas y da nDCG@10 de 0.6657 en duplicados de AskUbuntu (retrieval, no clustering) — [Superlinked](https://telemetry.superlinked.com/models/baai-bge-m3--score); [emergentmind](https://www.emergentmind.com/topics/multilingual-bge-m3-model). El umbral de coseno de ~0.9 viene de NLP general y hay que calibrarlo por dominio — [Zilliz FAQ](https://zilliz.com/ai-faq/what-is-an-example-of-using-sentence-transformers-for-duplicate-question-detection-in-forums-or-qa-websites.md)
- **[PRÁCTICA]** BERTopic funciona con embeddings, reducción de dimensionalidad y HDBSCAN (por defecto) más c-TF-IDF. Usar k-Means evita outliers con algo menos de coherencia — [Zilliz BERTopic](https://zilliz.com/learn/explore-bertopic-novel-neural-topic-modeling-technique); [TDS](https://towardsdatascience.com/a-practical-guide-to-bertopic-for-transformer-based-topic-modeling/)
- **[PRÁCTICA]** Clasificador barato de relevancia: SetFit o un encoder pequeño destilado, entre 25× y 130× más barato que un LLM en inferencia — [PGKD](https://arxiv.org/html/2411.05045v1); [SetFit](https://arxiv.org/pdf/2209.11055)

### Inferences
- Stack de coste casi cero recomendado:
  - Scraping a JSONL, más un parser determinista de la plantilla de Gitea.
  - Clasificador de relevancia SetFit/multilingual-e5 entrenado con etiquetas de un LLM (patrón FineWeb-Edu).
  - Extracción por claim con Ollama y Qwen o Gemma de 4–8B (o NuExtract) con esquema JSON. Los casos de baja confianza o desacuerdo pasan a una API en batch (50% de descuento) con un modelo grande.
  - bge-m3 para deduplicar fixes y procedimientos, con un umbral calibrado sobre unos 100 pares etiquetados a mano.
  - dbgpu para normalizar hardware y el snapshot de Open Data para validar.
  - Revisión humana de una muestra estratificada.
- El coste de API para miles de hilos con modelos pequeños en batch suele ser de pocos dólares. No es una cifra verificada; el coste depende de los precios por token actuales, que no consulté.

### Gaps
- No obtuve precios por token actuales (nov 2026) de los modelos baratos (Haiku, GPT-mini, Gemini Flash); hay que consultar las páginas oficiales.
- No encontré documentación oficial verificada de las gramáticas de llama.cpp ni del guided decoding de vLLM en esta búsqueda.
- No encontré casos documentados de equipos pequeños o educativos que construyan una KB de troubleshooting desde foros; el caso más sólido es el de LinkedIn (gran empresa).
