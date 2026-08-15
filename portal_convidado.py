import os
import io
import time
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
import numpy as np

from fastapi import Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from nicegui import ui, app

import theme
import drive_service
from database import (
    get_public_event,
    save_guest_face_profile,
    log_portal_analytics,
    save_guest_delivery
)

# ── SINGLETON DO MOTOR INSIGHTFACE (Warmup no Boot) ──────────────────────────
_FACE_APP_SINGLETON = None

def _get_face_app():
    """Retorna o singleton do FaceAnalysis com Warmup automático no boot."""
    global _FACE_APP_SINGLETON
    if _FACE_APP_SINGLETON is not None:
        return _FACE_APP_SINGLETON
    try:
        from sisgab_face_worker import init_face_engine
        _FACE_APP_SINGLETON = init_face_engine()
        if _FACE_APP_SINGLETON:
            print('[PORTAL_IA] ✅ Motor InsightFace carregado via sisgab_face_worker singleton!')
    except Exception:
        pass
    if _FACE_APP_SINGLETON is None:
        try:
            from insightface.app import FaceAnalysis
            _FACE_APP_SINGLETON = FaceAnalysis(
                name='buffalo_l',
                allowed_modules=['detection', 'recognition']
            )
            _FACE_APP_SINGLETON.prepare(ctx_id=-1, det_size=(160, 160))
            print('[PORTAL_IA] ✅ Motor InsightFace (buffalo_l, det=160px) pronto!')
        except Exception as e:
            print(f'[PORTAL_IA] ❌ Falha ao inicializar InsightFace: {e}')
            _FACE_APP_SINGLETON = None
    
    if _FACE_APP_SINGLETON is not None:
        try:
            dummy = np.zeros((480, 480, 3), dtype=np.uint8)
            _FACE_APP_SINGLETON.get(dummy)
            print('[PORTAL_IA] ⚡ Warmup concluído: rede neural pronta para respostas sub-100ms!')
        except Exception as e_w:
            print(f'[PORTAL_IA] Warmup aviso: {e_w}')

    return _FACE_APP_SINGLETON

MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

_EVENT_EMBEDDINGS_CACHE = {}
_EVENT_GERAL_PHOTOS_CACHE = {}

def _get_event_matrix(event_id: str) -> tuple[np.ndarray, list[dict]]:
    """Carrega matriz NxD de embeddings do evento com cache em RAM e arquivo binário em disco (.npz)."""
    now = time.time()
    if event_id in _EVENT_EMBEDDINGS_CACHE:
        cache = _EVENT_EMBEDDINGS_CACHE[event_id]
        if now - cache['timestamp'] < 86400:
            return cache['matrix'], cache['records']

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
            print(f"[PORTAL_IA] ⚡ Matriz ({matrix.shape[0]} faces) carregada do disco em {time.time()-t0:.3f}s!")
            return matrix, records
        except Exception as e_disk:
            print(f"[PORTAL_IA] ⚠️ Erro ao ler cache em disco do evento {event_id}: {e_disk}")

    try:
        from database import get_supabase_client
        sb = get_supabase_client()
        t0 = time.time()
        print(f"[PORTAL_IA] 🔄 Baixando embeddings do Supabase para o evento {event_id}...")

        all_records = []
        offset = 0
        limit = 1000
        while True:
            res = sb.table('face_embeddings') \
                .select('id, photo_id, embedding, processed_photos(drive_file_id, drive_link, photo_filename, storage_path)') \
                .eq('event_id', event_id) \
                .range(offset, offset + limit - 1) \
                .execute()
            rows = res.data or []
            all_records.extend(rows)
            if len(rows) < limit:
                break
            offset += limit

        if not all_records:
            print(f"[PORTAL_IA] ℹ️ Nenhuma face encontrada no Supabase para evento {event_id}")
            empty_mat = np.empty((0, 512), dtype=np.float32)
            _EVENT_EMBEDDINGS_CACHE[event_id] = {'matrix': empty_mat, 'records': [], 'timestamp': now}
            return empty_mat, []

        vectors = []
        cleaned_records = []
        for r in all_records:
            emb = r.get('embedding')
            if not emb:
                continue
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    continue
            vec = np.array(emb, dtype=np.float32)
            if vec.shape[0] != 512:
                continue
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)

            photo_data = r.get('processed_photos') or {}
            cleaned_records.append({
                'face_id': r.get('id'),
                'photo_id': r.get('photo_id'),
                'drive_file_id': photo_data.get('drive_file_id'),
                'drive_link': photo_data.get('drive_link'),
                'photo_filename': photo_data.get('photo_filename'),
                'storage_path': photo_data.get('storage_path')
            })

        if vectors:
            matrix = np.vstack(vectors).astype(np.float32)
        else:
            matrix = np.empty((0, 512), dtype=np.float32)

        try:
            np.savez_compressed(npz_path, matrix=matrix)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_records, f, ensure_ascii=False)
            print(f"[PORTAL_IA] 💾 Cache binário salvo em disco para evento {event_id} ({matrix.shape[0]} faces)")
        except Exception as e_save:
            print(f"[PORTAL_IA] ⚠️ Erro ao salvar cache em disco: {e_save}")

        _EVENT_EMBEDDINGS_CACHE[event_id] = {
            'matrix': matrix,
            'records': cleaned_records,
            'timestamp': now
        }
        print(f"[PORTAL_IA] 🚀 {matrix.shape[0]} faces carregadas do Supabase em {time.time()-t0:.2f}s!")
        return matrix, cleaned_records

    except Exception as e:
        print(f"[PORTAL_IA] ❌ Erro crítico ao carregar embeddings: {e}")
        empty_mat = np.empty((0, 512), dtype=np.float32)
        return empty_mat, []

