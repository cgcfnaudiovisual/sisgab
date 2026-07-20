import os
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

def find_ffmpeg() -> str:
    """Localiza o executável do FFmpeg no sistema ou pasta local"""
    # Verificar pasta local primeiro
    local_paths = [
        Path(__file__).parent.parent / "bin" / "ffmpeg.exe",
        Path(__file__).parent.parent / "ffmpeg.exe",
    ]
    for p in local_paths:
        if p.exists():
            return str(p)
    
    # Verificar PATH do sistema
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return "ffmpeg"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return None

def extract_audio(
    video_path: str,
    output_path: str,
    ffmpeg_bin: str = "ffmpeg",
    progress_callback: Optional[Callable] = None
) -> str:
    """
    Extrai áudio do vídeo como WAV mono 16kHz (formato ideal para Whisper e PyAnnote)
    
    Args:
        video_path: Caminho do arquivo de vídeo
        output_path: Caminho do arquivo WAV de saída
        ffmpeg_bin: Caminho do executável FFmpeg
        progress_callback: Função chamada com progresso (0.0-1.0)
    
    Returns:
        Caminho do arquivo WAV gerado
    """
    if ffmpeg_bin is None:
        ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin is None:
        raise RuntimeError("FFmpeg não encontrado. Execute setup.bat para instalar.")
    
    output_path = str(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Obter duração do vídeo para progresso
    duration = get_video_duration(video_path, ffmpeg_bin)
    
    cmd = [
        ffmpeg_bin,
        "-i", video_path,
        "-vn",               # sem vídeo
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "16000",      # 16kHz (necessário para Whisper)
        "-ac", "1",          # mono
        "-y",                # sobrescrever
        output_path
    ]
    
    logger.info(f"Extraindo áudio: {video_path} → {output_path}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Erro FFmpeg ao extrair áudio: {stderr}")
    
    if not os.path.exists(output_path):
        raise RuntimeError(f"Arquivo de saída não foi criado: {output_path}")
    
    logger.info(f"Áudio extraído com sucesso: {output_path}")
    return output_path

def get_video_duration(video_path: str, ffmpeg_bin: str = "ffmpeg") -> float:
    """Obtém duração do vídeo em segundos usando ffprobe"""
    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    
    try:
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception as e:
        logger.warning(f"Não foi possível obter duração: {e}")
    
    return 0.0

def get_video_info(video_path: str, ffmpeg_bin: str = "ffmpeg") -> Dict[str, Any]:
    """Obtém informações completas do vídeo (resolução, fps, codec, duração)"""
    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    
    info = {
        "path": video_path,
        "filename": os.path.basename(video_path),
        "duration": 0.0,
        "width": 1920,
        "height": 1080,
        "fps": 25.0,
        "codec": "h264"
    }
    
    try:
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            fmt = data.get("format", {})
            info["duration"] = float(fmt.get("duration", 0))
            
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["width"] = stream.get("width", 1920)
                    info["height"] = stream.get("height", 1080)
                    info["codec"] = stream.get("codec_name", "h264")
                    
                    # Calcular FPS
                    r_frame_rate = stream.get("r_frame_rate", "25/1")
                    if "/" in r_frame_rate:
                        num, den = r_frame_rate.split("/")
                        info["fps"] = round(float(num) / float(den), 3)
                    break
    except Exception as e:
        logger.warning(f"Erro ao obter info do vídeo {video_path}: {e}")
    
    return info
