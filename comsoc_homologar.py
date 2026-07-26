# modules/comsoc_homologar.py
from datetime import datetime
import json
import urllib.parse
from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection

THEME = theme.colors

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
                    in_categoria = ui.select(
                        {
                            'design_arte': '🎨 Design / Arte Visual',
                            'impressos_albuns': '📕 Impressos & Encadernação',
                            'brindes_lembrancas': '🎁 Brindes & Lembranças',
                            'audiovisual': '📸 Cobertura Audiovisual',
                            'redacao_textos': '✍️ Redação & Discursos',
                            'suporte_evento': '📦 Suporte Logístico / Receptivo',
                            'outra_tarefa': '⚡ Outra Tarefa Especial'
                        },
                        value=demanda.get('categoria_demanda', 'design_arte'),
                        label='Categoria da Demanda'
                    ).props('dark outlined dense option-dark').classes('w-1/2')
                    
                    in_produto = ui.input('Especificação do Produto / Peça', value=str(demanda.get('produto_especifico','') or '')).props('dark outlined dense').classes('w-1/2')
                
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
                if st_val not in ('pendente', 'aprovada', 'aprovado', 'ajustes', 'concluida', 'rejeitado', 'rejeitada'):
                    st_val = 'pendente'
                if st_val in ('aprovado', 'aprovada'):
                    st_val = 'aprovada'
                elif st_val in ('rejeitado', 'rejeitada'):
                    st_val = 'rejeitado'
                    
                in_status = ui.select(
                    {'pendente': 'Pendente (Aguardando Avaliação)', 'aprovada': 'Aprovada (Na Agenda)', 'ajustes': 'Solicitado Ajustes', 'concluida': 'Concluída', 'rejeitado': 'Rejeitada'},
                    value=st_val,
                    label='Status da Pauta'
                ).props('dark outlined dense w-full option-dark')

                 # Carrega opções do efetivo para designação de militares
                efetivo_options = {}
                db_ef = get_service_db_connection() or get_db_connection()
                if db_ef:
                    try:
                        res_ef = db_ef.table('efetivo').select('id, nome_guerra, role').execute()
                        if res_ef.data:
                            efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
                    except Exception as e_ef:
                        print(f"[EFETIVO LOAD ERR] {e_ef}")

                # Deduz designer_id a partir de notificar_militar_ids
                mids_str = demanda.get('notificar_militar_ids') or '[]'
                try:
                    mids = json.loads(mids_str)
                    if isinstance(mids, str):
                        mids = json.loads(mids)
                    if not isinstance(mids, list):
                        mids = []
                except Exception:
                    mids = []
                
                enc_id = demanda.get('encarregado_id')
                des_id = None
                for mid in mids:
                    if enc_id is None or str(mid) != str(enc_id):
                        des_id = mid
                        break

                ui.label('🎖️ Designação de Equipe Operacional / Criativa').classes('text-xs font-bold text-cyan q-mt-xs')
                with ui.row().classes('w-full gap-2 no-wrap'):
                    encarregado_select = ui.select(
                        efetivo_options,
                        value=demanda.get('encarregado_id'),
                        label='👤 Encarregado da Missão'
                    ).props('dark outlined dense option-dark').classes('w-1/2')

                    designer_select = ui.select(
                        efetivo_options,
                        value=des_id,
                        label='🎨 Militar Designado (Arte / Design)'
                    ).props('dark outlined dense option-dark').classes('w-1/2')

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
                            militar_ids = []
                            if encarregado_select.value:
                                militar_ids.append(encarregado_select.value)
                            if designer_select.value:
                                militar_ids.append(designer_select.value)

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
                                'categoria_demanda': in_categoria.value,
                                'produto_especifico': in_produto.value.strip(),
                                'encarregado_id': encarregado_select.value,
                                'notificar_militar_ids': json.dumps(list(set(militar_ids))),
                                'tipo_cobertura': json.dumps(cobs)
                            }
                            dem_id = demanda['id']
                            if isinstance(dem_id, str) and dem_id.isdigit():
                                dem_id = int(dem_id)
                            res = db.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                            print(f"[EDIT PAUTA SAVE RES] ID: {dem_id}, data: {res.data if hasattr(res, 'data') else res}")
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


