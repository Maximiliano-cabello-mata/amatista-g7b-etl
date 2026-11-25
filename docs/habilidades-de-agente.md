# Habilidades de los agentes de G7B

Un agente que abra este repositorio puede invocar una habilidad por su nombre. En Codex, escribe `$revisar-calibracion-site` o `$revisar-lote-telemetria`. También puede seleccionar una habilidad a partir de la descripción de la petición. Las dos habilidades de revisión calculan resultados que se pueden reproducir desde la terminal.

| Petición de ejemplo | Habilidad | Qué debe devolver |
|---|---|---|
| «¿Site alcanzó el 80 % en las páginas que nunca había visto?» | [Revisar calibración de Site](../.agents/skills/revisar-calibracion-site/SKILL.md) | Fuente, versión, censo de bloques y límite de confianza de la reserva |
| «¿Cuántas mediciones de la sonda están en revisión en este archivo?» | [Revisar lote de telemetría](../.agents/skills/revisar-lote-telemetria/SKILL.md) | Conteos por fuente y estado del cubo indicado |
| «¿Hay IDs duplicados o mediciones sin unidades en este cubo?» | Revisar lote de telemetría | Repeticiones, IDs ausentes, unidades ausentes y valores inválidos |
| «Despliega la araña» o «arma una lección de Blender» | Ninguna de estas dos | La petición corresponde a otro procedimiento |

## Habilidades de la comunidad integradas en G7B

Estas cuatro adaptaciones se descubren en el repositorio junto a las dos revisiones originales. Cada una enlaza la revisión exacta de su fuente. Las tres primeras incluyen referencias originales y su licencia MIT en `docs/referencias-habilidades/` para consultarlas en local. Los agentes las abren solo si necesitan profundizar en una técnica. Los agentes pueden invocarlas por nombre o seleccionarlas por la descripción.

| Petición | Habilidad | Cómo reconocer el resultado |
|---|---|---|
| «Diseña pruebas para redactar una habilidad que resuma lotes fallidos» | [writing-skills](../.agents/skills/writing-skills/SKILL.md) | Casos con y sin activación y una comparación de respuestas antes y después |
| «Define el contrato que detecta unidades incompatibles en el cubo» | [data-quality-frameworks](../.agents/skills/data-quality-frameworks/SKILL.md) | Filas conformes, incompatibles y sin regla, con el productor y la unidad esperada |
| «¿Son comparables los pilotos para afirmar que el nuevo selector generaliza mejor?» | [scientific-critical-thinking](../.agents/skills/scientific-critical-thinking/SKILL.md) | Unidad independiente, condiciones comparables, incertidumbre y alcance de la afirmación |
| «Audita el SKILL.md de conteos y prioriza sus problemas de estructura» | [evaluate-skill](../.agents/skills/evaluate-skill/SKILL.md) | Informe del evaluador original con hallazgos y prioridades para ese archivo |

El control del cubo usa el entorno DuckDB de G7B. Las guías de redacción y evaluación de evidencia se pueden leer en local. La primera preparación de `evaluate-skill` usa Git y acceso a GitHub para descargar el CLI en una revisión fija. Luego su análisis estático solo necesita Node.js 20 o superior y los archivos locales.

Para repetir la prueba de selección, presenta las cuatro peticiones de esta tabla y las cuatro de la tabla anterior, una por turno y sin mencionar la habilidad esperada. Registra qué eligió el agente y si entregó el resultado esperado. Para un control fuera de alcance, pide por separado «enséñame a modelar una mesa» y «pon en marcha la araña de producción». Evalúa ambas respuestas sin iniciar trabajos de producción.

## Cómo crear la siguiente

1. Elige una pregunta real que el equipo repita. Escribe un ejemplo de entrada y las cifras, archivos o decisiones que demostrarían una respuesta correcta.
2. Crea `.agents/skills/<nombre>/SKILL.md`. En el encabezado YAML usa `name` con el mismo nombre que la carpeta y una `description` que mencione cuándo corresponde usarla. En el cuerpo especifica qué datos necesita, qué ejecutar y cómo reconocer evidencia insuficiente.
3. Reutiliza las consultas y funciones del repositorio. Conserva en el archivo principal lo que el agente necesita para empezar y enlaza los criterios de dominio donde ya se mantienen. Un procedimiento repetible puede ir en un script. Estas dos habilidades llaman módulos desde la raíz para compartirlos con las pruebas.
4. Prueba la operación con un lote conocido y con uno incompleto o contradictorio. Después, en el agente de destino, ensaya peticiones reales sin mencionar la habilidad y alguna fuera de alcance. Registra por separado la selección correcta y la exactitud de la respuesta. Para medir si la habilidad mejora al agente, usa las mismas peticiones con y sin la habilidad.
5. Versiona junto al código los criterios de aceptación y ejemplos. Aquí se reproducen las pruebas de los dos módulos con `python -m pytest -q pruebas/test_habilidades_agentes.py` en el entorno de pruebas con DuckDB.

[Especificación de Agent Skills](https://agentskills.io/specification) · [Descubrimiento de habilidades en Codex](https://developers.openai.com/codex/skills/) · [Ejemplo de creación y evaluación en la comunidad](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
