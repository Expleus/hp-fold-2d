"""Piezas de interfaz compartidas por todas las páginas."""
import json
from pathlib import Path

import streamlit as st

from .motor import CONFIG_ACTUAL, ConfigHP, Resultado, a_estrella, optimo_exhaustivo

RAIZ = Path(__file__).resolve().parent.parent

# Colores de las gráficas (paleta categórica validada, en orden fijo).
AZUL, NARANJA, AQUA, AMARILLO = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
GRIS, GRIS_CLARO, TINTA_2 = '#898781', '#c3c2b7', '#52514e'

CSS = """
<style>
.block-container {max-width: 1080px; padding-top: 2.2rem;}
h1 {font-weight: 700; letter-spacing: -0.02em;}
h2, h3 {letter-spacing: -0.01em;}
.bajada {font-size: 1.12rem; color: #52514e; margin: -0.4rem 0 1.4rem 0; line-height: 1.55;}
.idea {border-left: 4px solid #2a78d6; background: #f3f7fd; padding: 0.75rem 1rem; border-radius: 0 8px 8px 0;
       margin: 0.6rem 0 1rem 0; color: #1d1c1a;}
.idea b.t {display:block; font-size: 0.78rem; text-transform: uppercase; letter-spacing: .06em; color:#2a78d6;
           margin-bottom: .15rem;}
.aviso {border-left: 4px solid #eda100; background: #fdf8ec; padding: 0.7rem 1rem; border-radius: 0 8px 8px 0;
        margin: 0.6rem 0 1rem 0;}
.ficha {border: 1px solid #e1e0d9; border-radius: 10px; padding: .9rem 1rem; height: 100%; background: #fff;}
.ficha .k {font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; color: #898781;}
.ficha .v {font-size: 1.05rem; font-weight: 600; margin: .1rem 0 .3rem 0;}
.ficha p {margin: 0; color: #52514e; font-size: .95rem;}
.etiqueta {display:inline-block; padding: .05rem .5rem; border-radius: 99px; font-size: .8rem; font-weight: 600;
           background: #eeede8; color: #52514e; margin-right: .3rem;}
.ref {padding-left: 2em !important; text-indent: -2em; margin: 0 0 .55rem 0; color: #1d1c1a; line-height: 1.5;}
.mono {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .04em;}
[data-testid="stMarkdownContainer"]:has(> .eq) {overflow: visible !important;}
.eq {position: relative; margin: 0; padding: .05rem 1.9rem .05rem .4rem; border-radius: 10px; cursor: help;
     transition: background-color .12s;}
.eq:hover, .eq:focus-within {background: #f5f4f0; outline: none;}
.eq::after {content: '?'; position: absolute; top: 50%; right: .6rem; transform: translateY(-50%); width: 1.15rem;
            height: 1.15rem; border-radius: 50%; border: 1px solid #c3c2b7; color: #898781; font-size: .72rem;
            font-weight: 600; line-height: 1.1rem; text-align: center;}
.eq:hover::after, .eq:focus-within::after {border-color: #2a78d6; color: #2a78d6;}
.eq .katex-display {margin: .55rem 0; overflow-x: auto; overflow-y: hidden;}
.eq-tip {display: none; position: absolute; z-index: 1000; top: calc(100% - .2rem); left: 0; right: 0;
         margin: 0 auto; width: fit-content; max-width: min(40rem, 100%); background: #fff; color: #1d1c1a;
         border: 1px solid #e1e0d9; border-radius: 10px; box-shadow: 0 10px 28px rgba(29, 28, 26, .14);
         padding: .65rem .95rem; font-size: .9rem; line-height: 1.45; text-align: left; cursor: auto;}
.eq:hover .eq-tip, .eq:focus-within .eq-tip {display: block;}
.eq-tip p {margin: 0 0 .4rem 0 !important; color: #52514e; font-size: .9rem !important;}
.eq-tip ul {margin: 0 !important; padding-left: 1.1rem;}
.eq-tip li {margin: .12rem 0 !important; font-size: .9rem !important;}
.eq-tip li p {margin: 0 !important; color: #1d1c1a;}
[data-testid="stMetricValue"] {font-size: 1.6rem;}
</style>
"""


def estilo():
    st.html(CSS)


def encabezado(titulo, bajada):
    st.title(titulo)
    st.markdown(f'<p class="bajada">{bajada}</p>', unsafe_allow_html=True)


def idea(texto, titulo='La idea'):
    st.markdown(f'<div class="idea"><b class="t">{titulo}</b>{texto}</div>', unsafe_allow_html=True)


def aviso(texto):
    st.markdown(f'<div class="aviso">{texto}</div>', unsafe_allow_html=True)


