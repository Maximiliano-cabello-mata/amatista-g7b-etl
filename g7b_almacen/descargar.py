"""Descarga y verifica el cubo vigente para Deepnote o una computadora local."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from .cubo import ACTUAL, CONTRATOS_LEGIBLES, sha
from .esquema_cubo import hechos_separados


def descargar(lago, destino):
    resultado, _ = descargar_con_manifiesto(lago, destino)
    return resultado


def descargar_con_manifiesto(lago, destino):
    destino = Path(destino)
    if destino.exists(): raise ValueError('elige un archivo nuevo para no sobrescribir una copia abierta')
    puntero = lago.leer_json(ACTUAL)
    if not puntero or puntero.get('contrato') not in CONTRATOS_LEGIBLES:
        raise ValueError('no hay cubo publicado compatible')
    contenido = lago.contenedor.download_blob(puntero['manifiesto']).readall()
    if sha(contenido) != puntero['sha256']: raise ValueError('manifiesto alterado')
    manifiesto = json.loads(contenido)
    if manifiesto.get('contrato') != puntero['contrato'] or manifiesto.get('version') != puntero['version']:
        raise ValueError('puntero y manifiesto distintos')
    separados = hechos_separados(manifiesto)
    meta = manifiesto['archivos']['oro/cubo.duckdb']
    datos = lago.contenedor.download_blob(meta['ruta']).readall()
    if sha(datos) != meta['sha256'] or len(datos) != meta['bytes']:
        raise ValueError('cubo alterado')
    destino.parent.mkdir(parents=True, exist_ok=True)
    consulta = ('SELECT (SELECT count(*) FROM hechos_directos) + (SELECT count(*) FROM hechos_relativos)'
                if separados else 'SELECT count(*) FROM mediciones')
    # Validar antes de crear el destino permite reintentar después de un cubo inválido.
    with TemporaryDirectory(dir=destino.parent) as carpeta:
        copia = Path(carpeta) / 'verificar.duckdb'
        copia.write_bytes(datos)
        with duckdb.connect(str(copia), read_only=True) as con:
            if con.execute(consulta).fetchone()[0] != manifiesto['mediciones']:
                raise ValueError('conteo distinto al manifiesto')
    with destino.open('xb') as archivo:
        try:
            archivo.write(datos)
        except OSError:
            archivo.close()
            destino.unlink()
            raise
    return {'version': puntero['version'], 'mediciones': manifiesto['mediciones'], 'sha256': meta['sha256']}, manifiesto


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destino', type=Path)
    a = p.parse_args()
    from g7b_lago import Lago
    print(json.dumps(descargar(Lago.desde_entorno(), a.destino)))


if __name__ == '__main__': main()
