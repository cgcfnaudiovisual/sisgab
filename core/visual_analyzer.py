import os
import json
import base64
import logging
import subprocess
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

from core.audio_extractor import get_video_duration, find_ffmpeg

logger = logging.getLogger(__name__)

def extract_video_frames(
    video_path: str,
    job_dir: str,
    vid_idx: int,
    ffmpeg_bin: str = "ffmpeg",
    progress_callback: Optional[Callable] = None
) -> tuple:
    """
    Extrai frames do vídeo a cada N segundos em uma resolução reduzida para análise do Gemini.
    Retorna (diretório_dos_frames, intervalo_segundos, lista_caminhos_frames)
    """
    duration = get_video_duration(video_path, ffmpeg_bin)
    if duration <= 0:
        duration = 600  # Fallback se não conseguir ler a duração
        
    # Calcular intervalo de frames dinâmico baseado na duração
    if duration < 300:      # < 5 min
        interval = 2        # 1 frame a cada 2s
    elif duration < 900:    # 5 a 15 min
        interval = 5        # 1 frame a cada 5s
    elif duration < 3600:   # 15 min a 1 hora
        interval = 10       # 1 frame a cada 10s
    else:                   # > 1 hora
        interval = 20       # 1 frame a cada 20s
        
    frames_dir = Path(job_dir) / f"frames_{vid_idx}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpar frames antigos se existirem
    for f in frames_dir.glob("*.jpg"):
        try:
            f.unlink()
        except Exception:
            pass
            
    if progress_callback:
        progress_callback(0.1, f"Extraindo quadros (1 a cada {interval}s) para análise visual...")
        
    # Usar FFmpeg para extrair quadros em baixa resolução (240p de altura) com qualidade otimizada
    # Usando escala -2 garante número par para compatibilidade com codecs, mas -1 com largura fixa funciona bem.
    cmd = [
        ffmpeg_bin,
        "-i", video_path,
        "-vf", f"fps=1/{interval},scale=426:-1",
        "-q:v", "6",  # Qualidade JPG de 1-31 (6 é ideal: leve mas nítida)
        "-y",
        str(frames_dir / "img_%04d.jpg")
    ]
    
    logger.info(f"Executando FFmpeg para extração de frames: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    if result.returncode != 0:
        logger.error(f"Erro no FFmpeg ao extrair frames: {result.stderr}")
        raise RuntimeError(f"Erro FFmpeg ao extrair quadros: {result.stderr}")
        
    frame_paths = sorted(list(frames_dir.glob("img_*.jpg")))
    logger.info(f"Extraídos {len(frame_paths)} quadros com intervalo de {interval}s em {frames_dir}")
    
    if progress_callback:
        progress_callback(0.35, f"{len(frame_paths)} quadros extraídos com sucesso.")
        
    return frames_dir, interval, frame_paths


def analyze_video_visual_gemini(
    video_path: str,
    theme: str,
    api_key: str,
    model_name: str = "gemini-1.5-flash",  # Gemini 1.5 Flash suporta muito bem multimodal
    job_dir: str = "",
    vid_idx: int = 0,
    ffmpeg_bin: str = "ffmpeg",
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Extrai frames do vídeo e envia para a API do Gemini junto com as imagens codificadas em base64.
    Retorna a lista de trechos sugeridos com scores e justificativas visuais.
    """
    if not api_key:
        raise ValueError("Chave de API do Gemini não configurada.")
        
    # 1. Extrair quadros
    _, interval, frame_paths = extract_video_frames(
        video_path, job_dir, vid_idx, ffmpeg_bin, progress_callback
    )
    
    if not frame_paths:
        raise RuntimeError("Nenhum quadro pôde ser extraído do vídeo para análise.")
        
    if progress_callback:
        progress_callback(0.4, "Convertendo imagens e montando prompt multimodal...")
        
    # Construir as partes do conteúdo (Imagens codificadas + rótulos de tempo)
    parts = []
    
    # Adicionar cada frame no payload com seu timestamp correspondente
    for idx, path in enumerate(frame_paths):
        # Frame 1 é o início do vídeo (0s), Frame 2 é aos 'interval' segundos, etc.
        timestamp_seconds = idx * interval
        
        # Converter imagem para Base64
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            
        parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": encoded_string
            }
        })
        parts.append({
            "text": f"Frame {idx + 1} (Tempo: {timestamp_seconds}s)"
        })
        
    # Prompt de instruções detalhado
    prompt = f"""Você é um editor de vídeos profissional especializado na criação de cortes, momentos de destaque (highlights) e conteúdos curtos para redes sociais (Instagram Reels, TikTok, YouTube Shorts).
Eu lhe enviei uma sequência ordenada de quadros (frames) extraídos deste vídeo a cada {interval} segundos.

Sua tarefa é analisar visualmente a evolução e o conteúdo desses quadros para identificar trechos (com tempos de início e fim) que sejam interessantes, dinâmicos ou de grande relevância visual para o seguinte tema solicitado pelo usuário: "{theme}".

Áreas de interesse visual:
1. Trechos de alta expressividade: gestos enérgicos, reações fortes ou expressões faciais marcantes.
2. Trechos de slides ou textos: quadros que mostram slides, gráficos, apresentações ou textos em tela muito claros e relevantes que agregam valor educacional ou informativo.
3. Mudanças de cena ou ações dinâmicas: cortes, movimentações de câmera, foco em objetos de interesse, ou transições marcantes.

Para cada corte/highlight interessante com score de relevância igual ou superior a 5.0, você deve definir:
- "start": Momento de início do trecho em segundos (número float ou inteiro).
- "end": Momento de término do trecho em segundos (número float ou inteiro).
- "score": Nota de 5.0 a 10.0 baseada no impacto visual do trecho.
- "category": Uma das categorias: "💎 Destaque forte", "⭐ Bom conteúdo", "📌 Conteúdo médio".
- "reason": Breve justificativa (1 frase) descrevendo o que acontece visualmente neste trecho (ex: "Exibição de slide com gráfico importante sobre crescimento", "O apresentador demonstra alta energia com as mãos").
- "speaker": Se houver uma pessoa visível focada em tela que pareça estar apresentando/falando, atribua a ela um identificador como "Speaker A", "Speaker B", mantendo consistência entre os trechos. Se não houver, ou for incerto, retorne "Speaker ?".

REGRAS CRÍTICAS:
- Retorne APENAS um objeto JSON válido (um array de objetos contendo os campos listados acima).
- NÃO adicione blocos de código markdown (como ```json) ou introduções/conclusões na resposta.
- Garanta que "start" e "end" correspondam à escala de tempo informada nas imagens.

Exemplo de retorno esperado:
[
  {{
    "start": 12.0,
    "end": 24.0,
    "score": 9.0,
    "category": "💎 Destaque forte",
    "reason": "O apresentador começa a falar apontando com entusiasmo, demonstrando linguagem corporal positiva.",
    "speaker": "Speaker A"
  }},
  {{
    "start": 60.0,
    "end": 75.0,
    "score": 7.8,
    "category": "⭐ Bom conteúdo",
    "reason": "Quadro exibe um slide detalhado contendo a definição do conceito abordado.",
    "speaker": "Speaker ?"
  }}
]
"""
    
    parts.append({
        "text": prompt
    })
    
    if progress_callback:
        progress_callback(0.65, "Enviando quadros para a API do Gemini (Multimodal)...")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": parts
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    data_bytes = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        if progress_callback:
            progress_callback(0.85, "Aguardando processamento visual do Gemini...")
            
        with urllib.request.urlopen(req, timeout=90) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
        text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Limpar blocos de código markdown caso o modelo tenha ignorado a instrução
        if text_response.startswith("```"):
            lines = text_response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            text_response = "\n".join(lines).strip()
            
        clips_list = json.loads(text_response)
        
        # Formatar a resposta no formato esperado de clips
        formatted_clips = []
        for item in clips_list:
            try:
                start = float(item["start"])
                end = float(item["end"])
                duration = end - start
                
                # Ignorar clips inválidos
                if duration <= 0:
                    continue
                    
                formatted_clips.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "duration": round(duration, 2),
                    "score": round(float(item.get("score", 5.0)), 2),
                    "category": item.get("category", "📌 Conteúdo médio"),
                    "text": f"[Análise Visual] {item.get('reason', 'Destaque visual identificado')}",
                    "score_reason": item.get("reason", "Análise de frames"),
                    "speaker": item.get("speaker", "Speaker ?")
                })
            except Exception as item_err:
                logger.warning(f"Erro ao formatar clip retornado pelo Gemini: {item_err}")
                
        if progress_callback:
            progress_callback(1.0, f"Análise visual pelo Gemini concluída! {len(formatted_clips)} trechos encontrados.")
            
        # Ordenar cronologicamente
        formatted_clips.sort(key=lambda c: c["start"])
        return formatted_clips
        
    except Exception as e:
        logger.error(f"Erro na análise visual do Gemini: {e}")
        if progress_callback:
            progress_callback(1.0, f"Falha na API do Gemini: {e}")
        raise e
