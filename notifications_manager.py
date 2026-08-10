import os
import json
import asyncio
import threading
from database import get_bot_db_connection as get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERENCES_FILE = os.path.join(BASE_DIR, 'telegram_preferences.json')
file_lock = threading.Lock()

DEFAULT_PREFERENCES = {
    "silence_all": False,
    "notify_new_user": True,
    "notify_demanda": True,
    "notify_homologacao": True,
    "notify_presenca": True,
    "notify_escala": True,
    "notify_aviso": True
}

def load_preferences() -> dict:
    with file_lock:
        if not os.path.exists(PREFERENCES_FILE):
            return {}
        try:
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PREFERENCES] Erro ao carregar preferências: {e}", flush=True)
            return {}

def save_preferences(prefs: dict):
    with file_lock:
        try:
            with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PREFERENCES] Erro ao salvar preferências: {e}", flush=True)

def get_user_preferences(user_id: str) -> dict:
    prefs = load_preferences()
    return prefs.get(str(user_id), DEFAULT_PREFERENCES.copy())

def save_user_preferences(user_id: str, user_prefs: dict):
    prefs = load_preferences()
    prefs[str(user_id)] = user_prefs
    save_preferences(prefs)

def check_notification_enabled(user_id: str, notification_type: str) -> bool:
    """Verifica se o usuário habilitou o tipo de notificação específica no Telegram e não está silenciado.
    Notificações do tipo 'system' sempre são entregues (ex: aprovação de acesso).
    """
    # Notificações de sistema nunca são bloqueadas por preferências
    if notification_type == 'system':
        return True
    user_prefs = get_user_preferences(user_id)
    if user_prefs.get("silence_all", False):
        return False
    
    pref_key = f"notify_{notification_type}"
    return user_prefs.get(pref_key, True)


async def _send_msg_safe(bot, chat_id: int, text: str, reply_markup=None):
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown', reply_markup=reply_markup)
        print(f"[NOTIFY] Mensagem enviada para o chat {chat_id}", flush=True)
    except Exception as e:
        print(f"[NOTIFY] Erro ao enviar mensagem para {chat_id}: {e}", flush=True)

async def send_notification_to_user(telegram_id: str, text: str):
    """Envia uma mensagem privada para um usuário específico se o bot estiver rodando."""
    import telegram_bot
    bot = telegram_bot.bot
    if not bot:
        token = telegram_bot.get_bot_token()
        if not token or os.getenv("DISABLE_TELEGRAM_BOT") == "True":
            return
        try:
            from telebot.async_telebot import AsyncTeleBot
            bot = AsyncTeleBot(token)
        except Exception:
            return
            
    try:
        await _send_msg_safe(bot, int(telegram_id), text)
    except Exception as e:
        print(f"[NOTIFY] Falha ao enviar para {telegram_id}: {e}", flush=True)

async def broadcast_notification(text: str, notification_type: str, role_required: str = None, specific_user_id: str = None, request_id: str = None, specific_telegram_id: str = None):
    """Envia notificação para usuários autorizados baseando-se em preferências."""
    import telegram_bot
    bot = telegram_bot.bot
    if not bot:
        token = telegram_bot.get_bot_token()
        if not token or os.getenv("DISABLE_TELEGRAM_BOT") == "True":
            return
        try:
            from telebot.async_telebot import AsyncTeleBot
            bot = AsyncTeleBot(token)
        except Exception:
            return
            
    if specific_telegram_id:
        await _send_msg_safe(bot, int(specific_telegram_id), text)
        return

    conn = get_db_connection()
    if not conn:
        print("[NOTIFY] Sem banco de dados para transmissão de notificação.", flush=True)
        return
        
    try:
        # Tenta buscar chat ID do grupo nas configurações
        group_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not group_chat_id:
            try:
                res_cfg = conn.table('config').select('*').eq('chave', 'telegram_chat_id').execute()
                if res_cfg.data and res_cfg.data[0].get('valor'):
                    group_chat_id = res_cfg.data[0]['valor'].strip()
            except Exception:
                pass

        markup = None
        if notification_type == "new_user" and request_id:
            from telebot import types
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ Aprovar", callback_data=f"approve_req:{request_id}"),
                types.InlineKeyboardButton("❌ Rejeitar", callback_data=f"reject_req:{request_id}")
            )

        tasks = []
        if group_chat_id:
            try:
                tasks.append(_send_msg_safe(bot, int(group_chat_id), text, reply_markup=markup))
            except Exception as e_grp:
                print(f"[NOTIFY] Erro ao adicionar envio para chat do grupo ({group_chat_id}): {e_grp}", flush=True)

        users_list = []
        try:
            query = conn.table('users').select('*')
            if role_required:
                query = query.eq('role', role_required)
            if specific_user_id:
                query = query.eq('id', specific_user_id)
            res = query.execute()
            if res.data:
                users_list = res.data
        except Exception as u_err:
            print(f"[NOTIFY] Erro ao buscar em 'users': {u_err}. Tentando 'efetivo'...", flush=True)
            try:
                res_ef = conn.table('efetivo').select('*').execute()
                if res_ef.data:
                    users_list = res_ef.data
            except Exception as ef_err:
                print(f"[NOTIFY] Erro ao buscar em 'efetivo': {ef_err}", flush=True)

        if users_list:
            for user in users_list:
                u_id = user.get('id')
                tg_id = user.get('telegram_id')
                if not tg_id or not str(tg_id).strip() or str(tg_id).strip() == group_chat_id:
                    continue
                
                if check_notification_enabled(u_id, notification_type):
                    tasks.append(_send_msg_safe(bot, int(tg_id), text, reply_markup=markup))
            
        if tasks:
            await asyncio.gather(*tasks)
    except Exception as e:
        print(f"[NOTIFY] Erro ao transmitir broadcast {notification_type}: {e}", flush=True)

