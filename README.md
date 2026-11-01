# G7B

Base de conocimiento y de mediciones para un 3D libre que funcione en cualquier computadora. Proyecto separado de [Amatista](https://github.com/Maximiliano-cabello-mata/amatista): Amatista lo consume como un cliente más.

G7B reúne lo que se sabe (documentación de herramientas libres, técnicas publicadas por la industria y equivalencias con Maya y 3ds Max) y lo que se mide (rendimiento en computadoras reales, de las más viejas a las más potentes). Cada dato lleva fuente, versión y licencia. No es un motor 3D nuevo ni un fork de Blender: alimenta con datos al Corazón Amatista y a Blender Amatista.

**Estado:** andamio inicial.

- `motor_extraccion/`: las arañas de Scrapy que corren en Zyte: `blender_docs` (el manual en varias versiones, estructurado), `manual_sphinx` (cualquier manual hecho con Sphinx) y `paginas` (genérica). Se despliegan solas con cada push a `main`.
- `sonda/`: la sonda de rendimiento v0, que mide Blender en cualquier computadora ([cómo correrla](sonda/LEEME.md)).
- `g7b_lago/`: el lago de datos en Azure: copia de Zyte al lago y subida de mediciones.
- `fuentes/` y `g7b_ingesta/`: catálogo de fuentes, sensores, disparadores y el embudo de calidad ([cómo funciona](docs/INGESTA.md)).
- `infra/`: [qué nube está lista y qué falta](infra/LEEME.md), y [cómo configurar Azure](infra/azure/LEEME.md).

Lo siguiente es la fase F0 del plan.

## Documentos

- [Plan](docs/PLAN.md): qué es G7B, reglas de calidad, fuentes, telemetría, arquitectura, visualización, fases. **Es el documento rector.**
- [Arquitectura cloud (historia)](ARQUITECTURA_CLOUD.md): primer despliegue en Zyte y MongoDB, y los errores resueltos.
