# sisgab_tv.py
import os
from datetime import datetime, timedelta
from nicegui import ui, app
import theme
from database import get_db_connection
from logo_base64 import LOGO_BASE64

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
    ):        # ── CABEÇALHO TÁTICO (Fixo) ──
        with ui.row().classes('w-full justify-between items-center q-pb-xs border-b border-cyan-500/40').style('background: rgba(5, 10, 25, 0.4); backdrop-filter: blur(10px); border-radius: 12px; padding: 8px 16px;'):
            with ui.row().classes('items-center gap-4'):
                # Logo Oficial da Tela Inicial do SisGAB
                ui.image(LOGO_BASE64).style('height: 55px; width: auto; object-fit: contain; filter: drop-shadow(0 0 14px rgba(197, 160, 89, 0.9));')
                with ui.column().classes('gap-0'):
                    ui.label('SISGAB - MONITOR').style('font-size: 1.8rem; font-weight: 900; color: #ffffff; letter-spacing: 3px; line-height: 1.1;')
                    ui.label('CENTRAL DE OPERAÇÕES E COMUNICAÇÃO SOCIAL').style('font-size: 0.8rem; color: #00e5ff; font-weight: 800; letter-spacing: 1.5px;')
            
            with ui.row().classes('items-center gap-3'):
                def open_tv_missao_rapida_dialog():
                    # Busca robusta do efetivo com fallback em ambas as tabelas (efetivo e users)
                    efetivo_options = {}
                    try:
                        db = fresh_db()
                        if db:
                            # 1. Efetivo
                            ef_res = db.table('efetivo').select('id, nome_guerra, posto_grad, email').execute()
                            if ef_res.data:
                                for m in ef_res.data:
                                    m_id = str(m.get('id') or m.get('nome_guerra'))
                                    pg = m.get('posto_grad') or ''
                                    ng = m.get('nome_guerra') or ''
                                    lbl = f"{pg} {ng}".strip()
                                    if lbl:
                                        efetivo_options[m_id] = lbl
                            # 2. Users (fallback / complemento)
                            u_res = db.table('users').select('id, nome, username').execute()
                            if u_res.data:
                                for u in u_res.data:
                                    u_id = str(u.get('id'))
                                    if u_id not in efetivo_options:
                                        nm = u.get('nome') or u.get('username') or ''
                                        if nm:
                                            efetivo_options[u_id] = nm
                    except Exception as e_ef:
                        print(f"[TV EFETIVO ERR] {e_ef}")

                    if not efetivo_options:
                        efetivo_options = {'1': 'SG CALAÇA (Admin)', '2': 'EQUIPE COMSOC / GABINETE'}

                    # Fuso Horário Oficial de Brasília (GMT-3)
                    now_br = datetime.utcnow() - timedelta(hours=3)
                    now_date = now_br.strftime('%Y-%m-%d')
                    now_time = now_br.strftime('%H:%M')

                    with ui.dialog() as diag, ui.card().classes('w-[980px] max-w-[96vw] q-pa-md bg-slate-900 border border-deep-orange-500/50 rounded-xl').style('box-shadow: 0 0 45px rgba(255, 87, 34, 0.25);'):
                        with ui.column().classes('w-full gap-3'):
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label('⚡ LANÇAR MISSÃO RÁPIDA (PAUTA / DEMANDA)').classes('text-deep-orange font-black text-md cyber-title')
                                ui.icon('assignment_late', size='1.5rem', color='deep-orange-5')
                            ui.separator().style('background-color: rgba(255, 87, 34, 0.3);')

                            # LAYOUT DE 2 COLUNAS ESPAÇOSAS (APROVEITAMENTO TOTAL DO ESPAÇO)
                            with ui.row().classes('w-full gap-4 items-stretch wrap-mobile'):
                                # --- COLUNA 1: DETALHES DO SERVIÇO & PAUTA ---
                                with ui.column().classes('flex-1 w-full gap-2.5'):
                                    ui.label('📌 Detalhes do Serviço').classes('text-xs font-bold text-amber-4 cyber-title')

                                    # Categoria com Multiseleção
                                    cat_select = ui.select(
                                        options={
                                            'audiovisual': '📷 Cobertura Fotográfica & Vídeo',
                                            'prensa': '🎥 Imprensa & Cobertura de Autoridades',
                                            'design': '🎨 Design / Arte / Placa JADE',
                                            'cerimonial': '📜 Cerimonial & Solenidade'
                                        },
                                        value=['audiovisual'],
                                        multiple=True,
                                        label='Categoria(s) da Demanda (Multiseleção)'
                                    ).props('dark outlined dense use-chips w-full')

                                    tit_inp = ui.input('Título Geral da Tarefa / Solenidade', placeholder='Ex: Cobertura Fotográfica da Passagem de Comando').props('dark outlined dense w-full')

                                    with ui.row().classes('w-full gap-2'):
                                        sol_inp = ui.input('Solicitante', value='CGCFN / GABINETE').props('dark outlined dense').classes('w-1/2')
                                        setor_inp = ui.input('Setor / OM', value='CGCFN').props('dark outlined dense').classes('w-1/2')

                                    with ui.row().classes('w-full gap-2'):
                                        ramal_inp = ui.input('Contato / Ramal', value='Interno').props('dark outlined dense').classes('w-1/2')
                                        prio_select = ui.select(
                                            options={'urgente': '🔥 Alta / Urgente', 'normal': '🟢 Normal', 'prontidao': '⚡ Prontidão 24h'},
                                            value='urgente',
                                            label='Prioridade'
                                        ).props('dark outlined dense').classes('w-1/2')

                                    with ui.row().classes('w-full gap-2'):
                                        data_inp = ui.input('Prazo / Data do Evento (GMT-3)', value=now_date).props('dark outlined dense type=date').classes('w-1/2')
                                        hora_inp = ui.input('Horário de Saída', value=now_time).props('dark outlined dense type=time').classes('w-1/2')

                                    sigilo_chk = ui.checkbox('🔒 Pauta Sigilosa / Reservada (Gabinete)', value=False).props('dark dense').classes('text-xs text-amber-3')

                                # --- COLUNA 2: OPERACIONAL & EXECUÇÃO (SEM CAUTELA - ESPAÇO EXPANDIDO) ---
                                with ui.column().classes('flex-1 w-full gap-2.5'):
                                    ui.label('⚙️ Operacional & Execução').classes('text-xs font-bold text-cyan cyber-title')

                                    # Militar Responsável com Multiseleção
                                    militar_select = ui.select(
                                        options=efetivo_options,
                                        multiple=True,
                                        value=[],
                                        label='Designar Militar(es) Responsável(is) (Multiseleção)'
                                    ).props('dark outlined dense use-chips w-full')

                                    loc_inp = ui.input('Local do Evento / Ponto de Encontro', value='Gabinete / COMSOC').props('dark outlined dense w-full')

                                    obs_inp = ui.textarea(
                                        'Briefing / Instruções de Execução',
                                        placeholder='Digite aqui orientações de fardamento, pauta, roteiro, cobertura e detalhes da autoridade...'
                                    ).props('dark outlined dense w-full rows=6').classes('w-full flex-grow')

                            # BOTÕES DE AÇÃO NA BASE
                            def salvar_missao(aprovar_direto=True):
                                t = tit_inp.value.strip()
                                if not t:
                                    ui.notify('Digite o título da missão.', color='warning')
                                    return
                                try:
                                    db = fresh_db()
                                    if db:
                                        militares_sel = militar_select.value or []
                                        militares_nomes = [efetivo_options[m_id] for m_id in militares_sel if m_id in efetivo_options]
                                        militares_str = ", ".join(militares_nomes) if militares_nomes else 'COMSOC / Monitor TV'

                                        cats_sel = cat_select.value or ['audiovisual']
                                        cat_primary = cats_sel[0] if isinstance(cats_sel, list) and cats_sel else 'audiovisual'

                                        prio_prefix = "🔒 " if sigilo_chk.value else ("🔥 " if prio_select.value == 'urgente' else "⚡ ")
                                        titulo_final = f"{prio_prefix}{t.upper()}"
                                        status_val = 'aprovada' if aprovar_direto else 'pendente'

                                        db.table('demandas_comunicacao').insert({
                                            'titulo_evento': titulo_final,
                                            'solicitante_nome': sol_inp.value or 'MONITOR TV',
                                            'contato': ramal_inp.value or 'Interno',
                                            'setor': setor_inp.value or 'Gabinete',
                                            'data_evento': data_inp.value or now_date,
                                            'hora_evento': hora_inp.value or now_time,
                                            'local_evento': loc_inp.value or 'Gabinete',
                                            'status': status_val,
                                            'categoria_demanda': cat_primary,
                                            'responsavel_id': militares_sel[0] if militares_sel else None,
                                            'observacoes': f"Equipe: {militares_str} | Briefing: {obs_inp.value}"
                                        }).execute()

                                        # Enviar notificação Telegram
                                        try:
                                            from notifications_manager import notify_telegram
                                            msg_tg = (
                                                f"🚨 *NOVA DEMANDA RÁPIDA LANÇADA NA TV*\n\n"
                                                f"📌 *Título:* {t}\n"
                                                f"📂 *Categorias:* {', '.join(cats_sel).upper()}\n"
                                                f"📍 *Local:* {loc_inp.value}\n"
                                                f"⏰ *Horário (GMT-3):* {hora_inp.value} ({data_inp.value})\n"
                                                f"🎖️ *Equipe:* {militares_str}\n"
                                                f"📝 *Briefing:* {obs_inp.value or 'Sem briefing'}\n"
                                                f"🔒 *Sigilo:* {'SIM (Reservada)' if sigilo_chk.value else 'NÃO'}\n\n"
                                                f"⚡ *Status:* {status_val.upper()}"
                                            )
                                            notify_telegram(msg_tg, "demandas")
                                        except Exception as tg_err:
                                            print(f"[TV TG ERR] {tg_err}")

                                        ui.notify(f"⚡ Missão '{t}' cadastrada como {status_val.upper()}!", color='positive')
                                        diag.close()
                                        render_tv_dashboard.refresh()
                                except Exception as e:
                                    ui.notify(f'Erro ao lançar missão: {e}', color='negative')

                            with ui.row().classes('w-full justify-between items-center q-mt-sm wrap gap-2'):
                                ui.button('Cancelar', on_click=diag.close).props('flat color=grey text-color=white')
                                with ui.row().classes('gap-2'):
                                    ui.button('⭐ SALVAR & APROVAR DIRETO (QUARTEL)', on_click=lambda: salvar_missao(True)).props('unelevated color=amber-9 text-color=black bold icon=star')
                                    ui.button('➢ ENVIAR PARA AVALIAÇÃO', on_click=lambda: salvar_missao(False)).props('unelevated color=cyan text-color=black bold icon=send')
                    diag.open()

                def toggle_fullscreen():
                    ui.run_javascript('''
                        if (!document.fullscreenElement) {
                            document.documentElement.requestFullscreen().catch(err => console.log(err));
                        } else {
                            if (document.exitFullscreen) {
                                document.exitFullscreen();
                            }
                        }
                    ''')

                ui.button('⚡ Missão Rápida', on_click=open_tv_missao_rapida_dialog).props('unelevated color=deep-orange-9 text-color=white dense bold icon=flash_on').classes('text-xs q-px-sm')
                ui.button('🪪 Placas JADE', on_click=lambda: ui.navigate.to('/comsoc_assentos')).props('outline color=indigo-4 text-color=white dense bold icon=badge').classes('text-xs q-px-sm')
                ui.button('🏠 Dashboard', on_click=lambda: ui.navigate.to('/')).props('outline color=cyan text-color=white dense bold icon=dashboard').classes('text-xs q-px-sm')
                ui.button('📺 Fullscreen', on_click=toggle_fullscreen).props('outline color=amber text-color=white dense bold icon=fullscreen').classes('text-xs q-px-sm')
                
                def toggle_alerts(val):
                    app.storage.user['tv_alerts_enabled'] = val
                    render_tv_dashboard.refresh()

                alerts_enabled = app.storage.user.get('tv_alerts_enabled', True)
                ui.checkbox('Card Alertas', value=alerts_enabled, on_change=lambda e: toggle_alerts(e.value)).props('dark dense').classes('text-xs text-white q-ml-sm')

            # Relógio Digital Gigante (Horário de Brasília GMT-3) - Aumentado +20%
            with ui.column().classes('items-end gap-0'):
                nonlocal_time = ui.label('').style('font-size: 2.2rem; font-weight: 900; color: #ffffff; line-height: 1; filter: drop-shadow(0 0 10px rgba(0,229,255,0.4));')
                nonlocal_date = ui.label('').style('font-size: 0.85rem; color: #a1a1aa; font-weight: bold; letter-spacing: 2px;')
                
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

            # ── BLOCO 1: PAINEL DE KPIs OPERACIONAIS (AMPLIADO, GLASSMORPHISM TRANSLÚCIDO) ──
            with ui.row().classes('w-full gap-3 justify-between items-stretch q-mt-xs flex-nowrap overflow-x-auto'):
                card_kpi_style = 'background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(12px); border: 1px solid rgba(0, 229, 255, 0.3); border-radius: 12px; min-height: 85px;'
                
                # KPI 1: Pautas Aprovadas
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('camera_alt', color='cyan-4', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('PAUTAS ATIVAS').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(str(total_pautas)).classes('text-2xl font-black text-white')
                
                # KPI 2: Pendente Análise
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('hourglass_top', color='amber-4', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('PENDENTE ANÁLISE').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(str(demandas_pendentes)).classes('text-2xl font-black text-amber-4')

                # KPI 3: Em Ajuste
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('build_circle', color='orange-4', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('EM AJUSTE').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(str(demandas_ajustes)).classes('text-2xl font-black text-orange-4')

                # KPI 4: Prontidão 24 Horas
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('bolt', color='yellow-4', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('PRONTIDÃO 24H').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(str(eventos_24h)).classes('text-2xl font-black text-yellow-4')

                # KPI 5: Missões Rápidas Hoje
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('flash_on', color='deep-orange-4', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('MISSÕES RÁPIDAS').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(str(missoes_rapidas_cnt)).classes('text-2xl font-black text-deep-orange-4')

                # KPI 6: Placas JADE (Solenidade)
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('badge', color='indigo-3', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('PLACAS JADE').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(f"{jade_printed}/{jade_total} IMP.").classes('text-xl font-black text-indigo-3')

                # KPI 7: Efetivo no Pronto
                with ui.card().classes('flex-1 q-pa-md flex-row items-center gap-3 justify-center shadow-lg').style(card_kpi_style):
                    ui.icon('shield', color='teal-3', size='md')
                    with ui.column().classes('gap-0'):
                        ui.label('EFETIVO PRONTO').classes('text-xs text-grey-4 font-bold tracking-wider')
                        ui.label(efetivo_pronto_str).classes('text-2xl font-black text-teal-3')

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
                pautas_alertas.sort(key=lambda x: (0 if x.get('alert_type') == 'LIVE' else 1, x.get('hora_evento', '')))
                alert_idx = (int(datetime.utcnow().timestamp() // 15)) % len(pautas_alertas)
                pauta_alerta = pautas_alertas[alert_idx]
                
                is_live = pauta_alerta.get('alert_type') == 'LIVE'
                badge_text = '🔴 EM COBERTURA AGORA' if is_live else '⏳ PRÓXIMO EVENTO'
                card_style = 'background: rgba(239,68,68,0.2); backdrop-filter: blur(10px); border: 1px solid rgba(239,68,68,0.6);' if is_live else 'background: rgba(0,229,255,0.15); backdrop-filter: blur(10px); border: 1px solid rgba(0,229,255,0.4);'
                badge_color = 'red-10' if is_live else 'cyan-9'
                
                hr_txt = str(pauta_alerta.get('hora_evento', '09:00'))[:5]
                enc_id = pauta_alerta.get('encarregado_id')
                enc_nome = get_militar_nome(enc_id)

                with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl flex-row items-center justify-between no-wrap q-mb-xs').style(f'{card_style} {"animate-pulse" if is_live else ""};'):
                    with ui.row().classes('items-center gap-3 col-grow truncate'):
                        ui.badge(badge_text, color=badge_color).classes('text-sm font-black tracking-wider q-px-md')
                        ui.label(pauta_alerta.get('titulo_evento', 'Sem Título').upper()).classes('text-sm font-black text-white truncate max-w-[500px]')
                    with ui.row().classes('items-center gap-3 text-xs text-slate-100 font-bold shrink-0'):
                        ui.label(f"🕒 {hr_txt}").classes('text-amber-4')
                        ui.label(f"📍 {pauta_alerta.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4')
                        if enc_nome:
                            ui.badge(f"🎖️ {enc_nome.upper()}", color='green-9').classes('text-xs font-bold')
                        ui.label(f"👤 {pauta_alerta.get('solicitante_nome', 'COMSOC').upper()}").classes('text-grey-3 text-xs')

            # ── GRIDS PRINCIPAIS DO MONITOR (COLUNAS REORDENADAS & GLASSMORPHISM TRANSLÚCIDO) ──
            card_col_style = 'background: rgba(10, 16, 32, 0.45); backdrop-filter: blur(14px); border: 1px solid rgba(0, 229, 255, 0.25); border-radius: 16px;'

            with ui.grid(columns=1).classes('w-full gap-4 flex-grow gt-xs items-stretch').style('grid-template-columns: 1.2fr 1.1fr 1fr; margin-top: 6px; min-height: calc(100vh - 230px);'):
                
                # pautas gerais reutilizadas nas colunas
                pautas = []
                if db:
                    try:
                        res_c = db.table('demandas_comunicacao').select('*').execute()
                        if res_c.data:
                            pautas = res_c.data
                    except Exception as e:
                        print(f"[TV CALENDAR DB ERR] {e}")

                # =========================================================================
                # COLUNA 1 (ESQUERDA - PRIORIDADE): PAUTAS HOJE & AMANHÃ (PRONTIDÃO 48H)
                # =========================================================================
                with ui.card().classes('q-pa-md no-shadow flex-col justify-between').style(card_col_style):
                    with ui.column().classes('w-full gap-2'):
                        with ui.row().classes('w-full items-center justify-between q-mb-xs border-b border-cyan-500/30 q-pb-xs'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('today', color='amber-4', size='sm')
                                ui.label('PAUTAS: HOJE & AMANHÃ').classes('text-base font-black text-white tracking-wider')
                            ui.badge('PRONTIDÃO 48H', color='amber-9').classes('text-xs font-mono font-bold')

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
                            pautas_hoje_amanha.sort(key=lambda x: (x[1] if isinstance(x, (tuple, list)) and len(x) > 1 else '', x[0].get('hora_evento', '') if isinstance(x, (tuple, list)) and len(x) > 0 and isinstance(x[0], dict) else ''))

                        if pautas_hoje_amanha:
                            with ui.column().classes('w-full gap-2 max-h-[580px] overflow-y-auto q-pr-xs'):
                                for item in pautas_hoje_amanha:
                                    if not (isinstance(item, (tuple, list)) and len(item) == 2):
                                        continue
                                    p, p_dt = item[0], item[1]
                                    is_hoje = (p_dt == hoje_obj)
                                    tag_dia = "HOJE" if is_hoje else "AMANHÃ"
                                    tag_bg = "rgba(245,158,11,0.25)" if is_hoje else "rgba(0,229,255,0.2)"
                                    border_tag = "#f59e0b" if is_hoje else "#00e5ff"
                                    st_val = str(p.get('status', '')).strip().lower()

                                    with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl').style(
                                        f'background: {tag_bg}; border: 1.5px solid {border_tag}; backdrop-filter: blur(8px);'
                                    ):
                                        hr_txt = str(p.get('hora_evento', '09:00'))[:5]
                                        enc_id = p.get('encarregado_id')
                                        enc_nome = get_militar_nome(enc_id)

                                        with ui.row().classes('w-full justify-between items-start no-wrap gap-2'):
                                            with ui.row().classes('items-start gap-2 col-grow'):
                                                ui.badge(tag_dia, color='amber-9' if is_hoje else 'cyan-9').classes('text-xs font-black shrink-0 q-mt-xs q-px-sm')
                                                ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-sm font-black text-white leading-tight break-words col-grow')
                                            
                                            if st_val in ('pendente', 'pendentes'):
                                                ui.badge('PENDENTE', color='amber-9').classes('text-xs font-bold shrink-0 q-mt-xs')
                                            else:
                                                ui.badge('APROVADA', color='green-9').classes('text-xs font-bold shrink-0 q-mt-xs')

                                        with ui.row().classes('w-full justify-between items-center q-mt-xs text-xs text-slate-200'):
                                            with ui.row().classes('items-center gap-2 wrap col-grow'):
                                                ui.label(f"🕒 {hr_txt}").classes('text-amber-4 font-black')
                                                ui.label('|').classes('text-white/20')
                                                ui.label(f"📍 {p.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4 font-bold')
                                                if enc_nome:
                                                    ui.label('|').classes('text-white/20')
                                                    ui.label(f"🎖️ {enc_nome.upper()}").classes('text-green-4 font-black')
                                            ui.label(f"👤 {p.get('solicitante_nome', 'CGCFN').upper()}").classes('text-grey-3 text-xs shrink-0 font-semibold')
                        else:
                            with ui.column().classes('w-full h-64 items-center justify-center gap-2 text-grey-4'):
                                ui.icon('event_available', size='3rem', color='cyan-4')
                                ui.label('Nenhuma pauta agendada para hoje ou amanhã.').classes('text-sm font-bold')

                # =========================================================================
                # COLUNA 2 (CENTRO): CRONOGRAMA DE PRODUÇÃO & FILTRO MULTI-PAINEL
                # =========================================================================
                with ui.card().classes('q-pa-md no-shadow flex-col justify-between').style(card_col_style):
                    with ui.column().classes('w-full gap-2'):
                        with ui.row().classes('w-full items-center justify-between q-mb-xs border-b border-cyan-500/30 q-pb-xs'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('calendar_month', color='cyan-4', size='sm')
                                ui.label('CRONOGRAMA DE PRODUÇÃO').classes('text-base font-black text-white tracking-wider')
                            
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
                            ).props('dark dense options-dense outlined').style('font-size: 11px; width: 145px;')

                        if not pautas:
                            with ui.column().classes('w-full h-64 items-center justify-center gap-2 text-grey-4'):
                                ui.icon('calendar_today', size='3rem', color='cyan-4')
                                ui.label('Sem pautas registradas.').classes('text-sm font-bold')
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
                                pautas_filtradas.sort(key=lambda x: x[1] if isinstance(x, (tuple, list)) and len(x) > 1 else datetime.min)

                                if pautas_filtradas:
                                    with ui.column().classes('w-full gap-2 max-h-[580px] overflow-y-auto q-pr-xs'):
                                        for item in pautas_filtradas:
                                            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                                                continue
                                            p, p_dt = item[0], item[1]
                                            dia_semana_lbl = p_dt.strftime('%a').upper()
                                            dia_num = p_dt.strftime('%d/%m')
                                            st_val = str(p.get('status', '')).strip().lower()
                                            is_pend = st_val in ('pendente', 'pendentes')
                                            prio = p.get('prioridade', 'normal')

                                            border_col = "#ef4444" if prio == 'altissima' else "#f97316" if prio == 'alta' else "#00e5ff" if not is_pend else "#eab308"

                                            with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl transition-all').style(
                                                f'background: rgba(255,255,255,0.03); border-left: 5px solid {border_col}; border-top: 1px solid rgba(255,255,255,0.08);'
                                            ):
                                                dia_semana_trad = translate_day(dia_semana_lbl)
                                                hr_txt = str(p.get('hora_evento', '09:00'))[:5]
                                                enc_id = p.get('encarregado_id')
                                                enc_nome = get_militar_nome(enc_id)

                                                with ui.row().classes('w-full justify-between items-start no-wrap gap-2'):
                                                    with ui.row().classes('items-start gap-2 col-grow'):
                                                        ui.label(f"{dia_semana_trad} {dia_num}").classes('text-xs font-black text-cyan font-mono shrink-0 q-mt-xs').style('min-width: 80px;')
                                                        ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-sm font-bold text-white leading-tight break-words col-grow')
                                                    
                                                    if is_pend:
                                                        ui.badge('PENDENTE', color='amber-9').classes('text-xs font-bold shrink-0 q-mt-xs')
                                                    else:
                                                        ui.badge('APROVADA', color='green-9').classes('text-xs font-bold shrink-0 q-mt-xs')

                                                with ui.row().classes('w-full justify-between items-center q-mt-xs text-xs text-slate-200'):
                                                    with ui.row().classes('items-center gap-2 wrap col-grow'):
                                                        ui.label(f"🕒 {hr_txt}").classes('text-amber-4 font-bold')
                                                        ui.label('|').classes('text-white/20')
                                                        ui.label(f"📍 {p.get('local_evento', 'Gabinete').upper()}").classes('text-cyan-4 font-bold')
                                                        if enc_nome:
                                                            ui.label('|').classes('text-white/20')
                                                            ui.label(f"🎖️ {enc_nome.upper()}").classes('text-green-4 font-black')
                                                    ui.label(f"👤 {p.get('solicitante_nome', 'CGCFN').upper()}").classes('text-grey-3 text-xs shrink-0 font-semibold')
                                else:
                                    with ui.column().classes('w-full h-64 items-center justify-center gap-2 text-grey-4'):
                                        ui.icon('event_busy', size='3rem', color='cyan-4')
                                        ui.label('Sem pautas para esta semana.').classes('text-sm font-bold')

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
                                pautas_filtradas.sort(key=lambda x: x[1] if isinstance(x, (tuple, list)) and len(x) > 1 else datetime.min)

                                if pautas_filtradas:
                                    with ui.column().classes('w-full gap-2 max-h-[580px] overflow-y-auto q-pr-xs'):
                                        for item in pautas_filtradas:
                                            if not (isinstance(item, (tuple, list)) and len(item) == 2):
                                                continue
                                            p, p_dt = item[0], item[1]
                                            dia_num = p_dt.strftime('%d/%m')
                                            st_val = str(p.get('status', '')).strip().lower()
                                            status_color = 'text-red' if st_val in ('pendente', 'pendentes') else 'text-cyan'
                                            with ui.row().classes('w-full items-center justify-between border-b border-white/10 py-1.5 text-xs'):
                                                ui.label(f"📅 {dia_num} - {p.get('titulo_evento', 'Sem Título').upper()}").classes('text-white font-bold truncate max-w-[240px]')
                                                ui.label(st_val.upper()).classes(f'text-xs font-bold shrink-0 {status_color}')
                                else:
                                    with ui.column().classes('w-full h-64 items-center justify-center gap-2 text-grey-4'):
                                        ui.icon('calendar_today', size='3rem', color='cyan-4')
                                        ui.label('Sem pautas para este mês.').classes('text-sm font-bold')

                            elif active_view == 'kanban':
                                col_pend = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('pendente', 'pendentes')][:5]
                                col_aprov = [p for p in pautas if str(p.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas')][:5]
                                
                                with ui.row().classes('w-full gap-2 items-stretch'):
                                    with ui.column().classes('col gap-1.5').style('background: rgba(255,255,255,0.02); border-radius: 8px; padding: 6px;'):
                                        ui.label('🔴 ANÁLISE').classes('text-xs font-black text-red-4 text-center w-full tracking-wider q-mb-xs')
                                        for p in col_pend:
                                            with ui.card().classes('w-full q-pa-xs no-shadow rounded-md').style('background: rgba(255,0,0,0.1); border: 1px solid rgba(255,0,0,0.25);'):
                                                ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-xs font-bold text-white truncate')
                                                ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[10px] text-grey-3 font-mono')
                                        if not col_pend:
                                            ui.label('Fila Limpa').classes('text-xs text-grey-5 text-center w-full py-4')

                                    with ui.column().classes('col gap-1.5').style('background: rgba(255,255,255,0.02); border-radius: 8px; padding: 6px;'):
                                        ui.label('🟢 APROVADO').classes('text-xs font-black text-cyan-4 text-center w-full tracking-wider q-mb-xs')
                                        for p in col_aprov:
                                            with ui.card().classes('w-full q-pa-xs no-shadow rounded-md').style('background: rgba(0,229,255,0.1); border: 1px solid rgba(0,229,255,0.25);'):
                                                ui.label(p.get('titulo_evento', 'Sem Título').upper()).classes('text-xs font-bold text-white truncate')
                                                ui.label(str(p.get('data_evento', ''))[5:]).classes('text-[10px] text-grey-3 font-mono')
                                        if not col_aprov:
                                            ui.label('Sem pautas').classes('text-xs text-grey-5 text-center w-full py-4')

                            else:
                                with ui.column().classes('w-full gap-2 max-h-[580px] overflow-y-auto q-pr-xs'):
                                    for p in pautas:
                                        st_val = str(p.get('status', '')).strip().lower()
                                        st_badge_color = 'green' if st_val in ('aprovada', 'aprovado') else 'grey' if st_val == 'concluida' else 'amber'
                                        data_txt = str(p.get('data_evento', 'N/I'))
                                        try:
                                            data_txt = datetime.strptime(data_txt[:10], '%Y-%m-%d').strftime('%d/%m')
                                        except Exception:
                                            pass

                                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg').style('background: rgba(255,255,255,0.03); border-left: 3px solid rgba(0,229,255,0.4);'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                ui.label(f"{data_txt} - {p.get('titulo_evento', 'Sem Título').upper()}").classes('text-xs font-bold text-white truncate max-w-[220px]')
                                                ui.badge(st_val.upper()).props(f'color={st_badge_color}').classes('text-[9px]')

                # =========================================================================
                # COLUNA 3 (DIREITA): PLACAS JADE PENDENTES & BOLETINS COMSOC (TRANSLÚCIDO)
                # =========================================================================
                with ui.column().classes('w-full gap-3 flex-grow q-pa-none'):
                    
                    # ALERTA TÁTICO DE PLACAS JADE PENDENTES
                    count_jade_pending = 0
                    if db:
                        try:
                            res_j = db.table('jade_convidados').select('*').eq('status_placa', 'pendente').execute()
                            count_jade_pending = len(res_j.data) if res_j.data else 0
                        except Exception:
                            pass
                            
                    if count_jade_pending > 0:
                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl border border-amber-500/60 flex-row items-center justify-between no-wrap animate-pulse').style('background: rgba(245,158,11,0.25); backdrop-filter: blur(10px);'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('print', color='amber-3', size='sm')
                                ui.label('PLACAS JADE PENDENTES:').classes('text-xs font-black text-amber-3 tracking-wider')
                            ui.badge(f'{count_jade_pending} PLACAS', color='amber-10').classes('text-xs font-black q-px-sm')

                    # MODO CARROSSEL DE INFORMATIVOS & EFEMÉRIDES (GLASSMORPHISM TRANSLÚCIDO)
                    slide_idx = (int(datetime.utcnow().timestamp() // 15)) % 3
                    slide_headers = [
                        ('announcement', '📢 BOLETINS COMSOC'),
                        ('anchor', '⚓ SETOR NAVAL'),
                        ('event', '🎂 EFEMÉRIDES MB')
                    ]
                    header_item = slide_headers[slide_idx] if 0 <= slide_idx < len(slide_headers) else ('announcement', '📢 BOLETINS COMSOC')
                    icon_name, title_lbl = header_item[0], header_item[1]

                    with ui.card().classes('w-full q-pa-md no-shadow flex-col justify-between flex-grow').style(card_col_style):
                        with ui.column().classes('w-full gap-2'):
                            with ui.row().classes('w-full items-center justify-between q-mb-xs border-b border-cyan-500/30 q-pb-xs'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon(icon_name, color='cyan-4', size='sm')
                                    ui.label(title_lbl).classes('text-sm font-black text-white tracking-wider')
                                ui.badge(f"{slide_idx+1}/3", color='cyan-9').classes('text-xs font-mono font-bold')

                            if slide_idx == 0:
                                boletins = []
                                if db:
                                    try:
                                        res = db.table('comsoc_noticias').select('*').order('data', desc=True).limit(3).execute()
                                        boletins = res.data if res.data else []
                                    except Exception:
                                        pass
                                        
                                if boletins:
                                    with ui.column().classes('w-full gap-2 q-mt-xs'):
                                        for b in boletins:
                                            with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl').style('background: rgba(255,255,255,0.03); border-left: 4px solid #00e5ff;'):
                                                ui.label(b.get('titulo', '')).classes('text-xs font-bold text-cyan truncate')
                                                ui.label(str(b.get('conteudo', ''))[:90] + "...").classes('text-[11px] text-grey-3 q-mt-xs leading-relaxed')
                                else:
                                    ui.label('Nenhum boletim ativo.').classes('text-xs text-grey-4 py-6 text-center w-full font-bold')

                            elif slide_idx == 1:
                                try:
                                    from comsoc_noticias import fetch_rss_news
                                    rss_items = fetch_rss_news()[:3]
                                except Exception:
                                    rss_items = []
                                
                                if rss_items:
                                    with ui.column().classes('w-full gap-2 q-mt-xs'):
                                        for item in rss_items:
                                            with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl').style('background: rgba(255,255,255,0.03); border-left: 4px solid #f59e0b;'):
                                                ui.label(item['fonte']).classes('text-[10px] text-amber-4 font-bold')
                                                ui.label(item['titulo']).classes('text-xs font-bold text-white truncate')
                                else:
                                    ui.label('Sem notícias navais.').classes('text-xs text-grey-4 py-6 text-center w-full font-bold')

                            else:
                                with ui.column().classes('w-full gap-2 q-mt-xs'):
                                    efemerides_list = [
                                        ('11 JUN', 'Batalha Naval do Riachuelo'),
                                        ('13 DEZ', 'Dia do Marinheiro'),
                                        ('23 OUT', 'Dia do Aviador Naval')
                                    ]
                                    for item_ef in efemerides_list:
                                        if not (isinstance(item_ef, (tuple, list)) and len(item_ef) == 2):
                                            continue
                                        dia_ef, tit_ef = item_ef[0], item_ef[1]
                                        with ui.row().classes('w-full justify-between items-center bg-black/30 px-3 py-1.5 rounded-lg text-xs border border-white/10'):
                                            ui.label(tit_ef).classes('text-white text-xs font-bold truncate max-w-[200px]')
                                            ui.label(dia_ef).classes('text-amber-4 font-mono text-xs font-bold')

            # ── LETREIRO DIGITAL CORRIDO (Ticker Marquee) no Rodapé ──
            bulletin_ticker_text = "⚓ MONITOR SISGAB COMSOC: Central de Operações de Comunicação Social. Acompanhe agendas de cobertura e inventário de material de forma tática.  "
            if 'boletins' in locals() and boletins:
                bulletin_ticker_text += " | ".join([f"📢 {b['titulo']}: {b['conteudo'][:120]}" for b in boletins])

            with ui.row().classes('w-full q-py-xs bg-black/70 border border-cyan-500/30 rounded-lg q-mt-auto items-center no-wrap').style('backdrop-filter: blur(10px);'):
                ui.label('ÚLTIMAS NOTÍCIAS').classes('bg-cyan-500 text-black text-xs font-black q-px-sm q-py-xs rounded-sm shrink-0 q-mr-sm tracking-wider')
                with ui.row().classes('marquee-container flex-grow'):
                    ui.label(bulletin_ticker_text).classes('marquee-content text-xs text-white')

        render_tv_dashboard()
        # Auto-refresh do painel a cada 15 segundos para rotação do Carrossel e atualização de pautas
        ui.timer(15.0, render_tv_dashboard.refresh)

