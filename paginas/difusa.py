import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from hp import dibujo
from hp.difuso import (KYTE_DOOLITTLE, NOMBRES_AA, PEPTIDOS, a_hp, ajustar_rampa, brier_escalon, cota_paridad,
                       energias_todas, fraccion_h, grados_kd, presupuesto, rampa, tabla_r0, veredicto)
from hp.motor import CONFIG_ACTUAL, grados_crisp
from hp.ui import (AZUL, GRIS, GRIS_CLARO, NARANJA, TINTA_2, aviso, datos, ecuacion, encabezado, idea, limpiar,
                   optimo, precalculado, resolver, navegacion, svg)

encabezado('Lógica difusa: del sí/no al «cuánto»',
           'El modelo HP dice que cada aminoácido es H o P, y R0 dice que una secuencia pliega o no pliega. Las dos '
           'cosas son, en realidad, cuestión de grado. La lógica difusa permite decir «bastante» en vez de «sí».')

idea('En la lógica clásica algo pertenece o no a un conjunto (1 o 0). En la difusa tiene un <b>grado de '
     'pertenencia</b> entre 0 y 1: un residuo puede ser hidrofóbico «en un 0.8». Aquí se aplica en dos sitios: '
     'a <b>las bolitas</b> (cada una tiene un grado de H) y a <b>R0</b> (cada secuencia tiene un grado de «plegable»).',
     titulo='Grados en vez de etiquetas')

PRESUPUESTO = (2_000, 300_000)
TOPE_AA = 300_000
pest1, pest2 = st.tabs(['Bolitas con grado de H', 'R0 sin corte brusco'])

