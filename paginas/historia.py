import altair as alt
import pandas as pd
import streamlit as st

from hp.ui import AZUL, GRIS, TINTA_2, encabezado, idea, navegacion

encabezado('Historia y referencias',
           'La app está ordenada por ideas, no por fechas. Aquí va el orden en que se construyó, los errores que '
           'enseñaron algo y las fuentes de cada pieza.')

st.markdown('### Cómo se construyó')

ETAPAS = [
    ('Sprint 1', 'Solo el buscador',
     'A* sobre cadenas de movimientos F/L/R. El costo real cuenta los contactos ya formados y la cola de '
     'prioridad ordena por $f$. La única restricción: dos bolitas no pueden ocupar la misma casilla.',
     [('paginas/busqueda.py', 'Cómo busca A*')]),
    ('Sprint 2', 'Reglas y heurística',
     'Encima del buscador se montan las cinco reglas de poda (R0 a R4) y una heurística que toma la más '
     'ajustada de dos cotas: la básica y la de paridad. Al contrastar el código con la enumeración exhaustiva '
     'aparecieron cuatro defectos (abajo).',
     [('paginas/reglas.py', 'Reglas de poda'), ('paginas/heuristica.py', 'La heurística')]),
    ('Sprint 3', 'Ajuste automático y robustez',
     'Cada corrección del sprint anterior era un número elegido a mano. Se dejan libres y CMA-ES busca dónde '
     'deberían estar, midiendo contra óptimos exactos. La mejor configuración acierta más y con cerca de un '
     'cuarto menos de nodos. Después, un adversario busca una configuración que aguante el peor caso: no la '
     'encuentra, y eso también es un resultado.',
     [('paginas/cmaes.py', 'Ajuste con CMA-ES'), ('paginas/adversario.py', 'Robustez: el adversario')]),
    ('Esta app', 'Lógica difusa',
     'Las dos extensiones pendientes del proyecto: hidrofobicidad graduada en lugar de H/P (con la cota de '
     'paridad re-derivada) y una R0 que nunca descarta, sino que reparte el presupuesto según una rampa '
     'ajustada a óptimos exactos.',
     [('paginas/difusa.py', 'Lógica difusa')]),
    ('Pendiente', 'Varios objetivos a la vez',
     'CMA-ES devuelve un único punto porque ordena primero por error y luego por costo. NSGA-II devolvería el '
     'frente de Pareto completo: todas las configuraciones donde no se puede ganar en exactitud sin pagar en '
     'nodos, y viceversa.',
     []),
]

for etiqueta, titulo, texto, enlaces in ETAPAS:
    with st.container(border=True):
        izq, der = st.columns([1, 4], gap='medium')
        izq.markdown(f'<span class="etiqueta">{etiqueta}</span>', unsafe_allow_html=True)
        der.markdown(f'**{titulo}**  \n{texto}')
        for ruta, nombre in enlaces:
            der.page_link(ruta, label=nombre, icon=':material/arrow_forward:')

st.markdown('### Los cuatro defectos del Sprint 2')
st.markdown('Se encontraron comparando el buscador contra la enumeración de **todas** las formas posibles '
            '(hasta 14 bolitas). Cada uno terminó convertido en una perilla del ajuste del Sprint 3.')
st.markdown(
    """
| Defecto | Por qué pasaba | Perilla en el Sprint 3 |
|---|---|---|
| La energía ya ganada no se restaba de la cota de paridad | El parámetro existía, pero no se pasaba en la llamada | $a_g$ |
| La paridad se contaba solo en el tramo que faltaba | Inconsistente con la resta anterior, que mira la cadena entera | interruptor «cadena entera» |
| El techo de contactos usaba $\\min+2$ en vez de $2\\cdot\\min+2$ | Subestimaba cuántos contactos caben | $a_p$, $c$ |
| La regla R4 nunca se ejecutaba | Código muerto: R2 la tapaba | `r4` |
"""
)
st.markdown('El cuarto es el más curioso. R4 buscaba **tres giros seguidos** hacia el mismo lado, pero tres giros '
            'así devuelven la cadena a una casilla ya ocupada, de modo que R2 (choque) la descartaba antes. Se '
            'comprobó con la enumeración completa hasta 12 bolitas y con 2 129 secuencias al azar: cero disparos. '
            'El rizo real se forma con **dos** giros; era un desfase de uno en el índice.')
