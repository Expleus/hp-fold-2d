# Copia literal del motor de Sprint_3.ipynb (celdas 6, 7, 13 y 14), solo para verificar.
from collections import namedtuple

# Secuencias que el motor de la celda siguiente pliega y dibuja.
secuencias = ["HPPHHPHPPPH","PPPHPHPPP","HHHHH","HPHPPHPPH"]

# Parámetros del motor A*. Por defecto, los valores actuales: la línea base que CMA-ES intenta superar.
ConfigHP = namedtuple('ConfigHP', ['a_b', 'a_p', 'c', 'a_g', 'm3', 'w', 'global_', 'r4'])
CONFIG_ACTUAL = ConfigHP(
    a_b=2.0,        # contactos que se le prometen a cada H sin colocar (cota básica)
    a_p=2.0,        # factor de la cota de paridad
    c=2.0,          # término constante de la cota de paridad
    a_g=1.0,        # cuánto de la energía ya lograda se descuenta en la cota de paridad
    m3=1.0,         # callejones sin salida: exige ceil(m3 · restantes) celdas libres alcanzables
    w=1.0,          # peso de la heurística en f = g + w·h
    global_=True,   # paridad de toda la cadena (True) o solo de lo que falta colocar (False)
    r4=2,           # poda un giro en U con menos de r4 H en sus 4 monómeros; 0 apaga la regla
)

import math, heapq

# Movimientos relativos: 'F' (adelante), 'L' (izquierda), 'R' (derecha).
ORIENTACIONES = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Norte, Este, Sur, Oeste


def comprobar_estabilidad(secuencia):
  # Si la secuencia no tiene suficientes monómeros H, no podrá darse el colapso
  # hidrofóbico (no puede plegarse)
  hs = secuencia.count("H")

  if hs/len(secuencia) < 0.3:
    return True
  else:
    return False

def paridad_h(secuencia):
  # Obtiene la cantidad de H pares e impares
  hs = secuencia.count("H")
  even = []
  odd = []

  for i in range(len(secuencia)):
    if secuencia[i] == "H":
      if i % 2 == 0:
        even.append(i)
      else:
        odd.append(i)

  return [len(even),len(odd)]

def reconstruir_coordenadas(secuencia_movs):
    """
    Convierte una secuencia de movimientos relativos ('F', 'L', 'R')
    en una lista de coordenadas absolutas 2D partiendo desde el origen.
    """
    coordenadas = [(0, 0), (0, 1)]  # El primer paso se fija hacia arriba
    orientacion_idx = 0  # 0: Arriba, 1: Derecha, 2: Abajo, 3: Izquierda

    for mov in secuencia_movs:
        if mov == 'L':
            orientacion_idx = (orientacion_idx - 1) % 4
        elif mov == 'R':
            orientacion_idx = (orientacion_idx + 1) % 4
        # Si es 'F', conserva la orientacion_idx actual

        dx, dy = ORIENTACIONES[orientacion_idx]
        ultima_x, ultima_y = coordenadas[-1]
        coordenadas.append((ultima_x + dx, ultima_y + dy))

    return coordenadas

def mostrar_red(secuencia, conformacion, destacar_inicio=True):
    """
    Imprime en consola una representación visual de la proteína en la red 2D.
    """
    xs = [pos[0] for pos in conformacion]
    ys = [pos[1] for pos in conformacion]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    ancho = max_x - min_x + 1
    alto = max_y - min_y + 1

    red = [[" . " for _ in range(ancho)] for _ in range(alto)]

    for i, (x, y) in enumerate(conformacion):
        r = max_y - y
        c = x - min_x

        simbolo = secuencia[i]

        if i == 0 and destacar_inicio:
            simbolo_f = f"*{simbolo}*"
        else:
            simbolo_f = f" {simbolo} "

        red[r][c] = simbolo_f

    for fila in red:
        print("".join(fila))


# --- Motor rápido: rejilla fija y energía incremental (sección 1) ---
class RejillaHP:
    """Rejilla (2n+1)x(2n+1) aplanada: índice del monómero en cada celda, -1 si libre."""
    def __init__(self, n):
        self.n, self.lado = n, 2 * n + 1
        lado = self.lado
        self.celdas = [-1] * (lado * lado)
        self.desp = (lado, 1, -lado, -1)          # N, E, S, O (mismo orden que ORIENTACIONES)
        self.borde = [x in (0, lado - 1) or y in (0, lado - 1) for y in range(lado) for x in range(lado)]
        self.marca, self.sello = [0] * (lado * lado), 0   # visitados del flood fill sin tener que limpiarlos
        self.origen = n * lado + n

    def coordenada(self, celda):
        y, x = divmod(celda, self.lado)
        return (x - self.n, y - self.n)


