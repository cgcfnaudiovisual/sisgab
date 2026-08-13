# modules/comsoc_homologar.py
from datetime import datetime
import asyncio
import json
import urllib.parse
from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection, get_demanda_drive_url
import drive_service

THEME = theme.colors

def get_rank_seniority(rank_str):
    if not rank_str:
        return 99
    rank = str(rank_str).upper().replace('.', '').replace(' ', '').strip()
    
    if rank in ('AE', 'ALMIRANTEDEESQUADRA'): return 1
    if rank in ('VA', 'VICEALMIRANTE'): return 2
    if rank in ('CA', 'CONTRAALMIRANTE'): return 3
    if rank in ('CMG', 'CAPITAODEMAREGUERRA'): return 4
    if rank in ('CF', 'CAPITAODEFRAGATA'): return 5
    if rank in ('CC', 'CAPITAODECORVETA'): return 6
    if rank in ('CT', 'CAPITAOTENENTE'): return 7
    if any(x in rank for x in ('1TEN', '1ºTEN', '1SOTEN', '1TENENTE', '1ºTENENTE')): return 8
    if any(x in rank for x in ('2TEN', '2ºTEN', '2SOTEN', '2TENENTE', '2ºTENENTE')): return 9
    if rank in ('GM', 'GUARDAMARINHA'): return 10
    if rank in ('SO', 'SUBOFICIAL', 'SUB-OFICIAL'): return 11
    if any(x in rank for x in ('1SG', '1ºSG', '1SGT', '1ºSGT', '1ºSARGENTO', '1SARGENTO')): return 12
    if any(x in rank for x in ('2SG', '2ºSG', '2SGT', '2ºSGT', '2ºSARGENTO', '2SARGENTO')): return 13
    if any(x in rank for x in ('3SG', '3ºSG', '3SGT', '3ºSGT', '3ºSARGENTO', '3SARGENTO', 'SG', 'SARGENTO')): return 14
    if rank in ('CB', 'CABO'): return 15
    if rank in ('SD', 'SOLDADO', 'MN', 'MARINHEIRO'): return 16
    return 98

