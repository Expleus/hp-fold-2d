import math

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.motor import NOMBRES
from hp.ui import AQUA, AZUL, GRIS, NARANJA, TINTA_2, banco, datos, ecuacion, encabezado, ficha, idea, navegacion, svg

encabezado('Robustez: un examinador adversario',
           'Ir bien en promedio no es lo mismo que no tener puntos débiles. Aquí un adversario busca a propósito las '
           'secuencias en las que el buscador flaquea, y el ajuste tiene que defenderse de él.')

H = datos('hedge.json')
N, T = len(H['banco']), H['T']

# ---------------------------------------------------------------- la analogía
st.markdown('### El estudiante y el examinador')
st.markdown('Un estudiante prepara un examen con un banco de preguntas de práctica. Si todas las preguntas pesan lo '
            'mismo, le basta con ir bien **en promedio**. Pero si el examinador **conoce sus puntos débiles** y arma '
            'el examen con ellos, lo que cuenta es su **peor tema**.')
c1, c2 = st.columns(2)
with c1:
    ficha('Afinador · el estudiante', 'Elige una configuración θ',
          'Los seis números del buscador. Quiere que la pérdida sea <b>baja</b>.')
with c2:
    ficha('Adversario · el examinador', 'Elige cuánto pesa cada secuencia',
          f'Un peso por cada una de las {N} secuencias de entrenamiento, que suman 1. Quiere que la pérdida sea '
          '<b>alta</b>.')
st.markdown('')
idea('Es un juego de <b>suma cero</b>: lo que gana uno lo pierde el otro. La pregunta es qué configuración aguanta '
     'mejor cuando el examen se diseña en su contra.')

# ---------------------------------------------------------------- piedra papel tijera
st.markdown('### Primero, un juego conocido: piedra, papel o tijera')
st.markdown(
    """
Quien saca siempre piedra acaba perdiendo: el rival lo nota y saca papel. Cualquier jugada fija se puede explotar,
y la única defensa es **mezclar al azar**, un tercio cada una. El algoritmo que usa el examinador, **Hedge**
(«pesos multiplicativos»), descubre eso solo:

1. lleva la cuenta de **cuánto habría ganado** con cada jugada en todas las rondas anteriores;
2. juega más a menudo lo que mejor le habría ido (con pesos que crecen de forma exponencial);
3. el rival, que ve esos pesos, responde con lo que más daño le hace.
"""
)
PPT = np.array([[0, -1, 1], [1, 0, -1], [-1, 1, 0]])
JUGADAS = ['Piedra', 'Papel', 'Tijera']


@st.cache_data(show_spinner=False)
def piedra_papel_tijera(rondas):
    eta = math.sqrt(8 * math.log(3) / rondas) / 2
    G = np.zeros(3)
    suma, filas = np.zeros(3), []
    marcas = set(np.unique(np.geomspace(1, rondas, 220).astype(int)))
    for t in range(1, rondas + 1):
        p = np.exp(eta * (G - G.max()))
        p /= p.sum()
        G += PPT[:, int(np.argmin(p @ PPT))]
        suma += p
        if t in marcas:
            for k, nombre in enumerate(JUGADAS):
                filas.append(dict(ronda=t, jugada=nombre, peso=p[k], media=suma[k] / t))
    return pd.DataFrame(filas), suma / rondas


rondas = st.select_slider('Rondas jugadas', [10, 100, 1000, 10000], value=1000, key='ppt_rondas')
df, media = piedra_papel_tijera(rondas)
color = alt.Color('jugada:N', title=None, scale=alt.Scale(domain=JUGADAS, range=[AZUL, NARANJA, AQUA]),
                  legend=alt.Legend(orient='top'))
x = alt.X('ronda:Q', title='Ronda', scale=alt.Scale(type='log'))
ronda_a_ronda = alt.Chart(df).mark_line(strokeWidth=1, opacity=0.35).encode(x=x, y='peso:Q', color=color)
promedio = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
    x=x, y=alt.Y('media:Q', title='Frecuencia con que juega cada opción', scale=alt.Scale(domain=[0, 1]),
                 axis=alt.Axis(format='%')),
    color=color, tooltip=['ronda', 'jugada', alt.Tooltip('media:Q', title='promedio', format='.1%'),
                          alt.Tooltip('peso:Q', title='en esta ronda', format='.1%')])
