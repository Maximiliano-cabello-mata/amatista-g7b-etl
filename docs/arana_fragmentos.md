# Extracci�n por apartados de manuales Sphinx

La ara�a blender_docs hereda esta mejora de manual_sphinx. Cada p�gina conserva
los campos anteriores y a�ade schema_version=2, extractor_version=manual_sphinx/2
y fragmentos. No se despliega autom�ticamente por abrir este PR.

## Qu� contiene cada fragmento

- T�tulo y jerarqu�a h1-h6, versi�n, programa y fuente.
- URL con el ancla real de Sphinx, URL de p�gina e identificador estable.
- Bloques de p�rrafo, lista, definiciones, c�digo, tabla, aviso e imagen.
- Tablas como filas/celdas; listas con orden y elementos; avisos con sus clases.
- Enlaces e im�genes referenciadas con texto alternativo; no se descargan im�genes.
- Hash del contenido estructurado. Las fechas no participan en el hash.

Cada bloque pertenece a un apartado, sin repetirlo en sus antecesores.
Las listas anidadas se conservan dentro de su elemento superior.
El c�digo dentro de listas/avisos/definiciones se conserva adem�s en bloques_codigo.
No se deducen requisitos, resultados esperados ni recomendaciones que el manual
no declare: esta primera etapa conserva evidencia para el clasificador posterior.

## Prueba peque�a, sin publicar en MongoDB

Ejecutar desde un checkout de esta rama con Scrapy instalado:

```bash
scrapy crawl blender_docs -a versiones='["4.5"]' -a secciones='["modeling/modifiers/generate/bevel.html"]' -a max_paginas=10 -O bevel.jsonl
```

Primero inspeccionar fragmentos[].ancla del resultado. Para seleccionar solo
apartados cuya ancla exacta sea options:

```bash
scrapy crawl blender_docs -a versiones='["4.5"]' -a secciones='["modeling/modifiers/generate/bevel.html"]' -a anclas_objetivo='["options"]' -a max_paginas=10 -O bevel-options.jsonl
```

La ruta y las anclas dependen de la versi�n del manual; si no existen hay que
ajustarlas a la fuente real. Este PR usa fixtures locales, no certifica esa URL.
En PowerShell puede ser necesario escapar las comillas JSON seg�n su versi�n.

anclas_objetivo selecciona fragmentos exactos, no incluye autom�ticamente sus
subapartados. Las p�ginas sin coincidencias no emiten documentos, pero se siguen
explorando sus enlaces. El campo contenido anterior mantiene la p�gina completa
como contexto: los consumidores que busquen solo lo seleccionado deben leer
fragmentos. No es un filtro sem�ntico ni reduce por s� mismo las descargas.
La estad�stica g7b/sin_anclas_objetivo cuenta las p�ginas sin coincidencias.

## Compatibilidad y l�mites

- Un documento por p�gina; doc_id conserva la identidad anterior.
- hash_contenido ahora incluye fragmentos y schema_version. Reprocesar una p�gina
  bajo este contrato debe detectarse como cambio, incluso si solo cambi� una tabla.
- El lago y el embudo no se migran aqu�. Los archivos ya marcados procesados
  necesitan una reingesta/reproceso deliberado para aprovechar estos campos.
- Sin ancla real se enlaza la p�gina; un ordinal local distingue fragmentos.
  Al reestructurar esa p�gina, dichos IDs sin ancla pueden cambiar.
- Se conserva el l�mite global max_paginas. No garantiza cobertura por versi�n.
- No se alteran versiones predeterminadas, robots.txt, frecuencia ni escritura Mongo.

## Validaci�n

```bash
python -m pytest pruebas/test_fragmentos_sphinx.py pruebas/test_manual_mongo.py -q
```

Los fixtures comprueban versiones separadas, jerarqu�a, anclas, tablas, avisos,
c�digo, enlaces, im�genes, listas sin duplicaci�n, huellas y selecci�n exacta.
Una ejecuci�n con datos reales sigue siendo necesaria antes de desplegar en Zyte.