# ======================================================================== 1. hidrofobicidad graduada
with pest1:
    st.markdown('### De la escala real a un grado entre 0 y 1')
    st.markdown('La hidrofobicidad de un aminoácido es un número continuo. La escala de **Kyte y Doolittle** va de '
                '−4.5 (arginina, la más afín al agua) a +4.5 (isoleucina, la que más la rehúye). Se reescala a un '
                'grado $\\mu$:')
    ecuacion(r'\mu = \frac{\mathrm{KD} + 4.5}{9} \in [0, 1]',
             [(r'\mu', 'grado de H de la bolita: 0 = nada hidrofóbica, 1 = todo lo hidrofóbica posible.'),
              (r'\mathrm{KD}', 'valor del aminoácido en la escala de Kyte y Doolittle, entre −4.5 y +4.5.'),
              (r'+4.5', 'corre la escala para que empiece en 0.'),
              (r'/\,9', 'la encoge a un ancho de 1 (la escala mide 9 de punta a punta).')])
    st.markdown('El modelo HP clásico equivale a redondear: $\\mu \\ge 0.5 \\Rightarrow$ H, si no P. Es la forma más '
                'brusca posible de tirar información.')

    opciones = [f'{k} · {v}' for k, v in PEPTIDOS.items()]
    eleccion = st.selectbox('Péptido (código de una letra)', opciones, key='df_pep', accept_new_options=True,
                            help='Elige uno real o escribe una secuencia de aminoácidos, p. ej. MKVLAAGIVG.')
    aa = limpiar(eleccion.split('·')[-1] if eleccion else '')
    if not aa or set(aa) - set(KYTE_DOOLITTLE):
        st.error('Usa solo las 20 letras de los aminoácidos: ' + ' '.join(sorted(KYTE_DOOLITTLE)) + '. '
                 'Mientras, se muestra la chignolina.')
        aa = PEPTIDOS['Chignolina (10)']
    elif not 4 <= len(aa) <= 24:
        st.error(f'Usa entre 4 y 24 aminoácidos (tiene {len(aa)}). Mientras, se muestra la chignolina.')
        aa = PEPTIDOS['Chignolina (10)']
    mu = grados_kd(aa)
    hp = a_hp(mu)

    dfm = pd.DataFrame(dict(i=range(len(aa)), aa=list(aa), nombre=[NOMBRES_AA[c] for c in aa], mu=mu,
                            kd=[KYTE_DOOLITTLE[c] for c in aa], hp=list(hp)))
    barras = alt.Chart(dfm).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X('i:O', title=None, axis=alt.Axis(labelExpr=f'{json.dumps(list(aa))}[datum.value]', labelAngle=0)),
        y=alt.Y('mu:Q', title='Grado de H (μ)', scale=alt.Scale(domain=[0, 1])),
        color=alt.Color('mu:Q', scale=alt.Scale(domain=[0, 1], range=['#f2e4dc', NARANJA]), legend=None),
        tooltip=[alt.Tooltip('nombre:N', title='Aminoácido'), alt.Tooltip('kd:Q', title='Kyte–Doolittle'),
                 alt.Tooltip('mu:Q', title='μ', format='.2f'), alt.Tooltip('hp:N', title='En el modelo HP')])
    corte = alt.Chart(pd.DataFrame(dict(y=[0.5]))).mark_rule(color=TINTA_2, strokeDash=[4, 4]).encode(y='y:Q')
    corte_t = alt.Chart(pd.DataFrame(dict(y=[0.5]))).mark_text(
        align='right', dy=-7, x='width', color=TINTA_2).encode(y='y:Q', text=alt.value('corte del modelo HP'))
    st.altair_chart((barras + corte + corte_t).properties(height=220), width='stretch')
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('**Con grados**')
        svg(dibujo.cinta(hp, mu=mu, tam=22))
    with c2:
        st.markdown('**Redondeada a H/P**')
        svg(dibujo.cinta(hp, tam=22))
    if 'H' not in hp:
        aviso(f'Redondeada, esta secuencia queda <b>toda P</b>: en el modelo clásico no hay ningún contacto posible '
              f'y todas las formas valen 0. Con grados sigue habiendo diferencias que aprovechar.')

    with st.expander('La escala completa'):
        kd = pd.DataFrame(sorted(((NOMBRES_AA[c], c, v, round((v + 4.5) / 9, 2)) for c, v in KYTE_DOOLITTLE.items()),
                                 key=lambda t: -t[2]), columns=['Aminoácido', 'Letra', 'Kyte–Doolittle', 'μ'])
        st.dataframe(kd, hide_index=True, width='stretch')

    # ---------------------------------------------------------------- energía de contacto
    st.markdown('### ¿Cuánto vale un contacto entre grados?')
    st.markdown('Si dos bolitas vecinas tienen grados $\\mu_i$ y $\\mu_j$, el contacto ya no vale exactamente −1. '
                'Hay dos reglas naturales, y las dos devuelven el modelo clásico cuando los grados son 0 o 1:')
    rejilla = pd.DataFrame([dict(a=a, b=b, a2=a + 0.1, b2=b + 0.1, mn=min(a + .05, b + .05),
                                 pr=(a + .05) * (b + .05)) for a in np.arange(0, 1, 0.1) for b in np.arange(0, 1, 0.1)])

    def mapa(campo, titulo):
        return alt.Chart(rejilla).mark_rect().encode(
            x=alt.X('a:Q', title='μᵢ', scale=alt.Scale(domain=[0, 1], nice=False)), x2='a2:Q',
            y=alt.Y('b:Q', title='μⱼ', scale=alt.Scale(domain=[0, 1], nice=False)), y2='b2:Q',
            color=alt.Color(f'{campo}:Q', title='|energía|', scale=alt.Scale(domain=[0, 1], range=['#f6f4ef', NARANJA])),
            tooltip=[alt.Tooltip(f'{campo}:Q', title='|energía|', format='.2f')]
        ).properties(height=220, title=titulo)

    ecuacion(r'\varepsilon_{ij} = -\min(\mu_i, \mu_j)',
             [(r'\varepsilon_{ij}', 'energía del contacto entre las bolitas $i$ y $j$ (negativa: un contacto '
                                    'siempre ayuda).'),
              (r'\mu_i,\ \mu_j', 'grados de H de las dos bolitas.'),
              (r'\min', 'el menor de los dos: manda la bolita más débil.')])
    st.altair_chart(mapa('mn', 'Mínimo: manda el más débil'), width='stretch')
    st.caption('El «Y» difuso clásico (Zadeh): el contacto es tan bueno como su bolita menos hidrofóbica.')
    ecuacion(r'\varepsilon_{ij} = -\mu_i\,\mu_j',
             [(r'\varepsilon_{ij}', 'energía del contacto entre las bolitas $i$ y $j$.'),
              (r'\mu_i\,\mu_j', 'producto de los grados: solo es grande si **los dos** lo son '
                                '(0.5 × 0.5 = 0.25).')])
    st.altair_chart(mapa('pr', 'Producto: más exigente'), width='stretch')
    st.caption('Solo dos bolitas muy hidrofóbicas dan un contacto fuerte. Se parece a las matrices de contacto '
               'de Miyazawa y Jernigan.')
    regla = st.segmented_control('Regla de contacto', ['min', 'producto'], default='min', key='df_regla') or 'min'
    regla = 'min' if regla == 'min' else 'prod'

    # ---------------------------------------------------------------- paisaje
    st.markdown('### El paisaje deja de tener mesetas')
    n = len(aa)
    if n <= 12:
        @st.cache_data(show_spinner='Probando todas las formas…')
        def paisaje(mu_t, hp_s, regla):
            difusa = energias_todas(list(mu_t), regla)
            clasica = energias_todas(grados_crisp(hp_s), regla)
            return difusa, clasica

        Ed, Ec = paisaje(tuple(mu), hp, regla)
        # Mismo eje para los dos: barras de ancho 1 (energías enteras) frente a barras finas (grados).
        lo = np.floor(min(min(Ec), min(Ed))) - 0.5
        for titulo, E, paso in zip(('Clásico (H/P)', 'Con grados'), (Ec, Ed), (1.0, 0.05)):
            st.markdown(f'**{titulo}**')
            hist = alt.Chart(pd.DataFrame(dict(E=E))).mark_bar(
                color=AZUL, cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
                x=alt.X('E:Q', bin=alt.Bin(step=paso, extent=[lo, 0.5]), title='Energía',
                        scale=alt.Scale(domain=[lo, 0.5], nice=False)),
                y=alt.Y('count():Q', title='Formas (escala log)', scale=alt.Scale(type='symlog')),
                tooltip=[alt.Tooltip('count():Q', title='formas')])
            st.altair_chart(hist.properties(height=180), width='stretch')
            mejor = min(E)
            m1, m2 = st.columns(2)
            m1.metric('Empatadas en la mejor', f'{sum(abs(e - mejor) < 1e-9 for e in E):,}'.replace(',', '\u2009'))
            m2.metric('Energías distintas', len({round(e, 6) for e in E}))
        st.markdown(f'Las {len(Ed):,} formas posibles de la cadena, agrupadas por energía. En el modelo clásico la '
                    'energía solo toma valores enteros y muchísimas formas empatan: son **mesetas** donde un buscador '
                    'no sabe hacia dónde ir. Con grados casi no hay empates.'.replace(',', ' '))
    else:
        st.caption('El histograma de todas las formas se calcula para cadenas de hasta 12 aminoácidos.')

    # ---------------------------------------------------------------- cota de paridad
    st.markdown('### La cota de paridad, rederivada')
    st.markdown(
        """
La heurística usaba el tablero de ajedrez: **cada contacto une una bolita par con una impar**, y cada bolita tiene
como mucho **2 vecinos libres** (3 si está en un extremo). Con grados el argumento sigue valiendo, pero en vez de
contar bolitas H se **suman sus grados**: un contacto nunca vale más que el grado de su bolita par (ni que el de
su bolita impar).
"""
    )
    ecuacion(r'|E| \;\le\; \min\Big(2\!\sum_{i\ \text{par}}\!\mu_i + \mu_{\text{extremos pares}},\;\; '
             r'2\!\!\sum_{i\ \text{impar}}\!\!\mu_i + \mu_{\text{extremos impares}}\Big)',
             [(r'|E|', 'la energía de la forma, sin el signo menos (la suma del valor de sus contactos).'),
              (r'\textstyle\sum_{i\ \text{par}} \mu_i', 'suma de los grados de las bolitas en posiciones pares '
                                                        '(0, 2, 4…).'),
              (r'\textstyle\sum_{i\ \text{impar}} \mu_i', 'lo mismo con las impares (1, 3, 5…).'),
              (r'2', 'cada bolita tiene como mucho 2 huecos libres para contactos.'),
              (r'\mu_{\text{extremos pares}}', 'grados de los extremos de la cadena que caen en posición par: '
                                               'tienen un hueco extra.'),
              (r'\min', 'todo contacto une una par con una impar, así que manda el lado que suma menos.')],
             nota='Es un techo. El razonamiento completo está en el desplegable de abajo.')
    with st.expander('El razonamiento paso a paso'):
        st.markdown(
            r"""
1. **Bipartición.** En la red cuadrada, las casillas se colorean como un tablero y la bolita $i$ cae en el color
   de la paridad de $i$. Dos casillas vecinas tienen colores distintos, así que todo contacto $(i, j)$ tiene un
   índice par y uno impar.
2. **Valor de un contacto.** Con la regla del mínimo, $\min(\mu_i,\mu_j) \le \mu_i$ y $\le \mu_j$. Con el producto,
   $\mu_i\mu_j \le \min(\mu_i,\mu_j)$ porque los grados son $\le 1$. En ambos casos un contacto vale como mucho el
   grado de su extremo par, y también como mucho el de su extremo impar.
3. **Contactos por bolita.** Una bolita interior tiene 4 vecinos en la red, 2 de ellos ocupados por sus vecinas de
   cadena: le quedan 2 para contactos. Un extremo de la cadena tiene solo una vecina de cadena: le quedan 3.
4. **Suma.** Agrupando los contactos por su extremo par,
   $|E| \le \sum_{i\ \text{par}} c_i\,\mu_i$ con $c_i = 2$ (o 3 en un extremo), que es
   $2\sum_\text{par}\mu_i + \mu_\text{extremos pares}$. Lo mismo agrupando por el impar, y vale el menor.

Con grados 0/1 se recupera la cota clásica; de hecho, es **más ajustada** que $2\min(H_\text{par}, H_\text{impar}) + 2$,
porque el «+2» solo hace falta si los extremos son H y tienen la paridad que manda.
"""
        )
    fina, simple = cota_paridad(mu)
    n_opt = len(aa) <= 14
    if n_opt:
        e_real = -optimo(hp, tuple(mu), regla)[0]
    filas = [dict(cota='Rederivada', valor=fina, tipo='cota'), dict(cota='Clásica 2·min + 2', valor=simple, tipo='cota')]
    if n_opt:
        filas.append(dict(cota='Óptimo exacto', valor=e_real, tipo='real'))
    dfc = pd.DataFrame(filas)
    barras = alt.Chart(dfc).mark_bar(cornerRadiusEnd=4, height=22).encode(
        x=alt.X('valor:Q', title='Contactos (suma de grados)'), y=alt.Y('cota:N', title=None, sort=None),
        color=alt.Color('tipo:N', scale=alt.Scale(domain=['cota', 'real'], range=[GRIS_CLARO, AZUL]), legend=None),
        tooltip=['cota', alt.Tooltip('valor:Q', format='.3f')])
    textos = barras.mark_text(align='left', dx=5, color=TINTA_2).encode(text=alt.Text('valor:Q', format='.2f'))
    st.altair_chart((barras + textos).properties(height=40 * len(filas) + 30), width='stretch')
    if n_opt:
        st.markdown(f'Para este péptido, el mejor plegamiento suma **{e_real:.2f}**: las dos cotas lo respetan '
                    f'(nunca prometen menos de lo posible), y la rederivada se queda más cerca.')
    else:
        st.markdown('El óptimo exacto se calcula probando todas las formas, solo hasta 14 aminoácidos.')

    # ---------------------------------------------------------------- A* difuso
    st.markdown('### A* con grados')
    st.markdown('El buscador funciona igual: $g$ suma grados en vez de contar contactos y la heurística usa la cota '
                'rederivada. Solo hay que ajustar **R4**, que mira la suma de H en una ventana de 4 bolitas: con '
                'grados esa suma es más baja (cuatro bolitas «medio hidrofóbicas» suman 2, no 4), y el umbral de '
                'libro (2) poda demasiado. Por eso con grados se usa `r4` = 1.')

    def comparar(aa, regla):
        mu = grados_kd(aa)
        hp = a_hp(mu)
        salida = []
        for r4 in (1, 2):
            cfg = CONFIG_ACTUAL._replace(r4=r4)
            salida.append(precalculado(aa, cfg, regla, tope=10**9) or
                          resolver(hp, tuple(cfg), tope=TOPE_AA, mu=tuple(mu), regla=regla))
        return salida

    with st.spinner('Buscando con A*…'):
        r1, r2 = comparar(aa, regla)
    izq, der = st.columns([3, 2], gap='large')
    with izq:
        if r1.movs is not None:
            svg(dibujo.conformacion(hp, r1.movs, mu=mu, regla=regla, celda=40, ancho_max=460,
                                    titulo=f'{aa} · energía {r1.energia:.3f}'))
        else:
            st.warning(f'Con r4 = 1 la búsqueda agotó el tope de {TOPE_AA:,} nodos sin cerrar una forma. Prueba una '
                       'cadena más corta.'.replace(',', ' '), icon=':material/hourglass_disabled:')
    with der:
        st.dataframe(pd.DataFrame([
            {'Versión': nombre, 'Energía': f'{r.energia:.3f}' if r.movs is not None else 'sin terminar',
             'Nodos': r.nodos} for nombre, r in (('r4 = 1 (con grados)', r1), ('r4 = 2 (de libro)', r2))
        ]), hide_index=True, width='stretch')
        st.caption('Las líneas punteadas son contactos; más gruesas cuanto más valen. El color de cada bolita '
                   'indica su grado de H.')
        if r1.movs is not None and r2.movs is not None and r2.energia > r1.energia + 1e-9:
            st.warning(f'Con el umbral de libro, R4 poda la buena forma y se queda en {r2.energia:.3f}.',
                       icon=':material/content_cut:')

