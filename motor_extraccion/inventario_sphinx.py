"""El inventario de Sphinx (objects.inv): la lista oficial de páginas de un manual.

Sphinx publica `objects.inv` junto a cada manual para que otros proyectos enlacen sus páginas
(intersphinx). Trae, entre otras cosas, una entrada `std:doc` por página. Con él la araña sabe de
antemano qué páginas existen: no recorre enlaces al azar, no pasa dos veces por la misma página y
puede comprobar al final qué parte del manual cubrió.

Formato (versión 2): cuatro líneas de encabezado en texto y el resto comprimido con zlib. Cada línea
del cuerpo es «nombre dominio:rol prioridad uri nombre-visible». En la uri, un «$» final se
reemplaza por el nombre. Referencia: https://sphobjinv.readthedocs.io/en/v2.4/syntax.html

No importa Scrapy: lo usan la araña (en Zyte) y el sensor del radar (en GitHub Actions).
"""
import hashlib
import zlib

ENCABEZADO = b"# Sphinx inventory version 2"


def leer(contenido):
    """{"proyecto", "version", "paginas": [uri ordenadas], "huella"} de un objects.inv v2."""
    lineas = contenido.split(b"\n", 4)
    if len(lineas) < 5 or lineas[0].strip() != ENCABEZADO:
        raise ValueError("no es un inventario de Sphinx versión 2")
    cuerpo = zlib.decompress(lineas[4]).decode("utf-8")
    paginas = set()
    for linea in cuerpo.splitlines():
        partes = linea.split(" ", 4)
        if len(partes) < 4 or partes[1] != "std:doc":
            continue
        nombre, uri = partes[0], partes[3]
        if uri.endswith("$"):
            uri = uri[:-1] + nombre
        uri = uri.split("#", 1)[0]
        if uri:
            paginas.add(uri)
    return {
        "proyecto": lineas[1].decode("utf-8").removeprefix("# Project:").strip(),
        "version": lineas[2].decode("utf-8").removeprefix("# Version:").strip(),
        "paginas": sorted(paginas),
        # Sobre el cuerpo descomprimido: cambia si se agregan, quitan o renombran páginas o
        # apartados, no por la fecha de compilación (las páginas sí la llevan, y cambian a diario).
        "huella": hashlib.sha256(cuerpo.encode("utf-8")).hexdigest(),
    }


def carpeta(seccion):
    """La carpeta que abarca una sección: «render/cycles/index.html» → «render/cycles/»."""
    return seccion.rsplit("/", 1)[0] + "/" if "/" in seccion else ""


def filtrar(paginas, secciones):
    """[(uri, seccion)] de las páginas dentro de alguna sección. Sin secciones, todo el manual.

    Cada página se asigna a una sola sección (la más específica), así que dos secciones que se
    solapan no la piden dos veces.
    """
    if not secciones:
        return [(p, carpeta(p).rstrip("/") or p) for p in paginas]
    carpetas = sorted({carpeta(s) for s in secciones}, key=len, reverse=True)
    salida = []
    for pagina in paginas:
        for c in carpetas:
            if pagina.startswith(c):
                salida.append((pagina, c.rstrip("/") or pagina))
                break
    return salida
