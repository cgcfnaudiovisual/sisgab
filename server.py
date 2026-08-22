import os
import io
import time
import json
import re
import asyncio
import threading
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, Form, Response
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REACT_DIST_DIR = os.path.join(BASE_DIR, "frontend-react", "dist")
ASSETS_DIR = os.path.join(REACT_DIST_DIR, "assets")

# ── Endpoints de Reconhecimento Facial Sob Demanda ──
try:
    from portal_convidado import (
        _extract_selfie_embedding,
        _get_event_matrix,
        _get_selfie_app,
        _get_geral_photos,
        _check_ai_idle_and_hibernate,
        _touch_ai_activity
    )
except Exception as e_import:
    print(f"[WARN] Erro ao importar portal_convidado: {e_import}")
    _extract_selfie_embedding = None
    _get_event_matrix = None
    _get_selfie_app = None
    _get_geral_photos = None
    _check_ai_idle_and_hibernate = None
    _touch_ai_activity = None

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # ── STARTUP ──
    print("⚓ [SisGAB 2.0] Inicializando serviços de produção...", flush=True)

    try:
        from alerts_manager import AlertsManager
        from notifications_manager import start_19h_briefing_scheduler, start_15h_demand_scheduler
        AlertsManager.start_alerts_scheduler()
        start_19h_briefing_scheduler()
        start_15h_demand_scheduler()
        print("⏰ [SisGAB 2.0] Agendadores de notificações (15h / 19h / Alertas) ativos.", flush=True)
    except Exception as e:
        print(f"[SisGAB] ⚠️ Erro ao iniciar agendadores: {e}", flush=True)

    def _start_bot_in_thread():
        try:
            import telegram_bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_bot.init_bot())
            loop.run_forever()
        except Exception as e:
            print(f"[SisGAB BOT THREAD ERR] {e}", flush=True)

    t_bot = threading.Thread(target=_start_bot_in_thread, daemon=True, name="SisGAB-TelegramBot")
    t_bot.start()

    # ── Monitor de Inatividade e Auto-Sleep (Libera RAM após 15 min sem uso) ──
    def _run_idle_monitor():
        while True:
            try:
                time.sleep(60)
                if _check_ai_idle_and_hibernate:
                    _check_ai_idle_and_hibernate()
            except Exception as e_idle:
                print(f"[SisGAB IDLE MONITOR ERR] {e_idle}", flush=True)

    t_idle = threading.Thread(target=_run_idle_monitor, daemon=True, name="SisGAB-AIIdleMonitor")
    t_idle.start()
    print("💤 [SisGAB 2.0] Monitor de Auto-Sleep facial ativo (libera RAM após 15 min de inatividade).", flush=True)

    yield

    # ── SHUTDOWN ──
    print("⚓ [SisGAB 2.0] Encerrando servidor.", flush=True)

app = FastAPI(
    title="SisGAB 2.0 - Servidor de Produção & Motor Híbrido",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta assets do React (JS/CSS/Imagens)
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="react-assets")

# Monta pasta de dados estáticos
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

@app.get("/health")
@app.get("/ping")
async def health_check():
    return {
        "status": "healthy",
        "system": "SisGAB 2.0 (React TS + Python On-Demand Engine)",
        "version": "2.0.0",
        "react_ready": os.path.exists(os.path.join(REACT_DIST_DIR, "index.html"))
    }

