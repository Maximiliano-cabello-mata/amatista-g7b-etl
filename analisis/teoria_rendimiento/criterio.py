"""Prototipo del criterio automático para el cubo: cada medición se juzga contra sus pares y contra la teoría.
Prueba sin etiquetas humanas: se corrompen mediciones a propósito y se mide cuántas detecta y cuántas buenas marca mal."""
import csv, math, sys, time
import duckdb, numpy as np

plano, datos = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(11)
c = duckdb.connect()
c.execute(rf"""create table m as select row_number() over () rid, dispositivo || ' · ' || backend id, backend,
    regexp_extract(version, '^(\d+\.\d+)') version, escena, ln(valor) lv
    from read_csv_auto('{plano}', header=true) where n_dispositivos = 1 and valor > 0
    and not regexp_matches(version, 'alpha|beta|rc', 'i')""")
df = c.execute("select rid, id, backend, version, escena, lv from m").df()
# Teoría por combinación (los factores que exportó teoria.py)
L = lambda f: {r[k]: r for r in csv.DictReader(open(f'{datos}/{f}', encoding='utf-8')) for k in [list(r)[0]]}
D, V, E = L('dispositivos.csv'), L('versiones.csv'), L('escenas.csv')
BV = {r['clave']: float(r['efecto']) for r in csv.DictReader(open(f'{datos}/backend_version.csv', encoding='utf-8'))}
BE = {r['clave']: float(r['efecto']) for r in csv.DictReader(open(f'{datos}/backend_escena.csv', encoding='utf-8'))}
base = float({r['clave']: r['valor'] for r in csv.DictReader(open(f'{datos}/modelo.csv'))}['base_log'])
def teoria(i, b, v, e):
    return base + float(D[i]['efecto']) + float(V[v]['efecto']) + BV.get(f'{b}|{v}', 0) + float(E[e]['efecto']) + BE.get(f'{b}|{e}', 0)
df['teo'] = [teoria(i, b, v, e) for i, b, v, e in zip(df.id, df.backend, df.version, df.escena)]

def juzgar(d):
    """Estado por medición: corroborado / anómalo / sin pares suficientes."""
    g = d.groupby(['id', 'version', 'escena'])['lv']
    d = d.assign(n=g.transform('size'), med=g.transform('median'),
                 mad=g.transform(lambda x: np.median(np.abs(x - np.median(x)))))
    escala = np.maximum(1.4826 * d['mad'], 0.08)              # piso: 8 % de dispersión natural
    z_pares = (d['lv'] - d['med']).abs() / escala
    z_teo = (d['lv'] - d['teo']).abs()                        # en log; 0.69 = el doble o la mitad
    con_pares = d['n'] >= 4
    anom = (con_pares & (z_pares > 4)) | (~con_pares & (z_teo > math.log(2.5)))
    corrob = con_pares & (z_pares <= 2.5) & (z_teo <= math.log(2.5))
    estado = np.where(anom, 'anomalo', np.where(corrob, 'corroborado', 'sin_pares_suficientes'))
    return estado

t = time.time()
estado = juzgar(df)
print(f'{len(df):,} mediciones juzgadas en {time.time()-t:.0f} s')
u, k = np.unique(estado, return_counts=True); print('estados:', dict(zip(u, [f'{x:,} ({x/len(df):.1%})' for x in k])))

# Prueba con errores sembrados: 2 % de las mediciones se corrompen de 4 formas realistas.
d2 = df.copy(); n = len(d2); idx = rng.choice(n, size=n // 50, replace=False)
tipos = rng.choice(['x3', 'entre3', 'x1.6', 'otro_dispositivo'], size=len(idx))
lv = d2['lv'].to_numpy().copy(); ids = d2['id'].to_numpy().copy()
todos = d2['id'].unique()
for j, ti in zip(idx, tipos):
    if ti == 'x3': lv[j] += math.log(3)
    elif ti == 'entre3': lv[j] -= math.log(3)
    elif ti == 'x1.6': lv[j] += math.log(1.6)
    else: lv[j] = d2['lv'].iloc[rng.integers(n)]              # valor de otra medición cualquiera
d2['lv'] = lv
e2 = juzgar(d2)
sembrado = np.zeros(n, bool); sembrado[idx] = True
print(f'\nerrores sembrados: {sembrado.sum():,}')
for ti in ['x3', 'entre3', 'x1.6', 'otro_dispositivo']:
    m = np.zeros(n, bool); m[idx[tipos == ti]] = True
    print(f'  {ti:17s} detectados como anómalos: {np.mean(e2[m] == "anomalo"):.0%} · aceptados como corroborados: {np.mean(e2[m] == "corroborado"):.1%}')
limpios = ~sembrado
print(f'  mediciones limpias marcadas como anómalas (falsa alarma): {np.mean(e2[limpios] == "anomalo"):.1%}')
print(f'  pureza de «corroborado» (sin error sembrado): {1 - np.mean(sembrado[e2 == "corroborado"]):.2%}')
