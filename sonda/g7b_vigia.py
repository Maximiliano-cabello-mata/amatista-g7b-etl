"""Vigía de G7B: la sonda continua (contrato g7b.ventana/1).

La sonda normal (g7b_sonda.py) corre unas pruebas fijas y termina. El vigía acompaña un trabajo real
que dura mucho, como el render de una animación pesada, y cada cierto tiempo (por omisión 5 minutos)
cierra una «ventana» con lo que pasó en ella:

    - cuántos cuadros terminó Blender y cuánto tardó cada uno (lo lee de la salida de Blender);
    - cómo estuvo el equipo: uso de procesador y memoria, la memoria de Blender, frecuencia y
      temperatura del procesador, y uso, temperatura y memoria de la GPU NVIDIA si la hay;
    - cuánto cambió frente a la primera ventana y frente a la anterior.

Cada ventana se guarda como JSON en la carpeta de salida y, si hay dónde, se sube al lago:
bronce/telemetria/vigia/<día>/<sesión>-<ventana>.json. Del lago, el cubo arma la serie de tiempo y
la vista v_variacion_ventanas (g7b_almacen/cubo.py).

Uso (lanza Blender y lo vigila):

    python sonda/g7b_vigia.py --blender "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe" \\
        --archivo mi_animacion.blend

    python sonda/g7b_vigia.py --blender blender --archivo escena.blend --ventana 300 --salida vigia

Opciones:
    --blender RUTA        el ejecutable de Blender
    --archivo RUTA        el .blend a renderizar (se renderiza la animación completa: -a)
    --inicio N --fin N    rango de cuadros (opcional)
    --ventana SEG         duración de cada ventana (por omisión 300 = 5 minutos)
    --muestreo SEG        cada cuánto mira el equipo (por omisión 5)
    --salida DIR          carpeta de las ventanas (por omisión vigia/)
    --entorno ...         no_declarado | equipo_docente | equipo_estudiante | laboratorio_escolar
    --consentimiento      registra el consentimiento (sin esto, la medición es relativa)
    --sin-subir           no sube al lago aunque haya credencial

Subir al lago: define la variable G7B_VIGIA_SAS con la URL del contenedor y una firma (SAS) que SOLO
permita crear archivos (permiso «c»), con vencimiento corto. Con ese permiso el vigía no puede leer,
listar, sobrescribir ni borrar nada del lago. Si no hay variable o falla la red, las ventanas quedan
en la carpeta y se reintentan en la siguiente ventana. Nunca escribas la firma en un archivo del repo.

Privacidad: no guarda usuario, nombre del equipo, rutas ni el nombre del archivo. El trabajo se
identifica con un resumen (hash) de su contenido, para comparar ventanas del mismo render.

Sin dependencias: solo Python 3.9+. Con «pip install psutil» mide además procesador, memoria y
temperaturas en cualquier sistema.
"""
import argparse
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

try:
    import psutil  # opcional
except ImportError:  # pragma: no cover - depende del equipo
    psutil = None

CONTRATO = "g7b.ventana/1"
VERSION_VIGIA = "0.1.0"
ENTORNOS = ("no_declarado", "equipo_docente", "equipo_estudiante", "laboratorio_escolar")
# Una ventana se compara con la primera completa (la línea base) y con la anterior.
UMBRAL_VARIACION = 0.10      # 10 %: la misma regla de repetibilidad del plan
UMBRAL_IMPORTANTE = 0.25     # 25 %: caída importante

# Salida de Blender al renderizar una animación:
#   Fra:12 Mem:512.3M (Peak 640.1M) | Time:00:03.21 | ... | Sample 64/128
#   Saved: '/tmp/0012.png'
#    Time: 00:05.42 (Saving: 00:00.03)
RE_CUADRO = re.compile(r"\bFra:\s*(\d+)")
RE_TIEMPO_CUADRO = re.compile(r"^\s*Time:\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\s*\(Saving")
RE_VERSION = re.compile(r"^Blender (\d+\.\d+(?:\.\d+)?)")


def ahora():
    return datetime.now(timezone.utc)


