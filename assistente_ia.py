from nicegui import ui, app, run
import theme
import ai_helper
from database import get_bot_db_connection, get_db_connection
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

        # Tabs Quasar responsivas para as 3 seções unificadas (fazem wrap automático abaixo)
        with ui.tabs().classes('w-full text-primary border-b border-gray-800 flex-wrap') as tabs:
            tab_chat = ui.tab('💬 Chat Geral & Dúvidas').classes('text-xs sm:text-sm')
            tab_redator = ui.tab('📝 Redator de Releases & Notas').classes('text-xs sm:text-sm')
            tab_demandas = ui.tab('📋 Triagem de Demandas (Questionários)').classes('text-xs sm:text-sm')

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

            # ABA 3: TRIAGEM DE DEMANDAS / QUESTIONÁRIOS
            with ui.tab_panel(tab_demandas).classes('p-0 gap-4 w-full'):
                with ui.card().classes('w-full q-pa-md border border-gray-800').style(f'background: {THEME["bg_panel"]}'):
                    with ui.row().classes('w-full justify-between items-center border-b border-gray-800 q-pb-sm q-mb-sm'):
                        with ui.row().classes('items-center gap-2'):
                            ui.label('📋 IMPORTADOR & DIGESTOR DE QUESTIONÁRIOS').classes('text-xs text-weight-bold text-primary cyber-title')
                            
                            # Seletor de Modelo Gemini dinâmico na Triagem
                            modelos_disponiveis = ai_helper.get_available_gemini_models()
                            modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                            if modelo_salvo not in modelos_disponiveis:
                                modelos_disponiveis[modelo_salvo] = f"{modelo_salvo} (Ativo)"
                                
                            triagem_model_select = ui.select(
                                modelos_disponiveis,
                                value=modelo_salvo,
                                on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                            ).props('dark outlined dense options-dark').classes('w-44 text-[10px]').style('max-height: 28px;')

                        ui.button(
                            'Copiar Questionário Padrão', 
                            icon='content_copy', 
                            on_click=lambda: (ui.run_javascript(f"navigator.clipboard.writeText({repr(CHECKLIST_TEMPLATE)})"), ui.notify("Questionário copiado!", color="success"))
                        ).props('flat dense color=cyan text-color=cyan size=sm')

                    ui.label('Cole a mensagem copiada do WhatsApp ou Telegram contendo as respostas brutas preenchidas pelo solicitante. A IA processará e preparará as informações estruturadas.').classes('text-xs text-grey-4 q-mb-md')
                    
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        triagem_input = ui.textarea(
                            placeholder='Cole a mensagem recebida com as respostas do questionário aqui...'
                        ).props('dark outlined w-full rows=6').classes('flex-grow')
                        
                        async def processar_triagem_ia():
                            text = triagem_input.value.strip()
                            if not text:
                                ui.notify('Cole o texto das respostas primeiro!', color='warning')
                                return
                            
                            # Limpa e mostra carregando
                            triagem_output.clear()
                            with triagem_output:
                                ui.spinner(color='cyan', size='md')
                                ui.label('Digerindo questionário...').classes('text-xs text-cyan')
                            
                            async def run_triagem():
                                try:
                                    ai_helper.GEMINI_MODEL_NAME = triagem_model_select.value or 'gemini-2.0-flash'
                                    res_json = await run.io_bound(ai_helper.digest_demand_questionnaire, text)
                                    parsed = json.loads(res_json)
                                    
                                    triagem_output.clear()
                                    with triagem_output:
                                        ui.label('✨ DADOS EXTRAÍDOS COM SUCESSO!').classes('text-xs font-bold text-cyan border-b border-gray-800 w-full q-pb-xs')
                                        with ui.grid(columns=2).classes('w-full gap-2 text-xs q-mt-md'):
                                            ui.label('Solicitante:').classes('text-grey-5')
                                            ui.label(parsed.get('solicitante_nome', 'N/I')).classes('text-white font-bold')
                                            
                                            ui.label('Setor/Divisão:').classes('text-grey-5')
                                            ui.label(parsed.get('setor', 'N/I')).classes('text-white font-bold')
                                            
                                            ui.label('Título da Pauta:').classes('text-grey-5')
                                            ui.label(parsed.get('titulo_evento', 'N/I')).classes('text-white font-bold')
                                            
                                            ui.label('Data/Hora:').classes('text-grey-5')
                                            ui.label(f"{parsed.get('data_evento', 'N/I')} às {parsed.get('hora_evento', 'N/I')}").classes('text-white font-bold')
                                            
                                            ui.label('Local:').classes('text-grey-5')
                                            ui.label(parsed.get('local_evento', 'N/I')).classes('text-white font-bold')
                                            
                                            ui.label('Autoridades:').classes('text-grey-5')
                                            ui.label(parsed.get('autoridades', 'N/I')).classes('text-white font-bold')
                                        
                                        ui.button(
                                            '⚡ Abrir Módulo de Demandas com esses dados preenchidos',
                                            on_click=lambda: ui.navigate.to(f'/comsoc_demandas?autofill={urllib.parse.quote(res_json)}')
                                        ).props('unelevated color=cyan text-color=black w-full q-mt-md').classes('font-bold')
                                except Exception as err:
                                    triagem_output.clear()
                                    with triagem_output:
                                        ui.label(f"Erro ao processar: {err}").classes('text-red text-xs')
                                        ui.notify('Ocorreu um erro no processamento. Tente outro modelo na barra acima.', color='warning')

                            ui.timer(0.1, run_triagem, once=True)

                        ui.button(
                            'Processar Respostas',
                            icon='psychology',
                            on_click=processar_triagem_ia
                        ).props('unelevated color=cyan text-color=black bold').classes('q-py-xl font-bold flex-shrink-0')
                    
                    triagem_output = ui.column().classes('w-full q-mt-md q-pa-md border border-gray-800 rounded bg-black/20')
                    with triagem_output:
                        ui.label('Os dados extraídos da triagem aparecerão aqui após processar o questionário.').classes('text-xs text-grey-5 italic text-center w-full')