def notify_telegram(text: str, notification_type: str, role_required: str = None, specific_user_id: str = None, request_id: str = None, custom_chat_id: str = None):
    """Sincronamente despacha o envio de notificação."""
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(broadcast_notification(text, notification_type, role_required, specific_user_id, request_id, specific_telegram_id=custom_chat_id))
        else:
            asyncio.run(broadcast_notification(text, notification_type, role_required, specific_user_id, request_id, specific_telegram_id=custom_chat_id))
    except Exception as e:
        print(f"[NOTIFY ERR] Falha ao despachar notificação de Telegram: {e}", flush=True)


async def broadcast_photo_notification(photo_bytes: bytes, caption: str, notification_type: str = "aviso"):
    """Envia uma foto para todos os usuários autorizados do Telegram baseando-se em preferências."""
    import telegram_bot
    bot = telegram_bot.bot
    if not bot:
        token = telegram_bot.get_bot_token()
        if not token or os.getenv("DISABLE_TELEGRAM_BOT") == "True":
            return
        try:
            from telebot.async_telebot import AsyncTeleBot
            bot = AsyncTeleBot(token)
        except Exception:
            return
            
    conn = get_db_connection()
    if not conn:
        return
        
    try:
        users_list = []
        try:
            res = conn.table('users').select('*').execute()
            if res.data: users_list = res.data
        except Exception:
            try:
                res = conn.table('efetivo').select('*').execute()
                if res.data: users_list = res.data
            except Exception:
                pass

        if users_list:
            tasks = []
            for user in users_list:
                u_id = user.get('id')
                tg_id = user.get('telegram_id')
                if not tg_id or not str(tg_id).strip():
                    continue
                
                if check_notification_enabled(u_id, notification_type):
                    async def send_photo_safe(chat_id, p_bytes, cap):
                        try:
                            await bot.send_photo(chat_id=chat_id, photo=p_bytes, caption=cap, parse_mode='Markdown')
                        except Exception as e:
                            print(f"[NOTIFY] Erro ao enviar foto para {chat_id}: {e}", flush=True)
                            
                    tasks.append(send_photo_safe(int(tg_id), photo_bytes, caption))
            
            if tasks:
                await asyncio.gather(*tasks)
    except Exception as e:
        print(f"[NOTIFY] Erro ao transmitir broadcast de foto: {e}", flush=True)

def notify_telegram_photo(photo_bytes: bytes, caption: str, notification_type: str = "aviso"):
    """Sincronamente despacha o envio de foto via Telegram."""
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(broadcast_photo_notification(photo_bytes, caption, notification_type))
        else:
            asyncio.run(broadcast_photo_notification(photo_bytes, caption, notification_type))
    except Exception as e:
        print(f"[NOTIFY ERR] Falha ao despachar notificação de foto: {e}", flush=True)


