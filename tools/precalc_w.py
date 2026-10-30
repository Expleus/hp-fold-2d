"""Barrido del peso w de la heurística (página «La heurística»). Escribe datos/pesos_w.json."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from hp.motor import CONFIG_ACTUAL, a_estrella, optimo_exhaustivo  # noqa: E402

SECUENCIAS = {'HPHPPHHPHPPHPHHPPHPH': -9, 'PPHHHPHPPHHPHPPH': None, 'HHPPHHPPHPHH': None}
TOPE = 400_000
salida = []
for sec, e_ref in SECUENCIAS.items():
    e_opt = e_ref if e_ref is not None else optimo_exhaustivo(sec)[0]
    for i in range(5, 21):
        w = i / 10
        r = a_estrella(sec, CONFIG_ACTUAL._replace(w=w), tope_nodos=TOPE)
        salida.append(dict(sec=sec, w=w, nodos=r.nodos, energia=r.energia if r.estado == 'ok' else None,
                           estado=r.estado, optimo=e_opt))
        print(sec, w, r.nodos, r.energia, r.estado, flush=True)
(RAIZ / 'datos' / 'pesos_w.json').write_text(json.dumps(dict(tope=TOPE, filas=salida)))
