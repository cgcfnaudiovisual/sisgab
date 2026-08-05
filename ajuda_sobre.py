from nicegui import ui, app
import theme

def render_page():
    user_data = app.storage.user.get('user_data', {})
    nome_guerra = str(user_data.get('nome_guerra') or user_data.get('username') or 'Militar').upper()
    user_role = str(user_data.get('role', 'militar')).strip().lower()

    role_labels = {
        'admin': '👑 Administrador (Acesso Total)',
        'supervisor': '⚖️ Supervisor COMSOC',
        'oficial_gab': '⚖️ Oficial do Gabinete',
        'oficial': '⚓ Oficial da OM',
        'praca_gab': '📜 Praça do Gabinete',
        'comsoc': '📸 Equipe COMSOC (Fotografia/Vídeo)',
        'comsoc_design': '🎨 Equipe COMSOC (Artes Gráficas/Canva)',
        'militar': '⚓ Militar / Efetivo em Geral'
    }
    role_display = role_labels.get(user_role, user_role.upper())

    with ui.column().classes('w-full max-w-6xl mx-auto q-pa-md gap-4'):

        # ── BANNER PRINCIPAL DE BOAS-VINDAS ──
        with ui.card().classes('w-full q-pa-lg no-shadow rounded-2xl border border-cyan-500/30 overflow-hidden relative').style(
            'background: linear-gradient(135deg, rgba(11,15,25,0.95) 0%, rgba(15,23,42,0.9) 100%);'
        ):
            with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.icon('verified_user', size='3.5rem', color='cyan-4').classes('drop-shadow-[0_0_15px_rgba(0,229,255,0.4)]')
                    with ui.column().classes('gap-1'):
                        ui.label(f'👋 SEJA BEM-VINDO(A), {nome_guerra}!').classes('text-2xl font-black text-white tracking-wide cyber-title')
                        ui.label('SisGAB — Central Integrada de Gestão de Gabinete e Comunicação Social').classes('text-xs text-grey-4 font-semibold')
                        with ui.row().classes('items-center gap-2 q-mt-xs'):
                            ui.badge('SISTEMA ONLINE', color='green-9').classes('text-[9px] font-bold')
                            ui.badge(f'SEU PERFIL: {role_display}', color='amber-9' if user_role == 'militar' else 'cyan-9').classes('text-[9px] font-bold')

        # ── CARD DE NOTA DE STATUS DO PERFIL MILITAR (SE FOR PERFIL MILITAR) ──
        if user_role == 'militar':
            with ui.card().classes('w-full q-pa-md no-shadow rounded-xl border border-amber-500/40').style(
                'background: rgba(245, 158, 11, 0.08);'
            ):
                with ui.row().classes('items-start gap-3'):
                    ui.icon('info', size='2rem', color='amber-4').classes('shrink-0 q-mt-xs')
                    with ui.column().classes('gap-1 col-grow'):
                        ui.label('📌 STATUS DO SEU CADASTRO').classes('text-sm font-bold text-amber-4 tracking-wider')
                        ui.label(
                            'Sua conta foi registrada com sucesso e seu acesso inicial está 100% ativo! '
                            'No momento, o seu usuário possui o perfil padrão de "Militar / Efetivo".'
                        ).classes('text-xs text-slate-200 leading-relaxed')
                        ui.label(
                            '💡 Caso você necessite de um perfil com permissões avançadas de gestão '
                            '(ex: Homologação de Pautas, Cautela de Equipamentos, Estúdio Canva, Mídia TV, Gerenciamento de Tarefas), '
                            'solicite a alteração ao Administrador do Gabinete no Painel de Controle ou via Telegram.'
                        ).classes('text-xs text-grey-4 q-mt-xs leading-relaxed')

        # ── NAVEGAÇÃO DE TABS ──
        with ui.card().classes('w-full q-pa-md no-shadow rounded-xl border border-white/5').style(
            f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]};'
        ):
            with ui.tabs().classes('w-full text-white flex-wrap') as tabs:
                tab_boas_vindas = ui.tab('👋 Boas-Vindas & Apresentação', icon='waving_hand')
                tab_manual = ui.tab('📘 Guias & Dúvidas Frequentes', icon='help')
                tab_sobre = ui.tab('⚓ Sobre o SisGAB v2.0', icon='info')

            with ui.tab_panels(tabs, value=tab_boas_vindas).classes('w-full bg-transparent text-white q-mt-md'):

                # ── TAB 1: BOAS-VINDAS E APRESENTAÇÃO ──
                with ui.tab_panel(tab_boas_vindas):
                    with ui.column().classes('w-full gap-6'):
                        ui.label('O que é o SisGAB?').classes('text-md font-bold text-cyan-4 cyber-title')
                        ui.markdown(
                            'O **SisGAB** é a plataforma oficial desenvolvida para modernizar, agilizar e unificar '
                            'as rotinas administrativas do Gabinete e o fluxo operacional da **Assessoria de Comunicação Social (COMSOC)**.\n\n'
                            'Ele foi desenhado com tecnologia de ponta para proporcionar controle em tempo real, inteligência artificial e alta disponibilidade.'
                        ).classes('text-grey-3 text-xs leading-relaxed')

                        ui.separator().style('background-color: rgba(255, 255, 255, 0.05);')

                        ui.label('Módulos Principais do Sistema').classes('text-md font-bold text-amber-4 cyber-title')

                        with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(3, 1fr);'):

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('assignment_ind', color='cyan-4', size='md')
                                ui.label('Chamada & Presença').classes('text-xs font-bold text-white')
                                ui.label('Controle matutino de presença e emissão imediata do relatório "Pronto do CheGab".').classes('text-[11px] text-grey-4')

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('camera_alt', color='cyan-4', size='md')
                                ui.label('Demandas COMSOC').classes('text-xs font-bold text-white')
                                ui.label('Abertura, parecer, homologação e acompanhamento de pautas de fotografia e vídeo.').classes('text-[11px] text-grey-4')

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('palette', color='cyan-4', size='md')
                                ui.label('Estúdio Canva & Artes').classes('text-xs font-bold text-white')
                                ui.label('Editor gráfico integrado com modelos oficiais para convites, cartazes e mídias sociais.').classes('text-[11px] text-grey-4')

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('event_seat', color='cyan-4', size='md')
                                ui.label('Placas de Assento Jade').classes('text-xs font-bold text-white')
                                ui.label('Mapeamento inteligente de auditório, precedência militar e impressão de placas de mesa.').classes('text-[11px] text-grey-4')

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('tv', color='cyan-4', size='md')
                                ui.label('Monitor TV Tático').classes('text-xs font-bold text-white')
                                ui.label('Modo painel em tempo real para telas do Gabinete com rotação de pautas e notícias.').classes('text-[11px] text-grey-4')

                            with ui.card().classes('q-pa-md rounded-xl border border-white/5 bg-black/20 gap-2'):
                                ui.icon('smart_toy', color='cyan-4', size='md')
                                ui.label('Assistente de IA').classes('text-xs font-bold text-white')
                                ui.label('Gerador de textos, redação oficial, resumos automáticos e suporte via Telegram.').classes('text-[11px] text-grey-4')

                # ── TAB 2: MANUAL & DÚVIDAS FREQUENTES ──
                with ui.tab_panel(tab_manual):
                    with ui.column().classes('w-full gap-4'):
                        ui.label('❓ Perguntas Frequentes & Orientações').classes('text-md font-bold text-cyan-4 cyber-title')

                        with ui.expansion('Como solicito uma alteração ou upgrade de perfil no sistema?', icon='badge').classes('w-full bg-black/20 rounded-lg text-xs'):
                            ui.markdown(
                                'Caso necessite de permissões de Administrador, Supervisor ou Operador COMSOC, '
                                'solicite diretamente ao **Administrador do Gabinete**. Ele poderá alterar seu perfil no **Painel de Usuários (`/admin_panel`)** '
                                'ou responder à solicitação pendente no **Bot do Telegram**.'
                            ).classes('q-pa-xs text-grey-3')

                        with ui.expansion('Como funciona a integração com o Bot do Telegram?', icon='send').classes('w-full bg-black/20 rounded-lg text-xs'):
                            ui.markdown(
                                'O SisGAB possui um Bot de Telegram integrado que envia alertas de pautas, confirmações de presença e notificações de sistema. '
                                'Para vincular seu Telegram, vá em **Configurações** ou digite o comando `/start` diretamente na conversa com o Bot.'
                            ).classes('q-pa-xs text-grey-3')

                        with ui.expansion('Como proceder para cadastrar uma nova demanda COMSOC?', icon='add_box').classes('w-full bg-black/20 rounded-lg text-xs'):
                            ui.markdown(
                                'Acesse o menu **Nova Solicitação / Demanda**, preencha o título do evento, data/hora, local, responsável e observações. '
                                'A demanda entrará automaticamente na fila para análise e parecer da chefia.'
                            ).classes('q-pa-xs text-grey-3')

                # ── TAB 3: SOBRE O SISGAB V2.0 ──
                with ui.tab_panel(tab_sobre):
                    with ui.column().classes('w-full gap-6'):
                        with ui.row().classes('w-full items-center gap-4 q-pa-md rounded-lg').style(
                            'background: linear-gradient(135deg, rgba(212,175,55,0.1) 0%, rgba(0,229,255,0.05) 100%); border: 1px solid rgba(255,255,255,0.05);'
                        ):
                            ui.icon('shield', size='3.5rem', color='cyan-4').classes('drop-shadow-[0_0_12px_rgba(0,229,255,0.3)]')
                            with ui.column().classes('gap-0'):
                                ui.label('SisGAB v2.0 (COMSOC Edition)').classes('text-xl font-bold text-white tracking-wide')
                                ui.label('Sistema de Gestão de Gabinete e Central de Comunicação Social').classes('text-grey-4 text-xs')
                                ui.label('Desenvolvido pela Assessoria COMSOC').classes('text-cyan-4 text-xs font-bold q-mt-xs')

                        ui.markdown(
                            'O **SisGAB v2.0** é mantido e atualizado continuamente para atender às demandas '
                            'institucionais com excelência, segurança da informação e facilidade de acesso em computadores e dispositivos móveis.'
                        ).classes('text-grey-3 text-xs leading-relaxed')
