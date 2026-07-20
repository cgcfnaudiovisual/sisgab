from telebot import types
from .utils import current_user_id, USER_PERMISSIONS_CACHE

def get_unauthorized_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("📝 Solicitar Acesso"))
    return markup

def get_main_menu_keyboard(is_operator=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_operator:
        markup.row(types.KeyboardButton("📋 Pautas COMSOC"), types.KeyboardButton("📅 Agenda Google"))
        markup.row(types.KeyboardButton("➕ Criar Demanda"), types.KeyboardButton("🔌 Cautelas Ativas"))
        markup.row(types.KeyboardButton("⚙️ Configurações"), types.KeyboardButton("ℹ️ Ajuda"))
    else:
        markup.row(types.KeyboardButton("➕ Criar Demanda"), types.KeyboardButton("📅 Agenda Google"))
        markup.row(types.KeyboardButton("⚙️ Configurações"), types.KeyboardButton("ℹ️ Ajuda"))
    markup.row(types.KeyboardButton("❌ Cancelar"))
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_settings_keyboard(is_authorized=True, is_admin=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_authorized:
        markup.row(types.KeyboardButton("📸 Cadastro Facial"), types.KeyboardButton("🔍 Buscar Minhas Fotos"))
        if is_admin:
            markup.row(types.KeyboardButton("🔔 Notificações"), types.KeyboardButton("👥 Pedidos de Acesso"))
        else:
            markup.row(types.KeyboardButton("🔔 Notificações"))
        markup.row(types.KeyboardButton("⬅️ Voltar"))
    else:
        markup.row(types.KeyboardButton("📝 Solicitar Acesso"), types.KeyboardButton("⬅️ Voltar"))
    return markup

def get_notifications_toggle_keyboard(user_prefs):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    
    st_silence = "🔴 SIM" if user_prefs.get("silence_all", False) else "🟢 NÃO"
    st_aviso = "🟢 ATIVADO" if user_prefs.get("notify_aviso", True) else "🔴 MUTADO"
    st_new_user = "🟢 ATIVADO" if user_prefs.get("notify_new_user", True) else "🔴 MUTADO"
    
    markup.row(types.KeyboardButton(f"📢 Letreiro/Avisos: {st_aviso}"))
    markup.row(types.KeyboardButton(f"👥 Novos Acessos: {st_new_user}"), types.KeyboardButton(f"🔇 Silenciar Tudo: {st_silence}"))
    markup.row(types.KeyboardButton("⬅️ Voltar"))
    return markup

def get_aviso_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("📢 Novo Aviso"), types.KeyboardButton("📋 Listar Existentes"))
    markup.row(types.KeyboardButton("✏️ Editar Aviso"), types.KeyboardButton("❌ Remover/Excluir"))
    markup.row(types.KeyboardButton("🔒 Enviar Aviso Privado"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_duration_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("1"), types.KeyboardButton("2"), types.KeyboardButton("3"))
    markup.row(types.KeyboardButton("5"), types.KeyboardButton("7"), types.KeyboardButton("10"))
    markup.row(types.KeyboardButton("15"), types.KeyboardButton("30"))
    return markup

def get_om_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⚓ CGCFN"), types.KeyboardButton("🏢 Outra OM"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_coverage_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("📸 Fotografia"), types.KeyboardButton("🎥 Vídeo"))
    markup.row(types.KeyboardButton("📸+🎥 Ambos (Foto & Vídeo)"), types.KeyboardButton("🚁 Foto, Vídeo & Drone"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_video_format_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("🎬 Melhores Momentos (Reels/Shorts)"))
    markup.row(types.KeyboardButton("🎞️ Cobertura Íntegra"), types.KeyboardButton("📦 Apenas Material Bruto"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_yes_no_keyboard(yes_label="Sim", no_label="Não"):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton(f"✅ {yes_label}"), types.KeyboardButton(f"❌ {no_label}"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_confirm_demanda_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("✅ Confirmar & Enviar Pauta"))
    markup.row(types.KeyboardButton("✏️ Reiniciar Formulação"), types.KeyboardButton("❌ Cancelar"))
    return markup

