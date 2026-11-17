"""Bronce → plata: cada registro pasa por el embudo (embudo.py), y se vuelve a pasar si las reglas cambian.

    python -m g7b_ingesta.procesar
    python -m g7b_ingesta.procesar --simulacro
    python -m g7b_ingesta.procesar --fuente blender-manual --forzar      # reevaluar una fuente
    python -m g7b_ingesta.procesar --lote bronce/arxiv-cs-gr/2026-11-11/  # reevaluar un lote

Reprocesamiento: cada archivo de bronce guarda con qué reglas se evaluó (su «huella de reglas»: la
versión del embudo, sus umbrales, la taxonomía y la entrada del catálogo de su fuente). Si alguna
cambia, el archivo se vuelve a evaluar solo en la siguiente pasada. Así un documento rechazado ayer
puede aceptarse hoy si el proyecto amplía sus preguntas o corrige un filtro. Bronce nunca se borra
ni se sobrescribe: es la fuente de toda reevaluación.

Volver a evaluar un archivo no duplica nada: antes se descuentan de los conteos y del índice de
repetidos los resultados que ese mismo archivo dejó la vez anterior, y sus salidas de plata se
reemplazan (las que quedan vacías se escriben vacías: la firma del lago no permite borrar).

Salidas, por archivo de bronce procesado:
    plata/aceptados/<fuente>/<fecha>/<archivo>.jsonl.gz    documento + resultado del embudo
    plata/revision/<fuente>/<fecha>/<archivo>.jsonl.gz     esperan a una persona
    plata/rechazados/<fuente>/<fecha>/<archivo>.jsonl.gz   solo url, etapa, motivos y puntajes (sin texto)
Control:
    control/procesados.json       qué archivos de bronce ya pasaron
    control/indice_embudo.json    huellas de lo aceptado (para detectar repetidos)
    control/embudo.json           conteos por fuente y etapa (para el tablero de salud)
"""
import argparse
import json
import posixpath
import sys
from collections import Counter
from datetime import datetime, timezone

from g7b_lago import Lago

from . import catalogo as cat
from . import texto as tx
from .embudo import ACEPTADO, RECHAZADO, REVISION, UMBRALES, VERSION_EMBUDO, Indice, evaluar

PROCESADOS = "control/procesados.json"
INDICE = "control/indice_embudo.json"
CONTEOS = "control/embudo.json"
EXCLUIR = ("bronce/sonda/", "bronce/telemetria/")  # recorrido numérico separado
FRAGMENTO_METADATOS = 300
PUBLICADOS = "control/publicados.json"
CARPETAS = {ACEPTADO: "aceptados", REVISION: "revision", RECHAZADO: "rechazados"}
# Arañas de Zyte y la fuente del catálogo que alimentan (cuando el registro no trae una conocida).
ARANAS = {"blender_docs": "blender-manual", "manual_sphinx": None, "paginas": None}


def fuente_de(ruta, registro, fuentes=None):
    """La fuente del catálogo de un registro: la que trae, un alias suyo o la de su ruta."""
    declarada = registro.get("fuente")
    if fuentes is not None and declarada and declarada not in fuentes:
        alias = next((f["id"] for f in fuentes.values() if declarada in (f.get("alias") or [])), None)
        declarada = alias or _fuente_de_ruta(ruta) or declarada
    return declarada or _fuente_de_ruta(ruta)


def _fuente_de_ruta(ruta):
    partes = ruta.split("/")
    if len(partes) > 2 and partes[1] == "zyte":
        return ARANAS.get(partes[2]) or partes[2]
    return partes[1] if len(partes) > 1 else ""


# Lo de una fuente que cambia el resultado del embudo. El resto (sensor, frecuencia, argumentos de la
# araña, nombre) es operación: cambiarlo no debe volver a evaluar todo lo que ya trajo.
REGLAS_DE_FUENTE = ("activa", "licencia", "licencia_verificada", "modo", "dominios", "preguntas", "umbrales",
                    "destino", "tipo", "programa")


