"""Sonda de rendimiento de G7B (contrato ``g7b.medicion/1``).

Mide qué tan bien trabaja Blender en esta computadora con escenas y ajustes
estándar, sin descargar nada: las escenas se generan aquí mismo. Corre dentro
de Blender, sin instalar software nuevo.

Uso (sin ventana: edición, animación y render):

    blender -b --factory-startup --python sonda/g7b_sonda.py -- --salida resultados

Con ventana (agrega la prueba de la vista 3D):

    blender --factory-startup --python sonda/g7b_sonda.py -- --salida resultados --salir

Opciones después de ``--``:

    --salida DIR       carpeta para el JSON (por omisión: resultados)
    --escena NOMBRE    ligera | media | pesada (por omisión: media)
    --perfiles LISTA   minimo,ligero,completo (por omisión: los tres)
    --repeticiones N   veces que se repite cada prueba (por omisión: 3)
    --nivel N          N0..N4 si lo conoces; si no, se estima
    --sin-render       omite las pruebas de render
    --rapida           escena ligera, perfil ligero y una repetición
    --salir            cierra Blender al terminar (modo con ventana)

Privacidad: no guarda nombre de usuario, nombre del equipo, rutas ni
contenido personal. La huella del equipo es un resumen (hash) del modelo de
CPU, la RAM redondeada, las GPU y el sistema operativo.

Licencia: GPL-3.0-or-later (usa la API de Python de Blender).
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

import bpy  # antes que bmesh: con Blender como módulo, bmesh existe solo después de bpy
import bmesh

CONTRATO = "g7b.medicion/1"
VERSION_SONDA = "0.1.0"

# Tamaño de la escena: es la carga de trabajo, igual en todas las computadoras.
ESCENAS = {
    "ligera": {"objetos": 12, "subdiv_base": 2, "cuadros": 60, "malla": 64},
    "media": {"objetos": 36, "subdiv_base": 3, "cuadros": 120, "malla": 128},
    "pesada": {"objetos": 96, "subdiv_base": 4, "cuadros": 240, "malla": 256},
}

# Perfil: los ajustes con que se trabaja esa escena (lo que el Corazón aplicaría).
PERFILES = {
    "minimo": {"subsurf": 0, "simplify": True, "muestras": 4, "res_pct": 50},
    "ligero": {"subsurf": 1, "simplify": False, "muestras": 16, "res_pct": 75},
    "completo": {"subsurf": 2, "simplify": False, "muestras": 64, "res_pct": 100},
}

TIPOS_GPU_CYCLES = ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI")


# --------------------------------------------------------------------------
# Huella del equipo
# --------------------------------------------------------------------------

def _leer(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _cpu_modelo():
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
            clave = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(clave, "ProcessorNameString")[0].strip()
        except Exception:
            pass
    elif sistema == "Darwin":
        modelo = _leer(["sysctl", "-n", "machdep.cpu.brand_string"])
        if modelo:
            return modelo
    return platform.processor() or "desconocido"


def _ram_gb():
    sistema = platform.system()
    try:
        if sistema == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for linea in f:
                    if linea.startswith("MemTotal"):
                        return round(int(linea.split()[1]) / 1024 / 1024, 1)
        elif sistema == "Windows":
            import ctypes

            class Estado(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            estado = Estado()
            estado.dwLength = ctypes.sizeof(Estado)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado))
            return round(estado.ullTotalPhys / 1024 ** 3, 1)
        elif sistema == "Darwin":
            return round(int(_leer(["sysctl", "-n", "hw.memsize"]) or 0) / 1024 ** 3, 1)
    except Exception:
        pass
    return None


def _gpu_vista():
    """Lo que Blender usa para dibujar (solo existe con ventana o contexto GPU)."""
    datos = {}
    try:
        import gpu
        datos["fabricante"] = gpu.platform.vendor_get()
        datos["modelo"] = gpu.platform.renderer_get()
        datos["version"] = gpu.platform.version_get()
        if hasattr(gpu.platform, "backend_type_get"):
            datos["backend"] = gpu.platform.backend_type_get()
    except Exception as error:  # sin ventana no hay contexto de dibujo
        datos["no_disponible"] = str(error)[:120]
    return datos


def _dispositivos_cycles():
    """GPU que Cycles puede usar para render (existe también sin ventana)."""
    dispositivos = []
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for tipo in TIPOS_GPU_CYCLES:
            try:
                prefs.compute_device_type = tipo
            except TypeError:
                continue
            if hasattr(prefs, "refresh_devices"):
                prefs.refresh_devices()
            else:
                prefs.get_devices()
            for d in prefs.devices:
                if d.type == tipo:
                    dispositivos.append({"tipo": tipo, "nombre": d.name})
        prefs.compute_device_type = "NONE"
    except Exception:
        pass
    # Un mismo dispositivo puede aparecer con OptiX y con CUDA: se deja una vez por nombre y tipo.
    unicos = {(d["tipo"], d["nombre"]): d for d in dispositivos}
    return list(unicos.values())


def _estimar_nivel(ram, gpus_cycles):
    discretas = [d for d in gpus_cycles if d["tipo"] in ("OPTIX", "CUDA", "HIP", "ONEAPI")]
    if discretas:
        return "N3"  # N4 requiere saber la memoria de video: se indica con --nivel
    if ram is not None and ram < 8:
        return "N1"
    return "N2"


def huella_equipo(nivel_manual=None):
    ram = _ram_gb()
    gpus = _dispositivos_cycles()
    equipo = {
        "so": platform.system(),
        "so_version": platform.release(),
        "arquitectura": platform.machine(),
        "cpu": _cpu_modelo(),
        "nucleos_logicos": os.cpu_count(),
        "ram_gb": ram,
        "gpu_vista": _gpu_vista(),
        "gpu_cycles": gpus,
    }
    base = "|".join([equipo["cpu"], str(round(ram or 0)), ",".join(sorted(g["nombre"] for g in gpus)),
                     equipo["so"], equipo["arquitectura"]])
    equipo["huella"] = hashlib.sha256(base.encode()).hexdigest()[:16]
    equipo["nivel"] = nivel_manual or _estimar_nivel(ram, gpus)
    equipo["nivel_estimado"] = nivel_manual is None
    return equipo


# --------------------------------------------------------------------------
# Escena estándar
# --------------------------------------------------------------------------

def escena_vacia():
    for objeto in list(bpy.data.objects):
        bpy.data.objects.remove(objeto, do_unlink=True)
    for coleccion in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.actions):
        for bloque in list(coleccion):
            coleccion.remove(bloque)
    escena = bpy.context.scene
    escena.frame_start, escena.frame_current = 1, 1
    return escena


def _malla_icosfera(nombre, subdiv):
    malla = bpy.data.meshes.new(nombre)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.5)
    bm.to_mesh(malla)
    bm.free()
    return malla


def construir_escena(escena_cfg, perfil_cfg):
    """Objetos animados con modificadores, una luz y una cámara. Siempre igual."""
    escena = escena_vacia()
    escena.frame_end = escena_cfg["cuadros"]
    escena.render.use_simplify = perfil_cfg["simplify"]
    escena.render.simplify_subdivision = 0 if perfil_cfg["simplify"] else 6
    material = bpy.data.materials.new("g7b_material")
    lado = max(1, round(escena_cfg["objetos"] ** 0.5))
    objetos = []
    for i in range(escena_cfg["objetos"]):
        obj = bpy.data.objects.new(f"g7b_{i}", _malla_icosfera(f"g7b_malla_{i}", escena_cfg["subdiv_base"]))
        escena.collection.objects.link(obj)
        obj.data.materials.append(material)
        obj.location = ((i % lado) * 1.2, (i // lado) * 1.2, 0)
        sub = obj.modifiers.new("subsurf", "SUBSURF")
        sub.levels = perfil_cfg["subsurf"]
        sub.render_levels = perfil_cfg["subsurf"]
        giro = obj.modifiers.new("giro", "SIMPLE_DEFORM")
        giro.deform_method = "TWIST"
        for cuadro, angulo in ((1, 0.0), (escena_cfg["cuadros"], 3.0)):
            giro.angle = angulo
            giro.keyframe_insert("angle", frame=cuadro)
        for cuadro, z in ((1, 0.0), (escena_cfg["cuadros"] // 2, 1.0), (escena_cfg["cuadros"], 0.0)):
            obj.location.z = z
            obj.keyframe_insert("location", index=2, frame=cuadro)
        objetos.append(obj)
    luz = bpy.data.objects.new("g7b_luz", bpy.data.lights.new("g7b_luz", "SUN"))
    escena.collection.objects.link(luz)
    luz.rotation_euler = (0.8, 0.2, 0.5)
    camara = bpy.data.objects.new("g7b_camara", bpy.data.cameras.new("g7b_camara"))
    escena.collection.objects.link(camara)
    centro = (lado - 1) * 0.6
    camara.location = (centro, -lado * 1.6 - 2, lado * 1.1 + 1)
    camara.rotation_euler = (1.0, 0.0, 0.0)
    escena.camera = camara
    return escena, objetos


# --------------------------------------------------------------------------
# Pruebas
# --------------------------------------------------------------------------

def prueba_edicion(escena_cfg, _perfil_cfg):
    """Operaciones de modelado comunes sobre una malla (subdividir, biselar, normales)."""
    n = escena_cfg["malla"]
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=n, y_segments=n, size=2.0)
    inicio = time.perf_counter()
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bmesh.ops.bevel(bm, geom=bm.edges[: len(bm.edges) // 4], offset=0.002, segments=2, affect="EDGES")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    duracion = time.perf_counter() - inicio
    caras = len(bm.faces)
    bm.free()
    return {"metrica": "tiempo_edicion", "valor": duracion, "unidad": "s", "extra": {"caras": caras}}


def prueba_modificadores(escena_cfg, perfil_cfg):
    """Primera evaluación de la escena: lo que tarda en reaccionar al abrirla o al cambiar su forma.

    Incluye preparar la subdivisión (un costo fijo que casi no crece con el nivel); el costo por
    nivel lo mide ``prueba_animacion``."""
    escena, objetos = construir_escena(escena_cfg, perfil_cfg)
    capa = bpy.context.view_layer
    inicio = time.perf_counter()
    capa.update()
    grafo = bpy.context.evaluated_depsgraph_get()
    caras = sum(len(o.evaluated_get(grafo).data.polygons) for o in objetos)
    duracion = time.perf_counter() - inicio
    return {"metrica": "tiempo_primera_evaluacion", "valor": duracion, "unidad": "s", "extra": {"caras_evaluadas": caras}}


def prueba_animacion(escena_cfg, perfil_cfg):
    """Recorrer la animación cuadro por cuadro: cuántos cuadros por segundo se calculan."""
    escena, _ = construir_escena(escena_cfg, perfil_cfg)
    cuadros = escena_cfg["cuadros"]
    escena.frame_set(1)
    inicio = time.perf_counter()
    for cuadro in range(1, cuadros + 1):
        escena.frame_set(cuadro)
    duracion = time.perf_counter() - inicio
    return {"metrica": "cuadros_por_segundo_animacion", "valor": cuadros / duracion if duracion else 0.0,
            "unidad": "fps", "extra": {"cuadros": cuadros}}


def _render(escena_cfg, perfil_cfg, motor, dispositivo="CPU"):
    escena, _ = construir_escena(escena_cfg, perfil_cfg)
    escena.render.engine = motor
    escena.render.resolution_x, escena.render.resolution_y = 640, 360
    escena.render.resolution_percentage = perfil_cfg["res_pct"]
    if motor == "CYCLES":
        escena.cycles.samples = perfil_cfg["muestras"]
        escena.cycles.use_denoising = False
        escena.cycles.device = dispositivo
    elif motor.startswith("BLENDER_EEVEE"):
        escena.eevee.taa_render_samples = perfil_cfg["muestras"]
    inicio = time.perf_counter()
    bpy.ops.render.render(write_still=False)
    return time.perf_counter() - inicio


def prueba_render_cycles_cpu(escena_cfg, perfil_cfg):
    return {"metrica": "tiempo_render_cycles_cpu", "valor": _render(escena_cfg, perfil_cfg, "CYCLES"), "unidad": "s"}


def prueba_render_cycles_gpu(escena_cfg, perfil_cfg):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in TIPOS_GPU_CYCLES:
        try:
            prefs.compute_device_type = tipo
        except TypeError:
            continue
        if hasattr(prefs, "refresh_devices"):
            prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == tipo]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == tipo
            try:
                valor = _render(escena_cfg, perfil_cfg, "CYCLES", "GPU")
            finally:
                prefs.compute_device_type = "NONE"
            return {"metrica": "tiempo_render_cycles_gpu", "valor": valor, "unidad": "s",
                    "extra": {"tipo": tipo, "gpus": [d.name for d in gpus]}}
    prefs.compute_device_type = "NONE"
    raise RuntimeError("sin GPU compatible con Cycles")


def _exigir_contexto_de_dibujo():
    """Workbench y EEVEE dibujan con la GPU. En Linux sin ventana, Blender usa EGL; si falta,
    Blender termina el proceso en lugar de lanzar un error, así que se revisa antes."""
    if bpy.app.background and platform.system() == "Linux":
        import ctypes.util
        if not ctypes.util.find_library("EGL"):
            raise RuntimeError("sin contexto de dibujo (falta libEGL)")


def _motor_eevee():
    motores = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    for candidato in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if candidato in motores:
            return candidato
    raise RuntimeError("EEVEE no disponible")


def prueba_render_eevee(escena_cfg, perfil_cfg):
    _exigir_contexto_de_dibujo()
    return {"metrica": "tiempo_render_eevee", "valor": _render(escena_cfg, perfil_cfg, _motor_eevee()), "unidad": "s"}


def prueba_render_workbench(escena_cfg, perfil_cfg):
    _exigir_contexto_de_dibujo()
    return {"metrica": "tiempo_render_workbench",
            "valor": _render(escena_cfg, perfil_cfg, "BLENDER_WORKBENCH"), "unidad": "s"}


def prueba_vista3d(escena_cfg, perfil_cfg):
    """Cuadros por segundo de la vista 3D al redibujar (solo con ventana)."""
    if bpy.app.background:
        raise RuntimeError("requiere ventana")
    construir_escena(escena_cfg, perfil_cfg)
    ventana = bpy.context.window_manager.windows[0]
    area = next(a for a in ventana.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    iteraciones = 30
    with bpy.context.temp_override(window=ventana, area=area, region=region):
        inicio = time.perf_counter()
        bpy.ops.wm.redraw_timer(type="DRAW", iterations=iteraciones)
        duracion = time.perf_counter() - inicio
    return {"metrica": "cuadros_por_segundo_vista3d", "valor": iteraciones / duracion if duracion else 0.0,
            "unidad": "fps", "extra": {"iteraciones": iteraciones}}


# (nombre, función, es render, depende del perfil)
PRUEBAS = [
    ("edicion", prueba_edicion, False, False),
    ("modificadores", prueba_modificadores, False, True),
    ("animacion", prueba_animacion, False, True),
    ("vista3d", prueba_vista3d, False, True),
    ("render_workbench", prueba_render_workbench, True, True),
    ("render_eevee", prueba_render_eevee, True, True),
    ("render_cycles_cpu", prueba_render_cycles_cpu, True, True),
    ("render_cycles_gpu", prueba_render_cycles_gpu, True, True),
]


# --------------------------------------------------------------------------
# Corrida
# --------------------------------------------------------------------------

def _guardar(medicion, ruta):
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(medicion, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)


def correr(opciones, ruta=None):
    escena_nombre = "ligera" if opciones.rapida else opciones.escena
    perfiles = ["ligero"] if opciones.rapida else opciones.perfiles
    repeticiones = 1 if opciones.rapida else opciones.repeticiones
    escena_cfg = ESCENAS[escena_nombre]
    calentar = repeticiones > 1
    inicio_total = time.perf_counter()
    resultados = []
    medicion = {
        "contrato": CONTRATO,
        "sonda": VERSION_SONDA,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sintetico": False,
        "completa": False,
        "blender": {"version": bpy.app.version_string, "hash": bpy.app.build_hash.decode(errors="replace"),
                    "sin_ventana": bool(bpy.app.background)},
        "equipo": huella_equipo(opciones.nivel),
        "escena": {"nombre": escena_nombre, **escena_cfg},
        "repeticiones": repeticiones,
        "calentamiento_descartado": calentar,
        "resultados": resultados,
    }
    if ruta is None:
        os.makedirs(opciones.salida, exist_ok=True)
        nombre = f"medicion_{medicion['fecha'][:10]}_{medicion['equipo']['huella'][:8]}_{int(time.time())}.json"
        ruta = os.path.join(opciones.salida, nombre)
    for indice, perfil in enumerate(perfiles):
        perfil_cfg = PERFILES[perfil]
        for nombre, funcion, es_render, por_perfil in PRUEBAS:
            if es_render and opciones.sin_render:
                continue
            if not por_perfil and indice > 0:
                continue  # no depende del perfil: se mide una sola vez
            registro = {"prueba": nombre, "perfil": perfil if por_perfil else None}
            valores, extra = [], None
            try:
                # La primera corrida calienta cachés y memoria; se descarta.
                for vuelta in range(repeticiones + (1 if calentar else 0)):
                    salida = funcion(escena_cfg, perfil_cfg)
                    if calentar and vuelta == 0:
                        continue
                    valores.append(salida["valor"])
                    extra = salida.get("extra")
                registro.update({"metrica": salida["metrica"], "unidad": salida["unidad"],
                                 "valores": [round(v, 4) for v in valores],
                                 "mediana": round(statistics.median(valores), 4)})
                mediana = statistics.median(valores)
                if len(valores) > 1 and mediana:
                    registro["variacion"] = round((max(valores) - min(valores)) / mediana, 4)
                if extra:
                    registro["extra"] = extra
                estado = f"{registro['mediana']} {registro['unidad']}"
            except Exception as error:
                registro["no_disponible"] = f"{type(error).__name__}: {str(error)[:160]}"
                estado = "no disponible"
            resultados.append(registro)
            print(f"[g7b-sonda] {registro['perfil'] or '-':9s} {nombre:18s} {estado}", flush=True)
            # Se guarda tras cada prueba: si Blender se cierra a medias, lo medido no se pierde.
            medicion["duracion_total_s"] = round(time.perf_counter() - inicio_total, 2)
            _guardar(medicion, ruta)
    medicion["completa"] = True
    _guardar(medicion, ruta)
    return medicion, ruta


def leer_opciones(argv):
    p = argparse.ArgumentParser(prog="g7b_sonda")
    p.add_argument("--salida", default="resultados")
    p.add_argument("--escena", choices=sorted(ESCENAS), default="media")
    p.add_argument("--perfiles", type=lambda s: [x for x in s.split(",") if x], default=list(PERFILES))
    p.add_argument("--repeticiones", type=int, default=3)
    p.add_argument("--nivel", choices=["N0", "N1", "N2", "N3", "N4"])
    p.add_argument("--sin-render", action="store_true")
    p.add_argument("--rapida", action="store_true")
    p.add_argument("--salir", action="store_true")
    opciones = p.parse_args(argv)
    desconocidos = set(opciones.perfiles) - set(PERFILES)
    if desconocidos:
        p.error(f"perfiles desconocidos: {', '.join(sorted(desconocidos))}")
    return opciones


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opciones = leer_opciones(argv)
    medicion, ruta = correr(opciones)
    print(f"[g7b-sonda] listo en {medicion['duracion_total_s']} s: {ruta}", flush=True)
    if opciones.salir and not bpy.app.background:
        bpy.ops.wm.quit_blender()
    return ruta


if __name__ == "__main__":
    main()
