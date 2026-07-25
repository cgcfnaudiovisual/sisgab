import io
import json
from datetime import datetime
import pandas as pd
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

# Estado local do módulo (reativo por usuário na sessão se necessário, mas mantido na UI do NiceGUI)
class ModuleState:
    def __init__(self):
        self.selected_event_id = None
        self.edit_mode = "alocacao"  # "alocacao" ou "layout"
        self.search_query = ""
        self.filter_category = "Todos"
        self.filter_only_unallocated = False

# Inicializar estado na memória do app por conexão do NiceGUI
state = ModuleState()

def get_row_label(index):
    """Retorna 'A', 'B', ... 'Z', 'AA', etc."""
    label = ""
    while index >= 0:
        label = chr(index % 26 + 65) + label
        index = index // 26 - 1
    return label

def sync_companions(main_guest_id, main_guest_name, max_acomp, event_id, category):
    db = get_service_db_connection() or get_db_connection()
    if not db:
        return
    try:
        # 1. Buscar acompanhantes existentes
        res = db.table('jade_convidados').select('*').eq('convidado_principal_id', main_guest_id).order('id', desc=False).execute()
        existing = res.data if res.data else []
        existing_count = len(existing)
        
        # 2. Se precisamos de mais
        if existing_count < max_acomp:
            needed = max_acomp - existing_count
            new_comps = []
            for i in range(existing_count + 1, max_acomp + 1):
                new_comps.append({
                    'evento_id': event_id,
                    'nome': f"ACOMP. {main_guest_name} ({i}/{max_acomp})",
                    'categoria': category,
                    'convidado_principal_id': main_guest_id,
                    'max_acompanhantes': 0,
                    'cargo_funcao': f"Acompanhante de {main_guest_name}"
                })
            if new_comps:
                db.table('jade_convidados').insert(new_comps).execute()
            
        # 3. Se temos demais (deleta excedentes mais novos)
        elif existing_count > max_acomp:
            to_delete = existing[max_acomp:]
            delete_ids = [d['id'] for d in to_delete]
            if delete_ids:
                db.table('jade_convidados').delete().in_('id', delete_ids).execute()

        # 4. Atualiza obrigatoriamente nomes, categorias e índices de todos os acompanhantes remanescentes
        res_remaining = db.table('jade_convidados').select('*').eq('convidado_principal_id', main_guest_id).order('id', desc=False).execute()
        remaining = res_remaining.data if res_remaining.data else []
        for idx, comp in enumerate(remaining, 1):
            db.table('jade_convidados').update({
                'nome': f"ACOMP. {main_guest_name} ({idx}/{max_acomp})",
                'categoria': category,
                'cargo_funcao': f"Acompanhante de {main_guest_name}"
            }).eq('id', comp['id']).execute()
    except Exception as e:
        print(f"[SYNC COMPANIONS ERR] {e}")


