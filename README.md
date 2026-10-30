# HP-Fold 2D

App didáctica sobre plegamiento de proteínas en el **modelo HP** (red cuadrada): cómo la búsqueda **A\*** encuentra la
forma de menor energía, qué hacen sus **reglas de poda** y su **heurística**, cómo **CMA-ES** ajusta sus perillas, qué
pasa cuando un **adversario** elige el examen y cómo cambia todo con **lógica difusa**.

**▶ Abrir la app: https://expleus.github.io/hp-fold-2d/**

La app es Streamlit corriendo entero en el navegador con [stlite](https://github.com/whitphx/stlite) (Python sobre
Pyodide), así que GitHub Pages la sirve sin servidor. La primera carga tarda unos segundos mientras se descarga Python.

## Páginas

| Página | Qué muestra |
|---|---|
| El problema | El modelo HP, plegar una cadena a mano y por qué no se puede probar todo |
| Cómo busca A\* | Reproductor paso a paso de la búsqueda |
| Reglas de poda | R0–R4, con ejemplos y cuánto ahorra cada una |
| La heurística | Cota básica, cota de paridad (tablero de ajedrez) y el peso w |
| Ajuste con CMA-ES | Las seis perillas, una demo 2D de CMA-ES y los resultados del ajuste |
| Robustez: el adversario | Hedge contra el afinador, juego minimax y examen con secuencias nuevas |
| Lógica difusa | Grados de hidrofobicidad (Kyte–Doolittle), cota de paridad rederivada y R0 en rampa |
| Laboratorio | Plegar cualquier secuencia HP o de aminoácidos con cualquier configuración |
| Historia y referencias | Cómo se construyó por sprints, los defectos encontrados y las fuentes |

## Correrla en local

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Estructura

- `app.py` — navegación; `paginas/` — una página por tema.
- `hp/motor.py` — modelo HP, A\* y reglas (verificado contra el motor del Sprint 3 en las 90 secuencias del banco).
- `hp/difuso.py`, `hp/dibujo.py`, `hp/ui.py` — lógica difusa, dibujos SVG y utilidades de interfaz.
- `datos/` — resultados precalculados (ajuste CMA-ES, rondas de Hedge, barrido de w, rampa de R0, péptidos); los
  scripts que los generan están en `tools/precalc_*.py`.
- `index.html` — se genera con `python tools/generar_index.py` (rehacer al añadir o quitar archivos).
- `tools/probar_stlite.py` — prueba la versión del navegador en Chromium sin ventana.

Proyecto de Fundamentos de Inteligencia Artificial — Juan Andrés Mejía y Santiago Rubiano.
