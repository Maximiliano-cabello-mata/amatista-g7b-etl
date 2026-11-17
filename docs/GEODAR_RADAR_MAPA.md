# Geodar Radar: mapa de sensores

Generado con `python -m geodar mapa --markdown` el 2026-11-17, desde [`fuentes/catalogo.yml`](../fuentes/catalogo.yml). No se edita a mano: se cambia el catálogo y se vuelve a generar. Cómo funciona: [GEODAR_RADAR.md](GEODAR_RADAR.md).

**34 fuentes:** 20 ✅ activa, 7 🔒 licencia por confirmar, 6 ⏸️ inactiva, 1 🔗 la trae otra tarea.

## Quién hace qué

| Herramienta | Responsabilidad | Fuentes |
|---|---|---|
| radar de telemetría | Cifras de equipos y rendimiento, con el estándar `g7b.hardware/1` → cubo (`geodar telemetria`) | 7 |
| araña de documentación (Zyte) | Documentación: manuales y notas de versión → embudo → MongoDB | 5 |
| sensor directo | Feeds, APIs y foros: el sensor ya trae el dato → bronce (`geodar vigilar`) | 19 |
| descarga directa | Archivos (PDF) → bronce | 0 |
| gestor externo | Lo trae otra tarea (la sonda, Amatista) | 3 |

## A dónde va cada cosa

Todo entra primero crudo a Azure (`bronce/<fuente>/<fecha>/`), así nada se pierde. Después:

| Destino | Va a |
|---|---|
| `documentos` | MongoDB conocimiento_3d.documentos, después del embudo de calidad (procesar + publicar) |
| `catalogo` | MongoDB g7b_catalogo.<coleccion> (catalogar) |
| `telemetria` | Azure: bronce → cubo DuckDB del warehouse (g7b_almacen) |
| `senales` | Azure: oro/senales/ con el resumen semanal (senales) → cubo y panel |

## F1 · Telemetría de equipos

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **blender-open-data**<br>Blender Open Data (benchmark de render) | colector blender_open_data: opendata.blender.org | radar de telemetría | `externo` | `telemetria` | CC0-1.0 (agregados) | ✅ activa | 168 h |
| **sonda-g7b**<br>Sonda de G7B (Blender medido en Actions, Azure, Colab, Camber, Codespaces, PCs y laboratorios) | sonda (sonda_matriz y Jobs de Azure; lo externo llega por el contenedor entrada) | gestor externo | `externo` | `telemetria` | propia (agregados) | 🔗 la trae otra tarea | 168 h |
| **caniuse-web3d**<br>Soporte de 3D en navegadores (caniuse) | raw.githubusercontent.com | radar de telemetría | `json_api` | `telemetria` | CC-BY-4.0 (agregados) | ✅ activa | 168 h |
| **blender-reportes**<br>Reportes de error de Blender (sistema, GPU, versión rota y versión que funcionaba) | projects.blender.org | radar de telemetría | `gitea_issues` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 24 h |
| **steam-encuesta-hardware**<br>Encuesta de hardware de Steam | colector pendiente: store.steampowered.com | radar de telemetría | `pagina` | `telemetria` | derechos_reservados (agregados) | ⏸️ inactiva | 720 h |
| **openbenchmarking-blender**<br>OpenBenchmarking.org, prueba pts/blender | colector pendiente: openbenchmarking.org | radar de telemetría | `pagina` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |
| **web3dsurvey**<br>Web3D Survey (soporte de WebGL y WebGPU por dispositivo) | colector pendiente: web3dsurvey.com | radar de telemetría | `pagina` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |
| **gpuinfo-opengl**<br>GPUinfo, capacidades OpenGL por tarjeta | colector pendiente: opengl.gpuinfo.org | radar de telemetría | `pagina` | `telemetria` | por_confirmar (agregados) | 🔒 licencia por confirmar | 720 h |

## F2 · Formas optimizadas (costo por operación)

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **sonda-operaciones**<br>Sonda de operaciones (subdividir, simplificar, booleanas, UV, horneado...) | sonda de operaciones (plan maestro B13; Colab, Camber y Azure → contenedor entrada) | gestor externo | `externo` | `telemetria` | propia (agregados) | ⏸️ inactiva | 720 h |

