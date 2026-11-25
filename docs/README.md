<a id="documentos-de-g7b"></a>

# G7B documentation

The guides are grouped by task. If two documents disagree, the master plan takes precedence. The Site 4.1 guide and telemetry standard are available in English. Most other linked documents are in Spanish. [Master plan](PLAN_MAESTRO.md)

<a id="rumbo"></a>

## Project direction

| Document | What it covers |
|---|---|
| [Project vision](VISION.md) | The project’s goals and how Amatista, G7B and Geoda work together |
| [Master plan](PLAN_MAESTRO.md) | The roadmap for cloud offers, Azure setup, the dashboard, the API and integration with Amatista |
| [Original plan](PLAN.md) | Quality rules, research questions P1–P7 and project phases |
| [Technical definitions](FICHAS_TECNICAS.md) | Hardware tiers N0–N4, profiles, interactive performance, the cube and Geoda |
| [Hack4Edu](hack4edu/README.md) | Work completed before and during the event, with instructions for verifying it |

<a id="cómo-funciona-cada-pieza"></a>

## How the components work

| Document | What it covers |
|---|---|
| [Agent skills](habilidades-de-agente.md) | How to use and test repository skills for Site calibration and telemetry batches |
| [Geodar Radar](GEODAR_RADAR.md) · [Sensor map](GEODAR_RADAR_MAPA.md) | Online sources, sensors, licenses and data destinations |
| [Ingestion](INGESTA.md) | Sensors, triggers and document quality checks |
| [Site 4.1](../algoritmos/documentacion/site-4.md) | How the documentation spider chooses pages and measures the usefulness of the blocks it extracts |
| [Telemetry standard](ESTANDAR_TELEMETRIA.md) | Which collectors supply measurements, the `g7b.hardware/1` contract, Open Data batches and Blender bug reports |
| [Telemetry capture](TELEMETRIA.md) | How G7B collects and validates measurements from the probe and Blender Open Data |
| [Data cube](CUBO.md) | The Parquet and DuckDB data model, publication and queries |
| [Official sources and cube review](investigacion/2026-11-17_cubo_documentacion_oficial.md) | Manuals, findings on record identity and redundancy, and proposed priorities and tests awaiting implementation |
| [Geoda responsibilities](GEODA_RESPONSABILIDADES.md) | The agreed approach: AI knowledge and the adaptive engine as independent lines, with agents as consumers |
| [Geoda](GEODA.md) | Kernel structure, contracts and implemented features |
| [Performance theory and measurement criterion](investigacion/2026-11-22_teoria_rendimiento_y_criterio.md) (in Spanish) | A validated model that predicts samples/min for unmeasured device × version × scene combinations (13 % median error), an automatic measurement criterion (1 M measurements in 9 s), the Power BI project, and how to reproduce them. Research code in `analisis/teoria_rendimiento/`; not part of the pipeline |
| [Developer Pack offers and GitHub](OFERTAS_Y_GITHUB.md) | What each offer and GitHub feature provides |
| [Performance probe](../sonda/LEEME.md) | How to run a measurement on a computer |
| [Infrastructure](../infra/LEEME.md) · [Azure setup](../infra/azure/LEEME.md) | Cloud environments and Azure configuration |

<a id="operación-en-azure-azure"></a>

## Azure operations

| Document | What it covers |
|---|---|
| [Azure operations center](azure/CENTRO_OPERACIONES_AZURE.md) | Private architecture, activation criteria and incidents |
| [Cloud Shell runbook](azure/AZURE_24_7_CLOUD_SHELL.md) | Cloud Shell operations, student credit and SAS rotation |
| [Azure operational review](azure/CIERRE_AZURE.md) | Verified infrastructure and outstanding work |
| [Private worker](azure/WORKER_AZURE.md) · [Publishing with OIDC](azure/PUBLICAR_WORKER_OIDC.md) | The private worker and its publishing workflow |
| [Log migration](azure/MIGRACION_LOGS_AZURE.md) | Migration of the log storage path |

<a id="historia-lo-que-pasó-no-se-reescribe"></a>

## Project history

These records preserve the project as it stood when they were written.

| Document | What it records |
|---|---|
| [Daily logs](bitacoras/) | Work completed, errors encountered and next steps on November 1, 2 and 3 |
| [Original cloud architecture](historia/ARQUITECTURA_CLOUD.md) | The first Zyte and MongoDB deployment on October 31 |
| [Reports](reportes/) | Proposals, outlook, offer reviews and quality findings |
| [Audits](auditorias/) | The November 15 spider and Azure audit and the November 16 verification against the code and data lake |
| [Sphinx manual spider](ARANA_MANUALES.md) | How the spider uses `objects.inv` to process each changed page once and measure coverage |
| [Continuous operation](OPERACION_24_7.md) | The six-hour cycle, notifications, external scheduler, reprocessing and first live run |
| [Research](investigacion/) | Prior work and Amatista integration. Three starting points from November 17 cover [sources and methods](investigacion/2026-11-17_nicho_fuentes_y_metodologia.md) (free APIs by research question and what to build), [spiders for specialized knowledge](investigacion/2026-11-17_aranas_nicho/README.md) (12 decisions and which have been tested) and [AI options](investigacion/2026-11-17_decision_ia.md) (local models and the free Gemini offering). |
| [Professional placement](estadia/) | The Amatista and G7B placement proposal |
