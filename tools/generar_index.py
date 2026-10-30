"""Genera index.html: la app Streamlit corriendo en el navegador con stlite (Pyodide), lista para GitHub Pages.
Volver a correrlo después de añadir o quitar archivos de la app."""
import json
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
STLITE = 'https://cdn.jsdelivr.net/npm/@stlite/browser@1.12.0/build'

archivos = sorted(['app.py', *(str(p.relative_to(RAIZ)) for d, patron in (('hp', '*.py'), ('paginas', '*.py'),
                                                                        ('datos', '*.json'))
                               for p in (RAIZ / d).glob(patron))])
config = tomllib.loads((RAIZ / '.streamlit' / 'config.toml').read_text(encoding='utf-8'))
streamlit_config = {f'{seccion}.{clave}': valor for seccion, valores in config.items() for clave, valor in valores.items()}
opciones = dict(entrypoint='app.py', requirements=['cma'], streamlitConfig=streamlit_config,
                files={a: {'url': f'./{a}'} for a in archivos})

HTML = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <title>HP-Fold 2D · plegamiento de proteínas con A*</title>
  <meta name="description" content="App didáctica: modelo HP de plegamiento en red cuadrada, búsqueda A*, reglas de poda, CMA-ES, un adversario y lógica difusa.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧬</text></svg>">
  <link rel="stylesheet" href="{STLITE}/stlite.css">
</head>
<body>
  <div id="root"></div>
  <script type="module">
    import {{ mount }} from "{STLITE}/stlite.js";
    mount({json.dumps(opciones, ensure_ascii=False, indent=2)}, document.getElementById("root"));
  </script>
</body>
</html>
"""
(RAIZ / 'index.html').write_text(HTML, encoding='utf-8')
print(f'index.html con {len(archivos)} archivos')
