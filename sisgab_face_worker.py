"""
sisgab_face_worker.py — Local GPU Worker Engine para SisGAB
Executa no seu computador local utilizando a GPU (DirectML / InsightFace 512D)
ou CPU fallback, baseado na arquitetura do PixdioLive_bot.

Conecta ao Supabase, verifica fotos pendentes em lote, detecta rostos,
compara com os vetores de face_embeddings, registra photo_matches
e atualiza o heartbeat de status no banco para a interface Web.
"""

import sys
import os
import io
import time
import json
import hashlib
import traceback
import numpy as np
from datetime import datetime, timedelta

# Import cv2
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[FACE_WORKER] WARN: opencv-python não instalado.")

# Import InsightFace
_FACE_APP = None
INSIGHTFACE_AVAILABLE = False

def init_face_engine():
    """Inicializa o motor InsightFace (buffalo_l) com fallback DirectML GPU / CPU."""
    global _FACE_APP, INSIGHTFACE_AVAILABLE
    if _FACE_APP is not None:
        return _FACE_APP

    try:
        from insightface.app import FaceAnalysis
        print("[FACE_WORKER] 🚀 Inicializando InsightFace (buffalo_l)...")
        
        # Tenta inicializar com suporte DirectML/GPU (ctx_id=0) ou CPU (ctx_id=-1)
        try:
            app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
            app.prepare(ctx_id=0, det_size=(640, 640))
            print("[FACE_WORKER] ✅ InsightFace iniciado com aceleração GPU (DirectML).")
        except Exception as e_gpu:
            print(f"[FACE_WORKER] GPU não disponível ({e_gpu}), usando CPU modo otimizado...")
            app = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
            app.prepare(ctx_id=-1, det_size=(320, 320))
            print("[FACE_WORKER] ✅ InsightFace iniciado no modo CPU.")

        _FACE_APP = app
        INSIGHTFACE_AVAILABLE = True
        return _FACE_APP
    except Exception as e:
        print(f"[FACE_WORKER] ❌ Erro ao inicializar InsightFace: {e}")
        INSIGHTFACE_AVAILABLE = False
        return None


# ─── Utilitários de Hash e Validação ────────────────────────────────────

def compute_image_hash(image_bytes: bytes) -> str:
    """Calcula o hash MD5 da imagem para filtro anti-duplicação (Sugestão 4)."""
    return hashlib.md5(image_bytes).hexdigest()


def evaluate_selfie_quality(image_bytes: bytes) -> tuple[bool, str, np.ndarray | None]:
    """
    Valida a qualidade de uma selfie de cadastro (baseado em PixdioLive telegram_runner.py).
    Retorna (sucesso: bool, mensagem: str, embedding: ndarray | None).
    """
    app = init_face_engine()
    if not app:
        return False, "❌ Motor de reconhecimento facial indisponível no servidor.", None

    if not CV2_AVAILABLE:
        return False, "❌ OpenCV não instalado.", None

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, "❌ Arquivo de imagem inválido ou corrompido.", None

        faces = app.get(img)
        if not faces:
            return False, "❌ Nenhum rosto detectado na foto. Envie uma foto nítida e bem iluminada.", None

        if len(faces) > 1:
            return False, f"❌ Detectamos {len(faces)} rostos. Envie uma foto individual (apenas o seu rosto).", None

        face = faces[0]

        # Checa nitidez / score de detecção (mínimo 0.60 do PixdioLive)
        if hasattr(face, 'det_score') and face.det_score < 0.60:
            return False, "❌ Rosto pouco nítido ou iluminação fraca. Tente em um ambiente mais claro.", None

        # Checa rotação da cabeça (pose yaw/pitch <= 25 graus)
        if hasattr(face, 'pose') and face.pose is not None:
            pitch, yaw, roll = face.pose
            if abs(yaw) > 25:
                return False, "❌ Rosto muito de lado. Olhe diretamente para a câmera.", None
            if abs(pitch) > 25:
                return False, "❌ Rosto inclinado (muito para cima ou para baixo). Olhe de frente.", None

        # Retorna o vetor normalizado de 512 dimensões
        embedding = face.normed_embedding
        return True, "✅ Selfie aprovada com sucesso!", embedding
    except Exception as e:
        print(f"[FACE_WORKER] Erro ao avaliar selfie: {e}")
        return False, f"❌ Erro no processamento: {str(e)}", None


