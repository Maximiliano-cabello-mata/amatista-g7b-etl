# Cambios de G7B

La etiqueta **`hack4edu`** (commit `3aad461`) separa lo que ya teníamos de lo trabajado durante Hack4Edu. Comprobación: `git log --oneline hack4edu..main`.


## Sin publicar · 16 de noviembre de 2026

- **Ciclo 24/7** (`.github/workflows/ciclo.yml`): un solo reloj que lanza en orden extracción, análisis, la parte semanal (telemetría, cubo y kernel de Geoda) y la entrega, espera cada tarea y abre un issue `g7b-alerta` si algo falla o hay fuentes atrasadas. Las demás tareas dejan de tener horario propio y encadenamientos. Se puede disparar desde un programador externo ([operación 24/7](docs/OPERACION_24_7.md)).
- **Reprocesamiento** (`g7b_ingesta/procesar.py`): cada archivo de bronce guarda su huella de reglas y se reevalúa solo cuando cambian la taxonomía, los umbrales, el catálogo de su fuente o la versión del embudo. Sin duplicar conteos ni chocar con el índice de repetidos. A mano: `--fuente`, `--lote`, `--forzar`.
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
