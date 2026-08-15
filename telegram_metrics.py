import asyncio
from datetime import datetime
from nicegui import ui
from database import get_db_connection

THEME = {
    'bg_main': '#030a17',
    'bg_panel': '#091326',
    'bg_card': '#0d1b34',
    'border': 'rgba(0, 229, 255, 0.2)',
    'accent': '#00e5ff',
    'text': '#e0f7fa'
}

def render_page(current_user=None):
    """Renderiza a página de Métricas e Auditoria do Bot Telegram para Administradores."""
    ui.colors(primary=THEME['accent'], dark=THEME['bg_main'])
    
    with ui.column().classes('w-full p-4 md:p-6 gap-6').style(f'background: {THEME["bg_main"]}; min-height: 100vh;'):
        
        # Cabeçalho da Página
        with ui.row().classes('w-full items-center justify-between border-b border-cyan-500/20 pb-4'):
            with ui.column().classes('gap-1'):
                ui.label('📊 Métricas & Logs do Bot Telegram').classes('text-2xl font-bold text-cyan cyber-title')
                ui.label('Painel exclusivo para Administradores — Auditoria de acesso e uso do assistente virtual').classes('text-xs text-grey-4')
            ui.button('🔄 Atualizar Dados', icon='refresh', on_click=lambda: page_container.refresh()).props('outline color=cyan dense')

        @ui.refreshable
        def page_container():
            db = get_db_connection()
            logs = []
            if db:
                try:
                    res = db.table('telegram_access_logs').select('*').order('created_at', desc=True).limit(200).execute()
                    logs = res.data or []
                except Exception as e:
                    print(f"[METRICS LOGS ERR] {e}")

            total_logs = len(logs)
            unique_users = len({l.get('chat_id') for l in logs if l.get('chat_id')})
            
            # Contagem de Comandos Mais Usados
            cmds_count = {}
            for l in logs:
                cmd = (l.get('command') or 'Interação').split()[0]
                cmds_count[cmd] = cmds_count.get(cmd, 0) + 1
            top_cmd = max(cmds_count, key=cmds_count.get) if cmds_count else 'Nenhum'

            # ─── CARDS DE MÉTRICAS ───
            with ui.row().classes('w-full gap-4 wrap'):
                with ui.card().classes('flex-1 min-w-[200px] p-4 rounded-xl no-shadow').style(
                    f'background: {THEME["bg_card"]}; border: 1px solid {THEME["border"]};'
                ):
                    ui.label('💬 TOTAL DE INTERAÇÕES').classes('text-xs text-grey-4 font-bold')
                    ui.label(str(total_logs)).classes('text-3xl font-bold text-cyan q-my-xs')
                    ui.label('Registros recentes no bot').classes('text-[10px] text-grey-5')

                with ui.card().classes('flex-1 min-w-[200px] p-4 rounded-xl no-shadow').style(
                    f'background: {THEME["bg_card"]}; border: 1px solid {THEME["border"]};'
                ):
                    ui.label('👥 USUÁRIOS ÚNICOS').classes('text-xs text-grey-4 font-bold')
                    ui.label(str(unique_users)).classes('text-3xl font-bold text-amber q-my-xs')
                    ui.label('IDs Telegram ativos').classes('text-[10px] text-grey-5')

                with ui.card().classes('flex-1 min-w-[200px] p-4 rounded-xl no-shadow').style(
                    f'background: {THEME["bg_card"]}; border: 1px solid {THEME["border"]};'
                ):
                    ui.label('⚡ COMANDO MAIS USADO').classes('text-xs text-grey-4 font-bold')
                    ui.label(top_cmd).classes('text-2xl font-bold text-emerald-400 q-my-xs truncate')
                    ui.label(f"{cmds_count.get(top_cmd, 0)} solicitações").classes('text-[10px] text-grey-5')

            # ─── TABELA DE LOGS E AUDITORIA ───
            with ui.card().classes('w-full p-4 rounded-xl no-shadow q-mt-md').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
            ):
                ui.label('📋 Histórico Recente de Acessos & Comandos').classes('text-sm font-bold text-cyan q-mb-md')
                
                columns = [
                    {'name': 'created_at', 'label': 'Data/Hora', 'field': 'created_at', 'align': 'left', 'sortable': True},
                    {'name': 'telegram_name', 'label': 'Usuário / Nome', 'field': 'telegram_name', 'align': 'left', 'sortable': True},
                    {'name': 'chat_id', 'label': 'Telegram ID', 'field': 'chat_id', 'align': 'left'},
                    {'name': 'command', 'label': 'Ação / Comando', 'field': 'command', 'align': 'left', 'sortable': True},
                ]

                formatted_rows = []
                for l in logs:
                    dt_str = l.get('created_at', '')[:19].replace('T', ' ')
                    formatted_rows.append({
                        'created_at': dt_str,
                        'telegram_name': l.get('telegram_name') or 'Anônimo',
                        'chat_id': str(l.get('chat_id', '')),
                        'command': l.get('command') or 'Interação'
                    })

                ui.table(columns=columns, rows=formatted_rows, row_key='created_at').props(
                    'dark flat bordered dense pagination-dark'
                ).classes('w-full text-xs')

        page_container()
