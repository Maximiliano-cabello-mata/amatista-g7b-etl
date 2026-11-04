"""Ejecuta el planificador sobre una entrega verificada del cubo, sin aplicar cambios."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import duckdb

from . import VERSION, costos, perfiles, planificador


def ejecutar(entrada, salida):
    entrada, salida = Path(entrada), Path(salida)
    meta = json.loads((entrada / 'manifiesto.json').read_text(encoding='utf-8'))
    db = entrada / 'oro/cubo.duckdb'
    digest = hashlib.sha256(db.read_bytes()).hexdigest()
    if meta.get('contrato') != 'g7b.cubo/1' or digest != meta['archivos']['oro/cubo.duckdb']['sha256']:
        raise ValueError('No coincide el contrato o la huella del cubo')
    with duckdb.connect(str(db), read_only=True) as con:
        calidad = dict(con.execute('SELECT estado,count(*) FROM mediciones GROUP BY estado').fetchall())
        if calidad != meta['calidad'] or sum(calidad.values()) != meta['mediciones']:
            raise ValueError('No coinciden los conteos del manifiesto')
        medidas, omitidas = perfiles.leer_cubo(con)
        documento = perfiles.generar(medidas, omitidas, cubo_version=digest)
        tabla = costos.TablaCostos.desde_cubo(con)
        equipos = con.execute("SELECT DISTINCT dispositivo,version FROM v_mediciones_aceptadas WHERE fuente='sonda'").fetchall()
        planes = Counter()
        for dispositivo, version in equipos:
            equipo = json.loads(dispositivo)['equipo']
            plan = planificador.decidir(equipo, {'tipo': 'practica', 'blender': version}, documento, tabla)
            planes[plan['perfil']['estado']] += 1
    informe = {'contrato': 'g7b.geoda.ejecucion/1', 'geoda': VERSION, 'cubo_sha256': digest,
               'mediciones': meta['mediciones'], 'calidad': calidad, 'mediciones_vista_elegibles': len(medidas),
               'planes_por_estado': dict(planes), 'aplicacion_automatica': False}
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, datos in [('informe', informe), ('perfiles_laboratorio', documento), ('operaciones', costos.catalogo())]:
        (salida / (nombre + '.json')).write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    return informe


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrada', required=True)
    p.add_argument('--salida', required=True)
    a = p.parse_args()
    print('GEODA_VERIFICADA', json.dumps(ejecutar(a.entrada, a.salida)))
