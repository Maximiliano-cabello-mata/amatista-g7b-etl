---
name: data-quality-frameworks
description: Diseña, contrasta o amplía contratos de calidad de la telemetría G7B cuando se pide validar pares métrica y unidad, cambios de esquema, consistencia entre columnas o antigüedad de un lote.
---

# Revisar un contrato de datos

Identifica el productor, el contrato versionado, la unidad de observación y el archivo. Para conteos por fuente y estado usa `$revisar-lote-telemetria`. Para evaluar las reglas del lote, sigue estos pasos.

1. Localiza la regla en el [estándar](../../../docs/ESTANDAR_TELEMETRIA.md), el [validador del cubo](../../../g7b_almacen/cubo.py) o la [sonda de Blender](../../../sonda/g7b_sonda.py). Distingue reglas vigentes y propuestas.
2. Para contrastar los pares de métrica y unidad del cubo local, ejecuta desde la raíz con el entorno DuckDB de G7B:

   ~~~console
   python -m herramientas.revisar_contrato_unidades "ruta/al/cubo.duckdb"
   ~~~

3. Informa filas comprobadas, unidad observada y esperada para cada discrepancia y cuántas quedan sin regla. Con cero filas indica «sin observaciones». Una métrica nueva queda pendiente de identificar a su productor. El resultado de unidades describe un solo control del contrato.
4. Para otro control, identifica el campo, la condición verificable y un ejemplo válido y otro defectuoso. Para evaluar puntualidad usa la fecha de referencia, zona horaria y plazo acordados para esa fuente. Si falta el plazo, informa la antigüedad observada y deja la decisión pendiente.
5. Devuelve los resultados al responsable de auditoría. La aprobación y los cambios de estado siguen el flujo de Amatista IA.

[Patrones originales de wshobson/agents](https://github.com/wshobson/agents/blob/c96b5f6552dba32e4492307493ee613581430715/plugins/data-engineering/skills/data-quality-frameworks/SKILL.md)

[Patrones de validación y ejemplos de contratos](../../../docs/referencias-habilidades/data-quality-frameworks/details.md) · [Licencia de la referencia](../../../docs/referencias-habilidades/data-quality-frameworks/LICENSE)