def open_tramitar_dialog(demanda, user_name_guerra="SUPERVISOR", is_approver=True, callback_refresh=None):
    efetivo_options = {}
    db = get_service_db_connection() or get_db_connection()
    if db:
        try:
            res_ef = db.table('efetivo').select('id, nome_guerra, role').execute()
            if res_ef.data:
                efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
        except Exception as e:
            print(f"[EFETIVO LOAD ERR] {e}")

    with ui.dialog() as tramitar_dialog, ui.card().classes('w-[620px] max-w-[95vw] q-pa-lg border').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius: 16px; max-height: 90vh; overflow-y: auto;'
    ):
        ui.label(f"⚖️ Tramitação & Parecer: {demanda.get('titulo_evento','')}").classes('text-white text-md font-bold cyber-title q-mb-xs')
        ui.label(f"Solicitante: {demanda.get('solicitante_nome','')} ({demanda.get('setor','')})").classes('text-xs text-grey-4 q-mb-md')
        
        # Deduz designer_id a partir de notificar_militar_ids
        mids_str = demanda.get('notificar_militar_ids') or '[]'
        try:
            mids = json.loads(mids_str)
            if isinstance(mids, str):
                mids = json.loads(mids)
            if not isinstance(mids, list):
                mids = []
        except Exception:
            mids = []
        
        enc_id = demanda.get('encarregado_id')
        des_id = None
        for mid in mids:
            if enc_id is None or str(mid) != str(enc_id):
                des_id = mid
                break

        with ui.column().classes('w-full gap-3 text-xs'):
            with ui.row().classes('w-full gap-2 no-wrap'):
                encarregado_select = ui.select(
                    efetivo_options,
                    value=demanda.get('encarregado_id'),
                    label='👤 Encarregado da Missão'
                ).props('dark outlined dense option-dark').classes('w-1/2')

                designer_select = ui.select(
                    efetivo_options,
                    value=des_id,
                    label='🎨 Militar Designado (Arte / Design)'
                ).props('dark outlined dense option-dark').classes('w-1/2')
            
            parecer_input = ui.textarea('✍️ Parecer da Chefia / Despacho', placeholder='Digite o parecer ou instruções...').props('dark outlined dense w-full rows=3')
            error_lbl = ui.label('').classes('text-xs text-red font-bold')

            def submeter_tramitacao(novo_status, acao_nome):
                if not encarregado_select.value and novo_status == 'aprovada':
                    error_lbl.text = "⚠️ É necessário definir o Encarregado da Missão para aprovar."
                    return
                    
                db = get_service_db_connection() or get_db_connection()
                if db:
                    try:
                        hist = {
                            'demanda_id': demanda['id'],
                            'data_hora': datetime.now().isoformat(),
                            'usuario': user_name_guerra,
                            'acao': acao_nome,
                            'parecer': parecer_input.value or ''
                        }
                        try:
                            db.table('demandas_historico_tramitacao').insert(hist).execute()
                        except Exception as h_err:
                            print(f"[HIST INSERT ERR] {h_err}")
                        
                        militar_ids = []
                        if encarregado_select.value:
                            militar_ids.append(encarregado_select.value)
                        if designer_select.value:
                            militar_ids.append(designer_select.value)

                        update_data = {
                            'status': novo_status,
                            'notificar_militar_ids': json.dumps(list(set(militar_ids)))
                        }
                        if encarregado_select.value:
                            update_data['encarregado_id'] = encarregado_select.value

                        dem_id = demanda['id']
                        if isinstance(dem_id, str) and dem_id.isdigit():
                            dem_id = int(dem_id)

                        db.table('demandas_comunicacao').update(update_data).eq('id', dem_id).execute()
                        demanda['status'] = novo_status
                        
                        ui.notify(f"Demanda tramitada: {acao_nome}", color='success')
                        tramitar_dialog.close()
                        if callback_refresh:
                            callback_refresh()
                    except Exception as e:
                        error_lbl.text = f"Erro na gravação: {e}"

            with ui.row().classes('w-full justify-between gap-3 q-mt-xs no-wrap'):
                ui.button('Rejeitar', on_click=lambda: submeter_tramitacao('rejeitado', 'Demanda Rejeitada')).props('unelevated color=red text-color=white bold').classes('col q-py-sm rounded-lg')
                ui.button('Pedir Ajustes', on_click=lambda: submeter_tramitacao('ajustes', 'Solicitado Ajustes')).props('unelevated color=orange text-color=black bold').classes('col q-py-sm rounded-lg')
                ui.button('Aprovar', on_click=lambda: submeter_tramitacao('aprovada', 'Demanda Aprovada')).props('unelevated color=green text-color=white bold').classes('col q-py-sm rounded-lg')

        ui.button('Fechar', on_click=tramitar_dialog.close).props('flat color=grey').classes('w-full q-mt-md text-xs bold')
    tramitar_dialog.open()


