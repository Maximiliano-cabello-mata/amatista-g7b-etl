# El nicho de G7B: fuentes, APIs, límites de las arañas y metodología (17 de noviembre de 2026)

**Para qué es este documento.** Se escribe porque el proyecto avanzaba sin un mapa del nicho. Junta tres cosas: qué hacen proyectos parecidos, qué fuentes y APIs gratuitas existen para cada pregunta del plan ([PLAN.md](../PLAN.md), sección 3), y qué metodologías ya establecidas aplican a G7B. La idea es dejar de inventar camino donde ya hay uno probado.

**Cómo leerlo.** Lo marcado como *verificado* se comprobó en documentación oficial o en vivo. Lo marcado como *por verificar* viene de fuentes secundarias o no se pudo probar desde la sesión. Las fuentes están al final.

---

## 1. Diagnóstico en una página

El análisis del lago del 17 de noviembre (sección 7) muestra que G7B junta lo fácil de juntar, no lo que más necesita:

| Pregunta del plan | Qué hay hoy | Qué tan bien la responde |
|---|---|---|
| **P1** Ajustes según el equipo | 133 documentos, pero solo 49 hablan de rendimiento o hardware. 18 mediciones de la sonda tomadas en servidores de GitHub | **Mal.** Ninguna medición viene de una computadora de estudiante |
| **P2** Qué versión conviene en cada equipo | 24 páginas del manual sobre solución de problemas por marca de tarjeta | Regular |
| **P3** Qué tan común es cada equipo | Nada | **Nada** |
| **P4** Equivalencias Maya / 3ds Max | 1 página útil (el mapa de teclas compatible con la industria) | **Casi nada** |
| **P5** Técnicas publicadas por la industria | 2 artículos de arXiv y algunas páginas de materiales | Débil |
| **P6** Cómo se hace X en la versión Y | 851 documentos del manual (642 páginas distintas), todos en inglés | **Bien**, como referencia general |
| **P7** Dónde se atoran los estudiantes | Nada | **Nada** |

**La conclusión.** Lo que distingue a Amatista (recomendar según la computadora del estudiante, equivalencias desde Maya y 3ds Max, y saber dónde se atoran) depende de **datos que nadie publica para nuestra población**. Ninguna araña los va a encontrar: hay que **producirlos**, con telemetría y mediciones con consentimiento, o **cruzar fuentes de población** como INEGI. Las arañas sirven para P5 y P6, y como señal de tendencia.

---

## 2. Qué tipo de proyecto es G7B (y quién ya hizo algo parecido)

G7B junta tres tipos de sistema que ya tienen nombre y literatura. Ninguno es raro; lo nuevo es combinarlos para equipos modestos.

