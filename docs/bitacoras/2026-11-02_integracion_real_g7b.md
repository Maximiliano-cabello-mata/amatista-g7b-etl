# G7B — Primera integración real de extremo a extremo

**Fecha:** 2 de noviembre de 2026 (México; ejecuciones registradas en UTC el 3 de noviembre)  
**Repositorio:** [Maximiliano-cabello-mata/amatista-g7b-etl](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl)  
**Rama probada:** `main`  
**Estado:** Primera integración real completada correctamente

---

## 1. Resumen ejecutivo

G7B es un sistema destinado a reunir, validar y organizar conocimiento técnico sobre herramientas y procesos 3D. Su objetivo es construir una base de conocimiento verificable, con información sobre fuentes, versiones y licencias, que posteriormente pueda utilizarse en Amatista y en otros componentes del ecosistema.

Durante esta jornada se comprobó por primera vez el funcionamiento real de la cadena:

**Zyte → Azure Blob Storage → G7B Embudo de calidad → Azure Plata → MongoDB Atlas**

El sistema extrajo previamente información mediante la araña `blender_docs`, recuperó un trabajo terminado de Zyte, almacenó 2,353 registros en Azure, evaluó su contenido y publicó 987 documentos nuevos en MongoDB.

La operación se realizó mediante GitHub Actions, sin ejecutar manualmente los programas Python en un servidor permanente.

### Resultados principales

| Indicador | Resultado |
|---|---:|
| Registros importados desde Zyte | 2,353 |
| Documentos aceptados | 987 |
| Documentos enviados a revisión | 52 |
| Documentos rechazados | 1,314 |
| Documentos nuevos publicados en MongoDB | 987 |
| Documentos actualizados en esta publicación | 0 |
| Archivos de plata publicados | 1 |

La ejecución de publicación terminó correctamente. Esto demuestra el funcionamiento básico del flujo de extremo a extremo; no representa todavía una certificación de calidad de todos los documentos ni una prueba de producción continua.

## 2. Infraestructura utilizada

### GitHub

Repositorio central del código, documentación, configuración y automatizaciones.

- Aloja los módulos Python, las arañas y el catálogo de fuentes.
- Ejecuta las tareas mediante GitHub Actions.
- Administra las versiones mediante ramas, commits y pull requests.
- Conserva los registros de cada ejecución.
- Proporciona un entorno denominado `amatista1` para las credenciales utilizadas por los workflows.

### Zyte

Servicio encargado de ejecutar las arañas de extracción web.

Configuración verificada:

- Proyecto: `883618`
- Araña utilizada: `blender_docs`
- Trabajo importado: `883618/1/13`
- Estado del trabajo: `finished`

La ejecución probada recuperó un trabajo previamente terminado. No se inició una araña nueva durante el simulacro ni durante la importación.

### Microsoft Azure

Almacena la información obtenida y procesada.

- Grupo de recursos: `g7b`
- Cuenta de almacenamiento: `g7blago09b52a0e`
- Contenedor: `lago`

Se utilizan zonas lógicas:

- **Bronce:** registros originales importados.
- **Plata:** información procesada y clasificada.
- **Oro:** publicación del conocimiento aceptado en MongoDB.

Archivo de bronce importado:

`bronce/zyte/blender_docs/2026-11-01/883618-1-13.jsonl.gz`

Archivo de plata publicado:

`plata/aceptados/zyte/blender_docs/2026-11-01/883618-1-13.jsonl.gz`

### MongoDB Atlas

Destino de los documentos aceptados.

- Base de datos: `conocimiento_3d`
- Colección utilizada por el publicador: `documentos`
- Documentos nuevos durante la prueba: 987

Antes de la publicación, el diagnóstico informó cinco documentos existentes y 56 registros en `foros_crudos`. El conteo posterior total de cada colección debe verificarse directamente en MongoDB.

## 3. Cómo funciona la arquitectura

### Etapa A. Vigilancia de fuentes

GitHub Actions ejecuta `g7b_ingesta.vigilar`.

El programa consulta el catálogo de fuentes y determina si corresponde revisar una fuente o si detecta cambios.

En nuestra prueba:

- Fuente examinada: `blender-manual`
- Cambio detectado: sí
- URLs reportadas: 1
- Modalidad: simulacro
- Resultado: exitoso

En modo simulacro, el sistema no escribe el estado ni inicia nuevas extracciones.

### Etapa B. Extracción con Zyte

La araña `blender_docs` se ejecuta en la infraestructura de Zyte. Sus resultados permanecen disponibles para el proceso de importación.

GitHub Actions puede consultar los trabajos terminados utilizando la API del proyecto Zyte.

### Etapa C. Transferencia a Azure Bronce

