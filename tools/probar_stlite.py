"""Abre la versión stlite (index.html servido en localhost) en Chromium sin ventana, recorre todas las páginas y
reporta errores y tiempos. Uso: python tools/probar_stlite.py [url] [carpeta_capturas]"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765/'
CAPTURAS = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/hpfold_capturas')
CAPTURAS.mkdir(parents=True, exist_ok=True)
PAGINAS = ['El problema', 'Cómo busca A*', 'Reglas de poda', 'La heurística', 'Ajuste con CMA-ES',
           'Robustez: el adversario', 'Lógica difusa', 'Laboratorio', 'Historia y referencias']


def esperar_quieto(pagina, tope=240):
    """Espera a que el texto de la página deje de cambiar durante 2.5 s (Streamlit terminó de correr)."""
    t = time.time()
    anterior, estable = None, 0.0
    while time.time() - t < tope:
        texto = pagina.locator('[data-testid="stMain"]').inner_text() if pagina.locator('[data-testid="stMain"]').count() else ''
        corriendo = pagina.locator('[data-testid="stStatusWidget"]').count() > 0
        if texto == anterior and not corriendo:
            estable += 0.5
            if estable >= 2.5:
                return time.time() - t - 2.5
        else:
            anterior, estable = texto, 0.0
        pagina.wait_for_timeout(500)
    return None


def revisar(pagina, nombre):
    exc = pagina.locator('[data-testid="stException"]')
    errores = [exc.nth(i).inner_text()[:400] for i in range(exc.count())]
    titulo = pagina.locator('h1').first.inner_text() if pagina.locator('h1').count() else 'SIN TITULO'
    return titulo, errores


with sync_playwright() as p:
    nav = p.chromium.launch()
    pagina = nav.new_page(viewport={'width': 1400, 'height': int(sys.argv[3]) if len(sys.argv) > 3 else 900})
    consola = []
    pagina.on('console', lambda m: consola.append(f'{m.type}: {m.text[:300]}') if m.type == 'error' else None)
    pagina.on('requestfailed', lambda r: consola.append(f'requestfailed: {r.url[:200]}'))
    pagina.on('pageerror', lambda e: consola.append(f'pageerror: {str(e)[:300]}'))
    t0 = time.time()
    pagina.goto(URL)
    pagina.wait_for_selector('h1', timeout=300_000)
    quieto = esperar_quieto(pagina)
    titulo, errores = revisar(pagina, 'Inicio')
    print(f'{"Inicio":26s} carga total {time.time() - t0:5.1f}s  [{titulo}] errores={len(errores)}')
    pagina.screenshot(path=str(CAPTURAS / '00_inicio.png'), full_page=True)
    for i, nombre in enumerate(PAGINAS, 1):
        t = time.time()
        pagina.locator('[data-testid="stSidebarNav"] a', has_text=nombre).first.click()
        pagina.wait_for_timeout(500)
        quieto = esperar_quieto(pagina)
        titulo, errores = revisar(pagina, nombre)
        print(f'{nombre:26s} {time.time() - t:5.1f}s  [{titulo}] errores={len(errores)}'
              + ('' if quieto is not None else '  (NO TERMINÓ)'))
        for e in errores:
            print('   ', e.replace('\n', ' | '))
        pagina.screenshot(path=str(CAPTURAS / f'{i:02d}.png'), full_page=True)
    # Descarga del laboratorio
    pagina.locator('[data-testid="stSidebarNav"] a', has_text='Laboratorio').first.click()
    esperar_quieto(pagina)
    try:
        with pagina.expect_download(timeout=20_000) as d:
            pagina.get_by_text('Descargar JSON').click()
        print('descarga OK:', d.value.suggested_filename, Path(d.value.path()).stat().st_size, 'bytes')
    except Exception as e:
        print('descarga FALLÓ:', str(e)[:200])
    print('consola:', *consola[:15], sep='\n  ')
    nav.close()
