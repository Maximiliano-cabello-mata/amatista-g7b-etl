# Tareas de las arañas: documentación y telemetría

Actualizado: 17 de noviembre de 2026. Esta es la lista viva de pendientes de las dos herramientas de Geodar ([GEODAR_RADAR.md](GEODAR_RADAR.md), sección 0):

- **Araña de documentación** (Zyte): manuales y notas de versión → embudo → MongoDB.
- **Radar de telemetría** (`geodar telemetria` y sensores directos): cifras de equipos y rendimiento con el estándar `g7b.hardware/1` → cubo → Geoda ([ESTANDAR_TELEMETRIA.md](ESTANDAR_TELEMETRIA.md)).

En cada tarea, «Hecho cuando» dice cómo se comprueba. De dónde sale cada una está en la [bitácora del 17 de noviembre](bitacoras/2026-11-17.md) y en la [investigación de arañas de nicho](investigacion/2026-11-17_aranas_nicho/REPORTE.md).

---

## Mañana, 18 de noviembre: lo primero

### Radar de telemetría

| # | Tarea | Por qué | Hecho cuando |
|---|---|---|---|
| T1 | **Reconstruir el cubo con la primera tanda real de Open Data** (lanzar «Cubo G7B» o el ciclo con `completo`) | La tanda de 20.000 registros (59.998 mediciones, del 15 de junio al 16 de noviembre de 2026) entró al lago a las 07:56, pero el cubo se había reconstruido a las 07:55 y sigue en 3.018 mediciones | El cubo tiene unas 63.000 mediciones y `v_render_por_nivel` muestra filas N2 (integradas) |
| T2 | **Medir la cobertura de `fuentes/hardware.yml`** en la tanda real: qué porcentaje de GPUs queda «desconocida» y cuáles son los 20 nombres más comunes sin regla | Lo que no se reconoce no recibe nivel. Hay que saber cuánto se pierde | Hay un informe con el porcentaje y, si pasa del 10 %, las reglas nuevas con sus pruebas |
| T3 | **Primer vistazo a P1 con datos reales**: mediana de render por nivel y clase de GPU para Blender 4.x y 5.x | Es la primera vez que hay datos de equipos modestos recientes | Hay una tabla en `docs/reportes/` con N2, N3 y N4, versión y escena, citando la versión del cubo |
| T4 | **Destrabar `blender-reportes`**: confirmar si `Type/Report` es la etiqueta de los reportes nuevos y si `since`/`before` filtran por actualización. Probar sin etiqueta y con otras, con `geodar probar` en Actions | La prueba con ventanas dio solo 5 reportes en 6 días, pocos para el tráfico de Blender | Hay un número creíble de reportes por día, y la configuración ajustada en el catálogo |
| T5 | **Revisar las condiciones de uso de projects.blender.org** (términos, `robots.txt` desde Actions) y decidir si se activa `blender-reportes` | Está inactiva por licencia y por los incidentes de carga en su infraestructura | Queda la decisión escrita en el catálogo (`licencia_verificada` y `revisar`) |

### Araña de documentación

| # | Tarea | Por qué | Hecho cuando |
|---|---|---|---|
| D1 | **Corregir la reextracción en el embudo**: una página que ya estaba aceptada y vuelve con otra extracción es una **actualización**, no un duplicado de sí misma | Le pasó a 1.014 páginas del recorrido `883618/1/16`: las 495 tablas nuevas y 266 páginas con texto cambiado no llegaron a MongoDB | Al reprocesar `883618-1-16`, esas páginas salen como «actualizado» en `publicar` |
| D2 | **Conservar la estructura hasta MongoDB**: tablas, propiedades (la lista completa, no la cuenta), jerarquía, bloques de código, `ruta`, `canonica` y `extraido_en` | Hoy `a_documento` reduce las propiedades a un número y descarta lo demás (auditoría del 15 de noviembre, defecto 5) | Un documento del manual en MongoDB trae sus tablas y sus propiedades |
| D3 | **Relevancia por fuente para documentación oficial**: el manual se etiqueta con las preguntas del plan, pero no se rechaza por no tener palabras clave | 335 páginas útiles rechazadas, sobre todo nodos de geometría y de sombreado | La simulación sobre el lago recupera esas páginas sin aceptar índices ni páginas vacías |

---

## Después: araña de documentación

