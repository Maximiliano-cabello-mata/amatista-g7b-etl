"""El manual de Blender en varias versiones, con las secciones que responden las preguntas del plan.

Antes solo sacaba los títulos del índice de scripting; ahora es manual_sphinx con valores de Blender.

    scrapy crawl blender_docs                       # todo (versiones y secciones de abajo)
    scrapy crawl blender_docs -a versiones='["5.2"]' -a max_paginas=20

Versiones: la LTS vigente (5.2), las LTS anteriores (4.5 y 3.6) y 2.79, la última con la interfaz
anterior a 2.80 (sirve para computadoras viejas, nivel N1).
Secciones: rendimiento y ajustes (P1, P2), equivalencias de teclas (P4) y cómo se hace (P6). Las
rutas cambian entre versiones; las que no existen en una versión dan 404 y se ven en las
estadísticas del trabajo en Zyte.
"""
from .manual_sphinx import ManualSphinxSpider


class BlenderDocsSpider(ManualSphinxSpider):
    name = "blender_docs"
    fuente_por_omision = "blender-manual"
    programa = "blender"
    base = "https://docs.blender.org/manual/en/"
    versiones = ["5.2", "4.5", "3.6", "2.79"]
    secciones = [
        # Rendimiento y ajustes según el equipo (P1, P2)
        "render/cycles/index.html",
        "render/eevee/index.html",
        "editors/preferences/system.html",
        "troubleshooting/index.html",
        # Equivalencias para quien viene de Maya o 3ds Max (P4)
        "interface/keymap/index.html",
        # Cómo se hace (P6)
        "advanced/scripting/index.html",
        "modeling/meshes/index.html",
        "modeling/modifiers/index.html",
        "modeling/geometry_nodes/index.html",
        "render/shader_nodes/index.html",
    ]
