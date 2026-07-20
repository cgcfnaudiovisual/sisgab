import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def group_segments(
    segments: List[Dict[str, Any]],
    max_gap: float = 1.5,
    min_duration: float = 8.0,
    max_duration: float = 90.0,
    padding_start: float = 0.3,
    padding_end: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Agrupa segmentos contíguos em blocos coerentes para corte.
    
    Regras:
    - Segmentos com gap <= max_gap e pertencentes ao mesmo locutor são unidos
    - Blocos menores que min_duration são descartados
    - Blocos maiores que max_duration são divididos em pontos de pausa natural
    - Padding adicionado no início e fim para evitar corte brusco
    
    Args:
    """
    if not segments:
        return []

    groups = []
    current_group = [segments[0]]

    for seg in segments[1:]:
        prev = current_group[-1]
        gap = seg["start"] - prev["end"]
        
        # Verificar se o locutor mudou (se houver identificação ativa)
        speaker_changed = (seg.get("speaker") != prev.get("speaker"))

        if gap <= max_gap and not speaker_changed:
            current_group.append(seg)
        else:
            groups.append(current_group)
            current_group = [seg]

    groups.append(current_group)

    # Converter grupos em clips
    clips = []
    for group in groups:
        clip = _group_to_clip(group, padding_start, padding_end)
        duration = clip["end"] - clip["start"]
        
        if duration < min_duration:
            continue  # descarta clips muito curtos

        if duration > max_duration:
            # Divide o grupo de forma inteligente respeitando pontuações e pausas
            sub_clips = _split_long_group_contextual(group, max_duration, padding_start, padding_end, min_duration)
            clips.extend(sub_clips)
        else:
            clips.append(clip)

    logger.info(f"Agrupamento inteligente: {len(segments)} segmentos → {len(clips)} clips")
    return clips


def _group_to_clip(group: List[Dict], padding_start: float, padding_end: float) -> Dict[str, Any]:
    """Converte uma lista de segmentos em um único clip"""
    start = max(0.0, group[0]["start"] - padding_start)
    end = group[-1]["end"] + padding_end
    text = " ".join(s["text"] for s in group).strip()

    # Categoria e score do segmento com maior relevância (peak score)
    best_seg = max(group, key=lambda s: s.get("score", 0.0))
    peak_score = best_seg.get("score", 5.0)

    # Speaker mais frequente no grupo
    from collections import Counter
    speaker_counts = Counter(s.get("speaker", "Speaker ?") for s in group)
    main_speaker = speaker_counts.most_common(1)[0][0]

    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(end - start, 3),
        "text": text,
        "score": round(peak_score, 2),
        "category": best_seg.get("category", "📌 Conteúdo médio"),
        "speaker": main_speaker,
        "segment_count": len(group),
        "raw_segments": group,
    }


def _split_long_group_contextual(
    group: List[Dict],
    max_duration: float,
    padding_start: float,
    padding_end: float,
    min_duration: float
) -> List[Dict[str, Any]]:
    """
    Divide um grupo longo em sub-clips de forma contextual.
    Tenta quebrar os blocos em finais de frase reais (marcados com ".", "!" ou "?") 
    e silêncios naturais, evitando cortes no meio de uma frase.
    """
    sub_clips = []
    current = []
    current_dur = 0.0

    for i, seg in enumerate(group):
        seg_dur = seg["end"] - seg["start"]
        text = seg.get("text", "").strip()
        ends_sentence = text.endswith((".", "!", "?")) if text else False

        # Caso adicionar esse segmento estoure a duração máxima rígida
        if current_dur + seg_dur > max_duration and current:
            clip = _group_to_clip(current, padding_start, padding_end)
            if clip["duration"] >= min_duration:
                sub_clips.append(clip)
            current = [seg]
            current_dur = seg_dur
        else:
            current.append(seg)
            current_dur += seg_dur

            # Ponto de quebra inteligente: se atingiu a duração mínima, o segmento atual
            # termina uma ideia/frase completa, e há um próximo segmento pendente:
            if current_dur >= min_duration and ends_sentence and i < len(group) - 1:
                next_seg = group[i + 1]
                next_seg_dur = next_seg["end"] - next_seg["start"]
                gap_to_next = next_seg["start"] - seg["end"]

                # Quebramos de forma preventiva se o próximo segmento levaria a duração
                # para muito perto do teto máximo (80%) ou se houver um silêncio considerável (> 1.2s)
                if current_dur + next_seg_dur > max_duration * 0.8 or gap_to_next > 1.2:
                    clip = _group_to_clip(current, padding_start, padding_end)
                    sub_clips.append(clip)
                    current = []
                    current_dur = 0.0

    if current:
        clip = _group_to_clip(current, padding_start, padding_end)
        if clip["duration"] >= min_duration:
            sub_clips.append(clip)

    return sub_clips


def filter_clips(
    clips: List[Dict[str, Any]],
    min_score: float = 6.5,
) -> List[Dict[str, Any]]:
    """
    Filtra clips pelo score mínimo e ordena por score decrescente.
    
    Args:
        clips: Lista de clips agrupados
        min_score: Score mínimo para incluir no resultado
    
    Returns:
        Clips filtrados, ordenados do melhor para o pior
    """
    filtered = [c for c in clips if c.get("score", 0) >= min_score]
    filtered.sort(key=lambda c: c["score"], reverse=True)

    logger.info(
        f"Filtro (score>={min_score}): {len(clips)} clips → {len(filtered)} selecionados"
    )
    return filtered


def get_stats(all_clips: List[Dict], selected_clips: List[Dict]) -> Dict[str, Any]:
    """Retorna estatísticas do processamento para exibir na GUI"""
    total_dur_all = sum(c["duration"] for c in all_clips)
    total_dur_sel = sum(c["duration"] for c in selected_clips)

    scores = [c["score"] for c in all_clips] if all_clips else [0]

    return {
        "total_clips": len(all_clips),
        "selected_clips": len(selected_clips),
        "total_duration_all": round(total_dur_all, 1),
        "total_duration_selected": round(total_dur_sel, 1),
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "max_score": round(max(scores), 2) if scores else 0,
        "min_score": round(min(scores), 2) if scores else 0,
        "reduction_pct": round((1 - total_dur_sel / total_dur_all) * 100, 1) if total_dur_all > 0 else 0,
    }
