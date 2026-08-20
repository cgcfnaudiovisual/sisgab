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
            
        now_br = datetime.utcnow() - timedelta(hours=3)
        hoje_str = now_br.strftime('%Y-%m-%d')
        hoje_br = now_br.strftime('%d/%m/%Y')
        
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


import unicodedata
import re

def _clean_military_name(name_str: str) -> str:
    """Normaliza nome de militar removendo postos/graduações, acentos e caracteres especiais para comparação segura."""
    if not name_str:
        return ""
    text = unicodedata.normalize('NFKD', str(name_str)).encode('ASCII', 'ignore').decode('ASCII').upper()
    # Remove postos e graduações comuns
    pat = r'\b(AE|VA|CA|CMG|CF|CC|CT|1TEN|2TEN|GM|SO|1SG|2SG|3SG|SG|CB|SD|MN|CAP|TEN|CEL|MAJ|MILITAR)\b'
    text = re.sub(pat, '', text)
    # Remove caracteres não alfanuméricos e espaços extras
    text = re.sub(r'[^A-Z0-9]', ' ', text)
    return ' '.join(text.split())

async def trigger_daily_attendance_call(bot, force_now=False):
    """Envia a chamada matutina para todos os militares ativos com Telegram ID às 07:00h (apenas dias úteis, exceto quando forçado)."""
    try:
        from timezone import timezone, timedelta
    except Exception:
        from datetime import timezone, timedelta
        
    tz_gmt3 = timezone(timedelta(hours=-3))
    now = datetime.now(tz_gmt3)

    # Bloqueia chamada matutina automática em finais de semana (Sábado=5, Domingo=6)
    if not force_now and now.weekday() >= 5:
        print(f"[ATTENDANCE CALL] Fim de semana (dia {now.weekday()}). Chamada matutina automática não enviada.", flush=True)
        return

    hoje_str = now.strftime('%Y-%m-%d')
    
    def _fetch_call_data():
        try:
            from database import get_bot_db_connection as get_db_connection
            conn = get_db_connection()
            if not conn: return None, set()
            
            res_ef = conn.table('efetivo').select('id, telegram_id, nome_guerra, posto_grad').execute()
            ef_data = res_ef.data if res_ef and res_ef.data else []

            isentos = set()
            try:
                res_ext = conn.table('presenca_diaria').select('nome_guerra, data_fim').in_('status', ['FE', 'L', 'DM']).lte('data', hoje_str).execute()
                if res_ext and res_ext.data:
                    for item in res_ext.data:
                        df = item.get('data_fim')
                        if df and str(df)[:10] >= hoje_str:
                            ng = str(item.get('nome_guerra') or '').strip()
                            if ng:
                                isentos.add(ng.upper())
                                clean_ng = _clean_military_name(ng)
                                if clean_ng: isentos.add(clean_ng)
            except Exception:
                pass
            return ef_data, isentos
        except Exception as e_fetch:
            print(f"[ATTENDANCE CALL FETCH ERR] {e_fetch}")
            return None, set()

    ef_data, isentos = await asyncio.to_thread(_fetch_call_data)
    if not ef_data:
        return

    from .keyboards import get_presenca_keyboard
    msg = (
        "🌅 **CHAMADA MATUTINA — CGCFN/SISGAB**\n\n"
        "Bom dia Equipe LANÇAMENTO 🚀!\n"
        "Solicito que todos acusem suas rotinas para hoje.\n\n"
        "🚨 *Senhores o regresso é 07:30h e o pronto da presença para o CheGab é até 8h.*\n\n"
        "Selecione a sua situação nos botões abaixo:"
    )
    
    for m in ef_data:
        nome_g = str(m.get('nome_guerra') or '').strip().upper()
        clean_g = _clean_military_name(nome_g)
        tg_id = m.get('telegram_id')
        
        is_isento = (nome_g in isentos) or (clean_g in isentos) or any(t in isentos for t in clean_g.split() if len(t) >= 3)
        if tg_id and not is_isento:
            try:
                await bot.send_message(str(tg_id).strip(), msg, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                await asyncio.sleep(0.03)  # Cede o controle ao loop do asyncio
            except Exception as e_send:
                print(f"[ATTENDANCE CALL SEND ERR] {tg_id}: {e_send}")


async def trigger_10min_attendance_reminder(bot, force_now=False):
    """Verifica militares pendentes de chamada no dia atual e envia lembrete inteligente (ignora fins de semana salvo solicitação manual)."""
    try:
        from timezone import timezone, timedelta
    except Exception:
        from datetime import timezone, timedelta

    tz_gmt3 = timezone(timedelta(hours=-3))
    now = datetime.now(tz_gmt3)
    
    # Bloqueia lembrete em finais de semana (Sábado=5, Domingo=6) salvo se forçado pelo admin/sargenteante
    if not force_now:
        if now.weekday() >= 5:
            print(f"[ATTENDANCE REMINDER] Fim de semana (dia {now.weekday()}). Lembrete automático suspenso.", flush=True)
            return 0
        if not (7 <= now.hour <= 9):
            return 0
        
    hoje_str = now.strftime('%Y-%m-%d')

    def _fetch_reminder_data():
        try:
            from database import get_bot_db_connection as get_db_connection
            conn = get_db_connection()
            if not conn: return None, set(), set(), {}
            
            res_ef = conn.table('efetivo').select('id, nome_guerra, telegram_id, posto_grad').execute()
            ef_data = res_ef.data if res_ef and res_ef.data else []
            if not ef_data: return None, set(), set(), {}

            respondidos_nomes = set()
            respondidos_tids = set()

            PENDING_STATUSES = {'', 'PEND', 'PENDENTE', 'NONE', 'NULL'}

            # 1. Checa escala_diaria no Supabase (data_referencia ou data)
            try:
                # Tenta pelo formato novo (data_referencia, militar_id, status, nome_guerra)
                res_esc = conn.table('escala_diaria').select('*').or_(f"data_referencia.eq.{hoje_str},data.eq.{hoje_str}").execute()
                if res_esc and res_esc.data:
                    for item in res_esc.data:
                        st = str(item.get('status') or item.get('cargo') or '').strip().upper()
                        if st and st not in PENDING_STATUSES:
                            m_id = str(item.get('militar_id') or '').strip()
                            n_g = str(item.get('nome_guerra') or item.get('nome') or '').strip()
                            t_id = str(item.get('telegram_id') or '').strip()
                            if m_id and m_id not in PENDING_STATUSES:
                                respondidos_tids.add(m_id)
                            if t_id and t_id.isdigit():
                                respondidos_tids.add(t_id)
                            if n_g:
                                respondidos_nomes.add(n_g.upper())
                                clean_n = _clean_military_name(n_g)
                                if clean_n:
                                    respondidos_nomes.add(clean_n)
            except Exception as e_esc_chk:
                # Fallback se a coluna data_referencia ou data for específica
                try:
                    res_esc_fb = conn.table('escala_diaria').select('*').execute()
                    if res_esc_fb and res_esc_fb.data:
                        for item in res_esc_fb.data:
                            dt_item = str(item.get('data_referencia') or item.get('data') or '')[:10]
                            if dt_item == hoje_str:
                                st = str(item.get('status') or item.get('cargo') or '').strip().upper()
                                if st and st not in PENDING_STATUSES:
                                    m_id = str(item.get('militar_id') or '').strip()
                                    n_g = str(item.get('nome_guerra') or item.get('nome') or '').strip()
                                    if m_id: respondidos_tids.add(m_id)
                                    if n_g:
                                        respondidos_nomes.add(n_g.upper())
                                        clean_n = _clean_military_name(n_g)
                                        if clean_n: respondidos_nomes.add(clean_n)
                except Exception:
                    pass

            # 2. Checa presenca_diaria no Supabase
            try:
                res_pr = conn.table('presenca_diaria').select('*').eq('data', hoje_str).execute()
                if res_pr and res_pr.data:
                    for p in res_pr.data:
                        st = str(p.get('status') or '').strip().upper()
                        if st and st not in PENDING_STATUSES:
                            ng = str(p.get('nome_guerra') or '').strip()
                            p_tid = str(p.get('telegram_id') or '').strip()
                            p_uid = str(p.get('user_id') or '').strip()
                            p_mid = str(p.get('militar_id') or '').strip()
                            if ng:
                                respondidos_nomes.add(ng.upper())
                                clean_ng = _clean_military_name(ng)
                                if clean_ng: respondidos_nomes.add(clean_ng)
                            if p_tid and p_tid.isdigit(): respondidos_tids.add(p_tid)
                            if p_uid: respondidos_tids.add(p_uid)
                            if p_mid: respondidos_tids.add(p_mid)
            except Exception:
                pass
            
            # 3. Checa presenca_diaria e escala_diaria local (SQLite fallback)
            try:
                from sqlite_adapter import LocalSQLiteClient
                local_db = LocalSQLiteClient()
                res_loc = local_db.table('presenca_diaria').select('*').eq('data', hoje_str).execute()
                if res_loc and res_loc.data:
                    for lp in res_loc.data:
                        st = str(lp.get('status') or '').strip().upper()
                        if st and st not in PENDING_STATUSES:
                            ng = str(lp.get('nome_guerra') or '').strip()
                            p_tid = str(lp.get('telegram_id') or '').strip()
                            if ng:
                                respondidos_nomes.add(ng.upper())
                                clean_ng = _clean_military_name(ng)
                                if clean_ng: respondidos_nomes.add(clean_ng)
                            if p_tid and p_tid.isdigit(): respondidos_tids.add(p_tid)
            except Exception:
                pass

            # 4. Afastados (Férias, Licença, Dispensa Médica) com data_fim ativa
            try:
                res_ext = conn.table('presenca_diaria').select('*').in_('status', ['FE', 'L', 'DM', 'LE', 'LTS', 'DS']).execute()
                if res_ext and res_ext.data:
                    for item in res_ext.data:
                        df = item.get('data_fim')
                        di = str(item.get('data') or item.get('data_referencia') or '')[:10]
                        if df and str(df)[:10] >= hoje_str and di <= hoje_str:
                            ng_ext = str(item.get('nome_guerra') or '').strip()
                            e_tid = str(item.get('telegram_id') or '').strip()
                            e_mid = str(item.get('militar_id') or '').strip()
                            if ng_ext:
                                respondidos_nomes.add(ng_ext.upper())
                                clean_ng = _clean_military_name(ng_ext)
                                if clean_ng: respondidos_nomes.add(clean_ng)
                            if e_tid and e_tid.isdigit(): respondidos_tids.add(e_tid)
                            if e_mid: respondidos_tids.add(e_mid)
            except Exception:
                pass
                
            user_tg_map = {}
            try:
                res_u = conn.table('users').select('id, nome, username, telegram_id').execute()
                if res_u and res_u.data:
                    for u_row in res_u.data:
                        tid = u_row.get('telegram_id')
                        if tid and str(tid).strip():
                            tid_str = str(tid).strip()
                            unm = str(u_row.get('username') or '').strip().upper()
                            if unm: user_tg_map[unm] = tid_str
                            nm = str(u_row.get('nome') or '').strip().upper()
                            if nm:
                                user_tg_map[nm] = tid_str
                                clean_nm = _clean_military_name(nm)
                                if clean_nm: user_tg_map[clean_nm] = tid_str
                                parts = nm.split()
                                if len(parts) > 1:
                                    user_tg_map[parts[-1]] = tid_str
            except Exception:
                pass

            return ef_data, respondidos_nomes, respondidos_tids, user_tg_map
        except Exception as e_f:
            print(f"[REMINDER FETCH ERR] {e_f}")
            return None, set(), set(), {}

    ef_data, respondidos_nomes, respondidos_tids, user_tg_map = await asyncio.to_thread(_fetch_reminder_data)
    if not ef_data:
        return 0

    from .keyboards import get_presenca_keyboard
    
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

    def _is_militar_respondido(m_nome, m_pg, m_tid, m_id):
        # 1. Checa correspondência direta por Telegram ID ou ID
        if m_tid and str(m_tid).strip() in respondidos_tids:
            return True
        if m_id and str(m_id).strip() in respondidos_tids:
            return True

        # 2. Checa por Nome de Guerra / Nome Completo Normalizado
        clean_m = _clean_military_name(m_nome)
        if not clean_m:
            return False

        if (m_nome.upper() in respondidos_nomes) or (clean_m in respondidos_nomes):
            return True

        for r_nome in respondidos_nomes:
            clean_r = _clean_military_name(r_nome)
            if not clean_r:
                continue
            if clean_m == clean_r or clean_m in clean_r or clean_r in clean_m:
                return True
            # Tokens de nome significativos (ex: CALACA, SILVA, SANTOS)
            m_tokens = [t for t in clean_m.split() if len(t) >= 3]
            r_tokens = [t for t in clean_r.split() if len(t) >= 3]
            if any(t in r_tokens for t in m_tokens):
                return True
        return False

    notified_count = 0
    for m in ef_data:
        nome_g = str(m.get('nome_guerra') or '').strip().upper()
        pg = str(m.get('posto_grad') or '').strip()
        m_id = str(m.get('id') or '').strip()
        tg_id = m.get('telegram_id')
        if not tg_id or not str(tg_id).strip():
            tg_id = (
                user_tg_map.get(nome_g)
                or user_tg_map.get(f"{pg} {nome_g}".strip())
                or user_tg_map.get(nome_g.split()[-1] if nome_g else '')
                or user_tg_map.get(_clean_military_name(nome_g))
            )
        
        if nome_g and tg_id and str(tg_id).strip():
            tid = str(tg_id).strip()
            if _is_militar_respondido(nome_g, pg, tid, m_id):
                print(f'[10MIN-CHECK] Militar {pg} {nome_g} (ID: {tid}) -> Presença já registrada, ignorando lembrete.', flush=True)
            else:
                try:
                    personalized_msg = f"{hdr}\n\n👤 *Militar:* {pg} {nome_g}\n{body}"
                    await bot.send_message(tid, personalized_msg, reply_markup=get_presenca_keyboard(), parse_mode='Markdown')
                    notified_count += 1
                    await asyncio.sleep(0.03)  # Cede o controle ao loop do asyncio
                except Exception as e_send:
                    print(f"[ATTENDANCE REMIND ERR] {tid}: {e_send}")

    total_militares = len(ef_data)
    print(f"[CHAMADA MATUTINA {now.strftime('%H:%M')}] 🔔 {notified_count} cobranças enviadas | Total efetivo: {total_militares}")

    return notified_count


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
    """Gera um relatório executivo enriquecido com KPIs de produção, presença, próximos eventos e cautelas."""
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if not conn:
            await bot.send_message(chat_id, "⚠️ Banco de dados indisponível no momento.")
            return

        now = datetime.now()
        mes_ano_prefix = now.strftime('%Y-%m')
        hoje_iso = now.strftime('%Y-%m-%d')
        
        # ═══════════════════════════════════════
        # 1. PAUTAS DO MÊS
        # ═══════════════════════════════════════
        res_dem = conn.table('demandas_comunicacao').select('*').gte('data_evento', f"{mes_ano_prefix}-01").execute()
        demandas = res_dem.data if (res_dem and res_dem.data) else []
        
        total = len(demandas)
        concluidas = sum(1 for d in demandas if str(d.get('status')).lower() in ('concluida', 'concluido', 'concluídas'))
        aprovadas = sum(1 for d in demandas if str(d.get('status')).lower() in ('aprovada', 'aprovado'))
        pendentes = sum(1 for d in demandas if str(d.get('status')).lower() in ('pendente', 'pendentes'))
        rejeitadas = sum(1 for d in demandas if str(d.get('status')).lower() in ('rejeitado', 'rejeitada'))
        em_ajuste = total - concluidas - aprovadas - pendentes - rejeitadas
        
        # Taxa de conclusão
        taxa_conclusao = f"{(concluidas/total*100):.0f}%" if total > 0 else "N/A"
        
        # Barra de progresso visual
        bar_len = 15
        filled = int(bar_len * concluidas / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        
        # Categorias mais requisitadas
        cats = {}
        for d in demandas:
            c = str(d.get('categoria_demanda') or d.get('in_categoria') or d.get('categoria') or 'geral').lower()
            label_map = {
                'audiovisual': '📸 Audiovisual', 'design_arte': '🎨 Design',
                'impressos_albuns': '📕 Impressos', 'redacao_textos': '✍️ Redação',
                'brindes_lembrancas': '🎁 Brindes', 'suporte_evento': '📦 Logístico',
                'outra_tarefa': '⚡ Outra', 'geral': '📋 Geral'
            }
            label = label_map.get(c, f'📋 {c.title()}')
            cats[label] = cats.get(label, 0) + 1
            
        top_cat = sorted(cats.items(), key=lambda x: x[1], reverse=True)[:4]
        top_cat_lines = "\n".join([f"   • {k}: **{v}** pauta(s)" for k, v in top_cat]) if top_cat else "   • Sem dados suficientes"
        
        # ═══════════════════════════════════════
        # 2. PRESENÇA DO DIA
        # ═══════════════════════════════════════
        pres_section = ""
        try:
            res_pres = conn.table('presenca_diaria').select('*').eq('data', hoje_iso).execute()
            presencas = res_pres.data if (res_pres and res_pres.data) else []
            
            res_ef = conn.table('efetivo').select('id').execute()
            total_ef = len(res_ef.data) if (res_ef and res_ef.data) else 0
            
            p_count = sum(1 for p in presencas if str(p.get('status','').upper()) == 'P')
            fe_count = sum(1 for p in presencas if str(p.get('status','').upper()) in ('FE', 'L'))
            dm_count = sum(1 for p in presencas if str(p.get('status','').upper()) in ('DM', 'H'))
            ma_count = sum(1 for p in presencas if str(p.get('status','').upper()) in ('MA', 'MT', 'S'))
            sem_registro = max(0, total_ef - len(presencas))
            
            pres_section = (
                f"\n👥 **CHAMADA DO DIA ({now.strftime('%d/%m')}):**\n"
                f"   🟢 Presentes: **{p_count}** | 🔵 Missão/Serviço: **{ma_count}**\n"
                f"   🟡 Férias/Licença: **{fe_count}** | 🔴 Dispensa/Hospital: **{dm_count}**\n"
                f"   ⚪ Sem Registro: **{sem_registro}** de {total_ef} militares\n"
            )
        except Exception as pres_err:
            print(f"[EXEC REPORT PRES ERR] {pres_err}")
        
        # ═══════════════════════════════════════
        # 3. PRÓXIMOS EVENTOS (3 dias)
        # ═══════════════════════════════════════
        prox_section = ""
        try:
            from datetime import timedelta
            fim_3d = (now + timedelta(days=3)).strftime('%Y-%m-%d')
            res_prox = conn.table('demandas_comunicacao').select('titulo_evento, data_evento, hora_evento, status').gte('data_evento', hoje_iso).lte('data_evento', fim_3d).in_('status', ['aprovada', 'aprovado', 'pendente']).order('data_evento', desc=False).order('hora_evento', desc=False).limit(6).execute()
            prox_events = res_prox.data if (res_prox and res_prox.data) else []
            
            if prox_events:
                prox_lines = []
                for ev in prox_events:
                    dt_ev = str(ev.get('data_evento', ''))[:10]
                    try:
                        parts = dt_ev.split('-')
                        dt_br = f"{parts[2]}/{parts[1]}" if len(parts) == 3 else dt_ev
                    except Exception:
                        dt_br = dt_ev
                    hr = str(ev.get('hora_evento', '09:00'))[:5]
                    tit = str(ev.get('titulo_evento', 'Evento'))[:35]
                    st_icon = '🟢' if 'aprov' in str(ev.get('status','')).lower() else '🟡'
                    prox_lines.append(f"   {st_icon} {dt_br} {hr} — {tit}")
                prox_section = f"\n📅 **PRÓXIMOS EVENTOS (72h):**\n" + "\n".join(prox_lines) + "\n"
        except Exception as prox_err:
            print(f"[EXEC REPORT PROX ERR] {prox_err}")
        
        # ═══════════════════════════════════════
        # 4. CAUTELAS ATIVAS
        # ═══════════════════════════════════════
        caut_section = ""
        try:
            res_caut = conn.table('cautela_equipamentos').select('equipamento').eq('status', 'retirado').execute()
            cautelas_ativas = res_caut.data if (res_caut and res_caut.data) else []
            caut_count = len(cautelas_ativas)
            if caut_count > 0:
                caut_nomes = ", ".join([str(c.get('equipamento', '?'))[:20] for c in cautelas_ativas[:5]])
                if caut_count > 5:
                    caut_nomes += f" (+{caut_count - 5})"
                caut_section = f"\n🔌 **CAUTELAS ATIVAS:** {caut_count} equipamento(s)\n   📦 {caut_nomes}\n"
            else:
                caut_section = "\n🔌 **CAUTELAS ATIVAS:** Nenhuma — acervo 100% disponível ✅\n"
        except Exception as caut_err:
            print(f"[EXEC REPORT CAUT ERR] {caut_err}")

        # ═══════════════════════════════════════
        # MONTAR RELATÓRIO FINAL
        # ═══════════════════════════════════════
        DIAS_SEMANA = {0:'SEG',1:'TER',2:'QUA',3:'QUI',4:'SEX',5:'SÁB',6:'DOM'}
        dia_semana = DIAS_SEMANA.get(now.weekday(), '')
        
        report_msg = (
            f"📊 **RELATÓRIO EXECUTIVO COMSOC**\n"
            f"📅 {dia_semana}, {now.strftime('%d/%m/%Y %H:%M')} — {mes_ano_prefix}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 **PRODUÇÃO DO MÊS:**\n"
            f"   [{bar}] {taxa_conclusao}\n"
            f"   📋 Total: **{total}** | ✅ Concluídas: **{concluidas}**\n"
            f"   🟢 Aprovadas: **{aprovadas}** | 🟡 Pendentes: **{pendentes}**\n"
            f"   🛠️ Outros: **{em_ajuste + rejeitadas}**\n\n"
            f"🎯 **DEMANDA POR CATEGORIA:**\n{top_cat_lines}\n"
            f"{pres_section}"
            f"{prox_section}"
            f"{caut_section}"
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚓ _Central de Inteligência Operacional — SisGAB_"
        )
        try:
            await bot.send_message(chat_id, report_msg, parse_mode='Markdown')
        except Exception:
            clean = report_msg.replace('**','').replace('*','').replace('_','')
            await bot.send_message(chat_id, clean)
    except Exception as e:
        print(f"[EXEC REPORT ERR] {e}")
        await bot.send_message(chat_id, f"❌ Erro ao gerar relatório executivo: {e}")
