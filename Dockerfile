# ==========================================
# Estágio 1: Build do Frontend React (Vite)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend-react

COPY frontend-react/package*.json ./
RUN npm ci

COPY frontend-react/ ./
RUN npm run build

# ==========================================
# Estágio 2: Runtime Python & Servidor SisGAB 2.0
# ==========================================
FROM python:3.10-slim

# Instala dependências de sistema para InsightFace e OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do backend e utilitários
COPY . .

# Copia a pasta de distribuição do React compilada no Estágio 1
COPY --from=frontend-builder /app/frontend-react/dist /app/frontend-react/dist

EXPOSE 8080
ENV PORT=8080
ENV UVICORN_FORWARDED_ALLOW_IPS=*
ENV UVICORN_PROXY_HEADERS=true
ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]
