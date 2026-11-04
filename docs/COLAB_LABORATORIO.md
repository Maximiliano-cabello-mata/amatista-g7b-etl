# Laboratorio G7B en Google Colab — prueba real de extremo a extremo

Esta guía no requiere cargar un notebook: **abre Colab → Nuevo cuaderno → pega cada bloque en una celda**.
Usa CPU (Entorno de ejecución → Cambiar tipo de entorno de ejecución → CPU).
No montes Google Drive ni agregues claves de Azure/MongoDB para este ensayo.

El código de esta guía está en la rama de integración `chatgpt/g7b-publicacion-segura-colab-20261101`,
basada en el PR #4; cuando llegue a `main`, podrás usar la rama principal.

## Celda 1 — Código del warehouse

```python
!git clone --depth 1 --branch chatgpt/g7b-publicacion-segura-colab-20261101 https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git /content/g7b
%cd /content/g7b
!pip install -q -r requirements-almacen.txt
```

## Celda 2 — Blender oficial para Linux x64

```python
%%bash
set -euxo pipefail
apt-get update -qq >/dev/null
apt-get install -y -qq libgl1 libx11-6 libxi6 libxrender1 libxxf86vm1 libxfixes3 libsm6 libxkbcommon0 libegl1 libopengl0 libxrandr2 libxcursor1 libxinerama1 >/dev/null
cd /content
wget --show-progress -O blender-4.5.15-linux-x64.tar.xz https://download.blender.org/release/Blender4.5/blender-4.5.15-linux-x64.tar.xz
tar -xJf blender-4.5.15-linux-x64.tar.xz
./blender-4.5.15-linux-x64/blender -b --factory-startup --python-expr "import bpy; print('BLENDER_OK:', bpy.app.version_string)"
```

Si el servidor de Blender o Colab cambia, detén la prueba y lee el error; no reemplaces Blender por un paquete externo desconocido.

## Celda 3 — Medición real (tres repeticiones)

```python
import subprocess
from pathlib import Path

comando = [
    "/content/blender-4.5.15-linux-x64/blender", "-b", "--factory-startup",
    "--python", "/content/g7b/sonda/g7b_sonda.py",
    "--", "--salida", "/content/mediciones",
    "--escena", "ligera", "--perfiles", "minimo,ligero,completo",
    "--repeticiones", "3", "--sin-render", "--origen", "colab",
]
r = subprocess.run(comando, capture_output=True, text=True, timeout=900)
print((r.stdout + "\n" + r.stderr)[-18000:])
assert r.returncode == 0, "Falló la sonda; revisa la salida anterior"
assert list(Path("/content/mediciones").glob("*.json"))
```

En modo sin ventana, la vista3d no es medible. Los FPS de animación **no son** FPS de la interfaz.
Colab está ejecutándose en hardware de Colab: **no lo etiquetes como una computadora vieja**.

## Celda 4 — Bronce → Plata → Cubo → Compuerta → Publicado

```python
import subprocess
import json
from pathlib import Path

root = "/content/g7b"
base = "/content/g7b_datos"
for args in [
    ["sonda", "/content/mediciones"],
    ["construir"],
]:
    cmd = ["python", "-m", "g7b_almacen", *args, "--carpeta", base]
    print("Ejecutando:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=root, check=True)

m = json.loads(Path(base + "/publicado/actual.json").read_text())
print("Versión aprobada:", m["version"])
p = Path(base) / m["archivos"]["perfiles"]["ruta"]
perfiles = json.loads(p.read_text())
print("Contrato:", perfiles["contrato"])
print("Perfiles:", json.dumps(perfiles["perfiles"], ensure_ascii=False, indent=2))
```

**Resultado esperado:** existe `publicado/actual.json` únicamente si la compuerta aprobó
los datos. Una recomendación puede ser provisional y no indica todavía validez estadística
en computadoras antiguas. El cubo real queda en `/content/g7b_datos/oro/cubo.duckdb`.

## Celda 5 — Guardar resultados (sin claves)

```python
import zipfile
from pathlib import Path
from google.colab import files
carpetas = [Path("/content/mediciones"), Path("/content/g7b_datos/publicado")]
ruta = "/content/g7b_resultado_laboratorio.zip"
with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
    for carpeta in carpetas:
        for f in carpeta.rglob("*.json"):
            z.write(f, arcname=str(f.relative_to("/content")))
files.download(ruta)
```

No sincronices automáticamente las mediciones a Azure hasta revisar la huella de hardware,
origen, consentimiento y metadatos. Para datos de rendimiento comparables, hay que
repetir pruebas en equipos físicos y registrar temperaturas, cargas y versiones.

## Integración con Amatista

El consumidor de perfiles **no debe leer `oro/perfiles.json` directamente**.
Debe consultar `publicado/actual.json`, verificar hashes y descargar el `perfiles.json`
de la versión indicada. En Amatista, los ajustes deben aplicarse con consentimiento,
permitir deshacer y conservar un perfil integrado para trabajar sin conexión.
