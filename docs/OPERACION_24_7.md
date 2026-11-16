# Operación 24/7 del flujo de G7B

Cómo corre solo el flujo, cómo avisa cuando no corre y cómo se reevalúa lo que ya está en el lago.

## 1. Un solo reloj: el ciclo

`.github/workflows/ciclo.yml` es lo único que decide cuándo corre el flujo. Las demás tareas ya no tienen horario propio ni se encadenan entre sí: el ciclo las lanza en orden y espera a que termine cada una.

| Paso | Tarea | Cuándo |
|---|---|---|
| Extracción | `vigilar.yml` (Geodar Radar) → `zyte_a_lago.yml` | Cada vuelta |
| Análisis | `procesar.yml`: el embudo con lo nuevo y con lo que cambió de reglas, y la publicación en MongoDB | Cada vuelta |
| Semanal | `telemetria.yml` → `cubo.yml` → `geoda_kernel.yml` | Martes, primera vuelta del día (UTC), o con `completo` |
| Entrega | `geoda_publicar.yml` → API de Amatista | Cada vuelta |

Una falla no detiene la vuelta: lo siguiente se intenta igual (publicar lo que el embudo ya aceptó). Solo se salta lo que depende de algo que falló: sin cubo nuevo no corre el kernel.

### El aviso

Al final de cada vuelta se revisa la salud del radar (`geodar salud`: fuentes con error o atrasadas más del doble de su frecuencia). Si una tarea falló o hay fuentes atrasadas, el ciclo:

- abre un issue con la etiqueta `g7b-alerta`, o comenta el que ya está abierto;
- termina en rojo en la pestaña Actions.

Cuando una vuelta sale bien, cierra el aviso. GitHub notifica por correo los issues nuevos del repositorio.

## 2. Quién dispara el ciclo

Del 11 al 16 de noviembre de 2026 GitHub no disparó **ningún** evento de este repositorio: ni horarios, ni encadenamientos (`workflow_run`), ni `push`. Solo funcionó lanzar a mano o por la API. Por eso el ciclo acepta tres disparadores:

| Disparador | Para qué |
|---|---|
| `schedule` (cada 6 horas) | Si GitHub vuelve a disparar los horarios, no hace falta nada más |
| `workflow_dispatch` | A mano desde la pestaña Actions, o desde un programador externo por la API |
| `repository_dispatch` (tipo `ciclo`) | Para programadores que solo saben hacer un POST |

Causas documentadas de horarios que no corren: el flujo no está en la rama por defecto, el repositorio es un fork (vienen apagados), 60 días sin actividad en un repositorio público, o retrasos y omisiones de GitHub en horas de carga. Conviene revisar la pestaña Actions y *Settings › Actions › General* de todos modos.

### Programador externo con cron-job.org (gratuito)

Mientras GitHub no dispare los horarios, esto es lo que deja el flujo corriendo solo.

1. **Token de GitHub de grano fino.** *Settings › Developer settings › Personal access tokens › Fine-grained tokens › Generate new token*:
   - Repository access: *Only select repositories* → `amatista-g7b-etl`.
   - Permissions › Repository permissions › **Actions: Read and write**. Nada más.
   - Caducidad: la más larga que permita; anota la fecha para renovarlo.
2. **Tarea en cron-job.org** (*Create cronjob*):
   - URL: `https://api.github.com/repos/Maximiliano-cabello-mata/amatista-g7b-etl/actions/workflows/ciclo.yml/dispatches`
   - Horario: cada 6 horas.
   - Método: `POST`. Cuerpo: `{"ref":"main"}`
   - Cabeceras: `Accept: application/vnd.github+json`, `Authorization: Bearer <el token>`, `X-GitHub-Api-Version: 2022-11-28`
   - Activa las notificaciones de falla por correo.
3. **Comprobar:** GitHub responde `204`. En la pestaña Actions aparece una vuelta de «Ciclo G7B (24/7)».

Así hay dos alarmas independientes: cron-job.org avisa si GitHub rechaza el disparo (token vencido, por ejemplo), y el ciclo avisa si una tarea falla o los datos se quedan viejos.

## 3. Reprocesamiento: nada de lo extraído se pierde

