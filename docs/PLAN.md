# Plan de G7B: datos de calidad para un 3D libre que funcione en cualquier computadora

Fecha: 2026-11-01. Documento rector de este repositorio. Si otro documento contradice este, manda este. Reemplaza las fases A, B y C de [ARQUITECTURA_CLOUD.md](../ARQUITECTURA_CLOUD.md), que se conserva como historia del primer despliegue.

## 1. Qué es G7B, en una frase

> **G7B es la base de conocimiento y de mediciones de un 3D libre:** reúne lo que se sabe (documentación, técnicas publicadas de la industria y equivalencias entre programas) y lo que se mide (rendimiento en computadoras reales, desde las más viejas hasta las más potentes), con fuente, versión y licencia, para que el Corazón Amatista y una IA puedan usarlo.

### Lo que G7B es y lo que no

| Es | No es |
|---|---|
| Un proyecto propio, separado de Amatista. Amatista lo consume como un cliente más, por una API | Parte del código de Amatista. Amatista vive en Oracle; G7B vive en sus propios servicios |
| Datos con pregunta, fuente, versión y licencia | Una aspiradora de internet. No se extrae nada que no responda una pregunta de la sección 3 |
| Una capa encima de herramientas libres que ya existen: Blender primero, después Godot, FreeCAD, Krita y otras | Un motor 3D nuevo ni un fork de Blender. No se reinventa la rueda |
| Técnicas públicas de la industria (artículos, charlas, cursos) traducidas a herramientas libres | Código, herramientas internas o material filtrado de ninguna empresa |
| Mediciones de computadoras reales, con consentimiento | Datos personales, contenido de escenas ni nada que identifique a una persona |

### Cómo encaja con Amatista y con Blender

```text
 Herramientas libres que ya existen     Blender · Godot · FreeCAD · Krita · MeshLab · glTF · OpenUSD
            ▲ adaptadores
 Corazón Amatista (amatista.corazon/1)  contrato común, perfiles por programa, señales, ramas
            ▲ perfiles, equivalencias, técnicas (datos de G7B)
 G7B                                    conocimiento + mediciones, con fuente, versión y licencia
            ▲ telemetría con consentimiento
 Personas y computadoras reales         desde una PC de 2012 hasta una estación de trabajo
```

El Corazón ya existe en `amatista` (`engine/amatista_engine/corazon/`): un contrato, adaptadores, perfiles de Blender y A-Frame estables, y perfiles de Maya y 3ds Max en borrador. G7B no lo reemplaza: **lo alimenta con datos**. Blender Amatista sigue siendo una plantilla de aplicación más un add-on, nunca un Blender recompilado.

## 2. Qué es un dato de calidad aquí

No se trata de juntar mucho. Un dato entra a G7B solo si cumple las siete reglas:

1. **Tiene pregunta.** Responde al menos una pregunta del catálogo (sección 3). Si no hay pregunta, no se extrae.
2. **Es de fuente primaria.** La documentación oficial le gana al tutorial; el artículo original le gana al resumen de un blog; una medición propia le gana a una opinión de foro.
3. **Dice su versión.** "Blender 4.2 LTS", "Godot 4.3". Un dato sin versión no sirve en 3D: lo que era cierto en 2.79 hoy es falso.
4. **Dice su licencia.** Si es abierta (CC BY, CC BY-SA, CC0, GPL), se guarda el texto completo. Si tiene derechos reservados, solo el enlace, los metadatos y un resumen propio. Si no se sabe, no entra.
5. **Dice de dónde vino.** URL, fecha de extracción, araña o sonda que lo trajo, y huella (hash) del contenido.
6. **No está repetido.** Se identifica por URL o por huella. Las corridas nuevas actualizan; no duplican.
7. **Aporta algo que una IA no sabe ya.** Lo genérico ("qué es un modificador") vale poco. Lo valioso es lo específico, lo versionado y lo medido: "en una Intel HD 4000, Blender 3.6 abre esta escena a 12 cuadros por segundo con estos ajustes".

### Cómo se vigila la calidad

