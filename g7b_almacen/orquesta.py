"""Orquestador por fases: trabaja 24/7, pero por pasos, no todo de un golpe.

La idea que pediste: un latido corre seguido (cada hora, por ejemplo), y en cada latido avanza **un
solo paso acotado**. Cada fase se enciende solo cuando tiene trabajo, lo hace, y se apaga pasándole
el turno a la siguiente. Entre una fase y la siguiente hay una **compuerta**: hasta que los datos no
pasan la calidad, el oro no se marca como confiable.

    ingesta  ──►  cubo  ──►  calidad (compuerta)  ──►  oro confiable
    (trae lo    (bronce →   (expectativas; si algo     (perfiles y
     nuevo)      plata →     falla, no avanza y          tablero listos
                 oro)        lo dice en oro/calidad)     para usarse)

El estado vive en ``control/orquesta.json``: qué fase sigue, qué está «sucio» (pendiente de rehacer)
y si el oro es confiable. Así el proceso se puede parar y seguir sin perder el hilo, y nunca rehace
algo que ya está al día. El lado de texto (arañas → embudo → ``control/embudo.json``) es su propia
fase anterior, con su propio interruptor; aquí se orquesta la columna medición → cubo → compuerta.
"""
import json
from datetime import datetime, timezone

from . import calidad, cubo, opendata

CONTROL = "control/orquesta.json"
INGESTA_DIAS = 7       # Open Data se revisa como mucho una vez por semana (publican a diario, no cambia tanto)
REINTENTO_MIN = 30     # si la ingesta falla (sin red), se hace a un lado este rato para no frenar el cubo

ESTADO_INICIAL = {"fase": "ingesta", "oro_confiable": False,
                  "sucio": {"bronce": False, "oro": False}, "historia": {}}


def _cargar(almacen):
    if almacen.existe(CONTROL):
        try:
            estado = json.loads(almacen.leer(CONTROL))
            estado.setdefault("sucio", {"bronce": False, "oro": False})
            estado.setdefault("historia", {})
            return estado
        except (ValueError, OSError):
            pass
    return json.loads(json.dumps(ESTADO_INICIAL))


def _guardar(almacen, estado, ahora):
    estado["actualizado"] = ahora.isoformat(timespec="seconds")
    almacen.escribir(CONTROL, json.dumps(estado, ensure_ascii=False, indent=2).encode())


def marcar_bronce(almacen, ahora=None):
    """Lo llama quien agrega datos crudos (la sonda) para que el cubo se reconstruya en el próximo latido."""
    ahora = ahora or datetime.now(timezone.utc)
    estado = _cargar(almacen)
    estado["sucio"]["bronce"] = True
    _guardar(almacen, estado, ahora)
    return estado


def _ingesta_pendiente(almacen):
    if not almacen.existe("control/opendata.json"):
        return True
    try:
        info = json.loads(almacen.leer("control/opendata.json"))
        dias = (datetime.now(timezone.utc) - datetime.fromisoformat(info["descargado"])).days
        return dias >= INGESTA_DIAS
    except (ValueError, KeyError, OSError):
        return True


def _ingesta_debe_correr(almacen, estado, ahora):
    """Pendiente, salvo que acabe de fallar: tras un error espera un rato y deja correr las demás fases."""
    if not _ingesta_pendiente(almacen):
        return False
    error_en = estado.get("ingesta_error_en")
    if error_en:
        try:
            minutos = (ahora - datetime.fromisoformat(error_en)).total_seconds() / 60
            if minutos < REINTENTO_MIN:
                return False
        except ValueError:
            pass
    return True


def paso(almacen, sesion=None, ahora=None, salida=print):
    """Avanza el pipeline un paso acotado. Devuelve qué fase corrió y su resultado."""
    ahora = ahora or datetime.now(timezone.utc)
    estado = _cargar(almacen)
    sucio = estado["sucio"]
    hay_bronce = bool(almacen.listar("bronce/"))

    def registrar(fase, resultado):
        estado["fase"] = fase
        estado["historia"][fase] = {"cuando": ahora.isoformat(timespec="seconds"), "resultado": resultado}
        _guardar(almacen, estado, ahora)
        return {"fase": fase, "hizo": True, "resultado": resultado, "oro_confiable": estado["oro_confiable"]}

    # Fase 1: ingesta. Trae Open Data si falta o ya tiene una semana. Si falla, se hace a un lado
    # (REINTENTO_MIN) para no frenar el cubo ni la compuerta con los datos que ya hay.
    if _ingesta_debe_correr(almacen, estado, ahora):
        try:
            ruta = opendata.descargar(almacen, sesion=sesion, salida=salida)
            if ruta:
                sucio["bronce"] = True
            estado["ingesta_error_en"] = None
            resultado = {"descargado": bool(ruta), "ruta": ruta}
        except Exception as error:  # la red puede fallar; el latido no se cae
            salida(f"ingesta: no se pudo descargar Open Data ({type(error).__name__}: {str(error)[:120]})")
            estado["ingesta_error_en"] = ahora.isoformat(timespec="seconds")
            resultado = {"descargado": False, "error": f"{type(error).__name__}"}
        return registrar("ingesta", resultado)

    # Fase 2: cubo. Reconstruye si hay crudo nuevo o si todavía no hay oro.
    if hay_bronce and (sucio["bronce"] or not almacen.existe("oro/resumen.json")):
        datos = cubo.construir(almacen, salida=salida, ahora=ahora)
        sucio["bronce"] = False
        sucio["oro"] = True
        return registrar("cubo", {"conteos": datos["conteos"], "perfiles": datos.get("perfiles", 0)})

    # Fase 3: compuerta de calidad. Decide si el oro es confiable.
    if hay_bronce and (sucio["oro"] or not almacen.existe("oro/calidad.json")):
        reporte = calidad.evaluar(almacen, ahora=ahora)
        sucio["oro"] = False
        estado["oro_confiable"] = reporte["aprobado"]
        salida(f"calidad: {'APROBADA' if reporte['aprobado'] else 'NO aprobada'} "
               f"({reporte.get('fallas', 0)} fallas, {reporte.get('avisos', 0)} avisos)")
        return registrar("calidad", {"aprobado": reporte["aprobado"], "fallas": reporte.get("fallas", 0),
                                      "avisos": reporte.get("avisos", 0)})

    # Nada pendiente: todo al día.
    estado["fase"] = "al_dia"
    _guardar(almacen, estado, ahora)
    razon = "sin datos en bronce todavía" if not hay_bronce else "todo al día"
    salida(f"orquesta: {razon}")
    return {"fase": "al_dia", "hizo": False, "razon": razon, "oro_confiable": estado["oro_confiable"]}
