# Estado del flujo de datos de G7B y Geoda · 10 de noviembre de 2026

Comprobación pieza por pieza, hecha a las 00:15 UTC del 11 de noviembre (tarde del 10 en Ciudad de México), sobre `main` (`92357d8`). Cada fila dice qué se probó de verdad y qué no se pudo probar.

```text
internet ──► arañas / Geodar ──► Azure (lago) ──► embudo ──► MongoDB
equipos  ──► sonda ───────────► Azure (lago) ──► cubo ──► Geoda ──► publicacion/geoda.json ──► API de Amatista ──► web
```

## Resultado

| Pieza | Qué se probó | Resultado |
|---|---|---|
| Código de G7B | `python -m pytest pruebas -q` en un entorno limpio | ✅ 122 aprobadas, 9 saltadas |
| Araña del manual de Blender | `scrapy crawl blender_docs` contra `docs.blender.org`, Blender 5.2, 4 páginas, sin escribir en ninguna base | ✅ 22 respuestas 200, 4 documentos extraídos, respeta `robots.txt` |
| Fuente de la araña | `https://docs.blender.org/manual/en/latest/` | ✅ Responde 200 |
| Azure: cuenta del lago | Petición sin credenciales a `g7blago09b52a0e.blob.core.windows.net` | ✅ **Existe y contesta.** Responde `PublicAccessNotPermitted`: está viva y cerrada al público, como debe |
| Azure: credencial de escritura (`AZURE_LAGO_URL`) | No se puede probar desde fuera: es un secreto del repositorio | ⚠️ El 5 de noviembre la CI falló con `AuthenticationFailed` por firma vencida. No hay evidencia de que se renovara |
| Publicación para Geoda | Buscar `publicacion/geoda.json` en `main` | ❌ **No existe.** El flujo `geoda_publicar.yml` nunca llegó a escribirlo |
| Puente en la API | `GET https://api.amatista-3dt.tech/api/g7b/v1/estado` | ❌ Responde `"estado":"sin_conexion"`, sin cubo ni perfiles. Es consecuencia de la fila anterior |
| GitHub Actions | Listar ejecuciones de `cubo.yml`, `telemetria.yml` y todas | ⚠️ GitHub devuelve **cero ejecuciones** y cero comprobaciones en el PR 18. Hay 11 flujos registrados y varios con horario (cada 6 horas). O las Actions están desactivadas en el repositorio, o el acceso de esta sesión no alcanza para verlas |
| Arañas en Zyte | — | No probado: necesita `ZYTE_API_KEY` |
| MongoDB | — | No probado: necesita `MONGO_URI` |
| Sonda dentro de Blender | — | No probado en esta revisión |

## Confirmado con una ejecución real (11 de noviembre, 00:22 UTC)

Se lanzó a mano `Vigilar fuentes (Geodar Radar)` en modo simulacro ([ejecución 42930800992](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42930800992)). Dos resultados:

- **GitHub Actions sí funciona.** La ejecución arrancó, instaló dependencias y corrió el radar. Es la número 22 de ese flujo; las anteriores ya no aparecen en la lista.
- **La firma de Azure está vencida.** Azure respondió `AuthenticationFailed`: «Signed expiry time [Wed, 04 Nov 2026 01:01:00 GMT]». Venció el 3 de noviembre por la tarde, hora de México. Desde entonces fallan todas las tareas programadas que tocan el lago.

Es el único bloqueo: con una firma nueva en el secreto `AZURE_LAGO_URL` del entorno `amatista1`, los horarios que ya existen (radar cada 6 horas, Zyte al lago y procesado a diario) vuelven a correr solos.

## Flujo reactivado (11 de noviembre, 00:44 a 01:05 UTC)

Con la firma nueva guardada en el secreto, se corrió cada tarea a mano y en orden:

