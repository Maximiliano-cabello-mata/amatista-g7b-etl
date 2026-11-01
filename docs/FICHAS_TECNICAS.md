# Fichas técnicas de G7B y Amatista

Fecha: 2026-11-01. Definición exacta de cada concepto interno, para que cada palabra signifique una sola cosa. Si un documento usa un término de otra forma, manda esta ficha. Los umbrales numéricos son **iniciales**: se ajustan con mediciones, y cada cambio se anota aquí con fecha.

**Estado:** ✅ hecho y probado con datos reales · 🟡 hecho, sin datos o sin probar en real · ⬜ planteado.

## 0. Mapa de conceptos

```text
            AMATISTA (enseña)                         G7B (sabe y mide)
   plataforma · prácticas · Goliat              lago · embudo · cubo · modelo de costos
                 │                                          │
                 └────────────►  GEODA (el kernel 3D)  ◄─────┘
                        Corazón (interacción) + Planificador (recursos)
                                     │ adaptadores
                  Blender · editor web · Godot · FreeCAD · librerías libres
```

---

## 1. Los proyectos

### 1.1 Amatista ✅
- **Es:** la plataforma educativa de 3D: PWA, API (Oracle), cursos, prácticas validadas, Goliat y el add-on.
- **No es:** un programa 3D ni una base de datos de telemetría.
- **Vive en:** Oracle Cloud (API y base) y Cloudflare (PWA). Repo `amatista`.
- **Relación con G7B:** cliente. Consume perfiles, búsqueda y equivalencias por la API de G7B, y nunca le entrega datos personales.

### 1.2 G7B ✅ (infraestructura) · 🟡 (datos)
- **Es:** la base de **conocimiento** (texto con fuente y licencia) y de **mediciones** (telemetría) del 3D libre, más los modelos que salen de ellas.
- **No es:** un motor 3D, un fork de Blender ni parte del código de Amatista.
- **Vive en:** Zyte, Azure (lago), MongoDB Atlas y GitHub Actions; más adelante Heroku (API). Repo `amatista-g7b-etl`.
- **Licencias:** código AGPL-3.0 (propuesta); datos publicados CC BY 4.0 o CC0 (propuesta).

### 1.3 Geoda: el kernel 3D ⬜ (nombre de trabajo)
- **Es:** la capa que **administra el trabajo 3D según los recursos del equipo**. Recibe operaciones, decide cómo y dónde correrlas con datos medidos, y las ejecuta con herramientas libres que ya existen.
- **No es:** un programa 3D nuevo, un motor de render propio ni un fork de Blender.
- **Partes:**
  - el **Corazón** (1.4), que decide qué ve y qué hace la persona;
  - el **planificador** (2.3), que decide cómo se ejecuta cada operación;
  - los **contratos de operación** (2.1);
  - los **controladores** (2.2).
- **Por qué "Geoda":** la amatista se forma dentro de una geoda; el kernel es lo que contiene y sostiene las herramientas. Propuesta: confirmar el nombre antes de usarlo en público.
- **Se sabe que funciona cuando:** en un equipo N1 o N2, una práctica que sin el kernel no se puede hacer, con el kernel sí se hace, o se hace más rápido (prueba del reporte de propuestas).

### 1.4 Corazón (`amatista.corazon/1`) ✅
- **Es:** el contrato de interacción de Amatista: lugares, señales, turnos, andamio y ramas. Existe y está probado en el repo `amatista`.
- **No es:** el planificador de recursos. El Corazón decide **qué se muestra**; el planificador decide **cómo se ejecuta**.
- **Partes:** adaptadores por programa (Blender y A-Frame estables; Maya y 3ds Max en borrador), extensiones y ramas (`amatista.rama/1`).

### 1.5 Amatista para Blender ✅ (antes "Blender Amatista")
- **Es:** la plantilla de aplicación más el add-on GPL-3.0 que convierte a Blender en el entorno de Amatista, sin recompilarlo.
- **Nota de marca:** "Blender" es una marca de la Blender Foundation. Usar "Amatista para Blender", no "Blender Amatista", salvo autorización.

### 1.6 Editor web de Amatista ⬜
- **Es:** un editor 3D ligero en el navegador (sobre el Motor Web de Amatista y three.js), para los niveles N0 y N1, que exporta a glTF.
- **No es:** Blender en el navegador.
- **Se adapta:** lee las capacidades del dispositivo (WebGL o WebGPU, memoria, núcleos) y aplica un perfil web.

---