def notify_jade_production(event_name: str, count_new: int, count_total_pending: int):
    """Envia notificação via Telegram sobre novas placas na fila de produção JADE."""
    msg = (
        f"🪑 **NOVAS PLACAS JADE NA FILA DE PRODUÇÃO!**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Solenidade:** {event_name}\n"
        f"🆕 **+ {count_new}** nova(s) placa(s) adicionada(s)\n"
        f"⏳ **Total Pendentes na Fila:** {count_total_pending} placa(s)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💡 _Acesse o Módulo JADE no SISGAB para confeccionar._"
    )
    notify_telegram(msg, "system")


def send_recovery_pin_email(to_email: str, pin: str) -> bool:
    """Envia um e-mail formatado em HTML com o código PIN de 6 dígitos para o e-mail do destinatário via SMTP."""
    if not to_email or '@' not in to_email or not pin:
        return False
        
    import smtplib
    import ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    try:
        from database import get_service_db_connection, get_db_connection
        db = get_service_db_connection() or get_db_connection()
        
        smtp_host = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "") or os.getenv("SMTP_PASSWORD", "")
        from_name = "SisGAB - Recuperação de Acesso"
        
        if db:
            try:
                res_host = db.table('config').select('valor').eq('chave', 'smtp_host').execute()
                if res_host.data and res_host.data[0].get('valor'):
                    smtp_host = str(res_host.data[0]['valor'])
                    
                res_port = db.table('config').select('valor').eq('chave', 'smtp_port').execute()
                if res_port.data and res_port.data[0].get('valor'):
                    smtp_port = int(res_port.data[0]['valor'])
                    
                res_u = db.table('config').select('valor').eq('chave', 'smtp_user').execute()
                if res_u.data and res_u.data[0].get('valor'):
                    smtp_user = str(res_u.data[0]['valor'])
                    
                res_p = db.table('config').select('valor').eq('chave', 'smtp_password').execute()
                if res_p.data and res_p.data[0].get('valor'):
                    smtp_pass = str(res_p.data[0]['valor'])
            except Exception as cfg_err:
                print(f"[SMTP CONFIG READ ERR] {cfg_err}")
                
        if not smtp_user or not smtp_pass:
            print("[SMTP] Credenciais SMTP não configuradas. O PIN foi gerado e notificado pelo Telegram.")
            return False
            
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔑 Código PIN de Recuperação: {pin} - SisGAB"
        msg['From'] = f"{from_name} <{smtp_user}>"
        msg['To'] = to_email
        
        text_body = f"Seu código PIN de recuperação do SisGAB é: {pin}\n\nVálido por 15 minutos."
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
        </head>
        <body style="margin:0; padding:0; background-color:#0f0f17; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color:#ffffff;">
          <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color:#0f0f17; padding:40px 10px;">
            <tr>
              <td align="center">
                <table width="100%" max-width="500" border="0" cellspacing="0" cellpadding="0" style="max-width:500px; background-color:#1a1a2e; border:1px solid #c5a059; border-radius:12px; padding:30px; text-align:center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                  <tr>
                    <td>
                      <h1 style="color:#c5a059; font-size:24px; margin:0 0 10px 0; letter-spacing:2px;">SisGAB</h1>
                      <p style="color:#a0a0b0; font-size:14px; margin:0 0 25px 0;">Recuperação de Senha de Acesso</p>
                      <hr style="border:0; border-top:1px solid rgba(197,160,89,0.2); margin:0 0 25px 0;">
                      
                      <p style="color:#e0e0e0; font-size:14px; margin-bottom:15px;">Utilize o código PIN de 6 dígitos abaixo para redefinir a sua senha no site:</p>
                      
                      <div style="background-color:#0f0f17; border:2px dashed #c5a059; border-radius:8px; padding:15px; margin:20px 0; display:inline-block; width:80%;">
                        <span style="font-size:36px; font-weight:bold; color:#ffb300; letter-spacing:8px; font-family:monospace;">{pin}</span>
                      </div>
                      
                      <p style="color:#8888a0; font-size:12px; margin-top:20px;">⏱️ Este código é válido por <strong>15 minutos</strong>.</p>
                      <p style="color:#666680; font-size:11px; margin-top:25px; border-top:1px solid #2a2a3e; padding-top:15px;">Se você não solicitou este código, desconsidere este e-mail.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
            
        print(f"[SMTP SUCCESS] Código PIN {pin} enviado para {to_email}!")
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Falha ao enviar e-mail com PIN: {e}")
        return False


