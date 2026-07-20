# modules/agenda_geral.py
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

def render_page():
    ui.label('📅 AGENDA GERAL DA COMSOC & COMPROMISSOS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')

    # Header Card com informações de Sincronização
    with ui.card().classes('w-full q-pa-md border border-cyan-500/30 rounded-xl bg-black/40 q-mb-md'):
        with ui.row().classes('w-full justify-between items-center wrap gap-4'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('calendar_month', color='cyan', size='2.2rem')
                with ui.column().classes('gap-0'):
                    ui.label('AGENDA OFICIAL DE COMPROMISSOS — CGCFN / COMSOC').classes('text-sm font-bold text-white cyber-title')
                    ui.label('Conta de Gestão: cgcfnaudiovisual@gmail.com').classes('text-xs text-cyan font-mono')
            
            with ui.row().classes('items-center gap-2'):
                ui.link(
                    '🔗 Abrir no Google Calendar',
                    'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                    new_tab=True
                ).classes('text-xs font-bold text-cyan underline q-px-sm q-py-xs bg-cyan-950/60 border border-cyan-500/40 rounded-lg')
                
                ui.button(
                    '➕ Nova Pauta / Evento',
                    icon='add_event',
                    on_click=lambda: ui.navigate.to('/comsoc_demandas')
                ).props('unelevated color=cyan text-color=black bold dense').classes('text-xs font-bold q-px-sm')

    # Grade Principal: Calendário Embutido (Esquerda) + Lista de Pautas Sincronizadas (Direita)
    with ui.row().classes('w-full gap-4 items-stretch justify-start'):
        
        # Coluna 1: Google Calendar Embutido (2/3 da largura)
        with ui.column().classes('col-12 col-lg-8 q-pa-none').style('min-width: 340px;'):
            with ui.card().classes('w-full q-pa-none no-shadow rounded-xl overflow-hidden').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 620px;'
            ):
                ui.html('''
                    <iframe 
                        src="https://calendar.google.com/calendar/embed?src=cgcfnaudiovisual%40gmail.com&ctz=America%2FSao_Paulo&mode=MONTH&showTitle=0&showNav=1&showDate=1&showPrint=0&showTabs=1&showCalendars=0&showTz=1" 
                        style="border: 0; width: 100%; height: 620px; background: #0b0f19;" 
                        frameborder="0" 
                        scrolling="no">
                    </iframe>
                ''').classes('w-full h-full')

        # Coluna 2: Lista Próximas Pautas e Efemérides (1/3 da largura)
        with ui.column().classes('col-12 col-lg-4 q-pa-none').style('min-width: 320px;'):
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 620px;'
            ):
                ui.label('📌 Próximas Coberturas Sincronizadas').classes('text-md font-bold text-white q-mb-md')
                
                pautas = []
                db = get_db_connection()
                if db:
                    try:
                        res = db.table('demandas_comunicacao').select('*').in_('status', ['aprovado', 'aprovada', 'pendente']).order('data_evento', desc=False).limit(10).execute()
                        pautas = res.data if res.data else []
                    except Exception as e:
                        print(f"[AGENDA GERAL DB ERR] {e}")
                
                if pautas:
                    with ui.column().classes('w-full gap-2'):
                        for p in pautas:
                            status_badge = '🟢 APROVADA' if p.get('status') in ('aprovado', 'aprovada') else '🟡 PENDENTE'
                            badge_color = 'emerald' if p.get('status') in ('aprovado', 'aprovada') else 'amber'
                            
                            with ui.card().classes('w-full q-pa-sm bg-black/30 border border-cyan-500/20 rounded-lg'):
                                with ui.row().classes('w-full justify-between items-center no-wrap'):
                                    ui.label(p['titulo_evento']).classes('text-xs font-bold text-white leading-tight')
                                    ui.badge(status_badge).props(f'color={badge_color} outline').classes('text-[8px]')
                                
                                with ui.row().classes('w-full justify-between items-center q-mt-xs text-[10px] text-grey-4'):
                                    ui.label(f"📅 {p['data_evento']} às {p.get('hora_evento', '09:00')}")
                                    ui.label(f"📍 {p['local_evento']}")
                                
                                ui.label(f"Sol: {p['solicitante_nome']} ({p.get('setor', 'CGCFN')})").classes('text-[9px] text-cyan q-mt-xs')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('event_available', size='3rem', color='cyan')
                        ui.label('Nenhum evento futuro agendado no momento.').classes('text-xs')
