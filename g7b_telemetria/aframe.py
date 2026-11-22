"""Mediciones manuales de cadencia en una escena activa en primer plano."""
from collections import Counter
import json
import math
import re
from statistics import median

from .capturar import MAX_LINEA, canon, fecha, huella, positivo

CAMPOS = {"contrato", "fecha", "version", "entorno", "carga", "intervalos_ms", "max_llamadas", "max_triangulos"}


def resumir(dato):
    if not isinstance(dato, dict) or set(dato) != CAMPOS or dato["contrato"] != "amatista.sonda_aframe/1":
        raise ValueError("campos o contrato no admitidos")
    fecha(dato["fecha"])
    if not isinstance(dato["version"], str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", dato["version"]):
        raise ValueError("versión inesperada")
    if dato["entorno"] not in ("equipo_voluntario", "laboratorio", "github_actions"):
        raise ValueError("entorno desconocido")
    if dato["carga"] not in ("cubo_basico", "practica", "otra"):
        raise ValueError("carga desconocida")
    tiempos = dato["intervalos_ms"]
    if not isinstance(tiempos, list) or not 1 <= len(tiempos) <= 32000:
        raise ValueError("cantidad de cuadros inválida")
    for campo in ("max_llamadas", "max_triangulos"):
        if type(dato[campo]) is not int or dato[campo] < 0:
            raise ValueError("contador de geometría inválido")
    ordenados = sorted(positivo(t) for t in tiempos)
    duracion = sum(ordenados)
    if not 2990 <= duracion <= 40500:
        raise ValueError("la duración no corresponde a una ventana de la sonda")
    n = len(tiempos)
    return {"contrato": "amatista.telemetria_aframe/1", "id": huella(dato),
            **{k: dato[k] for k in ("fecha", "version", "entorno", "carga", "max_llamadas", "max_triangulos")},
            "intervalos": n, "duracion_ms": duracion, "fps_observados": 1000 * n / duracion,
            "p50_ms": median(ordenados), "p95_ms": ordenados[math.ceil(0.95 * n) - 1],
            "estado": "revision", "motivo": "ventana_individual"}


def capturar(entrada, lago, salida):
    if entrada is None:
        return {"en_espera": True, "motivo": "esperando archivo manual de A-Frame"}
    if not entrada.exists():
        raise ValueError("ruta de la sonda A-Frame inexistente")
    rutas = sorted(entrada.glob("*.json")) if entrada.is_dir() else [entrada]
    salida.mkdir(parents=True, exist_ok=True)
    conteos = Counter()
    vistas = set()
    for ruta in rutas:
        try:
            if ruta.stat().st_size > MAX_LINEA:
                raise ValueError("archivo demasiado grande")
            dato = json.loads(ruta.read_bytes())
            fila = resumir(dato)
        except (ValueError, TypeError, OverflowError):
            conteos["rechazados"] += 1
            continue
        lote = fila["id"]
        if lote in vistas:
            conteos["duplicados"] += 1
            continue
        vistas.add(lote)
        if lago is not None:
            for clave, valor in [(f"bronce/telemetria/sonda-aframe/{lote}.jsonl.gz", dato),
                                 (f"plata/telemetria_web/sonda-aframe/{lote}.jsonl.gz", fila)]:
                lago.subir_jsonl_gz(clave, [valor])
                if huella(lago.leer_jsonl_gz(clave)) != huella([valor]):
                    raise RuntimeError("falló la verificación de la ventana A-Frame")
        (salida / (lote + ".jsonl")).write_bytes(canon(fila) + b"\n")
        conteos["registros_validos"] += 1
        conteos["revision"] += 1
    return {"fuente": "sonda-aframe", "conteos": dict(conteos), "nada_nuevo": not vistas,
            "azure": "subida_y_lectura_verificadas" if vistas and lago is not None else
                     "sin_escritura_de_mediciones" if lago is not None else "no_solicitado"}
