# modules/comsoc_historico.py
import json
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection

THEME = theme.colors

def render_page():
    ui.label('📜 HISTÓRICO E ARQUIVO DE EVENTOS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    # Estados de filtro de busca
    filter_state = {
        'termo': '',
        'local': '',
        'autoridade': '',
        'tipo_cobertura': 'todos'
    }

    @ui.refreshable
    def render_event_cards():
        db = get_db_connection()
        pautas = []
        fotos_por_evento = {}
        
        if db:
            try:
                # 1. Puxa todas as demandas aprovadas (eventos concluídos/em andamento)
                res_pautas = db.table('demandas_comunicacao').select('*').eq('status', 'aprovada').order('data_evento', desc=True).execute()
                pautas = res_pautas.data if res_pautas.data else []
                
                # 2. Puxa as fotos registradas e agrupa por evento para encontrar links de drives associados
                res_photos = db.table('processed_photos').select('*').execute()
                photos = res_photos.data if res_photos.data else []
                
                for p in photos:
                    ev_name = p.get('event_name')
                    if ev_name:
                        if ev_name not in fotos_por_evento:
                            fotos_por_evento[ev_name] = []
                        fotos_por_evento[ev_name].append(p)
            except Exception as e:
                print(f"[HISTORICO DB ERR] {e}")

        # Aplica filtros locais
        termo = filter_state['termo'].strip().lower()
        local = filter_state['local'].strip().lower()
        autoridade = filter_state['autoridade'].strip().lower()
        tipo_cob = filter_state['tipo_cobertura']
        
        pautas_filtradas = []
        for p in pautas:
            # Filtro por palavra-chave (título ou solicitante)
            if termo and not (termo in p['titulo_evento'].lower() or termo in p['solicitante_nome'].lower() or termo in p['setor'].lower()):
                continue
            # Filtro por local
            if local and not (local in (p.get('local_evento') or '').lower()):
                continue
            # Filtro por autoridades presentes
            if autoridade and not (autoridade in (p.get('autoridades') or '').lower()):
                continue
            # Filtro por tipo de cobertura (foto, video, redes)
            if tipo_cob != 'todos':
                try:
                    cobs = json.loads(p.get('tipo_cobertura', '[]'))
                    if tipo_cob not in cobs:
                        continue
                except:
                    continue
            pautas_filtradas.append(p)

        if pautas_filtradas:
            with ui.column().classes('w-full gap-4'):
                for p in pautas_filtradas:
                    ev_title = p['titulo_evento']
                    fotos = fotos_por_evento.get(ev_title, [])
                    drive_link = None
                    
                    # Se houver fotos vinculadas via uploader/webhook, pega o primeiro link do drive como oficial da galeria
                    if fotos:
                        drive_link = fotos[0].get('drive_link')
                    
                    # Fallback secundário: busca no campo local se há referências textuais ou no histórico
                    # (Permite também cadastrar link manualmente)
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ):
                        with ui.row().classes('w-full justify-between items-start no-wrap gap-4'):
                            with ui.column().classes('gap-1 flex-grow'):
                                with ui.row().classes('items-center gap-2 wrap'):
                                    ui.label(ev_title).classes('text-md font-bold text-white')
                                    if p.get('sigiloso') == 1:
                                        ui.badge('Sigiloso/Reservado', color='red-10').classes('text-[8px] font-bold')
                                
                                ui.label(f"📅 Data: {p['data_evento']} | Local: {p.get('local_evento', 'Não informado')}").classes('text-xs text-grey-4')
                                if p.get('autoridades'):
                                    ui.label(f"👥 Autoridades: {p['autoridades']}").classes('text-xs text-amber-5 font-semibold')
                                ui.label(f"👤 Solicitado por: {p['solicitante_nome']} ({p['setor']})").classes('text-[11px] text-grey-5')
                                
                                # Renderiza o anexo associado se houver
                                if p.get('arquivo_url') and p.get('arquivo_name'):
                                    with ui.row().classes('items-center gap-1 q-mt-xs bg-white/5 q-px-sm q-py-xs rounded border border-white/10'):
                                        ui.icon('attachment', size='1rem', color='grey-4')
                                        ui.link(
                                            f"Baixar Anexo: {p['arquivo_name']}",
                                            target=p['arquivo_url'],
                                            new_tab=True
                                        ).classes('text-[10px] text-grey-3 hover:underline font-semibold')

                            # Coluna de Links e Ações
                            with ui.column().classes('items-end justify-start gap-2 shrink-0'):
                                if drive_link:
                                    ui.link(
                                        '🔗 Acessar Galeria de Fotos', 
                                        target=drive_link,
                                        new_tab=True
                                    ).classes('text-xs text-cyan hover:underline font-bold bg-cyan/10 q-px-md q-py-sm rounded-lg border border-cyan/20')
                                else:
                                    # Caixa de texto rápida para o operador associar uma pasta do drive caso não tenha uploader automático
                                    def associar_drive(evento=ev_title):
                                        with ui.dialog() as diag, ui.card().classes('w-96 q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                                            ui.label('Associar Link do Drive').classes('text-white text-md font-bold')
                                            link_input = ui.input('Link do Google Drive', placeholder='https://drive.google.com/...').props('dark outlined dense w-full')
                                            
                                            def salvar_link():
                                                url = link_input.value.strip()
                                                if not url:
                                                    return
                                                conn = get_db_connection()
                                                if conn:
                                                    try:
                                                        # Insere registro mockado em processed_photos para registrar a galeria da pauta
                                                        conn.table('processed_photos').insert({
                                                            'event_name': evento,
                                                            'filename': 'drive_folder_link',
                                                            'drive_link': url,
                                                            'criado_em': datetime.now().isoformat()
                                                        }).execute()
                                                        ui.notify('Link da galeria associado com sucesso!', color='success')
                                                        diag.close()
                                                        render_event_cards.refresh()
                                                    except Exception as err:
                                                        ui.notify(f'Erro ao salvar: {err}', color='red')
                                            
                                            with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                                ui.button('Cancelar', on_click=diag.close).props('flat color=grey')
                                                ui.button('Salvar', on_click=salvar_link).props('unelevated color=primary text-color=black')
                                        diag.open()

                                    ui.button(
                                        'Vincular Galeria', 
                                        icon='link',
                                        on_click=associar_drive
                                    ).props('unelevated color=grey-8 text-color=white dense').classes('text-[10px] q-px-sm')
                                
                                # Badge do tipo de coberturas executadas
                                try:
                                    cobs = json.loads(p.get('tipo_cobertura', '[]'))
                                    with ui.row().classes('gap-1 q-mt-xs'):
                                        for c in cobs:
                                            ui.badge(c.upper(), color='slate-700').classes('text-[7.5px]')
                                except:
                                    pass

                                # Botão de Histórico de Alterações / Tramitações
                                def ver_historico_pauta(dem_id=p['id'], titulo=p['titulo_evento']):
                                    with ui.dialog() as diag, ui.card().classes('w-[500px] q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; border-radius:12px;'):
                                        ui.label(f"📜 Linha do Tempo: {titulo}").classes('text-white text-md font-bold cyber-title q-mb-md')
                                        
                                        trams = []
                                        c_db = get_db_connection()
                                        if c_db:
                                            try:
                                                res_tr = c_db.table('demandas_historico_tramitacao').select('*').eq('demanda_id', dem_id).order('data_hora', desc=False).execute()
                                                trams = res_tr.data if res_tr.data else []
                                            except Exception as ex:
                                                print(f"[HISTORICO DIALOG ERR] {ex}")
                                                
                                        if trams:
                                            with ui.column().classes('w-full gap-3 relative q-pl-md').style('border-left: 2px solid rgba(0, 229, 255, 0.15);'):
                                                for tr in trams:
                                                    with ui.column().classes('w-full gap-0 bg-white/5 q-pa-sm rounded-lg relative'):
                                                        # Bolinha da linha do tempo
                                                        ui.element('div').classes('absolute').style('width:10px; height:10px; border-radius:50%; background:#00e5ff; left:-22px; top:12px; border:2px solid #0a0f1e;')
                                                        
                                                        with ui.row().classes('w-full justify-between items-center'):
                                                            ui.label(tr['acao']).classes('text-xs font-bold text-cyan')
                                                            ui.label(tr['data_hora'][:16].replace('T', ' ')).classes('text-[9px] text-grey-4')
                                                        ui.label(tr['parecer']).classes('text-[11px] text-white q-mt-xs')
                                                        ui.label(f"Por: {tr['usuario']}").classes('text-[9px] text-grey-5 q-mt-xs')
                                        else:
                                            with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-5'):
                                                ui.icon('info', size='2rem')
                                                ui.label('Nenhum histórico registrado para este evento.').classes('text-xs')
                                                
                                        with ui.row().classes('w-full justify-end q-mt-md'):
                                            ui.button('Fechar', on_click=diag.close).props('flat color=grey')
                                    diag.open()

                                ui.button(
                                    'Histórico', 
                                    icon='history_edu',
                                    on_click=lambda dem_id=p['id'], tit=p['titulo_evento']: ver_historico_pauta(dem_id, tit)
                                ).props('flat dense color=amber-5').classes('text-[9px] q-px-sm')
        else:
            with ui.column().classes('w-full items-center justify-center q-py-xl gap-2 text-grey-4'):
                ui.icon('search_off', size='3rem')
                ui.label('Nenhum evento histórico atende aos filtros atuais.').classes('text-xs')

    # Painel de Filtros Superiores
    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full items-center gap-3 wrap justify-start'):
            txt_busca = ui.input(
                label='Buscar Palavra-chave (Título, Autoridade, etc.)', 
                placeholder='Ex: Deputado, Visita, Fortaleza...'
            ).props('dark outlined dense').classes('grow').style('min-width: 200px;')
            
            txt_local = ui.input(
                label='Localidade / Setor', 
                placeholder='Ex: Fortaleza, Gabinete...'
            ).props('dark outlined dense').classes('w-44').style('min-width: 140px;')
            
            sel_cob = ui.select(
                {
                    'todos': 'Todas Coberturas',
                    'foto': 'Fotografia',
                    'video': 'Vídeo / Filme',
                    'redes': 'Mídias / Texto'
                },
                value='todos',
                label='Escopo de Cobertura'
            ).props('dark outlined dense option-dark').classes('w-44').style('min-width: 140px;')

            def aplicar_filtros():
                filter_state['termo'] = txt_busca.value or ''
                filter_state['local'] = txt_local.value or ''
                filter_state['tipo_cobertura'] = sel_cob.value
                render_event_cards.refresh()

            ui.button(
                'Filtrar', 
                icon='search', 
                on_click=aplicar_filtros
            ).props('unelevated color=primary text-color=black bold').classes('q-px-lg cyber-glow')

    # Render do Grid principal
    render_event_cards()
