# Investigación: cómo se integran Amatista y G7B

Fecha: 2026-11-01. Basada en el código de los dos repositorios a esa fecha:
- `amatista`: `main`, con el add-on 7.1, el Corazón 1.0 y los scripts SQL hasta el 013.
- `amatista-g7b-etl`: `main`, con la PR #1 fusionada.

Es una propuesta de diseño, **no código hecho**: nada de esto existe todavía en Amatista.

## 1. Punto de partida: dos proyectos con fronteras claras

| | Amatista | G7B |
|---|---|---|
| Qué es | Plataforma educativa: PWA, API, motor de prácticas, add-on y Corazón | Base de conocimiento y de mediciones del 3D libre |
| Dónde vive | Oracle Cloud (API y base) y Cloudflare (PWA) | Zyte, Azure (lago), MongoDB Atlas, GitHub Actions; después Heroku (API) |
| Datos de personas | Sí: cuentas, progreso, eventos de aprendizaje | **Nunca.** Solo conocimiento público con licencia y mediciones anónimas |
| Funciona sin el otro | Sí: sin conexión y sin G7B | Sí: no depende de Amatista |

**Regla de integración:** Amatista consume G7B como un cliente más, igual que lo haría Claude por MCP o cualquier otra aplicación. **G7B nunca recibe datos personales.** Si G7B se cae, Amatista sigue funcionando igual que hoy.

## 2. Lo que ya existe en Amatista y sirve para integrar

Revisado en el código:

| Pieza | Dónde | Por qué importa |
|---|---|---|
| Conexión del add-on con la API | `addon/amatista_blender/red.py` | Peticiones en un hilo aparte, con tiempo límite, sin congelar Blender. Respeta el ajuste de Blender que apaga el acceso a internet (`bpy.app.online_access`). Lo que no se pudo enviar queda en una **cola en disco** (`pendientes.json`, últimos 50) y se reenvía después, con la cuenta correcta |
| Puntos de extensión del Corazón | `engine/amatista_engine/corazon/extensiones.py` | `observadores` recibe cada evento y cada turno: es **el lugar natural para la telemetría**. `andamio`, `pistas` y `turno` permiten cambiar la ayuda sin tocar el Corazón |
| Ramas del Corazón | `corazon/ramas.py`, `practices/ramas/*.json` | Variantes por archivo JSON con herencia (`amatista.rama/1`). Una rama "equipo modesto" no necesita versión nueva del motor |
| Perfiles por programa | `corazon/perfiles/` | Blender y A-Frame estables; Maya y 3ds Max en borrador. Ahí entra el mapa de equivalencias de G7B |
| API de eventos | `backend/api/eventos.py` | Ya recibe eventos de aprendizaje, con tipos validados y límite de escritura |
| API del add-on | `backend/api/addon.py`, `enlace.py` | Vínculo de cuenta, prácticas, intentos, latido cada 5 s y ajustes: el add-on ya sabe hablar con la API |
| Límites de uso | `backend/api/limites.py` | Lo que necesita un endpoint nuevo que llame a G7B |
| Goliat | `frontend/src/goliat/cerebro.js`, `conocimiento.js` | Ayudante por reglas en el navegador. Su bitácora ya decide que la IA entra **solo cuando la regla no entiende** (T-012) |
| Base de datos | `backend/sql/` | Scripts aditivos; el siguiente libre es el **014** |

## 3. Arquitectura propuesta

```text
                      ┌──────────────────────── G7B ────────────────────────┐
                      │  lago (Azure) ──► embudo ──► oro: MongoDB + Parquet │
                      │                                │                    │
                      │            API G7B v1 (Heroku) + servidor MCP       │
                      │   /v1/perfiles   /v1/buscar   /v1/equivalencias     │
                      │   /v1/tecnicas   /v1/mediciones (entrada)           │
                      └──────────▲───────────────────────────▲──────────────┘
                                 │ HTTPS con clave           │ lotes agregados,
                                 │ (solo del servidor)       │ anónimos (opcional)
 ┌───────────────────── Amatista ┴───────────────────────────┴─────────────┐
 │  API Amatista (Oracle): caché de perfiles, proxy de búsqueda,           │
 │  telemetría con consentimiento, exportación agregada                    │
 │        ▲                                   ▲                            │
 │   PWA + Goliat (navegador)            add-on + Corazón (Blender)        │
 │   regla primero; si no entiende,      perfiles de equipo, botón         │
 │   pregunta a la API de Amatista       "Medir mi equipo", observadores   │
 └─────────────────────────────────────────────────────────────────────────┘
```

