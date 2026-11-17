# Qué IA usar en G7B: local, Gemini gratuito u otra (17 de noviembre de 2026)

**Decisión propuesta:** IA **local por omisión** para todo el trabajo por lotes con datos públicos, que es la mayor parte. Las APIs gratuitas en la nube (Gemini y GitHub Models) sirven como **acelerador y segunda opinión**, nunca como pieza de la que dependa el flujo. **Ningún dato de estudiantes va a una capa gratuita.** El asistente para estudiantes se decide cuando haya piloto, con una API de pago que no use los datos para entrenar.

**¿Es práctico tomar este camino ahora?** Sí, para etiquetar y extraer información de documentos públicos: no necesita respuesta inmediata y los datos no son sensibles. Todavía no para el asistente que usarán los estudiantes: primero hacen falta privacidad, una evaluación y usuarios reales.

**El primer paso no es elegir un modelo, sino armar un conjunto de prueba.** Son 150 a 200 documentos del lago etiquetados a mano: si sirven, qué pregunta del plan responden y qué hechos contienen. Sin eso no hay forma de saber qué modelo funciona mejor ni de medir los errores ([reporte de arañas](2026-11-17_aranas_nicho/REPORTE.md), decisión 10).

---

## 1. Para qué necesita IA G7B

| Tarea | Volumen | ¿Necesita respuesta inmediata? | ¿Datos sensibles? |
|---|---|---|---|
| A. Etiquetar documentos (reemplazar el filtro por palabras clave) | Unos 10 000 de entrada y unos 200 al día después | No, va por lotes | No: documentación pública |
| B. Extraer hechos de reportes de error y foros (versión, GPU, síntoma, solución, cita) | Cientos al día | No | No: contenido público |
| C. Traducir al español lo que falte | Miles de fragmentos, una vez | No | No |
| D. Calcular vectores (*embeddings*) para buscar y detectar duplicados | Todo el lago | No | No |
| E. Asistente para estudiantes con citas (RAG) | Depende del uso | **Sí** | **Sí**: preguntas y telemetría de estudiantes |

A, B, C y D son el 95 % del trabajo y no tienen requisitos difíciles. Solo E necesita cuidado.

## 2. Las opciones, con lo que se pudo verificar

