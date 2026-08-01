# modules/comsoc_demandas.py
from datetime import datetime
import json
import urllib.parse
from nicegui import ui, app, run
import theme
from database import get_db_connection, get_service_db_connection
import ai_helper

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

def render_page(autofill: str = None):
    ui.label('📋 FLUXO BILATERAL DE DEMANDAS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_approver = user_role in ('admin', 'supervisor')
    is_internal_staff = user_role in ('admin', 'supervisor', 'oficial_gab', 'praca_gab', 'comsoc', 'comsoc_design', 'operador')
    user_name_guerra = user_data.get('nome_guerra', 'Operador').upper()

    # Estado local do formulário de viabilidade
    form_state = {
        'cobertura_foto': False,
        'cobertura_video': False,
        'cobertura_redes': False,
        'viabilidade_staff': False,
        'viabilidade_equip': False,
        'viabilidade_drone': False,
        'viabilidade_transp': False,
        'viabilidade_credencial': False,
        'viabilidade_anteced': False,
        'viabilidade_briefing': False,
        'notificar_militares': []
    }

    # Referências para binds/autofill
    sol_nome = None
    sol_setor = None
    sol_contato = None
    ev_titulo = None
    ev_data = None
    ev_data_fim = None
    ev_hora = None
    ev_local = None
    ev_aut = None
    ev_entrega_tipo = None
    score_label = None
    militar_select = None
    
    # Referências para uploads
    uploaded_file_url = None
    uploaded_file_name = None
    upload_status_lbl = None

    # Checkboxes individuais de checklist
    chk_staff = None
    chk_equip = None
    chk_drone = None
    chk_transp = None
    chk_cred = None
    chk_anteced = None
    chk_briefing = None

    # Checkboxes de cobertura
    chk_foto = None
    chk_video = None
    chk_redes = None
    chk_sigilo = None

    # Campos de reenvio/ajustes
    edit_id = None  # Se preenchido, estamos editando uma demanda existente devolvida para ajustes

    def calcular_score():
        # Checklist de viabilidade: 7 itens
        itens_viabilidade = sum([
            form_state['viabilidade_staff'],
            form_state['viabilidade_equip'],
            form_state['viabilidade_drone'],
            form_state['viabilidade_transp'],
            form_state['viabilidade_credencial'],
            form_state['viabilidade_anteced'],
            form_state['viabilidade_briefing']
        ])
        
        # Base de esforço reversa: quanto mais itens checkados, menor o risco/esforço operacional
        if itens_viabilidade >= 6:
            score_base = 1.0  # Viável / Baixo risco
        elif itens_viabilidade >= 4:
            score_base = 2.5  # Médio esforço
        elif itens_viabilidade >= 2:
            score_base = 4.0  # Alto esforço
        else:
            score_base = 5.0  # Crítico / Altíssimo esforço
            
        # Modificadores de escopo de cobertura
        coberturas_selecionadas = sum([
            form_state['cobertura_foto'],
            form_state['cobertura_video'],
            form_state['cobertura_redes']
        ])
        
        score_final = score_base + (coberturas_selecionadas * 0.4)
        if score_final > 5.0:
            score_final = 5.0
            
        return round(score_final, 1)

    def atualizar_score_ui():
        if score_label:
            val = calcular_score()
            if val <= 2.0:
                lbl_text = f"🟢 Score: {val} (Baixo Esforço)"
            elif val <= 3.5:
                lbl_text = f"🟡 Score: {val} (Médio Esforço)"
            else:
                lbl_text = f"🔴 Score: {val} (Alto Esforço)"
            score_label.text = lbl_text

    def popular_form_ia(dados_json):
        """Popula os campos do formulário a partir do JSON gerado pela IA."""
        try:
            dados = json.loads(dados_json)
            if sol_nome: sol_nome.value = dados.get('solicitante_nome', '')
            if sol_setor: sol_setor.value = dados.get('setor', '')
            if sol_contato: sol_contato.value = dados.get('contato', '')
            if ev_titulo: ev_titulo.value = dados.get('titulo_evento', '')
            if ev_data: ev_data.value = dados.get('data_evento', '')
            if ev_hora: ev_hora.value = dados.get('hora_evento', '')
            if ev_local: ev_local.value = dados.get('local_evento', '')
            if ev_aut: ev_aut.value = dados.get('autoridades', '')
            
            ui.notify('✨ Dados processados e preenchidos no formulário!', color='success')
        except Exception as e:
            ui.notify(f'Erro ao preencher dados da IA: {e}', color='red')

    def copiar_checklist_whatsapp():
        ui.run_javascript(f"navigator.clipboard.writeText({repr(CHECKLIST_TEMPLATE)})")
        ui.notify("📋 Questionário copiado! Envie ao solicitante.", color="success")

    def gerar_link_google_calendar(d):
        """Gera URL para adicionar o evento ao Google Calendar."""
        titulo = urllib.parse.quote(f"COBERTURA COMSOC: {d['titulo_evento']}")
        detalhes = urllib.parse.quote(f"Solicitante: {d['solicitante_nome']} ({d['setor']})\nAutoridades: {d['autoridades']}\nScore de Esforço: {d['score_esforco']}")
        local = urllib.parse.quote(d['local_evento'])
        
        # Datas no formato AAAAMMDD/AAAAMMDD
        data_res = d['data_evento'].replace('-', '')
        hora_res = d['hora_evento'].replace(':', '') + '00'
        dates = f"{data_res}T{hora_res}/{data_res}T{int(hora_res)+20000:06d}" # adiciona 2h padrão
        
        return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={titulo}&dates={dates}&details={detalhes}&location={local}"

    @ui.refreshable
    def render_content():
        # Busca efetivo militar do banco para notificação / designação de equipe
        efetivo_options = {}
        db_ef = get_service_db_connection() or get_db_connection()
        if db_ef:
            try:
                res_ef = db_ef.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
                if res_ef.data:
                    try:
                        from database import sort_efetivo_list
                        sorted_ef = sort_efetivo_list(res_ef.data)
                    except Exception:
                        sorted_ef = res_ef.data
                    
                    efetivo_options = {
                        str(item['id']): f"{(item.get('posto_grad') or '').strip()} {(item.get('nome_guerra') or '').strip()} ({(item.get('role') or 'membro').upper()})".strip()
                        for item in sorted_ef if item.get('nome_guerra')
                    }
            except Exception as e:
                print(f"[EFETIVO LOAD ERR] {e}")

        # Fallback local via SQLite se o Supabase estiver offline/vazio
        if not efetivo_options:
            try:
                from sqlite_adapter import SQLiteDatabaseAdapter
                local_db = SQLiteDatabaseAdapter()
                res_ef = local_db.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
                if res_ef.data:
                    efetivo_options = {
                        str(item['id']): f"{(item.get('posto_grad') or '').strip()} {(item.get('nome_guerra') or '').strip()} ({(item.get('role') or 'membro').upper()})".strip()
                        for item in res_ef.data if item.get('nome_guerra')
                    }
            except Exception as loc_err:
                print(f"[EFETIVO LOCAL LOAD ERR] {loc_err}")

        with ui.column().classes('w-full gap-4'):


            # ⚡ BARRA SUPERIOR DE ATALHOS RÁPIDOS EM 1 CLIQUE (PACOTES TEMÁTICOS)
            with ui.card().classes('w-full q-pa-sm px-4 no-shadow rounded-xl bg-black/40 border border-cyan-500/30 q-mb-xs'):
                with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                    ui.label('⚡ PACOTES DE ATALHO RÁPIDO (1 Clique):').classes('text-xs font-bold text-amber tracking-wider')
                    with ui.row().classes('items-center gap-2 wrap'):
                        def aplicar_pacote_solenidade_vip():
                            categoria_demanda.value = ['audiovisual', 'design_arte', 'redacao_textos']
                            tipo_cobertura.value = ['foto', 'video', 'drone', 'cardapio_design', 'discurso']
                            ev_entrega_tipo.value = 'captacao_e_edicao'
                            ev_titulo.value = 'SOLENIDADE MILITAR / PASSAGEM DE COMANDO'
                            ui.notify('🌟 Pacote Solenidade VIP Aplicado! (Foto + Vídeo + Drone + Cardápio + Discurso)', color='info')

                        def aplicar_pacote_almoco():
                            categoria_demanda.value = ['design_arte', 'impressos_albuns', 'brindes_lembrancas']
                            tipo_cobertura.value = ['cardapio_design', 'impressao_cardapio', 'kit_lembranca']
                            ev_entrega_tipo.value = 'impressao_fisica'
                            ev_titulo.value = 'ALMOÇO OFICIAL DE AUTORIDADES'
                            ui.notify('🍽️ Pacote Almoço Aplicado! (Cardápio + Paspatur + Brindes RP)', color='info')

                        def aplicar_pacote_reels():
                            categoria_demanda.value = ['audiovisual', 'redacao_textos']
                            tipo_cobertura.value = ['video', 'redes', 'release_prensa']
                            ev_entrega_tipo.value = 'captacao_e_edicao'
                            ev_titulo.value = 'COBERTURA REELS & REDES SOCIAIS'
                            ui.notify('📱 Pacote Mídias & Reels Aplicado! (Vídeo + Reels + Release)', color='info')

                        def aplicar_pacote_paspatur():
                            categoria_demanda.value = ['impressos_albuns', 'design_arte']
                            tipo_cobertura.value = ['quadro_paspatur', 'placa_paspatur_design']
                            ev_entrega_tipo.value = 'impressao_fisica'
                            ev_titulo.value = 'PASPATUR E MOLDURAS PARA HOMENAGEM'
                            ui.notify('🖼️ Pacote Paspatur Aplicado!', color='info')

                        def aplicar_pacote_discurso():
                            categoria_demanda.value = ['redacao_textos']
                            tipo_cobertura.value = ['discurso', 'materia_noticia']
                            ev_entrega_tipo.value = 'captacao_e_edicao'
                            ev_titulo.value = 'DISCURSO DE POSSE / ORDEM DO DIA'
                            ui.notify('📜 Pacote Redação Aplicado!', color='info')

                        ui.button('🌟 Solenidade VIP', on_click=aplicar_pacote_solenidade_vip).props('unelevated color=amber-9 text-color=black dense').classes('text-xs font-bold q-px-sm')
                        ui.button('🍽️ Almoço Oficial', on_click=aplicar_pacote_almoco).props('unelevated color=orange-9 text-color=white dense').classes('text-xs font-bold q-px-sm')
                        ui.button('📱 Mídias & Reels', on_click=aplicar_pacote_reels).props('unelevated color=pink-9 text-color=white dense').classes('text-xs font-bold q-px-sm')
                        ui.button('🖼️ Paspatur / Quadro', on_click=aplicar_pacote_paspatur).props('unelevated color=cyan-9 text-color=black dense').classes('text-xs font-bold q-px-sm')
                        ui.button('📜 Discurso', on_click=aplicar_pacote_discurso).props('unelevated color=purple-9 text-color=white dense').classes('text-xs font-bold q-px-sm')

            # 🤖 CARD 1: Assistente de Entrada & Triagem com IA (2 Modos)
            with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl bg-black/40 border border-cyan-500/20 q-mb-xs'):
                with ui.expansion('🤖 Assistente de Entrada / Triagem com IA (2 Modos)', icon='psychology', value=False).classes('w-full font-bold text-cyan').style('color: #00e5ff;'):
                    with ui.column().classes('w-full q-pa-md gap-3'):
                        
                        # Topo: Seletor de Modelo Gemini dinâmico e persistente (Modelos Ativos Apenas)
                        with ui.row().classes('w-full items-center justify-between no-wrap border-b border-cyan-500/20 q-pb-xs q-mb-xs'):
                            ui.label('SELECIONE O MOTOR DE IA:').classes('text-[11px] font-bold text-cyan tracking-wider')
                            modelos_disponiveis = ai_helper.get_available_gemini_models()
                            modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                            if modelo_salvo not in modelos_disponiveis:
                                modelo_salvo = list(modelos_disponiveis.keys())[0] if modelos_disponiveis else 'gemini-2.0-flash'
                                app.storage.user['preferred_gemini_model'] = modelo_salvo
                                
                            model_select_ia = ui.select(
                                modelos_disponiveis,
                                value=modelo_salvo,
                                on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                            ).props('dark outlined dense options-dark').classes('w-52 text-[10px]').style('max-height: 28px;')

                        # Sub-abas de escolha de modo
                        with ui.tabs().classes('w-full text-cyan dense') as ai_tabs:
                            tab_indiv = ui.tab('📋 Questionário Individual (1 Pauta)').classes('text-xs')
                            tab_lote_dem = ui.tab('📅 Lista Semanal / Múltiplas Pautas (Lote)').classes('text-xs')

                        with ui.tab_panels(ai_tabs, value=tab_indiv).classes('w-full bg-transparent no-shadow gap-0 q-pt-sm'):
                            
                            # ── MODO 1: QUESTIONÁRIO INDIVIDUAL ──
                            with ui.tab_panel(tab_indiv).classes('p-0 gap-3 w-full'):
                                ui.label('Cole a mensagem bruta com as respostas do solicitante no campo abaixo. O Gemini analisará o texto e preencherá o formulário individual automaticamente.').classes('text-xs text-grey-4')
                                
                                raw_input = ui.textarea(
                                    placeholder='Cole a mensagem recebida com as respostas do questionário aqui...'
                                ).props('dark outlined w-full rows=3').classes('w-full text-xs')
                                
                                async def processar_texto_ia():
                                    text = raw_input.value.strip()
                                    if not text:
                                        ui.notify('Cole o texto das respostas primeiro!', color='warning')
                                        return
                                    ui.notify('Gemini analisando questionário...', color='info')
                                    
                                    selected_model = model_select_ia.value or 'gemini-2.0-flash'
                                    ai_helper.GEMINI_MODEL_NAME = selected_model
                                    
                                    try:
                                        response_json = await run.io_bound(ai_helper.digest_demand_questionnaire, text)
                                        popular_form_ia(response_json)
                                    except Exception as err:
                                        err_msg = str(err)
                                        if "429" in err_msg or "quota" in err_msg.lower():
                                            ui.notify('⚠️ Cota excedida no modelo atual! Selecione outro modelo acima e tente novamente.', color='warning', duration=8)
                                        else:
                                            ui.notify(f'Erro na digestão: {err}', color='danger')
                                            
                                with ui.row().classes('w-full justify-between items-center q-mt-xs'):
                                    ui.button(
                                        'Copiar Questionário WhatsApp', 
                                        icon='content_copy', 
                                        on_click=copiar_checklist_whatsapp
                                    ).props('unelevated color=primary text-color=black bold dense').classes('text-[10px] q-px-sm')
                                    
                                    ui.button(
                                        'Processar e Preencher',
                                        icon='psychology',
                                        on_click=processar_texto_ia
                                    ).props('unelevated color=cyan text-color=black bold dense').classes('text-[10px] q-px-sm')

                            # ── MODO 2: LISTA SEMANAL / MÚLTIPLAS PAUTAS (LOTE) ──
                            with ui.tab_panel(tab_lote_dem).classes('p-0 gap-3 w-full'):
                                ui.label('Cole um texto livre (pauta semanal, mensagens do WhatsApp, e-mail) contendo vários eventos. A IA extrairá todas as pautas e permitirá revisar antes de cadastrar tudo na agenda de uma vez.').classes('text-xs text-grey-4')
                                
                                lote_input_dem = ui.textarea(
                                    placeholder='Ex: Pautas da semana:\n1. Formatura matutina dia 28/07 às 09:00h no pátio principal, uniforme 3.2, presença do Comandante-Geral.\n2. Reunião de pauta no gabinete dia 29/07 às 14:00h para planejar coberturas.'
                                ).props('dark outlined rows=4').classes('w-full text-xs')
                                
                                state_lote_dem = {'eventos': [], 'loading': False, 'error': None}
                                
                                @ui.refreshable
                                def render_lote_review_dem():
                                    if state_lote_dem['loading']:
                                        with ui.column().classes('w-full items-center justify-center q-pa-md'):
                                            ui.spinner(color='cyan', size='md')
                                            ui.label('Extraindo e destrinchando eventos com IA...').classes('text-xs text-cyan text-center font-bold q-mt-xs')
                                        return
                                    
                                    if state_lote_dem['error']:
                                        ui.label(f"Erro ao extrair lote: {state_lote_dem['error']}").classes('text-red text-xs q-pa-sm')
                                        return

                                    if not state_lote_dem['eventos']:
                                        ui.label('⚠️ Nenhum evento foi identificado no texto ou a resposta veio vazia. Verifique se o texto contém datas/eventos ou tente selecionar outro modelo de IA acima.').classes('text-xs text-amber q-pa-sm italic')
                                        return
                                    
                                    ui.label(f"✨ EVENTOS EXTRAÍDOS ({len(state_lote_dem['eventos'])}):").classes('text-xs font-bold text-cyan border-b border-gray-800 w-full q-pb-xs q-my-xs')
                                    
                                    # Prepara opções do efetivo para o dropdown
                                    mil_opts = {'': '-- Não designado (Escolha Posterior) --'}
                                    for m_id, m_label in efetivo_options.items():
                                        mil_opts[str(m_id)] = m_label

                                    for index, ev in enumerate(state_lote_dem['eventos']):
                                        with ui.card().classes('w-full q-pa-xs border border-cyan-500/30 rounded bg-black/30 q-mb-xs').style('border-left: 4px solid #00e5ff;'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap border-b border-gray-800/50 q-pb-xs'):
                                                ui.label(f"Pauta #{index + 1}").classes('text-[11px] font-bold text-cyan')
                                                ui.button(
                                                    icon='delete', 
                                                    on_click=lambda idx=index: (state_lote_dem['eventos'].pop(idx), render_lote_review_dem.refresh())
                                                ).props('flat round dense color=red').classes('text-xs')
                                            
                                            with ui.grid(columns=1).classes('w-full gap-1 sm:grid-cols-2 md:grid-cols-4 q-mt-xs'):
                                                t = ui.input('Título', value=ev.get('titulo_evento', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                t.bind_value(ev, 'titulo_evento')
                                                
                                                d = ui.input('Data (AAAA-MM-DD)', value=ev.get('data_evento', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                d.bind_value(ev, 'data_evento')
                                                
                                                h = ui.input('Hora (HH:MM)', value=ev.get('hora_evento', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                h.bind_value(ev, 'hora_evento')
                                                
                                                l = ui.input('Local', value=ev.get('local_evento', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                l.bind_value(ev, 'local_evento')
                                                
                                                s = ui.input('Solicitante', value=ev.get('solicitante_nome', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                s.bind_value(ev, 'solicitante_nome')
                                                
                                                a = ui.input('Autoridades', value=ev.get('autoridades', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                a.bind_value(ev, 'autoridades')

                                                # 📂 Categoria da Demanda (Multi-Seleção)
                                                cat_val = ev.get('categoria_demanda') or ['audiovisual']
                                                if isinstance(cat_val, str):
                                                    try: cat_val = json.loads(cat_val)
                                                    except: cat_val = [cat_val]
                                                if not isinstance(cat_val, list):
                                                    cat_val = ['audiovisual']

                                                cat_sel = ui.select(
                                                    options={
                                                        'audiovisual': '📸 Cobertura Audiovisual',
                                                        'design_arte': '🎨 Design / Gráficas',
                                                        'impressos_albuns': '📕 Impressos & Encadernação',
                                                        'brindes_lembrancas': '🎁 Brindes & Lembranças',
                                                        'redacao_textos': '✍️ Redação & Discursos',
                                                        'suporte_evento': '📦 Suporte Logístico',
                                                        'outra_tarefa': '⚡ Outra Tarefa'
                                                    },
                                                    value=cat_val,
                                                    label='📂 Categoria(s)',
                                                    multiple=True,
                                                    clearable=True
                                                ).props('dark outlined dense option-dark').classes('w-full text-[11px]')
                                                cat_sel.bind_value(ev, 'categoria_demanda')

                                                # 📷 Serviços / Subcategorias (Multi-Seleção Dinâmica)
                                                cob_val = ev.get('tipo_cobertura', ['foto'])
                                                if isinstance(cob_val, str):
                                                    try: cob_val = json.loads(cob_val)
                                                    except: cob_val = [cob_val]
                                                if not isinstance(cob_val, list):
                                                    cob_val = ['foto']

                                                def get_service_options_for_categories(cats):
                                                    if isinstance(cats, str): cats = [cats]
                                                    if not cats: cats = ['audiovisual']
                                                    servs_map = {
                                                        'audiovisual': {
                                                            'foto': '📸 Cobertura Fotográfica',
                                                            'video': '🎥 Gravação de Vídeo',
                                                            'redes': '📱 Redes Sociais / Reels',
                                                            'drone': '🛸 Imagens Aéreas (Drone)',
                                                            'transmissao': '📡 Transmissão ao Vivo'
                                                        },
                                                        'design_arte': {
                                                            'cardapio_design': '🍽️ Layout de Cardápio',
                                                            'banner_digital': '🖼️ Banner / Cartaz Digital',
                                                            'convite_artes': '✉️ Convite Digital / Panfleto',
                                                            'redes_design': '📲 Arte para Redes Sociais',
                                                            'placa_paspatur_design': '🏆 Layout Placa / Paspatur',
                                                            'brasao_selo': '🛡️ Brasão / Selo / Logotipo'
                                                        },
                                                        'impressos_albuns': {
                                                            'impressao_banner': '🖨️ Impressão de Banner / Lona',
                                                            'impressao_cardapio': '✂️ Impressão e Corte de Cardápio',
                                                            'quadro_paspatur': '🖼️ Moldura de Quadro / Paspatur',
                                                            'placa_homenagem': '🏅 Placa Acrílico / Metal',
                                                            'album_fotografico': '📘 Álbum Fotográfico'
                                                        },
                                                        'redacao_textos': {
                                                            'discurso': '📜 Discurso / Ordem do Dia',
                                                            'materia_noticia': '📰 Matéria Noticiário / Portal',
                                                            'release_prensa': '📢 Release para Imprensa',
                                                            'roteiro_video': '🎙️ Roteiro de Locução'
                                                        },
                                                        'brindes_lembrancas': {
                                                            'coin': '🪙 Coin / Moeda Comemorativa',
                                                            'kit_lembranca': '🎁 Kit Brinde Oficial',
                                                            'certificado': '📜 Certificados & Diplomas'
                                                        },
                                                        'suporte_evento': {
                                                            'credenciamento': '📇 Credenciamento Imprensa',
                                                            'som_audiovisual': '🎤 Sonorização / Microfones',
                                                            'receptivo': '🤝 Receptivo de Autoridades'
                                                        },
                                                        'outra_tarefa': {
                                                            'outra': '⚡ Outra Tarefa Especial'
                                                        }
                                                    }
                                                    res_opts = {}
                                                    for c in cats:
                                                        if c in servs_map:
                                                            res_opts.update(servs_map[c])
                                                    if not res_opts:
                                                        res_opts = dict(servs_map['audiovisual'])
                                                    return res_opts

                                                initial_cob_opts = get_service_options_for_categories(cat_val)
                                                for c_item in cob_val:
                                                    if c_item and c_item not in initial_cob_opts:
                                                        initial_cob_opts[c_item] = f"📌 {str(c_item).capitalize()}"

                                                cob_sel = ui.select(
                                                    options=initial_cob_opts,
                                                    value=cob_val,
                                                    label='📷 Serviços / Subcategorias',
                                                    multiple=True,
                                                    clearable=True
                                                ).props('dark outlined dense option-dark').classes('w-full text-[11px]')
                                                cob_sel.bind_value(ev, 'tipo_cobertura')

                                                def ao_mudar_categoria_card(e):
                                                    novas_opts = get_service_options_for_categories(e.value)
                                                    cur_vals = cob_sel.value or []
                                                    for c_item in cur_vals:
                                                        if c_item and c_item not in novas_opts:
                                                            novas_opts[c_item] = f"📌 {str(c_item).capitalize()}"
                                                    cob_sel.options = novas_opts
                                                    cob_sel.update()

                                                cat_sel.on_value_change(ao_mudar_categoria_card)

                                                # 🎯 Militar(es) Responsável(is) (Multi-Seleção)
                                                raw_mil = ev.get('militar_designado')
                                                mil_list = []
                                                if isinstance(raw_mil, list):
                                                    mil_list = [str(x).strip() for x in raw_mil if str(x).strip()]
                                                elif isinstance(raw_mil, str) and raw_mil.strip():
                                                    try:
                                                        parsed_mil = json.loads(raw_mil)
                                                        if isinstance(parsed_mil, list):
                                                            mil_list = [str(x).strip() for x in parsed_mil if str(x).strip()]
                                                        else:
                                                            mil_list = [raw_mil.strip()]
                                                    except Exception:
                                                        mil_list = [raw_mil.strip()]

                                                initial_mil_vals = []
                                                card_mil_opts = dict(mil_opts)

                                                for m_item in mil_list:
                                                    if m_item in mil_opts:
                                                        initial_mil_vals.append(m_item)
                                                    else:
                                                        found_k = None
                                                        for k, label in mil_opts.items():
                                                            if k and m_item.lower() in label.lower():
                                                                found_k = k
                                                                break
                                                        if found_k:
                                                            initial_mil_vals.append(found_k)
                                                        else:
                                                            initial_mil_vals.append(m_item)
                                                            card_mil_opts[m_item] = f"✏️ {m_item}"

                                                m_sel = ui.select(
                                                    options=card_mil_opts,
                                                    value=initial_mil_vals,
                                                    label='🎯 Militar(es) Responsável(is)',
                                                    multiple=True,
                                                    with_input=True,
                                                    clearable=True
                                                ).props('dark outlined dense option-dark new-value-mode=add').classes('w-full text-[11px]')
                                                m_sel.bind_value(ev, 'militar_designado')

                                                obs = ui.input('Observações', value=ev.get('observacoes_execucao', '')).props('dark outlined dense').classes('w-full text-[11px]')
                                                obs.bind_value(ev, 'observacoes_execucao')
                                
                                    with ui.row().classes('w-full justify-center q-mt-sm'):
                                        ui.button(
                                            'Confirmar e Cadastrar Todos na Agenda',
                                            icon='playlist_add_check',
                                            on_click=salvar_lote_agenda_dem
                                        ).props('unelevated color=green text-color=black bold dense').classes('q-py-xs text-xs font-black w-full')

                                async def extrair_lote_ia_dem():
                                    text = lote_input_dem.value.strip()
                                    if not text:
                                        ui.notify('Cole o texto da lista semanal primeiro!', color='warning')
                                        return
                                    
                                    state_lote_dem['loading'] = True
                                    state_lote_dem['error'] = None
                                    render_lote_review_dem.refresh()
                                    
                                    try:
                                        ai_helper.GEMINI_MODEL_NAME = model_select_ia.value or 'gemini-3.6-flash'
                                        res_json = await run.io_bound(ai_helper.parse_multiple_events, text)
                                        state_lote_dem['eventos'] = json.loads(res_json)
                                        state_lote_dem['loading'] = False
                                        render_lote_review_dem.refresh()
                                    except Exception as err:
                                        state_lote_dem['loading'] = False
                                        state_lote_dem['error'] = str(err)
                                        render_lote_review_dem.refresh()
                                        ui.notify(f'Falha ao processar lista: {err}', color='warning')

                                async def salvar_lote_agenda_dem():
                                    db = get_service_db_connection() or get_db_connection()
                                    if not db:
                                        ui.notify('Sem conexão com o banco de dados.', color='red')
                                        return
                                    
                                    try:
                                        payloads = []
                                        for ev in state_lote_dem['eventos']:
                                            if not ev.get('titulo_evento') or not str(ev.get('titulo_evento')).strip():
                                                ui.notify('Todos os eventos precisam de um Título!', color='warning')
                                                return
                                            if not ev.get('data_evento'):
                                                ui.notify(f"Falta a data para o evento '{ev.get('titulo_evento')}'!", color='warning')
                                                return
                                            
                                            cobs = ev.get('tipo_cobertura', ['foto'])
                                            if isinstance(cobs, str):
                                                try: cobs = json.loads(cobs)
                                                except: cobs = [cobs]
                                            if not isinstance(cobs, list):
                                                cobs = ['foto']

                                            # Trata militar(es) designado(s)
                                            raw_m_des = ev.get('militar_designado')
                                            m_des_items = []
                                            if isinstance(raw_m_des, list):
                                                m_des_items = raw_m_des
                                            elif isinstance(raw_m_des, str) and raw_m_des.strip():
                                                m_des_items = [raw_m_des.strip()]

                                            notificar_ids = []
                                            obs_text = ev.get('observacoes_execucao') or ''

                                            for m_item in m_des_items:
                                                m_str = str(m_item).strip()
                                                if not m_str:
                                                    continue
                                                if m_str.isdigit():
                                                    notificar_ids.append(int(m_str))
                                                else:
                                                    found_id = None
                                                    for ef_id, ef_label in efetivo_options.items():
                                                        if m_str.lower() in ef_label.lower() or str(ef_id) == m_str:
                                                            found_id = ef_id
                                                            break
                                                    if found_id:
                                                        notificar_ids.append(int(found_id))
                                                    else:
                                                        tag_mil = f"[Responsável: {m_str}]"
                                                        if tag_mil not in obs_text:
                                                            obs_text = f"{tag_mil} {obs_text}".strip()
                                            
                                            # Trata observações e autoridades sem quebrar colunas do Supabase
                                            aut_val = str(ev.get('autoridades') or '').strip()
                                            if obs_text:
                                                if aut_val:
                                                    aut_val = f"{aut_val} | Obs: {obs_text}"
                                                else:
                                                    aut_val = f"Obs: {obs_text}"
                                            
                                            raw_cat = ev.get('categoria_demanda') or ['audiovisual']
                                            if isinstance(raw_cat, list):
                                                cat_dem = json.dumps(raw_cat) if len(raw_cat) > 1 else (raw_cat[0] if raw_cat else 'audiovisual')
                                            else:
                                                cat_dem = str(raw_cat)

                                            payloads.append({
                                                'solicitante_nome': ev.get('solicitante_nome') or 'COMSOC / GABINETE',
                                                'setor': ev.get('setor') or 'Gabinete',
                                                'contato': ev.get('contato') or 'Interno',
                                                'titulo_evento': str(ev.get('titulo_evento', '')).upper(),
                                                'categoria_demanda': cat_dem,
                                                'data_evento': ev.get('data_evento'),
                                                'data_fim': ev.get('data_evento'),
                                                'hora_evento': ev.get('hora_evento') or '09:00',
                                                'local_evento': ev.get('local_evento') or 'Quartel / Gabinete',
                                                'tipo_cobertura': json.dumps(cobs),
                                                'autoridades': aut_val,
                                                'score_esforco': 1.0,
                                                'sigiloso': int(ev.get('sigiloso', 0)),
                                                'status': 'aprovado',
                                                'captacao_entrega': 'captacao_e_edicao',
                                                'notificar_militar_ids': json.dumps(notificar_ids)
                                            })
                                        
                                        if not payloads:
                                            ui.notify('Nenhum evento na lista para salvar.', color='warning')
                                            return
                                        
                                        res = db.table('demandas_comunicacao').insert(payloads).execute()
                                        inserted_rows = res.data if res.data else []
                                        
                                        for r in inserted_rows:
                                            dem_id = r.get('id')
                                            if dem_id:
                                                hist = {
                                                    'demanda_id': dem_id,
                                                    'data_hora': datetime.now().isoformat(),
                                                    'usuario': app.storage.user.get('user_data', {}).get('nome_guerra', 'ASSISTENTE IA'),
                                                    'acao': 'Pauta Cadastrada em Lote (IA)',
                                                    'parecer': 'Evento importado diretamente em lote via Inteligência Artificial.'
                                                }
                                                db.table('demandas_historico_tramitacao').insert(hist).execute()
                                        
                                        try:
                                            from notifications_manager import notify_telegram
                                            alert_txt = (
                                                f"📅 **CADASTRO EM LOTE REALIZADO (IA)**\n\n"
                                                f"👤 Operador: {app.storage.user.get('user_data', {}).get('nome_guerra', 'ASSISTENTE IA')}\n"
                                                f"📂 Total: {len(payloads)} eventos cadastrados na agenda tática."
                                            )
                                            notify_telegram(alert_txt, "saude", role_required="admin")
                                        except Exception as tel_err:
                                            print(f"[TELEGRAM NOTIF ERR] {tel_err}")
                                        
                                        ui.notify(f"🎯 {len(payloads)} eventos cadastrados com sucesso na agenda!", color='success')
                                        
                                        state_lote_dem['eventos'] = []
                                        state_lote_dem['loading'] = False
                                        lote_input_dem.value = ''
                                        render_lote_review_dem.refresh()
                                    except Exception as save_err:
                                        ui.notify(f"Erro ao salvar lote: {save_err}", color='red')

                                with ui.row().classes('w-full justify-between items-center q-mt-xs'):
                                    ui.button(
                                        'Extrair e Destrinchar Eventos',
                                        icon='psychology',
                                        on_click=extrair_lote_ia_dem
                                    ).props('unelevated color=cyan text-color=black bold dense').classes('text-[10px] q-px-sm')
                                
                                render_lote_review_dem()

            # 📝 CARD 2: Formulário Unificado com 2 colunas horizontais no Desktop
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
            ):
                ui.label('📝 Formulário da Demanda / Pauta COMSOC').classes('text-md font-bold text-cyan q-mb-md')
                
                with ui.row().classes('w-full gap-6 items-start wrap-mobile'):
                    
                    # COLUNA DA ESQUERDA (Dados Principais)
                    with ui.column().classes('col-12 col-md gap-3').style('flex: 1; min-width: 320px;'):
                        nonlocal sol_nome, sol_setor, sol_contato, ev_titulo, ev_data, ev_data_fim, ev_hora, ev_local, ev_aut, ev_entrega_tipo, militar_select, uploaded_file_url, uploaded_file_name, upload_status_lbl, chk_sigilo
                        nonlocal chk_staff, chk_equip, chk_drone, chk_transp, chk_cred, chk_anteced, chk_briefing, chk_foto, chk_video, chk_redes, score_label
                        
                        ui.label('🎯 Detalhes do Serviço').classes('text-xs font-bold text-amber')
                        
                        # Categoria Múltipla e Produto Específico
                        with ui.row().classes('w-full gap-2 wrap sm:no-wrap'):
                            categoria_demanda = ui.select(
                                {
                                    'audiovisual': '📸 Cobertura Audiovisual',
                                    'design_arte': '🎨 Design / Arte Visual',
                                    'impressos_albuns': '📕 Impressos & Encadernação',
                                    'redacao_textos': '✍️ Redação & Discursos',
                                    'brindes_lembrancas': '🎁 Brindes & Lembranças',
                                    'suporte_evento': '📦 Suporte Logístico / Receptivo',
                                    'outra_tarefa': '⚡ Outra Tarefa Especial'
                                },
                                value=['design_arte'],
                                label='Categoria(s) da Demanda',
                                multiple=True,
                                clearable=True
                            ).props('dark outlined dense option-dark use-chips').classes('w-full sm:w-1/2 font-bold text-cyan')

                            produto_especifico = ui.input('Especificação da Peça / Produto', placeholder='Ex: Cardápio Almoço, Paspatur A4, Vídeo Reels').props('dark outlined dense').classes('w-full sm:w-1/2')

                        # Título da demanda
                        ev_titulo = ui.input('Título Geral da Tarefa / Solenidade').props('dark outlined dense w-full')

                        # Solicitante + Setor + Contato
                        with ui.row().classes('w-full gap-2 wrap sm:no-wrap'):
                            sol_nome = ui.input('Solicitante', value='CGCFN / GABINETE').props('dark outlined dense').classes('w-full sm:w-1/3')
                            sol_setor = ui.input('Setor / OM', value='CGCFN').props('dark outlined dense').classes('w-full sm:w-1/3')
                            sol_contato = ui.input('Contato / Ramal', value='Interno').props('dark outlined dense').classes('w-full sm:w-1/3')

                        # Prioridade + Deadline + Formato Entrega
                        with ui.row().classes('w-full gap-2 wrap sm:no-wrap'):
                            prioridade_select = ui.select(
                                {
                                    'normal': '🟢 Normal',
                                    'urgente': '🟡 Urgente',
                                    'altissima': '🔴 ALTÍSSIMA / GAB'
                                },
                                value='normal',
                                label='Prioridade'
                            ).props('dark outlined dense option-dark').classes('w-full sm:w-1/3')

                            prazo_limite = ui.input('Prazo / Deadline', value=datetime.now().strftime('%Y-%m-%d')).props('type=date dark outlined dense').classes('w-full sm:w-1/3')

                            ev_entrega_tipo = ui.select(
                                {
                                    'apenas_captacao_bruto': 'Bruto / Sem Edição',
                                    'captacao_e_edicao': 'Peça Finalizada',
                                    'impressao_fisica': 'Impressão Física'
                                },
                                value='captacao_e_edicao',
                                label='Formato Entrega'
                            ).props('dark outlined dense option-dark').classes('w-full sm:w-1/3')

                        # Sigilo Checkbox
                        chk_sigilo = ui.checkbox('Pauta Sigilosa / Reservada (Gabinete)').classes('text-xs text-amber-5')

                        # 📷 SELETOR DE SERVIÇOS & SUBCATEGORIAS MULTIPLAS
                        def get_service_options_for_categories(cats):
                            if isinstance(cats, str): cats = [cats]
                            if not cats: cats = ['design_arte']
                            servs_map = {
                                'audiovisual': {
                                    'foto': '📸 Cobertura Fotográfica',
                                    'video': '🎥 Gravação de Vídeo',
                                    'redes': '📱 Redes Sociais / Reels',
                                    'drone': '🛸 Imagens Aéreas (Drone)',
                                    'transmissao': '📡 Transmissão ao Vivo'
                                },
                                'design_arte': {
                                    'cardapio_design': '🍽️ Layout de Cardápio',
                                    'banner_digital': '🖼️ Banner / Cartaz Digital',
                                    'convite_artes': '✉️ Convite Digital / Panfleto',
                                    'redes_design': '📲 Arte para Redes Sociais',
                                    'placa_paspatur_design': '🏆 Layout Placa / Paspatur'
                                },
                                'impressos_albuns': {
                                    'impressao_banner': '🖨️ Impressão de Banner / Lona',
                                    'impressao_cardapio': '✂️ Impressão de Cardápio',
                                    'quadro_paspatur': '🖼️ Moldura / Paspatur A4',
                                    'album_fotografico': '📘 Álbum Fotográfico'
                                },
                                'redacao_textos': {
                                    'discurso': '📜 Discurso / Ordem do Dia',
                                    'materia_noticia': '📰 Matéria para Portal',
                                    'release_prensa': '📢 Release para Imprensa'
                                },
                                'brindes_lembrancas': {
                                    'coin': '🪙 Moeda Comemorativa',
                                    'kit_lembranca': '🎁 Kit Brinde Oficial RP'
                                },
                                'suporte_evento': {
                                    'credenciamento': '📇 Credenciamento Imprensa',
                                    'som_audiovisual': '🎤 Sonorização / Evento'
                                }
                            }
                            res = {}
                            for c in cats:
                                if c in servs_map: res.update(servs_map[c])
                            return res if res else servs_map['design_arte']

                        tipo_cobertura = ui.select(
                            options=get_service_options_for_categories(['design_arte']),
                            value=['cardapio_design'],
                            label='📷 Serviços & Pecas Específicas',
                            multiple=True,
                            clearable=True
                        ).props('dark outlined dense option-dark use-chips').classes('w-full font-bold text-cyan q-my-xs')

                        # ── SEÇÕES DINÂMICAS GRADUAIS POR CATEGORIA ──
                        
                        # 1. Seção Audiovisual
                        with ui.column().classes('w-full gap-2 p-3 bg-black/30 rounded-lg border border-cyan-500/20 q-my-xs') as campos_audiovisual_container:
                            campos_audiovisual_container.set_visibility(False)
                            ui.label('📸 Detalhes do Evento (Audiovisual):').classes('text-xs font-bold text-cyan')
                            
                            with ui.row().classes('w-full gap-2 wrap sm:no-wrap'):
                                ev_data = ui.input('Data Início').props('type=date dark outlined dense').classes('w-full sm:w-1/3')
                                ev_data_fim = ui.input('Data Término').props('type=date dark outlined dense').classes('w-full sm:w-1/3')
                                ev_hora = ui.input('Hora Início').props('type=time dark outlined dense').classes('w-full sm:w-1/3')
                                
                            ev_local = ui.input('Local Exato do Evento').props('dark outlined dense w-full')
                            ev_aut = ui.input('Autoridades Presentes').props('dark outlined dense w-full')

                        # 2. Seção Design & Impressos
                        with ui.column().classes('w-full gap-2 p-3 bg-black/30 rounded-lg border border-purple-500/20 q-my-xs') as container_sec_design:
                            container_sec_design.set_visibility(False)
                            ui.label('🎨 Especificações de Design & Gráfica:').classes('text-xs font-bold text-purple-4')
                            ui.label('Indique observações sobre dimensões, formato de impressão, cores e padrão visual.').classes('text-[11px] text-grey-4')

                        # 3. Seção Redação & Texto
                        with ui.column().classes('w-full gap-2 p-3 bg-black/30 rounded-lg border border-emerald-500/20 q-my-xs') as container_sec_redacao:
                            container_sec_redacao.set_visibility(False)
                            ui.label('✍️ Diretrizes de Redação & Discurso:').classes('text-xs font-bold text-emerald-4')
                            ui.label('Informe a pauta do discurso, ordem do dia, tom do texto e trechos indispensáveis.').classes('text-[11px] text-grey-4')

                        # Reação de Abertura Gradual ao mudar Categorias
                        def ao_mudar_categorias(e):
                            cats = e.value or []
                            if isinstance(cats, str): cats = [cats]
                            
                            campos_audiovisual_container.set_visibility('audiovisual' in cats)
                            container_sec_design.set_visibility('design_arte' in cats or 'impressos_albuns' in cats)
                            container_sec_redacao.set_visibility('redacao_textos' in cats)
                            
                            novas_opts = get_service_options_for_categories(cats)
                            cur_vals = tipo_cobertura.value or []
                            if isinstance(cur_vals, str): cur_vals = [cur_vals]
                            for cv in cur_vals:
                                if cv and cv not in novas_opts:
                                    novas_opts[cv] = f"📌 {str(cv).capitalize()}"
                            tipo_cobertura.options = novas_opts
                            tipo_cobertura.update()

                        categoria_demanda.on_value_change(ao_mudar_categorias)

                    # COLUNA DA DIREITA (Execução, Anexos e Checklist)
                    with ui.column().classes('col-12 col-md gap-3').style('flex: 1; min-width: 320px;'):
                        ui.label('⚙️ Operacional & Execução').classes('text-xs font-bold text-cyan')

                        if is_internal_staff:
                            lbl_militar = '🎯 Designar Militar Responsável' if is_approver else '👤 Sugestão de Encarregado (Opcional)'
                            militar_select = ui.select(
                                efetivo_options,
                                multiple=True,
                                label=lbl_militar
                            ).props('dark outlined dense w-full option-dark').classes('w-full')
                        else:
                            militar_select = None

                        observacoes_exec = ui.textarea('📝 Briefing / Instruções de Execução').props('dark outlined dense w-full rows=2')

                        # Anexos
                        with ui.column().classes('w-full gap-1 p-2 bg-black/10 rounded-lg border border-white/5'):
                            ui.label('📎 Anexo (Briefing, Logotipos, Roteiro)').classes('text-[11px] font-bold text-grey-4')
                            
                            def handle_upload(e):
                                try:
                                    import os
                                    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'anexos_pautas')
                                    os.makedirs(folder, exist_ok=True)
                                    
                                    file_path = os.path.join(folder, e.name)
                                    with open(file_path, 'wb') as pf:
                                        pf.write(e.content.read())
                                    
                                    nonlocal uploaded_file_url, uploaded_file_name
                                    uploaded_file_url = f"/assets/anexos_pautas/{e.name}"
                                    uploaded_file_name = e.name
                                    upload_status_lbl.text = f"✅ Arquivo: {e.name} pronto para envio."
                                    ui.notify(f"Anexo carregado com sucesso: {e.name}!", color='success')
                                except Exception as ex:
                                    ui.notify(f"Erro no upload: {ex}", color='red')

                            ui.upload(
                                on_upload=handle_upload,
                                label='Escolher arquivo',
                                auto_upload=True
                            ).props('dark flat bordered text-color=white dense').classes('w-full text-xs').style('max-height: 60px;')
                            
                            upload_status_lbl = ui.label('Nenhum arquivo anexado').classes('text-[10px] text-grey-4 w-full text-center')

                        # Checklist de Suporte & Viabilidade (Apenas para Audiovisual)
                        with ui.column().classes('w-full gap-1 p-2 bg-black/25 rounded-lg border border-cyan-500/15') as checklist_card:
                            ui.label('🔍 Checklist de Viabilidade (Audiovisual)').classes('text-xs font-bold text-cyan')
                            
                            chk_staff = ui.checkbox('Pessoal disponível?', on_change=lambda e: (form_state.update({'viabilidade_staff': e.value}), atualizar_score_ui()))
                            chk_equip = ui.checkbox('Equipamento reservado?', on_change=lambda e: (form_state.update({'viabilidade_equip': e.value}), atualizar_score_ui()))
                            chk_drone = ui.checkbox('Necessita Drone?', on_change=lambda e: (form_state.update({'viabilidade_drone': e.value}), atualizar_score_ui()))
                            chk_transp = ui.checkbox('Transporte assegurado?', on_change=lambda e: (form_state.update({'viabilidade_transp': e.value}), atualizar_score_ui()))
                            chk_cred = ui.checkbox('Credenciamento de Imprensa?', on_change=lambda e: (form_state.update({'viabilidade_credencial': e.value}), atualizar_score_ui()))
                            chk_anteced = ui.checkbox('Antecedência suficiente?', on_change=lambda e: (form_state.update({'viabilidade_anteced': e.value}), atualizar_score_ui()))
                            chk_briefing = ui.checkbox('Briefing aprovado?', on_change=lambda e: (form_state.update({'viabilidade_briefing': e.value}), atualizar_score_ui()))
                            
                            ui.separator().style('background-color: rgba(255, 255, 255, 0.05); margin: 4px 0;')
                            
                            ui.label('📸 Escopo Adicional').classes('text-[10px] font-bold text-white')
                            with ui.row().classes('w-full gap-2'):
                                chk_foto = ui.checkbox('Foto', on_change=lambda e: (form_state.update({'cobertura_foto': e.value}), atualizar_score_ui()))
                                chk_video = ui.checkbox('Vídeo', on_change=lambda e: (form_state.update({'cobertura_video': e.value}), atualizar_score_ui()))
                                chk_redes = ui.checkbox('Redes', on_change=lambda e: (form_state.update({'cobertura_redes': e.value}), atualizar_score_ui()))
                            
                            score_label = ui.label('🟢 Score: 1.0 (Baixo Esforço)').classes('text-xs font-bold text-center w-full q-py-xs bg-black/30 rounded-md q-mt-xs')
                            atualizar_score_ui()

                        def checar_vis_checklist(v):
                            if isinstance(v, list): return 'audiovisual' in v
                            return v == 'audiovisual'
                        checklist_card.bind_visibility_from(categoria_demanda, 'value', backward=checar_vis_checklist)

                        # Botões de Ação
                        async def salvar_demanda(status_inicial='pendente', eh_evento_interno=False):
                            nome_sol = sol_nome.value or ('COMSOC / GABINETE' if eh_evento_interno else '')
                            if not nome_sol or not ev_titulo.value:
                                ui.notify('Por favor, preencha os campos obrigatórios (Título e Solicitante).', color='warning')
                                return
                                
                            cat_selected = categoria_demanda.value or ['design_arte']
                            if isinstance(cat_selected, str): cat_selected = [cat_selected]

                            if 'audiovisual' in cat_selected:
                                if not ev_data.value or not ev_local.value:
                                    ui.notify('Para Cobertura Audiovisual, a Data de Início e o Local Exato são obrigatórios!', color='warning')
                                    return
                                
                            db = get_service_db_connection() or get_db_connection()
                            if db:
                                try:
                                    coberturas = tipo_cobertura.value or []
                                    if isinstance(coberturas, str): coberturas = [coberturas]
                                    if form_state['cobertura_foto'] and 'foto' not in coberturas: coberturas.append('foto')
                                    if form_state['cobertura_video'] and 'video' not in coberturas: coberturas.append('video')
                                    if form_state['cobertura_redes'] and 'redes' not in coberturas: coberturas.append('redes')
                                    
                                    dt_ev = (ev_data.value if hasattr(ev_data, 'value') and ev_data.value else None) or prazo_limite.value or str(datetime.now().date())
                                    loc_ev = (ev_local.value if hasattr(ev_local, 'value') and ev_local.value else None) or 'Gabinete / CGCFN'

                                    aut_single = (ev_aut.value if hasattr(ev_aut, 'value') and ev_aut.value else '') or ''
                                    obs_single = (observacoes_exec.value if hasattr(observacoes_exec, 'value') and observacoes_exec.value else '') or ''
                                    if obs_single:
                                        if aut_single:
                                            aut_single = f"{aut_single} | Obs: {obs_single}"
                                        else:
                                            aut_single = f"Obs: {obs_single}"

                                    cat_final_db = json.dumps(cat_selected) if len(cat_selected) > 1 else (cat_selected[0] if cat_selected else 'design_arte')

                                    registro = {
                                        'solicitante_nome': nome_sol,
                                        'setor': sol_setor.value or ('GABINETE / QUARTEL' if eh_evento_interno else 'Gabinete'),
                                        'contato': sol_contato.value or 'Interno',
                                        'titulo_evento': ev_titulo.value.upper(),
                                        'categoria_demanda': cat_final_db,
                                        'produto_especifico': produto_especifico.value or '',
                                        'prioridade': prioridade_select.value or 'normal',
                                        'prazo_limite': prazo_limite.value or '',
                                        'data_evento': dt_ev,
                                        'data_fim': dt_ev,
                                        'hora_evento': (ev_hora.value if hasattr(ev_hora, 'value') and ev_hora.value else None) or '09:00',
                                        'local_evento': loc_ev,
                                        'tipo_cobertura': json.dumps(coberturas),
                                        'autoridades': aut_single,
                                        'score_esforco': calcular_score(),
                                        'sigiloso': 1 if chk_sigilo.value else 0,
                                        'status': 'aprovado' if eh_evento_interno else status_inicial,
                                        'captacao_entrega': ev_entrega_tipo.value or 'captacao_e_edicao',
                                        'notificar_militar_ids': json.dumps(militar_select.value) if (militar_select and militar_select.value) else '[]',
                                        'arquivo_url': uploaded_file_url,
                                        'arquivo_nome': uploaded_file_name
                                    }
                                    
                                    nonlocal edit_id
                                    if edit_id:
                                        db.table('demandas_comunicacao').update(registro).eq('id', edit_id).execute()
                                        hist = {
                                            'demanda_id': edit_id,
                                            'data_hora': datetime.now().isoformat(),
                                            'usuario': user_name_guerra,
                                            'acao': 'Reenviado para Avaliação',
                                            'parecer': 'Solicitação modificada e reenviada após pedido de ajustes.'
                                        }
                                        db.table('demandas_historico_tramitacao').insert(hist).execute()
                                        ui.notify('Demanda atualizada com sucesso!', color='success')
                                        edit_id = None
                                    else:
                                        res = db.table('demandas_comunicacao').insert(registro).execute()
                                        if eh_evento_interno:
                                            dem_id = res.data[0]['id'] if (res.data and isinstance(res.data, list) and len(res.data) > 0) else None
                                            if dem_id:
                                                hist = {
                                                    'demanda_id': dem_id,
                                                    'data_hora': datetime.now().isoformat(),
                                                    'usuario': user_name_guerra,
                                                    'acao': 'Pauta Aprovada Direto (Evento Interno)',
                                                    'parecer': 'Evento interno cadastrado diretamente na escala oficial do Quartel.'
                                                }
                                                db.table('demandas_historico_tramitacao').insert(hist).execute()
                                            ui.notify('🎖️ Nova Tarefa / Evento cadastrado e aprovado com sucesso!', color='success')
                                        else:
                                            ui.notify('📝 Solicitação enviada com sucesso! Aguardando aprovação.', color='success')
                                    
                                    try:
                                        from notifications_manager import notify_telegram
                                        titulo_ev = ev_titulo.value or 'Sem Título'
                                        data_ev = ev_data.value or 'N/I'
                                        hora_ev = ev_hora.value or 'N/I'
                                        local_ev = ev_local.value or 'N/I'
                                        nome_sol = sol_nome.value or 'N/I'
                                        status_txt = '✅ Aprovada (Evento Interno)' if eh_evento_interno else '⏳ Pendente (Aguardando Homologação)'
                                        notify_telegram(
                                            f"🆕 Nova Pauta via Web:\n"
                                            f"📌 {titulo_ev}\n"
                                            f"📅 {data_ev} às {hora_ev}\n"
                                            f"📍 {local_ev}\n"
                                            f"👤 Solicitante: {nome_sol}\n"
                                            f"📊 Status: {status_txt}",
                                            "system"
                                        )
                                    except Exception as tg_err:
                                        print(f"[TELEGRAM NOTIFY ERR] {tg_err}")

                                    sol_nome.value = 'CGCFN / GABINETE'
                                    ev_titulo.value = ''
                                    produto_especifico.value = ''
                                    observacoes_exec.value = ''
                                    if militar_select:
                                        militar_select.value = []
                                    render_content.refresh()
                                except Exception as ex:
                                    ui.notify(f'Erro ao salvar: {ex}', color='red')

                        with ui.row().classes('w-full gap-2 q-mt-sm justify-between no-wrap'):
                            ui.button(
                                '🎖️ Salvar & Aprovar Direto (Quartel)', 
                                icon='stars', 
                                on_click=lambda: salvar_demanda(status_inicial='aprovado', eh_evento_interno=True)
                            ).props('unelevated color=amber text-color=black bold').classes('col text-xs')
                            
                            ui.button(
                                '📝 Enviar Solicitação para Avaliação', 
                                icon='send', 
                                on_click=lambda: salvar_demanda(status_inicial='pendente', eh_evento_interno=False)
                            ).props('unelevated color=cyan text-color=black bold').classes('col text-xs')

    render_content()
    
    # Executa preenchimento se dados foram enviados via Query String (vêm do Assistente de IA)
    if autofill:
        ui.timer(0.2, lambda: popular_form_ia(autofill), once=True)
