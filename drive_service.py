"""
drive_service.py — Módulo de integração com Google Drive API v3
Gerencia criação de pastas, upload/download de arquivos, listagem e movimentação.
Utiliza Service Account para autenticação server-to-server.
"""

import json
import io
import os
import traceback
from datetime import datetime, timedelta

# Google Drive API imports
try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
except ImportError:
    print("[DRIVE_SERVICE] WARN: Pillow não instalado. Marca d'água indisponível.")

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    from google.oauth2.service_account import Credentials
    DRIVE_API_AVAILABLE = True
except ImportError:
    DRIVE_API_AVAILABLE = False
    print("[DRIVE_SERVICE] WARN: google-api-python-client ou google-auth não instalado. Drive API indisponível.")


# ─── Configuração & Conexão ─────────────────────────────────────────────

SCOPES = ['https://www.googleapis.com/auth/drive']

_drive_service_instance = None
_service_account_info = None
_pasta_mae_id = None

MESES_PT = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL',
    5: 'MAIO', 6: 'JUNHO', 7: 'JULHO', 8: 'AGOSTO',
    9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
}


_pastas_mae_list = []

def _load_config_from_db():
    """Carrega credenciais e lista de pastas mãe do banco config."""
    global _service_account_info, _pasta_mae_id, _pastas_mae_list
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        if db:
            res = db.table('config').select('valor').eq('chave', 'drive_service_account_json').execute()
            if res.data and res.data[0].get('valor'):
                _service_account_info = json.loads(res.data[0]['valor'])

            res2 = db.table('config').select('valor').eq('chave', 'drive_pasta_mae_id').execute()
            if res2.data and res2.data[0].get('valor'):
                _pasta_mae_id = res2.data[0]['valor'].strip()

            res3 = db.table('config').select('valor').eq('chave', 'drive_pastas_mae_json').execute()
            if res3.data and res3.data[0].get('valor'):
                try:
                    _pastas_mae_list = json.loads(res3.data[0]['valor'])
                except Exception:
                    _pastas_mae_list = []
            
            if not _pastas_mae_list and _pasta_mae_id:
                _pastas_mae_list = [{'id': '1', 'nome': 'Pasta Mãe Principal', 'folder_id': _pasta_mae_id, 'padrao': True}]
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao carregar config do DB: {e}")


def get_pastas_mae_list():
    """Retorna a lista de pastas mãe configuradas."""
    global _pastas_mae_list
    if not _pastas_mae_list:
        _load_config_from_db()
    return _pastas_mae_list or []


def get_pasta_mae_id(folder_id_custom=None):
    """Retorna o ID da pasta mãe (customizada ou a padrão)."""
    global _pasta_mae_id
    if folder_id_custom:
        return folder_id_custom.strip()
    if not _pasta_mae_id:
        _load_config_from_db()
    return _pasta_mae_id


def get_drive_service():
    """Retorna instância autenticada do Google Drive API v3."""
    global _drive_service_instance
    if not DRIVE_API_AVAILABLE:
        print("[DRIVE_SERVICE] Drive API não disponível (libs não instaladas).")
        return None

    if _drive_service_instance:
        return _drive_service_instance

    _load_config_from_db()

    if not _service_account_info:
        print("[DRIVE_SERVICE] Nenhuma Service Account configurada. Configure no painel Admin.")
        return None

    try:
        creds = Credentials.from_service_account_info(_service_account_info, scopes=SCOPES)
        _drive_service_instance = build('drive', 'v3', credentials=creds, cache_discovery=False)
        print("[DRIVE_SERVICE] ✅ Google Drive API conectado com sucesso.")
        return _drive_service_instance
    except Exception as e:
        print(f"[DRIVE_SERVICE] ❌ Erro ao conectar ao Drive: {e}")
        traceback.print_exc()
        return None


def get_pasta_mae_id():
    """Retorna o ID da pasta mãe configurada."""
    global _pasta_mae_id
    if not _pasta_mae_id:
        _load_config_from_db()
    return _pasta_mae_id


def reset_drive_service():
    """Reseta a instância do Drive para forçar reconexão."""
    global _drive_service_instance, _service_account_info, _pasta_mae_id
    _drive_service_instance = None
    _service_account_info = None
    _pasta_mae_id = None


