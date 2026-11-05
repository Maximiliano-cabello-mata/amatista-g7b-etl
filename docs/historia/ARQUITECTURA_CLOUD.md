# Arquitectura Cloud y Estrategia de Infraestructura - Amatista G7B

> **Nota del 2026-11-01:** este documento queda como historia del primer despliegue (secciones 1 y 2). La hoja de ruta de la sección 3 la reemplaza [docs/PLAN.md](../PLAN.md). Fase A: los modelos `.glb` de A-Frame pertenecen a Amatista, que vive en Oracle, no a G7B. Fase B: la API de G7B se sirve desde Heroku y Azure se usa como lago de datos. Fase C: el procesamiento pesado va a Camber y a la PC local, y Azure solo para una semana de benchmarks planeada.

Este documento detalla la topología de la nube del proyecto Amatista, la configuración de bases de datos, el registro de errores superados durante la construcción del motor ETL, y la hoja de ruta para aprovechar los créditos de Microsoft Azure.

---

## 1. Topología Actual: Extracción y Base de Datos (MongoDB Atlas)

Actualmente, el motor de extracción (Web Scraping con Scrapy) se ejecuta de forma autónoma en **Zyte Scrapy Cloud**. Los datos extraídos viajan directamente a nuestra base de datos principal.

*   **Proveedor:** MongoDB Atlas (Capa *Always Free*).
*   **Base de Datos:** `conocimiento_3d`
*   **Colección:** `foros_crudos`
*   **Propósito:** Almacenamiento permanente y estructurado de metadatos, enlaces, títulos y, en el futuro, el texto completo de los foros y tutoriales. Al ser una base de datos NoSQL, es ideal para consumir estos datos desde nuestro backend en FastAPI.

### 🛡️ Configuración de Seguridad
Para permitir que los servidores dinámicos de Zyte escriban en Atlas, el firewall (**Network Access**) está configurado con la regla `0.0.0.0/0` (Allow Access From Anywhere).

---

## 2. Bitácora de Errores y Soluciones del Motor ETL

Durante el despliegue de la araña `blender_docs` en Zyte, enfrentamos y resolvimos los siguientes bloqueos técnicos críticos:

1.  **Error de Pipeline Inactivo (Datos no llegaban a MongoDB):**
    *   *Problema:* Zyte ejecutaba la araña en 6 segundos pero ignoraba el archivo `pipelines.py`.
    *   *Solución:* Se forzó la activación inyectando `ITEM_PIPELINES = {"motor_extraccion.pipelines.MongoPipeline": 300}` directamente en los **Raw Settings** de Zyte.
2.  **Error de Dependencias (`ModuleNotFoundError: No module named 'pymongo'`):**
    *   *Problema:* Zyte no tenía instalada la librería de MongoDB en sus contenedores en blanco.
    *   *Solución:* Se creó un `requirements.txt` y se modificó el archivo `scrapinghub.yml` añadiendo la directiva `requirements: file: requirements.txt` para forzar la instalación durante el `shub deploy`.
3.  **Error de Autenticación (`ValueError: Falta MONGO_URI`):**
    *   *Problema:* El pipeline de seguridad bloqueó la ejecución al no detectar la contraseña.
    *   *Solución:* Se añadió la variable a los Raw Settings.
4.  **Error de Sintaxis de Conexión (`Invalid URI scheme`):**
    *   *Problema:* Zyte leía comillas o espacios en blanco antes del protocolo de MongoDB, rebotando la conexión.
    *   *Solución:* Se inyectó la cadena limpia y sin comillas dobles: `MONGO_URI = mongodb+srv://<usuario>:<password>@cluster...`

---

## 3. Hoja de Ruta: Integración con Microsoft Azure

Aprovechando los créditos estudiantiles de Microsoft Azure (vía GitHub Student Developer Pack), expandiremos la infraestructura para tareas de alto rendimiento que MongoDB Atlas no está diseñado para manejar. La estrategia se divide en tres fases para no agotar el saldo:

### Fase A: Almacenamiento de Modelos 3D (Azure Blob Storage)
*   **Propósito:** Crear una "bodega industrial" (CDN) para almacenar los archivos `.glb` generados en Blender.
*   **Beneficio:** Evita saturar el almacenamiento gratuito de MongoDB Atlas. Azure servirá los modelos 3D directamente a la experiencia web de A-Frame con latencia ultrabaja, consumiendo solo centavos al mes.

### Fase B: Despliegue Automatizado del Backend (Azure App Service)
*   **Propósito:** Alojamiento profesional para la API de FastAPI.
*   **Beneficio:** Implementar Integración Continua (CI/CD). Cada `git push` a la rama principal actualizará automáticamente el backend en Azure, exponiendo la base de datos de MongoDB a nuestra PWA (amatista-3d.tech) de manera segura y escalable.

### Fase C: Laboratorio de Inteligencia Artificial (Azure Virtual Machines)
*   **Propósito:** Orquestación de pipelines RAG (Retrieval-Augmented Generation) y pruebas con modelos locales (Llama 3.1 8B, Qwen).
*   **Beneficio:** Alquilar servidores de alta capacidad de cómputo por horas para procesar embeddings y vectorizar el texto extraído de los foros. Esto evitará cuellos de botella en el hardware local (Ryzen 5) y usará estratégicamente el presupuesto temporal.