def draw_face_bounding_box(image_bytes: bytes, bbox: list) -> bytes | None:
    """
    Desenha um retângulo cyan com destaque ao redor do rosto (Sugestão 3).
    Retorna os bytes da imagem com a caixa desenhada.
    """
    if not CV2_AVAILABLE:
        return None
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
        # Desenha retângulo verde/cyan
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 229, 0), 3)
        # Adiciona rótulo
        cv2.putText(img, "MATCH IA", (x1, max(15, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 229, 0), 2)

        _, buffer = cv2.imencode('.jpg', img)
        return buffer.tobytes()
    except Exception as e:
        print(f"[FACE_WORKER] Erro ao desenhar bbox: {e}")
        return None


# ─── Worker Loop Principal ──────────────────────────────────────────────

def update_heartbeat(db, is_online=True, queued_count=0):
    """Atualiza o status de atividade do worker no banco (Sugestão 1)."""
    try:
        now_iso = datetime.utcnow().isoformat()
        db.table('config').upsert({'chave': 'face_worker_heartbeat', 'valor': now_iso}).execute()
        db.table('config').upsert({'chave': 'face_worker_status', 'valor': 'online' if is_online else 'offline'}).execute()
        db.table('config').upsert({'chave': 'face_worker_queue_count', 'valor': str(queued_count)}).execute()
    except Exception as e:
        pass


def run_worker_cycle(db):
    """
    Executa 1 ciclo de processamento da fila de fotos pendentes.
    Retorna o número de fotos processadas.
    """
    app = init_face_engine()
    if not app:
        print("[FACE_WORKER] Motor de IA não disponível neste ambiente.")
        return 0

    try:
        import drive_service

        # 1. Carrega todos os embeddings dos militares cadastrados no banco
        res_emb = db.table('face_embeddings').select('user_id, nome_guerra, telegram_id, embedding').execute()
        militar_embeddings = []
        if res_emb.data:
            for item in res_emb.data:
                try:
                    emb_vec = np.array(json.loads(item['embedding']) if isinstance(item['embedding'], str) else item['embedding'])
                    militar_embeddings.append({
                        'user_id': item.get('user_id'),
                        'nome_guerra': item['nome_guerra'],
                        'telegram_id': item.get('telegram_id'),
                        'vec': emb_vec
                    })
                except Exception as e:
                    pass

        if not militar_embeddings:
            print("[FACE_WORKER] Nenhum militar com biometria facial cadastrada no banco.")
            return 0

        # 2. Busca fotos com status 'pendente' ou 'PENDENTE_AI' em processed_photos
        res_photos = db.table('processed_photos').select('*').in_('status', ['pendente', 'PENDENTE_AI']).limit(20).execute()
        photos_to_process = res_photos.data or []

        update_heartbeat(db, is_online=True, queued_count=len(photos_to_process))

        if not photos_to_process:
            return 0

        print(f"[FACE_WORKER] 🔍 Encontradas {len(photos_to_process)} fotos pendentes para processar com GPU...")

        processed_count = 0
        known_hashes = set()

        for p_rec in photos_to_process:
            photo_id = p_rec['id']
            drive_file_id = p_rec.get('drive_file_id')
            event_name = p_rec.get('event_name', 'Evento')

            # Download da foto do Drive
            image_bytes = None
            if drive_file_id:
                image_bytes = drive_service.download_file(drive_file_id)

            if not image_bytes:
                # Marca como falha se não conseguiu baixar
                db.table('processed_photos').update({'status': 'erro_download'}).eq('id', photo_id).execute()
                continue

            # Sugestão 4: Filtro Anti-Duplicação por Hash
            img_hash = compute_image_hash(image_bytes)
            if img_hash in known_hashes:
                print(f"[FACE_WORKER] ⚠️ Foto duplicada detectada (hash {img_hash[:8]}), ignorando...")
                db.table('processed_photos').update({'status': 'duplicada'}).eq('id', photo_id).execute()
                continue
            known_hashes.add(img_hash)

            # Decodifica com OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR) if CV2_AVAILABLE else None

            if img is None:
                db.table('processed_photos').update({'status': 'erro_decodificacao'}).eq('id', photo_id).execute()
                continue

            # Detecta todas as faces na foto
            faces = app.get(img)
            matches_found = 0

            for face in faces:
                emb_det = face.normed_embedding

                # Compara com cada militar cadastrado
                best_sim = 0.0
                best_militar = None

                for m in militar_embeddings:
                    sim = float(np.dot(emb_det, m['vec']))
                    if sim > best_sim:
                        best_sim = sim
                        best_militar = m

                # Threshold de corte: ≥ 0.50 considera match potencial
                if best_sim >= 0.50 and best_militar:
                    # Status: ≥ 0.75 auto-aprovado, < 0.75 moderação pendente
                    status_match = 'aprovado' if best_sim >= 0.75 else 'pendente'

                    # Grava no banco photo_matches
                    match_payload = {
                        'photo_id': photo_id,
                        'militar_id': best_militar['user_id'],
                        'similarity': round(best_sim, 4),
                        'status': status_match
                    }
                    db.table('photo_matches').insert(match_payload).execute()
                    matches_found += 1

                    print(f"[FACE_WORKER]  Match: {best_militar['nome_guerra']} (similaridade: {best_sim*100:.1f}%) -> {status_match}")

                    # Notifica no Telegram se auto-aprovado
                    if status_match == 'aprovado' and best_militar.get('telegram_id'):
                        try:
                            from notifications_manager import notify_telegram
                            msg_t = f"📸 *Reconhecimento Facial SisGAB*\n\nVocê foi identificado(a) na foto do evento *{event_name}* com {best_sim*100:.0f}% de certeza!"
                            notify_telegram(msg_t, 'face_match', custom_chat_id=best_militar['telegram_id'])
                        except Exception:
                            pass

            # Marca a foto como processada
            db.table('processed_photos').update({
                'status': 'processada',
                'faces_count': len(faces),
                'matches_count': matches_found
            }).eq('id', photo_id).execute()

            processed_count += 1

        print(f"[FACE_WORKER] ✅ Ciclo concluído! {processed_count} fotos processadas.")
        return processed_count

    except Exception as e:
        print(f"[FACE_WORKER] Erro no ciclo do worker: {e}")
        traceback.print_exc()
        return 0


def main_loop():
    """Loop contínuo para rodar localmente no PC do usuário."""
    print("=" * 60)
    print("  🚀 SisGAB — Worker de Reconhecimento Facial (GPU DirectML)")
    print("=" * 60)
    print("Pressione Ctrl+C para encerrar.\n")

    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()

        if not db:
            print("[FACE_WORKER] ❌ Não foi possível conectar ao banco de dados Supabase.")
            return

        while True:
            processed = run_worker_cycle(db)
            if processed == 0:
                update_heartbeat(db, is_online=True, queued_count=0)
                time.sleep(10)  # Aguarda 10s se não houver fotos
            else:
                time.sleep(2)
    except KeyboardInterrupt:
        print("\n[FACE_WORKER] Encerrado pelo usuário.")
        try:
            from database import get_service_db_connection, get_db_connection
            db = get_service_db_connection() or get_db_connection()
            if db:
                update_heartbeat(db, is_online=False, queued_count=0)
        except Exception:
            pass


if __name__ == '__main__':
    main_loop()
