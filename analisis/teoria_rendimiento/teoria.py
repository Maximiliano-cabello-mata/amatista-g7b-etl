"""Teoría del rendimiento de G7B: predice samples/min de CUALQUIER combinación dispositivo × versión × escena.

    python teoria.py plano.csv carpeta_salida/

Modelo aditivo en escala logarítmica (los rendimientos se multiplican):

    log(samples/min) = base + dispositivo + versión + escena + (backend × versión) + (backend × escena)

Se ajusta por retroajuste (backfitting) sobre la mediana de cada combinación medida, con encogimiento: un efecto con
poca evidencia se acerca a 0 (a «la media»), no se inventa un valor extremo.

Para un dispositivo que nadie midió: su efecto se estima con los 5 dispositivos medidos de NOMBRE más parecido y el
mismo backend (el número de modelo, como 4070 o 7900, y los núcleos de un CPU dicen mucho). Con --hipotetico se
puede pedir la teoría de cualquier nombre:

    python teoria.py plano.csv salida/ --hipotetico "NVIDIA GeForce RTX 5050" OPTIX --hipotetico "AMD Ryzen 5 9600X 6-Core Processor" CPU

Validación (antes de creerle): se esconden combinaciones que sí se midieron, se predicen y se compara.
"""
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np

SEMILLA = 7
LAMBDA = 2.0          # encogimiento: celdas «virtuales» en 0 que se suman a cada efecto
TERMINOS = ('dispositivo', 'version', 'escena', 'backend_version', 'backend_escena')


def cargar(plano):
    c = duckdb.connect()
    c.execute(f"""
        create table t as select * from read_csv_auto('{plano}', header=true, all_varchar=false)""")
    c.execute(r"""
        create table limpia as
        select dispositivo, backend, fabricante, clase, try_cast(vram_gb as double) vram_gb, nivel,
               regexp_extract(version, '^(\d+\.\d+)') as version, escena, ln(valor) as lv
        from t
        where n_dispositivos = 1 and valor > 0
          and not regexp_matches(version, 'alpha|beta|rc', 'i')""")
    total = c.execute("select count(*) from t").fetchone()[0]
    usadas = c.execute("select count(*) from limpia").fetchone()[0]
    celdas = c.execute("""
        select dispositivo || ' · ' || backend as id, dispositivo, backend, any_value(fabricante), any_value(clase),
               any_value(vram_gb), any_value(nivel), version, escena, count(*) n,
               median(lv) med, quantile_cont(lv, 0.25) p25, quantile_cont(lv, 0.75) p75
        from limpia group by all having count(*) >= 1
        order by id, version, escena""").fetchall()      # orden fijo: la partición al azar de la validación es reproducible
    return celdas, {'filas_snapshot': total, 'filas_usadas': usadas}


def claves(celda):
    _id, _d, b, *_ , v, e = celda[:9]
    return {'dispositivo': celda[0], 'version': celda[7], 'escena': celda[8],
            'backend_version': f'{celda[2]}|{celda[7]}', 'backend_escena': f'{celda[2]}|{celda[8]}'}


def ajustar(celdas, iteraciones=60):
    """Retroajuste con encogimiento. Devuelve base y efectos {término: {clave: efecto}}."""
    y = np.array([c[10] for c in celdas])
    w = np.log1p(np.array([c[9] for c in celdas], dtype=float))      # más mediciones, más peso, sin dominar
    ks = [claves(c) for c in celdas]
    base = float(np.average(y, weights=w))
    efectos = {t: defaultdict(float) for t in TERMINOS}
    indices = {t: defaultdict(list) for t in TERMINOS}
    for i, k in enumerate(ks):
        for t in TERMINOS:
            indices[t][k[t]].append(i)
    pred = np.full(len(y), base)
    for _ in range(iteraciones):
        cambio = 0.0
        for t in TERMINOS:
            actual = np.array([efectos[t][k[t]] for k in ks])
            resid = y - (pred - actual)
            for clave, idx in indices[t].items():
                nuevo = float(np.sum(w[idx] * resid[idx]) / (np.sum(w[idx]) + LAMBDA))
                cambio = max(cambio, abs(nuevo - efectos[t][clave]))
                efectos[t][clave] = nuevo
            pred = pred - actual + np.array([efectos[t][k[t]] for k in ks])
        if cambio < 1e-7:
            break
    return base, {t: dict(v) for t, v in efectos.items()}


