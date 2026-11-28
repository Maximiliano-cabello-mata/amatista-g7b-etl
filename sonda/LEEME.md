# Sonda de rendimiento (`g7b-sonda`)

Mide qué tan bien trabaja Blender en una computadora, con la misma escena y los mismos ajustes en todas. Así los resultados se pueden comparar entre equipos. Corre **dentro de Blender**: no instala nada y no descarga nada, porque la escena se genera ahí mismo. El resultado es un archivo JSON con el contrato `g7b.medicion/1`.

## Correrla en tu computadora

1. Instala Blender, de preferencia la LTS vigente (5.2 LTS). Para comparar versiones, puedes instalar varias.
2. Descarga este repositorio.
3. Corre la sonda:

**Windows** (si Blender no está en `C:\Program Files\Blender Foundation\Blender 5.2\`, primero `set BLENDER=C:\ruta\a\blender.exe`):

```bat
sonda\medir.bat
```

```bat
sonda\medir.bat ventana
```

**Linux o macOS:**

```bash
./sonda/medir.sh
```

```bash
./sonda/medir.sh ventana
```

Sin ventana mide edición, animación y render (unos 2 minutos en una PC modesta). Con `ventana` abre Blender, mide también la vista 3D y se cierra solo. El resultado queda en `resultados/` (Git lo ignora: no se sube por accidente).

### Pruebas sugeridas para tu PC

- Una corrida sin ventana y otra con ventana.
- La misma corrida dos veces seguidas: si una métrica cambia más de 10 %, esa medición todavía no es confiable (regla del plan).
- `--escena pesada` para ver hasta dónde llega tu equipo.
- La misma corrida en otra versión de Blender (por ejemplo 4.5 LTS o 3.6 LTS), cambiando `BLENDER`.

Opciones (van después de `--` si llamas a Blender directo): `--escena ligera|media|pesada`, `--perfiles minimo,ligero,completo`, `--repeticiones N`, `--nivel N0..N4`, `--sin-render`, `--rapida`.

## Qué mide

| Prueba | Métrica | Qué dice |
|---|---|---|
| `edicion` | Segundos | Operaciones de modelado sobre una malla: subdividir, biselar y recalcular normales |
| `modificadores` | Segundos | Primera evaluación de la escena, incluida la preparación de la subdivisión. Es lo que tarda en reaccionar al abrirla |
| `animacion` | Cuadros por segundo | Recalcular la animación cuadro por cuadro, sin dibujar |
| `vista3d` | Cuadros por segundo | Redibujar la vista 3D (solo con ventana) |
| `render_workbench`, `render_eevee` | Segundos | Render de un cuadro con los motores que usan la GPU para dibujar |
| `render_cycles_cpu`, `render_cycles_gpu` | Segundos | Render de un cuadro con Cycles en CPU y, si hay GPU compatible, en GPU |

Cada prueba se corre con tres perfiles de ajustes (`minimo`, `ligero`, `completo`): subdivisión, Simplify, muestras y resolución. Son los ajustes que después aplicaría el Corazón según el equipo. Cada medición se repite (3 veces por omisión) después de una corrida de calentamiento que se descarta, y se guarda la mediana y la variación.

Si una prueba no se puede hacer en ese equipo (por ejemplo, la vista 3D sin ventana, o Cycles en GPU sin una GPU compatible), queda como `no_disponible` con el motivo; no se inventa un valor. El JSON se guarda después de cada prueba: si Blender se cierra a medias, lo medido no se pierde (`"completa": false`).

## Privacidad

Se guarda: sistema operativo, modelo de CPU y núcleos, RAM redondeada, GPU que ve Blender, versión de Blender y las mediciones. **No** se guarda: nombre de usuario, nombre del equipo, rutas ni archivos. La `huella` es un resumen (hash) del hardware que identifica al tipo de equipo, no a la persona.

## En la nube

- **Google Colab (con GPU):** descarga el Blender oficial para Linux, que trae su propio Python, y córrelo sin ventana. Así se mide Cycles en las GPU de Colab, el equipo de gama alta que no tienes. Una corrida tarda minutos, así que gasta pocas unidades.
- **Azure y GitHub Actions:** sin GPU. Sirven de control para medir la CPU de forma repetible.

En servidores Linux sin GPU, Workbench y EEVEE quedan como `no_disponible` (falta `libEGL`). Es lo esperado.

## Probado

En un servidor Linux sin GPU (4 núcleos Xeon, 16 GB) con Blender 5.2.3 LTS como módulo de Python, sin ventana, dos corridas seguidas: edición, animación y Cycles en CPU difieren menos de 4 % entre corridas; la primera evaluación, cerca de 15 %. **La prueba con ventana y las de GPU todavía no se han probado en una computadora real.**

## Ensayo de aceptación en una vista 3D N1 o N2

Preparar una instancia nueva de Blender con `--factory-startup` y una escena de práctica copiada. Guardar en una carpeta local la copia, la versión de Blender y el artefacto de la corrida de **Cubo G7B**. Registrar el ID de Actions, la versión en `publicacion.json` y el SHA-256 de `oro/cubo.duckdb`. Comprobar que coincide con `kernel.cubo_sha256` y con el campo `cubo` de `geoda/perfiles_laboratorio.json`. Conservar el estado de evidencia que declara el perfil, incluso si dice `base`.

1. Elegir un equipo N1 o N2 identificado por la sonda y anotar RAM, GPU y versión del controlador. Fijar escena, fotograma, cámara, resolución, modo de sombreado y tamaño de ventana antes de ver los resultados. Elegir una operación de vista 3D. Para el primer ensayo usar un redibujo de la misma vista con una malla subdividida visible.
2. **A, referencia.** Anotar el valor de Simplify y el límite de subdivisión de vista. Medir 30 redibujos en el área VIEW_3D, con el mismo método de `prueba_vista3d` en `g7b_sonda.py`. Descartar una ronda de calentamiento y guardar cinco valores de FPS. Capturar la vista con **View → Viewport Render Image**, sin superposiciones y con la malla ocupando el encuadre. Guardar el PNG de referencia.
3. **B, ajuste.** Usar el límite de subdivisión del plan de Geoda para esa versión y ese equipo. Activar Simplify si la acción lo pide. Mantener la misma escena cargada y repetir la medición y captura, con la misma resolución. Registrar por separado cualquier propiedad que no admita la versión de Blender.
4. **A, restauración.** Restaurar exactamente ambos valores de la referencia. Repetir la medición y la captura. Comprobar que las propiedades coinciden, que vuelve la imagen de referencia y que las medianas de ambas fases A difieren como máximo un 10 %. Si la referencia deriva, repetir el ensayo.
5. Comparar las imágenes A y B sobre una región de la malla elegida antes de aplicar el ajuste. Usar las mismas coordenadas en ambas imágenes. Como medida reproducible para este piloto, usar SSIM de luminancia con escala de 0 a 1. Conservar la región, ambas imágenes y el algoritmo empleado. Un encuadre vacío o una captura de distinto tamaño invalida la comparación.

Registrar la mediana y la dispersión de cada fase, la acción y sus valores anterior y nuevo, el nivel y la evidencia del perfil, la versión y huella del cubo, SSIM y el resultado de restauración. El objetivo de la base se comprueba cuando A está por debajo de 15 FPS, B llega a 30 FPS o más y SSIM alcanza 0.80, con reversión verificada. Un resultado por debajo de cualquiera de estos umbrales también se conserva. La ejecución sin ventana carece de la medida de vista 3D.
