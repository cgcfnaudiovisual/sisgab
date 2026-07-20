import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


def _sort_clips(clips: List[Dict[str, Any]], sort_by: str = "chronological") -> List[Dict[str, Any]]:
    """Ordena os clips com base no critério de exportação escolhido"""
    if sort_by == "relevance":
        # Por relevância (melhores scores primeiro)
        return sorted(clips, key=lambda c: c.get("score", 0.0), reverse=True)
    elif sort_by == "speaker":
        # Agrupado por speaker, e cronológico dentro de cada speaker
        return sorted(clips, key=lambda c: (str(c.get("speaker", "Speaker ?")), c["start"]))
    else:
        # Default: cronológico (sequência natural)
        return sorted(clips, key=lambda c: c["start"])


def _to_fcpxml_time(seconds: float, fps_num: int = 25, fps_den: int = 1) -> str:
    """
    Converte segundos para o formato de tempo do FCPXML.
    Usa frações racionais exatas: ex: "125/25s" = 5 segundos a 25fps
    """
    # Arredondar para frame exato
    total_frames = round(seconds * fps_num / fps_den)
    if total_frames == 0:
        return "0s"
    # Simplificar fração se possível
    from math import gcd
    num = total_frames
    den = fps_num // fps_den
    divisor = gcd(num, den)
    return f"{num // divisor}/{den // divisor}s"


def _frame_duration(fps: float) -> str:
    """Retorna frameDuration no formato FCPXML para um dado FPS"""
    common = {
        23.976: "1001/24000s",
        24.0:   "100/2400s",
        25.0:   "100/2500s",
        29.97:  "1001/30000s",
        30.0:   "100/3000s",
        50.0:   "100/5000s",
        59.94:  "1001/60000s",
        60.0:   "100/6000s",
    }
    # Encontrar FPS mais próximo
    closest = min(common.keys(), key=lambda f: abs(f - fps))
    return common[closest]


