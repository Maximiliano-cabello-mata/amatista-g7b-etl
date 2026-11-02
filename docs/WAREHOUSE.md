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
