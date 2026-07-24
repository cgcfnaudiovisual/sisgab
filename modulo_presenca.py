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
    'MT': {'nome': 'Missão Tática / Operacional', 'icone': '⚔️', 'badge_color': 'deep-orange'},
    'FE': {'nome': 'Férias', 'icone': '🏖️', 'badge_color': 'blue'},
    'L': {'nome': 'Licença', 'icone': '📜', 'badge_color': 'purple'},
    'H': {'nome': 'Hospital', 'icone': '🏥', 'badge_color': 'red'},
    'DM': {'nome': 'Dispensa Médica', 'icone': '💊', 'badge_color': 'orange'},
    'S': {'nome': 'Serviço de Escala', 'icone': 'teal'},
}

def gerar_texto_pronto_chegab(data_str, presencas_dict, efetivo_lista):
    """Gera o texto oficial formatado no padrão da Sargenteação para o Chefe de Gabinete."""
    data_br = datetime.strptime(data_str, '%Y-%m-%d').strftime('%d/%m/%Y') if '-' in data_str else data_str
    
    linhas_militares = []
    for ef in efetivo_lista:
        nome_g = ef.get('nome_guerra', '').upper()
        p = presencas_dict.get(nome_g, {})
        sigla = p.get('status', 'PENDENTE').upper()
        obs = p.get('observacao', '').strip()
        
        txt_linha = f"{nome_g} - {sigla}"
        if obs:
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
        "(MT) - Missão Tática; e\n"
        "(S) - Serviço.\n\n"
        "Atenciosamente,\n"
        "Sargenteante do Gabinete"
    )
    return texto


def render_page():
    ui.label('📋 CHAMADA MATUTINA & PRONTO AO CHEGAB').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    
    data_selecionada = ui.input('Data da Chamada', value=datetime.now().strftime('%Y-%m-%d')).props('type=date dark outlined dense').classes('w-48 q-mb-md q-ml-md')

    @ui.refreshable
    def render_content():
        dt_str = data_selecionada.value or datetime.now().strftime('%Y-%m-%d')
        
        db = get_service_db_connection() or get_db_connection()
        efetivo_lista = []
        presencas_list = []
        
        if db:
            try:
                res_ef = db.table('efetivo').select('*').order('nome_guerra').execute()
                efetivo_lista = res_ef.data or []
            except Exception as e:
                print(f"[PRESENCA LOAD EFETIVO ERR] {e}")
                
            try:
                res_pr = db.table('presenca_diaria').select('*').eq('data', dt_str).execute()
                presencas_list = res_pr.data or []
            except Exception as e:
                print(f"[PRESENCA LOAD DIARIA ERR] {e}")

        # Mapeia presencas por nome_guerra
        presencas_dict = {p['nome_guerra'].upper(): p for p in presencas_list}
        
        # Contadores de estatísticas
        tot_efetivo = len(efetivo_lista)
        contadores = {'P': 0, 'MA': 0, 'MT': 0, 'FE': 0, 'L': 0, 'H': 0, 'DM': 0, 'S': 0, 'PENDENTE': 0}
        
        for ef in efetivo_lista:
            nome_g = ef.get('nome_guerra', '').upper()
            st = presencas_dict.get(nome_g, {}).get('status', 'PENDENTE').upper()
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
                    
                    # Botão para copiar texto do Pronto para o CheGab
                    def copiar_pronto():
                        txt = gerar_texto_pronto_chegab(dt_str, presencas_dict, efetivo_lista)
                        ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(txt)})')
                        ui.notify('📋 Pronto do CheGab copiado com sucesso! Envie no WhatsApp/Telegram.', color='positive', duration=5)
                        
                    ui.button('📋 Copiar Pronto ao CheGab', icon='content_copy', on_click=copiar_pronto).props('unelevated color=green text-color=white bold').classes('q-py-xs text-xs')

                # Chips de contagem
                with ui.row().classes('w-full gap-2 q-mt-md flex-wrap text-xs'):
                    ui.badge(f"🟢 Presentes (P): {contadores['P']}").props('color=green bold').classes('q-pa-xs')
                    ui.badge(f"💼 Missão Adm (MA): {contadores['MA']}").props('color=cyan bold').classes('q-pa-xs')
                    ui.badge(f"⚔️ Missão Tática (MT): {contadores['MT']}").props('color=deep-orange bold').classes('q-pa-xs')
                    ui.badge(f"🏖️ Férias (FE): {contadores['FE']}").props('color=blue bold').classes('q-pa-xs')
                    ui.badge(f"📜 Licença (L): {contadores['L']}").props('color=purple bold').classes('q-pa-xs')
                    ui.badge(f"🏥 Hospital (H): {contadores['H']}").props('color=red bold').classes('q-pa-xs')
                    ui.badge(f"💊 Disp. Médica (DM): {contadores['DM']}").props('color=orange bold').classes('q-pa-xs')
                    ui.badge(f"🛡️ Serviço (S): {contadores['S']}").props('color=teal bold').classes('q-pa-xs')
                    ui.badge(f"⏳ Pendentes: {contadores['PENDENTE']}").props('color=grey-7 bold').classes('q-pa-xs')

            # TABELA DE MILITARES E STATUS
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl bg-slate-900 border border-cyan-500/20'):
                ui.label('👥 Relação do Efetivo do Gabinete').classes('text-sm font-bold text-white q-mb-xs')
                
                with ui.column().classes('w-full gap-2'):
                    for ef in efetivo_lista:
                        nome_g = ef.get('nome_guerra', '').upper()
                        pres = presencas_dict.get(nome_g, {})
                        status_atual = pres.get('status', 'PENDENTE').upper()
                        obs_atual = pres.get('observacao', '')
                        hora_reg = pres.get('hora_presenca', '--:--')
                        
                        info_sigla = SIGLAS_MILITARES.get(status_atual, {'nome': 'Pendente', 'icone': '⏳', 'badge_color': 'grey-7'})
                        
                        with ui.row().classes('w-full justify-between items-center q-py-xs q-px-md bg-black/40 rounded-lg border border-cyan-500/10 hover:border-cyan-500/30 transition-all'):
                            with ui.row().classes('items-center gap-3 col-12 col-md-4'):
                                ui.label(info_sigla['icone']).classes('text-md')
                                ui.label(nome_g).classes('text-xs font-bold text-white')
                            
                            with ui.row().classes('items-center gap-2 col-12 col-md-5'):
                                ui.badge(f"({status_atual}) {info_sigla['nome']}").props(f"color={info_sigla.get('badge_color', 'cyan')}").classes('text-[10px]')
                                if hora_reg and hora_reg != '--:--':
                                    ui.label(f"⏰ {hora_reg[:5]}").classes('text-[10px] text-grey-4 font-mono')
                                if obs_atual:
                                    ui.label(f"✍️ {obs_atual}").classes('text-[11px] text-cyan italic')

                            # Ação de edição manual para o Sargenteante
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
                                        db_w = get_service_db_connection() or get_db_connection()
                                        if db_w:
                                            import uuid
                                            reg_data = {
                                                'id': pres.get('id', str(uuid.uuid4())),
                                                'user_id': militar.get('id'),
                                                'telegram_id': militar.get('telegram_id'),
                                                'nome_guerra': militar['nome_guerra'].upper(),
                                                'data': dt_str,
                                                'hora_presenca': datetime.now().strftime('%H:%M:%S'),
                                                'status': st_select.value,
                                                'observacao': obs_in.value or '',
                                                'criado_em': datetime.now().isoformat()
                                            }
                                            db_w.table('presenca_diaria').upsert(reg_data, on_conflict='id').execute()
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
