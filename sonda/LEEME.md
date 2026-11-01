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
