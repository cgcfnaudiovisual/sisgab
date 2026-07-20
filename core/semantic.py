import logging
import os
import math
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# Cache do modelo para não recarregar entre chamadas
_classifier = None

def load_classifier(progress_callback: Optional[Callable] = None):
    """Carrega o modelo BART zero-shot (baixa ~1.5GB na primeira vez)"""
    global _classifier
    if _classifier is not None:
        return _classifier
    
    try:
        from transformers import pipeline
    except ImportError:
        raise RuntimeError("transformers não instalado. Execute setup.bat.")
    
    if progress_callback:
        progress_callback(0.02, "Carregando modelo de análise semântica (primeira vez: ~1.5GB)...")
    
    logger.info("Carregando BART zero-shot classifier...")
    
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "smart-editor", "bart")
    
    _classifier = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli",
        device=-1,  # CPU
        cache_dir=cache_dir
    )
    
    logger.info("Modelo semântico carregado com sucesso")
    return _classifier


def score_segments(
    segments: List[Dict[str, Any]],
    theme: str = "conteúdo motivacional, inspiração, superação pessoal",
    batch_size: int = 8,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Avalia cada segmento semanticamente e atribui um score de 0-10.
    
    Usa BART zero-shot classification para determinar relevância em relação ao tema.
    
    Args:
        segments: Segmentos com texto transcrito
        theme: Tema para avaliar relevância (pode ser qualquer coisa)
        batch_size: Segmentos processados por vez
        progress_callback: Função de progresso(0.0-1.0, mensagem)
    
    Returns:
        Segmentos com campos adicionais: score, category, score_reason
    """
    classifier = load_classifier(progress_callback)
    
    # Labels para classificação zero-shot
    candidate_labels = [
        f"conteúdo muito relevante sobre {theme}",
        f"conteúdo moderadamente relevante sobre {theme}",
        f"conteúdo pouco relevante sobre {theme}",
        "conteúdo irrelevante, conversa casual, ou transição"
    ]
    
    # Mapear score baseado no label vencedor
    label_scores = {
        0: (8.5, 10.0),   # muito relevante
        1: (6.0, 8.4),    # moderadamente
        2: (3.5, 5.9),    # pouco relevante
        3: (0.0, 3.4),    # irrelevante
    }
    
    total = len(segments)
    scored = []
    
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        
        if not text or len(text) < 10:
            seg = seg.copy()
            seg["score"] = 0.0
            seg["category"] = "Vazio"
            seg["score_reason"] = "Segmento muito curto"
            scored.append(seg)
            continue
        
        try:
            # Truncar texto muito longo (BART tem limite de tokens)
            text_truncated = text[:512]
            
            result = classifier(
                text_truncated,
                candidate_labels,
                multi_label=False
            )
            
            # Índice do label com maior score
            top_label = result["labels"][0]
            top_score = result["scores"][0]
            
            # Determinar índice do label vencedor
            label_idx = candidate_labels.index(top_label)
            
            # Calcular score final (0-10)
            score_range = label_scores[label_idx]
            # Interpolar dentro do range baseado na confiança do modelo
            final_score = score_range[0] + (score_range[1] - score_range[0]) * top_score
            
            # Determinar categoria legível
            categories = [
                "💎 Destaque forte",
                "⭐ Bom conteúdo",
                "📌 Conteúdo médio",
                "⬇️ Pouco relevante"
            ]
            category = categories[label_idx]
            
            seg = seg.copy()
            seg["score"] = round(final_score, 2)
            seg["category"] = category
            seg["score_reason"] = f"Confiança: {top_score:.0%}"
            
        except Exception as e:
            logger.warning(f"Erro ao avaliar segmento {i}: {e}")
            seg = seg.copy()
            seg["score"] = 5.0
            seg["category"] = "Erro na análise"
            seg["score_reason"] = str(e)[:100]
        
        scored.append(seg)
        
        if progress_callback and total > 0:
            progress = 0.1 + (i / total) * 0.85
            progress_callback(progress, f"Analisando segmento {i+1}/{total}...")
    
    if progress_callback:
        progress_callback(1.0, f"Análise semântica completa: {len(scored)} segmentos avaliados")
    
    return scored


def score_segments_fast(
    segments: List[Dict[str, Any]],
    theme: str = "motivacional",
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Versão rápida baseada em palavras-chave (fallback sem modelo pesado).
    Menos precisa mas muito mais rápida.
    """
    # Palavras-chave motivacionais (expandidas automaticamente pelo tema)
    base_keywords = {
        "muito_relevante": [
            "acreditar", "superar", "conquista", "persistência", "determinação",
            "motivação", "sucesso", "inspiração", "mudança", "transformação",
            "potencial", "sonho", "objetivo", "meta", "propósito", "força",
            "coragem", "atitude", "mindset", "mentalidade", "crescimento",
            "nunca desistir", "não desistir", "continuar", "persistir",
            "resiliência", "vencer", "vitória", "campeão", "excelência"
        ],
        "relevante": [
            "trabalho", "esforço", "foco", "disciplina", "hábito", "rotina",
            "aprender", "evolução", "melhoria", "estratégia", "resultado",
            "oportunidade", "desafio", "dificuldade", "aprendizado"
        ],
        "irrelevante": [
            "né", "então", "bom", "tá", "aí", "oi", "olá", "pessoal",
            "hoje", "aqui", "vamos", "vou", "começa", "continua"
        ]
    }
    
    # Adicionar palavras do tema customizado
    theme_words = theme.lower().split(", ")
    base_keywords["muito_relevante"].extend(theme_words)
    
    scored = []
    for seg in segments:
        text = seg.get("text", "").lower()
        
        score = 5.0  # base
        category = "📌 Conteúdo médio"
        
        # Contar ocorrências de palavras-chave
        count_alto = sum(1 for kw in base_keywords["muito_relevante"] if kw in text)
        count_med = sum(1 for kw in base_keywords["relevante"] if kw in text)
        count_irr = sum(1 for kw in base_keywords["irrelevante"] if kw in text)
        
        # Calcular score ponderado
        word_count = max(len(text.split()), 1)
        score_raw = (count_alto * 2.0 + count_med * 0.8 - count_irr * 0.3) / (word_count / 10)
        score = max(0, min(10, 4.0 + score_raw * 2.5))
        
        # Ajuste: segmentos mais longos e coerentes ganham bonus
        duration = seg.get("end", 0) - seg.get("start", 0)
        if duration > 10:
            score = min(10, score + 0.3)
        
        if score >= 8:
            category = "💎 Destaque forte"
        elif score >= 6.5:
            category = "⭐ Bom conteúdo"
        elif score >= 4:
            category = "📌 Conteúdo médio"
        else:
            category = "⬇️ Pouco relevante"
        
        seg = seg.copy()
        seg["score"] = round(score, 2)
        seg["category"] = category
        seg["score_reason"] = f"Palavras-chave: {count_alto} fortes, {count_med} médias"
        scored.append(seg)
        
        if progress_callback:
            progress_callback(0.1 + (len(scored) / len(segments)) * 0.85, 
                            f"Analisando... {len(scored)}/{len(segments)}")
    
    if progress_callback:
        progress_callback(1.0, "Análise por palavras-chave concluída")
    
    return scored


def score_segments_gemini(
    segments: List[Dict[str, Any]],
    theme: str = "conteúdo motivacional, inspiração, superação pessoal",
    api_key: str = "",
    model_name: str = "gemini-3.5-flash",
    progress_callback: Optional[Callable] = None,
    diarization_mode: str = "gemini"
) -> List[Dict[str, Any]]:
    """
    Analisa os segmentos utilizando a API do Gemini 1.5 Flash na nuvem.
    Envia a transcrição inteira estruturada em um único prompt para ser ultra-rápido.
    """
    if not api_key:
        raise ValueError("Chave de API do Gemini não configurada.")
        
    if progress_callback:
        progress_callback(0.1, "Preparando transcrição para enviar ao Gemini...")
        
    # Construir texto estruturado com IDs
    transcript_text = []
    for idx, seg in enumerate(segments):
        speaker = seg.get("speaker", "Locutor")
        text = seg.get("text", "").strip()
        transcript_text.append(f"[{idx}] {speaker}: {text}")
        
    full_transcript = "\n".join(transcript_text)
    
    diarization_instruction = ""
    diarization_fields = ""
    if diarization_mode == "gemini":
        diarization_instruction = """
ADICIONAL (DIARIZAÇÃO POR IA): Analise o fluxo do diálogo na transcrição e identifique de forma consistente quem está falando cada segmento. Atribua um rótulo como "Speaker A", "Speaker B", "Speaker C", etc. para cada segmento com base no contexto das perguntas e respostas. Garanta consistência lógica ao longo de toda a conversa (a mesma pessoa deve ter o mesmo rótulo).
"""
        diarization_fields = """
- "speaker": O nome do locutor deduzido pelo contexto (ex: "Speaker A", "Speaker B"), mantendo consistência absoluta em todas as falas da mesma pessoa.
"""

    example_return = """[
  {"id": 0, "score": 9.2, "category": "💎 Destaque forte", "reason": "Frase de forte impacto motivacional sobre superar limites."%s},
  {"id": 15, "score": 6.8, "category": "⭐ Bom conteúdo", "reason": "Explicação relevante sobre abnegação nos estudos."%s}
]""" % ((', "speaker": "Speaker A"', ', "speaker": "Speaker B"') if diarization_mode == "gemini" else ("", ""))

    prompt = f"""Você é um especialista em edição de vídeos e cortes para redes sociais.
Sua tarefa é analisar a transcrição de um vídeo abaixo e identificar todos os segmentos relevantes em relação ao tema: "{theme}".
Os segmentos estão no formato "[ID] Locutor: Texto".
{diarization_instruction}
Regras de pontuação (de 0.0 a 10.0):
- 8.5 a 10.0: Frases de forte impacto, ensinamentos sobre o tema, abnegação, disciplina, superação de dificuldades, conquistas ou momentos inspiradores.
- 6.5 a 8.4: Bom conteúdo, explicações ou reflexões interessantes sobre o tema.
- 4.0 a 6.4: Conversas gerais de transição ou contexto geral.
- 0.0 a 3.9: Agradecimentos, falas casuais fora do tema, silêncios, ou sem relevância.

ATENÇÃO (MUITO IMPORTANTE): Para reduzir o tamanho da resposta e evitar timeouts, você deve retornar no JSON APENAS os segmentos que tenham score igual ou superior a 5.0 (relevância mínima, moderada ou forte). Omitir qualquer segmento que seja irrelevante (score abaixo de 5.0).

Você deve responder APENAS com um objeto JSON (um array de objetos), sem blocos de código markdown (como ```json) ou explicações adicionais.
Cada objeto no array deve conter exatamente estes campos:
- "id": O número inteiro do ID do segmento.
- "score": A nota de 5.0 a 10.0 (número float).
- "category": Uma das categorias: "💎 Destaque forte", "⭐ Bom conteúdo", "📌 Conteúdo médio".
- "reason": Breve justificativa de 1 frase para a nota.{diarization_fields}

Exemplo de retorno esperado:
{example_return}

Transcrição:
{full_transcript}
"""

    if progress_callback:
        progress_callback(0.4, "Enviando dados para a API do Gemini...")
        
    import urllib.request
    import json
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
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
            progress_callback(0.7, "Gemini processando o contexto do vídeo...")
            
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
        # Extrair texto da resposta
        text_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Limpar markdown se houver
        if text_response.startswith("```"):
            lines = text_response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            text_response = "\n".join(lines).strip()
            
        scores_list = json.loads(text_response)
        
        # Inicializar todos os segmentos com score baixo e default
        scored_segments = []
        for idx, seg in enumerate(segments):
            seg_copy = seg.copy()
            seg_copy["score"] = 3.0
            seg_copy["category"] = "⬇️ Pouco relevante"
            seg_copy["score_reason"] = "Trecho secundário ou de transição"
            scored_segments.append(seg_copy)
            
        # Mapear as notas recebidas do Gemini
        for item in scores_list:
            try:
                idx = int(item["id"])
                if 0 <= idx < len(scored_segments):
                    scored_segments[idx]["score"] = round(float(item.get("score", 5.0)), 2)
                    scored_segments[idx]["category"] = item.get("category", "📌 Conteúdo médio")
                    scored_segments[idx]["score_reason"] = item.get("reason", "Selecionado pelo Gemini")
                    if diarization_mode == "gemini" and "speaker" in item:
                        scored_segments[idx]["speaker"] = str(item["speaker"])
            except Exception as item_err:
                logger.warning(f"Erro ao mapear item do Gemini: {item_err}")
            
        if progress_callback:
            progress_callback(1.0, "Análise de contexto pelo Gemini concluída!")
            
        return scored_segments
        
    except Exception as e:
        logger.error(f"Erro ao chamar API do Gemini: {e}")
        if progress_callback:
            progress_callback(1.0, f"Falha na API do Gemini: {e}. Usando keywords como fallback...")
        return score_segments_fast(segments, theme, progress_callback)
