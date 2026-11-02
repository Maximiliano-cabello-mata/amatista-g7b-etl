"""El cubo: plata en Parquet y el modelo en estrella en DuckDB (oro).

    bronce/opendata/<día>/<copia>.zip  ─┐
    bronce/sonda/<día>/*.json          ─┴─► plata/opendata/render.parquet
                                            plata/sonda/medicion.parquet
                                              │
                                              ▼
                                            oro/cubo.duckdb              (todo junto, para DuckDB y Deepnote)
                                            oro/parquet/<tabla>.parquet  (cada tabla, para cualquier herramienta)
                                            oro/csv/<vista>.csv          (para Excel y tablas dinámicas)
                                            oro/resumen.json             (para el tablero público)
                                            oro/perfiles.json            (g7b.perfil/1, para Amatista)

Hechos: ``hechos_render`` (Open Data) y ``hechos_medicion`` (sonda). Dimensiones: dispositivo,
versión, escena, perfil, tiempo y origen (PLAN 7.4). Todo se reconstruye completo en cada corrida:
es barato a esta escala y así plata y oro nunca se desincronizan de bronce.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

import duckdb

from . import conocimiento, opendata, perfiles, plata

LTS = {"2.83", "2.93", "3.3", "3.6", "4.2", "4.5", "5.2"}

ESQUEMA_RENDER = {
    "render_id": "VARCHAR", "fecha": "DATE", "version_blender": "VARCHAR", "version_corta": "VARCHAR",
    "so": "VARCHAR", "arquitectura": "VARCHAR", "tipo_dispositivo": "VARCHAR", "dispositivo": "VARCHAR",
    "clase_dispositivo": "VARCHAR", "hilos_cpu": "INTEGER", "escena": "VARCHAR",
    "muestras_por_minuto": "DOUBLE", "tiempo_render_s": "DOUBLE", "memoria_pico_mb": "DOUBLE",
    "lanzador": "VARCHAR",
}
ESQUEMA_MEDICION = {
    "medicion_id": "VARCHAR", "archivo": "VARCHAR", "fecha": "DATE", "origen": "VARCHAR", "sonda": "VARCHAR",
    "completa": "BOOLEAN", "huella": "VARCHAR", "nivel": "VARCHAR", "nivel_estimado": "BOOLEAN",
    "so": "VARCHAR", "arquitectura": "VARCHAR", "cpu": "VARCHAR", "nucleos_logicos": "INTEGER",
    "ram_gb": "DOUBLE", "gpu_vista": "VARCHAR", "gpu_cycles": "VARCHAR", "version_blender": "VARCHAR",
    "version_corta": "VARCHAR", "sin_ventana": "BOOLEAN", "escena": "VARCHAR", "perfil": "VARCHAR",
    "prueba": "VARCHAR", "metrica": "VARCHAR", "unidad": "VARCHAR", "mediana": "DOUBLE",
    "variacion": "DOUBLE", "repeticiones": "INTEGER", "calidad": "VARCHAR", "motivo": "VARCHAR",
}
ORIGENES = {
    "opendata": "Blender Open Data (CC0), render de Cycles enviado por la comunidad",
    "pc": "La sonda en una computadora propia",
    "actions": "La sonda en un ejecutor de GitHub Actions (sin GPU)",
    "colab": "La sonda en Google Colab (con GPU)",
    "azure": "La sonda en una máquina de Azure",
    "laboratorio": "La sonda en un laboratorio con permiso (T3)",
}
VISTAS_CSV = ("v_render_por_clase", "v_medicion_por_nivel", "v_salud", "v_equipos_sonda")


def _cargar(con, tabla, esquema, filas, carpeta):
    """Crea la tabla con su esquema y la llena desde un JSONL temporal (rápido y sin pandas)."""
    columnas = ", ".join(f"{c} {t}" for c, t in esquema.items())
    con.execute(f"CREATE OR REPLACE TABLE {tabla} ({columnas})")
    ruta = os.path.join(carpeta, f"{tabla}.jsonl")
    cantidad = 0
    with open(ruta, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
            cantidad += 1
    if cantidad:
        tipos = "{" + ", ".join(f"'{c}': '{t}'" for c, t in esquema.items()) + "}"
        con.execute(f"INSERT INTO {tabla} SELECT * FROM read_json(?, format='newline_delimited', "
                    f"columns={tipos}, dateformat='%Y-%m-%d')", [ruta])
    return cantidad


def _filas_sonda(almacen, salida):
    for ruta in almacen.listar("bronce/sonda/"):
        if not ruta.endswith(".json"):
            continue
        try:
            medicion = plata.leer_medicion(almacen.leer(ruta))
        except (ValueError, json.JSONDecodeError) as error:
            salida(f"medición ignorada {ruta}: {error}")
            continue
        if medicion.get("sintetico", True):
            continue  # lo sintético nunca entra al cubo (PLAN 5.7)
        yield from plata.filas_medicion(medicion, archivo=os.path.basename(ruta))


def _modelo(con):
    """Dimensiones, hechos y vistas a partir de las dos tablas de plata."""
    con.execute("""
        CREATE OR REPLACE TABLE dim_dispositivo AS
        SELECT 'od:' || md5(dispositivo || '|' || tipo_dispositivo) AS clave_dispositivo, 'opendata' AS fuente,
               dispositivo AS nombre, tipo_dispositivo AS tipo, clase_dispositivo AS clase, '' AS nivel,
               mode(so) AS so, mode(arquitectura) AS arquitectura, NULL::DOUBLE AS ram_gb
        FROM plata_render GROUP BY dispositivo, tipo_dispositivo, clase_dispositivo
        UNION ALL
        SELECT 'sd:' || huella, 'sonda', arg_max(cpu || ' / ' || gpu_vista, fecha),
               CASE WHEN max(gpu_cycles) <> '' THEN 'GPU' ELSE 'CPU' END,
               CASE WHEN max(gpu_cycles) <> '' THEN 'gpu_dedicada' ELSE 'cpu' END,
               arg_max(nivel, fecha), arg_max(so, fecha), arg_max(arquitectura, fecha), max(ram_gb)
        FROM plata_medicion GROUP BY huella
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_version AS
        SELECT DISTINCT version_corta AS clave_version, version_corta,
               TRY_CAST(split_part(version_corta, '.', 1) AS INTEGER) AS mayor,
               TRY_CAST(split_part(version_corta, '.', 2) AS INTEGER) AS menor,
               version_corta IN ({", ".join(f"'{v}'" for v in sorted(LTS))}) AS es_lts
        FROM (SELECT version_corta FROM plata_render UNION SELECT version_corta FROM plata_medicion)
        WHERE version_corta <> ''
    """)
    con.execute("""
        CREATE OR REPLACE TABLE dim_escena AS
        SELECT DISTINCT escena, 'opendata' AS fuente FROM plata_render
        UNION SELECT DISTINCT escena, 'sonda' FROM plata_medicion WHERE escena <> ''
    """)
    con.execute("CREATE OR REPLACE TABLE dim_perfil (perfil VARCHAR, subsurf INTEGER, simplify BOOLEAN, "
                "muestras INTEGER, res_pct INTEGER)")
    con.executemany("INSERT INTO dim_perfil VALUES (?, ?, ?, ?, ?)",
                    [[p, a["subsurf"], a["simplify"], a["muestras"], a["res_pct"]]
                     for p, a in perfiles.AJUSTES.items()])
    con.execute("CREATE OR REPLACE TABLE dim_origen (origen VARCHAR, descripcion VARCHAR)")
    con.executemany("INSERT INTO dim_origen VALUES (?, ?)", list(ORIGENES.items()))
    con.execute("""
        CREATE OR REPLACE TABLE dim_tiempo AS
        SELECT DISTINCT fecha, year(fecha) AS anio, month(fecha) AS mes, weekofyear(fecha) AS semana
        FROM (SELECT fecha FROM plata_render UNION SELECT fecha FROM plata_medicion) WHERE fecha IS NOT NULL
    """)
    con.execute("""
        CREATE OR REPLACE TABLE hechos_render AS
        SELECT render_id, fecha, 'od:' || md5(dispositivo || '|' || tipo_dispositivo) AS clave_dispositivo,
               NULLIF(version_corta, '') AS clave_version, escena, 'opendata' AS origen, hilos_cpu,
               muestras_por_minuto, tiempo_render_s, memoria_pico_mb
        FROM plata_render
    """)
    con.execute("""
        CREATE OR REPLACE TABLE hechos_medicion AS
        SELECT medicion_id, fecha, 'sd:' || huella AS clave_dispositivo, NULLIF(version_corta, '') AS clave_version,
               escena, perfil, prueba, metrica, unidad, mediana, variacion, repeticiones, calidad, motivo,
               origen, sin_ventana, nivel AS nivel_medido
        FROM plata_medicion
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_render_por_clase AS
        SELECT d.clase, v.version_corta, v.es_lts, h.escena, count(*) AS renders,
               count(DISTINCT h.clave_dispositivo) AS dispositivos,
               round(quantile_cont(h.muestras_por_minuto, 0.1), 2) AS muestras_min_p10,
               round(median(h.muestras_por_minuto), 2) AS muestras_min_mediana,
               round(quantile_cont(h.muestras_por_minuto, 0.9), 2) AS muestras_min_p90
        FROM hechos_render h JOIN dim_dispositivo d USING (clave_dispositivo)
        JOIN dim_version v USING (clave_version)
        WHERE h.muestras_por_minuto IS NOT NULL
        GROUP BY ALL ORDER BY v.version_corta DESC, h.escena, d.clase
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_medicion_por_nivel AS
        SELECT d.nivel, v.version_corta, h.prueba, h.perfil, h.unidad, count(*) AS mediciones,
               count(DISTINCT h.clave_dispositivo) AS equipos, round(median(h.mediana), 3) AS mediana
        FROM hechos_medicion h JOIN dim_dispositivo d USING (clave_dispositivo)
        JOIN dim_version v USING (clave_version)
        WHERE h.calidad = 'ok'
        GROUP BY ALL ORDER BY d.nivel, v.version_corta DESC, h.prueba, h.perfil
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_salud AS
        SELECT 'sonda' AS fuente, calidad, count(*) AS filas FROM hechos_medicion GROUP BY calidad
        UNION ALL SELECT 'opendata', 'ok', count(*) FROM hechos_render
        ORDER BY fuente, calidad
    """)
    con.execute("""
        CREATE OR REPLACE VIEW v_equipos_sonda AS
        SELECT d.clave_dispositivo, d.nombre, d.nivel, d.so, d.arquitectura, d.ram_gb,
               count(DISTINCT h.medicion_id) AS corridas, min(h.fecha) AS primera, max(h.fecha) AS ultima,
               string_agg(DISTINCT h.origen, ', ') AS origenes
        FROM dim_dispositivo d JOIN hechos_medicion h USING (clave_dispositivo)
        GROUP BY ALL ORDER BY d.nivel, d.nombre
    """)


def _filas(con, sql, limite=None):
    cursor = con.execute(sql + (f" LIMIT {int(limite)}" if limite else ""))
    columnas = [c[0] for c in cursor.description]
    return [{c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(columnas, fila)}
            for fila in cursor.fetchall()]


def resumen(con, ahora, almacen=None):
    conteos = con.execute("""
        SELECT (SELECT count(*) FROM hechos_render), (SELECT count(*) FROM dim_dispositivo WHERE fuente='opendata'),
               (SELECT count(DISTINCT medicion_id) FROM hechos_medicion),
               (SELECT count(*) FROM dim_dispositivo WHERE fuente='sonda'),
               (SELECT max(fecha) FROM hechos_render)
    """).fetchone()
    return {
        "generado": ahora.isoformat(timespec="seconds"),
        "conteos": {"renders_opendata": conteos[0], "dispositivos_opendata": conteos[1],
                    "corridas_sonda": conteos[2], "equipos_sonda": conteos[3],
                    "opendata_hasta": conteos[4].isoformat() if conteos[4] else None},
        # Para el tablero: solo versiones LTS y las escenas con más datos.
        "render_por_clase": _filas(con, "SELECT * FROM v_render_por_clase WHERE es_lts AND renders >= 20", 300),
        "medicion_por_nivel": _filas(con, "SELECT * FROM v_medicion_por_nivel", 300),
        "equipos_sonda": _filas(con, "SELECT nivel, nombre, so, arquitectura, corridas, origenes "
                                     "FROM v_equipos_sonda", 200),
        "salud": _filas(con, "SELECT * FROM v_salud"),
        "conocimiento": conocimiento.resumen(almacen) if almacen is not None else {},
        "fuentes": [{"nombre": "Blender Open Data", "url": "https://opendata.blender.org/",
                     "licencia": opendata.LICENCIA},
                    {"nombre": "g7b-sonda", "url": "https://github.com/Maximiliano-cabello-mata/amatista-g7b-etl/"
                                                   "tree/main/sonda", "licencia": "CC0-1.0"}],
    }


def construir(almacen, salida=print, ahora=None):
    """Reconstruye plata y oro desde bronce. Devuelve el resumen."""
    ahora = ahora or datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="g7b_cubo_") as carpeta:
        ruta_cubo = os.path.join(carpeta, "cubo.duckdb")
        con = duckdb.connect(ruta_cubo)
        try:
            copia = opendata.ultima_copia(almacen)
            if copia:
                salida(f"Open Data: leyendo {copia}")
                registros = opendata.leer_registros(almacen.leer(copia))
                renders = _cargar(con, "plata_render", ESQUEMA_RENDER, opendata.filas_render(registros), carpeta)
            else:
                salida("Open Data: todavía no hay copia en bronce (python -m g7b_almacen opendata)")
                renders = _cargar(con, "plata_render", ESQUEMA_RENDER, [], carpeta)
            pruebas = _cargar(con, "plata_medicion", ESQUEMA_MEDICION, _filas_sonda(almacen, salida), carpeta)
            salida(f"plata: {renders} renders de Open Data y {pruebas} pruebas de la sonda")
            _modelo(con)
            documento = perfiles.generar(con, ahora)
            errores = perfiles.validar(documento)
            if errores:
                raise ValueError(f"perfiles.json no cumple {perfiles.CONTRATO}: {errores}")
            datos_resumen = resumen(con, ahora, almacen)
            datos_resumen["perfiles"] = len(documento["perfiles"])

            archivos = {}
            for tabla, destino in (("plata_render", "plata/opendata/render.parquet"),
                                   ("plata_medicion", "plata/sonda/medicion.parquet")):
                archivos[destino] = _copiar(con, f"SELECT * FROM {tabla}", carpeta, destino, "parquet")
            for tabla in ("dim_dispositivo", "dim_version", "dim_escena", "dim_perfil", "dim_origen",
                          "dim_tiempo", "hechos_render", "hechos_medicion"):
                destino = f"oro/parquet/{tabla}.parquet"
                archivos[destino] = _copiar(con, f"SELECT * FROM {tabla}", carpeta, destino, "parquet")
            for vista in VISTAS_CSV:
                destino = f"oro/csv/{vista}.csv"
                archivos[destino] = _copiar(con, f"SELECT * FROM {vista}", carpeta, destino, "csv")
            con.execute("DROP TABLE plata_render")
            con.execute("DROP TABLE plata_medicion")
            con.execute("CHECKPOINT")
        finally:
            con.close()
        archivos["oro/cubo.duckdb"] = ruta_cubo
        for destino, local in archivos.items():
            with open(local, "rb") as f:
                almacen.escribir(destino, f.read())
        almacen.escribir("oro/perfiles.json", json.dumps(documento, ensure_ascii=False, indent=2).encode())
        almacen.escribir("oro/resumen.json", json.dumps(datos_resumen, ensure_ascii=False, indent=2).encode())
    salida(f"oro: {len(archivos) + 2} archivos; {datos_resumen['perfiles']} perfiles")
    return datos_resumen


def _copiar(con, consulta, carpeta, destino, formato):
    local = os.path.join(carpeta, destino.replace("/", "__"))
    opciones = "FORMAT PARQUET, COMPRESSION ZSTD" if formato == "parquet" else "HEADER, DELIMITER ','"
    con.execute(f"COPY ({consulta}) TO '{local}' ({opciones})")
    return local
