"""Snapshot de Blender Open Data → tabla plana con el estándar g7b.hardware/1 (mismo código que el lago)."""
import csv, sys, time, collections
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from g7b_telemetria.capturar import registros_zip, opendata
from g7b_telemetria.hardware import limpiar
zipf, salida = Path(sys.argv[2]), Path(sys.argv[3])
errores = collections.Counter(); n = 0; t = time.time()
with open(salida, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['id_fuente', 'fecha', 'version', 'escena', 'backend', 'so', 'mide', 'dispositivo', 'n_dispositivos',
                'fabricante', 'clase', 'vram_gb', 'nivel', 'confianza_nivel', 'valor'])
    for dato in registros_zip(zipf):
        try:
            filas = opendata(dato)
        except Exception as e:
            errores[str(e)[:60]] += 1; continue
        for r in filas:
            hw = r['hardware']
            if hw['mide'] == 'gpu':
                g = hw['gpus'][0]; disp, fab, clase, vram = g['nombre'], g['fabricante'], g['clase'], g.get('vram_gb')
            else:
                c = hw['cpus'][0]; disp, fab, clase, vram = c['nombre'], c['fabricante'], 'cpu', None
            w.writerow([r['id_fuente'], r['fecha'], r['version'], r['escena'], r['backend'], r['so'], hw['mide'], disp,
                        len(r['dispositivos']), fab, clase, vram, hw.get('nivel'), hw.get('confianza'), r['valor']])
            n += 1
print(f'{n} filas en {time.time()-t:.0f} s; errores: {dict(errores.most_common(5))}')
