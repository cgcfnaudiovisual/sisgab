from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection
from services import data_service

THEME = theme.colors

# Opções de papéis/roles no sistema (8 Roles Oficiais)
ROLE_OPTIONS = {
    'admin': 'Administrador (Acesso Total)',
    'supervisor': 'Supervisor COMSOC',
    'oficial_gab': 'Oficial do Gabinete',
    'oficial': 'Oficial da OM',
    'praca_gab': 'Praça do Gabinete',
    'comsoc': 'Equipe COMSOC (Fotografia/Vídeo)',
    'comsoc_design': 'Equipe COMSOC (Artes Gráficas/Canva)',
    'militar': 'Militar / Efetivo em Geral'
}

ROLE_LABELS = {
    **ROLE_OPTIONS,
    'operador': 'Militar / Efetivo em Geral',
    'compel': 'Militar / Efetivo em Geral'
}

ROLE_DESCRIPTIONS = {
    'admin': {
        'title': '👑 Administrador (Acesso Total)',
        'web': '✅ ACESSO TOTAL: Painel Admin, Edição de Operadores, Homologação & Tramitação, Chamada Diária, Agenda, Cautelas, Brindes, TV Gabinete, Cadastro Facial e IA.',
        'telegram': '✅ ACESSO TOTAL: Criar Demandas por Botões, Chamada Matutina, Relatório /pronto CheGab, Digerir Pauta (IA), Cautelas e Painel de Aprovação.'
    },
    'supervisor': {
        'title': '⚖️ Supervisor COMSOC',
        'web': '✅ GESTÃO & HOMOLOGAÇÃO: Homologação e Tramitação de Pautas, Módulo de Presença & Pronto CheGab, Agenda Geral, Cautelas e Mídia TV.',
        'telegram': '✅ GESTÃO: Criar Demandas, Chamada Matutina, Relatório /pronto CheGab, Digerir IA, Agenda e Cautelas.'
    },
    'oficial_gab': {
        'title': '⚖️ Oficial do Gabinete',
        'web': '✅ CHEFIA DO GABINETE: Visualizar Pautas Homologadas, Acompanhar Agenda Geral, Chamada Diária & Pronto CheGab.',
        'telegram': '✅ CHEFIA: Receber Notificações, Dar Presença Diária, Consultar Agenda e /pronto CheGab.'
    },
    'oficial': {
        'title': '⚓ Oficial da OM',
        'web': '✅ OFICIALIDADE: Solicitar Demandas COMSOC, Acompanhar Pautas Homologadas e Consultar Agenda Geral.',
        'telegram': '✅ SOLICITAÇÕES: Criar Demandas por Botões, Consultar Agenda Semanal e Dar Presença.'
    },
    'praca_gab': {
        'title': '📜 Praça do Gabinete (Sargenteação)',
        'web': '✅ SARGENTEARIA & OPERACIONAL: Registrar Presença Diária, Apoiar Chamada, Cautela de Equipamentos e Agenda.',
        'telegram': '✅ SARGENTEARIA: Dar Presença Diária, Gerar /pronto CheGab, Criar Demandas e Cautelas.'
    },
    'comsoc': {
        'title': '📸 Equipe COMSOC (Fotografia/Vídeo)',
        'web': '🎨 EQUIPE COMSOC / PRODUÇÃO: Criar Demandas, Tramitação, Cautelas de Equipamentos, Estoque de Brindes e Mídia TV.',
        'telegram': '🎨 COMSOC: Criar Demandas com Botões, Dar Presença, Cautelas Ativas e Digerir Pauta (IA).'
    },
    'comsoc_design': {
        'title': '🎨 Equipe COMSOC (Artes Gráficas/Canva)',
        'web': '🎨 DESIGN & ARTES: Módulo de Produção Gráfica, Galeria de Artes, Demandas COMSOC e Brindes.',
        'telegram': '🎨 DESIGN: Criar Demandas, Digerir IA, Consultar Agenda e Dar Presença.'
    },
    'militar': {
        'title': '⚓ Militar / Efetivo em Geral',
        'web': '⚓ AUTOATENDIMENTO: Solicitar Cobertura COMSOC, Consultar Agenda e Galeria de Fotos.',
        'telegram': '⚓ AUTOATENDIMENTO: Responder Chamada Matutina, Consultar Agenda e Buscar Fotos.'
    }
}

