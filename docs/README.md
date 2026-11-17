# Documentos de G7B

Ordenados por para qué sirven. Si dos documentos dicen cosas distintas, manda el [plan maestro](PLAN_MAESTRO.md).

## Rumbo

| Documento | Para qué |
|---|---|
| [VISION.md](VISION.md) | El norte del proyecto y cómo se unen Amatista, G7B y Geoda |
| [PLAN_MAESTRO.md](PLAN_MAESTRO.md) | **El camino a seguir:** ofertas, Azure paso a paso, panel, API y la conexión con Amatista |
| [PLAN.md](PLAN.md) | El plan rector original: reglas de calidad, preguntas P1–P7 y fases |
| [FICHAS_TECNICAS.md](FICHAS_TECNICAS.md) | La definición exacta de cada concepto (niveles N0–N4, perfil, fluidez, cubo, Geoda…) |
| [hack4edu/](hack4edu/README.md) | Hack4Edu: lo que ya teníamos, lo trabajado y cómo comprobarlo |

## Cómo funciona cada pieza

| Documento | Pieza |
|---|---|
| [GEODAR_RADAR.md](GEODAR_RADAR.md) · [mapa](GEODAR_RADAR_MAPA.md) | Captura en internet: sensores, fuentes, licencias y destinos |
| [INGESTA.md](INGESTA.md) | Sensores, disparadores y el embudo de calidad de documentos |
| [TELEMETRIA.md](TELEMETRIA.md) | Captura de mediciones (sonda y Blender Open Data) y sus controles |
| [CUBO.md](CUBO.md) | El cubo Parquet + DuckDB: modelo, publicación y consultas |
| [Fuentes oficiales y revisión del cubo](investigacion/2026-11-17_cubo_documentacion_oficial.md) | Manuales, diagnóstico de identidad y redundancia, prioridades y pruebas propuestas; no implementadas |
| [GEODA.md](GEODA.md) | El kernel: estructura, contratos y lo que ya existe |
| [OFERTAS_Y_GITHUB.md](OFERTAS_Y_GITHUB.md) | Qué hace cada oferta del Developer Pack y cada función de GitHub |
| [../sonda/LEEME.md](../sonda/LEEME.md) | Cómo correr la sonda en una computadora |
| [../infra/LEEME.md](../infra/LEEME.md) · [../infra/azure/LEEME.md](../infra/azure/LEEME.md) | Nubes y cómo configurar Azure |

## Operación en Azure (`azure/`)

| Documento | Para qué |
|---|---|
| [azure/CENTRO_OPERACIONES_AZURE.md](azure/CENTRO_OPERACIONES_AZURE.md) | Arquitectura privada, puertas de activación e incidentes |
| [azure/AZURE_24_7_CLOUD_SHELL.md](azure/AZURE_24_7_CLOUD_SHELL.md) | Runbook de Cloud Shell, crédito de estudiante y rotación de SAS |
| [azure/CIERRE_AZURE.md](azure/CIERRE_AZURE.md) | Cierre operativo: base comprobada y pendientes |
| [azure/WORKER_AZURE.md](azure/WORKER_AZURE.md) · [azure/PUBLICAR_WORKER_OIDC.md](azure/PUBLICAR_WORKER_OIDC.md) | El worker privado y su publicación con OIDC |
| [azure/MIGRACION_LOGS_AZURE.md](azure/MIGRACION_LOGS_AZURE.md) | Migración de la ruta de logs |

## Historia (lo que pasó; no se reescribe)

| Documento | Qué registra |
|---|---|
| [bitacoras/](bitacoras/) | Cada día: lo hecho, los errores y el plan siguiente (1, 2 y 3 de noviembre; [16 y 17 de noviembre](bitacoras/2026-11-17.md)) |
| [historia/ARQUITECTURA_CLOUD.md](historia/ARQUITECTURA_CLOUD.md) | El primer despliegue en Zyte y MongoDB (31 de octubre) |
| [reportes/](reportes/) | Propuestas, horizonte, revisión de ofertas y observaciones de calidad | Última: [auditoría del flujo y de los datos del 17 de noviembre](reportes/2026-11-17_auditoria_flujo_y_datos.md).
| [auditorias/](auditorias/) | Auditoría de arañas y Azure (15 nov) y su revisión contra el código y el lago (16 nov) |
| [TAREAS_ARANAS.md](TAREAS_ARANAS.md) | **Lista viva de pendientes** de la araña de documentación y del radar de telemetría (qué sigue, con «hecho cuando») |
| [ESTANDAR_TELEMETRIA.md](ESTANDAR_TELEMETRIA.md) | Radar de telemetría frente a arañas de documentación, estándar `g7b.hardware/1`, Open Data por tandas y reportes de error de Blender |
| [ARANA_MANUALES.md](ARANA_MANUALES.md) | Araña de manuales Sphinx guiada por objects.inv: cada página una vez, solo cuando cambia, con cobertura medida |
| [OPERACION_24_7.md](OPERACION_24_7.md) | Ciclo de 6 horas, aviso, programador externo, reprocesamiento y primera vuelta real |
| [investigacion/](investigacion/) | Estado del arte e integración con Amatista. **Para empezar, tres documentos del 17 de noviembre:** [el nicho, fuentes y metodología](investigacion/2026-11-17_nicho_fuentes_y_metodologia.md) (APIs gratuitas por pregunta y qué construir), [arañas para conocimiento de nicho](investigacion/2026-11-17_aranas_nicho/README.md) (reporte con 12 decisiones, probado frente a teórico) y [qué IA usar](investigacion/2026-11-17_decision_ia.md) (local frente a Gemini gratuito). Además: [revisión de arañas de telemetría del navegador](investigacion/2026-11-17_aranas_telemetria_navegador/REVISION.md) e [índice de fuentes consultadas](investigacion/2026-11-17_fuentes_consultadas.md) |
| [estadia/](estadia/) | La propuesta de estadía (Amatista + G7B) |
