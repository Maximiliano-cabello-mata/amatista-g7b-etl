"""Contratos de Geoda: lo que entra y sale, en JSON versionado. Sin datos personales.

    g7b.huella/1     el equipo, solo datos técnicos (FICHAS_TECNICAS 3.2)
    g7b.perfil/1     perfiles recomendados por nivel y versión, con su evidencia (3.4)
    g7b.plan/1       la decisión para un equipo y una tarea, con acciones reversibles (2.3)
    g7b.operacion/1  catálogo de operaciones del kernel (2.1)
"""
import hashlib
import re
from dataclasses import asdict, dataclass, field

HUELLA = "g7b.huella/1"
PERFIL = "g7b.perfil/1"
PLAN = "g7b.plan/1"
OPERACION = "g7b.operacion/1"

NIVELES = ("N0", "N1", "N2", "N3", "N4")
ESTADOS_PERFIL = ("confiable", "provisional", "base")
TIPOS_GPU = ("integrada", "dedicada", "desconocida")

# Campos que JAMÁS deben llegar a Geoda: identifican a una persona o a un equipo concreto.
PROHIBIDOS = {"usuario", "nombre_equipo", "hostname", "correo", "email", "ip", "mac", "ruta", "rutas", "cuenta"}

# Tipos de dispositivo de Cycles que solo existen en GPU dedicadas (Metal también cubre integradas de Apple).
CYCLES_DEDICADA = {"OPTIX", "CUDA", "HIP", "ONEAPI"}


@dataclass
class Gpu:
    nombre: str
    tipo: str = "desconocida"          # integrada | dedicada | desconocida
    vram_gb: float | None = None


@dataclass
class Huella:
    """Lo mínimo que Geoda necesita saber de un equipo para decidir."""
    cpu: str = ""
    nucleos: int | None = None
    ram_gb: float | None = None
    gpus: list = field(default_factory=list)       # lista de Gpu
    opengl: float | None = None                    # 4.6, 3.3...; None si no se sabe
    vulkan: bool | None = None
    so: str = ""
    arquitectura: str = ""
    movil: bool = False                            # celular, tableta o Chromebook (N0)
    webgl2: bool | None = None

    def id(self):
        """SHA-256 (16 caracteres) de CPU, RAM redondeada, GPU, SO y arquitectura (FICHAS 3.2)."""
        base = "|".join([self.cpu, str(round(self.ram_gb or 0)), ",".join(sorted(g.nombre for g in self.gpus)),
                         self.so, self.arquitectura])
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    def como_dict(self):
        return {"contrato": HUELLA, "id": self.id(), **asdict(self)}

    @classmethod
    def desde_dict(cls, datos):
        """Lee un g7b.huella/1, o el «equipo» que escribe la sonda (g7b.medicion/1)."""
        prohibidos = PROHIBIDOS & set(datos)
        if prohibidos:
            raise ValueError(f"la huella trae datos que identifican a alguien: {sorted(prohibidos)}")
        if "gpu_cycles" in datos or "gpu_vista" in datos:
            return cls._desde_sonda(datos)
        gpus = [g if isinstance(g, Gpu) else Gpu(**{k: g.get(k) for k in ("nombre", "tipo", "vram_gb") if k in g})
                for g in datos.get("gpus", [])]
        for g in gpus:
            if g.tipo not in TIPOS_GPU:
                raise ValueError(f"tipo de GPU desconocido: {g.tipo}")
        return cls(cpu=datos.get("cpu") or "", nucleos=datos.get("nucleos"), ram_gb=datos.get("ram_gb"), gpus=gpus,
                   opengl=datos.get("opengl"), vulkan=datos.get("vulkan"), so=datos.get("so") or "",
                   arquitectura=datos.get("arquitectura") or "", movil=bool(datos.get("movil")),
                   webgl2=datos.get("webgl2"))

    @classmethod
    def _desde_sonda(cls, equipo):
        gpus = []
        for d in equipo.get("gpu_cycles") or []:
            tipo = "dedicada" if d.get("tipo") in CYCLES_DEDICADA else "desconocida"
            gpus.append(Gpu(nombre=d.get("nombre", ""), tipo=tipo))
        vista = equipo.get("gpu_vista") or {}
        if not gpus and vista.get("modelo"):
            gpus.append(Gpu(nombre=vista["modelo"], tipo=tipo_por_nombre(vista["modelo"])))
        return cls(cpu=equipo.get("cpu") or "", nucleos=equipo.get("nucleos_logicos"), ram_gb=equipo.get("ram_gb"),
                   gpus=gpus, opengl=version_opengl(vista.get("version")), so=equipo.get("so") or "",
                   arquitectura=equipo.get("arquitectura") or "")


def version_opengl(texto):
    """'4.6 (Core Profile) Mesa 24.0' → 4.6. Devuelve None si no se reconoce."""
    if not texto:
        return None
    hallado = re.match(r"\s*(\d+)\.(\d+)", str(texto))
    return float(f"{hallado.group(1)}.{hallado.group(2)}") if hallado else None


def tipo_por_nombre(nombre):
    """Una pista por el nombre, cuando no hay más datos. Nunca suple una medición."""
    n = (nombre or "").lower()
    if any(p in n for p in ("geforce", "rtx", "gtx", "quadro", "radeon rx", "radeon pro", "arc a")):
        return "dedicada"
    if any(p in n for p in ("intel", "uhd", "iris", "vega", "apple", "mali", "adreno", "llvmpipe")):
        return "integrada"
    return "desconocida"


def validar_perfiles(datos):
    """Errores de un documento g7b.perfil/1 (vacío si es válido)."""
    errores = []
    if datos.get("contrato") != PERFIL:
        errores.append(f"contrato distinto de {PERFIL}")
    vistos = set()
    for i, p in enumerate(datos.get("perfiles", [])):
        nombre = f"perfiles[{i}]"
        if p.get("nivel") not in NIVELES:
            errores.append(f"{nombre}: nivel inválido {p.get('nivel')!r}")
        if p.get("estado") not in ESTADOS_PERFIL:
            errores.append(f"{nombre}: estado inválido {p.get('estado')!r}")
        if not isinstance(p.get("ajustes"), dict):
            errores.append(f"{nombre}: faltan ajustes")
        if p.get("estado") == "confiable":
            ev = p.get("evidencia") or {}
            if ev.get("mediciones", 0) < 5 or ev.get("equipos", 0) < 3:
                errores.append(f"{nombre}: «confiable» exige 5 mediciones de 3 equipos o más")
        clave = (p.get("nivel"), p.get("programa"), p.get("version"))
        if clave in vistos:
            errores.append(f"{nombre}: repetido para {clave}")
        vistos.add(clave)
    return errores
