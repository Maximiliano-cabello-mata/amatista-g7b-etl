# Araña manual de telemetría de Amatista

La pregunta de Geoda es qué práctica, escena y configuración funcionan en un equipo concreto. El recolector conserva quién produjo la evidencia, qué operación se midió y en qué unidad. Se puede ejecutar sin cuenta de alumno, sin conexión a Azure y con copias locales de las fuentes públicas. Las observaciones de laboratorio y la experiencia de un alumno tienen poblaciones distintas.

## Ejecutar y leer una corrida

Desde la raíz del repositorio, con las dependencias de `requirements-lago.txt` instaladas, ejecuta Blender sobre una escena de la sonda. Guarda los resultados en una carpeta propia.

```sh
blender -b --factory-startup --python-exit-code 1 --python sonda/g7b_sonda.py -- --salida mediciones-blender --escena ligera --perfiles ligero --repeticiones 3 --sin-render --entorno laboratorio
python -m g7b_telemetria --sondas mediciones-blender --aframe medicion-aframe.json --limite 100 --salida captura/manual
```

Para producir el segundo archivo, abre una escena A-Frame de prueba en primer plano. Carga la copia revisada de `sonda/amatista_aframe.js` como script local en la página de prueba o como fragmento en las herramientas de desarrollo. Ejecuta las siguientes líneas en la consola de esa escena. Solo la segunda llamada crea una descarga. La sonda toma tiempos relativos y contadores del renderizador, sin enviar solicitudes. El nombre genérico de carga evita registrar la dirección de la página, la escena del estudiante o su cuenta.

```js
const medicion = await AmatistaTelemetria.medir({segundos: 5, entorno: "laboratorio", carga: "practica"});
AmatistaTelemetria.descargar(medicion);
```

Pasa el nombre real de la descarga a `--aframe`. También admite una carpeta de ventanas JSON. Para una corrida totalmente local, agrega `--snapshot opendata-latest.zip --caniuse data-2.0.json`. Para medir solamente A-Frame usa `--fuente sonda-aframe --aframe carpeta-o-archivo`. Para persistir agrega `--azure`, con las credenciales ya configuradas en el entorno. El modo local deja los resultados en el directorio indicado. Conviene usar una carpeta por corrida para conservar cada informe. [Sonda de Blender](../../sonda/g7b_sonda.py) · [Sonda de A-Frame](../../sonda/amatista_aframe.js) · [Recolector](../../g7b_telemetria/recopilar.py)

