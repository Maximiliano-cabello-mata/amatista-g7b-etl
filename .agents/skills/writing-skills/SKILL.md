---
name: writing-skills
description: Crea o modifica habilidades de los agentes de G7B y diseña pruebas de selección en lenguaje natural cuando alguien pide redactar una habilidad, corregir su activación o comparar el comportamiento antes y después.
---

# Crear y probar habilidades en G7B

Pide un ejemplo del error solo si la petición y el repositorio carecen de uno. Abre la habilidad que ya cubre la tarea y comprueba si se puede mejorar allí.

1. Escribe una petición representativa, otra parecida que corresponde a otra habilidad y una fuera del catálogo. Fija por adelantado la habilidad esperada, el resultado comprobable y el archivo de entrada.
2. Prueba las peticiones con el catálogo actual, sin mostrar los nombres esperados ni los criterios al agente. Conserva las respuestas. Un ejemplo de fallo es confundir «contar mediciones» con «diseñar el contrato de una medición».
3. Crea o modifica `.agents/skills/<nombre>/SKILL.md`. Incluye el nombre, una descripción que indique cuándo usarla, el comando o procedimiento reproducible y cómo informar evidencia insuficiente. Reutiliza los módulos del repositorio.
4. Repite las mismas peticiones en una sesión nueva con el catálogo modificado. Puntúa por separado la elección de habilidad y la exactitud del resultado. Una selección correcta seguida de cifras incorrectas es un fallo de ejecución. Indica número de casos, agente utilizado y alcance de la prueba.
5. Comprueba los enlaces y la estructura con `$evaluate-skill`. Entrega el cambio acompañado por el caso que corrige.

[Guía y casos del equipo](../../../docs/habilidades-de-agente.md) · [Método original de obra/superpowers](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/writing-skills/SKILL.md)

[Pruebas de comportamiento del agente](references/testing-skills-with-subagents.md) · [Licencia de la referencia](references/LICENSE)
