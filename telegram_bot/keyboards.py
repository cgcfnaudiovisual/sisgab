from telebot import types
from .utils import current_user_id, USER_PERMISSIONS_CACHE

def get_unauthorized_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("🔗 Vincular Meu Nome"), types.KeyboardButton("📝 Solicitar Acesso"))
    return markup

def get_om_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⚓ CGCFN (Gabinete / ComSOC)"), types.KeyboardButton("🏢 Outra OM / Organização Militar"))
    markup.row(types.KeyboardButton("❌ Cancelar"))
    return markup

def get_categoria_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("📸 Cobertura Audiovisual"), types.KeyboardButton("🎨 Design / Arte Visual"))
    markup.row(types.KeyboardButton("📕 Impressos & Encadernação"), types.KeyboardButton("✍️ Redação & Discursos"))
    markup.row(types.KeyboardButton("🎁 Brindes & Lembranças"), types.KeyboardButton("📦 Suporte Logístico"))
    markup.row(types.KeyboardButton("⚡ Outra Tarefa Especial"), types.KeyboardButton("❌ Cancelar"))
    return markup




def get_gabarito_postos_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    markup.row(types.KeyboardButton("⚓ AE - Almirante de Esquadra"), types.KeyboardButton("⚓ VA - Vice-Almirante"))
    markup.row(types.KeyboardButton("⚓ CA - Contra-Almirante"), types.KeyboardButton("🎖️ CMG - Capitão de Mar e Guerra"))
    markup.row(types.KeyboardButton("🎖️ CF - Capitão de Fragata"), types.KeyboardButton("🎖️ CC - Capitão de Corveta"))
    markup.row(types.KeyboardButton("🎖️ CT - Capitão-Tenente"), types.KeyboardButton("🏛️ Desembargador(a)"))
    markup.row(types.KeyboardButton("🏛️ Senador(a) / Deputado(a)"), types.KeyboardButton("🏛️ Juiz(a) de Direito"))
    markup.row(types.KeyboardButton("👤 Senhor / Senhora"), types.KeyboardButton("❌ Cancelar"))
    return markup


def get_demanda_summary_inline_keyboard(demanda_id):
    """Gera teclado inline resumido (apenas 1 botão para abrir o menu da demanda)."""
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("⚙️ Gerenciar / Opções da Demanda", callback_data=f"opcoes_dem:{demanda_id}")
    )
    return markup