def contactos_nuevos(rej, celda, k, es_h):
    """Contactos H-H del monómero k recién puesto en `celda` (j <= k-2 excluye al vecino de cadena)."""
    if not es_h[k]:
        return 0
    return sum(1 for d in rej.desp if 0 <= rej.celdas[celda + d] <= k - 2 and es_h[rej.celdas[celda + d]])


def espacio_suficiente(rej, inicio, umbral):
    """Flood fill: ¿hay al menos `umbral` celdas libres alcanzables desde `inicio`?"""
    celdas, marca, borde, desp = rej.celdas, rej.marca, rej.borde, rej.desp
    rej.sello += 1
    marca[inicio] = rej.sello
    cola, libres, i = [inicio], 0, 0
    while i < len(cola):
        actual = cola[i]; i += 1
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
    return False


# --- Motor parametrizado (sección 2) ---
Resultado = namedtuple('Resultado', ['movs', 'energia', 'nodos', 'estado'])


def a_estrella_param(sec, cfg, tope_nodos=None):
    """A* parametrizado. estado: 'ok', 'tope' (demasiados nodos) o 'sin_solucion'."""
    n = len(sec)
    es_h = [ch == 'H' for ch in sec]
    # Todo lo que depende solo de k (monómeros colocados) se calcula una vez.
    h_rest = [sec[k:].count('H') for k in range(n + 1)]
    cota_basica = [-cfg.a_b * h_rest[k] for k in range(n + 1)]
    if cfg.global_:
        p, q = paridad_h(sec)
        base_par = [-(cfg.a_p * min(p, q) + cfg.c)] * (n + 1)
    else:   # paridad solo de lo que falta colocar (índice absoluto: fija el color de la celda)
        base_par = [-(cfg.a_p * min(sum(es_h[i] for i in range(k, n) if i % 2 == 0),
                                    sum(es_h[i] for i in range(k, n) if i % 2 == 1)) + cfg.c)
                    for k in range(n + 1)]
    umbral = [math.ceil(cfg.m3 * r) for r in range(n + 1)]
    h_ventana = [sec[max(0, k - 4):k].count('H') for k in range(n + 1)]

    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp
    # Nodo: (f, g, movs, celdas ocupadas, orientación, ya giró). movs como str
    # desempata igual que la lista del motor original.
    heap = [(cfg.w * max(cota_basica[2], base_par[2]), 0, '', (rej.origen, rej.origen + desp[0]), 0, False)]
    nodos = 0
    while heap:
        _, g, movs, ocup, orient, giro = heapq.heappop(heap)
        k = len(ocup)
        if k == n:
            return Resultado(movs, g, nodos, 'ok')
        nodos += 1
        if tope_nodos and nodos > tope_nodos:
            return Resultado(None, 0, nodos, 'tope')
        for i, x in enumerate(ocup):          # cargar el camino en la rejilla
            celdas[x] = i
        restantes = n - k - 1
        for paso, giro_rel in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:                                     # simetría
                continue
            o = (orient + giro_rel) & 3
            nueva = ocup[-1] + desp[o]
            if celdas[nueva] != -1:                                          # colisión
                continue
            if paso != 'F' and movs and movs[-1] == paso and h_ventana[k + 1] < cfg.r4:
                continue                                                     # motivo estéril
            celdas[nueva] = k
            if restantes > 0 and not espacio_suficiente(rej, nueva, umbral[restantes]):
                celdas[nueva] = -1                                           # callejón
                continue
            g2 = g - contactos_nuevos(rej, nueva, k, es_h)
            celdas[nueva] = -1
            h2 = max(cota_basica[k + 1], base_par[k + 1] - cfg.a_g * g2)
            heapq.heappush(heap, (g2 + cfg.w * h2, g2, movs + paso, ocup + (nueva,), o, giro or paso != 'F'))
        for x in ocup:
            celdas[x] = -1
    return Resultado(None, 0, nodos, 'sin_solucion')


def a_estrella_hp(secuencia_hp, cfg=None):
    """Misma interfaz que la primera versión del motor: (movimientos, coordenadas, energía).
    Pliega con el motor parametrizado y la configuración de la celda de parámetros."""
    n = len(secuencia_hp)
    if n <= 2:
        return [], [(0, 0)] if n == 1 else [(0, 0), (0, 1)], 0
    if comprobar_estabilidad(secuencia_hp):                     # R0: no se pliega
        return "Secuencia no estable", [(0, i) for i in range(n)], 0
    r = a_estrella_param(secuencia_hp, cfg or CONFIG_ACTUAL)
    if r.estado != 'ok':
        return None, None, 0
    return list(r.movs), reconstruir_coordenadas(r.movs), r.energia




