# Cambios de G7B

La etiqueta **`hack4edu`** (commit `3aad461`) separa lo que ya teníamos de lo trabajado durante Hack4Edu. Comprobación: `git log --oneline hack4edu..main`.


## Sin publicar · 16 de noviembre de 2026

- **Cubo `g7b.cubo/3`: velocidad y rendimiento** ([CUBO.md](docs/CUBO.md), sección 1 bis):
  - Cada métrica tiene su naturaleza: **velocidad** (render: Open Data y las pruebas de render de la sonda) o **rendimiento** (fluidez de la vista 3D y de la animación, respuesta al editar: la sonda).
  - Cada medición lleva un **índice sin unidades** frente a la mediana geométrica de su grupo, calculado dentro de su clase y con referencia solo de mediciones fiables.
  - Vistas nuevas: `v_equipos_*` (velocidad y rendimiento juntos por equipo, para calibrar) y `v_naturaleza_por_nivel_*`.
  - El paquete de Geoda toma sus factores solo de la velocidad.
- **Núcleo público de Geoda** ([núcleo](docs/GEODA_NUCLEO.md); [revisión del flujo hasta el kernel](docs/reportes/2026-11-17_flujo_hasta_el_kernel.md)):
  - **Paquete de conocimiento** `g7b.geoda.paquete/1` (`geoda/paquete.py`): perfiles de directas (con un mínimo de 5 equipos), factores relativos de Open Data entre niveles, citas del manual verificadas contra `objects.inv` (`fuentes/citas_manual.yml`), el estándar de hardware, los niveles y las operaciones. Cada sección lleva su huella, y el paquete se valida para que no lleve datos de equipos.
  - **API** `geoda.nucleo/1` (`geoda/nucleo.py`): de la huella y la tarea al plan, sin red, con escalera de evidencia (`medido`, `provisional`, `regla_base`), estimación relativa marcada como tal y citas por versión e idioma.
  - **Conformidad** (`geoda/conformidad.json`): 12 casos para cualquier implementación futura. Hay comandos nuevos: `python -m geoda paquete | plan | conformidad`.
  - **`geoda_kernel.yml`** lee el cubo vigente del lago, en lugar del artefacto que caducaba, y publica el paquete en `oro/geoda/` y en `publicacion/geoda_paquete.json` solo si cambió.
  - **Primer paquete real:** 18 factores y 84 de 84 citas verificadas; todavía 0 perfiles medidos.
- **Hardware** (T14–T16): las clases `apple` y `servidor` se separan para comparar niveles, y hay VRAM de las RTX 50, RX 9000 y GTX 16. El cubo recalcula el hardware de Open Data al construirse, así que las correcciones de la tabla llegan sin volver a capturar. Además, el cubo lee el modelo de GPU de la vista que reporta la sonda.
- **Ciclo 24/7** (`.github/workflows/ciclo.yml`): un solo reloj que lanza en orden extracción, análisis, la parte semanal (telemetría, cubo y kernel de Geoda) y la entrega, espera cada tarea y abre un issue `g7b-alerta` si algo falla o hay fuentes atrasadas. Las demás tareas dejan de tener horario propio y encadenamientos. Se puede disparar desde un programador externo ([operación 24/7](docs/OPERACION_24_7.md)).
- **Reprocesamiento** (`g7b_ingesta/procesar.py`): cada archivo de bronce guarda su huella de reglas y se reevalúa solo cuando cambian la taxonomía, los umbrales, el catálogo de su fuente o la versión del embudo. Sin duplicar conteos ni chocar con el índice de repetidos. A mano: `--fuente`, `--lote`, `--forzar`.
- **Cubo `g7b.cubo/2`: mediciones directas y relativas separadas** ([CUBO.md](docs/CUBO.md)):
  - Las **directas** (estudiantes y laboratorios escolares, con consentimiento) y las **relativas** (Open Data, la sonda en servidores) viven en tablas separadas (`hechos_directos` y `hechos_relativos`) y ninguna vista las mezcla.
  - Geoda solo lee directas y aceptadas.
  - Las dimensiones son tipadas: el equipo con el estándar `g7b.hardware/1`, y un diccionario de métricas.
  - Identidad semántica para Open Data, y en la sonda un id que ya no depende del orden de la lista.
  - Carga en bloque: 63.019 mediciones en unos 9 segundos.
  - La sonda declara `--entorno` y `--consentimiento`; en GitHub Actions corre con `--entorno ci`.
