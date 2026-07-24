import json
from telebot import types
from datetime import datetime, timedelta
from .client import chat_states
from .utils import check_authorized_user, clear_state, USER_PERMISSIONS_CACHE
from .keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_unauthorized_keyboard


async def finalizar_solicitacao_acesso(bot, message, chat_id, state):
    """Finaliza o wizard de solicitação de acesso: grava no banco e notifica admins."""
    reg_nome = state['data'].get('reg_nome', 'N/I')
    reg_guerra = state['data'].get('reg_guerra', 'N/I')
    reg_email = state['data'].get('reg_email', 'N/I')
    reg_om = state['data'].get('reg_om', 'CGCFN')
    reg_funcao = state['data'].get('reg_funcao', 'Gabinete')
    
    try:
        from database import get_bot_db_connection as get_db_connection
        conn = get_db_connection()
        if conn:
            # Vincular no efetivo por e-mail e nome de guerra
            try:
                conn.table('efetivo').update({'telegram_id': str(chat_id)}).eq('email', reg_email).execute()
            except Exception as ef_err:
                print(f"[Bot Link Efetivo Email Error] {ef_err}")
            try:
                conn.table('efetivo').update({'telegram_id': str(chat_id)}).ilike('nome_guerra', reg_guerra).execute()
            except Exception as ef_err2:
                print(f"[Bot Link Efetivo Guerra Error] {ef_err2}")
            try:
                conn.table('users').update({'telegram_id': str(chat_id)}).ilike('username', reg_guerra).execute()
            except Exception as u_err:
                print(f"[Bot Link Users Error] {u_err}")
            try:
                import uuid
                conn.table('registration_requests').insert({
                    'id': str(uuid.uuid4()),
                    'email': reg_email,
                    'nome_completo': reg_nome,
                    'nome_guerra': reg_guerra,
                    'setor_om': reg_om,
                    'telegram_id': str(chat_id),
                    'tipo_usuario': 'comsoc' if 'CGCFN' in reg_om.upper() else 'externo',
                    'status': 'pendente'
                }).execute()
            except Exception as reg_err:
                print(f"[Bot Reg Request Insert Error] {reg_err}")

            # NOTIFICAR OS ADMINISTRADORES E SUPERVISORES VIA TELEGRAM
            try:
                from notifications_manager import notify_telegram
                alert_txt = (
                    f"🔔 **NOVA SOLICITAÇÃO DE ACESSO AO SISGAB** ⚓\n\n"
                    f"👤 **Militar:** {reg_guerra} ({reg_nome})\n"
                    f"📧 **E-mail:** {reg_email}\n"
                    f"🏢 **OM/Unidade:** {reg_om}\n"
                    f"🎯 **Seção/Função:** {reg_funcao}\n"
                    f"📱 **Telegram ID:** `{chat_id}`\n\n"
                    f"👉 *Acesse o painel 'Usuários e Permissões' no SisGAB para aprovar.*"
                )
                
                admin_tg_ids = set()
                try:
                    res_admin_ef = conn.table('efetivo').select('telegram_id').in_('role', ['admin', 'supervisor', 'oficial_gab']).execute()
                    if res_admin_ef and res_admin_ef.data:
                        for adm in res_admin_ef.data:
                            if adm_tg := adm.get('telegram_id'):
                                admin_tg_ids.add(str(adm_tg))
                except Exception as ef_search_err:
                    print(f"[EF SEARCH ERR] {ef_search_err}")

                try:
                    res_admin_u = conn.table('users').select('telegram_id').in_('role', ['admin', 'supervisor', 'oficial_gab']).execute()
                    if res_admin_u and res_admin_u.data:
                        for adm in res_admin_u.data:
                            if adm_tg := adm.get('telegram_id'):
                                admin_tg_ids.add(str(adm_tg))
                except Exception as u_search_err:
                    print(f"[U SEARCH ERR] {u_search_err}")

                if admin_tg_ids:
                    for adm_tg in admin_tg_ids:
                        notify_telegram(alert_txt, "system", custom_chat_id=adm_tg)
                else:
                    notify_telegram(alert_txt, "system", role_required="admin")
            except Exception as notif_err:
                print(f"[BOT ADMIN NOTIFY REG ERR] {notif_err}")

        await bot.reply_to(message, "✅ Solicitação de acesso registrada e enviada aos administradores!\nVocê receberá uma notificação assim que seu acesso for aprovado.", reply_markup=get_unauthorized_keyboard())
    except Exception as ex:
        await bot.reply_to(message, f"❌ Erro ao registrar solicitação: {ex}", reply_markup=get_unauthorized_keyboard())
    finally:
        clear_state(chat_id)


