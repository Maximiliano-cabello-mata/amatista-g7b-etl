"""Recolector manual de Amatista. Un informe de cobertura por ejecución."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from g7b_ingesta import catalogo as cat
from geodar.__main__ import COLECTORES
from . import aframe
from . import capturar as cap


def guardar(ruta, dato):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=ruta.parent, delete=False) as f:
        temporal = Path(f.name)
        f.write(cap.canon(dato))
    try:
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)


def sondas(carpeta, lago, salida, limite):
    """Lee lotes propios y el buzón inmutable del cargador histórico, archivo por archivo."""
    conteos = Counter()
    lotes = set()

    def recibir(dato):
        try:
            cap.sonda(dato)
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            conteos["rechazados"] += 1
            return "rechazado"
        lote = cap.huella([dato])
        if lote in lotes:
            conteos["duplicados"] += 1
            return "duplicado"
        informe = cap.capturar([dato], "sonda", salida / lote, 1, lago)
        lotes.add(lote)
        conteos.update(informe["conteos"])
        return "recibido"

    if carpeta is not None:
        if not carpeta.is_dir():
            raise ValueError("carpeta de sonda inexistente")
        for ruta in sorted(carpeta.glob("*.json")):
            if ruta.stat().st_size > cap.MAX_LINEA:
                conteos["rechazados"] += 1
                continue
            try:
                dato = json.loads(ruta.read_bytes())
            except (UnicodeError, ValueError):
                conteos["rechazados"] += 1
                continue
            recibir(dato)
    if lago is not None:
        prefijo = "control/telemetria/recibos_sonda/"
        revisados = set(lago.listar(prefijo))
        procesados = 0
        for ruta in sorted(lago.listar("bronce/sonda/")):
            if not ruta.endswith(".json"):
                continue
            recibo = prefijo + cap.huella(ruta) + ".json"
            if recibo in revisados:
                continue
            if procesados >= limite:
                conteos["pendientes_buzon"] += 1
                continue
            try:
                dato = lago.leer_json(ruta)
            except (json.JSONDecodeError, UnicodeError):
                dato = None
            estado = recibir(dato)
            lago.escribir_json(recibo, {"estado": estado})
            procesados += 1
    return {"fuente": "sonda-g7b", "conteos": dict(conteos), "nada_nuevo": not lotes,
            "azure": "subida_y_lectura_verificadas" if lotes and lago is not None else
                     "sin_escritura_de_mediciones" if lago is not None else "no_solicitado"}


def recopilar(catalogo, salida, limite=1000, carpeta=None, snapshot=None, caniuse=None, lago=None, solo=None,
              entrada_aframe=None):
    if not 1 <= limite <= cap.MAX_LIMITE:
        raise ValueError("límite fuera del rango admitido")
    fuentes = cat.por_destino(catalogo, "telemetria")
    if solo and set(solo) - {f["id"] for f in fuentes}:
        raise ValueError("identificador de fuente de telemetría desconocido")
    resultados = []
    for fuente in fuentes:
        ident = fuente["id"]
        fila = {"fuente": ident, "activa": fuente["activa"]}
        resultados.append(fila)
        if not fuente["activa"] or not fuente["licencia_verificada"]:
            fila.update(estado="pendiente", motivo=fuente.get("revisar") or fuente.get("gestor") or "fuente inactiva")
            continue
        if solo and ident not in solo:
            fila["estado"] = "omitida"
            continue
        destino = salida / ident
        try:
            if ident == "sonda-g7b":
                info = sondas(carpeta, lago, destino, limite)
            elif ident == "sonda-aframe":
                info = aframe.capturar(entrada_aframe, lago, destino)
            else:
                colector = COLECTORES[fuente["colector"]]
                entrada = {"blender-open-data": snapshot, "caniuse-web3d": caniuse}.get(ident)
                info = colector(fuente, lago, destino, limite, entrada=entrada, simulacro=lago is None)
            fila["informe"] = info
            fila["estado"] = "sin_novedad" if info.get("nada_nuevo") else "recibida"
            if info.get("conteos", {}).get("rechazados") and ident in ("sonda-g7b", "sonda-aframe"):
                fila["estado"] = "parcial" if not info["nada_nuevo"] else "error"
            if info.get("en_espera"):
                fila.update(estado="en_espera", motivo=info["motivo"])
            if ident == "sonda-g7b" and carpeta is None and lago is None:
                fila.update(estado="sin_entrada", motivo="indica --sondas o usa el buzón con --azure")
        except Exception as exc:
            # Las excepciones de red/SDK pueden incluir una URL firmada.
            fila.update(estado="error", tipo_error=type(exc).__name__)
            if lago is not None and fuente["extractor"] == "telemetria":
                control = f"control/telemetria/{ident}.json"
                try:
                    estado = lago.leer_json(control, por_omision={}) or {}
                    estado.update(ultimo_error=type(exc).__name__, ultimo_error_en=datetime.now(timezone.utc).isoformat())
                    lago.escribir_json(control, estado)
                except Exception as fallo:
                    fila["error_al_guardar_estado"] = type(fallo).__name__
    informe = {"contrato": "amatista.recoleccion_telemetria/1", "fecha": datetime.now(timezone.utc).isoformat(),
               "destino": "azure" if lago is not None else "local", "fuentes": resultados,
               "conteos": dict(Counter(r["estado"] for r in resultados))}
    guardar(salida / "informe.json", informe)
    return informe


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sondas", type=Path, help="carpeta de JSON generados por la sonda propia")
    p.add_argument("--aframe", type=Path, help="archivo o carpeta de la sonda manual de A-Frame")
    p.add_argument("--snapshot", type=Path, help="ZIP oficial de Blender descargado previamente")
    p.add_argument("--caniuse", type=Path, help="data-2.0.json oficial descargado previamente")
    p.add_argument("--salida", type=Path, default=Path("captura/telemetria-amatista"))
    p.add_argument("--limite", type=int, default=1000, help="benchmarks por tanda y archivos nuevos del buzón")
    p.add_argument("--fuente", action="append", help="ID del catálogo, repetible")
    p.add_argument("--azure", action="store_true", help="persistir y verificar cada lote en el lago")
    o = p.parse_args(argv)
    if not 1 <= o.limite <= cap.MAX_LIMITE:
        p.error("límite inválido")
    lago = None
    if o.azure:
        from g7b_lago import Lago
        lago = Lago.desde_entorno()
    resultado = recopilar(cat.cargar(), o.salida, o.limite, o.sondas, o.snapshot, o.caniuse, lago, o.fuente,
                          entrada_aframe=o.aframe)
    for fila in resultado["fuentes"]:
        info = fila.get("informe", {})
        print(fila["fuente"], fila["estado"], info.get("conteos", {}), "celdas", info.get("celdas", 0),
              fila.get("tipo_error", ""))
    return int(any(k in resultado["conteos"] for k in ("error", "parcial", "sin_entrada")))
