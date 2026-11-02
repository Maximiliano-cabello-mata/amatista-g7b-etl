# G7B

Base de conocimiento y de mediciones para un 3D libre que funcione en cualquier computadora. Proyecto separado de [Amatista](https://github.com/Maximiliano-cabello-mata/amatista): Amatista lo consume como un cliente más.

G7B reúne lo que se sabe (documentación de herramientas libres, técnicas publicadas por la industria y equivalencias con Maya y 3ds Max) y lo que se mide (rendimiento en computadoras reales, de las más viejas a las más potentes). Cada dato lleva fuente, versión y licencia. No es un motor 3D nuevo ni un fork de Blender: alimenta con datos al Corazón Amatista y a Blender Amatista.

**Estado (2026-11-02):** Azure G7B v3 desplegado con WorkloadProfiles/Consumption; despliegue, RBAC y smoke manual `Succeeded` según los logs reportados por el usuario. Commit `63da9c4` publicado en la rama del PR #9. Esto no valida acceso del Job al lago ni ETL real; presupuesto y revocación SAS no verificados. Ver [bitácora y evidencia](docs/bitacoras/2026-11-02.md). El hito previo de 5 documentos en MongoDB corresponde al 2026-11-01; no es resultado de este smoke. La ingesta programada se mantiene documentada como apagada (`G7B_INGESTA_ACTIVA`), sin revalidación en esta revisión.

**Proyecto hermano:** [Amatista](https://github.com/Maximiliano-cabello-mata/amatista), la plataforma que enseña y, desde el 2026-11-01, un centro de conocimiento 3D. Son proyectos separados que se alimentan: G7B mide y decide; Amatista enseña, recomienda y guarda los datos personales. Ver [VISION.md](docs/VISION.md).

- `motor_extraccion/`: las arañas de Scrapy que corren en Zyte: `blender_docs` (el manual en varias versiones, estructurado), `manual_sphinx` (cualquier manual hecho con Sphinx) y `paginas` (genérica). Se despliegan solas con cada push a `main`.
- `sonda/`: la sonda de rendimiento v0, que mide Blender en cualquier computadora ([cómo correrla](sonda/LEEME.md)).
- `g7b_lago/`: el lago de datos en Azure: copia de Zyte al lago y subida de mediciones.
- `fuentes/` y `g7b_ingesta/`: catálogo de fuentes, sensores, disparadores y el embudo de calidad ([cómo funciona](docs/INGESTA.md)).
- `infra/`: [qué nube está lista y qué falta](infra/LEEME.md), y [cómo configurar Azure](infra/azure/LEEME.md).

Lo siguiente es la fase F0 del plan.

## Documentos

- [Visión](docs/VISION.md): el norte del proyecto y su relación con Amatista.
- [Plan](docs/PLAN.md): qué es G7B, reglas de calidad, fuentes, telemetría, arquitectura, visualización, fases. **Es el documento rector.**
- [Arquitectura cloud (historia)](ARQUITECTURA_CLOUD.md): primer despliegue en Zyte y MongoDB, y los errores resueltos.
- [Ingesta](docs/INGESTA.md): sensores, disparadores, el embudo de calidad y la publicación en MongoDB.
- [Bitácoras](docs/bitacoras/): lo que se hizo cada día, los errores y el plan del día siguiente. Última: [2026-11-02](docs/bitacoras/2026-11-02.md).
- [Integración con Amatista](docs/investigacion/2026-11-01_integracion_amatista_g7b.md): cómo se conectan los dos proyectos, flujos y orden.
- [Reporte de propuestas](docs/reportes/2026-11-01_propuestas.md): cuáles son realistas, cuáles no y hacia dónde va el proyecto.
- [Fichas técnicas](docs/FICHAS_TECNICAS.md): la definición exacta de cada concepto interno (Geoda, Corazón, niveles N0 a N4, perfil, fluidez, cubo...).
- [Horizonte](docs/reportes/2026-11-01_horizonte.md): hasta dónde pueden llegar Amatista, G7B y Geoda, por etapas, y dónde está el techo.
- [¿Ya existe esto?](docs/investigacion/2026-11-01_novedad_kernel_3d.md): investigación del estado del arte: qué existe, en qué se diferencia, por qué falta lo que falta y si la necesidad es actual, futura o no prevista.
- [Ofertas y GitHub](docs/OFERTAS_Y_GITHUB.md): qué oferta del Developer Pack y qué función de GitHub cumple cada papel, y cuándo activarla.
- [Propuesta de estadía](docs/estadia/2026-11-01_propuesta_estadia.md): la versión integrada Amatista + G7B como trabajo final.