- **Bitácora del 16 y 17 de noviembre** ([bitácora](docs/bitacoras/2026-11-17.md)): incluye la primera tanda real de Open Data (20.000 registros y 59.998 mediciones), la [lista de tareas de las arañas](docs/TAREAS_ARANAS.md), el [índice de fuentes consultadas](docs/investigacion/2026-11-17_fuentes_consultadas.md) y la [revisión de arañas de telemetría del navegador](docs/investigacion/2026-11-17_aranas_telemetria_navegador/REVISION.md). El documento original de esa revisión pasa de la raíz a `docs/investigacion/`.
- **Radar de telemetría separado de las arañas de documentación** ([estándar de telemetría](docs/ESTANDAR_TELEMETRIA.md)):
  - **Estándar `g7b.hardware/1`** (`fuentes/hardware.yml` y `g7b_telemetria/hardware.py`): cualquier nombre de GPU o CPU se traduce a fabricante, clase y VRAM, y recibe un nivel N0–N4 con las reglas de Geoda, su confianza y sus motivos.
  - **Blender Open Data completo:** se recorre por tandas, de lo nuevo hacia atrás, con el estado guardado en el lago. Antes se tomaban siempre los primeros 1.000 registros: marzo de 2022 y Blender 3.0.1.
  - **Cubo:** la vista nueva `v_render_por_nivel`.
  - **Reportes de error de Blender:** el sensor `gitea_issues` extrae sistema, GPU, OpenGL y versiones de la plantilla, sin el texto. Queda inactivo hasta probarlo en vivo.
  - **Catálogo:** Zyte solo para documentación; la telemetría la trae el radar (`extractor: telemetria`). Hay un comando nuevo, `geodar telemetria`, y `geodar salud` ahora revisa también al radar.
- **Investigación del nicho (sin código):**
  - [Fuentes y APIs por pregunta del plan](docs/investigacion/2026-11-17_nicho_fuentes_y_metodologia.md).
  - [Reporte de arañas para conocimiento de nicho](docs/investigacion/2026-11-17_aranas_nicho/README.md), con 12 decisiones priorizadas y las notas de investigación.
  - [Decisión de IA](docs/investigacion/2026-11-17_decision_ia.md): local por omisión, Gemini y GitHub Models gratuitos como acelerador, ningún dato de estudiantes en capas gratuitas. El primer paso es un conjunto de prueba de 150 a 200 documentos etiquetados a mano.
- **Relevo del ciclo** (`relevo.yml`): GitHub se saltó tres de las cuatro horas del ciclo el 16 de noviembre. Ahora cada vuelta, al terminar, lanza un relevo que espera a la hora siguiente y lanza el ciclo con `workflow_dispatch`. Un horario de respaldo retoma la cadena si se corta. Además, se abre el aviso `g7b-alerta` si el ciclo pasa 8 horas sin una vuelta buena: antes, un ciclo que no arrancaba no avisaba.
- **Araña de manuales estable** ([araña de manuales](docs/ARANA_MANUALES.md)):
  - `blender_docs` pide exactamente las páginas del inventario `objects.inv` de cada versión, una vez cada una y sin seguir enlaces, con cobertura por versión en las estadísticas.
  - La misma página publicada en dos rutas sale una sola vez, más un alias.
  - El sensor `sphinx` relanza solo la versión cuyo inventario cambió (o a los 30 días), y nunca dos trabajos a la vez.
  - 2.79 sale de la lista: el `robots.txt` del sitio la prohíbe. Esa, y no el tope de páginas, era la razón de que no tuviera ninguna.
