import os
from nicegui import app
from fastapi.responses import HTMLResponse

base_dir = os.path.dirname(os.path.abspath(__file__))
estudio_html_path = os.path.join(base_dir, 'assets', 'estudio_grafico', 'index.html')

@app.get('/estudio_grafico')
def render_estudio_grafico():
    """Serves the yft-design canvas graphics editor (Estúdio Gráfico)."""
    if not os.path.exists(estudio_html_path):
        return HTMLResponse("<h1>Estúdio Gráfico indisponível (assets não encontrados).</h1>", status_code=404)
    
    with open(estudio_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Injeta a tag base para resolução perfeita dos scripts e css estáticos
    if '<head>' in html_content and '<base' not in html_content:
        html_content = html_content.replace('<head>', '<head><base href="/assets/estudio_grafico/">')
        
    return HTMLResponse(content=html_content)
