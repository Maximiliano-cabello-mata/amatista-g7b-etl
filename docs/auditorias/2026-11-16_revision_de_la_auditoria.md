# Revisión de la auditoría del 15 de noviembre (16 de noviembre de 2026)

Revisión punto por punto de [la auditoría de arañas y Azure](2026-11-15_auditoria_aranas_y_azure_g7b.md), contrastada con el código de `main` (commit `6e2bcc6`) y con el lago real después de la primera vuelta del ciclo 24/7 ([operación 24/7](../OPERACION_24_7.md), sección 5).

**Leyenda:** ✅ confirmado · ⚠️ cierto en parte o con cifra distinta · 🔧 ya corregido · ❌ no se sostiene.

## 1. Estado de los datos (tabla de la sección 1)

| Afirmación | Veredicto | Lo comprobado |
|---|---|---|
| 995 documentos en MongoDB, de 2.353 del lote `883618-1-13` | 🔧 | Era cierto el 15 de noviembre. Tras el reprocesamiento del 16 hay **1.021** en `conocimiento_3d.documentos` (+26) |
| 3.006 mediciones, Geoda con `perfiles: []` | ✅ | Sigue igual: ninguna medición de sonda con ventana real. Para resolverlo hay que medir en equipos de verdad, no en el runner |
| 19 fuentes activas, `robots.txt` respetado | ✅ | `geodar salud`: 19 de 19 sensores al día |
| Dependencia de SAS (`AZURE_LAGO_URL`) | ✅ | `g7b_lago/lago.py` solo acepta SAS o cadena de conexión. La firma actual vence en 2027 (política `actions-2027`); OIDC sigue siendo la mejora correcta (sección 4) |

## 2. Los cinco defectos de la araña (sección 3.1)

| # | Afirmación | Veredicto | Lo comprobado |
|---|---|---|---|
| 1 | 10 secciones semilla y un tope global de 3.000 páginas, que deja a 2.79 sin nada | ✅ | En `883618-1-13` hay 925 páginas de 5.2, 771 de 4.5, 657 de 3.6 y **ninguna de 2.79**. Faltan animación, escultura, UV, física, composición y Grease Pencil |
| 2 | Las tablas y los avisos se pierden | 🔧 en código, ⚠️ en producción | El PR #21 (`fragmentos_sphinx.py`) extrae tablas, avisos, código e imágenes por apartado. **No está desplegado en Zyte**: el despliegue del 16 de noviembre falló por un error en ese PR (sección 5 de este documento) |
| 3 | `<dd>` anidados duplican texto; `` queda en los títulos | 🔧 en parte | Los fragmentos nuevos no duplican listas ni definiciones. `limpio()` ahora quita también ``. El campo `contenido` de página completa conserva el comportamiento anterior |
| 4 | El embudo rechaza el 55,8 % del manual «por falta de palabras clave» | ❌ en la causa, ✅ en el umbral | El 55,8 % (1.332 de 2.353) es correcto, pero la causa principal es otra. La mayoría son **la misma página en otra versión** (casi duplicado), páginas índice y textos cortos. Por relevancia se rechazan 383 en todo el lago. `relevancia_min: 2.0` sí se aplica al manual, porque el catálogo no lo cambia |
| 5 | `a_documento` reduce `propiedades` a un número y descarta `jerarquia`, `bloques_codigo` y `extraido_en` | ✅ | `g7b_ingesta/procesar.py`: `metadatos["propiedades"] = len(...)`. Bronce sí conserva todo, así que se recupera con un reprocesamiento cuando se corrija |

### Qué conviene hacer, en orden

1. **Corregir y desplegar el PR #21** (hecho en el PR de esta revisión, falta fusionar). El siguiente trabajo de Zyte ya trae tablas y avisos.
2. **Tope por versión y secciones completas** (defecto 1): `max_paginas` contado por versión y semilla `index.html` de cada versión. Es la mejora con más impacto: hoy 2.79 queda vacía.
3. **Variantes de versión en vez de duplicados** (no lo propone la auditoría y pesa más que el defecto 4): la página de 4.5 igual a la de 5.2 se guarda como variante del documento aceptado, con su versión.
4. **Relevancia como etiqueta en documentación oficial** (defecto 4): `relevancia_min: 0` para `blender-manual` y etiqueta `P6` cuando no coincida nada. Gracias a la huella de reglas, el cambio en el catálogo reevalúa solo el manual, sin tocar lo demás.
5. **Conservar la estructura hasta MongoDB** (defecto 5). Cuidado con el límite de 512 MB de Atlas M0: hoy la base ocupa 3,15 MB, con margen de sobra.

## 3. Azure (sección 4)

| Afirmación | Veredicto | Comentario |
|---|---|---|
| La cuenta del lago cumple las buenas prácticas (TLS 1.2, sin acceso público, borrado suave, ciclo de vida) | ✅ | Sin cambios necesarios |
| El job de Container Apps con identidad administrada y mínimo privilegio | ✅ | Solo corre `auditoria.py`; el ETL sigue en GitHub Actions. Es una decisión de costo razonable |
| OIDC configurado solo para una rama vieja y solo para ACR | ✅ | Para usarlo con el lago hay que federar `environment:amatista1` y dar *Storage Blob Data Contributor* sobre el contenedor `lago` |
| «El 4 de noviembre venció la SAS y se detuvieron las tareas» | ⚠️ | Fue una de las causas. La otra: del 11 al 16 de noviembre GitHub no disparó horarios en este repositorio. La resolvió el ciclo único (sección 5) |
| Agregar `DefaultAzureCredential` a `Lago.desde_entorno()` | ✅ recomendado | Compatible con SAS y Azurite si se activa solo con `AZURE_STORAGE_ACCOUNT_URL`. Pendiente: necesita a la vez cambios en Azure (identidad federada, rol) y en los workflows (`id-token: write`, `azure/login`) |

## 4. Mapa de documentación (sección 5)

Correcto en general. Desde la auditoría se agregaron [operación 24/7](../OPERACION_24_7.md) (ciclo, aviso, programador externo y reprocesamiento) y esta carpeta `docs/auditorias/`.

## 5. Hallazgo de esta revisión: el PR #21 rompió las pruebas y el despliegue a Zyte

Al fusionar el PR #21 (16 nov, 04:18 UTC), **Pruebas** y **Desplegar a Zyte** fallaron. La causa:

- En `fragmentos_sphinx.py`, `_texto()` llamaba a `re.sub(r"\s+", " ".join(...))` sin el texto de reemplazo: `TypeError` en cada página.
- La codificación del PR cambió las tildes por `�`. En `manual_sphinx.py` eso convirtió `replace("¶", "")` en `replace("�", "")`, así que el símbolo de párrafo volvía a los títulos.

Corregido en este PR, que restaura las tildes desde la versión anterior. Pruebas en local: 139 aprobadas, 9 saltadas (las de Azurite). Mientras no se fusione, Zyte sigue con la araña anterior, que funciona.