| # | Tarea | Hecho cuando |
|---|---|---|
| D4 | **Variantes de versión**: la misma página en 4.5 y 3.6 se guarda como variante del documento aceptado (clave: `ruta` y `canonica`) y la búsqueda filtra por versión antes de buscar por similitud | Las 503 páginas «aceptadas en otra versión» quedan como variantes y el asistente responde según la versión |
| D5 | **Manual en español** (`docs.blender.org/manual/es/`): el `objects.inv` respondió 200 (168 KB) y la licencia es CC BY-SA 4.0. Va con la misma araña y el sensor `sphinx` | El lago tiene la primera tanda en español y el embudo la acepta con idioma `es` |
| D6 | **Documentación para desarrolladores de Blender** (notas de versión, compatibilidad, GPU): bajarla con `git clone` en Markdown, no con la araña | Las notas de 4.x y 5.x están en bronce con licencia y procedencia |
| D7 | **Verificar desde Actions** el `robots.txt`, las señales de contenido y los términos de los hosts candidatos: developer, studio y conference.blender.org, blender.stackexchange.com, blenderartists.org, polycount.com, 80.lv y help.autodesk.com | Hay una tabla con fecha y copia archivada de cada uno |
| D8 | **Registro de procedencia por documento**: licencia, copia del `robots.txt`, señal de contenido y uso permitido (ingerir, referenciar o solo enlazar) | Cada documento en plata lleva esos campos y el asistente se niega a citar en extenso lo que está en rojo |
| D9 | **Cobertura con alerta**: si un trabajo extrae menos páginas de las que lista el inventario, o no hubo ingesta en N días, se abre el aviso | El aviso `g7b-alerta` se abre en una prueba con un trabajo incompleto |
| D10 | **Lista de oro** de 50 a 100 páginas de nicho conocidas, para medir cuánto encuentra cada araña y cuánto descubre de dominios nuevos | La lista está en `fuentes/` y hay una primera medición |
| D11 | **Descubrir fuentes** con el índice de URL de Common Crawl (Parquet consultado con DuckDB) y los dominios que citan los foros | Una lista de candidatas, cada una con su licencia por revisar |

## Después: radar de telemetría

| # | Tarea | Hecho cuando |
|---|---|---|
| T6 | **Nombres de GPU de WebGL** en `g7b.hardware/1`: cadenas ANGLE («ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11…)») y marca `render_por_software` (SwiftShader, llvmpipe, «Software») | Pruebas con cadenas reales de Windows, Linux y macOS, y el render por software sale de las recomendaciones |
| T7 | **Sonda**: marcar `render_por_software` y agregar `fps_p01_low` (el 1 % más lento) a la vista 3D | Las mediciones del runner de GitHub quedan marcadas y fuera de Geoda |
| T8 | **Diseñar la sonda web de Amatista** (de la [revisión de arañas del navegador](investigacion/2026-11-17_aranas_telemetria_navegador/REVISION.md)): con consentimiento, `WEBGL_debug_renderer_info` normalizado con `g7b.hardware/1`, `fps_p50` y `fps_p01_low`, y `renderer.info` de Three.js. Solo clase y nivel, nunca la cadena cruda, y agregados de 5 equipos o más | Hay un contrato escrito (`g7b.huella_web/1`) y está aprobado el texto de consentimiento |
| T9 | **Censo de equipo en clase**: formulario de 2 minutos al inicio de cada grupo | Llega el primer grupo, cruzado con la ENDUTIH de INEGI |
| T10 | **Decidir las licencias pendientes** de los colectores: Steam, OpenBenchmarking, Web3D Survey y GPUinfo | Cada una queda activada con su colector o descartada con su motivo |
| T11 | **Ritmo de Open Data**: con 20.000 por semana, el archivo se completa en unas 18 semanas. Decidir si se sube a 50.000 | La decisión queda escrita en `telemetria.yml` |
| T12 | **Contexto de población**: ENDUTIH de INEGI (hogares con computadora, laptop o escritorio) y la encuesta de Steam como cota superior | Las dos fuentes están en el cubo como dimensión de población |

## Común a las dos

| # | Tarea | Hecho cuando |
|---|---|---|
| C1 | **Conjunto de prueba para IA**: 150 a 200 documentos del lago etiquetados a mano ([decisión de IA](investigacion/2026-11-17_decision_ia.md)) | El archivo está en `fuentes/` con su guía de etiquetado |
| C2 | Confirmar los límites reales de Gemini en AI Studio y el tipo de VM de Oracle | Los dos datos quedan escritos en la decisión de IA |
| C3 | Revisar con asesoría legal: Stack Exchange (términos de uso por IA), `use=reference` sin `ai-input` en docs.blender.org, y la posición del derecho mexicano | Queda una nota con la recomendación |