def export_fcpxml(
    clips: List[Dict[str, Any]],
    video_info: Dict[str, Any],
    output_path: str,
    project_name: str = "Smart Editor Highlights",
    sort_by: str = "chronological",
) -> str:
    """
    Gera arquivo FCPXML 1.10 compatível com DaVinci Resolve.
    
    Cada clip selecionado vira um evento na timeline com:
    - Referência exata ao arquivo MP4 original
    - Timecodes de entrada e saída precisos
    - Marker com score e texto transcrito
    - Cor do clip baseada no score
    
    Args:
        clips: Lista de clips selecionados (já filtrados e ordenados)
        video_info: Informações do vídeo (path, fps, width, height, duration)
        output_path: Caminho onde salvar o .fcpxml
        project_name: Nome do projeto na timeline
        sort_by: Critério de ordenação ('chronological', 'relevance', 'speaker')
    
    Returns:
        Caminho do arquivo gerado
    """
    fps = video_info.get("fps", 25.0)
    width = video_info.get("width", 1920)
    height = video_info.get("height", 1080)
    video_path = video_info.get("path", "")
    video_duration = video_info.get("duration", 0.0)
    video_name = Path(video_path).stem

    # Determinar frameDuration
    frame_dur = _frame_duration(fps)
    fps_num = round(fps)

    # URI do arquivo de vídeo (para FCPXML precisa ser file:// URI)
    abs_path = str(Path(video_path).resolve())
    # No Windows: file:///C:/path/to/file.mp4
    file_uri = "file:///" + abs_path.replace("\\", "/").lstrip("/")

    # Calcular duração total da timeline (soma dos clips)
    timeline_duration = sum(c["duration"] for c in clips)

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")

    # Mapa de cores por score (DaVinci Resolve suporta labels coloridos)
    def clip_color(score: float) -> str:
        if score >= 8.5:
            return "Green"
        elif score >= 7.0:
            return "Yellow"
        elif score >= 5.5:
            return "Orange"
        else:
            return "Red"

    # Gerar XML
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<!DOCTYPE fcpxml>')
    lines.append('<fcpxml version="1.10">')
    lines.append('')
    lines.append('  <resources>')
    lines.append(f'    <format id="r1" name="FFVideoFormat{height}p{fps_num}"')
    lines.append(f'           frameDuration="{frame_dur}"')
    lines.append(f'           width="{width}" height="{height}"/>')
    lines.append('')
    lines.append(f'    <asset id="r2" name="{_xml_escape(video_name)}"')
    lines.append(f'           start="0s"')
    lines.append(f'           duration="{_to_fcpxml_time(video_duration, fps_num)}"')
    lines.append( '           hasVideo="1" hasAudio="1" audioSources="1"')
    lines.append( '           audioChannels="2" audioRate="44100">')
    lines.append(f'      <media-rep kind="original-media" src="{file_uri}"/>')
    lines.append( '    </asset>')
    lines.append('  </resources>')
    lines.append('')
    lines.append('  <library>')
    lines.append(f'    <event name="{_xml_escape(project_name)}" uid="smart-editor-event-001">')
    lines.append(f'      <project name="{_xml_escape(project_name)}" uid="smart-editor-proj-001">')
    lines.append(f'        <sequence format="r1"')
    lines.append(f'                  duration="{_to_fcpxml_time(timeline_duration, fps_num)}"')
    lines.append( '                  tcStart="0s" tcFormat="NDF"')
    lines.append( '                  audioLayout="stereo" audioRate="44100">')
    lines.append('          <spine>')
 
    offset = 0.0
    clips_sorted = _sort_clips(clips, sort_by=sort_by)
    for i, clip in enumerate(clips_sorted):
        clip_start = clip["start"]
        clip_dur = clip["duration"]
        score = clip.get("score", 0.0)
        speaker = clip.get("speaker", "Speaker ?")
        text_preview = clip.get("text", "")[:120].replace("\n", " ")
        category = clip.get("category", "")
        color = clip_color(score)
        clip_name = f"[{score:.1f}] {speaker} — {category}"

        lines.append(f'')
        lines.append(f'            <asset-clip name="{_xml_escape(clip_name)}"')
        lines.append(f'                  ref="r2"')
        lines.append(f'                  offset="{_to_fcpxml_time(offset, fps_num)}"')
        lines.append(f'                  duration="{_to_fcpxml_time(clip_dur, fps_num)}"')
        lines.append(f'                  start="{_to_fcpxml_time(clip_start, fps_num)}">')
        lines.append(f'              <note>{_xml_escape(text_preview)}</note>')
        lines.append(f'              <marker start="{_to_fcpxml_time(clip_start, fps_num)}"')
        lines.append(f'                      duration="{_to_fcpxml_time(1.0, fps_num)}"')
        lines.append(f'                      value="{_xml_escape(f"Score {score:.1f} | {speaker}")}"/>')
        lines.append(f'            </asset-clip>')

        offset += clip_dur

    lines.append('          </spine>')
    lines.append('        </sequence>')
    lines.append('      </project>')
    lines.append('    </event>')
    lines.append('  </library>')
    lines.append('</fcpxml>')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"FCPXML exportado: {output_path} ({len(clips)} clips)")
    return output_path


