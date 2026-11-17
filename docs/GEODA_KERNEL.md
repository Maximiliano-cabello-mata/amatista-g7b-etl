# Geoda en GitHub Actions

El paquete de contratos, clasificación N0–N4, perfiles, costos y planificación se integra selectivamente desde el PR #10 (e923670). El puente del PR #16 conserva su contrato y su activación independiente. Geodar Radar es otra herramienta y no es el kernel.

**Desde el 17 de noviembre de 2026**, `geoda_kernel.yml` ya no descarga el artefacto del cubo (caducaba a los 14 días). Ahora lee el cubo vigente del lago, construye el paquete de conocimiento del núcleo público, corre los casos de conformidad y publica el paquete en el lago y en `publicacion/geoda_paquete.json`. Todo eso se explica en [GEODA_NUCLEO.md](GEODA_NUCLEO.md). El informe de laboratorio (`python -m geoda.ejecutar`) sigue disponible a mano.

Solo las pruebas de vista 3D aceptadas, con ventana y unidad fps, pueden alimentar los perfiles de fluidez. Los demás resultados siguen siendo útiles para cobertura y costos. La captura antigua no conserva el nivel: no se inventan observaciones de vista o costos ausentes. Las reglas base son hipótesis. Las huellas representan configuraciones de hardware, no usuarios ni un censo de máquinas.

Los artefactos de Actions duran 14 días: informe de cobertura y planes por estado, catálogo de operaciones y perfiles de laboratorio. Las acciones de Blender se describen como datos: esta versión no las aplica a escenas ni promueve recomendaciones al feed público. El catálogo enumera controladores candidatos; no los instala.

Uso local: `python -m geoda ejecutar` no es necesario; el proceso por lotes es `python -m geoda.ejecutar --entrada resultado-cubo --salida salida`. Para una huella técnica concreta: `python -m geoda decidir --huella equipo.json --perfiles salida/perfiles_laboratorio.json`. La integración del cliente Amatista y la prueba completa con una práctica real quedan para la siguiente etapa.