def _get_geral_photos(folder_id: str) -> list[dict]:
    """Lista fotos da pasta geral do Google Drive com cache em RAM."""
    now = time.time()
    if folder_id in _EVENT_GERAL_PHOTOS_CACHE:
        cache = _EVENT_GERAL_PHOTOS_CACHE[folder_id]
        if now - cache['timestamp'] < 1800:
            return cache['photos']

    try:
        t0 = time.time()
        photos = drive_service.list_files(folder_id)
        if photos:
            photos.sort(key=lambda x: x.get('name', ''), reverse=True)
            _EVENT_GERAL_PHOTOS_CACHE[folder_id] = {
                'photos': photos,
                'timestamp': now
            }
            print(f"[PORTAL_DRIVE] ☁️ {len(photos)} fotos listadas do Drive em {time.time()-t0:.2f}s (cache criado)")
        return photos or []
    except Exception as e:
        print(f"[PORTAL_DRIVE] ⚠️ Erro ao listar fotos da pasta geral {folder_id}: {e}")
        return []

def _extract_selfie_embedding(image_bytes: bytes) -> tuple[bool, str, np.ndarray | None]:
    """Extrai o embedding facial 512D da selfie com alta performance (sub-100ms)."""
    if not image_bytes:
        return False, "❌ Imagem vazia ou inválida.", None

    img_bgr = None
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        pass

    if img_bgr is None:
        try:
            from PIL import Image as PILImage
            pil_img = PILImage.open(io.BytesIO(image_bytes)).convert('RGB')
            img_rgb = np.array(pil_img)
            img_bgr = img_rgb[:, :, ::-1].copy()
        except Exception as e_pil:
            return False, f"❌ Erro ao decodificar imagem: {e_pil}", None

    if img_bgr is None:
        return False, "❌ Não foi possível carregar a imagem enviada.", None

    h, w = img_bgr.shape[:2]
    if max(h, w) > 480:
        scale = 480.0 / max(h, w)
        import cv2
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    try:
        app_face = _get_face_app()
        if app_face is None:
            return False, "❌ Motor de IA não disponível no momento. Tente novamente em instantes.", None

        t0 = time.time()
        faces = app_face.get(img_bgr)
        print(f'[PORTAL_IA] ⚡ Detecção facial turbo em {time.time()-t0:.3f}s → {len(faces)} rosto(s)')

        if not faces:
            return False, "❌ Nenhum rosto detectado. Envie uma foto nítida e bem iluminada de frente.", None

        face = max(faces, key=lambda f: getattr(f, 'det_score', 0))

        if hasattr(face, 'det_score') and face.det_score < 0.35:
            return False, "❌ Rosto pouco nítido ou desfocado. Tente em ambiente mais claro.", None

        return True, "✅ Rosto identificado com sucesso!", face.normed_embedding

    except Exception as e:
        return False, f"❌ Erro ao processar biometria: {e}", None


