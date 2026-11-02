# El warehouse de G7B

Fecha: 2026-11-02. Cómo funciona el Data Warehouse (`g7b_almacen`): de dónde salen los datos, cómo se limpian, el cubo de dimensiones y qué entrega. Es la columna vertebral del plan (sección 0, punto 2). Corre igual en tu PC, en Deepnote o en GitHub Actions, sin encender ninguna máquina.

## 1. La cadena, de un vistazo

```text
 BRONCE (crudo, nunca se toca)            PLATA (limpio, Parquet)          ORO (listo para usar)
 bronce/opendata/<día>/<copia>.zip  ──►   plata/opendata/render.parquet ─┐
 bronce/sonda/<día>/*.json          ──►   plata/sonda/medicion.parquet  ─┴─► oro/cubo.duckdb
                                                                              oro/parquet/<tabla>.parquet
 (sintetico/sonda/... NUNCA entra al cubo)                                    oro/csv/<vista>.csv   (Excel)
                                                                              oro/resumen.json      (tablero)
                                                                              oro/perfiles.json     (Amatista)
```

Siempre es **ELT**: primero se guarda el crudo, después se transforma. Por eso el cubo se reconstruye entero en cada corrida: a esta escala es barato y así oro nunca se desincroniza de bronce. Si mañana cambias una regla de calidad, vuelves a construir y listo, sin re-descargar nada.

## 2. Cómo correrlo

Contra una carpeta local (sin nube, ideal para probar y para Deepnote):

```bash
pip install -r requirements-almacen.txt
python -m g7b_almacen opendata  --carpeta datos   # baja Blender Open Data a bronce
python -m g7b_almacen sonda resultados --carpeta datos   # agrega tus mediciones de la sonda
python -m g7b_almacen construir --carpeta datos   # arma plata y oro (cubo, CSV, perfiles)
```

Contra el lago de Azure (lo mismo, sin `--carpeta`): necesita `AZURE_LAGO_URL`. En GitHub Actions lo hace solo la tarea **Warehouse (Open Data y cubo)** cada semana.

## 3. El cubo (modelo en estrella)

Dos tablas de hechos y seis dimensiones, en DuckDB (PLAN 7.4):

| Hechos | Una fila es | Fuente |
|---|---|---|
| `hechos_render` | Un render de una escena con su tiempo y muestras por minuto | Blender Open Data (CC0) |
| `hechos_medicion` | Una prueba de la sonda (edición, vista 3D, animación, render) con su mediana y calidad | Amatista Sonda |

Dimensiones: `dim_dispositivo` (clase: cpu, gpu_integrada, gpu_dedicada; y nivel N0–N4 para la sonda), `dim_version` (con marca LTS), `dim_escena`, `dim_perfil`, `dim_origen` (tus PCs, Actions, Colab, Azure, laboratorio) y `dim_tiempo`.

El `resumen.json` para el tablero junta las **dos mitades** del proyecto: las mediciones (sonda y Open Data) y el **conocimiento** (documentos del embudo de texto, que ya funcionaba): lee `control/embudo.json` y `control/procesados.json` tal como los dejó `g7b_ingesta/procesar.py`, sin re-procesar ni tocar MongoDB. Si la ingesta de texto está apagada, ese bloque va en ceros.

Vistas listas para leer: `v_render_por_clase`, `v_medicion_por_nivel`, `v_salud` (cuántas filas por calidad) y `v_equipos_sonda`. Se exportan a CSV para abrirlas en Excel con tablas dinámicas, y el cubo entero (`oro/cubo.duckdb`) se abre en Deepnote con una línea de SQL.

## 4. Calidad: qué dato cuenta

Cada prueba de la sonda lleva una etiqueta de calidad: `ok` (repetida y estable, varía ≤ 10 %), `variable` (varía más: no se usa aún), `una_repeticion` (falta repetir) y `no_disponible` (no se pudo medir, con su motivo). Solo las `ok` de mediciones **reales** cuentan para los perfiles. Lo sintético se guarda aparte y nunca entra al cubo (PLAN 5.7).

## 5. perfiles.json: lo que Amatista recibe

`oro/perfiles.json` (contrato `g7b.perfil/1`) dice, por nivel de equipo y versión de Blender, el perfil más completo que sigue siendo fluido (30 fps de vista 3D, o 24 de animación si no hay datos con ventana). Cada perfil trae su evidencia y su estado:

- **confiable:** 5 mediciones o más, de 3 equipos o más (meta H1 del horizonte).
- **provisional:** hay señal, pero aún no suficiente. Amatista puede usarlo mostrándolo como provisional.