def predecir(base, efectos, k, efecto_dispositivo=None):
    d = efectos['dispositivo'].get(k['dispositivo'], 0.0) if efecto_dispositivo is None else efecto_dispositivo
    return base + d + sum(efectos[t].get(k[t], 0.0) for t in TERMINOS if t != 'dispositivo')


def vram_grupo(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 'sin dato'
    return '≤4 GB' if v <= 4 else '6–8 GB' if v <= 8 else '10–12 GB' if v <= 12 else '16 GB' if v <= 16 else '>16 GB'


def grupos_hardware(dispositivos, efectos):
    """Efecto medio de los dispositivos por grupo de características, de lo específico a lo general."""
    niveles = [('backend', 'clase', 'fabricante', 'vram'), ('backend', 'clase', 'fabricante'), ('backend', 'clase'), ('backend',)]
    tablas = []
    for campos in niveles:
        acum = defaultdict(list)
        for d in dispositivos.values():
            if d['id'] in efectos['dispositivo']:
                acum[tuple(d[c] for c in campos)].append(efectos['dispositivo'][d['id']])
        tablas.append((campos, {k: (sum(v) / (len(v) + 1.0), len(v)) for k, v in acum.items()}))   # encogimiento suave
    return tablas


def efecto_por_caracteristicas(tablas, d, minimo=3):
    for campos, tabla in tablas:
        k = tuple(d[c] for c in campos)
        if k in tabla and tabla[k][1] >= minimo:
            return tabla[k][0], ' + '.join(campos), tabla[k][1]
    return 0.0, 'media general', 0


PALABRAS_VACIAS = {'nvidia', 'geforce', 'amd', 'radeon', 'intel', 'r', 'tm', 'graphics', 'processor', 'cpu', 'core',
                   'gpu', 'apple', 'with'}


def rasgos(nombre):
    n = nombre.lower()
    toks = set(re.findall(r'[a-z]+|\d+', n)) - PALABRAS_VACIAS
    nums = [int(x) for x in re.findall(r'\d{3,5}', n)]
    nucleos = re.search(r'(\d+)-core', n)
    return toks, (nums[0] if nums else None), (int(nucleos.group(1)) if nucleos else None)


def similitud(a, b):
    """Parecido entre dos nombres: palabras en común + número de modelo cercano + núcleos cercanos."""
    (ta, na, ca), (tb, nb, cb) = a, b
    s = len(ta & tb) / max(1, len(ta | tb))
    if na and nb:
        s += 1.0 / (1 + abs(math.log(na) - math.log(nb)) * 20)
    if ca and cb:
        s += 1.0 / (1 + abs(ca - cb) / 4)
    return s


def efecto_por_nombre(nombre, backend, dispositivos, efectos, k=5):
    """Efecto estimado de un dispositivo por sus k vecinos de nombre más parecido (mismo backend)."""
    r = rasgos(nombre)
    pares = sorted(((similitud(r, rasgos(d['dispositivo'])), efectos['dispositivo'][d['id']], d['dispositivo'])
                    for d in dispositivos.values() if d['backend'] == backend and d['id'] in efectos['dispositivo']),
                   reverse=True)[:k]
    if not pares:
        return 0.0, []
    w = np.array([p[0] for p in pares]) + 1e-6
    return float(np.average([p[1] for p in pares], weights=w)), [p[2] for p in pares]


def errores(reales, predichos):
    e = np.exp(np.array(predichos) - np.array(reales)) - 1          # error relativo (predicho/real − 1)
    a = np.abs(e)
    return {'n': int(len(a)), 'error_mediano_pct': float(np.median(a) * 100),
            'dentro_25pct': float(np.mean(a <= 0.25)), 'dentro_50pct': float(np.mean(a <= 0.50))}


def validar(celdas, dispositivos):
    rng = np.random.default_rng(SEMILLA)
    resultados = {}
    # A) Combinaciones medidas escondidas al azar (20 %).
    mascara = rng.random(len(celdas)) < 0.2
    entren = [c for c, m in zip(celdas, mascara) if not m]
    prueba = [c for c, m in zip(celdas, mascara) if m]
    base, ef = ajustar(entren)
    resultados['A_combinaciones_al_azar'] = errores([c[10] for c in prueba], [predecir(base, ef, claves(c)) for c in prueba])
    # Referencia ingenua: el promedio del dispositivo, sin versión ni escena.
    por_disp = defaultdict(list)
    for c in entren:
        por_disp[c[0]].append(c[10])
    media = float(np.mean([c[10] for c in entren]))
    resultados['A_referencia_promedio_dispositivo'] = errores(
        [c[10] for c in prueba], [np.mean(por_disp[c[0]]) if c[0] in por_disp else media for c in prueba])
    # B) Un dispositivo en una versión donde nunca se midió (se esconden todas sus escenas en esa versión).
    pares = sorted({(c[0], c[7]) for c in celdas})
    versiones_por_disp = defaultdict(set)
    for d, v in pares:
        versiones_por_disp[d].add(v)
    candidatos = [p for p in pares if len(versiones_por_disp[p[0]]) >= 2]
    escondidos = {candidatos[i] for i in rng.choice(len(candidatos), size=len(candidatos) // 5, replace=False)}
    entren = [c for c in celdas if (c[0], c[7]) not in escondidos]
    prueba = [c for c in celdas if (c[0], c[7]) in escondidos]
    base, ef = ajustar(entren)
    pred_b = [predecir(base, ef, claves(c)) for c in prueba]
    resultados['B_dispositivo_en_version_nueva'] = errores([c[10] for c in prueba], pred_b)
    # Intervalos: cuantiles del error en B, según cuánta evidencia tiene el dispositivo.
    n_celdas = defaultdict(int)
    for c in entren:
        n_celdas[c[0]] += 1
    por_grupo = defaultdict(list)
    for c, p in zip(prueba, pred_b):
        por_grupo[grupo_evidencia(n_celdas[c[0]])].append(c[10] - p)
    intervalos = {g: (float(np.quantile(r, 0.10)), float(np.quantile(r, 0.90)), len(r)) for g, r in por_grupo.items()}
    # C) Un dispositivo que nadie midió: se esconde entero y se estima por sus características.
    ids = sorted({c[0] for c in celdas})
    con_datos = [i for i in ids if sum(1 for c in celdas if c[0] == i) >= 3]
    fuera = set(rng.choice(con_datos, size=len(con_datos) // 5, replace=False))
    entren = [c for c in celdas if c[0] not in fuera]
    prueba = [c for c in celdas if c[0] in fuera]
    base, ef = ajustar(entren)
    conocidos = {k: v for k, v in dispositivos.items() if k not in fuera}
    tablas = grupos_hardware(conocidos, ef)
    pred_c2 = [predecir(base, ef, claves(c), efecto_por_caracteristicas(tablas, dispositivos[c[0]])[0]) for c in prueba]
    resultados['C2_nunca_medido_por_caracteristicas'] = errores([c[10] for c in prueba], pred_c2)
    por_nombre = {i: efecto_por_nombre(dispositivos[i]['dispositivo'], dispositivos[i]['backend'], conocidos, ef)[0] for i in fuera}
    pred_c = [predecir(base, ef, claves(c), por_nombre[c[0]]) for c in prueba]
    resultados['C_dispositivo_nunca_medido_por_nombre'] = errores([c[10] for c in prueba], pred_c)
    r = [c[10] - p for c, p in zip(prueba, pred_c)]
    intervalos['hipotético (estimado por nombre)'] = (float(np.quantile(r, 0.10)), float(np.quantile(r, 0.90)), len(r))
    return resultados, intervalos


def grupo_evidencia(n):
    return 'poca (1–5 combinaciones)' if n <= 5 else 'media (6–20)' if n <= 20 else 'mucha (>20)'


def orden_version(v):
    a, b = v.split('.')
    return int(a) * 100 + int(b)


def escribir(ruta, encabezado, filas):
    with open(ruta, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(encabezado)
        w.writerows(filas)


def main():
    plano, salida = Path(sys.argv[1]), Path(sys.argv[2])
    hipoteticos = []
    resto = sys.argv[3:]
    while resto:
        if resto[0] != '--hipotetico' or len(resto) < 3:
            sys.exit('uso: teoria.py plano.csv salida/ [--hipotetico "NOMBRE" BACKEND]...')
        hipoteticos.append((resto[1], resto[2].upper()))
        resto = resto[3:]
    salida.mkdir(parents=True, exist_ok=True)
    celdas, conteo = cargar(plano)
    dispositivos = {}
    for c in celdas:
        d = dispositivos.setdefault(c[0], {'id': c[0], 'dispositivo': c[1], 'backend': c[2], 'fabricante': c[3] or 'desconocido',
                                           'clase': c[4] or 'desconocida', 'vram_gb': c[5], 'nivel': c[6] or '',
                                           'vram': vram_grupo(c[5]), 'n_celdas': 0, 'n': 0, 'versiones': set()})
        d['n_celdas'] += 1
        d['n'] += c[9]
        d['versiones'].add(c[7])
    print(f"{conteo['filas_usadas']} de {conteo['filas_snapshot']} mediciones; {len(celdas)} combinaciones medidas; "
          f"{len(dispositivos)} dispositivos")
    validacion, intervalos = validar(celdas, dispositivos)
    for k, v in validacion.items():
        print(f"  {k}: error mediano {v['error_mediano_pct']:.1f} % · dentro de ±25 %: {v['dentro_25pct']:.0%} · n={v['n']}")
    print('  intervalos 80 % (factor bajo–alto):', {g: (round(math.exp(a), 2), round(math.exp(b), 2), n) for g, (a, b, n) in intervalos.items()})

    base, ef = ajustar(celdas)
    tablas = grupos_hardware(dispositivos, ef)
    versiones = sorted({c[7] for c in celdas}, key=orden_version)
    escenas = sorted({c[8] for c in celdas})
    backends = sorted({d['backend'] for d in dispositivos.values()})
    n_ver, n_esc = defaultdict(int), defaultdict(int)
    for c in celdas:
        n_ver[c[7]] += c[9]
        n_esc[c[8]] += c[9]

    filas_hipoteticas = []
    for nombre, backend in hipoteticos:
        efecto, vecinos = efecto_por_nombre(nombre, backend, dispositivos, ef)
        print(f'  hipotético {nombre} ({backend}): factor {math.exp(efecto):.2f} × la media; vecinos: {vecinos}')
        filas_hipoteticas.append([f'{nombre} · {backend} (hipotético)', nombre, backend, '', '', '', '', '', round(efecto, 6),
                                  round(math.exp(efecto), 4), 0, 0, '', '', 'hipotético (estimado por nombre)',
                                  '; '.join(vecinos)])
    escribir(salida / 'dispositivos.csv',
             ['id', 'dispositivo', 'backend', 'fabricante', 'clase', 'vram_gb', 'grupo_vram', 'nivel', 'efecto', 'factor',
              'n_combinaciones', 'n_mediciones', 'version_min', 'version_max', 'evidencia', 'vecinos'],
             [[d['id'], d['dispositivo'], d['backend'], d['fabricante'], d['clase'],
               '' if d['vram_gb'] is None else d['vram_gb'], d['vram'], d['nivel'],
               round(ef['dispositivo'][d['id']], 6), round(math.exp(ef['dispositivo'][d['id']]), 4),
               d['n_celdas'], d['n'], min(d['versiones'], key=orden_version), max(d['versiones'], key=orden_version),
               grupo_evidencia(d['n_celdas']), ''] for d in sorted(dispositivos.values(), key=lambda x: x['id'])]
             + filas_hipoteticas)
    escribir(salida / 'versiones.csv', ['version', 'orden', 'efecto', 'factor', 'n_mediciones'],
             [[v, orden_version(v), round(ef['version'][v], 6), round(math.exp(ef['version'][v]), 4), n_ver[v]] for v in versiones])
    escribir(salida / 'escenas.csv', ['escena', 'efecto', 'factor', 'n_mediciones'],
             [[e, round(ef['escena'][e], 6), round(math.exp(ef['escena'][e]), 4), n_esc[e]] for e in escenas])
    escribir(salida / 'backend_version.csv', ['clave', 'backend', 'version', 'efecto', 'factor'],
             [[f'{b}|{v}', b, v, round(ef['backend_version'].get(f'{b}|{v}', 0.0), 6), round(math.exp(ef['backend_version'].get(f'{b}|{v}', 0.0)), 4)]
              for b in backends for v in versiones])
    escribir(salida / 'backend_escena.csv', ['clave', 'backend', 'escena', 'efecto', 'factor'],
             [[f'{b}|{e}', b, e, round(ef['backend_escena'].get(f'{b}|{e}', 0.0), 6), round(math.exp(ef['backend_escena'].get(f'{b}|{e}', 0.0)), 4)]
              for b in backends for e in escenas])
    filas_hw = []
    for campos, tabla in tablas[:1]:      # el grupo más específico: backend + clase + fabricante + memoria
        for k, (efecto, n) in sorted(tabla.items()):
            d = dict(zip(campos, k))
            efecto_final, nivel_usado, n_usado = efecto_por_caracteristicas(tablas, d)
            filas_hw.append([' · '.join(map(str, k)), d['backend'], d['clase'], d['fabricante'], d['vram'],
                             round(efecto_final, 6), round(math.exp(efecto_final), 4), n, nivel_usado])
    escribir(salida / 'hardware_teorico.csv',
             ['clave', 'backend', 'clase', 'fabricante', 'grupo_vram', 'efecto', 'factor', 'n_dispositivos', 'estimado_con'], filas_hw)
    escribir(salida / 'combinaciones_medidas.csv',
             ['id', 'version', 'escena', 'clave_bv', 'clave_be', 'n', 'mediana', 'p25', 'p75', 'teoria', 'error_pct'],
             [[c[0], c[7], c[8], f'{c[2]}|{c[7]}', f'{c[2]}|{c[8]}', c[9], round(math.exp(c[10]), 3), round(math.exp(c[11]), 3),
               round(math.exp(c[12]), 3), round(math.exp(predecir(base, ef, claves(c))), 3),
               round((math.exp(predecir(base, ef, claves(c)) - c[10]) - 1) * 100, 2)] for c in celdas])
    escribir(salida / 'intervalos.csv', ['evidencia', 'factor_bajo', 'factor_alto', 'n_validacion'],
             [[g, round(math.exp(a), 4), round(math.exp(b), 4), n] for g, (a, b, n) in sorted(intervalos.items())])
    modelo = {'base_log': base, 'base_samples_min': math.exp(base), 'lambda': LAMBDA, **conteo,
              'combinaciones_medidas': len(celdas), 'dispositivos': len(dispositivos),
              'combinaciones_posibles': len(dispositivos) * len(versiones) * len(escenas), 'validacion': validacion}
    (salida / 'modelo.json').write_text(json.dumps(modelo, ensure_ascii=False, indent=2), encoding='utf-8')
    escribir(salida / 'modelo.csv', ['clave', 'valor'],
             [['base_log', round(base, 6)], ['base_samples_min', round(math.exp(base), 3)],
              ['combinaciones_medidas', len(celdas)], ['combinaciones_posibles', modelo['combinaciones_posibles']],
              ['dispositivos', len(dispositivos)], ['mediciones_usadas', conteo['filas_usadas']]] +
             [[f'{k}_error_mediano_pct', round(v['error_mediano_pct'], 2)] for k, v in validacion.items()] +
             [[f'{k}_dentro_25pct', round(v['dentro_25pct'], 4)] for k, v in validacion.items()])


if __name__ == '__main__':
    main()