def render_page():
    ui.label('🪑 PROJETAR ASSENTOS (PLACAS JADE)').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_name = user_data.get('nome_guerra', 'Operador')
    
    # Refreshable principal do conteúdo do painel
    @ui.refreshable
    def render_content():
        db = get_db_connection()
        if not db:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('cloud_off', size='4rem')
                ui.label('Banco de dados não disponível. Verifique a conexão.').classes('text-md font-bold')
            return

        # 1. Carregar lista de eventos
        eventos = []
        try:
            res_ev = db.table('jade_eventos').select('*').order('data_evento', desc=True).execute()
            eventos = res_ev.data if res_ev.data else []
        except Exception as e:
            print(f"[JADE EVENTS FETCH ERR] {e}")

        # Se não há evento selecionado e existem eventos, seleciona o primeiro
        if not state.selected_event_id and eventos:
            state.selected_event_id = eventos[0]['id']

        # Encontra dados do evento selecionado
        current_event = next((e for e in eventos if e['id'] == state.selected_event_id), None)

        # Cabeçalho de Controle de Eventos
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.row().classes('w-full items-center justify-between wrap-mobile gap-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.label('Solenidade Ativa:').classes('text-xs text-grey-4 font-bold')
                    
                    if eventos:
                        event_options = {e['id']: f"{e['nome']} ({e['data_evento']})" for e in eventos}
                        ui.select(
                            options=event_options,
                            value=state.selected_event_id,
                            on_change=lambda e: select_event(e.value)
                        ).props('dark outlined dense').style('min-width: 280px;')
                    else:
                        ui.label('Nenhum evento cadastrado.').classes('text-sm text-amber font-bold')

                with ui.row().classes('items-center gap-2'):
                    ui.button(
                        'Novo Evento', 
                        icon='add', 
                        on_click=open_create_event_dialog
                    ).props('unelevated color=primary text-color=black dense').classes('q-px-sm')
                    
                    if current_event:
                        ui.button(
                            'Editar Evento',
                            icon='edit',
                            on_click=lambda: open_edit_event_dialog(current_event, layout)
                        ).props('unelevated color=accent dense outline').classes('q-px-sm')
                        
                        ui.button(
                            'Excluir Evento', 
                            icon='delete', 
                            on_click=lambda: confirm_delete_event(current_event)
                        ).props('unelevated color=danger dense outline').classes('q-px-sm')

        if not current_event:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-4'):
                ui.icon('event_seat', size='5rem', color='cyan')
                ui.label('Por favor, crie um evento para iniciar o mapeamento de assentos.').classes('text-md text-white font-bold')
                ui.button('Criar Primeiro Evento', icon='add', on_click=open_create_event_dialog).props('unelevated color=primary text-color=black')
            return

        # Carregar convidados do evento ativo
        convidados = []
        try:
            res_conv = db.table('jade_convidados').select('*').eq('evento_id', current_event['id']).execute()
            convidados = res_conv.data if res_conv.data else []
        except Exception as e:
            print(f"[JADE GUESTS FETCH ERR] {e}")

        # Parse do layout do evento
        layout = {}
        try:
            layout = json.loads(current_event['layout_json']) if current_event.get('layout_json') else {}
        except Exception as e:
            print(f"[LAYOUT PARSE ERR] {e}")
            
        rows_count = layout.get('rows', 5)
        cols_count = layout.get('cols', 8)
        blocked_seats = layout.get('blocked_seats', [])

        # Lista de categorias encontradas nos convidados para o filtro
        categories = sorted(list(set(c['categoria'] for c in convidados if c.get('categoria'))))
        category_options = ["Todos"] + categories

        # Divisão da página
        with ui.row().classes('w-full gap-4 wrap-mobile items-stretch justify-start'):
            
            # --- COLUNA ESQUERDA: LISTA DE CONVIDADOS ---
            with ui.column().classes('col-12 col-md-4 q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 550px;'
                ):
                    ui.label('👥 Convidados').classes('text-md font-bold text-cyan q-mb-md')
                    
                    # Filtros de Convidados
                    with ui.row().classes('w-full gap-2 items-center q-mb-sm'):
                        ui.input(
                            placeholder='Buscar por nome ou cargo...',
                            on_change=lambda e: update_search(e.value)
                        ).props('dark outlined dense clearable').classes('col')
                        
                        ui.select(
                            options=category_options,
                            value=state.filter_category,
                            on_change=lambda e: update_filter_category(e.value)
                        ).props('dark outlined dense').style('width: 110px;')
                        
                    ui.checkbox(
                        'Apenas não alocados', 
                        value=state.filter_only_unallocated,
                        on_change=lambda e: update_filter_unallocated(e.value)
                    ).props('dark dense').classes('text-xs text-grey-4 q-mb-md')
                    
                    # Lista de cards dos convidados
                    with ui.column().classes('w-full gap-2 q-mb-md scroll-container').style('max-height: 380px; overflow-y: auto;'):
                        # Filtrar convidados localmente
                        filtered_convidados = convidados
                        if state.search_query:
                            q = state.search_query.lower()
                            filtered_convidados = [
                                c for c in filtered_convidados 
                                if q in c['nome'].lower() or 
                                (c.get('cargo_funcao') and q in c['cargo_funcao'].lower()) or
                                (c.get('posto_graduacao') and q in c['posto_graduacao'].lower())
                            ]
                        if state.filter_category != "Todos":
                            filtered_convidados = [c for c in filtered_convidados if c.get('categoria') == state.filter_category]
                        if state.filter_only_unallocated:
                            filtered_convidados = [c for c in filtered_convidados if not c.get('assento_id')]

                        if filtered_convidados:
                            for c in filtered_convidados:
                                is_allocated = bool(c.get('assento_id'))
                                card_bg = 'rgba(0, 229, 255, 0.05)' if is_allocated else 'rgba(255, 255, 255, 0.02)'
                                card_border = 'rgba(0, 229, 255, 0.2)' if is_allocated else 'rgba(255, 255, 255, 0.05)'
                                
                                with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style(
                                    f'background: {card_bg}; border: 1px solid {card_border};'
                                ):
                                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                                        with ui.column().classes('gap-0 col'):
                                            # Exibe Posto + Nome ou apenas Nome
                                            nome_exibicao = f"{c.get('posto_graduacao') or ''} {c['nome']}".strip()
                                            ui.label(nome_exibicao).classes('text-xs font-bold text-white')
                                            
                                            sub_label = c.get('cargo_funcao') or c.get('categoria') or 'Convidado'
                                            ui.label(sub_label).classes('text-[10px] text-grey-4')
                                            
                                            # Acompanhantes
                                            if c.get('max_acompanhantes', 0) > 0:
                                                ui.label(f"Acompanhantes: {c['max_acompanhantes']}").classes('text-[9px] text-amber')
                                                
                                        # Status do assento
                                        with ui.row().classes('items-center gap-1'):
                                            if is_allocated:
                                                ui.badge(f"Assento {c['assento_id']}").props('color=cyan text-color=black').classes('text-[9px]')
                                                ui.button(
                                                    icon='cancel', 
                                                    on_click=lambda c=c: remove_guest_allocation(c)
                                                ).props('unelevated color=danger dense flat round').classes('text-xs')
                                            else:
                                                ui.badge('Não Alocado').props('color=grey-7').classes('text-[9px]')
                                                
                                            # Botão editar convidado
                                            ui.button(
                                                icon='edit',
                                                on_click=lambda c=c: open_edit_guest_dialog(c)
                                            ).props('unelevated color=primary dense flat round').classes('text-xs')
                                            
                                            # Botão excluir convidado
                                            ui.button(
                                                icon='delete',
                                                on_click=lambda c=c: confirm_delete_guest(c)
                                            ).props('unelevated color=danger dense flat round').classes('text-xs')
                        else:
                            with ui.column().classes('w-full items-center justify-center q-py-lg text-grey'):
                                ui.icon('person_off', size='2.5rem')
                                ui.label('Nenhum convidado encontrado.').classes('text-xs q-mt-xs')
                    
                    # Botões de Ação na base da lista
                    ui.separator().classes('q-my-md').style('border-color: rgba(255,255,255,0.05);')
                    
                    with ui.row().classes('w-full justify-between gap-2'):
                        ui.button(
                            'Modelo Excel', 
                            icon='download', 
                            on_click=download_template
                        ).props('unelevated color=cyan dense outline').classes('col text-xs')
                        
                        # Upload para importação
                        with ui.button('Importar Lista', icon='upload').props('unelevated color=primary text-color=black dense').classes('col text-xs'):
                            ui.upload(
                                on_upload=lambda e: handle_import_list(e, current_event['id']),
                                multiple=False,
                                auto_upload=True
                            ).props('dark accept=.xlsx,.csv').classes('hidden')
                            
                    ui.button(
                        'Adicionar Convidado Manual', 
                        icon='person_add', 
                        on_click=lambda: open_edit_guest_dialog(None, current_event['id'])
                    ).props('unelevated color=primary text-color=black dense w-full q-mt-sm').classes('w-full text-xs')

            # --- COLUNA DIREITA: GRID DO MAPA DE ASSENTOS ---
            with ui.column().classes('col-12 col-md q-pa-none').style('flex-grow: 1;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 550px;'
                ):
                    with ui.row().classes('w-full items-center justify-between q-mb-md wrap-mobile gap-2'):
                        with ui.column().classes('gap-0'):
                            ui.label('🗺️ Mapa de Assentos').classes('text-md font-bold text-cyan')
                            ui.label(f"Layout atual: {rows_count} fileiras × {cols_count} colunas").classes('text-[11px] text-grey')
                        
                        # Seletor de Modo de Edição
                        with ui.row().classes('items-center bg-black-10 rounded-lg q-pa-xs border border-white-10'):
                            ui.button(
                                'Alocação', 
                                icon='event_seat', 
                                on_click=lambda: toggle_mode("alocacao")
                            ).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "alocacao" else "flat text-color=grey"}').classes('text-xs q-px-sm')
                            
                            ui.button(
                                'Editor Layout', 
                                icon='edit_road', 
                                on_click=lambda: toggle_mode("layout")
                            ).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "layout" else "flat text-color=grey"}').classes('text-xs q-px-sm')

                    # Grid Renderizado
                    # Dicionário de Assento -> Convidado
                    allocated_map = {}
                    for c in convidados:
                        if c.get('assento_id'):
                            allocated_map[c['assento_id']] = c

                    # Renderizador de Grid HTML/CSS embutido responsivo
                    with ui.column().classes('w-full items-center justify-start q-py-md scroll-container').style('overflow-x: auto;'):
                        # Referência Superior (Palco, etc.)
                        ref_top = layout.get('ref_top', 'PALCO PRINCIPAL')
                        if ref_top:
                            with ui.row().classes('w-full justify-center q-mb-sm'):
                                ui.label(f"▲ {ref_top.upper()} ▲").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

                        # Grid de Assentos
                        with ui.grid(columns=cols_count + 1).classes('gap-2 items-center').style('min-width: 600px;'):
                            # Célula canto superior esquerdo (vazia)
                            ui.label('').classes('text-center font-bold text-grey-5').style('width: 40px;')
                            
                            # Cabeçalhos das Colunas (1, 2, 3...)
                            for col in range(1, cols_count + 1):
                                ui.label(str(col)).classes('text-center font-bold text-grey-5').style('width: 70px; font-size: 11px;')
                                
                            # Fileiras (A, B, C...)
                            for r in range(rows_count):
                                row_label = get_row_label(r)
                                # Lote da Fileira (Cabeçalho lateral)
                                ui.label(row_label).classes('text-center font-bold text-grey-5 text-md').style('width: 40px;')
                                
                                for col in range(1, cols_count + 1):
                                    seat_id = f"{row_label}-{col}"
                                    is_blocked = seat_id in blocked_seats
                                    guest = allocated_map.get(seat_id)
                                    
                                    # Estilo do assento baseado no estado
                                    if is_blocked:
                                        # Espaço vazio / Corredor
                                        if state.edit_mode == "layout":
                                            with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105').style(
                                                'width: 70px; height: 48px; border: 1px dashed rgba(255,255,255,0.15); border-radius: 4px; background: rgba(255,255,255,0.02); gap: 0;'
                                            ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                                ui.label(seat_id).classes('text-[8px] text-grey-5 font-mono')
                                                ui.label('CORREDOR').classes('text-[7px] text-grey-6 font-bold')
                                        else:
                                            # Apenas espaço em branco
                                            ui.label('').style('width: 70px; height: 48px;')
                                    else:
                                        if guest:
                                            # Cadeira Ocupada
                                            display_name = f"{guest.get('posto_graduacao') or ''} {guest['nome']}".strip()
                                            if len(display_name) > 12:
                                                display_name = display_name[:10] + '..'
                                                
                                            # Cores por categoria
                                            is_vip = guest.get('categoria') == 'VIP'
                                            border_c = THEME['primary'] if is_vip else THEME['accent']
                                            bg_c = 'rgba(0, 229, 255, 0.15)' if is_vip else 'rgba(0, 162, 255, 0.15)'
                                            text_c = THEME['primary'] if is_vip else THEME['accent']
                                            
                                            with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                                f'width: 70px; height: 48px; border-radius: 4px; border-color: {border_c} !important; background: {bg_c}; gap: 0;'
                                            ).on('click', lambda s=seat_id, g=guest: open_seat_actions_dialog(s, g, convidados, current_event['id'])):
                                                ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                                ui.label(display_name).classes('text-[9px] font-bold text-center leading-none text-white overflow-hidden w-full')
                                                
                                                category_label = str(guest.get('categoria', 'Geral')).upper()
                                                if len(category_label) > 10:
                                                    category_label = category_label[:8] + '..'
                                                ui.label(category_label).classes(f'text-[7px] text-center leading-none').style(f'color: {text_c}; font-weight: bold;')
                                        else:
                                            # Cadeira Livre
                                            if state.edit_mode == "layout":
                                                # No modo layout, clica para bloquear (virar corredor)
                                                with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105 border').style(
                                                    'width: 70px; height: 48px; border-radius: 4px; border-color: rgba(255,255,255,0.15) !important; background: #1b2535; gap: 0;'
                                                ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                                    ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono')
                                                    ui.label('BLOQUEAR').classes('text-[7px] text-grey-5 font-bold')
                                            else:
                                                # Modo alocação, clica para alocar
                                                with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                                    f'width: 70px; height: 48px; border-radius: 4px; border-color: {THEME["success"]}40 !important; background: rgba(0, 230, 118, 0.05); gap: 0;'
                                                ).on('click', lambda s=seat_id: open_allocate_seat_dialog(s, convidados, current_event['id'])):
                                                    ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                                    ui.label('LIVRE').classes('text-[9px] font-bold text-center leading-none').style(f'color: {THEME["success"]};')
                                                    ui.label('(vazio)').classes('text-[7px] text-grey-5 text-center leading-none')

                        # Referência Inferior (Entrada, etc.)
                        ref_bottom = layout.get('ref_bottom', 'ENTRADA / FACHADA')
                        if ref_bottom:
                            with ui.row().classes('w-full justify-center q-mt-sm q-mb-md'):
                                ui.label(f"▼ {ref_bottom.upper()} ▼").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

                    # Controles de Dimensão do Layout na Base
                    ui.separator().classes('q-my-md').style('border-color: rgba(255,255,255,0.05);')
                    
                    with ui.row().classes('w-full justify-between items-center wrap-mobile gap-2'):
                        with ui.row().classes('items-center gap-1'):
                            ui.label('Fileiras:').classes('text-xs text-grey-4')
                            ui.button(icon='remove', on_click=lambda: update_grid_size(current_event, layout, -1, 0)).props('unelevated color=grey-8 dense round flat')
                            ui.button(icon='add', on_click=lambda: update_grid_size(current_event, layout, 1, 0)).props('unelevated color=grey-8 dense round flat')
                            
                            ui.label('Colunas:').classes('text-xs text-grey-4 q-ml-md')
                            ui.button(icon='remove', on_click=lambda: update_grid_size(current_event, layout, 0, -1)).props('unelevated color=grey-8 dense round flat')
                            ui.button(icon='add', on_click=lambda: update_grid_size(current_event, layout, 0, 1)).props('unelevated color=grey-8 dense round flat')
                        
                        ui.button(
                            'Exportar Planilha de Assentos', 
                            icon='table_chart', 
                            on_click=lambda: export_map(current_event['id'], current_event['nome'], rows_count, cols_count, blocked_seats, convidados)
                        ).props('unelevated color=cyan dense').classes('text-xs')

    # --- FUNÇÕES AUXILIARES DE ESTADO ---
    
    def select_event(event_id):
        state.selected_event_id = event_id
        render_content.refresh()
        
    def toggle_mode(mode):
        state.edit_mode = mode
        render_content.refresh()
        
    def update_search(val):
        state.search_query = val or ""
        render_content.refresh()
        
    def update_filter_category(val):
        state.filter_category = val
        render_content.refresh()
        
    def update_filter_unallocated(val):
        state.filter_only_unallocated = val
        render_content.refresh()

    # --- COMANDOS E TRANSAÇÕES NO BANCO DE DADOS ---

    def create_event(nome, data, local, layout_tipo, rows, cols, ref_top="PALCO PRINCIPAL", ref_bottom="ENTRADA / FACHADA"):
        if not nome or not data:
            ui.notify('Nome e Data do Evento são obrigatórios.', color='warning')
            return
            
        db = get_db_connection()
        if db:
            try:
                layout_json = json.dumps({
                    'rows': int(rows),
                    'cols': int(cols),
                    'blocked_seats': [],
                    'ref_top': ref_top or 'PALCO PRINCIPAL',
                    'ref_bottom': ref_bottom or 'ENTRADA / FACHADA'
                })
                registro = {
                    'nome': nome.upper(),
                    'data_evento': data,
                    'local': local or '',
                    'tipo_layout': layout_tipo,
                    'layout_json': layout_json,
                    'status': 'ativo',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                res = db.table('jade_eventos').insert(registro).execute()
                ui.notify('Evento criado com sucesso!', color='success')
                
                # Salva log
                db.table('jade_log').insert({
                    'evento_id': res.data[0]['id'] if res.data else None,
                    'acao': 'criar_evento',
                    'detalhes': f"Evento {nome.upper()} criado por {user_name}",
                    'usuario': user_name,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }).execute()
                
                if res.data:
                    state.selected_event_id = res.data[0]['id']
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao criar evento: {e}", color='red')

    def delete_event(event):
        db = get_db_connection()
        if db:
            try:
                # 1. Remove convidados do evento
                db.table('jade_convidados').delete().eq('evento_id', event['id']).execute()
                # 2. Remove logs
                db.table('jade_log').delete().eq('evento_id', event['id']).execute()
                # 3. Remove evento
                db.table('jade_eventos').delete().eq('id', event['id']).execute()
                
                ui.notify('Evento e todos os dados vinculados foram excluídos.', color='success')
                state.selected_event_id = None
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao excluir evento: {e}", color='red')

    def save_guest(guest_id, data, event_id):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                if guest_id:
                    # Update
                    db.table('jade_convidados').update(data).eq('id', guest_id).execute()
                    ui.notify('Dados do convidado atualizados.', color='success')
                    sync_companions(guest_id, data['nome'], data['max_acompanhantes'], event_id, data['categoria'])
                else:
                    # Insert
                    data['evento_id'] = event_id
                    res = db.table('jade_convidados').insert(data).execute()
                    ui.notify('Convidado adicionado à lista.', color='success')
                    if res.data:
                        new_id = res.data[0]['id']
                        sync_companions(new_id, data['nome'], data['max_acompanhantes'], event_id, data['categoria'])
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao salvar convidado: {e}", color='red')

    def delete_guest(guest):
        db = get_db_connection()
        if db:
            try:
                # Remove acompanhantes primeiro
                db.table('jade_convidados').delete().eq('convidado_principal_id', guest['id']).execute()
                # Remove convidado
                db.table('jade_convidados').delete().eq('id', guest['id']).execute()
                ui.notify(f"Convidado {guest['nome']} e acompanhantes removidos.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao excluir convidado: {e}", color='red')

    def allocate_guest(guest_id, seat_id, event_id):
        db = get_db_connection()
        if db:
            try:
                # 1. Garante que ninguém mais está no mesmo assento
                db.table('jade_convidados').update({'assento_id': None}).eq('evento_id', event_id).eq('assento_id', seat_id).execute()
                
                # 2. Aloca o convidado selecionado
                db.table('jade_convidados').update({'assento_id': seat_id}).eq('id', guest_id).execute()
                
                # 3. Log
                db.table('jade_log').insert({
                    'evento_id': event_id,
                    'acao': 'alocar_assento',
                    'detalhes': f"Convidado ID {guest_id} alocado ao assento {seat_id}",
                    'usuario': user_name,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }).execute()
                
                ui.notify(f"Assento {seat_id} ocupado com sucesso.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao alocar assento: {e}", color='red')

    def remove_guest_allocation(guest):
        db = get_db_connection()
        if db:
            try:
                db.table('jade_convidados').update({'assento_id': None}).eq('id', guest['id']).execute()
                ui.notify(f"Convidado {guest['nome']} removido do assento {guest['assento_id']}.", color='success')
                
                # Log
                db.table('jade_log').insert({
                    'evento_id': guest['evento_id'],
                    'acao': 'desalocar_assento',
                    'detalhes': f"Convidado {guest['nome']} removido do assento {guest['assento_id']}",
                    'usuario': user_name,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }).execute()
                
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao remover alocação: {e}", color='red')

    def swap_guests(guest_a, guest_b_id, event_id):
        db = get_db_connection()
        if db:
            try:
                seat_a = guest_a.get('assento_id')
                
                # Resgata o outro convidado
                res_b = db.table('jade_convidados').select('*').eq('id', guest_b_id).execute()
                if not res_b.data:
                    return
                guest_b = res_b.data[0]
                seat_b = guest_b.get('assento_id')
                
                # Troca os assentos
                db.table('jade_convidados').update({'assento_id': seat_b}).eq('id', guest_a['id']).execute()
                db.table('jade_convidados').update({'assento_id': seat_a}).eq('id', guest_b['id']).execute()
                
                # Log
                db.table('jade_log').insert({
                    'evento_id': event_id,
                    'acao': 'swap_assentos',
                    'detalhes': f"Troca de assentos: {guest_a['nome']} ({seat_a} -> {seat_b}) e {guest_b['nome']} ({seat_b} -> {seat_a})",
                    'usuario': user_name,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }).execute()
                
                ui.notify("Troca de assentos efetuada.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao realizar troca: {e}", color='red')

    def toggle_seat_block(seat_id, event, layout):
        db = get_db_connection()
        if db:
            blocked = layout.get('blocked_seats', [])
            if seat_id in blocked:
                blocked.remove(seat_id)
            else:
                blocked.append(seat_id)
                
            layout['blocked_seats'] = blocked
            new_layout_json = json.dumps(layout)
            
            try:
                # 1. Garante que qualquer convidado alocado nesse assento agora bloqueado seja desalocado
                db.table('jade_convidados').update({'assento_id': None}).eq('evento_id', event['id']).eq('assento_id', seat_id).execute()
                
                # 2. Atualiza o layout do evento
                db.table('jade_eventos').update({'layout_json': new_layout_json}).eq('id', event['id']).execute()
                
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao atualizar layout: {e}", color='red')

    def update_grid_size(event, layout, row_delta, col_delta):
        db = get_db_connection()
        if db:
            r = max(1, min(20, layout.get('rows', 5) + row_delta))
            c = max(1, min(25, layout.get('cols', 8) + col_delta))
            
            layout['rows'] = r
            layout['cols'] = c
            
            new_layout_json = json.dumps(layout)
            try:
                db.table('jade_eventos').update({'layout_json': new_layout_json}).eq('id', event['id']).execute()
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao alterar dimensões do grid: {e}", color='red')

    # --- COMPONENTES DE INTERFACE DE DIÁLOGOS (MODAIS) ---

    def open_create_event_dialog():
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 380px;'):
            ui.label('📅 Novo Evento de Assento').classes('text-md font-bold text-cyan q-mb-md')
            
            nome = ui.input('Nome do Evento / Solenidade').props('dark outlined dense w-full')
            data = ui.input('Data do Evento').props('type=date dark outlined dense w-full')
            local = ui.input('Local (ex: Auditório)').props('dark outlined dense w-full')
            
            ref_top = ui.input('Referência Superior (ex: Palco)', value='PALCO PRINCIPAL').props('dark outlined dense w-full')
            ref_bottom = ui.input('Referência Inferior (ex: Entrada)', value='ENTRADA / FACHADA').props('dark outlined dense w-full')
            
            with ui.row().classes('w-full gap-2'):
                rows = ui.number('Linhas (Grid)', value=5, min=1, max=20, step=1).props('dark outlined dense').classes('col')
                cols = ui.number('Colunas (Grid)', value=8, min=1, max=25, step=1).props('dark outlined dense').classes('col')
                
            layout_tipo = ui.select(
                options={'auditorio': 'Auditório (Fileiras)', 'mesas': 'Mesas Redondas'}, 
                value='auditorio'
            ).props('dark outlined dense w-full')
            
            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 text-color=white dense')
                ui.button(
                    'Criar', 
                    on_click=lambda: [create_event(nome.value, data.value, local.value, layout_tipo.value, rows.value, cols.value, ref_top.value, ref_bottom.value), diag.close()]
                ).props('unelevated color=primary text-color=black dense')
                
        diag.open()

    def open_edit_event_dialog(event, layout):
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 380px;'):
            ui.label('📝 Editar Detalhes do Evento').classes('text-md font-bold text-cyan q-mb-md')
            
            nome = ui.input('Nome do Evento / Solenidade', value=event['nome']).props('dark outlined dense w-full')
            data = ui.input('Data do Evento', value=event['data_evento']).props('type=date dark outlined dense w-full')
            local = ui.input('Local', value=event.get('local') or '').props('dark outlined dense w-full')
            
            ref_top = ui.input('Referência Superior (ex: Palco)', value=layout.get('ref_top', 'PALCO PRINCIPAL')).props('dark outlined dense w-full')
            ref_bottom = ui.input('Referência Inferior (ex: Entrada)', value=layout.get('ref_bottom', 'ENTRADA / FACHADA')).props('dark outlined dense w-full')
            
            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
                def salvar_alteracoes():
                    db = get_db_connection()
                    if db:
                        layout['ref_top'] = ref_top.value
                        layout['ref_bottom'] = ref_bottom.value
                        try:
                            db.table('jade_eventos').update({
                                'nome': nome.value.upper(),
                                'data_evento': data.value,
                                'local': local.value or '',
                                'layout_json': json.dumps(layout)
                            }).eq('id', event['id']).execute()
                            
                            ui.notify('Evento atualizado com sucesso!', color='success')
                            render_content.refresh()
                            diag.close()
                        except Exception as e:
                            ui.notify(f"Erro ao salvar: {e}", color='red')
                            
                ui.button('Salvar', on_click=salvar_alteracoes).props('unelevated color=primary text-color=black dense')
                
        diag.open()

    def confirm_delete_event(event):
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 320px;'):
            ui.label('⚠️ Excluir Evento?').classes('text-md font-bold text-red q-mb-sm')
            ui.label(f'Tem certeza que deseja excluir o evento "{event["nome"]}"? Esta ação removerá definitivamente toda a lista de convidados e logs associados.').classes('text-xs text-grey-4 q-mb-md')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                ui.button(
                    'Confirmar Exclusão', 
                    on_click=lambda: [delete_event(event), diag.close()]
                ).props('unelevated color=danger dense')
        diag.open()

    def open_edit_guest_dialog(guest=None, event_id=None):
        title_text = '➕ Adicionar Convidado' if not guest else '📝 Editar Convidado'
        
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 360px;'):
            ui.label(title_text).classes('text-md font-bold text-cyan q-mb-md')
            
            nome = ui.input('Nome do Convidado', value=guest['nome'] if guest else '').props('dark outlined dense w-full')
            posto = ui.input('Posto / Graduação (ex: CT, CF, Ten)', value=guest.get('posto_graduacao') or '' if guest else '').props('dark outlined dense w-full')
            cargo = ui.input('Cargo / Função (ex: Secretário)', value=guest.get('cargo_funcao') or '' if guest else '').props('dark outlined dense w-full')
            
            cat_list = ['VIP', 'Autoridade Civil', 'Autoridade Militar', 'Imprensa', 'Apoio', 'Geral']
            categoria = ui.select(
                options=cat_list, 
                value=guest.get('categoria', 'Geral') if guest else 'Geral'
            ).props('dark outlined dense w-full')
            
            acomps = ui.number('Acompanhantes', value=guest.get('max_acompanhantes', 0) if guest else 0, min=0, step=1).props('dark outlined dense w-full')
            
            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
                def salvar():
                    reg = {
                        'nome': nome.value.upper(),
                        'posto_graduacao': posto.value or None,
                        'cargo_funcao': cargo.value or None,
                        'categoria': categoria.value,
                        'max_acompanhantes': int(acomps.value)
                    }
                    save_guest(guest['id'] if guest else None, reg, event_id)
                    diag.close()
                    
                ui.button('Salvar', on_click=salvar).props('unelevated color=primary text-color=black dense')
        diag.open()

    def confirm_delete_guest(guest):
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 320px;'):
            ui.label('⚠️ Remover Convidado?').classes('text-md font-bold text-red q-mb-sm')
            ui.label(f'Tem certeza que deseja remover "{guest["nome"]}" da lista?').classes('text-xs text-grey-4 q-mb-md')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                ui.button(
                    'Remover', 
                    on_click=lambda: [delete_guest(guest), diag.close()]
                ).props('unelevated color=danger dense')
        diag.open()

    def open_allocate_seat_dialog(seat_id, convidados, event_id):
        def get_category_priority(cat):
            cat_upper = str(cat or '').upper()
            if 'VIP' in cat_upper:
                return 0
            if 'MILITAR' in cat_upper:
                return 1
            if 'CIVIL' in cat_upper:
                return 2
            if 'IMPRENSA' in cat_upper:
                return 3
            if 'APOIO' in cat_upper:
                return 4
            return 5

        # Ordena todos os convidados por prioridade de grupo, posto e nome
        sorted_convidados = sorted(
            convidados,
            key=lambda c: (get_category_priority(c.get('categoria', 'Geral')), c.get('posto_graduacao') or '', c['nome'])
        )
        
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 420px; max-height: 550px;'):
            ui.label(f'Alocar Assento {seat_id}').classes('text-md font-bold text-cyan q-mb-xs')
            ui.label('Selecione um convidado na lista para alocar imediatamente:').classes('text-xs text-grey-4 q-mb-md')
            
            # Campo de busca tático
            search_input = ui.input(placeholder='Filtrar por nome ou cargo...').props('dark outlined dense clearable w-full q-mb-md')
            
            # Container da lista reativa
            @ui.refreshable
            def render_dialog_guests():
                query = search_input.value.lower() if search_input.value else ""
                filtered = sorted_convidados
                if query:
                    filtered = [
                        c for c in sorted_convidados
                        if query in c['nome'].lower() or
                        (c.get('cargo_funcao') and query in c['cargo_funcao'].lower()) or
                        (c.get('posto_graduacao') and query in c['posto_graduacao'].lower())
                    ]
                
                with ui.column().classes('w-full gap-2 scroll-container q-py-xs').style('overflow-y: auto; max-height: 320px;'):
                    if filtered:
                        for c in filtered:
                            is_seated = bool(c.get('assento_id'))
                            card_bg = 'rgba(0, 229, 255, 0.08)' if is_seated else 'rgba(255, 255, 255, 0.02)'
                            card_border = 'rgba(0, 229, 255, 0.25)' if is_seated else 'rgba(255, 255, 255, 0.06)'
                            text_style = 'opacity-70' if is_seated else ''
                            
                            # Clicar no convidado faz a alocação e fecha o modal
                            with ui.card().classes('w-full q-pa-xs px-2 no-shadow rounded-lg cursor-pointer transition-all hover:bg-cyan-500/20').style(
                                f'background: {card_bg}; border: 1px solid {card_border}; gap: 0;'
                            ).on('click', lambda c_id=c['id']: [allocate_guest(c_id, seat_id, event_id), diag.close()]):
                                with ui.row().classes('w-full justify-between items-center no-wrap'):
                                    with ui.column().classes('gap-0'):
                                        nome_exibicao = f"{c.get('posto_graduacao') or ''} {c['nome']}".strip()
                                        ui.label(nome_exibicao).classes(f'text-xs font-bold text-white {text_style}')
                                        
                                        sub = c.get('cargo_funcao') or 'Sem cargo/função'
                                        ui.label(f"[{c.get('categoria', 'Geral').upper()}] {sub}").classes('text-[9px] text-grey-4')
                                    
                                    if is_seated:
                                        ui.badge(f"Assento {c['assento_id']}").props('color=cyan text-color=black').classes('text-[8px]')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-md text-grey'):
                            ui.label('Nenhum convidado disponível').classes('text-xs')
                            
            search_input.on('value-change', render_dialog_guests.refresh)
            
            render_dialog_guests()
            
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
        diag.open()

    def open_seat_actions_dialog(seat_id, guest, convidados, event_id):
        # 1. Carrega dados do layout para identificar assentos livres
        rows_count = 5
        cols_count = 8
        blocked_seats = []
        db = get_db_connection()
        if db:
            try:
                res_ev = db.table('jade_eventos').select('layout_json').eq('id', event_id).execute()
                if res_ev.data:
                    layout = json.loads(res_ev.data[0]['layout_json'])
                    rows_count = layout.get('rows', 5)
                    cols_count = layout.get('cols', 8)
                    blocked_seats = layout.get('blocked_seats', [])
            except Exception as ex:
                print(f"[FETCH LAYOUT FOR ACTIONS ERR] {ex}")

        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 400px; max-height: 600px;'):
            ui.label(f'Ações do Assento {seat_id}').classes('text-md font-bold text-cyan q-mb-xs')
            
            # Detalhes do ocupante
            nome_completo = f"{guest.get('posto_graduacao') or ''} {guest['nome']}".strip()
            ui.label(nome_completo).classes('text-sm font-bold text-white')
            ui.label(guest.get('cargo_funcao') or guest.get('categoria') or 'Convidado').classes('text-xs text-grey-4 q-mb-md')
            
            # 1. Desalocar
            ui.button(
                'Liberar / Desalocar Assento', 
                icon='block', 
                on_click=lambda: [remove_guest_allocation(guest), diag.close()]
            ).props('unelevated color=danger w-full q-mb-sm dense')
            
            # 2. Trocar (Swap) com outra pessoa alocada
            other_allocated = [c for c in convidados if c.get('assento_id') and c['id'] != guest['id']]
            if other_allocated:
                ui.separator().classes('q-my-sm')
                ui.label('Permutar (Swap) com outro assento ocupado:').classes('text-[11px] text-grey q-mb-xs')
                
                swap_options = {
                    c['id']: f"{c['assento_id']} - {c.get('posto_graduacao') or ''} {c['nome']}".strip()
                    for c in other_allocated
                }
                swap_target = ui.select(swap_options).props('dark outlined dense w-full')
                
                ui.button(
                    'Confirmar Troca de Assentos', 
                    on_click=lambda: [swap_guests(guest, swap_target.value, event_id), diag.close()]
                ).props('unelevated color=primary text-color=black w-full q-mt-sm dense')
            
            # 3. Acompanhantes vinculados
            companions = [c for c in convidados if c.get('convidado_principal_id') == guest['id']]
            if companions:
                ui.separator().classes('q-my-sm')
                ui.label('Acompanhantes Vinculados:').classes('text-[11px] font-bold text-cyan q-mb-xs')
                
                # Lista de assentos livres
                free_seats = sorted(list(set(
                    f"{get_row_label(r)}-{col}" 
                    for r in range(rows_count) 
                    for col in range(1, cols_count + 1)
                ) - set(c['assento_id'] for c in convidados if c.get('assento_id')) - set(blocked_seats)))
                
                # Ordenação por proximidade
                try:
                    main_row_label, main_col_str = seat_id.split('-')
                    main_row_idx = 0
                    for r in range(rows_count):
                        if get_row_label(r) == main_row_label:
                            main_row_idx = r
                            break
                    main_col_idx = int(main_col_str)
                    
                    def get_seat_distance(s_id):
                        try:
                            r_lbl, c_str = s_id.split('-')
                            r_idx = 0
                            for r in range(rows_count):
                                if get_row_label(r) == r_lbl:
                                    r_idx = r
                                    break
                            c_idx = int(c_str)
                            return abs(main_row_idx - r_idx) + abs(main_col_idx - c_idx)
                        except:
                            return 999
                    
                    sorted_free_seats = sorted(free_seats, key=get_seat_distance)
                except:
                    sorted_free_seats = free_seats

                with ui.column().classes('w-full gap-2 q-mt-xs'):
                    for comp in companions:
                        comp_seat = comp.get('assento_id')
                        with ui.row().classes('w-full items-center justify-between no-wrap gap-2').style('background: rgba(255,255,255,0.02); padding: 4px; border-radius: 4px;'):
                            ui.label(comp['nome']).classes('text-xs text-white col-grow truncate')
                            
                            if comp_seat:
                                ui.badge(f"Assento {comp_seat}").props('color=cyan text-color=black').classes('text-[9px]')
                                ui.button(
                                    icon='cancel',
                                    on_click=lambda c=comp: [remove_guest_allocation(c), diag.close()]
                                ).props('flat round dense color=danger').classes('text-xs')
                            else:
                                if sorted_free_seats:
                                    seat_select = ui.select(options=sorted_free_seats, label='Assento').props('dark outlined dense').style('width: 100px; font-size: 10px;')
                                    ui.button(
                                        icon='check',
                                        on_click=lambda c=comp, sel=seat_select: [
                                            allocate_guest(c['id'], sel.value, event_id) if sel.value else None,
                                            diag.close()
                                        ]
                                    ).props('unelevated color=success text-color=black dense').classes('q-px-xs')
                                else:
                                    ui.label('Sem vagas').classes('text-[9px] text-grey-5')
            
            ui.separator().classes('q-my-sm')
            ui.button('Fechar', on_click=diag.close).props('unelevated color=grey-8 w-full dense')
            
        diag.open()

    # --- IMPLEMENTAÇÃO DE PARSER DE IMPORTAÇÃO (PANDAS/EXCEL) ---

    def download_template():
        # Cria dataframe modelo
        df = pd.DataFrame(columns=['Nome', 'Posto_Graduacao', 'Cargo_Funcao', 'Categoria', 'Acompanhantes'])
        # Adiciona um registro de exemplo
        df.loc[0] = ['Exemplo de Silva', 'Capitão-Tenente', 'Chefe de Relações Públicas', 'VIP', 0]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Convidados')
            
        xlsx_data = output.getvalue()
        ui.download(xlsx_data, 'modelo_importacao_jade.xlsx')

    def handle_import_list(e, event_id):
        # Lê arquivo importado pelo NiceGUI
        content = e.content.read()
        try:
            if e.name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
                
            # Verifica colunas necessárias
            required_cols = ['Nome']
            for col in required_cols:
                if col not in df.columns:
                    ui.notify(f"Coluna obrigatória '{col}' não encontrada na planilha.", color='red')
                    return
                    
            db = get_db_connection()
            if not db:
                return
                
            inserted_count = 0
            for _, row in df.iterrows():
                if pd.isna(row['Nome']):
                    continue
                    
                nome = str(row['Nome']).strip().upper()
                posto = str(row['Posto_Graduacao']).strip() if 'Posto_Graduacao' in df.columns and not pd.isna(row['Posto_Graduacao']) else None
                cargo = str(row['Cargo_Funcao']).strip() if 'Cargo_Funcao' in df.columns and not pd.isna(row['Cargo_Funcao']) else None
                categoria = str(row['Categoria']).strip() if 'Categoria' in df.columns and not pd.isna(row['Categoria']) else 'Geral'
                
                acomps = 0
                if 'Acompanhantes' in df.columns and not pd.isna(row['Acompanhantes']):
                    try:
                        acomps = int(row['Acompanhantes'])
                    except:
                        pass
                        
                registro = {
                    'evento_id': event_id,
                    'nome': nome,
                    'posto_graduacao': posto,
                    'cargo_funcao': cargo,
                    'categoria': categoria,
                    'max_acompanhantes': acomps
                }
                
                # Evitar duplicados no mesmo evento
                existing = db.table('jade_convidados').select('id').eq('evento_id', event_id).eq('nome', nome).execute()
                if not existing.data:
                    res = db.table('jade_convidados').insert(registro).execute()
                    inserted_count += 1
                    if res.data:
                        new_id = res.data[0]['id']
                        sync_companions(new_id, nome, acomps, event_id, categoria)
                    
            ui.notify(f"Importação concluída. {inserted_count} novos convidados adicionados.", color='success')
            
            # Log
            db.table('jade_log').insert({
                'evento_id': event_id,
                'acao': 'importacao_convidados',
                'detalhes': f"Importação de {inserted_count} convidados via planilha",
                'usuario': user_name,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }).execute()
            
            render_content.refresh()
        except Exception as ex:
            ui.notify(f"Erro ao processar planilha: {ex}", color='red')

    def export_map(event_id, event_name, rows, cols, blocked_seats, guests):
        # Gera matriz para planilha excel
        grid_data = []
        
        # Mapeamento assento -> nome
        seat_map = {}
        for g in guests:
            if g.get('assento_id'):
                seat_map[g['assento_id']] = f"{g.get('posto_graduacao') or ''} {g['nome']}".strip()
                
        for r in range(rows):
            row_label = get_row_label(r)
            row_cells = []
            for c in range(1, cols + 1):
                seat_id = f"{row_label}-{c}"
                if seat_id in blocked_seats:
                    row_cells.append("[Corredor]")
                elif seat_id in seat_map:
                    row_cells.append(seat_map[seat_id])
                else:
                    row_cells.append("Livre")
            grid_data.append(row_cells)
            
        df = pd.DataFrame(
            grid_data, 
            index=[get_row_label(r) for r in range(rows)], 
            columns=[str(c) for c in range(1, cols + 1)]
        )
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Mapa de Assentos')
            
        xlsx_data = output.getvalue()
        file_name = f"mapa_assentos_{event_name.lower().replace(' ', '_')}.xlsx"
        ui.download(xlsx_data, file_name)

    # Renderiza o layout inicial
    render_content()
