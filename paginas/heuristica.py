import altair as alt
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.motor import CONFIG_ACTUAL, contactos, grados_crisp, paridad, reconstruir_coordenadas
from hp.ui import (AQUA, AZUL, GRIS, GRIS_CLARO, NARANJA, datos, encabezado, idea, optimo, referencia, resolver,
                   secuencia_hp, siguiente, svg)

encabezado('La heurística: cuánto falta por ganar',
           'A* necesita, para cada cadena a medio hacer, una estimación rápida de cuántos contactos podrían añadir las '
           'bolitas que faltan. De lo buena que sea esa estimación depende casi todo.')

idea('Si la estimación <b>promete de más</b>, todas las cadenas parecen buenas y A* acaba revisándolo casi todo. '
     'Si <b>promete de menos</b>, puede descartar sin querer el camino correcto. La ideal promete <i>justo</i> un poco '
     'más de lo que se puede conseguir.')

# ---------------------------------------------------------------- cota básica
st.markdown('### Primera cota: contar huecos')
izq, der = st.columns([1, 2], gap='large')
with izq:
    svg(dibujo.conformacion('PHP', 'F', marcas=[(-1, 1), (1, 1)], celda=50, ancho_max=200))
with der:
    st.markdown(
        """
En la cuadrícula cada casilla tiene **4 vecinas**. Una bolita del medio de la cadena ya usa 2 para unirse a la
anterior y a la siguiente, así que le quedan **unos 2 huecos** donde podría tocar a otra H.

Por tanto, si quedan $H_{\\text{rest}}$ bolitas H por colocar, como mucho aportarán unos $2\\,H_{\\text{rest}}$
contactos más:

$$
h_{\\text{básica}} = -\\,a_b \\cdot H_{\\text{rest}}, \\qquad a_b = 2
$$

Es fácil de calcular, pero muy optimista: supone que **todas** las H encuentran pareja en **todos** sus huecos.
"""
    )

# ---------------------------------------------------------------- paridad
st.markdown('### Segunda cota: el tablero de ajedrez')
HERO = 'HPHPPHHPHPPHPHHPPHPH'
r_hero = resolver(HERO)
mu = grados_crisp(HERO)
pares, impares = paridad(mu)
izq, der = st.columns([1, 1], gap='large')
with izq:
    svg(dibujo.conformacion(HERO, r_hero.movs, ajedrez=True, celda=40, ancho_max=380))
with der:
    st.markdown(
        f"""
Pinta la cuadrícula como un tablero de ajedrez. Cada paso de la cadena cambia de color, así que:

- las bolitas **pares** (0, 2, 4…) caen siempre en casillas de un color,
- las **impares** (1, 3, 5…), siempre en el otro,
- y dos casillas vecinas son siempre de colores distintos.

Conclusión: **un contacto siempre une una H par con una H impar**. Si hay pocas H impares, da igual cuántas pares
haya: no tienen con quién emparejarse. Cada H aporta como mucho 2 contactos (3 si está en un extremo):

$$
|E| \\le 2\\cdot\\min(H_{{\\text{{par}}}},\\ H_{{\\text{{impar}}}}) + 2
$$

En la figura hay **{pares:g} H pares** y **{impares:g} impares**: como mucho {2 * min(pares, impares) + 2:g}
contactos. La mejor forma consigue {-r_hero.energia:g}.
"""
    )

# ---------------------------------------------------------------- pruébalo
st.markdown('#### Compara las cotas con la realidad')
OPCIONES = ['HHPPHHPPHPHH', 'HPHPHPHPHPHP', 'HHHHHHHHHH', 'PPHHHPHPPH', 'HPHPPHHPHPPHPHHPPHPH']
sec = secuencia_hp('Secuencia', OPCIONES, key='heu_sec', n_max=24)
mu = grados_crisp(sec)
p, q = paridad(mu)
if len(sec) <= 14:
    e_opt, mov_opt = optimo(sec)[:2]
    fuente = 'calculado probando todas las formas'
else:
    r = resolver(sec)
    e_ref = referencia(sec)
    e_opt, mov_opt = (e_ref if e_ref is not None else r.energia), r.movs
    fuente = 'referencia del banco' if e_ref is not None else 'la mejor que encuentra A*'