| Opción | Costo | Límites | Uso de los datos | Comentario |
|---|---|---|---|---|
| **Gemini API, capa gratuita** | US$0 | **Inestables.** Google ya no publica las cifras por modelo en su página. Las fuentes secundarias van de 20–50 solicitudes al día para Flash, tras recortes de 50–80 % a fines de 2025, a unas 1 000 al día para Flash-Lite. Hay que confirmarlo en la consola de AI Studio | **Google puede usar lo enviado para mejorar sus productos, y lo pueden leer revisores humanos.** Sus términos piden no enviar información personal o confidencial a la capa gratuita ([términos](https://ai.google.dev/terms), [registro de datos](https://ai.google.dev/gemini-api/docs/logs-policy)) | Sirve para documentos públicos (A–C). **No sirve para el asistente ni para la telemetría.** No conviene que el flujo dependa de ella: los límites cambian sin aviso |
| Gemini API de pago | Bajo (por token) | Altos | No usa los datos para mejorar productos | Candidata para el asistente cuando haya piloto |
| **GitHub Models** (desde Actions con el token del flujo) | US$0 | Para cuentas gratuitas: 150 solicitudes al día, 15 por minuto, 8 000 tokens de entrada y 4 000 de salida por solicitud ([docs oficiales](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models)) | Pensado para prototipos | Ventaja: no hay que guardar ninguna clave nueva, se activa con `models: read`. Alcanza para lo incremental del día, no para la carga inicial |
| **Local en GitHub Actions** (Ollama o llama.cpp en CPU) | US$0: el repositorio es público y los minutos son gratis | Solo la velocidad. Un modelo de 4B cuantizado da del orden de 10 a 15 tokens por segundo en un CPU de escritorio; **en el runner de GitHub no está medido** ([guías CPU](https://insiderllm.com/guides/cpu-only-llms-what-actually-works/), [itsfoss](https://itsfoss.com/testing-local-llms-without-gpu)). Cada trabajo dura como máximo 6 horas | Nada sale del entorno | Base recomendada para A, B y D. Para etiquetar, las respuestas son cortas (JSON), y lo que más tarda es leer el documento. Estimación por medir: unos 1 000 documentos por trabajo de 6 horas |
| Local en la VM de Oracle | US$0 si es la instancia Always Free Ampere A1 (4 OCPU, 24 GB) | Estimación de 8 a 12 tokens por segundo con un modelo de 7B, sin benchmark publicado para ese tamaño ([Oracle/Ampere](https://blogs.oracle.com/ai-and-datascience/post/smaller-llama-llm-models-cost-efficient-ampere-cpus), [EaseCloud](https://blog.easecloud.io/ai-cloud/launch-oracle-cloud-llms-in/)) | Nada sale del entorno | La comparte la API de Amatista. Posible para un asistente con poco tráfico, y lento. Hay que confirmar qué tipo de instancia es |
| APIs de pago por lotes (Gemini, OpenAI, Anthropic) | Bajo, con 50 % de descuento en lotes | Altos | No se usan los datos para entrenar en las capas de pago | Opción para la carga inicial si lo local resulta demasiado lento, y para la segunda opinión de calidad |

Modelos locales candidatos: Qwen3 4B, Gemma 3 4B y NuExtract (4B, Apache-2.0) para extraer; un modelo de 7–8B si el equipo aguanta. Para vectores, bge-m3 o multilingual-e5, que funcionan en español ([notas de extracción](2026-11-17_aranas_nicho/notas_extraccion_conocimiento.md)).

## 3. Recomendación por tarea

| Tarea | Principal | Respaldo | Por qué |
|---|---|---|---|
| A. Etiquetar documentos | **Modelo local en Actions** sobre una muestra; después, un **clasificador pequeño** (SetFit) que corre en `procesar` en milisegundos. El modelo de IA solo revisa lo nuevo o lo dudoso | Gemini o GitHub Models para comparar en los casos dudosos | Es el patrón de FineWeb-Edu: la IA etiqueta una muestra y un modelo pequeño escala. Sin depender de límites externos |
| B. Extraer hechos | **Local**, con esquema plano y cita literal obligatoria | Segunda extracción con Gemini o GitHub Models para comparar campo por campo | La doble extracción es parte de la validación ([reporte](2026-11-17_aranas_nicho/REPORTE.md), decisiones 9 y 10) |
| C. Traducir | Gemini (gratuito) o local | — | Son datos públicos con CC BY-SA: la traducción se publica con la misma licencia y se marca como automática |
| D. Vectores | **Local** (bge-m3 o multilingual-e5) | — | Corre en CPU, es gratis y funciona en español |
| E. Asistente para estudiantes | Por decidir en el piloto: **API de pago** sin uso de datos, o un modelo local en Oracle si el tráfico es bajo | — | No puede ir a una capa gratuita: los datos de estudiantes se usarían para entrenar y los podrían revisar personas |

## 4. Por qué no apostar todo a Gemini gratuito

1. **Los límites cambian sin aviso.** Las cifras publicadas van de 20 a 1 500 solicitudes al día según la fuente y la fecha, y Google dejó de publicarlas. Un flujo 24/7 que dependa de eso se cae solo, que es justo lo que pasó con los horarios de GitHub.
2. **Privacidad.** En la capa gratuita los datos se usan para mejorar los productos de Google y los pueden leer revisores humanos. Es aceptable para el manual público, pero no para preguntas ni telemetría de estudiantes. En México eso choca con la ley de protección de datos personales en posesión de particulares; conviene revisarlo con quien lleve la parte legal.
3. **No hace falta.** El trabajo es por lotes y los minutos de Actions son gratis. Lo local es más lento, pero no tiene límites que cambien.

Como **acelerador** sí conviene: es útil para la segunda opinión en la validación y para las traducciones.

## 5. Plan sin código, en orden

1. **Conjunto de prueba:** 150 a 200 documentos del lago etiquetados a mano por el equipo, incluidos rechazados y casos dudosos. Lo hacemos nosotros; ningún modelo lo reemplaza.
2. **Confirmar límites:** abrir AI Studio y anotar los límites reales de Flash y Flash-Lite de la cuenta. Confirmar qué tipo de instancia es la VM de Oracle.
3. **Prueba de modelos** (cuando se retome el código): 2 o 3 modelos locales y Gemini Flash-Lite sobre el conjunto de prueba. Se mide acierto, velocidad en el runner de Actions y costo.
4. Elegir con esos números. Escribirlo aquí como decisión, con la fecha.

## Fuentes

- Gemini: [términos adicionales](https://ai.google.dev/terms) · [registro y uso de datos](https://ai.google.dev/gemini-api/docs/logs-policy) · [archivo de términos 2025](https://ai.google.dev/gemini-api/terms-archive/terms_10_07_25) · límites, secundarias y contradictorias: [pecollective (abr. 2026)](https://pecollective-com.pages.dev/tools/gemini-free-tier-guide/), [agentdeals (abr. 2026)](https://agentdeals.dev/gemini-api-pricing-changes), [yingtu](https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026), [scriptbyai](https://www.scriptbyai.com/gemini-api-free-tier-limits/)
- GitHub Models: [prototipos con modelos (docs)](https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models) · [facturación](https://docs.github.com/en/billing/concepts/product-billing/github-models) · [modelos en proyectos de código abierto](https://github.blog/ai-and-ml/llms/solving-the-inference-problem-for-open-source-ai-projects-with-github-models/)
- Modelos locales en CPU: [insiderllm](https://insiderllm.com/guides/cpu-only-llms-what-actually-works/) · [itsfoss](https://itsfoss.com/testing-local-llms-without-gpu) · [computingforgeeks](https://computingforgeeks.com/ollama-local-llm-fedora-cpu/)
- Oracle Ampere: [Llama pequeño en Ampere](https://blogs.oracle.com/ai-and-datascience/post/smaller-llama-llm-models-cost-efficient-ampere-cpus) · [Llama 3 en A1](https://blogs.oracle.com/ai-and-datascience/post/introducing-meta-llama-3-on-oci-ampere-a1) · [EaseCloud](https://blog.easecloud.io/ai-cloud/launch-oracle-cloud-llms-in/)
