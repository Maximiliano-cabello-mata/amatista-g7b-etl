"""Descarga y verifica el cubo vigente para Deepnote o una computadora local."""
import argparse
import json
from pathlib import Path

import duckdb

from .cubo import ACTUAL, CONTRATO, sha


def descargar(lago, destino):
    destino = Path(destino)
    if destino.exists(): raise ValueError('elige un archivo nuevo para no sobrescribir una copia abierta')
    puntero = lago.leer_json(ACTUAL)
    if not puntero or puntero.get('contrato') != CONTRATO:
        raise ValueError('no hay cubo publicado compatible')
    contenido = lago.contenedor.download_blob(puntero['manifiesto']).readall()
    if sha(contenido) != puntero['sha256']: raise ValueError('manifiesto alterado')
    manifiesto = json.loads(contenido)
    meta = manifiesto['archivos']['oro/cubo.duckdb']
    datos = lago.contenedor.download_blob(meta['ruta']).readall()
    if sha(datos) != meta['sha256'] or len(datos) != meta['bytes']:
        raise ValueError('cubo alterado')
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Escritura exclusiva: nunca reemplazar una base que pueda estar abierta.
    with destino.open('xb') as archivo:
        archivo.write(datos)
    with duckdb.connect(str(destino), read_only=True) as con:
        if con.execute('SELECT count(*) FROM mediciones').fetchone()[0] != manifiesto['mediciones']:
            raise ValueError('conteo distinto al manifiesto')
    return {'version': puntero['version'], 'mediciones': manifiesto['mediciones'], 'sha256': meta['sha256']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destino', type=Path)
    a = p.parse_args()
    from g7b_lago import Lago
    print(json.dumps(descargar(Lago.desde_entorno(), a.destino)))


if __name__ == '__main__': main()
