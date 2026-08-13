"""
comsoc_galeria.py - Galeria de Fotos & Acervo Digital
Visualizacao de fotos locais e do Google Drive, upload direto,
busca inteligente por IA, curadoria e distribuicao via Telegram.
"""
import os
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

    # ─── BARRA DE ACOES ───
    with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl q-mb-sm').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full items-center gap-2 flex-wrap'):
            def _open_drive():
                p = pautas_data.get(str(page_state['pauta_id']), {})
                fid = get_drive_folder_id(p)
                if fid:
                    ui.open(f'https://drive.google.com/drive/folders/{fid}', new_tab=True)
                else:
                    ui.notify('Pasta nao vinculada.', color='warning')
            ui.button('Abrir Drive', icon='folder_open', on_click=_open_drive).props('dense outline color=cyan').classes('text-xs')
            if is_operator:
                ui.button('Distribuir', icon='send', on_click=lambda: _abrir_distribuir()).props('dense outline color=green').classes('text-xs')
                ui.button('Vincular/Criar Pasta', icon='link', on_click=lambda: _abrir_vincular()).props('dense outline color=amber').classes('text-xs')
            ui.button('Biometria Facial', icon='face', on_click=lambda: _abrir_biometria()).props('dense outline color=purple').classes('text-xs')

    # ─── MURAL DE EVENTOS RECENTES ───
    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-sm').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full justify-between items-center q-mb-sm'):
            ui.label('Mural de Eventos & Acervo').classes('text-sm font-bold text-cyan')
            ui.badge(f'{len(pautas_data)} eventos', color='primary').classes('text-xs')

        if pautas_data:
            with ui.element('div').classes('w-full overflow-auto').style('max-height: 280px;'):
                with ui.element('table').classes('w-full').style(
                    'border-collapse: collapse; font-size: 11px;'
                ):
                    # Header
                    with ui.element('thead'):
                        with ui.element('tr').style('border-bottom: 1px solid rgba(197,160,89,0.2);'):
                            for h in ['Data', 'Evento', 'Fotos', 'Drive', 'Acoes']:
                                with ui.element('th').classes('text-left text-grey-4 font-bold q-pa-xs'):
                                    ui.label(h)
                    # Body
                    with ui.element('tbody'):
                        for eid, ev in list(pautas_data.items())[:20]:
                            data_ev = ev.get('data_evento', '')[:10]
                            titulo = ev.get('titulo_evento', 'Sem titulo')
                            dfid = get_drive_folder_id(ev)
                            n_local = len(get_local_photos(eid))
                            drive_url = ev.get('drive_url', '')
                            is_sel = str(eid) == str(page_state['pauta_id'])
                            row_bg = 'background: rgba(0,229,255,0.08);' if is_sel else ''

                            with ui.element('tr').style(
                                f'border-bottom: 1px solid rgba(255,255,255,0.04); cursor: pointer; {row_bg}'
                            ).classes('hover:bg-white/5').on('click', lambda _, _id=eid: _on_event_change(_id)):
                                with ui.element('td').classes('q-pa-xs text-grey-3'):
                                    ui.label(data_ev).classes('text-[10px]')
                                with ui.element('td').classes('q-pa-xs'):
                                    ui.label(titulo[:45] + ('...' if len(titulo) > 45 else '')).classes(
                                        'text-[11px] text-white font-bold' if is_sel else 'text-[11px] text-grey-2'
                                    )
                                with ui.element('td').classes('q-pa-xs text-center'):
                                    if n_local > 0:
                                        ui.badge(str(n_local), color='cyan').classes('text-[9px]')
                                    else:
                                        ui.label('-').classes('text-[10px] text-grey-6')
                                with ui.element('td').classes('q-pa-xs text-center'):
                                    if dfid:
                                        ui.icon('cloud_done', size='14px', color='green')
                                    else:
                                        ui.icon('cloud_off', size='14px', color='grey')
                                with ui.element('td').classes('q-pa-xs'):
                                    with ui.row().classes('gap-1 items-center'):
                                        if drive_url:
                                            ui.button(icon='open_in_new', on_click=lambda _, u=drive_url: ui.open(u, new_tab=True)).props(
                                                'flat dense round size=xs color=cyan'
                                            ).tooltip('Abrir pasta no Drive')
                                        ui.button(icon='photo_library', on_click=lambda _, _id=eid: _on_event_change(_id)).props(
                                            'flat dense round size=xs color=amber'
                                        ).tooltip('Ver galeria')
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
                        await asyncio.wait_for(
                            asyncio.to_thread(drive_service.upload_file, content, fname, fid), timeout=15.0
                        )
                        ui.notify(f'{fname} enviada ao Drive!', color='info')
                    except Exception as ex:
                        print(f"[GALERIA] [WARN] Upload Drive falhou: {ex}")
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
                drive_photos = drive_service.list_files(dfid, mime_filter='image/') or []
                selecao_fid = drive_service.find_folder('SELEÇÃO', dfid)
                if selecao_fid:
                    drive_selecao = drive_service.list_files(selecao_fid, mime_filter='image/') or []
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
        with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-sm w-full').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
            ui.label('Cadastrar Biometria Facial').classes('text-lg font-bold text-cyan q-mb-md')
            ui.label('Envie uma selfie clara do seu rosto.').classes('text-xs text-grey-4 q-mb-sm')
            async def handle_selfie(e):
                fb = e.content.read()
                try:
                    import sisgab_face_worker
                    ok, msg, emb = sisgab_face_worker.evaluate_selfie_quality(fb)
                    if not ok:
                        ui.notify(msg, color='negative'); return
                    c = get_db_connection()
                    if c:
                        c.table('face_embeddings').insert({'user_id': user_data.get('id'), 'nome_guerra': user_data.get('nome_guerra', ''), 'telegram_id': user_data.get('telegram_id', ''), 'embedding': emb}).execute()
                        ui.notify('Biometria cadastrada!', color='positive'); dlg.close()
                except Exception as ex:
                    ui.notify(f'Erro: {ex}', color='negative')
            ui.upload(on_upload=handle_selfie, auto_upload=True).props('accept="image/*" w-full')
            ui.button('Cancelar', on_click=dlg.close).props('flat w-full color=grey q-mt-sm')
        dlg.open()

    def _abrir_vincular():
        pauta = pautas_data.get(str(page_state['pauta_id']), {})
        with ui.dialog() as dlg, ui.card().classes('w-96 q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
            ui.label('Vincular Pasta do Drive').classes('text-white text-sm font-bold q-mb-xs')
            in_url = ui.input('Link do Google Drive', placeholder='https://drive.google.com/drive/folders/...').props('dark outlined dense w-full')
            def salvar():
                v = in_url.value.strip()
                if not v: return
                fid = v.split('folders/')[-1].split('?')[0].split('/')[0] if 'folders/' in v else v
                pauta['drive_folder_id'] = fid; pauta['drive_url'] = v
                from database import salvar_demanda_drive_link
                salvar_demanda_drive_link(pauta.get('id'), pauta.get('titulo_evento'), v, fid)
                ui.notify('Link vinculado!', color='success'); dlg.close(); render_main_content.refresh()
            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                ui.button('Cancelar', on_click=dlg.close).props('flat color=grey')
                ui.button('Salvar', on_click=salvar).props('unelevated color=cyan bold')
        dlg.open()

    async def _criar_pasta():
        pauta = pautas_data.get(str(page_state['pauta_id']), {})
        n = ui.notify('Criando pasta no Drive...', color='info', spinner=True, timeout=0)
        try:
            drive_service.reset_drive_service()
            res = await asyncio.wait_for(asyncio.to_thread(drive_service.criar_pasta_evento, pauta.get('titulo_evento', ''), pauta.get('data_evento', '')), timeout=15.0)
            if res and res.get('evento_link'):
                pauta['drive_folder_id'] = res['evento_folder_id']; pauta['drive_url'] = res['evento_link']
                from database import salvar_demanda_drive_link
                salvar_demanda_drive_link(pauta.get('id'), pauta.get('titulo_evento'), res['evento_link'], res['evento_folder_id'])
                ui.notify('Pasta criada!', color='success'); render_main_content.refresh()
            else:
                ui.notify('Falha ao criar pasta. Verifique credenciais.', color='warning')
        except Exception as ex:
            ui.notify(f'Erro: {ex}', color='negative')
        finally:
            try: n.dismiss()
            except Exception: pass

    def _abrir_distribuir():
        pauta = pautas_data.get(str(page_state['pauta_id']), {})
        if not pauta.get('id'):
            ui.notify('Selecione um evento.', color='warning'); return
        dests = {}
        c = get_db_connection()
        if c:
            try:
                r = c.table('efetivo').select('nome_guerra, posto_grad, telegram_id').not_('telegram_id', 'is', 'null').execute()
                if r.data:
                    for ef in r.data:
                        tg = ef.get('telegram_id')
                        if tg: dests[str(tg)] = f"{ef.get('posto_grad', '')} {ef.get('nome_guerra', '')} (ID: {tg})"
            except Exception: pass
        dests['manual'] = 'Inserir ID Manualmente...'
        with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-sm w-full').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
            ui.label('Distribuir Acervo').classes('text-lg font-bold text-cyan q-mb-md')
            sel = ui.select(dests, label='Destinatario', value=list(dests.keys())[0]).props('dark outlined dense w-full option-dark q-mb-sm')
            man = ui.input('ID Telegram').props('dark outlined dense w-full q-mb-md').bind_visibility_from(sel, 'value', value=lambda v: v == 'manual')
            async def do_d(acao):
                cid = man.value if sel.value == 'manual' else sel.value
                if not cid: ui.notify('Selecione destinatario.', color='warning'); return
                import telegram_bot; from telegram_bot.utils import enviar_links_acervo, enviar_album_hd_drive
                bot = telegram_bot.bot
                if not bot: ui.notify('Bot nao inicializado.', color='negative'); return
                dlg.close(); ui.notify('Iniciando...', color='info')
                try:
                    if acao in ['links', 'ambos']: await enviar_links_acervo(bot, cid, pauta); ui.notify('Links enviados!', color='success')
                    if acao in ['album', 'ambos']:
                        fid = get_drive_folder_id(pauta)
                        if fid:
                            sf = drive_service.find_folder('SELEÇÃO', fid)
                            if sf: cnt = await enviar_album_hd_drive(bot, cid, sf); ui.notify(f'Album {cnt} fotos!', color='success')
                except Exception as e: ui.notify(f'Erro: {e}', color='negative')
            with ui.column().classes('w-full gap-2 mt-2'):
                ui.button('Enviar Links', icon='link', on_click=lambda: do_d('links')).props('unelevated w-full color=primary text-color=black bold')
                ui.button('Enviar Album HD', icon='photo_album', on_click=lambda: do_d('album')).props('unelevated w-full color=secondary text-color=black bold')
                ui.button('Enviar Ambos', icon='send', on_click=lambda: do_d('ambos')).props('unelevated w-full color=accent text-color=white bold')
                ui.button('Cancelar', on_click=dlg.close).props('flat w-full color=grey')
        dlg.open()
