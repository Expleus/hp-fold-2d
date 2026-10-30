import math

import altair as alt
import cma
import numpy as np
import pandas as pd
import streamlit as st

from hp.motor import CONFIG_ACTUAL, LIMITES, NOMBRES, ConfigHP, a_estrella
from hp.ui import (AQUA, AZUL, GRIS, NARANJA, TINTA_2, avanzar, controles, datos, ecuacion, encabezado,
                   fragmento, idea, presets, quieto, navegacion)

encabezado('Ajuste automático con CMA-ES',
           'La heurística y las reglas tienen seis números que hasta ahora se eligieron «a mano». ¿Y si hay valores '
           'mejores? En vez de razonarlos uno a uno, se deja que un algoritmo evolutivo los busque.')

# ---------------------------------------------------------------- perillas
st.markdown('### Seis perillas y dos interruptores')
st.markdown(
    """
| Perilla | Qué controla | De libro |
|---|---|---|
| $a_b$ | Cuánto promete cada H pendiente (cota básica) | 2 |
| $a_p$ | Peso del emparejamiento par–impar (cota de paridad) | 2 |
| $c$ | Término fijo de la cota de paridad (los extremos) | 2 |
| $a_g$ | Cuánto se descuenta de la paridad lo ya conseguido | 1 |
| $m_3$ | Cuánto espacio libre exige R3 | 1 |
| $w$ | Cuánto pesa la estimación en $f = g + w\\,h$ | 1 |

Además, dos interruptores: calcular la paridad sobre la cadena **entera** o solo sobre **lo que falta**, y el
umbral de R4 (`r4` = 0 la apaga, 2 es la versión más estricta).
"""
)

# ---------------------------------------------------------------- pruébalas
CONJUNTO = ['HHPHPPPPHH', 'PHHPPPHHPPHP', 'PHHPHHPHHHPPHH', 'PHPHHPHPHPHHPH', 'PHPHHHHPPPHHH',
            'HPHHPPHHPPHHPPHHPPPH', 'HHPHPHPPPHHHPPPHPPHPH', 'PPPHHHPPHPHPHHHPPHPPPP']
TOPE = 60_000
corridas = datos('cmaes.json')['corridas']
PRESETS = presets()


def cargar():
    for k, v in PRESETS[st.session_state.cm_preset].items():
        st.session_state[f'cm_{k}'] = v if k in ('global_', 'r4') else round(float(v), 2)


if 'cm_a_b' not in st.session_state:
    st.session_state.cm_preset = 'De libro'
    cargar()


@st.cache_data(max_entries=128, show_spinner='Plegando las 8 secuencias…')
def examen(cfg_tupla):
    cfg = ConfigHP(*cfg_tupla)
    filas = []
    for s in CONJUNTO:
        r = a_estrella(s, cfg, tope_nodos=TOPE)
        filas.append(dict(sec=s, energia=r.energia if r.estado == 'ok' else None, nodos=r.nodos, estado=r.estado))
    return filas


def resumen(filas):
    ref = {b['sec']: b['E'] for b in datos('banco.json')}
    err, cost = [], []
    for f in filas:
        if f['estado'] != 'ok':
            err.append(1.0)
            cost.append(math.log10(TOPE))
        else:
            err.append(max((f['energia'] - ref[f['sec']]) / abs(ref[f['sec']]), 0.0))
            cost.append(math.log10(f['nodos'] + 1))
    return float(np.mean(err)), float(np.mean(cost)), sum(e == 0 for e in err), err


st.markdown('#### Pruébalas tú')
st.caption('Mueve las perillas y pulsa «Probar»: el buscador pliega 8 secuencias del conjunto de prueba y se compara '
           'con la configuración de libro.')
with st.container(border=True):
    st.radio('Partir de', list(PRESETS), key='cm_preset', horizontal=True, on_change=cargar)
    with st.form('cm_form', border=False):
        cols = st.columns(3)
        LATEX = dict(a_b='$a_b$', a_p='$a_p$', c='$c$', a_g='$a_g$', m3='$m_3$', w='$w$')
        ayudas = dict(a_b='Cota básica', a_p='Cota de paridad', c='Término fijo', a_g='Descuento de lo conseguido',
                      m3='Espacio exigido por R3', w='Peso de la estimación')
        for i, (k, (lo, hi)) in enumerate(zip(NOMBRES, LIMITES)):
            cols[i % 3].slider(f'{LATEX[k]} · {ayudas[k]}', float(lo), float(hi), step=0.01, key=f'cm_{k}')
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.toggle('Paridad de la cadena entera', key='cm_global_')
        c2.select_slider('Umbral de R4', [0, 1, 2], key='cm_r4')
        enviado = c3.form_submit_button('Probar', icon=':material/play_arrow:', width='stretch', type='primary')

