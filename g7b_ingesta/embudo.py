"""El embudo de calidad: cada documento pasa cinco etapas y sale aceptado, a revisión o rechazado,
siempre con sus motivos (docs/INGESTA.md).

    1. entrada      fuente vigilable, dominio permitido, licencia confirmada, modo respetado
    2. calidad      texto suficiente, idioma, que sea prosa y no basura (menús, listas, repetición)
    3. duplicados   ni repetido exacto ni casi-duplicado de algo que ya pasó
    4. relevancia   responde alguna pregunta del plan (taxonomía)
    5. valor        es específico: medidas, versiones, hardware, código, ajustes; no genérico

Solo lo aceptado sigue hacia oro y el warehouse. Lo rechazado se guarda con su motivo para el
tablero de salud; lo de revisión espera a una persona.
"""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import texto as tx

ACEPTADO, REVISION, RECHAZADO = "aceptado", "revision", "rechazado"

UMBRALES = {
    "palabras_min": 40,
    "palabras_max": 200_000,
    "palabras_min_metadatos": 15,     # un resumen de arXiv es corto
    "proporcion_alfabetica_min": 0.6,
    "linea_repetida_max": 0.3,
    "relevancia_min": 2.0,
    "valor_min": 2.0,
    "valor_revision": 1.0,
    "hamming_casi_duplicado": 3,
    "resumen_metadatos_max": 1200,    # caracteres de texto propio permitidos en solo_metadatos
    "version_desactualizada": (2, 80),  # antes de 2.80 la interfaz de Blender era otra
}

_SENALES_VALOR = [
    ("medida", re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:fps|ms|s|seg|segundos|seconds|min|gb|mb|%|x)\b", re.I), 1.5),
    ("version", re.compile(r"\b(?:blender|godot|freecad|krita)\s*\d+\.\d+", re.I), 1.0),
    ("hardware", re.compile(r"\b(?:gtx|rtx|radeon|rx\s?\d{3,4}|intel\s?(?:hd|uhd|iris)|vega|ryzen|core\s?i[3579]|"
                            r"apple\s?m[1-4]|geforce|quadro|arc\s?a\d{3})\b", re.I), 1.5),
    ("codigo", re.compile(r"\bbpy\.\w+|\bimport\s+bpy\b|```|\bdef\s+\w+\(", re.I), 1.5),
    ("ajuste", re.compile(r"\b(?:simplify|samples|muestras|subdivision levels?|denois\w*|viewport shading|"
                          r"workbench|eevee|cycles|tile size|clamp|resolution|resolucion|lod|decimate)\b", re.I), 1.0),
    ("comparacion", re.compile(r"\b(?:faster|slower|mas rapido|mas lento|compared|comparado|versus|vs\.?)\b", re.I), 0.5),
]
_GENERICO = re.compile(r"\b(?:top \d+|best \w+ ever|you won'?t believe|increible|click here|haz clic|"
                       r"subscribe|suscribete|sponsored|patrocinado)\b", re.I)


@dataclass
class Resultado:
    estado: str
    etapa: str
    motivos: list = field(default_factory=list)
    puntajes: dict = field(default_factory=dict)
    preguntas: list = field(default_factory=list)
    huella: str = ""
    simhash: int = 0

    def como_dict(self):
        return {"estado": self.estado, "etapa": self.etapa, "motivos": self.motivos, "puntajes": self.puntajes,
                "preguntas": self.preguntas, "huella": self.huella, "simhash": f"{self.simhash:016x}"}


class Indice:
    """Lo que ya pasó el embudo: huellas exactas y simhash, para detectar repetidos."""

    def __init__(self, exactas=None, aproximadas=None):
        self.exactas = set(exactas or [])
        self.aproximadas = list(aproximadas or [])

    def agregar(self, huella, simhash):
        self.exactas.add(huella)
        self.aproximadas.append(simhash)

    def como_dict(self):
        return {"exactas": sorted(self.exactas), "aproximadas": [f"{h:016x}" for h in self.aproximadas]}

    @classmethod
    def desde_dict(cls, datos):
        datos = datos or {}
        return cls(datos.get("exactas"), [int(h, 16) for h in datos.get("aproximadas", [])])


def _relevancia(texto_normal, taxonomia):
    puntajes = {}
    for pregunta, definicion in taxonomia.get("preguntas", {}).items():
        total = 0.0
        for entrada in definicion.get("claves", []):
            clave, peso = (entrada if isinstance(entrada, (list, tuple)) else (entrada, 1.0))
            clave = tx.normalizar(str(clave))
            if not clave:
                continue
            ocurrencias = len(re.findall(r"\b" + re.escape(clave), texto_normal))
            total += min(ocurrencias, 3) * float(peso)  # tope: repetir una palabra no la hace más relevante
        if total:
            puntajes[pregunta] = round(total, 2)
    return puntajes


def _valor(texto_original):
    senales, total = {}, 0.0
    for nombre, patron, peso in _SENALES_VALOR:
        n = len(patron.findall(texto_original))
        if n:
            senales[nombre] = n
            total += min(n, 4) * peso
    genericos = len(_GENERICO.findall(texto_original))
    if genericos:
        senales["generico"] = genericos
        total -= 2.0 * genericos
    return round(total, 2), senales


