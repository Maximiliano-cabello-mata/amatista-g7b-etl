"""Invariantes del contrato analitico v2, sin servicios externos."""
from uuid import UUID

import duckdb
import pytest

from g7b_almacen.cubo import construir, preparar
from pruebas.test_cubo import fila


def test_un_hecho_repeticiones_y_hardware_consultable(tmp_path):
    a = fila(equipo={'cpu': 'CPU', 'ram_gb': 16, 'so': 'Linux', 'arquitectura': 'x86_64'})
    informe = construir([('a', a), ('b', a)], tmp_path)
    assert informe['contrato'] == 'g7b.cubo/2'
    assert informe['mediciones'] == 1 and informe['repeticiones'] == 3
    assert not (tmp_path / 'oro/parquet/hechos_medicion.parquet').exists()
    with duckdb.connect(str(tmp_path / 'oro/cubo.duckdb'), read_only=True) as con:
        assert con.execute("SELECT table_type FROM information_schema.tables WHERE table_name='hechos_medicion'").fetchone()[0] == 'VIEW'
        assert con.execute('SELECT cpu, ram_gb, so, mejor, agregacion FROM v_geoda_mediciones').fetchone() == ('CPU', 16, 'Linux', 'menor', 'no_aditiva')
        assert con.execute('SELECT count(*) FROM repeticiones').fetchone()[0] == 3
        assert con.execute('SELECT count(*) FROM procedencia').fetchone()[0] == 2
        assert con.execute('SELECT median(valor) FROM repeticiones').fetchone()[0] == a['valor']
        assert UUID(con.execute('SELECT clave_dispositivo FROM mediciones').fetchone()[0]).version == 5


@pytest.mark.parametrize('cambio', [
    {'metrica': 'tiempo_edicion', 'unidad': 'fps'},
    {'metrica': 'desconocida'}, {'valor': 2}, {'variacion': float('nan')},
    {'valores': [True, 1, 1]}, {'valores': [1, 1, 2], 'variacion': 0},
    {'equipo': {'cpu': 'CPU', 'ram_gb': -1}}, {'motivos': [123]},
])
def test_contradicciones_no_se_publican(cambio):
    with pytest.raises(ValueError):
        preparar([('x', fila(**cambio))])


def test_reprocesar_y_cambiar_orden_no_cambia_claves(tmp_path):
    a, b = fila(), fila(2, version='4.3')
    claves = []
    for nombre, entradas in [('a', [('a', a), ('b', b)]), ('b', [('b', b), ('a', a), ('c', a)])]:
        construir(entradas, tmp_path / nombre)
        with duckdb.connect(str(tmp_path / nombre / 'oro/cubo.duckdb'), read_only=True) as con:
            claves.append(con.execute('SELECT id, clave_dispositivo, clave_version, clave_metrica FROM mediciones ORDER BY id').fetchall())
    assert claves[0] == claves[1]


def test_publico_sin_repeticiones_no_inventa_muestras(tmp_path):
    publico = fila(2, fuente='blender-open-data', estado='revision', motivos=['no_reproducido'],
        dispositivos=['GPU'], backend='CUDA', so='Linux', licencia='CC0-1.0',
        metrica='samples_per_minute', unidad='samples/min', id_fuente='publico-1')
    for campo in ('equipo', 'valores', 'variacion'):
        publico.pop(campo, None)
    informe = construir([('publico', publico)], tmp_path)
    assert informe['repeticiones'] == 0
    with duckdb.connect(str(tmp_path / 'oro/cubo.duckdb'), read_only=True) as con:
        assert con.execute('SELECT id_fuente FROM linaje').fetchone()[0] == 'publico-1'
        assert con.execute('SELECT cpu, ram_gb FROM v_geoda_mediciones').fetchone() == (None, None)


def test_captura_real_contrato_hasta_cubo(tmp_path):
    import json
    from g7b_telemetria.capturar import capturar
    from pruebas.test_telemetria import medicion, benchmark
    datos = medicion()
    datos['resultados'][0]['metrica'] = 'tiempo_edicion'
    entradas = []
    for fuente, dato in [('sonda', datos), ('blender-open-data', benchmark())]:
        carpeta = tmp_path / fuente
        capturar([dato], fuente, carpeta)
        entradas.extend((fuente, json.loads(linea)) for linea in (carpeta / 'mediciones.jsonl').read_text().splitlines())
    resultado = construir(entradas, tmp_path / 'cubo')
    assert resultado['calidad'] == {'aceptado': 1, 'revision': 1}
    assert resultado['repeticiones'] == 3


def test_lector_geoda_admite_v1_y_v2():
    import json
    from g7b_almacen.cubo import sha
    from g7b_almacen.geoda_estado import estado_del_cubo
    from pruebas.test_geoda_estado import LagoFalso
    lago = LagoFalso(contrato='g7b.cubo/1')
    lago.puntero['contrato'] = 'g7b.cubo/1'
    lago.datos = json.dumps(lago.manifiesto).encode()
    lago.puntero['sha256'] = sha(lago.datos)
    assert estado_del_cubo(lago)['mediciones'] == 3003
