"""
comsoc_galeria_components.py - Componentes reutilizaveis da Galeria
Grid de fotos, preview, moderacao, galeria pessoal e busca inteligente.
"""
import os
import asyncio
from datetime import datetime
from difflib import SequenceMatcher
from nicegui import ui, app
from database import get_db_connection
import drive_service

GALERIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'galeria_hot')

# ─── Busca Inteligente (Hibrida: Fuzzy + IA) ─────────────────────────

def fuzzy_search(query: str, options: dict) -> list:
    """Busca fuzzy local por titulo de evento. Retorna lista de (id, score, label)."""
    query_up = query.strip().upper()
    results = []
    for eid, label in options.items():
        label_up = label.upper()
        if query_up in label_up:
            results.append((eid, 0.95, label))
            continue
        words = query_up.split()
        word_hits = sum(1 for w in words if w in label_up)
        if word_hits > 0:
            results.append((eid, word_hits / max(len(words), 1) * 0.8, label))
            continue
        ratio = SequenceMatcher(None, query_up, label_up).ratio()
        if ratio > 0.35:
            results.append((eid, ratio, label))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:10]


async def ai_search(query: str, options: dict) -> list:
    """Busca semantica usando Gemini para interpretar a intencao do usuario."""
    try:
        import google.generativeai as genai
        from ai_helper import _get_google_api_key, _get_gemini_model_name
        api_key = _get_google_api_key()
        if not api_key:
            return []
        genai.configure(api_key=api_key)
        events_list = "\n".join([f"ID:{eid} | {label}" for eid, label in list(options.items())[:50]])
        prompt = (
            f"O usuario busca um evento com o texto: \"{query}\"\n\n"
            f"Lista de eventos disponiveis:\n{events_list}\n\n"
            f"Retorne APENAS os IDs dos eventos que correspondem a busca, "
            f"separados por virgula, do mais relevante ao menos. "
            f"Se nenhum corresponder, retorne 'NENHUM'. "
            f"Responda SOMENTE com os IDs, nada mais."
        )
        model = genai.GenerativeModel(
            _get_gemini_model_name(),
            system_instruction="Voce e um assistente de busca. Retorne apenas IDs numericos separados por virgula."
        )
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text.strip()
        )
        if not response or 'NENHUM' in response.upper():
            return []
        ids = [x.strip() for x in response.replace('ID:', '').split(',') if x.strip()]
        results = []
        for i, eid in enumerate(ids):
            if eid in options:
                results.append((eid, 0.9 - i * 0.05, options[eid]))
        return results
    except Exception as e:
        print(f"[GALERIA] [WARN] Busca IA falhou: {e}")
        return []


# ─── Helpers ──────────────────────────────────────────────────────────

def get_local_photos(pauta_id):
    """Lista fotos locais de um evento."""
    folder = os.path.join(GALERIA_DIR, str(pauta_id))
    if not os.path.exists(folder):
        return []
    return [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]


def get_drive_folder_id(pauta: dict) -> str:
    """Extrai drive_folder_id de uma demanda com fallbacks."""
    fid = pauta.get('drive_folder_id')
    if fid:
        return fid
    url = pauta.get('drive_url', '') or ''
    if 'folders/' in url:
        return url.split('folders/')[-1].split('?')[0].split('/')[0]
    db = get_db_connection()
    if db and pauta.get('titulo_evento'):
        try:
            res = db.table('processed_photos').select('drive_link').eq(
                'event_name', pauta['titulo_evento']
            ).eq('filename', 'drive_folder_link').execute()
            if res.data and res.data[0].get('drive_link'):
                u = res.data[0]['drive_link']
                if 'folders/' in u:
                    return u.split('folders/')[-1].split('?')[0].split('/')[0]
        except Exception:
            pass
    return None


def check_worker_status():
    """Verifica se o worker GPU esta online."""
    db = get_db_connection()
    if db:
        try:
            hb = db.table('config').select('value').eq('key', 'face_worker_heartbeat').execute()
            if hb.data:
                import datetime as dt
                last = datetime.fromisoformat(hb.data[0]['value'].replace('Z', '+00:00'))
                now = dt.datetime.now(dt.timezone.utc)
                if (now - last).total_seconds() < 60:
                    return 'online'
        except Exception:
            pass
    return 'offline'


def empty_state(icon_name, text):
    """Renderiza estado vazio padronizado."""
    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
        ui.icon(icon_name, size='3rem')
        ui.label(text).classes('text-xs text-center')


# ─── Grids de Fotos ──────────────────────────────────────────────────

