#!/usr/bin/env python3
"""
event_photo_watcher.py — Portal do Convidado: Watcher de Fotos com Upload Paralelo + IA Local

Monitora uma pasta local de fotos de evento, faz upload paralelo ao Google Drive (10 workers)
e processa com InsightFace localmente (sem baixar do Drive) para extrair embeddings faciais.

Uso:
    python event_photo_watcher.py --event-id solenidade-ago-2026 --pasta "D:\\FOTOS\\Solenidade"

Flags opcionais:
    --workers N          Número de workers de upload paralelo (padrão: 10)
    --threshold N        Threshold de similaridade para match (padrão: 0.45)
    --batch-only         Processa apenas arquivos existentes e encerra (sem monitorar)
    --skip-ia            Apenas faz upload, sem processar com InsightFace
"""

import os
import sys
import time
import json
import hashlib
import argparse
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import cv2

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================
MAX_UPLOAD_WORKERS = 10
MAX_RETRIES = 3
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
MIN_FILE_SIZE_BYTES = 50_000  # Ignorar thumbs do SO (< 50KB)
MIN_FACE_SIZE_PX = 50         # Ignorar rostos menores que 50x50
MIN_DET_SCORE = 0.50           # Score mínimo de detecção

# ============================================================================
# ESTADO GLOBAL
# ============================================================================
_processed_hashes = set()  # MD5 de arquivos já processados (deduplicação)
_hashes_lock = threading.Lock()
_stats = {
    'total_na_pasta': 0,
    'upload_ok': 0,
    'upload_fail': 0,
    'ia_ok': 0,
    'ia_skip': 0,
    'rostos': 0,
    'matches_proativos': 0,
    'erros': [],
}
_stats_lock = threading.Lock()


# ============================================================================
# GPU AUTO-DETECTION
# ============================================================================
_FACE_APP = None
_GPU_INFO = 'não inicializado'


def init_face_engine():
    """Inicializa InsightFace com auto-detecção: NVIDIA CUDA → AMD DirectML → CPU."""
    global _FACE_APP, _GPU_INFO

    if _FACE_APP is not None:
        return _FACE_APP

    try:
        from insightface.app import FaceAnalysis
    except ImportError:
        print("❌ InsightFace não instalado. Use: pip install insightface onnxruntime")
        _GPU_INFO = 'indisponível'
        return None

    # 1º NVIDIA CUDA
    try:
        import onnxruntime as ort
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
            app.prepare(ctx_id=0, det_size=(640, 640))
            _FACE_APP = app
            _GPU_INFO = 'NVIDIA CUDA (640x640)'
            print(f"✅ GPU detectada: {_GPU_INFO}")
            return _FACE_APP
    except Exception:
        pass

    # 2º AMD DirectML
    try:
        import onnxruntime as ort
        if 'DmlExecutionProvider' in ort.get_available_providers():
            app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
            app.prepare(ctx_id=0, det_size=(640, 640))
            _FACE_APP = app
            _GPU_INFO = 'AMD DirectML (640x640)'
            print(f"✅ GPU detectada: {_GPU_INFO}")
            return _FACE_APP
    except Exception:
        pass

    # 3º CPU Fallback
    try:
        app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
        app.prepare(ctx_id=-1, det_size=(320, 320))
        _FACE_APP = app
        _GPU_INFO = 'CPU (320x320)'
        print(f"⚠️ Nenhuma GPU detectada, usando {_GPU_INFO}")
        return _FACE_APP
    except Exception as e:
        print(f"❌ Falha ao inicializar InsightFace: {e}")
        _GPU_INFO = 'falha'
        return None


