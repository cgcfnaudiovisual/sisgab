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
                ui.button('🌐 Portal do Convidado', icon='qr_code_2', on_click=lambda: _abrir_portal_convidado()).props('dense unelevated color=amber-9 text-color=white font-bold').classes('text-xs cyber-glow')
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
                            raw_dt = str(ev.get('data_evento') or '').strip()
                            data_ev = raw_dt[:10] if raw_dt and raw_dt.upper() != 'ASD' else 'ASD'
                            titulo = ev.get('titulo_evento', 'Sem titulo')
                            from database import get_demanda_drive_url
                            dfid = get_drive_folder_id(ev)
                            drive_url = get_demanda_drive_url(ev)
                            n_local = len(get_local_photos(eid))
                            is_sel = str(eid) == str(page_state['pauta_id'])
                            row_bg = 'background: rgba(0,229,255,0.08);' if is_sel else ''

                            with ui.element('tr').style(
                                f'border-bottom: 1px solid rgba(255,255,255,0.04); cursor: pointer; {row_bg}'
                            ).classes('hover:bg-white/5').on('click', lambda _, _id=eid: _on_event_change(_id)):
                                with ui.element('td').classes('q-pa-xs text-grey-3'):
                                    if data_ev == 'ASD':
                                        ui.badge('ASD', color='amber').classes('text-[10px] text-black font-bold').tooltip('Data a Definir (ASD)')
                                    else:
                                        ui.label(data_ev).classes('text-[10px]')
                                with ui.element('td').classes('q-pa-xs'):
                                    ui.label(titulo[:45] + ('...' if len(titulo) > 45 else '')).classes(
                                        'text-[11px] text-white font-bold' if is_sel else 'text-[11px] text-grey-2'
                                    )
                                with ui.element('td').classes('q-pa-xs text-center'):
                                    if n_local > 0:
                                        ui.badge(str(n_local), color='cyan').classes('text-[9px]')
                                    elif dfid or drive_url:
                                        ui.badge('Nuvem', color='blue-grey').classes('text-[8px]')
                                    else:
                                        ui.label('-').classes('text-[10px] text-grey-6')
                                with ui.element('td').classes('q-pa-xs text-center'):
                                    if dfid or drive_url:
                                        ui.icon('cloud_done', size='14px', color='green')
                                    else:
                                        ui.icon('cloud_off', size='14px', color='grey')
                                with ui.element('td').classes('q-pa-xs'):
                                    with ui.row().classes('gap-1 items-center'):
                                        if drive_url or dfid:
                                            target_link = drive_url or f"https://drive.google.com/drive/folders/{dfid}"
                                            ui.button(icon='open_in_new', on_click=lambda _, u=target_link: ui.open(u, new_tab=True)).props(
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

    def _abrir_distribuir(pauta):
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

        with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-xl w-full rounded-2xl').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; shadow: 0 0 30px rgba(0,229,255,0.2);'
        ):
            # Cabeçalho com Resumo do Evento
            with ui.row().classes('w-full justify-between items-center q-mb-sm border-b border-cyan-500/20 pb-2'):
                with ui.column().classes('gap-0'):
                    ui.label('🚀 Distribuir Acervo & Links').classes('text-base font-bold text-cyan')
                    ui.label(f"{titulo} ({data_ev})").classes('text-xs text-grey-4 truncate max-w-[380px]')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense text-color=white')

            # Abas de Envio
            with ui.tabs().classes('w-full text-cyan') as tabs:
                tab_envio = ui.tab('envio', label='📲 Telegram', icon='send')
                tab_zap = ui.tab('whatsapp', label='📋 Copiar Texto (Zap/Texto)', icon='content_copy')

            with ui.tab_panels(tabs, value=tab_envio).classes('w-full bg-transparent p-0 q-mt-sm'):
                
                # ─── PAINEL TELEGRAM ───
                with ui.tab_panel(tab_envio).classes('w-full p-0 gap-3'):
                    mode_select = ui.select(
                        {
                            'nominal': '👤 Militar Específico do Efetivo',
                            'todos': f'👥 Todos os Militares Cadastrados ({len(todos_tids)})',
                            'manual': '💬 Digitar ID / Chat ID Manual'
                        },
                        value='nominal',
                        label='Destinatário'
                    ).props('dark outlined dense w-full option-dark').classes('q-mb-xs')

                    mil_select = ui.select(
                        militares_opts if militares_opts else {'none': 'Nenhum militar com Telegram registrado'},
                        value=list(militares_opts.keys())[0] if militares_opts else 'none',
                        label='Selecione o Militar'
                    ).props('dark outlined dense w-full option-dark').bind_visibility_from(
                        mode_select, 'value', value=lambda v: v == 'nominal'
                    )

                    manual_input = ui.input('ID Telegram (ex: 123456789)').props(
                        'dark outlined dense w-full'
                    ).bind_visibility_from(mode_select, 'value', value=lambda v: v == 'manual')

                    # Opções do conteúdo
                    with ui.row().classes('w-full items-center justify-between p-2 bg-slate-900/60 rounded-lg border border-white/5 q-my-xs'):
                        chk_links = ui.checkbox('🔗 Links do Drive', value=True).props('dark color=cyan dense')
                        chk_album = ui.checkbox('⭐ Álbum HD (Seleção)', value=True).props('dark color=amber dense')

                    async def disparar_telegram():
                        mode = mode_select.value
                        target_ids = []
                        if mode == 'nominal':
                            if mil_select.value and mil_select.value != 'none':
                                target_ids.append(mil_select.value)
                        elif mode == 'todos':
                            target_ids = todos_tids
                        elif mode == 'manual':
                            v = (manual_input.value or '').strip()
                            if v: target_ids.append(v)

                        if not target_ids:
                            ui.notify('Selecione ou digite ao menos um destinatário.', color='warning')
                            return

                        import telegram_bot
                        from telegram_bot.utils import enviar_links_acervo, enviar_album_hd_drive
                        bot = telegram_bot.bot
                        if not bot:
                            ui.notify('Bot do Telegram não inicializado.', color='negative')
                            return

                        dlg.close()
                        notif = ui.notification(f"🚀 Enviando acervo para {len(target_ids)} destinatário(s)...", timeout=0, spinner=True)
                        sucessos = 0
                        try:
                            for cid in target_ids:
                                if chk_links.value:
                                    await enviar_links_acervo(bot, cid, pauta)
                                if chk_album.value and fid:
                                    sf = drive_service.find_folder('SELEÇÃO', fid) or fid
                                    await enviar_album_hd_drive(bot, cid, sf)
                                sucessos += 1
                            notif.dismiss()
                            ui.notify(f'✅ Acervo enviado com sucesso para {sucessos} destinatário(s)!', color='positive')
                        except Exception as ex_send:
                            notif.dismiss()
                            ui.notify(f'Erro ao enviar: {ex_send}', color='negative')

                    ui.button('🚀 Disparar Distribuição', icon='send', on_click=disparar_telegram).props(
                        'unelevated color=cyan text-color=black bold w-full'
                    ).classes('q-mt-sm')

                # ─── PAINEL WHATSAPP / MENSAGEM PADRÃO ───
                with ui.tab_panel(tab_zap).classes('w-full p-0 gap-3'):
                    ui.label('Mensagem Padrão Pronta para Copiar:').classes('text-xs text-grey-4')
                    txt_area = ui.textarea(value=texto_padrao).props('dark outlined dense w-full rows=6').classes('w-full font-mono text-xs')

                    def copiar_texto():
                        val = txt_area.value
                        escaped = val.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                        ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                        ui.notify('📋 Texto copiado para a área de transferência!', color='positive', icon='content_copy')

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

        portal_url = f"https://sisgab.com/evento/{slug}"

        # Gera QR Code
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

        with ui.dialog() as dlg_portal, ui.card().classes('q-pa-md max-w-3xl w-full rounded-2xl bg-slate-900 border border-cyan-500/30 text-white').style('box-shadow: 0 0 40px rgba(0,229,255,0.15);'):
            # Header
            with ui.row().classes('w-full justify-between items-center border-b border-cyan-500/20 pb-2'):
                with ui.column().classes('gap-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('qr_code_2', size='1.5rem', color='amber-4')
                        ui.label('🌐 GESTÃO DO PORTAL DO CONVIDADO').classes('text-base font-black text-amber-4 tracking-wide')
                    ui.label(f"{titulo} ({data_ev})").classes('text-xs text-grey-4 truncate max-w-[450px]')
                ui.button(icon='close', on_click=dlg_portal.close).props('flat round dense text-color=white')

            # Abas das 5 Etapas
            with ui.tabs().classes('w-full text-cyan') as tabs_p:
                t_cfg = ui.tab('cfg', label='⚙️ 1. Configuração', icon='settings')
                t_proc = ui.tab('proc', label='⬆️ 2. Upload & IA', icon='memory')
                t_cur = ui.tab('cur', label='📷 3. Curadoria GERAL', icon='collections')
                t_guest = ui.tab('guest', label='👥 4. Convidados', icon='people')
                t_qr = ui.tab('qr', label='📱 5. QR Code & Divulgação', icon='qr_code')

            with ui.tab_panels(tabs_p, value=t_cfg).classes('w-full bg-transparent p-0 q-mt-sm'):
                
                # ── ETAPA 1: CONFIGURAÇÃO ──
                with ui.tab_panel(t_cfg).classes('w-full p-2 gap-4'):
                    with ui.column().classes('w-full gap-3'):
                        status_val = ev_pub.get('status', 'ativo')
                        sw_status = ui.switch('Status do Portal (Ativo / Inativo)', value=(status_val == 'ativo')).props('dark color=green')
                        
                        threshold_slider = ui.slider(min=0.35, max=0.70, step=0.01, value=float(ev_pub.get('threshold_match') or 0.45)).props('dark label-always color=amber')
                        ui.label(f'Threshold de Similaridade Facial: {threshold_slider.value:.2f} (padrão: 0.45)').classes('text-xs text-grey-4')

                        wm_check = ui.checkbox('Habilitar Marca d\'Água Institucional nas Fotos', value=bool(ev_pub.get('watermark_enabled', True))).props('dark color=cyan dense')
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

                        ui.button('💾 Salvar Configurações', icon='save', on_click=salvar_configuracoes).props('unelevated color=cyan text-color=black bold w-full').classes('q-mt-sm')

                # ── ETAPA 2: UPLOAD & PROCESSAMENTO ──
                with ui.tab_panel(t_proc).classes('w-full p-2 gap-4'):
                    with ui.card().classes('w-full bg-slate-950/80 border border-cyan-500/20 p-4 rounded-xl gap-2'):
                        ui.label('📊 Status do Acervo & Embeddings IA').classes('text-sm font-bold text-cyan')
                        emb_count = count_event_embeddings(slug)
                        ws = check_worker_status()
                        
                        with ui.row().classes('w-full justify-between items-center text-xs py-1'):
                            ui.label('Motor de IA Local (GPU):')
                            ui.badge('Online' if ws == 'online' else 'Offline', color='positive' if ws == 'online' else 'warning')
                        with ui.row().classes('w-full justify-between items-center text-xs py-1'):
                            ui.label('Rostos Mapeados no Evento:')
                            ui.badge(f"{emb_count} embeddings", color='amber-9').classes('font-bold')

                    with ui.column().classes('w-full gap-2 q-mt-2'):
                        ui.label('🚀 Comando para Watcher Local (10 Workers):').classes('text-xs font-bold text-amber-4')
                        pasta_input = ui.input('Caminho da Pasta Local das Fotos', value=f"D:\\FOTOS\\{slug}").props('dark outlined dense w-full')
                        
                        def copiar_cmd_watcher():
                            cmd = f'python event_photo_watcher.py --event-id "{slug}" --pasta "{pasta_input.value}"'
                            escaped = cmd.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                            ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                            ui.notify('📋 Comando copiado! Cole no terminal do PC com GPU.', color='positive', icon='content_copy')

                        ui.button('📋 Copiar Comando Watcher', icon='terminal', on_click=copiar_cmd_watcher).props('unelevated color=amber text-color=black bold w-full')

                # ── ETAPA 3: CURADORIA GERAL ──
                with ui.tab_panel(t_cur).classes('w-full p-2 gap-4'):
                    with ui.column().classes('w-full gap-2 text-center items-center'):
                        ui.icon('photo_library', size='3rem', color='cyan-4')
                        ui.label('Subpasta GERAL no Google Drive').classes('text-sm font-bold text-white')
                        ui.label('As fotos colocadas dentro da subpasta GERAL serão exibidas para TODOS os convidados que acessarem o link.').classes('text-xs text-grey-4 max-w-md')
                        
                        if geral_fid:
                            ui.button('📂 Abrir Pasta GERAL no Drive', icon='open_in_new', on_click=lambda: ui.open(f'https://drive.google.com/drive/folders/{geral_fid}', new_tab=True)).props('unelevated color=cyan text-color=black bold').classes('q-mt-sm')
                        else:
                            ui.label('Pasta GERAL não encontrada. Crie a estrutura de pastas do evento primeiro.').classes('text-xs text-amber-4')

                # ── ETAPA 4: CONVIDADOS & ENTREGAS ──
                with ui.tab_panel(t_guest).classes('w-full p-2 gap-4'):
                    metrics = get_portal_analytics_summary(slug)
                    profiles = get_guest_profiles_for_event(slug)

                    with ui.grid().classes('w-full grid-cols-3 gap-2'):
                        with ui.card().classes('p-2 bg-slate-950 text-center rounded-lg border border-slate-800'):
                            ui.label(str(metrics.get('acessos', 0))).classes('text-lg font-black text-cyan-4')
                            ui.label('Acessos').classes('text-[10px] text-grey-4')
                        with ui.card().classes('p-2 bg-slate-950 text-center rounded-lg border border-slate-800'):
                            ui.label(str(len(profiles))).classes('text-lg font-black text-amber-4')
                            ui.label('Convidados').classes('text-[10px] text-grey-4')
                        with ui.card().classes('p-2 bg-slate-950 text-center rounded-lg border border-slate-800'):
                            ui.label(str(metrics.get('emails', 0))).classes('text-lg font-black text-green-4')
                            ui.label('E-mails').classes('text-[10px] text-grey-4')

                # ── ETAPA 5: QR CODE & DIVULGAÇÃO ──
                with ui.tab_panel(t_qr).classes('w-full p-2 gap-4 items-center text-center'):
                    with ui.column().classes('w-full items-center gap-3'):
                        ui.image(qr_b64).classes('w-44 h-44 rounded-xl border-2 border-amber-500/40 p-1 bg-white')
                        ui.label(portal_url).classes('text-xs font-mono text-cyan-3 font-bold')

                        with ui.row().classes('w-full justify-center gap-2 flex-wrap'):
                            def copiar_link_portal():
                                escaped = portal_url.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
                                ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                                ui.notify('📋 Link do Portal copiado!', color='positive', icon='content_copy')

                            ui.button('📋 Copiar Link', icon='content_copy', on_click=copiar_link_portal).props('dense outline color=cyan').classes('text-xs')
                            ui.button('🌐 Testar / Abrir Portal', icon='open_in_new', on_click=lambda: ui.open(portal_url, new_tab=True)).props('dense unelevated color=amber-9 text-color=white bold').classes('text-xs')

        dlg_portal.open()