def sort_efetivo_list(ef_list):
    def sort_key(item):
        role = str(item.get('role', 'compel')).strip().lower()
        is_comsoc = role in ('admin', 'supervisor', 'comsoc', 'comsoc_design', 'operador')
        group_priority = 0 if is_comsoc else 1
        
        pg = item.get('posto_grad') or ''
        seniority = get_rank_seniority(pg)
        nome_guerra = str(item.get('nome_guerra') or '').upper()
        return (group_priority, seniority, nome_guerra)
        
    return sorted(ef_list, key=sort_key)

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

                # Formata a hora de entrada estritamente em HH:MM (ex: 09:00) sem segundos extras
                raw_hora = str(demanda.get('hora_evento', '09:00') or '09:00').strip()
                if len(raw_hora) >= 5 and ':' in raw_hora:
                    parts = raw_hora.split(':')
                    formatted_hora = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
                else:
                    formatted_hora = "09:00"

                with ui.row().classes('w-full gap-2 no-wrap'):
                    in_data_inicio = ui.input('Data Início', value=str(demanda.get('data_evento','') or '')).props('type=date dark outlined dense').classes('w-1/3')
                    in_data_fim = ui.input('Data Término (Opcional)', value=str(demanda.get('data_fim', demanda.get('data_evento','')) or '')).props('type=date dark outlined dense').classes('w-1/3')
                    in_hora = ui.input('Hora', value=formatted_hora).props('type=time step=60 dark outlined dense').classes('w-1/3')

                # Campo de Briefing, Observações e Autoridades (Sempre Visível e Destacado)
                in_autoridades = ui.textarea(
                    '📝 Briefing / Observações & Autoridades Presentes',
                    value=str(demanda.get('autoridades') or demanda.get('observacoes') or ''),
                    placeholder='Digite orientações da missão, fardamento, roteiro, autoridades presentes e observações gerais...'
                ).props('dark outlined dense w-full rows=3').classes('w-full q-mt-xs')

                # Campo de Link da Pasta do Google Drive / Acervo na Nuvem
                from database import get_demanda_drive_url
                cur_drive_url = get_demanda_drive_url(demanda)
                with ui.column().classes('w-full gap-1 p-2 bg-blue-950/30 rounded-lg border border-blue-500/20 q-my-xs'):
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label('📁 Link da Pasta no Google Drive / Acervo Nuvem').classes('text-xs font-bold text-blue-4')
                        if cur_drive_url:
                            ui.button('📁 Abrir Drive', on_click=lambda u=cur_drive_url: ui.open(u, new_tab=True)).props('unelevated color=blue icon=open_in_new dense').classes('text-[10px] px-2')
                        else:
                            pastas_mae = drive_service.get_pastas_mae_list()
                            sel_pasta_mae = None
                            if len(pastas_mae) > 1:
                                opts_pm = {p['folder_id']: f"📁 {p['nome']}" for p in pastas_mae}
                                default_pm = next((p['folder_id'] for p in pastas_mae if p.get('padrao')), pastas_mae[0]['folder_id'])
                                sel_pasta_mae = ui.select(opts_pm, value=default_pm, label='Pasta Mãe do Drive').props('dark outlined dense').classes('text-xs')

                            async def criar_pasta_manual():
                                tit_val = in_titulo.value.strip() if in_titulo.value else demanda.get('titulo_evento', '')
                                dt_val = in_data_inicio.value.strip() if in_data_inicio.value else demanda.get('data_evento', '')
                                
                                n_wait = ui.notify("📂 Criando pasta no Google Drive...", color='info', spinner=True, timeout=0)
                                try:
                                    import drive_service
                                    drive_service.reset_drive_service()
                                    pm_id = sel_pasta_mae.value if sel_pasta_mae else None
                                    result = await asyncio.wait_for(
                                        asyncio.to_thread(drive_service.criar_pasta_evento, tit_val, dt_val, pm_id),
                                        timeout=12.0
                                    )
                                    if result and result.get('evento_link'):
                                        in_drive_url.value = result['evento_link']
                                        ui.notify(f"📂 Pasta criada no Drive!", color='success', timeout=5000)
                                    else:
                                        ui.notify("⚠️ Não foi possível criar a pasta no Drive. Verifique se o JSON da Service Account e a Pasta Mãe foram salvos no Painel Admin (/admin_panel).", color='warning', timeout=8000)
                                except asyncio.TimeoutError:
                                    ui.notify("⏱️ Tempo limite excedido ao conectar ao Google Drive. Verifique a internet ou o JSON da Service Account no Admin.", color='warning', timeout=8000)
                                except Exception as ex_cp:
                                    ui.notify(f"Erro ao criar pasta no Drive: {ex_cp}", color='negative', timeout=8000)
                                finally:
                                    try:
                                        n_wait.dismiss()
                                    except Exception:
                                        pass
                            ui.button('📂 Criar Pasta no Drive', on_click=criar_pasta_manual).props('unelevated color=blue-7 dense').classes('text-[10px] px-2')
                    in_drive_url = ui.input(
                        placeholder='https://drive.google.com/drive/folders/...',
                        value=cur_drive_url
                    ).props('dark outlined dense w-full').classes('w-full')

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

                # Reatividade dinâmica das labels e especificações conforme a Categoria da Demanda
                def atualizar_especificacoes_categoria(cat):
                    if cat == 'design_arte':
                        in_produto.props('label="Especificação da Peça / Dimensões (ex: 1080x1920, A4)"')
                    elif cat == 'impressos_albuns':
                        in_produto.props('label="Tiragem, Tipo de Papel / Encadernação"')
                    elif cat == 'brindes_lembrancas':
                        in_produto.props('label="Tipo e Quantidade de Brindes / Lembranças"')
                    elif cat == 'redacao_textos':
                        in_produto.props('label="Tipo de Texto / Discurso / Publicação"')
                    elif cat == 'suporte_evento':
                        in_produto.props('label="Especificação do Receptivo / Assentos Jade"')
                    else:
                        in_produto.props('label="Especificação do Produto / Peça"')
                    in_produto.update()

                in_categoria.on_value_change(lambda e: atualizar_especificacoes_categoria(e.value))
                atualizar_especificacoes_categoria(in_categoria.value)

                 # Carrega opções do efetivo para designação de militares
                efetivo_options = {}
                db_ef = get_service_db_connection() or get_db_connection()
                if db_ef:
                    try:
                        res_ef = db_ef.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
                        if res_ef.data:
                            sorted_ef = sort_efetivo_list(res_ef.data)
                            seen_ef_labels = set()
                            efetivo_options = {}
                            for item in sorted_ef:
                                lbl = f"{item.get('posto_grad') or ''} {item['nome_guerra']} ({str(item.get('role', 'gabinete')).upper()})".strip()
                                if lbl not in seen_ef_labels:
                                    seen_ef_labels.add(lbl)
                                    efetivo_options[item['id']] = lbl
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
                
                # Converte IDs para inteiros ou mantém texto para militares livres
                enc_id = demanda.get('encarregado_id')
                if enc_id is not None and str(enc_id).strip():
                    raw_enc = str(enc_id).strip()
                    try:
                        enc_id = int(raw_enc)
                    except ValueError:
                        enc_id = raw_enc
                else:
                    enc_id = None

                des_id = None
                for mid in mids:
                    if mid is not None and str(mid).strip():
                        raw_m = str(mid).strip()
                        try:
                            mid_int = int(raw_m)
                        except ValueError:
                            mid_int = raw_m
                        if enc_id is None or str(mid_int) != str(enc_id):
                            des_id = mid_int
                            break

                if enc_id is not None and enc_id not in efetivo_options:
                    efetivo_options[enc_id] = str(enc_id) if isinstance(enc_id, str) else f"Militar (ID: {enc_id})"
                if des_id is not None and des_id not in efetivo_options:
                    efetivo_options[des_id] = str(des_id) if isinstance(des_id, str) else f"Militar (ID: {des_id})"

                ui.label('🎖️ Designação de Equipe Operacional / Criativa').classes('text-xs font-bold text-cyan q-mt-xs')
                with ui.row().classes('w-full gap-2 no-wrap'):
                    encarregado_select = ui.select(
                        efetivo_options,
                        value=enc_id,
                        label='👤 Encarregado da Missão',
                        with_input=True,
                        clearable=True
                    ).props('dark outlined dense option-dark new-value-mode=add-unique').classes('w-1/2').tooltip('Selecione do efetivo ou digite o nome do militar')

                    designer_select = ui.select(
                        efetivo_options,
                        value=des_id,
                        label='🎨 Militar Designado (Arte / Design)',
                        with_input=True,
                        clearable=True
                    ).props('dark outlined dense option-dark new-value-mode=add-unique').classes('w-1/2').tooltip('Selecione do efetivo ou digite o nome do militar')

                # Container Dinâmico para Tipos de Serviço Requeridos (exibido para Coberturas Audiovisuais)
                container_servicos = ui.column().classes('w-full gap-1 q-mt-xs')
                with container_servicos:
                    ui.label('📸 Tipos de Serviço Requeridos').classes('text-xs font-bold text-cyan')
                    chk_foto = ui.checkbox('Fotografia', value='foto' in cob_list)
                    chk_video = ui.checkbox('Vídeo / Filmagem', value='video' in cob_list)
                    chk_grafico = ui.checkbox('🎨 Serviço Gráfico / Design', value='grafico' in cob_list)
                    chk_drone = ui.checkbox('🚁 Imagens Aéreas / Drone', value='drone' in cob_list)
                    chk_redes = ui.checkbox('📱 Mídias Sociais / Reels', value='redes' in cob_list)

                # Liga a visibilidade da caixa de serviços requeridos à categoria selecionada
                container_servicos.bind_visibility_from(
                    in_categoria, 'value',
                    backward=lambda cat: cat in ('audiovisual', 'outra_tarefa')
                )


                def excluir_pauta():
                    with ui.dialog() as confirm_dlg, ui.card().classes('q-pa-md bg-slate-900 border border-red-500 rounded-xl').style('max-width: 440px;'):
                        ui.label('⚠️ Confirmar Exclusão').classes('text-md font-bold text-red cyber-title')
                        ui.label(f"Tem certeza que deseja excluir permanentemente a pauta '{demanda.get('titulo_evento','')}'? Esta ação não poderá ser desfeita.").classes('text-xs text-grey-3 q-my-md')
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Cancelar', on_click=confirm_dlg.close).props('flat color=grey')
                            def confirmar_delecao():
                                db_del = get_service_db_connection() or get_db_connection()
                                if db_del:
                                    dem_id_del = demanda['id']
                                    if isinstance(dem_id_del, str) and dem_id_del.isdigit():
                                        dem_id_del = int(dem_id_del)
                                    db_del.table('demandas_comunicacao').delete().eq('id', dem_id_del).execute()
                                    ui.notify('🗑️ Pauta excluída com sucesso!', color='positive')
                                    confirm_dlg.close()
                                    edit_dialog.close()
                                    if callback_refresh:
                                        callback_refresh()
                            ui.button('🗑️ Sim, Excluir', on_click=confirmar_delecao).props('unelevated color=red text-color=white bold')
                    confirm_dlg.open()

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
                            enc_save = None
                            aut_extra = []

                            enc_val = encarregado_select.value
                            if enc_val:
                                enc_save = str(enc_val).strip()
                                if isinstance(enc_val, int) or (isinstance(enc_val, str) and enc_val.isdigit()):
                                    militar_ids.append(int(enc_val))
                                else:
                                    aut_extra.append(f"[Responsável: {enc_save}]")

                            des_val = designer_select.value
                            if des_val:
                                if isinstance(des_val, int) or (isinstance(des_val, str) and des_val.isdigit()):
                                    militar_ids.append(int(des_val))
                                else:
                                    aut_extra.append(f"[Design: {str(des_val).strip()}]")

                            aut_final = str(in_autoridades.value or '').strip()
                            d_url_val = str(in_drive_url.value or '').strip()
                            if d_url_val:
                                if '[DRIVE:' in aut_final:
                                    import re
                                    aut_final = re.sub(r'\[DRIVE:[^\]]+\]', f'[DRIVE: {d_url_val}]', aut_final)
                                else:
                                    aut_final = f"{aut_final} [DRIVE: {d_url_val}]".strip()

                            update_payload = {
                                'titulo_evento': in_titulo.value.strip(),
                                'solicitante_nome': in_solicitante.value.strip(),
                                'setor': in_setor.value.strip(),
                                'contato': in_contato.value.strip(),
                                'local_evento': in_local.value.strip(),
                                'data_evento': in_data_inicio.value,
                                'data_fim': in_data_fim.value or in_data_inicio.value,
                                'hora_evento': in_hora.value or '09:00',
                                'autoridades': aut_final,
                                'drive_url': d_url_val,
                                'status': in_status.value,
                                'categoria_demanda': in_categoria.value,
                                'produto_especifico': in_produto.value.strip(),
                                'encarregado_id': enc_save,
                                'notificar_militar_ids': json.dumps(list(set(militar_ids))),
                                'tipo_cobertura': json.dumps(cobs)
                            }
                            dem_id = demanda['id']
                            if isinstance(dem_id, str) and dem_id.isdigit():
                                dem_id = int(dem_id)
                            try:
                                res = db.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                            except Exception as e_sup:
                                update_payload.pop('drive_url', None)
                                res = db.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()

                            if d_url_val:
                                from database import salvar_demanda_drive_link
                                salvar_demanda_drive_link(dem_id, in_titulo.value.strip(), d_url_val)

                            # Sincroniza também no banco SQLite local
                            try:
                                from sqlite_adapter import LocalSQLiteClient
                                loc_db = LocalSQLiteClient()
                                loc_db.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                            except Exception:
                                pass

                            print(f"[EDIT PAUTA SAVE RES] ID: {dem_id}, data: {res.data if hasattr(res, 'data') else res}")
                            ui.notify('✅ Pauta editada e salva com sucesso!', color='positive')
                            edit_dialog.close()
                            if callback_refresh:
                                callback_refresh()
                        except Exception as e_save:
                            ui.notify(f'Erro ao editar pauta: {e_save}', color='negative')

                with ui.row().classes('w-full justify-between items-center q-mt-md'):
                    ui.button('🗑️ Excluir Pauta', on_click=excluir_pauta).props('flat color=red icon=delete').classes('text-xs')
                    with ui.row().classes('items-center gap-2'):
                        ui.button('Cancelar', on_click=edit_dialog.close).props('flat color=grey')
                        ui.button('💾 Salvar Alterações', on_click=salvar_edicao).props('unelevated color=green text-color=white bold')
                    
        edit_dialog.open()
    except Exception as err_dlg:
        print(f"[EDIT PAUTA DIALOG ERR] {err_dlg}")
        ui.notify(f"Erro ao abrir modal de edição: {err_dlg}", color="negative")


