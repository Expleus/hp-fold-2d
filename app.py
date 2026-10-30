"""HP-Fold 2D: plegamiento de proteínas en el modelo HP, explicado de forma visual."""
import streamlit as st

from hp.ui import estilo

st.set_page_config(page_title='HP-Fold 2D', page_icon='🧬', layout='wide',
                   menu_items={'About': 'HP-Fold 2D · Fundamentos de IA · Juan Andrés Mejía y Santiago Rubiano'})
estilo()

paginas = {
    '': [st.Page('paginas/inicio.py', title='Inicio', icon=':material/home:', default=True)],
    'Aprender': [
        st.Page('paginas/problema.py', title='El problema', icon=':material/genetics:'),
        st.Page('paginas/busqueda.py', title='Cómo busca A*', icon=':material/travel_explore:'),
        st.Page('paginas/reglas.py', title='Reglas de poda', icon=':material/content_cut:'),
        st.Page('paginas/heuristica.py', title='La heurística', icon=':material/explore:'),
        st.Page('paginas/cmaes.py', title='Ajuste con CMA-ES', icon=':material/tune:'),
        st.Page('paginas/adversario.py', title='Robustez: el adversario', icon=':material/swords:'),
        st.Page('paginas/difusa.py', title='Lógica difusa', icon=':material/blur_on:'),
    ],
    'Herramientas': [st.Page('paginas/laboratorio.py', title='Laboratorio', icon=':material/science:')],
    'Proyecto': [st.Page('paginas/historia.py', title='Historia y referencias', icon=':material/history_edu:')],
}
st.navigation(paginas).run()
