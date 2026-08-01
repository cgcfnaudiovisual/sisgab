from nicegui import ui, app, run
import theme
import ai_helper
from database import get_bot_db_connection, get_db_connection, get_service_db_connection
import json
import re
import urllib.parse

THEME = theme.colors

# Questionário padrão do Checklist para enviar aos solicitantes
CHECKLIST_TEMPLATE = """📋 QUESTIONÁRIO DE SOLICITAÇÃO DE PAUTA E COBERTURA - COMSOC/CGCFN
Por favor, responda as perguntas abaixo com o máximo de detalhes possível para o agendamento da equipe de Audiovisual:

1. Dados do Solicitante
1. Posto/Graduação e Nome Completo do Solicitante?

2. Organização Militar (OM) solicitante?
( ) CGCFN
( ) Outra OM. (Se outra, digite qual: _______________)

3. Ramal ou Telefone de contato?

2. Detalhes do Evento
4. Título do Evento ou Pauta?

5. Data de Início e Data de Término (DD/MM/AAAA)?

6. Horário de Início (HH:MM) e Horário de Término previsto?

7. Local exato do Evento?

8. Uniforme do evento?

9. Quais autoridades estarão presentes? (Opcional)

10. O roteiro, VOGAL ou documento de produção da cobertura está disponível?
(Nota: Favor encaminhar o arquivo de roteiro para o e-mail: cgcfnaudiovisual@gmail.com)

3. Escopo do Audiovisual e Logística
11. Tipo de cobertura requerida?
( ) Fotografia
( ) Vídeo
( ) Ambos (Fotografia e Vídeo)

12. Formato de entrega do vídeo desejado?
( ) Cobertura Íntegra (registro completo do evento)
( ) Melhores Momentos (vídeo curto resumo / Reels / Shorts)
( ) Apenas Material Bruto

13. Há transporte assegurado para a equipe de cobertura e seus equipamentos?

14. O local do evento possui estrutura ou viabilidade de espaço adequado para a equipe descarregar (fazer o backup) do material captado?

⚠️ INFORMAÇÃO IMPORTANTE:
Após o envio das respostas, esta solicitação será encaminhada para a avaliação do Oficial responsável pela ComSoc para verificação de viabilidade técnica, prioridade institucional e escala da equipe.

Por favor, aguarde o retorno com a confirmação da pauta.
"""