## 2. El kernel por dentro

### 2.1 Operación ⬜
- **Es:** una tarea 3D básica con entrada, parámetros y salida definidos. Es la "llamada al sistema" del kernel.
- **Catálogo inicial:**

| Operación | Entrada | Salida | Controladores candidatos (libres) |
|---|---|---|---|
| `subdividir` | malla, niveles | malla | OpenSubdiv (vía Blender) |
| `simplificar` | malla, proporción | malla | meshoptimizer |
| `booleana` | dos mallas, tipo | malla | Manifold |
| `desenvolver_uv` | malla | malla con UV | xatlas |
| `renderizar` | escena, motor, muestras, resolución | imagen | Cycles, EEVEE, Workbench (Blender); Embree |
| `quitar_ruido` | imagen | imagen | Open Image Denoise |
| `simular` | escena, pasos | escena | Bullet |
| `nube_de_puntos` | puntos | malla | Open3D |

- **Contrato propuesto:** `g7b.operacion/1`, con nombre, parámetros, tamaño de la entrada, versión del controlador y licencia.

### 2.2 Controlador ⬜
- **Es:** la implementación concreta de una operación con una herramienta libre, en una versión fija.
- **Regla:** solo licencias compatibles con GPL-3.0 (PLAN, sección 6.2). Cada controlador declara su licencia y su versión.

### 2.3 Planificador ⬜
- **Es:** el que decide, para cada operación, cuatro cosas:
  1. **Si cabe** (memoria).
  2. **Con qué calidad** (ajustes).
  3. **Dónde** (este equipo, otra PC de la red o la nube).
  4. **Con qué controlador.**
- **Entra:** la operación, la huella del equipo (3.2) y el modelo de costos (2.4).
- **Sale:** un plan de ejecución.
- **Primera versión, más simple:** elegir el perfil de ajustes (3.4) para la escena completa.

### 2.4 Modelo de costos ⬜
- **Es:** un modelo aprendido de la telemetría que **predice** tiempo, memoria y fps de una operación en un equipo, incluso en uno que nadie ha medido, a partir de sus especificaciones.
- **Técnica inicial:** gradient boosting o una red pequeña. Ya entrenado debe pesar menos de 1 MB y correr **localmente** en el add-on.
- **Se entrena:** en Colab o Camber, con datos del cubo (5.3).
- **Se sabe que funciona cuando:** el error medio de predicción en equipos que no vio al entrenar es **menor al 25 %** (umbral inicial).

---

## 3. Equipos y ajustes

### 3.1 Niveles de equipo ✅ (definición) · 🟡 (clasificación automática)

| Nivel | Criterio exacto (inicial) | Qué corre |
|---|---|---|
| **N0** | Celular, tableta o Chromebook; solo navegador con WebGL 2 | Editor web |
| **N1** | No cumple los mínimos del Blender actual: GPU sin OpenGL 4.3, o RAM < 8 GB | Blender 3.6 LTS o 2.93; perfil mínimo |
| **N2** | GPU integrada con OpenGL 4.3 o Vulkan; RAM de 8 a 16 GB | Blender actual; perfil ligero |
| **N3** | GPU dedicada de 4 a 8 GB de VRAM | Blender completo; EEVEE fluido |
| **N4** | GPU dedicada de 12 GB o más de VRAM | Cycles en GPU, simulación, escenas pesadas |

Desde Blender 4.0 el mínimo es OpenGL 4.3; Blender 3.x pedía 3.3. Si la RAM y la GPU dan niveles distintos, cuenta el más bajo.

### 3.2 Huella del equipo ✅
- **Es:** el SHA-256 (los primeros 16 caracteres) de: modelo de CPU, RAM redondeada a GB, nombres de las GPU, sistema operativo y arquitectura.
- **Identifica:** un **tipo de equipo**, nunca a una persona. No incluye usuario, nombre del equipo ni rutas.

### 3.3 Fluidez ✅ (definición)

| Estado | Vista 3D (mediana) | Edición (operación común) |
|---|---|---|
| **Fluido** | 30 fps o más | menos de 100 ms |
| **Usable** | de 15 a 30 fps | de 100 a 500 ms |
| **No usable** | menos de 15 fps | más de 500 ms |

### 3.4 Perfil (`g7b.perfil/1`) 🟡
- **Es:** un conjunto de ajustes (subdivisión, Simplify, muestras, resolución, motor) recomendado para un nivel de equipo y una versión de Blender, **con la evidencia** que lo respalda: celdas del cubo y número de mediciones.
- **Hoy existen tres perfiles de prueba en la sonda:** mínimo, ligero y completo. Todavía no hay perfiles recomendados.
- **Regla de elección:** el perfil con más calidad (3.5) que mantenga la fluidez "fluido" en ese nivel.

