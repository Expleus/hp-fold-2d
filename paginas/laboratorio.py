import json

import streamlit as st

from hp import dibujo
from hp.difuso import KYTE_DOOLITTLE, PEPTIDOS, a_hp, fraccion_h, grados_kd, presupuesto, rampa, veredicto
from hp.motor import LIMITES, NOMBRES, ConfigHP, grados_crisp, reconstruir_coordenadas
from hp.ui import encabezado, limpiar, optimo, precalculado, presets, referencia, resolver, navegacion, svg

encabezado('Laboratorio',
           'Todo junto y sin guion: elige una secuencia, una configuración del buscador y mira qué forma encuentra, '
           'cuánto le cuesta y si es la mejor.')

PRESETS = presets()
RAMPA = (0.15, 0.35)          # R0 difusa ajustada con el criterio «2 contactos o más»
PRESUPUESTO = (2_000, 300_000)
EJEMPLOS = {
    'HP': ['HPHPPHHPHPPHPHHPPHPH', 'HHPHPHPPPHHHPPPHPPHPH', 'HHPPHPPHPPHPPHPPHPPHPPHH', 'PPHHHPHPPH',
           'HPPPPHPPPPPPHP'],
    'Aminoácidos': [f'{k} · {v}' for k, v in PEPTIDOS.items()],
}


def cargar():
    for k, v in PRESETS[st.session_state.lab_preset].items():
        st.session_state[f'lab_{k}'] = v if k in ('global_', 'r4') else round(float(v), 2)


if 'lab_a_b' not in st.session_state:
    st.session_state.lab_preset = 'De libro'
    cargar()

izq, der = st.columns([2, 3], gap='large')
with izq:
    modo = st.segmented_control('Tipo de secuencia', list(EJEMPLOS), default='HP', key='lab_modo') or 'HP'
    valor = st.selectbox('Secuencia', EJEMPLOS[modo], key=f'lab_sec_{modo}', accept_new_options=True,
                         help='Elige un ejemplo o escribe la tuya.')
    sec = limpiar((valor or '').split('·')[-1])
    letras = {'H', 'P'} if modo == 'HP' else set(KYTE_DOOLITTLE)
    if not sec or set(sec) - letras:
        st.error('Solo H y P.' if modo == 'HP' else 'Solo las 20 letras de los aminoácidos.')
        st.stop()
    if not 4 <= len(sec) <= 30:
        st.error(f'Usa entre 4 y 30 (tiene {len(sec)}).')
        st.stop()
    if modo == 'HP':
        mu, hp, regla = None, sec, 'min'
    else:
        mu = grados_kd(sec)
        hp = a_hp(mu)
        regla = 'min' if (st.segmented_control('Regla de contacto', ['mínimo', 'producto'], default='mínimo',
                                               key='lab_regla') or 'mínimo') == 'mínimo' else 'prod'

    st.radio('Configuración', list(PRESETS), key='lab_preset', on_change=cargar)
    with st.expander('Ajustar a mano'):
        for k, (lo, hi) in zip(NOMBRES, LIMITES):
            st.slider(k, float(lo), float(hi), step=0.01, key=f'lab_{k}')
        st.toggle('Paridad de la cadena entera', key='lab_global_')
        st.select_slider('Umbral de R4', [0, 1, 2], key='lab_r4')
    r4 = st.session_state.lab_r4
    if mu is not None and r4 > 1 and st.toggle('Bajar R4 a 1 para grados', value=True, key='lab_r4_difusa',
                                               help='Con grados, la suma de H en la ventana de R4 es menor y el '
                                                    'umbral 2 poda demasiado (página de lógica difusa).'):
        r4 = 1
    cfg = ConfigHP(*(st.session_state[f'lab_{k}'] for k in NOMBRES), st.session_state.lab_global_, r4)

    mu_r0 = mu if mu is not None else grados_crisp(hp)
    f = fraccion_h(mu_r0)
    grado = float(rampa(f, *RAMPA))
    if st.toggle('Presupuesto según la R0 difusa', value=False, key='lab_r0',
                 help='En vez de un tope fijo, el grado de «plegable» decide cuántos nodos puede expandir.'):
        tope = presupuesto(grado, *PRESUPUESTO)
    else:
        tope = st.select_slider('Tope de nodos', [10_000, 50_000, 100_000, 300_000, 500_000, 1_000_000],
                                value=300_000, key='lab_tope',
                                help='Más de 500 000 nodos puede tardar varios segundos y gastar bastante '
                                     'memoria en el navegador.', format_func=lambda v: f'{v:,}'.replace(',', ' '))

with der:
    with st.spinner('Plegando…'):
        r = (mu is not None and precalculado(sec, cfg, regla, tope)) or \
            resolver(hp, tuple(cfg), tope=tope, mu=tuple(mu) if mu else None, regla=regla)
    titulo = f'{sec} · energía {r.energia:.3g}' if r.movs is not None else sec
    if r.movs is not None:
        svg(dibujo.conformacion(hp, r.movs, mu=mu, regla=regla, celda=40, ancho_max=620, titulo=titulo))
    else:
        st.warning(f'Se agotó el tope de {tope:,} nodos antes de encontrar una forma completa. Prueba otra '
                   'configuración o sube el tope.'.replace(',', ' '), icon=':material/hourglass_disabled:')
    m1, m2, m3 = st.columns(3)
    m1.metric('Energía', f'{r.energia:.3g}' if r.movs is not None else '—')
    m2.metric('Nodos expandidos', f'{r.nodos:,}'.replace(',', ' '), help=f'Tope: {tope:,}'.replace(',', ' '))
    if len(sec) <= 14:
        e_opt = optimo(hp, tuple(mu) if mu else None, regla)[0]
        m3.metric('Mejor posible', f'{e_opt:.3g}', help='Calculado probando todas las formas.')
        if r.movs is not None:
            if r.energia <= e_opt + 1e-9:
                st.success('Encontró la mejor forma posible.', icon=':material/check_circle:')
            else:
                st.info('Hay una forma mejor: esta configuración la podó o la estimación la engañó.',
                        icon=':material/info:')
    elif modo == 'HP' and referencia(sec) is not None:
        m3.metric('Referencia', f'{referencia(sec):g}', help='Mejor energía conocida (banco del proyecto).')

    nombre, texto = veredicto(grado)
    st.markdown(f'**R0 clásica:** {"la acepta" if f >= 0.3 else "la descartaría sin buscar"} '
                f'({f:.0%} de H). **R0 difusa:** grado {grado:.2f}, *{nombre}*. {texto}')
    if r.movs is not None:
        coords = reconstruir_coordenadas(r.movs)
        salida = dict(secuencia=sec, grados=mu, regla=regla if mu else None, configuracion=cfg._asdict(),
                      tope_nodos=tope, movimientos=r.movs, coordenadas=coords, energia=r.energia, nodos=r.nodos,
                      estado=r.estado)
        c1, c2 = st.columns([3, 2])
        c1.markdown(f'Movimientos: <span class="mono">{r.movs}</span>', unsafe_allow_html=True)
        c2.download_button('Descargar JSON', json.dumps(salida, ensure_ascii=False, indent=2),
                           file_name=f'plegamiento_{sec}.json', mime='application/json',
                           icon=':material/download:', width='stretch')

navegacion('paginas/laboratorio.py')
