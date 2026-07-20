import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection, execute_query_safe

THEME = theme.colors

def fetch_rss_news():
    """Busca notícias externas do feed do portal Poder Naval com fallback mock."""
    url = "https://www.naval.com.br/feed/"
    news = []
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:6]:
                title = item.find('title').text
                link = item.find('link').text
                pub_date = item.find('pubDate').text
                try:
                    # Converte data ex: 'Fri, 17 Jul 2026 15:30:00 +0000'
                    dt = datetime.strptime(pub_date[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                    pub_date_br = dt.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    pub_date_br = pub_date
                news.append({
                    'titulo': title,
                    'link': link,
                    'data': pub_date_br,
                    'fonte': 'Poder Naval'
                })
    except Exception as e:
        print(f"[RSS FEED ERROR] {e}. Usando mock.")
        # Fallback Mock
        news = [
            {'titulo': 'Marinha do Brasil realiza Operação de Patrulha Naval no Atlântico Sul', 'link': 'https://agencia.marinha.mil.br/', 'data': datetime.now().strftime('%d/%m/%Y %H:%M'), 'fonte': 'Agência Marinha'},
            {'titulo': 'Navio-Aeródromo Multiproposito realiza exercício conjunto na costa sudeste', 'link': 'https://agencia.marinha.mil.br/', 'data': datetime.now().strftime('%d/%m/%Y %H:%M'), 'fonte': 'Agência Marinha'},
            {'titulo': 'Navio Veleiro Cisne Branco inicia viagem de representação internacional', 'link': 'https://agencia.marinha.mil.br/', 'data': datetime.now().strftime('%d/%m/%Y %H:%M'), 'fonte': 'Agência Marinha'}
        ]
    return news

def render_page():
    ui.label('📢 CANAL DE NOTÍCIAS COMSOC').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_editor = user_role in ('admin', 'supervisor')

    @ui.refreshable
    def render_content():
        # Verificação de solicitações pendentes para exibir alerta inicial para supervisores
        solicitacoes_pendentes_count = 0
        db = get_db_connection()
        if db and user_role in ('admin', 'supervisor'):
            try:
                res_pendentes = db.table('demandas_comunicacao').select('id').eq('status', 'pendente').execute()
                if res_pendentes.data:
                    solicitacoes_pendentes_count = len(res_pendentes.data)
            except Exception as e:
                print(f"[PENDENTES WARNING COUNT ERR] {e}")

        if solicitacoes_pendentes_count > 0:
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl border border-amber-500/30 q-mb-md flex-row items-center justify-between no-wrap').style(
                'background: rgba(245, 158, 11, 0.06);'
            ):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('warning', color='amber-5', size='md').classes('animate-pulse')
                    with ui.column().classes('gap-0'):
                        ui.label('⚠️ ANÁLISE DE DEMANDAS REQUERIDA').classes('text-xs font-bold text-amber-5 tracking-wider')
                        ui.label(f"Existem {solicitacoes_pendentes_count} solicitações de cobertura COMSOC aguardando homologação.").classes('text-[11px] text-grey-4')
                def ir_para_pendentes():
                    ui.navigate.to('/comsoc_homologar')

                ui.button(
                    'Visualizar e Tramitar', 
                    icon='visibility',
                    on_click=ir_para_pendentes
                ).props('unelevated color=amber-9 text-color=black dense bold').classes('text-xs q-px-sm')

        # WIDGET DESTACADO DA AGENDA GOOGLE CALENDAR NA DASHBOARD PRINCIPAL
        with ui.card().classes('w-full q-pa-sm border border-cyan-500/40 rounded-xl bg-black/40 q-mb-md'):
            with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('calendar_month', color='cyan', size='1.8rem')
                    with ui.column().classes('gap-0'):
                        ui.label('📅 AGENDA GOOGLE CALENDAR OFICIAL DO GABINETE / COMSOC').classes('text-xs font-bold text-white cyber-title')
                        ui.label('Sincronizada em Tempo Real • cgcfnaudiovisual@gmail.com').classes('text-[10px] text-cyan font-mono')
                
                with ui.row().classes('items-center gap-2'):
                    ui.button(
                        'Ver Agenda Completa',
                        icon='calendar_today',
                        on_click=lambda: ui.navigate.to('/agenda_geral')
                    ).props('unelevated color=cyan text-color=black bold dense').classes('text-xs q-px-xs')

                    ui.link(
                        '🔗 Abrir no Google',
                        'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                        new_tab=True
                    ).classes('text-[10px] font-bold text-cyan underline q-px-xs q-py-xs bg-cyan-950/60 border border-cyan-500/40 rounded-lg')

        with ui.row().classes('w-full gap-4 items-stretch justify-start'):
            # Coluna 1: Canal Oficial e Interno
            with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 500px;'
                ):
                    with ui.row().classes('w-full justify-between items-center q-mb-md'):
                        ui.label('📢 Informativos e Boletins Oficiais').classes('text-md font-bold text-white')
                        if is_editor:
                            ui.button(
                                'Novo Boletim', 
                                icon='add', 
                                on_click=lambda: open_new_bulletin_dialog()
                            ).props('unelevated color=primary text-color=black bold dense').classes('text-xs q-px-sm')
                            
                    # Carregar boletins do banco de dados
                    boletins = []
                    db = get_db_connection()
                    if db:
                        try:
                            res = db.table('comsoc_noticias').select('*').order('data', desc=True).execute()
                            boletins = res.data if res.data else []
                        except Exception as e:
                            print(f"[DB NOTICIAS ERR] {e}")
                            
                    if boletins:
                        for b in boletins:
                            with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                'background: rgba(255,255,255,0.02); border: 1px solid rgba(0,229,255,0.08);'
                            ):
                                with ui.row().classes('w-full justify-between items-center no-wrap'):
                                    ui.label(b['titulo']).classes('text-xs font-bold text-cyan')
                                    ui.label(b['data']).classes('text-[9px] text-grey')
                                ui.label(b['conteudo']).classes('text-grey-3 text-[11px] leading-relaxed q-mt-xs')
                                with ui.row().classes('w-full justify-between items-center q-mt-sm no-wrap'):
                                    ui.label(f"Autor: {b['autor']}").classes('text-[9px] text-grey')
                                    if b.get('tags'):
                                        ui.badge(b['tags']).props('color=cyan outline').classes('text-[8px]')
                    else:
                        with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-4'):
                            ui.icon('inbox', size='3rem')
                            ui.label('Nenhum informativo registrado.').classes('text-xs')

            # Coluna 2: Notícias Externas (Defesa e Assuntos Marítimos)
            with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 500px;'
                ):
                    ui.label('⚓ Notícias do Setor Naval').classes('text-md font-bold text-white q-mb-md')
                    
                    external_news = fetch_rss_news()
                    for item in external_news:
                        with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg hover:border-primary/50 transition-all').style(
                            'background: rgba(255,255,255,0.01); border: 1px solid rgba(255,255,255,0.03);'
                        ):
                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                ui.label(item['fonte']).classes('text-[9px] text-amber-5 font-bold')
                                ui.label(item['data']).classes('text-[9px] text-grey')
                            
                            # Título clicável
                            ui.link(
                                item['titulo'], 
                                target=item['link'], 
                                new_tab=True
                            ).classes('text-xs font-semibold text-white no-underline hover:underline hover:text-cyan q-mt-xs block')

    def open_new_bulletin_dialog():
        with ui.dialog() as bulletin_dialog, ui.card().classes('w-96 q-pa-md').style(
            f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
        ):
            with ui.column().classes('w-full gap-4'):
                ui.label('📢 LANÇAR BOLETIM INFORMATIVO').classes('text-white text-md font-bold cyber-title')
                
                titulo_input = ui.input('Título do Boletim').props('dark outlined dense w-full')
                conteudo_input = ui.textarea('Conteúdo').props('dark outlined w-full').classes('text-xs')
                tags_input = ui.input('Tags (ex: Defesa, Escala)').props('dark outlined dense w-full')
                error_lbl = ui.label('').classes('text-xs text-red w-full text-center')

                def save_bulletin():
                    if not titulo_input.value or not conteudo_input.value:
                        error_lbl.text = "Preencha todos os campos obrigatórios."
                        return
                    db = get_db_connection()
                    if db:
                        try:
                            registro = {
                                'titulo': titulo_input.value,
                                'conteudo': conteudo_input.value,
                                'autor': user_data.get('nome_guerra', 'Operador').upper(),
                                'data': datetime.now().strftime('%Y-%m-%d'),
                                'tags': tags_input.value
                            }
                            db.table('comsoc_noticias').insert(registro).execute()
                            ui.notify('Boletim registrado com sucesso!', color='success')
                            bulletin_dialog.close()
                            render_content.refresh()
                        except Exception as e:
                            error_lbl.text = f"Erro ao salvar: {e}"

                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                    ui.button('Cancelar', on_click=bulletin_dialog.close).props('flat color=grey')
                    ui.button('Lançar', on_click=save_bulletin).props('unelevated color=primary text-color=black bold')
        bulletin_dialog.open()

    render_content()
