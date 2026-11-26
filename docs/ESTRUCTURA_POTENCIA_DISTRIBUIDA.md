# Estructura Distribuida de Potencia 24/7 (G7B · MongoDB Flex · VM Oracle · Auditores IA)

Este documento describe cómo operan en conjunto las cinco piezas activas del ecosistema de datos y auditoría de **G7B + Amatista IA**, qué responsabilidad exclusiva tiene cada nodo, qué límites y candados protegen los datos y dónde vive cada resultado.

---

## 1. Visión general de los 5 motores

| Nodo / Servicio | Rol exclusivo | Qué lee | Dónde escribe | Candado principal |
|---|---|---|---|---|
| **1. GitHub Actions + Zyte (`Ciclo G7B 24/7`)** | Extracción documental masiva y embudo determinista | Manuales Sphinx (`objects.inv`, 16 capítulos en 3 LTS), APIs de Stack Exchange / Stack Overflow / GameDev, feeds (`arXiv`, blogs) y catálogos (`Poly Haven`, `ambientCG`, `GitHub Releases`) | Azure Blob (`bronce/`, `plata/`, `oro/`, `control/`) y MongoDB (`conocimiento_3d.documentos`, `g7b_catalogo.*`, `g7b_panel.senales`) | Regla 4: solo entra `activa: true` + `licencia_verificada: true` + respeto estricto a `robots.txt`. `bronce/` nunca se sobrescribe. |
| **2. VM de Oracle (`158.101.118.222`)** | Motor multinúcleo de telemetría de hardware (**cero retención en disco**) | Snapshots públicos `CC0` de Blender Open Data, matriz `caniuse-web3d` (`CC-BY-4.0`) y cabeceras estructuradas de hardware en `projects.blender.org` (sin prosa de usuarios) | Solo en RAM (`/dev/shm`) y bandeja efímera `/tmp/g7b-bandeja-salida` → vaciada por `relevo_github_24h.py` hacia la rama aislada `telemetria-vm-24h` en GitHub | **Cero retención local:** cada lote `.jsonl.gz` y `.matriz.json.gz` se verifica con `SHA-256` al subir a GitHub y se borra de inmediato en la VM. `amatista-nodo` permanece congelado. |
| **3. MongoDB Atlas Flex (`Cluster1`, MongoDB 8.0)** | Almacén documental operativo, búsqueda híbrida (léxica + vectorial) y analítica agregada | Recibe documentos filtrados por G7B, promociones auditadas por `amatista-ia` y matrices estadísticas de hardware | Bases `conocimiento_3d`, `g7b_catalogo`, `g7b_panel`, `g7b_analitica` y `telemetria_3d` | Nadie fuera de G7B escribe en `conocimiento_3d.documentos`. Los embeddings semánticos se generan en el servidor (`voyage-4-lite` `autoEmbed`). |
| **4. PC Local (`amatista-ia`, `qwen3:8b` + `bge-m3`)** | Auditor primario 24/7 en cuarentena y única puerta de promoción | `conocimiento_3d.documentos` (usuario de solo lectura) + Canon v5 de Supabase (`SUPABASE_PUBLISHABLE_KEY`) | Cuarentena local `salidas/consola/lote_NNN.jsonl`, cierres de 20 muestras en Escritorio y, tras veredicto humano (`consola promover`), `conocimiento_3d.conocimiento_auditado` | `max_lotes_esperando: 50` (flujo sin pausa) y exclusión automática (`excluir_carpetas`) para no auditar documentos ya revisados por Gemini API. |
| **5. Gemini API (`lab-limites-gemini`, baja frecuencia)** | Segundo auditor independiente para documentación pública pesada y contraste A/B | Fuentes públicas abiertas de `conocimiento_3d.documentos` (solo lectura) + Canon v5 vivo de Supabase | Lotes locales aislados `resultados/ciclo_24h/lote_api_NNN.jsonl` y resúmenes por lote | Cero datos de alumnos; frecuencia limitada (`24–30 s` entre llamadas ≈ 2–2.5 RPM), cascada automática `3.5-flash → 3.5-flash-lite → 3.1-flash-lite` y exclusión mutua con `amatista-ia`. |

---

## 2. Flujo de punta a punta

```
Fuentes abiertas (Blender Manual 16 cap., Stack Overflow, Stack Exchange, GameDev, arXiv)
      │
      ▼  [Vigilar (Geodar Radar) + Zyte Scrapy Cloud]
Azure Blob Storage (zona bronce/ — inmutable, lectura con split("\n") segura ante U+2028/U+2029)
      │
      ▼  [Procesar (Embudo determinista de 5 etapas) + Publicar]
MongoDB Atlas Flex (Cluster1) ──► conocimiento_3d.documentos
      │                            ├─ Índice Atlas Search: busqueda_3d (con sinonimos_3d Maya/Max/ES ↔ Blender)
      │                            └─ Índice Vector Search: vec_texto (autoEmbed voyage-4-lite)
      │
      ├──────────────────────────────────────────┐
      ▼ (orden doc_id asc · sin cruce)           ▼ (round-robin más pesados · 2–2.5 RPM · sin cruce)
Auditor Local (qwen3:8b + Canon v5)        Gemini API 24h (cascada 3.5-flash + Canon v5)
  salidas/consola/lote_NNN.jsonl             resultados/ciclo_24h/lote_api_NNN.jsonl
      │
      ▼  [20 muestras por lote → Veredicto humano → python -m consola promover]
MongoDB Atlas Flex (Cluster1) ──► conocimiento_3d.conocimiento_auditado (índice vec_auditado)
                                         │
                                         ▼
                               Geoda / Amatista (solo lee lo aprobado)
```