| Control | Cuándo | Qué hace si falla |
|---|---|---|
| Esquema (contratos de la sección 6) | Al entrar a la zona plata | El registro se queda en bronce, marcado con el motivo |
| Licencia y versión obligatorias | Al entrar a plata | Igual |
| Duplicados por huella | Al entrar a plata | Se descarta la copia |
| Valores imposibles (por ejemplo, 900 cuadros por segundo en una gráfica integrada de 2012) | En las mediciones | Va a revisión, no a oro |
| Cobertura por nivel de equipo (sección 5) | Cada semana | El reporte marca qué niveles faltan |
| Muestra humana: 20 registros al azar | Cada semana | Si más de 3 de 20 son basura, **esa fuente se pausa** hasta corregir la araña |
| Monitor de cada trabajo programado (Sentry) | En cada corrida | Aviso si una araña o un trabajo no reportó |

## 3. Las preguntas que los datos deben responder

Cada fuente y cada medición existe para responder alguna de estas preguntas. Si aparece una pregunta nueva, se agrega aquí antes de extraer nada.

| # | Pregunta | Para qué sirve | Datos que la responden |
|---|---|---|---|
| P1 | En una computadora de cierto nivel, ¿qué ajustes de Blender permiten trabajar con fluidez? | Perfiles de hardware del Corazón | Sonda de rendimiento, Blender Open Data |
| P2 | ¿Qué versión de Blender conviene en cada nivel de equipo? | Recomendar la versión en Amatista | Sonda en varias versiones, compatibilidad de OpenGL |
| P3 | ¿Qué tan común es cada nivel de equipo en la población real? | Definir el "peor caso" con datos | Encuesta de hardware de Steam (agregada), telemetría de Amatista |
| P4 | ¿Qué hace Maya o 3ds Max que la gente usa de verdad, y cómo se hace con herramientas libres? | Mapa de equivalencias y lista de brechas | Documentación pública, listas de funciones, flujos de trabajo |
| P5 | ¿Qué técnicas publicadas por la industria se pueden aplicar con herramientas libres, y cuánto cuestan en hardware? | Fichas de técnica para prácticas, ajustes y add-ons | SIGGRAPH, GDC, laboratorios de investigación, arXiv |
| P6 | ¿Cómo se hace X en la versión Y de Blender (o de Godot, FreeCAD...)? | Que una IA responda con la fuente; servidor MCP | Manuales y referencias de API oficiales |
| P7 | ¿En qué paso de qué práctica se atora la gente, y depende de su computadora? | Mejorar prácticas y señales del Corazón | Telemetría del add-on, con consentimiento |

## 4. Fuentes

### 4.1 Rendimiento y hardware (P1, P2, P3)

| Fuente | Qué trae | Licencia | Prioridad |
|---|---|---|---|
| **Blender Open Data** (opendata.blender.org) | Resultados reales del benchmark oficial de Blender por CPU y GPU, enviados por usuarios | Datos abiertos (licencia exacta por confirmar en F0) | **Primera**: análisis el primer fin de semana |
| **Sonda de rendimiento G7B** (sección 5) | Mediciones propias: vista 3D, edición y render, con perfiles de ajustes | Propia: se publica agregada | Desde la semana 1 |
| **Encuesta de hardware de Steam** | Qué hardware tiene la gente cada mes | Sin licencia de redistribución: solo cifras agregadas y el enlace | Mensual |
| **Notas de versión de Blender** | Requisitos mínimos y cambios de rendimiento por versión | CC BY-SA | Por versión |

### 4.2 Documentación primaria de software libre (P6)

Blender (manual, referencia de la API `bpy`, notas de versión, documentación de desarrollo); después Godot, FreeCAD, Krita y MeshLab, y las especificaciones de glTF, OpenUSD y MaterialX. El manual de Blender es CC BY-SA 4.0. **La licencia de cada otra fuente se confirma y se anota en el catálogo antes de extraerla.** Se extrae una vez por versión y se revisa cada semana lo nuevo; no se rastrea a diario.

### 4.3 Técnicas públicas de la industria (P5)

Cursos y artículos de SIGGRAPH (por ejemplo "Advances in Real-Time Rendering"), charlas de la GDC con video o diapositivas públicas, publicaciones de laboratorios de estudios (EA SEED, Ubisoft La Forge, Activision Research), la sección de gráficos de arXiv (`cs.GR`) y libros abiertos como *Physically Based Rendering*.

