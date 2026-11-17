"""Paquete de conocimiento del kernel (g7b.geoda.paquete/1): la única entrada del núcleo de Geoda.

Reúne en un solo documento versionado, con hashes, todo lo que el núcleo necesita para decidir sin
red y sin el cubo. Es lo que se publica:

    perfiles      g7b.perfil/1, solo de mediciones DIRECTAS (estudiantes y laboratorios escolares,
                  con consentimiento). Sin directas suficientes, las reglas base.
    factores      cuánto rinde cada nivel frente al N2, por serie de Blender y escena, de mediciones
                  RELATIVAS (Blender Open Data). Sirven para estimar, nunca se presentan como medidas.
    citas         la página del manual que explica cada ajuste del plan, por versión e idioma.
    hardware      el estándar g7b.hardware/1 (fuentes/hardware.yml), para normalizar sin red.
    niveles       las reglas N0–N4 de Geoda.
    operaciones   el catálogo de operaciones (g7b.operacion/1).

Privacidad: solo agregados. Un perfil medido con menos de 5 equipos no se publica (queda la regla
base), y el paquete nunca lleva huellas, mediciones individuales ni datos de equipos.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

import yaml

from . import VERSION, costos, niveles, perfiles
from .contratos import NIVELES

CONTRATO = "g7b.geoda.paquete/1"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CITAS = os.path.join(RAIZ, "fuentes", "citas_manual.yml")
RUTA_HARDWARE = os.path.join(RAIZ, "fuentes", "hardware.yml")
VERSIONES_MANUAL = ("5.2", "4.5", "3.6")
MIN_EQUIPOS_PUBLICO = 5        # agregados de 5 equipos o más (misma regla que amatista-agregados)
MIN_MEDICIONES_FACTOR = 30     # por celda, en el nivel y en la referencia N2
NIVEL_REFERENCIA = "N2"


def _canon(dato):
    return json.dumps(dato, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def huella(dato):
    return hashlib.sha256(_canon(dato)).hexdigest()


def _tiene(con, vista):
    return bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
                            [vista]).fetchone()[0])


def factores_relativos(con, minimo=MIN_MEDICIONES_FACTOR):
    """Mediana de render de cada nivel dividida entre la del N2, en la misma serie y escena.

    Solo GPU integradas y dedicadas con nivel de confianza alta o media: sin Apple Silicon, sin GPU de
    servidor y sin las dedicadas sin VRAM conocida, que sesgarían la comparación.
    """
    if con is None or not _tiene(con, "v_relativas"):
        return []
    # Desde g7b.cubo/3 cada métrica dice su naturaleza: los factores son de VELOCIDAD (render), no de
    # rendimiento (fluidez de la vista 3D). En un cubo /2 todo lo de Open Data ya era velocidad.
    columnas = {c[0] for c in con.execute("SELECT column_name FROM information_schema.columns "
                                          "WHERE table_name = 'v_relativas'").fetchall()}
    solo_velocidad = "AND naturaleza = 'velocidad'" if "naturaleza" in columnas else ""
    filas = con.execute(f"""
        SELECT nivel, serie, escena, count(*) AS n, median(valor) AS mediana
        FROM v_relativas
        WHERE fuente = 'blender-open-data' AND mide = 'gpu' AND nivel IS NOT NULL
          AND gpu_clase IN ('integrada', 'dedicada') AND nivel_confianza IN ('alta', 'media') {solo_velocidad}
        GROUP BY ALL""").fetchall()
    celdas = {(nivel, serie, escena): (n, mediana) for nivel, serie, escena, n, mediana in filas}
    salida = []
    for (nivel, serie, escena), (n, mediana) in sorted(celdas.items()):
        referencia = celdas.get((NIVEL_REFERENCIA, serie, escena))
        if not referencia or n < minimo or referencia[0] < minimo or not referencia[1]:
            continue
        salida.append({"nivel": nivel, "serie": serie, "escena": escena, "mediciones": n,
                       "mediciones_referencia": referencia[0], "mediana_samples_min": round(mediana, 1),
                       "factor_frente_a_N2": round(mediana / referencia[1], 3),
                       "clase_dato": "relativa", "naturaleza": "velocidad", "fuente": "blender-open-data",
                       "nota": "render de Cycles en equipos públicos; no es la fluidez de la vista 3D"})
    return salida


def perfiles_publicos(con):
    """g7b.perfil/1 solo con directas, y sin perfiles medidos de menos de 5 equipos."""
    mediciones, sin_nivel = perfiles.leer_cubo(con) if con is not None and _tiene(con, "v_mediciones_aceptadas") else ([], 0)
    documento = perfiles.generar(mediciones, sin_nivel)
    publicos = []
    retirados = 0
    for p in documento["perfiles"]:
        if p["estado"] != "base" and (p.get("evidencia") or {}).get("equipos", 0) < MIN_EQUIPOS_PUBLICO:
            retirados += 1
            continue
        publicos.append(p)
    cubiertos = {p["nivel"] for p in publicos}
    publicos += [perfiles._perfil_base(n) for n in NIVELES if n not in cubiertos]
    publicos.sort(key=lambda p: (NIVELES.index(p["nivel"]), str(p["version"])))
    documento["perfiles"] = publicos
    documento["retirados_por_privacidad"] = retirados
    return documento


def citas(inventarios=None, aceptadas=None, versiones=VERSIONES_MANUAL):
    """Cita de cada ajuste por versión e idioma, marcando cómo se verificó que la página existe.

    inventarios: {versión: set(rutas)} de los objects.inv (en Actions; sin red, None).
    aceptadas:   set de URL que la araña de documentación ya aceptó (conocimiento de G7B).
    """
    with open(RUTA_CITAS, encoding="utf-8") as archivo:
        tabla = yaml.safe_load(archivo)

    def resolver(entrada):
        salida = []
        for version in versiones:
            for idioma in tabla["idiomas"]:
                url = tabla["base"].format(idioma=idioma, version=version) + entrada["ruta"]
                if inventarios and entrada["ruta"] in inventarios.get(version, set()):
                    verificada = "inventario"
                elif aceptadas and url.replace(f"/{idioma}/", "/en/") in aceptadas:
                    verificada = "conocimiento_g7b"
                else:
                    verificada = "sin_verificar"
                salida.append({"version": version, "idioma": idioma, "url": url, "verificada": verificada})
        return {**{k: v for k, v in entrada.items() if k != "ruta"}, "ruta": entrada["ruta"], "enlaces": salida}

    return {
        "licencia_manual": "CC-BY-SA-4.0 (solo enlaces y títulos; el texto no se copia)",
        "acciones": {ruta: [resolver(e) for e in entradas] for ruta, entradas in tabla["citas"].items()},
        "generales": {nivel: [resolver(e) for e in entradas] for nivel, entradas in tabla["generales"].items()},
    }


def inventarios_manual(versiones=VERSIONES_MANUAL, idioma="en", abrir=None):
    """{versión: set(rutas .html)} desde los objects.inv del manual (una descarga por versión).

    Si una versión no responde, queda fuera y sus citas salen «sin_verificar»: no se inventa.
    """
    import urllib.request

    from motor_extraccion.inventario_sphinx import leer as leer_inventario

    abrir = abrir or (lambda url: urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "g7b-geoda/1"}), timeout=30).read())
    salida = {}
    for version in versiones:
        try:
            contenido = abrir(f"https://docs.blender.org/manual/{idioma}/{version}/objects.inv")
            salida[version] = set(leer_inventario(contenido)["paginas"])
        except Exception as error:  # noqa: BLE001 — una versión caída no tumba el paquete
            print(f"objects.inv {version}: {error}")
    return salida


def hardware_publico():
    with open(RUTA_HARDWARE, encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)
    return {"estandar": "g7b.hardware/1", "version": datos["version"], "gpus": datos["gpus"], "cpus": datos["cpus"]}


def construir(con=None, cubo=None, inventarios=None, aceptadas=None, ahora=None):
    """El paquete completo. con: conexión de solo lectura al cubo g7b.cubo/2 o /3 (o None: solo reglas)."""
    secciones = {
        "perfiles": perfiles_publicos(con),
        "factores": factores_relativos(con),
        "citas": citas(inventarios, aceptadas),
        "hardware": hardware_publico(),
        "niveles": {"reglas": [linea.strip() for linea in niveles.__doc__.splitlines()
                               if linea.strip().startswith("N")],
                    "opengl_blender_actual": niveles.OPENGL_BLENDER_ACTUAL},
        "operaciones": costos.catalogo(),
    }
    generado = (ahora or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    contenido = {k: huella(v) for k, v in secciones.items()}
    paquete = {
        "contrato": CONTRATO,
        "geoda": VERSION,
        "generado": generado,
        "version": generado.replace("-", "").replace(":", "")[:15] + "Z-" + huella(contenido)[:12],
        "cubo": cubo or {"contrato": None, "nota": "sin cubo: solo reglas base"},
        "evidencia": {
            "perfiles_medidos": sum(1 for p in secciones["perfiles"]["perfiles"] if p["estado"] != "base"),
            "factores": len(secciones["factores"]),
            "citas_verificadas": sum(1 for e in _enlaces(secciones["citas"]) if e["verificada"] != "sin_verificar"),
            "citas_total": sum(1 for _ in _enlaces(secciones["citas"])),
        },
        "privacidad": {"min_equipos_por_perfil": MIN_EQUIPOS_PUBLICO,
                       "contiene": "solo agregados: sin huellas, sin mediciones individuales"},
        "licencia": {"codigo": "por_definir", "datos": "por_definir",
                     "atribuciones": ["Blender Open Data (CC0 1.0), opendata.blender.org",
                                      "Manual de Blender (CC BY-SA 4.0), docs.blender.org: solo enlaces"]},
        "huellas": contenido,
        **secciones,
    }
    errores = validar(paquete)
    if errores:
        raise ValueError("paquete inválido: " + "; ".join(errores))
    return paquete


def _enlaces(seccion_citas):
    for grupo in ("acciones", "generales"):
        for entradas in seccion_citas[grupo].values():
            for e in entradas:
                yield from e["enlaces"]


PROHIBIDO_EN_PUBLICO = ("huella_equipo", '"equipo":', "gpu_cycles", "nombre_equipo", "hostname")


def validar(paquete):
    """Lo mínimo que cualquier lector del paquete (o una implementación del núcleo) puede suponer."""
    errores = []
    if paquete.get("contrato") != CONTRATO:
        errores.append("contrato desconocido")
    for k in ("perfiles", "factores", "citas", "hardware", "niveles", "operaciones"):
        if k not in paquete:
            errores.append(f"falta la sección {k}")
        elif paquete.get("huellas", {}).get(k) != huella(paquete[k]):
            errores.append(f"la sección {k} no coincide con su huella")
    if not errores:
        if {p["nivel"] for p in paquete["perfiles"]["perfiles"]} != set(NIVELES):
            errores.append("falta un perfil para algún nivel")
        for f in paquete["factores"]:
            if f.get("clase_dato") != "relativa":
                errores.append("un factor no está marcado como relativo")
            if f.get("naturaleza", "velocidad") != "velocidad":
                errores.append("un factor no es de velocidad: el rendimiento sale de las directas")
        texto = _canon(paquete).decode("utf-8")
        for prohibido in PROHIBIDO_EN_PUBLICO:
            if prohibido in texto:
                errores.append(f"el paquete público contiene «{prohibido}»")
    return errores


def leer(ruta_o_dict):
    paquete = ruta_o_dict
    if not isinstance(paquete, dict):
        with open(ruta_o_dict, encoding="utf-8") as archivo:
            paquete = json.load(archivo)
    errores = validar(paquete)
    if errores:
        raise ValueError("paquete inválido: " + "; ".join(errores))
    return paquete
