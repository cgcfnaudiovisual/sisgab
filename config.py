from nicegui import ui, app, run
import theme
import os
import io
import json
from database import get_db_connection, SUPABASE_URL, get_bot_db_connection as get_admin_db_connection
from services import data_service
from datetime import date

THEME = theme.colors

# Configurações padrão alinhadas ao Gabinete & COMSOC
DEFAULT_CONFIGS = {
    'tempo_polling_tv': '30',
    'cabecalho_tv_title': 'MONITOR TÁTICO — COMUNICAÇÃO SOCIAL',
    'cabecalho_tv_subtitle': 'COMUNICAÇÃO SOCIAL • GABINETE',
    'cargos_escala_lista': 'SUPERVISOR, FOTÓGRAFO, CINEGRAFISTA, MÍDIAS SOCIAIS, REDATOR',
    'tempo_alerta_tv': '10',
    'telegram_bot_token': '',
    'telegram_chat_id': '',
    'gemini_model_name': 'gemini-2.5-flash',
    'google_calendar_email': 'cgcfnaudiovisual@gmail.com',
    'google_calendar_url': 'https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20'
}

def render_page():
    # Injeta script de desbloqueio de áudio por gesto do usuário
    ui.add_head_html("""
    <script>
        window.resumeComcaAudio = function() {
            try {
                if (!window.globalAudioContext) {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (AudioContext) {
                        window.globalAudioContext = new AudioContext();
                        console.log("[AUDIO] AudioContext initialized via gesture");
                    }
                }
                if (window.globalAudioContext) {
                    if (window.globalAudioContext.state === 'suspended') {
                        window.globalAudioContext.resume();
                    }
                }
            } catch (e) {
                console.error("[AUDIO] Erro ao retomar áudio:", e);
            }
        };
        document.addEventListener('click', window.resumeComcaAudio, { once: true });
    </script>
    """)

    def testar_som(som_key: str):
        """Executa a síntese de som no navegador."""
        if som_key == 'silent':
            ui.notify('Silencioso ativado para este som.', color='warning')
            return

        js_code = f"""
        try {{
            let ctx = window.globalAudioContext;
            if (!ctx) {{
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {{ ctx = new AudioContext(); window.globalAudioContext = ctx; }}
            }}
            if (ctx) {{
                let now = ctx.currentTime;
                let osc = ctx.createOscillator();
                let gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                
                if ('{som_key}' === 'success') {{
                    osc.frequency.setValueAtTime(523.25, now);
                    osc.frequency.setValueAtTime(659.25, now + 0.1);
                    gain.gain.setValueAtTime(0.3, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
                    osc.start(now); osc.stop(now + 0.3);
                }} else if ('{som_key}' === 'warning') {{
                    osc.frequency.setValueAtTime(440, now);
                    osc.frequency.setValueAtTime(349.23, now + 0.15);
                    gain.gain.setValueAtTime(0.4, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
                    osc.start(now); osc.stop(now + 0.4);
                }} else {{
                    osc.frequency.setValueAtTime(880, now);
                    gain.gain.setValueAtTime(0.3, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
                    osc.start(now); osc.stop(now + 0.2);
                }}
            }}
        }} catch(e) {{ console.error(e); }}
        """
        ui.run_javascript(js_code)
        ui.notify(f"🔊 Reproduzindo som: {som_key.upper()}", color='info')

    # Carrega dados atuais do banco
    try:
        config_df = data_service.get_config_data(force_refresh=True)
        db_configs = dict(zip(config_df['chave'], config_df['valor'])) if not config_df.empty else {}
    except Exception as e:
        print(f"[CONFIG] Erro ao carregar configurações: {e}")
        db_configs = {}

    current_configs = {k: db_configs.get(k, v) for k, v in DEFAULT_CONFIGS.items()}

    from alerts_manager import load_alerts_config, save_alerts_config
    alerts_config = load_alerts_config()
    sound_mappings = alerts_config.get("sound_mappings", {})
    message_templates = alerts_config.get("message_templates", {})

    with ui.column().classes('w-full q-pa-lg gap-6'):
        ui.label('⚙️ CONFIGURAÇÕES DO SISGAB (COMSOC & GABINETE)').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')

        # ── ESTRUTURA DE ABAS ──
        with ui.tabs().classes('w-full border-b border-white/10 q-mb-md text-white flex-wrap') as tabs:
            tab_tv = ui.tab('tv', label='Monitor TV & Projeção', icon='tv').classes('cyber-title text-xs font-bold')
            tab_telegram = ui.tab('telegram', label='Notificações & Telegram', icon='notifications').classes('cyber-title text-xs font-bold')
            tab_avisos = ui.tab('avisos', label='Avisos & Ordens do Gabinete', icon='campaign').classes('cyber-title text-xs font-bold')
            tab_templates = ui.tab('templates', label='Modelos de Texto (Pronto CheGab)', icon='description').classes('cyber-title text-xs font-bold')
            tab_sistema = ui.tab('sistema', label='Sistema & Backup', icon='save').classes('cyber-title text-xs font-bold')

        panels = ui.tab_panels(tabs, value='tv').classes('w-full bg-transparent')
        with panels:

            # =========================================================================
            # ABA 1: MONITOR TV & PROJEÇÃO TÁTICA
            # =========================================================================
            with ui.tab_panel('tv').classes('bg-transparent q-pa-none gap-6'):
                with ui.grid(columns='1 md:grid-cols-2').classes('w-full gap-6'):
                    with theme.card_base().classes('w-full q-pa-md'):
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('tv', size='2rem').style(f'color: {THEME["accent"]}')
                                ui.label('Painel de Projeção (Modo TV)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                            ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                            input_polling = ui.input(
                                'Tempo de Polling/Atualização (segundos)', 
                                value=current_configs.get('tempo_polling_tv', '30')
                            ).props('dark dense outlined w-full').classes('w-full')

                            input_cabecalho_tv = ui.input(
                                'Título do Cabeçalho da TV', 
                                value=current_configs.get('cabecalho_tv_title', 'MONITOR TÁTICO — COMUNICAÇÃO SOCIAL')
                            ).props('dark dense outlined w-full').classes('w-full')

                            input_subcabecalho_tv = ui.input(
                                'Subtítulo do Cabeçalho da TV', 
                                value=current_configs.get('cabecalho_tv_subtitle', 'COMUNICAÇÃO SOCIAL • GABINETE')
                            ).props('dark dense outlined w-full').classes('w-full')

                            input_cargos_escala = ui.input(
                                'Funções da Escala Diária (separadas por vírgula)', 
                                value=current_configs.get('cargos_escala_lista', 'SUPERVISOR, FOTÓGRAFO, CINEGRAFISTA, MÍDIAS SOCIAIS, REDATOR')
                            ).props('dark dense outlined w-full').classes('w-full')

                            input_alerta_tv = ui.input(
                                'Tempo de Exibição de Alertas Toast (segundos)', 
                                value=current_configs.get('tempo_alerta_tv', '10')
                            ).props('dark dense outlined w-full').classes('w-full')

                    # Card de Teste de Alertas Sonoros
                    with theme.card_base().classes('w-full q-pa-md'):
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('volume_up', size='2rem').style(f'color: {THEME["accent"]}')
                                ui.label('Alertas Sonoros da TV & Sistema').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                            ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                            ui.label('Teste de reprodução dos sons emitidos ao receber solicitações ou notificações:').classes('text-xs text-grey-4')

                            with ui.row().classes('w-full gap-2 flex-wrap'):
                                ui.button('🔊 Nova Demanda (Info)', on_click=lambda: testar_som('info')).props('unelevated color=cyan dense').classes('text-xs')
                                ui.button('🔔 Demanda Aprovada (Success)', on_click=lambda: testar_som('success')).props('unelevated color=green dense').classes('text-xs')
                                ui.button('⚠️ Ajustes (Warning)', on_click=lambda: testar_som('warning')).props('unelevated color=amber dense').classes('text-xs')

            # =========================================================================
            # ABA 2: NOTIFICAÇÕES & TELEGRAM (TERMOS COMSOC)
            # =========================================================================
            with ui.tab_panel('telegram').classes('bg-transparent q-pa-none gap-6'):
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('notifications', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Integrador de Notificações Telegram Bot').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                        input_telegram_token = ui.input(
                            'Token do Bot do Telegram', 
                            value=current_configs.get('telegram_bot_token', ''),
                            password=True, password_toggle_button=True
                        ).props('dark dense outlined w-full').classes('w-full')

                        input_telegram_chat = ui.input(
                            'ID do Chat / Grupo do Telegram', 
                            value=current_configs.get('telegram_chat_id', '')
                        ).props('dark dense outlined w-full').classes('w-full')

                        ui.label('Gatilhos Automáticos de Notificação:').classes('text-xs font-bold text-white q-mt-sm')

                        chk_notify_demanda = ui.checkbox('📝 Notificar Nova Solicitação de Demanda / Pauta', value=True).classes('text-xs text-grey-3')
                        chk_notify_homologacao = ui.checkbox('⚖️ Notificar Tramitação & Homologação de Pautas', value=True).classes('text-xs text-grey-3')
                        chk_notify_presenca = ui.checkbox('📋 Notificar Envio do Pronto Matutino ao CheGab', value=True).classes('text-xs text-grey-3')
                        chk_notify_escala = ui.checkbox('🛡️ Notificar Alteração na Escala de Serviço', value=True).classes('text-xs text-grey-3')
                        chk_notify_aviso = ui.checkbox('📢 Notificar Novos Avisos & Ordens do Gabinete', value=True).classes('text-xs text-grey-3')

                        def testar_telegram():
                            try:
                                from notifications_manager import notify_telegram
                                notify_telegram("🧪 **TESTE DE CONEXÃO SISGAB**\nO canal de notificações está operando corretamente!", "system")
                                ui.notify('Mensagem de teste enviada via Telegram!', color='success')
                            except Exception as err:
                                ui.notify(f'Erro ao enviar teste: {err}', color='negative')

                        ui.button('🧪 Testar Envio Telegram', icon='send', on_click=testar_telegram).props('unelevated color=cyan text-color=black bold dense').classes('text-xs q-mt-sm')

            # =========================================================================
            # ABA 3: AVISOS & ORDENS DO GABINETE
            # =========================================================================
            with ui.tab_panel('avisos').classes('bg-transparent q-pa-none gap-6'):
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('campaign', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Ordens Diárias e Avisos do Gabinete').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                        order_state = {'date': date.today().strftime('%Y-%m-%d')}
                        
                        with ui.row().classes('w-full items-center gap-2'):
                            date_input = ui.input('Data dos Avisos', value=order_state['date']).props('dark dense outlined type=date').classes('col-grow')
                            date_input.on('change', lambda: (order_state.update({'date': date_input.value}), render_orders_list.refresh()))

                        @ui.refreshable
                        def render_orders_list():
                            db_conn = get_db_connection()
                            orders = []
                            if db_conn:
                                try:
                                    res = db_conn.table('Ordens_Diarias').select('*').eq('data', order_state['date']).execute()
                                    orders = res.data or []
                                except Exception as e:
                                    print(f"[CONFIG] Erro ao carregar ordens: {e}")

                            with ui.column().classes('w-full gap-2 border border-white/5 q-pa-sm rounded bg-black/10').style('max-height: 200px; overflow-y: auto;'):
                                if not orders:
                                    ui.label('Sem avisos cadastrados para esta data.').classes('text-xs italic text-grey-5 text-center w-full py-2')
                                else:
                                    for o in orders:
                                        with ui.row().classes('w-full justify-between items-center py-1 border-b border-white/5'):
                                            with ui.column().classes('gap-0 col-grow'):
                                                ui.label(o['texto']).classes('text-xs text-white')
                                                ui.label(f"Por: {o.get('autor_id', 'GABINETE')}").classes('text-[9px] text-grey-5')

                                            def excluir_ordem(o_id=o.get('id')):
                                                db_c = get_db_connection()
                                                if db_c and o_id:
                                                    try:
                                                        db_c.table('Ordens_Diarias').delete().eq('id', o_id).execute()
                                                        ui.notify('Aviso excluído com sucesso!', color='success')
                                                        render_orders_list.refresh()
                                                    except Exception as err:
                                                        ui.notify(f'Erro: {err}', color='red')

                                            ui.button(icon='delete', on_click=excluir_ordem).props('flat round dense color=red').classes('text-xs')

                        render_orders_list()

                        input_ordem_text = ui.input('Novo Aviso / Ordem do Dia', placeholder='Ex: Formatura Geral às 07:30 Uniforme 3º A.').props('dark dense outlined w-full').classes('w-full')

                        def adicionar_ordem():
                            val = input_ordem_text.value.strip()
                            if not val:
                                ui.notify('Digite o texto do aviso.', color='warning')
                                return
                            autor = app.storage.user.get('user_data', {}).get('nome_guerra', 'GABINETE').upper()
                            db_conn = get_db_connection()
                            if db_conn:
                                try:
                                    db_conn.table('Ordens_Diarias').insert({
                                        'data': order_state['date'],
                                        'texto': val,
                                        'autor_id': autor,
                                        'status': 'Ativo'
                                    }).execute()
                                    ui.notify('Aviso publicado com sucesso!', color='success')
                                    input_ordem_text.value = ''
                                    render_orders_list.refresh()

                                    # Notifica no Telegram
                                    try:
                                        from notifications_manager import notify_telegram
                                        notify_telegram(f"📢 **NOVO AVISO DO GABINETE**\n👤 Autor: {autor}\n\n\"{val}\"", "aviso")
                                    except Exception:
                                        pass
                                except Exception as err:
                                    ui.notify(f'Erro: {err}', color='negative')

                        ui.button('📢 Publicar Aviso', icon='send', on_click=adicionar_ordem).props('unelevated color=amber-9 text-color=black bold dense').classes('w-full text-xs')

            # =========================================================================
            # ABA 4: MODELOS DE TEXTO & RESUMOS (PRONTO CHEGAB)
            # =========================================================================
            with ui.tab_panel('templates').classes('bg-transparent q-pa-none gap-6'):
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('description', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Modelos de Texto Oficial e Formatação').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                        ui.label('Personalize a estrutura de texto utilizada ao copiar o Pronto do CheGab ou disparar confirmações:').classes('text-xs text-grey-4')

                        tpl_pronto = ui.textarea(
                            'Estrutura do Pronto ao CheGab (Chamada Matutina)',
                            value=message_templates.get("Chamada Matutina", "Bom dia Equipe LANÇAMENTO 🚀, resumo das rotinas para hoje ({data}):\n\n🚨 *pronto da presença para o CheGab:*\n\n{linhas_militares}\n\nLegenda:\n(P) - Presente | (MA) - Missão Adm | (MT) - Mais Tarde | (FE) - Férias | (L) - Licença | (H) - Hospital | (DM) - Dispensa Médica | (S) - Serviço | (OUTRO) - Outra Situação\n\nAtenciosamente,\nSargenteante do Gabinete")
                        ).props('dark outlined w-full').classes('text-xs')

                        tpl_demanda = ui.textarea(
                            'Modelo de Confirmação de Recebimento de Demanda',
                            value=message_templates.get("Nova Demanda", "📝 **Nova Solicitação de Pauta**:\n{message}")
                        ).props('dark outlined w-full').classes('text-xs')

            # =========================================================================
            # ABA 5: SISTEMA & BACKUP
            # =========================================================================
            with ui.tab_panel('sistema').classes('bg-transparent q-pa-none gap-6'):
                with ui.grid(columns='1 md:grid-cols-2').classes('w-full gap-6'):
                    # Card Backup
                    with theme.card_base().classes('w-full q-pa-md'):
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('save', size='2rem').style(f'color: {THEME["accent"]}')
                                ui.label('Cópia de Segurança (Backup)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                            ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                            ui.label('Gere uma cópia de segurança completa do banco de dados do SISGAB em formato JSON:').classes('text-xs text-grey-4')

                            def baixar_backup_json():
                                try:
                                    db_conn = get_db_connection()
                                    backup_data = {}
                                    if db_conn:
                                        tabelas = ['demandas_comunicacao', 'efetivo', 'presenca_diaria', 'comsoc_noticias', 'escala_diaria', 'comsoc_equipamentos']
                                        for tab in tabelas:
                                            try:
                                                res = db_conn.table(tab).select('*').execute()
                                                backup_data[tab] = res.data or []
                                            except Exception:
                                                pass
                                    json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
                                    dt_file = datetime.now().strftime('%Y-%m-%d_%H%M')
                                    ui.download(json_str.encode('utf-8'), f"SISGAB_Backup_{dt_file}.json")
                                    ui.notify('💾 Backup do SISGAB gerado com sucesso!', color='positive')
                                except Exception as bck_err:
                                    ui.notify(f'Erro ao gerar backup: {bck_err}', color='negative')

                            ui.button('💾 Download do Backup (JSON)', icon='download', on_click=baixar_backup_json).props('unelevated color=cyan text-color=black bold dense').classes('text-xs')

                    # Card Atalho Permissões (Apenas para Administrador)
                    user_data_cfg = app.storage.user.get('user_data', {})
                    if str(user_data_cfg.get('role', '')).strip().lower() == 'admin':
                        with theme.card_base().classes('w-full q-pa-md'):
                            with ui.column().classes('w-full gap-4'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('admin_panel_settings', size='2rem').style(f'color: {THEME["accent"]}')
                                    ui.label('Usuários & Permissões').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                                ui.separator().style('background-color: rgba(0, 229, 255, 0.15);')

                                ui.label('O gerenciamento de usuários, aprovação de novos cadastros e níveis de acesso foi unificado na central dedicada:').classes('text-xs text-grey-4')

                                ui.button('🛡️ Abrir Gerenciador de Usuários', icon='launch', on_click=lambda: ui.navigate.to('/admin_panel')).props('unelevated color=primary text-color=black bold dense').classes('text-xs')


        # ── BOTÃO GLOBAL DE SALVAMENTO DE CONFIGURAÇÕES ──
        async def salvar_configs():
            try:
                int(input_polling.value)
                int(input_alerta_tv.value)
            except ValueError:
                ui.notify('Os campos de tempo devem conter valores inteiros válidos.', color='red')
                return

            db_conn = get_admin_db_connection() or get_db_connection()
            novas_configs = [
                {'chave': 'tempo_polling_tv', 'valor': str(input_polling.value)},
                {'chave': 'cabecalho_tv_title', 'valor': str(input_cabecalho_tv.value)},
                {'chave': 'cabecalho_tv_subtitle', 'valor': str(input_subcabecalho_tv.value)},
                {'chave': 'cargos_escala_lista', 'valor': str(input_cargos_escala.value)},
                {'chave': 'tempo_alerta_tv', 'valor': str(input_alerta_tv.value)},
                {'chave': 'telegram_bot_token', 'valor': str(input_telegram_token.value)},
                {'chave': 'telegram_chat_id', 'valor': str(input_telegram_chat.value)}
            ]

            # Atualiza message_templates
            new_alerts_config = load_alerts_config()
            if 'message_templates' not in new_alerts_config:
                new_alerts_config['message_templates'] = {}
            new_alerts_config['message_templates']["Chamada Matutina"] = tpl_pronto.value
            new_alerts_config['message_templates']["Nova Demanda"] = tpl_demanda.value
            save_alerts_config(new_alerts_config)

            if db_conn:
                try:
                    for item in novas_configs:
                        db_conn.table('Config').upsert(item, on_conflict='chave').execute()
                    ui.notify('✅ Configurações salvas no Supabase com sucesso!', color='success')
                except Exception as err:
                    ui.notify(f'Erro ao salvar no banco: {err}', color='warning')

            data_service.clear_cache()

        with ui.row().classes('w-full justify-end q-mt-md'):
            ui.button('💾 Salvar Configurações', on_click=salvar_configs).props('unelevated dense').style(f'background: {THEME["primary"]}; color: #0b0f19; font-weight: bold;').classes('cyber-glow px-6 py-2')