def _texto_comando(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------------------------- el equipo

def cpu_modelo():
    sistema = platform.system()
    if sistema == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for linea in f:
                    if linea.lower().startswith("model name"):
                        return linea.split(":", 1)[1].strip()
        except OSError:
            pass
    elif sistema == "Windows":
        try:
            import winreg
            clave = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return str(winreg.QueryValueEx(clave, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    elif sistema == "Darwin":
        texto = _texto_comando(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
        if texto:
            return texto
    return platform.processor() or "desconocido"


def ram_gb():
    if psutil:
        return round(psutil.virtual_memory().total / 2**30, 1)
    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for linea in f:
                    if linea.startswith("MemTotal:"):
                        return round(int(linea.split()[1]) / 2**20, 1)
        except OSError:
            pass
    if platform.system() == "Windows":
        import ctypes

        class Estado(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
        estado = Estado()
        estado.dwLength = ctypes.sizeof(Estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            return round(estado.ullTotalPhys / 2**30, 1)
    return None


def gpus_sistema():
    """Nombres de las tarjetas gráficas que ve el sistema (sin datos personales)."""
    nombres = []
    if shutil.which("nvidia-smi"):
        nombres += [n.strip() for n in _texto_comando(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]).splitlines() if n.strip()]
    sistema = platform.system()
    if sistema == "Windows":
        texto = _texto_comando(["powershell", "-NoProfile", "-Command",
                                "(Get-CimInstance Win32_VideoController).Name"])
        nombres += [n.strip() for n in texto.splitlines() if n.strip()]
    elif sistema == "Linux" and shutil.which("lspci"):
        for linea in _texto_comando(["lspci"]).splitlines():
            if re.search(r"VGA|3D controller|Display", linea):
                nombres.append(linea.split(":", 2)[-1].strip())
    elif sistema == "Darwin":
        for linea in _texto_comando(["system_profiler", "SPDisplaysDataType"]).splitlines():
            if "Chipset Model:" in linea:
                nombres.append(linea.split(":", 1)[1].strip())
    return sorted(set(nombres))


def equipo():
    datos = {"so": platform.system(), "so_version": platform.release(), "arquitectura": platform.machine(),
             "cpu": cpu_modelo(), "nucleos_logicos": os.cpu_count(), "ram_gb": ram_gb(), "gpus": gpus_sistema()}
    base = "|".join([datos["cpu"], str(round(datos["ram_gb"] or 0)), ",".join(datos["gpus"]), datos["so"],
                     datos["arquitectura"]])
    datos["huella"] = hashlib.sha256(base.encode()).hexdigest()[:16]
    return datos


# ---------------------------------------------------------------------------------- muestras

def _nvidia():
    if not shutil.which("nvidia-smi"):
        return {}
    texto = _texto_comando(["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,clocks.sm",
                            "--format=csv,noheader,nounits"]).strip().splitlines()
    if not texto:
        return {}
    try:
        uso, temp, memoria, reloj = [float(x) for x in texto[0].split(",")]
    except ValueError:
        return {}
    return {"gpu_uso_pct": uso, "gpu_temp_c": temp, "gpu_mem_mb": memoria, "gpu_mhz": reloj}


def muestra(proceso_pid=None):
    """Una foto del equipo en este instante. Lo que no se puede medir, no aparece."""
    datos = {}
    if psutil:
        datos["cpu_pct"] = psutil.cpu_percent(interval=None)
        datos["ram_pct"] = psutil.virtual_memory().percent
        frecuencia = psutil.cpu_freq()
        if frecuencia and frecuencia.current:
            datos["cpu_mhz"] = round(frecuencia.current)
        try:
            sensores = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            lecturas = [t.current for grupo in sensores.values() for t in grupo if t.current]
            if lecturas:
                datos["cpu_temp_c"] = max(lecturas)
        except Exception:  # noqa: BLE001 - algunos sistemas no dan sensores
            pass
        if proceso_pid:
            try:
                proceso = psutil.Process(proceso_pid)
                rss = proceso.memory_info().rss
                for hijo in proceso.children(recursive=True):
                    rss += hijo.memory_info().rss
                datos["blender_ram_gb"] = round(rss / 2**30, 2)
            except psutil.Error:
                pass
    elif platform.system() == "Linux":
        datos.update(_cpu_linux())
    datos.update(_nvidia())
    return datos


_ANTERIOR_LINUX = {}


def _cpu_linux():
    try:
        with open("/proc/stat", encoding="utf-8") as f:
            campos = [int(x) for x in f.readline().split()[1:]]
    except OSError:
        return {}
    ocioso, total = campos[3] + campos[4], sum(campos)
    previo = _ANTERIOR_LINUX.get("cpu")
    _ANTERIOR_LINUX["cpu"] = (ocioso, total)
    if not previo or total == previo[1]:
        return {}
    return {"cpu_pct": round(100 * (1 - (ocioso - previo[0]) / (total - previo[1])), 1)}


# ---------------------------------------------------------------------------------- ventanas

def _resumen(valores):
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    ordenados = sorted(valores)
    return {"mediana": round(statistics.median(ordenados), 3),
            "p90": round(ordenados[min(len(ordenados) - 1, int(0.9 * len(ordenados)))], 3),
            "maximo": round(ordenados[-1], 3), "n": len(ordenados)}


def _cambio(actual, referencia):
    if not actual or not referencia:
        return None
    return round(actual / referencia - 1, 4)


def clasificar_cambio(cambio):
    """Para tiempos por cuadro (más es peor): estable, variación o caída importante (o mejora)."""
    if cambio is None:
        return "sin_datos"
    if cambio >= UMBRAL_IMPORTANTE:
        return "caida_importante"
    if cambio >= UMBRAL_VARIACION:
        return "variacion"
    if cambio <= -UMBRAL_VARIACION:
        return "mejora"
    return "estable"


class Sesion:
    """Arma las ventanas: guarda cuadros y muestras, y cierra una cada `ventana` segundos."""

    def __init__(self, equipo_datos, trabajo, blender_version=None, entorno="no_declarado",
                 consentimiento=False, ventana=300, muestreo=5):
        self.id = uuid.uuid4().hex[:16]
        self.equipo = equipo_datos
        self.trabajo = trabajo
        self.blender_version = blender_version
        self.entorno = entorno
        self.consentimiento = consentimiento
        self.ventana = ventana
        self.muestreo = muestreo
        self.numero = 0
        self.inicio_ventana = ahora()
        self.cuadros = []          # (cuadro, segundos)
        self.muestras = []
        self.base = None           # mediana por cuadro de la primera ventana con cuadros
        self.anterior = None

    def cuadro(self, numero, segundos):
        self.cuadros.append((numero, segundos))

    def tomar(self, datos):
        if datos:
            self.muestras.append(datos)

    def cerrar(self, estado="renderizando"):
        fin = ahora()
        tiempos = [s for _, s in self.cuadros]
        cuadro = _resumen(tiempos)
        mediana = cuadro["mediana"] if cuadro else None
        if self.base is None and mediana is not None:
            self.base = mediana
        frente_base, frente_anterior = _cambio(mediana, self.base), _cambio(mediana, self.anterior)
        equipo_resumen = {k: _resumen([m.get(k) for m in self.muestras]) for k in (
            "cpu_pct", "ram_pct", "cpu_mhz", "cpu_temp_c", "blender_ram_gb", "gpu_uso_pct", "gpu_temp_c",
            "gpu_mem_mb", "gpu_mhz")}
        registro = {
            "contrato": CONTRATO, "vigia": VERSION_VIGIA, "sintetico": False,
            "sesion": self.id, "ventana": self.numero, "inicio": self.inicio_ventana.isoformat(),
            "fin": fin.isoformat(), "duracion_s": round((fin - self.inicio_ventana).total_seconds(), 1),
            "estado": estado, "entorno": self.entorno, "consentimiento": self.consentimiento,
            "trabajo": self.trabajo, "blender": self.blender_version, "equipo": self.equipo,
            "cuadros": {"terminados": len(tiempos), "primero": self.cuadros[0][0] if self.cuadros else None,
                        "ultimo": self.cuadros[-1][0] if self.cuadros else None,
                        "segundos": [round(s, 3) for s in tiempos], "resumen": cuadro},
            "muestras": len(self.muestras),
            "sistema": {k: v for k, v in equipo_resumen.items() if v},
            "variacion": {"frente_a_base": frente_base, "frente_a_anterior": frente_anterior,
                          "estado": clasificar_cambio(frente_base),
                          "nota": "tiempo por cuadro: positivo es más lento"},
        }
        self.anterior = mediana if mediana is not None else self.anterior
        self.numero += 1
        self.inicio_ventana = fin
        self.cuadros, self.muestras = [], []
        return registro


# ---------------------------------------------------------------------------------- lago

def ruta_lago(registro):
    return f"bronce/telemetria/vigia/{registro['inicio'][:10]}/{registro['sesion']}-{registro['ventana']:04d}.json"


def subir(registro, sas_url, abrir=urllib.request.urlopen):
    """PUT del JSON con una firma de solo creación. Devuelve True si quedó en el lago."""
    partes = urllib.parse.urlsplit(sas_url)
    url = urllib.parse.urlunsplit((partes.scheme, partes.netloc,
                                   partes.path.rstrip("/") + "/" + ruta_lago(registro), partes.query, ""))
    cuerpo = json.dumps(registro, ensure_ascii=False).encode("utf-8")
    pedido = urllib.request.Request(url, data=cuerpo, method="PUT", headers={
        "x-ms-blob-type": "BlockBlob", "x-ms-version": "2021-08-06", "Content-Type": "application/json",
        "If-None-Match": "*"})          # bronce no se sobrescribe nunca
    try:
        with abrir(pedido, timeout=30) as respuesta:
            return 200 <= respuesta.status < 300
    except urllib.error.HTTPError as error:
        return error.code == 409        # ya existía: no se vuelve a subir
    except (urllib.error.URLError, OSError):
        return False


class Envio:
    """Guarda cada ventana en disco y sube las pendientes; lo que falla se reintenta después."""

    def __init__(self, carpeta, sas_url=None, subir_fn=subir, salida=print):
        self.carpeta = carpeta
        self.sas_url = sas_url
        self.subir_fn = subir_fn
        self.salida = salida
        os.makedirs(os.path.join(carpeta, "pendientes"), exist_ok=True)
        os.makedirs(os.path.join(carpeta, "subidas"), exist_ok=True)

    def guardar(self, registro):
        nombre = f"{registro['sesion']}-{registro['ventana']:04d}.json"
        destino = os.path.join(self.carpeta, "pendientes", nombre)
        with open(destino, "w", encoding="utf-8") as archivo:
            json.dump(registro, archivo, ensure_ascii=False, indent=1)
        self.enviar_pendientes()
        return nombre

    def enviar_pendientes(self):
        if not self.sas_url:
            return 0
        enviadas = 0
        pendientes = os.path.join(self.carpeta, "pendientes")
        for nombre in sorted(os.listdir(pendientes)):
            ruta = os.path.join(pendientes, nombre)
            with open(ruta, encoding="utf-8") as archivo:
                registro = json.load(archivo)
            if self.subir_fn(registro, self.sas_url):
                os.replace(ruta, os.path.join(self.carpeta, "subidas", nombre))
                enviadas += 1
            else:
                self.salida(f"  no se pudo subir {nombre}: queda pendiente para la siguiente ventana")
                break
        return enviadas


# ---------------------------------------------------------------------------------- vigilar

def huella_trabajo(ruta):
    """Resumen del contenido del .blend (primeros 4 MB y tamaño): sin nombre ni ruta."""
    h = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        h.update(archivo.read(4 * 2**20))
    h.update(str(os.path.getsize(ruta)).encode())
    return h.hexdigest()[:16]


def leer_salida(flujo, cola):
    for linea in iter(flujo.readline, ""):
        cola.put(linea)
    cola.put(None)


def vigilar(comando, sesion, envio, reloj=time.monotonic, salida=print):
    """Lanza Blender, lee su salida y cierra una ventana cada `sesion.ventana` segundos."""
    proceso = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace", bufsize=1)
    cola = queue.Queue()
    threading.Thread(target=leer_salida, args=(proceso.stdout, cola), daemon=True).start()
    if psutil:
        psutil.cpu_percent(interval=None)   # la primera lectura de psutil siempre es 0
    cuadro_actual, terminado = None, False
    proxima_muestra = reloj()
    proximo_cierre = reloj() + sesion.ventana
    while not terminado:
        try:
            linea = cola.get(timeout=0.5)
        except queue.Empty:
            linea = ""
        if linea is None:
            terminado = True
        elif linea:
            if sesion.blender_version is None and RE_VERSION.match(linea):
                sesion.blender_version = RE_VERSION.match(linea).group(1)
            encontrado = RE_CUADRO.search(linea)
            if encontrado:
                cuadro_actual = int(encontrado.group(1))
            tiempo = RE_TIEMPO_CUADRO.match(linea)
            if tiempo:
                horas, minutos, segundos = tiempo.groups()
                total = int(horas or 0) * 3600 + int(minutos) * 60 + float(segundos)
                sesion.cuadro(cuadro_actual, total)
                salida(f"  cuadro {cuadro_actual}: {total:.2f} s")
        if reloj() >= proxima_muestra:
            sesion.tomar(muestra(proceso.pid))
            proxima_muestra = reloj() + sesion.muestreo
        if reloj() >= proximo_cierre:
            _cerrar(sesion, envio, "renderizando", salida)
            proximo_cierre = reloj() + sesion.ventana
    codigo = proceso.wait()
    _cerrar(sesion, envio, "terminado" if codigo == 0 else f"blender_salio_con_{codigo}", salida)
    return codigo


def _cerrar(sesion, envio, estado, salida):
    registro = sesion.cerrar(estado)
    nombre = envio.guardar(registro)
    r, v = registro["cuadros"]["resumen"], registro["variacion"]
    texto = (f"mediana {r['mediana']:.2f} s/cuadro, {registro['cuadros']['terminados']} cuadros"
             if r else "sin cuadros terminados")
    cambio = f", {v['frente_a_base']:+.0%} frente a la primera" if v["frente_a_base"] is not None else ""
    salida(f"Ventana {registro['ventana']} ({estado}): {texto}{cambio} → {v['estado']} [{nombre}]")


def main(argv=None):
    p = argparse.ArgumentParser(prog="g7b_vigia", description="Sonda continua de G7B (g7b.ventana/1)")
    p.add_argument("--blender", required=True)
    p.add_argument("--archivo", required=True)
    p.add_argument("--inicio", type=int)
    p.add_argument("--fin", type=int)
    p.add_argument("--ventana", type=float, default=300)
    p.add_argument("--muestreo", type=float, default=5)
    p.add_argument("--salida", default="vigia")
    p.add_argument("--entorno", choices=ENTORNOS, default="no_declarado")
    p.add_argument("--consentimiento", action="store_true")
    p.add_argument("--sin-subir", action="store_true")
    o = p.parse_args(argv)
    if not os.path.isfile(o.archivo):
        p.error(f"no existe el archivo {o.archivo}")
    comando = [o.blender, "-b", o.archivo]
    if o.inicio is not None:
        comando += ["-s", str(o.inicio)]
    if o.fin is not None:
        comando += ["-e", str(o.fin)]
    comando.append("-a")
    sas = None if o.sin_subir else os.environ.get("G7B_VIGIA_SAS")
    sesion = Sesion(equipo(), huella_trabajo(o.archivo), entorno=o.entorno, consentimiento=o.consentimiento,
                    ventana=o.ventana, muestreo=o.muestreo)
    envio = Envio(o.salida, sas)
    print(f"Vigía {VERSION_VIGIA}: sesión {sesion.id}, ventanas de {o.ventana:g} s, "
          f"{'sube al lago' if sas else 'solo en disco (sin G7B_VIGIA_SAS)'}"
          f"{'' if psutil else '; sin psutil: solo tiempos por cuadro y GPU NVIDIA'}")
    return vigilar(comando, sesion, envio)


if __name__ == "__main__":
    sys.exit(main())
