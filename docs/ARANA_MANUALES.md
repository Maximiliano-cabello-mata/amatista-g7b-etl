# Araña de manuales Sphinx: cada página una vez (16 de noviembre de 2026)

Corrige dos problemas de `blender_docs` / `manual_sphinx`: **se recorría el manual completo una y otra vez**, y **la misma página llegaba más de una vez**. También deja medido qué parte del manual cubre cada trabajo.

## 1. Qué pasaba (medido)

| Síntoma | Causa | Evidencia |
|---|---|---|
| El manual entero se recorría de nuevo en cada revisión | El sensor `pagina` comparaba la huella de la portada `latest/`, y docs.blender.org reconstruye **todas** las páginas a diario: el pie dice «Last updated on 2026-11-16» incluso en 4.5. Para el sensor, el manual siempre «cambió» | Los trabajos `883618-1-13`, `-14` y `-15` traen las mismas 2.353 páginas. En la vuelta del 16 de noviembre, 4.684 rechazos por duplicado exacto salieron de `-14` y `-15` |
| Dos recorridos casi a la vez | Nada impedía lanzar un trabajo mientras otro seguía en Zyte. Una revisión forzada a mano, o dos seguidas, lanzaban dos | Varias ejecuciones de vigilar a mano el 11 de noviembre |
| La misma página llegaba dos veces dentro de un trabajo | No era la URL: el filtro de Scrapy (`RFPDupeFilter`) ya descarta URL repetidas, y en `-13` hay 2.353 URL únicas. Era Sphinx, que publica **la misma página en dos rutas** (por ejemplo `render/eevee/render_settings/grease_pencil.html` y `render/cycles/render_settings/grease_pencil.html`) | 86 páginas de `-13` tienen el mismo contenido que otra de la misma versión |
| Una versión sin nada (2.79) | No era el tope de páginas: **el `robots.txt` de docs.blender.org prohíbe `/*/2.79/` a todos los bots**, y la araña lo respeta (`ROBOTSTXT_OBEY`) | `Forbidden by robots.txt` al pedir `2.79/objects.inv` |
| No se sabía qué parte del manual se recorrió | La araña seguía enlaces y no tenía una lista de lo esperado | — |

## 2. Qué dice la documentación