def testar_conexao():
    """Testa a conexão com o Drive e retorna (success: bool, message: str)."""
    service = get_drive_service()
    if not service:
        return False, "Serviço não configurado. Verifique a Service Account e a Pasta Mãe."
    try:
        pasta_id = get_pasta_mae_id()
        if not pasta_id:
            return False, "ID da Pasta Mãe não configurado."
        result = service.files().get(fileId=pasta_id, fields='id, name').execute()
        return True, f"✅ Conectado! Pasta Mãe: {result.get('name', 'N/A')} (ID: {result.get('id')})"
    except Exception as e:
        return False, f"❌ Erro de conexão: {str(e)}"


# ─── Operações de Pastas ────────────────────────────────────────────────

def create_folder(name, parent_id=None):
    """Cria uma pasta no Google Drive. Retorna o ID da pasta criada."""
    service = get_drive_service()
    if not service:
        return None
    try:
        metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            metadata['parents'] = [parent_id]
        folder = service.files().create(body=metadata, fields='id, webViewLink').execute()
        folder_id = folder.get('id')
        print(f"[DRIVE_SERVICE] Pasta criada: '{name}' -> ID: {folder_id}")
        return folder_id
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao criar pasta '{name}': {e}")
        return None


def find_folder(name, parent_id=None):
    """Busca uma pasta pelo nome dentro de um diretório pai. Retorna o ID ou None."""
    service = get_drive_service()
    if not service:
        return None
    try:
        q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        result = service.files().list(q=q, fields='files(id, name)', pageSize=1).execute()
        files = result.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao buscar pasta '{name}': {e}")
        return None


def find_or_create_folder(name, parent_id=None):
    """Busca uma pasta, se não existir cria. Retorna o ID."""
    folder_id = find_folder(name, parent_id)
    if folder_id:
        return folder_id
    return create_folder(name, parent_id)


def criar_pasta_evento(titulo_evento, data_evento_str, pasta_mae_id=None):
    """
    Cria a estrutura completa de pastas para um evento:
    PASTA_MAE / YYYY-MM - MÊS / MM-DD-YY - TÍTULO / SELEÇÃO
    
    Retorna dict: {'evento_folder_id': str, 'selecao_folder_id': str, 'evento_link': str} ou None
    """
    pasta_mae = get_pasta_mae_id(pasta_mae_id)
    if not pasta_mae:
        print("[DRIVE_SERVICE] Pasta Mãe não configurada.")
        return None

    try:
        # Parse da data flexível (suporta YYYY-MM-DD, DD/MM/YYYY, etc.)
        dt = None
        if isinstance(data_evento_str, datetime):
            dt = data_evento_str
        elif isinstance(data_evento_str, str) and data_evento_str.strip():
            s_dt = data_evento_str.strip()[:10]
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
                try:
                    dt = datetime.strptime(s_dt, fmt)
                    break
                except Exception:
                    pass
        if not dt:
            dt = datetime.now()

        # Nome da pasta do mês: "2026-08 - AGOSTO"
        mes_nome = MESES_PT.get(dt.month, str(dt.month))
        pasta_mes_name = f"{dt.strftime('%Y-%m')} - {mes_nome}"
        
        # Nome da pasta do evento: "08-15-26 - SOLENIDADE PASSAGEM DE COMANDO" (MM-DD-YY - TÍTULO)
        titulo_clean = str(titulo_evento).strip().upper()[:80]
        pasta_evento_name = f"{dt.strftime('%m-%d-%y')} - {titulo_clean}"

        # Criar/encontrar pasta do mês
        mes_id = find_or_create_folder(pasta_mes_name, pasta_mae)
        if not mes_id:
            return None

        # Criar pasta do evento
        evento_id = find_or_create_folder(pasta_evento_name, mes_id)
        if not evento_id:
            return None

        # Criar subpasta SELEÇÃO
        selecao_id = find_or_create_folder('SELEÇÃO', evento_id)

        # Gerar link compartilhável
        link = get_shareable_link(evento_id)

        print(f"[DRIVE_SERVICE] ✅ Estrutura criada para '{titulo_clean}': evento={evento_id}, selecao={selecao_id}")
        return {
            'evento_folder_id': evento_id,
            'selecao_folder_id': selecao_id,
            'evento_link': link or f"https://drive.google.com/drive/folders/{evento_id}"
        }
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao criar pasta do evento: {e}")
        traceback.print_exc()
        return None


# ─── Operações de Arquivos ──────────────────────────────────────────────