tercio = alt.Chart(pd.DataFrame(dict(y=[1 / 3]))).mark_rule(color=GRIS, strokeDash=[4, 4]).encode(y='y:Q')
st.altair_chart((tercio + ronda_a_ronda + promedio).properties(height=280), width='stretch')
st.caption('Líneas finas: los pesos de cada ronda, que oscilan porque el rival siempre contraataca. Líneas '
           'gruesas: el promedio acumulado, que se acerca a un tercio.')
for col, nombre, m in zip(st.columns(3), JUGADAS, media):
    col.metric(f'{nombre}, en promedio', f'{m:.1%}')

st.markdown('La regla de Hedge, aplicada al examinador: el peso de cada secuencia $s$ en la ronda $t$ crece '
            'exponencialmente con la pérdida que el afinador **ya acumuló** en ella.')
ecuacion(r'p_t(s) \;=\; \frac{e^{\eta\, L_{t-1}(s)}}{\sum_{s^\prime} e^{\eta\, L_{t-1}(s^\prime)}}\,, \qquad '
         r'L_{t-1}(s) = \sum_{k<t} \ell(\theta_k, s)',
         [(r'p_t(s)', 'probabilidad de que el examinador ponga la secuencia $s$ en la ronda $t$.'),
          (r'L_{t-1}(s)', 'pérdida que el afinador acumuló en $s$ en todas las rondas anteriores.'),
          (r'\eta', 'sensibilidad: cuánto reacciona el examinador a esa pérdida (con 0, todas pesarían igual).'),
          (r'e^{\eta L}', 'hace que el peso crezca exponencialmente con la pérdida.'),
          (r'\textstyle\sum_{s^\prime}', 'suma sobre todas las secuencias: divide para que las probabilidades '
                                         'sumen 1.'),
          (r'\ell(\theta_k, s)', r'pérdida en $s$ de la configuración $\theta_k$, la que eligió el afinador en la '
                                 'ronda $k$ (se explica justo abajo).')],
         nota='Donde el afinador viene fallando, el examinador pregunta más: ataca sus puntos débiles.')
st.caption(f'η controla cuánto reacciona el examinador. Con η = √(8 ln N / T) = '
           f'{math.sqrt(8 * math.log(N) / T):.2f} (N = {N} secuencias, T = {T} rondas), la teoría garantiza que su '
           'desventaja frente al mejor examen fijo posible no pasa de √(ln N / 2T) por ronda.')

# ---------------------------------------------------------------- la pérdida
st.markdown('### Cómo se califica cada secuencia')
r = np.geomspace(0.05, 20, 120)
dfl = pd.DataFrame(dict(r=r, l=np.clip((1 + np.log10(r)) / 2, 0, 1)))
curva = alt.Chart(dfl).mark_line(color=AZUL, strokeWidth=2).encode(
    x=alt.X('r:Q', title='Nodos de θ ÷ nodos de la de libro', scale=alt.Scale(type='log'),
            axis=alt.Axis(values=[0.1, 0.3, 1, 3, 10], format='~g')),
    y=alt.Y('l:Q', title='Pérdida ℓ', scale=alt.Scale(domain=[0, 1.05])),
    tooltip=[alt.Tooltip('r:Q', title='proporción', format='.2f'), alt.Tooltip('l:Q', title='ℓ', format='.2f')])
marcas = pd.DataFrame(dict(r=[0.1, 1, 10], l=[0, 0.5, 1], t=['10× más rápida', 'empate', '10× más lenta']))
puntos = alt.Chart(marcas).mark_point(filled=True, size=70, color=AZUL).encode(x='r:Q', y='l:Q')
textos = alt.Chart(marcas).mark_text(dx=8, dy=-10, align='left', color=TINTA_2).encode(x='r:Q', y='l:Q', text='t:N')
fallo = alt.Chart(pd.DataFrame(dict(y=[1]))).mark_rule(color=NARANJA, strokeDash=[5, 4]).encode(y='y:Q')
fallo_t = alt.Chart(pd.DataFrame(dict(y=[1], r=[0.05]))).mark_text(
    align='left', dy=-8, color=NARANJA, fontWeight=600).encode(x='r:Q', y='y:Q',
                                                                text=alt.value('energía equivocada: ℓ = 1'))
