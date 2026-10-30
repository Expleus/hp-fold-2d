import altair as alt
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.motor import MOTIVOS, reconstruir_coordenadas
from hp.ui import (AZUL, GRIS, NARANJA, avanzar, controles, encabezado, ficha, fragmento, idea, optimo, quieto,
                   resolver_con_traza, secuencia_hp, siguiente, svg)

encabezado('Cómo busca A*',
           'En vez de probar todas las formas, A* construye la cadena bolita a bolita y en cada momento sigue '
           'por la cadena a medio hacer que más promete. Las que prometen poco esperan… y muchas nunca se tocan.')

st.markdown('### Una promesa por cada cadena a medio hacer')
c1, c2, c3 = st.columns(3)
with c1:
    ficha('g · lo que ya tengo', 'Energía actual', 'Los contactos que ya formaron las bolitas colocadas. Es exacto.')
with c2:
    ficha('h · lo que aún puedo ganar', 'Estimación', 'Una cota de cuántos contactos podrían añadir las bolitas que '
          'faltan. Se calcula sin colocarlas, en un instante.')
with c3:
    ficha('f = g + h · la promesa', 'Prioridad', 'La mejor energía final a la que podría llegar esta cadena. '
          'Cuanto más negativa, más prometedora.')

st.markdown('')
st.markdown(
    """
Todas las cadenas pendientes esperan en una **fila ordenada por su promesa f** (la *cola de prioridad*). En cada paso A*:

1. saca la de **f más baja**;
2. prueba a añadirle una bolita **recto, a la izquierda o a la derecha**;
3. descarta las opciones que rompen alguna **regla** (siguiente página) y mete las demás en la fila con su nueva f.

Se detiene cuando lo que sale de la fila es una **cadena completa**: ninguna otra promete algo mejor.
"""
)
idea('Es como un GPS: para cada ruta suma lo ya recorrido (g) y una estimación en línea recta de lo que falta (h), '
     'y explora primero las rutas cuyo total es menor. Si la estimación nunca es demasiado pesimista, la primera '
     'ruta completa que encuentra es la mejor.')

# ---------------------------------------------------------------- reproductor
st.markdown('### Reproductor paso a paso')
OPCIONES = ['HHPHPHHPPH', 'HPPHPPHHPH', 'PPHHHPHPPH', 'HPPPHHPHPH', 'HHPHPPPPHH']
sec = secuencia_hp('Secuencia', OPCIONES, key='as_sec', n_max=14,
                   ayuda='Cadenas cortas: así el recorrido completo cabe en el reproductor.')
r, traza = resolver_con_traza(sec)
T = len(traza)
if st.session_state.get('as_para') != sec:
    st.session_state.as_para, st.session_state.as_paso, st.session_state.as_paso_play = sec, 1, False
completo = bool(traza) and traza[-1]['final']
if not completo:
    st.caption(f'Esta secuencia necesita más de {T} pasos: el reproductor muestra solo los primeros {T}.')


