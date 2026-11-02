"""Blender Open Data: el primer insumo del cubo (PLAN, sección 0).

Blender publica cada día una copia completa de todos los benchmarks enviados, con licencia CC0
(https://opendata.blender.org/download/). Es un ZIP con un archivo JSON Lines. Aquí se hace lo de
siempre (ELT):

1. ``descargar``: encuentra el enlace de la copia más reciente y la guarda tal cual en
   ``bronce/opendata/<AAAA-MM-DD>/<archivo>``. Si el archivo es el mismo que la última vez
   (misma ETag o mismo tamaño), no se vuelve a bajar.
2. ``leer_registros``: recorre el JSONL dentro del ZIP sin cargarlo entero en memoria.
3. ``filas_render``: convierte cada resultado en una fila plana para plata.

El formato de Open Data cambió con los años (esquemas v1 a v4), así que la lectura es tolerante:
lo que no se encuentra queda vacío y la fila sigue; lo que no tiene escena o tiempo se descarta.
"""
import hashlib
import io
import json
import os
import re
import zipfile
from datetime import date, datetime, timezone
from urllib.parse import urljoin

PAGINA = "https://opendata.blender.org/download/"
CONTROL = "control/opendata.json"
LICENCIA = "CC0-1.0"

_ENLACE = re.compile(r"""href=["']([^"']+\.(?:zip|jsonl(?:\.gz)?))["']""", re.I)


# --------------------------------------------------------------------------
# Descarga
# --------------------------------------------------------------------------

def encontrar_enlace(html, base=PAGINA):
    """El enlace más reciente de la página de descargas (el nombre lleva la fecha: se ordena)."""
    # Se ordena por el nombre del archivo (lleva la fecha), no por la ruta completa.
    enlaces = sorted({urljoin(base, e) for e in _ENLACE.findall(html)}, key=lambda e: e.rsplit("/", 1)[-1])
    if not enlaces:
        raise RuntimeError("La página de Open Data no tiene enlaces .zip ni .jsonl; revisar G7B_OPENDATA_URL")
    latest = [e for e in enlaces if "latest" in e.lower()]
    return latest[0] if latest else enlaces[-1]