def get_event_drive_photos(event_id: str):
    """
    Busca automaticamente as fotos do evento a partir do registro da pauta no banco de dados e do Google Drive.
    """
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if not db:
            return None
        
        dem = None
        try:
            res = db.table('demandas_comunicacao').select('*').eq('id', int(event_id)).execute()
            if res.data:
                dem = res.data[0]
        except Exception:
            try:
                res = db.table('demandas_comunicacao').select('*').eq('id', str(event_id)).execute()
                if res.data:
                    dem = res.data[0]
            except Exception:
                pass
        
        if not dem:
            return None
            
        from database import get_demanda_drive_url
        drive_url = get_demanda_drive_url(dem) or dem.get('drive_url') or dem.get('drive_link') or dem.get('arquivo_url') or ''
        drive_folder_id = dem.get('drive_folder_id') or ''
        
        # Extrai folder_id com suporte a múltiplos formatos
        if not drive_folder_id and drive_url:
            m = re.search(r'folders/([a-zA-Z0-9_-]+)', drive_url)
            if m:
                drive_folder_id = m.group(1)
            elif '/d/' in drive_url:
                m2 = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
                if m2:
                    drive_folder_id = m2.group(1)
            elif 'id=' in drive_url:
                m3 = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', drive_url)
                if m3:
                    drive_folder_id = m3.group(1)
            elif len(drive_url.strip()) in (28, 33, 34, 44) and '/' not in drive_url:
                drive_folder_id = drive_url.strip()
                
        # Se ainda não achou, busca nas observações/autoridades
        if not drive_folder_id:
            raw_text = f"{dem.get('autoridades', '')} {dem.get('produto_especifico', '')} {dem.get('observacoes', '')}"
            m_raw = re.search(r'https:\/\/drive\.google\.com\/[^\s\]]+', raw_text)
            if m_raw:
                drive_url = m_raw.group(0)
                m_fid = re.search(r'folders/([a-zA-Z0-9_-]+)', drive_url) or re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
                if m_fid:
                    drive_folder_id = m_fid.group(1)
                
        # Se for o evento 50 (Veteranos) e tiver o json local, carrega rápido
        local_json_path = os.path.join(REACT_DIST_DIR, f"event_{event_id}_photos.json")
        if not drive_folder_id and str(event_id) == "50" and os.path.exists(local_json_path):
            with open(local_json_path, 'r', encoding='utf-8') as f:
                return {
                    'ok': True,
                    'event': {
                        'id': dem.get('id'),
                        'title': dem.get('titulo_evento'),
                        'date': dem.get('data_evento'),
                        'location': dem.get('local_evento'),
                        'drive_url': drive_url
                    },
                    'photos': json.load(f)
                }

        if not drive_folder_id:
            return {
                'ok': False,
                'message': 'Evento não possui pasta vinculada do Google Drive.',
                'event': {
                    'id': dem.get('id'),
                    'title': dem.get('titulo_evento'),
                    'date': dem.get('data_evento'),
                    'location': dem.get('local_evento'),
                    'drive_url': drive_url
                },
                'photos': []
            }
            
        import drive_service
        service = drive_service.get_drive_service()
        
        selecao_folder_id = None
        geral_folder_id = None
        selecao_photos = []
        geral_photos = []
        seen_ids = set()

        # 1. Busca subpastas SELEÇÃO / GERAL
        if service:
            try:
                q_sub = f"'{drive_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                res_sub = service.files().list(q=q_sub, fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                subfolders = res_sub.get('files', [])
                for sf in subfolders:
                    s_name = sf.get('name', '').upper()
                    if any(k in s_name for k in ['SELECAO', 'SELE', 'DESTAQUE', 'TOP', 'MELHORE', 'PRINCIPAI', 'ESCOLHIDA', 'FAVORITA']):
                        selecao_folder_id = sf.get('id')
                    elif any(k in s_name for k in ['GERAL', 'BRUTA', 'COBERTURA', 'TODA']):
                        geral_folder_id = sf.get('id')
            except Exception as e_sf:
                print(f"[DRIVE_CURATION] Erro ao listar subpastas: {e_sf}")

        # 2. Carrega fotos da pasta SELEÇÃO (Prioridade Máxima)
        if selecao_folder_id:
            s_items = drive_service.list_files(selecao_folder_id, mime_filter='image/', page_size=5000) or []
            for p in s_items:
                fid = p.get('id') or p.get('drive_file_id')
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    fname = p.get('name') or p.get('filename') or f"{fid}.jpg"
                    selecao_photos.append({
                        'id': fid,
                        'filename': fname,
                        'drive_file_id': fid,
                        'url': p.get('webViewLink') or f"https://drive.google.com/uc?export=view&id={fid}",
                        'thumbnail_url': p.get('thumbnailLink') or f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                        'drive_thumb': f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                        'drive_link': f"https://drive.google.com/file/d/{fid}/view",
                        'is_destaque_top20': True,
                        'is_selecao': True,
                        'categoria': 'selecao',
                        'origem_pasta': 'SELEÇÃO'
                    })

        # 3. Carrega fotos da pasta GERAL (se existir)
        if geral_folder_id:
            g_items = drive_service.list_files(geral_folder_id, mime_filter='image/', page_size=5000) or []
            for p in g_items:
                fid = p.get('id') or p.get('drive_file_id')
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    fname = p.get('name') or p.get('filename') or f"{fid}.jpg"
                    geral_photos.append({
                        'id': fid,
                        'filename': fname,
                        'drive_file_id': fid,
                        'url': p.get('webViewLink') or f"https://drive.google.com/uc?export=view&id={fid}",
                        'thumbnail_url': p.get('thumbnailLink') or f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                        'drive_thumb': f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                        'drive_link': f"https://drive.google.com/file/d/{fid}/view",
                        'is_destaque_top20': False,
                        'is_selecao': False,
                        'categoria': 'geral',
                        'origem_pasta': 'GERAL'
                    })

        # 4. Carrega fotos da raiz (excluindo subpastas)
        root_items = drive_service.list_files(drive_folder_id, mime_filter='image/', page_size=5000) or []
        for p in root_items:
            if p.get('mimeType') == 'application/vnd.google-apps.folder':
                continue
            fid = p.get('id') or p.get('drive_file_id')
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                fname = p.get('name') or p.get('filename') or f"{fid}.jpg"
                geral_photos.append({
                    'id': fid,
                    'filename': fname,
                    'drive_file_id': fid,
                    'url': p.get('webViewLink') or f"https://drive.google.com/uc?export=view&id={fid}",
                    'thumbnail_url': p.get('thumbnailLink') or f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                    'drive_thumb': f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                    'drive_link': f"https://drive.google.com/file/d/{fid}/view",
                    'is_destaque_top20': False,
                    'is_selecao': False,
                    'categoria': 'geral',
                    'origem_pasta': 'RAIZ'
                })

        all_formatted_photos = selecao_photos + geral_photos

        return {
            'ok': True,
            'event': {
                'id': dem.get('id'),
                'title': dem.get('titulo_evento'),
                'date': dem.get('data_evento'),
                'location': dem.get('local_evento'),
                'drive_url': drive_url
            },
            'stats': {
                'total': len(all_formatted_photos),
                'selecao': len(selecao_photos),
                'geral': len(geral_photos),
                'has_selecao': len(selecao_photos) > 0,
                'selecao_folder_id': selecao_folder_id,
                'geral_folder_id': geral_folder_id,
            },
            'photos': all_formatted_photos
        }
    except Exception as e:
        print(f"[GET_EVENT_DRIVE_PHOTOS ERR] {e}")
        return {'ok': False, 'message': str(e), 'photos': []}