st.markdown('#### La misma secuencia, versión tras versión')
st.markdown('<span class="mono">HPHPPHHPHPPHPHHPPHPH</span>, cuyo mínimo es −9. Una heurística que promete menos de '
            'lo alcanzable abre pocos nodos, pero poda ramas buenas y se queda corta.', unsafe_allow_html=True)
VERSIONES = pd.DataFrame(dict(
    version=['Cuaderno tal cual', '+ paridad en toda la cadena, restando lo ganado', '+ factor 2 en la paridad',
             '+ cota básica −2H (admisible)', '+ R4 corregida (de libro)', 'Ajustada por CMA-ES (G1)'],
    energia=[-5, -8, -7, -9, -9, -9], nodos=[33, 97, 46, 12_692, 9_964, 2_974]))
VERSIONES['etiqueta'] = VERSIONES.apply(lambda f: f"E = {f.energia}  ·  {f.nodos:,} nodos".replace(',', ' '), axis=1)
VERSIONES['piso'] = 10  # las barras en escala log necesitan un origen > 0
VERSIONES['optimo'] = VERSIONES.energia.map(lambda e: 'Llega a −9' if e == -9 else 'Se queda corta')
orden = list(VERSIONES.version)
base = alt.Chart(VERSIONES).encode(y=alt.Y('version:N', sort=orden, title=None, axis=alt.Axis(labelLimit=320)))
barras = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
    x=alt.X('nodos:Q', scale=alt.Scale(type='log', domain=[10, 200_000]), title='Nodos expandidos (escala log)',
            axis=alt.Axis(values=[10, 100, 1_000, 10_000, 100_000], format=',')),
    x2='piso:Q',
    color=alt.Color('optimo:N', scale=alt.Scale(domain=['Llega a −9', 'Se queda corta'], range=[AZUL, GRIS]),
                    legend=alt.Legend(title=None, orient='top')),
    tooltip=[alt.Tooltip('version:N', title='Versión'), alt.Tooltip('energia:Q', title='Energía'),
             alt.Tooltip('nodos:Q', title='Nodos', format=',')])
texto = base.mark_text(align='left', dx=6, color=TINTA_2).encode(x='nodos:Q', text='etiqueta:N')
st.altair_chart((barras + texto).properties(height=250), width='stretch')
idea('Corregir solo el factor de paridad <b>empeoraba</b> el resultado (−8 a −7). La cota de paridad se volvía '
     'más holgada, dejaba de ser la más ajustada de las dos y cedía el control a la cota básica, que también estaba '
     'mal: una bolita recién puesta puede cerrar dos contactos, no uno. Las correcciones solo funcionan juntas.',
     'Una lección')

st.markdown('### Autores')
st.markdown('**Juan Andrés Mejía** y **Santiago Rubiano** · Fundamentos de Inteligencia Artificial.')
st.caption('La app corre entera en tu navegador (Streamlit sobre stlite/Pyodide), sin servidor. Por eso los '
           'experimentos largos, como el ajuste con CMA-ES, el adversario y la tabla de R0, vienen precalculados; '
           'lo demás se calcula en vivo.')

