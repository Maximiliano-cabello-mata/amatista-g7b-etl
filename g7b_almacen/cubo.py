"""Cubo g7b.cubo/2: mediciones DIRECTAS y RELATIVAS, separadas y con dimensiones normalizadas.

Dos clases de dato que nunca se mezclan (docs/CUBO.md, sección 1):

    directa   medida por G7B o Amatista en el equipo real de un estudiante o de un laboratorio
              escolar, con consentimiento registrado. Es la única que puede alimentar a Geoda.
    relativa  todo lo demás: benchmarks públicos (Blender Open Data), la sonda en servidores de
              GitHub o en la nube, o cualquier medición sin entorno o consentimiento declarado.
              Sirve para comparar niveles entre sí, nunca para recomendar ajustes.

Lo que no declara su entorno y su consentimiento es relativo: la duda nunca sube de clase.
«sintetico» sigue significando otra cosa: datos inventados para pruebas, que nunca entran.

No produce perfiles ni recomendaciones (eso es Geoda, solo sobre las directas).
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from uuid import uuid4

import duckdb

CONTRATO = 'g7b.cubo/2'
CONTRATOS_LEGIBLES = ('g7b.cubo/1', 'g7b.cubo/2')   # los lectores aceptan el anterior mientras se migra
ACTUAL = 'control/cubo_actual.json'
MAX_FILAS = 1_000_000
CLASES = ('directa', 'relativa')
ENTORNOS_DIRECTOS = {'equipo_estudiante', 'laboratorio_escolar'}
# Diccionario de métricas: hacia dónde es mejor cada unidad (no se suman ni se comparan entre sí).
MEJOR = {'s': 'menor', 'fps': 'mayor', 'samples/min': 'mayor'}
DIMENSIONES = ('fuente', 'equipo', 'version', 'prueba', 'perfil', 'tiempo')


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


def clase_de(f):
    """(clase, motivo) de una medición. Directa solo con declaración explícita."""
    if f['fuente'] == 'blender-open-data':
        return 'relativa', 'benchmark público: no lo midieron G7B ni Amatista'
    entorno = f.get('entorno') or 'no_declarado'
    if entorno not in ENTORNOS_DIRECTOS:
        return 'relativa', f'entorno «{entorno}»: no es el equipo de un estudiante ni un laboratorio escolar'
    if f.get('consentimiento') is not True:
        return 'relativa', 'sin consentimiento registrado'
    return 'directa', f'medida por G7B en {entorno}, con consentimiento'


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
    if f.get('unidad') not in MEJOR:
        raise ValueError('unidad sin entrada en el diccionario de métricas')
    if 'entorno' in f and f['entorno'] is not None:
        texto(f['entorno'])
    if 'consentimiento' in f and not isinstance(f['consentimiento'], bool):
        raise ValueError('consentimiento debe ser verdadero o falso')
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


def identidad_semantica(f):
    """Qué observación es, sin depender del orden en la lista ni de su estado de calidad."""
    origen = f.get('id_fuente') or f['huella_origen']
    return (f['fuente'], origen, f['escena'], f.get('prueba') or 'render_cycles', f['metrica'], f.get('perfil'))


def preparar(entradas):
    unicos, procedencia = {}, set()
    semanticas, conteo = {}, Counter()
    leidos = 0
    for ruta, f in entradas:
        leidos += 1
        if leidos > MAX_FILAS: raise ValueError('se excedió el límite de filas del cubo')
        validar(f)
        # No elegir silenciosamente entre dos versiones de la misma medición.
        if f['id'] in unicos and serializar(f) != serializar(unicos[f['id']]):
            raise ValueError('id repetido con contenido contradictorio')
        procedencia.add((f['id'], ruta))
        if f['id'] in unicos:
            conteo['duplicados_exactos'] += 1
            continue
        # Solo donde la fuente da su propio id (Open Data): ahí una misma observación pudo capturarse
        # con dos fórmulas de id. La sonda ya identifica por su contenido (huella_origen).
        llave = identidad_semantica(f) if f.get('id_fuente') else None
        previo = semanticas.get(llave) if llave else None
        if previo is not None and previo != f['id']:
            # La misma observación con otro id (p. ej. capturada con otra fórmula de id): se cuenta.
            if unicos[previo]['valor'] != f['valor']:
                raise ValueError('la misma observación trae valores distintos')
            conteo['duplicados_semanticos'] += 1
            continue
        if llave:
            semanticas[llave] = f['id']
        unicos[f['id']] = f
    if not unicos: raise ValueError('no hay mediciones; se conserva la publicación anterior')
    return [unicos[k] for k in sorted(unicos)], sorted(procedencia), leidos, conteo


def _equipo(f):
    """Columnas tipadas del equipo (estándar g7b.hardware/1) y el JSON original para trazabilidad."""
    from g7b_telemetria import hardware

    if f['fuente'] == 'sonda':
        e = f.get('equipo', {})
        vista = e.get('gpu_vista')
        gpu_texto = vista.get('modelo') if isinstance(vista, dict) else (vista if isinstance(vista, str) else None)
        g = hardware.gpu(gpu_texto) if gpu_texto else {}
        c = hardware.cpu(e.get('cpu'))
        original = {'fuente': 'sonda', 'equipo': e}
        return (('equipo', g.get('nombre'), g.get('fabricante'), g.get('clase'), g.get('vram_gb'),
                 c['nombre'], c['familia'], e.get('so'), None, e.get('nivel'),
                 'estimado' if e.get('nivel_estimado') else ('declarado' if e.get('nivel') else None),
                 serializar(original).decode()))
    # El estándar se aplica AL CONSTRUIR, con la tabla vigente (fuentes/hardware.yml): si la tabla
    # mejora, el cubo mejora sin volver a capturar. Lo que vino al capturar queda en equipo_json.
    h = hardware.de_benchmark(f['dispositivos'], f['backend'], f['so'])
    g = (h.get('gpus') or [{}])[0]
    c = (h.get('cpus') or [{}])[0]
    original = {'fuente': f['fuente'], 'dispositivos': sorted(f['dispositivos']), 'backend': f['backend'],
                'so': f['so'], **({'hardware_capturado': f['hardware']} if f.get('hardware') else {})}
    return ((h.get('mide') or 'sin_clasificar', g.get('nombre'), g.get('fabricante'), g.get('clase'),
             g.get('vram_gb'), c.get('nombre'), c.get('familia'), f['so'], f['backend'], h.get('nivel'),
             h.get('confianza'), serializar(original).decode()))


ESQUEMAS = {
    'dim_fuente': {'clave_fuente': 'VARCHAR', 'fuente': 'VARCHAR', 'licencia': 'VARCHAR', 'entorno': 'VARCHAR',
                   'clase_dato': 'VARCHAR'},
    'dim_equipo': {'clave_equipo': 'VARCHAR', 'mide': 'VARCHAR', 'gpu': 'VARCHAR', 'gpu_fabricante': 'VARCHAR',
                   'gpu_clase': 'VARCHAR', 'gpu_vram_gb': 'DOUBLE', 'cpu': 'VARCHAR', 'cpu_familia': 'VARCHAR',
                   'so': 'VARCHAR', 'backend': 'VARCHAR', 'nivel': 'VARCHAR', 'nivel_confianza': 'VARCHAR',
                   'equipo_json': 'VARCHAR'},
    'dim_version': {'clave_version': 'VARCHAR', 'programa': 'VARCHAR', 'version': 'VARCHAR', 'serie': 'VARCHAR'},
    'dim_prueba': {'clave_prueba': 'VARCHAR', 'fuente': 'VARCHAR', 'prueba': 'VARCHAR', 'escena': 'VARCHAR',
                   'metrica': 'VARCHAR', 'unidad': 'VARCHAR', 'mejor': 'VARCHAR'},
    'dim_perfil': {'clave_perfil': 'VARCHAR', 'perfil': 'VARCHAR', 'version_sonda': 'VARCHAR'},
    'dim_tiempo': {'clave_tiempo': 'VARCHAR', 'fecha': 'DATE', 'anio': 'INTEGER', 'mes': 'INTEGER', 'dia': 'INTEGER'},
}
HECHOS = {'id': 'VARCHAR', 'id_fuente': 'VARCHAR', 'clave_fuente': 'VARCHAR', 'clave_equipo': 'VARCHAR',
          'clave_version': 'VARCHAR', 'clave_prueba': 'VARCHAR', 'clave_perfil': 'VARCHAR', 'clave_tiempo': 'VARCHAR',
          'fecha': 'TIMESTAMPTZ', 'valor': 'DOUBLE', 'estado': 'VARCHAR', 'motivos_json': 'VARCHAR',
          'motivo_clase': 'VARCHAR', 'variacion': 'DOUBLE', 'repeticiones': 'INTEGER', 'sin_ventana': 'BOOLEAN',
          'huella_origen': 'VARCHAR'}
TABLAS_HECHOS = {'directa': 'hechos_directos', 'relativa': 'hechos_relativos'}


def _cargar(con, tabla, columnas, filas, carpeta):
    """Carga masiva: escribe JSONL y lo lee con DuckDB (insertar fila por fila tardaba minutos)."""
    ruta = Path(carpeta) / f'{tabla}.jsonl'
    nombres = list(columnas)
    with ruta.open('w', encoding='utf-8') as archivo:
        for fila in filas:
            archivo.write(json.dumps(dict(zip(nombres, fila)), ensure_ascii=False) + '\n')
    tipos = ', '.join(f"'{n}': '{t}'" for n, t in columnas.items())
    con.execute(f'CREATE TABLE {tabla} ({", ".join(f"{n} {t}" for n, t in columnas.items())})')
    if filas:
        con.execute(f"INSERT INTO {tabla} SELECT {', '.join(nombres)} FROM read_json(?, format='newline_delimited', "
                    f"columns={{{tipos}}})", [str(ruta)])


def modelo(con, filas, procedencia):
    dimensiones = {d: {} for d in DIMENSIONES}
    hechos = {c: [] for c in CLASES}
    for f in filas:
        fecha = validar(f)
        clase, motivo = clase_de(f)
        serie = '.'.join(f['version'].split('.')[:2])
        datos = {
            'fuente': (f['fuente'], f['licencia'], f.get('entorno') or 'no_declarado', clase),
            'equipo': _equipo(f),
            'version': ('blender', f['version'], serie),
            'prueba': (f['fuente'], f.get('prueba', 'render_cycles'), f['escena'], f['metrica'], f['unidad'],
                       MEJOR[f['unidad']]),
            'perfil': (f.get('perfil') or 'no_aplica', f.get('sonda') or 'no_aplica'),
            'tiempo': (fecha.date().isoformat(), fecha.year, fecha.month, fecha.day),
        }
        claves = []
        for dimension, atributos in datos.items():
            k = clave([dimension, atributos])
            dimensiones[dimension][k] = atributos
            claves.append(k)
        hechos[clase].append([f['id'], f.get('id_fuente'), *claves, fecha.isoformat(), f['valor'], f['estado'],
                              json.dumps(f['motivos'], ensure_ascii=False), motivo, f.get('variacion'),
                              len(f.get('valores', [])) or None, f.get('sin_ventana'), f['huella_origen']])
    with tempfile.TemporaryDirectory() as carpeta:
        for d in DIMENSIONES:
            tabla = 'dim_' + d
            _cargar(con, tabla, ESQUEMAS[tabla], [[k, *v] for k, v in sorted(dimensiones[d].items())], carpeta)
        for clase, tabla in TABLAS_HECHOS.items():
            _cargar(con, tabla, HECHOS, hechos[clase], carpeta)
        _cargar(con, 'procedencia', {'id': 'VARCHAR', 'archivo': 'VARCHAR'}, procedencia, carpeta)
    for d in DIMENSIONES:
        con.execute(f'ALTER TABLE dim_{d} ADD PRIMARY KEY (clave_{d})')
    for tabla in TABLAS_HECHOS.values():
        con.execute(f'ALTER TABLE {tabla} ADD PRIMARY KEY (id)')
    for clase, tabla in TABLAS_HECHOS.items():
        vista = 'v_directas' if clase == 'directa' else 'v_relativas'
        con.execute(f'''CREATE VIEW {vista} AS
            SELECT h.*, f.fuente, f.licencia, f.entorno, f.clase_dato, e.mide, e.gpu, e.gpu_fabricante, e.gpu_clase,
                   e.gpu_vram_gb, e.cpu, e.cpu_familia, e.so, e.backend, e.nivel, e.nivel_confianza,
                   e.equipo_json AS dispositivo, v.programa, v.version, v.serie, p.prueba, p.escena, p.metrica,
                   p.unidad, p.mejor, pf.perfil, pf.version_sonda
            FROM {tabla} h JOIN dim_fuente f USING(clave_fuente) JOIN dim_equipo e USING(clave_equipo)
            JOIN dim_version v USING(clave_version) JOIN dim_prueba p USING(clave_prueba)
            JOIN dim_perfil pf USING(clave_perfil) JOIN dim_tiempo t USING(clave_tiempo)''')
        con.execute(f'''CREATE VIEW v_resumen_{vista[2:]} AS
            SELECT fuente, entorno, nivel, gpu_clase, backend, serie, version, escena, perfil, prueba, metrica,
                   unidad, mejor, estado, sin_ventana, count(*) AS mediciones, median(valor) AS mediana,
                   quantile_cont(valor, 0.25) AS p25, quantile_cont(valor, 0.75) AS p75,
                   min(valor) AS minimo, max(valor) AS maximo
            FROM {vista} GROUP BY ALL''')
    # Lo único que lee Geoda: directas y aceptadas. Las relativas nunca entran aquí.
    con.execute("CREATE VIEW v_mediciones_aceptadas AS SELECT * FROM v_directas WHERE estado = 'aceptado'")
    # Comparación relativa entre niveles: solo con las relativas, por serie de versión y escena.
    con.execute('''CREATE VIEW v_relativas_por_nivel AS
        SELECT nivel, mide, gpu_clase, backend, serie, escena, metrica, unidad, count(*) AS mediciones,
               median(valor) AS mediana, quantile_cont(valor, 0.25) AS p25, quantile_cont(valor, 0.75) AS p75
        FROM v_relativas WHERE fuente = 'blender-open-data' GROUP BY ALL''')
    con.execute('''CREATE VIEW v_calidad AS
        SELECT 'directa' AS clase_dato, f.fuente, h.estado, count(*) AS mediciones
          FROM hechos_directos h JOIN dim_fuente f USING(clave_fuente) GROUP BY ALL
        UNION ALL
        SELECT 'relativa', f.fuente, h.estado, count(*)
          FROM hechos_relativos h JOIN dim_fuente f USING(clave_fuente) GROUP BY ALL''')
    return {c: len(v) for c, v in hechos.items()}


def construir(entradas, destino):
    filas, procedencia, leidos, duplicados = preparar(entradas)
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    if any(destino.iterdir()): raise ValueError('la carpeta de salida debe estar vacía')
    (destino / 'plata').mkdir()
    (destino / 'oro/parquet').mkdir(parents=True)
    db = destino / 'oro/cubo.duckdb'
    con = duckdb.connect(str(db))
    try:
        con.execute("SET TimeZone='UTC'")
        por_clase = modelo(con, filas, procedencia)
        tablas = list(TABLAS_HECHOS.values()) + ['procedencia'] + ['dim_' + d for d in DIMENSIONES]
        for tabla in tablas:
            nombre = (f'plata/{tabla}.parquet' if tabla.startswith('hechos_') else f'oro/parquet/{tabla}.parquet')
            con.execute(f'COPY (SELECT * FROM {tabla} ORDER BY 1) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)',
                        [str(destino / nombre)])
        for vista in ('directas', 'relativas'):
            con.execute(f'COPY (SELECT * FROM v_resumen_{vista} ORDER BY ALL) TO ? (FORMAT CSV, HEADER)',
                        [str(destino / f'oro/resumen_{vista}.csv')])
        def conteos(tabla):
            return dict(con.execute(f'SELECT estado, count(*) FROM {tabla} GROUP BY estado').fetchall())
        directas, relativas = conteos('hechos_directos'), conteos('hechos_relativos')
        calidad = Counter(directas) + Counter(relativas)
        resumen = {'contrato': CONTRATO, 'leidos': leidos, 'mediciones': len(filas),
                   'duplicados_eliminados': leidos - len(filas), **{k: duplicados.get(k, 0) for k in
                                                                     ('duplicados_exactos', 'duplicados_semanticos')},
                   'directas': directas, 'relativas': relativas, 'calidad': dict(calidad),
                   'huella_datos': clave(filas), 'duckdb': duckdb.__version__,
                   'recomendaciones_habilitadas': False}
        vistas = sum(con.execute(f'SELECT count(*) FROM {v}').fetchone()[0] for v in ('v_directas', 'v_relativas'))
        if vistas != len(filas) or sum(por_clase.values()) != len(filas):
            raise ValueError('los joins alteran la cardinalidad')
        con.execute('CHECKPOINT')
    finally:
        con.close()
    # Validar el archivo cerrado y el Parquet, no solo la conexión de construcción.
    with duckdb.connect(str(db), read_only=True) as verificar:
        for tabla in TABLAS_HECHOS.values():
            parquet = str(destino / f'plata/{tabla}.parquet')
            diferencia = verificar.execute(f'''SELECT count(*) FROM (
                (SELECT * FROM {tabla} EXCEPT ALL SELECT * FROM read_parquet(?))
                UNION ALL (SELECT * FROM read_parquet(?) EXCEPT ALL SELECT * FROM {tabla}))''',
                [parquet, parquet]).fetchone()[0]
            if diferencia: raise ValueError(f'Parquet y DuckDB difieren en {tabla}')
        if sum(verificar.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in TABLAS_HECHOS.values()) != len(filas):
            raise ValueError('cubo cerrado inconsistente')
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