@fragmento('as_paso', segundos=0.8)
def reproductor():
    avanzar('as_paso', T)
    st.slider('Paso', 1, T, key='as_paso', label_visibility='collapsed', on_change=quieto, args=('as_paso',))
    controles('as_paso', T)

    paso = st.session_state.as_paso
    rec = traza[paso - 1]
    coords_todas = [reconstruir_coordenadas(x['movs']) for x in traza]
    xs = [x for c in coords_todas for x, _ in c]
    ys = [y for c in coords_todas for _, y in c]
    marco = (min(xs) - 2, max(xs) + 2, min(ys) - 2, max(ys) + 2)

    izq, der = st.columns([3, 2], gap='large')
    with izq:
        if rec['final']:
            svg(dibujo.conformacion(sec, rec['movs'], celda=44, ancho_max=480, marco=marco))
        else:
            svg(dibujo.conformacion(sec, rec['movs'], candidatos=rec['hijos'], celda=44, ancho_max=480, marco=marco))
    with der:
        k = len(rec['movs']) + 2
        if rec['final']:
            st.success(f"**Paso {paso}: solución.** Sale de la fila una cadena completa con energía **{rec['g']:g}**. "
                       f"Ninguna de las {rec['frontera']} que esperan promete algo mejor.", icon=':material/flag:')
        else:
            st.markdown(f"**Paso {paso} de {T}.** Se expande la cadena de **{k} bolitas** "
                        f"<span class='mono'>{rec['movs'] or '(inicio)'}</span>.", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric('g', f"{rec['g']:g}", help='Energía de los contactos ya formados.')
        m2.metric('h', f"{rec['h']:.1f}", help='Estimación de lo que aún se puede ganar.')
        m3.metric('f = g + h', f"{rec['f']:.1f}", help='La promesa; la fila se ordena por este número.')
        if not rec['final']:
            filas = []
            for h in rec['hijos']:
                filas.append({'Paso': {'F': 'Recto', 'L': 'Izquierda', 'R': 'Derecha'}[h['paso']],
                              'Resultado': MOTIVOS[h['motivo']],
                              'f': '—' if h['motivo'] != 'ok' else f"{h['f']:.1f}"})
            st.dataframe(pd.DataFrame(filas), hide_index=True, width='stretch')
            st.caption(f"Quedan **{rec['frontera']}** cadenas esperando en la fila. Las primeras, por promesa: " +
                       ', '.join(f"<span class='mono'>{m or '·'}</span> ({f:.1f})" for f, m in rec['cola'][:4]),
                       unsafe_allow_html=True)

    df = pd.DataFrame(dict(paso=range(1, T + 1), f=[x['f'] for x in traza],
                           bolitas=[len(x['movs']) + 2 for x in traza]))
    e_opt = optimo(sec)[0]
    linea = alt.Chart(df).mark_line(color=AZUL, strokeWidth=2, interpolate='step-after').encode(
        x=alt.X('paso:Q', title='Paso'), y=alt.Y('f:Q', title='Promesa f'),
        tooltip=['paso', alt.Tooltip('f:Q', format='.2f'), alt.Tooltip('bolitas:Q', title='bolitas')])
    regla = alt.Chart(pd.DataFrame(dict(y=[e_opt]))).mark_rule(color=NARANJA, strokeDash=[5, 4]).encode(y='y:Q')
    texto = alt.Chart(pd.DataFrame(dict(y=[e_opt], x=[1]))).mark_text(
        align='left', dy=-7, color=NARANJA, fontWeight=600).encode(x='x:Q', y='y:Q',
                                                                    text=alt.value('mejor energía posible'))
    cursor = alt.Chart(pd.DataFrame(dict(x=[paso]))).mark_rule(color=GRIS).encode(x='x:Q')
    st.altair_chart((linea + regla + texto + cursor).properties(height=220), width='stretch')
    st.caption('La promesa de lo que se expande casi nunca baja: A* empieza por lo más optimista y va «pagando» la '
               'diferencia hasta que la promesa coincide con una cadena real.')


reproductor()

with st.expander('Por qué la primera cadena completa es la mejor (y cuándo deja de serlo)'):
    st.markdown(
        r"""
La fila se ordena por $f = g + w\,h$. Con $w = 1$, si $h$ **nunca promete menos de lo que realmente queda**
(es decir, $g + h$ es siempre una cota inferior de la energía final de cualquier forma de terminar esa cadena), cuando
sale una cadena completa con energía $E$ todas las demás tienen $f \ge E$: ninguna puede terminar por debajo. A esa
propiedad se le llama **admisibilidad**.

En el proyecto la garantía se cambia a veces por velocidad, de forma consciente:

- $w < 1$ rebaja las promesas: las cadenas que ya tienen contactos pasan delante de las que solo prometen, A* se
  lanza antes hacia el final, expande menos y puede quedarse con una forma algo peor ($w > 1$ hace lo contrario);
- algunas reglas (R3 con $m_3 > 1$, R4) cortan ramas que *probablemente* no sirven, no que *seguro* no sirven;
- los coeficientes de la heurística se ajustan con datos (página de CMA-ES) para equilibrar acierto y esfuerzo.
"""
    )

siguiente('paginas/reglas.py', 'Reglas de poda')
