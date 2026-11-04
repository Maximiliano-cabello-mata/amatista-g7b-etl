# Deepnote para G7B

Este paquete incorpora una primera herramienta de análisis documental. No modifica el ETL ni implementa todavía el cubo de rendimiento.

## Inicio

1. Acceder al espacio de Deepnote y comprobar que el beneficio educativo esté aplicado. La oferta pública no demuestra que una cuenta específica ya lo tenga activo.
2. Crear un proyecto privado de análisis G7B e importar `01_explorar_documentacion.ipynb` en Notebooks.
3. Subir `requirements-deepnote.txt`. Instalarlo desde el entorno con `pip install -r requirements-deepnote.txt`.
4. Subir el archivo `883618-1-13.jsonl.gz` en Files. No está incluido en este paquete. El lector acepta gzip auténtico y JSONL plano con extensión .gz.
5. Mantener FUENTE="local" y ejecutar todas las celdas. Si el archivo está en otra carpeta, ajustar ARCHIVO.
6. Examinar las tablas, las alertas y los textos. Completar el dictamen humano de la muestra: una alerta automática no decide si el documento es útil.

## Conexiones opcionales

Para Azure, instalar las dependencias y configurar G7B_AZURE_LAGO_URL como variable secreta de Deepnote con acceso de lectura al contenedor lago. Elegir FUENTE="azure". Se descarga solo el blob indicado en la celda de configuración.

Para MongoDB, configurar G7B_MONGO_URI con un usuario de lectura de conocimiento_3d. Elegir FUENTE="mongo". Se consulta documentos filtrando origen al lote de esta prueba. Los 987 son una referencia histórica, no un resultado garantizado para una base que pudo cambiar.

No copiar credenciales del pipeline a celdas. Las integraciones de variables deben estar conectadas al proyecto. No habilitar horarios automáticos antes de verificar conexiones y resultados.

## Resultados

El cuaderno exporta metricas.json, revision_humana.csv y documentos_metadatos.parquet en resultados_deepnote/. Las salidas quedan en el proyecto; no se escriben en Azure ni MongoDB. No subir datos, resultados ni credenciales a Git. Limpiar las salidas de las celdas antes de versionar el cuaderno.

## Relación con el plan

Deepnote proporciona exploración colaborativa y consultas DuckDB sobre documentos. La integración posterior con Open Data y mediciones requiere un modelo propio, contratos validados y datos reales: esta primera entrega no debe describirse como telemetría ni como un cubo de hardware terminado.

## Referencias oficiales

- https://deepnote.com/docs/importing-and-exporting-jupyter-notebooks
- https://deepnote.com/docs/github
- https://deepnote.com/docs/environment-variables
- https://deepnote.com/docs/azure-blob-storage
- https://education.github.com/pack

La creación del proyecto, la activación del plan educativo y la ejecución en la nube requieren acceso al espacio Deepnote. El paquete no acredita esas acciones.

## Validación realizada

El 3 de noviembre de 2026 se ejecutaron todas las celdas de código localmente con Python 3.13 y DuckDB 2.0 sobre el lote real recibido: 987 registros, 656 valores cero, 262 títulos con iconos y 10 candidatos por encabezados consecutivos. Se verificaron consultas SQL, exportación y relectura de Parquet, normalización del formato Mongo, JSONL plano y gzip, entrada inválida y límite de tamaño. El cuaderno distribuido está sin salidas ni datos incrustados.

No se ha ejecutado en Deepnote Cloud ni se han probado conexiones reales a Azure/MongoDB en esta entrega. La creación del proyecto y el beneficio educativo siguen pendientes de acceso a la cuenta. No se agregan tareas programadas.
