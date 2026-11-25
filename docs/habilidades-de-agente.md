# Habilidades de los agentes de G7B

Un agente que abra este repositorio puede invocar una habilidad por su nombre. En Codex, escribe `$revisar-calibracion-site` o `$revisar-lote-telemetria`. También puede seleccionar una habilidad a partir de la descripción de la petición. Cada tarea produce un informe que se puede reproducir desde la terminal.

| Petición de ejemplo | Habilidad | Qué debe devolver |
|---|---|---|
| «¿Site alcanzó el 80 % en las páginas que nunca había visto?» | [Revisar calibración de Site](../.agents/skills/revisar-calibracion-site/SKILL.md) | Fuente, versión, censo de bloques y límite de confianza de la reserva |
| «¿Cuántas mediciones de la sonda están en revisión en este archivo?» | [Revisar lote de telemetría](../.agents/skills/revisar-lote-telemetria/SKILL.md) | Conteos por fuente y estado del cubo indicado |
| «¿Hay IDs duplicados o mediciones sin unidades en este cubo?» | Revisar lote de telemetría | Repeticiones, IDs ausentes, unidades ausentes y valores inválidos |
| «Despliega la araña» o «arma una lección de Blender» | Ninguna de estas dos | La petición corresponde a otro procedimiento |

## Cómo crear la siguiente

1. Elige una pregunta real que el equipo repita. Escribe un ejemplo de entrada y las cifras, archivos o decisiones que demostrarían una respuesta correcta.
2. Crea `.agents/skills/<nombre>/SKILL.md`. En el encabezado YAML usa `name` con el mismo nombre que la carpeta y una `description` que mencione cuándo corresponde usarla. En el cuerpo especifica qué datos necesita, qué ejecutar y cómo reconocer evidencia insuficiente.
3. Reutiliza las consultas y funciones del repositorio. Conserva en el archivo principal lo que el agente necesita para empezar y enlaza los criterios de dominio donde ya se mantienen. Un procedimiento repetible puede ir en un script. Estas dos habilidades llaman módulos desde la raíz para compartirlos con las pruebas.
4. Prueba la operación con un lote conocido y con uno incompleto o contradictorio. Después, en el agente de destino, ensaya peticiones reales sin mencionar la habilidad y alguna fuera de alcance. Registra por separado la selección correcta y la exactitud de la respuesta. Para medir si la habilidad mejora al agente, usa las mismas peticiones con y sin la habilidad.
5. Versiona junto al código los criterios de aceptación y ejemplos. Aquí se reproducen las pruebas de los dos módulos con `python -m pytest -q pruebas/test_habilidades_agentes.py` en el entorno de pruebas con DuckDB.

[Especificación de Agent Skills](https://agentskills.io/specification) · [Descubrimiento de habilidades en Codex](https://developers.openai.com/codex/skills/) · [Ejemplo de creación y evaluación en la comunidad](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