st.markdown('### Referencias')
REFERENCIAS = {
    'Modelo HP y proteínas': [
        'Berger, B., & Leighton, T. (1998). Protein folding in the hydrophobic-hydrophilic (HP) model is '
        'NP-complete. <i>Journal of Computational Biology, 5</i>(1), 27–40. https://doi.org/10.1089/cmb.1998.5.27',
        'Dill, K. A. (1985). Theory for the folding and stability of globular proteins. <i>Biochemistry, 24</i>(6), '
        '1501–1509. https://doi.org/10.1021/bi00327a032',
        'Honda, S., Yamasaki, K., Sawada, Y., & Morii, H. (2004). 10 residue folded peptide designed by segment '
        'statistics. <i>Structure, 12</i>(8), 1507–1518. https://doi.org/10.1016/j.str.2004.05.022',
        'Lau, K. F., & Dill, K. A. (1989). A lattice statistical mechanics model of the conformational and '
        'sequence spaces of proteins. <i>Macromolecules, 22</i>(10), 3986–3997. https://doi.org/10.1021/ma00200a030',
        'Neidigh, J. W., Fesinmeyer, R. M., & Andersen, N. H. (2002). Designing a 20-residue protein. '
        '<i>Nature Structural Biology, 9</i>(6), 425–430. https://doi.org/10.1038/nsb798',
        'OEIS Foundation Inc. (s. f.). <i>A001411: Number of n-step self-avoiding walks on square lattice</i>. The '
        'On-Line Encyclopedia of Integer Sequences. Recuperado el 29 de octubre de 2026, de https://oeis.org/A001411',
    ],
    'Búsqueda': [
        'Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of '
        'minimum cost paths. <i>IEEE Transactions on Systems Science and Cybernetics, 4</i>(2), 100–107. '
        'https://doi.org/10.1109/TSSC.1968.300136',
    ],
    'Optimización y teoría de juegos': [
        'Cesa-Bianchi, N., & Lugosi, G. (2006). <i>Prediction, learning, and games</i>. Cambridge University '
        'Press. https://doi.org/10.1017/CBO9780511546921',
        'Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic '
        'algorithm: NSGA-II. <i>IEEE Transactions on Evolutionary Computation, 6</i>(2), 182–197. '
        'https://doi.org/10.1109/4235.996017',
        'Freund, Y., & Schapire, R. E. (1997). A decision-theoretic generalization of on-line learning and an '
        'application to boosting. <i>Journal of Computer and System Sciences, 55</i>(1), 119–139. '
        'https://doi.org/10.1006/jcss.1997.1504',
        'Freund, Y., & Schapire, R. E. (1999). Adaptive game playing using multiplicative weights. <i>Games and '
        'Economic Behavior, 29</i>(1–2), 79–103. https://doi.org/10.1006/game.1999.0738',
        'Hansen, N., Akimoto, Y., & Baudis, P. (2019). <i>CMA-ES/pycma on GitHub</i> [Software]. Zenodo. '
        'https://doi.org/10.5281/zenodo.2559634',
        'Hansen, N., & Ostermeier, A. (2001). Completely derandomized self-adaptation in evolution strategies. '
        '<i>Evolutionary Computation, 9</i>(2), 159–195. https://doi.org/10.1162/106365601750190398',
        'von Neumann, J. (1928). Zur Theorie der Gesellschaftsspiele. <i>Mathematische Annalen, 100</i>(1), '
        '295–320. https://doi.org/10.1007/BF01448847',
    ],
    'Lógica difusa e hidrofobicidad': [
        'Kyte, J., & Doolittle, R. F. (1982). A simple method for displaying the hydropathic character of a '
        'protein. <i>Journal of Molecular Biology, 157</i>(1), 105–132. '
        'https://doi.org/10.1016/0022-2836(82)90515-0',
        'Miyazawa, S., & Jernigan, R. L. (1985). Estimation of effective interresidue contact energies from '
        'protein crystal structures: Quasi-chemical approximation. <i>Macromolecules, 18</i>(3), 534–552. '
        'https://doi.org/10.1021/ma00145a039',
        'Zadeh, L. A. (1965). Fuzzy sets. <i>Information and Control, 8</i>(3), 338–353. '
        'https://doi.org/10.1016/S0019-9958(65)90241-X',
    ],
}


def enlazar(ref):
    inicio = ref.index('https://')
    url = ref[inicio:]
    return f'{ref[:inicio]}<a href="{url}" target="_blank">{url}</a>'


for tema, refs in REFERENCIAS.items():
    st.markdown(f'**{tema}**')
    st.markdown(''.join(f'<div class="ref">{enlazar(r)}</div>' for r in refs), unsafe_allow_html=True)

navegacion('paginas/historia.py')
