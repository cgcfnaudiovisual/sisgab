# modules/agenda_geral.py
import urllib.parse
from datetime import datetime, timedelta
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

# ── Google Calendar Sync URL Builder ──
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

    # ══════════════════════════════════════════════════════════════════
    #  HEADER — Título + Ações Rápidas
    # ══════════════════════════════════════════════════════════════════
    with ui.row().classes('w-full items-center justify-between q-px-md q-pt-md q-pb-sm'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('calendar_month', color='cyan', size='1.8rem')
            with ui.column().classes('gap-0'):
                ui.label('AGENDA GERAL').classes('text-xl font-bold text-white tracking-wide')
                ui.label('cgcfnaudiovisual@gmail.com').classes('text-[11px] text-cyan-7 font-mono')

        with ui.row().classes('items-center gap-2'):
            ui.link(
                '🔗 Abrir no Google Calendar',
                'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                new_tab=True
            ).classes(
                'text-xs text-cyan underline q-px-sm q-py-xs '
                'bg-cyan-950/40 rounded-lg border border-cyan-500/20 '
                'hover:bg-cyan-900/40 transition-all'
            )
            ui.button('Nova Pauta', icon='add', on_click=lambda: ui.navigate.to('/comsoc_demandas')).props(
                'unelevated color=cyan text-color=black dense'
            ).classes('text-xs font-bold')

    # ══════════════════════════════════════════════════════════════════
    #  GOOGLE CALENDAR — iFrame Embutido (Visão Mensal)
    # ══════════════════════════════════════════════════════════════════
    with ui.card().classes('w-full rounded-xl no-shadow overflow-hidden q-mx-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        ui.html('''
            <iframe 
                src="https://calendar.google.com/calendar/embed?src=cgcfnaudiovisual%40gmail.com&ctz=America%2FSao_Paulo&mode=MONTH&showTitle=0&showNav=1&showDate=1&showPrint=0&showTabs=0&showCalendars=0&showTz=0" 
                style="border:0; width:100%; height:460px; border-radius:12px; background:#0b0f19;" 
                frameborder="0" scrolling="no">
            </iframe>
        ''').classes('w-full')

    # ══════════════════════════════════════════════════════════════════
    #  PRÓXIMOS COMPROMISSOS — Pautas do Banco de Dados
    # ══════════════════════════════════════════════════════════════════
    with ui.card().classes('w-full q-mx-md q-mt-md rounded-xl no-shadow q-pa-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        # ── Sub-header com contador ──
        with ui.row().classes('w-full items-center justify-between q-mb-sm'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('event_note', color='cyan', size='1.2rem')
                ui.label('PRÓXIMOS COMPROMISSOS').classes('text-sm font-bold text-white tracking-wide')
            counter_label = ui.label('').classes('text-[11px] text-grey-5 font-mono')

        # ── Container de Eventos ──
        events_container = ui.column().classes('w-full gap-1')

        def render_events():
            events_container.clear()

            db = get_db_connection()
            events_list = []
            if db:
                try:
                    hoje = datetime.now().date()
                    fim = hoje + timedelta(days=60)
                    res = db.table('demandas_comunicacao').select('*').gte(
                        'data_evento', hoje.isoformat()
                    ).lte(
                        'data_evento', fim.isoformat()
                    ).order('data_evento', desc=False).execute()
                    events_list = [
                        ev for ev in (res.data or [])
                        if str(ev.get('status', '')).strip().lower()
                        not in ('concluida', 'concluido', 'concluidas', 'rejeitado', 'rejeitada')
                    ]
                except Exception as err:
                    print(f"[AGENDA DB ERR] {err}")

            counter_label.text = f'{len(events_list)} evento(s) nos próximos 60 dias'

            with events_container:
                if events_list:
                    for ev in events_list:
                        is_approved = ev.get('status') in ('aprovado', 'aprovada')
                        is_today = ev.get('data_evento') == datetime.now().strftime('%Y-%m-%d')

                        # ── Linha do Evento ──
                        row_border = 'border-emerald-500/30' if is_today else 'border-cyan-500/10'
                        row_bg = 'bg-emerald-950/20' if is_today else 'bg-black/20'

                        with ui.row().classes(
                            f'w-full items-center q-py-sm q-px-md rounded-lg gap-4 '
                            f'{row_bg} border {row_border} '
                            f'hover:border-cyan-500/40 transition-all cursor-default'
                        ):
                            # ▸ Indicador de Status
                            ui.icon(
                                'check_circle' if is_approved else 'schedule',
                                color='green' if is_approved else 'amber',
                                size='1.1rem'
                            ).tooltip('Aprovado' if is_approved else 'Pendente')

                            # ▸ Data
                            date_str = ev.get('data_evento', '')
                            try:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                date_display = dt.strftime('%d/%m')
                                day_name = dt.strftime('%a').upper()
                            except Exception:
                                date_display = date_str or '—'
                                day_name = ''

                            with ui.column().classes('gap-0 items-center').style('min-width:55px;'):
                                ui.label(date_display).classes('text-sm font-bold text-cyan')
                                if day_name:
                                    ui.label(day_name).classes('text-[9px] text-grey-6 font-mono')

                            # ▸ Hora
                            hora = ev.get('hora_evento', '--:--')
                            if hora and len(str(hora)) >= 5:
                                hora = str(hora)[:5]
                            ui.label(hora).classes('text-xs text-grey-4 font-mono').style('min-width:40px;')

                            # ▸ Separador visual
                            ui.element('div').classes('bg-cyan-500/20').style('width:1px; height:28px;')

                            # ▸ Título + Local
                            with ui.column().classes('gap-0 flex-grow'):
                                ui.label(ev.get('titulo_evento', 'Sem Título')).classes(
                                    'text-sm font-bold text-white'
                                ).style('line-height:1.3;')
                                loc = ev.get('local_evento', '')
                                if loc:
                                    ui.label(f"📍 {loc}").classes('text-[11px] text-grey-5')

                            # ▸ Responsável
                            try:
                                from telegram_bot.handlers_common import _format_militar_responsavel
                                resp_str = _format_militar_responsavel(ev, db)
                            except Exception:
                                resp_str = ev.get('solicitante_nome', '—')

                            ui.label(resp_str).classes(
                                'text-[11px] text-amber-4 font-bold gt-xs'
                            ).style(
                                'max-width:160px; overflow:hidden; '
                                'text-overflow:ellipsis; white-space:nowrap;'
                            ).tooltip(resp_str)

                            # ▸ Ações (Editar + Sync)
                            with ui.row().classes('gap-1 items-center'):
                                def _edit(dem=ev):
                                    from comsoc_homologar import open_editar_pauta_dialog
                                    open_editar_pauta_dialog(dem, render_events)

                                ui.button(icon='edit', on_click=_edit).props(
                                    'flat round dense color=cyan size=sm'
                                ).tooltip('Editar Pauta')

                                from database import get_demanda_drive_url
                                ev_d_url = get_demanda_drive_url(ev)
                                if ev_d_url:
                                    ui.button(icon='folder', on_click=lambda u=ev_d_url: ui.open(u, new_tab=True)).props('flat round dense color=blue size=sm').tooltip('Abrir Pasta no Google Drive / Acervo')

                                gcal_url = make_gcal_sync_url(
                                    title=ev.get('titulo_evento', ''),
                                    date_str=ev.get('data_evento', datetime.now().strftime('%Y-%m-%d')),
                                    time_str=ev.get('hora_evento', '09:00'),
                                    location=ev.get('local_evento', 'CGCFN'),
                                    details=f"Solicitante: {ev.get('solicitante_nome', 'N/I')}"
                                )
                                ui.link('📅', gcal_url, new_tab=True).classes(
                                    'text-sm q-pa-xs rounded hover:bg-cyan-900/40 transition-all'
                                ).tooltip('Adicionar ao Google Calendar')

                else:
                    # ── Estado Vazio ──
                    with ui.column().classes('w-full items-center q-py-xl gap-2'):
                        ui.icon('event_available', size='2.5rem', color='cyan')
                        ui.label('Nenhum compromisso agendado nos próximos 60 dias.').classes(
                            'text-xs text-grey-5'
                        )

        # ── Renderiza ao carregar ──
        render_events()
