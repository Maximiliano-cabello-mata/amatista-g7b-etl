# Errores y aciertos documentados en proyectos de scraping/crawling para bases de conocimiento y RAG (aplicado a G7B)

Etiquetas usadas en cada ítem:
- **[DOC]** = documentado en proyectos reales (paper, postmortem, documentación oficial, fallo judicial).
- **[TEO]** = recomendado en teoría / guía de proveedor / tutorial, sin evidencia medida publicada.
- **[INF]** = inferencia propia para G7B (va en la subsección Inferences).

Nota de método: en esta sesión, huggingface.co, arxiv.org y kapa.ai **no fueron accesibles con WebFetch** (bloqueo de red del entorno), así que casi todo viene de resultados de búsqueda que resumen fuentes primarias (papers en arxiv/NeurIPS, docs de Zyte/MongoDB/GitHub, análisis de despachos). Las cifras que solo vienen de fuentes secundarias se marcan. Las fuentes anteriores a 2022 se marcan como "(antigua)".

---

## 1. Proyectos de datos a gran escala (Common Crawl, C4, RefinedWeb, FineWeb/FineWeb-Edu, DCLM, Dolma): qué errores y lecciones de filtrado reportaron y qué se aplica a un proyecto temático pequeño

### Takeaway
Los grandes corpus coinciden en tres lecciones que se transfieren directamente a G7B: (1) extraer el texto uno mismo del HTML con un extractor tipo trafilatura es mejor que usar texto "pre-extraído"; (2) los filtros heurísticos pueden **sobre-filtrar** de forma destructiva (el filtro de puntuación final de C4 eliminaba ~30% de los tokens) y deben medirse por su tasa de eliminación; (3) la deduplicación agresiva no siempre mejora: FineWeb vio que deduplicar globalmente entre snapshots era peor que hacerlo por snapshot, porque se pierden copias útiles.

