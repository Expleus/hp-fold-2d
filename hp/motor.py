"""Motor HP 2D: rejilla, A* parametrizado (con traza opcional) y enumeración exacta.

Es el motor de Sprint_3.ipynb generalizado a grados de hidrofobicidad μ ∈ [0, 1]:
con μ ∈ {0, 1} (H = 1, P = 0) reproduce exactamente sus energías y nodos
(lo comprueba tools/verificar_motor.py sobre las 90 secuencias del banco).
"""
import heapq
import math
from collections import namedtuple

# Norte, Este, Sur, Oeste. 'L' gira a la izquierda (o − 1), 'R' a la derecha (o + 1).
ORIENTACIONES = [(0, 1), (1, 0), (0, -1), (-1, 0)]

ConfigHP = namedtuple('ConfigHP', ['a_b', 'a_p', 'c', 'a_g', 'm3', 'w', 'global_', 'r4'])
CONFIG_ACTUAL = ConfigHP(2.0, 2.0, 2.0, 1.0, 1.0, 1.0, True, 2)
NOMBRES = ('a_b', 'a_p', 'c', 'a_g', 'm3', 'w')
LIMITES = ((0, 3), (0, 3), (0, 4), (0, 1.5), (0.5, 2), (0.5, 2))

Resultado = namedtuple('Resultado', ['movs', 'energia', 'nodos', 'estado'])

MOTIVOS = {
    'ok': 'Aceptada',
    'simetria': 'R1 · simetría',
    'colision': 'R2 · colisión',
    'esteril': 'R4 · motivo estéril',
    'callejon': 'R3 · callejón sin salida',
}


def grados_crisp(sec):
    """H → 1, P → 0: el modelo HP clásico como caso particular del difuso."""
    return [1.0 if ch == 'H' else 0.0 for ch in sec]


def comprobar_estabilidad(sec):
    """R0 clásica: True si la secuencia es INESTABLE (fracción de H < 0.3)."""
    return sec.count('H') / len(sec) < 0.3


def paridad(mu, desde=0):
    """Suma de grados en índices pares e impares (desde `desde` hasta el final)."""
    pares = sum(m for i, m in enumerate(mu) if i >= desde and i % 2 == 0)
    impares = sum(m for i, m in enumerate(mu) if i >= desde and i % 2 == 1)
    return pares, impares


def reconstruir_coordenadas(movs):
    """Movimientos relativos → coordenadas absolutas. Los dos primeros monómeros
    quedan fijos en (0, 0) y (0, 1), mirando al norte."""
    coords, o = [(0, 0), (0, 1)], 0
    for m in movs:
        if m == 'L':
            o = (o - 1) % 4
        elif m == 'R':
            o = (o + 1) % 4
        dx, dy = ORIENTACIONES[o]
        x, y = coords[-1]
        coords.append((x + dx, y + dy))
    return coords


def contactos(coords, mu=None, sec=None):
    """Pares (i, j) en contacto topológico: vecinos en la red pero no en la cadena.
    Si se da `mu` (o `sec`), solo los pares con μ_i·μ_j > 0."""
    if mu is None and sec is not None:
        mu = grados_crisp(sec)
    pos = {c: i for i, c in enumerate(coords)}
    pares = []
    for i, (x, y) in enumerate(coords):
        for dx, dy in ORIENTACIONES:
            j = pos.get((x + dx, y + dy))
            if j is not None and j > i + 1 and (mu is None or mu[i] * mu[j] > 0):
                pares.append((i, j))
    return pares


def energia(coords, mu, regla='min'):
    """Energía de una conformación: −Σ peso de cada contacto (−1 por contacto H–H)."""
    t = min if regla == 'min' else (lambda a, b: a * b)
    return -sum(t(mu[i], mu[j]) for i, j in contactos(coords, mu))


def es_valida(coords):
    """Camino autoevitante: ninguna celda repetida."""
    return len(set(coords)) == len(coords)


