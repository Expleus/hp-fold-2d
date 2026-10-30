import altair as alt
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.difuso import conformaciones_posibles, formato_grande
from hp.motor import contactos, reconstruir_coordenadas
from hp.ui import AZUL, GRIS, encabezado, ficha, idea, optimo, referencia, resolver, secuencia_hp, siguiente, svg

encabezado('El problema: plegar una cadena',
           'Una proteína es una cadena de aminoácidos que, en agua, se dobla sola hasta una forma concreta, y esa '
           'forma decide lo que hace. El modelo HP es la versión más simple que conserva la idea central.')

# ---------------------------------------------------------------- el modelo
st.markdown('### El modelo en tres reglas')
c1, c2, c3 = st.columns(3)
with c1:
    ficha('1 · Dos tipos de bolita', 'H y P',
          '<b style="color:#eb6834">H</b>, hidrofóbica: rehúye el agua, como el aceite. '
          '<b>P</b>, polar: se lleva bien con el agua.')
with c2:
    ficha('2 · Una cuadrícula', 'Sin pisarse',
          'Cada bolita ocupa una casilla, las consecutivas van en casillas vecinas y nunca dos en la misma.')
with c3:
    ficha('3 · Un puntaje', 'Energía = − contactos',
          'Cada par H–H vecino en la cuadrícula (pero no seguido en la cadena) es un contacto y resta 1.')

idea('Como gotas de aceite en agua: las H tienden a juntarse en el centro y dejan las P por fuera. '
     'La mejor forma es la que <b>más contactos H–H</b> consigue, es decir, la de <b>menor energía</b>.')

# ---------------------------------------------------------------- pliégala tú
st.markdown('### Pliégala tú')
st.markdown('Las instrucciones son **relativas**, como al conducir: *recto*, *a la izquierda* o *a la derecha* '
            'según hacia dónde mira la última bolita. Las dos primeras quedan fijas, mirando hacia arriba.')

OPCIONES = ['HPPHPPHHPH', 'PPHHHPHPPH', 'HHPHPHHPPH', 'PHPHPPHHPPH', 'HHPPHHPPHPHH', 'HPHPPHHPHPPHPHHPPHPH']
sec = secuencia_hp('Secuencia', OPCIONES, key='pl_sec', n_max=24)
if st.session_state.get('pl_para') != sec:
    st.session_state.pl_para, st.session_state.pl_movs = sec, ''
movs = st.session_state.pl_movs
coords = reconstruir_coordenadas(movs)
ocupadas = set(coords)
n = len(sec)
completa = len(coords) == n
NOMBRE = {'L': 'Izquierda', 'F': 'Recto', 'R': 'Derecha'}
libres = {p: dibujo.siguiente_celda(movs, p) not in ocupadas for p in 'LFR'} if not completa else {}


def mover(p):
    st.session_state.pl_movs += p


def deshacer():
    st.session_state.pl_movs = st.session_state.pl_movs[:-1]


def reiniciar():
    st.session_state.pl_movs = ''


izq, der = st.columns([1, 1], gap='medium')
with der:
    b1, b2, b3 = st.columns(3)
    for col, p, icono in ((b1, 'L', ':material/turn_left:'), (b2, 'F', ':material/straight:'),
                          (b3, 'R', ':material/turn_right:')):
        col.button(NOMBRE[p], icon=icono, on_click=mover, args=(p,), width='stretch',
                   disabled=completa or not libres.get(p, False), key=f'pl_{p}')
    b4, b5 = st.columns(2)
    b4.button('Deshacer', icon=':material/undo:', on_click=deshacer, disabled=not movs, width='stretch')
    b5.button('Reiniciar', icon=':material/restart_alt:', on_click=reiniciar, disabled=not movs,
              width='stretch')

    e = -len(contactos(coords, sec=sec[:len(coords)]))
    if n <= 14:
        e_opt, ayuda = optimo(sec)[0], 'Calculado probando todas las formas.'
    else:
        e_opt = referencia(sec)
        e_opt, ayuda = (e_opt, 'Referencia del banco.') if e_opt is not None else \
            (resolver(sec).energia, 'La mejor que encuentra A* (siguiente página).')
    m1, m2 = st.columns(2)
    m1.metric('Tu energía', f'{e:g}', help='−1 por cada contacto H–H (las líneas punteadas).')
    m2.metric('Mejor posible', f'{e_opt:g}', help=ayuda)
    st.progress(len(coords) / n, text=f'{len(coords)} de {n} bolitas colocadas')
    if completa:
        if e_opt is not None and e <= e_opt:
            st.success('¡Forma óptima! No hay ninguna con más contactos.', icon=':material/emoji_events:')
        else:
            st.info('Cadena completa. ¿Puedes conseguir más contactos? Deshaz unos pasos y prueba otra ruta.',
                    icon=':material/lightbulb:')
    elif not any(libres.values()):
        st.warning('Te encerraste: no queda ninguna casilla libre al lado. Deshaz un paso.', icon=':material/block:')
    st.markdown(f'Movimientos: <span class="mono">{movs or "—"}</span>', unsafe_allow_html=True)

