from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection, execute_query_safe

THEME = theme.colors

def render_page():
    ui.label('🎁 CONTROLE DE BRINDES (RELAÇÕES PÚBLICAS)').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_editor = user_role in ('admin', 'supervisor')

    @ui.refreshable
    def render_content():
        with ui.row().classes('w-full gap-4 items-stretch justify-start'):
            # Seção 1: Cadastrar Brinde (1/3 da largura)
            if is_editor:
                with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                    ):
                        ui.label('➕ Novo Item no Estoque').classes('text-md font-bold text-cyan q-mb-md')
                        
                        item_nome = ui.input('Nome do Brinde / Item', placeholder='ex: Moeda de Prata').props('dark outlined dense w-full')
                        item_qtd = ui.number('Quantidade Inicial', value=10, min=0, step=1).props('dark outlined dense w-full')
                        item_desc = ui.textarea('Descrição / Finalidade').props('dark outlined w-full').classes('text-xs')
                        
                        def salvar_novo_item():
                            if not item_nome.value or item_qtd.value is None:
                                ui.notify('Por favor, preencha o nome e quantidade.', color='warning')
                                return
                            db = get_db_connection()
                            if db:
                                try:
                                    registro = {
                                        'nome_item': item_nome.value.upper(),
                                        'quantidade_total': int(item_qtd.value),
                                        'quantidade_disponivel': int(item_qtd.value),
                                        'descricao': item_desc.value or ''
                                    }
                                    db.table('comsoc_brindes_estoque').insert(registro).execute()
                                    ui.notify('Brinde cadastrado com sucesso!', color='success')
                                    
                                    # Limpa form
                                    item_nome.value = ''
                                    item_desc.value = ''
                                    render_content.refresh()
                                except Exception as ex:
                                    ui.notify(f'Erro ao salvar: {ex}', color='red')
                        
                        ui.button(
                            'Salvar Item', 
                            icon='save', 
                            on_click=salvar_novo_item
                        ).props('unelevated color=primary text-color=black bold w-full q-mt-md').classes('w-full font-bold')

            # Seção 2: Lista de Itens (1/3 da largura)
            with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                ):
                    ui.label('📦 Itens Cadastrados').classes('text-md font-bold text-cyan q-mb-md')
                    
                    itens = []
                    db = get_db_connection()
                    if db:
                        try:
                            res = db.table('comsoc_brindes_estoque').select('*').order('nome_item').execute()
                            itens = res.data if res.data else []
                        except Exception as e:
                            print(f"[DB BRINDES ESTOQUE ERR] {e}")
                            
                    if itens:
                        for item in itens:
                            with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);'
                            ):
                                with ui.row().classes('w-full justify-between items-center no-wrap'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(item['nome_item']).classes('text-xs font-bold text-white')
                                        ui.label(item['descricao'] or 'Sem descrição').classes('text-[10px] text-grey')
                                        
                                    # Status do Estoque
                                    disp = item['quantidade_disponivel']
                                    total = item['quantidade_total']
                                    color = "green" if disp >= 10 else "orange" if disp > 0 else "red"
                                    
                                    with ui.row().classes('items-center gap-2'):
                                        ui.badge(f"{disp}/{total}").props(f"color={color}").classes('text-[10px]')
                                        
                                        if disp > 0:
                                            ui.button(
                                                'Distribuir', 
                                                icon='card_giftcard', 
                                                on_click=lambda item=item: open_distribuir_dialog(item)
                                            ).props('unelevated color=cyan text-color=black dense').classes('text-[9px] q-px-sm')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-4'):
                            ui.icon('inventory', size='3rem')
                            ui.label('Nenhum item cadastrado no estoque.').classes('text-xs')

            # Seção 3: Histórico de Distribuição & Saídas (1/3 da largura)
            with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 450px;'
                ):
                    ui.label('🚛 Distribuição / Saídas').classes('text-md font-bold text-cyan q-mb-md')
                    
                    saidas = []
                    db = get_db_connection()
                    if db:
                        try:
                            res = db.table('comsoc_brindes_distribuicao').select('*, comsoc_brindes_estoque(nome_item)').order('id', desc=True).execute()
                            saidas = res.data if res.data else []
                        except Exception as e:
                            print(f"[DB BRINDES DISTRIBUICAO ERR] {e}")
                            
                    if saidas:
                        # Carrega mapeamento rápido para fallback do banco local SQLite
                        estoque_map = {}
                        if db:
                            try:
                                res_est = db.table('comsoc_brindes_estoque').select('id, nome_item').execute()
                                if res_est.data:
                                    estoque_map = {item['id']: item['nome_item'] for item in res_est.data}
                            except Exception as e_est:
                                print(f"[ESTOQUE MAP ERR] {e_est}")

                        for s in saidas:
                            # Resgatar nome do brinde
                            brinde_nome = "Brinde"
                            if s.get('comsoc_brindes_estoque'):
                                brinde_nome = s['comsoc_brindes_estoque']['nome_item']
                            elif s.get('brinde_id') in estoque_map:
                                brinde_nome = estoque_map[s['brinde_id']]
                            
                            with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                'background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03);'
                            ):
                                with ui.row().classes('w-full justify-between items-center'):
                                    ui.label(f"🎁 {s['quantidade']}x {brinde_nome}").classes('text-xs font-bold text-cyan')
                                    ui.label(s['data_entrega']).classes('text-[10px] text-grey')
                                ui.label(f"Para: {s['destinatario_nome']}").classes('text-[11px] text-grey-3 q-mt-xs')
                                ui.label(f"Por: {s['entregue_por']}").classes('text-[9px] text-grey q-mt-xs')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-4'):
                            ui.icon('local_shipping', size='3rem')
                            ui.label('Nenhuma entrega registrada.').classes('text-xs')

    def open_distribuir_dialog(item):
        pautas_options = {}
        db = get_db_connection()
        if db:
            try:
                res_p = db.table('demandas_comunicacao').select('id, titulo_evento, data_evento').eq('status', 'aprovada').execute()
                if res_p.data:
                    pautas_options = {p['id']: f"{p['titulo_evento']} ({p['data_evento']})" for p in res_p.data}
            except Exception as e:
                print(f"[DB BRINDES DIALOG ERR] {e}")

        with ui.dialog() as dist_dialog, ui.card().classes('w-96 q-pa-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.column().classes('w-full gap-4'):
                ui.label(f"🎁 Distribuir: {item['nome_item']}").classes('text-white text-sm font-bold cyber-title')
                ui.label(f"Quantidade disponível: {item['quantidade_disponivel']}").classes('text-[11px] text-grey-4')
                
                dest_input = ui.input('Nome do Destinatário / Autoridade').props('dark outlined dense w-full')
                qtd_input = ui.number('Quantidade', value=1, min=1, max=item['quantidade_disponivel'], step=1).props('dark outlined dense w-full')
                
                ui.select(
                    pautas_options,
                    label='Pauta Vinculada (Opcional)'
                ).props('dark outlined dense w-full option-dark')
                
                error_lbl = ui.label('').classes('text-xs text-red w-full text-center')

                def submeter_distribuicao():
                    if not dest_input.value or qtd_input.value is None:
                        error_lbl.text = "Preencha o nome do destinatário."
                        return
                    
                    qtd = int(qtd_input.value)
                    if qtd > item['quantidade_disponivel']:
                        error_lbl.text = "Quantidade excede o disponível."
                        return
                        
                    db_c = get_db_connection()
                    if db_c:
                        try:
                            # 1. Registra distribuição
                            dist_record = {
                                'brinde_id': item['id'],
                                'quantidade': qtd,
                                'destinatario_nome': dest_input.value.upper(),
                                'data_entrega': datetime.now().strftime('%Y-%m-%d'),
                                'entregue_por': user_data.get('nome_guerra', 'Supervisor').upper()
                            }
                            db_c.table('comsoc_brindes_distribuicao').insert(dist_record).execute()
                            
                            # 2. Atualiza estoque disponível
                            nova_disponibilidade = item['quantidade_disponivel'] - qtd
                            db_c.table('comsoc_brindes_estoque').update({
                                'quantidade_disponivel': nova_disponibilidade
                            }).eq('id', item['id']).execute()
                            
                            ui.notify('Brinde distribuído com sucesso!', color='success')
                            dist_dialog.close()
                            render_content.refresh()
                        except Exception as e:
                            error_lbl.text = f"Erro ao registrar: {e}"

                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                    ui.button('Cancelar', on_click=dist_dialog.close).props('flat color=grey')
                    ui.button('Entregar', on_click=submeter_distribuicao).props('unelevated color=primary text-color=black bold')
        dist_dialog.open()
    render_content()