THUMBS_CACHE_DIR = os.path.join(BASE_DIR, "data", "thumbs_cache")
os.makedirs(THUMBS_CACHE_DIR, exist_ok=True)

def _get_or_create_thumb_cache(file_id: str, direct_url: str = None) -> str:
    """
    Retorna o caminho da miniatura em cache local.
    Se não existir, baixa do Google Drive/Thumbnail, comprime para JPEG 600px (~100-150KB) e salva em disco.
    """
    target_path = os.path.join(THUMBS_CACHE_DIR, f"{file_id}.jpg")
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        return target_path

    try:
        from PIL import Image
        import urllib.request
        
        img_bytes = None
        # 1. Tenta baixar direto da CDN do Google Thumbnail (muito mais rápido)
        urls_to_try = [
            f"https://drive.google.com/thumbnail?id={file_id}&sz=w800",
            f"https://lh3.googleusercontent.com/d/{file_id}=w800",
        ]
        if direct_url and 'http' in direct_url:
            urls_to_try.insert(0, direct_url)
            
        for u in urls_to_try:
            try:
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    if resp.status == 200:
                        b = resp.read()
                        if len(b) > 1500:
                            img_bytes = b
                            break
            except Exception:
                pass
                
        # 2. Fallback para drive_service
        if not img_bytes:
            import drive_service
            img_bytes = drive_service.download_file(file_id)
            
        if not img_bytes:
            return None
            
        # 3. Redimensiona e comprime para miniatura HD nítida (1400px para preview cristalino e ~250KB)
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
            
        max_dim = 1400
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
        img.save(target_path, format="JPEG", quality=88, optimize=True)
        return target_path
    except Exception as e:
        print(f"[THUMB_CACHE_ERR] {file_id}: {e}")
        return None

@app.get("/api/cache/thumb/{file_id}")
async def api_cache_thumb(file_id: str):
    """Serve a miniatura HD do cache local do servidor."""
    thumb_path = await asyncio.to_thread(_get_or_create_thumb_cache, file_id)
    if thumb_path and os.path.exists(thumb_path):
        return FileResponse(
            thumb_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=864000"} # Cache de 10 dias no navegador
        )
    return JSONResponse({'error': 'Thumbnail unavailable'}, status_code=404)

@app.get("/api/proxy/image")
async def api_proxy_image(drive_id: str = None, url: str = None):
    """Proxy resiliente de imagens para contornar restrições de CORS e alimentar o Gemini Vision AI."""
    try:
        fid = str(drive_id).strip() if drive_id else None
        
        # 1. Se tiver drive_id, usa o cache local HD ou baixa via drive_service
        if fid:
            thumb_path = await asyncio.to_thread(_get_or_create_thumb_cache, fid)
            if thumb_path and os.path.exists(thumb_path):
                return FileResponse(thumb_path, media_type="image/jpeg")

        # 2. Se for uma URL externa
        target_url = url
        if not target_url and fid:
            target_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w1400"

        if not target_url:
            return JSONResponse({'error': 'drive_id ou url é obrigatório'}, status_code=400)

        import urllib.request
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read()
            m_type = resp.headers.get_content_type() or 'image/jpeg'
            return Response(content=content, media_type=m_type)

    except Exception as e:
        print(f"[PROXY_IMAGE_ERR] {e}")
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/api/portal/photos")
async def api_portal_photos(event_id: str):
    """Retorna dinamicamente os dados do evento e todas as fotos da sua pasta vinculada no Google Drive com suporte a miniaturas cacheadas."""
    res = await asyncio.to_thread(get_event_drive_photos, str(event_id))
    if not res:
        return JSONResponse({'ok': False, 'message': 'Evento não encontrado.', 'photos': []}, status_code=404)
    return JSONResponse(res)

@app.api_route("/api/portal/warmup", methods=["GET", "POST"])
async def api_portal_warmup(event_id: str = "50"):
    """
    Pré-aquecimento Just-in-Time (JIT) assíncrono disparado ao entrar na galeria.
    Carrega o modelo buffalo_m e a matriz do evento na RAM em background de forma controlada.
    """
    def _do_warmup():
        try:
            if _touch_ai_activity:
                _touch_ai_activity()
            if _get_selfie_app:
                _get_selfie_app()
            if _get_event_matrix and event_id:
                _get_event_matrix(str(event_id))
            return True
        except Exception as e:
            print(f"[WARMUP_ERR] {e}")
            return False

    asyncio.create_task(asyncio.to_thread(_do_warmup))
    return JSONResponse({'ok': True, 'message': 'Aquecimento Just-in-Time ativo.'})

@app.post("/api/portal/match")
async def api_portal_match(
    event_id: str = Form(...),
    session_id: str = Form(''),
    file: UploadFile = File(...)
):
    """Endpoint REST ultra-rápido para recepção direta da selfie e cruzamento com a matriz de embeddings do evento."""
    try:
        content = await file.read()
        if not content:
            return JSONResponse({'ok': False, 'message': 'Foto vazia.'}, status_code=400)
        
        if _extract_selfie_embedding is None:
            return JSONResponse({'ok': False, 'message': 'Motor de IA não inicializado no servidor.'}, status_code=500)

        ok, msg, embedding = await asyncio.to_thread(_extract_selfie_embedding, content)
        if not ok or embedding is None:
            return JSONResponse({'ok': False, 'message': msg})
        
        matrix, records = await asyncio.to_thread(_get_event_matrix, str(event_id))
        threshold_match = 0.38
        
        matched_items = []
        if matrix is not None and len(matrix.shape) == 2 and matrix.shape[0] > 0:
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
                if idx < len(records):
                    rec = records[idx]
                    fid = rec.get('drive_file_id')
                    if fid and fid not in seen_fids:
                        seen_fids.add(fid)
                        matched_items.append({
                            'drive_file_id': fid,
                            'drive_link': rec.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view",
                            'filename': rec.get('photo_filename', 'foto.jpg'),
                            'similarity': round(score, 3)
                        })
        
        return JSONResponse({
            'ok': True,
            'count': len(matched_items),
            'matched_photos': matched_items
        })
    except Exception as e:
        print(f"[API_PORTAL_MATCH_ERR] {e}")
        return JSONResponse({'ok': False, 'message': str(e)}, status_code=500)

