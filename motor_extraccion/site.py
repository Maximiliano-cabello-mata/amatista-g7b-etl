"""Selección documental de Site. La puntuación de enlaces solo ordena las descargas."""
import math
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

from .documental import CONDICION, VERSION, ModeloDocumental, decidir, normal
from .frontera_documental import palabras

MODELO_SITE = "site/4.0"
PARAMETRO = re.compile(r"\b(?:blur|radius|threshold|samples?|filter|alpha|resolution|intensity|"
                       r"exposure|saturation|opacity|contrast|gamma|scale|kernel|factor|mask|"
                       r"buffer|pixel size|precision|quality|denois\w*|render time|frame rate)\b")
EFECTO = re.compile(r"\b(?:determines?|controls?|reduces?|increases?|decreases?|limits?|"
                    r"preserves?|prevents?|multiplies|divides|affects?|specifies|clamps?|"
                    r"controla|reduce|aumenta|limita|determina)\b")
PESOS = (0.25, 0.40, 0.20)


class ModeloSite(ModeloDocumental):
    version_modelo = MODELO_SITE

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
