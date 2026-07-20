import logging
import os
import multiprocessing
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# Cache do modelo para não recarregar a cada vídeo
_model_cache: Dict[str, Any] = {}

def transcribe(
    audio_path: str,
    model_size: str = "medium",
    language: str = "pt",
    progress_callback: Optional[Callable] = None,
    beam_size: int = 1,          # 1 = greedy (muito mais rápido, qualidade ok)
    word_timestamps: bool = True,
    initial_prompt: str = ""
) -> List[Dict[str, Any]]:
    """
    Transcreve áudio usando faster-whisper com timestamps precisos por segmento.

    Args:
        audio_path:       Caminho do arquivo WAV
        model_size:       Tamanho do modelo Whisper (tiny, base, small, medium, large-v3)
        language:         Código do idioma (pt, en, es) ou None para autodetectar
        progress_callback: Função de progresso(0.0-1.0, mensagem)
        beam_size:        1=greedy/rápido, 5=preciso/lento
        word_timestamps:  Gerar timestamps por palavra (necessário para cortes precisos)
        initial_prompt:   Dica de contexto para o modelo
    Returns:
        Lista de segmentos: [{start, end, text, words, avg_logprob}]
    """
    import hashlib
    import json
    
    # Gerar chave de cache baseada nas propriedades do áudio para evitar re-transcrever
    try:
        audio_size = os.path.getsize(audio_path)
    except Exception:
        audio_size = 0
        
    cache_trans_dir = os.path.join(os.path.expanduser("~"), ".cache", "smart-editor", "transcripts")
    os.makedirs(cache_trans_dir, exist_ok=True)
    
    trans_key_str = f"{audio_size}_{model_size}_{language}_{beam_size}"
    trans_cache_key = hashlib.md5(trans_key_str.encode('utf-8')).hexdigest()
    trans_cache_path = os.path.join(cache_trans_dir, f"{trans_cache_key}.json")
    
    if os.path.exists(trans_cache_path):
        logger.info(f"Carregando transcrição do cache local: {trans_cache_path}")
        if progress_callback:
            progress_callback(0.75, "Transcrição carregada instantaneamente do cache local! ✓")
        try:
            with open(trans_cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao ler cache de transcrição: {e}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper não instalado. Execute setup.bat.")

    # ── Número ótimo de threads CPU ────────────────────────────────────
    cpu_count = multiprocessing.cpu_count()
    cpu_threads = max(4, min(cpu_count, 8))   # entre 4 e 8 threads

    cache_key = f"{model_size}_{cpu_threads}"

    if cache_key not in _model_cache:
        if progress_callback:
            progress_callback(0.02, f"Carregando modelo Whisper ({model_size})...")
        logger.info(f"Carregando modelo Whisper: {model_size} | threads={cpu_threads}")

        _model_cache[cache_key] = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",        # reduz uso de RAM sem perda perceptível
            cpu_threads=cpu_threads,    # usa mais núcleos do processador
            num_workers=2,              # workers paralelos para pré-processamento
            download_root=os.path.join(
                os.path.expanduser("~"), ".cache", "smart-editor", "whisper"
            )
        )
    else:
        if progress_callback:
            progress_callback(0.02, f"Modelo Whisper ({model_size}) já carregado ✓")

    model = _model_cache[cache_key]

    if progress_callback:
        progress_callback(0.05, "Transcrevendo áudio...")

    logger.info(f"Transcrevendo: {audio_path} | beam_size={beam_size}")

    # Prompt padrão se não foi fornecido
    if not initial_prompt:
        initial_prompt = "Conteúdo motivacional em português brasileiro."

    segments_gen, info = model.transcribe(
        audio_path,
        language=language if language else None,
        word_timestamps=word_timestamps,

        # ── Velocidade ─────────────────────────────────────────────────
        beam_size=beam_size,            # 1=greedey (2-3x mais rápido) | 5=preciso
        best_of=1 if beam_size == 1 else 5,
        temperature=0.0,               # determinístico, mais rápido
        condition_on_previous_text=False,  # False = mais rápido, menos contexto

        # ── VAD (remove silêncio automaticamente) ─────────────────────
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 400,
            "speech_pad_ms": 150,
            "threshold": 0.45,
        },

        # ── Qualidade ─────────────────────────────────────────────────
        initial_prompt=initial_prompt,
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.55,
    )

    segments = []
    total_duration = info.duration if hasattr(info, "duration") else None
    detected_lang  = getattr(info, "language", language)

    if progress_callback and detected_lang and detected_lang != language:
        progress_callback(0.06, f"Idioma detectado: {detected_lang}")

    for seg in segments_gen:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word":        w.word.strip(),
                    "start":       round(w.start, 3),
                    "end":         round(w.end, 3),
                    "probability": round(w.probability, 3),
                })

        segment_data = {
            "start":         round(seg.start, 3),
            "end":           round(seg.end, 3),
            "text":          seg.text.strip(),
            "words":         words,
            "avg_logprob":   round(seg.avg_logprob, 4) if hasattr(seg, "avg_logprob") else 0.0,
            "no_speech_prob":round(seg.no_speech_prob, 4) if hasattr(seg, "no_speech_prob") else 0.0,
        }

        # Filtrar não-fala e segmentos vazios
        if segment_data["text"] and segment_data["no_speech_prob"] < 0.6:
            segments.append(segment_data)

        # Progresso em tempo real
        if progress_callback and total_duration and total_duration > 0:
            progress = 0.05 + (seg.end / total_duration) * 0.7
            elapsed_pct = int(seg.end / total_duration * 100)
            progress_callback(
                min(progress, 0.75),
                f"Transcrevendo: {elapsed_pct}% — {seg.end:.0f}s / {total_duration:.0f}s — \"{seg.text.strip()[:50]}\""
            )

    logger.info(f"Transcricao completa: {len(segments)} segmentos")

    if progress_callback:
        progress_callback(0.75, f"Transcricao concluida: {len(segments)} segmentos")

    # Salvar no cache para evitar processar novamente no futuro
    try:
        with open(trans_cache_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)
        logger.info(f"Transcrição salva no cache: {trans_cache_path}")
    except Exception as e:
        logger.warning(f"Erro ao salvar cache de transcrição: {e}")

    return segments


def clear_model_cache():
    """Libera memória RAM descarregando modelos em cache."""
    global _model_cache
    _model_cache.clear()
    logger.info("Cache de modelos Whisper liberado")