Para repetir el piloto con una versión fija, el workflow descarga Blender 4.2.20 LTS desde el archivo oficial y contrasta su SHA-256 antes de ejecutarlo. La primera corrida documentada al final usó Blender 4.0.2 de Ubuntu. [Archivo oficial de Blender 4.2](https://download.blender.org/release/Blender4.2/)

La raíz de la salida contiene `informe.json`. Cada fuente indica si tuvo datos, si terminó sin novedades, si espera una medición manual o si falló. Una captura parcial conserva las mediciones válidas y hace que la orden termine con error. El registro de Can I Use distingue cada función incluso cuando cambia una nota vinculada al código. El workflow de producción conserva la ejecución manual y el ciclo semanal existentes. El piloto del PR escribe en el disco del runner. [Flujo de telemetría](../../.github/workflows/telemetria.yml) · [Piloto reproducible](../../.github/workflows/piloto_telemetria.yml)

## Origen y resolución de la evidencia

| Fuente habilitada | Unidad de observación | Qué puede responder | Límite |
|---|---|---|---|
| Sonda de Blender | Una operación, escena, perfil, versión y equipo. Tiempos en s o cadencia interna en FPS | Coste de edición, modificadores, animación y renders disponibles | El piloto sin ventana cubre CPU. La vista interactiva necesita una ventana y los renders necesitan su propia corrida |
| Blender Open Data | Escena del benchmark Cycles, backend y dispositivo. Muestras/min | Rendimiento relativo de render para configuraciones comparables | Resultados voluntarios de la comunidad. Se conservan en revisión. No permiten estimar por sí solos uso escolar o fluidez en pantalla |
| Sonda de A-Frame | Ventana de 3–30 s en primer plano. Intervalos en ms y actividad del renderizador | Cadencia observada, pausas largas, llamadas de dibujo y triángulos máximos | Un navegador de CI con render por software y un equipo de aula deben analizarse en estratos distintos. La versión inicial excluye sesiones inmersivas XR |
| Can I Use | Función × navegador × versión, con código y notas | Soporte declarado para WebGL, WebGL 2, WebGPU, WebXR, Wasm y OffscreenCanvas | Un soporte parcial o bajo bandera requiere revisar su nota. Las cuotas globales de uso proceden de otra población |

El cubo de Blender consume `plata/telemetria/`. Can I Use conserva sus matrices en `plata/compatibilidad/` y A-Frame guarda ventanas en `plata/telemetria_web/`. Hay que consultar estas últimas por separado hasta que el cubo incorpore sus contratos. Con Azure, la sonda Blender procesa también el buzón histórico `bronce/sonda/` y marca cada archivo una vez procesado. Los lotes se identifican por contenido y se verifican mediante una segunda lectura. [Cubo](../../g7b_almacen/cubo.py) · [Catálogo](../../fuentes/catalogo.yml)

## Qué enseñan los proyectos estudiados

**Blender Open Data.** El proyecto mantiene escenas de prueba y un archivo de resultados aportados voluntariamente por la comunidad. Conservamos cada escena y su backend con la puntuación original. Un equipo rápido en Cycles todavía necesita ejecutar la práctica de edición para comparar esa carga. El importador comprueba la licencia dentro del ZIP y dispone de un cursor para recorrer tandas en el lago. Con archivos locales verifica el mismo formato. [Blender Benchmark](https://www.blender.org/news/introducing-blender-benchmark/) · [Open Data](https://opendata.blender.org/about/)

**A-Frame, Three.js y MDN.** A-Frame ofrece estadísticas de escena, entre ellas llamadas por cuadro y geometría. El navegador puede suspender los callbacks en pestañas ocultas y su frecuencia depende de la pantalla. La sonda exige que el renderizador avance y aborta si se oculta el documento o entra en XR. El p95 permite identificar intervalos largos aunque la mediana sea estable. El tiempo medido expresa la cadencia observada desde JavaScript, sin atribuir por sí mismo la demora a CPU, GPU o presentación física. [A-Frame stats](https://aframe.io/docs/1.7.0/components/stats.html) · [Three.js](https://threejs.org/docs/pages/WebGLRenderer.html) · [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

**Can I Use.** El repositorio oficial distribuye su tabla bajo CC BY 4.0. La adaptación de Amatista retiene la procedencia y el código íntegro de cada celda, incluidas banderas y referencias a notas. Contrastar esta tabla con una ventana local de A-Frame permite investigar dos preguntas diferentes sobre el mismo navegador. Para decidir compatibilidad en un equipo concreto todavía conviene probar la función habilitada en ese equipo. Datos de Alexis Deveria y colaboradores de Can I Use. [Datos y atribución](https://github.com/Fyrd/caniuse) · [Metodología y cuotas](https://caniuse.com/ciu/about)

**pyperf y Chromium Catapult.** pyperf diferencia calentamientos, valores y procesos. Catapult separa la escena y la secuencia de acciones de la métrica. En el laboratorio de Amatista esto implica comparar el mismo archivo o versión de práctica y repetir sesiones independientes por equipo. Tres vueltas en una misma sesión estiman ruido a corto plazo. Para evaluar una actualización conviene alternar el orden A/B entre equipos y registrar por separado la carga en frío. [pyperf](https://pyperf.readthedocs.io/en/latest/run_benchmark.html) · [Chromium Telemetry](https://chromium.googlesource.com/catapult/+/master/telemetry/README.md)

**OpenTelemetry.** Para contadores futuros de fallos o intentos harán falta una ventana, una población y una temporalidad definidas. Un contador acumulado se transforma en incrementos dentro de la misma serie y se reinicia cuando cambia su origen temporal. La tasa de fallos de una práctica se calcularía como fallos sobre intentos de la misma ventana. Con solo reportes enviados se puede describir qué falló, pero falta el denominador para estimar esa tasa. [Modelo de métricas](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)

## Ecuaciones y criterios de uso

| Indicador | Cálculo | Interpretación |
|---|---|---|
| Repetibilidad de la sonda de Blender | $m=\operatorname{mediana}(x_i)$, $R=(\max x_i-\min x_i)/m$ | Validación de la sonda existente. Con al menos tres repeticiones, calentamiento descartado, corrida completa y $R\leq 0.10$, la medición puede pasar a aceptada. Un valor de $R$ no es un intervalo de confianza |
| Cadencia de A-Frame | $f=1000n/\sum_i \Delta t_i$ con $\Delta t_i$ en ms | Promedia por el tiempo transcurrido. Se contabilizan intervalos entre cuadros observados. Se informa la mediana y el p95 por rango más próximo, $\Delta t_{(\lceil0.95n\rceil)}$, y se conserva la ventana en revisión |
| Cobertura del catálogo | Fuentes con datos / fuentes catalogadas. Para disponibilidad operativa, informar por separado las fuentes consultadas con éxito y sin novedades | Una fuente que espera aportes manuales se distingue de una caída de red. Miles de celdas del mismo proveedor siguen siendo una sola fuente |
| Cambio de rendimiento propuesto | Para tiempo de operación sobre el mismo equipo, $g_i=(t_{base,i}-t_{nuevo,i})/t_{base,i}$ | Informar la mediana de los cambios emparejados por equipo y sus tamaños de muestra. Un valor positivo indica reducción de tiempo. Mantener constantes escena, versión, perfil y backend salvo el factor experimental |

El umbral documental del 80 % evalúa páginas seleccionadas. Para recomendar un ajuste de rendimiento interesa otra pregunta. La validación propuesta reserva equipos completos, mide la práctica con ambas configuraciones y publica cuántos equipos alcanzaron el objetivo definido antes del ensayo. Si hay cinco PCs y cien repeticiones en uno de ellos, la unidad independiente sigue siendo el equipo. Separar por GPU/CPU, nivel de RAM y entorno también permite reconocer los estratos con datos insuficientes.

## Siete fuentes pendientes

| Fuente | Dato que aportaría | Condición que registra el proyecto |
|---|---|---|
| Reportes de Blender | Fallos asociados con versión, GPU o sistema | Revisar condiciones de reutilización, leer campos estructurados y comprobar paginación |
| Encuesta de Steam | Distribución de hardware de quienes participan | Revisar uso de agregados publicados y definir el adaptador |
| OpenBenchmarking | Resultados de pruebas de Blender | Verificar reutilización y asociar cada resultado con versión y perfil |
| Web3D Survey | Capacidades web observadas por dispositivo | Verificar licencia y qué población aporta datos |
| GPUinfo OpenGL | Extensiones declaradas por modelo de GPU | Verificar condiciones y compatibilidad del esquema |
| Sonda de operaciones | Costes de operaciones individuales como UV y horneado | Construir escenarios repetibles para las operaciones que faltan |
| Agregados de prácticas de Amatista | Fallos e intentos por práctica y ventana | Implementar emisión voluntaria, agrupación mínima de cinco equipos según el catálogo y la ruta de agregados de la API |

La API inspeccionada ofrece el estado agregado de Geoda. La recepción de sesiones de alumnos sigue pendiente. Una importación manual del laboratorio no activa captura en el complemento ni en la PWA. [Consentimiento del proyecto](../../docs/CONSENTIMIENTO_TELEMETRIA.md) · [API de Amatista](https://github.com/Maximiliano-cabello-mata/amatista-api-)

## Primera ejecución conjunta verificada

El piloto del commit `61852b7` ejecutó las cuatro fuentes el 19 de noviembre de 2026, hora de México. Recorrió 438 008 entradas del archivo oficial de Blender. Encontró 87 848 de esquemas históricos y seleccionó cinco benchmarks v4, que aportaron 15 resultados por escena en revisión. La sonda Blender del runner entregó tres mediciones aceptadas. Can I Use produjo 4 296 celdas de seis funciones. [Registro del piloto](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44662229403)

En Chromium con renderizado por software, la escena de un cubo produjo 301 intervalos en 5 016,5 ms. La mediana fue 16,7 ms y el p95 fue 16,8 ms. El máximo observado fue una llamada de dibujo y 12 triángulos. Es una sola ventana del runner, guardada en revisión. La cobertura de esta corrida fue 4/4 fuentes habilitadas y 4/11 inventariadas. El destino fue local al runner. La verificación de ese commit incluyó 212 pruebas aprobadas y cinco subpruebas. [Artefacto del piloto](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44662229403/artifacts/14594969871) · [Pruebas](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44662229398)
