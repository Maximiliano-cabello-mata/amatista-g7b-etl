# Comparación de las arañas de documentación y telemetría

Prueba del 19 de noviembre de 2026, hora de México. Las dos arañas ejecutaron su código real en GitHub Actions. Site releyó las páginas públicas ya archivadas en el lago. Las sondas de telemetría generaron datos nuevos en el runner. [Ejecución y registros](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44666052441) · [Datos del experimento](comparacion-2026-11-19.json)

## Site, con la misma entrada y el mismo presupuesto

Se probaron la araña documental v3, Site 4.0 y Site 4.1. Primero recibieron los mismos 131 HTML, en el mismo orden y con el mismo identificador de fuente, programa y versión. Después cada versión arrancó desde el índice y eligió sus siguientes páginas con su propia frontera, con un máximo de 64 intentos. Las seis corridas terminaron sin páginas ausentes del archivo y sin publicar candidatos. El artefacto incluye la huella SHA-256 de cada HTML. [Datos de Site](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44666052441/artifacts/14597003970)

| Versión | 131 páginas, útiles / seleccionados | Precisión | 64 intentos, útiles / seleccionados | Precisión |
|---|---:|---:|---:|---:|
| Documental v3 | 20 / 21 | 95,2 % | 14 / 15 | 93,3 % |
| Site 4.0 | 66 / 80 | 82,5 % | 36 / 44 | 81,8 % |
| Site 4.1 | 64 / 70 | 91,4 % | 36 / 38 | 94,7 % |

Con 64 intentos, Site 4.1 conserva los mismos 36 bloques útiles que 4.0 y elimina seis de los ocho falsos positivos. La reducción es del 75 % y la mejora de precisión es de 12,9 puntos porcentuales. Frente a v3 aumenta de 14 a 36 bloques útiles. En todo el capítulo aumenta de 20 a 64 respecto a v3, con una precisión 3,8 puntos inferior.

En el capítulo completo, 4.1 excluye diez candidatos presentes en 4.0. Ocho eran falsos positivos y dos contenían información útil en su ubicación. En un caso, el texto técnico de Mix Vector también aparece completo en Mix Color y 4.1 conserva esa copia. El otro caso fue el procedimiento para reproducir la distorsión de Wave Texture con las coordenadas y la salida de Noise. Contar por bloque y ubicación hace visible esa pérdida. [Wave Texture](https://docs.blender.org/manual/en/4.5/compositing/types/texture/wave.html#inputs) · [Mix Vector](https://docs.blender.org/manual/en/4.5/compositing/types/vector/mix_vector.html#properties) · [Mix Color](https://docs.blender.org/manual/en/4.5/compositing/types/color/mix/mix_color.html#properties)

La unidad de calidad es el bloque seleccionado con su URL. La precisión se calcula como útiles / seleccionados. Entre todos los recorridos hubo 80 candidatos distintos por identificador y ubicación. Se reutilizaron 76 etiquetas coincidentes del archivo y Codex clasificó los cuatro restantes por su cita antes de consultar qué versiones los eligieron. Se exigió una acción o parámetro con efecto técnico concreto y correctamente atribuido. La evaluación tiene un único tipo de revisor y el capítulo ya había servido para ajustar Site. Esta comparación permite medir regresiones en el material revisado. El conjunto independiente anterior conserva 20 aciertos de 24 y un límite inferior unilateral al 95 % de 67,6 %, por debajo del mínimo del 80 % para publicar automáticamente. Los bloques que ninguna versión eligió quedan fuera de la evaluación de calidad. [Calibración de Site](../documentacion/resultados-site-4.1.json)

## Telemetría, con mediciones compartidas

Tres procesos independientes de Blender 4.2.20 LTS midieron la misma escena ligera con tres repeticiones internas por operación. Tres sesiones de Chromium ejecutaron una escena A-Frame de un cubo con WebGL por software. Se descargó una sola copia del snapshot de Blender Open Data y una de Can I Use. El flujo anterior y la herramienta nueva procesaron las mismas entradas admitidas en cada caso. Los resultados de la prueba de telemetría quedaron en los artefactos del runner. [Datos de telemetría](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44666052441/artifacts/14596724519)

| Indicador | Recorrido anterior | Recolector nuevo |
|---|---:|---:|
| Fuentes reunidas por la tarea de telemetría | 2 | 4 |
| Fuentes distintas contando también el sensor web anterior, que corría por separado | 3 | 4 |
| Mediciones de la sonda de Blender | 9 aceptadas | Las mismas 9 aceptadas |
| Filas de la sonda Blender con el entorno de ejecución explícito | 0 / 9 | 9 / 9 |
| Mediciones públicas por escena de 50 benchmarks v4 | 150 en revisión | Las mismas 150 en revisión |
| Compatibilidad web | 4 296 celdas contenidas en seis fichas del sensor independiente | 4 296 filas consultables con los mismos códigos |
| Rendimiento observado de A-Frame | Sin sonda de escena en el recorrido | 3 ventanas de 301 intervalos cada una |

La comparación comprobó la igualdad de todas las propiedades de las 159 filas de Blender salvo la procedencia de ejecución incorporada en la sonda propia. También cotejó cada combinación de función, navegador, versión y código de Can I Use. Las tres ventanas de A-Frame sumaron 903 intervalos en unos 15 segundos, con un p95 por ventana entre 16,7 y 16,8 ms. Esto mide la escena en el runner. El informe del recolector identifica cuatro fuentes recibidas y las siete pendientes. Los datos permiten comprobar cobertura y trazabilidad. Para medir un cambio en el rendimiento de una práctica hace falta un ensayo sobre equipos representativos.

[Suite del repositorio, 213 pruebas y cinco subpruebas](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/44666052398) · [Implementación del recolector, PR #35](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/pull/35)
