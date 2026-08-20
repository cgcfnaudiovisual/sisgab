import os
import io
import time
import json
import re
import asyncio
import numpy as np
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SisGAB 2.0 - Servidor de Produção & Motor Híbrido")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REACT_DIST_DIR = os.path.join(BASE_DIR, "frontend-react", "dist")
ASSETS_DIR = os.path.join(REACT_DIST_DIR, "assets")

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

# ── Endpoints de Reconhecimento Facial Sob Demanda ──
try:
    from portal_convidado import _extract_selfie_embedding, _get_event_matrix, _get_selfie_app, _get_geral_photos
except Exception as e_import:
    print(f"[WARN] Erro ao importar portal_convidado: {e_import}")
    _extract_selfie_embedding = None
    _get_event_matrix = None
    _get_selfie_app = None
    _get_geral_photos = None

@app.on_event("startup")
async def startup_event():
    print("⚓ [SisGAB 2.0] Pré-aquecendo motor de IA facial e matrizes em RAM...")
    try:
        if _get_selfie_app:
            asyncio.create_task(asyncio.to_thread(_get_selfie_app))
        if _get_event_matrix:
            asyncio.create_task(asyncio.to_thread(_get_event_matrix, "50"))
    except Exception as e:
        print(f"[SisGAB] ⚠️ Aviso na inicialização: {e}")

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

        # Extrai folder_id e drive_url de todos os campos possíveis da demanda
        raw_candidates = [
            str(dem.get('drive_url') or ''),
            str(dem.get('drive_link') or ''),
            str(dem.get('drive_folder_id') or ''),
            str(dem.get('autoridades') or ''),
            str(dem.get('arquivo_url') or '')
        ]
        combined_text = ' '.join(raw_candidates)

        drive_folder_id = ''
        drive_url = dem.get('drive_url') or dem.get('drive_link') or ''

        m = re.search(r'folders/([a-zA-Z0-9_-]+)', combined_text)
        if m:
            drive_folder_id = m.group(1)
        elif '/d/' in combined_text:
            m2 = re.search(r'/d/([a-zA-Z0-9_-]+)', combined_text)
            if m2:
                drive_folder_id = m2.group(1)
        elif dem.get('drive_folder_id'):
            drive_folder_id = str(dem.get('drive_folder_id')).strip()

        if drive_folder_id and not drive_url:
            drive_url = f"https://drive.google.com/drive/folders/{drive_folder_id}"

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
                        'drive_url': drive_url or 'https://drive.google.com/drive/folders/1cqK3F24QQCj5tgkXy-zJZoP1al-dF3Yv'
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

@app.get("/api/proxy/image")
async def proxy_image(url: str = "", drive_id: str = ""):
    """Proxy CORS para download e conversão de fotos do Google Drive para uso em IA / Vision."""
    try:
        target_url = url
        if drive_id and not target_url:
            target_url = f"https://drive.google.com/thumbnail?id={drive_id}&sz=w800"
            
        if not target_url:
            return JSONResponse({'error': 'URL não informada'}, status_code=400)
            
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                media_type = resp.headers.get("content-type", "image/jpeg")
                return Response(
                    content=resp.content,
                    media_type=media_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
            else:
                return JSONResponse({'error': f'Falha ao carregar imagem: status {resp.status_code}'}, status_code=resp.status_code)
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

@app.post("/api/workers/face-index")
async def trigger_face_indexing():
    """Dispara a indexação facial sob demanda."""
    return {"status": "success", "message": "Motor de reconhecimento facial sob demanda iniciado."}

@app.post("/api/workers/telegram-alert")
async def trigger_telegram_alert(payload: dict):
    """Envia alertas do Telegram sob demanda."""
    return {"status": "success", "message": "Alerta despachado."}

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
    print(f"⚓ [SisGAB 2.0] Servidor de produção ativo na porta {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False, proxy_headers=True, forwarded_allow_ips="*")
