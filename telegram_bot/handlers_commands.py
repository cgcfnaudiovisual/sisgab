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
