import os
import re
import threading
import yt_dlp

class YouTubeDownloader:
    def __init__(self):
        self.active_downloads = {}  # id: progress_dict

    def get_info(self, url):
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Não foi possível obter informações do vídeo.")
                
                if 'entries' in info:
                    entries = []
                    for entry in info['entries']:
                        if entry:
                            entries.append({
                                'title': entry.get('title') or 'Vídeo sem título',
                                'url': entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'id': entry.get('id'),
                                'duration': entry.get('duration'),
                                'thumbnail': entry.get('thumbnail') or (f"https://img.youtube.com/vi/{entry.get('id')}/0.jpg" if entry.get('id') else None)
                            })
                    return {
                        'title': info.get('title') or 'Playlist sem título',
                        'is_playlist': True,
                        'entries': entries,
                        'url': url
                    }
                
                formats = []
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        resolution = f.get('height')
                        if resolution and resolution not in [fmt['height'] for fmt in formats]:
                            formats.append({
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'height': resolution,
                                'resolution': f"{resolution}p ({f.get('ext')})",
                                'filesize': f.get('filesize')
                            })
                
                formats = sorted(formats, key=lambda x: x['height'], reverse=True)
                
                return {
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'author': info.get('uploader'),
                    'formats': formats,
                    'is_playlist': False,
                    'url': url
                }
            except Exception as e:
                raise Exception(f"Erro: {str(e)}")

    def download(self, url, download_id, output_path, is_audio=False, quality='best', custom_filename=None, progress_callback=None):
        def run():
            def update_progress(info):
                if download_id in self.active_downloads:
                    self.active_downloads[download_id].update(info)
                else:
                    self.active_downloads[download_id] = info
                if progress_callback:
                    progress_callback(download_id, info)

            def ydl_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    percent = (downloaded / total * 100) if total > 0 else 0
                    
                    speed = d.get('speed')
                    speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "N/A"
                    
                    eta = d.get('eta')
                    eta_str = f"{eta}s" if eta else "N/A"
                    
                    update_progress({
                        'status': 'downloading',
                        'percent': percent,
                        'speed': speed_str,
                        'eta': eta_str
                    })
                        
                elif d['status'] == 'finished':
                    update_progress({
                        'status': 'converting',
                        'percent': 100,
                        'speed': '0 MB/s',
                        'eta': '0s'
                    })

            def find_ffmpeg():
                from pathlib import Path
                root = Path(__file__).parent
                paths = [
                    root / "bin" / "ffmpeg.exe",
                    root / "ffmpeg.exe",
                    root / "bin" / "ffmpeg",
                    root / "ffmpeg",
                ]
                for p in paths:
                    if p.exists():
                        return str(p)
                return None

            os.makedirs(output_path, exist_ok=True)
            
            ydl_opts = {
                'progress_hooks': [ydl_hook],
            }
            
            if custom_filename:
                safe_name = re.sub(r'[\\/*?:"<>|]', "", custom_filename)
                ydl_opts['outtmpl'] = os.path.join(output_path, f"{safe_name}.%(ext)s")
            else:
                ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.%(ext)s')

            ffmpeg_loc = find_ffmpeg()
            if ffmpeg_loc:
                ydl_opts['ffmpeg_location'] = ffmpeg_loc

            if is_audio:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality if quality in ['320', '256', '192', '128'] else '192',
                    }],
                })
            else:
                if quality == 'best':
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    ydl_opts['format'] = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best'

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    
                    filepath = None
                    if info_dict:
                        if 'entries' in info_dict:
                            filepath = None
                        else:
                            filename = ydl.prepare_filename(info_dict)
                            if is_audio:
                                filename = os.path.splitext(filename)[0] + ".mp3"
                            if os.path.exists(filename):
                                filepath = filename
                            else:
                                base_no_ext = os.path.splitext(filename)[0]
                                for ext in ['.mp3', '.mp4', '.mkv', '.webm', '.m4a']:
                                    if os.path.exists(base_no_ext + ext):
                                        filepath = base_no_ext + ext
                                        break
                                        
                update_progress({
                    'status': 'completed', 
                    'percent': 100,
                    'filepath': filepath,
                    'folder': output_path
                })
            except Exception as e:
                update_progress({'status': 'failed', 'error': str(e), 'percent': 0})

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t