# ── FASTAPI TURBO MATCH ENDPOINT ─────────────────────────────────────────────
@app.post('/api/portal/match')
async def api_portal_match(
    request: Request,
    event_id: str = Form(...),
    session_id: str = Form(''),
    file: UploadFile = File(...)
):
    """Endpoint REST ultra-rápido para recepção direta da selfie do navegador."""
    try:
        content = await file.read()
        if not content:
            return JSONResponse({'ok': False, 'message': 'Foto vazia.'}, status_code=400)
        
        ok, msg, embedding = await asyncio.to_thread(_extract_selfie_embedding, content)
        if not ok or embedding is None:
            return JSONResponse({'ok': False, 'message': msg})
        
        matrix, records = await asyncio.to_thread(_get_event_matrix, event_id)
        event = get_public_event(event_id) or {}
        threshold_match = float(event.get('threshold_match') or 0.40)
        
        matched_items = []
        if matrix.shape[0] > 0:
            s_vec = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(s_vec)
            if norm > 0:
                s_vec = s_vec / norm
            scores = matrix @ s_vec
            
            seen_fids = set()
            for idx in np.argsort(-scores):
                score = float(scores[idx])
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
        
        # Gravação assíncrona no Supabase em segundo plano
        if session_id:
            asyncio.create_task(asyncio.to_thread(
                save_guest_face_profile,
                event_id, session_id, [embedding.tolist()]
            ))
            asyncio.create_task(asyncio.to_thread(
                log_portal_analytics,
                event_id, 'match', session_id=session_id, metadata={'count': len(matched_items)}
            ))

        matched_fids_str = ','.join([m['drive_file_id'] for m in matched_items])
        response = JSONResponse({
            'ok': True,
            'count': len(matched_items),
            'matched_photos': matched_items,
            'embedding': embedding.tolist()
        })
        response.set_cookie(f'portal_m_{event_id}', matched_fids_str, max_age=86400, path='/')
        response.set_cookie(f'portal_s_{event_id}', '1', max_age=86400, path='/')
        return response
    except Exception as e:
        print(f"[API_PORTAL_MATCH_ERR] {e}")
        return JSONResponse({'ok': False, 'message': str(e)}, status_code=500)


