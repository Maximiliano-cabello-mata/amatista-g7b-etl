"""Cubo v1 sobre g7b.telemetria/1; no produce perfiles ni recomendaciones."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from uuid import uuid4

import duckdb

CONTRATO = 'g7b.cubo/1'
ACTUAL = 'control/cubo_actual.json'
MAX_FILAS = 1_000_000
DIMENSIONES = ('dispositivo', 'version', 'escena', 'perfil', 'tiempo', 'origen')


def serializar(dato):
    return json.dumps(dato, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(datos):
    return hashlib.sha256(datos).hexdigest()


def clave(dato):
    return sha(serializar(dato))


def texto(valor):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > 1000:
        raise ValueError('campo de texto requerido o excesivo')
    return valor


def validar(f):
    if not isinstance(f, dict) or f.get('contrato') != 'g7b.telemetria/1' or f.get('sintetico') is not False:
        raise ValueError('contrato desconocido o dato sintético')
    for campo in ('id', 'huella_origen'):
        if not re.fullmatch('[0-9a-f]{64}', f.get(campo, '')):
            raise ValueError('identificador o huella inválidos')
    if f.get('fuente') not in ('sonda', 'blender-open-data') or f.get('estado') not in ('aceptado', 'revision'):
        raise ValueError('fuente o estado desconocidos')
    valor = f.get('valor')
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
        raise ValueError('valor inválido')
    for campo in ('version', 'escena', 'metrica', 'licencia'):
        texto(f.get(campo))
    instante = datetime.fromisoformat(texto(f.get('fecha')).replace('Z', '+00:00'))
    if instante.tzinfo is None: raise ValueError('fecha sin zona horaria')
    if not isinstance(f.get('motivos'), list): raise ValueError('faltan motivos de calidad')
    if f['fuente'] == 'blender-open-data':
        if (f.get('unidad') != 'samples/min' or f['metrica'] != 'samples_per_minute'
                or f['estado'] != 'revision' or f['licencia'] != 'CC0-1.0'):
            raise ValueError('benchmark público no compatible con esta versión')
        if not f.get('dispositivos'): raise ValueError('sin dispositivos')
        for d in f['dispositivos']: texto(d)
        texto(f.get('backend'))
        texto(f.get('so'))
    else:
        if f.get('unidad') not in ('s', 'fps') or not isinstance(f.get('equipo'), dict):
            raise ValueError('sonda sin equipo o unidad válida')
        texto(f['equipo'].get('cpu'))
        texto(f.get('prueba'))
        if f['estado'] == 'aceptado' and (f['motivos'] or f.get('variacion', 1) > .10 or len(f.get('valores', [])) < 3):
            raise ValueError('aceptación contradictoria con calidad')
    return instante.astimezone(timezone.utc)


def preparar(entradas):
    unicos, procedencia = {}, set()
    leidos = 0
    for ruta, f in entradas:
        leidos += 1
        if leidos > MAX_FILAS: raise ValueError('se excedió el límite de filas del cubo v1')
        validar(f)
        # No elegir silenciosamente entre dos versiones de la misma medición.
        if f['id'] in unicos and serializar(f) != serializar(unicos[f['id']]):
            raise ValueError('id repetido con contenido contradictorio')
        unicos[f['id']] = f
        procedencia.add((f['id'], ruta))
    if not unicos: raise ValueError('no hay mediciones; se conserva la publicación anterior')
    return [unicos[k] for k in sorted(unicos)], sorted(procedencia), leidos


def modelo(con, filas, procedencia):
    dimensiones = {d: {} for d in DIMENSIONES}
    hechos = []
    for f in filas:
        fecha = validar(f)
        equipo = f.get('equipo', {})
        dispositivo = {'fuente': f['fuente'], 'equipo': equipo} if f['fuente'] == 'sonda' else {
            'fuente': f['fuente'], 'dispositivos': sorted(f['dispositivos']), 'backend': f['backend'], 'so': f['so']}
        datos = {
            'dispositivo': (serializar(dispositivo).decode(),),
            'version': ('blender', f['version']),
            'escena': (f['fuente'], f['escena']),
            'perfil': (f['fuente'], f.get('perfil') or 'no_aplica', f.get('sonda') or 'no_aplica'),
            'tiempo': (fecha.date().isoformat(), fecha.year, fecha.month, fecha.day),
            'origen': (f['fuente'], f.get('entorno', 'no_declarado'), f['licencia']),
        }
        claves = []
        for dimension, atributos in datos.items():
            k = clave([dimension, atributos])
            dimensiones[dimension][k] = atributos
            claves.append(k)
        hechos.append([f['id'], *claves, fecha.isoformat(), f['fuente'],
                       f.get('prueba', 'render_cycles'), f['metrica'], f['unidad'], f['valor'],
                       f['estado'], serializar(f['motivos']).decode(), f.get('variacion'),
                       len(f.get('valores', [])) or None, f.get('sin_ventana'), f['huella_origen']])
    esquemas = {
        'dispositivo': 'atributos_json VARCHAR',
        'version': 'programa VARCHAR, version VARCHAR',
        'escena': 'fuente VARCHAR, escena VARCHAR',
        'perfil': 'fuente VARCHAR, perfil VARCHAR, version_sonda VARCHAR',
        'tiempo': 'fecha DATE, anio INTEGER, mes INTEGER, dia INTEGER',
        'origen': 'fuente VARCHAR, entorno VARCHAR, licencia VARCHAR',
    }
    for d in DIMENSIONES:
        con.execute(f'CREATE TABLE dim_{d} (clave_{d} VARCHAR PRIMARY KEY, {esquemas[d]})')
        datos = [[k, *v] for k, v in sorted(dimensiones[d].items())]
        con.executemany(f'INSERT INTO dim_{d} VALUES ({",".join("?" for _ in datos[0])})', datos)
    claves_sql = ', '.join(f'clave_{d} VARCHAR NOT NULL REFERENCES dim_{d}(clave_{d})' for d in DIMENSIONES)
    con.execute(f'''CREATE TABLE mediciones (
        id VARCHAR PRIMARY KEY, {claves_sql}, fecha TIMESTAMPTZ, fuente VARCHAR,
        prueba VARCHAR, metrica VARCHAR, unidad VARCHAR, valor DOUBLE,
        estado VARCHAR, motivos_json VARCHAR, variacion DOUBLE, repeticiones INTEGER,
        sin_ventana BOOLEAN, huella_origen VARCHAR)''')
    con.executemany(f'INSERT INTO mediciones VALUES ({",".join("?" for _ in hechos[0])})', hechos)
    con.execute('CREATE TABLE procedencia (id VARCHAR, archivo VARCHAR, PRIMARY KEY(id, archivo))')
    con.executemany('INSERT INTO procedencia VALUES (?, ?)', procedencia)
    con.execute("CREATE TABLE hechos_medicion AS SELECT * FROM mediciones WHERE fuente='sonda'")
    con.execute("CREATE TABLE hechos_render AS SELECT * FROM mediciones WHERE fuente='blender-open-data'")
    con.execute('''CREATE VIEW v_exploracion AS
        SELECT m.*, v.programa, v.version, e.escena, p.perfil, p.version_sonda,
               d.atributos_json AS dispositivo, o.entorno, o.licencia
        FROM mediciones m JOIN dim_version v USING(clave_version)
        JOIN dim_escena e USING(clave_escena) JOIN dim_perfil p USING(clave_perfil)
        JOIN dim_dispositivo d USING(clave_dispositivo) JOIN dim_origen o USING(clave_origen)''')
    con.execute("CREATE VIEW v_mediciones_aceptadas AS SELECT * FROM v_exploracion WHERE estado='aceptado'")
    con.execute('''CREATE VIEW v_resumen AS
        SELECT fuente, entorno, dispositivo, version, escena, perfil, version_sonda,
               prueba, metrica, unidad, estado, sin_ventana, count(*) AS mediciones,
               median(valor) AS mediana, min(valor) AS minimo, max(valor) AS maximo
        FROM v_exploracion GROUP BY ALL''')
    con.execute('CREATE VIEW v_calidad AS SELECT fuente, estado, count(*) AS mediciones FROM mediciones GROUP BY ALL')


def construir(entradas, destino):
    filas, procedencia, leidos = preparar(entradas)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if any(destino.iterdir()): raise ValueError('la carpeta de salida debe estar vacía')
    (destino / 'plata').mkdir()
    (destino / 'oro/parquet').mkdir(parents=True)
    db = destino / 'oro/cubo.duckdb'
    con = duckdb.connect(str(db))
    try:
        con.execute("SET TimeZone='UTC'")
        modelo(con, filas, procedencia)
        tablas = ['mediciones', 'hechos_medicion', 'hechos_render', 'procedencia'] + ['dim_' + d for d in DIMENSIONES]
        for tabla in tablas:
            nombre = 'plata/mediciones.parquet' if tabla == 'mediciones' else f'oro/parquet/{tabla}.parquet'
            con.execute(f'COPY (SELECT * FROM {tabla} ORDER BY 1) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)', [str(destino / nombre)])
        con.execute('COPY (SELECT * FROM v_resumen ORDER BY ALL) TO ? (FORMAT CSV, HEADER)', [str(destino / 'oro/resumen.csv')])
        conteos = dict(con.execute('SELECT estado, count(*) FROM mediciones GROUP BY estado').fetchall())
        resumen = {'contrato': CONTRATO, 'leidos': leidos, 'mediciones': len(filas),
                   'duplicados_eliminados': leidos - len(filas), 'calidad': conteos,
                   'hechos_medicion': con.execute('SELECT count(*) FROM hechos_medicion').fetchone()[0],
                   'hechos_render': con.execute('SELECT count(*) FROM hechos_render').fetchone()[0],
                   'huella_datos': clave(filas), 'duckdb': duckdb.__version__,
                   'recomendaciones_habilitadas': False}
        if con.execute('SELECT count(*) FROM v_exploracion').fetchone()[0] != len(filas):
            raise ValueError('los joins alteran la cardinalidad')
        con.execute('CHECKPOINT')
    finally:
        con.close()
    # Validar el archivo cerrado y el Parquet, no solo la conexión de construcción.
    with duckdb.connect(str(db), read_only=True) as verificar:
        if verificar.execute('SELECT count(*) FROM mediciones').fetchone()[0] != len(filas):
            raise ValueError('cubo cerrado inconsistente')
        diferencia = verificar.execute('''SELECT count(*) FROM (
            (SELECT * FROM mediciones EXCEPT ALL SELECT * FROM read_parquet(?))
            UNION ALL (SELECT * FROM read_parquet(?) EXCEPT ALL SELECT * FROM mediciones))''',
            [str(destino / 'plata/mediciones.parquet')] * 2).fetchone()[0]
        if diferencia: raise ValueError('Parquet y DuckDB difieren')
    (destino / 'oro/resumen.json').write_bytes(serializar(resumen))
    archivos = {f.relative_to(destino).as_posix(): {'sha256': sha(f.read_bytes()), 'bytes': f.stat().st_size}
                for f in sorted(destino.rglob('*')) if f.is_file()}
    manifiesto = {**resumen, 'generado': datetime.now(timezone.utc).isoformat(), 'archivos': archivos}
    (destino / 'manifiesto.json').write_bytes(serializar(manifiesto))
    return manifiesto


def leer_lago(lago):
    for ruta in sorted(lago.listar('plata/telemetria/')):
        partes = ruta.split('/')
        if len(partes) != 5 or not ruta.endswith('.jsonl.gz') or partes[2] not in ('aceptado', 'revision'):
            continue
        for f in lago.leer_jsonl_gz(ruta):
            if f.get('estado') != partes[2] or f.get('fuente') != partes[3]:
                raise ValueError('procedencia y contenido no coinciden')
            yield ruta, f


def publicar(lago, destino, manifiesto):
    destino = Path(destino)
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:12]
    rutas = {}
    for nombre, meta in manifiesto['archivos'].items():
        datos = (destino / nombre).read_bytes()
        if sha(datos) != meta['sha256']: raise ValueError('salida local modificada')
        ruta = (f'plata/cubo/{version}/' + nombre.removeprefix('plata/') if nombre.startswith('plata/')
                else f'oro/cubos/{version}/' + nombre.removeprefix('oro/'))
        lago.subir_bytes(ruta, datos, sobrescribir=False)
        if sha(lago.contenedor.download_blob(ruta).readall()) != meta['sha256']:
            raise ValueError('falló verificación de artefacto en Azure')
        rutas[nombre] = {**meta, 'ruta': ruta}
    publicado = {**manifiesto, 'version': version, 'archivos': rutas, 'estado': 'verificado'}
    ruta_manifiesto = f'oro/cubos/{version}/manifiesto.json'
    contenido = serializar(publicado)
    lago.subir_bytes(ruta_manifiesto, contenido, tipo='application/json')
    if lago.contenedor.download_blob(ruta_manifiesto).readall() != contenido:
        raise ValueError('falló verificación del manifiesto')
    # Único punto mutable, solo después de verificar TODOS los archivos.
    puntero = {'contrato': CONTRATO, 'version': version, 'manifiesto': ruta_manifiesto,
               'sha256': sha(contenido), 'cubo': rutas['oro/cubo.duckdb']['ruta']}
    lago.escribir_json(ACTUAL, puntero)
    if lago.leer_json(ACTUAL) != puntero: raise ValueError('puntero no confirmado')
    return puntero


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrada', type=Path, help='carpeta de JSONL normalizados, búsqueda recursiva')
    p.add_argument('--azure', action='store_true', help='leer plata y publicar versión verificada')
    p.add_argument('--salida', required=True, type=Path)
    a = p.parse_args()
    if bool(a.entrada) == a.azure: p.error('elige --entrada o --azure')
    lago = None
    if a.azure:
        from g7b_lago import Lago
        lago = Lago.desde_entorno()
        entradas = leer_lago(lago)
    else:
        def locales():
            for ruta in sorted(a.entrada.rglob('*.jsonl')):
                with ruta.open(encoding='utf-8') as archivo:
                    for linea in archivo:
                        if linea.strip(): yield ruta.relative_to(a.entrada).as_posix(), json.loads(linea)
        entradas = locales()
    manifiesto = construir(entradas, a.salida)
    resumen = {k: v for k, v in manifiesto.items() if k != 'archivos'}
    if lago: resumen['publicacion'] = publicar(lago, a.salida, manifiesto)
    print('G7B_CUBO_VERIFICADO', json.dumps(resumen, ensure_ascii=False))


if __name__ == '__main__':
    main()