cfg = ConfigHP(*(st.session_state[f'cm_{k}'] for k in NOMBRES), st.session_state.cm_global_, st.session_state.cm_r4)
mia, base = examen(tuple(cfg)), examen(tuple(CONFIG_ACTUAL))
e_m, c_m, a_m, err_m = resumen(mia)
e_b, c_b, a_b_, err_b = resumen(base)
m1, m2, m3 = st.columns(3)
m1.metric('Error medio', f'{e_m:.3f}', delta=f'{e_m - e_b:+.3f}' if abs(e_m - e_b) > 1e-9 else None,
          delta_color='inverse', help='Cuánto le falta, en promedio, para llegar a la mejor energía (0 = perfecto).')
m2.metric('Costo', f'{c_m:.2f}', delta=f'{c_m - c_b:+.2f}' if abs(c_m - c_b) > 1e-9 else None, delta_color='inverse',
          help='Promedio de log₁₀(nodos expandidos): +1 significa diez veces más trabajo.')
m3.metric('Aciertos', f'{a_m} de {len(CONJUNTO)}', delta=a_m - a_b_ if a_m != a_b_ else None)
tabla = pd.DataFrame([{'Secuencia': f['sec'], 'Energía': f['energia'], 'Nodos': f['nodos'],
                       'Nodos (libro)': b['nodos'], '¿Óptima?': '✓' if e == 0 else ('tope' if f['estado'] != 'ok' else '✗')}
                      for f, b, e in zip(mia, base, err_m)])
with st.expander('Ver secuencia por secuencia'):
    st.dataframe(tabla, hide_index=True, width='stretch')

idea('Hay que equilibrar dos cosas que tiran en sentidos opuestos: <b>acertar</b> (llegar a la mejor energía) y '
     '<b>gastar poco</b> (expandir pocos nodos). Y las perillas interactúan: subir una puede compensar bajar otra.')

# ---------------------------------------------------------------- cómo funciona
st.markdown('### Cómo busca CMA-ES')
st.markdown('**CMA-ES** (*Covariance Matrix Adaptation Evolution Strategy*) no necesita derivadas ni fórmulas: solo '
            'probar puntos y saber **cuál es mejor que cuál**. Así se ve en un problema de dos perillas, donde el '
            'fondo indica lo bueno (claro) o malo (oscuro) de cada combinación:')


def valle(x, y):
    a, b = x - 1.5, y + 1.0
    u, v = 0.825 * a - 0.565 * b, 0.565 * a + 0.825 * b
    return u ** 2 + 20 * v ** 2


FUNCIONES = {
    'Valle inclinado': (valle, (-3.0, 3.0), (1.5, -1.0)),
    'Escalones': (lambda x, y: np.floor(valle(x, y) / 4) * 4, (-3.0, 3.0), (1.5, -1.0)),
    'Banana': (lambda x, y: (1 - x) ** 2 + 20 * (y - x ** 2) ** 2, (-3.0, -2.0), (1.0, 1.0)),
}
LAM, MU_, GENS = 8, 4, 40


@st.cache_data(show_spinner=False)
def demo(nombre):
    f, x0, _ = FUNCIONES[nombre]
    # Sin 'bounds': con límites, cma guarda la media y la covarianza en un espacio interno distinto del de los
    # puntos, y la elipse dibujada dejaría de ser la nube de la que salen.
    es = cma.CMAEvolutionStrategy(list(x0), 0.8, {'popsize': LAM, 'CMA_mu': MU_, 'seed': 7, 'verbose': -9})
    gens = []
    for _ in range(GENS):
        media, sigma, C = es.mean.copy(), float(es.sigma), np.array(es.C, dtype=float)
        X = es.ask()
        vals = [float(f(*x)) for x in X]
        orden = np.argsort(vals, kind='stable')
        gens.append(dict(media=media.tolist(), sigma=sigma, C=C.tolist(), X=np.array(X).tolist(), vals=vals,
                         elegidos=orden[:MU_].tolist()))
        es.tell(X, vals)
    return gens


@st.cache_data(show_spinner=False)
def fondo(nombre):
    f = FUNCIONES[nombre][0]
    paso = 8 / 48
    xs = np.arange(-4, 4, paso)
    filas = [dict(x=x, x2=x + paso, y=y, y2=y + paso, v=math.log10(1 + float(f(x + paso / 2, y + paso / 2))))
             for x in xs for y in xs]
    return pd.DataFrame(filas)


