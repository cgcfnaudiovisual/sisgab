from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection
from services import data_service

THEME = theme.colors

# Opções de papéis/roles no sistema
ROLE_OPTIONS = {
    'admin': 'Administrador (Acesso Total)',
    'supervisor': 'Supervisor COMSOC',
    'oficial_gab': 'Oficial do Gabinete',
    'oficial': 'Oficial da OM',
    'praca_gab': 'Praça do Gabinete',
    'comsoc': 'Equipe COMSOC (Fotografia/Vídeo)',
    'comsoc_design': 'Equipe COMSOC (Edições Gráficas/Artes)',
    'operador': 'Operador COMSOC',
    'militar': 'Militar em Geral (Autoatendimento)',
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
        'web': '✅ GESTÃO & HOMOLOGAÇÃO: Homologação e Tramitação de Pautas, Modulo de Presença & Pronto CheGab, Agenda Geral, Cautelas e Mídia TV.',
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
        'title': '📜 Praça do Gabinete',
        'web': '✅ SARGENTEARIA & OPERACIONAL: Registrar Presença Diária, Apoiar Chamada, Cautela de Equipamentos e Agenda.',
        'telegram': '✅ SARGENTEARIA: Dar Presença Diária, Gerar /pronto CheGab, Criar Demandas e Cautelas.'
    },
    'comsoc': {
        'title': '📸 Equipe COMSOC (Fotografia/Vídeo)',
        'web': '🎨 EQUIPE COMSOC / PRODUÇÃO: Criar Demandas, Tramitação, Cautelas de Equipamentos, Estoque de Brindes e Mídia TV.',
        'telegram': '🎨 COMSOC: Criar Demandas com Botões, Dar Presença, Cautelas Ativas e Digerir Pauta (IA).'
    },
    'comsoc_design': {
        'title': '🎨 Equipe COMSOC (Edições Gráficas/Artes)',
        'web': '🎨 DESIGN & ARTES: Modulo de Produção Gráfica, Galeria de Artes, Demandas COMSOC e Brindes.',
        'telegram': '🎨 DESIGN: Criar Demandas, Digerir IA, Consultar Agenda e Dar Presença.'
    },
    'operador': {
        'title': '⚙️ Operador COMSOC',
        'web': '⚙️ OPERADOR COMSOC: Painel de Tramitação, Demandas, Cautelas, Presença Diária e Galeria de Fotos.',
        'telegram': '⚙️ OPERADOR: Criar Demandas por Botões, Dar Presença, /pronto, IA e Cautelas.'
    },
    'militar': {
        'title': '⚓ Militar Externo / Outras OMs (Acesso Mínimo)',
        'web': '⚓ ACESSO MÍNIMO: Preencher Nova Solicitação de Cobertura COMSOC, Consultar Agenda Geral e Buscar Fotos por Reconhecimento Facial.',
        'telegram': '⚓ ACESSO MÍNIMO: Criar Demanda por Botões, Consultar Agenda Semanal, Enviar Selfie e Buscar Fotos por Reconhecimento Facial.'
    },
    'compel': {
        'title': '⚓ Militar / Efetivo em Geral',
        'web': '⚓ ACESSO MÍNIMO: Preencher Nova Solicitação de Cobertura, Consultar Agenda e Reconhecimento Facial.',
        'telegram': '⚓ ACESSO MÍNIMO: Criar Demanda por Botões, Consultar Agenda e Buscar Fotos.'
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
                # Solicitações pendentes reais
                req_res = db_conn.table('registration_requests').select('*').in_('status', ['pending', 'pendente']).execute()
                requests_data = req_res.data if req_res.data else []

                # Usuários e Efetivo reais
                users_res = db_conn.table('users').select('*').execute()
                users_data = users_res.data if users_res.data else []
                
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
                            users_data.append({
                                'id': str(ef.get('id')),
                                'username': guerra.lower() if guerra else 'militar',
                                'nome': f"{pg} {guerra}".strip() if pg else guerra,
                                'role': ef.get('role', 'praca_gab'),
                                'telegram_id': ef.get('telegram_id', ''),
                                'url_foto': ef.get('url_foto', ''),
                                'posto_grad': pg
                            })
                            if email: existing_emails.add(email)
                            if tg_id: existing_tgs.add(tg_id)
                            if guerra_clean: existing_clean_names.add(guerra_clean)


                # Preenche posto_grad para os usuários da tabela users
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

                # Ordena os operadores: COMSOC/Admin primeiro, depois por Antiguidade, depois por Nome
                def sort_users(u):
                    role = str(u.get('role', 'compel')).strip().lower()
                    is_comsoc = role in ('admin', 'supervisor', 'comsoc', 'comsoc_design', 'operador')
                    group_priority = 0 if is_comsoc else 1
                    
                    pg = u.get('posto_grad') or ''
                    if not pg:
                        parts = str(u.get('nome', '')).split()
                        pg = parts[0] if parts else ''
                    
                    seniority = get_rank_seniority(pg)
                    nome_guerra = str(u.get('nome', '')).upper()
                    return (group_priority, seniority, nome_guerra)
                
                users_data = sorted(users_data, key=sort_users)
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
                    
                    c_role = ui.select(ROLE_OPTIONS, label='Papel do Usuário', value='compel').props('dark outlined dense w-full')
                    
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
                            
                            if is_offline:
                                ui.notify(f"[OFFLINE] Novo operador {c_nome.value.upper()} cadastrado!", color='success')
                                users_data.append({
                                    'id': f'mock-uid-{len(users_data)+1}',
                                    'username': c_email.value.split('@')[0],
                                    'nome': c_nome.value.upper(),
                                    'role': c_role.value,
                                    'telegram_id': c_tg.value or '',
                                    'url_foto': c_foto.value or ''
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

                            # Insere na tabela users
                            try:
                                try:
                                    conn.table('users').insert({
                                        'id': auth_id,
                                        'username': c_email.value.split('@')[0],
                                        'nome': c_nome.value.upper(),
                                        'role': c_role.value,
                                        'telegram_id': c_tg.value or None,
                                        'url_foto': c_foto.value or None,
                                        'email': c_email.value
                                    }).execute()
                                except Exception as e_mail_err:
                                    # Fallback: salva sem a coluna email
                                    conn.table('users').insert({
                                        'id': auth_id,
                                        'username': c_email.value.split('@')[0],
                                        'nome': c_nome.value.upper(),
                                        'role': c_role.value,
                                        'telegram_id': c_tg.value or None,
                                        'url_foto': c_foto.value or None
                                    }).execute()
                            except Exception as db_err:
                                if 'url_foto' in str(db_err):
                                    # Fallback: salva sem a coluna url_foto
                                    conn.table('users').insert({
                                        'id': auth_id,
                                        'username': c_email.value.split('@')[0],
                                        'nome': c_nome.value.upper(),
                                        'role': c_role.value,
                                        'telegram_id': c_tg.value or None
                                    }).execute()
                                    ui.notify('Operador cadastrado sem foto. Adicione a coluna url_foto no Supabase!', color='warning', duration=6)
                                else:
                                    raise db_err
                            
                            # Cria também na tabela efetivo para manter integridade
                            try:
                                try:
                                    conn.table('efetivo').insert({
                                        'telegram_id': c_tg.value or None,
                                        'nome_guerra': c_nome.value.upper(),
                                        'email': c_email.value,
                                        'senha_hash': pwd_hash,
                                        'role': c_role.value,
                                        'url_foto': c_foto.value or None
                                    }).execute()
                                except Exception as db_err:
                                    if 'url_foto' in str(db_err):
                                        conn.table('efetivo').insert({
                                            'telegram_id': c_tg.value or None,
                                            'nome_guerra': c_nome.value.upper(),
                                            'email': c_email.value,
                                            'senha_hash': pwd_hash,
                                            'role': c_role.value
                                        }).execute()
                                    else:
                                        raise db_err
                            except Exception as db_err:
                                print(f"[DB WARN] Sincronização parcial em efetivo: {db_err}")
                            
                            ui.notify(f"Operador {c_nome.value.upper()} cadastrado com sucesso!", color='success')
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
                    e_role = ui.select(ROLE_OPTIONS, label='Papel do Usuário', value=user_role_val).props('dark outlined dense w-full')
                    
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
                        
                        if is_offline:
                            ui.notify(f"[OFFLINE] Dados de {user['username']} atualizados!", color='success')
                            user['nome'] = nome_final
                            user['username'] = e_unm.value
                            user['telegram_id'] = e_tg.value or ''
                            user['url_foto'] = e_foto.value or ''
                            user['role'] = e_role.value
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

                            # 2. Atualiza a tabela users de forma segura
                            user_payload = {
                                'nome': nome_final,
                                'posto': e_posto.value,
                                'username': e_unm.value,
                                'telegram_id': e_tg.value or None,
                                'url_foto': e_foto.value or None,
                                'role': e_role.value
                            }
                            if e_email.value:
                                user_payload['email'] = e_email.value.strip()

                            if is_uuid:
                                try:
                                    conn.table('users').update(user_payload).eq('id', uid_str).execute()
                                except Exception as u_err:
                                    if 'email' in user_payload:
                                        user_payload.pop('email')
                                        conn.table('users').update(user_payload).eq('id', uid_str).execute()
                            else:
                                try:
                                    if user_email:
                                        conn.table('users').update(user_payload).eq('email', user_email).execute()
                                    else:
                                        conn.table('users').update(user_payload).eq('username', user.get('username')).execute()
                                except Exception as u_err_non_uuid:
                                    print(f"[USERS UPDATE NON-UUID WARN] {u_err_non_uuid}")

                            # 3. Tenta manter a integridade da tabela efetivo
                            try:
                                update_fields = {
                                    'nome_guerra': nome_final,
                                    'posto': e_posto.value,
                                    'posto_grad': e_posto.value,
                                    'telegram_id': e_tg.value or None,
                                    'role': e_role.value,
                                    'email': e_email.value or None,
                                    'url_foto': e_foto.value or None
                                }
                                ef_query = conn.table('efetivo').update(update_fields)
                                if not is_uuid and uid_str.isdigit():
                                    ef_query.eq('id', int(uid_str)).execute()
                                elif user_email:
                                    ef_query.eq('email', user_email).execute()
                                elif user.get('telegram_id'):
                                    ef_query.eq('telegram_id', user.get('telegram_id')).execute()
                                else:
                                    ef_query.eq('nome_guerra', user.get('nome', '').upper()).execute()
                            except Exception as sync_err:
                                print(f"[DB WARN] Erro ao sincronizar efetivo: {sync_err}")
                            
                            ui.notify(f"Cadastro de {nome_final} atualizado!", color='success')
                            data_service.clear_cache()
                            edit_dialog.close()
                            reload_admin_data()
                        except Exception as err:
                            e_error.text = f"Erro: {err}"
                            
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
                        if not conn:
                            ui.notify('Sem conexão com o banco', color='red')
                            return
                        try:
                            configs = [
                                {'chave': 'smtp_host', 'valor': s_host.value.strip()},
                                {'chave': 'smtp_port', 'valor': s_port.value.strip()},
                                {'chave': 'smtp_user', 'valor': s_user.value.strip()},
                                {'chave': 'smtp_password', 'valor': s_pass.value.strip()},
                                {'chave': 'smtp_from_name', 'valor': s_name.value.strip()},
                            ]
                            for item in configs:
                                conn.table('config').upsert(item).execute()
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
                                state = {'role': 'compel'}
                                
                                with ui.card().classes('w-full q-pa-sm border hover:border-cyan-500/40 bg-black/20').style(f'border-color: rgba(0, 229, 255, 0.1);'):
                                    with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                                        with ui.column().classes('gap-1'):
                                            ui.label(req['nome_completo']).classes('text-subtitle2 font-bold').style(f'color: {THEME["text_main"]}')
                                            with ui.row().classes('gap-4 text-caption').style(f'color: {THEME["text_dim"]}'):
                                                ui.label(f"Guerra: {req['nome_guerra']}")
                                                ui.label(f"E-mail: {req['email']}")
                                                date_str = req.get('created_at', '')[:10] if req.get('created_at') else ''
                                                if date_str:
                                                    ui.label(f"Solicitado em: {date_str}")
                                        
                                        # Controles de aprovação
                                        with ui.row().classes('items-center gap-3'):
                                            ui.select(
                                                ROLE_OPTIONS, 
                                                value='compel',
                                                label='Papel a Atribuir',
                                                on_change=lambda e, s=state: s.update({'role': e.value})
                                            ).props('dark outlined dense').classes('w-60')
                                            
                                            def process_request(req_id=req['id'], req_email=req['email'], req_guerra=req['nome_guerra'], action='', s=state):
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
                                                        conn.table('registration_requests').update({'status': 'approved'}).eq('id', req_id).execute()
                                                        
                                                        # Upsert em users e efetivo salvando telegram_id se disponivel
                                                        conn.table('users').upsert({
                                                            'id': req_id,
                                                            'username': req_email.split('@')[0],
                                                            'nome': req_guerra,
                                                            'role': s['role'],
                                                            'telegram_id': req_tg_id
                                                        }, on_conflict='id').execute()
                                                        
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


                    ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                    if not users_data:
                        ui.label('Nenhum operador cadastrado.').classes('italic q-py-md text-sm').style(f'color: {THEME["text_dim"]}')
                    else:
                        with ui.column().classes('w-full gap-3'):
                            for u in users_data:
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
                                            role_color = '#00e676' if u.get('role') == 'admin' else '#00b0ff' if u.get('role') == 'supervisor' else '#e040fb' if u.get('role') == 'comcia' else '#ff9100' if u.get('role') == 'aluno' else '#d500f9' if u.get('role') == 'ajosca' else '#90a4ae'
                                            ui.element('div').classes('shadow border shrink-0').style(
                                                f"width: 48px; height: 48px; background-image: url('{user_avatar_src}'); "
                                                f"background-size: cover; background-repeat: no-repeat; "
                                                f"background-position: center; background-color: #050b14; "
                                                f"border: 2px solid {role_color}; border-radius: 4px;"
                                            )
                                            with ui.column().classes('gap-0.5'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(u['nome']).classes('font-black text-sm uppercase').style(f'color: {THEME["text_main"]}')
                                                    role_text = ROLE_OPTIONS.get(u.get('role', 'compel'), 'Compel').split(' (')[0]
                                                    ui.label(role_text.upper()).classes('text-[9px] font-bold px-1.5 py-0.5 rounded border').style(
                                                        f"color: {role_color}; border-color: {role_color}40; background: {role_color}10;"
                                                    )
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
                                            ).props('flat round dense color=primary').classes('text-xs').style('background: rgba(0, 229, 255, 0.05);')
                                            ui.tooltip('Editar Perfil')
                                            
                                            # Alterar Senha
                                            ui.button(
                                                icon='vpn_key',
                                                on_click=lambda _, cur_u=u: open_password_dialog(cur_u)
                                            ).props('flat round dense color=amber-9').classes('text-xs').style('background: rgba(255, 193, 7, 0.05);')
                                            ui.tooltip('Redefinir Senha')
                                            
                                            # Excluir
                                            ui.button(
                                                icon='delete',
                                                on_click=lambda _, cur_u=u: open_delete_dialog(cur_u)
                                            ).props('flat round dense color=red').classes('text-xs').style('background: rgba(255, 23, 68, 0.05);')
                                            ui.tooltip('Excluir Operador')

    # Primeiro carregamento
    reload_admin_data()