st.altair_chart((fallo + fallo_t + curva + puntos + textos).properties(height=260), width='stretch')
st.markdown(
    r"""
Una carrera contra la configuración de libro, secuencia por secuencia:

- si θ **no llega a la mejor energía**, queda descalificada: $\ell = 1$;
- si llega, se compara cuántos nodos gastó con los que gastó la de libro.
"""
)
ecuacion(r'\ell = \frac{1}{2}\left(1 + \log_{10}\frac{\text{nodos}_\theta}{\text{nodos}_\text{libro}}\right)',
         [(r'\ell', 'pérdida de la configuración en una secuencia: 0 es lo mejor, 1 lo peor.'),
          (r'\text{nodos}_\theta', r'cadenas que A* tuvo que expandir con la configuración $\theta$.'),
          (r'\text{nodos}_\text{libro}', 'las que expandió con la configuración de libro.'),
          (r'\log_{10}', r'mide el cociente en potencias de 10: +1 si $\theta$ gastó diez veces más, −1 si '
                         'gastó diez veces menos, 0 si igual.'),
          (r'\tfrac{1}{2}(1 + \cdot)', 'lleva ese rango de −1…+1 a 0…1.')])
st.markdown(
    r"""
recortada entre 0 y 1: **0.5 es empatar**, 0 es ser diez veces más rápida y 1 diez veces más lenta.
"""
)
st.caption(f'Por eso el juego usa {N} secuencias y no 45: en 4 la configuración de libro no llega a la mejor '
           'energía y no sirve de referencia.')
idea('Se compara con la de libro <b>en cada secuencia</b>, no en nodos absolutos. Si no, el examinador pondría todo '
     'el peso en las secuencias largas, que son caras para cualquiera, y no aprendería nada de θ.',
     titulo='¿Por qué relativo?')

# ---------------------------------------------------------------- el juego
st.markdown('### El juego, ronda a ronda')
st.markdown(f'Se juegan {T} rondas. En cada una el examinador fija los pesos con Hedge, y el afinador «estudia para '
            f'ese examen»: CMA-ES busca durante {H["generaciones"]} generaciones la θ con menor pérdida ponderada.')

orden = list(np.argsort(H['p_final'])[::-1])
celdas = []
for t, rd in enumerate(H['rondas'], start=1):
    for pos, i in enumerate(orden):
        celdas.append(dict(ronda=t, pos=pos, sec=H['banco'][i], peso=rd['p'][i], perdida=rd['l'][i],
                           fallo=rd['l'][i] >= 1))
dfc = pd.DataFrame(celdas)
base = alt.Chart(dfc).encode(
    x=alt.X('pos:O', title=f'Las {N} secuencias, ordenadas por su peso al final', axis=alt.Axis(labels=False, ticks=False)),
    y=alt.Y('ronda:O', title='Ronda'))
mapa = base.mark_rect(stroke='white', strokeWidth=1).encode(
    color=alt.Color('peso:Q', title='Peso', scale=alt.Scale(range=['#eef3fa', '#123f75']),
                    legend=alt.Legend(format='.0%', orient='right')),
    tooltip=[alt.Tooltip('sec:N', title='Secuencia'), 'ronda', alt.Tooltip('peso:Q', format='.1%'),
             alt.Tooltip('perdida:Q', title='Pérdida de θ_t', format='.2f')])
cruces = base.transform_filter('datum.fallo').mark_text(text='×', color=NARANJA, fontSize=15, fontWeight=700)
st.altair_chart((mapa + cruces).properties(height=300), width='stretch')
st.caption('Cada fila es una ronda; cada columna, una secuencia. Más oscuro = más peso en el examen. '
           'Las × naranjas son secuencias en las que la θ de esa ronda no llegó a la mejor energía.')

c1, c2, c3 = st.columns(3)
with c1:
    ficha('Ronda 1 · pesos iguales', 'La brillante',
          'θ₁ consigue la mejor pérdida media del juego (0.31) pero falla 2 secuencias.')
with c2:
    ficha('Ronda 2 · vaivén', 'La temeraria',
          'Esos 2 fallos aún pesan poco, y θ₂ arriesga más: rapidísima en 30, pero falla 11.')
