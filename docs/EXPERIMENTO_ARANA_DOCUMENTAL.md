# Experimento de recorrido documental en G7B

`paginas_laboratorio` es una tercera araña de Scrapy para comparar formas de recorrer sitios documentales. Deriva de `paginas` y reutiliza el extractor de fragmentos del manual. Zyte Scrapy Cloud ejecuta el código como un trabajo. El catálogo y los disparadores existentes siguen utilizando sus arañas configuradas. La telemetría queda fuera de esta prueba.

## Qué información produce

Con `modo=texto_completo`, cada ítem conserva la salida original de `paginas` y añade `fragmentos` con encabezado, enlace citable, bloques de texto, tablas, código y huella de contenido estructurado. Con `modo=solo_metadatos`, el ítem solo contiene los metadatos habituales. `programa` y `version` son opcionales y deben proceder de la fuente. Una versión desconocida queda vacía. Las capturas con texto similar conservan su procedencia individual. Para los manuales Sphinx con inventario conocido, la referencia sigue siendo `manual_sphinx`.

## Cómo elige un enlace

La frontera mantiene URLs pendientes distintas. Para cada enlace conoce el texto del ancla $A$, la ruta $P$ y el encabezado precedente $H$ de nivel 1 a 3. El conjunto de términos objetivo es $T$. Se pasan a minúsculas y se eliminan diacríticos antes de formar conjuntos de palabras. Todos los datos usados al puntuar están disponibles en la página de origen.

$$
J(X,T)=\frac{|X\cap T|}{|X\cup T|},\qquad J(\varnothing,\varnothing)=0
$$

$$
s(u)=0.85^{\max(0,d-1)}\big[0.60J(A,T)+0.25J(P,T)+0.15J(H,T)\big]
$$

$d$ es el número de enlaces desde la semilla por el camino observado. Las señales y la puntuación pertenecen a $[0,1]$. Si la misma URL se descubre dos veces antes de visitarla, conserva la mayor puntuación observada y la menor distancia para desempate y límite de profundidad. Los pesos son una hipótesis del experimento. La similitud se calcula por coincidencia de palabras y pierde sinónimos y equivalencias entre idiomas.

| Estrategia | Próxima URL |
|---|---|
| `amplitud` | Menor profundidad y luego orden de descubrimiento. Control con el mismo presupuesto y extractor. |
| `foco` | Mayor puntuación, menor profundidad y luego orden de descubrimiento. |
| `foco_puentes` | Cada tercera elección posterior a las semillas reserva un turno para un índice pendiente, si lo hay. Escoge el menos profundo y más antiguo. El resto de turnos sigue `foco`. |

La señal de índice se activa por palabras como *índice*, *catalog* o *reference* en el ancla o en el último componente de la ruta. Un índice puede abrir acceso a material relevante aunque por sí solo aporte poco texto. Los empates son reproducibles. La cola se examina en memoria en cada despacho, con coste lineal en el número de URLs pendientes. El diseño prioriza la comparación entre estrategias en trabajos pequeños.

## Presupuesto y observación

`max_paginas` limita los intentos de páginas de la nueva araña. Cada semilla, respuesta fallida o salto de redirección despachado gasta un intento. Hay una petición documental activa a la vez. Una redirección HTTP se valida contra el dominio, origen y prefijo configurados antes de ofrecer el destino. La araña conserva las consultas, idioma y versión, elimina el ancla para deduplicar solicitudes y aplica `profundidad` a los enlaces del grafo. `seguir=0` desactiva la exploración de enlaces. Hereda la política de robots y la regulación de velocidad del proyecto. Los reintentos automáticos de las peticiones documentales están desactivados para controlar el coste.

En estadísticas de Scrapy, `g7b/lab/intentos` cuenta despachos de la frontera, `g7b/lab/html` respuestas HTML de éxito y `g7b/lab/fragmentos` fragmentos emitidos. También hay contadores para fallos, redirecciones y descartes por estado o tipo. Un rechazo de robots puede consumir un despacho sin que llegue una petición de página al servidor. Para coste HTTP, consultar también `downloader/request_count`. En el banco, el servidor cuenta directamente **todos** los GET, incluido robots.txt.

