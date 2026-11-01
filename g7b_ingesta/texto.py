"""Herramientas de texto del embudo: extraer, normalizar, idioma, versiones y huellas."""
import hashlib
import io
import re
import unicodedata

_PALABRA = re.compile(r"[a-z0-9áéíóúüñ][a-z0-9áéíóúüñ'\-]*", re.IGNORECASE)
_VERSION_BLENDER = re.compile(r"\bblender\s*(?:v(?:ersion)?\.?\s*)?([2-9])\.(\d{1,2})\b", re.IGNORECASE)

# Palabras muy frecuentes: bastan para distinguir español de inglés en textos técnicos.
_VACIAS = {
    "es": {"el", "la", "los", "las", "de", "del", "que", "y", "en", "un", "una", "por", "con", "para",
           "es", "se", "no", "lo", "como", "mas", "pero", "sus", "al", "este", "esta", "cuando"},
    "en": {"the", "of", "and", "to", "in", "is", "that", "for", "it", "with", "as", "on", "this",
           "be", "are", "by", "an", "or", "can", "you", "if", "from", "not", "when"},
}


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar(texto):
    """Minúsculas, sin acentos y con espacios simples: para comparar, no para guardar."""
    return re.sub(r"\s+", " ", sin_acentos(texto or "").lower()).strip()


def palabras(texto):
    return _PALABRA.findall(texto or "")


def extraer_html(html, url=None):
    """Texto principal de una página, sin menús, pies ni anuncios (trafilatura)."""
    if not html:
        return ""
    try:
        import trafilatura

        texto = trafilatura.extract(html, url=url, include_comments=False, include_tables=True,
                                    favor_precision=True)
        if texto:
            return texto
    except Exception:
        pass
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def extraer_pdf(datos, max_paginas=200):
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(datos))
    return "\n".join((pagina.extract_text() or "") for pagina in lector.pages[:max_paginas]).strip()


def idioma(texto):
    cuenta = {"es": 0, "en": 0}
    for p in palabras(normalizar(texto))[:2000]:
        for lengua, vacias in _VACIAS.items():
            if p in vacias:
                cuenta[lengua] += 1
    total = sum(cuenta.values())
    if total < 5:
        return "desconocido"
    mejor = max(cuenta, key=cuenta.get)
    return mejor if cuenta[mejor] / total >= 0.6 else "mixto"


def versiones_blender(texto):
    """Versiones de Blender mencionadas ("Blender 2.79", "Blender 4.2"), de menor a mayor."""
    vistas = {(int(a), int(b)) for a, b in _VERSION_BLENDER.findall(texto or "")}
    return sorted(vistas)


def huella_exacta(texto):
    return hashlib.sha256(normalizar(texto).encode("utf-8")).hexdigest()


def simhash(texto, bits=64):
    """Huella que cambia poco si el texto cambia poco: detecta casi-duplicados."""
    tokens = palabras(normalizar(texto))
    tejas = [" ".join(tokens[i:i + 3]) for i in range(max(1, len(tokens) - 2))] if tokens else []
    pesos = [0] * bits
    for teja in tejas:
        h = int.from_bytes(hashlib.blake2b(teja.encode("utf-8"), digest_size=8).digest(), "big")
        for i in range(bits):
            pesos[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(bits) if pesos[i] > 0)


def distancia_hamming(a, b):
    return bin(a ^ b).count("1")