with izq:
    cand = [] if completa else [dict(paso=p, motivo='ok', texto=NOMBRE[p]) for p in 'LFR' if libres[p]]
    svg(dibujo.conformacion(sec, movs, candidatos=cand, celda=46, ancho_max=460))
    if not completa:
        svg(dibujo.cinta(sec, resaltar=(len(coords),)))
        st.caption(f'La bolita {len(coords)} (marcada en azul) es la siguiente en colocarse.')

# ---------------------------------------------------------------- explosión combinatoria
st.markdown('### ¿Por qué no probar todas las formas?')
st.markdown('Porque son demasiadas. Cada bolita nueva tiene hasta tres opciones, así que el número de formas '
            'crece de manera **exponencial**: casi se multiplica por 2.6 con cada bolita que se añade.')

filas = []
for k in range(4, 32):
    filas.append(dict(n=k, serie='Todas las instrucciones', formas=(3 ** (k - 2) + 1) // 2))
    filas.append(dict(n=k, serie='Sin chocar consigo mismas', formas=conformaciones_posibles(k)))
df = pd.DataFrame(filas)
df['texto'] = df['formas'].map(formato_grande)
color = alt.Color('serie:N', title=None, legend=alt.Legend(orient='top', labelLimit=320),
                  scale=alt.Scale(domain=['Sin chocar consigo mismas', 'Todas las instrucciones'],
                                  range=[AZUL, GRIS]))
base = alt.Chart(df).encode(
    x=alt.X('n:Q', title='Número de bolitas (n)', scale=alt.Scale(domain=[4, 31])),
    y=alt.Y('formas:Q', title='Formas distintas (escala logarítmica)', scale=alt.Scale(type='log'),
            axis=alt.Axis(format='~s')),
    color=color,
    tooltip=[alt.Tooltip('n:Q', title='n'), alt.Tooltip('serie:N', title='Serie'),
             alt.Tooltip('texto:N', title='Formas')])
grafica = base.mark_line(strokeWidth=2) + base.mark_point(size=40, filled=True, opacity=0.9)

izq, der = st.columns([3, 2], gap='large')
with izq:
    st.altair_chart(grafica.properties(height=320), width='stretch')
with der:
    k = st.slider('Longitud de la cadena', 10, 31, 30)
    formas = conformaciones_posibles(k)
    seg = formas / 1e6

    def duracion(s):
        for lim, div, nombre in ((60, 1, 'segundos'), (3600, 60, 'minutos'), (86400, 3600, 'horas'),
                                 (86400 * 365, 86400, 'días')):
            if s < lim:
                return f'{s / div:.1f} {nombre}'.replace('.', ',')
        return f'{s / (86400 * 365):.1f} años'.replace('.', ',')

    st.metric('Formas sin choques', formato_grande(formas))
    st.metric('Revisando un millón por segundo', duracion(seg))
    st.caption('Las proteínas reales tienen cientos de aminoácidos y viven en 3D: probarlo todo es imposible. '
               'Hace falta buscar con inteligencia.')

with st.expander('De dónde salen estos números'):
    st.markdown(
        r"""
- **Todas las instrucciones**: después de las dos bolitas fijas, cada una elige entre recto, izquierda o derecha:
  $3^{n-2}$ cadenas. Se divide entre 2 porque cada forma tiene una gemela en espejo con la misma energía.
- **Las que no chocan**: son los *caminos autoevitantes* de $n-1$ pasos en la red cuadrada, $c_{n-1}$.
  No hay fórmula cerrada; los valores exactos están tabulados (OEIS A001411). Fijar el primer paso divide
  entre 4 (las 4 rotaciones) y quitar el espejo, entre 2: $\;(c_{n-1}/4 + 1)/2$.
- Para cadenas largas $c_N \sim \mu^N$ con $\mu \approx 2.638$: por eso el factor de crecimiento «casi 2.6».
"""
    )

siguiente('paginas/busqueda.py', 'Cómo busca A*')