Así se aprovechan las técnicas de empresas como Rockstar sin usar nada suyo: **se estudia lo que ellos mismos publicaron y se traduce a herramientas libres**. Cada técnica se vuelve una ficha (`g7b.tecnica/1`): qué es, de dónde sale, qué herramienta libre ya la implementa (EEVEE, Cycles, Geometry Nodes, Godot), cómo se aplica y cuánto cuesta en hardware. La mayoría de estos documentos tiene derechos reservados: se guarda el enlace, los metadatos y un resumen propio, no el texto.

### 4.4 Equivalencias con Maya y 3ds Max (P4)

La meta no es copiar Maya ni 3ds Max, sino **que una persona pueda hacer el mismo trabajo sin pagar licencia**. Se construye un catálogo de tareas reales (modelado, UV, rigging, animación, render y exportación), y cada tarea queda en uno de cuatro estados:

| Estado | Significado |
|---|---|
| Nativo | Blender (u otra herramienta libre) ya lo hace igual o mejor |
| Con add-on libre | Existe un add-on con licencia libre que lo cubre; se integra, no se reescribe |
| Con ajuste Amatista | Se cubre con un perfil, una plantilla, un mapa de teclas o un nodo de Geometry Nodes de Amatista |
| Brecha | No existe; entra a la lista de trabajo ordenada por cuánto se usa |

**Meta medible:** cobertura ponderada de al menos 50 % del catálogo, contando las tareas por cuánto se usan, no por cuántas son.

**"Sin que se vea obvio" tiene reglas:** se implementa el concepto, no la expresión. No se copian nombres registrados, íconos, textos de su documentación ni el diseño de su interfaz. Cada cosa lleva nombre y estilo propios (el sistema Facetas de Amatista). Blender ya trae un mapa de teclas "Industry Compatible" para quien viene de otros programas; se aprovecha. Algunas técnicas de gráficos están patentadas: antes de convertir una técnica en add-on, se revisa si tiene patente vigente. Esto no es asesoría legal; ante una duda seria, se consulta.

### 4.5 Comunidad (P6, después de F2)

Los volcados públicos de Blender Stack Exchange (CC BY-SA), filtrados por versión y puntuación. Entran solo después de que la documentación primaria esté completa y medida.

### 4.6 Escenas de prueba

Para la sonda: modelos y texturas de Poly Haven (CC0) y archivos de demostración de Blender con licencia abierta. Son las mismas escenas para todas las computadoras, así que los resultados se pueden comparar.

### 4.7 Lo que nunca entra

- Código filtrado de cualquier empresa, ni fragmentos ni "solo para leerlo". Contamina todo el proyecto.
- Material bajo contrato o licencia de uso (NDA, EULA), como el código de Unreal.
- Cursos de pago, aunque estén publicados sin permiso.
- Datos personales, contenido de escenas de alumnos, o telemetría sin consentimiento.
- Sitios cuyas condiciones prohíben la extracción. Se respeta `robots.txt` (`ROBOTSTXT_OBEY = True` ya está puesto).

## 5. Telemetría: de la computadora más vieja a la más potente

Esta es la parte que nadie más tiene, y la que justifica G7B. Hay dos instrumentos, los dos construidos sobre lo que Blender ya trae.

### 5.1 Niveles de equipo

| Nivel | Ejemplo | Qué se espera |
|---|---|---|
| N0 | Celular o Chromebook, en el navegador | Visor y taller básico de A-Frame |
| N1 | PC de 2012 a 2015: gráfica integrada antigua, 4 GB de RAM, disco mecánico | Blender LTS antiguo (2.93 o 3.6) con perfil mínimo |
| N2 | PC modesta actual: gráfica integrada moderna (por ejemplo Ryzen 5 5600G), 8 a 16 GB | Blender actual con perfil ligero |
| N3 | GPU dedicada de 4 a 8 GB | Blender completo, render EEVEE fluido |
| N4 | GPU de 12 GB o más, estación de trabajo | Cycles, simulaciones, escenas pesadas |
| Nube | Máquinas de Azure y ejecutores de GitHub Actions, sin GPU | Control: miden CPU y memoria de forma repetible |

### 5.2 Sonda de rendimiento (`g7b-sonda`)

Un script de Python que se ejecuta **dentro de Blender**, sin software nuevo:

