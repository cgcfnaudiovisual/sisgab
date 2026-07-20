from nicegui import ui
import theme

def render_page():
    ui.label('ℹ️ AJUDA / SOBRE O SISTEMA').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    with ui.card().classes('w-full max-w-5xl mx-auto q-pa-lg no-shadow rounded-xl').style(
        f'background: {theme.colors["bg_panel"]}; border: 1px solid {theme.colors["border"]};'
    ):
        # Tabs para Ajuda e Sobre
        with ui.tabs().classes('w-full text-white flex-wrap') as tabs:
            tab_manual = ui.tab('📘 Manual do Usuário & Comandos', icon='menu_book')
            tab_arquitetura = ui.tab('⚙️ Arquitetura & Módulos', icon='account_tree')
            tab_sobre = ui.tab('⚓ Sobre o SisGAB', icon='info')
            
        with ui.tab_panels(tabs, value=tab_sobre).classes('w-full bg-transparent text-white q-mt-md'):
            # Painel do SOBRE
            with ui.tab_panel(tab_sobre):
                with ui.column().classes('w-full gap-6'):
                    # Cabeçalho com Gradient e Efeito Premium
                    with ui.row().classes('w-full items-center gap-4 q-pa-md rounded-lg').style(
                        'background: linear-gradient(135deg, rgba(212,175,55,0.1) 0%, rgba(0,229,255,0.05) 100%); border: 1px solid rgba(255,255,255,0.05);'
                    ):
                        ui.icon('shield', size='4rem', color='cyan-5').classes('drop-shadow-[0_0_12px_rgba(0,229,255,0.3)]')
                        with ui.column().classes('gap-0'):
                            ui.label('SisGAB v2.0 (COMSOC Edition)').classes('text-xl font-bold text-white tracking-wide')
                            ui.label('Sistema de Gestão de Gabinete e Central de Comunicação Social').classes('text-grey-4 text-xs')
                            ui.label('Desenvolvido pela Assessoria COMSOC').classes('text-cyan-4 text-xs font-bold q-mt-xs')
                    
                    # Descrição do App
                    with ui.column().classes('w-full gap-2 q-px-sm'):
                        ui.label('Sobre o Aplicativo').classes('text-md font-bold text-primary cyber-title')
                        ui.markdown(
                            'O **SisGAB** é uma plataforma corporativa de alta performance projetada para centralizar, '
                            'organizar e automatizar todas as rotinas administrativas do Gabinete e do fluxo de Comunicação Social. '
                            'Integrando inteligência artificial, controle preditivo de cautelas de equipamentos fotográficos, '
                            'análise inteligente de viabilidade de demandas e letreiro digital para o Modo TV, o sistema '
                            'proporciona um monitor tático operacional unificado e dinâmico.'
                        ).classes('text-grey-3 text-xs leading-relaxed')

                    ui.separator().style('background-color: rgba(255, 255, 255, 0.05);')
                    
                    # Funções Incrementadas da v1.0 para v2.0
                    with ui.column().classes('w-full gap-3 q-px-sm'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('trending_up', color='primary').classes('text-lg')
                            ui.label('Evolução do Sistema (v1.0 ➔ v2.0)').classes('text-md font-bold text-primary cyber-title')
                        
                        ui.label('Confira os novos recursos operacionais implementados na versão 2.0:').classes('text-grey-4 text-xs')
                        
                        # Grid de Funcionalidades
                        with ui.grid(columns=1).classes('w-full gap-4 gt-xs').style('grid-template-columns: repeat(2, 1fr);'):
                            
                            # Card 1: Fluxo de Demandas
                            with ui.card().classes('q-pa-md no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'):
                                with ui.row().classes('items-center gap-2 q-mb-xs'):
                                    ui.icon('assignment', color='cyan-5').classes('text-md')
                                    ui.label('Fluxo de Demandas Inteligente').classes('text-xs font-bold text-white')
                                ui.markdown(
                                    '- **Viabilidade Analítica**: Cálculo automático de score de esforço reativo baseado em complexidade, prazo e recursos.\n'
                                    '- **Tramitação Bilateral**: Fluxo de aprovação transparente para supervisores e operadores.\n'
                                    '- **Pre-Checklist**: Validação automática de pré-requisitos antes do envio da demanda.'
                                ).classes('text-grey-4 text-[11px] leading-relaxed')
                                
                            # Card 2: Cautela de Equipamentos
                            with ui.card().classes('q-pa-md no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'):
                                with ui.row().classes('items-center gap-2 q-mb-xs'):
                                    ui.icon('camera_alt', color='cyan-5').classes('text-md')
                                    ui.label('Prevenção de Conflitos em Cautelas').classes('text-xs font-bold text-white')
                                ui.markdown(
                                    '- **Prevenção Preditiva**: Alertas instantâneos ao tentar reservar equipamentos em horários conflitantes.\n'
                                    '- **Log de Cautelas**: Histórico digital de retiradas e devoluções de câmeras, lentes e baterias.'
                                ).classes('text-grey-4 text-[11px] leading-relaxed')

                            # Card 3: Monitor Tático TV
                            with ui.card().classes('q-pa-md no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'):
                                with ui.row().classes('items-center gap-2 q-mb-xs'):
                                    ui.icon('tv', color='cyan-5').classes('text-md')
                                    ui.label('Modo TV / Monitor Tático').classes('text-xs font-bold text-white')
                                ui.markdown(
                                    '- **Dashboard Dinâmico**: Exibição em tempo real de pautas de hoje, cautelas ativas e boletins oficiais.\n'
                                    '- **Ticker Tape (Letreiro)**: Notícias e avisos correndo de forma contínua no rodapé da tela.'
                                ).classes('text-grey-4 text-[11px] leading-relaxed')

                            # Card 4: Entrega em Hot
                            with ui.card().classes('q-pa-md no-shadow rounded-lg').style('background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);'):
                                with ui.row().classes('items-center gap-2 q-mb-xs'):
                                    ui.icon('photo_library', color='cyan-5').classes('text-md')
                                    ui.label('Galeria "Entrega em Hot"').classes('text-xs font-bold text-white')
                                ui.markdown(
                                    '- **Uploader Seguro**: Restrição rígida de arquivos apenas para formatos `.jpg` e `.jpeg`.\n'
                                    '- **Organização Dinâmica**: Separação física de fotos organizadas por pastas de eventos no servidor.'
                                ).classes('text-grey-4 text-[11px] leading-relaxed')

            # Painel do AJUDA
            with ui.tab_panel(tab_ajuda):
                with ui.column().classes('w-full items-center justify-center q-pa-xl gap-4 text-center'):
                    ui.icon('help_outline', size='4rem', color='grey-6')
                    ui.label('Central de Ajuda & Tutoriais').classes('text-lg font-bold text-white')
                    ui.label('Esta seção está sendo preparada e no momento não inclui documentações externas. Volte em breve para consultar tutoriais, manuais e guias passo a passo de utilização do SisGAB!').classes('text-grey-4 text-xs max-w-md leading-relaxed')