def render_drive_grid(fotos, page_state, is_operator, selecao_fid, theme, is_selecao=False):
    """Renderiza grid de fotos do Drive."""
    if is_operator and not is_selecao:
        with ui.row().classes('w-full items-center gap-2 q-mb-sm'):
            def toggle_cur():
                page_state['curation_mode'] = not page_state['curation_mode']
                page_state['selected_files'].clear()
            btn_c = 'amber' if page_state.get('curation_mode') else 'grey-8'
            ui.button('Modo Curadoria', icon='edit', on_click=toggle_cur).props(
                f'dense unelevated color={btn_c} text-color=black'
            ).classes('text-xs')
            if page_state.get('curation_mode'):
                n_sel = len(page_state['selected_files'])
                ui.button(f'Mover para SELECAO ({n_sel})', icon='star',
                          on_click=lambda: _mover_selecao(page_state, selecao_fid)).props(
                    'dense unelevated color=amber text-color=black'
                ).classes('text-xs')

    with ui.element('div').classes('w-full gap-3').style(
        'display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));'
    ):
        for f in fotos:
            fid = f.get('id')
            thumb = f.get('thumbnailLink', '')
            is_selected = fid in page_state.get('selected_files', set())
            border = 'border: 2px solid #ffc107;' if is_selected else (
                'border: 1px solid rgba(255,193,7,0.8);' if is_selecao else f'border: 1px solid {theme["border"]};'
            )
            with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden cursor-pointer hover-scale').style(
                f'background: {theme["bg_editor"]}; {border}'
            ):
                if page_state.get('curation_mode') and not is_selecao:
                    def toggle(e, file_id=fid):
                        if file_id in page_state['selected_files']:
                            page_state['selected_files'].remove(file_id)
                        else:
                            page_state['selected_files'].add(file_id)
                    ui.checkbox('', value=is_selected, on_change=toggle).classes(
                        'absolute top-1 left-1 z-10'
                    ).props('dark color=amber')

                img = ui.image(thumb).classes('w-full').style('height: 150px; object-fit: cover;')
                if not page_state.get('curation_mode'):
                    img.on('click', lambda _, fi=f: preview_drive_photo(fi, theme))

                with ui.row().classes('w-full q-pa-xs items-center bg-black/50'):
                    ui.label(f.get('name', '')[:20]).classes('text-[9px] text-grey-3 truncate flex-grow')
                    badge_txt = 'Selecao' if is_selecao else 'Drive'
                    badge_col = 'amber' if is_selecao else 'blue-grey'
                    ui.badge(badge_txt, color=badge_col).classes('text-[8px]')


def preview_drive_photo(file_info, theme):
    """Modal de preview de foto do Drive."""
    with ui.dialog() as modal, ui.card().classes('q-pa-md max-w-4xl max-h-[90vh] overflow-hidden').style(
        f'background: {theme["bg_panel"]}; border: 1px solid {theme["border"]};'
    ):
        with ui.row().classes('w-full justify-between items-center q-mb-sm'):
            ui.label(file_info.get('name', 'Preview')).classes('text-sm font-bold text-cyan truncate max-w-[70%]')
            ui.button(icon='close', on_click=modal.close).props('flat round dense text-color=white')
        thumb = file_info.get('thumbnailLink', '')
        large_img = thumb.replace('=s220', '=s1000') if thumb else file_info.get('webViewLink', '')
        if large_img:
            ui.image(large_img).style('max-height: 65vh; object-fit: contain;')
        created = file_info.get('createdTime', '')[:10]
        ui.label(f"Upload: {created}").classes('text-[10px] text-grey-5 q-mt-sm')
        with ui.row().classes('w-full justify-end q-mt-md'):
            if file_info.get('webViewLink'):
                ui.button('Abrir no Drive', icon='open_in_new',
                          on_click=lambda: ui.open(file_info['webViewLink'], new_tab=True)).props(
                    'unelevated color=primary text-color=black bold'
                )
    modal.open()


async def _mover_selecao(page_state, selecao_fid):
    """Move fotos selecionadas para pasta SELECAO."""
    if not page_state['selected_files'] or not selecao_fid:
        ui.notify('Selecione fotos e certifique-se que a pasta SELECAO existe.', color='warning')
        return
    n = len(page_state['selected_files'])
    notif = ui.notification(f"Movendo {n} arquivos...", timeout=0, spinner=True)
    for fid in list(page_state['selected_files']):
        await asyncio.to_thread(drive_service.move_file, fid, selecao_fid)
    notif.dismiss()
    ui.notify(f'{n} arquivos movidos para SELECAO!', color='success')
    page_state['selected_files'].clear()


# ─── Moderacao e Galeria Pessoal ──────────────────────────────────────

