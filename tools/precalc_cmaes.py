"""Repite el afinamiento con CMA-ES de Sprint_3.ipynb (celdas 16–20) y guarda la historia
de convergencia y los resultados en datos/cmaes.json. Mismas semillas y ajustes."""
import sys, os, math, json, time
from functools import cmp_to_key
from multiprocessing import Pool
import numpy as np
import cma
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [RAIZ, os.path.join(RAIZ, 'tools')]
from motor_sprint3 import BANCO
from hp.motor import a_estrella, ConfigHP, CONFIG_ACTUAL, NOMBRES

LIMITES = np.array([[0, 3], [0, 3], [0, 4], [0, 1.5], [0.5, 2], [0.5, 2]], dtype=float)
TOPE, TOL, MARGEN = 250_000, 1e-3, 0.10
LAMBDA, MU, SIGMA0, GENS = 9, 4, 0.25, 15
E_REF = {s: e for s, e, *_ in BANCO}
ENTR = [s for s, _, _, c, _ in BANCO if c == 'E']
PRUEBA = [s for s, _, _, c, _ in BANCO if c == 'P']
CENT = [s for s, *_, k in BANCO if k]
MEMO = {}
POOL = None

def decodificar(x, g, r4):
    v = LIMITES[:, 0] + np.asarray(x) * (LIMITES[:, 1] - LIMITES[:, 0])
    return ConfigHP(*map(float, v), bool(g), int(r4))

def _buscar(t):
    s, c = t
    r = a_estrella(s, c, TOPE)
    return r.energia, r.nodos, r.estado

def resolver(cfgs, secs):
    pend = sorted({(s, c) for c in cfgs for s in secs if (c, s) not in MEMO}, key=lambda t: -len(t[0]))
    for (s, c), r in zip(pend, POOL.imap(_buscar, pend)):
        MEMO[(c, s)] = r

def medir(cfgs, secs):
    resolver(cfgs, secs)
    out = []
    for c in cfgs:
        errs, costos = [], []
        for s in secs:
            e, nodos, est = MEMO[(c, s)]
            if est != 'ok':
                errs.append(1.0); costos.append(math.log10(TOPE)); continue
            errs.append(max((e - E_REF[s]) / abs(E_REF[s]), 0.0)); costos.append(math.log10(nodos + 1))
        out.append(dict(error=float(np.mean(errs)), costo=float(np.mean(costos)), aciertos=sum(e == 0 for e in errs)))
    return out

def comparar(a, b):
    if abs(a[0] - b[0]) >= TOL:
        return -1 if a[0] < b[0] else 1
    return (a[1] > b[1]) - (a[1] < b[1])

def ordenar(claves):
    return sorted(range(len(claves)), key=cmp_to_key(lambda i, j: comparar(claves[i], claves[j])))

def domina(a, b):
    return a[0] < b[0] + TOL and a[1] <= b[1] and (a[0] <= b[0] - TOL or a[1] < b[1])

def generacion(X, g, r4):
    cand = []
    for x in X:
        xp = np.clip(x, 0, 1)
        cand.append(dict(x=np.round(xp, 3), pen=float(np.sum((x - xp) ** 2))))
        cand[-1]['cfg'] = decodificar(cand[-1]['x'], g, r4)
    m1 = medir([c['cfg'] for c in cand], CENT)
    k1 = [(m['error'] + c['pen'], m['costo'] + c['pen']) for m, c in zip(m1, cand)]
    o1 = ordenar(k1)
    siguen = [i for p, i in enumerate(o1) if p < MU or k1[i][0] <= k1[o1[0]][0] + MARGEN]
    for i, m in zip(siguen, medir([cand[i]['cfg'] for i in siguen], ENTR)):
        cand[i].update(completo=True, error=m['error'], costo=m['costo'],
                       clave=(m['error'] + cand[i]['pen'], m['costo'] + cand[i]['pen']))
    aband = [i for i in range(len(cand)) if i not in siguen]
    for i in aband:
        cand[i].update(completo=False, clave=k1[i])
    orden = [siguen[j] for j in ordenar([cand[i]['clave'] for i in siguen])] + \
            [aband[j] for j in ordenar([cand[i]['clave'] for i in aband])]
    return orden, cand

def optimizar(g, r4, semilla):
    es = cma.CMAEvolutionStrategy([0.5] * 6, SIGMA0, {'popsize': LAMBDA, 'CMA_mu': MU, 'CMA_active': False,
                                  'seed': semilla, 'verbose': -9, 'verb_log': 0, 'verb_disp': 0})
    mejor, hist, nubes = None, [], []
    for _ in range(GENS):
        X = es.ask()
        orden, cand = generacion(np.array(X), g, r4)
        pos = np.empty(LAMBDA); pos[orden] = np.arange(LAMBDA)
        es.tell(X, pos.tolist())
        for c in cand:
            if c['completo'] and (mejor is None or comparar((c['error'], c['costo']), (mejor['error'], mejor['costo'])) < 0):
                mejor = c
        hist.append((mejor['error'], mejor['costo']))
        nubes.append(dict(media=np.round(es.mean, 4).tolist(), sigma=float(es.sigma),
                          cand=[[round(float(v), 3) for v in c['x']] for c in cand]))
    return dict(global_=g, r4=r4, cfg=mejor['cfg']._asdict(), error=mejor['error'], costo=mejor['costo'],
                historia=hist, nubes=nubes)

if __name__ == '__main__':
    POOL = Pool(16)
    t0 = time.time()
    base = {n: medir([CONFIG_ACTUAL], c)[0] for n, c in (('entrenamiento', ENTR), ('prueba', PRUEBA))}
    print('base', base)
    corr = []
    for i, (g, r4) in enumerate([(g, r) for g in (True, False) for r in (0, 1, 2)]):
        corr.append(optimizar(g, r4, 1000 + i))
        print(g, r4, round(corr[-1]['error'], 4), round(corr[-1]['costo'], 3), f'{time.time() - t0:.0f}s', flush=True)
    bp = (base['prueba']['error'], base['prueba']['costo'])
    for c, m in zip(corr, medir([ConfigHP(**c['cfg']) for c in corr], PRUEBA)):
        c['prueba'] = m
        c['domina'] = domina((m['error'], m['costo']), bp)
        print(c['global_'], c['r4'], round(m['error'], 4), round(m['costo'], 3), m['aciertos'], c['domina'],
              [round(c['cfg'][k], 2) for k in NOMBRES])
    json.dump(dict(base=base, corridas=corr, lam=LAMBDA, mu=MU, sigma0=SIGMA0, generaciones=GENS),
              open(os.path.join(RAIZ, 'datos', 'cmaes.json'), 'w'))
    print(f'total {time.time() - t0:.0f}s')