def export_fcpxml_multi(
    clips_by_video: List[Dict[str, Any]],
    output_path: str,
    project_name: str = "Smart Editor Highlights",
    sort_by: str = "chronological",
) -> str:
    """
    Versão para múltiplos vídeos: todos os clips de todos os vídeos
    numa única timeline FCPXML.
    
    Args:
        clips_by_video: Lista de {video_info, clips}
        output_path: Caminho de saída
        project_name: Nome do projeto
        sort_by: Critério de ordenação
    
    Returns:
        Caminho do FCPXML gerado
    """
    # Usar o fps/resolução do primeiro vídeo como referência
    first_vi = clips_by_video[0]["video_info"]
    fps = first_vi.get("fps", 25.0)
    width = first_vi.get("width", 1920)
    height = first_vi.get("height", 1080)
    fps_num = round(fps)
    frame_dur = _frame_duration(fps)

    total_clips = sum(len(v["clips"]) for v in clips_by_video)
    total_duration = sum(
        c["duration"] for v in clips_by_video for c in v["clips"]
    )

    def clip_color(score: float) -> str:
        if score >= 8.5: return "Green"
        elif score >= 7.0: return "Yellow"
        elif score >= 5.5: return "Orange"
        else: return "Red"

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<!DOCTYPE fcpxml>')
    lines.append('<fcpxml version="1.10">')
    lines.append('  <resources>')
    lines.append(f'    <format id="r1" name="FFVideoFormat{height}p{fps_num}"')
    lines.append(f'           frameDuration="{frame_dur}" width="{width}" height="{height}"/>')

    # Um asset por vídeo
    for vid_idx, vid_data in enumerate(clips_by_video):
        vi = vid_data["video_info"]
        vid_path = vi.get("path", "")
        vid_dur = vi.get("duration", 0.0)
        vid_name = Path(vid_path).stem
        abs_path = str(Path(vid_path).resolve())
        file_uri = "file:///" + abs_path.replace("\\", "/").lstrip("/")
        asset_id = f"r{vid_idx + 2}"

        lines.append(f'    <asset id="{asset_id}" name="{_xml_escape(vid_name)}"')
        lines.append(f'           start="0s" duration="{_to_fcpxml_time(vid_dur, fps_num)}"')
        lines.append(f'           hasVideo="1" hasAudio="1" audioSources="1"')
        lines.append(f'           audioChannels="2" audioRate="44100">')
        lines.append(f'      <media-rep kind="original-media" src="{file_uri}"/>')
        lines.append(f'    </asset>')

    lines.append('  </resources>')
    lines.append('  <library>')
    lines.append(f'    <event name="{_xml_escape(project_name)}">')
    lines.append(f'      <project name="{_xml_escape(project_name)}">')
    lines.append(f'        <sequence format="r1" duration="{_to_fcpxml_time(total_duration, fps_num)}"')
    lines.append( '                  tcStart="0s" tcFormat="NDF"')
    lines.append( '                  audioLayout="stereo" audioRate="44100">')
    lines.append('          <spine>')

    offset = 0.0
    for vid_idx, vid_data in enumerate(clips_by_video):
        asset_id = f"r{vid_idx + 2}"
        clips_sorted = _sort_clips(vid_data["clips"], sort_by=sort_by)
        for clip in clips_sorted:
            score = clip.get("score", 0.0)
            speaker = clip.get("speaker", "Speaker ?")
            category = clip.get("category", "")
            clip_name = f"[{score:.1f}] {speaker} — {category}"
            color = clip_color(score)
            text_preview = clip.get("text", "")[:120].replace("\n", " ")

            lines.append(f'            <asset-clip name="{_xml_escape(clip_name)}"')
            lines.append(f'                  ref="{asset_id}"')
            lines.append(f'                  offset="{_to_fcpxml_time(offset, fps_num)}"')
            lines.append(f'                  duration="{_to_fcpxml_time(clip["duration"], fps_num)}"')
            lines.append(f'                  start="{_to_fcpxml_time(clip["start"], fps_num)}">')
            lines.append(f'              <note>{_xml_escape(text_preview)}</note>')
            lines.append(f'            </asset-clip>')

            offset += clip["duration"]

    lines.append('          </spine>')
    lines.append('        </sequence>')
    lines.append('      </project>')
    lines.append('    </event>')
    lines.append('  </library>')
    lines.append('</fcpxml>')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"FCPXML multi-vídeo: {output_path} ({total_clips} clips)")
    return output_path