def huella_reglas(fuente, taxonomia):
    """Con qué reglas se evalúa una fuente. Si cambia, sus archivos de bronce se vuelven a evaluar."""
    import hashlib

    reglas = {k: fuente[k] for k in REGLAS_DE_FUENTE if k in fuente} if fuente else fuente
    base = {"embudo": VERSION_EMBUDO, "umbrales": UMBRALES, "taxonomia": taxonomia, "fuente": reglas}
    return hashlib.sha256(json.dumps(base, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def _salidas(ruta):
    partes = ruta.split("/")
    destino = "/".join(partes[1:-1])  # <fuente>/<fecha> (o zyte/<araña>/<fecha>)
    return {estado: f"plata/{carpeta}/{destino}/{posixpath.basename(ruta)}" for estado, carpeta in CARPETAS.items()}


def _retirar_anterior(lago, ruta, indice, conteos):
    """Descuenta lo que este archivo dejó la vez anterior (conteos e índice). Devuelve qué salidas existían."""
    existian = []
    for estado, salida in _salidas(ruta).items():
        if not lago.existe(salida):
            continue
        existian.append(salida)
        for doc in lago.leer_jsonl_gz(salida):
            embudo = doc.get("embudo") or {}
            clave = f"{embudo.get('estado')}:{embudo.get('etapa')}"
            por_fuente = conteos.get(doc.get("fuente"), {})
            if por_fuente.get(clave):
                por_fuente[clave] -= 1
                if not por_fuente[clave]:
                    del por_fuente[clave]
                if not por_fuente:
                    conteos.pop(doc.get("fuente"), None)
            if estado == ACEPTADO:
                indice.quitar(embudo.get("huella"), embudo.get("simhash"))
    return existian


def es_documento(ruta, fuentes):
    """El embudo es para documentos: catálogos, telemetría y señales siguen su propio camino (Geodar)."""
    partes = ruta.split("/")
    if len(partes) < 3 or partes[1] == "zyte":
        return True
    fuente = fuentes.get(partes[1])
    return fuente is None or cat.destino(fuente) == "documentos"


def a_documento(registro, lago, fuente):
    """Convierte un registro crudo (de cualquier extractor) en {url, titulo, texto, metadatos}."""
    url = registro.get("url") or registro.get("enlace")
    metadatos = {k: registro[k] for k in ("fecha", "autores", "autor", "autor_respuesta", "etiquetas", "categorias")
                 if registro.get(k)}
    if registro.get("duplicado_de"):  # la araña ya vio esta página en otra ruta: solo anota el alias
        texto = ""
        metadatos.update({k: registro[k] for k in ("duplicado_de", "version", "seccion", "ruta", "canonica")
                          if registro.get(k)})
    elif "contenido" in registro:  # araña estructurada de manuales (manual_sphinx, blender_docs)
        texto = registro["contenido"]
        metadatos.update({k: registro[k] for k in ("version", "seccion", "programa", "operadores_bpy", "ruta",
                                                     "canonica") if registro.get(k)})
        if registro.get("propiedades"):
            metadatos["propiedades"] = len(registro["propiedades"])
    elif "html" in registro:
        texto = tx.extraer_html(registro["html"], url)
    elif "texto_html" in registro:
        texto = tx.extraer_html(registro["texto_html"], url)
        metadatos["puntaje_foro"] = registro.get("puntaje", 0)
        metadatos["respuesta_aceptada"] = registro.get("respuesta_aceptada", False)
    elif "resumen" in registro:
        texto = tx.extraer_html(registro["resumen"]) if "<" in (registro["resumen"] or "") else registro["resumen"]
    elif registro.get("archivo", "").endswith(".pdf"):
        texto = tx.extraer_pdf(lago.contenedor.download_blob(registro["archivo"]).readall())
    else:
        texto = registro.get("texto") or registro.get("descripcion") or ""
    if fuente and fuente.get("modo") == "solo_metadatos" and len(texto) > UMBRALES["resumen_metadatos_max"]:
        texto = texto[:FRAGMENTO_METADATOS]  # derechos reservados: solo un fragmento para clasificar
        metadatos["texto_recortado"] = True
    return {"url": url, "titulo": registro.get("titulo") or "", "texto": texto, "metadatos": metadatos}


def pendientes_de(lago, fuentes, taxonomia, procesados, solo_fuente=None, lote=None, forzar=False,
                  reevaluar=True):
    """{ruta: motivo} de los archivos de bronce que toca evaluar ahora."""
    salida = {}
    for r in lago.listar("bronce/"):
        if not r.endswith(".jsonl.gz") or r.startswith(EXCLUIR) or not es_documento(r, fuentes):
            continue
        id_fuente = _fuente_de_ruta(r)
        if solo_fuente and id_fuente != solo_fuente:
            continue
        if lote and not r.startswith(lote):
            continue
        previo = procesados.get(r)
        if previo is None:
            salida[r] = "nuevo"
        elif forzar:
            salida[r] = "forzado"
        elif reevaluar and previo.get("reglas") != huella_reglas(fuentes.get(id_fuente), taxonomia):
            salida[r] = "reglas cambiaron"
    return salida


def procesar(lago, catalogo, taxonomia, simulacro=False, salida=print, solo_fuente=None, lote=None,
             forzar=False, reevaluar=True):
    fuentes = cat.por_id(catalogo)
    procesados = lago.leer_json(PROCESADOS, por_omision={}) or {}
    indice = Indice.desde_dict(lago.leer_json(INDICE))
    conteos = lago.leer_json(CONTEOS, por_omision={}) or {}
    publicados = lago.leer_json(PUBLICADOS, por_omision={}) or {}
    por_procesar = pendientes_de(lago, fuentes, taxonomia, procesados, solo_fuente, lote, forzar, reevaluar)
    pendientes = list(por_procesar)
    motivos_pasada = Counter(por_procesar.values())
    if motivos_pasada:
        salida("Archivos por evaluar: " + ", ".join(f"{v} {k}" for k, v in motivos_pasada.most_common()))
    total = Counter()
    motivos = Counter()   # (estado, etapa, motivo) -> cuántos: para ajustar umbrales con datos
    ejemplos = {}
    for ruta in sorted(pendientes):
        existian = [] if simulacro else _retirar_anterior(lago, ruta, indice, conteos)
        grupos = {ACEPTADO: [], REVISION: [], RECHAZADO: []}
        for registro in lago.leer_jsonl_gz(ruta):
            id_fuente = fuente_de(ruta, registro, fuentes)
            fuente = fuentes.get(id_fuente)
            if fuente is None:
                resultado = {"estado": RECHAZADO, "etapa": "entrada", "motivos": [f"fuente desconocida: {id_fuente}"]}
                doc = {"url": registro.get("url") or registro.get("enlace")}
            else:
                doc = a_documento(registro, lago, fuente)
                r = evaluar(doc, fuente, taxonomia, indice)
                if r.estado == ACEPTADO:
                    indice.agregar(r.huella, r.simhash)
                resultado = r.como_dict()
            salida_doc = {"fuente": id_fuente, "url": doc.get("url"), "origen": ruta, "embudo": resultado}
            if resultado["estado"] != RECHAZADO:
                salida_doc.update({"titulo": doc.get("titulo"), "texto": doc.get("texto"),
                                   "metadatos": doc.get("metadatos"),
                                   "licencia": (fuente or {}).get("licencia"), "modo": (fuente or {}).get("modo")})
            grupos[resultado["estado"]].append(salida_doc)
            clave = f"{resultado['estado']}:{resultado['etapa']}"
            conteos.setdefault(id_fuente, {}).setdefault(clave, 0)
            conteos[id_fuente][clave] += 1
            total[resultado["estado"]] += 1
            if resultado["estado"] != ACEPTADO:
                for motivo in resultado.get("motivos") or ["sin motivo"]:
                    llave = (resultado["estado"], resultado["etapa"], _sin_numeros(motivo))
                    motivos[llave] += 1
                    ejemplos.setdefault(llave, doc.get("url"))
        resumen = {estado: len(docs) for estado, docs in grupos.items()}
        salida(f"{ruta} ({por_procesar[ruta]}): " + ", ".join(f"{k} {v}" for k, v in resumen.items()))
        if simulacro:
            continue
        salidas = _salidas(ruta)
        for estado, docs in grupos.items():
            # Una salida que existía y ahora queda vacía se reemplaza por una vacía (no se puede borrar).
            if docs or salidas[estado] in existian:
                lago.subir_bytes(salidas[estado], _jsonl_gz(docs), tipo="application/x-ndjson",
                                 codificacion="gzip", sobrescribir=True)
        if salidas[ACEPTADO] in publicados:
            del publicados[salidas[ACEPTADO]]  # cambió: publicar la vuelve a leer (guardar es idempotente)
            lago.escribir_json(PUBLICADOS, publicados)
        # Orden pensado para interrupciones: primero índice y conteos, al final «procesado». Si se corta
        # antes, el archivo se reevalúa y _retirar_anterior descuenta lo que alcanzó a dejar.
        lago.escribir_json(INDICE, indice.como_dict())
        lago.escribir_json(CONTEOS, conteos)
        previo = procesados.get(ruta) or {}
        procesados[ruta] = {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"), **resumen,
                            "reglas": huella_reglas(fuentes.get(_fuente_de_ruta(ruta)), taxonomia),
                            "evaluaciones": previo.get("evaluaciones", 1 if previo else 0) + 1}
        lago.escribir_json(PROCESADOS, procesados)
    if motivos:
        salida("Motivos (rechazo y revisión), de más a menos frecuente:")
        for (estado, etapa, motivo), n in motivos.most_common():
            salida(f"  {n:4d}  {estado:9s} {etapa:11s} {motivo}   ej.: {ejemplos[(estado, etapa, motivo)]}")
    return dict(total)


def _sin_numeros(motivo):
    """Agrupa motivos que solo cambian en un número ("12 palabras", "30 palabras")."""
    import re

    return re.sub(r"\d+", "N", motivo)


def _jsonl_gz(docs):
    import gzip
    import io

    bufer = io.BytesIO()
    with gzip.GzipFile(fileobj=bufer, mode="wb", mtime=0) as gz:
        for d in docs:
            gz.write((json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    return bufer.getvalue()


def main(argv=None):
    p = argparse.ArgumentParser(prog="procesar")
    p.add_argument("--simulacro", action="store_true")
    p.add_argument("--fuente", help="solo los archivos de esta fuente")
    p.add_argument("--lote", help="solo los archivos de bronce que empiezan así (una carpeta o un archivo)")
    p.add_argument("--forzar", action="store_true", help="reevaluar aunque las reglas no hayan cambiado")
    p.add_argument("--sin-reevaluar", action="store_true", help="solo archivos nuevos, aunque las reglas cambien")
    o = p.parse_args(argv)
    total = procesar(Lago.desde_entorno(), cat.cargar(), cat.cargar_taxonomia(), simulacro=o.simulacro,
                     solo_fuente=o.fuente, lote=o.lote, forzar=o.forzar, reevaluar=not o.sin_reevaluar)
    print(json.dumps(total, ensure_ascii=False))
    return total


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
