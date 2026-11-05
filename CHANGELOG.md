# Cambios de G7B

La etiqueta **`hack4edu`** (commit `3aad461`) separa lo que ya teníamos de lo trabajado durante Hack4Edu. Comprobación: `git log --oneline hack4edu..main`.

## Durante Hack4Edu (después de la etiqueta `hack4edu`)

### 3 de noviembre de 2026
- **Geoda, cimientos (0.1.0):**
  - contratos `g7b.huella/1`, `g7b.perfil/1`, `g7b.plan/1` y `g7b.operacion/1`;
  - clasificación N0–N4 con motivos y confianza;
  - perfiles con evidencia desde el cubo real;
  - modelo de costos v0 (tabla del cubo, sin inventar);
  - planificador con acciones reversibles para Blender.

  18 pruebas.
- **La captura de telemetría conserva el nivel y la GPU del equipo** (sin datos personales), para que Geoda pueda clasificar.
- **Consolidación de ramas** en la PR #10:
  - `main`;
  - Geodar Radar y el plan maestro;
  - Azure privado (PR #9);
  - observaciones de calidad documental;
  - cuaderno de Deepnote.

  Las PR #4 a #8 no se fusionan: su cubo choca con el de `main` ([detalle](docs/hack4edu/README.md#4-lo-que-no-se-integró-y-por-qué)).
- **Repo ordenado:**
  - documentos de Azure en `docs/azure/`;
  - la primera arquitectura en `docs/historia/`;
  - índice en `docs/README.md`;
  - evidencia de Hack4Edu en `docs/hack4edu/`.
- **Cubo de telemetría** Parquet + DuckDB versionado, verificado con SHA-256 en Azure: 3,003 mediciones (PR #15).
- **Telemetría real** de la sonda y de Blender Open Data con controles numéricos, verificada en Azure (PR #14).
- Cuaderno de Deepnote para auditar la calidad documental.

## Antes de Hack4Edu (hasta la etiqueta `hack4edu`)

### 2 de noviembre de 2026
- **Primera integración real de punta a punta:** Zyte → Azure → embudo → MongoDB, con 2,353 registros y 987 documentos publicados (PR #11).
- En ramas, sin integrar todavía:
  - Geodar Radar y el plan maestro (PR #10);
  - Azure privado con identidad administrada y OIDC (PR #9);
  - observaciones de calidad de los 987 documentos.

### 1 de noviembre de 2026
- Plan rector, visión, fichas técnicas, horizonte, investigación del estado del arte y propuesta de estadía.
- Sonda de rendimiento v0; lago en Azure; catálogo de fuentes, sensores, disparadores y embudo de calidad.
- Araña estructurada del manual de Blender y Mongo idempotente; environment `amatista1` e interruptor `G7B_INGESTA_ACTIVA` (PR #1 a #3).
- En ramas, sin integrar: primer warehouse, publicación segura, pruebas en Azure y tablero HTML (PR #4 a #8).

### 31 de octubre de 2026
- Andamiaje de Scrapy, primer despliegue en Zyte y MongoDB ([historia](docs/historia/ARQUITECTURA_CLOUD.md)).