**Decisiones de diseño:**

1. **El add-on y la PWA nunca hablan directo con G7B.** Siempre pasan por la API de Amatista.
   - La clave de G7B vive solo en el servidor de Amatista.
   - Amatista guarda en caché lo que G7B responde.
   - Si G7B no está, Amatista responde con su caché o con los valores incluidos en el add-on.
2. **Los perfiles viajan también dentro del add-on.** Cada versión del add-on incluye una copia de `perfiles.json`. Sin internet, o sin G7B, el add-on aplica igual el perfil incluido. Así se respeta el "local primero" de Amatista.
3. **La telemetría de personas se queda en Amatista.** La recibe la API de Amatista (con consentimiento) por la misma cola y los mismos límites que ya existen. Si se comparte algo con G7B, es en **lotes agregados** (grupos de 5 o más) y sin identificadores. G7B nunca ve una cuenta.
4. **Las mediciones de la sonda sí pueden ir directo a G7B.** No contienen datos de la persona, solo el hardware y los tiempos.
5. **Contratos versionados.** Lo que cruza la frontera son los contratos `g7b.*/1` del plan (sección 7.3). Un cambio incompatible es un `/2` nuevo; el `/1` se mantiene.

## 4. Los cinco flujos de integración

### 4.1 Perfiles de equipo (la integración con más valor)

```text
sonda y Blender Open Data ──► G7B: g7b.perfil/1 ──► API Amatista (caché) ──► add-on
                                                                              │
                                    detecta el equipo (gpu.platform, RAM, Cycles)
                                    y aplica el perfil: Simplify, subdivisión,
                                    muestras, resolución, versión recomendada
```

- **En el add-on:** al arrancar, o con el botón "Ajustar a mi equipo", se lee la huella del equipo (el mismo código de `sonda/g7b_sonda.py`) y se elige el perfil. Los ajustes se aplican a la escena de la práctica, nunca a la configuración global de Blender sin permiso, y se pueden revertir con un clic.
- **En el Corazón:** una rama `blender-equipo-modesto.json` que hereda de `blender-principiante` y baja las exigencias visuales del andamio. Si el perfil lo pide, también cambia qué señales se hacen solas.
- **En Amatista:** una tabla `PERFILES_EQUIPO` (script 014), que es la caché de lo que publica G7B, más un endpoint `GET /api/addon/v1/perfil?huella=...`.
- **Sin G7B:** el add-on usa el `perfiles.json` incluido.

### 4.2 "Medir mi equipo" (la sonda dentro del add-on)

- Un botón del add-on corre la sonda con la escena ligera y el perfil ligero, en uno o dos minutos y en segundo plano, y muestra el resultado con palabras simples ("tu equipo trabaja fluido con el perfil ligero").
- Con permiso explícito, la medición se envía. Lo más simple es mandarla a la API de Amatista, que la reenvía a G7B sin datos de la cuenta.
- La cola en disco que ya existe sirve para enviarla cuando vuelva la conexión.

### 4.3 Goliat y el tutor (T-012)

```text
alumno escribe ──► cerebro.js (reglas) ──► ¿entendió? ─sí─► responde
                                               │no
                                               ▼
                              API Amatista /api/tutor/preguntar
                       (contexto: lección, versión de Blender, paso)
                                               │
                                     G7B /v1/buscar ──► fragmentos con fuente
                                               │
                         respuesta corta, con enlace a la fuente,
                         sin dar la solución del ejercicio
```

- **Primera versión, sin modelo de lenguaje:** Goliat muestra los 2 o 3 fragmentos más relevantes, con su enlace. Ya es útil, no cuesta nada y no inventa nada.
- **Segunda versión, con modelo:** el modelo redacta a partir de esos fragmentos. Dónde corre el modelo sigue siendo una decisión pendiente del plan. Hasta decidirlo, la primera versión basta.
- **Reglas que se mantienen:** Goliat nunca da la respuesta de un ejercicio (regla de `conocimiento.js`); sin conexión, solo funcionan las reglas; y todo pasa por los límites de `limites.py`.

### 4.4 Equivalencias para quien viene de Maya o 3ds Max