- **Sphinx publica un inventario `objects.inv` junto a cada manual**, la lista que usa *intersphinx* para enlazar entre proyectos. Trae una entrada `std:doc` por página. En Blender: 5.2 tiene 2.358 páginas, 4.5 tiene 2.072 y 3.6 tiene 1.995. El formato v2 son cuatro líneas de encabezado y un cuerpo comprimido con zlib ([sintaxis de objects.inv v2, sphobjinv](https://sphobjinv.readthedocs.io/en/v2.4/syntax.html)). El de 4.5 tiene `Last-Modified: 1 nov 2025` y ETag: no cambia aunque las páginas se reconstruyan.
- **Scrapy** filtra peticiones repetidas por huella de la URL canónica con `RFPDupeFilter`, salvo `dont_filter=True` ([código de `scrapy.dupefilters`](https://docs.scrapy.org/en/2.16/_modules/scrapy/dupefilters.html)). Eso evita bajar dos veces la misma URL dentro de un trabajo, pero no evita la misma página publicada en dos URL ni que se repita entre trabajos.
- **Zyte DeltaFetch** (más DotScrapy Persistence) es la forma clásica de rastreo incremental en Scrapy Cloud. **No sirve aquí**: no salta las peticiones que salen de `start_requests`, y Zyte marcó el complemento como obsoleto ([DeltaFetch en Scrapy Cloud](https://support.zyte.com/support/solutions/articles/22000221912-incremental-crawls-with-scrapy-and-deltafetch-in-scrapy-cloud), [complemento Delta Fetch](https://support.zyte.com/support/solutions/articles/22000200411-delta-fetch-addon)). Además, en el plan gratuito los datos de Zyte duran 7 días. El estado del rastreo vive mejor en nuestro lago.
- **Cada página declara su URL canónica** (`<link rel="canonical">`), que apunta a `latest/`. Sirve para juntar la misma página de distintas versiones.
- **`robots.txt` de docs.blender.org:** `Content-Signal: search=yes, ai-train=no, use=reference` y `Disallow: /*/2.79/`. G7B usa el manual como referencia citada (CC BY-SA 4.0) y no para entrenar modelos.

## 3. Cómo funciona ahora

```
vigilar (cada 24 h)                         Zyte: blender_docs (solo si toca)
  sensor «sphinx»                             por versión pedida:
    objects.inv de 5.2, 4.5 y 3.6               objects.inv → páginas de las secciones
    con ETag (304 si no cambió)                 una petición por página, en orden
    ¿cambió la huella o pasaron 30 días?        sin seguir enlaces
        │ sí: versiones = [las que tocan]       misma página en otra ruta → registro corto
        ▼                                         con «duplicado_de»
  ¿hay un trabajo de blender_docs pendiente     al cerrar: esperadas / extraídas /
   o corriendo en Zyte? → no se lanza otro        repetidas / fallidas por versión
```

| Pieza | Archivo | Qué hace |
|---|---|---|
| Lector del inventario | `motor_extraccion/inventario_sphinx.py` | Lee `objects.inv` v2 (sin Scrapy, para usarlo en la araña y en el radar). Da la lista de páginas y una huella del cuerpo. Cada página se asigna a una sola sección, la más específica |
| Araña | `motor_extraccion/spiders/manual_sphinx.py` | Modo `inventario` por omisión, con reserva al modo `enlaces` si una versión no tiene inventario. `max_por_version` evita que una versión deje sin cupo a otra. Agrega `ruta` y `canonica` a cada registro. Si una página repite el texto de otra de la misma versión, sale como alias, sin repetir el texto |
| Sensor | `g7b_ingesta/sensores.py` (`sensor_sphinx`) | Revisa el inventario de cada versión con ETag y avisa qué versiones recorrer: la que cambió de inventario, y las demás cada `refresco_dias` (30), para recoger ediciones de texto |
| Candado | `g7b_ingesta/vigilar.py` (`en_curso`, `TrabajoEnCurso`) | Antes de lanzar, pregunta a Zyte si hay un trabajo de la misma araña pendiente o corriendo. Si lo hay, no lanza y no guarda el estado nuevo: la próxima revisión lo intenta de nuevo |
| Embudo | `g7b_ingesta/embudo.py` y `procesar.py` | El alias se rechaza como «la misma página ya se extrajo en otra ruta del manual», sin evaluar texto. Queda en plata con su motivo |
| Catálogo | `fuentes/catalogo.yml` (`blender-manual`) | `sensor: {tipo: sphinx, versiones: [5.2, 4.5, 3.6], refresco_dias: 30}`, `max_por_version: 1200`, revisión cada 24 h |

## 4. Verificación

- **Pruebas** (`pruebas/test_inventario_sphinx.py`, 11 nuevas) sobre:
  - lectura del inventario, `$` y huella estable;
  - una sola sección por página;
  - orden y cero enlaces seguidos;
  - tope por versión;
  - alias dentro de la versión pero no entre versiones;
  - reserva sin inventario;
  - sensor (primera vez, sin cambios con ETag, cambio en una versión, refresco a los 30 días, error);
  - candado de Zyte y versiones pasadas a la araña;
  - alias en el embudo.
- **Suite completa con Azurite:** 160 aprobadas.
- **En vivo contra docs.blender.org** (4.5, `render/cycles/render_settings/` y `render/eevee/render_settings/`): 22 de 22 páginas del inventario, 22 URL únicas, y un alias detectado: `eevee/.../grease_pencil.html`, que es la misma página que la de `cycles/...`. Con 2.79, la araña respeta `robots.txt`.

## 5. Qué esperar en el lago

- La primera revisión después de fusionar ve «primera vez» en las tres versiones y lanza **un** recorrido, con las mismas 10 secciones: unas 2.370 páginas (930 + 775 + 665). Después, nada, hasta que cambie un inventario o pasen 30 días.
- Los rechazos por «duplicado exacto» entre trabajos dejan de crecer cada semana.
- Sigue pendiente guardar la misma página de 4.5 y 3.6 como **variante de versión** del documento aceptado, en lugar de rechazarla como casi duplicada. `ruta` y `canonica` ya dan la clave para juntarlas.
- La huella de reglas de cada archivo de bronce ahora solo toma de la fuente lo que cambia el resultado del embudo: licencia, modo, dominios, preguntas, umbrales y tipo. Así, cambiar el sensor o los argumentos de la araña no vuelve a evaluar todo. El cambio de fórmula provoca **una** reevaluación completa la próxima vez (unos 45 segundos, con el mismo resultado).
