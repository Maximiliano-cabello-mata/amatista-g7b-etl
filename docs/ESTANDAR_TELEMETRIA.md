<a id="estándar-de-telemetría-de-g7b"></a>

# G7B telemetry standard

November 17, 2026. This standard defines how G7B represents hardware and performance data so the cube and Geoda can compare equivalent measurements. It covers Blender Open Data, the performance probe and Blender bug reports. It also applies to prospective sources such as OpenBenchmarking and the Steam Hardware Survey.

<a id="1-quién-trae-la-telemetría"></a>

## 1. Telemetry collection

The source catalog enforces Geodar’s routing rules through the `validar` function in `g7b_ingesta/catalogo.py`.

| Tool | What it collects | How it runs |
|---|---|---|
| **Telemetry radar** | Hardware specifications and performance measurements | `python -m geodar telemetria` runs the collectors. Direct sensors can also use `destino: telemetria`. |
| **Documentation spiders on Zyte** | Manuals and release notes | `geodar vigilar` starts the spider and `zyte_a_lago` retrieves the results. |
| Direct sensors | Feeds, APIs and forums | `geodar vigilar` |
| External producers | Measurements from the probe and data from Amatista | Each runs its own jobs. |

Catalog rules apply to every source.

- A source with `extractor: zyte` must use `destino: documentos`.
- A source with `destino: telemetria` must use `extractor: telemetria` with a `colector`, or use `directo` or `externo`.
- The value `colector: pendiente` means the collector has yet to be implemented, usually because its license still needs confirmation. A source in that state must remain inactive.

<a id="2-el-equipo-g7bhardware1"></a>

## 2. Hardware records (`g7b.hardware/1`)

The `hardware` block describes the equipment for a measurement or event. The normalizer in `g7b_telemetria/hardware.py` uses G7B’s own lookup table. The `mide` field identifies a GPU benchmark (`gpu`), a CPU benchmark (`cpu`) or a failure event (`falla`). Field names and stored values below match the data contract. [Hardware lookup table](../fuentes/hardware.yml)

```json
{
  "estandar": "g7b.hardware/1",
  "mide": "gpu",
  "so": "Windows",
  "gpus": [{"nombre": "NVIDIA GeForce RTX 3060 Laptop GPU", "nombre_original": "...",
            "fabricante": "nvidia", "clase": "dedicada", "vram_gb": 6, "regla": "rtx 3060 laptop"}],
  "nivel": "N3", "confianza": "media",
  "motivos": ["GPU dedicada con 6 GB de VRAM", "sin dato de RAM"]
}
```

- **Name.** Normalization strips strings such as `(R)`, `(TM)` and `/PCIe/SSE2` while preserving the original name.
- **GPU class.** The values are `integrada` (integrated), `dedicada` (discrete) and `desconocida` (unknown). An unrecognized model receives `desconocida` and has no assigned tier.
- **VRAM.** The normalizer records capacity only when the model has one known configuration. The desktop RTX 3060 comes in both 8 GB and 12 GB versions, so its capacity is left empty.
- **Hardware tier N0–N4.** The normalizer applies Geoda’s rules in `geoda/niveles.py` and records both confidence and the reasons for the assignment. When system RAM is unknown, the GPU determines the tier and confidence drops. A source such as a bug report can also provide the OpenGL version. An integrated GPU running OpenGL 3.3 drops to N1.
- **CPU benchmarks.** A record with `mide: cpu` has no assigned tier because it does not identify the machine’s GPU.

To add a GPU model, add a rule to `fuentes/hardware.yml` and a test to `pruebas/test_radar_telemetria.py`. Place more specific rules first. Maintain the project’s own table. The project excludes copies of third-party databases such as TechPowerUp, which prohibits extraction.

<a id="3-la-medición-g7btelemetria1"></a>

## 3. Measurements (`g7b.telemetria/1`)

Measurements enter the cube through `g7b_almacen/cubo.py` from `plata/telemetria/<estado>/<fuente>/<lote>.jsonl.gz`.