- G7B publica `g7b.equivalencia/1`.
- Amatista lo usa en dos lugares: en las **lecciones**, como un bloque "Si vienes de Maya", y en el **Corazón**, que completa los perfiles `maya.py` y `max3ds.py`, hoy en borrador.
- Las brechas, ordenadas por uso, se vuelven la lista de trabajo del add-on: presets, plantillas y nodos.

### 4.5 Telemetría de prácticas (etapa T4 del plan)

- Una extensión del Corazón en el punto `observadores` registra eventos que ya existen: paso iniciado, paso cumplido, señal perdida, tiempo en el paso y nivel del equipo.
- Esos eventos van a la API de eventos de Amatista, con un tipo nuevo, y solo con consentimiento.
- Amatista exporta a G7B solo lo agregado ("en el paso 3 de la práctica X se atora el 40 % de los equipos N1"), y G7B lo cruza con los perfiles. **No antes de tener usuarios y un aviso de privacidad.**

## 5. Seguridad, privacidad y fallas

| Riesgo | Respuesta |
|---|---|
| La clave de G7B se filtra desde el add-on | El add-on nunca la tiene: solo la API de Amatista |
| G7B caído o lento | Caché en Amatista, `perfiles.json` incluido en el add-on, tiempo límite corto; Goliat vuelve a las reglas |
| Datos falsos en las mediciones | Clave por instalación, límite de envíos y valores imposibles a revisión (plan, sección 7.2) |
| Una respuesta del tutor equivocada | Siempre con la fuente enlazada; solo fragmentos aceptados por el embudo; la regla de no dar soluciones |
| Privacidad de alumnos | Consentimiento, identificadores anónimos, publicación agregada (5 o más); G7B sin datos personales |
| Licencias | Cada fragmento lleva su licencia; lo que es CC BY-SA se muestra con atribución |
| Cambios incompatibles | Contratos versionados; Amatista declara qué versión entiende |

## 6. Orden recomendado (y por qué ese orden)

| Paso | Qué | En qué repo | Requiere | Esfuerzo estimado |
|---|---|---|---|---|
| I0 | `perfiles.json` v0 hecho a mano con Blender Open Data y tus mediciones; incluido en el add-on, con el botón "Ajustar a mi equipo" | G7B (datos) y `amatista` (add-on) | Sonda corrida en 2 o 3 equipos | 1 a 2 sesiones |
| I1 | Botón "Medir mi equipo" en el add-on | `amatista` | I0 | 1 sesión |
| I2 | API de G7B v1 en Heroku: `/v1/perfiles` y `/v1/buscar`; servidor MCP | G7B | F2 del plan (fragmentos y vectores) | 2 o 3 sesiones |
| I3 | Endpoint en Amatista con caché (script 014) | `amatista` | I2 | 1 sesión |
| I4 | Goliat con búsqueda de respaldo (primera versión, sin modelo) | `amatista` | I3 | 1 o 2 sesiones |
| I5 | Equivalencias en lecciones y perfiles de Maya y 3ds Max | Los dos | Catálogo de equivalencias v0 (F3) | 2 o 3 sesiones |
| I6 | Telemetría de prácticas con consentimiento | `amatista` | Usuarios reales y aviso de privacidad | 2 sesiones |

**Por qué empezar por I0:** no necesita la API, ni Heroku, ni modelos de lenguaje. Solo un archivo de datos medidos y un botón. Es también la primera prueba de la única idea realmente nueva del proyecto (ver el [reporte de propuestas](../reportes/2026-11-01_propuestas.md)): que una persona con una computadora modesta trabaje mejor gracias a datos medidos.

## 7. Decisiones que necesita esta integración

1. **¿El add-on puede cambiar ajustes de la escena solo, o siempre pregunta?** Recomendación: la primera vez pregunta y muestra qué cambia; después recuerda la respuesta.
2. **¿Las mediciones de la sonda van por la API de Amatista o directo a G7B?** Recomendación: por Amatista, para tener un solo punto de consentimiento.
3. **Dónde corre el modelo de lenguaje del tutor.** No hace falta decidirlo hasta después de I4.
4. **Licencia de los datos publicados por G7B** (plan, sección 12): define si Amatista puede incluir `perfiles.json` en el add-on sin más trámite. Con CC BY 4.0 o CC0, sí.
