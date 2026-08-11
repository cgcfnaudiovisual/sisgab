# modules/comsoc_historico.py
import io
import json
from datetime import datetime
import pandas as pd
from nicegui import ui, app
import theme
from database import get_db_connection, get_service_db_connection

THEME = theme.colors

def render_page():
    ui.label('📜 HISTÓRICO, ARQUIVO & RELATÓRIOS COMSOC').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    # Estados de filtro de busca para o Acervo
    filter_state = {
        'termo': '',
        'local': '',
        'autoridade': '',
        'tipo_cobertura': 'todos',
        'data_inicio': '',
        'data_fim': '',
        'categoria': 'todos'
    }

    with ui.tabs().classes('w-full text-cyan q-mb-md') as tabs:
        tab_acervo = ui.tab('Acervo de Eventos & Fotos', icon='photo_library')
        tab_relatorio = ui.tab('Relatório & Carga do Efetivo', icon='analytics')

    with ui.tab_panels(tabs, value=tab_acervo).classes('w-full bg-transparent p-0'):

        # =========================================================================
        # ABA 1: ACERVO DE EVENTOS & GALERIAS DE FOTOS
        # =========================================================================
        with ui.tab_panel(tab_acervo).classes('p-0'):

            # Painel de Filtros Superiores
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
            ):
                with ui.row().classes('w-full items-center gap-3 wrap justify-start'):
                    txt_busca = ui.input(
                        label='Buscar Palavra-chave (Título, Autoridade, etc.)', 
                        placeholder='Ex: Deputado, Visita, Fortaleza...'
                    ).props('dark outlined dense').classes('grow').style('min-width: 200px;')
                    
                    txt_local = ui.input(
                        label='Localidade / Setor', 
                        placeholder='Ex: Fortaleza, Gabinete...'
                    ).props('dark outlined dense').classes('w-44').style('min-width: 140px;')
                    
                    dt_inicio = ui.input(label='Data Início').props('type=date dark outlined dense').classes('w-32').style('min-width: 130px;')
                    
                    dt_fim = ui.input(label='Data Fim').props('type=date dark outlined dense').classes('w-32').style('min-width: 130px;')
                    
                    sel_cob = ui.select(
                        {
                            'todos': 'Todas Coberturas',
                            'foto': 'Fotografia',
                            'video': 'Vídeo / Filme',
                            'redes': 'Mídias / Texto'
                        },
                        value='todos',
                        label='Escopo de Cobertura'
                    ).props('dark outlined dense option-dark').classes('w-44').style('min-width: 140px;')

                    sel_cat = ui.select(
                        {
                            'todos': '📋 Todas',
                            'audiovisual': '📸 Audiovisual',
                            'design_arte': '🎨 Design',
                            'impressos_albuns': '📕 Impressos',
                            'redacao_textos': '✍️ Redação',
                            'brindes_lembrancas': '🎁 Brindes',
                            'suporte_evento': '📦 Suporte',
                            'outra_tarefa': '⚡ Outras'
                        },
                        value='todos',
                        label='Categoria'
                    ).props('dark outlined dense option-dark').classes('w-44').style('min-width: 140px;')

                    def aplicar_filtros():
                        filter_state['termo'] = txt_busca.value or ''
                        filter_state['local'] = txt_local.value or ''
                        filter_state['tipo_cobertura'] = sel_cob.value
                        filter_state['data_inicio'] = dt_inicio.value or ''
                        filter_state['data_fim'] = dt_fim.value or ''
                        filter_state['categoria'] = sel_cat.value
                        render_event_cards.refresh()

                    ui.button(
                        'Filtrar', 
                        icon='search', 
                        on_click=aplicar_filtros
                    ).props('unelevated color=primary text-color=black bold').classes('q-px-lg cyber-glow')

            @ui.refreshable
            def render_event_cards():
                db = get_db_connection()
                pautas = []
                fotos_por_evento = {}
                
                if db:
                    try:
                        res_pautas = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'aprovado', 'concluida']).order('data_evento', desc=True).execute()
                        pautas = res_pautas.data if res_pautas.data else []
                        
                        res_photos = db.table('processed_photos').select('*').execute()
                        photos = res_photos.data if res_photos.data else []
                        
                        for p in photos:
                            ev_name = p.get('event_name')
                            if ev_name:
                                if ev_name not in fotos_por_evento:
                                    fotos_por_evento[ev_name] = []
                                fotos_por_evento[ev_name].append(p)
                    except Exception as e:
                        print(f"[HISTORICO DB ERR] {e}")

                termo = filter_state['termo'].strip().lower()
                local = filter_state['local'].strip().lower()
                autoridade = filter_state['autoridade'].strip().lower()
                tipo_cob = filter_state['tipo_cobertura']
                data_inicio = filter_state['data_inicio']
                data_fim = filter_state['data_fim']
                categoria = filter_state['categoria']
                
                pautas_filtradas = []
                for p in pautas:
                    if termo:
                        tit = str(p.get('titulo_evento', '')).lower()
                        sol = str(p.get('solicitante_nome', '')).lower()
                        setor = str(p.get('setor', '')).lower()
                        aut = str(p.get('autoridades', '')).lower()
                        prod = str(p.get('produto_especifico', '')).lower()
                        if not (termo in tit or termo in sol or termo in setor or termo in aut or termo in prod):
                            continue
                    if local and not (local in (p.get('local_evento') or '').lower()):
                        continue
                    if autoridade and not (autoridade in (p.get('autoridades') or '').lower()):
                        continue
                    if tipo_cob != 'todos':
                        try:
                            cobs = json.loads(p.get('tipo_cobertura', '[]'))
                            if tipo_cob not in cobs:
                                continue
                        except Exception:
                            continue
                    if data_inicio and p.get('data_evento', '') < data_inicio:
                        continue
                    if data_fim and p.get('data_evento', '') > data_fim:
                        continue
                    if categoria != 'todos' and p.get('categoria_demanda', '') != categoria:
                        continue
                    pautas_filtradas.append(p)

                if pautas_filtradas:
                    with ui.column().classes('w-full gap-4'):
                        for p in pautas_filtradas:
                            ev_title = p['titulo_evento']
                            fotos = fotos_por_evento.get(ev_title, [])
                            drive_link = fotos[0].get('drive_link') if fotos else None
                            
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                            ):
                                with ui.row().classes('w-full justify-between items-start no-wrap gap-4'):
                                    with ui.column().classes('gap-1 flex-grow'):
                                        with ui.row().classes('items-center gap-2 wrap'):
                                            ui.label(ev_title).classes('text-md font-bold text-white')
                                            if p.get('sigiloso') == 1:
                                                ui.badge('Sigiloso/Reservado', color='red-10').classes('text-[8px] font-bold')
                                        
                                        ui.label(f"📅 Data: {p['data_evento']} | Local: {p.get('local_evento', 'Não informado')}").classes('text-xs text-grey-4')
                                        if p.get('autoridades'):
                                            ui.label(f"👥 Autoridades: {p['autoridades']}").classes('text-xs text-amber-5 font-semibold')
                                        ui.label(f"👤 Solicitado por: {p['solicitante_nome']} ({p['setor']})").classes('text-[11px] text-grey-5')
                                        
                                        if p.get('arquivo_url') and p.get('arquivo_name'):
                                            with ui.row().classes('items-center gap-1 q-mt-xs bg-white/5 q-px-sm q-py-xs rounded border border-white/10'):
                                                ui.icon('attachment', size='1rem', color='grey-4')
                                                ui.link(
                                                    f"Baixar Anexo: {p['arquivo_name']}",
                                                    target=p['arquivo_url'],
                                                    new_tab=True
                                                ).classes('text-[10px] text-grey-3 hover:underline font-semibold')

                                    with ui.column().classes('items-end justify-start gap-2 shrink-0'):
                                        if drive_link:
                                            ui.link(
                                                '🔗 Acessar Galeria de Fotos', 
                                                target=drive_link,
                                                new_tab=True
                                            ).classes('text-xs text-cyan hover:underline font-bold bg-cyan/10 q-px-md q-py-sm rounded-lg border border-cyan/20')
                                        else:
                                            def associar_drive(evento=ev_title):
                                                with ui.dialog() as diag, ui.card().classes('w-96 q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                                                    ui.label('Associar Link do Drive').classes('text-white text-md font-bold')
                                                    link_input = ui.input('Link do Google Drive', placeholder='https://drive.google.com/...').props('dark outlined dense w-full')
                                                    
                                                    def salvar_link():
                                                        url = link_input.value.strip()
                                                        if not url:
                                                            return
                                                        conn = get_db_connection()
                                                        if conn:
                                                            try:
                                                                conn.table('processed_photos').insert({
                                                                    'event_name': evento,
                                                                    'filename': 'drive_folder_link',
                                                                    'drive_link': url,
                                                                    'criado_em': datetime.now().isoformat()
                                                                }).execute()
                                                                ui.notify('Link da galeria associado com sucesso!', color='success')
                                                                diag.close()
                                                                render_event_cards.refresh()
                                                            except Exception as err:
                                                                ui.notify(f'Erro ao salvar: {err}', color='red')
                                                    
                                                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                                        ui.button('Cancelar', on_click=diag.close).props('flat color=grey')
                                                        ui.button('Salvar', on_click=salvar_link).props('unelevated color=primary text-color=black')
                                                diag.open()

                                            ui.button(
                                                'Vincular Galeria', 
                                                icon='link',
                                                on_click=associar_drive
                                            ).props('unelevated color=grey-8 text-color=white dense').classes('text-[10px] q-px-sm')
                                        
                                        try:
                                            cobs = json.loads(p.get('tipo_cobertura', '[]'))
                                            with ui.row().classes('gap-1 q-mt-xs'):
                                                for c in cobs:
                                                    ui.badge(c.upper(), color='slate-700').classes('text-[7.5px]')
                                        except Exception:
                                            pass

                                        def ver_historico_pauta(dem_id=p['id'], titulo=p['titulo_evento']):
                                            with ui.dialog() as diag, ui.card().classes('w-[500px] q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius:12px;'):
                                                ui.label(f"📜 Linha do Tempo: {titulo}").classes('text-white text-md font-bold cyber-title q-mb-md')
                                                
                                                trams = []
                                                c_db = get_db_connection()
                                                if c_db:
                                                    try:
                                                        res_tr = c_db.table('demandas_historico_tramitacao').select('*').eq('demanda_id', dem_id).order('data_hora', desc=False).execute()
                                                        trams = res_tr.data if res_tr.data else []
                                                    except Exception as ex:
                                                        print(f"[HISTORICO DIALOG ERR] {ex}")
                                                        
                                                if trams:
                                                    with ui.column().classes('w-full gap-3 relative q-pl-md').style('border-left: 2px solid rgba(0, 229, 255, 0.15);'):
                                                        for tr in trams:
                                                            with ui.column().classes('w-full gap-0 bg-white/5 q-pa-sm rounded-lg relative'):
                                                                ui.element('div').classes('absolute').style('width:10px; height:10px; border-radius:50%; background:#00e5ff; left:-22px; top:12px; border:2px solid #0a0f1e;')
                                                                
                                                                with ui.row().classes('w-full justify-between items-center'):
                                                                    ui.label(tr['acao']).classes('text-xs font-bold text-cyan')
                                                                    ui.label(tr['data_hora'][:16].replace('T', ' ')).classes('text-[9px] text-grey-4')
                                                                ui.label(tr['parecer']).classes('text-[11px] text-white q-mt-xs')
                                                                ui.label(f"Por: {tr['usuario']}").classes('text-[9px] text-grey-5 q-mt-xs')
                                                else:
                                                    with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-5'):
                                                        ui.icon('info', size='2rem')
                                                        ui.label('Nenhum histórico registrado para este evento.').classes('text-xs')
                                                        
                                                with ui.row().classes('w-full justify-end q-mt-md'):
                                                    ui.button('Fechar', on_click=diag.close).props('flat color=grey')
                                            diag.open()

                                        ui.button(
                                            'Histórico', 
                                            icon='history_edu',
                                            on_click=lambda dem_id=p['id'], tit=p['titulo_evento']: ver_historico_pauta(dem_id, tit)
                                        ).props('flat dense color=amber-5').classes('text-[9px] q-px-sm')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('search_off', size='3rem')
                        ui.label('Nenhum evento histórico atende aos filtros atuais.').classes('text-xs')

            render_event_cards()

        # =========================================================================
        # ABA 2: RELATÓRIO DE CARGA & PRODUTIVIDADE DO EFETIVO
        # =========================================================================
        with ui.tab_panel(tab_relatorio).classes('p-0'):

            @ui.refreshable
            def render_relatorio_efetivo():
                db = get_service_db_connection() or get_db_connection()
                efetivo = []
                demandas = []
                presencas_hoje = {}
                
                hoje_str = datetime.now().strftime('%Y-%m-%d')

                if db:
                    try:
                        res_ef = db.table('efetivo').select('*').order('nome_guerra').execute()
                        efetivo = res_ef.data or []
                    except Exception as e:
                        print(f"[RELATORIO EFETIVO DB ERR] {e}")

                    try:
                        res_dem = db.table('demandas_comunicacao').select('*').execute()
                        demandas = res_dem.data or []
                    except Exception as e:
                        print(f"[RELATORIO DEMANDAS DB ERR] {e}")

                    try:
                        res_pr = db.table('presenca_diaria').select('*').eq('data', hoje_str).execute()
                        if res_pr.data:
                            presencas_hoje = {p['nome_guerra'].upper(): p.get('status', 'PENDENTE') for p in res_pr.data}
                    except Exception as e:
                        print(f"[RELATORIO PRESENCA DB ERR] {e}")

                # Processamento das estatísticas por militar
                relatorio_militar = []
                tot_concluidas_geral = 0
                tot_pendentes_geral = 0

                for militar in efetivo:
                    nome_g = str(militar.get('nome_guerra') or '').replace('None', '').strip().upper()
                    militar_id_str = str(militar.get('id', ''))
                    posto_grad = str(militar.get('posto_grad') or militar.get('posto') or '').replace('None', '').strip().upper()
                    cargo = str(militar.get('cargo_funcao') or militar.get('role') or 'Operador COMSOC').replace('None', '').strip()

                    pautas_militar = []
                    pendentes_militar = []
                    concluidas_militar = []

                    for dem in demandas:
                        enc_id = str(dem.get('encarregado_id', ''))
                        
                        target_ids = set()
                        raw_ids = dem.get('notificar_militar_ids')
                        if raw_ids:
                            try:
                                parsed = json.loads(raw_ids) if isinstance(raw_ids, str) else raw_ids
                                if isinstance(parsed, list):
                                    target_ids = {str(x) for x in parsed if str(x).isdigit()}
                            except Exception:
                                pass

                        # Verifica se o militar está individualmente vinculado à demanda
                        eh_responsavel = (
                            (militar_id_str and enc_id == militar_id_str) or
                            (militar_id_str and militar_id_str in target_ids)
                        )

                        if eh_responsavel:
                            pautas_militar.append(dem)
                            st = str(dem.get('status', '')).strip().lower()
                            if st in ('pendente', 'pendentes', 'aprovada', 'aprovado', 'ajustes'):
                                pendentes_militar.append(dem)
                            elif st in ('concluida', 'concluido', 'concluidas'):
                                concluidas_militar.append(dem)

                    st_presenca = presencas_hoje.get(nome_g, 'P')
                    
                    # Nível de carga
                    qtd_ativas = len(pendentes_militar)
                    if qtd_ativas == 0:
                        nivel_carga = 'LIVRE'
                        cor_carga = 'green'
                    elif qtd_ativas <= 2:
                        nivel_carga = 'MODERADO'
                        cor_carga = 'amber'
                    else:
                        nivel_carga = 'ALTA CARGA'
                        cor_carga = 'red'

                    tot_concluidas_geral += len(concluidas_militar)
                    tot_pendentes_geral += len(pendentes_militar)

                    relatorio_militar.append({
                        'militar': militar,
                        'nome_guerra': nome_g,
                        'posto_grad': posto_grad,
                        'cargo': cargo,
                        'presenca_hoje': st_presenca,
                        'tot_pautas': len(pautas_militar),
                        'ativas': len(pendentes_militar),
                        'concluidas': len(concluidas_militar),
                        'pautas_ativas_list': pendentes_militar,
                        'nivel_carga': nivel_carga,
                        'cor_carga': cor_carga
                    })

                # Ordena por número de pautas ativas (mais ocupados primeiro)
                relatorio_militar.sort(key=lambda x: x['ativas'], reverse=True)

                # ── CABEÇALHO COM KPIS E BOTÃO DE EXPORTAÇÃO EXCEL ──
                with ui.row().classes('w-full justify-between items-center q-mb-md wrap gap-3'):
                    with ui.row().classes('items-center gap-3 flex-wrap'):
                        ui.badge(f"👥 Efetivo Ativo: {len(efetivo)}").props('color=cyan-9 bold').classes('q-pa-xs text-xs')
                        ui.badge(f"⏳ Demandas Ativas: {tot_pendentes_geral}").props('color=amber-9 bold').classes('q-pa-xs text-xs')
                        ui.badge(f"✅ Concluídas no Total: {tot_concluidas_geral}").props('color=green-9 bold').classes('q-pa-xs text-xs')

                    def exportar_excel():
                        try:
                            export_data = []
                            for r in relatorio_militar:
                                export_data.append({
                                    'Posto/Grad': r['posto_grad'],
                                    'Nome de Guerra': r['nome_guerra'],
                                    'Cargo/Função': r['cargo'],
                                    'Presença Hoje': r['presenca_hoje'],
                                    'Pautas Ativas/Pendentes': r['ativas'],
                                    'Pautas Concluídas': r['concluidas'],
                                    'Nível de Carga': r['nivel_carga']
                                })
                            df = pd.DataFrame(export_data)
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df.to_excel(writer, sheet_name='Produtividade_COMSOC', index=False)
                            buffer.seek(0)
                            ui.download(buffer.getvalue(), f"Relatorio_Produtividade_COMSOC_{hoje_str}.xlsx")
                            ui.notify('📥 Relatório Excel gerado e baixado com sucesso!', color='positive')
                        except Exception as exp_err:
                            ui.notify(f'Erro ao exportar Excel: {exp_err}', color='negative')

                    ui.button('📥 Exportar Relatório (Excel)', icon='download',
                              on_click=exportar_excel
                    ).props('unelevated color=green text-color=white bold dense').classes('text-xs q-px-sm')

                # ── CARDS DE MILITARES E SUA CARGA DE TRABALHO ──
                if relatorio_militar:
                    with ui.column().classes('w-full gap-3'):
                        for r in relatorio_militar:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                            ):
                                with ui.row().classes('w-full justify-between items-center wrap gap-3'):
                                    # Dados do Militar
                                    with ui.row().classes('items-center gap-3'):
                                        ui.icon('person', size='2rem', color='cyan-5')
                                        with ui.column().classes('gap-0'):
                                            with ui.row().classes('items-center gap-2'):
                                                clean_pg = str(r['posto_grad'] or '').replace('None', '').strip()
                                                clean_title = f"{clean_pg} {r['nome_guerra']}".strip()
                                                ui.label(clean_title).classes('text-sm font-bold text-white')
                                                ui.badge(r['nivel_carga']).props(f"color={r['cor_carga']} bold").classes('text-[9px]')
                                            ui.label(r['cargo']).classes('text-xs text-grey-4')

                                    # Indicadores de Carga
                                    with ui.row().classes('items-center gap-3 text-xs'):
                                        with ui.column().classes('items-center gap-0'):
                                            ui.label(str(r['ativas'])).classes(f"text-lg font-black text-{r['cor_carga']}")
                                            ui.label('Ativas / Pendentes').classes('text-[9px] text-grey-4')

                                        ui.separator().props('vertical').classes('q-mx-xs')

                                        with ui.column().classes('items-center gap-0'):
                                            ui.label(str(r['concluidas'])).classes('text-lg font-black text-green-4')
                                            ui.label('Concluídas').classes('text-[9px] text-grey-4')

                                # Pautas ativas vinculadas (se houver)
                                if r['pautas_ativas_list']:
                                    with ui.column().classes('w-full q-mt-sm q-pt-xs border-t border-cyan-500/10 gap-1'):
                                        ui.label('📌 Pautas ativas sob responsabilidade:').classes('text-[10px] text-cyan font-bold')
                                        for p_ativa in r['pautas_ativas_list']:
                                            dt_ev = p_ativa.get('data_evento', '')
                                            tit_ev = p_ativa.get('titulo_evento', 'Sem Título')
                                            st_ev = p_ativa.get('status', 'pendente')
                                            with ui.row().classes('w-full items-center justify-between text-[11px] bg-black/20 q-px-sm q-py-xs rounded'):
                                                ui.label(f"• {tit_ev} ({dt_ev})").classes('text-white font-semibold truncate max-w-[70%]')
                                                ui.badge(st_ev.upper()).props('color=amber-9 dense text-color=black').classes('text-[8px]')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('group_off', size='3rem')
                        ui.label('Nenhum militar encontrado no cadastro de efetivo.').classes('text-xs')

            render_relatorio_efetivo()