- **Huella del equipo:** modelo de CPU y núcleos, RAM, modelo de GPU, memoria de video, controlador, versión de OpenGL o Vulkan (`gpu.platform` de Blender), sistema operativo y versión de Blender. Sin nombre de usuario ni de equipo.
- **Escenas estándar:** ligera, media y pesada (sección 4.6).
- **Perfiles de ajustes:** de mínimo a completo (Workbench o sólido, Simplify, niveles de subdivisión, EEVEE, Cycles con pocas muestras más quitar el ruido).
- **Mediciones:** tiempo de abrir la escena; cuadros por segundo de la vista 3D (necesita ventana); tiempo de operaciones de edición comunes; tiempo de render de un cuadro; memoria máxima; errores.
- **Dos modos:** sin ventana (`blender -b`), para render y edición en contenedores y en la nube; y con ventana, para la vista 3D en computadoras reales.
- **Tres formas de correrla:** como botón "Medir mi equipo" en el add-on de Amatista; como script suelto para laboratorios (universidades, centros comunitarios); y en contenedor para la nube.
- **Varias versiones de Blender** en N1 y N2, para responder P2.

No sustituye al benchmark oficial de Blender, que solo mide render: lo complementa con la vista 3D, la edición y los perfiles.

### 5.3 Telemetría de uso en el add-on de Amatista

Eventos que ya existen en el Corazón (paso iniciado, paso cumplido, señal mostrada o perdida, tiempo en el paso, deshacer, errores), más muestras de cuadros por segundo y el nivel del equipo.

- **Solo con consentimiento explícito**, que se puede retirar en cualquier momento, y con aviso de privacidad publicado antes de activarla.
- **Identificador anónimo** por instalación. Sin nombre, sin correo y sin contenido de la escena.
- **Se publica solo agregado**, en grupos de al menos 5 equipos, para que nadie pueda identificarse.
- Esta parte se programa en el repo `amatista`, no aquí. G7B solo define el contrato `g7b.evento/1` y recibe los datos.

### 5.4 Metas de cobertura (12 semanas)

- Al menos **30 equipos distintos medidos** con la sonda, con **al menos 5 por nivel** de N1 a N4.
- Al menos 3 versiones de Blender medidas en N1 y N2.
- Para conseguir equipos: tus propias PCs (la PC 4 con Ryzen 5 5600G es un N2 perfecto), laboratorios de la UTN, compañeros y familia, y la nube como control.

Sin cobertura de N1 no hay conclusiones sobre "computadoras viejas"; el reporte semanal lo dice claramente en vez de inventarlo.

## 6. Arquitectura

### 6.1 Flujo de datos y zonas

Se usa la convención de zonas por calidad: bronce (crudo), plata (validado) y oro (curado, listo para usarse). Siempre **ELT**: primero se guarda el crudo y después se transforma, para poder reprocesar sin volver a extraer.

```text
 FUENTES          INGESTA                BRONCE (crudo)        PLATA (validado)        ORO (curado)              SERVIR / VER
 web ─────────►  Zyte (arañas) ──┐
 Git, volcados ► GitHub Actions ─┼────►  Azure Blob           Azure Blob (Parquet)    MongoDB Atlas:            API G7B + MCP (Heroku)
 Open Data ────► GitHub Actions ─┤       JSONL / HTML ──────► documentos y ─────────► fragmentos + vectores ──► Claude y otras IA
 sonda ────────► API de G7B ─────┤       sin tocar            mediciones limpias      Parquet: tablas de       Tablero público (Pages)
 telemetría ───► API de G7B ─────┘                            (controles sección 2)   hechos y dimensiones     Cuadernos (Deepnote)
                                         ▲ procesamiento: tu Ryzen y Actions (ligero) · Camber (GPU, pesado)
                                         ▲ secretos: Doppler · vigilancia: Sentry
```

### 6.2 Un servicio por capa