## F3 · Texturas y materiales

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **polyhaven-texturas**<br>Poly Haven, texturas | api.polyhaven.com, polyhaven.com | sensor directo | `json_api` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
| **polyhaven-hdri**<br>Poly Haven, HDRI (iluminación) | api.polyhaven.com, polyhaven.com | sensor directo | `json_api` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
| **ambientcg-materiales**<br>ambientCG, materiales | ambientcg.com | sensor directo | `json_api` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |

## F4 · Herramientas

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **blender-extensiones**<br>Plataforma de extensiones de Blender | extensions.blender.org | sensor directo | `json_api` | `catalogo` | varias (solo_metadatos) | ✅ activa | 168 h |
| **herramientas-libres**<br>Versiones de herramientas 3D libres (GitHub) | GitHub: 18 repos | sensor directo | `github_releases` | `catalogo` | varias (solo_metadatos) | ✅ activa | 24 h |

## F5 · Técnicas y conocimiento

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **arxiv-cs-gr**<br>arXiv, gráficos por computadora (cs.GR) | rss.arxiv.org, arxiv.org | sensor directo | `atom` | `documentos` | CC0-1.0 (solo_metadatos) | ✅ activa | 24 h |
| **blender-stackexchange**<br>Blender Stack Exchange | blender.stackexchange.com | sensor directo | `stackexchange` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 24 h |
| **computergraphics-stackexchange**<br>Computer Graphics Stack Exchange | computergraphics.stackexchange.com | sensor directo | `stackexchange` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 72 h |
| **blender-manual**<br>Manual de Blender (LTS vigente) | docs.blender.org | araña de documentación (Zyte) | `sphinx` | `documentos` | CC-BY-SA-4.0 (texto_completo) | ✅ activa | 24 h |
| **blender-noticias**<br>Noticias de blender.org | www.blender.org | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **blender-code-blog**<br>Blog de desarrollo de Blender (code.blender.org) | code.blender.org | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 72 h |
| **godot-blog**<br>Blog de Godot | godotengine.org | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ⏸️ inactiva | 72 h |
| **blendernation**<br>BlenderNation (noticias y tutoriales de la comunidad) | www.blendernation.com | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ⏸️ inactiva | 24 h |
| **freecad-blog**<br>Blog de FreeCAD | blog.freecad.org | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 72 h |
| **krita-noticias**<br>Noticias de Krita | krita.org | sensor directo | `rss` | `documentos` | derechos_reservados (solo_metadatos) | ✅ activa | 72 h |
| **blender-notas-version**<br>Notas de versión de Blender | developer.blender.org | araña de documentación (Zyte) | `pagina` | `documentos` | por_confirmar (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **blender-api-python**<br>Referencia de la API de Python de Blender | docs.blender.org | araña de documentación (Zyte) | `pagina` | `documentos` | por_confirmar (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **godot-docs**<br>Documentación de Godot (estable) | docs.godotengine.org | araña de documentación (Zyte) | `pagina` | `documentos` | CC-BY-3.0 (texto_completo) | 🔒 licencia por confirmar | 168 h |
| **siggraph-advances**<br>SIGGRAPH, curso "Advances in Real-Time Rendering" | advances.realtimerendering.com | araña de documentación (Zyte) | `pagina` | `documentos` | derechos_reservados (solo_metadatos) | ⏸️ inactiva | 720 h |
| **blender-artists**<br>Foro Blender Artists | blenderartists.org | sensor directo | `discourse` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 12 h |
| **blender-devtalk**<br>Foro de desarrollo de Blender (devtalk) | devtalk.blender.org | sensor directo | `discourse` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **godot-foro**<br>Foro de Godot | forum.godotengine.org | sensor directo | `discourse` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |
| **threejs-foro**<br>Foro de three.js (3D en la web) | discourse.threejs.org | sensor directo | `discourse` | `senales` | derechos_reservados (solo_metadatos) | ✅ activa | 24 h |

## F6 · Aprendizaje

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **amatista-agregados**<br>Amatista, eventos de práctica agregados (≥5 equipos, con consentimiento) | traer_amatista.yml (plan maestro B8) desde /api/g7b/v1/agregados | gestor externo | `externo` | `telemetria` | propia (agregados) | ⏸️ inactiva | 24 h |

## F7 · Modelos 3D

| Fuente | Dónde está el sensor | Herramienta | Sensor | Destino | Licencia | Estado | Cada |
|---|---|---|---|---|---|---|---|
| **polyhaven-modelos**<br>Poly Haven, modelos 3D | api.polyhaven.com, polyhaven.com | sensor directo | `json_api` | `catalogo` | CC0-1.0 (solo_metadatos) | ✅ activa | 168 h |
