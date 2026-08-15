"""
portal_convidado.py — Portal do Convidado (Real-Time Hot Photo Delivery)
Módulo público de zero fricção para entrega de fotos em tempo real via reconhecimento facial.
Acesso via rota dinâmica /evento/{id_evento}.
"""

import os
import sys
import io
import time
import json
import base64
import zipfile
import asyncio
import math
from datetime import datetime
from pathlib import Path
from nicegui import ui, app
import numpy as np

import theme
from database import (
    get_public_event,
    get_event_photo_embeddings,
    save_guest_face_profile,
    save_guest_delivery,
    log_portal_analytics,
    send_real_email_smtp,
    get_service_db_connection,
    get_db_connection,
)
import drive_service

# Cache em memória da matriz de embeddings por evento
_EVENT_EMBEDDINGS_CACHE = {}
_EVENT_GERAL_PHOTOS_CACHE = {}

def _get_geral_photos(folder_id: str) -> list[dict]:
    """Retorna a lista de fotos da pasta geral do evento com cache em RAM por 1 hora."""
    if not folder_id:
        return []
    now = time.time()
    if folder_id in _EVENT_GERAL_PHOTOS_CACHE:
        c = _EVENT_GERAL_PHOTOS_CACHE[folder_id]
        if now - c['time'] < 3600:
            return c['photos']
    try:
        t0 = time.time()
        files = drive_service.list_files(folder_id, page_size=5000)
        photos = [
            {'drive_file_id': f['id'], 'drive_link': f.get('webViewLink'), 'filename': f.get('name', 'foto.jpg'), 'thumbnailLink': f.get('thumbnailLink')}
            for f in files
        ] if files else []
        _EVENT_GERAL_PHOTOS_CACHE[folder_id] = {'photos': photos, 'time': now}
        print(f"[PORTAL_DRIVE] ☁️ {len(photos)} fotos listadas do Drive em {time.time()-t0:.2f}s (cache criado)")
        return photos
    except Exception as e:
        print(f"[PORTAL_DRIVE] Erro ao listar Drive: {e}")
        return []


# ── SINGLETON DO MOTOR INSIGHTFACE (inicializado UMA vez, reutilizado sempre) ──
_FACE_APP_SINGLETON = None
_FACE_APP_LOCK = asyncio.Lock() if False else None  # placeholder; lock criado dinamicamente


def _get_face_app():
    """Retorna o singleton do FaceAnalysis, criando-o na primeira chamada."""
    global _FACE_APP_SINGLETON
    if _FACE_APP_SINGLETON is not None:
        return _FACE_APP_SINGLETON
    try:
        from sisgab_face_worker import init_face_engine
        _FACE_APP_SINGLETON = init_face_engine()
        if _FACE_APP_SINGLETON:
            print('[PORTAL_IA] ✅ Motor InsightFace carregado via sisgab_face_worker singleton!')
            return _FACE_APP_SINGLETON
    except Exception:
        pass
    try:
        from insightface.app import FaceAnalysis
        _FACE_APP_SINGLETON = FaceAnalysis(
            name='buffalo_l',
            allowed_modules=['detection', 'recognition']
        )
        _FACE_APP_SINGLETON.prepare(ctx_id=-1, det_size=(160, 160))  # 160px = rápido para selfies
        print('[PORTAL_IA] ✅ Motor InsightFace (buffalo_l, det=160px) pronto!')
    except Exception as e:
        print(f'[PORTAL_IA] ❌ Falha ao inicializar InsightFace: {e}')
        _FACE_APP_SINGLETON = None
    return _FACE_APP_SINGLETON

MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}


