# Cubo G7B: Parquet + DuckDB en Azure

## Qué se integra

Esta entrega continúa el diseño de hechos/dimensiones del [PR #4](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/4)
y la verificación de escritura/lectura del [experimento del PR #7](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/7).
Esas propuestas no estaban integradas en main. La implementación actual adapta el
modelo al contrato `g7b.telemetria/1` que ya produce la captura real. No fusiona sus
workflows, estimaciones de perfiles ni otras modificaciones pendientes.

El análisis documental de Deepnote del PR #13 es distinto: sus conteos de texto no
se convierten en rendimiento. La documentación sigue en su recorrido actual.

## Almacenamiento y consulta

Azure guarda versiones de archivos; DuckDB ejecuta las consultas en Actions,
Deepnote o una computadora. No se comparte un archivo abierto para múltiples
escritores. Los datos portables están en Parquet y la copia DuckDB es reconstruible.

- Entrada: `plata/telemetria/{aceptado,revision}/<fuente>/*.jsonl.gz`.
- Plata portable: `plata/cubo/<version>/mediciones.parquet`.
- Oro: `oro/cubos/<version>/cubo.duckdb`, `parquet/*.parquet`, `resumen.csv`,
  `resumen.json` y `manifiesto.json`.
- Puntero vigente: `control/cubo_actual.json`.

La versión publicada no se sobrescribe. Se verifica SHA-256 de todos los archivos
descargándolos de Azure, luego el manifiesto, y solo entonces se cambia el puntero.
Una falla previa conserva la versión vigente; puede dejar una versión parcial no
referenciada. El workflow serializa publicaciones. No se ha definido todavía una
política de eliminación de versiones; hay que vigilar su crecimiento.

## Modelo

Una fila es una prueba/escena medida, no un equipo ni una corrida completa.

| Tabla | Contenido |
|---|---|
| `mediciones` | Tabla completa validada, clave única por medición |
| `hechos_medicion` | Pruebas de la sonda |
| `hechos_render` | Resultados públicos por escena de Cycles |
| `dim_dispositivo` | Hardware declarado, backend y sistema; sin adivinar nivel |
| `dim_version` | Programa y versión completa, sin juntar parches |
| `dim_escena` | Nombre y fuente, para evitar colisiones |
| `dim_perfil` | Perfil, fuente y versión de sonda; no_aplica cuando falta |
| `dim_tiempo` | Día UTC, año y mes; instante original normalizado en hechos |
| `dim_origen` | Fuente, entorno declarado y licencia |
| `procedencia` | Archivos de entrada asociados a cada medición |

El contrato de captura actual no declara entorno de ejecución: se conserva
`no_declarado`, sin inferir que toda sonda proviene de una PC personal. Esa mejora
de procedencia queda pendiente en la captura. Los datos públicos no identifican
computadoras individuales: un modelo de dispositivo no es un equipo único.

## Calidad y consultas

`v_exploracion` conserva aceptados y revisión; `v_mediciones_aceptadas` solo
aceptados. `v_calidad` cuenta filas por fuente y estado. `v_resumen` agrupa por
hardware, versión, escena, perfil, sonda, prueba, métrica, unidad, estado y modo
sin ventana. No suma FPS con muestras/minuto ni compara escenas diferentes.

```sql
SELECT * FROM v_calidad ORDER BY fuente, estado;
SELECT fuente, version, escena, metrica, unidad, estado, mediciones, mediana
FROM v_resumen ORDER BY mediciones DESC LIMIT 20;
SELECT version, prueba, unidad, valor FROM v_mediciones_aceptadas;
```

El constructor elimina duplicados exactos por `id` y conserva todas sus rutas de
procedencia. Si un mismo ID cambia de contenido, falla: no elige una versión a
ciegas. Rechaza sintéticos, valores inválidos, contratos desconocidos y aceptación
contradictoria. Compara contenido de Parquet con DuckDB y reabre el archivo cerrado.

Esta validación técnica **no certifica representatividad ni recomendaciones**.
Los benchmarks públicos permanecen en revisión. No se publica `perfiles.json`.
El cubo es exploratorio; Geoda y la relación semántica con documentos siguen pendientes.

## Ejecutar

```sh
pip install -r requirements-cubo.txt
# Reconstrucción local; salida nueva/vacía, JSONL normalizados en entrada:
python -m g7b_almacen.cubo --entrada captura --salida resultado-cubo
# Leer el lago y publicar una versión (credenciales en el entorno):
python -m g7b_almacen.cubo --azure --salida resultado-azure
# Descargar la versión vigente; verifica hash y conteo:
python -m g7b_almacen.descargar cubo-local.duckdb
```

Configurar AZURE_LAGO_URL como secreto, nunca en código. Para consumo de Deepnote,
usar una credencial de solo lectura. Abrir siempre la copia con
`duckdb.connect('cubo-local.duckdb', read_only=True)` y cerrar antes de reemplazarla.
El [cuaderno](../analisis/cubo/Deepnote_G7B.ipynb) descarga una copia nueva y muestra
las consultas. Se entrega preparado; ejecutarlo dentro de Deepnote requiere la
integración de credenciales de ese workspace.

## Operación

`Cubo G7B` corre al integrar su código en main, manualmente y después de una
ejecución exitosa de `Telemetría G7B` en main. Usa `amatista1`, 20 minutos de
límite y guarda artefactos por 14 días. Después de publicar descarga nuevamente
el cubo mediante el puntero vigente, verifica su hash y lo abre en solo lectura.

Se reconstruye completo con un máximo de un millón de filas de entrada; no es
incremental. El conjunto actual es pequeño. Se deberán revisar memoria, costos,
retención y particionado al crecer, y ampliar la muestra pública de captura.
