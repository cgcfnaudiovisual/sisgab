# modules/modulo_presenca.py
from datetime import datetime
import json
import urllib.parse
from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection

THEME = theme.colors

# Mapeamento oficial das siglas militares
SIGLAS_MILITARES = {
    'P': {'nome': 'Presente', 'icone': '🟢', 'badge_color': 'green'},
    'MA': {'nome': 'Missão Administrativa', 'icone': '💼', 'badge_color': 'cyan'},
    'MT': {'nome': 'Mais Tarde', 'icone': '🕒', 'badge_color': 'deep-orange'},
    'FE': {'nome': 'Férias', 'icone': '🏖️', 'badge_color': 'blue'},
    'L': {'nome': 'Licença', 'icone': '📜', 'badge_color': 'purple'},
    'H': {'nome': 'Hospital', 'icone': '🏥', 'badge_color': 'red'},
    'DM': {'nome': 'Dispensa Médica', 'icone': '💊', 'badge_color': 'orange'},
    'S': {'nome': 'Serviço de Escala', 'icone': 'teal'},
    'OUTRO': {'nome': 'Outra Situação', 'icone': '✏️', 'badge_color': 'indigo'},
}


def salvar_presenca_unificada(dt_str: str, nome_guerra: str, status_code: str, observacao: str = '', user_id: str = None, telegram_id: str = None, data_fim: str = None):
    """Salva/atualiza a presença simultaneamente em escala_diaria (Supabase), presenca_diaria (Supabase) e SQLite local."""
    import uuid
    from datetime import datetime, timedelta
    
    now_br = datetime.utcnow() - timedelta(hours=3)
    hr_str = now_br.strftime('%H:%M:%S')
    iso_br = now_br.isoformat()
    
    nome_clean = str(nome_guerra or 'MILITAR').replace('None ', '').replace('None', '').strip().upper()
    status_clean = str(status_code or 'P').strip().upper()
    obs_clean = str(observacao or '').strip()
    
    # 1. Supabase (escala_diaria principal + presenca_diaria se existir)
    try:
        db_s = get_service_db_connection() or get_db_connection()
        if db_s:
            try:
                res_esc = db_s.table('escala_diaria').select('id').eq('data', dt_str).ilike('nome', f"%{nome_clean}%").execute()
                if res_esc and res_esc.data:
                    db_s.table('escala_diaria').update({
                        'cargo': status_clean,
                        'observacao': obs_clean
                    }).eq('id', res_esc.data[0]['id']).execute()
                else:
                    db_s.table('escala_diaria').insert({
                        'data': dt_str,
                        'cargo': status_clean,
                        'nome': nome_clean,
                        'observacao': obs_clean
                    }).execute()
            except Exception as e_esc:
                print(f"[UNIFIED ESCALA_DIARIA SAVE WARN] {e_esc}")

            try:
                pres_id = str(uuid.uuid4())
                res_p = db_s.table('presenca_diaria').select('id').eq('data', dt_str).eq('nome_guerra', nome_clean).execute()
                if res_p and res_p.data:
                    pres_id = res_p.data[0]['id']
                db_s.table('presenca_diaria').upsert({
                    'id': pres_id,
                    'user_id': str(user_id).strip() if user_id else None,
                    'telegram_id': str(telegram_id).strip() if telegram_id else None,
                    'nome_guerra': nome_clean,
                    'data': dt_str,
                    'hora_presenca': hr_str,
                    'status': status_clean,
                    'observacao': obs_clean,
                    'data_fim': data_fim,
                    'criado_em': iso_br,
                    'updated_at': iso_br
                }, on_conflict='id').execute()
            except Exception:
                pass
    except Exception as sp_err:
        print(f"[UNIFIED SUPABASE WARN] {sp_err}")

    # 2. SQLite Local (escala_diaria e presenca_diaria)
    try:
        from sqlite_adapter import LocalSQLiteClient
        local_db = LocalSQLiteClient()
        pres_id_loc = str(uuid.uuid4())
        try:
            res_loc_p = local_db.table('presenca_diaria').select('id').eq('data', dt_str).eq('nome_guerra', nome_clean).execute()
            if res_loc_p and res_loc_p.data:
                pres_id_loc = res_loc_p.data[0]['id']
        except Exception:
            pass
            
        local_db.table('presenca_diaria').upsert({
            'id': pres_id_loc,
            'user_id': str(user_id).strip() if user_id else None,
            'telegram_id': str(telegram_id).strip() if telegram_id else None,
            'nome_guerra': nome_clean,
            'data': dt_str,
            'hora_presenca': hr_str,
            'status': status_clean,
            'observacao': obs_clean,
            'data_fim': data_fim,
            'criado_em': iso_br,
            'updated_at': iso_br
        }, on_conflict='id').execute()

        try:
            res_loc_e = local_db.table('escala_diaria').select('id').eq('data', dt_str).eq('nome', nome_clean).execute()
            if res_loc_e and res_loc_e.data:
                local_db.table('escala_diaria').update({'cargo': status_clean, 'observacao': obs_clean}).eq('id', res_loc_e.data[0]['id']).execute()
            else:
                local_db.table('escala_diaria').insert({'data': dt_str, 'cargo': status_clean, 'nome': nome_clean, 'observacao': obs_clean}).execute()
        except Exception:
            pass
    except Exception as loc_err:
        print(f"[UNIFIED LOCAL WARN] {loc_err}")