# ============================================================================
# UPLOAD COM RETRY
# ============================================================================
def upload_with_retry(file_path: Path, folder_id: str) -> dict | None:
    """Upload de um arquivo para o Google Drive com retry e backoff exponencial."""
    import drive_service

    filename = file_path.name
    for attempt in range(MAX_RETRIES):
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            mime = 'image/jpeg'
            ext = file_path.suffix.lower()
            if ext == '.png':
                mime = 'image/png'
            elif ext in ('.tif', '.tiff'):
                mime = 'image/tiff'
            elif ext == '.bmp':
                mime = 'image/bmp'

            result = drive_service.upload_file(file_bytes, filename, folder_id, mime_type=mime)

            if result and isinstance(result, dict) and result.get('id'):
                return result
            elif result and isinstance(result, dict) and result.get('error') == 'storageQuotaExceeded':
                print(f"  ❌ Quota do Drive excedida para {filename}")
                return None

            raise Exception(f"Resultado inesperado: {result}")

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"  ⚠️ Retry {attempt + 1}/{MAX_RETRIES} para {filename}: {e} (aguardando {wait}s)")
                time.sleep(wait)
            else:
                print(f"  ❌ Falha definitiva no upload de {filename} após {MAX_RETRIES} tentativas: {e}")
                return None
    return None


# ============================================================================
# PROCESSAMENTO IA LOCAL
# ============================================================================
def process_faces_locally(file_path: Path, event_id: str, drive_file_id: str,
                          drive_link: str, photo_id: str = None) -> list:
    """Processa foto LOCAL com InsightFace. Retorna lista de embeddings salvos."""
    app = _FACE_APP
    if app is None:
        return []

    try:
        img = cv2.imread(str(file_path))
        if img is None:
            print(f"  ⚠️ Imagem corrompida ou ilegível: {file_path.name}")
            return []

        faces = app.get(img)
        if not faces:
            return []

        from database import save_event_photo_embeddings_batch

        records = []
        for face in faces:
            # Filtro de qualidade
            det_score = float(face.det_score) if hasattr(face, 'det_score') else 0
            if det_score < MIN_DET_SCORE:
                continue

            bbox = face.bbox.tolist() if hasattr(face, 'bbox') else None
            if bbox:
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w < MIN_FACE_SIZE_PX or h < MIN_FACE_SIZE_PX:
                    continue

            embedding = face.normed_embedding.tolist() if hasattr(face, 'normed_embedding') else None
            if embedding is None:
                continue

            records.append({
                'event_id': event_id,
                'photo_id': photo_id,
                'drive_file_id': drive_file_id,
                'drive_link': drive_link,
                'filename': file_path.name,
                'embedding': embedding,
                'bbox': bbox,
                'det_score': det_score,
            })

        if records:
            saved = save_event_photo_embeddings_batch(records)
            with _stats_lock:
                _stats['rostos'] += saved
            return records

    except Exception as e:
        print(f"  ❌ Erro IA em {file_path.name}: {e}")
        with _stats_lock:
            _stats['erros'].append(f"{file_path.name}: {e}")

    return []


# ============================================================================
# MATCH PROATIVO CONTRA CONVIDADOS PRÉ-CADASTRADOS
# ============================================================================
def run_proactive_matching(event_id: str, new_embeddings: list):
    """Compara novos embeddings contra perfis de convidados já cadastrados."""
    if not new_embeddings:
        return

    try:
        from database import (get_guest_profiles_not_notified, get_public_event,
                              mark_guest_notified, save_guest_delivery,
                              send_real_email_smtp)

        profiles = get_guest_profiles_not_notified(event_id)
        if not profiles:
            return

        event = get_public_event(event_id)
        threshold = event.get('threshold_match', 0.45) if event else 0.45

        for profile in profiles:
            guest_embeddings = json.loads(profile['embeddings']) if isinstance(profile['embeddings'], str) else profile['embeddings']
            email = profile.get('email')
            if not email or not guest_embeddings:
                continue

            # Multi-vetor max: para cada embedding do convidado, buscar max similarity
            matched_files = set()
            for guest_emb in guest_embeddings:
                guest_vec = np.array(guest_emb, dtype=np.float32)
                for rec in new_embeddings:
                    photo_vec = np.array(rec['embedding'], dtype=np.float32)
                    sim = float(np.dot(guest_vec, photo_vec))
                    if sim >= threshold:
                        matched_files.add(rec['drive_file_id'])

            if matched_files:
                # Enviar e-mail automático
                try:
                    photo_links = [f"https://drive.google.com/file/d/{fid}/view" for fid in matched_files]
                    links_html = ''.join(
                        f'<p>📷 <a href="{link}">Foto {i+1}</a></p>' for i, link in enumerate(photo_links)
                    )
                    body = f"""
                    <h2>📷 Suas fotos do evento estão prontas!</h2>
                    <p>Evento: <strong>{event.get('nome', event_id)}</strong></p>
                    <p>{len(matched_files)} foto(s) encontrada(s):</p>
                    {links_html}
                    <p>Acesse o portal para ver todas: <a href="https://sisgab-cgcfn.ddns.net/evento/{event_id}">Ver Galeria</a></p>
                    <hr>
                    <p><small>COMSOC / CGCFN</small></p>
                    """
                    send_real_email_smtp(email, f"📷 Suas fotos do evento {event.get('nome', '')}", body)
                    save_guest_delivery(event_id, email, ','.join(matched_files), len(matched_files))
                    mark_guest_notified(profile['id'])
                    with _stats_lock:
                        _stats['matches_proativos'] += 1
                    print(f"  📧 E-mail enviado para {email} ({len(matched_files)} fotos)")
                except Exception as e_mail:
                    print(f"  ⚠️ Falha ao enviar e-mail para {email}: {e_mail}")

    except Exception as e:
        print(f"  ⚠️ Erro no match proativo: {e}")


