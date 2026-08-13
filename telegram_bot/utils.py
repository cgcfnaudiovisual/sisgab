import unicodedata
import contextvars
import re
from datetime import datetime
from database import get_bot_db_connection as get_db_connection, get_db_connection as get_user_db_connection
from .client import chat_states

# Caches e Contextos para permissões dinâmicas no menu do Telegram
current_user_id = contextvars.ContextVar('current_user_id', default=None)
USER_PERMISSIONS_CACHE = {}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()

def student_matches(al: dict, query_normalized: str) -> bool:
    if not query_normalized:
        return False
    num = normalize_text(str(al.get('numero_interno', '')))
    nome = normalize_text(str(al.get('nome_guerra', '')))
    nome_comp = normalize_text(str(al.get('nome_completo', '')))
    
    if query_normalized in num or num.endswith("-" + query_normalized) or num.endswith(query_normalized):
        return True
        
    query_words = query_normalized.split()
    if not query_words:
        return False
        
    full_name_text = f"{nome} {nome_comp}"
    return all(word in full_name_text for word in query_words)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f"\\{char}")
    return text

def format_health_report(records, title) -> str:
    if not records:
        return f"📈 **{escape_markdown(title)}**\n\n🟢 Nenhum registro de saúde encontrado para este filtro."
    
    records_sorted = sorted(records, key=lambda r: natural_sort_key(r.get('numero_interno', '')))
    
    msg = f"📈 **{escape_markdown(title)}**\n"
    msg += f"Total de casos: {len(records)}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    categories = {
        'enfermaria': [],
        'dispensa': [],
        'licenca': [],
        'outro': []
    }
    
    for r in records_sorted:
        cat = r.get('categoria') or 'outro'
        if cat in categories:
            categories[cat].append(r)
        else:
            categories['outro'].append(r)
            
    cat_labels = {
        'enfermaria': '🏥 ENFERMARIA / INTERNAÇÃO',
        'dispensa': '📋 DISPENSAS MÉDICAS',
        'licenca': '🏠 LICENÇAS AUTORIZADAS',
        'outro': '❓ OUTRAS ALTERAÇÕES'
    }
    
    hoje_str = datetime.now().strftime('%Y-%m-%d')
    
    for cat_key, cat_records in categories.items():
        if not cat_records:
            continue
        msg += f"🔹 **{cat_labels[cat_key]}** ({len(cat_records)}):\n"
        for r in cat_records:
            name = escape_markdown(str(r.get('nome_guerra', '')).upper())
            num = escape_markdown(str(r.get('numero_interno', '')))
            turma = escape_markdown(str(r.get('turma', '')).upper())
            status = escape_markdown(str(r.get('status', '')))
            motivo = escape_markdown(str(r.get('motivo', 'Sem motivo')))
            detalhe = escape_markdown(r.get('detalhe') or r.get('tipo_licenca') or '')
            obs = escape_markdown(r.get('observacao') or '')
            
            d_ref = r.get('data')
            if d_ref:
                try:
                    d_ref_br = datetime.strptime(d_ref, '%Y-%m-%d').strftime('%d/%m/%Y')
                except Exception:
                    d_ref_br = str(d_ref)
            else:
                d_ref_br = "Não informada"
                
            d_ini = r.get('data_ini')
            d_fim = r.get('data_fim')
            periodo = ""
            if d_ini and d_fim:
                try:
                    ini_br = datetime.strptime(d_ini, '%Y-%m-%d').strftime('%d/%m')
                    fim_br = datetime.strptime(d_fim, '%Y-%m-%d').strftime('%d/%m')
                    periodo = f"({ini_br} a {fim_br})"
                except Exception:
                    periodo = f"({d_ini} a {d_fim})"
            elif d_ini:
                try:
                    ini_br = datetime.strptime(d_ini, '%Y-%m-%d').strftime('%d/%m')
                    periodo = f"(A partir de {ini_br})"
                except Exception:
                    periodo = f"(A partir de {d_ini})"
                    
            status_ativo = ""
            if r.get('status') == 'Alta':
                status_ativo = "🔴 Alta/Encerrado"
            elif d_ini and d_fim:
                if d_ini <= hoje_str <= d_fim:
                    status_ativo = "🟢 Ativa"
                elif hoje_str > d_fim:
                    status_ativo = "⚪ Finalizada"
                else:
                    status_ativo = "🟡 Futura"
            elif d_ini:
                if d_ini <= hoje_str:
                    status_ativo = "🟢 Ativa"
                else:
                    status_ativo = "🟡 Futura"
            else:
                status_ativo = "🟢 Ativa"
                
            msg += f"• **{num}—{name}** ({turma})\n"
            msg += f"  ↳ *Registro*: {escape_markdown(d_ref_br)}\n"
            msg += f"  ↳ *Situação*: {status} {escape_markdown(periodo)} — {escape_markdown(status_ativo)}\n"
            msg += f"  ↳ *Motivo*: {motivo}\n"
            if detalhe:
                msg += f"  ↳ *Detalhe*: {detalhe}\n"
            if obs:
                msg += f"  ↳ *Obs*: {obs}\n"
        msg += "\n"
        
    return msg

