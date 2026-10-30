import altair as alt
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.motor import CONFIG_ACTUAL, MOTIVOS, a_estrella
from hp.ui import AZUL, NARANJA, aviso, encabezado, idea, optimo, resolver, navegacion, svg

encabezado('Reglas de poda',
           'Cada cadena a medio hacer tiene hasta tres hijos, y cada hijo, tres nietos. Una regla que descarta un hijo '
           'temprano se ahorra todo lo que colgaba de él. Estas son las cinco que usa el buscador.')

idea('Podar es decir «por aquí no» lo antes posible. Algunas reglas son <b>seguras</b> (nunca descartan la mejor forma) '
     'y otras son <b>apuestas</b>: casi siempre aciertan y ahorran mucho, pero a veces se equivocan.')

st.markdown(
    """
| Regla | Qué descarta | ¿Segura? |
|---|---|---|
| **R0 · Estabilidad** | La secuencia entera, antes de buscar, si tiene menos de 30 % de H | No |
| **R1 · Simetría** | El primer giro a la derecha (es el espejo de uno a la izquierda) | Sí |
| **R2 · Colisión** | Poner una bolita en una casilla ocupada | Sí (es la regla del juego) |
| **R3 · Callejón** | Meterse en un hueco donde no caben las bolitas que faltan | Sí, con la perilla m3 ≤ 1 |
| **R4 · Motivo estéril** | Una horquilla cerrada (dos giros iguales seguidos) con pocas H cerca | No |
"""
)
st.markdown('')

t0, t1, t2, t3, t4 = st.tabs(['R0 · Estabilidad', 'R1 · Simetría', 'R2 · Colisión', 'R3 · Callejón',
                              'R4 · Motivo estéril'])

# ---------------------------------------------------------------- R0
with t0:
    EJ = 'HPPHPPHPPHPPPP'
    r = resolver(EJ)
    izq, der = st.columns([2, 3], gap='large')
    with der:
        st.markdown(
            """
**Antes de buscar nada**, se cuenta qué fracción de la cadena es H. Si es menor que **0.3**, la secuencia se declara
*inestable* (no tendría con qué formar un núcleo) y no se busca.

Es un corte **seco**: una secuencia con 29.9 % de H se descarta y otra con 30.1 % se pliega con todo el esfuerzo.
Y no siempre acierta. La de la izquierda tiene solo 4 H de 14 (29 %), así que R0 la descarta… pero sus cuatro H
pueden formar un cuadrado con **4 contactos**.
"""
        )
        aviso('Al revisar todas las cadenas de 10 a 14 bolitas que R0 descarta, <b>la mitad</b> (1232 de 2436) tiene '
              'al menos dos contactos en su mejor forma. En la página de <b>lógica difusa</b> el corte seco se cambia '
              'por una rampa ajustada con esos datos.')
    with izq:
        svg(dibujo.conformacion(EJ, r.movs, celda=40, ancho_max=320,
                                titulo=f'{EJ.count("H")} H de {len(EJ)} · energía {r.energia:g}'))
    fr = pd.DataFrame(dict(f=[0, 0.3, 0.3, 0.6], v=[0, 0, 1, 1]))
    escalon = alt.Chart(fr).mark_line(color=AZUL, strokeWidth=2).encode(
        x=alt.X('f:Q', title='Fracción de H', scale=alt.Scale(domain=[0, 0.6])),
        y=alt.Y('v:Q', title='¿Se busca?', axis=alt.Axis(values=[0, 1], labelExpr="datum.value ? 'sí' : 'no'")))
    punto = alt.Chart(pd.DataFrame(dict(f=[EJ.count('H') / len(EJ)], v=[0]))).mark_point(
        color=NARANJA, filled=True, size=90).encode(x='f:Q', y='v:Q')
    st.altair_chart((escalon + punto).properties(height=150), width='stretch')
    st.caption('El punto naranja es la secuencia del dibujo: queda justo del lado del «no».')

# ---------------------------------------------------------------- R1
with t1:
    sec = 'PHPPHP'
    marco = dibujo.marco_comun('FLLR', 'FRRL')
    izq, der = st.columns([1, 1], gap='large')
    with izq:
        svg(dibujo.fila(dibujo.conformacion(sec, 'FLLR', celda=42, marco=marco, titulo='FLLR'),
                        dibujo.conformacion(sec, 'FRRL', celda=42, marco=marco, titulo='FRRL')))
    with der:
        st.markdown(
            """
Toda forma tiene una **gemela en espejo**: cambiando cada izquierda por derecha (y al revés) sale la misma figura
reflejada, con los mismos contactos y la misma energía.

Para no buscar dos veces lo mismo, el primer giro **siempre es a la izquierda**: mientras la cadena vaya recta,
la opción «derecha» se descarta.
"""
        )
        idea('Corta muy pocas ramas, pero todas están arriba del árbol: cada una es la raíz de <b>la mitad</b> de las '
             'formas posibles. Es la poda más barata y más rentable.', titulo='Por qué vale tanto')