with c3:
    ficha('Rondas 3–10', 'La prudente',
          'El peso se carga sobre los fallos y el afinador cambia de táctica: ya no vuelve a fallar ninguna.')
st.markdown('')

rondas_df = pd.DataFrame([dict(ronda=t, valor=rd['valor'],
                               efectivas=math.exp(-sum(p * math.log(p) for p in rd['p'] if p > 0)))
                          for t, rd in enumerate(H['rondas'], start=1)])
linea = alt.Chart(rondas_df).mark_line(color=AZUL, strokeWidth=2, point=alt.OverlayMarkDef(size=50)).encode(
    x=alt.X('ronda:Q', title='Ronda', axis=alt.Axis(tickMinStep=1)),
    y=alt.Y('valor:Q', title='Nota del examen (pérdida ponderada)', scale=alt.Scale(domain=[0.25, 0.55])),
    tooltip=['ronda', alt.Tooltip('valor:Q', format='.4f')])
empate = alt.Chart(pd.DataFrame(dict(y=[0.5]))).mark_rule(color=GRIS, strokeDash=[4, 4]).encode(y='y:Q')
st.altair_chart((empate + linea).properties(height=230), width='stretch')
st.caption('Sube hasta casi 0.5: el examinador va encontrando dónde nadie mejora a la de libro.')
linea = alt.Chart(rondas_df).mark_line(color=AZUL, strokeWidth=2, point=alt.OverlayMarkDef(size=50)).encode(
    x=alt.X('ronda:Q', title='Ronda', axis=alt.Axis(tickMinStep=1)),
    y=alt.Y('efectivas:Q', title='Secuencias que «mira» el examinador', scale=alt.Scale(domain=[0, N + 2])),
    tooltip=['ronda', alt.Tooltip('efectivas:Q', title='número efectivo', format='.1f')])
tope = alt.Chart(pd.DataFrame(dict(y=[N]))).mark_rule(color=GRIS, strokeDash=[4, 4]).encode(y='y:Q')
st.altair_chart((tope + linea).properties(height=230), width='stretch')
st.caption('Número efectivo de secuencias, $e^{\\text{entropía}}$: de 41 baja a unas 21. El examinador se '
           'concentra, pero no se obsesiona con dos o tres.')

with st.expander('Tabla de las rondas'):
    filas = []
    for t, rd in enumerate(H['rondas'], start=1):
        l = np.array(rd['l'])
        filas.append({'Ronda': t, 'Nota': round(rd['valor'], 4), 'Media': round(float(l.mean()), 3),
                      'Peor': round(float(l.max()), 3), 'Fallos': int((l >= 1).sum()),
                      **{k: round(rd['cfg'][k], 2) for k in NOMBRES}})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width='stretch')

# ---------------------------------------------------------------- garantías
st.markdown('### Lo que dice la teoría')
st.markdown('El **teorema minimax** (von Neumann) asegura que el juego tiene un **valor** $v$: la pérdida más baja '
            'que el afinador puede garantizarse aunque el examinador vea su jugada. Hedge se acerca a ese valor sin '
            'calcular el equilibrio exacto, que sería carísimo.')
m1, m2, m3 = st.columns(3)
m1.metric('Valor del juego', '0.495', help='Promedio de la nota en las rondas 6 a 10, cuando el juego ya se asentó.')
m2.metric('Arrepentimiento del examinador', '0.134', help='Cuánto peor le fue que al mejor examen fijo en '
          'retrospectiva, por ronda. La teoría garantiza que no pasa de √(ln N / 2T).')
m3.metric('Margen de la teoría', '0.431', help='√(ln 41 / 20). Con solo 10 rondas es holgado.')
st.markdown(
    """
- El valor ≈ 0.5 era lo esperable: en **5 secuencias** ninguna θ consigue ser más rápida que la de libro, y ahí el
  examinador se asegura un empate. Al final esas 5 se llevan el 54 % del peso.
- La configuración **robusta** es la de las rondas 9–10: su peor pérdida es 0.5, es decir, nunca es más lenta que la de
  libro (aunque tampoco mucho más rápida). Sortear al azar entre las 10 θ, que es lo que garantiza la teoría, sería
  peor (0.6), porque arrastra los fallos de las dos primeras rondas.
"""
)