@fragmento('cm_gen', segundos=0.6)
def nube():
    avanzar('cm_gen', GENS)
    izq, der = st.columns([3, 2], gap='large')
    with der:
        nombre = st.segmented_control('Problema', list(FUNCIONES), default='Valle inclinado', key='cm_fun')
        nombre = nombre or 'Valle inclinado'
        g = st.slider('Generación', 1, GENS, key='cm_gen', on_change=quieto, args=('cm_gen',))
        controles('cm_gen', GENS, compacto=True)
        gens = demo(nombre)
        G = gens[g - 1]
        st.markdown(
            f"""
1. **Muestrear.** Se lanzan {LAM} puntos al azar desde una «nube» (la elipse azul).
2. **Ordenar.** Se evalúan y se ordenan. Solo importa el **orden**, no cuánto mejor es uno que otro.
3. **Moverse.** El centro de la nube (rombo naranja) se desplaza hacia los {MU_} mejores (puntos azules).
4. **Deformarse.** La nube se **estira** en la dirección en que se avanzó y se **encoge** cuando ya está cerca.
"""
        )
        st.caption(f'Tamaño de la nube en esta generación: σ = {G["sigma"]:.3f}. Mejor valor de la generación: '
                   f'{min(G["vals"]):.3g}.')
    with izq:
        fd = fondo(nombre)
        capa = alt.Chart(fd).mark_rect().encode(
            x=alt.X('x:Q', title='Perilla 1', scale=alt.Scale(domain=[-4, 4], nice=False)), x2='x2:Q',
            y=alt.Y('y:Q', title='Perilla 2', scale=alt.Scale(domain=[-4, 4], nice=False)), y2='y2:Q',
            color=alt.Color('v:Q', scale=alt.Scale(range=['#fbfaf7', '#9fb3cc']), legend=None), tooltip=alt.value(None))
        m = np.array(G['media'])
        S = (G['sigma'] ** 2) * np.array(G['C'])
        val, vec = np.linalg.eigh(S)
        t = np.linspace(0, 2 * np.pi, 80)
        pts = m[:, None] + 2 * vec @ (np.sqrt(np.maximum(val, 0))[:, None] * np.vstack([np.cos(t), np.sin(t)]))
        elipse = alt.Chart(pd.DataFrame(dict(x=pts[0], y=pts[1], o=range(80)))).mark_line(
            color=AZUL, strokeWidth=2, clip=True).encode(x='x:Q', y='y:Q', order='o:Q')
        X = np.array(G['X'])
        dfp = pd.DataFrame(dict(x=X[:, 0], y=X[:, 1], valor=G['vals'],
                                tipo=['elegido' if i in G['elegidos'] else 'descartado' for i in range(len(X))]))
        puntos = alt.Chart(dfp).mark_point(size=70, strokeWidth=2, clip=True).encode(
            x='x:Q', y='y:Q',
            color=alt.Color('tipo:N', scale=alt.Scale(domain=['elegido', 'descartado'], range=[AZUL, GRIS]),
                            legend=alt.Legend(orient='bottom', title=None)),
            fill=alt.Fill('tipo:N', scale=alt.Scale(domain=['elegido', 'descartado'], range=[AZUL, 'transparent']),
                          legend=None),
            tooltip=[alt.Tooltip('valor:Q', title='Valor', format='.3g')])
        camino = pd.DataFrame([dict(x=x[0], y=x[1], o=i) for i, x in enumerate(d['media'] for d in gens[:g])])
        rastro = alt.Chart(camino).mark_line(color=NARANJA, strokeWidth=1.5, opacity=0.6, clip=True).encode(
            x='x:Q', y='y:Q', order='o:Q')
        centro = alt.Chart(pd.DataFrame(dict(x=[m[0]], y=[m[1]]))).mark_point(
            shape='diamond', size=140, filled=True, color=NARANJA, stroke='white', strokeWidth=1.5, clip=True
        ).encode(x='x:Q', y='y:Q')
        meta = FUNCIONES[nombre][2]
        objetivo = alt.Chart(pd.DataFrame(dict(x=[meta[0]], y=[meta[1]]))).mark_point(
            shape='cross', size=90, color=TINTA_2, filled=True).encode(x='x:Q', y='y:Q')
        st.altair_chart((capa + objetivo + rastro + elipse + puntos + centro).properties(height=430),
                        width='stretch')


nube()

st.markdown(
    """
Fíjate en **Escalones**: el paisaje está hecho de mesetas planas, igual que la energía del modelo HP (que solo toma
valores enteros). Un método basado en pendientes se queda quieto en una meseta; CMA-ES no, porque solo necesita
ordenar y su nube sigue explorando. Por eso es una buena elección aquí.
"""
)

