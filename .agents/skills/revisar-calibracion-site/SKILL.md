---
name: revisar-calibracion-site
description: Evalúa si la araña documental Site de G7B alcanza la meta de utilidad del 80 % cuando se pide revisar un piloto, sus etiquetas, la precisión en páginas inéditas o la evidencia para publicación automática.
---

# Revisar la calibración de Site

Usa esta habilidad con un informe archivado y el archivo de etiquetas que le corresponde. Si te dan otro lote, usa las dos rutas de ese lote. Para el piloto versionado de Blender 4.5, ejecuta desde la raíz del repositorio con Python 3:

~~~console
python -m herramientas.revisar_calibracion_site algoritmos/documentacion/resultados-site-4.1.json algoritmos/documentacion/auditoria.json
~~~

1. Identifica la fuente, el modelo y el revisor. El comando cruza por ID y URL los bloques de muestra con las etiquetas y usa el cálculo de Wilson del proyecto. La pertenencia a la reserva proviene de la auditoría archivada. Consulta el plan de selección si alguien cuestiona la independencia de las páginas.
2. Informa por separado las páginas con candidatos sobre las visitadas, los bloques útiles sobre los revisados y las muestras útiles sobre las páginas de reserva. Expresa los tres denominadores. Explica qué fuente y qué versión cubre el resultado.
3. Para la meta del 80 %, comunica el límite inferior unilateral de Wilson al 95 % y la decisión del campo `reserva.habilitada`. Con cero muestras, informa «sin evidencia de calibración». Si el comando falla, informa la discrepancia y deja la conclusión pendiente. La revisión termina al informar el resultado.
4. Si te piden una mejora respecto de otra versión, comprueba que ambas se evaluaron en páginas independientes comparables, con la misma rúbrica y unidad de muestreo. Indica qué comparación permiten los datos.

El estándar y los límites del estudio están en [la guía de Site](../../../algoritmos/documentacion/site-4.md). Para contar mediciones de rendimiento, usa la habilidad de telemetría.
