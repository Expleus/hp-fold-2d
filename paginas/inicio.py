import streamlit as st

from hp import dibujo
from hp.ui import encabezado, resolver, svg

encabezado('HP-Fold 2D',
           'Cómo puede una computadora plegar una proteína (de juguete) sin probar todas las formas posibles: '
           'un modelo simple, un buscador con buen olfato y un ajuste automático de sus perillas.')

EJEMPLO = 'HPHPPHHPHPPHPHHPPHPH'
r = resolver(EJEMPLO)

izq, der = st.columns([5, 4], gap='large')
with izq:
    svg(dibujo.conformacion(EJEMPLO, r.movs, celda=40, ancho_max=380, indices=False))
with der:
    st.markdown('#### Lo que estás viendo')
    st.markdown(
        f"""
- Una cadena de **{len(EJEMPLO)} bolitas** puesta sobre una cuadrícula, sin que dos ocupen la misma casilla.
- Las **naranjas (H)** rehúyen el agua; las **blancas (P)** se llevan bien con ella.
- Cada **línea punteada** une dos H vecinas que no son consecutivas en la cadena: un *contacto*.
- Esta forma tiene **{-int(r.energia)} contactos**, el máximo posible para esta secuencia. Encontrarla es el reto.
"""
    )
    st.page_link('paginas/laboratorio.py', label='Pliega tu propia secuencia', icon=':material/science:')

st.markdown('### Recorrido sugerido')
st.caption('Cada página se apoya en la anterior, pero puedes saltar a la que quieras desde el menú lateral.')

PASOS = [
    ('paginas/problema.py', '1 · El problema', 'Qué es el modelo HP, por qué no se puede probar todo y cómo se mide '
                                               'qué tan buena es una forma.'),
    ('paginas/busqueda.py', '2 · Cómo busca A*', 'Construir la cadena bolita a bolita, siempre por el camino '
                                                 'más prometedor. Con reproductor paso a paso.'),
    ('paginas/reglas.py', '3 · Reglas de poda', 'Cinco atajos de sentido común para no perder tiempo en '
                                                'caminos sin futuro.'),
    ('paginas/heuristica.py', '4 · La heurística', 'Cómo estimar cuánto se puede ganar todavía, con un argumento '
                                                   'de tablero de ajedrez.'),
    ('paginas/cmaes.py', '5 · Ajuste con CMA-ES', 'Un algoritmo evolutivo que mueve las seis perillas del '
                                                  'buscador por nosotros.'),
    ('paginas/adversario.py', '6 · Robustez', 'Un examinador que insiste en las preguntas difíciles, para que '
                                              'el ajuste no sea bueno solo en promedio.'),
    ('paginas/difusa.py', '7 · Lógica difusa', 'Cambiar el «H o P» por grados, y el corte de la regla R0 por '
                                               'una rampa medida con datos.'),
    ('paginas/laboratorio.py', 'Laboratorio', 'Todo junto: pliega cualquier secuencia, HP o de aminoácidos, con '
                                              'la configuración que quieras.'),
]
for fila in (PASOS[:4], PASOS[4:]):
    cols = st.columns(4)
    for col, (ruta, titulo, texto) in zip(cols, fila):
        with col.container(border=True, height='stretch'):
            st.page_link(ruta, label=f'**{titulo}**')
            st.caption(texto)
