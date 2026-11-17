# El núcleo público de Geoda (`geoda.nucleo/1`)

El núcleo es la parte de Geoda que se va a publicar. Recibe dos cosas, el equipo (una huella técnica sin datos personales) y la tarea, y devuelve un plan. Ese plan dice qué versión de Blender usar, qué ajustes cambiar, por qué, con qué evidencia y en qué página del manual se explica cada ajuste.

Todo lo que sabe el núcleo viene de **un solo archivo**: el paquete de conocimiento. No lee el cubo, ni el lago, ni internet. Así se garantizan tres cosas:

- **Es determinista:** con el mismo paquete y la misma entrada, da el mismo plan.
- **Funciona sin red:** dentro de Amatista, en una computadora de la escuela o en el navegador.
- **Se puede reimplementar:** una versión portable (Rust o C++ compilados a WebAssembly) solo tiene que leer el mismo paquete y pasar los mismos casos de conformidad.

```
arañas y radar ─▶ lago (bronce/plata) ─▶ cubo g7b.cubo/3 ─▶ paquete g7b.geoda.paquete/1 ─▶ núcleo geoda.nucleo/1 ─▶ plan g7b.plan/1
                                         directas │ relativas        (solo agregados)             (sin red)
```

## Lenguaje: Python ahora, núcleo portable después

**Decisión (17 de noviembre de 2026):** Python como implementación de referencia, con una especificación y casos de conformidad, y un núcleo portable más adelante.

Por qué no se empieza en C++:

- **El trabajo del kernel no es cálculo pesado.** Consiste en clasificar un equipo, elegir un perfil y armar unas diez acciones: microsegundos en cualquier lenguaje. Lo pesado (las 63.000 mediciones) ya lo hace DuckDB al construir el cubo, y DuckDB ya está escrito en C++.
- **El riesgo está en otra parte.** Está en que las reglas sean correctas y en que lo relativo no se presente como medido, y eso se cuida mejor con contratos y pruebas que con velocidad.
- **El paquete y los casos de conformidad son el verdadero contrato.** Cuando haga falta correr el núcleo dentro del navegador de Amatista, o en un equipo sin Python, se escribe en Rust o C++, se compila a WebAssembly y se valida con `geoda/conformidad.json`. Las reglas no se tienen que traducir a mano.

## El paquete de conocimiento (`g7b.geoda.paquete/1`)

Lo construye `geoda/paquete.py` a partir del cubo vigente:

| Sección | Qué lleva | De dónde sale |
|---|---|---|
| `perfiles` | El perfil por nivel (N0–N4): versión de Blender, motor y ajustes | Solo de mediciones **directas** (estudiantes y laboratorios con consentimiento). Un perfil medido con menos de 5 equipos no se publica: en su lugar queda la regla base. |
| `factores` | Cuánto rinde cada nivel frente al N2, por serie de Blender y escena | De mediciones **relativas** de **velocidad** (Blender Open Data): GPU integradas **modernas** y dedicadas con confianza alta o media, sin Apple Silicon ni GPU de servidor, y con al menos 30 mediciones por celda. La referencia es el N2 con integradas modernas. Cada factor va marcado `clase_dato: relativa`. |
| `render_cpu` | El render de Cycles en CPU por grupo de procesador y escena, frente al N2 moderno | Open Data con Blender 4.0 o más nuevo y al menos 3 mediciones por grupo. Es para los equipos con **integradas básicas**, que renderizan con el procesador. Con datos reales hay 111 grupos. |
| `citas` | La página del manual de cada ajuste, para cada versión (5.2, 4.5 y 3.6) e idioma (es, en) | `fuentes/citas_manual.yml`, comprobada contra el `objects.inv` de cada versión. Cada enlace dice `verificada: inventario`, `conocimiento_g7b` o `sin_verificar`. Solo se guardan enlaces y títulos: el texto del manual no se copia. |
| `hardware` | El estándar `g7b.hardware/1` | `fuentes/hardware.yml` |
| `niveles` | Las reglas N0–N4 | `geoda/niveles.py` |
| `operaciones` | El catálogo de operaciones | `geoda/costos.py` |

Cada sección lleva su huella SHA-256. La versión del paquete se forma con la fecha y la huella del contenido (por ejemplo, `20261117T085540Z-420dc251c058`). `geoda.paquete.validar()` rechaza un paquete en estos casos:

- una sección alterada;
- un nivel sin perfil;
- un factor que no esté marcado como relativo;
- un paquete que contenga algo que identifique equipos (`huella_equipo`, `hostname`, etc.).

**Primer paquete con datos reales** (17 de noviembre, desde el cubo con 63.019 mediciones):

- 0 perfiles medidos: todavía no hay mediciones directas, así que todos los niveles usan la regla base;
- 18 factores relativos;
- 84 de 84 citas verificadas;
- 36 KB.

Ejemplo: en Blender 5.2 y la escena classroom, un N2 integrado hace unas 123 muestras por minuto. Un N3 rinde 5,9 veces eso, y un N4, 13,4 veces.

## La API del núcleo

```python
from geoda.nucleo import Nucleo

nucleo = Nucleo.desde_archivo("publicacion/geoda_paquete.json")
huella = nucleo.huella(gpu="Intel(R) UHD Graphics 620", ram_gb=8, opengl=4.6, so="windows")
plan = nucleo.decidir(huella, {"tipo": "practica", "blender": "4.5"}, idioma="es")
```

