# Del rastreo al kernel: revisión del flujo completo (17 de noviembre de 2026)

Revisión de cada etapa, desde que se extrae la información hasta que llega a Geoda, con lo que entra y sale de cada una medido el 17 de noviembre, para construir el núcleo de Geoda sobre una base sólida. Cifras: [auditoría del flujo y de los datos](2026-11-17_auditoria_flujo_y_datos.md).

## 1. El camino hoy

```
 FUENTES ──► RADAR Y ARAÑAS ──► BRONCE ──┬─► EMBUDO ──► PLATA (documentos) ──► MongoDB (1.029 docs)
 (33 en el   (relevo, cada 6 h)  35.201   │                                         │
  catálogo)                      registros│                                         ✗ el kernel no lo usa
                                          │
                                          └─► TELEMETRÍA ──► PLATA (63.019 mediciones)
                                                                │
                                                     CUBO g7b.cubo/2 ─┬─ directas: 0
                                                                      └─ relativas: 63.019
                                                                │
                                          KERNEL GEODA (lote en Actions) ◄─ artefacto del cubo (dura 14 días)
                                            lee solo directas aceptadas de vista 3D → 0 elegibles
                                            → 4 planes, todos «base» (reglas escritas a mano)
                                                                │
                                          SALIDAS: artefactos de 14 días (informe, perfiles de laboratorio,
                                                   catálogo de operaciones) · geoda.json (solo conteos, perfiles: [])
                                                                │
                                          AMATISTA: lee geoda.json; el add-on decide con su copia de los contratos
```

## 2. Etapa por etapa

| Etapa | Estado | Lo que entrega al kernel | Problema para el kernel |
|---|---|---|---|
| Radar y arañas | ✅ Corre solo desde el 17 de noviembre (relevo) | Nada directo | — |
| Embudo y conocimiento | ⚠️ 1.029 documentos; rechaza las reextracciones (D1); todo en inglés | **Nada**: el kernel no consulta el conocimiento | Los planes explican «por qué» sin citar el manual, aunque las páginas exactas existen (Simplify, ajustes de EEVEE y Cycles, solución de problemas por GPU) |
| Telemetría y cubo | ✅ Cubo 2 con directas y relativas separadas | 0 directas; 63.019 relativas que el kernel **no usa** | Sin directas, todo plan es «base». Las relativas podrían dar **factores entre niveles** (cuánto rinde un N3 frente a un N2), con su etiqueta |
| Entrada del kernel | ⚠️ Descarga el **artefacto** de la última corrida del cubo | — | Si pasan 14 días sin cubo, el kernel no tiene insumo. Debería leer la versión vigente del lago (`control/cubo_actual.json`), con hash, como ya hace `descargar` |
| Kernel Geoda 0.1.0 | ⚠️ Funciona como lote; 4 planes «base» | — | No es una **biblioteca ni un servicio**: no hay una API estable ni versionada |
| Salidas | ⚠️ Artefactos de 14 días y `geoda.json` con solo conteos | — | Nada de lo que decide el kernel queda publicado, versionado ni disponible para Amatista |
| Amatista | ⏳ Pendiente | — | El cliente decide con su copia de los contratos, sin perfiles medidos |

## 3. Qué tiene ya el kernel (una buena base)

| Pieza | Archivo | Estado |
|---|---|---|
| Contratos | `geoda/contratos.py` | `g7b.huella/1` (rechaza datos personales), `g7b.perfil/1`, `g7b.plan/1` y `g7b.operacion/1` |
| Niveles N0–N4 | `geoda/niveles.py` | Reglas de las fichas técnicas, con confianza y motivos; las reutiliza el estándar de hardware |
| Perfiles | `geoda/perfiles.py` | De mediciones de vista 3D, con estados `confiable`, `provisional` y `base` según la evidencia |
| Costos | `geoda/costos.py` | Tabla de medianas del cubo; dice «sin datos» en lugar de inventar |
| Planificador | `geoda/planificador.py` | Plan con acciones como datos (ruta de la propiedad y valor) para poder deshacer, y una explicación en español |

## 4. Lo que falta para un núcleo sólido

1. **Un paquete de conocimiento versionado como única entrada del kernel.** Debe reunir:
   - los perfiles medidos (de las directas);
   - los factores relativos entre niveles (de las relativas, etiquetados como relativos);
   - el estándar de hardware;
   - las reglas de niveles;
   - el catálogo de operaciones;
   - el índice de citas del manual por ajuste.

   Todo con hashes. Esto es lo que se puede publicar.
2. **Una escalera de evidencia en cada plan:**
   - **medido en equipos como el tuyo:** directas, con suficientes equipos;
   - **provisional:** directas, todavía pocas;
   - **estimado por comparación pública:** relativas, nunca presentadas como medición propia;
   - **regla base.**
3. **Citas:** cada acción del plan enlaza la página del manual que la explica, en su versión de Blender.
4. **Leer el cubo vigente del lago**, no un artefacto que caduca.
5. **Una API estable del núcleo**, una función pura de huella y tarea a plan, determinista y sin red, con un **conjunto de casos de conformidad** que debe pasar cualquier implementación.
6. **Publicación:** el paquete de conocimiento y el kernel con su versión, para Amatista y para el público. Solo agregados; nunca mediciones individuales ni huellas.

## 5. Lo que se construyó el mismo día

Los seis puntos de la lista anterior quedan resueltos en esta versión. Los detalles están en [GEODA_NUCLEO.md](../GEODA_NUCLEO.md).

| Punto | Dónde quedó |
|---|---|
| 1. Paquete de conocimiento | `geoda/paquete.py` (`g7b.geoda.paquete/1`) |
| 2. Escalera de evidencia | `evidencia.escalera` y `evidencia.estimacion_relativa` en cada plan |
| 3. Citas del manual | `fuentes/citas_manual.yml`: 84 de 84 enlaces verificados contra `objects.inv` |
| 4. Cubo vigente del lago | `g7b_almacen/paquete_geoda.py` y `geoda_kernel.yml` |
| 5. API estable y conformidad | `geoda/nucleo.py` (`geoda.nucleo/1`) y `geoda/conformidad.json` (12 casos) |
| 6. Publicación | `oro/geoda/<versión>/paquete.json`, `control/geoda_paquete_actual.json` y `publicacion/geoda_paquete.json` |

**Sigue abierto:**

- las licencias del código y de los datos;
- las primeras mediciones directas;
- la API HTTP en Oracle;
- la integración con Amatista.
