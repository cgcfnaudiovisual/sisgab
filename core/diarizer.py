import logging
import os
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


def diarize(
    audio_path: str,
    hf_token: Optional[str] = None,
    num_speakers: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Identifica quem está falando em cada momento do áudio (diarização).
    
    Se hf_token fornecido: usa pyannote.audio (melhor qualidade)
    Se não: retorna lista vazia (segmentos não terão speaker definido)
    
    Args:
        audio_path: Caminho do arquivo WAV 16kHz mono
        hf_token: Token HuggingFace (opcional, gratuito em hf.co)
        num_speakers: Número de speakers esperado (None = autodetectar)
        progress_callback: Função de progresso(0.0-1.0, mensagem)
    
    Returns:
        Lista de turnos: [{start, end, speaker}]
    """
    if not hf_token:
        logger.info("Token HuggingFace não configurado. Diarização desativada.")
        if progress_callback:
            progress_callback(1.0, "Diarização pulada (sem token HuggingFace)")
        return []
    
    try:
        from pyannote.audio import Pipeline
        import torch
    except ImportError:
        logger.warning("pyannote.audio não instalado. Diarização desativada.")
        if progress_callback:
            progress_callback(1.0, "pyannote não instalado")
        return []
    
    if progress_callback:
        progress_callback(0.1, "Carregando modelo de diarização...")
    
    logger.info("Carregando pipeline de diarização pyannote...")
    
    try:
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token,
                cache_dir=os.path.join(os.path.expanduser("~"), ".cache", "smart-editor", "pyannote")
            )
        except TypeError:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
                cache_dir=os.path.join(os.path.expanduser("~"), ".cache", "smart-editor", "pyannote")
            )
        
        # Configurar para CPU
        pipeline = pipeline.to(torch.device("cpu"))
        
        if progress_callback:
            progress_callback(0.3, "Analisando speakers no áudio...")
        
        # Executar diarização
        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers
        
        diarization = pipeline(audio_path, **kwargs)
        
        # Converter resultado para lista de dicionários
        turns = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            turns.append({
                "start": round(turn.start, 3),
                "end": round(turn.end, 3),
                "speaker": speaker
            })
        
        # Normalizar nomes dos speakers (SPEAKER_00 → Speaker A, etc.)
        unique_speakers = sorted(set(t["speaker"] for t in turns))
        speaker_map = {}
        for i, sp in enumerate(unique_speakers):
            label = chr(65 + i)  # A, B, C, D...
            speaker_map[sp] = f"Speaker {label}"
        
        for turn in turns:
            turn["speaker"] = speaker_map[turn["speaker"]]
        
        logger.info(f"Diarização completa: {len(unique_speakers)} speakers, {len(turns)} turnos")
        
        if progress_callback:
            progress_callback(1.0, f"Diarização concluída: {len(unique_speakers)} pessoa(s) identificada(s)")
        
        return turns
    
    except Exception as e:
        logger.error(f"Erro na diarização: {e}")
        if progress_callback:
            progress_callback(1.0, f"Erro na diarização: {str(e)[:100]}")
        return []


def assign_speakers_to_segments(
    segments: List[Dict[str, Any]],
    turns: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Atribui o speaker correto a cada segmento de transcrição baseado nos turnos de diarização.
    Usa timestamps por palavra (word-level) se disponíveis para fatiar o segmento
    exatamente onde há mudança de locutor.
    Se não houver palavras disponíveis, faz fallback por máxima sobreposição do segmento completo.
    
    Args:
        segments: Segmentos da transcrição (com start, end, text, words)
        turns: Turnos de diarização (com start, end, speaker)
    
    Returns:
        Segmentos atualizados e fatiados precisamente com campo 'speaker'
    """
    if not turns:
        # Sem diarização: todos os segmentos ficam como Speaker Desconhecido
        for seg in segments:
            seg["speaker"] = "Speaker ?"
        return segments
    
    def get_speaker_at(time_sec: float) -> str:
        # Encontra o speaker ativo nesse timestamp
        for turn in turns:
            if turn["start"] <= time_sec <= turn["end"]:
                return turn["speaker"]
        # Se não achar correspondência exata, tenta encontrar o mais próximo
        best_speaker = "Speaker ?"
        best_overlap = 0.0
        for turn in turns:
            overlap = max(0.0, min(time_sec + 0.1, turn["end"]) - max(time_sec - 0.1, turn["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]
        return best_speaker

    precise_segments = []
    
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Fallback para overlap do segmento inteiro se não tiver palavras
            best_speaker = "Speaker ?"
            best_overlap = 0.0
            seg_start = seg["start"]
            seg_end = seg["end"]
            for turn in turns:
                overlap_start = max(seg_start, turn["start"])
                overlap_end = min(seg_end, turn["end"])
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = turn["speaker"]
            seg["speaker"] = best_speaker
            precise_segments.append(seg)
            continue
            
        # Mapear cada palavra para o locutor ativo na metade do seu tempo
        word_speakers = []
        for w in words:
            mid_time = (w["start"] + w["end"]) / 2.0
            word_speakers.append(get_speaker_at(mid_time))
            
        # Agrupar palavras consecutivas que pertencem ao mesmo locutor
        current_speaker = word_speakers[0]
        current_words = [words[0]]
        
        for idx in range(1, len(words)):
            w = words[idx]
            sp = word_speakers[idx]
            if sp == current_speaker:
                current_words.append(w)
            else:
                # Mudança de locutor! Salva o bloco anterior
                text_block = " ".join(wd["word"] for wd in current_words).strip()
                if text_block:
                    precise_segments.append({
                        "start": current_words[0]["start"],
                        "end": current_words[-1]["end"],
                        "text": text_block,
                        "words": current_words,
                        "speaker": current_speaker,
                        "avg_logprob": seg.get("avg_logprob", 0.0),
                        "no_speech_prob": seg.get("no_speech_prob", 0.0),
                    })
                current_speaker = sp
                current_words = [w]
                
        # Salvar o último bloco
        text_block = " ".join(wd["word"] for wd in current_words).strip()
        if text_block:
            precise_segments.append({
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "text": text_block,
                "words": current_words,
                "speaker": current_speaker,
                "avg_logprob": seg.get("avg_logprob", 0.0),
                "no_speech_prob": seg.get("no_speech_prob", 0.0),
            })
            
    return precise_segments