### 3.5 Calidad visual ⬜
- **Es:** cuánto se parece un render con ajustes reducidos a uno de referencia con ajustes completos.
- **Métricas:** SSIM (clásica) y LPIPS (red neuronal que imita la percepción).
- **Umbral inicial:** SSIM de 0.95 o más, o LPIPS de 0.10 o menos, cuenta como "sin pérdida visible".

---

## 4. Telemetría

### 4.1 Medición (`g7b.medicion/1`) ✅
- **Es:** una corrida de la sonda: huella del equipo, versión de Blender, escena, perfil y, por cada prueba, valores, mediana y variación.
- **Es válida si:** tiene 3 repeticiones o más tras un calentamiento descartado, la variación es del 10 % o menos y `sintetico: false`.
- **Hoy hay:** 1 (servidor Linux sin GPU, Blender 5.2.3).

### 4.2 Sondas

| Sonda | Mide | Estado |
|---|---|---|
| **Sonda de Blender** (`sonda/g7b_sonda.py`) | Edición, primera evaluación, animación, vista 3D, render | ✅ probada sin ventana; falta ventana y GPU en una PC real |
| **Sonda de operaciones** | Cada operación de 2.1 en mallas de 10 mil, 100 mil y 1 millón de polígonos | ⬜ |
| **Sonda web** | fps de WebGL y WebGPU, memoria y escenas del editor web en el navegador | ⬜ |

### 4.3 Etapas de la telemetría
T0 internet · T1 tus equipos · T2 nube (Actions, Colab, Azure) · T3 universidad, con acuerdos · T4 uso real, con consentimiento. Detalle: PLAN, sección 5.2.

### 4.4 Dato sintético ✅ (regla)
Cualquier dato generado por una IA o simulado. Lleva `sintetico: true`, vive en `sintetico/` y **nunca** entra al cubo ni a un reporte.

---

## 5. Datos y almacén

### 5.1 Lago ✅
Contenedor `lago` en Azure (West US 2), organizado por zonas:
- **Bronce:** crudo; nunca se sobrescribe.
- **Plata:** validado.
- **Oro:** curado.
- **Sintético:** datos generados.
- **Control:** estado de los procesos.
- **Tmp:** temporales; se borran solos a los 7 días.

### 5.2 Embudo ✅
Cinco etapas en orden: entrada, calidad, duplicados, relevancia y valor. Cada rechazo lleva su motivo. Se aplica al **texto**; las mediciones tienen su propia validación (4.1). Detalle: `docs/INGESTA.md`.

### 5.3 Cubo ⬜
- **Es:** el resumen de **todas** las mediciones por cada combinación de dimensiones, calculado de una vez (DuckDB, `GROUP BY CUBE`) y guardado en oro.
- **Hechos:** `hechos_medicion` (sonda) y `hechos_render` (Blender Open Data).
- **Dimensiones:** dispositivo, versión, escena, perfil, tiempo y origen.
- **Medidas por celda:** mediana, p10, p90 y número de muestras.
- **Una celda es confiable si:** tiene 5 muestras o más, de 3 equipos distintos o más. Si no, se muestra marcada como "poca evidencia".
- **Salidas:** Parquet en oro, rebanadas en MongoDB (`cubo_*`) y un CSV para Excel.

### 5.4 Conocimiento (texto) ✅
Documentos aceptados por el embudo, en `conocimiento_3d.documentos`. **No alimenta al kernel:** sirve para que una IA consulte la documentación (MCP) y para Goliat. Hoy hay 5.

---

## 6. Glosario rápido

| Término | Significa aquí |
|---|---|
| Fuente | Un sitio o conjunto de datos del catálogo (`fuentes/catalogo.yml`), con licencia confirmada |
| Sensor | El que detecta si una fuente tiene algo nuevo |
| Disparador | El que lanza la extracción cuando el sensor detecta algo |
| Rebanada | Una parte del cubo con un eje fijo |
| API de G7B | La "ventanilla" para que otros programas pregunten a G7B (todavía no existe) |
| MCP | La forma en que una IA consulta a G7B como herramienta |
| Interruptor | La variable `G7B_INGESTA_ACTIVA`: sin ella en `true`, las tareas programadas no corren |
