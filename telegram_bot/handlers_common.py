import json
from datetime import datetime, timedelta
from telebot import types
from .client import chat_states
from .utils import check_authorized_user, clear_state, USER_PERMISSIONS_CACHE, escape_markdown

from .keyboards import *
from database import get_bot_db_connection as get_db_connection





async def finalizar_solicitacao_acesso(bot, message, chat_id, state):
    """Finaliza o wizard de solicitação de acesso: grava no banco e notifica admins."""
    reg_nome = state['data'].get('reg_nome', 'N/I')
    reg_guerra = state['data'].get('reg_guerra', 'N/I')
    reg_email = state['data'].get('reg_email', 'N/I')
    reg_om = state['data'].get('reg_om', 'CGCFN')
    reg_funcao = state['data'].get('reg_funcao', 'Gabinete')
    
    try:
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

        if not db:
            from database import get_bot_db_connection
            db = get_bot_db_connection()
            
        nomes = []
        if db:
            try:
                res_ef = db.table('efetivo').select('*').execute()
                if res_ef and res_ef.data:
                    ef_map = {}
                    for item in res_ef.data:
                        nome_g = str(item.get('nome_guerra') or item.get('nome') or '').replace('None', '').strip()
                        pg = str(item.get('posto_grad') or item.get('posto') or '').replace('None', '').strip()
                        full_name = f"{pg} {nome_g}".strip() if pg else nome_g
                        if item.get('id'):
                            ef_map[str(item['id'])] = full_name
                        if nome_g:
                            ef_map[nome_g.upper()] = full_name

                    for mid in m_ids:
                        mid_str = str(mid).strip()
                        if mid_str in ef_map:
                            nomes.append(ef_map[mid_str])
                        elif mid_str.upper() in ef_map:
                            nomes.append(ef_map[mid_str.upper()])
                        elif not mid_str.isdigit():
                            nomes.append(mid_str)
            except Exception as ef_err:
                print(f"[FORMAT MILITAR RESP DB ERR] {ef_err}")
                
        if not nomes:
            nomes = [str(x) for x in m_ids if str(x).strip() and not str(x).isdigit()]
            
        return ", ".join(list(set(nomes))) if nomes else "ASD"
    except Exception:
        return "ASD"


def _get_weekly_events_text():
    """Busca eventos dos próximos 7 dias na tabela demandas_comunicacao e retorna texto formatado com encarregados/responsáveis."""
    try:
        db = get_db_connection()
        if not db:
            return "⚠️ Banco de dados indisponível no momento."
        
        hoje = datetime.now().date()
        fim_semana = hoje + timedelta(days=7)
        
        try:
            res = db.table('demandas_comunicacao').select('*').gte(
                'data_evento', hoje.isoformat()
            ).lte(
                'data_evento', fim_semana.isoformat()
            ).order('data_evento', desc=False).execute()
            events = res.data if (res and res.data) else []
        except Exception as e_db:
            print(f"[BOT AGENDA DB ERR] {e_db}")
            events = []
        
        if not events:
            return (
                f"📅 **AGENDA SEMANAL — COMSOC/CGCFN**\n"
                f"Período: {hoje.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}\n\n"
                f"🟢 Nenhum evento ou pauta agendada para os próximos 7 dias.\n\n"
                f"Use a opção **➕ Criar Demanda** no menu para cadastrar."
            )
        
        DIAS_SEMANA_PT = {
            0: 'SEGUNDA-FEIRA', 1: 'TERÇA-FEIRA', 2: 'QUARTA-FEIRA',
            3: 'QUINTA-FEIRA', 4: 'SEXTA-FEIRA', 5: 'SÁBADO', 6: 'DOMINGO'
        }

        events_by_date = {}
        for ev in events:
            dt_str = str(ev.get('data_evento', '')).strip()
            if not dt_str:
                continue
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
                dt_obj = datetime.strptime(dt_str[:10], '%Y-%m-%d')
                weekday_name = DIAS_SEMANA_PT.get(dt_obj.weekday(), '')
                date_header = f"📅 **{weekday_name} — {dt_obj.strftime('%d/%m/%Y')}**"
            except Exception:
                date_header = f"📅 **DATA: {dt_str}**"

            msg += f"{date_header}\n"
            for ev in day_events:
                st_val = str(ev.get('status', '')).strip().lower()
                st_icon = '🟢' if st_val in ('aprovado', 'aprovada', 'aprovadas') else '🟡' if st_val in ('pendente', 'pendentes') else '🛠️'
                hora = str(ev.get('hora_evento', '09:00'))[:5]
                
                resp_txt = str(_format_militar_responsavel(ev, db)).replace('*', '').replace('_', '')
                titulo = str(ev.get('titulo_evento', 'Sem Título')).replace('*', '').replace('_', '')
                local = str(ev.get('local_evento', 'N/I')).replace('*', '').replace('_', '')
                solicitante = str(ev.get('solicitante_nome', 'N/I')).replace('*', '').replace('_', '')
                setor = str(ev.get('setor', 'CGCFN')).replace('*', '').replace('_', '')
                
                msg += (
                    f"   {st_icon} **{hora}** — **{titulo}**\n"
                    f"      📍 Local: {local}\n"
                    f"      👤 Solicitante: {solicitante} ({setor})\n"
                    f"      👨‍✈️ Equipe: {resp_txt}\n\n"
                )
        
        msg += f"📊 Total: **{len(events)} evento(s)** na semana.\n⚓ _SisGAB — Gestão de Gabinete_"
        return msg
    except Exception as e:
        print(f"[CRITICAL BOT AGENDA ERR] {e}")
        return f"❌ Erro ao buscar agenda semanal: {e}"


async def mostrar_historico_usuarios_telegram(bot, message):
    chat_id = message.chat.id
    db = get_db_connection()
    if not db:
        await bot.send_message(chat_id, "⚠️ Banco de dados indisponível.")
        return

    from .utils import sort_efetivo_by_rank, normalize_text
    
    seen_nips = set()
    seen_emails = set()
    seen_names = set()
    users_list = []
    
    for u in raw_users:
        nip = str(u.get('nip') or '').strip()
        email = normalize_text(str(u.get('email') or u.get('username') or ''))
        nome = normalize_text(str(u.get('nome_guerra') or u.get('nome') or ''))
        
        if nip and nip in seen_nips:
            continue
        if email and '@' in email and email in seen_emails:
            continue
        if nome and nome in seen_names:
            continue
            
        if nip: seen_nips.add(nip)
        if email and '@' in email: seen_emails.add(email)
        if nome: seen_names.add(nome)
        users_list.append(u)

    users_list = sort_efetivo_by_rank(users_list)

    if not users_list:
        await bot.send_message(chat_id, "📭 Nenhum usuário cadastrado no histórico.")
        return

    from .utils import check_authorized_user
    profile = await check_authorized_user(message.from_user.id)
    chat_states[chat_id] = {
        'action': 'gerenciar_usuarios_pendentes',
        'requests': users_list,
        'user': profile
    }

    reply_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=1)
    
    msg_hist = f"📜 **HISTÓRICO COMPLETO DE USUÁRIOS ({len(users_list)})**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for idx, u in enumerate(users_list[:15], 1):
        u_guerra = str(u.get('nome') or u.get('nome_guerra') or 'Militar').upper()
        u_email = str(u.get('email') or u.get('username') or 'N/I')
        u_role = str(u.get('role') or 'militar').upper()
        msg_hist += f"{idx}. **{u_guerra}** ({u_email}) — Perfil: `{u_role}`\n"
        
        btn_label = f"👤 #{idx} — {u_guerra} ({u_email.split('@')[0]})".strip()
        reply_markup.add(types.KeyboardButton(btn_label))

    is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design') if profile else False
    reply_markup.add(types.KeyboardButton("⬅️ Voltar"))
    
    msg_hist += "\n💡 *Para alterar o perfil de qualquer usuário acima, clique no botão correspondente no teclado abaixo:*"

    await bot.send_message(chat_id, msg_hist, reply_markup=reply_markup, parse_mode='Markdown')