AUTHORIZED_PROFILES_CACHE = {}

async def execute_bot_query_safe(query_fn, retries=1):
    last_err = None
    for attempt in range(retries):
        try:
            conn = get_db_connection()
            if not conn:
                raise RuntimeError("Sem conexão com o banco de dados.")
            return query_fn(conn).execute()
        except Exception as e:
            last_err = e
            print(f"[BOT DB QUERY TRY {attempt+1}/{retries}] Falha na query: {e}")
            from database import reset_db_connection
            reset_db_connection()
    return None

async def get_allowed_features_for_user(profile) -> set:
    allowed_features = set()
    if not profile:
        return allowed_features
    user_role = str(profile.get('role', 'compel')).strip().lower()
    
    defaults = {
        'menu_comsoc_noticias': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'operador'],
        'menu_comsoc_demandas': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'operador'],
        'menu_comsoc_cautela': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'],
        'menu_comsoc_brindes': ['admin', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'],
        'menu_comsoc_galeria': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'operador'],
        'menu_sisgab_tv': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador'],
        'menu_assistente_ia': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'operador'],
        'menu_config': ['admin', 'oficial_gab', 'operador'],
        'menu_admin_panel': ['admin'],
        'menu_ajuda_sobre': ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar', 'operador']
    }
    
    try:
        res = await execute_bot_query_safe(lambda c: c.table('permissions').select('*'))
        if res and res.data:
            for row in res.data:
                fk = row.get('feature_key')
                allowed = row.get('allowed_roles')
                if fk and allowed:
                    defaults[fk] = [r.strip().lower() for r in allowed.split(',') if r.strip()]
    except Exception as e:
        print(f"[Bot] Erro ao ler permissions do banco: {e}")
            
    for fk, roles in defaults.items():
        if user_role in roles:
            allowed_features.add(fk)
    return allowed_features

async def check_authorized_user(from_user_id: int):
    current_user_id.set(from_user_id)
    str_uid = str(from_user_id)
    
    # 1. Checa cache de memória para resposta ultra-rápida (0ms)
    if str_uid in AUTHORIZED_PROFILES_CACHE:
        return AUTHORIZED_PROFILES_CACHE[str_uid]
        
    try:
        # Busca primeiro na tabela do efetivo
        res_ef = await execute_bot_query_safe(lambda c: c.table('efetivo').select('*').eq('telegram_id', str_uid))
        if res_ef and res_ef.data:
            profile = res_ef.data[0]
            allowed = await get_allowed_features_for_user(profile)
            USER_PERMISSIONS_CACHE[from_user_id] = allowed
            AUTHORIZED_PROFILES_CACHE[str_uid] = profile
            return profile
            
        # Fallback na tabela users
        res = await execute_bot_query_safe(lambda c: c.table('users').select('*').eq('telegram_id', str_uid))
        if res and res.data:
            sorted_profiles = sorted(res.data, key=lambda u: 1 if u.get('role') == 'aluno' else 0)
            profile = sorted_profiles[0]
            allowed = await get_allowed_features_for_user(profile)
            USER_PERMISSIONS_CACHE[from_user_id] = allowed
            AUTHORIZED_PROFILES_CACHE[str_uid] = profile
            return profile
    except Exception as e:
        print(f"[Bot] Erro ao validar telegram_id {from_user_id}: {e}")
    return None

