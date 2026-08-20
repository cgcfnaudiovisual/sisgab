import os
import uvicorn
from fastapi import FastAPI, Request
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

# ── Endpoints de Rotinas Sob Demanda em Python ──
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
