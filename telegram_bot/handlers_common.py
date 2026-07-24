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

    @bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_service:'))
    async def handle_service_toggle_callback(call):
        chat_id = call.message.chat.id
        if chat_id not in chat_states or chat_states[chat_id].get('action') != 'criar_demanda':
            await bot.answer_callback_query(call.id, "Sessão expirada. Inicie com ➕ Criar Demanda.")
            return

        action_code = call.data.split(':')[1]
        state = chat_states[chat_id]
        selected_set = state['data'].setdefault('selected_services_set', set())

        if action_code == 'all':
            if len(selected_set) == 5:
                selected_set.clear()
            else:
                selected_set.update(['foto', 'video', 'grafico', 'drone', 'redes'])
            await bot.answer_callback_query(call.id, "Todos os serviços selecionados!")
        elif action_code == 'done':
            if not selected_set:
                selected_set.add('foto')
            
            state['data']['tipo_cobertura'] = json.dumps(list(selected_set))
            
            labels_map = {
                'foto': '📸 Cobertura Fotográfica',
                'video': '🎥 Cobertura em Vídeo / Filmagem',
                'grafico': '🎨 Serviço Gráfico / Design',
                'drone': '🚁 Imagens Aéreas / Drone',
                'redes': '📱 Mídias Sociais / Reels / Shorts'
            }
            state['data']['servicos_formatados'] = "\n".join([f"   • {labels_map[c]}" for c in selected_set])
            
            state['step'] = 'observacoes'
            await bot.answer_callback_query(call.id, "Serviços salvos!")
            
            from .keyboards import get_observations_keyboard
            await bot.send_message(
                chat_id,
                "[Passo Extra] 📝 **Observações ou Detalhes Adicionais**\n\n"
                "Deseja registrar alguma informação adicional (ex: roteiro, transmissão, contatos extra)?\n"
                "Ou clique em **⏭️ Pular / Nenhuma Observação**:",
                reply_markup=get_observations_keyboard(),
                parse_mode='Markdown'
            )
            return
        else:
            if action_code in selected_set:
                selected_set.remove(action_code)
                await bot.answer_callback_query(call.id, "Removido")
            else:
                selected_set.add(action_code)
                await bot.answer_callback_query(call.id, "Adicionado")

        from .keyboards import get_multi_service_inline_keyboard
        new_markup = get_multi_service_inline_keyboard(selected_set)
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=new_markup)
        except Exception:
            pass

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
                if "vincular" in text.lower() or text == "🔗 Vincular Meu Nome":
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    ef_lista = []
                    if db:
                        try:
                            res = db.table('efetivo').select('id, nome_guerra').execute()
                            ef_lista = res.data or []
                        except Exception as e:
                            print(f"[VINCULAR LOAD ERR] {e}")
                    
                    if ef_lista:
                        chat_states[chat_id] = {
                            'action': 'vincular_efetivo',
                            'step': 'select_militar',
                            'user': None,
                            'data': {}
                        }
                        from .keyboards import get_efetivo_linking_keyboard
                        await bot.reply_to(
                            message,
                            "⚓ **VINCULAR CONTA DE MILITAR DO GABINETE**\n\n"
                            "Selecione o seu **Nome de Guerra** nos botões abaixo para vincular este Telegram à sua conta:",
                            reply_markup=get_efetivo_linking_keyboard(ef_lista),
                            parse_mode='Markdown'
                        )
                    else:
                        await bot.reply_to(message, "⚠️ Nenhum militar cadastrado para vinculação.", reply_markup=get_unauthorized_keyboard())
                    return

                elif text.lower() in ["📝 solicitar acesso", "/start", "/solicitar", "/acesso", "solicitar", "solicitar acesso", "acesso"]:
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
                        f"Clique em **🔗 Vincular Meu Nome** se você já é do efetivo ou **📝 Solicitar Acesso** para pedir novo cadastro.", 
                        reply_markup=get_unauthorized_keyboard(),
                        parse_mode='Markdown'
                    )
                return

            # --- Usuário autorizado: roteamento dos botões do menu ---
            allowed = USER_PERMISSIONS_CACHE.get(message.from_user.id, set())
            is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design')

            from .keyboards import get_settings_keyboard
            if text == "⚙️ Configurações":
                chat_states[chat_id] = {
                    'action': 'settings',
                    'step': 'main_menu',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(message, "⚙️ **CONFIGURAÇÕES**\nEscolha uma das opções abaixo:", reply_markup=get_settings_keyboard(True, is_operator))

            elif text == "➕ Criar Demanda":
                chat_states[chat_id] = {
                    'action': 'criar_demanda',
                    'step': 'solicitante_om',
                    'user': profile,
                    'data': {
                        'selected_services_set': set()
                    }
                }
                from .keyboards import get_om_keyboard
                await bot.reply_to(
                    message, 
                    "📋 **NOVA SOLICITAÇÃO DE PAUTA — CGCFN**\n\n[Passo 1/9] ⚓ A solicitação é do **CGCFN** ou de **Outra OM**?", 
                    reply_markup=get_om_keyboard(), 
                    parse_mode='Markdown'
                )

            elif text == "📋 Pautas COMSOC" or text == "📅 Agenda Semanal":
                txt = _get_weekly_events_text()
                await bot.reply_to(message, txt, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')

            elif text == "📋 Dar Presença" or text == "🟢 Dar Presença" or text == "/presenca":
                chat_states[chat_id] = {
                    'action': 'presenca_diaria',
                    'step': 'choose_sigla',
                    'user': profile,
                    'data': {}
                }
                from .keyboards import get_presenca_keyboard
                await bot.reply_to(
                    message,
                    "🌅 **CHAMADA MATUTINA — CGCFN/SISGAB**\n\n"
                    "Por favor, selecione a sigla da sua rotina para hoje:",
                    reply_markup=get_presenca_keyboard(),
                    parse_mode='Markdown'
                )

            elif text == "/pronto" or text == "📋 Pronto CheGab":
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if db:
                    dt_str = datetime.now().strftime('%Y-%m-%d')
                    try:
                        res_ef = db.table('efetivo').select('*').order('nome_guerra').execute()
                        efetivo_lista = res_ef.data or []
                        res_pr = db.table('presenca_diaria').select('*').eq('data', dt_str).execute()
                        presencas_list = res_pr.data or []
                        
                        presencas_dict = {p['nome_guerra'].upper(): p for p in presencas_list}
                        
                        from modulo_presenca import gerar_texto_pronto_chegab
                        relatorio_txt = gerar_texto_pronto_chegab(dt_str, presencas_dict, efetivo_lista)
                        await bot.reply_to(message, relatorio_txt, parse_mode='Markdown')
                    except Exception as pr_err:
                        await bot.reply_to(message, f"❌ Erro ao gerar pronto: {pr_err}")
                return

            elif text == "🤖 Digerir Pauta (IA)":
                chat_states[chat_id] = {
                    'action': 'digerir_pauta_ia',
                    'step': 'send_raw_text',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(
                    message, 
                    "🤖 **DIGESTÃO INTELIGENTE DE PAUTA (IA GEMINI)**\n\n"
                    "Por favor, cole abaixo o **texto das respostas do questionário/checklist** recebido do solicitante.\n\n"
                    "O Gemini extrairá automaticamente título, data, local e escopo.", 
                    reply_markup=get_cancel_keyboard(), 
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
                    "🔹 **Comandos Principais:**\n"
                    "• ➕ **Criar Demanda:** Cadastrar nova pauta com seleção por botões.\n"
                    "• 🟢 **Dar Presença:** Acusar a chamada matutina.\n"
                    "• 📋 **Pronto CheGab:** Gerar o relatório da Sargenteação.\n"
                    "• 📅 **Agenda Semanal:** Consultar pautas dos próximos 7 dias.\n"
                    "• 🤖 **Digerir Pauta (IA):** Criar pauta colando questionário."
                )
                await bot.reply_to(message, help_msg, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
            else:
                await bot.reply_to(
                    message, 
                    f"⚓ **Menu Principal — SisGAB**\n\nOlá, *{profile.get('nome_guerra', 'Militar')}*! Selecione uma opção nos botões abaixo:", 
                    reply_markup=get_main_menu_keyboard(is_operator), 
                    parse_mode='Markdown'
                )
            return

        # =====================================================================
        # SEÇÃO 2: Processamento de Estados Ativos do Usuário (Wizards)
        # =====================================================================
        state = chat_states[chat_id]
        action = state.get('action')
        step = state.get('step')
        profile = state.get('user')
        is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design') if profile else False

        if text in ["❌ Cancelar", "cancelar"]:
            clear_state(chat_id)
            await bot.reply_to(message, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator) if profile else get_unauthorized_keyboard())
            return

        if action == 'presenca_diaria':
            step = state.get('step')
            if step == 'choose_sigla':
                sigla_txt = text.upper()
                sigla_code = 'P'
                if '(MA)' in sigla_txt or 'MA' in sigla_txt: sigla_code = 'MA'
                elif '(MT)' in sigla_txt or 'MT' in sigla_txt: sigla_code = 'MT'
                elif '(FE)' in sigla_txt or 'FE' in sigla_txt: sigla_code = 'FE'
                elif '(L)' in sigla_txt or 'L' in sigla_txt: sigla_code = 'L'
                elif '(H)' in sigla_txt or 'H' in sigla_txt: sigla_code = 'H'
                elif '(DM)' in sigla_txt or 'DM' in sigla_txt: sigla_code = 'DM'
                elif '(S)' in sigla_txt or 'S' in sigla_txt: sigla_code = 'S'
                
                state['data']['status'] = sigla_code
                
                if sigla_code in ('MA', 'MT', 'H'):
                    state['step'] = 'input_obs'
                    await bot.reply_to(
                        message,
                        f"✍️ Por favor, digite a localização/motivo para **({sigla_code})**:",
                        reply_markup=get_cancel_keyboard(),
                        parse_mode='Markdown'
                    )
                else:
                    from .utils import _salvar_presenca_bot
                    await _salvar_presenca_bot(bot, message, chat_id, state, sigla_code, "")
                    
            elif step == 'input_obs':
                sigla_code = state['data'].get('status', 'P')
                from .utils import _salvar_presenca_bot
                await _salvar_presenca_bot(bot, message, chat_id, state, sigla_code, text)
            return

        if action == 'vincular_efetivo':
            if step == 'select_militar':
                nome_sel = text.replace('🎖️', '').strip().upper()
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if db:
                    try:
                        db.table('efetivo').update({'telegram_id': str(chat_id)}).eq('nome_guerra', nome_sel).execute()
                        await bot.reply_to(
                            message,
                            f"✅ **VINCULAÇÃO CONCLUÍDA COM SUCESSO!**\n\n"
                            f"Seu Telegram `{chat_id}` foi vinculado ao militar *{nome_sel}*.\n\n"
                            f"Você já pode responder às chamadas diárias e utilizar o menu!",
                            reply_markup=get_main_menu_keyboard(True),
                            parse_mode='Markdown'
                        )
                    except Exception as e_vinc:
                        await bot.reply_to(message, f"❌ Erro ao vincular: {e_vinc}", reply_markup=get_unauthorized_keyboard())
                clear_state(chat_id)
                return

        # ----- WIZARD: Digerir Pauta com IA (Gemini) -----
        if action == 'digerir_pauta_ia':
            if step == 'send_raw_text':
                await bot.reply_to(message, "⏳ Analisando questionário com Gemini...")
                try:
                    import ai_helper
                    
                    response_json = ai_helper.digest_demand_questionnaire(text)
                    dados = json.loads(response_json)
                    
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

        # ----- WIZARD: Criar Demanda (Interativo com Botões em todas as Etapas) -----
        if action == 'criar_demanda':
            from .keyboards import (
                get_om_keyboard, get_date_keyboard, get_time_keyboard,
                get_uniform_keyboard, get_authorities_keyboard, get_observations_keyboard,
                get_multi_service_inline_keyboard, get_confirm_demanda_keyboard
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

            if step == 'solicitante_om':
                history.append(('solicitante_om', dict(state['data'])))
                if "CGCFN" in text.upper():
                    state['data']['solicitante_nome'] = "CGCFN / GABINETE"
                    state['data']['setor'] = "CGCFN"
                    state['data']['contato'] = "21982043314 / Ramal CGCFN"
                    state['step'] = 'titulo'
                    await bot.reply_to(message, "[Passo 2/9] ✍️ Qual o **Título do Evento ou Pauta**?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                else:
                    state['step'] = 'solicitante_om_custom'
                    await bot.reply_to(message, "🏢 Por favor, digite o nome da **Outra OM**:", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'solicitante_om_custom':
                history.append(('solicitante_om_custom', dict(state['data'])))
                state['data']['setor'] = text.upper()
                state['step'] = 'contato'
                await bot.reply_to(message, "📞 Qual o **Ramal ou Telefone** de contato?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'contato':
                history.append(('contato', dict(state['data'])))
                state['data']['contato'] = text
                state['step'] = 'titulo'
                await bot.reply_to(message, "[Passo 2/9] ✍️ Qual o **Título do Evento ou Pauta**?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'titulo':
                history.append(('titulo', dict(state['data'])))
                state['data']['titulo'] = text
                state['step'] = 'data_evento'
                await bot.reply_to(message, "[Passo 3/9] 📅 Qual a **Data de Início** do Evento?", reply_markup=get_date_keyboard(False), parse_mode='Markdown')

            elif step == 'data_evento':
                history.append(('data_evento', dict(state['data'])))
                date_txt = text.strip()
                clean_dt = date_txt.split('(')[-1].replace(')', '').strip() if '(' in date_txt else date_txt
                parsed_dt = False
                for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y', '%d/%m'):
                    try:
                        if fmt == '%d/%m':
                            clean_dt = f"{clean_dt}/{datetime.now().year}"
                            fmt = '%d/%m/%Y'
                        clean_dt = datetime.strptime(clean_dt, fmt).strftime('%Y-%m-%d')
                        parsed_dt = True
                        break
                    except ValueError:
                        continue
                if not parsed_dt:
                    clean_dt = datetime.now().strftime('%Y-%m-%d')
                    
                state['data']['data_evento'] = clean_dt
                state['data']['data_fim'] = clean_dt
                state['step'] = 'data_fim'
                await bot.reply_to(message, "[Passo 4/9] 📅 Qual a **Data de Término**? (Opcional):", reply_markup=get_date_keyboard(True), parse_mode='Markdown')

            elif step == 'data_fim':
                history.append(('data_fim', dict(state['data'])))
                if "Mesmo Dia" not in text:
                    date_txt = text.strip()
                    clean_dt = date_txt.split('(')[-1].replace(')', '').strip() if '(' in date_txt else date_txt
                    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y', '%d/%m'):
                        try:
                            if fmt == '%d/%m':
                                clean_dt = f"{clean_dt}/{datetime.now().year}"
                                fmt = '%d/%m/%Y'
                            clean_dt = datetime.strptime(clean_dt, fmt).strftime('%Y-%m-%d')
                            state['data']['data_fim'] = clean_dt
                            break
                        except ValueError:
                            continue
                
                state['step'] = 'hora_evento'
                await bot.reply_to(message, "[Passo 5/9] ⏰ Qual o **Horário de Início**?", reply_markup=get_time_keyboard(), parse_mode='Markdown')

            elif step == 'hora_evento':
                history.append(('hora_evento', dict(state['data'])))
                state['data']['hora_evento'] = text.replace('⏰', '').strip()
                state['step'] = 'local'
                await bot.reply_to(message, "[Passo 6/9] 📍 Qual o **Local exato do Evento**?", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif step == 'local':
                history.append(('local', dict(state['data'])))
                state['data']['local'] = text
                state['step'] = 'uniforme'
                await bot.reply_to(message, "[Passo 7/9] 👔 Qual o **Uniforme** do evento?", reply_markup=get_uniform_keyboard(), parse_mode='Markdown')

            elif step == 'uniforme':
                history.append(('uniforme', dict(state['data'])))
                state['data']['uniforme'] = text
                state['step'] = 'autoridades'
                await bot.reply_to(message, "[Passo 8/9] 👑 Quais **Autoridades** estarão presentes?", reply_markup=get_authorities_keyboard(), parse_mode='Markdown')

            elif step == 'autoridades':
                history.append(('autoridades', dict(state['data'])))
                state['data']['autoridades'] = text
                state['step'] = 'choose_coverage'
                state['data']['selected_services_set'] = set()
                await bot.reply_to(
                    message, 
                    "[Passo 9/9] 📸 **Selecione os Tipos de Serviço Requeridos**\n\n"
                    "Clique nos botões inline abaixo para marcar um ou mais serviços.\n"
                    "Quando terminar, clique em **➡️ CONCLUIR SELEÇÃO DOS SERVIÇOS ➡️**:", 
                    reply_markup=get_multi_service_inline_keyboard(state['data']['selected_services_set']), 
                    parse_mode='Markdown'
                )

            elif step == 'observacoes':
                history.append(('observacoes', dict(state['data'])))
                if "Pular" in text or "Nenhuma" in text:
                    state['data']['observacoes'] = "Nenhuma"
                else:
                    state['data']['observacoes'] = text
                    
                state['step'] = 'review_confirm'
                d = state['data']
                dt_fim_txt = f" até {d.get('data_fim')}" if d.get('data_fim') and d.get('data_fim') != d.get('data_evento') else " (mesmo dia)"
                
                resumo = (
                    "📋 **REVISÃO DA SOLICITAÇÃO DE PAUTA / CGCFN**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🏛️ **OM / Setor:** {d.get('setor')}\n"
                    f"👤 **Solicitante:** {d.get('solicitante_nome')}\n"
                    f"📞 **Contato:** {d.get('contato')}\n"
                    f"📌 **Evento:** {d.get('titulo')}\n"
                    f"📅 **Data:** {d.get('data_evento')}{dt_fim_txt}\n"
                    f"⏰ **Horário:** {d.get('hora_evento')}\n"
                    f"📍 **Local:** {d.get('local')}\n"
                    f"👔 **Uniforme:** {d.get('uniforme')}\n"
                    f"👑 **Autoridades:** {d.get('autoridades')}\n\n"
                    f"📸 **Tipos de Serviços Solicitados:**\n"
                    f"{d.get('servicos_formatados', '   • 📸 Cobertura Fotográfica')}\n\n"
                    f"📝 **Observações:** {d.get('observacoes')}\n\n"
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
                                'solicitante_nome': d.get('solicitante_nome', 'CGCFN').upper(),
                                'setor': d.get('setor', 'CGCFN').upper(),
                                'contato': d.get('contato', 'N/I'),
                                'titulo_evento': d.get('titulo', 'Evento').upper(),
                                'data_evento': d.get('data_evento'),
                                'data_fim': d.get('data_fim', d.get('data_evento')),
                                'hora_evento': d.get('hora_evento', '09:00'),
                                'local_evento': d.get('local', 'Gabinete').upper(),
                                'tipo_cobertura': d.get('tipo_cobertura', '["foto"]'),
                                'autoridades': d.get('autoridades', ''),
                                'observacoes': d.get('observacoes', ''),
                                'score_esforco': 1.5,
                                'status': 'pendente'
                            }
                            db.table('demandas_comunicacao').insert(registro).execute()
                            await bot.reply_to(message, "✅ **Demanda cadastrada com sucesso!**\nAguardando homologação do Supervisor responsável.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')

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
                    state['step'] = 'solicitante_om'
                    state['data'] = {'selected_services_set': set()}
                    state['history_steps'] = []
                    from .keyboards import get_om_keyboard
                    await bot.reply_to(message, "✏️ **Formulação Reiniciada**\n\n[Passo 1/9] ⚓ A solicitação é do **CGCFN** ou de **Outra OM**?", reply_markup=get_om_keyboard(), parse_mode='Markdown')
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
