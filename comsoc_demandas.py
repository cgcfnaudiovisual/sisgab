# modules/comsoc_demandas.py
from datetime import datetime
import json
import urllib.parse
from nicegui import ui, app
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
        # Busca efetivo militar do banco para notificação
        efetivo_options = {}
        db = get_db_connection()
        if db:
            try:
                res_ef = db.table('efetivo').select('id, nome_guerra, role').execute()
                if res_ef.data:
                    efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
            except Exception as e:
                print(f"[EFETIVO LOAD ERR] {e}")

        with ui.column().classes('w-full gap-4'):
            # SEÇÃO SUPERIOR: ASSISTENTE DE ENTRADA COM IA (100% de largura)
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
            ):
                with ui.row().classes('w-full justify-between items-center q-mb-xs'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('🤖 Assistente de Entrada de Dados com IA').classes('text-md font-bold text-cyan')
                        
                        # Seletor de Modelo Gemini dinâmico para evitar rate limits
                        modelos_disponiveis = ai_helper.get_available_gemini_models()
                        modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                        if modelo_salvo not in modelos_disponiveis:
                            modelos_disponiveis[modelo_salvo] = f"{modelo_salvo} (Ativo)"
                            
                        # Carrega dropdown de modelos compacto
                        model_select_ia = ui.select(
                            modelos_disponiveis,
                            value=modelo_salvo,
                            on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                        ).props('dark outlined dense options-dark').classes('w-44 text-[10px]').style('max-height: 28px; margin-top: -2px;')
                    
                    ui.button(
                        'Copiar Questionário para WhatsApp/Telegram', 
                        icon='content_copy', 
                        on_click=copiar_checklist_whatsapp
                    ).props('unelevated color=primary text-color=black bold dense').classes('text-[10px] q-px-sm')
                
                ui.label('Cole a mensagem bruta com as respostas do solicitante no campo abaixo. O Gemini analisará o texto e preencherá todo o formulário automaticamente.').classes('text-xs text-grey-4 q-mb-md')
                
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    raw_input = ui.textarea(
                        placeholder='Cole a mensagem recebida com as respostas do questionário aqui...'
                    ).props('dark outlined w-full rows=3').classes('flex-grow')
                    
                    async def processar_texto_ia():
                        text = raw_input.value.strip()
                        if not text:
                            ui.notify('Cole o texto das respostas primeiro!', color='warning')
                            return
                        ui.notify('Gemini analisando questionário...', color='info')
                        
                        # Injeta temporariamente o modelo selecionado no cache do helper
                        selected_model = model_select_ia.value or 'gemini-2.0-flash'
                        ai_helper.GEMINI_MODEL_NAME = selected_model
                        
                        ans = await ui.run_javascript(f"Promise.resolve(true)")
                        try:
                            # Executa digestão usando o modelo escolhido
                            response_json = ai_helper.digest_demand_questionnaire(text)
                            popular_form_ia(response_json)
                        except Exception as err:
                            err_msg = str(err)
                            if "429" in err_msg or "quota" in err_msg.lower():
                                ui.notify('⚠️ Cota excedida no modelo atual! Selecione outro modelo ao lado e tente novamente.', color='warning', duration=8)
                            else:
                                ui.notify(f'Erro na digestão: {err}', color='danger')
                            
                    ui.button(
                        'Processar e Preencher',
                        icon='psychology',
                        on_click=processar_texto_ia
                    ).props('unelevated color=cyan text-color=black bold').classes('q-py-md font-bold flex-shrink-0')

            # SEÇÃO OPERACIONAL: FORMULÁRIO (Esquerda) E AJUSTES (Direita)
            with ui.row().classes('w-full gap-4 items-stretch justify-start'):
                # 1. Detalhes do Evento (Formulário Principal)
                with ui.column().classes('col-12 col-md-5 q-pa-none').style('min-width: 320px;'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                    ):
                        nonlocal sol_nome, sol_setor, sol_contato, ev_titulo, ev_data, ev_data_fim, ev_hora, ev_local, ev_aut, ev_entrega_tipo, militar_select, uploaded_file_url, uploaded_file_name, upload_status_lbl
                        
                        ui.label('📝 Detalhes do Evento').classes('text-md font-bold text-cyan q-mb-xs')
                        sol_nome = ui.input('Nome do Solicitante').props('dark outlined dense w-full')
                        
                        with ui.row().classes('w-full gap-3 no-wrap'):
                            sol_setor = ui.input('Setor / Divisão').props('dark outlined dense').classes('w-1/2')
                            sol_contato = ui.input('Telefone / Ramal').props('dark outlined dense').classes('w-1/2')
                            
                        ev_titulo = ui.input('Título do Evento / Pauta').props('dark outlined dense w-full')
                        
                        with ui.row().classes('w-full gap-3 no-wrap'):
                            ev_data = ui.input('Data Início').props('type=date dark outlined dense').classes('w-1/3')
                            ev_data_fim = ui.input('Data Término').props('type=date dark outlined dense').classes('w-1/3')
                            ev_hora = ui.input('Hora').props('type=time dark outlined dense').classes('w-1/3')
                            
                        ev_local = ui.input('Local do Evento').props('dark outlined dense w-full')
                        ev_aut = ui.input('Autoridades Presentes').props('dark outlined dense w-full')
                        
                        ev_entrega_tipo = ui.select(
                            {
                                'apenas_captacao_bruto': 'Apenas Captação (Entrega de material bruto)',
                                'captacao_e_edicao': 'Captação + Edição concluída'
                            },
                            value='captacao_e_edicao',
                            label='Formato de Entrega'
                        ).props('dark outlined dense w-full option-dark').classes('w-full')
                        
                        militar_select = ui.select(
                            efetivo_options,
                            multiple=True,
                            label='Selecionar Militares'
                        ).props('dark outlined dense w-full option-dark').classes('w-full')

                        ui.separator().style('background-color: rgba(255, 255, 255, 0.05); margin: 12px 0;')

                        # Componente de anexo de arquivo
                        ui.label('📎 Anexo (Briefing, Arte ou Produto Corrigido)').classes('text-xs font-bold text-white')
                        
                        def handle_upload(e):
                            try:
                                import os
                                # Pasta temporária ou definitiva de anexos
                                folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'anexos_pautas')
                                os.makedirs(folder, exist_ok=True)
                                
                                # Salva arquivo localmente
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

                        # Uploader do NiceGUI compacto
                        ui.upload(
                            on_upload=handle_upload,
                            label='Escolher arquivo',
                            auto_upload=True
                        ).props('dark flat bordered text-color=white dense').classes('w-full text-xs').style('max-height: 80px;')
                        
                        upload_status_lbl = ui.label('Nenhum arquivo anexado').classes('text-[10px] text-grey-4 w-full text-center')

                # 2. Checklist & Escopo (Checklist de Viabilidade)
                with ui.column().classes('col-12 col-md-4 q-pa-none').style('min-width: 320px;'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                    ):
                        ui.label('🔍 Checklist de Viabilidade').classes('text-md font-bold text-cyan q-mb-xs')
                        
                        nonlocal chk_staff, chk_equip, chk_drone, chk_transp, chk_cred, chk_anteced, chk_briefing
                        nonlocal chk_foto, chk_video, chk_redes, chk_sigilo
                        
                        chk_staff = ui.checkbox('Há pessoal de cobertura na escala?', on_change=lambda e: (form_state.update({'viabilidade_staff': e.value}), atualizar_score_ui()))
                        chk_equip = ui.checkbox('Equipamentos reservados?', on_change=lambda e: (form_state.update({'viabilidade_equip': e.value}), atualizar_score_ui()))
                        chk_drone = ui.checkbox('Necessita Drone (Piloto/Homologação)?', on_change=lambda e: (form_state.update({'viabilidade_drone': e.value}), atualizar_score_ui()))
                        chk_transp = ui.checkbox('Transporte/Logística assegurado?', on_change=lambda e: (form_state.update({'viabilidade_transp': e.value}), atualizar_score_ui()))
                        chk_cred = ui.checkbox('Credenciamento de Imprensa externa?', on_change=lambda e: (form_state.update({'viabilidade_credencial': e.value}), atualizar_score_ui()))
                        chk_anteced = ui.checkbox('Antecedência maior que 48h?', on_change=lambda e: (form_state.update({'viabilidade_anteced': e.value}), atualizar_score_ui()))
                        chk_briefing = ui.checkbox('Briefing/Ordem de Serviço (VOGAL) concluída?', on_change=lambda e: (form_state.update({'viabilidade_briefing': e.value}), atualizar_score_ui()))
                        
                        ui.separator().style('background-color: rgba(255, 255, 255, 0.05);')
                        
                        ui.label('📸 Escopo de Cobertura').classes('text-xs font-bold text-white q-mt-xs')
                        chk_foto = ui.checkbox('Fotografia', on_change=lambda e: (form_state.update({'cobertura_foto': e.value}), atualizar_score_ui()))
                        chk_video = ui.checkbox('Vídeo / Filmagem', on_change=lambda e: (form_state.update({'cobertura_video': e.value}), atualizar_score_ui()))
                        chk_redes = ui.checkbox('Redes Sociais / Texto', on_change=lambda e: (form_state.update({'cobertura_redes': e.value}), atualizar_score_ui()))
                        
                        nonlocal score_label
                        score_label = ui.label('🟢 Score: 1.0 (Baixo Esforço)').classes('text-sm font-bold text-center w-full q-py-xs bg-black/30 rounded-md q-mt-md')
                        atualizar_score_ui()

                        chk_sigilo = ui.checkbox('Pauta Sigilosa / Reservada').classes('text-xs text-amber-5 q-mt-xs')
                        
                        async def salvar_demanda(status_inicial='pendente', eh_evento_interno=False):
                            nome_sol = sol_nome.value or ('COMSOC / GABINETE' if eh_evento_interno else '')
                            if not nome_sol or not ev_titulo.value or not ev_data.value or not ev_local.value:
                                ui.notify('Por favor, preencha os campos obrigatórios (Título, Data e Local).', color='warning')
                                return
                                
                            db = get_service_db_connection() or get_db_connection()
                            if db:
                                try:
                                    coberturas = []
                                    if form_state['cobertura_foto']: coberturas.append('foto')
                                    if form_state['cobertura_video']: coberturas.append('video')
                                    if form_state['cobertura_redes']: coberturas.append('redes')
                                    
                                    registro = {
                                        'solicitante_nome': nome_sol,
                                        'setor': sol_setor.value or ('GABINETE / QUARTEL' if eh_evento_interno else 'Gabinete'),
                                        'contato': sol_contato.value or 'Interno',
                                        'titulo_evento': ev_titulo.value,
                                        'data_evento': ev_data.value,
                                        'data_fim': ev_data_fim.value or ev_data.value,
                                        'hora_evento': ev_hora.value or '09:00',
                                        'local_evento': ev_local.value,
                                        'tipo_cobertura': json.dumps(coberturas),
                                        'autoridades': ev_aut.value or '',
                                        'score_esforco': calcular_score(),
                                        'sigiloso': 1 if chk_sigilo.value else 0,
                                        'status': 'aprovado' if eh_evento_interno else status_inicial,
                                        'captacao_entrega': ev_entrega_tipo.value or 'apenas_captacao_bruto',
                                        'notificar_militar_ids': json.dumps(militar_select.value) if militar_select.value else '[]',
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
                                            ui.notify('🎖️ Novo Evento do Quartel cadastrado e aprovado com sucesso!', color='success')
                                        else:
                                            ui.notify('📝 Solicitação enviada com sucesso! Aguardando aprovação.', color='success')
                                    
                                    sol_nome.value = ''
                                    ev_titulo.value = ''
                                    ev_local.value = ''
                                    ev_aut.value = ''
                                    militar_select.value = []
                                    render_content.refresh()
                                except Exception as ex:
                                    ui.notify(f'Erro ao salvar: {ex}', color='red')
                         
                        with ui.row().classes('w-full gap-2 q-mt-sm justify-between'):
                            ui.button(
                                '🎖️ Novo Evento (Interno do Quartel)', 
                                icon='stars', 
                                on_click=lambda: salvar_demanda(status_inicial='aprovado', eh_evento_interno=True)
                            ).props('unelevated color=emerald text-color=white bold').classes('col-12 font-bold')

                            ui.button(
                                '📝 Nova Solicitação (Externa)', 
                                icon='send', 
                                on_click=lambda: salvar_demanda(status_inicial='pendente', eh_evento_interno=False)
                            ).props('outline color=cyan text-color=white bold').classes('col-12 font-bold q-mt-xs')

                        # CARD DE INTEGRAÇÃO COM O GOOGLE CALENDAR OFICIAL
                        with ui.card().classes('w-full q-pa-sm border border-cyan-500/30 rounded-xl bg-black/40 q-mt-sm'):
                            with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('calendar_month', color='cyan', size='1.5rem')
                                    with ui.column().classes('gap-0'):
                                        ui.label('📅 AGENDA GOOGLE CALENDAR OFICIAL').classes('text-[11px] font-bold text-white')
                                        ui.label('cgcfnaudiovisual@gmail.com').classes('text-[9px] text-cyan font-mono')
                                
                                ui.link(
                                    '🔗 Abrir Google Calendar',
                                    'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20',
                                    new_tab=True
                                ).classes('text-[10px] font-bold text-cyan underline q-px-xs q-py-xs bg-cyan-950/60 border border-cyan-500/40 rounded-lg')

                # 3. Demandas em Ajustes (Direita - 1/3 da largura)
                with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                    ):
                        ui.label('⚠️ Aguardando Ajustes').classes('text-md font-bold text-cyan q-mb-md')
                        
                        minhas_demandas = []
                        db = get_db_connection()
                        if db:
                            try:
                                res = db.table('demandas_comunicacao').select('*').eq('status', 'ajustes').execute()
                                minhas_demandas = res.data if res.data else []
                            except Exception as e:
                                print(f"[DB MINHAS DEMANDAS ERR] {e}")
                                
                        if minhas_demandas:
                            for d in minhas_demandas:
                                with ui.card().classes('w-full q-pa-sm q-mb-sm no-shadow rounded-lg').style(
                                    'background: rgba(255,255,255,0.02); border: 1px solid rgba(255,160,0,0.3);'
                                ):
                                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                                        with ui.column().classes('gap-0'):
                                            ui.label(d['titulo_evento']).classes('text-xs font-bold text-white')
                                            ui.label("Retornado para correções").classes('text-[9px] text-amber-5')
                                        
                                        def aplicar_ajustes_no_form(dem=d):
                                            nonlocal edit_id
                                            edit_id = dem['id']
                                            sol_nome.value = dem['solicitante_nome']
                                            sol_setor.value = dem['setor']
                                            sol_contato.value = dem['contato']
                                            ev_titulo.value = dem['titulo_evento']
                                            ev_data.value = dem['data_evento']
                                            ev_data_fim.value = dem.get('data_fim', dem['data_evento'])
                                            ev_hora.value = dem['hora_evento']
                                            ev_local.value = dem['local_evento']
                                            ev_aut.value = dem['autoridades']
                                            
                                            try:
                                                m_ids = json.loads(dem.get('notificar_militar_ids', '[]'))
                                                militar_select.value = m_ids
                                            except:
                                                militar_select.value = []
                                                
                                            ui.notify('Dados carregados! Faça as correções e clique em Enviar.', color='info', duration=5)
                                            
                                        ui.button(
                                            'Editar',
                                            icon='edit',
                                            on_click=lambda dem=d: aplicar_ajustes_no_form(dem)
                                        ).props('unelevated color=amber-5 text-color=black dense').classes('text-[9px] q-px-sm')
                        else:
                            with ui.column().classes('w-full items-center justify-center q-py-lg gap-2 text-grey-4'):
                                ui.icon('verified', size='2rem', color='grey')
                                ui.label('Nenhuma pauta sua necessita de ajustes.').classes('text-[10px]')

    render_content()
    
    # Executa preenchimento se dados foram enviados via Query String (vêm do Assistente de IA)
    if autofill:
        ui.timer(0.2, lambda: popular_form_ia(autofill), once=True)
