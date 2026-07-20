import os
import re
import math
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def format_timecode(seconds: float, fps: int = 25) -> str:
    """Converte segundos para timecode HH:MM:SS:FF"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    f = int(round((seconds % 1) * fps))
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

def seconds_to_rational(seconds: float, fps: int = 25) -> tuple:
    """Converte segundos para valor racional (numerador, denominador) para FCPXML"""
    frames = round(seconds * fps)
    return frames, fps

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos de nome de arquivo"""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def ensure_dir(path: str) -> Path:
    """Cria diretório se não existir"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def format_duration(seconds: float) -> str:
    """Formata duração legível: 1m23s"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}m{s:.0f}s"

def score_to_color(score: float) -> str:
    """Retorna cor hex baseada no score 0-10"""
    if score >= 8.0:
        return "#00ff88"   # verde brilhante
    elif score >= 6.5:
        return "#ffcc00"   # amarelo
    elif score >= 5.0:
        return "#ff8800"   # laranja
    else:
        return "#ff4444"   # vermelho
