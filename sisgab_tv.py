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
            
            # Relógio Digital Gigante
            with ui.column().classes('items-end gap-0'):
                nonlocal_time = ui.label('').style('font-size: 1.8rem; font-weight: 900; color: #ffffff; line-height: 1;')
                nonlocal_date = ui.label('').style('font-size: 0.75rem; color: #a1a1aa; font-weight: bold; letter-spacing: 1.5px;')
                
                def update_clock():
                    nonlocal_time.text = datetime.now().strftime('%H:%M:%S')
                    nonlocal_date.text = datetime.now().strftime('%d DE %B DE %Y').upper()
                
                ui.timer(1.0, update_clock)
                update_clock()

        # ── PAINEL PRINCIPAL REFRESHÁVEL AUTOMATICAMENTE ──
        @ui.refreshable
        def render_tv_dashboard():
            db = fresh_db()

            # 1. CARGA DE KPIS OPERACIONAIS E ESTRATÉGICOS
            total_pautas = 0
            demandas_pendentes = 0
            demandas_ajustes = 0
            eventos_24h = 0
            taxa_entregas_str = "100%"
            efetivo_pronto_str = "0 / 0"

            hoje = datetime.now().date()
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

                    res_ef = db.table('efetivo').select('id').execute()
                    tot_ef = len(res_ef.data) if res_ef.data else 0

                    res_pr = db.table('presenca_diaria').select('id, status').eq('data', hoje_str).execute()
                    if res_pr.data:
                        prontos = len([p for p in res_pr.data if str(p.get('status', '')).upper() in ('P', 'MA', 'MT')])
                        efetivo_pronto_str = f"{prontos}/{tot_ef}"
                    else:
                        efetivo_pronto_str = f"{tot_ef}/{tot_ef}"
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

            # ── BLOCO 1: PAINEL DE KPIs OPERACIONAIS (6 CARDS TÁTICOS) ──
            with ui.row().classes('w-full gap-2 justify-between items-center q-mt-xs flex-wrap'):
                # KPI 1: Pautas Aprovadas
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('camera_alt', color='cyan-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PAUTAS ATIVAS').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(total_pautas)).classes('text-lg font-black text-white')
                
                # KPI 2: Pendente Análise
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('hourglass_top', color='amber-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PENDENTE ANÁLISE').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(demandas_pendentes)).classes('text-lg font-black text-amber-4')

                # KPI 3: Em Ajuste
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('build_circle', color='orange-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('EM AJUSTE').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(demandas_ajustes)).classes('text-lg font-black text-orange-4')

                # KPI 4: Prontidão 24 Horas
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('bolt', color='yellow-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('PRONTIDÃO 24H').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(str(eventos_24h)).classes('text-lg font-black text-yellow-4')

                # KPI 5: Taxa de Entrega
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('task_alt', color='green-5', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('TAXA ENTREGAS').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(taxa_entregas_str).classes('text-lg font-black text-green-4')

                # KPI 6: Efetivo no Pronto
                with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-3 justify-center').style('background: rgba(10,15,30,0.4); min-width: 140px;'):
                    ui.icon('shield', color='teal-4', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label('EFETIVO NO PRONTO').classes('text-[9px] text-grey-5 font-bold tracking-wider')
                        ui.label(efetivo_pronto_str).classes('text-lg font-black text-teal-3')

            # ── SELO HIGHLIGHT: COBERTURA EM ANDAMENTO AGORA ──
            agora_dt = datetime.now()
            pauta_ao_vivo = None
            if db:
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
                                    if -30 <= diff_mins <= 120:
                                        pauta_ao_vivo = p_live
                                        break
                                except Exception:
                                    pass
                except Exception as live_err:
                    print(f"[TV LIVE HIGHLIGHT ERR] {live_err}")

            if pauta_ao_vivo:
                with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl border border-red-500/50 flex-row items-center justify-between no-wrap animate-pulse q-mb-xs').style('background: rgba(239,68,68,0.15);'):
                    with ui.row().classes('items-center gap-2'):
                        ui.badge('🔴 EM COBERTURA AGORA', color='red-10').classes('text-xs font-black tracking-wider q-px-sm')
                        ui.label(pauta_ao_vivo.get('titulo_evento', '')).classes('text-xs font-bold text-white truncate max-w-[450px]')
                    with ui.row().classes('items-center gap-3 text-[11px] text-grey-3 font-semibold'):
                        ui.label(f"📍 {pauta_ao_vivo.get('local_evento', 'Gabinete')}")
                        ui.label(f"🕒 {pauta_ao_vivo.get('hora_evento', '')}")
                        ui.label(f"👤 Solicitante: {pauta_ao_vivo.get('solicitante_nome', 'COMSOC')}")

            # ── GRIDS PRINCIPAIS DO MONITOR ──
            with ui.grid(columns=1).classes('w-full gap-4 flex-grow gt-xs').style('grid-template-columns: 1.2fr 1fr 1fr; margin-top: 6px;'):
                
                # COLUNA 1: QUADRO DE FLUXO DE PAUTAS (CALENDÁRIO DINÂMICO & KANBAN)
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
                                'kanban': 'Quadro Kanban'
                            }, 
                            value=view_state['active'],
                            on_change=on_view_change
                        ).props('dark dense options-dense outlined').style('font-size: 10px; width: 110px;')

                    pautas = []
                    if db:
                        try:
                            res_c = db.table('demandas_comunicacao').select('*').execute()
                            if res_c.data:
                                pautas = [d for d in res_c.data if str(d.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas', 'pendente', 'pendentes')]
                        except Exception as e:
                            print(f"[TV CALENDAR DB ERR] {e}")

                    if not pautas:
                        with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('calendar_today', size='2.5rem')
                            ui.label('Sem pautas registradas.').classes('text-xs')
                    else:
                        hoje_dt = datetime.now()
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
                                with ui.column().classes('w-full gap-2'):
                                    for p, p_dt in pautas_filtradas:
                                        dia_semana_lbl = p_dt.strftime('%a').upper()
                                        dia_num = p_dt.strftime('%d/%m')
                                        st_val = str(p.get('status', '')).strip().lower()
                                        is_pend = st_val in ('pendente', 'pendentes')
                                        prio = p.get('prioridade', 'normal')
                                        cat_lbl = p.get('categoria_demanda', 'audiovisual').replace('_', ' ').title()
                                        prod_lbl = p.get('produto_especifico') or 'Cobertura'

                                        if prio == 'altissima':
                                            border_col = "#ef4444"
                                            prio_lbl = "ALTÍSSIMA"
                                        elif prio == 'alta':
                                            border_col = "#f97316"
                                            prio_lbl = "ALTA"
                                        else:
                                            border_col = "#00e5ff" if not is_pend else "#eab308"
                                            prio_lbl = "NORMAL"

                                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg transition-all').style(
                                            f'background: rgba(255,255,255,0.02); border-left: 4px solid {border_col}; border-top: 1px solid rgba(255,255,255,0.05);'
                                        ):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                with ui.row().classes('items-center gap-2 no-wrap'):
                                                    ui.label(f"{dia_semana_lbl} {dia_num}").classes('text-xs font-black text-cyan font-mono').style('min-width: 75px;')
                                                    ui.label(p.get('titulo_evento', 'Sem Título')).classes('text-xs font-bold text-white truncate max-w-[180px]')
                                                
                                                if is_pend:
                                                    ui.badge('PENDENTE').props('color=amber text-color=black').classes('text-[9px] font-bold')
                                                else:
                                                    ui.badge('APROVADA').props('color=cyan text-color=black').classes('text-[9px] font-bold')

                                            with ui.row().classes('w-full justify-between items-center q-mt-xs text-[10px] text-grey-4'):
                                                ui.label(f"🕒 {p.get('hora_evento', '09:00')} | 📍 {p.get('local_evento', 'Gabinete')}").classes('truncate max-w-[200px]')
                                                ui.label(f"📦 {cat_lbl} ({prod_lbl})").classes('text-grey-5 text-[9px]')
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
                                with ui.column().classes('w-full gap-2 max-h-[300px] overflow-y-auto q-pr-xs'):
                                    for p, p_dt in pautas_filtradas:
                                        dia_num = p_dt.strftime('%d/%m')
                                        st_val = str(p.get('status', '')).strip().lower()
                                        status_color = 'text-red' if st_val in ('pendente', 'pendentes') else 'text-cyan'
                                        with ui.row().classes('w-full items-center justify-between border-b border-white/5 py-1 text-xs'):
                                            ui.label(f"📅 {dia_num} - {p.get('titulo_evento', 'Sem Título')}").classes('text-white font-bold truncate max-w-[210px]')
                                            ui.label(st_val.upper()).classes(f'text-[8px] font-bold shrink-0 {status_color}')
                            else:
                                with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                                    ui.icon('calendar_today', size='2.5rem')
                                    ui.label('Sem pautas para este mês.').classes('text-xs')

                        else:
                            # Visualização Kanban
                            col_pend = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('pendente', 'pendentes')][:3]
                            col_aprov = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas')][:3]
                            
                            with ui.row().classes('w-full gap-2 items-stretch'):
                                with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                    ui.label('🔴 ANÁLISE').classes('text-[9px] font-black text-red-4 text-center w-full tracking-wider q-mb-xs')
                                    for p in col_pend:
                                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(255,0,0,0.05); border: 1px solid rgba(255,0,0,0.15);'):
                                            ui.label(p.get('titulo_evento', 'Sem Título')).classes('text-[9.5px] font-bold text-white truncate')
                                            ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[8px] text-grey-4')
                                    if not col_pend:
                                        ui.label('Fila Limpa').classes('text-[8px] text-grey-6 text-center w-full py-4')

                                with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                    ui.label('🟢 APROVADO').classes('text-[9px] font-black text-cyan-4 text-center w-full tracking-wider q-mb-xs')
                                    for p in col_aprov:
                                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.15);'):
                                            ui.label(p.get('titulo_evento', 'Sem Título')).classes('text-[9.5px] font-bold text-white truncate')
                                            ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[8px] text-grey-4')
                                    if not col_aprov:
                                        ui.label('Sem pautas').classes('text-[8px] text-grey-6 text-center w-full py-4')

                # COLUNA 2: ESCALA DE SERVIÇO DIÁRIA & ANIVERSARIANTES
                with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                    with ui.row().classes('w-full items-center gap-2 q-mb-md'):
                        ui.icon('shield', color='orange-5', size='sm')
                        ui.label('ESCALA DE SERVIÇO E OPERAÇÕES').classes('text-sm font-bold text-white tracking-wider')
                    
                    escala = {}
                    aniversariantes = []
                    if db:
                        try:
                            hoje_str = datetime.now().strftime('%Y-%m-%d')
                            res_esc = db.table('escala_diaria').select('*').eq('data', hoje_str).execute()
                            if res_esc.data:
                                escala = res_esc.data[0]
                            
                            res_ef = db.table('efetivo').select('nome_guerra', 'posto_grad', 'data_nascimento').execute()
                            if res_ef.data:
                                mes_atual = datetime.now().month
                                for e in res_ef.data:
                                    birth = e.get('data_nascimento')
                                    if birth:
                                        try:
                                            b_dt = datetime.strptime(str(birth), '%Y-%m-%d')
                                            if b_dt.month == mes_atual:
                                                aniversariantes.append({
                                                    'nome': f"{e.get('posto_grad') or ''} {e.get('nome_guerra', '')}".upper(),
                                                    'dia': b_dt.day
                                                })
                                        except Exception:
                                            pass
                                aniversariantes.sort(key=lambda x: x['dia'])
                        except Exception as e:
                            print(f"[TV ESCALA & NIVER ERR] {e}")

                    with ui.column().classes('w-full gap-2 q-mb-md'):
                        ui.label('🛡️ SERVIÇO DIÁRIO COMSOC').classes('text-[10px] text-grey-5 font-bold tracking-wider')
                        
                        esc_rows = [
                            ('SUPERVISOR', escala.get('supervisor_dia', '1º TEN CALAÇA')),
                            ('FOTÓGRAFO', escala.get('inspetor_dia', 'SG SILVA')),
                            ('CINEGRAFISTA', escala.get('oficial_dia', 'CB COSTA')),
                            ('MÍDIAS SOCIAIS', escala.get('auxiliar_dia', 'AL AMANDA'))
                        ]
                        
                        for label, name in esc_rows:
                            with ui.row().classes('w-full justify-between items-center bg-black/10 py-1 px-2 rounded border border-white/5 text-xs'):
                                ui.label(label).classes('text-grey-4 font-semibold')
                                ui.label(name).classes('text-white font-bold')

                    ui.separator().style('background-color: rgba(255, 255, 255, 0.05);')
                    
                    with ui.column().classes('w-full gap-1 q-mt-xs'):
                        ui.label('🎂 ANIVERSARIANTES DO SETOR').classes('text-[10px] text-grey-5 font-bold tracking-wider q-mb-xs')
                        
                        if aniversariantes:
                            for n in aniversariantes[:3]:
                                with ui.row().classes('w-full items-center justify-between text-xs'):
                                    ui.label(n['nome']).classes('text-white font-bold truncate max-w-[190px]')
                                    ui.label(f"Dia {n['dia']}").classes('text-amber-5 font-mono text-[10px]')
                        else:
                            mock_niver = [
                                {'nome': 'SO ALMEIDA', 'dia': 18},
                                {'nome': 'SGT CALAÇA', 'dia': 22}
                            ]
                            for n in mock_niver:
                                with ui.row().classes('w-full items-center justify-between text-xs'):
                                    ui.label(n['nome']).classes('text-white font-bold')
                                    ui.label(f"Dia {n['dia']}").classes('text-amber-5 font-mono text-[10px]')

                # COLUNA 3: MODO CARROSSEL DE INFORMATIVOS & EFEMÉRIDES MARÍTIMAS
                slide_idx = (int(datetime.now().timestamp() // 15)) % 3
                slide_headers = [
                    ('announcement', '📢 BOLETINS & AVISOS COMSOC'),
                    ('anchor', '⚓ NOTÍCIAS DO SETOR NAVAL'),
                    ('event', '🎂 EFEMÉRIDES MARÍTIMAS')
                ]
                icon_name, title_lbl = slide_headers[slide_idx]

                with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60 flex-col justify-between').style('background: rgba(10,15,30,0.45);'):
                    with ui.column().classes('w-full gap-2'):
                        with ui.row().classes('w-full items-center justify-between q-mb-xs'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon(icon_name, color='cyan-5', size='sm')
                                ui.label(title_lbl).classes('text-xs font-bold text-white tracking-wider')
                            ui.badge(f"PAINEL {slide_idx+1}/3", color='cyan-9').classes('text-[8px] font-mono')

                        if slide_idx == 0:
                            boletins = []
                            if db:
                                try:
                                    res = db.table('comsoc_noticias').select('*').order('data', desc=True).limit(3).execute()
                                    boletins = res.data if res.data else []
                                except Exception as e:
                                    print(f"[TV BOLETINS ERR] {e}")
                                    
                            if boletins:
                                with ui.column().classes('w-full gap-2 q-mt-xs'):
                                    for b in boletins:
                                        data_noticia = str(b.get('data', ''))
                                        try:
                                            data_noticia = datetime.strptime(data_noticia[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                                        except Exception:
                                            pass
                                            
                                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 3px solid #00e5ff;'):
                                            ui.label(b.get('titulo', '')).classes('text-xs font-bold text-cyan')
                                            ui.label(str(b.get('conteudo', ''))[:90] + "...").classes('text-[10px] text-grey-4 q-mt-xs')
                                            with ui.row().classes('w-full justify-between items-center text-[8px] text-grey-5 q-mt-xs'):
                                                ui.label(f"✍️ {b.get('autor', 'COMSOC')}")
                                                ui.label(f"📅 {data_noticia}")
                            else:
                                with ui.column().classes('w-full h-36 items-center justify-center gap-2 text-grey-5'):
                                    ui.icon('notifications_off', size='2rem')
                                    ui.label('Nenhum comunicado ativo.').classes('text-xs')

                        elif slide_idx == 1:
                            try:
                                from comsoc_noticias import fetch_rss_news
                                rss_items = fetch_rss_news()[:3]
                            except Exception:
                                rss_items = []
                            
                            if rss_items:
                                with ui.column().classes('w-full gap-2 q-mt-xs'):
                                    for item in rss_items:
                                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 3px solid #f59e0b;'):
                                            ui.label(item['fonte']).classes('text-[9px] text-amber-5 font-bold')
                                            ui.label(item['titulo']).classes('text-xs font-bold text-white leading-tight q-mt-xs')
                                            ui.label(item['data']).classes('text-[8px] text-grey-5 q-mt-xs')
                            else:
                                with ui.column().classes('w-full h-36 items-center justify-center gap-2 text-grey-5'):
                                    ui.icon('rss_feed', size='2rem')
                                    ui.label('Notícias do Setor Naval indisponíveis.').classes('text-xs')

                        else:
                            with ui.column().classes('w-full gap-2 q-mt-xs'):
                                ui.label('⚓ DESTAQUES DA MARINHA DO BRASIL').classes('text-[9px] font-bold text-cyan-4 tracking-wider')
                                efemerides_list = [
                                    ('11 JUN', 'Batalha Naval do Riachuelo (Data Magna)'),
                                    ('13 DEZ', 'Dia do Marinheiro (Patrono Tamandaré)'),
                                    ('23 OUT', 'Dia do Aviador Naval'),
                                    ('16 NOV', 'Dia da Amazônia Azul')
                                ]
                                for dia_ef, tit_ef in efemerides_list:
                                    with ui.row().classes('w-full justify-between items-center bg-black/20 px-2 py-1 rounded text-xs border border-white/5'):
                                        ui.label(tit_ef).classes('text-white text-[10px] font-semibold truncate max-w-[200px]')
                                        ui.label(dia_ef).classes('text-amber-4 font-mono text-[9px] font-bold')

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