| Lo que hace G7B | Nombre establecido | Referentes | Qué tomar de ellos |
|---|---|---|---|
| Medir el rendimiento de Blender en muchos equipos y recomendar ajustes | **Benchmarking colaborativo** (*crowdsourced benchmarking*) | [Blender Open Data](https://opendata.blender.org/about/), con resultados voluntarios y una copia diaria de todo el conjunto. [OpenBenchmarking.org / Phoronix Test Suite](https://openbenchmarking.org/test/pts/blender-4.0.0), con resultados públicos y siempre voluntarios | Medir con un cliente estándar que el usuario ejecuta en su propio equipo, con escenas fijas y publicación voluntaria. **No** medir en servidores |
| Registrar qué hace el estudiante en las prácticas | **Analítica del aprendizaje** (*learning analytics*), estándar **xAPI** | Wu, Guo y Zhu (2020) recogieron datos de un curso de diseño 3D con xAPI ([ECNU](https://pure.ecnu.edu.cn/en/publications/design-and-implementation-of-data-collection-mechanism-for-3d-des/)). Onshape exporta cada acción de un estudiante en CAD para investigación ([Onshape](https://onshape.com/en/blog/why-engineering-collaboration-starts-in-the-classroom)). [xAPI Made Easy](https://www.academia.edu/112203333/xAPI_Made_Easy_A_Learning_Analytics_Infrastructure_for_Interdisciplinary_Projects) | Registrar cada evento como «actor, verbo, objeto» (xAPI) para que la telemetría de P7 sea comparable con otras investigaciones y exportable |
| Juntar documentos, filtrarlos y servirlos a una IA | **Curación de datos con modelos** y **RAG** | FineWeb-Edu: un LLM calificó 460 000 páginas y con eso se entrenó un clasificador pequeño que reemplaza las reglas ([clasificador](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier), [artículo NeurIPS 2024](https://proceedings.nips.cc/paper_files/paper/2024/file/370df50ccfdf8bde18f8f9c2d9151bda-Paper-Datasets_and_Benchmarks_Track.pdf)). [propella-1](https://arxiv.org/html/2602.12414v2) etiqueta 18 propiedades en vez de un solo puntaje | Pasar del filtro por palabras clave (la taxonomía P1–P6) a etiquetas hechas por un modelo y validadas a mano |
| Construir y mejorar las prácticas con datos de uso | **Investigación basada en diseño** (*Design-Based Research*, DBR) | Ciclos de análisis, diseño y evaluación ([Wikipedia](https://Www.Wikipedia.org/wiki/Design-based_research), [Advances in DBR](https://journals.sfu.ca/flr/index.php/journal/article/download/114/212?inline=1), revisión 2019–2023 en [AJET](https://ajet.org.au/index.php/AJET/article/download/10380/2201/35549)) | Es la metodología que da forma académica a la estadía: cada práctica es un prototipo, se mide, se ajusta y se documenta el ciclo |
| Lago bronce → plata → oro con contratos | **Arquitectura medallion** y **contratos de datos** | Ya está en el proyecto (ver la auditoría del 15 de noviembre) | Sin cambios. Esta parte sí sigue la práctica de la industria |

**El contexto de la población** (México, verificado en [INEGI, ENDUTIH 2024](https://inegi.org.mx/contenidos/programas/endutih/2024/doc/presentacion_endutih2024.pdf)): **43,9 % de los hogares tiene computadora**, y de esos el **77,4 % tiene laptop** y solo el 27,0 % de escritorio. El «peor caso» de Amatista es una laptop con gráficos integrados, y es lo que menos aparece en Blender Open Data, donde dominan Ryzen 9 y RTX 3080.

En Latinoamérica la literatura sobre Blender en el aula con equipos de bajos recursos es escasa: hay artículos de opinión y estudios generales de brecha digital ([Correo del Sur](https://correodelsur.com/opinion/20260310/innovacion-en-la-ensenanza-stem-en-bolivia-blender-como-herramienta-cognitiva-para-el-aprendizaje-de-matematicas-y-fisica.html), [Ciencia Latina](https://ciencialatina.org/index.php/cienciala/article/download/15638/22292), [BID](https://www.iadb.org/es/blog/educacion/maestros-y-libros-para-los-ricos-robots-y-pantallas-para-los-pobres-0)). **Es un hueco real**: lo que G7B mida con estudiantes puede ser una contribución original.

---

## 3. Fuentes y APIs por pregunta

Veredictos: **Usar**, **Usar con cuidado** y **No conviene**.

### P1 y P2: rendimiento y versión según el equipo

| Fuente | Qué da | Acceso y límites | Veredicto |
|---|---|---|---|
| **Blender Open Data, copia diaria completa** | Todas las mediciones públicas de Blender Benchmark, en JSONL | Gratis. Hay una copia diaria de todo el conjunto en [opendata.blender.org/download](https://opendata.blender.org/download/). Hay que revisar la licencia en esa página antes de redistribuir | **Usar, y ya.** Hoy G7B tiene una sola semana de marzo de 2022 con Blender 3.0.1. Con la copia completa se puede filtrar a gráficos integrados, gama baja y versiones 4.x y 5.x |
| **OpenBenchmarking.org (`pts/blender`)** | Resultados públicos por CPU y GPU, escenas BMW27, Classroom y otras | Gratis, resultados voluntarios. No encontré documentación de API (*por verificar*); las páginas de resultados son públicas | Usar con cuidado: como segunda fuente para cruzar Blender Open Data |
| **Gestor de errores de Blender** (projects.blender.org, Gitea) | Cada reporte trae el sistema operativo, la **tarjeta gráfica**, la versión y lo que falló | Gitea publica una API REST `/api/v1/repos/blender/blender/issues`. **No se pudo probar**: el proxy de esta sesión bloquea el sitio (*por verificar* desde GitHub Actions) | **Usar.** Es la mejor fuente para P2 («la versión X falla con la tarjeta Y»). Con IA se extrae una tabla de versión, GPU, síntoma y solución |
| Requisitos oficiales y notas de compatibilidad de cada versión | OpenGL o Vulkan mínimos, GPUs que dejan de funcionar | Páginas públicas de blender.org y developer.blender.org | Usar: pocas páginas y muy específicas |
| Manual, `troubleshooting/gpu/*` | Problemas por marca y sistema | Ya está en el lago | Ya se usa |

### P3: qué tan común es cada equipo

| Fuente | Qué da | Acceso y límites | Veredicto |
|---|---|---|---|
| **INEGI ENDUTIH** | Hogares con computadora, tipo de equipo, internet, por entidad y por zona urbana o rural | Datos abiertos y microdatos de INEGI, gratis. Encontré la presentación y el boletín 2024; la ruta exacta de los microdatos queda *por verificar* | **Usar.** Es la única fuente de población real para México |
| Encuesta de hardware de Steam | Porcentaje de GPUs, RAM y sistema operativo de los usuarios de Steam | Valve no tiene API. Hay CSV históricos de la comunidad, armados desde el Wayback Machine ([jdegene/steamHWsurvey](https://github.com/jdegene/steamHWsurvey), [myagues/steam-hss-data](https://github.xiaohuzi123231346.workers.dev/myagues/steam-hss-data)). Los datos tienen saltos raros, como el de chino simplificado en febrero de 2026 | Usar con cuidado: está sesgada a jugadores, así que sirve como cota superior |
| StatCounter (México) | Sistema operativo y resolución de pantalla en escritorio | Gráficas públicas. La descarga en CSV y su licencia quedan *por verificar*. En México, 1366×768 sigue en torno al 8–9 % de escritorio | Usar con cuidado para resolución, que importa para la interfaz de Blender |
| **Censo propio en clase** (sección 5) | El equipo real de nuestros estudiantes | Lo construimos nosotros | **Usar. Es la fuente principal de P3** |

### P4: equivalencias de Maya y 3ds Max

| Fuente | Qué da | Acceso | Veredicto |
|---|---|---|---|
| Manual de Blender, mapa de teclas compatible con la industria | La correspondencia oficial de atajos | Ya está en el lago | Ya se usa |
| Documentación pública de Autodesk (listas de funciones de Maya y 3ds Max) | Qué hace cada herramienta, para armar la lista de brechas | Páginas públicas; revisar robots.txt y términos | Usar: solo títulos y estructura, sin copiar texto |
| Stack Exchange (preguntas con etiquetas o texto «Maya», «3ds Max», «coming from») | Dudas reales de quien migra | API gratuita (ya en el catálogo) | Usar: búsqueda por texto, con la cuota diaria |
| YouTube Data API | Títulos y descripciones de tutoriales «Maya to Blender», como señal de demanda | 10 000 unidades al día. La búsqueda es cara y los subtítulos de videos ajenos no se pueden descargar por la API ([cuotas oficiales](https://developers.google.com/youtube/v3/determine_quota_cost)) | Usar con cuidado: solo metadatos |

### P5: técnicas publicadas por la industria

| Fuente | Acceso | Veredicto |
|---|---|---|
| arXiv (cs.GR) | Ya en el catálogo. Ojo: la relevancia hoy se calcula sobre un fragmento recortado (sección 7) | Ya se usa; corregir el filtro |
| **OpenAlex** | **Cambió en febrero de 2026**: sin clave hay unos US$0,10 de uso al día y con clave gratuita unos US$1. La **copia completa es CC0 y gratis** ([resumen](https://jwatte.com/blog/openalex-open-index-of-research.md)) | Usar para citas y para encontrar trabajos de SIGGRAPH, Eurographics y otras conferencias por tema |
| Blog de desarrolladores de Blender y DevTalk | Ya en el catálogo | Usar como señal de qué técnicas entran a Blender |

### P6: cómo se hace X en la versión Y

| Fuente | Acceso | Veredicto |
|---|---|---|
| **Manual de Blender en español** (`docs.blender.org/manual/es/`) | Misma araña y mismo inventario (`objects.inv`). Traducción de la versión 4.5 al **73 %** ([translate.blender.org](https://translate.blender.org/projects/blender-manual/blender-4-5/manual-4-5/es)) | **Usar.** Hoy todo el conocimiento está en inglés y la plataforma es en español |
| Manual en inglés (5.2, 4.5, 3.6) | Ya en el lago; la araña estable desde el 17 de noviembre | Ya se usa; faltan las correcciones del filtro (sección 7) |
| Stack Exchange: API y copias completas | API: 300 llamadas al día sin clave y 10 000 con clave. Las copias oficiales piden cuenta desde 2024 y su licencia excluye entrenar modelos; hay copias de la comunidad hasta 2026-03-31 ([Archive.org](https://archive.org/details/stackexchange_20251231), [Hugging Face](https://huggingface.co/datasets/flymin/stackexchange_20260331)). Las copias de 2025-06-30 traían registros falsos de marca de agua | Usar la API para lo nuevo. La copia completa de Blender Stack Exchange, solo para consulta (RAG), no para entrenar |
| Manual de Godot (Sphinx) | Probablemente publica `objects.inv` (*por verificar*) | Usar cuando entre Godot a las prácticas |

### Señales de comunidad (tendencias, no respuestas)

| Red | Acceso gratuito | Veredicto |
|---|---|---|
| Foros Discourse (Blender Artists, DevTalk, Godot, Three.js) | JSON público (ya en el catálogo) | Ya se usa. Son temas generales: sirven como señal |
| **Bluesky** | API pública sin clave (`app.bsky.feed.searchPosts`) y flujo en vivo Jetstream ([documentación](https://docs.bsky.app/blog/jetstream)). Límites no documentados | **Usar**: buscar «Blender», «b3d», «#b3d» y contar temas por semana |
| **Mastodon** | Línea de tiempo por etiqueta sin clave, unas 300 peticiones cada 5 minutos por instancia ([documentación](https://docs.joinmastodon.org/methods/timelines/)) | **Usar**: `#b3d` y `#blender3d` en instancias de arte |
| YouTube | 10 000 unidades al día | Usar con cuidado: tendencias de tutoriales en español |
| **Reddit** | Desde finales de 2025 hace falta aprobación. Solo uso no comercial, **prohíbe usar los datos para IA**, unas 100 consultas por minuto. Los detalles cambian y las fuentes se contradicen (*por verificar* en Reddit) | **No conviene** por ahora: el uso con IA de G7B choca con sus términos |
| **X (Twitter)** | Sin capa gratuita desde febrero de 2026: unos US$0,005 por publicación leída | No conviene |
| Facebook, Instagram, TikTok, Discord | Las APIs de investigación están restringidas o piden aprobación; Discord solo lee servidores donde está el bot. *No se investigó a fondo* | No conviene, salvo un servidor de Discord propio de Amatista |

### Recursos para las prácticas

| Fuente | Acceso | Veredicto |
|---|---|---|
| Poly Haven y ambientCG (CC0) | Ya en el lago (2.487 recursos) | Ya se usa; **es de lo más valioso que hay** |
| Sketchfab Data API v3 | La búsqueda es pública; la descarga pide token y solo aplica a modelos con licencia Creative Commons. Los límites oficiales quedan *por verificar* ([developers](https://sketchfab.com/developers/data-api/v3)) | Usar con cuidado: filtrar por licencia y guardar la atribución |
| Extensiones de Blender | Ya en el lago (1.632) | Ya se usa |

---

## 4. Hasta dónde pueden llegar las arañas

| Límite | Regla | Ejemplo en G7B |
|---|---|---|
| `robots.txt` | Se respeta siempre (`ROBOTSTXT_OBEY`) | docs.blender.org prohíbe `/*/2.79/`; godot-blog y blendernation se retiraron |
| **Señales de contenido** (*Content-Signal*) | Hay sitios que declaran para qué se puede usar lo que publican | docs.blender.org: `search=yes, ai-train=no, use=reference`. **G7B puede usar el manual como referencia citada (RAG), pero no para entrenar modelos** |
| Derechos de autor | Si no hay licencia libre, solo se guarda el título, el enlace y un fragmento (`solo_metadatos`) | Noticias de Krita, FreeCAD y blender.org |
| Términos de servicio | No se rastrea lo que pide iniciar sesión ni lo que los términos prohíben | Facebook, Instagram, Discord, X y Reddit, en este último caso por el uso con IA |
| Recursos de Zyte gratuito | 1 unidad, trabajos de hasta 1 hora y datos que duran 7 días | Por eso la araña ahora recorre solo lo que cambió (`objects.inv`) |
| Lo que ninguna araña encuentra | Datos que no están publicados en ningún lado | P3 y P7 para nuestra población: hay que producirlos (sección 5) |

**Regla práctica.** Antes de agregar una fuente, hay que poder contestar: ¿qué pregunta del plan responde?, ¿qué permite su licencia?, ¿qué dicen su robots.txt y sus términos? y ¿hay una API o una copia completa antes que rastrear página por página? Si existe una copia completa (Blender Open Data, OpenAlex, Stack Exchange), es mejor que una araña.

---

## 5. APIs que conviene construir nosotros

Lo que falta (P1, P3 y P7 para estudiantes reales) no existe publicado. Estas cinco piezas lo producen:

1. **Sonda voluntaria en el equipo del estudiante** (P1 y P2). Es el mismo modelo que Blender Open Data, pero midiendo **fluidez de trabajo** (*viewport*, edición, modificadores) y no solo velocidad de render.
   - Corre desde el add-on, con consentimiento ([CONSENTIMIENTO_TELEMETRIA.md](../CONSENTIMIENTO_TELEMETRIA.md)) y escenas fijas.
   - Envía a un endpoint de la API de Amatista en Oracle, con el contrato `g7b.telemetria/1`.
   - El equipo se agrupa en rangos («integrada Intel, 8 GB») para no identificar a nadie.
2. **Censo de equipo en clase** (P3). Un formulario de 2 minutos al inicio de cada grupo: modelo de laptop, RAM, GPU, sistema y resolución. Con la sonda, se llena solo. Se cruza con la ENDUTIH para estimar qué parte de la población representa.
3. **Telemetría de prácticas con xAPI** (P7). Cada paso de una práctica deja un registro «estudiante (anónimo), verbo (*inició*, *terminó*, *se atoró*, *pidió ayuda*), objeto (práctica, paso)», junto con el perfil del equipo. Así se responde «¿se atoran por la práctica o por su computadora?».
4. **API de Geoda** (perfil del equipo → ajustes y versión recomendados). Ya está diseñada en el cubo (`perfiles`, `recomendaciones_habilitadas`); se enciende cuando haya mediciones reales.
5. **Servidor MCP sobre el conocimiento** (P6). Ya está en el plan: que una IA responda «cómo se hace X en la versión Y» citando la página del manual.

---

## 6. Dónde meter IA de forma directa

| Uso | Cómo | Cuidado |
|---|---|---|
| **Reemplazar el filtro por palabras clave** | Como en FineWeb-Edu: un modelo grande etiqueta unos cientos o miles de documentos con la pregunta, la utilidad y el nivel de equipo. Se revisa una muestra a mano y se entrena un clasificador pequeño, o se usa el modelo directamente si el volumen es bajo | Medir con un conjunto de validación etiquetado por nosotros antes de cambiar el filtro |
| **Extraer datos de los reportes de error y de los foros** | De cada reporte, sacar versión, GPU, controlador, síntoma y si se resolvió. Eso arma la tabla de P2 | Guardar la cita al reporte original |
| **Traducir el manual** donde falta el español | Traducir solo lo que no tiene traducción oficial y marcarlo como «traducción automática» | Lo traducido es obra derivada: sale con CC BY-SA 4.0 y atribución |
| **Asistente con citas (RAG)** | Buscar en el manual y responder citando | Evaluar con un conjunto de preguntas y respuestas correctas propias, no solo con métricas automáticas: [RAGAS](https://docs.ragas.io/en/stable/references/metrics.html) mide fidelidad y relevancia, pero una respuesta equivocada puede sacar puntaje perfecto si el contexto recuperado estaba mal |
| **Etiquetar las señales de la comunidad** | Agrupar los temas de foros y redes por tema y por nivel de equipo | — |

**Lo que no se puede hacer.** Entrenar o ajustar modelos con el manual de Blender (`ai-train=no`), con las copias de Stack Exchange posteriores a 2024 ni con datos de Reddit. Usarlos como referencia con cita sí se puede.

---

## 7. Lo que dicen los datos del lago (17 de noviembre de 2026)

Análisis de solo lectura sobre una copia del lago.

- **Documentos aceptados: 1.029.**
  - 1.022 son del manual y equivalen a 642 páginas distintas, porque el resto es la misma página en otra versión. Las otras fuentes aportan 7.
  - El 100 % está en inglés y el 38 % del manual son nodos de geometría.
  - En todo el texto, «Intel UHD», «4 GB», «8 GB» y «GTX» aparecen 0 veces y «VRAM» 1 vez.
- **Del manual, 1.376 páginas nunca se aceptaron.** Unas 920 sirven:
  - 503 son la misma página en otra versión.
  - 335 son nodos que la taxonomía no reconoce.
  - 74 caen por filtros de calidad demasiado estrictos.
  - 11 se quedaron en revisión sin que nadie las revise.

  Además hay una falla: **cuando la araña vuelve a extraer una página ya aceptada, el filtro la rechaza como duplicada de sí misma**. Por eso las 495 tablas nuevas no llegan a MongoDB.
- **Cubo.**
  - Las 18 mediciones de la sonda salieron de servidores de GitHub (Xeon y EPYC, 15 GB de RAM, sin GPU ni pantalla), con una sola escena y Blender 4.0.2.
  - Las 3.000 de Blender Open Data son de una semana de 2022, con Blender 3.0.1 y equipos de gama alta.
  - Geoda tiene `perfiles: []`.
- **Crudo.**
  - 329 temas de foros, de los cuales 5 tratan de rendimiento.
  - Unos 4.200 recursos y extensiones; esto sí sirve ya para las prácticas.
- **Otras fuentes.**
  - En arXiv, la relevancia se calcula sobre un fragmento de 43 a 65 palabras en lugar del resumen completo de 160 a 320.
  - En Stack Exchange, preguntas con respuesta aceptada y votos caen por no traer «medidas».

---

## 8. Camino recomendado

**Ya, con lo que hay (semanas 1–2):**
1. Corregir el embudo: que la reextracción actualice en lugar de rechazar, que el manual oficial solo se etiquete y no se rechace, guardar variantes de versión, ajustar los filtros de calidad y calcular la relevancia con el texto completo. Recupera unas 920 páginas sin extraer nada nuevo.
2. Importar la copia completa de Blender Open Data, filtrada a gama baja y a versiones 4.x y 5.x.
3. Agregar el manual en español con la misma araña.

**Siguiente (semanas 3–6):**
4. Construir la sonda voluntaria en el add-on y el censo de equipo en clase. Es lo único que llena P1 y P3 para nuestra población.
5. Agregar la ENDUTIH de INEGI y la encuesta de Steam al cubo como contexto de población.
6. Agregar los reportes de error de Blender (P2), extraídos con IA.
7. Agregar señales de Bluesky y Mastodon.

**Con estudiantes (estadía):**
8. Telemetría de prácticas con xAPI (P7), en ciclos de investigación basada en diseño, documentados como parte de la estadía.
9. Encender las recomendaciones de Geoda cuando cada perfil tenga suficientes mediciones aceptadas.
10. Reemplazar la taxonomía por palabras clave con etiquetas de IA validadas.

---

## 9. Pendiente de verificar

- La API de projects.blender.org: el proxy de la sesión la bloqueó. Probarla desde GitHub Actions.
- La licencia de la copia de Blender Open Data, en su página de descarga.
- La ruta de los microdatos de la ENDUTIH 2024.
- La descarga en CSV de StatCounter y su licencia.
- Los términos vigentes de Reddit: las fuentes secundarias se contradicen.
- Si OpenBenchmarking.org tiene una API documentada.
- Los límites oficiales de Sketchfab.
- Si el manual de Godot publica `objects.inv`.

## Fuentes

- Benchmarks: [Blender Open Data, descarga](https://opendata.blender.org/download/) · [qué es Open Data](https://opendata.blender.org/about/) · [OpenBenchmarking pts/blender](https://openbenchmarking.org/test/pts/blender-4.0.0) · [system/blender](https://openbenchmarking.org/test/system/blender-1.1.0)
- Población: [INEGI ENDUTIH 2024, presentación](https://inegi.org.mx/contenidos/programas/endutih/2024/doc/presentacion_endutih2024.pdf) · [boletín](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/endutih/ENDUTIH_24_RR.pdf) · [resumen (Yucatán.com.mx)](https://www.yucatan.com.mx/merida/2025/05/08/acceso-a-internet-en-yucatan-cuantos-para-que-y-donde-lo-usamos-segun-inegi.html) · [Steam HW survey, histórico](https://github.com/jdegene/steamHWsurvey) · [steam-hss-data](https://github.xiaohuzi123231346.workers.dev/myagues/steam-hss-data) · [StatCounter México](https://gs.statcounter.com/screen-resolution-stats/desktop/mexico)
- Redes y APIs: [Reddit 2026 (secundaria)](https://data365.co/blog/reddit-api-pricing) · [Reddit, lo que sigue gratis](https://apiserpent.com/blog/free-reddit-api) · [YouTube, costo por método](https://developers.google.com/youtube/v3/determine_quota_cost) · [YouTube, cuotas y auditorías](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits?hl=en) · [Bluesky Jetstream](https://docs.bsky.app/blog/jetstream) · [AT Protocol, streaming](https://atproto.com/guides/streaming-data) · [Mastodon timelines](https://docs.joinmastodon.org/methods/timelines/) · [X, precios 2026 (secundaria)](https://data365.co/guides/twitter-api-limitations-and-pricing) · [Sketchfab Data API](https://sketchfab.com/developers/data-api/v3) · [Sketchfab, ayuda](https://help.sketchfab.com/en/articles/16152031-api-overview)
- Académico y datos abiertos: [OpenAlex 2026 (secundaria)](https://jwatte.com/blog/openalex-open-index-of-research.md) · [Stack Exchange dump 2025-12-31](https://archive.org/details/stackexchange_20251231) · [Academic Torrents](https://academictorrents.com/details/0d1d597fa7809f0e85f127b5eb3088219ddbad39) · [dump 2026-03-31](https://huggingface.co/datasets/flymin/stackexchange_20260331) · [restricción de 2024 (DevClass)](https://www.devclass.com/development/2024/07/30/stack-exchange-restricts-access-to-dump-of-user-contributed-data-critics-complain-this-contradicts-license/1625192) · [traducción del manual al español](https://translate.blender.org/projects/blender-manual/blender-4-5/manual-4-5/es)
- Metodología: [FineWeb-Edu (NeurIPS 2024)](https://proceedings.nips.cc/paper_files/paper/2024/file/370df50ccfdf8bde18f8f9c2d9151bda-Paper-Datasets_and_Benchmarks_Track.pdf) · [clasificador FineWeb-Edu](https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier) · [propella-1](https://arxiv.org/html/2602.12414v2) · [RAGAS, métricas](https://docs.ragas.io/en/stable/references/metrics.html) · [Design-Based Research](https://Www.Wikipedia.org/wiki/Design-based_research) · [Advances in DBR](https://journals.sfu.ca/flr/index.php/journal/article/download/114/212?inline=1) · [DBR en educación superior (AJET)](https://ajet.org.au/index.php/AJET/article/download/10380/2201/35549)
- Analítica del aprendizaje en 3D: [xAPI en un curso de diseño 3D (Wu et al., 2020)](https://pure.ecnu.edu.cn/en/publications/design-and-implementation-of-data-collection-mechanism-for-3d-des/) · [xAPI Made Easy](https://www.academia.edu/112203333/xAPI_Made_Easy_A_Learning_Analytics_Infrastructure_for_Interdisciplinary_Projects) · [Onshape y la investigación en clase](https://onshape.com/en/blog/why-engineering-collaboration-starts-in-the-classroom)
- Contexto latinoamericano: [Blender en Bolivia (opinión)](https://correodelsur.com/opinion/20260310/innovacion-en-la-ensenanza-stem-en-bolivia-blender-como-herramienta-cognitiva-para-el-aprendizaje-de-matematicas-y-fisica.html) · [herramientas digitales en Latinoamérica](https://ciencialatina.org/index.php/cienciala/article/download/15638/22292) · [BID](https://www.iadb.org/es/blog/educacion/maestros-y-libros-para-los-ricos-robots-y-pantallas-para-los-pobres-0)