def find_presence_for_militar(ef, presencas_list, presencas_dict=None):
    """Localiza o registro de presença de um militar usando nome_guerra, telegram_id, user_id ou busca por sub-string inteligente."""
    if not ef:
        return {}

    ef_nome = str(ef.get('nome_guerra', '')).upper().strip()
    ef_tg = str(ef.get('telegram_id', '')).strip()
    ef_id = str(ef.get('id', '')).strip()

    if presencas_dict and ef_nome in presencas_dict:
        return presencas_dict[ef_nome]

    ef_words = set(ef_nome.split())
    sig_words = [w for w in ef_words if w not in ('SG', 'CB', 'SO', 'CT', 'CC', 'CF', '1TEN', '2TEN', '3SG', '1SG', '2SG', 'SD', 'MILITAR', 'ADMIN')]

    for p in (presencas_list or []):
        p_tg = str(p.get('telegram_id', '')).strip()
        p_uid = str(p.get('user_id', '')).strip()
        p_nome = str(p.get('nome_guerra', '')).upper().strip()

        if ef_tg and p_tg and ef_tg == p_tg:
            return p
        if ef_id and p_uid and ef_id == p_uid:
            return p
        if ef_nome and p_nome:
            if ef_nome == p_nome or ef_nome in p_nome or p_nome in ef_nome:
                return p
            p_words = set(p_nome.split())
            if sig_words and any(w in p_words for w in sig_words):
                return p

    return {}


def gerar_texto_pronto_chegab(data_str, presencas_dict, efetivo_lista, presencas_list=None):
    """Gera o texto oficial formatado no padrão da Sargenteação para o Chefe de Gabinete."""
    data_br = datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y') if '-' in data_str else data_str
    
    linhas_militares = []
    for ef in efetivo_lista:
        nome_g = ef.get('nome_guerra', '').upper()
        p = find_presence_for_militar(ef, presencas_list, presencas_dict)
        sigla = p.get('status', 'PENDENTE').upper()
        obs = p.get('observacao', '').strip()
        
        txt_linha = f"{nome_g} - {sigla}"
        if obs and sigla not in ('FE', 'L', 'DM'):
            txt_linha += f" ({obs})"
        linhas_militares.append(txt_linha)
        
    texto = (
        f"Bom dia Equipe LANÇAMENTO 🚀, resumo das rotinas para hoje ({data_br}):\n\n"
        f"🚨 *pronto da presença para o CheGab:*\n\n"
    )
    texto += "\n".join(linhas_militares)
    texto += (
        "\n\nOBS:\n"
        "(P) - Presente;\n"
        "(MA) - Missão Administrativa;\n"
        "(L) - Licença;\n"
        "(H) - Hospital;\n"
        "(DM) - Dispensa Médica;\n"
        "(FE) - Férias;\n"
        "(MT) - Mais Tarde;\n"
        "(S) - Serviço; e\n"
        "(OUTRO) - Outra Situação.\n\n"
        "Atenciosamente,\n"
        "Sargenteante do Gabinete"
    )
    return texto


