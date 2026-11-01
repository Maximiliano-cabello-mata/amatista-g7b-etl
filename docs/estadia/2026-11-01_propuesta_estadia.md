# Propuesta de estadía (versión integrada Amatista + G7B)

Fecha: 2026-11-01. Borrador para adaptar al formato y al reglamento de estadías de la universidad. Une los dos proyectos en **una sola pregunta**: Amatista es la intervención educativa y G7B la medición y la adaptación. Ver [VISION.md](../VISION.md).

## 1. Título tentativo

*Adaptación del entorno de aprendizaje de Blender al hardware del estudiante mediante perfiles basados en mediciones: estudio en los laboratorios de [universidad].*

## 2. Problema

- **Requisitos que suben:** cada versión de Blender pide más. La 4.0 exige OpenGL 4.3 y dejó fuera gráficas como la Intel HD 4000; la 5.0 pide GeForce 900, AMD GCN 4 o Intel Kaby Lake como mínimo.
- **Acceso escaso en México:**
  - el 44.7 % de los hogares tiene computadora (ENDUTIH 2025);
  - el 53.7 % de las escuelas públicas de educación básica no tiene computadoras (SEP 2025-26).
- **Nadie mide lo que importa para aprender:** los datos abiertos que existen (Blender Open Data) solo miden el render, no la vista 3D ni la edición. Nadie ajusta Blender al equipo con datos medidos.

Fuentes: [investigación del estado del arte](../investigacion/2026-11-01_novedad_kernel_3d.md). Algunas cifras vienen de fragmentos de búsqueda y hay que verificarlas antes de citarlas.

## 3. Pregunta y hipótesis

- **Pregunta principal (una sola):** ¿adaptar el entorno de Blender al equipo, con un perfil de ajustes elegido con mediciones, mejora la fluidez y el desempeño de los estudiantes en una práctica de modelado 3D en equipos modestos?
- **Hipótesis:** con el perfil, la vista 3D alcanza la fluidez definida (30 fps o más de mediana) en los equipos N2, y los estudiantes terminan la práctica en menos tiempo y con menos pistas que con la configuración por omisión.
- **Secundarias,** que se reportan sin cambiar la pregunta: usabilidad percibida (SUS) y diferencias por nivel de equipo.

## 4. Objetivos

1. Medir con la sonda de G7B todos los equipos del laboratorio y clasificarlos en niveles N1 a N4.
2. Elegir con los datos un perfil de ajustes por nivel.
3. Integrar en el add-on de Amatista la detección del nivel, la aplicación del perfil y el registro de eventos de la práctica, con consentimiento.
4. Hacer un experimento con estudiantes: la misma práctica con y sin perfil.
5. Publicar el dataset del laboratorio, sin datos personales, con DOI.
6. Entregar a la universidad un diagnóstico de sus laboratorios: qué versión de Blender y qué ajustes convienen en cada equipo.

## 5. Método

- **Diseño:** intra-sujetos. Cada estudiante hace dos variantes equivalentes de la práctica, una con perfil y otra sin él, en orden aleatorio (contrabalanceo).
- **Participantes:** de 10 a 20 estudiantes, con consentimiento informado.
- **Variables:**

| Variable | Cómo se mide |
|---|---|
| Fluidez | fps de la vista 3D (sonda y extensión del Corazón) |
| Tiempo por paso y total | Eventos del Corazón |
| Pistas usadas y señales perdidas | Eventos del Corazón |
| Finalización | Si se cumple la práctica (validación de Amatista) |
| Usabilidad percibida | Cuestionario SUS (System Usability Scale) |

- **Análisis:** pruebas para datos pareados (Wilcoxon de rangos con signo), con el tamaño del efecto. Un resultado sin diferencia también se reporta.
- **Ética y datos:** aviso de privacidad, consentimiento que se puede retirar, identificadores anónimos, y nada personal fuera de Amatista.

## 6. Entregables

1. La memoria de la estadía.
2. El add-on con detección del nivel, perfiles y registro de eventos (GPL).
3. El dataset del laboratorio con DOI.
4. El diagnóstico de laboratorios para la universidad.
5. Una presentación, y si el resultado lo permite, un artículo para un congreso de tecnología educativa o de interacción humano-computadora.

## 7. Cronograma (17 semanas aproximadas)

| Semanas | Actividad |
|---|---|
| 1–2 | Protocolo, permiso del laboratorio, aviso de privacidad y consentimiento |
| 3–5 | Medición de todos los equipos del laboratorio con la sonda; clasificación por nivel |
| 6–8 | Perfiles por nivel con los datos; detección y registro de eventos en el add-on |
| 9 | Prueba piloto con 2 o 3 personas |
| 10–12 | Experimento con estudiantes |
| 13–14 | Análisis estadístico; publicación del dataset |
| 15–17 | Memoria, diagnóstico para la universidad y presentación |

## 8. Estructura de la memoria

1. Problema.
2. Estado del arte.
3. Arquitectura: Amatista y G7B, sus contratos y el ciclo de retroalimentación.
4. G7B: la sonda, los niveles y los perfiles.
5. Amatista: la práctica, el add-on y los eventos.
6. Experimento.
7. Resultados.
8. Limitaciones y trabajo futuro: Geoda, el planificador, el editor web y el centro 3D.

## 9. Lo que no entra en la estadía

El lago de texto, los foros, arXiv, el editor web, el planificador, Camber, Heroku y el resto de las nubes. **Son el proyecto grande, no la estadía:** van en "trabajo futuro".

## 10. Riesgos

| Riesgo | Respuesta |
|---|---|
| Pocos participantes | Acordar el grupo con un profesor desde la semana 1 |
| Equipos del laboratorio muy parecidos | Comparar perfiles dentro de un nivel; reportarlo como limitación |
| Uso de IA en el desarrollo | Declararlo según la política de la universidad; poder explicar cada parte en la defensa |
| Resultado negativo | Es válido si el método es bueno; se reporta igual |
| Estadía dentro de la escuela | Confirmar en el reglamento que un departamento puede fungir como organización receptora |

## 11. Tareas relacionadas

En el tablero de Amatista, versión **v3.5.0 · Centro 3D con G7B**: protocolo, aviso de privacidad, detección del nivel en el add-on, extensión observadora del Corazón, exportación agregada, elección de la práctica y recomendaciones.