def export_srt(
    clips: List[Dict[str, Any]],
    output_path: str,
    sort_by: str = "chronological",
) -> str:
    """
    Exporta os melhores trechos como arquivo SRT (legenda).
    Útil para revisar o conteúdo selecionado antes de cortar.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def fmt_time(s: float) -> str:
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = int(s % 60)
        ms = int((s % 1) * 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    clips_sorted = _sort_clips(clips, sort_by=sort_by)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, clip in enumerate(clips_sorted, 1):
            f.write(f"{i}\n")
            f.write(f"{fmt_time(clip['start'])} --> {fmt_time(clip['end'])}\n")
            score = clip.get("score", 0)
            category = clip.get("category", "")
            f.write(f"[Score: {score:.1f}] {category}\n")
            f.write(clip.get("text", "") + "\n\n")

    logger.info(f"SRT exportado: {output_path}")
    return output_path


def export_premiere_xml(
    clips_by_video: List[Dict[str, Any]],
    output_path: str,
    project_name: str = "Smart Editor Highlights",
    sort_by: str = "chronological",
) -> str:
    """
    Gera arquivo Premiere XML (FCP 7 XML) compatível com DaVinci Resolve e Premiere.
    """
    first_vi = clips_by_video[0]["video_info"]
    fps = first_vi.get("fps", 25.0)
    width = first_vi.get("width", 1920)
    height = first_vi.get("height", 1080)
    fps_num = round(fps)
    
    total_duration = sum(c["duration"] for v in clips_by_video for c in v["clips"])
    total_frames = round(total_duration * fps)

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<!DOCTYPE xmeml>')
    lines.append('<xmeml version="5">')
    lines.append('  <project>')
    lines.append(f'    <name>{_xml_escape(project_name)}</name>')
    lines.append('    <children>')
    lines.append(f'      <sequence id="sequence-1">')
    lines.append(f'        <name>{_xml_escape(project_name)}</name>')
    lines.append(f'        <duration>{total_frames}</duration>')
    lines.append('        <rate>')
    lines.append(f'          <timebase>{fps_num}</timebase>')
    lines.append('          <ntsc>FALSE</ntsc>')
    lines.append('        </rate>')
    lines.append('        <media>')
    lines.append('          <video>')
    lines.append('            <format>')
    lines.append('              <samplecharacteristics>')
    lines.append(f'                <width>{width}</width>')
    lines.append(f'                <height>{height}</height>')
    lines.append('                <rate>')
    lines.append(f'                  <timebase>{fps_num}</timebase>')
    lines.append('                </rate>')
    lines.append('              </samplecharacteristics>')
    lines.append('            </format>')
    lines.append('            <track>')

    clip_item_idx = 1
    offset_frames = 0
    for vid_idx, vid_data in enumerate(clips_by_video):
        vi = vid_data["video_info"]
        vid_path = vi.get("path", "")
        vid_dur = vi.get("duration", 0.0)
        vid_name = Path(vid_path).name
        abs_path = str(Path(vid_path).resolve())
        file_uri = "file://localhost/" + abs_path.replace("\\", "/").replace(" ", "%20")
        
        total_video_frames = round(vid_dur * fps)
        file_id = f"file-{vid_idx + 1}"

        # Ordenar trechos de acordo com o critério escolhido
        clips_sorted = _sort_clips(vid_data["clips"], sort_by=sort_by)
        for clip in clips_sorted:
            clip_dur = clip["duration"]
            clip_start = clip["start"]
            clip_end = clip["end"]
            
            dur_frames = round(clip_dur * fps)
            start_frame = round(clip_start * fps)
            end_frame = round(clip_end * fps)
            
            score = clip.get("score", 0.0)
            speaker = clip.get("speaker", "Speaker ?")
            category = clip.get("category", "")
            clip_name = f"[{score:.1f}] {speaker} — {category}"
            
            lines.append(f'              <clipitem id="clipitem-{clip_item_idx}">')
            lines.append(f'                <name>{_xml_escape(clip_name)}</name>')
            lines.append(f'                <duration>{total_video_frames}</duration>')
            lines.append('                <rate>')
            lines.append(f'                  <timebase>{fps_num}</timebase>')
            lines.append('                </rate>')
            lines.append(f'                <in>{start_frame}</in>')
            lines.append(f'                <out>{end_frame}</out>')
            lines.append(f'                <start>{offset_frames}</start>')
            lines.append(f'                <end>{offset_frames + dur_frames}</end>')
            lines.append(f'                <file id="{file_id}">')
            lines.append(f'                  <name>{_xml_escape(vid_name)}</name>')
            lines.append(f'                  <pathurl>{file_uri}</pathurl>')
            lines.append('                  <rate>')
            lines.append(f'                    <timebase>{fps_num}</timebase>')
            lines.append('                  </rate>')
            lines.append(f'                  <duration>{total_video_frames}</duration>')
            lines.append('                </file>')
            lines.append('              </clipitem>')
            
            offset_frames += dur_frames
            clip_item_idx += 1

    lines.append('            </track>')
    lines.append('          </video>')
    
    # ── Áudio: Adiciona as faixas de áudio estéreo coordenadas ──
    lines.append('          <audio>')
    lines.append('            <numChannels>2</numChannels>')
    lines.append('            <format>')
    lines.append('              <samplecharacteristics>')
    lines.append('                <depth>16</depth>')
    lines.append('                <samplerate>44100</samplerate>')
    lines.append('              </samplecharacteristics>')
    lines.append('            </format>')
    
    for track_idx in [1, 2]:
        lines.append('            <track>')
        clip_item_idx = 1
        offset_frames = 0
        for vid_idx, vid_data in enumerate(clips_by_video):
            vi = vid_data["video_info"]
            vid_path = vi.get("path", "")
            vid_dur = vi.get("duration", 0.0)
            vid_name = Path(vid_path).name
            total_video_frames = round(vid_dur * fps)
            file_id = f"file-{vid_idx + 1}"
            
            clips_sorted = _sort_clips(vid_data["clips"], sort_by=sort_by)
            for clip in clips_sorted:
                clip_dur = clip["duration"]
                clip_start = clip["start"]
                dur_frames = round(clip_dur * fps)
                start_frame = round(clip_start * fps)
                end_frame = start_frame + dur_frames
                
                score = clip.get("score", 0.0)
                speaker = clip.get("speaker", "Speaker ?")
                category = clip.get("category", "")
                clip_name = f"[{score:.1f}] {speaker} — {category}"
                
                audio_clipitem_id = f"clipitem-{clip_item_idx}-a{track_idx}"
                
                lines.append(f'              <clipitem id="{audio_clipitem_id}">')
                lines.append(f'                <name>{_xml_escape(clip_name)}</name>')
                lines.append(f'                <duration>{total_video_frames}</duration>')
                lines.append('                <rate>')
                lines.append(f'                  <timebase>{fps_num}</timebase>')
                lines.append('                </rate>')
                lines.append(f'                <in>{start_frame}</in>')
                lines.append(f'                <out>{end_frame}</out>')
                lines.append(f'                <start>{offset_frames}</start>')
                lines.append(f'                <end>{offset_frames + dur_frames}</end>')
                lines.append(f'                <file id="{file_id}"/>')
                lines.append('                <sourcetrack>')
                lines.append('                  <tracktype>audio</tracktype>')
                lines.append(f'                  <trackindex>{track_idx}</trackindex>')
                lines.append('                </sourcetrack>')
                lines.append('              </clipitem>')
                
                offset_frames += dur_frames
                clip_item_idx += 1
        lines.append('            </track>')
    lines.append('          </audio>')
    lines.append('        </media>')
    lines.append('      </sequence>')
    lines.append('    </children>')
    lines.append('  </project>')
    lines.append('</xmeml>')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Premiere XML exportado: {output_path} ({clip_item_idx-1} clips)")
    return output_path

def export_individual_clips_zip(
    clips_by_video: List[Dict[str, Any]],
    output_zip_path: str,
    ffmpeg_bin: str = "ffmpeg",
    sort_by: str = "chronological"
) -> str:
    """
    Usa o FFmpeg para fatiar o vídeo original em clipes individuais em MP4
    e empacota todos eles em um arquivo ZIP.
    """
    import subprocess
    import tempfile
    import zipfile
    
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        clip_counter = 1
        for vid_data in clips_by_video:
            vi = vid_data["video_info"]
            video_path = vi.get("path", "")
            video_stem = Path(video_path).stem
            
            # Ordenar trechos conforme a escolha do usuário
            clips_sorted = _sort_clips(vid_data["clips"], sort_by=sort_by)
            
            for clip in clips_sorted:
                start = clip["start"]
                duration = clip["duration"]
                
                # Nome do arquivo do clipe dentro do zip
                score_str = f"{clip.get('score', 0.0):.1f}"
                spk_str = str(clip.get("speaker", "Speaker ?")).replace(" ", "_").replace("?", "X")
                out_name = f"clip_{clip_counter:03d}_[Score_{score_str}]_{spk_str}_{video_stem}.mp4"
                
                # Criar clipe numa pasta temporária e gravar no ZIP
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_out = Path(tmpdir) / out_name
                    
                    cmd = [
                        ffmpeg_bin,
                        "-ss", str(start),
                        "-t", str(duration),
                        "-i", video_path,
                        "-c", "copy",  # Copiar streams direto (sem re-codificar, instantâneo)
                        "-avoid_negative_ts", "make_zero",
                        "-y",
                        str(tmp_out)
                    ]
                    
                    subprocess.run(cmd, capture_output=True)
                    
                    if tmp_out.exists():
                        zipf.write(str(tmp_out), arcname=out_name)
                        
                clip_counter += 1
                
    logger.info(f"ZIP com {clip_counter-1} clipes individuais gerado em: {output_zip_path}")
    return output_zip_path


def export_unified_video(
    clips_by_video: List[Dict[str, Any]],
    output_mp4_path: str,
    ffmpeg_bin: str = "ffmpeg",
    sort_by: str = "chronological"
) -> str:
    """
    Gera pedaços temporários para cada clipe e usa o demuxer 'concat'
    do FFmpeg para uni-los em um único arquivo de vídeo (instantâneo, sem re-codificar).
    """
    import subprocess
    import tempfile
    
    os.makedirs(os.path.dirname(output_mp4_path), exist_ok=True)
    
    temp_dir = tempfile.TemporaryDirectory()
    temp_files = []
    
    try:
        clip_counter = 1
        for vid_data in clips_by_video:
            vi = vid_data["video_info"]
            video_path = vi.get("path", "")
            
            clips_sorted = _sort_clips(vid_data["clips"], sort_by=sort_by)
            for clip in clips_sorted:
                start = clip["start"]
                duration = clip["duration"]
                
                temp_clip_path = Path(temp_dir.name) / f"temp_{clip_counter:04d}.mp4"
                
                # Recortar o trecho
                cmd = [
                    ffmpeg_bin,
                    "-ss", str(start),
                    "-t", str(duration),
                    "-i", video_path,
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    "-y",
                    str(temp_clip_path)
                ]
                subprocess.run(cmd, capture_output=True)
                
                if temp_clip_path.exists():
                    temp_files.append(temp_clip_path)
                clip_counter += 1
                
        if not temp_files:
            raise RuntimeError("Nenhum clipe válido pôde ser extraído para a unificação.")
            
        # Criar arquivo de texto listando os vídeos para o concat do FFmpeg
        concat_txt_path = Path(temp_dir.name) / "concat.txt"
        with open(concat_txt_path, "w", encoding="utf-8") as f:
            for file_path in temp_files:
                # O FFmpeg exige caminhos absolutos com barras normais '/' no arquivo concat
                safe_path = str(file_path.absolute()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                
        # Concatenar todos os arquivos sem re-codificação
        cmd = [
            ffmpeg_bin,
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt_path),
            "-c", "copy",
            "-y",
            output_mp4_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            logger.error(f"Erro no FFmpeg concat: {result.stderr}")
            raise RuntimeError(f"Erro ao mesclar clipes no FFmpeg: {result.stderr}")
            
    finally:
        try:
            temp_dir.cleanup()
        except Exception:
            pass
            
    logger.info(f"Vídeo unificado gerado com sucesso em: {output_mp4_path}")
    return output_mp4_path


def _xml_escape(text: str) -> str:
    """Escapa caracteres especiais XML"""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

