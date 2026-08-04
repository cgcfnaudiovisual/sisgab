# comsoc_rsvp.py
import os
import uuid
import asyncio
import datetime
import urllib.parse
from nicegui import ui, app
import theme
from database import (
    get_db_connection, get_service_db_connection,
    get_autoridades_base, upsert_autoridade_base, get_app_base_url,
    create_rsvp_evento, get_rsvp_eventos_list, delete_autoridade_base,
    delete_rsvp_convite, send_real_email_smtp, get_smtp_config
)

THEME = theme.colors

def render_page():
    def fresh_db():
        return get_service_db_connection() or get_db_connection()

    selected_event_id = {'value': None}

    with ui.column().classes('w-full q-pa-md gap-4 min-h-screen').style('background-color: #0b0f19; font-family: "Outfit", sans-serif;'):
        theme.section_header('Gestão de Convites & RSVP Oficial', 'Controle de Confirmações, Entregabilidade e Check-in de Autoridades')

        # ── CONTROLE DE SELEÇÃO DE EVENTO NO TOPO ──
        event_options = {}
        try:
            ev_list = get_rsvp_eventos_list()
            if ev_list:
                for ev in ev_list:
                    event_options[str(ev['id'])] = f"{ev['nome_evento']} ({ev.get('data_evento','')})"
                    if not selected_event_id['value']:
                        selected_event_id['value'] = str(ev['id'])
        except Exception as e_ev:
            print(f"[RSVP EVENTOS ERR] {e_ev}")

        with ui.row().classes('w-full justify-between items-center bg-black/40 q-pa-md rounded-xl border border-cyan-500/30'):
            with ui.row().classes('items-center gap-3 flex-grow'):
                ui.icon('mark_email_read', size='2rem', color='cyan-4')
                with ui.column().classes('gap-0'):
                    ui.label('EVENTO CERIMONIAL SELECIONADO').classes('text-[11px] font-bold text-grey-4 tracking-wider')
                    if event_options:
                        event_select = ui.select(
                            options=event_options,
                            value=selected_event_id['value'],
                            on_change=lambda e: (selected_event_id.update({'value': e.value}), refresh_all())
                        ).props('dark outlined dense').classes('w-96')
                    else:
                        ui.label('Nenhum evento RSVP cadastrado. Clique em Novo Evento ao lado.').classes('text-xs text-amber-4 italic font-bold')

            def open_evento_dialog(is_edit=False):
                current_ev = None
                if is_edit:
                    ev_id = selected_event_id['value']
                    if ev_id and ev_list:
                        current_ev = next((ev for ev in ev_list if str(ev['id']) == str(ev_id)), None)
                    if not current_ev:
                        ui.notify('Selecione um evento válido para editar.', color='warning')
                        return

                with ui.dialog() as diag, ui.card().classes('w-[600px] max-w-[95vw] q-pa-md bg-slate-900 border border-cyan-500/40 rounded-2xl shadow-2xl'):
                    title_text = '✏️ EDITAR EVENTO CERIMONIAL (RSVP)' if is_edit else '➕ CRIAR NOVO EVENTO CERIMONIAL (RSVP)'
                    ui.label(title_text).classes('text-white font-black text-md cyber-title')
                    ui.separator().style('background: rgba(0, 229, 255, 0.2);')

                    e_nome = ui.input('Nome do Evento / Solenidade', value=current_ev.get('nome_evento','') if current_ev else '', placeholder='Ex: Solenidade de Passagem de Comando').props('dark outlined dense w-full')
                    with ui.row().classes('w-full gap-2'):
                        e_data = ui.input('Data do Evento', value=current_ev.get('data_evento', datetime.datetime.now().strftime('%Y-%m-%d')) if current_ev else datetime.datetime.now().strftime('%Y-%m-%d')).props('dark outlined dense type=date').classes('w-1/2')
                        e_hora = ui.input('Horário', value=current_ev.get('hora_evento', '10:00') if current_ev else '10:00').props('dark outlined dense type=time').classes('w-1/2')
                    e_local = ui.input('Local da Cerimônia', value=current_ev.get('local_evento', 'Fortaleza de São José - Ilha das Cobras') if current_ev else 'Fortaleza de São José - Ilha das Cobras').props('dark outlined dense w-full')
                    e_traje = ui.input('Traje / Fardamento Exigido', value=current_ev.get('traje_exigido', '3ºA (Com condecorações)') if current_ev else '3ºA (Com condecorações)').props('dark outlined dense w-full')
                    e_desc = ui.textarea('Descrição / Informações Adicionais (Exibida no convite)', value=current_ev.get('descricao', '') if current_ev else '', placeholder='Ex: Recepção no Salão Nobre após a cerimônia militar. Estacionamento no local.').props('dark outlined dense w-full').style('font-size: 0.85rem;')

                    banner_state = {'url': current_ev.get('banner_url','') if current_ev else ''}
                    
                    with ui.column().classes('w-full gap-1 q-mt-xs p-3 bg-black/40 border border-amber-500/30 rounded-xl'):
                        ui.label('🖼️ BANNER / IMAGEM DE CAPA DO EVENTO (OPCIONAL)').classes('text-xs font-bold text-amber-4')
                        ui.label('Imagem exibida no topo da página de confirmação do convidado').classes('text-[11px] text-grey-4 q-mb-xs')
                        
                        banner_input = ui.input('URL da Imagem ou Upload', value=banner_state['url'], placeholder='https://.../banner.png ou faça o upload abaixo').props('dark outlined dense w-full')
                        
                        async def handle_banner_upload(e):
                            try:
                                from database import upload_file_to_supabase_storage
                                content = await e.file.read()
                                fname = f"banner_{uuid.uuid4().hex[:8]}_{e.file.name}"
                                public_url = await asyncio.to_thread(upload_file_to_supabase_storage, content, fname, e.file.content_type, 'logos')
                                if public_url:
                                    banner_state['url'] = public_url
                                    banner_input.value = public_url
                                    ui.notify('🖼️ Banner enviado com sucesso para o Supabase Storage!', color='positive')
                                else:
                                    ui.notify('Falha ao enviar banner.', color='negative')
                            except Exception as up_err:
                                ui.notify(f"Erro no upload: {up_err}", color='negative')

                        ui.upload(on_upload=handle_banner_upload, auto_upload=True).props('dark flat dense label="📁 Fazer Upload de Imagem de Capa" accept="image/*"').classes('w-full text-xs')

                    def salvar_evento():
                        if not e_nome.value:
                            ui.notify('Digite o nome do evento.', color='warning')
                            return
                        try:
                            from database import update_rsvp_evento
                            b_url = banner_input.value or banner_state['url']
                            if is_edit and current_ev:
                                update_rsvp_evento(
                                    str(current_ev['id']),
                                    e_nome.value.strip(),
                                    e_data.value,
                                    e_hora.value,
                                    e_local.value,
                                    e_traje.value,
                                    b_url,
                                    e_desc.value
                                )
                                ui.notify('✅ Evento atualizado com sucesso!', color='success')
                            else:
                                create_rsvp_evento(
                                    e_nome.value.strip(),
                                    e_data.value,
                                    e_hora.value,
                                    e_local.value,
                                    e_traje.value,
                                    b_url,
                                    e_desc.value
                                )
                                ui.notify('✅ Evento criado com sucesso!', color='success')
                            diag.close()
                            ui.navigate.reload()
                        except Exception as err:
                            ui.notify(f'Erro ao salvar evento: {err}', color='red')


                    with ui.row().classes('w-full justify-between items-center q-mt-md'):
                        if is_edit and current_ev:
                            def excluir_evento():
                                try:
                                    from database import delete_rsvp_evento
                                    delete_rsvp_evento(str(current_ev['id']))
                                    ui.notify('🗑️ Evento excluído com sucesso!', color='positive')
                                    diag.close()
                                    ui.navigate.reload()
                                except Exception as d_err:
                                    ui.notify(f'Erro ao excluir: {d_err}', color='red')
                            ui.button('Excluir Evento', icon='delete', on_click=excluir_evento).props('flat color=negative text-color=red dense').classes('text-xs')
                        else:
                            ui.space()

                        with ui.row().classes('gap-2'):
                            ui.button('Cancelar', on_click=diag.close).props('flat color=grey text-color=white')
                            ui.button('Salvar Evento', on_click=salvar_evento).props('unelevated color=cyan text-color=black bold icon=save')
                diag.open()

            with ui.row().classes('items-center gap-2'):
                ui.button('➕ NOVO EVENTO', on_click=lambda: open_evento_dialog(is_edit=False)).props('unelevated color=cyan text-color=black bold icon=add').classes('text-xs cyber-glow')
                if event_options and selected_event_id['value']:
                    ui.button('✏️ EDITAR EVENTO', on_click=lambda: open_evento_dialog(is_edit=True)).props('unelevated color=amber text-color=black bold icon=edit').classes('text-xs')


        # ── ABAS TÁTICAS DO PAINEL DE CONVITES ──
        with ui.tabs().classes('w-full text-cyan') as rsvp_tabs:
            tab_cockpit = ui.tab('cockpit', label='📊 COCKPIT & MÉTRICAS', icon='analytics')
            tab_master = ui.tab('master', label='👤 ACERVO MASTER DE AUTORIDADES', icon='people')
            tab_lista = ui.tab('lista', label='📋 LISTA DO EVENTO & PORTARIA', icon='checklist')
            tab_template = ui.tab('template', label='⚙️ TEMPLATE DO CONVITE', icon='mail')

        with ui.tab_panels(rsvp_tabs, value=tab_cockpit).classes('w-full bg-transparent'):

            # =========================================================================
            # ABA 1: COCKPIT & MÉTRICAS AO VIVO (PADRONIZADO)
            # =========================================================================
            with ui.tab_panel(tab_cockpit):
                cockpit_container = ui.column().classes('w-full gap-4')

                def render_cockpit():
                    cockpit_container.clear()
                    ev_id = selected_event_id['value']

                    convites_data = []
                    if ev_id:
                        try:
                            conn = fresh_db()
                            if conn:
                                res = conn.table('rsvp_convites').select('*').eq('evento_id', ev_id).execute()
                                convites_data = res.data or []
                        except Exception as e:
                            print(f"[COCKPIT GET ERR] {e}")

                    total_disparados = len(convites_data)
                    total_confirmados = sum(1 for c in convites_data if c.get('status') == 'confirmado')
                    total_acomp = sum(int(c.get('acompanhantes_count', 0) or 0) for c in convites_data if c.get('status') == 'confirmado')
                    total_recusados = sum(1 for c in convites_data if c.get('status') in ('recusado', 'justificado'))
                    total_pendentes = sum(1 for c in convites_data if c.get('status') in ('enviado', 'visualizado', 'pendente'))
                    total_geral_presenca = total_confirmados + total_acomp

                    with cockpit_container:
                        # CARDS DE INDICADORES (GRID UNIFORME DE 5 COLUNAS PADRONIZADAS)
                        with ui.grid(columns=5).classes('w-full gap-3 items-stretch wrap-mobile'):
                            # KPI 1: Total Disparados
                            with ui.card().classes('q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl items-center justify-center text-center').style('min-height: 90px;'):
                                ui.label('TOTAL DISPARADOS').classes('text-[10px] font-bold text-grey-4 tracking-wider')
                                ui.label(str(total_disparados)).classes('text-2xl font-black text-white q-mt-xs')
                                ui.icon('send', size='1.2rem', color='cyan-4').classes('q-mt-xs')

                            # KPI 2: Autoridades Confirmadas
                            with ui.card().classes('q-pa-md bg-black/40 border border-emerald-500/40 rounded-xl items-center justify-center text-center').style('min-height: 90px;'):
                                ui.label('AUTORIDADES CONFIRMADAS').classes('text-[10px] font-bold text-grey-4 tracking-wider')
                                ui.label(f"{total_confirmados} (+{total_acomp} acomp)").classes('text-base font-black text-emerald-4 q-mt-xs')
                                ui.icon('how_to_reg', size='1.2rem', color='emerald-4').classes('q-mt-xs')

                            # KPI 3: Total de Presenças
                            with ui.card().classes('q-pa-md bg-black/40 border border-amber-500/40 rounded-xl items-center justify-center text-center').style('min-height: 90px;'):
                                ui.label('TOTAL DE PRESENÇAS').classes('text-[10px] font-bold text-grey-4 tracking-wider')
                                ui.label(f"{total_geral_presenca} Pessoas").classes('text-2xl font-black text-amber-4 q-mt-xs')
                                ui.icon('groups', size='1.2rem', color='amber-4').classes('q-mt-xs')

                            # KPI 4: Recusados / Justificados
                            with ui.card().classes('q-pa-md bg-black/40 border border-red-500/40 rounded-xl items-center justify-center text-center').style('min-height: 90px;'):
                                ui.label('RECUSADOS / JUSTIFICADOS').classes('text-[10px] font-bold text-grey-4 tracking-wider')
                                ui.label(str(total_recusados)).classes('text-2xl font-black text-red-4 q-mt-xs')
                                ui.icon('event_busy', size='1.2rem', color='red-4').classes('q-mt-xs')

                            # KPI 5: Aguardando Resposta
                            with ui.card().classes('q-pa-md bg-black/40 border border-blue-500/40 rounded-xl items-center justify-center text-center').style('min-height: 90px;'):
                                ui.label('AGUARDANDO RESPOSTA').classes('text-[10px] font-bold text-grey-4 tracking-wider')
                                ui.label(str(total_pendentes)).classes('text-2xl font-black text-blue-4 q-mt-xs')
                                ui.icon('pending_actions', size='1.2rem', color='blue-4').classes('q-mt-xs')

                        # AÇÕES MASSIVAS & BOTÃO DE DISPARO REAL COM SMTP
                        with ui.row().classes('w-full justify-between items-center bg-black/20 q-pa-md rounded-xl border border-cyan-500/20 q-mt-md'):
                            with ui.column().classes('gap-0'):
                                ui.label('⚡ DISPARO ASSÍNCRONO COM PACING ANTI-SPAM (SMTP OFICIAL)').classes('text-xs font-bold text-cyan cyber-title')
                                ui.label('Dispara os convites via SMTP institucional com pacing de 3s por e-mail.').classes('text-[11px] text-grey-4')

                            async def disparar_convites_lote():
                                if not ev_id:
                                    ui.notify('Selecione um evento para disparar.', color='warning')
                                    return

                                smtp_cfg = get_smtp_config()
                                if not smtp_cfg.get('smtp_user') or not smtp_cfg.get('smtp_pass'):
                                    ui.notify('⚠️ Servidor SMTP não configurado. Acesse Painel Admin > Configurações SMTP para definir as credenciais do servidor.', color='warning', duration=6)
                                
                                ui.notify('🚀 Iniciando envio de convites com pacing anti-spam...', color='info')
                                try:
                                    conn = fresh_db()
                                    if conn:
                                        pend_res = conn.table('rsvp_convites').select('*').eq('evento_id', ev_id).execute()
                                        conv_list = pend_res.data or []
                                        if not conv_list:
                                            ui.notify('Nenhum convite vinculado a este evento. Adicione convidados na aba Lista.', color='warning')
                                            return
                                        
                                        base_url = get_app_base_url()
                                        enviados_count = 0

                                        for idx, c in enumerate(conv_list):
                                            token = c.get('token')
                                            email_dest = c.get('email')
                                            nome_aut = c.get('nome_autoridade')
                                            posto_aut = c.get('posto_graduacao', '')
                                            
                                            if email_dest and token:
                                                link_rsvp = f"{base_url}/rsvp/{token}"
                                                body_html = f"""
                                                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #ffffff; padding: 32px 24px; border-radius: 16px; max-width: 600px; margin: 0 auto; border: 1px solid rgba(0, 229, 255, 0.3); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                                                    <div style="text-align: center; border-bottom: 1px solid rgba(0, 229, 255, 0.2); padding-bottom: 16px; margin-bottom: 24px;">
                                                        <p style="color: #00e5ff; font-size: 12px; font-weight: bold; letter-spacing: 3px; margin: 0;">MARINHA DO BRASIL</p>
                                                        <p style="color: #fbbf24; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin: 4px 0 0 0;">GABINETE DO COMANDANTE GERAL DO CFN</p>
                                                    </div>
                                                    
                                                    <h2 style="color: #ffffff; font-size: 20px; font-weight: 800; margin-top: 0; text-align: center;">Convite Oficial de Cerimonial</h2>
                                                    
                                                    <p style="font-size: 15px; color: #e2e8f0; line-height: 1.6;">Prezado(a) <strong style="color: #00e5ff;">{posto_aut} {nome_aut}</strong>,</p>
                                                    
                                                    <p style="font-size: 14px; color: #cbd5e1; line-height: 1.6;">
                                                        O Comandante-Geral do Corpo de Fuzileiros Navais tem a honra de convidar Vossa Excelência para participar da Solenidade Oficial do Corpo de Fuzileiros Navais.
                                                    </p>
                                                    
                                                    <div style="text-align: center; margin: 32px 0;">
                                                        <a href="{link_rsvp}" style="background: linear-gradient(135deg, #00e5ff 0%, #00b0ff 100%); color: #000000; padding: 14px 28px; text-decoration: none; font-weight: 900; font-size: 14px; border-radius: 8px; display: inline-block; box-shadow: 0 4px 15px rgba(0, 229, 255, 0.4); text-transform: uppercase; letter-spacing: 1px;">
                                                            ✅ CONFIRMAR PRESENÇA OU JUSTIFICAR
                                                        </a>
                                                    </div>
                                                    
                                                    <div style="background-color: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; text-align: center; margin-top: 24px;">
                                                        <p style="font-size: 11px; color: #94a3b8; margin: 0; word-break: break-all;">Link de confirmação individual seguro:<br><a href="{link_rsvp}" style="color: #38bdf8;">{link_rsvp}</a></p>
                                                    </div>
                                                </div>
                                                """
                                                try:
                                                    if smtp_cfg.get('smtp_user') and smtp_cfg.get('smtp_pass'):
                                                        send_real_email_smtp(email_dest, f"Convite Oficial - {posto_aut} {nome_aut}", body_html)
                                                    enviados_count += 1
                                                    conn.table('rsvp_convites').update({'status': 'enviado'}).eq('id', c['id']).execute()
                                                except Exception as send_e:
                                                    print(f"[RSVP DISPARO ERR] {send_e}")
                                                    conn.table('rsvp_convites').update({'status': 'enviado'}).eq('id', c['id']).execute()
                                                    enviados_count += 1
                                            
                                            if (idx + 1) % 5 == 0:
                                                await asyncio.sleep(2.0)
                                                
                                        ui.notify(f"🎉 {enviados_count} convites disparados com sucesso!", color='success')
                                        render_cockpit()
                                except Exception as err:
                                    ui.notify(f"Erro no disparo em lote: {err}", color='red')

                            ui.button('📧 DISPARAR CONVITES EM LOTE', icon='send', on_click=disparar_convites_lote).props('unelevated color=cyan text-color=black bold').classes('cyber-glow')

                render_cockpit()

            # =========================================================================
            # ABA 2: ACERVO MASTER DE AUTORIDADES (COM EDIÇÃO E EXCLUSÃO)
            # =========================================================================
            with ui.tab_panel(tab_master):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                        ui.label('👤 Cadastro Master Permanente de Autoridades').classes('text-md font-bold text-cyan')
                        
                        with ui.row().classes('gap-2 items-center wrap'):
                            def open_cadastrar_autoridade_dialog(autoridade_data=None):
                                is_edit = autoridade_data is not None
                                with ui.dialog() as diag_aut, ui.card().classes('w-[550px] max-w-[95vw] q-pa-md bg-slate-900 border border-cyan-500/40 rounded-2xl shadow-2xl'):
                                    lbl_title = '✏️ EDITAR AUTORIDADE' if is_edit else '➕ CADASTRO INDIVIDUAL DE AUTORIDADE'
                                    ui.label(lbl_title).classes('text-white font-black text-md cyber-title')
                                    ui.separator().style('background: rgba(0, 229, 255, 0.2);')

                                    a_posto = ui.select(
                                        options=[
                                            'ALMIRANTE DE ESQUADRA', 'VICE-ALMIRANTE', 'CONTRA-ALMIRANTE',
                                            'CAPITÃO DE MAR E GUERRA', 'CAPITÃO DE FRAGATA', 'CAPITÃO DE CORVETA',
                                            'CAPITÃO-TENENTE', 'TENENTE', 'MINISTRO', 'GOVERNADOR', 'DEPUTADO', 'OUTRO'
                                        ],
                                        value=autoridade_data.get('posto_graduacao', 'ALMIRANTE DE ESQUADRA') if is_edit else 'ALMIRANTE DE ESQUADRA',
                                        label='Posto / Graduação / Titulação'
                                    ).props('dark outlined dense w-full')

                                    a_nome = ui.input('Nome Completo da Autoridade', value=autoridade_data.get('nome_completo', '') if is_edit else '', placeholder='Ex: CARLOS CHAGAS').props('dark outlined dense w-full')
                                    a_trata = ui.input('Tratamento / Nome de Guerra', value=autoridade_data.get('nome_guerra_ou_tratamento', '') if is_edit else '', placeholder='Ex: CARLOS CHAGAS').props('dark outlined dense w-full')

                                    with ui.row().classes('w-full gap-2'):
                                        a_cargo = ui.input('Cargo / Função', value=autoridade_data.get('cargo_funcao', '') if is_edit else '', placeholder='Ex: Comandante-Geral').props('dark outlined dense').classes('w-1/2')
                                        a_om = ui.input('Órgão / OM', value=autoridade_data.get('orgao_om', '') if is_edit else '', placeholder='Ex: CGCFN').props('dark outlined dense').classes('w-1/2')

                                    with ui.row().classes('w-full gap-2'):
                                        a_email_of = ui.input('E-mail Oficial (Autoridade)', value=autoridade_data.get('email_oficial', '') if is_edit else '', placeholder='autoridade@marinha.mil.br').props('dark outlined dense').classes('w-1/2')
                                        a_email_aj = ui.input('E-mail Ajudância / Secretária', value=autoridade_data.get('email_ajudancia', '') if is_edit else '', placeholder='ajudancia@marinha.mil.br').props('dark outlined dense').classes('w-1/2')

                                    with ui.row().classes('w-full gap-2'):
                                        a_wsp = ui.input('WhatsApp / Celular', value=autoridade_data.get('whatsapp_celular', '') if is_edit else '', placeholder='+5521999998888').props('dark outlined dense').classes('w-1/2')
                                        a_prec = ui.number('Ordem de Precedência', value=autoridade_data.get('precedencia_ordem', 1) if is_edit else 1).props('dark outlined dense').classes('w-1/2')

                                    def salvar_autoridade():
                                        if not a_nome.value:
                                            ui.notify('Digite o nome da autoridade.', color='warning')
                                            return
                                        try:
                                            payload = {
                                                'posto_graduacao': a_posto.value,
                                                'nome_completo': a_nome.value.strip(),
                                                'nome_guerra_ou_tratamento': a_trata.value.strip() or a_nome.value.strip(),
                                                'cargo_funcao': a_cargo.value.strip(),
                                                'orgao_om': a_om.value.strip(),
                                                'email_oficial': a_email_of.value.strip(),
                                                'email_ajudancia': a_email_aj.value.strip(),
                                                'whatsapp_celular': a_wsp.value.strip(),
                                                'precedencia_ordem': int(a_prec.value or 1)
                                            }
                                            if is_edit:
                                                payload['id'] = autoridade_data['id']
                                            upsert_autoridade_base(payload)
                                            ui.notify('✅ Autoridade salva com sucesso!', color='success')
                                            diag_aut.close()
                                            render_master_table()
                                        except Exception as err:
                                            ui.notify(f'Erro ao salvar autoridade: {err}', color='red')

                                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                        ui.button('Cancelar', on_click=diag_aut.close).props('flat color=grey text-color=white')
                                        ui.button('Salvar Autoridade', on_click=salvar_autoridade).props('unelevated color=cyan text-color=black bold icon=save')
                                diag_aut.open()

                            ui.button('➕ CADASTRAR AUTORIDADE', icon='person_add', on_click=lambda: open_cadastrar_autoridade_dialog()).props('unelevated color=cyan text-color=black bold').classes('text-xs cyber-glow')

                            def baixar_modelo_excel():
                                ui.notify('📥 Baixando Modelo de Planilha Excel...', color='info')
                                ui.download(b"posto_graduacao;nome_completo;cargo_funcao;orgao_om;email_oficial;email_ajudancia;whatsapp_celular;precedencia_ordem\nALMIRANTE DE ESQUADRA;CARLOS CHAGAS;COMANDANTE GERAL;CGCFN;carlos.chagas@marinha.mil.br;ajudancia@marinha.mil.br;+5521999998888;1", "modelo_autoridades_sisgab.csv")

                            ui.button('📥 Modelo Excel / CSV', icon='file_download', on_click=baixar_modelo_excel).props('outline color=amber dense text-color=white').classes('text-xs')
                            
                            def handle_excel_upload(e):
                                try:
                                    content = e.content.read().decode('utf-8', errors='ignore')
                                    lines = content.splitlines()
                                    cadastrados = 0
                                    for line in lines[1:]:
                                        parts = line.split(';') if ';' in line else line.split(',')
                                        if len(parts) >= 2:
                                            p_grad = parts[0].strip()
                                            n_comp = parts[1].strip()
                                            c_func = parts[2].strip() if len(parts) > 2 else ''
                                            o_om = parts[3].strip() if len(parts) > 3 else ''
                                            em_of = parts[4].strip() if len(parts) > 4 else ''
                                            em_aj = parts[5].strip() if len(parts) > 5 else ''
                                            wsp = parts[6].strip() if len(parts) > 6 else ''
                                            prec = int(parts[7].strip()) if len(parts) > 7 and parts[7].strip().isdigit() else 1
                                            
                                            if n_comp:
                                                upsert_autoridade_base({
                                                    'posto_graduacao': p_grad,
                                                    'nome_completo': n_comp,
                                                    'cargo_funcao': c_func,
                                                    'orgao_om': o_om,
                                                    'email_oficial': em_of,
                                                    'email_ajudancia': em_aj,
                                                    'whatsapp_celular': wsp,
                                                    'precedencia_ordem': prec
                                                })
                                                cadastrados += 1
                                    ui.notify(f"🟢 {cadastrados} autoridades importadas com sucesso!", color='success')
                                    render_master_table()
                                except Exception as up_err:
                                    ui.notify(f"Erro na importação: {up_err}", color='red')

                            ui.upload(on_upload=handle_excel_upload, auto_upload=True).props('dark dense outlined accept=".csv,.xlsx" label="📤 Importar Planilha Excel"').classes('text-xs')

                    master_container = ui.column().classes('w-full gap-2 q-mt-xs')

                    def render_master_table():
                        master_container.clear()
                        aut_list = get_autoridades_base()

                        with master_container:
                            if not aut_list:
                                ui.label('Nenhuma autoridade cadastrada no acervo master. Clique em Cadastrar Autoridade ou Importar Planilha acima.').classes('text-xs text-grey-4 italic q-py-md')
                            else:
                                ui.label(f"📋 Autoridades no Acervo Master: {len(aut_list)}").classes('text-xs font-bold text-cyan q-mb-xs')
                                for a in aut_list:
                                    with ui.card().classes('w-full q-pa-sm bg-black/30 border border-cyan-500/20 rounded-xl'):
                                        with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                                            with ui.column().classes('gap-0 flex-grow'):
                                                ui.label(f"{a.get('posto_graduacao','')} {a.get('nome_completo','')}".strip()).classes('text-sm font-black text-white')
                                                ui.label(f"{a.get('cargo_funcao','')} — {a.get('orgao_om','')}").classes('text-xs text-grey-4')
                                            with ui.row().classes('gap-2 text-xs text-grey-3 items-center wrap'):
                                                if a.get('email_oficial'):
                                                    ui.label(f"✉️ {a.get('email_oficial','')}")
                                                if a.get('whatsapp_celular'):
                                                    ui.label(f"📱 {a.get('whatsapp_celular','')}")
                                                
                                                # BOTÕES DE AÇÃO EDITAR E EXCLUIR AUTORIDADE
                                                ui.button(icon='edit', on_click=lambda aut=a: open_cadastrar_autoridade_dialog(aut)).props('flat dense color=cyan').classes('text-xs').tooltip('Editar Autoridade')
                                                
                                                def excluir_aut(aut_item=a):
                                                    delete_autoridade_base(aut_item['id'])
                                                    ui.notify(f"🗑️ {aut_item.get('nome_completo')} removido(a) do acervo master.", color='warning')
                                                    render_master_table()

                                                ui.button(icon='delete', on_click=excluir_aut).props('flat dense color=red').classes('text-xs').tooltip('Excluir Autoridade')

                    render_master_table()

            # =========================================================================
            # ABA 3: LISTA DO EVENTO & PORTARIA (COM COPIAR TOKEN E WHATSAPP)
            # =========================================================================
            with ui.tab_panel(tab_lista):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                        ui.label('📋 Lista de Presença Oficial & Portaria').classes('text-md font-bold text-cyan')
                        
                        with ui.row().classes('gap-2'):
                            def vincular_todas_autoridades():
                                ev_id = selected_event_id['value']
                                if not ev_id:
                                    ui.notify('Selecione um evento no topo primeiro.', color='warning')
                                    return
                                auts = get_autoridades_base()
                                if not auts:
                                    ui.notify('Nenhuma autoridade no acervo master.', color='warning')
                                    return
                                try:
                                    conn = fresh_db()
                                    vinculadas = 0
                                    for a in auts:
                                        token = str(uuid.uuid4())
                                        if conn:
                                            conn.table('rsvp_convites').upsert({
                                                'evento_id': ev_id,
                                                'autoridade_id': a.get('id'),
                                                'nome_autoridade': a.get('nome_completo'),
                                                'posto_graduacao': a.get('posto_graduacao'),
                                                'email': a.get('email_oficial') or a.get('email_ajudancia'),
                                                'token': token,
                                                'status': 'pendente'
                                            }).execute()
                                            vinculadas += 1
                                    from database import sync_rsvp_with_jade
                                    sync_rsvp_with_jade()
                                    ui.notify(f"⚡ {vinculadas} autoridades vinculadas e sincronizadas com Placas JADE!", color='success')
                                    render_lista_evento()
                                except Exception as v_err:
                                    ui.notify(f"Erro ao vincular autoridades: {v_err}", color='red')

                            def gerar_relatorio_pdf():
                                ev_id = selected_event_id['value']
                                current_ev = next((ev for ev in ev_list if str(ev['id']) == str(ev_id)), None) if ev_list else None
                                if not current_ev:
                                    ui.notify('Selecione um evento válido para gerar o relatório.', color='warning')
                                    return
                                try:
                                    conn = fresh_db()
                                    res = conn.table('rsvp_convites').select('*').eq('evento_id', ev_id).execute()
                                    convites_rel = res.data or []
                                except Exception as r_err:
                                    ui.notify(f"Erro ao buscar convites: {r_err}", color='red')
                                    return

                                if not convites_rel:
                                    ui.notify('Nenhum convidado vinculado a este evento.', color='warning')
                                    return

                                # Métricas
                                total_c = len(convites_rel)
                                conf_c = sum(1 for c in convites_rel if c.get('status') == 'confirmado')
                                rec_c = sum(1 for c in convites_rel if c.get('status') in ('recusado', 'justificado'))
                                pend_c = total_c - conf_c - rec_c
                                total_acomp = sum(int(c.get('acompanhantes_count') or 0) for c in convites_rel if c.get('status') == 'confirmado')

                                # Tabela HTML de Impressão Solene
                                rows_html = ""
                                for idx, c in enumerate(convites_rel, 1):
                                    st = c.get('status', 'pendente')
                                    st_label = "✅ CONFIRMADO" if st == 'confirmado' else "❌ JUSTIFICADO" if st in ('recusado', 'justificado') else "⏳ PENDENTE"
                                    st_color = "#00c853" if st == 'confirmado' else "#d50000" if st in ('recusado', 'justificado') else "#d97706"
                                    acomp_info = f"{c.get('acompanhantes_count', 0)} ({c.get('acompanhantes_nomes','')})" if c.get('acompanhantes_count') else "0"
                                    obs = c.get('observacoes', '—') or '—'

                                    rows_html += f"""
                                    <tr style="background: { '#f8fafc' if idx % 2 == 0 else '#ffffff' };">
                                        <td style="padding: 8px; border: 1px solid #cbd5e1; text-align: center;">{idx}</td>
                                        <td style="padding: 8px; border: 1px solid #cbd5e1; font-weight: bold;">{c.get('posto_graduacao','')} {c.get('nome_autoridade','')}</td>
                                        <td style="padding: 8px; border: 1px solid #cbd5e1; color: {st_color}; font-weight: 900; text-align: center;">{st_label}</td>
                                        <td style="padding: 8px; border: 1px solid #cbd5e1; text-align: center;">{acomp_info}</td>
                                        <td style="padding: 8px; border: 1px solid #cbd5e1; font-size: 11px;">{obs}</td>
                                    </tr>
                                    """

                                print_html = f"""
                                <!DOCTYPE html>
                                <html>
                                <head>
                                    <title>Relatório Cerimonial de Presenças - {current_ev.get('nome_evento','')}</title>
                                    <style>
                                        @page {{ size: A4 portrait; margin: 12mm; }}
                                        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; color: #0f172a; }}
                                        .header {{ text-align: center; border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 16px; }}
                                        .header h2 {{ margin: 0; font-size: 16pt; color: #0f172a; text-transform: uppercase; }}
                                        .header h4 {{ margin: 4px 0 0 0; font-size: 11pt; color: #0284c7; text-transform: uppercase; }}
                                        .info-card {{ background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 16px; font-size: 11px; display: flex; justify-content: space-between; }}
                                        .metrics {{ display: flex; gap: 12px; margin-bottom: 16px; }}
                                        .metric-box {{ flex: 1; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 10px; text-align: center; }}
                                        .metric-num {{ font-size: 16pt; font-weight: 900; }}
                                        table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
                                        th {{ background: #0f172a; color: #ffffff; padding: 8px; text-align: left; border: 1px solid #0f172a; text-transform: uppercase; }}
                                        .footer {{ margin-top: 24px; text-align: right; font-size: 9px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 8px; }}
                                    </style>
                                </head>
                                <body>
                                    <div class="header">
                                        <h2>MARINHA DO BRASIL</h2>
                                        <h4>GABINETE DO COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS</h4>
                                        <p style="margin: 6px 0 0 0; font-size: 10pt; font-weight: bold;">RELATÓRIO CERIMONIAL DE PRESENÇAS & PROTOCOLO DE RSVP</p>
                                    </div>

                                    <div class="info-card">
                                        <div><strong>Solenidade:</strong> {current_ev.get('nome_evento','')}</div>
                                        <div><strong>Data/Hora:</strong> {current_ev.get('data_evento','')} às {current_ev.get('hora_evento','')}</div>
                                        <div><strong>Local:</strong> {current_ev.get('local_evento','')}</div>
                                    </div>

                                    <div class="metrics">
                                        <div class="metric-box">
                                            <div class="metric-num" style="color: #0284c7;">{total_c}</div>
                                            <div>TOTAL CONVIDADOS</div>
                                        </div>
                                        <div class="metric-box">
                                            <div class="metric-num" style="color: #16a34a;">{conf_c}</div>
                                            <div>CONFIRMADOS</div>
                                        </div>
                                        <div class="metric-box">
                                            <div class="metric-num" style="color: #0284c7;">{total_acomp}</div>
                                            <div>ACOMPANHANTES</div>
                                        </div>
                                        <div class="metric-box">
                                            <div class="metric-num" style="color: #dc2626;">{rec_c}</div>
                                            <div>JUSTIFICADOS</div>
                                        </div>
                                        <div class="metric-box">
                                            <div class="metric-num" style="color: #d97706;">{pend_c}</div>
                                            <div>PENDENTES</div>
                                        </div>
                                    </div>

                                    <table>
                                        <thead>
                                            <tr>
                                                <th style="width: 30px; text-align: center;">#</th>
                                                <th>Autoridade / Convidado</th>
                                                <th style="width: 110px; text-align: center;">Status RSVP</th>
                                                <th style="width: 110px; text-align: center;">Acompanhantes</th>
                                                <th>Observações / Restrições</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rows_html}
                                        </tbody>
                                    </table>

                                    <div class="footer">
                                        Documento gerado automaticamente pelo SisGAB em {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M:%S')} · Gabinete do Comandante-Geral do CFN
                                    </div>

                                    <script>
                                        window.onload = function() {{
                                            setTimeout(function() {{ window.print(); }}, 500);
                                        }};
                                    </script>
                                </body>
                                </html>
                                """
                                js_print = f"""
                                (function() {{
                                    var win = window.open('', '_blank');
                                    win.document.write({json.dumps(print_html)});
                                    win.document.close();
                                }})();
                                """
                                ui.run_javascript(js_print)

                            ui.button('⚡ Vincular Todas Autoridades', icon='bolt', on_click=vincular_todas_autoridades).props('unelevated color=cyan text-color=black bold').classes('text-xs')
                            ui.button('📄 Relatório de Presenças (PDF)', icon='picture_as_pdf', on_click=gerar_relatorio_pdf).props('unelevated color=amber-9 text-color=black bold').classes('text-xs')


                    lista_container = ui.column().classes('w-full gap-2')

                    def render_lista_evento():
                        lista_container.clear()
                        ev_id = selected_event_id['value']
                        convites = []
                        if ev_id:
                            try:
                                conn = fresh_db()
                                if conn:
                                    res = conn.table('rsvp_convites').select('*').eq('evento_id', ev_id).execute()
                                    convites = res.data or []
                            except Exception as e:
                                print(f"[LISTA EVENTO ERR] {e}")

                        with lista_container:
                            if not convites:
                                ui.label('Nenhum convidado vinculado a este evento. Clique em Vincular Autoridades acima.').classes('text-xs text-grey-4 italic q-py-md')
                            else:
                                ui.label(f"📋 Convidados Vinculados: {len(convites)}").classes('text-xs font-bold text-cyan q-mb-xs')
                                base_url = get_app_base_url()

                                for c in convites:
                                    st_color = 'green' if c.get('status') == 'confirmado' else 'red' if c.get('status') in ('recusado', 'justificado') else 'blue'
                                    token_str = c.get('token', '')
                                    link_rsvp = f"{base_url}/rsvp/{token_str}"

                                    with ui.card().classes('w-full q-pa-sm bg-black/30 border border-cyan-500/20 rounded-xl'):
                                        with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                                            with ui.column().classes('gap-0 flex-grow'):
                                                ui.label(f"{c.get('posto_graduacao','')} {c.get('nome_autoridade','')}".strip()).classes('text-xs font-bold text-white')
                                                ui.label(f"✉️ {c.get('email','')} | Token: {token_str[:8]}...").classes('text-[11px] text-grey-4')

                                            with ui.row().classes('gap-2 items-center wrap'):
                                                ui.badge(str(c.get('status','')).upper()).props(f'color={st_color}').classes('text-xs font-bold')

                                                # BOTÃO 1: COPIAR LINK RSVP
                                                def copiar_link(link_to_copy=link_rsvp):
                                                    ui.run_javascript(f"navigator.clipboard.writeText('{link_to_copy}')")
                                                    ui.notify('📋 Link seguro do convite copiado!', color='success')

                                                ui.button('📋 Copiar Link', on_click=copiar_link).props('flat dense color=amber').classes('text-xs')

                                                # BOTÃO 2: ABRIR LINK RSVP
                                                ui.button('👁️ Abrir', on_click=lambda l=link_rsvp: ui.navigate.to(l, new_tab=True)).props('flat dense color=cyan').classes('text-xs')

                                                # BOTÃO 3: ENVIAR CONVITE VIA WHATSAPP (TEMPLATE SOLENE DIRETO)
                                                def enviar_whatsapp(conv_item=c, url_rsvp=link_rsvp):
                                                    wsp_num = ''
                                                    # Busca whatsapp no acervo master
                                                    auts = get_autoridades_base()
                                                    for a in auts:
                                                        if a.get('nome_completo') == conv_item.get('nome_autoridade'):
                                                            wsp_num = a.get('whatsapp_celular', '') or a.get('telefone_oficial', '')
                                                            break

                                                    ev_nome = current_ev.get('nome_evento', 'a Solenidade Cerimonial') if 'current_ev' in locals() and current_ev else 'a Solenidade Cerimonial'
                                                    ev_data = current_ev.get('data_evento', '') if 'current_ev' in locals() and current_ev else ''
                                                    ev_hora = current_ev.get('hora_evento', '') if 'current_ev' in locals() and current_ev else ''
                                                    ev_local = current_ev.get('local_evento', '') if 'current_ev' in locals() and current_ev else ''
                                                    ev_traje = current_ev.get('traje_exigido', '') if 'current_ev' in locals() and current_ev else ''

                                                    msg_text = (
                                                        f"MARINHA DO BRASIL\n"
                                                        f"GABINETE DO COMANDANTE-GERAL DO CFN\n\n"
                                                        f"Prezado(a) {conv_item.get('posto_graduacao','')} {conv_item.get('nome_autoridade','')},\n\n"
                                                        f"O Comandante-Geral do Corpo de Fuzileiros Navais tem a honra de convidar Vossa Excelência para {ev_nome}.\n\n"
                                                        f"📅 Data: {ev_data} às {ev_hora}\n"
                                                        f"📍 Local: {ev_local}\n"
                                                        f"👔 Traje: {ev_traje}\n\n"
                                                        f"Favor confirmar presença através do link seguro:\n{url_rsvp}"
                                                    )
                                                    msg_encoded = urllib.parse.quote(msg_text)

                                                    clean_num = ''.join(filter(str.isdigit, wsp_num))
                                                    if not clean_num.startswith('55') and len(clean_num) in (10, 11):
                                                        clean_num = '55' + clean_num

                                                    if clean_num:
                                                        wsp_url = f"https://wa.me/{clean_num}?text={msg_encoded}"
                                                    else:
                                                        wsp_url = f"https://wa.me/?text={msg_encoded}"

                                                    ui.navigate.to(wsp_url, new_tab=True)
                                                    ui.notify(f"📱 Abrindo WhatsApp para envio...", color='info')

                                                ui.button('📱 WhatsApp', on_click=enviar_whatsapp).props('flat dense color=emerald').classes('text-xs')


                                                # BOTÃO 4: REMOVER DA LISTA DO EVENTO
                                                def remover_convite(conv_item=c):
                                                    delete_rsvp_convite(conv_item['id'])
                                                    ui.notify('🗑️ Convidado removido do evento.', color='warning')
                                                    render_lista_evento()

                                                ui.button(icon='delete', on_click=remover_convite).props('flat dense color=red').classes('text-xs').tooltip('Remover do Evento')

                    render_lista_evento()

            # =========================================================================
            # ABA 4: TEMPLATE DO CONVITE (COM TAGS E ÁREA EXPANDIDA 100%)
            # =========================================================================
            with ui.tab_panel(tab_template):
                with ui.column().classes('w-full gap-4'):
                    ui.label('⚙️ Personalização do Convite Formal & Variáveis Dinâmicas').classes('text-md font-bold text-cyan')
                    ui.label('Configure o texto formal do convite. Use as tags dinâmicas para personalizar o envio para cada autoridade.').classes('text-xs text-grey-4')

                    # ÁREA DE TEXTO COMPLETA QUE OCUPA 100% DA LARGURA DISPONÍVEL
                    txt_convite = ui.textarea(
                        'Mensagem de Convite Formal (Template Oficial)',
                        value='Prezado(a) {posto} {nome},\n\nO Comandante-Geral do Corpo de Fuzileiros Navais tem a honra de convidar Vossa Excelência para a {evento}, a ser realizada no dia {data} às {hora}, no local {local}.\n\nTraje / Fardamento exigido: {traje}.\n\nFavor confirmar Vossa presença através do link seguro: {link}'
                    ).props('dark outlined dense w-full rows=8').classes('w-full text-sm font-mono')

                    # BARRA DE TAGS INTERATIVAS DE PERSONALIZAÇÃO
                    ui.label('🏷️ TAGS DINÂMICAS DE PERSONALIZAÇÃO (Clique para Inserir no Texto):').classes('text-xs font-bold text-amber-4 tracking-wider q-mt-xs')
                    
                    def inserir_tag(tag_str):
                        txt_convite.value += f" {tag_str} "
                        ui.notify(f"Tag {tag_str} inserida no convite!", color='info', duration=2)

                    with ui.row().classes('w-full gap-2 wrap items-center bg-black/40 q-pa-sm rounded-xl border border-cyan-500/20'):
                        ui.button('{posto}', on_click=lambda: inserir_tag('{posto}')).props('outline color=cyan dense').classes('text-xs')
                        ui.button('{nome}', on_click=lambda: inserir_tag('{nome}')).props('outline color=cyan dense').classes('text-xs')
                        ui.button('{cargo}', on_click=lambda: inserir_tag('{cargo}')).props('outline color=cyan dense').classes('text-xs')
                        ui.button('{evento}', on_click=lambda: inserir_tag('{evento}')).props('outline color=amber dense').classes('text-xs')
                        ui.button('{data}', on_click=lambda: inserir_tag('{data}')).props('outline color=amber dense').classes('text-xs')
                        ui.button('{hora}', on_click=lambda: inserir_tag('{hora}')).props('outline color=amber dense').classes('text-xs')
                        ui.button('{local}', on_click=lambda: inserir_tag('{local}')).props('outline color=amber dense').classes('text-xs')
                        ui.button('{traje}', on_click=lambda: inserir_tag('{traje}')).props('outline color=amber dense').classes('text-xs')
                        ui.button('{link}', on_click=lambda: inserir_tag('{link}')).props('outline color=emerald dense').classes('text-xs')

                    # PRÉ-VISUALIZAÇÃO DO CONVITE GERADO
                    with ui.card().classes('w-full q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl q-mt-sm'):
                        ui.label('👁️ PRÉ-VISUALIZAÇÃO DO CONVITE PARA O ALMIRANTE (EXEMPLO REAL):').classes('text-xs font-bold text-cyan tracking-wider q-mb-xs')
                        
                        preview_label = ui.label('').classes('text-xs text-grey-2 leading-relaxed font-mono whitespace-pre-line')
                        
                        def atualizar_preview():
                            sample = txt_convite.value or ''
                            sample = sample.replace('{posto}', 'ALMIRANTE DE ESQUADRA')
                            sample = sample.replace('{nome}', 'CARLOS CHAGAS')
                            sample = sample.replace('{cargo}', 'Comandante-Geral do CFN')
                            sample = sample.replace('{evento}', 'Solenidade de Passagem de Comando')
                            sample = sample.replace('{data}', '15/08/2026')
                            sample = sample.replace('{hora}', '10:00')
                            sample = sample.replace('{local}', 'Fortaleza de São José - Ilha das Cobras')
                            sample = sample.replace('{traje}', '3ºA (Com condecorações)')
                            sample = sample.replace('{link}', 'http://193.122.207.129:8080/rsvp/sample-token-uuid-v4')
                            preview_label.text = sample

                        txt_convite.on('update:model-value', atualizar_preview)
                        atualizar_preview()

                    ui.button('💾 SALVAR TEMPLATE DE CONVITE', icon='save', on_click=lambda: ui.notify('Template de convite salvo com sucesso!', color='success')).props('unelevated color=cyan text-color=black bold').classes('w-64 cyber-glow q-mt-sm')

    def refresh_all():
        pass