| Llamada | Devuelve |
|---|---|
| `Nucleo(paquete)` / `Nucleo.desde_archivo(ruta)` | El núcleo; antes valida el paquete |
| `info()` | La API, la versión de Geoda, la versión del paquete y su evidencia |
| `gpu(nombre)` | La clase y la VRAM de una GPU, según la tabla del paquete |
| `huella(gpu, ram_gb, so, opengl, vulkan, movil, cpu)` | Una `g7b.huella/1` armada con datos sueltos |
| `clasificar(huella)` | El nivel, la confianza y los motivos |
| `decidir(huella, tarea, idioma)` | El plan `g7b.plan/1`, con los añadidos que siguen |

Lo que `decidir` agrega al plan del planificador:

- **`acciones[].citas`:** la página del manual de cada ajuste, en la versión que recomienda el plan y en el idioma pedido (si no existe en ese idioma, en inglés).
- **`evidencia.escalera`:** de dónde sale la recomendación:
  - `medido`: perfil confiable de mediciones directas;
  - `provisional`: mediciones directas, todavía pocas;
  - `regla_base`: la regla de las fichas técnicas.
- **`evidencia.graficos`:** `integrada_basica` cuando el equipo solo tiene gráficos integrados básicos. En ese caso la estimación relativa sale de `render_cpu`, según el grupo de su procesador, y el plan advierte que Cycles usará el procesador.
- **`evidencia.estimacion_relativa`:** la comparación con datos públicos para el nivel del equipo, siempre con `clase_dato: relativa` y con un texto que dice que **no es una medición de tu equipo**. Para el nivel N0 no se calcula.
- **`ayuda`:** páginas generales para los niveles bajos (solución de problemas de la GPU, preferencias de la vista 3D).
- **`kernel`:** la API, la versión de Geoda y la versión del paquete con que se decidió.

Desde la terminal:

```bash
python -m geoda paquete --cubo oro/cubo.duckdb --manifiesto manifiesto.json --verificar-manual --salida paquete.json
```

```bash
python -m geoda plan --paquete paquete.json --huella equipo.json --blender 4.5 --idioma es
```

```bash
python -m geoda conformidad --paquete paquete.json
```

## Casos de conformidad

`geoda/conformidad.json` tiene 15 casos que **cualquier** implementación debe pasar **con cualquier paquete válido**:

- un celular va al editor web;
- con poca RAM u OpenGL viejo, Blender 3.6;
- integrada, dedicada media y dedicada grande;
- una dedicada sin VRAM conocida no da confianza alta;
- Apple Silicon cuenta como integrada;
- una integrada básica (UHD con i3) no se compara con render en GPU ni recibe Cycles en GPU, y lleva advertencia;
- una integrada moderna (Radeon 780M) no se trata como básica;
- una Intel Arc Pro es dedicada;
- una GPU desconocida no inventa;
- las citas siguen la versión que recomienda el plan;
- las citas salen en el idioma pedido;
- se rechazan los datos personales.

Además, en todos los casos se comprueba que lo relativo nunca se presente como medido. Lo que depende de los datos, como el factor exacto, no se fija en los casos.

## Cómo se publica

Lo hace `.github/workflows/geoda_kernel.yml`, que el ciclo lanza en la vuelta semanal después del cubo:

1. Descarga el cubo **vigente del lago** (`control/cubo_actual.json`) y verifica sus huellas y conteos. Ya no depende del artefacto de Actions, que caducaba a los 14 días.
2. Construye el paquete y comprueba las citas contra los `objects.inv` del manual.
3. Corre los casos de conformidad contra el paquete nuevo. Si alguno falla, no se publica nada.
4. Publica solo si el contenido cambió:
   - en el lago, `oro/geoda/<versión>/paquete.json` (no se sobrescribe) y el puntero `control/geoda_paquete_actual.json`;
   - en el repositorio, `publicacion/geoda_paquete.json`.

El paquete solo lleva agregados: ni huellas, ni mediciones individuales, ni datos de equipos.

## La API HTTP (siguiente etapa)

El núcleo se va a alojar como la API del kernel de G7B/Geoda en el servidor de Oracle donde viven las APIs de Amatista. Como el núcleo es una función pura, la API es una capa delgada:

| Método | Ruta | Cuerpo / respuesta |
|---|---|---|
| `GET` | `/api/geoda/v1/info` | `Nucleo.info()` |
| `POST` | `/api/geoda/v1/plan` | `{"huella": {…g7b.huella/1…}, "tarea": {"tipo": "practica", "blender": "4.5"}, "idioma": "es"}` → `g7b.plan/1` |
| `POST` | `/api/geoda/v1/nivel` | `{"huella": {…}}` → nivel, confianza y motivos |
| `GET` | `/api/geoda/v1/gpu?nombre=…` | `Nucleo.gpu(nombre)` |
| `GET` | `/api/geoda/v1/paquete` | el paquete vigente (para clientes que deciden sin red) |

Reglas para esa etapa:

- **El servidor no guarda las huellas que recibe.** Solo cuenta planes por nivel y estado.
- **El paquete se actualiza** leyendo el puntero del lago (o `publicacion/geoda_paquete.json`), sin reiniciar el servicio.
- **La integración completa con Amatista** (el cliente que aplica y deshace las acciones en Blender) va después.

## Pendiente antes de anunciarlo como público

- **Licencias:** el código y los datos del paquete están marcados `por_definir`. Hay que elegir las dos (por ejemplo, una licencia abierta para el código y CC BY 4.0 o CC0 para el paquete) y agregar un `LICENSE`. Las atribuciones de Blender Open Data (CC0) y del manual de Blender (CC BY-SA, solo enlaces) ya van en el paquete.
- **Mediciones directas:** mientras no existan, todos los planes dicen `regla_base`. Las primeras sondas en laboratorios escolares, con consentimiento, son las que convierten la regla en medición.
