import copy
import json
import zipfile

import pytest

from g7b_telemetria.capturar import capturar, opendata, registros_zip, sonda


def medicion():
    return {'contrato': 'g7b.medicion/1', 'sintetico': False, 'sonda': '0.1.0',
            'fecha': '2026-11-03T00:00:00Z', 'blender': {'version': '4.2', 'sin_ventana': True},
            'escena': {'nombre': 'ligera'}, 'equipo': {'cpu': 'prueba'}, 'repeticiones': 3,
            'completa': True, 'calentamiento_descartado': True,
            'resultados': [{'prueba': 'edicion', 'metrica': 'tiempo', 'unidad': 's',
                            'valores': [1, 1.01, 1.02], 'mediana': 1.01}]}


def benchmark():
    return {'schema_version': 'v4', 'id': '00000000-0000-0000-0000-000000000001',
            'created_at': '2026-11-03T00:00:00Z', 'data': [{
                'blender_version': {'version': '4.2'}, 'scene': {'label': 'monster'},
                'system_info': {'system': 'Linux'},
                'device_info': {'device_type': 'CPU', 'compute_devices': [{'name': 'CPU'}]},
                'stats': {'samples_per_minute': 123}}]}


def test_variacion_se_recalcula():
    d = medicion()
    assert sonda(d)[0]['estado'] == 'aceptado'
    d['resultados'][0].update(valores=[.5, 1.01, 2], variacion=0)
    assert sonda(d)[0]['estado'] == 'revision'


@pytest.mark.parametrize('valor', [float('nan'), float('inf'), -1, 0, True])
def test_rechaza_valores_imposibles(valor):
    d = benchmark()
    d['data'][0]['stats']['samples_per_minute'] = valor
    with pytest.raises(ValueError): opendata(d)


def test_no_convierte_sinteticos_ni_medianas_inconsistentes():
    d = medicion()
    d['sintetico'] = True
    with pytest.raises(ValueError): sonda(d)
    d['sintetico'] = False
    d['resultados'][0]['mediana'] = 99
    with pytest.raises(ValueError): sonda(d)


def test_fuente_publica_no_es_fps():
    fila = opendata(benchmark())[0]
    assert fila['unidad'] == 'samples/min'
    assert fila['estado'] == 'revision'
    assert fila['preguntas'] == ['P1']


def test_duplicados_reintentos_y_lectura_azure(tmp_path):
    class Lago:
        def __init__(self): self.archivos = {}
        def subir_jsonl_gz(self, ruta, datos): self.archivos.setdefault(ruta, copy.deepcopy(datos))
        def leer_jsonl_gz(self, ruta): return self.archivos[ruta]
    lago = Lago()
    r = capturar([benchmark(), benchmark()], 'blender-open-data', tmp_path, lago=lago)
    assert r['conteos']['duplicados'] == 1
    assert r['azure'] == 'subida_y_lectura_verificadas'
    antes = copy.deepcopy(lago.archivos)
    capturar([benchmark()], 'blender-open-data', tmp_path, lago=lago)
    assert lago.archivos == antes
    assert len(lago.archivos) == 2


def test_zip_licencia_y_esquema(tmp_path):
    archivo = tmp_path / 'snapshot.zip'
    with zipfile.ZipFile(archivo, 'w') as z:
        z.writestr('LICENSE.txt', 'CC0')
        z.writestr('data.jsonl', json.dumps(benchmark()) + '\n')
    assert len(list(registros_zip(archivo))) == 1
    with zipfile.ZipFile(archivo, 'w') as z:
        z.writestr('data.jsonl', '{}')
    with pytest.raises(ValueError): list(registros_zip(archivo))


def test_sin_datos_no_publica(tmp_path):
    with pytest.raises(ValueError): capturar([{}], 'sonda', tmp_path)


def test_conserva_nivel_y_gpu_para_geoda_sin_datos_personales():
    d = medicion()
    d['equipo'] = {'cpu': 'prueba', 'nivel': 'N2', 'nivel_estimado': True, 'huella': 'abc',
                   'gpu_vista': {'modelo': 'Intel UHD 620', 'version': '4.6'}, 'so_version': '6.1',
                   'gpu_cycles': [], 'usuario': 'no-debe-pasar'}
    equipo = sonda(d)[0]['equipo']
    assert equipo['nivel'] == 'N2' and equipo['gpu_vista']['modelo'] == 'Intel UHD 620'
    assert 'usuario' not in equipo and 'so_version' not in equipo