def render_moderation(user_data, theme):
    """Renderiza grid de moderacao de reconhecimento facial."""
    db = get_db_connection()
    pending = []
    if db:
        try:
            res = db.table('photo_matches').select('*').eq('status', 'pendente').execute()
            if res.data:
                for m in res.data:
                    rp = db.table('processed_photos').select('*').eq('id', m['photo_id']).execute()
                    ru = db.table('Users').select('nome_guerra, telegram_id').eq('id', m['militar_id']).execute()
                    if rp.data and ru.data:
                        pending.append({'match_id': m['id'], 'similarity': m['similarity'],
                                        'bbox': m.get('bbox'), 'photo': rp.data[0], 'user': ru.data[0]})
        except Exception as ex:
            print(f"[GALERIA] [ERR] Moderacao: {ex}")

    if pending:
        with ui.element('div').classes('w-full gap-4').style(
            'display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));'
        ):
            for item in pending:
                p, u = item['photo'], item['user']
                sim_pct = item['similarity'] * 100
                with ui.card().classes('q-pa-none no-shadow rounded-xl overflow-hidden').style(
                    f'background: {theme["bg_panel"]}; border: 1px solid {theme["border"]};'
                ):
                    web_path = f"/assets/galeria_hot/{p.get('event_name','')}/{p.get('filename','')}"
                    ui.image(web_path).style('height: 160px; object-fit: cover;')
                    with ui.column().classes('q-pa-sm w-full gap-1'):
                        ui.label(f"{u['nome_guerra']}").classes('text-sm font-bold text-white')
                        ui.label(f"Evento: {p.get('event_name','')}").classes('text-xs text-grey-4')
                        ui.label(f"Similaridade: {sim_pct:.1f}%").classes('text-xs text-cyan font-bold')
                        with ui.row().classes('w-full justify-between q-mt-sm'):
                            async def rej(mid=item['match_id']):
                                conn = get_db_connection()
                                if conn:
                                    conn.table('photo_matches').update({'status': 'rejeitado'}).eq('id', mid).execute()
                                ui.notify('Rejeitado.', color='warning')

                            async def apr(mid=item['match_id'], tg=u.get('telegram_id'),
                                          link=p.get('drive_link', ''), ev=p.get('event_name', ''),
                                          nm=u['nome_guerra']):
                                conn = get_db_connection()
                                if conn:
                                    conn.table('photo_matches').update({'status': 'aprovado'}).eq('id', mid).execute()
                                    if tg:
                                        try:
                                            import telegram_bot
                                            bot = telegram_bot.bot
                                            if bot:
                                                caption = f"Uma nova foto sua foi registrada!\nEvento: {ev}\nMilitar: {nm}\nLink: {link}"
                                                await bot.send_message(chat_id=tg, text=caption)
                                        except Exception:
                                            pass
                                ui.notify('Aprovado e notificado!', color='success')

                            ui.button('Rejeitar', icon='close', on_click=rej).props('flat dense color=red').classes('text-xs')
                            ui.button('Aprovar', icon='check', on_click=apr).props('flat dense color=green').classes('text-xs font-bold')
    else:
        empty_state('fact_check', 'Nenhuma foto aguardando moderacao.')


def render_pessoal(user_id, theme):
    """Renderiza galeria pessoal do militar logado."""
    if not user_id:
        empty_state('person_off', 'Faca login para ver sua galeria pessoal.')
        return

    db = get_db_connection()
    photos = []
    if db:
        try:
            res = db.table('photo_matches').select('photo_id, similarity').eq(
                'militar_id', user_id
            ).eq('status', 'aprovado').execute()
            if res.data:
                for m in res.data:
                    rp = db.table('processed_photos').select('*').eq('id', m['photo_id']).execute()
                    if rp.data:
                        photos.append({'photo': rp.data[0], 'similarity': m['similarity']})
        except Exception as ex:
            print(f"[GALERIA] [ERR] Pessoal: {ex}")

    if photos:
        ui.badge(f'Voce apareceu em {len(photos)} fotos!', color='primary').classes('q-mb-md text-bold')
        with ui.element('div').classes('w-full gap-3').style(
            'display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));'
        ):
            for item in photos:
                p = item['photo']
                sim = item['similarity'] * 100
                web_path = f"/assets/galeria_hot/{p.get('event_name','')}/{p.get('filename','')}"
                with ui.card().classes('q-pa-none no-shadow rounded-lg overflow-hidden hover-scale').style(
                    f'background: {theme["bg_editor"]}; border: 1px solid {theme["border"]};'
                ):
                    ui.image(web_path).style('height: 150px; object-fit: cover;')
                    with ui.column().classes('q-pa-xs w-full gap-0'):
                        ui.label(p.get('event_name', '')).classes('text-[10px] font-bold text-white truncate')
                        ui.label(f"{sim:.0f}% de certeza").classes('text-[9px] text-cyan')
                        if p.get('drive_link'):
                            ui.button('Abrir no Drive', icon='open_in_new',
                                      on_click=lambda l=p['drive_link']: ui.open(l, new_tab=True)).props(
                                'flat dense color=cyan'
                            ).classes('text-[9px] w-full')
    else:
        empty_state('face', 'Voce ainda nao foi identificado em nenhuma foto. Cadastre sua selfie!')
