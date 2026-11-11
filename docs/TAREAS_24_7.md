# Tareas para dejar el flujo de datos funcionando 24/7

Estado al 11 de noviembre de 2026. El flujo va por etapas y cada una espera a la anterior: **extraer → analizar → entregar a Geoda**. Los horarios ya están escritos en `.github/workflows/`; no hay que programar nada nuevo para que corra solo. Lo que falta es destrabarlo y comprobar cada etapa una vez.

Diagnóstico de partida: [estado del flujo](reportes/2026-11-11_estado_del_flujo.md).

## Etapa 0 · Destrabar (responsable, unos 15 minutos)

| # | Tarea | Hecho cuando |
|---|---|---|
| 0.1 | Generar la firma nueva de Azure en Cloud Shell (comandos en el [plan maestro](PLAN_MAESTRO.md), paso 0.1) | Cloud Shell imprime la dirección del contenedor `lago` |
| 0.2 | Guardarla en GitHub: *Settings › Environments › amatista1 ›* secreto `AZURE_LAGO_URL` | El secreto muestra «Updated» con fecha de hoy |
| 0.3 | Confirmar que existen los secretos `ZYTE_API_KEY` y `MONGO_URI` en ese mismo entorno | Aparecen en la lista |

Nunca pegar la firma en un chat ni en un archivo.

## Etapa 1 · Extracción

| # | Tarea | Flujo | Horario | Hecho cuando |
|---|---|---|---|---|
| 1.1 | Correr el radar a mano en simulacro | `Vigilar fuentes (Geodar Radar)` | — | Termina en verde y lista las fuentes revisadas |
| 1.2 | Correrlo sin simulacro | el mismo, `simulacro: false` | — | Escribe en el lago y el paso «Salud de los sensores» pasa |
| 1.3 | Comprobar las arañas en Zyte | `Desplegar a Zyte` y `Zyte al lago` | — | `Zyte al lago` copia al menos un trabajo |
| 1.4 | Dejarlo solo | `Vigilar fuentes` | Cada 6 horas, al minuto 23 | Dos ejecuciones programadas seguidas en verde |
| 1.5 | Dejarlo solo | `Zyte al lago` | Diario, 09:17 UTC | Una ejecución programada en verde |

## Etapa 2 · Análisis

| # | Tarea | Flujo | Horario | Hecho cuando |
|---|---|---|---|---|
| 2.1 | Pasar lo crudo por el embudo de calidad | `Procesar bronce` | Diario, 10:47 UTC | Reporta cuántos documentos entraron y cuántos se rechazaron, con motivo |
| 2.2 | Capturar telemetría | `Telemetría G7B` | Martes, 10:23 UTC | Guarda y verifica en Azure, sin caer a la captura local de contingencia |
| 2.3 | Construir el cubo | `Cubo G7B` | Solo, al terminar 2.2 | Publica un cubo con versión y número de mediciones |
| 2.4 | Cuadernos de lectura | `Cuadernos G7B` | Diario, 12:41 UTC | Corren sin error contra el cubo nuevo |

## Etapa 3 · Entrega a Geoda

| # | Tarea | Flujo | Horario | Hecho cuando |
|---|---|---|---|---|
| 3.1 | Correr el kernel sobre el cubo | `Geoda kernel` | Solo, al terminar 2.3 | Deja perfiles como artefacto |
| 3.2 | Publicar el estado | `Publicar estado para Geoda` | Cada 6 horas y al terminar 2.1 o 2.3 | Existe `publicacion/geoda.json` en `main` |
| 3.3 | Comprobar el puente | — | — | `https://api.amatista-3dt.tech/api/g7b/v1/estado` deja de decir `sin_conexion` |

## Etapa 4 · Que no se vuelva a detener

| # | Tarea | Por qué |
|---|---|---|
| 4.1 | Aviso cuando un flujo programado falle dos veces seguidas | El flujo estuvo detenido una semana sin que nadie lo notara |
| 4.2 | Pasar de firma con vencimiento a identidad federada (OIDC) entre GitHub y Azure | La firma vuelve a vencer; la identidad federada no |
| 4.3 | Revisar una vez al mes el informe de salud del radar | Las fuentes cambian de formato y dejan de responder |

## Etapa 5 · Geoda con inteligencia artificial

Hoy Geoda decide con reglas y filtros fijos. La propuesta es agregar aprendizaje en dos lugares, sin quitar los filtros: siguen como barandal.

| # | Qué aprende | Con qué | Tamaño | Requisito |
|---|---|---|---|---|
| 5.1 | **Cuánto tarda una operación en un equipo.** Reemplaza la tabla de medianas de `geoda/costos.py` por un modelo que generaliza a equipos que nunca midió | Las mediciones del cubo | Un modelo pequeño (menos de 1 MB), entrenable en Colab en minutos, sin GPU | Etapas 1 a 3 funcionando, y unos miles de mediciones |
| 5.2 | **Qué documento sirve y cuál no.** Un clasificador que puntúa cada documento antes de guardarlo: ¿responde alguna de las preguntas del plan? | Los documentos ya aceptados y rechazados por el embudo, que sirven de ejemplos | Un modelo de lenguaje existente, por uso; no se entrena nada | Etapa 2 funcionando |
| 5.3 | **Comparar configuraciones.** «Con esta configuración tardas tanto; con esta otra, menos, con calidad parecida» | El modelo de 5.1 | Código, no modelo | 5.1 |

Reglas para esta etapa:

- El modelo **propone** y los filtros **deciden** qué no entra nunca: datos personales, licencias no verificadas y campos prohibidos.
- Si el modelo no tiene evidencia, responde «sin datos», igual que hoy.
- Toda decisión guarda con qué versión del modelo y con cuántas mediciones se tomó.
- 5.1 va antes que 5.2: es más barato, más medible y es lo que Geoda necesita para dar tiempos.