# ---------------------------------------------------------------- R2
with t2:
    sec = 'HPPHPH'
    cand = [dict(paso='F', motivo='ok', texto='Recto'), dict(paso='L', motivo='colision'),
            dict(paso='R', motivo='ok', texto='Derecha')]
    izq, der = st.columns([1, 1], gap='large')
    with izq:
        svg(dibujo.conformacion(sec, 'LL', candidatos=cand, celda=50, ancho_max=300))
    with der:
        st.markdown(
            """
La regla del juego: **dos bolitas no pueden ocupar la misma casilla**. Si girar a la izquierda cae sobre la bolita 0,
esa opción no existe.

Es la que más ramas descarta en números absolutos, porque cuanto más compacta es la forma (justo lo que busca
el plegamiento), más casillas vecinas están ya ocupadas.
"""
        )

# ---------------------------------------------------------------- R3
with t3:
    sec = 'HPHPPHHPHPPHPHHPPHPH'
    movs = 'FFLFLFFFL'
    cand = [dict(paso='F', motivo='ok', texto='Recto'), dict(paso='L', motivo='callejon'),
            dict(paso='R', motivo='ok', texto='Derecha')]
    izq, der = st.columns([1, 1], gap='large')
    with izq:
        svg(dibujo.conformacion(sec, movs, candidatos=cand, region=[(-1, 1), (-1, 2)], celda=46, ancho_max=340))
    with der:
        faltan = len(sec) - len(movs) - 3
        st.markdown(
            f"""
Si la bolita 11 gira a la izquierda, entra en un **bolsillo** cerrado: solo quedan libres las 2 casillas marcadas
en rojo, y todavía faltan **{faltan} bolitas** por colocar. Esa rama no puede terminar nunca.

Para saberlo, el buscador hace un **relleno por inundación**: desde la casilla nueva, «derrama agua» por las
casillas libres vecinas y cuenta cuántas alcanza.

- Si alcanza al menos $\\lceil m_3 \\cdot \\text{{faltan}} \\rceil$ casillas, sigue adelante.
- Si el agua sale del bolsillo y llega lejos, hay espacio de sobra y deja de contar.
"""
        )
        st.caption('Con m3 = 1 la regla es segura: solo descarta lo imposible. Con m3 > 1 exige espacio de más '
                   '(se vuelve una apuesta); con m3 < 1, de menos (poda menos). El ajuste de la página 5 mueve esta perilla.')

# ---------------------------------------------------------------- R4
with t4:
    sec = 'HPPHPPHHPH'
    cand = [dict(paso='F', motivo='ok', texto='Recto'), dict(paso='L', motivo='esteril'),
            dict(paso='R', motivo='ok', texto='Derecha')]
    izq, der = st.columns([1, 1], gap='large')
    with izq:
        svg(dibujo.conformacion(sec, 'FFL', candidatos=cand, celda=50, ancho_max=300))
    with der:
        st.markdown(
            """
Dos giros iguales seguidos (izquierda-izquierda o derecha-derecha) doblan la cadena en una **horquilla**: un
giro en U muy cerrado. Si en las **últimas 4 bolitas hay menos de 2 H**, esa horquilla gasta espacio sin dar
contactos, y se descarta.

Aquí la ventana son las bolitas 2 a 5 (la 5 es la que se colocaría): P, H, P, P. Solo una H, así que «izquierda» se descarta.
"""
        )
    st.markdown('#### Es una apuesta, y a veces pierde')
    SEC = 'HHPHPPPPHH'
    con = resolver(SEC)
    e_opt, mov_opt = optimo(SEC)[:2]
    marco = dibujo.marco_comun(con.movs, mov_opt)
    izq, der = st.columns([3, 2], gap='large')
    with izq:
        svg(dibujo.fila(dibujo.conformacion(SEC, con.movs, celda=40, marco=marco,
                                            titulo=f'Con R4 · energía {con.energia:g}'),
                        dibujo.conformacion(SEC, mov_opt, celda=40, marco=marco,
                                            titulo=f'La mejor · energía {e_opt:g}')))
    with der:
        st.markdown(
            f"""
En `{SEC}` la mejor forma usa justamente una horquilla de P para juntar las H de los dos extremos. R4 la ve
«estéril» y la descarta, y el buscador se queda con **{-con.energia:g} contactos en lugar de {-e_opt:g}**.

En la mayoría de secuencias R4 ahorra trabajo sin cambiar el resultado; por eso se mantiene, y su umbral
(`r4` = 0, 1 o 2) es otra de las cosas que se ajustan en la página de CMA-ES.
"""
        )
    with st.expander('Una regla que nunca hacía nada'):
        izq, der = st.columns([1, 2], gap='large')
        with izq:
            svg(dibujo.conformacion('PPPPPP', 'FLL', candidatos=[dict(paso='L', motivo='colision')],
                                    celda=44, ancho_max=220, contactos_visibles=False))
        with der:
            st.markdown(
                """
La primera versión de R4 buscaba **tres** giros iguales seguidos (izquierda-izquierda-izquierda). Pero tres giros
iguales cierran un cuadrado y la bolita cae sobre una que ya está: **R2 la descartaba antes** y R4 nunca llegaba a
actuar: cero disparos en todas las cadenas hasta 12 bolitas y en 2129 secuencias al azar. Era código muerto, un desfase de uno en el índice. Se corrigió en el sprint 2: el motivo cerrado real se forma con **dos** giros.
"""
            )