# ─────────────────────────────────────────────────────────────
#  AGENDADOR AUTOMÁTICO DO RELATÓRIO TÁTICO DAS 19:00H (TELEGRAM)
# ─────────────────────────────────────────────────────────────

_SCHEDULER_19H_STARTED = False
_LAST_19H_SENT_DATE = None

def send_daily_19h_telegram_briefing() -> bool:
    """Busca as pautas agendadas para o dia seguinte e envia o relatório tático diário no Telegram."""
    try:
        from database import get_service_db_connection, get_db_connection
        from datetime import datetime, timedelta
        import json

        db = get_service_db_connection() or get_db_connection()
        if not db:
            print("[19H BRIEFING] Erro: Sem conexão ativa com o banco de dados.", flush=True)
            return False

        now_br = datetime.utcnow() - timedelta(hours=3)
        amanha = (now_br + timedelta(days=1)).date()
        amanha_iso = amanha.isoformat()

        dias_semana = {
            0: "SEGUNDA-FEIRA", 1: "TERÇA-FEIRA", 2: "QUARTA-FEIRA",
            3: "QUINTA-FEIRA", 4: "SEXTA-FEIRA", 5: "SÁBADO", 6: "DOMINGO"
        }
        dia_semana_str = dias_semana.get(amanha.weekday(), "")
        data_fmt = amanha.strftime("%d/%m/%Y")

        res = db.table('demandas_comunicacao').select('*').eq('data_evento', amanha_iso).execute()
        pautas = res.data if res.data else []

        pautas_ativas = []
        for p in pautas:
            st = str(p.get('status', '')).strip().lower()
            if st not in ('rejeitado', 'rejeitada', 'cancelado', 'cancelada'):
                pautas_ativas.append(p)

        pautas_ativas.sort(key=lambda x: str(x.get('hora_evento', '09:00'))[:5])

        if not pautas_ativas:
            msg = (
                f"📌 *RELATÓRIO TÁTICO DE AMANHÃ ({data_fmt} - {dia_semana_str})*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🟢 *SITUAÇÃO:* Nenhuma pauta ou compromisso agendado para amanhã.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 _SisGAB Tático • Relatório Automático das 19:00h_\n"
                f"🌐 `https://sisgab-cgcfn.ddns.net`"
            )
        else:
            def format_coberturas(p):
                cob_raw = p.get('tipo_cobertura')
                cat_raw = p.get('categoria_demanda')
                items = []
                if cob_raw:
                    try:
                        items = json.loads(cob_raw) if isinstance(cob_raw, str) else cob_raw
                    except Exception:
                        items = [str(cob_raw)]
                if cat_raw:
                    items.append(str(cat_raw))
                
                icons = []
                full_str = " ".join(items).lower()
                if 'foto' in full_str: icons.append("📸 Fotografia")
                if 'video' in full_str or 'filmagem' in full_str: icons.append("🎥 Vídeo")
                if 'grafico' in full_str or 'design' in full_str: icons.append("🎨 Design Gráfico")
                if 'drone' in full_str or 'aerea' in full_str: icons.append("🚁 Drone")
                if 'rede' in full_str or 'reels' in full_str: icons.append("📱 Redes Sociais")
                if 'cerimonial' in full_str or 'jade' in full_str: icons.append("🪪 Cerimonial")
                
                return " | ".join(icons) if icons else "📌 Cobertura Padrão"

            def get_encarregado_nome(enc_id):
                if not enc_id:
                    return "⚠️ PENDENTE DE DESIGNAÇÃO"
                try:
                    res_m = db.table('efetivo').select('nome_guerra, posto_grad').eq('id', enc_id).execute()
                    if res_m.data:
                        m = res_m.data[0]
                        pg = m.get('posto_grad', '')
                        ng = m.get('nome_guerra', '')
                        return f"{pg} {ng}".strip().upper()
                except Exception:
                    pass
                return f"MILITAR #{enc_id}"

            blocos = []
            for idx, p in enumerate(pautas_ativas, 1):
                tit = str(p.get('titulo_evento', 'Sem Título')).upper()
                hr = str(p.get('hora_evento', '09:00'))[:5]
                loc = str(p.get('local_evento', 'Gabinete')).upper()
                sol = str(p.get('solicitante_nome', 'CGCFN')).upper()
                enc_nome = get_encarregado_nome(p.get('encarregado_id'))
                cobs_txt = format_coberturas(p)
                obs_txt = str(p.get('autoridades') or p.get('observacoes') or '').strip().upper()
                from database import get_demanda_drive_url
                p_drive = get_demanda_drive_url(p)

                linha_obs = f"\n   📝 Briefing: {obs_txt}" if obs_txt else ""
                linha_drive = f"\n   📁 Acervo Drive: {p_drive}" if p_drive else ""

                blocos.append(
                    f"🔹 *{idx}. {hr}h — {tit}*\n"
                    f"   📍 Local: {loc}\n"
                    f"   🛠️ Serviços: {cobs_txt}\n"
                    f"   🎖️ Encarregado: {enc_nome}\n"
                    f"   👤 Solicitante: {sol}"
                    f"{linha_obs}"
                    f"{linha_drive}"
                )

            resumo_pautas = "\n\n".join(blocos)
            qtd = len(pautas_ativas)
            msg = (
                f"📌 *RELATÓRIO TÁTICO DE AMANHÃ ({data_fmt} - {dia_semana_str})*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚨 *ATENÇÃO COMSOC / GABINETE:* Há {qtd} pauta(s) agendada(s) para amanhã.\n\n"
                f"{resumo_pautas}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 _SisGAB Tático • Relatório Automático das 19:00h_\n"
                f"🌐 `https://sisgab-cgcfn.ddns.net`"
            )

        notify_telegram(msg, "demanda")
        print(f"[19H BRIEFING] Relatório enviado no Telegram para {data_fmt} ({len(pautas_ativas)} pautas).", flush=True)
        return True
    except Exception as err:
        print(f"[19H BRIEFING ERROR] Erro ao gerar/enviar relatório das 19h: {err}", flush=True)
        return False