### Cited Findings
- [DOC] FineWeb comparó extracción con Trafilatura sobre WARC frente al texto WET por defecto de Common Crawl; la extracción propia rindió mejor. Usaron Trafilatura con `favour_precision=True`. — [FineWeb paper (arXiv 2406.17557)](https://arxiv.org/pdf/2406.17557); [Blog FineWeb (HF)](https://huggingfacefw-blogpost-fineweb-v1.static.hf.space/index.html)
- [DOC] DCLM (DataComp-LM) llegó a la misma conclusión: resiliparse y trafilatura mejoran la métrica CORE en al menos 2.5 puntos frente a WET. — [DCLM paper (arXiv 2406.11794)](https://arxiv.org/pdf/2406.11794)
- [DOC] FineWeb hizo deduplicación MinHash **por snapshot individual** y no global. Deduplicar cada snapshot por separado igualó el rendimiento de RefinedWeb. Los autores concluyen que eliminar los grandes clusters de duplicados comunes a todos los crawls ayuda, pero que **sobre-deduplicar clusters pequeños puede ser perjudicial**. — [FineWeb paper](https://arxiv.org/pdf/2406.17557); [NeurIPS 2024 version](https://papers.neurips.cc/paper_files/paper/2024/file/370df50ccfdf8bde18f8f9c2d9151bda-Paper-Datasets_and_Benchmarks_Track.pdf)
- [DOC] El filtro de "terminal punctuation" de C4 (descarta líneas que no terminan en puntuación) eliminaba ~30% de todos los tokens según el blog de FineWeb, y el paper dice que eliminaba "una cantidad excesivamente grande de datos". FineWeb aplicó todos los filtros de C4 **excepto** ese. "Todos los filtros excepto el (muy destructivo) terminal_punct" rindió mejor que terminal_punct solo, eliminando en total ~7%. — [Blog FineWeb](https://huggingfacefw-blogpost-fineweb-v1.static.hf.space/index.html); [FineWeb paper](https://arxiv.org/pdf/2406.17557)
- [DOC] FineWeb-Edu: clasificador entrenado con 450k anotaciones de Llama-3-70B (escala 0–5). El umbral 3 da F1 de 82% como clasificador binario, y la ficha del modelo recomienda `int_score >= 3`. Con ese umbral se conservaron 1.3T tokens y se eliminó **~92%** de FineWeb. — [Ficha fineweb-edu-classifier](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier); [aiwiki FineWeb-Edu (secundaria)](https://aiwiki.ai/wiki/fineweb_edu)
- [DOC, secundaria] Las mejoras reportadas en MMLU/ARC con FineWeb-Edu varían según el resumen (de ~33% a ~37% en MMLU; "+4 MMLU, +11 ARC" con 1.71B; "5–7 puntos"). Las cifras no coinciden entre resúmenes, así que hay que verificarlas en el paper. — [aiwiki](https://aiwiki.ai/wiki/fineweb_edu); [ZeroEntropy](https://www.zeroentropy.dev/concepts/fineweb/)
- [DOC, secundaria] Limitaciones conocidas del clasificador educativo: hereda los sesgos de un solo anotador LLM, tiende a premiar contenido que "parece académico" (prosa formal) frente a material igual de útil pero más llano, y subir el umbral por encima de 3 empieza a perjudicar HellaSwag/PIQA (este último punto no lo verifiqué en el paper). — [aiwiki FineWeb-Edu](https://aiwiki.ai/wiki/fineweb_edu)
- [DOC] Un paper de ACL 2026 sobre fallos de los clasificadores de calidad encontró que, con umbral 3, reescribir en estilo Wikipedia texto que originalmente puntuaba ≤2 lo hacía pasar en 5–7% de los casos (NemoCurator Mixtral >7%, FineWeb-Edu 6%). Es decir, el clasificador es sensible al estilo y no solo al contenido. — [ACL 2026 short paper](https://aclanthology.org/2026.acl-short.10.pdf)
- [DOC] RefinedWeb (Falcon): leyó WARC directamente con trafilatura, aplicó reglas a nivel documento y línea, una blocklist de URLs NSFW de ~4.6M dominios más puntuación de URL por listas de palabras, y deduplicación por subcadena exacta + MinHash que eliminó ~50%. — [RefinedWeb paper (arXiv 2306.01116)](https://ar5iv.labs.arxiv.org/html/2306.01116); [Christian Perone, blog (2023)](https://blog.christianperone.com/2023/06/appreciating-llms-data-pipelines/)
- [DOC, secundaria] Dolma deduplica con filtros Bloom a nivel URL, documento y párrafo, **dentro de cada fuente pero no entre fuentes**, y reimplementa heurísticas de C4/Gopher en lugar de clasificadores. — [Dolma paper (ar5iv 2402.00159)](https://ar5iv.labs.arxiv.org/html/2402.00159); [resumen neura.market](https://neura.market/ai-and-ml-research-papers/dolma)
- [DOC] DCLM usó un filtro Bloom modificado (BFF) a nivel documento y párrafo, con rendimiento comparable a MinHash pero mucho mejor escalabilidad (>10 TB), seguido de un filtro de calidad fastText. — [DCLM paper](https://arxiv.org/pdf/2406.11794); [resumen DCLM (secundaria)](https://summary-of-some-paper-in-cuda.readthedocs.io/en/latest/pretraining/DataComp-LM-Insearchofthenextgenerationoftrainingsetsforlang/)
- [DOC] Zyphra (Zyda-2) aplicó el filtro de calidad por modelo solo a las fuentes menos filtradas (Zyda-1, Dolma-CC) y no a las ya curadas. También informó de muchos duplicados internos en DCLM y FineWeb-Edu, aunque esos papers decían que la deduplicación interna no ayudaba. — [Zyphra, Building Zyda-2](https://zyphra.com/post/building-zyda-2)

### Inferences
- [INF] El problema de G7B de que el "filtro de relevancia por palabras clave rechaza páginas útiles" tiene la misma forma que el sobre-filtrado de terminal_punct en C4. Lo que se aprende de FineWeb es **medir la tasa de eliminación por filtro e inspeccionar a mano una muestra de lo rechazado** antes de adoptar un filtro. Para un corpus temático pequeño (el manual de Blender es todo relevante por definición), la relevancia debería decidirse por la **fuente/sección (allowlist de URLs)** y no por palabras clave del contenido. Los filtros de contenido deberían reservarse para fuentes comunitarias ruidosas, que es lo que hizo Zyphra.
- [INF] La lección de FineWeb (no deduplicar globalmente entre snapshots) aplica casi literalmente a los "duplicados casi exactos entre versiones del manual que se rechazaban": esas versiones son como snapshots. Conviene deduplicar **dentro de una versión** y mantener las variantes entre versiones con metadatos de versión.
- [INF] Un clasificador educativo tipo FineWeb-Edu probablemente rechazaría foros, Q&A y tutoriales informales en español porque premia la prosa académica. Para contenido comunitario es mejor un umbral bajo o un etiquetado sin descarte.
- [INF] A escala pequeña (miles de páginas), la deduplicación exacta por hash del texto normalizado más MinHash/SimHash dentro de una versión es barata. No hace falta replicar la infraestructura de Bloom filters.

### Gaps
- No pude leer directamente los parámetros MinHash de FineWeb (n-gramas, buckets, umbral ~0.75 que se cita con frecuencia) porque arxiv.org y huggingface.co estaban bloqueados. Un resumen secundario afirma que RefinedWeb, FineWeb y SlimPajama usan MinHash sobre 5-gramas con LSH, pero no lo verifiqué. — [Perone blog](https://blog.christianperone.com/2023/06/appreciating-llms-data-pipelines/)
- No encontré fuentes que traten específicamente sobre RedPajama ni postmortems de Common Crawl.
- No encontré ningún estudio que mida el conocimiento perdido en el ~92% que descarta FineWeb-Edu.

---

## 2. RAG sobre documentación técnica: lecciones documentadas (chunking, documentación versionada, citas, contenido obsoleto, evaluación)

### Takeaway
El fallo más documentado en RAG sobre documentación es la **mezcla de versiones**: el retriever trae fragmentos semánticamente perfectos pero de otra versión. Los metadatos de versión solo ayudan si se filtran **antes** de la búsqueda por similitud. Los proveedores (Kapa.ai) insisten en curar las fuentes, citar con enlaces y hacer chunking que respete la estructura del código, aunque esto es material de proveedor y no tiene métricas independientes.

### Cited Findings
- [DOC] Paper VersionRAG (2025): el RAG estándar recupera contenido semánticamente similar de varias versiones. En un benchmark de 34 documentos técnicos versionados, VersionRAG alcanzó 90% de precisión frente a 58% del RAG ingenuo y 64% de GraphRAG. Propone enrutar según el tipo de consulta (contenido, listado de versiones, cambios entre versiones). — [VersionRAG (arXiv 2510.08109)](https://arxiv.org/html/2510.08109)
- [DOC, anecdótico] Reporte de un practicante: la causa raíz de las respuestas erróneas eran fragmentos de documentación de versiones incompatibles que coexistían sin metadatos que los distinguieran. — [aiweekly (resumen de un post de Reddit)](https://aiweekly.co/node/2592)
- [TEO] Guardar campos como `version`, `is_current`, `valid_from` o `superseded_by` no cambia la búsqueda por vecinos más cercanos. Si se recupera todo el espacio y la versión solo se muestra después, un fragmento obsoleto puede entrar al prompt y recibir la cita final. — [Zimaspace blog](https://shop.zimaspace.com/blogs/tech-ai-hub/rag-citations-point-superseded-document-versions)
- [TEO] Guía de AWS Builder: cuando el RAG sigue respondiendo mal después de actualizar la documentación, verificar que la fuente se resincronizó, eliminar o filtrar versiones viejas, y probar la recuperación por separado de la generación ("mira los chunks antes que la respuesta"). — [AWS Builder Center](https://builder.aws.com/content/3KYVgdVvBszygwKcGrZblhI4bZt/rag-still-answering-wrong-after-you-updated-the-docs-check-the-librarian-not-the-temperature)
- [TEO / proveedor] Kapa.ai dice haber trabajado con más de 100 equipos técnicos (Docker, CircleCI, Reddit, Monday.com). Recomienda empezar por las fuentes núcleo (documentación, referencia de API, notas de versión) y fundamentar las respuestas en ellas. — [Kapa.ai, RAG Best Practices](https://www.kapa.ai/blog/rag-best-practices)
- [TEO / proveedor] Kapa sostiene que mejorar la recuperación y los datos rinde más que cambiar de LLM, y que en productos técnicos el chunking consciente del código permite citar el archivo y la línea exactos. — [Kapa.ai, How to Improve RAG Accuracy](https://www.kapa.ai/library/how-to-improve-rag-accuracy-10-techniques-that-work)
- [TEO / proveedor] Kapa publica una guía para escribir documentación pensando en RAG, con la premisa de que la calidad de la respuesta depende de la calidad de la documentación que se recupera. — [docs.kapa.ai, writing best practices](https://docs.kapa.ai/improving/writing-best-practices)
- [DOC] Un estudio académico (University of Minnesota) sobre el chatbot RAG de Kapa en comunicación técnica señala que, a diferencia de ChatGPT, el bot de Kapa sí fundamenta con enlaces directos a la documentación. — [UMN Conservancy](https://conservancy.umn.edu/server/api/core/bitstreams/7b4b3ce9-4553-4c82-86c8-f7c6c3b6bb80/content)
- [DOC] Paper "Engineering RAG Systems for Real-World Applications" (2025): documenta 12 lecciones de cinco aplicaciones de dominio. No es de Kapa. — [arXiv 2506.20869](https://arxiv.org/html/2506.20869v1)

### Inferences
- [INF] Para G7B: cada chunk en MongoDB debería llevar `blender_version`, `lang`, `source_type` (manual/foro/tutorial), `canonical_url` y `is_latest`, con un **pre-filtro** (`filter` en `$vectorSearch`) por versión. La versión por defecto debería ser la LTS o estable actual, y la UI debería permitir elegir otra.
- [INF] Como el manual de Blender cambia la interfaz entre versiones (2.7x frente a 2.8+ frente a 4.x/5.x), las preguntas educativas en español sufrirán exactamente el modo de fallo que describe VersionRAG si se indexan varias versiones sin filtro.
- [INF] Hay que evaluar la recuperación por separado: un conjunto pequeño de preguntas reales de estudiantes con la URL esperada (recall@k), repetido después de cada re-ingesta.

### Gaps
- No pude abrir los artículos de Kapa (dominio bloqueado). Tampoco encontré postmortems públicos con métricas de Mendable, del bot de documentación de LangChain (chat-langchain), de Microsoft Learn ni de OverflowAI de Stack Overflow. No los cito.

---

## 3. Práctica con Scrapy/Zyte: errores comunes, DeltaFetch, dupefilter, monitorización con Spidermon (deriva silenciosa de cobertura)

### Takeaway
Los dos errores de Scrapy que mejor explican los síntomas de G7B son: (1) asumir que el dupefilter da deduplicación persistente o a nivel de item, cuando solo filtra requests dentro de un job; y (2) no tener un mecanismo incremental (DeltaFetch, o requests condicionales con fecha/ETag/sitemap lastmod). En Scrapy Cloud hay además una trampa de configuración documentada por Zyte. Los "fallos silenciosos" (menos items sin errores) solo los detectan monitores de recuento y de cobertura de campos.

### Cited Findings
- [DOC] El blog de Zyte ("Scrapy Tips from the Pros", 2016, antigua) recomienda DeltaFetch para re-crawls periódicos: evita pedir páginas ya raspadas en ejecuciones anteriores, y se resetea con un argumento del spider. — [Zyte blog (2016)](https://www.zyte.com/blog/scrapy-tips-from-the-pros-july-2016/)
- [DOC] Trampa específica de Scrapy Cloud: activar DeltaFetch a nivel de proyecto o en `settings.py` **no funciona**, porque la configuración por defecto de Zyte se propaga a nivel de organización y tiene más prioridad. — [Zyte Support, Incremental crawls with DeltaFetch](https://support.zyte.com/support/solutions/articles/22000221912-incremental-crawls-with-scrapy-and-deltafetch-in-scrapy-cloud)
- [DOC] El add-on DeltaFetch del dashboard de Zyte está deprecado. Zyte remite a la librería `scrapy-deltafetch`, un spider middleware que ignora requests a páginas vistas en crawls anteriores del mismo spider. — [Zyte Support, Delta Fetch addon](https://support.zyte.com/support/solutions/articles/22000200411-delta-fetch-addon); [PyPI scrapy-deltafetch](https://pypi.org/project/scrapy-deltafetch)
- [TEO] El dupefilter de Scrapy deduplica **requests** y no items. Es un error común esperar deduplicación de items. Se sugiere `JOBDIR` para que el estado sobreviva a una caída. — [DEV Community](https://dev.to/ikram_khan/handling-duplicate-items-in-scrapy-stop-scraping-the-same-thing-twice-1bjo)
- [DOC] Spidermon (Zyte): monitores de recuento de items (ejemplo de Zyte: un spider que suele sacar 2,700 items y de repente saca 500), de cobertura por campo (ejemplo: presencia de imagen que cae de 60% a 30%) y de `finish_reason` (cierres anormales por timeout o ban). — [Zyte, Spidermon secret sauce](https://www.zyte.com/blog/spidermon-the-secret-sauce-to-our-data-quality-guarantee/); [Spidermon docs, getting started](https://spidermon.readthedocs.io/en/1.20.0/getting-started.html)
- [DOC] Zyte llama al "silent failure problem" el tipo de bug más caro en web scraping. — [Zyte, AI won't fix your data quality](https://www.zyte.com/blog/ai-wont-fix-your-data-quality/)
- [DOC] Los errores de validación de items **no** aparecen automáticamente en los resultados de los monitores; hay que crear un monitor que lea esas estadísticas. — [Zyte blog, Spidermon spidey-senses](https://www.zyte.com/blog/giving-spidey-senses-to-your-web-scraping-spiders-using-spidermon/)
- [TEO] Un patrón típico: caída del recuento con cero errores y salida limpia, normalmente por un cambio de selector en el que el contenedor exterior ya no coincide. Solo un monitor de recuento lo detecta. — [DEV Community/extractdata](https://dev.to/extractdata/why-your-scraper-breaks-without-warning-and-how-to-fix-that-1k9a)
- [TEO] Zyte publica guías de AUTOTHROTTLE para ajustar la velocidad sin ser bloqueado. — [DEV/extractdata, AutoThrottle](https://dev.to/extractdata/scrapy-autothrottle-how-to-tune-crawl-speed-without-getting-blocked-5bgd)

### Inferences
- [INF] Re-crawl completo porque el sitio se reconstruye a diario: el manual de Blender se regenera con Sphinx, así que las fechas `Last-Modified` del servidor probablemente cambian en cada build aunque el contenido no cambie. DeltaFetch, que se basa en URLs vistas, evitaría re-pedir, pero también evitaría detectar cambios reales. La solución robusta es **pedir siempre (o según sitemap/lastmod si existe), calcular un hash del texto extraído y normalizado, y escribir solo si el hash cambió**. Así se separa "rastrear" de "ingerir".
- [INF] "Páginas re-rastreadas rechazadas como duplicadas de sí mismas": señal de que la deduplicación compara el contenido nuevo contra el índice que ya contiene esa misma URL. La clave de deduplicación debería ser `canonical_url (+ versión)`. Si coincide la URL, es un **upsert/actualización**; si coincide el hash con una URL distinta, es un duplicado o un mirror. Solo debería rechazarse un near-duplicate de una URL **distinta** dentro de la misma versión.
- [INF] "Misma página bajo dos URLs": normalizar URLs (esquema, barra final, `index.html`, query params, fragmentos) y respetar `<link rel="canonical">` antes del dupefilter de Scrapy, o usar un `REQUEST_FINGERPRINTER` personalizado.
- [INF] Hay que añadir Spidermon (o un equivalente simple) con un recuento mínimo por sección del manual, para detectar la "deriva silenciosa de cobertura" cuando cambie la plantilla de Sphinx.

### Gaps
- No encontré documentación verificada sobre HTTPCACHE de Scrapy con ETag/Last-Modified (RFC2616Policy) en las búsquedas. Hay que revisar la documentación oficial de Scrapy.
- No encontré casos documentados de Zyte sobre calendarios infinitos o trampas de paginación aplicables al manual. Son riesgos teóricos para foros.

---

## 4. Deduplicación de contenido versionado y en mirrors (URLs canónicas, MinHash/SimHash, conservar variantes de versión)

### Takeaway
La evidencia de los grandes corpus (FineWeb, Dolma) apoya deduplicar **dentro** de un ámbito (snapshot o fuente) y no globalmente, y la evidencia de RAG (VersionRAG) apoya **conservar las variantes de versión con metadatos** en vez de descartarlas. Juntas contradicen la práctica de G7B de rechazar las versiones casi duplicadas del manual.

### Cited Findings
- [DOC] La sobre-deduplicación de clusters pequeños puede ser perjudicial; FineWeb solo deduplicó por snapshot. — [FineWeb paper](https://arxiv.org/pdf/2406.17557)
- [DOC] Dolma deduplica dentro de cada fuente pero no entre fuentes, con Bloom filters a nivel URL, documento y párrafo. — [Dolma paper](https://ar5iv.labs.arxiv.org/html/2402.00159)
- [DOC] RefinedWeb usó subcadena exacta + MinHash (~50% eliminado). — [RefinedWeb paper](https://ar5iv.labs.arxiv.org/html/2306.01116)
- [DOC] DCLM: los Bloom filters a nivel párrafo rinden de forma comparable a MinHash y escalan mejor. — [DCLM paper](https://arxiv.org/pdf/2406.11794)
- [DOC] En RAG, mezclar versiones sin metadatos causa respuestas erróneas; el filtrado o enrutado por versión sube la precisión del 58% al 90%. — [VersionRAG](https://arxiv.org/html/2510.08109)
- [DOC] El manual de Blender existe en muchas versiones e idiomas con URLs paralelas del tipo `docs.blender.org/manual/{lang}/{version}/...` (por ejemplo `en/4.0`, `en/5.1`, `ja/dev`, `id/3.6`), lo que genera de forma estructural casi duplicados entre versiones e idiomas. — [Blender Manual 4.0 copyright](https://docs.blender.org/manual/en/4.0/copyright.html); [Blender Manual 5.1](https://docs.blender.org/manual/en/5.1/copyright.html)

### Inferences
- [INF] Modelo recomendado para G7B: `doc_id = (lang, ruta_relativa)`, con una variante por `version`. Deduplicación exacta por hash dentro de (lang, versión). Near-duplicates (MinHash/SimHash) solo para detectar mirrors entre URLs distintas de la misma versión. Entre versiones, **guardar un diff o solo las versiones cuyo contenido cambió** (por hash), para ahorrar espacio en Atlas: si 4.4 y 4.5 son idénticas en una página, se guarda una sola variante con `versions: ["4.4","4.5"]`.
- [INF] Lo mismo con `dev` frente a la versión estable: tratar `dev` como no-canónica y no indexarla por defecto.

### Gaps
- No encontré un estudio específico sobre deduplicación de documentación versionada (más allá de VersionRAG) ni comparativas de SimHash frente a MinHash a escala pequeña.

---

## 5. Legal y ético: robots.txt (RFC 9309), IETF AI preferences / Cloudflare Content Signals, Art. 4 de la Directiva DSM, casos de EE. UU., copyright en RAG frente a entrenamiento, CC BY-SA, México. Qué está asentado y qué no en 2026

### Takeaway
Lo más asentado para G7B es contractual: el manual de Blender es CC BY-SA 4.0 (con excepciones para logos, código y scripts), así que usarlo en RAG exige atribución y, si se redistribuyen derivados, compartir igual. El scraping de datos públicos sin sesión iniciada ganó en tribunales de distrito de EE. UU. (Meta v. Bright Data, X v. Bright Data), pero no es precedente vinculante. Las señales de preferencia de IA (Content Signals, IETF aipref) **no son todavía estándares RFC**. En la UE, los opt-outs en lenguaje natural no se han aceptado como "legibles por máquina" (LAION en Hamburgo, 2025; Dinamarca, 2026).

### Cited Findings
- [DOC] Manual de Blender: salvo indicación contraria, el contenido está bajo CC BY-SA 4.0 Internacional "o cualquier versión posterior". Se excluyen logos, marcas, iconos, código fuente y scripts de Python. Se pide atribución al "Blender Documentation Team". — [Blender Manual, copyright (5.1)](https://docs.blender.org/manual/en/5.1/copyright.html); [4.0](https://docs.blender.org/manual/en/4.0/copyright.html)
- [DOC] Meta v. Bright Data (N.D. Cal., enero de 2024): el juez Chen concedió juicio sumario a Bright Data; los términos de Meta no prohíben el scraping de datos públicos sin sesión iniciada. Meta desistió en febrero de 2024. Los comentaristas dudan de su alcance porque depende de la redacción concreta de los términos. — [Farella Braun + Martel](https://www.fbm.com/post/102kqw7/); [Eric Goldman blog](https://blog.ericgoldman.org/?p=26009)
- [DOC] X Corp. v. Bright Data: el juez Alsup desestimó la demanda. Las reclamaciones estatales por scraping y venta de datos se consideraron desplazadas (preempted) por la Copyright Act. — [Social Media Today](https://www.socialmediatoday.com/news/x-formerly-twitter-loses-lawsuit-against-data-scrapers/715868/)
- [DOC] hiQ v. LinkedIn: el scraping en sí se consideró legal, pero la creación de cuentas falsas generó responsabilidad, y LinkedIn acabó ganando una resolución clave que le permitió bloquear a hiQ. (No verifiqué los términos del acuerdo final.) — [Farella Braun + Martel](https://www.fbm.com/post/102kqw7/); [Eric Goldman blog](https://blog.ericgoldman.org/?p=26009)
- [DOC] Thomson Reuters v. Ross (D. Del., feb. 2025): usar los headnotes de Westlaw para entrenar una herramienta **no generativa** de búsqueda legal que competía con el original **no** fue fair use; pesó el daño al mercado, incluido el mercado de licencias de datos de entrenamiento. Un reporte de septiembre de 2026 indica que el Tercer Circuito lo confirmó (fuentes anteriores lo daban como pendiente; hay que verificarlo en la opinión). — [Ropes & Gray](https://www.ropesgray.com/en/insights/alerts/2025/07/a-tale-of-three-cases-how-fair-use-is-playing-out-in-ai-copyright-lawsuits); [Nieman Lab (sep. 2026)](https://www.niemanlab.org/2026/09/federal-appeals-court-upholds-thomson-reuters-landmark-ai-copyright-win/); [ABA Business Law Today](https://www.americanbar.org/groups/business_law/resources/business-law-today/2026-september/thomson-reuters-v-ross-one-year-later/)
- [DOC] Bartz v. Anthropic y Kadrey v. Meta (N.D. Cal., junio de 2025): fair use para entrenar con libros adquiridos lícitamente (Bartz), pero no para copias de procedencia ilícita, lo que llevó a un acuerdo de hasta 1,500 millones de dólares. Kadrey es explícitamente estrecho. — [Ropes & Gray](https://www.ropesgray.com/en/insights/alerts/2025/07/a-tale-of-three-cases-how-fair-use-is-playing-out-in-ai-copyright-lawsuits); [IPWatchdog (dic. 2025)](https://ipwatchdog.com/2025/12/23/copyright-ai-collide-three-key-decisions-ai-training-copyrighted-content-2025/)
- [DOC] Kneschke v. LAION, OLG Hamburgo (10 dic. 2025, 5 U 104/24): confirmó que la creación del dataset estaba cubierta por la excepción TDM (Art. 4 DSM / § 44b UrhG) y por la de investigación científica (§ 60d, sin opt-out). Un opt-out en lenguaje natural no se consideró legible por máquina en 2021. Se admitió recurso ante el BGH, con vista listada para el 3 sep. 2026 (no confirmé el resultado). — [Bird & Bird](https://cm.twobirds.com/en/insights/2025/germany/higher-regional-court-hamburg-confirms-ai-training-was-permitted-(kneschke-v,-d-,-laion)); [Grünecker](https://grunecker.de/insights/ai-and-copyright-hamburg-court-of-appeal-rejects-appeal-in-laion-case/); [Morgan Lewis (jun. 2026)](https://www.morganlewis.com/pubs/2026/06/ai-and-copyright-judicial-landscape-in-germany)
- [DOC] Dinamarca (mayo de 2026, BoligPortal v. ReData, apelación): un opt-out TDM en lenguaje natural en un sitio web no cumplió el requisito de legibilidad por máquina; el tribunal citó LAION. Open Future señala que LAION deja sin resolver cómo hacer un opt-out válido. — [Morgan Lewis](https://www.morganlewis.com/pubs/2026/06/ai-and-copyright-judicial-landscape-in-germany); [Open Future](https://openfuture.eu/blog/laion-round-2-machine-readable-but-still-not-actionable/)
- [DOC] Cloudflare Content Signals Policy (sep. 2025): extiende robots.txt con `search`, `ai-input` y `ai-train` (yes/no). El robots.txt gestionado por Cloudflare cubre más de 3.8M dominios, con `search=yes` y `ai-train=no` por defecto y `ai-input` neutral. Se presentó como aporte al grupo IETF aipref, cuyos borradores siguen siendo Internet-Drafts y no RFC, y usan nombres de categorías distintos que pueden cambiar. — [Cloudflare blog](https://blog.cloudflare.com/content-signals-policy/); [Search Engine Land](https://searchengineland.com/cloudflare-content-signals-462538)

### Inferences
- [INF] G7B (educativo, RAG con atribución y enlace a la fuente, sin sesión iniciada ni evasión de bloqueos) se sitúa en el lado de bajo riesgo de todos estos casos. Los riesgos residuales son: (a) cumplir CC BY-SA mostrando la atribución y la licencia en cada respuesta que use el manual; (b) leer y respetar robots.txt **y** las líneas `Content-Signal` (un RAG encaja en `ai-input`); (c) el contenido comunitario (foros, YouTube, Stack Exchange) tiene licencias y términos propios: Stack Exchange es CC BY-SA, pero sus términos para uso por IA deberían verificarse aparte.
- [INF] Las traducciones al español de páginas CC BY-SA son obras derivadas: si G7B publica resúmenes o traducciones, deben ir bajo CC BY-SA.
- [INF] Qué está asentado y qué no: asentado, que el scraping de datos públicos sin sesión iniciada no infringe la CFAA (hiQ) y que hay que cumplir las licencias CC. Incierto, el fair use en entrenamiento (fallos divididos y estrechos), si los RAG que reproducen fragmentos sustituyen al original (Ross apunta a que la competencia directa pesa en contra) y el formato válido de opt-out en la UE.

### Gaps
- **México**: no encontré en esta sesión fuentes sobre la posición de la Ley Federal del Derecho de Autor respecto a la minería de datos o la IA. La LFDA no tiene, que yo sepa, una excepción TDM equivalente al Art. 4 DSM, pero no lo verifiqué. Hace falta una búsqueda específica (INDAUTOR, iniciativas de reforma 2024–2026).
- No verifiqué el texto de RFC 9309 ni el estado de ai.txt (Spawning) en esta sesión.
- No encontré análisis legales específicos sobre RAG frente a entrenamiento; la distinción sigue sin resolverse en las fuentes encontradas.

---

## 6. Coste y operación: trampas de los planes gratuitos (Zyte, GitHub Actions, MongoDB Atlas M0) y monitorización

### Takeaway
Los tres planes gratuitos tienen límites documentados que explican directamente los síntomas de G7B. Zyte gratis corta los jobs a **1 hora** y borra los datos a los **7 días**. GitHub Actions retrasa o **descarta** ejecuciones programadas en horas de alta carga (sobre todo en punto) y, según fuentes de terceros, desactiva los schedules tras 60 días sin actividad en el repo. Atlas Free limita a 100 ops/s, **3 índices de search/vector en total** y ~512 MB.

### Cited Findings
- [DOC] Scrapy Cloud gratis: 1 unidad con la mitad de recursos, jobs de **máximo 1 hora**, datos del job retenidos **7 días**, 1 crawl concurrente. Las unidades de pago cuestan 9 USD al mes, quitan el límite de duración y retienen 120 días. El post antiguo de Scrapy Cloud 2.0 decía 24 h (ya no vigente). — [Zyte docs, pricing](https://docs.zyte.com/scrapy-cloud/pricing.html); [Zyte Scrapy Cloud](https://www.zyte.com/scrapy-cloud/); [Capterra](https://www.capterra.com/p/180165/Zyte/pricing)
- [DOC] GitHub Actions: la documentación del evento `schedule` dice que las ejecuciones pueden retrasarse en momentos de alta carga, que el inicio de cada hora es un momento de alta carga y que algunos jobs en cola pueden descartarse si la carga es suficiente. — [GitHub community discussion](https://github.com/orgs/community/discussions/201738); [DEV, monitoring scheduled workflows](https://dev.to/krissv/monitoring-github-actions-scheduled-workflows-a-practical-guide-31h7)
- [DOC] Incidente de GitHub (enero de 2026): un patrón de carga causado por jobs programados saturó un recurso compartido y retrasó el arranque de Actions. — [GitHub Status](https://www.githubstatus.com/incidents/fw294tth5m8y)
- [DOC, terceros] Los schedules se desactivan en silencio en repos sin actividad durante 60 días (no verifiqué el texto oficial en esta sesión). Hay reportes comunitarios de retrasos de 8–14 h en repos nuevos. — [cronuru](https://cronuru.com/guides/github-actions-scheduled-workflows); [HackerNoon](https://hackernoon.com/your-github-actions-cron-job-can-disappear-without-failing); [GitHub discussion](https://github.com/orgs/community/discussions/201738)
- [DOC] MongoDB Atlas Free: 100 operaciones por segundo y un máximo de **3 índices** (search o vector, contados juntos). Vector Search está disponible en el tier gratuito. Para el almacenamiento se citan 512 MB (terceros) frente a 500 MB (foro); hay que verificarlo en la página de límites. — [MongoDB, free-shared limitations](https://mongodb.com/docs/atlas/reference/free-shared-limitations/); [Atlas Search limitations](https://docs.atlas.mongodb.com/atlas-search/limitations/); [Foro MongoDB](https://mongodb.com/community/forums/t/is-vector-search-feature-paid-or-free/267191)

### Inferences
- [INF] El límite de 1 h de Zyte hace inviable un crawl completo y lento del manual (miles de páginas × versiones × AUTOTHROTTLE). Otra razón para el modo incremental por hash y para dividir el crawl por sección o versión en varios jobs. Además, hay que exportar a Azure Blob (bronze) dentro del propio job: con 7 días de retención, no hay que depender de los items de Zyte como almacenamiento.
- [INF] GitHub Actions: programar el cron en un minuto no redondo (p. ej. `17 3 * * *`), hacer el pipeline idempotente para que un run perdido se recupere en el siguiente, añadir `workflow_dispatch`, y tener un "dead-man's switch" (alerta si no hubo ingesta en N horas) en vez de confiar en el schedule.
- [INF] Atlas Free: 512 MB se llenan rápido con embeddings (p. ej. 1024 dims × 4 bytes ≈ 4 KB por chunk más texto e índices, del orden de decenas de miles de chunks como máximo). Guardar en Atlas solo la capa gold (la última versión más las variantes que cambiaron) y dejar bronze/silver en Azure Blob. Con el límite de 3 índices, usar un solo índice vectorial con campos filtrables (versión, idioma, tipo) en lugar de uno por versión.

### Gaps
- No encontré postmortems publicados de proyectos pequeños que se quedaran sin espacio en Atlas M0. El cálculo de capacidad es una estimación propia.
- No verifiqué en la documentación oficial de GitHub la regla de los 60 días.
