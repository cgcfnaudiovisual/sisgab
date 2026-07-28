# sisgab_tv.py
import os
from datetime import datetime, timedelta
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

def render_page():
    # Estilos CSS customizados para o letreiro de notícias (Ticker Marquee)
    ui.add_head_html("""
    <style>
    @keyframes marquee {
        0% { transform: translate3d(0, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }
    .marquee-container {
        overflow: hidden;
        white-space: nowrap;
        box-sizing: border-box;
        width: 100%;
        position: relative;
    }
    .marquee-content {
        display: inline-block;
        padding-left: 100%;
        animation: marquee 25s linear infinite;
        font-weight: bold;
    }
    .marquee-content:hover {
        animation-play-state: paused;
    }
    </style>
    """)

    def fresh_db():
        return get_db_connection()

    view_state = {'active': 'semana'}
    last_known_pendentes = [-1]

    # Layout de tela cheia para a TV
    with ui.column().classes('w-full min-h-screen q-pa-md gap-4 overflow-hidden').style(
        'background: radial-gradient(circle, #0c1020 0%, #05070e 100%); font-family: "Outfit", sans-serif;'
    ):
        # ── CABEÇALHO TÁTICO (Fixo) ──
        with ui.row().classes('w-full justify-between items-center q-pb-xs border-b border-cyan-500/30'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('tv', size='2.5rem', color='cyan-5')
                with ui.column().classes('gap-0'):
                    ui.label('MONITOR TÁTICO COMSOC').style('font-size: 1.5rem; font-weight: 900; color: #ffffff; letter-spacing: 2px;')
                    ui.label('CENTRAL DE OPERAÇÕES E COMUNICAÇÃO').style('font-size: 0.65rem; color: #00e5ff; font-weight: 700; letter-spacing: 1px;')
            
            with ui.row().classes('items-center gap-2'):
                def open_tv_missao_rapida_dialog():
                    with ui.dialog() as diag, ui.card().classes('w-96 q-pa-md bg-slate-900 border border-deep-orange-500/50 rounded-xl'):
                        ui.label('⚡ LANÇAR MISSÃO RÁPIDA (TV)').classes('text-deep-orange font-bold text-md cyber-title')
                        ui.label('Cadastre uma missão de campo urgente diretamente pelo painel.').classes('text-xs text-grey-4 q-mb-sm')
                        tit_inp = ui.input('Título / Objetivo da Missão', placeholder='Ex: Cobertura Urgente Chegada Comandante').props('dark outlined dense w-full')
                        loc_inp = ui.input('Local', value='Gabinete / COMSOC').props('dark outlined dense w-full')
                        
                        def salvar_missao():
                            t = tit_inp.value.strip()
                            if not t:
                                ui.notify('Digite um título válido', color='warning')
                                return
                            try:
                                db = fresh_db()
                                if db:
                                    now_str = datetime.now().strftime('%Y-%m-%d')
                                    db.table('demandas_comunicacao').insert({
                                        'titulo_evento': f"⚡ {t}",
                                        'solicitante_nome': 'MONITOR TV',
                                        'contato': 'COMSOC / Monitor TV',
                                        'setor': 'COMSOC / GABINETE',
                                        'data_evento': now_str,
                                        'hora_evento': datetime.now().strftime('%H:%M'),
                                        'local_evento': loc_inp.value or 'Gabinete',
                                        'status': 'aprovada',
                                        'categoria_demanda': 'audiovisual'
                                    }).execute()
                                    ui.notify(f"⚡ Missão Rápida '{t}' lançada com sucesso!", color='positive')
                                    diag.close()
                                    render_tv_dashboard.refresh()
                            except Exception as e:
                                ui.notify(f'Erro ao lançar missão: {e}', color='negative')

                        with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                            ui.button('Cancelar', on_click=diag.close).props('flat color=grey text-color=white')
                            ui.button('⚡ Lançar Agora', on_click=salvar_missao).props('unelevated color=deep-orange text-color=white bold')
                    diag.open()

                ui.button('⚡ Missão Rápida', on_click=open_tv_missao_rapida_dialog).props('unelevated color=deep-orange-9 text-color=white dense bold icon=flash_on').classes('text-xs q-px-sm')
                ui.button('🪪 Placas JADE', on_click=lambda: app.navigate.to('/comsoc_assentos')).props('outline color=indigo-4 text-color=white dense bold icon=badge').classes('text-xs q-px-sm')
                
                def toggle_alerts(val):
                    app.storage.user['tv_alerts_enabled'] = val
                    render_tv_dashboard.refresh()

                alerts_enabled = app.storage.user.get('tv_alerts_enabled', True)
                ui.checkbox('Card Alertas', value=alerts_enabled, on_change=lambda e: toggle_alerts(e.value)).props('dark dense').classes('text-xs text-white q-ml-sm')

            # Relógio Digital Gigante (Horário de Brasília GMT-3)
            with ui.column().classes('items-end gap-0'):
                nonlocal_time = ui.label('').style('font-size: 1.8rem; font-weight: 900; color: #ffffff; line-height: 1;')
                nonlocal_date = ui.label('').style('font-size: 0.75rem; color: #a1a1aa; font-weight: bold; letter-spacing: 1.5px;')
                
                def update_clock():
                    now_br = datetime.utcnow() - timedelta(hours=3)
                    nonlocal_time.text = now_br.strftime('%H:%M:%S')
                    nonlocal_date.text = now_br.strftime('%d DE %B DE %Y').upper()
                
                ui.timer(1.0, update_clock)
                update_clock()

        # ── PAINEL PRINCIPAL REFRESHÁVEL AUTOMATICAMENTE ──
        @ui.refreshable
        def render_tv_dashboard():
            db = fresh_db()
            efetivo_nomes = {}

            def get_militar_nome(m_id):
                if m_id is None:
                    return None
                try:
                    return efetivo_nomes.get(int(m_id)) or efetivo_nomes.get(str(m_id))
                except:
                    return efetivo_nomes.get(str(m_id))

            def translate_day(day_lbl):
                day_lbl = str(day_lbl).upper().strip()
                mapping = {
                    'MON': 'SEG',
                    'TUE': 'TER',
                    'WED': 'QUA',
                    'THU': 'QUI',
                    'FRI': 'SEX',
                    'SAT': 'SAB',
                    'SUN': 'DOM'
                }
                return mapping.get(day_lbl, day_lbl)

            # 1. CARGA DE KPIS OPERACIONAIS E ESTRATÉGICOS
            total_pautas = 0
            demandas_pendentes = 0
            demandas_ajustes = 0
            eventos_24h = 0
            taxa_entregas_str = "100%"
            efetivo_pronto_str = "0 / 0"
            jade_event_name = "Nenhum"
            jade_printed = 0
            jade_total = 0
            missoes_rapidas_cnt = 0

            hoje = (datetime.utcnow() - timedelta(hours=3)).date()
            amanha = hoje + timedelta(days=1)
            hoje_str = hoje.strftime('%Y-%m-%d')

            if db:
                try:
                    res_p = db.table('demandas_comunicacao').select('id, status, data_evento').execute()
                    if res_p.data:
                        todas = res_p.data
                        aprovadas_cnt = 0
                        concluidas_cnt = 0

                        for d in todas:
                            st = str(d.get('status', '')).strip().lower()
                            if st in ('aprovada', 'aprovado', 'aprovadas'):
                                aprovadas_cnt += 1
                            elif st in ('pendente', 'pendentes'):
                                demandas_pendentes += 1
                            elif st in ('ajustes', 'ajuste'):
                                demandas_ajustes += 1
                            elif st in ('concluida', 'concluido', 'concluidas'):
                                concluidas_cnt += 1

                            dt_str = str(d.get('data_evento', ''))
                            try:
                                dt_ev = datetime.strptime(dt_str, '%Y-%m-%d').date()
                                if dt_ev in (hoje, amanha):
                                    eventos_24h += 1
                            except Exception:
                                pass

                        total_pautas = aprovadas_cnt
                        if (concluidas_cnt + aprovadas_cnt) > 0:
                            pct = int((concluidas_cnt / (concluidas_cnt + aprovadas_cnt)) * 100)
                            taxa_entregas_str = f"{pct}%"

                    res_ef = db.table('efetivo').select('id, nome_guerra, posto_grad').execute()
                    tot_ef = len(res_ef.data) if res_ef.data else 0
                    if res_ef.data:
                        for m in res_ef.data:
                            pg = m.get('posto_grad') or ''
                            ng = m.get('nome_guerra') or 'Militar'
                            efetivo_nomes[m['id']] = f"{pg} {ng}".strip()

                    res_pr = db.table('presenca_diaria').select('id, status').eq('data', hoje_str).execute()
                    if res_pr.data:
                        prontos = len([p for p in res_pr.data if str(p.get('status', '')).upper() in ('P', 'MA', 'MT')])
                        efetivo_pronto_str = f"{prontos}/{tot_ef}"
                    else:
                        efetivo_pronto_str = f"{tot_ef}/{tot_ef}"

                    # 2. CARGA DE KPIS JADE & MISSÕES RÁPIDAS
                    try:
                        res_ev = db.table('jade_eventos').select('*').order('data_evento', desc=True).limit(1).execute()
                        if res_ev.data:
                            active_ev = res_ev.data[0]
                            jade_event_name = active_ev.get('nome', 'Solenidade')
                            res_c = db.table('jade_convidados').select('id, status_placa').eq('evento_id', active_ev['id']).execute()
                            if res_c.data:
                                convs = res_c.data
                                jade_total = len(convs)
                                jade_printed = sum(1 for c in convs if c.get('status_placa') == 'impressa')
                    except Exception as j_err:
                        print(f"[TV JADE KPI ERR] {j_err}")

                    try:
                        res_mr = db.table('demandas_comunicacao').select('id').eq('data_evento', hoje_str).like('titulo_evento', '%⚡%').execute()
                        if res_mr.data:
                            missoes_rapidas_cnt = len(res_mr.data)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[TV KPIs ERR] {e}")

            # Alerta sonoro/visual se houver novas demandas pendentes
            if last_known_pendentes[0] != -1 and demandas_pendentes > last_known_pendentes[0]:
                diff = demandas_pendentes - last_known_pendentes[0]
                ui.notify(
                    f'🚨 {diff} NOVA(S) DEMANDA(S) PENDENTE(S)!',
                    color='warning',
                    position='top',
                    timeout=15000,
                    close_button='OK'
                )
            last_known_pendentes[0] = demandas_pendentes

            # ── BLOCO 1: PAINEL DE KPIs OPERACIONAIS (CARDS TÁTICOS COMPLETO) ──
            with ui.row().classes('w-full gap-2 justify-between items-center q-mt-xs flex-wrap'):
                # KPI 1: Pautas Aprovadas
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('camera_alt', color='cyan-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PAUTAS ATIVAS').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(total_pautas)).classes('text-lg font-black text-white')
                
                # KPI 2: Pendente Análise
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('hourglass_top', color='amber-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PENDENTE ANÁLISE').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(demandas_pendentes)).classes('text-lg font-black text-amber-4')

                # KPI 3: Em Ajuste
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('build_circle', color='orange-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('EM AJUSTE').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(demandas_ajustes)).classes('text-lg font-black text-orange-4')

                # KPI 4: Prontidão 24 Horas
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('bolt', color='yellow-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PRONTIDÃO 24H').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(eventos_24h)).classes('text-lg font-black text-yellow-4')

                # KPI 5: Missões Rápidas Hoje
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('flash_on', color='deep-orange-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('MISSÕES RÁPIDAS').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(missoes_rapidas_cnt)).classes('text-lg font-black text-deep-orange-4')

                # KPI 6: Placas JADE (Solenidade)
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('badge', color='indigo-4', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PLACAS JADE').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(f"{jade_printed}/{jade_total} IMP.").classes('text-sm font-black text-indigo-3')

                # KPI 7: Efetivo no Pronto
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 130px;'):
                    ui.icon('shield', color='teal-4', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('EFETIVO NO PRONTO').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(efetivo_pronto_str).classes('text-lg font-black text-teal-3')

            # ── SELO HIGHLIGHT: COBERTURA EM TEMPO REAL / PRÓXIMO EVENTO ──
            agora_dt = datetime.utcnow() - timedelta(hours=3)
            show_alerts = app.storage.user.get('tv_alerts_enabled', True)
            pautas_alertas = []
            
            if db and show_alerts:
                try:
                    res_live = db.table('demandas_comunicacao').select('*').eq('data_evento', hoje_str).execute()
                    if res_live.data:
                        for p_live in res_live.data:
                            st_live = str(p_live.get('status', '')).strip().lower()
                            if st_live in ('aprovada', 'aprovado', 'aprovadas'):
                                hr_str = str(p_live.get('hora_evento', '09:00'))
                                try:
                                    hr_dt = datetime.strptime(f"{hoje_str} {hr_str[:5]}", '%Y-%m-%d %H:%M')
                                    diff_mins = (agora_dt - hr_dt).total_seconds() / 60.0
                                    
                                    # LIVE: entre 30 minutos antes e 120 minutos depois do início
                                    if -30 <= diff_mins <= 120:
                                        p_live['alert_type'] = 'LIVE'
                                        pautas_alertas.append(p_live)
                                    # PRÓXIMO: mais de 30 minutos antes do início (ainda vai acontecer hoje)
                                    elif diff_mins < -30:
                                        p_live['alert_type'] = 'NEXT'
                                        pautas_alertas.append(p_live)
                                except Exception:
                                    pass
                except Exception as live_err:
                    print(f"[TV LIVE HIGHLIGHT ERR] {live_err}")

            if pautas_alertas:
                # Ordena os alertas (LIVE primeiro, depois os de NEXT por hora)
                pautas_alertas.sort(key=lambda x: (0 if x.get('alert_type') == 'LIVE' else 1, x.get('hora_evento', '')))
                
                # Rotaciona entre os alertas a cada 15 segundos com base no timestamp
                alert_idx = (int(datetime.utcnow().timestamp() // 15)) % len(pautas_alertas)
                pauta_alerta = pautas_alertas[alert_idx]
                
                is_live = pauta_alerta.get('alert_type') == 'LIVE'
                badge_text = '🔴 EM COBERTURA AGORA' if is_live else '⏳ PRÓXIMO EVENTO'
                card_style = 'background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.5);' if is_live else 'background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.3);'
                badge_color = 'red-10' if is_live else 'cyan-9'
                
                hr_txt = str(pauta_alerta.get('hora_evento', '09:00'))[:5]
                enc_id = pauta_alerta.get('encarregado_id')
                enc_nome = get_militar_nome(enc_id)

                with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl flex-row items-center justify-between no-wrap q-mb-xs').style(f'{card_style} {"animate-pulse" if is_live else ""};'):
                    with ui.row().classes('items-center gap-2 col-grow truncate'):
                        ui.badge(badge_text, color=badge_color).classes('text-xs font-black tracking-wider q-px-sm')
                        ui.label(pauta_alerta.get('titulo_evento', 'Sem Título').upper()).classes('text-xs font-bold text-white truncate max-w-[450px]')
                    with ui.row().classes('items-center gap-3 text-[11px] text-slate-200 font-bold shrink-0'):
                        ui.label(f"🕒 {hr_txt}").classes('text-amber-4')
                        ui.label(f"📍 {pauta_alerta.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4')
                        if enc_nome:
                            ui.badge(f"🎖️ {enc_nome.upper()}", color='green-9').classes('text-[9px] font-bold')
                        ui.label(f"👤 {pauta_alerta.get('solicitante_nome', 'COMSOC').upper()}").classes('text-grey-4 text-[10px]')

            # ── GRIDS PRINCIPAIS DO MONITOR ──
            with ui.grid(columns=1).classes('w-full gap-4 flex-grow gt-xs').style('grid-template-columns: 1.2fr 1.1fr 1fr; margin-top: 6px;'):
                
                # =========================================================================
                # COLUNA 1 (ESQUERDA): CRONOGRAMA DE PRODUÇÃO & FILTRO MULTI-PAINEL
                # =========================================================================
                with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                    with ui.row().classes('w-full items-center justify-between q-mb-md no-wrap'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('calendar_month', color='cyan-5', size='sm')
                            ui.label('CRONOGRAMA DE PRODUÇÃO').classes('text-sm font-bold text-white tracking-wider')
                        
                        def on_view_change(e):
                            view_state['active'] = e.value
                            render_tv_dashboard.refresh()

                        ui.select(
                            {
                                'semana': 'Esta Semana',
                                'mes': 'Este Mês',
                                'kanban': 'Quadro Kanban',
                                'todas': 'Todas as Demandas'
                            }, 
                            value=view_state['active'],
                            on_change=on_view_change
                        ).props('dark dense options-dense outlined').style('font-size: 10px; width: 125px;')

                    pautas = []
                    if db:
                        try:
                            res_c = db.table('demandas_comunicacao').select('*').execute()
                            if res_c.data:
                                pautas = res_c.data
                        except Exception as e:
                            print(f"[TV CALENDAR DB ERR] {e}")

                    if not pautas:
                        with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('calendar_today', size='2.5rem')
                            ui.label('Sem pautas registradas.').classes('text-xs')
                    else:
                        hoje_dt = datetime.utcnow() - timedelta(hours=3)
                        active_view = view_state['active']

                        if active_view == 'semana':
                            limite_semana = hoje_dt + timedelta(days=7)
                            pautas_filtradas = []
                            for p in pautas:
                                try:
                                    p_dt = datetime.strptime(str(p.get('data_evento', '')), '%Y-%m-%d')
                                    if hoje_dt.date() <= p_dt.date() <= limite_semana.date():
                                        pautas_filtradas.append((p, p_dt))
                                except Exception:
                                    pass
                            pautas_filtradas.sort(key=lambda x: x[1])

                            if pautas_filtradas:
                                with ui.column().classes('w-full gap-2 max-h-[420px] overflow-y-auto q-pr-xs'):
                                    for p, p_dt in pautas_filtradas:
                                        dia_semana_lbl = p_dt.strftime('%a').upper()
                                        dia_num = p_dt.strftime('%d/%m')
                                        st_val = str(p.get('status', '')).strip().lower()
                                        is_pend = st_val in ('pendente', 'pendentes')
                                        prio = p.get('prioridade', 'normal')

                                        border_col = "#ef4444" if prio == 'altissima' else "#f97316" if prio == 'alta' else "#00e5ff" if not is_pend else "#eab308"

                                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg transition-all').style(
                                            f'background: rgba(255,255,255,0.02); border-left: 4px solid {border_col}; border-top: 1px solid rgba(255,255,255,0.05);'
                                        ):
                                            dia_semana_trad = translate_day(dia_semana_lbl)
                                            hr_txt = str(p.get('hora_evento', '09:00'))[:5]
                                            enc_id = p.get('encarregado_id')
                                            enc_nome = get_militar_nome(enc_id)

                                            with ui.row().classes('w-full justify-between items-start no-wrap gap-2'):
                                                with ui.row().classes('items-start gap-2 col-grow'):
                                                    ui.label(f"{dia_semana_trad} {dia_num}").classes('text-xs font-black text-cyan font-mono shrink-0 q-mt-xs').style('min-width: 75px;')
                                                    ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-xs font-bold text-white leading-tight break-words col-grow')
                                                
                                                if is_pend:
                                                    ui.badge('PENDENTE', color='amber-9').classes('text-[8px] font-bold shrink-0 q-mt-xs')
                                                else:
                                                    ui.badge('APROVADA', color='green-9').classes('text-[8px] font-bold shrink-0 q-mt-xs')

                                            with ui.row().classes('w-full justify-between items-center q-mt-xs text-[10px] text-slate-300'):
                                                with ui.row().classes('items-center gap-2 wrap col-grow'):
                                                    ui.label(f"🕒 {hr_txt}").classes('text-amber-4 font-bold')
                                                    ui.label('|').classes('text-white/20')
                                                    ui.label(f"📍 {p.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4 font-bold')
                                                    if enc_nome:
                                                        ui.label('|').classes('text-white/20')
                                                        ui.label(f"🎖️ {enc_nome.upper()}").classes('text-green-4 font-black')
                                                ui.label(f"👤 {p.get('solicitante_nome', 'CGCFN').upper()}").classes('text-grey-4 text-[9px] shrink-0 font-semibold')
                            else:
                                with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                                    ui.icon('event_busy', size='2.5rem')
                                    ui.label('Sem pautas para esta semana.').classes('text-xs')

                        elif active_view == 'mes':
                            mes_atual = hoje_dt.month
                            pautas_filtradas = []
                            for p in pautas:
                                try:
                                    p_dt = datetime.strptime(str(p.get('data_evento', '')), '%Y-%m-%d')
                                    if p_dt.month == mes_atual:
                                        pautas_filtradas.append((p, p_dt))
                                except Exception:
                                    pass
                            pautas_filtradas.sort(key=lambda x: x[1])

                            if pautas_filtradas:
                                with ui.column().classes('w-full gap-2 max-h-[420px] overflow-y-auto q-pr-xs'):
                                    for p, p_dt in pautas_filtradas:
                                        dia_num = p_dt.strftime('%d/%m')
                                        st_val = str(p.get('status', '')).strip().lower()
                                        status_color = 'text-red' if st_val in ('pendente', 'pendentes') else 'text-cyan'
                                        with ui.row().classes('w-full items-center justify-between border-b border-white/5 py-1 text-xs'):
                                            ui.label(f"📅 {dia_num} - {p.get('titulo_evento', 'Sem Título').upper()}").classes('text-white font-bold truncate max-w-[210px]')
                                            ui.label(st_val.upper()).classes(f'text-[8px] font-bold shrink-0 {status_color}')
                            else:
                                with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                                    ui.icon('calendar_today', size='2.5rem')
                                    ui.label('Sem pautas para este mês.').classes('text-xs')

                        elif active_view == 'kanban':
                            col_pend = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('pendente', 'pendentes')][:4]
                            col_aprov = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas')][:4]
                            
                            with ui.row().classes('w-full gap-2 items-stretch'):
                                with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                    ui.label('🔴 ANÁLISE').classes('text-[9px] font-black text-red-4 text-center w-full tracking-wider q-mb-xs')
                                    for p in col_pend:
                                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(255,0,0,0.05); border: 1px solid rgba(255,0,0,0.15);'):
                                            ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-[9.5px] font-bold text-white truncate')
                                            ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[8px] text-grey-4')
                                    if not col_pend:
                                        ui.label('Fila Limpa').classes('text-[8px] text-grey-6 text-center w-full py-4')

                                with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                    ui.label('🟢 APROVADO').classes('text-[9px] font-black text-cyan-4 text-center w-full tracking-wider q-mb-xs')
                                    for p in col_aprov:
                                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.15);'):
                                            ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-[9.5px] font-bold text-white truncate')
                                            ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[8px] text-grey-4')
                                    if not col_aprov:
                                        ui.label('Sem pautas').classes('text-[8px] text-grey-6 text-center w-full py-4')

                        else:
                            # Visão: TODAS AS DEMANDAS EXISTENTES
                            with ui.column().classes('w-full gap-2 max-h-[420px] overflow-y-auto q-pr-xs'):
                                for p in pautas:
                                    st_val = str(p.get('status', '')).strip().lower()
                                    st_badge_color = 'green' if st_val in ('aprovada', 'aprovado') else 'grey' if st_val == 'concluida' else 'amber'
                                    data_txt = str(p.get('data_evento', 'N/I'))
                                    try:
                                        data_txt = datetime.strptime(data_txt[:10], '%Y-%m-%d').strftime('%d/%m')
                                    except Exception:
                                        pass

                                    with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 3px solid rgba(0,229,255,0.3);'):
                                        with ui.row().classes('w-full justify-between items-center no-wrap'):
                                            ui.label(f"{data_txt} - {p.get('titulo_evento', 'Sem Título').upper()}").classes('text-xs font-bold text-white truncate max-w-[200px]')
                                            ui.badge(st_val.upper()).props(f'color={st_badge_color}').classes('text-[8px]')

                # =========================================================================
                # COLUNA 2 (CENTRO): DEMANDAS DO DIA CORRENTE E DIA SEGUINTE (HOJE & AMANHÃ)
                # =========================================================================
                with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                    with ui.row().classes('w-full items-center justify-between q-mb-md'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('today', color='amber-5', size='sm')
                            ui.label('PAUTAS: HOJE & AMANHÃ').classes('text-sm font-bold text-white tracking-wider')
                        ui.badge('PRONTIDÃO 48H', color='amber-9').classes('text-[8px] font-mono')

                    pautas_hoje_amanha = []
                    hoje_obj = (datetime.utcnow() - timedelta(hours=3)).date()
                    amanha_obj = hoje_obj + timedelta(days=1)

                    if pautas:
                        for p in pautas:
                            try:
                                p_dt = datetime.strptime(str(p.get('data_evento', '')), '%Y-%m-%d').date()
                                if p_dt in (hoje_obj, amanha_obj):
                                    pautas_hoje_amanha.append((p, p_dt))
                            except Exception:
                                pass
                        pautas_hoje_amanha.sort(key=lambda x: (x[1], x[0].get('hora_evento', '')))

                    if pautas_hoje_amanha:
                        with ui.column().classes('w-full gap-2 max-h-[420px] overflow-y-auto q-pr-xs'):
                            for p, p_dt in pautas_hoje_amanha:
                                is_hoje = (p_dt == hoje_obj)
                                tag_dia = "HOJE" if is_hoje else "AMANHÃ"
                                tag_bg = "rgba(245,158,11,0.2)" if is_hoje else "rgba(0,229,255,0.15)"
                                border_tag = "#f59e0b" if is_hoje else "#00e5ff"
                                st_val = str(p.get('status', '')).strip().lower()

                                with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style(
                                    f'background: {tag_bg}; border: 1px solid {border_tag};'
                                ):
                                    hr_txt = str(p.get('hora_evento', '09:00'))[:5]
                                    enc_id = p.get('encarregado_id')
                                    enc_nome = get_militar_nome(enc_id)

                                    with ui.row().classes('w-full justify-between items-start no-wrap gap-2'):
                                        with ui.row().classes('items-start gap-2 col-grow'):
                                            ui.badge(tag_dia, color='amber-9' if is_hoje else 'cyan-9').classes('text-[9px] font-black shrink-0 q-mt-xs')
                                            ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-xs font-bold text-white leading-tight break-words col-grow')
                                        
                                        # Badges uniformes
                                        if st_val in ('pendente', 'pendentes'):
                                            ui.badge('PENDENTE', color='amber-9').classes('text-[8px] font-bold shrink-0 q-mt-xs')
                                        else:
                                            ui.badge('APROVADA', color='green-9').classes('text-[8px] font-bold shrink-0 q-mt-xs')

                                    with ui.row().classes('w-full justify-between items-center q-mt-xs text-[10px] text-slate-300'):
                                        with ui.row().classes('items-center gap-2 wrap col-grow'):
                                            ui.label(f"🕒 {hr_txt}").classes('text-amber-4 font-bold')
                                            ui.label('|').classes('text-white/20')
                                            ui.label(f"📍 {p.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4 font-bold')
                                            if enc_nome:
                                                ui.label('|').classes('text-white/20')
                                                ui.label(f"🎖️ {enc_nome.upper()}").classes('text-green-4 font-black')
                                        ui.label(f"👤 {p.get('solicitante_nome', 'CGCFN').upper()}").classes('text-grey-4 text-[9px] shrink-0 font-semibold')
                    else:
                        with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('event_available', size='2.5rem')
                            ui.label('Nenhuma pauta agendada para hoje ou amanhã.').classes('text-xs')

                # =========================================================================
                # COLUNA 3 (DIREITA): ESCALA DE SERVIÇO (TOPO) + CARROSSEL (BASE)
                # =========================================================================
                with ui.column().classes('w-full gap-3 flex-grow q-pa-none'):
                    


                    # BLOCO 1.5: ALERTA TÁTICO DE PLACAS JADE PENDENTES
                    count_jade_pending = 0
                    if db:
                        try:
                            res_j = db.table('jade_convidados').select('*').eq('status_placa', 'pendente').execute()
                            count_jade_pending = len(res_j.data) if res_j.data else 0
                        except Exception:
                            pass
                            
                    if count_jade_pending > 0:
                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-xl border border-amber-500/50 flex-row items-center justify-between no-wrap animate-pulse').style('background: rgba(245,158,11,0.15);'):
                            with ui.row().classes('items-center gap-1.5'):
                                ui.icon('print', color='amber-4', size='xs')
                                ui.label('PLACAS JADE PENDENTES:').classes('text-[10px] font-black text-amber-4 tracking-wider')
                            ui.badge(f'{count_jade_pending} PLACAS', color='amber-10').classes('text-[10px] font-black')

                    # BLOCO 2: MODO CARROSSEL DE INFORMATIVOS & EFEMÉRIDES (PAINEL INFERIOR)
                    slide_idx = (int(datetime.utcnow().timestamp() // 15)) % 3
                    slide_headers = [
                        ('announcement', '📢 BOLETINS COMSOC'),
                        ('anchor', '⚓ SETOR NAVAL'),
                        ('event', '🎂 EFEMÉRIDES MB')
                    ]
                    icon_name, title_lbl = slide_headers[slide_idx]

                    with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl border border-cyan-950/60 flex-col justify-between flex-grow').style('background: rgba(10,15,30,0.45);'):
                        with ui.column().classes('w-full gap-2'):
                            with ui.row().classes('w-full items-center justify-between q-mb-xs'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(icon_name, color='cyan-5', size='xs')
                                    ui.label(title_lbl).classes('text-xs font-bold text-white tracking-wider')
                                ui.badge(f"{slide_idx+1}/3", color='cyan-9').classes('text-[8px] font-mono')

                            if slide_idx == 0:
                                boletins = []
                                if db:
                                    try:
                                        res = db.table('comsoc_noticias').select('*').order('data', desc=True).limit(2).execute()
                                        boletins = res.data if res.data else []
                                    except Exception:
                                        pass
                                        
                                if boletins:
                                    with ui.column().classes('w-full gap-1 q-mt-xs'):
                                        for b in boletins:
                                            with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 3px solid #00e5ff;'):
                                                ui.label(b.get('titulo', '')).classes('text-[11px] font-bold text-cyan truncate')
                                                ui.label(str(b.get('conteudo', ''))[:70] + "...").classes('text-[9px] text-grey-4 q-mt-xs')
                                else:
                                    ui.label('Nenhum boletim ativo.').classes('text-[10px] text-grey-5 py-4 text-center w-full')

                            elif slide_idx == 1:
                                try:
                                    from comsoc_noticias import fetch_rss_news
                                    rss_items = fetch_rss_news()[:2]
                                except Exception:
                                    rss_items = []
                                
                                if rss_items:
                                    with ui.column().classes('w-full gap-1 q-mt-xs'):
                                        for item in rss_items:
                                            with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 3px solid #f59e0b;'):
                                                ui.label(item['fonte']).classes('text-[8px] text-amber-5 font-bold')
                                                ui.label(item['titulo']).classes('text-[10px] font-bold text-white truncate')
                                else:
                                    ui.label('Sem notícias navais.').classes('text-[10px] text-grey-5 py-4 text-center w-full')

                            else:
                                with ui.column().classes('w-full gap-1 q-mt-xs'):
                                    efemerides_list = [
                                        ('11 JUN', 'Batalha Naval do Riachuelo'),
                                        ('13 DEZ', 'Dia do Marinheiro'),
                                        ('23 OUT', 'Dia do Aviador Naval')
                                    ]
                                    for dia_ef, tit_ef in efemerides_list:
                                        with ui.row().classes('w-full justify-between items-center bg-black/20 px-2 py-0.5 rounded text-[10px] border border-white/5'):
                                            ui.label(tit_ef).classes('text-white text-[9px] font-semibold truncate max-w-[170px]')
                                            ui.label(dia_ef).classes('text-amber-4 font-mono text-[8px] font-bold')

            # ── LETREIRO DIGITAL CORRIDO (Ticker Marquee) no Rodapé ──
            bulletin_ticker_text = "⚓ MONITOR SISGAB COMSOC: Central de Operações de Comunicação Social. Acompanhe agendas de cobertura e inventário de material de forma tática.  "
            if 'boletins' in locals() and boletins:
                bulletin_ticker_text += " | ".join([f"📢 {b['titulo']}: {b['conteudo'][:120]}" for b in boletins])

            with ui.row().classes('w-full q-py-xs bg-black/60 border border-cyan-500/20 rounded-md q-mt-auto items-center no-wrap'):
                ui.label('ÚLTIMAS NOTÍCIAS').classes('bg-cyan-500 text-black text-[10px] font-black q-px-sm q-py-xs rounded-sm shrink-0 q-mr-sm tracking-wider')
                with ui.row().classes('marquee-container flex-grow'):
                    ui.label(bulletin_ticker_text).classes('marquee-content text-xs text-white')

        render_tv_dashboard()
        # Auto-refresh do painel a cada 15 segundos para rotação do Carrossel e atualização de pautas
        ui.timer(15.0, render_tv_dashboard.refresh)
