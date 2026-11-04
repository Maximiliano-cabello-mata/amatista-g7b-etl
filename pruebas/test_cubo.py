import json
import os
from uuid import uuid4

import duckdb
import pytest

from g7b_almacen.cubo import ACTUAL, construir, preparar, publicar
from g7b_almacen.descargar import descargar


def fila(i=1, **cambios):
    f = {'id': f'{i:064x}', 'huella_origen': 'a' * 64, 'contrato': 'g7b.telemetria/1',
         'sintetico': False, 'fuente': 'sonda', 'estado': 'aceptado', 'fecha': '2026-11-03T00:00:00Z',
         'version': '4.2.0', 'escena': 'ligera', 'perfil': 'ligero', 'sonda': '0.1.0',
         'metrica': 'tiempo_edicion', 'unidad': 's', 'valor': 1.0, 'motivos': [],
         'variacion': .01, 'valores': [1, 1, 1], 'prueba': 'edicion',
         'equipo': {'cpu': 'CPU', 'so': 'Linux'}, 'licencia': 'propia', 'sin_ventana': True}
    return {**f, **cambios}


def test_estrella_dedup_calidad_y_versiones(tmp_path):
    a = fila()
    b = fila(2, estado='revision', motivos=['variacion'], variacion=.5, valor=100)
    c = fila(3, version='4.2.1', valor=4)
    informe = construir([('lote1', a), ('lote2', a), ('lote1', b), ('lote1', c)], tmp_path)
    assert informe['duplicados_eliminados'] == 1
    assert informe['mediciones'] == 3
    with duckdb.connect(str(tmp_path / 'oro/cubo.duckdb'), read_only=True) as con:
        assert con.execute('SELECT count(*) FROM v_mediciones_aceptadas').fetchone()[0] == 2
        assert con.execute('SELECT count(*) FROM dim_version').fetchone()[0] == 2
        assert con.execute('SELECT count(*) FROM v_resumen').fetchone()[0] == 3
        assert con.execute('SELECT count(*) FROM procedencia').fetchone()[0] == 4
        assert con.execute('SELECT count(*) FROM hechos_render').fetchone()[0] == 0


@pytest.mark.parametrize('cambio', [{'sintetico': True}, {'valor': float('nan')}, {'valor': -2},
                                 {'estado': 'aceptado', 'variacion': .5}, {'fecha': '2026-01-01'},
                                 {'estado': 'inventado'}])
def test_no_publicar_datos_invalidos(cambio):
    with pytest.raises(ValueError): preparar([('x', fila(**cambio))])


def test_conflicto_no_elige_un_valor():
    with pytest.raises(ValueError): preparar([('a', fila()), ('b', fila(valor=2))])
    with pytest.raises(ValueError): preparar([])


def test_unidades_y_escenas_separadas(tmp_path):
    publico = fila(2, fuente='blender-open-data', estado='revision', motivos=['no_reproducido'],
                   dispositivos=['GPU'], backend='CUDA', so='Linux', licencia='CC0-1.0',
                   metrica='samples_per_minute', unidad='samples/min')
    construir([('sonda', fila()), ('publico', publico)], tmp_path)
    with duckdb.connect(str(tmp_path / 'oro/cubo.duckdb'), read_only=True) as con:
        assert con.execute('SELECT count(*) FROM dim_escena').fetchone()[0] == 2
        assert con.execute('SELECT count(*) FROM hechos_render').fetchone()[0] == 1
        assert con.execute('SELECT count(*) FROM v_resumen').fetchone()[0] == 2


class Lago:
    def __init__(self):
        self.archivos = {ACTUAL: b'{"anterior": true}'}
        self.contenedor = self
        self.corromper = False
    def subir_bytes(self, ruta, datos, **kw): self.archivos.setdefault(ruta, datos)
    def escribir_json(self, ruta, dato): self.archivos[ruta] = json.dumps(dato).encode()
    def leer_json(self, ruta): return json.loads(self.archivos[ruta])
    def download_blob(self, ruta):
        contenido = b'corrupto' if self.corromper else self.archivos[ruta]
        return type('Blob', (), {'readall': lambda _: contenido})()


def test_publicacion_no_promueve_si_falla_y_descarga_verifica(tmp_path):
    local = tmp_path / 'construccion'
    informe = construir([('x', fila())], local)
    lago = Lago()
    lago.corromper = True
    with pytest.raises(ValueError): publicar(lago, local, informe)
    assert lago.leer_json(ACTUAL) == {'anterior': True}
    lago.corromper = False
    puntero = publicar(lago, local, informe)
    assert lago.leer_json(ACTUAL) == puntero
    resultado = descargar(lago, tmp_path / 'copia.duckdb')
    assert resultado['mediciones'] == 1
    with pytest.raises(ValueError): descargar(lago, tmp_path / 'copia.duckdb')
    lago.archivos[puntero['cubo']] = b'alterado'
    with pytest.raises(ValueError): descargar(lago, tmp_path / 'corrupto.duckdb')


@pytest.mark.skipif(not os.environ.get('AZURE_PRUEBAS_CONEXION'), reason='requiere Azurite')
def test_cubo_azure_integracion(tmp_path):
    from azure.storage.blob import BlobServiceClient
    from g7b_lago import Lago as LagoReal
    servicio = BlobServiceClient.from_connection_string(os.environ['AZURE_PRUEBAS_CONEXION'])
    contenedor = servicio.create_container('cubo' + uuid4().hex[:12])
    try:
        lago = LagoReal(contenedor)
        informe = construir([('plata/prueba', fila())], tmp_path / 'construccion')
        publicar(lago, tmp_path / 'construccion', informe)
        assert descargar(lago, tmp_path / 'azure.duckdb')['mediciones'] == 1
    finally:
        contenedor.delete_container()
