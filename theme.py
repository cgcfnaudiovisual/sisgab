# modules/theme.py
from nicegui import ui
from badge_base64 import BADGE_FN_BASE64

# Paleta de Cores "Gold Military" (alinhada com o brasão COMSOC)
colors = {
    'bg_app': '#0b0f19',       # Fundo Global
    'bg_panel': '#131a26',     # Sidebar / Cards
    'bg_editor': '#1b2535',    # Cor específica do editor
    'bg_input': '#1b2535',     # Campos de texto
    'primary': '#c5a059',      # Dourado Metálico (Primário)
    'secondary': '#f8fafc',    # Branco azulado
    'accent': '#d4af37',       # Dourado Brilhante
    'text_main': '#e2e8f0',
    'text_dim': '#64748b',
    'border': 'rgba(197, 160, 89, 0.15)',
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
    border: 1px solid rgba(197, 160, 89, 0.15) !important;
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
    background: rgba(197, 160, 89, 0.2);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(197, 160, 89, 0.5);
}

/* Permite que as abas do Quasar façam wrap */
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
    border: 1px solid rgba(197, 160, 89, 0.1) !important;
    border-radius: 6px !important;
}
.q-field--dark.q-field--focused .q-field__control {
    border-color: #c5a059 !important;
    box-shadow: 0 0 10px rgba(197, 160, 89, 0.2) !important;
}
.q-field__native, .q-field__prefix, .q-field__suffix, .q-field__input {
    color: #e2e8f0 !important;
}
.q-field__label {
    color: #64748b !important;
}

/* Efeito Glow Cyber */
.cyber-glow {
    box-shadow: 0 0 15px rgba(197, 160, 89, 0.25) !important;
    border: 1px solid rgba(197, 160, 89, 0.4) !important;
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
    border: 1px solid rgba(197, 160, 89, 0.3) !important;
    color: #c5a059 !important;
}
.q-btn--outline:hover {
    background: rgba(197, 160, 89, 0.05) !important;
    box-shadow: 0 0 8px rgba(197, 160, 89, 0.3) !important;
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
/* Efeito de Hover com Brilho Tático Antigravidade nos Cards */
.q-card, .nicegui-card {
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s ease, border-color 0.25s ease !important;
}
.q-card:hover, .nicegui-card:hover {
    border-color: rgba(197, 160, 89, 0.45) !important;
    box-shadow: 0 8px 30px rgba(197, 160, 89, 0.18), 0 0 15px rgba(197, 160, 89, 0.1) !important;
}

/* Estilização Tática Militar do Aviso de Reconexão */
.nicegui-connection-lost {
    background: #0f172a !important;
    border: 1px solid rgba(197, 160, 89, 0.4) !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.85) !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
    font-family: 'Share Tech Mono', monospace !important;
}
</style>

<canvas id="antigravity-canvas" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 0; opacity: 0.9;"></canvas>

<script>
(function() {
  if (window.__antigravity_initialized) return;
  window.__antigravity_initialized = true;

  const fnBadgeImg = new Image();
  fnBadgeImg.src = "${BADGE_FN_BASE64}";

  function initAntigravity() {
    let canvas = document.getElementById('antigravity-canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'antigravity-canvas';
      canvas.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; z-index: 0; opacity: 0.85;';
      document.body.prepend(canvas);
    }
    const ctx = canvas.getContext('2d', { alpha: true });
    let width = canvas.width = window.innerWidth;
    let height = canvas.height = window.innerHeight;

    window.addEventListener('resize', function() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    }, { passive: true });

    const isMobile = window.innerWidth < 768;
    const particleCount = isMobile ? 14 : 32;
    const particles = [];
    const mouse = { x: -1000, y: -1000, radius: 140 };

    window.addEventListener('mousemove', function(e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    }, { passive: true });

    window.addEventListener('mouseleave', function() {
      mouse.x = -1000;
      mouse.y = -1000;
    }, { passive: true });

    class Particle {
      constructor() {
        this.reset();
      }
      reset() {
        this.x = Math.random() * width;
        this.y = height + Math.random() * 80;
        this.size = Math.random() * 2 + 1.2;
        this.speedY = Math.random() * 0.7 + 0.35;
        this.speedX = (Math.random() - 0.5) * 0.4;
        this.alpha = Math.random() * 0.6 + 0.35;
        this.color = Math.random() > 0.3 ? '212, 175, 55' : '255, 193, 7';
        this.isBadge = Math.random() < 0.30;
      }
      update() {
        this.y -= this.speedY;
        this.x += this.speedX;

        const dx = mouse.x - this.x;
        const dy = mouse.y - this.y;
        const distSq = dx * dx + dy * dy;

        if (distSq < 19600) { // 140^2
          const dist = Math.sqrt(distSq);
          const force = (140 - dist) / 140;
          const angle = Math.atan2(dy, dx);
          this.x -= Math.cos(angle) * force * 3;
          this.y -= Math.sin(angle) * force * 3;
        }

        if (this.y < -20 || this.x < -20 || this.x > width + 20) {
          this.reset();
        }
      }
      draw() {
        if (this.isBadge && fnBadgeImg.complete && fnBadgeImg.naturalWidth !== 0) {
          ctx.save();
          ctx.globalAlpha = this.alpha;
          const bSize = this.size * 5.5 + 10;
          ctx.drawImage(fnBadgeImg, this.x - bSize/2, this.y - bSize/2, bSize, bSize);
          ctx.restore();
        } else {
          // Núcleo nítido e halo leve sem o custo pesado de shadowBlur
          ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`;
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.size, 0, 6.28318);
          ctx.fill();

          ctx.fillStyle = `rgba(${this.color}, ${this.alpha * 0.25})`;
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.size * 2.2, 0, 6.28318);
          ctx.fill();
        }
      }
    }

    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    let isRunning = true;
    document.addEventListener('visibilitychange', function() {
      if (document.hidden) {
        isRunning = false;
      } else if (!isRunning) {
        isRunning = true;
        requestAnimationFrame(animate);
      }
    });

    const maxDistSq = 95 * 95; // 9025

    function animate() {
      if (!isRunning) return;

      ctx.clearRect(0, 0, width, height);

      // 1. Atualiza e desenha partículas
      for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
      }

      // 2. Desenha conexões em lote (Único stroke call por frame)
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(197, 160, 89, 0.12)';
      ctx.lineWidth = 0.55;
      let hasLines = false;

      for (let i = 0; i < particles.length; i++) {
        const pi = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const pj = particles[j];
          const dx = pi.x - pj.x;
          const dy = pi.y - pj.y;
          const distSq = dx * dx + dy * dy;

          if (distSq < maxDistSq) {
            ctx.moveTo(pi.x, pi.y);
            ctx.lineTo(pj.x, pj.y);
            hasLines = true;
          }
        }
      }

      if (hasLines) {
        ctx.stroke();
      }

      requestAnimationFrame(animate);
    }

    animate();
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(initAntigravity, 150);
  } else {
    window.addEventListener('DOMContentLoaded', initAntigravity);
  }
})();
</script>
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