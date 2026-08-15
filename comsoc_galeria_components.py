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

import re

MONTH_MAP = {
    'JANEIRO': '01', 'JAN': '01',
    'FEVEREIRO': '02', 'FEV': '02',
    'MARCO': '03', 'MARÇO': '03', 'MAR': '03',
    'ABRIL': '04', 'ABR': '04',
    'MAIO': '05', 'MAI': '05',
    'JUNHO': '06', 'JUN': '06',
    'JULHO': '07', 'JUL': '07',
    'AGOSTO': '08', 'AGO': '08',
    'SETEMBRO': '09', 'SET': '09',
    'OUTUBRO': '10', 'OUT': '10',
    'NOVEMBRO': '11', 'NOV': '11',
    'DEZEMBRO': '12', 'DEZ': '12'
}

def parse_date_query(query: str):
    """Detecta datas no texto de busca (ex: '12 de agosto', '12/08', '12-08-2026')."""
    q_up = query.upper().strip()
    m = re.search(r'(\d{1,2})\s+DE\s+([A-ZÇ]+)(?:\s+DE\s+(\d{4}))?', q_up)
    if m:
        day = int(m.group(1))
        m_str = m.group(2)
        year = m.group(3)
        if m_str in MONTH_MAP:
            return f"{day:02d}", MONTH_MAP[m_str], year

    m2 = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', q_up)
    if m2:
        return f"{int(m2.group(3)):02d}", f"{int(m2.group(2)):02d}", m2.group(1)

    m3 = re.search(r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?', q_up)
    if m3:
        day = int(m3.group(1))
        month = int(m3.group(2))
        year = m3.group(3)
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{day:02d}", f"{month:02d}", year

    return None, None, None


def fuzzy_search(query: str, options: dict) -> list:
    """Busca fuzzy local por titulo de evento com suporte a datas exatas."""
    query_up = query.strip().upper()
    
    # 1. Filtro estrito de data se informado dia e mês (ex: 12 de agosto)
    day_str, month_str, year_str = parse_date_query(query)
    if day_str and month_str:
        target_pattern = f"{year_str}-{month_str}-{day_str}" if year_str else f"-{month_str}-{day_str}"
        date_results = []
        for eid, label in options.items():
            if target_pattern in label:
                date_results.append((eid, 0.99, label))
        if date_results:
            return date_results[:10]

    results = []
    for eid, label in options.items():
        label_up = label.upper()
        if query_up in label_up:
            results.append((eid, 0.95, label))
            continue
        words = [w for w in query_up.split() if len(w) > 2 and w not in ('DE', 'DO', 'DA', 'EM')]
        if words:
            word_hits = sum(1 for w in words if w in label_up)
            if word_hits > 0:
                results.append((eid, word_hits / len(words) * 0.8, label))
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
    """Extrai drive_folder_id de uma demanda com fallbacks universais."""
    if not pauta or not isinstance(pauta, dict):
        return None
    fid = pauta.get('drive_folder_id')
    if fid:
        return fid
    from database import get_demanda_drive_url
    url = get_demanda_drive_url(pauta)
    if url and 'folders/' in url:
        return url.split('folders/')[-1].split('?')[0].split('/')[0]
    if url and len(url) > 20 and '/' not in url:
        return url
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
    """Renderiza grid de fotos do Drive com paginação rápida, miniaturas HD e ações em lote."""
    if not fotos:
        empty_state('photo_library', 'Nenhuma foto encontrada nesta pasta.')
        return

    all_ids = {f.get('id') for f in fotos if f.get('id')}
    selected_set = page_state.setdefault('selected_files', set())
    grid_cfg = page_state.setdefault('grid_pagination', {'page': 1, 'per_page': 60})

    @ui.refreshable
    def _draw_grid_content():
        total_fotos = len(fotos)
        raw_per_page = grid_cfg.get('per_page', 60)
        
        if raw_per_page == 'all' or (isinstance(raw_per_page, int) and raw_per_page >= total_fotos):
            per_page = total_fotos
            total_pages = 1
            cur_page = 1
            start_idx = 0
            end_idx = total_fotos
        else:
            per_page = int(raw_per_page)
            total_pages = max(1, (total_fotos + per_page - 1) // per_page)
            cur_page = min(max(1, grid_cfg.get('page', 1)), total_pages)
            start_idx = (cur_page - 1) * per_page
            end_idx = min(start_idx + per_page, total_fotos)

        visible_fotos = fotos[start_idx:end_idx]
        visible_ids = {f.get('id') for f in visible_fotos if f.get('id')}

        def set_page(p):
            grid_cfg['page'] = min(max(1, p), total_pages)
            _draw_grid_content.refresh()
            ui.run_javascript('window.scrollTo({ top: 380, behavior: "smooth" });')

        def set_per_page(val):
            grid_cfg['per_page'] = val
            grid_cfg['page'] = 1
            _draw_grid_content.refresh()

        # ─── BARRA DE FERRAMENTAS E SELEÇÃO EM LOTE ───
        with ui.column().classes('w-full gap-2 q-mb-md'):
            with ui.row().classes('w-full items-center justify-between wrap gap-2 bg-slate-900/90 p-3 rounded-2xl border border-cyan-500/30 shadow-md'):
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    def toggle_cur():
                        page_state['curation_mode'] = not page_state.get('curation_mode', False)
                        _draw_grid_content.refresh()

                    cur_active = page_state.get('curation_mode', False)
                    btn_cur_col = 'amber' if cur_active else 'cyan-9'
                    ui.button(
                        'Modo Curadoria: LIGADO' if cur_active else '⚡ Ativar Modo Curadoria',
                        icon='brush' if cur_active else 'edit',
                        on_click=toggle_cur
                    ).props(f'dense unelevated color={btn_cur_col} text-color=white bold').classes('text-xs px-3 rounded-xl')

                    def select_page():
                        selected_set.update(visible_ids)
                        _draw_grid_content.refresh()

                    def select_all():
                        selected_set.update(all_ids)
                        _draw_grid_content.refresh()

                    def deselect_all():
                        selected_set.clear()
                        _draw_grid_content.refresh()

                    ui.button(f'☑️ Selecionar Página ({len(visible_fotos)})', on_click=select_page).props('flat dense color=cyan').classes('text-xs')
                    if total_fotos > len(visible_fotos):
                        ui.button(f'🌟 Selecionar Todas ({total_fotos})', on_click=select_all).props('flat dense color=amber-4').classes('text-xs font-bold')
                    ui.button('⬜ Desmarcar', on_click=deselect_all).props('flat dense color=grey-4').classes('text-xs')

                # Ações de Download e Curadoria
                n_sel = len(selected_set)
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    if n_sel > 0:
                        ui.badge(f'{n_sel} selecionada(s)', color='amber').classes('text-xs text-black font-bold')

                        def baixar_selecionadas():
                            id_list = ",".join(list(selected_set))
                            zip_url = f"/api/drive_download_zip?ids={id_list}"
                            ui.open(zip_url, new_tab=True)
                            ui.notify(f'🚀 Gerando e baixando arquivo ZIP com {n_sel} foto(s)...', color='positive')

                        ui.button(f'⬇️ Baixar Seleção ({n_sel})', icon='download', on_click=baixar_selecionadas).props(
                            'unelevated color=cyan text-color=black bold dense'
                        ).classes('text-xs px-3 rounded-xl')

                        if is_operator and not is_selecao and selecao_fid:
                            ui.button(f'⭐ Mover para SELEÇÃO ({n_sel})', icon='star',
                                      on_click=lambda: _mover_selecao(page_state, selecao_fid)).props(
                                'unelevated color=amber text-color=black bold dense'
                            ).classes('text-xs px-3 rounded-xl')

                    def baixar_tudo():
                        if is_selecao and selecao_fid:
                            zip_url = f"/api/drive_download_zip?folder_id={selecao_fid}"
                        else:
                            id_list = ",".join([f['id'] for f in fotos if f.get('id')])
                            zip_url = f"/api/drive_download_zip?ids={id_list}"
                        ui.open(zip_url, new_tab=True)
                        ui.notify(f'🚀 Gerando e baixando arquivo ZIP com todas as {total_fotos} foto(s)...', color='positive')

                    ui.button(f'📦 Baixar Todas ({total_fotos})', icon='cloud_download', on_click=baixar_tudo).props(
                        'outline color=cyan dense'
                    ).classes('text-xs px-3 rounded-xl')

            # ─── BARRA DE PAGINAÇÃO (TOPO) ───
            if total_pages > 1 or total_fotos > 30:
                with ui.row().classes('w-full items-center justify-between wrap gap-2 bg-slate-950 p-2.5 rounded-xl border border-white/10'):
                    with ui.row().classes('items-center gap-1'):
                        ui.button(icon='first_page', on_click=lambda: set_page(1)).props('flat dense color=cyan text-color=cyan round').classes('h-8 w-8').tooltip('Primeira Página')
                        ui.button(icon='chevron_left', on_click=lambda: set_page(cur_page - 1)).props('unelevated dense color=cyan-9 text-color=white round').classes('h-8 w-8').tooltip('Página Anterior')
                        
                        ui.label(f'Página {cur_page} de {total_pages}').classes('text-xs font-black text-cyan-3 px-2')
                        ui.label(f'({start_idx + 1}–{end_idx} de {total_fotos} fotos)').classes('text-[11px] text-grey-4')

                        ui.button(icon='chevron_right', on_click=lambda: set_page(cur_page + 1)).props('unelevated dense color=cyan-9 text-color=white round').classes('h-8 w-8').tooltip('Próxima Página')
                        ui.button(icon='last_page', on_click=lambda: set_page(total_pages)).props('flat dense color=cyan text-color=cyan round').classes('h-8 w-8').tooltip('Última Página')

                    with ui.row().classes('items-center gap-1.5'):
                        ui.label('Fotos por página:').classes('text-[11px] text-grey-4')
                        for opt_val, opt_lbl in [(30, '30'), (60, '60'), (120, '120'), (240, '240'), (500, '500')]:
                            is_curr = raw_per_page == opt_val
                            btn_style = 'unelevated color=cyan-7 text-color=black bold' if is_curr else 'flat color=grey text-color=grey-3'
                            ui.button(opt_lbl, on_click=lambda _, v=opt_val: set_per_page(v)).props(f'dense {btn_style}').classes('text-[11px] px-2 py-0.5 rounded-lg')

        # ─── GRID DE MINIATURAS (proporcao sem cortes, 260px min) ───
        with ui.element('div').classes('w-full gap-4').style(
            'display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));'
        ):
            for f in visible_fotos:
                fid = f.get('id')
                raw_thumb = f.get('thumbnailLink', '')
                if '=s220' in raw_thumb:
                    thumb = raw_thumb.replace('=s220', '=s800')
                elif '=' in raw_thumb:
                    thumb = raw_thumb.split('=')[0] + '=s800'
                else:
                    thumb = raw_thumb

                is_selected = fid in selected_set
                border_style = 'border: 2px solid #ffc107; box-shadow: 0 0 12px rgba(255,193,7,0.4);' if is_selected else (
                    'border: 1px solid rgba(255,193,7,0.6);' if is_selecao else f'border: 1px solid {theme["border"]};'
                )

                with ui.card().classes(
                    'q-pa-none no-shadow rounded-xl overflow-hidden cursor-pointer transition-all duration-200 hover:scale-[1.02]'
                ).style(f'background: {theme["bg_editor"]}; {border_style}'):

                    with ui.element('div').classes('relative w-full overflow-hidden').style(
                        'height: 240px; background: #030a17; display: flex; align-items: center; justify-content: center;'
                    ):
                        def make_toggle(file_id=fid):
                            def _toggle(e):
                                if file_id in selected_set:
                                    selected_set.remove(file_id)
                                else:
                                    selected_set.add(file_id)
                                _draw_grid_content.refresh()
                            return _toggle

                        ui.checkbox('', value=is_selected, on_change=make_toggle(fid)).classes(
                            'absolute top-2 left-2 z-20 bg-black/70 rounded p-1'
                        ).props('dark color=amber dense')

                        img = ui.image(thumb).style('max-height: 240px; width: 100%; object-fit: contain;')
                        img.on('click', lambda _, fi=f: preview_drive_photo(fi, theme))

                    with ui.row().classes('w-full p-2 items-center justify-between bg-slate-950 border-t border-white/5 gap-1'):
                        ui.label(f.get('name', '')).classes('text-[11px] text-grey-2 font-bold truncate flex-grow')
                        badge_txt = '⭐ Seleção' if is_selecao else '☁️ Drive'
                        badge_col = 'amber' if is_selecao else 'blue-grey'
                        ui.badge(badge_txt, color=badge_col).classes('text-[9px]')
                        
                        fname_esc = f.get('name', 'foto.jpg')
                        d_url = f"/api/drive_download/{fid}?filename={fname_esc}"
                        ui.button('Baixar', icon='download', on_click=lambda _, u=d_url: ui.open(u, new_tab=True)).props(
                            'unelevated color=cyan text-color=black dense bold'
                        ).classes('text-[10px] px-2 py-0.5').tooltip('Baixar foto HD')

        # ─── BARRA DE PAGINAÇÃO (RODAPÉ) ───
        if total_pages > 1:
            with ui.row().classes('w-full items-center justify-center gap-2 q-mt-md p-3 bg-slate-950/80 rounded-2xl border border-white/10'):
                ui.button(icon='first_page', on_click=lambda: set_page(1)).props('flat dense color=cyan text-color=cyan round').classes('h-9 w-9').tooltip('Primeira Página')
                ui.button('Anterior', icon='chevron_left', on_click=lambda: set_page(cur_page - 1)).props('unelevated color=cyan-9 text-color=white bold').classes('text-xs px-3 rounded-xl')
                
                ui.button('Próxima', icon='chevron_right', on_click=lambda: set_page(cur_page + 1)).props('unelevated color=cyan-9 text-color=white bold icon-right=chevron_right').classes('text-xs px-3 rounded-xl')
                ui.button(icon='last_page', on_click=lambda: set_page(total_pages)).props('flat dense color=cyan text-color=cyan round').classes('h-9 w-9').tooltip('Última Página')

    _draw_grid_content()


def preview_drive_photo(file_info, theme):
    """Modal de preview HD de foto do Drive com download."""
    with ui.dialog() as modal, ui.card().classes('q-pa-md max-w-5xl max-h-[95vh] overflow-hidden rounded-2xl').style(
        f'background: {theme["bg_panel"]}; border: 1px solid {theme["border"]}; shadow: 0 0 30px rgba(0,229,255,0.2);'
    ):
        with ui.row().classes('w-full justify-between items-center q-mb-xs'):
            ui.label(file_info.get('name', 'Visualização HD')).classes('text-sm font-bold text-cyan truncate max-w-[70%]')
            ui.button(icon='close', on_click=modal.close).props('flat round dense text-color=white')

        raw_thumb = file_info.get('thumbnailLink', '')
        large_img = raw_thumb.replace('=s220', '=s1600') if raw_thumb else file_info.get('webViewLink', '')
        if large_img:
            ui.image(large_img).style('max-height: 72vh; width: 100%; object-fit: contain; border-radius: 8px;')

        with ui.row().classes('w-full justify-between items-center q-mt-md'):
            created = file_info.get('createdTime', '')[:10]
            ui.label(f"📅 Data no Acervo: {created}").classes('text-xs text-grey-4')
            with ui.row().classes('gap-2'):
                if file_info.get('webContentLink'):
                    ui.button('⬇️ Baixar Foto Original', icon='download',
                              on_click=lambda: ui.open(file_info['webContentLink'], new_tab=True)).props(
                        'unelevated color=cyan text-color=black bold'
                    )
                if file_info.get('webViewLink'):
                    ui.button('📁 Abrir no Drive', icon='open_in_new',
                              on_click=lambda: ui.open(file_info['webViewLink'], new_tab=True)).props(
                        'outline color=grey-4'
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