def render_page():
    db_conn = get_bot_db_connection()
    
    # State local do chat
    state = {
        'chat_messages': [],
    }

    with ui.column().classes('w-full q-pa-lg gap-4'):
        ui.label('🤖 CENTRAL DE INTELIGÊNCIA ARTIFICIAL (IA)').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')

        # Tabs Quasar responsivas para as 4 seções unificadas (fazem wrap automático abaixo)
        with ui.tabs().classes('w-full text-primary border-b border-gray-800 flex-wrap') as tabs:
            tab_chat = ui.tab('💬 Chat Geral & Dúvidas').classes('text-xs sm:text-sm')
            tab_redator = ui.tab('📝 Redator de Releases & Notas').classes('text-xs sm:text-sm')
            tab_lote = ui.tab('📅 Cadastro em Lote (IA)').classes('text-xs sm:text-sm')

        with ui.tab_panels(tabs, value=tab_chat).classes('w-full bg-transparent no-shadow gap-0'):
            
            # ABA 1: CONVERSA TÁTICA (CHAT)
            with ui.tab_panel(tab_chat).classes('p-0 gap-4 w-full'):
                with ui.column().classes('w-full gap-4'):
                    # Card principal do Chat
                    with ui.card().classes('w-full q-pa-md h-[550px] flex flex-col justify-between border border-gray-800').style(f'background: {THEME["bg_panel"]}'):
                        
                        # Mensagem de Boas-vindas da IA
                        with ui.row().classes('w-full items-center justify-between border-b border-gray-800 q-pb-sm'):
                            with ui.row().classes('items-center gap-2'):
                                ui.avatar(icon='psychology').style(f'background: {THEME["primary"]}; color: {THEME["bg_app"]}; width: 32px; height: 32px;')
                                with ui.column().classes('gap-0'):
                                    ui.label('ASSISTENTE VIRTUAL DE GABINETE').classes('text-xs text-weight-bold tracking-wider text-white cyber-title')
                                    ui.label('Motor Gemini • Apoio Operacional e Comunicação').classes('text-[10px] text-grey-5')
                            
                            # Seletor de Modelo Gemini dinâmico no Chat
                            modelos_disponiveis = ai_helper.get_available_gemini_models()
                            modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                            if modelo_salvo not in modelos_disponiveis:
                                modelos_disponiveis[modelo_salvo] = f"{modelo_salvo} (Ativo)"
                                
                            chat_model_select = ui.select(
                                modelos_disponiveis,
                                value=modelo_salvo,
                                on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                            ).props('dark outlined dense options-dark').classes('w-44 text-[10px]').style('max-height: 28px;')
                        
                        # Área de Conversa com Scroll
                        with ui.scroll_area().classes('w-full flex-grow q-py-md') as scroll_area:
                            chat_area = ui.column().classes('w-full gap-3')
                            
                            # Bolha de boas vindas inicial
                            with chat_area:
                                with ui.row().classes('w-full gap-2 items-start justify-start'):
                                    ui.avatar(icon='psychology').style(f'background: {THEME["primary"]}; color: {THEME["bg_app"]}; width: 36px; height: 36px;')
                                    with ui.column().classes('max-w-[75%] gap-1'):
                                        ui.label('SISGAB-AI').classes('text-[10px] text-grey-5 text-weight-bold')
                                        with ui.card().classes('q-pa-sm rounded-lg border border-gray-800').style(f'background: {THEME["bg_editor"]}; color: #e2e8f0;'):
                                            ui.label('Olá! Sou o Assistente Virtual do Gabinete. Posso auxiliar com redação de documentos militares oficiais, confecção de partes, consultas do Regulamento Disciplinar da Marinha (RDM), roteiros de pauta e releases para a imprensa. Como posso ajudar hoje?').classes('text-sm text-weight-medium')

                        # Atalhos Rápidos (Perguntas Frequentes)
                        with ui.row().classes('w-full gap-2 q-py-xs justify-center border-t border-gray-800/50'):
                            def select_fast_question(q_text):
                                chat_input.value = q_text
                                send_message()
                            
                            ui.button('📰 Nota Oficial', on_click=lambda: select_fast_question('Redija uma nota oficial de Comunicação Social para divulgação de um evento institucional da Marinha do Brasil. Use o padrão formal e institucional.')).props('outline dense size=sm color=cyan').classes('text-[10px] font-bold')
                            ui.button('⚖️ Consultar RDM', on_click=lambda: select_fast_question('Quais as principais esferas de punição e contrapesos previstos no Regulamento Disciplinar da Marinha (RDM) para contravensões disciplinares leves?')).props('outline dense size=sm color=cyan').classes('text-[10px] font-bold')
                            ui.button('✍️ Elaborar Ofício/Parte', on_click=lambda: select_fast_question('Como estruturar uma Parte de Ocorrência formal direcionada ao Comando da OM relatando uma avaria ou extravio de material?')).props('outline dense size=sm color=cyan').classes('text-[10px] font-bold')

                        # Caixa de Input e Envio
                        with ui.row().classes('w-full gap-2 items-center justify-between'):
                            chat_input = ui.input(placeholder='Digite sua consulta ao assistente de inteligência artificial...').props('dark outlined dense').classes('flex-grow').style(f'background: {THEME["bg_input"]}')
                            
                            def send_message():
                                text = chat_input.value.strip()
                                if not text:
                                    return
                                
                                chat_input.value = ''
                                
                                # Adiciona bolha do usuário
                                user_data = app.storage.user.get('user_data', {})
                                user_name = user_data.get('nome_guerra', 'Operador')
                                user_photo = user_data.get('url_foto')
                                
                                with chat_area:
                                    with ui.row().classes('w-full gap-2 items-start justify-end'):
                                        with ui.column().classes('max-w-[75%] gap-1 items-end'):
                                            ui.label(user_name).classes('text-[10px] text-grey-5 text-weight-bold')
                                            with ui.card().classes('q-pa-sm rounded-lg').style(f'background: {THEME["primary"]}; color: {THEME["bg_app"]}; font-weight: 500;'):
                                                ui.label(text).classes('text-sm text-weight-medium')
                                        if user_photo and isinstance(user_photo, str) and user_photo.startswith('http'):
                                            ui.avatar().style(f"background-image: url('{user_photo}'); background-size: cover; background-position: center; width: 36px; height: 36px;")
                                        else:
                                            ui.avatar(icon='person').style(f'background: {THEME["bg_editor"]}; color: #e2e8f0; width: 36px; height: 36px;')
                                
                                scroll_area.scroll_to(percent=1.0)
                                
                                # Resposta (Spinner)
                                with chat_area:
                                    bot_row = ui.row().classes('w-full gap-2 items-start justify-start')
                                    with bot_row:
                                        ui.avatar(icon='psychology').style(f'background: {THEME["primary"]}; color: {THEME["bg_app"]}; width: 36px; height: 36px;')
                                        with ui.column().classes('max-w-[75%] gap-1'):
                                            ui.label('SISGAB-AI').classes('text-[10px] text-grey-5 text-weight-bold')
                                            spinner = ui.spinner(color='cyan', size='md')
                                
                                scroll_area.scroll_to(percent=1.0)
                                
                                async def fetch_ai_response():
                                    try:
                                        # Carrega o modelo selecionado no dropdown
                                        ai_helper.GEMINI_MODEL_NAME = chat_model_select.value or 'gemini-2.0-flash'
                                        ans = await run.io_bound(ai_helper.chat_with_ai, text)
                                    except Exception as e:
                                        ans = f"Erro ao contatar o assistente de IA: {e}"
                                    
                                    spinner.delete()
                                    with bot_row:
                                        with ui.card().classes('q-pa-sm rounded-lg border border-gray-800 w-full').style(f'background: {THEME["bg_editor"]}; color: #e2e8f0;'):
                                            ui.markdown(ans).classes('text-sm text-weight-medium w-full')
                                    scroll_area.scroll_to(percent=1.0)
                                
                                ui.timer(0.1, fetch_ai_response, once=True)
 
                            chat_btn = ui.button(icon='send', on_click=send_message).props('unelevated color=cyan text-color=dark').classes('q-px-sm')
                            chat_input.on('keydown.enter', send_message)

            # ABA 2: REDATOR DE RELEASES & NOTAS
            with ui.tab_panel(tab_redator).classes('p-0 gap-4 w-full'):
                with ui.row().classes('w-full gap-4 items-stretch'):
                    
                    # Painel da Esquerda (Entrada)
                    with ui.column().classes('col-12 col-md-6 gap-4'):
                        with ui.card().classes('w-full q-pa-md border border-gray-800').style(f'background: {THEME["bg_panel"]}'):
                            with ui.row().classes('w-full justify-between items-center border-b border-gray-800 q-pb-sm q-mb-sm'):
                                ui.label('📝 REDATOR INTELIGENTE DE DOCUMENTOS').classes('text-xs text-weight-bold text-primary cyber-title')
                                
                                # Seletor de Modelo Gemini dinâmico no Redator
                                modelos_disponiveis = ai_helper.get_available_gemini_models()
                                modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                                if modelo_salvo not in modelos_disponiveis:
                                    modelos_disponiveis[modelo_salvo] = f"{modelo_salvo} (Ativo)"
                                    
                                redator_model_select = ui.select(
                                    modelos_disponiveis,
                                    value=modelo_salvo,
                                    on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                                ).props('dark outlined dense options-dark').classes('w-44 text-[10px]').style('max-height: 28px;')
                            
                            redator_style = ui.select(
                                label='Estilo / Tom de Linguagem',
                                options={
                                    'military': 'Redação Oficial Naval (Padrão de Ofício/Parte da MB)',
                                    'formal': 'Jornalístico / Divulgação Oficial (Releases)',
                                    'simple': 'Simples & Direto'
                                },
                                value='military'
                             ).classes('w-full').props('dark dense outlined options-dense')
                            
                            redator_input = ui.textarea(
                                label='Rascunho Inicial do Texto',
                                placeholder='Cole o rascunho de informações ou texto incompleto que deseja formatar...'
                            ).classes('w-full').props('dark outlined rows=12')
                            
                            redator_btn = ui.button('✨ Melhorar e Adaptar Estilo', on_click=lambda: adapt_text_style()).props('unelevated color=cyan text-color=dark w-full bold').classes('q-py-xs font-bold')

                    # Painel da Direita (Saída)
                    with ui.column().classes('col-12 col-md-6 gap-4'):
                        with ui.card().classes('w-full q-pa-md border border-gray-800 h-full flex flex-col justify-between').style(f'background: {THEME["bg_panel"]}'):
                            
                            with ui.row().classes('w-full justify-between items-center border-b border-gray-800 q-pb-sm'):
                                ui.label('✨ RESULTADO OTIMIZADO PELA IA').classes('text-xs text-weight-bold text-primary cyber-title')
                                redator_copy_btn = ui.button('📋 Copiar', on_click=lambda: copy_redator_text()).props('flat dense color=cyan text-color=cyan size=sm').classes('hidden')
                            
                            with ui.scroll_area().classes('w-full flex-grow q-py-md h-[400px]') as redator_scroll:
                                redator_output_area = ui.column().classes('w-full')
                                with redator_output_area:
                                    redator_placeholder = ui.label('Rascunhe um texto e escolha o estilo no painel esquerdo para obter uma redação militar impecável.').classes('text-grey-5 text-sm q-pa-md text-center w-full')
                            
                            redator_state = {'text': ''}

                            def copy_redator_text():
                                if redator_state['text']:
                                    ui.run_javascript(f"navigator.clipboard.writeText({repr(redator_state['text'])})")
                                    ui.notify("Texto otimizado copiado!", color="success")

                            def adapt_text_style():
                                if not redator_input.value or not redator_input.value.strip():
                                    ui.notify('Escreva um rascunho antes!', color='warning')
                                    return
                                
                                redator_placeholder.delete()
                                redator_output_area.clear()
                                with redator_output_area:
                                    with ui.column().classes('w-full items-center justify-center gap-2 q-py-xl'):
                                        ui.spinner(color='cyan', size='lg')
                                        ui.label('Formatando redação...').classes('text-cyan text-xs font-bold tracking-widest cyber-title')
                                
                                async def run_redator_ai():
                                    try:
                                        ai_helper.GEMINI_MODEL_NAME = redator_model_select.value or 'gemini-2.0-flash'
                                        ans = await run.io_bound(
                                            ai_helper.improve_text,
                                            text=redator_input.value.strip(),
                                            style=redator_style.value
                                        )
                                    except Exception as e:
                                        ans = f"Erro na chamada da API de IA: {str(e)}"
                                    
                                    redator_output_area.clear()
                                    redator_state['text'] = ans
                                    redator_copy_btn.classes(remove='hidden')
                                    with redator_output_area:
                                        ui.markdown(ans).classes('text-sm text-white w-full q-pa-sm')
                                    redator_scroll.scroll_to(percent=0.0)

                                ui.timer(0.1, run_redator_ai, once=True)

            # ABA 4: CADASTRO EM LOTE (IA)
            with ui.tab_panel(tab_lote).classes('p-0 gap-4 w-full'):
                with ui.card().classes('w-full q-pa-md border border-gray-800').style(f'background: {THEME["bg_panel"]}'):
                    with ui.row().classes('w-full justify-between items-center border-b border-gray-800 q-pb-sm q-mb-sm'):
                        # Lado Esquerdo: Título e Identidade
                        with ui.row().classes('items-center gap-2'):
                            ui.avatar(icon='calendar_month').style(f'background: {THEME["primary"]}; color: {THEME["bg_app"]}; width: 32px; height: 32px;')
                            with ui.column().classes('gap-0'):
                                ui.label('📅 CADASTRO INTELIGENTE EM LOTE (IA)').classes('text-xs text-weight-bold tracking-wider text-white cyber-title')
                                ui.label('Inserção Múltipla Dinâmica na Agenda').classes('text-[10px] text-grey-5')
                            
                        # Lado Direito: Seletor de Modelo Gemini
                        modelos_disponiveis = ai_helper.get_available_gemini_models()
                        modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                        if modelo_salvo not in modelos_disponiveis:
                            modelo_salvo = list(modelos_disponiveis.keys())[0] if modelos_disponiveis else 'gemini-2.0-flash'
                            app.storage.user['preferred_gemini_model'] = modelo_salvo
                            
                        lote_model_select = ui.select(
                            modelos_disponiveis,
                            value=modelo_salvo,
                            on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                        ).props('dark outlined dense options-dark').classes('w-48 text-[11px]').style('max-height: 28px;')

                    ui.label('Cole um texto livre (pauta semanal, mensagens do WhatsApp, e-mail) contendo um ou vários eventos/pautas. A IA identificará todos os eventos e montará um formulário de revisão para você ajustar e confirmar antes de salvar tudo na agenda de uma vez.').classes('text-xs text-grey-4 q-mb-md')
                    
                    lote_input = ui.textarea(
                        placeholder='Ex: Pautas da semana:\n1. Formatura matutina dia 28/07 às 09:00h no pátio principal, uniforme 3.2, presença do Comandante-Geral.\n2. Reunião de pauta no gabinete dia 29/07 às 14:00h para planejar coberturas.'
                    ).props('dark outlined rows=6').classes('w-full q-mb-md')
                    
                    # Estado reativo dos eventos extraídos
                    state_lote = {'eventos': []}
                    
                    @ui.refreshable
                    def render_lote_review_form():
                        if not state_lote['eventos']:
                            ui.label('Nenhum evento extraído ainda. Cole um texto acima e clique em "Extrair e Destrinchar Eventos".').classes('text-xs text-grey-5 italic text-center w-full q-py-lg')
                            return
                        
                        ui.label(f"✨ EVENTOS EXTRAÍDOS ({len(state_lote['eventos'])}):").classes('text-xs font-bold text-cyan border-b border-gray-800 w-full q-pb-xs q-mb-md')
                        
                        # Loop para renderizar cada evento em um card editável
                        for index, ev in enumerate(state_lote['eventos']):
                            with ui.card().classes('w-full q-pa-sm border border-gray-800 rounded bg-black/10 q-mb-md').style('border-left: 4px solid #00e5ff;'):
                                with ui.row().classes('w-full justify-between items-center no-wrap border-b border-gray-800/50 q-pb-xs q-mb-sm'):
                                    ui.label(f"Pauta #{index + 1}").classes('text-xs font-bold text-white')
                                    ui.button(
                                        icon='delete', 
                                        on_click=lambda idx=index: remover_evento_lote(idx)
                                    ).props('flat round dense color=red').classes('text-xs')
                                
                                with ui.grid(columns=1).classes('w-full gap-2 sm:grid-cols-2 md:grid-cols-3'):
                                    # Título
                                    t = ui.input('Título do Evento', value=ev.get('titulo_evento', '')).props('dark outlined dense').classes('w-full text-xs')
                                    t.bind_value(ev, 'titulo_evento')
                                    
                                    # Data
                                    d = ui.input('Data (AAAA-MM-DD)', value=ev.get('data_evento', '')).props('dark outlined dense').classes('w-full text-xs')
                                    d.bind_value(ev, 'data_evento')
                                    # Adiciona seletor de data
                                    with d.add_slot('append'):
                                        ui.icon('event').classes('cursor-pointer').on('click', lambda: date_picker.open())
                                    with ui.dialog() as date_dialog:
                                        date_picker = ui.date(on_change=lambda e: (d.set_value(e.value), date_dialog.close())).props('dark')
                                    
                                    # Hora
                                    h = ui.input('Hora (HH:MM)', value=ev.get('hora_evento', '')).props('dark outlined dense').classes('w-full text-xs')
                                    h.bind_value(ev, 'hora_evento')
                                    
                                    # Local
                                    l = ui.input('Local', value=ev.get('local_evento', '')).props('dark outlined dense').classes('w-full text-xs')
                                    l.bind_value(ev, 'local_evento')
                                    
                                    # Solicitante
                                    s = ui.input('Solicitante', value=ev.get('solicitante_nome', '')).props('dark outlined dense').classes('w-full text-xs')
                                    s.bind_value(ev, 'solicitante_nome')
                                    
                                    # Autoridades
                                    a = ui.input('Autoridades', value=ev.get('autoridades', '')).props('dark outlined dense').classes('w-full text-xs')
                                    a.bind_value(ev, 'autoridades')
                                
                                # Tipo Cobertura (checkboxes)
                                cobs = ev.get('tipo_cobertura', ['foto'])
                                if isinstance(cobs, str):
                                    try:
                                        cobs = json.loads(cobs)
                                    except:
                                        cobs = [cobs]
                                
                                with ui.row().classes('w-full gap-4 q-mt-sm items-center'):
                                    ui.label('Cobertura:').classes('text-xs text-grey-5')
                                    def update_cob(ev_ref=ev, key='', val=False):
                                        current = ev_ref.get('tipo_cobertura', ['foto'])
                                        if isinstance(current, str):
                                            try: current = json.loads(current)
                                            except: current = [current]
                                        if val:
                                            if key not in current: current.append(key)
                                        else:
                                            if key in current: current.remove(key)
                                        ev_ref['tipo_cobertura'] = current

                                    ui.checkbox('Foto', value='foto' in cobs, on_change=lambda e, ev_ref=ev: update_cob(ev_ref, 'foto', e.value)).classes('text-xs')
                                    ui.checkbox('Vídeo', value='video' in cobs, on_change=lambda e, ev_ref=ev: update_cob(ev_ref, 'video', e.value)).classes('text-xs')
                                    ui.checkbox('Redes', value='redes' in cobs, on_change=lambda e, ev_ref=ev: update_cob(ev_ref, 'redes', e.value)).classes('text-xs')
                                    
                                    # Sigilo
                                    ui.checkbox('Sigiloso/Reservado', value=ev.get('sigiloso') == 1, on_change=lambda e, ev_ref=ev: ev_ref.update({'sigiloso': 1 if e.value else 0})).classes('text-xs text-amber-5 ml-auto')

                        # Botão de confirmação final
                        with ui.row().classes('w-full justify-center q-mt-lg'):
                            ui.button(
                                'Confirmar e Cadastrar todos na Agenda',
                                icon='playlist_add_check',
                                on_click=lambda: salvar_lote_agenda()
                            ).props('unelevated color=green text-color=dark w-full bold').classes('q-py-md text-sm font-black w-full max-w-lg')

                    def remover_evento_lote(index):
                        state_lote['eventos'].pop(index)
                        render_lote_review_form.refresh()

                    async def extrair_lote_ia():
                        text = lote_input.value.strip()
                        if not text:
                            ui.notify('Cole o texto antes de processar!', color='warning')
                            return
                        
                        # Mostra spinner
                        lote_review_container.clear()
                        with lote_review_container:
                            ui.spinner(color='cyan', size='lg').classes('q-mx-auto')
                            ui.label('Analisando e destrinchando eventos com IA...').classes('text-xs text-cyan text-center w-full font-bold tracking-widest cyber-title')
                        
                        try:
                            ai_helper.GEMINI_MODEL_NAME = lote_model_select.value or 'gemini-2.0-flash'
                            res_json = await run.io_bound(ai_helper.parse_multiple_events, text)
                            state_lote['eventos'] = json.loads(res_json)
                            lote_review_container.clear()
                            with lote_review_container:
                                render_lote_review_form()
                        except Exception as err:
                            lote_review_container.clear()
                            with lote_review_container:
                                ui.label(f"Erro ao processar lote: {err}").classes('text-red text-xs text-center w-full')
                                ui.notify('Falha ao interpretar lote. Escolha outro modelo ou tente novamente.', color='warning')

                    async def salvar_lote_agenda():
                        db = get_service_db_connection() or get_db_connection()
                        if not db:
                            ui.notify('Sem conexão ativa com o banco de dados.', color='red')
                            return
                        
                        try:
                            # Prepara payloads mapeados ao banco
                            payloads = []
                            for ev in state_lote['eventos']:
                                # Validação mínima
                                if not ev.get('titulo_evento') or not ev.get('titulo_evento').strip():
                                    ui.notify('Todos os eventos necessitam de um Título!', color='warning')
                                    return
                                if not ev.get('data_evento'):
                                    ui.notify(f"Falta a data para o evento '{ev.get('titulo_evento')}'!", color='warning')
                                    return
                                
                                cobs = ev.get('tipo_cobertura', ['foto'])
                                if isinstance(cobs, str):
                                    try: cobs = json.loads(cobs)
                                    except: cobs = [cobs]
                                
                                 obs_text = ev.get('observacoes_execucao') or ''
                                 aut_text = ev.get('autoridades') or ''
                                 full_aut = f"{aut_text} | Obs: {obs_text}".strip(' |') if obs_text else aut_text

                                 payloads.append({
                                     'solicitante_nome': ev.get('solicitante_nome') or 'COMSOC / GABINETE',
                                     'setor': ev.get('setor') or 'Gabinete',
                                     'contato': ev.get('contato') or 'Interno',
                                     'titulo_evento': str(ev.get('titulo_evento', '')).upper(),
                                     'categoria_demanda': 'audiovisual',
                                     'data_evento': ev.get('data_evento'),
                                     'data_fim': ev.get('data_evento'),
                                     'hora_evento': ev.get('hora_evento') or '09:00',
                                     'local_evento': ev.get('local_evento') or 'Quartel / Gabinete',
                                     'tipo_cobertura': json.dumps(cobs),
                                     'autoridades': full_aut,
                                     'score_esforco': 1.0,
                                     'sigiloso': int(ev.get('sigiloso', 0)),
                                     'status': 'aprovado',  # Inserção direta aprovada
                                     'captacao_entrega': 'captacao_e_edicao',
                                     'notificar_militar_ids': '[]'
                                 })
                            
                            if not payloads:
                                ui.notify('Nenhum evento na lista para salvar.', color='warning')
                                return
                            
                            # Executa inserção no banco
                            res = db.table('demandas_comunicacao').insert(payloads).execute()
                            inserted_rows = res.data if res.data else []
                            
                            # Registra histórico de tramitação para cada evento inserido
                            for r in inserted_rows:
                                dem_id = r.get('id')
                                if dem_id:
                                    hist = {
                                        'demanda_id': dem_id,
                                        'data_hora': datetime.now().isoformat(),
                                        'usuario': app.storage.user.get('user_data', {}).get('nome_guerra', 'ASSISTENTE IA'),
                                        'acao': 'Pauta Cadastrada em Lote (IA)',
                                        'parecer': 'Evento importado e cadastrado diretamente em lote via Inteligência Artificial.'
                                    }
                                    db.table('demandas_historico_tramitacao').insert(hist).execute()
                            
                            # Notifica admin via Telegram
                            try:
                                from notifications_manager import notify_telegram
                                alert_txt = (
                                    f"📅 **CADASTRO EM LOTE REALIZADO COM SUCESSO (IA)**\n\n"
                                    f"👤 Operador: {app.storage.user.get('user_data', {}).get('nome_guerra', 'ASSISTENTE IA')}\n"
                                    f"📂 Quantidade: {len(payloads)} novos eventos inseridos de forma única na agenda tática.\n\n"
                                    f"Acesse a Agenda Geral ou o Homologar Pautas para escalar os militares encarregados."
                                )
                                notify_telegram(alert_txt, "saude", role_required="admin")
                            except Exception as tel_err:
                                print(f"[TELEGRAM LOTE NOTIF ERR] {tel_err}")
                            
                            ui.notify(f"🎯 {len(payloads)} eventos cadastrados com sucesso na agenda!", color='success')
                            
                            # Reseta o formulário
                            state_lote['eventos'] = []
                            lote_input.value = ''
                            lote_review_container.clear()
                            with lote_review_container:
                                render_lote_review_form()
                        except Exception as save_err:
                            ui.notify(f"Erro ao salvar eventos: {save_err}", color='red')

                    with ui.row().classes('w-full justify-center'):
                        ui.button(
                            'Extrair e Destrinchar Eventos',
                            icon='psychology',
                            on_click=extrair_lote_ia
                        ).props('unelevated color=cyan text-color=dark bold').classes('q-py-sm font-bold w-full max-w-sm')
                    
                    lote_review_container = ui.column().classes('w-full q-mt-md q-pa-md border border-gray-800 rounded bg-black/20')
                    with lote_review_container:
                        render_lote_review_form()
