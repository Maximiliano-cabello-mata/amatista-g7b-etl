# Estándar de telemetría de G7B

Fecha: 17 de noviembre de 2026. Este documento dice cómo debe verse cualquier cifra de equipos y rendimiento que entre a G7B, venga de donde venga: Blender Open Data, la sonda, los reportes de error de Blender o fuentes futuras como OpenBenchmarking o la encuesta de Steam. Así el cubo y Geoda comparan peras con peras.

## 1. Quién trae la telemetría

Geodar tiene responsabilidades separadas, y el catálogo las hace cumplir (`g7b_ingesta/catalogo.py`, `validar`):

| Herramienta | Qué trae | Cómo se corre |
|---|---|---|
| **Radar de telemetría** | Cifras de equipos y rendimiento | `python -m geodar telemetria` (colectores) y sensores directos con `destino: telemetria` |
| **Arañas de documentación (Zyte)** | Manuales y notas de versión | `geodar vigilar` lanza la araña y `zyte_a_lago` la trae |
| Sensores directos | Feeds, APIs y foros | `geodar vigilar` |
| Gestores externos | La sonda y Amatista | Sus propias tareas |

**Reglas del catálogo:**
- Una fuente con `extractor: zyte` debe tener `destino: documentos`.
- Una fuente con `destino: telemetria` usa `extractor: telemetria` (con un `colector`), `directo` o `externo`. Nunca una araña.
- `colector: pendiente` significa que el colector aún no existe, normalmente porque falta confirmar la licencia. Una fuente así no puede estar activa.

## 2. El equipo: `g7b.hardware/1`

Cada medición o evento lleva un bloque `hardware` hecho por `g7b_telemetria/hardware.py` con la tabla propia [`fuentes/hardware.yml`](../fuentes/hardware.yml):

```json
{
  "estandar": "g7b.hardware/1",
  "mide": "gpu",                       // gpu | cpu | falla
  "so": "Windows",
  "gpus": [{"nombre": "NVIDIA GeForce RTX 3060 Laptop GPU", "nombre_original": "...",
            "fabricante": "nvidia", "clase": "dedicada", "vram_gb": 6, "regla": "rtx 3060 laptop"}],
  "nivel": "N3", "confianza": "media",
  "motivos": ["GPU dedicada con 6 GB de VRAM", "sin dato de RAM"]
}
```

- **Nombre:** se limpian «(R)», «(TM)» y «/PCIe/SSE2», y se conserva el original.
- **Clase:** `integrada`, `dedicada` o `desconocida`. Lo que la tabla no reconoce queda `desconocida` y **no recibe nivel**: no se adivina.
- **VRAM:** solo cuando el modelo tiene una sola cantidad. La RTX 3060 de escritorio viene con 8 o 12 GB, así que se deja vacía.
- **Nivel N0–N4:** con las mismas reglas de Geoda (`geoda/niveles.py`), siempre con su **confianza** y sus **motivos**. Sin dato de RAM, decide la GPU y la confianza baja. Si la fuente trae la versión de OpenGL, como los reportes de error, se usa; una integrada con OpenGL 3.3 baja a N1.
- **Benchmark de CPU:** `mide: cpu`, sin nivel, porque no dice qué GPU tiene el equipo.

**Agregar un modelo:** se añade una línea a `fuentes/hardware.yml`, lo más específico arriba, con una prueba en `pruebas/test_radar_telemetria.py`. Nunca se copian bases de terceros (TechPowerUp prohíbe la extracción).

## 3. La medición: `g7b.telemetria/1`

Lo que entra a `plata/telemetria/<estado>/<fuente>/<lote>.jsonl.gz` y de ahí al cubo (`g7b_almacen/cubo.py`):

| Campo | Qué es |
|---|---|
| `contrato`, `sintetico` | `g7b.telemetria/1` y `false`. Nada sintético entra al cubo |
| `id`, `huella_origen` | SHA-256 de la medición y del registro original |
| `fuente`, `licencia`, `licencia_url` | De dónde viene y con qué licencia |
| `fecha` | ISO 8601 con zona horaria |
| `version`, `escena`, `prueba` | Programa medido y qué se midió |
| `metrica`, `unidad`, `valor` | Unidades canónicas: `s`, `fps`, `samples/min`. El valor es positivo y finito |
| `hardware` | El bloque `g7b.hardware/1` |
| `estado`, `motivos` | `aceptado` o `revision`, con los motivos. Un benchmark público que G7B no reprodujo queda en `revision` |

En el cubo, la vista **`v_render_por_nivel`** agrupa el render público por nivel, clase de GPU, backend, versión y escena, con mediana y cuartiles. Las filas viejas sin `hardware` quedan con nivel NULL: se ven, pero no se mezclan con las clasificadas.

## 4. Blender Open Data, completo y por tandas

Antes se tomaban los primeros 1.000 registros del archivo, que son los más viejos (marzo de 2022, Blender 3.0.1), y cada semana volvían a ser los mismos. Ahora (`seleccionar_opendata`):

1. Cada corrida lee el archivo completo una vez y se queda con una tanda de hasta `--limite` registros (20.000 en el flujo semanal).
2. Primero entra **lo nuevo desde la última vez**. Con lo que sobra del límite, **sigue hacia atrás** desde donde se quedó, de lo más reciente a lo más viejo, sin huecos y sin repetir.
3. El estado vive en el lago (`control/telemetria/blender-open-data.json`): el tramo `desde`–`hasta` ya capturado, los id del borde y si ya se llegó al principio (`completo_hacia_atras`). Se guarda **al final**: si algo falla antes, la tanda se repite.
4. `geodar salud` revisa también al radar: si falla, aparece como `error`, y si pasan más de dos semanas sin captura, como `atrasada`.

## 5. Telemetría de fallas: los reportes de error de Blender

El sensor `gitea_issues` (fuente `blender-reportes`) lee los reportes de projects.blender.org por su API y saca de la plantilla:
- el sistema operativo;
- la tarjeta gráfica, con su nivel según `g7b.hardware/1`;
- la versión de OpenGL;
- la versión que falla y la que funcionaba;
- las etiquetas del reporte (por ejemplo, el módulo afectado).

**El texto del reporte no se guarda**, porque es de su autor: solo esos campos, el título, el enlace y las fechas. Responde la pregunta P2 del plan: qué versión conviene en cada equipo.

Pide poco: solo los reportes actualizados desde la última vez y como mucho 3 páginas de 50 al día. La infraestructura de Blender ya tuvo incidentes por carga de arañas. Está **inactiva** hasta probarla en vivo (`python -m geodar probar --fuente blender-reportes`, o el flujo «Geodar Radar (probar y revisar)») y confirmar las condiciones de uso del sitio.

## 6. Agregar una fuente de telemetría

1. **En el catálogo:** `destino: telemetria`, `modo: agregados`, la licencia confirmada y las preguntas del plan que responde.
2. **Elegir cómo entra:**
   - Si la fuente es una API o un feed que ya trae el dato, un sensor directo.
   - Si es un archivo grande o hace falta recorrerla por tandas, un colector en `geodar/__main__.py` (`COLECTORES`).
3. **Normalizar el equipo** con `g7b_telemetria.hardware`; nunca con reglas propias de la fuente.
4. **Unidades canónicas y estado:** lo que G7B no midió entra en `revision`.
5. **Pruebas** con datos de ejemplo, y una prueba en vivo con `geodar probar` antes de activar.