def _get_event_matrix(event_id: str) -> tuple[np.ndarray, list[dict]]:
    """Carrega matriz NxD de embeddings do evento com cache em RAM e arquivo binário em disco (.npz)."""
    now = time.time()
    if event_id in _EVENT_EMBEDDINGS_CACHE:
        cache = _EVENT_EMBEDDINGS_CACHE[event_id]
        if now - cache['timestamp'] < 86400:  # Cache em RAM por 24 horas
            return cache['matrix'], cache['records']

    # 1. Tenta carregar do arquivo binário em disco (velocidade: 0.01s)
    cache_dir = Path('data')
    cache_dir.mkdir(exist_ok=True)
    npz_path = cache_dir / f"event_embeddings_{event_id}.npz"
    json_path = cache_dir / f"event_records_{event_id}.json"

    if npz_path.exists() and json_path.exists():
        try:
            t0 = time.time()
            data = np.load(npz_path)
            matrix = data['matrix']
            with open(json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
            _EVENT_EMBEDDINGS_CACHE[event_id] = {
                'matrix': matrix,
                'records': records,
                'timestamp': now
            }
            print(f"[PORTAL_IA] ⚡ Matriz ({matrix.shape[0]} faces) carregada do disco em {time.time() - t0:.3f}s!")
            return matrix, records
        except Exception as e_npz:
            print(f"[PORTAL_IA] Erro ao ler cache em disco: {e_npz}")

    # 2. Se não estiver em disco, baixa do banco e salva em disco
    print(f"[PORTAL_IA] 📥 Baixando embeddings faciais do evento #{event_id} do Supabase...")
    t0 = time.time()
    raw_records = get_event_photo_embeddings(event_id)
    if not raw_records:
        return np.empty((0, 512), dtype=np.float32), []

    valid_vectors = []
    valid_records = []
    for r in raw_records:
        try:
            emb = r['embedding']
            if isinstance(emb, str):
                emb = json.loads(emb)
            if emb and len(emb) == 512:
                valid_vectors.append(np.array(emb, dtype=np.float32))
                valid_records.append({
                    'id': r.get('id'),
                    'drive_file_id': r.get('drive_file_id'),
                    'drive_link': r.get('drive_link'),
                    'photo_filename': r.get('photo_filename')
                })
        except Exception:
            continue

    if not valid_vectors:
        return np.empty((0, 512), dtype=np.float32), []

    matrix = np.stack(valid_vectors)  # Shape: (N, 512)
    _EVENT_EMBEDDINGS_CACHE[event_id] = {
        'matrix': matrix,
        'records': valid_records,
        'timestamp': now
    }

    try:
        np.savez_compressed(npz_path, matrix=matrix)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(valid_records, f)
        print(f"[PORTAL_IA] 💾 Cache em disco salvo ({matrix.shape[0]} faces)!")
    except Exception as e_save:
        print(f"[PORTAL_IA] Erro ao salvar cache em disco: {e_save}")

    print(f"[PORTAL_IA] ✅ Matriz indexada com {len(valid_vectors)} faces em {time.time() - t0:.2f}s!")
    return matrix, valid_records


async def _extract_upload_bytes(e) -> bytes:
    """Extrai os bytes do arquivo de forma 100% universal e compatível com NiceGUI 1.x e 2.x."""
    try:
        f = getattr(e, 'file', None)
        if f is not None:
            if hasattr(f, 'read'):
                res = f.read()
                if asyncio.iscoroutine(res):
                    return await res
                return res
        c = getattr(e, 'content', None)
        if c is not None:
            if hasattr(c, 'read'):
                res = c.read()
                if asyncio.iscoroutine(res):
                    return await res
                return res
            return c
    except Exception as ex:
        print(f"[EXTRACT UPLOAD BYTES ERR] {ex}")
    return b''


def _extract_selfie_embedding(image_bytes: bytes) -> tuple[bool, str, np.ndarray | None]:
    """Extrai o embedding facial 512D da selfie usando o singleton global do motor de IA."""
    if not image_bytes:
        return False, "❌ Imagem vazia ou inválida.", None

    # Decodifica e redimensiona para 640px máx (suficiente para selfie, rápido)
    img_bgr = None
    try:
        from PIL import Image as PILImage
        pil_img = PILImage.open(io.BytesIO(image_bytes)).convert('RGB')
        w, h = pil_img.size
        if max(w, h) > 640:
            scale = 640.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), PILImage.Resampling.LANCZOS)
        img_rgb = np.array(pil_img)
        img_bgr = img_rgb[:, :, ::-1].copy()
    except Exception as e_pil:
        try:
            import cv2
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            return False, f"❌ Erro ao decodificar imagem: {e_pil}", None

    if img_bgr is None:
        return False, "❌ Não foi possível carregar a imagem enviada.", None

    try:
        app_face = _get_face_app()
        if app_face is None:
            return False, "❌ Motor de IA não disponível no momento. Tente novamente em instantes.", None

        t0 = time.time()
        faces = app_face.get(img_bgr)
        print(f'[PORTAL_IA] 🔍 Detecção facial em {time.time()-t0:.3f}s → {len(faces)} rosto(s)')

        if not faces:
            return False, "❌ Nenhum rosto detectado. Envie uma foto nítida e bem iluminada de frente.", None

        # Seleciona o rosto com maior det_score (frente da câmera)
        face = max(faces, key=lambda f: getattr(f, 'det_score', 0))

        if hasattr(face, 'det_score') and face.det_score < 0.40:
            return False, "❌ Rosto pouco nítido ou desfocado. Tente em ambiente mais claro.", None

        return True, "✅ Rosto identificado com sucesso!", face.normed_embedding

    except Exception as e:
        return False, f"❌ Erro ao processar biometria: {e}", None


