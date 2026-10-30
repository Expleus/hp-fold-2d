"""Dibujo de conformaciones como SVG (sin dependencias: se inserta con st.markdown)."""
from html import escape

from .motor import ORIENTACIONES, contactos, grados_crisp, reconstruir_coordenadas

# Paleta (tinta y superficies neutras; naranja = hidrofóbico, azul = resaltado).
NARANJA = '#eb6834'
AZUL = '#2a78d6'
ROJO = '#d03b3b'
TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
TENUE = '#898781'
RED = '#d9d8d2'
CADENA = '#b9b7ae'
AJEDREZ = '#efede7'


def _mezcla(mu):
    """Blanco → naranja según el grado de hidrofobicidad."""
    r0, g0, b0 = 255, 255, 255
    r1, g1, b1 = 0xeb, 0x68, 0x34
    return '#%02x%02x%02x' % (round(r0 + (r1 - r0) * mu), round(g0 + (g1 - g0) * mu), round(b0 + (b1 - b0) * mu))


def siguiente_celda(movs, paso):
    """Celda a la que iría el siguiente monómero con el paso F, L o R."""
    coords = reconstruir_coordenadas(movs)
    o = 0
    for m in movs:
        o = (o - 1) % 4 if m == 'L' else (o + 1) % 4 if m == 'R' else o
    o = (o - 1) % 4 if paso == 'L' else (o + 1) % 4 if paso == 'R' else o
    (x, y), (dx, dy) = coords[-1], ORIENTACIONES[o]
    return (x + dx, y + dy)


def conformacion(sec, movs='', *, mu=None, regla='min', celda=46, ancho_max=None, indices=True,
                 contactos_visibles=True, ajedrez=False, resaltar=(), candidatos=(), region=(),
                 fantasma=None, marcas=(), titulo=None, marco=None):
    """SVG de una cadena (completa o parcial) sobre la red cuadrada.

    sec        : secuencia 'H'/'P' (si hay `mu`, solo se usa para la etiqueta).
    movs       : movimientos relativos ya hechos; se dibujan len(movs) + 2 monómeros.
    mu         : grados de hidrofobicidad (color graduado y grosor de los contactos).
    candidatos : [{paso, motivo, f?}] posibles siguientes pasos (A* paso a paso).
    region     : celdas encerradas (regla R3).
    fantasma   : celda (x, y) a marcar como colisión (círculo rojo con ×).
    marcas     : celdas (x, y) libres donde podría formarse un contacto (círculo naranja punteado).
    marco      : (xmin, xmax, ymin, ymax) fijo, para que varias figuras compartan escala.
    """
    coords = reconstruir_coordenadas(movs)
    k = len(coords)
    mu_total = list(mu) if mu is not None else grados_crisp(sec)
    mu_vis = mu_total[:k]
    sec_vis = sec[:k] if sec else ''

    extra = [siguiente_celda(movs, c['paso']) for c in candidatos] + list(region) + list(marcas)
    if fantasma:
        extra.append(fantasma)
    xs = [x for x, _ in coords + extra]
    ys = [y for _, y in coords + extra]
    if marco:
        x0, x1, y0, y1 = marco
    else:
        x0, x1, y0, y1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    s = celda
    W, H = (x1 - x0) * s + s, (y1 - y0) * s + s
    alto_titulo = 26 if titulo else 0

    def px(x, y):
        return (x - x0) * s + s / 2, (y1 - y) * s + s / 2 + alto_titulo

    partes = []
    if titulo:
        partes.append(f'<text x="{W / 2}" y="17" text-anchor="middle" font-size="14" '
                      f'font-weight="600" fill="{TINTA_2}">{escape(titulo)}</text>')
    # Tablero de ajedrez: las casillas alternan color igual que la paridad del índice.
    if ajedrez:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                if (x + y) % 2 == 0:
                    cx, cy = px(x, y)
                    partes.append(f'<rect x="{cx - s / 2}" y="{cy - s / 2}" width="{s}" height="{s}" '
                                  f'fill="{AJEDREZ}"/>')
    # Puntos de la red.
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            cx, cy = px(x, y)
            partes.append(f'<circle cx="{cx}" cy="{cy}" r="2" fill="{RED}"/>')
    # Región encerrada (R3).
    for x, y in region:
        cx, cy = px(x, y)
        partes.append(f'<rect x="{cx - s / 2 + 3}" y="{cy - s / 2 + 3}" width="{s - 6}" height="{s - 6}" '
                      f'rx="6" fill="{ROJO}" fill-opacity="0.10" stroke="{ROJO}" stroke-opacity="0.55" '
                      f'stroke-dasharray="4 3"/>')
    # Casillas donde cabría un contacto.
    for x, y in marcas:
        cx, cy = px(x, y)
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="{s * 0.3}" fill="{NARANJA}" fill-opacity="0.08" '
                      f'stroke="{NARANJA}" stroke-width="1.8" stroke-dasharray="4 3"/>')
    # Contactos H–H (líneas punteadas).
    if contactos_visibles and k >= 2:
        t = min if regla == 'min' else (lambda a, b: a * b)
        for i, j in contactos(coords, mu_vis):
            peso = t(mu_vis[i], mu_vis[j])
            (ax, ay), (bx, by) = px(*coords[i]), px(*coords[j])
            partes.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{NARANJA}" '
                          f'stroke-width="{1.2 + 2.3 * peso:.2f}" stroke-dasharray="5 4" stroke-linecap="round"/>')
    # Esqueleto de la cadena.
    if k >= 2:
        pts = ' '.join('%g,%g' % px(x, y) for x, y in coords)
        partes.append(f'<polyline points="{pts}" fill="none" stroke="{CADENA}" stroke-width="{s * 0.12:.1f}" '
                      f'stroke-linecap="round" stroke-linejoin="round"/>')
    # Candidatos del siguiente paso.
    if candidatos:
        (lx, ly) = px(*coords[-1])
        for c in candidatos:
            x, y = siguiente_celda(movs, c['paso'])
            cx, cy = px(x, y)
            r = s * 0.3
            if c['motivo'] == 'ok':
                partes.append(f'<line x1="{lx}" y1="{ly}" x2="{cx}" y2="{cy}" stroke="{AZUL}" stroke-width="2" '
                              f'stroke-dasharray="3 3"/>')
                partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#ffffff" stroke="{AZUL}" '
                              f'stroke-width="2" stroke-dasharray="4 3"/>')
                etiqueta = c.get('texto') or (c['paso'] if c.get('f') is None else f"{c['paso']} · f={c['f']:.1f}")
                partes.append(f'<text x="{cx}" y="{cy + r + 13}" text-anchor="middle" font-size="11" '
                              f'font-weight="600" fill="{AZUL}">{escape(etiqueta)}</text>')
            else:
                d = s * 0.14
                partes.append(f'<path d="M{cx - d},{cy - d} L{cx + d},{cy + d} M{cx + d},{cy - d} L{cx - d},{cy + d}" '
                              f'stroke="{ROJO}" stroke-width="2.6" stroke-linecap="round"/>')
                regla_txt = {'simetria': 'R1', 'colision': 'R2', 'callejon': 'R3', 'esteril': 'R4'}[c['motivo']]
                partes.append(f'<text x="{cx}" y="{cy + d + 15}" text-anchor="middle" font-size="11" '
                              f'font-weight="600" fill="{ROJO}">{c["paso"]} · {regla_txt}</text>')
    # Monómeros.
    r = s * 0.3
    for i, (x, y) in enumerate(coords):
        cx, cy = px(x, y)
        m = mu_vis[i]
        if mu is None:
            relleno = NARANJA if m >= 0.5 else '#ffffff'
            borde = '#ffffff' if m >= 0.5 else TINTA_2
            ancho = 2 if m >= 0.5 else 1.8
        else:
            relleno = _mezcla(m)
            borde = TINTA_2 if m < 0.5 else '#ffffff'
            ancho = 1.8
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{relleno}" stroke="{borde}" stroke-width="{ancho}"/>')
        if m >= 0.5 and mu is None:   # anillo fino para que el blanco del borde no se pierda
            partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 1.5}" fill="none" stroke="{NARANJA}" stroke-width="1"/>')
        if i in resaltar:
            partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 5}" fill="none" stroke="{AZUL}" stroke-width="2.4"/>')
        if indices:
            color = '#ffffff' if m >= 0.55 else TINTA_2
            partes.append(f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="{11 if i < 10 else 10}" '
                          f'font-weight="600" fill="{color}">{i}</text>')
    # Colisión marcada.
    if fantasma:
        cx, cy = px(*fantasma)
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{ROJO}" fill-opacity="0.12" stroke="{ROJO}" '
                      f'stroke-width="2" stroke-dasharray="4 3"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H + alto_titulo}" '
            f'style="max-width:{ancho_max or W}px;width:100%;height:auto;display:block;margin:auto;font-family:inherit" '
            f'role="img" aria-label="{escape(titulo or "Conformación " + sec_vis)}">' + ''.join(partes) + '</svg>')


