---
name: evaluate-skill
description: Audita un SKILL.md existente de G7B con el evaluador local de Codex cuando se pide revisar estructura, descripción, enlaces, tamaño o prioridades de corrección, o preparar su evaluación.
---

# Auditar una habilidad del repositorio

Desde la raíz de G7B, resuelve el nombre a `.agents/skills/<nombre>`. El evaluador original requiere Git y Node.js 20 o posterior. Su análisis estático se ejecuta localmente. Para preparar la primera copia del evaluador se necesita acceso a GitHub. El directorio `resultados/` está excluido de Git.

1. Comprueba si `resultados/upstream-openai/plugins/plugin-eval/scripts/plugin-eval.js` existe y si `git -C resultados/upstream-openai rev-parse HEAD` devuelve la revisión fijada abajo. Si ya coincide, pasa al análisis. Para una primera copia ejecuta estos comandos en orden, deteniéndote ante cualquier error:

   ~~~console
   git clone --depth=1 --filter=blob:none --sparse --no-checkout https://github.com/openai/plugins.git resultados/upstream-openai
   git -C resultados/upstream-openai sparse-checkout set --cone plugins/plugin-eval
   git -C resultados/upstream-openai fetch --depth=1 origin 981b02c0c44058b595f3b4180002c3ae3c806d40
   git -C resultados/upstream-openai checkout --detach FETCH_HEAD
   git -C resultados/upstream-openai rev-parse HEAD
   ~~~

   Si existe un checkout de otra versión o con cambios locales, prepara la copia en otra carpeta y ajusta la ruta del comando. Confirma el SHA antes de ejecutar el evaluador.

2. Sustituye la ruta de ejemplo por la habilidad solicitada y ejecuta:

   ~~~console
   node resultados/upstream-openai/plugins/plugin-eval/scripts/plugin-eval.js analyze .agents/skills/revisar-calibracion-site --format markdown
   ~~~

3. Entrega los hallazgos respaldados por una ruta concreta e indica qué corregir primero. Indica si un aviso se debe a una referencia compartida en G7B. Un análisis estático comprueba estructura; la selección por un agente se mide mediante peticiones reales con `$writing-skills`.
4. Si la petición incluye preparar un benchmark, llama al mismo ejecutable con `init-benchmark <ruta>` y revisa sus casos antes de medir.

[Evaluador y procedimiento originales de OpenAI](https://github.com/openai/plugins/blob/981b02c0c44058b595f3b4180002c3ae3c806d40/plugins/plugin-eval/skills/evaluate-skill/SKILL.md)
