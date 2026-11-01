"""Esquema de los documentos de manuales (araña manual_sphinx). Solo documenta los campos:
las arañas devuelven diccionarios con estos nombres."""

CAMPOS_DOCUMENTO_MANUAL = {
    "doc_id": "SHA-256 de la URL canónica",
    "fuente": "id del catálogo (fuentes/catalogo.yml)",
    "url": "URL canónica (sin #ancla)",
    "programa": "blender, godot...",
    "version": "versión del manual: 5.2, 4.5, 3.6, 2.79...",
    "seccion": "sección de inicio (render/cycles, modeling/meshes...)",
    "titulo": "título de la página",
    "jerarquia": "subtítulos H2 y H3 en orden",
    "contenido": "texto en orden: títulos, párrafos, listas, propiedades y código (Markdown sencillo)",
    "propiedades": "lista de {nombre, descripcion}: cada ajuste descrito en el manual (<dt>/<dd>)",
    "bloques_codigo": "bloques de código en orden",
    "operadores_bpy": "llamadas bpy.* encontradas",
    "conteo_palabras": "palabras del contenido",
    "hash_contenido": "SHA-256 de contenido + código: cambia solo si la página cambió",
    "extraido_en": "fecha UTC ISO-8601",
}
