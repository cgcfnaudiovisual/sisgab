import os
import asyncio
from datetime import datetime, timedelta
from database import get_bot_db_connection as get_db_connection
from .utils import escape_markdown

async def send_daily_morning_report(bot, chat_id=None):
    """Gera e envia o relatório diário 'Bom Dia COMSOC'"""
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("[CRON] TELEGRAM_CHAT_ID não configurado.")
        return
        
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn:
            return
            
        hoje_str = datetime.now().strftime('%Y-%m-%d')
        hoje_br = datetime.now().strftime('%d/%m/%Y')
        
        # 1. Carrega pautas do dia
        res_pautas = conn.table('demandas_comunicacao').select('*').eq('data_evento', hoje_str).eq('status', 'aprovada').execute()
        pautas = res_pautas.data if res_pautas.data else []
        
        # 2. Carrega cautelas ativas
        res_cautelas = conn.table('cautela_equipamentos').select('*').eq('status', 'retirado').execute()
        cautelas = res_cautelas.data if res_cautelas.data else []
        
        pautas_txt = ""
        if pautas:
            for idx, p in enumerate(pautas, 1):
                pautas_txt += (
                    f"{idx}. 📸 **{escape_markdown(p['titulo_evento'])}**\n"
                    f"   🕒 Hora: {p['hora_evento']} | 📍 Local: {escape_markdown(p['local_evento'])}\n"
                    f"   👥 Equipe/Autoridades: {escape_markdown(p.get('autoridades') or 'Não informado')}\n"
                )
        else:
            pautas_txt = "🟢 Nenhuma pauta de cobertura agendada para hoje.\n"
            
        cautelas_txt = ""
        if cautelas:
            for c in cautelas:
                cautelas_txt += f"• 🔋 **{escape_markdown(c['equipamento'])}** retirado por {escape_markdown(c['retirado_por'])}\n"
        else:
            cautelas_txt = "🟢 Nenhum equipamento pendente de devolução.\n"
            
        msg = (
            f"🌅 **BOM DIA, COMSOC!**\n"
            f"📅 **Hoje: {hoje_br}**\n\n"
            f"📸 **PAUTAS DO DIA:**\n"
            f"{pautas_txt}\n"
            f"🔋 **CAUTELAS DE EQUIPAMENTO:**\n"
            f"{cautelas_txt}\n"
            f"⚓ _Central de Operações COMSOC_IA_"
        )
        await bot.send_message(chat_id, msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[CRON] Erro ao enviar relatório diário: {e}")

async def send_weekly_summary_report(bot, chat_id=None):
    """Gera e envia o resumo semanal de pautas para os próximos 7 dias"""
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("[CRON] TELEGRAM_CHAT_ID não configurado.")
        return
        
    try:
        conn = get_db_connection()
        if not conn:
            return
            
        hoje = datetime.now().date()
        fim_semana = hoje + timedelta(days=7)
        
        res_pautas = conn.table('demandas_comunicacao').select('*').gte('data_evento', hoje.isoformat()).lte('data_evento', fim_semana.isoformat()).eq('status', 'aprovada').execute()
        pautas = res_pautas.data if res_pautas.data else []
        
        pautas_txt = ""
        if pautas:
            # Ordena por data
            pautas_sorted = sorted(pautas, key=lambda x: x.get('data_evento', ''))
            for p in pautas_sorted:
                data_br = datetime.strptime(p['data_evento'], '%Y-%m-%d').strftime('%d/%m')
                pautas_txt += f"• 📅 **{data_br}** — {escape_markdown(p['titulo_evento'])} ({p['hora_evento']})\n"
        else:
            pautas_txt = "🟢 Nenhuma pauta cadastrada para os próximos 7 dias.\n"
            
        msg = (
            f"📅 **PLANEJAMENTO SEMANAL COMSOC**\n"
            f"Período: {hoje.strftime('%d/%m')} a {fim_semana.strftime('%d/%m')}\n\n"
            f"📋 **Próximas Pautas:**\n"
            f"{pautas_txt}\n"
            f"⚓ _Central de Operações COMSOC_IA_"
        )
        await bot.send_message(chat_id, msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[CRON] Erro ao enviar resumo semanal: {e}")


async def trigger_daily_attendance_call(bot):
    """Envia a chamada matutina para todos os militares ativos com Telegram ID às 07:00h."""
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn: return
        
        res_ef = conn.table('efetivo').select('telegram_id, nome_guerra').execute()
        if not res_ef.data: return
        
        from .keyboards import get_presenca_keyboard
        msg = (
            "🌅 **CHAMADA MATUTINA — CGCFN/SISGAB**\n\n"
            "Bom dia Equipe LANÇAMENTO 🚀!\n"
            "Solicito que todos acusem suas rotinas para hoje.\n\n"
            "🚨 *Senhores o regresso é 07:30h e o pronto da presença para o CheGab é até 8h.*\n\n"
            "Selecione a sua situação nos botões abaixo:"
        )
        
        for m in res_ef.data:
            tg_id = m.get('telegram_id')
            if tg_id:
                try:
                    await bot.send_message(tg_id, msg, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                except Exception as e_send:
                    print(f"[ATTENDANCE CALL SEND ERR] {tg_id}: {e_send}")
    except Exception as e:
        print(f"[ATTENDANCE CALL ERR] {e}")


async def trigger_10min_attendance_reminder(bot):
    """Verifica militares pendentes de chamada no dia atual entre 07:30h e 08:00h e envia aviso a cada 10 min."""
    now = datetime.now()
    if not (7 <= now.hour <= 8):
        return
        
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn: return
        
        hoje_str = now.strftime('%Y-%m-%d')
        
        res_ef = conn.table('efetivo').select('nome_guerra, telegram_id').execute()
        if not res_ef.data: return
        
        res_pr = conn.table('presenca_diaria').select('nome_guerra').eq('data', hoje_str).execute()
        respondidos = {p['nome_guerra'].upper() for p in res_pr.data} if res_pr.data else set()
        
        from .keyboards import get_presenca_keyboard
        msg_remind = (
            "🚨 *LEMBRETE RECORRENTE DA SARGENTEAÇÃO*\n\n"
            "Atenção! O regresso é 07:30h e o pronto para o CheGab é até **08:00h**.\n"
            "Você ainda não acusou sua rotina de hoje!\n\n"
            "Por favor, selecione sua situação nos botões abaixo:"
        )
        
        for m in res_ef.data:
            nome_g = m['nome_guerra'].upper()
            tg_id = m.get('telegram_id')
            if nome_g not in respondidos and tg_id:
                try:
                    await bot.send_message(tg_id, msg_remind, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                except Exception as e_send:
                    print(f"[ATTENDANCE REMIND ERR] {tg_id}: {e_send}")
    except Exception as e:
        print(f"[ATTENDANCE REMINDER LOOP ERR] {e}")