def _get_last_19h_sent_date() -> str:
    """Busca a última data de envio do relatório das 19h no banco de dados ou memória."""
    global _LAST_19H_SENT_DATE
    if _LAST_19H_SENT_DATE:
        return _LAST_19H_SENT_DATE
    try:
        from database import get_bot_db_connection
        conn = get_bot_db_connection()
        if conn:
            res = conn.table('config').select('valor').eq('chave', 'telegram_briefing_19h_last_date').execute()
            if res and res.data and res.data[0].get('valor'):
                _LAST_19H_SENT_DATE = res.data[0]['valor'].strip()
                return _LAST_19H_SENT_DATE
    except Exception as e:
        print(f"[19H READ LAST DATE ERR] {e}")
    return _LAST_19H_SENT_DATE or ""


def _set_last_19h_sent_date(date_str: str):
    """Salva a última data de envio do relatório das 19h no banco de dados e memória."""
    global _LAST_19H_SENT_DATE
    _LAST_19H_SENT_DATE = date_str
    try:
        from database import get_bot_db_connection
        conn = get_bot_db_connection()
        if conn:
            conn.table('config').upsert({'chave': 'telegram_briefing_19h_last_date', 'valor': date_str}, on_conflict='chave').execute()
    except Exception as e:
        print(f"[19H SAVE LAST DATE ERR] {e}")


def start_19h_briefing_scheduler():
    """Inicia a thread em background que verifica se deu 19:00 BRT e despacha o relatório."""
    global _SCHEDULER_19H_STARTED
    if _SCHEDULER_19H_STARTED:
        return
    _SCHEDULER_19H_STARTED = True

    def _loop():
        import time
        from datetime import datetime, timedelta
        print("[19H SCHEDULER] Loop agendador do relatório das 19:00h iniciado com sucesso.", flush=True)
        while True:
            try:
                now_br = datetime.utcnow() - timedelta(hours=3)
                today_str = now_br.strftime('%Y-%m-%d')
                last_sent = _get_last_19h_sent_date()
                
                # Se for 19:00 BRT ou mais tarde e ainda não disparou hoje
                if now_br.hour >= 19 and last_sent != today_str:
                    _set_last_19h_sent_date(today_str)
                    print(f"[19H SCHEDULER] Disparando relatório diário automático das 19:00h ({today_str})...", flush=True)
                    send_daily_19h_telegram_briefing()
            except Exception as loop_err:
                print(f"[19H SCHEDULER LOOP ERR] {loop_err}", flush=True)
            time.sleep(30)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


# Inicia o agendador automaticamente ao carregar o módulo
start_19h_briefing_scheduler()


