import os
import inspect
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection, get_service_db_connection
import drive_service

THEME = theme.colors

# Caminho da galeria local nos assets estáticos do NiceGUI
GALERIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'galeria_hot')
os.makedirs(GALERIA_DIR, exist_ok=True)

def render_page(evento_id: str = None, **kwargs):
    user_data = app.storage.user.get('user_data', {})
    
    with ui.row().classes('w-full justify-between items-center q-mb-md q-ml-md q-pr-md'):
        ui.label('🔥 GALERIA DE FOTOS').classes('text-2xl font-bold text-white cyber-title gt-xs')
        
        def abrir_cadastrar_biometria():
            with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-sm w-full').style(f'background: {THEME["bg_panel"]};'):
                ui.label('👤 Cadastrar Biometria Facial').classes('text-lg font-bold text-cyan q-mb-md')
                ui.label('Envie uma selfie clara do seu rosto.').classes('text-xs text-grey-4 q-mb-sm')
                
                async def handle_upload(e):
                    file_bytes = e.content.read()
                    try:
                        import sisgab_face_worker
                        is_valid, msg, embedding = sisgab_face_worker.evaluate_selfie_quality(file_bytes)
                        if not is_valid:
                            ui.notify(f'❌ {msg}', color='negative')
                            return
                            
                        db = get_db_connection()
                        if db:
                            db.table('face_embeddings').insert({
                                'user_id': user_data.get('id'),
                                'nome_guerra': user_data.get('nome_guerra', ''),
                                'telegram_id': user_data.get('telegram_id', ''),
                                'embedding': embedding
                            }).execute()
                            ui.notify('✅ Biometria facial cadastrada com sucesso!', color='positive')
                            dlg.close()
                    except Exception as ex:
                        ui.notify(f'Erro ao processar biometria: {ex}', color='negative')

                ui.upload(on_upload=handle_upload, auto_upload=True).props('accept="image/*" w-full')
                ui.button('Cancelar', on_click=dlg.close).props('flat w-full color=grey q-mt-sm')
            dlg.open()
            
        ui.button('👤 Cadastrar Biometria Facial', on_click=abrir_cadastrar_biometria).props('outline color=cyan').classes('font-bold')

    db = get_db_connection()
    worker_status = 'offline'
    queue_count = 0
    if db:
        try:
            hb_res = db.table('config').select('value').eq('key', 'face_worker_heartbeat').execute()
            if hb_res.data:
                try:
                    last_hb_str = hb_res.data[0]['value'].replace('Z', '+00:00')
                    last_hb = datetime.fromisoformat(last_hb_str)
                    import datetime as dt
                    now = dt.datetime.now(dt.timezone.utc) if last_hb.tzinfo else datetime.now()
                    if (now - last_hb).total_seconds() < 60:
                        worker_status = 'online'
                except Exception:
                    pass
            
            qc_res = db.table('config').select('value').eq('key', 'face_worker_queue_count').execute()
            if qc_res.data:
                queue_count = int(qc_res.data[0]['value'])
            
            if worker_status == 'offline':
                pend_res = db.table('processed_photos').select('id', count='exact').in_('status', ['pendente', 'PENDENTE_AI']).execute()
                queue_count = pend_res.count or 0
        except Exception as e:
            print(f"[WORKER STATUS ERR] {e}")

    with ui.row().classes('w-full q-ml-md q-mb-md items-center'):
        if worker_status == 'online':
            ui.badge('🟢 Worker GPU Online (PXSTUDIO)', color='positive').classes('text-sm font-bold q-pa-sm')
        else:
            ui.badge(f'🟡 Worker GPU Offline ({queue_count} fotos na fila de espera)', color='warning').classes('text-sm font-bold text-black q-pa-sm q-mr-sm')
            ui.button('⚡ Processar no Servidor', on_click=lambda: ui.notify('Processamento CPU iniciado (fallback).', color='info')).props('dense rounded color=blue').classes('text-xs font-bold')

    
    user_data = app.storage.user.get('user_data', {})
    user_id = user_data.get('id')
    user_role = str(user_data.get('role', '')).strip().lower()
    is_operator = user_role in ['admin', 'supervisor', 'operador']
    
    pautas_options = {}
    pautas_data = {}
    db = get_db_connection()
    if db:
        try:
            res_p = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'concluida']).order('data_evento', desc=True).execute()
            if res_p.data:
                for p in res_p.data:
                    ev_id = str(p['id'])
                    pautas_options[ev_id] = f"📸 {p.get('data_evento', '')} - {p.get('titulo_evento', '')}"
                    pautas_data[ev_id] = p
        except Exception as e:
            print(f"[DB GALERIA PAUTAS ERR] {e}")

    if not pautas_options:
        pautas_options['geral'] = 'Geral / Sem Pauta'
        
    evento_selecionado = str(evento_id) if evento_id and str(evento_id) in pautas_options else list(pautas_options.keys())[0]
    
    page_state = {
        'pauta_id': evento_selecionado,
        'curation_mode': False,
        'selected_files': set()
    }

    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
        with ui.row().classes('w-full justify-between items-center q-mb-xs'):
            ui.label('Selecione o Evento').classes('text-xs font-bold text-cyan')
            if is_operator:
                ui.button('📲 Distribuir Acervo', on_click=lambda: abrir_dialog_distribuir()).props('dense rounded flat color=emerald').classes('text-xs font-bold bg-cyan-9 text-white px-3')
        
        def on_event_change(e):
            page_state['pauta_id'] = e.value
            render_drive_tabs.refresh()
            
        ui.select(
            pautas_options,
            value=page_state['pauta_id'],
            on_change=on_event_change
        ).props('dark outlined dense w-full option-dark')

    def abrir_dialog_distribuir():
        pauta_id = page_state.get('pauta_id')
        demanda = pautas_data.get(str(pauta_id))
        if not demanda:
            ui.notify('Selecione um evento válido', color='warning')
            return
            
        destinatarios = {}
        db = get_db_connection()
        if db:
            try:
                res_ef = db.table('efetivo').select('nome_guerra, posto_grad, telegram_id').not_('telegram_id', 'is', 'null').execute()
                if res_ef.data:
                    for ef in res_ef.data:
                        tg_id = ef.get('telegram_id')
                        if tg_id:
                            destinatarios[str(tg_id)] = f"{ef.get('posto_grad', '')} {ef.get('nome_guerra', '')} (ID: {tg_id})"
            except Exception as e:
                print(f"[DB] Erro buscando destinatários: {e}")
                
        destinatarios['manual'] = 'Inserir ID Manualmente...'
        
        dialog_state = {'dest_id': list(destinatarios.keys())[0] if destinatarios else None, 'manual_id': ''}
        
        with ui.dialog() as dlg, ui.card().classes('q-pa-md max-w-sm w-full').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
            ui.label('Distribuir Acervo no Telegram').classes('text-lg font-bold text-cyan q-mb-md')
            
            sel = ui.select(destinatarios, label='Destinatário', value=dialog_state['dest_id']).props('dark outlined dense w-full option-dark q-mb-sm')
            man_input = ui.input('ID Telegram (Manual)').props('dark outlined dense w-full q-mb-md').bind_visibility_from(sel, 'value', value=lambda v: v == 'manual')
            
            def get_target_chat_id():
                return man_input.value if sel.value == 'manual' else sel.value
                
            async def do_distribuir(acao):
                chat_id = get_target_chat_id()
                if not chat_id:
                    ui.notify('Selecione um destinatário válido.', color='warning')
                    return
                
                import telegram_bot
                from telegram_bot.utils import enviar_links_acervo, enviar_album_hd_drive
                import drive_service
                
                bot_inst = telegram_bot.bot
                
                if not bot_inst:
                    ui.notify('Bot não inicializado.', color='negative')
                    return
                
                dlg.close()
                ui.notify('Iniciando distribuição... aguarde.', color='info')
                
                try:
                    if acao in ['links', 'ambos']:
                        res = await enviar_links_acervo(bot_inst, chat_id, demanda)
                        if res:
                            ui.notify(f'✅ Links enviados para {chat_id}!', color='success')
                        else:
                            ui.notify('❌ Erro ao enviar links.', color='negative')
                            
                    if acao in ['album', 'ambos']:
                        drive_folder_id = demanda.get('drive_folder_id')
                        if not drive_folder_id and demanda.get('drive_url'):
                            url = demanda.get('drive_url')
                            if 'folders/' in url:
                                drive_folder_id = url.split('folders/')[-1].split('?')[0]
                                
                        if not drive_folder_id:
                            ui.notify('❌ ID da pasta principal não encontrado.', color='negative')
                            return
                            
                        selecao_id = drive_service.find_folder('SELEÇÃO', drive_folder_id)
                        if not selecao_id:
                            ui.notify('❌ Pasta SELEÇÃO não encontrada no Drive.', color='negative')
                            return
                            
                        count = await enviar_album_hd_drive(bot_inst, chat_id, selecao_id)
                        if count:
                            ui.notify(f'✅ Álbum HD de {count} fotos enviado para {chat_id}!', color='success')
                        else:
                            ui.notify('❌ Erro ou sem fotos para enviar Álbum HD.', color='negative')
                except Exception as e:
                    ui.notify(f'Erro na distribuição: {e}', color='negative')

            with ui.column().classes('w-full gap-2 mt-2'):
                ui.button('🔗 Enviar Links no Telegram', on_click=lambda: do_distribuir('links')).props('unelevated w-full color=primary text-color=black bold')
                ui.button('📸 Enviar Álbum HD (SELEÇÃO)', on_click=lambda: do_distribuir('album')).props('unelevated w-full color=secondary text-color=black bold')
                ui.button('📲 Enviar Ambos (Links + Álbum)', on_click=lambda: do_distribuir('ambos')).props('unelevated w-full color=accent text-color=white bold')
                ui.button('Cancelar', on_click=dlg.close).props('flat w-full color=grey')
                
        dlg.open()

    def open_preview_modal(file_info):
        with ui.dialog() as modal, ui.card().classes('q-pa-md max-w-4xl max-h-[90vh] overflow-hidden').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
            with ui.row().classes('w-full justify-between items-center q-mb-sm'):
                ui.label(file_info.get('name', 'Preview')).classes('text-sm font-bold text-cyan truncate max-w-[70%]')
                ui.button(icon='close', on_click=modal.close).props('flat round dense text-color=white')
            
            img_url = file_info.get('webViewLink') or file_info.get('thumbnailLink')
            if img_url:
                thumb = file_info.get('thumbnailLink', '')
                large_img = thumb.replace('=s220', '=s1000') if thumb else img_url
                ui.image(large_img).style('max-height: 65vh; object-fit: contain;')
            
            created = file_info.get('createdTime', '')[:10]
            ui.label(f"Upload: {created}").classes('text-[10px] text-grey-5 q-mt-sm')
            
            with ui.row().classes('w-full justify-end q-mt-md'):
                if file_info.get('webViewLink'):
                    ui.button('🔗 Abrir no Drive', on_click=lambda: ui.open(file_info['webViewLink'], new_tab=True)).props('unelevated color=primary text-color=black bold')
        modal.open()

    def open_lightbox_local(image_path):
        with ui.dialog() as lightbox, ui.card().classes('q-pa-none max-w-4xl max-h-[85vh] overflow-hidden').style('background: transparent;'):
            ui.image(image_path).style('max-height: 80vh; object-fit: contain;')
        lightbox.open()

    @ui.refreshable
    def render_gallery_grid_local(pauta_id):
        pauta_subfolder = os.path.join(GALERIA_DIR, str(pauta_id))
        os.makedirs(pauta_subfolder, exist_ok=True)
        files = []
        if os.path.exists(pauta_subfolder):
            files = [f for f in os.listdir(pauta_subfolder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
        if files:
            with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));'):
                for f in files:
                    file_web_path = f"/assets/galeria_hot/{pauta_id}/{f}"
                    with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden hover:scale-105 transition-all cursor-pointer').style(
                        'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'
                    ).on('click', lambda _, path=file_web_path: open_lightbox_local(path)):
                        ui.image(file_web_path).style('height: 150px; object-fit: cover;')
                        with ui.row().classes('w-full q-pa-sm justify-between items-center bg-black/40'):
                            ui.label(f[:15] + "..." if len(f) > 15 else f).classes('text-[10px] text-grey-3')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('photo_library', size='3rem')
                ui.label('Nenhuma foto enviada para esta pauta ainda.').classes('text-xs')

    def render_photo_grid(fotos, is_selecao):
        if fotos:
            with ui.grid().classes('w-full gap-4 q-mt-md').style('grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));'):
                for f in fotos:
                    fid = f.get('id')
                    is_selected = fid in page_state['selected_files']
                    if page_state['curation_mode'] and is_selected:
                        border_style = 'border: 2px solid rgba(255, 193, 7, 1);'
                    elif is_selecao:
                        border_style = 'border: 1px solid rgba(255, 193, 7, 0.8);'
                    else:
                        border_style = 'border: 1px solid rgba(0, 229, 255, 0.15);'

                    with ui.card().classes('w-[180px] cursor-pointer hover:scale-105 transition-all relative q-pa-none').style(
                        f'background: #091326; {border_style} border-radius: 12px; overflow: hidden;'
                    ):
                        if page_state['curation_mode']:
                            def toggle_sel(e, file_id=fid):
                                if file_id in page_state['selected_files']:
                                    page_state['selected_files'].remove(file_id)
                                else:
                                    page_state['selected_files'].add(file_id)
                                render_drive_tabs.refresh()
                            ui.checkbox('', value=is_selected, on_change=toggle_sel).classes('absolute top-1 left-1 z-10').props('dark color=amber')
                            img = ui.image(f.get('thumbnailLink', '')).classes('w-full h-[130px] object-cover')
                            img.on('click', toggle_sel)
                        else:
                            img = ui.image(f.get('thumbnailLink', '')).classes('w-full h-[130px] object-cover')
                            img.on('click', lambda _, file_info=f: open_preview_modal(file_info))
                        
                        with ui.column().classes('q-pa-xs gap-0 w-full'):
                            ui.label(f.get('name', '')[:25]).classes('text-[10px] text-grey-3 truncate')
        else:
            ui.label('Nenhuma foto encontrada nesta pasta.').classes('text-grey-5 q-pa-md')

    @ui.refreshable
    def render_drive_tabs():
        pauta_id = page_state.get('pauta_id')
        pauta = pautas_data.get(str(pauta_id), {})
        
        drive_svc = drive_service.get_drive_service()
        drive_folder_id = pauta.get('drive_folder_id')
        
        if not drive_folder_id:
            db_conn = get_db_connection()
            if db_conn and pauta.get('titulo_evento'):
                res = db_conn.table('processed_photos').select('drive_link').eq('event_name', pauta['titulo_evento']).eq('filename', 'drive_folder_link').execute()
                if res.data and res.data[0].get('drive_link'):
                    url = res.data[0]['drive_link']
                    if 'folders/' in url:
                        drive_folder_id = url.split('folders/')[-1].split('?')[0]

        if not (drive_svc and drive_folder_id):
            ui.label('⚠️ Integração com Google Drive não configurada ou pasta não vinculada. Exibindo galeria local.').classes('text-warning text-xs q-mb-md q-pa-md bg-black/50 rounded')
            render_gallery_grid_local(pauta_id)
            return

        selecao_folder_id = drive_service.find_folder('SELEÇÃO', drive_folder_id)
        fotos_todas = drive_service.list_files(drive_folder_id, mime_filter='image/')
        fotos_selecao = drive_service.list_files(selecao_folder_id, mime_filter='image/') if selecao_folder_id else []

        with ui.row().classes('w-full justify-between items-center q-my-sm bg-black/30 q-pa-sm rounded-lg border border-white/10'):
            ui.label(f"📸 {len(fotos_todas)} fotos na pasta | ⭐ {len(fotos_selecao)} na SELEÇÃO").classes('text-sm font-bold text-amber-5')
            if is_operator:
                def toggle_curation():
                    page_state['curation_mode'] = not page_state['curation_mode']
                    page_state['selected_files'].clear()
                    render_drive_tabs.refresh()
                btn_color = 'amber' if page_state['curation_mode'] else 'grey-8'
                ui.button('✏️ Modo Curadoria', on_click=toggle_curation).props(f'unelevated color={btn_color} text-color=black bold').classes('text-xs')

        if page_state['curation_mode']:
            with ui.row().classes('w-full justify-between items-center q-pa-sm bg-amber-9/20 rounded-lg border border-amber-500/50 q-mb-md'):
                with ui.row().classes('gap-2'):
                    def select_all():
                        for f in fotos_todas:
                            page_state['selected_files'].add(f.get('id'))
                        for f in fotos_selecao:
                            page_state['selected_files'].add(f.get('id'))
                        render_drive_tabs.refresh()
                    def deselect_all():
                        page_state['selected_files'].clear()
                        render_drive_tabs.refresh()
                    ui.button('☑️ Selecionar Todas', on_click=select_all).props('outline color=amber dense').classes('text-xs')
                    ui.button('☐ Desmarcar Todas', on_click=deselect_all).props('outline color=grey dense').classes('text-xs')
                
                with ui.row().classes('gap-2'):
                    async def mover_para_selecao():
                        if not page_state['selected_files']: return
                        if not selecao_folder_id:
                            ui.notify('Pasta SELEÇÃO não encontrada.', color='negative')
                            return
                        n = len(page_state['selected_files'])
                        notif = ui.notification(f"Movendo {n} arquivos para SELEÇÃO...", timeout=0, spinner=True)
                        
                        db = get_db_connection()
                        wm_enabled = False
                        wm_text = 'COMSOC / CGCFN'
                        if db:
                            res1 = db.table('config').select('value').eq('key', 'drive_watermark_enabled').execute()
                            if res1.data and res1.data[0].get('value') == 'True':
                                wm_enabled = True
                            res2 = db.table('config').select('value').eq('key', 'drive_watermark_text').execute()
                            if res2.data:
                                wm_text = res2.data[0].get('value', wm_text)
                                
                        for fid in list(page_state['selected_files']):
                            if wm_enabled:
                                import asyncio
                                await asyncio.to_thread(drive_service.copy_and_watermark_to_selecao, fid, selecao_folder_id, wm_text)
                            else:
                                drive_service.move_file(fid, selecao_folder_id)
                        notif.dismiss()
                        ui.notify(f'{n} arquivos movidos para SELEÇÃO!', color='success')
                        page_state['selected_files'].clear()
                        render_drive_tabs.refresh()
                        
                    async def devolver_selecao():
                        if not page_state['selected_files']: return
                        n = len(page_state['selected_files'])
                        notif = ui.notification(f"Devolvendo {n} arquivos para pasta principal...", timeout=0, spinner=True)
                        for fid in list(page_state['selected_files']):
                            drive_service.move_file(fid, drive_folder_id)
                        notif.dismiss()
                        ui.notify(f'{n} arquivos devolvidos!', color='success')
                        page_state['selected_files'].clear()
                        render_drive_tabs.refresh()
                        
                    n_sel = len(page_state['selected_files'])
                    ui.button(f'⭐ Mover para SELEÇÃO ({n_sel})', on_click=mover_para_selecao).props('unelevated color=amber text-color=black bold').classes('text-xs')
                    ui.button(f'↩️ Devolver ({n_sel})', on_click=devolver_selecao).props('unelevated color=grey text-color=white bold').classes('text-xs')

        with ui.tabs().classes('w-full text-cyan flex-wrap') as drive_tabs:
            tab_t = ui.tab('📸 Todas as Fotos')
            tab_s = ui.tab('⭐ Seleção (Melhores)')
            
        with ui.tab_panels(drive_tabs, value=tab_t).classes('w-full bg-transparent p-0'):
            with ui.tab_panel(tab_t):
                render_photo_grid(fotos_todas, False)
            with ui.tab_panel(tab_s):
                render_photo_grid(fotos_selecao, True)

    @ui.refreshable
    def render_moderation_grid():
        db = get_db_connection()
        pending_matches = []
        if db:
            try:
                res_m = db.table('photo_matches').select('*').eq('status', 'pendente').execute()
                if res_m.data:
                    for m in res_m.data:
                        res_p = db.table('processed_photos').select('*').eq('id', m['photo_id']).execute()
                        res_u = db.table('Users').select('nome_guerra, telegram_id').eq('id', m['militar_id']).execute()
                        if res_p.data and res_u.data:
                            pending_matches.append({
                                'match_id': m['id'],
                                'similarity': m['similarity'],
                                'bbox': m.get('bbox'),
                                'photo': res_p.data[0],
                                'user': res_u.data[0]
                            })
            except Exception as ex:
                print(f"[MODERATION DB ERR] {ex}")

        if pending_matches:
            with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(3, 1fr);'):
                for item in pending_matches:
                    match_id = item['match_id']
                    p = item['photo']
                    u = item['user']
                    sim_pct = item['similarity'] * 100
                    file_web_path = f"/assets/galeria_hot/{p['event_name']}/{p['filename']}"
                    
                    with ui.card().classes('q-pa-none no-shadow rounded-xl overflow-hidden').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ):
                        try:
                            import sisgab_face_worker
                            import base64
                            local_img_path = os.path.join(GALERIA_DIR, p['event_name'], p['filename'])
                            bbox = item.get('bbox')
                            if bbox and os.path.exists(local_img_path):
                                with open(local_img_path, 'rb') as img_f:
                                    img_bytes = img_f.read()
                                drawn_bytes = sisgab_face_worker.draw_face_bounding_box(img_bytes, bbox)
                                b64_img = base64.b64encode(drawn_bytes).decode('utf-8')
                                img_src = f"data:image/jpeg;base64,{b64_img}"
                            else:
                                img_src = file_web_path
                        except Exception:
                            img_src = file_web_path

                        ui.image(img_src).style('height: 160px; object-fit: cover;')
                        with ui.column().classes('q-pa-md w-full gap-1'):
                            ui.label(f"👮 {u['nome_guerra']}").classes('text-md font-bold text-white')
                            ui.label(f"⚓ Pauta: {p['event_name']}").classes('text-xs text-grey-4')
                            ui.label(f"📈 Similaridade: {sim_pct:.1f}%").classes('text-xs text-cyan font-bold')
                            
                            with ui.row().classes('w-full justify-between q-mt-md'):
                                async def aprovar(m_id=match_id, tg_id=u['telegram_id'], link=p['drive_link'], ev=p['event_name'], fn=p['filename'], name=u['nome_guerra']):
                                    try:
                                        conn = get_db_connection()
                                        if conn:
                                            conn.table('photo_matches').update({'status': 'aprovado'}).eq('id', m_id).execute()
                                            if tg_id:
                                                import telegram_bot
                                                bot_inst = telegram_bot.bot
                                                if bot_inst:
                                                    caption = (
                                                        f"📸 *UMA NOVA FOTO SUA ACABOU DE SER REGISTRADA!* 🎉\n\n"
                                                        f"⚓ *Evento:* {ev}\n"
                                                        f"👤 *Militar:* {name}\n"
                                                        f"🔗 [Acesse no Google Drive]({link})\n\n"
                                                        f"Espero que goste!"
                                                    )
                                                    local_thumb = os.path.join(GALERIA_DIR, ev, fn)
                                                    if os.path.exists(local_thumb):
                                                        with open(local_thumb, 'rb') as pf:
                                                            await bot_inst.send_photo(chat_id=tg_id, photo=pf, caption=caption, parse_mode='Markdown')
                                                    else:
                                                        await bot_inst.send_message(chat_id=tg_id, text=caption, parse_mode='Markdown')
                                        ui.notify('Foto aprovada e enviada ao militar!', color='success')
                                        render_moderation_grid.refresh()
                                    except Exception as err:
                                        ui.notify(f'Erro ao aprovar: {err}', color='red')

                                async def rejeitar(m_id=match_id):
                                    try:
                                        conn = get_db_connection()
                                        if conn:
                                            conn.table('photo_matches').update({'status': 'rejeitado'}).eq('id', m_id).execute()
                                        ui.notify('Foto rejeitada.', color='warning')
                                        render_moderation_grid.refresh()
                                    except Exception as err:
                                        ui.notify(f'Erro ao rejeitar: {err}', color='red')
                                        
                                ui.button('❌ Rejeitar Match', on_click=rejeitar).props('flat dense color=red').classes('text-xs')
                                ui.button('✅ Aprovar Match', on_click=aprovar).props('flat dense color=green').classes('text-xs font-bold')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('fact_check', size='3rem')
                ui.label('Nenhuma foto aguardando moderação facial no momento.').classes('text-xs')

    @ui.refreshable
    def render_pessoal_grid():
        if not user_id:
            ui.label('Faça login para visualizar sua galeria pessoal.').classes('text-xs text-grey-4')
            return
            
        db = get_db_connection()
        pessoal_photos = []
        if db:
            try:
                res_m = db.table('photo_matches').select('photo_id, similarity').eq('militar_id', user_id).eq('status', 'aprovado').execute()
                if res_m.data:
                    for m in res_m.data:
                        res_p = db.table('processed_photos').select('*').eq('id', m['photo_id']).execute()
                        if res_p.data:
                            pessoal_photos.append({
                                'photo': res_p.data[0],
                                'similarity': m['similarity']
                            })
            except Exception as ex:
                print(f"[PESSOAL DB ERR] {ex}")
                
        if pessoal_photos:
            ui.badge(f"📸 Você apareceu em {len(pessoal_photos)} fotos nos eventos!", color='primary').classes('q-mb-md text-bold')
            with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(4, 1fr);'):
                for item in pessoal_photos:
                    p = item['photo']
                    sim_pct = item['similarity'] * 100
                    file_web_path = f"/assets/galeria_hot/{p['event_name']}/{p['filename']}"
                    
                    with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden hover:scale-105 transition-all').style(
                        'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'
                    ):
                        ui.image(file_web_path).style('height: 150px; object-fit: cover;')
                        with ui.column().classes('q-pa-sm w-full gap-1'):
                            ui.label(p['event_name']).classes('text-xs font-bold text-white')
                            date_str = p.get('created_at', '')[:10] if p.get('created_at') else ''
                            if date_str:
                                ui.label(f"📅 {date_str}").classes('text-[10px] text-grey-4')
                            ui.label(f"📈 {sim_pct:.0f}% de certeza").classes('text-[10px] text-cyan')
                            with ui.row().classes('w-full justify-between mt-2 gap-1'):
                                ui.button('⬇️ Baixar', on_click=lambda l=p.get('drive_link', file_web_path): ui.download(l)).props('flat dense color=white').classes('text-[10px] font-bold flex-1')
                                ui.button('🔗 Abrir no Drive', on_click=lambda link=p.get('drive_link'): ui.open(link, new_tab=True) if link else ui.notify('Link não disponível', color='warning')).props('flat dense color=cyan').classes('text-[10px] font-bold flex-1')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('face', size='3rem')
                ui.label('Você ainda não foi identificado em nenhuma foto. Cadastre sua selfie no Telegram!').classes('text-xs')

    # Main Tabs
    with ui.tabs().classes('w-full text-cyan flex-wrap') as main_tabs:
        tab_galeria = ui.tab('📸 Eventos & Galeria')
        if is_operator:
            tab_mod = ui.tab('🔍 Moderação')
        tab_pes = ui.tab('👤 Minhas Fotos')
        
    with ui.tab_panels(main_tabs, value=tab_galeria).classes('w-full bg-transparent no-shadow q-pa-none q-mt-md'):
        with ui.tab_panel(tab_galeria):
            render_drive_tabs()
            
        if is_operator:
            with ui.tab_panel(tab_mod):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                    ui.label('👥 Fotos em Moderação (Fuzzy Matches)').classes('text-md font-bold text-cyan q-mb-md')
                    render_moderation_grid()
                    
        with ui.tab_panel(tab_pes):
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                ui.label('🖼️ Minha Galeria Pessoal (Identificação por IA)').classes('text-md font-bold text-cyan q-mb-md')
                render_pessoal_grid()