| # | Tarea | Ejecución | Resultado |
|---|---|---|---|
| 1 | Radar en simulacro | [42933696471](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42933696471) | Azure aceptó la firma. 20 de 22 fuentes bien; `godot-blog` y `blendernation` bloqueadas por su `robots.txt` |
| 2 | Probar todas las fuentes, con las candidatas | [42934566192](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42934566192) | `freecad-blog` y `krita-noticias` responden; se activan en lugar de las dos bloqueadas |
| 3 | Radar de verdad, con el catálogo corregido | [42934853554](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42934853554) | ✅ Verde. Escribió en el lago |
| 4 | Telemetría | [42935203859](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42935203859) | ✅ Verde. Guardó y verificó en Azure |
| 5 | Cubo | [42935705846](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42935705846) | ✅ Verde. 3.006 mediciones: 5 aceptadas y 3.001 en revisión |
| 6 | Kernel de Geoda | [42936154406](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42936154406) | ✅ Verde |
| 7 | Publicar estado para Geoda | commit `abfef59` | ✅ Existe `publicacion/geoda.json` en `main` |
| 8 | Puente en la API de Amatista | `GET /api/g7b/v1/estado` | ✅ `"estado":"conectado"`, 995 documentos y el cubo nuevo |
| 9 | Embudo (Procesar bronce) | [42935199307](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/42935199307) | Seguía corriendo a los 14 minutos; procesa lo acumulado de una semana |

Observaciones:

- **Las cadenas automáticas no se dispararon** al lanzar a mano: el cubo no arrancó solo tras la telemetría, ni el kernel tras el cubo. Hubo que lanzarlos. Falta comprobar que sí se encadenan cuando la telemetría corre por su horario.
- **Geoda sigue sin recomendar.** De 3.006 mediciones solo 5 están aceptadas; las demás están «en revisión» y `recomendaciones_habilitadas` es `false`. El flujo entrega, pero Geoda todavía decide con reglas base.
- **El radar programado seguirá en rojo en `main`** hasta que se fusione el cambio del catálogo y de `vigilar` de este PR.

## Diagnóstico

El código está sano y las dos puntas externas responden: la fuente que recorren las arañas y la cuenta de Azure. Lo que está detenido es la **operación**:

1. **La credencial de Azure.** Sin una firma vigente no se escribe en el lago, no se construye el cubo y Geoda no tiene de dónde leer. Es la causa más probable de todo lo demás.
2. **La publicación para Geoda nunca se generó**, así que la API y la web muestran a G7B como desconectado.
3. **No se ven ejecuciones de Actions.** Hay que abrir la pestaña Actions del repositorio y confirmar si están activas.

## Para reactivarlo

En este orden. Los tres primeros pasos son del responsable, porque piden sus credenciales:

1. **Confirmar Actions.** En el repositorio, pestaña *Actions*: si pide habilitarlas, habilitarlas. Si hay ejecuciones recientes, anotar cuáles fallan.
2. **Renovar la firma de Azure.** Runbook: [`docs/azure/AZURE_24_7_CLOUD_SHELL.md`](../azure/AZURE_24_7_CLOUD_SHELL.md) y el paso 1.2 del [plan maestro](../PLAN_MAESTRO.md). Guardar la URL nueva en el secreto `AZURE_LAGO_URL`. Nunca pegarla en un chat ni en un archivo.
3. **Correr a mano, en este orden:** `Telemetría G7B` → `Cubo G7B` → `Publicar estado para Geoda`. El último debe dejar `publicacion/geoda.json` en `main`.
4. **Comprobar el puente:** `curl https://api.amatista-3dt.tech/api/g7b/v1/estado` debe dejar de decir `sin_conexion` en un máximo de 15 minutos.

Mejora recomendada después: pasar de firmas con vencimiento a identidad federada (OIDC) entre GitHub y Azure, que ya está preparada en `infra/azure/`. Así no vuelve a detenerse por una firma vencida.

## Sobre Codespaces

No hace falta para este flujo. Todo lo periódico ya corre (o debe correr) en GitHub Actions, que es gratuito para un repositorio público. Un Codespace sirve para trabajar a mano en el código desde el navegador, no para tareas programadas, y consume horas de la cuenta.