BANCO = [
    ('PPPPPHHHPHHHPP', -2, 'C', 'E', 0),
    ('PHHHHHPPPHP', -2, 'C', 'E', 0),
    ('HPPPPPPHHPPH', -3, 'C', 'P', 0),
    ('HPHHPPHHHHH', -4, 'C', 'P', 0),
    ('HHHHPHPHHH', -4, 'C', 'P', 0),
    ('PHPHHHHHPPPH', -3, 'C', 'P', 0),
    ('PPHHPHHPHHHHP', -4, 'C', 'P', 0),
    ('HPHHPHHHHPHHPP', -5, 'C', 'P', 0),
    ('PHPHPPHHPPH', -4, 'C', 'E', 0),
    ('PPHHPHHPPH', -3, 'C', 'P', 0),
    ('PHPPPHHHPP', -1, 'C', 'E', 1),
    ('HHHPHHPHHPHPP', -4, 'C', 'E', 0),
    ('HHHPPHPPPPP', -2, 'C', 'E', 1),
    ('PHHPHPHPHHH', -4, 'C', 'P', 0),
    ('HHHHPHHPHPPPP', -3, 'C', 'P', 0),
    ('HHPPHHPHPHP', -4, 'C', 'P', 0),
    ('HPHHHHHHHP', -3, 'C', 'E', 0),
    ('PHPPHHHHPHH', -4, 'C', 'E', 0),
    ('PPPPHPHHHHHH', -3, 'C', 'E', 0),
    ('PHPPPHHPHHPHH', -4, 'C', 'E', 0),
    ('HPHHHHPHHH', -4, 'C', 'P', 0),
    ('HHHPPPPPHHH', -2, 'C', 'E', 0),
    ('HHPHHHPHPH', -4, 'C', 'E', 0),
    ('PHHHHPPPPHP', -2, 'C', 'P', 0),
    ('PHPHHPHHPHPPPP', -3, 'C', 'E', 0),
    ('HPHPHHHPPP', -2, 'C', 'P', 0),
    ('PHHPPHPHHHHHHH', -6, 'C', 'P', 0),
    ('PHHPHHPHHHPPHH', -6, 'C', 'P', 0),
    ('HPPPPHHPHHPPPP', -3, 'C', 'E', 0),
    ('HPPHPPHHPH', -4, 'C', 'E', 0),
    ('HPPHHPPPPHH', -3, 'C', 'E', 0),
    ('PHHHHPHHHHH', -4, 'C', 'E', 0),
    ('PHPHHPHPHPHHPH', -5, 'C', 'P', 0),
    ('HHHHHPPPPP', -1, 'C', 'P', 0),
    ('HHPHHHPHHP', -4, 'C', 'P', 0),
    ('PHPHHHHPPPHHH', -5, 'C', 'P', 0),
    ('PPPHHHHPPPPP', -1, 'C', 'P', 0),
    ('HHPHPHHPPH', -4, 'C', 'P', 0),
    ('HHHHPHHHHPH', -5, 'C', 'P', 0),
    ('HHPHHPPHHHPP', -4, 'C', 'E', 0),
    ('PHPHHPHPHPP', -3, 'C', 'E', 1),
    ('PHPPHHPPHHH', -4, 'C', 'P', 0),
    ('PHHPHPHPHHPHP', -4, 'C', 'E', 0),
    ('HHPHPPPPHH', -3, 'C', 'P', 0),
    ('PHHPHPPHHHHHHH', -6, 'C', 'P', 0),
    ('PHHPHHHPPHPH', -4, 'C', 'E', 1),
    ('HPHHHHPHHPHHP', -5, 'C', 'E', 0),
    ('HHHHPPHHHPH', -4, 'C', 'E', 0),
    ('PHHPHPPPPPPHPH', -3, 'C', 'P', 0),
    ('PPHPHPHHHHPHP', -4, 'C', 'E', 0),
    ('HPPPHHPHPH', -3, 'C', 'E', 1),
    ('PHHHHPHHHH', -4, 'C', 'E', 0),
    ('PHPHPHPHHHHP', -4, 'C', 'P', 0),
    ('PHPPHPHHPHP', -3, 'C', 'E', 0),
    ('HPHPPHPPHHHPHP', -4, 'C', 'P', 0),
    ('PHHPPPHHPPHP', -3, 'C', 'P', 0),
    ('HPHPHPHPPHPPPH', -4, 'C', 'E', 0),
    ('PPPHHHPHPHH', -3, 'C', 'P', 0),
    ('PPPHHHHHHPP', -2, 'C', 'E', 0),
    ('PPHHHPHPPH', -3, 'C', 'E', 0),
    ('HPHHHPHHPPHHHHPPPPPP', -6, 'L', 'E', 0),
    ('HHPHPHPHHHHPPPPPPHPHPP', -7, 'L', 'E', 0),
    ('HPPPHPHPPHPPPHHHPPPHPH', -7, 'L', 'P', 0),
    ('HHHHPPHPHPHPHHPPPHPHPH', -10, 'L', 'E', 0),
    ('HHHPPPPPHPPHPHPPHPHHPP', -7, 'L', 'E', 0),
    ('HHHHPPPHHHPHHHPHHHH', -9, 'L', 'P', 0),
    ('PHPHPHHHHPHPPHPPHPPPPPP', -7, 'L', 'E', 0),
    ('PHPHHPHHPHPPPPPHPPPHH', -6, 'L', 'P', 0),
    ('PHHPHHHHHPPPHHHHHPHH', -9, 'L', 'E', 0),
    ('PPPHHHPPHPHPHHHPPHPPPP', -7, 'L', 'P', 0),
    ('HHPHPHPPPHHHPPPHPPHPH', -8, 'L', 'P', 0),
    ('HHPHPHHHHHPPPPPHPHHHPPHP', -10, 'L', 'P', 0),
    ('HHPPPHPPPHPHPPPHPPPP', -3, 'L', 'E', 0),
    ('HHHHPHPPPPPHPHHHHPPHPHHP', -10, 'L', 'E', 1),
    ('HHPHHHHHHHHPPHHHHHP', -10, 'L', 'P', 0),
    ('HHPPHHPHPPPPPHHPPPPPPHP', -6, 'L', 'P', 0),
    ('PPHHPHPHHHHHPHPHPH', -6, 'L', 'P', 0),
    ('PHPHPHPHHPPPHPHPHHP', -6, 'L', 'E', 1),
    ('HHPHPPPHPHHHHHHPHP', -8, 'L', 'P', 0),
    ('PPHHPPHHPHPPHHPPHHP', -7, 'L', 'E', 0),
    ('HPPHHPHPPHPPHHPPPP', -5, 'L', 'E', 1),
    ('HPPPHHHPHHHHPHPPHHHH', -10, 'L', 'E', 0),
    ('PHHPHPHHPHHHPPHHPPP', -6, 'L', 'P', 0),
    ('PHHPHHHPPHHPHPHPHHPPPPP', -8, 'L', 'E', 0),
    ('PPHPPHHHPHPPPPPPPPPH', -4, 'L', 'E', 0),
    ('HHHHPPHPHPPHHHPPHHP', -9, 'L', 'P', 0),
    ('PHHPHHHHPPHHHHHPPPH', -8, 'L', 'P', 0),
    ('PHPHPPPPHPHPPPHHPHPHPPP', -6, 'L', 'E', 0),
    ('HPHHPPHHPPHHPPHHPPPH', -8, 'L', 'P', 0),
    ('HPPHPPHHPHHHHHHPPHHHHPP', -11, 'L', 'P', 0),
]



import random, time
def optimo_exhaustivo(sec):
    """Energía mínima exacta: DFS por todas las cadenas auto-evitantes.
    Solo poda por colisión y simetría (el motivo estéril podría descartar el óptimo)."""
    n, es_h = len(sec), [ch == 'H' for ch in sec]
    rej = RejillaHP(n)
    celdas, desp = rej.celdas, rej.desp
    celdas[rej.origen], celdas[rej.origen + desp[0]] = 0, 1
    mejor = [0]

    def dfs(k, ultima, orient, giro, g):
        if k == n:
            mejor[0] = min(mejor[0], g)
            return
        for paso, giro_rel in (('F', 0), ('L', 3), ('R', 1)):
            if paso == 'R' and not giro:
                continue
            o = (orient + giro_rel) & 3
            nueva = ultima + desp[o]
            if celdas[nueva] == -1:
                celdas[nueva] = k
                dfs(k + 1, nueva, o, giro or paso != 'F', g - contactos_nuevos(rej, nueva, k, es_h))
                celdas[nueva] = -1

    dfs(2, rej.origen + desp[0], 0, False, 0)
    return mejor[0]


