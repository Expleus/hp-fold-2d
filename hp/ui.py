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
