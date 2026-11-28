"""El manual de Blender en varias versiones, con las secciones que responden las preguntas del plan.

Antes solo sacaba los títulos del índice de scripting; ahora es manual_sphinx con valores de Blender.

    scrapy crawl blender_docs                       # todo (versiones y secciones de abajo)
    scrapy crawl blender_docs -a versiones='["5.2"]' -a max_paginas=20

Versiones: la LTS vigente (5.2) y las LTS anteriores (4.5 y 3.6). 2.79 (la última con la interfaz
anterior a 2.80) no se recorre: el robots.txt de docs.blender.org prohíbe /*/2.79/ a todos los bots.
Secciones: rendimiento y ajustes (P1, P2), equivalencias de teclas (P4) y cómo se hace (P6). Las
páginas de cada sección salen del inventario (objects.inv) de su versión, así que una sección que no
existe en una versión simplemente no aporta páginas.
"""
from ..inventario_sphinx import SECCIONES_BLENDER
from .manual_sphinx import ManualSphinxSpider


class BlenderDocsSpider(ManualSphinxSpider):
    name = "blender_docs"
    fuente_por_omision = "blender-manual"
    programa = "blender"
    base = "https://docs.blender.org/manual/en/"
    versiones = ["5.3", "5.2", "4.5", "3.6"]
    secciones = list(SECCIONES_BLENDER)