class RejillaHP:
    """Rejilla (2n+1)×(2n+1) aplanada: índice del monómero en cada celda, −1 si libre."""

    def __init__(self, n):
        self.n, self.lado = n, 2 * n + 1
        lado = self.lado
        self.celdas = [-1] * (lado * lado)
        self.desp = (lado, 1, -lado, -1)            # N, E, S, O (mismo orden que ORIENTACIONES)
        self.borde = [x in (0, lado - 1) or y in (0, lado - 1) for y in range(lado) for x in range(lado)]
        self.marca, self.sello = [0] * (lado * lado), 0
        self.origen = n * lado + n

    def coordenada(self, celda):
        y, x = divmod(celda, self.lado)
        return (x - self.n, y - self.n)


def espacio_suficiente(rej, inicio, umbral, region=None):
    """Flood fill: ¿hay al menos `umbral` celdas libres alcanzables desde `inicio`?
    Si se pasa una lista `region` y la respuesta es no, se llena con las celdas encerradas."""
    celdas, marca, borde, desp = rej.celdas, rej.marca, rej.borde, rej.desp
    rej.sello += 1
    marca[inicio] = rej.sello
    cola, libres, i = [inicio], 0, 0
    while i < len(cola):
        actual = cola[i]
        i += 1
        for d in desp:
            v = actual + d
            if marca[v] != rej.sello and celdas[v] == -1:
                marca[v] = rej.sello
                if borde[v]:
                    return True
                libres += 1
                if libres >= umbral:
                    return True
                cola.append(v)
    if region is not None:
        region.extend(rej.coordenada(c) for c in cola[1:])
    return False


def a_estrella(sec, cfg=CONFIG_ACTUAL, tope_nodos=None, mu=None, regla='min', traza=None, max_traza=600,
               conteo=None):
    """A* parametrizado sobre la rejilla.

    sec   : cadena de 'H'/'P' (solo para longitud si se da `mu`).
    mu    : grados de hidrofobicidad; por defecto H = 1, P = 0 (modelo clásico).
    regla : peso de un contacto: 'min' → min(μi, μj); 'producto' → μi·μj.
    traza : si es una lista, se llena con cada expansión (para el reproductor paso a paso).
    conteo: si es un dict, acumula cuántos hijos descarta cada regla (claves de MOTIVOS).
    Devuelve Resultado(movs, energia, nodos, estado) con estado 'ok', 'tope' o 'sin_solucion'.
    """
    n = len(sec) if mu is None else len(mu)
    mu = grados_crisp(sec) if mu is None else list(mu)
    if n <= 2:
        return Resultado('', 0, 0, 'ok')
    t = min if regla == 'min' else (lambda a, b: a * b)

    # Todo lo que depende solo de k (monómeros colocados) se calcula una vez.
    h_rest = [sum(mu[k:]) for k in range(n + 1)]
    cota_basica = [-cfg.a_b * h_rest[k] for k in range(n + 1)]
    if cfg.global_:
        p, q = paridad(mu)
        base_par = [-(cfg.a_p * min(p, q) + cfg.c)] * (n + 1)
    else:   # paridad solo de lo que falta colocar
        base_par = [-(cfg.a_p * min(paridad(mu, k)) + cfg.c) for k in range(n + 1)]
    umbral = [math.ceil(cfg.m3 * r) for r in range(n + 1)]
    h_ventana = [sum(mu[max(0, k - 4):k]) for k in range(n + 1)]

    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp

    def nuevos(celda, k):
        if mu[k] == 0:
            return 0
        return sum(t(mu[k], mu[celdas[celda + d]]) for d in desp if 0 <= celdas[celda + d] <= k - 2)

    h0 = max(cota_basica[2], base_par[2])
    # Nodo: (f, g, movs, celdas ocupadas, orientación, ya giró, h). movs desempata
    # igual que el motor original; h va al final y nunca participa en el orden.
    heap = [(cfg.w * h0, 0, '', (rej.origen, rej.origen + desp[0]), 0, False, h0)]
    nodos = 0
    while heap:
        f, g, movs, ocup, orient, giro, h = heapq.heappop(heap)
        k = len(ocup)
        if k == n:
            if traza is not None:
                traza.append(dict(movs=movs, g=g, h=h, f=f, final=True, frontera=len(heap), hijos=[]))
            return Resultado(movs, g, nodos, 'ok')
        nodos += 1
        if tope_nodos and nodos > tope_nodos:
            return Resultado(None, 0, nodos, 'tope')
        anotar = traza is not None and len(traza) < max_traza
        hijos = [] if anotar else None
        for i, x in enumerate(ocup):          # cargar el camino en la rejilla
            celdas[x] = i
        restantes = n - k - 1
        for paso, giro_rel in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:                                     # R1 simetría
                if anotar:
                    hijos.append(dict(paso=paso, motivo='simetria'))
                if conteo is not None:
                    conteo['simetria'] = conteo.get('simetria', 0) + 1
                continue
            o = (orient + giro_rel) & 3
            nueva = ocup[-1] + desp[o]
            if celdas[nueva] != -1:                                          # R2 colisión
                if anotar:
                    hijos.append(dict(paso=paso, motivo='colision'))
                if conteo is not None:
                    conteo['colision'] = conteo.get('colision', 0) + 1
                continue
            if paso != 'F' and movs and movs[-1] == paso and h_ventana[k + 1] < cfg.r4:
                if anotar:                                                   # R4 motivo estéril
                    hijos.append(dict(paso=paso, motivo='esteril'))
                if conteo is not None:
                    conteo['esteril'] = conteo.get('esteril', 0) + 1
                continue
            celdas[nueva] = k
            region = [] if anotar else None
            if restantes > 0 and not espacio_suficiente(rej, nueva, umbral[restantes], region):
                celdas[nueva] = -1                                           # R3 callejón
                if anotar:
                    hijos.append(dict(paso=paso, motivo='callejon', region=region,
                                      necesarias=umbral[restantes]))
                if conteo is not None:
                    conteo['callejon'] = conteo.get('callejon', 0) + 1
                continue
            g2 = g - nuevos(nueva, k)
            celdas[nueva] = -1
            h2 = max(cota_basica[k + 1], base_par[k + 1] - cfg.a_g * g2)
            f2 = g2 + cfg.w * h2
            if anotar:
                hijos.append(dict(paso=paso, motivo='ok', g=g2, h=h2, f=f2))
            heapq.heappush(heap, (f2, g2, movs + paso, ocup + (nueva,), o, giro or paso != 'F', h2))
        for x in ocup:
            celdas[x] = -1
        if anotar:
            traza.append(dict(movs=movs, g=g, h=h, f=f, final=False, frontera=len(heap), hijos=hijos,
                              cola=[(e[0], e[2]) for e in heapq.nsmallest(6, heap)]))
    return Resultado(None, 0, nodos, 'sin_solucion')