def ecuacion(latex, simbolos, nota=None):
    """Ecuación en bloque. Al pasar el mouse por encima (o tocarla) aparece qué es cada símbolo.

    simbolos: lista de (símbolo en LaTeX, descripción en Markdown); nota: frase opcional sobre la ecuación entera.
    Las líneas en blanco alrededor del HTML hacen que el Markdown de dentro (y su LaTeX) se siga interpretando."""
    filas = '\n'.join(f'- ${s}$ — {d}' for s, d in simbolos)
    nota = f'{nota}\n\n' if nota else ''
    st.markdown(f'<div class="eq" tabindex="0">\n\n$$\n{latex}\n$$\n\n<div class="eq-tip">\n\n{nota}{filas}\n\n'
                '</div></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- reproducir
# Un reproductor es un st.fragment: mientras suena se vuelve a ejecutar solo cada `segundos` y avanza un paso el
# slider `clave`. Solo los ticks del reloj avanzan; las ejecuciones completas y los clics marcan `_quieto`.

def reproduciendo(clave):
    return st.session_state.get(f'{clave}_play', False)


def quieto(clave):
    """La próxima ejecución del fragmento no debe avanzar (la causó un clic, no el reloj)."""
    st.session_state[f'{clave}_quieto'] = True


def fragmento(clave, segundos=0.8):
    """Decorador del reproductor: un fragmento que se repite solo mientras `clave` se reproduce."""
    quieto(clave)
    return st.fragment(run_every=segundos if reproduciendo(clave) else None)


def avanzar(clave, total):
    """Al principio del fragmento, antes de crear el slider `clave`. Al llegar al final se detiene."""
    st.session_state.setdefault(clave, 1)
    if st.session_state.pop(f'{clave}_quieto', False) or not reproduciendo(clave):
        return
    st.session_state[clave] = min(st.session_state[clave] + 1, total)
    if st.session_state[clave] >= total:
        st.session_state[f'{clave}_play'] = False
        st.rerun()  # página entera: así el fragmento deja de repetirse y el botón vuelve a «Reproducir»


def _alternar(clave, total):
    st.session_state[f'{clave}_play'] = not reproduciendo(clave)
    if reproduciendo(clave) and st.session_state.get(clave, 1) >= total:
        st.session_state[clave] = 1  # si ya estaba al final, vuelve a empezar
    quieto(clave)


def boton_reproducir(clave, total, donde=st, **kw):
    activo = reproduciendo(clave)
    if donde.button('Pausa' if activo else 'Reproducir', icon=':material/pause:' if activo else ':material/play_arrow:',
                    key=f'{clave}_btn', type='primary', on_click=_alternar, args=(clave, total), **kw):
        st.rerun()  # el intervalo del fragmento se fija al dibujar la página entera


def ficha(clave, valor, texto):
    st.markdown(f'<div class="ficha"><div class="k">{clave}</div><div class="v">{valor}</div><p>{texto}</p></div>',
                unsafe_allow_html=True)


def svg(codigo):
    # st.html no pinta SVG en stlite (deja el contenedor vacío); st.markdown sí.
    st.markdown(codigo.replace('\n', ' '), unsafe_allow_html=True)


def siguiente(ruta, texto):
    st.divider()
    _, der = st.columns([3, 2])
    der.page_link(ruta, label=f'Siguiente: {texto}', icon=':material/arrow_forward:', width='stretch')


@st.cache_data
def datos(nombre):
    with open(RAIZ / 'datos' / nombre, encoding='utf-8') as f:
        return json.load(f)


def banco():
    return datos('banco.json')


def precalculado(aa, cfg, regla, tope):
    """Resultado guardado de A* difuso para los péptidos de ejemplo con la configuración de libro (r4 = 1 o 2).
    Si el tope pedido no alcanza, devuelve lo que habría dado la búsqueda: un tope agotado."""
    guardado = datos('peptidos.json').get(f'{aa}|{regla}|{cfg.r4}')
    if guardado is None or tuple(cfg) != tuple(CONFIG_ACTUAL._replace(r4=cfg.r4)):
        return None
    r = Resultado(**guardado)
    return r if r.nodos <= tope else Resultado(None, None, tope, 'tope')


def presets():
    """Configuraciones con nombre: la de libro, la que encontró CMA-ES (G1) y la robusta del adversario."""
    g1 = next(c['cfg'] for c in datos('cmaes.json')['corridas'] if c['global_'] and c['r4'] == 1)
    return {'De libro': CONFIG_ACTUAL._asdict(), 'Ajustada por CMA-ES (G1)': g1,
            'Robusta (adversario)': datos('hedge.json')['rondas'][8]['cfg']}


def referencia(sec):
    """Energía de referencia del banco, si la secuencia está en él."""
    for b in banco():
        if b['sec'] == sec:
            return b['E']
    return None


@st.cache_data(max_entries=256, show_spinner=False)
def resolver(sec, cfg_tupla=tuple(CONFIG_ACTUAL), tope=300_000, mu=None, regla='min'):
    r = a_estrella(sec, ConfigHP(*cfg_tupla), tope_nodos=tope, mu=list(mu) if mu else None, regla=regla)
    return r


@st.cache_data(max_entries=64, show_spinner=False)
def resolver_con_traza(sec, cfg_tupla=tuple(CONFIG_ACTUAL), max_traza=600, tope=200_000):
    traza = []
    r = a_estrella(sec, ConfigHP(*cfg_tupla), tope_nodos=tope, traza=traza, max_traza=max_traza)
    return r, traza


@st.cache_data(max_entries=256, show_spinner=False)
def optimo(sec, mu=None, regla='min'):
    """Óptimo exacto por enumeración (solo cadenas cortas)."""
    return optimo_exhaustivo(sec, mu=list(mu) if mu else None, regla=regla)


def limpiar(texto):
    return ''.join(c for c in texto.upper() if not c.isspace())


def secuencia_hp(etiqueta, opciones, key, n_min=4, n_max=30, ayuda=None):
    """Selector de secuencia HP: lista de ejemplos y, además, se puede escribir una nueva."""
    valor = st.selectbox(etiqueta, opciones, key=key, accept_new_options=True,
                         help=ayuda or 'Elige un ejemplo o escribe tu propia secuencia de H y P.')
    sec = limpiar(valor or '')
    if not sec or set(sec) - {'H', 'P'}:
        st.error('La secuencia solo puede tener las letras H y P.')
        st.stop()
    if not n_min <= len(sec) <= n_max:
        st.error(f'Usa entre {n_min} y {n_max} monómeros (tiene {len(sec)}).')
        st.stop()
    return sec
