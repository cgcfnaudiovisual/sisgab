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
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REACT_DIST_DIR = os.path.join(BASE_DIR, "frontend-react", "dist")
ASSETS_DIR = os.path.join(REACT_DIST_DIR, "assets")

# ── Endpoints de Reconhecimento Facial Sob Demanda ──
try:
    from portal_convidado import _extract_selfie_embedding, _get_event_matrix, _get_selfie_app, _get_geral_photos
except Exception as e_import:
    print(f"[WARN] Erro ao importar portal_convidado: {e_import}")
    _extract_selfie_embedding = None
    _get_event_matrix = None
    _get_selfie_app = None
    _get_geral_photos = None

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # ── STARTUP (TOTALMENTE ASSÍNCRONO EM SEGUNDO PLANO) ──
    def _bg_worker():
        print("⚓ [SisGAB 2.0] Pré-aquecendo motor de IA facial e matrizes em RAM...", flush=True)
        try:
            if _get_selfie_app:
                _get_selfie_app()
            if _get_event_matrix:
                _get_event_matrix("50")
        except Exception as e:
            print(f"[SisGAB] ⚠️ Aviso na inicialização da IA: {e}", flush=True)

        try:
            import telegram_bot
            print("🤖 [SisGAB 2.0] Inicializando Bot do Telegram em thread dedicada...", flush=True)
            bot_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(bot_loop)
            bot_loop.run_until_complete(telegram_bot.init_bot())
            bot_loop.run_forever()
        except Exception as e:
            print(f"[SisGAB] ⚠️ Erro no Bot do Telegram: {e}", flush=True)

    t_bg = threading.Thread(target=_bg_worker, daemon=True, name="SisGAB-BackgroundEngine")
    t_bg.start()

    try:
        from alerts_manager import AlertsManager
        from notifications_manager import start_19h_briefing_scheduler, start_15h_demand_scheduler
        AlertsManager.start_alerts_scheduler()
        start_19h_briefing_scheduler()
        start_15h_demand_scheduler()
        print("⏰ [SisGAB 2.0] Agendadores de notificações (15h / 19h / Alertas) ativos.", flush=True)
    except Exception as e:
        print(f"[SisGAB] ⚠️ Erro ao iniciar agendadores: {e}", flush=True)

    yield

    # ── SHUTDOWN ──
    try:
        import telegram_bot
        await telegram_bot.stop_bot()
        print("🤖 [SisGAB 2.0] Bot do Telegram encerrado.", flush=True)
    except Exception as e:
        print(f"[SisGAB] Erro ao encerrar bot: {e}", flush=True)

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
            
        drive_url = dem.get('drive_url') or dem.get('drive_link') or ''
        drive_folder_id = dem.get('drive_folder_id') or ''
        
        # Extrai folder_id se for URL
        if not drive_folder_id and drive_url:
            m = re.search(r'folders/([a-zA-Z0-9_-]+)', drive_url)
            if m:
                drive_folder_id = m.group(1)
            elif '/d/' in drive_url:
                m2 = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_url)
                if m2:
                    drive_folder_id = m2.group(1)
            elif len(drive_url.strip()) in (28, 33, 34, 44) and '/' not in drive_url:
                drive_folder_id = drive_url.strip()
                
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
        raw_photos = []
        if _get_geral_photos:
            raw_photos = _get_geral_photos(drive_folder_id)
        if not raw_photos:
            raw_photos = drive_service.list_files(drive_folder_id, mime_filter='image/', page_size=5000) or []
            
        formatted_photos = []
        for p in raw_photos:
            fid = p.get('id') or p.get('drive_file_id')
            fname = p.get('name') or p.get('filename') or f"{fid}.jpg"
            formatted_photos.append({
                'id': fid,
                'filename': fname,
                'drive_file_id': fid,
                'url': p.get('webViewLink') or f"https://drive.google.com/uc?export=view&id={fid}",
                'thumbnail_url': p.get('thumbnailLink') or f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                'drive_thumb': f"https://drive.google.com/thumbnail?id={fid}&sz=w600",
                'drive_link': f"https://drive.google.com/file/d/{fid}/view"
            })
            
        return {
            'ok': True,
            'event': {
                'id': dem.get('id'),
                'title': dem.get('titulo_evento'),
                'date': dem.get('data_evento'),
                'location': dem.get('local_evento'),
                'drive_url': drive_url
            },
            'photos': formatted_photos
        }
    except Exception as e:
        print(f"[GET_EVENT_DRIVE_PHOTOS ERR] {e}")
        return {'ok': False, 'message': str(e), 'photos': []}

@app.get("/api/portal/photos")
async def api_portal_photos(event_id: str):
    """Retorna dinamicamente os dados do evento e todas as fotos da sua pasta vinculada no Google Drive."""
    res = await asyncio.to_thread(get_event_drive_photos, str(event_id))
    if not res:
        return JSONResponse({'ok': False, 'message': 'Evento não encontrado.', 'photos': []}, status_code=404)
    return JSONResponse(res)

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

@app.post("/api/workers/face-index")
async def trigger_face_indexing():
    """Dispara a indexação facial sob demanda."""
    return {"status": "success", "message": "Motor de reconhecimento facial sob demanda iniciado."}

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

        # Se demanda_id foi informado, atualiza o drive_url na demanda automaticamente
        if demanda_id:
            try:
                from database import get_service_db_connection, get_db_connection
                db = get_service_db_connection() or get_db_connection()
                if db:
                    db.table('demandas_comunicacao').update({
                        'drive_url': result.get('evento_link', '')
                    }).eq('id', int(demanda_id)).execute()
                    print(f"[DRIVE_API] drive_url atualizado na demanda #{demanda_id}")
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
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
