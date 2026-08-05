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
    """Envia a chamada matutina para todos os militares ativos com Telegram ID às 07:00h (excluindo os em férias/licença ativas)."""
    try:
        from timezone import timezone, timedelta
    except Exception:
        from datetime import timezone, timedelta
        
    tz_gmt3 = timezone(timedelta(hours=-3))
    now = datetime.now(tz_gmt3)
    hoje_str = now.strftime('%Y-%m-%d')
    
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn: return
        
        res_ef = conn.table('efetivo').select('telegram_id, nome_guerra').execute()
        if not res_ef.data: return

        # Isenção por férias/licenças ativas
        isentos = set()
        try:
            res_ext = conn.table('presenca_diaria').select('nome_guerra, data_fim').in_('status', ['FE', 'L', 'DM']).lte('data', hoje_str).execute()
            if res_ext and res_ext.data:
                for item in res_ext.data:
                    df = item.get('data_fim')
                    if df and df >= hoje_str:
                        isentos.add(item.get('nome_guerra', '').upper())
        except Exception as ext_err:
            print(f"[ATTENDANCE CALL ISENTOS WARN] {ext_err}")
        
        from .keyboards import get_presenca_keyboard
        msg = (
            "🌅 **CHAMADA MATUTINA — CGCFN/SISGAB**\n\n"
            "Bom dia Equipe LANÇAMENTO 🚀!\n"
            "Solicito que todos acusem suas rotinas para hoje.\n\n"
            "🚨 *Senhores o regresso é 07:30h e o pronto da presença para o CheGab é até 8h.*\n\n"
            "Selecione a sua situação nos botões abaixo:"
        )
        
        for m in res_ef.data:
            nome_g = m.get('nome_guerra', '').upper()
            tg_id = m.get('telegram_id')
            if tg_id and nome_g not in isentos:
                try:
                    await bot.send_message(tg_id, msg, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                except Exception as e_send:
                    print(f"[ATTENDANCE CALL SEND ERR] {tg_id}: {e_send}")
    except Exception as e:
        print(f"[ATTENDANCE CALL ERR] {e}")


async def trigger_10min_attendance_reminder(bot, force_now=False):
    """Verifica militares pendentes de chamada no dia atual (fuso GMT-3) e envia aviso/cobrança insistente via Telegram."""
    try:
        from timezone import timezone, timedelta
    except Exception:
        from datetime import timezone, timedelta

    tz_gmt3 = timezone(timedelta(hours=-3))
    now = datetime.now(tz_gmt3)
    
    # Se não for disparado manualmente, executa na janela matutina das 07:10h às 09:30h
    if not force_now and not (7 <= now.hour <= 9):
        return 0
        
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn: return 0
        
        hoje_str = now.strftime('%Y-%m-%d')
        
        res_ef = conn.table('efetivo').select('nome_guerra, telegram_id, posto_grad').execute()
        if not res_ef.data: return 0
        
        res_pr = conn.table('presenca_diaria').select('nome_guerra, status').eq('data', hoje_str).execute()
        respondidos = {p['nome_guerra'].upper() for p in res_pr.data if p.get('status')} if res_pr.data else set()
        
        # Inclui militares com isenção ativa de férias/licença no conjunto de respondidos
        try:
            res_ext = conn.table('presenca_diaria').select('nome_guerra, data_fim').in_('status', ['FE', 'L', 'DM']).lte('data', hoje_str).execute()
            if res_ext and res_ext.data:
                for item in res_ext.data:
                    df = item.get('data_fim')
                    if df and df >= hoje_str:
                        respondidos.add(item.get('nome_guerra', '').upper())
        except Exception as ext_err:
            print(f"[REMINDER ISENTOS WARN] {ext_err}")
            
        from .keyboards import get_presenca_keyboard
        
        # Mensagem insistente e contextual conforme o horário
        if now.hour == 7 and now.minute < 30:
            hdr = "⏰ *AVISO DE REGRESSO DE CHAMADA — CGCFN/SISGAB*"
            body = (
                f"🚨 O horário de regresso é até **07:30h** e o pronto ao CheGab é até **08:00h**.\n"
                f"Você ainda **não acusou sua rotina** de hoje!\n\n"
                f"Por favor, selecione sua situação nos botões abaixo:"
            )
        elif (now.hour == 7 and now.minute >= 30) or (now.hour == 8 and now.minute == 0):
            hdr = "🚨 *URGENTE — REGRESSO VENCIDO / PRONTO AO CHEGAB*"
            body = (
                f"⚠️ *ATENÇÃO!* O regresso das 07:30h já passou e o limite do pronto para o CheGab é **08:00h**!\n\n"
                f"Sua presença ainda consta como **PENDENTE**. Toque no seu status IMEDIATAMENTE:"
            )
        else:
            hdr = "🔥 *ALERTA CRÍTICO — PRESENÇA EM ATRASO*"
            body = (
                f"❌ *ATENÇÃO URGENTE!* O horário limite das 08:00h JÁ VENCEU!\n\n"
                f"Consta pendência no seu registro diário. Regularize sua situação para a sargenteação:"
            )

        notified_count = 0
        for m in res_ef.data:
            nome_g = m['nome_guerra'].upper()
            pg = m.get('posto_grad') or ''
            tg_id = m.get('telegram_id')
            if nome_g not in respondidos and tg_id and str(tg_id).strip():
                try:
                    personalized_msg = f"{hdr}\n\n👤 *Militar:* {pg} {nome_g}\n{body}"
                    await bot.send_message(tg_id, personalized_msg, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                    notified_count += 1
                except Exception as e_send:
                    print(f"[ATTENDANCE REMIND ERR] {tg_id}: {e_send}")

        return notified_count
    except Exception as e:
        print(f"[ATTENDANCE REMINDER LOOP ERR] {e}")
        return 0


SENT_2H_REMINDERS = set()

async def send_tactical_2h_reminders(bot):
    """Verifica pautas do dia que iniciam em aproximadamente 2 horas e envia um lembrete tático."""
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn:
            return
            
        now = datetime.now()
        hoje_str = now.strftime('%Y-%m-%d')
        
        res = conn.table('demandas_comunicacao').select('*').eq('data_evento', hoje_str).eq('status', 'aprovada').execute()
        pautas = res.data if (res and res.data) else []
        
        for p in pautas:
            p_id = p.get('id')
            if not p_id or p_id in SENT_2H_REMINDERS:
                continue
                
            hr_str = str(p.get('hora_evento', '09:00'))[:5]
            try:
                ev_time = datetime.strptime(f"{hoje_str} {hr_str}", "%Y-%m-%d %H:%M")
                diff_min = (ev_time - now).total_seconds() / 60
                
                # Se faltar entre 10 min e 130 min (aprox 2 horas)
                if 10 <= diff_min <= 130:
                    SENT_2H_REMINDERS.add(p_id)
                    chat_id = os.getenv("TELEGRAM_CHAT_ID")
                    
                    titulo = str(p.get('titulo_evento', 'Sem Título')).replace('*', '').replace('_', '')
                    local = str(p.get('local_evento', 'N/I')).replace('*', '').replace('_', '')
                    
                    msg = (
                        f"⏰ **LEMBRETE DE COBERTURA EM 2 HORAS!**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📌 **Pauta:** {titulo}\n"
                        f"🕒 **Horário:** {hr_str}h | 📍 **Local:** {local}\n\n"
                        f"🔋 **Prontidão de Equipamentos:**\n"
                        f"• Baterias das câmeras e drones carregadas\n"
                        f"• Cartões de memória limpos e formatados\n"
                        f"• Uniforme previsto para a missão\n\n"
                        f"⚓ _SisGAB — Gestão de Gabinete_"
                    )
                    
                    if chat_id:
                        try:
                            await bot.send_message(chat_id, msg, parse_mode='Markdown')
                        except Exception as e_send:
                            print(f"[TACTICAL 2H REMINDER ERR] {e_send}")
            except Exception as e_t:
                print(f"[TACTICAL 2H TIME PARSE ERR] {e_t}")
    except Exception as e:
        print(f"[TACTICAL 2H REMINDER CRITICAL ERR] {e}")


async def generate_executive_report(bot, chat_id):
    """Gera um relatório executivo resumido de KPIs de produção do mês."""
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn:
            await bot.send_message(chat_id, "⚠️ Banco de dados indisponível no momento.")
            return

        now = datetime.now()
        mes_ano_prefix = now.strftime('%Y-%m')
        
        # Pautas do mês
        res_dem = conn.table('demandas_comunicacao').select('*').gte('data_evento', f"{mes_ano_prefix}-01").execute()
        demandas = res_dem.data if (res_dem and res_dem.data) else []
        
        total = len(demandas)
        concluidas = sum(1 for d in demandas if str(d.get('status')).lower() in ('concluida', 'concluido', 'concluídas'))
        aprovadas = sum(1 for d in demandas if str(d.get('status')).lower() in ('aprovada', 'aprovado'))
        pendentes = sum(1 for d in demandas if str(d.get('status')).lower() in ('pendente', 'pendentes'))
        
        # Categorias mais requisitadas
        cats = {}
        for d in demandas:
            c = str(d.get('in_categoria') or d.get('categoria') or 'Geral').title()
            cats[c] = cats.get(c, 0) + 1
            
        top_cat = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:3]
        top_cat_str = ", ".join([f"{k} ({v})" for k, v in top_cat]) if top_cat else "N/A"
        
        report_msg = (
            f"📊 **RELATÓRIO EXECUTIVO COMSOC — {now.strftime('%m/%Y')}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 **INDICADORES DE PRODUÇÃO:**\n"
            f"• Total de Demandas no Mês: **{total}**\n"
            f"• ✅ Missões Concluídas: **{concluidas}**\n"
            f"• 🟢 Pautas Aprovadas em Execução: **{aprovadas}**\n"
            f"• 🟡 Pautas Aguardando Homologação: **{pendentes}**\n\n"
            f"🎯 **Categorias Principais:** {top_cat_str}\n\n"
            f"⚓ _Central de Inteligência Operacional SisGAB_"
        )
        await bot.send_message(chat_id, report_msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[EXEC REPORT ERR] {e}")
        await bot.send_message(chat_id, f"❌ Erro ao gerar relatório executivo: {e}")