def optimo_exhaustivo(sec, mu=None, regla='min', limite=None):
    """Energía mínima exacta por DFS sobre todas las cadenas autoevitantes
    (solo poda por colisión y simetría). Devuelve (energía, movs, n.º de óptimos, hojas)."""
    n = len(sec) if mu is None else len(mu)
    mu = grados_crisp(sec) if mu is None else list(mu)
    t = min if regla == 'min' else (lambda a, b: a * b)
    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp
    celdas[rej.origen], celdas[rej.origen + desp[0]] = 0, 1
    mejor = [0.0, '', 0, 0]           # energía, movs, cuántas la alcanzan, hojas visitadas
    eps = 1e-9

    def dfs(k, ultima, orient, giro, g, movs):
        if k == n:
            mejor[3] += 1
            if g < mejor[0] - eps:
                mejor[0], mejor[1], mejor[2] = g, movs, 1
            elif abs(g - mejor[0]) <= eps:
                mejor[2] += 1
                if not mejor[1]:
                    mejor[1] = movs
            return
        if limite and mejor[3] >= limite:
            return
        for paso, giro_rel in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:
                continue
            o = (orient + giro_rel) & 3
            nueva = ultima + desp[o]
            if celdas[nueva] == -1:
                celdas[nueva] = k
                dg = 0
                if mu[k]:
                    dg = sum(t(mu[k], mu[celdas[nueva + d]]) for d in desp if 0 <= celdas[nueva + d] <= k - 2)
                dfs(k + 1, nueva, o, giro or paso != 'F', g - dg, movs + paso)
                celdas[nueva] = -1

    if n <= 2:
        return 0.0, '', 1, 1
    dfs(2, rej.origen + desp[0], 0, False, 0.0, '')
    return mejor[0], mejor[1], mejor[2], mejor[3]
