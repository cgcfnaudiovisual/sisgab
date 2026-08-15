# Usa uma imagem oficial leve do Python
FROM python:3.10-slim

# Instala dependências de compilação e bibliotecas de sistema necessárias para InsightFace e OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root com UID 1000
RUN useradd -m -u 1000 appuser

# Define o diretório de trabalho
WORKDIR /app

# Copia o arquivo de dependências primeiro (otimiza cache do docker)
COPY requirements.txt .

# Instala as dependências do seu SisGAB (incluindo insightface e onnxruntime)
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código para dentro do container
COPY --chown=appuser:appuser . .

# Ajusta permissões extras da pasta
RUN chown -R appuser:appuser /app

# Muda para o usuário não-root
USER appuser

EXPOSE 8080
ENV PORT=8080
ENV UVICORN_FORWARDED_ALLOW_IPS=*
ENV UVICORN_PROXY_HEADERS=true

CMD ["python", "main.py"]
