import io
import json
from datetime import datetime
import pandas as pd
from nicegui import ui, app
import theme
from database import get_db_connection, get_service_db_connection

THEME = theme.colors

# Estado local do módulo
class ModuleState:
    def __init__(self):
        self.selected_event_id = None
        self.edit_mode = "alocacao"  # "alocacao" ou "layout"
        self.search_query = ""
        self.filter_category = "Todos"
        self.filter_only_unallocated = False

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
            
        # 3. Se temos demais (deleta excedentes dando prioridade aos NÃO ALOCADOS)
        elif existing_count > max_acomp:
            needed_delete = existing_count - max_acomp
            # Separa acompanhantes sem assento e com assento
            unallocated = [d for d in existing if not d.get('assento_id')]
            allocated = [d for d in existing if d.get('assento_id')]
            
            # Ordena não alocados decrescente por ID e alocados decrescente por ID
            unallocated_sorted = sorted(unallocated, key=lambda x: x['id'], reverse=True)
            allocated_sorted = sorted(allocated, key=lambda x: x['id'], reverse=True)
            
            # Prioriza deletar os não alocados primeiro
            candidates = unallocated_sorted + allocated_sorted
            to_delete = candidates[:needed_delete]
            delete_ids = [d['id'] for d in to_delete]
            
            if delete_ids:
                # 3.1 Garante que se algum alocado for deletado, a cadeira é liberada no mapa
                for d in to_delete:
                    if d.get('assento_id'):
                        try:
                            db.table('jade_convidados').update({'assento_id': None}).eq('id', d['id']).execute()
                        except Exception:
                            pass
                # 3.2 Deleta os registros excedentes
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
    
    @ui.refreshable
    def render_content():
        db = get_service_db_connection() or get_db_connection()
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

        if not state.selected_event_id and eventos:
            state.selected_event_id = eventos[0]['id']

        current_event = next((e for e in eventos if e['id'] == state.selected_event_id), None)

        # --- CABEÇALHO DE CONTROLE DE EVENTOS ---
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

                with ui.row().classes('items-center gap-2 wrap'):
                    ui.button('Novo Evento', icon='add', on_click=open_create_event_dialog).props('unelevated color=primary text-color=black dense').classes('q-px-sm')
                    
                    if current_event:
                        ui.button('🖨️ Imprimir Placas por Fileira', icon='print', on_click=lambda: open_print_cards_dialog(current_event, convidados, layout)).props('unelevated color=cyan text-color=black dense bold').classes('q-px-sm')
                        ui.button('🔍 Scanner & Conferência', icon='qr_code_scanner', on_click=lambda: open_tactical_scanner_dialog(current_event, convidados)).props('unelevated color=amber text-color=black dense bold').classes('q-px-sm')
                        
                        ui.button('Editar Evento', icon='edit', on_click=lambda: open_edit_event_dialog(current_event, layout)).props('unelevated color=accent dense outline').classes('q-px-sm')
                        ui.button('Excluir Evento', icon='delete', on_click=lambda: confirm_delete_event(current_event)).props('unelevated color=danger dense outline').classes('q-px-sm')

        if not current_event:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-4'):
                ui.icon('event_seat', size='5rem', color='cyan')
                ui.label('Por favor, crie um evento para iniciar o mapeamento de assentos.').classes('text-md text-white font-bold')
                ui.button('Criar Primeiro Evento', icon='add', on_click=open_create_event_dialog).props('unelevated color=primary text-color=black')
            return

        # Carregar convidados do evento ativo
        convidados = []
        try:
            res_conv = db.table('jade_convidados').select('*').eq('evento_id', current_event['id']).order('id', desc=False).execute()
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

        categories = sorted(list(set(c['categoria'] for c in convidados if c.get('categoria'))))
        category_options = ["Todos"] + categories

        allocated_map = {c['assento_id']: c for c in convidados if c.get('assento_id')}

        # =========================================================================
        # SEÇÃO 1 (TOPO): MAPA DE ASSENTOS / GRID
        # =========================================================================
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.row().classes('w-full items-center justify-between q-mb-sm wrap-mobile gap-2'):
                with ui.column().classes('gap-0'):
                    ui.label('🗺️ MAPA DE ASSENTOS DA SOLENIDADE').classes('text-md font-bold text-cyan cyber-title')
                    ui.label(f"Grid: {rows_count} fileiras × {cols_count} colunas • {len(allocated_map)} de {rows_count * cols_count - len(blocked_seats)} lugares ocupados").classes('text-[11px] text-grey-4')
                
                # Seletor de Modo de Edição
                with ui.row().classes('items-center bg-black/30 rounded-lg q-pa-xs border border-white/10'):
                    ui.button(
                        'Alocação Rápida', 
                        icon='event_seat', 
                        on_click=lambda: toggle_mode("alocacao")
                    ).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "alocacao" else "flat text-color=grey"}').classes('text-xs q-px-sm')
                    
                    ui.button(
                        'Editor de Layout / Corredores', 
                        icon='edit_road', 
                        on_click=lambda: toggle_mode("layout")
                    ).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "layout" else "flat text-color=grey"}').classes('text-xs q-px-sm')

            # Parse dos setores / blocos de assentos
            sectors = layout.get('sectors', [
                {'name': 'SETOR ALPHA (ESQUERDA)', 'start_col': 1, 'end_col': max(1, cols_count // 3)},
                {'name': 'SETOR NOBRE (CENTRO)', 'start_col': max(1, cols_count // 3) + 1, 'end_col': max(1, (cols_count * 2) // 3)},
                {'name': 'SETOR BRAVO (DIREITA)', 'start_col': max(1, (cols_count * 2) // 3) + 1, 'end_col': cols_count}
            ]) if cols_count >= 6 else []

            # Renderizador de Grid de Assentos por Setores
            with ui.column().classes('w-full items-center justify-start q-py-md scroll-container').style('overflow-x: auto;'):
                ref_top = layout.get('ref_top', 'PALCO PRINCIPAL')
                if ref_top:
                    with ui.row().classes('w-full justify-center q-mb-sm'):
                        ui.label(f"▲ {ref_top.upper()} ▲").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

                # BARRA DE TÍTULOS DE SETORES (SE HOUVER SUBDIVISÃO DE SETORES)
                if sectors:
                    with ui.row().classes('w-full justify-between items-center q-mb-xs gap-2 px-8').style('min-width: 650px;'):
                        for sec in sectors:
                            sec_cols = sec['end_col'] - sec['start_col'] + 1
                            if sec_cols > 0:
                                with ui.card().classes('q-pa-xs no-shadow rounded-lg text-center bg-cyan-950/40 border border-cyan-500/30 col'):
                                    ui.label(sec['name']).classes('text-[10px] font-black text-cyan tracking-wider truncate')

                with ui.grid(columns=cols_count + 1).classes('gap-2 items-center').style('min-width: 600px;'):
                    ui.label('').classes('text-center font-bold text-grey-5').style('width: 40px;')
                    
                    for col in range(1, cols_count + 1):
                        ui.label(str(col)).classes('text-center font-bold text-grey-5').style('width: 70px; font-size: 11px;')
                        
                    for r in range(rows_count):
                        row_label = get_row_label(r)
                        ui.label(row_label).classes('text-center font-bold text-grey-5 text-md').style('width: 40px;')
                        
                        for col in range(1, cols_count + 1):
                            seat_id = f"{row_label}-{col}"
                            is_blocked = seat_id in blocked_seats
                            guest = allocated_map.get(seat_id)
                            
                            if is_blocked:
                                if state.edit_mode == "layout":
                                    with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105').style(
                                        'width: 70px; height: 48px; border: 1px dashed rgba(255,255,255,0.15); border-radius: 4px; background: rgba(255,255,255,0.02); gap: 0;'
                                    ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                        ui.label(seat_id).classes('text-[8px] text-grey-5 font-mono')
                                        ui.label('CORREDOR').classes('text-[7px] text-grey-6 font-bold')
                                else:
                                    ui.label('').style('width: 70px; height: 48px;')
                            else:
                                if guest:
                                    display_name = f"{guest.get('posto_graduacao') or ''} {guest['nome']}".strip()
                                    if len(display_name) > 12:
                                        display_name = display_name[:10] + '..'
                                        
                                    is_vip = guest.get('categoria') == 'VIP'
                                    is_acomp = bool(guest.get('convidado_principal_id'))
                                    
                                    border_c = THEME['primary'] if is_vip else ('#ffb74d' if is_acomp else THEME['accent'])
                                    bg_c = 'rgba(0, 229, 255, 0.15)' if is_vip else ('rgba(255, 183, 77, 0.12)' if is_acomp else 'rgba(0, 162, 255, 0.15)')
                                    text_c = THEME['primary'] if is_vip else ('#ffb74d' if is_acomp else THEME['accent'])
                                    
                                    with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                        f'width: 70px; height: 48px; border-radius: 4px; border-color: {border_c} !important; background: {bg_c}; gap: 0;'
                                    ).on('click', lambda s=seat_id, g=guest: open_seat_actions_dialog(s, g, convidados, current_event['id'])):
                                        ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                        ui.label(display_name).classes('text-[9px] font-bold text-center leading-none text-white overflow-hidden w-full')
                                        
                                        category_label = 'ACOMP' if is_acomp else str(guest.get('categoria', 'Geral')).upper()
                                        if len(category_label) > 10:
                                            category_label = category_label[:8] + '..'
                                        ui.label(category_label).classes(f'text-[7px] text-center leading-none').style(f'color: {text_c}; font-weight: bold;')
                                else:
                                    if state.edit_mode == "layout":
                                        with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105 border').style(
                                            'width: 70px; height: 48px; border-radius: 4px; border-color: rgba(255,255,255,0.15) !important; background: #1b2535; gap: 0;'
                                        ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                            ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono')
                                            ui.label('BLOQUEAR').classes('text-[7px] text-grey-5 font-bold')
                                    else:
                                        with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                            f'width: 70px; height: 48px; border-radius: 4px; border-color: {THEME["success"]}40 !important; background: rgba(0, 230, 118, 0.05); gap: 0;'
                                        ).on('click', lambda s=seat_id: open_allocate_seat_dialog(s, convidados, current_event['id'])):
                                            ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                            ui.label('LIVRE').classes('text-[9px] font-bold text-center leading-none').style(f'color: {THEME["success"]};')
                                            ui.label('(vazio)').classes('text-[7px] text-grey-5 text-center leading-none')

                ref_bottom = layout.get('ref_bottom', 'ENTRADA / FACHADA')
                if ref_bottom:
                    with ui.row().classes('w-full justify-center q-mt-sm q-mb-sm'):
                        ui.label(f"▼ {ref_bottom.upper()} ▼").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

            # Controles de Dimensão do Layout na Base
            with ui.row().classes('w-full justify-between items-center wrap-mobile gap-2 q-mt-xs'):
                with ui.row().classes('items-center gap-1'):
                    ui.label('Fileiras:').classes('text-xs text-grey-4')
                    ui.button(icon='remove', on_click=lambda: update_grid_size(current_event, layout, -1, 0)).props('unelevated color=grey-8 dense round flat')
                    ui.button(icon='add', on_click=lambda: update_grid_size(current_event, layout, 1, 0)).props('unelevated color=grey-8 dense round flat')
                    
                    ui.label('Colunas:').classes('text-xs text-grey-4 q-ml-sm')
                    ui.button(icon='remove', on_click=lambda: update_grid_size(current_event, layout, 0, -1)).props('unelevated color=grey-8 dense round flat')
                    ui.button(icon='add', on_click=lambda: update_grid_size(current_event, layout, 0, 1)).props('unelevated color=grey-8 dense round flat')
                    
                ui.label('Dica: Clique nos lugares vagos para alocar convidados.').classes('text-[11px] text-grey-5 italic')

        # =========================================================================
        # SEÇÃO 2 (ABAIXO DO GRID): LISTA DE CONVIDADOS HIERÁRQUICA E ACOMPANHANTES
        # =========================================================================
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.row().classes('w-full justify-between items-center wrap-mobile gap-2 q-mb-md'):
                ui.label('👥 PAINEL DE CONVIDADOS E ACOMPANHANTES').classes('text-md font-bold text-cyan cyber-title')
                
                with ui.row().classes('items-center gap-2'):
                    ui.button('Modelo Excel', icon='download', on_click=download_template).props('unelevated color=cyan dense outline').classes('text-xs')
                    
                    with ui.button('Importar Lista', icon='upload').props('unelevated color=primary text-color=black dense').classes('text-xs'):
                        ui.upload(
                            on_upload=lambda e: handle_import_list(e, current_event['id']),
                            multiple=False,
                            auto_upload=True
                        ).props('dark accept=.xlsx,.csv').classes('hidden')
                        
                    ui.button('➕ Adicionar Convidado Principal', icon='person_add', on_click=lambda: open_edit_guest_dialog(None, current_event['id'])).props('unelevated color=primary text-color=black dense').classes('text-xs')

            # Estado de colapsar tudo / expandir tudo se desejado
            if not hasattr(state, 'filter_seat_status'):
                state.filter_seat_status = "Todos"

            # Filtros de Convidados
            with ui.row().classes('w-full gap-2 items-center q-mb-md wrap-mobile'):
                ui.input(
                    placeholder='Buscar autoridade, convidado ou acompanhante...',
                    on_change=lambda e: update_search(e.value)
                ).props('dark outlined dense clearable').classes('col')
                
                ui.select(
                    options=category_options,
                    value=state.filter_category,
                    on_change=lambda e: update_filter_category(e.value),
                    label='Categoria'
                ).props('dark outlined dense').style('width: 140px;')
                
                ui.select(
                    options={'Todos': 'Status: Todos', 'pendentes': '⏳ Com Pendências', 'completos': '✅ Assentos Completos'},
                    value=getattr(state, 'filter_seat_status', 'Todos'),
                    on_change=lambda e: update_filter_seat_status(e.value)
                ).props('dark outlined dense').style('width: 170px;')

            # Filtra autoridades principais (sem convidado_principal_id)
            principais = [c for c in convidados if not c.get('convidado_principal_id')]
            
            # Filtro por busca de texto
            if state.search_query:
                q = state.search_query.lower()
                filtered_principais = []
                for p in principais:
                    acomp_p = [c for c in convidados if c.get('convidado_principal_id') == p['id']]
                    match_p = q in p['nome'].lower() or (p.get('cargo_funcao') and q in p['cargo_funcao'].lower()) or (p.get('posto_graduacao') and q in p['posto_graduacao'].lower())
                    match_ac = any(q in a['nome'].lower() for a in acomp_p)
                    if match_p or match_ac:
                        filtered_principais.append(p)
                principais = filtered_principais

            if state.filter_category != "Todos":
                principais = [p for p in principais if p.get('categoria') == state.filter_category]

            # Filtro por status de alocação (Pendente x Completo)
            status_filter = getattr(state, 'filter_seat_status', 'Todos')
            if status_filter == 'pendentes':
                # Tem pendência se a própria autoridade ou algum acompanhante não tem assento
                principais = [
                    p for p in principais 
                    if not p.get('assento_id') or any(not c.get('assento_id') for c in convidados if c.get('convidado_principal_id') == p['id'])
                ]
            elif status_filter == 'completos':
                # 100% alocado se a autoridade E todos os seus acompanhantes têm assento
                principais = [
                    p for p in principais 
                    if p.get('assento_id') and all(c.get('assento_id') for c in convidados if c.get('convidado_principal_id') == p['id'])
                ]

            if principais:
                with ui.column().classes('w-full gap-3 scroll-container q-pr-xs').style('max-height: 680px; overflow-y: auto;'):
                    with ui.grid(columns='1 md:grid-cols-2 lg:grid-cols-3').classes('w-full gap-4'):
                        for p in principais:
                            acomp_list = [c for c in convidados if c.get('convidado_principal_id') == p['id']]
                            
                            is_p_allocated = bool(p.get('assento_id'))
                            all_acomp_allocated = len(acomp_list) > 0 and all(bool(ac.get('assento_id')) for ac in acomp_list)
                            is_group_complete = is_p_allocated and (len(acomp_list) == 0 or all_acomp_allocated)

                            card_border = 'rgba(0, 230, 118, 0.4)' if is_group_complete else ('rgba(0, 229, 255, 0.4)' if is_p_allocated else 'rgba(255, 255, 255, 0.08)')
                            header_icon = '✅' if is_group_complete else ('⏳' if is_p_allocated else '⚠️')
                            
                            nome_p = f"{p.get('posto_graduacao') or ''} {p['nome']}".strip()
                            cargo_p = p.get('cargo_funcao') or p.get('categoria') or 'Autoridade'
                            
                            with ui.expansion().classes('w-full rounded-xl border no-shadow').style(
                                f'background: rgba(19, 26, 38, 0.95); border-color: {card_border} !important;'
                            ) as exp:
                                with exp.add_slot('header'):
                                    with ui.row().classes('w-full justify-between items-center no-wrap gap-2'):
                                        with ui.column().classes('gap-0 col'):
                                            ui.label(f"{header_icon} {nome_p}").classes('text-sm font-bold text-white cyber-title')
                                            ui.label(f"[{p.get('categoria', 'Geral')}] {cargo_p}").classes('text-xs text-grey-4')

                                        with ui.row().classes('items-center gap-1'):
                                            if is_p_allocated:
                                                ui.badge(f"Assento {p['assento_id']}").props('color=cyan text-color=black bold').classes('text-[10px]')
                                            else:
                                                ui.badge('Sem Assento').props('color=grey-8').classes('text-[10px]')

                                # --- CONTEÚDO DO CARD COLAPSÁVEL ---
                                with ui.column().classes('w-full q-pa-sm gap-2'):
                                    # Ações da Autoridade
                                    with ui.row().classes('w-full justify-between items-center bg-black/30 q-pa-xs rounded-lg'):
                                        ui.label('Ações da Autoridade:').classes('text-[11px] text-grey-4 font-bold')
                                        with ui.row().classes('items-center gap-1'):
                                            if is_p_allocated:
                                                ui.button('Desalocar', icon='cancel', on_click=lambda p=p: remove_guest_allocation(p)).props('unelevated color=danger dense flat').classes('text-xs')
                                            ui.button('Editar', icon='edit', on_click=lambda p=p: open_edit_guest_dialog(p)).props('unelevated color=primary dense flat').classes('text-xs')
                                            ui.button('Excluir', icon='delete', on_click=lambda p=p: confirm_delete_guest(p)).props('unelevated color=danger dense flat').classes('text-xs')

                                    # Controle Quantitativo (+ / -)
                                    max_ac = p.get('max_acompanhantes', 0)
                                    with ui.row().classes('w-full justify-between items-center q-py-xs bg-black/20 px-2 rounded-lg'):
                                        ui.label(f"Acompanhantes Vagas: {max_ac}").classes('text-xs text-amber font-bold')
                                        
                                        with ui.row().classes('items-center gap-1'):
                                            if max_ac > 0:
                                                def dec_acomp(p_ref=p):
                                                    new_ac = max(0, p_ref.get('max_acompanhantes', 0) - 1)
                                                    reg = {
                                                        'nome': p_ref['nome'],
                                                        'posto_graduacao': p_ref.get('posto_graduacao'),
                                                        'cargo_funcao': p_ref.get('cargo_funcao'),
                                                        'categoria': p_ref.get('categoria', 'Geral'),
                                                        'max_acompanhantes': new_ac
                                                    }
                                                    save_guest(p_ref['id'], reg, current_event['id'])
                                                
                                                ui.button('-', on_click=dec_acomp).props('unelevated color=amber text-color=black dense round').style('width: 22px; height: 22px; font-weight: bold;')

                                            def inc_acomp(p_ref=p):
                                                new_ac = p_ref.get('max_acompanhantes', 0) + 1
                                                reg = {
                                                    'nome': p_ref['nome'],
                                                    'posto_graduacao': p_ref.get('posto_graduacao'),
                                                    'cargo_funcao': p_ref.get('cargo_funcao'),
                                                    'categoria': p_ref.get('categoria', 'Geral'),
                                                    'max_acompanhantes': new_ac
                                                }
                                                save_guest(p_ref['id'], reg, current_event['id'])

                                            ui.button('+', on_click=inc_acomp).props('unelevated color=amber text-color=black dense round').style('width: 22px; height: 22px; font-weight: bold;')

                                    # Lista de Acompanhantes
                                    if acomp_list:
                                        with ui.column().classes('w-full gap-1 q-mt-xs pl-2 border-l-2 border-amber-500/40'):
                                            for ac in acomp_list:
                                                is_ac_allocated = bool(ac.get('assento_id'))
                                                ac_bg = 'rgba(255, 183, 77, 0.08)' if is_ac_allocated else 'rgba(255, 255, 255, 0.02)'
                                                
                                                with ui.card().classes('w-full q-pa-xs px-2 no-shadow rounded-md').style(f'background: {ac_bg}; border: 1px solid rgba(255,183,77,0.2);'):
                                                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                        with ui.column().classes('gap-0'):
                                                            ui.label(ac['nome']).classes('text-xs text-grey-2 font-medium')
                                                            ui.label('(Acompanhante)').classes('text-[9px] text-amber-4 italic')
                                                        
                                                        if is_ac_allocated:
                                                            with ui.row().classes('items-center gap-1'):
                                                                ui.badge(f"Assento {ac['assento_id']}").props('color=amber text-color=black').classes('text-[9px]')
                                                                ui.button(icon='cancel', on_click=lambda ac=ac: remove_guest_allocation(ac)).props('unelevated color=danger dense flat round').classes('text-xs')
                                                        else:
                                                            ui.badge('Sem Assento').props('color=grey-8').classes('text-[9px]')
            else:
                with ui.column().classes('w-full items-center justify-center q-py-xl text-grey'):
                    ui.icon('person_off', size='3rem')
                    ui.label('Nenhuma autoridade ou convidado encontrado.').classes('text-sm q-mt-xs')

    # Métodos utilitários do painel
    def select_event(event_id):
        state.selected_event_id = event_id
        render_content.refresh()

    def toggle_mode(mode):
        state.edit_mode = mode
        render_content.refresh()

    def update_search(query):
        state.search_query = query
        render_content.refresh()

    def update_filter_category(cat):
        state.filter_category = cat
        render_content.refresh()

    def update_filter_unallocated(val):
        state.filter_only_unallocated = val
        render_content.refresh()

    def update_filter_seat_status(val):
        state.filter_seat_status = val
        render_content.refresh()

    def create_event(nome, data, local, layout_tipo, rows, cols, ref_top, ref_bottom):
        if not nome or not data:
            ui.notify('Nome e Data do evento são obrigatórios.', color='warning')
            return
            
        db = get_service_db_connection() or get_db_connection()
        if db:
            layout_data = {
                'tipo': layout_tipo,
                'rows': int(rows),
                'cols': int(cols),
                'ref_top': ref_top or 'PALCO PRINCIPAL',
                'ref_bottom': ref_bottom or 'ENTRADA / FACHADA',
                'blocked_seats': []
            }
            try:
                res = db.table('jade_eventos').insert({
                    'nome': nome.upper(),
                    'data_evento': data,
                    'local': local or '',
                    'layout_json': json.dumps(layout_data)
                }).execute()
                
                ui.notify('Evento criado com sucesso!', color='success')
                if res.data:
                    state.selected_event_id = res.data[0]['id']
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao criar evento: {e}", color='red')

    def delete_event(event):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                db.table('jade_convidados').delete().eq('evento_id', event['id']).execute()
                db.table('jade_eventos').delete().eq('id', event['id']).execute()
                ui.notify('Evento e dados associados excluídos.', color='success')
                state.selected_event_id = None
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao excluir evento: {e}", color='red')

    def save_guest(guest_id, data, event_id):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                if guest_id:
                    db.table('jade_convidados').update(data).eq('id', guest_id).execute()
                    ui.notify('Dados do convidado atualizados.', color='success')
                    sync_companions(guest_id, data['nome'], data['max_acompanhantes'], event_id, data['categoria'])
                else:
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
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                db.table('jade_convidados').delete().eq('convidado_principal_id', guest['id']).execute()
                db.table('jade_convidados').delete().eq('id', guest['id']).execute()
                ui.notify(f"Convidado {guest['nome']} e acompanhantes removidos.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao excluir convidado: {e}", color='red')

    def allocate_guest(guest_id, seat_id, event_id):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                db.table('jade_convidados').update({'assento_id': None}).eq('evento_id', event_id).eq('assento_id', seat_id).execute()
                db.table('jade_convidados').update({'assento_id': seat_id}).eq('id', guest_id).execute()
                ui.notify(f"Assento {seat_id} ocupado com sucesso.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao alocar assento: {e}", color='red')

    def remove_guest_allocation(guest):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                db.table('jade_convidados').update({'assento_id': None}).eq('id', guest['id']).execute()
                ui.notify(f"Convidado {guest['nome']} removido do assento {guest['assento_id']}.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao remover alocação: {e}", color='red')

    def swap_guests(guest_a, guest_b_id, event_id):
        db = get_service_db_connection() or get_db_connection()
        if db:
            try:
                seat_a = guest_a.get('assento_id')
                res_b = db.table('jade_convidados').select('*').eq('id', guest_b_id).execute()
                if not res_b.data:
                    return
                guest_b = res_b.data[0]
                seat_b = guest_b.get('assento_id')
                
                db.table('jade_convidados').update({'assento_id': seat_b}).eq('id', guest_a['id']).execute()
                db.table('jade_convidados').update({'assento_id': seat_a}).eq('id', guest_b['id']).execute()
                
                ui.notify("Troca de assentos efetuada.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao realizar troca: {e}", color='red')

    def toggle_seat_block(seat_id, event, layout):
        db = get_service_db_connection() or get_db_connection()
        if db:
            blocked = layout.get('blocked_seats', [])
            if seat_id in blocked:
                blocked.remove(seat_id)
            else:
                blocked.append(seat_id)
                
            layout['blocked_seats'] = blocked
            new_layout_json = json.dumps(layout)
            
            try:
                db.table('jade_convidados').update({'assento_id': None}).eq('evento_id', event['id']).eq('assento_id', seat_id).execute()
                db.table('jade_eventos').update({'layout_json': new_layout_json}).eq('id', event['id']).execute()
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao atualizar layout: {e}", color='red')

    def update_grid_size(event, layout, row_delta, col_delta):
        db = get_service_db_connection() or get_db_connection()
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

    # --- MODAIS E DIÁLOGOS ---
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
                    db = get_service_db_connection() or get_db_connection()
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
                    save_guest(guest['id'] if guest else None, reg, event_id or state.selected_event_id)
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
            if 'VIP' in cat_upper: return 0
            if 'MILITAR' in cat_upper: return 1
            if 'CIVIL' in cat_upper: return 2
            if 'IMPRENSA' in cat_upper: return 3
            if 'APOIO' in cat_upper: return 4
            return 5

        sorted_convidados = sorted(
            convidados,
            key=lambda c: (get_category_priority(c.get('categoria', 'Geral')), c.get('posto_graduacao') or '', c['nome'])
        )
        
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 420px; max-height: 550px;'):
            ui.label(f'Alocar Assento {seat_id}').classes('text-md font-bold text-cyan q-mb-xs')
            ui.label('Selecione um convidado na lista para alocar imediatamente:').classes('text-xs text-grey-4 q-mb-md')
            
            search_input = ui.input(placeholder='Filtrar por nome ou cargo...').props('dark outlined dense clearable w-full q-mb-md')
            
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
        with ui.dialog() as diag, ui.card().classes('q-pa-md').style('min-width: 400px; max-height: 600px;'):
            ui.label(f'Ações do Assento {seat_id}').classes('text-md font-bold text-cyan q-mb-xs')
            
            nome_completo = f"{guest.get('posto_graduacao') or ''} {guest['nome']}".strip()
            ui.label(nome_completo).classes('text-sm font-bold text-white')
            ui.label(guest.get('cargo_funcao') or guest.get('categoria') or 'Convidado').classes('text-xs text-grey-4 q-mb-md')
            
            ui.button(
                'Liberar / Desalocar Assento', 
                icon='block', 
                on_click=lambda: [remove_guest_allocation(guest), diag.close()]
            ).props('unelevated color=danger w-full q-mb-sm dense')
            
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
                    'Confirmar Troca', 
                    icon='swap_horiz', 
                    on_click=lambda: [swap_guests(guest, swap_target.value, event_id), diag.close()]
                ).props('unelevated color=primary text-color=black w-full q-mt-xs dense')
                
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('Fechar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
        diag.open()

    def open_print_cards_dialog(event, convidados, layout):
        rows_count = layout.get('rows', 5)
        allocated_by_row = {}
        for r in range(rows_count):
            row_label = get_row_label(r)
            allocated_by_row[row_label] = [c for c in convidados if c.get('assento_id', '').startswith(f"{row_label}-")]

    def open_print_cards_dialog(event, convidados, layout):
        rows_count = layout.get('rows', 5)
        allocated_by_row = {}
        for r in range(rows_count):
            row_label = get_row_label(r)
            allocated_by_row[row_label] = [c for c in convidados if c.get('assento_id', '').startswith(f"{row_label}-")]

        # Estado local de modelo de impressão
        print_config = {
            'model': 'cadeira_a4', # 'cadeira_a4', 'mesa_a5_dobravel', 'credencial'
            'show_logo': True,
            'show_qr': True,
            'show_rank': True,
            'show_cargo': True
        }

        # Insígnias / Indicadores visuais por Posto/Graduação
        rank_badges = {
            'AE': '⭐⭐⭐⭐ ALMIRANTE DE ESQUADRA',
            'VA': '⭐⭐⭐ VICE-ALMIRANTE',
            'CA': '⭐⭐ CONTRA-ALMIRANTE',
            'CMG': '🦅 CAPITÃO DE MAR E GUERRA',
            'CF': '⚓ CAPITÃO DE FRAGATA',
            'CT': '⚓ CAPITÃO DE CORVETA',
            'CC': '⚓ CAPITÃO-TENENTE',
            '1DN': '🔰 MARINHA DO BRASIL',
            'Dr.': '⚖️ AUTORIDADE CIVIL',
            'Min.': '🏛️ MINISTRO DE ESTADO'
        }

        with ui.dialog() as diag, ui.card().classes('q-pa-lg').style('min-width: 780px; max-width: 95vw; max-height: 90vh; overflow-y: auto;'):
            ui.label(f"🖨️ ESTÚDIO DE IMPRESSÃO DE PLACAS & CREDENCIAIS JADE").classes('text-md font-bold text-cyan cyber-title q-mb-xs')
            ui.label("Configure os Modelos de Placas, Brasões, Insígnias de Posto/Graduação e Quebra de Páginas").classes('text-xs text-grey-4 q-mb-md')

            # --- CONTROLES DO ESTÚDIO DE IMPRESSÃO ---
            with ui.card().classes('w-full q-pa-sm bg-black/40 border border-cyan-500/30 rounded-xl q-mb-md print-hide'):
                with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Modelo de Impressão:').classes('text-xs text-grey-3 font-bold')
                        model_select = ui.select(
                            options={
                                'cadeira_a4': '📄 Placa de Cadeira (A4 Padrão)',
                                'mesa_a5_dobravel': '🏷️ Placa de Mesa Dobrável (A5 Display)',
                                'credencial': '🪪 Credencial / Crachá de Peito'
                            },
                            value=print_config['model']
                        ).props('dark outlined dense').style('min-width: 260px;')

                    with ui.row().classes('items-center gap-3'):
                        ui.checkbox('Brasão da MB', value=print_config['show_logo'], on_change=lambda e: preview_container.refresh()).props('dark dense').classes('text-xs text-grey-3')
                        ui.checkbox('QR Code Tático', value=print_config['show_qr'], on_change=lambda e: preview_container.refresh()).props('dark dense').classes('text-xs text-grey-3')
                        ui.checkbox('Insígnia de Posto', value=print_config['show_rank'], on_change=lambda e: preview_container.refresh()).props('dark dense').classes('text-xs text-grey-3')

            # CSS Específico para Impressão Perfeita no Papel / PDF
            print_css = """
            <style>
            @media print {
                body * { visibility: hidden !important; background: white !important; color: black !important; }
                .print-area, .print-area * { visibility: visible !important; }
                .print-area { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; }
                .print-hide { display: none !important; }
                .page-break { page-break-after: always !important; }
                .print-card-a4 { border: 2px solid #000 !important; margin-bottom: 20px !important; padding: 20px !important; background: #fff !important; color: #000 !important; border-radius: 8px !important; }
                .print-card-mesa { border: 2px dashed #666 !important; padding: 15px !important; background: #fff !important; color: #000 !important; margin-bottom: 20px !important; }
                .print-card-credencial { border: 1px solid #000 !important; width: 300px !important; height: 420px !important; padding: 15px !important; margin: 10px !important; float: left !important; }
            }
            </style>
            """
            ui.add_head_html(print_css)

            @ui.refreshable
            def preview_container():
                current_model = model_select.value
                with ui.column().classes('w-full gap-4 print-area'):
                    for row_label, list_c in allocated_by_row.items():
                        if not list_c:
                            continue

                        with ui.column().classes('w-full gap-2 page-break q-mb-md'):
                            with ui.row().classes('w-full justify-between items-center bg-cyan-950/60 q-pa-sm rounded-lg border border-cyan-500/40 print-hide'):
                                ui.label(f"FILEIRA {row_label} — {len(list_c)} CARTÕES").classes('text-sm font-bold text-cyan')
                                ui.badge(f"Lote Fileira {row_label}").props('color=cyan text-color=black')

                            # RENDERIZAÇÃO DOS CARTÕES CONFORME MODELO SELECIONADO
                            if current_model == 'cadeira_a4':
                                with ui.grid(columns='1 sm:grid-cols-2').classes('w-full gap-4'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id','')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        insignia = rank_badges.get(posto, '⚓ MARINHA DO BRASIL') if print_config['show_rank'] else ''
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={c['id']}&color=000000&bgcolor=ffffff"

                                        with ui.card().classes('w-full q-pa-md print-card-a4 bg-slate-900 border border-cyan-500/40 rounded-xl').style('border-left: 6px solid #00e5ff !important;'):
                                            with ui.row().classes('w-full justify-between items-start no-wrap'):
                                                with ui.column().classes('gap-0 col'):
                                                    if print_config['show_logo']:
                                                        ui.label('⚓ MARINHA DO BRASIL').classes('text-[10px] font-black text-cyan tracking-widest')
                                                    
                                                    ui.badge(f"ASSENTO {c['assento_id']}").props('color=cyan text-color=black bold').classes('text-xs w-fit q-my-xs')
                                                    
                                                    if insignia:
                                                        ui.label(insignia).classes('text-[9px] text-amber font-bold')
                                                        
                                                    nome_c = f"{posto} {c['nome']}".strip()
                                                    ui.label(nome_c).classes('text-md font-black text-white leading-tight q-mt-xs')
                                                    
                                                    sub = '(Acompanhante Oficial)' if is_acomp else (c.get('cargo_funcao') or c.get('categoria') or 'Convidado de Honra')
                                                    ui.label(sub).classes('text-xs text-grey-4 font-bold q-mt-xs')
                                                
                                                if print_config['show_qr']:
                                                    with ui.column().classes('items-center gap-0'):
                                                        ui.image(qr_url).classes('w-16 h-16 rounded bg-white p-1')
                                                        ui.label(f"ID:{c['id']}").classes('text-[8px] font-mono text-grey-5')

                            elif current_model == 'mesa_a5_dobravel':
                                with ui.grid(columns='1 sm:grid-cols-2').classes('w-full gap-4'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id','')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        nome_c = f"{posto} {c['nome']}".strip()
                                        sub = '(Acompanhante)' if is_acomp else (c.get('cargo_funcao') or 'Convidado')
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={c['id']}"

                                        with ui.card().classes('w-full q-pa-md print-card-mesa bg-slate-900 border-2 border-dashed border-cyan-500/40 rounded-xl text-center'):
                                            ui.label('✂️ DOBRA DE MESA (FACE FRONTAL)').classes('text-[8px] text-grey-5 tracking-widest uppercase print-hide')
                                            ui.label(f"ASSENTO {c['assento_id']}").classes('text-sm font-black text-cyan')
                                            ui.label(nome_c).classes('text-lg font-black text-white q-my-xs')
                                            ui.label(sub).classes('text-xs text-grey-3 font-bold')
                                            
                                            ui.separator().classes('q-my-sm print-hide').style('border-color: rgba(255,255,255,0.1);')
                                            ui.label('✂️ DOBRA DE MESA (FACE TRASEIRA)').classes('text-[8px] text-grey-5 tracking-widest uppercase print-hide')
                                            with ui.row().classes('w-full justify-center items-center gap-2 q-mt-xs'):
                                                if print_config['show_qr']:
                                                    ui.image(qr_url).classes('w-12 h-12 bg-white p-1 rounded')
                                                ui.label(f"FILEIRA {row_label} | {c['assento_id']}").classes('text-xs text-grey-4 font-mono font-bold')

                            elif current_model == 'credencial':
                                with ui.grid(columns='1 sm:grid-cols-2 md:grid-cols-3').classes('w-full gap-3'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id','')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        nome_c = f"{posto} {c['nome']}".strip()
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={c['id']}"

                                        with ui.card().classes('w-full print-card-credencial bg-slate-900 border border-amber-500/40 rounded-2xl q-pa-md items-center text-center justify-between').style('height: 280px;'):
                                            with ui.column().classes('items-center gap-0 w-full'):
                                                ui.label('⚓ MARINHA DO BRASIL').classes('text-[9px] font-black text-cyan tracking-widest')
                                                ui.label(event.get('nome','SOLENIDADE')).classes('text-[10px] font-bold text-amber truncate w-full')
                                                ui.separator().classes('q-my-xs w-full').style('border-color: rgba(255,255,255,0.1);')
                                            
                                            with ui.column().classes('items-center gap-0 w-full'):
                                                ui.badge(f"FILEIRA {row_label} - ASSENTO {c['assento_id']}").props('color=cyan text-color=black bold').classes('text-xs q-mb-xs')
                                                ui.label(nome_c).classes('text-sm font-black text-white leading-tight')
                                                sub = '(Acompanhante)' if is_acomp else (c.get('cargo_funcao') or c.get('categoria'))
                                                ui.label(sub).classes('text-[10px] text-grey-4 font-bold')

                                            if print_config['show_qr']:
                                                ui.image(qr_url).classes('w-14 h-14 bg-white p-1 rounded border border-cyan-500')

            model_select.on('value-change', preview_container.refresh)
            preview_container()

            with ui.row().classes('w-full justify-end gap-2 q-mt-md print-hide'):
                ui.button('Fechar', on_click=diag.close).props('unelevated color=grey-8 dense')
                ui.button('🖨️ Imprimir Placas Selecionadas (Ctrl + P)', on_click=lambda: ui.run_javascript('window.print()')).props('unelevated color=cyan text-color=black bold dense')
        diag.open()

    def open_tactical_scanner_dialog(event, convidados):
        scanned_history = []

        with ui.dialog() as diag, ui.card().classes('q-pa-lg').style('min-width: 620px; max-width: 95vw;'):
            ui.label('🔍 SCANNER & CONFERÊNCIA TÁTICA').classes('text-md font-bold text-amber cyber-title q-mb-xs')
            ui.label('Use a Câmera do Celular ou Leitor Físico para separar e bater a lista por Fileira').classes('text-xs text-grey-4 q-mb-md')
            
            with ui.row().classes('w-full gap-2 q-mb-md items-center'):
                scan_input = ui.input(placeholder='Bipe o QR Code ou digite ID/Nome/Assento (ex: G-5)...').props('dark outlined dense autofocus').classes('col')
                cam_btn = ui.button('📸 Câmera do Celular', icon='videocam').props('unelevated color=primary text-color=black dense').classes('text-xs')

            # Container da Câmera do Celular (HTML5 QR Scanner)
            cam_container = ui.column().classes('w-full hidden q-mb-md border border-cyan-500/40 rounded-xl q-pa-sm bg-black/60')
            with cam_container:
                ui.label('📸 Aponta a câmera para o QR Code impresso no cartão:').classes('text-xs font-bold text-cyan text-center w-full q-mb-xs')
                ui.html('''
                    <div id="qr-reader" style="width:100%; max-width:400px; margin:0 auto; background:#000; border-radius:8px;"></div>
                    <script src="https://unpkg.com/html5-qrcode"></script>
                ''').classes('w-full flex justify-center')
                ui.button('🛑 Fechar Câmera', on_click=lambda: cam_container.classes(add='hidden')).props('flat color=grey dense').classes('w-full text-xs q-mt-xs')

            def toggle_camera():
                cam_container.classes(remove='hidden')
                ui.run_javascript('''
                    if (window.html5QrcodeScanner) {
                        try { window.html5QrcodeScanner.clear(); } catch(e){}
                    }
                    window.html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", { fps: 10, qrbox: {width: 250, height: 250} }, false);
                    window.html5QrcodeScanner.render(function(decodedText, decodedResult) {
                        let inp = document.querySelector('input[placeholder*="Bipe"]');
                        if (inp) {
                            inp.value = decodedText;
                            inp.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter', 'keyCode': 13, 'bubbles': true}));
                        }
                    }, function(error) {});
                ''')

            cam_btn.on_click(toggle_camera)
            feedback_container = ui.column().classes('w-full')

            # Script de áudio para bipe sonoro tático
            audio_script = """
            function playBeep(type) {
                try {
                    let ctx = new (window.AudioContext || window.webkitAudioContext)();
                    let osc = ctx.createOscillator();
                    let gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    if (type === 'success') {
                        osc.frequency.value = 880;
                        gain.gain.value = 0.12;
                        osc.start();
                        setTimeout(() => osc.stop(), 150);
                    } else if (type === 'duplicate') {
                        osc.frequency.value = 280;
                        gain.gain.value = 0.25;
                        osc.start();
                        setTimeout(() => osc.stop(), 320);
                    }
                } catch(e) {}
            }
            """
            ui.add_head_html(f"<script>{audio_script}</script>")

            def process_scan(val):
                if not val or not val.strip():
                    return
                query = val.strip().lower()
                scan_input.value = ''
                feedback_container.clear()
                
                # Busca convidado por ID exato do QR Code, Assento ou Nome
                matches = [
                    c for c in convidados
                    if str(c.get('id', '')) == query or
                    query == str(c.get('assento_id', '')).lower() or
                    query in c['nome'].lower() or
                    (c.get('posto_graduacao') and query in f"{c.get('posto_graduacao')} {c['nome']}".lower())
                ]

                with feedback_container:
                    if not matches:
                        ui.run_javascript("playBeep('duplicate')")
                        with ui.card().classes('w-full q-pa-md bg-red-950/80 border border-red-500 rounded-xl text-center'):
                            ui.icon('cancel', color='red', size='3rem')
                            ui.label('❌ CARTÃO / CONVIDADO NÃO ENCONTRADO!').classes('text-sm font-bold text-red-3')
                            ui.label(f"Nenhum assento ou convidado registrado para o código: '{val}'").classes('text-xs text-grey-4')
                    else:
                        target = matches[0]
                        seat = target.get('assento_id', 'NÃO ALOCADO')
                        row_name = seat.split('-')[0] if '-' in seat else 'N/A'
                        is_duplicate = target['id'] in scanned_history

                        if is_duplicate:
                            ui.run_javascript("playBeep('duplicate')")
                            with ui.card().classes('w-full q-pa-md bg-amber-950/80 border border-amber-500 rounded-xl text-center'):
                                ui.icon('warning', color='amber', size='3rem')
                                ui.label('⚠️ ATENÇÃO: CARTÃO JÁ CONFERIDO & SEPARADO!').classes('text-sm font-bold text-amber-3')
                                ui.label(f"{target['nome']} — Assento: {seat} (Fileira {row_name})").classes('text-xs text-grey-3 font-bold')
                                ui.label('Este cartão já passou pela triagem anteriormente.').classes('text-[11px] text-amber-4 q-mt-xs')
                        else:
                            scanned_history.append(target['id'])
                            ui.run_javascript("playBeep('success')")
                            
                            main_info = ""
                            if target.get('convidado_principal_id'):
                                p_main = next((x for x in convidados if x['id'] == target['convidado_principal_id']), None)
                                if p_main:
                                    main_info = f" (Acompanhante de {p_main['nome']})"

                            with ui.card().classes('w-full q-pa-md bg-green-950/80 border border-green-500 rounded-xl text-center'):
                                ui.icon('check_circle', color='green', size='3rem')
                                ui.label('✅ CONFERIDO & SEPARADO COM SUCESSO!').classes('text-sm font-bold text-green-3')
                                ui.label(f"{target.get('posto_graduacao') or ''} {target['nome']}{main_info}").classes('text-md font-bold text-white')
                                
                                with ui.row().classes('w-full justify-center items-center gap-2 q-mt-xs'):
                                    ui.badge(f"COLOCAR NA FILEIRA {row_name}").props('color=cyan text-color=black bold').classes('text-sm q-px-sm')
                                    ui.badge(f"ASSENTO {seat}").props('color=green text-color=white bold').classes('text-sm q-px-sm')

            scan_input.on('keydown.enter', lambda: process_scan(scan_input.value))

            with ui.row().classes('w-full justify-between items-center q-mt-md'):
                ui.label(f"Total Conferidos: {len(scanned_history)} de {len([c for c in convidados if c.get('assento_id')])} cartões").classes('text-xs text-cyan font-bold')
                ui.button('Concluir Conferência', on_click=diag.close).props('unelevated color=grey-8 dense')
        diag.open()

    def download_template():
        df = pd.DataFrame([
            {
                'Nome': 'ALMIRANTE SILVA', 
                'Posto/Graduacao': 'AE', 
                'Cargo/Função': 'Comandante da Marinha', 
                'Categoria': 'VIP', 
                'Max Acompanhantes': 2
            },
            {
                'Nome': 'MINISTRO SANTOS', 
                'Posto/Graduacao': 'Dr.', 
                'Cargo/Função': 'Ministro de Estado', 
                'Categoria': 'Autoridade Civil', 
                'Max Acompanhantes': 1
            }
        ])
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Convidados')
        output.seek(0)
        
        ui.download(output.read(), 'modelo_importacao_jade.xlsx')

    def handle_import_list(e, event_id):
        try:
            file = e.files[0]
            content = file.content.read()
            
            if file.name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
                
            required_cols = ['Nome']
            for col in required_cols:
                if col not in df.columns:
                    ui.notify(f"Coluna obrigatória '{col}' não encontrada na planilha.", color='red')
                    return
                    
            db = get_service_db_connection() or get_db_connection()
            if not db:
                return
                
            count = 0
            for _, row in df.iterrows():
                nome = str(row['Nome']).strip().upper()
                if not nome or nome == 'NAN':
                    continue
                    
                posto = str(row.get('Posto/Graduacao', '')).strip() if pd.notna(row.get('Posto/Graduacao')) else None
                cargo = str(row.get('Cargo/Função', '')).strip() if pd.notna(row.get('Cargo/Função')) else None
                cat = str(row.get('Categoria', 'Geral')).strip() if pd.notna(row.get('Categoria')) else 'Geral'
                
                try:
                    acomp = int(row.get('Max Acompanhantes', 0)) if pd.notna(row.get('Max Acompanhantes')) else 0
                except ValueError:
                    acomp = 0
                    
                guest_data = {
                    'evento_id': event_id,
                    'nome': nome,
                    'posto_graduacao': posto,
                    'cargo_funcao': cargo,
                    'categoria': cat,
                    'max_acompanhantes': acomp
                }
                
                res = db.table('jade_convidados').insert(guest_data).execute()
                if res.data:
                    new_id = res.data[0]['id']
                    sync_companions(new_id, nome, acomp, event_id, cat)
                count += 1
                
            ui.notify(f"Importados {count} convidados com sucesso!", color='success')
            render_content.refresh()
        except Exception as ex:
            ui.notify(f"Erro ao importar planilha: {ex}", color='red')

    render_content()