def open_concluir_missao_dialog(demanda, user_name_guerra="SUPERVISOR", callback_refresh=None):
    efetivo_options = {}
    db = get_service_db_connection() or get_db_connection()
    if db:
        try:
            res_ef = db.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
            if res_ef.data:
                sorted_ef = sort_efetivo_list(res_ef.data)
                seen_ef_labels = set()
                efetivo_options = {}
                for item in sorted_ef:
                    lbl = f"{item.get('posto_grad') or ''} {item['nome_guerra']} ({str(item.get('role', 'gabinete')).upper()})".strip()
                    if lbl not in seen_ef_labels:
                        seen_ef_labels.add(lbl)
                        efetivo_options[item['id']] = lbl
        except Exception as e:
            print(f"[EFETIVO CONCLUIR ERR] {e}")

    with ui.dialog() as concluir_dialog, ui.card().classes('w-[580px] max-w-[95vw] q-pa-lg border').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius: 16px;'
    ):
        ui.label(f"🎯 Conclusão & Entrega de Missão: {demanda.get('titulo_evento','')}").classes('text-white text-md font-bold cyber-title q-mb-xs')
        ui.label(f"Solicitante: {demanda.get('solicitante_nome','')} ({demanda.get('setor','')})").classes('text-xs text-grey-4 q-mb-md')

        enc_id = demanda.get('encarregado_id')
        if enc_id is not None and str(enc_id).strip():
            raw_enc = str(enc_id).strip()
            try:
                enc_id = int(raw_enc)
            except ValueError:
                enc_id = raw_enc
        else:
            enc_id = None

        if enc_id is not None and enc_id not in efetivo_options:
            efetivo_options[enc_id] = str(enc_id) if isinstance(enc_id, str) else f"Militar (ID: {enc_id})"

        with ui.column().classes('w-full gap-3 text-xs'):
            encarregado_sel = ui.select(
                efetivo_options,
                value=enc_id,
                label='👤 Encarregado da Missão',
                with_input=True,
                clearable=True
            ).props('dark outlined dense option-dark new-value-mode=add-unique w-full').classes('w-full').tooltip('Selecione do efetivo ou digite o nome do militar')

            fotografo_sel = ui.select(
                efetivo_options,
                label='📷 Fotógrafo / Cinegrafista',
                with_input=True,
                clearable=True
            ).props('dark outlined dense option-dark new-value-mode=add-unique w-full').classes('w-full').tooltip('Selecione do efetivo ou digite o nome do fotógrafo')

            designer_sel = ui.select(
                efetivo_options,
                label='🎨 Designer / Redator',
                with_input=True,
                clearable=True
            ).props('dark outlined dense option-dark new-value-mode=add-unique w-full').classes('w-full').tooltip('Selecione do efetivo ou digite o nome do designer')

            drive_input = ui.input('🔗 Link da Galeria de Fotos / Drive (Opcional)', placeholder='https://drive.google.com/...').props('dark outlined dense w-full')
            parecer_input = ui.textarea('✍️ Relatório de Entrega / Parecer Final', placeholder='Ex: Cobertura realizada. 50 fotos tratadas enviadas ao acervo.').props('dark outlined dense w-full rows=3')
            error_lbl = ui.label('').classes('text-xs text-red font-bold')

            def efetuar_conclusao():
                db_c = get_service_db_connection() or get_db_connection()
                if db_c:
                    try:
                        militar_ids = []
                        aut_extra = []

                        enc_val = encarregado_sel.value
                        enc_save = None
                        if enc_val:
                            enc_save = str(enc_val).strip()
                            if isinstance(enc_val, int) or (isinstance(enc_val, str) and enc_val.isdigit()):
                                militar_ids.append(int(enc_val))
                            else:
                                aut_extra.append(f"[Responsável: {enc_save}]")

                        fot_val = fotografo_sel.value
                        if fot_val:
                            if isinstance(fot_val, int) or (isinstance(fot_val, str) and fot_val.isdigit()):
                                militar_ids.append(int(fot_val))
                            else:
                                aut_extra.append(f"[Fotógrafo: {str(fot_val).strip()}]")

                        des_val = designer_sel.value
                        if des_val:
                            if isinstance(des_val, int) or (isinstance(des_val, str) and des_val.isdigit()):
                                militar_ids.append(int(des_val))
                            else:
                                aut_extra.append(f"[Design: {str(des_val).strip()}]")

                        drive_url_val = str(drive_input.value or '').strip()
                        update_payload = {
                            'status': 'concluida',
                            'drive_url': drive_url_val,
                            'notificar_militar_ids': json.dumps(list(set(militar_ids)))
                        }
                        if enc_save:
                            update_payload['encarregado_id'] = enc_save

                        aut_atual = demanda.get('autoridades') or ''
                        if aut_extra:
                            for a_ex in aut_extra:
                                if a_ex not in aut_atual:
                                    aut_atual = f"{aut_atual} {a_ex}".strip()
                        if drive_url_val:
                            if '[DRIVE:' in aut_atual:
                                import re
                                aut_atual = re.sub(r'\[DRIVE:[^\]]+\]', f'[DRIVE: {drive_url_val}]', aut_atual)
                            else:
                                aut_atual = f"{aut_atual} [DRIVE: {drive_url_val}]".strip()
                        update_payload['autoridades'] = aut_atual

                        dem_id = demanda['id']
                        if isinstance(dem_id, str) and dem_id.isdigit():
                            dem_id = int(dem_id)

                        try:
                            db_c.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                        except Exception as e_sup_c:
                            if 'drive_url' in str(e_sup_c):
                                update_payload.pop('drive_url', None)
                                db_c.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                            else:
                                raise e_sup_c

                        # Sincroniza também no banco SQLite local
                        try:
                            from sqlite_adapter import LocalSQLiteClient
                            loc_db = LocalSQLiteClient()
                            loc_db.table('demandas_comunicacao').update(update_payload).eq('id', dem_id).execute()
                        except Exception:
                            pass

                        # Monta descrição da equipe de cobertura
                        equipe_str_list = []
                        if enc_val:
                            lbl_e = efetivo_options.get(enc_val, str(enc_val))
                            equipe_str_list.append(f"Encarregado: {lbl_e}")
                        if fot_val:
                            lbl_f = efetivo_options.get(fot_val, str(fot_val))
                            equipe_str_list.append(f"Fotógrafo/Cinegrafista: {lbl_f}")
                        if des_val:
                            lbl_d = efetivo_options.get(des_val, str(des_val))
                            equipe_str_list.append(f"Designer/Redator: {lbl_d}")

                        parecer_texto = parecer_input.value or 'Pauta concluída e entregue.'
                        if equipe_str_list:
                            parecer_texto += f"\n\n👨‍✈️ Equipe da Cobertura: {', '.join(equipe_str_list)}"

                        hist = {
                            'demanda_id': dem_id,
                            'data_hora': datetime.now().isoformat(),
                            'usuario': user_name_guerra,
                            'acao': 'Missão Concluída',
                            'parecer': parecer_texto
                        }
                        try:
                            db_c.table('demandas_historico_tramitacao').insert(hist).execute()
                        except Exception:
                            pass

                        if drive_input.value and drive_input.value.strip():
                            try:
                                db_c.table('processed_photos').insert({
                                    'event_name': demanda.get('titulo_evento', ''),
                                    'filename': 'drive_folder_link',
                                    'drive_link': drive_input.value.strip(),
                                    'criado_em': datetime.now().isoformat()
                                }).execute()
                            except Exception:
                                pass

                        try:
                            from notifications_manager import notify_telegram
                            notify_telegram(
                                f"🎯 **Missão Concluída & Entregue!**\n"
                                f"📌 {demanda.get('titulo_evento', 'Sem Título')}\n"
                                f"👨‍✈️ Concluído por: {user_name_guerra}\n"
                                f"💬 Relatório: {parecer_input.value[:120] if parecer_input.value else 'Entregue'}",
                                "system"
                            )
                        except Exception:
                            pass

                        ui.notify('🎯 Missão finalizada e registrada com sucesso!', color='positive')
                        concluir_dialog.close()
                        if callback_refresh:
                            callback_refresh()
                    except Exception as err:
                        error_lbl.text = f"Erro ao concluir: {err}"

            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Cancelar', on_click=concluir_dialog.close).props('flat color=grey')
                ui.button('🎯 Confirmar Conclusão da Missão', on_click=efetuar_conclusao).props('unelevated color=green text-color=white bold')

    concluir_dialog.open()