## Prueba técnica reproducible

Desde la raíz del repositorio, con las dependencias de desarrollo instaladas:

```bash
python -m experimentos.arana_documental --solo-orden
python -m experimentos.arana_documental
python -m pytest pruebas/test_arana_paginas_laboratorio.py -q
```

El primer comando reproduce la frontera con la biblioteca estándar. El segundo arranca un servidor HTTP en loopback y ejecuta el comando real `scrapy crawl` ocho veces. Usa dos sitios sintéticos con los mismos tres hechos anotados, semilla, temas, cupo nominal de seis páginas y extractor. Solo cambia la disposición y rotulación de los enlaces. Una tabla cuenta como recuperada cuando coinciden la página, el ancla, los encabezados y la pareja propiedad–valor, en orden. La araña productiva `paginas` participa como cuarto control y se evalúa aplicando el mismo extractor a su HTML. Su tope opera sobre respuestas procesadas, por lo que se informa su número efectivo de solicitudes.

Sean $U$ las relaciones distintas recuperadas y verificadas, $Q$ las solicitudes HTTP que recibió el servidor y $T=3$ las relaciones anotadas. Cada relación ocupa un fragmento en este banco.

$$
Y_{100}=100\frac{U}{Q},\qquad F=\frac{U}{T}
$$

$F$ mide recuperación documental de extremo a extremo. En una auditoría real también conviene medir fidelidad condicionada a páginas visitadas para distinguir errores de navegación de errores del extractor. Un sitio abierto sin inventario completo solo admite cobertura sobre una muestra anotada o un inventario declarado.

| Hechos alcanzables en las seis selecciones del control de orden | Amplitud | Foco | Foco con puentes |
|---|---:|---:|---:|
| Enlaces descriptivos | 1/3 | 2/3 | 3/3 |
| Enlaces ambiguos | 3/3 | 2/3 | 1/3 |

El segundo comando imprime los resultados HTTP, las rutas efectivas, $U$, $Q$, $F$ y $Y_{100}$ para los cuatro recorridos. Las pruebas de integración comparan los tres modos experimentales con el orden previsto y verifican la estructura de sus tablas. Una última prueba de campo debe usar capturas fijas de fuentes reales, alguna fuente reservada para evaluación y resultados por sitio, versión y tipo de contenido antes de elegir nuevos pesos o promover una estrategia.

## Ejecución manual en Scrapy o Zyte

Ejemplo para una sección pequeña con versión explícita, desde una terminal Bash:

```bash
scrapy crawl paginas_laboratorio -a fuente=blender-manual -a programa=Blender -a version=4.5 \
  -a urls='["https://docs.blender.org/manual/en/4.5/render/cycles/index.html"]' \
  -a prefijo=https://docs.blender.org/manual/en/4.5/render/cycles/ \
  -a temas='["render","sampling","memory","noise"]' -a estrategia=foco_puentes \
  -a max_paginas=12 -a profundidad=3 -O piloto.jsonl
```

En un proyecto de prueba de Scrapy Cloud con esta revisión desplegada, se selecciona `paginas_laboratorio` y se introducen los mismos argumentos como pares nombre/valor, sin `-a`. El banco local funciona sin cuenta Zyte, Azure ni MongoDB. Para comparar un dominio real, conservar los registros de cada trabajo, la lista de semillas y el gasto efectivo.

**Referencias.** [Chakrabarti, van den Berg y Dom, focused crawling](https://www.cse.iitb.ac.in/~soumen/doc/www1999f/html/) · [Spiders y callbacks de Scrapy](https://docs.scrapy.org/en/latest/topics/spiders.html) · [Trabajos de Zyte Scrapy Cloud](https://docs.zyte.com/scrapy-cloud/usage/reference/http/jobs.html).
