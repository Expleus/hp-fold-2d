"""Recorre todas las páginas con AppTest y reporta excepciones y tiempos."""
import sys
import time

from streamlit.testing.v1 import AppTest

PAGINAS = sys.argv[1:] or ['inicio', 'problema', 'busqueda', 'reglas', 'heuristica', 'cmaes', 'adversario',
                           'difusa', 'laboratorio', 'historia']
for p in PAGINAS:
    at = AppTest.from_file('../app.py', default_timeout=600)
    at.run()
    t = time.time()
    at.switch_page(f'paginas/{p}.py').run()
    errores = [e.value for e in at.exception] + [e.value for e in at.error]
    print(f'{p:12s} [{at.title[0].value if at.title else "SIN TITULO"}] {time.time() - t:6.1f}s  excepciones={len(at.exception)} errores={len(at.error)} '
          f'warnings={len(at.warning)}')
    for e in at.exception:
        print('   EXC', e.message, '\n', '\n'.join(e.stack_trace[-6:]))
    for e in at.warning:
        print('   WARN', e.value[:120])
    for e in at.error:
        print('   ERR', e.value)