# ---------------------------------------------------------------- ahorro
st.markdown('### ¿Cuánto ahorra cada regla?')
OPCIONES = {'HHPHHPPHHHPP (12)': 'HHPHHPPHHHPP', 'PPHPHPHHHHPHP (13)': 'PPHPHPHHHHPHP',
            'HHHHPPHPHPPHHHPPHHP (19)': 'HHHHPPHPHPPHHHPPHHP', 'HHPHPHPPPHHHPPPHPPHPH (21)': 'HHPHPHPPPHHHPPPHPPHPH'}
eleccion = st.segmented_control('Secuencia', list(OPCIONES), default='HHHHPPHPHPPHHHPPHHP (19)',
                                label_visibility='collapsed')
sec = OPCIONES[eleccion or 'HHHHPPHPHPPHHHPPHHP (19)']


@st.cache_data(show_spinner=False)
def comparar(sec):
    conteo = {}
    todas = a_estrella(sec, CONFIG_ACTUAL, tope_nodos=300_000, conteo=conteo)
    sin_r3 = a_estrella(sec, CONFIG_ACTUAL._replace(m3=0), tope_nodos=300_000)
    sin_r4 = a_estrella(sec, CONFIG_ACTUAL._replace(r4=0), tope_nodos=300_000)
    return conteo, todas, sin_r3, sin_r4


conteo, todas, sin_r3, sin_r4 = comparar(sec)
df = pd.DataFrame([dict(regla=MOTIVOS[m], ramas=conteo.get(m, 0)) for m in ('simetria', 'colision', 'callejon',
                                                                             'esteril')])
barras = alt.Chart(df).mark_bar(color=AZUL, cornerRadiusEnd=4, height=22).encode(
    x=alt.X('ramas:Q', title='Hijos descartados durante la búsqueda'),
    y=alt.Y('regla:N', title=None, sort=None, axis=alt.Axis(labelLimit=240)), tooltip=['regla', 'ramas'])
etiquetas = barras.mark_text(align='left', dx=4, color='#52514e').encode(text='ramas:Q')
st.altair_chart((barras + etiquetas).properties(height=180), width='stretch')
filas = [('Con todas las reglas', todas), ('Sin R3 (m3 = 0)', sin_r3), ('Sin R4 (r4 = 0)', sin_r4)]
st.dataframe(pd.DataFrame([{'Variante': k, 'Nodos expandidos': v.nodos, 'Energía': v.energia} for k, v in filas]),
             hide_index=True, width='stretch')
st.caption('Contar ramas descartadas no es lo mismo que medir el ahorro: una rama cortada arriba vale miles '
           'cortadas abajo. Por eso R1 casi no aparece en las barras y aun así reduce la búsqueda a la mitad.')
if sin_r4.energia < todas.energia:
    extra = ' y además expande <b>menos</b> nodos' if sin_r4.nodos < todas.nodos else ''
    aviso(f'En esta secuencia R4 se equivoca: sin ella el buscador encuentra una forma <b>mejor</b> '
          f'({sin_r4.energia:g} frente a {todas.energia:g}){extra}. Las apuestas de poda interactúan con la '
          f'heurística de formas difíciles de prever: de ahí la idea de ajustarlas con datos.')

navegacion('paginas/reglas.py')