# ── Motor de Indexação Facial de Baixo Consumo de CPU (VPS Safe) ──
_INDEXING_STATUS = {} # {event_id: {'status': 'processing'|'done'|'error', 'current': int, 'total': int, 'faces': int, 'message': str}}
_INDEXING_LOCK = asyncio.Lock()

async def _index_event_faces_task(event_id: str, title: str = ""):
    """
    Varre as fotos do Google Drive, detecta rostos com 1 thread e salva matriz compactada.
    Usa pausas para manter CPU abaixo de 40%.
    """
    global _INDEXING_STATUS
    eid_str = str(event_id)
    try:
        _INDEXING_STATUS[eid_str] = {'status': 'processing', 'current': 0, 'total': 0, 'faces': 0, 'percent': 0, 'message': 'Listando fotos do Drive...'}
        
        # 1. Busca fotos do evento
        photos_data = await asyncio.to_thread(get_event_drive_photos, eid_str)
        if not photos_data or not photos_data.get('photos'):
            _INDEXING_STATUS[eid_str] = {'status': 'error', 'current': 0, 'total': 0, 'faces': 0, 'percent': 0, 'message': 'Nenhuma foto encontrada no Drive.'}
            return
            
        photos = photos_data['photos']
        total_photos = len(photos)
        event_title = title or photos_data.get('event', {}).get('title') or f"Solenidade #{eid_str}"
        _INDEXING_STATUS[eid_str]['total'] = total_photos
        
        # 2. Inicializa o motor InsightFace (1 thread de inferência)
        from portal_convidado import _get_selfie_app
        app_ai = await asyncio.to_thread(_get_selfie_app)
        if not app_ai:
            _INDEXING_STATUS[eid_str] = {'status': 'error', 'message': 'Motor de IA não disponível.'}
            return
            
        import drive_service
        from PIL import Image
        import cv2
        
        all_embeddings = []
        all_records = []
        
        print(f"[FACE_INDEXER] 🚀 Iniciando indexação segura de {total_photos} fotos para '{event_title}'...", flush=True)
        
        for idx, p in enumerate(photos):
            fid = p.get('id') or p.get('drive_file_id')
            fname = p.get('filename', f"foto_{idx}.jpg")
            
            _INDEXING_STATUS[eid_str]['current'] = idx + 1
            _INDEXING_STATUS[eid_str]['percent'] = int(((idx + 1) / float(total_photos)) * 100)
            _INDEXING_STATUS[eid_str]['message'] = f"Processando {fname} ({idx+1}/{total_photos})"
            
            try:
                # Baixa a foto original em HD do Google Drive ou usa o cache de 1400px
                raw_bytes = await asyncio.to_thread(drive_service.download_file, fid)
                img_cv = None
                if raw_bytes:
                    nparr = np.frombuffer(raw_bytes, np.uint8)
                    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                else:
                    thumb_path = _get_or_create_thumb_cache(fid)
                    if thumb_path and os.path.exists(thumb_path):
                        img_cv = cv2.imread(thumb_path)
                        
                if img_cv is not None:
                    # Mantém resolução HD (1280px) para alta precisão mesmo em fotos com várias pessoas
                    h, w = img_cv.shape[:2]
                    if max(h, w) > 1280:
                        scale = 1280.0 / max(h, w)
                        img_cv = cv2.resize(img_cv, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                    faces = await asyncio.to_thread(app_ai.get, img_cv)
                    for face in faces:
                        if face.embedding is not None:
                            emb = face.embedding.astype(np.float32)
                            norm = np.linalg.norm(emb)
                            if norm > 0:
                                emb = emb / norm
                            all_embeddings.append(emb)
                            all_records.append({
                                'drive_file_id': fid,
                                'photo_filename': fname,
                                'drive_link': p.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view"
                            })
                            _INDEXING_STATUS[eid_str]['faces'] = len(all_embeddings)
            except Exception as f_err:
                print(f"[FACE_INDEXER WARN] Foto {fname}: {f_err}")
                
            # Pausa tática para respiro de CPU (150ms)
            await asyncio.sleep(0.15)
            
        # 3. Salva Matriz Compactada compatível com _get_event_matrix
        if all_embeddings:
            matrix_arr = np.vstack(all_embeddings).astype(np.float32)
            mat_dir = os.path.join(BASE_DIR, "data")
            os.makedirs(mat_dir, exist_ok=True)
            
            npz_path = os.path.join(mat_dir, f"event_embeddings_{eid_str}.npz")
            json_path = os.path.join(mat_dir, f"event_records_{eid_str}.json")
            
            np.savez_compressed(npz_path, matrix=matrix_arr)
            with open(json_path, 'w', encoding='utf-8') as fj:
                json.dump(all_records, fj, ensure_ascii=False)
                
            print(f"[FACE_INDEXER] ✅ Matriz salva com sucesso: {matrix_arr.shape} em {npz_path}", flush=True)

        _INDEXING_STATUS[eid_str] = {
            'status': 'done',
            'current': total_photos,
            'total': total_photos,
            'faces': len(all_embeddings),
            'percent': 100,
            'message': f"Concluído! {len(all_embeddings)} rostos mapeados em {total_photos} fotos."
        }

        # 4. 📢 Notificação EXCLUSIVA PARA O ADMIN no Telegram
        try:
            from notifications_manager import notify_telegram
            portal_url = f"https://sisgab-cgcfn.ddns.net/evento/{eid_str}"
            tg_msg = (
                f"📸 *INDEXAÇÃO FACIAL CONCLUÍDA COM SUCESSO!*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎖️ *Solenidade:* `{event_title}`\n"
                f"📊 *Total de Fotos:* {total_photos}\n"
                f"👥 *Rostos Mapeados:* {len(all_embeddings)} faces identificadas\n\n"
                f"⚡ _A busca biométrica por selfie já está 100% ativa para este evento._\n\n"
                f"🌐 *Link Público do Portal:* [Acessar Galeria]({portal_url})"
            )
            notify_telegram(tg_msg, "aviso", role_required="admin")
            print(f"[FACE_INDEXER] Notificação de conclusão enviada para o Administrador!", flush=True)
        except Exception as tg_err:
            print(f"[FACE_INDEXER TG ERR] {tg_err}")

    except Exception as e:
        print(f"[FACE_INDEXER ERR] {e}", flush=True)
        _INDEXING_STATUS[eid_str] = {'status': 'error', 'message': str(e)}

@app.post("/api/ai/index_event")
async def api_ai_index_event(request: Request):
    """Dispara a indexação facial do evento em background com baixo uso de CPU."""
    body = await request.json()
    event_id = str(body.get('event_id', '')).strip()
    title = str(body.get('title', '')).strip()
    
    if not event_id:
        return JSONResponse({'ok': False, 'message': 'event_id obrigatório.'}, status_code=400)
        
    curr = _INDEXING_STATUS.get(event_id, {})
    if curr.get('status') == 'processing':
        return JSONResponse({'ok': True, 'message': 'Indexação já está em andamento.', 'status': curr})
        
    asyncio.create_task(_index_event_faces_task(event_id, title))
    return JSONResponse({'ok': True, 'message': 'Indexação facial iniciada em segundo plano.'})

@app.post("/api/ai/upload_matrix")
async def api_ai_upload_matrix(
    event_id: str = Form(...),
    npz_file: UploadFile = File(...),
    json_file: UploadFile = File(None)
):
    """Recebe a matriz de faces pré-processada pelo assistente local com GPU e salva na VPS."""
    try:
        eid_str = str(event_id).strip()
        mat_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(mat_dir, exist_ok=True)

        # 1. Salva arquivo .npz
        npz_bytes = await npz_file.read()
        npz_path = os.path.join(mat_dir, f"event_embeddings_{eid_str}.npz")
        with open(npz_path, "wb") as f_npz:
            f_npz.write(npz_bytes)

        # 2. Salva arquivo .json se fornecido
        records_count = 0
        if json_file:
            json_bytes = await json_file.read()
            json_path = os.path.join(mat_dir, f"event_records_{eid_str}.json")
            with open(json_path, "wb") as f_json:
                f_json.write(json_bytes)
            try:
                records = json.loads(json_bytes.decode('utf-8'))
                records_count = len(records)
            except Exception:
                pass

        # 3. Atualiza estado em memória
        _INDEXING_STATUS[eid_str] = {
            'status': 'done',
            'current': records_count or 100,
            'total': records_count or 100,
            'faces': records_count or 100,
            'percent': 100,
            'message': f'Matriz importada com sucesso ({records_count} faces mapeadas).'
        }

        # Limpa cache do portal para carregar a nova matriz imediatamente
        from portal_convidado import _EVENT_EMBEDDINGS_CACHE
        if eid_str in _EVENT_EMBEDDINGS_CACHE:
            del _EVENT_EMBEDDINGS_CACHE[eid_str]

        print(f"[MATRIX_UPLOAD] ✅ Matriz de faces importada com sucesso para solenidade #{eid_str}!", flush=True)
        return JSONResponse({'ok': True, 'message': 'Matriz facial importada e ativada com sucesso!'})
    except Exception as e:
        print(f"[MATRIX_UPLOAD_ERR] {e}", flush=True)
        return JSONResponse({'ok': False, 'message': str(e)}, status_code=500)

@app.get("/api/ai/index_status")
async def api_ai_index_status(event_id: str):
    """Retorna o status em tempo real da indexação facial do evento."""
    eid_str = str(event_id).strip()
    
    # Se já existir em memória
    if eid_str in _INDEXING_STATUS:
        return JSONResponse({'ok': True, 'status': _INDEXING_STATUS[eid_str]})
        
    # Verifica se já existe matriz em disco (.npz e .json)
    npz_path = os.path.join(BASE_DIR, "data", f"event_embeddings_{eid_str}.npz")
    json_path = os.path.join(BASE_DIR, "data", f"event_records_{eid_str}.json")
    if os.path.exists(npz_path) and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as fj:
                recs = json.load(fj)
            return JSONResponse({
                'ok': True,
                'status': {
                    'status': 'done',
                    'current': len(recs),
                    'total': len(recs),
                    'faces': len(recs),
                    'percent': 100,
                    'message': f"Indexado com sucesso ({len(recs)} faces mapeadas)."
                }
            })
        except Exception:
            pass
            
    return JSONResponse({
        'ok': True,
        'status': {'status': 'idle', 'current': 0, 'total': 0, 'faces': 0, 'percent': 0, 'message': 'Não indexado.'}
    })

@app.post("/api/workers/telegram-alert")
async def trigger_telegram_alert(payload: dict):
    """Envia alertas do Telegram sob demanda."""
    return {"status": "success", "message": "Alerta despachado."}

# ── Endpoints de Integração com Google Drive ──
try:
    from drive_service import criar_pasta_evento, get_pastas_mae_list
except Exception as e_drive_import:
    print(f"[WARN] Erro ao importar drive_service: {e_drive_import}")
    criar_pasta_evento = None
    get_pastas_mae_list = None

@app.get("/api/drive/pastas_mae")
async def api_drive_pastas_mae():
    """Retorna a lista de pastas mãe configuradas no Google Drive."""
    try:
        if not get_pastas_mae_list:
            return JSONResponse({'ok': False, 'error': 'drive_service não disponível'}, status_code=500)
        pastas = await asyncio.to_thread(get_pastas_mae_list)
        return JSONResponse({'ok': True, 'pastas': pastas})
    except Exception as e:
        print(f"[API_DRIVE_PASTAS_MAE_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post("/api/drive/create_event_folder")
async def api_drive_create_event_folder(request: Request):
    """Cria estrutura de pastas no Google Drive para um evento/pauta."""
    try:
        if not criar_pasta_evento:
            return JSONResponse({'ok': False, 'error': 'drive_service não disponível'}, status_code=500)

        body = await request.json()
        titulo = body.get('titulo_evento', '').strip()
        data_evento = body.get('data_evento', '')
        demanda_id = body.get('demanda_id')

        if not titulo:
            return JSONResponse({'ok': False, 'error': 'titulo_evento é obrigatório'}, status_code=400)

        result = await asyncio.to_thread(criar_pasta_evento, titulo, data_evento)

        if not result:
            return JSONResponse({'ok': False, 'error': 'Falha ao criar pasta no Google Drive. Verifique as credenciais e a pasta mãe.'}, status_code=500)

        # Se demanda_id foi informado, atualiza o drive_url na demanda automaticamente de forma resiliente
        if demanda_id:
            try:
                from database import salvar_demanda_drive_link
                await asyncio.to_thread(
                    salvar_demanda_drive_link,
                    int(demanda_id),
                    titulo,
                    result.get('evento_link', ''),
                    result.get('evento_folder_id', '')
                )
                print(f"[DRIVE_API] drive_url vinculado com sucesso na demanda #{demanda_id}")
            except Exception as e_db:
                print(f"[DRIVE_API] Erro ao atualizar drive_url na demanda: {e_db}")

        return JSONResponse({
            'ok': True,
            'evento_folder_id': result.get('evento_folder_id'),
            'selecao_folder_id': result.get('selecao_folder_id'),
            'geral_folder_id': result.get('geral_folder_id'),
            'evento_link': result.get('evento_link'),
        })
    except Exception as e:
        print(f"[API_DRIVE_CREATE_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post("/api/drive/save_drive_link")
async def api_drive_save_link(request: Request):
    """Salva o link do Google Drive em uma demanda de forma resiliente (via campo autoridades se coluna drive_url não existir)."""
    try:
        body = await request.json()
        demanda_id = body.get('demanda_id')
        titulo = body.get('titulo_evento', '')
        drive_url = body.get('drive_url', '').strip()

        if not demanda_id or not drive_url:
            return JSONResponse({'ok': False, 'error': 'demanda_id e drive_url são obrigatórios'}, status_code=400)

        from database import salvar_demanda_drive_link
        ok = await asyncio.to_thread(salvar_demanda_drive_link, int(demanda_id), titulo, drive_url)
        return JSONResponse({'ok': ok})
    except Exception as e:
        print(f"[API_DRIVE_SAVE_LINK_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post("/api/drive/upload_photo")
async def api_drive_upload_photo(
    event_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Recebe upload direto de foto do navegador/celular e envia para a pasta do evento no Google Drive."""
    try:
        content = await file.read()
        if not content:
            return JSONResponse({'ok': False, 'error': 'Arquivo vazio.'}, status_code=400)

        filename = file.filename or f"foto_{int(time.time())}.jpg"
        
        # 1. Obtém a pasta do evento
        event = get_public_event(str(event_id)) or {}
        drive_url = event.get('drive_url')
        
        import drive_service
        folder_id = None
        if drive_url:
            folder_id = drive_service.extract_folder_id_from_url(drive_url)
            
        if not folder_id:
            # Tenta criar ou encontrar pasta
            res_pasta = await asyncio.to_thread(
                drive_service.criar_pasta_evento,
                event.get('title') or f"Solenidade {event_id}",
                str(event.get('date') or datetime.now().strftime('%Y-%m-%d'))
            )
            if res_pasta:
                folder_id = res_pasta.get('geral_folder_id') or res_pasta.get('evento_folder_id')

        if not folder_id:
            folder_id = drive_service.get_pasta_mae_id()

        if not folder_id:
            return JSONResponse({'ok': False, 'error': 'Pasta do Drive não encontrada.'}, status_code=404)

        # 2. Faz o upload
        mime = file.content_type or 'image/jpeg'
        res_upload = await asyncio.to_thread(drive_service.upload_file, content, filename, folder_id, mime)
        
        if res_upload and res_upload.get('id'):
            return JSONResponse({
                'ok': True,
                'file_id': res_upload.get('id'),
                'filename': filename,
                'link': res_upload.get('webViewLink')
            })
        else:
            err_msg = res_upload.get('detail') if isinstance(res_upload, dict) else 'Falha ao gravar no Drive.'
            return JSONResponse({'ok': False, 'error': err_msg}, status_code=500)
    except Exception as e:
        print(f"[API_DRIVE_UPLOAD_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ── GERENCIADOR MULTI-CONTA E OAUTH 2.0 DO GOOGLE DRIVE ──

@app.get("/api/drive/accounts")
async def api_drive_get_accounts():
    """Retorna as contas cadastradas, modo ativo e status da conexão."""
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        
        mode = 'service_account'
        oauth_token = None
        sa_info = None
        pastas_mae = []
        
        if db:
            r_mode = db.table('config').select('valor').eq('chave', 'drive_auth_mode').execute()
            if r_mode.data and r_mode.data[0].get('valor'):
                mode = r_mode.data[0]['valor'].strip().lower()

            r_oauth = db.table('config').select('valor').eq('chave', 'drive_oauth_token_json').execute()
            if r_oauth.data and r_oauth.data[0].get('valor'):
                try:
                    oauth_token = json.loads(r_oauth.data[0]['valor'])
                except Exception:
                    oauth_token = None

            r_sa = db.table('config').select('valor').eq('chave', 'drive_service_account_json').execute()
            if r_sa.data and r_sa.data[0].get('valor'):
                try:
                    sa_info = json.loads(r_sa.data[0]['valor'])
                except Exception:
                    sa_info = None

            import drive_service
            pastas_mae = drive_service.get_pastas_mae_list()

        # Testa conexão atual
        import drive_service
        ok, msg = await asyncio.to_thread(drive_service.testar_conexao)

        return JSONResponse({
            'ok': True,
            'active_mode': mode,
            'connection_status': ok,
            'connection_message': msg,
            'has_oauth': oauth_token is not None,
            'oauth_email': oauth_token.get('client_email') or oauth_token.get('email') if oauth_token else None,
            'has_service_account': sa_info is not None,
            'sa_email': sa_info.get('client_email') if sa_info else None,
            'pastas_mae': pastas_mae
        })
    except Exception as e:
        print(f"[API_DRIVE_ACCOUNTS_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post("/api/drive/set_mode")
async def api_drive_set_mode(request: Request):
    """Alterna o modo de autenticação ativo entre 'oauth' (conta pessoal com espaço) e 'service_account'."""
    try:
        body = await request.json()
        mode = body.get('mode', 'service_account').strip().lower()
        if mode not in ('oauth', 'service_account'):
            return JSONResponse({'ok': False, 'error': 'Modo inválido. Use oauth ou service_account.'}, status_code=400)

        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if db:
            db.table('config').upsert({'chave': 'drive_auth_mode', 'valor': mode}, on_conflict='chave').execute()

        import drive_service
        drive_service.reset_drive_service()
        ok, msg = await asyncio.to_thread(drive_service.testar_conexao)

        return JSONResponse({'ok': True, 'mode': mode, 'connection_ok': ok, 'message': msg})
    except Exception as e:
        print(f"[API_DRIVE_SET_MODE_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post("/api/drive/save_oauth_token")
async def api_drive_save_oauth_token(request: Request):
    """Salva o token OAuth JSON fornecido diretamente ou via credenciais."""
    try:
        body = await request.json()
        token_data = body.get('token')
        if not token_data:
            return JSONResponse({'ok': False, 'error': 'Dados do token são obrigatórios.'}, status_code=400)

        token_json_str = json.dumps(token_data) if isinstance(token_data, dict) else str(token_data).strip()

        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if db:
            db.table('config').upsert({'chave': 'drive_oauth_token_json', 'valor': token_json_str}, on_conflict='chave').execute()
            db.table('config').upsert({'chave': 'drive_auth_mode', 'valor': 'oauth'}, on_conflict='chave').execute()

        import drive_service
        drive_service.reset_drive_service()
        ok, msg = await asyncio.to_thread(drive_service.testar_conexao)

        return JSONResponse({'ok': True, 'connection_ok': ok, 'message': msg})
    except Exception as e:
        print(f"[API_DRIVE_SAVE_TOKEN_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ── FASE 3: INTEGRAÇÃO META GRAPH API (INSTAGRAM DIRECT PUBLISHING) ──

@app.get("/api/instagram/config")
async def api_instagram_get_config():
    """Retorna o status da integração com a Meta Graph API / Instagram Graph API."""
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        
        has_token = False
        account_id = None
        username = None
        
        if db:
            res_t = db.table('config').select('valor').eq('chave', 'instagram_access_token').execute()
            if res_t.data and res_t.data[0].get('valor'):
                has_token = True
            
            res_a = db.table('config').select('valor').eq('chave', 'instagram_business_account_id').execute()
            if res_a.data and res_a.data[0].get('valor'):
                account_id = res_a.data[0]['valor']

            res_u = db.table('config').select('valor').eq('chave', 'instagram_username').execute()
            if res_u.data and res_u.data[0].get('valor'):
                username = res_u.data[0]['valor']

        return JSONResponse({
            'ok': True,
            'is_configured': has_token and (account_id is not None),
            'account_id': account_id,
            'username': username or 'COMSOC / CGCFN Oficial'
        })
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post("/api/instagram/config")
async def api_instagram_save_config(request: Request):
    """Salva credenciais da Meta Graph API (Access Token de Longa Duração e Business Account ID)."""
    try:
        body = await request.json()
        token = body.get('access_token', '').strip()
        account_id = body.get('business_account_id', '').strip()
        username = body.get('username', '').strip()

        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if db:
            if token:
                db.table('config').upsert({'chave': 'instagram_access_token', 'valor': token}, on_conflict='chave').execute()
            if account_id:
                db.table('config').upsert({'chave': 'instagram_business_account_id', 'valor': account_id}, on_conflict='chave').execute()
            if username:
                db.table('config').upsert({'chave': 'instagram_username', 'valor': username}, on_conflict='chave').execute()

        return JSONResponse({'ok': True, 'message': 'Configurações da Meta API salvas com sucesso!'})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


@app.post("/api/instagram/publish")
async def api_instagram_publish_post(request: Request):
    """
    Publica uma foto ou carrossel diretamente no Instagram via Meta Graph API oficial.
    Fluxo: Container Creation -> Media Publish -> Status
    """
    try:
        body = await request.json()
        image_url = body.get('image_url', '').strip()
        caption = body.get('caption', '').strip()
        is_carousel = body.get('is_carousel', False)
        children_urls = body.get('children_urls', [])

        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        
        token = None
        account_id = None
        if db:
            r_tok = db.table('config').select('valor').eq('chave', 'instagram_access_token').execute()
            if r_tok.data and r_tok.data[0].get('valor'):
                token = r_tok.data[0]['valor']
            
            r_acc = db.table('config').select('valor').eq('chave', 'instagram_business_account_id').execute()
            if r_acc.data and r_acc.data[0].get('valor'):
                account_id = r_acc.data[0]['valor']

        if not token or not account_id:
            return JSONResponse({
                'ok': False,
                'error': 'Meta Graph API não configurada. Insira o Access Token e o Instagram Business ID no Painel Admin.'
            }, status_code=400)

        # 1. Cria Container de Mídia na Meta API
        import urllib.parse
        import urllib.request

        container_url = f"https://graph.facebook.com/v19.0/{account_id}/media"
        
        params = {
            'access_token': token,
            'caption': caption
        }

        if is_carousel and len(children_urls) > 1:
            # Cria containers filhos
            child_ids = []
            for c_url in children_urls[:10]:
                c_params = urllib.parse.urlencode({
                    'image_url': c_url,
                    'is_carousel_item': 'true',
                    'access_token': token
                }).encode('utf-8')
                req_c = urllib.request.Request(container_url, data=c_params)
                with urllib.request.urlopen(req_c, timeout=15) as resp_c:
                    res_c_json = json.loads(resp_c.read().decode('utf-8'))
                    if 'id' in res_c_json:
                        child_ids.append(res_c_json['id'])

            if not child_ids:
                return JSONResponse({'ok': False, 'error': 'Falha ao criar itens do carrossel na Meta API.'}, status_code=500)

            # Container mestre do carrossel
            params['media_type'] = 'CAROUSEL'
            params['children'] = ','.join(child_ids)
        else:
            params['image_url'] = image_url

        data_post = urllib.parse.urlencode(params).encode('utf-8')
        req = urllib.request.Request(container_url, data=data_post)

        with urllib.request.urlopen(req, timeout=20) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            creation_id = res_json.get('id')

        if not creation_id:
            return JSONResponse({'ok': False, 'error': 'Não foi possível obter o Creation ID da Meta API.'}, status_code=500)

        # 2. Publica o Container
        publish_url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
        pub_params = urllib.parse.urlencode({
            'creation_id': creation_id,
            'access_token': token
        }).encode('utf-8')

        req_pub = urllib.request.Request(publish_url, data=pub_params)
        with urllib.request.urlopen(req_pub, timeout=20) as resp_pub:
            pub_json = json.loads(resp_pub.read().decode('utf-8'))
            post_id = pub_json.get('id')

        # 3. Notifica a equipe via Telegram
        try:
            from notifications_manager import notify_telegram
            notify_telegram(
                f"🚀 *NOVO POST PUBLICADO NO INSTAGRAM OFICIAL*\n\n"
                f"📸 Solenidade/Evento: *{caption[:60]}...*\n"
                f"🆔 Post ID Meta: `{post_id}`\n\n"
                f"⚓ _SisGAB — Gestão de Mídia Social Agressiva_",
                category='social_media'
            )
        except Exception as e_notif:
            print(f"[INSTA_NOTIF_WARN] {e_notif}")

        return JSONResponse({
            'ok': True,
            'post_id': post_id,
            'message': 'Post publicado no Instagram com sucesso!'
        })
    except Exception as e:
        print(f"[API_INSTAGRAM_PUBLISH_ERR] {e}")
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)


# ── SPA Catch-All: Entrega o React Router para todas as rotas ──
@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_react_spa(full_path: str):
    # Se for um arquivo estático existente no dist (ex: logo, manifest, etc.)
    target_file = os.path.join(REACT_DIST_DIR, full_path)
    if full_path and os.path.isfile(target_file):
        return FileResponse(target_file)

    # Entrega o index.html do React para todas as rotas (SPA)
    index_file = os.path.join(REACT_DIST_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)

    return JSONResponse(
        status_code=503,
        content={"error": "Compilação do React não encontrada. Execute 'npm run build' em frontend-react."}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"⚓ [SisGAB 2.0] Servidor de produção ativo na porta {port}...", flush=True)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False, proxy_headers=True, forwarded_allow_ips="*")
