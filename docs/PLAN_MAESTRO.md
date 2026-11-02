# Plan maestro: el camino a seguir

Fecha: 2026-11-02. Un solo camino, de principio a fin, para que G7B quede **funcional y automático** con las ofertas del GitHub Student Developer Pack, y para que **Amatista, Geoda y G7B se alimenten entre sí**.

- **Reúne** lo que se construyó con los dos agentes (PR #1 a #10): ingesta de texto, lago, warehouse, publicación segura, Azure privado y catálogo de ofertas.
- **Manda sobre lo anterior:** donde otro documento diga algo distinto ([PLAN.md](PLAN.md), [OFERTAS_Y_GITHUB.md](OFERTAS_Y_GITHUB.md), `CIERRE_AZURE.md`, `infra/ofertas/catalogo.json`), vale este plan. Esos documentos quedan como detalle o como historia.
- **Del lado de Amatista,** la misma conexión está en su repo: `docs/arquitectura/2026-11-02_conexion_g7b_y_geoda.md`.

**Cómo leerlo:** cada paso dice quién lo hace y cómo saber que quedó.
- **[Tú]**: algo que solo tú puedes hacer, como reclamar una oferta, entrar a un portal o pegar un secreto.
- **[Código]**: lo programa un agente (Claude u otro) en una rama con su PR.
- **Hecho cuando**: la comprobación. Si no se cumple, **no se pasa al siguiente paso.**

---

## 1. El sistema en una página

### 1.1 Tres piezas, un ciclo

| Pieza | Qué es | Dónde vive |
|---|---|---|
| **Amatista** | La plataforma: enseña, recomienda y es el centro de conocimiento 3D. **La única que guarda datos de personas.** | Oracle (API y base) + Cloudflare (PWA) + add-on de Blender |
| **Geoda** | El kernel. Su mitad **cliente** vive en el add-on de Amatista (el Corazón) y en cada equipo: detecta el equipo, decide, aplica y vuelve a medir. Su mitad **cerebro**, el modelo de costos y el planificador, se entrena en G7B. | Add-on de Amatista + G7B |
| **G7B** | El motor de datos: captura, guarda, limpia, calcula y **publica** perfiles, recomendaciones, catálogos y el modelo de costos. | Azure, MongoDB, GitHub, Heroku y las demás ofertas |

```text
        ┌──────────────────────────── G7B (medir y decidir) ─────────────────────────────┐
        │ captura ─► entrada/lago (Azure) ─► cubo + compuerta ─► publicado ─► API (Heroku) │
        │     ▲                                                     │            │          │
        │     │                                              panel (Atlas Charts)│          │
        └─────┼─────────────────────────────────────────────────────────────────┼──────────┘
              │ agregados (≥5 equipos, sin personas)                              │ perfiles, recomendaciones,
              │                                                                   │ texturas, herramientas,
        ┌─────┴──────────────── AMATISTA (enseñar y recomendar) ─────────────────▼──────────┐
        │ API en Oracle: guarda en caché lo de G7B y junta los eventos de las prácticas     │
        │      ▲                                    │                                        │
        │      │ eventos de práctica                ▼ recomendación para ESTE equipo         │
        │  ┌───┴────────────────── GEODA (en el add-on, en el equipo del alumno) ─────────┐ │
        │  │ detecta el equipo → pide recomendación → decide con el modelo de costos       │ │
        │  │ → aplica el perfil (se puede deshacer) → vuelve a medir → reporta el evento   │ │
        │  └───────────────────────────────────────────────────────────────────────────────┘ │
        └────────────────────────────────────────────────────────────────────────────────────┘
```

**El ciclo:**
1. G7B mide el mundo: equipos, versiones, texturas, herramientas y técnicas.
2. Amatista toma esas decisiones y Geoda las aplica en cada equipo.
3. Geoda vuelve a medir, y Amatista agrega esos resultados sin datos personales.
4. G7B los recibe y mejora sus decisiones.

### 1.2 Dónde corre cada cosa

```text
 RELOJ ÚNICO: GitHub Actions (repo público: minutos ilimitados)
 │
 ├─ CAPTURA en Actions ─ Open Data · sonda en matriz · texturas · herramientas · texto (Zyte)
 │                       · sonda web (BrowserStack) · agregados de Amatista ─► lago/bronce
 ├─ CAPTURA externa ──── Colab y Camber (GPU) · Codespaces (núcleos) · tus PCs · laboratorios
 │                       · semana VS Dev Essentials ─► contenedor «entrada» (solo escritura)
 │
 AZURE (solo dos servicios: Blob Storage + Container Apps Jobs)
 ├─ Blob «lago»: bronce → plata → oro (+ control, sintetico, tmp)
 ├─ Blob «entrada»: buzón; un Job valida y pasa a bronce lo que cumple el contrato
 ├─ Blob «publicado»: solo lo aprobado por la compuerta (lo que lee el mundo)
 ├─ Job g7b-latido (cada 6 h): entrada→bronce, cubo, compuerta, publicar, panel
 └─ Job g7b-sonda (semanal): Blender en CPU, 2 vCPU y 4 GiB
 │
 SALIDAS
 ├─ MongoDB Atlas: conocimiento (Goliat) + catálogos + panel ─► Atlas Charts (TU PANEL)
 ├─ Heroku: API pública de G7B + servidor MCP (lee «publicado» y Mongo)
 ├─ GitHub Pages: copia estática de «publicado» + CSV para Excel
 ├─ GitHub Releases + Zenodo: dataset mensual con DOI
 └─ Deepnote y Excel: análisis profundo cuando quieras
 │
 ALREDEDOR: Doppler (secretos) · 1Password (tus contraseñas) · Sentry (alarmas)
            · Codecov, CodeQL, Dependabot y reglas de main (errores de programación)
```

---

## 2. Qué se recopila: siete familias de datos

| # | Familia | Fuentes (todas abiertas y con licencia revisada) | Cómo se captura | Qué recibe Amatista |
|---|---|---|---|---|
| F1 | **Telemetría de equipos** | Sonda de Blender (CPU y GPU); Blender Open Data (CC0); sonda web en celulares | Actions, Azure, Colab, Camber, Codespaces, BrowserStack, PCs y laboratorios | Nivel del equipo (N0–N4), perfil de ajustes y versión de Blender recomendada |
| F2 | **Formas optimizadas** (costo por operación) | Sonda de operaciones: subdividir, simplificar, booleanas, remallar, desplegar UV, hornear, geometry nodes. Compara técnicas que logran el mismo resultado (mapa normal o subdivisión, simplificar o remallar) | Las mismas máquinas que F1 | "En tu equipo, haz X de esta forma"; el modelo de costos de Geoda |
| F3 | **Texturas y materiales** | Poly Haven y ambientCG (CC0; respetar los términos de su API) | Metadatos en Actions; costo por resolución con la sonda; etiquetas por IA en Colab | Biblioteca de texturas por nivel ("en N1 usa 1K") |
| F4 | **Herramientas** | Catálogo de extensiones de Blender, repos de software libre (API de GitHub), equivalencias con Maya y 3ds Max (lista curada) | Actions | Herramientas recomendadas por tema, versión y equipo |
| F5 | **Técnicas y conocimiento** | Manual de Blender, Blender Stack Exchange, arXiv (lo que ya funciona) | Zyte + embudo + Actions | Goliat responde con fuentes; fichas de técnica |
| F6 | **Aprendizaje** | Eventos de las prácticas de Amatista, **agregados** (≥5 equipos) y con consentimiento | Amatista los expone; Actions los trae | Prácticas que se adaptan; los datos de la estadía |
| F7 | **Modelos 3D** (para la tienda, después) | Poly Haven (modelos CC0): polígonos y costo de carga | Actions + sonda | Modelos por nivel de equipo |

**La herramienta que captura todo esto es [Geodar Radar](GEODAR_RADAR.md)** (`python -m geodar`); su [mapa de sensores](GEODAR_RADAR_MAPA.md) dice dónde vigila cada fuente.

**Lo que nunca entra:** datos personales; código o herramientas filtradas o propietarias; sitios que lo prohíben en su `robots.txt`; datos sintéticos mezclados con los reales.

---

## 3. Reglas para no volver a sufrir

En Azure se sufrió por dos causas: servicios que la suscripción de estudiante no admite (Express, ACR Tasks), y cambios hechos a mano sin comprobación. Estas reglas cierran las dos puertas.

1. **Azure solo hace dos cosas:** guardar (Blob) y correr trabajos (Container Apps Jobs, en el entorno v3 que ya funciona). Nada de servicios nuevos: sin ACR, Functions, Data Factory, Synapse, Key Vault, redes virtuales ni máquinas encendidas. Lo demás vive en GitHub y en las otras ofertas.
2. **Cada cambio en Azure es un bloque de este plan:** se copia tal cual en Cloud Shell y se comprueba con su "Hecho cuando". Si falla, se pega la salida en la conversación y no se improvisa.
3. **Primero en GitHub, después en Azure:** la misma imagen de contenedor se prueba antes en Actions. A Azure solo llega lo que ya funcionó.
4. **Nada llega a `main` sin pruebas en verde:** reglas de la rama, Codecov y revisión de Copilot en cada PR.
5. **Una IA por rama y nada de cadenas:** las PR encadenadas (#4 a #8) se juntaron. A partir de hoy, cada trabajo sale de `main` en su propia rama.
6. **Un solo interruptor:** la variable `G7B_INGESTA_ACTIVA=true` enciende todas las tareas programadas de GitHub, y en `false` todo se detiene. Los Jobs de Azure se pausan con un comando (sección 12).
7. **Secretos en un solo lugar:** Doppler. Nunca en el código, en un log ni en el chat.

---

## 4. Estado de hoy (2 de noviembre)

| Pieza | Estado |
|---|---|
| Arañas de Zyte → lago → embudo → MongoDB | **Funciona** (primera corrida real: 5 documentos publicados) |
| Lago en Azure (`g7blago09b52a0e`, contenedor `lago`) | **Funciona** |
| Warehouse: cubo DuckDB, compuerta, publicación, tablero HTML | **Código listo** en las PR #4 a #8; 7 filas reales |
| Azure: entorno v3, Job auditor, ACR, OIDC, Log Analytics | **Funciona,** pero solo cuenta archivos |
| Catálogo de 82 ofertas | En la PR #9 |
| Conexión con Amatista | **No existe todavía** |

**Los ~$6 al mes que ves en Azure:** casi todo es el registro de imágenes **ACR Basic (≈$5 al mes)**; el resto son logs y almacenamiento. Con Azure for Students no te cobran a la tarjeta, pero se descuenta de los $100 del año. Al pasar la imagen a `ghcr.io` (gratis) y borrar el ACR (Fase 3), el gasto baja a **≈$1 al mes o menos**. Puedes confirmarlo en Portal › Cost Management › Cost analysis, agrupado por recurso.

---

## 5. Fase 0: seguridad y orden (día 1, unas 2 horas)

### 0.1 Cerrar el incidente de la SAS [Tú, Cloud Shell, Bash]

La SAS vieja se firmó con una llave de la cuenta. Renovar las dos llaves la invalida para siempre. Las SAS nuevas se firman con una **política guardada**: si alguna vez se filtra, se revoca borrando la política, sin tocar las llaves.

```bash
G=g7b; C=g7blago09b52a0e; VENCE=2027-11-01T00:00Z
az storage account keys renew -g $G -n $C --key primary -o none
az storage account keys renew -g $G -n $C --key secondary -o none
for N in entrada publicado; do az storage container create --account-name $C -n $N -o none; done
az storage container policy create --account-name $C -c lago      -n actions-2027 --permissions racwl --expiry $VENCE
az storage container policy create --account-name $C -c entrada   -n buzon-2027   --permissions cw    --expiry $VENCE
az storage container policy create --account-name $C -c publicado -n lectura-2027 --permissions rl    --expiry $VENCE
for P in "lago actions-2027" "entrada buzon-2027" "publicado lectura-2027"; do set -- $P
  echo "$1: https://$C.blob.core.windows.net/$1?$(az storage container generate-sas --account-name $C -n $1 --policy-name $2 --https-only -o tsv)"
done
```

- **Desde que renuevas las llaves hasta que actualizas Doppler (paso 1.2), las tareas de GitHub que escriben al lago fallan.** Es normal: deja el interruptor apagado mientras tanto.
- Las tres líneas que imprime son: `AZURE_LAGO_URL` (lago), `AZURE_ENTRADA_URL` (entrada, **solo escritura**) y `AZURE_PUBLICADO_URL` (publicado, **solo lectura**). **No las pegues en el chat:** van directo a Doppler (paso 1.2).
- **Hecho cuando:** después del paso 1.2, la tarea `pruebas.yml` y una corrida manual de `vigilar.yml` terminan en verde con la SAS nueva.

### 0.2 Bajar el gasto de logs [Tú, Cloud Shell]

```bash
az monitor log-analytics workspace update -g g7b -n g7b-logs-laboratorio --quota 0.1
```

Esto pone un tope diario de 0.1 GB (el plan gratuito incluye 5 GB al mes). **Hecho cuando:** el portal muestra *Daily cap: 0.1 GB* en el workspace.

### 0.3 Juntar las PR [Código, con tu sí]

1. Una sola PR de integración de `chatgpt/tablero-g7b-html-20261101` (que ya contiene #4 a #8) hacia `main`. Las #4 a #8 se cierran como "incluidas".
2. Fusionar la #9 (Azure privado) y después la #10 (revisión) y este plan.

Combinadas pasan 102 pruebas. **Hecho cuando:** `main` contiene `g7b_almacen/`, `infra/azure/g7b-operacion.bicep` y este plan, y `pruebas.yml` está en verde.

### 0.4 Proteger el repo [Tú, GitHub › Settings]

| Dónde | Qué activar |
|---|---|
| Code security | Secret scanning + **Push protection**, Dependabot alerts, CodeQL (*Default setup*) |
| Rules › Rulesets › New branch ruleset (`main`) | *Require a pull request* + *Require status checks to pass* (elegir `pruebas`) + *Block force pushes* |
| Actions › General | *Workflow permissions: Read repository contents* (cada workflow pide lo que necesita) |

**Hecho cuando:** un push directo a `main` es rechazado.

---

## 6. Fase 1: reclamar las ofertas y conectarlas (días 1 y 2)

**Cómo se reclama:** entras a <https://education.github.com/pack> con tu cuenta de GitHub (tu estatus de estudiante ya está verificado, por eso tienes GitHub Pro). En cada oferta pulsas el botón del socio, inicias sesión con GitHub y aceptas. Algunas dan un código que se pega en el portal del socio. **Antes de reclamar una oferta con reloj, revisa su fecha de inicio en la tabla 1.3.**

### 1.1 Primero, la caja fuerte

| Oferta | Reclamar | Conectar | Hecho cuando |
|---|---|---|---|
| **1Password** | Desde el pack | Guarda ahí las contraseñas y códigos de recuperación de: GitHub, Azure, Atlas, Zyte, Heroku, Name.com, Doppler, Sentry, BrowserStack, Oracle y Cloudflare | Las 11 cuentas están guardadas |
| **Doppler** | Desde el pack (plan para estudiantes) | Proyecto `g7b`, config `prd`. Integraciones: **GitHub Actions** → repo `amatista-g7b-etl`, environment `amatista1`; **GitHub Codespaces** → mismo repo; **Heroku** → app `g7b-api` (cuando exista). Los cambios se hacen solo en Doppler: GitHub no deja leer los secretos de vuelta | Los secretos de `amatista1` dicen *"managed by Doppler"* |

### 1.2 Inventario único de secretos (todos en Doppler `g7b/prd`)

| Secreto | De dónde sale | Lo usa |
|---|---|---|
| `AZURE_LAGO_URL` | Paso 0.1 (lago, `racwl`) | Actions: captura y ingesta de texto |
| `AZURE_ENTRADA_URL` | Paso 0.1 (entrada, solo escritura) | Colab, Camber, Codespaces, PCs, laboratorios, VS Dev Essentials |
| `AZURE_PUBLICADO_URL` | Paso 0.1 (publicado, solo lectura) | Heroku, Pages, Deepnote |
| `ZYTE_API_KEY` | Ya existe | Actions |
| `MONGO_URI` | Atlas, usuario `g7b_escritor` (paso 1.3) | Actions y Job `g7b-latido` |
| `MONGO_URI_LECTURA` | Atlas, usuario `g7b_lector` | Heroku |
| `SENTRY_DSN` | Sentry (paso 1.3) | Actions, Jobs y Heroku |
| `BROWSERSTACK_USERNAME`, `BROWSERSTACK_ACCESS_KEY` | BrowserStack | Actions (`sonda_web.yml`) |
| `HEROKU_API_KEY` | `heroku authorizations:create` | Actions (`desplegar_api.yml`) |
| `AMATISTA_G7B_TOKEN` | Lo generas tú (40 caracteres al azar) y se guarda **igual** en el Doppler de Amatista | Actions (`traer_amatista.yml`) ↔ API de Amatista |
| `CODECOV_TOKEN` | Codecov | Actions (`pruebas.yml`) |

Las **variables**, que no son secretas, siguen en GitHub › environment `amatista1`: `ZYTE_PROJECT_ID=883618`, `G7B_INGESTA_ACTIVA`, `G7B_AZURE_CLIENT_ID`, `G7B_AZURE_TENANT_ID` y `G7B_AZURE_SUBSCRIPTION_ID`.

### 1.3 Todas las ofertas: reclamar, conectar, comprobar

**Ya activas (solo conectar):**

| Oferta | Conectar | Hecho cuando |
|---|---|---|
| **Azure for Students** ($100 al año, se renueva mientras seas estudiante) | Ya conectado (grupo `g7b`, West US 2). Saldo en <https://www.microsoftazuresponsorships.com/> | Ves el saldo y la fecha de renovación |
| **MongoDB Atlas** (M0 gratis + **$50** de crédito) | Canjear el código del pack en Atlas › Organization › Billing › *Apply credit*. En Database Access crear `g7b_escritor` (lectura y escritura en `conocimiento_3d`, `g7b_panel`, `g7b_catalogo`) y `g7b_lector` (solo lectura). Network Access: `0.0.0.0/0`, porque Actions, Azure y Heroku no tienen IP fija; la protección es la contraseña. El crédito queda **de reserva** para cuando se pasen los 512 MB | Los dos usuarios conectan con `mongosh` |
| **Zyte** | Ya conectado (proyecto 883618) | `desplegar_zyte.yml` en verde |
| **GitHub Pro** (Actions, Codespaces 180 h-núcleo y 20 GB al mes, Pages, Packages) | Pasos 0.4 y 2.x | — |
| **GitHub Copilot** | <https://github.com/settings/copilot>: activar, incluida la **revisión de código** en las PR | Copilot comenta en una PR |
| **.TECH** | Ya usado: `amatista-3d.tech` es de Amatista | — |

**Reclamar hoy (sin reloj, o con reloj de un año o más):**

| Oferta | Reclamar y conectar | Hecho cuando |
|---|---|---|
| **Sentry** | Reclamar; crear el proyecto `g7b` (Python); `SENTRY_DSN` a Doppler. Crear **Cron Monitors** para `g7b-latido`, `g7b-sonda`, `almacen`, `sonda_matriz` y `vigilar` | El primer *check-in* aparece en Sentry |
| **Codecov** | Instalar la app de Codecov en el repo; `CODECOV_TOKEN` a Doppler | La PR muestra el % de cobertura |
| **Deepnote** | Reclamar el plan educativo; proyecto "G7B análisis"; variable `AZURE_PUBLICADO_URL` | El cuaderno abre `cubo.duckdb` |
| **Microsoft 365** (Excel) | Activar con tu correo escolar si tu universidad lo da, o desde el pack | Excel › Datos › *Desde la web* carga un CSV de Pages (paso 2.4) |
| **JetBrains** | Reclamar la licencia educativa (DataSpell y PyCharm) | DataSpell abre el repo |
| **Notion** | Plan educativo; espacio "Estadía G7B + Amatista" | Existe la página del protocolo |
| **Visme, ToDiagram** | Reclamar; se usan en la estadía | — |
| **MongoDB University** | Ruta y certificación gratuita de MongoDB | — |
| **GitHub Campus Experts** | Postular | Solicitud enviada |

**Reclamar el día que se usan (el reloj corre desde que reclamas):**

| Oferta | Cuándo reclamarla | Reloj | Conectar |
|---|---|---|---|
| **Heroku** ($13 al mes) | Inicio de la **Fase 4** | **24 meses** desde que reclamas; mayor de 18 años; **pide tarjeta** para verificar | Paso 4.1 |
| **Name.com** (dominio gratis) | Inicio de la **Fase 4** | 1 año | Paso 4.3 |
| **BrowserStack** | Inicio de la **Fase 5** | ≈1 año | Paso 5.3 |
| **Camber** | Inicio de la **Fase 5** | Cuota mensual | Paso 5.2 |
| **VS Dev Essentials** ($200 de Azure) | **Fase 6**, el día de la semana de mediciones | **30 días.** Suele crear otra suscripción y pedir tarjeta: revisarlo en <https://my.visualstudio.com> | Paso 6.2 |
| **DataCamp, FrontendMasters, Educative** | Cuando tengas tiempo de estudiar | 3 a 6 meses | — |

**Van a Amatista, no a G7B** (están en su documento de conexión): ConfigCat, SimpleAnalytics, Stripe (modo de prueba), POEditor, Testmail, Pageclip, Icons8, IconScout, Bootstrap Studio y AstraSecurity.

**No se activan,** porque duplican algo o no encajan: Datadog, New Relic, Honeybadger, LambdaTest (solo si BrowserStack no tiene un modelo), Travis CI, LocalStack, Appwrite, Clerk, Dashlane, PopSQL, SQLGate, Adafruit, Arduino, Blockchair, Appfigures, Vaadin, Xojo, SymfonyCasts, GoRails y Azure for ages 13–17.

---

## 7. Fase 2: núcleo automático y tu panel (semana 1)

### 2.1 Encender lo que ya existe [Tú]

1. GitHub › Actions › **Warehouse (Open Data y cubo)** › *Run workflow* (`todo`).
2. Actions › **Sonda en matriz (nube)** › *Run workflow* (`5.2`, `media`).
3. Si ambas terminan en verde: Settings › Environments › `amatista1` › variable `G7B_INGESTA_ACTIVA=true`.

**Hecho cuando:** `oro/calidad.json` del lago dice `"aprobada": true` y `hechos_render` tiene miles de filas.

### 2.2 El buzón de entrada [Código]

- Nuevo `g7b_almacen/entrada.py`: lee el contenedor `entrada` y valida cada archivo contra su contrato (`g7b.medicion/1`, `g7b.textura/1`...). Lo que cumple pasa a `lago/bronce/<familia>/`; lo que no, a `lago/control/rechazados/` con su motivo.
- Se ejecuta como la primera fase del latido.
- **Hecho cuando:** un JSON subido desde Colab aparece en bronce, y uno roto aparece en rechazados.

### 2.3 El panel: MongoDB Atlas Charts [Código + Tú]

**Tu panel no es un HTML:** es **Atlas Charts**, que viene con tu Atlas. Se abre desde el celular, se comparte con un enlace y en el plan gratuito **se actualiza solo cada 4 horas**.

- **[Código]** Nueva fase `panel` en el latido. Escribe en la base `g7b_panel` **solo agregados**, unos pocos MB, para no acercarse a los 512 MB:

| Colección | Qué muestra |
|---|---|
| `salud` | Cada corrida: fase, duración, resultado de la compuerta, filas por calidad |
| `equipos_por_nivel` | Cuántos equipos hay de cada nivel, clase y origen |
| `rendimiento` | Mediana por nivel, versión, perfil y prueba |
| `perfiles` | El perfil publicado por nivel, con su estado (confiable o provisional) |
| `texturas`, `herramientas`, `conocimiento` | Conteos y lo más nuevo de F3, F4 y F5 |
| `aprendizaje` | Agregados de Amatista (F6) |

- **[Tú]** Atlas › pestaña **Charts** › activar › *Add data source* (tu clúster) › nuevo dashboard **"G7B"**. Seis tableros: **Salud**, **Equipos**, **Rendimiento**, **Perfiles**, **Catálogos** y **Aprendizaje**. El agente te da las consultas de cada gráfica.
- **Análisis profundo**, cuando lo quieras: Deepnote (SQL sobre el cubo) o Excel (paso 2.4).
- **Hecho cuando:** abres el dashboard en el celular y ves la última corrida.

### 2.4 Copia pública en Pages [Código + Tú]

- **[Código]** `publicar_pages.yml` (cada día): copia `publicado/actual.json`, los JSON aprobados y los CSV de `oro/csv/` a GitHub Pages. Es el respaldo estático: si la API cae, Amatista lee de aquí.
- **[Tú]** Settings › Pages › *Source: GitHub Actions*.
- **Hecho cuando:** `https://maximiliano-cabello-mata.github.io/amatista-g7b-etl/publicado/actual.json` responde.

### 2.5 Codespaces listo [Código]

- `.devcontainer/devcontainer.json` con Python, DuckDB, Azure CLI, Doppler CLI y las dependencias. Así nadie instala nada en su PC y el entorno es idéntico siempre, lo que evita errores de "en mi máquina sí funciona".
- **Hecho cuando:** *Code › Codespaces › Create* abre y `pytest` pasa adentro.

---

## 8. Fase 3: Azure hace trabajo de verdad (semana 2)

### 3.1 La imagen, en GitHub y gratis [Código]

- `infra/azure/trabajador/Dockerfile` con `g7b_lago` y `g7b_almacen`, más una variante con Blender en Linux (CPU) para la sonda.
- `publicar_trabajador.yml` la construye y la sube a `ghcr.io/maximiliano-cabello-mata/g7b-trabajador` con las etiquetas `:estable` (Blender incluido) y `:latido` (sin Blender).
- `g7b_lago` acepta **identidad administrada**: si existen `AZURE_STORAGE_ACCOUNT_URL` y no hay SAS, usa `DefaultAzureCredential`. Dentro de Azure no hay ninguna llave.
- **Primero en GitHub (regla 3):** una corrida de prueba en Actions con la misma imagen.
- `latido.yml` (Actions) pierde su cron y queda solo manual, como **respaldo** por si Azure falla. Así no hay dos latidos escribiendo a la vez.
- **[Tú]** GitHub › tu perfil › Packages › `g7b-trabajador` › *Change visibility: Public*. La imagen no lleva secretos, y así Azure la descarga sin credenciales.

### 3.2 Los dos Jobs [Tú, Cloud Shell; copiar tal cual]

```bash
G=g7b; E=g7b-env-laboratorio-jobs-v3; C=g7blago09b52a0e; IMG=ghcr.io/maximiliano-cabello-mata/g7b-trabajador
CUENTA=https://$C.blob.core.windows.net
read -rsp "MONGO_URI (g7b_escritor): " MONGO; echo
read -rsp "SENTRY_DSN: " DSN; echo

az containerapp job create -g $G -n g7b-latido --environment $E --workload-profile-name Consumption \
  --trigger-type Schedule --cron-expression "17 */6 * * *" \
  --replica-timeout 1800 --replica-retry-limit 1 --parallelism 1 --replica-completion-count 1 \
  --image $IMG:latido --cpu 1 --memory 2Gi --mi-system-assigned \
  --secrets mongo-uri="$MONGO" sentry-dsn="$DSN" \
  --env-vars AZURE_STORAGE_ACCOUNT_URL=$CUENTA MONGO_URI=secretref:mongo-uri SENTRY_DSN=secretref:sentry-dsn

az containerapp job create -g $G -n g7b-sonda --environment $E --workload-profile-name Consumption \
  --trigger-type Schedule --cron-expression "41 9 * * 4" \
  --replica-timeout 3600 --replica-retry-limit 0 --parallelism 1 --replica-completion-count 1 \
  --image $IMG:estable --cpu 2 --memory 4Gi --mi-system-assigned \
  --secrets sentry-dsn="$DSN" \
  --env-vars AZURE_STORAGE_ACCOUNT_URL=$CUENTA G7B_ORIGEN=azure SENTRY_DSN=secretref:sentry-dsn

ST=$(az storage account show -g $G -n $C --query id -o tsv)
for J in g7b-latido g7b-sonda; do
  P=$(az containerapp job show -g $G -n $J --query identity.principalId -o tsv)
  for K in lago entrada publicado; do
    az role assignment create --assignee-object-id $P --assignee-principal-type ServicePrincipal \
      --role "Storage Blob Data Contributor" --scope "$ST/blobServices/default/containers/$K" -o none
  done
done
az containerapp job start -g $G -n g7b-latido
```

- **No se pasan `--command` ni `--args`.** Cada imagen trae su propio arranque: `:latido` corre `python -m g7b_almacen latido` y `:estable` corre la sonda y sube el JSON. Así se evita el error de las cadenas vacías del 2 de noviembre (`d0a2881`), y los argumentos que empiezan con guion no se confunden con opciones de `az`. El agente deja las dos imágenes probadas en Actions antes de este paso.
- **Cuánto cuesta:** latido cada 6 h (1 vCPU, ~5 min) + sonda semanal (2 vCPU, ~45 min) ≈ 58 000 vCPU-segundos y ≈115 000 GiB-segundos al mes. La cuota gratuita mensual de Container Apps es de **180 000 vCPU-segundos y 360 000 GiB-segundos** por suscripción. Se confirma en la factura del primer mes.
- **Hecho cuando:**
  - `az containerapp job execution list -g g7b -n g7b-latido -o table` muestra `Succeeded`;
  - Atlas Charts muestra esa corrida en **Salud**;
  - Sentry recibe el *check-in*.

### 3.3 Limpiar lo que ya no se usa [Tú, una semana después de 3.2 en verde]

```bash
az containerapp job delete -g g7b -n g7b-smoke-laboratorio --yes
az acr delete -g g7b -n g7bacr09b52a0e --yes
```

- **Antes, revisa** que `g7b-latido` lleve una semana con todas sus corridas en `Succeeded`.
- Después, en GitHub › environment `amatista1`, borrar la variable `G7B_ACR_OIDC_LISTO`.
- **Hecho cuando:** el gasto diario en Cost analysis baja a centavos.

> **Pausar Azure de emergencia:** `az containerapp job update -g g7b -n g7b-latido --trigger-type Manual` (y lo mismo para `g7b-sonda`). Se reactiva volviendo a poner `--trigger-type Schedule --cron-expression ...`.

---

## 9. Fase 4: la API y la conexión con Amatista (semana 3)

### 4.1 Heroku: la API de G7B [Tú + Código]

**[Tú]**
1. Reclamar Heroku en el pack (pide tarjeta y ser mayor de 18).
2. Instalar la CLI y entrar: `heroku login`.
3. Crear la app y prepararla:

```bash
heroku create g7b-api --stack container
heroku authorizations:create -d "G7B Actions"
```

4. El segundo comando imprime un token: va a Doppler como `HEROKU_API_KEY`. Si el nombre `g7b-api` está ocupado, elige otro y díselo al agente.
5. Doppler › integración **Heroku** › app `g7b-api`, con `MONGO_URI_LECTURA`, `AZURE_PUBLICADO_URL` y `SENTRY_DSN`.
6. Después del primer despliegue: `heroku ps:type web=basic -a g7b-api`, para que no se duerma; el plan Eco sí se duerme.

**[Código]**
- `api/` (FastAPI) + `heroku.yml` + `desplegar_api.yml`, que despliega en cada fusión a `main` que toque `api/`.
- La API **solo lee**: no guarda nada de quien la consulta, salvo contadores.

| Ruta | Devuelve | Lee de |
|---|---|---|
| `GET /v1/salud` | Versión publicada y hora de la última corrida | `publicado` |
| `GET /v1/publicado` | El manifiesto `g7b.publicacion/1` con sus hashes | `publicado` |
| `GET /v1/perfiles?nivel=&blender=` | Perfil con evidencia y estado | `publicado` |
| `POST /v1/recomendacion` | Recibe **solo** la huella técnica (CPU, GPU, RAM, SO y versión de Blender, sin nombres). Devuelve nivel, perfil, versión de Blender, texturas y herramientas | `publicado` + Mongo |
| `GET /v1/texturas?nivel=&tipo=` | Catálogo F3 | Mongo `g7b_catalogo` |
| `GET /v1/herramientas?tema=&blender=` | Catálogo F4 + equivalencias | Mongo `g7b_catalogo` |
| `GET /v1/conocimiento?q=` | Fragmentos con su fuente (para Goliat) | Mongo `conocimiento_3d` |
| `GET /v1/modelo-costos` | El modelo de costos de Geoda (archivo pequeño, versionado) | `publicado` |
| `/mcp` | Las mismas consultas como servidor MCP | Igual |

**Costo:** el dyno Basic (≈$7 al mes) cabe en los $13 de crédito. **Hecho cuando:** `curl https://g7b-api-<id>.herokuapp.com/v1/salud` responde con la versión publicada.

### 4.2 Amatista se conecta [Código en el repo de Amatista]

El detalle está en su documento de conexión. En resumen:

1. **Caché:**
   - una tabla `G7B_CACHE` en Oracle;
   - un temporizador systemd `amatista-g7b.timer` cada 6 h que baja el manifiesto, verifica los hashes y guarda la copia;
   - si la API no responde, usa Pages.
2. **Rutas nuevas:** `GET /api/g7b/v1/recomendacion` para el add-on y la PWA, usando **la caché**. Amatista nunca depende de que G7B esté arriba.
3. **Exportación agregada:** `GET /api/g7b/v1/agregados?desde=` con `AMATISTA_G7B_TOKEN`. Solo celdas con 5 equipos o más, sin cuentas, correos ni IP.
4. **[Código, G7B]** `traer_amatista.yml` (cada día) llama a esa ruta y guarda en `lago/bronce/amatista/`.

**Hecho cuando:**
- Amatista › Admin › Estado muestra la versión de G7B en caché;
- `bronce/amatista/` recibe su primer archivo (aunque venga vacío).

### 4.3 El dominio [Tú]

1. Reclamar Name.com; elegir un dominio para G7B.
2. En su DNS:
   - `CNAME api` → el destino que da `heroku domains:add api.<dominio> -a g7b-api` (Heroku pone el certificado solo);
   - `CNAME datos` → `maximiliano-cabello-mata.github.io`, más Settings › Pages › *Custom domain*.

**Hecho cuando:** `https://api.<dominio>/v1/salud` y `https://datos.<dominio>/publicado/actual.json` responden.

---

## 10. Fase 5: GPU, web y las familias nuevas (semana 4)

### 5.1 Colab (GPU) [Código + Tú]

- **[Código]** `cuadernos/g7b_gpu.ipynb`, con un botón "Abrir en Colab" en el README. Hace tres trabajos:
  - la sonda con Cycles en GPU (CUDA/OptiX), con `--origen colab`;
  - los vectores (embeddings) de los documentos de F5 para la búsqueda de Goliat;
  - etiquetas de texturas por IA (F3) y la métrica de calidad visual LPIPS.

  Todo se sube a `entrada`.
- **[Tú]** Colab › 🔑 *Secrets* › `AZURE_ENTRADA_URL`. Una corrida al mes con cada tipo de GPU disponible (T4, L4, A100).
- **Hecho cuando:** en el panel, **Equipos** muestra el origen `colab` con GPU.

### 5.2 Camber (lotes mensuales) [Tú + Código]

- **[Tú]** Reclamar; crear un espacio de trabajo; clonar el repo; variable `AZURE_ENTRADA_URL`.
- **[Código]** `cuadernos/g7b_lote_operaciones.ipynb`: la sonda de operaciones (F2) en CPU y GPU, más el entrenamiento mensual del **modelo de costos**, que se publica como archivo.
- **Hecho cuando:** `GET /v1/modelo-costos` devuelve una versión con fecha del mes.

### 5.3 Sonda web en celulares reales [Tú + Código]

- **[Tú]** Reclamar BrowserStack; usuario y llave a Doppler.
- **[Código]**
  - `sonda_web/` en Pages: una escena A-Frame que mide los fps durante 20 s;
  - `sonda_web.yml` (día 1 de cada mes): la abre en una lista de celulares y navegadores de BrowserStack y sube los resultados a bronce (F1 web).
- **Hecho cuando:** **Rendimiento** muestra la clase `movil` y Amatista puede recomendar entornos A-Frame por equipo.

### 5.4 Texturas, herramientas y modelos [Código]

- `capturar_catalogos.yml` (miércoles): metadatos de Poly Haven y ambientCG (F3 y F7), del catálogo de extensiones de Blender y de repos de software libre (F4).
- La sonda mide el costo de cargar cada textura en 1K, 2K y 4K.
- GitHub Models (`permissions: models: read`, gratis con tu cuenta) normaliza nombres y clasifica en tema o técnica.
- **Hecho cuando:** `GET /v1/texturas?nivel=N1` devuelve texturas con su resolución recomendada.

---

## 11. Fase 6: Geoda cierra el ciclo (semana 5)

### 6.1 Geoda en el add-on [Código en Amatista]

El add-on (ya tiene `red.py` y `corazon/adaptador.py`) suma el módulo `geoda`:

1. **detecta** la huella técnica del equipo (sin datos personales);
2. **pide** la recomendación a la API de Amatista;
3. **decide** con el modelo de costos local;
4. **aplica** el perfil con botón de deshacer, encendido poco a poco con **ConfigCat**;
5. **mide** los fps durante la práctica;
6. **reporta** el evento por la cola que ya existe (`pendientes.json`).

**Hecho cuando:** una práctica en un equipo N1 termina con el perfil aplicado y su evento llega a Amatista.

### 6.2 La semana de máquinas (VS Dev Essentials) [Tú + Código]

- **[Código]** `infra/azure/semana_vm.sh`: crea máquinas de varias series y tamaños (las que permita la cuota de esa suscripción). Cada una corre la sonda con `cloud-init`, sube a `entrada` y **se borra sola** al terminar.
- **[Tú]** Reclamar el crédito en my.visualstudio.com, correr el guion en esa suscripción y revisar al final de cada día que no quede nada encendido: `az vm list -o table`.
- **Hecho cuando:** **Equipos** muestra decenas de configuraciones de origen `azure` y el crédito se usó en mediciones.

### 6.3 El dataset con DOI [Tú + Código]

- **[Tú]** <https://zenodo.org> › entrar con GitHub › activar el repo.
- **[Código]** `liberar_dataset.yml` (día 1 de cada mes): crea un Release con los Parquet aprobados y su ficha. Zenodo le asigna un DOI.
- **Hecho cuando:** el primer DOI existe y está en la propuesta de estadía.

---

## 12. Todo lo automático, en una tabla

| Qué | Dónde | Cuándo (UTC) |
|---|---|---|
| `vigilar` (sensores de texto) | Actions | Cada 6 h |
| `zyte_a_lago` + `procesar` (texto) | Actions | Cada noche |
| `almacen` (Open Data) | Actions | Lunes 08:23 |
| `sonda_matriz` (Linux, ARM, Windows, macOS) | Actions | Martes 07:11 |
| `capturar_catalogos` (F3, F4, F7) | Actions | Miércoles |
| `g7b-sonda` (CPU) | Azure | Jueves 09:41 |
| `g7b-latido` (entrada → cubo → compuerta → publicado → panel) | Azure | Cada 6 h, minuto 17 |
| `traer_amatista` (F6) | Actions | Cada día |
| `publicar_pages` | Actions | Cada día |
| `sonda_web` (BrowserStack) | Actions | Día 1 de cada mes |
| `liberar_dataset` (Zenodo) | Actions | Día 1 de cada mes |
| Cuadernos de Colab y Camber | Tú | Una vez al mes |
| Escalado en Codespaces (2 a 16 núcleos) | Tú | Una vez al mes |
| API de G7B | Heroku | Siempre encendida |
| Caché de Amatista | Oracle | Cada 6 h |

**Apagar todo:**
- GitHub: `G7B_INGESTA_ACTIVA=false`;
- Azure: el comando de pausa de la sección 8;
- Heroku: `heroku ps:scale web=0 -a g7b-api`.

---

## 13. Lo que hay que programar (para los agentes)

| # | Trabajo | Repo | Fase | Tamaño |
|---|---|---|---|---|
| B1 | Integrar las PR #4 a #10 | G7B | 0 | S |
| B2 | `entrada.py` (buzón con contratos) | G7B | 2 | M |
| B3 | Fase `panel` → `g7b_panel` (Atlas Charts) | G7B | 2 | M |
| B4 | `publicar_pages.yml` + CSV | G7B | 2 | S |
| B5 | `.devcontainer/` | G7B | 2 | S |
| B6 | Imagen `g7b-trabajador` + identidad administrada en `g7b_lago` + `publicar_trabajador.yml` | G7B | 3 | M |
| B7 | `api/` en Heroku + MCP + `desplegar_api.yml` | G7B | 4 | L |
| B8 | `traer_amatista.yml` | G7B | 4 | S |
| B9 | Caché, rutas y exportación agregada | Amatista | 4 | M |
| B10 | Cuadernos de Colab y Camber (GPU, vectores, LPIPS, modelo de costos) | G7B | 5 | L |
| B11 | Sonda web + `sonda_web.yml` | G7B | 5 | M |
| B12 | `capturar_catalogos.yml` (F3, F4, F7) | G7B | 5 | M |
| B13 | Sonda de operaciones (F2) | G7B | 5 | L |
| B14 | Módulo `geoda` en el add-on + ConfigCat | Amatista | 6 | L |
| B15 | `semana_vm.sh` | G7B | 6 | M |
| B16 | `liberar_dataset.yml` | G7B | 6 | S |

S = una sesión, M = dos o tres, L = una semana. Cada uno en su rama desde `main`, con pruebas y su PR.

---

## 14. Cuánto dura

| Capa | Qué incluye | Dura |
|---|---|---|
| **Núcleo** | Actions, Pages, Atlas M0 y Charts, DuckDB, Zyte gratuito; Amatista en Oracle y Cloudflare | **Indefinido**, a ≈$0 |
| **Azure** | Lago y Jobs (≈$1 al mes de los $100) | **Todo el año** y se renueva mientras seas estudiante |
| **API** | Heroku | **24 meses.** Después pasa a un Container App de Azure que se apaga solo sin tráfico, o se queda en Pages; Amatista no lo nota |
| **Aceleradores** | BrowserStack, dominio, Camber, Colab, VS Dev Essentials | 1 a 12 meses; lo que midieron queda en el lago y en el DOI |

**En resumen:**
- el sistema completo funciona a toda máquina **unos 12 meses**;
- la API, **24**;
- el núcleo que alimenta a Amatista y a Geoda **no tiene fecha de fin**.

---

## 15. Cuando algo falla

1. **No improvisar en Azure:** copia la salida completa del error y pégala en la conversación. Nunca pegues SAS, llaves ni cadenas de conexión.
2. **Mira primero:**
   - el panel (**Salud**);
   - Sentry (¿qué tarea dejó de reportar?);
   - Actions (¿qué corrida está en rojo?).
3. **Si se filtró un secreto:**
   - SAS → `az storage container policy delete` de su política, y se genera otra;
   - Mongo, Heroku u otro → rotarlo en su portal y actualizar Doppler.

   Las tres SAS se revocan por separado.
4. **Si una tarea programada gasta de más:** apagar todo (sección 12) y revisar.
