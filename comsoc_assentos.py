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
        self.selected_sector = "Todos"  # "Todos" ou nome específico do Setor
        self.zoom_level = "normal"  # "compact", "normal", "large"

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

        convidados = []
        layout = {}
        if current_event:
            try:
                res_conv = db.table('jade_convidados').select('*').eq('evento_id', current_event['id']).order('id', desc=False).execute()
                convidados = res_conv.data if res_conv.data else []
            except Exception as e:
                print(f"[JADE GUESTS FETCH ERR] {e}")

            try:
                layout = json.loads(current_event['layout_json']) if current_event.get('layout_json') else {}
            except Exception as e:
                print(f"[LAYOUT PARSE ERR] {e}")

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
                        ui.button('⚡ Placa Express', icon='bolt', on_click=lambda: open_express_plate_dialog(current_event, convidados, layout)).props('unelevated color=deep-orange text-color=white dense bold').classes('q-px-sm')
                        ui.button('✅ Confirmar Presenças', icon='how_to_reg', on_click=lambda: open_mass_confirmation_dialog(current_event, convidados)).props('unelevated color=green text-color=white dense bold').classes('q-px-sm')
                        ui.button('📥 Importar Excel', icon='file_upload', on_click=lambda: open_smart_excel_import_dialog(current_event)).props('unelevated color=deep-purple text-color=white dense bold').classes('q-px-sm')
                        ui.button('🏛️ Cadastro Mestre', icon='account_balance', on_click=lambda: open_master_authorities_dialog(current_event)).props('unelevated color=indigo text-color=white dense bold').classes('q-px-sm')
                        ui.button('🖨️ Imprimir Placas', icon='print', on_click=lambda: open_print_cards_dialog(current_event, convidados, layout)).props('unelevated color=cyan text-color=black dense bold').classes('q-px-sm')
                        ui.button('🔍 Scanner & Conferência', icon='qr_code_scanner', on_click=lambda: open_tactical_scanner_dialog(current_event, convidados)).props('unelevated color=amber text-color=black dense bold').classes('q-px-sm')
                        
                        ui.button('Editar Evento', icon='edit', on_click=lambda: open_edit_event_dialog(current_event, layout)).props('unelevated color=accent dense outline').classes('q-px-sm')
                        ui.button('Excluir Evento', icon='delete', on_click=lambda: confirm_delete_event(current_event)).props('unelevated color=danger dense outline').classes('q-px-sm')

        # ═══════════════════════════════════════════════════════════════
        # FASE 1: PAINEL DE FILA DE PRODUÇÃO DE PLACAS JADE
        # ═══════════════════════════════════════════════════════════════
        if current_event and convidados:
            # Contadores de status de placa
            count_pending = sum(1 for c in convidados if c.get('status_placa') == 'pendente')
            count_producing = sum(1 for c in convidados if c.get('status_placa') == 'em_producao')
            count_printed = sum(1 for c in convidados if c.get('status_placa') == 'impressa')
            count_reprint = sum(1 for c in convidados if c.get('status_placa') == 'reimpressao')
            count_delivered = sum(1 for c in convidados if c.get('status_placa') == 'entregue')
            count_not_needed = sum(1 for c in convidados if c.get('status_placa', 'nao_necessaria') == 'nao_necessaria')
            
            # Contadores de confirmação
            count_confirmed = sum(1 for c in convidados if c.get('status_confirmacao') == 'confirmado')
            count_refused = sum(1 for c in convidados if c.get('status_confirmacao') == 'recusado')
            count_probable = sum(1 for c in convidados if c.get('status_confirmacao') == 'provavel')
            count_conf_pending = len(convidados) - count_confirmed - count_refused - count_probable
            
            total_plates_active = count_pending + count_producing + count_reprint

            if total_plates_active > 0 or count_printed > 0 or count_confirmed > 0:
                with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl q-mb-md').style(
                    f'background: linear-gradient(135deg, rgba(0,20,40,0.9) 0%, rgba(0,40,60,0.8) 100%); border: 1px solid rgba(0,229,255,0.3);'
                ):
                    with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('print', color='cyan').classes('text-lg')
                            ui.label('FILA DE PRODUÇÃO JADE').classes('text-xs font-bold text-cyan tracking-widest')
                        
                        with ui.row().classes('items-center gap-2 wrap'):
                            # Badges de status com cores
                            if count_pending > 0:
                                with ui.badge(f'🟡 {count_pending} Pendentes').props('color=amber text-color=black').classes('text-xs cursor-pointer'):
                                    pass
                            if count_producing > 0:
                                with ui.badge(f'🔵 {count_producing} Em Produção').props('color=blue text-color=white').classes('text-xs'):
                                    pass
                            if count_printed > 0:
                                with ui.badge(f'🟢 {count_printed} Impressas').props('color=green text-color=white').classes('text-xs'):
                                    pass
                            if count_reprint > 0:
                                with ui.badge(f'🔴 {count_reprint} Reimpressão').props('color=red text-color=white').classes('text-xs'):
                                    pass
                            if count_delivered > 0:
                                with ui.badge(f'✅ {count_delivered} Entregues').props('color=teal text-color=white').classes('text-xs'):
                                    pass
                        
                        with ui.row().classes('items-center gap-1'):
                            ui.label(f'👥 {count_confirmed} conf. | {count_conf_pending} pend. | {count_refused} rec.').classes('text-[10px] text-grey-4')
                            
                            # Botões de ação rápida
                            async def mark_pending_as_producing():
                                _db = get_service_db_connection() or get_db_connection()
                                if _db:
                                    for c in convidados:
                                        if c.get('status_placa') == 'pendente':
                                            try:
                                                _db.table('jade_convidados').update({'status_placa': 'em_producao'}).eq('id', c['id']).execute()
                                            except Exception:
                                                pass
                                    ui.notify(f'🔵 {count_pending} placas movidas para "Em Produção"', color='info')
                                    render_content.refresh()
                            
                            async def mark_producing_as_printed():
                                _db = get_service_db_connection() or get_db_connection()
                                if _db:
                                    for c in convidados:
                                        if c.get('status_placa') == 'em_producao':
                                            try:
                                                _db.table('jade_convidados').update({'status_placa': 'impressa'}).eq('id', c['id']).execute()
                                            except Exception:
                                                pass
                                    ui.notify(f'🟢 {count_producing} placas marcadas como "Impressas"', color='success')
                                    render_content.refresh()
                            
                            if count_pending > 0:
                                ui.button('▶ Iniciar Produção', on_click=mark_pending_as_producing).props('unelevated color=blue-8 text-color=white dense').classes('text-[10px] q-px-xs')
                            if count_producing > 0:
                                ui.button('✅ Marcar Impressas', on_click=mark_producing_as_printed).props('unelevated color=green-8 text-color=white dense').classes('text-[10px] q-px-xs')

        if not current_event:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-4'):
                ui.icon('event_seat', size='5rem', color='cyan')
                ui.label('Por favor, crie um evento para iniciar o mapeamento de assentos.').classes('text-md text-white font-bold')
                ui.button('Criar Primeiro Evento', icon='add', on_click=open_create_event_dialog).props('unelevated color=primary text-color=black')
            return
            
        rows_count = layout.get('rows', 5)
        cols_count = layout.get('cols', 8)
        blocked_seats = layout.get('blocked_seats', [])

        categories = sorted(list(set(c['categoria'] for c in convidados if c.get('categoria'))))
        category_options = ["Todos"] + categories

        allocated_map = {c['assento_id']: c for c in convidados if c.get('assento_id')}

        # Parse dos setores / blocos de assentos
        sectors = layout.get('sectors', [])
        
        # Se existirem setores, garante que o cols_count abranja até a última coluna cadastrada nos setores
        if sectors:
            max_sector_col = max(s.get('end_col', 1) for s in sectors)
            if max_sector_col > cols_count:
                cols_count = max_sector_col
        else:
            if cols_count >= 4:
                sectors = [
                    {'name': 'SETOR ALPHA (ESQUERDA)', 'start_col': 1, 'end_col': max(1, cols_count // 3)},
                    {'name': 'SETOR NOBRE (CENTRO)', 'start_col': max(1, cols_count // 3) + 1, 'end_col': max(1, (cols_count * 2) // 3)},
                    {'name': 'SETOR BRAVO (DIREITA)', 'start_col': max(1, (cols_count * 2) // 3) + 1, 'end_col': cols_count}
                ]

        # Determinar faixa de colunas ativas conforme filtro de setor
        active_start_col = 1
        active_end_col = cols_count

        if getattr(state, 'selected_sector', 'Todos') != "Todos" and sectors:
            target_sec = next((s for s in sectors if s['name'] == state.selected_sector), None)
            if target_sec:
                active_start_col = target_sec['start_col']
                active_end_col = target_sec['end_col']

        display_cols = list(range(active_start_col, active_end_col + 1))
        display_cols_count = len(display_cols)

        # --- CABEÇALHO DO MAPA DE ASSENTOS COM FILTRO DE SETOR ---
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.row().classes('w-full items-center justify-between q-mb-sm wrap-mobile gap-2'):
                with ui.column().classes('gap-0'):
                    ui.label('🗺️ MAPA DE ASSENTOS DA SOLENIDADE').classes('text-md font-bold text-cyan cyber-title')
                    ui.label(f"Grid: {rows_count} fileiras × {cols_count} colunas • Exibindo: {getattr(state, 'selected_sector', 'Todos').upper()} ({display_cols_count} colunas)").classes('text-[11px] text-grey-4')
                
                    with ui.row().classes('items-center gap-2 wrap'):
                        # SELETOR DE SETOR ATIVO NO MESMO EVENTO
                        if sectors:
                            sector_options = {'Todos': '🌐 Todos os Setores'}
                            for s in sectors:
                                sector_options[s['name']] = f"📍 {s['name']}"
                                
                            ui.select(
                                options=sector_options,
                                value=getattr(state, 'selected_sector', 'Todos'),
                                on_change=lambda e: [setattr(state, 'selected_sector', e.value), render_content.refresh()]
                            ).props('dark outlined dense').style('min-width: 200px;').classes('text-xs')

                        # SELETOR DE ZOOM / TAMANHO DOS ASSENTOS (COMPACTO / NORMAL / AMPLO)
                        ui.select(
                            options={'compact': '🔍 Zoom: Compacto', 'normal': '🔍 Zoom: Normal', 'large': '🔍 Zoom: Amplo'},
                            value=getattr(state, 'zoom_level', 'normal'),
                            on_change=lambda e: [setattr(state, 'zoom_level', e.value), render_content.refresh()]
                        ).props('dark outlined dense').style('width: 145px;').classes('text-xs')

                        # Seletor de Modo de Edição
                        with ui.row().classes('items-center bg-black/30 rounded-lg q-pa-xs border border-white/10'):
                            ui.button('Alocação Rápida', icon='event_seat', on_click=lambda: toggle_mode("alocacao")).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "alocacao" else "flat text-color=grey"}').classes('text-xs q-px-sm')
                            ui.button('Editor de Layout / Corredores', icon='edit_road', on_click=lambda: toggle_mode("layout")).props(f'dense unelevated {"color=primary text-color=black" if state.edit_mode == "layout" else "flat text-color=grey"}').classes('text-xs q-px-sm')

            # Dimensões dinâmicas conforme Zoom
            zoom = getattr(state, 'zoom_level', 'normal')
            if zoom == 'compact':
                seat_w, seat_h, font_name, font_sub = '52px', '38px', '8px', '6px'
            elif zoom == 'large':
                seat_w, seat_h, font_name, font_sub = '90px', '58px', '11px', '8px'
            else:
                seat_w, seat_h, font_name, font_sub = '70px', '48px', '9px', '7px'

            # Renderizador de Grid de Assentos por Setores com Rolagem Dupla Completa
            with ui.column().classes('w-full items-start justify-start q-py-md scroll-container').style('overflow-x: auto; overflow-y: auto; max-height: 580px;'):
                ref_top = layout.get('ref_top', 'PALCO PRINCIPAL')
                if ref_top:
                    with ui.row().classes('w-full justify-center q-mb-sm'):
                        ui.label(f"▲ {ref_top.upper()} ▲").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

                # Cálculo de largura mínima necessária para caber TODAS as colunas sem cortar
                num_px = int(seat_w.replace('px',''))
                min_grid_w = max(600, (display_cols_count + 1) * (num_px + 8) + 60)

                # Cores vibrantes e bem visíveis para diferenciar nitidamente os setores do auditório
                sector_colors = [
                    {'bg': 'rgba(0, 229, 255, 0.18)', 'border': 'rgba(0, 229, 255, 0.45)', 'text': '#00e5ff'},   # Setor 1: Cyan Forte
                    {'bg': 'rgba(255, 183, 77, 0.20)', 'border': 'rgba(255, 183, 77, 0.50)', 'text': '#ffb74d'},  # Setor 2: Amber/Dourado Vívido
                    {'bg': 'rgba(171, 71, 188, 0.20)', 'border': 'rgba(171, 71, 188, 0.50)', 'text': '#ab47bc'},  # Setor 3: Roxo Marcante
                    {'bg': 'rgba(102, 187, 106, 0.20)', 'border': 'rgba(102, 187, 106, 0.50)', 'text': '#66bb6a'}, # Setor 4: Verde Intenso
                    {'bg': 'rgba(239, 83, 80, 0.20)', 'border': 'rgba(239, 83, 80, 0.50)', 'text': '#ef5350'}     # Setor 5: Vermelho Vibrante
                ]

                def get_seat_sector_info(col_num, row_num):
                    if not sectors:
                        return {'bg': 'rgba(0, 230, 118, 0.12)', 'border': 'rgba(0, 230, 118, 0.35)', 'text': '#00e676', 'active': True}
                    for idx, sec in enumerate(sectors):
                        if sec['start_col'] <= col_num <= sec['end_col']:
                            sec_rows = sec.get('rows_count', rows_count)
                            is_active = row_num < sec_rows
                            style_info = sector_colors[idx % len(sector_colors)].copy()
                            style_info['active'] = is_active
                            return style_info
                    return {'bg': 'rgba(255, 255, 255, 0.05)', 'border': 'rgba(255, 255, 255, 0.15)', 'text': '#9e9e9e', 'active': True}

                with ui.grid(columns=display_cols_count + 1).classes('gap-2 items-center').style(f'min-width: {min_grid_w}px;'):
                    ui.label('').classes('text-center font-bold text-grey-5').style('width: 40px;')
                    
                    for col in display_cols:
                        ui.label(str(col)).classes('text-center font-bold text-grey-5').style(f'width: {seat_w}; font-size: 11px;')
                        
                    for r in range(rows_count):
                        row_label = get_row_label(r)
                        ui.label(row_label).classes('text-center font-bold text-grey-5 text-md').style('width: 40px;')
                        
                        for col in display_cols:
                            seat_id = f"{row_label}-{col}"
                            is_blocked = seat_id in blocked_seats
                            guest = allocated_map.get(seat_id)
                            sec_info = get_seat_sector_info(col, r)
                            
                            # Se a fileira estiver fora da quantidade de fileiras deste setor específico
                            if not sec_info['active']:
                                ui.label('').style(f'width: {seat_w}; height: {seat_h};')
                                continue

                            if is_blocked:
                                if state.edit_mode == "layout":
                                    with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105').style(
                                        f'width: {seat_w}; height: {seat_h}; border: 1px dashed rgba(255,255,255,0.15); border-radius: 4px; background: rgba(255,255,255,0.02); gap: 0;'
                                    ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                        ui.label(seat_id).classes('text-[8px] text-grey-5 font-mono')
                                        ui.label('CORREDOR').classes('text-[7px] text-grey-6 font-bold')
                                else:
                                    ui.label('').style(f'width: {seat_w}; height: {seat_h};')
                            else:
                                if guest:
                                    display_name = f"{guest.get('posto_graduacao') or ''} {guest['nome']}".strip()
                                    if len(display_name) > 12:
                                        display_name = display_name[:10] + '..'
                                        
                                    is_vip = guest.get('categoria') == 'VIP'
                                    is_acomp = bool(guest.get('convidado_principal_id'))
                                    
                                    border_c = THEME['primary'] if is_vip else ('#ffb74d' if is_acomp else THEME['accent'])
                                    bg_c = 'rgba(0, 229, 255, 0.25)' if is_vip else ('rgba(255, 183, 77, 0.22)' if is_acomp else 'rgba(0, 162, 255, 0.25)')
                                    text_c = THEME['primary'] if is_vip else ('#ffb74d' if is_acomp else THEME['accent'])
                                    
                                    with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                        f'width: {seat_w}; height: {seat_h}; border-radius: 4px; border-color: {border_c} !important; background: {bg_c}; gap: 0;'
                                    ).on('click', lambda s=seat_id, g=guest: open_seat_actions_dialog(s, g, convidados, current_event['id'])):
                                        ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                        ui.label(display_name).classes(f'font-bold text-center leading-none text-white overflow-hidden w-full').style(f'font-size: {font_name};')
                                        
                                        category_label = 'ACOMP' if is_acomp else str(guest.get('categoria', 'Geral')).upper()
                                        if len(category_label) > 10:
                                            category_label = category_label[:8] + '..'
                                        ui.label(category_label).classes(f'text-center leading-none').style(f'color: {text_c}; font-weight: bold; font-size: {font_sub};')
                                else:
                                    if state.edit_mode == "layout":
                                        with ui.column().classes('items-center justify-center cursor-pointer transition-all hover:scale-105 border').style(
                                            f'width: {seat_w}; height: {seat_h}; border-radius: 4px; border-color: rgba(255,255,255,0.15) !important; background: #1b2535; gap: 0;'
                                        ).on('click', lambda s=seat_id: toggle_seat_block(s, current_event, layout)):
                                            ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono')
                                            ui.label('BLOQUEAR').classes('text-[7px] text-grey-5 font-bold')
                                    else:
                                        with ui.column().classes('items-center justify-between q-pa-xs cursor-pointer transition-all hover:scale-105 border').style(
                                            f'width: {seat_w}; height: {seat_h}; border-radius: 4px; border-color: {sec_info["border"]} !important; background: {sec_info["bg"]}; gap: 0;'
                                        ).on('click', lambda s=seat_id: open_allocate_seat_dialog(s, convidados, current_event['id'])):
                                            ui.label(seat_id).classes('text-[8px] text-grey-4 font-mono leading-none')
                                            ui.label('LIVRE').classes('font-bold text-center leading-none').style(f'color: {sec_info["text"]}; font-size: {font_name};')
                                            ui.label('(vazio)').classes('text-grey-4 text-center leading-none').style(f'font-size: {font_sub};')

                ref_bottom = layout.get('ref_bottom', 'ENTRADA / FACHADA')
                if ref_bottom:
                    with ui.row().classes('w-full justify-center q-mt-sm q-mb-sm'):
                        ui.label(f"▼ {ref_bottom.upper()} ▼").classes('text-[10px] font-black tracking-widest text-cyan px-4 py-1 rounded-full border border-cyan-500/20 bg-cyan-500/5')

            # Faixa Informativa de Legenda e Dimensões do Auditório na Base
            with ui.row().classes('w-full justify-between items-center wrap-mobile gap-2 q-mt-sm bg-black/40 q-pa-xs px-3 rounded-lg border border-cyan-500/20'):
                with ui.row().classes('items-center gap-3'):
                    ui.label(f"🏛️ Dimensão Total: {rows_count} Fileiras × {cols_count} Colunas").classes('text-xs text-cyan font-bold')
                    ui.separator().props('vertical').classes('q-my-none').style('height: 16px; border-color: rgba(255,255,255,0.1);')
                    ui.label('💡 Clique nos lugares vagos para alocar convidados. A estrutura de setores é gerida no menu "Editar Evento".').classes('text-[11px] text-grey-4 italic')

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

    def create_event(nome, data, local, layout_tipo, rows, cols, ref_top, ref_bottom, custom_sectors=None):
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
                'blocked_seats': [],
                'sectors': custom_sectors or []
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
            r = max(1, min(50, layout.get('rows', 5) + row_delta))
            c = max(1, min(100, layout.get('cols', 8) + col_delta))
            
            layout['rows'] = r
            layout['cols'] = c
            
            # Se colunas foram alteradas, reajusta o limite do último setor para cobrir o grid
            sectors = layout.get('sectors', [])
            if sectors and col_delta != 0:
                sectors[-1]['end_col'] = max(sectors[-1]['start_col'], c)
                layout['sectors'] = sectors

            new_layout_json = json.dumps(layout)
            try:
                db.table('jade_eventos').update({'layout_json': new_layout_json}).eq('id', event['id']).execute()
                ui.notify(f"Grid ajustado para {r} fileiras × {c} colunas.", color='success')
                render_content.refresh()
            except Exception as e:
                ui.notify(f"Erro ao alterar dimensões do grid: {e}", color='red')

    # --- MODAIS E DIÁLOGOS DE GERENCIAMENTO DE SETORES E EVENTOS ---
    def open_create_event_dialog():
        with ui.dialog() as diag, ui.card().classes('q-pa-lg').style('min-width: 520px; max-width: 90vw;'):
            ui.label('📅 Novo Evento com Gestão de Setores').classes('text-md font-bold text-cyan cyber-title q-mb-xs')
            ui.label('Cadastre a solenidade e configure as dimensões e nomes dos setores').classes('text-xs text-grey-4 q-mb-md')
            
            nome = ui.input('Nome do Evento / Solenidade').props('dark outlined dense w-full')
            data = ui.input('Data do Evento').props('type=date dark outlined dense w-full')
            local = ui.input('Local (ex: Auditório Principal)').props('dark outlined dense w-full')
            
            with ui.row().classes('w-full gap-2'):
                ref_top = ui.input('Referência Superior', value='PALCO PRINCIPAL').props('dark outlined dense').classes('col')
                ref_bottom = ui.input('Referência Inferior', value='ENTRADA / FACHADA').props('dark outlined dense').classes('col')
            
            with ui.row().classes('w-full gap-2'):
                rows = ui.number('Linhas (Grid Total)', value=6, min=1, max=25, step=1).props('dark outlined dense').classes('col')
                cols = ui.number('Colunas (Grid Total)', value=12, min=1, max=30, step=1).props('dark outlined dense').classes('col')
                
            layout_tipo = ui.select(
                options={'auditorio': 'Auditório (Fileiras em Setores)', 'mesas': 'Mesas Redondas'}, 
                value='auditorio'
            ).props('dark outlined dense w-full')
            
            ui.separator().classes('q-my-sm')
            ui.label('⚙️ Nomes dos Setores Customizados (Opcional):').classes('text-xs text-amber font-bold')
            sec1 = ui.input('Setor 1 (Esquerda/Alpha)', value='SETOR ALPHA (ESQUERDA)').props('dark outlined dense w-full')
            sec2 = ui.input('Setor 2 (Centro/Nobre)', value='SETOR NOBRE (CENTRO)').props('dark outlined dense w-full')
            sec3 = ui.input('Setor 3 (Direita/Bravo)', value='SETOR BRAVO (DIREITA)').props('dark outlined dense w-full')

            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
                def criar_evento_custom():
                    c_total = int(cols.value)
                    custom_sectors = [
                        {'name': sec1.value.strip().upper(), 'start_col': 1, 'end_col': max(1, c_total // 3)},
                        {'name': sec2.value.strip().upper(), 'start_col': max(1, c_total // 3) + 1, 'end_col': max(1, (c_total * 2) // 3)},
                        {'name': sec3.value.strip().upper(), 'start_col': max(1, (c_total * 2) // 3) + 1, 'end_col': c_total}
                    ]
                    create_event(nome.value, data.value, local.value, layout_tipo.value, rows.value, cols.value, ref_top.value, ref_bottom.value, custom_sectors)
                    diag.close()

                ui.button('Criar Evento', on_click=criar_evento_custom).props('unelevated color=primary text-color=black dense bold')
                
        diag.open()

    def open_edit_event_dialog(event, layout):
        sectors_list = list(layout.get('sectors', []))
        c_total = layout.get('cols', 12)

        if not sectors_list:
            sectors_list = [
                {'name': 'SETOR ALPHA (ESQUERDA)', 'start_col': 1, 'end_col': max(1, c_total // 3)},
                {'name': 'SETOR NOBRE (CENTRO)', 'start_col': max(1, c_total // 3) + 1, 'end_col': max(1, (c_total * 2) // 3)},
                {'name': 'SETOR BRAVO (DIREITA)', 'start_col': max(1, (c_total * 2) // 3) + 1, 'end_col': c_total}
            ]

        with ui.dialog() as diag, ui.card().classes('q-pa-lg').style('min-width: 650px; max-width: 95vw; max-height: 88vh; overflow-y: auto;'):
            ui.label('📝 Configuração do Layout e Gestão de Setores').classes('text-md font-bold text-cyan cyber-title q-mb-xs')
            ui.label('Adicione, exclua ou renomeie setores e configure os limites de colunas').classes('text-xs text-grey-4 q-mb-md')
            
            nome = ui.input('Nome do Evento / Solenidade', value=event['nome']).props('dark outlined dense w-full')
            data = ui.input('Data do Evento', value=event['data_evento']).props('type=date dark outlined dense w-full')
            local = ui.input('Local', value=event.get('local') or '').props('dark outlined dense w-full')
            
            with ui.row().classes('w-full gap-2'):
                ref_top = ui.input('Referência Superior', value=layout.get('ref_top', 'PALCO PRINCIPAL')).props('dark outlined dense').classes('col')
                ref_bottom = ui.input('Referência Inferior', value=layout.get('ref_bottom', 'ENTRADA / FACHADA')).props('dark outlined dense').classes('col')
            
            with ui.row().classes('w-full gap-2 q-mt-xs'):
                rows_input = ui.number('Fileiras Totais (Linhas)', value=layout.get('rows', 5), min=1, max=50, step=1).props('dark outlined dense').classes('col')
                cols_input = ui.number('Colunas Totais (Largura)', value=layout.get('cols', 12), min=1, max=100, step=1).props('dark outlined dense').classes('col')

            # Prepara setores para edição exibindo a Quantidade de Fileiras e Colunas individuais
            for s in sectors_list:
                width = (s.get('end_col', 1) - s.get('start_col', 1)) + 1
                s['cols_count'] = max(1, width)
                if 'rows_count' not in s:
                    s['rows_count'] = layout.get('rows', 5)

            with ui.row().classes('w-full justify-between items-center q-mb-xs'):
                ui.label('📍 SETORES DO AUDITÓRIO (Fileiras e Colunas Individuais)').classes('text-xs text-amber font-bold')
                
                def add_sector_item():
                    num_sectors = len(sectors_list)
                    default_r = int(rows_input.value or 5)
                    sectors_list.append({
                        'name': f"SETOR {num_sectors + 1}",
                        'rows_count': default_r,
                        'cols_count': 12
                    })
                    render_sectors_editor.refresh()

                ui.button('➕ Adicionar Setor', icon='add', on_click=add_sector_item).props('unelevated color=amber text-color=black dense').classes('text-xs')

            # Renderizador dinâmico de campos de setores com botão de exclusão e cálculo de quantitativos
            sector_inputs = []

            @ui.refreshable
            def render_sectors_editor():
                sector_inputs.clear()
                total_seats_calc = 0

                with ui.column().classes('w-full gap-2 q-my-xs'):
                    for idx, sec in enumerate(sectors_list):
                        r_val = int(sec.get('rows_count', int(rows_input.value or 5)))
                        c_val = int(sec.get('cols_count', 12))
                        sec_seats = r_val * c_val
                        total_seats_calc += sec_seats

                        with ui.card().classes('w-full q-pa-xs px-3 bg-black/40 border border-cyan-500/20 rounded-lg'):
                            with ui.row().classes('w-full items-center justify-between gap-2'):
                                s_name = ui.input(f'Nome do Setor {idx+1}', value=sec['name']).props('dark outlined dense').classes('col')
                                s_rows = ui.number('Fileiras', value=r_val, min=1, max=50).props('dark outlined dense').style('width: 90px;')
                                s_cols = ui.number('Colunas', value=c_val, min=1, max=100).props('dark outlined dense').style('width: 90px;')
                                
                                # Badge com o quantitativo de assentos do setor (Fileiras x Colunas)
                                with ui.column().classes('items-center gap-0').style('min-width: 100px;'):
                                    ui.label(f"🪑 {sec_seats} lugares").classes('text-xs font-bold text-cyan')
                                    ui.label(f"({r_val} fil × {c_val} col)").classes('text-[9px] text-grey-4 font-mono')

                                def remove_sector(i=idx):
                                    if len(sectors_list) > 1:
                                        sectors_list.pop(i)
                                        render_sectors_editor.refresh()
                                    else:
                                        ui.notify('O evento precisa de pelo menos 1 setor.', color='warning')

                                ui.button(icon='delete', on_click=remove_sector).props('unelevated color=danger dense flat round').classes('text-xs')
                                sector_inputs.append((s_name, s_rows, s_cols))

                    # Banner de Quantitativo Geral de Assentos do Evento
                    with ui.card().classes('w-full q-pa-sm bg-cyan-950/40 border border-cyan-500/40 rounded-lg q-mt-xs'):
                        with ui.row().classes('w-full justify-between items-center px-2'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('event_seat', color='cyan', size='sm')
                                ui.label('QUANTITATIVO TOTAL DO AUDITÓRIO:').classes('text-xs font-bold text-white')
                            ui.badge(f"{total_seats_calc} ASSENTOS TOTAIS").props('color=cyan text-color=black bold').classes('text-xs q-px-sm')

            # Atualiza os cálculos ao alterar fileiras gerais
            rows_input.on('change', render_sectors_editor.refresh)
            render_sectors_editor()

            with ui.row().classes('w-full justify-end q-mt-md gap-2'):
                ui.button('Cancelar', on_click=diag.close).props('unelevated color=grey-8 dense')
                
                def salvar_alteracoes():
                    db = get_service_db_connection() or get_db_connection()
                    if db:
                        layout['ref_top'] = ref_top.value
                        layout['ref_bottom'] = ref_bottom.value
                        
                        # Converte a quantidade simples de fileiras e colunas de cada setor em posições sequenciais automáticas
                        new_sectors = []
                        current_col = 1
                        max_grid_rows = 1

                        for inp_name, inp_rows, inp_cols in sector_inputs:
                            if inp_name.value and inp_name.value.strip():
                                q_rows = max(1, int(inp_rows.value or 1))
                                q_cols = max(1, int(inp_cols.value or 1))
                                
                                if q_rows > max_grid_rows:
                                    max_grid_rows = q_rows

                                start_val = current_col
                                end_val = current_col + q_cols - 1
                                new_sectors.append({
                                    'name': inp_name.value.strip().upper(),
                                    'rows_count': q_rows,
                                    'start_col': start_val,
                                    'end_col': end_val
                                })
                                current_col = end_val + 1
                                
                        layout['sectors'] = new_sectors
                        layout['rows'] = max_grid_rows
                        layout['cols'] = current_col - 1

                        try:
                            updated_json = json.dumps(layout)
                            db.table('jade_eventos').update({
                                'nome': nome.value.upper(),
                                'data_evento': data.value,
                                'local': local.value or '',
                                'layout_json': updated_json
                            }).eq('id', event['id']).execute()
                            
                            # Atualiza atributos do objeto em memória
                            event['nome'] = nome.value.upper()
                            event['data_evento'] = data.value
                            event['local'] = local.value or ''
                            event['layout_json'] = updated_json
                            
                            # Reseta o seletor de setor e recarrega
                            state.selected_sector = 'Todos'
                            
                            ui.notify('Layout e Setores atualizados com sucesso!', color='success')
                            diag.close()
                            render_content.refresh()
                        except Exception as e:
                            ui.notify(f"Erro ao salvar: {e}", color='red')
                            
                ui.button('Salvar Alterações', on_click=salvar_alteracoes).props('unelevated color=primary text-color=black dense bold')
                
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

    # ═══════════════════════════════════════════════════════════════
    # FASE 2: DIALOG DE CONFIRMAÇÃO DE PRESENÇAS EM MASSA
    # ═══════════════════════════════════════════════════════════════
    def open_mass_confirmation_dialog(event, convidados):
        """Dialog para confirmar/recusar presenças em massa, com checkboxes por categoria."""
        
        # Estado local do dialog
        selected_ids = set()
        filter_status = {'value': 'todos'}
        
        with ui.dialog().classes('q-dialog--maximized') as diag, ui.card().classes('w-full').style(
            f'background: {THEME["bg_panel"]}; max-width: 1200px; max-height: 95vh;'
        ):
            # Cabeçalho
            with ui.row().classes('w-full items-center justify-between q-mb-sm'):
                with ui.column().classes('gap-0'):
                    ui.label('✅ CONFIRMAÇÃO DE PRESENÇAS EM MASSA').classes('text-lg font-bold text-cyan')
                    ui.label(f'Evento: {event.get("nome", "N/I")} — {event.get("data_evento", "")}').classes('text-xs text-grey-4')
                ui.button(icon='close', on_click=diag.close).props('flat round dense text-color=grey')

            # Agrupar convidados por categoria (excluir acompanhantes — eles seguem o principal)
            main_guests = [c for c in convidados if not c.get('convidado_principal_id')]
            categories = {}
            for c in main_guests:
                cat = c.get('categoria', 'Sem Categoria') or 'Sem Categoria'
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(c)

            # Contadores resumo
            total = len(main_guests)
            count_conf = sum(1 for c in main_guests if c.get('status_confirmacao') == 'confirmado')
            count_ref = sum(1 for c in main_guests if c.get('status_confirmacao') == 'recusado')
            count_prov = sum(1 for c in main_guests if c.get('status_confirmacao') == 'provavel')
            count_pend = total - count_conf - count_ref - count_prov

            # Barra de resumo
            with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg q-mb-sm').style('background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);'):
                with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                    with ui.row().classes('gap-2 wrap'):
                        ui.badge(f'📋 Total: {total}').props('color=grey-7 text-color=white').classes('text-xs')
                        ui.badge(f'✅ Confirmados: {count_conf}').props('color=green text-color=white').classes('text-xs')
                        ui.badge(f'🟡 Prováveis: {count_prov}').props('color=amber text-color=black').classes('text-xs')
                        ui.badge(f'❓ Pendentes: {count_pend}').props('color=blue-grey text-color=white').classes('text-xs')
                        ui.badge(f'❌ Recusados: {count_ref}').props('color=red text-color=white').classes('text-xs')

            # Filtro de status
            @ui.refreshable
            def render_filter_bar():
                with ui.row().classes('w-full items-center gap-2 q-mb-sm wrap'):
                    ui.label('Filtrar:').classes('text-xs text-grey-4 font-bold')
                    filter_options = [
                        ('todos', '🌐 Todos', 'grey-7'),
                        ('confirmado', '✅ Confirmados', 'green'),
                        ('pendente', '❓ Pendentes', 'blue-grey'),
                        ('provavel', '🟡 Prováveis', 'amber'),
                        ('recusado', '❌ Recusados', 'red'),
                    ]
                    for fval, flabel, fcol in filter_options:
                        is_active = filter_status['value'] == fval
                        def make_filter_click(v=fval):
                            def _click():
                                filter_status['value'] = v
                                render_filter_bar.refresh()
                                render_guest_list.refresh()
                            return _click
                        ui.button(flabel, on_click=make_filter_click()).props(
                            f'dense {"unelevated" if is_active else "outline"} color={fcol} {"text-color=white" if is_active else ""}'
                        ).classes('text-[10px] q-px-xs')
                    
                    ui.separator().props('vertical').classes('q-mx-xs')
                    ui.label(f'🔲 {len(selected_ids)} selecionados').classes('text-[10px] text-grey-5 font-bold')

            render_filter_bar()

            # Lista de convidados agrupados por categoria
            @ui.refreshable
            def render_guest_list():
                with ui.scroll_area().classes('w-full').style('max-height: 55vh;'):
                    for cat_name, cat_guests in sorted(categories.items()):
                        # Filtrar conforme o filtro ativo
                        fval = filter_status['value']
                        if fval == 'todos':
                            filtered = cat_guests
                        elif fval == 'pendente':
                            filtered = [c for c in cat_guests if c.get('status_confirmacao', 'pendente') not in ('confirmado', 'recusado', 'provavel')]
                        else:
                            filtered = [c for c in cat_guests if c.get('status_confirmacao') == fval]
                        
                        if not filtered:
                            continue

                        with ui.expansion(
                            f'📁 {cat_name} ({len(filtered)} convidados)',
                            value=True
                        ).classes('w-full q-mb-xs text-white font-bold').style(
                            'background: rgba(0,60,80,0.3); border-radius: 8px;'
                        ):
                            # Botão selecionar todo o bloco
                            with ui.row().classes('w-full items-center justify-between q-mb-xs q-px-sm'):
                                def make_select_all(guests=filtered):
                                    def _click():
                                        all_ids = {str(g['id']) for g in guests}
                                        if all_ids.issubset(selected_ids):
                                            selected_ids.difference_update(all_ids)
                                        else:
                                            selected_ids.update(all_ids)
                                        render_guest_list.refresh()
                                        render_filter_bar.refresh()
                                    return _click
                                
                                all_selected = all(str(g['id']) in selected_ids for g in filtered)
                                ui.button(
                                    f'{"☑ Desmarcar" if all_selected else "☐ Selecionar"} Todo o Bloco',
                                    on_click=make_select_all()
                                ).props(f'dense flat text-color={"cyan" if not all_selected else "amber"}').classes('text-[10px]')

                            for g in filtered:
                                g_id = str(g['id'])
                                nome = g.get('nome', 'N/I')
                                posto = g.get('posto_graduacao', '') or ''
                                cargo = g.get('cargo_funcao', '') or ''
                                st = g.get('status_confirmacao', 'pendente') or 'pendente'
                                max_ac = g.get('max_acompanhantes', 0) or 0
                                
                                st_emoji = {'confirmado': '✅', 'recusado': '❌', 'provavel': '🟡', 'pendente': '❓'}.get(st, '❓')
                                st_color = {'confirmado': 'rgba(0,200,80,0.15)', 'recusado': 'rgba(200,0,0,0.15)', 'provavel': 'rgba(255,200,0,0.15)'}.get(st, 'rgba(255,255,255,0.03)')
                                
                                is_checked = g_id in selected_ids

                                with ui.row().classes('w-full items-center q-py-xs q-px-sm rounded-lg gap-2').style(
                                    f'background: {st_color}; border-bottom: 1px solid rgba(255,255,255,0.05);'
                                ):
                                    def make_toggle(gid=g_id):
                                        def _toggle(e):
                                            if e.value:
                                                selected_ids.add(gid)
                                            else:
                                                selected_ids.discard(gid)
                                            render_filter_bar.refresh()
                                        return _toggle

                                    ui.checkbox('', value=is_checked, on_change=make_toggle()).props('dense dark')
                                    ui.label(f'{st_emoji}').classes('text-sm')
                                    ui.label(f'{posto}').classes('text-[10px] text-amber font-bold').style('min-width: 60px;')
                                    ui.label(f'{nome}').classes('text-xs text-white font-bold flex-grow')
                                    if cargo:
                                        ui.label(f'{cargo[:40]}').classes('text-[9px] text-grey-5 truncate').style('max-width: 200px;')
                                    if max_ac > 0:
                                        ui.badge(f'+{max_ac} acomp.').props('color=blue-grey text-color=white').classes('text-[9px]')

            render_guest_list()

            # Barra de ações
            ui.separator().classes('q-my-sm')
            with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                with ui.row().classes('gap-2 wrap'):
                    async def batch_update_status(new_status):
                        if not selected_ids:
                            ui.notify('⚠️ Nenhum convidado selecionado.', color='warning')
                            return
                        _db = get_service_db_connection() or get_db_connection()
                        if not _db:
                            ui.notify('❌ Banco indisponível.', color='negative')
                            return
                        
                        # Determinar status_placa com base no status de confirmação
                        if new_status == 'confirmado':
                            new_placa = 'pendente'  # Placa precisa ser impressa
                        elif new_status == 'provavel':
                            new_placa = 'pendente'  # Tier 2 — preventivo
                        elif new_status == 'recusado':
                            new_placa = 'nao_necessaria'
                        else:
                            new_placa = 'nao_necessaria'
                        
                        count_updated = 0
                        for gid in list(selected_ids):
                            try:
                                _db.table('jade_convidados').update({
                                    'status_confirmacao': new_status,
                                    'status_placa': new_placa
                                }).eq('id', int(gid)).execute()
                                count_updated += 1
                            except Exception:
                                # Fallback: coluna status_placa pode não existir ainda
                                try:
                                    _db.table('jade_convidados').update({
                                        'status_confirmacao': new_status
                                    }).eq('id', int(gid)).execute()
                                    count_updated += 1
                                except Exception as e2:
                                    print(f"[BATCH UPDATE ERR] {e2}")
                        
                        status_labels = {'confirmado': 'CONFIRMADOS', 'recusado': 'RECUSADOS', 'provavel': 'PROVÁVEIS', 'pendente': 'PENDENTES'}
                        ui.notify(f'✅ {count_updated} convidados marcados como {status_labels.get(new_status, new_status)}!', color='positive')
                        
                        # Notificar via Telegram se gerou novas placas pendentes
                        if new_status in ('confirmado', 'provavel') and count_updated > 0:
                            try:
                                from notifications_manager import notify_jade_production
                                notify_jade_production(event.get('nome', 'Solenidade'), count_updated, count_updated)
                            except Exception as n_err:
                                print(f"[JADE NOTIFY ERR] {n_err}")
                                
                        selected_ids.clear()
                        diag.close()
                        render_content.refresh()

                    ui.button('✅ Confirmar Selecionados', icon='check_circle', on_click=lambda: batch_update_status('confirmado')).props('unelevated color=green text-color=white dense').classes('text-xs q-px-sm')
                    ui.button('🟡 Marcar Prováveis (Tier 2)', icon='trending_up', on_click=lambda: batch_update_status('provavel')).props('unelevated color=amber text-color=black dense').classes('text-xs q-px-sm')
                    ui.button('❌ Recusar Selecionados', icon='cancel', on_click=lambda: batch_update_status('recusado')).props('unelevated color=red text-color=white dense').classes('text-xs q-px-sm')
                    ui.button('❓ Voltar a Pendente', icon='pending', on_click=lambda: batch_update_status('pendente')).props('outline color=grey dense').classes('text-xs q-px-sm')

                ui.button('Fechar', icon='close', on_click=diag.close).props('unelevated color=grey-8 dense').classes('text-xs')

        diag.open()

    # ═══════════════════════════════════════════════════════════════
    # FASE 3: IMPORTADOR INTELIGENTE DE EXCEL COM LEITURA DE CORES
    # ═══════════════════════════════════════════════════════════════
    def open_smart_excel_import_dialog(event):
        """Dialog com upload de arquivo .xlsx para importação inteligente de convidados com leitura de cores."""
        with ui.dialog() as diag, ui.card().classes('w-full').style(
            f'background: {THEME["bg_panel"]}; max-width: 650px;'
        ):
            ui.label('📥 IMPORTADOR INTELIGENTE JADE (EXCEL COM CORES)').classes('text-md font-bold text-cyan')
            ui.label(f'Solenidade Destino: {event.get("nome", "N/I")}').classes('text-xs text-grey-4 q-mb-sm')
            
            ui.markdown(
                "**Como funciona a importação inteligente:**\n"
                "• **Suporta o modelo oficial:** Planilhas `.xlsx` com blocos (ex: `LISTA DE CONVITE.xlsx`).\n"
                "• **Leitura de Cores:** Células **Verdes** na coluna *Confirmado* viram **CONFIRMADO** (placa na fila de produção). Células **Vermelhas** viram **RECUSADO**.\n"
                "• **Anti-duplicação:** Se a autoridade já existir na solenidade (mesmo Nome + Posto), os dados e acompanhantes são **atualizados sem duplicar**.\n"
                "• **Categorias:** Os blocos (Almirantado, CMGs FN, Civis, etc.) são identificados automaticamente."
            ).classes('text-xs text-grey-3 bg-black/30 q-pa-sm rounded-lg border border-white/10')
            
            log_container = ui.column().classes('w-full q-my-sm')

            async def handle_upload(e):
                file_bytes = e.content.read()
                if not file_bytes:
                    ui.notify('❌ Arquivo vazio.', color='negative')
                    return
                
                try:
                    import io
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
                    sheet = wb.active
                    
                    db = get_service_db_connection() or get_db_connection()
                    if not db:
                        ui.notify('❌ Banco de dados indisponível.', color='negative')
                        return
                    
                    event_id = event['id']
                    res_exist = db.table('jade_convidados').select('*').eq('evento_id', event_id).execute()
                    existing_list = res_exist.data if res_exist.data else []
                    
                    existing_map = {}
                    for item in existing_list:
                        if not item.get('convidado_principal_id'):
                            key = f"{(item.get('nome') or '').strip().upper()}|{(item.get('posto_graduacao') or '').strip().upper()}"
                            existing_map[key] = item

                    current_category = "Geral"
                    count_inserted = 0
                    count_updated = 0
                    count_conf = 0
                    count_rec = 0
                    count_pend = 0

                    for r in range(1, sheet.max_row + 1):
                        row_cells = [sheet.cell(row=r, column=c) for c in range(1, sheet.max_column + 1)]
                        row_vals = [c.value for c in row_cells]

                        if not any(v is not None for v in row_vals):
                            continue

                        c0 = str(row_vals[0]).strip() if len(row_vals) > 0 and row_vals[0] is not None else ""
                        c1 = str(row_vals[1]).strip() if len(row_vals) > 1 and row_vals[1] is not None else ""
                        c2 = str(row_vals[2]).strip() if len(row_vals) > 2 and row_vals[2] is not None else ""

                        if c0.upper() in ('QTD', 'QUANTIDADE') or c1.upper() in ('POSTO', 'GRAU'):
                            continue

                        if c0 and not c0.isdigit() and c0.upper() not in ('QTD', 'QUANTIDADE'):
                            current_category = c0
                            continue

                        nome = c2
                        if not nome or nome.upper() in ('NOME', 'CONVITE'):
                            continue

                        posto = c1
                        cargo = str(row_vals[3]).strip() if len(row_vals) > 3 and row_vals[3] is not None else ""
                        conf_val = row_vals[5] if len(row_vals) > 5 else None
                        conjuge_val = row_vals[6] if len(row_vals) > 6 else None

                        conf_fill = ""
                        if len(row_cells) > 5 and row_cells[5].fill and row_cells[5].fill.start_color:
                            conf_fill = str(row_cells[5].fill.start_color.rgb or "")

                        status_conf = "pendente"
                        status_placa = "nao_necessaria"

                        if any(g in conf_fill for g in ('00B050', '92D050', '00FF00')):
                            status_conf = "confirmado"
                            status_placa = "pendente"
                            count_conf += 1
                        elif any(rc in conf_fill for rc in ('FF0000', 'FA1717', 'C00000', 'FF5555')):
                            status_conf = "recusado"
                            status_placa = "nao_necessaria"
                            count_rec += 1
                        else:
                            if conf_val in (1, 2, '1', '2', 'SIM', 'Sim', 'sim', 'CONFIRMADO'):
                                status_conf = "confirmado"
                                status_placa = "pendente"
                                count_conf += 1
                            else:
                                count_pend += 1

                        max_acomp = 0
                        if isinstance(conf_val, int) and conf_val > 1:
                            max_acomp = conf_val - 1
                        elif str(conf_val).strip().isdigit() and int(str(conf_val).strip()) > 1:
                            max_acomp = int(str(conf_val).strip()) - 1
                        elif conjuge_val in ('E', '1', 1) or (isinstance(conjuge_val, str) and len(conjuge_val) > 2):
                            max_acomp = 1

                        key = f"{nome.strip().upper()}|{posto.strip().upper()}"
                        
                        conv_data = {
                            'evento_id': event_id,
                            'nome': nome,
                            'posto_graduacao': posto,
                            'cargo_funcao': cargo,
                            'categoria': current_category,
                            'status_confirmacao': status_conf,
                            'max_acompanhantes': max_acomp,
                        }
                        
                        conv_data_with_placa = dict(conv_data)
                        conv_data_with_placa['status_placa'] = status_placa

                        if key in existing_map:
                            existing_id = existing_map[key]['id']
                            try:
                                db.table('jade_convidados').update(conv_data_with_placa).eq('id', existing_id).execute()
                            except Exception:
                                db.table('jade_convidados').update(conv_data).eq('id', existing_id).execute()
                            
                            sync_companions(existing_id, nome, max_acomp, event_id, current_category)
                            count_updated += 1
                        else:
                            res_ins = None
                            try:
                                res_ins = db.table('jade_convidados').insert(conv_data_with_placa).execute()
                            except Exception:
                                res_ins = db.table('jade_convidados').insert(conv_data).execute()
                            
                            if res_ins and res_ins.data:
                                new_id = res_ins.data[0]['id']
                                sync_companions(new_id, nome, max_acomp, event_id, current_category)
                            count_inserted += 1

                    ui.notify(f'✅ Importação concluída! {count_inserted} novos, {count_updated} atualizados.', color='positive')
                    
                    if count_conf > 0:
                        try:
                            from notifications_manager import notify_jade_production
                            notify_jade_production(event.get('nome', 'Solenidade'), count_conf, count_conf)
                        except Exception as n_err:
                            print(f"[JADE NOTIFY ERR] {n_err}")

                    log_container.clear()
                    with log_container:
                        with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style('background: rgba(0,255,150,0.1); border: 1px solid rgba(0,255,150,0.3);'):
                            ui.label('📊 RELATÓRIO DE IMPORTAÇÃO CONCLUÍDA').classes('text-xs font-bold text-green')
                            ui.label(f'• Registros Processados: {count_inserted + count_updated}').classes('text-xs text-white')
                            ui.label(f'• 🆕 Novos Convidados Inseridos: {count_inserted}').classes('text-xs text-green font-bold')
                            ui.label(f'• 🔄 Atualizados (Merge Anti-Duplicação): {count_updated}').classes('text-xs text-cyan font-bold')
                            ui.label(f'• ✅ Confirmados (Placa na Fila de Produção): {count_conf}').classes('text-xs text-amber font-bold')
                            ui.label(f'• ❌ Recusados: {count_rec}').classes('text-xs text-red')
                            ui.label(f'• ❓ Pendentes: {count_pend}').classes('text-xs text-grey-4')
                    
                    render_content.refresh()

                except Exception as ex:
                    print(f"[SMART IMPORT ERR] {ex}")
                    ui.notify(f'❌ Erro ao processar planilha: {ex}', color='negative')

            ui.upload(on_upload=handle_upload, auto_upload=True).props('accept=.xlsx dark').classes('w-full q-my-sm')
            
            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('Fechar', icon='close', on_click=diag.close).props('unelevated color=grey-8 dense').classes('text-xs')

        diag.open()

    # ═══════════════════════════════════════════════════════════════
    # FASE 5: CADASTRO MESTRE DE AUTORIDADES (REUTILIZÁVEL)
    # ═══════════════════════════════════════════════════════════════
    def open_master_authorities_dialog(event):
        """Dialog para gerenciar e importar autoridades da base mestre permanente."""
        with ui.dialog().classes('q-dialog--maximized') as diag, ui.card().classes('w-full').style(
            f'background: {THEME["bg_panel"]}; max-width: 1100px; max-height: 90vh;'
        ):
            with ui.row().classes('w-full items-center justify-between q-mb-sm'):
                with ui.column().classes('gap-0'):
                    ui.label('🏛️ CADASTRO MESTRE DE AUTORIDADES').classes('text-lg font-bold text-indigo')
                    ui.label(f'Base permanente de convidados | Solenidade Ativa: {event.get("nome", "N/I")}').classes('text-xs text-grey-4')
                ui.button(icon='close', on_click=diag.close).props('flat round dense text-color=grey')

            db = get_service_db_connection() or get_db_connection()
            master_list = []
            if db:
                try:
                    res_m = db.table('jade_autoridades_base').select('*').order('categoria', desc=False).execute()
                    master_list = res_m.data if res_m.data else []
                except Exception as e_m:
                    print(f"[MASTER FETCH ERR] {e_m}")

            # Se a base mestre estiver vazia, sugerir sincronizar os convidados do evento ativo
            with ui.row().classes('w-full items-center justify-between bg-black/30 q-pa-sm rounded-lg border border-white/10 q-mb-md wrap gap-2'):
                ui.label(f'📊 {len(master_list)} autoridades cadastradas na Base Mestre').classes('text-xs font-bold text-white')
                
                with ui.row().classes('gap-2 wrap'):
                    async def save_current_to_master():
                        if not db:
                            return
                        res_c = db.table('jade_convidados').select('*').eq('evento_id', event['id']).execute()
                        convs = res_c.data if res_c.data else []
                        if not convs:
                            ui.notify('⚠️ Nenhum convidado no evento ativo para exportar.', color='warning')
                            return
                        
                        count_added = 0
                        for c in convs:
                            if c.get('convidado_principal_id'):
                                continue
                            nome = (c.get('nome') or '').strip()
                            posto = (c.get('posto_graduacao') or '').strip()
                            cat = c.get('categoria', 'Geral')
                            cargo = c.get('cargo_funcao', '')
                            
                            res_chk = db.table('jade_autoridades_base').select('id').eq('nome', nome).eq('posto_graduacao', posto).execute()
                            if not res_chk.data:
                                try:
                                    db.table('jade_autoridades_base').insert({
                                        'nome': nome,
                                        'posto_graduacao': posto,
                                        'cargo_funcao': cargo,
                                        'categoria': cat,
                                        'max_acompanhantes': c.get('max_acompanhantes', 0)
                                    }).execute()
                                    count_added += 1
                                except Exception as err_m:
                                    print(f"[SAVE MASTER ERR] {err_m}")
                        
                        ui.notify(f'✅ {count_added} novas autoridades salvas no Cadastro Mestre!', color='positive')
                        diag.close()
                        render_content.refresh()

                    ui.button('💾 Salvar Convidados Deste Evento no Mestre', icon='save', on_click=save_current_to_master).props('unelevated color=indigo dense').classes('text-xs')

            categories = {}
            for m in master_list:
                cat = m.get('categoria', 'Geral') or 'Geral'
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(m)

            selected_master_ids = set()

            with ui.scroll_area().classes('w-full').style('max-height: 55vh;'):
                if not master_list:
                    with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                        ui.icon('account_balance', size='3rem', color='indigo')
                        ui.label('O Cadastro Mestre está vazio. Clique no botão acima para exportar os convidados do evento atual para a Base Mestre.').classes('text-xs text-center max-w-md')
                else:
                    for cat_name, items in sorted(categories.items()):
                        with ui.expansion(f'📁 {cat_name} ({len(items)} autoridades)', value=True).classes('w-full q-mb-xs text-white font-bold').style('background: rgba(63,81,181,0.15); border-radius: 8px;'):
                            for item in items:
                                m_id = str(item['id'])
                                is_sel = m_id in selected_master_ids
                                
                                def make_master_toggle(mid=m_id):
                                    def _toggle(e):
                                        if e.value:
                                            selected_master_ids.add(mid)
                                        else:
                                            selected_master_ids.discard(mid)
                                    return _toggle

                                with ui.row().classes('w-full items-center q-py-xs q-px-sm rounded-lg gap-2 border-b border-white/5'):
                                    ui.checkbox('', value=is_sel, on_change=make_master_toggle()).props('dense dark')
                                    ui.label(f"{item.get('posto_graduacao', '') or ''}").classes('text-[10px] text-amber font-bold').style('min-width: 60px;')
                                    ui.label(f"{item.get('nome', '')}").classes('text-xs text-white font-bold flex-grow')
                                    if item.get('cargo_funcao'):
                                        ui.label(f"{item['cargo_funcao'][:40]}").classes('text-[9px] text-grey-4 truncate').style('max-width: 200px;')

            ui.separator().classes('q-my-sm')
            with ui.row().classes('w-full justify-between items-center'):
                async def import_selected_from_master():
                    if not selected_master_ids:
                        ui.notify('⚠️ Nenhuma autoridade selecionada.', color='warning')
                        return
                    if not db:
                        return
                    
                    event_id = event['id']
                    count_imported = 0
                    for mid in list(selected_master_ids):
                        m_item = next((x for x in master_list if str(x['id']) == mid), None)
                        if m_item:
                            nome = m_item['nome']
                            posto = m_item.get('posto_graduacao', '')
                            cargo = m_item.get('cargo_funcao', '')
                            cat = m_item.get('categoria', 'Geral')
                            max_ac = m_item.get('max_acompanhantes', 0)
                            
                            res_chk = db.table('jade_convidados').select('id').eq('evento_id', event_id).eq('nome', nome).eq('posto_graduacao', posto).execute()
                            if not res_chk.data:
                                try:
                                    res_ins = db.table('jade_convidados').insert({
                                        'evento_id': event_id,
                                        'nome': nome,
                                        'posto_graduacao': posto,
                                        'cargo_funcao': cargo,
                                        'categoria': cat,
                                        'max_acompanhantes': max_ac,
                                        'status_confirmacao': 'pendente',
                                        'status_placa': 'nao_necessaria'
                                    }).execute()
                                    if res_ins.data:
                                        sync_companions(res_ins.data[0]['id'], nome, max_ac, event_id, cat)
                                    count_imported += 1
                                except Exception as err_imp:
                                    print(f"[IMPORT FROM MASTER ERR] {err_imp}")
                    
                    ui.notify(f'✅ {count_imported} autoridades importadas do Cadastro Mestre para o evento!', color='positive')
                    selected_master_ids.clear()
                    diag.close()
                    render_content.refresh()

                ui.button('📥 Puxar Selecionadas para Este Evento', icon='download', on_click=import_selected_from_master).props('unelevated color=indigo text-color=white dense').classes('text-xs')
                ui.button('Fechar', icon='close', on_click=diag.close).props('unelevated color=grey-8 dense').classes('text-xs')

        diag.open()


    # ═══════════════════════════════════════════════════════════════
    # FASE 6: PLACA EXPRESS (GERAÇÃO E IMPRESSÃO EM 1 CLIQUE)
    # ═══════════════════════════════════════════════════════════════
    def open_express_plate_dialog(event, convidados, layout):
        """Dialog de busca tática ultra-rápida para impressão individual de placas no ato."""
        search_input = {'text': ''}
        
        with ui.dialog() as diag, ui.card().classes('w-full').style(
            f'background: {THEME["bg_panel"]}; max-width: 650px;'
        ):
            with ui.row().classes('w-full items-center justify-between q-mb-xs'):
                with ui.column().classes('gap-0'):
                    ui.label('⚡ PLACA EXPRESS (1 CLIQUE)').classes('text-md font-bold text-deep-orange')
                    ui.label('Busca rápida para confeccionar placa no ato do evento').classes('text-[11px] text-grey-4')
                ui.button(icon='close', on_click=diag.close).props('flat round dense text-color=grey')

            ui.input(
                placeholder='🔍 Digite o nome ou posto da autoridade...',
                on_change=lambda e: [search_input.update({'text': e.value}), results_container.refresh()]
            ).props('dark outlined dense autofocus').classes('w-full q-mb-sm text-xs')

            @ui.refreshable
            def results_container():
                query = search_input['text'].strip().lower()
                if not query:
                    ui.label('💡 Digite acima para buscar entre os convidados cadastrados.').classes('text-xs text-grey-5 q-py-md text-center w-full')
                    return

                matches = [
                    c for c in convidados
                    if query in (c.get('nome') or '').lower()
                    or query in (c.get('posto_graduacao') or '').lower()
                    or query in (c.get('cargo_funcao') or '').lower()
                ]

                if not matches:
                    with ui.column().classes('w-full items-center justify-center q-py-md gap-1'):
                        ui.label(f'Nenhuma autoridade encontrada para "{query}".').classes('text-xs text-amber font-bold')
                        
                        async def quick_add_express():
                            _db = get_service_db_connection() or get_db_connection()
                            if _db:
                                try:
                                    res = _db.table('jade_convidados').insert({
                                        'evento_id': event['id'],
                                        'nome': query.upper(),
                                        'posto_graduacao': 'AUTORIDADE',
                                        'cargo_funcao': 'Convidado de Honra',
                                        'categoria': 'Express',
                                        'status_confirmacao': 'confirmado',
                                        'status_placa': 'impressa'
                                    }).execute()
                                    ui.notify(f'⚡ {query.upper()} adicionado e marcado para impressão!', color='positive')
                                    diag.close()
                                    render_content.refresh()
                                    if res.data:
                                        open_print_cards_dialog(event, [res.data[0]], layout)
                                except Exception as err_q:
                                    ui.notify(f'Erro: {err_q}', color='negative')

                        ui.button('➕ Adicionar e Imprimir Agora', icon='add', on_click=quick_add_express).props('unelevated color=deep-orange dense').classes('text-xs q-mt-xs')
                    return

                with ui.column().classes('w-full gap-1 max-h-[350px] overflow-y-auto q-pr-xs'):
                    for m in matches[:15]:
                        g_nome = m.get('nome', 'N/I')
                        g_posto = m.get('posto_graduacao', '') or ''
                        g_cargo = m.get('cargo_funcao', '') or ''
                        g_assento = m.get('assento_id', '') or 'Sem Assento'
                        
                        with ui.card().classes('w-full q-pa-xs no-shadow rounded-lg border border-white/10').style('background: rgba(255,255,255,0.03);'):
                            with ui.row().classes('w-full items-center justify-between wrap gap-1'):
                                with ui.column().classes('gap-0 flex-grow'):
                                    ui.label(f"{g_posto} {g_nome}").classes('text-xs font-bold text-white')
                                    ui.label(f"{g_cargo} • 🪑 Assento: {g_assento}").classes('text-[10px] text-cyan')

                                async def make_print_express(guest=m):
                                    _db = get_service_db_connection() or get_db_connection()
                                    if _db:
                                        try:
                                            _db.table('jade_convidados').update({'status_placa': 'impressa'}).eq('id', guest['id']).execute()
                                        except Exception:
                                            pass
                                    diag.close()
                                    open_print_cards_dialog(event, [guest], layout)

                                ui.button('🖨️ IMPRIMIR AGORA', icon='print', on_click=make_print_express).props('unelevated color=deep-orange text-color=white dense bold').classes('text-[10px] q-px-xs')

            results_container()

            with ui.row().classes('w-full justify-end q-mt-sm'):
                ui.button('Fechar', icon='close', on_click=diag.close).props('unelevated color=grey-8 dense').classes('text-xs')

        diag.open()

    def open_print_cards_dialog(event, convidados, layout):
        rows_count = layout.get('rows', 5)
        allocated_by_row = {}
        for r in range(rows_count):
            row_label = get_row_label(r)
            allocated_by_row[row_label] = [c for c in convidados if (c.get('assento_id') or '').startswith(f"{row_label}-")]

        # Estado do estúdio de impressão
        print_config = {
            'model': 'cadeira_a4',
            'show_logo': True,
            'show_qr': True,
            'show_rank': True,
            'show_cargo': True,
            'qr_position': 'direita',
            'brasao_position': 'esquerda',
            'header_line1': 'MARINHA DO BRASIL',
            'header_line2': event.get('nome', 'SOLENIDADE').upper(),
            'template_bg_url': '',
            'brasao_left_url': '',
            'brasao_right_url': '',
            'use_template_bg': False
        }

        # Insígnias oficiais por Posto/Graduação (texto rico com indicador visual)
        RANK_INSIGNIAS = {
            'AE':  {'stars': '★★★★', 'title': 'ALMIRANTE DE ESQUADRA',       'color': '#FFD700'},
            'VA':  {'stars': '★★★',  'title': 'VICE-ALMIRANTE',              'color': '#FFD700'},
            'CA':  {'stars': '★★',   'title': 'CONTRA-ALMIRANTE',            'color': '#FFD700'},
            'CMG': {'stars': '★',    'title': 'CAPITÃO DE MAR E GUERRA',     'color': '#C0C0C0'},
            'CF':  {'stars': '⚓',   'title': 'CAPITÃO DE FRAGATA',          'color': '#C0C0C0'},
            'CC':  {'stars': '⚓',   'title': 'CAPITÃO DE CORVETA',          'color': '#C0C0C0'},
            'CT':  {'stars': '⚓',   'title': 'CAPITÃO-TENENTE',             'color': '#B0B0B0'},
            '1TEN': {'stars': '▬',   'title': '1º TENENTE',                  'color': '#B0B0B0'},
            '2TEN': {'stars': '▬',   'title': '2º TENENTE',                  'color': '#B0B0B0'},
            'SO':  {'stars': '◆',    'title': 'SUBOFICIAL',                  'color': '#CD7F32'},
            '1SG': {'stars': '▲▲▲',  'title': '1º SARGENTO',                 'color': '#CD7F32'},
            '2SG': {'stars': '▲▲',   'title': '2º SARGENTO',                 'color': '#CD7F32'},
            '3SG': {'stars': '▲',    'title': '3º SARGENTO',                 'color': '#CD7F32'},
            'CB':  {'stars': '∨∨',   'title': 'CABO',                        'color': '#808080'},
            'SD':  {'stars': '∨',    'title': 'SOLDADO',                     'color': '#808080'},
            'MN':  {'stars': '∨',    'title': 'MARINHEIRO',                  'color': '#808080'},
            'Dr.': {'stars': '⚖️',   'title': 'AUTORIDADE CIVIL',            'color': '#4A90D9'},
            'Min.':{'stars': '🏛️',   'title': 'MINISTRO DE ESTADO',          'color': '#9B59B6'},
            'Dep.':{'stars': '🏛️',   'title': 'DEPUTADO',                    'color': '#27AE60'},
            'Sen.':{'stars': '🏛️',   'title': 'SENADOR',                     'color': '#2980B9'},
            'Gen.':{'stars': '★★★★', 'title': 'GENERAL DE EXÉRCITO',         'color': '#FFD700'},
            'Cel.':{'stars': '★',    'title': 'CORONEL',                     'color': '#C0C0C0'},
            'TC':  {'stars': '★',    'title': 'TENENTE-CORONEL',             'color': '#C0C0C0'},
            'Maj': {'stars': '★',    'title': 'MAJOR',                       'color': '#C0C0C0'}
        }

        with ui.dialog() as diag, ui.card().classes('q-pa-lg').style('min-width: 860px; max-width: 96vw; max-height: 92vh; overflow-y: auto;'):
            ui.label(f"🖨️ ESTÚDIO DE IMPRESSÃO DE PLACAS & CREDENCIAIS JADE").classes('text-md font-bold text-cyan cyber-title q-mb-xs')
            ui.label("Personalize Modelos, Templates de Fundo, Brasões, Insígnias e Posicionamento").classes('text-xs text-grey-4 q-mb-md')

            # ═══════════════════════════════════════════════════════════════
            # PAINEL DE CONFIGURAÇÃO EXPANDIDO (print-hide)
            # ═══════════════════════════════════════════════════════════════
            with ui.card().classes('w-full q-pa-md bg-black/50 border border-cyan-500/30 rounded-xl q-mb-md print-hide'):

                # ── Linha 1: Modelo + Toggles ──
                with ui.row().classes('w-full items-center gap-3 wrap'):
                    ui.label('Modelo:').classes('text-xs text-grey-3 font-bold')
                    model_select = ui.select(
                        options={
                            'cadeira_a4': '📄 Placa de Cadeira (A4 Padrão)',
                            'mesa_a5_dobravel': '🏷️ Placa de Mesa Dobrável (A5)',
                            'credencial': '🪪 Credencial / Crachá de Peito',
                            'template_custom': '🎨 Template Customizado (Imagem de Fundo)'
                        },
                        value=print_config['model']
                    ).props('dark outlined dense').style('min-width: 280px;')

                    with ui.row().classes('items-center gap-2'):
                        chk_logo = ui.checkbox('Brasão MB', value=True).props('dark dense').classes('text-xs text-grey-3')
                        chk_qr = ui.checkbox('QR Code', value=True).props('dark dense').classes('text-xs text-grey-3')
                        chk_rank = ui.checkbox('Insígnia de Posto', value=True).props('dark dense').classes('text-xs text-grey-3')

                ui.separator().classes('q-my-sm').style('border-color: rgba(255,255,255,0.08);')

                # ── Linha 2: Cabeçalho e Título Editáveis ──
                with ui.row().classes('w-full gap-2'):
                    with ui.column().classes('col gap-0'):
                        ui.label('Linha 1 do Cabeçalho:').classes('text-[10px] text-grey-5')
                        input_header1 = ui.input(value=print_config['header_line1']).props('dark outlined dense').classes('w-full')
                    with ui.column().classes('col gap-0'):
                        ui.label('Linha 2 (Título do Evento):').classes('text-[10px] text-grey-5')
                        input_header2 = ui.input(value=print_config['header_line2']).props('dark outlined dense').classes('w-full')

                ui.separator().classes('q-my-sm').style('border-color: rgba(255,255,255,0.08);')

                # ── Linha 3: Brasões e Posicionamento ──
                with ui.row().classes('w-full gap-3 items-end wrap'):
                    with ui.column().classes('gap-0'):
                        ui.label('Posição dos Brasões:').classes('text-[10px] text-grey-5')
                        sel_brasao_pos = ui.select(
                            options={
                                'esquerda': '◀ Brasão à Esquerda',
                                'ambos': '◀ Esquerda + Direita ▶',
                                'centro': '● Brasão Centralizado',
                                'nenhum': '✕ Sem Brasão'
                            },
                            value='esquerda'
                        ).props('dark outlined dense').style('min-width: 210px;')

                    with ui.column().classes('gap-0'):
                        ui.label('Posição QR Code:').classes('text-[10px] text-grey-5')
                        sel_qr_pos = ui.select(
                            options={
                                'direita': '▶ Canto Direito',
                                'esquerda': '◀ Canto Esquerdo',
                                'centro_baixo': '▼ Centro Inferior'
                            },
                            value='direita'
                        ).props('dark outlined dense').style('min-width: 180px;')

                    with ui.column().classes('gap-0 col'):
                        ui.label('Upload Brasão Esquerdo (PNG):').classes('text-[10px] text-grey-5')
                        upload_brasao_left = ui.input(placeholder='URL do brasão esquerdo...').props('dark outlined dense').classes('w-full')
                    with ui.column().classes('gap-0 col'):
                        ui.label('Upload Brasão Direito (PNG):').classes('text-[10px] text-grey-5')
                        upload_brasao_right = ui.input(placeholder='URL do brasão direito...').props('dark outlined dense').classes('w-full')

                ui.separator().classes('q-my-sm').style('border-color: rgba(255,255,255,0.08);')

                # ── Linha 4: Template de Fundo ──
                with ui.row().classes('w-full gap-3 items-end'):
                    with ui.column().classes('col gap-0'):
                        ui.label('🎨 Template de Fundo (URL da Imagem PNG/JPG):').classes('text-[10px] text-amber-4 font-bold')
                        input_template_bg = ui.input(placeholder='Cole a URL da imagem de fundo ou deixe vazio para fundo padrão...').props('dark outlined dense').classes('w-full')
                        ui.label('As informações (Nome, Posto, Assento, QR Code) serão sobrepostas sobre a imagem.').classes('text-[9px] text-grey-6')

                with ui.row().classes('w-full justify-end q-mt-sm'):
                    ui.button('🔄 Atualizar Pré-Visualização', on_click=lambda: preview_container.refresh()).props('unelevated color=cyan text-color=black dense bold').classes('text-xs')

            # ═══════════════════════════════════════════════════════════════
            # CSS DE IMPRESSÃO
            # ═══════════════════════════════════════════════════════════════
            print_css = """
            <style>
            @media print {
                body * { visibility: hidden !important; background: white !important; color: black !important; }
                .print-area, .print-area * { visibility: visible !important; }
                .print-area { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; }
                .print-hide { display: none !important; }
                .page-break { page-break-after: always !important; }
                .jade-card { border: 2px solid #000 !important; margin-bottom: 16px !important; padding: 16px !important; background: #fff !important; color: #000 !important; border-radius: 8px !important; }
                .jade-card-template { margin-bottom: 16px !important; page-break-inside: avoid !important; }
                .jade-card-mesa { border: 2px dashed #666 !important; padding: 12px !important; background: #fff !important; color: #000 !important; margin-bottom: 16px !important; }
                .jade-card-cred { border: 1px solid #000 !important; width: 300px !important; height: 420px !important; padding: 12px !important; margin: 8px !important; float: left !important; }
            }
            .jade-template-card {
                position: relative;
                width: 100%;
                min-height: 180px;
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                border-radius: 12px;
                overflow: hidden;
            }
            .jade-template-overlay {
                position: relative;
                z-index: 2;
                padding: 16px;
                min-height: 180px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                background: rgba(0,0,0,0.45);
            }
            .jade-insignia-badge {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            </style>
            """
            ui.add_head_html(print_css)

            # ═══════════════════════════════════════════════════════════════
            # ÁREA DE PRÉ-VISUALIZAÇÃO
            # ═══════════════════════════════════════════════════════════════
            @ui.refreshable
            def preview_container():
                current_model = model_select.value
                h1 = input_header1.value or 'MARINHA DO BRASIL'
                h2 = input_header2.value or ''
                brasao_pos = sel_brasao_pos.value
                qr_pos = sel_qr_pos.value
                show_logo = chk_logo.value
                show_qr = chk_qr.value
                show_rank = chk_rank.value
                bg_url = input_template_bg.value.strip()
                brasao_l_url = upload_brasao_left.value.strip()
                brasao_r_url = upload_brasao_right.value.strip()
                use_bg = bool(bg_url) or current_model == 'template_custom'

                with ui.column().classes('w-full gap-4 print-area'):
                    for row_label, list_c in allocated_by_row.items():
                        if not list_c:
                            continue

                        with ui.column().classes('w-full gap-2 page-break q-mb-md'):
                            with ui.row().classes('w-full justify-between items-center bg-cyan-950/60 q-pa-sm rounded-lg border border-cyan-500/40 print-hide'):
                                ui.label(f"FILEIRA {row_label} — {len(list_c)} CARTÕES").classes('text-sm font-bold text-cyan')
                                ui.badge(f"Lote Fileira {row_label}").props('color=cyan text-color=black')

                            # ═══ MODELO: TEMPLATE CUSTOMIZADO ═══
                            if current_model == 'template_custom' or use_bg:
                                with ui.grid(columns='1 sm:grid-cols-2').classes('w-full gap-4'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id', '')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        insignia_data = RANK_INSIGNIAS.get(posto, None)
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={c['id']}&color=000000&bgcolor=ffffff"

                                        bg_style = f"background-image: url('{bg_url}');" if bg_url else "background: linear-gradient(135deg, #0a1628 0%, #1a2744 50%, #0d1b2a 100%);"

                                        with ui.card().classes('w-full jade-card-template jade-template-card').style(f'{bg_style} border: 2px solid rgba(0,229,255,0.3); border-radius: 12px;'):
                                            with ui.column().classes('jade-template-overlay'):
                                                # TOPO: Brasões + Cabeçalho
                                                with ui.row().classes('w-full justify-between items-start'):
                                                    if show_logo and brasao_pos in ('esquerda', 'ambos'):
                                                        if brasao_l_url:
                                                            ui.image(brasao_l_url).classes('w-10 h-10 rounded')
                                                        else:
                                                            ui.label('⚓').classes('text-2xl')
                                                    with ui.column().classes('col items-center gap-0'):
                                                        ui.label(h1).classes('text-[10px] font-black text-cyan tracking-[3px] text-center')
                                                        if h2:
                                                            ui.label(h2).classes('text-[9px] font-bold text-amber text-center')
                                                        if show_logo and brasao_pos == 'centro':
                                                            if brasao_l_url:
                                                                ui.image(brasao_l_url).classes('w-8 h-8 rounded q-mt-xs')
                                                            else:
                                                                ui.label('⚓').classes('text-xl')
                                                    if show_logo and brasao_pos in ('ambos',):
                                                        if brasao_r_url:
                                                            ui.image(brasao_r_url).classes('w-10 h-10 rounded')
                                                        else:
                                                            ui.label('⚓').classes('text-2xl')

                                                # MEIO: Insígnia + Nome + Assento
                                                with ui.column().classes('w-full items-center gap-1 q-my-sm'):
                                                    if show_rank and insignia_data:
                                                        ui.html(
                                                            f'<span class="jade-insignia-badge" style="background:{insignia_data["color"]}22; color:{insignia_data["color"]}; border: 1px solid {insignia_data["color"]}44;">'
                                                            f'{insignia_data["stars"]} {insignia_data["title"]}</span>'
                                                        )
                                                    nome_c = f"{posto} {c['nome']}".strip()
                                                    ui.label(nome_c).classes('text-lg font-black text-white text-center leading-tight')
                                                    sub = '(Acompanhante Oficial)' if is_acomp else (c.get('cargo_funcao') or c.get('categoria') or '')
                                                    if sub:
                                                        ui.label(sub).classes('text-[10px] text-grey-3 font-bold')
                                                    ui.badge(f"ASSENTO {c['assento_id']}").props('color=cyan text-color=black bold').classes('text-xs q-mt-xs')

                                                # BASE: QR Code
                                                if show_qr:
                                                    qr_align = 'justify-end' if qr_pos == 'direita' else ('justify-start' if qr_pos == 'esquerda' else 'justify-center')
                                                    with ui.row().classes(f'w-full {qr_align} items-end'):
                                                        with ui.column().classes('items-center gap-0'):
                                                            ui.image(qr_url).classes('w-14 h-14 rounded bg-white p-1')
                                                            ui.label(f"ID:{c['id']}").classes('text-[7px] font-mono text-grey-5')

                            # ═══ MODELO: PLACA DE CADEIRA A4 ═══
                            elif current_model == 'cadeira_a4':
                                with ui.grid(columns='1 sm:grid-cols-2').classes('w-full gap-4'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id', '')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        insignia_data = RANK_INSIGNIAS.get(posto, None)
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=120x120&data={c['id']}&color=000000&bgcolor=ffffff"

                                        with ui.card().classes('w-full q-pa-md jade-card bg-slate-900 border border-cyan-500/40 rounded-xl').style('border-left: 6px solid #00e5ff !important;'):
                                            with ui.row().classes('w-full justify-between items-start no-wrap'):
                                                with ui.column().classes('gap-0 col'):
                                                    # Brasão no topo
                                                    if show_logo:
                                                        with ui.row().classes('items-center gap-1'):
                                                            if brasao_l_url:
                                                                ui.image(brasao_l_url).classes('w-5 h-5')
                                                            ui.label(h1).classes('text-[10px] font-black text-cyan tracking-widest')

                                                    ui.badge(f"ASSENTO {c['assento_id']}").props('color=cyan text-color=black bold').classes('text-xs w-fit q-my-xs')

                                                    if show_rank and insignia_data:
                                                        ui.html(
                                                            f'<span class="jade-insignia-badge" style="background:{insignia_data["color"]}22; color:{insignia_data["color"]}; border: 1px solid {insignia_data["color"]}44;">'
                                                            f'{insignia_data["stars"]} {insignia_data["title"]}</span>'
                                                        )

                                                    nome_c = f"{posto} {c['nome']}".strip()
                                                    ui.label(nome_c).classes('text-md font-black text-white leading-tight q-mt-xs')
                                                    sub = '(Acompanhante Oficial)' if is_acomp else (c.get('cargo_funcao') or c.get('categoria') or 'Convidado de Honra')
                                                    ui.label(sub).classes('text-xs text-grey-4 font-bold q-mt-xs')
                                                    if h2:
                                                        ui.label(h2).classes('text-[9px] text-amber font-bold q-mt-xs')

                                                if show_qr:
                                                    with ui.column().classes('items-center gap-0'):
                                                        ui.image(qr_url).classes('w-16 h-16 rounded bg-white p-1')
                                                        ui.label(f"ID:{c['id']}").classes('text-[8px] font-mono text-grey-5')

                            # ═══ MODELO: MESA DOBRÁVEL A5 ═══
                            elif current_model == 'mesa_a5_dobravel':
                                with ui.grid(columns='1 sm:grid-cols-2').classes('w-full gap-4'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id', '')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        nome_c = f"{posto} {c['nome']}".strip()
                                        sub = '(Acompanhante)' if is_acomp else (c.get('cargo_funcao') or 'Convidado')
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={c['id']}"

                                        with ui.card().classes('w-full q-pa-md jade-card-mesa bg-slate-900 border-2 border-dashed border-cyan-500/40 rounded-xl text-center'):
                                            ui.label('✂️ DOBRA DE MESA (FACE FRONTAL)').classes('text-[8px] text-grey-5 tracking-widest uppercase print-hide')
                                            if show_logo:
                                                ui.label(h1).classes('text-[9px] font-black text-cyan tracking-widest')
                                            ui.label(f"ASSENTO {c['assento_id']}").classes('text-sm font-black text-cyan')
                                            ui.label(nome_c).classes('text-lg font-black text-white q-my-xs')
                                            ui.label(sub).classes('text-xs text-grey-3 font-bold')

                                            ui.separator().classes('q-my-sm print-hide').style('border-color: rgba(255,255,255,0.1);')
                                            ui.label('✂️ DOBRA DE MESA (FACE TRASEIRA)').classes('text-[8px] text-grey-5 tracking-widest uppercase print-hide')
                                            with ui.row().classes('w-full justify-center items-center gap-2 q-mt-xs'):
                                                if show_qr:
                                                    ui.image(qr_url).classes('w-12 h-12 bg-white p-1 rounded')
                                                ui.label(f"FILEIRA {row_label} | {c['assento_id']}").classes('text-xs text-grey-4 font-mono font-bold')

                            # ═══ MODELO: CREDENCIAL / CRACHÁ ═══
                            elif current_model == 'credencial':
                                with ui.grid(columns='1 sm:grid-cols-2 md:grid-cols-3').classes('w-full gap-3'):
                                    for c in sorted(list_c, key=lambda x: x.get('assento_id', '')):
                                        is_acomp = bool(c.get('convidado_principal_id'))
                                        posto = c.get('posto_graduacao') or ''
                                        nome_c = f"{posto} {c['nome']}".strip()
                                        insignia_data = RANK_INSIGNIAS.get(posto, None)
                                        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={c['id']}"

                                        with ui.card().classes('w-full jade-card-cred bg-slate-900 border border-amber-500/40 rounded-2xl q-pa-md items-center text-center justify-between').style('height: 300px;'):
                                            with ui.column().classes('items-center gap-0 w-full'):
                                                if show_logo:
                                                    with ui.row().classes('items-center gap-1'):
                                                        if brasao_l_url:
                                                            ui.image(brasao_l_url).classes('w-6 h-6')
                                                        ui.label(h1).classes('text-[9px] font-black text-cyan tracking-widest')
                                                        if brasao_r_url and brasao_pos == 'ambos':
                                                            ui.image(brasao_r_url).classes('w-6 h-6')
                                                if h2:
                                                    ui.label(h2).classes('text-[10px] font-bold text-amber truncate w-full')
                                                ui.separator().classes('q-my-xs w-full').style('border-color: rgba(255,255,255,0.1);')

                                            with ui.column().classes('items-center gap-0 w-full'):
                                                ui.badge(f"FILEIRA {row_label} - {c['assento_id']}").props('color=cyan text-color=black bold').classes('text-xs q-mb-xs')
                                                if show_rank and insignia_data:
                                                    ui.html(
                                                        f'<span class="jade-insignia-badge" style="background:{insignia_data["color"]}22; color:{insignia_data["color"]}; border: 1px solid {insignia_data["color"]}44; font-size:8px;">'
                                                        f'{insignia_data["stars"]} {insignia_data["title"]}</span>'
                                                    )
                                                ui.label(nome_c).classes('text-sm font-black text-white leading-tight')
                                                sub = '(Acompanhante)' if is_acomp else (c.get('cargo_funcao') or c.get('categoria'))
                                                if sub:
                                                    ui.label(sub).classes('text-[10px] text-grey-4 font-bold')

                                            if show_qr:
                                                ui.image(qr_url).classes('w-14 h-14 bg-white p-1 rounded border border-cyan-500')

            model_select.on('update:model-value', lambda: preview_container.refresh())
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

            # Injeta biblioteca HTML5-QRCode no head
            ui.add_head_html('<script src="https://unpkg.com/html5-qrcode"></script>')

            # Container da Câmera do Celular (HTML5 QR Scanner)
            cam_container = ui.column().classes('w-full hidden q-mb-md border border-cyan-500/40 rounded-xl q-pa-sm bg-black/60')
            with cam_container:
                ui.label('📸 Aponta a câmera para o QR Code impresso no cartão:').classes('text-xs font-bold text-cyan text-center w-full q-mb-xs')
                ui.html('<div id="qr-reader" style="width:100%; max-width:400px; margin:0 auto; background:#000; border-radius:8px;"></div>').classes('w-full flex justify-center')
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