Así el add-on aplica un perfil medido, no una corazonada, y si G7B no responde usa la copia incluida.

## 6. Qué entra y qué no

- **Sí:** datos públicos de rendimiento de 3D libre, con fuente y licencia (Blender Open Data hoy; el catálogo se amplía a otros programas y librerías). Mediciones de la sonda sin datos personales.
- **No:** datos personales de nadie. La telemetría de personas se queda en Amatista, con consentimiento, y a G7B solo llega agregada. Una sonda que mida a alguien sin que lo sepa no se construye: contradice el aviso de privacidad del proyecto y la ley.

## 7. Tareas programadas (el «24/7»)

El warehouse no necesita una máquina encendida. Son tareas que corren solas y se apagan:

| Tarea | Cuándo | Qué hace |
|---|---|---|
| **Warehouse (Open Data y cubo)** | Lunes | Baja la copia de Open Data y reconstruye el cubo |
| **Sonda en matriz (nube)** | Martes | Corre la sonda en Linux x64/ARM, Windows y macOS, y sube las mediciones |
| vigilar · zyte_a_lago · procesar | Ya existían | Ingesta de texto, apagada por el interruptor `G7B_INGESTA_ACTIVA` |

Con Sentry (`SENTRY_DSN`), cada tarea avisa si deja de correr. El detalle de cuánto tiempo aguanta cada oferta está en [OFERTAS_Y_GITHUB.md](OFERTAS_Y_GITHUB.md), sección «¿Cuánto dura el 24/7?».

## 8. Calidad por compuertas y el latido 24/7

Añadido 2026-11-02. Cómo aseguran las empresas grandes que los datos lleguen limpios, y cómo lo hacemos nosotros con el mismo principio pero gratis.

### Cómo lo hace la industria (y dónde está en G7B)

| Práctica de la industria | Qué es | Dónde vive en G7B |
|---|---|---|
| **Contratos de datos** | Cada dato cumple un esquema con versión; lo que no cumple, se rechaza | Contratos `g7b.*/1`; se validan al leer |
| **Arquitectura medallón** (bronce/plata/oro) | Guardar el crudo y refinar por capas, sin perder el origen | `bronce/` → `plata/` → `oro/` en el lago |
| **Expectativas de calidad** (Great Expectations, tests de dbt) | Reglas que los datos deben cumplir, medidas en cada corrida | `g7b_almacen/calidad.py` |
| **Compuerta de calidad** (quality gate) | No se promueve a «bueno» lo que no pasa las reglas | La fase `calidad` del orquestador; si algo falla, el oro no se marca confiable |
| **Orquestación por fases** (Airflow, Dagster) | Un paso corre, termina, y dispara el siguiente | `g7b_almacen/orquesta.py` + el latido |
| **ELT idempotente** | Reprocesar sin volver a extraer; correr dos veces da lo mismo | El cubo se reconstruye entero desde bronce |
| **Observabilidad** | Avisar cuando una tarea deja de correr o la calidad baja | Sentry (monitores) + `oro/calidad.json` |
| **Sin datos personales** | Minimizar y separar lo identificable | Nada personal entra a G7B; solo agregados con consentimiento |

### Las compuertas (`calidad.py`)

Antes de dar el oro por bueno, se corren expectativas sobre el cubo: contrato de los perfiles, volumen, frescura de Open Data, sin duplicados, sin nulos en las claves, fps dentro de rango, que no haya datos sintéticos, un perfil por nivel, y cuánta medición quedó inestable. Cada una pasa (`ok`), avisa (`aviso`) o falla (`falla`); la compuerta se **aprueba** solo si ninguna falla, y todo queda en `oro/calidad.json` para el tablero de salud.

### El latido (`orquesta.py`)

Trabaja 24/7 pero **por pasos**, no todo de un golpe. Cada hora, el latido avanza una sola fase:

```text
ingesta ──► cubo ──► calidad (compuerta) ──► oro confiable
```

Cada fase se enciende solo cuando tiene trabajo y se apaga pasando el turno. El estado vive en `control/orquesta.json`, así el proceso se para y sigue sin perder el hilo y nunca rehace lo que ya está al día. Si la ingesta falla (sin red), se hace a un lado un rato para no frenar el cubo ni la compuerta con los datos que ya hay.

```bash
python -m g7b_almacen calidad   # corre solo la compuerta
python -m g7b_almacen latido    # avanza un paso del pipeline
```

El análisis del resultado (ciencia de datos) entra por [analisis/](../analisis/README.md): el cubo se abre en Deepnote, Excel o Camber, todos leyendo el mismo `oro/cubo.duckdb`.