def fetch_efetivo_and_presencas(dt_str: str):
    """Busca o efetivo e a presença diária sincronizando escala_diaria (Supabase), presenca_diaria e SQLite local."""
    efetivo_lista = []
    presencas_list = []
    seen_militares = set()

    db = get_service_db_connection() or get_db_connection()
    if db:
        try:
            res_ef = db.table('efetivo').select('*').order('nome_guerra').execute()
            efetivo_lista = res_ef.data or []
        except Exception as e:
            print(f"[PRESENCA LOAD EFETIVO WARN] {e}")

        # 1. Carregar escala_diaria do Supabase (tabela principal no Supabase)
        try:
            res_esc = db.table('escala_diaria').select('*').eq('data', dt_str).execute()
            if res_esc and res_esc.data:
                for r in res_esc.data:
                    nome_g = str(r.get('nome') or '').strip().upper()
                    if nome_g:
                        presencas_list.append({
                            'id': str(r.get('id', '')),
                            'nome_guerra': nome_g,
                            'data': dt_str,
                            'status': str(r.get('cargo') or 'P').strip().upper(),
                            'observacao': str(r.get('observacao') or '').strip(),
                            'criado_em': r.get('criado_em')
                        })
                        seen_militares.add(nome_g)
        except Exception as e_esc:
            print(f"[PRESENCA LOAD ESCALA WARN] {e_esc}")

        # 2. Carregar presenca_diaria do Supabase (se a tabela existir no projeto)
        try:
            res_pr = db.table('presenca_diaria').select('*').eq('data', dt_str).execute()
            if res_pr and res_pr.data:
                for p in res_pr.data:
                    nome_g = str(p.get('nome_guerra') or '').strip().upper()
                    if nome_g and nome_g not in seen_militares:
                        presencas_list.append(p)
                        seen_militares.add(nome_g)
        except Exception as e:
            pass

    # 3. Busca e mescla presenças do SQLite local (presenca_diaria e escala_diaria)
    try:
        from sqlite_adapter import LocalSQLiteClient
        local_db = LocalSQLiteClient()
        if not efetivo_lista:
            res_ef_loc = local_db.table('efetivo').select('*').order('nome_guerra').execute()
            efetivo_lista = res_ef_loc.data or []

        try:
            res_pr_loc = local_db.table('presenca_diaria').select('*').eq('data', dt_str).execute()
            if res_pr_loc and res_pr_loc.data:
                for lp in res_pr_loc.data:
                    l_ng = (lp.get('nome_guerra') or '').strip().upper()
                    if l_ng and l_ng not in seen_militares:
                        presencas_list.append(lp)
                        seen_militares.add(l_ng)
        except Exception:
            pass

        try:
            res_esc_loc = local_db.table('escala_diaria').select('*').eq('data', dt_str).execute()
            if res_esc_loc and res_esc_loc.data:
                for le in res_esc_loc.data:
                    l_ng = (le.get('nome') or '').strip().upper()
                    if l_ng and l_ng not in seen_militares:
                        presencas_list.append({
                            'id': str(le.get('id', '')),
                            'nome_guerra': l_ng,
                            'data': dt_str,
                            'status': str(le.get('cargo') or 'P').strip().upper(),
                            'observacao': str(le.get('observacao') or '').strip()
                        })
                        seen_militares.add(l_ng)
        except Exception:
            pass
    except Exception as loc_err:
        print(f"[PRESENCA LOCAL FALLBACK WARN] {loc_err}")

    # 4. Busca isenções ativas por período (FE, L, DM com data_fim)
    try:
        db_ref = get_service_db_connection() or get_db_connection()
        if db_ref:
            res_extended = db_ref.table('presenca_diaria').select('*').in_('status', ['FE', 'L', 'DM']).lte('data', dt_str).execute()
            if res_extended and res_extended.data:
                for item in res_extended.data:
                    nome_g = item.get('nome_guerra', '').upper()
                    if nome_g not in seen_militares:
                        data_fim = item.get('data_fim')
                        if data_fim and data_fim >= dt_str:
                            presencas_list.append({
                                'nome_guerra': nome_g,
                                'data': dt_str,
                                'status': item.get('status'),
                                'observacao': item.get('observacao', ''),
                                'data_fim': data_fim
                            })
                            seen_militares.add(nome_g)
    except Exception as ext_err:
        pass
        
    try:
        from telegram_bot.utils import sort_efetivo_by_rank, normalize_text
        
        # Deduplicação estrita de efetivo
        dedup_ef = []
        seen_ef_nips = set()
        seen_ef_names = set()
        
        for ef in efetivo_lista:
            nip = str(ef.get('nip') or '').strip()
            ng = normalize_text(str(ef.get('nome_guerra') or ef.get('nome') or ''))
            
            if nip and nip in seen_ef_nips:
                continue
            if ng and ng in seen_ef_names:
                continue
                
            if nip: seen_ef_nips.add(nip)
            if ng: seen_ef_names.add(ng)
            dedup_ef.append(ef)
            
        efetivo_lista = sort_efetivo_by_rank(dedup_ef)
    except Exception as sort_err:
        print(f"[SORT EFETIVO WARN] {sort_err}")

    return efetivo_lista, presencas_list


