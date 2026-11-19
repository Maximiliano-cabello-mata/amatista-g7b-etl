"""Modelo documental v3. Señales observables por bloque y realimentación determinista por página."""
import hashlib
import json
import re
import unicodedata
from collections import Counter

MODELO = "documental/3.0"
TECNICO = re.compile(r"\b(?:noise threshold|min samples|samples?|muestras?|sampling|threshold|umbral|vram|memory|memoria|subdivision|subdivisi[oó]n|denois\w*|resoluci[oó]n|resolution|viewport|modifier|modificador|shader|compression|compresi[oó]n|bpy\.\w+)\b", re.I)
EFECTO = re.compile(r"\b(?:determines?|controls?|selects?|enables?|disables?|reduces?|increases?|decreases?|limits?|stops?|automatically|determina|controla|selecciona|habilita|desactiva|reduce|aumenta|limita|automaticamente)\b", re.I)
CONDICION = re.compile(r"\b(?:when|if|unless|under|cuando|si|al activar|al desactivar|al poner)\b|(?:=|set to|valor de)\s*\d", re.I)
ACCION = re.compile(r"\b(?:rename|select|press|set|enable|disable|renombra|selecciona|pulsa|activa|desactiva|ajusta)\b", re.I)
OBSERVABLE = re.compile(r"\b(?:verify|confirm|check that|should appear|should see|comprueba|verifica|debe aparecer|deberias ver)\b", re.I)
OBJETIVOS = {"identificar_objetos": {"outliner", "object", "objeto", "objetos"},
             "ajustar_render": {"sampling", "muestras", "samples", "denoising", "render"},
             "editar_malla": {"mesh", "malla", "vertices", "vertex"}}
GENERAL = re.compile(r"^(?:blender (?:is|es) (?:a |an |un |una ).{0,100}(?:3d|modelado|modeling).{0,60}|(?:subscribe|suscribete|click here|haz clic aqui)[.! ]*)$", re.I)
VERSION = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def normal(texto):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", texto.casefold())
                            if not unicodedata.combining(c)).split())


def huella(valor):
    datos = json.dumps(valor, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(datos.encode()).hexdigest()


def decidir(bloque, frag, foro):
    texto = normal(bloque.get("texto", ""))
    titulo = normal(frag.get("titulo", ""))
    ajuste = TECNICO.search(texto) or TECNICO.search(titulo)
    relacion = bool(ajuste and EFECTO.search(texto))
    condicion = bool(CONDICION.search(texto))
    version = bool(VERSION.fullmatch(str(frag.get("version") or "")))
    palabras = set(re.findall(r"\w+", texto + " " + titulo))
    objetivos = sorted(k for k, vocab in OBJETIVOS.items() if palabras & vocab)
    accion, observable = bool(ACCION.search(texto)), bool(OBSERVABLE.search(texto))
    g = relacion and (condicion or version)
    e = bool(objetivos and accion and observable)
    senales = {"R": relacion, "C": condicion, "V": version, "L": objetivos, "A": accion, "O": observable}
    destinos = (["geoda"] if g else []) + (["amatista"] if e else [])
    if foro and (destinos or (ajuste and re.search(r"\b\d+(?:[.,]\d+)?\s*(?:ms|s|fps|gib|gb)\b", texto))):
        return "hipotesis", destinos, senales
    if destinos:
        return "candidato", destinos, senales
    if GENERAL.fullmatch(texto):
        return "descartado", [], senales
    if bloque.get("enlaces") and normal(" ".join(e["texto"] for e in bloque["enlaces"])) == texto:
        return "navegacion", [], senales
    return "revision", [], senales


class ModeloDocumental:
    def __init__(self):
        self.vistos = {}
        self.tablas = {}
        self.rendimiento = 0.5

    def anotar(self, item, foro=False):
        eventos = []
        for frag in item.get("fragmentos", []):
            for pos, bloque in enumerate(frag["bloques"]):
                estado, destinos, senales = decidir(bloque, frag, foro)
                # La misma versión y contenido estructurado equivalen a la misma evidencia.
                identidad = [item.get("fuente"), frag.get("programa"), frag.get("version"),
                             frag.get("jerarquia"), bloque]
                clave = huella(identidad)
                evento = {"id": clave, "fragmento": frag["fragmento_id"], "bloque": pos,
                          "url": frag["url"], "decision": estado, "destinos": destinos, "senales": senales}
                # Conflictos exactos en tablas propiedad/valor bajo el mismo encabezado y contexto.
                for fila in (bloque.get("filas") or [])[1:]:
                    if len(fila) != 2:
                        continue
                    k = huella([identidad[:4], bloque["filas"][0], fila[0]])
                    valores = self.tablas.setdefault(k, {})
                    if valores and fila[1] not in valores:
                        evento["decision"] = "conflicto"
                        evento.setdefault("contrasta_con", []).extend(sorted(set(valores.values())))
                    valores.setdefault(fila[1], frag["url"])
                if clave in self.vistos:
                    evento.update(decision="referencia", referencia=self.vistos[clave])
                else:
                    self.vistos[clave] = frag["url"]
                eventos.append(evento)
        counts = Counter(ev["decision"] for ev in eventos)
        evaluables = sum(counts[k] for k in ("candidato", "revision", "descartado", "hipotesis", "conflicto"))
        delta = 0.0
        if evaluables:
            observado = counts["candidato"] / evaluables
            delta = observado - self.rendimiento
            self.rendimiento += 0.25 * delta
        item["documental"] = {"modelo": MODELO, "eventos": eventos, "conteos": dict(counts),
                              "gradiente": delta, "rendimiento": self.rendimiento}
        return item
