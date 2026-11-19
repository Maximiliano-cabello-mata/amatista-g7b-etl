# Revisión: «Arañas cibernéticas de telemetría» (17 de noviembre de 2026)

Revisión del documento [DOCUMENTO.md](DOCUMENTO.md), subido el 17 de noviembre. Estaba en la raíz del repositorio como `documentacion_aranas_telemetria_3d.md`.

## Veredicto

El documento está bien documentado técnicamente: el protocolo de depuración de Chrome (CDP), las extensiones de WebGL y WebGPU, Spector.js y la emulación por software de Chromium se describen con sus fuentes oficiales. Pero **responde a otra pregunta**. No describe una araña que salga a internet a recoger telemetría de los equipos de otras personas: describe cómo **medir la máquina en la que corre el navegador** mientras carga una página 3D.

- **Para el radar de telemetría, casi nada.** Medir el equipo donde corre la araña es medir un servidor de GitHub sin GPU; el propio documento lo reconoce en la sección 5.1. OpenWPM, VisibleV8 y ByteDefender son de investigación de privacidad, y HTTP Archive y sitespeed.io miden la velocidad de carga de páginas, no el rendimiento de Blender.
- **Para Amatista y la sonda, varias piezas útiles** (abajo).
- **La parte de evadir detectores de bots se descarta** (sección 5.2: ocultar `navigator.webdriver`, falsificar firmas de GPU, simular el movimiento del ratón, Stygian Browser). Choca con las reglas de Geodar, que se identifica como bot y respeta `robots.txt`, y expone al proyecto legalmente.
- **Cifras sin verificar:** las de arXiv («1,69 veces más telemetría», «pierden hasta el 45 %») no se pudieron confirmar porque la red de la sesión bloqueaba arxiv.org. Además miden eventos de rastreo publicitario, no hardware.

## Lo que se rescata

| Pieza | Para qué en G7B | Cuidado |
|---|---|---|
| `WEBGL_debug_renderer_info` (sección 4.1) | **Lo más valioso.** Dentro de Amatista, con consentimiento, da el nombre real de la GPU del estudiante, por ejemplo «ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11…)». Es la telemetría de población que falta (P3) y lo que permite asignar el nivel N0–N4 de cada estudiante con `g7b.hardware/1` | Esa cadena también sirve para identificar personas. Se guardan solo la clase y el nivel normalizados, nunca la cadena junto con otros datos, y se publican agregados de 5 equipos o más |
| Detectar render por software (secciones 4.1 y 5.1): SwiftShader, llvmpipe o «Software» en el nombre del renderer, y `failIfMajorPerformanceCaveat` | Una marca explícita `render_por_software` en la sonda y en cualquier medición web, que la saca de las recomendaciones. Es más clara que el `sin_ventana` actual | — |
| Métricas de fluidez (secciones 3.2, 4.2 y 7): `fps_p01_low` (el 1 % más lento, que detecta los tirones), cuadros de animación largos (W3C LoAF) y temporizadores de GPU (`EXT_disjoint_timer_query_webgl2`, `timestamp-query` en WebGPU) | La sonda de vista 3D y el editor web de Amatista | Los temporizadores de GPU no están en todos los navegadores; hay que tratarlos como opcionales |
| `renderer.info` de Three.js (sección 4.3) | Telemetría de prácticas en el editor web (P7): llamadas de dibujo, triángulos y texturas por cuadro, para saber si una práctica se atora por la escena o por el equipo | Hay que poner `autoReset = false` si hay varias pasadas por cuadro |
| Esquema de la sección 7 | Extender `g7b.telemetria/1` con `execution_mode`, `render_por_software` y `fps_p01_low` | Sin la cadena cruda del renderer |
| Código de referencia (sección 6) | Punto de partida para una **sonda web**, no para el radar | Sin las partes de evasión |

## Conclusión

La telemetría de equipos reales no se rastrea en internet: se **mide en los equipos de los estudiantes, con su permiso**, o se toma de fuentes públicas que ya la reunieron (Blender Open Data, reportes de error). Este documento sirve para la primera vía, dentro del navegador. Las tareas que salen de aquí están en [TAREAS_ARANAS.md](../../TAREAS_ARANAS.md).