def clear_state(chat_id):
    if chat_id in chat_states:
        del chat_states[chat_id]

def get_user_active_year(profile):
    if not profile or 'id' not in profile:
        return '2026'
    if profile.get('ano_letivo'):
        return str(profile['ano_letivo'])
    from notifications_manager import get_user_preferences
    try:
        user_prefs = get_user_preferences(profile['id'])
        return user_prefs.get('ano_letivo_ativo', '2026')
    except Exception:
        return '2026'

def set_user_active_year(profile, ano: str):
    if not profile or 'id' not in profile:
        return
    from notifications_manager import get_user_preferences, save_user_preferences
    try:
        user_prefs = get_user_preferences(profile['id'])
        user_prefs['ano_letivo_ativo'] = ano
        save_user_preferences(profile['id'], user_prefs)
    except Exception as e:
        print(f"[YEAR SAVE LOCAL ERR] {e}")
    try:
        conn = get_user_db_connection()
        if conn:
            conn.table('users').update({'ano_letivo': ano}).eq('id', profile['id']).execute()
    except Exception as e:
        print(f"[YEAR SAVE DB ERR] {e}")


def parse_date_or_days(text_input: str):
    """Tenta converter a entrada (ex: '20/08', '20/08/2026' ou '10' dias) para data final (YYYY-MM-DD) e texto legível."""
    if not text_input:
        return "", ""
    text_clean = text_input.strip()
    now = datetime.now()
    
    if text_clean.isdigit():
        dias = int(text_clean)
        target_dt = now + timedelta(days=dias)
        return target_dt.strftime('%Y-%m-%d'), target_dt.strftime('%d/%m/%Y')
        
    match_dt = re.search(r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?', text_clean)
    if match_dt:
        dia = int(match_dt.group(1))
        mes = int(match_dt.group(2))
        ano = int(match_dt.group(3)) if match_dt.group(3) else now.year
        if ano < 100: ano += 2000
        try:
            target_dt = datetime(ano, mes, dia)
            return target_dt.strftime('%Y-%m-%d'), target_dt.strftime('%d/%m/%Y')
        except Exception:
            pass
            
    return "", text_clean


async def _salvar_presenca_bot(bot, message, chat_id, state, sigla_code, obs_txt, data_fim=""):
    """Salva a presença diária informada pelo Telegram no Supabase e no SQLite local com esquema completo."""
    import uuid
    profile = state.get('user') or {}
    user_id = profile.get('id') or str(chat_id)
    nome_g = None
    
    # 1. Tenta buscar o nome_guerra e id oficial na tabela efetivo via telegram_id
    try:
        from database import get_bot_db_connection
        db_chk = get_bot_db_connection()
        if db_chk:
            res_ef = db_chk.table('efetivo').select('id, nome_guerra').eq('telegram_id', str(chat_id)).execute()
            if res_ef and res_ef.data:
                nome_g = res_ef.data[0].get('nome_guerra')
                if res_ef.data[0].get('id'):
                    user_id = res_ef.data[0].get('id')
    except Exception as ef_chk_err:
        print(f"[PRESENCA CHECK EFETIVO ERR] {ef_chk_err}")
        
    if not nome_g:
        nome_g = profile.get('nome_guerra') or profile.get('nome') or 'MILITAR'
        
    nome_g = str(nome_g).replace('None ', '').replace('None', '').strip().upper()
    from datetime import datetime, timedelta
    now_br = datetime.utcnow() - timedelta(hours=3)
    dt_str = now_br.strftime('%Y-%m-%d')
    hr_str = now_br.strftime('%H:%M:%S')
    
    # Buscar registro existente para (user_id/telegram_id/nome_guerra, data) antes de inserir
    pres_id = None
    try:
        from database import get_bot_db_connection
        db_check = get_bot_db_connection()
        if db_check:
            # Tenta buscar por telegram_id ou user_id ou nome_guerra para a data de hoje
            res_all = db_check.table('presenca_diaria').select('id, user_id, telegram_id, nome_guerra').eq('data', dt_str).execute()
            if res_all and res_all.data:
                for row in res_all.data:
                    r_tg = str(row.get('telegram_id') or '').strip()
                    r_uid = str(row.get('user_id') or '').strip()
                    r_ng = str(row.get('nome_guerra') or '').strip().upper()
                    if (r_tg and r_tg == str(chat_id)) or (r_uid and r_uid == str(user_id)) or (r_ng and r_ng == nome_g):
                        pres_id = row.get('id')
                        break
    except Exception as chk_err:
        print(f"[PRESENCA CHECK EXISTING ERR] {chk_err}")
    
    if not pres_id:
        pres_id = str(uuid.uuid4())
    
    payload = {
        'id': pres_id,
        'user_id': str(user_id),
        'telegram_id': str(chat_id),
        'nome_guerra': nome_g,
        'data': dt_str,
        'hora_presenca': hr_str,
        'status': sigla_code,
        'observacao': obs_txt.strip() if obs_txt else '',
        'data_fim': data_fim if data_fim else None,
        'criado_em': now_br.isoformat(),
        'updated_at': now_br.isoformat()
    }
    
    # Chama a função unificada para garantir sincronia em todos os bancos
    try:
        import sys, os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from modulo_presenca import salvar_presenca_unificada
        salvar_presenca_unificada(
            dt_str=dt_str,
            nome_guerra=nome_g,
            status_code=sigla_code,
            observacao=obs_txt,
            user_id=str(user_id).strip() if user_id else None,
            telegram_id=str(chat_id).strip(),
            data_fim=data_fim
        )
    except Exception as err_uni:
        print(f"[UNIFICADO SAVE ERR] {err_uni}")
        
    is_operator = str(profile.get('role', '')).strip().lower() in ('admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'operador')
    clear_state(chat_id)
    
    obs_line = f"✍️ Obs: _{obs_txt}_\n" if obs_txt and sigla_code not in ('FE', 'L', 'DM') else ""
    info_fim = f"🏖️ Chamada suspensa até: *{data_fim}*\n" if data_fim and sigla_code in ('FE', 'L', 'DM') else ""
    from .keyboards import get_main_menu_keyboard
    await bot.reply_to(
        message,
        f"✅ **PRESENÇA REGISTRADA COM SUCESSO!**\n\n"
        f"👤 Militar: *{nome_g}*\n"
        f"📌 Rotina: *({sigla_code})*\n"
        f"📅 Data: *{dt_str}*\n"
        f"{obs_line}{info_fim}\n"
        f"Sua presença foi salva na Sargenteação!",
        reply_markup=get_main_menu_keyboard(is_operator),
        parse_mode='Markdown'
    )


def get_rank_seniority(rank_str: str) -> int:
    """Retorna o valor numérico de antiguidade militar (menor número = maior antiguidade)."""
    if not rank_str:
        return 99
    
    tokens = re.findall(r'[A-Z0-9º]+', str(rank_str).upper())
    if not tokens:
        return 99

    for t in tokens:
        if t in ('AE', 'ALMIRANTE'): return 1
        if t in ('VA', 'VICEALMIRANTE'): return 2
        if t in ('CA', 'CONTRAALMIRANTE'): return 3
        if t in ('CMG', 'CAPITAODEMAREGUERRA'): return 4
        if t in ('CF', 'CAPITAODEFRAGATA'): return 5
        if t in ('CC', 'CAPITAODECORVETA'): return 6
        if t in ('CT', 'CAPITAOTENENTE'): return 7
        if t in ('1TEN', '1ºTEN', '1SOTEN', '1TENENTE', '1ºTENENTE'): return 8
        if t in ('2TEN', '2ºTEN', '2SOTEN', '2TENENTE', '2ºTENENTE'): return 9
        if t in ('GM', 'GUARDAMARINHA'): return 10
        if t in ('SO', 'SUBOFICIAL', 'SUB-OFICIAL'): return 11
        if t in ('1SG', '1ºSG', '1SGT', '1ºSGT', '1ºSARGENTO'): return 12
        if t in ('2SG', '2ºSG', '2SGT', '2ºSGT', '2ºSARGENTO'): return 13
        if t in ('3SG', '3ºSG', '3SGT', '3ºSGT', '3ºSARGENTO', 'SG', 'SARGENTO'): return 14
        if t in ('CB', 'CABO'): return 15
        if t in ('SD', 'SOLDADO', 'MN', 'MARINHEIRO'): return 16

    return 98

ANTIGUIDADE_OFICIAL_EXATA = [
    'SO ROBERTO', 'SO CARVALHO', 'SO HENRIQUE', 'SO ABREU', 'SO COSTA', 'SO CRISTIAN',
    'SG ERBE', 'SG MOISÉS', 'SG MOISES', 'SG SILVA', 'SG SANTANA', 'SG CALAÇA', 'SG CALACA',
    'SG TONETTI', 'SG THIAGO NUNES', 'SG BORGES', 'SG TAVARES', 'SG SOUZA', 'SG ESDRAS',
    'SG MICHELLE FIDELIS', 'SG MICHELLE', 'CB THIAGO FERREIRA', 'CB DE SOUZA', 'CB HENTTYZY', 'CB TANAKA'
]

def sort_efetivo_by_rank(ef_list: list) -> list:
    """Ordena uma lista de militares priorizando 1º a Equipe COMSOC e 2º Demais Praças, ambos pela antiguidade oficial."""
    def sort_key(item):
        role = str(item.get('role', '')).strip().lower()
        setor = str(item.get('setor', '')).strip().upper()
        secao = str(item.get('secao', '')).strip().upper()
        funcao = str(item.get('funcao', '')).strip().upper()

        is_comsoc = (
            role in ('admin', 'supervisor', 'comsoc', 'comsoc_design') or
            'COMSOC' in setor or 'COMSOC' in secao or 'COMSOC' in funcao
        )
        group_priority = 0 if is_comsoc else 1

        pg = str(item.get('posto_grad') or item.get('posto') or '').strip().upper()
        ng = str(item.get('nome_guerra') or item.get('nome') or '').strip().upper()
        full = f"{pg} {ng}".strip().upper()

        ant_idx = 999
        for idx, target in enumerate(ANTIGUIDADE_OFICIAL_EXATA):
            if full == target:
                ant_idx = idx
                break
        if ant_idx == 999:
            for idx, target in enumerate(ANTIGUIDADE_OFICIAL_EXATA):
                parts = target.split(maxsplit=1)
                if len(parts) == 2 and ng == parts[1]:
                    ant_idx = idx
                    break
        if ant_idx == 999:
            for idx, target in enumerate(ANTIGUIDADE_OFICIAL_EXATA):
                if ng in target or target in ng:
                    ant_idx = idx
                    break

        return (group_priority, ant_idx, ng)

    return sorted(ef_list, key=sort_key)


async def upload_photos_to_drive(bot, chat_id, photos_info, demanda):
    """Downloads photos from Telegram and uploads to Drive event folder."""
    import drive_service
    import os
    import asyncio
    from database import get_bot_db_connection
    import uuid
    from datetime import datetime

    success_count = 0
    
    drive_service.reset_drive_service()
    
    folder_id = demanda.get('drive_folder_id')
    if not folder_id and demanda.get('drive_url'):
        url = demanda.get('drive_url', '')
        if 'folders/' in url:
            folder_id = url.split('folders/')[-1].split('?')[0].split('/')[0]

    if not folder_id:
        titulo = demanda.get('titulo_evento', 'Evento sem titulo')
        dt_evento = demanda.get('data_evento', datetime.now().strftime('%Y-%m-%d'))
        res = await asyncio.to_thread(drive_service.criar_pasta_evento, titulo, dt_evento)
        if res and res.get('evento_folder_id'):
            folder_id = res.get('evento_folder_id')
            db = get_bot_db_connection()
            if db and demanda.get('id'):
                try:
                    db.table('demandas_comunicacao').update({
                        'drive_folder_id': folder_id,
                        'drive_url': res.get('evento_link')
                    }).eq('id', demanda['id']).execute()
                    demanda['drive_url'] = res.get('evento_link')
                except Exception:
                    pass
    
    if not folder_id:
        await bot.send_message(chat_id, "⚠️ Não foi possível determinar ou criar a pasta no Google Drive. Verifique as credenciais no Admin.")
        return 0
        
    db = get_bot_db_connection()
        
    for photo in photos_info:
        try:
            file_info = await bot.get_file(photo['file_id'])
            downloaded_file = await bot.download_file(file_info.file_path)
            
            filename = photo.get('file_name', f"photo_{uuid.uuid4().hex[:8]}.jpg")
            
            # Salvar copia local para galeria web
            try:
                import os as _os
                _local_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'assets', 'galeria_hot', str(demanda.get('id', 'unknown')))
                _os.makedirs(_local_dir, exist_ok=True)
                _local_path = _os.path.join(_local_dir, filename)
                with open(_local_path, 'wb') as _f:
                    _f.write(downloaded_file)
                print(f'[UPLOAD] [OK] Copia local salva: {_local_path}')
            except Exception as _le:
                print(f'[UPLOAD] [WARN] Falha ao salvar copia local: {_le}')
            
            upload_res = await asyncio.wait_for(
                asyncio.to_thread(drive_service.upload_file, downloaded_file, filename, folder_id),
                timeout=15.0
            )
            if isinstance(upload_res, dict) and upload_res.get('error') == 'storageQuotaExceeded':
                await bot.send_message(
                    chat_id,
                    "⚠️ *ERRO DE COTA NO GOOGLE DRIVE (Quota Exceeded)*\n\n"
                    "As Service Accounts do Google possuem 0 GB de cota própria para uploads em contas pessoais `@gmail.com`.\n\n"
                    "💡 *Como Resolver (Passo a Passo em 1 minuto):*\n"
                    "1. No Google Drive, acesse **Drives Compartilhados** e crie um novo Drive Compartilhado.\n"
                    "2. Adicione a Service Account como Administrador:\n`sisgab-drive-service@sisgab-drive.iam.gserviceaccount.com`\n"
                    "3. Cole o ID do Drive Compartilhado no Painel Admin do SisGAB (`/admin_panel`).",
                    parse_mode="Markdown"
                )
                return 0
            elif isinstance(upload_res, dict) and upload_res.get('id'):
                success_count += 1
                if db and demanda.get('id'):
                    try:
                        db.table('processed_photos').insert({
                            'demanda_id': demanda['id'],
                            'event_name': demanda.get('titulo_evento', ''),
                            'file_id': photo['file_id'],
                            'file_name': filename,
                            'drive_link': upload_res.get('webViewLink', ''),
                            'uploaded_by': str(chat_id),
                            'created_at': datetime.now().isoformat()
                        }).execute()
                    except Exception as db_err:
                        print(f"Erro ao registrar foto processada: {db_err}")
        except Exception as e:
            print(f"Erro no upload da foto {photo.get('file_id')}: {e}")
            
    return success_count

async def enviar_links_acervo(bot, chat_id, demanda):
    """Envia mensagem formatada no Telegram com links da pasta completa e SELEÇÃO."""
    from database import get_demanda_drive_url
    
    titulo = (demanda.get('titulo_evento') or 'Evento').upper()
    data_ev = demanda.get('data_evento', '')
    local = demanda.get('local_evento', 'CGCFN')
    
    drive_url = get_demanda_drive_url(demanda)
    fid = demanda.get('drive_folder_id', '')
    if not drive_url and fid:
        drive_url = f"https://drive.google.com/drive/folders/{fid}"
        
    msg = f"📸 *ACERVO FOTOGRÁFICO: {titulo}*\n"
    msg += f"📅 Data: {data_ev} | 📍 Local: {local}\n\n"
    
    if drive_url:
        msg += f"📁 *Pasta Completa do Evento no Google Drive:*\n{drive_url}\n\n"
    else:
        msg += "⚠️ *Link do Drive não disponível.*\n\n"
        
    msg += "📱 *Gerado pelo SisGAB — COMSOC / CGCFN*"
    
    try:
        await bot.send_message(chat_id, msg, parse_mode='Markdown')
        return True
    except Exception as e:
        print(f"[BOT] Erro ao enviar links do acervo: {e}")
        return False


async def enviar_album_hd_drive(bot, chat_id, selecao_folder_id, max_photos=12):
    """
    Baixa as fotos da pasta SELEÇÃO no Drive e envia de forma progressiva em lotes rápidos (send_media_group).
    Informa a quantidade total de fotos no início e envia gradativamente.
    """
    import drive_service
    from telebot.types import InputMediaPhoto
    
    if not selecao_folder_id:
        await bot.send_message(chat_id, "⚠️ Pasta de SELEÇÃO não vinculada.")
        return 0
        
    files = drive_service.list_files(selecao_folder_id, mime_filter='image/', page_size=max_photos)
    if not files:
        await bot.send_message(chat_id, "ℹ️ Nenhuma foto encontrada na pasta SELEÇÃO.")
        return 0

    total_files = len(files)
    status_msg = None
    try:
        status_msg = await bot.send_message(
            chat_id, 
            f"⏳ *Iniciando envio do Álbum HD...*\n📷 Total de fotos na Seleção: **{total_files}**\n_Baixando e enviando em lotes rápidos..._",
            parse_mode='Markdown'
        )
    except Exception:
        pass

    batch_size = 4
    sent_count = 0
    
    for i in range(0, total_files, batch_size):
        chunk_files = files[i:i + batch_size]
        media_group = []
        
        for idx, f in enumerate(chunk_files):
            file_bytes = drive_service.download_file(f['id'])
            if file_bytes:
                current_num = i + idx + 1
                caption = f"📸 Foto {current_num}/{total_files}" if (current_num == 1 or current_num % batch_size == 1) else ""
                media_group.append(InputMediaPhoto(file_bytes, caption=caption))
                
        if media_group:
            try:
                await bot.send_media_group(chat_id, media_group)
                sent_count += len(media_group)
            except Exception as send_err:
                print(f"[BOT] Erro ao enviar lote de fotos: {send_err}")
                
    if status_msg and hasattr(status_msg, 'message_id'):
        try:
            await bot.edit_message_text(
                f"✅ *Álbum HD Entregue!*\n📸 Total de **{sent_count} foto(s)** enviadas.",
                chat_id,
                status_msg.message_id,
                parse_mode='Markdown'
            )
        except Exception:
            pass

    return sent_count