def render_page(event_id: str, request: Request = None):
    """Renderiza a página completa do Portal do Convidado para o evento especificado."""
    theme.apply_global_styles()

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

    # Registra analytics de acesso em background
    session_id = app.storage.user.get('portal_session_id')
    if not session_id:
        session_id = f"guest_{int(time.time()*1000)}"
        app.storage.user['portal_session_id'] = session_id
    
    asyncio.create_task(asyncio.to_thread(log_portal_analytics, event_id, 'acesso', session_id=session_id))

    # Recupera matched FIDs dos cookies HTTP de forma síncrona e instantânea
    matched_photos_initial = []
    has_searched_initial = False
    if request:
        cookie_matches = request.cookies.get(f'portal_m_{event_id}', '')
        cookie_searched = request.cookies.get(f'portal_s_{event_id}', '')
        if cookie_searched:
            has_searched_initial = True
        if cookie_matches:
            target_fids = set(f.strip() for f in cookie_matches.split(',') if f.strip())
            if target_fids:
                _, records = _get_event_matrix(event_id)
                seen = set()
                for r in records:
                    fid = r.get('drive_file_id')
                    if fid and fid in target_fids and fid not in seen:
                        seen.add(fid)
                        matched_photos_initial.append({
                            'drive_file_id': fid,
                            'drive_link': r.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view",
                            'filename': r.get('photo_filename', 'foto.jpg')
                        })

    # Estado local da sessão do convidado
    guest_state = {
        'selfie_embeddings': [],
        'matched_photos': matched_photos_initial,
        'geral_photos': [],
        'selected_fids': set(),
        'has_searched': has_searched_initial,
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

    # Pré-aquece SIMULTANEAMENTE: IA + matriz de embeddings + fotos do Drive
    asyncio.create_task(asyncio.to_thread(_get_face_app))
    asyncio.create_task(asyncio.to_thread(_get_event_matrix, event_id))
    if drive_geral_id:
        asyncio.create_task(asyncio.to_thread(_get_geral_photos, drive_geral_id))

    # Injeta CSS e Script Turbo Client-Side no Header
    ui.add_head_html(f'''
    <style>
        .photo-card-selected {{
            border: 2px solid #00e5ff !important;
            box-shadow: 0 0 15px rgba(0,229,255,0.4) !important;
        }}
        @keyframes turbo-spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .turbo-upload-label {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 52px;
            border-radius: 12px;
            font-weight: 900;
            font-size: 13px;
            letter-spacing: 0.3px;
            cursor: pointer;
            user-select: none;
            transition: transform 0.15s ease, filter 0.15s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            text-align: center;
            padding: 0 12px;
        }}
        .turbo-upload-label:active {{
            transform: scale(0.96);
            filter: brightness(0.9);
        }}
        .turbo-btn-camera {{
            background: #00b4d8;
            color: #000000;
            flex: 1;
        }}
        .turbo-btn-gallery {{
            background: #ffb703;
            color: #000000;
            flex: 1;
        }}
    </style>
    <div id="turbo-loading-overlay" style="display: none; position: fixed; inset: 0; background: rgba(11, 15, 25, 0.94); backdrop-filter: blur(10px); z-index: 999999; flex-direction: column; align-items: center; justify-content: center; gap: 16px;">
        <div style="width: 54px; height: 54px; border: 4px solid rgba(0, 229, 255, 0.2); border-top-color: #00e5ff; border-radius: 50%; animation: turbo-spin 0.8s linear infinite;"></div>
        <div style="font-size: 1.15rem; font-weight: 900; color: #ffffff; letter-spacing: 0.5px; text-shadow: 0 0 12px rgba(0,229,255,0.6);">ANALISANDO SUA FOTO COM IA...</div>
        <div id="turbo-status-text" style="font-size: 0.85rem; color: #94a3b8;">Buscando suas fotos no evento em tempo real</div>
    </div>
    <script>
    window._PORTAL_EVENT_ID = "{event_id}";
    window._PORTAL_SESSION_ID = "{session_id}";

    async function processSelectedFile(file) {{
        if (!file) return;
        
        const overlay = document.getElementById('turbo-loading-overlay');
        const statusText = document.getElementById('turbo-status-text');
        if (overlay) overlay.style.display = 'flex';
        if (statusText) statusText.innerText = 'Otimizando foto no smartphone...';
        
        try {{
            const img = new Image();
            const url = URL.createObjectURL(file);
            
            await new Promise((resolve, reject) => {{
                img.onload = () => resolve();
                img.onerror = () => reject(new Error('Falha ao decodificar a foto selecionada.'));
                img.src = url;
            }});
            URL.revokeObjectURL(url);
            
            const maxDim = 480;
            let w = img.naturalWidth || img.width;
            let h = img.naturalHeight || img.height;
            if (w > maxDim || h > maxDim) {{
                if (w > h) {{
                    h = Math.round((h * maxDim) / w);
                    w = maxDim;
                }} else {{
                    w = Math.round((w * maxDim) / h);
                    h = maxDim;
                }}
            }}
            
            const canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, w, h);
            
            if (statusText) statusText.innerText = 'Consultando inteligência artificial...';
            
            const blob = await new Promise((resolve) => {{
                canvas.toBlob((b) => resolve(b), 'image/jpeg', 0.82);
            }});
            
            if (!blob) {{
                throw new Error('Falha ao converter a imagem no dispositivo.');
            }}
            
            const formData = new FormData();
            formData.append('file', blob, 'selfie.jpg');
            formData.append('event_id', window._PORTAL_EVENT_ID);
            formData.append('session_id', window._PORTAL_SESSION_ID || '');
            
            const response = await fetch('/api/portal/match', {{
                method: 'POST',
                body: formData
            }});
            
            if (!response.ok) {{
                throw new Error('Servidor retornou erro HTTP ' + response.status);
            }}
            
            const data = await response.json();
            
            if (data.ok) {{
                if (statusText) statusText.innerText = 'Fotos encontradas! Carregando...';
                window.location.reload();
            }} else {{
                if (overlay) overlay.style.display = 'none';
                alert(data.message || 'Nenhum rosto identificado com clareza. Envie outra foto bem iluminada de frente.');
            }}
        }} catch (err) {{
            console.error('[TURBO_UPLOAD_ERR]', err);
            if (overlay) overlay.style.display = 'none';
            alert('Erro ao processar foto: ' + (err.message || err));
        }}
    }}

    function setupUploadInputs() {{
        const camInput = document.getElementById('portal-native-camera');
        const galInput = document.getElementById('portal-native-gallery');
        
        if (camInput) {{
            camInput.onchange = function() {{
                if (this.files && this.files[0]) {{
                    const f = this.files[0];
                    this.value = '';
                    processSelectedFile(f);
                }}
            }};
        }}
        if (galInput) {{
            galInput.onchange = function() {{
                if (this.files && this.files[0]) {{
                    const f = this.files[0];
                    this.value = '';
                    processSelectedFile(f);
                }}
            }};
        }}
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', setupUploadInputs);
    }} else {{
        setupUploadInputs();
    }}
    setTimeout(setupUploadInputs, 300);
    setTimeout(setupUploadInputs, 1000);
    </script>
    ''')

    # Container principal
    with ui.column().classes('w-full min-h-screen items-center justify-start p-2 sm:p-4 bg-slate-950 text-white').style('font-family: "Outfit", sans-serif;'):

        # ── INPUTS NATIVOS DE UPLOAD OFF-SCREEN ──
        ui.html('''
        <input type="file" id="portal-native-camera" accept="image/*" capture="user" style="position: absolute; left: -9999px; opacity: 0; width: 1px; height: 1px;">
        <input type="file" id="portal-native-gallery" accept="image/*" style="position: absolute; left: -9999px; opacity: 0; width: 1px; height: 1px;">
        ''')

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

        # ── 1. DOWNLOAD INDIVIDUAL ────────────────────────────────────────────
        def download_single(file_id: str):
            dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            ui.run_javascript(f'window.open("{dl_url}", "_blank")')
            ui.notify('Iniciando download da foto em alta resolução...', color='info', timeout=3000)

        # ── 2. LIGHTBOX PROFISSIONAL FULLSCREEN ───────────────────────────────
        def open_full_lightbox(initial_index: int, photos_list: list[dict]):
            if not photos_list:
                return

            current_idx = {'value': initial_index}

            with ui.dialog().classes('w-full h-full max-w-none max-h-none m-0 p-0').props('maximized transition-show=fade transition-hide=fade') as dialog:
                with ui.card().classes('w-full h-full bg-black/95 text-white p-0 m-0 flex flex-col justify-between items-center relative overflow-hidden select-none'):
                    with ui.row().classes('w-full items-center justify-between p-3 sm:p-4 bg-gradient-to-b from-black/80 to-transparent z-10'):
                        counter_label = ui.label(f"{current_idx['value'] + 1} / {len(photos_list)}").classes('text-xs sm:text-sm font-mono text-grey-4')
                        with ui.row().classes('items-center gap-2'):
                            def dl_current():
                                photo = photos_list[current_idx['value']]
                                fid = photo.get('drive_file_id') or photo.get('id')
                                if fid:
                                    download_single(fid)
                            ui.button(icon='download', on_click=dl_current).props('round flat color=cyan size=sm').classes('bg-slate-800/80')
                            ui.button(icon='close', on_click=dialog.close).props('round flat color=white size=sm').classes('bg-slate-800/80')

                    img_container = ui.column().classes('w-full flex-1 items-center justify-center p-2 relative overflow-hidden')

                    def update_lightbox_image():
                        img_container.clear()
                        photo = photos_list[current_idx['value']]
                        fid = photo.get('drive_file_id') or photo.get('id')
                        img_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w1600"
                        with img_container:
                            ui.image(img_url).classes('max-h-[82vh] max-w-full object-contain rounded-lg shadow-2xl')
                        counter_label.set_text(f"{current_idx['value'] + 1} / {len(photos_list)}")

                    update_lightbox_image()

                    def prev_photo():
                        if current_idx['value'] > 0:
                            current_idx['value'] -= 1
                            update_lightbox_image()

                    def next_photo():
                        if current_idx['value'] < len(photos_list) - 1:
                            current_idx['value'] += 1
                            update_lightbox_image()

                    if len(photos_list) > 1:
                        ui.button(icon='chevron_left', on_click=prev_photo).props('round unelevated color=slate-900/80 text-color=white size=md').classes('absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 z-10 border border-white/20')
                        ui.button(icon='chevron_right', on_click=next_photo).props('round unelevated color=slate-900/80 text-color=white size=md').classes('absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 z-10 border border-white/20')

            dialog.open()

        # ── 3. RENDERIZADOR DE GRADE DE FOTOS (Proporção Panorâmica 16:10) ─────
        def render_photo_grid(photos_list: list[dict], is_personal: bool = False):
            if not photos_list:
                return

            with ui.element('div').classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 sm:gap-3'):
                for idx, photo in enumerate(photos_list):
                    fid = photo.get('drive_file_id') or photo.get('id')
                    if not fid:
                        continue
                    thumb_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w800"
                    is_selected = fid in guest_state['selected_fids']

                    card_border = 'photo-card-selected' if is_selected else 'border border-slate-800'
                    with ui.card().classes(f"w-full bg-slate-900 rounded-xl overflow-hidden shadow-md {card_border} p-0 relative transition-all duration-200"):
                        with ui.element('div').classes('w-full relative aspect-[16/10] overflow-hidden bg-slate-950 cursor-pointer').on('click', lambda _, i=idx, pl=photos_list: open_full_lightbox(i, pl)):
                            ui.image(thumb_url).classes('w-full h-full object-cover')

                        with ui.row().classes('w-full items-center justify-between px-2 py-1.5 bg-slate-900/90 gap-1'):
                            def toggle_select(_, f=fid):
                                if f in guest_state['selected_fids']:
                                    guest_state['selected_fids'].remove(f)
                                else:
                                    guest_state['selected_fids'].add(f)
                                refresh_ui()

                            ui.button(
                                icon='check_circle' if is_selected else 'radio_button_unchecked',
                                on_click=lambda _, f=fid: toggle_select(None, f)
                            ).props(f"flat dense round size=sm {'color=cyan-4' if is_selected else 'color=grey-5'}").classes('text-xs')

                            ui.button(
                                icon='download',
                                on_click=lambda _, f=fid: download_single(f)
                            ).props('flat dense round color=grey-4 size=sm').classes('text-xs')

        # ── 4. BARRA DE FERRAMENTAS DE SELEÇÃO ─────────────────────────────────
        def render_selection_toolbar():
            all_visible = guest_state['matched_photos'] if guest_state['matched_photos'] else guest_state['geral_photos']
            if not all_visible:
                return

            selected_count = len(guest_state['selected_fids'])

            with ui.card().classes('w-full bg-slate-900/95 border border-slate-700/60 rounded-xl p-2 sm:p-3 shadow-lg'):
                with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('photo_library', color='cyan-4', size='1.3rem')
                        ui.label(f"{len(all_visible)} foto(s) disponíveis").classes('text-xs sm:text-sm font-bold text-white')
                        if selected_count > 0:
                            ui.badge(f"{selected_count} selecionada(s)", color='cyan-9').classes('text-xs font-bold px-2 py-0.5 rounded-md')

                    with ui.row().classes('items-center gap-1.5 sm:gap-2 flex-wrap'):
                        start_idx = (guest_state['page'] - 1) * guest_state['per_page']
                        end_idx = start_idx + guest_state['per_page']
                        page_all = all_visible[start_idx:end_idx]

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
                            fids_to_dl = list(guest_state['selected_fids']) if guest_state['selected_fids'] else [p.get('drive_file_id') or p.get('id') for p in all_visible]
                            if not fids_to_dl:
                                ui.notify('Nenhuma foto selecionada.', color='warning')
                                return

                            n_zip = ui.notify(f"📦 Compactando {len(fids_to_dl)} foto(s) em arquivo ZIP...", color='info', spinner=True, timeout=0)
                            try:
                                import zipfile
                                def build_zip():
                                    buf = io.BytesIO()
                                    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                                        for idx, fid in enumerate(fids_to_dl):
                                            img_b = drive_service.download_file(fid)
                                            if img_b:
                                                zf.writestr(f"foto_{idx+1:03d}_{fid}.jpg", img_b)
                                    buf.seek(0)
                                    return buf.read()

                                zip_bytes = await asyncio.to_thread(build_zip)
                                n_zip.dismiss()

                                if not zip_bytes:
                                    ui.notify('Falha ao baixar fotos para o ZIP.', color='negative')
                                    return

                                b64_zip = base64.b64encode(zip_bytes).decode('ascii')
                                filename = f"fotos_{event.get('nome', 'evento')[:15]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                                js_dl = f'''
                                    var a = document.createElement("a");
                                    a.href = "data:application/zip;base64,{b64_zip}";
                                    a.download = "{filename}";
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                '''
                                ui.run_javascript(js_dl)
                                ui.notify(f"✅ ZIP com {len(fids_to_dl)} foto(s) baixado com sucesso!", color='positive')
                            except Exception as e_zip:
                                n_zip.dismiss()
                                ui.notify(f"Erro ao gerar ZIP: {e_zip}", color='negative')

                        ui.button('Baixar ZIP', icon='archive', on_click=download_selected_zip).props('unelevated color=cyan-7 text-color=black bold dense size=sm no-caps').classes('text-[11px] rounded-lg px-2.5 shadow')

        # ── 5. GALERIA OFICIAL DO EVENTO COM PAGINAÇÃO NO RODAPÉ ──────────────
        def render_official_gallery(folder_id: str):
            if not folder_id:
                with ui.card().classes('w-full bg-slate-900/60 p-4 text-center rounded-xl'):
                    ui.label('Fotos da galeria oficial serão disponibilizadas em breve.').classes('text-xs text-grey-5')
                return

            photos = _get_geral_photos(folder_id)
            guest_state['geral_photos'] = photos

            if not photos:
                with ui.card().classes('w-full bg-slate-900/60 p-4 text-center rounded-xl'):
                    ui.label('Nenhuma foto encontrada na galeria oficial deste evento.').classes('text-xs text-grey-5')
                return

            total_photos = len(photos)
            per_page = guest_state['per_page']
            total_pages = max(1, (total_photos + per_page - 1) // per_page)
            current_page = max(1, min(guest_state['page'], total_pages))

            start_idx = (current_page - 1) * per_page
            end_idx = min(start_idx + per_page, total_photos)
            current_batch = photos[start_idx:end_idx]

            render_photo_grid(current_batch, is_personal=False)

            if total_pages > 1:
                with ui.card().classes('w-full bg-slate-900/90 border border-slate-800 rounded-xl p-2.5 mt-3 shadow-md'):
                    with ui.row().classes('w-full items-center justify-center gap-2 sm:gap-4 flex-nowrap'):
                        def go_first():
                            guest_state['page'] = 1
                            refresh_ui()

                        def go_prev():
                            if guest_state['page'] > 1:
                                guest_state['page'] -= 1
                                refresh_ui()

                        def go_next():
                            if guest_state['page'] < total_pages:
                                guest_state['page'] += 1
                                refresh_ui()

                        def go_last():
                            guest_state['page'] = total_pages
                            refresh_ui()

                        ui.button(icon='first_page', on_click=go_first).props('flat dense round color=grey-4 size=sm').set_visibility(current_page > 1)
                        ui.button(icon='chevron_left', on_click=go_prev).props('flat dense round color=cyan-4 size=md').set_visibility(current_page > 1)

                        ui.label(f"Página {current_page} de {total_pages}").classes('text-xs sm:text-sm font-bold text-white font-mono px-2')

                        ui.button(icon='chevron_right', on_click=go_next).props('flat dense round color=cyan-4 size=md').set_visibility(current_page < total_pages)
                        ui.button(icon='last_page', on_click=go_last).props('flat dense round color=grey-4 size=sm').set_visibility(current_page < total_pages)

        # ── 6. SEÇÃO DE ENTREGA ───────────────────────────────────────────────
        def render_delivery_section():
            with ui.column().classes('w-full gap-2.5 q-mt-4'):
                with ui.card().classes('w-full bg-slate-900/90 border border-cyan-500/20 rounded-2xl p-4 sm:p-5 gap-3 shadow-xl'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('forward_to_inbox', size='1.5rem', color='cyan-4')
                        ui.label('RECEBER FOTOS EM ALTA RESOLUÇÃO').classes('text-sm sm:text-base font-black text-cyan-3 tracking-wide')

                    ui.label('Informe seu e-mail institucional ou WhatsApp para receber o pacote completo com todas as suas fotos em resolução máxima:').classes('text-xs text-grey-4')

                    with ui.row().classes('w-full gap-2 sm:gap-3 flex-wrap'):
                        input_nome = ui.input(placeholder='Seu nome completo', value=guest_state['guest_name']).props('outlined dense dark').classes('flex-1 min-w-[200px] text-xs bg-slate-950/60 rounded-xl')
                        input_email = ui.input(placeholder='Seu e-mail (@marinha.mil.br ou pessoal)', value=guest_state['guest_email']).props('outlined dense dark').classes('flex-1 min-w-[220px] text-xs bg-slate-950/60 rounded-xl')

                    async def submit_delivery():
                        nome = input_nome.value.strip()
                        email = input_email.value.strip()
                        if not email:
                            ui.notify('Por favor, informe seu e-mail.', color='warning')
                            return

                        guest_state['guest_name'] = nome
                        guest_state['guest_email'] = email
                        app.storage.user['portal_guest_name'] = nome
                        app.storage.user['portal_guest_email'] = email

                        fids = list(guest_state['selected_fids']) if guest_state['selected_fids'] else [p.get('drive_file_id') or p.get('id') for p in (guest_state['matched_photos'] or guest_state['geral_photos'])]
                        
                        ok = await asyncio.to_thread(
                            save_guest_delivery,
                            event_id=event_id,
                            email=email,
                            photo_ids=','.join(fids),
                            count=len(fids)
                        )
                        if ok:
                            ui.notify(f"✅ Solicitação registrada com sucesso! Enviaremos as fotos para {email}.", color='positive', timeout=6000)
                        else:
                            ui.notify('Erro ao registrar solicitação. Tente novamente.', color='negative')

                    with ui.row().classes('w-full justify-end mt-1'):
                        ui.button('Solicitar Envio', icon='send', on_click=submit_delivery).props('unelevated color=cyan-7 text-color=black bold no-caps').classes('rounded-xl text-xs px-4 py-2 font-bold shadow-md')

        # ── 7. MONTAGEM DO CONTEÚDO PRINCIPAL ─────────────────────────────────
        def render_portal_content():
            pin_req = str(event.get('pin_acesso') or '').strip()
            is_authenticated = app.storage.user.get(f'portal_auth_{event_id}', False)

            if pin_req and not is_authenticated:
                with ui.card().classes('w-full bg-slate-900/95 border border-amber-500/40 rounded-2xl p-5 sm:p-7 text-center items-center gap-3 shadow-2xl'):
                    ui.icon('lock', size='3rem', color='amber-4')
                    ui.label('EVENTO RESTRITO — INSIRA O PIN').classes('cyber-title text-base sm:text-xl font-black text-amber-4')
                    ui.label('Este evento possui controle de acesso. Digite o PIN de 4 dígitos ou valide sua presença com uma selfie:').classes('text-xs text-grey-4 max-w-md')

                    with ui.row().classes('items-center justify-center gap-2 q-my-sm'):
                        pin_input = ui.input(placeholder='PIN').props('outlined dense dark type=password maxlength=6').classes('w-32 text-center text-lg font-mono bg-slate-950 rounded-xl')
                        def check_pin():
                            if pin_input.value.strip() == pin_req:
                                app.storage.user[f'portal_auth_{event_id}'] = True
                                ui.notify('✅ Acesso liberado!', color='positive')
                                refresh_ui()
                            else:
                                ui.notify('❌ PIN incorreto.', color='negative')
                        ui.button('Entrar', on_click=check_pin).props('unelevated color=amber-7 text-color=black bold').classes('rounded-xl text-xs h-10 px-4')

                    ui.separator().classes('w-full opacity-20 q-my-sm')

                    ui.html('''
                    <div style="display: flex; gap: 10px; width: 100%; margin-top: 6px;">
                        <label for="portal-native-camera" class="turbo-upload-label turbo-btn-camera">📸 VALIDAR COM CÂMERA</label>
                        <label for="portal-native-gallery" class="turbo-upload-label turbo-btn-gallery">📁 ESCOLHER DA GALERIA</label>
                    </div>
                    ''')

                return

            # 1. SEÇÃO DE CAPTURA BIOMÉTRICA / SELFIE (Card Compacto Direto com Labels Nativas)
            with ui.card().classes('w-full bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-3 sm:p-5 shadow-xl text-center gap-1.5'):
                with ui.row().classes('w-full items-center justify-center gap-2'):
                    ui.icon('face_retouching_natural', size='1.5rem', color='cyan-4')
                    ui.label('ENCONTRE SUAS FOTOS DO EVENTO').classes('text-sm sm:text-base font-black text-cyan-3 tracking-wide')

                num_matches = len(guest_state['matched_photos'])
                ui.label('Tire uma selfie ou escolha uma foto sua para a inteligência artificial localizar todas as suas fotos no evento:').classes('text-xs text-grey-4 max-w-xl mx-auto')

                btn_cam_txt = '📸 TIRAR SELFIE (CÂMERA)' if num_matches == 0 else '📸 OUTRA SELFIE'
                btn_gal_txt = '📁 ESCOLHER FOTO' if num_matches == 0 else '📁 OUTRA FOTO'

                ui.html(f'''
                <div style="display: flex; gap: 10px; width: 100%; margin-top: 6px;">
                    <label for="portal-native-camera" class="turbo-upload-label turbo-btn-camera">{btn_cam_txt}</label>
                    <label for="portal-native-gallery" class="turbo-upload-label turbo-btn-gallery">{btn_gal_txt}</label>
                </div>
                ''')

                if guest_state['has_searched']:
                    def reset_selfies():
                        guest_state['selfie_embeddings'] = []
                        guest_state['matched_photos'] = []
                        guest_state['has_searched'] = False
                        ui.run_javascript(f"document.cookie = 'portal_m_{event_id}=; path=/; max-age=0'; document.cookie = 'portal_s_{event_id}=; path=/; max-age=0'; window.location.reload();")
                    with ui.row().classes('items-center justify-between w-full pt-1'):
                        ui.label('🔒 Foto processada em memória e descartada.').classes('text-[10px] text-grey-5')
                        ui.button('Recomeçar busca', icon='refresh', on_click=reset_selfies).props('flat dense color=grey-4 size=xs').classes('text-[10px]')
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

        # ── 8. REFRESH UI (CONTAINER DINÂMICO) ────────────────────────────────
        def refresh_ui():
            content_container.clear()
            with content_container:
                render_portal_content()

        # ── 9. INICIALIZA A PRIMEIRA RENDERIZAÇÃO NA RAIZ DA PÁGINA ───────────
        refresh_ui()
