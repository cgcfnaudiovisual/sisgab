from telebot import types
from .utils import current_user_id, USER_PERMISSIONS_CACHE

def get_unauthorized_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("🔗 Vincular Meu Nome"), types.KeyboardButton("📝 Solicitar Acesso"))
    return markup

def get_main_menu_keyboard(is_operator=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_operator:
        markup.row(types.KeyboardButton("🟢 Dar Presença"), types.KeyboardButton("📋 Pronto CheGab"))
        markup.row(types.KeyboardButton("📋 Pautas COMSOC"), types.KeyboardButton("📅 Agenda Semanal"))
        markup.row(types.KeyboardButton("➕ Criar Demanda"), types.KeyboardButton("🤖 Digerir Pauta (IA)"))
        markup.row(types.KeyboardButton("🔌 Cautelas Ativas"), types.KeyboardButton("⚙️ Configurações"))
        markup.row(types.KeyboardButton("ℹ️ Ajuda"), types.KeyboardButton("❌ Cancelar"))
    else:
        markup.row(types.KeyboardButton("🟢 Dar Presença"), types.KeyboardButton("📅 Agenda Semanal"))
        markup.row(types.KeyboardButton("➕ Criar Demanda"), types.KeyboardButton("⚙️ Configurações"))
        markup.row(types.KeyboardButton("ℹ️ Ajuda"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_efetivo_linking_keyboard(efetivo_lista):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    row = []
    for ef in efetivo_lista:
        row.append(types.KeyboardButton(f"🎖️ {ef['nome_guerra']}"))
        if len(row) == 2:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
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

def get_date_keyboard(is_end_date=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    from datetime import datetime, timedelta
    now = datetime.now()
    d0 = now.strftime('%d/%m/%Y')
    d1 = (now + timedelta(days=1)).strftime('%d/%m/%Y')
    d2 = (now + timedelta(days=2)).strftime('%d/%m/%Y')
    d3 = (now + timedelta(days=3)).strftime('%d/%m/%Y')
    d7 = (now + timedelta(days=7)).strftime('%d/%m/%Y')

    if is_end_date:
        markup.row(types.KeyboardButton("📌 Mesmo Dia (Sem Término)"))
        markup.row(types.KeyboardButton(f"📅 +1 Dia ({d1[:5]})"), types.KeyboardButton(f"📅 +2 Dias ({d2[:5]})"))
        markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    else:
        markup.row(types.KeyboardButton(f"📅 Hoje ({d0[:5]})"), types.KeyboardButton(f"📅 Amanhã ({d1[:5]})"))
        markup.row(types.KeyboardButton(f"📅 Em 3 Dias ({d3[:5]})"), types.KeyboardButton(f"📅 Em 1 Semana ({d7[:5]})"))
        markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_time_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⏰ 08:00"), types.KeyboardButton("⏰ 08:30"), types.KeyboardButton("⏰ 09:00"))
    markup.row(types.KeyboardButton("⏰ 10:00"), types.KeyboardButton("⏰ 13:30"), types.KeyboardButton("⏰ 14:00"))
    markup.row(types.KeyboardButton("⏰ 15:00"), types.KeyboardButton("⏰ 16:00"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_uniform_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("👔 3.3 (Instalação / Comum)"), types.KeyboardButton("👔 4.4 (Operacional / Camuflado)"))
    markup.row(types.KeyboardButton("👔 3.1 (Passeio / Branco)"), types.KeyboardButton("👔 1.1 (Gala / Cerimonial)"))
    markup.row(types.KeyboardButton("👕 Paisano / Esporte"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_authorities_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("👑 Comandante do CGCFN"), types.KeyboardButton("👑 Almirantes / Generais"))
    markup.row(types.KeyboardButton("👑 Nenhuma Autoridade Especial"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_observations_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⏭️ Pular / Nenhuma Observação"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_multi_service_inline_keyboard(selected_services=None):
    if selected_services is None:
        selected_services = set()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    services = [
        ("foto", "📸 Cobertura Fotográfica"),
        ("video", "🎥 Cobertura em Vídeo / Filmagem"),
        ("grafico", "🎨 Serviço Gráfico / Design"),
        ("drone", "🚁 Imagens Aéreas / Drone"),
        ("redes", "📱 Mídias Sociais / Reels / Shorts")
    ]
    
    for code, label in services:
        is_sel = code in selected_services
        icon = "✅" if is_sel else "☑️"
        btn_txt = f"{icon} {label}"
        markup.add(types.InlineKeyboardButton(text=btn_txt, callback_data=f"toggle_service:{code}"))
        
    markup.add(types.InlineKeyboardButton(text="📦 Selecionar Tudo (Completo)", callback_data="toggle_service:all"))
    markup.add(types.InlineKeyboardButton(text="➡️ CONCLUIR SELEÇÃO DOS SERVIÇOS ➡️", callback_data="toggle_service:done"))
    return markup

def get_confirm_demanda_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("✅ Confirmar & Enviar Pauta"))
    markup.row(types.KeyboardButton("✏️ Reiniciar Formulação"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_presenca_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("🟢 (P) Presente"), types.KeyboardButton("💼 (MA) Missão Adm"))
    markup.row(types.KeyboardButton("⚔️ (MT) Missão Tática"), types.KeyboardButton("🏖️ (FE) Férias"))
    markup.row(types.KeyboardButton("📜 (L) Licença"), types.KeyboardButton("🏥 (H) Hospital"))
    markup.row(types.KeyboardButton("💊 (DM) Disp. Médica"), types.KeyboardButton("🛡️ (S) Serviço"))
    markup.row(types.KeyboardButton("❌ Cancelar"))
    return markup

