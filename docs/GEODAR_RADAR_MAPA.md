# Geodar Radar: mapa de sensores

Generado con `python -m geodar mapa --markdown` el 2026-11-02, desde [`fuentes/catalogo.yml`](../fuentes/catalogo.yml). No se edita a mano: se cambia el catálogo y se vuelve a generar. Cómo funciona: [GEODAR_RADAR.md](GEODAR_RADAR.md).

**31 fuentes:** 19 ✅ activa, 6 🔒 licencia por confirmar, 4 ⏸️ inactiva, 2 🔗 la trae otra tarea.

## A dónde va cada cosa

Todo entra primero crudo a Azure (`bronce/<fuente>/<fecha>/`), así nada se pierde. Después:

| Destino | Va a |
|---|---|
| `documentos` | MongoDB conocimiento_3d.documentos, después del embudo de calidad (procesar + publicar) |
| `catalogo` | MongoDB g7b_catalogo.<coleccion> (catalogar) |
| `telemetria` | Azure: bronce → cubo DuckDB del warehouse (g7b_almacen) |
| `senales` | Azure: oro/senales/ con el resumen semanal (senales) → cubo y panel |

## F1 · Telemetría de equipos

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **blender-open-data**<br>Blender Open Data (benchmark de render) | g7b_almacen opendata (tarea Warehouse, cada lunes) | `externo` | `externo` | `telemetria` | CC0-1.0 (agregados) | 🔗 la trae otra tarea | 168 h |
| **sonda-g7b**<br>Sonda de G7B (Blender medido en Actions, Azure, Colab, Camber, Codespaces, PCs y laboratorios) | sonda (sonda_matriz y Jobs de Azure; lo externo llega por el contenedor entrada) | `externo` | `externo` | `telemetria` | propia (agregados) | 🔗 la trae otra tarea | 168 h |
| **caniuse-web3d**<br>Soporte de 3D en navegadores (caniuse) | raw.githubusercontent.com | `json_api` | `directo` | `telemetria` | CC-BY-4.0 (agregados) | ✅ activa | 168 h |
| **steam-encuesta-hardware**<br>Encuesta de hardware de Steam | store.steampowered.com | `pagina` | `zyte` | `telemetria` | derechos_reservados (agregados) | ⏸️ inactiva | 720 h |
| **openbenchmarking-blender**<br>OpenBenchmarking.org, prueba pts/blender | openbenchmarking.org | `pagina` | `zyte` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |
| **web3dsurvey**<br>Web3D Survey (soporte de WebGL y WebGPU por dispositivo) | web3dsurvey.com | `pagina` | `zyte` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |
| **gpuinfo-opengl**<br>GPUinfo, capacidades OpenGL por tarjeta | opengl.gpuinfo.org | `pagina` | `zyte` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |

## F2 · Formas optimizadas (costo por operación)

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **sonda-operaciones**<br>Sonda de operaciones (subdividir, simplificar, booleanas, UV, horneado...) | sonda de operaciones (plan maestro B13; Colab, Camber y Azure → contenedor entrada) | `externo` | `externo` | `telemetria` | propia (agregados) | ⏸️ inactiva | 720 h |

## F3 · Texturas y materiales

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **polyhaven-texturas**<br>Poly Haven, texturas | api.polyhaven.com, polyhaven.com | `json_api` | `directo` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
| **polyhaven-hdri**<br>Poly Haven, HDRI (iluminación) | api.polyhaven.com, polyhaven.com | `json_api` | `directo` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
| **ambientcg-materiales**<br>ambientCG, materiales | ambientcg.com | `json_api` | `directo` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |

## F4 · Herramientas

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **blender-extensiones**<br>Plataforma de extensiones de Blender | extensions.blender.org | `json_api` | `directo` | `catalogo` | varias (solo_metadatos) | ✅ activa | 168 h |
| **herramientas-libres**<br>Versiones de herramientas 3D libres (GitHub) | GitHub: 18 repos | `github_releases` | `directo` | `catalogo` | varias (solo_metadatos) | ✅ activa | 24 h |

## F5 · Técnicas y conocimiento

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **arxiv-cs-gr**<br>arXiv, gráficos por computadora (cs.GR) | rss.arxiv.org, arxiv.org | `atom` | `directo` | `documentos` | CC0-1.0 (solo_metadatos) | ✅ activa | 24 h |
| **blender-stackexchange**<br>Blender Stack Exchange | blender.stackexchange.com | `stackexchange` | `directo` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 24 h |
| **computergraphics-stackexchange**<br>Computer Graphics Stack Exchange | computergraphics.stackexchange.com | `stackexchange` | `directo` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 72 h |
| **blender-manual**<br>Manual de Blender (LTS vigente) | docs.blender.org | `pagina` | `zyte` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 168 h |
| **blender-noticias**<br>Noticias de blender.org | www.blender.org | `rss` | `directo` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **blender-code-blog**<br>Blog de desarrollo de Blender (code.blender.org) | code.blender.org | `rss` | `directo` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 72 h |
| **godot-blog**<br>Blog de Godot | godotengine.org | `rss` | `directo` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 72 h |
| **blendernation**<br>BlenderNation (noticias y tutoriales de la comunidad) | www.blendernation.com | `rss` | `directo` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **blender-notas-version**<br>Notas de versión de Blender | developer.blender.org | `pagina` | `zyte` | `documentos` | por_confirmar (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **blender-api-python**<br>Referencia de la API de Python de Blender | docs.blender.org | `pagina` | `zyte` | `documentos` | por_confirmar (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **godot-docs**<br>Documentación de Godot (estable) | docs.godotengine.org | `pagina` | `zyte` | `documentos` | CC-BY-3.0 (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **siggraph-advances**<br>SIGGRAPH, curso "Advances in Real-Time Rendering" | advances.realtimerendering.com | `pagina` | `zyte` | `documentos` | derechos_reservados (solo_metadatos) | ⏸️ inactiva | 720 h |
| **blender-artists**<br>Foro Blender Artists | blenderartists.org | `discourse` | `directo` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 12 h |
| **blender-devtalk**<br>Foro de desarrollo de Blender (devtalk) | devtalk.blender.org | `discourse` | `directo` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **godot-foro**<br>Foro de Godot | forum.godotengine.org | `discourse` | `directo` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **threejs-foro**<br>Foro de three.js (3D en la web) | discourse.threejs.org | `discourse` | `directo` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |

## F6 · Aprendizaje

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **amatista-agregados**<br>Amatista, eventos de práctica agregados (≥5 equipos, con consentimiento) | traer_amatista.yml (plan maestro B8) desde /api/g7b/v1/agregados | `externo` | `externo` | `telemetria` | propia (agregados) | ⏸️ inactiva | 24 h |

## F7 · Modelos 3D

| Fuente | Dónde está el sensor | Sensor | Extractor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **polyhaven-modelos**<br>Poly Haven, modelos 3D | api.polyhaven.com, polyhaven.com | `json_api` | `directo` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
