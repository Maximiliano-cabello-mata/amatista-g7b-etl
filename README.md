# G7B

G7B measures how open-source 3D software runs on real computers, from older machines to high-end workstations. It collects documentation, techniques, textures and tools alongside those measurements. Geoda uses this evidence to choose settings for each machine. Each record carries its source, version and license.

G7B is the sister project of **Amatista**, the platform for learning 3D with Blender and A-Frame. The projects have separate repositories and cloud infrastructure and exchange data through JSON contracts. G7B measures performance and selects settings. Amatista teaches, recommends settings and is the only project that stores personal data. [Amatista repository](https://github.com/Maximiliano-cabello-mata/amatista)

| Data source | Path through G7B |
|---|---|
| Online sources | Geodar Radar → Azure data lake → quality checks → documents and catalogs in MongoDB |
| Real computers | Performance probe → Azure data lake → DuckDB cube → Geoda → `perfiles.json` → Amatista |

After each successful cube build, the Geoda lab planner processes the verified cube in GitHub Actions. The workflow stores its results as artifacts separate from Amatista’s public status data. [Geoda on GitHub Actions](docs/GEODA_KERNEL.md)

## Hack4Edu

G7B and Amatista participate in Hack4Edu together. The `hack4edu` Git tag marks the starting point. To see what the team built during the event, run the command below. [Hack4Edu evidence and verification commands](docs/hack4edu/README.md)

```bash
git log --oneline hack4edu..main
```

<a id="las-piezas"></a>

## Components

| Component | Role | Directory | Recorded status |
|---|---|---|---|
| **Geodar Radar** | Monitors 33 online 3D sources, including forums, manuals, articles, CC0 textures, open-source tools and web telemetry. Routes each record to its destination. | `geodar/`, `g7b_ingesta/`, `fuentes/` | Automated tests pass. Run a live check in Actions before enabling a source. |
| **Documentation spiders** | Crawl four versions of the Blender manual and other Sphinx manuals on Zyte. | `motor_extraccion/` | In production, with 987 documents published. |
| **Data lake** | Stores raw records in the bronze layer of Azure Blob Storage, then processes them through silver and gold. | `g7b_lago/`, `infra/azure/` | In production. |
| **Document quality checks** | Apply five quality checks before publication to MongoDB and record the reasons for each decision. | `g7b_ingesta/` | In production. |
| **Performance probe** | Measures Blender viewport, editing, animation and rendering performance on individual machines. | `sonda/` | v0.2 |
| **Telemetry** | Validates measurements from the probe and Blender Open Data and stores them in Azure. | `g7b_telemetria/` | Verified in Azure on November 3. |
| **Data cube** | Stores six dimensions in a versioned Parquet and DuckDB cube. | `g7b_almacen/` | 3,003 measurements verified in Azure. |
| **Geoda** | Classifies hardware into tiers N0–N4 and builds evidence-based profiles with costs and a reversible plan. | `geoda/` | Initial implementation (0.1.0). |
| **Private Azure infrastructure** | Runs jobs with managed identity and OIDC and maintains a catalog of offers. | `infra/azure/`, `infra/ofertas/` | Lab deployed. |
| **Analysis** | Provides Deepnote notebooks for exploring the cube and document quality. | `analisis/` | Available. |

<a id="probarlo"></a>

## Getting started

Run these commands from the repository root. The command names and flags are in Spanish.

```bash
pip install -r requirements-dev.txt          # Data lake, cube and test dependencies
python -m pytest pruebas -q                  # Run the automated tests
python -m geodar mapa                        # List the sensors and their locations
python -m geoda perfiles                     # Show profiles by tier (uses baseline rules without a cube)
python -m geoda decidir --huella equipo.json # Generate a plan for one machine
```

<a id="documentos"></a>

## Documentation

For the two collection paths, start with the [Site 4.1 documentation spider](algoritmos/documentacion/site-4.md) and the [G7B telemetry standard](docs/ESTANDAR_TELEMETRIA.md). The [documentation index](docs/README.md) also covers the master plan, Azure architecture, reports and project logs.
