"""Plata: las mediciones de la sonda (``g7b.medicion/1``) como filas limpias.

Una medición de la sonda trae varias pruebas por perfil; aquí cada prueba es una fila. Lo que la
sonda marcó como ``no_disponible`` se conserva con su motivo (sirve para saber qué no se puede hacer
en un equipo), pero no cuenta para medianas ni perfiles.

Controles de calidad (PLAN, sección 2), que van en la columna ``calidad``:

    ok                  la prueba se repitió y varía 10 % o menos
    variable            varía más de 10 %: no se usa para perfiles hasta repetirla
    una_repeticion      una sola repetición: se guarda, pero no basta
    no_disponible       la prueba no se pudo hacer
"""
import hashlib
import json

CONTRATO = "g7b.medicion/1"
VARIACION_MAX = 0.10


def leer_medicion(datos):
    medicion = json.loads(datos)
    if medicion.get("contrato") != CONTRATO:
        raise ValueError(f"contrato {medicion.get('contrato')!r}, se esperaba {CONTRATO}")
    return medicion


def _calidad(registro):
    if registro.get("no_disponible"):
        return "no_disponible"
    if len(registro.get("valores") or []) < 2:
        return "una_repeticion"
    if (registro.get("variacion") or 0) > VARIACION_MAX:
        return "variable"
    return "ok"


def filas_medicion(medicion, archivo="", origen=None):
    """Filas para ``plata/sonda/medicion.parquet``."""
    equipo = medicion.get("equipo") or {}
    blender = medicion.get("blender") or {}
    escena = medicion.get("escena") or {}
    version = str(blender.get("version") or "")
    medicion_id = hashlib.sha256(
        f"{archivo}|{medicion.get('fecha')}|{equipo.get('huella')}".encode()).hexdigest()[:20]
    gpus = equipo.get("gpu_cycles") or []
    from .opendata import version_corta  # misma regla de versión en los dos insumos

    for registro in medicion.get("resultados") or []:
        yield {
            "medicion_id": medicion_id,
            "archivo": archivo,
            "fecha": str(medicion.get("fecha") or "")[:10] or None,
            "origen": origen or medicion.get("origen") or "pc",
            "sonda": str(medicion.get("sonda") or ""),
            "completa": bool(medicion.get("completa")),
            "huella": str(equipo.get("huella") or ""),
            "nivel": str(equipo.get("nivel") or ""),
            "nivel_estimado": bool(equipo.get("nivel_estimado", True)),
            "so": str(equipo.get("so") or ""),
            "arquitectura": str(equipo.get("arquitectura") or ""),
            "cpu": str(equipo.get("cpu") or ""),
            "nucleos_logicos": int(equipo.get("nucleos_logicos") or 0),
            "ram_gb": float(equipo.get("ram_gb") or 0),
            "gpu_vista": str(equipo.get("gpu_vista") or ""),
            "gpu_cycles": " + ".join(sorted(str(g.get("nombre", "")) for g in gpus if isinstance(g, dict))),
            "version_blender": version,
            "version_corta": version_corta(version),
            "sin_ventana": bool(blender.get("sin_ventana")),
            "escena": str(escena.get("nombre") or ""),
            "perfil": registro.get("perfil") or "",
            "prueba": str(registro.get("prueba") or ""),
            "metrica": str(registro.get("metrica") or ""),
            "unidad": str(registro.get("unidad") or ""),
            "mediana": registro.get("mediana"),
            "variacion": registro.get("variacion"),
            "repeticiones": len(registro.get("valores") or []),
            "calidad": _calidad(registro),
            "motivo": registro.get("no_disponible") or "",
        }