def _get_weekly_events_text():
    """Busca eventos dos próximos 7 dias na tabela demandas_comunicacao e retorna texto formatado."""
    try:
        from database import get_bot_db_connection as get_db_connection
        db = get_db_connection()
        if not db:
            return "⚠️ Banco de dados indisponível."
        
        hoje = datetime.now().date()
        fim_semana = hoje + timedelta(days=7)
        
        res = db.table('demandas_comunicacao').select('*').gte(
            'data_evento', hoje.isoformat()
        ).lte(
            'data_evento', fim_semana.isoformat()
        ).order('data_evento', desc=False).execute()
        
        events = res.data if res.data else []
        
        if not events:
            return (
                f"📅 **AGENDA SEMANAL — COMSOC/CGCFN**\n"
                f"Período: {hoje.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}\n\n"
                f"🟢 Nenhum evento ou pauta agendada para os próximos 7 dias.\n\n"
                f"Use **➕ Criar Demanda** para adicionar uma nova pauta."
            )
        
        msg = (
            f"📅 **AGENDA SEMANAL — COMSOC/CGCFN**\n"
            f"Período: {hoje.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}\n\n"
        )
        
        for idx, ev in enumerate(events, 1):
            status_icon = '🟢' if ev.get('status') in ('aprovado', 'aprovada') else '🟡'
            try:
                data_br = datetime.strptime(str(ev.get('data_evento', '')), '%Y-%m-%d').strftime('%d/%m')
            except Exception:
                data_br = str(ev.get('data_evento', 'N/I'))
            
            msg += (
                f"{status_icon} **{idx}. {ev.get('titulo_evento', 'Sem Título')}**\n"
                f"   📅 {data_br} às {ev.get('hora_evento', '09:00')}\n"
                f"   📍 {ev.get('local_evento', 'N/I')}\n"
                f"   👤 {ev.get('solicitante_nome', 'N/I')}\n\n"
            )
        
        msg += f"📊 Total: **{len(events)} evento(s)** na semana.\n⚓ _SisGAB — Gestão de Gabinete_"
        return msg
    except Exception as e:
        return f"❌ Erro ao buscar agenda: {e}"


