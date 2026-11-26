# Ejecución de Geoda sobre el cubo

Al publicar, `g7b_almacen.cubo` ejecuta el kernel sobre el DuckDB que acaba de construir. Comprueba la huella antes de actualizar el puntero de Azure. El manifiesto publicado incluye el informe de Geoda. El feed comprueba su huella y conteos antes de anunciar esa versión. Si falla, queda disponible el último feed válido. La primera publicación tras actualizar el código requiere un cubo con ese informe.

El período semanal comienza el martes en UTC. El ciclo consulta el último cierre satisfactorio del período en GitHub Actions. Una vuelta tardía recupera el trabajo pendiente. La opción `completo` permite repetirlo a petición del operador. La entrega conserva `publicacion.json`, el DuckDB y los resultados de laboratorio. Para reproducir una entrega, abre el workflow **Geoda kernel** e indica la ejecución de **Cubo G7B**.


El paquete de contratos, clasificación N0–N4, perfiles, costos y planificación se integra selectivamente desde el PR #10 (e923670). El puente del PR #16 conserva su contrato y su activación independiente. Geodar Radar es otra herramienta y no es el kernel.


Solo las pruebas de vista 3D aceptadas, con ventana y unidad fps, pueden alimentar los perfiles de fluidez. Los demás resultados siguen siendo útiles para cobertura y costos. La captura antigua no conserva el nivel: no se inventan observaciones de vista o costos ausentes. Las reglas base son hipótesis. Las huellas representan configuraciones de hardware, no usuarios ni un censo de máquinas.

Los artefactos de Actions duran 14 días: informe de cobertura y planes por estado, catálogo de operaciones y perfiles de laboratorio. Las acciones de Blender se describen como datos: esta versión no las aplica a escenas ni promueve recomendaciones al feed público. El catálogo enumera controladores candidatos; no los instala.

Uso local: `python -m geoda ejecutar` no es necesario; el proceso por lotes es `python -m geoda.ejecutar --entrada resultado-cubo --salida salida`. Para una huella técnica concreta: `python -m geoda decidir --huella equipo.json --perfiles salida/perfiles_laboratorio.json`. La integración del cliente Amatista y la prueba completa con una práctica real quedan para la siguiente etapa.
