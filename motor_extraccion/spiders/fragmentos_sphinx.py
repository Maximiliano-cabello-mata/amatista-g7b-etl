"""Fragmentos citables de Sphinx; sin inferir pasos ni requisitos ausentes."""
import hashlib
import json
import re
from urllib.parse import quote


def _texto(nodo):
    return re.sub(r"\s+", " ", " ".join(nodo.xpath(
        ".//text()[not(ancestor::a[contains(@class, 'headerlink')])]"
    ))).strip()


def extraer_fragmentos(contenedor, response, fuente, programa, version, titulo):
    """Asigna cada bloque al encabezado más cercano, sin duplicar subsecciones.

    Sin ancla real se cita la página y se identifica por ordinal local;
    ese ordinal puede variar cuando se edita la estructura de la página.
    """
    url = response.url.split("#", 1)[0]
    grupos, pila = [], []
    actual = {"titulo": titulo, "ancla": "", "jerarquia": [titulo], "bloques": []}
    grupos.append(actual)

    def recorrer(nodo):
        nonlocal actual
        etiqueta = nodo.tag
        if not isinstance(etiqueta, str):
            return
        clases = (nodo.get("class") or "").split()
        if etiqueta in ("nav", "aside", "script", "style") or "headerlink" in clases or "md-sidebar" in clases:
            return
        if etiqueta in ("h1", "h2", "h3", "h4", "h5", "h6"):
            nivel = int(etiqueta[1])
            texto = _texto(nodo)
            while pila and pila[-1][0] >= nivel:
                pila.pop()
            pila.append((nivel, texto))
            padre = nodo.getparent()
            ancla = nodo.get("id") or ""
            if not ancla and padre is not None and (
                    padre.tag == "section" or "section" in (padre.get("class") or "").split()):
                ancla = padre.get("id") or ""
            actual = {"titulo": texto, "ancla": ancla,
                      "jerarquia": [t for _, t in pila], "bloques": []}
            grupos.append(actual)
            return
        bloque = None
        if etiqueta == "pre":
            bloque = {"tipo": "codigo", "texto": "".join(nodo.itertext()).strip("\n")}
        elif etiqueta == "table":
            filas = [[_texto(celda) for celda in fila.xpath("./th | ./td")]
                     for fila in nodo.xpath(".//tr")]
            bloque = {"tipo": "tabla", "filas": filas, "texto": _texto(nodo)}
        elif "admonition" in clases:
            bloque = {"tipo": "aviso", "clases": clases, "texto": _texto(nodo)}
        elif etiqueta in ("ul", "ol"):
            bloque = {"tipo": "lista", "ordenada": etiqueta == "ol",
                      "elementos": [_texto(li) for li in nodo.xpath("./li")],
                      "texto": _texto(nodo)}
        elif etiqueta == "dl":
            bloque = {"tipo": "definiciones", "texto": _texto(nodo)}
        elif etiqueta == "p":
            bloque = {"tipo": "parrafo", "texto": _texto(nodo)}
        if bloque is not None:
            bloque["bloques_codigo"] = [
                "".join(pre.itertext()).strip("\n") for pre in nodo.xpath(".//pre")]
            bloque["enlaces"] = [
                {"url": response.urljoin(a.get("href")), "texto": _texto(a)}
                for a in nodo.xpath(".//a[@href]")
                if "headerlink" not in (a.get("class") or "").split()]
            bloque["imagenes"] = [
                {"url": response.urljoin(i.get("src")), "alt": i.get("alt", "")}
                for i in nodo.xpath(".//img[@src]")]
            if bloque["texto"] or bloque["imagenes"]:
                actual["bloques"].append(bloque)
            return
        if etiqueta == "img" and nodo.get("src"):
            actual["bloques"].append({"tipo": "imagen",
                                      "url": response.urljoin(nodo.get("src")),
                                      "alt": nodo.get("alt", ""), "texto": ""})
            return
        for hijo in nodo:
            recorrer(hijo)

    recorrer(contenedor.root)
    salida = []
    for ordinal, grupo in enumerate(grupos):
        if not grupo["bloques"]:
            continue
        ancla = grupo["ancla"]
        enlace = url + ("#" + quote(ancla, safe="-._~") if ancla else "")
        identidad = [fuente, programa, version, url, ancla or f"sin-ancla:{ordinal}"]
        serializado = json.dumps(grupo, ensure_ascii=False, sort_keys=True)
        salida.append({
            **grupo, "fragmento_id": hashlib.sha256(
                json.dumps(identidad, ensure_ascii=False).encode()).hexdigest(),
            "url": enlace, "url_pagina": url, "fuente": fuente,
            "programa": programa, "version": version,
            "contenido": "\n\n".join(b["texto"] for b in grupo["bloques"] if b["texto"]),
            "hash_contenido": hashlib.sha256(serializado.encode()).hexdigest(),
        })
    return salida