def get_manage_demanda_inline_keyboard(demanda_id, status='aprovada'):
    """Gera teclado inline contextual completo baseado no status da demanda."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    st = str(status).lower().strip()

    # Botão de detalhes sempre visível
    markup.row(
        types.InlineKeyboardButton("🔎 Ver Detalhes Completos", callback_data=f"detalhe_dem:{demanda_id}")
    )

    if st in ('pendente', 'em_ajuste', 'ajustes'):
        # Pendente: pode aprovar, rejeitar, editar
        markup.row(
            types.InlineKeyboardButton("✅ Aprovar Pauta", callback_data=f"aprovar_dem:{demanda_id}"),
            types.InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_dem:{demanda_id}")
        )
        markup.row(
            types.InlineKeyboardButton("✏️ Editar Horário", callback_data=f"edithora_dem:{demanda_id}"),
            types.InlineKeyboardButton("✏️ Editar Local", callback_data=f"editlocal_dem:{demanda_id}")
        )
        markup.row(
            types.InlineKeyboardButton("👤 Atribuir Equipe", callback_data=f"equipe_dem:{demanda_id}")
        )
    elif st in ('aprovada', 'aprovado'):
        # Aprovada: pode concluir, atribuir equipe, editar, rejeitar
        markup.row(
            types.InlineKeyboardButton("🎯 Concluir Missão", callback_data=f"concluir_dem:{demanda_id}"),
            types.InlineKeyboardButton("👤 Atribuir Equipe", callback_data=f"equipe_dem:{demanda_id}")
        )
        markup.row(
            types.InlineKeyboardButton("✏️ Editar Horário", callback_data=f"edithora_dem:{demanda_id}"),
            types.InlineKeyboardButton("✏️ Editar Local", callback_data=f"editlocal_dem:{demanda_id}")
        )
        markup.row(
            types.InlineKeyboardButton("✏️ Editar Título", callback_data=f"edittitulo_dem:{demanda_id}"),
            types.InlineKeyboardButton("❌ Rejeitar / Cancelar", callback_data=f"rejeitar_dem:{demanda_id}")
        )
    elif st in ('concluida', 'concluído', 'concluido'):
        # Concluída
        markup.row(
            types.InlineKeyboardButton("🔄 Reabrir Pauta", callback_data=f"reabrir_dem:{demanda_id}")
        )
    else:
        # Fallback
        markup.row(
            types.InlineKeyboardButton("🎯 Concluir", callback_data=f"concluir_dem:{demanda_id}"),
            types.InlineKeyboardButton("👤 Atribuir Equipe", callback_data=f"equipe_dem:{demanda_id}")
        )

    # Botão para recolher o menu de opções
    markup.row(
        types.InlineKeyboardButton("⬅️ Ocultar Opções", callback_data=f"fechar_opcoes_dem:{demanda_id}")
    )

    return markup



def get_multi_militar_inline_keyboard(efetivo_list, selected_ids=None, prefix="sel_mil"):
    if selected_ids is None:
        selected_ids = set()
    from .utils import sort_efetivo_by_rank
    sorted_ef = sort_efetivo_by_rank(efetivo_list)
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ef in sorted_ef:
        ef_id = str(ef.get('id', ''))
        nome = f"{ef.get('posto_grad') or ''} {ef.get('nome_guerra', '')}".strip()
        is_sel = str(ef_id) in [str(x) for x in selected_ids]
        icon = "✅" if is_sel else "⬜"
        markup.add(types.InlineKeyboardButton(text=f"{icon} {nome}", callback_data=f"{prefix}:{ef_id}"))
        
    cnt = len(selected_ids)
    markup.add(types.InlineKeyboardButton(text=f"➡️ CONFIRMAR ({cnt} SELECIONADOS) ➡️", callback_data=f"{prefix}:done"))
    return markup

def get_efetivo_linking_keyboard(efetivo_lista, selected_ids=None, is_multi=False):
    from .utils import sort_efetivo_by_rank
    sorted_ef = sort_efetivo_by_rank(efetivo_lista)
    selected_set = set(str(x) for x in (selected_ids or []))
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_multi:
        cnt = len(selected_set)
        markup.row(types.KeyboardButton(f"➡️ CONCLUIR SELEÇÃO DA EQUIPE ({cnt}) ➡️"))
        
    row = []
    for ef in sorted_ef:
        m_id = str(ef.get('id', ''))
        nome_g = ef.get('nome_guerra') or ef.get('nome') or 'MILITAR'
        pg = ef.get('posto_grad') or ''
        base_label = f"🎖️ {pg} {nome_g}".strip() if pg else f"🎖️ {nome_g}"
        
        if is_multi and m_id in selected_set:
            label = f"✅ {base_label}"
        else:
            label = base_label
            
        row.append(types.KeyboardButton(label))
        if len(row) == 2:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    markup.row(types.KeyboardButton("❌ Cancelar"))
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_settings_keyboard(is_authorized=True, is_admin=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_authorized:
        markup.row(types.KeyboardButton("📸 Cadastro Facial"), types.KeyboardButton("🔍 Buscar Minhas Fotos"))
        if is_admin:
            markup.row(types.KeyboardButton("🔔 Notificações"), types.KeyboardButton("👥 Pedidos de Acesso"))
        else:
            markup.row(types.KeyboardButton("🔔 Notificações"))
        markup.row(types.KeyboardButton("⬅️ Voltar"))
    else:
        markup.row(types.KeyboardButton("📝 Solicitar Acesso"), types.KeyboardButton("⬅️ Voltar"))
    return markup

def get_notifications_toggle_keyboard(user_prefs):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    
    st_silence = "🔴 SIM" if user_prefs.get("silence_all", False) else "🟢 NÃO"
    st_aviso = "🟢 ATIVADO" if user_prefs.get("notify_aviso", True) else "🔴 MUTADO"
    st_new_user = "🟢 ATIVADO" if user_prefs.get("notify_new_user", True) else "🔴 MUTADO"
    
    markup.row(types.KeyboardButton(f"📢 Letreiro/Avisos: {st_aviso}"))
    markup.row(types.KeyboardButton(f"👥 Novos Acessos: {st_new_user}"), types.KeyboardButton(f"🔇 Silenciar Tudo: {st_silence}"))
    markup.row(types.KeyboardButton("⬅️ Voltar"))
    return markup

def get_roles_selection_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True, row_width=2)
    markup.row(types.KeyboardButton("👑 1. Administrador (Acesso Total)"), types.KeyboardButton("⚖️ 2. Supervisor COMSOC"))
    markup.row(types.KeyboardButton("⚖️ 3. Oficial do Gabinete"), types.KeyboardButton("⚓ 4. Oficial da OM"))
    markup.row(types.KeyboardButton("📜 5. Praça do Gabinete"), types.KeyboardButton("📸 6. Equipe COMSOC (Fotografia/Vídeo)"))
    markup.row(types.KeyboardButton("🎨 7. Equipe COMSOC (Design/Canva)"), types.KeyboardButton("⚓ 8. Militar / Efetivo em Geral"))
    markup.row(types.KeyboardButton("❌ 9. Rejeitar Cadastro"), types.KeyboardButton("⬅️ Voltar"))
    return markup

def get_aviso_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("📢 Novo Aviso"), types.KeyboardButton("📋 Listar Existentes"))
    markup.row(types.KeyboardButton("✏️ Editar Aviso"), types.KeyboardButton("❌ Remover/Excluir"))
    markup.row(types.KeyboardButton("🔒 Enviar Aviso Privado"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_duration_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("1"), types.KeyboardButton("2"), types.KeyboardButton("3"))
    markup.row(types.KeyboardButton("5"), types.KeyboardButton("7"), types.KeyboardButton("10"))
    markup.row(types.KeyboardButton("15"), types.KeyboardButton("30"))
    return markup

def get_date_keyboard(is_end_date=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    from datetime import datetime, timedelta
    now = datetime.now()
    d0 = now.strftime('%d/%m/%Y')
    d1 = (now + timedelta(days=1)).strftime('%d/%m/%Y')
    d2 = (now + timedelta(days=2)).strftime('%d/%m/%Y')
    d3 = (now + timedelta(days=3)).strftime('%d/%m/%Y')
    d7 = (now + timedelta(days=7)).strftime('%d/%m/%Y')

    if is_end_date:
        markup.row(types.KeyboardButton("📌 Mesmo Dia (Sem Término)"))
        markup.row(types.KeyboardButton(f"📅 +1 Dia ({d1[:5]})"), types.KeyboardButton(f"📅 +2 Dias ({d2[:5]})"))
        markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    else:
        markup.row(types.KeyboardButton(f"📅 Hoje ({d0[:5]})"), types.KeyboardButton(f"📅 Amanhã ({d1[:5]})"))
        markup.row(types.KeyboardButton(f"📅 Em 3 Dias ({d3[:5]})"), types.KeyboardButton(f"📅 Em 1 Semana ({d7[:5]})"))
        markup.row(types.KeyboardButton("📅 Data a Definir (ASD)"))
        markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_time_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⏰ 08:00"), types.KeyboardButton("⏰ 08:30"), types.KeyboardButton("⏰ 09:00"))
    markup.row(types.KeyboardButton("⏰ 10:00"), types.KeyboardButton("⏰ 13:30"), types.KeyboardButton("⏰ 14:00"))
    markup.row(types.KeyboardButton("⏰ 15:00"), types.KeyboardButton("⏰ 16:00"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_uniform_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("👔 3.3 (Instalação / Comum)"), types.KeyboardButton("👔 4.4 (Operacional / Camuflado)"))
    markup.row(types.KeyboardButton("👔 3.1 (Passeio / Branco)"), types.KeyboardButton("👔 1.1 (Gala / Cerimonial)"))
    markup.row(types.KeyboardButton("👕 Paisano / Esporte"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_authorities_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("👑 Comandante do CGCFN"), types.KeyboardButton("👑 Almirantes / Generais"))
    markup.row(types.KeyboardButton("👑 Nenhuma Autoridade Especial"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_observations_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("⏭️ Pular / Nenhuma Observação"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_demandas_list_reply_keyboard(demandas_list):
    """Gera teclado de resposta rápida no rodapé para selecionar qual demanda gerenciar por data e título."""
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    row = []
    for d in demandas_list:
        d_id = d.get('id')
        dt_raw = d.get('data_evento', '')
        dt_short = ""
        try:
            parts = str(dt_raw).split('T')[0].split(' ')[0].split('-')
            if len(parts) == 3:
                dt_short = f"{parts[2]}/{parts[1]}"
        except Exception:
            pass
        
        dt_prefix = f"({dt_short}) " if dt_short else ""
        tit = (d.get('titulo_evento') or 'Pauta')[:15]
        btn_label = f"⚙️ #{d_id} — {dt_prefix}{tit}".strip()
        row.append(types.KeyboardButton(btn_label))
        if len(row) == 2:
            markup.row(*row)
            row = []
    if row:
        markup.row(*row)
    markup.row(types.KeyboardButton("⬅️ Voltar ao Menu Principal"))
    return markup


def get_main_menu_keyboard(is_operator=False):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    if is_operator:
        markup.row(types.KeyboardButton("🟢 Dar Presença"), types.KeyboardButton("📋 Pronto CheGab"))
        markup.row(types.KeyboardButton("📸 Enviar Fotos / Drive"), types.KeyboardButton("🙋 Minhas Fotos (IA)"))
        markup.row(types.KeyboardButton("📂 Buscar Acervo"), types.KeyboardButton("⚡ Missão Rápida"))
        markup.row(types.KeyboardButton("📋 Gerenciar Demandas"), types.KeyboardButton("📊 Relatório Executivo"))
        markup.row(types.KeyboardButton("👥 Cadastros Pendentes"), types.KeyboardButton("📅 Agenda Semanal"))
        markup.row(types.KeyboardButton("➕ Criar Demanda"), types.KeyboardButton("🤖 Digerir Pauta (IA)"))
        markup.row(types.KeyboardButton("🪑 Placas JADE"), types.KeyboardButton("🔌 Cautelas Ativas"))
        markup.row(types.KeyboardButton("⚙️ Configurações"), types.KeyboardButton("❌ Cancelar"))
    else:
        markup.row(types.KeyboardButton("🟢 Dar Presença"), types.KeyboardButton("📸 Enviar Fotos / Drive"))
        markup.row(types.KeyboardButton("🙋 Minhas Fotos (IA)"), types.KeyboardButton("📂 Buscar Acervo"))
        markup.row(types.KeyboardButton("📅 Agenda Semanal"), types.KeyboardButton("➕ Criar Demanda"))
        markup.row(types.KeyboardButton("⚡ Missão Rápida"), types.KeyboardButton("⚙️ Configurações"))
        markup.row(types.KeyboardButton("ℹ️ Ajuda"), types.KeyboardButton("❌ Cancelar"))
    return markup


def get_confirm_ciente_inline_keyboard(demanda_id):
    """Gera botão inline para o militar escalado confirmar ciente no Telegram."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👍 Confirmar Ciente da Missão", callback_data=f"confirm_ciente:{demanda_id}"))
    return markup