# ---------------------------------------------------------------- qué es mejor
st.markdown('### ¿Qué significa «mejor»?')
c1, c2 = st.columns(2, gap='large')
with c1:
    st.markdown(
        r"""
**Error**: cuánto se queda corta la energía encontrada respecto a la mejor conocida, en proporción:
"""
    )
    ecuacion(r'\text{error} = \operatorname{media}\;\max\!\left(\frac{E - E^\ast}{|E^\ast|},\, 0\right)',
             [(r'E', 'energía que encontró A* con la configuración, en una secuencia.'),
              (r'E^\ast', 'la mejor energía conocida para esa secuencia.'),
              (r'\frac{E - E^\ast}{|E^\ast|}', 'cuánto se quedó corta, como fracción: 0.25 es que le faltó un 25 % '
                                               'de los contactos.'),
              (r'\max(\cdot,\, 0)', 'si llega a la mejor energía, el error es 0 (nunca negativo).'),
              (r'\operatorname{media}', 'promedio sobre todas las secuencias del examen.')])
    st.markdown(
        r"""
**Costo**: el trabajo, en órdenes de magnitud: $\operatorname{media}\,\log_{10}(\text{nodos} + 1)$.
Si se agota el tope de 250 000 nodos, cuenta como error 1.
"""
    )
with c2:
    st.markdown(
        """
- **Primero acertar, después ahorrar.** Dos configuraciones se comparan por error; solo si empatan
  (diferencia < 0.001) decide el costo. Así no hay que inventar cuánto «vale» un nodo frente a un contacto.
- **Centinelas.** Cada candidata se prueba primero en 8 secuencias rápidas. Solo las 4 mejores (o las que no
  queden más de 0.10 por detrás) pasan al examen completo de 45. Ahorra mucho tiempo.
- **Entrenar y examinar por separado.** Hay 90 secuencias: 45 para ajustar y 45 que CMA-ES nunca ve, para
  comprobar que lo aprendido sirve con secuencias nuevas.
"""
        )
st.caption(f'Cada ajuste: {datos("cmaes.json")["lam"]} candidatas por generación, '
           f'{datos("cmaes.json")["generaciones"]} generaciones, una corrida por cada combinación de interruptores.')

# ---------------------------------------------------------------- resultados
st.markdown('### Resultados')
base = datos('cmaes.json')['base']


def etiqueta(c):
    return ('G' if c['global_'] else 'R') + str(c['r4'])


filas = [dict(nombre=etiqueta(c), paridad='cadena entera' if c['global_'] else 'lo que falta', r4=str(c['r4']),
              error=c['prueba']['error'], costo=c['prueba']['costo'], aciertos=c['prueba']['aciertos'],
              domina=c['domina']) for c in corridas]
df = pd.DataFrame(filas)
izq, der = st.columns([3, 2], gap='large')
with izq:
    bx, by = base['prueba']['error'], base['prueba']['costo']
    zona = alt.Chart(pd.DataFrame(dict(x=[-0.002], x2=[bx], y=[3.0], y2=[by]))).mark_rect(
        color=AZUL, opacity=0.06).encode(x='x:Q', x2='x2:Q', y='y:Q', y2='y2:Q')
    zona_txt = alt.Chart(pd.DataFrame(dict(x=[-0.001], y=[3.02]))).mark_text(
        align='left', color=AZUL, fontSize=11, fontWeight=600).encode(x='x:Q', y='y:Q',
                                                                      text=alt.value('mejor que la base en ambas'))
    puntos = alt.Chart(df).mark_point(size=110, filled=True, strokeWidth=2).encode(
        x=alt.X('error:Q', title='Error en el conjunto de prueba', scale=alt.Scale(domain=[-0.002, 0.046])),
        y=alt.Y('costo:Q', title='Costo (log₁₀ nodos)', scale=alt.Scale(domain=[3.0, 3.56])),
        color=alt.Color('r4:N', title='r4', scale=alt.Scale(domain=['0', '1', '2'], range=[AZUL, NARANJA, AQUA]),
                        legend=alt.Legend(orient='top')),
        shape=alt.Shape('paridad:N', title='Paridad de',
                        scale=alt.Scale(domain=['cadena entera', 'lo que falta'], range=['circle', 'square']),
                        legend=alt.Legend(orient='top')),
        tooltip=['nombre', 'paridad', 'r4', alt.Tooltip('error:Q', format='.4f'), alt.Tooltip('costo:Q', format='.3f'),
                 'aciertos'])
    nombres = alt.Chart(df).mark_text(dx=12, dy=-9, color=TINTA_2, fontWeight=600).encode(
        x='error:Q', y='costo:Q', text='nombre:N')
    b = alt.Chart(pd.DataFrame(dict(x=[bx], y=[by], t=['libro']))).mark_point(
        shape='cross', size=150, filled=True, color=GRIS).encode(x='x:Q', y='y:Q')
    bt = alt.Chart(pd.DataFrame(dict(x=[bx], y=[by]))).mark_text(dx=10, dy=12, color=GRIS, fontWeight=600).encode(
        x='x:Q', y='y:Q', text=alt.value('de libro'))
    st.altair_chart((zona + zona_txt + puntos + nombres + b + bt).properties(height=340), width='stretch')
    st.caption('G = paridad de la cadena entera, R = de lo que falta; el número es r4. Abajo a la izquierda es mejor.')
