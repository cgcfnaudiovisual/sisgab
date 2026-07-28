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


def _format_militar_responsavel(ev, db=None):
    """Retorna os nomes dos militares responsáveis pela pauta ou 'ASD' (A Ser Designado)."""
    try:
        raw_m = ev.get('notificar_militar_ids') or ev.get('encarregado_id') or ev.get('militares_escalados_json')
        if not raw_m:
            return "ASD"
            
        m_ids = []
        if isinstance(raw_m, list):
            m_ids = raw_m
        elif isinstance(raw_m, str):
            try:
                m_ids = json.loads(raw_m)
            except Exception:
                m_ids = [s.strip() for s in raw_m.split(',') if s.strip()]
                
        if not m_ids:
            return "ASD"
            
        nomes = []
        if db:
            try:
                res_ef = db.table('efetivo').select('id, nome_guerra').execute()
                if res_ef and res_ef.data:
                    ef_map = {str(item['id']): item['nome_guerra'] for item in res_ef.data}
                    for mid in m_ids:
                        mid_str = str(mid)
                        if mid_str in ef_map:
                            nomes.append(ef_map[mid_str])
                        elif not mid_str.isdigit():
                            nomes.append(mid_str)
            except Exception:
                pass
                
        if not nomes:
            nomes = [str(x) for x in m_ids if str(x).strip()]
            
        return ", ".join(nomes) if nomes else "ASD"
    except Exception:
        return "ASD"


