"""Extensión difusa: hidrofobicidad graduada y R0 como grado de pertenencia."""
import math

import numpy as np

from .motor import RejillaHP

# Escala de hidropatía de Kyte & Doolittle (1982), código de una letra.
KYTE_DOOLITTLE = {
    'I': 4.5, 'V': 4.2, 'L': 3.8, 'F': 2.8, 'C': 2.5, 'M': 1.9, 'A': 1.8, 'G': -0.4, 'T': -0.7, 'S': -0.8,
    'W': -0.9, 'Y': -1.3, 'P': -1.6, 'H': -3.2, 'E': -3.5, 'Q': -3.5, 'D': -3.5, 'N': -3.5, 'K': -3.9, 'R': -4.5,
}
NOMBRES_AA = {
    'A': 'alanina', 'R': 'arginina', 'N': 'asparagina', 'D': 'aspartato', 'C': 'cisteína', 'Q': 'glutamina',
    'E': 'glutamato', 'G': 'glicina', 'H': 'histidina', 'I': 'isoleucina', 'L': 'leucina', 'K': 'lisina',
    'M': 'metionina', 'F': 'fenilalanina', 'P': 'prolina', 'S': 'serina', 'T': 'treonina', 'W': 'triptófano',
    'Y': 'tirosina', 'V': 'valina',
}
# Péptidos cortos reales (secuencia en código de una letra).
PEPTIDOS = {
    'Chignolina (10)': 'GYDPETGTWG',
    'Trp-cage TC5b (20)': 'NLYIQWLKDGGPSSGRPPPS',
}


def grados_kd(aa):
    """Grado μ ∈ [0, 1] de cada residuo: la escala KD reescalada linealmente de [−4.5, 4.5] a [0, 1]."""
    return [round((KYTE_DOOLITTLE[c] + 4.5) / 9, 3) for c in aa]


def a_hp(mu, umbral=0.5):
    """Defuzzificación: H si μ ≥ umbral (lo que hace el modelo HP clásico)."""
    return ''.join('H' if m >= umbral else 'P' for m in mu)


def fraccion_h(mu):
    """Fracción hidrofóbica. Para grados es el «sigma-count» relativo: Σμ / n."""
    return sum(mu) / len(mu)


def cota_paridad(mu):
    """Cota de paridad rederivada para grados: |E| ≤ 2·min(Σμ pares, Σμ impares) + μ de los extremos.
    Devuelve (cota fina, cota simple = 2·min + 2)."""
    n = len(mu)
    pares = sum(mu[i] for i in range(0, n, 2))
    impares = sum(mu[i] for i in range(1, n, 2))
    ext_par = sum(mu[i] for i in {0, n - 1} if i % 2 == 0)
    ext_impar = sum(mu[i] for i in {0, n - 1} if i % 2 == 1)
    fina = min(2 * pares + ext_par, 2 * impares + ext_impar)
    return fina, 2 * min(pares, impares) + 2


# ---------- R0 difusa ----------

def rampa(f, a, b):
    """Pertenencia a «plegable»: 0 por debajo de a, 1 por encima de b, lineal en medio."""
    f = np.asarray(f, dtype=float)
    if b <= a:
        return (f >= a).astype(float)
    return np.clip((f - a) / (b - a), 0.0, 1.0)


def tabla_r0(grupos, contactos_min):
    """Por cada (n, k): fracción f = k/n, cuántas secuencias hay y qué proporción pliega de verdad
    (energía óptima ≤ −contactos_min)."""
    filas = []
    for g in grupos:
        total = sum(g['E'].values())
        pliegan = sum(c for e, c in g['E'].items() if int(e) <= -contactos_min)
        filas.append(dict(n=g['n'], k=g['k'], f=g['k'] / g['n'], total=total, pliegan=pliegan,
                          prop=pliegan / total))
    return filas