def list_files(folder_id, mime_filter=None, page_size=100):
    """
    Lista arquivos de uma pasta do Drive.
    Retorna lista de dicts: [{'id', 'name', 'mimeType', 'size', 'thumbnailLink', 'webViewLink'}]
    """
    service = get_drive_service()
    if not service:
        return []
    try:
        q = f"'{folder_id}' in parents and trashed = false"
        if mime_filter:
            q += f" and mimeType contains '{mime_filter}'"

        result = service.files().list(
            q=q,
            fields='files(id, name, mimeType, size, thumbnailLink, webViewLink, createdTime)',
            pageSize=page_size,
            orderBy='createdTime desc'
        ).execute()
        return result.get('files', [])
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao listar arquivos: {e}")
        return []


def upload_file(file_bytes, filename, folder_id, mime_type='image/jpeg'):
    """
    Faz upload de um arquivo para uma pasta do Drive.
    Retorna dict: {'id', 'name', 'webViewLink'} ou None.
    """
    service = get_drive_service()
    if not service:
        return None
    try:
        metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        result = service.files().create(
            body=metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        print(f"[DRIVE_SERVICE] Upload OK: {filename} -> {result.get('id')}")
        return result
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro no upload de '{filename}': {e}")
        return None


def download_file(file_id):
    """
    Faz download de um arquivo do Drive.
    Retorna bytes do arquivo ou None.
    """
    service = get_drive_service()
    if not service:
        return None
    try:
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro no download do arquivo {file_id}: {e}")
        return None


def move_file(file_id, dest_folder_id):
    """Move um arquivo para outra pasta no Drive."""
    service = get_drive_service()
    if not service:
        return False
    try:
        file_info = service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file_info.get('parents', []))
        service.files().update(
            fileId=file_id,
            addParents=dest_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        print(f"[DRIVE_SERVICE] Arquivo {file_id} movido para {dest_folder_id}")
        return True
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao mover arquivo: {e}")
        return False


def get_shareable_link(file_id):
    """Gera um link compartilhável (público) para um arquivo ou pasta."""
    service = get_drive_service()
    if not service:
        return None
    try:
        # Torna o arquivo acessível por qualquer pessoa com o link
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()
        result = service.files().get(fileId=file_id, fields='webViewLink').execute()
        return result.get('webViewLink')
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao gerar link: {e}")
        return f"https://drive.google.com/drive/folders/{file_id}"


def get_file_info(file_id):
    """Retorna informações de um arquivo/pasta."""
    service = get_drive_service()
    if not service:
        return None
    try:
        return service.files().get(
            fileId=file_id,
            fields='id, name, mimeType, size, webViewLink, thumbnailLink, createdTime'
        ).execute()
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao obter info do arquivo {file_id}: {e}")
        return None


# ─── Funções de Marca d'Água ──────────────────────────────────────────────

def apply_watermark(image_bytes, text="COMSOC / CGCFN", opacity=0.45):
    """
    Applies a semi-transparent text/badge watermark on the bottom-right corner of an image.
    Returns watermarked image bytes (PNG/JPEG format).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size
        
        # Create transparent overlay
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Font size relative to image size
        font_size = max(16, int(height * 0.035))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
            
        # Watermark text
        full_text = f"  {text}  "
        
        # Draw bounding box on bottom right
        margin = int(width * 0.02)
        text_bbox = draw.textbbox((0, 0), full_text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        
        x = width - text_w - margin - 20
        y = height - text_h - margin - 20
        
        # Draw dark semi-transparent rectangle badge
        alpha = int(255 * opacity)
        draw.rectangle([x, y, x + text_w + 16, y + text_h + 12], fill=(0, 20, 40, int(alpha * 0.85)))
        # Draw cyan text
        draw.text((x + 8, y + 4), full_text, fill=(0, 229, 255, alpha), font=font)
        
        # Composite image
        watermarked = Image.alpha_composite(img, overlay)
        output = io.BytesIO()
        watermarked.convert("RGB").save(output, format="JPEG", quality=92)
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"[DRIVE_SERVICE] Erro ao aplicar marca d'água: {e}")
        return image_bytes

def copy_and_watermark_to_selecao(file_id, selecao_folder_id, watermark_text="COMSOC / CGCFN"):
    """
    Baixa um arquivo, aplica a marca d'água e faz upload na pasta de SELEÇÃO.
    """
    file_info = get_file_info(file_id)
    if not file_info:
        return None
    
    original_name = file_info.get('name', 'imagem.jpg')
    file_bytes = download_file(file_id)
    if not file_bytes:
        return None
        
    watermarked_bytes = apply_watermark(file_bytes, watermark_text)
    new_name = f"WM_{original_name}"
    
    uploaded = upload_file(watermarked_bytes, new_name, selecao_folder_id)
    return uploaded