def descargar(almacen, sesion=None, url=None, dia=None, salida=print):
    """Baja la copia más reciente a bronce. Devuelve la ruta en el almacén, o None si no cambió."""
    import requests

    sesion = sesion or requests.Session()
    cabeceras = {"User-Agent": "G7B/0.2 (+https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl)"}
    url = url or os.environ.get("G7B_OPENDATA_URL")
    if not url:
        pagina = sesion.get(PAGINA, headers=cabeceras, timeout=60)
        pagina.raise_for_status()
        url = encontrar_enlace(pagina.text, PAGINA)
    control = json.loads(almacen.leer(CONTROL)) if almacen.existe(CONTROL) else {}
    cabeza = sesion.head(url, headers=cabeceras, timeout=60, allow_redirects=True)
    firma = cabeza.headers.get("ETag") or cabeza.headers.get("Content-Length") or ""
    if firma and control.get("url") == url and control.get("firma") == firma:
        salida(f"Open Data sin cambios ({url}); se usa {control.get('ruta')}")
        return None
    respuesta = sesion.get(url, headers=cabeceras, timeout=900)
    respuesta.raise_for_status()
    datos = respuesta.content
    nombre = os.path.basename(url.split("?", 1)[0]) or "opendata.zip"
    ruta = f"bronce/opendata/{(dia or date.today()).isoformat()}/{nombre}"
    almacen.escribir(ruta, datos)
    control = {"url": url, "firma": firma, "ruta": ruta, "bytes": len(datos),
               "sha256": hashlib.sha256(datos).hexdigest(),
               "descargado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    almacen.escribir(CONTROL, json.dumps(control, indent=2).encode("utf-8"))
    salida(f"Open Data descargado: {len(datos) / 1e6:.1f} MB -> {ruta}")
    return ruta


def ultima_copia(almacen):
    """La copia de Open Data más reciente en bronce (cada copia es completa: basta la última)."""
    rutas = [r for r in almacen.listar("bronce/opendata/") if r.endswith((".zip", ".jsonl", ".jsonl.gz"))]
    return sorted(rutas)[-1] if rutas else None


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------

def leer_registros(datos):
    """Registros JSON de una copia: ZIP con JSONL dentro, JSONL suelto o JSONL comprimido."""
    if datos[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            for nombre in sorted(zf.namelist()):
                if nombre.endswith((".jsonl", ".json")):
                    with zf.open(nombre) as f:
                        yield from _lineas(io.TextIOWrapper(f, encoding="utf-8"))
        return
    if datos[:2] == b"\x1f\x8b":
        import gzip

        datos = gzip.decompress(datos)
    yield from _lineas(io.StringIO(datos.decode("utf-8")))


def _lineas(texto):
    for linea in texto:
        linea = linea.strip()
        if not linea:
            continue
        try:
            yield json.loads(linea)
        except json.JSONDecodeError:
            continue


def _resultados(registro):
    """Un envío puede traer uno o varios resultados en ``data``; los esquemas viejos, ninguno."""
    datos = registro.get("data", registro)
    if isinstance(datos, list):
        return [d for d in datos if isinstance(d, dict)]
    return [datos] if isinstance(datos, dict) else []


def _texto(valor):
    if isinstance(valor, dict):
        return valor.get("version") or valor.get("label") or valor.get("name") or ""
    return "" if valor is None else str(valor)


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero == numero and numero >= 0 else None  # descarta NaN y negativos


_IGPU = re.compile(
    r"\b(?:uhd|hd graphics|iris|radeon\(tm\) graphics|radeon graphics|vega \d+ graphics|"
    r"radeon \d{3}m|arc graphics|adreno|mali)\b|apple m\d(?!\s*(?:pro|max|ultra))", re.I)


def clase_dispositivo(tipo, nombre):
    """cpu, gpu_integrada o gpu_dedicada, a partir del tipo que reporta Cycles y del nombre."""
    if (tipo or "").upper() == "CPU" or not nombre:
        return "cpu"
    return "gpu_integrada" if _IGPU.search(nombre) else "gpu_dedicada"


def version_corta(version):
    """'4.2.3' -> '4.2'; deja vacío lo que no parece versión."""
    coincidencia = re.match(r"(\d+)\.(\d+)", version or "")
    return f"{coincidencia.group(1)}.{coincidencia.group(2)}" if coincidencia else ""


def filas_render(registros):
    """Filas planas para ``plata/opendata/render.parquet``. Una fila = un render de una escena."""
    vistos = set()
    for registro in registros:
        envio = str(registro.get("id") or "")
        for indice, r in enumerate(_resultados(registro)):
            escena = _texto(r.get("scene"))
            estadisticas = r.get("stats") or {}
            if not isinstance(estadisticas, dict):
                continue
            muestras_min = _numero(estadisticas.get("samples_per_minute"))
            tiempo = _numero(estadisticas.get("render_time_no_sync") or estadisticas.get("total_render_time"))
            if not escena or (muestras_min is None and tiempo is None):
                continue
            dispositivo = r.get("device_info") or {}
            sistema = r.get("system_info") or {}
            tipo = (dispositivo.get("device_type") or "").upper()
            nombres = []
            for d in dispositivo.get("compute_devices") or []:
                nombre = d.get("name") if isinstance(d, dict) else d
                if nombre:
                    nombres.append(str(nombre).strip())
            nombre_dispositivo = " + ".join(sorted(set(nombres)))
            version = _texto(r.get("blender_version"))
            fecha = str(r.get("timestamp") or registro.get("created_at") or "")[:10]
            clave = hashlib.sha256(
                f"{envio}|{indice}|{escena}|{nombre_dispositivo}|{version}|{muestras_min}|{tiempo}".encode()
            ).hexdigest()[:20]
            if clave in vistos:
                continue
            vistos.add(clave)
            yield {
                "render_id": clave,
                "fecha": fecha or None,
                "version_blender": version,
                "version_corta": version_corta(version),
                "so": str(sistema.get("system") or ""),
                "arquitectura": str(sistema.get("machine") or ""),
                "tipo_dispositivo": tipo or "CPU",
                "dispositivo": nombre_dispositivo or "desconocido",
                "clase_dispositivo": clase_dispositivo(tipo, nombre_dispositivo),
                "hilos_cpu": int(_numero(dispositivo.get("num_cpu_threads") or sistema.get("num_cpu_threads")) or 0),
                "escena": escena,
                "muestras_por_minuto": muestras_min,
                "tiempo_render_s": tiempo,
                "memoria_pico_mb": _numero(estadisticas.get("device_peak_memory")),
                "lanzador": _texto(r.get("benchmark_launcher")),
            }