with der:
    st.dataframe(
        df.assign(error=df.error.round(4), costo=df.costo.round(3),
                  domina=df.domina.map({True: '✓', False: ''}))[['nombre', 'error', 'costo', 'aciertos', 'domina']]
        .rename(columns={'nombre': 'Combinación', 'error': 'Error', 'costo': 'Costo', 'aciertos': 'Aciertos (de 45)',
                         'domina': '✓'}),
        hide_index=True, width='stretch')
    st.caption(f"De libro: error {base['prueba']['error']:.4f}, costo {base['prueba']['costo']:.3f}, "
               f"{base['prueba']['aciertos']} aciertos. ✓ = mejor que la de libro en error y en costo.")

g1 = next(c for c in corridas if c['global_'] and c['r4'] == 1)
ahorro = 1 - 10 ** (g1['prueba']['costo'] - base['prueba']['costo'])
st.markdown(
    f"""
- **G1** (paridad de la cadena entera, `r4` = 1) gana a la configuración de libro en las dos cosas a la vez con
  secuencias que nunca vio: falla en 1 de 45 en vez de 5, y expande en torno a un **{ahorro:.0%} menos de nodos**
  (media geométrica).
- Las dos combinaciones con `r4` = 1 son las más certeras: la versión estricta de R4 (`r4` = 2) es la que más
  óptimos pierde, como ya se vio en la página de reglas.
- Las perillas ganadoras son **muy distintas entre sí** (por ejemplo, $a_p$ va de 0.9 a 2.7). Hay muchas maneras
  casi igual de buenas: el paisaje es un valle ancho y plano, no un pozo.
"""
)

with st.expander('Valores encontrados y convergencia'):
    st.dataframe(pd.DataFrame([{**{'Combinación': etiqueta(c)}, **{k: round(c['cfg'][k], 2) for k in NOMBRES}}
                               for c in corridas]), hide_index=True, width='stretch')
    conv = pd.DataFrame([dict(nombre=etiqueta(c), r4=str(c['r4']),
                              paridad='cadena entera' if c['global_'] else 'lo que falta',
                              gen=i + 1, error=e, costo=k) for c in corridas for i, (e, k) in enumerate(c['historia'])])
    enc = dict(x=alt.X('gen:Q', title='Generación'),
               color=alt.Color('r4:N', title='r4', scale=alt.Scale(domain=['0', '1', '2'],
                                                                 range=[AZUL, NARANJA, AQUA]),
                               legend=alt.Legend(orient='top')),
               strokeDash=alt.StrokeDash('paridad:N', title='Paridad de',
                                         scale=alt.Scale(domain=['cadena entera', 'lo que falta'],
                                                         range=[[1, 0], [5, 3]]), legend=alt.Legend(orient='top')),
               detail='nombre:N', tooltip=['nombre', 'gen', alt.Tooltip('error:Q', format='.4f'),
                                           alt.Tooltip('costo:Q', format='.3f')])
    c1, c2 = st.columns(2)
    c1.altair_chart(alt.Chart(conv).mark_line(strokeWidth=2, interpolate='step-after').encode(
        y=alt.Y('error:Q', title='Error (entrenamiento)'), **enc).properties(height=230), width='stretch')
    c2.altair_chart(alt.Chart(conv).mark_line(strokeWidth=2, interpolate='step-after').encode(
        y=alt.Y('costo:Q', title='Costo (entrenamiento)', scale=alt.Scale(zero=False)), **enc).properties(height=230),
        width='stretch')
    st.caption('Se muestra la mejor configuración encontrada hasta cada generación. El costo a veces sube: es el '
               'precio de bajar el error, que manda primero.')

navegacion('paginas/cmaes.py')
