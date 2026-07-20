import json
from telebot import types
from datetime import datetime
from .client import chat_states
from .utils import check_authorized_user, clear_state, USER_PERMISSIONS_CACHE
from .keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_unauthorized_keyboard

def register_common_handlers(bot):
    
    @bot.message_handler(func=lambda msg: True)
    async def handle_all_messages(message):
        chat_id = message.chat.id
        text = message.text.strip()
        
        # 1. Roteamento de Teclado Principal (caso sem estado anterior)
        if chat_id not in chat_states:
            profile = await check_authorized_user(message.from_user.id)
            if not profile:
                if text == "📝 Solicitar Acesso":
                    # Inicia wizard de solicitação
                    chat_states[chat_id] = {
                        'action': 'settings',
                        'step': 'request_access_name',
                        'user': None,
                        'data': {}
                    }
                    await bot.reply_to(message, "📝 **Solicitação de Acesso**\n\nPor favor, informe seu **Posto ou Graduação** (ex: Sgt, Ten, Cap):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                else:
                    await bot.reply_to(message, "⚓ Assistente SisGAB: Envie /menu para ver os comandos permitidos.", reply_markup=get_unauthorized_keyboard())
                return

            allowed = USER_PERMISSIONS_CACHE.get(message.from_user.id, set())
            
            if text == "⚙️ Configurações":
                from .handlers_settings import register_settings_command
                await register_settings_command(message)
            elif text == "📸 Cadastro Facial":
                chat_states[chat_id] = {
                    'action': 'cadastro_facial',
                    'step': 'send_selfie',
                    'user': profile
                }
                await bot.reply_to(
                    message,
                    "📸 **CADASTRO FACIAL - SISGAB**\n\n"
                    "Por favor, envie uma **selfie nítida** de frente (sem boné ou óculos de sol).\n\n"
                    "Esta foto será utilizada como referência para identificá-lo automaticamente nas coberturas fotográficas!",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='Markdown'
                )
            elif text == "🔍 Buscar Minhas Fotos":
                from database import get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco de dados offline. Tente novamente mais tarde.")
                    return
                try:
                    res_m = db.table('photo_matches').select('photo_id, similarity').eq('militar_id', profile['id']).eq('status', 'aprovado').execute()
                    if res_m.data:
                        photo_ids = [m['photo_id'] for m in res_m.data]
                        res_p = db.table('processed_photos').select('*').in_('id', photo_ids).execute()
                        if res_p.data:
                            sim_dict = {m['photo_id']: m['similarity'] for m in res_m.data}
                            response_text = "🔍 **FOTOS ENCONTRADAS EM QUE VOCÊ APARECE:**\n\n"
                            for p in res_p.data:
                                p_id = p['id']
                                sim_val = sim_dict.get(p_id, 0.0) * 100
                                response_text += (
                                    f"⚓ *Evento:* {p['event_name']}\n"
                                    f"📂 *Arquivo:* `{p['filename']}`\n"
                                    f"📈 *Similaridade:* {sim_val:.1f}%\n"
                                    f"🔗 [Abrir no Google Drive]({p['drive_link']})\n\n"
                                )
                            if len(response_text) > 4000:
                                response_text = response_text[:3900] + "\n\n*(resultado truncado devido ao tamanho...)*"
                            await bot.reply_to(message, response_text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')
                        else:
                            await bot.reply_to(message, "🔍 Nenhuma foto sua foi encontrada no Drive.", reply_markup=get_main_menu_keyboard())
                    else:
                        await bot.reply_to(message, "🔍 Nenhuma foto sua foi identificada no banco de dados até agora.", reply_markup=get_main_menu_keyboard())
                except Exception as ex:
                    await bot.reply_to(message, f"❌ Erro ao buscar fotos: {ex}", reply_markup=get_main_menu_keyboard())
            elif text == "ℹ️ Ajuda":
                help_text = (
                    "⚓ **Ajuda - SisGAB Bot** ⚓\n\n"
                    "Este bot auxilia nas comunicações e alertas do Gabinete.\n\n"
                    "**Comandos disponíveis:**\n"
                    "/menu - Menu Principal\n"
                    "/settings - Painel de Configurações\n"
                    "/cancelar - Cancela qualquer ação ativa"
                )
                is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design')
                await bot.reply_to(message, help_text, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
            elif text == "📋 Pautas COMSOC":
                from database import get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco offline.")
                    return
                try:
                    res = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'pendente']).execute()
                    if res.data:
                        msg_p = "📋 **PAUTAS E EVENTOS COMSOC:**\n\n"
                        for d in res.data:
                            status_ico = "🟢" if d['status'] == 'aprovada' else "🟡"
                            msg_p += (
                                f"{status_ico} **{d['titulo_evento']}**\n"
                                f"📅 *Data:* {d['data_evento']} às {d['hora_evento']}\n"
                                f"📍 *Local:* {d['local_evento']}\n"
                                f"👤 *Solicitante:* {d['solicitante_nome']} ({d['setor']})\n\n"
                            )
                        await bot.reply_to(message, msg_p, reply_markup=get_main_menu_keyboard(True), parse_mode='Markdown')
                    else:
                        await bot.reply_to(message, "📋 Nenhuma pauta cadastrada ou pendente.", reply_markup=get_main_menu_keyboard(True))
                except Exception as ex:
                    await bot.reply_to(message, f"❌ Erro ao listar pautas: {ex}")
            
            elif text == "🔌 Cautelas Ativas":
                from database import get_db_connection
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
                    'data': {}
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
                is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
                await bot.reply_to(message, "Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
            else:
                is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
                await bot.reply_to(message, "⚓ Assistente SisGAB Ativo. Envie /menu para opções.", reply_markup=get_main_menu_keyboard(is_operator))
            return

        # 2. Processamento do Estado / Wizard Ativo
        state = chat_states[chat_id]
        action = state.get('action')
        step = state.get('step')
        profile = state.get('user')
        is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
        
        if text.lower() in ['cancelar', '❌ cancelar']:
            clear_state(chat_id)
            await bot.reply_to(message, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
            return
            
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

async def finalizar_solicitacao_acesso(bot, message, chat_id, state):
    reg_nome = state['data'].get('reg_nome', 'N/I')
    reg_guerra = state['data'].get('reg_guerra', 'N/I')
    reg_email = state['data'].get('reg_email', 'N/I')
    reg_om = state['data'].get('reg_om', 'CGCFN')
    reg_funcao = state['data'].get('reg_funcao', 'Gabinete')
    
    try:
        from database import get_db_connection
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
                    'tipo_usuario': 'comsoc' if 'CGCFN' in reg_om.upper() else 'externo',
                    'status': 'pendente'
                }).execute()
            except Exception as reg_err:
                print(f"[Bot Reg Request Insert Error] {reg_err}")

            # NOTIFICAR OS ADMINISTRADORES E SUPERVISORES VIA TELEGRAM
            try:
                from notifications_manager import notify_telegram
                res_admin = conn.table('efetivo').select('telegram_id').in_('role', ['admin', 'supervisor', 'oficial_gab']).execute()
                if res_admin and res_admin.data:
                    alert_txt = (
                        f"🔔 **NOVA SOLICITAÇÃO DE ACESSO AO SISGAB** ⚓\n\n"
                        f"👤 **Militar:** {reg_guerra} ({reg_nome})\n"
                        f"📧 **E-mail:** {reg_email}\n"
                        f"🏢 **OM/Unidade:** {reg_om}\n"
                        f"🎯 **Seção/Função:** {reg_funcao}\n"
                        f"📱 **Telegram ID:** `{chat_id}`\n\n"
                        f"👉 *Acesse o painel 'Usuários e Permissões' no SisGAB para aprovar.*"
                    )
                    for adm in res_admin.data:
                        if adm_tg := adm.get('telegram_id'):
                            notify_telegram(alert_txt, "system", custom_chat_id=adm_tg)
            except Exception as notif_err:
                print(f"[BOT ADMIN NOTIFY REG ERR] {notif_err}")

        await bot.reply_to(message, "✅ Solicitação de acesso registrada e enviada aos administradores!\nVocê receberá uma notificação assim que seu acesso for aprovado.", reply_markup=get_unauthorized_keyboard())
    except Exception as ex:
        await bot.reply_to(message, f"❌ Erro ao registrar solicitação: {ex}", reply_markup=get_unauthorized_keyboard())
    finally:
        clear_state(chat_id)

        elif action == 'digerir_pauta_ia':
            if step == 'send_raw_text':
                await bot.reply_to(message, "⏳ Analisando questionário com Gemini...")
                try:
                    import ai_helper
                    import json
                    
                    response_json = ai_helper.digest_demand_questionnaire(text)
                    dados = json.loads(response_json)
                    
                    # Salva no banco
                    from database import get_db_connection
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
                            "new_user" # Reutiliza canal prioritário de avisos urgentes
                        )
                    else:
                        await bot.reply_to(message, "⚠️ Erro ao salvar: Banco indisponível.")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao digerir questionário: {e}\nPor favor, tente enviar novamente ou criar manualmente.", reply_markup=get_main_menu_keyboard(is_operator))
                finally:
                    clear_state(chat_id)

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
                    "➕ **SOLICITAÇÃO DE PAUTA E COBERTURA - COMSOC/CGCFN**\n\n"
                    "[Passo 1/12] 👤 Qual o **Posto/Graduação e Nome Completo** do Solicitante?", 
                    reply_markup=get_cancel_keyboard(), 
                    parse_mode='Markdown'
                )

        # 2. Processamento do Estado / Wizard Ativo
        state = chat_states[chat_id]
        action = state.get('action')
        step = state.get('step')
        profile = state.get('user')
        is_operator = profile and str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')
        
        if text.lower() in ['cancelar', '❌ cancelar']:
            clear_state(chat_id)
            await bot.reply_to(message, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator))
            return
            
        from .keyboards import (
            get_om_keyboard, get_coverage_keyboard, get_video_format_keyboard,
            get_yes_no_keyboard, get_confirm_demanda_keyboard
        )

        if action == 'criar_demanda':
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
                if "Outra" in text:
                    state['step'] = 'solicitante_om_custom'
                    await bot.reply_to(message, "🏢 Por favor, digite o nome da **Outra OM**:", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                else:
                    state['data']['setor'] = "CGCFN"
                    state['step'] = 'contato'
                    await bot.reply_to(message, "[Passo 3/12] 📞 Qual o **Ramal ou Telefone** de contato?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'solicitante_om_custom':
                history.append(('solicitante_om_custom', dict(state['data'])))
                state['data']['setor'] = text.upper()
                state['step'] = 'contato'
                await bot.reply_to(message, "[Passo 3/12] 📞 Qual o **Ramal ou Telefone** de contato?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'contato':
                history.append(('contato', dict(state['data'])))
                state['data']['contato'] = text
                state['step'] = 'titulo'
                await bot.reply_to(message, "[Passo 4/12] ✍️ Qual o **Título do Evento ou Pauta** da cobertura?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'titulo':
                history.append(('titulo', dict(state['data'])))
                state['data']['titulo'] = text
                state['step'] = 'data_evento'
                await bot.reply_to(message, "[Passo 5/12] 📅 Qual a **Data de Início e Término**? (ex: 25/07/2026 a 27/07/2026):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'data_evento':
                history.append(('data_evento', dict(state['data'])))
                date_txt = text.strip()
                if '/' in date_txt and 'a' not in date_txt.lower():
                    try:
                        date_txt = datetime.strptime(date_txt, '%d/%m/%Y').strftime('%Y-%m-%d')
                    except:
                        pass
                state['data']['data_evento'] = date_txt
                state['step'] = 'hora_evento'
                await bot.reply_to(message, "[Passo 6/12] ⏰ Qual o **Horário de Início e Término previsto**? (ex: 09:00 às 17:00):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'hora_evento':
                history.append(('hora_evento', dict(state['data'])))
                state['data']['hora_evento'] = text
                state['step'] = 'local'
                await bot.reply_to(message, "[Passo 7/12] 📍 Qual o **Local exato do Evento**?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'local':
                history.append(('local', dict(state['data'])))
                state['data']['local'] = text
                state['step'] = 'uniforme'
                await bot.reply_to(message, "[Passo 8/12] 👔 Qual o **Uniforme** do evento? (ex: 3.3, 4.4, Passeio):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'uniforme':
                history.append(('uniforme', dict(state['data'])))
                state['data']['uniforme'] = text
                state['step'] = 'autoridades'
                await bot.reply_to(message, "[Passo 9/12] 👑 Quais **Autoridades** estarão presentes? (se nenhuma, digite Nenhuma):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'autoridades':
                history.append(('autoridades', dict(state['data'])))
                state['data']['autoridades'] = text
                state['step'] = 'choose_coverage'
                await bot.reply_to(
                    message, 
                    "[Passo 10/12] 📸 **Escopo / Tipo de Cobertura Requerida**\n\nSelecione uma das opções nos botões:", 
                    reply_markup=get_coverage_keyboard(), 
                    parse_mode='Markdown'
                )

            elif step == 'choose_coverage':
                history.append(('choose_coverage', dict(state['data'])))
                coverage_txt = text.upper()
                coberturas = []
                if "FOTO" in coverage_txt:
                    coberturas.append("foto")
                if "VIDEO" in coverage_txt or "VÍDEO" in coverage_txt:
                    coberturas.append("video")
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
                    from database import get_db_connection
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
                    from database import get_db_connection
                    db = get_db_connection()
                    if db:
                        web_path = f"/assets/selfies/{message.from_user.id}.jpg"
                        db.table('Users').update({'url_foto': web_path}).eq('id', profile['id']).execute()
                
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