El programa `g7b_lago.zyte_a_lago` consulta los trabajos de Zyte y compara su estado con el control almacenado en Azure.

Si encuentra un trabajo pendiente, puede descargar sus resultados y almacenarlos en el lago.

La prueba real produjo:

`{"pendientes": 1, "copiados": 1, "registros": 2353, "ya_existian": 0}`

### Etapa D. Embudo de calidad

El programa `g7b_ingesta.procesar` examina los documentos de bronce.

Evalúa aspectos como:

- Relevancia respecto al plan de conocimiento.
- Duplicados exactos y casi duplicados.
- Cantidad y calidad del texto.
- Páginas índice con poco contenido sustantivo.
- Repetición excesiva de contenido.
- Posible desactualización de información.

Los registros se clasifican en tres estados: aceptado, revisión y rechazado.

Resultado:

| Estado | Documentos | Porcentaje |
|---|---:|---:|
| Aceptado | 987 | 41.9% |
| Revisión | 52 | 2.2% |
| Rechazado | 1,314 | 55.8% |

Los criterios se ejecutaron correctamente. Sin embargo, debe revisarse una muestra para medir falsos positivos y falsos rechazos.

### Etapa E. Publicación en MongoDB

El programa `g7b_ingesta.publicar` toma los archivos aceptados de plata y los publica en la base de conocimiento.

Resultado final:

`{"nuevo": 987, "actualizado": 0, "sin_cambios": 0, "archivos": 1}`

Esta es la evidencia principal de que la cadena de datos se completó.

## 4. Qué hace GitHub en G7B

GitHub cumple tres funciones centrales: almacenamiento del código, coordinación del desarrollo y ejecución automatizada.

### Repositorio y ramas

El repositorio contiene el código de G7B, las configuraciones de infraestructura, los workflows y su documentación.

La rama `main` representa el estado integrado que se utilizó durante estas pruebas.

Las ramas de trabajo permiten desarrollar nuevas funciones sin modificar inmediatamente `main`. Los pull requests permiten comparar cambios, ejecutar pruebas y revisar el código antes de integrarlo.

### GitHub Actions

Los archivos YAML de `.github/workflows/` indican a GitHub cuándo ejecutar determinadas tareas y qué comandos debe utilizar.

Flujos comprobados:

| Workflow | Programa | Función |
|---|---|---|
| `vigilar.yml` | `g7b_ingesta.vigilar` | Detectar cambios en fuentes |
| `zyte_a_lago.yml` | `g7b_lago.zyte_a_lago` | Copiar extracciones terminadas |
| `procesar.yml` | `g7b_ingesta.procesar` y `g7b_ingesta.publicar` | Validar y publicar conocimiento |

Cuando se inicia un workflow, GitHub proporciona un ejecutor temporal con Ubuntu y Python 3.12. Este ejecutor descarga el repositorio, instala las dependencias, utiliza las credenciales autorizadas, ejecuta el programa y conserva sus registros.

No es necesario mantener Cloud Shell abierta después de iniciar el workflow.

### Credenciales y variables

Los workflows utilizan los siguientes nombres de secretos del environment `amatista1` (sin reproducir sus valores):

- `AZURE_LAGO_URL`: acceso al contenedor Azure mediante SAS.
- `ZYTE_API_KEY`: autenticación para Zyte.
- `MONGO_URI`: conexión a MongoDB.

Los secretos no deben guardarse en código, archivos de documentación ni registros visibles.

Se identificó además el uso de `ZYTE_PROJECT_ID`, con valor predeterminado `883618`, y la variable `G7B_INGESTA_ACTIVA`, utilizada para habilitar los trabajos programados.

### Ejecución manual y programada

Los tres workflows admiten ejecución manual mediante `workflow_dispatch`.

Sus horarios configurados son:

- Vigilancia: cada seis horas.
- Zyte al lago: 09:17 UTC diariamente.
- Procesamiento: 10:47 UTC diariamente.

Los trabajos programados de estos workflows están condicionados a `G7B_INGESTA_ACTIVA=true`. En las pruebas realizadas, las ejecuciones fueron manuales.

Los simulacros se utilizan para validar el comportamiento sin publicar ni copiar datos. En una ejecución real, `simulacro=false` habilita las escrituras correspondientes; esto no implica que el sistema esté validado para producción continua.

## 5. Registro de ejecuciones comprobadas

| Ejecución | Operación | Resultado |
|---|---|---|
| [41556104847](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41556104847) | Vigilancia inicial | Falló autenticación SAS |
| [41556983434](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41556983434) | Vigilancia simulada | Correcta |
| [41560618173](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41560618173) | Zyte → Azure, simulacro | 1 trabajo pendiente |
| [41560794339](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41560794339) | Zyte → Azure, real | 2,353 registros importados |
| [41560965091](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41560965091) | Procesamiento simulado | 987 aceptados; MongoDB conectado |
| [41561411691](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41561411691) | Procesamiento y publicación real | 987 documentos nuevos |

