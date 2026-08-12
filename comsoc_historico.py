# modules/comsoc_historico.py
import io
import json
from datetime import datetime
import pandas as pd
from nicegui import ui, app
import theme
from database import get_db_connection, get_service_db_connection, get_demanda_drive_url
import drive_service

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
                    ).props('unelevated color=primary text-color=black bold').classes('q-px-md cyber-glow')

                    def exportar_pdf_historico():
                        try:
                            from reportlab.lib.pagesizes import A4
                            from reportlab.lib import colors
                            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

                            buffer = io.BytesIO()
                            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                            styles = getSampleStyleSheet()

                            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#091326'), alignment=1, spaceAfter=4)
                            sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#475569'), alignment=1, spaceAfter=12)
                            hdr_style = ParagraphStyle('HdrStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)
                            cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9)
                            cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9)

                            elements = [
                                Paragraph("<b>MARINHA DO BRASIL</b><br/>COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS<br/>ASSESSORIA DE COMUNICAÇÃO SOCIAL", title_style),
                                Paragraph(f"RELATÓRIO HISTÓRICO DE COBERTURAS & ACERVO — {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub_style),
                                Spacer(1, 5)
                            ]

                            tbl_data = [[
                                Paragraph("Data", hdr_style),
                                Paragraph("Evento / Pauta", hdr_style),
                                Paragraph("Local / Setor", hdr_style),
                                Paragraph("Solicitante / Autoridades", hdr_style),
                                Paragraph("Status Drive", hdr_style)
                            ]]

                            p_list = current_pautas_filtradas if 'current_pautas_filtradas' in locals() and current_pautas_filtradas else pautas
                            for p_item in p_list[:60]:
                                dt_str = str(p_item.get('data_evento', ''))
                                tit_str = str(p_item.get('titulo_evento', ''))
                                loc_str = str(p_item.get('local_evento', 'Quartel'))
                                sol_str = f"Sol: {p_item.get('solicitante_nome','')}<br/>Aut: {p_item.get('autoridades','')}"
                                d_url = get_demanda_drive_url(p_item)
                                st_drive = "COBERTURA OK" if d_url else "SEM DRIVE"

                                tbl_data.append([
                                    Paragraph(dt_str, cell_bold),
                                    Paragraph(f"<b>{tit_str}</b>", cell_style),
                                    Paragraph(loc_str, cell_style),
                                    Paragraph(sol_str, cell_style),
                                    Paragraph(st_drive, cell_bold)
                                ])

                            t = Table(tbl_data, colWidths=[55, 170, 95, 140, 75])
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#091326')),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
                            ]))
                            elements.append(t)
                            doc.build(elements)
                            buffer.seek(0)

                            ui.download(buffer.getvalue(), f"Relatorio_Acervo_COMSOC_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
                            ui.notify("📄 Relatório PDF do Histórico gerado com sucesso!", color="success")
                        except Exception as pdf_err:
                            ui.notify(f"Erro ao gerar PDF: {pdf_err}", color="negative")

                    ui.button(
                        'PDF', 
                        icon='picture_as_pdf', 
                        on_click=exportar_pdf_historico
                    ).props('unelevated color=red-9 text-color=white bold').classes('q-px-md').tooltip('Exportar Relatório PDF do Histórico')

            current_pautas_filtradas = []

            @ui.refreshable
            def render_event_cards():
                nonlocal current_pautas_filtradas
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

                # ── PAINEL DE KPIS SUPERIOR ──
                tot_eventos = len(pautas)
                tot_drive = sum(1 for p in pautas if get_demanda_drive_url(p))
                tot_fotos = sum(len(v) for v in fotos_por_evento.values())
                mes_atual_str = datetime.now().strftime('%Y-%m')
                tot_mes = sum(1 for p in pautas if str(p.get('data_evento', '')).startswith(mes_atual_str))

                with ui.row().classes('w-full gap-3 q-mb-md justify-between items-center wrap'):
                    with ui.card().classes('grow q-pa-sm no-shadow rounded-xl border border-cyan-500/20 bg-cyan-950/20 text-center').style('min-width: 140px;'):
                        ui.label(str(tot_eventos)).classes('text-lg font-black text-cyan')
                        ui.label('📁 Total de Eventos').classes('text-[9px] text-grey-4 uppercase font-bold')

                    with ui.card().classes('grow q-pa-sm no-shadow rounded-xl border border-teal-500/20 bg-teal-950/20 text-center').style('min-width: 140px;'):
                        ui.label(str(tot_drive)).classes('text-lg font-black text-teal-4')
                        ui.label('☁️ Com Pasta no Drive').classes('text-[9px] text-grey-4 uppercase font-bold')

                    with ui.card().classes('grow q-pa-sm no-shadow rounded-xl border border-amber-500/20 bg-amber-950/20 text-center').style('min-width: 140px;'):
                        ui.label(str(tot_fotos)).classes('text-lg font-black text-amber-4')
                        ui.label('📸 Fotos no Sistema').classes('text-[9px] text-grey-4 uppercase font-bold')

                    with ui.card().classes('grow q-pa-sm no-shadow rounded-xl border border-blue-500/20 bg-blue-950/20 text-center').style('min-width: 140px;'):
                        ui.label(str(tot_mes)).classes('text-lg font-black text-blue-4')
                        ui.label('📅 Coberturas no Mês').classes('text-[9px] text-grey-4 uppercase font-bold')

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

                current_pautas_filtradas = pautas_filtradas

                if pautas_filtradas:
                    with ui.column().classes('w-full gap-4'):
                        for p in pautas_filtradas:
                            ev_title = p['titulo_evento']
                            fotos = fotos_por_evento.get(ev_title, [])
                            drive_link = get_demanda_drive_url(p) or (fotos[0].get('drive_link') if fotos else None)
                            
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                            ):
                                with ui.row().classes('w-full justify-between items-start no-wrap gap-4'):
                                    with ui.column().classes('gap-1 flex-grow'):
                                        with ui.row().classes('items-center gap-2 wrap'):
                                            ui.label(ev_title).classes('text-md font-bold text-white')
                                            if drive_link:
                                                ui.badge('🟢 Drive Vinculado', color='teal-9').classes('text-[8px] font-bold')
                                            else:
                                                ui.badge('⚪ Sem Drive', color='grey-9').classes('text-[8px]')
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
                                        with ui.row().classes('gap-1.5 items-center wrap justify-end'):
                                            if drive_link:
                                                ui.button('📸 Galeria', on_click=lambda id=p['id']: ui.navigate.to(f'/comsoc_galeria?evento_id={id}')).props('unelevated color=primary text-color=black dense').classes('text-[10px] q-px-sm bold')
                                                ui.button('📁 Drive', on_click=lambda u=drive_link: ui.open(u, new_tab=True)).props('unelevated color=blue dense icon=open_in_new').classes('text-[10px] q-px-xs')
                                                
                                                def abrir_distribuir_acervo(cur_p=p, d_link=drive_link):
                                                    with ui.dialog() as dlg_dist, ui.card().classes('w-[520px] max-w-[95vw] q-pa-md'):
                                                        ui.label(f"📲 Distribuir Acervo: {cur_p['titulo_evento']}").classes('text-sm font-bold text-cyan q-mb-xs')
                                                        ui.label('Escolha o canal e os destinatários para encaminhar os links oficiais').classes('text-[11px] text-grey-4 q-mb-md')
                                                        
                                                        with ui.tabs().classes('w-full text-cyan') as tabs_dist:
                                                            tab_tg = ui.tab('✈️ Telegram', icon='send')
                                                            tab_zap = ui.tab('🟢 WhatsApp', icon='chat')
                                                            
                                                        with ui.tab_panels(tabs_dist, value=tab_tg).classes('w-full bg-transparent p-0 q-mt-sm'):
                                                            # ABA 1: TELEGRAM
                                                            with ui.tab_panel(tab_tg).classes('p-0'):
                                                                opt_modo = ui.radio(
                                                                    {
                                                                        'todos': '👥 Todos os Militares (Broadcast no Telegram)',
                                                                        'membros': '🎯 Seleção de Militares Específicos',
                                                                        'custom': '💬 Chat ID / Grupo Específico'
                                                                    },
                                                                    value='todos'
                                                                ).props('dark dense').classes('text-xs gap-2 q-mb-sm')
                                                                
                                                                # Lista de militares com telegram
                                                                militia_tg = []
                                                                svc_db = get_service_db_connection() or get_db_connection()
                                                                if svc_db:
                                                                    try:
                                                                        res_m = svc_db.table('efetivo').select('*').not_.is_('telegram_id', 'null').execute()
                                                                        militia_tg = res_m.data or []
                                                                    except Exception:
                                                                        pass
                                                                
                                                                opts_mil = {str(m['telegram_id']): f"{m.get('posto_grad','')} {m.get('nome_guerra','')}".strip() for m in militia_tg if m.get('telegram_id')}
                                                                sel_mil_multi = ui.select(opts_mil, label='Escolha os Militares', multiple=True).props('dark outlined dense use-chips w-full').classes('q-mb-sm text-xs')
                                                                sel_mil_multi.set_visibility(False)
                                                                
                                                                txt_custom_id = ui.input('Chat ID / Grupo ID do Telegram', placeholder='Ex: -100123456789 ou 123456789').props('dark outlined dense w-full').classes('q-mb-sm')
                                                                txt_custom_id.set_visibility(False)
                                                                
                                                                def toggle_modo_tg(e):
                                                                    sel_mil_multi.set_visibility(e.value == 'membros')
                                                                    txt_custom_id.set_visibility(e.value == 'custom')
                                                                
                                                                opt_modo.on_value_change(toggle_modo_tg)
                                                                
                                                                async def executar_envio_tg():
                                                                    from telegram_bot.utils import enviar_links_acervo, get_telegram_bot_instance
                                                                    bot = await get_telegram_bot_instance()
                                                                    if not bot:
                                                                        ui.notify('Bot do Telegram não inicializado no servidor.', color='warning')
                                                                        return
                                                                    
                                                                    alvos = []
                                                                    if opt_modo.value == 'todos':
                                                                        alvos = [str(m['telegram_id']) for m in militia_tg if m.get('telegram_id')]
                                                                    elif opt_modo.value == 'membros':
                                                                        alvos = sel_mil_multi.value or []
                                                                    elif opt_modo.value == 'custom':
                                                                        if txt_custom_id.value.strip():
                                                                            alvos = [txt_custom_id.value.strip()]
                                                                    
                                                                    if not alvos:
                                                                        ui.notify('Nenhum destinatário selecionado.', color='warning')
                                                                        return
                                                                    
                                                                    sucessos = 0
                                                                    for cid in alvos:
                                                                        ok = await enviar_links_acervo(bot, cid, cur_p)
                                                                        if ok:
                                                                            sucessos += 1
                                                                    
                                                                    ui.notify(f"✈️ Mensagem enviada para {sucessos} destinatário(s) no Telegram!", color='success')
                                                                    dlg_dist.close()

                                                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                                                    ui.button('Cancelar', on_click=dlg_dist.close).props('flat color=grey')
                                                                    ui.button('✈️ Disparar Telegram', on_click=executar_envio_tg).props('unelevated color=cyan bold')

                                                            # ABA 2: WHATSAPP
                                                            with ui.tab_panel(tab_zap).classes('p-0'):
                                                                txt_zap_msg = f"""📸 *ACERVO FOTOGRÁFICO COMSOC / CGCFN*

🎖️ *Evento:* {cur_p['titulo_evento']}
📅 *Data:* {cur_p['data_evento']}
📍 *Local:* {cur_p.get('local_evento', 'Quartel')}
👤 *Solicitante:* {cur_p['solicitante_nome']} ({cur_p.get('setor','')})

📁 *Link do Google Drive / Fotos:*
{d_link}

_Comunicação Social — Comando-Geral do Corpo de Fuzileiros Navais_"""

                                                                area_zap = ui.textarea('Mensagem Pronta para WhatsApp', value=txt_zap_msg).props('dark outlined dense w-full rows=7').classes('font-mono text-xs')
                                                                
                                                                def copiar_zap():
                                                                    encoded = urllib.parse.quote(area_zap.value)
                                                                    ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(area_zap.value)})')
                                                                    ui.notify('📋 Texto copiado para a área de transferência!', color='success')

                                                                def abrir_web_zap():
                                                                    encoded = urllib.parse.quote(area_zap.value)
                                                                    ui.open(f"https://api.whatsapp.com/send?text={encoded}", new_tab=True)

                                                                with ui.row().classes('w-full justify-between items-center q-mt-md'):
                                                                    ui.button('📋 Copiar Texto', on_click=copiar_zap).props('outline color=amber dense').classes('text-xs')
                                                                    ui.button('🟢 Abrir WhatsApp Web', on_click=abrir_web_zap).props('unelevated color=green dense bold').classes('text-xs')

                                                    dlg_dist.open()

                                                ui.button('📲 Distribuir', on_click=abrir_distribuir_acervo).props('outline color=cyan dense').classes('text-[10px] q-px-xs').tooltip('Distribuir via Telegram ou WhatsApp')
                                            else:
                                                def criar_pasta_historico(cur_p=p):
                                                    res = drive_service.criar_pasta_evento(cur_p['titulo_evento'], cur_p['data_evento'])
                                                    if res:
                                                        new_link = res['evento_link']
                                                        conn = get_db_connection()
                                                        if conn:
                                                            try:
                                                                conn.table('demandas_comunicacao').update({'drive_url': new_link}).eq('id', cur_p['id']).execute()
                                                            except Exception:
                                                                pass
                                                        ui.notify(f"📂 Pasta criada no Drive!", color='success')
                                                        render_event_cards.refresh()
                                                    else:
                                                        ui.notify("⚠️ Não foi possível criar pasta no Drive. Verifique se o JSON da Service Account e a Pasta Mãe foram configurados no Admin.", color='warning')

                                                ui.button('📂 Criar Pasta no Drive', on_click=criar_pasta_historico).props('unelevated color=blue-7 dense').classes('text-[10px] q-px-xs bold').tooltip('Criar Pasta no Drive automaticamente')

                                                def associar_drive(evento=ev_title):
                                                    with ui.dialog() as diag, ui.card().classes('w-96 q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                                                        ui.label('Associar Link do Drive Manualmente').classes('text-white text-md font-bold')
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

                                                ui.button('🔗 Vincular', on_click=associar_drive).props('flat color=grey-4 dense').classes('text-[10px] q-px-xs').tooltip('Vincular link existente manualmente')
                                        
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
                efetivo_raw = []
                demandas = []
                presencas_hoje = {}
                
                hoje_str = datetime.now().strftime('%Y-%m-%d')

                if db:
                    try:
                        res_ef = db.table('efetivo').select('*').order('nome_guerra').execute()
                        efetivo_raw = res_ef.data or []
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

                # 1. Filtra apenas a equipe COMSOC / Gabinete (exclui a categoria genérica 'militar' / 'operador' / 'compel')
                # 2. Remove duplicados por (posto_grad, nome_guerra)
                efetivo = []
                seen_militar = set()
                for m in efetivo_raw:
                    role_raw = str(m.get('role') or 'militar').strip().lower()
                    if role_raw in ('militar', 'compel', 'operador'):
                        continue  # Não listar os da categoria militar/geral
                    
                    pg = str(m.get('posto_grad') or m.get('posto') or '').replace('None', '').strip().upper()
                    ng = str(m.get('nome_guerra') or m.get('nome') or '').replace('None', '').strip().upper()
                    key = (pg, ng)
                    if key not in seen_militar and ng:
                        seen_militar.add(key)
                        efetivo.append(m)

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
                        st = str(dem.get('status', '')).strip().lower()
                        
                        enc_id = str(dem.get('encarregado_id', ''))
                        des_id = str(dem.get('designer_id', ''))
                        fot_id = str(dem.get('fotografo_id', ''))
                        
                        raw_notif = str(dem.get('notificar_militar_ids') or '')
                        aut_obs = f"{dem.get('autoridades', '')} {dem.get('observacoes', '')} {dem.get('solicitante_nome', '')} {dem.get('titulo_evento', '')}".upper()

                        eh_vinculado = False
                        if militar_id_str and militar_id_str in (enc_id, des_id, fot_id):
                            eh_vinculado = True
                        elif militar_id_str and (f'"{militar_id_str}"' in raw_notif or f'[{militar_id_str}' in raw_notif or f', {militar_id_str}' in raw_notif):
                            eh_vinculado = True
                        elif nome_g and len(nome_g) >= 3 and (nome_g in raw_notif.upper() or nome_g in aut_obs):
                            eh_vinculado = True

                        if eh_vinculado:
                            pautas_militar.append(dem)
                            if st in ('pendente', 'pendentes', 'aprovada', 'aprovado', 'ajustes'):
                                pendentes_militar.append(dem)
                            elif st in ('concluida', 'concluido', 'concluidas'):
                                concluidas_militar.append(dem)

                    st_presenca = presencas_hoje.get(nome_g, 'P')
                    
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
                        'pautas_todas_list': pautas_militar,
                        'nivel_carga': nivel_carga,
                        'cor_carga': cor_carga
                    })

                # Ordenação padrão: Maior Carga / Mais Missões
                relatorio_militar.sort(key=lambda x: (x['ativas'], x['tot_pautas']), reverse=True)

                # ── CABEÇALHO COM KPIS, ORDENAÇÃO E BOTÃO EXCEL ──
                with ui.row().classes('w-full justify-between items-center q-mb-md wrap gap-3'):
                    with ui.row().classes('items-center gap-2 flex-wrap'):
                        ui.badge(f"👥 Efetivo COMSOC: {len(relatorio_militar)}").props('color=cyan-9 bold').classes('q-pa-xs text-xs')
                        ui.badge(f"⏳ Ativas: {tot_pendentes_geral}").props('color=amber-9 bold').classes('q-pa-xs text-xs')
                        ui.badge(f"✅ Concluídas: {tot_concluidas_geral}").props('color=green-9 bold').classes('q-pa-xs text-xs')

                    with ui.row().classes('items-center gap-3 wrap'):
                        sort_select = ui.select(
                            {
                                'carga_desc': '📊 Maior Carga (Ativas)',
                                'tot_desc': '📋 Mais Missões Totais',
                                'concluidas_desc': '✅ Mais Concluídas',
                                'nome_asc': '🔤 Nome (A-Z)'
                            },
                            value='carga_desc',
                            label='Ordenar Efetivo Por'
                        ).props('dark outlined dense').classes('w-56 text-xs')

                        def reordenar_efetivo(e):
                            criterio = e.value
                            if criterio == 'carga_desc':
                                relatorio_militar.sort(key=lambda x: (x['ativas'], x['tot_pautas']), reverse=True)
                            elif criterio == 'tot_desc':
                                relatorio_militar.sort(key=lambda x: x['tot_pautas'], reverse=True)
                            elif criterio == 'concluidas_desc':
                                relatorio_militar.sort(key=lambda x: x['concluidas'], reverse=True)
                            elif criterio == 'nome_asc':
                                relatorio_militar.sort(key=lambda x: x['nome_guerra'])
                            render_relatorio_efetivo.refresh()

                        sort_select.on_value_change(reordenar_efetivo)

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
                                        'Total Missões': r['tot_pautas'],
                                        'Nível de Carga': r['nivel_carga']
                                    })
                                df = pd.DataFrame(export_data)
                                buffer = io.BytesIO()
                                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                    df.to_excel(writer, sheet_name='Produtividade_COMSOC', index=False)
                                buffer.seek(0)
                                ui.download(buffer.getvalue(), f"Relatorio_Produtividade_COMSOC_{hoje_str}.xlsx")
                                ui.notify('📥 Relatório Excel gerado com sucesso!', color='positive')
                            except Exception as exp_err:
                                ui.notify(f'Erro ao exportar Excel: {exp_err}', color='negative')

                        ui.button('📥 Exportar Excel', icon='download',
                                  on_click=exportar_excel
                        ).props('unelevated color=green text-color=white bold dense').classes('text-xs q-px-sm')

                # ── GRID EM 4 COLUNAS COM CARDS DE USUÁRIOS ──
                if relatorio_militar:
                    with ui.row().classes('w-full gap-3 items-stretch wrap'):
                        for r in relatorio_militar:
                            clean_pg = str(r['posto_grad'] or '').replace('None', '').strip()
                            clean_title = f"{clean_pg} {r['nome_guerra']}".strip()

                            with ui.card().classes('q-pa-md no-shadow rounded-xl border flex flex-col justify-between').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; width: calc(25% - 10px); min-width: 230px; flex: 1 1 230px;'
                            ):
                                # Topo do Card: Nome, Cargo e Badge de Carga
                                with ui.column().classes('w-full gap-1'):
                                    with ui.row().classes('w-full justify-between items-start no-wrap gap-1'):
                                        with ui.row().classes('items-center gap-1.5 shrink-0'):
                                            ui.icon('person', size='1.3rem', color='cyan-4')
                                            ui.label(clean_title).classes('text-xs font-bold text-white truncate max-w-[140px]')
                                        ui.badge(r['nivel_carga']).props(f"color={r['cor_carga']} bold").classes('text-[8px]')

                                    ui.label(r['cargo']).classes('text-[10px] text-grey-4 truncate')

                                # Meio do Card: Métricas e Indicadores (Ativas, Concluídas, Total)
                                with ui.row().classes('w-full justify-around items-center bg-black/20 q-py-xs rounded q-my-xs text-center border border-white/5'):
                                    with ui.column().classes('items-center gap-0'):
                                        ui.label(str(r['ativas'])).classes(f"text-md font-black text-{r['cor_carga']}")
                                        ui.label('Ativas').classes('text-[8px] text-grey-4')

                                    ui.separator().props('vertical').classes('q-mx-2')

                                    with ui.column().classes('items-center gap-0'):
                                        ui.label(str(r['concluidas'])).classes('text-md font-black text-green-4')
                                        ui.label('Concluídas').classes('text-[8px] text-grey-4')

                                    ui.separator().props('vertical').classes('q-mx-2')

                                    with ui.column().classes('items-center gap-0'):
                                        ui.label(str(r['tot_pautas'])).classes('text-md font-black text-cyan-4')
                                        ui.label('Total').classes('text-[8px] text-grey-4')

                                # Rodapé: Botão de Ver Missões do Militar
                                def abrir_missoes_militar(data=r):
                                    with ui.dialog() as dlg_m, ui.card().classes('w-[520px] max-w-[95vw] q-pa-md'):
                                        ui.label(f"📋 Missões de {data['posto_grad']} {data['nome_guerra']}").classes('text-sm font-bold text-cyan q-mb-sm')
                                        if data['pautas_todas_list']:
                                            with ui.column().classes('w-full gap-2 max-h-[350px] overflow-y-auto'):
                                                for p_m in data['pautas_todas_list']:
                                                    st_m = str(p_m.get('status', 'pendente')).upper()
                                                    st_color = 'green' if 'CONCLU' in st_m else 'amber'
                                                    with ui.card().classes('w-full q-pa-xs px-2 no-shadow rounded bg-white/5 border border-white/10'):
                                                        with ui.row().classes('w-full justify-between items-center text-xs'):
                                                            ui.label(p_m.get('titulo_evento', '')).classes('font-bold text-white truncate max-w-[70%]')
                                                            ui.badge(st_m).props(f'color={st_color} dense').classes('text-[8px]')
                                                        ui.label(f"📅 {p_m.get('data_evento','')} | 📍 {p_m.get('local_evento','')}").classes('text-[10px] text-grey-4')
                                        else:
                                            ui.label('Nenhuma missão vinculada a este militar.').classes('text-xs text-grey-5 italic q-my-md')
                                        
                                        with ui.row().classes('w-full justify-end q-mt-sm'):
                                            ui.button('Fechar', on_click=dlg_m.close).props('flat color=grey')
                                    dlg_m.open()

                                ui.button('📋 Ver Missões', on_click=lambda d=r: abrir_missoes_militar(d)).props('flat dense color=cyan icon=list_alt').classes('w-full text-[10px]')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('group_off', size='3rem')
                        ui.label('Nenhum militar da COMSOC/Gabinete encontrado.').classes('text-xs')

            render_relatorio_efetivo()