Bronce guarda todo lo extraído y nunca se borra ni se sobrescribe. Lo que cambia es cómo se evalúa.

Cada archivo de bronce recuerda con qué reglas se evaluó: su **huella de reglas**, que combina la versión del embudo (`VERSION_EMBUDO`), sus umbrales, la taxonomía (`fuentes/taxonomia.yml`) y la entrada del catálogo de su fuente. En cada vuelta, el procesador evalúa los archivos nuevos y además **vuelve a evaluar los que se evaluaron con reglas distintas**. Ejemplos:

- Se agrega una pregunta sobre animación a la taxonomía → todo bronce se reevalúa y lo que antes se rechazó por «no responde ninguna pregunta del plan» puede aceptarse.
- Se cambian los umbrales de una sola fuente en el catálogo → solo esa fuente se reevalúa.
- Se corrige la lógica del embudo → se sube `VERSION_EMBUDO` y todo se reevalúa.

Volver a evaluar no duplica nada:

- antes se descuenta lo que ese mismo archivo dejó la vez anterior, en los conteos y en el índice de repetidos, así que un documento no choca consigo mismo;
- sus salidas de plata se reemplazan; las que quedan vacías se escriben vacías, porque la firma del lago no permite borrar;
- lo aceptado que cambió se vuelve a publicar en MongoDB, que solo reescribe si el contenido cambió.

A mano, desde la pestaña Actions (*Procesar bronce › Run workflow*) o la terminal:

```bash
python -m geodar procesar --fuente blender-manual --forzar           # una fuente
python -m geodar procesar --lote bronce/arxiv-cs-gr/2026-11-11/      # un lote
python -m geodar procesar --simulacro                               # ver qué cambiaría, sin escribir
```

**Límite conocido:** si un documento estaba aceptado y con reglas nuevas deja de estarlo, sale de plata pero sigue en MongoDB. Retirarlo de MongoDB queda pendiente.

## 4. Por qué el embudo rechazaba tanto (medido el 16 de noviembre)

Del lago real: 2.570 documentos evaluados, 995 aceptados, 70 en revisión y 1.505 rechazados. Los rechazos, por causa:

| Causa | Documentos | Diagnóstico |
|---|---|---|
| No responde ninguna pregunta del plan | 383 | Correcto con la taxonomía de hoy. Es lo que el reprocesamiento recupera cuando el plan crezca |
| Casi duplicado o duplicado exacto | 560 | Casi todo es la misma página del manual en 5.2, 4.5, 3.6 y 2.79. No es basura: es información de versión que hoy se descarta (ver «Siguiente») |
| Texto insuficiente, página índice o líneas repetidas | 409 | Correcto: páginas índice, menús y fichas casi vacías |
| Fuente desconocida | 142 | **Error.** 112 son la araña antigua («Blender Docs») y 30 son `krita-noticias` y `freecad-blog`, que llegaron antes que el catálogo. Corregido: alias en el catálogo y reprocesamiento |
| Genérico (sin medidas, versiones ni ajustes) | 3 | Correcto |
| Idioma «desconocido» | 8 | **Error.** Resúmenes cortos sin palabras vacías. Corregido: solo se rechaza por idioma un texto de 80 palabras o más |
| Revisión por «versiones anteriores a 2.80» | 41 | **Error.** Era el manual 2.79, que se extrae a propósito para equipos viejos. Corregido: una página con versión declarada no se marca |

Además, «mixto» (español e inglés juntos) ya es un idioma admitido.

Con estas correcciones, la simulación sobre una copia del lago da 1.020 aceptados (antes 995) y 32 en revisión (antes 70), y una segunda pasada no cambia nada.

### Siguiente (no hecho)

- **Variantes de versión:** guardar la página del manual de cada versión como variante del documento aceptado, en lugar de rechazarla como duplicada.
- **Noticias:** de 79 documentos de fuentes de noticias, casi ninguno pasa. Solo se guarda el título por derechos de autor, y un título rara vez responde una pregunta del plan. Conviene tratarlas como señales de tendencia, igual que los foros.
- **Retirar de MongoDB** lo que deja de estar aceptado.
