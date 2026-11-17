# Documentación Técnica: Arañas Cibernéticas de Telemetría (SAIT) e Instrumentación 3D/WebGL/WebGPU

**Estado del documento:** Especificación de Arquitectura y Referencia Técnica  
**Ámbito:** Recolección activa de telemetría web, instrumentación de motores de navegador (Blink/V8/Gecko) y perfilado de contextos gráficos 3D (WebGL2 / WebGPU)  
**Repositorio objetivo:** Pipeline de extracción y cubo analítico de telemetría (`Geoda` / `amatista-g7b-etl`)

## 1. Definición Arquitectónica: Raspadores de Contenido vs. Sondas de Telemetría (SAIT)

En la ingeniería de extracción de datos, las plataformas comerciales convencionales como Zyte, Scrapy o Crawlee operan como **raspadores de estado estático o de DOM**: su objetivo es realizar peticiones HTTP o renderizar una página para extraer texto, atributos HTML y estructuras JSON de negocio.

Por el contrario, una **Araña Cibernética de Telemetría** —o **Sistema Automatizado de Ingesta de Telemetría (SAIT)**— no busca únicamente el contenido semántico de la página, sino la **observabilidad de ejecución del sistema que la procesa**. Una sonda de telemetría instrumenta el binario del navegador, intercepta el bus de depuración en tiempo real, coloca ganchos (*hooks*) sobre las APIs nativas de C++/JavaScript y captura el flujo de comandos enviados hacia la tarjeta gráfica (GPU) y la pila de red.

La escasa documentación bajo el nombre genérico de «araña de telemetría» se debe a que la literatura científica e industrial la divide en cuatro dominios especializados con nomenclaturas propias:

1. **Automated Telemetry Harnesses (Arneses de Telemetría de Navegador):** Representados por el framework oficial [Chromium Catapult Telemetry](https://chromium.googlesource.com/catapult/+/HEAD/telemetry/) y su sistema de trazas [Perfetto](https://perfetto.dev/docs/getting-started/chrome-tracing). Fueron diseñados por el equipo de ingeniería de Google Chrome para ejecutar acciones automatizadas sobre conjuntos de páginas (*story sets*) utilizando reproducción determinista de red (*Web Page Replay*) y extraer histogramas de bajo nivel de CPU, GPU y memoria.
2. **Browser Instrumentation Crawlers (Arañas de Instrumentación y Auditoría):** Encabezados por [OpenWPM](https://github.com/openwpm/OpenWPM) (desarrollado en la Universidad de Princeton y mantenido para estudios a escala de millones de sitios) y motores basados en parches sobre V8 como [VisibleV8 y ByteDefender](https://arxiv.org/html/2509.09950v1). Estas arañas interceptan llamadas a prototipos de JavaScript (`HTMLCanvasElement`, `WebGLRenderingContext`, `AudioContext`, `RTCPeerConnection`) y registran la pila de ejecución (*call stack*) y el *bytecode* de cada script.
3. **Large-Scale Synthetic RUM Crawlers (Sondas Sintéticas de Rendimiento a Gran Escala):** La infraestructura que impulsa el [HTTP Archive](https://github.com/httparchive) mediante [WebPageTest](https://www.logicmonitor.com/webpagetest) y el motor [Browsertime de Sitespeed.io](https://github.com/sitespeedio/browsertime). Estas arañas levantan contenedores aislados, graban video del puerto de visualización a 60 cuadros por segundo para calcular métricas visuales mediante `ffmpeg` y extraen cascadas completas de red y trazas del procesador.
4. **WebGL / WebGPU Command Interceptors (Interceptores de Búfer de Comandos 3D):** Herramientas de introspección gráfica como [Spector.js](https://github.com/BabylonJS/Spector.js/) y los contadores internos de motores como [`WebGLRenderer.info` en Three.js](https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info), capaces de envolver el contexto gráfico para auditar cada llamada de dibujo (*draw call*), estado de *shaders*, uso de VRAM y tiempos de GPU en nanosegundos.

## 2. Taxonomía Comparativa de Motores y Frameworks Documentados

La siguiente tabla sintetiza la arquitectura, el vector de inyección y las variables recolectadas por los principales sistemas documentados en la literatura técnica:

| Sistema / Framework | Motor Base y Protocolo | Vector de Instrumentación | Variables de Telemetría Extraídas | Documentación y Fuente Primaria |
| :--- | :--- | :--- | :--- | :--- |
| **Chromium Telemetry (Catapult)** | Chromium / Chrome vía DevTools Remote Debugging y ADB | Controlador en Python que lanza el navegador con banderas específicas, reproduce archivos WPR y extrae trazas del inspector. | Histogramas de latencia del *compositor*, tiempos de rasterización en GPU, consumo de memoria por proceso y perfiles de CPU. | [Catapult Telemetry Docs](https://chromium.googlesource.com/catapult/+/HEAD/telemetry/docs/) |
| **OpenWPM** | Firefox instrumentado vía Selenium y extensión dedicada | *Monkey-patching* sobre `window` y prototipos DOM antes de la carga de scripts de la página; almacenamiento estructurado en SQLite/LevelDB. | Llamadas a APIs de alto riesgo/entropía (`WebGL`, `Canvas`, `Navigator`), lecturas/escrituras de cookies, peticiones HTTP y *stack traces*. | [Repositorio OpenWPM](https://github.com/openwpm/OpenWPM) / [Estudio de 1M de sitios](https://www.researchgate.net/publication/310821260_Online_Tracking_A_1-million-site_Measurement_and_Analysis) |
| **VisibleV8 / ByteDefender** | Chromium con motor V8 instrumentado en C++ | Modificación directa del intérprete V8 para registrar accesos a propiedades nativas y secuencias de *bytecode* sin ser detectado desde JS. | Trazas a nivel de función, extracción de *bytecode* V8 y detección de heurísticas de *fingerprinting* (p. ej. >20 llamadas a `measureText`). | [ByteDefender (arXiv:2509.09950v1)](https://arxiv.org/html/2509.09950v1) / [Survey (arXiv:2606.14525v1)](https://arxiv.org/html/2606.14525v1) |
| **Browsertime / Sitespeed.io** | Chrome, Firefox, Edge y Safari (iOS USB) vía WebDriver/CDP | Orquestación en Docker con captura de pantalla por `ffmpeg`, inyección de scripts de métricas W3C y recolección de archivos HAR. | Core Web Vitals ([LCP](https://web.dev/articles/lcp)), *First Visual Change*, *SpeedIndex*, tiempos de CPU por tarea y métricas de red TCP/TLS/QUIC. | [Browsertime GitHub](https://github.com/sitespeedio/browsertime) / [Sitespeed Browsers Docs](https://www.sitespeed.io/documentation/sitespeed.io/browsers/) |
| **Spector.js** | Cualquier navegador con contexto WebGL 1.0 / WebGL 2.0 | Envoltorio (*proxy*) en tiempo de ejecución sobre `HTMLCanvasElement.prototype.getContext` expuesto mediante `window.spector`. | Captura cuadro por cuadro de comandos GL, conteo de *draw calls*, vértices, primitivas, *Uniform Buffer Objects* (UBOs), texturas y *shaders*. | [Spector.js Repository](https://github.com/BabylonJS/Spector.js/) / [API Programática](https://github.com/BabylonJS/Spector.js/blob/master/documentation/extension.md) |
| **Browser-Use / SuperScraper** | Chromium vía CDP directo o control de OS guiado por VLM | Agentes impulsados por modelos de visión ([Qwen3-VL-8B y OmniParser](https://arxiv.org/html/2611.06197)) que interactúan con la interfaz gráfica. | Telemetría en páginas profundas (niveles 2 a 10), evasión de bloqueos antibot y captura de hasta 1.69x más eventos de rastreo que un crawler pasivo. | [Beyond the Landing Page (arXiv:2611.06197)](https://arxiv.org/html/2611.06197) |

## 3. Telemetría General del Navegador, Sistema y Red (No-3D)

Para que una araña recopile telemetría integral del entorno de ejecución más allá de los gráficos 3D, debe acoplarse a dos fuentes estandarizadas: el protocolo [Chrome DevTools Protocol (CDP)](https://chromedevtools.github.io/devtools-protocol/) a través de una conexión WebSocket full-duplex (`/devtools/page/{targetId}` o `/devtools/browser/{guid}`) y las especificaciones del grupo de trabajo de rendimiento web del W3C ([Web Performance Working Group](https://webperfwg.org/)).

### 3.1. Instrumentación mediante Chrome DevTools Protocol (CDP)

A través de bibliotecas como [Playwright `CDPSession`](https://playwright.dev/python/docs/api/class-cdpsession), Puppeteer o clientes directos en Python/Go/Rust, la araña invoca cuatro dominios fundamentales de CDP:

* **Dominio `Performance` ([Documentación CDP Performance](https://chromedevtools.github.io/devtools-protocol/1-3/Performance/)):**
  Al habilitar el dominio y ejecutar el comando `Performance.getMetrics`, el proceso renderizador devuelve un arreglo de contadores numéricos instantáneos ([desglose técnico de métricas](https://stackoverflow.com/questions/53723263/understanding-chrome-devtools-performance-getmetrics-results)):
  * `Timestamp`: Marca de tiempo exacta de la muestra.
  * `JSHeapUsedSize` y `JSHeapTotalSize`: Memoria dinámica de JavaScript utilizada y reservada en el motor V8 (en bytes).
  * `ScriptDuration`: Tiempo acumulado (en segundos) dedicado a la ejecución de código JavaScript.
  * `LayoutCount` y `LayoutDuration`: Número total de recálculos de geometría de página (*reflows*) y su duración combinada.
  * `RecalcStyleCount` y `RecalcStyleDuration`: Número y duración de recálculos de árboles CSS.
  * `TaskDuration`: Duración combinada de todas las tareas ejecutadas por el hilo principal del navegador.
  * `Nodes`, `Documents`, `Frames` y `JSEventListeners`: Conteo de nodos en el árbol DOM y escuchadores de eventos activos (crucial para detectar fugas de memoria o *memory leaks* durante sesiones prolongadas).
* **Dominio `SystemInfo` ([Especificación `SystemInfo.getInfo`](https://github.com/chromedp/cdproto/blob/master/systeminfo/systeminfo.go)):**
  Permite a la araña auditar el hardware físico o virtualizado sobre el que corre el navegador. Devuelve la estructura `GPUInfo` (arreglo de dispositivos con `vendorId`, `deviceId`, `driverVendor`, `driverVersion`), las capacidades de decodificación/codificación de video por hardware, el `modelName` del equipo anfitrión y la cadena exacta de `commandLine` con la que se inicializó el binario.
* **Dominio `Tracing` ([Método `Tracing.start`](https://github.com/puppeteer/puppeteer/issues/8991) y [Formato Perfetto](https://perfetto.dev/docs/getting-started/other-formats)):**
  A diferencia de `Performance.getMetrics` (que entrega promedios o acumulados), `Tracing.start` abre una grabación continua de eventos internos de C++ de Chromium en un búfer circular (que por defecto es de [200 MB y puede escalarse a 300–400 MB](https://issues.chromium.org/409086863)). La araña especifica categorías (`categories`) como `devtools.timeline`, `v8.execute`, `gpu`, `cc` (compositor de Chromium), `blink.user_timing` y `latencyInfo`. Cada evento registrado incluye `pid` (ID de proceso), `tid` (ID de hilo), `ts` (marca de tiempo en microsegundos), `ph` (fase: inicio, fin, contador, flujo), `cat` y `args`.
* **Dominio `Network`:**
  Al suscribirse a `Network.requestWillBeSent`, `Network.responseReceived` y `Network.loadingFinished`, la sonda captura la telemetría de transporte de cada subrecurso (texturas `.ktx2`, mallas `.glb`/`.gltf`, binarios `.wasm`, scripts `.js`): tiempos de resolución DNS, negociación TLS, protocolo negociado (`h2`, `h3`/QUIC), bytes transferidos por cable (`encodedDataLength`) frente a bytes descomprimidos en memoria, y aciertos de caché.

### 3.2. Estándares W3C Performance Timeline y OpenTelemetry en el Hilo de Página

De manera complementaria a CDP, la araña puede inyectar un `PerformanceObserver` estándar en el contexto de la página para recolectar telemetría compatible con cualquier navegador moderno:

* **[Navigation Timing Level 2 (W3C)](https://www.w3.org/TR/navigation-timing-2/) y [Resource Timing (W3C)](https://www.w3.org/TR/resource-timing/):** Miden con resolución de sub-milisegundos (`DOMHighResTimeStamp`) desde el inicio de la navegación (`startTime = 0`) los intervalos `domainLookupStart/End`, `connectStart/End`, `requestStart`, `responseStart` (Time to First Byte), `domInteractive` y `loadEventEnd`.
* **[Long Tasks API (W3C)](https://www.w3.org/TR/longtasks-1/):** Registra cualquier tarea del bucle de eventos (*event loop*) más su punto de control de microtareas inmediato cuya duración supere los **50 ms**, identificando el contexto o `iframe` responsable (`same-origin`, `cross-origin-descendant`, etc.).
* **[Long Animation Frames API - LoAF (W3C)](https://www.w3.org/TR/long-animation-frames/):** Evolución publicada por el W3C para diagnosticar cuadros de animación lentos (>50 ms) que bloquean el hilo de interfaz de usuario e impiden procesar entradas o ejecutar callbacks de `requestAnimationFrame`, detallando los scripts exactos que provocaron el retraso.
* **[User Timing API (W3C)](https://www.w3.org/TR/user-timing-1/) y [OpenTelemetry Browser Instrumentation](https://opentelemetry.io/docs/languages/js/getting-started/browser/):** Permiten emitir marcas (`performance.mark`) y mediciones (`performance.measure`) personalizadas desde los ganchos de la araña y exportarlas como trazas distribuidas siguiendo las [convenciones semánticas de navegador de OpenTelemetry](https://opentelemetry.io/docs/specs/semconv/resource/browser/).

## 4. Telemetría 3D Profunda: Instrumentación de WebGL, WebGL2 y WebGPU

El mayor desafío técnico al diseñar una araña que recolecte telemetría 3D es que una aplicación tridimensional (desarrollada en [Three.js](https://threejs.org/docs/), Babylon.js, A-Frame, PlayCanvas o Unity/Godot exportado a WebAssembly) se presenta en el DOM como un único nodo `<canvas>` opaco. Un raspador convencional no ve mallas, ni luces, ni *shaders*, ni cuadros por segundo.

Para extraer telemetría 3D real, la araña debe operar como un **interceptor de contexto gráfico** inyectado mediante `Page.addScriptToEvaluateOnNewDocument` antes de que se ejecute la primera línea de JavaScript de la página.

### 4.1. Identificación sin Máscara del Hardware Gráfico (`WEBGL_debug_renderer_info`)

Antes de interpretar cualquier métrica de rendimiento 3D, la araña debe registrar qué unidad de procesamiento gráfico está ejecutando el código. Mediante la extensión estándar [`WEBGL_debug_renderer_info` documentada en MDN](https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info) y el método [`gl.getExtension()`](https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/getExtension), la sonda consulta dos [constantes de WebGL](https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Constants) a través de `gl.getParameter()`:

* `debugInfo.UNMASKED_VENDOR_WEBGL` (`0x9245`): Identifica al fabricante del controlador o capa de traducción (p. ej. `Google Inc. (AMD)`, `NVIDIA Corporation`).
* `debugInfo.UNMASKED_RENDERER_WEBGL` (`0x9246`): Devuelve la cadena exacta del motor de renderizado y hardware subyacente (p. ej. `ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)` frente a `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))`).

Asimismo, al probar la creación del contexto, el atributo booleano `failIfMajorPerformanceCaveat` ([especificado en MDN](https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info)) permite a la araña verificar si el navegador considera que el rendimiento 3D del sistema actual es drásticamente inferior al umbral de hardware (por ejemplo, cuando cae en emulación por software).

### 4.2. Cronometraje Asíncrono de GPU en Nanosegundos (WebGL2 y WebGPU)

Medir el tiempo que tarda en ejecutarse una función de JavaScript (`requestAnimationFrame`) **no mide el tiempo de la GPU**, ya que la CPU simplemente encola comandos en un búfer y continúa su ejecución de forma asíncrona. Para medir el tiempo real que tarda el silicio de la GPU en procesar vértices y fragmentos, la araña debe emplear consultas de temporizador de hardware:

1. **En contextos WebGL 1.0 y WebGL 2.0 ([`EXT_disjoint_timer_query` y `EXT_disjoint_timer_query_webgl2`](https://developer.mozilla.org/en-US/docs/Web/API/EXT_disjoint_timer_query)):**
   * En WebGL 2.0, la araña solicita `const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2')` ([soporte y especificación de la extensión](https://web3dsurvey.com/webgl2/extensions/EXT_disjoint_timer_query_webgl2)) y crea un objeto [`WebGLQuery`](https://developer.mozilla.org/en-US/docs/Web/API/WebGLQuery) mediante `gl.createQuery()`.
   * Al inicio del cuadro (o de un *draw call* específico), invoca `gl.beginQuery(ext.TIME_ELAPSED_EXT, query)` y al finalizar invoca `gl.endQuery(ext.TIME_ELAPSED_EXT)`.
   * En cuadros posteriores (cuando `gl.getQueryParameter(query, gl.QUERY_RESULT_AVAILABLE)` devuelve `true` y `gl.getParameter(ext.GPU_DISJOINT_EXT)` es `false`, lo que garantiza que la GPU no sufrió escalado dinámico de frecuencia ni interrupciones térmicas), la araña extrae `gl.getQueryParameter(query, gl.QUERY_RESULT)`, obteniendo el tiempo exacto de ejecución en la GPU expresado en **nanosegundos** ($10^{-9}\text{ s}$).
2. **En contextos WebGPU ([`GPUQuerySet`](https://developer.mozilla.org/en-US/docs/Web/API/GPUQuerySet) y `timestamp-query`):**
   * En la API moderna [WebGPU](https://generalistprogrammer.com/tutorials/webgl-game-development-complete-browser-gaming-guide-2025), si el dispositivo se inicializa con la característica `timestamp-query`, la araña crea un conjunto de consultas mediante [`device.createQuerySet({ type: 'timestamp', count: N })`](https://developer.mozilla.org/en-US/docs/Web/API/GPUDevice/createQuerySet).
   * Al codificar pasadas de renderizado con [`GPUCommandEncoder.beginRenderPass()`](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginRenderPass) o pasadas de cómputo con [`GPUCommandEncoder.beginComputePass()`](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginComputePass), se inyecta la propiedad `timestampWrites` indicando `beginningOfPassWriteIndex` y `endOfPassWriteIndex` (o mediante [`GPUCommandEncoder.writeTimestamp()`](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/writeTimestamp)).
   * Adicionalmente, WebGPU permite adjuntar un `occlusionQuerySet` en `beginRenderPass()` para contabilizar cuántas muestras de fragmentos superaron las pruebas de profundidad y *stencil*, permitiendo a la araña medir objetivamente el *overdraw* o si un objeto 3D fue realmente visible en pantalla.

### 4.3. Contadores de Geometría, Shaders y VRAM (`WebGLRenderer.info` y `Spector.js`)

Además de los tiempos de reloj, una araña de telemetría 3D debe cuantificar la carga estructural de la escena:

* **Extracción directa en motores basados en Three.js / A-Frame ([`WebGLRenderer.info`](https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info)):**
  La propiedad `renderer.info` mantiene estadísticas internas de la memoria de la GPU y del proceso de renderizado:
  * `renderer.info.memory`: Expone `geometries` (número de geometrías activas en búferes de vértices) y `textures` (número de texturas cargadas en VRAM).
  * `renderer.info.render`: Expone por cada cuadro `frame` (identificador del cuadro), `calls` (número de *draw calls* emitidos), `triangles` (total de triángulos rasterizados), `points` y `lines`.
  * `renderer.info.programs`: Arreglo de programas *shader* WebGL compilados en memoria.
  * *Nota crítica de implementación:* Como documenta [Three.js `WebGLRenderer.info`](https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info), estos contadores se reinician automáticamente en cada llamada a `render()`. Si la aplicación 3D realiza múltiples pasadas por cuadro (por ejemplo, mapas de sombras o post-procesado *bloom*/SSAO), la araña debe establecer `renderer.info.autoReset = false` y llamar manualmente a `renderer.info.reset()` al cierre del ciclo de `requestAnimationFrame` para no perder las métricas de las primeras pasadas.
* **Captura agnóstica del flujo de comandos con [Spector.js](https://github.com/BabylonJS/Spector.js/blob/master/readme.md):**
  Cuando el sitio web no expone una instancia de Three.js o utiliza WebGL puro/Babylon.js/WASM, la araña puede inyectar `Spector.js` y controlar el objeto global `window.spector` ([documentación de extensión y captura programática](https://github.com/BabylonJS/Spector.js/blob/master/documentation/extension.md) e [Issue #293](https://github.com/BabylonJS/Spector.js/issues/293)). Al invocar `spector.captureCanvas(canvasElement, commandCount)`, la herramienta intercepta todas las llamadas a la máquina de estados WebGL durante un cuadro completo y genera un JSON estructurado con cada cambio de estado (enlaces de texturas, compilación de *shaders*, valores de *Uniform Buffer Objects*, modos de mezcla y llamadas a `drawElements`/`drawArrays` o `drawElementsInstanced`).

## 5. El Problema del Modo Headless en 3D (SwiftShader / SwANGLE) y la Detección Antibot

Al desplegar una araña de telemetría 3D en producción, existen dos factores documentados que pueden invalidar o sesgar por completo los datos recolectados si no se controlan arquitectónicamente.

### 5.1. La Obsolescencia del Fallback Automático a SwiftShader y el Sesgo de CPU

Históricamente, cuando Chromium se ejecutaba en un servidor Linux o contenedor sin GPU física (`headless`), recurría automáticamente a **SwiftShader**, una implementación en software de las APIs Vulkan y OpenGL ES que corre íntegramente sobre la CPU ([Documentación oficial de Chromium SwiftShader](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md)).

Sin embargo, como establece la [especificación vigente del proceso GPU de Chromium](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md):

> *"Allowing automatic fallback to WebGL backed by SwiftShader has been deprecated and WebGL context creation will soon fail instead of falling back to SwiftShader."*

Chromium tomó esta decisión por dos motivos: el riesgo de seguridad de ejecutar código JIT dentro del proceso privilegiado de GPU y la degradación extrema de rendimiento cuando un navegador cae silenciosamente de una GPU física a un rasterizador por CPU. En consecuencia:

1. **En entornos sin GPU (CI/CD, contenedores en la nube):** Si una araña intenta inicializar una vista 3D sin banderas explícitas, la creación del contexto WebGL fallará o devolverá `0 FPS`. Para permitir que la araña valide escenas 3D en servidores sin tarjeta gráfica mediante **SwANGLE** (ANGLE sobre SwiftShader Vulkan), es obligatorio lanzar el binario de Chromium con los interruptores documentados en [Using Chromium with SwiftShader](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md):
   ```bash
   --use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader
   ```
2. **Separación estricta en el cubo de telemetría:** Dado que SwANGLE ejecuta los *vertex* y *fragment shaders* en la CPU del servidor, cualquier medición de `FPS` o `TIME_ELAPSED_EXT` obtenida bajo SwANGLE mide la velocidad de emulación por software y **no el rendimiento real en hardware gráfico**. Por lo tanto, el pipeline ETL debe etiquetar esas corridas con `is_software_renderer = true` (usándolas únicamente para auditar conteo de *draw calls*, triángulos, memoria de geometrías y errores de compilación de *shaders*), y exigir corridas con aceleración de hardware real (modo con ventana o servidor Xvfb acoplado a GPU física) para calcular perfiles de rendimiento de cuadros por segundo (`vista3d`).

### 5.2. Pérdida de Telemetría por Sistemas Antibot y Huella de Automatización

La literatura científica de medición web demuestra que las arañas automatizadas sufren una pérdida severa de visibilidad cuando los sitios web detectan que están siendo auditados:

* **Fugas del protocolo CDP y banderas Headless:** Los sistemas antifraude modernos detectan la presencia de automatización inspeccionando fugas de serialización en el protocolo CDP ([análisis de detección de CDP en Puppeteer/Playwright](https://blog.octobrowser.net/cdp-leaks-in-puppeteer-how-anti-fraud-systems-detect-automation-through-chrome-devtools-protocol)), la bandera `navigator.webdriver`, la ausencia de hardware gráfico real y las velocidades mecánicas sin eventos previos de desplazamiento o puntero ([análisis de huella de navegador y comportamiento](https://heyjunior.ai/blog/phantombuster-alternatives-that-run-locally/)).
* **Evidencia cuantitativa en la literatura académica (2025–2026):**
  * Según el compendio de estudios de medición web publicado en [Detecting Bot Detection (arXiv:2606.14525v1)](https://arxiv.org/html/2606.14525v1), las arañas automatizadas convencionales **pierden hasta el 45 %** de los eventos de telemetría y *fingerprinting* que experimentan los usuarios reales (Annamalai et al.), debido a bloqueos silenciosos y banners de consentimiento no resueltos.
  * En el mismo estudio ([arXiv:2606.14525v1](https://arxiv.org/html/2606.14525v1)), el análisis con **VisibleV8** sobre el Alexa Top 50K demostró que el **29 %** de los sitios web cargan scripts que buscan activamente 46 artefactos de espacio de nombres asociados a plataformas de automatización de navegadores, mientras que el **14 %** de las portadas del Tranco Top 100K detectan a OpenWPM, subiendo al **19 %** al visitar subpáginas (Krumnow et al.).
  * Más aún, el estudio [Beyond the Landing Page (arXiv:2611.06197, noviembre de 2026)](https://arxiv.org/html/2611.06197), que evaluó ocho configuraciones de arañas sobre 2,000 dominios navegando hasta 10 páginas internas por sitio, demostró que la tasa de denegación/bloqueo de Chromium estándar pasa de apenas **0.2 %** en la página principal (*landing page*) a **10.4 %** en las páginas internas 2 a 6 (una escalada de **+10.1 puntos porcentuales**, es decir, 52 veces más bloqueo tras el primer clic).
  * En contraste, las arañas agénticas evaluadas en [arXiv:2611.06197](https://arxiv.org/html/2611.06197) (`browser-use` sobre CDP directo y `SuperScraper` mediante interacción a nivel de sistema operativo) no sufrieron escalada de bloqueo en páginas internas (−0.4 pp y −1.7 pp respectivamente) y lograron capturar entre **1.50x y 1.69x más telemetría** que un crawler estático sobre las mismas URLs.
* **Mitigación técnica en la sonda:** Arquitecturas especializadas como [Stygian Browser](https://docs.rs/stygian-browser) documentan que ocultar `navigator.webdriver`, proteger los descriptores de CDP, mantener firmas plausibles de familias reales de GPU y emitir trayectorias humanas de ratón/teclado añade apenas **10 a 30 ms de sobrecarga por página**, pero evita que los sitios degraden o bloqueen la ejecución de sus motores gráficos. Además, en visores 3D interactivos (que suelen pausar el bucle de renderizado cuando la cámara está estática para ahorrar energía), la inyección de eventos `pointermove` y `wheel` sobre el `<canvas>` es indispensable para despertar el *render loop* y capturar los cuadros por segundo reales.

## 6. Arquitectura de Implementación de Referencia (Preload Hook + Playwright CDP)

A continuación se presenta la estructura de código en Python y JavaScript (lista para integrarse en un módulo de sonda como `sonda_vista3d.py`) que combina la sesión nativa [`CDPSession` de Playwright](https://playwright.dev/python/docs/api/class-cdpsession) con un interceptor de prototipo sobre `HTMLCanvasElement.prototype.getContext`.

Este diseño intercepta cualquier contexto `webgl`, `webgl2` o `webgpu` creado por la página, contabiliza *draw calls*, vértices y triángulos por cuadro, mide tiempos reales de GPU en nanosegundos vía [`EXT_disjoint_timer_query_webgl2`](https://developer.mozilla.org/en-US/docs/Web/API/EXT_disjoint_timer_query) y extrae en paralelo las métricas de V8 y DOM mediante [`Performance.getMetrics`](https://chromedevtools.github.io/devtools-protocol/1-3/Performance/) y [`SystemInfo.getInfo`](https://github.com/chromedp/cdproto/blob/master/systeminfo/systeminfo.go):

```python
import asyncio
import statistics
from playwright.async_api import async_playwright

# Script de instrumentación inyectado antes de cualquier script de la página (Preload Hook)
PRELOAD_3D_TELEMETRY_HOOK = """
(() => {
  window.__SAIT_TELEMETRY__ = {
    contextsCreated: [],
    gpuVendor: null,
    gpuRenderer: null,
    isSoftwareRenderer: false,
    frames: [],
    currentFrame: { drawCalls: 0, triangles: 0, vertices: 0, points: 0, lines: 0 },
    gpuTimesNs: [],
    texturesCreated: 0,
    buffersCreated: 0,
    shadersCompiled: 0
  };

  const origGetContext = HTMLCanvasElement.prototype.getContext;

  HTMLCanvasElement.prototype.getContext = function(type, attributes) {
    const ctx = origGetContext.call(this, type, attributes);
    if (!ctx) return ctx;

    const cleanType = String(type).toLowerCase();
    if ((cleanType === 'webgl' || cleanType === 'webgl2' || cleanType === 'experimental-webgl') && !ctx.__sait_hooked__) {
      ctx.__sait_hooked__ = true;
      window.__SAIT_TELEMETRY__.contextsCreated.push(cleanType);

      // 1. Identificación sin máscara de GPU y detección de SwiftShader/SwANGLE
      const debugInfo = ctx.getExtension('WEBGL_debug_renderer_info');
      if (debugInfo) {
        const vendor = ctx.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        const renderer = ctx.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        window.__SAIT_TELEMETRY__.gpuVendor = vendor;
        window.__SAIT_TELEMETRY__.gpuRenderer = renderer;
        if (String(renderer).toLowerCase().includes('swiftshader') || String(renderer).toLowerCase().includes('llvmpipe')) {
          window.__SAIT_TELEMETRY__.isSoftwareRenderer = true;
        }
      }

      // 2. Extensión de reloj de hardware en nanosegundos (WebGL2)
      const timerExt = (cleanType === 'webgl2')
        ? ctx.getExtension('EXT_disjoint_timer_query_webgl2')
        : ctx.getExtension('EXT_disjoint_timer_query');
      const pendingQueries = [];

      // 3. Contadores de recursos en VRAM
      const origCreateTexture = ctx.createTexture.bind(ctx);
      ctx.createTexture = function() {
        window.__SAIT_TELEMETRY__.texturesCreated++;
        return origCreateTexture();
      };

      const origCreateBuffer = ctx.createBuffer.bind(ctx);
      ctx.createBuffer = function() {
        window.__SAIT_TELEMETRY__.buffersCreated++;
        return origCreateBuffer();
      };

      const origCompileShader = ctx.compileShader.bind(ctx);
      ctx.compileShader = function(shader) {
        window.__SAIT_TELEMETRY__.shadersCompiled++;
        return origCompileShader(shader);
      };

      // 4. Interceptación de llamadas de dibujo (Draw Calls y Geometría)
      const tallyPrimitives = (mode, count, instances = 1) => {
        const total = count * instances;
        window.__SAIT_TELEMETRY__.currentFrame.drawCalls++;
        window.__SAIT_TELEMETRY__.currentFrame.vertices += total;
        if (mode === ctx.TRIANGLES) {
          window.__SAIT_TELEMETRY__.currentFrame.triangles += Math.floor(total / 3);
        } else if (mode === ctx.TRIANGLE_STRIP || mode === ctx.TRIANGLE_FAN) {
          window.__SAIT_TELEMETRY__.currentFrame.triangles += Math.max(0, (count - 2) * instances);
        } else if (mode === ctx.LINES || mode === ctx.LINE_STRIP || mode === ctx.LINE_LOOP) {
          window.__SAIT_TELEMETRY__.currentFrame.lines += Math.floor(total / 2);
        } else if (mode === ctx.POINTS) {
          window.__SAIT_TELEMETRY__.currentFrame.points += total;
        }
      };

      const origDrawArrays = ctx.drawArrays.bind(ctx);
      ctx.drawArrays = function(mode, first, count) {
        tallyPrimitives(mode, count, 1);
        return origDrawArrays(mode, first, count);
      };

      const origDrawElements = ctx.drawElements.bind(ctx);
      ctx.drawElements = function(mode, count, type, offset) {
        tallyPrimitives(mode, count, 1);
        return origDrawElements(mode, count, type, offset);
      };

      if (cleanType === 'webgl2') {
        const origDrawArraysInstanced = ctx.drawArraysInstanced.bind(ctx);
        ctx.drawArraysInstanced = function(mode, first, count, instanceCount) {
          tallyPrimitives(mode, count, instanceCount);
          return origDrawArraysInstanced(mode, first, count, instanceCount);
        };

        const origDrawElementsInstanced = ctx.drawElementsInstanced.bind(ctx);
        ctx.drawElementsInstanced = function(mode, count, type, offset, instanceCount) {
          tallyPrimitives(mode, count, instanceCount);
          return origDrawElementsInstanced(mode, count, type, offset, instanceCount);
        };
      }

      // 5. Bucle de muestreo de cuadros (Frame Pacing + GPU Timer Queries)
      let lastTime = performance.now();
      let activeQuery = null;

      const sampleFrame = (now) => {
        const dt = now - lastTime;
        lastTime = now;

        if (cleanType === 'webgl2' && timerExt) {
          if (activeQuery) {
            ctx.endQuery(timerExt.TIME_ELAPSED_EXT);
            pendingQueries.push(activeQuery);
            activeQuery = null;
          }
          // Recolectar consultas finalizadas sin bloquear el pipeline
          for (let i = pendingQueries.length - 1; i >= 0; i--) {
            const q = pendingQueries[i];
            const available = ctx.getQueryParameter(q, ctx.QUERY_RESULT_AVAILABLE);
            const disjoint = ctx.getParameter(timerExt.GPU_DISJOINT_EXT);
            if (available) {
              if (!disjoint) {
                const ns = ctx.getQueryParameter(q, ctx.QUERY_RESULT);
                window.__SAIT_TELEMETRY__.gpuTimesNs.push(ns);
              }
              ctx.deleteQuery(q);
              pendingQueries.splice(i, 1);
            }
          }
          activeQuery = ctx.createQuery();
          ctx.beginQuery(timerExt.TIME_ELAPSED_EXT, activeQuery);
        }

        window.__SAIT_TELEMETRY__.frames.push({
          frameTimeMs: dt,
          drawCalls: window.__SAIT_TELEMETRY__.currentFrame.drawCalls,
          triangles: window.__SAIT_TELEMETRY__.currentFrame.triangles,
          vertices: window.__SAIT_TELEMETRY__.currentFrame.vertices
        });

        window.__SAIT_TELEMETRY__.currentFrame = { drawCalls: 0, triangles: 0, vertices: 0, points: 0, lines: 0 };
        requestAnimationFrame(sampleFrame);
      };

      requestAnimationFrame(sampleFrame);
    }
    return ctx;
  };
})();
"""

async def run_telemetry_spider(target_url: str, headless_mode: bool = False):
    async with async_playwright() as p:
        # En servidores sin GPU física, agregar las banderas de SwANGLE documentadas por Chromium;
        # en estaciones con GPU real, ejecutar con headless=False para medir FPS genuinos.
        browser_args = ["--enable-webgl", "--ignore-gpu-blocklist"]
        if headless_mode:
            browser_args.extend([
                "--use-gl=angle",
                "--use-angle=swiftshader-webgl",
                "--enable-unsafe-swiftshader"
            ])

        browser = await p.chromium.launch(headless=headless_mode, args=browser_args)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        # 1. Abrir sesión directa al Chrome DevTools Protocol (CDP)
        cdp = await context.new_cdp_session(page)
        await cdp.send("Performance.enable")
        sys_info = await cdp.send("SystemInfo.getInfo")

        # 2. Inyectar el interceptor 3D antes de evaluar cualquier script del sitio
        await page.add_init_script(PRELOAD_3D_TELEMETRY_HOOK)

        # 3. Navegar y estimular el lienzo 3D (despertar renderizado on-demand)
        await page.goto(target_url, wait_until="networkidle")
        await page.mouse.move(640, 360)
        await page.mouse.down()
        for offset in range(0, 200, 20):
            await page.mouse.move(640 + offset, 360 + (offset // 2))
            await asyncio.sleep(0.05)
        await page.mouse.up()

        # Muestrear durante 5 segundos de ejecución activa
        await asyncio.sleep(5.0)

        # 4. Extraer contadores del motor C++ (Blink / V8) vía CDP
        cdp_metrics_raw = await cdp.send("Performance.getMetrics")
        cdp_metrics = {m["name"]: m["value"] for m in cdp_metrics_raw.get("metrics", [])}

        # 5. Extraer telemetría 3D acumulada en el hook
        webgl_data = await page.evaluate("() => window.__SAIT_TELEMETRY__")
        await browser.close()

        # 6. Consolidación de percentiles para el cubo analítico (DuckDB / Parquet)
        frame_times = [f["frameTimeMs"] for f in webgl_data["frames"] if f["frameTimeMs"] > 0]
        fps_samples = [1000.0 / ft for ft in frame_times]

        return {
            "url": target_url,
            "gpu_vendor": webgl_data["gpuVendor"],
            "gpu_renderer": webgl_data["gpuRenderer"],
            "is_software_renderer": webgl_data["isSoftwareRenderer"],
            "system_gpu_devices": sys_info.get("gpu", {}).get("devices", []),
            "frames_captured": len(fps_samples),
            "fps_median_p50": round(statistics.median(fps_samples), 2) if fps_samples else 0.0,
            "fps_1pct_low": round( sorted(fps_samples)[max(0, int(len(fps_samples) * 0.01))] , 2) if fps_samples else 0.0,
            "gpu_time_ns_median": int(statistics.median(webgl_data["gpuTimesNs"])) if webgl_data["gpuTimesNs"] else None,
            "draw_calls_per_frame_max": max((f["drawCalls"] for f in webgl_data["frames"]), default=0),
            "triangles_per_frame_max": max((f["triangles"] for f in webgl_data["frames"]), default=0),
            "vram_textures_created": webgl_data["texturesCreated"],
            "vram_buffers_created": webgl_data["buffersCreated"],
            "shaders_compiled": webgl_data["shadersCompiled"],
            "js_heap_used_mb": round(cdp_metrics.get("JSHeapUsedSize", 0) / (1024 * 1024), 2),
            "script_duration_s": round(cdp_metrics.get("ScriptDuration", 0.0), 4),
            "dom_nodes_count": int(cdp_metrics.get("Nodes", 0))
        }
```

## 7. Esquema de Datos Recomendado para el Cubo Analítico (Arquitectura Medallion)

Para almacenar estas mediciones en una arquitectura de lago de datos (Bronce $\rightarrow$ Plata $\rightarrow$ Oro en Parquet/DuckDB) y permitir que el motor de decisiones recomiende perfiles de hardware de manera confiable, se recomienda estructurar la tabla dimensional de sesiones de telemetría con los siguientes campos normalizados:

| Nombre de Columna | Tipo (DuckDB / Parquet) | Capa de Origen | Descripción Técnica y Regla de Validación |
| :--- | :--- | :--- | :--- |
| `run_id` | `UUID` / `VARCHAR` | Orquestador | Identificador único de la ejecución de la sonda. |
| `captured_at_utc` | `TIMESTAMP` | Orquestador | Marca de tiempo UTC del inicio del muestreo. |
| `target_url` | `VARCHAR` | Orquestador | URL canónica auditada por la araña. |
| `execution_mode` | `VARCHAR` | Configuración | `'windowed_gpu'` (hardware real con ventana) o `'headless_swangle'` (CI/CD en software). |
| `is_software_renderer` | `BOOLEAN` | `WEBGL_debug_renderer_info` | `true` si `UNMASKED_RENDERER_WEBGL` contiene `SwiftShader`, `llvmpipe` o `Software`. **Filtro obligatorio:** excluir filas con `true` al calcular recomendaciones de FPS de GPU. |
| `gpu_unmasked_vendor` | `VARCHAR` | `WEBGL_debug_renderer_info` | Fabricante reportado por el driver WebGL (`0x9245`). |
| `gpu_unmasked_renderer` | `VARCHAR` | `WEBGL_debug_renderer_info` | Cadena completa del dispositivo y API gráfica (`Direct3D11`, `Vulkan`, `Metal`, `OpenGL ES`). |
| `webgl_context_version` | `VARCHAR` | Preload Hook | `'webgl2'`, `'webgl'` o `'webgpu'`. |
| `fps_p50` | `DOUBLE` | Preload Hook (`rAF`) | Mediana de cuadros por segundo durante la ventana de interacción activa. |
| `fps_p01_low` | `DOUBLE` | Preload Hook (`rAF`) | Percentil 1 % más bajo de FPS (métrica crítica para detectar micro-cortes o *stuttering* por compilación de *shaders*). |
| `gpu_pass_time_ns_p50` | `BIGINT` | `EXT_disjoint_timer_query_webgl2` / `GPUQuerySet` | Mediana del tiempo real de ejecución en el silicio de la GPU en nanosegundos (solo muestras con `GPU_DISJOINT_EXT == false`). |
| `draw_calls_per_frame` | `INTEGER` | Preload Hook / `WebGLRenderer.info` | Conteo máximo de llamadas a `drawArrays`/`drawElements` en un cuadro completo. |
| `triangles_per_frame` | `BIGINT` | Preload Hook / `WebGLRenderer.info` | Total de triángulos enviados al rasterizador por cuadro. |
| `vram_textures_count` | `INTEGER` | Preload Hook / `WebGLRenderer.info` | Cantidad de objetos de textura alojados en memoria de video. |
| `vram_buffers_count` | `INTEGER` | Preload Hook | Cantidad de búferes de vértices/índices/UBOs creados en el contexto. |
| `js_heap_used_mb` | `DOUBLE` | CDP `Performance.getMetrics` | Memoria utilizada por el *heap* de V8 en megabytes (`JSHeapUsedSize / 1048576`). |
| `script_duration_ms` | `DOUBLE` | CDP `Performance.getMetrics` | Tiempo total de CPU invertido en ejecución de scripts JS en milisegundos. |
| `loaf_blocking_ms` | `DOUBLE` | W3C `long-animation-frames` | Suma de tiempo de bloqueo en cuadros de animación largos (>50 ms). |

## 8. Fuentes Primarias, Estándares y Literatura Científica

Toda la información y especificaciones de este documento provienen de las siguientes fuentes verificadas:

1. **Chromium Catapult Telemetry Framework (Repositorio Oficial):** [https://chromium.googlesource.com/catapult/+/HEAD/telemetry/](https://chromium.googlesource.com/catapult/+/HEAD/telemetry/)
2. **Documentación de Arquitectura y Perfiles de Chromium Telemetry:** [https://chromium.googlesource.com/catapult/+/HEAD/telemetry/docs/](https://chromium.googlesource.com/catapult/+/HEAD/telemetry/docs/)
3. **Chrome DevTools Protocol (CDP) — Especificación Oficial:** [https://chromedevtools.github.io/devtools-protocol/](https://chromedevtools.github.io/devtools-protocol/)
4. **CDP Dominio `Performance` y comando `Performance.getMetrics`:** [https://chromedevtools.github.io/devtools-protocol/1-3/Performance/](https://chromedevtools.github.io/devtools-protocol/1-3/Performance/)
5. **CDP Dominio `SystemInfo` y estructura `GPUInfo`:** [https://github.com/chromedp/cdproto/blob/master/systeminfo/systeminfo.go](https://github.com/chromedp/cdproto/blob/master/systeminfo/systeminfo.go)
6. **Perfetto Tracing Docs — Grabación automatizada en Chrome y Crossbench:** [https://perfetto.dev/docs/getting-started/chrome-tracing](https://perfetto.dev/docs/getting-started/chrome-tracing)
7. **Perfetto Tracing Docs — Formato JSON de trazas de Chrome y Track Events:** [https://perfetto.dev/docs/getting-started/other-formats](https://perfetto.dev/docs/getting-started/other-formats)
8. **MDN Web Docs — Extensión `WEBGL_debug_renderer_info`:** [https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info](https://developer.mozilla.org/en-US/docs/Web/API/WEBGL_debug_renderer_info)
9. **MDN Web Docs — Extensión `EXT_disjoint_timer_query` y `EXT_disjoint_timer_query_webgl2`:** [https://developer.mozilla.org/en-US/docs/Web/API/EXT_disjoint_timer_query](https://developer.mozilla.org/en-US/docs/Web/API/EXT_disjoint_timer_query)
10. **Web3DSurvey — Reporte de soporte y especificación `EXT_disjoint_timer_query_webgl2`:** [https://web3dsurvey.com/webgl2/extensions/EXT_disjoint_timer_query_webgl2](https://web3dsurvey.com/webgl2/extensions/EXT_disjoint_timer_query_webgl2)
11. **MDN Web Docs — Interfaz `WebGLQuery`:** [https://developer.mozilla.org/en-US/docs/Web/API/WebGLQuery](https://developer.mozilla.org/en-US/docs/Web/API/WebGLQuery)
12. **MDN Web Docs — WebGPU `GPUQuerySet` (Consultas de oclusión y timestamps):** [https://developer.mozilla.org/en-US/docs/Web/API/GPUQuerySet](https://developer.mozilla.org/en-US/docs/Web/API/GPUQuerySet)
13. **MDN Web Docs — `GPUCommandEncoder.beginRenderPass()` y `timestampWrites`:** [https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginRenderPass](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginRenderPass)
14. **MDN Web Docs — `GPUCommandEncoder.beginComputePass()`:** [https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginComputePass](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/beginComputePass)
15. **MDN Web Docs — `GPUCommandEncoder.writeTimestamp()`:** [https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/writeTimestamp](https://developer.mozilla.org/en-US/docs/Web/API/GPUCommandEncoder/writeTimestamp)
16. **BabylonJS / Spector.js — Repositorio Oficial de Captura e Introspección WebGL:** [https://github.com/BabylonJS/Spector.js/](https://github.com/BabylonJS/Spector.js/)
17. **Spector.js — Documentación de Uso Programático (`window.spector`):** [https://github.com/BabylonJS/Spector.js/blob/master/documentation/extension.md](https://github.com/BabylonJS/Spector.js/blob/master/documentation/extension.md)
18. **Three.js Docs — Especificación de `WebGLRenderer.info` (`memory` y `render`):** [https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info](https://threejs.org/docs/#api/en/renderers/WebGLRenderer.info)
19. **Documentación de GPU de Chromium — Uso de SwiftShader y banderas SwANGLE en modo Headless:** [https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md](https://chromium.googlesource.com/chromium/src/+/main/docs/gpu/swiftshader.md)
20. **OpenWPM — Framework de Medición y Telemetría de Privacidad Web (GitHub):** [https://github.com/openwpm/OpenWPM](https://github.com/openwpm/OpenWPM)
21. **Englehardt & Narayanan — *Online Tracking: A 1-million-site Measurement and Analysis*:** [https://www.researchgate.net/publication/310821260_Online_Tracking_A_1-million-site_Measurement_and_Analysis](https://www.researchgate.net/publication/310821260_Online_Tracking_A_1-million-site_Measurement_and_Analysis)
22. **Estudio sobre Detección de Crawlers y Fingerprinting WebGL/Performance (arXiv:2606.14525v1, 2026):** [https://arxiv.org/html/2606.14525v1](https://arxiv.org/html/2606.14525v1)
23. **Estudio sobre Crawlers Agénticos vs. Bloqueo en Páginas Profundas (arXiv:2611.06197, 2026):** [https://arxiv.org/html/2611.06197](https://arxiv.org/html/2611.06197)
24. **ByteDefender — Clasificación de Fingerprinting a Nivel de Bytecode en V8 (arXiv:2509.09950v1):** [https://arxiv.org/html/2509.09950v1](https://arxiv.org/html/2509.09950v1)
25. **Sitespeed.io / Browsertime — Motor de Telemetría Visual y de Navegador:** [https://github.com/sitespeedio/browsertime](https://github.com/sitespeedio/browsertime)
26. **HTTP Archive — Infraestructura de Rastreo y Telemetría Web a Gran Escala:** [https://github.com/httparchive](https://github.com/httparchive)
27. **W3C Navigation Timing Level 2 Specification:** [https://www.w3.org/TR/navigation-timing-2/](https://www.w3.org/TR/navigation-timing-2/)
28. **W3C Resource Timing Specification:** [https://www.w3.org/TR/resource-timing/](https://www.w3.org/TR/resource-timing/)
29. **W3C Long Animation Frames API (LoAF):** [https://www.w3.org/TR/long-animation-frames/](https://www.w3.org/TR/long-animation-frames/)
30. **W3C Long Tasks API:** [https://www.w3.org/TR/longtasks-1/](https://www.w3.org/TR/longtasks-1/)
31. **OpenTelemetry — Convenciones Semánticas e Instrumentación de Navegador:** [https://opentelemetry.io/docs/specs/semconv/resource/browser/](https://opentelemetry.io/docs/specs/semconv/resource/browser/)
32. **Playwright Python — Documentación Oficial de `CDPSession`:** [https://playwright.dev/python/docs/api/class-cdpsession](https://playwright.dev/python/docs/api/class-cdpsession)
33. **Stygian Browser — Automatización CDP Antidetección y Aleatorización WebGL en Rust:** [https://docs.rs/stygian-browser](https://docs.rs/stygian-browser)
