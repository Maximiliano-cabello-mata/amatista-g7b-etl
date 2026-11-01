# Las nubes de G7B: qué está listo y qué falta

Cada nube cumple una capa del [plan](../docs/PLAN.md#72-un-servicio-por-capa). Se activa **solo cuando una fase la necesita**, para que los créditos no venzan sin usarse.

| Orden | Servicio | Capa | Estado | Qué hacer | Cuándo |
|---|---|---|---|---|---|
| 1 | **Zyte** | Ingesta web | Conectado. Las arañas nuevas (`blender_docs` estructurada, `paginas`, `manual_sphinx`) ya no escriben en MongoDB | Nada a mano: **Desplegar a Zyte** las despliega con cada push a `main`. Solo necesita el secreto `ZYTE_API_KEY`. Quitar `ITEM_PIPELINES` de los Raw Settings, porque ahora vive en `settings.py` | Ya |
| 2 | **MongoDB Atlas M0** | Conocimiento (oro) | Activo, capa gratuita | Crear dos usuarios de base de datos: uno que solo escribe y otro que solo lee (plan 7.2). Guardar la cadena del que escribe como secreto `MONGO_URI` en GitHub: **Procesar bronce** publica ahí lo aceptado (colección `documentos`). La colección vieja `foros_crudos` solo tiene los títulos del índice y se puede borrar. **No activar los $50** | Ya |
| 3 | **Azure** | Lago (bronce y plata) | Código listo y probado | Seguir [azure/LEEME.md](azure/LEEME.md): activar, correr el script, presupuesto y llaves | **Ahora** |
| 4 | **GitHub Actions** | Reloj y tareas programadas | Archivos listos: `vigilar` (cada 6 h), `zyte_a_lago` y `procesar` (cada noche), `pruebas` | Fusionar la PR; crear los secretos `AZURE_LAGO_URL` y `ZYTE_API_KEY` y la variable `ZYTE_PROJECT_ID` | Junto con Azure |
| 5 | **Doppler** | Secretos | Sin activar | Proyecto `g7b` con `AZURE_LAGO_URL`, `ZYTE_API_KEY` y `MONGO_URI`. Quitar `MONGO_URI` de los Raw Settings de Zyte cuando la araña lo lea de otro lado | Junto con Azure |
| 6 | **Sentry** | Vigilancia | Sin activar | Un monitor de tareas programadas para `zyte_a_lago` | F0, cuando la tarea ya corra |
| 7 | **Deepnote** | Cuadernos de análisis | Sin activar | Conectar el lago y analizar Blender Open Data con DuckDB | F0 |
| 8 | **Google Colab** | GPU para la sonda | Créditos disponibles | La sonda con Cycles en GPU (sonda/LEEME.md) | F1 |
| 9 | **Camber** | Procesamiento pesado | Sin activar | Fragmentos y vectores con GPU | F2 |
| 10 | **Heroku** | API de G7B y MCP | Sin activar | Desplegar la API cuando exista | F2 o F4 |
| 11 | **GitHub Pages + Name.com** | Tablero público | Sin activar | Dominio `.dev` o `.software` y el tablero con Evidence | F0 o F1 |

**Se guardan:** los $50 de MongoDB (hasta que el M0 se acerque a 400 MB) y los $200 de Visual Studio Dev Essentials (solo duran el primer mes: para una semana de benchmarks planeada).
