"""Compuertas de calidad: expectativas sobre el cubo antes de dar los datos por buenos.

Es lo que en la industria se llama *data quality gate* (como Great Expectations o los tests de dbt):
una lista de **expectativas** que los datos deben cumplir; cada una pasa (`ok`), avisa (`aviso`) o
falla (`falla`). La compuerta se **aprueba** solo si ninguna falla. Mientras no apruebe, el oro no se
marca como confiable y el orquestador no avanza.

Cada expectativa dice su nombre, su estado, un detalle legible y el valor medido, y todo se guarda en
``oro/calidad.json`` para el tablero de salud. No borra ni arregla datos: solo mide y decide.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

import duckdb

from . import perfiles

OK, AVISO, FALLA = "ok", "aviso", "falla"

# Rangos razonables para descartar mediciones imposibles (no un modelo, solo cordura).
FPS_MAX = 100_000.0
FRESCURA_AVISO_DIAS = 14
FRESCURA_FALLA_DIAS = 60
VARIABLE_AVISO = 0.30  # si más del 30 % de las pruebas varía demasiado, algo anda mal en la sonda


def _check(nombre, estado, detalle, valor=None):
    return {"nombre": nombre, "estado": estado, "detalle": detalle, "valor": valor}


def _frescura(almacen, con, checks):
    hay_render = con.execute("SELECT count(*) FROM hechos_render").fetchone()[0]
    control = "control/opendata.json"
    if not almacen.existe(control):
        estado = AVISO if hay_render == 0 else FALLA
        checks.append(_check("frescura_opendata", estado, "no hay registro de descarga de Open Data"))
        return
    try:
        info = json.loads(almacen.leer(control))
        cuando = datetime.fromisoformat(info["descargado"])
        dias = (datetime.now(timezone.utc) - cuando).days
    except (ValueError, KeyError, OSError):
        checks.append(_check("frescura_opendata", AVISO, "no se pudo leer la fecha de Open Data"))
        return
    estado = OK if dias <= FRESCURA_AVISO_DIAS else (AVISO if dias <= FRESCURA_FALLA_DIAS else FALLA)
    checks.append(_check("frescura_opendata", estado, f"última copia hace {dias} días", dias))


def _consulta(con, sql):
    return con.execute(sql).fetchone()[0]


def evaluar(almacen, ahora=None):
    """Abre oro/cubo.duckdb del almacén y corre las expectativas. Devuelve el reporte y lo guarda."""
    ahora = ahora or datetime.now(timezone.utc)
    checks = []
    if not almacen.existe("oro/cubo.duckdb"):
        reporte = {"aprobado": False, "generado": ahora.isoformat(timespec="seconds"),
                   "checks": [_check("cubo_existe", FALLA, "todavía no hay cubo (corre 'construir')")]}
        almacen.escribir("oro/calidad.json", json.dumps(reporte, ensure_ascii=False, indent=2).encode())
        return reporte

    with tempfile.TemporaryDirectory(prefix="g7b_calidad_") as carpeta:
        local = os.path.join(carpeta, "cubo.duckdb")
        almacen.descargar("oro/cubo.duckdb", local)
        con = duckdb.connect(local, read_only=True)
        try:
            # Contrato: los perfiles cumplen g7b.perfil/1.
            if almacen.existe("oro/perfiles.json"):
                errores = perfiles.validar(json.loads(almacen.leer("oro/perfiles.json")))
                checks.append(_check("contrato_perfiles", OK if not errores else FALLA,
                                     "perfiles.json cumple el contrato" if not errores else f"{errores[:3]}",
                                     len(errores)))
            else:
                checks.append(_check("contrato_perfiles", FALLA, "falta oro/perfiles.json"))
            # Volumen: hay datos.
            render = _consulta(con, "SELECT count(*) FROM hechos_render")
            sonda = _consulta(con, "SELECT count(DISTINCT medicion_id) FROM hechos_medicion")
            checks.append(_check("volumen", OK if render + sonda > 0 else FALLA,
                                 f"{render} renders de Open Data y {sonda} corridas de sonda", render + sonda))
            # Frescura: Open Data no demasiado viejo.
            _frescura(almacen, con, checks)
            # Unicidad: sin render_id repetido.
            dup = _consulta(con, "SELECT count(*) - count(DISTINCT render_id) FROM hechos_render")
            checks.append(_check("sin_duplicados_render", OK if dup == 0 else FALLA,
                                 "render_id único" if dup == 0 else f"{dup} repetidos", dup))
            # Nulos: la clave de dispositivo y la escena no faltan.
            nulos = _consulta(con, "SELECT count(*) FROM hechos_render WHERE clave_dispositivo IS NULL OR escena IS NULL")
            checks.append(_check("sin_nulos_clave", OK if nulos == 0 else FALLA,
                                 "dispositivo y escena presentes" if nulos == 0 else f"{nulos} filas con nulos", nulos))
            # Rango: fps posibles (la vista 3D o la animación no pueden dar millones).
            fuera = _consulta(con, "SELECT count(*) FROM hechos_medicion WHERE unidad = 'fps' "
                                   f"AND (mediana < 0 OR mediana > {FPS_MAX})")
            checks.append(_check("rango_fps", OK if fuera == 0 else FALLA,
                                 "fps dentro de rango" if fuera == 0 else f"{fuera} fuera de rango", fuera))
            # Sintético fuera: el cubo nunca debe contener mediciones sintéticas.
            sint = _consulta(con, "SELECT count(*) FROM hechos_medicion WHERE origen = 'sintetico'")
            checks.append(_check("sintetico_excluido", OK if sint == 0 else FALLA,
                                 "sin datos sintéticos" if sint == 0 else f"{sint} filas sintéticas", sint))
            # Unicidad de perfil: un perfil por nivel y versión.
            if almacen.existe("oro/perfiles.json"):
                lista = json.loads(almacen.leer("oro/perfiles.json")).get("perfiles", [])
                claves = [(p.get("nivel"), p.get("blender")) for p in lista]
                repet = len(claves) - len(set(claves))
                checks.append(_check("perfil_unico_por_nivel", OK if repet == 0 else FALLA,
                                     "un perfil por nivel y versión" if repet == 0 else f"{repet} repetidos", repet))
            # Estabilidad: cuánta medición quedó 'variable' (señal de que la sonda necesita repetir).
            total = _consulta(con, "SELECT count(*) FROM hechos_medicion WHERE calidad IN ('ok', 'variable')")
            variable = _consulta(con, "SELECT count(*) FROM hechos_medicion WHERE calidad = 'variable'")
            razon = (variable / total) if total else 0
            checks.append(_check("estabilidad_sonda", OK if razon <= VARIABLE_AVISO else AVISO,
                                 f"{razon:.0%} de las pruebas varía más de 10 %", round(razon, 3)))
        finally:
            con.close()

    fallas = [c for c in checks if c["estado"] == FALLA]
    avisos = [c for c in checks if c["estado"] == AVISO]
    reporte = {
        "aprobado": not fallas,
        "generado": ahora.isoformat(timespec="seconds"),
        "revisadas": len(checks),
        "fallas": len(fallas),
        "avisos": len(avisos),
        "checks": checks,
    }
    almacen.escribir("oro/calidad.json", json.dumps(reporte, ensure_ascii=False, indent=2).encode())
    return reporte
