"""Escenarios de interacción por página (AppTest): cambia widgets y reporta excepciones."""
import time

from streamlit.testing.v1 import AppTest


def revisar(at, nombre, t):
    print(f'{nombre:48s} {time.time() - t:6.1f}s exc={len(at.exception)} err={len(at.error)} warn={len(at.warning)}')
    for e in at.exception:
        print('   EXC', e.message, '\n   ', '\n    '.join(e.stack_trace[-4:]))
    for e in list(at.error) + list(at.warning):
        print('   MSG', e.value[:140])


def pagina(p):
    at = AppTest.from_file('../app.py', default_timeout=900)
    at.run()
    at.switch_page(f'paginas/{p}.py').run()
    return at


ESCENARIOS = {
    'laboratorio': [
        {'lab_modo': 'Aminoácidos', 'lab_sec_Aminoácidos': 'Trp-cage TC5b (20) · NLYIQWLKDGGPSSGRPPPS'},
        {'lab_modo': 'Aminoácidos', 'lab_sec_Aminoácidos': 'Trp-cage TC5b (20) · NLYIQWLKDGGPSSGRPPPS',
         'lab_regla': 'producto'},
        {'lab_modo': 'Aminoácidos', 'lab_sec_Aminoácidos': 'Chignolina (10) · GYDPETGTWG', 'lab_r0': True},
        {'lab_modo': 'HP', 'lab_sec_HP': 'HHPPHH'},
        {'lab_sec_HP': 'HPPPPHPPPPPPHP', 'lab_r0': True},
        {'lab_sec_HP': 'HHPPHPPHPPHPPHPPHPPHPPHH', 'lab_r0': False, 'lab_tope': 10_000},
        {'lab_sec_HP': 'HXP'},
    ],
    'difusa': [
        {'df_pep': 'Trp-cage TC5b (20) · NLYIQWLKDGGPSSGRPPPS'},
        {'df_pep': 'Trp-cage TC5b (20) · NLYIQWLKDGGPSSGRPPPS', 'df_regla': 'producto'},
        {'df_crit': 3, 'df_r0_sec': 'PPPPHPPPPP'},
        {'df_pep': 'ACDEFGHIK'},
        {'df_pep': 'zzz', 'df_r0_sec': 'HQ'},
    ],
    'adversario': [{'ppt_rondas': 10_000}],
    'heuristica': [{'heu_w': 2.0}, {'heu_w': 0.5}],
    'busqueda': [{'as_paso': 0}],
}

for p, pasos in ESCENARIOS.items():
    for cambios in pasos:
        at = pagina(p)
        for k, v in cambios.items():
            at.session_state[k] = v
        t = time.time()
        try:
            at.run()
        except ValueError as e:
            print(f'{p} {cambios}'[:48], 'límite de AppTest con opciones nuevas:', e)
            continue
        revisar(at, f'{p} {cambios}'[:48], t)

# Presets con callback y formulario de CMA-ES
at = pagina('cmaes')
for preset in ('Robusta (adversario)', 'Ajustada por CMA-ES (G1)'):
    t = time.time()
    at.radio(key='cm_preset').set_value(preset).run()
    revisar(at, f'cmaes preset {preset}', t)
    print('   a_b en sesión:', at.session_state['cm_a_b'])
botones = [b for b in at.button if 'FormSubmit' in type(b).__name__ or b.proto.is_form_submitter]
print('   botones de formulario:', len(botones))
if botones:
    t = time.time()
    botones[0].click().run()
    revisar(at, 'cmaes enviar formulario', t)
    print('   métricas:', [(m.label, m.value) for m in at.metric][:6])
t = time.time()
at.session_state['cm_fun'] = 'Banana'
at.run()
revisar(at, 'cmaes demo banana', t)

at = pagina('laboratorio')
at.radio(key='lab_preset').set_value('Robusta (adversario)').run()
revisar(at, 'laboratorio preset robusta', time.time())
print('   métricas:', [(m.label, m.value) for m in at.metric])