En paralelo, el carril de **telemetría de hardware** corre sin tocar la colección documental:

```
Blender Open Data (CC0) + Can I Use Web3D (CC-BY-4.0) + Cabeceras GPU Gitea (sin texto de usuario)
      │
      ▼  [VM Oracle · 3 núcleos ARM64 Neoverse-N1 · ProcessPoolExecutor en RAM /dev/shm · 50k benchmarks/lote]
/tmp/g7b-bandeja-salida (máx. 4 lotes en espera; si se llena, borra ZIP de /dev/shm y pausa)
      │
      ▼  [relevo_github_24h.py · verificación SHA-256 · borrado inmediato rm -f en la VM]
      ├──► GitHub (rama huérfana telemetria-vm-24h, commits con [skip ci]): .jsonl.gz + .matriz.json.gz
      └──► MongoDB Atlas Flex: telemetria_3d.matriz_rendimiento_gpu (curvas p25/p50/p75/p90 N1–N4 en < 5 ms)
```

---

## 3. Estructura de bases, colecciones e índices en MongoDB Atlas (`Cluster1`)

1. **`conocimiento_3d` (base principal de conocimiento):**
   - `documentos`: escrita **únicamente** por G7B (`g7b_ingesta.publicar`). Tiene índices clásicos (`doc_id_1`, `fuente_1_preguntas_1`), búsqueda léxica con sinónimos **`busqueda_3d`** y búsqueda semántica **`vec_texto`** (`voyage-4-lite`).
   - `sinonimos_3d`: equivalencias de términos entre 3ds Max / Maya / español y Blender (ej. `turbosmooth` / `meshsmooth` ↔ `subdivision surface` / `subsurf`), consumidas por `busqueda_3d`.
   - `conocimiento_auditado`: escrita **únicamente** por `python -m consola promover` cuando un lote local recibe veredicto aprobatorio. Tiene índice semántico **`vec_auditado`** (`voyage-4-lite`).
2. **`g7b_catalogo`:** colecciones `texturas`, `hdri`, `modelos`, `extensiones_blender` y `herramientas` pobladas por `geodar catalogar`.
3. **`g7b_panel`:** colección `senales` con resúmenes semanales agregados de foros comunitarios (`Solo metadatos`).
4. **`g7b_analitica`:** vistas materializadas del corpus (`resumen_fuentes` e `indice_operadores_bpy` con extracción de APIs `bpy.*` y `THREE.*`).
5. **`telemetria_3d`:** colección `matriz_rendimiento_gpu` con percentiles `p25 / mediana / p75 / p90` (`samples/min`) por dispositivo, backend (`OPTIX`, `HIP`, `METAL`, `CUDA`, `ONEAPI`, `CPU`), serie de Blender, escena y nivel Geoda (`N1–N4`), indexada con `idx_gpu_serie_backend_escena` e `idx_nivel_geoda_spm`.

---

## 4. Arañas masivas y paginación incremental

- **Manual oficial de Blender (`blender_docs` en Zyte):** guiada por `objects.inv` (`motor_extraccion/inventario_sphinx.py`, constante `SECCIONES_BLENDER` libre de dependencia a `scrapy`), cubre los **16 capítulos técnicos completos** en las versiones LTS `5.2`, `4.5` y `3.6` (`max_paginas: 7500`, `max_por_version: 2500`). `sensor_sphinx` detecta automáticamente cambios en el inventario, ampliaciones de alcance (`alcance`) o recorridos forzados puntuales (`--fuente blender-manual --forzar`).
- **Modo masivo de Stack Exchange / Stack Overflow (`sensor_stackexchange`):** soporta listas de `etiquetas`, múltiples `paginas` por vuelta, ventana histórica (`dias_desde` / `dias_hasta`), cursor persistente por etiqueta (`recorrer: true`) que avanza hacia preguntas menos votadas en cada ciclo de 6 horas, respeto automático a `backoff` y memoria de `VISTOS_MAX = 40000` IDs.

---

## 5. Órdenes operativas clave

```bash
# 1. Mapa y salud de todos los sensores en Geodar
python -m geodar mapa --markdown docs/GEODAR_RADAR_MAPA.md
python -m geodar salud

# 2. En la VM de Oracle (158.101.118.222): estado del motor 3x ARM64 en RAM
systemctl status g7b-telemetria-24h.service
cat /home/opc/g7b-telemetria-vm/estado/cursor_vm.json
ls -lh /dev/shm /tmp/g7b-bandeja-salida
```
