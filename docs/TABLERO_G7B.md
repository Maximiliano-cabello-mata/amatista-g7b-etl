# Interfaz de G7B — Observatorio de rendimiento

Ya existe un **tablero HTML interactivo y sin servidor** para el primer cubo DuckDB real.

## Dónde obtenerlo

Abre [el workflow "Generar tablero HTML G7B desde DuckDB verificado"](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/workflows/generar_tablero_aislado.yml), entra en la ejecución satisfactoria y, al final de la página, descarga el artefacto **G7B-Tablero-DuckDB-Real**. Extrae el ZIP y abre `index.html` con Chrome, Firefox o Edge.

El HTML no incluye claves de Azure, no usa servidores ni scripts de terceros, y funciona sin internet. Los datos son una **instantánea** del cubo del experimento, no una conexión en tiempo real.

## Qué puedes hacer en la interfaz

- **Visión general:** filas, mediciones válidas/no disponibles, corridas y número real de equipos medidos.
- **Comparador:** elegir edición, modificadores o animación; nunca mezcla segundos y FPS.
- **Mediciones:** buscar por prueba, escena, nivel, origen; filtrar por calidad/perfil y exportar CSV.
- **Perfiles:** ver el recomendado, ajustes y evidencia de equipos/mediciones; deja claro cuándo es provisional.
- **Calidad:** controles, avisos, fallos y cobertura del experimento.

### Seguridad y limitaciones

La generación solo utiliza los archivos de este primer experimento verificado:

`lago/tmp/pruebas-duckdb/41380886305-intento1/`

El workflow comprueba el manifiesto `verificacion_duckdb.json`, los SHA-256 y el tamaño de cuatro archivos: `cubo.duckdb`, `resumen.json`, `perfiles.json` y `calidad.json`. **No escribe ni modifica datos en Azure.**

El tablero excluye huellas de hardware, nombres de equipos, datos personales y credenciales. Aunque el cubo tiene siete hechos, solo cinco mediciones tienen resultado; dos pruebas de vista 3D no pudieron ejecutarse sin ventana. Todo proviene de **una sola computadora temporal de GitHub Actions**, no de una población representativa.

La carpeta está en `tmp/` y se purga a los siete días según la configuración actual del lago. Descarga el artefacto si deseas conservar la instantánea.

## Generar el mismo tablero sin Azure

Si ya tienes los cuatro archivos localmente y Python disponible:

```bash
pip install duckdb
python -m g7b_almacen.tablero \
  --cubo datos/oro/cubo.duckdb \
  --resumen datos/oro/resumen.json \
  --perfiles datos/oro/perfiles.json \
  --calidad datos/oro/calidad.json \
  --salida tablero.html
```

Abre `tablero.html` en tu navegador. No necesitas instalar un servidor web, MongoDB ni conectarte a Azure.

**Siguiente fase:** actualizar el panel automáticamente con cada cubo aprobado y ponerlo detrás de autenticación si se desea acceso web permanente. No publicar archivos ni perfiles de hardware públicamente sin decidir antes su política de privacidad.
