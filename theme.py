# modules/theme.py
from nicegui import ui

# Paleta de Cores "Cyber Military"
colors = {
    'bg_app': '#0b0f19',       # Fundo Global
    'bg_panel': '#131a26',     # Sidebar / Cards
    'bg_editor': '#1b2535',    # Cor específica do editor
    'bg_input': '#1b2535',     # Campos de texto
    'primary': '#00e5ff',      # Ciano Neon (Primário)
    'secondary': '#f8fafc',    # Branco azulado
    'accent': '#00a2ff',       # Azul Neon
    'text_main': '#e2e8f0',
    'text_dim': '#64748b',
    'border': 'rgba(0, 229, 255, 0.15)',
    'success': '#00e676',
    'danger': '#ff1744'
}

CYBER_MILITARY_CSS = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#0b0f19">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      navigator.serviceWorker.register('/service-worker.js').then(function(reg) {
        console.log('ServiceWorker registration successful with scope: ', reg.scope);
      }).catch(function(err) {
        console.log('ServiceWorker registration failed: ', err);
      });
    });
  }
</script>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;700&family=Outfit:wght@400;500;600;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
/* Customização de Fontes Globais */
body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #0b0f19 !important;
    color: #e2e8f0 !important;
    font-size: 13.5px !important;
}

/* Títulos e Fontes Cyber */
.cyber-title {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* Customização dos painéis do Quasar e NiceGUI */
.q-card, .nicegui-card {
    background-color: #131a26 !important;
    border: 1px solid rgba(0, 229, 255, 0.15) !important;
    box-shadow: 0 4px 25px 0 rgba(0, 0, 0, 0.6) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}

.q-avatar img {
    object-fit: cover !important;
}

/* Scrollbars Táticos */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #0b0f19;
}
::-webkit-scrollbar-thumb {
    background: rgba(0, 229, 255, 0.2);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 229, 255, 0.5);
}

/* Permite que as abas do Quasar façam wrap (quebrem linha para baixo) quando o espaço horizontal for reduzido */
.q-tabs__content {
    flex-wrap: wrap !important;
    height: auto !important;
}
.q-tabs {
    height: auto !important;
}

/* Inputs do Quasar */
.q-field--dark .q-field__control {
    background-color: #1b2535 !important;
    border: 1px solid rgba(0, 229, 255, 0.1) !important;
    border-radius: 6px !important;
}
.q-field--dark.q-field--focused .q-field__control {
    border-color: #00e5ff !important;
    box-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
}
.q-field__native, .q-field__prefix, .q-field__suffix, .q-field__input {
    color: #e2e8f0 !important;
}
.q-field__label {
    color: #64748b !important;
}

/* Efeito Glow Cyber */
.cyber-glow {
    box-shadow: 0 0 15px rgba(0, 229, 255, 0.25) !important;
    border: 1px solid rgba(0, 229, 255, 0.4) !important;
}
.cyber-glow-amber {
    box-shadow: 0 0 15px rgba(212, 175, 55, 0.25) !important;
    border: 1px solid rgba(212, 175, 55, 0.4) !important;
}

/* Botões do Quasar com visual militar tático */
.q-btn {
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}
.q-btn--outline {
    border: 1px solid rgba(0, 229, 255, 0.3) !important;
    color: #00e5ff !important;
}
.q-btn--outline:hover {
    background: rgba(0, 229, 255, 0.05) !important;
    box-shadow: 0 0 8px rgba(0, 229, 255, 0.3) !important;
}

/* Responsividade para Tabelas do Quasar */
.q-table__container {
    max-width: 100% !important;
    overflow-x: auto !important;
}

/* Responsividade de Linhas de Grade e Layouts para Mobile */
@media (max-width: 1024px) {
    .wrap-mobile {
        flex-direction: column !important;
        flex-wrap: wrap !important;
        align-items: stretch !important;
        gap: 16px !important;
    }
    .wrap-mobile > div {
        width: 100% !important;
        max-width: 100% !important;
    }
}
</style>
"""

def apply_global_styles():
    """Aplica cores globais ao Quasar/NiceGUI"""
    ui.colors(
        primary=colors['primary'],
        secondary=colors['secondary'],
        accent=colors['accent'],
        dark=colors['bg_app'],
        positive=colors['success'],
        negative=colors['danger']
    )
    ui.add_head_html(CYBER_MILITARY_CSS)
    ui.query('body').style(f'background-color: {colors["bg_app"]} !important;')

def section_header(title, subtitle=None):
    with ui.column().classes('gap-0 q-mb-md'):
        ui.label(title).classes('cyber-title').style(f'color: {colors["text_main"]}; font-size: 1.5rem; font-weight: 700;')
        if subtitle:
            ui.label(subtitle).style(f'color: {colors["text_dim"]}; font-size: 0.85rem;')

def card_base():
    """Retorna um card com o estilo padrão (sem sombra, borda fina)"""
    return ui.card().classes('no-shadow').style(
        f'background: {colors["bg_panel"]} !important; border: 1px solid {colors["border"]} !important; border-radius: 8px;'
    )

def badge_status(status):
    """Badge padronizada"""
    map_color = {
        'Publicado': 'green',
        'Editado': 'blue',
        'Bruto': 'grey'
    }
    color = map_color.get(status, 'grey')
    return ui.badge(status, color=color).props('outline rounded')