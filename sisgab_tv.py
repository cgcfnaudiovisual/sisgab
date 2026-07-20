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

    db = get_db_connection()
    
    # ── CARGA DE DADOS DOS INDICADORES (KPIs) ──
    total_pautas = 0
    total_cautelas = 0
    demandas_pendentes = 0
    operador_destaque = "Nenhum"
    
    if db:
        try:
            # 1. Total pautas aprovadas do mês
            hoje = datetime.now()
            inicio_mes = hoje.replace(day=1).strftime('%Y-%m-%d')
            fim_mes = (hoje.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            fim_mes_str = fim_mes.strftime('%Y-%m-%d')
            
            res_p = db.table('demandas_comunicacao').select('id, status, solicitante_nome').execute()
            if res_p.data:
                total_pautas = len([d for d in res_p.data if d['status'] == 'aprovada'])
                demandas_pendentes = len([d for d in res_p.data if d['status'] == 'pendente'])
                
                # Encontra operador mais ativo
                solicitantes = [d['solicitante_nome'].upper() for d in res_p.data if d.get('solicitante_nome')]
                if solicitantes:
                    operador_destaque = max(set(solicitantes), key=solicitantes.count)
            
            # 2. Cautelas ativas
            res_c = db.table('cautela_equipamentos').select('id').eq('status', 'retirado').execute()
            if res_c.data:
                total_cautelas = len(res_c.data)
                
        except Exception as e:
            print(f"[TV KPIs ERR] {e}")

    # Layout de tela cheia para a TV
    with ui.column().classes('w-full min-h-screen q-pa-md gap-4 overflow-hidden').style(
        'background: radial-gradient(circle, #0c1020 0%, #05070e 100%); font-family: "Outfit", sans-serif;'
    ):
        # ── CABEÇALHO TÁTICO ──
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

        # ── BLOCO 1: PAINEL DE KPIs ──
        with ui.row().classes('w-full gap-4 justify-between items-center q-mt-sm'):
            # KPI 1: Pautas Aprovadas
            with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-4 justify-center').style('background: rgba(10,15,30,0.4);'):
                ui.icon('camera_alt', color='cyan-5', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('PAUTAS ATIVAS').classes('text-[10px] text-grey-5 font-bold tracking-wider')
                    ui.label(str(total_pautas)).classes('text-xl font-black text-white')
            
            # KPI 2: Materiais Cautelados
            with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-4 justify-center').style('background: rgba(10,15,30,0.4);'):
                ui.icon('battery_charging_full', color='orange-5', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('MATERIAL FORA').classes('text-[10px] text-grey-5 font-bold tracking-wider')
                    ui.label(str(total_cautelas)).classes('text-xl font-black text-white')

            # KPI 3: Demandas Pendentes
            with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-4 justify-center').style('background: rgba(10,15,30,0.4);'):
                ui.icon('hourglass_empty', color='red-400', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('PENDENTE ANÁLISE').classes('text-[10px] text-grey-5 font-bold tracking-wider')
                    ui.label(str(demandas_pendentes)).classes('text-xl font-black text-white')

            # KPI 4: Operador Destaque
            with ui.card().classes('col q-pa-sm rounded-lg border border-cyan-950/60 flex-row items-center gap-4 justify-center').style('background: rgba(10,15,30,0.4);'):
                ui.icon('person', color='green-400', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('DESTAQUE COMSOC').classes('text-[10px] text-grey-5 font-bold tracking-wider')
                    ui.label(operador_destaque).classes('text-sm font-black text-white truncate')

        # ── GRIDS PRINCIPAIS DO MONITOR ──
        # ── GRIDS PRINCIPAIS DO MONITOR ──
        with ui.grid(columns=1).classes('w-full gap-4 flex-grow gt-xs').style('grid-template-columns: 1.2fr 1fr 1fr; margin-top: 10px;'):
            
            # COLUNA 1: QUADRO DE FLUXO DE PAUTAS (CALENDÁRIO DINÂMICO & KANBAN)
            with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                with ui.row().classes('w-full items-center justify-between q-mb-md no-wrap'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('calendar_month', color='cyan-5', size='sm')
                        ui.label('CRONOGRAMA DE PRODUÇÃO').classes('text-sm font-bold text-white tracking-wider')
                    
                    # Seletor dinâmico de visualização na TV (Semana/Mês)
                    view_select = ui.select(
                        {
                            'semana': 'Esta Semana',
                            'mes': 'Este Mês',
                            'kanban': 'Quadro Kanban'
                        }, 
                        value='semana'
                    ).props('dark dense options-dense outlined').style('font-size: 10px; width: 110px;')

                @ui.refreshable
                def render_calendar_view():
                    active_view = view_select.value
                    pautas = []
                    if db:
                        try:
                            res_c = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'pendente']).execute()
                            pautas = res_c.data if res_c.data else []
                        except Exception as e:
                            print(f"[TV CALENDAR DB ERR] {e}")

                    if not pautas:
                        with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('calendar_today', size='2.5rem')
                            ui.label('Sem pautas registradas.').classes('text-xs')
                        return

                    hoje_dt = datetime.now()

                    if active_view == 'semana':
                        # Filtra pautas dos próximos 7 dias
                        limite_semana = hoje_dt + timedelta(days=7)
                        pautas_filtradas = []
                        for p in pautas:
                            try:
                                p_dt = datetime.strptime(p['data_evento'], '%Y-%m-%d')
                                if hoje_dt.date() <= p_dt.date() <= limite_semana.date():
                                    pautas_filtradas.append((p, p_dt))
                            except:
                                pass
                        
                        pautas_filtradas.sort(key=lambda x: x[1])

                        if pautas_filtradas:
                            with ui.column().classes('w-full gap-2'):
                                for p, p_dt in pautas_filtradas:
                                    dia_semana_lbl = p_dt.strftime('%a').upper()
                                    dia_num = p_dt.strftime('%d/%m')
                                    is_pend = p['status'] == 'pendente'
                                    border_col = "#ef4444" if is_pend else "#00e5ff"
                                    badge_lbl = "PENDENTE" if is_pend else "APROVADA"
                                    badge_color = "red-5" if is_pend else "cyan-9"

                                    with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style(f'background: rgba(255,255,255,0.02); border-left: 4px solid {border_col};'):
                                        with ui.row().classes('w-full justify-between items-center no-wrap'):
                                            with ui.row().classes('items-center gap-2'):
                                                ui.label(f"[{dia_semana_lbl} {dia_num}]").classes('text-[11px] font-bold text-cyan-4')
                                                ui.label(p['titulo_evento']).classes('text-xs font-bold text-white truncate max-w-[140px]')
                                            ui.badge(badge_lbl).props(f"color={badge_color} dense").classes('text-[8px] q-px-sm')
                                        with ui.row().classes('w-full justify-between items-center text-[10px] text-grey-4 q-mt-xs'):
                                            ui.label(f"🕒 {p['hora_evento']} | 📍 {p['local_evento'] or 'Gabinete'}")
                                            ui.label(f"👤 {p['solicitante_nome']}").classes('text-[9px] truncate max-w-[100px]')
                        else:
                            with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                                ui.icon('event_busy', size='2.5rem')
                                ui.label('Sem pautas para esta semana.').classes('text-xs')

                    elif active_view == 'mes':
                        # Filtra pautas deste mês
                        mes_atual = hoje_dt.month
                        pautas_filtradas = []
                        for p in pautas:
                            try:
                                p_dt = datetime.strptime(p['data_evento'], '%Y-%m-%d')
                                if p_dt.month == mes_atual:
                                    pautas_filtradas.append((p, p_dt))
                            except:
                                pass
                        
                        pautas_filtradas.sort(key=lambda x: x[1])

                        if pautas_filtradas:
                            with ui.column().classes('w-full gap-2 max-h-[300px] overflow-y-auto q-pr-xs'):
                                for p, p_dt in pautas_filtradas:
                                    dia_num = p_dt.strftime('%d/%m')
                                    with ui.row().classes('w-full items-center justify-between border-b border-white/5 py-1 text-xs'):
                                        ui.label(f"📅 {dia_num} - {p['titulo_evento']}").classes('text-white font-bold truncate max-w-[210px]')
                                        status_color = 'text-red' if p['status'] == 'pendente' else 'text-cyan'
                                        ui.label(p['status'].upper()).classes(f'text-[8px] font-bold shrink-0 {status_color}')
                        else:
                            with ui.column().classes('w-full h-48 items-center justify-center gap-2 text-grey-5'):
                                ui.icon('calendar_today', size='2.5rem')
                                ui.label('Sem pautas para este mês.').classes('text-xs')

                    else:
                        # Visualização Kanban de Pautas
                        col_pend = [p for p in pautas if p['status'] == 'pendente'][:3]
                        col_aprov = [p for p in pautas if p['status'] == 'aprovada'][:3]
                        
                        with ui.row().classes('w-full gap-2 items-stretch'):
                            # Coluna PENDENTES
                            with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                ui.label('🔴 ANÁLISE').classes('text-[9px] font-black text-red-4 text-center w-full tracking-wider q-mb-xs')
                                for p in col_pend:
                                    with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(255,0,0,0.05); border: 1px solid rgba(255,0,0,0.15);'):
                                        ui.label(p['titulo_evento']).classes('text-[9.5px] font-bold text-white truncate')
                                        ui.label(p['data_evento'][5:]).classes('text-[8px] text-grey-4')
                                if not col_pend:
                                    ui.label('Fila Limpa').classes('text-[8px] text-grey-6 text-center w-full py-4')

                            # Coluna APROVADAS
                            with ui.column().classes('col gap-1').style('background: rgba(255,255,255,0.01); border-radius: 4px; padding: 4px;'):
                                ui.label('🟢 APROVADO').classes('text-[9px] font-black text-cyan-4 text-center w-full tracking-wider q-mb-xs')
                                for p in col_aprov:
                                    with ui.card().classes('w-full q-pa-xs no-shadow rounded-sm').style('background: rgba(0,229,255,0.05); border: 1px solid rgba(0,229,255,0.15);'):
                                        ui.label(p['titulo_evento']).classes('text-[9.5px] font-bold text-white truncate')
                                        ui.label(p['data_evento'][5:]).classes('text-[8px] text-grey-4')
                                if not col_aprov:
                                    ui.label('Sem pautas').classes('text-[8px] text-grey-6 text-center w-full py-4')

                view_select.on('change', render_calendar_view.refresh)
                render_calendar_view()

            # COLUNA 2: ESCALA DE SERVIÇO DIÁRIA & ANIVERSARIANTES NAVEGAÇÃO
            with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                with ui.row().classes('w-full items-center gap-2 q-mb-md'):
                    ui.icon('shield', color='orange-5', size='sm')
                    ui.label('ESCALA DE SERVIÇO E OPERAÇÕES').classes('text-sm font-bold text-white tracking-wider')
                
                escala = {}
                aniversariantes = []
                efemerides = []
                if db:
                    try:
                        # 1. Busca escala diária
                        hoje_str = datetime.now().strftime('%Y-%m-%d')
                        res_esc = db.table('escala_diaria').select('*').eq('data', hoje_str).execute()
                        if res_esc.data:
                            escala = res_esc.data[0]
                        
                        # 2. Busca aniversariantes do mês (Efetivo)
                        res_ef = db.table('efetivo').select('nome_guerra', 'posto_grad', 'data_nascimento').execute()
                        if res_ef.data:
                            mes_atual = datetime.now().month
                            for e in res_ef.data:
                                birth = e.get('data_nascimento')
                                if birth:
                                    try:
                                        b_dt = datetime.strptime(birth, '%Y-%m-%d')
                                        if b_dt.month == mes_atual:
                                            aniversariantes.append({
                                                'nome': f"{e.get('posto_grad') or ''} {e['nome_guerra']}".upper(),
                                                'dia': b_dt.day
                                            })
                                    except:
                                        pass
                            aniversariantes.sort(key=lambda x: x['dia'])
                    except Exception as e:
                        print(f"[TV ESCALA & NIVER ERR] {e}")

                # Lista de Escala
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

                # Aniversariantes e Efemérides
                ui.separator().style('background-color: rgba(255, 255, 255, 0.05);')
                
                with ui.column().classes('w-full gap-1 q-mt-xs'):
                    ui.label('🎂 ANIVERSARIANTES DO SETOR').classes('text-[10px] text-grey-5 font-bold tracking-wider q-mb-xs')
                    
                    if aniversariantes:
                        for n in aniversariantes[:3]:
                            with ui.row().classes('w-full items-center justify-between text-xs'):
                                ui.label(n['nome']).classes('text-white font-bold truncate max-w-[190px]')
                                ui.label(f"Dia {n['dia']}").classes('text-amber-5 font-mono text-[10px]')
                    else:
                        # Fallback/Mock para demonstração visual
                        mock_niver = [
                            {'nome': 'SO ALMEIDA', 'dia': 18},
                            {'nome': 'SGT CALAÇA', 'dia': 22}
                        ]
                        for n in mock_niver:
                            with ui.row().classes('w-full items-center justify-between text-xs'):
                                ui.label(n['nome']).classes('text-white font-bold')
                                ui.label(f"Dia {n['dia']}").classes('text-amber-5 font-mono text-[10px]')

            # COLUNA 3: COMUNICADOS & ÚLTIMAS NOTÍCIAS
            with ui.card().classes('q-pa-md no-shadow rounded-xl border border-cyan-950/60').style('background: rgba(10,15,30,0.45);'):
                with ui.row().classes('w-full items-center gap-2 q-mb-md'):
                    ui.icon('announcement', color='cyan-5', size='sm')
                    ui.label('COMUNICADOS E BOLETINS').classes('text-sm font-bold text-white tracking-wider')
                
                boletins = []
                if db:
                    try:
                        res = db.table('comsoc_noticias').select('*').order('data', desc=True).limit(3).execute()
                        boletins = res.data if res.data else []
                    except Exception as e:
                        print(f"[TV BOLETINS ERR] {e}")
                        
                if boletins:
                    with ui.column().classes('w-full gap-3'):
                        for b in boletins:
                            # Formata data
                            data_noticia = b.get('data', '')
                            try:
                                data_noticia = datetime.strptime(data_noticia[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                            except:
                                pass
                                
                            with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border-left: 4px solid #ef4444;'):
                                ui.label(b['titulo']).classes('text-xs font-bold text-white')
                                ui.label(b['conteudo'][:100] + "...").classes('text-[10px] text-grey-4 q-mt-xs')
                                with ui.row().classes('w-full justify-between items-center text-[8px] text-grey-5 q-mt-xs'):
                                    ui.label(f"✍️ Por: {b.get('autor', 'COMSOC')}")
                                    ui.label(f"📅 {data_noticia}")
                else:
                    with ui.column().classes('w-full h-40 items-center justify-center gap-2 text-grey-5'):
                        ui.icon('notifications_off', size='2.5rem')
                        ui.label('Nenhum comunicado ativo.').classes('text-xs')

        # ── LETREIRO DIGITAL CORRIDO (Ticker Marquee) no Rodapé ──
        bulletin_ticker_text = "⚓ MONITOR SISGAB COMSOC: Central de Operações de Comunicação Social. Acompanhe agendas de cobertura e inventário de material de forma tática.  "
        if boletins:
            bulletin_ticker_text += " | ".join([f"📢 {b['titulo']}: {b['conteudo'][:120]}" for b in boletins])
            

        with ui.row().classes('w-full q-py-xs bg-black/60 border border-cyan-500/20 rounded-md q-mt-auto items-center no-wrap'):
            ui.label('ÚLTIMAS NOTÍCIAS').classes('bg-cyan-500 text-black text-[10px] font-black q-px-sm q-py-xs rounded-sm shrink-0 q-mr-sm tracking-wider')
            with ui.row().classes('marquee-container flex-grow'):
                ui.label(bulletin_ticker_text).classes('marquee-content text-xs text-white')
