"""Precalcula A* difuso para los péptidos de ejemplo (la variante más pesada pide ~660k nodos y ~0.5 GB,
demasiado para el navegador). Salida: datos/peptidos.json con clave 'secuencia|regla|r4'."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from hp.difuso import PEPTIDOS, a_hp, grados_kd  # noqa: E402
from hp.motor import CONFIG_ACTUAL, a_estrella  # noqa: E402

salida = {}
for aa in PEPTIDOS.values():
    mu = grados_kd(aa)
    for regla in ('min', 'prod'):
        for r4 in (1, 2):
            r = a_estrella(a_hp(mu), CONFIG_ACTUAL._replace(r4=r4), tope_nodos=2_000_000, mu=mu, regla=regla)
            salida[f'{aa}|{regla}|{r4}'] = r._asdict()
            print(aa, regla, r4, r.estado, r.energia, r.nodos)
(RAIZ / 'datos' / 'peptidos.json').write_text(json.dumps(salida, indent=1), encoding='utf-8')
