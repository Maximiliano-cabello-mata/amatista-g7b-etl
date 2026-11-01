# Ingesta: sensores, disparadores y el embudo de calidad

Cómo llega un dato de internet al warehouse, y por qué casi nada llega. Aplica las reglas de calidad del [plan](PLAN.md#2-qué-es-un-dato-de-calidad-aquí).

```text
 fuentes/catalogo.yml ──► SENSORES ──► DISPARADORES ──► BRONCE ──► EMBUDO (5 etapas) ──► PLATA ──► ORO / warehouse
 (qué, licencia,          ¿hay algo     directo: feed/API          crudo,     entrada               aceptados   (F2: fragmentos,
  preguntas, cada         nuevo?        zyte: araña "paginas"      sin tocar  calidad               revisión    vectores, tablas)
  cuánto)                 ETag, huella, descarga: PDF                         duplicados            rechazados
                          ids vistos                                          relevancia            (con motivo)
                                                                              valor
      cada 6 h: Vigilar fuentes        cada noche: Zyte al lago        cada noche: Procesar bronce
```

## 1. Catálogo de fuentes (`fuentes/catalogo.yml`)

Cada fuente declara qué es y cómo se trata:

| Campo | Para qué |
|---|---|
| `licencia`, `licencia_verificada` | **Una fuente solo se vigila si su licencia está confirmada.** `por_confirmar` bloquea todo |
| `modo` | `texto_completo` (licencia abierta), `solo_metadatos` (derechos reservados: título, enlace y un fragmento corto) o `agregados` (solo cifras) |
| `preguntas` | Qué preguntas del plan (P1 a P7) debería responder. Si responde otras, va a revisión |
| `sensor` | Cómo se detecta lo nuevo (sección 2) |
| `extractor` | Qué se lanza cuando hay algo nuevo (sección 3) |
| `frecuencia_horas` | Cada cuánto se revisa. La documentación, semanal; los foros y artículos, diario |
| `dominios` | Los únicos dominios de los que se acepta contenido |
| `umbrales` | Opcional: ajusta el embudo para esa fuente (por ejemplo, en un resumen académico el valor es la técnica, no las medidas) |

El catálogo se valida en cada prueba. Por ejemplo, no se permite `texto_completo` con `derechos_reservados`, ni `licencia_verificada: true` con una licencia por confirmar.

**Fuentes vigiladas hoy:**
- **arXiv cs.GR:** solo metadatos y resúmenes, que arXiv publica como CC0.
- **Blender Stack Exchange:** CC BY-SA, con atribución al autor.
- **Manual de Blender:** CC BY-SA.

**Definidas pero apagadas hasta confirmar su licencia o sus condiciones:**
- Notas de versión y API de Python de Blender.
- Documentación de Godot.
- Blender Open Data.
- SIGGRAPH "Advances".
- Encuesta de hardware de Steam.

**Para agregar una fuente:**
1. Agrega su entrada al catálogo, con la licencia confirmada en su sitio.
2. Corre las pruebas.
3. Corre **Vigilar fuentes** con `fuente` = su id y "simulacro" marcado.

## 2. Sensores (`g7b_ingesta/sensores.py`)

Un sensor responde "¿hay algo nuevo?" gastando lo menos posible: no descarga lo que no cambió.

| Sensor | Cómo detecta lo nuevo | Para |
|---|---|---|
| `atom`, `rss` | IDs de entradas no vistas; petición condicional (ETag, Last-Modified) | arXiv, blogs con feed |
| `pagina` | Petición condicional y huella (hash) del contenido | Portadas de manuales y sitios sin feed |
| `sitemap` | URLs nuevas o con `lastmod` más reciente | Sitios grandes con sitemap |
| `stackexchange` | Preguntas creadas **hace 7 a 30 días** con un puntaje mínimo de votos, más su respuesta aceptada o la más votada | Foros de Stack Exchange |

En Stack Exchange se espera una semana para que los votos se asienten: un filtro de votos sobre preguntas de ayer no sirve. Sin clave, la API permite unas 300 peticiones al día; con el secreto opcional `STACKEXCHANGE_KEY`, muchas más.

Todas las peticiones se identifican como `G7B-bot`, respetan `robots.txt` y tienen tiempo límite.

## 3. Disparadores (`g7b_ingesta/vigilar.py`)

La tarea **Vigilar fuentes** corre cada 6 horas. A cada fuente vigilable a la que le toca según su frecuencia:
1. Le corre su sensor.
2. Si hay algo nuevo, lanza su extractor:
   - **`directo`:** lo que trajo el sensor (feed o API) va directo a `bronce/<fuente>/<fecha>/`.
   - **`zyte`:** lanza en Zyte la araña genérica `paginas` (`motor_extraccion/spiders/paginas.py`) con las URLs. Puede recorrer todo un prefijo, como el manual completo, con un tope de páginas. Sus resultados llegan a bronce con **Zyte al lago**. Esta araña no escribe en MongoDB: el crudo va al lago.
   - **`descarga`:** descarga cada archivo (PDF, hasta 50 MB) a bronce, junto con un índice de lo descargado.
3. Guarda el estado de cada sensor (ETag, huellas, IDs vistos) en `control/sensores.json`, y la bitácora de la corrida en `control/vigilancia/`.

Si una fuente falla, las demás siguen, y la tarea termina en rojo para que se note.

## 4. El embudo (`g7b_ingesta/embudo.py`)

La tarea **Procesar bronce** corre cada noche. Cada registro nuevo de bronce pasa por cinco etapas, en orden. En cuanto una falla, el registro sale **rechazado con su motivo**.

| Etapa | Rechaza si... | Ejemplos |
|---|---|---|
| **1. Entrada** | La fuente no es vigilable; el dominio no es de la fuente; en `solo_metadatos`, el texto es largo | Un enlace que salió del manual a otro sitio |
| **2. Calidad** | Menos de 40 palabras (15 en resúmenes); poca prosa (código suelto, tablas, basura); más de 30 % de líneas repetidas (menús); un idioma distinto de español o inglés | Una página de navegación; un "gracias, me sirvió" |
| **3. Duplicados** | Ya pasó un documento idéntico, o casi idéntico (SimHash, a 3 bits o menos de distancia) | La misma respuesta copiada en otro hilo |
| **4. Relevancia** | No alcanza el mínimo en ninguna pregunta del plan, según `fuentes/taxonomia.yml` | Una receta de pan; una noticia de la empresa |
| **5. Valor** | Es genérico: no tiene medidas, versiones, hardware, código ni ajustes concretos, o tiene señales de clickbait | "Optimizar es importante para tener buen rendimiento" |

**Va a revisión** (no se pierde, pero espera a una persona) lo que tiene valor en el límite, lo que solo menciona versiones de Blender anteriores a 2.80 (cuando la interfaz era otra) y lo que responde preguntas distintas a las esperadas de su fuente.

**Suma valor:**
- Medidas con unidades (fps, ms, GB, %).
- Versiones ("Blender 4.2").
- Modelos de hardware (UHD 620, RTX 3060, Ryzen).
- Código (`bpy.`).
- Ajustes concretos (Simplify, samples, Workbench).
- Comparaciones.
- En foros, los votos (hasta 2 puntos) y la respuesta aceptada (1 punto).

**Salidas:**
- **`plata/aceptados/` y `plata/revision/`:** el documento con su licencia, su atribución y el resultado del embudo (preguntas, puntajes, señales).
- **`plata/rechazados/`:** solo la URL, la etapa, el motivo y los puntajes, **sin el texto**.
- **`control/embudo.json`:** conteos por fuente y etapa. Es la base del tablero de salud (plan, sección 8).

## 5. La revisión humana (cada semana)

Regla del plan: 20 registros al azar de lo aceptado. Si más de 3 son basura, **la fuente se pausa** (`activa: false`) hasta corregir sus umbrales o su araña. Lo que está en revisión se acepta o se rechaza a mano.

## 6. Lo que falta y los límites honestos

- **La relevancia es por palabras clave.** Es simple, pero se puede explicar y corregir. En F2, cuando existan los vectores, se agrega un clasificador por similitud con ejemplos de cada pregunta, sin quitar las palabras clave.
- **Los umbrales son iniciales.** Se ajustan con la revisión humana y con los conteos de `control/embudo.json`.
- **El historial de Stack Exchange** (preguntas antiguas muy votadas) no llega por la API, porque el sensor solo mira el último mes. Llegará por los volcados públicos del sitio, como fuente aparte.
- **PDF de artículos:** el extractor `descarga` y la lectura de PDF existen y están probados en código. Ninguna fuente activa los usa todavía, porque en arXiv solo se guardan metadatos.
- **Probado** con datos de ejemplo y contra Azurite (26 pruebas). **No probado** contra los sitios reales: la primera corrida de **Vigilar fuentes** se hace con "simulacro" marcado.
