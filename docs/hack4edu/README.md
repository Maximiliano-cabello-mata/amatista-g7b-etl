# G7B en Hack4Edu: antes y ahora, comprobable

**Corte:** etiqueta de Git **`hack4edu`**, creada el 3 de noviembre de 2026 a las 14:14 (UTC−6). Apunta al commit **`3aad461`**, el `main` de la noche del 2 de noviembre. Todo lo que está en `3aad461` o antes es **lo que ya teníamos**. Todo lo que entra después es **lo trabajado durante Hack4Edu**, hasta el viernes 6 de noviembre.

La plataforma completa (Amatista) tiene su propio corte, con la misma etiqueta, en su repo: [`docs/hack4edu/`](https://github.com/Maximiliano-cabello-mata/amatista/tree/main/docs/hack4edu).

## Cómo comprobarlo uno mismo

```bash
git clone https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl.git && cd amatista-g7b-etl
git show hack4edu --stat              # el corte y su mensaje
git log --oneline hack4edu            # todo lo anterior (lo que ya teníamos)
git log --oneline hack4edu..main      # todo lo posterior (lo de Hack4Edu)
git diff --stat hack4edu..main        # qué archivos cambiaron desde el corte
python -m pytest pruebas -q           # las pruebas, en cualquier punto
```

## 1. Lo que YA TENÍAMOS (en `hack4edu` = `3aad461`)

32 commits, del 31 de octubre al 2 de noviembre de 2026.

| Pieza | Qué hace | Evidencia |
|---|---|---|
| Arañas en Zyte | `blender_docs` (manual de Blender en 4 versiones), `manual_sphinx`, `paginas` | `motor_extraccion/`; despliegue automático a Zyte |
| Lago en Azure | Zonas bronce, plata y oro en Blob Storage (West US 2) | `g7b_lago/`, `infra/azure/crear_lago.sh` |
| Embudo de calidad | 5 etapas (entrada, calidad, duplicados, relevancia, valor) con motivos | `g7b_ingesta/`, `docs/INGESTA.md` |
| **Primera integración real de punta a punta** | Zyte → Azure → embudo → MongoDB: 2,353 registros, **987 documentos publicados** | [Bitácora del 2 de noviembre](../bitacoras/2026-11-02_integracion_real_g7b.md) |
| Sonda de rendimiento v0 | Mide Blender (vista 3D, edición, animación, render) en cualquier equipo | `sonda/g7b_sonda.py` |
| Plan, visión, fichas técnicas, investigación | El rumbo del proyecto y el estado del arte | `docs/` |

**Ya existían en ramas al momento del corte, pero sin integrar a `main`:**

| Rama | Qué trae | Último commit |
|---|---|---|
| `claude/project-thread-pgechg` (PR #4) | Primer warehouse: cubo DuckDB sobre Open Data, `perfiles.json` v0, compuerta de calidad, latido | `e9fa65a` · 2-nov |
| `chatgpt/…-publicacion-segura-colab…` (PR #5) | Publicación versionada tras la compuerta; laboratorio Colab | `d6a106d` · 1-nov |
| `chatgpt/…-prueba-blender-azure…` y `…-duckdb-azure…` (PR #6, #7) | Blender real en Actions → Azure; primer `cubo.duckdb` en Azure | `abe2712`, `7aea045` · 1-nov |
| `chatgpt/tablero-g7b-html…` (PR #8) | Tablero HTML sin conexión | `7cfafb0` · 1-nov |
| `chatgpt/g7b-arquitectura-privada-ofertas…` (PR #9) | Azure privado: Job con identidad administrada, OIDC, catálogo de 82 ofertas | `c6d1257` · 2-nov |
| `claude/peaceful-tesla-ctqaps` (PR #10) | Plan maestro, revisión de ofertas y **Geodar Radar** | `69430af` · 2-nov |
| `docs/observaciones-documentacion…` | Auditoría de calidad de los 987 documentos | `2894cf0` · 2-nov |

## 2. Lo trabajado DURANTE Hack4Edu (después de `hack4edu`)

| Fecha | Qué | Evidencia |
|---|---|---|
| 3-nov | **Telemetría real:** sonda y Blender Open Data con controles numéricos → Azure | PR #14 (`a3dcfc1`); [TELEMETRIA.md](../TELEMETRIA.md); [ejecución 41707925151](https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/actions/runs/41707925151) |
| 3-nov | **Cubo de telemetría** Parquet + DuckDB versionado y verificado con SHA-256 en Azure: 3,003 mediciones | PR #15 (`408ef9c`); [CUBO.md](../CUBO.md) |
| 3-nov | Cuaderno Deepnote de calidad documental | `analisis/deepnote/` (`b7c8a11`) |
| 3-nov | **Consolidación** (esta rama, PR #10): `main` + Geodar Radar + Azure privado (#9) + observaciones + Deepnote. **112 pruebas pasan sin nube y 9 más con Azurite** | `git log hack4edu..claude/peaceful-tesla-ctqaps` |
| 3-nov | **Cimientos de Geoda:** detectar (N0–N4), perfiles con evidencia desde el cubo real, modelo de costos v0, planificador con acciones reversibles; la captura conserva GPU y nivel | `geoda/`, [GEODA.md](../GEODA.md), `pruebas/test_geoda.py` (18 pruebas) |
| 4 al 6-nov | Lo que sigue (sección 3) | — |

## 3. Lo que se va a trabajar hasta el viernes 6

Coincide con el plan de la etiqueta de Amatista ([CORTE_HACK4EDU.md](https://github.com/Maximiliano-cabello-mata/amatista/blob/main/docs/CORTE_HACK4EDU.md)).

| Día | G7B | Cómo se comprueba |
|---|---|---|
| Mié 4 | Fusionar la consolidación (PR #10). Decidir qué se porta de las PR #4 a #8: su cubo choca con el de `main`, así que se conserva el de `main` y se traen encima la compuerta y la publicación. Rotar la SAS (plan maestro, Fase 0) | `pytest` en verde en `main` |
| Jue 5 | `geoda perfiles` en `cubo.yml`: cada cubo publicado trae su `perfiles.json` con hash. Correr la sonda en 3 o más equipos reales para tener perfiles «provisionales» o «confiables» | `perfiles.json` publicado en Azure con evidencia |
| Vie 6 | `perfiles.json` dentro del add-on de Amatista (T-188) y recorrido de la demostración | Guion del video ([Amatista › docs/hack4edu/video](https://github.com/Maximiliano-cabello-mata/amatista/tree/main/docs/hack4edu/video)) |

## 4. Lo que NO se integró, y por qué

**PR #4 a #8 (primer warehouse):** su `g7b_almacen/cubo.py` es otra implementación del cubo y choca con la de `main` (PR #15), que ya está verificada en Azure. No se fusiona a ciegas.

**Propuesta:** conservar el cubo de `main` y traer encima solo lo que no existe:
- la compuerta de calidad (`calidad.py`);
- la publicación versionada (`publicacion.py`);
- el tablero.

Los perfiles ya los genera Geoda desde el cubo de `main`.