df = pd.DataFrame([
    dict(cota='Básica: 2 × H', valor=2 * sum(mu), tipo='válida'),
    dict(cota='Paridad: 2·min + 2', valor=2 * min(p, q) + 2, tipo='válida'),
    dict(cota='Paridad con error: min + 2', valor=min(p, q) + 2, tipo='con error'),
])
izq, der = st.columns([3, 2], gap='large')
with izq:
    barras = alt.Chart(df).mark_bar(cornerRadiusEnd=4, height=24).encode(
        x=alt.X('valor:Q', title='Contactos como máximo', scale=alt.Scale(domainMin=0)),
        y=alt.Y('cota:N', title=None, sort=None, axis=alt.Axis(labelLimit=240)),
        color=alt.Color('tipo:N', scale=alt.Scale(domain=['válida', 'con error'], range=[GRIS_CLARO, '#e9c9c9']),
                        legend=None),
        tooltip=[alt.Tooltip('cota:N', title='Cota'), alt.Tooltip('valor:Q', title='Máximo')])
    texto = barras.mark_text(align='left', dx=4, color='#52514e').encode(text='valor:Q')
    real = alt.Chart(pd.DataFrame(dict(x=[-e_opt]))).mark_rule(color=NARANJA, strokeWidth=2.5).encode(x='x:Q')
    etiqueta = alt.Chart(pd.DataFrame(dict(x=[-e_opt], y=['Básica: 2 × H']))).mark_text(
        align='left', dx=5, dy=-18, color=NARANJA, fontWeight=600).encode(
        x='x:Q', y=alt.Y('y:N', sort=None), text=alt.value(f'real: {abs(e_opt):g}'))
    st.altair_chart((barras + texto + real + etiqueta).properties(height=170), width='stretch')
with der:
    st.markdown(f'Mejor forma posible: **{abs(e_opt):g} contactos** ({fuente}).')
    st.markdown(f'H pares: **{p:g}** · H impares: **{q:g}**')
    if min(p, q) + 2 < -e_opt:
        st.error('La versión con error promete **menos** de lo que se puede conseguir: A* podría descartar la mejor '
                 'forma creyendo que no vale la pena.', icon=':material/error:')
    elif p == 0 or q == 0:
        st.info('Todas las H tienen la misma paridad: no pueden tocarse nunca. La cota de paridad lo ve; la básica, no.',
                icon=':material/lightbulb:')
    else:
        st.caption('Una cota válida nunca queda a la izquierda de la línea naranja. Cuanto más cerca de ella, mejor '
                   'guía a la búsqueda.')

# ---------------------------------------------------------------- h completa
st.markdown('### Juntando las piezas')
st.markdown(
    r"""
Las dos cotas son correctas, así que la estimación se queda con **la más ajustada** de las dos. Y a la de paridad, que
habla de la cadena **entera**, se le descuenta lo que ya se consiguió ($g$ es negativo: $-a_g\,g$ resta contactos
ya hechos):

$$
h = \max\Big(\;-a_b\,H_{\text{rest}}\;,\;\; -\big(a_p\cdot\min(H_{\text{par}},H_{\text{impar}}) + c\big) - a_g\, g\;\Big)
\qquad f = g + w\cdot h
$$

Con los valores «de libro» $a_b = a_p = c = 2$, $a_g = 1$ y $w = 1$ la estimación nunca promete de menos. Esos seis
números son las **perillas** que la página siguiente ajusta automáticamente.
"""
)

if mov_opt:
    filas = []
    a = CONFIG_ACTUAL
    H = sum(mu)
    for k in range(2, len(sec) + 1):
        coords = reconstruir_coordenadas(mov_opt[:k - 2])
        g = -len(contactos(coords, sec=sec[:k]))
        h = max(-a.a_b * (H - sum(mu[:k])), -(a.a_p * min(p, q) + a.c) - a.a_g * g)
        for nombre, v in (('g · ya conseguido', g), ('h · estimación', h), ('f = g + h', g + h)):
            filas.append(dict(k=k, serie=nombre, valor=v))
    df = pd.DataFrame(filas)
    orden = ['g · ya conseguido', 'h · estimación', 'f = g + h']
    lineas = alt.Chart(df).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=30)).encode(
        x=alt.X('k:Q', title='Bolitas colocadas (siguiendo la mejor forma)'),
        y=alt.Y('valor:Q', title='Energía'),
        color=alt.Color('serie:N', title=None, sort=orden, legend=alt.Legend(orient='top'),
                        scale=alt.Scale(domain=orden, range=[AZUL, NARANJA, AQUA])),
        tooltip=[alt.Tooltip('k:Q', title='Bolitas'), alt.Tooltip('serie:N', title='Serie'),
                 alt.Tooltip('valor:Q', title='Valor', format='.1f')])
    meta = alt.Chart(pd.DataFrame(dict(y=[e_opt]))).mark_rule(color=GRIS, strokeDash=[5, 4]).encode(y='y:Q')
    st.altair_chart((lineas + meta).properties(height=260), width='stretch')
    st.caption(f'Recorriendo la mejor forma de {sec}: g baja a medida que aparecen contactos, h se encoge porque '
               'queda menos por ganar, y f se mantiene por debajo de la energía final (línea gris) hasta encontrarse '
               'con ella. Eso es lo que hace que A* no la descarte.')