async def listar_cadastros_pendentes(bot, message):
    chat_id = message.chat.id
    from .utils import check_authorized_user
    profile = await check_authorized_user(message.from_user.id)
    db = get_db_connection()
    if not db:
        await bot.send_message(chat_id, "⚠️ Banco de dados indisponível no momento.")
        return

    raw_reqs = []
    for tbl in ['RegistrationRequests', 'registration_requests']:
        try:
            res = db.table(tbl).select('*').in_('status', ['pending', 'pendente']).execute()
            if res and res.data:
                raw_reqs.extend(res.data)
        except Exception as err:
            print(f"[BOT REG PENDENTES QUERY ERR] {err}")

    seen = set()
    pending_requests = []
    for r in raw_reqs:
        r_key = r.get('id') or r.get('email')
        if r_key and r_key not in seen:
            seen.add(r_key)
            pending_requests.append(r)

    if not pending_requests:
        try:
            res_u = db.table('users').select('*').in_('role', ['aluno', 'pendente']).limit(10).execute()
            if res_u and res_u.data:
                pending_requests.extend(res_u.data)
        except Exception:
            pass

    if not pending_requests:
        reply_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        reply_markup.row(types.KeyboardButton("📜 Ver Histórico Completo de Usuários"), types.KeyboardButton("⬅️ Voltar"))
        await bot.send_message(
            chat_id,
            "✅ **NENHUMA SOLICITAÇÃO PENDENTE DE APROVAÇÃO!**\n\n"
            "Todas as solicitações de cadastro de novos usuários já foram processadas.\n"
            "Você pode alterar o perfil dos usuários cadastrados clicando no botão abaixo:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    chat_states[chat_id] = {
        'action': 'gerenciar_usuarios_pendentes',
        'requests': pending_requests,
        'user': profile
    }

    await bot.send_message(
        chat_id,
        f"📋 **ENCONTRADAS {len(pending_requests)} SOLICITAÇÃO(ÕES) PENDENTE(S)**\n\n"
        f"Escolha a forma de aprovação:\n"
        f"1️⃣ Clique em **Aprovar & Escolher Perfil** no chat, OU\n"
        f"2️⃣ Selecione o militar nos **Botões do Teclado (rodapé)**.",
        parse_mode='Markdown'
    )

    reply_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=1)

    for idx, req in enumerate(pending_requests, 1):
        req_id = req.get('id', '')
        req_nome = req.get('nome_completo') or req.get('nome_guerra') or 'Militar'
        req_guerra = req.get('nome_guerra', req_nome)
        req_email = req.get('email', 'N/I')
        req_date = req.get('created_at', '')[:10] if req.get('created_at') else 'N/I'

        card_txt = (
            f"👤 **SOLICITAÇÃO #{idx}**\n\n"
            f"📌 **Nome:** `{req_nome}`\n"
            f"🎖️ **Guerra:** `{req_guerra}`\n"
            f"📧 **E-mail:** `{req_email}`\n"
            f"📅 **Data:** `{req_date}`\n"
            f"⚙️ **Status:** `PENDENTE`"
        )

        inline_markup = types.InlineKeyboardMarkup(row_width=2)
        inline_markup.add(
            types.InlineKeyboardButton("✅ Aprovar & Escolher Perfil", callback_data=f"approve_req:{req_id}"),
            types.InlineKeyboardButton("❌ Rejeitar", callback_data=f"reject_req:{req_id}")
        )

        await bot.send_message(chat_id, card_txt, reply_markup=inline_markup, parse_mode='Markdown')

        btn_label = f"👤 #{idx} — {str(req_guerra).upper()} ({req_email.split('@')[0]})".strip()
        reply_markup.add(types.KeyboardButton(btn_label))

    reply_markup.add(types.KeyboardButton("📜 Ver Histórico Completo de Usuários"), types.KeyboardButton("⬅️ Voltar"))

    await bot.send_message(
        chat_id,
        "👇 **Menu de Teclado Embutido:** Selecione o militar abaixo para alterar perfil:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


_upload_state = {}  # {chat_id: {'photos': [file_info], 'last_time': float, 'waiting_event': bool}}

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

        new_markup = get_multi_service_inline_keyboard(selected_set)
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=new_markup)
        except Exception:
            pass

    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_ciente:'))
    async def handle_confirm_ciente_callback(call):
        try:
            dem_id = call.data.split(':')[1]
            user_id = call.from_user.id
            user_name = call.from_user.first_name or "Militar"
            await bot.answer_callback_query(call.id, "👍 Ciente registrado com sucesso!")
            
            try:
                await bot.edit_message_text(
                    f"✅ **CIÊNCIA CONFIRMADA!**\n"
                    f"Militar *{user_name}* confirmou presença/ciência na missão ID #{dem_id}.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='Markdown'
                )
            except Exception:
                pass
                
            from notifications_manager import notify_telegram
            notify_telegram(f"👍 **Confirmação de Ciência**\nO militar {user_name} confirmou ciente na pauta ID #{dem_id}.", "system")
        except Exception as e:
            print(f"[CONFIRM CIENTE ERR] {e}")

    @bot.callback_query_handler(func=lambda call: any(call.data.startswith(p) for p in ['appr_dem:', 'conc_dem:', 'rej_dem:', 'reopen_dem:', 'det_dem:']))
    async def handle_inline_demanda_actions(call):
        try:
            parts = call.data.split(':')
            action = parts[0]
            dem_id = parts[1]
            chat_id = call.message.chat.id
            
            db = get_db_connection()
            if not db:
                await bot.answer_callback_query(call.id, "Banco indisponível.")
                return

            if action == 'appr_dem':
                db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                await bot.answer_callback_query(call.id, "Pauta aprovada!")
                await bot.send_message(chat_id, f"✅ **PAUTA #{dem_id} APROVADA COM SUCESSO!**", parse_mode='Markdown')
            elif action == 'conc_dem':
                db.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                await bot.answer_callback_query(call.id, "Missão concluída!")
                
                from database import get_demanda_drive_url
                res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                d_obj = res_d.data[0] if (res_d and res_d.data) else {}
                d_url = get_demanda_drive_url(d_obj)
                
                markup_c = types.InlineKeyboardMarkup()
                if d_url:
                    markup_c.add(types.InlineKeyboardButton("📁 Abrir Pasta no Google Drive", url=d_url))
                
                await bot.send_message(
                    chat_id,
                    f"🎯 **MISSÃO #{dem_id} CONCLUÍDA COM SUCESSO!**\n\n"
                    f"💡 *Dica:* Para anexar ou alterar o link do acervo no Google Drive, edite a pauta no painel Web ou envie a URL aqui.",
                    parse_mode='Markdown',
                    reply_markup=markup_c if d_url else None
                )
            elif action == 'rej_dem':
                db.table('demandas_comunicacao').update({'status': 'rejeitado'}).eq('id', dem_id).execute()
                await bot.answer_callback_query(call.id, "Pauta rejeitada.")
                await bot.send_message(chat_id, f"❌ **PAUTA #{dem_id} MARCADA COMO REJEITADA.**", parse_mode='Markdown')
            elif action == 'reopen_dem':
                db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                await bot.answer_callback_query(call.id, "Pauta reaberta.")
                await bot.send_message(chat_id, f"🔄 **PAUTA #{dem_id} REABERTA COMO APROVADA.**", parse_mode='Markdown')
            elif action == 'det_dem':
                await bot.answer_callback_query(call.id, "Carregando detalhes...")
                res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                if res_d and res_d.data:
                    d = res_d.data[0]
                    from database import get_demanda_drive_url
                    d_url = get_demanda_drive_url(d)
                    
                    det_txt = (
                        f"🔎 **DETALHES DA PAUTA #{dem_id}**\n\n"
                        f"📌 **Título:** {d.get('titulo_evento')}\n"
                        f"📅 **Data/Hora:** {d.get('data_evento')} às {d.get('hora_evento')}\n"
                        f"📍 **Local:** {d.get('local_evento')}\n"
                        f"⚡ **Status:** {str(d.get('status')).upper()}\n"
                        f"👤 **Solicitante:** {d.get('solicitante_nome')} ({d.get('setor', 'CGCFN')})"
                    )
                    if d_url:
                        det_txt += f"\n\n📁 **Link do Drive / Acervo:** {d_url}"
                        
                    markup_det = types.InlineKeyboardMarkup()
                    if d_url:
                        markup_det.add(types.InlineKeyboardButton("📁 Abrir Pasta no Google Drive", url=d_url))
                    
                    await bot.send_message(chat_id, det_txt, parse_mode='Markdown', reply_markup=markup_det if d_url else None)
        except Exception as e:
            print(f"[INLINE DEMANDA ACTION ERR] {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_req:', 'reject_req:', 'approve_role:')))
    async def handle_user_approval_callbacks(call):
        try:
            db = get_db_connection()

            if call.data.startswith('approve_req:'):
                req_id = call.data.split(':', 1)[1]
                await bot.answer_callback_query(call.id, "Selecione o perfil...")
                
                # Cria o teclado inline para seleção do papel do novo operador
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("👑 Administrador", callback_data=f"approve_role:admin:{req_id}"),
                    types.InlineKeyboardButton("⚖️ Supervisor", callback_data=f"approve_role:supervisor:{req_id}"),
                    types.InlineKeyboardButton("⚖️ Oficial Gabinete", callback_data=f"approve_role:oficial_gab:{req_id}"),
                    types.InlineKeyboardButton("⚓ Oficial OM", callback_data=f"approve_role:oficial:{req_id}"),
                    types.InlineKeyboardButton("📜 Praça Gabinete", callback_data=f"approve_role:praca_gab:{req_id}"),
                    types.InlineKeyboardButton("📸 COMSOC", callback_data=f"approve_role:comsoc:{req_id}"),
                    types.InlineKeyboardButton("🎨 COMSOC Design", callback_data=f"approve_role:comsoc_design:{req_id}"),
                    types.InlineKeyboardButton("⚓ Militar Geral", callback_data=f"approve_role:militar:{req_id}")
                )
                
                await bot.send_message(
                    call.message.chat.id,
                    f"⚙️ **APROVAÇÃO DE ACESSO (ID: `{req_id}`)**\n\n"
                    f"Escolha a permissão/papel a ser atribuído a este usuário:",
                    reply_markup=markup,
                    parse_mode='Markdown'
                )

            elif call.data.startswith('approve_role:'):
                parts = call.data.split(':', 2)
                role_selected = parts[1]
                req_id = parts[2]

                try:
                    await bot.answer_callback_query(call.id, f"Aprovando perfil: {role_selected}...")
                except Exception:
                    pass

                # Busca os dados da solicitação no banco de dados
                req_data = None
                if db:
                    for tbl in ['RegistrationRequests', 'registration_requests']:
                        try:
                            res = db.table(tbl).select('*').eq('id', req_id).execute()
                            if res and res.data:
                                req_data = res.data[0]
                                break
                        except Exception:
                            pass
                    
                    if not req_data and req_id.isdigit():
                        for tbl in ['RegistrationRequests', 'registration_requests']:
                            try:
                                res = db.table(tbl).select('*').eq('id', int(req_id)).execute()
                                if res and res.data:
                                    req_data = res.data[0]
                                    break
                            except Exception:
                                pass
                
                u_email = req_data.get('email', '') if req_data else f"user_{req_id[:6]}@marinha.mil.br"
                u_guerra = req_data.get('nome_guerra') or req_data.get('nome_completo') or "Militar"
                u_tg_id = req_data.get('telegram_id') if req_data else None

                # 1. Atualiza o status em ambas as tabelas de solicitação
                if db:
                    for tbl in ['RegistrationRequests', 'registration_requests']:
                        try:
                            db.table(tbl).update({'status': 'approved'}).eq('id', req_id).execute()
                        except Exception:
                            pass
                        if req_id.isdigit():
                            try:
                                db.table(tbl).update({'status': 'approved'}).eq('id', int(req_id)).execute()
                            except Exception:
                                pass
                        if u_email:
                            try:
                                db.table(tbl).update({'status': 'approved'}).eq('email', u_email).execute()
                            except Exception:
                                pass

                    # 2. Atualiza a role na tabela USERS
                    try:
                        db.table('users').update({'role': role_selected}).eq('id', req_id).execute()
                    except Exception as u_err1:
                        print(f"[USERS UPDATE ID ERR] {u_err1}")
                        
                    if u_email:
                        try:
                            db.table('users').update({'role': role_selected}).eq('email', u_email).execute()
                        except Exception as u_err2:
                            print(f"[USERS UPDATE EMAIL ERR] {u_err2}")

                    # 3. Atualiza a role na tabela EFETIVO
                    if u_email:
                        try:
                            db.table('efetivo').update({'role': role_selected}).eq('email', u_email).execute()
                        except Exception as ef_err1:
                            print(f"[EFETIVO UPDATE EMAIL ERR] {ef_err1}")

                    if u_guerra:
                        try:
                            db.table('efetivo').update({'role': role_selected}).ilike('nome_guerra', u_guerra).execute()
                        except Exception as ef_err2:
                            print(f"[EFETIVO UPDATE GUERRA ERR] {ef_err2}")

                role_labels = {
                    'admin': '👑 Administrador',
                    'supervisor': '⚖️ Supervisor COMSOC',
                    'oficial_gab': '⚖️ Oficial do Gabinete',
                    'oficial': '⚓ Oficial da OM',
                    'praca_gab': '📜 Praça do Gabinete',
                    'comsoc': '📸 Equipe COMSOC (Foto/Vídeo)',
                    'comsoc_design': '🎨 Equipe COMSOC (Design)',
                    'militar': '⚓ Militar / Efetivo em Geral'
                }
                label_str = role_labels.get(role_selected, role_selected)

                confirm_txt = (
                    f"✅ **SOLICITAÇÃO DE ACESSO APROVADA!**\n\n"
                    f"👤 **Operador:** `{u_guerra.upper()}`\n"
                    f"📧 **E-mail:** `{u_email}`\n"
                    f"⚙️ **Perfil Concedido:** {label_str}"
                )

                # Edita a mensagem no chat do administrador
                try:
                    await bot.edit_message_text(
                        confirm_txt,
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    await bot.send_message(
                        call.message.chat.id,
                        confirm_txt,
                        parse_mode='Markdown'
                    )

                # Se houver ID do Telegram do usuário solicitante, notifica-o!
                if u_tg_id:
                    try:
                        await bot.send_message(
                            int(u_tg_id),
                            f"🎉 **SEU ACESSO AO SISGAB FOI APROVADO!**\n\n"
                            f"Seu perfil foi ativado como: **{label_str}**.\n"
                            f"Você já pode utilizar todas as funcionalidades do sistema na Web e no Telegram!",
                            parse_mode='Markdown'
                        )
                    except Exception as notif_user_err:
                        print(f"[NOTIFY USER APPROVED ERR] {notif_user_err}")

            elif call.data.startswith('reject_req:'):
                req_id = call.data.split(':', 1)[1]
                await bot.answer_callback_query(call.id, "Solicitação rejeitada.")

                if db:
                    for tbl in ['RegistrationRequests', 'registration_requests']:
                        try:
                            db.table(tbl).update({'status': 'rejected'}).eq('id', req_id).execute()
                        except Exception:
                            pass

                try:
                    await bot.edit_message_text(
                        f"❌ **SOLICITAÇÃO DE ACESSO REJEITADA.**\nID da solicitação: `{req_id}`",
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        parse_mode='Markdown'
                    )
                except Exception:
                    pass
        except Exception as err:
            print(f"[APPROVAL CALLBACK ERR] {err}")
            try:
                await bot.answer_callback_query(call.id, f"Erro: {err}")
            except Exception:
                pass

    import time
    import asyncio
    
    async def render_upload_event_menu(chat_id, page=0, search_query=None, edit_message_id=None):
        db = get_db_connection()
        from database import get_demanda_drive_url
        try:
            query = db.table('demandas_comunicacao').select('*').in_('status', ['aprovado', 'aprovada', 'concluida'])
            
            if search_query:
                query = query.ilike('titulo_evento', f'%{search_query}%')
            
            offset_val = page * 8
            res = query.order('data_evento', desc=True).range(offset_val, offset_val + 7).execute()
            events = res.data if res and res.data else []
            
            if not events and page > 0:
                await bot.send_message(chat_id, "⚠️ Nenhuma outra pauta mais antiga encontrada.")
                return
            elif not events and search_query:
                await bot.send_message(chat_id, f"⚠️ Nenhuma pauta encontrada com o termo '{search_query}'. Tente outra palavra-chave.")
                return
            elif not events:
                await bot.send_message(chat_id, "⚠️ Nenhuma pauta aprovada ou concluída encontrada no sistema.")
                if chat_id in _upload_state:
                    del _upload_state[chat_id]
                return

            markup = types.InlineKeyboardMarkup(row_width=1)
            for ev in events:
                dt_label = str(ev.get('data_evento', ''))[:10]
                tit_label = str(ev.get('titulo_evento', ''))[:40]
                d_url = get_demanda_drive_url(ev)
                has_drive = "📁" if d_url else "➕📂"
                markup.add(types.InlineKeyboardButton(f"{has_drive} {dt_label} — {tit_label}", callback_data=f"upload_evt_{ev['id']}"))
            
            # Linha de Navegação e Busca
            nav_row = []
            if page > 0:
                nav_row.append(types.InlineKeyboardButton(f"⬅️ Pág {page}", callback_data=f"upload_pg_{page-1}"))
            nav_row.append(types.InlineKeyboardButton("🔍 Pesquisar", callback_data="upload_search_evt"))
            if len(events) >= 8:
                nav_row.append(types.InlineKeyboardButton(f"Pág {page+2} ➡️", callback_data=f"upload_pg_{page+1}"))
            
            markup.row(*nav_row)
            markup.add(types.InlineKeyboardButton("❌ Cancelar Upload", callback_data="upload_evt_cancel"))
            
            n_photos = len(_upload_state.get(chat_id, {}).get('photos', []))
            header_text = f"📸 *ENVIO DE FOTOS PARA O DRIVE*\nRecebi {n_photos} foto(s).\n\n"
            if search_query:
                header_text += f"🔍 *Resultado da busca:* '{search_query}' (Pág {page+1}):"
            else:
                header_text += f"Escolha o evento para salvar no Drive (Pág {page+1}):\n_(Ícone ➕📂 cria a pasta no Drive automaticamente se não existir)_"
            
            if edit_message_id:
                try:
                    await bot.edit_message_text(header_text, chat_id=chat_id, message_id=edit_message_id, parse_mode="Markdown", reply_markup=markup)
                    return
                except Exception:
                    pass
            await bot.send_message(chat_id, header_text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"[RENDER UPLOAD MENU ERR] {e}")
            if chat_id in _upload_state:
                del _upload_state[chat_id]

    async def wait_for_photos(chat_id):
        while True:
            await asyncio.sleep(1)
            if chat_id not in _upload_state:
                break
            if time.time() - _upload_state[chat_id]['last_time'] >= 4.0:
                if not _upload_state[chat_id].get('waiting_event'):
                    _upload_state[chat_id]['waiting_event'] = True
                    await render_upload_event_menu(chat_id, page=0)
                break

    @bot.callback_query_handler(func=lambda call: call.data == 'upload_evt_cancel')
    async def handle_cancel_upload(call):
        chat_id = call.message.chat.id
        if chat_id in _upload_state:
            del _upload_state[chat_id]
        await bot.answer_callback_query(call.id, "Upload cancelado.")
        try:
            await bot.edit_message_text("❌ Upload de fotos cancelado.", chat_id=chat_id, message_id=call.message.message_id)
        except Exception:
            pass

    @bot.callback_query_handler(func=lambda call: call.data.startswith('upload_pg_'))
    async def handle_upload_pagination(call):
        chat_id = call.message.chat.id
        try:
            pg = int(call.data.split('_')[2])
        except Exception:
            pg = 0
        s_query = _upload_state.get(chat_id, {}).get('search_query')
        await bot.answer_callback_query(call.id)
        await render_upload_event_menu(chat_id, page=pg, search_query=s_query, edit_message_id=call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == 'upload_search_evt')
    async def handle_upload_search_prompt(call):
        chat_id = call.message.chat.id
        if chat_id in _upload_state:
            _upload_state[chat_id]['waiting_search_query'] = True
        await bot.answer_callback_query(call.id, "Digite a palavra-chave no chat")
        await bot.send_message(chat_id, "🔍 *BUSCA DE EVENTOS*\nDigite no chat o nome, palavra-chave ou local da pauta que deseja pesquisar:", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('upload_evt_'))
    async def handle_upload_event_callback(call):
        chat_id = call.message.chat.id
        demanda_id = call.data.split('_')[2]
        
        if chat_id not in _upload_state or not _upload_state[chat_id].get('photos'):
            await bot.answer_callback_query(call.id, "Sessão expirada ou nenhuma foto na fila.")
            return

        photos_info = _upload_state[chat_id]['photos']
        await bot.answer_callback_query(call.id, "Processando evento...")
        
        db = get_db_connection()
        res = db.table('demandas_comunicacao').select('*').eq('id', demanda_id).execute()
        if not res or not res.data:
            await bot.send_message(chat_id, "❌ Erro: Evento não encontrado.")
            return
            
        demanda = res.data[0]
        
        from database import get_demanda_drive_url
        d_url = get_demanda_drive_url(demanda)
        
        # Se a pauta ainda não tem pasta no Drive, cria a pasta agora no Google Drive!
        if not d_url:
            await bot.send_message(chat_id, f"📂 *Criando pasta no Google Drive...*\nAguarde, gerando pasta para: *{demanda.get('titulo_evento')}*", parse_mode="Markdown")
            import drive_service
            drive_service.reset_drive_service()
            tit_e = demanda.get('titulo_evento', 'Evento')
            dt_e = demanda.get('data_evento', '')
            res_drive = await asyncio.to_thread(drive_service.criar_pasta_evento, tit_e, dt_e)
            if res_drive and res_drive.get('evento_link'):
                d_url = res_drive.get('evento_link')
                demanda['drive_folder_id'] = res_drive.get('evento_folder_id')
                demanda['drive_url'] = d_url
                try:
                    db.table('processed_photos').insert({
                        'event_name': demanda.get('titulo_evento', ''),
                        'filename': 'drive_folder_link',
                        'drive_link': d_url,
                        'uploaded_by': str(chat_id),
                        'created_at': datetime.now().isoformat()
                    }).execute()
                    await bot.send_message(chat_id, f"✅ Pasta criada no Drive com sucesso!\n🔗 {d_url}")
                except Exception as e_up:
                    print(f"[TELEGRAM DRIVE UPDATE ERR] {e_up}")
            else:
                await bot.send_message(chat_id, "⚠️ Não foi possível criar a pasta no Drive. Verifique as configurações da Service Account no Admin.")
                return

        await bot.send_message(chat_id, f"⏳ Iniciando upload de {len(photos_info)} foto(s)... Por favor, aguarde.")
        
        from .utils import upload_photos_to_drive
        success_count = await upload_photos_to_drive(bot, chat_id, photos_info, demanda)
        
        d_link_final = get_demanda_drive_url(demanda) or demanda.get('drive_url', '')
        if success_count > 0:
            await bot.send_message(chat_id, f"✅ {success_count} fotos enviadas para o Drive!\n📍 Evento: *{demanda.get('titulo_evento')}*\n🔗 Link: {d_link_final}", parse_mode="Markdown")
        else:
            await bot.send_message(chat_id, "❌ Falha ao enviar fotos para o Drive. Tente novamente.")
            
        if chat_id in _upload_state:
            del _upload_state[chat_id]

    @bot.message_handler(content_types=['document'], func=lambda msg: msg.document and msg.document.mime_type and msg.document.mime_type.startswith('image/'))
    async def handle_document_photo(message):
        chat_id = message.chat.id
        if chat_id not in _upload_state:
            _upload_state[chat_id] = {'photos': [], 'last_time': time.time(), 'waiting_event': False}
            asyncio.create_task(wait_for_photos(chat_id))
        else:
            _upload_state[chat_id]['last_time'] = time.time()
            
        file_info = {'file_id': message.document.file_id, 'file_name': message.document.file_name}
        _upload_state[chat_id]['photos'].append(file_info)

    @bot.message_handler(content_types=['photo'])
    async def handle_regular_photo(message):
        chat_id = message.chat.id
        
        is_new = chat_id not in _upload_state
        if is_new:
            _upload_state[chat_id] = {'photos': [], 'last_time': time.time(), 'waiting_event': False}
            asyncio.create_task(wait_for_photos(chat_id))
            await bot.send_message(chat_id, "📌 Dica: Envie como documento para manter a qualidade HD!")
        else:
            _upload_state[chat_id]['last_time'] = time.time()
            
        best_photo = message.photo[-1]
        file_info = {'file_id': best_photo.file_id, 'file_name': f"photo_{best_photo.file_id}.jpg"}
        _upload_state[chat_id]['photos'].append(file_info)

    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith('acervo_'))
    async def handle_acervo_callback(call):
        chat_id = call.message.chat.id
        data = call.data
        
        if data == 'acervo_cancel':
            await bot.answer_callback_query(call.id, 'Cancelado')
            await bot.edit_message_text('Busca cancelada.', chat_id, call.message.message_id)
            clear_state(chat_id)
            return
        
        if data.startswith('acervo_select:'):
            ev_id = data.split(':')[1]
            # Buscar dados do evento
            db = get_db_connection()
            if not db:
                await bot.answer_callback_query(call.id, 'Banco offline')
                return
            try:
                res = db.table('demandas_comunicacao').select('*').eq('id', int(ev_id)).execute()
                if not res.data:
                    await bot.answer_callback_query(call.id, 'Evento nao encontrado')
                    return
                ev = res.data[0]
                titulo = ev.get('titulo_evento', 'Evento')
                data_ev = ev.get('data_evento', '')
                drive_url = ev.get('drive_url', '')
                
                from .keyboards import get_acervo_actions_keyboard
                msg = f"📸 *{titulo}*\n📅 {data_ev}\n"
                if drive_url:
                    msg += f"📁 Drive: {drive_url}\n"
                msg += "\nEscolha uma acao:"
                
                await bot.edit_message_text(msg, chat_id, call.message.message_id, parse_mode='Markdown', reply_markup=get_acervo_actions_keyboard(ev_id))
                await bot.answer_callback_query(call.id)
            except Exception as e:
                await bot.answer_callback_query(call.id, f'Erro: {str(e)[:50]}')
            return
        
        if data.startswith('acervo_album:'):
            ev_id = data.split(':')[1]
            await bot.answer_callback_query(call.id, 'Baixando fotos...')
            db = get_db_connection()
            if db:
                from database import get_demanda_drive_url
                res = db.table('demandas_comunicacao').select('*').eq('id', int(ev_id)).execute()
                if res.data:
                    ev = res.data[0]
                    import drive_service
                    fid = ev.get('drive_folder_id', '')
                    url = get_demanda_drive_url(ev)
                    if not fid and url:
                        if 'folders/' in url:
                            fid = url.split('folders/')[-1].split('?')[0].split('/')[0]
                    if fid:
                        sel_fid = drive_service.find_folder('SELEÇÃO', fid) or fid
                        from .utils import enviar_album_hd_drive
                        await enviar_album_hd_drive(bot, chat_id, sel_fid)
                    else:
                        await bot.send_message(chat_id, "⚠️ Pasta do Drive não vinculada a este evento.")
            clear_state(chat_id)
            return
        
        if data.startswith('acervo_links:'):
            ev_id = data.split(':')[1]
            await bot.answer_callback_query(call.id, 'Buscando links...')
            ev_data = None
            
            # 1. Tenta pegar do mapa em memoria
            if chat_id in chat_states and 'acervo_map' in chat_states[chat_id]:
                ev_data = chat_states[chat_id]['acervo_map'].get(ev_id)
                
            # 2. Se nao encontrou em memoria, busca no banco
            if not ev_data:
                db = get_db_connection()
                if db:
                    try:
                        ev_id_val = int(ev_id) if ev_id.isdigit() else ev_id
                        res = db.table('demandas_comunicacao').select('*').eq('id', ev_id_val).execute()
                        if res.data:
                            ev_data = res.data[0]
                    except Exception as e_db:
                        print(f"[ACERVO LINKS DB ERR] {e_db}")
                        
            if ev_data:
                from .utils import enviar_links_acervo
                await enviar_links_acervo(bot, chat_id, ev_data)
            else:
                await bot.send_message(chat_id, "⚠️ Evento não encontrado.")
                
            clear_state(chat_id)
            return

        if data.startswith('acervo_portal:'):
            ev_id = data.split(':')[1]
            await bot.answer_callback_query(call.id)
            db = get_db_connection()
            if db:
                try:
                    ev_id_val = int(ev_id) if ev_id.isdigit() else ev_id
                    res = db.table('demandas_comunicacao').select('*').eq('id', ev_id_val).execute()
                    if res.data:
                        ev_item = res.data[0]
                        titulo = ev_item.get('titulo_evento', 'Evento')
                        slug = str(ev_item.get('id', ev_id))
                        portal_url = f"https://sisgab-cgcfn.ddns.net/evento/{slug}"
                        msg_portal = (
                            f"🌐 **PORTAL DO CONVIDADO — SISGAB**\n\n"
                            f"📌 **Evento:** {titulo}\n"
                            f"📅 **Data:** {ev_item.get('data_evento', 'N/I')}\n\n"
                            f"🔗 **Link Público de Entrega:**\n{portal_url}\n\n"
                            f"💡 *Convidados podem acessar este link, registrar uma selfie e receber suas fotos automaticamente em tempo real!*"
                        )
                        await bot.send_message(chat_id, msg_portal, parse_mode='Markdown')
                    else:
                        await bot.send_message(chat_id, "⚠️ Evento não localizado no banco.")
                except Exception as e_p:
                    await bot.send_message(chat_id, f"❌ Erro ao consultar portal: {e_p}")
            clear_state(chat_id)
            return

    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith('confirm_ia_demanda:'))
    async def handle_confirm_ia_demanda_callback(call):
        chat_id = call.message.chat.id if call.message else call.from_user.id
        action_code = call.data.split(':')[1]
        try:
            await bot.answer_callback_query(call.id)
        except Exception:
            pass

        if chat_id in chat_states and 'parsed_registro' in chat_states[chat_id]:
            registro = chat_states[chat_id]['parsed_registro']
            if action_code == 'yes':
                db = get_db_connection()
                if db:
                    try:
                        res = db.table('demandas_comunicacao').insert(registro).execute()
                        dem_id = res.data[0]['id'] if res and res.data else ''
                        id_txt = f" (ID #{dem_id})" if dem_id else ""
                        fotografo_txt = f"\n📸 **Equipe/Fotógrafo:** {registro.get('notificar_militar_ids')}" if registro.get('notificar_militar_ids') else ""
                        periodo_txt = f" a {registro['data_fim']}" if registro.get('data_fim') and registro['data_fim'] != registro['data_evento'] else ""
                        
                        confirm_msg = (
                            f"✅ **Pauta confirmada e salva com sucesso via IA!**{id_txt}\n\n"
                            f"📌 **Evento:** {registro['titulo_evento']}\n"
                            f"📅 **Data:** {registro['data_evento']}{periodo_txt} às {registro['hora_evento']}\n"
                            f"📍 **Local:** {registro['local_evento']}\n"
                            f"👤 **Solicitante:** {registro['solicitante_nome']}"
                            f"{fotografo_txt}\n\n"
                            "A pauta foi incluída na lista de demandas da COMSOC!"
                        )
                        await bot.edit_message_text(confirm_msg, chat_id, call.message.message_id, parse_mode='Markdown')
                    except Exception as e_save:
                        await bot.send_message(chat_id, f"❌ Erro ao salvar pauta: {e_save}")
            else:
                await bot.edit_message_text("❌ *Inclusão da pauta cancelada.*", chat_id, call.message.message_id, parse_mode='Markdown')
            clear_state(chat_id)
        else:
            await bot.send_message(chat_id, "⚠️ A sessão expirou ou os dados já foram salvos. Envie novamente o texto da pauta se necessário.")

    @bot.message_handler(func=lambda msg: True)
    async def handle_all_messages(message):
        chat_id = message.chat.id
        
        db = get_db_connection()
        
        # Guard: mensagens sem texto (stickers, contatos, etc)
        if not message.text:
            return
        
        text = message.text.strip()

        # Log de Acesso para Auditoria de Métricas (Admin)
        try:
            from database import log_telegram_access
            u_name = message.from_user.first_name or message.from_user.username or 'Militar'
            log_telegram_access(chat_id, u_name, text)
        except Exception:
            pass

        # Intercepta busca de eventos para envio de fotos no Telegram
        if chat_id in _upload_state and _upload_state[chat_id].get('waiting_search_query'):
            _upload_state[chat_id]['waiting_search_query'] = False
            _upload_state[chat_id]['search_query'] = text
            await render_upload_event_menu(chat_id, page=0, search_query=text)
            return
        # =====================================================================
        # SEÇÃO 1: Roteamento de Teclado Principal (usuário SEM estado ativo)
        # =====================================================================
        if chat_id not in chat_states:
            profile = await check_authorized_user(message.from_user.id)
            
            # --- Usuário NÃO autorizado ---
            if not profile:
                if "vincular" in text.lower() or text == "🔗 Vincular Meu Nome":
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

            # Se o usuário clicar em qualquer botão do Telegram enquanto estava em um prompt de edição, cancela a edição pendente!
            button_prefixes = ('❌ ', '✅ ', '🎯 ', '🔄 ', '✏️ ', '👤 ', '⚙️ ', '🔎 ', '📋 ', '⚡ ', '🟢 ', '🪑 ', '➕ ')
            if chat_id in chat_states:
                st_act = chat_states[chat_id].get('action')
                if st_act in ('edit_titulo_demanda', 'edit_local_demanda', 'edit_hora_demanda', 'assign_equipe') and text.startswith(button_prefixes):
                    clear_state(chat_id)

            if text == "⚙️ Configurações":
                chat_states[chat_id] = {
                    'action': 'settings',
                    'step': 'main_menu',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(message, "⚙️ **CONFIGURAÇÕES**\nEscolha uma das opções abaixo:", reply_markup=get_settings_keyboard(True, is_operator))

            elif text in ("📸 Enviar Fotos / Drive", "📸 Enviar Fotos", "/upload"):
                await bot.reply_to(
                    message,
                    "📸 *ENVIO DE FOTOS PARA O GOOGLE DRIVE*\n\n"
                    "Envie **uma ou várias fotos (ou arquivos de imagem)** diretamente aqui no chat do Telegram!\n\n"
                    "O assistente identificará as fotos e exibirá o menu para você escolher o evento (ou criar a pasta no Drive na hora se não existir).",
                    parse_mode='Markdown'
                )

            elif text in ("🙋 Minhas Fotos (IA)", "📸 Minhas Fotos", "/minhas_fotos"):
                from .handlers_commands import minhas_fotos_cmd
                await minhas_fotos_cmd(message)

            elif text in ("📂 Buscar Acervo", "/acervo"):
                chat_states[chat_id] = {
                    'action': 'buscar_acervo',
                    'step': 'await_query',
                    'user': profile
                }
                await bot.reply_to(
                    message,
                    "📂 *BUSCAR ACERVO FOTOGRAFICO*\n\n"
                    "Digite o nome, data ou descricao do evento que deseja buscar.\n\n"
                    "_Exemplo: almoco com senador, solenidade agosto, banda marcial..._",
                    parse_mode='Markdown',
                    reply_markup=get_cancel_keyboard()
                )

            elif text == "➕ Criar Demanda":
                chat_states[chat_id] = {
                    'action': 'criar_demanda',
                    'step': 'solicitante_om',
                    'user': profile,
                    'data': {
                        'selected_services_set': set()
                    }
                }
                await bot.reply_to(
                    message, 
                    "📋 **NOVA SOLICITAÇÃO DE PAUTA — CGCFN**\n\n[Passo 1/9] ⚓ A solicitação é do **CGCFN** ou de **Outra OM**?", 
                    reply_markup=get_om_keyboard(), 
                    parse_mode='Markdown'
                )

            elif text in ("👥 Cadastros Pendentes", "🔑 Aprovar Cadastros", "/pendentes", "/cadastros", "/usuarios", "/aprovar"):
                user_role = str(profile.get('role', '')).lower()
                if user_role not in ('admin', 'supervisor', 'oficial_gab', 'oficial'):
                    await bot.reply_to(message, "⛔ Apenas Administradores ou Supervisores podem gerenciar solicitações de cadastro.")
                    return
                await listar_cadastros_pendentes(bot, message)
                return

            elif text in ("📋 Gerenciar Demandas", "📋 Voltar para Lista de Demandas", "/demandas", "/gerenciar"):
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco de dados indisponível.")
                    return
                try:
                    res_dem = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'aprovado', 'pendente', 'em_ajuste', 'ajustes']).order('data_evento', desc=False).order('hora_evento', desc=False).limit(15).execute()
                    demandas = res_dem.data if res_dem.data else []
                    if not demandas:
                        await bot.reply_to(message, "🟢 Nenhuma demanda ativa pendente de gestão no momento.", reply_markup=get_main_menu_keyboard(is_operator))
                        return
                    
                    status_emoji = {
                        'pendente': '🟡 PENDENTE',
                        'aprovada': '🟢 APROVADO',
                        'aprovado': '🟢 APROVADO',
                        'em_ajuste': '🟠 EM AJUSTE',
                        'ajustes': '🟠 EM AJUSTE'
                    }
                    
                    demandas_map = {}
                    list_msg = f"📋 **GERENCIAMENTO DE PAUTAS ATIVAS ({len(demandas)})**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    for d in demandas:
                        d_id = d.get('id')
                        tit = d.get('titulo_evento', 'Sem Título')
                        dt_raw = d.get('data_evento', 'N/I')
                        dt_formatted = dt_raw
                        dt_short = ""
                        try:
                            parts = str(dt_raw).split('T')[0].split(' ')[0].split('-')
                            if len(parts) == 3:
                                dt_formatted = f"{parts[2]}/{parts[1]}/{parts[0]}"
                                dt_short = f"{parts[2]}/{parts[1]}"
                        except Exception:
                            pass

                        hr_raw = str(d.get('hora_evento', '09:00'))[:5]
                        raw_st = str(d.get('status', 'pendente')).lower()
                        st_display = status_emoji.get(raw_st, f'⚪ {raw_st.upper()}')
                        loc = d.get('local_evento', 'N/I')
                        resp_txt = escape_markdown(str(_format_militar_responsavel(d, db)))
                        tit_esc = escape_markdown(str(tit))
                        loc_esc = escape_markdown(str(loc))

                        dt_hdr = f"({dt_short}) " if dt_short else ""
                        list_msg += f"📌 **{dt_hdr}{tit_esc}**\n   📅 {dt_formatted} às {hr_raw} | 📍 {loc_esc}\n   ⚡ {st_display} | 👨‍✈️ Equipe: {resp_txt}\n\n"

                        btn_label = f"⚙️ #{d_id} — {dt_hdr}{(tit or 'Pauta')[:15]}".strip()
                        demandas_map[btn_label] = d_id

                    # NÃO setar estado aqui — os handlers de "⚙️ #ID" e "🔎 Detalhes" vivem na SEÇÃO 1
                    # e precisam que o chat_id NÃO esteja em chat_states para funcionar.

                    list_msg += "👇 **Selecione a pauta no teclado de resposta rápida abaixo para gerenciar:**"
                    try:
                        await bot.send_message(chat_id, list_msg, reply_markup=get_demandas_list_reply_keyboard(demandas), parse_mode='Markdown')
                    except Exception:
                        clean_list = list_msg.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
                        await bot.send_message(chat_id, clean_list, reply_markup=get_demandas_list_reply_keyboard(demandas))
                except Exception as e_dem:
                    await bot.reply_to(message, f"❌ Erro ao listar demandas: {e_dem}")

            elif (text.startswith("⚙️ ") and text != "⚙️ Configurações") or text.startswith("⚙️ #"):
                try:
                    import re
                    dem_id = None
                    # 1. Extração direta de ID numérico via regex (ex: ⚙️ #14 — (03/08) FAINA DO CPROT)
                    match_id = re.search(r'#(\d+)', text)
                    if match_id:
                        dem_id = match_id.group(1)

                    # 2. Busca no mapa de estado da sessão
                    if not dem_id and chat_id in chat_states and chat_states[chat_id].get('demandas_map'):
                        dem_id = chat_states[chat_id]['demandas_map'].get(text)

                    # 3. Busca no banco por correspondência de título (para botões antigos sem #ID)
                    if not dem_id:
                        db = get_db_connection()
                        if db:
                            res_dem = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'aprovado', 'pendente', 'em_ajuste', 'ajustes']).order('data_evento', desc=False).order('hora_evento', desc=False).limit(30).execute()
                            for d in (res_dem.data or []):
                                d_tit = str(d.get('titulo_evento', '')).strip().upper()
                                text_clean = text.replace('⚙️', '').replace('(', '').replace(')', '').strip().upper()
                                # Se o título do evento estiver contido no texto do botão clicado
                                if d_tit and (d_tit in text_clean or text_clean in d_tit or d_tit[:10] in text_clean):
                                    dem_id = d.get('id')
                                    break


                    if dem_id:
                        db = get_db_connection()
                        res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                        if res_d and res_d.data:
                            d = res_d.data[0]
                            tit = d.get('titulo_evento', 'Sem Título')
                            raw_st = str(d.get('status', 'pendente')).lower()
                            dt_raw = d.get('data_evento', '')
                            dt_short = ""
                            try:
                                parts = str(dt_raw).split('T')[0].split(' ')[0].split('-')
                                if len(parts) == 3:
                                    dt_short = f"{parts[2]}/{parts[1]}"
                            except Exception:
                                pass
                            dt_hdr = f"({dt_short}) " if dt_short else ""
                            
                            txt = (
                                f"⚙️ **PAUTA SELECIONADA: {dt_hdr}{escape_markdown(tit)}**\n"
                                f"Status atual: **{raw_st.upper()}**\n\n"
                                f"Escolha a ação desejada no teclado de resposta rápida no rodapé:"
                            )
                            try:
                                await bot.send_message(chat_id, txt, reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=raw_st), parse_mode='Markdown')
                            except Exception:
                                await bot.send_message(chat_id, txt.replace('*', '').replace('_', ''), reply_markup=get_demanda_actions_reply_keyboard(dem_id, status=raw_st))
                    else:
                        await bot.reply_to(message, "⚠️ Não foi possível identificar a pauta selecionada.")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao selecionar demanda: {e}")

            elif text.startswith("🔎 Detalhes #"):
                try:
                    dem_id = text.split('#')[1].strip()
                    db = get_db_connection()
                    res_d = db.table('demandas_comunicacao').select('*').eq('id', dem_id).execute()
                    if res_d and res_d.data:
                        d = res_d.data[0]
                        tit = d.get('titulo_evento', 'Sem Título')
                        dt = d.get('data_evento', 'N/I')
                        hr = d.get('hora_evento', 'N/I')
                        loc = d.get('local_evento', 'N/I')
                        st = str(d.get('status', 'pendente')).upper()
                        obs = d.get('observacoes') or (d.get('autoridades') if 'Obs:' in str(d.get('autoridades')) else '') or 'Nenhuma'
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
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'concluida'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"🎯 **MISSÃO CONCLUÍDA!**\nPauta ID #{dem_id} foi encerrada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    from notifications_manager import notify_telegram
                    notify_telegram(f"🎯 **Pauta Concluída via Telegram**\nID #{dem_id} foi finalizada.", "system")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao concluir pauta: {e}")

            elif text.startswith("✅ Aprovar #"):
                clear_state(chat_id)
                try:
                    dem_id = text.split('#')[1].strip()
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'aprovada'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"✅ **PAUTA APROVADA!**\nPauta ID #{dem_id} foi homologada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    from notifications_manager import notify_telegram
                    notify_telegram(f"✅ **Pauta Aprovada via Telegram**\nID #{dem_id} foi homologada.", "system")
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao aprovar pauta: {e}")

            elif text.startswith("❌ Rejeitar #"):
                clear_state(chat_id)
                try:
                    dem_id = text.split('#')[1].strip()
                    db = get_db_connection()
                    db.table('demandas_comunicacao').update({'status': 'rejeitado'}).eq('id', dem_id).execute()
                    await bot.reply_to(message, f"❌ **PAUTA REJEITADA!**\nPauta ID #{dem_id} foi marcada como rejeitada.", reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao rejeitar pauta: {e}")

            elif text.startswith("🔄 Reabrir Pauta #"):
                try:
                    dem_id = text.split('#')[1].strip()
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
                    db = get_db_connection()
                    res_ef = db.table('efetivo').select('*').execute()
                    efetivo_list = res_ef.data if res_ef.data else []
                    from .utils import sort_efetivo_by_rank
                    efetivo_list = sort_efetivo_by_rank(efetivo_list)

                    # Buscar militares ja vinculados no banco
                    current_ids = set()
                    try:
                        res_dem = db.table('demandas_comunicacao').select('notificar_militar_ids').eq('id', dem_id).execute()
                        if res_dem and res_dem.data and res_dem.data[0].get('notificar_militar_ids'):
                            raw_json = res_dem.data[0]['notificar_militar_ids']
                            parsed_ids = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                            current_ids = set(str(x) for x in parsed_ids if str(x).isdigit())
                    except Exception as res_err:
                        print(f"[FETCH CURRENT EQUIPE ERR] {res_err}")

                    chat_states[chat_id] = {
                        'action': 'assign_equipe',
                        'demanda_id': dem_id,
                        'selected_ids': current_ids,
                        'efetivo_list': efetivo_list
                    }

                    sel_nomes = []
                    for ef in efetivo_list:
                        if str(ef.get('id')) in current_ids:
                            sel_nomes.append(f"{ef.get('posto_grad') or ''} {ef.get('nome_guerra', '')}".strip())

                    nomes_txt = "\n".join([f"   • {n}" for n in sel_nomes]) if sel_nomes else "   • Nenhum selecionado ainda"

                    await bot.send_message(
                        chat_id,
                        f"👤 **ATRIBUIR EQUIPE OPERACIONAL (ID #{dem_id})**\n\n"
                        f"👥 **Militares Atualmente Selecionados ({len(current_ids)}):**\n{nomes_txt}\n\n"
                        f"Clique nos botões de resposta rápida para alternar cada militar e em **➡️ CONCLUIR SELEÇÃO DA EQUIPE ➡️** ao terminar:",
                        reply_markup=get_efetivo_linking_keyboard(efetivo_list, selected_ids=current_ids, is_multi=True),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao carregar efetivo: {e}")

            elif text in ("🪑 Placas JADE", "/jade", "/placas"):
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
                    await bot.reply_to(message, msg_jade, reply_markup=get_jade_menu_inline_keyboard(), parse_mode='Markdown')
                except Exception as e_j:
                    await bot.reply_to(message, f"❌ Erro ao consultar placas JADE: {e_j}")

            elif text in ("🔌 Cautelas Ativas", "/cautelas", "/cautela"):
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco de dados indisponível.")
                    return
                try:
                    res_caut = db.table('cautela_equipamentos').select('*').eq('status', 'retirado').execute()
                    cautelas = res_caut.data if res_caut and res_caut.data else []
                    
                    if not cautelas:
                        msg_c = (
                            "🔌 **CAUTELAS DE EQUIPAMENTOS ATIVAS**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            "🟢 **Nenhum equipamento encontra-se cautelado no momento.** Todos os itens estão disponíveis no acervo."
                        )
                    else:
                        msg_c = (
                            f"🔌 **EQUIPAMENTOS EM CAUTELAS ATIVAS ({len(cautelas)})**\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        )
                        for c in cautelas:
                            eq = c.get('equipamento') or c.get('equipamento_nome') or 'Equipamento'
                            militar = c.get('retirado_por') or c.get('militar_nome') or 'N/I'
                            dt = c.get('data_retirada') or (c.get('created_at', '')[:10] if c.get('created_at') else 'N/I')
                            msg_c += f"📦 **{eq}**\n   👤 Cautelado por: *{militar}*\n   📅 Data de Retirada: _{dt}_\n\n"
                    
                    await bot.reply_to(message, msg_c, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                except Exception as e_caut:
                    await bot.reply_to(message, f"❌ Erro ao consultar cautelas: {e_caut}", reply_markup=get_main_menu_keyboard(is_operator))

            elif text in ("⚡ Missão Rápida", "/missaorapida", "/missao_rapida"):
                chat_states[chat_id] = {
                    'action': 'missao_rapida',
                    'step': 'input_titulo',
                    'user': profile,
                    'selected_ids': set()
                }
                await bot.reply_to(
                    message,
                    "⚡ **CRIAR MISSÃO RÁPIDA**\n\n"
                    "Digite o **Título ou Objetivo** da missão expressa (ex: *Cobertura Fotográfica da Visita do Comandante*):",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='Markdown'
                )

            elif text in ("🪑 Solicitar Assento JADE", "/solicitar_assento", "/novo_assento"):
                chat_states[chat_id] = {
                    'action': 'solicitar_assento_jade',
                    'step': 'select_posto',
                    'user': profile,
                    'data': {}
                }
                await bot.reply_to(
                    message,
                    "🏛️ **JADE — SOLICITAÇÃO EXPRESSA DE ASSENTO DE ÚLTIMA HORA**\n\n"
                    "Escolha abaixo o **Posto, Graduação ou Título Civil** no Gabarito Oficial:",
                    reply_markup=get_gabarito_postos_keyboard(),
                    parse_mode='Markdown'
                )

            elif text in ("📋 Pautas COMSOC", "📅 Agenda Semanal", "/agenda", "/semana"):
                try:
                    txt = _get_weekly_events_text()
                    try:
                        await bot.reply_to(message, txt, reply_markup=get_main_menu_keyboard(is_operator), parse_mode='Markdown')
                    except Exception as md_err:
                        print(f"[AGENDA MD ERR] {md_err}")
                        clean_txt = txt.replace('**', '').replace('__', '').replace('*', '').replace('_', '').replace('\\', '')
                        await bot.reply_to(message, clean_txt, reply_markup=get_main_menu_keyboard(is_operator))
                except Exception as err_ag:
                    print(f"[AGENDA HANDLER ERR] {err_ag}")
                    await bot.reply_to(message, f"❌ Erro ao carregar agenda: {err_ag}", reply_markup=get_main_menu_keyboard(is_operator))



            elif text == "📋 Dar Presença" or text == "🟢 Dar Presença" or text == "/presenca":
                now_br = datetime.utcnow() - timedelta(hours=3)
                dt_str = now_br.strftime('%Y-%m-%d')
                dt_br = now_br.strftime('%d/%m/%Y')

                chat_states[chat_id] = {
                    'action': 'presenca_diaria',
                    'step': 'choose_sigla',
                    'user': profile,
                    'data': {}
                }

                # Buscar status de presenca atual do militar para hoje
                status_atual_txt = ""
                try:
                    from modulo_presenca import fetch_efetivo_and_presencas, find_presence_for_militar
                    ef_list, p_list = fetch_efetivo_and_presencas(dt_str)
                    p_user = find_presence_for_militar(profile, p_list)
                    if p_user and p_user.get('status'):
                        st_code = p_user.get('status', '').upper()
                        obs_curr = p_user.get('observacao', '').strip()
                        obs_info = f" ({obs_curr})" if obs_curr else ""
                        status_atual_txt = f"\n\n📌 **Seu status atual gravado para hoje ({dt_br}):** *({st_code})*{obs_info}\n*Para alterar ou confirmar, selecione uma sigla abaixo:*"
                except Exception as st_err:
                    print(f"[CHECK PRESENCE CURRENT ERR] {st_err}")

                msg_prompt = (
                    f"🌅 **CHAMADA MATUTINA — CGCFN/SISGAB**\n"
                    f"📅 Data: **{dt_br}**"
                    f"{status_atual_txt}\n\n"
                    f"Por favor, selecione a sigla da sua rotina para hoje:"
                )
                await bot.reply_to(
                    message,
                    msg_prompt,
                    reply_markup=get_presenca_keyboard(),
                    parse_mode='Markdown'
                )

            elif any(sigla_key in text.upper() for sigla_key in ("(P)", "(MA)", "(MT)", "(FE)", "(L)", "(H)", "(DM)", "(S)", "(OUTRO)", "OUTRA SITUAÇÃO")):
                sigla_txt = text.upper()
                sigla_code = None
                
                if '(P)' in sigla_txt or sigla_txt == 'P' or 'PRESENTE' in sigla_txt: sigla_code = 'P'
                elif '(MA)' in sigla_txt or sigla_txt == 'MA' or 'MISSÃO ADM' in sigla_txt: sigla_code = 'MA'
                elif '(MT)' in sigla_txt or sigla_txt == 'MT' or 'MAIS TARDE' in sigla_txt: sigla_code = 'MT'
                elif '(FE)' in sigla_txt or sigla_txt == 'FE' or 'FÉRIAS' in sigla_txt or 'FERIAS' in sigla_txt: sigla_code = 'FE'
                elif '(L)' in sigla_txt or sigla_txt == 'L' or 'LICENÇA' in sigla_txt or 'LICENCA' in sigla_txt: sigla_code = 'L'
                elif '(H)' in sigla_txt or sigla_txt == 'H' or 'HOSPITAL' in sigla_txt: sigla_code = 'H'
                elif '(DM)' in sigla_txt or sigla_txt == 'DM' or 'DISPENSA' in sigla_txt: sigla_code = 'DM'
                elif '(S)' in sigla_txt or sigla_txt == 'S' or 'SERVIÇO' in sigla_txt or 'SERVICO' in sigla_txt: sigla_code = 'S'
                elif '(OUTRO)' in sigla_txt or 'OUTRA SITUAÇÃO' in sigla_txt or 'OUTRO' in sigla_txt: sigla_code = 'OUTRO'

                if sigla_code:
                    state = {
                        'action': 'presenca_diaria',
                        'step': 'choose_sigla',
                        'user': profile,
                        'data': {'status': sigla_code}
                    }
                    chat_states[chat_id] = state
                    
                    if sigla_code in ('MA', 'MT', 'H', 'OUTRO'):
                        state['step'] = 'input_obs'
                        prompts = {
                            'MA': "✍️ Por favor, digite o motivo/local da **Missão Administrativa (MA)**:",
                            'MT': "✍️ Por favor, digite o horário previsto de chegada ou motivo para **(MT) Mais Tarde**:",
                            'H': "✍️ Por favor, digite o hospital ou motivo para **(H) Hospital**:",
                            'OUTRO': "✍️ Por favor, descreva a sua situação/rotina de hoje:"
                        }
                        await bot.reply_to(message, prompts.get(sigla_code, f"✍️ Por favor, digite a observação para **({sigla_code})**:"), reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                    elif sigla_code in ('FE', 'L', 'DM'):
                        state['step'] = 'input_data_fim'
                        await bot.reply_to(message, "🏖️ Por favor, informe a **data de término** das suas férias/licença\n(ex: `20/08`, `20/08/2026` ou número de dias ex: `10`):", reply_markup=get_cancel_keyboard(), parse_mode='Markdown')
                    else:
                        from .utils import _salvar_presenca_bot
                        await _salvar_presenca_bot(bot, message, chat_id, state, sigla_code, "")
                    return

            elif text == "/pronto" or text == "📋 Pronto CheGab":
                now_br = datetime.utcnow() - timedelta(hours=3)
                dt_str = now_br.strftime('%Y-%m-%d')
                try:
                    from modulo_presenca import fetch_efetivo_and_presencas, gerar_texto_pronto_chegab
                    efetivo_lista, presencas_list = fetch_efetivo_and_presencas(dt_str)
                    presencas_dict = {p['nome_guerra'].upper(): p for p in presencas_list if p.get('nome_guerra')}
                    
                    relatorio_txt = gerar_texto_pronto_chegab(dt_str, presencas_dict, efetivo_lista, presencas_list=presencas_list)
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
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "⚠️ Banco offline.")
                    return
                try:
                    try:
                        res = db.table('photo_matches').select('*').eq('militar_id', profile['id']).execute()
                    except Exception:
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

            elif text in ("/relatorio", "/resumo", "📊 Relatório Executivo"):
                from .scheduled_jobs import generate_executive_report
                await generate_executive_report(bot, chat_id)

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

        # 🛡️ MENU OVERRIDE: Se o usuário clicar em qualquer botão do menu principal
        # enquanto está num wizard, limpar o estado e reprocessar na SEÇÃO 1.
        MAIN_MENU_BUTTONS = (
            "📋 Gerenciar Demandas", "📋 Voltar para Lista de Demandas",
            "📅 Agenda Semanal", "📋 Pautas COMSOC",
            "🔌 Cautelas Ativas", "🤖 Digerir Pauta (IA)",
            "📋 Pronto CheGab", "📊 Relatório Executivo",
            "🟢 Dar Presença", "📋 Dar Presença",
            "📸 Enviar Fotos / Drive", "📸 Enviar Fotos",
            "🙋 Minhas Fotos (IA)", "📸 Minhas Fotos",
            "➕ Criar Demanda", "🪑 Placas JADE",
            "⚡ Missão Rápida", "ℹ️ Ajuda",
            "📸 Cadastro Facial", "🔍 Buscar Minhas Fotos",
            "📂 Buscar Acervo",
            "🪑 Solicitar Assento JADE", "⚙️ Configurações",
            "👥 Cadastros Pendentes", "🔑 Aprovar Cadastros",
        )
        # Também detectar botões de ação de demanda (⚙️ #ID, 🔎 Detalhes, ✅ Aprovar, etc.)
        is_demanda_action = (
            text.startswith("⚙️ #") or text.startswith("⚙️ ") or
            text.startswith("🔎 Detalhes #") or text.startswith("🎯 Concluir Missão #") or
            text.startswith("✅ Aprovar #") or text.startswith("❌ Rejeitar #") or
            text.startswith("🔄 Reabrir Pauta #") or text.startswith("✏️ Editar") or
            text.startswith("👤 Equipe #")
        )
        if text in MAIN_MENU_BUTTONS or is_demanda_action:
            clear_state(chat_id)
            # Re-invocar o handler como se fosse SEÇÃO 1 (sem estado)
            return await handle_all_messages(message)

        if text in ["❌ Cancelar", "cancelar"]:
            clear_state(chat_id)
            await bot.reply_to(message, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard(is_operator) if profile else get_unauthorized_keyboard())
            return

        if action == 'buscar_acervo':
            if step == 'await_query':
                from difflib import SequenceMatcher
                query = text.strip()
                db = get_db_connection()
                if not db:
                    await bot.reply_to(message, "Banco de dados indisponivel.")
                    clear_state(chat_id)
                    return
                try:
                    res = db.table('demandas_comunicacao').select('*').in_('status', ['aprovada', 'concluida']).order('data_evento', desc=True).execute()
                    if not res.data:
                        await bot.reply_to(message, "Nenhum evento encontrado.", reply_markup=get_main_menu_keyboard(is_operator))
                        clear_state(chat_id)
                        return
                    
                    # Busca fuzzy com suporte a datas exatas (ex: 12 de agosto, 12/08)
                    from comsoc_galeria_components import parse_date_query
                    day_str, month_str, year_str = parse_date_query(query)
                    scored = []
                    
                    if day_str and month_str:
                        target_pattern = f"{year_str}-{month_str}-{day_str}" if year_str else f"-{month_str}-{day_str}"
                        for ev in res.data:
                            data_ev = str(ev.get('data_evento') or '')
                            if target_pattern in data_ev or (data_ev.endswith(f"-{month_str}-{day_str}")):
                                scored.append((ev, 0.99))
                    else:
                        query_up = query.upper()
                        words = [w for w in query_up.split() if len(w) > 2 and w not in ('DE', 'DO', 'DA', 'EM')]
                        for ev in res.data:
                            titulo = (ev.get('titulo_evento') or '').upper()
                            data = (ev.get('data_evento') or '')
                            full = f"{data} {titulo}".upper()
                            if query_up in full:
                                scored.append((ev, 0.95))
                            elif words:
                                hits = sum(1 for w in words if w in full)
                                if hits > 0:
                                    scored.append((ev, hits / len(words) * 0.8))
                                else:
                                    ratio = SequenceMatcher(None, query_up, titulo).ratio()
                                    if ratio > 0.35:
                                        scored.append((ev, ratio))
                    
                    scored.sort(key=lambda x: x[1], reverse=True)
                    top = scored[:8]
                    
                    if not top:
                        # Fallback: busca IA
                        try:
                            import google.generativeai as genai
                            from ai_helper import _get_google_api_key, _get_gemini_model_name
                            api_key = _get_google_api_key()
                            if api_key:
                                genai.configure(api_key=api_key)
                                events_list = "\n".join([f"ID:{e['id']} | {e.get('data_evento','')} - {e.get('titulo_evento','')}" for e in res.data[:50]])
                                prompt = f"O usuario busca: \"{query}\"\nEventos:\n{events_list}\nRetorne APENAS os IDs separados por virgula. Se nenhum, retorne NENHUM."
                                model = genai.GenerativeModel(_get_gemini_model_name(), system_instruction="Retorne apenas IDs numericos separados por virgula.")
                                ai_resp = model.generate_content(prompt).text.strip()
                                if ai_resp and 'NENHUM' not in ai_resp.upper():
                                    ai_ids = [x.strip().replace('ID:', '') for x in ai_resp.split(',')]
                                    ev_map = {str(e['id']): e for e in res.data}
                                    for aid in ai_ids:
                                        if aid in ev_map:
                                            top.append((ev_map[aid], 0.85))
                        except Exception as ai_err:
                            print(f"[ACERVO] [WARN] Busca IA Telegram: {ai_err}")
                    
                    if not top:
                        await bot.reply_to(message, f"Nenhum evento encontrado para \"{query}\". Tente outros termos.", reply_markup=get_main_menu_keyboard(is_operator))
                        clear_state(chat_id)
                        return
                    
                    # Salvar resultados no estado
                    acervo_map = {str(ev['id']): ev for ev, _ in top}
                    chat_states[chat_id]['acervo_map'] = acervo_map
                    
                    # Construir mensagem e teclado inline
                    from .keyboards import get_acervo_result_keyboard
                    results = [(str(ev['id']), f"{ev.get('data_evento', '')} - {ev.get('titulo_evento', '')}") for ev, sc in top]
                    msg = f"📂 *RESULTADOS DA BUSCA:* \"{query}\"\n\nEncontrados {len(results)} evento(s). Selecione:\n"
                    await bot.reply_to(message, msg, reply_markup=get_acervo_result_keyboard(results), parse_mode='Markdown')
                except Exception as e:
                    await bot.reply_to(message, f"Erro na busca: {e}", reply_markup=get_main_menu_keyboard(is_operator))
                    clear_state(chat_id)
            return

        if action == 'settings':
            if text in ("👥 Pedidos de Acesso", "👥 Cadastros Pendentes", "cadastros pendentes", "pedidos de acesso"):
                clear_state(chat_id)
                user_role = str(profile.get('role', '')).lower() if profile else ''
                if user_role not in ('admin', 'supervisor', 'oficial_gab', 'oficial'):
                    await bot.reply_to(message, "⛔ Apenas Administradores ou Supervisores podem gerenciar solicitações de cadastro.")
                    return
                await listar_cadastros_pendentes(bot, message)
                return
            elif text in ("🔔 Notificações", "notificações"):
                clear_state(chat_id)
                from notifications_manager import get_user_preferences
                u_id = profile.get('id') if profile else None
                u_prefs = get_user_preferences(u_id) if u_id else {}
                await bot.reply_to(
                    message,
                    "🔔 **PREFERÊNCIAS DE NOTIFICAÇÕES**\n\nAjuste suas preferências de recebimento de alertas:",
                    reply_markup=get_notifications_toggle_keyboard(u_prefs),
                    parse_mode='Markdown'
                )
                return
            elif text in ("📸 Cadastro Facial", "cadastro facial"):
                chat_states[chat_id] = {
                    'action': 'cadastro_facial',
                    'step': 'send_selfie',
                    'user': profile
                }
                await bot.reply_to(message, "📸 **CADASTRO FACIAL**\n\nPor favor, envie uma foto nítida do seu rosto no chat para cadastrar a biometria facial.")
                return
            elif text in ("🔍 Buscar Minhas Fotos", "buscar minhas fotos"):
                clear_state(chat_id)
                await bot.reply_to(
                    message,
                    "🔍 **BUSCA DE FOTOS**\n\nRecurso de busca acionado.",
                    reply_markup=get_main_menu_keyboard(is_operator)
                )
                return
            elif text in ("⬅️ Voltar", "voltar"):
                clear_state(chat_id)
                await bot.reply_to(
                    message,
                    "⚓ **Menu Principal — SisGAB**",
                    reply_markup=get_main_menu_keyboard(is_operator),
                    parse_mode='Markdown'
                )
                return

        if action == 'gerenciar_usuarios_pendentes':
            if text == "📜 Ver Histórico Completo de Usuários":
                await mostrar_historico_usuarios_telegram(bot, message)
                return
            elif text in ("⬅️ Voltar", "voltar"):
                clear_state(chat_id)
                await bot.reply_to(
                    message,
                    "⚓ **Menu Principal — SisGAB**",
                    reply_markup=get_main_menu_keyboard(is_operator),
                    parse_mode='Markdown'
                )
                return
            elif text.startswith("👤 #"):
                try:
                    idx_str = text.split("#")[1].split(" ")[0]
                    idx = int(idx_str) - 1
                    requests_list = state.get('requests', [])
                    if 0 <= idx < len(requests_list):
                        req_sel = requests_list[idx]
                        chat_states[chat_id] = {
                            'action': 'selecionar_perfil_usuario',
                            'req_data': req_sel,
                            'user': profile
                        }
                        req_nome = req_sel.get('nome_guerra') or req_sel.get('nome_completo') or req_sel.get('nome') or 'Militar'
                        await bot.reply_to(
                            message,
                            f"⚙️ **SELEÇÃO DE PERFIL PARA: `{req_nome.upper()}`**\n\nEscolha a permissão/papel a ser atribuído no teclado abaixo:",
                            reply_markup=get_roles_selection_keyboard(),
                            parse_mode='Markdown'
                        )
                        return
                except Exception as err_sel:
                    print(f"[USER SEL ERR] {err_sel}")

        if action == 'selecionar_perfil_usuario':
            req_sel = state.get('req_data', {})
            role_map = {
                "👑 1. Administrador (Acesso Total)": "admin",
                "⚖️ 2. Supervisor COMSOC": "supervisor",
                "⚖️ 3. Oficial do Gabinete": "oficial_gab",
                "⚓ 4. Oficial da OM": "oficial",
                "📜 5. Praça do Gabinete": "praca_gab",
                "📸 6. Equipe COMSOC (Fotografia/Vídeo)": "comsoc",
                "🎨 7. Equipe COMSOC (Design/Canva)": "comsoc_design",
                "⚓ 8. Militar / Efetivo em Geral": "militar"
            }

            if text in role_map or any(r_val in text.lower() for r_val in role_map.values()):
                role_selected = role_map.get(text)
                if not role_selected:
                    for label, r_val in role_map.items():
                        if r_val in text.lower() or label in text:
                            role_selected = r_val
                            break
                if not role_selected:
                    role_selected = 'militar'

                req_id = req_sel.get('id', '')
                u_email = req_sel.get('email', '')
                u_guerra = req_sel.get('nome_guerra') or req_sel.get('nome_completo') or req_sel.get('nome') or "Militar"
                u_tg_id = req_sel.get('telegram_id')

                db = get_db_connection()
                if db:
                    for tbl in ['RegistrationRequests', 'registration_requests']:
                        try:
                            db.table(tbl).update({'status': 'approved'}).eq('id', req_id).execute()
                        except Exception:
                            pass
                        if u_email:
                            try:
                                db.table(tbl).update({'status': 'approved'}).eq('email', u_email).execute()
                            except Exception:
                                pass

                    try:
                        db.table('users').update({'role': role_selected}).eq('id', req_id).execute()
                    except Exception:
                        pass
                    if u_email:
                        try:
                            db.table('users').update({'role': role_selected}).eq('email', u_email).execute()
                        except Exception:
                            pass

                    if u_email:
                        try:
                            db.table('efetivo').update({'role': role_selected}).eq('email', u_email).execute()
                        except Exception:
                            pass
                    if u_guerra:
                        try:
                            db.table('efetivo').update({'role': role_selected}).ilike('nome_guerra', u_guerra).execute()
                        except Exception:
                            pass

                clear_state(chat_id)
                await bot.reply_to(
                    message,
                    f"✅ **PERFIL DO OPERADOR `{u_guerra.upper()}` ATUALIZADO!**\n\n⚙️ **Novo Perfil:** `{role_selected.upper()}`",
                    reply_markup=get_main_menu_keyboard(is_operator),
                    parse_mode='Markdown'
                )

                if u_tg_id:
                    try:
                        await bot.send_message(
                            int(u_tg_id),
                            f"🎉 **SEU PERFIL NO SISGAB FOI ATUALIZADO!**\n\nSeu novo papel é: **{role_selected.upper()}**.\nVocê já pode acessar as funcionalidades e menus liberados!",
                            parse_mode='Markdown'
                        )
                    except Exception:
                        pass
                return
            elif text in ("❌ 9. Rejeitar Cadastro", "Rejeitar"):
                req_id = req_sel.get('id', '')
                db = get_db_connection()
                if db:
                    for tbl in ['RegistrationRequests', 'registration_requests']:
                        try:
                            db.table(tbl).update({'status': 'rejected'}).eq('id', req_id).execute()
                        except Exception:
                            pass
                clear_state(chat_id)
                await bot.reply_to(message, "❌ **Solicitação rejeitada.**", reply_markup=get_main_menu_keyboard(is_operator))
                return
            elif text in ("⬅️ Voltar", "voltar"):
                clear_state(chat_id)
                await bot.reply_to(
                    message,
                    "⚓ **Menu Principal — SisGAB**",
                    reply_markup=get_main_menu_keyboard(is_operator),
                    parse_mode='Markdown'
                )
                return

        if action == 'edit_hora_demanda':
            dem_id = state.get('demanda_id')
            novahora = text.strip()
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
            selected_ids = set(str(x) for x in state.get('selected_ids', set()))
            user_name = profile.get('nome_guerra') or profile.get('nome') or 'Operador' if profile else 'Operador'
            user_name = str(user_name).replace('None ', '').replace('None', '').strip().upper()

            # 1. Se o usuário clicou no botão "CONCLUIR SELEÇÃO DA EQUIPE"
            if "CONCLUIR" in text.upper() or "➡️" in text:
                db = get_db_connection()
                if db and dem_id:
                    try:
                        int_ids = [int(x) for x in selected_ids if str(x).isdigit()]
                        db.table('demandas_comunicacao').update({
                            'notificar_militar_ids': json.dumps(int_ids)
                        }).eq('id', dem_id).execute()

                        # Notificar militares escalados
                        escalados_nomes = []
                        for ef in efetivo_list:
                            m_id = str(ef.get('id', ''))
                            if m_id in selected_ids or (m_id.isdigit() and int(m_id) in int_ids):
                                m_nome = f"{ef.get('posto_grad') or ''} {ef.get('nome_guerra', '')}".strip()
                                escalados_nomes.append(m_nome)
                                t_id = ef.get('telegram_id')
                                if t_id:
                                    try:
                                        from notifications_manager import notify_telegram
                                        notify_telegram(
                                            f"🎖️ **VOCÊ FOI ESCALADO PARA UMA MISSÃO!**\n\n"
                                            f"📌 Pauta ID #{dem_id}\n"
                                            f"👨‍✈️ Escalado por: {user_name}",
                                            "system",
                                            custom_chat_id=t_id
                                        )
                                    except Exception as n_err:
                                        print(f"[NOTIFY MILITAR ERR] {n_err}")

                        clear_state(chat_id)
                        equipe_lines = "\n".join([f"   • {n}" for n in escalados_nomes]) if escalados_nomes else "   • Nenhum militar escalado"
                        await bot.reply_to(
                            message,
                            f"✅ **EQUIPE OPERACIONAL HOMOLOGADA COM SUCESSO!**\n\n"
                            f"📌 **Pauta ID:** #{dem_id}\n"
                            f"👨‍✈️ **Equipe Escalada ({len(escalados_nomes)}):**\n{equipe_lines}\n\n"
                            f"Todos os militares vinculados foram notificados.",
                            reply_markup=get_main_menu_keyboard(is_operator),
                            parse_mode='Markdown'
                        )
                    except Exception as e_eq:
                        await bot.reply_to(message, f"❌ Erro ao atribuir equipe: {e_eq}")
                return

            # 2. Alternar seleção do militar clicado
            nome_digitado = text.replace('✅', '').replace('🎖️', '').strip().upper()

            militar_encontrado = None
            for ef in efetivo_list:
                guerra = (ef.get('nome_guerra') or '').strip().upper()
                posto = (ef.get('posto_grad') or '').strip().upper()
                nome_completo = f"{posto} {guerra}".strip().upper()
                if guerra == nome_digitado or nome_completo == nome_digitado or guerra in nome_digitado or (guerra and guerra in nome_digitado):
                    militar_encontrado = ef
                    break

            if militar_encontrado:
                m_id = str(militar_encontrado.get('id', ''))
                if m_id in selected_ids:
                    selected_ids.remove(m_id)
                else:
                    selected_ids.add(m_id)
                
                state['selected_ids'] = selected_ids
                
                # Nomes dos militares selecionados atualmente
                sel_nomes = []
                for ef in efetivo_list:
                    if str(ef.get('id', '')) in selected_ids:
                        sel_nomes.append(f"{ef.get('posto_grad') or ''} {ef.get('nome_guerra', '')}".strip())

                nomes_txt = "\n".join([f"   • {n}" for n in sel_nomes]) if sel_nomes else "   • Nenhum selecionado ainda"
                
                await bot.reply_to(
                    message,
                    f"👤 **ATRIBUIR EQUIPE OPERACIONAL (ID #{dem_id})**\n\n"
                    f"👥 **Militares Selecionados ({len(selected_ids)}):**\n{nomes_txt}\n\n"
                    f"Clique nos botões de resposta rápida para alternar e em **➡️ CONCLUIR SELEÇÃO DA EQUIPE ➡️** ao terminar:",
                    reply_markup=get_efetivo_linking_keyboard(efetivo_list, selected_ids=selected_ids, is_multi=True),
                    parse_mode='Markdown'
                )
            else:
                await bot.reply_to(
                    message,
                    f"⚠️ Militar **'{text}'** não encontrado.\nPor favor, escolha um militar no teclado abaixo:",
                    reply_markup=get_efetivo_linking_keyboard(efetivo_list, selected_ids=selected_ids, is_multi=True)
                )
            return

        if action == 'solicitar_assento_jade':
            step = state.get('step')
            if step == 'select_posto':
                posto_sel = text.replace('⚓', '').replace('🎖️', '').replace('🏛️', '').replace('👤', '').strip()
                state['data']['posto'] = posto_sel
                state['step'] = 'input_nome'
                await bot.reply_to(
                    message,
                    f"✅ **Posto/Cargo selecionado:** *{posto_sel}*\n\n"
                    "Digite agora o **Nome Completo ou Nome de Guerra da Autoridade**:",
                    reply_markup=get_cancel_keyboard(),
                    parse_mode='Markdown'
                )
                return
            elif step == 'input_nome':
                state['data']['nome'] = text.strip().upper()
                state['step'] = 'select_acomp'
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.row(types.KeyboardButton("0 (Sem Acompanhantes)"), types.KeyboardButton("1 Acompanhante"))
                markup.row(types.KeyboardButton("2 Acompanhantes"), types.KeyboardButton("3 Acompanhantes"))
                markup.row(types.KeyboardButton("❌ Cancelar"))
                await bot.reply_to(
                    message,
                    f"👤 **Autoridade:** *{state['data']['nome']}*\n\n"
                    "Selecione a **Quantidade de Acompanhantes / Placas Reservadas** desejada:",
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
                return
            elif step == 'select_acomp':
                num_acomp = 0
                if "1" in text: num_acomp = 1
                elif "2" in text: num_acomp = 2
                elif "3" in text: num_acomp = 3
                
                posto_val = state['data'].get('posto', '')
                nome_val = state['data'].get('nome', '')
                
                db = get_db_connection()
                if db:
                    try:
                        event_id = state.get('event_id')
                        if not event_id:
                            res_ev = db.table('jade_eventos').select('*').order('data_evento', desc=True).limit(1).execute()
                            if not res_ev.data:
                                res_ev = db.table('eventos_assentos').select('*').limit(1).execute()
                            event_id = res_ev.data[0]['id'] if (res_ev and res_ev.data) else 'e1'
                        
                        main_ins = db.table('jade_convidados').insert({
                            'evento_id': event_id,
                            'nome': nome_val,
                            'posto_graduacao': posto_val,
                            'status_confirmacao': 'confirmado',
                            'status_placa': 'pendente',
                            'max_acompanhantes': num_acomp
                        }).execute()

                        main_id = main_ins.data[0]['id'] if (main_ins and main_ins.data) else None
                        
                        for i in range(num_acomp):
                            db.table('jade_convidados').insert({
                                'evento_id': event_id,
                                'nome': f"ACOMP. {nome_val} ({i+1}/{num_acomp})",
                                'posto_graduacao': posto_val,
                                'convidado_principal_id': main_id,
                                'status_confirmacao': 'confirmado',
                                'status_placa': 'pendente'
                            }).execute()
                    except Exception as db_e:
                        print(f"[JADE SOLICITAR ASSENTO ERR] {db_e}")

                del chat_states[chat_id]
                await bot.reply_to(
                    message,
                    f"🎉 **SOLICITAÇÃO DE ASSENTO REGISTRADA COM SUCESSO!**\n\n"
                    f"📌 **Autoridade:** {posto_val} {nome_val}\n"
                    f"👥 **Acompanhantes:** {num_acomp}\n"
                    f" STATUS: *PENDENTE DE CONFECÇÃO NA FILA JADE*\n\n"
                    f"O militar responsável no Estúdio de Impressão foi notificado para revisão e confecção.",
                    reply_markup=get_main_menu_keyboard(is_operator),
                    parse_mode='Markdown'
                )
                return

        if action == 'missao_rapida':
            step = state.get('step')
            if step == 'input_titulo':
                state['titulo'] = text.strip()
                state['step'] = 'select_categoria'
                await bot.reply_to(
                    message,
                    f"⚡ **MISSÃO RÁPIDA:** *{state['titulo']}*\n\n"
                    f"Selecione o **Tipo / Categoria** da demanda nos botões abaixo:",
                    reply_markup=get_categoria_keyboard(),
                    parse_mode='Markdown'
                )
            elif step == 'select_categoria':
                cat_text = text.strip()
                cat_code = 'audiovisual'
                cat_label = '📸 Cobertura Audiovisual'
                
                cat_map = [
                    ('cobertura audiovisual', 'audiovisual', '📸 Cobertura Audiovisual'),
                    ('design / arte visual', 'design_arte', '🎨 Design / Arte Visual'),
                    ('impressos & encadernação', 'impressos_albuns', '📕 Impressos & Encadernação'),
                    ('redação & discursos', 'redacao_textos', '✍️ Redação & Discursos'),
                    ('brindes & lembranças', 'brindes_lembrancas', '🎁 Brindes & Lembranças'),
                    ('suporte logístico', 'suporte_evento', '📦 Suporte Logístico'),
                    ('outra tarefa especial', 'outra_tarefa', '⚡ Outra Tarefa Especial')
                ]
                
                for key, code, lbl in cat_map:
                    if key in cat_text.lower() or code in cat_text.lower():
                        cat_code = code
                        cat_label = lbl
                        break
                        
                state['categoria_code'] = cat_code
                state['categoria_label'] = cat_label
                state['step'] = 'select_militares'

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
                
                await bot.reply_to(
                    message,
                    f"⚡ **MISSÃO RÁPIDA:** *{state['titulo']}*\n"
                    f"🎯 **Categoria:** *{cat_label}*\n\n"
                    f"Selecione o militar escalado no teclado de resposta rápida no rodapé:",
                    reply_markup=get_efetivo_linking_keyboard(sorted_ef),
                    parse_mode='Markdown'
                )
            elif step == 'select_militares':
                user_name = profile.get('nome_guerra') or profile.get('nome') or 'Operador' if profile else 'Operador'
                user_name = str(user_name).replace('None ', '').replace('None', '').strip().upper()
                titulo_m = state.get('titulo', 'Missão Rápida')
                cat_code = state.get('categoria_code', 'audiovisual')
                cat_label = state.get('categoria_label', '📸 Cobertura Audiovisual')
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

                db = get_db_connection()

                if militar_encontrado and db:
                    m_id = militar_encontrado.get('id')
                    m_nome = f"{militar_encontrado.get('posto_grad') or ''} {militar_encontrado.get('nome_guerra', '')}".strip()
                    try:
                        now_str = datetime.now().strftime('%Y-%m-%d')
                        novo_registro = {
                            'titulo_evento': f"⚡ {titulo_m}",
                            'solicitante_nome': user_name,
                            'contato': 'COMSOC / Telegram',
                            'setor': 'COMSOC / GABINETE',
                            'data_evento': now_str,
                            'hora_evento': datetime.now().strftime('%H:%M'),
                            'local_evento': 'Gabinete / COMSOC',
                            'status': 'aprovada',
                            'categoria_demanda': cat_code,
                            'notificar_militar_ids': json.dumps([int(m_id)] if str(m_id).isdigit() else [])
                        }
                        db.table('demandas_comunicacao').insert(novo_registro).execute()
                        
                        from notifications_manager import notify_telegram
                        notify_telegram(
                            f"⚡ **NOVA MISSÃO RÁPIDA REGISTRADA!**\n"
                            f"📌 {titulo_m}\n"
                            f"🎯 Categoria: {cat_label}\n"
                            f"👨‍✈️ Criada por: {user_name}\n"
                            f"👥 Escalado: {m_nome}",
                            "system"
                        )

                        t_id = militar_encontrado.get('telegram_id')
                        if t_id:
                            notify_telegram(f"⚡ **VOCÊ FOI ESCALADO PARA UMA MISSÃO RÁPIDA!**\n📌 {titulo_m}\n🎯 Categoria: {cat_label}\nEscalado por: {user_name}", "system", custom_chat_id=t_id)

                        clear_state(chat_id)
                        await bot.reply_to(
                            message,
                            f"⚡ **MISSÃO RÁPIDA CRIADA E ENVIADA!**\n\n"
                            f"📌 *{escape_markdown(titulo_m)}*\n"
                            f"🎯 Categoria: *{escape_markdown(cat_label)}*\n"
                            f"📅 Data: {now_str}\n"
                            f"👨‍✈️ Militar Escalado: **{escape_markdown(m_nome)}**.",
                            reply_markup=get_main_menu_keyboard(is_operator),
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        clear_state(chat_id)
                        await bot.reply_to(message, f"❌ Erro ao criar missão rápida: {e}", reply_markup=get_main_menu_keyboard(is_operator))
                else:
                    await bot.reply_to(
                        message,
                        f"⚠️ Militar **'{text}'** não encontrado.\nPor favor, escolha um militar no teclado no rodapé:",
                        reply_markup=get_efetivo_linking_keyboard(efetivo_list)
                    )
            return

        if action == 'presenca_diaria':
            step = state.get('step')
            is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador')
            
            if text.upper() in ("❌ CANCELAR", "CANCELAR", "❌"):
                clear_state(chat_id)
                await bot.reply_to(message, "❌ Lançamento de presença cancelado.", reply_markup=get_main_menu_keyboard(is_operator))
                return

            if step == 'choose_sigla':
                sigla_txt = text.upper()
                sigla_code = None
                
                if '(P)' in sigla_txt or sigla_txt == 'P' or 'PRESENTE' in sigla_txt: sigla_code = 'P'
                elif '(MA)' in sigla_txt or sigla_txt == 'MA' or 'MISSÃO ADM' in sigla_txt: sigla_code = 'MA'
                elif '(MT)' in sigla_txt or sigla_txt == 'MT' or 'MAIS TARDE' in sigla_txt: sigla_code = 'MT'
                elif '(FE)' in sigla_txt or sigla_txt == 'FE' or 'FÉRIAS' in sigla_txt or 'FERIAS' in sigla_txt: sigla_code = 'FE'
                elif '(L)' in sigla_txt or sigla_txt == 'L' or 'LICENÇA' in sigla_txt or 'LICENCA' in sigla_txt: sigla_code = 'L'
                elif '(H)' in sigla_txt or sigla_txt == 'H' or 'HOSPITAL' in sigla_txt: sigla_code = 'H'
                elif '(DM)' in sigla_txt or sigla_txt == 'DM' or 'DISPENSA' in sigla_txt: sigla_code = 'DM'
                elif '(S)' in sigla_txt or sigla_txt == 'S' or 'SERVIÇO' in sigla_txt or 'SERVICO' in sigla_txt: sigla_code = 'S'
                elif '(OUTRO)' in sigla_txt or 'OUTRA SITUAÇÃO' in sigla_txt or 'OUTRO' in sigla_txt: sigla_code = 'OUTRO'

                if not sigla_code:
                    await bot.reply_to(
                        message,
                        "⚠️ Não reconheci a sigla ou rotina informada.\n"
                        "Por favor, selecione uma das opções de presença no teclado abaixo:",
                        reply_markup=get_presenca_keyboard()
                    )
                    return
                
                state['data']['status'] = sigla_code
                
                if sigla_code in ('MA', 'MT', 'H', 'OUTRO'):
                    state['step'] = 'input_obs'
                    prompts = {
                        'MA': "✍️ Por favor, digite o motivo/local da **Missão Administrativa (MA)**:",
                        'MT': "✍️ Por favor, digite o horário previsto de chegada ou motivo para **(MT) Mais Tarde**:",
                        'H': "✍️ Por favor, digite o hospital ou motivo para **(H) Hospital**:",
                        'OUTRO': "✍️ Por favor, descreva a sua situação/rotina de hoje:"
                    }
                    await bot.reply_to(
                        message,
                        prompts.get(sigla_code, f"✍️ Por favor, digite a observação para **({sigla_code})**:"),
                        reply_markup=get_cancel_keyboard(),
                        parse_mode='Markdown'
                    )
                elif sigla_code in ('FE', 'L', 'DM'):
                    state['step'] = 'input_data_fim'
                    await bot.reply_to(
                        message,
                        f"🏖️ Por favor, informe a **data de término** das suas férias/licença\n"
                        f"(ex: `20/08`, `20/08/2026` ou número de dias ex: `10`):",
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

            elif step == 'input_data_fim':
                sigla_code = state['data'].get('status', 'FE')
                from .utils import _salvar_presenca_bot, parse_date_or_days
                dt_fim_iso, dt_fim_br = parse_date_or_days(text)
                await _salvar_presenca_bot(
                    bot, message, chat_id, state, sigla_code, 
                    f"Término: {dt_fim_br}" if dt_fim_br else "", 
                    data_fim=dt_fim_iso
                )
            return

        if action == 'vincular_efetivo':
            if step == 'select_militar':
                nome_sel = text.replace('🎖️', '').strip().upper()
                db = get_db_connection()
                if db:
                    try:
                        # Define status_aprovacao como 'pendente' até deliberação do Admin
                        db.table('efetivo').update({
                            'telegram_id': str(chat_id),
                            'status_aprovacao': 'pendente'
                        }).eq('nome_guerra', nome_sel).execute()
                        
                        from .utils import notify_telegram_admin
                        await notify_telegram_admin(
                            f"🔔 *NOVO PEDIDO DE VINCULAÇÃO TELEGRAM*\n\n"
                            f"Militar: *{nome_sel}*\n"
                            f"Telegram ID: `{chat_id}`\n"
                            f"Usuário: @{message.from_user.username or 'N/A'}\n\n"
                            f"Acesse o painel web ou digite /aprovar no Telegram para deliberar."
                        )
                        
                        await bot.reply_to(
                            message,
                            f"⏳ **SOLICITAÇÃO DE VINCULAÇÃO REGISTRADA!**\n\n"
                            f"Sua solicitação para vincular ao militar *{nome_sel}* (ID: `{chat_id}`) foi enviada para validação dos Administradores do Gabinete.\n\n"
                            f"Você receberá uma notificação assim que o seu acesso for aprovado.",
                            reply_markup=get_unauthorized_keyboard(),
                            parse_mode='Markdown'
                        )
                    except Exception as e_vinc:
                        await bot.reply_to(message, f"❌ Erro ao solicitar vinculação: {e_vinc}", reply_markup=get_unauthorized_keyboard())
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
                    
                    equipe_val = dados.get('equipe_escalada') or dados.get('fotografo') or ''
                    data_fim_val = dados.get('data_fim') or None
                    tipos_cob = dados.get('tipo_cobertura')
                    if isinstance(tipos_cob, list):
                        tipos_cob_json = json.dumps(tipos_cob)
                    else:
                        tipos_cob_json = '["foto"]'

                    registro = {
                        'solicitante_nome': dados.get('solicitante_nome', 'N/I').upper(),
                        'setor': dados.get('setor', 'Gabinete').upper(),
                        'contato': dados.get('contato', 'N/I'),
                        'titulo_evento': dados.get('titulo_evento', 'Evento Sem Título').upper(),
                        'data_evento': dados.get('data_evento', datetime.now().strftime('%Y-%m-%d')),
                        'data_fim': data_fim_val,
                        'hora_evento': dados.get('hora_evento', '09:00'),
                        'local_evento': dados.get('local_evento', 'Gabinete').upper(),
                        'tipo_cobertura': tipos_cob_json,
                        'autoridades': dados.get('autoridades', ''),
                        'score_esforco': 2.0,
                        'status': 'pendente',
                        'notificar_militar_ids': equipe_val.upper() if equipe_val else None
                    }
                    
                    state['parsed_registro'] = registro
                    state['step'] = 'confirm_ia_save'

                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton("✅ Confirmar & Incluir", callback_data="confirm_ia_demanda:yes"),
                        types.InlineKeyboardButton("❌ Cancelar", callback_data="confirm_ia_demanda:cancel")
                    )

                    periodo_txt = f" a {data_fim_val}" if data_fim_val and data_fim_val != registro['data_evento'] else ""
                    equipe_txt = f"📸 **Equipe/Fotógrafo:** {equipe_val.upper()}\n" if equipe_val else ""
                    aut_txt = f"🎖️ **Autoridades:** {registro['autoridades']}\n" if registro['autoridades'] and registro['autoridades'] != 'Nenhuma' else ""

                    confirm_msg = (
                        "🤖 **PRÉ-VISUALIZAÇÃO DA PAUTA EXTRAÍDA PELA IA**\n\n"
                        f"📌 **Evento:** {registro['titulo_evento']}\n"
                        f"📅 **Data:** {registro['data_evento']}{periodo_txt} às {registro['hora_evento']}\n"
                        f"📍 **Local:** {registro['local_evento']}\n"
                        f"👤 **Solicitante:** {registro['solicitante_nome']}\n"
                        f"{aut_txt}"
                        f"{equipe_txt}\n"
                        "⚠️ *Confirma os dados acima para salvar e incluir na agenda?*"
                    )
                    await bot.reply_to(message, confirm_msg, reply_markup=markup, parse_mode='Markdown')
                except Exception as e:
                    await bot.reply_to(message, f"❌ Erro ao digerir questionário: {e}\nPor favor, tente enviar novamente ou criar manualmente.", reply_markup=get_main_menu_keyboard(is_operator))
                    clear_state(chat_id)
            return

        # ----- WIZARD: Criar Demanda (Interativo com Botões em todas as Etapas) -----
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
                if 'ASD' in date_txt.upper() or 'DEFINIR' in date_txt.upper():
                    clean_dt = 'ASD'
                else:
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
                if "VOLTAR" in text.upper() or text in ["⬅️ Voltar", "voltar"]:
                    state['step'] = 'autoridades'
                    from .keyboards import get_authorities_keyboard
                    await bot.reply_to(message, "[Passo 8/9] 👑 Quais **Autoridades** estarão presentes?", reply_markup=get_authorities_keyboard(), parse_mode='Markdown')
                    return
                elif "Fotográfica" in text:
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
                    db = get_db_connection()
                    if db:
                        try:
                            d = state['data']
                            aut_val = str(d.get('autoridades', '') or '').strip()
                            obs_val = str(d.get('observacoes', '') or '').strip()
                            if obs_val and obs_val.lower() != "nenhuma":
                                if aut_val and aut_val.lower() != "nenhuma autoridade especial":
                                    aut_final = f"{aut_val} | Obs: {obs_val}"
                                else:
                                    aut_final = f"Obs: {obs_val}"
                            else:
                                aut_final = aut_val

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
                                'autoridades': aut_final,
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
                    await bot.reply_to(message, "✏️ **Formulação Reiniciada**\n\n[Passo 1/9] ⚓ A solicitação é do **CGCFN** ou de **Outra OM**?", reply_markup=get_om_keyboard(), parse_mode='Markdown')
                else:
                    await bot.reply_to(message, "Selecione uma das opções nos botões abaixo:", reply_markup=get_confirm_demanda_keyboard())
            return

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('solicitar_assento_jade', 'jade_escolher_evento', 'jade_ev_sel:', 'jade_extra_acomp', 'jade_refresh_queue', 'jade_cancel')))
    async def handle_jade_menu_callbacks(call):
        chat_id = call.message.chat.id if call.message else call.from_user.id
        data = call.data

        try:
            await bot.answer_callback_query(call.id)
        except Exception:
            pass

        db = get_db_connection()

        if data == 'jade_refresh_queue':
            if db:
                res_j = db.table('jade_convidados').select('*').eq('status_placa', 'pendente').execute()
                pendentes = res_j.data if res_j.data else []
                res_prod = db.table('jade_convidados').select('*').eq('status_placa', 'em_producao').execute()
                em_producao = res_prod.data if res_prod.data else []
                res_imp = db.table('jade_convidados').select('*').eq('status_placa', 'impressa').execute()
                impressas = res_imp.data if res_imp.data else []

                msg_jade = (
                    f"🪑 **FILA DE PRODUÇÃO DE PLACAS JADE (ATUALIZADA)**\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"🟡 **Pendentes:** {len(pendentes)} placa(s)\n"
                    f"🔵 **Em Produção:** {len(em_producao)} placa(s)\n"
                    f"🟢 **Já Impressas:** {len(impressas)} placa(s)\n\n"
                )
                if pendentes:
                    msg_jade += "📌 **PRÓXIMAS PLACAS A CONFECCIONAR:**\n"
                    for idx, p in enumerate(pendentes[:10], 1):
                        msg_jade += f"{idx}. *{p.get('posto_graduacao','') or ''} {p.get('nome','N/I')}* — _{p.get('cargo_funcao','') or ''}_\n"
                else:
                    msg_jade += "🎉 *Nenhuma placa pendente no momento!*\n"

                msg_jade += "\n━━━━━━━━━━━━━━━━━━"
                await bot.send_message(chat_id, msg_jade, reply_markup=get_jade_menu_inline_keyboard(), parse_mode='Markdown')
            return

        elif data == 'jade_escolher_evento':
            if db:
                res_ev = db.table('jade_eventos').select('*').order('data_evento', desc=True).limit(8).execute()
                events_list = res_ev.data if res_ev and res_ev.data else []
                if not events_list:
                    res_ev = db.table('eventos_assentos').select('*').limit(8).execute()
                    events_list = res_ev.data if res_ev and res_ev.data else []

                if events_list:
                    await bot.send_message(
                        chat_id,
                        "🏛️ **SELECIONE A SOLENIDADE / EVENTO:**\n"
                        "Escolha para qual solenidade você deseja cadastrar ou gerenciar as placas JADE:",
                        reply_markup=get_jade_events_inline_keyboard(events_list),
                        parse_mode='Markdown'
                    )
                else:
                    await bot.send_message(chat_id, "⚠️ Nenhuma solenidade cadastrada no momento. Crie o evento no painel web primeiro.")
            return

        elif data.startswith('jade_ev_sel:'):
            ev_id = data.split(':')[1]
            chat_states[chat_id] = {
                'action': 'solicitar_assento_jade',
                'step': 'select_posto',
                'event_id': ev_id,
                'data': {}
            }
            await bot.send_message(
                chat_id,
                "✅ **Solenidade selecionada!**\n\n"
                "Selecione o **Posto/Graduação ou Cargo da Autoridade** no menu abaixo:",
                reply_markup=get_gabarito_postos_keyboard(),
                parse_mode='Markdown'
            )
            return

        elif data == 'solicitar_assento_jade':
            chat_states[chat_id] = {
                'action': 'solicitar_assento_jade',
                'step': 'select_posto',
                'data': {}
            }
            await bot.send_message(
                chat_id,
                "🪑 **SOLICITAÇÃO DE ASSENTO JADE**\n\n"
                "Selecione o **Posto/Graduação ou Cargo da Autoridade** no teclado abaixo:",
                reply_markup=get_gabarito_postos_keyboard(),
                parse_mode='Markdown'
            )
            return

        elif data == 'jade_extra_acomp':
            chat_states[chat_id] = {
                'action': 'solicitar_assento_jade',
                'step': 'input_nome',
                'data': {'posto': 'RESERVADO (Extra)'}
            }
            await bot.send_message(
                chat_id,
                "➕ **PLACA EXTRA DE ACOMPANHANTE**\n\n"
                "Digite o **Nome da Autoridade Principal ou Acompanhante** para quem deseja a placa extra:",
                reply_markup=get_cancel_keyboard(),
                parse_mode='Markdown'
            )
            return

        elif data == 'jade_cancel':
            if chat_id in chat_states:
                del chat_states[chat_id]
            await bot.send_message(chat_id, "❌ Operação cancelada.", reply_markup=get_main_menu_keyboard())
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
                obs = d.get('observacoes') or (d.get('autoridades') if 'Obs:' in str(d.get('autoridades')) else '') or 'Nenhuma'
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


    @bot.message_handler(content_types=['photo'], func=lambda m: m.chat.id in chat_states and chat_states[m.chat.id].get('action') == 'cadastro_facial')
    async def handle_photo_messages(message):
        import os
        chat_id = message.chat.id
        state = chat_states.get(chat_id, {})
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
                    'autoridades': f"Obs: Transcrição de áudio: {transcricao}"
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

    @bot.message_handler(content_types=['photo', 'document'], func=lambda m: m.chat.id in chat_states and chat_states[m.chat.id].get('action') == 'waiting_selfie_registration')
    async def handle_selfie_registration(message):
        chat_id = message.chat.id
        state = chat_states[chat_id]
        profile = state.get('user')
        
        await bot.reply_to(message, "⏳ Processando sua selfie, aguarde...")
        
        try:
            file_info = None
            if message.content_type == 'photo':
                file_info = await bot.get_file(message.photo[-1].file_id)
            elif message.content_type == 'document':
                if not message.document.mime_type.startswith('image/'):
                    await bot.reply_to(message, "❌ Por favor, envie um arquivo de imagem.")
                    return
                file_info = await bot.get_file(message.document.file_id)
                
            file_bytes = await bot.download_file(file_info.file_path)
            
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from sisgab_face_worker import evaluate_selfie_quality
            
            success, msg, embedding = evaluate_selfie_quality(file_bytes)
            
            if not success:
                await bot.reply_to(message, msg)
                return
                
            from database import get_bot_db_connection
            db = get_bot_db_connection()
            if not db:
                await bot.reply_to(message, "❌ Erro ao conectar ao banco de dados.")
                return
                
            user_id = profile.get('id')
            nome_guerra = profile.get('nome_guerra') or profile.get('nome') or 'Militar'
            
            import json
            payload = {
                'user_id': user_id,
                'telegram_id': str(chat_id),
                'nome_guerra': nome_guerra,
                'embedding': json.dumps(embedding.tolist())
            }
            db.table('face_embeddings').upsert(payload).execute()
            await bot.reply_to(message, "✅ *Biometria Facial Cadastrada com Sucesso!*\nAgora você receberá notificações automáticas quando aparecer em fotos de eventos.", parse_mode='Markdown')
            clear_state(chat_id)
        except Exception as e:
            await bot.reply_to(message, f"❌ Erro ao salvar biometria: {e}")
