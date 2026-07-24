# modules/comsoc_homologar.py
from datetime import datetime
import json
import urllib.parse
from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection

THEME = theme.colors

def render_page():
    ui.label('⚖️ HOMOLOGAÇÃO & GESTÃO DE PAUTAS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_approver = user_role in ('admin', 'supervisor', 'oficial_gab')
    user_name_guerra = user_data.get('nome_guerra', 'Supervisor').upper()

    def gerar_link_google_calendar(d):
        titulo = urllib.parse.quote(f"COBERTURA COMSOC: {d.get('titulo_evento','')}")
        detalhes = urllib.parse.quote(
            f"Solicitante: {d.get('solicitante_nome','')} ({d.get('setor','')})\n"
            f"Autoridades: {d.get('autoridades','')}\n"
            f"Score de Esforço: {d.get('score_esforco','')}"
        )
        local = urllib.parse.quote(d.get('local_evento',''))
        data_res = d.get('data_evento','').replace('-', '')
        hora_res = d.get('hora_evento','09:00').replace(':', '') + '00'
        dates = f"{data_res}T{hora_res}/{data_res}T{int(hora_res[:4] or 900)+200:04d}00"
        return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo}&dates={dates}&details={detalhes}&location={local}"

    def gerar_link_whatsapp_confirmacao(dem, parecer=""):
        import re
        raw_phone = dem.get('contato', '')
        digits = re.sub(r'\D', '', raw_phone)
        if digits and not digits.startswith('55') and len(digits) in (10, 11):
            digits = '55' + digits
            
        st = dem.get('status', 'pendente')
        if st == 'aprovada':
            st_txt = "✅ APROVADA"
        elif st == 'ajustes':
            st_txt = "⚠️ SOLICITADO AJUSTES"
        else:
            st_txt = "❌ REJEITADA"
        
        msg = (
            f"📋 *COMPROVANTE DE PAUTA & HOMOLOGAÇÃO - COMSOC/CGCFN*\n\n"
            f"Prezado(a) *{dem.get('solicitante_nome','')}*,\n"
            f"Sua solicitação de pauta foi *{st_txt}*.\n\n"
            f"🔹 *Pauta:* {dem.get('titulo_evento','')}\n"
            f"📅 *Data:* {dem.get('data_evento','')} às {dem.get('hora_evento','')}\n"
            f"📍 *Local:* {dem.get('local_evento','')}\n"
            f"📞 *Contato:* {dem.get('contato','')}\n"
        )
        if parecer:
            msg += f"\n✍️ *Parecer da Chefia / COMSOC:*\n_{parecer}_\n"

        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{digits}?text={encoded}" if digits else f"https://wa.me/?text={encoded}", msg