# ============================================================================
# PROCESSAMENTO DE UM ARQUIVO (UPLOAD + IA)
# ============================================================================
def process_single_file(file_path: Path, event_id: str, folder_id: str, skip_ia: bool = False):
    """Processa um único arquivo: upload ao Drive + IA local."""
    # Deduplicação por hash MD5
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
    except Exception:
        return

    with _hashes_lock:
        if file_hash in _processed_hashes:
            return
        _processed_hashes.add(file_hash)

    # Upload ao Drive
    result = upload_with_retry(file_path, folder_id)
    if result and result.get('id'):
        drive_file_id = result['id']
        drive_link = result.get('webViewLink', f"https://drive.google.com/file/d/{drive_file_id}/view")

        with _stats_lock:
            _stats['upload_ok'] += 1

        # Registrar em processed_photos
        try:
            from database import get_service_db_connection, get_db_connection
            conn = get_service_db_connection() or get_db_connection()
            if conn:
                conn.table('processed_photos').insert({
                    'event_name': event_id,
                    'filename': file_path.name,
                    'drive_file_id': drive_file_id,
                    'drive_link': drive_link,
                    'status': 'pendente' if skip_ia else 'processando',
                }).execute()
        except Exception as e_db:
            print(f"  ⚠️ Erro ao registrar {file_path.name} no banco: {e_db}")

        # Processamento IA local (paralelo — do arquivo local, sem baixar do Drive)
        if not skip_ia and _FACE_APP is not None:
            embeddings = process_faces_locally(file_path, event_id, drive_file_id, drive_link)
            if embeddings:
                with _stats_lock:
                    _stats['ia_ok'] += 1
                # Match proativo contra convidados pré-cadastrados
                run_proactive_matching(event_id, embeddings)
            else:
                with _stats_lock:
                    _stats['ia_skip'] += 1

            # Atualizar status da foto
            try:
                from database import get_service_db_connection, get_db_connection
                conn = get_service_db_connection() or get_db_connection()
                if conn:
                    conn.table('processed_photos').update({
                        'status': 'processada',
                        'faces_count': len(embeddings) if embeddings else 0,
                    }).eq('drive_file_id', drive_file_id).execute()
            except Exception:
                pass
    else:
        with _stats_lock:
            _stats['upload_fail'] += 1
            _stats['erros'].append(f"Upload falhou: {file_path.name}")