| Capa | Servicio | Por qué | Cuánto dura |
|---|---|---|---|
| Ingesta web | Zyte Scrapy Cloud (ya conectado) | Una unidad gratis para siempre; tiempo de rastreo ilimitado | Datos 120 días: por eso se copian al lago |
| Descargas y reloj | GitHub Actions (GitHub Pro) | Tareas programadas sin máquinas encendidas | Mientras seas estudiante |
| Lago (bronce y plata) | Azure Blob Storage | Barato; el crédito de $100 dura casi solo para esto | Crédito de estudiante |
| Procesamiento pesado | Camber | 40 h de CPU y 5 h de GPU **cada mes**; servidor MCP para Claude Code | Mientras estudies |
| Procesamiento ligero | Tu Ryzen y GitHub Actions | Gratis | — |
| Conocimiento (oro) | MongoDB Atlas M0 (ya activo) con búsqueda por vectores | Ya está; 512 MB alcanzan para la documentación de Blender con vectores | Gratis; los $50 se guardan hasta llegar a unos 400 MB |
| Analítica (warehouse oro) | Parquet en Azure Blob + DuckDB | Un warehouse de pago es innecesario a esta escala | Gratis |
| Servir | Heroku: API de G7B y servidor MCP | El crédito más largo: $13 al mes durante 24 meses | 24 meses |
| Secretos | Doppler | Una sola fuente de claves; nada pegado a mano en Zyte | Mientras estudies |
| Vigilancia | Sentry (monitores de tareas programadas) | Avisa cuando una araña deja de reportar | 1 año, renovable |
| Publicación | GitHub Pages + dominio gratis de Name.com (`.dev` o `.software`) | Identidad propia, separada de amatista-3d.tech | Dominio por 1 año |

**Créditos que se guardan:** los $50 de MongoDB (hasta acercarse al límite del M0) y los $200 de Visual Studio Dev Essentials, que **solo duran el primer mes**: se usan en una semana de benchmarks en varios tamaños de máquina, planeada de antemano. Revisar antes si pide tarjeta y si convive con la cuenta de estudiante de Azure.

**Seguridad:**
- Un usuario de MongoDB por componente: uno que solo escribe (Zyte y los trabajos) y otro que solo lee (la API).
- La regla de red `0.0.0.0/0` se mantiene porque Zyte, Actions y Heroku cambian de IP; los permisos mínimos limitan el daño posible.
- La API que recibe mediciones y telemetría pide clave por instalación y tiene límite de envíos, para que nadie la llene de datos falsos.

### 6.3 Contratos de datos

Mismo estilo que `amatista.practice/2` y `amatista.corazon/1`: JSON versionado, validado con un esquema.

| Contrato | Qué describe | Campos clave |
|---|---|---|
| `g7b.documento/1` | Un documento de conocimiento | url, fuente, programa, versión, licencia, título, texto o resumen, huella, fecha |
| `g7b.fragmento/1` | Un pedazo de documento con su vector | documento, encabezado, texto, vector, versión |
| `g7b.medicion/1` | Una corrida de la sonda | huella del equipo, nivel, escena, perfil, versión de Blender, métricas, errores |
| `g7b.evento/1` | Un evento de telemetría de práctica | instalación anónima, práctica, paso, tipo de evento, duración, nivel del equipo |
| `g7b.tecnica/1` | Una técnica de la industria | nombre, fuente, idea, herramienta libre que la implementa, costo en hardware, ejemplo |
| `g7b.equivalencia/1` | Una tarea de Maya o 3ds Max | tarea, disciplina, estado (sección 4.4), cómo se hace en libre, uso relativo |
| `g7b.perfil/1` | Ajustes recomendados por nivel de equipo | nivel, versión de Blender, ajustes, cuadros por segundo esperados, evidencia |

### 6.4 Warehouse: modelo en estrella

| Tabla de hechos | Una fila es | Dimensiones |
|---|---|---|
| `hechos_medicion` | Una métrica de una corrida de la sonda | equipo, nivel, escena, perfil, versión de Blender, fecha |
| `hechos_paso` | Un paso de una práctica hecho por una instalación | práctica, paso, nivel del equipo, versión de Blender, fecha |
| `hechos_cobertura` | Una tarea del catálogo de equivalencias en un momento | tarea, disciplina, estado, fecha |

Todo en Parquet y consultado con DuckDB, desde tu PC, desde Deepnote o desde Camber, sin servidor de base de datos.

## 7. Cómo vas a ver los datos