| Field | Meaning |
|---|---|
| `contrato`, `sintetico` | The contract is `g7b.telemetria/1`. The cube accepts records explicitly marked `false` for synthetic data. |
| `id`, `huella_origen` | SHA-256 identifiers for the measurement and its source record |
| `fuente`, `licencia`, `licencia_url` | Source and licensing information |
| `fecha` | ISO 8601 timestamp with time zone |
| `version`, `escena`, `prueba` | Software version, scene and operation measured |
| `metrica`, `unidad`, `valor` | Metric, canonical unit (`s`, `fps` or `samples/min`) and a positive, finite value |
| `hardware` | The `g7b.hardware/1` block |
| `estado`, `motivos` | Quality status (`aceptado` or `revision`) and its reasons. Public benchmarks that G7B has yet to reproduce remain in `revision`. |

The cube view `v_render_por_nivel` groups public rendering measurements by hardware tier, GPU class, backend, software version and scene, and reports medians and quartiles. Older rows without `hardware` remain visible with a NULL tier, separate from classified measurements.

<a id="4-blender-open-data-completo-y-por-tandas"></a>

## 4. Processing the full Blender Open Data archive in batches

The old collector read the first 1,000 records every week. These were the oldest entries in the archive, from March 2022 and Blender 3.0.1. The `seleccionar_opendata` function now works through the archive as follows.

1. Each run scans the full archive once and selects up to `--limite` records. The weekly workflow uses 20,000.
2. New records since the previous run take priority. Any remaining capacity goes to older records, working backward from the last checkpoint without gaps or duplicates.
3. The lake stores the checkpoint in `control/telemetria/blender-open-data.json`. It records the captured date range (`desde` to `hasta`), the IDs at its boundaries and whether the beginning of the archive has been reached (`completo_hacia_atras`). The collector writes the checkpoint at the end so it can retry the batch after a failure.
4. The `geodar salud` command also checks the radar. It reports `error` after a failure and `atrasada` when more than two weeks have passed without a capture.

A live dry run on November 17 read the official archive in GitHub Actions with lake writes disabled. [Run 44037096411](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44037096411)

- The archive contained **437,638 records**. Of these, 87,848 used older schemas that the collector skips and **349,790** used the current schema.
- The batch of 2,000 records produced 6,000 measurements across three scenes per record. Each measurement included a `hardware` block.
- At 20,000 records per week, the archive at that size would take about 18 weeks to process. The batch limit can be increased to 50,000.

<a id="5-telemetría-de-fallas-los-reportes-de-error-de-blender"></a>

## 5. Failure telemetry from Blender bug reports

The `gitea_issues` sensor for the `blender-reportes` source reads the projects.blender.org API. It extracts the following fields from the report template.

- Operating system
- GPU and its tier under `g7b.hardware/1`
- OpenGL version
- The software version that failed and the version that worked
- Issue labels, such as the affected module

The report body belongs to its author. G7B keeps only the structured fields, title, link and dates. These records help answer research question P2 about which version works best on a given machine.

Blender’s infrastructure has experienced incidents caused by crawler load. The sensor requests reports updated since the previous run. The November 17 guide described a limit of three pages of 50 reports per day. The catalog now caps each daily check at six requests, with up to 50 results per page. The source is **inactive** pending confirmation of the site’s terms. To test it, run `python -m geodar probar --fuente blender-reportes` or use the workflow named “Geodar Radar (probar y revisar)”. [Source configuration](../fuentes/catalogo.yml)

Two live checks on November 17 illustrate why the query window matters.

- **Without time windows**, the API returned 150 reports. **131 included GPU details (87%)**, but the records dated from mid-2024 because the API did not return the newest reports first. The sensor now advances through update windows from `desde` to `desde` plus the window length, independently of result order. [Run 44036674216](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44036674216)
- **With time windows**, the sensor scanned six 24-hour windows from November 3 to 9 and found five reports, three with GPU details. The count was low for Blender’s traffic, and some results were older reports with recent updates. Before activation, check whether new reports carry the `Type/Report` label and whether `since` and `before` filter by update time as documented by Gitea. [Run 44037092158](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44037092158)

<a id="6-agregar-una-fuente-de-telemetría"></a>

## 6. Adding a telemetry source

1. Register the source in the catalog with `destino: telemetria`, `modo: agregados`, its confirmed license and the research questions it answers.
2. Choose the ingestion method. Use a direct sensor for an API or feed that already supplies the data. For a large archive or a source that requires batches, register a collector in `COLECTORES` in `geodar/__main__.py`.
3. Normalize equipment with `g7b_telemetria.hardware` so that every source uses the same hardware rules.
4. Use canonical units and assign a quality status. Measurements from outside G7B enter `revision`.
5. Test with sample data, then run a live check with `geodar probar` before activating the source.
