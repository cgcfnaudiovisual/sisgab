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

async def _tactical_reminder_loop():
    """Loop que executa a checagem de lembretes táticos a cada 10 minutos em segundo plano."""
    from .scheduled_jobs import send_tactical_2h_reminders
    while True:
        try:
            if bot:
                await send_tactical_2h_reminders(bot)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[TACTICAL REMINDER LOOP ERR] {e}")
        await asyncio.sleep(600)  # Checa a cada 10 minutos

async def _morning_attendance_loop():
    """Loop que monitora a chamada matutina (07:00) e cobranças recorrentes (07:10 às 09:30) via Telegram."""
    from datetime import datetime
    from .scheduled_jobs import trigger_daily_attendance_call, trigger_10min_attendance_reminder
    
    last_0700_date = None
    last_reminder_ts = 0
    
    while True:
        try:
            if bot:
                try:
                    from timezone import timezone, timedelta
                except Exception:
                    from datetime import timezone, timedelta
                
                tz_gmt3 = timezone(timedelta(hours=-3))
                now = datetime.now(tz_gmt3)
                today_str = now.strftime('%Y-%m-%d')
                now_ts = now.timestamp()
                
                # 1. Chamada Matutina Geral exatamente às 07:00 (disparada 1 vez por dia)
                if now.hour == 7 and now.minute == 0 and last_0700_date != today_str:
                    last_0700_date = today_str
                    print(f"[BOT MORNING CRON] Disparando Chamada Matutina das 07:00h para o efetivo...", flush=True)
                    asyncio.create_task(trigger_daily_attendance_call(bot))
                
                # 2. Cobrança Recorrente a cada 10 minutos (das 07:10h às 09:30h) para quem ainda estiver PENDENTE
                is_janela = (now.hour == 7 and now.minute >= 10) or (now.hour == 8) or (now.hour == 9 and now.minute <= 30)
                if is_janela and (now_ts - last_reminder_ts) >= 600:  # 10 minutos
                    last_reminder_ts = now_ts
                    print(f"[BOT MORNING CRON] Disparando cobrança de presença para pendentes às {now.strftime('%H:%M')}h...", flush=True)
                    asyncio.create_task(trigger_10min_attendance_reminder(bot))
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[MORNING ATTENDANCE LOOP ERR] {e}", flush=True)
            
        await asyncio.sleep(20)  # Checa a cada 20 segundos


async def _run_resilient_polling(bot_instance):
    asyncio.create_task(_tactical_reminder_loop())
    asyncio.create_task(_morning_attendance_loop())
    while True:
        try:
            if not bot_instance or bot is not bot_instance:
                print("[TELEGRAM BOT] Instância alterada ou nula. Encerrando polling antigo.", flush=True)
                break
            print("[TELEGRAM BOT] Iniciando loop de escuta Polling...", flush=True)
            try:
                await bot_instance.delete_webhook()
            except Exception as e:
                print(f"[TELEGRAM BOT] Aviso ao limpar webhook: {e}", flush=True)

            await bot_instance.polling(non_stop=True, timeout=10, request_timeout=20)
        except asyncio.CancelledError:
            print("[TELEGRAM BOT] Polling cancelado pelo sistema.", flush=True)
            break
        except Exception as poll_err:
            err_str = str(poll_err)
            if "Conflict" in err_str or "409" in err_str:
                print(f"[TELEGRAM BOT CONFLITO 409] Outra instância detectada. Tentando reconectar em 7s...", flush=True)
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
                types.BotCommand("relatorio", "Gera o Relatório Executivo do mês"),
                types.BotCommand("settings", "Acessa as configurações e notificações"),
                types.BotCommand("cadastrar_face", "Cadastra biometria facial para reconhecimento"),
                types.BotCommand("minhas_fotos", "Visualiza suas fotos nos eventos da Marinha"),
                types.BotCommand("cancelar", "Cancela a operação atual")
            ])

            print("[TELEGRAM BOT] Lista de comandos configurada com sucesso!", flush=True)
        except Exception as cmd_err:
            print(f"[TELEGRAM BOT] Aviso ao configurar lista de comandos: {cmd_err}", flush=True)

        try:
            print("[TELEGRAM BOT] Limpando webhooks...", flush=True)
            await bot.delete_webhook()
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
