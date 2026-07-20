import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from database import get_bot_db_connection as get_db_connection, reset_db_connection

bot = None
polling_task = None
chat_states = {}

DEFAULT_BOT_TOKEN = "8867290420:AAGsruGmuzwH3PYWGbiQwa2zShB0_aEpHjw"

def get_bot_token() -> str:
    """Busca o token do Telegram na tabela Config do banco, .env ou fallback padrao."""
    token = ""
    try:
        conn = get_db_connection()
        if conn:
            res = conn.table('config').select('*').eq('chave', 'telegram_bot_token').execute()
            if res.data and res.data[0].get('valor'):
                token = res.data[0]['valor'].strip()
    except Exception as e:
        print(f"[Bot] Erro ao ler token do banco de dados: {e}")
    
    if not token:
        token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        token = DEFAULT_BOT_TOKEN
    return token

async def _run_resilient_polling(bot_instance):
    while True:
        try:
            print("[TELEGRAM BOT] Iniciando loop de escuta Polling...", flush=True)
            try:
                await bot_instance.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                print(f"[TELEGRAM BOT] Aviso ao limpar webhook: {e}", flush=True)

            await bot_instance.polling(non_stop=True, timeout=15, request_timeout=30)
        except asyncio.CancelledError:
            print("[TELEGRAM BOT] Polling cancelado pelo sistema.", flush=True)
            break
        except Exception as poll_err:
            err_str = str(poll_err)
            if "Conflict" in err_str or "409" in err_str:
                print(f"[TELEGRAM BOT CONFLITO 409] Outra instância detectada. Limpando sessão e tentando reconectar em 7s...", flush=True)
                await asyncio.sleep(7)
            else:
                print(f"[TELEGRAM BOT POLLING ERR] {poll_err}. Reconectando em 5s...", flush=True)
                await asyncio.sleep(5)

async def init_bot():
    """Tarefa assíncrona inicializada no startup do NiceGUI para rodar o Telegram bot."""
    global bot, polling_task
    
    if os.getenv("DISABLE_TELEGRAM_BOT") == "True":
        print("[TELEGRAM BOT] Desabilitado via variável de ambiente DISABLE_TELEGRAM_BOT=True.", flush=True)
        return
        
    if polling_task or bot:
        print("[TELEGRAM BOT] Detectada instância ativa anterior. Parando-a primeiro...", flush=True)
        await stop_bot()
        
    token = get_bot_token()
    if not token:
        print("[TELEGRAM BOT] Erro: TELEGRAM_TOKEN não configurado no banco e nem no .env. Bot desabilitado.", flush=True)
        return
        
    try:
        print("[TELEGRAM BOT] Conectando ao Telegram...", flush=True)
        
        import telebot
        from telebot import asyncio_helper
        
        custom_api_url = os.getenv("TELEGRAM_API_URL")
        if custom_api_url:
            print(f"[TELEGRAM BOT] Usando URL de API personalizada: {custom_api_url}", flush=True)
            telebot.apihelper.API_URL = custom_api_url
            asyncio_helper.API_URL = custom_api_url
            
        custom_proxy = os.getenv("TELEGRAM_PROXY")
        if custom_proxy:
            print(f"[TELEGRAM BOT] Usando proxy de conexao: {custom_proxy}", flush=True)
            telebot.apihelper.proxy = {'https': custom_proxy, 'http': custom_proxy}
            asyncio_helper.proxy = {'https': custom_proxy, 'http': custom_proxy}

        bot = AsyncTeleBot(token)
        
        from .handlers import setup_handlers
        setup_handlers(bot)
        
        try:
            print("[TELEGRAM BOT] Configurando lista de comandos no menu do Telegram...", flush=True)
            await bot.set_my_commands([
                types.BotCommand("menu", "Exibe o menu de comandos e teclado"),
                types.BotCommand("settings", "Acessa as configurações e notificações"),
                types.BotCommand("cancelar", "Cancela a operação atual")
            ])
            print("[TELEGRAM BOT] Lista de comandos configurada com sucesso!", flush=True)
        except Exception as cmd_err:
            print(f"[TELEGRAM BOT] Aviso ao configurar lista de comandos: {cmd_err}", flush=True)

        try:
            print("[TELEGRAM BOT] Limpando webhooks e atualizações pendentes...", flush=True)
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as wh_err:
            print(f"[TELEGRAM BOT] Aviso ao deletar webhook: {wh_err}", flush=True)
            
        polling_task = asyncio.create_task(_run_resilient_polling(bot))
        print("[TELEGRAM BOT] Bot de Telegram ativo em segundo plano e escutando com reconexão automática!", flush=True)
    except Exception as e:
        print(f"[TELEGRAM BOT] Erro crítico ao iniciar o Bot: {e}", flush=True)

async def stop_bot():
    """Para o bot de Telegram cancelando a tarefa de polling e fechando a sessão."""
    global bot, polling_task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        polling_task = None
    if bot:
        try:
            await bot.close_session()
        except Exception as e:
            print(f"[TELEGRAM BOT] Erro ao fechar sessão: {e}", flush=True)
        bot = None
    print("[TELEGRAM BOT] Bot parado com sucesso.", flush=True)

async def restart_bot():
    """Para e reinicia o bot do Telegram com as novas configurações."""
    print("[TELEGRAM BOT] Reiniciando bot...", flush=True)
    await stop_bot()
    await init_bot()