| Qué | Herramienta | Para quién |
|---|---|---|
| **Tablero público** | Evidence (código abierto: páginas escritas con SQL y Markdown sobre DuckDB, que se compilan a un sitio estático) publicado en GitHub Pages y regenerado por Actions. Alternativa: Observable Framework | Cualquiera |
| **Cuadernos de análisis** | Deepnote, con DuckDB sobre el Parquet | Tú, y quien invites |
| **Salud del sistema** | Reporte semanal generado por Actions, más los monitores de Sentry | Tú |
| **Preguntar al conocimiento** | Servidor MCP desde Claude Code, y una búsqueda simple en el tablero | Tú y cualquier IA |

Páginas del tablero:
1. **"¿Mi computadora puede?"** Eliges tu CPU y tu GPU, y ves qué versión de Blender y qué perfil te tocan, con la evidencia medida.
2. **Rendimiento por nivel:** cuadros por segundo y tiempos por escena y perfil, de N1 a N4.
3. **Cobertura de equipos:** cuántos equipos hay por nivel y qué falta medir.
4. **Cobertura frente a Maya y 3ds Max:** porcentaje ponderado y lista de brechas ordenada.
5. **Técnicas:** el catálogo de fichas con su costo en hardware.
6. **Salud de los datos:** fuentes activas, última corrida, muestra humana y registros rechazados con su motivo.

## 8. Del dato al kernel: cómo se usa lo que juntamos

Los datos no se convierten solos en software. Cada tipo de dato tiene un camino concreto hacia el Corazón y hacia Blender Amatista:

| Dato de G7B | Se convierte en | Dónde vive | Qué cambia para la persona |
|---|---|---|---|
| `g7b.perfil/1` (P1, P2) | Perfil de hardware que el add-on aplica al arrancar: detecta el equipo y elige los ajustes | Extensión o rama del Corazón (`amatista.rama/1`) en el repo `amatista` | Blender abre fluido en su computadora, sin configurar nada |
| `g7b.equivalencia/1` (P4) | Lista de brechas: cada una se cubre con un add-on libre existente, un perfil, una plantilla o un nodo de Geometry Nodes | Add-on y plantilla Blender Amatista; perfiles de familiaridad para Maya y 3ds Max | Quien viene de Maya o 3ds Max encuentra cómo hacer su trabajo |
| `g7b.tecnica/1` (P5) | Ajustes, prácticas y recursos que aplican técnicas de la industria con herramientas libres | Prácticas de Amatista, presets del add-on | Resultados de nivel profesional con lo que ya tiene |
| `g7b.evento/1` (P7) | Prácticas y señales corregidas donde la gente se atora | Prácticas y Corazón | Menos frustración, medida y no supuesta |
| `g7b.documento/1` y fragmentos (P6) | Respuestas con fuente, a través del servidor MCP | API de G7B | Una IA (Claude incluido) ayuda a escribir add-ons y adaptadores con la API real de la versión correcta |

**El orden importa:** primero perfiles (dan resultados visibles con pocos datos), después equivalencias y técnicas, y la telemetría de prácticas cuando haya personas usando Amatista.

### Blender y los add-ons: la herramienta que construimos

- **Blender Amatista** ya es una plantilla de aplicación (`--app-template amatista`) más un add-on GPL-3.0. Se sigue así: sin recompilar Blender, se hereda cada mejora de la Blender Foundation.
- **Lo que se agrega** se hace con lo que Blender ya ofrece: la API de Python, recursos de Geometry Nodes, mapas de teclas, preferencias y la plataforma de extensiones. Antes de escribir un add-on se busca uno libre que ya lo haga, y se integra respetando su licencia.
- **Otros programas** entran como adaptadores del Corazón con su propio sistema de extensión: Godot (plugins), FreeCAD y Krita (Python). Uno a la vez, y solo cuando el anterior pase su prueba de conformidad.

## 9. Fases y calendario

Cada fase tiene criterio de salida (cuándo está lista) y criterio de abandono (cuándo se cambia de rumbo).

