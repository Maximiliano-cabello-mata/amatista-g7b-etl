# Crawling enfocado, crawling guiado por LLM, descubrimiento de fuentes y re-crawling incremental (para G7B)

Nota metodológica: arxiv.org no era accesible desde esta sesión (WebFetch falló por DNS/red); las cifras de papers de arXiv provienen de snippets de búsqueda, resúmenes de terceros (AlphaXiv, DeepAI, Emergent Mind) o versiones ACL/CEUR. Se marcan como "verificar en el PDF" donde corresponde. Etiquetas: **[PRÁCTICA]** = usado en sistemas reales con evidencia; **[TEORÍA]** = sólo papers/simulación; **[MIXTO]** = idea académica con implementación usable pero sin evidencia de adopción amplia.

## 1. Crawling enfocado clásico (Chakrabarti 1999, best-first, shark search, context graphs, RL)

### Takeaway
La idea clásica (clasificador de relevancia + frontera best-first) es sólida y sobrevive en herramientas reales (ACHE, BestFirst de crawl4ai, priorización en Scrapy), pero las variantes sofisticadas (context graphs, RL, ontologías) casi sólo se evalúan contra baselines débiles en papers; ninguna tiene adopción de producción documentada. Para G7B, "best-first con un scorer simple" es lo probado; RL es teoría.

