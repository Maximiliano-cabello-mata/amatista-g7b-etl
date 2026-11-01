# Ofertas del Developer Pack y funciones de GitHub en G7B

Fecha: 2026-11-01. Qué servicio cumple cada papel, cuándo activarlo y qué no conviene activar. Estado detallado de cada nube: [infra/LEEME.md](../infra/LEEME.md).

## 1. Ya en uso

| Servicio | Papel |
|---|---|
| Zyte | Arañas de la ingesta web |
| MongoDB Atlas M0 | Conocimiento (`documentos`) y, pronto, las rebanadas del cubo. **Los $50 de crédito sin activar** |
| Azure ($100) | Lago de datos (West US 2) |
| GitHub Pro y Actions | Tareas programadas, pruebas, despliegue a Zyte, environment `amatista1` |
| Google Colab (créditos propios) | GPU para la sonda, cuando toque |

## 2. El "mutante" completo: cada oferta en su lugar

```text
 CAPTURAR                GUARDAR             PROCESAR            CONSULTAR Y VER            USAR
 Zyte · Actions ─┐                                              Atlas + Compass
 BrowserStack    ├──► Azure (lago) ──► DuckDB (cubo) ────────►  Deepnote (SQL)       ──► perfiles.json
 Colab · Azure + │    MongoDB (oro)     Camber (pesado)          Excel (tablas            → Amatista
  VS Dev Ess.    │                      Colab (GPU)               dinámicas)              → editor web
 Sonda en PCs ───┘                                              Atlas Charts · Pages
 Alrededor: Doppler (llaves) · Sentry (alarmas) · DataCamp y MongoDB University (aprender)
```

| Oferta | Papel | Cuándo |
|---|---|---|
| **BrowserStack** (1 año) | Sonda web en celulares y navegadores reales | Al construir la sonda web |
| **Doppler** | Llaves en un solo lugar | Ya |
| **Sentry** | Alarmas de tareas programadas | Antes de encender el interruptor |
| **Deepnote** | Análisis con SQL sobre DuckDB | Al llegar Blender Open Data |
| **Microsoft 365 (Excel)** | El cubo en tablas dinámicas (CSV exportado) | Al tener el cubo |
| **Camber** (mensual) | Procesamiento pesado y vectores | Si Actions no alcanza |
| **Heroku** ($13 al mes, 24 meses) | API de G7B y servidor MCP | Cuando exista la API |
| **VS Dev Essentials** ($200, **solo un mes**) | Una semana de mediciones en muchas máquinas de Azure | Semana planeada |
| **Name.com** (`.dev`) | Dirección del tablero público | Con el tablero |
| **CARTO** | Mapa de la brecha de equipo | Con datos de laboratorios y permiso de ubicación |
| **Visme** | Presentaciones para universidades | Al empezar las pláticas |
| **SimpleAnalytics** | Estadísticas del editor web que respetan la privacidad | Con usuarios |
| **Stripe** ($25) | Cobros de Amatista | Cuando Amatista cobre |
| **DataCamp, MongoDB University** (certificación gratuita), Educative | Aprender ingeniería de datos y SQL | Cuando haya tiempo |

**No activar, porque duplican algo:**
- Datadog, New Relic y Honeybadger (basta Sentry).
- LambdaTest (basta BrowserStack).
- PopSQL y SQLGate (no hay servidor SQL; basta Deepnote).
- Appwrite y Clerk (Amatista ya tiene cuentas).
- CodeScene, Travis CI y LocalStack.

**El núcleo que hace la diferencia:** Azure, MongoDB, GitHub Actions, DuckDB, Deepnote y BrowserStack, más Excel para el cubo.

## 3. Funciones de GitHub que conviene usar

| Función | Uso en G7B | Prioridad |
|---|---|---|
| **Escaneo de secretos con protección al subir** | Bloquear un push que lleve la SAS de Azure o la cadena de Mongo | **Activar ya** (Settings › Code security) |
| **Matriz de Actions** | Sonda en Linux x86, Linux ARM, Windows y macOS (Apple Silicon), cada noche y gratis en repos públicos | Alta |
| **Contenedor en `ghcr.io`** | La sonda con Blender incluido: un laboratorio la corre con un comando | Alta |
| **Formularios en Issues** | "Envía tu medición": una tarea valida el JSON y lo sube al lago. Los issues son públicos: solo la huella del hardware | Media |
| **Releases + Zenodo** | Una versión mensual del dataset con **DOI**, citable | Alta |
| **Pages** | Tablero público "¿Mi computadora puede?" | Media |
| **`repository_dispatch`** | Procesar en cuanto termina un trabajo de Zyte | Media |
| **Codespaces** | Entorno de desarrollo en la nube, y medir cómo escala una operación con 2 a 16 núcleos | Baja |
| **CodeQL, Dependabot, reglas de `main`** | Seguridad y calidad automáticas | Media |
| **Discussions** | Foro de la comunidad que mide | Con comunidad |
| **GitHub Models** | Modelos de lenguaje con límites gratuitos, para prototipos | Baja |
| **Sponsors** | Patrocinios del proyecto abierto | Con comunidad |
| **Campus Experts** | Respaldo para las pláticas en la universidad (etapa T3) | **Postularse pronto** |

Las máquinas con GPU de GitHub no vienen en el plan Pro: para GPU se usan Colab y Camber. Los límites exactos (horas de Codespaces, tamaño de los archivos de Releases) se confirman al configurar cada cosa.
