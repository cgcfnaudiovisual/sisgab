import os
from datetime import datetime
from telebot import types
from .client import chat_states
from .utils import check_authorized_user, clear_state, get_user_active_year
from .keyboards import get_settings_keyboard, get_unauthorized_keyboard

def register_settings_handlers(bot):
    
    @bot.message_handler(commands=['settings', 'configuracoes', 'config'])
    async def register_settings_command(message):
        chat_id = message.chat.id
        clear_state(chat_id)
        
        profile = await check_authorized_user(message.from_user.id)
        
        chat_states[chat_id] = {
            'action': 'settings',
            'step': 'choose_option',
            'user': profile,
            'data': {}
        }
        
        is_authorized = profile is not None
        is_admin = profile and str(profile.get('role', '')).strip().lower() == 'admin'
        status_cadastro = "Não Cadastrado"
        if is_authorized:
            from database import get_bot_db_connection as get_db_connection
            db = get_db_connection()
            if db:
                try:
                    res_face = db.table('face_embeddings').select('id').eq('user_id', profile['id']).execute()
                    if res_face.data:
                        status_cadastro = "🟢 ATIVO (Cadastrado)"
                    else:
                        selfie_path = os.path.join("assets", "selfies", f"{message.from_user.id}.jpg")
                        if os.path.exists(selfie_path):
                            status_cadastro = "🟡 PROCESSANDO IA (Selfie Recebida)"
                        else:
                            status_cadastro = "🔴 PENDENTE (Enviar Selfie)"
                except Exception:
                    status_cadastro = "Erro ao consultar banco"
            
        await bot.reply_to(
            message,
            "⚙️ **CONFIGURAÇÕES DO OPERADOR - SISGAB**\n\n"
            f"👤 **Operador:** `{profile['nome'] if profile else 'Não Identificado'}`\n"
            f"📸 **Cadastro Facial:** `{status_cadastro}`\n\n"
            "Escolha uma das opções abaixo para gerenciar seu perfil:",
            reply_markup=get_settings_keyboard(is_authorized, is_admin),
            parse_mode='Markdown'
        )