# ---------------------------------------------------------------- w
st.markdown('### La perilla w: cuánto creerle a la estimación')
st.markdown(
    r"""
Con $f = g + w\,h$, el peso $w$ decide cuánto pesan las promesas frente a lo ya conseguido. Como aquí $h$ promete
contactos (es negativa):

- **$w < 1$** rebaja las promesas: pasan delante las cadenas que ya tienen contactos. A* corre hacia el final,
  revisa poco… y puede quedarse con una forma peor.
- **$w > 1$** infla las promesas: las cadenas cortas, que tienen mucho por delante, parecen mejores. A* explora a lo
  ancho y gasta mucho más.
"""
)
barrido = pd.DataFrame(datos('pesos_w.json')['filas'])
tope = datos('pesos_w.json')['tope']
elegida = st.segmented_control('Secuencia del barrido', sorted(barrido.sec.unique(), key=len),
                               default='HPHPPHHPHPPHPHHPPHPH', key='heu_w')
sub = barrido[barrido.sec == (elegida or 'HPHPPHHPHPPHPHHPPHPH')].copy()
sub['resultado'] = sub.apply(lambda r: 'tope de nodos' if r.estado != 'ok' else
                             ('óptima' if r.energia <= r.optimo else 'peor que la óptima'), axis=1)
dom = ['óptima', 'peor que la óptima', 'tope de nodos']
izq, der = st.columns(2, gap='large')
with izq:
    graf = alt.Chart(sub).mark_line(color=GRIS_CLARO, strokeWidth=2).encode(
        x=alt.X('w:Q', title='w'), y=alt.Y('nodos:Q', title='Nodos expandidos (escala log)', scale=alt.Scale(type='log')))
    puntos = alt.Chart(sub).mark_point(filled=True, size=70).encode(
        x='w:Q', y='nodos:Q',
        color=alt.Color('resultado:N', title=None, scale=alt.Scale(domain=dom, range=[AZUL, NARANJA, GRIS]),
                        legend=alt.Legend(orient='top')),
        shape=alt.Shape('resultado:N', scale=alt.Scale(domain=dom, range=['circle', 'triangle-down', 'square']),
                        legend=None),
        tooltip=[alt.Tooltip('w:Q'), alt.Tooltip('nodos:Q', title='Nodos', format=','),
                 alt.Tooltip('energia:Q', title='Energía'), alt.Tooltip('resultado:N', title='Resultado')])
    uno = alt.Chart(pd.DataFrame(dict(x=[1.0]))).mark_rule(color=GRIS, strokeDash=[4, 4]).encode(x='x:Q')
    st.altair_chart((graf + puntos + uno).properties(height=260), width='stretch')
with der:
    w1 = sub[sub.w == 1.0].iloc[0]
    rapido = sub[(sub.resultado == 'óptima')].nsmallest(1, 'nodos')
    st.metric('Con w = 1', f'{int(w1.nodos):,} nodos'.replace(',', '.'), help='La configuración de libro.')
    if not rapido.empty and rapido.iloc[0].w != 1.0:
        fila = rapido.iloc[0]
        st.metric(f'Con w = {fila.w:g}', f'{int(fila.nodos):,} nodos'.replace(',', '.'),
                  delta=f'{fila.nodos / w1.nodos - 1:+.0%}'.replace('.', ','), delta_color='inverse',
                  help='El w más barato que todavía encuentra la mejor forma.')
    st.caption(f'Los cuadrados grises agotaron el tope de {tope:,} nodos sin terminar.'.replace(',', '.') +
               ' El punto dulce depende de la secuencia y de las otras cinco perillas: por eso se ajusta con datos.')

siguiente('paginas/cmaes.py', 'Ajuste con CMA-ES')
