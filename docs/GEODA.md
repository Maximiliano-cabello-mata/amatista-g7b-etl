# Geoda: cómo está estructurado y qué ya existe

Fecha: 2026-11-03 (cimientos, `geoda` 0.1.0). Geoda es el **kernel** que adapta el trabajo 3D a los recursos de cada equipo. Usa los datos que mide G7B y deja el trabajo listo para las herramientas libres que ya existen. No es un programa 3D ni un fork de Blender. Definiciones exactas: [FICHAS_TECNICAS.md](FICHAS_TECNICAS.md), secciones 1.3, 2 y 3.

Viene después en el orden acordado: **captura → cubo → Geoda**. La captura y el cubo se integraron el 3 de noviembre ([TELEMETRIA.md](TELEMETRIA.md), [CUBO.md](CUBO.md)).

## 1. Dos mitades y un contrato

```text
        G7B (este repo)                                   AMATISTA (add-on y API)
 ┌──────────────── CEREBRO ─────────────────┐       ┌──────────────── CLIENTE ────────────────┐
 │ cubo (mediciones reales)                  │       │ detecta la huella del equipo             │
 │   └► perfiles.py  → perfiles.json         │──────►│ pide la recomendación (caché de Amatista)│
 │   └► costos.py    → tabla / modelo        │ JSON  │ aplica las ACCIONES del plan,            │
 │ niveles.py · planificador.py              │       │   guardando el valor anterior (deshacer) │
 │ contratos: g7b.huella/1 · g7b.perfil/1 ·  │       │ mide la fluidez lograda                  │
 │            g7b.plan/1 · g7b.operacion/1   │◄──────│ reporta el evento (agregado, con permiso)│
 └───────────────────────────────────────────┘       └──────────────────────────────────────────┘
```

- **El cerebro** (paquete `geoda/` de este repo): clasifica equipos, genera perfiles con evidencia del cubo, estima costos y arma planes.
- **El cliente** (add-on de Amatista, tareas T-188 y T-199): no necesita este código. Le bastan los **contratos JSON**, así que sigue funcionando sin red con la copia incluida.
- **La regla de datos:** la huella rechaza cualquier campo que identifique a una persona (usuario, nombre del equipo, IP, correo, rutas).

## 2. Los cinco verbos

| Verbo | Qué hace | Dónde | Estado |
|---|---|---|---|
| **Detectar** | Huella técnica (CPU, RAM, GPU, OpenGL, SO) → nivel **N0 a N4** con motivos y confianza | `geoda/contratos.py`, `geoda/niveles.py` | ✅ Reglas de FICHAS 3.1; no inventa: si falta un dato, baja la confianza y lo dice |
| **Consultar** | `perfiles.json` (`g7b.perfil/1`): por nivel y versión, el perfil más completo que es **fluido** (≥ 30 fps), con evidencia | `geoda/perfiles.py` | ✅ Desde el cubo real. Sin mediciones usa reglas base (estado `base`). «Confiable» exige ≥ 5 mediciones de ≥ 3 equipos |
| **Decidir** | Plan (`g7b.plan/1`): dónde trabajar, qué versión, qué perfil y las acciones exactas | `geoda/planificador.py` | ✅ Primera versión: perfil para la escena completa |
| **Aplicar** | Cambiar las propiedades de la escena y poder deshacer | Add-on de Amatista | ⬜ T-188 y T-199 en Amatista |
| **Medir** | Fluidez lograda → evento → cubo | Add-on + sonda | 🟡 La sonda mide; el evento de práctica es T-189 y T-190 en Amatista |

Y el **modelo de costos** (`geoda/costos.py`):
- **v0:** una tabla de medianas del cubo por nivel, prueba y perfil. Si una celda no tiene datos responde `sin_datos`; nunca inventa.
- **Siguiente versión:** un modelo aprendido de menos de 1 MB, entrenado en Colab o Camber, con la misma interfaz `estimar()`.

## 3. Cómo se usa

```bash
python -m geoda nivel --huella equipo.json               # N2, confianza alta, motivos
python -m geoda perfiles --cubo cubo.duckdb --salida perfiles.json
python -m geoda decidir --huella equipo.json --blender 4.5 --perfiles perfiles.json
python -m geoda operaciones                              # catálogo de operaciones del kernel
```

`equipo.json` puede ser un `g7b.huella/1` o el bloque `equipo` de una medición de la sonda.

Ejemplo de plan para una laptop con Intel UHD 620 y 8 GB:

```json
{
  "contrato": "g7b.plan/1",
  "clasificacion": {"nivel": "N2", "confianza": "alta",
                    "motivos": ["GPU integrada con OpenGL 4.6"]},
  "donde": "este_equipo", "programa": "blender", "version": "4.5",
  "perfil": {"perfil": "ligero", "estado": "base"},
  "acciones": [
    {"ruta": "scene.render.engine", "valores_posibles": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"]},
    {"ruta": "scene.render.use_simplify", "valor": true},
    {"ruta": "scene.render.simplify_subdivision", "valor": 1},
    {"ruta": "scene.render.resolution_percentage", "valor": 75},
    {"ruta": "scene.eevee.taa_render_samples", "valor": 16}
  ],
  "explicacion": "Tu equipo es N2 (...). Te recomendamos Blender 4.5 con el perfil ligero (sugerido: todavía sin mediciones de equipos como el tuyo). Puedes deshacerlo con un clic."
}
```

## 4. Lo que se cambió en la captura para que Geoda funcione

La captura (`g7b_telemetria/capturar.py`) descartaba la GPU y el nivel del equipo, y sin eso Geoda no puede clasificar las mediciones. Ahora conserva `nivel`, `nivel_estimado`, `gpu_vista` y `gpu_cycles`: son datos técnicos que no identifican a nadie. Todo lo demás sigue fuera (versión del SO, usuario, rutas).

**Las mediciones capturadas antes de este cambio no traen GPU ni nivel:** Geoda las cuenta como `mediciones_sin_nivel` y no las usa. Hay que volver a correr la sonda.

## 5. Lo que sigue

| Paso | Repo | Tarea |
|---|---|---|
| Publicar `perfiles.json` junto con cada versión del cubo, con su hash | G7B | `cubo.yml`: llamar a `geoda perfiles` |
| Incluir el `perfiles.json` en el add-on y aplicar el plan con deshacer | Amatista | T-188 |
| Caché y rutas `/api/g7b/v1/recomendacion` | Amatista | T-196 a T-198 |
| Sonda de operaciones (simplificar, booleana, UV...) para llenar el catálogo de costos | G7B | Plan maestro B13 |
| Modelo de costos aprendido (< 1 MB, error < 25 % en equipos no vistos) | G7B | Colab y Camber |
| Planificador completo: si cabe, con qué calidad, **dónde** (otra PC, la nube) y con qué controlador | G7B | FICHAS 2.3 |
