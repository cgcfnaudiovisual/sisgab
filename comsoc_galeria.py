import os
import inspect
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

# Caminho da galeria local nos assets estáticos do NiceGUI
GALERIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'galeria_hot')
os.makedirs(GALERIA_DIR, exist_ok=True)

def render_page():
    ui.label('🔥 ENTREGA EM HOT (GALERIA & IA)').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_id = user_data.get('id')
    user_role = str(user_data.get('role', '')).strip().lower()
    is_operator = user_role in ['admin', 'supervisor', 'operador']
    
    # Estado da pauta selecionada
    page_state = {
        'pauta_id': 'geral'
    }

    # --------------------------------------------------------------------------
    # COMPONENTE: GRID GALERIA GERAL
    # --------------------------------------------------------------------------
    @ui.refreshable
    def render_gallery_grid():
        pauta_subfolder = os.path.join(GALERIA_DIR, str(page_state['pauta_id']))
        os.makedirs(pauta_subfolder, exist_ok=True)
        
        # Lista imagens
        files = []
        if os.path.exists(pauta_subfolder):
            files = [f for f in os.listdir(pauta_subfolder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
        if files:
            with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(4, 1fr);'):
                for f in files:
                    file_web_path = f"/assets/galeria_hot/{page_state['pauta_id']}/{f}"
                    
                    with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden hover:scale-105 transition-all cursor-pointer').style(
                        'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'
                    ):
                        # Imagem de visualização
                        ui.image(file_web_path).style('height: 150px; object-fit: cover;')
                        
                        # Nome do arquivo
                        with ui.row().classes('w-full q-pa-sm justify-between items-center bg-black/40'):
                            ui.label(f[:15] + "..." if len(f) > 15 else f).classes('text-[10px] text-grey-3')
                            ui.button(
                                icon='visibility', 
                                on_click=lambda path=file_web_path: open_lightbox(path)
                            ).props('flat round color=cyan dense').style('font-size: 0.8rem;')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('photo_library', size='3rem')
                ui.label('Nenhuma foto enviada para esta pauta ainda.').classes('text-xs')

    def open_lightbox(image_path):
        with ui.dialog() as lightbox, ui.card().classes('q-pa-none max-w-4xl max-h-[85vh] overflow-hidden').style('background: transparent;'):
            ui.image(image_path).style('max-height: 80vh; object-fit: contain;')
        lightbox.open()

    # --------------------------------------------------------------------------
    # COMPONENTE: GRID FILA DE MODERAÇÃO
    # --------------------------------------------------------------------------
    @ui.refreshable
    def render_moderation_grid():
        db = get_db_connection()
        pending_matches = []
        if db:
            try:
                res_m = db.table('photo_matches').select('*').eq('status', 'pendente').execute()
                if res_m.data:
                    for m in res_m.data:
                        # Busca detalhes da foto
                        res_p = db.table('processed_photos').select('*').eq('id', m['photo_id']).execute()
                        # Busca nome do militar
                        res_u = db.table('Users').select('nome_guerra, telegram_id').eq('id', m['militar_id']).execute()
                        
                        if res_p.data and res_u.data:
                            pending_matches.append({
                                'match_id': m['id'],
                                'similarity': m['similarity'],
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
                        ui.image(file_web_path).style('height: 160px; object-fit: cover;')
                        
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
                                            
                                            # Envia Telegram se configurado
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
                                        
                                ui.button('Rejeitar', on_click=rejeitar).props('flat dense color=red').classes('text-xs')
                                ui.button('Aprovar', on_click=aprovar).props('flat dense color=green').classes('text-xs font-bold')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('fact_check', size='3rem')
                ui.label('Nenhuma foto aguardando moderação facial no momento.').classes('text-xs')

    # --------------------------------------------------------------------------
    # COMPONENTE: GRID GALERIA PESSOAL ("MINHAS FOTOS")
    # --------------------------------------------------------------------------
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
                            ui.label(f"📈 Similaridade: {sim_pct:.1f}%").classes('text-[10px] text-cyan')
                            
                            ui.button(
                                'Abrir no Google Drive', 
                                icon='open_in_new', 
                                on_click=lambda link=p['drive_link']: ui.open(link, new_tab=True)
                            ).props('flat w-full dense color=cyan').classes('text-[10px] font-bold')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('face', size='3rem')
                ui.label('Você ainda não foi identificado em nenhuma foto. Cadastre sua selfie no Telegram!').classes('text-xs')

    # --------------------------------------------------------------------------
    # RENDERIZADOR PRINCIPAL DE ABAS
    # --------------------------------------------------------------------------
    with ui.tabs().classes('w-full text-cyan flex-wrap') as tabs:
        tab_geral = ui.tab('📸 Geral & Upload')
        if is_operator:
            tab_mod = ui.tab('👥 Fila de Moderação')
        tab_pes = ui.tab('🖼️ Minhas Fotos')
        
    with ui.tab_panels(tabs, value=tab_geral).classes('w-full bg-transparent no-shadow q-pa-none q-mt-md'):
        with ui.tab_panel(tab_geral):
            # Carregar pautas para o dropdown
            pautas_options = {'geral': 'Geral / Sem Pauta'}
            db = get_db_connection()
            if db:
                try:
                    res_p = db.table('demandas_comunicacao').select('id, titulo_evento, data_evento').eq('status', 'aprovada').execute()
                    if res_p.data:
                        for p in res_p.data:
                            pautas_options[str(p['id'])] = f"{p['titulo_evento']} ({p['data_evento']})"
                except Exception as e:
                    print(f"[DB GALERIA PAUTAS ERR] {e}")

            with ui.row().classes('w-full gap-4 items-stretch'):
                # Form de Upload
                with ui.column().classes('col-12 col-md-4 gap-4'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ):
                        ui.label('📸 Upload em Campo').classes('text-md font-bold text-cyan q-mb-xs')
                        
                        def on_pauta_change(e):
                            page_state['pauta_id'] = str(e.value)
                            render_gallery_grid.refresh()

                        ui.select(
                            pautas_options,
                            value='geral',
                            label='Selecionar Evento / Pauta',
                            on_change=on_pauta_change
                        ).props('dark outlined dense w-full option-dark')

                        async def handle_upload(e):
                            try:
                                file_bytes = e.content.read()
                                if inspect.isawaitable(file_bytes):
                                    file_bytes = await file_bytes
                                    
                                filename = e.name
                                pauta_subfolder = os.path.join(GALERIA_DIR, str(page_state['pauta_id']))
                                os.makedirs(pauta_subfolder, exist_ok=True)
                                
                                dest_path = os.path.join(pauta_subfolder, filename)
                                with open(dest_path, 'wb') as f:
                                    f.write(file_bytes)
                                    
                                ui.notify(f'Foto {filename} enviada!', color='success')
                                render_gallery_grid.refresh()

                                # Despacho Telegram (Entrega em Hot)
                                try:
                                    from notifications_manager import notify_telegram_photo
                                    pauta_nome = pautas_options.get(str(page_state['pauta_id']), 'Geral / Sem Pauta')
                                    op_nome = user_data.get('nome_guerra', 'Operador')
                                    caption_msg = (
                                        f"📸 *ENTREGA EM HOT*\n"
                                        f"Nova foto enviada em tempo real!\n\n"
                                        f"⚓ *Evento:* {pauta_nome}\n"
                                        f"📂 *Arquivo:* `{filename}`\n"
                                        f"👤 *Operador:* {op_nome}"
                                    )
                                    notify_telegram_photo(file_bytes, caption_msg, "aviso")
                                except Exception as tg_err:
                                    print(f"[TG HOT UPLOAD ERR] {tg_err}")
                            except Exception as ex:
                                ui.notify(f'Erro no upload: {ex}', color='red')

                        # Upload restrito a apenas JPG e JPEG
                        ui.upload(
                            label='Selecionar Fotos (.jpg, .jpeg)',
                            on_upload=handle_upload,
                            multiple=True,
                            auto_upload=True
                        ).props('accept=".jpg,.jpeg" flat color=cyan w-full text-color=white').classes('q-mt-md text-xs')

                # Painel da Galeria
                with ui.column().classes('col-12 col-md-7 gap-4'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ):
                        ui.label('🖼️ Pré-visualização Rápida').classes('text-md font-bold text-cyan q-mb-md')
                        render_gallery_grid()

        if is_operator:
            with ui.tab_panel(tab_mod):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                ):
                    ui.label('👥 Fotos em Moderação (Fuzzy Matches)').classes('text-md font-bold text-cyan q-mb-md')
                    render_moderation_grid()

        with ui.tab_panel(tab_pes):
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
            ):
                ui.label('🖼️ Minha Galeria Pessoal (Identificação por IA)').classes('text-md font-bold text-cyan q-mb-md')
                render_pessoal_grid()