def ajustar_rampa(filas, paso=0.005):
    """Rampa (a, b) que minimiza el error cuadrático por secuencia (puntaje de Brier) frente a los
    óptimos exactos. Búsqueda en rejilla: es pequeña y no depende de ningún optimizador."""
    f = np.array([r['f'] for r in filas])
    p = np.array([r['prop'] for r in filas])
    w = np.array([r['total'] for r in filas], dtype=float)
    cand = np.arange(0.0, 0.7 + 1e-9, paso)
    A, B = np.meshgrid(cand, cand, indexing='ij')
    ok = B > A
    A, B = A[ok], B[ok]
    pred = np.clip((f[None, :] - A[:, None]) / (B - A)[:, None], 0, 1)
    costo = ((pred - p[None, :]) ** 2 * w[None, :]).sum(1) / w.sum()
    i = int(np.argmin(costo))
    return float(A[i]), float(B[i]), float(costo[i])


def brier_escalon(filas, umbral=0.3):
    """El mismo puntaje para la R0 clásica (escalón en 0.3), para comparar."""
    f = np.array([r['f'] for r in filas])
    p = np.array([r['prop'] for r in filas])
    w = np.array([r['total'] for r in filas], dtype=float)
    pred = (f >= umbral).astype(float)
    return float(((pred - p) ** 2 * w).sum() / w.sum())


def presupuesto(grado, minimo, maximo):
    """Nodos permitidos según el grado: interpolación geométrica (cada décima de grado multiplica
    el presupuesto por el mismo factor), porque el esfuerzo de A* crece exponencialmente."""
    return int(round(minimo * (maximo / minimo) ** float(np.clip(grado, 0, 1))))


def veredicto(grado):
    if grado >= 0.8:
        return 'plegable', 'Presupuesto completo: lo más probable es que tenga un núcleo hidrofóbico.'
    if grado >= 0.3:
        return 'dudosa', 'Presupuesto parcial: puede plegar, pero con pocos contactos.'
    return 'poco plegable', ('Presupuesto mínimo. Advertencia: la conformación devuelta '
                             'probablemente no sea relevante.')


# ---------- Paisaje de energías ----------

def energias_todas(mu, regla='min', limite=400_000):
    """Energía de TODAS las conformaciones (salvo simetría). Para n ≤ 13 aprox."""
    n = len(mu)
    t = min if regla == 'min' else (lambda a, b: a * b)
    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp
    celdas[rej.origen], celdas[rej.origen + desp[0]] = 0, 1
    salida = []

    def dfs(k, ultima, o, giro, g):
        if k == n:
            salida.append(g)
            return
        if len(salida) >= limite:
            return
        for paso, dr in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:
                continue
            oo = (o + dr) & 3
            nueva = ultima + desp[oo]
            if celdas[nueva] == -1:
                celdas[nueva] = k
                dg = 0.0
                if mu[k]:
                    dg = sum(t(mu[k], mu[celdas[nueva + d]]) for d in desp if 0 <= celdas[nueva + d] <= k - 2)
                dfs(k + 1, nueva, oo, giro or paso != 'F', g - dg)
                celdas[nueva] = -1

    dfs(2, rej.origen + desp[0], 0, False, 0.0)
    return salida


def conformaciones_posibles(n):
    """Cuántas formas distintas tiene una cadena de n monómeros (sin contar giros ni espejos):
    a partir del número de caminos autoevitantes c_{n−1} (OEIS A001411)."""
    c = CAMINOS_AUTOEVITANTES
    if n - 1 >= len(c):
        return None
    return (c[n - 1] // 4 + 1) // 2


# c_N: caminos autoevitantes de N pasos en la red cuadrada (OEIS A001411), N = 0..30.
CAMINOS_AUTOEVITANTES = [
    1, 4, 12, 36, 100, 284, 780, 2172, 5916, 16268, 44100, 120292, 324932, 881500, 2374444, 6416596,
    17245332, 46466676, 124658732, 335116620, 897697164, 2408806028, 6444560484, 17266613812,
    46146397316, 123481354908, 329712786220, 881317491628, 2351378582244, 6279396229332, 16741957935348,
]


def formato_grande(x):
    """Número grande en palabras cortas (miles, millones, …)."""
    if x < 1e4:
        return f'{x:,.0f}'.replace(',', ' ')
    for valor, nombre in ((1e12, 'billones'), (1e9, 'mil millones'), (1e6, 'millones'), (1e3, 'mil')):
        if x >= valor:
            return f'{x / valor:.1f} {nombre}'.replace('.', ',')
    return str(x)


def log10_seguro(x):
    return math.log10(max(x, 1))
