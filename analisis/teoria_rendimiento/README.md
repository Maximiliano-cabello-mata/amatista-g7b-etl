# Teoría de rendimiento y criterio de mediciones

Código de investigación. **No forma parte del flujo de G7B:** no escribe en el lago ni en el cubo. El método, la validación y los hallazgos están en [`docs/investigacion/2026-11-22_teoria_rendimiento_y_criterio.md`](../../docs/investigacion/2026-11-22_teoria_rendimiento_y_criterio.md).

| Archivo | Qué hace |
|---|---|
| `convertir.py` | Snapshot de Blender Open Data → tabla plana. Usa `g7b_telemetria.capturar.opendata` y el estándar `g7b.hardware/1`, igual que el lago |
| `teoria.py` | Ajusta y valida la teoría de rendimiento. Exporta los CSV que lee Power BI. Con `--hipotetico`, estima dispositivos que no existen en los datos |
| `criterio.py` | Juzga cada medición contra sus pares y la teoría, y se pone a prueba con errores sembrados |
| `pbip.py` | Genera el proyecto de Power BI (`.pbip`, modelo en TMDL) y un script para la vista TMDL |

Dependencias: `duckdb`, `numpy` y `pandas`. Para la conversión hace falta además el código de G7B (este repositorio).