def open_tramitar_dialog(demanda, user_name_guerra="SUPERVISOR", is_approver=True, callback_refresh=None):
    efetivo_options = {}
    db = get_service_db_connection() or get_db_connection()
    if db:
        try:
            res_ef = db.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
            if res_ef.data:
                sorted_ef = sort_efetivo_list(res_ef.data)
                seen_ef_labels = set()
                efetivo_options = {}
                for item in sorted_ef:
                    lbl = f"{item.get('posto_grad') or ''} {item['nome_guerra']} ({str(item.get('role', 'gabinete')).upper()})".strip()
                    if lbl not in seen_ef_labels:
                        seen_ef_labels.add(lbl)
                        efetivo_options[item['id']] = lbl
        except Exception as e:
            print(f"[EFETIVO LOAD ERR] {e}")

    with ui.dialog() as tramitar_dialog, ui.card().classes('w-[620px] max-w-[95vw] q-pa-lg border').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius: 16px; max-height: 90vh; overflow-y: auto;'
    ):
        ui.label(f"⚖️ Tramitação & Parecer: {demanda.get('titulo_evento','')}").classes('text-white text-md font-bold cyber-title q-mb-xs')
        ui.label(f"Solicitante: {demanda.get('solicitante_nome','')} ({demanda.get('setor','')})").classes('text-xs text-grey-4 q-mb-md')
        
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
        if enc_id is not None and str(enc_id).strip():
            raw_enc = str(enc_id).strip()
            try:
                enc_id = int(raw_enc)
            except ValueError:
                enc_id = raw_enc
        else:
            enc_id = None

        des_id = None
        for mid in mids:
            if mid is not None and str(mid).strip():
                raw_m = str(mid).strip()
                try:
                    mid_int = int(raw_m)
                except ValueError:
                    mid_int = raw_m
                if enc_id is None or str(mid_int) != str(enc_id):
                    des_id = mid_int
                    break

        if enc_id is not None and enc_id not in efetivo_options:
            efetivo_options[enc_id] = str(enc_id) if isinstance(enc_id, str) else f"Militar (ID: {enc_id})"
        if des_id is not None and des_id not in efetivo_options:
            efetivo_options[des_id] = str(des_id) if isinstance(des_id, str) else f"Militar (ID: {des_id})"

        with ui.column().classes('w-full gap-3 text-xs'):
            with ui.row().classes('w-full gap-2 no-wrap'):
                encarregado_select = ui.select(
                    efetivo_options,
                    value=enc_id,
                    label='👤 Encarregado da Missão',
                    with_input=True,
                    clearable=True
                ).props('dark outlined dense option-dark new-value-mode=add-unique').classes('w-1/2').tooltip('Selecione do efetivo ou digite o nome do militar')

                designer_select = ui.select(
                    efetivo_options,
                    value=des_id,
                    label='🎨 Militar Designado (Arte / Design)',
                    with_input=True,
                    clearable=True
                ).props('dark outlined dense option-dark new-value-mode=add-unique').classes('w-1/2').tooltip('Selecione do efetivo ou digite o nome do militar')
            
            parecer_input = ui.textarea('✍️ Parecer da Chefia / Despacho', placeholder='Digite o parecer ou instruções...').props('dark outlined dense w-full rows=3')
            error_lbl = ui.label('').classes('text-xs text-red font-bold')

            def submeter_tramitacao(novo_status, acao_nome):
                if not encarregado_select.value and novo_status == 'aprovada':
                    error_lbl.text = "⚠️ É necessário definir o Encarregado da Missão para aprovar."
                    return
                    
                db = get_service_db_connection() or get_db_connection()
                if db:
                    try:
                        militar_ids = []
                        aut_extra = []

                        enc_val = encarregado_select.value
                        enc_save = None
                        if enc_val:
                            enc_save = str(enc_val).strip()
                            if isinstance(enc_val, int) or (isinstance(enc_val, str) and enc_val.isdigit()):
                                militar_ids.append(int(enc_val))
                            else:
                                aut_extra.append(f"[Responsável: {enc_save}]")

                        des_val = designer_select.value
                        if des_val:
                            if isinstance(des_val, int) or (isinstance(des_val, str) and des_val.isdigit()):
                                militar_ids.append(int(des_val))
                            else:
                                aut_extra.append(f"[Design: {str(des_val).strip()}]")

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

                        update_data = {
                            'status': novo_status,
                            'notificar_militar_ids': json.dumps(list(set(militar_ids)))
                        }
                        if enc_save:
                            update_data['encarregado_id'] = enc_save

                        if aut_extra:
                            aut_atual = demanda.get('autoridades') or ''
                            for a_ex in aut_extra:
                                if a_ex not in aut_atual:
                                    aut_atual = f"{aut_atual} {a_ex}".strip()
                            update_data['autoridades'] = aut_atual

                        dem_id = demanda['id']
                        if isinstance(dem_id, str) and dem_id.isdigit():
                            dem_id = int(dem_id)

                        db.table('demandas_comunicacao').update(update_data).eq('id', dem_id).execute()
                        demanda['status'] = novo_status
                        
                        if novo_status in ('aprovado', 'aprovada'):
                            import drive_service
                            result = drive_service.criar_pasta_evento(demanda['titulo_evento'], demanda.get('data_evento', ''))
                            if result:
                                db.table('demandas_comunicacao').update({
                                    'drive_url': result['evento_link']
                                }).eq('id', dem_id).execute()
                                ui.notify(f"📂 Pasta criada no Drive!", color='success')

                        ui.notify(f"Demanda tramitada: {acao_nome}", color='success')

                        try:
                            from notifications_manager import notify_telegram
                            titulo_dem = demanda.get('titulo_evento', 'Sem Título')
                            emoji_status = '✅' if novo_status == 'aprovada' else '❌' if novo_status == 'rejeitado' else '⚠️'
                            notify_telegram(
                                f"📋 Pauta Tramitada:\n"
                                f"📌 {titulo_dem}\n"
                                f"{emoji_status} Status: {acao_nome}\n"
                                f"👨‍✈️ Tramitado por: {user_name_guerra}\n"
                                f"💬 Parecer: {parecer_input.value[:120] if parecer_input.value else 'N/I'}",
                                "system"
                            )
                        except Exception as tg_err:
                            print(f"[TELEGRAM TRAMITAR ERR] {tg_err}")

                        tramitar_dialog.close()
                        if callback_refresh:
                            callback_refresh()
                    except Exception as e:
                        error_lbl.text = f"Erro na gravação: {e}"

            def deletar_pauta_confirm():
                def efetuar_delecao():
                    db = get_service_db_connection() or get_db_connection()
                    if db:
                        try:
                            dem_id = demanda['id']
                            if isinstance(dem_id, str) and dem_id.isdigit():
                                dem_id = int(dem_id)
                            db.table('demandas_comunicacao').delete().eq('id', dem_id).execute()
                            ui.notify(f"🗑️ Pauta #{demanda.get('id')} excluída permanentemente!", color='negative')
                            confirm_del_dialog.close()
                            tramitar_dialog.close()
                            if callback_refresh:
                                callback_refresh()
                        except Exception as e_del:
                            error_lbl.text = f"Erro ao excluir pauta: {e_del}"

                with ui.dialog() as confirm_del_dialog, ui.card().classes('w-96 q-pa-md bg-slate-900 border border-red-500/50 rounded-xl'):
                    ui.label('⚠️ CONFIRMAR EXCLUSÃO').classes('text-red font-bold text-md cyber-title')
                    ui.label(f"Tem certeza que deseja excluir permanentemente a pauta #{demanda.get('id')} ({demanda.get('titulo_evento')})?").classes('text-xs text-white q-my-sm')
                    ui.label('Esta ação não poderá ser desfeita.').classes('text-[10px] text-grey-4 italic')
                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                        ui.button('Cancelar', on_click=confirm_del_dialog.close).props('flat color=grey text-color=white')
                        ui.button('🗑️ Excluir Permanentemente', on_click=efetuar_delecao).props('unelevated color=red text-color=white bold')
                confirm_del_dialog.open()

            with ui.row().classes('w-full justify-between gap-2 q-mt-xs flex-wrap'):
                ui.button('Rejeitar', on_click=lambda: submeter_tramitacao('rejeitado', 'Demanda Rejeitada')).props('unelevated color=red text-color=white bold').classes('col q-py-sm rounded-lg')
                ui.button('Pedir Ajustes', on_click=lambda: submeter_tramitacao('ajustes', 'Solicitado Ajustes')).props('unelevated color=orange text-color=black bold').classes('col q-py-sm rounded-lg')
                ui.button('Aprovar', on_click=lambda: submeter_tramitacao('aprovada', 'Demanda Aprovada')).props('unelevated color=green text-color=white bold').classes('col q-py-sm rounded-lg')
                ui.button('🎯 Concluir Missão', on_click=lambda: (tramitar_dialog.close(), open_concluir_missao_dialog(demanda, user_name_guerra, callback_refresh))).props('unelevated color=cyan text-color=black bold').classes('col q-py-sm rounded-lg')
                ui.button('🗑️ Excluir Pauta', on_click=deletar_pauta_confirm).props('outline color=red text-color=red bold icon=delete').classes('col q-py-sm rounded-lg')

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
                ui.label('⚖️ GESTÃO DE DEMANDAS & PAUTAS').classes('text-xl font-bold text-white cyber-title')
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

            def sort_by_date_time(demand_list, desc=False):
                def get_sort_key(d):
                    d_date = str(d.get('data_evento') or '9999-12-31').strip()
                    d_time = str(d.get('hora_evento') or '23:59').strip()
                    if not d_date or d_date == 'None':
                        d_date = '9999-12-31'
                    if not d_time or d_time == 'None':
                        d_time = '23:59'
                    return (d_date, d_time)
                return sorted(demand_list, key=get_sort_key, reverse=desc)

            raw_pendentes  = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('pendente', 'pendentes')]
            raw_aprovadas  = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('aprovada', 'aprovado', 'aprovadas')]
            raw_ajustes    = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('ajustes', 'ajuste')]
            raw_concluidas = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('concluida', 'concluída', 'concluido', 'concluído')]
            raw_rejeitadas = [d for d in todas_demandas if str(d.get('status', '')).strip().lower() in ('rejeitado', 'rejeitada', 'indeferida', 'indeferido')]

            pendentes  = sort_by_date_time(raw_pendentes, desc=False)
            aprovadas  = sort_by_date_time(raw_aprovadas, desc=False)
            ajustes    = sort_by_date_time(raw_ajustes, desc=False)
            concluidas = sort_by_date_time(raw_concluidas, desc=True)
            rejeitadas = sort_by_date_time(raw_rejeitadas, desc=True)

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

            # Helper para renderizar card completo de demanda com ações rápidas
            def render_homologar_card(d, status_type):
                bg_style = 'background: rgba(0,229,255,0.03); border: 1px solid rgba(0,229,255,0.25);'
                st_color = 'amber-9'
                if status_type == 'aprovada':
                    bg_style = 'background: rgba(34,197,94,0.04); border: 1px solid rgba(34,197,94,0.3);'
                    st_color = 'green-9'
                elif status_type == 'ajustes':
                    bg_style = 'background: rgba(251,146,60,0.04); border: 1px solid rgba(251,146,60,0.3);'
                    st_color = 'orange-9'
                elif status_type == 'concluida':
                    bg_style = 'background: rgba(148,163,184,0.04); border: 1px solid rgba(148,163,184,0.2);'
                    st_color = 'grey-7'
                elif status_type == 'rejeitada':
                    bg_style = 'background: rgba(239,68,68,0.04); border: 1px solid rgba(239,68,68,0.3);'
                    st_color = 'red-9'

                with ui.card().classes('w-full q-pa-md no-shadow rounded-2xl flex flex-col justify-between hover:border-cyan-400/60 transition-all').style(bg_style):
                    with ui.column().classes('w-full gap-2'):
                        # Header do Card: Título + Badge Status + Score
                        with ui.row().classes('w-full justify-between items-start gap-2'):
                            ui.label(d.get('titulo_evento', 'PAUTA SEM TÍTULO')).classes('text-sm font-black text-white cyber-title leading-tight')
                            with ui.row().classes('items-center gap-1 shrink-0'):
                                score = d.get('score_esforco', 1.0)
                                score_col = "green" if score <= 2.0 else ("orange" if score <= 3.5 else "red")
                                ui.badge(f"Esforço: {score}").props(f"color={score_col}").classes('text-[9px]')
                                st_label = str(d.get('status', status_type)).upper().replace('_', ' ')
                                ui.badge(st_label).props(f"color={st_color} text-color=white bold").classes('text-[9px] q-px-xs')

                        # Categoria & Serviços
                        cat_val = str(d.get('categoria_demanda') or 'audiovisual').strip().lower()
                        cob_val = d.get('tipo_cobertura') or '[]'
                        try:
                            cobs = json.loads(cob_val) if isinstance(cob_val, str) else (cob_val if isinstance(cob_val, list) else [])
                        except Exception:
                            cobs = []

                        with ui.row().classes('items-center gap-1 flex-wrap q-my-xs'):
                            if 'audiovisual' in cat_val or any(x in cobs for x in ('foto', 'video', 'redes', 'drone')):
                                ui.badge('📸 Audiovisual').props('color=cyan-9 text-color=white bold').classes('text-[10px] q-px-xs')
                            if 'design' in cat_val or 'grafic' in cat_val:
                                ui.badge('🎨 Design / Artes').props('color=purple-9 text-color=white bold').classes('text-[10px] q-px-xs')
                            if 'impresso' in cat_val:
                                ui.badge('🖨️ Impressos').props('color=orange-9 text-color=white bold').classes('text-[10px] q-px-xs')

                            prod_manual = d.get('produto_especifico') or ''
                            if prod_manual:
                                ui.badge(f"📦 {prod_manual}").props('color=blue-9 text-color=white').classes('text-[10px] q-px-xs')

                            for cob in cobs:
                                if cob == 'foto': ui.badge('📷 Fotografia').props('color=cyan-10').classes('text-[9px] q-px-xs')
                                elif cob == 'video': ui.badge('🎥 Vídeo').props('color=teal-10').classes('text-[9px] q-px-xs')
                                elif cob == 'drone': ui.badge('🚁 Imagens Aéreas').props('color=amber-10').classes('text-[9px] q-px-xs')
                                elif cob == 'redes': ui.badge('📱 Redes Sociais').props('color=pink-10').classes('text-[9px] q-px-xs')

                        ui.separator().style('background: rgba(255,255,255,0.08); margin: 2px 0;')

                        # Informações do Evento
                        with ui.column().classes('w-full gap-1 text-xs'):
                            ui.label(f"👤 Solicitante: {d.get('solicitante_nome', 'COMSOC')} ({d.get('setor', 'Gabinete')})").classes('text-grey-3 font-medium')
                            
                            dt_ev = d.get('data_evento', 'N/I')
                            hr_ev = d.get('hora_evento', '09:00')
                            dt_label = f"📅 Data: {dt_ev} às {hr_ev}"
                            if dt_ev == str(datetime.now().date()):
                                dt_label += " ⚡ (HOJE!)"
                            ui.label(dt_label).classes('text-cyan-3 font-bold')

                            if d.get('local_evento'):
                                ui.label(f"📍 Local: {d['local_evento']}").classes('text-grey-4')

                            # Autoridades / Observações
                            aut_txt = str(d.get('autoridades') or '').strip()
                            if aut_txt:
                                ui.label(f"👑 Autoridades/Obs: {aut_txt[:90]}{'...' if len(aut_txt)>90 else ''}").classes('text-[11px] text-amber-2/90 italic q-mt-xs')

                    # Rodapé com Botões de Ação Rápida
                    ui.separator().style('background: rgba(255,255,255,0.08); margin: 6px 0;')
                    with ui.row().classes('w-full justify-between items-center gap-1 flex-wrap'):
                        with ui.row().classes('items-center gap-1'):
                            ui.button('✏️', on_click=lambda cur_d=d: open_editar_pauta_dialog(cur_d, render_content.refresh)).props('flat round dense color=cyan size=sm').tooltip('Editar Pauta')
                            ui.button('📅', on_click=lambda: ui.navigate.to('/agenda_geral')).props('flat round dense color=cyan size=sm').tooltip('Ver na Agenda Geral')
                            cur_d_url = get_demanda_drive_url(d)
                            if cur_d_url:
                                ui.button('📁 Drive', on_click=lambda u=cur_d_url: ui.open(u, new_tab=True)).props('unelevated color=blue icon=open_in_new dense').classes('text-[10px] q-px-xs').tooltip('Abrir Pasta no Google Drive / Acervo')

                        with ui.row().classes('items-center gap-1'):
                            if status_type == 'pendente':
                                ui.button('⚖️ Analisar & Tramitar', on_click=lambda cur_d=d: open_tramitar_dialog(cur_d, user_name_guerra, is_approver, render_content.refresh)).props('unelevated color=primary text-color=black dense bold').classes('text-xs q-px-sm')
                            elif status_type == 'aprovada':
                                ui.button('🎯 Concluir Missão', on_click=lambda cur_d=d: open_concluir_missao_dialog(cur_d, user_name_guerra, render_content.refresh)).props('unelevated color=green text-color=white dense bold icon=task_alt').classes('text-xs q-px-xs')
                                ui.button('Detalhes', on_click=lambda cur_d=d: open_tramitar_dialog(cur_d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')
                            else:
                                ui.button('Detalhes / Parecer', on_click=lambda cur_d=d: open_tramitar_dialog(cur_d, user_name_guerra, is_approver, render_content.refresh)).props('flat color=cyan dense').classes('text-xs')

            with ui.tab_panels(tabs, value=initial_tab).classes('w-full bg-transparent no-shadow q-pa-none q-mt-md'):
                
                # --- ABA PENDENTES ---
                with ui.tab_panel(tab_pend):
                    if pendentes:
                        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for d in pendentes:
                                render_homologar_card(d, 'pendente')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('check_circle', size='3rem', color='green')
                            ui.label('Nenhuma pauta pendente de homologação.').classes('text-xs')

                # --- ABA APROVADAS ---
                with ui.tab_panel(tab_aprov):
                    if aprovadas:
                        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for d in aprovadas:
                                render_homologar_card(d, 'aprovada')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('event_available', size='3rem')
                            ui.label('Nenhuma pauta aprovada em andamento.').classes('text-xs')

                # --- ABA AJUSTES ---
                with ui.tab_panel(tab_ajust):
                    if ajustes:
                        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for d in ajustes:
                                render_homologar_card(d, 'ajustes')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('thumb_up', size='3rem')
                            ui.label('Nenhuma pauta aguardando ajustes.').classes('text-xs')

                # --- ABA CONCLUÍDAS ---
                with ui.tab_panel(tab_concl):
                    if concluidas:
                        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for d in concluidas:
                                render_homologar_card(d, 'concluida')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                            ui.icon('task_alt', size='3rem')
                            ui.label('Nenhuma pauta concluída registrada.').classes('text-xs')

                # --- ABA REJEITADAS ---
                with ui.tab_panel(tab_rej):
                    if rejeitadas:
                        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for d in rejeitadas:
                                render_homologar_card(d, 'rejeitada')
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