def get_demanda_actions_inline_keyboard(demanda_id, status='aprovada'):
    """Gera botões Inline interativos para gerenciar a pauta diretamente na mensagem."""
    markup = types.InlineKeyboardMarkup()
    st = str(status).lower().strip()

    row1 = [
        types.InlineKeyboardButton("🔎 Detalhes", callback_data=f"det_dem:{demanda_id}"),
        types.InlineKeyboardButton("👤 Equipe", callback_data=f"equipe_dem:{demanda_id}")
    ]
    markup.row(*row1)

    if st in ('pendente', 'em_ajuste', 'ajustes'):
        row2 = [
            types.InlineKeyboardButton("✅ Aprovar", callback_data=f"appr_dem:{demanda_id}"),
            types.InlineKeyboardButton("❌ Rejeitar", callback_data=f"rej_dem:{demanda_id}")
        ]
        markup.row(*row2)
    elif st in ('aprovada', 'aprovado'):
        row2 = [
            types.InlineKeyboardButton("🎯 Concluir Missão", callback_data=f"conc_dem:{demanda_id}"),
            types.InlineKeyboardButton("❌ Rejeitar", callback_data=f"rej_dem:{demanda_id}")
        ]
        markup.row(*row2)
    elif st in ('concluida', 'concluído', 'concluido'):
        markup.row(types.InlineKeyboardButton("🔄 Reabrir Pauta", callback_data=f"reopen_dem:{demanda_id}"))

    return markup