def _get_weekly_events_text():
    """Busca eventos dos próximos 7 dias na tabela demandas_comunicacao e retorna texto formatado com encarregados/responsáveis."""
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
        
        DIAS_SEMANA_PT = {
            0: 'SEGUNDA-FEIRA', 1: 'TERÇA-FEIRA', 2: 'QUARTA-FEIRA',
            3: 'QUINTA-FEIRA', 4: 'SEXTA-FEIRA', 5: 'SÁBADO', 6: 'DOMINGO'
        }

        events_by_date = {}
        for ev in events:
            dt_str = str(ev.get('data_evento', ''))
            if dt_str not in events_by_date:
                events_by_date[dt_str] = []
            events_by_date[dt_str].append(ev)

        msg = (
            f"📅 **AGENDA SEMANAL — COMSOC/CGCFN**\n"
            f"Período: {hoje.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for dt_str in sorted(events_by_date.keys()):
            day_events = events_by_date[dt_str]
            day_events.sort(key=lambda x: str(x.get('hora_evento', '00:00')))
            
            try:
                dt_obj = datetime.strptime(dt_str, '%Y-%m-%d')
                weekday_name = DIAS_SEMANA_PT.get(dt_obj.weekday(), '')
                date_header = f"📅 **{weekday_name} — {dt_obj.strftime('%d/%m/%Y')}**"
            except Exception:
                date_header = f"📅 **DATA: {dt_str}**"

            msg += f"{date_header}\n"
            for ev in day_events:
                st_val = str(ev.get('status', '')).strip().lower()
                st_icon = '🟢' if st_val in ('aprovado', 'aprovada', 'aprovadas') else '🟡' if st_val in ('pendente', 'pendentes') else '🛠️'
                hora = str(ev.get('hora_evento', '09:00'))[:5]
                resp_txt = _format_militar_responsavel(ev, db)
                
                msg += (
                    f"   {st_icon} **{hora}** — **{ev.get('titulo_evento', 'Sem Título')}**\n"
                    f"      📍 Local: {ev.get('local_evento', 'N/I')}\n"
                    f"      👤 Solicitante: {ev.get('solicitante_nome', 'N/I')} ({ev.get('setor', 'CGCFN')})\n"
                    f"      👨‍✈️ Equipe: {resp_txt}\n\n"
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

            elif text in ("📋 Gerenciar Demandas", "📋 Voltar para Lista de Demandas", "/demandas", "/gerenciar"):
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco de dados indisponível.")
                    return
                try:
                    res_dem = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'aprovado', 'pendente', 'em_ajuste', 'ajustes']).order('data_evento', desc=False).limit(15).execute()
                    demandas = res_dem.data if res_dem.data else []
                    if not demandas:
                        await bot.reply_to(message, "🟢 Nenhuma demanda ativa pendente de gestão no momento.", reply_markup=get_main_menu_keyboard(is_operator))
                        return
                    
                    from .keyboards import get_demandas_list_reply_keyboard
                    
                    status_emoji = {
                        'pendente': '🟡 PENDENTE',
                        'aprovada': '🟢 APROVADO',
                        'aprovado': '🟢 APROVADO',
                        'em_ajuste': '🟠 EM AJUSTE',
                        'ajustes': '🟠 EM AJUSTE'
                    }
                    
                    list_msg = f"📋 **GERENCIAMENTO DE PAUTAS ATIVAS ({len(demandas)})**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    for d in demandas:
                        d_id = d.get('id')
                        tit = d.get('titulo_evento', 'Sem Título')
                        dt = d.get('data_evento', 'N/I')
                        hr = d.get('hora_evento', '09:00')
                        raw_st = str(d.get('status', 'pendente')).lower()
                        st_display = status_emoji.get(raw_st, f'⚪ {raw_st.upper()}')
                        loc = d.get('local_evento', 'N/I')
                        
                        resp_txt = _format_militar_responsavel(d, db)
                        list_msg += f"📌 **#{d_id} — {tit}**\n   📅 {dt} às {hr} | 📍 {loc}\n   ⚡ {st_display} | 👨‍✈️ Equipe: {resp_txt}\n\n"

                    list_msg += "👇 **Selecione a pauta no teclado de resposta rápida abaixo para gerenciar:**"
                    try:
                        await bot.send_message(chat_id, list_msg, reply_markup=get_demandas_list_reply_keyboard(demandas), parse_mode='Markdown')
                    except Exception:
                        clean_list = list_msg.replace('**', '').replace('__', '')
                        await bot.send_message(chat_id, clean_list, reply_markup=get_demandas_list_reply_keyboard(demandas))
                except Exception as e_dem:
                    await bot.reply_to(message, f"❌ Erro ao listar demandas: {e_dem}")

            elif text.startswith("⚙️ #"):
                try:
                    dem_id = text.split('#')[1].split(' ')[0].split('—')[0].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                    if res_d and res_d.data:
                        d = res_d.data[0]
                        tit = d.get('titulo_evento', 'Sem Título')
                        raw_st = str(d.get('status', 'pendente')).lower()
                        from .keyboards import get_demanda_actions_reply_keyboard
                        txt = (
                            f"⚙️ **PAUTA SELECIONADA: #{dem_id} — {tit}**\n"
                            f"Status atual: **{raw_st.upper()}**\n\n"
                            f"Escolha a ação desejada no teclado de resposta rápida no rodapé:"
                        )
                        try:
                            await bot.send_message(chat_id, txt, reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=raw_st), parse_mode='Markdown')
                        except Exception:
                            await bot.send_message(chat_id, txt.replace('*', ''), reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=raw_st))
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao selecionar demanda: {e}")

            elif text.startswith("🔎 Detalhes #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                    if res_d and res_d.data:
                        d = res_d.data[0]
                        tit = d.get('titulo_evento', 'Sem Título')
                        dt = d.get('data_evento', 'N/I')
                        hr = d.get('hora_evento', 'N/I')
                        loc = d.get('local_evento', 'N/I')
                        st = str(d.get('status', 'pendente')).upper()
                        obs = d.get('observacoes', '') or 'Nenhuma'
                        solicitante = d.get('solicitante_nome', 'N/I')
                        setor = d.get('setor', 'N/I')
                        contato = d.get('contato', 'N/I')
                        autoridades = d.get('autoridades', '') or 'Nenhuma'
                        resp_txt = _format_militar_responsavel(d, db)
                        
                        detail_msg = (
                            f"🔎 **DETALHES COMPLETOS — #{dem_id}**\n"
                            f"━━━━━━━━━━━━━━━━━━\n\n"
                            f"📌 **Título:** {tit}\n"
                            f"📅 **Data:** {dt} às {hr}\n"
                            f"📍 **Local:** {loc}\n"
                            f"⚡ **Status:** {st}\n\n"
                            f"👤 **Solicitante:** {solicitante}\n"
                            f"🏢 **Setor:** {setor}\n"
                            f"📞 **Contato:** {contato}\n\n"
                            f"👑 **Autoridades:** {autoridades}\n\n"
                            f"👨‍✈️ **Equipe Escalada:** {resp_txt}\n\n"
                            f"📝 **Observações:** {obs}\n"
                            f"━━━━━━━━━━━━━━━━━━"
                        )
                        from .keyboards import get_demanda_actions_reply_keyboard
                        try:
                            await bot.send_message(chat_id, detail_msg, reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=st.lower()), parse_mode='Markdown')
                        except Exception:
                            clean_det = detail_msg.replace('**', '').replace('__', '')
                            await bot.send_message(chat_id, clean_det, reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=st.lower()))
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao buscar detalhes: {e}")

            elif text.startswith("🎯 Concluir Missão #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"🎯 **MISSÃO CONCLUÍDA!**\nPauta ID #{dem_id} foi encerrada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    from notifications_manager import notify_telegram
                    notify_telegram(f"🎯 **Pauta Concluída via Telegram**\nID #{dem_id} foi finalizada.", "system")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao concluir pauta: {e}")

            elif text.startswith("✅ Aprovar #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"✅ **PAUTA APROVADA!**\nPauta ID #{dem_id} foi homologada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    from notifications_manager import notify_telegram
                    notify_telegram(f"✅ **Pauta Aprovada via Telegram**\nID #{dem_id} foi homologada.", "system")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao aprovar pauta: {e}")

            elif text.startswith("❌ Rejeitar #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'rejeitado'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"❌ **PAUTA REJEITADA!**\nPauta ID #{dem_id} foi marcada como rejeitada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao rejeitar pauta: {e}")

            elif text.startswith("🔄 Reabrir Pauta #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"🔄 **PAUTA REABERTA!**\nPauta ID #{dem_id} voltou ao status APROVADA.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao reabrir pauta: {e}")

            elif text.startswith("✏️ Editar Horário #"):
                dem_id = text.split('#')[1].strip()
                chat_states[chat_id] = {
                    'action': 'edit_hora_demanda',
                    'demanda_id': dem_id,
                    'user': profile
                }
                await bot.send_message(chat_id, f"✏️ **EDITAR HORÁRIO (ID #{dem_id})**\n\nDigite o novo horário no formato **HH:MM** (ex: `14:30`):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif text.startswith("✏️ Editar Local #"):
                dem_id = text.split('#')[1].strip()
                chat_states[chat_id] = {
                    'action': 'edit_local_demanda',
                    'demanda_id': dem_id,
                    'user': profile
                }
                await bot.send_message(chat_id, f"✏️ **EDITAR LOCAL (ID #{dem_id})**\n\nDigite o novo local do evento (ex: `Auditório Principal`):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif text.startswith("✏️ Editar Título #"):
                dem_id = text.split('#')[1].strip()
                chat_states[chat_id] = {
                    'action': 'edit_titulo_demanda',
                    'demanda_id': dem_id,
                    'user': profile
                }
                await bot.send_message(chat_id, f"✏️ **EDITAR TÍTULO (ID #{dem_id})**\n\nDigite o novo título do evento:", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')

            elif text.startswith("👤 Equipe #"):
                dem_id = text.split('#')[1].strip()
                try:
                    from database import get_bot_db_connection as get_db_connection
                    db = get_db_connection()
                    res_ef = db.table('efetivo').select('*').execute()
                    efetivo_list = res_ef.data if res_ef.data else []
                    from .utils import sort_efetivo_by_rank
                    efetivo_list = sort_efetivo_by_rank(efetivo_list)

                    chat_states[chat_id] = {
                        'action': 'assign_equipe',
                        'demanda_id': dem_id,
                        'selected_ids': set(),
                        'efetivo_list': efetivo_list
                    }
                    from .keyboards import get_efetivo_linking_keyboard
                    await bot.send_message(
                        chat_id,
                        f"👤 **ATRIBUIR EQUIPE OPERACIONAL (ID #{dem_id})**\n\n"
                        f"Selecione um militar no teclado abaixo para vincular à pauta:",
                        reply_markup=get_efetivo_linking_keyboard(efetivo_list),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao carregar efetivo: {e}")

            elif text in ("🪑 Placas JADE", "/jade", "/placas"):
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco de dados indisponível.")
                    return
                try:
                    res_j = db.table('jade_convidados').select('*').eq('status_placa', 'pendente').execute()
                    pendentes = res_j.data if res_j.data else []
                    
                    res_prod = db.table('jade_convidados').select('*').eq('status_placa', 'em_producao').execute()
                    em_producao = res_prod.data if res_prod.data else []

                    res_imp = db.table('jade_convidados').select('*').eq('status_placa', 'impressa').execute()
                    impressas = res_imp.data if res_imp.data else []

                    msg_jade = (
                        f"🪑 **FILA DE PRODUÇÃO DE PLACAS JADE**\n"
                        f"━━━━━━━━━━━━━━━━━━\n\n"
                        f"🟡 **Pendentes:** {len(pendentes)} placa(s)\n"
                        f"🔵 **Em Produção:** {len(em_producao)} placa(s)\n"
                        f"🟢 **Já Impressas:** {len(impressas)} placa(s)\n\n"
                    )
                    
                    if pendentes:
                        msg_jade += "📌 **PRÓXIMAS PLACAS A CONFECCIONAR:**\n"
                        for idx, p in enumerate(pendentes[:10], 1):
                            nome_p = p.get('nome', 'N/I')
                            posto_p = p.get('posto_graduacao', '') or ''
                            cargo_p = p.get('cargo_funcao', '') or ''
                            msg_jade += f"{idx}. *{posto_p} {nome_p}* — _{cargo_p}_\n"
                        if len(pendentes) > 10:
                            msg_jade += f"\n_...e mais {len(pendentes) - 10} placa(s)._\n"
                    else:
                        msg_jade += "🎉 *Nenhuma placa pendente no momento!*\n"

                    msg_jade += "\n━━━━━━━━━━━━━━━━━━"
                    await bot.reply_to(message, msg_jade, parse_mode='Markdown')
                except Exception as e_j:
                    await bot.reply_to(message, f"❌ Erro ao consultar placas JADE: {e_j}")

            elif text in ("⚡ Missão Rápida", "/missaorapida", "/missao_rapida"):
                chat_states[chat_id] = {
                    'action': 'missao_rapida',
                    'step': 'input_titulo',
                    'user': profile,
                    'selected_ids': set()
                }
                from .keyboards import get_cancel_keyboard
                await bot.reply_to(
                    message,
                    "⚡ **CRIAR MISSÃO RÁPIDA**\n\n"
                    "Digite o **Título ou Objetivo** da missão expressa (ex: *Cobertura Fotográfica da Visita do Comandante*):",
                    reply_markup=get_cancel_keyboard(),
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
                dt_str = datetime.now().strftime('%Y-%m-%d')
                try:
                    from modulo_presenca import fetch_efetivo_and_presencas, gerar_texto_pronto_chegab
                    efetivo_lista, presencas_list = fetch_efetivo_and_presencas(dt_str)
                    presencas_dict = {p['nome_guerra'].upper(): p for p in presencas_list}
                    
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

        if action == 'edit_hora_demanda':
            dem_id = state.get('demanda_id')
            novahora = text.strip()
            from database import get_bot_db_connection as get_db_connection
            db = get_db_connection()
            if db and dem_id:
                try:
                    db.table('demandas_comunicacao').update({'hora_evento': novahora}).eq('id', dem_id).execute()
                    clear_state(chat_id)
                    await bot.reply_to(message, f"✅ **Horário atualizado com sucesso!**\nDemanda #{dem_id} alterada para **{novahora}**.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e_ed:
                    await bot.reply_to(message, f"❌ Erro ao atualizar horário: {e_ed}")
            return

        if action == 'edit_local_demanda':
            dem_id = state.get('demanda_id')
            novo_local = text.strip().upper()
            from database import get_bot_db_connection as get_db_connection
            db = get_db_connection()
            if db and dem_id:
                try:
                    db.table('demandas_comunicacao').update({'local_evento': novo_local}).eq('id', dem_id).execute()
                    clear_state(chat_id)
                    await bot.reply_to(message, f"✅ **Local atualizado com sucesso!**\nDemanda #{dem_id} alterada para **{novo_local}**.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e_ed:
                    await bot.reply_to(message, f"❌ Erro ao atualizar local: {e_ed}")
            return

        if action == 'edit_titulo_demanda':
            dem_id = state.get('demanda_id')
            novo_titulo = text.strip().upper()
            from database import get_bot_db_connection as get_db_connection
            db = get_db_connection()
            if db and dem_id:
                try:
                    db.table('demandas_comunicacao').update({'titulo_evento': novo_titulo}).eq('id', dem_id).execute()
                    clear_state(chat_id)
                    await bot.reply_to(message, f"✅ **Título atualizado com sucesso!**\nDemanda #{dem_id} alterada para **{novo_titulo}**.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e_ed:
                    await bot.reply_to(message, f"❌ Erro ao atualizar título: {e_ed}")
            return

        if action == 'assign_equipe':
            dem_id = state.get('demanda_id')
            efetivo_list = state.get('efetivo_list', [])
            selected_ids = state.get('selected_ids', set())

            nome_digitado = text.replace('🎖️', '').strip().upper()

            militar_encontrado = None
            for ef in efetivo_list:
                guerra = (ef.get('nome_guerra') or '').strip().upper()
                posto = (ef.get('posto_grad') or '').strip().upper()
                nome_completo = f"{posto} {guerra}".strip().upper()
                if guerra == nome_digitado or nome_completo == nome_digitado or guerra in nome_digitado or (guerra and guerra in nome_digitado):
                    militar_encontrado = ef
                    break

            from database import get_bot_db_connection as get_db_connection
            db = get_bot_db_connection()

            if militar_encontrado and db and dem_id:
                m_id = militar_encontrado.get('id')
                m_nome = f"{militar_encontrado.get('posto_grad') or ''} {militar_encontrado.get('nome_guerra', '')}".strip()
                selected_ids.add(m_id)
                
                try:
                    import json
                    db.table('demandas_comunicacao').update({
                        'notificar_militar_ids': json.dumps([int(x) for x in selected_ids if str(x).isdigit()])
                    }).eq('id', dem_id).execute()

                    t_id = militar_encontrado.get('telegram_id')
                    if t_id:
                        from notifications_manager import notify_telegram
                        notify_telegram(f"🎖️ **VOCÊ FOI ESCALADO PARA UMA MISSÃO!**\nPauta ID #{dem_id}\nEscalado por: {user_name}", "system", custom_chat_id=t_id)

                    clear_state(chat_id)
                    await bot.reply_to(
                        message,
                        f"✅ **MILITAR ESCALADO COM SUCESSO!**\n\n"
                        f"👨‍✈️ **{m_nome}** foi vinculado(a) à Pauta ID **#{dem_id}**.",
                        reply_markup=get_main_menu_keyboard(is_operator),
                        parse_mode='Markdown'
                    )
                except Exception as e_eq:
                    await bot.reply_to(message, f"❌ Erro ao atribuir equipe: {e_eq}")
            else:
                from .keyboards import get_efetivo_linking_keyboard
                await bot.reply_to(
                    message,
                    f"⚠️ Militar **'{text}'** não encontrado.\nPor favor, escolha um militar no teclado abaixo:",
                    reply_markup=get_efetivo_linking_keyboard(efetivo_list)
                )
            return

        if action == 'missao_rapida':
            step = state.get('step')
            if step == 'input_titulo':
                state['titulo'] = text.strip()
                state['step'] = 'select_militares'
                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()
                efetivo_list = []
                if db:
                    try:
                        res_ef = db.table('efetivo').select('*').execute()
                        efetivo_list = res_ef.data or []
                    except Exception:
                        pass
                from .utils import sort_efetivo_by_rank
                sorted_ef = sort_efetivo_by_rank(efetivo_list)
                state['efetivo_list'] = sorted_ef
                from .keyboards import get_efetivo_linking_keyboard
                await bot.reply_to(
                    message,
                    f"⚡ **MISSÃO RÁPIDA:** *{state['titulo']}*\n\n"
                    f"Selecione o militar escalado no teclado de resposta rápida no rodapé:",
                    reply_markup=get_efetivo_linking_keyboard(sorted_ef),
                    parse_mode='Markdown'
                )
            elif step == 'select_militares':
                titulo_m = state.get('titulo', 'Missão Rápida')
                efetivo_list = state.get('efetivo_list', [])
                nome_digitado = text.replace('🎖️', '').strip().upper()

                militar_encontrado = None
                for ef in efetivo_list:
                    guerra = (ef.get('nome_guerra') or '').strip().upper()
                    posto = (ef.get('posto_grad') or '').strip().upper()
                    nome_completo = f"{posto} {guerra}".strip().upper()
                    if guerra == nome_digitado or nome_completo == nome_digitado or guerra in nome_digitado or (guerra and guerra in nome_digitado):
                        militar_encontrado = ef
                        break

                from database import get_bot_db_connection as get_db_connection
                db = get_db_connection()

                if militar_encontrado and db:
                    m_id = militar_encontrado.get('id')
                    m_nome = f"{militar_encontrado.get('posto_grad') or ''} {militar_encontrado.get('nome_guerra', '')}".strip()
                    try:
                        import json
                        from datetime import datetime
                        now_str = datetime.now().strftime('%Y-%m-%d')
                        novo_registro = {
                            'titulo_evento': f"⚡ {titulo_m}",
                            'solicitante_nome': user_name,
                            'setor': 'COMSOC / GABINETE',
                            'data_evento': now_str,
                            'hora_evento': datetime.now().strftime('%H:%M'),
                            'local_evento': 'Gabinete / COMSOC',
                            'status': 'aprovada',
                            'categoria_demanda': 'audiovisual',
                            'notificar_militar_ids': json.dumps([int(m_id)] if str(m_id).isdigit() else [])
                        }
                        db.table('demandas_comunicacao').insert(novo_registro).execute()
                        
                        from notifications_manager import notify_telegram
                        notify_telegram(
                            f"⚡ **NOVA MISSÃO RÁPIDA REGISTRADA!**\n"
                            f"📌 {titulo_m}\n"
                            f"👨‍✈️ Criada por: {user_name}\n"
                            f"👥 Escalado: {m_nome}",
                            "system"
                        )

                        t_id = militar_encontrado.get('telegram_id')
                        if t_id:
                            notify_telegram(f"⚡ **VOCÊ FOI ESCALADO PARA UMA MISSÃO RÁPIDA!**\n📌 {titulo_m}\nEscalado por: {user_name}", "system", custom_chat_id=t_id)

                        clear_state(chat_id)
                        await bot.reply_to(
                            message,
                            f"⚡ **MISSÃO RÁPIDA CRIADA E ENVIADA!**\n\n"
                            f"📌 *{titulo_m}*\n"
                            f"📅 Data: {now_str}\n"
                            f"👨‍✈️ Militar Escalado: **{m_nome}**.",
                            reply_markup=get_main_menu_keyboard(is_operator),
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        await bot.reply_to(message, f"❌ Erro ao criar missão rápida: {e}")
                else:
                    from .keyboards import get_efetivo_linking_keyboard
                    await bot.reply_to(
                        message,
                        f"⚠️ Militar **'{text}'** não encontrado.\nPor favor, escolha um militar no teclado no rodapé:",
                        reply_markup=get_efetivo_linking_keyboard(efetivo_list)
                    )
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
                        from .utils import AUTHORIZED_PROFILES_CACHE
                        AUTHORIZED_PROFILES_CACHE[str(chat_id)] = {'nome_guerra': nome_sel, 'role': 'operador', 'telegram_id': str(chat_id)}
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
                sel_set = state['data'].setdefault('selected_services_set', set())
                from .keyboards import get_multi_service_reply_keyboard
                try:
                    await bot.reply_to(
                        message, 
                        "[Passo 9/9] 📸 **Selecione os Tipos de Serviço Requeridos**\n\n"
                        "Clique nos botões de resposta rápida abaixo no teclado para alternar cada serviço.\n"
                        "Quando terminar, clique em **➡️ CONCLUIR SELEÇÃO DOS SERVIÇOS ➡️**:", 
                        reply_markup=get_multi_service_reply_keyboard(sel_set), 
                        parse_mode='Markdown'
                    )
                except Exception:
                    await bot.reply_to(
                        message, 
                        "[Passo 9/9] Selecione os Tipos de Serviço Requeridos no teclado abaixo:", 
                        reply_markup=get_multi_service_reply_keyboard(sel_set)
                    )

            elif step == 'choose_coverage':
                history.append(('choose_coverage', dict(state['data'])))
                sel_set = state['data'].setdefault('selected_services_set', set())
                
                # Tratar botões de seleção no teclado de resposta rápida
                if "Fotográfica" in text:
                    if "foto" in sel_set: sel_set.remove("foto")
                    else: sel_set.add("foto")
                elif "Vídeo" in text:
                    if "video" in sel_set: sel_set.remove("video")
                    else: sel_set.add("video")
                elif "Gráfico" in text:
                    if "grafico" in sel_set: sel_set.remove("grafico")
                    else: sel_set.add("grafico")
                elif "Drone" in text:
                    if "drone" in sel_set: sel_set.remove("drone")
                    else: sel_set.add("drone")
                elif "Mídias Sociais" in text or "Reels" in text:
                    if "redes" in sel_set: sel_set.remove("redes")
                    else: sel_set.add("redes")
                elif "Selecionar Todos" in text or "Completo" in text:
                    if len(sel_set) == 5: sel_set.clear()
                    else: sel_set.update(['foto', 'video', 'grafico', 'drone', 'redes'])
                elif "CONCLUIR SELEÇÃO" in text or "concluir" in text.lower():
                    if not sel_set:
                        sel_set.add('foto')
                    state['data']['tipo_cobertura'] = json.dumps(list(sel_set))
                    labels_map = {
                        'foto': '📸 Cobertura Fotográfica',
                        'video': '🎥 Cobertura em Vídeo / Filmagem',
                        'grafico': '🎨 Serviço Gráfico / Design',
                        'drone': '🚁 Imagens Aéreas / Drone',
                        'redes': '📱 Mídias Sociais / Reels / Shorts'
                    }
                    state['data']['servicos_formatados'] = "\n".join([f"   • {labels_map[c]}" for c in sel_set if c in labels_map])
                    
                    state['step'] = 'observacoes'
                    from .keyboards import get_observations_keyboard
                    try:
                        await bot.reply_to(
                            message,
                            "[Passo Extra] 📝 **Observações ou Detalhes Adicionais**\n\n"
                            "Deseja registrar alguma informação adicional (ex: roteiro, transmissão, contatos extra)?\n"
                            "Ou clique em **⏭️ Pular / Nenhuma Observação**:",
                            reply_markup=get_observations_keyboard(),
                            parse_mode='Markdown'
                        )
                    except Exception:
                        await bot.reply_to(
                            message,
                            "[Passo Extra] Observações ou Detalhes Adicionais:",
                            reply_markup=get_observations_keyboard()
                        )
                    return

                # Se apenas alternou o serviço, atualiza o teclado
                from .keyboards import get_multi_service_reply_keyboard
                await bot.reply_to(
                    message,
                    f"📸 **Serviços Selecionados ({len(sel_set)}):**\n"
                    "Clique nos botões para alternar ou em **➡️ CONCLUIR SELEÇÃO ➡️**:",
                    reply_markup=get_multi_service_reply_keyboard(sel_set)
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
                try:
                    await bot.reply_to(message, resumo, reply_markup=get_confirm_demanda_keyboard(), parse_mode='Markdown')
                except Exception:
                    clean_resumo = resumo.replace('**', '').replace('__', '').replace('*', '')
                    await bot.reply_to(message, clean_resumo, reply_markup=get_confirm_demanda_keyboard())

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('opcoes_dem:', 'fechar_opcoes_dem:', 'concluir_dem:', 'rejeitar_dem:', 'equipe_dem:', 'edithora_dem:', 'sel_mil:', 'quick_mil:', 'detalhe_dem:', 'aprovar_dem:', 'editlocal_dem:', 'edittitulo_dem:', 'reabrir_dem:')))
    async def handle_demanda_management_callbacks(call):
        chat_id = call.message.chat.id if call.message else call.from_user.id
        message_id = call.message.message_id if call.message else None
        data = call.data

        async def safe_answer(text=None, show_alert=False):
            try:
                await bot.answer_callback_query(call.id, text=text, show_alert=show_alert)
            except Exception:
                pass

        # Responde imediatamente ao Telegram para parar o brilho/spinner no botão!
        await safe_answer()

        profile = await check_authorized_user(call.from_user.id)
        if not profile:
            profile = {'nome_guerra': call.from_user.first_name or 'Operador', 'role': 'operador', 'telegram_id': str(call.from_user.id)}

        db = get_db_connection()
        if not db:
            return

        user_name = profile.get('nome_guerra') or profile.get('nome', 'Operador')

        # --- EXPANDIR OPÇÕES DA DEMANDA ---
        if data.startswith('opcoes_dem:'):
            dem_id = data.split(':')[1]
            try:
                raw_st = 'aprovada'
                try:
                    res_d = db.table('demandas_comunicacao').select('status').eq('id', dem_id).execute()
                    if res_d and res_d.data:
                        raw_st = str(res_d.data[0].get('status', 'aprovada')).lower()
                except Exception:
                    pass

                from .keyboards import get_manage_demanda_inline_keyboard
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=get_manage_demanda_inline_keyboard(dem_id, status=raw_st)
                )
            except Exception as e:
                print(f"[OPCOES_DEM ERR] {e}")

        # --- OCULTAR OPÇÕES DA DEMANDA ---
        elif data.startswith('fechar_opcoes_dem:'):
            dem_id = data.split(':')[1]
            try:
                from .keyboards import get_demanda_summary_inline_keyboard
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=get_demanda_summary_inline_keyboard(demanda_id=dem_id)
                )
            except Exception as e:
                print(f"[FECHAR_OPCOES ERR] {e}")

        # --- CONCLUIR PAUTA ---
        elif data.startswith('concluir_dem:'):
            dem_id = data.split(':')[1]
            try:
                db.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                await safe_answer("✅ Pauta Concluída!")
                txt = f"🎯 **MISSÃO CONCLUÍDA!**\nPauta ID #{dem_id} foi encerrada por {user_name}."
                try:
                    await bot.edit_message_text(txt, chat_id=chat_id, message_id=call.message.message_id, parse_mode='Markdown')
                except Exception:
                    await bot.edit_message_text(txt.replace('*', ''), chat_id=chat_id, message_id=call.message.message_id)
                
                from notifications_manager import notify_telegram
                notify_telegram(f"🎯 **Pauta Concluída via Telegram**\nID #{dem_id} foi finalizada por {user_name}.", "system")
            except Exception as e:
                await safe_answer(f"Erro: {e}")

        # --- REJEITAR PAUTA ---
        elif data.startswith('rejeitar_dem:'):
            dem_id = data.split(':')[1]
            try:
                db.table('demandas_comunicacao').update({'status': 'rejeitado'}).eq('id', dem_id).execute()
                await safe_answer("❌ Pauta Rejeitada.")
                txt = f"❌ **PAUTA INDEFERIDA**\nPauta ID #{dem_id} foi marcada como rejeitada por {user_name}."
                try:
                    await bot.edit_message_text(txt, chat_id=chat_id, message_id=call.message.message_id, parse_mode='Markdown')
                except Exception:
                    await bot.edit_message_text(txt.replace('*', ''), chat_id=chat_id, message_id=call.message.message_id)
            except Exception as e:
                await safe_answer(f"Erro: {e}")

        # --- ATRIBUIR EQUIPE (INÍCIO) ---
        elif data.startswith('equipe_dem:'):
            dem_id = data.split(':')[1]
            try:
                res_ef = db.table('efetivo').select('*').execute()
                efetivo_list = res_ef.data if res_ef.data else []
                from .utils import sort_efetivo_by_rank
                efetivo_list = sort_efetivo_by_rank(efetivo_list)

                chat_states[chat_id] = {
                    'action': 'assign_equipe',
                    'demanda_id': dem_id,
                    'selected_ids': set(),
                    'efetivo_list': efetivo_list
                }
                from .keyboards import get_multi_militar_inline_keyboard
                msg_txt = (
                    f"👤 **ATRIBUIR EQUIPE OPERACIONAL**\nDemanda ID #{dem_id}\n\n"
                    f"Selecione os militares que participarão da missão (ordenados por antiguidade):"
                )
                try:
                    await bot.edit_message_text(
                        msg_txt,
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_multi_militar_inline_keyboard(efetivo_list, set(), prefix="sel_mil"),
                        parse_mode='Markdown'
                    )
                except Exception:
                    await bot.edit_message_text(
                        msg_txt.replace('*', ''),
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_multi_militar_inline_keyboard(efetivo_list, set(), prefix="sel_mil")
                    )
                await safe_answer()
            except Exception as e:
                await safe_answer(f"Erro ao carregar efetivo: {e}")

        # --- TOGGLE MILITAR EM EQUIPE ---
        elif data.startswith('sel_mil:'):
            action_code = data.split(':')[1]
            st = chat_states.get(chat_id, {})
            if st.get('action') != 'assign_equipe':
                await safe_answer("Sessão de seleção expirada.")
                return

            if action_code == 'done':
                selected_ids = list(st.get('selected_ids', set()))
                dem_id = st.get('demanda_id')
                try:
                    import json
                    db.table('demandas_comunicacao').update({
                        'notificar_militar_ids': json.dumps([int(x) for x in selected_ids if str(x).isdigit()])
                    }).eq('id', dem_id).execute()

                    # Notifica os militares selecionados
                    for m_id in selected_ids:
                        try:
                            res_m = db.table('efetivo').select('telegram_id, nome_guerra').eq('id', m_id).execute()
                            if res_m.data and res_m.data[0].get('telegram_id'):
                                t_id = res_m.data[0]['telegram_id']
                                from notifications_manager import send_notification_to_user
                                await send_notification_to_user(t_id, f"🎖️ **VOCÊ FOI ESCALADO PARA UMA MISSÃO!**\nPauta ID #{dem_id}\nEscalado por: {user_name}")
                        except Exception:
                            pass

                    clear_state(chat_id)
                    txt = f"✅ **EQUIPE ATRIBUÍDA COM SUCESSO!**\nDemanda ID #{dem_id}\nTotal de {len(selected_ids)} militar(es) escalado(s)."
                    try:
                        await bot.edit_message_text(
                            txt,
                            chat_id=chat_id,
                            message_id=call.message.message_id,
                            parse_mode='Markdown'
                        )
                    except Exception:
                        await bot.edit_message_text(txt.replace('*', ''), chat_id=chat_id, message_id=call.message.message_id)
                    await safe_answer("Equipe salva!")
                except Exception as e:
                    await safe_answer(f"Erro ao salvar equipe: {e}")
            else:
                sel = st.get('selected_ids', set())
                if action_code in sel:
                    sel.remove(action_code)
                else:
                    sel.add(action_code)
                st['selected_ids'] = sel
                
                from .keyboards import get_multi_militar_inline_keyboard
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_multi_militar_inline_keyboard(st.get('efetivo_list', []), sel, prefix="sel_mil")
                    )
                except Exception:
                    pass
                await safe_answer()

        # --- TOGGLE MILITAR EM MISSÃO RÁPIDA ---
        elif data.startswith('quick_mil:'):
            action_code = data.split(':')[1]
            st = chat_states.get(chat_id, {})
            if st.get('action') != 'missao_rapida' or st.get('step') != 'select_militares':
                await safe_answer("Sessão expirada.")
                return

            if action_code == 'done':
                selected_ids = list(st.get('selected_ids', set()))
                titulo_m = st.get('titulo', 'Missão Rápida')
                try:
                    import json
                    from datetime import datetime
                    now_str = datetime.now().strftime('%Y-%m-%d')
                    novo_registro = {
                        'titulo_evento': f"⚡ {titulo_m}",
                        'solicitante_nome': user_name,
                        'setor': 'COMSOC / GABINETE',
                        'data_evento': now_str,
                        'hora_evento': datetime.now().strftime('%H:%M'),
                        'local_evento': 'Gabinete / COMSOC',
                        'status': 'aprovada',
                        'categoria_demanda': 'audiovisual',
                        'notificar_militar_ids': json.dumps([int(x) for x in selected_ids if str(x).isdigit()])
                    }
                    res_ins = db.table('demandas_comunicacao').insert(novo_registro).execute()
                    
                    from notifications_manager import notify_telegram
                    notify_telegram(
                        f"⚡ **NOVA MISSÃO RÁPIDA REGISTRADA!**\n"
                        f"📌 {titulo_m}\n"
                        f"👨‍✈️ Criada por: {user_name}\n"
                        f"👥 Equipe Escalada: {len(selected_ids)} militar(es)",
                        "system"
                    )

                    clear_state(chat_id)
                    txt = f"⚡ **MISSÃO RÁPIDA CRIADA E ENVIADA!**\n\n📌 *{titulo_m}*\n📅 Data: {now_str}\n👥 Escalados: {len(selected_ids)} militar(es)."
                    try:
                        await bot.edit_message_text(
                            txt,
                            chat_id=chat_id,
                            message_id=call.message.message_id,
                            parse_mode='Markdown'
                        )
                    except Exception:
                        await bot.edit_message_text(txt.replace('*', '').replace('_', ''), chat_id=chat_id, message_id=call.message.message_id)
                    await safe_answer("Missão enviada!")
                except Exception as e:
                    await safe_answer(f"Erro ao criar missão: {e}")
            else:
                sel = st.get('selected_ids', set())
                if action_code in sel:
                    sel.remove(action_code)
                else:
                    sel.add(action_code)
                st['selected_ids'] = sel
                
                from .keyboards import get_multi_militar_inline_keyboard
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_multi_militar_inline_keyboard(st.get('efetivo_list', []), sel, prefix="quick_mil")
                    )
                except Exception:
                    pass
                await safe_answer()

        # --- EDITAR HORÁRIO DA PAUTA ---
        elif data.startswith('edithora_dem:'):
            dem_id = data.split(':')[1]
            chat_states[chat_id] = {
                'action': 'edit_hora_demanda',
                'demanda_id': dem_id,
                'user': profile
            }
            txt = f"✏️ **EDITAR HORÁRIO (ID #{dem_id})**\n\nDigite o novo horário no formato **HH:MM** (ex: `14:30`):"
            try:
                await bot.send_message(chat_id, txt, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chat_id, txt.replace('*', '').replace('`', ''))
            await safe_answer()

        # --- VER DETALHES COMPLETOS DA DEMANDA ---
        elif data.startswith('detalhe_dem:'):
            dem_id = data.split(':')[1]
            try:
                res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                if not res_d.data:
                    await safe_answer("Demanda não encontrada.")
                    return
                d = res_d.data[0]
                tit = d.get('titulo_evento', 'Sem Título')
                dt = d.get('data_evento', 'N/I')
                hr = d.get('hora_evento', 'N/I')
                loc = d.get('local_evento', 'N/I')
                st = str(d.get('status', 'pendente')).upper()
                obs = d.get('observacoes', '') or 'Nenhuma'
                solicitante = d.get('solicitante_nome', 'N/I')
                setor = d.get('setor', 'N/I')
                contato = d.get('contato', 'N/I')
                autoridades = d.get('autoridades', '') or 'Nenhuma'
                
                resp_txt = _format_militar_responsavel(d, db)
                
                tipo_cob = d.get('tipo_cobertura', '')
                servicos_str = "N/I"
                if tipo_cob:
                    try:
                        import json as _json
                        cob_list = _json.loads(tipo_cob) if isinstance(tipo_cob, str) else tipo_cob
                        labels_map = {
                            'foto': '📸 Cobertura Fotográfica',
                            'video': '🎥 Vídeo / Filmagem',
                            'grafico': '🎨 Serviço Gráfico',
                            'drone': '🚁 Imagens Aéreas / Drone',
                            'redes': '📱 Mídias Sociais'
                        }
                        servicos_str = "\n".join([f"   • {labels_map.get(s, s)}" for s in cob_list])
                    except Exception:
                        servicos_str = str(tipo_cob)
                
                status_emojis = {
                    'PENDENTE': '🟡', 'APROVADA': '🟢', 'APROVADO': '🟢',
                    'EM_AJUSTE': '🟠', 'AJUSTES': '🟠',
                    'CONCLUIDA': '✅', 'REJEITADO': '❌'
                }
                st_emoji = status_emojis.get(st, '⚪')
                
                detail_msg = (
                    f"🔎 **DETALHES COMPLETOS — #{dem_id}**\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"📌 **Título:** {tit}\n"
                    f"📅 **Data:** {dt} às {hr}\n"
                    f"📍 **Local:** {loc}\n"
                    f"{st_emoji} **Status:** {st}\n\n"
                    f"👤 **Solicitante:** {solicitante}\n"
                    f"🏢 **Setor:** {setor}\n"
                    f"📞 **Contato:** {contato}\n\n"
                    f"👑 **Autoridades:** {autoridades}\n\n"
                    f"🔧 **Serviços Solicitados:**\n{servicos_str}\n\n"
                    f"👨‍✈️ **Equipe Escalada:** {resp_txt}\n\n"
                    f"📝 **Observações:** {obs}\n"
                    f"━━━━━━━━━━━━━━━━━━"
                )
                try:
                    await bot.send_message(chat_id, detail_msg, parse_mode='Markdown')
                except Exception:
                    clean_detail = detail_msg.replace('**', '').replace('__', '')
                    await bot.send_message(chat_id, clean_detail)
                await safe_answer()
            except Exception as e:
                await safe_answer(f"Erro: {e}")

        # --- APROVAR PAUTA PENDENTE ---
        elif data.startswith('aprovar_dem:'):
            dem_id = data.split(':')[1]
            try:
                db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                await safe_answer("✅ Pauta Aprovada!")
                txt = f"✅ **PAUTA APROVADA!**\nPauta ID #{dem_id} foi homologada por {user_name}."
                try:
                    await bot.edit_message_text(
                        txt,
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    await bot.edit_message_text(txt.replace('*', ''), chat_id=chat_id, message_id=call.message.message_id)
                from notifications_manager import notify_telegram
                notify_telegram(f"✅ **Pauta Aprovada via Telegram**\nID #{dem_id} foi homologada por {user_name}.", "system")
            except Exception as e:
                await safe_answer(f"Erro: {e}")

        # --- EDITAR LOCAL DA PAUTA ---
        elif data.startswith('editlocal_dem:'):
            dem_id = data.split(':')[1]
            chat_states[chat_id] = {
                'action': 'edit_local_demanda',
                'demanda_id': dem_id,
                'user': profile
            }
            txt = f"✏️ **EDITAR LOCAL (ID #{dem_id})**\n\nDigite o novo local do evento (ex: `Auditório Principal`):"
            try:
                await bot.send_message(chat_id, txt, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chat_id, txt.replace('*', '').replace('`', ''))
            await safe_answer()

        # --- EDITAR TÍTULO DA PAUTA ---
        elif data.startswith('edittitulo_dem:'):
            dem_id = data.split(':')[1]
            chat_states[chat_id] = {
                'action': 'edit_titulo_demanda',
                'demanda_id': dem_id,
                'user': profile
            }
            txt = f"✏️ **EDITAR TÍTULO (ID #{dem_id})**\n\nDigite o novo título do evento:"
            try:
                await bot.send_message(chat_id, txt, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chat_id, txt.replace('*', ''))
            await safe_answer()

        # --- REABRIR PAUTA CONCLUÍDA ---
        elif data.startswith('reabrir_dem:'):
            dem_id = data.split(':')[1]
            try:
                db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                await safe_answer("🔄 Pauta Reaberta!")
                txt = f"🔄 **PAUTA REABERTA!**\nPauta ID #{dem_id} foi reaberta por {user_name} e voltou ao status APROVADA."
                try:
                    await bot.edit_message_text(
                        txt,
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    await bot.edit_message_text(txt.replace('*', ''), chat_id=chat_id, message_id=call.message.message_id)
            except Exception as e:
                await safe_answer(f"Erro: {e}")

    # 🛡️ CATCH-ALL CALLBACK HANDLER: Garante que NENHUM botão inline no Telegram fique travado ou sem resposta!
    @bot.callback_query_handler(func=lambda call: True)
    async def handle_catchall_callbacks(call):
        try:
            await bot.answer_callback_query(call.id)
        except Exception:
            pass


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
                        try:
                            db.table('efetivo').update({'selfie_path': local_path}).eq('id', profile['id']).execute()
                        except Exception as sp_err:
                            print(f"[SELFIE WARN] {sp_err}")

                await bot.reply_to(
                    message,
                    "✅ **Selfie recebida com sucesso!**\n\n"
                    "Sua foto foi gravada e habilitada para reconhecimento facial em coberturas.",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode='Markdown'
                )
            except Exception as e:
                await bot.reply_to(message, f"❌ Ocorreu um erro ao salvar sua selfie: {e}", reply_markup=get_main_menu_keyboard())
            finally:
                clear_state(chat_id)


    @bot.message_handler(content_types=['voice', 'audio'])
    async def handle_voice_messages(message):
        import os, tempfile, json
        from datetime import datetime
        chat_id = message.chat.id
        profile = await check_authorized_user(message.from_user.id)
        if not profile:
            await bot.reply_to(message, "⚠️ Acesso restrito.")
            return

        user_name = profile.get('nome_guerra') or profile.get('nome', 'Operador')
        msg_waiting = await bot.reply_to(message, "🎙️ **Ouvindo e interpretando áudio com IA Gemini...**", parse_mode='Markdown')

        try:
            file_obj = message.voice if message.voice else message.audio
            file_info = await bot.get_file(file_obj.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
                tmp.write(downloaded_file)
                tmp_path = tmp.name

            import ai_helper
            res_json_str = ai_helper.transcribe_and_digest_audio(tmp_path, mime_type="audio/ogg")
            try:
                os.remove(tmp_path)
            except Exception:
                pass

            data = json.loads(res_json_str)
            if "error" in data and not data.get("titulo_evento"):
                await bot.edit_message_text(f"❌ Erro ao processar áudio: {data.get('error')}", chat_id=chat_id, message_id=msg_waiting.message_id)
                return

            transcricao = data.get('transcricao', 'Áudio recebido.')
            titulo = data.get('titulo_evento') or 'Pauta via Mensagem de Voz'
            data_ev = data.get('data_evento') or datetime.now().strftime('%Y-%m-%d')
            hora_ev = data.get('hora_evento') or '09:00'
            local_ev = data.get('local_evento') or 'Gabinete'
            militares_citados = data.get('militares_citados', [])

            from database import get_bot_db_connection as get_db_connection
            db = get_db_connection()
            d_id = 'OK'
            if db:
                novo_reg = {
                    'titulo_evento': f"🎙️ {titulo}",
                    'solicitante_nome': user_name,
                    'setor': 'VOZ TELEGRAM',
                    'data_evento': data_ev,
                    'hora_evento': hora_ev,
                    'local_evento': local_ev,
                    'status': 'aprovada',
                    'tipo_cobertura': '["foto", "video"]',
                    'descricao': f"Transcrevendo de áudio: {transcricao}"
                }
                res_ins = db.table('demandas_comunicacao').insert(novo_reg).execute()
                if res_ins.data:
                    d_id = res_ins.data[0].get('id', 'OK')

                from notifications_manager import notify_telegram
                notify_telegram(
                    f"🎙️ **NOVA DEMANDA CRIADA VIA ÁUDIO DE VOZ!**\n"
                    f"📌 {titulo}\n"
                    f"📅 {data_ev} às {hora_ev} | 📍 {local_ev}\n"
                    f"👤 Enviado por: {user_name}\n"
                    f"🗣️ Transcrição: _{transcricao}_",
                    "system"
                )

            mil_txt = ", ".join(militares_citados) if militares_citados else "Nenhum citado"
            await bot.edit_message_text(
                f"✅ **ÁUDIO PROCESSADO E DEMANDA REGISTRADA!**\n\n"
                f"📌 **Título:** {titulo} (ID #{d_id})\n"
                f"📅 **Data/Hora:** {data_ev} às {hora_ev}\n"
                f"📍 **Local:** {local_ev}\n"
                f"🗣️ **Transcrição IA:** _{transcricao}_\n"
                f"👥 **Militares Citados:** {mil_txt}",
                chat_id=chat_id,
                message_id=msg_waiting.message_id,
                parse_mode='Markdown'
            )
        except Exception as err:
            await bot.edit_message_text(f"❌ Falha ao interpretar áudio: {err}", chat_id=chat_id, message_id=msg_waiting.message_id)