| Fase | Cuándo | Qué se hace | Lista cuando | Se replantea si |
|---|---|---|---|---|
| **F0 Base** | Fin de semana 1 | Limpiar el repo; contratos; Doppler; Azure con el contenedor `lago`; arañas del manual y de la API `bpy` de Blender 4.x LTS; copia de Zyte al lago; Blender Open Data en DuckDB; primera página del tablero | Hay un análisis real de Open Data publicado y el manual completo en bronce sin duplicados | — |
| **F1 Sonda** | Semanas 1 y 2 | `g7b-sonda` v0 (sin ventana y con ventana); medir tus PCs, ejecutores de Actions y 2 o 3 tamaños de máquina en Azure | 5 equipos medidos de al menos 3 niveles, y resultados repetibles: misma máquina, diferencia menor al 10 % | Las mediciones no se repiten: se arregla la sonda antes de seguir |
| **F2 Conocimiento** | Semanas 3 y 4 | Fragmentos y vectores en Camber; índice de búsqueda por vectores en Mongo; servidor MCP; prueba de 20 preguntas técnicas con y sin G7B | Con G7B mejoran las respuestas y citan la fuente en al menos 15 de 20 | Si no mejora, se dejan de extraer documentos y se revisa la fragmentación |
| **F3 Telemetría y catálogos** | Semanas 5 a 8 | Aviso de privacidad; botón "Medir mi equipo" y telemetría con consentimiento en el add-on (repo `amatista`); conseguir equipos; catálogo de equivalencias v0 (unas 100 tareas); 50 fichas de técnica | 20 equipos medidos; catálogo con estado y uso; primer porcentaje de cobertura | Menos de 10 equipos a la semana 8: se cambia la forma de conseguirlos (laboratorios) |
| **F4 Al kernel** | Semanas 9 a 12 | `g7b.perfil/1` v1 y su uso en el Corazón; API y MCP en Heroku; tablero completo; reporte trimestral | 30 equipos, 5 por nivel; el add-on aplica un perfil medido y mejora la fluidez en N1 o N2 | Si los perfiles no mejoran nada medible, se revisa la sonda y los niveles |

Lo que queda corriendo después de F0 no son máquinas encendidas, sino **trabajos programados**: revisión semanal de fuentes, descarga de Open Data, el reporte de calidad y los monitores.

## 10. Riesgos

| Riesgo | Respuesta |
|---|---|
| Juntar datos que nadie usa | Regla 1 de calidad: sin pregunta no se extrae |
| Problemas legales (licencias, marcas, patentes) | Licencia obligatoria por dato; lista de lo que nunca entra; revisar patentes antes de implementar una técnica |
| Privacidad | Consentimiento, identificador anónimo, publicación agregada y aviso de privacidad antes de activar |
| Datos falsos en mediciones o telemetría | Clave por instalación, límite de envíos y detección de valores imposibles |
| Las arañas se rompen en silencio | Monitores de Sentry, reporte semanal y muestra humana |
| Créditos que vencen sin usarse, o que se gastan sin control | Activar cada crédito solo cuando una fase lo necesita (sección 6.2) |
| Un solo desarrollador con muchos frentes | Una fase a la vez; máximo 3 tareas en progreso; G7B no detiene la prueba de Amatista con personas reales |
| Faltan computadoras viejas (N1) | Buscarlas a propósito: laboratorios, escuelas, donaciones. Sin datos de N1, no se afirman conclusiones sobre N1 |

## 11. Decisiones pendientes

1. **Licencias:** propuesta de código de G7B en AGPL-3.0 (cubre el uso como servicio en red), datos agregados publicados en CC BY 4.0 y registro de la marca. Por confirmar.
2. **Versiones de Blender de referencia:** propuesta: 4.2 LTS y 3.6 LTS, más 2.93 para N1.
3. **Dominio de G7B:** un `.dev` o `.software` de Name.com.
4. **Aviso de privacidad** para la sonda y la telemetría, antes de F3.
5. **Dónde corre el modelo de lenguaje**, si algún día se necesita uno propio. No hace falta hasta después de F2: el servidor MCP le sirve a la IA que ya usas.

## 12. Reglas de trabajo

1. Sin pregunta en la sección 3, no se extrae.
2. Ningún servicio ni crédito nuevo sin una fase que lo necesite.
3. Una fase a la vez; máximo 3 tareas en progreso.
4. Los secretos viven en Doppler; nunca en Git, en el código ni pegados en paneles.
5. Cada fase termina con algo visible en el tablero.
6. Lo que deja de regir se marca como historia, no se borra.