# ---------------------------------------------------------------- examen final
st.markdown('### El examen final: secuencias nuevas')
st.markdown('**Hipótesis:** la configuración robusta se defenderá mejor con secuencias que nadie vio, aunque en '
            'entrenamiento tenga peor promedio. Se comparan cuatro, todas con paridad de la cadena entera y `r4` = 2, '
            'en las 40 secuencias de prueba que la de libro resuelve.')
final = pd.DataFrame([
    ('De libro', 0.500, 0.500, 0.500, 0.500, 0, 1.00),
    ('CMA-ES (G2)', 0.485, 0.500, 0.477, 0.500, 0, 0.90),
    ('θ₁, la brillante', 0.315, 1.000, 0.262, 0.500, 0, 0.30),
    ('θ robusta', 0.481, 0.500, 0.469, 0.500, 0, 0.86),
], columns=['Configuración', 'Media (entr.)', 'Peor (entr.)', 'Media (prueba)', 'Peor (prueba)', 'Fallos (prueba)',
            'Nodos ÷ libro (prueba)'])
st.dataframe(final, hide_index=True, width='stretch')
st.markdown(
    """
**La hipótesis no se cumple.** θ₁ no se hunde con secuencias nuevas: no falla ninguna, su peor pérdida empata con la
robusta y gasta en promedio **3.3 veces menos nodos** que la de libro (la robusta, solo 1.16 veces menos). En este
banco, el sobreajuste no era el problema que se suponía: el estudiante brillante también aprobó el examen final.
"""
)
st.caption('Precaución: 0 fallos en 40 solo permite decir, con un 95 % de confianza, que la tasa de fallos de θ₁ está '
           'por debajo de ~7.5 % (regla del tres: 3/40). Para distinguir un 5 % de un 0 % harían falta cientos de '
           'secuencias.')

# ---------------------------------------------------------------- qué señaló
st.markdown('### ¿Encontró un punto débil, o preguntas sueltas?')
ref = {b['sec']: b for b in banco()}
pf = H['p_final']
izq, der = st.columns(2, gap='large')
for col, titulo, idx in ((izq, 'Las 4 con más peso', orden[:4]), (der, 'Las 4 con menos peso', orden[-4:][::-1])):
    with col:
        st.markdown(f'**{titulo}**')
        for i in idx:
            s = H['banco'][i]
            svg(dibujo.cinta(s, tam=18))
            st.caption(f'Peso {pf[i]:.1%} · {len(s)} bolitas · {ref[s]["nodos_base"]:,} nodos para la de libro'
                       .replace(',', ' '))
st.markdown(
    """
**Preguntas sueltas.** Las de más peso son las que falló alguna θ al principio y en las que después **nadie mejora**
a la de libro, así que el fallo nunca se compensa. Dos de ellas son cortas y baratas (64 y 81 nodos): si la de libro ya
las resuelve casi sin buscar, nadie puede ser diez veces más rápido. Eso dice más de la forma de medir que del buscador.
"""
)
corr = pd.DataFrame(dict(rasgo=['Longitud', 'Fracción de H', 'Desbalance par–impar', 'Nodos de la de libro'],
                         rho=[-0.20, -0.19, 0.17, -0.32]))
barras = alt.Chart(corr).mark_bar(color=GRIS, cornerRadiusEnd=4, height=16).encode(
    x=alt.X('rho:Q', title='Correlación de rangos con el peso final', scale=alt.Scale(domain=[-1, 1])),
    y=alt.Y('rasgo:N', title=None, sort=None, axis=alt.Axis(labelLimit=240)), tooltip=['rasgo', alt.Tooltip('rho:Q', title='ρ de Spearman')])
cero = alt.Chart(pd.DataFrame(dict(x=[0]))).mark_rule(color=TINTA_2).encode(x='x:Q')
st.altair_chart((barras + cero).properties(height=alt.Step(34)), width='stretch')
st.caption('Ningún rasgo de la secuencia explica bien el peso (todas las correlaciones están cerca de 0). La más '
           'marcada, y aún en el límite del azar, es que el peso tiende a irse a las secuencias baratas.')
st.caption('Límites: una sola corrida con una semilla, 10 rondas y un banco pequeño (41 + 40 secuencias).')

navegacion('paginas/adversario.py')
