# Visión de G7B y su relación con Amatista

Fecha: 2026-11-01. Es el **norte** del proyecto: hacia dónde va, qué es cada pieza y cómo se une con Amatista. El orden de trabajo concreto está en [PLAN.md](PLAN.md) y las definiciones exactas, en [FICHAS_TECNICAS.md](FICHAS_TECNICAS.md). Del lado de Amatista, la misma visión está en su repo: [propuesta "centro 3D y G7B"](https://github.com/Maximiliano-cabello-mata/amatista/blob/main/docs/propuestas/2026-11-01_centro_3d_y_g7b.md).

## 1. La visión en una frase

> **Que cualquier persona pueda aprender y trabajar 3D con herramientas libres, con una experiencia que se adapta a la computadora que tiene, en español y sin depender de internet.**

## 2. Tres piezas, dos proyectos

| Pieza | Qué es | Repo |
|---|---|---|
| **Amatista** | La plataforma: **enseña** (cursos, prácticas validadas en Blender, Goliat) y, desde hoy, es también un **centro de conocimiento 3D** (recomendaciones, recursos y equivalencias según el equipo y el avance) | `amatista` |
| **G7B** | El motor de datos: **mide, ordena y decide.** Lago, embudo, cubo, modelo de costos y perfiles | `amatista-g7b-etl` (este) |
| **Geoda** (nombre de trabajo) | El kernel: la capa que **aplica** las decisiones de G7B dentro de las herramientas. Su parte de interacción (el Corazón) vive en Amatista; su parte de recursos (planificador y operaciones) se diseña aquí | Los dos |

### Separados, pero unidos

```text
        AMATISTA (enseñar y recomendar)                     G7B (medir y decidir)
   prácticas, Goliat, recomendaciones ── eventos y mediciones ──►  lago ► cubo ► modelo de costos
            ▲                            (con consentimiento,               │
            │                             sin datos personales)              │
            └──────── perfiles, recomendaciones, equivalencias ◄─────────────┘
```

- **Separados:** cada uno funciona sin el otro, tiene su repo, sus servicios y su licencia. Amatista vive en Oracle y Cloudflare; G7B en Zyte, Azure, MongoDB y GitHub Actions.
- **Unidos:** se alimentan mutuamente por **contratos versionados** (`g7b.perfil/1`, `g7b.medicion/1`, `g7b.evento/1`). Amatista le da a G7B mediciones y eventos de práctica; G7B le devuelve perfiles, recomendaciones y equivalencias.
- **La regla de datos:** los datos personales viven **solo** en Amatista. G7B recibe mediciones sin identificar o agregados de 5 equipos o más.

## 3. Lo que G7B mide y para qué

**Prioridad desde el 2026-11-01: telemetría antes que texto.** El texto (manuales, foros, artículos) sirve para que una IA consulte la documentación; las mediciones son lo que hace funcionar al kernel.

| Lo que se mide | Fuente | Para qué |
|---|---|---|
| Render por dispositivo | Blender Open Data (CC0) | Mapa de capacidad del hardware |
| Vista 3D, edición, animación y render con perfiles | Sonda de Blender: tus PCs, GitHub Actions, Colab, Azure, laboratorios | Perfiles por nivel de equipo |
| Costo de cada operación 3D (subdividir, simplificar, booleanas, UV...) | Sonda de operaciones (por construir) | Modelo de costos y planificador de Geoda |
| Rendimiento en navegadores y celulares | Sonda web con BrowserStack (por construir) | Editor web y entornos A-Frame de Amatista |
| Eventos de las prácticas (pasos, pistas, tiempos) | Amatista, con consentimiento | Prácticas que se adaptan; la estadía |

Todo pasa por el **warehouse**: captura → lago (bronce) → transformación (plata, Parquet) → **cubo** (oro: hechos y dimensiones en DuckDB) → interfaz (Atlas, Excel, Deepnote, tablero público) y `perfiles.json`.

## 4. Lo que hace Geoda con esos datos

1. **Detecta el equipo** (huella del hardware, nivel N0 a N4).
2. **Consulta el modelo de costos:** cuánto costará cada operación en ese equipo.
3. **Decide:** si cabe, con qué calidad y dónde correrla (aquí, en otra PC de la red o en la nube).
4. **Aplica** con herramientas libres: Blender, el editor web y después Godot o FreeCAD.
5. **Mide otra vez** y corrige.

La IA entra **dentro** del sistema:
- un modelo de costos pequeño que corre local;
- una métrica de calidad visual (LPIPS);
- un detector de mediciones anómalas;
- un modelo de lenguaje local (Ollama) para normalizar nombres de equipos y preguntarle al cubo en español.

## 5. Lo que no es

- **No es un programa 3D nuevo** ni un fork de Blender. No se recompila Blender: se ofrece la versión oficial adecuada con la plantilla y el add-on de Amatista.
- **No es un motor de render propio** ni una IA generativa entrenada desde cero.
- **No es "big data" por sí mismo:** son miles de mediciones bien hechas al mes, no millones sin control.

## 6. Licencias y marca

- **Código:** GPL-3.0 o posterior en lo que usa la API de Blender (add-on, Corazón). Para el resto de G7B se propone AGPL-3.0.
- **Datos que se publiquen:** se proponen CC BY 4.0 o CC0, con DOI (GitHub Releases y Zenodo).
- **Marca:** "Blender" es de la Blender Foundation; se usa "Amatista para Blender".

## 7. Hasta dónde puede llegar

Por etapas, en el [horizonte](reportes/2026-11-01_horizonte.md):
- **H1 (3 meses):** el cubo, los perfiles aplicados por el add-on, un dataset con DOI y la prueba con personas (la estadía).
- **H2 (6 a 12 meses):** el modelo de costos, el planificador, el editor web y Godot como segundo programa.
- **H3 (1 a 3 años):** la distribución abierta del 3D y Amatista como centro de la comunidad.

¿Ya existe esto? La [investigación del estado del arte](investigacion/2026-11-01_novedad_kernel_3d.md) concluye que nadie reúne estas piezas:
- **Necesidad real hoy, de nicho:** la plataforma educativa, los perfiles y el dataset.
- **Necesidad futura:** el planificador y el editor web.
- **Necesidad que nadie prevé todavía:** el modelo de costos por operación y la capa kernel.
