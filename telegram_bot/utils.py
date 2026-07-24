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
