# Auditoría Técnica y Estándares de Industria: Arañas, Trazabilidad y Arquitectura Azure en G7B

**Fecha de revisión:** 15 de noviembre de 2026  
**Repositorio auditado:** [Maximiliano-cabello-mata/amatista-g7b-etl](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl)  
**Propósito:** Documentar el diagnóstico de extremo a extremo de los datos actuales de G7B, los estándares de la industria y casos comparables para pipelines multi-nube, las causas exactas por las que la araña (`blender_docs` / `manual_sphinx`) pierde información y filtra páginas válidas, y la evaluación técnica de la infraestructura en Microsoft Azure frente al [Microsoft Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/data/executive-strategy-unified-data-platform).

## 1. Resumen Ejecutivo: Estado Real de los Datos y la Trazabilidad

El ecosistema G7B implementa un patrón de ingeniería de datos reconocido en producción que combina tres arquitecturas estándar:
1. **[Arquitectura Medallion (Bronce → Plata → Oro)](https://www.techment.com/blogs/medallion-architecture-explained/)** sobre almacenamiento de objetos en Azure Blob Storage (`g7blago09b52a0e`, contenedor `lago`).
2. **[Modern Data Stack in a Box (MDS-in-a-Box)](https://motherduck.com/blog/15-companies-duckdb-in-prod/)** mediante cómputo efímero en GitHub Actions que construye y valida cubos analíticos en [DuckDB y Apache Parquet](https://github.com/duckdb/dbt-duckdb/blob/main/README.md).
3. **[Curación Web y Monitoreo de Spiders](https://www.zyte.com/blog/storing-and-curating-data/)** desde Zyte Scrapy Cloud hacia MongoDB Atlas (`conocimiento_3d.documentos`) y publicación por contrato JSON estilo [GitHub Flat Data](https://githubnext.com/projects/flat-data/) (`publicacion/geoda.json`).

| División de Datos | Volumen Actual | Estado de Trazabilidad | Valor de Negocio Actual | Cuello de Botella Principal |
| :--- | :--- | :--- | :--- | :--- |
| **Documentación (`conocimiento_3d.documentos`)** | **995 documentos** aceptados en MongoDB (de 2,353 extraídos en el lote `883618-1-13`) | **Alta:** `doc_id` SHA-256, SimHash de 64 bits, URL, versión y archivo de origen en Bronce | **Medio-Alto:** Útil para consultas de nodos y mallas, pero incompleto en atajos y propiedades | La araña `manual_sphinx.py` ignora tablas `<table>`, duplica `<dd>` anidados y el embudo rechaza el 55.8 % por falta de palabras clave |
| **Cubo de Telemetría (`oro/cubo.duckdb`)** | **3,006 mediciones** (3,000 de [Blender Open Data](https://opendata.blender.org/download/) en revisión; 6 de sonda, 5 aceptadas) | **Excelente:** Tabla `procedencia`, verificación cruzada Parquet vs. DuckDB y `manifiesto.json` con SHA-256 | **Bloqueado para Geoda (`perfiles: []`):** `recomendaciones_habilitadas` es `false` | 0 mediciones con `sin_ventana = false` y `prueba = 'vista3d'` (el runner de Actions corre `blender -b` sin pantalla) |
| **Catálogos y Señales (`fuentes/catalogo.yml`)** | **19 fuentes activas** con licencia verificada (Poly Haven, ambientCG, GitHub, Discourse) | **Alta:** Huellas en `control/sensores.json` y respeto estricto a `robots.txt` | **Listo para ingesta continua** | Dependencia de token SAS (`AZURE_LAGO_URL`) en lugar de identidad federada OIDC en los workflows de datos |

## 2. Casos Documentados en la Industria Similares a G7B

Para evaluar la trazabilidad y el diseño multi-nube de G7B frente a sistemas reales que operan con Scrapy/Zyte, Azure, MongoDB, DuckDB y GitHub Actions, se contrastaron cuatro implementaciones de referencia:

| Caso de Referencia en la Industria | Arquitectura y Herramientas | Equivalente en `amatista-g7b-etl` | Lección Aplicable a G7B |
| :--- | :--- | :--- | :--- |
| **[Zyte Data-on-Demand Pipeline](https://www.zyte.com/blog/storing-and-curating-data/)** y **[Spidermon](https://www.zyte.com/blog/giving-spidey-senses-to-your-web-scraping-spiders-using-spidermon/)** | Scrapy Cloud (Zyte) → Almacenamiento de objetos → Cuadernos Jupyter de QA → **MongoDB Atlas** con deduplicación por hash | `motor_extraccion/` → `zyte_a_lago.py` → `embudo.py` → `analisis/deepnote/` → MongoDB (`conocimiento_3d`) | Zyte advierte que el fallo más costoso en scraping es el **fallo silencioso de cobertura de campos** (*field coverage drift*): la araña termina en verde pero omite elementos HTML críticos (como ocurrió con las tablas en `manual_sphinx.py`). |
| **[Datadex / MDS-in-a-Box](https://motherduck.com/blog/15-companies-duckdb-in-prod/)** y **[dbt-duckdb](https://github.com/duckdb/dbt-duckdb/blob/main/README.md)** | **GitHub Actions** (cómputo efímero) → **Parquet** en almacenamiento cloud → **DuckDB** embebido sin servidor 24/7 | `.github/workflows/cubo.yml` → `g7b_almacen/cubo.py` (`oro/cubo.duckdb` + `plata/mediciones.parquet`) | Mantener el almacenamiento desacoplado del cómputo reduce el gasto a centavos. La doble verificación de G7B (`EXCEPT ALL` entre Parquet y DuckDB y puntero atómico `control/cubo_actual.json`) cumple prácticas de grado industrial. |
| **[GitHub OCTO Flat Data](https://githubnext.com/projects/flat-data/)** ([githubocto/flat](https://github.com/githubocto/flat)) | **GitHub Actions** por horario → Extracción y agregación → Commit automático de archivo JSON versionado en el repositorio | `.github/workflows/geoda_publicar.yml` → `g7b_almacen/geoda_estado.py` → `publicacion/geoda.json` | Permite que aplicaciones externas (la API de Amatista en Oracle) lean el estado verificado sin exponer credenciales de Azure ni pagar una base de datos intermedia encendida todo el día. |
| **[Medallion Architecture con Contratos de Datos](https://datakitchen.io/blog/the-race-for-data-quality-in-a-medallion-architecture/)** y **[ODCS](https://datacontract-specification.com/)** | Capas **Bronce, Plata y Oro** gobernadas por esquemas explícitos y linaje tipo **[OpenLineage](https://openlineage.io/)** | `bronce/`, `plata/`, `oro/` + contratos `g7b.telemetria/1`, `g7b.cubo/1`, `g7b.perfil/1`, `g7b.plan/1` | Cada capa falla distinto: Bronce falla por credenciales vencidas o ausencias silenciosas; Plata falla por reglas de transformación que mutilan campos; Oro falla cuando faltan muestras representativas para activar reglas de negocio. |

## 3. Diagnóstico Profundo de la Araña (`blender_docs` y `manual_sphinx`)

La revisión del código en `motor_extraccion/spiders/` y `g7b_ingesta/` demuestra que la pérdida de datos **no es un fallo de Zyte**, sino el resultado de cinco filtros y selectores restrictivos programados en el repositorio que impiden recopilar toda la información del manual.

### 3.1. Los 5 defectos exactos en el código actual

| # | Archivo y Líneas | Qué hace actualmente el código | Consecuencia real en los datos de G7B |
| :--- | :--- | :--- | :--- |
| **1** | `motor_extraccion/spiders/blender_docs.py` (líneas 21–36) y `manual_sphinx.py` (líneas 56–59) | Solo define **10 rutas semilla** (`secciones`) y aplica un tope global `max_paginas = 3000` compartido entre las 4 versiones (`5.2`, `4.5`, `3.6`, `2.79`). | Quedan fuera secciones enteras del manual (*Animation & Rigging*, *Sculpting & Painting*, *UVs*, *Physics*, *Compositing*, *Grease Pencil*). Además, el tope global se agota en las versiones nuevas y deja a **Blender 2.79 con 0 documentos aceptados**. |
| **2** | `motor_extraccion/spiders/manual_sphinx.py` (línea 22, `_BLOQUES`) | El XPath `.//p[not(ancestor::table)]` excluye párrafos en tablas y **no incluye `.//table`**, `.//h4` ni bloques de advertencia (`div.admonition`). | En páginas basadas en tablas como *Industry Compatible Keymap* (línea 1 del lote) y *Common Shortcuts* (línea 116), **se pierden todos los atajos de teclado** y solo se guardan los encabezados vacíos. |
| **3** | `motor_extraccion/spiders/manual_sphinx.py` (líneas 29–31 y 97–103) | `texto_de(nodo)` ejecuta `.//text()` sobre cada `<dd>`. Cuando una propiedad padre contiene sub-propiedades `<dl><dt><dd>` anidadas, extrae todo el texto junto y luego vuelve a extraer cada hijo por separado. | **Duplicación interna severa** en páginas como *Vertex Groups*, *Multiresolution* y *Viewport*, ensuciando el texto para RAG y distorsionando el conteo de palabras. Además, `limpio()` solo borra `¶`, dejando el icono `\uf0c1` (``) en 262 títulos de Blender 3.6. |
| **4** | `g7b_ingesta/embudo.py` (líneas 145–153) y `fuentes/catalogo.yml` | Aunque `blender-manual` tiene `valor_min: 0` en la etapa 5 (*Valor*), la etapa 4 (*Relevancia*) exige `relevancia_min: 2.0` buscando coincidencias exactas con `fuentes/taxonomia.yml`. | **Destruye el 55.8 % de lo que descarga la araña (1,314 páginas rechazadas).** Cualquier página oficial del manual que explique una herramienta o nodo sin repetir las palabras de `taxonomia.yml` es rechazada con `"no responde ninguna pregunta del plan"`. |
| **5** | `g7b_ingesta/procesar.py` (líneas 45–50, `a_documento`) | Reemplaza la lista estructurada de propiedades por un entero (`metadatos["propiedades"] = len(registro["propiedades"])`) y omite `jerarquia`, `bloques_codigo` y `extraido_en`. | Aunque la araña extrajo cada propiedad con su nombre y descripción, **Plata y MongoDB reciben únicamente un número** y pierden la estructura semántica y la fecha exacta de extracción. |

### 3.2. Estándar de extracción completa (Full-Fidelity Scraping para RAG)

En sistemas de ingeniería de datos documentales (como los basados en [Spidermon de Zyte](https://www.zyte.com/blog/giving-spidey-senses-to-your-web-scraping-spiders-using-spidermon/) y arquitecturas ELT), una fuente primaria con licencia abierta (`CC-BY-SA-4.0` como `docs.blender.org`) debe procesarse bajo tres reglas:
1. **Extracción estructural íntegra en Bronce:** Capturar todos los encabezados (`h1`–`h4`), párrafos, listas, **tablas convertidas a Markdown (`| col | col |`)**, bloques de código `<pre>`, cuadros de nota/advertencia (`Note`, `Warning`, `Tip`), enlaces internos/externos resueltos y referencias de imágenes (`alt` + `src`), sin duplicar `<dd>` anidados.
2. **Separar clasificación temática de aceptación en fuentes primarias:** En documentos oficiales (`tipo: documentacion`), `taxonomia.yml` debe usarse para **etiquetar** qué preguntas (`P1`–`P6`) se relacionan con la página, pero **nunca para rechazar páginas válidas del manual** (`relevancia_min: 0`). Solo deben descartarse páginas sin contenido o duplicadas.
3. **Preservación de metadatos de Bronce a Oro:** Conservar intactos `propiedades`, `tablas`, `jerarquia`, `bloques_codigo`, `operadores_bpy` y `extraido_en` hasta MongoDB Atlas.

### 3.3. Especificación de cambios en código para recopilar toda la información

#### A. En `motor_extraccion/spiders/manual_sphinx.py`
* Limpiar caracteres residuales de Sphinx en todas las versiones: reemplazar tanto `"¶"` como `"\uf0c1"` (``).
* Para evitar que un `<dd>` padre duplique el texto de un `<dl>` hijo, extraer en `texto_dd(nodo)` únicamente los nodos de texto que no sean descendientes de un `<dl>` interno: `.//text()[not(ancestor::pre) and count(ancestor::dl) = $profundidad_dl]`.
* Agregar soporte de tablas HTML convirtiendo cada `<table>` en una tabla Markdown limpia y guardándola también en un campo estructurado `"tablas"`.
* Cambiar el límite `max_paginas` para que se cuente **por versión** (`self.paginas_por_version[version]`) y no deje a Blender `2.79` o `3.6` sin recorrido.

#### B. En `motor_extraccion/spiders/blender_docs.py`
* Incluir `"index.html"` o el mapa completo de secciones del manual (agregando `animation/index.html`, `sculpt_paint/index.html`, `grease_pencil/index.html`, `physics/index.html`, `compositing/index.html`, `scene_layout/index.html`, `files/index.html`, `editors/index.html`) para que no se quede encerrada en 10 subcarpetas.

#### C. En `fuentes/catalogo.yml` y `g7b_ingesta/embudo.py`
* En `fuentes/catalogo.yml`, dentro de `id: blender-manual`, actualizar los umbrales a:
  ```yaml
  umbrales: {relevancia_min: 0, valor_min: 0, valor_revision: 0}
  ```
* En `g7b_ingesta/embudo.py` (etapa 4), permitir que cuando `u["relevancia_min"] == 0` (fuentes primarias de documentación), si el documento no coincide con ninguna palabra clave de `taxonomia.yml`, no sea rechazado sino que reciba la etiqueta `"general"` o las preguntas base de su fuente (`preguntas = sorted(propias) or ["P6"]`) y pase como `ACEPTADO`.

#### D. En `g7b_ingesta/procesar.py`
* En `a_documento(registro, lago, fuente)`, conservar la estructura completa extraída por la araña:
  ```python
  if "contenido" in registro:
      texto = registro["contenido"]
      metadatos.update({
          k: registro[k]
          for k in (
              "version", "seccion", "programa", "operadores_bpy",
              "jerarquia", "propiedades", "bloques_codigo",
              "tablas", "extraido_en", "conteo_palabras"
          )
          if registro.get(k)
      })
  ```

## 4. Investigación y Auditoría de la Arquitectura en Microsoft Azure

Se auditó toda la configuración de Azure en el repositorio (`infra/azure/`, `docs/azure/`, `g7b_lago/`, `g7b_ops/` y `.github/workflows/`) contrastándola con las guías oficiales del **[Microsoft Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/data/executive-strategy-unified-data-platform)**, **[Azure Container Apps Jobs con Managed Identity](https://github.com/Azure-Samples/container-apps-jobs)** y **[Federated Credentials (OIDC) con GitHub Actions](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)**.

### 4.1. Cómo se maneja Azure hoy en la industria en proyectos similares

En pipelines modernos de datos sobre Azure (especialmente cuando se optimizan costos o créditos como *Azure for Students*), la industria sigue cinco patrones arquitectónicos:

1. **Almacenamiento Medallion en una sola cuenta con Lifecycle Management ([Guía de Tiers en Azure Blob](https://numlytics.com/blog/azure-blob-storage-tiers-guide/)):**
   * Incluso en entornos empresariales grandes, se recomienda usar una cuenta de almacenamiento `StorageV2` (`Standard_LRS`, `allowBlobPublicAccess: false`, `minimumTlsVersion: TLS1_2`, *soft-delete* de 7 días) con separación por prefijos (`bronce/`, `plata/`, `oro/`) y políticas automáticas de ciclo de vida que pasen `bronce/` a nivel *Cool* tras 30 días y eliminen archivos temporales (`tmp/`).
2. **Cero llaves estáticas ni SAS manuales (Passwordless con [OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect) y [Managed Identity](https://github.com/Azure-Samples/container-apps-jobs)):**
   * Los tokens SAS firmados con la llave primaria de la cuenta (`AccountKey`) se consideran deuda técnica porque o vencen y rompen los pipelines en silencio, o duran demasiado (1 año) y representan un riesgo si se filtran en un log.
   * El estándar actual es **Workload Identity Federation (OIDC)** entre GitHub Actions y Microsoft Entra ID (`azure/login@v2` con `id-token: write`, sin guardar secretos que expiren) y **`SystemAssigned` / `UserAssigned` Managed Identity** para los contenedores que corren dentro de Azure (`ManagedIdentityCredential` en Python).
3. **Cómputo Serverless que escala a cero con [Azure Container Apps Jobs](https://github.com/Azure-Samples/container-apps-jobs):**
   * En lugar de pagar máquinas virtuales encendidas 24/7 o clústeres caros de Databricks/AKS, las tareas por lotes (como construir el cubo DuckDB o auditar el lago) se empaquetan en contenedores sin puerto HTTP (*no ingress*) dentro de un entorno `WorkloadProfiles` (perfil `Consumption`), pagando únicamente por los segundos que dura el Job.
4. **Infraestructura como Código (IaC) declarativa con [Bicep y validación `what-if` en CI](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-github-actions):**
   * Todos los recursos y asignaciones de roles RBAC (`Storage Blob Data Reader`, `Storage Blob Data Contributor`, `AcrPull`) se versionan en archivos `.bicep`, se compilan en GitHub Actions (`az bicep build`) y se previsualizan con `az deployment group what-if` antes de tocar la suscripción.
5. **Observabilidad en Azure Monitor con tablas dedicadas ([Migración de Logs en Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/log-options)):**
   * Envío de `ContainerAppConsoleLogs` y `ContainerAppSystemLogs` vía `Microsoft.Insights/diagnosticSettings` en modo `Dedicated` hacia un workspace de Log Analytics con cuota diaria y retención controlada.

### 4.2. Radiografía de cómo está configurado TU Azure actualmente en G7B

Al inspeccionar tus archivos (`infra/azure/base_operativa.json`, `g7b-control-privado.bicep`, `g7b-operacion.bicep`, `g7b-ruta-logs.bicep`, `consolidar_azure.py` y `crear_lago.sh`), tu proyecto tiene **dos mundos conviviendo al mismo tiempo**:

| Componente en tu Azure (`westus2`, grupo `g7b`) | Configuración Actual en tu Repositorio | Evaluación frente al Estándar de Industria |
| :--- | :--- | :--- |
| **1. Cuenta del Lago (`g7blago09b52a0e`)** | `StorageV2`, `Standard_LRS`, `allowBlobPublicAccess: false`, `HTTPS only`, `TLS 1.2`, *soft-delete* de 7 días y `politica_ciclo.json` (`bronce/` a *Cool* a los 30 días; `tmp/` se borra a los 7 días). | **10/10 (Excelente).** Cumple punto por punto las buenas prácticas de seguridad y ahorro de costos en Azure Blob Storage. |
| **2. Entorno y Job Privado (`g7b-env-laboratorio-jobs-v3` + `g7b-smoke-laboratorio`)** | Entorno `WorkloadProfiles` (`Consumption`), Job manual sin ingress HTTP, usuario no-root en Dockerfile, imagen fijada por digest inmutable (`@sha256:aa21dd18...`) desde ACR privado (`g7bacr09b52a0e` con admin deshabilitado) e identidad `SystemAssigned` con rol `AcrPull` y `Storage Blob Data Reader` acotado exactamente al contenedor `lago`. | **9.5/10 (Nivel Senior / Producción).** El código de `g7b_ops/auditoria.py` y `consolidar_azure.py` aplica principio de mínimo privilegio real, verifica ausencia de deriva (*drift*) y usa `ManagedIdentityCredential` rechazando llaves SAS. |
| **3. Federación OIDC (`g7b-github-acr` en `configurar_publicacion_oidc.sh`)** | Identidad administrada de usuario federada con GitHub Actions (`https://token.actions.githubusercontent.com`), pero **atada únicamente a la rama `chatgpt/g7b-arquitectura-privada-ofertas-20261101` y solo con permisos sobre el ACR (`AcrPush`)**. | **7/10 (Incompleto).** Demostraste que OIDC funciona en tu suscripción, pero se quedó encerrado en la rama del PR #9 y solo sirve para subir la imagen Docker del auditor, no para que tus workflows de datos en `main` lean/escriban en el lago. |
| **4. Acceso al Lago desde los Workflows de Datos (`g7b_lago/lago.py`)** | `Lago.desde_entorno()` solo acepta `AZURE_LAGO_URL` (con token SAS pegado en el secreto de GitHub) o `AZURE_STORAGE_CONNECTION_STRING`. **No soporta `DefaultAzureCredential` / OIDC.** | **5/10 (El talón de Aquiles actual).** Por esta razón el 4 de noviembre venció la firma SAS y se detuvieron todas las tareas programadas (`vigilar.yml`, `zyte_a_lago.yml`, `procesar.yml`, `telemetria.yml`, `cubo.yml`). |
| **5. Plantillas Bicep (`g7b-control-privado.bicep` vs. `g7b-operacion.bicep`)** | Tienes el diseño dividido en 3 plantillas parciales y scripts de guardia que bloquean cambios, y el Job en Azure solo corre `auditoria.py` (que cuenta archivos) en lugar de correr el ETL real o el cubo. | **7.5/10 (Seguro pero fragmentado).** Tus controles preflight (`consolidar_azure.py`) son sumamente cuidadosos para no romper nada ni gastar crédito, pero mantienen la infraestructura de Azure haciendo solo una prueba de lectura (`auditoria.py`) mientras todo el trabajo real sigue corriendo en GitHub Actions con SAS. |

### 4.3. Cómo unificar tu Azure para que funcione 24/7 sin que vuelva a caducar ninguna llave

No necesitas pagar ni levantar más recursos en Azure (de hecho, correr los workflows en GitHub Actions y usar Azure Blob Storage como lago te ahorra casi todo tu crédito de $100 USD). Lo único que necesitas es **unificar la seguridad que ya construiste en `g7b_ops/` dentro de `g7b_lago/lago.py` y los workflows de `main`**:

1. **Habilitar OIDC en `g7b_lago/lago.py` (sin romper compatibilidad con SAS ni Azurite):**
   Agregar un tercer método en `Lago.desde_entorno()` para que, si existe `AZURE_STORAGE_ACCOUNT_URL` (por ejemplo `https://g7blago09b52a0e.blob.core.windows.net`), se conecte con `DefaultAzureCredential()` de `azure-identity`:
   ```python
   cuenta_url = os.environ.get("AZURE_STORAGE_ACCOUNT_URL")
   if cuenta_url:
       from azure.identity import DefaultAzureCredential
       nombre = os.environ.get("AZURE_LAGO_CONTENEDOR", "lago")
       cliente = ContainerClient(
           account_url=cuenta_url,
           container_name=nombre,
           credential=DefaultAzureCredential(),
       )
       return cls(cliente)
   ```
2. **Federar la rama `main` y el environment `amatista1` en tu identidad `g7b-github-acr` (o una identidad `g7b-github-lago`):**
   * Crear la credencial federada para `repo:Maximiliano-cabello-mata/amatista-g7b-etl:environment:amatista1` y `repo:Maximiliano-cabello-mata/amatista-g7b-etl:ref:refs/heads/main`.
   * Asignarle el rol **Storage Blob Data Contributor** (`ba92f5b4-2d11-453d-a403-e96b0029c9fe`) con alcance (`--scope`) exclusivo al contenedor `/subscriptions/.../storageAccounts/g7blago09b52a0e/blobServices/default/containers/lago`.
   * En tus workflows (`vigilar.yml`, `zyte_a_lago.yml`, `procesar.yml`, `telemetria.yml`, `cubo.yml`), agregar `permissions: id-token: write` y el paso `uses: azure/login@v2`. Con eso **nunca más volverá a caducar `AZURE_LAGO_URL`**.
3. **Completar la migración de logs planeada (`g7b-ruta-logs.bicep`):**
   * Cuando quieras usar el Job de Azure Container Apps para tareas pesadas, aplicar `g7b-ruta-logs.bicep` hacia `g7b-logs-laboratorio` para dejar lista la tabla dedicada antes del retiro definitivo de la API legacy de Log Analytics.

## 5. Mapa de Documentación del Repositorio frente a Estándares de Industria

Para tu portafolio profesional y la presentación de estadía, tu carpeta `docs/` ya cubre los cinco artefactos documentales que exigen los equipos de Data Engineering, mapeados así:

| Categoría Estándar en la Industria | Qué documenta | Archivos equivalentes que ya tienes en `amatista-g7b-etl` |
| :--- | :--- | :--- |
| **1. Architecture Decision Records (ADRs)** | Decisiones técnicas de diseño, alternativas descartadas y límites del estado del arte | `docs/investigacion/2026-11-01_novedad_kernel_3d.md`, `docs/OFERTAS_Y_GITHUB.md`, `docs/hack4edu/README.md` |
| **2. Data Contracts ([ODCS](https://datacontract-specification.com/))** | Esquemas estrictos de intercambio, licencias permitidas y reglas de validación | `geoda/contratos.py` (`g7b.huella/1`, `g7b.perfil/1`, `g7b.plan/1`), `fuentes/catalogo.yml`, `docs/CUBO.md` |
| **3. Data Lineage & Manifests ([OpenLineage](https://openlineage.io/))** | Trazabilidad por lote, hashes SHA-256 de archivos y tablas de procedencia | `g7b_almacen/cubo.py` (`manifiesto.json`, tabla `procedencia`), `control/procesados.json`, `control/zyte_trabajos.json` |
| **4. Data Quality Audit & Post-Mortems** | Auditorías estadísticas de muestras reales, conteo de rechazos y defectos de extracción | `docs/reportes/2026-11-02_observaciones_documentacion_g7b.md`, `docs/bitacoras/2026-11-02_integracion_real_g7b.md` |
| **5. Operational Runbooks & IaC Guides** | Procedimientos de recuperación, rotación de credenciales, `what-if` y diagnóstico sin cambios | `docs/azure/AZURE_24_7_CLOUD_SHELL.md`, `docs/azure/CIERRE_AZURE.md`, `docs/reportes/2026-11-11_estado_del_flujo.md` |
