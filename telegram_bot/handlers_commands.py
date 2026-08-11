import os
from datetime import datetime
from telebot import types
from .client import chat_states
from .utils import check_authorized_user, clear_state, USER_PERMISSIONS_CACHE
from .keyboards import get_main_menu_keyboard, get_unauthorized_keyboard

def register_commands(bot):
    
    @bot.message_handler(commands=['start', 'help', 'menu'])
    async def send_welcome(message):
        chat_id = message.chat.id
        clear_state(chat_id)
        
        profile = await check_authorized_user(message.from_user.id)
        if not profile:
            welcome_text = (
                "⚓ **Comando Tático SisGAB** ⚓\n\n"
                "Olá! Você está acessando o assistente oficial do SisGAB por Telegram.\n\n"
                "⚠️ **Acesso Restrito / Não Autorizado**\n"
                f"Seu Telegram ID (`{message.from_user.id}`) não está vinculado a nenhum operador ativo no sistema.\n\n"
                "Para realizar qualquer tarefa, é necessário **solicitar acesso** para aprovação do Administrador.\n"
                "Clique no botão abaixo para preencher sua solicitação."
            )
            await bot.reply_to(message, welcome_text, reply_markup=get_unauthorized_keyboard(), parse_mode='Markdown')
            return

        is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
        nome_user = profile.get('nome_guerra') or profile.get('nome_completo') or profile.get('username') or profile.get('nome', 'Operador')
        welcome_text = (
            "⚓ **Comando Tático SisGAB** ⚓\n\n"
            f"Olá, {nome_user}! Eu sou o assistente oficial do SisGAB para o painel operacional de comunicação social e gabinete.\n\n"
            "Use os botões do teclado abaixo para acessar as opções."
        )
        await bot.reply_to(message, welcome_text, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')

    @bot.message_handler(commands=['cancelar'])
    async def cancel_action(message):
        chat_id = message.chat.id
        clear_state(chat_id)
        profile = await check_authorized_user(message.from_user.id)
        is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
        await bot.reply_to(message, "❌ Operação cancelada com sucesso.", reply_markup=get_main_menu_keyboard(is_operator))

    @bot.message_handler(commands=['cobrar_presenca', 'lembrar_presenca', 'insistir_presenca'])
    async def cobrar_presenca_cmd(message):
        profile = await check_authorized_user(message.from_user.id)
        if not profile or str(profile.get('role', '')).lower() not in ('admin', 'supervisor', 'praca_gab', 'comsoc', 'oficial'):
            await bot.reply_to(message, "⛔ Acesso restrito aos sargenteantes e administradores.")
            return
        from .scheduled_jobs import trigger_10min_attendance_reminder
        notified = await trigger_10min_attendance_reminder(bot, force_now=True)
        if notified > 0:
            await bot.reply_to(message, f"📢 **Cobrança Recorrente Disparada!**\nLembrete/alerta enviado para **{notified}** militar(es) com presença pendente de resposta.", parse_mode='Markdown')
        else:
            await bot.reply_to(message, "🟢 Todos os militares já acusaram presença hoje ou não há pendências ativas!", parse_mode='Markdown')

    @bot.message_handler(commands=['cadastrar_face'])
    async def cadastrar_face_cmd(message):
        chat_id = message.chat.id
        from .utils import check_authorized_user
        profile = await check_authorized_user(message.from_user.id)
        if not profile:
            await bot.reply_to(message, "⛔ Usuário não autorizado.")
            return

        chat_states[chat_id] = {'action': 'waiting_selfie_registration', 'user': profile}
        await bot.reply_to(message, "📸 Por favor, envie uma foto individual do seu rosto (selfie), nítida e bem iluminada.")

    @bot.message_handler(commands=['minhas_fotos'])
    async def minhas_fotos_cmd(message):
        from db_utils import get_db_connection, get_service_db_connection
        chat_id = message.chat.id
        from .utils import check_authorized_user
        profile = await check_authorized_user(message.from_user.id)
        if not profile:
            await bot.reply_to(message, "⛔ Usuário não autorizado.")
            return

        db = get_db_connection()
        if not db:
            await bot.reply_to(message, "⚠️ Banco de dados indisponível.")
            return

        user_id = profile.get('id')
        
        try:
            res_matches = db.table('photo_matches').select('photo_id, processed_photos(event_name, drive_file_id)').eq('militar_id', user_id).eq('status', 'aprovado').execute()
            matches = res_matches.data if res_matches and res_matches.data else []
            
            if not matches:
                await bot.reply_to(message, "📸 *Você ainda não possui fotos identificadas nos eventos da Marinha.*", parse_mode='Markdown')
                return
                
            events = {}
            for match in matches:
                p_photo = match.get('processed_photos', {})
                evt_name = p_photo.get('event_name', 'Evento Desconhecido') if isinstance(p_photo, dict) else 'Evento Desconhecido'
                
                if evt_name not in events:
                    events[evt_name] = 0
                events[evt_name] += 1
                
            reply_txt = f"📸 *SUAS FOTOS NOS EVENTOS DO CGCFN*\n\nVocê foi identificado(a) em {len(matches)} fotos:\n\n"
            
            idx = 1
            for evt_name, count in events.items():
                reply_txt += f"{idx}. 🎖️ {evt_name} ({count} fotos)\n"
                idx += 1
                
            await bot.reply_to(message, reply_txt, parse_mode='Markdown')
            
        except Exception as e:
            await bot.reply_to(message, f"❌ Erro ao buscar fotos: {e}")
