"""Selección documental de Site. La puntuación de enlaces solo ordena las descargas."""
import math
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

from .documental import CONDICION, VERSION, ModeloDocumental, decidir, huella, normal
from .frontera_documental import palabras

MODELO_SITE_ANTERIOR = "site/4.0"
MODELO_SITE = "site/4.1"
PARAMETRO = re.compile(r"\b(?:blur|radius|threshold|samples?|filter|alpha|resolution|intensity|"
                       r"exposure|saturation|opacity|contrast|gamma|scale|kernel|factor|mask|"
                       r"buffer|pixel size|precision|quality|denois\w*|render time|frame rate)\b")
EFECTO = re.compile(r"\b(?:determines?|controls?|reduces?|increases?|decreases?|limits?|"
                    r"preserves?|prevents?|multiplies|divides|affects?|specifies|clamps?|"
                    r"controla|reduce|aumenta|limita|determina)\b")
# Descripciones de interfaz que se repiten en numerosos nodos. Solo puntúan
# cuando el bloque aporta además una condición, un ejemplo o un efecto específico.
FRASE_ESTANDAR = re.compile(
    r"\b(?:standard (?:color|float|vector|image) input|controls the amount of influence "
    r"the node exerts on the output image|controls the amount of mixing between the [ab] and [ab] inputs|"
    r"the two inputs that are mixed together)\b", re.I)
UNIDADES = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:%|px|pixels?|ms|fps|gib|frames?|seconds?)\b")
EVIDENCIA = re.compile(r"\b(?:if|when|unless|instead|whereas|because|without|at the cost of|"
                       r"for example|by default|in order to|si|cuando|a costa de)\b")
PESOS = (0.25, 0.40, 0.20)


class ModeloSite(ModeloDocumental):
    version_modelo = MODELO_SITE

    @staticmethod
    def clave_referencia(item, frag, bloque, estado, original):
        texto = normal(bloque.get("texto", ""))
        if estado == "candidato" and len(texto.split()) >= 30 and bloque.get("tipo") in {
                "parrafo", "definiciones", "lista", "aviso"} and not bloque.get("bloques_codigo"):
            return huella([item.get("fuente"), frag.get("programa"), frag.get("version"), texto])
        return original

    @staticmethod
    def clasificar(bloque, frag, foro):
        texto = normal(bloque.get("texto", ""))
        enlaces = bloque.get("enlaces") or []
        total = len(texto.split())
        enlazadas = sum(len(e["texto"].split()) for e in enlaces)
        densidad = min(1.0, enlazadas / max(1, total))
        if enlaces and (densidad >= 0.80 or
                        (bloque.get("tipo") == "lista" and len(enlaces) >= 3 and densidad >= 0.55)):
            return "navegacion", [], {"densidad_enlaces": round(densidad, 4)}
        estado, destinos, senales = decidir(bloque, frag, foro)
        if estado == "revision" and PARAMETRO.search(texto) and EFECTO.search(texto):
            if CONDICION.search(texto) or VERSION.fullmatch(str(frag.get("version") or "")):
                estado, destinos = ("hipotesis" if foro else "candidato"), ["geoda"]
                senales["parametro_con_efecto"] = True
        if estado == "candidato" and destinos == ["geoda"]:
            if FRASE_ESTANDAR.search(texto):
                restante = FRASE_ESTANDAR.sub(" ", texto)
                if len(restante.split()) < 12 and not (UNIDADES.search(restante) or EVIDENCIA.search(restante)):
                    return "revision", [], {**senales, "descripcion_generica": True}
            # En «for ultimate control» y expresiones similares el sustantivo
            # no establece la relación técnica que busca el clasificador base.
            sin_sustantivo = re.sub(r"\b(?:for|more|greater|full|ultimate|total|fine) (?:\w+ )?control\b",
                                    "", texto)
            if sin_sustantivo != texto:
                alterno, _, _ = decidir({**bloque, "texto": sin_sustantivo}, frag, foro)
                if alterno != "candidato" and not EFECTO.search(sin_sustantivo):
                    return "revision", [], {**senales, "efecto_sin_demostrar": True}
        return estado, destinos, senales


def frecuencias(texto):
    return Counter(re.findall(r"[^\W_]+", normal(texto)))


def puntuar_enlaces(enlaces, temas, rendimiento):
    """BM25 por campo sobre los enlaces de un padre, con longitud media e IDF locales."""
    filas = [(url, [frecuencias(unquote(urlsplit(url).path)), frecuencias(ancla), frecuencias(contexto)])
             for url, ancla, contexto in enlaces]
    if not filas:
        return
    n = len(filas)
    notas = [0.15 * rendimiento] * n
    for campo, peso in enumerate(PESOS):
        documentos = [campos[campo] for _, campos in filas]
        longitudes = [sum(d.values()) for d in documentos]
        media = sum(longitudes) / n or 1.0
        df = Counter(t for d in documentos for t in temas.intersection(d))
        idf = {t: math.log1p((n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        for i, doc in enumerate(documentos):
            norma = 1.2 * (0.25 + 0.75 * longitudes[i] / media)
            bruto = sum(idf[t] * doc[t] * 2.2 / (doc[t] + norma) for t in sorted(temas.intersection(doc)))
            notas[i] += peso * bruto / (1.0 + bruto)
    for (url, _), (_, ancla, _), nota in zip(filas, enlaces, notas):
        puente = bool(palabras(ancla) & {"indice", "index", "reference", "catalog", "catalogo"})
        yield url, nota, puente