- **Primera vuelta del ciclo** (16 nov, 15:33 UTC): todo en verde, 147 registros nuevos, 1.021 aceptados (+26 en MongoDB). El horario de GitHub omitió las dos vueltas anteriores: hace falta el programador externo.
- **Araña (PR #21) corregida**: `_texto()` fallaba en cada página (`re.sub` sin reemplazo) y las tildes se habían convertido en `�`, incluido el `¶` que se limpia de los títulos. Ahora también se limpia `\uf0c1`. Esto había dejado en rojo Pruebas y Desplegar a Zyte.
- **Auditoría del 15 de noviembre** movida a `docs/auditorias/`, con su [revisión punto por punto](docs/auditorias/2026-11-16_revision_de_la_auditoria.md).
- **Embudo 2**: «mixto» es un idioma admitido; un resumen corto no se rechaza por idioma desconocido; el manual 2.79 no se marca como desactualizado. Alias «Blender Docs» para la araña antigua.

## Durante Hack4Edu (después de la etiqueta `hack4edu`)

### 3 de noviembre de 2026
- **Geoda, cimientos (0.1.0):**
  - contratos `g7b.huella/1`, `g7b.perfil/1`, `g7b.plan/1` y `g7b.operacion/1`;
  - clasificación N0–N4 con motivos y confianza;
  - perfiles con evidencia desde el cubo real;
  - modelo de costos v0 (tabla del cubo, sin inventar);
  - planificador con acciones reversibles para Blender.

  18 pruebas.
- **La captura de telemetría conserva el nivel y la GPU del equipo** (sin datos personales), para que Geoda pueda clasificar.
- **Consolidación de ramas** en la PR #10:
  - `main`;
  - Geodar Radar y el plan maestro;
  - Azure privado (PR #9);
  - observaciones de calidad documental;
  - cuaderno de Deepnote.

  Las PR #4 a #8 no se fusionan: su cubo choca con el de `main` ([detalle](docs/hack4edu/README.md#4-lo-que-no-se-integró-y-por-qué)).
- **Repo ordenado:**
  - documentos de Azure en `docs/azure/`;
  - la primera arquitectura en `docs/historia/`;
  - índice en `docs/README.md`;
  - evidencia de Hack4Edu en `docs/hack4edu/`.
- **Cubo de telemetría** Parquet + DuckDB versionado, verificado con SHA-256 en Azure: 3,003 mediciones (PR #15).
- **Telemetría real** de la sonda y de Blender Open Data con controles numéricos, verificada en Azure (PR #14).
- Cuaderno de Deepnote para auditar la calidad documental.

## Antes de Hack4Edu (hasta la etiqueta `hack4edu`)

### 2 de noviembre de 2026
- **Primera integración real de punta a punta:** Zyte → Azure → embudo → MongoDB, con 2,353 registros y 987 documentos publicados (PR #11).
- En ramas, sin integrar todavía:
  - Geodar Radar y el plan maestro (PR #10);
  - Azure privado con identidad administrada y OIDC (PR #9);
  - observaciones de calidad de los 987 documentos.

### 1 de noviembre de 2026
- Plan rector, visión, fichas técnicas, horizonte, investigación del estado del arte y propuesta de estadía.
- Sonda de rendimiento v0; lago en Azure; catálogo de fuentes, sensores, disparadores y embudo de calidad.
- Araña estructurada del manual de Blender y Mongo idempotente; environment `amatista1` e interruptor `G7B_INGESTA_ACTIVA` (PR #1 a #3).
- En ramas, sin integrar: primer warehouse, publicación segura, pruebas en Azure y tablero HTML (PR #4 a #8).

### 31 de octubre de 2026
- Andamiaje de Scrapy, primer despliegue en Zyte y MongoDB ([historia](docs/historia/ARQUITECTURA_CLOUD.md)).
