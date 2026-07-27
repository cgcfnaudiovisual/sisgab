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
        db = get_db_connection() or get_service_db_connection()
        if db:
            try:
                res_ef = db.table('efetivo').select('id, nome_guerra, role').execute()
                if res_ef.data:
                    efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
            except Exception as e:
                print(f"[EFETIVO LOAD ERR] {e}")

        # Fallback local via SQLite se o Supabase estiver offline/vazio
        if not efetivo_options:
            try:
                from sqlite_adapter import SQLiteDatabaseAdapter
                local_db = SQLiteDatabaseAdapter()
                res_ef = local_db.table('efetivo').select('id, nome_guerra, role').execute()
                if res_ef.data:
                    efetivo_options = {item['id']: f"{item['nome_guerra']} ({item['role'].upper()})" for item in res_ef.data}
            except Exception as loc_err:
                print(f"[EFETIVO LOCAL LOAD ERR] {loc_err}")

        with ui.column().classes('w-full gap-4'):


            # ⚡ BARRA SUPERIOR DE ATALHOS RÁPIDOS EM 1 CLIQUE
            with ui.card().classes('w-full q-pa-sm px-4 no-shadow rounded-xl bg-black/40 border border-cyan-500/30 q-mb-xs'):
                with ui.row().classes('w-full items-center justify-between wrap gap-2'):
                    ui.label('⚡ MODELOS DE ATALHO RÁPIDO (1 Clique):').classes('text-xs font-bold text-amber tracking-wider')
                    with ui.row().classes('items-center gap-2 wrap'):
                        def aplicar_template_cardapio():
                            categoria_demanda.value = 'design_arte'
                            produto_especifico.value = 'Cardápio de Almoço de Autoridade'
                            ev_entrega_tipo.value = 'impressao_fisica'
                            ev_titulo.value = 'CARDÁPIO - ALMOÇO OFICIAL'
                            ui.notify('🍽️ Modelo Cardápio Aplicado! Preencha apenas o Prazo e Detalhes.', color='info')

                        def aplicar_template_paspatur():
                            categoria_demanda.value = 'impressos_albuns'
                            produto_especifico.value = 'Paspatur / Moldura de Quadro A4'
                            ev_entrega_tipo.value = 'impressao_fisica'
                            ev_titulo.value = 'PASPATUR PARA SOLENIDADE'
                            ui.notify('🖼️ Modelo Paspatur Aplicado!', color='info')

                        def aplicar_template_redacao():
                            categoria_demanda.value = 'redacao_textos'
                            produto_especifico.value = 'Discurso / Ordem do Dia'
                            ev_entrega_tipo.value = 'captacao_e_edicao'
                            ev_titulo.value = 'DISCURSO DE POSSE / NOTA OFICIAL'
                            ui.notify('📜 Modelo Redação Aplicado!', color='info')

                        def aplicar_template_audiovisual():
                            categoria_demanda.value = 'audiovisual'
                            produto_especifico.value = 'Cobertura Completa (Foto + Vídeo)'
                            ev_entrega_tipo.value = 'captacao_e_edicao'
                            ev_titulo.value = 'COBERTURA FOTOGRÁFICA E VÍDEO'
                            ui.notify('📸 Modelo Cobertura Audiovisual Aplicado!', color='info')

                        ui.button('🍽️ Cardápio Almoço', on_click=aplicar_template_cardapio).props('unelevated color=amber text-color=black dense').classes('text-xs font-bold q-px-sm')
                        ui.button('🖼️ Paspatur / Moldura', on_click=aplicar_template_paspatur).props('unelevated color=cyan text-color=black dense').classes('text-xs font-bold q-px-sm')
                        ui.button('📜 Discurso / Nota', on_click=aplicar_template_redacao).props('unelevated color=purple-9 text-color=white dense').classes('text-xs font-bold q-px-sm')
                        ui.button('📸 Foto & Vídeo', on_click=aplicar_template_audiovisual).props('unelevated color=green-9 text-color=white dense').classes('text-xs font-bold q-px-sm')

            # SEÇÃO OPERACIONAL: FORMULÁRIO DINÂMICO (Esquerda) E PAINEL COMPLEMENTAR (Direita)
            with ui.row().classes('w-full gap-4 items-stretch justify-start'):
                # 1. Formulário Principal Inteligente
                with ui.column().classes('col-12 col-md-6 q-pa-none').style('min-width: 320px;'):
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                    ):
                        nonlocal sol_nome, sol_setor, sol_contato, ev_titulo, ev_data, ev_data_fim, ev_hora, ev_local, ev_aut, ev_entrega_tipo, militar_select, uploaded_file_url, uploaded_file_name, upload_status_lbl, chk_sigilo
                        
                        ui.label('📝 Formulação da Demanda / Tarefa Tática').classes('text-md font-bold text-cyan q-mb-xs')
                        
                        ui.label('🎯 Categoria & Produto Solicitado:').classes('text-xs font-bold text-amber q-mt-xs')
                        
                        # Container para controlar visibilidade dos campos específicos de evento audiovisual
                        campos_audiovisual_container = None

                        def ao_mudar_categoria(e):
                            eh_audiovisual = e.value == 'audiovisual'
                            if campos_audiovisual_container:
                                if eh_audiovisual:
                                    campos_audiovisual_container.set_visibility(True)
                                else:
                                    campos_audiovisual_container.set_visibility(False)

                        categoria_demanda = ui.select(
                            {
                                'design_arte': '🎨 Design / Arte Visual (Cardápio, Paspatur, Card, Banner)',
                                'impressos_albuns': '📕 Impressos & Encadernação (Álbum, Livro de Honra, Porta-Copo)',
                                'brindes_lembrancas': '🎁 Brindes & Lembranças (Kits, Placas Comemorativas)',
                                'audiovisual': '📸 Cobertura Audiovisual (Fotografia e Vídeo)',
                                'redacao_textos': '✍️ Redação & Discursos (Ordem do Dia, Notas, Convites)',
                                'suporte_evento': '📦 Suporte Logístico / Receptivo de Evento',
                                'outra_tarefa': '⚡ Outra Tarefa Especial (Descreva no campo abaixo)'
                            },
                            value='design_arte',
                            label='Categoria do Serviço / Demanda',
                            on_change=ao_mudar_categoria
                        ).props('dark outlined dense w-full option-dark').classes('w-full font-bold text-cyan')

                        produto_especifico = ui.input('Especificação da Peça (ex: Cardápio Almoço, Paspatur A4, Arte Instagram)').props('dark outlined dense w-full')
                        
                        ev_titulo = ui.input('Título Geral da Tarefa / Solenidade').props('dark outlined dense w-full')

                        with ui.row().classes('w-full gap-2 no-wrap q-mt-xs'):
                            prioridade_select = ui.select(
                                {
                                    'normal': '🟢 Normal (Prazo Padrão)',
                                    'urgente': '🟡 Urgente (Prioridade do Dia)',
                                    'altissima': '🔴 ALTÍSSIMA / GABINETE (Urgência Imediata)'
                                },
                                value='normal',
                                label='Nível de Prioridade / Urgência'
                            ).props('dark outlined dense option-dark').classes('w-1/2')

                            prazo_limite = ui.input('Prazo Limite / Deadline (Término)', value=datetime.now().strftime('%Y-%m-%d')).props('type=date dark outlined dense').classes('w-1/2')

                        with ui.row().classes('w-full gap-3 no-wrap'):
                            sol_nome = ui.input('Solicitante', value='CGCFN / GABINETE').props('dark outlined dense').classes('w-1/2')
                            sol_setor = ui.input('Setor / OM', value='CGCFN').props('dark outlined dense').classes('w-1/2')

                        sol_contato = ui.input('Contato / Ramal', value='21982043314 / Ramal CGCFN').props('dark outlined dense w-full')
                        chk_sigilo = ui.checkbox('Pauta Sigilosa / Reservada (Gabinete)').classes('text-xs text-amber-5 q-mt-xs')

                        # CONTAINER DE CAMPOS EXCLUSIVOS DE COBERTURA AUDIOVISUAL (Escondido se for Design/Cardápio)
                        with ui.column().classes('w-full gap-2 p-2 bg-black/20 rounded-lg border border-cyan-500/10 q-my-xs') as campos_audiovisual_container:
                            campos_audiovisual_container.set_visibility(False)
                            ui.label('📸 Detalhes de Cobertura Audiovisual (Eventos Externa/Interna):').classes('text-xs font-bold text-cyan')
                            
                            with ui.row().classes('w-full gap-3 no-wrap'):
                                ev_data = ui.input('Data Início').props('type=date dark outlined dense').classes('w-1/3')
                                ev_data_fim = ui.input('Data Término').props('type=date dark outlined dense').classes('w-1/3')
                                ev_hora = ui.input('Hora Início').props('type=time dark outlined dense').classes('w-1/3')
                                
                            ev_local = ui.input('Local Exato do Evento').props('dark outlined dense w-full')
                            ev_aut = ui.input('Autoridades Presentes').props('dark outlined dense w-full')
                        
                        ev_entrega_tipo = ui.select(
                            {
                                'apenas_captacao_bruto': 'Apenas Captação / Entrega Bruta',
                                'captacao_e_edicao': 'Produção Completa / Peça Finalizada',
                                'impressao_fisica': 'Impressão Física / Arte Final'
                            },
                            value='captacao_e_edicao',
                            label='Formato de Entrega Final'
                        ).props('dark outlined dense w-full option-dark').classes('w-full')
                        
                        if is_internal_staff:
                            lbl_militar = '🎯 Designar Militar Responsável / Equipe da Missão' if is_approver else '👤 Sugestão de Encarregado (Opcional)'
                            militar_select = ui.select(
                                efetivo_options,
                                multiple=True,
                                label=lbl_militar
                            ).props('dark outlined dense w-full option-dark').classes('w-full')
                        else:
                            militar_select = None

                        observacoes_exec = ui.textarea('📝 Observações / Notas Importantes de Produção', placeholder='Digite instruções adicionais para o designer/impressor...').props('dark outlined dense w-full rows=2')

                        ui.separator().style('background-color: rgba(255, 255, 255, 0.05); margin: 8px 0;')

                        # Componente de anexo de arquivo
                        ui.label('📎 Anexo (Briefing, Logotipos, Roteiro ou Arte)').classes('text-xs font-bold text-white')
                        
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
                        ).props('dark flat bordered text-color=white dense').classes('w-full text-xs').style('max-height: 70px;')
                        
                        upload_status_lbl = ui.label('Nenhum arquivo anexado').classes('text-[10px] text-grey-4 w-full text-center')

                        async def salvar_demanda(status_inicial='pendente', eh_evento_interno=False):
                            nome_sol = sol_nome.value or ('COMSOC / GABINETE' if eh_evento_interno else '')
                            if not nome_sol or not ev_titulo.value:
                                ui.notify('Por favor, preencha os campos obrigatórios (Título e Solicitante).', color='warning')
                                return
                                
                            # Validação inteligente por categoria
                            if categoria_demanda.value == 'audiovisual':
                                if not ev_data.value or not ev_local.value:
                                    ui.notify('Para Cobertura Audiovisual, a Data de Início e o Local Exato são obrigatórios!', color='warning')
                                    return
                                
                            db = get_service_db_connection() or get_db_connection()
                            if db:
                                try:
                                    coberturas = []
                                    if form_state['cobertura_foto']: coberturas.append('foto')
                                    if form_state['cobertura_video']: coberturas.append('video')
                                    if form_state['cobertura_redes']: coberturas.append('redes')
                                    
                                    dt_ev = (ev_data.value if hasattr(ev_data, 'value') and ev_data.value else None) or prazo_limite.value
                                    loc_ev = (ev_local.value if hasattr(ev_local, 'value') and ev_local.value else None) or 'Gabinete / CGCFN'

                                    registro = {
                                        'solicitante_nome': nome_sol,
                                        'setor': sol_setor.value or ('GABINETE / QUARTEL' if eh_evento_interno else 'Gabinete'),
                                        'contato': sol_contato.value or 'Interno',
                                        'titulo_evento': ev_titulo.value.upper(),
                                        'categoria_demanda': categoria_demanda.value or 'design_arte',
                                        'produto_especifico': produto_especifico.value or '',
                                        'prioridade': prioridade_select.value or 'normal',
                                        'prazo_limite': prazo_limite.value or '',
                                        'observacoes_execucao': observacoes_exec.value or '',
                                        'data_evento': dt_ev,
                                        'data_fim': dt_ev,
                                        'hora_evento': (ev_hora.value if hasattr(ev_hora, 'value') and ev_hora.value else None) or '09:00',
                                        'local_evento': loc_ev,
                                        'tipo_cobertura': json.dumps(coberturas),
                                        'autoridades': (ev_aut.value if hasattr(ev_aut, 'value') and ev_aut.value else '') or '',
                                        'score_esforco': calcular_score(),
                                        'sigiloso': 1 if chk_sigilo.value else 0,
                                        'status': 'aprovado' if eh_evento_interno else status_inicial,
                                        'captacao_entrega': ev_entrega_tipo.value or 'captacao_e_edicao',
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
                                            ui.notify('🎖️ Nova Tarefa / Evento cadastrado e aprovado com sucesso!', color='success')
                                        else:
                                            ui.notify('📝 Solicitação enviada com sucesso! Aguardando aprovação.', color='success')
                                    
                                    # Notificação Telegram para gestores (interconexão Web → Telegram)
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
                                    militar_select.value = []
                                    render_content.refresh()
                                except Exception as ex:
                                    ui.notify(f'Erro ao salvar: {ex}', color='red')
                         
                        with ui.row().classes('w-full gap-2 q-mt-sm justify-between'):
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


                # 2. Painel de Suporte & Checklist Completo (Coluna da Direita)
                with ui.column().classes('col-12 col-md-5 q-pa-none gap-4').style('min-width: 320px;'):
                    
                    # CARD 1: Assistente de Entrada com IA (Expansível / Compacto)
                    with ui.card().classes('w-full q-pa-sm no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ):
                        with ui.expansion('🤖 Assistente de Entrada com IA', icon='psychology', value=False).classes('w-full font-bold text-cyan').style('color: #00e5ff;'):
                            with ui.column().classes('w-full q-pa-md gap-3'):
                                ui.label('Cole a mensagem bruta com as respostas do solicitante no campo abaixo. O Gemini analisará o texto e preencherá todo o formulário automaticamente.').classes('text-xs text-grey-4')
                                
                                # Seletor de Modelo Gemini dinâmico
                                with ui.row().classes('w-full items-center justify-between no-wrap'):
                                    ui.label('Modelo IA:').classes('text-xs text-grey-4')
                                    modelos_disponiveis = ai_helper.get_available_gemini_models()
                                    modelo_salvo = app.storage.user.get('preferred_gemini_model', 'gemini-2.0-flash')
                                    if modelo_salvo not in modelos_disponiveis:
                                        modelos_disponiveis[modelo_salvo] = f"{modelo_salvo} (Ativo)"
                                        
                                    model_select_ia = ui.select(
                                        modelos_disponiveis,
                                        value=modelo_salvo,
                                        on_change=lambda e: app.storage.user.update({'preferred_gemini_model': e.value})
                                    ).props('dark outlined dense options-dark').classes('w-36 text-[10px]').style('max-height: 28px;')

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
                                        response_json = ai_helper.digest_demand_questionnaire(text)
                                        popular_form_ia(response_json)
                                    except Exception as err:
                                        err_msg = str(err)
                                        if "429" in err_msg or "quota" in err_msg.lower():
                                            ui.notify('⚠️ Cota excedida no modelo atual! Selecione outro modelo ao lado e tente novamente.', color='warning', duration=8)
                                        else:
                                            ui.notify(f'Erro na digestão: {err}', color='danger')
                                            
                                with ui.row().classes('w-full justify-between items-center q-mt-xs'):
                                    ui.button(
                                        'Copiar Questionário', 
                                        icon='content_copy', 
                                        on_click=copiar_checklist_whatsapp
                                    ).props('unelevated color=primary text-color=black bold dense').classes('text-[10px] q-px-sm')
                                    
                                    ui.button(
                                        'Processar e Preencher',
                                        icon='psychology',
                                        on_click=processar_texto_ia
                                    ).props('unelevated color=cyan text-color=black bold dense').classes('text-[10px] q-px-sm')

                    # CARD 2: Checklist de Suporte & Viabilidade (Surge apenas para Cobertura Audiovisual)
                    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
                    ) as checklist_card:
                        ui.label('🔍 Checklist de Suporte & Viabilidade').classes('text-md font-bold text-cyan q-mb-xs')
                        ui.label('(Necessário para missões de Cobertura Audiovisual)').classes('text-[11px] text-grey-4 q-mb-xs')
                        
                        nonlocal chk_staff, chk_equip, chk_drone, chk_transp, chk_cred, chk_anteced, chk_briefing
                        nonlocal chk_foto, chk_video, chk_redes
                        
                        chk_staff = ui.checkbox('Pessoal escalado e disponível?', on_change=lambda e: (form_state.update({'viabilidade_staff': e.value}), atualizar_score_ui()))
                        chk_equip = ui.checkbox('Equipamentos / Insumos reservados?', on_change=lambda e: (form_state.update({'viabilidade_equip': e.value}), atualizar_score_ui()))
                        chk_drone = ui.checkbox('Necessita Drone / Homologação?', on_change=lambda e: (form_state.update({'viabilidade_drone': e.value}), atualizar_score_ui()))
                        chk_transp = ui.checkbox('Transporte / Logística assegurado?', on_change=lambda e: (form_state.update({'viabilidade_transp': e.value}), atualizar_score_ui()))
                        chk_cred = ui.checkbox('Credenciamento de Imprensa externa?', on_change=lambda e: (form_state.update({'viabilidade_credencial': e.value}), atualizar_score_ui()))
                        chk_anteced = ui.checkbox('Antecedência suficiente?', on_change=lambda e: (form_state.update({'viabilidade_anteced': e.value}), atualizar_score_ui()))
                        chk_briefing = ui.checkbox('Briefing / Roteiro aprovado?', on_change=lambda e: (form_state.update({'viabilidade_briefing': e.value}), atualizar_score_ui()))
                        
                        ui.separator().style('background-color: rgba(255, 255, 255, 0.05); margin: 8px 0;')
                        
                        ui.label('📸 Escopo Adicional').classes('text-xs font-bold text-white q-mt-xs')
                        chk_foto = ui.checkbox('Fotografia', on_change=lambda e: (form_state.update({'cobertura_foto': e.value}), atualizar_score_ui()))
                        chk_video = ui.checkbox('Vídeo / Filmagem', on_change=lambda e: (form_state.update({'cobertura_video': e.value}), atualizar_score_ui()))
                        chk_redes = ui.checkbox('Redes Sociais / Texto', on_change=lambda e: (form_state.update({'cobertura_redes': e.value}), atualizar_score_ui()))
                        
                        nonlocal score_label
                        score_label = ui.label('🟢 Score: 1.0 (Baixo Esforço)').classes('text-sm font-bold text-center w-full q-py-xs bg-black/30 rounded-md q-mt-md')
                        atualizar_score_ui()

                    # Vincula a visibilidade do Checklist apenas à categoria Audiovisual
                    checklist_card.bind_visibility_from(categoria_demanda, 'value', value='audiovisual')


    render_content()
    
    # Executa preenchimento se dados foram enviados via Query String (vêm do Assistente de IA)
    if autofill:
        ui.timer(0.2, lambda: popular_form_ia(autofill), once=True)
