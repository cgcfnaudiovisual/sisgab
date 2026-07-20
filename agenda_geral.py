# modules/agenda_geral.py
import urllib.parse
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

def make_gcal_sync_url(title, date_str, time_str='09:00', location='CGCFN', details=''):
    try:
        clean_date = str(date_str).replace('-', '')
        clean_time = str(time_str).replace(':', '') + '00'
        if len(clean_time) == 4:
            clean_time += '00'
        start_dt = f"{clean_date}T{clean_time}"
        params = {
            'action': 'TEMPLATE',
            'text': f"[COMSOC/CGCFN] {title}",
            'dates': f"{start_dt}/{start_dt}",
            'details': f"Evento/Pauta COMSOC - {details}\nConta Oficial: cgcfnaudiovisual@gmail.com",
            'location': location,
            'sf': 'true'
        }
        return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"
    except Exception:
        return "https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20"

def render_page():
    ui.label('📅 AGENDA GERAL DA COMSOC & COMPROMISSOS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')

    # Card Superior com Informações de Sincronização
    with ui.card().classes('w-full q-pa-md border border-cyan-500/30 rounded-xl bg-black/40 q-mb-md'):
        with ui.row().classes('w-full justify-between items-center wrap gap-4'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('calendar_month', color='cyan', size='2.2rem')
                with ui.column().classes('gap-0'):
                    ui.label('AGENDA OFICIAL DE COMPROMISSOS — CGCFN / COMSOC').classes('text-sm font-bold text-white cyber-title')
                    ui.label('Conta Oficial: cgcfnaudiovisual@gmail.com').classes('text-xs text-cyan font-mono')
            
            with ui.row().classes('items-center gap-2'):
                ui.link(
                    '🔗 Abrir Google Calendar Oficial',
                    'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                    new_tab=True
                ).classes('text-xs font-bold text-cyan underline q-px-sm q-py-xs bg-cyan-950/60 border border-cyan-500/40 rounded-lg')
                
                ui.button(
                    '➕ Nova Pauta / Evento',
                    icon='add_event',
                    on_click=lambda: ui.navigate.to('/comsoc_demandas')
                ).props('unelevated color=cyan text-color=black bold dense').classes('text-xs font-bold q-px-sm')

    # Abas principais da Agenda
    with ui.card().classes('w-full q-pa-none no-shadow rounded-xl').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.tabs().classes('w-full border-b border-cyan-500/20 text-cyan-4') as tabs:
            tab_native = ui.tab('native', label='📅 Calendário & Pautas (100% Automático)', icon='event')
            tab_gcal = ui.tab('gcal', label='🌐 Google Calendar (cgcfnaudiovisual@gmail.com)', icon='language')

        with ui.tab_panels(tabs, value=tab_native).classes('w-full q-pa-md bg-transparent'):
            
            # =========================================================================
            # TAB 1: CALENDÁRIO NATIVO E PAUTAS REGISTRADAS NO BANCO
            # =========================================================================
            with ui.tab_panel(tab_native):
                with ui.row().classes('w-full gap-4 items-stretch justify-start'):
                    
                    # Coluna Esquerda: Seletor de Data Interativo
                    with ui.column().classes('col-12 col-md-5 col-lg-4 q-pa-none'):
                        ui.label('📆 Selecione uma data para filtrar:').classes('text-xs font-bold text-cyan q-mb-xs')
                        selected_date = ui.date(value=datetime.now().strftime('%Y/%m/%d')).props('dark flat bordered w-full').classes('w-full rounded-xl')
                        
                        btn_all = ui.button('🔄 Mostrar Todos os Eventos', icon='list').props('outline color=cyan dense w-full').classes('q-mt-sm text-xs font-bold')
                    
                    # Coluna Direita: Pautas e Eventos
                    with ui.column().classes('col-12 col-md-7 col-lg-8 q-pa-none flex-grow'):
                        details_container = ui.column().classes('w-full gap-3')

                        def render_events(filter_by_date=None):
                            details_container.clear()
                            
                            db = get_db_connection()
                            events_list = []
                            if db:
                                try:
                                    query = db.table('demandas_comunicacao').select('*')
                                    if filter_by_date:
                                        query = query.eq('data_evento', filter_by_date)
                                    res = query.order('data_evento', desc=False).execute()
                                    events_list = res.data if res.data else []
                                except Exception as err:
                                    print(f"[AGENDA DB ERR] {err}")
                            
                            with details_container:
                                if filter_by_date:
                                    ui.label(f"📌 Compromissos do dia {filter_by_date}:").classes('text-sm font-bold text-cyan q-mb-xs')
                                else:
                                    ui.label('📋 Todos os Eventos e Pautas Agendadas (Visão Geral):').classes('text-sm font-bold text-white q-mb-xs')
                                
                                if events_list:
                                    for ev in events_list:
                                        status_st = '🟢 APROVADO' if ev.get('status') in ('aprovado', 'aprovada') else '🟡 PENDENTE'
                                        badge_col = 'emerald' if ev.get('status') in ('aprovado', 'aprovada') else 'amber'
                                        
                                        with ui.card().classes('w-full q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl gap-2 hover:border-cyan-400/60 transition-all'):
                                            with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                                                ui.label(ev['titulo_evento']).classes('text-sm font-bold text-white')
                                                ui.badge(status_st).props(f'color={badge_col} bold').classes('text-xs')
                                            
                                            with ui.row().classes('w-full gap-4 text-xs text-grey-4 flex-wrap'):
                                                ui.label(f"📅 Data: {ev.get('data_evento', 'N/I')} às {ev.get('hora_evento', '09:00')}")
                                                ui.label(f"📍 Local: {ev.get('local_evento', 'N/I')}")
                                                ui.label(f"👤 Solicitante: {ev.get('solicitante_nome', 'N/I')} ({ev.get('setor', 'CGCFN')})")
                                            
                                            if ev.get('autoridades'):
                                                ui.label(f"🎖️ Autoridades: {ev['autoridades']}").classes('text-xs text-cyan')
                                            
                                            gcal_link = make_gcal_sync_url(
                                                title=ev['titulo_evento'],
                                                date_str=ev.get('data_evento', datetime.now().strftime('%Y-%m-%d')),
                                                time_str=ev.get('hora_evento', '09:00'),
                                                location=ev.get('local_evento', 'CGCFN'),
                                                details=f"Solicitante: {ev.get('solicitante_nome', 'N/I')}"
                                            )
                                            
                                            with ui.row().classes('w-full justify-end q-mt-xs'):
                                                ui.link('📅 Sync com Google Calendar', gcal_link, new_tab=True).classes('text-xs font-bold text-cyan underline bg-cyan-950/50 q-px-sm q-py-xs rounded border border-cyan-500/30')
                                else:
                                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                                        ui.icon('event_busy', size='3rem', color='cyan')
                                        if filter_by_date:
                                            ui.label(f"Nenhum evento agendado para o dia {filter_by_date}.").classes('text-xs')
                                        else:
                                            ui.label("Nenhum evento ou pauta cadastrada no banco no momento.").classes('text-xs')

                        def on_date_change():
                            raw_date = selected_date.value
                            if raw_date:
                                formatted_date = raw_date.replace('/', '-')
                                render_events(filter_by_date=formatted_date)

                        btn_all.on_click(lambda: render_events(filter_by_date=None))
                        selected_date.on_value_change(on_date_change)
                        
                        # Carrega TODOS os eventos por padrão ao abrir a página
                        render_events(filter_by_date=None)

            # =========================================================================
            # TAB 2: GOOGLE CALENDAR EMBUTIDO (INSTRUÇÕES E IFRAME)
            # =========================================================================
            with ui.tab_panel(tab_gcal):
                with ui.column().classes('w-full gap-4'):
                    ui.label('🌐 Agenda Google da Conta Oficial (cgcfnaudiovisual@gmail.com)').classes('text-md font-bold text-cyan')
                    
                    with ui.card().classes('w-full q-pa-sm bg-black/40 border border-cyan-500/20 rounded-lg'):
                        ui.label('💡 Para o iFrame do Google exibir sem tela preta no navegador:').classes('text-xs font-bold text-amber-4')
                        ui.label('1. Acesse o Google Calendar logado em cgcfnaudiovisual@gmail.com.').classes('text-[11px] text-grey-3')
                        ui.label('2. Vá em Configurações da Agenda > Permissões de Acesso > Marque "Tornar disponível ao público".').classes('text-[11px] text-grey-3')
                    
                    ui.html('''
                        <iframe 
                            src="https://calendar.google.com/calendar/embed?src=cgcfnaudiovisual%40gmail.com&ctz=America%2FSao_Paulo&mode=MONTH&showTitle=0&showNav=1&showDate=1&showPrint=0&showTabs=1&showCalendars=0&showTz=1" 
                            style="border: 0; width: 100%; height: 550px; background: #0b0f19; border-radius: 12px;" 
                            frameborder="0" 
                            scrolling="no">
                        </iframe>
                    ''').classes('w-full')