def render_page(event_id: str):
    """Renderiza a página completa do Portal do Convidado para o evento especificado."""
    theme.apply_global_styles()
    ui.add_head_html('''
    <style>
        .photo-card-selected {
            border: 2px solid #00e5ff !important;
            box-shadow: 0 0 15px rgba(0,229,255,0.4) !important;
        }
    </style>
    ''')

    event = get_public_event(event_id)

    # ── EVENTO NÃO LOCALIZADO OU INATIVO ────────────────────────────────────
    if not event:
        with ui.column().classes('w-full min-h-screen items-center justify-center p-6 text-center').style('background: radial-gradient(circle, #1e1b4b 0%, #0b0f19 100%);'):
            ui.icon('event_busy', size='4.5rem', color='red-5')
            ui.label('EVENTO NÃO ENCONTRADO').classes('cyber-title text-2xl font-bold text-red-4 q-mt-md')
            ui.label('O link acessado não corresponde a um evento público ativo no momento.').classes('text-sm text-grey-4 max-w-md')
            ui.button('Voltar ao Início', on_click=lambda: ui.navigate.to('/')).props('flat color=cyan').classes('q-mt-lg')
        return

    if event.get('status') != 'ativo':
        with ui.column().classes('w-full min-h-screen items-center justify-center p-6 text-center').style('background: radial-gradient(circle, #1e1b4b 0%, #0b0f19 100%);'):
            ui.icon('lock_clock', size='4.5rem', color='amber-5')
            ui.label('GALERIA ENCERRADA').classes('cyber-title text-2xl font-bold text-amber-4 q-mt-md')
            ui.label(f"A galeria do evento '{event.get('nome')}' foi encerrada pela organização.").classes('text-sm text-grey-4 max-w-md')
        return

    # Registra analytics de acesso
    session_id = app.storage.user.get('portal_session_id')
    if not session_id:
        session_id = f"guest_{int(time.time()*1000)}"
        app.storage.user['portal_session_id'] = session_id
    
    log_portal_analytics(event_id, 'acesso', session_id=session_id)

    # Estado local persistente da sessão do convidado
    saved_selfies = app.storage.user.get(f'portal_embs_{event_id}', [])
    guest_state = {
        'selfie_embeddings': saved_selfies or [],
        'matched_photos': [],
        'geral_photos': [],
        'selected_fids': set(),
        'has_searched': bool(saved_selfies),
        'guest_name': app.storage.user.get('portal_guest_name', ''),
        'guest_email': app.storage.user.get('portal_guest_email', ''),
        'rate_limit_count': 0,
        'last_search_time': 0,
        'page': 1,
        'per_page': 60,
    }

    # Dados do evento
    nome_evento = event.get('nome', 'Evento Oficial')
    local_evento = event.get('local', 'Gabinete do CGCFN')
    data_str = event.get('data_evento', '')
    if data_str:
        try:
            dt = datetime.strptime(str(data_str)[:10], '%Y-%m-%d')
            mes_nome = MESES_PT.get(dt.month, str(dt.month))
            data_formatada = f"{dt.day:02d} de {mes_nome} de {dt.year}"
        except Exception:
            data_formatada = str(data_str)
    else:
        data_formatada = ''

    threshold_match = float(event.get('threshold_match') or 0.40)
    drive_geral_id = event.get('drive_geral_folder_id') or event.get('drive_folder_id')

    # Pré-aquece SIMULTANEAMENTE: motor de IA + matriz de embeddings do evento + fotos gerais do Drive
    asyncio.create_task(asyncio.to_thread(_get_face_app))
    asyncio.create_task(asyncio.to_thread(_get_event_matrix, event_id))
    if drive_geral_id:
        asyncio.create_task(asyncio.to_thread(_get_geral_photos, drive_geral_id))

    # Container principal — ocupa toda a tela
    with ui.column().classes('w-full min-h-screen items-center justify-start p-2 sm:p-4 bg-slate-950 text-white').style('font-family: "Outfit", sans-serif;'):

        # ── INPUTS DE UPLOAD OFF-SCREEN (100% compatíveis com Android, iOS e Desktop) ──
        with ui.element('div').style('position: fixed; top: -9999px; left: -9999px; width: 1px; height: 1px; opacity: 0; pointer-events: none;'):
            ui.upload(
                on_upload=lambda e: process_image_from_upload(e),
                auto_upload=True,
                max_files=1
            ).props('id=portal-cam-upload accept="image/*" capture="user"')
            
            ui.upload(
                on_upload=lambda e: process_image_from_upload(e),
                auto_upload=True,
                max_files=1
            ).props('id=portal-gal-upload accept="image/*"')

        # ── CARD PRINCIPAL COMPACTO DO EVENTO ─────────────────────────────────
        with ui.card().classes('w-full max-w-5xl bg-slate-900/90 border border-amber-500/30 rounded-2xl shadow-xl overflow-hidden p-3 sm:p-5 text-center gap-1.5'):
            ui.label(nome_evento.upper()).classes('text-base sm:text-2xl font-black text-white tracking-wide leading-tight')
            with ui.row().classes('items-center justify-center gap-3 sm:gap-5 text-xs text-grey-4 flex-wrap mt-0.5'):
                if data_formatada:
                    ui.label(f"📅 {data_formatada}").classes('font-bold text-amber-3')
                if local_evento:
                    ui.label(f"📍 {local_evento}").classes('font-semibold text-cyan-3')

        # ── ÁREA DINÂMICA DE CONTEÚDO ─────────────────────────────────────────
        content_container = ui.column().classes('w-full max-w-5xl p-0 gap-4 mt-2')

        def refresh_ui():
            content_container.clear()
            with content_container:
                render_portal_content()

        # ── PROCESSAMENTO DO ARQUIVO RECEBIDO ──────────────────────────────────
        async def process_image_from_upload(e):
            try:
                content = await _extract_upload_bytes(e)
                if not content:
                    ui.notify("Não foi possível ler o arquivo enviado. Tente novamente.", color='warning')
                    return
                await process_image_bytes(content)
            except Exception as ex_up:
                ui.notify(f"Erro no envio da foto: {ex_up}", color='negative')

        async def process_image_bytes(file_content: bytes):
            now_t = time.time()
            if guest_state['rate_limit_count'] >= 8 and (now_t - guest_state['last_search_time'] < 20):
                ui.notify('⏳ Por favor, aguarde alguns segundos antes de tentar novamente.', color='warning')
                return

            guest_state['rate_limit_count'] += 1
            guest_state['last_search_time'] = now_t

            if not file_content or len(file_content) < 1000:
                ui.notify('❌ Imagem inválida ou vazia.', color='negative')
                return

            # Spinner de busca amigável
            with ui.dialog() as loading_dialog, ui.card().classes('bg-slate-900 border border-cyan-500/40 p-6 items-center text-center gap-4 rounded-2xl'):
                ui.spinner(size='3rem', color='cyan')
                ui.label('Analisando sua foto com IA...').classes('text-lg font-bold text-white')
                ui.label('Buscando suas fotos no evento em tempo real.').classes('text-xs text-grey-4')
            loading_dialog.open()

            # Processa embedding da selfie em thread com downscaling
            ok, msg, embedding = await asyncio.to_thread(_extract_selfie_embedding, file_content)

            if not ok or embedding is None:
                loading_dialog.close()
                ui.notify(msg, color='negative', timeout=6000)
                return

            # Adiciona o vetor à lista de selfies do convidado (até 3)
            guest_state['selfie_embeddings'].append(embedding.tolist())
            if len(guest_state['selfie_embeddings']) > 3:
                guest_state['selfie_embeddings'] = guest_state['selfie_embeddings'][-3:]

            # Persiste na sessão para recuperação automática em caso de queda de conexão
            app.storage.user[f'portal_embs_{event_id}'] = guest_state['selfie_embeddings']

            # Registra perfil no banco
            save_guest_face_profile(
                event_id, session_id, guest_state['selfie_embeddings'],
                nome=guest_state['guest_name'], email=guest_state['guest_email']
            )
            log_portal_analytics(event_id, 'selfie', session_id=session_id)

            # Executa match contra a matriz do evento
            matched_items, n_faces = await execute_matching()

            loading_dialog.close()

            # Notifica resultado no contexto correto do slot NiceGUI
            pin_req = str(event.get('pin_acesso') or '').strip()
            if matched_items:
                if pin_req:
                    app.storage.user[f'portal_auth_{event_id}'] = True
                ui.notify(f"🎉 {len(matched_items)} foto(s) sua(s) encontrada(s) no evento!", color='positive', timeout=5000)
            elif n_faces == 0:
                ui.notify('⚠️ Nenhum rosto detectado. Tente uma foto mais nítida e de frente.', color='warning', timeout=6000)
            else:
                ui.notify('ℹ️ Nenhuma foto sua identificada nesta busca. Veja a Galeria Oficial abaixo.', color='info', timeout=6000)

            refresh_ui()

        async def execute_matching() -> tuple[list, int]:
            """Executa o match vetorial e retorna (matched_items, n_embeddings_selfie)."""
            matrix, records = await asyncio.to_thread(_get_event_matrix, event_id)
            matched_items = []
            n_faces = len(guest_state['selfie_embeddings'])

            if matrix.shape[0] > 0 and guest_state['selfie_embeddings']:
                all_scores = np.zeros(matrix.shape[0], dtype=np.float32)
                for s_emb in guest_state['selfie_embeddings']:
                    s_vec = np.array(s_emb, dtype=np.float32)
                    norm = np.linalg.norm(s_vec)
                    if norm > 0:
                        s_vec = s_vec / norm
                    scores = matrix @ s_vec
                    all_scores = np.maximum(all_scores, scores)

                seen_fids = set()
                for idx in np.argsort(-all_scores):
                    score = float(all_scores[idx])
                    if score < threshold_match:
                        break
                    rec = records[idx]
                    fid = rec.get('drive_file_id')
                    if fid and fid not in seen_fids:
                        seen_fids.add(fid)
                        matched_items.append({
                            'drive_file_id': fid,
                            'drive_link': rec.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view",
                            'filename': rec.get('photo_filename', 'foto.jpg'),
                            'similarity': score
                        })

            guest_state['matched_photos'] = matched_items
            guest_state['has_searched'] = True

            try:
                pin_req = str(event.get('pin_acesso') or '').strip()
                if matched_items:
                    if pin_req:
                        app.storage.user[f'portal_auth_{event_id}'] = True
                    log_portal_analytics(event_id, 'match', session_id=session_id, metadata={'count': len(matched_items)})
            except Exception:
                pass

            return matched_items, n_faces

        # ── RENDERIZAÇÃO DO CONTEÚDO ──────────────────────────────────────────
        def render_portal_content():
            pin_evento = str(event.get('pin_acesso') or '').strip()
            is_auth = True
            if pin_evento:
                is_auth = app.storage.user.get(f'portal_auth_{event_id}', False)

            # Se o evento possui PIN e o usuário ainda não autenticou
            if not is_auth:
                with ui.card().classes('w-full bg-slate-950/95 border-2 border-amber-500/40 rounded-2xl p-4 sm:p-6 items-center text-center gap-4 shadow-2xl'):
                    ui.icon('lock', size='3rem', color='amber-4')
                    ui.label('ACESSO RESTRITO AO EVENTO').classes('text-base sm:text-xl font-black text-white tracking-wider')
                    ui.label('Digite o PIN do evento ou valide sua presença com uma selfie facial.').classes('text-xs text-grey-3 max-w-sm')

                    pin_box = ui.input('PIN do Evento', placeholder='Digite o PIN').props('dark outlined dense type=password').classes('w-full max-w-xs text-center text-lg tracking-widest')
                    
                    def verificar_pin():
                        val = (pin_box.value or '').strip()
                        if val.lower() == pin_evento.lower():
                            app.storage.user[f'portal_auth_{event_id}'] = True
                            ui.notify('✅ Acesso liberado!', color='positive')
                            refresh_ui()
                        else:
                            ui.notify('❌ PIN incorreto. Tente novamente ou use a validação por Selfie.', color='negative')

                    ui.button('🔓 DESBLOQUEAR COM PIN', icon='key', on_click=verificar_pin).props('unelevated color=amber-9 text-color=black bold').classes('w-full max-w-xs h-12 rounded-xl text-xs font-bold')

                    ui.separator().classes('w-full').style('background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.4), transparent);')

                    ui.label('OU VALIDE SUA PRESENÇA COM UMA SELFIE').classes('text-xs font-bold text-cyan-4 tracking-wider')

                    with ui.row().classes('w-full justify-center gap-2 sm:gap-3 flex-wrap'):
                        ui.button(
                            '📸 VALIDAR COM CÂMERA',
                            icon='photo_camera',
                            on_click=lambda: ui.run_javascript('document.querySelector("#portal-cam-upload input[type=file]")?.click()')
                        ).props('unelevated color=cyan-8 text-color=white bold no-caps').classes('flex-1 min-w-[150px] h-12 rounded-xl text-xs font-bold')

                        ui.button(
                            '📁 ESCOLHER FOTO DA GALERIA',
                            icon='photo_library',
                            on_click=lambda: ui.run_javascript('document.querySelector("#portal-gal-upload input[type=file]")?.click()')
                        ).props('unelevated color=amber-8 text-color=black bold no-caps').classes('flex-1 min-w-[150px] h-12 rounded-xl text-xs font-bold')

                return

            # 1. SEÇÃO DE BUSCA FACIAL — COMPACTA E DIRETA
            num_selfies = len(guest_state['selfie_embeddings'])
            with ui.card().classes('w-full bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-3 sm:p-5 gap-2.5 shadow-xl'):

                if num_selfies == 0:
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.row().classes('items-center gap-1.5'):
                            ui.icon('face', size='1.4rem', color='cyan-4')
                            ui.label('ENCONTRE SUAS FOTOS DO EVENTO').classes('text-xs sm:text-base font-black text-white tracking-wide')
                        ui.badge('✨ IA Facial', color='cyan-9').classes('text-[10px] font-bold px-1.5')

                    # Orientações em linha única
                    with ui.row().classes('w-full justify-center gap-2 text-[11px] text-grey-3 py-0.5 flex-wrap'):
                        ui.label('☀️ Boa luz').classes('bg-slate-950 px-2 py-0.5 rounded-md border border-white/5')
                        ui.label('👤 De frente').classes('bg-slate-950 px-2 py-0.5 rounded-md border border-white/5')
                        ui.label('🚫 Sem óculos').classes('bg-slate-950 px-2 py-0.5 rounded-md border border-white/5')
                else:
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.row().classes('items-center gap-1.5'):
                            ui.icon('check_circle', size='1.4rem', color='green-4')
                            ui.label(f"Biometria ativa ({num_selfies} foto{'s' if num_selfies>1 else ''})").classes('text-xs sm:text-sm font-bold text-green-4')
                        ui.badge('Ativo', color='green-9').classes('text-[10px] font-bold px-1.5')

                # BOTÕES NATIVOS 100% CLICÁVEIS
                with ui.row().classes('w-full gap-2 sm:gap-3 mt-1'):
                    btn_cam_label = '📸 TIRAR SELFIE (CÂMERA)' if num_selfies == 0 else '📸 OUTRA SELFIE'
                    ui.button(
                        btn_cam_label,
                        on_click=lambda: ui.run_javascript('document.querySelector("#portal-cam-upload input[type=file]")?.click()')
                    ).props('unelevated color=cyan-7 text-color=black bold no-caps').classes(
                        'flex-1 h-12 sm:h-14 font-black rounded-xl text-xs sm:text-sm shadow-md active:scale-95 transition-transform'
                    )

                    btn_gal_label = '📁 ESCOLHER FOTO' if num_selfies == 0 else '📁 OUTRA FOTO'
                    ui.button(
                        btn_gal_label,
                        on_click=lambda: ui.run_javascript('document.querySelector("#portal-gal-upload input[type=file]")?.click()')
                    ).props('unelevated color=amber-7 text-color=black bold no-caps').classes(
                        'flex-1 h-12 sm:h-14 font-black rounded-xl text-xs sm:text-sm shadow-md active:scale-95 transition-transform'
                    )

                if num_selfies > 0:
                    def reset_selfies():
                        guest_state['selfie_embeddings'] = []
                        guest_state['matched_photos'] = []
                        guest_state['has_searched'] = False
                        app.storage.user[f'portal_embs_{event_id}'] = []
                        ui.notify('Biometria limpa.', color='info')
                        refresh_ui()
                    with ui.row().classes('items-center justify-between w-full pt-1'):
                        ui.label('🔒 Foto processada em memória e descartada.').classes('text-[10px] text-grey-5')
                        ui.button('Recomeçar', icon='refresh', on_click=reset_selfies).props('flat dense color=grey-4 size=xs').classes('text-[10px]')
                else:
                    ui.label('🔒 Sua foto é processada em memória e descartada imediatamente.').classes('text-[10px] text-grey-5 text-center w-full')

            # 2. BARRA DE FERRAMENTAS DE SELEÇÃO & DOWNLOAD EM LOTE
            render_selection_toolbar()

            # 3. SEÇÃO DE FOTOS PESSOAIS IDENTIFICADAS
            if guest_state['has_searched']:
                if guest_state['matched_photos']:
                    with ui.column().classes('w-full gap-2.5 q-mt-3'):
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.row().classes('items-center gap-1.5'):
                                ui.icon('auto_awesome', size='1.4rem', color='amber-4')
                                ui.label('SUAS FOTOS IDENTIFICADAS').classes('text-sm sm:text-lg font-black text-amber-4 tracking-wide')
                            ui.badge(f"{len(guest_state['matched_photos'])} fotos", color='amber-9').classes('text-xs font-bold px-2 py-0.5 rounded-lg')

                        render_photo_grid(guest_state['matched_photos'], is_personal=True)
                else:
                    with ui.card().classes('w-full bg-slate-900/90 border border-amber-500/30 rounded-2xl p-3.5 text-center items-center gap-1 shadow-lg'):
                        ui.icon('person_search', size='2rem', color='amber-4')
                        ui.label('Nenhuma foto sua identificada nesta selfie').classes('text-xs sm:text-sm font-bold text-white')
                        ui.label('Dica: Envie outra foto bem iluminada de frente, ou confira a Galeria Oficial abaixo.').classes('text-[11px] text-grey-4 max-w-md')

            # 4. SEÇÃO DE FOTOS OFICIAIS DO EVENTO (PASTA GERAL)
            with ui.column().classes('w-full gap-2.5 q-mt-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-1.5'):
                        ui.icon('collections', size='1.4rem', color='cyan-4')
                        ui.label('GALERIA OFICIAL DO EVENTO').classes('text-sm sm:text-lg font-black text-cyan-3 tracking-wide')
                    ui.label('Fotos institucionais').classes('text-[11px] text-grey-4')

                render_official_gallery(drive_geral_id)

            # 5. SEÇÃO DE ENTREGA (E-MAIL INSTITUCIONAL & WHATSAPP)
            render_delivery_section()

        # ── BARRA DE SELEÇÃO MÚLTIPLA E DOWNLOAD EM LOTE ──────────────────────
        def render_selection_toolbar():
            all_visible = guest_state['matched_photos'] + guest_state['geral_photos']
            if not all_visible:
                return

            total_geral = len(guest_state['geral_photos'])
            per_p = guest_state.get('per_page', 60)
            cur_p = guest_state.get('page', 1)
            start_i = (cur_p - 1) * per_p
            end_i = min(start_i + per_p, total_geral)
            page_geral = guest_state['geral_photos'][start_i:end_i]
            page_all = guest_state['matched_photos'] + page_geral

            selected_count = len(guest_state['selected_fids'])

            with ui.card().classes('w-full bg-slate-900/90 border border-white/10 rounded-2xl p-2.5 sm:p-3 shadow-md'):
                with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                    with ui.row().classes('items-center gap-1.5'):
                        ui.icon('check_box', size='1.2rem', color='cyan-4')
                        ui.label(f"{selected_count} selecionada(s)").classes('text-xs font-bold text-white')

                    with ui.row().classes('items-center gap-1.5 flex-wrap'):
                        def select_page():
                            for p in page_all:
                                fid = p.get('drive_file_id') or p.get('id')
                                if fid: guest_state['selected_fids'].add(fid)
                            refresh_ui()

                        def select_all():
                            for p in all_visible:
                                fid = p.get('drive_file_id') or p.get('id')
                                if fid: guest_state['selected_fids'].add(fid)
                            refresh_ui()

                        def clear_selection():
                            guest_state['selected_fids'].clear()
                            refresh_ui()

                        ui.button(f'Página ({len(page_all)})', icon='done', on_click=select_page).props('outline color=cyan-4 text-color=cyan-3 dense size=sm no-caps').classes('text-[11px] rounded-lg px-2')
                        ui.button(f'Todas ({len(all_visible)})', icon='done_all', on_click=select_all).props('outline color=amber-4 text-color=amber-3 dense size=sm no-caps').classes('text-[11px] rounded-lg px-2')

                        if selected_count > 0:
                            ui.button('Desmarcar', icon='clear', on_click=clear_selection).props('flat color=grey-4 dense size=sm no-caps').classes('text-[11px] px-1.5')

                        async def download_selected_zip():
                            fids_to_dl = list(guest_state['selected_fids']) if guest_state['selected_fids'] else [p.get('drive_file_id') for p in all_visible]
                            if not fids_to_dl:
                                ui.notify('Nenhuma foto selecionada.', color='warning')
                                return

                            n_zip = ui.notify(f"📦 Compactando {len(fids_to_dl)} foto(s) em arquivo ZIP...", color='info', spinner=True, timeout=0)
                            try:
                                def build_zip():
                                    buf = io.BytesIO()
                                    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                                        for idx, fid in enumerate(fids_to_dl):
                                            img_b = drive_service.download_file(fid)
                                            if img_b:
                                                zf.writestr(f"foto_{idx+1:03d}_{fid}.jpg", img_b)
                                    buf.seek(0)
                                    return buf.getvalue()

                                zip_bytes = await asyncio.to_thread(build_zip)
                                log_portal_analytics(event_id, 'download', session_id=session_id, metadata={'count': len(fids_to_dl)})
                                ui.download(zip_bytes, f"fotos_{event_id}.zip")
                                ui.notify('✅ Download do ZIP iniciado!', color='positive')
                            except Exception as ex_zip:
                                ui.notify(f"Erro ao gerar ZIP: {ex_zip}", color='negative')
                            finally:
                                try: n_zip.dismiss()
                                except Exception: pass

                        dl_btn_label = f"📥 Baixar ({selected_count})" if selected_count > 0 else f"📥 Baixar Todas ({len(all_visible)})"
                        ui.button(dl_btn_label, icon='archive', on_click=download_selected_zip).props('unelevated color=amber-8 text-color=black bold size=sm no-caps').classes('text-[11px] font-bold rounded-xl px-2.5')

        # ── GRADE DE FOTOS RESPONSIVA (ENCAIXE PERFEITO ASPECT 4:3) ───────────
        def render_photo_grid(photos_list: list[dict], is_personal: bool = False):
            with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2 sm:gap-3'):
                for idx, p in enumerate(photos_list):
                    fid = p.get('drive_file_id') or p.get('id')
                    raw_thumb = str(p.get('thumbnailLink') or '')
                    if '=s220' in raw_thumb:
                        thumb_url = raw_thumb.replace('=s220', '=s800')
                    elif '=' in raw_thumb:
                        thumb_url = raw_thumb.split('=')[0] + '=s800'
                    elif fid:
                        thumb_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w800"
                    else:
                        thumb_url = ''

                    is_selected = fid in guest_state['selected_fids']
                    border_style = 'border: 2px solid #00e5ff; box-shadow: 0 0 12px rgba(0,229,255,0.4);' if is_selected else 'border: 1px solid rgba(255,255,255,0.08);'

                    with ui.card().classes('q-pa-none no-shadow rounded-xl overflow-hidden cursor-pointer transition-transform duration-150 active:scale-[0.98]').style(f'background: #0f172a; {border_style}'):
                        # Container da foto com formato horizontal landscape (16:10)
                        with ui.element('div').classes('relative w-full bg-[#030a17] flex items-center justify-center overflow-hidden').style('aspect-ratio: 16/10;'):
                            def toggle_select(f=fid):
                                if f in guest_state['selected_fids']:
                                    guest_state['selected_fids'].remove(f)
                                else:
                                    guest_state['selected_fids'].add(f)
                                refresh_ui()

                            # Checkbox compacto no canto superior
                            with ui.element('div').classes('absolute top-1 left-1 z-20 bg-black/70 backdrop-blur-md rounded-md p-0.5').on('click', lambda _, f=fid: toggle_select(f)):
                                ui.checkbox(value=is_selected, on_change=lambda _, f=fid: toggle_select(f)).props('dark color=cyan dense size=xs')

                            img = ui.image(thumb_url).classes('w-full h-full').style('object-fit: cover;')
                            img.on('click', lambda _, i=idx, l=photos_list: open_full_lightbox(i, l))

                        # Rodapé em duas linhas compactas
                        with ui.column().classes('w-full p-1.5 sm:p-2 bg-slate-950/95 border-t border-white/5 gap-0.5'):
                            fname = p.get('filename') or p.get('name') or 'foto.jpg'
                            ui.label(fname).classes('text-[10px] text-slate-300 font-semibold truncate w-full')
                            
                            with ui.row().classes('w-full items-center justify-between gap-1'):
                                badge_txt = '⭐ Sua foto' if is_personal else '☁️ Drive'
                                badge_col = 'amber-9' if is_personal else 'blue-grey-8'
                                ui.badge(badge_txt, color=badge_col).classes('text-[8px] font-bold px-1.5 py-0.5')

                                with ui.row().classes('items-center gap-0.5'):
                                    ui.button(icon='fullscreen', on_click=lambda _, i=idx, l=photos_list: open_full_lightbox(i, l)).props('flat dense size=xs color=grey-4').classes('p-0.5').tooltip('Ampliar')
                                    ui.button(icon='download', on_click=lambda _, f=fid: download_single(f)).props('unelevated color=cyan text-color=black dense bold size=xs').classes('px-1.5 py-0.2 rounded text-[9px]').tooltip('Baixar foto HD')

            # ── GALERIA OFICIAL COM PAGINAÇÃO COMPLETA (IGUAL COMSOC_GALERIA) ─
            def render_official_gallery(folder_id: str):
                if not folder_id:
                    ui.label('Nenhuma foto oficial disponibilizada ainda.').classes('text-xs text-grey-5 italic')
                    return

                try:
                    if not guest_state['geral_photos']:
                        guest_state['geral_photos'] = _get_geral_photos(folder_id)

                    fotos = guest_state['geral_photos']
                    if not fotos:
                        ui.label('As fotos do evento estão sendo processadas pela equipe de Comunicação Social.').classes('text-xs text-grey-4 italic')
                        return

                    total_fotos = len(fotos)
                    per_page = guest_state.get('per_page', 60)
                    total_pages = max(1, math.ceil(total_fotos / per_page))
                    cur_page = max(1, min(guest_state.get('page', 1), total_pages))
                    guest_state['page'] = cur_page

                    start_idx = (cur_page - 1) * per_page
                    end_idx = min(start_idx + per_page, total_fotos)
                    visible_fotos = fotos[start_idx:end_idx]

                    def set_page(p):
                        guest_state['page'] = max(1, min(p, total_pages))
                        refresh_ui()

                    def set_per_page(v):
                        guest_state['per_page'] = v
                        guest_state['page'] = 1
                        refresh_ui()

                    # ─── GRID DE FOTOS DA PÁGINA ───
                    render_photo_grid(visible_fotos, is_personal=False)

                    # ─── PAGINAÇÃO APENAS NO RODAPÉ: centralizada, linha única com seletor ───
                    with ui.row().classes('w-full items-center justify-center flex-wrap gap-2 sm:gap-3 mt-4 pt-3 border-t border-white/10'):
                        ui.button(icon='first_page', on_click=lambda: set_page(1)).props('flat dense color=cyan round size=sm').tooltip('Primeira')
                        ui.button(icon='chevron_left', on_click=lambda: set_page(cur_page - 1)).props('unelevated dense color=cyan-9 text-color=white round size=sm').tooltip('Anterior')

                        ui.label(f'Pág. {cur_page}/{total_pages}').classes('text-xs font-bold text-cyan-3 px-1')
                        ui.label(f'({start_idx+1}–{end_idx} de {total_fotos})').classes('text-[11px] text-grey-5')

                        ui.button(icon='chevron_right', on_click=lambda: set_page(cur_page + 1)).props('unelevated dense color=cyan-9 text-color=white round size=sm').tooltip('Próxima')
                        ui.button(icon='last_page', on_click=lambda: set_page(total_pages)).props('flat dense color=cyan round size=sm').tooltip('Última')

                        ui.separator().props('vertical').classes('h-6 opacity-30')

                        for opt_val, opt_lbl in [(30,'30'),(60,'60'),(120,'120'),(240,'240'),(500,'500')]:
                            is_curr = per_page == opt_val
                            ui.button(opt_lbl, on_click=lambda _, v=opt_val: set_per_page(v)).props(
                                f'dense {"unelevated color=cyan-7 text-color=black" if is_curr else "flat color=grey text-color=grey-4"}'
                            ).classes('text-[11px] px-2 rounded-lg min-w-[28px]')

                except Exception as e:
                    ui.label(f"Não foi possível carregar a galeria: {e}").classes('text-xs text-red-4')

            # ── LIGHTBOX AVANÇADO COM PASSADOR ⬅️ ➡️ E TECLADO ──────────────
            def open_full_lightbox(initial_index: int, photos_list: list[dict]):
                cur_idx = {'val': initial_index}

                with ui.dialog() as dlg, ui.card().classes('bg-black/95 border border-cyan-500/40 p-2 sm:p-4 items-center rounded-3xl w-[96vw] max-w-5xl max-h-[95vh] overflow-hidden justify-between flex flex-col'):
                    
                    # Topo do Lightbox
                    with ui.row().classes('w-full justify-between items-center p-2 border-b border-white/10'):
                        counter_label = ui.label(f"Foto {cur_idx['val'] + 1} de {len(photos_list)}").classes('text-xs sm:text-sm font-bold text-cyan-3')
                        with ui.row().classes('items-center gap-2'):
                            btn_dl_box = ui.button(icon='download', on_click=lambda: download_single(photos_list[cur_idx['val']]['drive_file_id'])).props('flat dense size=sm color=amber')
                            ui.button(icon='close', on_click=dlg.close).props('flat round dense text-color=white')

                    # Imagem Central
                    img_elem = ui.image(f"https://drive.google.com/thumbnail?id={photos_list[cur_idx['val']]['drive_file_id']}&sz=w1600").classes('max-w-full max-h-[72vh] object-contain rounded-2xl my-2')

                    def update_lightbox_img(new_i: int):
                        if 0 <= new_i < len(photos_list):
                            cur_idx['val'] = new_i
                            fid = photos_list[new_i]['drive_file_id']
                            img_elem.set_source(f"https://drive.google.com/thumbnail?id={fid}&sz=w1600")
                            counter_label.set_text(f"Foto {cur_idx['val'] + 1} de {len(photos_list)}")

                    # Controles de Navegação (Passador Anterior / Próximo)
                    with ui.row().classes('w-full justify-between items-center p-2 border-t border-white/10'):
                        ui.button('⬅️ Anterior', icon='arrow_back', on_click=lambda: update_lightbox_img(cur_idx['val'] - 1)).props('unelevated color=slate-8 text-color=white bold no-caps').classes('px-4 rounded-xl text-xs')
                        
                        ui.button('Abrir Original no Drive', icon='open_in_new', on_click=lambda: ui.navigate.to(photos_list[cur_idx['val']].get('drive_link') or f"https://drive.google.com/file/d/{photos_list[cur_idx['val']]['drive_file_id']}/view", new_tab=True)).props('flat dense color=cyan size=sm no-caps').classes('text-xs')

                        ui.button('Próxima ➡️', icon='arrow_forward', on_click=lambda: update_lightbox_img(cur_idx['val'] + 1)).props('unelevated color=cyan-8 text-color=white bold no-caps').classes('px-4 rounded-xl text-xs')

                dlg.open()

            # ── SEÇÃO DE ENTREGA (E-MAIL INSTITUCIONAL & WHATSAPP) ────────────
            def render_delivery_section():
                all_photos = []
                seen = set()
                for p in (guest_state['matched_photos'] + guest_state['geral_photos']):
                    fid = p.get('drive_file_id') or p.get('id')
                    if fid and fid not in seen:
                        seen.add(fid)
                        all_photos.append(p)

                with ui.card().classes('w-full max-w-5xl bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-6 gap-3 q-mt-4'):
                    ui.label('📥 RECEBER OU COMPARTILHAR SUAS FOTOS').classes('text-sm sm:text-base font-black text-white tracking-wide')
                    
                    # Botão de Compartilhar no WhatsApp
                    event_url = f"https://sisgab-cgcfn.ddns.net/evento/{event_id}"
                    whatsapp_text = f"📷 Acesse as fotos oficiais do evento {nome_evento}: {event_url}"
                    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_text.replace(' ', '%20')}"

                    with ui.row().classes('w-full items-center gap-3'):
                        ui.button('Compartilhar Galeria no WhatsApp', icon='share', on_click=lambda: (log_portal_analytics(event_id, 'whatsapp', session_id=session_id), ui.navigate.to(whatsapp_url, new_tab=True))).props('unelevated color=green-7 text-color=white bold no-caps').classes('w-full h-12 text-xs sm:text-sm font-bold rounded-xl shadow-md')

                    # Envio por E-mail Institucional com Pré-Cadastro Permanente
                    with ui.column().classes('w-full gap-2.5 q-mt-1'):
                        ui.label('Ou salve seu e-mail para receber fotos automaticamente neste e em futuros eventos:').classes('text-[11px] sm:text-xs text-grey-4')
                        
                        with ui.row().classes('w-full items-center gap-3 flex-wrap'):
                            name_input = ui.input(placeholder='Seu Nome (opcional)', value=guest_state['guest_name']).props('dark outlined dense').classes('w-full sm:w-60')
                            email_input = ui.input(placeholder='seu.email@exemplo.com', value=guest_state['guest_email']).props('dark outlined dense').classes('flex-1 min-w-[240px]')
                            
                            async def send_email_action():
                                email_val = (email_input.value or '').strip()
                                name_val = (name_input.value or '').strip()
                                if not email_val or '@' not in email_val:
                                    ui.notify('❌ Digite um e-mail válido.', color='warning')
                                    return
                                
                                if not all_photos:
                                    ui.notify('ℹ️ Nenhuma foto para enviar no momento.', color='info')
                                    return

                                guest_state['guest_name'] = name_val
                                guest_state['guest_email'] = email_val
                                app.storage.user['portal_guest_name'] = name_val
                                app.storage.user['portal_guest_email'] = email_val

                                # Salva perfil permanente no banco para histórico multi-evento
                                save_guest_face_profile(
                                    event_id, session_id, guest_state['selfie_embeddings'],
                                    nome=name_val, email=email_val
                                )
                                
                                links_html = ''.join(
                                    f'<p style="margin: 6px 0;">📷 <a href="https://drive.google.com/file/d/{p.get("drive_file_id")}/view" style="color: #0284c7; text-decoration: none; font-weight: bold;">Foto {i+1} — Abrir no Drive</a></p>'
                                    for i, p in enumerate(all_photos[:30])
                                )

                                default_template = f"""
                                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; color: #f8fafc; padding: 24px; border-radius: 16px; border: 1px solid #334155;">
                                    <div style="text-align: center; margin-bottom: 20px;">
                                        <h2 style="color: #f59e0b; margin: 0; font-size: 20px; text-transform: uppercase;">MARINHA DO BRASIL</h2>
                                        <p style="color: #38bdf8; margin: 4px 0 0 0; font-size: 11px; font-weight: bold; letter-spacing: 2px;">GABINETE DO COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS</p>
                                    </div>
                                    <hr style="border: 0; height: 1px; background: #334155; margin: 16px 0;" />
                                    <p style="font-size: 15px;">Prezado(a) <strong>{name_val or 'Convidado(a)'}</strong>,</p>
                                    <p style="font-size: 14px; color: #cbd5e1;">Suas fotos do evento <strong>{nome_evento}</strong> já estão prontas para visualização e download:</p>
                                    <div style="background: #1e293b; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                        {links_html}
                                    </div>
                                    <p style="text-align: center; margin-top: 20px;">
                                        <a href="{event_url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Ver Galeria Completa</a>
                                    </p>
                                    <hr style="border: 0; height: 1px; background: #334155; margin: 20px 0;" />
                                    <p style="font-size: 11px; color: #64748b; text-align: center;">Comunicação Social — CGCFN • Este é um e-mail automático institucional.</p>
                                </div>
                                """

                                template_to_use = event.get('email_template') or default_template
                                template_to_use = template_to_use.replace('{EVENTO_NOME}', nome_evento)
                                template_to_use = template_to_use.replace('{EVENTO_DATA}', data_formatada)
                                template_to_use = template_to_use.replace('{EVENTO_LOCAL}', local_evento)
                                template_to_use = template_to_use.replace('{FOTOS_LINKS}', links_html)
                                template_to_use = template_to_use.replace('{TOTAL_FOTOS}', str(len(all_photos)))

                                try:
                                    await asyncio.to_thread(
                                        send_real_email_smtp,
                                        email_val,
                                        f"📷 Suas fotos do evento {nome_evento}",
                                        template_to_use
                                    )
                                    save_guest_delivery(event_id, email_val, ','.join(p.get('drive_file_id') for p in all_photos), len(all_photos))
                                    log_portal_analytics(event_id, 'email', session_id=session_id)
                                    ui.notify('✅ E-mail institucional enviado com sucesso e perfil salvo!', color='positive')
                                except Exception as err_mail:
                                    ui.notify(f"❌ Erro ao enviar e-mail: {err_mail}", color='negative')

                            ui.button('📧 Enviar Fotos por E-mail', on_click=send_email_action).props('unelevated color=cyan text-color=black font-bold icon=send').classes('h-11 px-6 rounded-xl text-xs')

            def download_single(file_id: str):
                log_portal_analytics(event_id, 'download', session_id=session_id)
                ui.navigate.to(f"https://drive.google.com/uc?export=download&id={file_id}", new_tab=True)

            # Auto-executa match se já houver selfies salvas na sessão persistente
            if guest_state['selfie_embeddings']:
                async def auto_match_on_load():
                    await execute_matching()
                    refresh_ui()
                asyncio.create_task(auto_match_on_load())

            # Inicializa a primeira renderização
            refresh_ui()
