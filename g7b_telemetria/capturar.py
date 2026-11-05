"""Captura limitada, auditable y repetible de sondas y Blender Open Data."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import urllib.request
from uuid import UUID
import zipfile

URL = 'https://opendata.blender.org/snapshots/opendata-latest.zip'
LICENCIA = 'https://opendata.blender.org/download/'
MAX_ARCHIVO = 256 * 1024 * 1024
MAX_EXPANDIDO = 2 * 1024 * 1024 * 1024
MAX_LINEA = 2 * 1024 * 1024


def canon(dato):
    return json.dumps(dato, ensure_ascii=False, sort_keys=True, allow_nan=False).encode('utf-8')


def huella(dato):
    return hashlib.sha256(canon(dato)).hexdigest()


def positivo(valor):
    if isinstance(valor, bool) or not isinstance(valor, (float, int)) or not math.isfinite(valor) or valor <= 0:
        raise ValueError('valor numérico no positivo o no finito')
    return valor


def texto(valor):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > 300:
        raise ValueError('texto requerido o demasiado largo')
    return valor


def fecha(valor):
    f = datetime.fromisoformat(texto(valor).replace('Z', '+00:00'))
    if f.tzinfo is None:
        raise ValueError('fecha sin zona horaria')
    return f.isoformat()


def sonda(dato):
    if dato['contrato'] != 'g7b.medicion/1' or dato['sintetico'] is not False:
        raise ValueError('se requiere contrato de sonda y medición explícitamente real')
    base = {'fuente': 'sonda', 'fecha': fecha(dato['fecha']),
            'version': texto(dato['blender']['version']), 'escena': texto(dato['escena']['nombre']),
            # nivel y GPU: los necesita Geoda para clasificar el equipo (no identifican a nadie).
            'equipo': {k: dato['equipo'].get(k) for k in ('cpu', 'ram_gb', 'so', 'arquitectura', 'huella',
                                                         'nivel', 'nivel_estimado', 'gpu_vista', 'gpu_cycles')},
            'sonda': texto(dato['sonda']), 'sin_ventana': dato['blender']['sin_ventana'],
            'licencia': 'propia; publicación agregada', 'preguntas': ['P1', 'P2']}
    filas = []
    for r in dato['resultados']:
        if 'no_disponible' in r:
            continue
        valores = [positivo(v) for v in r['valores']]
        if not valores or len(valores) != dato['repeticiones'] or r['unidad'] not in ('s', 'fps'):
            raise ValueError('repeticiones o unidad inválidas')
        mediana = statistics.median(valores)
        if not math.isclose(positivo(r['mediana']), mediana, abs_tol=0.00011):
            raise ValueError('mediana inconsistente')
        variacion = (max(valores) - min(valores)) / mediana
        motivos = []
        if len(valores) < 3: motivos.append('menos_de_tres_repeticiones')
        if variacion > .10: motivos.append('variacion_superior_10_por_ciento')
        if dato.get('completa') is not True: motivos.append('corrida_incompleta')
        if dato.get('calentamiento_descartado') is not True: motivos.append('sin_calentamiento')
        filas.append({**base, 'prueba': texto(r['prueba']), 'perfil': r.get('perfil'),
                      'metrica': texto(r['metrica']), 'unidad': r['unidad'], 'valor': mediana,
                      'valores': valores, 'variacion': variacion, 'motivos': motivos,
                      'estado': 'revision' if motivos else 'aceptado'})
    if not filas:
        raise ValueError('sin mediciones disponibles')
    return filas


def opendata(dato):
    if dato['schema_version'] != 'v4':
        raise ValueError('esquema histórico no compatible; no se convierte su puntuación')
    identificador = str(UUID(dato['id']))
    filas = []
    for escena in dato['data']:
        dispositivos = escena['device_info']['compute_devices']
        if not dispositivos: raise ValueError('sin dispositivo')
        filas.append({'fuente': 'blender-open-data', 'id_fuente': identificador,
                      'fecha': fecha(dato['created_at']),
                      'version': texto(escena['blender_version']['version']),
                      'escena': texto(escena['scene']['label']),
                      'dispositivos': [texto(d['name']) for d in dispositivos],
                      'backend': texto(escena['device_info']['device_type']),
                      'so': texto(escena['system_info']['system']),
                      'metrica': 'samples_per_minute', 'unidad': 'samples/min',
                      'valor': positivo(escena['stats']['samples_per_minute']),
                      'licencia': 'CC0-1.0', 'licencia_url': LICENCIA, 'preguntas': ['P1'],
                      'estado': 'revision', 'motivos': ['benchmark_publico_no_reproducido_por_g7b']})
    if not filas: raise ValueError('benchmark vacío')
    return filas


def descargar(destino):
    temporal = destino.with_suffix('.part')
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'G7B/0.1 (research; Blender benchmarks)'})
        with urllib.request.urlopen(req, timeout=60) as respuesta, temporal.open('wb') as f:
            total = 0
            while bloque := respuesta.read(1024 * 1024):
                total += len(bloque)
                if total > MAX_ARCHIVO: raise ValueError('snapshot supera límite de descarga')
                f.write(bloque)
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)


def registros_zip(archivo):
    if archivo.stat().st_size > MAX_ARCHIVO: raise ValueError('archivo demasiado grande')
    with zipfile.ZipFile(archivo) as z:
        miembros = z.infolist()
        if sum(m.file_size for m in miembros) > MAX_EXPANDIDO:
            raise ValueError('snapshot expandido demasiado grande')
        licencias = [m for m in miembros if Path(m.filename).name == 'LICENSE.txt']
        if len(licencias) != 1 or licencias[0].file_size > 100000:
            raise ValueError('falta licencia del archivo')
        licencia = z.read(licencias[0]).decode('utf-8').lower()
        if 'cc0' not in licencia and 'creative commons zero' not in licencia:
            raise ValueError('licencia CC0 no confirmada')
        datos = [m for m in miembros if m.filename.endswith('.jsonl')]
        if len(datos) != 1: raise ValueError('se esperaba un único JSONL')
        with z.open(datos[0]) as f:
            while linea := f.readline(MAX_LINEA + 1):
                if len(linea) > MAX_LINEA: raise ValueError('línea demasiado grande')
                if linea.strip(): yield json.loads(linea)


def capturar(registros, fuente, salida, limite=1000, lago=None):
    if fuente not in ('sonda', 'blender-open-data') or not 1 <= limite <= 10000:
        raise ValueError('fuente o límite inválido')
    salida.mkdir(parents=True, exist_ok=True)
    resumen = Counter()
    vistos = set()
    filas, crudos = [], []
    convertir = sonda if fuente == 'sonda' else opendata
    for dato in registros:
        resumen['leidos'] += 1
        if fuente == 'blender-open-data' and isinstance(dato, dict) and dato.get('schema_version') != 'v4':
            resumen['esquema_no_soportado'] += 1
            if resumen['leidos'] >= 100000: break
            continue
        try:
            nuevas = convertir(dato)
            identidad = huella(dato) if fuente == 'sonda' else str(UUID(dato['id']))
            if identidad in vistos:
                resumen['duplicados'] += 1
                continue
            vistos.add(identidad)
            for i, fila in enumerate(nuevas):
                fila.update(contrato='g7b.telemetria/1', sintetico=False,
                            id=huella([fuente, identidad, i]), huella_origen=huella(dato))
            filas.extend(nuevas)
            crudos.append(dato)
            resumen['registros_validos'] += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            resumen['rechazados'] += 1
        if resumen['registros_validos'] >= limite or resumen['leidos'] >= 100000:
            break
    if not filas: raise ValueError('ninguna medición válida; no se publica')
    resumen.update(f['estado'] for f in filas)
    lote = huella(crudos)
    (salida / 'mediciones.jsonl').write_bytes(b'\n'.join(canon(f) for f in filas) + b'\n')
    informe = {'fuente': fuente, 'lote': lote, 'conteos': dict(resumen),
               'limite_registros': limite, 'muestra_no_representativa': True,
               'extraido_en': datetime.now(timezone.utc).isoformat(),
               'url': URL if fuente == 'blender-open-data' else None,
               'azure': 'no_solicitado'}
    if lago is not None:
        prefijo = f'bronce/telemetria/{fuente}/{lote}'
        lago.subir_jsonl_gz(prefijo + '.jsonl.gz', crudos)
        if huella(lago.leer_jsonl_gz(prefijo + '.jsonl.gz')) != lote:
            raise ValueError('falló verificación de bronce en Azure')
        for estado in ('aceptado', 'revision'):
            grupo = [f for f in filas if f['estado'] == estado]
            if grupo:
                ruta = f'plata/telemetria/{estado}/{fuente}/{lote}.jsonl.gz'
                lago.subir_jsonl_gz(ruta, grupo)
                if huella(lago.leer_jsonl_gz(ruta)) != huella(grupo):
                    raise ValueError('falló verificación de plata en Azure')
        informe['azure'] = 'subida_y_lectura_verificadas'
    (salida / 'informe.json').write_bytes(canon(informe))
    return informe


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('fuente', choices=['sonda', 'blender-open-data'])
    p.add_argument('--entrada', type=Path, help='carpeta JSON de sonda o ZIP oficial descargado')
    p.add_argument('--salida', type=Path, required=True)
    p.add_argument('--limite', type=int, default=1000)
    p.add_argument('--azure', action='store_true', help='escribir con las credenciales del entorno')
    a = p.parse_args()
    if not 1 <= a.limite <= 10000: p.error('límite permitido: 1..10000')
    a.salida.mkdir(parents=True, exist_ok=True)
    lago = None
    if a.azure:
        from g7b_lago import Lago
        lago = Lago.desde_entorno()
    if a.fuente == 'sonda':
        if not a.entrada or not a.entrada.is_dir(): p.error('indica la carpeta de la sonda')
        registros = (json.loads(f.read_text(encoding='utf-8')) for f in sorted(a.entrada.glob('*.json'))
                     if f.stat().st_size <= MAX_LINEA)
    else:
        archivo = a.entrada or a.salida / 'opendata.zip'
        if not a.entrada: descargar(archivo)
        registros = registros_zip(archivo)
    print(json.dumps(capturar(registros, a.fuente, a.salida, a.limite, lago), ensure_ascii=False))


if __name__ == '__main__':
    main()