def open_editar_pauta_dialog(demanda, callback_refresh=None):
    if not demanda:
        ui.notify('Pauta inválida.', color='warning')
        return
        
    try:
        raw_cob = demanda.get('tipo_cobertura')
        cob_list = []
        if isinstance(raw_cob, list):
            cob_list = raw_cob
        elif isinstance(raw_cob, str):
            try:
                cob_list = json.loads(raw_cob)
            except Exception:
                cob_list = [s.strip() for s in raw_cob.split(',') if s.strip()]
        if not isinstance(cob_list, list):
            cob_list = []

        with ui.dialog() as edit_dialog, ui.card().classes('w-[680px] max-w-[95vw] q-pa-lg border bg-slate-900 border-cyan-500/40').style('max-height: 90vh; overflow-y: auto;'):
            ui.label(f"✏️ Editar Pauta: {demanda.get('titulo_evento','')}").classes('text-white text-md font-bold cyber-title q-mb-md')
            
            with ui.column().classes('w-full gap-3 text-xs'):
                in_titulo = ui.input('Título do Evento / Pauta', value=str(demanda.get('titulo_evento','') or '')).props('dark outlined dense w-full')
                
                with ui.row().classes('w-full gap-2 no-wrap'):
                    in_solicitante = ui.input('Nome do Solicitante', value=str(demanda.get('solicitante_nome','') or '')).props('dark outlined dense').classes('w-1/2')
                    in_setor = ui.input('Setor / OM', value=str(demanda.get('setor','') or '')).props('dark outlined dense').classes('w-1/2')
                    
                with ui.row().classes('w-full gap-2 no-wrap'):
                    in_contato = ui.input('Telefone / Contato', value=str(demanda.get('contato','') or '')).props('dark outlined dense').classes('w-1/2')
                    in_local = ui.input('Local do Evento', value=str(demanda.get('local_evento','') or '')).props('dark outlined dense').classes('w-1/2')

                with ui.row().classes('w-full gap-2 no-wrap'):
                    in_data_inicio = ui.input('Data Início', value=str(demanda.get('data_evento','') or '')).props('type=date dark outlined dense').classes('w-1/3')
                    in_data_fim = ui.input('Data Término (Opcional)', value=str(demanda.get('data_fim', demanda.get('data_evento','')) or '')).props('type=date dark outlined dense').classes('w-1/3')
                    in_hora = ui.input('Hora', value=str(demanda.get('hora_evento','09:00') or '09:00')).props('type=time dark outlined dense').classes('w-1/3')

                in_autoridades = ui.input('Autoridades Presentes', value=str(demanda.get('autoridades','') or '')).props('dark outlined dense w-full')
                
                st_val = str(demanda.get('status', 'pendente') or 'pendente').lower()
                if st_val not in ('pendente', 'aprovada', 'ajustes', 'concluida', 'rejeitado'):
                    st_val = 'pendente'
                    
                in_status = ui.select(
                    {'pendente': 'Pendente (Aguardando Avaliação)', 'aprovada': 'Aprovada (Na Agenda)', 'ajustes': 'Solicitado Ajustes', 'concluida': 'Concluída', 'rejeitado': 'Rejeitada'},
                    value=st_val,
                    label='Status da Pauta'
                ).props('dark outlined dense w-full option-dark')

                ui.label('📸 Tipos de Serviço Requeridos').classes('text-xs font-bold text-cyan q-mt-xs')
                
                chk_foto = ui.checkbox('Fotografia', value='foto' in cob_list)
                chk_video = ui.checkbox('Vídeo / Filmagem', value='video' in cob_list)
                chk_grafico = ui.checkbox('🎨 Serviço Gráfico / Design', value='grafico' in cob_list)
                chk_drone = ui.checkbox('🚁 Imagens Aéreas / Drone', value='drone' in cob_list)
                chk_redes = ui.checkbox('📱 Mídias Sociais / Reels', value='redes' in cob_list)

                def salvar_edicao():
                    if not in_titulo.value or not in_data_inicio.value or not in_local.value:
                        ui.notify('Título, Data de Início e Local são obrigatórios.', color='warning')
                        return
                    
                    cobs = []
                    if chk_foto.value: cobs.append('foto')
                    if chk_video.value: cobs.append('video')
                    if chk_grafico.value: cobs.append('grafico')
                    if chk_drone.value: cobs.append('drone')
                    if chk_redes.value: cobs.append('redes')

                    db = get_service_db_connection() or get_db_connection()
                    if db:
                        try:
                            update_payload = {
                                'titulo_evento': in_titulo.value.strip(),
                                'solicitante_nome': in_solicitante.value.strip(),
                                'setor': in_setor.value.strip(),
                                'contato': in_contato.value.strip(),
                                'local_evento': in_local.value.strip(),
                                'data_evento': in_data_inicio.value,
                                'data_fim': in_data_fim.value or in_data_inicio.value,
                                'hora_evento': in_hora.value or '09:00',
                                'autoridades': in_autoridades.value.strip(),
                                'status': in_status.value,
                                'tipo_cobertura': json.dumps(cobs)
                            }
                            db.table('demandas_comunicacao').update(update_payload).eq('id', demanda['id']).execute()
                            ui.notify('✅ Pauta editada e salva com sucesso!', color='positive')
                            edit_dialog.close()
                            if callback_refresh:
                                callback_refresh()
                        except Exception as e_save:
                            ui.notify(f'Erro ao editar pauta: {e_save}', color='negative')

                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                    ui.button('Cancelar', on_click=edit_dialog.close).props('flat color=grey')
                    ui.button('💾 Salvar Alterações', on_click=salvar_edicao).props('unelevated color=green text-color=white bold')
                    
        edit_dialog.open()
    except Exception as err_dlg:
        print(f"[EDIT PAUTA DIALOG ERR] {err_dlg}")
        ui.notify(f"Erro ao abrir modal de edição: {err_dlg}", color="negative")

    def open_tramitar_dialog(demanda, callback_refresh=None):
        efetivo_options = {}
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                res_ef = db.table('efetivo').select('id, nome_guerra, role').execute()
                if res_ef.data:
                    efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
            except Exception as e:
                print(f"[EFETIVO LOAD ERR] {e}")

        # Carrega histórico específico da demanda
        historico_demanda = []
        if db:
            try:
                res_h = db.table('demandas_historico_tramitacao').select('*').eq('demanda_id', demanda['id']).order('data_hora', desc=True).execute()
                historico_demanda = res_h.data or []
            except Exception as e:
                print(f"[HIST DEMANDA ERR] {e}")

        with ui.dialog() as tramitar_dialog, ui.card().classes('w-[620px] max-w-[95vw] q-pa-lg border').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius: 16px; max-height: 90vh; overflow-y: auto;'
        ):
            with ui.column().classes('w-full gap-4'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(f"⚖️ {demanda['titulo_evento']}").classes('text-white text-md font-bold cyber-title')
                        ui.button('✏️ Editar Pauta', on_click=lambda: (tramitar_dialog.close(), open_editar_pauta_dialog(demanda, callback_refresh))).props('flat color=cyan dense icon=edit').classes('text-xs')
                    ui.badge(demanda.get('status','pendente').upper()).props('color=cyan').classes('text-xs')

                # Dados completos da Pauta
                with ui.card().classes('w-full q-pa-md no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(0,229,255,0.1);'):
                    with ui.grid(columns=2).classes('w-full gap-2 text-xs'):
                        ui.label(f"👤 Solicitante: {demanda['solicitante_nome']}").classes('text-grey-3 font-bold')
                        ui.label(f"🏢 OM/Setor: {demanda['setor']}").classes('text-grey-3')
                        ui.label(f"📅 Data/Hora: {demanda['data_evento']} às {demanda['hora_evento']}").classes('text-grey-3')
                        ui.label(f"📍 Local: {demanda['local_evento']}").classes('text-grey-3')
                        ui.label(f"📞 Contato: {demanda.get('contato','N/I')}").classes('text-grey-3')
                        ui.label(f"👑 Autoridades: {demanda.get('autoridades','Nenhuma')}").classes('text-grey-3')

                    score = demanda.get('score_esforco', 1.0)
                    s_color = "green" if score <= 2.0 else "orange" if score <= 3.5 else "red"
                    ui.badge(f"Score de Esforço Técnico: {score}").props(f"color={s_color}").classes('q-mt-sm text-xs')

                # Histórico desta pauta especificamente
                if historico_demanda:
                    ui.label('📜 Histórico de Tramitações desta Pauta:').classes('text-xs font-bold text-cyan q-mt-xs')
                    with ui.column().classes('w-full gap-1'):
                        for h in historico_demanda:
                            with ui.row().classes('w-full justify-between items-center text-[10px] bg-slate-800/40 p-2 rounded'):
                                ui.label(f"• {h['acao']} ({h['usuario']})").classes('text-cyan font-bold')
                                ui.label(h['data_hora'][:16].replace('T', ' ')).classes('text-grey-4')
                                if h.get('parecer'):
                                    ui.label(f'"{h["parecer"]}"').classes('w-full text-grey-3 italic text-[10.5px]')

                if is_approver:
                    ui.separator().style('background: rgba(0, 229, 255, 0.1);')
                    parecer_input = ui.textarea('Parecer / Observações da Chefia').props('dark outlined w-full rows=3').classes('text-xs')
                    
                    encarregado_select = ui.select(
                        efetivo_options,
                        label='Encarregado / Supervisor da Missão'
                    ).props('dark outlined dense w-full option-dark').classes('w-full')
                    
                    error_lbl = ui.label('').classes('text-xs text-red-400 w-full text-center font-bold')

                    def submeter_tramitacao(novo_status, acao_nome):
                        if not parecer_input.value:
                            error_lbl.text = "⚠️ É necessário registrar o parecer/despacho antes de tramitar."
                            return
                        
                        if novo_status == 'aprovada' and not encarregado_select.value:
                            error_lbl.text = "⚠️ É necessário definir o Encarregado da Missão para aprovar."
                            return
                            
                        db = get_db_connection()
                        if db:
                            try:
                                hist = {
                                    'demanda_id': demanda['id'],
                                    'data_hora': datetime.now().isoformat(),
                                    'usuario': user_name_guerra,
                                    'acao': acao_nome,
                                    'parecer': parecer_input.value
                                }
                                db.table('demandas_historico_tramitacao').insert(hist).execute()
                                
                                update_data = {'status': novo_status}
                                if encarregado_select.value:
                                    update_data['encarregado_id'] = encarregado_select.value
                                db.table('demandas_comunicacao').update(update_data).eq('id', demanda['id']).execute()
                                demanda['status'] = novo_status
                                
                                try:
                                    from notifications_manager import notify_telegram
                                    militar_ids = []
                                    if de_ids := demanda.get('notificar_militar_ids'):
                                        militar_ids = json.loads(de_ids)
                                    
                                    if encarregado_select.value:
                                        militar_ids.append(encarregado_select.value)
                                    
                                    enc_name = efetivo_options.get(encarregado_select.value, "N/I") if encarregado_select.value else "Nenhum"
                                    alert_txt = (
                                        f"🔔 **ATUALIZAÇÃO DE PAUTA COMSOC**\n\n"
                                        f"📌 Pauta: {demanda['titulo_evento']}\n"
                                        f"⚡ Status: `{novo_status.upper()}` ({acao_nome})\n"
                                        f"👤 Encarregado da Missão: {enc_name}\n"
                                        f"✍️ Parecer: {parecer_input.value}\n"
                                        f"⚙️ Por: {user_name_guerra}"
                                    )
                                    
                                    if militar_ids:
                                        militar_ids = list(set(militar_ids))
                                        # Registra no histórico de fainas para o novo relatório de missões executadas
                                        for m_id in militar_ids:
                                            try:
                                                payload_faina = {
                                                    'demanda_id': demanda_id,
                                                    'militar_id': str(m_id),
                                                    'nome_guerra': str(m_id),
                                                    'titulo_evento': demanda.get('titulo_evento', ''),
                                                    'data_evento': demanda.get('data_evento', ''),
                                                    'status': novo_status,
                                                    'tipo_servico': str(demanda.get('tipo_cobertura', '')),
                                                    'created_at': datetime.now().isoformat()
                                                }
                                                if db:
                                                    db.table('fainas_historico_militares').insert(payload_faina).execute()
                                                from sqlite_adapter import SQLiteDatabaseAdapter
                                                local_db = SQLiteDatabaseAdapter()
                                                local_db.table('fainas_historico_militares').insert(payload_faina).execute()
                                            except Exception as faina_err:
                                                print(f"[FAINA SAVE WARN] {faina_err}")

                                        if db:
                                            res_ef = db.table('efetivo').select('telegram_id').in_('id', militar_ids).execute()
                                            if res_ef.data:
                                                for m in res_ef.data:
                                                    if tel_id := m.get('telegram_id'):
                                                        notify_telegram(alert_txt, "pauta", custom_chat_id=tel_id)
                                except Exception as e_notif:
                                    print(f"[TRAMITAR NOTIFY ERR] {e_notif}")
                                
                                ui.notify(f"Demanda tramitada: {acao_nome}", color='success')
                                tramitar_dialog.close()
                                if callback_refresh:
                                    callback_refresh()
                            except Exception as e:
                                error_lbl.text = f"Erro na gravação: {e}"

                    # Botões principais de decisão
                    with ui.row().classes('w-full justify-between gap-3 q-mt-xs no-wrap'):
                        ui.button('Rejeitar', on_click=lambda: submeter_tramitacao('rejeitado', 'Demanda Rejeitada')).props('unelevated color=red text-color=white bold').classes('col q-py-sm rounded-lg')
                        ui.button('Pedir Ajustes', on_click=lambda: submeter_tramitacao('ajustes', 'Solicitado Ajustes')).props('unelevated color=orange text-color=black bold').classes('col q-py-sm rounded-lg')
                        ui.button('Aprovar', on_click=lambda: submeter_tramitacao('aprovada', 'Demanda Aprovada')).props('unelevated color=green text-color=white bold').classes('col q-py-sm rounded-lg')
                        
                ui.separator().style('background: rgba(0, 229, 255, 0.1); margin: 8px 0;')

                # Ações rápidas de envio/resumo
                with ui.row().classes('w-full justify-between gap-2 items-center'):
                    wa_url, raw_text_confirm = gerar_link_whatsapp_confirmacao(demanda)
                    ui.link('📱 Enviar Resumo via WhatsApp', target=wa_url, new_tab=True).classes('text-xs font-bold text-green-4 hover:underline')
                    
                    def copiar_resumo():
                        _, txt = gerar_link_whatsapp_confirmacao(demanda, parecer_input.value if is_approver and parecer_input and parecer_input.value else "")
                        ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(txt)})')
                        ui.notify('📋 Comprovante de Pauta copiado com sucesso!', color='positive')

                    ui.button('📋 Copiar Comprovante', on_click=copiar_resumo).props('flat color=cyan dense').classes('text-xs')

                ui.button('Fechar', on_click=tramitar_dialog.close).props('flat color=grey').classes('w-full q-mt-xs text-xs bold')
        tramitar_dialog.open()

    # --------------------------------------------------------------------------
    # PAINEL PRINCIPAL COM ABAS POR STATUS
    # --------------------------------------------------------------------------
    @ui.refreshable
    def render_content():
        db = get_service_db_connection() or get_db_connection()
        todas_demandas = []
        historico_global = []
        if db:
            try:
                res_d = db.table('demandas_comunicacao').select('*').order('id', desc=True).execute()
                todas_demandas = res_d.data or []
            except Exception as e:
                print(f"[LOAD DEMANDAS ERR] {e}")
            try:
                res_h = db.table('demandas_historico_tramitacao').select('*').order('data_hora', desc=True).execute()
                historico_global = res_h.data or []
            except Exception as e:
                print(f"[LOAD HISTORICO ERR] {e}")

        # Fallback local via SQLite se o Supabase estiver offline ou sem retorno
        if not todas_demandas:
            try:
                from sqlite_adapter import SQLiteDatabaseAdapter
                local_db = SQLiteDatabaseAdapter()
                res_d_loc = local_db.table('demandas_comunicacao').select('*').order('id', desc=True).execute()
                todas_demandas = res_d_loc.data or []
                res_h_loc = local_db.table('demandas_historico_tramitacao').select('*').order('data_hora', desc=True).execute()
                historico_global = res_h_loc.data or []
            except Exception as loc_e:
                print(f"[LOAD HOMOLOGAR LOCAL WARN] {loc_e}")

        # Agrupamento por status
        pendentes  = [d for d in todas_demandas if d.get('status') == 'pendente']
        aprovadas  = [d for d in todas_demandas if d.get('status') == 'aprovada']
        ajustes    = [d for d in todas_demandas if d.get('status') == 'ajustes']
        concluidas = [d for d in todas_demandas if d.get('status') == 'concluida']
        rejeitadas = [d for d in todas_demandas if d.get('status') == 'rejeitado']

        with ui.tabs().classes('w-full text-cyan flex-wrap border-b border-cyan/20') as tabs:
            tab_pend = ui.tab(f'⏳ Pendentes ({len(pendentes)})')
            tab_aprov = ui.tab(f'🟢 Aprovadas ({len(aprovadas)})')
            tab_ajust = ui.tab(f'⚠️ Ajustes ({len(ajustes)})')
            tab_concl = ui.tab(f'✅ Concluídas ({len(concluidas)})')
            tab_rej = ui.tab(f'❌ Rejeitadas ({len(rejeitadas)})')
            tab_hist = ui.tab(f'📜 Linha do Tempo Global ({len(historico_global)})')

        with ui.tab_panels(tabs, value=tab_pend).classes('w-full bg-transparent no-shadow q-pa-none q-mt-md'):
            
            # --- ABA 1: PENDENTES ---
            with ui.tab_panel(tab_pend):
                if pendentes:
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for d in pendentes:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(0,229,255,0.03); border: 1px solid rgba(0,229,255,0.2);'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(d['titulo_evento']).classes('text-sm font-bold text-white cyber-title')
                                    score = d.get('score_esforco', 1.0)
                                    color = "green" if score <= 2.0 else "orange" if score <= 3.5 else "red"
                                    ui.badge(f"Esforço: {score}").props(f"color={color}").classes('text-[9px]')

                                ui.separator().style('background: rgba(255,255,255,0.05); margin: 6px 0;')
                                ui.label(f"👤 Solicitante: {d['solicitante_nome']} ({d['setor']})").classes('text-xs text-grey-3')
                                ui.label(f"📅 Data: {d['data_evento']} às {d['hora_evento']}").classes('text-xs text-grey-3')
                                ui.label(f"📍 Local: {d['local_evento']}").classes('text-xs text-grey-3')

                                with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                    ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                    ui.button('⚖️ Analisar & Tramitar', on_click=lambda d=d: open_tramitar_dialog(d, render_content.refresh)).props('unelevated color=primary text-color=black dense bold').classes('text-xs q-px-sm')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('check_circle', size='3rem', color='green')
                        ui.label('Nenhuma pauta pendente no momento.').classes('text-xs')

            # --- ABA 2: APROVADAS ---
            with ui.tab_panel(tab_aprov):
                if aprovadas:
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for d in aprovadas:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(76,175,80,0.04); border: 1px solid rgba(76,175,80,0.3);'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(d['titulo_evento']).classes('text-sm font-bold text-white cyber-title')
                                    ui.badge('APROVADA').props('color=green').classes('text-[9px]')

                                ui.separator().style('background: rgba(255,255,255,0.05); margin: 6px 0;')
                                ui.label(f"👤 Solicitante: {d['solicitante_nome']} ({d['setor']})").classes('text-xs text-grey-3')
                                ui.label(f"📅 Data: {d['data_evento']} às {d['hora_evento']}").classes('text-xs text-grey-3')
                                ui.label(f"📍 Local: {d['local_evento']}").classes('text-xs text-grey-3')

                                with ui.row().classes('w-full justify-between items-center q-mt-sm'):
                                    cal_url = gerar_link_google_calendar(d)
                                    ui.link('📅 Add Calendar', target=cal_url, new_tab=True).classes('text-xs text-cyan hover:underline font-bold')
                                    
                                    def concluir_pauta(dem_id=d['id']):
                                        db_c = get_db_connection()
                                        if db_c:
                                            db_c.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                                            ui.notify('✅ Pauta concluída com sucesso!', color='positive')
                                            render_content.refresh()

                                    with ui.row().classes('items-center gap-1'):
                                        ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                        ui.button('Concluir', on_click=concluir_pauta).props('flat color=green dense').classes('text-xs')
                                        ui.button('Detalhes', on_click=lambda d=d: open_tramitar_dialog(d, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('event_available', size='3rem')
                        ui.label('Nenhuma pauta aprovada em andamento.').classes('text-xs')

            # --- ABA 3: AJUSTES SOLICITADOS ---
            with ui.tab_panel(tab_ajust):
                if ajustes:
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for d in ajustes:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(255,152,0,0.04); border: 1px solid rgba(255,152,0,0.3);'):
                                ui.label(d['titulo_evento']).classes('text-sm font-bold text-white cyber-title')
                                ui.label(f"De: {d['solicitante_nome']} ({d['setor']})").classes('text-xs text-grey-3')
                                ui.label(f"📅 Data: {d['data_evento']} às {d['hora_evento']}").classes('text-xs text-grey-3')
                                ui.badge('AGUARDANDO CORREÇÃO DO SOLICITANTE').props('color=orange').classes('text-[9px] q-mt-xs')

                                with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                    ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                    ui.button('Ver Detalhes', on_click=lambda d=d: open_tramitar_dialog(d, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('thumb_up', size='3rem')
                        ui.label('Nenhuma pauta aguardando ajustes.').classes('text-xs')

            # --- ABA 4: CONCLUÍDAS ---
            with ui.tab_panel(tab_concl):
                if concluidas:
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for d in concluidas:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1);'):
                                ui.label(d['titulo_evento']).classes('text-sm font-bold text-white cyber-title')
                                ui.label(f"De: {d['solicitante_nome']} ({d['setor']})").classes('text-xs text-grey-3')
                                ui.label(f"📅 Concluído em: {d['data_evento']}").classes('text-xs text-grey-4')
                                ui.badge('CONCLUÍDA').props('color=grey-7').classes('text-[9px] q-mt-xs')

                                with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                    ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                    ui.button('Ver Histórico', on_click=lambda d=d: open_tramitar_dialog(d, render_content.refresh)).props('flat color=grey dense').classes('text-xs')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('task_alt', size='3rem')
                        ui.label('Nenhuma pauta concluída registrada.').classes('text-xs')

            # --- ABA 5: REJEITADAS ---
            with ui.tab_panel(tab_rej):
                if rejeitadas:
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for d in rejeitadas:
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(244,67,54,0.04); border: 1px solid rgba(244,67,54,0.3);'):
                                ui.label(d['titulo_evento']).classes('text-sm font-bold text-white cyber-title')
                                ui.label(f"De: {d['solicitante_nome']} ({d['setor']})").classes('text-xs text-grey-3')
                                ui.badge('INDEFERIDA').props('color=red').classes('text-[9px] q-mt-xs')

                                with ui.row().classes('w-full justify-end q-mt-sm'):
                                    ui.button('Ver Motivo / Parecer', on_click=lambda d=d: open_tramitar_dialog(d, render_content.refresh)).props('flat color=red dense').classes('text-xs')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('block', size='3rem')
                        ui.label('Nenhuma pauta indeferida.').classes('text-xs')

            # --- ABA 6: LINHA DO TEMPO GLOBAL ---
            with ui.tab_panel(tab_hist):
                if historico_global:
                    with ui.column().classes('w-full gap-3'):
                        for h in historico_global:
                            with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03);'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(h['acao']).classes('text-xs font-bold text-cyan')
                                    ui.label(h['data_hora'][:16].replace('T', ' ')).classes('text-[9px] text-grey font-mono')
                                ui.label(h.get('parecer','')).classes('text-[11px] text-grey-3 q-mt-xs')
                                ui.label(f"Por: {h.get('usuario','Supervisor')}").classes('text-[9px] text-grey font-bold')
                else:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('history', size='3rem')
                        ui.label('Nenhum registro de histórico encontrado.').classes('text-xs')

    render_content()