def register_common_handlers(bot):
    
    @bot.message_handler(func=lambda msg: True)
    async def handle_all_messages(message):
        chat_id = message.chat.id
        
        # Guard: mensagens sem texto (stickers, contatos, etc)
        if not message.text:
            return
        
        text = message.text.strip()
        
        # =====================================================================
        # SEÇÃO 1: Roteamento de Teclado Principal (usuário SEM estado ativo)
        # =====================================================================
        if chat_id not in chat_states:
            profile = await check_authorized_user(message.from_user.id)
            
            # --- Usuário NÃO autorizado ---
            if not profile:
                if text.lower() in ["📝 solicitar acesso", "/start", "/solicitar", "/acesso", "solicitar", "solicitar acesso", "acesso"]:
                    # Inicia wizard de solicitação
                    chat_states[chat_id] = {
                        'action': 'settings',
                        'step': 'request_access_name',
                        'user': None,
                        'data': {}
                    }
                    await bot.reply_to(
                        message, 
                        f"📝 **SOLICITAÇÃO DE ACESSO — SISGAB** ⚓\n\n"
                        f"Bem-vindo! Seu Telegram ID é `{chat_id}`.\n\n"
                        f"Por favor, informe seu **Posto ou Graduação** (ex: Sgt, Ten, Cap, Civ):", 
                        reply_markup=get_cancel_keyboard(), 
                        parse_mode='Markdown'
                    )
                else:
                    await bot.reply_to(
                        message, 
                        f"⚓ **Assistente SisGAB**\n\n"
                        f"Olá! Seu acesso ainda não está liberado no sistema.\n"
                        f"📱 **Seu Telegram ID:** `{chat_id}`\n\n"
                        f"Clique no botão **📝 Solicitar Acesso** abaixo ou envie /solicitar para pedir seu cadastro.", 
                        reply_markup=get_unauthorized_keyboard(),
                        parse_mode='Markdown'
                    )
                return

            # --- Usuário autorizado: roteamento dos botões do menu ---
            allowed = USER_PERMISSIONS_CACHE.get(message.from_user.id, set())
            is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')

            if text == "⚙️ Configurações":
                from .handlers_settings import register_settings_handlers
                # Dispara diretamente o comando /settings via handler
                clear_state(chat_id)
                chat_states[chat_id] = {
                    'action': 'settings',
                    'step': 'choose_option',
                    'user': profile,
                    'data': {}
                }
                from .keyboards import get_settings_keyboard
                is_admin = str(profile.get('role', '')).strip().lower() == 'admin'
                await bot.reply_to(
                    message,
                    "⚙️ **CONFIGURAÇÕES DO OPERADOR - SISGAB**\n\n"
                    f"👤 **Operador:** `{profile.get('nome', profile.get('nome_guerra', 'Militar'))}`\n\n"
                    "Escolha uma das opções abaixo:",
                    reply_markup=get_settings_keyboard(True, is_admin),
                    parse_mode='Markdown'
                )

            elif text == "📸 Cadastro Facial":
                chat_states[chat_id] = {
                    'action': 'cadastro_facial',
                    'step': 'send_selfie',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(
                    message, 
                    "📸 **CADASTRO FACIAL — RECONHECIMENTO AUTOMÁTICO**\n\n"
                    "Por favor, envie uma **selfie frontal** com boa iluminação.\n\n"
                    "O sistema processará sua foto para habilitar o reconhecimento facial nas coberturas fotográficas.", 
                    reply_markup=get_cancel_keyboard(), 
                    parse_mode='Markdown'
                )

            elif text == "🔍 Buscar Minhas Fotos":
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco offline.")
                    return
                try:
                    res = db.table('photo_matches').select('*').eq('user_id', profile['id']).execute()
                    if res.data:
                        msg = "📸 **MINHAS FOTOS IDENTIFICADAS:**\n\n"
                        for match in res.data[:10]:
                            score = match.get('similarity_score', 0)
                            icon = "🟢" if score > 0.85 else "🟡"
                            msg += f"{icon} {match.get('photo_file', 'foto')} — Confiança: {score:.0%}\n"
                        await bot.reply_to(message, msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    else:
                        await bot.reply_to(message, "📭 Nenhuma foto identificada até o momento.", reply_markup=get_main_menu_keyboard(is_operator))
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro: {e}", reply_markup=get_main_menu_keyboard(is_operator))

            elif text == "ℹ️ Ajuda":
                help_msg = (
                    "⚓ **AJUDA — SISGAB BOT**\n\n"
                    "Este é o assistente oficial do Sistema de Gestão de Gabinete (SisGAB) do CGCFN.\n\n"
                    "📋 **/menu** — Exibe o menu principal\n"
                    "⚙️ **/settings** — Configurações e notificações\n"
                    "❌ **/cancelar** — Cancela a operação atual\n\n"
                    "📅 **Agenda Semanal** — Veja os próximos eventos\n"
                    "➕ **Criar Demanda** — Solicite cobertura COMSOC\n"
                    "🤖 **Digerir Pauta (IA)** — Processe questionários com Gemini\n\n"
                    "💡 _Desenvolvido por Sargento Calaça 🇧🇷_"
                )
                await bot.reply_to(message, help_msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')

            elif text == "📋 Pautas COMSOC":
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco offline.")
                    return
                try:
                    res = db.table('demandas_comunicacao').select('*').order('data_evento', desc=False).limit(10).execute()
                    if res.data:
                        msg = "📋 **PAUTAS COMSOC — ÚLTIMAS 10:**\n\n"
                        for p in res.data:
                            status_icon = '🟢' if p.get('status') in ('aprovado', 'aprovada') else '🟡'
                            msg += (
                                f"{status_icon} **{p['titulo_evento']}**\n"
                                f"   📅 {p.get('data_evento', 'N/I')} | 📍 {p.get('local_evento', 'N/I')}\n"
                                f"   👤 {p.get('solicitante_nome', 'N/I')} | Status: {p.get('status', 'pendente')}\n\n"
                            )
                        await bot.reply_to(message, msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    else:
                        await bot.reply_to(message, "📭 Nenhuma pauta cadastrada no momento.", reply_markup=get_main_menu_keyboard(is_operator))
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro: {e}")

            elif text in ["📅 Agenda Semanal", "📅 Agenda Google", "/agenda"]:
                # Mostra eventos dos próximos 7 dias do banco
                weekly_msg = _get_weekly_events_text()
                google_cal_url = "https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20"
                weekly_msg += f"\n\n🔗 [Abrir Google Calendar Oficial]({google_cal_url})"
                await bot.reply_to(message, weekly_msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
            
            elif text == "🔌 Cautelas Ativas":
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco offline.")
                    return
                try:
                    res = db.table('cautela_equipamentos').select('*').eq('status', 'retirado').execute()
                    if res.data:
                        msg_c = "🔌 **CAUTELAS DE EQUIPAMENTOS ATIVAS:**\n\n"
                        for c in res.data:
                            pessoal_tag = " [PESSOAL]" if c.get('e_pessoal') == 1 else ""
                            msg_c += (
                                f"🔋 **{c['equipamento']}**{pessoal_tag}\n"
                                f"👤 *Retirado por:* {c['retirado_por']}\n"
                                f"📅 *Data:* {c['data_retirada'][:16].replace('T', ' ')}\n\n"
                            )
                        await bot.reply_to(message, msg_c, reply_markup=get_main_menu_keyboard(True), parse_mode='Markdown')
                    else:
                        await bot.reply_to(message, "🔌 Nenhum equipamento em cautela no momento.", reply_markup=get_main_menu_keyboard(True))
                except Exception as ex:
                    await bot.reply_to(message, f"❌ Erro ao listar cautelas: {ex}")

            elif text == "➕ Criar Demanda":
                chat_states[chat_id] = {
                    'action': 'criar_demanda',
                    'step': 'solicitante_nome',
                    'user': profile,
                    'data': {},
                    'history_steps': []
                }
                await bot.reply_to(
                    message, 
                    "➕ **NOVA DEMANDA COMSOC**\n\nQual o **Nome completo do Solicitante** da cobertura?", 
                    reply_markup=get_cancel_keyboard(), 
                    parse_mode='Markdown'
                )

            elif text == "🤖 Digerir Pauta (IA)":
                chat_states[chat_id] = {
                    'action': 'digerir_pauta_ia',
                    'step': 'send_raw_text',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(
                    message, 
                    "🤖 **DIGERIR QUESTIONÁRIO COM IA (GEMINI)**\n\n"
                    "Por favor, **cole a resposta bruta ou questionário** enviado pelo solicitante no WhatsApp/Telegram.\n\n"
                    "O Gemini irá processar o texto e criar a pauta de forma automatizada no banco de dados!", 
                    reply_markup=get_cancel_keyboard(), 
                    parse_mode='Markdown'
                )

            elif text == "❌ Cancelar":
                clear_state(chat_id)
                await bot.reply_to(message, "Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
            else:
                await bot.reply_to(message, "⚓ Assistente SisGAB Ativo. Envie /menu para opções.", reply_markup=get_main_menu_keyboard(is_operator))
            return

        # =====================================================================
        # SEÇÃO 2: Processamento do Estado / Wizard Ativo
        # =====================================================================
        state = chat_states.get(chat_id)
        if not state:
            return
            
        action = state.get('action')
        step = state.get('step')
        profile = state.get('user')
        is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
        
        # Cancelamento global
        if text.lower() in ['cancelar', '❌ cancelar']:
            clear_state(chat_id)
            await bot.reply_to(message, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
            return
            
        # ----- WIZARD: Solicitação de Acesso -----
        if action == 'settings':
            if step == 'request_access_name':
                state['data']['reg_nome'] = text
                state['step'] = 'request_access_guerra'
                await bot.reply_to(message, "👮 Digite seu **Nome de Guerra** (ex: Silva):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
            elif step == 'request_access_guerra':
                state['data']['reg_guerra'] = text
                state['step'] = 'request_access_email'
                await bot.reply_to(message, "📧 Digite seu **E-mail institucional** (ex: militar@marinha.mil.br):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
            elif step == 'request_access_email':
                state['data']['reg_email'] = text.strip().lower()
                state['step'] = 'request_access_om'
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                markup.row(types.KeyboardButton("🏛️ CGCFN"))
                markup.row(types.KeyboardButton("⚓ ComNavOper"), types.KeyboardButton("⚓ Com1ºDN"))
                markup.row(types.KeyboardButton("🏢 Outra OM"), types.KeyboardButton("❌ Cancelar"))
                await bot.reply_to(message, "🏢 **Selecione a sua Organização Militar (OM):**", reply_markup=markup, parse_mode='Markdown')
                
            elif step == 'request_access_om':
                selected_om = text.strip()
                state['data']['reg_om'] = selected_om
                
                if "CGCFN" in selected_om.upper():
                    state['step'] = 'request_access_funcao'
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    markup.row(types.KeyboardButton("📸 ComSoc"), types.KeyboardButton("🛡️ Gabinete"))
                    markup.row(types.KeyboardButton("📜 Ajudantaria"), types.KeyboardButton("⚙️ Operações / Outro"))
                    markup.row(types.KeyboardButton("❌ Cancelar"))
                    await bot.reply_to(message, "🎯 **Informe a sua Seção / Função no CGCFN:**", reply_markup=markup, parse_mode='Markdown')
                else:
                    state['data']['reg_funcao'] = 'Solicitante Externo'
                    await finalizar_solicitacao_acesso(bot, message, chat_id, state)
                    
            elif step == 'request_access_funcao':
                state['data']['reg_funcao'] = text.strip()
                await finalizar_solicitacao_acesso(bot, message, chat_id, state)
            return

        # ----- WIZARD: Digerir Pauta com IA (Gemini) -----
        if action == 'digerir_pauta_ia':
            if step == 'send_raw_text':
                await bot.reply_to(message, "⏳ Analisando questionário com Gemini...")
                try:
                    import ai_helper
                    
                    response_json = ai_helper.digest_demand_questionnaire(text)
                    dados = json.loads(response_json)
                    
                    # Salva no banco
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    if db:
                        registro = {
                            'solicitante_nome': dados.get('solicitante_nome', 'N/I').upper(),
                            'setor': dados.get('setor', 'Gabinete').upper(),
                            'contato': dados.get('contato', 'N/I'),
                            'titulo_evento': dados.get('titulo_evento', 'Evento Sem Título').upper(),
                            'data_evento': dados.get('data_evento', datetime.now().strftime('%Y-%m-%d')),
                            'hora_evento': dados.get('hora_evento', '09:00'),
                            'local_evento': dados.get('local_evento', 'Gabinete').upper(),
                            'tipo_cobertura': '["foto", "video"]',
                            'autoridades': dados.get('autoridades', ''),
                            'score_esforco': 2.0,
                            'status': 'pendente'
                        }
                        
                        db.table('demandas_comunicacao').insert(registro).execute()
                        
                        confirm_msg = (
                            "✅ **Pauta processada e salva com sucesso via IA!**\n\n"
                            f"📌 **Evento:** {registro['titulo_evento']}\n"
                            f"📅 **Data:** {registro['data_evento']} às {registro['hora_evento']}\n"
                            f"📍 **Local:** {registro['local_evento']}\n"
                            f"👤 **Solicitante:** {registro['solicitante_nome']}\n\n"
                            "A pauta foi adicionada à lista de pendentes e aguarda homologação do supervisor."
                        )
                        await bot.reply_to(message, confirm_msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                        
                        # Dispara broadcast para avisar administradores sobre nova pauta
                        from notifications_manager import notify_telegram
                        notify_telegram(
                            f"🆕 **Nova Pauta Criada via IA (Telegram)**\n\n"
                            f"📌 Evento: {registro['titulo_evento']}\n"
                            f"📅 Data: {registro['data_evento']}\n"
                            f"Acesse o painel web ou use o menu do bot para tramitar.",
                            "new_user"
                        )
                    else:
                        await bot.reply_to(message, "⚠️ Erro ao salvar: Banco indisponível.")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao digerir questionário: {e}\nPor favor, tente enviar novamente ou criar manualmente.", reply_markup=get_main_menu_keyboard(is_operator))
                finally:
                    clear_state(chat_id)
            return

        # ----- WIZARD: Criar Demanda (12 passos) -----
        if action == 'criar_demanda':
            from .keyboards import (
                get_om_keyboard, get_coverage_keyboard, get_video_format_keyboard,
                get_yes_no_keyboard, get_confirm_demanda_keyboard
            )
            
            # Suporte ao botão "⬅️ Voltar"
            if text in ["⬅️ Voltar", "voltar"] and state.get('history_steps'):
                prev_step, prev_data = state['history_steps'].pop()
                state['step'] = prev_step
                state['data'] = prev_data
                await bot.reply_to(
                    message,
                    f"⬅️ Voltando ao passo anterior (`{prev_step}`). Por favor, responda novamente:",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='Markdown'
                )
                return

            history = state.setdefault('history_steps', [])

            if step == 'solicitante_nome':
                history.append(('solicitante_nome', dict(state['data'])))
                state['data']['solicitante_nome'] = text
                state['step'] = 'solicitante_om'
                await bot.reply_to(
                    message, 
                    "[Passo 2/12] ⚓ Qual a **Organização Militar (OM)** solicitante?", 
                    reply_markup=get_om_keyboard(), 
                    parse_mode='Markdown'
                )

            elif step == 'solicitante_om':
                history.append(('solicitante_om', dict(state['data'])))
                if "CGCFN" in text.upper():
                    state['data']['setor'] = "CGCFN"
                    state['data']['contato'] = "21982043314 / Ramal CGCFN"
                    state['step'] = 'titulo'
                    await bot.reply_to(message, "[Passo 3/10] ✍️ Qual o **Título do Evento ou Pauta** da cobertura?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                else:
                    state['step'] = 'solicitante_om_custom'
                    await bot.reply_to(message, "🏢 Por favor, digite o nome da **Outra OM**:", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'solicitante_om_custom':
                history.append(('solicitante_om_custom', dict(state['data'])))
                state['data']['setor'] = text.upper()
                state['step'] = 'contato'
                await bot.reply_to(message, "[Passo 3/10] 📞 Qual o **Ramal ou Telefone** de contato?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'contato':
                history.append(('contato', dict(state['data'])))
                state['data']['contato'] = text
                state['step'] = 'titulo'
                await bot.reply_to(message, "[Passo 4/10] ✍️ Qual o **Título do Evento ou Pauta** da cobertura?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'titulo':
                history.append(('titulo', dict(state['data'])))
                state['data']['titulo'] = text
                state['step'] = 'data_evento'
                await bot.reply_to(message, "[Passo 5/10] 📅 Qual a **Data do Evento**? (ex: 25/07/2026 - Término opcional):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'data_evento':
                history.append(('data_evento', dict(state['data'])))
                date_txt = text.strip()
                parsed = False
                
                # Tenta formatos comuns de entrada de data
                for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y'):
                    try:
                        date_txt = datetime.strptime(date_txt, fmt).strftime('%Y-%m-%d')
                        parsed = True
                        break
                    except ValueError:
                        continue
                
                # Fallback: Se digitou sem ano (ex: "20/07"), assume o ano atual
                if not parsed and '/' in date_txt and date_txt.count('/') == 1:
                    try:
                        temp_date = f"{date_txt}/{datetime.now().year}"
                        date_txt = datetime.strptime(temp_date, '%d/%m/%Y').strftime('%Y-%m-%d')
                    except Exception:
                        pass
                        
                state['data']['data_evento'] = date_txt
                state['data']['data_fim'] = date_txt # Padrão: início e término no mesmo dia se não informado
                state['step'] = 'hora_evento'
                await bot.reply_to(message, "[Passo 6/10] ⏰ Qual o **Horário de Início**? (ex: 09:00):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'hora_evento':
                history.append(('hora_evento', dict(state['data'])))
                state['data']['hora_evento'] = text
                state['step'] = 'local'
                await bot.reply_to(message, "[Passo 7/10] 📍 Qual o **Local exato do Evento**?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'local':
                history.append(('local', dict(state['data'])))
                state['data']['local'] = text
                state['step'] = 'uniforme'
                await bot.reply_to(message, "[Passo 8/10] 👔 Qual o **Uniforme** do evento? (ex: 3.3, 4.4, Passeio):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'uniforme':
                history.append(('uniforme', dict(state['data'])))
                state['data']['uniforme'] = text
                state['step'] = 'autoridades'
                await bot.reply_to(message, "[Passo 9/10] 👑 Quais **Autoridades** estarão presentes? (se nenhuma, digite Nenhuma):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'autoridades':
                history.append(('autoridades', dict(state['data'])))
                state['data']['autoridades'] = text
                state['step'] = 'choose_coverage'
                await bot.reply_to(
                    message, 
                    "[Passo 10/10] 📸 **Tipo de Serviço / Escopo de Cobertura**\n\nSelecione o serviço nos botões abaixo:", 
                    reply_markup=get_coverage_keyboard(), 
                    parse_mode='Markdown'
                )

            elif step == 'choose_coverage':
                history.append(('choose_coverage', dict(state['data'])))
                coverage_txt = text.upper()
                coberturas = []
                if "GRAFICO" in coverage_txt or "GRÁFICO" in coverage_txt or "DESIGN" in coverage_txt:
                    coberturas.append("grafico")
                if "FOTO" in coverage_txt:
                    coberturas.append("foto")
                if "VIDEO" in coverage_txt or "VÍDEO" in coverage_txt:
                    coberturas.append("video")
                if "DRONE" in coverage_txt:
                    coberturas.append("drone")
                if "REDES" in coverage_txt or "MÍDIAS" in coverage_txt:
                    coberturas.append("redes")
                if "COMPLETO" in coverage_txt or "TUDO" in coverage_txt:
                    coberturas = ["foto", "video", "grafico", "drone", "redes"]
                
                if not coberturas:
                    coberturas = ["foto", "video"]
                state['data']['tipo_cobertura'] = json.dumps(coberturas)
                if "DRONE" in coverage_txt:
                    coberturas.append("drone")
                if not coberturas:
                    coberturas = ["foto"]

                state['data']['coberturas'] = coberturas
                state['data']['coberturas_str'] = text
                state['step'] = 'choose_format'
                await bot.reply_to(
                    message, 
                    "[Passo 11/12] 🎬 **Formato de entrega do Vídeo desejado**\n\nSelecione o formato utilizando os botões abaixo:", 
                    reply_markup=get_video_format_keyboard(), 
                    parse_mode='Markdown'
                )

            elif step == 'choose_format':
                history.append(('choose_format', dict(state['data'])))
                state['data']['formato_video'] = text
                state['step'] = 'transporte'
                await bot.reply_to(
                    message, 
                    "[Passo 12/12] 🚗 **Logística**\nHá transporte assegurado para a equipe de cobertura e equipamentos?", 
                    reply_markup=get_yes_no_keyboard("Sim, Transporte Assegurado", "Não Assegurado"), 
                    parse_mode='Markdown'
                )

            elif step == 'transporte':
                history.append(('transporte', dict(state['data'])))
                state['data']['transporte'] = text
                state['step'] = 'review_confirm'
                
                d = state['data']
                resumo = (
                    "📋 **REVISÃO DA SOLICITAÇÃO DE PAUTA / CGCFN**\n\n"
                    f"👤 **Solicitante:** {d.get('solicitante_nome')}\n"
                    f"🏢 **OM / Setor:** {d.get('setor')}\n"
                    f"📞 **Contato:** {d.get('contato')}\n"
                    f"📌 **Evento:** {d.get('titulo')}\n"
                    f"📅 **Data:** {d.get('data_evento')}\n"
                    f"⏰ **Horário:** {d.get('hora_evento')}\n"
                    f"📍 **Local:** {d.get('local')}\n"
                    f"👔 **Uniforme:** {d.get('uniforme')}\n"
                    f"👑 **Autoridades:** {d.get('autoridades')}\n"
                    f"📸 **Cobertura:** {d.get('coberturas_str')}\n"
                    f"🎬 **Formato Vídeo:** {d.get('formato_video')}\n"
                    f"🚗 **Transporte:** {d.get('transporte')}\n\n"
                    "⚠️ *Confirma os dados acima para cadastrar a solicitação?*"
                )
                await bot.reply_to(message, resumo, reply_markup=get_confirm_demanda_keyboard(), parse_mode='Markdown')

            elif step == 'review_confirm':
                if "Confirmar" in text or "✅" in text:
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    if db:
                        try:
                            d = state['data']
                            registro = {
                                'solicitante_nome': d['solicitante_nome'].upper(),
                                'setor': d['setor'].upper(),
                                'contato': d['contato'],
                                'titulo_evento': d['titulo'].upper(),
                                'data_evento': d['data_evento'],
                                'hora_evento': d['hora_evento'],
                                'local_evento': d['local'].upper(),
                                'tipo_cobertura': json.dumps(d.get('coberturas', ['foto'])),
                                'autoridades': d.get('autoridades', ''),
                                'score_esforco': 1.5,
                                'status': 'pendente'
                            }
                            db.table('demandas_comunicacao').insert(registro).execute()
                            await bot.reply_to(message, "✅ **Demanda cadastrada com sucesso!**\nAguardando homologação do Supervisor responsável.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')

                            # Dispara broadcast para avisar administradores sobre nova pauta
                            from notifications_manager import notify_telegram
                            notify_telegram(
                                f"🆕 **Nova Pauta Criada via Telegram**\n\n"
                                f"📌 Evento: {registro['titulo_evento']}\n"
                                f"👤 Solicitante: {registro['solicitante_nome']} ({registro['setor']})\n"
                                f"📅 Data: {registro['data_evento']}\n"
                                f"Acesse o painel web ou use o menu do bot para tramitar.",
                                "new_user"
                            )
                        except Exception as err:
                            await bot.reply_to(message, f"❌ Erro ao salvar no banco: {err}", reply_markup=get_main_menu_keyboard(is_operator))
                    else:
                        await bot.reply_to(message, "⚠️ Banco indisponível. Ação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
                    clear_state(chat_id)
                elif "Reiniciar" in text or "✏️" in text:
                    state['step'] = 'solicitante_nome'
                    state['data'] = {}
                    state['history_steps'] = []
                    await bot.reply_to(message, "✏️ **Formulação Reiniciada**\n\n[Passo 1/12] 👤 Qual o **Posto/Graduação e Nome Completo** do Solicitante?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                else:
                    await bot.reply_to(message, "Selecione uma das opções nos botões abaixo:", reply_markup=get_confirm_demanda_keyboard())
            return


    @bot.message_handler(content_types=['photo'])
    async def handle_photo_messages(message):
        import os
        chat_id = message.chat.id
        if chat_id not in chat_states:
            await bot.reply_to(message, "💡 Se deseja cadastrar seu rosto, primeiro vá em Configurações ➔ Cadastro Facial.")
            return
            
        state = chat_states[chat_id]
        if state.get('action') == 'cadastro_facial' and state.get('step') == 'send_selfie':
            try:
                file_info = message.photo[-1]
                file_id = file_info.file_id
                selfies_dir = os.path.join("assets", "selfies")
                os.makedirs(selfies_dir, exist_ok=True)
                local_path = os.path.join(selfies_dir, f"{message.from_user.id}.jpg")
                
                file_data = await bot.get_file(file_id)
                downloaded_file = await bot.download_file(file_data.file_path)
                with open(local_path, 'wb') as new_file:
                    new_file.write(downloaded_file)
                
                profile = state.get('user')
                if profile:
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    if db:
                        web_path = f"/assets/selfies/{message.from_user.id}.jpg"
                        try:
                            db.table('users').update({'url_foto': web_path}).eq('id', profile['id']).execute()
                        except Exception:
                            pass
                
                await bot.reply_to(
                    message,
                    "✅ **Selfie recebida com sucesso!**\n\n"
                    "Ela já foi enviada para a fila de processamento do assistente local da COMSOC. "
                    "Assim que for processada, você receberá um alerta automático confirmando a ativação!",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode='Markdown'
                )
            except Exception as e:
                await bot.reply_to(message, f"❌ Ocorreu um erro ao salvar sua selfie: {e}", reply_markup=get_main_menu_keyboard())
            finally:
                clear_state(chat_id)