def get_demanda_actions_reply_keyboard(demanda_id, status='aprovada'):
    """Gera teclado de resposta rápida no rodapé para gerenciar uma demanda específica."""
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    st = str(status).lower().strip()

    markup.row(types.KeyboardButton(f"🔎 Detalhes #{demanda_id}"), types.KeyboardButton(f"👤 Equipe #{demanda_id}"))

    if st in ('pendente', 'em_ajuste', 'ajustes'):
        markup.row(types.KeyboardButton(f"✅ Aprovar #{demanda_id}"), types.KeyboardButton(f"❌ Rejeitar #{demanda_id}"))
        markup.row(types.KeyboardButton(f"✏️ Editar Horário #{demanda_id}"), types.KeyboardButton(f"✏️ Editar Local #{demanda_id}"))
    elif st in ('aprovada', 'aprovado'):
        markup.row(types.KeyboardButton(f"🎯 Concluir Missão #{demanda_id}"), types.KeyboardButton(f"❌ Rejeitar #{demanda_id}"))
        markup.row(types.KeyboardButton(f"✏️ Editar Horário #{demanda_id}"), types.KeyboardButton(f"✏️ Editar Local #{demanda_id}"))
        markup.row(types.KeyboardButton(f"✏️ Editar Título #{demanda_id}"))
    elif st in ('concluida', 'concluído', 'concluido'):
        markup.row(types.KeyboardButton(f"🔄 Reabrir Pauta #{demanda_id}"))
    else:
        markup.row(types.KeyboardButton(f"🎯 Concluir Missão #{demanda_id}"), types.KeyboardButton(f"👤 Equipe #{demanda_id}"))

    markup.row(types.KeyboardButton("📋 Voltar para Lista de Demandas"), types.KeyboardButton("⬅️ Voltar ao Menu Principal"))
    return markup


