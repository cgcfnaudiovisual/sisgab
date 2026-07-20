from pathlib import Path
from scenedetect import detect, ContentDetector

def analyze_video_scenes(video_path, threshold=27.0):
    """
    Analisa o vídeo usando PySceneDetect (local) para encontrar cortes visuais (transições de cena).
    Retorna uma lista de clips formatada para o Smart Editor.
    """
    try:
        # Executa detecção local de cenas baseada em conteúdo
        scene_list = detect(str(Path(video_path).resolve()), ContentDetector(threshold=threshold))
        
        clips = []
        for idx, scene in enumerate(scene_list):
            start_sec = scene[0].get_seconds()
            end_sec = scene[1].get_seconds()
            duration = end_sec - start_sec
            
            # Formatar timecode amigável
            start_tc = scene[0].get_timecode()
            
            clips.append({
                "id": idx,
                "start": start_sec,
                "end": end_sec,
                "duration": duration,
                "score": 10.0,  # Score máximo padrão para cortes visuais exatos
                "category": "🎬 Cena",
                "reason": f"Cena {idx + 1} (Início: {start_tc})",
                "text": f"[Cena {idx + 1}] Trecho visual analisado localmente via PySceneDetect.",
                "speaker": "Cena Visual"
            })
            
        return clips
    except Exception as e:
        raise RuntimeError(f"Erro no PySceneDetect: {e}")