### Cited Findings
- Chakrabarti, van den Berg y Dom (WWW'99 / Computer Networks vol. 31) introducen el focused crawler con un clasificador (Naive Bayes) y un "distiller" de hubs; el abstract afirma que el crawler enfocado adquiere páginas relevantes de forma sostenida mientras el crawler estándar "se pierde" rápidamente. **[TEORÍA → base de práctica]** — [IAS repository](https://repository.ias.ac.in/100130); [PDF WWW'99](https://www.math.unipd.it/~dulli/corso04/www1999f.pdf)
- Chakrabarti, Punera y Subramanyam (WWW 2002, "Accelerated focused crawling through online relevance feedback") definen harvest rate como la fracción de páginas relevantes recolectadas y reportan reducciones de la tasa de pérdida de 30–90% usando un "apprentice" que aprende de los enlaces. **[TEORÍA]** — [WWW2002](https://archives.iw3c2.org/www2002/CDROM/refereed/336.html)
- Definición estándar: harvest rate = páginas relevantes / páginas recuperadas; loss rate = 1 − harvest rate. — [Novak, survey SiKDD 2004](https://ailab.ijs.si/Dunja/SiKDD2004/Papers/BlazNovak-FocusedCrawling.pdf); otra revisión añade target recall, precisión y F1 — [SciELO survey 2022](https://scielo.br/j/babt/a/yG9Bw9htLXd554BfFcwwLCy/?lang=en)
- Shark Search extiende Fish Search refinando la priorización de la frontera; muchas variantes (incluida Shark Search) usan best-first como estrategia subyacente. **[TEORÍA; hoy integrado como heurística]** — [Gogar, CTU poster 2016](https://poster.fel.cvut.cz/poster2016/proceedings/Section_ICS/ICS_017_Gogar.pdf); [Novak](https://ailab.ijs.si/Dunja/SiKDD2004/Papers/BlazNovak-FocusedCrawling.pdf)
- Problema de evaluación: muchos autores sólo comparan contra best-first básico, lo que dificulta comparar papers; la variante ontológica de Shark Search mejoró harvest rate frente a keyword-match pero no se comparó con otros focused crawlers. — [Gogar](https://poster.fel.cvut.cz/poster2016/proceedings/Section_ICS/ICS_017_Gogar.pdf); [Novak](https://ailab.ijs.si/Dunja/SiKDD2004/Papers/BlazNovak-FocusedCrawling.pdf)
- TRES (Tree REinforcement Spider, Kontogiannis et al., arXiv 2112.07620, v4 mayo 2025): modela el crawling como MDP con "Tree-Frontier" (discretización por árbol de decisión de estados/acciones); el abstract afirma superar el estado del arte en harvest rate en al menos 58% y reducir en órdenes de magnitud las acciones evaluadas por paso. Código en github.com/ddaedalus/tres. **[TEORÍA]** — [arXiv 2112.07620](https://arxiv.org/abs/2112.07620v2); [GitHub TRES](https://github.com/ddaedalus/tres)
- Cifras de TRES según un resumen de terceros (no verificadas en PDF): harvest rate 97,43% (Sports), 98,90% (Food), 87,30% (Hardware) frente a ACHE 54,43%, 57,07%, 42,95%. — [AlphaXiv overview](https://www.alphaxiv.org/overview/2112.07620)
- ACHE (NYU VIDA, programa DARPA Memex): focused crawler open-source con clasificador de páginas entrenado en el Domain Discovery Tool (DDT) y SeedFinder, que usa buscadores comerciales para descubrir semillas. Es el ejemplo más cercano a "focused crawler clásico en uso real", pero la página del proyecto está marcada "legacy" y no se encontraron despliegues documentados recientes. **[MIXTO: usado en Memex, hoy poco mantenido]** — [ACHE docs](https://ache.readthedocs.io/en/0.15.0/tutorial-focused-crawl.html); [VIDA Memex](https://vida.engineering.nyu.edu/research/memex); [GitHub VIDA-NYU/ache](https://github.com/VIDA-NYU/ache/blob/master/docs/tutorial-focused-crawl.rst)
- Una guía de Memex Explorer advierte que relanzar ACHE borra el crawl previo y que Nutch es "mucho más fácil" de poner en marcha (fricción operacional). — [Memex Explorer Crawler Guide](https://memex-explorer.readthedocs.io/en/stable/crawler_guide.html)
- Fraunhofer describe un focused crawler sobre Apache StormCrawler que consulta LLMs para estimar relevancia bajo demanda (análisis de tendencias industriales) — ejemplo de práctica institucional, no masiva. **[MIXTO]** — [Fraunhofer publica](https://publica-rest.fraunhofer.de/server/api/core/bitstreams/2f9de95a-dce6-4a61-a3a2-223710f45084/content)

### Inferences
- Lo que sobrevive en producción es el patrón "frontera con prioridad + scorer de relevancia (keywords/clasificador barato) + límite de profundidad". Scrapy ya admite `priority` en `Request`, así que G7B puede implementar best-first sin dependencias nuevas.
- Context graphs (Diligenti et al. 2000) e "intelligent crawling" (Aggarwal et al. 2001) no aparecieron en ninguna herramienta actual encontrada; tratarlos como teoría.
- RL (TRES) requiere entrenamiento y muchas iteraciones; inviable con jobs de 1 hora en Zyte free.

### Gaps
- No obtuve las tablas numéricas originales de Chakrabarti 1999 ni de context graphs/intelligent crawling (sin acceso a PDFs).
- No hay evidencia encontrada de que buscadores comerciales usen RL para frontera de forma pública.

## 2. Enfoques modernos: crawlers guiados por LLM, herramientas "LLM-ready" y clasificadores de calidad

### Takeaway
Hay resultados medidos sólidos pero en simulación sobre grafos estáticos (Craw4LLM: 21% de páginas para igual rendimiento; Neural Prioritisation: hasta +149% harvest rate en fases tempranas). En la práctica, lo adoptado masivamente son herramientas de extracción/conversión a Markdown (crawl4ai, Firecrawl, Jina Reader) y clasificadores fastText baratos para filtrar; la priorización de frontera con LLM en crawls reales no tiene adopción documentada.

### Cited Findings
- Craw4LLM (Yu, Liu, Xiong; Tsinghua/CMU; ACL Findings 2025): prioriza URLs por "influencia en preentrenamiento" (puntuación del pipeline de filtrado tipo DCLM) en vez de conectividad del grafo. Con el mismo rendimiento downstream, rastrea sólo ~21% de las páginas del baseline; alcanza >95% del rendimiento de un oráculo rastreando 2,2% de los datos; experimentos en ClueWeb22-A (900M páginas en inglés). Es simulación sobre un grafo estático, no crawling en vivo. **[TEORÍA (simulación)]** — [arXiv 2502.13347](https://arxiv.org/html/2502.13347v1); [ACL Anthology](https://preview.aclanthology.org/setup/2025.findings-acl.712)
- Neural Prioritisation for Web Crawling (Pezzuti, MacAvaney, Tonellotto; ICTIR '25): políticas QFirst/QMin que usan un estimador de calidad basado en LLM (heredando la puntuación de la página padre); en ClueWeb22-B inglés con Researchy Questions mejoran significativamente harvest rate, maxNDCG y efectividad de búsqueda en las etapas tempranas; hasta +149% de HR sobre BFS en consultas en lenguaje natural y hasta +20% con consultas MS MARCO de keywords. QOracle (conoce el texto antes de descargar) es la cota superior. **[TEORÍA (simulación)]** — [arXiv 2506.16146](https://arxiv.org/abs/2506.16146v1); [CEUR-WS Vol-4026](https://ceur-ws.org/Vol-4026/paper3.pdf); [Glasgow eprints](https://eprints.gla.ac.uk/359292)
- WebWalker / WebWalkerQA (Alibaba, ACL 2025): benchmark de 680 consultas sobre >1.373 páginas en 4 escenarios para LLMs que navegan subpáginas de un sitio con sólo acciones "click"; framework multi-agente explore-critic comparado con ReAct y Reflexion. Muestra que el recorrido de sitios por LLM es un problema abierto. **[TEORÍA/benchmark]** — [HF Papers 2501.07572](https://huggingface.co/papers/2501.07572); [ACL Anthology](https://preview.aclanthology.org/setup/2025.acl-long.508)
- crawl4ai: `BestFirstCrawlingStrategy` prioriza URLs con scorers (p. ej. `KeywordRelevanceScorer`) y `max_depth`; `AdaptiveCrawler.digest(start_url, query)` decide cuándo parar con un sistema de tres capas (coverage, consistency, saturation). Licencia Apache 2.0, sin créditos; el coste es infraestructura (servidor, proxies, claves LLM). **[PRÁCTICA como herramienta; el "adaptive" sin benchmarks independientes encontrados]** — [crawl4ai Deep Crawling](https://docs.crawl4ai.com/core/deep-crawling/); [crawl4ai Adaptive Crawling](https://docs.crawl4ai.com/core/adaptive-crawling/); [API adaptive-crawler](https://docs.crawl4ai.com/api/adaptive-crawler/); [Firecrawl vs Crawl4AI (vendor)](https://www.firecrawl.dev/alternatives/firecrawl-vs-crawl4ai)
- Adopción (estrellas GitHub, fuentes contradictorias): crawl4ai ~50k según una comparativa, >62k según un artículo de 2026, ~87,1k según una página de noviembre 2026; Firecrawl ~20k en una comparativa (sin cifra fiable actual). Firecrawl es AGPL-3.0. — [toolhalla](https://toolhalla.ai/compare/crawl4ai-vs-firecrawl); [aitoolsatlas](https://aitoolsatlas.ai/compare/crawl4ai-vs-firecrawl); [capsolver blog](https://capsolver-website-nuxt.pages.dev/blog/AI/crawl4ai-vs-firecrawl)
- Firecrawl free tier: contradictorio — 500 créditos únicos vs 1.000 créditos/mes según la fuente; planes pagos desde ~$16–19/mes. — [scrape.do](https://scrape.do/blog/firecrawl-alternatives); [Firecrawl blog](https://www.firecrawl.dev/blog/bing-search-api-alternatives)
- Benchmark independiente-ish de 1.000 URLs entre Crawl4AI, Firecrawl y Spider existe pero es de un vendor (Spider). — [spider.cloud](https://spider.cloud/blog/firecrawl-vs-crawl4ai-vs-spider-honest-benchmark/)
- Clasificadores de calidad para datos de preentrenamiento: DCLM encontró que un clasificador fastText era el mejor filtro basado en modelo entre los probados; DCLM-Baseline logra 64% MMLU con 40% menos cómputo que el SOTA previo de datos abiertos. **[PRÁCTICA en pipelines de datos (filtrado post-crawl, no priorización de frontera)]** — [Resumen DCLM](https://liner.com/review/datacomplm-in-search-next-generation-training-sets-for-language-models); [NeurIPS 2024 DCLM supplement](https://proceedings.nips.cc/paper_files/paper/2024/file/370df50ccfdf8bde18f8f9c2d9151bda-Supplemental-Datasets_and_Benchmarks_Track.pdf)
- Coste: Ultra-FineWeb estima ~6.000 horas H100 para clasificar 15T tokens con un clasificador LLM, frente a 80 CPUs × 1.000 h con fastText; Ultra-FineWeb (fastText) promedia 45,891 vs FineWeb 42,278 vs FineWeb-Edu 44,560. — [arXiv 2505.05427 vía AlphaXiv](https://alphaxiv.org/overview/2505.05427v1)
- Contrapunto: FineWeb-Edu y DCLM eliminan ~90% de los tokens con filtrado agresivo, descartando datos útiles. — [arXiv 2502.10361 (NVIDIA)](https://arxiv.org/html/2502.10361v1)

### Inferences
- Para G7B, el análogo barato de Craw4LLM/Neural Prioritisation es: puntuar cada página descargada con un clasificador barato (keywords Blender ES/EN + fastText o embeddings pequeños) y heredar esa puntuación como `priority` a sus enlaces salientes (esto es literalmente QFirst). Usar un LLM por página es caro; usarlo sólo para revisar una muestra o para etiquetar datos de entrenamiento del clasificador es lo viable.
- Las ganancias medidas son en "etapas tempranas" del crawl — exactamente el régimen de G7B (presupuesto de pocas miles de páginas por job de 1 h).
- Los "deep research agents" (navegación agentiva) son útiles para descubrir fuentes una sola vez de forma manual/semiautomática, no como crawler recurrente: coste por consulta y no determinismo.

### Gaps
- No encontré benchmarks independientes de harvest rate de crawl4ai `BestFirst`/`Adaptive`, Firecrawl `/crawl`, browser-use, GPT-crawler o Jina Reader; las comparativas existentes son de vendors.
- No se obtuvieron las precisiones numéricas de WebWalker.
- Free tier actual de Jina Reader no verificado.

## 3. Descubrimiento de fuentes (search APIs, Common Crawl index, grafos de enlaces, Wikipedia/Wikidata, awesome-lists)

### Takeaway
El mercado de APIs de búsqueda gratuitas colapsó en 2025–2026 (Bing retirado, Brave sin tier gratis, Google CSE cerrado a nuevos), así que el descubrimiento barato y fiable hoy pasa por el índice columnar de Common Crawl (Parquet consultable con DuckDB), extracción de enlaces salientes de fuentes ya conocidas y listas curadas; las APIs de búsqueda quedan como pequeñas cuotas de créditos.

### Cited Findings
- Microsoft retiró las Bing Search APIs el 11-ago-2025 (claves devuelven HTTP 410, sin altas nuevas); reemplazo "Grounding with Bing" sólo dentro de Azure y más caro. **[hecho]** — [cloro.dev](https://cloro.dev/blog/bing-search-api-key/); [dev.to](https://dev.to/tonywangca/best-bing-search-api-alternatives-in-2026-after-the-retirement-kdi)
- Brave eliminó su tier gratuito (febrero 2026 según Implicator/Parallel; otras fuentes dicen finales de 2025); ahora da $5/mes de crédito (~1.000 consultas) que requiere atribución. — [Implicator](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/); [Parallel](https://parallel.ai/articles/best-free-web-search-api.md)
- Google Custom Search JSON API cerrada a nuevos clientes; los existentes tienen hasta el 1-ene-2027. — [Parallel, comparativa Bing](https://parallel.ai/articles/bing-api-comparison)
- Otras cuotas gratis citadas (fuentes de vendors, cambian a menudo): Firecrawl 1.000 créditos/mes, Tavily 1.000 créditos/mes, Exa ~$10 de crédito inicial. — [Firecrawl blog](https://www.firecrawl.dev/blog/best-web-search-apis); [Parallel](https://parallel.ai/ai/articles/best-free-web-search-api)
- Common Crawl URL Index (antes "Columnar Index"): índice en Apache Parquet de URLs y registros WARC en `s3://commoncrawl/cc-index/table/cc-main/warc/`; consultable con Athena (us-east-1) o DuckDB por rangos HTTP. No hay columna de tema: se filtra por host/TLD, idioma de contenido y path de URL. El bucket no permite listado anónimo, así que con DuckDB hay que listar los .parquet explícitamente. **[PRÁCTICA]** — [Common Crawl blog](https://blog.commoncrawl.org/blog/the-columnar-index-is-now-the-url-index); [cc-index-table](https://github.com/commoncrawl/cc-index-table); [ccrawl-cli guía](https://ccrawl-cli.pages.dev/guides/columnar-index/); [MotherDuck: 100B filas](https://motherduck.com/blog/querying-the-entire-internet-100-billion-rows-with-motherduck/)
- Los ejemplos oficiales incluyen encontrar dominios multilingües, homepages de lenguas de pocos recursos y dominios de un TLD concreto (patrones reutilizables: p. ej. `content_languages` = spa y `url_path` con "blender"). — [skeptric: CC Index Athena](https://www.skeptric.com/common-crawl-index-athena); [cc-index-table](https://github.com/commoncrawl/cc-index-table)
- ACHE SeedFinder: genera semillas automáticamente consultando buscadores comerciales (patrón histórico de "buscar antes de rastrear"). — [ACHE docs](https://ache.readthedocs.io/en/0.14.0/tutorial-focused-crawl.html)
- Common Crawl usa muestras de sitemaps como fuente de URLs semilla (p. ej. 160M URLs extraídas de sitemaps de 25M hosts en 2017). — [Common Crawl, April 2017](https://commoncrawl.org/blog/april-2017-crawl-archive-now-available)

### Inferences
- Fuente más barata y fiable para G7B: consulta DuckDB mensual en GitHub Actions al URL index (filtrando idioma español + términos "blender", "render", "cycles", "eevee", "geometry nodes" en URL/host), agregando por dominio para obtener una lista de dominios candidatos; luego validarlos con unos pocos fetches. Coste: cero dinero, ancho de banda moderado (sólo columnas necesarias).
- Enlaces salientes de fuentes ya rastreadas (Discourse, manual, RSS) son el "grafo de enlaces" gratuito: contar dominios externos citados repetidamente es un descubridor de fuentes de nicho con buena precisión (inferencia, no medido).
- Wikidata/Wikipedia external links y awesome-lists de GitHub (p. ej. listas "awesome-blender") son baratos vía API pública; no encontré estudios de su efectividad: tratarlos como heurística práctica sin evaluación.

### Gaps
- No busqué/verifiqué específicamente la API de Wikidata (P856 "official website") ni la existencia/estado de repos awesome-blender concretos.
- Sin datos medidos sobre la calidad de dominios descubiertos vía CC index para un tema de nicho.

## 4. Crawling incremental y políticas de revisita

### Takeaway
Lo probado en práctica es simple: peticiones condicionales (ETag/If-None-Match, Last-Modified/If-Modified-Since), sitemaps con lastmod, feeds RSS, deduplicación por hash de contenido y alargar el intervalo de revisita cuando no hay cambios. La teoría de Cho & Garcia-Molina muestra que la intuición "revisitar más lo que más cambia" puede ser peor que revisitar uniformemente. Cuando un sitio regenera páginas a diario (validadores HTTP que cambian en cada deploy), hay que comparar un hash del contenido extraído, no las cabeceras.

### Cited Findings
- Cho & Garcia-Molina (SIGMOD 2000): freshness = fracción de la copia local actualizada; algunas políticas intuitivas rinden peor que la ingenua; en freshness promedio la política uniforme supera a la proporcional tanto en simulación como en crawl real; validación con 270 sitios durante 4 meses. **[TEORÍA influyente]** — [Paper (KTH copy)](https://www.kth.se/social/files/554f1d5bf27654514fd00393/synchronizing-a-database-to-improve-freshness.pdf); [Wikipedia: Web crawler](https://en.wikipedia.org/wiki/Web_crawler)
- Trabajo posterior (Azar et al.) muestra que la política óptima no es ni uniforme ni proporcional. — [Horvitz et al. PNAS](https://www.erichorvitz.com/Crawl_1801519115.full.pdf)
- Google documenta (dic. 2024) soporte de caché HTTP en sus crawlers vía ETag/If-None-Match y Last-Modified/If-Modified-Since, y prefiere ETag por ser menos propenso a errores de formato de fecha. **[PRÁCTICA]** — [Google Search Central blog](https://developers.google.com/search/blog/2024/12/crawling-december-caching?hl=hi); [SEJ](https://www.searchenginejournal.com/googles-updated-crawler-guidance-recommends-etags/534936/)
- Riesgo real: cada deploy puede resetear los validadores de caché de todo el sitio (ETag/Last-Modified nuevos sin cambio de contenido). — [dev.to: "Your last deploy reset every cache validator"](https://dev.to/jangwook_kim_e31e7291ad98/your-last-deploy-reset-every-cache-validator-on-the-site-4dd3)
- Heurística en lista de Common Crawl: si la revisita da duplicado (mismo contenido o 304), se incrementa el intervalo de esa URL (no confirmado como política oficial actual). **[PRÁCTICA probable]** — [Common Crawl Google Group](https://groups.google.com/g/common-crawl/c/M7lQfMECffA)
- Funnelback (motor comercial) tiene una política de revisita que omite URLs sin cambios en las últimas 5 descargas. **[PRÁCTICA]** — [Funnelback RevisitPolicy](https://docs.funnelback.com/administer/reference-documents/collection-options/crawler.classes.RevisitPolicy.html)
- scrapy-deltafetch (último v2.1.0) evita re-procesar requests que ya produjeron items; en Scrapy Cloud se activa con los addons DeltaFetch + DotScrapy Persistence. **[PRÁCTICA, mantenimiento incierto]** — [PyPI scrapy-deltafetch](https://pypi.org/project/scrapy-deltafetch); [Zyte blog tips 2016](https://www.zyte.com/blog/scrapy-tips-from-the-pros-july-2016/)

### Inferences
- Con retención de 7 días en Zyte free, el estado incremental (hashes, ETags, fechas lastmod) no debe vivir en `.scrapy` de Zyte sino en el repositorio/artefactos de GitHub Actions (p. ej. un JSON/SQLite versionado).
- Para Discourse: usar `/latest.json` y `bumped_at`; para Sphinx: comparar hash de objects.inv/páginas; para RSS: la fuente ya es incremental. WebSub no verificado para estos sitios.
- deltafetch sólo sirve para "no volver a ver lo ya visto", no para detectar actualizaciones; para re-crawl de contenido que cambia, combinar condicional HTTP + hash de texto extraído + intervalo adaptativo (duplicar al no cambiar, reducir al cambiar).

### Gaps
- No encontré documentación oficial actual de CCBot sobre peticiones condicionales, ni de `AdaptiveFetchSchedule` de Nutch (existe en Nutch, pero no lo verifiqué en esta sesión).
- No verifiqué soporte de WebSub en Blender Artists/devtalk/YouTube para este caso.

## 5. Frameworks y herramientas: adopción real y trade-offs con presupuesto cero

### Takeaway
Nutch y StormCrawler son la práctica a escala (Common Crawl usa Nutch para el crawl principal y StormCrawler para noticias) pero exigen infraestructura Hadoop/Storm, sobredimensionada para G7B. Para un proyecto diminuto en Zyte free + GitHub Actions, Scrapy con prioridad best-first y estado externo es lo más adecuado; crawl4ai es una alternativa libre (Apache 2.0) con best-first integrado si se ejecuta en Actions; Firecrawl/Zyte API son de pago por uso con cuotas pequeñas.

### Cited Findings
- Common Crawl adoptó Nutch para su crawl a gran escala en febrero de 2014; Nutch es proyecto top-level de Apache desde abril de 2010; hay un fork de Nutch de Common Crawl. **[PRÁCTICA]** — [Wikipedia: Apache Nutch](https://en.wikipedia.org/wiki/Apache_Nutch); [GitHub commoncrawl/nutch](https://github.com/commoncrawl/nutch)
- Common Crawl usa StormCrawler para su dataset de noticias (WARC). StormCrawler pasó por la incubadora de Apache; una fuente secundaria afirma que es top-level desde el 3-jun-2025 (no verificado en ASF). Un benchmark de 2017 lo encontró 60% más eficiente que Nutch (único y antiguo). **[PRÁCTICA]** — [Wikipedia: StormCrawler](https://en.wikipedia.org/wiki/StormCrawler); [Apache Incubator](https://incubator.apache.org/clutch/stormcrawler.html); [DZone 2017](https://dzone.com/articles/the-battle-of-the-crawlers-apache-nutch-vs-stormcr)
- Zyte Scrapy Cloud free: una unidad de bajos recursos (mitad de una unidad pagada); fuentes secundarias: 1 h por job, 1 crawl concurrente, 7 días de retención, sin scheduling en free (este último punto viene de una página de un competidor); unidades pagadas ~$9/mes. — [Zyte Scrapy Cloud](https://www.zyte.com/scrapy-cloud/); [Scrapy deploy](https://www.scrapy.org/deploy); [Apify comparativa (competidor)](https://apify.com/alternatives/zyte-alternative); [Prospeo](https://prospeo.io/s/scrapy-pricing-reviews-pros-and-cons)
- Crawl4AI: Apache 2.0, sin créditos, coste = infraestructura; cloud API en beta cerrada. Firecrawl: AGPL-3.0, cuota gratis pequeña. — [Firecrawl vs Crawl4AI](https://www.firecrawl.dev/alternatives/firecrawl-vs-crawl4ai); [scrappey](https://scrappey.com/qa/web-scraping-apis/crawl4ai-vs-firecrawl)
- ACHE es más difícil de operar que Nutch según Memex Explorer. — [Memex Explorer](https://memex-explorer.readthedocs.io/en/stable/crawler_guide.html)

### Inferences
- scrapy-frontera: sólo encontré menciones en boletines antiguos de Zyte; tratarlo como inactivo/no recomendado (verificar en GitHub). Una frontera ligera en SQLite/JSON gestionada por el propio spider es más simple.
- Heritrix (Internet Archive) y Crawlee (Apify, JS/Python) no se investigaron a fondo en esta sesión; Heritrix es práctica en archivos web, Crawlee es práctica en scraping comercial, pero ninguno aporta priorización temática superior a Scrapy.
- Estrategia sugerida: Zyte para los spiders "fijos" (manual, RSS, Discourse) dentro de 1 h; GitHub Actions (6 h por job, gratis en repos públicos — dato a verificar) para el crawler de descubrimiento best-first y la consulta DuckDB al CC index.

### Gaps
- No verifiqué estado de mantenimiento de scrapy-frontera ni de scrapy-deltafetch en GitHub.
- No verifiqué precios actuales de Zyte API automatic extraction ni límites exactos de GitHub Actions.
- Sin datos de adopción de browser-use / GPT-crawler para crawling (más orientados a agentes/ingesta RAG).

## 6. Evaluación: cómo miden el éxito los focused crawlers y cómo podría medirlo G7B

### Takeaway
La métrica dominante es harvest rate (relevantes/descargadas), complementada por target recall (cobertura de un conjunto objetivo conocido), precisión/F1 y, en trabajos recientes, métricas downstream (nDCG de búsqueda, rendimiento del modelo). G7B puede medir harvest rate con un juez barato sobre muestras y recall contra una lista de "páginas de oro" curada a mano.

### Cited Findings
- Harvest rate y loss rate como métricas estándar. — [Novak](https://ailab.ijs.si/Dunja/SiKDD2004/Papers/BlazNovak-FocusedCrawling.pdf)
- Target recall, precisión y F1 como métricas complementarias. — [SciELO survey](https://scielo.br/j/babt/a/yG9Bw9htLXd554BfFcwwLCy/?lang=en)
- TRES define harvest rate como porcentaje de páginas relevantes recuperadas. — [DeepAI TRES](https://api.deepai.org/publication/tree-based-focused-web-crawling-with-reinforcement-learning)
- Neural Prioritisation mide harvest rate, maxNDCG y efectividad de búsqueda a lo largo del crawl (curvas por etapa). — [arXiv 2506.16146](https://arxiv.org/abs/2506.16146v1)
- Craw4LLM mide rendimiento downstream de un LLM preentrenado con los datos rastreados frente a un oráculo y a baselines con 1×/2×/4× datos. — [arXiv 2502.13347](https://arxiv.org/html/2502.13347v1)
- Comparaciones contra baselines débiles (sólo best-first básico) son un problema recurrente de la literatura. — [Gogar](https://poster.fel.cvut.cz/poster2016/proceedings/Section_ICS/ICS_017_Gogar.pdf)

### Inferences
- Protocolo mínimo para G7B: (1) lista de oro de ~50–100 URLs de nicho conocidas (pipelines, optimización en PCs modestos, técnicas no documentadas); (2) por job, registrar páginas descargadas, puntuación del scorer y dominio; (3) etiquetar a mano o con un LLM barato una muestra aleatoria de ~50 páginas → harvest rate; (4) recall = fracción de la lista de oro alcanzada; (5) "novedad" = páginas relevantes de dominios no vistos antes; (6) comparar contra baseline BFS con el mismo presupuesto de páginas (curva harvest vs páginas, como en Neural Prioritisation).

### Gaps
- No existe benchmark público de focused crawling para dominios de software creativo/Blender o en español.
