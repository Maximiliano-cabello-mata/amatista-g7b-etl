# Revisión del repo y plan para usar todas las ofertas

Fecha: 2026-11-02. Revisión de todo lo que entró al repo desde el cierre del 1 de noviembre (PR #4 a PR #9), comparada con el plan ([PLAN.md](../PLAN.md), sección 0) y la [visión](../VISION.md). Incluye la decisión del día sobre las ofertas del GitHub Student Developer Pack.

## 0. La decisión que cambia la regla

> **Decisión de Maximiliano (2026-11-02):** las ofertas se usan **ya**, todas las que sirvan al fin final. Una oferta que se guarda "para cuando haga falta" termina sin usarse.

Esto **reemplaza** dos reglas anteriores:
- "Encender cada oferta solo cuando una fase la necesita", en `OFERTAS_Y_GITHUB.md` §4 (rama del PR #8);
- "No activar servicios de cuota temporal sin hipótesis...", en `infra/ofertas/catalogo.json` (PR #9).

La nueva regla tiene **una sola condición**: cada oferta activada recibe **un trabajo concreto** que alimenta el fin final (sección 3). Si no hay trabajo para ella, no se activa. El límite ya no es el dinero, sino el tiempo de Maximiliano.

## 1. El fin final (para no perderlo de vista)

**G7B no es el producto.** La ciencia de datos tampoco es el oficio de Maximiliano ni el objetivo: es la herramienta para tomar **una decisión** (qué perfil, qué versión y qué recurso le conviene a cada equipo).

```text
 FIN FINAL:  Amatista (enseña y recomienda)  +  Geoda (adapta las herramientas al equipo)
                    ▲                                   ▲
                    └──────── perfiles, recomendaciones ┘
                                    ▲
 MEDIO:      G7B: mide → cubo → compuertas → perfiles publicados (automático)
```

Por eso el warehouse tiene que ser **automático**: las compuertas de calidad y la publicación versionada deciden solas qué dato vale, y Maximiliano no tiene que analizar a mano. Su papel es de **ingeniero de producto y de sistemas**, no de analista.

## 2. Estado del repo y alineación con el plan

### 2.1 Lo que hay

| PR | Rama | Qué trae | Estado |
|---|---|---|---|
| #3 | `claude/peaceful-tesla-ctqaps` | Arañas, embudo, visión, estadía | **Fusionada** |
| #4 (borrador) | `claude/project-thread-pgechg` | `g7b_almacen`: Open Data, cubo DuckDB, `perfiles.json`, compuertas, latido cada hora | Abierta, base `main` |
| #5 | `chatgpt/g7b-publicacion-segura-colab-…` | Publicación versionada tras la compuerta; laboratorio Colab | Abierta, base #4 |
| #6 | `chatgpt/prueba-blender-azure-aislada-…` | Blender real en Actions → `tmp/` del lago, verificado con SHA-256 | Abierta, base #5 |
| #7 | `chatgpt/duckdb-azure-aislado-…` | Primer `cubo.duckdb` real en Azure (7 hechos, 1 corrida) | Abierta, base #6 |
| #8 | `chatgpt/tablero-g7b-html-…` | Tablero HTML sin conexión desde DuckDB | Abierta, base #7 |
| #9 | `chatgpt/g7b-arquitectura-privada-ofertas-…` | Azure privado: Container Apps Job, ACR, OIDC, Log Analytics, catálogo de 82 ofertas | Abierta, base `main` |

**Comprobado en esta revisión:** la cadena #4→#8 y la #9 se combinan sobre `main` **sin conflictos**. Juntas pasan **102 pruebas, con 8 omitidas** (las de Azurite) y 2 guiones de shell. El repo es **público**, así que GitHub Actions no tiene tope de minutos.

### 2.2 Qué está alineado

| Plan (sección 0) | Dónde quedó | Juicio |
|---|---|---|
| Telemetría antes que texto | `g7b_almacen`, sonda 0.2.0 con `--origen` | ✅ Alineado |
| Cubo con hechos y dimensiones | `cubo.py`: `hechos_render`, `hechos_medicion`, 6 dimensiones, vistas | ✅ Alineado |
| Blender Open Data como primera fuente | `opendata.py` (CC0, con licencia registrada) | ✅ Código listo; **aún no hay datos en el lago productivo** |
| `perfiles.json` para Amatista | `perfiles.py` + `publicacion.py` (`publicado/actual.json` con hashes) | ✅ Mejor que el plan: Amatista solo lee lo aprobado |
| Calidad antes que volumen | `calidad.py` (compuerta), lo sintético nunca entra al cubo | ✅ Alineado |
| Matriz de Actions (Linux, ARM, Windows, macOS) | `sonda_matriz.yml` | ✅ Lista, apagada por el interruptor |
| Sin datos personales | Contratos, `huella` como hash, tablero sin datos del equipo | ✅ Alineado |
| Interruptor `G7B_INGESTA_ACTIVA` | Todas las tareas programadas nuevas lo respetan | ✅ Nada corre solo |

### 2.3 Qué no está alineado o falta

1. **Azure trabaja, pero todavía no mide nada.** La PR #9 es técnicamente sólida: identidad administrada, OIDC sin llaves e imagen privada por digest. Pero son 29 commits y unas 3 000 líneas para un Job que **solo cuenta los archivos del lago**. Mientras tanto ACR y Log Analytics cobran aunque no corra nada.
   - **Arreglo:** que el mismo Job corra el trabajo útil: `python -m g7b_almacen latido` (cubo y compuerta) y, en otra variante, la sonda con Blender en CPU. La infraestructura ya está y solo cambia la imagen.
2. **El cubo tiene 7 filas.** Hay una sola corrida real de la sonda y nada de Open Data en el lago productivo, así que los perfiles salen como "provisional". Lo que falta es **una corrida de `almacen.yml`** (Open Data) y **una de `sonda_matriz.yml`**: dos clics en Actions.
3. **Cinco PRs en cadena y dos IAs escribiendo a la vez.** Cada PR de la cadena se apoya en la anterior, y mientras sigan abiertas las ramas se separan más. Conviene **fusionar ya, en orden**: #4, #5, #6, #7 y #8; luego #9.
4. **Dos listas de ofertas que se contradicen:** `docs/OFERTAS_Y_GITHUB.md` (22 ofertas, "cuándo activar") e `infra/ofertas/catalogo.json` (82 ofertas, 72 en "evaluar"). Este reporte (sección 3) las unifica bajo la decisión nueva. Al fusionar, el catálogo JSON queda como **fuente única** y se actualiza su campo `estado`.
5. **El incidente de la SAS no está cerrado.** La PR #9 registra una exposición histórica de la SAS en un log de Actions, con una rotación **no verificada**. Como el repo es público, la acción segura es **generar una SAS nueva hoy** y actualizar el secreto `AZURE_LAGO_URL` del environment `amatista1`. Son 5 minutos.
6. **Datos de Azure en un repo público.** `infra/azure/base_operativa.json` publica el id de la suscripción y el del workspace. No son secretos, pero tampoco aportan nada en público. Conviene moverlos a variables del environment.
7. **Del lado de Amatista no hay consumidor todavía.** Nada lee `publicado/actual.json`. La tarea de Amatista "detección del nivel en el add-on" (v3.5.0) es la que cierra el ciclo y debe ir antes que cualquier otra mejora del warehouse.

## 3. Todas las ofertas, cada una con su trabajo

Fuente: las 82 ofertas de `infra/ofertas/catalogo.json`. Están agrupadas por **para qué sirven al fin final**. "Quién" dice si se puede hacer desde el repo (código) o si requiere que Maximiliano reclame la oferta o configure una cuenta.

### 3.1 Medir (alimenta el modelo de costos de Geoda y los perfiles)

| Oferta | Trabajo concreto | Quién |
|---|---|---|
| **Microsoft Azure** ($100) | El Job de Container Apps corre la sonda en CPU y el latido del warehouse, no solo el auditor | Código + 1 despliegue en Cloud Shell |
| **VS Dev Essentials** ($200 de Azure) | Semana de mediciones en varios tamaños de máquina virtual: la sonda en 2, 4, 8 y 16 núcleos para la curva de escalado | Maximiliano reclama; código listo antes |
| **GitHub Actions** | `sonda_matriz.yml` cada semana: Linux x64 y ARM, Windows y macOS | Encender el interruptor |
| **GitHub Codespaces** | La sonda en máquinas de 2 a 16 núcleos: escalado por núcleos sin gastar Azure | Código (devcontainer) |
| **Google Colab** (~200 créditos) | Sonda con GPU (Cycles con CUDA/OptiX) y métrica LPIPS de calidad visual | Notebook ya documentado (`COLAB_LABORATORIO.md`) |
| **Camber** (CPU y GPU cada mes) | Lotes mensuales: la sonda de operaciones (subdividir, simplificar, booleanas, UV) en GPU | Maximiliano reclama |
| **BrowserStack** | Sonda web: fps de una escena A-Frame en celulares y navegadores reales → entornos A-Frame de Amatista | Código + cuenta |
| **LambdaTest** | Segunda fuente de dispositivos para los modelos que BrowserStack no tenga; sirve para validar una medición con otra | Cuenta |
| **Polypane** | Revisar que la PWA de Amatista y el tablero se vean bien en todos los tamaños de pantalla | Maximiliano |

> **Única advertencia:** VS Dev Essentials da **un solo mes**. Ese reloj arranca al reclamarlo, así que conviene reclamarlo el día en que el Job de la sonda en Azure ya corra (punto 1 de la sección 2.3), y no antes. Todo lo demás se puede reclamar hoy.

### 3.2 Guardar, procesar y consultar

| Oferta | Trabajo concreto | Quién |
|---|---|---|
| **MongoDB** ($50 de crédito + M0) | Usar el crédito: búsqueda vectorial de Atlas sobre los documentos del manual (para Goliat) y **Atlas Charts** del cubo | Maximiliano activa el crédito |
| **MongoDB University** | Certificación gratuita (vale en el CV) | Maximiliano |
| **Deepnote** | Un cuaderno público "G7B en vivo" que lee `oro/cubo.duckdb` | Código + cuenta |
| **Microsoft 365** | Excel con tablas dinámicas sobre los CSV del cubo; Word para la memoria de la estadía | Maximiliano |
| **PopSQL / SQLGate** | Consultas SQL guardadas sobre DuckDB, si el cliente lo admite; si no, no se activan (Deepnote ya cubre esto) | Probar 10 minutos |
| **JetBrains** (DataSpell y PyCharm) | Abrir el cubo y depurar `g7b_almacen` con un editor completo | Maximiliano |

### 3.3 Servir a Amatista (aquí se cierra el ciclo)

| Oferta | Trabajo concreto | Quién |
|---|---|---|
| **Heroku** ($13 al mes) | **API de G7B y servidor MCP desde ya:** `GET /perfiles`, `GET /recomendacion?equipo=…`; Goliat consulta el cubo por MCP | Código + cuenta |
| **Name.com / .TECH** | `g7b.dev` (o `.tech`): `api.` para Heroku, `datos.` para el tablero en Pages | Maximiliano reclama |
| **GitHub Pages** | Tablero público "¿Mi computadora puede?" con el HTML de la PR #8 | Código |
| **ConfigCat / DevCycle** | Encender los perfiles en el add-on poco a poco (10 %, 50 %, 100 %), con botón para apagarlos | Código en Amatista |
| **Stripe** | Modo de prueba ya configurado para la futura tienda de modelos de Amatista | Maximiliano |
| **SimpleAnalytics** | Estadísticas de la PWA de Amatista que respetan la privacidad | Maximiliano + 1 línea en la PWA |
| **Pageclip** | Formulario "inscribe tu laboratorio o tu equipo" sin servidor | Código |
| **Testmail** | Probar los correos de Amatista (registro, avisos) sin cuentas reales | Código en Amatista |
| **POEditor** | Traducir Amatista y el add-on (español → inglés); abre el centro 3D a más gente | Maximiliano |
| **Icons8 / IconScout / Octicons** | Íconos del centro 3D y del tablero | Maximiliano |
| **Bootstrap Studio / Themeisle** | Página de aterrizaje del centro 3D | Maximiliano |
| **Requestly** | Simular la API de G7B mientras el add-on se programa | Maximiliano |
| **Appwrite / Clerk** | **No:** Amatista ya tiene cuentas; duplicarían | — |

### 3.4 Operar seguro

| Oferta | Trabajo concreto | Quién |
|---|---|---|
| **Doppler** | Todas las llaves en un solo lugar, sincronizadas con el environment `amatista1` y con Heroku | Maximiliano |
| **1Password** | Credenciales humanas: Azure, Zyte, Atlas, Oracle y recuperación | Maximiliano |
| **Sentry** | Monitores de las tareas programadas (`SENTRY_DSN` ya está en los workflows) | Maximiliano crea el DSN |
| **Codecov** | Cobertura de `pruebas.yml` visible en cada PR | Código |
| **DeepScan / CodeScene** | Calidad del JavaScript de la PWA de Amatista | Maximiliano |
| **AstraSecurity** | Escaneo de seguridad del sitio de Amatista en Oracle | Maximiliano |
| **Blackfire** | Perfilar la API de G7B en Heroku cuando exista | Después de la API |
| **Imgbot** | Comprimir solo las imágenes del repo de Amatista | 1 clic |
| **Termius** | SSH a la máquina de Oracle de Amatista desde el celular | Maximiliano |
| **Datadog / New Relic / Honeybadger** | **No:** Sentry ya cubre esto, y tener tres alarmas confunde | — |
| **Travis CI / LocalStack** | **No:** Actions ya cubre la CI y no se usa AWS | — |

### 3.5 Presentar y aprender (alimenta la estadía y la carrera)

| Oferta | Trabajo concreto |
|---|---|
| **Visme** | Presentaciones para la universidad y para la defensa de la estadía |
| **ToDiagram** | Diagramas de la arquitectura para la memoria |
| **Notion** (+ plantillas) | Cuaderno de la estadía: protocolo, consentimientos, avance semanal |
| **CARTO** | Mapa de la brecha de equipo (con datos de laboratorios y permiso) |
| **GitHub Campus Experts** | Postularse: respaldo para hablar en la universidad |
| **GitHub Copilot, GitHub Desktop, GitKraken, GitLens, Tower, WorkingCopy, VS Code** | Herramientas diarias; con una o dos basta |
| **FrontendMasters** | Cursos de WebGL y Three.js: la base del editor web y de A-Frame |
| **DataCamp, Educative, Scrimba, Boot.dev, Codedex** | Lo justo de SQL y de ingeniería de datos para mantener G7B, sin volverse analista |
| **AlgoExpert, InterviewCake** | Preparación para entrevistas de trabajo |
| **HazeOver, PomoDone** | Productividad personal |

### 3.6 Las que no encajan (no se activan)

Adafruit, Arduino, Blockchair, Appfigures, Vaadin, Xojo, SymfonyCasts, GoRails, Dashlane (1Password ya cubre esto) y Microsoft Azure for ages 13–17 (no aplica). Nada en el fin final las necesita. Activarlas solo consumiría tiempo.

> Idea aparte, para más adelante: con un medidor de consumo eléctrico (Arduino o Adafruit), la sonda podría medir **watts** además de tiempo. Sería un dato que casi nadie publica, pero no es prioridad.

## 4. Orden de la semana

| Día | Qué | Quién |
|---|---|---|
| 1 | Generar una SAS nueva y actualizar `AZURE_LAGO_URL` (incidente) | Maximiliano |
| 1 | Fusionar en orden: #4, #5, #6, #7, #8 y luego #9 | Maximiliano (o Claude, si lo pide) |
| 1 | Correr a mano `almacen.yml` (Open Data) y `sonda_matriz.yml` | Actions |
| 1 | Reclamar: Heroku, Name.com, BrowserStack, Doppler, 1Password, Sentry, Deepnote, Codecov, el crédito de Atlas, Campus Experts | Maximiliano |
| 2–3 | Cambiar la imagen del Job de Azure para que corra el latido y la sonda | Código |
| 2–3 | API mínima de G7B en Heroku: `/perfiles` lee `publicado/actual.json` | Código |
| 3–4 | Tablero en Pages y el dominio apuntando a la API y al tablero | Código + DNS |
| 4–5 | Sonda web con BrowserStack (escena A-Frame) | Código |
| 5 | Reclamar VS Dev Essentials y lanzar la semana de mediciones en Azure | Maximiliano + código |
| 5+ | En Amatista: detección del nivel en el add-on, leyendo la API (cierra el ciclo) | Código en Amatista |

**Criterio de éxito de la semana:** el add-on de Amatista pide un perfil a `api.<dominio>`, lo recibe con su evidencia y lo aplica con opción de deshacer. Ese día G7B deja de ser infraestructura y pasa a ser **producto**.