def get_multi_service_reply_keyboard(selected_services=None):
    if selected_services is None:
        selected_services = set()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    
    services = [
        ("foto", "📸 Cobertura Fotográfica"),
        ("video", "🎥 Cobertura em Vídeo"),
        ("grafico", "🎨 Serviço Gráfico"),
        ("drone", "🚁 Imagens Aéreas / Drone"),
        ("redes", "📱 Mídias Sociais / Reels")
    ]
    
    for code, label in services:
        is_sel = code in selected_services
        icon = "✅" if is_sel else "☑️"
        markup.row(types.KeyboardButton(f"{label} {icon}"))
        
    cnt = len(selected_services)
    markup.row(types.KeyboardButton(f"➡️ CONCLUIR SELEÇÃO DOS SERVIÇOS ({cnt}) ➡️"))
    markup.row(types.KeyboardButton("📦 Selecionar Todos os Serviços"))
    markup.row(types.KeyboardButton("⬅️ Voltar"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_confirm_demanda_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("✅ Confirmar & Enviar Pauta"))
    markup.row(types.KeyboardButton("✏️ Reiniciar Formulação"), types.KeyboardButton("❌ Cancelar"))
    return markup

def get_presenca_keyboard():
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row(types.KeyboardButton("🟢 (P) Presente"), types.KeyboardButton("💼 (MA) Missão Adm"))
    markup.row(types.KeyboardButton("🕒 (MT) Mais Tarde"), types.KeyboardButton("🏖️ (FE) Férias"))
    markup.row(types.KeyboardButton("📜 (L) Licença"), types.KeyboardButton("🏥 (H) Hospital"))
    markup.row(types.KeyboardButton("💊 (DM) Disp. Médica"), types.KeyboardButton("🛡️ (S) Serviço"))
    markup.row(types.KeyboardButton("✏️ (OUTRO) Outra Situação"), types.KeyboardButton("❌ Cancelar"))
    return markup


def get_jade_menu_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.row(
        types.InlineKeyboardButton("➕ Solicitar Nova Placa JADE", callback_data="solicitar_assento_jade")
    )
    markup.row(
        types.InlineKeyboardButton("📅 Escolher Solenidade / Evento Específico", callback_data="jade_escolher_evento")
    )
    markup.row(
        types.InlineKeyboardButton("➕ Adicionar Placa Extra / Acompanhante", callback_data="jade_extra_acomp")
    )
    markup.row(
        types.InlineKeyboardButton("🔄 Atualizar Fila JADE", callback_data="jade_refresh_queue")
    )
    return markup


def get_jade_events_inline_keyboard(events_list):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ev in events_list:
        ev_id = ev['id']
        ev_nome = ev.get('nome', 'Solenidade')
        ev_data = ev.get('data_evento', '')
        btn_text = f"🏛️ {ev_nome} ({ev_data})" if ev_data else f"🏛️ {ev_nome}"
        markup.row(types.InlineKeyboardButton(btn_text[:50], callback_data=f"jade_ev_sel:{ev_id}"))
    markup.row(types.InlineKeyboardButton("❌ Cancelar", callback_data="jade_cancel"))
    return markup


def get_acervo_result_keyboard(results):
    """Gera teclado com resultados de busca de acervo."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ev_id, titulo in results:
        titulo_short = titulo[:40] + '...' if len(titulo) > 40 else titulo
        markup.add(
            types.InlineKeyboardButton(f"📸 {titulo_short}", callback_data=f"acervo_select:{ev_id}")
        )
    return markup


def get_acervo_actions_keyboard(ev_id):
    """Gera botoes de acao apos selecionar um evento do acervo (sem redundancia)."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⭐ Receber Álbum HD (Fotos)", callback_data=f"acervo_album:{ev_id}"),
        types.InlineKeyboardButton("🔗 Ver Link & Detalhes do Acervo", callback_data=f"acervo_links:{ev_id}"),
        types.InlineKeyboardButton("❌ Cancelar", callback_data="acervo_cancel")
    )
    return markup
