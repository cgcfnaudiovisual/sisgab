from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection, execute_query_safe

THEME = theme.colors

def render_page():
    ui.label('🔋 CAUTELA DE EQUIPAMENTOS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_operator = user_role in ('admin', 'supervisor', 'operador', 'comcia')

    # Estado local do formulário
    cautela_state = {
        'equipamento_nome': '',
        'pauta_id': None,
        'e_pessoal': False,
        'conflito': False,
        'conflito_msg': ''
    }

    # Elementos de interface para atualização
    warning_card = None
    warning_lbl = None

    def verificar_conflitos():
        equip = cautela_state['equipamento_nome'].strip().upper()
        pauta_id = cautela_state['pauta_id']
        
        cautela_state['conflito'] = False
        cautela_state['conflito_msg'] = ''
        
        if not equip:
            if warning_card:
                warning_card.visible = False
            return
            
        db = get_db_connection()
        if db:
            try:
                # 1. Verifica se já está cautelado fisicamente (status = retirado)
                res_retirados = db.table('cautela_equipamentos').select('*').eq('equipamento', equip).eq('status', 'retirado').execute()
                if res_retirados.data:
                    cautela_state['conflito'] = True
                    cautela_state['conflito_msg'] = f"Atenção: O equipamento '{equip}' já está retirado por {res_retirados.data[0]['retirado_por']}!"
                    
                # 2. Se houver pauta vinculada, faz a checagem de agenda
                if pauta_id and not cautela_state['conflito']:
                    res_pauta = db.table('demandas_comunicacao').select('data_evento, titulo_evento').eq('id', pauta_id).execute()
                    if res_pauta.data:
                        data_evento = res_pauta.data[0]['data_evento']
                        
                        # Verifica se existe outra reserva de cautela na mesma data
                        res_choque = db.table('cautela_equipamentos').select('*, demandas_comunicacao(titulo_evento)').eq('equipamento', equip).eq('event_date', data_evento).eq('status', 'retirado').execute()
                        if res_choque.data:
                            cautela_state['conflito'] = True
                            evento_choque = "outro evento"
                            if res_choque.data[0].get('demandas_comunicacao'):
                                evento_choque = res_choque.data[0]['demandas_comunicacao']['titulo_evento']
                            cautela_state['conflito_msg'] = f"Choque de Agenda: Este item já está alocado para o evento '{evento_choque}' na mesma data ({data_evento})!"
            except Exception as e:
                print(f"[CONFLITO CHECK ERR] {e}")

        if warning_card and warning_lbl:
            warning_lbl.text = cautela_state['conflito_msg']
            warning_card.visible = cautela_state    # Layout de Abas com Estilo Seletor por Botões
    active_tab = 'cautelas'

    @ui.refreshable
    def render_tab_selectors():
        with ui.row().classes('w-full gap-3 q-mb-md justify-start items-center'):
            # Botão 1: Cautelas
            btn_cautelas_style = 'unelevated color=primary text-color=black' if active_tab == 'cautelas' else 'flat color=grey text-color=white'
            ui.button(
                '⚡ Cautelas & Retiradas', 
                icon='battery_charging_full', 
                on_click=lambda: select_tab('cautelas')
            ).props(btn_cautelas_style).classes('font-bold')

            # Botão 2: Catálogo
            btn_catalogo_style = 'unelevated color=primary text-color=black' if active_tab == 'catalogo' else 'flat color=grey text-color=white'
            ui.button(
                '📋 Catálogo de Equipamentos', 
                icon='inventory', 
                on_click=lambda: select_tab('catalogo')
            ).props(btn_catalogo_style).classes('font-bold')

    def select_tab(name):
        nonlocal active_tab
        active_tab = name
        render_tab_selectors.refresh()
        render_panels.refresh()

    @ui.refreshable
    def render_panels():
        if active_tab == 'cautelas':
            # PANEL 1: Cautelas e Retiradas
            with ui.column().classes('w-full p-0'):
                @ui.refreshable
                def render_cautelas_panel():
                    pautas_options = {}
                    equipamentos_options = {}
                    db = get_db_connection()
                    if db:
                        try:
                            # Carregar pautas aprovadas
                            res_p = db.table('demandas_comunicacao').select('id, titulo_evento, data_evento').eq('status', 'aprovada').execute()
                            if res_p.data:
                                pautas_options = {p['id']: f"{p['titulo_evento']} ({p['data_evento']})" for p in res_p.data}
                            
                            # Carregar catálogo de equipamentos
                            res_e = db.table('comsoc_equipamentos').select('*').order('nome').execute()
                            if res_e.data:
                                equipamentos_options = {
                                    e['nome']: f"{e['nome']} {'(Pessoal/Restrito 🔒)' if e.get('e_pessoal') == 1 else '(Público 🌐)'}"
                                    for e in res_e.data
                                }
                        except Exception as e:
                            print(f"[DB CAUTELA LOAD ERR] {e}")

                    with ui.row().classes('w-full gap-4 items-stretch justify-start'):
                        # Formulário de Nova Retirada
                        with ui.column().classes('col-12 col-md-5 gap-4'):
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                            ):
                                ui.label('⚡ Registrar Saída de Material').classes('text-md font-bold text-cyan q-mb-md')
                                
                                # Select de equipamento integrado ao Catálogo
                                if equipamentos_options:
                                    equip_select = ui.select(
                                        equipamentos_options,
                                        label='Selecionar Equipamento',
                                        on_change=lambda e: (
                                            cautela_state.update({'equipamento_nome': e.value}),
                                            verificar_e_pessoal_catalogo(e.value),
                                            verificar_conflitos()
                                        )
                                    ).props('dark outlined dense w-full option-dark')
                                else:
                                    ui.label('⚠️ Nenhum equipamento cadastrado no catálogo. Vá ao Catálogo para adicionar itens.').classes('text-xs text-amber-5 q-my-sm')
                                    equip_select = None

                                nome_input = ui.input(
                                    'Retirado por (Militar)',
                                    value=user_data.get('nome_guerra', '').upper()
                                ).props('dark outlined dense w-full')
                                
                                # Dropdown de Pautas
                                ui.select(
                                    pautas_options,
                                    label='Vincular à Pauta / Evento',
                                    on_change=lambda e: (cautela_state.update({'pauta_id': e.value}), verificar_conflitos())
                                ).props('dark outlined dense w-full option-dark')

                                chk_pessoal = ui.checkbox(
                                    'Equipamento de Uso Pessoal / Restrito', 
                                    value=False,
                                    on_change=lambda e: cautela_state.update({'e_pessoal': e.value})
                                ).classes('text-xs text-grey-4 q-mt-xs')

                                # Card de Alerta de Conflito
                                nonlocal warning_card, warning_lbl
                                with ui.card().classes('w-full q-pa-sm bg-red-950/40 border border-red-500 rounded-lg q-mt-md').style('display: none;') as warning_card:
                                    with ui.row().classes('items-center gap-2 text-red-400 text-xs font-bold no-wrap'):
                                        ui.icon('warning', size='sm')
                                        warning_lbl = ui.label('Atenção: Equipamento indisponível para este horário!')

                                def verificar_e_pessoal_catalogo(nome_equip):
                                    conn_ep = get_db_connection()
                                    if conn_ep:
                                        try:
                                            res_ep = conn_ep.table('comsoc_equipamentos').select('e_pessoal').eq('nome', nome_equip).execute()
                                            if res_ep.data and res_ep.data[0].get('e_pessoal') == 1:
                                                chk_pessoal.value = True
                                                cautela_state['e_pessoal'] = True
                                            else:
                                                chk_pessoal.value = False
                                                cautela_state['e_pessoal'] = False
                                        except Exception as ex_ep:
                                            print(f"[ERR CHECK E_PESSOAL] {ex_ep}")

                                def salvar_cautela():
                                    if not equip_select or not equip_select.value or not nome_input.value:
                                        ui.notify('Preencha os campos obrigatórios.', color='warning')
                                        return
                                    
                                    conn = get_db_connection()
                                    if conn:
                                        try:
                                            data_ev = None
                                            if cautela_state['pauta_id']:
                                                res_p = conn.table('demandas_comunicacao').select('data_evento').eq('id', cautela_state['pauta_id']).execute()
                                                if res_p.data:
                                                    data_ev = res_p.data[0]['data_evento']

                                            registro = {
                                                'equipamento': equip_select.value.upper(),
                                                'retirado_por': nome_input.value.upper(),
                                                'data_retirada': datetime.now().isoformat(),
                                                'pauta_id': cautela_state['pauta_id'],
                                                'status': 'retirado',
                                                'e_pessoal': 1 if cautela_state['e_pessoal'] else 0,
                                                'event_date': data_ev
                                            }
                                            conn.table('cautela_equipamentos').insert(registro).execute()
                                            ui.notify('Equipamento retirado com sucesso!', color='success')
                                            
                                            if equip_select:
                                                equip_select.value = None
                                            cautela_state['pauta_id'] = None
                                            render_cautelas_panel.refresh()
                                        except Exception as ex:
                                            ui.notify(f'Erro ao salvar: {ex}', color='red')

                                ui.button(
                                    'Confirmar Retirada', 
                                    icon='check', 
                                    on_click=salvar_cautela
                                ).props('unelevated color=primary text-color=black bold w-full q-mt-md').classes('w-full font-bold')

                        # Lista de Cautelas Ativas
                        with ui.column().classes('col-12 col-md-6 gap-4'):
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                            ):
                                ui.label('🔌 Equipamentos em Cautela (Ativos)').classes('text-md font-bold text-cyan q-mb-md')
                                
                                cautelas = []
                                conn = get_db_connection()
                                if conn:
                                    try:
                                        res_c = conn.table('cautela_equipamentos').select('*').eq('status', 'retirado').execute()
                                        cautelas = res_c.data if res_c.data else []
                                    except Exception as e:
                                        print(f"[DB CAUTELAS LIST ERR] {e}")
                                        
                                if cautelas:
                                    for c in cautelas:
                                        with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                            'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);'
                                        ):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                with ui.column().classes('gap-0'):
                                                    ui.row().classes('items-center gap-2')
                                                    ui.label(c['equipamento']).classes('text-xs font-bold text-white')
                                                    if c.get('e_pessoal') == 1:
                                                        ui.badge('Pessoal').props('color=amber text-color=black dense').classes('text-[9px]')
                                                    
                                                    ui.label(f"Retirado por: {c['retirado_por']}").classes('text-[10px] text-grey')
                                                    if c.get('event_date'):
                                                        ui.label(f"Reserva Evento: {c['event_date']}").classes('text-[9px] text-cyan')
                                                    ui.label(f"Retirada em: {c['data_retirada'][:16].replace('T', ' ')}").classes('text-[9px] text-grey-4')
                                                
                                                def devolver_cautela(c_id=c['id']):
                                                    db_c = get_db_connection()
                                                    if db_c:
                                                        try:
                                                            db_c.table('cautela_equipamentos').update({
                                                                'status': 'devolvido',
                                                                'data_devolucao': datetime.now().isoformat()
                                                            }).eq('id', c_id).execute()
                                                            ui.notify('Equipamento devolvido com sucesso!', color='success')
                                                            render_cautelas_panel.refresh()
                                                        except Exception as ex:
                                                            ui.notify(f'Erro na devolução: {ex}', color='red')
                                                            
                                                ui.button(
                                                    'Devolver', 
                                                    icon='assignment_returned', 
                                                    on_click=lambda c_id=c['id']: devolver_cautela(c_id)
                                                ).props('unelevated color=amber-9 text-color=black dense bold').classes('text-[9px] q-px-sm')
                                else:
                                    with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-4'):
                                        ui.icon('check_circle', size='3rem', color='green')
                                        ui.label('Todos os equipamentos encontram-se em estoque.').classes('text-xs')
                render_cautelas_panel()

        elif active_tab == 'catalogo':
            # PANEL 2: Catálogo de Equipamentos (Adicionar/Retirar da Lista)
            with ui.column().classes('w-full p-0'):
                @ui.refreshable
                def render_catalogo_panel():
                    with ui.row().classes('w-full gap-4 items-stretch justify-start'):
                        # Cadastrar Equipamento no Catálogo
                        with ui.column().classes('col-12 col-md-5 gap-4'):
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                            ):
                                ui.label('➕ Adicionar ao Catálogo').classes('text-md font-bold text-cyan q-mb-md')
                                
                                c_nome = ui.input('Nome do Equipamento', placeholder='Ex: Câmera Sony Alpha 7 IV').props('dark outlined dense w-full')
                                c_desc = ui.input('Descrição / Observações').props('dark outlined dense w-full')
                                c_pessoal = ui.checkbox('Uso Restrito / Pessoal (Apenas o dono pode reservar)').classes('text-xs text-grey-4')

                                def cadastrar_item():
                                    if not c_nome.value:
                                        ui.notify('Informe o nome do equipamento.', color='warning')
                                        return
                                    conn = get_db_connection()
                                    if conn:
                                        try:
                                            conn.table('comsoc_equipamentos').insert({
                                                'nome': c_nome.value.strip().upper(),
                                                'e_pessoal': 1 if c_pessoal.value else 0,
                                                'descricao': c_desc.value or ''
                                            }).execute()
                                            ui.notify('Equipamento cadastrado com sucesso!', color='success')
                                            c_nome.value = ''
                                            c_desc.value = ''
                                            c_pessoal.value = False
                                            render_catalogo_panel.refresh()
                                        except Exception as ex:
                                            ui.notify(f'Erro ao cadastrar: {ex}', color='red')

                                ui.button(
                                    'Salvar no Catálogo',
                                    icon='save',
                                    on_click=cadastrar_item
                                ).props('unelevated color=cyan-9 text-color=white bold w-full q-mt-md')

                        # Listagem e Exclusão do Catálogo
                        with ui.column().classes('col-12 col-md-6 gap-4'):
                            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                            ):
                                ui.label('📋 Equipamentos Cadastrados').classes('text-md font-bold text-cyan q-mb-md')
                                
                                itens = []
                                conn = get_db_connection()
                                if conn:
                                    try:
                                        res_items = conn.table('comsoc_equipamentos').select('*').order('nome').execute()
                                        itens = res_items.data if res_items.data else []
                                    except Exception as e:
                                        print(f"[DB LIST CATALOG ERR] {e}")

                                if itens:
                                    for item in itens:
                                        with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                            'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04)'
                                        ):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                with ui.column().classes('gap-0'):
                                                    ui.row().classes('items-center gap-2')
                                                    ui.label(item['nome']).classes('text-xs font-bold text-white')
                                                    if item.get('e_pessoal') == 1:
                                                        ui.badge('Pessoal / Restrito').props('color=amber text-color=black dense').classes('text-[9px]')
                                                    else:
                                                        ui.badge('Público').props('color=blue dense').classes('text-[9px]')
                                                    if item.get('descricao'):
                                                        ui.label(item['descricao']).classes('text-[10px] text-grey-4 q-mt-xs')

                                                def remover_item(item_id=item['id']):
                                                    conn_del = get_db_connection()
                                                    if conn_del:
                                                        try:
                                                            conn_del.table('comsoc_equipamentos').delete().eq('id', item_id).execute()
                                                            ui.notify('Equipamento removido do catálogo.', color='success')
                                                            render_catalogo_panel.refresh()
                                                        except Exception as ex:
                                                            ui.notify(f'Erro ao remover: {ex}', color='red')

                                                ui.button(
                                                    'Excluir',
                                                    icon='delete',
                                                    on_click=lambda id_item=item['id']: remover_item(id_item)
                                                ).props('unelevated color=red-9 text-color=white dense').classes('text-[9px] q-px-sm')
                                else:
                                    with ui.column().classes('w-full items-center justify-center q-py-lg text-grey-4'):
                                        ui.icon('inventory', size='3rem')
                                        ui.label('Nenhum item cadastrado no catálogo.').classes('text-xs')
                render_catalogo_panel()

    render_tab_selectors()
    render_panels()