# ============================================================================
# BANNER E STATUS
# ============================================================================
def print_banner(event_id: str, pasta: str, workers: int, skip_ia: bool):
    """Exibe banner inicial do watcher."""
    print("\n" + "=" * 70)
    print("  🌐 PORTAL DO CONVIDADO — Event Photo Watcher")
    print("=" * 70)
    print(f"  📌 Evento:     {event_id}")
    print(f"  📁 Pasta:      {pasta}")
    print(f"  ⚙️  Workers:    {workers}")
    print(f"  🧠 IA:         {'Desativada' if skip_ia else _GPU_INFO}")
    print(f"  ⏱️  Início:     {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70 + "\n")


def print_progress():
    """Exibe resumo de progresso."""
    with _stats_lock:
        total = _stats['total_na_pasta']
        up_ok = _stats['upload_ok']
        up_fail = _stats['upload_fail']
        ia_ok = _stats['ia_ok']
        rostos = _stats['rostos']
        matches = _stats['matches_proativos']

    done = up_ok + up_fail
    pct = (done / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)

    print(f"\r  {bar} {pct:.0f}%  ⬆️ {up_ok}/{total}  ❌{up_fail}  🧠{ia_ok}  👤{rostos}  📧{matches}", end='', flush=True)


def print_summary():
    """Exibe resumo final."""
    with _stats_lock:
        s = _stats.copy()
        erros = s['erros'].copy()

    print("\n\n" + "=" * 70)
    print("  ✅ PROCESSAMENTO CONCLUÍDO")
    print("=" * 70)
    print(f"  📁 Total de fotos:          {s['total_na_pasta']}")
    print(f"  ⬆️  Upload OK:               {s['upload_ok']}")
    print(f"  ❌ Upload falha:             {s['upload_fail']}")
    print(f"  🧠 IA processadas:           {s['ia_ok']}")
    print(f"  🔇 IA ignoradas (sem rosto): {s['ia_skip']}")
    print(f"  👤 Rostos detectados:        {s['rostos']}")
    print(f"  📧 Matches proativos:        {s['matches_proativos']}")

    if erros:
        print(f"\n  ⚠️ Erros ({len(erros)}):")
        for err in erros[:10]:
            print(f"    • {err}")
        if len(erros) > 10:
            print(f"    ... e mais {len(erros) - 10} erros")

    print("=" * 70 + "\n")


# ============================================================================
# WATCHDOG FILE SYSTEM HANDLER
# ============================================================================
def setup_watchdog(pasta: str, event_id: str, folder_id: str, workers: int, skip_ia: bool):
    """Inicia o monitoramento da pasta com watchdog."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ watchdog não instalado. Use: pip install watchdog")
        sys.exit(1)

    class PhotoHandler(FileSystemEventHandler):
        def __init__(self):
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

        def on_created(self, event):
            if event.is_directory:
                return
            file_path = Path(event.src_path)
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                return
            if file_path.stat().st_size < MIN_FILE_SIZE_BYTES:
                return

            # Aguardar arquivo terminar de ser copiado (check size stability)
            time.sleep(1)
            try:
                size1 = file_path.stat().st_size
                time.sleep(1)
                size2 = file_path.stat().st_size
                if size1 != size2:
                    time.sleep(3)  # Arquivo ainda sendo escrito, aguardar mais
            except Exception:
                return

            with _stats_lock:
                _stats['total_na_pasta'] += 1

            print(f"\n  📷 Nova foto detectada: {file_path.name}")
            self._executor.submit(process_single_file, file_path, event_id, folder_id, skip_ia)

    handler = PhotoHandler()
    observer = Observer()
    observer.schedule(handler, pasta, recursive=True)
    observer.start()

    print(f"  👁️ Monitorando pasta: {pasta}")
    print(f"  ℹ️  Pressione Ctrl+C para parar.\n")

    try:
        while True:
            time.sleep(5)
            if _stats['total_na_pasta'] > 0:
                print_progress()
    except KeyboardInterrupt:
        print("\n\n  ⏹️ Monitoramento interrompido pelo usuário.")
        observer.stop()
    observer.join()


# ============================================================================
# PROCESSAMENTO EM LOTE (BATCH)
# ============================================================================
def run_batch(pasta: str, event_id: str, folder_id: str, workers: int, skip_ia: bool):
    """Processa todos os arquivos existentes na pasta em lote."""
    pasta_path = Path(pasta)
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(pasta_path.rglob(f'*{ext}'))
        files.extend(pasta_path.rglob(f'*{ext.upper()}'))

    # Remover duplicatas e filtrar por tamanho mínimo
    seen = set()
    unique_files = []
    for f in files:
        resolved = f.resolve()
        if resolved not in seen and f.stat().st_size >= MIN_FILE_SIZE_BYTES:
            seen.add(resolved)
            unique_files.append(f)

    if not unique_files:
        print("  ℹ️  Nenhuma foto encontrada na pasta.")
        return

    with _stats_lock:
        _stats['total_na_pasta'] = len(unique_files)

    print(f"  📁 {len(unique_files)} fotos encontradas. Iniciando processamento...\n")

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_single_file, f, event_id, folder_id, skip_ia): f
            for f in unique_files
        }

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            try:
                future.result()
            except Exception as e:
                file_path = futures[future]
                with _stats_lock:
                    _stats['erros'].append(f"{file_path.name}: {e}")

            if completed % 5 == 0 or completed == len(unique_files):
                elapsed = time.time() - start_time
                rate = completed / elapsed * 60 if elapsed > 0 else 0
                remaining = (len(unique_files) - completed) / (rate / 60) if rate > 0 else 0
                print_progress()
                print(f"  ⏱️ {rate:.0f} fotos/min  📡 ~{remaining:.0f}s restantes", end='')

    print_summary()


# ============================================================================
# VALIDAÇÃO E CONFIGURAÇÃO DO EVENTO
# ============================================================================
def validate_event(event_id: str) -> dict | None:
    """Valida se o evento existe e retorna seus dados."""
    try:
        from database import get_public_event
        event = get_public_event(event_id)
        if event:
            return event
    except Exception:
        pass

    print(f"  ⚠️ Evento '{event_id}' não encontrado no banco. Continuando com configuração local.")
    return None


def ensure_drive_folder(event_id: str, event: dict = None) -> str | None:
    """Garante que a pasta do evento existe no Drive. Retorna folder_id."""
    if event and event.get('drive_folder_id'):
        return event['drive_folder_id']

    try:
        import drive_service
        folder_id = drive_service.find_or_create_folder(event_id)
        if folder_id:
            print(f"  📂 Pasta Drive: {folder_id}")
            return folder_id
    except Exception as e:
        print(f"  ❌ Erro ao criar pasta Drive: {e}")

    return None


# ============================================================================
# MAIN
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description='Portal do Convidado — Watcher de Fotos com Upload Paralelo + IA Local',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python event_photo_watcher.py --event-id solenidade-ago-2026 --pasta "D:\\FOTOS\\Solenidade"
  python event_photo_watcher.py --event-id formatura-2026 --pasta "./fotos" --batch-only
  python event_photo_watcher.py --event-id teste --pasta "./fotos" --skip-ia --workers 4
        """
    )
    parser.add_argument('--event-id', required=True, help='ID do evento público (slug)')
    parser.add_argument('--pasta', required=True, help='Caminho da pasta local com as fotos')
    parser.add_argument('--workers', type=int, default=MAX_UPLOAD_WORKERS, help=f'Workers paralelos (padrão: {MAX_UPLOAD_WORKERS})')
    parser.add_argument('--threshold', type=float, default=0.45, help='Threshold de match (padrão: 0.45)')
    parser.add_argument('--batch-only', action='store_true', help='Processa apenas existentes e encerra')
    parser.add_argument('--skip-ia', action='store_true', help='Apenas upload, sem InsightFace')

    args = parser.parse_args()

    # Validar pasta
    pasta = os.path.abspath(args.pasta)
    if not os.path.isdir(pasta):
        print(f"❌ Pasta não encontrada: {pasta}")
        sys.exit(1)

    # Inicializar InsightFace (se não --skip-ia)
    if not args.skip_ia:
        init_face_engine()
        if _FACE_APP is None:
            print("⚠️ InsightFace não disponível. Continuando apenas com upload.")
            args.skip_ia = True

    # Validar evento no banco
    event = validate_event(args.event_id)

    # Garantir pasta no Drive
    folder_id = ensure_drive_folder(args.event_id, event)
    if not folder_id:
        print("❌ Não foi possível obter/criar a pasta do evento no Google Drive.")
        sys.exit(1)

    # Banner
    print_banner(args.event_id, pasta, args.workers, args.skip_ia)

    # Processar
    if args.batch_only:
        run_batch(pasta, args.event_id, folder_id, args.workers, args.skip_ia)
    else:
        # Primeiro batch dos existentes, depois monitorar novos
        print("  📦 Processando fotos existentes na pasta...\n")
        run_batch(pasta, args.event_id, folder_id, args.workers, args.skip_ia)
        print("  👁️ Iniciando monitoramento de novas fotos...\n")
        setup_watchdog(pasta, args.event_id, folder_id, args.workers, args.skip_ia)


if __name__ == '__main__':
    # Adicionar diretório do projeto ao path para imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
