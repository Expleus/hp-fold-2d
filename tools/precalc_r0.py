"""Óptimo exacto de TODAS las secuencias HP con n = 10..14 (31 744 secuencias), para
ajustar la rampa de la R0 difusa. Enumera una vez las conformaciones de cada longitud,
se queda con los conjuntos de contactos distintos y evalúa todas las secuencias con numpy."""
import sys, os, json, time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from hp.motor import RejillaHP

def conjuntos_de_contactos(n):
    pares = [(i, j) for i in range(n) for j in range(i + 3, n) if (j - i) % 2 == 1]
    idx = {p: b for b, p in enumerate(pares)}
    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp
    celdas[rej.origen], celdas[rej.origen + desp[0]] = 0, 1
    vistos, hojas = set(), [0]
    def dfs(k, ultima, o, giro, mask):
        if k == n:
            hojas[0] += 1; vistos.add(mask); return
        for paso, dr in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:
                continue
            oo = (o + dr) & 3
            nueva = ultima + desp[oo]
            if celdas[nueva] == -1:
                celdas[nueva] = k
                m = mask
                for d in desp:
                    j = celdas[nueva + d]
                    if 0 <= j <= k - 3:
                        m |= 1 << idx[(j, k)]
                dfs(k + 1, nueva, oo, giro or paso != 'F', m)
                celdas[nueva] = -1
    dfs(2, rej.origen + desp[0], 0, False, 0)
    # quitar los conjuntos contenidos en otro (nunca dan el mínimo: los pesos son ≥ 0)
    masks = sorted(vistos, key=lambda m: -bin(m).count('1'))
    maximales = []
    for m in masks:
        if not any(m & M == m for M in maximales):
            maximales.append(m)
    A = np.array([[(m >> b) & 1 for b in range(len(pares))] for m in maximales], dtype=np.float32)
    return pares, A, hojas[0]

if __name__ == '__main__':
    t0 = time.time()
    salida = dict(grupos=[], hojas={})
    for n in range(10, 15):
        pares, A, hojas = conjuntos_de_contactos(n)
        salida['hojas'][n] = hojas
        S = np.arange(2 ** n)
        H = ((S[:, None] >> np.arange(n)[None, :]) & 1).astype(np.float32)     # bit i = monómero i es H
        W = np.stack([H[:, i] * H[:, j] for i, j in pares], axis=1)
        E = np.empty(len(S), dtype=np.int32)
        for a in range(0, len(S), 2048):
            E[a:a + 2048] = -(W[a:a + 2048] @ A.T).max(axis=1)
        nh = H.sum(1).astype(int)
        for k in range(n + 1):
            e, c = np.unique(E[nh == k], return_counts=True)
            salida['grupos'].append(dict(n=n, k=k, E={int(x): int(y) for x, y in zip(e, c)}))
        print(n, 'hojas', hojas, 'conjuntos maximales', len(A), f'{time.time() - t0:.0f}s', flush=True)
    json.dump(salida, open(os.path.join(RAIZ, 'datos', 'r0.json'), 'w'))