## 6. Problemas encontrados y soluciones

### Error de autenticación SAS

La primera vigilancia falló con:

`AuthenticationFailed: Signature did not match`

Se verificó que el contenedor Azure estaba disponible mediante autenticación con la identidad de Azure Cloud Shell.

Posteriormente se generó una SAS nueva y se actualizó `AZURE_LAGO_URL` en GitHub.

La vigilancia siguiente completó correctamente la lectura de Azure.

**Riesgo pendiente:** la SAS generada para esta prueba tenía una duración de 24 horas. Es necesario establecer una estrategia de autenticación duradera y segura, preferentemente sin depender permanentemente de SAS manuales de corta duración.

### Autenticación de GitHub CLI

Cloud Shell perdió la sesión de autenticación de GitHub después de reiniciarse.

La solución fue volver a iniciar sesión mediante `gh auth login`.

Este problema afectaba al terminal interactivo, no a la ejecución autónoma de GitHub Actions.

### Advertencias de dependencias

Aparecieron avisos sobre la compatibilidad de acciones con Node.js 20 y la declaración del extra `srv` de PyMongo.

No bloquearon las ejecuciones verificadas, pero deben revisarse como mantenimiento técnico.

## 7. Qué tenemos actualmente

### Capacidades verificadas

- Repositorio operativo en GitHub.
- Workflows ejecutables manualmente.
- Autenticación funcional con Zyte.
- Acceso funcional al almacenamiento Azure.
- Importación real de datos al lago.
- Embudo de clasificación ejecutado con datos reales.
- Generación de documentos aceptados en plata.
- Conexión funcional a MongoDB.
- Publicación real de 987 documentos nuevos.
- Trazabilidad de las ejecuciones mediante registros de GitHub Actions.

### Capacidades existentes pero aún no validadas en esta prueba

El repositorio también contiene componentes para medición de rendimiento, otras arañas, infraestructura Azure y documentación de integración con Amatista.

Estas funciones no quedan automáticamente validadas por la prueba de ingesta realizada.

## 8. Trabajo pendiente

**Prioridad 1. Seguridad y continuidad.** Resolver la autenticación de Azure a largo plazo y verificar la vigencia de los secretos.

**Prioridad 2. Integridad.** Consultar MongoDB directamente para comprobar el conteo posterior y una muestra de documentos.

**Prioridad 3. Idempotencia.** Repetir controladamente el procesamiento y confirmar que los documentos existentes no se duplican.

**Prioridad 4. Calidad.** Auditar muestras de documentos aceptados, rechazados y en revisión.

**Prioridad 5. Automatización.** Activar los procesos programados únicamente después de validar seguridad, costos, cuotas y comportamiento ante fallos.

**Prioridad 6. Integración funcional.** Preparar mecanismos para que Geoda y Amatista consulten el conocimiento de G7B de forma controlada.

## 9. Conclusión

El 2 de noviembre de 2026 se alcanzó un hito técnico fundamental: G7B procesó datos reales a través de servicios independientes y consiguió publicar conocimiento aceptado en MongoDB.

La arquitectura básica funciona y GitHub Actions demostró ser capaz de coordinar su ejecución.

La siguiente fase consiste en transformar esta prueba exitosa en una operación confiable, reproducible, segura y mantenible, antes de ampliar el volumen de extracción.

**Estado del hito: COMPLETADO.**

**Estado de producción continua: PENDIENTE DE VALIDACIÓN.**

## 10. Alcance de la verificación documental

Esta bitácora conserva la documentación de la conversación «Validar despliegue G7B». Al incorporarla se contrastaron las seis ejecuciones con GitHub Actions: todas fueron manuales sobre el commit `07fbcc062d0abec7563c13cfece4a99c5a3b41a4` de `main`; la primera terminó en fallo y las cinco posteriores en éxito. Los logs de importación y publicación reales confirman las cifras de las secciones 1 y 3. Los horarios, programas y condiciones de ejecución se contrastaron con los workflows de ese commit.

La renovación de la SAS por 24 horas y la recuperación de la sesión de Cloud Shell corresponden al relato de la jornada. Esta revisión documental no consultó valores de secretos, no verificó su vigencia actual ni ejecutó nuevas ingestas. Tampoco consultó directamente MongoDB: 987 es el número de documentos nuevos reportado por el publicador, no el total actual de la colección. Los porcentajes están redondeados y pueden no sumar exactamente 100%.

GitHub conserva el código, las versiones y los registros de ejecución; los datos importados y procesados se almacenan en Azure y MongoDB. Este cambio incorpora únicamente documentación.
