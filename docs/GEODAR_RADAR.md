# Geodar Radar

Fecha: 2026-11-02. **Geodar Radar** es la herramienta de G7B para **vigilar y extraer información de 3D en internet**: foros, documentación, publicaciones, catálogos de texturas y modelos, versiones de herramientas libres y telemetría pública. Es la pieza de captura del [plan maestro](PLAN_MAESTRO.md) (familias F1 a F7).

- **El mapa de sensores**, generado del catálogo: [GEODAR_RADAR_MAPA.md](GEODAR_RADAR_MAPA.md).
- **Qué hace cada etapa del embudo de texto:** [INGESTA.md](INGESTA.md).

## 1. Qué hace, en una imagen

```text
  fuentes/catalogo.yml  (QUÉ se vigila, DÓNDE, con qué LICENCIA y a qué DESTINO)
          │
          ▼
  SENSORES ─ cada uno revisa su fuente con el menor costo y solo avisa de lo nuevo
  │  atom/rss · pagina · sitemap · stackexchange · discourse · github_releases · json_api
  ▼
  EXTRACTORES ─ directo (el sensor ya trae el dato) · zyte (arañas) · descarga (PDF) · externo
  │
  ▼
  AZURE, bronce/<fuente>/<fecha>/   ← TODO entra aquí primero, crudo y con su procedencia
  │
  ├─ destino documentos ─► embudo de calidad ─► plata ─► MongoDB conocimiento_3d.documentos
  ├─ destino catalogo ───► MongoDB g7b_catalogo.<coleccion>   (texturas, hdri, modelos, herramientas…)
  ├─ destino senales ────► Azure oro/senales/semanal.json  (+ g7b_panel.senales para Atlas Charts)
  └─ destino telemetria ─► se queda en bronce para el cubo DuckDB del warehouse (Azure)
```

**La división que se acordó:**
- **MongoDB guarda documentos y catálogos:** texto y fichas que se consultan.
- **Azure guarda telemetría y señales:** números que van al cubo.
- **Todo pasa primero por Azure**, así nada se pierde y se puede reprocesar sin volver a descargar.

## 2. Dónde están los sensores

31 fuentes, agrupadas por familia. La lista completa, con su estado, está en el [mapa](GEODAR_RADAR_MAPA.md).

| Familia | Qué vigila | Dónde |
|---|---|---|
| **F5 Técnicas y conocimiento** | Preguntas y respuestas con votos, manuales, artículos y noticias | Blender Stack Exchange, Computer Graphics Stack Exchange, manual de Blender, arXiv cs.GR, blender.org, code.blender.org, blog de Godot, BlenderNation |
| **Señales de la comunidad** | Qué se pregunta y cuánto interesa: temas nuevos, vistas, «me gusta», respuestas y etiquetas | Foros Discourse: Blender Artists, devtalk.blender.org, foro de Godot, foro de three.js |
| **F4 Herramientas** | Extensiones de Blender y versiones de 18 herramientas libres, con su licencia | extensions.blender.org; GitHub: Godot, glTF-Blender-IO, three.js, A-Frame, meshoptimizer, Manifold, xatlas, OpenSubdiv, OIDN, OpenVDB, MaterialX, Draco, KTX, Basis Universal, Bullet, Open3D, FreeCAD, Armory |
| **F3 Texturas y materiales** | Texturas, HDRI y materiales CC0 con su resolución, categorías y descargas | Poly Haven (API), ambientCG (API) |
| **F7 Modelos 3D** | Modelos CC0 con su número de polígonos | Poly Haven (API) |
| **F1 Telemetría** | Render por dispositivo; soporte de WebGL, WebGL 2, WebGPU y WebXR en navegadores; mediciones propias | Blender Open Data, caniuse (CC BY 4.0), la sonda de G7B |
| **F2 y F6** | Costo por operación; aprendizaje en Amatista | Sonda de operaciones y Amatista (se encienden cuando existan) |

**Pendientes de licencia** (no se vigilan hasta confirmarla; `python -m geodar licencias` las lista):
- notas de versión y API de Blender;
- documentación de Godot;
- OpenBenchmarking;
- Web3D Survey;
- GPUinfo;
- encuesta de hardware de Steam.

### Fuentes que no se usan, y por qué

