---
name: revisar-lote-telemetria
description: Inspecciona un cubo DuckDB de telemetría G7B cuando se pregunta qué mediciones llegaron, cuántas están aceptadas o en revisión por fuente, o si un lote presenta IDs repetidos, unidades ausentes o valores inválidos.
---

# Revisar un lote de telemetría

Usa el archivo DuckDB del lote que indique el usuario. Para afirmaciones sobre el lago actual hace falta una exportación identificada y su fecha. Si solo hay un cubo histórico, indica esa procedencia. Desde la raíz del repositorio, usa el entorno Python del cubo con DuckDB de [requirements-cubo.txt](../../../requirements-cubo.txt). Sustituye la ruta entre comillas por la real:

~~~console
python -m herramientas.revisar_lote_telemetria "ruta/al/cubo.duckdb"
~~~

1. Lee el total directamente de `mediciones`. Las tablas de hechos y las vistas de resumen pueden contener las mismas observaciones. El comando abre el archivo en modo de solo lectura.
2. Presenta los conteos por fuente y estado tal como están almacenados. Identifica las aceptadas, las que requieren revisión y cualquier otro estado presente. Si una partición esperada no aparece, indícalo como ausencia en este lote.
3. Informa filas, IDs distintos, filas sin ID y repeticiones adicionales de un ID. Revisa también unidades vacías y valores ausentes o no finitos. Con cero filas, informa «lote vacío». Ante un esquema incompatible o un archivo ausente, incluye el motivo y deja los conteos pendientes.
4. Identifica el archivo o lote en la respuesta. Un valor de benchmark, un FPS y un tiempo de edición tienen unidades y condiciones distintas. Para comparar rendimiento se necesitan métricas, unidades, perfiles y condiciones compatibles.

El significado de las mediciones está en [el estándar de telemetría](../../../docs/ESTANDAR_TELEMETRIA.md). Para evaluar páginas útiles del manual, usa la habilidad de calibración de Site.