def render_page():
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_approver = user_role in ('admin', 'supervisor', 'oficial_gab', 'comsoc')
    user_name_guerra = str(user_data.get('nome_guerra', 'Supervisor')).upper()

    with ui.column().classes('w-full q-pa-md gap-4'):
        with ui.row().classes('w-full justify-between items-center bg-slate-900/60 q-pa-md rounded-xl border border-cyan-500/20'):
            with ui.column().classes('gap-0'):
                ui.label('⚖️ HOMOLOGAÇÃO & GESTÃO DE PAUTAS').classes('text-xl font-bold text-white cyber-title')
                ui.label('Painel de Acompanhamento, Parecer e Homologação de Coberturas COMSOC').classes('text-xs text-grey-4')
            
            ui.button('🔄 Recarregar Dados', on_click=lambda: render_content.refresh()).props('unelevated color=cyan text-color=black dense bold icon=refresh').classes('text-xs')

        @ui.refreshable
        def render_content():
            db = get_service_db_connection() or get_db_connection()
            todas_demandas = []
            historico_global = []

            if db:
                try:
                    res_d = db.table('demandas_comunicacao').select('*').order('id', desc=True).execute()
                    if res_d and hasattr(res_d, 'data') and res_d.data:
                        todas_demandas = [d for d in res_d.data if isinstance(d, dict)]
                except Exception as e:
                    print(f"[LOAD DEMANDAS ERR] {e}")

                try:
                    res_h = db.table('demandas_historico_tramitacao').select('*').order('data_hora', desc=True).execute()
                    if res_h and hasattr(res_h, 'data') and res_h.data:
                        historico_global = [h for h in res_h.data if isinstance(h, dict)]
                except Exception as e:
                    print(f"[LOAD HISTORICO ERR] {e}")

            pendentes  = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('pendente', 'pendentes')]
            aprovadas  = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas')]
            ajustes    = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('ajustes', 'ajuste')]
            concluidas = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('concluida', 'concluída', 'concluido', 'concluído')]
            rejeitadas = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('rejeitado', 'rejeitada', 'indeferida', 'indeferido')]

            # Seleciona a aba inicial inteligente: se não tiver pendente, abre Aprovadas diretamente
            initial_tab_value = 'pendentes' if len(pendentes) > 0 else 'aprovadas'

            with ui.tabs().classes('w-full text-cyan flex-wrap border-b border-cyan/20') as tabs:
                tab_pend = ui.tab(f'⏳ Pendentes ({len(pendentes)})')
                tab_aprov = ui.tab(f'🟢 Aprovadas ({len(aprovadas)})')
                tab_ajust = ui.tab(f'⚠️ Ajustes ({len(ajustes)})')
                tab_concl = ui.tab(f'✅ Concluídas ({len(concluidas)})')
                tab_rej = ui.tab(f'❌ Rejeitadas ({len(rejeitadas)})')
                tab_hist = ui.tab(f'📜 Histórico Global ({len(historico_global)})')

            initial_tab = tab_pend if len(pendentes) > 0 else tab_aprov

            with ui.tab_panels(tabs, value=initial_tab).classes('w-full bg-transparent no-shadow q-pa-none q-mt-md'):
                
                # --- ABA PENDENTES ---
                with ui.tab_panel(tab_pend):
                    if pendentes:
                        with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                            for d in pendentes:
                                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(0,229,255,0.03); border: 1px solid rgba(0,229,255,0.2);'):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label(d.get('titulo_evento', 'Pauta sem título')).classes('text-sm font-bold text-white cyber-title')
                                        score = d.get('score_esforco', 1.0)
                                        color = "green" if score <= 2.0 else "orange" if score <= 3.5 else "red"
                                        ui.badge(f"Esforço: {score}").props(f"color={color}").classes('text-[9px]')

                                    # Dedução inteligente de categoria e produto caso estejam vazios ou padrão
                                    cat_val = str(d.get('categoria_demanda') or 'design_arte').strip().lower()
                                    cob_val = d.get('tipo_cobertura') or '[]'
                                    try:
                                        cobs = json.loads(cob_val) if isinstance(cob_val, str) else cob_val
                                        if not isinstance(cobs, list):
                                            cobs = []
                                    except Exception:
                                        cobs = []
                                        
                                    if cobs and cat_val == 'design_arte':
                                        cat_val = 'audiovisual'
                                        
                                    cat_nome = '📸 Cobertura Audiovisual' if cat_val == 'audiovisual' else cat_val.replace('_', ' ').title()
                                    
                                    with ui.row().classes('items-center gap-2 q-mt-xs wrap'):
                                        # Badge da Categoria
                                        ui.badge(f"📌 {cat_nome}").props('color=amber-9 text-color=black bold').classes('text-xs q-py-xs q-px-sm')
                                        
                                        # Se houver especificação de produto manual
                                        prod_manual = d.get('produto_especifico') or ''
                                        if prod_manual:
                                            ui.badge(f"🎯 {prod_manual}").props('color=blue-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')
                                        
                                        # Badges individuais para cada serviço/cobertura selecionada
                                        for cob in cobs:
                                            if cob == 'foto':
                                                ui.badge('📸 Fotografia').props('color=cyan-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')
                                            elif cob == 'video':
                                                ui.badge('🎥 Vídeo / Filmagem').props('color=teal-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')
                                            elif cob == 'grafico':
                                                ui.badge('🎨 Design / Arte').props('color=purple-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')
                                            elif cob == 'drone':
                                                ui.badge('🚁 Imagens Aéreas').props('color=orange-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')
                                            elif cob == 'redes':
                                                ui.badge('📱 Mídias Sociais').props('color=pink-9 text-color=white bold').classes('text-xs q-py-xs q-px-sm')

                                    ui.separator().style('background: rgba(255,255,255,0.05); margin: 6px 0;')
                                    ui.label(f"👤 Solicitante: {d.get('solicitante_nome', 'N/I')} ({d.get('setor', 'CGCFN')})").classes('text-xs text-grey-3')
                                    ui.label(f"📅 Data: {d.get('data_evento', 'N/I')} às {d.get('hora_evento', '09:00')}").classes('text-xs text-grey-3')
                                    ui.label(f"📍 Local: {d.get('local_evento', 'N/I')}").classes('text-xs text-grey-3')

                                    with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                        ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                        ui.button('⚖️ Analisar & Tramitar', on_click=lambda d=d: open_tramitar_dialog(d, user_name_guerra, is_approver, render_content.refresh)).props('unelevated color=primary text-color=black dense bold').classes('text-xs q-px-sm')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('check_circle', size='3rem', color='green')
                            ui.label('Nenhuma pauta pendente de homologação.').classes('text-xs')

                # --- ABA APROVADAS ---
                with ui.tab_panel(tab_aprov):
                    if aprovadas:
                        with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                            for d in aprovadas:
                                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(76,175,80,0.04); border: 1px solid rgba(76,175,80,0.3);'):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label(d.get('titulo_evento', 'Pauta sem título')).classes('text-sm font-bold text-white cyber-title')
                                        ui.badge('APROVADA').props('color=green').classes('text-[9px]')

                                    ui.separator().style('background: rgba(255,255,255,0.05); margin: 6px 0;')
                                    ui.label(f"👤 Solicitante: {d.get('solicitante_nome', 'N/I')} ({d.get('setor', 'CGCFN')})").classes('text-xs text-grey-3')
                                    ui.label(f"📅 Data: {d.get('data_evento', 'N/I')} às {d.get('hora_evento', '09:00')}").classes('text-xs text-grey-3')
                                    ui.label(f"📍 Local: {d.get('local_evento', 'N/I')}").classes('text-xs text-grey-3')

                                    def concluir_pauta(dem_id=d.get('id')):
                                        if dem_id:
                                            db_c = get_service_db_connection() or get_db_connection()
                                            if db_c:
                                                db_c.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                                                ui.notify('✅ Pauta concluída com sucesso!', color='positive')
                                                render_content.refresh()

                                    with ui.row().classes('w-full justify-end items-center gap-1 q-mt-sm'):
                                        ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                        ui.button('Concluir', on_click=concluir_pauta).props('flat color=green dense').classes('text-xs')
                                        ui.button('Detalhes', on_click=lambda d=d: open_tramitar_dialog(d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('event_available', size='3rem')
                            ui.label('Nenhuma pauta aprovada em andamento.').classes('text-xs')

                # --- ABA AJUSTES ---
                with ui.tab_panel(tab_ajust):
                    if ajustes:
                        with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                            for d in ajustes:
                                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(255,152,0,0.04); border: 1px solid rgba(255,152,0,0.3);'):
                                    ui.label(d.get('titulo_evento', 'Pauta sem título')).classes('text-sm font-bold text-white cyber-title')
                                    ui.label(f"De: {d.get('solicitante_nome', 'N/I')} ({d.get('setor', 'CGCFN')})").classes('text-xs text-grey-3')
                                    ui.label(f"📅 Data: {d.get('data_evento', 'N/I')} às {d.get('hora_evento', '09:00')}").classes('text-xs text-grey-3')
                                    ui.badge('AGUARDANDO CORREÇÃO').props('color=orange').classes('text-[9px] q-mt-xs')

                                    with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                        ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                        ui.button('Ver Detalhes', on_click=lambda d=d: open_tramitar_dialog(d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('thumb_up', size='3rem')
                            ui.label('Nenhuma pauta aguardando ajustes.').classes('text-xs')

                # --- ABA CONCLUÍDAS ---
                with ui.tab_panel(tab_concl):
                    if concluidas:
                        with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                            for d in concluidas:
                                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.1);'):
                                    ui.label(d.get('titulo_evento', 'Pauta sem título')).classes('text-sm font-bold text-white cyber-title')
                                    ui.label(f"De: {d.get('solicitante_nome', 'N/I')} ({d.get('setor', 'CGCFN')})").classes('text-xs text-grey-3')
                                    ui.badge('CONCLUÍDA').props('color=grey-7').classes('text-[9px] q-mt-xs')

                                    with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                        ui.button('✏️ Editar', on_click=lambda d=d: open_editar_pauta_dialog(d, render_content.refresh)).props('flat color=cyan dense icon=edit').classes('text-xs')
                                        ui.button('Ver Histórico', on_click=lambda d=d: open_tramitar_dialog(d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=grey dense').classes('text-xs')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('task_alt', size='3rem')
                            ui.label('Nenhuma pauta concluída registrada.').classes('text-xs')

                # --- ABA REJEITADAS ---
                with ui.tab_panel(tab_rej):
                    if rejeitadas:
                        with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                            for d in rejeitadas:
                                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style('background: rgba(244,67,54,0.04); border: 1px solid rgba(244,67,54,0.3);'):
                                    ui.label(d.get('titulo_evento', 'Pauta sem título')).classes('text-sm font-bold text-white cyber-title')
                                    ui.label(f"De: {d.get('solicitante_nome', 'N/I')} ({d.get('setor', 'CGCFN')})").classes('text-xs text-grey-3')
                                    ui.badge('INDEFERIDA').props('color=red').classes('text-[9px] q-mt-xs')

                                    with ui.row().classes('w-full justify-end q-mt-sm'):
                                        ui.button('Ver Motivo / Parecer', on_click=lambda d=d: open_tramitar_dialog(d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=red dense').classes('text-xs')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('block', size='3rem')
                            ui.label('Nenhuma pauta indeferida.').classes('text-xs')

                # --- ABA HISTÓRICO GLOBAL ---
                with ui.tab_panel(tab_hist):
                    if historico_global:
                        with ui.column().classes('w-full gap-3'):
                            for h in historico_global:
                                with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03);'):
                                    with ui.row().classes('w-full justify-between items-center'):
                                        ui.label(h.get('acao', 'Ação')).classes('text-xs font-bold text-cyan')
                                        data_h_txt = str(h.get('data_hora', ''))[:16].replace('T', ' ')
                                        ui.label(data_h_txt).classes('text-[9px] text-grey font-mono')
                                    ui.label(h.get('parecer','')).classes('text-[11px] text-grey-3 q-mt-xs')
                                    ui.label(f"Por: {h.get('usuario','Supervisor')}").classes('text-[9px] text-grey font-bold')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('history', size='3rem')
                            ui.label('Nenhum registro de histórico encontrado.').classes('text-xs')

        render_content()
