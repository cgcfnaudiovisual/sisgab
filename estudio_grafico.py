import os
from nicegui import app
from fastapi.responses import HTMLResponse

base_dir = os.path.dirname(os.path.abspath(__file__))
estudio_html_path = os.path.join(base_dir, 'assets', 'estudio_grafico', 'index.html')

def get_estudio_html_content():
    if not os.path.exists(estudio_html_path):
        return HTMLResponse("<h1>Estúdio Gráfico indisponível (assets não encontrados).</h1>", status_code=404)

    with open(estudio_html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Reescrever todos os caminhos relativos de assets para absolutos
    #    Assim o Vue Router não interfere no carregamento de JS/CSS/fontes
    html = html.replace('href="./assets/', 'href="/assets/estudio_grafico/assets/')
    html = html.replace('src="./assets/', 'src="/assets/estudio_grafico/assets/')
    html = html.replace("href='./assets/", "href='/assets/estudio_grafico/assets/")
    html = html.replace("src='./assets/", "src='/assets/estudio_grafico/assets/")
    html = html.replace('href="./favicon.ico"', 'href="/assets/estudio_grafico/favicon.ico"')
    html = html.replace('src="./favicon.ico"', 'src="/assets/estudio_grafico/favicon.ico"')

    # 2. Injetar <base href="/estudio_grafico/"> para que o Vue Router interno
    #    consiga fazer strip do path e encontrar a rota "/" (home) corretamente.
    #    Caminhos absolutos acima NÃO serão afetados pela tag base.
    if '<base' not in html:
        html = html.replace('<head>', '<head><base href="/estudio_grafico/">', 1)

    # 3. Remover tracker externo do Baidu (desnecessário para uso interno)
    baidu_start = html.find('<script>var _hmt')
    if baidu_start != -1:
        baidu_end = html.find('</script>', baidu_start) + len('</script>')
        html = html[:baidu_start] + html[baidu_end:]

    return HTMLResponse(content=html)


@app.get('/estudio_grafico')
def render_estudio_grafico():
    """Rota principal do Estúdio Gráfico (yft-design)."""
    return get_estudio_html_content()

@app.get('/assets/estudio_grafico/estudio_grafico')
@app.get('/assets/estudio_grafico/index.html')
@app.get('/assets/estudio_grafico/')
def render_estudio_grafico_alias():
    """Aliases caso o navegador redirecione para caminhos alternativos."""
    return get_estudio_html_content()
