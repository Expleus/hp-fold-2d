"""Copia a datos/ lo que la app necesita del banco (Sprint 3) y del juego Hedge."""
import json, os, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
from motor_sprint3 import BANCO

ADV = os.path.join(RAIZ, '..', 'datos_hp_adversario')
base = json.load(open(os.path.join(ADV, 'nodos_base.json')))['ref']
banco = []
for sec, e_ref, tipo, conjunto, centinela in BANCO:
    e, nodos, estado = base[sec]
    banco.append(dict(sec=sec, E=e_ref, tipo=tipo, conjunto=conjunto, centinela=bool(centinela),
                      nodos_base=nodos, estado_base=estado))
json.dump(banco, open(os.path.join(RAIZ, 'datos', 'banco.json'), 'w'), ensure_ascii=False)

juego = json.load(open(os.path.join(ADV, 'juego_hedge.json')))
par = juego['parametros']
salida = dict(T=par['T'], generaciones=par['generaciones'], banco=par['banco'], p_final=juego['p_final'],
              rondas=[dict(cfg=r['cfg'], l=r['l'], p=r['p'], valor=r['valor']) for r in juego['rondas']])
json.dump(salida, open(os.path.join(RAIZ, 'datos', 'hedge.json'), 'w'), ensure_ascii=False)
print(len(banco), 'secuencias;', len(salida['rondas']), 'rondas; banco adversario', len(salida['banco']))