def evaluar(doc, fuente, taxonomia, indice, umbrales=UMBRALES):
    """doc: {"url", "titulo", "texto", "metadatos"}; fuente: entrada del catálogo (dict)."""
    u = {**umbrales, **(fuente.get("umbrales") or {})}  # una fuente puede ajustar sus umbrales
    texto = doc.get("texto") or ""
    titulo = doc.get("titulo") or ""
    completo = f"{titulo}\n{texto}".strip()

    # 1. Entrada
    if not (fuente.get("activa") and fuente.get("licencia_verificada")):
        return Resultado(RECHAZADO, "entrada", ["fuente inactiva o licencia sin confirmar"])
    dominio = urlparse(doc.get("url") or "").hostname or ""
    permitidos = fuente.get("dominios") or []
    if permitidos and not any(dominio == d or dominio.endswith("." + d) for d in permitidos):
        return Resultado(RECHAZADO, "entrada", [f"dominio no permitido: {dominio or 'sin url'}"])
    modo = fuente.get("modo", "texto_completo")
    if modo == "agregados":
        return Resultado(REVISION, "entrada", ["fuente de agregados: se procesa con su propio extractor de cifras"])
    if modo == "solo_metadatos" and len(texto) > u["resumen_metadatos_max"]:
        return Resultado(RECHAZADO, "entrada",
                         [f"modo solo_metadatos: el texto excede {u['resumen_metadatos_max']} caracteres"])

    # 2. Calidad
    lista = tx.palabras(completo)
    minimo = u["palabras_min_metadatos"] if modo == "solo_metadatos" else u["palabras_min"]
    if len(lista) < minimo:
        return Resultado(RECHAZADO, "calidad", [f"texto insuficiente: {len(lista)} palabras (mínimo {minimo})"])
    if len(lista) > u["palabras_max"]:
        return Resultado(RECHAZADO, "calidad", [f"texto demasiado largo: {len(lista)} palabras"])
    simbolos = re.findall(r"\S+", completo)
    alfabeticas = sum(1 for s in simbolos if re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", s))
    if simbolos and alfabeticas / len(simbolos) < u["proporcion_alfabetica_min"]:
        return Resultado(RECHAZADO, "calidad", ["poca prosa: parece código suelto, tablas o basura"])
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if len(lineas) >= 5:
        repetidas = len(lineas) - len(set(lineas))
        if repetidas / len(lineas) > u["linea_repetida_max"]:
            return Resultado(RECHAZADO, "calidad", ["demasiadas líneas repetidas (menús o plantillas)"])
    lengua = tx.idioma(completo)
    if lengua not in ("es", "en"):
        return Resultado(RECHAZADO, "calidad", [f"idioma no soportado: {lengua}"])

    # 3. Duplicados
    huella = tx.huella_exacta(completo)
    aproximada = tx.simhash(completo)
    if huella in indice.exactas:
        return Resultado(RECHAZADO, "duplicados", ["duplicado exacto"], huella=huella, simhash=aproximada)
    for previa in indice.aproximadas:
        if tx.distancia_hamming(previa, aproximada) <= u["hamming_casi_duplicado"]:
            return Resultado(RECHAZADO, "duplicados", ["casi duplicado de un documento aceptado"],
                             huella=huella, simhash=aproximada)

    # 4. Relevancia
    normal = tx.normalizar(completo)
    por_pregunta = _relevancia(normal, taxonomia)
    propias = set(fuente.get("preguntas") or [])
    preguntas = sorted((p for p, v in por_pregunta.items() if v >= u["relevancia_min"]),
                       key=lambda p: -por_pregunta[p])
    relevancia = max(por_pregunta.values(), default=0.0)
    puntajes = {"palabras": len(lista), "idioma": lengua, "relevancia": relevancia, "por_pregunta": por_pregunta}
    if not preguntas:
        return Resultado(RECHAZADO, "relevancia", ["no responde ninguna pregunta del plan"],
                         puntajes, [], huella, aproximada)
    motivos = []
    if propias and not propias.intersection(preguntas):
        motivos.append("responde preguntas distintas a las esperadas de su fuente")

    # 5. Valor
    valor, senales = _valor(completo)
    if doc.get("metadatos", {}).get("puntaje_foro") is not None:
        votos = doc["metadatos"]["puntaje_foro"]
        valor += min(max(votos, 0), 20) / 10   # votos de la comunidad: hasta 2 puntos
        senales["votos"] = votos
        if doc["metadatos"].get("respuesta_aceptada"):
            valor += 1.0
            senales["respuesta_aceptada"] = True
    valor = round(valor, 2)
    puntajes.update({"valor": valor, "senales": senales})
    versiones = tx.versiones_blender(completo)
    if versiones:
        puntajes["versiones_blender"] = [f"{a}.{b}" for a, b in versiones]
        if max(versiones) < u["version_desactualizada"]:
            motivos.append("solo menciona versiones de Blender anteriores a 2.80: puede estar desactualizado")

    if valor < u["valor_revision"]:
        return Resultado(RECHAZADO, "valor", ["genérico: sin medidas, versiones, hardware, código ni ajustes"],
                         puntajes, preguntas, huella, aproximada)
    if valor < u["valor_min"] or motivos:
        return Resultado(REVISION, "valor", motivos or ["valor en el límite"], puntajes, preguntas, huella, aproximada)
    return Resultado(ACEPTADO, "valor", [], puntajes, preguntas, huella, aproximada)
