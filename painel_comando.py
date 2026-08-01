# modules/painel_comando.py
# Painel de Comando Unificado — Dashboard + Agenda + KPIs + Feed
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import calendar
from datetime import datetime, timedelta
from nicegui import ui, app
import theme
from database import get_db_connection, get_service_db_connection, execute_query_safe

THEME = theme.colors

# Configura calendário para semana começando na Segunda-feira
calendar.setfirstweekday(calendar.MONDAY)
DIAS_SEMANA = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM']


# ─────────────────────────────────────────────────────────────
#  UTILITÁRIOS
# ─────────────────────────────────────────────────────────────

def make_gcal_sync_url(title, date_str, time_str='09:00', location='CGCFN', details=''):
    """Gera URL para adicionar evento ao Google Calendar."""
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


def fetch_rss_news():
    """Busca notícias externas do feed do portal Poder Naval com fallback mock."""
    url = "https://www.naval.com.br/blog/feed/"
    news = []
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:4]:
                title = item.find('title').text
                link = item.find('link').text
                pub_date = item.find('pubDate').text
                try:
                    dt = datetime.strptime(pub_date[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                    pub_date_br = dt.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    pub_date_br = pub_date
                news.append({'titulo': title, 'link': link, 'data': pub_date_br, 'fonte': 'Poder Naval'})
    except Exception as e:
        print(f"[RSS FEED ERROR] {e}. Usando mock.")
        news = [
            {'titulo': 'Marinha do Brasil realiza Operação de Patrulha Naval no Atlântico Sul', 'link': 'https://agencia.marinha.mil.br/', 'data': datetime.now().strftime('%d/%m/%Y'), 'fonte': 'Agência Marinha'},
            {'titulo': 'Navio-Aeródromo Multipropósito realiza exercício conjunto', 'link': 'https://agencia.marinha.mil.br/', 'data': datetime.now().strftime('%d/%m/%Y'), 'fonte': 'Agência Marinha'},
        ]
    return news


# ─────────────────────────────────────────────────────────────
#  PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────

def render_page():
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_editor = user_role in ('admin', 'supervisor')

    # ── Injetar CSS responsivo ──
    ui.add_head_html('''<style>
        .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; width: 100%; }
        .cal-header { text-align: center; font-size: 10px; font-weight: 700; color: #64748b; padding: 6px 0; letter-spacing: 1px; }
        .cal-day {
            position: relative; text-align: center; padding: 10px 4px; border-radius: 8px;
            font-size: 13px; font-weight: 500; color: #e2e8f0; cursor: pointer;
            transition: all 0.15s ease; border: 1px solid transparent; min-height: 44px;
            display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
        }
        .cal-day:hover { background: rgba(197,160,89,0.08); border-color: rgba(197,160,89,0.3); }
        .cal-day.today { background: rgba(197,160,89,0.12); border-color: rgba(197,160,89,0.5); font-weight: 800; color: #c5a059; }
        .cal-day.selected { background: rgba(197,160,89,0.2); border-color: #c5a059; }
        .cal-day.empty { cursor: default; }
        .cal-day.empty:hover { background: transparent; border-color: transparent; }
        .cal-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
        .cal-dot.green { background: #00e676; }
        .cal-dot.amber { background: #fbbf24; }
        .cal-dot.red { background: #ff1744; }
        .cal-dots { display: flex; gap: 2px; justify-content: center; min-height: 8px; }
        @media (max-width: 768px) {
            .cal-day { padding: 6px 2px; font-size: 12px; min-height: 38px; }
            .kpi-row { flex-wrap: wrap !important; }
            .kpi-card { min-width: calc(33% - 8px) !important; }
            .event-row-desktop { display: none !important; }
            .event-card-mobile { display: flex !important; }
        }
        @media (min-width: 769px) {
            .event-row-desktop { display: flex !important; }
            .event-card-mobile { display: none !important; }
        }
    </style>''')

    # ══════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════
    with ui.row().classes('w-full items-center justify-between q-px-md q-pt-md q-pb-sm'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('dashboard', color='cyan', size='1.8rem')
            ui.label('PAINEL DE COMANDO').classes('text-xl font-bold text-white tracking-wide gt-xs')
        with ui.row().classes('items-center gap-2'):
            ui.link(
                '🔗 Google Calendar',
                'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                new_tab=True
            ).classes('text-xs text-cyan underline q-px-sm q-py-xs bg-cyan-950/40 rounded-lg border border-cyan-500/20 gt-xs')
            ui.button('Nova Pauta', icon='add', on_click=lambda: ui.navigate.to('/comsoc_demandas')).props(
                'unelevated color=cyan text-color=black dense'
            ).classes('text-xs font-bold')

    # ══════════════════════════════════════════════════════════
    #  DADOS DO BANCO — Carregamento único
    # ══════════════════════════════════════════════════════════
    db = get_service_db_connection() or get_db_connection()
    todas_demandas = []
    if db:
        try:
            res_all = db.table('demandas_comunicacao').select('*').execute()
            todas_demandas = res_all.data if res_all.data else []
        except Exception as e:
            print(f"[PAINEL DB ERR] {e}")

    hoje = datetime.now().date()

    # Classificar por status
    kpi_pendentes = 0
    kpi_aprovadas = 0
    kpi_ajustes = 0
    kpi_eventos_hoje = 0
    kpi_vencidas = 0
    kpi_tarefas_exec = 0

    # Mapeamento: data_evento -> lista de status
    eventos_por_dia = {}

    for d in todas_demandas:
        st = str(d.get('status', '')).strip().lower()
        if st in ('pendente', 'pendentes'):
            kpi_pendentes += 1
        elif st in ('aprovada', 'aprovado', 'aprovadas'):
            kpi_aprovadas += 1
        elif st in ('ajustes', 'ajuste'):
            kpi_ajustes += 1

        dt_str = str(d.get('data_evento', ''))
        try:
            dt_ev = datetime.strptime(dt_str, '%Y-%m-%d').date()
            if dt_ev == hoje:
                kpi_eventos_hoje += 1
            # Vencidas: data já passou e não está concluída/rejeitada
            if dt_ev < hoje and st not in ('concluida', 'concluido', 'concluidas', 'rejeitado', 'rejeitada'):
                kpi_vencidas += 1
            # Mapear eventos por dia para o calendário
            if dt_str not in eventos_por_dia:
                eventos_por_dia[dt_str] = []
            eventos_por_dia[dt_str].append(st)
        except Exception:
            pass

    # Contar tarefas em execução (categoria != audiovisual)
    for d in todas_demandas:
        cat = str(d.get('categoria', '')).strip().lower()
        st = str(d.get('status', '')).strip().lower()
        if cat != 'audiovisual' and st in ('em andamento', 'em_andamento', 'aprovada', 'aprovado'):
            kpi_tarefas_exec += 1

    # ══════════════════════════════════════════════════════════
    #  ALERTA DE PENDÊNCIAS (para admin/supervisor)
    # ══════════════════════════════════════════════════════════
    if kpi_pendentes > 0 and user_role in ('admin', 'supervisor'):
        with ui.card().classes(
            'w-full q-pa-sm no-shadow rounded-xl q-mb-sm q-mx-md'
        ).style('background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.3);'):
            with ui.row().classes('w-full items-center justify-between gap-3 flex-wrap'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('warning', color='amber-5', size='sm').classes('animate-pulse')
                    ui.label(f'⚠️ {kpi_pendentes} demanda(s) aguardando aprovação').classes('text-xs font-bold text-amber-5')
                ui.button('Tramitar →', icon='visibility', on_click=lambda: ui.navigate.to('/comsoc_homologar')).props(
                    'unelevated color=amber-9 text-color=black dense'
                ).classes('text-xs')

    # ══════════════════════════════════════════════════════════
    #  KPIs — Barra de Métricas Clicáveis
    # ══════════════════════════════════════════════════════════
    with ui.row().classes('w-full gap-2 q-mb-md q-px-md kpi-row'):
        kpi_items = [
            {'label': 'PENDENTES', 'value': kpi_pendentes, 'icon': 'hourglass_top', 'color': 'amber', 'bg': 'rgba(245,158,11,0.08)', 'border': 'rgba(245,158,11,0.3)', 'path': '/comsoc_homologar'},
            {'label': 'APROVADAS', 'value': kpi_aprovadas, 'icon': 'check_circle', 'color': 'green', 'bg': 'rgba(34,197,94,0.08)', 'border': 'rgba(34,197,94,0.3)', 'path': '/comsoc_homologar'},
            {'label': 'EM EXECUÇÃO', 'value': kpi_tarefas_exec, 'icon': 'play_circle', 'color': 'primary', 'bg': 'rgba(197,160,89,0.08)', 'border': 'rgba(197,160,89,0.3)', 'path': '/comsoc_tarefas'},
            {'label': 'VENCIDAS', 'value': kpi_vencidas, 'icon': 'error', 'color': 'red', 'bg': 'rgba(255,23,68,0.08)', 'border': 'rgba(255,23,68,0.3)', 'path': '/comsoc_homologar'},
            {'label': 'HOJE', 'value': kpi_eventos_hoje, 'icon': 'today', 'color': 'primary', 'bg': 'rgba(197,160,89,0.08)', 'border': 'rgba(197,160,89,0.3)', 'path': None},
        ]
        for kpi in kpi_items:
            with ui.card().classes(
                'q-pa-sm no-shadow rounded-xl cursor-pointer hover:scale-[1.02] transition-all kpi-card'
            ).style(
                f"background: {kpi['bg']}; border: 1px solid {kpi['border']}; flex: 1; min-width: 100px;"
            ).on('click', lambda p=kpi['path']: ui.navigate.to(p) if p else None):
                with ui.row().classes('items-center gap-2 justify-center'):
                    ui.icon(kpi['icon'], color=kpi['color'], size='1.3rem')
                    with ui.column().classes('gap-0'):
                        ui.label(str(kpi['value'])).classes(f"text-lg font-black text-{kpi['color']}")
                        ui.label(kpi['label']).classes('text-[9px] font-bold text-grey-5 tracking-wider')

    # ══════════════════════════════════════════════════════════
    #  CALENDÁRIO MENSAL NATIVO
    # ══════════════════════════════════════════════════════════
    # Estado reativo do mês/ano e dia selecionado
    state = {'year': hoje.year, 'month': hoje.month, 'selected_date': None}

    with ui.card().classes('w-full q-mx-md rounded-xl no-shadow q-pa-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        # ── Navegação do mês ──
        with ui.row().classes('w-full items-center justify-between q-mb-sm'):
            btn_prev = ui.button(icon='chevron_left', on_click=lambda: nav_month(-1)).props('flat round dense color=cyan size=sm')
            month_label = ui.label('').classes('text-sm font-bold text-white tracking-wide')
            btn_next = ui.button(icon='chevron_right', on_click=lambda: nav_month(1)).props('flat round dense color=cyan size=sm')

        # ── Grade do calendário ──
        cal_container = ui.element('div').classes('cal-grid w-full')

        # ── Legenda ──
        with ui.row().classes('w-full justify-center gap-4 q-mt-sm'):
            for dot_cls, lbl in [('green', 'Aprovado'), ('amber', 'Pendente'), ('red', 'Vencido')]:
                with ui.row().classes('items-center gap-1'):
                    ui.element('span').classes(f'cal-dot {dot_cls}')
                    ui.label(lbl).classes('text-[10px] text-grey-5')

    # ── Container de Compromissos (abaixo do calendário) ──
    with ui.card().classes('w-full q-mx-md q-mt-sm rounded-xl no-shadow q-pa-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full items-center justify-between q-mb-sm'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('event_note', color='cyan', size='1.2rem')
                events_title = ui.label('PRÓXIMOS COMPROMISSOS').classes('text-sm font-bold text-white tracking-wide')
            events_counter = ui.label('').classes('text-[11px] text-grey-5 font-mono')
        events_container = ui.column().classes('w-full gap-1')

    # ══════════════════════════════════════════════════════════
    #  FEED DE NOTÍCIAS (Colapsável)
    # ══════════════════════════════════════════════════════════
    with ui.expansion('📰 FEED RÁPIDO — Informativos & Notícias Navais', icon='newspaper').classes(
        'w-full q-mx-md q-mt-sm rounded-xl no-shadow'
    ).style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ).props('dense') as feed_expansion:
        feed_container = ui.column().classes('w-full gap-2 q-pa-sm')

    # ──────────────────────────────────────────────────────────
    #  FUNÇÕES DE RENDERIZAÇÃO
    # ──────────────────────────────────────────────────────────

    def render_calendar():
        """Renderiza a grade mensal com marcadores de eventos."""
        cal_container.clear()
        y, m = state['year'], state['month']

        # Nomes dos meses em português
        meses_pt = ['', 'JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
                     'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
        month_label.text = f'{meses_pt[m]} {y}'

        # Dias do mês (calendar.monthcalendar já respeita firstweekday=MONDAY)
        cal_weeks = calendar.monthcalendar(y, m)

        with cal_container:
            # Cabeçalho dos dias da semana
            for dia_nome in DIAS_SEMANA:
                ui.label(dia_nome).classes('cal-header')

            # Dias do mês
            for week in cal_weeks:
                for day in week:
                    if day == 0:
                        ui.element('div').classes('cal-day empty')
                    else:
                        date_key = f'{y}-{m:02d}-{day:02d}'
                        is_today = (day == hoje.day and m == hoje.month and y == hoje.year)
                        is_selected = (state['selected_date'] == date_key)

                        classes = 'cal-day'
                        if is_today:
                            classes += ' today'
                        if is_selected:
                            classes += ' selected'

                        with ui.element('div').classes(classes).on(
                            'click', lambda e, dk=date_key: on_day_click(dk)
                        ):
                            ui.label(str(day)).style('line-height: 1;')
                            # Marcadores de eventos
                            statuses = eventos_por_dia.get(date_key, [])
                            if statuses:
                                with ui.element('div').classes('cal-dots'):
                                    has_approved = any(s in ('aprovada', 'aprovado', 'aprovadas') for s in statuses)
                                    has_pending = any(s in ('pendente', 'pendentes', 'ajustes', 'ajuste') for s in statuses)
                                    try:
                                        dt_check = datetime.strptime(date_key, '%Y-%m-%d').date()
                                        has_overdue = dt_check < hoje and has_pending
                                    except Exception:
                                        has_overdue = False

                                    if has_approved:
                                        ui.element('span').classes('cal-dot green')
                                    if has_pending and not has_overdue:
                                        ui.element('span').classes('cal-dot amber')
                                    if has_overdue:
                                        ui.element('span').classes('cal-dot red')

    def on_day_click(date_key):
        """Filtra compromissos pelo dia clicado."""
        if state['selected_date'] == date_key:
            state['selected_date'] = None
        else:
            state['selected_date'] = date_key
        render_calendar()
        render_events()

    def nav_month(delta):
        """Navega para o mês anterior/próximo."""
        m = state['month'] + delta
        y = state['year']
        if m < 1:
            m = 12
            y -= 1
        elif m > 12:
            m = 1
            y += 1
        state['month'] = m
        state['year'] = y
        state['selected_date'] = None
        render_calendar()
        render_events()

    def render_events():
        """Renderiza a lista de compromissos."""
        events_container.clear()
        selected = state['selected_date']

        if selected:
            # Filtrar por dia selecionado
            filtered = [d for d in todas_demandas if d.get('data_evento') == selected]
            try:
                dt_sel = datetime.strptime(selected, '%Y-%m-%d')
                events_title.text = f'COMPROMISSOS — {dt_sel.strftime("%d/%m/%Y")}'
            except Exception:
                events_title.text = f'COMPROMISSOS — {selected}'
        else:
            # Próximos 60 dias
            fim = hoje + timedelta(days=60)
            filtered = []
            for d in todas_demandas:
                try:
                    dt_ev = datetime.strptime(str(d.get('data_evento', '')), '%Y-%m-%d').date()
                    if hoje <= dt_ev <= fim:
                        st = str(d.get('status', '')).strip().lower()
                        if st not in ('concluida', 'concluido', 'concluidas', 'rejeitado', 'rejeitada'):
                            filtered.append(d)
                except Exception:
                    pass
            filtered.sort(key=lambda x: (x.get('data_evento', ''), x.get('hora_evento', '')))
            events_title.text = 'PRÓXIMOS COMPROMISSOS'

        events_counter.text = f'{len(filtered)} evento(s)'

        with events_container:
            if filtered:
                for ev in filtered:
                    is_approved = str(ev.get('status', '')).strip().lower() in ('aprovado', 'aprovada', 'aprovadas')
                    is_today_ev = ev.get('data_evento') == hoje.isoformat()
                    is_overdue = False
                    try:
                        dt_ev = datetime.strptime(str(ev.get('data_evento', '')), '%Y-%m-%d').date()
                        is_overdue = dt_ev < hoje
                    except Exception:
                        pass

                    row_border = 'border-emerald-500/30' if is_today_ev else ('border-red-500/30' if is_overdue else 'border-cyan-500/10')
                    row_bg = 'bg-emerald-950/20' if is_today_ev else ('bg-red-950/10' if is_overdue else 'bg-black/20')

                    # ── Desktop: linha horizontal ──
                    with ui.row().classes(
                        f'w-full items-center q-py-sm q-px-md rounded-lg gap-4 '
                        f'{row_bg} border {row_border} '
                        f'hover:border-cyan-500/40 transition-all event-row-desktop'
                    ):
                        ui.icon(
                            'check_circle' if is_approved else ('error' if is_overdue else 'schedule'),
                            color='green' if is_approved else ('red' if is_overdue else 'amber'),
                            size='1.1rem'
                        ).tooltip('Aprovado' if is_approved else ('Vencido' if is_overdue else 'Pendente'))

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

                        hora = ev.get('hora_evento', '--:--')
                        if hora and len(str(hora)) >= 5:
                            hora = str(hora)[:5]
                        ui.label(hora).classes('text-xs text-grey-4 font-mono').style('min-width:40px;')

                        ui.element('div').classes('bg-cyan-500/20').style('width:1px; height:28px;')

                        with ui.column().classes('gap-0 flex-grow'):
                            ui.label(ev.get('titulo_evento', 'Sem Título')).classes('text-sm font-bold text-white').style('line-height:1.3;')
                            loc = ev.get('local_evento', '')
                            if loc:
                                ui.label(f"📍 {loc}").classes('text-[11px] text-grey-5')

                        try:
                            from telegram_bot.handlers_common import _format_militar_responsavel
                            resp_str = _format_militar_responsavel(ev, db)
                        except Exception:
                            resp_str = ev.get('solicitante_nome', '—')
                        ui.label(resp_str).classes('text-[11px] text-amber-4 font-bold gt-xs').style(
                            'max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'
                        ).tooltip(resp_str)

                        with ui.row().classes('gap-1 items-center'):
                            def _edit(dem=ev):
                                from comsoc_homologar import open_editar_pauta_dialog
                                open_editar_pauta_dialog(dem, render_events)
                            ui.button(icon='edit', on_click=_edit).props('flat round dense color=cyan size=sm').tooltip('Editar')
                            gcal_url = make_gcal_sync_url(
                                title=ev.get('titulo_evento', ''),
                                date_str=ev.get('data_evento', hoje.isoformat()),
                                time_str=ev.get('hora_evento', '09:00'),
                                location=ev.get('local_evento', 'CGCFN'),
                                details=f"Solicitante: {ev.get('solicitante_nome', 'N/I')}"
                            )
                            ui.link('📅', gcal_url, new_tab=True).classes(
                                'text-sm q-pa-xs rounded hover:bg-cyan-900/40 transition-all'
                            ).tooltip('Sync Google Calendar')

                    # ── Mobile: card empilhado ──
                    with ui.card().classes(
                        f'w-full q-pa-sm rounded-lg no-shadow {row_bg} border {row_border} event-card-mobile'
                    ).style('display: none;'):
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon(
                                    'check_circle' if is_approved else ('error' if is_overdue else 'schedule'),
                                    color='green' if is_approved else ('red' if is_overdue else 'amber'),
                                    size='1rem'
                                )
                                date_str_m = ev.get('data_evento', '')
                                try:
                                    dt_m = datetime.strptime(date_str_m, '%Y-%m-%d')
                                    ui.label(dt_m.strftime('%d/%m %a').upper()).classes('text-xs font-bold text-cyan')
                                except Exception:
                                    ui.label(date_str_m).classes('text-xs font-bold text-cyan')
                                hora_m = ev.get('hora_evento', '')
                                if hora_m:
                                    ui.label(str(hora_m)[:5]).classes('text-xs text-grey-4 font-mono')
                            with ui.row().classes('gap-1'):
                                def _edit_m(dem=ev):
                                    from comsoc_homologar import open_editar_pauta_dialog
                                    open_editar_pauta_dialog(dem, render_events)
                                ui.button(icon='edit', on_click=_edit_m).props('flat round dense color=cyan size=xs')
                        ui.label(ev.get('titulo_evento', 'Sem Título')).classes('text-sm font-bold text-white q-mt-xs')
                        loc_m = ev.get('local_evento', '')
                        if loc_m:
                            ui.label(f"📍 {loc_m}").classes('text-[11px] text-grey-5')
            else:
                with ui.column().classes('w-full items-center q-py-lg gap-2'):
                    ui.icon('event_available', size='2rem', color='cyan')
                    if selected:
                        ui.label('Nenhum compromisso neste dia.').classes('text-xs text-grey-5')
                    else:
                        ui.label('Nenhum compromisso nos próximos 60 dias.').classes('text-xs text-grey-5')

    def render_feed():
        """Renderiza feed de notícias e informativos."""
        feed_container.clear()

        with feed_container:
            # Informativos internos
            boletins = []
            db_f = get_service_db_connection() or get_db_connection()
            if db_f:
                try:
                    res = db_f.table('comsoc_noticias').select('*').order('data', desc=True).limit(3).execute()
                    boletins = res.data if res.data else []
                except Exception:
                    pass

            if not boletins:
                try:
                    from sqlite_adapter import SQLiteDatabaseAdapter
                    loc_db = SQLiteDatabaseAdapter()
                    res_loc = loc_db.table('comsoc_noticias').select('*').order('data', desc=True).limit(3).execute()
                    boletins = res_loc.data if res_loc.data else []
                except Exception:
                    pass

            if boletins:
                ui.label('📢 Informativos Internos').classes('text-xs font-bold text-white q-mb-xs')
                for b in boletins:
                    with ui.row().classes('w-full items-center gap-3 q-py-xs').style('border-bottom: 1px solid rgba(197,160,89,0.06);'):
                        ui.label(b.get('titulo', '')).classes('text-xs font-bold text-cyan flex-grow')
                        ui.label(b.get('data', '')).classes('text-[9px] text-grey-5')
                        if b.get('tags'):
                            ui.badge(b['tags']).props('color=cyan outline').classes('text-[8px]')

            # Notícias externas
            ui.label('⚓ Notícias Navais').classes('text-xs font-bold text-white q-mt-md q-mb-xs')
            external_news = fetch_rss_news()
            for item in external_news:
                with ui.row().classes('w-full items-center gap-3 q-py-xs').style('border-bottom: 1px solid rgba(255,255,255,0.03);'):
                    ui.link(item['titulo'], target=item['link'], new_tab=True).classes(
                        'text-xs text-white no-underline hover:underline hover:text-cyan flex-grow'
                    )
                    ui.label(item['data']).classes('text-[9px] text-grey-5')
                    ui.label(item['fonte']).classes('text-[9px] text-amber-5 font-bold')

            # Botão de novo boletim para editores
            if is_editor:
                ui.button('Novo Boletim', icon='add', on_click=lambda: open_bulletin_dialog()).props(
                    'unelevated color=cyan text-color=black dense'
                ).classes('text-xs q-mt-sm')

    def open_bulletin_dialog():
        """Diálogo para lançar novo boletim informativo."""
        with ui.dialog() as dlg, ui.card().classes('w-96 q-pa-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            ui.label('📢 NOVO BOLETIM').classes('text-white text-md font-bold')
            titulo_in = ui.input('Título').props('dark outlined dense w-full')
            conteudo_in = ui.textarea('Conteúdo').props('dark outlined w-full').classes('text-xs')
            tags_in = ui.input('Tags').props('dark outlined dense w-full')

            def save():
                if not titulo_in.value or not conteudo_in.value:
                    ui.notify('Preencha título e conteúdo.', color='warning')
                    return
                registro = {
                    'titulo': titulo_in.value,
                    'conteudo': conteudo_in.value,
                    'autor': user_data.get('nome_guerra', 'Operador').upper(),
                    'data': datetime.now().strftime('%Y-%m-%d'),
                    'tags': tags_in.value
                }
                db_s = get_service_db_connection() or get_db_connection()
                saved = False
                if db_s:
                    try:
                        db_s.table('comsoc_noticias').insert(registro).execute()
                        saved = True
                    except Exception as e:
                        print(f"[SAVE BULLETIN ERR] {e}")
                if not saved:
                    try:
                        from sqlite_adapter import SQLiteDatabaseAdapter
                        SQLiteDatabaseAdapter().table('comsoc_noticias').insert(registro).execute()
                    except Exception as e:
                        ui.notify(f'Erro: {e}', color='negative')
                        return
                ui.notify('Boletim registrado!', color='positive')
                dlg.close()
                render_feed()

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Cancelar', on_click=dlg.close).props('flat color=grey')
                ui.button('Lançar', on_click=save).props('unelevated color=cyan text-color=black bold')
        dlg.open()

    # ── Renderização Inicial ──
    render_calendar()
    render_events()
    render_feed()