def render_page():
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', '')).strip().lower()

    container = ui.column().classes('w-full q-pa-lg gap-6')

    if user_role != 'admin':
        with container:
            with theme.card_base().classes('w-full q-pa-lg items-center justify-center text-center gap-4'):
                ui.icon('gpp_bad', size='4rem').classes('text-red-5')
                ui.label('Acesso Restrito ao Administrador').classes('text-xl font-bold text-red-4')
                ui.label('O gerenciamento de usuários, permissões e aprovação de novos cadastros é exclusivo para Administradores.').classes('text-sm text-grey-4')
                ui.button('⬅️ Voltar ao Início', on_click=lambda: ui.navigate.to('/')).props('unelevated color=primary text-color=black bold').classes('q-mt-sm')
        return

    selected_user_ids = set()

    def reload_admin_data():

        container.clear()
        
        # Carregar solicitações pendentes e usuários
        db_conn = get_service_db_connection() or get_db_connection()
        requests_data = []
        users_data = []
        is_offline = not db_conn

        if db_conn:
            try:
                # Solicitações pendentes reais (suporta 'RegistrationRequests' e 'registration_requests')
                raw_reqs = []
                for tbl in ['RegistrationRequests', 'registration_requests']:
                    try:
                        req_res = db_conn.table(tbl).select('*').in_('status', ['pending', 'pendente']).execute()
                        if req_res and req_res.data:
                            raw_reqs.extend(req_res.data)
                    except Exception:
                        pass
                
                # Deduplica por ID ou e-mail
                seen_req_ids = set()
                requests_data = []
                for r in raw_reqs:
                    r_key = r.get('id') or r.get('email')
                    if r_key and r_key not in seen_req_ids:
                        seen_req_ids.add(r_key)
                        requests_data.append(r)

                # Usuários e Efetivo reais (suporta 'Users' e 'users')
                raw_users = []
                for u_tbl in ['Users', 'users']:
                    try:
                        u_res = db_conn.table(u_tbl).select('*').execute()
                        if u_res and u_res.data:
                            raw_users.extend(u_res.data)
                    except Exception:
                        pass
                
                # Deduplica usuários reais
                seen_u_keys = set()
                users_data = []
                for u in raw_users:
                    uk = u.get('id') or u.get('email') or u.get('username')
                    if uk and uk not in seen_u_keys:
                        seen_u_keys.add(uk)
                        users_data.append(u)
                
                def clean_militar_name(name_str):
                    if not name_str:
                        return ""
                    words = str(name_str).strip().upper().split()
                    stopwords = {
                        'SO', 'SG', 'CB', 'SD', 'MN', 'CMG', 'CF', 'CC', 'CT', '1TEN', '2TEN', 'GM',
                        'SARGENTO', 'CABO', 'SOLDADO', 'SUBOFICIAL', 'ADMIN', 'ADMINISTRADOR', 'OPERADOR',
                        'NONE', '1º', '2º', '3º', 'OFICIAL'
                    }
                    cleaned = [w for w in words if w not in stopwords and not w.isdigit()]
                    return " ".join(cleaned) if cleaned else " ".join(words)

                # Conjuntos para deduplicação robusta
                existing_emails = {str(u.get('email', '')).strip().lower() for u in users_data if u.get('email')}
                existing_tgs = {str(u.get('telegram_id', '')).strip() for u in users_data if u.get('telegram_id')}
                existing_clean_names = {clean_militar_name(u.get('nome')) for u in users_data if u.get('nome')}
                existing_usernames = {str(u.get('username', '')).strip().lower() for u in users_data if u.get('username')}

                efetivo_res = db_conn.table('efetivo').select('*').execute()
                posto_map = {}
                if efetivo_res and efetivo_res.data:
                    for ef in efetivo_res.data:
                        pg = ef.get('posto_grad') or ''
                        email = str(ef.get('email') or '').strip().lower()
                        guerra = str(ef.get('nome_guerra') or '').strip().upper()
                        guerra_clean = clean_militar_name(guerra)
                        tg_id = str(ef.get('telegram_id') or '').strip()

                        if email: posto_map[email] = pg
                        if guerra: posto_map[guerra] = pg

                        # Checa se este operador já existe nos usuários
                        is_dup = False
                        if email and email in existing_emails:
                            is_dup = True
                        elif tg_id and tg_id in existing_tgs:
                            is_dup = True
                        elif guerra_clean and guerra_clean in existing_clean_names:
                            is_dup = True
                        elif guerra and guerra.lower() in existing_usernames:
                            is_dup = True

                        if not is_dup:
                            ant_val = ef.get('antiguidade_num') or ef.get('numero_antiguidade') or ef.get('ordem_precedencia')
                            users_data.append({
                                'id': str(ef.get('id')),
                                'username': guerra.lower() if guerra else 'militar',
                                'nome': f"{pg} {guerra}".strip() if pg else guerra,
                                'role': ef.get('role', 'praca_gab'),
                                'telegram_id': ef.get('telegram_id', ''),
                                'url_foto': ef.get('url_foto', ''),
                                'posto_grad': pg,
                                'antiguidade_num': ant_val
                            })
                            if email: existing_emails.add(email)
                            if tg_id: existing_tgs.add(tg_id)
                            if guerra_clean: existing_clean_names.add(guerra_clean)


                # Preenche posto_grad e normaliza antiguidade para os usuários da tabela users
                for u in users_data:
                    # Remove "NONE" do nome do usuário se houver devido a bug anterior
                    if str(u.get('nome', '')).upper().startswith("NONE "):
                        u['nome'] = str(u.get('nome', ''))[5:].strip()
                        
                    if 'posto_grad' not in u:
                        email = str(u.get('username', '')).lower()
                        nome = str(u.get('nome', '')).upper()
                        pg = posto_map.get(email) or posto_map.get(nome) or ''
                        if not pg:
                            parts = nome.split()
                            first_word = parts[0] if parts else ''
                            if first_word in ('SO', 'SG', 'CB', 'SD', 'MN', 'CMG', 'CF', 'CC', 'CT', '1TEN', '2TEN', 'GM', 'SARGENTO', 'CABO', 'SOLDADO', 'SUBOFICIAL'):
                                pg = first_word
                        u['posto_grad'] = pg

                # Determina antiguidade de postos/graduações da Marinha (1 = mais antigo, 99 = sem posto)
                def get_rank_seniority(rank_str):
                    if not rank_str:
                        return 99
                    rank = str(rank_str).upper().replace('.', '').replace(' ', '').strip()
                    
                    if rank in ('AE', 'ALMIRANTEDEESQUADRA'): return 1
                    if rank in ('VA', 'VICEALMIRANTE'): return 2
                    if rank in ('CA', 'CONTRAALMIRANTE'): return 3
                    if rank in ('CMG', 'CAPITAODEMAREGUERRA'): return 4
                    if rank in ('CF', 'CAPITAODEFRAGATA'): return 5
                    if rank in ('CC', 'CAPITAODECORVETA'): return 6
                    if rank in ('CT', 'CAPITAOTENENTE'): return 7
                    if any(x in rank for x in ('1TEN', '1ºTEN', '1SOTEN', '1TENENTE', '1ºTENENTE')): return 8
                    if any(x in rank for x in ('2TEN', '2ºTEN', '2SOTEN', '2TENENTE', '2ºTENENTE')): return 9
                    if rank in ('GM', 'GUARDAMARINHA'): return 10
                    if rank in ('SO', 'SUBOFICIAL', 'SUB-OFICIAL'): return 11
                    if any(x in rank for x in ('1SG', '1ºSG', '1SGT', '1ºSGT', '1ºSARGENTO', '1SARGENTO')): return 12
                    if any(x in rank for x in ('2SG', '2ºSG', '2SGT', '2ºSGT', '2ºSARGENTO', '2SARGENTO')): return 13
                    if any(x in rank for x in ('3SG', '3ºSG', '3SGT', '3ºSGT', '3ºSARGENTO', '3SARGENTO', 'SG', 'SARGENTO')): return 14
                    if rank in ('CB', 'CABO'): return 15
                    if rank in ('SD', 'SOLDADO', 'MN', 'MARINHEIRO'): return 16
                    return 98

                # Ordena os operadores pela coluna antiguidade_num (cadeia hierarquica unica)
                def sort_users(u):
                    role = str(u.get('role', '')).strip().lower()
                    is_comsoc = role in ('admin', 'supervisor', 'comsoc', 'comsoc_design')
                    group_priority = 0 if is_comsoc else 1

                    raw_ant = u.get('antiguidade_num') or u.get('numero_antiguidade') or u.get('ordem_precedencia')
                    try:
                        ant_val = int(str(raw_ant).strip()) if raw_ant is not None else 9999
                    except Exception:
                        ant_val = 9999

                    # Fallback por posto/graduacao se nao houver numero definido
                    if ant_val in (99, 9999):
                        pg = u.get('posto_grad') or ''
                        if not pg:
                            parts = str(u.get('nome', '')).split()
                            pg = parts[0] if parts else ''
                        ant_val = get_rank_seniority(pg) + 1000  # Coloca apos os que tem numero definido

                    nome_guerra = str(u.get('nome', '')).upper()
                    return (group_priority, ant_val, nome_guerra)
                
                users_data = sorted(users_data, key=sort_users)

                cur_filter = app.storage.user.get('admin_filter_role', 'TODOS')
                if cur_filter != 'TODOS':
                    if cur_filter == 'comsoc':
                        users_data = [u for u in users_data if str(u.get('role', '')).lower() in ('comsoc', 'comsoc_design', 'supervisor')]
                    elif cur_filter == 'militar':
                        users_data = [u for u in users_data if str(u.get('role', '')).lower() in ('militar', 'compel', 'oficial', 'oficial_gab')]
                    else:
                        users_data = [u for u in users_data if str(u.get('role', '')).lower() == cur_filter]
            except Exception as e:
                print(f"[ADMIN] Erro ao carregar dados do Supabase: {e}")

        # --- DIÁLOGOS ADMINISTRATIVOS ---

        # 1. Diálogo de Criação de Operador
        def open_create_dialog():
            with ui.dialog() as create_dialog, ui.card().classes('w-[420px] q-pa-md bg-slate-900 border').style(f'border-color: {THEME["accent"]};'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2 w-full justify-between'):
                        ui.label('➕ CADASTRAR OPERADOR').classes('text-white text-md font-black cyber-title')
                        ui.icon('person_add', size='1.5rem').style(f'color: {THEME["accent"]}')
                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    ranks_options = ['AE', 'VA', 'CA', 'CMG', 'CF', 'CC', 'CT', '1ºTEN', '2ºTEN', 'GM', 'SO', '1ºSG', '2ºSG', '3ºSG', 'CB', 'SD/MN']
                    with ui.row().classes('w-full gap-2 no-wrap'):
                        c_posto = ui.select(ranks_options, label='Posto / Graduação', value='SO').props('dark outlined dense').classes('w-1/2')
                        c_antiguidade = ui.number('Antiguidade / Precedência', value=1, min=1, step=1).props('dark outlined dense').classes('w-1/2').tooltip('Ordem de precedência militar no grupo (1 = Mais Antigo)')

                    c_email = ui.input('E-mail (Login)', placeholder='militar@marinha.mil.br').props('dark outlined dense w-full')
                    c_pwd = ui.input('Senha Inicial', password=True).props('dark outlined dense w-full')
                    c_nome = ui.input('Nome de Guerra').props('dark outlined dense w-full')
                    c_tg = ui.input('Telegram ID (Opcional)').props('dark outlined dense w-full')
                    c_foto = ui.input('URL da Foto (Opcional)').props('dark outlined dense w-full')
                    
                    async def handle_c_upload(e):
                        import re
                        import uuid
                        import inspect
                        import asyncio
                        file_bytes = e.file.read()
                        if inspect.isawaitable(file_bytes):
                            file_bytes = await file_bytes
                        clean_name = re.sub(r'\W+', '', c_nome.value or 'operador').lower()
                        filename = f"operadores/{clean_name}_{uuid.uuid4().hex[:8]}.jpg"
                        from database import upload_file_to_supabase_storage
                        public_url = await asyncio.to_thread(upload_file_to_supabase_storage, file_bytes, filename, e.file.content_type)
                        if public_url:
                            c_foto.value = public_url
                            ui.notify('Foto enviada com sucesso!', color='success')
                        else:
                            ui.notify('Erro ao enviar foto ao Supabase.', color='red')
                    
                    ui.upload(label='Enviar Foto para o Supabase', on_upload=handle_c_upload, auto_upload=True, max_files=1).props('dark dense').classes('w-full h-20')
                    
                    c_role = ui.select(ROLE_OPTIONS, label='Papel do Usuário', value='militar').props('dark outlined dense w-full')
                    
                    c_error = ui.label('').classes('text-xs text-red w-full text-center')
                    
                    def handle_create():
                        try:
                            # SEGURANÇA: Verificação de privilégios server-side
                            user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                            if not any(r in user_role for r in ('ADMIN', 'SUPERVISOR', 'GERENTE', 'CHEFE', 'COMSOC', 'OFICIAL')):
                                ui.notify("⛔ Acesso negado. Apenas administradores ou supervisores.", color='negative')
                                return
                            if not c_email.value or not c_pwd.value or not c_nome.value:
                                c_error.text = 'E-mail, Senha e Nome de Guerra são obrigatórios.'
                                return
                            
                            import bcrypt
                            pwd_hash = bcrypt.hashpw(c_pwd.value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                            clean_name_save = clean_militar_name(c_nome.value)
                            full_name_save = f"{c_posto.value} {clean_name_save}".strip()
                            ant_save = int(c_antiguidade.value) if c_antiguidade.value else 99
                            
                            if is_offline:
                                ui.notify(f"[OFFLINE] Novo operador {full_name_save} cadastrado!", color='success')
                                users_data.append({
                                    'id': f'mock-uid-{len(users_data)+1}',
                                    'username': c_email.value.split('@')[0],
                                    'nome': full_name_save,
                                    'role': c_role.value,
                                    'telegram_id': c_tg.value or '',
                                    'url_foto': c_foto.value or '',
                                    'posto_grad': c_posto.value,
                                    'antiguidade_num': ant_save
                                })
                                create_dialog.close()
                                reload_admin_data()
                                return
                            
                            conn = get_service_db_connection() or get_db_connection()
                            if not conn:
                                ui.notify('Sem conexão com banco de dados', color='red')
                                return
                            
                            auth_id = None
                            admin_conn = None
                            from database import get_bot_db_connection
                            try:
                                admin_conn = get_bot_db_connection()
                            except Exception:
                                pass
                            
                            if admin_conn and hasattr(admin_conn, 'auth') and hasattr(admin_conn.auth, 'admin'):
                                try:
                                    res = admin_conn.auth.admin.create_user({
                                        "email": c_email.value,
                                        "password": c_pwd.value,
                                        "email_confirm": True
                                    })
                                    if res and res.user:
                                        auth_id = res.user.id
                                except Exception as auth_err:
                                    print(f"[AUTH ERROR] Tentando signup direto: {auth_err}")
                            
                            if not auth_id:
                                # Fallback para signup regular
                                try:
                                    res = conn.auth.sign_up({"email": c_email.value, "password": c_pwd.value})
                                    if res and res.user:
                                        auth_id = res.user.id
                                except Exception as sign_err:
                                    print(f"[SIGNUP ERR] {sign_err}")
                                    ui.notify("Limite do Supabase Auth atingido. Criando usuário no banco local...", color='warning', duration=5)
                            
                            if not auth_id:
                                import uuid
                                auth_id = str(uuid.uuid4())
                                ui.notify('Operador registrado com sucesso no banco de dados local!', color='success')

                            # Insere na tabela users (com antiguidade_num apos migracao SQL)
                            u_payload = {
                                'id': auth_id,
                                'username': c_email.value.split('@')[0],
                                'nome': full_name_save,
                                'role': c_role.value,
                                'telegram_id': c_tg.value or None,
                                'url_foto': c_foto.value or None,
                                'email': c_email.value,
                                'antiguidade_num': ant_save
                            }
                            try:
                                conn.table('users').insert(u_payload).execute()
                            except Exception:
                                u_payload.pop('email', None)
                                try:
                                    conn.table('users').insert(u_payload).execute()
                                except Exception:
                                    u_payload.pop('url_foto', None)
                                    conn.table('users').insert(u_payload).execute()
                            
                            # Cria também na tabela efetivo para manter integridade
                            ef_payload = {
                                'telegram_id': c_tg.value or None,
                                'nome_guerra': clean_name_save,
                                'posto': c_posto.value,
                                'posto_grad': c_posto.value,
                                'email': c_email.value,
                                'senha_hash': pwd_hash,
                                'role': c_role.value,
                                'url_foto': c_foto.value or None,
                                'antiguidade_num': ant_save
                            }
                            try:
                                conn.table('efetivo').insert(ef_payload).execute()
                            except Exception:
                                ef_payload.pop('antiguidade_num', None)
                                try:
                                    conn.table('efetivo').insert(ef_payload).execute()
                                except Exception:
                                    ef_payload.pop('url_foto', None)
                                    conn.table('efetivo').insert(ef_payload).execute()
                            
                            ui.notify(f"Operador {full_name_save} cadastrado com sucesso!", color='success')
                            data_service.clear_cache()
                            create_dialog.close()
                            reload_admin_data()
                        except Exception as err:
                            c_error.text = f"Erro: {err}"
                    
                    with ui.row().classes('w-full justify-end gap-2'):
                        ui.button('Cancelar', on_click=create_dialog.close).props('flat color=grey')
                        ui.button('Cadastrar', on_click=handle_create).props('unelevated color=cyan-9 text-color=white')
            create_dialog.open()

        # 2. Diálogo de Edição de Operador
        def open_edit_dialog(user):
            user_email = user.get('email', '') or ""
            if not user_email:
                db_conn = get_service_db_connection() or get_db_connection()
                if db_conn:
                    try:
                        res_ef = db_conn.table('efetivo').select('email').eq('nome_guerra', user.get('nome', '').upper()).execute()
                        if res_ef.data and res_ef.data[0].get('email'):
                            user_email = res_ef.data[0]['email']
                        else:
                            if user.get('telegram_id'):
                                res_ef2 = db_conn.table('efetivo').select('email').eq('telegram_id', user['telegram_id']).execute()
                                if res_ef2.data and res_ef2.data[0].get('email'):
                                    user_email = res_ef2.data[0]['email']
                    except Exception as ef_err:
                        print(f"[EDIT EMAIL LOOKUP ERR] {ef_err}")

            with ui.dialog() as edit_dialog, ui.card().classes('w-[420px] q-pa-md bg-slate-900 border').style(f'border-color: {THEME["accent"]};'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2 w-full justify-between'):
                        ui.label('✏️ EDITAR OPERADOR').classes('text-white text-md font-black cyber-title')
                        ui.icon('edit', size='1.5rem').style(f'color: {THEME["accent"]}')
                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    # Limpa o prefixo 'None ' se existir
                    clean_nome_val = str(user.get('nome', '') or '').replace('None ', '').replace('None', '').strip()
                    
                    user_pg_val = str(user.get('posto_grad') or user.get('posto') or '').strip().upper()
                    ranks_options = ['AE', 'VA', 'CA', 'CMG', 'CF', 'CC', 'CT', '1ºTEN', '2ºTEN', 'GM', 'SO', '1ºSG', '2ºSG', '3ºSG', 'CB', 'SD/MN']
                    if user_pg_val not in ranks_options:
                        user_pg_val = 'SO' if 'SO' in clean_nome_val else ('SG' if 'SG' in clean_nome_val else ('CB' if 'CB' in clean_nome_val else 'SO'))

                    with ui.row().classes('w-full gap-2 no-wrap'):
                        e_posto = ui.select(ranks_options, label='Posto / Graduação', value=user_pg_val).props('dark outlined dense').classes('w-1/3')
                        e_nome = ui.input('Nome de Guerra', value=clean_nome_val).props('dark outlined dense').classes('w-2/3')

                    e_email = ui.input('E-mail (Login)', value=user_email).props('dark outlined dense w-full')
                    e_unm = ui.input('Username (Login)', value=user.get('username', '')).props('dark outlined dense w-full')
                    e_tg = ui.input('Telegram ID', value=user.get('telegram_id', '') or '').props('dark outlined dense w-full')
                    
                    # Layout de duas colunas: Esquerda (URL), Direita (Preview da foto)
                    with ui.row().classes('w-full items-start gap-4 no-wrap'):
                        with ui.column().classes('col-grow gap-2'):
                            e_foto = ui.input('URL da Foto', value=user.get('url_foto', '') or '').props('dark outlined dense w-full').classes('text-xs')
                        
                        # Preview do Avatar
                        user_photo = user.get('url_foto') or ''
                        user_avatar_src = user_photo if isinstance(user_photo, str) and user_photo.startswith('http') else 'https://cdn.quasar.dev/img/boy-avatar.png'
                        with ui.column().classes('items-center justify-center shrink-0'):
                            img_box = ui.element('div').classes('shadow border border-cyan-500/30').style(
                                f"width: 72px; height: 72px; background-image: url('{user_avatar_src}'); "
                                f"background-size: cover; background-repeat: no-repeat; "
                                f"background-position: center; background-color: #050b14; border-radius: 4px;"
                            )
                            ui.label('FOTO').classes('text-[9px] text-grey-5 font-bold tracking-widest q-mt-xs')
                    
                    # Uploader de arquivos
                    async def handle_e_upload(e):
                        import re
                        import inspect
                        import asyncio
                        file_bytes = e.file.read()
                        if inspect.isawaitable(file_bytes):
                            file_bytes = await file_bytes
                        clean_name = re.sub(r'\W+', '', e_nome.value or 'operador').lower()
                        filename = f"operadores/{clean_name}_{str(user['id'])[:8]}.jpg"
                        from database import upload_file_to_supabase_storage
                        public_url = await asyncio.to_thread(upload_file_to_supabase_storage, file_bytes, filename, e.file.content_type)
                        if public_url:
                            e_foto.value = public_url
                            img_box.style(f"background-image: url('{public_url}');")
                            ui.notify('Foto enviada com sucesso!', color='success')
                        else:
                            ui.notify('Erro ao enviar foto ao Supabase.', color='red')
                            
                    ui.upload(label='Fazer Upload de Nova Foto', on_upload=handle_e_upload, auto_upload=True, max_files=1).props('dark dense').classes('w-full h-20')
                    
                    def update_foto_preview():
                        src = e_foto.value.strip() if e_foto.value else ''
                        if not src.startswith('http'):
                            src = 'https://cdn.quasar.dev/img/boy-avatar.png'
                        img_box.style(f"background-image: url('{src}');")
                        
                    e_foto.on('change', update_foto_preview)
                    
                    user_role_val = str(user.get('role', 'compel')).strip().lower()
                    if user_role_val not in ROLE_OPTIONS:
                        user_role_val = 'compel'

                    cur_ant_raw = user.get('antiguidade_num') or user.get('numero_antiguidade') or user.get('ordem_precedencia')
                    if cur_ant_raw is not None and str(cur_ant_raw).strip().isdigit():
                        cur_ant_val = int(str(cur_ant_raw).strip())
                    else:
                        cur_ant_val = get_rank_seniority(user_pg_val)

                    with ui.row().classes('w-full gap-2 no-wrap'):
                        e_role = ui.select(ROLE_OPTIONS, label='Papel do Usuário', value=user_role_val).props('dark outlined dense').classes('w-2/3')
                        e_antiguidade = ui.number('Antiguidade / Precedência', value=cur_ant_val, min=1, step=1).props('dark outlined dense').classes('w-1/3').tooltip('Ordem de precedência militar no grupo (1 = Mais Antigo)')
                    
                    # Painel Dinâmico de Detalhamento das Permissões do Papel
                    role_info_box = ui.column().classes('w-full q-pa-sm border border-cyan-500/30 rounded-lg bg-black/50 gap-1')
                    
                    def render_role_permissions_info(r_val):
                        role_info_box.clear()
                        info = ROLE_DESCRIPTIONS.get(r_val, ROLE_DESCRIPTIONS['militar'])
                        with role_info_box:
                            ui.label(f"📋 PERMISSÕES DE ACESSO DO PERFIL ({r_val.upper()}):").classes('text-[10px] font-bold text-cyan')
                            ui.label(f"🌐 Web App SisGAB:").classes('text-[10px] font-bold text-white q-mt-xs')
                            ui.label(info['web']).classes('text-[10px] text-grey-3 font-mono leading-tight')
                            ui.label(f"📱 Telegram Bot:").classes('text-[10px] font-bold text-cyan-4 q-mt-xs')
                            ui.label(info['telegram']).classes('text-[10px] text-cyan-2 font-mono leading-tight')

                    e_role.on_value_change(lambda e: render_role_permissions_info(e.value))
                    render_role_permissions_info(user_role_val)

                    e_error = ui.label('').classes('text-xs text-red w-full text-center')
                    
                    def handle_edit():
                        # SEGURANÇA: Verificação de privilégios server-side
                        user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                        if not any(r in user_role for r in ('ADMIN', 'SUPERVISOR', 'GERENTE', 'CHEFE', 'COMSOC', 'OFICIAL')):
                            ui.notify("⛔ Acesso negado. Apenas administradores ou supervisores.", color='negative')
                            return
                        if not e_nome.value or not e_unm.value:
                            e_error.text = 'Nome de Guerra e Username são obrigatórios.'
                            return
                        
                        nome_final = e_nome.value.replace('None ', '').replace('None', '').strip().upper()
                        ant_save = int(e_antiguidade.value) if e_antiguidade.value else 99
                        
                        if is_offline:
                            ui.notify(f"[OFFLINE] Dados de {user['username']} atualizados!", color='success')
                            user['nome'] = nome_final
                            user['username'] = e_unm.value
                            user['telegram_id'] = e_tg.value or ''
                            user['url_foto'] = e_foto.value or ''
                            user['role'] = e_role.value
                            user['antiguidade_num'] = ant_save
                            edit_dialog.close()
                            reload_admin_data()
                            return
                        
                        conn = get_service_db_connection() or get_db_connection()
                        if not conn:
                            ui.notify('Sem conexão com banco de dados', color='red')
                            return
                        
                        try:
                            uid_str = str(user.get('id', ''))
                            is_uuid = len(uid_str) == 36 and '-' in uid_str

                            # 1. Atualiza o e-mail no Supabase Auth se fornecido e alterado
                            if is_uuid and e_email.value and e_email.value.strip() != user_email:
                                from database import get_bot_db_connection
                                admin_conn = None
                                try:
                                    admin_conn = get_bot_db_connection()
                                except Exception:
                                    pass
                                if admin_conn and hasattr(admin_conn, 'auth') and hasattr(admin_conn.auth, 'admin'):
                                    try:
                                        admin_conn.auth.admin.update_user_by_id(uid_str, {"email": e_email.value.strip()})
                                    except Exception as auth_email_err:
                                        print(f"[AUTH EMAIL UPDATE ERR] {auth_email_err}")

                            # 2. Atualiza a tabela users (antiguidade_num disponivel apos executar a migracao SQL)
                            nome_com_posto = f"{e_posto.value} {clean_militar_name(nome_final)}".strip()
                            user_payload = {
                                'nome': nome_com_posto,
                                'username': e_unm.value,
                                'telegram_id': e_tg.value or None,
                                'url_foto': e_foto.value or None,
                                'role': e_role.value,
                                'antiguidade_num': ant_save
                            }
                            if e_email.value:
                                user_payload['email'] = e_email.value.strip()

                            users_updated = False
                            users_err_msg = ''
                            try:
                                if is_uuid:
                                    res_u = conn.table('users').update(user_payload).eq('id', uid_str).execute()
                                elif user_email:
                                    res_u = conn.table('users').update(user_payload).eq('email', user_email).execute()
                                else:
                                    res_u = conn.table('users').update(user_payload).eq('username', user.get('username')).execute()
                                # Verifica se alguma linha foi de fato afetada
                                if res_u and hasattr(res_u, 'data') and res_u.data:
                                    users_updated = True
                                    print(f"[USERS UPDATE OK] {len(res_u.data)} linha(s) atualizada(s) para {nome_com_posto}")
                                else:
                                    users_err_msg = 'Nenhuma linha afetada na tabela users (ID/email não encontrado)'
                                    print(f"[USERS UPDATE WARN] {users_err_msg} | uid={uid_str} | email={user_email}")
                            except Exception as u_err:
                                users_err_msg = str(u_err)
                                print(f"[USERS UPDATE ERR] {u_err}")
                                # Tenta sem email (campo pode ter restrição de unicidade)
                                try:
                                    payload_sem_email = {k: v for k, v in user_payload.items() if k != 'email'}
                                    if is_uuid:
                                        res_u2 = conn.table('users').update(payload_sem_email).eq('id', uid_str).execute()
                                    else:
                                        res_u2 = conn.table('users').update(payload_sem_email).eq('username', user.get('username')).execute()
                                    if res_u2 and hasattr(res_u2, 'data') and res_u2.data:
                                        users_updated = True
                                        print(f"[USERS UPDATE RETRY OK] {len(res_u2.data)} linha(s)")
                                except Exception as u_retry_err:
                                    print(f"[USERS RETRY ERR] {u_retry_err}")

                            # 3. Garante UNICIDADE de precedência: se outro militar já tem ant_save, faz o swap
                            try:
                                res_check = conn.table('efetivo').select('id, nome_guerra, email, antiguidade_num').eq('antiguidade_num', ant_save).execute()
                                if res_check and res_check.data:
                                    for conflito in res_check.data:
                                        conflito_email = conflito.get('email', '')
                                        conflito_id = conflito.get('id')
                                        # Só faz swap se for um registro diferente do atual
                                        if conflito_email != user_email and str(conflito_id) != uid_str:
                                            # Busca a precedência atual deste usuário para fazer o swap
                                            cur_ant = user.get('antiguidade_num') or 99
                                            try:
                                                if conflito_id:
                                                    conn.table('efetivo').update({'antiguidade_num': int(cur_ant)}).eq('id', conflito_id).execute()
                                                    print(f"[PRECEDENCIA SWAP] {conflito.get('nome_guerra')} {ant_save} -> {cur_ant}")
                                            except Exception as swap_err:
                                                print(f"[PRECEDENCIA SWAP ERR] {swap_err}")
                            except Exception as check_err:
                                print(f"[PRECEDENCIA CHECK ERR] {check_err}")

                            # 4. Mantém a integridade da tabela efetivo (SEMPRE tenta, independente do status de users)
                            ef_updated = False
                            try:
                                update_fields = {
                                    'nome_guerra': clean_militar_name(nome_final),
                                    'posto': e_posto.value,
                                    'posto_grad': e_posto.value,
                                    'telegram_id': e_tg.value or None,
                                    'role': e_role.value,
                                    'email': e_email.value or None,
                                    'url_foto': e_foto.value or None,
                                    'antiguidade_num': ant_save
                                }
                                
                                res_ef = None
                                if not is_uuid and uid_str.isdigit():
                                    res_ef = conn.table('efetivo').update(update_fields).eq('id', int(uid_str)).execute()
                                elif user_email:
                                    res_ef = conn.table('efetivo').update(update_fields).eq('email', user_email).execute()
                                elif user.get('telegram_id'):
                                    res_ef = conn.table('efetivo').update(update_fields).eq('telegram_id', user.get('telegram_id')).execute()
                                else:
                                    clean_target = clean_militar_name(user.get('nome', ''))
                                    res_ef = conn.table('efetivo').update(update_fields).ilike('nome_guerra', f"%{clean_target}%").execute()
                                
                                if res_ef and hasattr(res_ef, 'data') and res_ef.data:
                                    ef_updated = True
                                    print(f"[EFETIVO UPDATE OK] {len(res_ef.data)} linha(s) atualizada(s)")
                                else:
                                    print(f"[EFETIVO UPDATE WARN] Nenhuma linha afetada | uid={uid_str} | email={user_email}")
                                    
                            except Exception as ef_err:
                                print(f"[EFETIVO UPDATE ERR] {ef_err}")
                                # Tenta sem antiguidade_num se a coluna não existir no efetivo
                                try:
                                    update_fields_sem_ant = {k: v for k, v in update_fields.items() if k != 'antiguidade_num'}
                                    if user_email:
                                        conn.table('efetivo').update(update_fields_sem_ant).eq('email', user_email).execute()
                                    elif user.get('telegram_id'):
                                        conn.table('efetivo').update(update_fields_sem_ant).eq('telegram_id', user.get('telegram_id')).execute()
                                except Exception as ef_retry_err:
                                    print(f"[EFETIVO RETRY ERR] {ef_retry_err}")

                            # 4. Atualiza o dict local imediatamente para o UI refletir sem depender do reload
                            user['nome'] = nome_com_posto
                            user['username'] = e_unm.value
                            user['telegram_id'] = e_tg.value or ''
                            user['url_foto'] = e_foto.value or ''
                            user['role'] = e_role.value
                            user['antiguidade_num'] = ant_save
                            user['posto_grad'] = e_posto.value

                            # 5. Feedback de resultado real
                            if users_updated or ef_updated:
                                ui.notify(f"✅ Cadastro de {nome_final} atualizado com sucesso!", color='positive')
                            elif not users_updated and not ef_updated:
                                ui.notify(f"⚠️ Salvo localmente mas não encontrado no banco. Verifique o ID/email. Erro: {users_err_msg[:80]}", color='warning', duration=8)
                            else:
                                ui.notify(f"✅ {nome_final} atualizado (efetivo: {ef_updated}, users: {users_updated})", color='positive')
                            
                            data_service.clear_cache()
                            edit_dialog.close()
                            reload_admin_data()
                        except Exception as err:
                            e_error.text = f"Erro: {err}"
                            ui.notify(f"❌ Erro ao salvar: {err}", color='negative', duration=8)

                            
                    # Botões de Ação (recuados para ficarem dentro da coluna do diálogo)
                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                        ui.button('Cancelar', on_click=edit_dialog.close).props('flat color=grey')
                        ui.button('Salvar', on_click=handle_edit).props('unelevated color=cyan-9 text-color=white')
            edit_dialog.open()

        # 3. Diálogo de Redefinição de Senha
        def open_password_dialog(user):
            with ui.dialog() as pwd_dialog, ui.card().classes('w-[380px] q-pa-md bg-slate-900 border border-amber-500/30'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2 w-full justify-between'):
                        ui.label('🔑 ALTERAR SENHA').classes('text-white text-md font-black cyber-title')
                        ui.icon('lock_reset', size='1.5rem').style('color: #ffb300;')
                    ui.separator().style('background-color: rgba(255, 179, 0, 0.15);')
                    
                    ui.label(f"Alterar senha para: {user['nome']}").classes('text-xs text-grey-4')
                    new_pwd = ui.input('Nova Senha', password=True).props('dark outlined dense w-full')
                    pwd_error = ui.label('').classes('text-xs text-red w-full text-center')
                    
                    def handle_password():
                        # SEGURANÇA: Verificação de privilégios server-side
                        user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                        if not any(r in user_role for r in ('ADMIN', 'SUPERVISOR', 'GERENTE', 'CHEFE', 'COMSOC', 'OFICIAL')):
                            ui.notify("⛔ Acesso negado. Apenas administradores ou supervisores.", color='negative')
                            return
                        if not new_pwd.value or len(new_pwd.value) < 6:
                            pwd_error.text = 'A senha deve conter no mínimo 6 caracteres.'
                            return
                        
                        import bcrypt
                        pwd_hash = bcrypt.hashpw(new_pwd.value.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                        
                        if is_offline:
                            ui.notify(f"[OFFLINE] Senha de {user['nome']} redefinida!", color='success')
                            pwd_dialog.close()
                            return
                        
                        conn = get_service_db_connection() or get_db_connection()
                        if not conn:
                            ui.notify('Sem conexão com banco de dados', color='red')
                            return
                        
                        try:
                            from database import get_bot_db_connection
                            admin_conn = None
                            try:
                                admin_conn = get_bot_db_connection()
                            except Exception:
                                pass
                            
                            auth_updated = False
                            if admin_conn and hasattr(admin_conn, 'auth') and hasattr(admin_conn.auth, 'admin'):
                                try:
                                    admin_conn.auth.admin.update_user_by_id(user['id'], {"password": new_pwd.value})
                                    auth_updated = True
                                except Exception as auth_err:
                                    print(f"[AUTH PASSWORD UPDATE ERROR] {auth_err}")
                            
                            # Atualiza também a tabela efetivo
                            try:
                                if user.get('telegram_id'):
                                    conn.table('efetivo').update({'senha_hash': pwd_hash}).or_(f"telegram_id.eq.{user['telegram_id']},nome_guerra.eq.{user.get('nome', '').upper()}").execute()
                                else:
                                    conn.table('efetivo').update({'senha_hash': pwd_hash}).eq('nome_guerra', user.get('nome', '').upper()).execute()
                            except Exception as db_err:
                                print(f"[DB PASSWORD UPDATE ERR] {db_err}")
                            
                            if auth_updated:
                                ui.notify(f"Senha de {user['nome']} alterada com sucesso!", color='success')
                            else:
                                ui.notify(f"Senha atualizada no DB! Nota: Sem permissão service_role para redefinir no Auth.", color='warning')
                            
                            data_service.clear_cache()
                            pwd_dialog.close()
                        except Exception as err:
                            pwd_error.text = f"Erro: {err}"
            
                    # Botões de Ação (dentro da coluna do diálogo)
                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                        ui.button('Cancelar', on_click=pwd_dialog.close).props('flat color=grey')
                        ui.button('Alterar Senha', on_click=handle_password).props('unelevated color=amber-9 text-color=black')
            pwd_dialog.open()

        # 4. Diálogo de Confirmação de Exclusão
        def open_delete_dialog(user):
            with ui.dialog() as del_dialog, ui.card().classes('w-[380px] q-pa-md bg-slate-900 border border-red-500/30'):
                with ui.column().classes('w-full gap-4 items-center text-center'):
                    ui.icon('warning', color='red', size='3rem').classes('animate-pulse')
                    ui.label('CONFIRMAR EXCLUSÃO').classes('text-white text-md font-black cyber-title')
                    ui.label(f"Tem certeza que deseja excluir o acesso de {user['nome']} ({user['username']})?").classes('text-sm text-grey-4')
                    ui.label('Esta ação removerá definitivamente o militar das permissões do painel.').classes('text-xs text-red-400 font-bold')
                    
                    del_error = ui.label('').classes('text-xs text-red w-full')
                    
                    def handle_delete():
                        # SEGURANÇA: Apenas administradores reais podem excluir
                        user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                        if not any(r in user_role for r in ('ADMIN', 'SUPERVISOR', 'GERENTE', 'CHEFE')):
                            ui.notify("⛔ Acesso negado. Apenas administradores podem excluir operadores.", color='negative')
                            return
                        if is_offline:
                            ui.notify(f"[OFFLINE] Operador {user['nome']} removido!", color='success')
                            if user in users_data:
                                users_data.remove(user)
                            del_dialog.close()
                            reload_admin_data()
                            return
                        
                        conn = get_service_db_connection() or get_db_connection()
                        if not conn:
                            ui.notify('Sem conexão com banco de dados', color='red')
                            return
                        
                        try:
                            u_id = str(user['id'])
                            raw_nome = str(user.get('nome') or user.get('username') or '').upper()
                            
                            clean_words = [w for w in raw_nome.split() if w not in ('SO', 'SG', 'CB', 'SD', 'MN', 'CMG', 'CF', 'CC', 'CT', '1TEN', '2TEN', 'GM', 'ADMIN', 'ADMINISTRADOR', 'OPERADOR', 'NONE', '1º', '2º', '3º', 'OFICIAL') and not w.isdigit()]
                            clean_name = " ".join(clean_words) if clean_words else raw_nome

                            # 1. Tenta deletar via Supabase Auth Admin (se for UUID)
                            if not u_id.isdigit():
                                try:
                                    from database import get_bot_db_connection
                                    admin_conn = get_bot_db_connection()
                                    if admin_conn and hasattr(admin_conn, 'auth') and hasattr(admin_conn.auth, 'admin'):
                                        admin_conn.auth.admin.delete_user(u_id)
                                except Exception as auth_err:
                                    print(f"[AUTH DELETE WARN] {auth_err}")

                            # 2. Deleta da tabela users
                            try:
                                conn.table('users').delete().or_(f"id.eq.{u_id},username.ilike.{user.get('username')},nome.ilike.%{clean_name}%").execute()
                            except Exception as u_err:
                                print(f"[USERS DELETE WARN] {u_err}")

                            # 3. Deleta da tabela efetivo por ID ou por Nome de Guerra
                            try:
                                if u_id.isdigit():
                                    conn.table('efetivo').delete().eq('id', int(u_id)).execute()
                                if clean_name:
                                    conn.table('efetivo').delete().ilike('nome_guerra', f"%{clean_name}%").execute()
                                if user.get('email'):
                                    conn.table('efetivo').delete().eq('email', user['email']).execute()
                            except Exception as ef_err:
                                print(f"[EFETIVO DELETE WARN] {ef_err}")

                            # 4. Deleta da tabela registration_requests
                            try:
                                if clean_name:
                                    conn.table('registration_requests').delete().ilike('nome_guerra', f"%{clean_name}%").execute()
                            except Exception:
                                pass

                            ui.notify(f"Operador {user.get('nome', '')} removido definitivamente!", color='success')

                            data_service.clear_cache()
                            del_dialog.close()
                            reload_admin_data()
                        except Exception as err:
                            del_error.text = f"Erro: {err}"
            
                    # Botões de Ação (dentro da coluna do diálogo)
                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                        ui.button('Cancelar', on_click=del_dialog.close).props('flat color=grey')
                        ui.button('Confirmar Exclusão', on_click=handle_delete).props('unelevated color=red text-color=white')
            del_dialog.open()

        # 5. Diálogo de Confirmação de Exclusão em Lote
        def open_batch_delete_dialog(uids):
            selected_users_objs = [u for u in users_data if u['id'] in uids]
            names_str = ", ".join([u['nome'] for u in selected_users_objs])
            with ui.dialog() as batch_del_dialog, ui.card().classes('w-[420px] q-pa-md bg-slate-900 border border-red-500/30'):
                with ui.column().classes('w-full gap-4 items-center text-center'):
                    ui.icon('warning', color='red', size='3rem').classes('animate-pulse')
                    ui.label('CONFIRMAR EXCLUSÃO EM LOTE').classes('text-white text-md font-black cyber-title')
                    ui.label(f"Tem certeza que deseja excluir o acesso de {len(uids)} operadores selecionados?").classes('text-sm text-grey-4')
                    ui.label(f"Operadores: {names_str}").classes('text-xs text-amber-400 font-mono max-h-24 overflow-y-auto w-full')
                    ui.label('Esta ação removerá definitivamente todos os militares selecionados.').classes('text-xs text-red-400 font-bold')
                    
                    del_error = ui.label('').classes('text-xs text-red w-full')
                    
                    def handle_batch_delete():
                        # SEGURANÇA: Apenas administradores reais podem excluir em lote
                        user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                        if not any(r in user_role for r in ('ADMIN', 'SUPERVISOR', 'GERENTE', 'CHEFE')):
                            ui.notify("⛔ Acesso negado. Apenas administradores podem excluir operadores em lote.", color='negative')
                            return
                        if is_offline:
                            ui.notify(f"[OFFLINE] Removido {len(uids)} operadores!", color='success')
                            for uid in list(uids):
                                for u in list(users_data):
                                    if u['id'] == uid:
                                        users_data.remove(u)
                            uids.clear()
                            batch_del_dialog.close()
                            reload_admin_data()
                            return
                        
                        conn = get_service_db_connection() or get_db_connection()
                        if not conn:
                            ui.notify('Sem conexão com banco de dados', color='red')
                            return
                        
                        try:
                            for u in selected_users_objs:
                                u_id = str(u['id'])
                                raw_nome = str(u.get('nome') or u.get('username') or '').upper()
                                clean_words = [w for w in raw_nome.split() if w not in ('SO', 'SG', 'CB', 'SD', 'MN', 'CMG', 'CF', 'CC', 'CT', '1TEN', '2TEN', 'GM', 'ADMIN', 'ADMINISTRADOR', 'OPERADOR', 'NONE', '1º', '2º', '3º', 'OFICIAL') and not w.isdigit()]
                                clean_name = " ".join(clean_words) if clean_words else raw_nome

                                # 1. Supabase Auth (se UUID)
                                if not u_id.isdigit():
                                    try:
                                        from database import get_bot_db_connection
                                        admin_conn = get_bot_db_connection()
                                        if admin_conn and hasattr(admin_conn, 'auth') and hasattr(admin_conn.auth, 'admin'):
                                            admin_conn.auth.admin.delete_user(u_id)
                                    except Exception as auth_err:
                                        print(f"[AUTH BATCH DELETE WARN] {auth_err}")

                                # 2. Users
                                try:
                                    conn.table('users').delete().or_(f"id.eq.{u_id},username.ilike.{u.get('username')},nome.ilike.%{clean_name}%").execute()
                                except Exception:
                                    pass

                                # 3. Efetivo
                                try:
                                    if u_id.isdigit():
                                        conn.table('efetivo').delete().eq('id', int(u_id)).execute()
                                    if clean_name:
                                        conn.table('efetivo').delete().ilike('nome_guerra', f"%{clean_name}%").execute()
                                    if u.get('email'):
                                        conn.table('efetivo').delete().eq('email', u['email']).execute()
                                except Exception:
                                    pass

                                # 4. RegistrationRequests
                                try:
                                    if clean_name:
                                        conn.table('registration_requests').delete().ilike('nome_guerra', f"%{clean_name}%").execute()
                                except Exception:
                                    pass

                            ui.notify(f"{len(selected_users_objs)} operadores removidos com sucesso!", color='success')

                            uids.clear()
                            data_service.clear_cache()
                            batch_del_dialog.close()
                            reload_admin_data()
                        except Exception as err:
                            del_error.text = f"Erro: {err}"
            
                    # Botões de Ação (dentro da coluna do diálogo)
                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                        ui.button('Cancelar', on_click=batch_del_dialog.close).props('flat color=grey')
                        ui.button('Confirmar Exclusão em Lote', on_click=handle_batch_delete).props('unelevated color=red text-color=white')
            batch_del_dialog.open()

        # 6. Diálogo de Configurações SMTP de E-mail
        def open_smtp_dialog():

            with ui.dialog() as smtp_dialog, ui.card().classes('w-[450px] q-pa-md bg-slate-900 border').style(f'border-color: {THEME["accent"]};'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2 w-full justify-between'):
                        ui.label('📧 CONFIGURAR E-MAIL (SMTP)').classes('text-white text-md font-black cyber-title')
                        ui.icon('mark_email_read', size='1.5rem').style(f'color: {THEME["accent"]}')
                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    ui.label('Insira as credenciais SMTP (Gmail ou Servidor Institucional) para envio de PINs de recuperação, alertas e aniversariantes.').classes('text-grey-4 text-xs')

                    conn = get_service_db_connection() or get_db_connection()
                    cur_host = 'smtp.gmail.com'
                    cur_port = '587'
                    cur_user = 'CGCFNaudiovisual@gmail.com'
                    cur_pass = ''
                    cur_name = 'SisGAB - Gabinete'

                    if conn:
                        try:
                            res_h = conn.table('config').select('valor').eq('chave', 'smtp_host').execute()
                            if res_h.data and res_h.data[0].get('valor'): cur_host = str(res_h.data[0]['valor'])
                            res_p = conn.table('config').select('valor').eq('chave', 'smtp_port').execute()
                            if res_p.data and res_p.data[0].get('valor'): cur_port = str(res_p.data[0]['valor'])
                            res_u = conn.table('config').select('valor').eq('chave', 'smtp_user').execute()
                            if res_u.data and res_u.data[0].get('valor'): cur_user = str(res_u.data[0]['valor'])
                            res_pw = conn.table('config').select('valor').eq('chave', 'smtp_password').execute()
                            if res_pw.data and res_pw.data[0].get('valor'): cur_pass = str(res_pw.data[0]['valor'])
                            res_n = conn.table('config').select('valor').eq('chave', 'smtp_from_name').execute()
                            if res_n.data and res_n.data[0].get('valor'): cur_name = str(res_n.data[0]['valor'])
                        except Exception as e_cfg:
                            print(f"[SMTP LOAD ERR] {e_cfg}")

                    s_host = ui.input('Servidor SMTP (Host)', value=cur_host).props('dark outlined dense w-full')
                    s_port = ui.input('Porta SMTP', value=cur_port).props('dark outlined dense w-full')
                    s_user = ui.input('E-mail Remetente (Usuário)', value=cur_user).props('dark outlined dense w-full')
                    s_pass = ui.input('Senha de App (16 caracteres do Google)', value=cur_pass, password=True).props('dark outlined dense w-full')
                    s_name = ui.input('Nome do Remetente', value=cur_name).props('dark outlined dense w-full')

                    smtp_status = ui.label('').classes('text-xs text-amber-4 text-center w-full')

                    def test_smtp():
                        if not s_user.value or not s_pass.value:
                            smtp_status.text = 'Preencha o e-mail e a senha de app para testar.'
                            return
                        smtp_status.text = 'Conectando ao servidor SMTP...'
                        try:
                            import smtplib, ssl
                            ctx = ssl.create_default_context()
                            with smtplib.SMTP(s_host.value.strip(), int(s_port.value.strip()), timeout=8) as server:
                                server.ehlo()
                                server.starttls(context=ctx)
                                server.login(s_user.value.strip(), s_pass.value.strip())
                            smtp_status.text = ''
                            ui.notify('🟢 Conexão SMTP estabelecida com sucesso!', color='success')
                        except Exception as err:
                            smtp_status.text = f'❌ Falha na conexão: {err}'

                    def save_smtp():
                        try:
                            from database import save_smtp_config
                            save_smtp_config({
                                'smtp_host': s_host.value.strip(),
                                'smtp_port': s_port.value.strip(),
                                'smtp_user': s_user.value.strip(),
                                'smtp_pass': s_pass.value.strip(),
                                'smtp_sender_name': s_name.value.strip(),
                                'smtp_use_tls': True
                            })
                            ui.notify('✅ Configurações SMTP salvas com sucesso!', color='success')
                            smtp_dialog.close()
                        except Exception as err:
                            smtp_status.text = f'Erro ao salvar: {err}'


                    with ui.row().classes('w-full justify-between items-center q-mt-md'):
                        ui.button('🧪 Testar Conexão', on_click=test_smtp).props('outline dense color=amber-9')
                        with ui.row().classes('gap-2'):
                            ui.button('Cancelar', on_click=smtp_dialog.close).props('flat color=grey')
                            ui.button('💾 Salvar', on_click=save_smtp).props('unelevated color=cyan-9 text-color=white')

            smtp_dialog.open()

        # --- FIM DIÁLOGOS ---


        with container:
            with ui.row().classes('w-full justify-between items-center'):
                theme.section_header('Usuários e Permissões', 'Gestão de Usuários, Permissões e Servidor SMTP')
                ui.button('📧 Configurações SMTP / E-mail', on_click=open_smtp_dialog).props('unelevated color=cyan text-color=black bold icon=email').classes('text-xs cyber-glow')

            
            if is_offline:
                with ui.row().classes('w-full items-center q-pa-sm rounded-lg text-caption gap-2').style('background: rgba(255, 152, 0, 0.1); border: 1px solid rgba(255, 152, 0, 0.3); color: #ffb300;'):
                    ui.icon('warning', size='1.2rem')
                    ui.label('Banco de dados Supabase offline ou inacessível. Exibindo dados simulados. Ações serão apenas visuais.').classes('font-bold')

            # --- SEÇÃO 1: SOLICITAÇÕES PENDENTES ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('assignment_ind', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label(f'Solicitações Pendentes ({len(requests_data)})').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    if not requests_data:
                        ui.label('Não há solicitações de acesso pendentes de aprovação.').classes('italic q-py-md text-sm').style(f'color: {THEME["text_dim"]}')
                    else:
                        with ui.column().classes('w-full gap-3'):
                            for req in requests_data:
                                state = {'role': 'militar'}
                                
                                with ui.card().classes('w-full q-pa-sm border hover:border-cyan-500/40 bg-black/20').style(f'border-color: rgba(0, 229, 255, 0.1);'):
                                    with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                                        with ui.column().classes('gap-1'):
                                            ui.label(req.get('nome_completo') or req.get('nome_guerra') or 'Operador').classes('text-subtitle2 font-bold').style(f'color: {THEME["text_main"]}')
                                            with ui.row().classes('gap-4 text-caption').style(f'color: {THEME["text_dim"]}'):
                                                ui.label(f"Guerra: {req.get('nome_guerra', 'N/I')}")
                                                ui.label(f"E-mail: {req.get('email', 'N/I')}")
                                                date_str = req.get('created_at', '')[:10] if req.get('created_at') else ''
                                                if date_str:
                                                    ui.label(f"Solicitado em: {date_str}")
                                        
                                        # Controles de aprovação
                                        with ui.row().classes('items-center gap-3'):
                                            ui.select(
                                                ROLE_OPTIONS, 
                                                value='militar',
                                                label='Papel a Atribuir',
                                                on_change=lambda e, s=state: s.update({'role': e.value})
                                            ).props('dark outlined dense').classes('w-60')
                                            
                                            def process_request(req_id=req['id'], req_email=req.get('email', ''), req_guerra=req.get('nome_guerra', ''), action='', s=state):
                                                # SEGURANÇA: Verificação de privilégios server-side
                                                user_role = str(app.storage.user.get('user_data', {}).get('role', '')).upper()
                                                if user_role not in ('ADMIN', 'SUPERVISOR'):
                                                    ui.notify("⛔ Acesso negado. Apenas administradores ou supervisores podem aprovar/rejeitar solicitações.", color='negative')
                                                    return
                                                if is_offline:
                                                    ui.notify(f"Simulando {action} para o e-mail {req_email}", color='info')
                                                    reload_admin_data()
                                                    return

                                                conn = get_service_db_connection() or get_db_connection()
                                                if not conn:
                                                    ui.notify('Sem conexão com banco de dados', color='red')
                                                    return
                                                
                                                try:
                                                    if action == 'approved':
                                                        req_tg_id = req.get('telegram_id') or None
                                                        for tbl_name in ['RegistrationRequests', 'registration_requests']:
                                                            try:
                                                                conn.table(tbl_name).update({'status': 'approved'}).eq('id', req_id).execute()
                                                            except Exception:
                                                                pass
                                                        
                                                        # Upsert em users e efetivo salvando telegram_id se disponivel
                                                        try:
                                                            conn.table('users').upsert({
                                                                'id': req_id,
                                                                'username': req_email.split('@')[0] if '@' in req_email else req_guerra.lower(),
                                                                'nome': req_guerra,
                                                                'role': s['role'],
                                                                'telegram_id': req_tg_id
                                                            }, on_conflict='id').execute()
                                                        except Exception as u_err:
                                                            print(f"[USERS UPSERT ERR] {u_err}")
                                                        
                                                        try:
                                                            conn.table('efetivo').upsert({
                                                                'nome_guerra': req_guerra,
                                                                'email': req_email,
                                                                'role': s['role'],
                                                                'telegram_id': req_tg_id
                                                            }, on_conflict='nome_guerra').execute()
                                                        except Exception as ef_upsert_err:
                                                            print(f"[EFETIVO UPSERT ERR] {ef_upsert_err}")

                                                        try:
                                                            from database import confirm_supabase_user
                                                            confirm_supabase_user(req_id)
                                                        except Exception as conf_err:
                                                            print(f"[CONFIRM ERR] {conf_err}")
                                                        
                                                        # Notifica o usuário aprovado via Telegram
                                                        try:
                                                            tg_id_to_notify = req_tg_id
                                                            if not tg_id_to_notify:
                                                                user_res = conn.table('users').select('telegram_id, nome').eq('id', req_id).execute()
                                                                if user_res.data and user_res.data[0].get('telegram_id'):
                                                                    tg_id_to_notify = user_res.data[0]['telegram_id']
                                                            
                                                            if tg_id_to_notify:
                                                                from notifications_manager import notify_telegram
                                                                msg_tg = (
                                                                    f"✅ *Acesso ao SisGAB Aprovado!*\n\n"
                                                                    f"Olá, *{req_guerra.upper()}*! Seu acesso foi aprovado pelo administrador.\n\n"
                                                                    f"🔑 Papel atribuído: `{s['role']}`\n"
                                                                    f"📱 Você já pode usar o bot normalmente (/menu).\n"
                                                                    f"🌐 Acesse também o sistema web para operações avançadas."
                                                                )
                                                                notify_telegram(msg_tg, "system", custom_chat_id=str(tg_id_to_notify))
                                                        except Exception as notif_err:
                                                            print(f"[PANEL NOTIFY APPROVED ERR] {notif_err}")
                                                        ui.notify(f"Usuário {req_guerra} aprovado como {s['role'].upper()}!", color='success')
                                                    else:
                                                        conn.table('registration_requests').update({'status': 'rejected'}).eq('id', req_id).execute()
                                                        ui.notify(f"Solicitação de {req_guerra} rejeitada.", color='warning')
                                                    
                                                    data_service.clear_cache()
                                                    reload_admin_data()
                                                except Exception as err:
                                                    ui.notify(f"Erro ao processar solicitação: {err}", color='red')

                                            ui.button(
                                                'Rejeitar', 
                                                on_click=lambda r_id=req['id'], r_email=req['email'], r_g=req['nome_guerra']: process_request(r_id, r_email, r_g, 'rejected')
                                            ).props('outline dense').style(f'color: {THEME["danger"]}; border-color: rgba(255, 23, 68, 0.4);')
                                            
                                            ui.button(
                                                'Aprovar Acesso', 
                                                on_click=lambda r_id=req['id'], r_email=req['email'], r_g=req['nome_guerra']: process_request(r_id, r_email, r_g, 'approved')
                                            ).props('unelevated dense').style(f'background: {THEME["success"]}; color: #0b0f19; font-weight: bold;').classes('cyber-glow')

            # --- SEÇÃO 2: USUÁRIOS ATIVOS (CRUD COMPLETO) ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center justify-between w-full'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('people', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label(f'Operadores Cadastrados ({len(users_data)})').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        
                        with ui.row().classes('gap-2 items-center'):
                            # Selecionar/Desselecionar Todos
                            all_ids = {u['id'] for u in users_data}
                            all_selected = all_ids == selected_user_ids if all_ids else False
                            
                            def toggle_select_all():
                                if all_selected:
                                    selected_user_ids.clear()
                                else:
                                    selected_user_ids.update(all_ids)
                                reload_admin_data()
                                
                            ui.button(
                                '⬜ DESSELECIONAR TODOS' if all_selected else '☑️ SELECIONAR TODOS',
                                on_click=toggle_select_all
                            ).props('outline dense color=cyan').classes('text-xs px-3 py-1.5')

                            # Botão de exclusão em lote
                            batch_count = len(selected_user_ids)
                            batch_del_btn = ui.button(
                                f'🗑️ EXCLUIR SELECIONADOS ({batch_count})',
                                on_click=lambda: open_batch_delete_dialog(selected_user_ids)
                            ).props('unelevated dense color=red').classes('text-xs px-3 py-1.5')
                            # Botão de configuração SMTP de e-mail
                            ui.button(
                                '📧 CONFIGURAÇÕES SMTP',
                                on_click=open_smtp_dialog
                            ).props('unelevated dense color=amber-9 text-color=black').classes('text-xs px-3 py-1.5 font-bold')

                            # Botão administrativo para novo cadastro direto
                            ui.button(
                                '➕ CADASTRAR OPERADOR',
                                on_click=open_create_dialog
                            ).props('unelevated dense').style(f'background: {THEME["accent"]}; color: #0b0f19; font-weight: bold;').classes('cyber-glow text-xs px-3 py-1.5')


                    # Filtros rápidos por papel/categoria
                    with ui.row().classes('w-full items-center justify-between gap-2 q-my-xs flex-wrap text-xs'):
                        with ui.row().classes('items-center gap-1.5 flex-wrap'):
                            ui.label('🔍 Filtrar Categoria:').classes('text-grey-4 font-bold mr-1')
                            
                            current_filter = app.storage.user.get('admin_filter_role', 'TODOS')
                            
                            def set_role_filter(r_val):
                                app.storage.user['admin_filter_role'] = r_val
                                reload_admin_data()

                            filter_options = [
                                ('TODOS', 'Todos'),
                                ('admin', '👑 Admins'),
                                ('comsoc', '📸 COMSOC/Design'),
                                ('praca_gab', '📜 Sargenteação'),
                                ('militar', '⚓ Militares')
                            ]
                            for f_val, f_lbl in filter_options:
                                is_sel = (current_filter == f_val)
                                f_props = 'unelevated dense color=cyan text-color=black font-bold' if is_sel else 'outline dense color=grey-6 text-color=white'
                                ui.button(f_lbl, on_click=lambda _, v=f_val: set_role_filter(v)).props(f_props).classes('text-[11px] px-2 py-0.5')

                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    if not users_data:
                        ui.label('Nenhum operador cadastrado.').classes('italic q-py-md text-sm').style(f'color: {THEME["text_dim"]}')
                    else:
                        try:
                            from telegram_bot.utils import sort_efetivo_by_rank
                            users_data = sort_efetivo_by_rank(users_data)
                        except Exception:
                            pass

                        with ui.column().classes('w-full gap-3'):
                            for u_idx, u in enumerate(users_data, 1):
                                with ui.card().classes('w-full q-pa-sm border bg-black/10 hover:border-cyan-500/20 transition-all').style(f'border-color: rgba(0, 229, 255, 0.1);'):
                                    with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                                        # 1. Informações básicas + Foto de Perfil Quadrada
                                        with ui.row().classes('items-center gap-3 col-grow'):
                                            # Checkbox para seleção em lote
                                            def on_checkbox_change(e, uid=u['id']):
                                                if e.value:
                                                    selected_user_ids.add(uid)
                                                else:
                                                    selected_user_ids.discard(uid)
                                                count = len(selected_user_ids)
                                                batch_del_btn.set_visibility(count > 0)
                                                batch_del_btn.text = f'🗑️ EXCLUIR SELECIONADOS ({count})'
                                            
                                            ui.checkbox(
                                                value=u['id'] in selected_user_ids,
                                                on_change=on_checkbox_change
                                            ).props('dense dark color=red')

                                            # Foto de Perfil Tática
                                            user_photo = u.get('url_foto') or ''
                                            user_avatar_src = user_photo if isinstance(user_photo, str) and user_photo.startswith('http') else 'https://cdn.quasar.dev/img/boy-avatar.png'
                                            u_role_raw = str(u.get('role', 'praca_gab')).lower()
                                            role_color = '#00e676' if u_role_raw == 'admin' else '#00b0ff' if u_role_raw == 'supervisor' else '#ab47bc' if u_role_raw == 'oficial_gab' else '#7e57c2' if u_role_raw == 'oficial' else '#29b6f6' if u_role_raw == 'comsoc' else '#f06292' if u_role_raw == 'comsoc_design' else '#ff9100'
                                            ui.element('div').classes('shadow border shrink-0').style(
                                                f"width: 48px; height: 48px; background-image: url('{user_avatar_src}'); "
                                                f"background-size: cover; background-repeat: no-repeat; "
                                                f"background-position: center; background-color: #050b14; "
                                                f"border: 2px solid {role_color}; border-radius: 4px;"
                                            )
                                            with ui.column().classes('gap-0.5'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(u['nome']).classes('font-black text-sm uppercase').style(f'color: {THEME["text_main"]}')
                                                    role_text = ROLE_LABELS.get(u_role_raw, 'Praça do Gabinete').split(' (')[0]
                                                    ui.label(role_text.upper()).classes('text-[9px] font-bold px-1.5 py-0.5 rounded border').style(
                                                        f"color: {role_color}; border-color: {role_color}40; background: {role_color}10;"
                                                    )
                                                    ui.label(f"🎖️ Precedência: #{u_idx}").classes('text-[9px] font-bold px-1.5 py-0.5 rounded border border-amber-500/40 text-amber-400 bg-amber-500/10').tooltip('Ordem de precedência militar no grupo')
                                                with ui.row().classes('items-center gap-4 text-[11px]').style(f'color: {THEME["text_dim"]}'):
                                                    ui.label(f"User: {u['username']}")
                                                    if u.get('telegram_id'):
                                                        ui.label(f"TG ID: {u['telegram_id']}").classes('font-mono text-cyan-400')
                                                    else:
                                                        ui.label("TG ID: não associado").classes('italic')
                                        
                                        # 2. Ações Administrativas (Editar Perfil, Alterar Senha, Excluir)
                                        with ui.row().classes('items-center gap-2'):
                                            # Editar Perfil
                                            ui.button(
                                                icon='edit',
                                                on_click=lambda _, cur_u=u: open_edit_dialog(cur_u)
                                            ).props('flat round dense color=primary').classes('text-xs').style('background: rgba(0, 229, 255, 0.05);').tooltip('Editar Perfil')
                                            
                                            # Alterar Senha
                                            ui.button(
                                                icon='vpn_key',
                                                on_click=lambda _, cur_u=u: open_password_dialog(cur_u)
                                            ).props('flat round dense color=amber-9').classes('text-xs').style('background: rgba(255, 193, 7, 0.05);').tooltip('Redefinir Senha')
                                            
                                            # Excluir
                                            ui.button(
                                                icon='delete',
                                                on_click=lambda _, cur_u=u: open_delete_dialog(cur_u)
                                            ).props('flat round dense color=red').classes('text-xs').style('background: rgba(255, 23, 68, 0.05);').tooltip('Excluir Operador')

            # --- SEÇÃO 3: CONFIGURAÇÃO GOOGLE DRIVE ---
            with theme.card_base().classes('w-full q-pa-md q-mt-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('folder_shared', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('📂 Integração Google Drive').classes('text-lg font-bold cyber-title')
                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    import drive_service
                    
                    db = get_service_db_connection() or get_db_connection()
                    cur_sa = ""
                    cur_folder = ""
                    cur_pastas_mae = []
                    cur_wm_enabled = False
                    cur_wm_text = "COMSOC / CGCFN"

                    def _safe_get_config(key, default=""):
                        if not db: return default
                        try:
                            res = db.table('config').select('valor').eq('chave', key).execute()
                            if res and res.data and res.data[0].get('valor'):
                                return res.data[0]['valor']
                        except Exception:
                            pass
                        return default

                    cur_sa = _safe_get_config('drive_service_account_json', '')
                    cur_folder = _safe_get_config('drive_pasta_mae_id', '')
                    cur_wm_enabled = _safe_get_config('drive_watermark_enabled', 'False') == 'True'
                    cur_wm_text = _safe_get_config('drive_watermark_text', 'COMSOC / CGCFN')
                    
                    pastas_raw = _safe_get_config('drive_pastas_mae_json', '[]')
                    try:
                        cur_pastas_mae = json.loads(pastas_raw)
                    except Exception:
                        cur_pastas_mae = []

                    if not cur_pastas_mae and cur_folder:
                        cur_pastas_mae = [{'id': '1', 'nome': 'Pasta Mãe Principal', 'folder_id': cur_folder, 'padrao': True}]

                    in_sa_json = ui.textarea('JSON da Service Account', value=cur_sa).props('dark outlined w-full rows=3').classes('w-full text-xs font-mono')
                    
                    # 📁 GERENCIADOR DE MULTIPLAS PASTAS MÃE
                    ui.label('📁 Pastas Mãe do Google Drive:').classes('text-xs font-bold text-cyan q-mt-sm')
                    
                    pastas_container = ui.column().classes('w-full gap-2')

                    def render_pastas_mae_list():
                        pastas_container.clear()
                        with pastas_container:
                            if not cur_pastas_mae:
                                ui.label('Nenhuma Pasta Mãe cadastrada. Clique abaixo para adicionar.').classes('text-xs text-grey-4 italic')
                            else:
                                for idx, p in enumerate(cur_pastas_mae):
                                    with ui.card().classes('w-full q-pa-xs px-3 no-shadow rounded-lg border').style(
                                        f'background: {"rgba(0, 229, 255, 0.08)" if p.get("padrao") else "rgba(255, 255, 255, 0.03)"}; '
                                        f'border: 1px solid {"#00e5ff" if p.get("padrao") else "rgba(255, 255, 255, 0.1)"};'
                                    ):
                                        with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                                            with ui.column().classes('gap-0 flex-grow'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(p.get('nome', 'Pasta Mãe')).classes('text-xs font-bold text-white')
                                                    if p.get('padrao'):
                                                        ui.badge('PADRÃO', color='cyan').classes('text-[10px]')
                                                ui.label(f"ID: {p.get('folder_id', '')}").classes('text-[10px] text-grey-4 font-mono')

                                            with ui.row().classes('items-center gap-1'):
                                                if not p.get('padrao'):
                                                    def set_default(p_idx=idx):
                                                        for item in cur_pastas_mae:
                                                            item['padrao'] = False
                                                        cur_pastas_mae[p_idx]['padrao'] = True
                                                        render_pastas_mae_list()
                                                        ui.notify('Pasta padrão atualizada!', color='info')
                                                    ui.button('⭐ Tornar Padrão', on_click=set_default).props('flat dense color=cyan size=xs')

                                                def edit_pasta(p_idx=idx):
                                                    item = cur_pastas_mae[p_idx]
                                                    with ui.dialog() as dlg_e, ui.card().classes('w-[450px] max-w-[90vw] q-pa-md'):
                                                        ui.label('Editar Pasta Mãe').classes('text-sm font-bold text-white q-mb-sm')
                                                        e_nome = ui.input('Nome da Pasta', value=item.get('nome', '')).props('dark outlined dense w-full')
                                                        e_id = ui.input('ID no Drive', value=item.get('folder_id', '')).props('dark outlined dense w-full')
                                                        def salvar_e():
                                                            if not e_nome.value or not e_id.value:
                                                                ui.notify('Preencha nome e ID!', color='warning')
                                                                return
                                                            item['nome'] = e_nome.value.strip()
                                                            item['folder_id'] = e_id.value.strip()
                                                            dlg_e.close()
                                                            render_pastas_mae_list()
                                                        with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                                            ui.button('Cancelar', on_click=dlg_e.close).props('flat color=grey')
                                                            ui.button('Salvar', on_click=salvar_e).props('unelevated color=cyan')
                                                    dlg_e.open()
                                                ui.button('✏️', on_click=edit_pasta).props('flat round dense color=grey size=xs').tooltip('Editar')

                                                def delete_pasta(p_idx=idx):
                                                    cur_pastas_mae.pop(p_idx)
                                                    if cur_pastas_mae and not any(x.get('padrao') for x in cur_pastas_mae):
                                                        cur_pastas_mae[0]['padrao'] = True
                                                    render_pastas_mae_list()
                                                    ui.notify('Pasta removida.', color='info')
                                                ui.button('🗑️', on_click=delete_pasta).props('flat round dense color=red size=xs').tooltip('Excluir')

                    render_pastas_mae_list()

                    def add_nova_pasta_mae():
                        with ui.dialog() as dlg_add, ui.card().classes('w-[450px] max-w-[90vw] q-pa-md'):
                            ui.label('➕ Adicionar Nova Pasta Mãe').classes('text-sm font-bold text-white q-mb-sm')
                            a_nome = ui.input('Nome da Pasta (ex: Acervo Histórico)', placeholder='Ex: Pasta Geral COMSOC').props('dark outlined dense w-full')
                            a_id = ui.input('ID da Pasta no Google Drive', placeholder='Cole o ID do link do Drive').props('dark outlined dense w-full')
                            a_padrao = ui.checkbox('Definir como Pasta Padrão').props('dark')
                            
                            def salvar_add():
                                if not a_nome.value or not a_id.value:
                                    ui.notify('Preencha o Nome e o ID da pasta!', color='warning')
                                    return
                                new_item = {
                                    'id': str(len(cur_pastas_mae) + 1),
                                    'nome': a_nome.value.strip(),
                                    'folder_id': a_id.value.strip(),
                                    'padrao': a_padrao.value or (len(cur_pastas_mae) == 0)
                                }
                                if new_item['padrao']:
                                    for x in cur_pastas_mae:
                                        x['padrao'] = False
                                cur_pastas_mae.append(new_item)
                                dlg_add.close()
                                render_pastas_mae_list()
                                ui.notify('Nova Pasta Mãe adicionada!', color='success')

                            with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                ui.button('Cancelar', on_click=dlg_add.close).props('flat color=grey')
                                ui.button('Adicionar', on_click=salvar_add).props('unelevated color=cyan')
                        dlg_add.open()

                    ui.button('➕ Adicionar Pasta Mãe', on_click=add_nova_pasta_mae).props('outline color=cyan size=sm dense').classes('q-mb-sm')
                    
                    with ui.row().classes('w-full items-center gap-4 q-mt-xs'):
                        in_wm_enabled = ui.checkbox('Marca d\'Água Automática na SELEÇÃO', value=cur_wm_enabled).props('dark')
                        in_wm_text = ui.input('Texto da Marca d\'Água', value=cur_wm_text).props('dark outlined dense').classes('col-grow')

                    drive_status = ui.label('').classes('text-xs text-amber font-bold q-mt-xs')

                    def test_drive_connection():
                        drive_status.text = 'Testando conexão...'
                        ui.timer(0.1, lambda: (
                            drive_status.set_text(
                                'Conexão OK!' if drive_service.testar_conexao() else 'Erro na conexão.'
                            )
                        ), once=True)

                    def save_drive_config():
                        db_s = get_service_db_connection() or get_db_connection()
                        if db_s:
                            try:
                                # Identifica a pasta padrão
                                padrao_folder_id = ""
                                for item in cur_pastas_mae:
                                    if item.get('padrao'):
                                        padrao_folder_id = item.get('folder_id', '')
                                        break
                                if not padrao_folder_id and cur_pastas_mae:
                                    padrao_folder_id = cur_pastas_mae[0].get('folder_id', '')

                                # Upsert usando chave e valor com on_conflict='chave'
                                db_s.table('config').upsert({'chave': 'drive_service_account_json', 'valor': in_sa_json.value.strip()}, on_conflict='chave').execute()
                                db_s.table('config').upsert({'chave': 'drive_pasta_mae_id', 'valor': padrao_folder_id}, on_conflict='chave').execute()
                                db_s.table('config').upsert({'chave': 'drive_pastas_mae_json', 'valor': json.dumps(cur_pastas_mae)}, on_conflict='chave').execute()
                                db_s.table('config').upsert({'chave': 'drive_watermark_enabled', 'valor': str(in_wm_enabled.value)}, on_conflict='chave').execute()
                                db_s.table('config').upsert({'chave': 'drive_watermark_text', 'valor': in_wm_text.value.strip()}, on_conflict='chave').execute()

                                drive_service.reset_drive_service()
                                ui.notify('✅ Configurações do Drive salvas com sucesso!', color='success')
                            except Exception as e_save:
                                ui.notify(f'Erro ao salvar: {e_save}', color='negative')
                        else:
                            ui.notify('Sem conexão com banco de dados', color='negative')

                    with ui.row().classes('w-full gap-2 justify-end q-mt-md'):
                        ui.button('🔗 Testar Conexão com Drive', on_click=test_drive_connection).props('outline color=cyan text-color=white bold')
                        ui.button('💾 Salvar Configurações do Drive', on_click=save_drive_config).props('unelevated color=green text-color=white bold')


    # Primeiro carregamento
    reload_admin_data()