def marco_comun(*listas_movs):
    """Marco que contiene varias conformaciones, para dibujarlas a la misma escala."""
    pts = [c for movs in listas_movs for c in reconstruir_coordenadas(movs)]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1


def fila(*svgs, hueco=24):
    """Varios SVG lado a lado (se apilan en pantallas estrechas)."""
    celdas = ''.join(f'<div style="flex:1 1 0;min-width:160px">{s}</div>' for s in svgs)
    return f'<div style="display:flex;flex-wrap:wrap;gap:{hueco}px;align-items:flex-end">{celdas}</div>'


def cinta(sec, mu=None, resaltar=(), tam=26):
    """La secuencia como una fila de bolitas (sin plegar)."""
    mu = list(mu) if mu is not None else grados_crisp(sec)
    n, r = len(mu), tam * 0.38
    W, H = n * tam + 8, tam + 18
    partes = [f'<line x1="{tam / 2 + 4}" y1="{tam / 2 + 2}" x2="{W - tam / 2 - 4}" y2="{tam / 2 + 2}" '
              f'stroke="{CADENA}" stroke-width="3"/>']
    for i, m in enumerate(mu):
        cx, cy = 4 + tam * i + tam / 2, tam / 2 + 2
        relleno = _mezcla(m)
        borde = TINTA_2 if m < 0.5 else '#ffffff'
        partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{relleno}" stroke="{borde}" stroke-width="1.6"/>')
        if i in resaltar:
            partes.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 4}" fill="none" stroke="{AZUL}" stroke-width="2"/>')
        partes.append(f'<text x="{cx}" y="{H - 2}" text-anchor="middle" font-size="9" fill="{TENUE}">{i}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'style="max-width:{W}px;width:100%;height:auto;display:block;font-family:inherit" role="img" '
            f'aria-label="Secuencia">' + ''.join(partes) + '</svg>')
