# Extracción por apartados de manuales Sphinx

La araña blender_docs hereda esta mejora de manual_sphinx. Cada página conserva
los campos anteriores y añade schema_version=2, extractor_version=manual_sphinx/2
y fragmentos. No se despliega automáticamente por abrir este PR.

## Qué contiene cada fragmento

- Título y jerarquía h1-h6, versión, programa y fuente.
- URL con el ancla real de Sphinx, URL de página e identificador estable.
- Bloques de párrafo, lista, definiciones, código, tabla, aviso e imagen.
- Tablas como filas/celdas; listas con orden y elementos; avisos con sus clases.
- Enlaces e imágenes referenciadas con texto alternativo; no se descargan imágenes.
- Hash del contenido estructurado. Las fechas no participan en el hash.

Cada bloque pertenece a un apartado, sin repetirlo en sus antecesores.
Las listas anidadas se conservan dentro de su elemento superior.
El código dentro de listas/avisos/definiciones se conserva además en bloques_codigo.
No se deducen requisitos, resultados esperados ni recomendaciones que el manual
no declare: esta primera etapa conserva evidencia para el clasificador posterior.

## Prueba pequeña, sin publicar en MongoDB

Ejecutar desde un checkout de esta rama con Scrapy instalado:

```bash
scrapy crawl blender_docs -a versiones='["4.5"]' -a secciones='["modeling/modifiers/generate/bevel.html"]' -a max_paginas=10 -O bevel.jsonl
```

Primero inspeccionar fragmentos[].ancla del resultado. Para seleccionar solo
apartados cuya ancla exacta sea options:

```bash
scrapy crawl blender_docs -a versiones='["4.5"]' -a secciones='["modeling/modifiers/generate/bevel.html"]' -a anclas_objetivo='["options"]' -a max_paginas=10 -O bevel-options.jsonl
```

La ruta y las anclas dependen de la versión del manual; si no existen hay que
ajustarlas a la fuente real. Este PR usa fixtures locales, no certifica esa URL.
En PowerShell puede ser necesario escapar las comillas JSON según su versión.

anclas_objetivo selecciona fragmentos exactos, no incluye automáticamente sus
subapartados. Las páginas sin coincidencias no emiten documentos, pero se siguen
explorando sus enlaces. El campo contenido anterior mantiene la página completa
como contexto: los consumidores que busquen solo lo seleccionado deben leer
fragmentos. No es un filtro semántico ni reduce por sí mismo las descargas.
La estadística g7b/sin_anclas_objetivo cuenta las páginas sin coincidencias.

## Compatibilidad y límites

- Un documento por página; doc_id conserva la identidad anterior.
- hash_contenido ahora incluye fragmentos y schema_version. Reprocesar una página
  bajo este contrato debe detectarse como cambio, incluso si solo cambió una tabla.
- El lago y el embudo no se migran aquí. Los archivos ya marcados procesados
  necesitan una reingesta/reproceso deliberado para aprovechar estos campos.
- Sin ancla real se enlaza la página; un ordinal local distingue fragmentos.
  Al reestructurar esa página, dichos IDs sin ancla pueden cambiar.
- Se conserva el límite global max_paginas. No garantiza cobertura por versión.
- No se alteran versiones predeterminadas, robots.txt, frecuencia ni escritura Mongo.

## Validación

```bash
python -m pytest pruebas/test_fragmentos_sphinx.py pruebas/test_manual_mongo.py -q
```

Los fixtures comprueban versiones separadas, jerarquía, anclas, tablas, avisos,
código, enlaces, imágenes, listas sin duplicación, huellas y selección exacta.
Una ejecución con datos reales sigue siendo necesaria antes de desplegar en Zyte.

