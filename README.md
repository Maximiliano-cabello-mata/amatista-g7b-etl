# G7B

Base de conocimiento y de mediciones para un 3D libre que funcione en cualquier computadora. Proyecto separado de [Amatista](https://github.com/Maximiliano-cabello-mata/amatista): Amatista lo consume como un cliente más.

G7B reúne lo que se sabe (documentación de herramientas libres, técnicas publicadas por la industria y equivalencias con Maya y 3ds Max) y lo que se mide (rendimiento en computadoras reales, de las más viejas a las más potentes). Cada dato lleva fuente, versión y licencia. No es un motor 3D nuevo ni un fork de Blender: alimenta con datos al Corazón Amatista y a Blender Amatista.

**Estado (2026-11-02):** prueba manual real de extremo a extremo completada: Zyte → Azure Bronce → embudo → Azure Plata → MongoDB. Se importaron **2,353 registros**: 987 aceptados, 52 en revisión y 1,314 rechazados; el publicador reportó **987 documentos nuevos** y 0 actualizados. Esa cifra no es el total actual de MongoDB. Ver la [bitácora técnica y las seis ejecuciones](docs/bitacoras/2026-11-02_integracion_real_g7b.md).

**Producción continua: pendiente de validación.** Falta comprobar el conteo posterior en MongoDB, la idempotencia, muestras de calidad y la continuidad de la autenticación Azure. Los workflows programados requieren `G7B_INGESTA_ACTIVA=true`; esta prueba manual no acredita su operación continua. La prioridad de telemetría y el cubo permanece en el [plan, sección 0](docs/PLAN.md#0-rumbo-actualizado-2026-11-01-tarde).

**Proyecto hermano:** [Amatista](https://github.com/Maximiliano-cabello-mata/amatista), la plataforma que enseña y, desde el 2026-11-01, un centro de conocimiento 3D. Son proyectos separados que se alimentan: G7B mide y decide; Amatista enseña, recomienda y guarda los datos personales. Ver [VISION.md](docs/VISION.md).

- `motor_extraccion/`: las arañas de Scrapy que corren en Zyte: `blender_docs` (el manual en varias versiones, estructurado), `manual_sphinx` (cualquier manual hecho con Sphinx) y `paginas` (genérica). Se despliegan solas con cada push a `main`.
- `sonda/`: la sonda de rendimiento v0, que mide Blender en cualquier computadora ([cómo correrla](sonda/LEEME.md)).
- `g7b_lago/`: el lago de datos en Azure: copia de Zyte al lago y subida de mediciones.
- `fuentes/` y `g7b_ingesta/`: catálogo de fuentes, sensores, disparadores y el embudo de calidad ([cómo funciona](docs/INGESTA.md)).
- `infra/`: [qué nube está lista y qué falta](infra/LEEME.md), y [cómo configurar Azure](infra/azure/LEEME.md).

Los siguientes pasos de ingesta están en la [bitácora, trabajo pendiente](docs/bitacoras/2026-11-02_integracion_real_g7b.md#8-trabajo-pendiente), en coordinación con la fase F0 del plan.

## Documentos

- [Puente G7B → Geoda → Amatista](docs/GEODA_PUENTE_24_7.md): publicador de conteos agregados tras procesar y construir el cubo; sus recomendaciones de rendimiento seguirán desactivadas hasta obtener evidencia. Incluye la operación continua y la activación segura.

- [Cubo de telemetría](docs/CUBO.md): **publicado y verificado en Azure** el 2026-11-03, con 3,003 mediciones (tres aceptadas y 3,000 en revisión). Parquet + DuckDB versionados, seis dimensiones y deduplicación. Se reconstruye tras cada captura exitosa. Incluye cuaderno de consulta para Deepnote; no genera recomendaciones de Geoda.

- [Telemetría: captura y controles](docs/TELEMETRIA.md): primera ejecución cloud verificada el 2026-11-03: tres mediciones de sonda aceptadas y 3,000 mediciones públicas en revisión, con escritura y lectura comprobadas en Azure. [Ejecución 41707925151](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41707925151). Programación semanal habilitada; continuidad aún por observar. Cubo y Geoda pendientes.

- [Visión](docs/VISION.md): el norte del proyecto y su relación con Amatista.
- [Plan](docs/PLAN.md): qué es G7B, reglas de calidad, fuentes, telemetría, arquitectura, visualización, fases. **Es el documento rector.**
- [Arquitectura cloud (historia)](ARQUITECTURA_CLOUD.md): primer despliegue en Zyte y MongoDB, y los errores resueltos.
- [Ingesta](docs/INGESTA.md): sensores, disparadores, el embudo de calidad y la publicación en MongoDB.
- [Bitácoras](docs/bitacoras/): lo que se hizo cada día, los errores y el plan del día siguiente. Última: [2026-11-02 — integración real G7B](docs/bitacoras/2026-11-02_integracion_real_g7b.md).
- [Integración con Amatista](docs/investigacion/2026-11-01_integracion_amatista_g7b.md): cómo se conectan los dos proyectos, flujos y orden.
- [Reporte de propuestas](docs/reportes/2026-11-01_propuestas.md): cuáles son realistas, cuáles no y hacia dónde va el proyecto.
- [Fichas técnicas](docs/FICHAS_TECNICAS.md): la definición exacta de cada concepto interno (Geoda, Corazón, niveles N0 a N4, perfil, fluidez, cubo...).
- [Horizonte](docs/reportes/2026-11-01_horizonte.md): hasta dónde pueden llegar Amatista, G7B y Geoda, por etapas, y dónde está el techo.
- [¿Ya existe esto?](docs/investigacion/2026-11-01_novedad_kernel_3d.md): investigación del estado del arte: qué existe, en qué se diferencia, por qué falta lo que falta y si la necesidad es actual, futura o no prevista.
- [Ofertas y GitHub](docs/OFERTAS_Y_GITHUB.md): qué oferta del Developer Pack y qué función de GitHub cumple cada papel, y cuándo activarla.
- [Propuesta de estadía](docs/estadia/2026-11-01_propuesta_estadia.md): la versión integrada Amatista + G7B como trabajo final.
