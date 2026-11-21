# Algoritmos de Geoda

| Modelo | Alcance | Código y evaluación |
|---|---|---|
| [Site 4.1](documentacion/site-4.md) | Sitios por eventos, clasificación de navegación y prioridad BM25 | [Modelo](../motor_extraccion/site.py) · [Registros históricos](historicos/README.md) |
| [Selección documental v3](documentacion/README.md) | Descubrimiento de páginas, valoración de bloques, gradiente por evento y precisión de lo seleccionado | [Clasificador](../motor_extraccion/documental.py) · [Frontera](../motor_extraccion/frontera_documental.py) · [Cálculo del 80 %](../g7b_ingesta/calidad_documental.py) |
| [Telemetría manual de Amatista](telemetria/README.md) | Mediana y dispersión en Blender, cadencia en A-Frame, cobertura y procedencia por fuente | [Recolector](../g7b_telemetria/recopilar.py) · [Piloto](../.github/workflows/piloto_telemetria.yml) |

El registro conserva la versión del modelo, la unidad de decisión, sus parámetros, los datos de evaluación y las limitaciones de cada experimento. La telemetría sigue su propio recorrido.
