"""
comsoc_galeria.py - Galeria de Fotos & Acervo Digital
Visualizacao de fotos locais e do Google Drive, upload direto,
busca inteligente por IA, curadoria e distribuicao via Telegram.
"""
import os
import sys
import subprocess
import asyncio
from nicegui import ui, app, events
import theme
from database import get_db_connection
import drive_service
from comsoc_galeria_components import (
    fuzzy_search, ai_search, get_local_photos, get_drive_folder_id,
    check_worker_status, empty_state, render_drive_grid,
    render_moderation, render_pessoal, GALERIA_DIR
)

THEME = theme.colors
_ACTIVE_WATCHERS = {}


def render_page(evento_id: str = None, **kwargs):
    user_data = app.storage.user.get('user_data', {})
    user_id = user_data.get('id')
    user_role = str(user_data.get('role', '')).strip().lower()
    is_operator = user_role in ['admin', 'supervisor', 'operador', 'comsoc', 'comsoc_design']

    # ── Carregar pautas/eventos ──
    pautas_options = {}
    pautas_data = {}
    db = get_db_connection()
    if db:
        try:
            res_p = db.table('demandas_comunicacao').select('*').in_(
                'status', ['aprovada', 'concluida']
            ).order('data_evento', desc=True).execute()
            if res_p.data:
                for p in res_p.data:
                    ev_id = str(p['id'])
                    has_drive = bool(get_drive_folder_id(p))
                    local_count = len(get_local_photos(ev_id))
                    icon = chr(128193) if has_drive else (chr(128247) if local_count > 0 else chr(128204))
                    count_txt = f" ({local_count} fotos)" if local_count > 0 else ""
                    pautas_options[ev_id] = f"{icon} {p.get('data_evento', '')} - {p.get('titulo_evento', '')}{count_txt}"
                    pautas_data[ev_id] = p
        except Exception as e:
            print(f"[GALERIA] [ERR] Erro ao carregar pautas: {e}")

    if not pautas_options:
        pautas_options['geral'] = 'Geral / Sem Pauta'

    sel_id = str(evento_id) if evento_id and str(evento_id) in pautas_options else list(pautas_options.keys())[0]
    page_state = {'pauta_id': sel_id, 'curation_mode': False, 'selected_files': set()}

    # ─── HEADER ───
    with ui.row().classes('w-full justify-between items-center q-mb-md q-px-md flex-wrap gap-2'):
        ui.label('GALERIA DE FOTOS & ACERVO').classes('text-2xl font-bold text-white cyber-title gt-xs')
        with ui.row().classes('gap-2 items-center'):
            ws = check_worker_status()
            if ws == 'online':
                ui.badge('GPU Online', color='positive').classes('text-xs font-bold q-pa-xs')
            else:
                ui.badge('GPU Offline', color='warning').classes('text-xs font-bold q-pa-xs text-black')

    # ─── SELETOR DE EVENTO + BUSCA IA ───
    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-sm').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full items-end gap-3 flex-wrap'):
            with ui.column().classes('flex-grow min-w-[250px] gap-1'):
                ui.label('Selecione o Evento').classes('text-xs font-bold text-cyan')
                event_select = ui.select(
                    pautas_options, value=page_state['pauta_id'],
                    on_change=lambda e: _on_event_change(e.value)
                ).props('dark outlined dense option-dark').classes('w-full')

            with ui.column().classes('min-w-[200px] gap-1'):
                ui.label('Busca Inteligente (IA)').classes('text-xs font-bold text-amber-4')
                with ui.row().classes('w-full gap-1 items-center'):
                    search_input = ui.input(placeholder='Ex: almoco com senador...').props('dark outlined dense').classes('flex-grow')
                    ui.button(icon='search', on_click=lambda: _do_smart_search(search_input.value)).props('dense round color=amber text-color=black')

        search_results_box = ui.column().classes('w-full q-mt-sm gap-1')
        search_results_box.set_visibility(False)

    def _on_event_change(new_id):
        page_state['pauta_id'] = new_id
        event_select.set_value(new_id)
        render_main_content.refresh()

    async def _do_smart_search(query):
        if not query or len(query.strip()) < 2:
            ui.notify('Digite ao menos 2 caracteres.', color='warning')
            return
        search_results_box.clear()
        search_results_box.set_visibility(True)
        # Fase 1: fuzzy local
        fuzzy = fuzzy_search(query, pautas_options)
        # Fase 2: IA se fuzzy fraco
        ai_res = []
        if not fuzzy or fuzzy[0][1] < 0.7:
            with search_results_box:
                ui.label('Consultando IA...').classes('text-xs text-grey-4 animate-pulse')
            ai_res = await ai_search(query, pautas_options)
        # Combinar
        combined = {}
        for eid, score, label in fuzzy:
            combined[eid] = (score, label, 'Fuzzy')
        for eid, score, label in ai_res:
            if eid not in combined or combined[eid][0] < score:
                combined[eid] = (score, label, 'IA')
        sorted_r = sorted(combined.items(), key=lambda x: x[1][0], reverse=True)[:8]
        search_results_box.clear()
        if not sorted_r:
            with search_results_box:
                ui.label('Nenhum evento encontrado.').classes('text-xs text-grey-5')
            return
        with search_results_box:
            ui.label(f'{len(sorted_r)} resultado(s):').classes('text-xs text-grey-4')
            for eid, (score, label, src) in sorted_r:
                pct = int(score * 100)
                with ui.row().classes('w-full items-center gap-2 q-py-xs cursor-pointer hover:bg-white/5 rounded q-px-sm').on(
                    'click', lambda _, _id=eid: (_on_event_change(_id), search_results_box.set_visibility(False))
                ):
                    ui.badge(f'{src} {pct}%', color='cyan' if src == 'IA' else 'grey-7').classes('text-[9px]')
                    ui.label(label).classes('text-xs text-white truncate flex-grow')

    # ─── BARRA DE AÇÕES ORGANIZADA POR FLUXOS COERENTES ───
    with ui.card().classes('w-full q-pa-md no-shadow rounded-2xl q-mb-sm').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full justify-between items-center gap-3 flex-wrap'):
            def _open_drive():
                p = pautas_data.get(str(page_state['pauta_id']), {})
                from database import get_demanda_drive_url
                fid = get_drive_folder_id(p)
                drive_url = get_demanda_drive_url(p)
                if drive_url or fid:
                    target = drive_url or f"https://drive.google.com/drive/folders/{fid}"
                    ui.open(target, new_tab=True)
                else:
                    ui.notify('Pasta do Google Drive não vinculada a este evento.', color='warning')

            # Grupo 1: Integração Google Drive & Sincronização
            with ui.row().classes('items-center gap-2 flex-wrap'):
                ui.badge('☁️ GOOGLE DRIVE', color='blue-10').classes('text-[10px] font-black text-cyan-3 tracking-wider q-px-sm')
                ui.button('Abrir Pasta', icon='folder_open', on_click=_open_drive).props('unelevated color=blue-9 text-color=white no-caps').classes('text-xs font-bold px-3 py-1.5 rounded-xl hover:brightness-110').tooltip('Abrir a pasta deste evento no Google Drive')
                if is_operator:
                    ui.button('Sincronizar Acervo', icon='sync', on_click=lambda: _sincronizar_todas_pastas_drive()).props('unelevated color=cyan-8 text-color=black no-caps').classes('text-xs font-black px-3 py-1.5 rounded-xl hover:brightness-110').tooltip('Varre o Google Drive e vincula todas as pastas aos eventos')
                    ui.button('Vincular / Criar Pasta', icon='add_link', on_click=lambda: _abrir_vincular()).props('unelevated color=amber-8 text-color=black no-caps').classes('text-xs font-bold px-3 py-1.5 rounded-xl hover:brightness-110').tooltip('Vincular link manual ou gerar nova pasta no Drive')

            # Grupo 2: Entrega Hot & Reconhecimento IA
            with ui.row().classes('items-center gap-2 flex-wrap'):
                ui.badge('🚀 ENTREGA & IA', color='purple-10').classes('text-[10px] font-black text-amber-3 tracking-wider q-px-sm')
                if is_operator:
                    ui.button('Portal do Convidado (Hot Delivery)', icon='qr_code_2', on_click=lambda: _abrir_portal_convidado()).props('unelevated color=amber-9 text-color=white no-caps').classes('text-xs font-black px-3.5 py-1.5 rounded-xl cyber-glow hover:brightness-110').tooltip('Gerenciar QR Code e entrega de fotos por Reconhecimento Facial')
                    ui.button('Distribuir no Telegram', icon='send', on_click=lambda: _abrir_distribuir()).props('unelevated color=green-7 text-color=white no-caps').classes('text-xs font-bold px-3 py-1.5 rounded-xl hover:brightness-110').tooltip('Disparar fotos para militares e canais do Telegram')
                ui.button('Biometria Facial', icon='face', on_click=lambda: _abrir_biometria()).props('unelevated color=purple-7 text-color=white no-caps').classes('text-xs font-bold px-3 py-1.5 rounded-xl hover:brightness-110').tooltip('Cadastrar foto para reconhecimento facial')

    # ─── MURAL DE EVENTOS RECENTES & ACERVO ───
    with ui.card().classes('w-full q-pa-md no-shadow rounded-2xl q-mb-sm').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full justify-between items-center q-mb-sm'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('collections_bookmark', color='cyan-4').classes('text-lg')
                ui.label('Mural de Eventos & Acervo Oficial').classes('text-sm font-bold text-cyan')
            with ui.row().classes('items-center gap-2'):
                ui.label('Legenda:').classes('text-[10px] text-grey-4')
                ui.icon('cloud_done', size='16px', color='green').tooltip('Conectado ao Google Drive')
                ui.icon('cloud_off', size='16px', color='grey').tooltip('Pendente de pasta no Drive')
                ui.badge(f'{len(pautas_data)} eventos', color='primary').classes('text-xs font-bold')

        if pautas_data:
            with ui.element('div').classes('w-full overflow-auto').style('max-height: 320px;'):
                with ui.element('table').classes('w-full').style(
                    'border-collapse: collapse; font-size: 12px;'
                ):
                    # Header
                    with ui.element('thead'):
                        with ui.element('tr').style('border-bottom: 1px solid rgba(0,229,255,0.2); background: rgba(0,0,0,0.25);'):
                            for h in ['Data', 'Evento / Pauta', 'Fotos', 'Status Drive', 'Ações']:
                                with ui.element('th').classes('text-left text-cyan-3 font-bold q-pa-sm'):
                                    ui.label(h)
                                    
                    # Funções de ação do mural
                    def _open_drive_tab(link_url):
                        if link_url:
                            ui.run_javascript(f'window.open("{link_url}", "_blank");')
                        else:
                            ui.notify('Link do Google Drive não disponível para este evento.', color='warning')

                    def _carregar_galeria_evento(target_id, target_name):
                        _on_event_change(target_id)
                        ui.notify(f'📂 Carregando galeria: {target_name}', color='positive', timeout=2500)
                        ui.run_javascript('window.scrollTo({ top: 400, behavior: "smooth" });')

                    # Body
                    with ui.element('tbody'):
                        for eid, ev in list(pautas_data.items())[:100]:
                            raw_dt = str(ev.get('data_evento') or '').strip()
                            data_ev = raw_dt[:10] if raw_dt and raw_dt.upper() != 'ASD' else 'ASD'
                            titulo = ev.get('titulo_evento', 'Sem título')
                            from database import get_demanda_drive_url
                            dfid = get_drive_folder_id(ev)
                            drive_url = get_demanda_drive_url(ev)
                            n_local = len(get_local_photos(eid))
                            is_sel = str(eid) == str(page_state['pauta_id'])
                            row_bg = 'background: rgba(0,229,255,0.12); border-left: 3px solid #00e5ff;' if is_sel else ''

                            with ui.element('tr').style(
                                f'border-bottom: 1px solid rgba(255,255,255,0.05); {row_bg}'
                            ).classes('hover:bg-white/5 transition-colors'):
                                # Data
                                with ui.element('td').classes('q-pa-sm text-grey-3 font-mono text-xs'):
                                    if data_ev == 'ASD':
                                        ui.badge('ASD', color='amber').classes('text-[10px] text-black font-bold').tooltip('Data a Definir (ASD)')
                                    else:
                                        ui.label(data_ev)

                                # Evento
                                with ui.element('td').classes('q-pa-sm cursor-pointer').on('click', lambda _, _id=eid, _t=titulo: _carregar_galeria_evento(_id, _t)):
                                    ui.label(titulo).classes(
                                        'text-xs text-cyan-2 font-bold' if is_sel else 'text-xs text-white font-medium hover:text-cyan'
                                    )

                                # Fotos
                                with ui.element('td').classes('q-pa-sm text-center'):
                                    if n_local > 0:
                                        ui.badge(f'📸 {n_local}', color='cyan-9').classes('text-[10px] font-bold')
                                    elif dfid or drive_url:
                                        ui.badge('☁️ Nuvem', color='blue-grey-9').classes('text-[10px] font-semibold text-grey-2')
                                    else:
                                        ui.label('-').classes('text-xs text-grey-6')

                                # Status Drive
                                with ui.element('td').classes('q-pa-sm text-center'):
                                    if dfid or drive_url:
                                        ui.icon('cloud_done', size='18px', color='green').tooltip('Pasta vinculada no Google Drive')
                                    else:
                                        ui.icon('cloud_off', size='18px', color='grey-6').tooltip('Sem pasta vinculada')

                                # Botões de Ação Ampliados
                                with ui.element('td').classes('q-pa-sm'):
                                    with ui.row().classes('gap-2 items-center no-wrap'):
                                        if drive_url or dfid:
                                            target_link = drive_url or f"https://drive.google.com/drive/folders/{dfid}"
                                            ui.button('Drive', icon='open_in_new', on_click=lambda _, l=target_link: _open_drive_tab(l)).props(
                                                'unelevated dense color=blue-8 text-color=white no-caps'
                                            ).classes('text-[11px] font-bold px-2.5 py-1 rounded-lg hover:brightness-110').tooltip('Abrir pasta no Google Drive em nova aba')
                                        
                                        ui.button('Ver Galeria', icon='photo_library', on_click=lambda _, _id=eid, _t=titulo: _carregar_galeria_evento(_id, _t)).props(
                                            'unelevated dense color=amber-8 text-color=black no-caps'
                                        ).classes('text-[11px] font-bold px-2.5 py-1 rounded-lg hover:brightness-110 cyber-glow').tooltip('Carregar fotos deste evento na tela')
        else:
            empty_state('event_busy', 'Nenhum evento cadastrado ainda.')

    # ─── UPLOAD DE FOTOS ───
    if is_operator:
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-sm').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid rgba(0, 229, 255, 0.2);'
        ):
            ui.label('Upload Rapido de Fotos').classes('text-sm font-bold text-cyan q-mb-xs')
            ui.label('Arraste fotos .jpg/.jpeg para o evento selecionado').classes('text-[10px] text-grey-5 q-mb-sm')

            async def handle_photo_upload(e: events.UploadEventArguments):
                content = e.content.read()
                fname = e.name
                if not fname.lower().endswith(('.jpg', '.jpeg')):
                    ui.notify('Apenas .jpg e .jpeg aceitos.', color='negative')
                    return
                pid = page_state['pauta_id']
                local_dir = os.path.join(GALERIA_DIR, str(pid))
                os.makedirs(local_dir, exist_ok=True)
                with open(os.path.join(local_dir, fname), 'wb') as f:
                    f.write(content)
                ui.notify(f'Foto {fname} salva!', color='positive')
                # Drive em background
                pauta = pautas_data.get(str(pid), {})
                fid = get_drive_folder_id(pauta)
                if fid:
                    try:
                        drive_service.upload_file(content, fname, fid)
                    except Exception:
                        pass
                render_main_content.refresh()

            ui.upload(on_upload=handle_photo_upload, auto_upload=True, multiple=True,
                      label='Clique ou arraste fotos aqui').props('accept=".jpg,.jpeg" flat bordered color=cyan dark').classes('w-full').style('min-height: 80px;')

    # ─── CONTEUDO PRINCIPAL ───
    @ui.refreshable
    def render_main_content():
        pid = page_state['pauta_id']
        pauta = pautas_data.get(str(pid), {})
        dfid = get_drive_folder_id(pauta)
        local_photos = get_local_photos(pid)
        drive_photos, drive_selecao, selecao_fid = [], [], None
        if dfid:
            try:
                drive_photos = drive_service.list_files(dfid, mime_filter='image/', page_size=5000) or []
                selecao_fid = drive_service.find_folder('SELEÇÃO', dfid)
                if selecao_fid:
                    drive_selecao = drive_service.list_files(selecao_fid, mime_filter='image/', page_size=5000) or []
            except Exception as e:
                print(f"[GALERIA] [WARN] Drive list: {e}")
        n_local, n_drive, n_sel = len(local_photos), len(drive_photos), len(drive_selecao)

        # Info do evento
        if pauta.get('titulo_evento'):
            with ui.row().classes('w-full items-center gap-2 q-mb-sm q-px-xs'):
                ui.label(pauta.get('titulo_evento', '')).classes('text-sm font-bold text-white')
                ui.badge(f'{n_local + n_drive} fotos', color='primary').classes('text-xs')
                ui.badge('Drive OK' if dfid else 'Sem Drive', color='positive' if dfid else 'grey-7').classes('text-[9px]')

        with ui.tabs().classes('w-full text-cyan flex-wrap') as tabs:
            tl = ui.tab(f'Fotos Locais ({n_local})', icon='photo_library')
            td = ui.tab(f'Google Drive ({n_drive})', icon='cloud')
            ts = ui.tab(f'Selecao ({n_sel})', icon='star')
            if is_operator:
                tm = ui.tab('Moderacao IA', icon='fact_check')
            tp = ui.tab('Minhas Fotos', icon='face')

        default = tl if n_local > 0 else (td if n_drive > 0 else tl)
        with ui.tab_panels(tabs, value=default).classes('w-full bg-transparent no-shadow q-pa-none q-mt-sm'):
            with ui.tab_panel(tl):
                if local_photos:
                    with ui.element('div').classes('w-full gap-3').style(
                        'display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));'
                    ):
                        for f in sorted(local_photos):
                            wp = f"/assets/galeria_hot/{pid}/{f}"
                            with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden cursor-pointer hover-scale').style(
                                f'background: {THEME["bg_editor"]}; border: 1px solid {THEME["border"]};'
                            ).on('click', lambda _, p=wp: _lightbox(p)):
                                ui.image(wp).classes('w-full').style('height: 150px; object-fit: cover;')
                                with ui.row().classes('w-full q-pa-xs items-center bg-black/50'):
                                    ui.label(f[:20] + '...' if len(f) > 20 else f).classes('text-[9px] text-grey-3 truncate flex-grow')
                                    ui.badge('Local', color='cyan').classes('text-[8px]')
                else:
                    empty_state('photo_library', 'Nenhuma foto local. Use o upload acima ou envie pelo Telegram.')

            with ui.tab_panel(td):
                if not dfid:
                    empty_state('cloud_off', 'Pasta do Google Drive nao vinculada.')
                    if is_operator:
                        with ui.row().classes('w-full justify-center q-mt-md gap-2'):
                            ui.button('Criar Pasta', icon='create_new_folder', on_click=lambda: _criar_pasta()).props('unelevated color=blue-7').classes('text-xs')
                            ui.button('Vincular Link', icon='link', on_click=lambda: _abrir_vincular()).props('outline color=cyan').classes('text-xs')
                elif drive_photos:
                    render_drive_grid(drive_photos, page_state, is_operator, selecao_fid, THEME)
                else:
                    empty_state('cloud_done', 'Pasta vinculada mas sem fotos ainda.')

            with ui.tab_panel(ts):
                if drive_selecao:
                    render_drive_grid(drive_selecao, page_state, is_operator, None, THEME, is_selecao=True)
                else:
                    empty_state('star_border', 'Nenhuma foto na SELECAO. Use Curadoria na aba Drive.')

            if is_operator:
                with ui.tab_panel(tm):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                        ui.label('Fotos em Moderacao (Reconhecimento Facial)').classes('text-md font-bold text-cyan q-mb-md')
                        render_moderation(user_data, THEME)

            with ui.tab_panel(tp):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                    ui.label('Minha Galeria Pessoal (IA)').classes('text-md font-bold text-cyan q-mb-md')
                    render_pessoal(user_id, THEME)

    render_main_content()

    # ─── DIALOGS ──────────────────────────────────────────────────────
    def _lightbox(path):
        with ui.dialog() as dlg, ui.card().classes('q-pa-none max-w-4xl max-h-[90vh] overflow-hidden').style('background: transparent;'):
            with ui.row().classes('w-full justify-end q-pa-sm absolute top-0 right-0 z-10'):
                ui.button(icon='close', on_click=dlg.close).props('flat round dense text-color=white')
            ui.image(path).style('max-height: 85vh; object-fit: contain;')
        dlg.open()

    def _abrir_biometria():
        pauta = pautas_data.get(str(page_state['pauta_id']), {})
        slug = str(pauta.get('id', '50'))
        titulo_ev = (pauta.get('titulo_evento') or 'Evento Selecionado').upper()

        with ui.dialog() as dlg_bio, ui.card().classes('w-[780px] max-w-[96vw] max-h-[92vh] q-pa-lg rounded-3xl bg-slate-950 border-2 border-purple-500/40 text-white flex flex-col justify-start overflow-y-auto').style('box-shadow: 0 0 45px rgba(168,85,247,0.25);'):
            # Header
            with ui.row().classes('w-full justify-between items-center border-b border-purple-500/20 pb-3 mb-3'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('face_retouching_natural', size='2rem', color='purple-4')
                    with ui.column().classes('gap-0'):
                        ui.label('CENTRAL DE BIOMETRIA FACIAL & IA').classes('text-base font-black text-purple-3 cyber-title')
                        ui.label(f'Evento Ativo: {titulo_ev} (ID: #{slug})').classes('text-xs text-grey-4 truncate max-w-[450px]')
                ui.button(icon='close', on_click=dlg_bio.close).props('flat round dense text-color=grey-4')

            with ui.tabs().classes('w-full text-purple-3 border-b border-white/10') as bio_tabs:
                t_cad = ui.tab('cad', label='👤 1. Cadastrar / Atualizar Biometria', icon='badge')
                t_search = ui.tab('search', label='🔍 2. Localizar Fotos no Evento', icon='manage_search')
                t_list = ui.tab('list', label='📋 3. Militares Cadastrados', icon='groups')

            with ui.tab_panels(bio_tabs, value=t_cad).classes('w-full bg-transparent p-0 q-mt-md'):
                
                # ── ABA 1: CADASTRAR BIOMETRIA ──
                with ui.tab_panel(t_cad).classes('w-full p-2 gap-4 flex flex-col'):
                    with ui.card().classes('w-full bg-slate-900/90 border border-purple-500/30 p-4 rounded-2xl gap-3'):
                        ui.label('Identificação do Militar / Autoridade:').classes('text-xs font-bold text-amber-3')
                        with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-3 gap-2'):
                            in_nome = ui.input('Nome de Guerra / Completo', value=user_data.get('nome_guerra') or user_data.get('nome') or '').props('dark outlined dense')
                            in_posto = ui.input('Posto / Graduação', value=user_data.get('posto_grad') or '').props('dark outlined dense')
                            in_tg = ui.input('Telegram ID (opcional)', value=str(user_data.get('telegram_id') or '')).props('dark outlined dense')

                        ui.separator().classes('my-1 border-white/10')
                        ui.label('Foto / Selfie para Treinamento Biométrico (Rosto Nitido e Centralizado):').classes('text-xs font-bold text-cyan-3')
                        
                        bio_preview_box = ui.column().classes('w-full items-center justify-center p-3 bg-black/50 border border-dashed border-purple-500/40 rounded-xl min-h-[120px] gap-2')
                        with bio_preview_box:
                            ui.icon('add_a_photo', size='2rem', color='purple-4')
                            ui.label('Selecione ou tire uma foto frontal clara').classes('text-xs text-grey-4')

                        uploaded_bio_bytes = {'data': None}

                        async def handle_bio_upload(e):
                            fb = e.content.read()
                            uploaded_bio_bytes['data'] = fb
                            bio_preview_box.clear()
                            with bio_preview_box:
                                import base64
                                b64_img = base64.b64encode(fb).decode('utf-8')
                                ui.image(f"data:image/jpeg;base64,{b64_img}").classes('w-32 h-32 rounded-2xl object-cover border-2 border-purple-400')
                                ui.label(f'Foto carregada ({len(fb) // 1024} KB)').classes('text-xs text-green-4 font-bold')

                        ui.upload(on_upload=handle_bio_upload, auto_upload=True).props('accept="image/*" w-full').classes('q-mb-sm')

                        async def salvar_biometria_militar():
                            if not uploaded_bio_bytes['data']:
                                ui.notify('Envie uma foto ou tire uma selfie primeiro!', color='warning')
                                return
                            nome = (in_nome.value or '').strip()
                            if not nome:
                                ui.notify('Preencha o Nome de Guerra ou Nome Completo!', color='warning')
                                return

                            n_bio = ui.notify('🧠 Extraindo vetor facial com InsightFace...', color='info', spinner=True, timeout=0)
                            try:
                                import sisgab_face_worker
                                ok, msg, emb = sisgab_face_worker.evaluate_selfie_quality(uploaded_bio_bytes['data'])
                                if not ok or emb is None:
                                    n_bio.dismiss()
                                    ui.notify(f'Qualidade Insuficiente: {msg}', color='negative', timeout=5000)
                                    return

                                from database import save_guest_face_profile
                                pid = save_guest_face_profile(
                                    event_id='global_militar',
                                    embedding=emb,
                                    email=f"{in_tg.value or 'militar'}@sisgab.mil.br",
                                    nome=f"{in_posto.value} {nome}".strip()
                                )
                                n_bio.dismiss()
                                ui.notify(f'✅ Biometria de {nome} cadastrada e ativada com sucesso! (ID: {pid})', color='positive', timeout=6000)
                            except Exception as ex_bio:
                                n_bio.dismiss()
                                ui.notify(f'Erro ao processar biometria: {ex_bio}', color='negative')

                        ui.button('💾 Salvar & Ativar Biometria Facial', icon='save', on_click=salvar_biometria_militar).props('unelevated color=purple-8 text-color=white bold w-full').classes('h-12 rounded-xl cyber-glow')

                # ── ABA 2: BUSCAR FOTOS NESTE EVENTO (INSTANT MATCH) ──
                with ui.tab_panel(t_search).classes('w-full p-2 gap-4 flex flex-col'):
                    with ui.card().classes('w-full bg-slate-900/90 border border-cyan-500/30 p-4 rounded-2xl gap-3'):
                        ui.label(f'Localizador Facial no Evento #{slug}: {titulo_ev}').classes('text-xs font-bold text-cyan-3')
                        ui.label('Compara a selfie do militar contra todas as fotos indexadas deste evento.').classes('text-xs text-grey-4')

                        thresh_slider = ui.slider(min=0.35, max=0.70, step=0.01, value=0.45).props('dark label-always color=cyan')
                        ui.label(f'Threshold de Similaridade: {thresh_slider.value:.2f} (0.45 = Padrão)').classes('text-[11px] text-grey-5')

                        results_container = ui.column().classes('w-full gap-2 q-mt-2')

                        async def buscar_fotos_evento():
                            if not uploaded_bio_bytes['data']:
                                ui.notify('Faça upload de uma selfie na Aba 1 para comparar!', color='warning')
                                return

                            results_container.clear()
                            n_match = ui.notify('🔍 Analisando acervo do evento...', color='info', spinner=True, timeout=0)
                            try:
                                import sisgab_face_worker
                                ok, msg, query_emb = sisgab_face_worker.evaluate_selfie_quality(uploaded_bio_bytes['data'])
                                if not ok or query_emb is None:
                                    n_match.dismiss()
                                    ui.notify(f'Erro na selfie: {msg}', color='negative')
                                    return

                                from database import get_event_photo_embeddings
                                all_embs = get_event_photo_embeddings(slug)
                                if not all_embs:
                                    n_match.dismiss()
                                    with results_container:
                                        with ui.card().classes('w-full p-4 bg-black/60 border border-amber-500/30 rounded-xl text-center gap-2'):
                                            ui.icon('info', size='2rem', color='amber-4')
                                            ui.label('Nenhuma foto indexada com IA neste evento ainda.').classes('text-sm font-bold text-amber-3')
                                            ui.label('Execute o Watcher de fotos no seu PC (com GPU) para extrair os rostos do evento!').classes('text-xs text-grey-4')
                                    return

                                q_vec = np.array(query_emb, dtype=np.float32)
                                q_norm = np.linalg.norm(q_vec)
                                if q_norm > 0:
                                    q_vec = q_vec / q_norm

                                matches = []
                                for rec in all_embs:
                                    r_emb = rec.get('embedding')
                                    if not r_emb: continue
                                    r_vec = np.array(r_emb, dtype=np.float32)
                                    r_norm = np.linalg.norm(r_vec)
                                    if r_norm > 0: r_vec = r_vec / r_norm
                                    sim = float(np.dot(q_vec, r_vec))
                                    if sim >= float(thresh_slider.value):
                                        matches.append((sim, rec))

                                matches.sort(key=lambda x: x[0], reverse=True)
                                n_match.dismiss()

                                with results_container:
                                    if not matches:
                                        ui.label(f'Nenhuma foto encontrada com similaridade ≥ {thresh_slider.value:.2f}. Tente diminuir o threshold no slider.').classes('text-xs text-amber-4 italic p-2')
                                    else:
                                        ui.label(f'🎉 {len(matches)} foto(s) localizada(s) com sucesso!').classes('text-sm font-black text-green-4')
                                        with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-h-80 overflow-y-auto p-1'):
                                            for sim, rec in matches:
                                                fid = rec.get('drive_file_id')
                                                fname = rec.get('photo_filename') or f'foto_{fid[:8]}.jpg'
                                                dlink = rec.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view"
                                                with ui.card().classes('p-2 bg-black/80 border border-cyan-500/40 rounded-xl flex flex-col items-center gap-1'):
                                                    ui.label(f'{sim:.1%} Match').classes('text-xs font-black text-amber-3 bg-amber-900/60 px-2 py-0.5 rounded-full')
                                                    ui.label(fname).classes('text-[10px] text-white font-mono truncate w-full text-center')
                                                    ui.button('Abrir no Drive', icon='open_in_new', on_click=lambda l=dlink: ui.open(l, new_tab=True)).props('flat dense color=cyan text-color=cyan').classes('text-[10px]')

                            except Exception as ex_m:
                                n_match.dismiss()
                                ui.notify(f'Erro na busca: {ex_m}', color='negative')

                        ui.button('🚀 BUSCAR MINHAS FOTOS NESTE EVENTO', icon='search', on_click=buscar_fotos_evento).props('unelevated color=cyan-8 text-color=black bold w-full').classes('h-12 rounded-xl cyber-glow')

                # ── ABA 3: PERFIS CADASTRADOS ──
                with ui.tab_panel(t_list).classes('w-full p-2 gap-3 flex flex-col'):
                    with ui.card().classes('w-full bg-slate-900/90 border border-slate-800 p-4 rounded-2xl gap-2'):
                        from database import get_guest_profiles_for_event
                        profiles = get_guest_profiles_for_event('global_militar') + get_guest_profiles_for_event(slug)
                        if not profiles:
                            ui.label('Nenhum perfil biométrico registrado ainda.').classes('text-xs text-grey-5 italic')
                        else:
                            ui.label(f'Total de Perfis Ativos: {len(profiles)}').classes('text-xs font-bold text-purple-3')
                            with ui.column().classes('w-full gap-1.5 max-h-80 overflow-y-auto font-mono text-xs'):
                                for prof in profiles:
                                    with ui.row().classes('w-full items-center justify-between p-2 bg-black/40 rounded-xl border border-white/5'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label('👤').classes('text-sm')
                                            ui.label(prof.get('nome') or prof.get('email') or f"Perfil #{prof.get('id')}").classes('text-white font-bold')
                                        ui.badge(prof.get('event_id', 'global'), color='purple-9').classes('text-[10px]')

        dlg_bio.open()

    def _abrir_distribuir(pauta=None):
        if pauta is None:
            pauta = pautas_data.get(str(page_state['pauta_id']), {})
        if not pauta or not pauta.get('id'):
            ui.notify('Selecione um evento para distribuir o acervo.', color='warning')
            return

        from database import get_demanda_drive_url, get_db_connection
        titulo = (pauta.get('titulo_evento') or 'Sem Título').upper()
        data_ev = pauta.get('data_evento', '')
        local_ev = pauta.get('local_evento', 'CGCFN')
        drive_url = get_demanda_drive_url(pauta)
        fid = get_drive_folder_id(pauta)
        if not drive_url and fid:
            drive_url = f"https://drive.google.com/drive/folders/{fid}"

        # Carregar militares cadastrados no efetivo
        militares_opts = {}
        todos_tids = []
        c = get_db_connection()
        if c:
            try:
                r = c.table('efetivo').select('nome_guerra, posto_grad, telegram_id').not_('telegram_id', 'is', 'null').execute()
                if r.data:
                    for ef in r.data:
                        tg = str(ef.get('telegram_id') or '').strip()
                        if tg and tg.isdigit():
                            lbl = f"{ef.get('posto_grad', '')} {ef.get('nome_guerra', '')}".strip()
                            militares_opts[tg] = f"👤 {lbl} (ID: {tg})"
                            todos_tids.append(tg)
            except Exception:
                pass

        # Texto padrão formatado para WhatsApp / Telegram
        texto_padrao = (
            f"📸 *ACERVO FOTOGRÁFICO — CGCFN / COMSOC*\n\n"
            f"📌 *Evento:* {titulo}\n"
            f"📅 *Data:* {data_ev}\n"
            f"📍 *Local:* {local_ev}\n\n"
            f"📁 *Pasta Completa no Google Drive:*\n{drive_url or 'Link não disponível'}\n\n"
            f"📱 *SisGAB — Comando-Geral do Corpo de Fuzileiros Navais*"
        )

        with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-2xl w-full rounded-3xl bg-slate-950 border border-cyan-500/40 text-white flex flex-col gap-3').style('box-shadow: 0 0 35px rgba(0,229,255,0.2);'):
            # Cabeçalho com Resumo do Evento
            with ui.row().classes('w-full justify-between items-center border-b border-cyan-500/20 pb-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('send', size='1.5rem', color='cyan-4')
                    with ui.column().classes('gap-0'):
                        ui.label('DISTRIBUIR ACERVO & LINKS').classes('text-sm font-black text-cyan cyber-title')
                        ui.label(f"{titulo} ({data_ev})").classes('text-xs text-grey-4 truncate max-w-[420px]')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense text-color=grey-4')

            # Abas de Envio
            with ui.tabs().classes('w-full text-cyan border-b border-white/10') as tabs:
                tab_envio = ui.tab('envio', label='📲 Telegram', icon='send')
                tab_zap = ui.tab('whatsapp', label='📋 WhatsApp & Texto', icon='content_copy')

            with ui.tab_panels(tabs, value=tab_envio).classes('w-full bg-transparent p-0 q-mt-sm'):
                
                # ─── PAINEL TELEGRAM ───
                with ui.tab_panel(tab_envio).classes('w-full p-0 gap-3 flex flex-col'):
                    mode_select = ui.select(
                        {
                            'manual': '💬 Digitar ID do Telegram / Canal / Grupo Manualmente',
                            'nominal': '👤 Militar Específico do Efetivo',
                            'todos': f'👥 Todos os Militares Cadastrados ({len(todos_tids)})',
                        },
                        value='manual',
                        label='Tipo de Destinatário'
                    ).props('dark outlined dense w-full option-dark')

                    dest_container = ui.column().classes('w-full gap-2')

                    def render_dest_fields():
                        dest_container.clear()
                        with dest_container:
                            m = mode_select.value
                            if m == 'manual':
                                manual_in = ui.input('ID do Telegram ou @Canal (ex: 5425877837 ou @comsoc_cgcfn)', placeholder='Ex: 5425877837').props('dark outlined dense w-full')
                                dest_container.manual_in = manual_in
                                
                                with ui.card().classes('w-full p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-xl gap-1 text-xs text-cyan-2'):
                                    ui.label('💡 Como a pessoa ou canal descobre o ID do Telegram?').classes('font-bold text-amber-3')
                                    ui.label('• Envie /start ou /meuid no bot oficial @SisGAB_bot no Telegram.')
                                    ui.label('• Ou consulte o bot oficial @userinfobot para obter o Chat ID numérico.')
                                    ui.label('• Para canais/grupos: digite o @nomedocanal ou o ID numérico (começado com -100).')
                            elif m == 'nominal':
                                if militares_opts:
                                    mil_in = ui.select(militares_opts, value=list(militares_opts.keys())[0], label='Selecione o Militar').props('dark outlined dense w-full option-dark')
                                    dest_container.mil_in = mil_in
                                else:
                                    ui.label('Nenhum militar com Telegram ID cadastrado no efetivo ainda. Use a opção de digitação manual acima.').classes('text-xs text-amber-4 italic p-2 bg-amber-950/30 rounded-lg')
                            elif m == 'todos':
                                ui.label(f'Será enviado para todos os {len(todos_tids)} militares com Telegram vinculado no sistema.').classes('text-xs text-green-4 font-bold p-2 bg-green-950/30 rounded-lg')

                    mode_select.on_value_change(render_dest_fields)
                    render_dest_fields()

                    # Opções do conteúdo
                    with ui.row().classes('w-full items-center justify-between p-2.5 bg-slate-900 rounded-xl border border-white/5'):
                        chk_links = ui.checkbox('🔗 Enviar Link da Pasta do Drive', value=True).props('dark color=cyan dense')
                        chk_album = ui.checkbox('⭐ Enviar Fotos em HD', value=True).props('dark color=amber dense')

                    # Área de Edição da Mensagem
                    ui.label('Mensagem que será enviada:').classes('text-xs font-bold text-grey-3')
                    msg_text_input = ui.textarea(value=texto_padrao).props('dark outlined rows=4 w-full').classes('font-mono text-xs')

                    async def disparar_telegram():
                        mode = mode_select.value
                        target_ids = []
                        if mode == 'manual':
                            v = getattr(dest_container, 'manual_in', None)
                            if v and v.value:
                                target_ids.append(v.value.strip())
                        elif mode == 'nominal':
                            v = getattr(dest_container, 'mil_in', None)
                            if v and v.value:
                                target_ids.append(v.value)
                        elif mode == 'todos':
                            target_ids = todos_tids

                        if not target_ids:
                            ui.notify('Digite ou selecione um destinatário válido!', color='warning')
                            return

                        dlg.close()
                        notif = ui.notify(f"🚀 Enviando acervo para {len(target_ids)} destinatário(s)...", timeout=0, spinner=True, color='info')
                        try:
                            import telegram_bot
                            from telegram_bot.utils import enviar_links_acervo, enviar_album_hd_drive
                            bot = telegram_bot.bot
                            if not bot:
                                notif.dismiss()
                                ui.notify('Bot do Telegram não inicializado.', color='negative')
                                return

                            for cid in target_ids:
                                try:
                                    bot.send_message(cid, msg_text_input.value or texto_padrao, parse_mode='Markdown')
                                    if chk_album.value and fid:
                                        sf = drive_service.find_folder('SELEÇÃO', fid) or fid
                                        await enviar_album_hd_drive(bot, cid, sf)
                                except Exception as ex_item:
                                    print(f"Erro ao enviar para {cid}: {ex_item}")

                            notif.dismiss()
                            ui.notify(f"✅ Disparo concluído com sucesso para {len(target_ids)} destinatário(s)!", color='positive')
                        except Exception as ex_tg:
                            notif.dismiss()
                            ui.notify(f'Erro no disparo: {ex_tg}', color='negative')

                    ui.button('🚀 DISPARAR DISTRIBUIÇÃO TELEGRAM', icon='send', on_click=disparar_telegram).props('unelevated color=cyan-8 text-color=black bold w-full').classes('h-11 rounded-xl cyber-glow')

                # ─── PAINEL WHATSAPP & TEXTO ───
                with ui.tab_panel(tab_zap).classes('w-full p-0 gap-3 flex flex-col'):
                    ui.label('Texto Formatado para WhatsApp / Mensagens:').classes('text-xs font-bold text-amber-3')
                    zap_text = ui.textarea(value=texto_padrao).props('dark outlined rows=6 w-full').classes('font-mono text-xs')

                    import urllib.parse
                    def abrir_whatsapp():
                        txt = zap_text.value or texto_padrao
                        encoded = urllib.parse.quote(txt)
                        ui.open(f"https://api.whatsapp.com/send?text={encoded}", new_tab=True)

                    def copiar_texto():
                        txt = zap_text.value or texto_padrao
                        escaped = txt.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                        ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                    with ui.row().classes('w-full justify-between items-center q-mt-xs'):
                        ui.button('📋 Copiar Texto Padrão', icon='content_copy', on_click=copiar_texto).props(
                            'unelevated color=amber text-color=black bold'
                        ).classes('text-xs')
                        if drive_url:
                            ui.button('📁 Abrir Drive', icon='open_in_new', on_click=lambda: ui.open(drive_url, new_tab=True)).props(
                                'flat dense color=cyan'
                            ).classes('text-xs')

        dlg.open()

    def _abrir_portal_convidado():
        pauta = pautas_data.get(str(page_state['pauta_id']), {})
        if not pauta or not pauta.get('id'):
            ui.notify('Selecione um evento válido para gerenciar o Portal do Convidado.', color='warning')
            return

        p_id = str(pauta.get('id'))
        slug = str(pauta.get('id'))
        titulo = pauta.get('titulo_evento', 'Evento Oficial')
        data_ev = pauta.get('data_evento', '')
        local_ev = pauta.get('local_evento', 'Gabinete do CGCFN')
        drive_fid = get_drive_folder_id(pauta)
        geral_fid = None
        if drive_fid:
            geral_fid = drive_service.find_folder('GERAL', drive_fid) or drive_fid

        from database import (
            get_public_event, create_public_event, update_public_event,
            count_event_embeddings, get_guest_profiles_for_event,
            get_portal_analytics_summary
        )

        ev_pub = get_public_event(slug)
        if not ev_pub:
            create_public_event(
                event_id=slug,
                nome=titulo,
                data_evento=data_ev or '2026-08-15',
                local=local_ev,
                drive_folder_id=drive_fid,
                drive_geral_folder_id=geral_fid,
                demanda_id=int(p_id) if p_id.isdigit() else None
            )
            ev_pub = get_public_event(slug) or {}

        portal_url = f"https://sisgab-cgcfn.ddns.net/evento/{slug}"

        # Diagnóstico de Hardware & GPU em tempo real
        hw_info = {
            'gpu_type': 'CPU (Otimizado)',
            'is_gpu': False,
            'det_size': '320x320',
            'engine_status': 'InsightFace buffalo_l (512D)',
            'provider': 'CPUExecutionProvider'
        }
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if 'CUDAExecutionProvider' in providers:
                hw_info['gpu_type'] = 'NVIDIA CUDA (Alta Performance)'
                hw_info['is_gpu'] = True
                hw_info['det_size'] = '640x640 HD'
                hw_info['provider'] = 'CUDAExecutionProvider'
            elif 'DmlExecutionProvider' in providers:
                hw_info['gpu_type'] = 'DirectML GPU (DirectX 12 — AMD / Intel / NVIDIA)'
                hw_info['is_gpu'] = True
                hw_info['det_size'] = '640x640 HD'
                hw_info['provider'] = 'DmlExecutionProvider'
        except Exception:
            pass

        # Gera QR Code com fallback seguro
        qr_b64 = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&margin=10&data={portal_url}"
        try:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(portal_url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img_qr.save(buf, format="PNG")
            qr_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
        except Exception:
            pass

        # MODAL EXPANDIDO E ESPAÇOSO (940px)
        with ui.dialog() as dlg_portal, ui.card().classes('w-[940px] max-w-[96vw] max-h-[92vh] q-pa-lg rounded-3xl bg-slate-900 border-2 border-cyan-500/30 text-white flex flex-col justify-start overflow-y-auto').style('box-shadow: 0 0 50px rgba(0,229,255,0.2);'):
            
            # CABEÇALHO DO MODAL
            with ui.row().classes('w-full justify-between items-center border-b border-cyan-500/20 pb-3 mb-2'):
                with ui.column().classes('gap-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('qr_code_2', size='1.8rem', color='amber-4')
                        ui.label('🌐 GESTÃO DO PORTAL DO CONVIDADO (HOT DELIVERY)').classes('text-lg font-black text-amber-4 tracking-wider cyber-title')
                    ui.label(f"📌 {titulo.upper()} • 📅 {data_ev or 'Data a definir'} • 📍 {local_ev}").classes('text-xs text-cyan-2 font-medium truncate max-w-[700px]')
                ui.button(icon='close', on_click=dlg_portal.close).props('flat round dense text-color=grey-4')

            # ABAS EM LINHA ÚNICA HORIZONTAL (SEM QUEBRA DE LINHA)
            with ui.tabs().props('dense no-caps inline-label mobile-arrows').classes('w-full text-cyan-3 border-b border-cyan-500/20 q-mb-md') as tabs_p:
                t_cfg = ui.tab('cfg', label='⚙️ 1. Configuração', icon='settings').classes('px-3')
                t_proc = ui.tab('proc', label='🚀 2. Upload & IA (GPU)', icon='memory').classes('px-3 font-bold text-amber-4')
                t_cur = ui.tab('cur', label='📷 3. Curadoria GERAL', icon='collections').classes('px-3')
                t_guest = ui.tab('guest', label='👥 4. Convidados', icon='people').classes('px-3')
                t_qr = ui.tab('qr', label='📱 5. QR Code & Divulgação', icon='qr_code').classes('px-3')

            with ui.tab_panels(tabs_p, value=t_proc).classes('w-full bg-transparent p-0'):
                
                # ── ETAPA 1: CONFIGURAÇÃO ──
                with ui.tab_panel(t_cfg).classes('w-full p-2 gap-4'):
                    with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 gap-4'):
                        with ui.card().classes('p-4 bg-slate-950/80 border border-slate-800 rounded-2xl gap-3'):
                            ui.label('Parâmetros de Operação').classes('text-xs font-bold text-cyan')
                            
                            status_val = ev_pub.get('status', 'ativo')
                            sw_status = ui.switch('Status da Galeria (Ativa / Inativa)', value=(status_val == 'ativo')).props('dark color=green')
                            
                            threshold_slider = ui.slider(min=0.35, max=0.70, step=0.01, value=float(ev_pub.get('threshold_match') or 0.45)).props('dark label-always color=amber')
                            ui.label(f'Threshold de Similaridade Facial: {threshold_slider.value:.2f} (0.45 = Precisão Equilibrada)').classes('text-xs text-grey-4')

                        with ui.card().classes('p-4 bg-slate-950/80 border border-slate-800 rounded-2xl gap-3'):
                            ui.label('Marca d\'Água & Visual').classes('text-xs font-bold text-amber-4')
                            
                            wm_check = ui.checkbox('Aplicar Marca d\'Água Institucional', value=bool(ev_pub.get('watermark_enabled', True))).props('dark color=cyan dense')
                            wm_input = ui.input('Texto da Marca d\'Água', value=ev_pub.get('watermark_text') or 'COMSOC / CGCFN').props('dark outlined dense w-full')
                            banner_input = ui.input('URL do Banner / Cartaz (opcional)', value=ev_pub.get('banner_url') or '').props('dark outlined dense w-full')

                    def salvar_configuracoes():
                        novos_dados = {
                            'status': 'ativo' if sw_status.value else 'inativo',
                            'threshold_match': float(threshold_slider.value),
                            'watermark_enabled': wm_check.value,
                            'watermark_text': (wm_input.value or '').strip(),
                            'banner_url': (banner_input.value or '').strip() or None,
                        }
                        update_public_event(slug, novos_dados)
                        ui.notify('✅ Configurações do Portal salvas com sucesso!', color='positive')

                    ui.button('💾 Salvar Configurações', icon='save', on_click=salvar_configuracoes).props('unelevated color=cyan text-color=black bold w-full').classes('h-11 rounded-xl q-mt-sm')

                # ── ETAPA 2: UPLOAD & PROCESSAMENTO IA (CENTRAL DE HARDWARE E LIVE MONITOR) ──
                with ui.tab_panel(t_proc).classes('w-full p-2 gap-4'):
                    
                    # 1. CARD DE DIAGNÓSTICO DE HARDWARE & IA
                    with ui.card().classes('w-full bg-slate-950/90 border border-cyan-500/30 p-4 rounded-2xl gap-3 shadow-lg'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('developer_board', size='1.5rem', color='cyan-4')
                                ui.label('DIAGNÓSTICO DO MOTOR DE IA & ACELERAÇÃO POR GPU').classes('text-sm font-black text-cyan-3 tracking-wide')
                            
                            if hw_info['is_gpu']:
                                ui.badge('🟢 ACELERAÇÃO POR GPU ATIVA', color='positive').classes('text-xs font-black px-2 py-1')
                            else:
                                ui.badge('🟡 CPU FALLBACK ATIVO', color='amber-9').classes('text-xs font-bold px-2 py-1')

                        with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1'):
                            with ui.column().classes('p-2 bg-black/50 rounded-xl border border-white/5 gap-0.5'):
                                ui.label('🎮 Placa de Vídeo / Hardware').classes('text-[10px] text-grey-4')
                                ui.label(hw_info['gpu_type']).classes('font-bold text-white truncate')
                            
                            with ui.column().classes('p-2 bg-black/50 rounded-xl border border-white/5 gap-0.5'):
                                ui.label('🧠 Motor Facial InsightFace').classes('text-[10px] text-grey-4')
                                ui.label('buffalo_l (512D)').classes('font-bold text-green-4')

                            with ui.column().classes('p-2 bg-black/50 rounded-xl border border-white/5 gap-0.5'):
                                ui.label('🎯 Resolução de Detecção').classes('text-[10px] text-grey-4')
                                ui.label(hw_info['det_size']).classes('font-bold text-amber-4')

                            with ui.column().classes('p-2 bg-black/50 rounded-xl border border-white/5 gap-0.5'):
                                ui.label('⚡ Workers Paralelos').classes('text-[10px] text-grey-4')
                                ui.label('10 Threads Simultâneas').classes('font-bold text-cyan-4')

                    # 2. MÉTRICAS AO VIVO DO EVENTO
                    watcher_dynamic_container = ui.column().classes('w-full gap-3 q-mt-1')

                    def render_watcher_panel():
                        watcher_dynamic_container.clear()
                        with watcher_dynamic_container:
                            emb_count = count_event_embeddings(slug)
                            proc = _ACTIVE_WATCHERS.get(slug)
                            is_running = proc is not None and (proc.poll() is None)

                            # Grid de KPIs
                            with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-4 gap-3'):
                                with ui.card().classes('p-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-center'):
                                    ui.label('📁').classes('text-xl')
                                    ui.label('Status do Watcher').classes('text-[10px] text-grey-4')
                                    if is_running:
                                        ui.label('RODANDO').classes('text-sm font-black text-green-4 animate-pulse')
                                    else:
                                        ui.label('PARADO').classes('text-sm font-bold text-grey-5')

                                with ui.card().classes('p-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-center'):
                                    ui.label('👤').classes('text-xl')
                                    ui.label('Rostos Mapeados').classes('text-[10px] text-grey-4')
                                    ui.label(str(emb_count)).classes('text-xl font-black text-amber-4')

                                with ui.card().classes('p-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-center'):
                                    ui.label('☁️').classes('text-xl')
                                    ui.label('Subpasta GERAL').classes('text-[10px] text-grey-4')
                                    ui.label('Conectada' if geral_fid else 'Pendente').classes('text-sm font-bold text-cyan-4')

                                with ui.card().classes('p-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-center'):
                                    ui.label('⚡').classes('text-xl')
                                    ui.label('Velocidade Upload').classes('text-[10px] text-grey-4')
                                    ui.label('10x Paralelo').classes('text-sm font-bold text-purple-4')

                            # Controles da Pasta e Execução
                            with ui.card().classes('w-full bg-slate-950/90 border border-slate-800 rounded-2xl p-4 gap-3'):
                                ui.label('📂 Pasta Local com as Fotos no seu Computador (com GPU):').classes('text-xs font-bold text-amber-3')
                                pasta_input = ui.input(placeholder='Ex: F:\\CGCFN\\ENCONTRO VETE ou D:\\FOTOS\\50', value=f"D:\\FOTOS\\{slug}").props('dark outlined dense w-full')

                                with ui.row().classes('w-full gap-3 items-center flex-wrap'):
                                    def abrir_info_execucao_local():
                                        caminho_p = pasta_input.value.strip()
                                        cmd_str = f'python event_photo_watcher.py --event-id "{slug}" --pasta "{caminho_p}" --workers 10'
                                        escaped = cmd_str.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                                        
                                        with ui.dialog() as dlg_info, ui.card().classes('bg-slate-900 border border-cyan-500/40 p-6 rounded-3xl max-w-xl w-full text-white gap-4'):
                                            with ui.row().classes('w-full items-center justify-between'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.icon('rocket_launch', size='1.8rem', color='amber-4')
                                                    ui.label('COMO PROCESSAR NA GPU LOCAL').classes('text-base font-black text-amber-4')
                                                ui.button(icon='close', on_click=dlg_info.close).props('flat round dense text-color=grey-4')

                                            ui.label(f'Como a plataforma web está na nuvem (VPS), o processamento acelerado por GPU (InsightFace 512D) e os 10 workers de upload rodam direto no seu PC Windows onde está a pasta:').classes('text-xs text-grey-3 leading-relaxed')
                                            
                                            with ui.element('div').classes('p-3 bg-black/80 rounded-xl border border-white/10 font-mono text-xs text-cyan-3 break-all select-all'):
                                                ui.label(cmd_str)

                                            with ui.row().classes('w-full gap-2 justify-end'):
                                                ui.button('📋 Copiar Comando', icon='content_copy', on_click=lambda: (ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);'), ui.notify('📋 Comando copiado!', color='positive'))).props('unelevated color=amber-9 text-color=black bold').classes('text-xs')
                                                ui.button('Fechar', on_click=dlg_info.close).props('flat color=grey').classes('text-xs')
                                        dlg_info.open()

                                    if sys.platform == 'win32' and not os.environ.get('RENDER_EXTERNAL_URL'):
                                        if not is_running:
                                            def iniciar_watcher_direto():
                                                caminho_pasta = pasta_input.value.strip()
                                                if not os.path.exists(caminho_pasta):
                                                    try: os.makedirs(caminho_pasta, exist_ok=True)
                                                    except Exception: pass
                                                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'event_photo_watcher.py')
                                                cmd = [sys.executable, script_path, '--event-id', slug, '--pasta', caminho_pasta]
                                                try:
                                                    p = subprocess.Popen(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
                                                    _ACTIVE_WATCHERS[slug] = p
                                                    ui.notify('🚀 Processamento iniciado no PC local!', color='positive')
                                                    render_watcher_panel()
                                                except Exception as ex_proc:
                                                    ui.notify(f'Erro: {ex_proc}', color='negative')

                                            ui.button('▶️ INICIAR PROCESSAMENTO (PC LOCAL)', icon='play_arrow', on_click=iniciar_watcher_direto).props('unelevated color=green-8 text-color=white bold').classes('flex-1 h-13 text-sm font-black rounded-xl cyber-glow')
                                        else:
                                            def parar_watcher_direto():
                                                p = _ACTIVE_WATCHERS.get(slug)
                                                if p:
                                                    try:
                                                        p.terminate()
                                                        _ACTIVE_WATCHERS[slug] = None
                                                        ui.notify('⏹️ Processamento encerrado.', color='info')
                                                    except Exception: pass
                                                render_watcher_panel()

                                            ui.button('⏹️ PARAR PROCESSAMENTO', icon='stop', on_click=parar_watcher_direto).props('unelevated color=red-8 text-color=white bold').classes('flex-1 h-13 text-sm font-black rounded-xl')
                                    else:
                                        ui.button('🚀 COMO EXECUTAR NO SEU PC (GPU)', icon='terminal', on_click=abrir_info_execucao_local).props('unelevated color=amber-9 text-color=black bold').classes('flex-1 h-13 text-sm font-black rounded-xl cyber-glow')

                                    def copiar_cmd_watcher():
                                        cmd = f'python event_photo_watcher.py --event-id "{slug}" --pasta "{pasta_input.value}"'
                                        escaped = cmd.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                                        ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                                        ui.notify('📋 Comando do Watcher copiado! Cole no PowerShell do seu PC.', color='positive', icon='content_copy')

                                    ui.button('📋 Copiar Comando Watcher', icon='content_copy', on_click=copiar_cmd_watcher).props('unelevated color=cyan-8 text-color=white bold').classes('h-13 px-4 rounded-xl text-xs')
                                    ui.button(icon='refresh', on_click=render_watcher_panel).props('unelevated color=slate-8 text-color=cyan round').classes('h-13 w-13').tooltip('Atualizar contadores e logs')

                            # 3. LOG EM TEMPO REAL DAS ÚLTIMAS FOTOS PROCESSADAS
                            with ui.card().classes('w-full bg-slate-950 border border-cyan-500/20 rounded-2xl p-4 gap-2 q-mt-1'):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('list_alt', size='1.3rem', color='cyan-4')
                                        ui.label('LOG AO VIVO DE FOTOS PROCESSADAS COM IA').classes('text-xs font-bold text-cyan-3')
                                    ui.badge(f'{emb_count} rostos no total', color='amber-9').classes('text-[10px]')

                                recent_logs = get_event_photo_embeddings(slug)
                                if not recent_logs:
                                    ui.label('Aguardando envio e processamento de fotos da pasta local...').classes('text-xs text-grey-5 italic py-2')
                                else:
                                    # Mostra até as 8 últimas fotos únicas
                                    seen_photos = set()
                                    unique_recents = []
                                    for r in reversed(recent_logs):
                                        fid = r.get('drive_file_id')
                                        if fid not in seen_photos:
                                            seen_photos.add(fid)
                                            unique_recents.append(r)
                                        if len(unique_recents) >= 8:
                                            break

                                    with ui.column().classes('w-full gap-1 font-mono text-[11px] max-h-48 overflow-y-auto'):
                                        for item in unique_recents:
                                            fname = item.get('photo_filename') or f"foto_{item.get('drive_file_id')[:8]}.jpg"
                                            dt_raw = item.get('criado_em', '')[:19].replace('T', ' ')
                                            with ui.row().classes('w-full items-center justify-between p-1.5 bg-black/40 rounded border border-white/5'):
                                                with ui.row().classes('items-center gap-2 truncate'):
                                                    ui.label('🟢').classes('text-[8px]')
                                                    ui.label(fname).classes('text-white font-bold truncate max-w-xs')
                                                with ui.row().classes('items-center gap-3'):
                                                    ui.label(f'👤 {item.get("det_score", 0.95):.0%} conf.').classes('text-amber-3 text-[10px]')
                                                    ui.label(dt_raw).classes('text-grey-5 text-[10px]')

                    render_watcher_panel()

                # ── ETAPA 3: CURADORIA GERAL ──
                with ui.tab_panel(t_cur).classes('w-full p-2 gap-4'):
                    with ui.card().classes('w-full bg-slate-950/80 border border-slate-800 rounded-2xl p-6 text-center items-center gap-3'):
                        ui.icon('photo_library', size='3.5rem', color='cyan-4')
                        ui.label('Subpasta GERAL no Google Drive').classes('text-base font-bold text-white')
                        ui.label('As fotos colocadas dentro da subpasta GERAL serão exibidas para TODOS os convidados que acessarem o link oficial do evento.').classes('text-xs text-grey-3 max-w-lg leading-relaxed')
                        
                        if geral_fid:
                            ui.button('📂 ABRIR PASTA GERAL NO GOOGLE DRIVE', icon='open_in_new', on_click=lambda: ui.open(f'https://drive.google.com/drive/folders/{geral_fid}', new_tab=True)).props('unelevated color=cyan text-color=black bold').classes('h-12 px-6 rounded-xl q-mt-sm')
                        else:
                            ui.label('Subpasta GERAL não encontrada. Crie a estrutura oficial primeiro na opção "Vincular/Criar Pasta".').classes('text-xs text-amber-4')

                # ── ETAPA 4: CONVIDADOS & ENTREGAS ──
                with ui.tab_panel(t_guest).classes('w-full p-2 gap-4'):
                    metrics = get_portal_analytics_summary(slug)
                    profiles = get_guest_profiles_for_event(slug)

                    with ui.grid().classes('w-full grid-cols-3 gap-3'):
                        with ui.card().classes('p-3 bg-slate-950 text-center rounded-2xl border border-slate-800'):
                            ui.label(str(metrics.get('acessos', 0))).classes('text-2xl font-black text-cyan-4')
                            ui.label('Total de Acessos').classes('text-xs text-grey-4')
                        with ui.card().classes('p-3 bg-slate-950 text-center rounded-2xl border border-slate-800'):
                            ui.label(str(len(profiles))).classes('text-2xl font-black text-amber-4')
                            ui.label('Convidados com Selfie').classes('text-xs text-grey-4')
                        with ui.card().classes('p-3 bg-slate-950 text-center rounded-2xl border border-slate-800'):
                            ui.label(str(metrics.get('emails', 0))).classes('text-2xl font-black text-green-4')
                            ui.label('E-mails Entregues').classes('text-xs text-grey-4')

                # ── ETAPA 5: QR CODE & DIVULGAÇÃO ──
                with ui.tab_panel(t_qr).classes('w-full p-2 gap-4 items-center text-center'):
                    with ui.column().classes('w-full items-center gap-3 py-2'):
                        ui.image(qr_b64).classes('w-52 h-52 rounded-2xl border-2 border-amber-500/40 p-2 bg-white shadow-2xl')
                        ui.label(portal_url).classes('text-xs font-mono text-cyan-3 font-bold bg-black/60 px-3 py-1.5 rounded-lg border border-white/10')

                        with ui.row().classes('w-full justify-center gap-3 flex-wrap q-mt-2'):
                            def copiar_link_portal():
                                escaped = portal_url.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                                ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                                ui.notify('📋 Link do Portal copiado para a área de transferência!', color='positive', icon='content_copy')

                            ui.button('📋 Copiar Link do Portal', icon='content_copy', on_click=copiar_link_portal).props('unelevated color=cyan-8 text-color=white bold').classes('h-11 px-4 rounded-xl text-xs')
                            ui.button('🌐 Testar / Abrir Portal', icon='open_in_new', on_click=lambda: ui.open(portal_url, new_tab=True)).props('unelevated color=amber-9 text-color=black bold').classes('h-11 px-4 rounded-xl text-xs')

        dlg_portal.open()
