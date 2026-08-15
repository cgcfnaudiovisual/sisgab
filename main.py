import os
import socket

from nicegui import ui, app
from fastapi import Request
from dotenv import load_dotenv
import asyncio


# Mapeia a pasta local de assets para servir arquivos estáticos no navegador
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
os.makedirs(assets_dir, exist_ok=True)
app.add_static_files('/assets', assets_dir)

@app.api_route('/ping', methods=['GET', 'HEAD', 'POST'])
@app.api_route('/health', methods=['GET', 'HEAD', 'POST'])
def get_health_ping():
    return {"status": "ok", "app": "SisGAB", "bot": "active"}

@app.get('/manifest.json')
def get_manifest():
    return {
        "name": "SisGAB - Gestão de Gabinete",
        "short_name": "SisGAB",
        "description": "Sistema de Gestão e Comunicação Social do Gabinete",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0b0f19",
        "theme_color": "#00e5ff",
        "orientation": "portrait",
        "icons": [
            {
                "src": "/assets/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "/assets/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }

@app.get('/service-worker.js')
def get_service_worker():
    from fastapi.responses import Response
    sw_code = """
    self.addEventListener('install', event => {
      self.skipWaiting();
    });

    self.addEventListener('activate', event => {
      event.waitUntil(
        caches.keys().then(cacheNames => {
          return Promise.all(
            cacheNames.map(cache => {
              console.log('[PWA] Clearing old cache:', cache);
              return caches.delete(cache);
            })
          );
        }).then(() => clients.claim())
      );
    });

    self.addEventListener('fetch', event => {
      // Passthrough para evitar interferência com WebSockets e comunicação em tempo real do NiceGUI
    });
    """
    return Response(content=sw_code, media_type="application/javascript")


# --- ENDPOINTS DE API DO SISGAB ---
from database import get_db_connection
from fastapi import Body

@app.get('/api/face_embeddings')
def api_get_face_embeddings():
    from database import get_db_connection
    db = get_db_connection()
    if not db:
        return {"error": "Database offline"}, 500
    try:
        res = db.table('face_embeddings').select('*').execute()
        return res.data or []
    except Exception as e:
        return {"error": str(e)}, 500

@app.post('/api/photo_processed')
async def api_photo_processed(payload: dict = Body(...)):
    from datetime import datetime
    from database import get_db_connection
    db = get_db_connection()
    if not db:
        return {"error": "Database offline"}, 500
    
    event_name = payload.get('event_name')
    filename = payload.get('filename')
    drive_file_id = payload.get('drive_file_id')
    drive_link = payload.get('drive_link')
    matches = payload.get('matches', [])
    thumbnail_b64 = payload.get('thumbnail_base64')
    
    try:
        # Salva miniatura local se enviada
        if thumbnail_b64:
            try:
                import base64
                thumb_bytes = base64.b64decode(thumbnail_b64)
                dest_dir = os.path.join(assets_dir, 'galeria_hot', event_name)
                os.makedirs(dest_dir, exist_ok=True)
                with open(os.path.join(dest_dir, filename), 'wb') as f_thumb:
                    f_thumb.write(thumb_bytes)
            except Exception as thumb_err:
                print(f"[API THUMB ERR] {thumb_err}")
                
        # 1. Registrar a foto
        photo_record = {
            'event_name': event_name,
            'filename': filename,
            'drive_file_id': drive_file_id,
            'drive_link': drive_link,
            'criado_em': datetime.now().isoformat()
        }
        res_photo = db.table('processed_photos').insert(photo_record).execute()
        if not res_photo.data:
            return {"error": "Falha ao registrar foto"}, 500
        
        photo_id = res_photo.data[0]['id']
        
        # 2. Registrar correspondências
        for m in matches:
            militar_id = m.get('militar_id')
            similarity = m.get('similarity')
            
            # Limiar de moderação
            status = 'aprovado' if similarity >= 0.65 else 'pendente'
            
            match_record = {
                'photo_id': photo_id,
                'militar_id': militar_id,
                'similarity': similarity,
                'status': status,
                'criado_em': datetime.now().isoformat()
            }
            db.table('photo_matches').insert(match_record).execute()
            
        return {"status": "success", "photo_id": str(photo_id)}
    except Exception as e:
        return {"error": str(e)}, 500


# --- ENDPOINTS DO ESTÚDIO GRÁFICO (yft-design) ---
@app.get('/api/artes_graficas')
def api_get_artes_graficas(criado_por: str = None):
    from database import get_db_connection
    db = get_db_connection()
    if not db:
        return {"error": "Database offline"}, 500
    try:
        query = db.table('artes_graficas').select('*').order('atualizado_em', desc=True)
        if criado_por:
            query = query.eq('criado_por', criado_por)
        res = query.execute()
        return res.data or []
    except Exception as e:
        return {"error": str(e)}, 500

@app.post('/api/artes_graficas')
async def api_save_arte_grafica(payload: dict = Body(...)):
    from datetime import datetime
    from database import get_db_connection
    db = get_db_connection()
    if not db:
        return {"error": "Database offline"}, 500
    try:
        arte_id = payload.get('id')
        arte_record = {
            'titulo': payload.get('titulo', 'Sem Título'),
            'criado_por': payload.get('criado_por', 'Operador'),
            'tipo': payload.get('tipo', 'arte'),
            'json_data': payload.get('json_data', {}),
            'thumbnail_url': payload.get('thumbnail_url', ''),
            'pdf_url': payload.get('pdf_url', ''),
            'atualizado_em': datetime.now().isoformat()
        }
        if arte_id:
            res = db.table('artes_graficas').update(arte_record).eq('id', arte_id).execute()
        else:
            arte_record['criado_em'] = datetime.now().isoformat()
            res = db.table('artes_graficas').insert(arte_record).execute()
        return {"status": "success", "data": res.data or []}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get('/api/templates_graficos')
def api_get_templates_graficos():
    from database import get_db_connection
    db = get_db_connection()
    if not db:
        return {"error": "Database offline"}, 500
    try:
        res = db.table('templates_graficos').select('*').eq('publico', True).execute()
        return res.data or []
    except Exception as e:
        return {"error": str(e)}, 500


from fastapi.responses import Response, RedirectResponse
import zipfile
import io

@app.get('/api/drive_download/{file_id}')
def api_drive_download_file(file_id: str, filename: str = None):
    import drive_service
    file_bytes = drive_service.download_file(file_id)
    if file_bytes:
        fname = filename or f"foto_{file_id[:8]}.jpg"
        if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
            fname += ".jpg"
        return Response(
            content=file_bytes,
            media_type='image/jpeg',
            headers={'Content-Disposition': f'attachment; filename="{fname}"'}
        )
    return RedirectResponse(url=f"https://drive.google.com/uc?id={file_id}&export=download")


@app.get('/api/drive_download_zip')
def api_drive_download_zip(ids: str = '', folder_id: str = ''):
    import drive_service
    file_ids = [i.strip() for i in ids.split(',') if i.strip()]
    
    if not file_ids and folder_id:
        files = drive_service.list_files(folder_id, mime_filter='image/', page_size=50)
        file_ids = [f['id'] for f in files if f.get('id')]
        
    if not file_ids:
        return Response(content="Nenhum arquivo selecionado.", status_code=400)
        
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for idx, fid in enumerate(file_ids):
            fbytes = drive_service.download_file(fid)
            if fbytes:
                zip_file.writestr(f"foto_{idx+1:02d}_{fid[:6]}.jpg", fbytes)
                
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type='application/zip',
        headers={'Content-Disposition': 'attachment; filename="acervo_fotos.zip"'}
    )


import theme
from logo_base64 import LOGO_BASE64

# Carrega o logotipo (URL ou Base64) para gerar os ícones do PWA na inicialização se não existirem
try:
    logo_bytes = None
    if LOGO_BASE64.startswith('http'):
        import requests
        for icon_name in ['icon-192.png', 'icon-512.png', 'apple-touch-icon.png']:
            icon_path = os.path.join(assets_dir, icon_name)
            if not os.path.exists(icon_path):
                if logo_bytes is None:
                    res = requests.get(LOGO_BASE64, timeout=5)
                    if res.status_code == 200:
                        logo_bytes = res.content
                if logo_bytes:
                    with open(icon_path, 'wb') as f:
                        f.write(logo_bytes)
    else:
        import base64
        logo_data = LOGO_BASE64.split(',')[-1]
        logo_bytes = base64.b64decode(logo_data)
        for icon_name in ['icon-192.png', 'icon-512.png', 'apple-touch-icon.png']:
            icon_path = os.path.join(assets_dir, icon_name)
            if not os.path.exists(icon_path):
                with open(icon_path, 'wb') as f:
                    f.write(logo_bytes)
except Exception as e:
    print(f"[PWA] Erro ao carregar logo para icones: {e}", flush=True)

import admin
import notifications
import theme_toggle
import assistente_ia
import config
import admin_panel
import telegram_bot
import sisgab_tv
import ajuda_sobre
import comsoc_noticias
import comsoc_demandas
import comsoc_tarefas
import comsoc_cautela
import comsoc_brindes
import comsoc_galeria
import comsoc_historico
import comsoc_aniversariantes
import smart_editor
import agenda_geral
import painel_comando
import comsoc_assentos
import estudio_grafico
import comsoc_rsvp
import modulo_presenca
import qrcode_generator
import telegram_metrics
import portal_convidado
import jarvis_voice
from database import authenticate_user, get_user_by_id

from services import data_service

# Carrega o .env a partir do diretório absoluto do arquivo
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

app.native.window_args['resizable'] = True
app.native.window_args['title'] = 'SisGAB'

PUBLIC_ROUTES = {'/login', '/evento', '/rsvp'}

sisgab_menu_categories = [
    {
        'category': '🏛️ GABINETE & OPERAÇÕES DIÁRIAS',
        'items': [
            {'name': 'Painel de Comando', 'icon': 'dashboard', 'path': '/', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'], 'subtitle': 'Agenda, KPIs e panorama geral'},
            {'name': 'Chamada & Presença Diária', 'icon': 'assignment_ind', 'path': '/presenca', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'], 'subtitle': 'Chamada matutina e Pronto do CheGab'},
            {'name': 'Nova Solicitação / Demanda', 'icon': 'add_box', 'path': '/comsoc_demandas', 'roles': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Formulário de pautas e tarefas'},
            {'name': 'Gestão de Demandas', 'icon': 'gavel', 'path': '/comsoc_homologar', 'roles': ['admin', 'supervisor', 'oficial_gab', 'comsoc', 'praca_gab'], 'subtitle': 'Parecer e aprovação de pautas'},
        ]
    },
    {
        'category': '🎯 TAREFAS & CERIMONIAL',
        'items': [
            {'name': 'Tarefas COMSOC', 'icon': 'task_alt', 'path': '/comsoc_tarefas', 'roles': ['admin', 'supervisor', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'], 'subtitle': 'Kanban de tarefas criativas e internas'},
            {'name': 'Placas de Assento (Jade)', 'icon': 'event_seat', 'path': '/comsoc_assentos', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Mapeamento e alocação de auditório'},
            {'name': 'Gestão de Convites & RSVP', 'icon': 'mark_email_read', 'path': '/comsoc_rsvp', 'roles': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Convites formais e confirmação de presença'},
        ]
    },
    {
        'category': '📦 LOGÍSTICA & MATERIAL',
        'items': [
            {'name': 'Estoque de Brindes', 'icon': 'card_giftcard', 'path': '/comsoc_brindes', 'roles': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Controle de brindes do RP'},
            {'name': 'Cautela de Material', 'icon': 'battery_charging_full', 'path': '/comsoc_cautela', 'roles': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Empréstimos de equipamentos'},
        ]
    },
    {
        'category': '📣 COMUNICAÇÃO & MÍDIA',
        'items': [
            {'name': 'Central de IA', 'icon': 'psychology', 'path': '/assistente_ia', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Chat, redator e triagem de demandas'},
            {'name': 'Jarvis Assistente de Voz', 'icon': 'graphic_eq', 'path': '/jarvis', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'], 'subtitle': 'Voz em tempo real e palavra-chave Jarvis'},
            {'name': 'Smart Editor IA', 'icon': 'movie_filter', 'path': '/smart_editor', 'roles': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'supervisor'], 'subtitle': 'Cortes com IA, SFX e FCPXML'},
            {'name': 'Estúdio Gráfico (Canva)', 'icon': 'palette', 'path': '/estudio_grafico', 'roles': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'supervisor'], 'subtitle': 'Editor visual de artes e impressos', 'new_tab': True},
            {'name': 'Galeria de Fotos & Acervo', 'icon': 'photo_library', 'path': '/comsoc_galeria', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar'], 'subtitle': 'Visualizador do Drive, Seleção Curada e Reconhecimento Facial'},
            {'name': 'Arquivo e Histórico', 'icon': 'history', 'path': '/comsoc_historico', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Busca e links de coberturas passadas'},
            {'name': 'Aniversariantes & Datas', 'icon': 'cake', 'path': '/comsoc_aniversariantes', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design'], 'subtitle': 'Mensagens com IA e impressão'},
            {'name': 'Monitor TV (COMSOC TV)', 'icon': 'tv', 'path': '/sisgab_tv', 'roles': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'tv', 'tv_comcia'], 'subtitle': 'Modo TV tático', 'new_tab': True},
            {'name': 'Gerador de QR Code', 'icon': 'qr_code_2', 'path': '/qrcode_generator', 'roles': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar'], 'subtitle': 'Gerar QR Codes para links e eventos'},
        ]
    },
    {
        'category': '⚙️ SISTEMA & ADMINISTRAÇÃO',
        'items': [
            {'name': 'Métricas do Bot Telegram', 'icon': 'analytics', 'path': '/telegram_metrics', 'roles': ['admin', 'supervisor'], 'subtitle': 'Auditoria e logs do assistente virtual'},
            {'name': 'Configurações', 'icon': 'settings', 'path': '/config', 'roles': ['admin', 'oficial_gab'], 'subtitle': 'Parâmetros do sistema'},
            {'name': 'Usuários e Permissões', 'icon': 'admin_panel_settings', 'path': '/admin_panel', 'roles': ['admin'], 'subtitle': 'Controle de acesso e aprovação'},
            {'name': 'Ajuda / Sobre', 'icon': 'help_outline', 'path': '/ajuda_sobre', 'roles': ['admin', 'supervisor', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'compel', 'operador'], 'subtitle': 'Manuais e suporte'},
        ]
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# Mapeamento de rotas → roles permitidos (construído a partir do menu)
# Rotas sem restrição de role ficam abertas a qualquer usuário autenticado.
# ─────────────────────────────────────────────────────────────────────────────
ROUTE_ROLES: dict[str, list[str]] = {}
for _cat in sisgab_menu_categories:
    for _item in _cat['items']:
        if 'roles' in _item:
            ROUTE_ROLES[_item['path']] = _item['roles']


def is_authenticated() -> bool:
    authenticated = app.storage.user.get('authenticated', False)
    if authenticated:
        login_time = app.storage.user.get('login_time')
        duration = app.storage.user.get('session_duration')
        if login_time and duration and duration > 0:
            import time
            if time.time() - login_time > duration:
                app.storage.user.clear()
                return False
    return authenticated


def get_current_user() -> dict:
    return app.storage.user.get('user_data', {})


def check_auth():
    if not is_authenticated():
        ui.navigate.to('/login')


def run_auth_checks():
    if not is_authenticated():
        ui.navigate.to('/login')
        return False
        
    role_user = str(app.storage.user.get('user_data', {}).get('role', '')).strip().lower()
    if role_user in ('tv', 'tv_comcia') and app.storage.user.get('current_path') != '/sisgab_tv':
        ui.navigate.to('/sisgab_tv')
        return False
        
    if role_user in ('tv', 'tv_comcia') and app.storage.user.get('tv_lock_active', False) and app.storage.user.get('current_path') != '/sisgab_tv':
        ui.navigate.to('/sisgab_tv')
        return False

    if role_user == 'militar' and app.storage.user.get('current_path') != '/ajuda_sobre':
        app.storage.user['current_path'] = '/ajuda_sobre'
        ui.notify("ℹ️ Seu perfil 'militar' possui acesso apenas ao painel de Ajuda / Sobre por enquanto.", color='warning')
        ui.navigate.to('/ajuda_sobre')
        return False

    # ── AUTORIZAÇÃO SERVER-SIDE: verifica role contra rotas protegidas ──
    current_path = app.storage.user.get('current_path', '/')
    path_clean = current_path.strip('/').replace('/', '_')
    f_key = f"menu_{path_clean}"
    
    import pandas as pd
    perms_df = data_service.get_core_data().get('permissions', pd.DataFrame())
    row = perms_df[perms_df['feature_key'] == f_key] if not perms_df.empty else pd.DataFrame()
    
    allowed_roles = []
    if not row.empty:
        allowed_roles_str = str(row['allowed_roles'].iloc[0])
        allowed_roles = [r.strip().lower() for r in allowed_roles_str.split(',') if r.strip()]
    elif current_path in ROUTE_ROLES:
        allowed_roles = ROUTE_ROLES[current_path]
        
    if allowed_roles:
        if role_user not in allowed_roles:
            target = '/ajuda_sobre' if role_user == 'militar' else '/'
            ui.notify('⛔ Acesso não autorizado para esta página.', color='negative')
            app.storage.user['current_path'] = target
            ui.navigate.to(target)
            return False
            
    return True


def build_layout_base():
    theme.apply_global_styles()
    
    # Se for sessão temporária, atualiza o timestamp de atividade para renovar as 2h
    duration = app.storage.user.get('session_duration')
    if duration and duration > 0:
        import time
        app.storage.user['login_time'] = time.time()
        
    user_cached = get_current_user()
    user = user_cached
    if user_cached and 'id' in user_cached:
        import pandas as pd
        users_df = data_service.get_core_data().get('users', pd.DataFrame())
        if not users_df.empty:
            user_row = users_df[users_df['id'].astype(str) == str(user_cached['id'])]
            if not user_row.empty:
                p_row = user_row.iloc[0]
                user = {
                    'id': p_row.get('id'),
                    'username': p_row.get('username'),
                    'nome_guerra': p_row.get('nome', p_row.get('username')),
                    'role': p_row.get('role', 'compel'),
                    'email': user_cached.get('email', ''),
                    'url_foto': p_row.get('url_foto')
                }
    
    user_name = user.get('nome_guerra') if user else 'Operador'
    role = str(user.get('role', 'compel')).strip().lower() if user else 'compel'
    role_map = {
        'admin': 'Administrador',
        'supervisor': 'Supervisor',
        'operador': 'Operador COMSOC',
        'militar': 'Militar',
        'tv': 'Monitor TV',
        'tv_comcia': 'Monitor TV COMSOC'
    }
    user_posto = user.get('posto') or role_map.get(role, 'Operador')
    
    system_title = "SISGAB"
    ui.run_javascript(f"document.title = '{system_title}'")

    with ui.header().classes('no-shadow relative').style(f'background: {theme.colors["bg_panel"]}; border-bottom: {theme.colors["border"]}; height: 56px; min-height: 56px; padding: 0 12px;'):

        with ui.row().classes('w-full h-full items-center justify-between no-wrap gap-2'):
            # LADO ESQUERDO: Botão de Menu + Logo + Título SISGAB
            with ui.row().classes('items-center gap-2 no-wrap shrink-0'):
                ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white dense')
                ui.image(LOGO_BASE64).style('width: 32px; height: 32px; filter: drop-shadow(0 0 6px rgba(197, 160, 89, 0.9));').classes('shrink-0')
                with ui.column().classes('gap-0 items-start'):
                    ui.label('SISGAB').style(f'color: {theme.colors["primary"]}; font-weight: bold; line-height: 1.1; letter-spacing: 1px; font-size: 0.95rem;').classes('cyber-title text-left no-wrap')
                    ui.label('Comunicação Social • Gabinete').style('font-size: 0.65rem; color: #64748b;').classes('text-left no-wrap gt-xs')



            # LADO DIREITO: Rádio Marinha + Avatar do Usuário
            with ui.row().classes('items-center gap-3 shrink-0 ml-auto no-wrap'):
                # Período de referência ativo
                active_year = app.storage.user.setdefault('ano_letivo_ativo', '2026')
                
                # Notificação inicial de conexão de sessão
                if not app.storage.user.get('year_notified'):
                    user_cached = app.storage.user.get('user_data', {})
                    u_nome = user_cached.get('nome_guerra') or user_cached.get('username') or ''
                    if u_nome and u_nome.lower() != 'militar':
                        ui.notify(
                            f'🛡️ SESSÃO ATIVA — BEM-VINDO AO SISGAB, {u_nome.upper()}!',
                            color='dark',
                            position='top',
                            icon='shield',
                            close_button='OK'
                        )
                    else:
                        ui.notify(f'🟢 Conectado ao SisGAB — Período {active_year}', color='dark', position='top')
                    app.storage.user['year_notified'] = True

                # Player de Rádio Minimalista
                with ui.row().classes('items-center gap-1 no-wrap q-mr-xs gt-xs').style('border-right: 1px solid rgba(197, 160, 89, 0.15); padding-right: 10px;'):
                    ui.html('<audio id="radio-player" src="https://stm0.inovativa.net/listen/radiomarinha/radio.mp3" preload="none"></audio>')
                    ui.label('RÁDIO MARINHA').classes('text-[10px] font-bold tracking-wider text-cyan q-mr-xs gt-sm')
                    
                    class RadioState:
                        playing = False
                        volume = 0.5
                    
                    radio_state = RadioState()
                    
                    def toggle_radio(btn):
                        radio_state.playing = not radio_state.playing
                        if radio_state.playing:
                            btn.props('icon=pause color=cyan')
                            ui.run_javascript("document.getElementById('radio-player').play()")
                            ui.notify('📻 Rádio Marinha Sintonizada', color='cyan', position='bottom-right')
                        else:
                            btn.props('icon=play_arrow color=grey')
                            ui.run_javascript("document.getElementById('radio-player').pause()")
                            
                    def set_radio_volume(val):
                        radio_state.volume = val
                        ui.run_javascript(f"document.getElementById('radio-player').volume = {val}")
                        
                    radio_btn = ui.button(icon='play_arrow').props('flat round color=grey dense').style('font-size: 1.1rem;')
                    radio_btn.on_click(lambda: toggle_radio(radio_btn))
                    with radio_btn:
                        ui.tooltip('Sintonizar Rádio Marinha')
                        
                    ui.icon('volume_up', color='grey-5').classes('text-xs gt-sm')
                    ui.slider(min=0, max=1, step=0.05, value=0.5, on_change=lambda e: set_radio_volume(e.value)).props('dark dense').classes('gt-sm').style('width: 50px; margin: 0; padding: 0;')

                # Informações do Usuário e Avatar
                with ui.column().classes('items-end gap-0 gt-xs'):
                    ui.label(user_name).classes('text-white text-weight-bold text-xs')
                    ui.label(user_posto).classes('text-grey-5 text-xs')
                user_photo = user.get('url_foto') if user else None
                user_avatar_src = user_photo if isinstance(user_photo, str) and user_photo.startswith('http') else 'https://cdn.quasar.dev/img/boy-avatar.png'
                ui.element('div').classes('shadow shrink-0 cursor-pointer').style(
                    f"width: 32px; height: 32px; background-image: url('{user_avatar_src}'); "
                    f"background-size: cover; background-position: center; border-radius: 6px; "
                    f"border: 1.5px solid rgba(197, 160, 89, 0.5); box-shadow: 0 0 10px rgba(197, 160, 89, 0.2);"
                )

    try:
        user_agent = ui.context.client.request.headers.get('user-agent', '').lower()
        is_mobile = any(x in user_agent for x in ['mobile', 'android', 'iphone', 'ipad', 'phone'])
    except Exception:
        is_mobile = False

    # Define largura padrão bem ampla para acomodar confortavelmente todos os menus sem quebrar linha e sem rolagem horizontal
    sidebar_width = 340

    left_drawer = ui.left_drawer(value=not is_mobile).props(f'width={sidebar_width} breakpoint=1024').classes('no-shadow').style(
        f'background: {theme.colors["bg_panel"]}; border-right: {theme.colors["border"]}; overflow-x: hidden;'
    )
    with left_drawer:
        # overflow-x hidden na scroll_area impede barras de rolagem horizontais indesejadas
        with ui.column().classes('w-full h-full justify-between').style('padding: 8px 10px; overflow-x: hidden;'):
            with ui.scroll_area().classes('w-full flex-grow').style('overflow-x: hidden;'):
                with ui.column().classes('w-full gap-1').style('overflow-x: hidden;'):

                    def render_menu_list(categories):
                        user_role = role
                        import pandas as pd
                        perms_df = data_service.get_core_data().get('permissions', pd.DataFrame())
                        
                        # Recupera dicionário de contagem de cliques do usuário atual
                        click_counts = app.storage.user.setdefault('menu_clicks', {})
                        
                        for cat in categories:
                            allowed_items = []
                            for item in cat['items']:
                                path_clean = item['path'].strip('/').replace('/', '_')
                                f_key = f"menu_{path_clean}"
                                row = perms_df[perms_df['feature_key'] == f_key] if not perms_df.empty else pd.DataFrame()
                                
                                if not row.empty:
                                    allowed_roles_str = str(row['allowed_roles'].iloc[0])
                                    allowed_roles = [r.strip().lower() for r in allowed_roles_str.split(',') if r.strip()]
                                    if user_role in allowed_roles:
                                        allowed_items.append(item)
                                else:
                                    if 'roles' in item:
                                        if user_role in item['roles']:
                                            allowed_items.append(item)
                                    else:
                                        allowed_items.append(item)
                            
                            if not allowed_items:
                                continue
                                
                            # Ordena dinamicamente os itens permitidos da categoria com base no número de cliques (decrescente)
                            allowed_items.sort(key=lambda x: click_counts.get(x['path'], 0), reverse=True)
                                
                            with ui.row().classes('w-full items-center gap-2 q-mt-md q-mb-xs px-1 no-wrap').style('border-bottom: 1px solid rgba(197, 160, 89, 0.12); padding-bottom: 4px;'):
                                ui.label(cat['category']).classes('text-xs font-bold tracking-wider cyber-title no-wrap').style('font-size: 11.5px; color: #c5a059; white-space: nowrap;')
                            
                            for item in allowed_items:
                                is_active = app.storage.user.get('current_path') == item['path']
                                
                                if is_active:
                                    block_style = (
                                        f'border: 1.5px solid {theme.colors["primary"]}; '
                                        f'background: rgba(197, 160, 89, 0.08); '
                                        f'box-shadow: 0 0 10px rgba(197, 160, 89, 0.15);'
                                    )
                                    icon_color = theme.colors['primary']
                                    text_color = theme.colors['primary']
                                else:
                                    block_style = (
                                        f'border: 1px solid rgba(197, 160, 89, 0.08); '
                                        f'background: rgba(12, 18, 30, 0.25);'
                                    )
                                    icon_color = '#64748b'
                                    text_color = '#e2e8f0'
                                
                                # Calcula badge de pendentes se for Homologar Pautas
                                badge_count = 0
                                if item['path'] == '/comsoc_homologar':
                                    from database import get_db_connection
                                    db_b = get_db_connection()
                                    if db_b:
                                        try:
                                            res_b = db_b.table('demandas_comunicacao').select('id').eq('status', 'pendente').execute()
                                            if res_b.data:
                                                badge_count = len(res_b.data)
                                        except Exception as e:
                                            print(f"[MENU BADGE ERR] {e}")
                                    
                                # Função para registrar clique e redirecionar
                                def make_click_handler(target_path=item['path'], new_tab=item.get('new_tab', False)):
                                    def on_click():
                                        current_clicks = app.storage.user.setdefault('menu_clicks', {})
                                        current_clicks[target_path] = current_clicks.get(target_path, 0) + 1
                                        app.storage.user['menu_clicks'] = current_clicks
                                        ui.navigate.to(target_path, new_tab=new_tab)
                                    return on_click
                                    
                                with ui.button(on_click=make_click_handler()).props('flat no-caps').classes('w-full q-pa-none q-ma-none text-left').style('margin-bottom: 2px;'):
                                    with ui.row().classes(
                                        'w-full items-center gap-3 p-2 rounded-xl transition-all hover:border-primary/45 hover:bg-primary/5 no-wrap'
                                    ).style(block_style):
                                        ui.icon(item['icon']).classes('text-lg flex-shrink-0').style(f'color: {icon_color};')
                                        with ui.column().classes('gap-0 flex-grow min-w-0 leading-none'):
                                            with ui.row().classes('items-center gap-2 no-wrap w-full justify-between'):
                                                ui.label(item['name']).classes('text-[10.5px] font-bold no-wrap').style(f'color: {text_color}; white-space: nowrap;')
                                                if badge_count > 0:
                                                    ui.badge(str(badge_count)).props('color=red-7 dense text-color=white').classes('text-[8px] q-px-sm')
                                            if item.get('subtitle'):
                                                ui.label(item['subtitle']).classes('text-[7.8px] q-mt-xs no-wrap').style('color: #64748b; white-space: nowrap;')

                    render_menu_list(sisgab_menu_categories)
                
            # ── RODAPÉ DA SIDEBAR: Alterar Senha & Sair do Sistema ──
            with ui.column().classes('w-full gap-1 q-pt-sm border-t border-gray-800/60 q-mt-xs shrink-0'):
                with ui.button(on_click=lambda: open_change_password_dialog(user)).props('flat no-caps').classes('w-full q-pa-none text-left'):
                    with ui.row().classes('w-full items-center gap-3 p-2 rounded-xl border border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10 no-wrap'):
                        ui.icon('vpn_key').classes('text-lg text-amber-500 flex-shrink-0')
                        ui.label('Alterar Minha Senha').classes('text-[11px] font-bold text-amber-400 no-wrap')

                with ui.button(on_click=logout).props('flat no-caps').classes('w-full q-pa-none text-left'):
                    with ui.row().classes('w-full items-center gap-3 p-2 rounded-xl border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 no-wrap'):
                        ui.icon('logout').classes('text-lg text-red-500 flex-shrink-0')
                        ui.label('Sair do Sistema').classes('text-[11px] font-bold text-red-400 no-wrap')

    return ui.column().classes('w-full h-full p-0')


def build_layout(page_func, **extra_kwargs):
    import inspect
    is_async = inspect.iscoroutinefunction(page_func)
    
    if is_async:
        async def wrapper():
            if not run_auth_checks():
                return
            container = build_layout_base()
            with container:
                await page_func(**extra_kwargs)
        return wrapper
    else:
        def wrapper():
            if not run_auth_checks():
                return
            container = build_layout_base()
            with container:
                page_func(**extra_kwargs)
        return wrapper


def open_change_password_dialog(user):
    with ui.dialog() as pwd_dialog, ui.card().classes('w-96 q-pa-md').style(
        f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]};'
    ):
        with ui.column().classes('w-full gap-4'):
            with ui.row().classes('items-center gap-2 w-full justify-between'):
                ui.label('🔑 ALTERAR MINHA SENHA').classes('text-white text-md font-black cyber-title')
                ui.icon('lock_reset', size='1.5rem').style('color: #ffb300;')
            ui.separator().style('background-color: rgba(255, 179, 0, 0.15);')
            
            ui.label(f"Militar: {user.get('nome_guerra', '').upper()}").classes('text-xs text-grey-4')
            current_pwd = ui.input('Senha Atual', password=True).props('dark outlined dense w-full')
            new_pwd = ui.input('Nova Senha', password=True).props('dark outlined dense w-full')
            confirm_pwd = ui.input('Confirmar Nova Senha', password=True).props('dark outlined dense w-full')
            pwd_error = ui.label('').classes('text-xs text-red w-full text-center')
            
            def handle_password_change():
                if not current_pwd.value:
                    pwd_error.text = 'Informe a sua senha atual.'
                    return
                if not new_pwd.value or len(new_pwd.value) < 6:
                    pwd_error.text = 'A nova senha deve conter no mínimo 6 caracteres.'
                    return
                if new_pwd.value != confirm_pwd.value:
                    pwd_error.text = 'As novas senhas digitadas não coincidem.'
                    return
                
                from database import get_db_connection, get_service_db_connection
                db_conn = get_service_db_connection() or get_db_connection()
                if not db_conn:
                    ui.notify('Sem conexão com banco de dados', color='red')
                    return
                
                try:
                    import bcrypt
                    user_email = user.get('email')
                    nome_guerra = user.get('nome_guerra')
                    user_id = user.get('id')
                    
                    # 1. Valida a senha atual no banco
                    res_m = None
                    if user_id:
                        res_m = db_conn.table('efetivo').select('senha_hash').eq('id', user_id).execute()
                    if (not res_m or not res_m.data) and user_email:
                        res_m = db_conn.table('efetivo').select('senha_hash').eq('email', user_email).execute()
                    if (not res_m or not res_m.data) and nome_guerra:
                        res_m = db_conn.table('efetivo').select('senha_hash').eq('nome_guerra', nome_guerra.upper()).execute()
                        
                    stored_hash = res_m.data[0].get('senha_hash', '') if (res_m and res_m.data) else ''
                    
                    if stored_hash and (stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$')):
                        if not bcrypt.checkpw(current_pwd.value.encode('utf-8'), stored_hash.encode('utf-8')):
                            pwd_error.text = 'Senha atual incorreta.'
                            return

                    # 2. Gera novo hash e atualiza
                    pwd_hash = bcrypt.hashpw(new_pwd.value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                    updated_in_db = False

                    # Atualiza na tabela efetivo
                    try:
                        if user_id:
                            db_conn.table('efetivo').update({'senha_hash': pwd_hash}).eq('id', user_id).execute()
                            updated_in_db = True
                        elif user_email:
                            db_conn.table('efetivo').update({'senha_hash': pwd_hash}).eq('email', user_email).execute()
                            updated_in_db = True
                        elif nome_guerra:
                            db_conn.table('efetivo').update({'senha_hash': pwd_hash}).eq('nome_guerra', nome_guerra.upper()).execute()
                            updated_in_db = True
                    except Exception as ef_err:
                        print(f"[EFETIVO PWD UPDATE ERR] {ef_err}")

                    # Atualiza na tabela users se existir id
                    try:
                        if user_id:
                            db_conn.table('users').update({'senha_hash': pwd_hash}).eq('id', user_id).execute()
                            updated_in_db = True
                    except Exception as u_err:
                        print(f"[USERS PWD UPDATE ERR] {u_err}")

                    if updated_in_db:
                        ui.notify('Sua senha foi alterada com sucesso!', color='success')
                        pwd_dialog.close()
                    else:
                        pwd_error.text = "Erro ao localizar registro do usuário para atualização."
                except Exception as err:
                    pwd_error.text = f"Erro ao atualizar: {err}"

            
            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Cancelar', on_click=pwd_dialog.close).props('flat color=grey')
                ui.button('Salvar Senha', on_click=handle_password_change).props('unelevated color=amber-9 text-color=black')
    pwd_dialog.open()


def logout():
    app.storage.user.clear()
    ui.notify('Session encerrada', color='info')
    ui.navigate.to('/login')


@ui.page('/')
def index_page():
    app.storage.user['current_path'] = '/'
    build_layout(painel_comando.render_page)()


@ui.page('/admin')
def admin_page():
    app.storage.user['current_path'] = '/admin'
    build_layout(admin.render_page)()


@ui.page('/assistente_ia')
def assistente_ia_page():
    app.storage.user['current_path'] = '/assistente_ia'
    build_layout(assistente_ia.render_page)()


@ui.page('/config')
def config_page():
    app.storage.user['current_path'] = '/config'
    build_layout(config.render_page)()


@ui.page('/admin_panel')
def admin_panel_page():
    app.storage.user['current_path'] = '/admin_panel'
    build_layout(admin_panel.render_page)()


@ui.page('/ajuda_sobre')
def ajuda_sobre_page():
    app.storage.user['current_path'] = '/ajuda_sobre'
    build_layout(ajuda_sobre.render_page)()


@ui.page('/comsoc_noticias')
def comsoc_noticias_page():
    app.storage.user['current_path'] = '/comsoc_noticias'
    build_layout(comsoc_noticias.render_page)()


@ui.page('/comsoc_demandas')
def comsoc_demandas_page(autofill: str = None):
    app.storage.user['current_path'] = '/comsoc_demandas'
    if autofill:
        # Repassa dados recebidos para o formulário
        build_layout(lambda: comsoc_demandas.render_page(autofill=autofill))()
    else:
        build_layout(comsoc_demandas.render_page)()


@ui.page('/comsoc_tarefas')
def comsoc_tarefas_page():
    app.storage.user['current_path'] = '/comsoc_tarefas'
    build_layout(comsoc_tarefas.render_page)()


@ui.page('/comsoc_homologar')
def comsoc_homologar_page():
    app.storage.user['current_path'] = '/comsoc_homologar'
    import comsoc_homologar
    build_layout(comsoc_homologar.render_page)()


@ui.page('/comsoc_cautela')
def comsoc_cautela_page():
    app.storage.user['current_path'] = '/comsoc_cautela'
    build_layout(comsoc_cautela.render_page)()


@ui.page('/comsoc_brindes')
def comsoc_brindes_page():
    app.storage.user['current_path'] = '/comsoc_brindes'
    build_layout(comsoc_brindes.render_page)()


@ui.page('/comsoc_assentos')
def comsoc_assentos_page():
    app.storage.user['current_path'] = '/comsoc_assentos'
    build_layout(comsoc_assentos.render_page)()


@ui.page('/comsoc_galeria')
def comsoc_galeria_page(evento_id: str = None):
    app.storage.user['current_path'] = '/comsoc_galeria'
    build_layout(comsoc_galeria.render_page, evento_id=evento_id)()


@ui.page('/comsoc_historico')
def comsoc_historico_page():
    app.storage.user['current_path'] = '/comsoc_historico'
    build_layout(comsoc_historico.render_page)()


@ui.page('/comsoc_aniversariantes')
def comsoc_aniversariantes_page():
    app.storage.user['current_path'] = '/comsoc_aniversariantes'
    build_layout(comsoc_aniversariantes.render_page)()


@ui.page('/agenda_geral')
def agenda_geral_page():
    """Redireciona para o Painel de Comando unificado."""
    ui.navigate.to('/')


@ui.page('/presenca')
def presenca_page():
    app.storage.user['current_path'] = '/presenca'
    build_layout(modulo_presenca.render_page)()


@ui.page('/smart_editor')
def smart_editor_page():
    app.storage.user['current_path'] = '/smart_editor'
    build_layout(smart_editor.render_page)()


@ui.page('/comsoc_rsvp')
def comsoc_rsvp_page():
    app.storage.user['current_path'] = '/comsoc_rsvp'
    build_layout(comsoc_rsvp.render_page)()


@ui.page('/qrcode_generator')
def qrcode_generator_page():
    app.storage.user['current_path'] = '/qrcode_generator'
    build_layout(qrcode_generator.render_page)()


@ui.page('/telegram_metrics')
def telegram_metrics_page():
    app.storage.user['current_path'] = '/telegram_metrics'
    build_layout(telegram_metrics.render_page)()


@ui.page('/jarvis')
def jarvis_page():
    app.storage.user['current_path'] = '/jarvis'
    build_layout(jarvis_voice.render_page)()


@ui.page('/rsvp/{token}')
def rsvp_public_page(token: str, request: Request):
    """Página pública e solene de RSVP com design VIP/Institucional, Hero Banner e alta acessibilidade."""
    theme.apply_global_styles()
    from database import get_rsvp_by_token, update_rsvp_response
    from comsoc_assentos import parse_almirantado_stars
    convite = get_rsvp_by_token(token)

    if not convite:
        with ui.column().classes('w-full min-h-screen items-center justify-center q-pa-md text-center').style('background: radial-gradient(circle, #1e1b4b 0%, #0b0f19 100%);'):
            ui.icon('gavel', size='4rem', color='red-5')
            ui.label('CONVITE INVÁLIDO OU EXPIRADO').classes('cyber-title text-xl font-bold text-red-4 q-mt-md')
            ui.label('O link de confirmação acessado não foi localizado no protocolo do Gabinete.').classes('text-xs text-grey-4')
        return

    evento = convite.get('evento') or {}
    nome_aut = convite.get('nome_autoridade', 'Excelentíssimo(a) Convidado(a)')
    posto_aut = convite.get('posto_graduacao', '')
    almirantado = parse_almirantado_stars(posto_aut)
    
    banner_url = evento.get('banner_url') or 'assets/brasao_cgcfn.png'

    with ui.column().classes('w-full min-h-screen items-center justify-center p-2 sm:p-6 bg-transparent').style('font-family: "Outfit", sans-serif; position: relative; z-index: 10;'):
        # CARTÃO CENTRAL DE LUXO COM SOMBRA DOURADA E BRILHO INSTITUCIONAL
        with ui.card().classes('w-full max-w-2xl bg-slate-900/95 border-2 border-amber-500/40 rounded-3xl shadow-2xl overflow-hidden').style('box-shadow: 0 0 60px rgba(245, 158, 11, 0.2); backdrop-filter: blur(16px);'):

            
            # HERO BANNER / CABEÇALHO DE PRESTÍGIO
            if banner_url and len(banner_url) > 10 and banner_url != 'assets/brasao_cgcfn.png':
                banner_bg = f'background: linear-gradient(180deg, rgba(15, 23, 42, 0.5) 0%, rgba(15, 23, 42, 0.95) 100%), url("{banner_url}") center/cover no-repeat;'
            else:
                banner_bg = 'background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);'

            with ui.element('div').classes('w-full relative min-h-[180px] flex items-center justify-center text-center p-6').style(banner_bg):

                with ui.column().classes('w-full items-center gap-1.5 z-10'):
                    ui.image('assets/brasao_cgcfn.png').style('width: 72px; height: auto; filter: drop-shadow(0 0 12px rgba(245, 158, 11, 0.5));')
                    ui.label('MARINHA DO BRASIL').classes('text-xs font-black text-amber-4 tracking-[4px] uppercase q-mt-xs')
                    ui.label('GABINETE DO COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS').classes('text-[10px] font-bold text-cyan-3 tracking-[2px] uppercase opacity-90')

            ui.separator().style('background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.5), transparent); height: 2px;')

            # CORPO DO CONVITE
            with ui.column().classes('w-full p-4 sm:p-8 items-center text-center gap-4'):
                
                # INSÍGNIA / ESTRELAS DE PRECEDÊNCIA DO POSTO
                if almirantado.get('stars'):
                    ui.label(almirantado['stars']).classes('text-amber-4 text-xl font-bold tracking-widest')
                
                with ui.column().classes('gap-0 items-center'):
                    if posto_aut:
                        ui.label(posto_aut.upper()).classes('text-xs font-black text-amber-4 tracking-widest')
                    ui.label(nome_aut.upper()).classes('text-xl sm:text-2xl font-black text-white tracking-wide leading-snug')

                # CARTÃO DE DETALHES DO EVENTO
                if evento:
                    with ui.card().classes('w-full p-4 sm:p-5 bg-black/60 border border-cyan-500/30 rounded-2xl text-left gap-3 shadow-inner'):
                        ui.label(evento.get('nome_evento', 'SOLENIDADE INSTITUCIONAL').upper()).classes('text-sm font-black text-cyan-4 tracking-wider')
                        
                        if evento.get('descricao'):
                            ui.label(evento['descricao']).classes('text-xs text-grey-3 italic leading-relaxed')

                        ui.separator().style('background-color: rgba(6, 182, 212, 0.2);')
                        
                        with ui.column().classes('gap-2 text-xs sm:text-sm'):
                            with ui.row().classes('items-center gap-2 text-grey-2'):
                                ui.icon('event', size='1.2rem', color='cyan-4')
                                ui.label(f"Data e Horário: ").classes('font-bold text-grey-4')
                                ui.label(f"{evento.get('data_evento','')} às {evento.get('hora_evento','')}").classes('font-black text-white')
                            
                            with ui.row().classes('items-center gap-2 text-grey-2'):
                                ui.icon('place', size='1.2rem', color='cyan-4')
                                ui.label(f"Local: ").classes('font-bold text-grey-4')
                                ui.label(f"{evento.get('local_evento','')}").classes('font-bold text-white')

                            with ui.row().classes('items-center gap-2 text-amber-4'):
                                ui.icon('checkroom', size='1.2rem', color='amber-4')
                                ui.label(f"Traje Exigido: ").classes('font-bold text-grey-4')
                                ui.label(f"{evento.get('traje_exigido','')}").classes('font-black text-amber-3')


                ui.separator().style('background: linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.3), transparent);')

                dynamic_area = ui.column().classes('w-full items-center text-center gap-4')

                def render_content(show_conclusion=False, final_status=None):
                    dynamic_area.clear()
                    st = final_status or convite.get('status', 'enviado')

                    with dynamic_area:
                        if show_conclusion or (st in ('confirmado', 'justificado', 'recusado') and not show_conclusion):
                            # TELA SOLENE DE CONCLUSÃO DE SESSÃO DO PROTOCOLO
                            with ui.column().classes('w-full items-center text-center gap-4 q-py-md'):
                                if st == 'confirmado':
                                    ui.icon('check_circle', size='4.5rem', color='emerald-4')
                                    ui.label('PRESENÇA CONFIRMADA NO PROTOCOLO').classes('text-lg sm:text-xl font-black text-emerald-4 cyber-title')
                                    ui.label('O Comandante-Geral do Corpo de Fuzileiros Navais estimas os cumprimentos e agradece a confirmação de Vossa Excelência.').classes('text-xs sm:text-sm text-grey-2 leading-relaxed font-semibold')
                                    
                                    with ui.card().classes('w-full p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-2xl text-left gap-1.5'):
                                        ui.label('📧 COMPROVANTE & ORIENTAÇÕES:').classes('text-xs font-black text-emerald-4')
                                        ui.label('Um e-mail de confirmação contendo os detalhes do protocolo e orientação de acesso foi enviado. Vossa Excelência poderá alterar sua resposta quando desejar acessando este mesmo link.').classes('text-xs text-grey-3 leading-relaxed')

                                elif st in ('justificado', 'recusado'):
                                    ui.icon('cancel', size='4.5rem', color='red-4')
                                    ui.label('JUSTIFICATIVA REGISTRADA').classes('text-lg sm:text-xl font-black text-red-4 cyber-title')
                                    ui.label('A justificativa de ausência de Vossa Excelência foi formalmente registrada no protocolo do evento.').classes('text-xs sm:text-sm text-grey-2 leading-relaxed font-semibold')

                                else:
                                    ui.icon('schedule', size='4.5rem', color='amber-4')
                                    ui.label('RESPOSTA MANTIDA EM ABERTO').classes('text-lg sm:text-xl font-black text-amber-4 cyber-title')
                                    ui.label('A solicitação continuará aguardando retorno no sistema do Gabinete. Vossa Excelência poderá retornar a este link a qualquer momento.').classes('text-xs sm:text-sm text-grey-2 leading-relaxed font-semibold')

                                ui.separator().style('background-color: rgba(255, 255, 255, 0.1);').classes('w-full q-my-xs')

                                with ui.row().classes('w-full justify-center gap-3 q-mt-xs wrap'):
                                    ui.button('✏️ ALTERAR MINHA RESPOSTA', on_click=lambda: render_content(show_conclusion=False, final_status='pendente')).props('outline color=amber text-color=white bold icon=edit').style('font-size: 0.85rem; padding: 10px 20px; border-radius: 12px;')
                                    ui.button('📧 FECHAR ESTA PÁGINA', on_click=lambda: ui.run_javascript('window.close()')).props('unelevated color=grey-8 text-color=white bold icon=close').style('font-size: 0.85rem; padding: 10px 20px; border-radius: 12px;')

                        else:
                            # FORMULÁRIO ATIVO DE RESPOSTA (SENIOR ACCESSIBILITY & DESIGN VIP)
                            with ui.column().classes('w-full gap-4 items-center'):
                                # PAINEL DE ACOMPANHANTES E COMITIVAS DE LUXO
                                with ui.column().classes('w-full gap-3 text-left bg-black/60 p-4 sm:p-5 rounded-2xl border border-amber-500/30 shadow-inner'):
                                    acomp_chk = ui.checkbox('Irei acompanhado(a) a esta solenidade', value=bool(convite.get('acompanhantes_count'))).props('dark').style('font-size: 0.95rem; font-weight: 800; color: #fbbf24;')
                                    
                                    acomp_container = ui.column().classes('w-full gap-3 q-mt-xs')
                                    acomp_container.bind_visibility_from(acomp_chk, 'value')

                                    selected_count = {'val': int(convite.get('acompanhantes_count', 1) or 1)}
                                    initial_names = convite.get('acompanhantes_nomes','') or ''

                                    with acomp_container:
                                        ui.label('SELECIONE O NÚMERO DE ACOMPANHANTES OU COMITIVA:').classes('text-[11px] font-bold text-grey-4 tracking-wider')
                                        
                                        # Seletores estilo pílula rápida + Input Customizado
                                        with ui.row().classes('w-full gap-2 items-center wrap'):
                                            btn_pills = {}
                                            num_input = ui.number(value=selected_count['val'], min=1, max=50).props('dark outlined dense').classes('w-24').style('font-size: 0.9rem;')

                                            def update_count(val):
                                                selected_count['val'] = int(val or 1)
                                                num_input.value = selected_count['val']
                                                render_name_fields()

                                            for n in [1, 2, 3, 4]:
                                                btn_pills[n] = ui.button(f'{n}', on_click=lambda v=n: update_count(v)).props('unelevated dense').style('min-width: 38px; border-radius: 8px; font-weight: 900;')

                                            ui.label('pessoas').classes('text-xs text-grey-4 font-bold')

                                        num_input.on('update:model-value', lambda e: update_count(e.value))

                                        names_area = ui.column().classes('w-full gap-2 q-mt-xs')

                                        def render_name_fields():
                                            names_area.clear()
                                            cnt = selected_count['val']
                                            
                                            # Atualiza estilo das pílulas
                                            for n, b in btn_pills.items():
                                                if n == cnt:
                                                    b.style('background: #f59e0b !important; color: #000 !important; min-width: 38px; border-radius: 8px; font-weight: 900;')
                                                else:
                                                    b.style('background: rgba(255,255,255,0.1) !important; color: #fff !important; min-width: 38px; border-radius: 8px; font-weight: 900;')

                                            with names_area:
                                                if cnt <= 4:
                                                    # Modo Individual com Nome + Parentesco/Cargo opcional
                                                    existing_list = [n.strip() for n in initial_names.split(',') if n.strip()]
                                                    inputs_list = []
                                                    for i in range(cnt):
                                                        val_full = existing_list[i] if i < len(existing_list) else ''
                                                        # Extrai parentesco se estiver entre parênteses
                                                        p_name = val_full
                                                        p_rel = ''
                                                        if '(' in val_full and ')' in val_full:
                                                            p_name = val_full.split('(')[0].strip()
                                                            p_rel = val_full.split('(')[1].replace(')', '').strip()

                                                        with ui.card().classes('w-full p-3 bg-black/40 border border-grey-800 rounded-xl gap-2 q-my-xs'):
                                                            ui.label(f'ACOMPANHANTE {i+1}').classes('text-[10px] font-bold text-amber-4 tracking-wider')
                                                            with ui.row().classes('w-full gap-2 items-center wrap'):
                                                                inp_n = ui.input('Nome Completo', value=p_name, placeholder='Ex: Maria Silva').props('dark outlined dense').classes('w-full sm:w-[58%]').style('font-size: 0.85rem;')
                                                                inp_r = ui.input('Parentesco / Vínculo (Opcional)', value=p_rel, placeholder='Ex: Esposa, Filho, Ajudante').props('dark outlined dense').classes('w-full sm:w-[38%]').style('font-size: 0.85rem;')
                                                                inputs_list.append((inp_n, inp_r))
                                                    names_area.inputs_ref = inputs_list
                                                    names_area.mode = 'individual'
                                                else:
                                                    # Modo Comitiva / Delegação (5 a 50+ acompanhantes)
                                                    ui.label(f'📝 RELAÇÃO DA COMITIVA ({cnt} INTEGRANTES):').classes('text-xs font-bold text-cyan-4')
                                                    ui.label('Informe ou cole a lista de nomes da delegação abaixo (um por linha ou por vírgula):').classes('text-[11px] text-grey-4')
                                                    text_comitiva = ui.textarea(value=initial_names, placeholder='Ex:\n1. Cap. Lucas Silva\n2. Sra. Ana Souza\n3. Maj. Marcos Oliveira').props('dark outlined w-full').style('font-size: 0.88rem;')
                                                    names_area.textarea_ref = text_comitiva
                                                    names_area.mode = 'comitiva'

                                        render_name_fields()


                                obs_input = ui.input('Observações / Restrições Especiais (Opcional)', value=convite.get('observacoes','') or '', placeholder='Ex: Restrição de mobilidade ou dieta especial').props('dark outlined w-full').style('font-size: 0.9rem;')

                                def submit_resposta(choice):
                                    try:
                                        client_ip = request.client.host if request.client else ''
                                        ac_count = selected_count['val'] if acomp_chk.value else 0
                                        
                                        if acomp_chk.value:
                                            if getattr(names_area, 'mode', '') == 'individual':
                                                names_arr = []
                                                for inp_n, inp_r in getattr(names_area, 'inputs_ref', []):
                                                    nm = inp_n.value.strip() if inp_n.value else ''
                                                    rel = inp_r.value.strip() if inp_r.value else ''
                                                    if nm:
                                                        if rel:
                                                            names_arr.append(f"{nm} ({rel})")
                                                        else:
                                                            names_arr.append(nm)
                                                ac_nome = ', '.join(names_arr)
                                            else:
                                                ac_nome = getattr(names_area, 'textarea_ref', ui.input()).value.strip()
                                        else:
                                            ac_nome = ''

                                        
                                        update_rsvp_response(token, choice, ac_count, ac_nome, obs_input.value, client_ip)
                                        convite['status'] = choice
                                        render_content(show_conclusion=True, final_status=choice)
                                    except Exception as err:
                                        ui.notify(f"Erro ao registrar resposta: {err}", color='red')


                                # BOTÕES VIP DE ALTO CONTRASTE E TOUCH-FRIENDLY
                                with ui.column().classes('w-full gap-3 q-mt-sm items-center'):
                                    ui.button(
                                        '✅ CONFIRMAR MINHA PRESENÇA',
                                        on_click=lambda: submit_resposta('confirmado')
                                    ).style(
                                        'background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #ffffff !important; '
                                        'font-size: 1.05rem !important; font-weight: 900 !important; '
                                        'padding: 16px 24px !important; width: 100% !important; border-radius: 14px !important; '
                                        'box-shadow: 0 4px 25px rgba(16, 185, 129, 0.4) !important;'
                                    )

                                    with ui.row().classes('w-full justify-between gap-3 wrap-mobile'):
                                        ui.button(
                                            '❌ JUSTIFICAR AUSÊNCIA',
                                            on_click=lambda: submit_resposta('justificado')
                                        ).classes('w-full sm:w-[48%]').style(
                                            'background-color: #dc2626 !important; color: #ffffff !important; '
                                            'font-size: 0.9rem !important; font-weight: 900 !important; '
                                            'padding: 14px 16px !important; border-radius: 12px !important;'
                                        )

                                        ui.button(
                                            '⏳ DECIDIR MAIS TARDE',
                                            on_click=lambda: submit_resposta('pendente')
                                        ).classes('w-full sm:w-[48%]').style(
                                            'background-color: #d97706 !important; color: #ffffff !important; '
                                            'font-size: 0.9rem !important; font-weight: 900 !important; '
                                            'padding: 14px 16px !important; border-radius: 12px !important;'
                                        )

                render_content()


@ui.page('/evento/{id_evento}')
def evento_publico_page(id_evento: str):
    """Portal do Convidado — rota pública e dinâmica para entrega de fotos em tempo real via IA."""
    portal_convidado.render_page(id_evento)


@ui.page('/sisgab_tv')
def sisgab_tv_page():
    """Modo TV/Monitor do SisGAB — sem barra lateral, tela cheia."""
    if not is_authenticated():
        ui.navigate.to('/login')
        return
    app.storage.user['current_path'] = '/sisgab_tv'
    app.storage.user['tv_lock_active'] = True
    theme.apply_global_styles()
    sisgab_tv.render_page()



@ui.page('/login')
def login_page(request: Request):
    if is_authenticated():
        role_user = str(app.storage.user.get('user_data', {}).get('role', '')).strip().lower()
        target_path = '/sisgab_tv' if role_user in ('tv', 'tv_comcia') else '/'
        ui.navigate.to(target_path)
        return

    theme.apply_global_styles()
    
    # Dialog de Solicitação de Acesso
    with ui.dialog() as reg_dialog, ui.card().classes('w-96 q-pa-md').style(
        f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]};'
    ):
        with ui.column().classes('w-full items-center gap-4'):
            ui.label('📝 Solicitar Acesso').classes('text-white text-lg font-bold')
            ui.label('Preencha os dados para solicitar acesso').classes('text-grey-5 text-xs text-center')
            
            reg_email = ui.input('E-mail').props('dark dense outlined w-full')
            reg_pwd = ui.input('Senha', password=True).props('dark dense outlined w-full')
            reg_guerra = ui.input('Nome de Guerra com Posto/Graduação', placeholder='Ex: SG SILVA, TEN COSTA').props('dark dense outlined w-full')
            
            reg_error = ui.label('').classes('text-caption text-red')
            
            def submit_registration():
                if not reg_email.value or not reg_pwd.value or not reg_guerra.value:
                    reg_error.text = 'Preencha todos os campos'
                    return
                if len(reg_pwd.value) < 6:
                    reg_error.text = 'A senha deve ter no mínimo 6 caracteres'
                    return
                
                from database import get_db_connection, get_service_db_connection
                db_conn = get_db_connection()
                if db_conn:
                    try:
                        svc_conn = get_service_db_connection()
                        auth_id = None
                        created_via_admin = False
                        
                        # 1. Tenta criar via Service Role Admin (bypassa confirmação de e-mail e rate limit)
                        if svc_conn and hasattr(svc_conn, 'auth') and hasattr(svc_conn.auth, 'admin'):
                            try:
                                res = svc_conn.auth.admin.create_user({
                                    "email": reg_email.value,
                                    "password": reg_pwd.value,
                                    "email_confirm": True
                                })
                                if res and res.user:
                                    auth_id = res.user.id
                                    created_via_admin = True
                            except Exception as admin_err:
                                print(f"[ADMIN SIGNUP REGISTER ERR] {admin_err}")
                                
                        # 2. Se falhar ou não tiver a chave, tenta signup normal
                        if not auth_id:
                            try:
                                res = db_conn.auth.sign_up({"email": reg_email.value, "password": reg_pwd.value})
                                if res and res.user:
                                    auth_id = res.user.id
                            except Exception as signup_err:
                                print(f"[NORMAL SIGNUP REGISTER ERR] {signup_err}")
                                
                        # 3. Se ainda assim falhar (ex: rate limit exceeded), cria no banco local/Postgres diretamente
                        if not auth_id:
                            import uuid
                            auth_id = str(uuid.uuid4())
                            ui.notify('Limite de e-mails atingido. Criando conta no banco local...', color='warning', duration=6)
                            
                        # Determina conexão a ser usada para as inserções no banco
                        svc_conn_to_use = svc_conn if svc_conn else db_conn
                        
                        # 1. Cria a solicitação pendente em ambas as tabelas (RegistrationRequests e registration_requests)
                        for tbl in ['RegistrationRequests', 'registration_requests']:
                            try:
                                svc_conn_to_use.table(tbl).insert({
                                    "id": auth_id,
                                    "email": reg_email.value,
                                    "nome_completo": reg_guerra.value.upper(),
                                    "nome_guerra": reg_guerra.value.upper(),
                                    "status": "pending"
                                }).execute()
                            except Exception as req_err:
                                print(f"[REG REQUEST {tbl} ERR] {req_err}")
                            
                        # 2. Cria o perfil de acesso padrão (militar) em ambas as tabelas (Users e users)
                        for tbl in ['Users', 'users']:
                            try:
                                svc_conn_to_use.table(tbl).insert({
                                    "id": auth_id,
                                    "username": reg_email.value.split('@')[0],
                                    "nome": reg_guerra.value.upper(),
                                    "role": "militar"
                                }).execute()
                            except Exception as users_err:
                                print(f"[REG USERS {tbl} ERR] {users_err}")
                            
                        # 3. Cria o hash e insere na tabela efetivo
                        import bcrypt
                        pwd_hash = bcrypt.hashpw(reg_pwd.value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                        try:
                            svc_conn_to_use.table('efetivo').insert({
                                'nome_guerra': reg_guerra.value.upper(),
                                'email': reg_email.value,
                                'senha_hash': pwd_hash,
                                'role': 'militar'
                            }).execute()
                        except Exception as e_ef:
                            print(f"[REG EFETIVO ERR] {e_ef}")
                            
                        try:
                            from notifications_manager import notify_telegram
                            alert_txt = (
                                f"🔔 **NOVA SOLICITAÇÃO DE ACESSO**\n\n"
                                f"👤 Nome: {reg_guerra.value.upper()}\n"
                                f"📧 E-mail: {reg_email.value}\n"
                                f"⚡ Papel Inicial: `militar` (Militar / Efetivo em Geral).\n"
                                f"⚙️ Ação: O administrador pode alterar as permissões deste usuário no painel a qualquer momento."
                            )
                            notify_telegram(alert_txt, "new_user", role_required="admin", request_id=auth_id)
                        except Exception as e_notif:
                            print(f"[MAIN REG NOTIFY ERROR] {e_notif}")
                            
                        ui.notify('Solicitação enviada e acesso inicial liberado! Efetue o login.', color='success')
                        reg_dialog.close()
                    except Exception as err:
                        reg_error.text = f'Erro: {err}'
                else:
                    ui.notify('Solicitação simulada com sucesso (modo offline)', color='warning')
                    reg_dialog.close()
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=reg_dialog.close).props('flat color=grey')
                ui.button('Enviar', on_click=submit_registration).props('unelevated color=amber-9 text-color=black')

    # Dialog de Recuperação de Senha por Código PIN (6 Dígitos)
    with ui.dialog() as rec_pwd_dialog, ui.card().classes('w-96 q-pa-md').style(
        f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]};'
    ):
        with ui.column().classes('w-full items-center gap-3'):
            ui.label('🔑 RECUPERAR MINHA SENHA').classes('text-white text-md font-bold cyber-title')
            
            # Container do Passo 1: Solicitar Código PIN
            step1_container = ui.column().classes('w-full gap-2 items-center')
            # Container do Passo 2: Inserir PIN e Nova Senha
            step2_container = ui.column().classes('w-full gap-2 items-center').style('display: none;')
            
            rec_error = ui.label('').classes('text-xs text-red text-center w-full')
            
            with step1_container:
                ui.label('Insira seu e-mail cadastrado para receber o código PIN de 6 dígitos.').classes('text-grey-5 text-xs text-center q-mb-xs')
                rec_email = ui.input('E-mail Cadastrado').props('dark dense outlined w-full')
                
                def request_pin():
                    if not rec_email.value or '@' not in rec_email.value:
                        rec_error.text = 'Insira um e-mail válido'
                        return
                    
                    from database import generate_recovery_pin_for_email, get_db_connection
                    pin_generated = generate_recovery_pin_for_email(rec_email.value)
                    
                    if not pin_generated:
                        rec_error.text = 'Erro ao gerar código PIN.'
                        return
                        
                    sent_email = False
                    try:
                        from notifications_manager import send_recovery_pin_email
                        sent_email = send_recovery_pin_email(rec_email.value, pin_generated)
                    except Exception as email_err:
                        print(f"[RECOVERY DIRECT MAIL ERR] {email_err}")
                        
                    db_conn = get_db_connection()
                    if db_conn and not sent_email:
                        try:
                            proto = request.headers.get('x-forwarded-proto', request.url.scheme)
                            host = request.headers.get('x-forwarded-host') or request.headers.get('host') or request.url.netloc
                            redirect_url = f"{proto}://{host}/"
                            db_conn.auth.reset_password_for_email(rec_email.value, options={"redirect_to": redirect_url})
                            sent_email = True
                        except Exception as mail_err:
                            print(f"[RECOVERY MAIL ERR] {mail_err}")

                            
                    # Notificação segura no Telegram:
                    try:
                        from notifications_manager import notify_telegram, send_notification_to_user
                        user_tg_id = None
                        
                        # Tenta buscar o Telegram ID do próprio usuário que solicitou
                        if db_conn:
                            res_m = db_conn.table('efetivo').select('telegram_id').ilike('email', rec_email.value).execute()
                            if res_m.data and res_m.data[0].get('telegram_id'):
                                user_tg_id = res_m.data[0]['telegram_id']
                            else:
                                res_u = db_conn.table('users').select('telegram_id').ilike('email', rec_email.value).execute()
                                if res_u.data and res_u.data[0].get('telegram_id'):
                                    user_tg_id = res_u.data[0]['telegram_id']

                        # 1. Se o próprio militar tiver Telegram ID associado, envia o PIN EXCLUSIVAMENTE para ele em mensagem privada
                        if user_tg_id:
                            user_msg = (
                                f"🔑 **RECUPERAÇÃO DE SENHA DO SISGAB**\n\n"
                                f"Seu código PIN de recuperação é: `{pin_generated}`\n\n"
                                f"⏱️ Válido por 15 minutos. Insira este código no site para redefinir sua senha."
                            )
                            import asyncio
                            asyncio.run(send_notification_to_user(user_tg_id, user_msg))

                        # 2. Para os Administradores, envia apenas o ALERTA DE AUDITORIA (SEM EXPOR O PIN)
                        admin_alert = (
                            f"🛡️ **AUDITORIA DE SEGURANÇA - RECUPERAÇÃO DE SENHA**\n\n"
                            f"📧 Usuário/E-mail: `{rec_email.value}`\n"
                            f"⚡ Ação: O militar solicitou o PIN de redefinição de senha no site.\n"
                            f"📱 Telegram Privado do Usuário: {'✅ Enviado' if user_tg_id else '⚠️ Não associado ao perfil'}"
                        )
                        notify_telegram(admin_alert, "saude", role_required="admin")
                    except Exception as e_notif:
                        print(f"[RECOVERY TELEGRAM SECURE ERR] {e_notif}")

                        
                    rec_error.text = ''
                    step1_container.style('display: none;')
                    step2_container.style('display: flex;')
                    ui.notify(f'Código PIN de 6 dígitos gerado com sucesso! Digite o PIN e a nova senha abaixo.', color='success', duration=8)

                with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                    ui.button('Cancelar', on_click=rec_pwd_dialog.close).props('flat color=grey')
                    ui.button('Enviar Código PIN', on_click=request_pin).props('unelevated color=amber-9 text-color=black')

            with step2_container:
                ui.label('Insira o código PIN de 6 dígitos e defina sua nova senha:').classes('text-grey-5 text-xs text-center q-mb-xs')
                ui.label('💡 Caso precise do código PIN, você também pode solicitá-lo ao Administrador.').classes('text-amber-4 text-[11px] text-center bg-black/30 q-pa-xs rounded w-full')
                input_pin = ui.input('Código PIN (6 dígitos)').props('dark dense outlined w-full placeholder=123456')
                new_pwd = ui.input('Nova Senha', password=True).props('dark dense outlined w-full')
                confirm_new_pwd = ui.input('Confirmar Nova Senha', password=True).props('dark dense outlined w-full')


                def submit_pin_reset():
                    if not input_pin.value or not new_pwd.value:
                        rec_error.text = 'Preencha o código PIN e a nova senha'
                        return
                    if new_pwd.value != confirm_new_pwd.value:
                        rec_error.text = 'As senhas digitadas não coincidem'
                        return
                        
                    from database import verify_and_reset_password_with_pin
                    success, msg = verify_and_reset_password_with_pin(rec_email.value, input_pin.value, new_pwd.value)
                    
                    if success:
                        ui.notify(msg, color='success', duration=6)
                        rec_pwd_dialog.close()
                    else:
                        rec_error.text = msg

                with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                    ui.button('Voltar', on_click=lambda: (step2_container.style('display: none;'), step1_container.style('display: flex;'))).props('flat color=grey')
                    ui.button('Redefinir Senha', on_click=submit_pin_reset).props('unelevated color=amber-9 text-color=black')


    # Fundo do login com transparência para o efeito de Partículas Antigravidade
    with ui.column().classes('w-full min-h-screen items-center justify-center p-2 sm:p-4 gap-2').style(
        'background: transparent; position: relative; z-index: 1;'
    ):

        with ui.card().classes('w-full max-w-sm no-shadow rounded-xl q-pa-md').style(
            f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]}; box-shadow: 0 10px 40px rgba(0,0,0,0.6) !important;'
        ):
            with ui.column().classes('w-full items-center gap-2'):
                
                # ── TOPO: LOGO IMPONENTE E TÍTULO ──
                ui.image(LOGO_BASE64).style('width: 165px; height: 165px; filter: drop-shadow(0 0 16px rgba(197, 160, 89, 0.9));').classes('q-my-xs')
                ui.label('SisGAB').classes('cyber-title').style(
                    f'color: {theme.colors["primary"]}; font-size: 2.2rem; font-weight: 700; letter-spacing: 2px; line-height: 1;'
                )

                
                ui.separator().style('background-color: rgba(197, 160, 89, 0.15); height: 1px;').classes('w-3/4 q-my-xs')
                
                # ── FORMULÁRIO DE ACESSO DIRETO ──
                with ui.element('form').props('onsubmit="return false;"').classes('w-full flex flex-col gap-2 items-center').on('submit', lambda: try_login()):
                    with ui.column().classes('w-full gap-0 items-center text-center q-mb-xs'):
                        ui.label('🔐 ACESSO AO SISTEMA').classes('text-white text-sm font-bold cyber-title tracking-widest')
                        ui.label('Entre com suas credenciais').classes('text-grey-5 text-[11px]')
                    
                    user = ui.input('E-mail ou Usuário', value=app.storage.user.get('last_username', '')).props('dark outlined w-full autocomplete=username name=username dense').classes('w-full text-xs')
                    pwd = ui.input('Senha', password=True).props('dark outlined w-full autocomplete=current-password name=password dense').classes('w-full text-xs')
                    with pwd:
                        pwd_visible = {'show': False}
                        def toggle_pwd_vis(btn):
                            pwd_visible['show'] = not pwd_visible['show']
                            if pwd_visible['show']:
                                pwd.props('password=false')
                                btn.props('icon=visibility_off color=amber-9')
                            else:
                                pwd.props('password=true')
                                btn.props('icon=visibility color=grey-5')
                        btn_vis = ui.button(icon='visibility').props('flat round dense color=grey-5')
                        btn_vis.on_click(lambda: toggle_pwd_vis(btn_vis))

                    
                    session_type = ui.radio(
                        {0: 'Manter conectado (Sempre)', 7200: 'Sessão temporária (2 horas)'}, 
                        value=0
                    ).props('dark inline dense').classes('text-[10px] text-grey q-mt-xs self-center')
                    
                    error_label = ui.label('').classes('text-xs text-red w-full text-center')
                    
                    def try_login():
                        if not user.value or not pwd.value:
                            error_label.text = 'Preencha todos os campos'
                            return
                        
                        # Rate Limiting contra Brute-Force (A6)
                        from rate_limit import rate_limiter, get_client_ip
                        client_ip = get_client_ip()
                        key = f"login_attempt:{client_ip}"
                        if not rate_limiter.is_allowed(key, max_requests=5, window_seconds=20):
                            error_label.text = 'Muitas tentativas. Login bloqueado por 20 segundos.'
                            import log_acessos
                            log_acessos.log_access(f"Tentativa de login bloqueada (Brute-force)", "Autenticação", "BLOQUEADO")
                            return
                        
                        from database import get_db_connection, authenticate_user, authenticate_user_supabase
                        db_conn = get_db_connection()
                        
                        if not db_conn:
                            error_label.text = 'Sem conexão com o Supabase. Verifique sua rede.'
                            return
                        
                        original_input = user.value.strip()
                        password_val = pwd.value.strip()

                        # 1. Tenta autenticação direta otimizada no banco (efetivo / users) em 1 único roundtrip
                        local_user = authenticate_user(original_input, password_val)
                        
                        profile = None
                        session_data = None
                        login_email = original_input

                        if local_user:
                            profile = local_user
                            login_email = local_user.get('email') or original_input
                        else:
                            # 2. Se não encontrar no banco local/efetivo, tenta Supabase Auth Cloud
                            try:
                                auth_res = authenticate_user_supabase(original_input, password_val)
                                if auth_res:
                                    profile = auth_res['profile']
                                    session_data = auth_res['session']
                                    login_email = profile.get('email') or original_input
                            except Exception as e:
                                print(f"[LOGIN SUPABASE AUTH ERR] {e}")

                        if profile:
                            ng = profile.get('nome_guerra') or profile.get('nome') or profile.get('nome_completo') or original_input
                            pg = profile.get('posto_grad') or ''
                            nome_exibicao = f"{pg} {ng}".strip().upper() if ng and '@' not in str(ng) else original_input.upper()

                            import time
                            app.storage.user['authenticated'] = True
                            app.storage.user['login_time'] = time.time()
                            app.storage.user['session_duration'] = session_type.value
                            app.storage.user['last_username'] = user.value
                            app.storage.user['user_data'] = {
                                'id': profile.get('id'),
                                'username': profile.get('username') or profile.get('nome_guerra'),
                                'nome_guerra': nome_exibicao,
                                'posto_grad': pg,
                                'role': profile.get('role', 'compel'),
                                'email': login_email
                            }
                            app.storage.user['supabase_session'] = session_data
                            
                            role_user = str(profile.get('role', 'compel')).strip().lower()
                            target_path = '/sisgab_tv' if role_user in ('tv', 'tv_comcia') else '/'
                            app.storage.user['current_path'] = target_path
                            if role_user not in ('tv', 'tv_comcia'):
                                app.storage.user['tv_lock_active'] = False
                            
                            ui.notify(
                                f'🛡️ SESSÃO AUTENTICADA — BEM-VINDO AO SISGAB, {nome_exibicao}!',
                                color='dark',
                                position='top',
                                icon='shield',
                                close_button='OK'
                            )
                            
                            try:
                                import log_acessos
                                log_acessos.log_access("Login", "Autenticação", "SUCESSO")
                            except Exception:
                                pass
                            
                            ui.run_javascript(f"window.location.href = '{target_path}';")
                            return
                        else:
                            error_label.text = 'E-mail, usuário ou senha incorretos'
                            try:
                                import log_acessos
                                log_acessos.log_access(f"Falha de Login: {user.value}", "Autenticação", "FALHA")
                            except Exception:
                                pass
  
                    ui.button('🚀 Entrar no Sistema').props('type=submit unelevated color=amber-9 text-color=black w-full bold').classes('q-py-sm font-bold text-sm cyber-title w-full')
                    
                    with ui.row().classes('w-full justify-between items-center q-mt-xs'):
                        ui.button('📝 Solicitar acesso', on_click=reg_dialog.open).props('flat color=grey no-caps').classes('text-xs')
                        ui.button('🔑 Esqueci a senha', on_click=rec_pwd_dialog.open).props('flat color=grey no-caps').classes('text-xs')

        # Hook para checar e processar redirecionamento de recuperação de senha (URL hash #access_token=...)
        async def check_recovery():
            try:
                # Aguarda a conexão do WebSocket ser estabelecida
                await ui.context.client.connected()
                url_hash = await ui.run_javascript('window.location.hash')
                if url_hash and 'access_token=' in url_hash:
                    # Parseia os parâmetros da hash URL
                    params = {}
                    for part in url_hash.lstrip('#').split('&'):
                        if '=' in part:
                            k, v = part.split('=', 1)
                            params[k] = v
                    
                    access_token = params.get('access_token')
                    refresh_token = params.get('refresh_token')
                    token_type = params.get('type')
                    
                    if access_token and token_type == 'recovery':
                        # Limpa a hash da URL no navegador para evitar reprocessamentos
                        await ui.run_javascript('window.location.hash = ""')
                        
                        from database import get_db_connection
                        db_conn = get_db_connection()
                        if db_conn:
                            # Restabelece a sessão no Supabase usando o access_token recebido
                            db_conn.auth.set_session(access_token, refresh_token)
                            user_obj = db_conn.auth.get_user()
                            if user_obj and user_obj.user:
                                # Salva a sessão no storage para persistir o login
                                app.storage.user['supabase_session'] = {
                                    'access_token': access_token,
                                    'refresh_token': refresh_token
                                }
                                
                                # Busca o perfil na base de dados (efetivo ou users)
                                res_ef = db_conn.table('efetivo').select('*').eq('email', user_obj.user.email).execute()
                                user_profile = res_ef.data[0] if res_ef.data else None
                                if not user_profile:
                                    res_u = db_conn.table('users').select('*').eq('email', user_obj.user.email).execute()
                                    user_profile = res_u.data[0] if res_u.data else {}
                                
                                app.storage.user['user_data'] = user_profile
                                ui.notify('Sessão de recuperação iniciada. Redefina sua senha abaixo.', color='warning')
                                # Abre o diálogo padrão de troca de senha
                                open_change_password_dialog(user_profile)
            except Exception as e:
                print(f"[RECOVERY HASH ERR] {e}")

        ui.timer(0.1, check_recovery, once=True)

        # Rodapé (Footer) centralizado fora do card principal
        ui.label('🚀 Desenvolvido por Sargento Calaça 🇧🇷').classes('text-amber-5 text-xs font-bold tracking-wider opacity-80')

def sync_menu_permissions_db():
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if not db:
            return
        
        # Obter todos os itens de menu
        menu_items = []
        for cat in sisgab_menu_categories:
            for item in cat['items']:
                menu_items.append(item)
                
        # Buscar permissões atuais
        res = db.table('permissions').select('feature_key').execute()
        existing_keys = {row['feature_key'] for row in res.data} if res.data else set()
        
        # Inserir novos itens de menu se não existirem
        new_permissions = []
        for item in menu_items:
            path_clean = item['path'].strip('/').replace('/', '_')
            f_key = f"menu_{path_clean}"
            if f_key not in existing_keys:
                # Default allowed roles (as configured in main.py)
                default_roles = ",".join(item.get('roles', [])) if 'roles' in item else "admin,supervisor,oficial_gab,oficial,praca_gab,comsoc,comsoc_design,militar,compel,operador"
                new_permissions.append({
                    'feature_key': f_key,
                    'feature_name': f"Acesso ao Menu: {item['name']}",
                    'allowed_roles': default_roles
                })
        
        if new_permissions:
            db.table('permissions').insert(new_permissions).execute()
            print(f"[DB] Sincronizados {len(new_permissions)} novos menus com a tabela Permissions.")
        
        # Garante estritamente que 'Usuários e Permissões' (menu_admin_panel) seja restrito apenas a 'admin'
        try:
            db.table('permissions').update({'allowed_roles': 'admin'}).eq('feature_key', 'menu_admin_panel').execute()
        except Exception:
            pass
    except Exception as e:
        print(f"[ERRO sync_menu_permissions_db] {e}")


# Inicializa o Bot do Telegram e Agendadores em tarefas desacopladas para nao bloquear a inicializacao da NiceGUI
from alerts_manager import AlertsManager
from notifications_manager import start_19h_briefing_scheduler, start_15h_demand_scheduler
from database import seed_default_admin, seed_efetivo_gabinete

async def _non_blocking_startup():
    try:
        await asyncio.to_thread(seed_default_admin)
        await asyncio.to_thread(seed_efetivo_gabinete)
        await asyncio.to_thread(sync_menu_permissions_db)
    except Exception as e:
        print(f"[STARTUP SEED ERR] {e}", flush=True)

    try:
        asyncio.create_task(telegram_bot.init_bot())
    except Exception as e:
        print(f"[STARTUP BOT ERR] {e}", flush=True)

    try:
        AlertsManager.start_alerts_scheduler()
        start_19h_briefing_scheduler()
        start_15h_demand_scheduler()
    except Exception as e:
        print(f"[STARTUP SCHEDULERS ERR] {e}", flush=True)

def start_background_services():
    asyncio.create_task(_non_blocking_startup())

app.on_startup(start_background_services)

# Loop de liberação periódica de memória RAM para manter o pico sob 400MB
async def _memory_cleanup_task():
    import gc
    while True:
        await asyncio.sleep(300) # Coleta a cada 5 minutos
        gc.collect()

def start_memory_cleanup():
    try:
        asyncio.create_task(_memory_cleanup_task())
    except Exception as e:
        print(f"[MEMORY CLEANUP ERR] {e}")

app.on_startup(start_memory_cleanup)

# Loop de Auto-Ping para manter a aplicacao no Render online 24/7 sem entrar em Sleep Mode
async def _render_keepalive_task():
    import urllib.request
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if not render_url:
        return
    ping_endpoint = f"{render_url}/ping"
    while True:
        await asyncio.sleep(240)  # Pinga a cada 4 minutos para impedir o Sleep Mode no Render
        try:
            req = urllib.request.Request(ping_endpoint, headers={'User-Agent': 'SisGAB-KeepAlive/1.0'})
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
        except Exception as e:
            print(f"[KEEPALIVE PING] {e}")

def start_render_keepalive():
    if os.environ.get('RENDER_EXTERNAL_URL'):
        try:
            asyncio.create_task(_render_keepalive_task())
        except Exception as e:
            print(f"[RENDER KEEPALIVE ERR] {e}")

app.on_startup(start_render_keepalive)

# Garante o encerramento limpo da sessão do bot do Telegram ao desligar ou recarregar
app.on_shutdown(telegram_bot.stop_bot)

# Configuração dinâmica para deploy na nuvem (Render, Railway, Hugging Face, etc.)
port_env = int(os.environ.get('PORT', 8080))
host_env = os.environ.get('HOST', '0.0.0.0')
# SEGURANÇA: Exige STORAGE_SECRET no ambiente para segurança de sessão
secret_env = os.environ.get('STORAGE_SECRET') or "sisgab-secret-key-cgcfn-audiovisual-2026-prod-fallback"

# Desativamos o 'reload' por padrão para rodar em Modo Produção super leve, veloz, estável e sem reinícios.
ui.run(
    title='SisGAB', 
    dark=True, 
    storage_secret=secret_env, 
    reconnect_timeout=10.0, # 10 segundos de tolerância contra pequenas oscilações de rede antes de mostrar 'Connection lost'
    session_middleware_kwargs={'max_age': 30 * 24 * 60 * 60}, # 30 dias de persistência para "Manter conectado"
    host=host_env,
    port=port_env,
    reload=False
)
