"""Comprueba que hp/motor.py reproduce al motor de Sprint_3.ipynb (energía, nodos y movimientos)."""
import sys, os, time
from multiprocessing import Pool
sys.path[:0] = [os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.path.dirname(os.path.abspath(__file__))]
import motor_sprint3 as viejo
from hp import motor as nuevo

CFGS = [viejo.CONFIG_ACTUAL, viejo.CONFIG_ACTUAL._replace(r4=0),
        viejo.ConfigHP(1.26, 1.61, 0.70, 0.33, 1.79, 1.25, True, 1),
        viejo.ConfigHP(1.18, 1.37, 3.77, 0.0, 1.18, 1.47, False, 1)]

def caso(t):
    s, cfg = t
    a = viejo.a_estrella_param(s, cfg, 250_000)
    b = nuevo.a_estrella(s, nuevo.ConfigHP(*cfg), 250_000)
    tr = []
    c = nuevo.a_estrella(s, nuevo.ConfigHP(*cfg), 250_000, traza=tr) if len(s) <= 14 else b
    return s, cfg, tuple(a) == (b.movs, b.energia, b.nodos, b.estado) == (c.movs, c.energia, c.nodos, c.estado), a, b

if __name__ == '__main__':
    t0 = time.time()
    tareas = [(s, c) for c in CFGS for s, *_ in viejo.BANCO]
    with Pool(16) as p:
        res = p.map(caso, tareas, chunksize=1)
    malos = [r for r in res if not r[2]]
    print(f'{len(res) - len(malos)}/{len(res)} idénticos ({time.time() - t0:.0f} s)')
    for r in malos[:5]:
        print(r)
    # Óptimo exhaustivo: mismo valor que el original en las cortas
    cortas = [(s, e) for s, e, est, *_ in viejo.BANCO if est == 'C'][:12]
    ok = all(nuevo.optimo_exhaustivo(s)[0] == viejo.optimo_exhaustivo(s) == e for s, e in cortas)
    print('óptimo exhaustivo coincide:', ok)