def render_page():
    ui.label('📋 CHAMADA MATUTINA & PRONTO AO CHEGAB').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    
    data_selecionada = ui.input('Data da Chamada', value=datetime.now().strftime('%Y-%m-%d')).props('type=date dark outlined dense').classes('w-48 q-mb-md q-ml-md')

    @ui.refreshable
    def render_content():
        dt_str = data_selecionada.value or datetime.now().strftime('%Y-%m-%d')
        efetivo_lista, presencas_list = fetch_efetivo_and_presencas(dt_str)

        # Mapeia presencas por nome_guerra
        presencas_dict = {p['nome_guerra'].upper(): p for p in presencas_list if p.get('nome_guerra')}
        
        # Contadores de estatísticas
        tot_efetivo = len(efetivo_lista)
        contadores = {'P': 0, 'MA': 0, 'MT': 0, 'FE': 0, 'L': 0, 'H': 0, 'DM': 0, 'S': 0, 'OUTRO': 0, 'PENDENTE': 0}
        
        for ef in efetivo_lista:
            p_ef = find_presence_for_militar(ef, presencas_list, presencas_dict)
            st = p_ef.get('status', 'PENDENTE').upper()
            if st in contadores:
                contadores[st] += 1
            else:
                contadores['PENDENTE'] += 1

        with ui.column().classes('w-full gap-4'):
            # INDICADORES DA CHAMADA
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl bg-slate-900 border border-cyan-500/30'):
                with ui.row().classes('w-full justify-between items-center wrap gap-4'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('assignment_ind', color='cyan', size='2rem')
                        with ui.column().classes('gap-0'):
                            ui.label('EFETIVO E CHAMADA DIÁRIA').classes('text-sm font-bold text-white')
                            ui.label(f"Total: {tot_efetivo} militares | Data: {dt_str}").classes('text-xs text-grey-4 font-mono')
                    
                ui.badge(f"⚔️ Missão Tática (MT): {contadores['MT']}").props('color=deep-orange bold').classes('q-pa-xs')
                ui.badge(f"🏖️ Férias (FE): {contadores['FE']}").props('color=blue bold').classes('q-pa-xs')
                ui.badge(f"📜 Licença (L): {contadores['L']}").props('color=purple bold').classes('q-pa-xs')
                ui.badge(f"🏥 Hospital (H): {contadores['H']}").props('color=red bold').classes('q-pa-xs')
                ui.badge(f"💊 Disp. Médica (DM): {contadores['DM']}").props('color=orange bold').classes('q-pa-xs')
                ui.badge(f"🛡️ Serviço (S): {contadores['S']}").props('color=teal bold').classes('q-pa-xs')
                ui.badge(f"⏳ Pendentes: {contadores['PENDENTE']}").props('color=grey-7 bold').classes('q-pa-xs')

        # BARRA DE AÇÕES EM LOTE
        selected_ids = set()
        checkbox_refs = {}

        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl bg-slate-900 border border-cyan-500/20'):
            ui.label('👥 Relação do Efetivo do Gabinete').classes('text-sm font-bold text-white q-mb-xs')

            # Toolbar de Ações em Lote
            with ui.row().classes('w-full items-center gap-3 q-mb-md q-pa-sm rounded-lg').style(
                'background: rgba(0,229,255,0.04); border: 1px solid rgba(0,229,255,0.15);'
            ):
                def toggle_all(e):
                    if e.value:
                        for ef_item in efetivo_lista:
                            selected_ids.add(ef_item.get('id', ef_item.get('nome_guerra', '')))
                    else:
                        selected_ids.clear()
                    for cb_ref in checkbox_refs.values():
                        cb_ref.value = e.value
                    lbl_sel.text = f'{len(selected_ids)} selecionado(s)'

                chk_all = ui.checkbox('Selecionar Todos', on_change=toggle_all).classes('text-xs text-cyan font-bold')

                ui.separator().props('vertical').classes('q-mx-xs')

                lbl_sel = ui.label('0 selecionado(s)').classes('text-[10px] text-grey-4 font-mono')

                ui.separator().props('vertical').classes('q-mx-xs')

                # Botão rápido: Todos Pendentes → Presente
                def marcar_todos_presentes():
                    cnt = 0
                    for ef_item in efetivo_lista:
                        nome_g = ef_item.get('nome_guerra', '').upper()
                        pres_item = find_presence_for_militar(ef_item, presencas_list, presencas_dict)
                        st_atual = pres_item.get('status', 'PENDENTE').upper()
                        if st_atual == 'PENDENTE':
                            salvar_presenca_unificada(
                                dt_str=dt_str,
                                nome_guerra=nome_g,
                                status_code='P',
                                observacao='',
                                user_id=ef_item.get('id'),
                                telegram_id=ef_item.get('telegram_id')
                            )
                            cnt += 1
                    if cnt > 0:
                        ui.notify(f'✅ {cnt} militar(es) marcado(s) como Presente!', color='positive')
                        render_content.refresh()
                    else:
                        ui.notify('Nenhum militar pendente encontrado.', color='info')

                ui.button('⚡ Todos Pendentes → Presente', icon='check_circle',
                          on_click=marcar_todos_presentes
                ).props('unelevated color=green text-color=white dense bold').classes('text-[11px]')

            # Barra de Ação em Lote para selecionados
            with ui.row().classes('w-full items-center gap-3 q-mb-md q-pa-sm rounded-lg').style(
                'background: rgba(245,158,11,0.04); border: 1px solid rgba(245,158,11,0.15);'
            ):
                ui.label('Ação em Lote:').classes('text-[11px] font-bold text-amber-4')
                lote_status = ui.select(
                    {k: f"({k}) {v['nome']}" for k, v in SIGLAS_MILITARES.items()},
                    value='P', label='Status'
                ).props('dark outlined dense').classes('text-xs').style('min-width: 180px;')
                lote_obs = ui.input('Observação (opcional)').props('dark outlined dense').classes('text-xs flex-1')

                def aplicar_lote():
                    if not selected_ids:
                        ui.notify('Selecione pelo menos um militar.', color='warning')
                        return
                    cnt = 0
                    for ef_item in efetivo_lista:
                        ef_id = ef_item.get('id', ef_item.get('nome_guerra', ''))
                        if ef_id in selected_ids:
                            nome_g = ef_item.get('nome_guerra', '').upper()
                            salvar_presenca_unificada(
                                dt_str=dt_str,
                                nome_guerra=nome_g,
                                status_code=lote_status.value,
                                observacao=lote_obs.value or '',
                                user_id=ef_item.get('id'),
                                telegram_id=ef_item.get('telegram_id')
                            )
                            cnt += 1
                    if cnt > 0:
                        ui.notify(f'✅ {cnt} lançamento(s) salvo(s) com sucesso!', color='positive')
                        render_content.refresh()

                ui.button('✅ Aplicar em Lote', icon='playlist_add_check',
                          on_click=aplicar_lote
                ).props('unelevated color=amber text-color=black dense bold').classes('text-[11px]')

            # Tabela com checkboxes
            with ui.column().classes('w-full gap-1'):
                for ef in efetivo_lista:
                    nome_g = ef.get('nome_guerra', '').upper()
                    pres = find_presence_for_militar(ef, presencas_list, presencas_dict)
                    status_atual = pres.get('status', 'PENDENTE').upper()
                    obs_atual = pres.get('observacao', '')
                    hora_reg = pres.get('hora_presenca', '--:--')
                    ef_id = ef.get('id', nome_g)

                    info_sigla = SIGLAS_MILITARES.get(status_atual, {'nome': 'Pendente', 'icone': '⏳', 'badge_color': 'grey-7'})

                    row_bg = 'rgba(0,0,0,0.3)' if status_atual != 'PENDENTE' else 'rgba(100,100,100,0.15)'

                    with ui.row().classes('w-full justify-between items-center q-py-xs q-px-sm rounded-lg border border-cyan-500/10 hover:border-cyan-500/30 transition-all').style(f'background: {row_bg};'):
                        # Checkbox de seleção
                        def on_check(e, eid=ef_id):
                            if e.value:
                                selected_ids.add(eid)
                            else:
                                selected_ids.discard(eid)
                            lbl_sel.text = f'{len(selected_ids)} selecionado(s)'

                        cb = ui.checkbox('', on_change=on_check).classes('q-mr-xs')
                        checkbox_refs[ef_id] = cb

                        with ui.row().classes('items-center gap-2 flex-1'):
                            ui.label(info_sigla['icone']).classes('text-md')
                            ui.label(nome_g).classes('text-xs font-bold text-white')

                        with ui.row().classes('items-center gap-2'):
                            ui.badge(f"({status_atual}) {info_sigla['nome']}").props(f"color={info_sigla.get('badge_color', 'cyan')}").classes('text-[10px]')
                            if hora_reg and hora_reg != '--:--':
                                ui.label(f"⏰ {hora_reg[:5]}").classes('text-[10px] text-grey-4 font-mono')
                            if obs_atual:
                                ui.label(f"✍️ {obs_atual}").classes('text-[11px] text-cyan italic')

                        # Botão individual (mantido para casos específicos)
                        def alterar_status_dialog(militar=ef, st_act=status_atual, obs_act=obs_atual):
                            with ui.dialog() as dlg, ui.card().classes('w-96 bg-slate-900 border border-cyan-500/40 q-pa-md'):
                                ui.label(f"Lançar Presença: {militar['nome_guerra']}").classes('text-sm font-bold text-white cyber-title')
                                st_select = ui.select(
                                    {k: f"({k}) {v['nome']}" for k, v in SIGLAS_MILITARES.items()},
                                    value=st_act if st_act in SIGLAS_MILITARES else 'P',
                                    label='Situação / Sigla'
                                ).props('dark outlined w-full dense')
                                obs_in = ui.input('Observação / Justificativa', value=obs_act).props('dark outlined w-full dense')

                                def salvar_lancamento():
                                    salvar_presenca_unificada(
                                        dt_str=dt_str,
                                        nome_guerra=militar['nome_guerra'].upper(),
                                        status_code=st_select.value,
                                        observacao=obs_in.value or '',
                                        user_id=militar.get('id'),
                                        telegram_id=militar.get('telegram_id')
                                    )
                                    ui.notify(f"Lançamento de {militar['nome_guerra']} atualizado!", color='success')
                                    dlg.close()
                                    render_content.refresh()

                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=dlg.close).props('flat color=grey')
                                    ui.button('Salvar', on_click=salvar_lancamento).props('unelevated color=cyan text-color=black bold')
                            dlg.open()

                        ui.button('Lançar', icon='edit', on_click=alterar_status_dialog).props('flat color=cyan dense').classes('text-xs')

    data_selecionada.on_value_change(lambda: render_content.refresh())
    render_content()
