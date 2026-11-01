"""Bronce → plata: cada registro nuevo pasa por el embudo (embudo.py).

    python -m g7b_ingesta.procesar
    python -m g7b_ingesta.procesar --simulacro

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
from .embudo import ACEPTADO, RECHAZADO, REVISION, UMBRALES, Indice, evaluar

PROCESADOS = "control/procesados.json"
INDICE = "control/indice_embudo.json"
CONTEOS = "control/embudo.json"
EXCLUIR = ("bronce/sonda/",)  # las mediciones tienen su propio camino
FRAGMENTO_METADATOS = 300


def fuente_de(ruta, registro):
    if registro.get("fuente"):
        return registro["fuente"]
    partes = ruta.split("/")
    return partes[2] if partes[1] == "zyte" else partes[1]


def a_documento(registro, lago, fuente):
    """Convierte un registro crudo (de cualquier extractor) en {url, titulo, texto, metadatos}."""
    url = registro.get("url") or registro.get("enlace")
    metadatos = {k: registro[k] for k in ("fecha", "autores", "autor", "autor_respuesta", "etiquetas", "categorias")
                 if registro.get(k)}
    if "contenido" in registro:  # araña estructurada de manuales (manual_sphinx, blender_docs)
        texto = registro["contenido"]
        metadatos.update({k: registro[k] for k in ("version", "seccion", "programa", "operadores_bpy")
                          if registro.get(k)})
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


def procesar(lago, catalogo, taxonomia, simulacro=False, salida=print):
    fuentes = cat.por_id(catalogo)
    procesados = lago.leer_json(PROCESADOS, por_omision={}) or {}
    indice = Indice.desde_dict(lago.leer_json(INDICE))
    conteos = lago.leer_json(CONTEOS, por_omision={}) or {}
    pendientes = [r for r in lago.listar("bronce/")
                  if r.endswith(".jsonl.gz") and not r.startswith(EXCLUIR) and r not in procesados]
    total = Counter()
    motivos = Counter()   # (estado, etapa, motivo) -> cuántos: para ajustar umbrales con datos
    ejemplos = {}
    for ruta in sorted(pendientes):
        grupos = {ACEPTADO: [], REVISION: [], RECHAZADO: []}
        for registro in lago.leer_jsonl_gz(ruta):
            id_fuente = fuente_de(ruta, registro)
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
        salida(f"{ruta}: " + ", ".join(f"{k} {v}" for k, v in resumen.items()))
        if simulacro:
            continue
        partes = ruta.split("/")
        destino = "/".join(partes[1:-1])  # <fuente>/<fecha> (o zyte/<araña>/<fecha>)
        for estado, docs in grupos.items():
            if docs:
                carpeta = {"aceptado": "aceptados", "revision": "revision", "rechazado": "rechazados"}[estado]
                lago.subir_bytes(f"plata/{carpeta}/{destino}/{posixpath.basename(ruta)}", _jsonl_gz(docs),
                                 tipo="application/x-ndjson", codificacion="gzip", sobrescribir=True)
        procesados[ruta] = {"cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"), **resumen}
        lago.escribir_json(PROCESADOS, procesados)
        lago.escribir_json(INDICE, indice.como_dict())
        lago.escribir_json(CONTEOS, conteos)
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
    o = p.parse_args(argv)
    total = procesar(Lago.desde_entorno(), cat.cargar(), cat.cargar_taxonomia(), simulacro=o.simulacro)
    print(json.dumps(total, ensure_ascii=False))
    return total


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