| Fuente | Motivo |
|---|---|
| Reddit (r/blender y otros) | Desde 2023 sus condiciones de API restringen el uso de su contenido sin acuerdo |
| ArtStation, 80.lv | Contenido con derechos reservados y condiciones que prohíben la extracción automatizada |
| Base de GPUs de TechPowerUp | Prohíbe la extracción automatizada |
| Sketchfab | Cada modelo tiene su licencia y la API pide una llave; queda para la tienda de modelos (F7, más adelante) |
| Polycount, Geekbench Browser | Por revisar sus condiciones antes de considerarlas |
| Código o herramientas filtradas o propietarias | Nunca (regla del proyecto) |

## 3. Las reglas que Geodar cumple siempre

1. **Sin licencia confirmada, no entra:** `licencia_verificada: true` es obligatorio para vigilar.
2. **Con derechos reservados,** solo título, enlace, fecha, etiquetas y cifras (`solo_metadatos`). Nunca el texto de otros.
3. **Respeta `robots.txt`** en cada página. Las APIs oficiales y documentadas (GitHub, Stack Exchange, Poly Haven) se rigen por sus propias condiciones: identificación, cuota y llave.
4. **Se identifica:** `G7B-bot/0.1 (Geodar Radar; +enlace al repo)`. Poly Haven lo exige.
5. **Pide poco:** peticiones condicionales (ETag), solo lo nuevo o lo cambiado, y una frecuencia por fuente.
6. **Una fuente rota no detiene a las demás.** Su error queda en `control/sensores.json` y lo reporta `salud`.
7. **Sin datos personales:** de los foros solo se guarda el nombre público del autor cuando la licencia (CC BY-SA) exige atribuirlo.

## 4. Cómo se usa

```bash
python -m geodar mapa                          # la lista de sensores en la terminal
python -m geodar mapa --markdown docs/GEODAR_RADAR_MAPA.md   # regenerar el mapa
python -m geodar probar --fuente blender-artists             # en vivo y SIN escribir nada
python -m geodar probar --todas                # todas, incluidas las inactivas
python -m geodar licencias                     # lo pendiente de confirmar
python -m geodar vigilar --simulacro           # la vigilancia real, sin escribir
python -m geodar vigilar                       # la vigilancia real → bronce
python -m geodar procesar | publicar           # documentos → MongoDB
python -m geodar catalogar                     # catálogos → MongoDB g7b_catalogo
python -m geodar senales                       # foros → oro/senales/ (+ panel)
python -m geodar salud                         # ¿algo falla o se atrasó? (sale con 1 si sí)
```

En GitHub, todo corre solo con el interruptor `G7B_INGESTA_ACTIVA=true`:

| Tarea | Cuándo | Qué hace |
|---|---|---|
| **Vigilar fuentes (Geodar Radar)** | Cada 6 h | `geodar vigilar` + `geodar salud --guardar` |
| **Zyte al lago** | Cada noche | Lo que trajeron las arañas → bronce |
| **Procesar bronce** | Cada noche | `procesar` → `publicar` → `catalogar` → `senales` |
| **Geodar Radar (probar y revisar)** | A mano | `probar` en vivo, `mapa` con estado o `salud`; el resultado queda en la pestaña *Summary* |

**Antes de encender el interruptor:**
1. Actions › **Geodar Radar (probar y revisar)** › *Run workflow* › `probar` (vacío = todas).
2. La tabla del *Summary* dice qué fuentes responden.
3. Si alguna falla porque cambió su API o su `robots.txt` no lo permite, se corrige o se apaga en el catálogo (`activa: false`).

## 5. Agregar una fuente

1. Agregar el bloque a `fuentes/catalogo.yml`. Necesita: `id`, `nombre`, `familia`, `destino` (y `coleccion` si es catálogo), `licencia` y `licencia_verificada`, `modo`, `sensor`, `extractor`, `frecuencia_horas`, `dominios` y `activa`.
2. `python -m geodar probar --fuente <id>` (o la tarea de Actions).
3. `python -m pytest pruebas -q`: el catálogo se valida en las pruebas.
4. `python -m geodar mapa --markdown docs/GEODAR_RADAR_MAPA.md`.

Si la fuente es una API JSON nueva, casi siempre basta el sensor `json_api` con `items`, `id`, `titulo`, `campos` y `url_item`. No hace falta programar.

## 6. Lo que viene

- **El cubo** (PR #4 a #8, `g7b_almacen`) leerá `bronce/caniuse-web3d/` y `oro/senales/` junto con Open Data y la sonda.
- **El panel** (Atlas Charts) suma el tablero **Señales** desde `g7b_panel.senales`.
- **La API de G7B** (Heroku) servirá `g7b_catalogo` a Amatista: texturas por nivel, herramientas y extensiones por versión.
- **Más fuentes**, cuando se confirmen sus licencias.