# ======================================================================== 2. R0 difusa
with pest2:
    st.markdown('### Un corte en 0.3 que no corresponde a nada físico')
    st.markdown('R0 declara «no plegable» toda secuencia con menos de un 30 % de H y **aborta** la búsqueda. Una '
                'secuencia con 29.9 % se descarta y una con 30.1 % se pliega entera. ¿Es razonable? No hace falta '
                'opinar: se puede **medir**. Para cada secuencia HP de 10 a 14 bolitas se calculó su mejor energía '
                'probando todas las formas.')
    R0 = datos('r0.json')
    rechazadas = [g for g in R0['grupos'] if g['k'] / g['n'] < 0.3]
    tot = sum(sum(g['E'].values()) for g in rechazadas)
    dos = sum(v for g in rechazadas for e, v in g['E'].items() if int(e) <= -2)
    aviso(f'R0 rechaza <b>{tot:,}</b> secuencias de 10 a 14 bolitas. <b>{dos:,}</b> de ellas ({dos / tot:.0%}) '
          'consiguen 2 contactos o más: R0 está tirando plegamientos de verdad.'.replace(',', ' '))

    criterio = st.segmented_control('¿Qué cuenta como «pliega»?', [1, 2, 3], default=2, key='df_crit',
                                    format_func=lambda c: f'{c} contacto' + ('s' if c > 1 else '') + ' o más') or 2
    filas = tabla_r0(R0['grupos'], criterio)
    a, b, brier = ajustar_rampa(filas)
    brier_e = brier_escalon(filas)
    dfp = pd.DataFrame(filas)
    dfp = dfp.groupby('f', as_index=False).agg(total=('total', 'sum'), pliegan=('pliegan', 'sum'))
    dfp['prop'] = dfp.pliegan / dfp.total
    xs = np.linspace(0, 1, 201)
    curvas = pd.DataFrame([dict(f=x, grado=float(rampa(x, a, b)), forma='Rampa ajustada') for x in xs] +
                          [dict(f=x, grado=float(x >= 0.3), forma='R0 clásica (escalón)') for x in xs])
    lineas = alt.Chart(curvas).mark_line(strokeWidth=2.5, interpolate='linear').encode(
        x=alt.X('f:Q', title='Fracción de H', axis=alt.Axis(format='%')),
        y=alt.Y('grado:Q', title='Proporción que pliega / grado', axis=alt.Axis(format='%')),
        color=alt.Color('forma:N', title=None, legend=alt.Legend(orient='top'),
                        scale=alt.Scale(domain=['Rampa ajustada', 'R0 clásica (escalón)'], range=[NARANJA, GRIS])),
        strokeDash=alt.StrokeDash('forma:N', legend=None,
                                  scale=alt.Scale(domain=['Rampa ajustada', 'R0 clásica (escalón)'],
                                                  range=[[1, 0], [5, 4]])))
    puntos = alt.Chart(dfp).mark_circle(color=AZUL, opacity=0.85, stroke='white', strokeWidth=1).encode(
        x='f:Q', y='prop:Q', size=alt.Size('total:Q', title='Secuencias', scale=alt.Scale(range=[20, 400]),
                                           legend=alt.Legend(orient='top')),
        tooltip=[alt.Tooltip('f:Q', title='fracción de H', format='.1%'), alt.Tooltip('total:Q', title='secuencias'),
                 alt.Tooltip('prop:Q', title='pliegan', format='.1%')])
    st.altair_chart((lineas + puntos).properties(height=320), width='stretch')
    st.caption('Cada punto azul agrupa las secuencias con la misma fracción de H (más grande = más secuencias); '
               'su altura es la proporción que de verdad pliega.')
    st.markdown(f'**Rampa ajustada a los datos:** grado 0 por debajo de **{a:.0%}** de H, grado 1 por encima de '
                f'**{b:.0%}**, y lineal en medio.')
    ecuacion(r'\mu_\text{plegable}(f) = \begin{cases} 0 & f \le a \\ \dfrac{f - a}{b - a} & a < f < b \\ 1 & f \ge b'
             r'\end{cases}',
             [(r'\mu_\text{plegable}', 'grado de «plegable» de la secuencia, entre 0 y 1.'),
              (r'f', r'fracción de H de la secuencia (con grados, el promedio de $\mu$).'),
              (r'a', f'fracción por debajo de la cual el grado es 0 (aquí, {a:.0%}).'),
              (r'b', f'fracción por encima de la cual el grado es 1 (aquí, {b:.0%}).'),
              (r'\frac{f - a}{b - a}',
               'dónde cae $f$ entre $a$ y $b$: sube en línea recta de 0 (en $a$) a 1 (en $b$).')])
    m1, m2 = st.columns(2)
    m1.metric('Error de la rampa', f'{brier:.4f}')
    m2.metric('Error del escalón', f'{brier_e:.4f}')
    st.caption('Error cuadrático medio por secuencia (puntaje de Brier) frente a lo que de verdad pliega. La '
               'rampa no se elige a ojo: es la que mejor encaja con los óptimos exactos.')

    st.markdown('### Lo importante: no abortar, sino dosificar')
    st.markdown('La R0 difusa **nunca aborta**. El grado decide **cuánto esfuerzo** merece la secuencia: con grado 1 '
                'el buscador tiene todo el presupuesto de nodos; con grado bajo, un presupuesto reducido y una '
                'advertencia de que la forma devuelta probablemente no importe. Como el esfuerzo de A* crece de forma '
                'exponencial, el presupuesto también se reparte así:')
    ecuacion(r'\text{nodos} = N_\text{mín}\,\Big(\frac{N_\text{máx}}{N_\text{mín}}\Big)^{\mu_\text{plegable}}',
             [(r'\text{nodos}', 'presupuesto: cuántas cadenas puede expandir A* como máximo.'),
              (r'N_\text{mín}', 'presupuesto con grado 0.'),
              (r'N_\text{máx}', 'presupuesto completo, con grado 1.'),
              (r'\mu_\text{plegable}', 'grado de «plegable» de la secuencia.')],
             nota='El grado va en el exponente: cada décima de grado multiplica el presupuesto por el mismo factor. '
                  'Así, grado 0.5 da la media geométrica entre $N_\\text{mín}$ y $N_\\text{máx}$, no la aritmética.')
    entrada = st.text_input('Prueba una secuencia (H/P o aminoácidos)', 'HPPPPHPPPPPPHP', key='df_r0_sec')
    s = limpiar(entrada)
    if s and not set(s) - {'H', 'P'}:
        mu_s, tipo = grados_crisp(s), 'HP'
    elif s and not set(s) - set(KYTE_DOOLITTLE):
        mu_s, tipo = grados_kd(s), 'aminoácidos'
    else:
        st.error('Escribe una secuencia de H y P, o de aminoácidos. Mientras, se usa HPPPPHPPPPPPHP.')
        mu_s, tipo = grados_crisp('HPPPPHPPPPPPHP'), 'HP'
    f = fraccion_h(mu_s)
    grado = float(rampa(f, a, b))
    nombre, texto = veredicto(grado)
    gs = np.linspace(0, 1, 101)
    dfb = pd.DataFrame(dict(grado=gs, nodos=[presupuesto(g, *PRESUPUESTO) for g in gs]))
    curva = alt.Chart(dfb).mark_line(color=AZUL, strokeWidth=2).encode(
        x=alt.X('grado:Q', title='Grado de «plegable»'),
        y=alt.Y('nodos:Q', title='Presupuesto de nodos (escala log)', scale=alt.Scale(type='log'),
                axis=alt.Axis(format='~s')),
        tooltip=[alt.Tooltip('grado:Q', format='.2f'), alt.Tooltip('nodos:Q', format=',')])
    punto = alt.Chart(pd.DataFrame(dict(grado=[grado], nodos=[presupuesto(grado, *PRESUPUESTO)]))).mark_point(
        filled=True, size=120, color=NARANJA, stroke='white', strokeWidth=1.5).encode(x='grado:Q', y='nodos:Q')
    st.altair_chart((curva + punto).properties(height=280), width='stretch')
    st.caption(f'Entre {PRESUPUESTO[0]:,} y {PRESUPUESTO[1]:,} nodos. El punto naranja es la secuencia de '
               f'arriba.'.replace(',', ' '))
    m0, m1, m2 = st.columns(3)
    m0.metric('Fracción de H' + (' (suma de grados ÷ n)' if tipo == 'aminoácidos' else ''), f'{f:.1%}')
    m1.metric('Grado de «plegable»', f'{grado:.2f}')
    m2.metric('Presupuesto', f'{presupuesto(grado, *PRESUPUESTO):,} nodos'.replace(',', ' '))
    (st.success if grado >= 0.8 else st.info if grado >= 0.3 else st.warning)(f'**{nombre.capitalize()}.** {texto}')
    st.caption('R0 clásica: ' + ('la acepta.' if f >= 0.3 else '**la descarta sin buscar.**'))

navegacion('paginas/difusa.py')
