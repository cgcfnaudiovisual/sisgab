# modules/comsoc_aniversariantes.py
import json
import os
from datetime import datetime
from nicegui import ui, app
import theme
from database import get_db_connection
import ai_helper
from logo_base64 import LOGO_BASE64

THEME = theme.colors

# Estado persistido de emails enviados na sessão/memória para marcar com check positivo
EMAILS_ENVIADOS = set()

def render_page():
    ui.label('🎂 ANIVERSARIANTES E DATAS COMEMORATIVAS').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
    
    # Estado da tela
    state = {
        'mes_filtro': str(datetime.now().month),
        'search': '',
        'categoria_filtro': 'todos'
    }

    # Estilos de impressão nítida
    ui.add_head_html("""
    <style>
    @media print {
        body * {
            visibility: hidden;
        }
        .print-card-area, .print-card-area * {
            visibility: visible;
        }
        .print-card-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 10.5cm;
            height: 15cm;
            border: 2px solid #000 !important;
            padding: 1.5cm;
            box-sizing: border-box;
            background: #fff !important;
            color: #000 !important;
        }
        .no-print {
            display: none !important;
        }
    }
    </style>
    """)

    @ui.refreshable
    def render_content():
        db = get_db_connection()
        efetivo = []
        datas_comemorativas = []
        if db:
            try:
                # 1. Puxa aniversariantes (Efetivo + Visitantes)
                res = db.table('efetivo').select('*').execute()
                efetivo = res.data if res.data else []
                
                # 2. Puxa datas comemorativas dinâmicas registradas no banco
                res_dc = db.table('datas_comemorativas').select('*').execute()
                datas_comemorativas = res_dc.data if res_dc.data else []
            except Exception as e:
                print(f"[BIRTHDAY DATA LOAD ERR] {e}")

        # Filtros
        mes_atual = int(state['mes_filtro'])
        q = state['search'].strip().lower()
        cat_filtro = state['categoria_filtro']
        
        aniversariantes_filtrados = []
        for e in efetivo:
            birth = e.get('data_nascimento')
            if not birth:
                continue
            
            # Filtro de busca textual (nome, posto, setor, origem)
            nome_val = (e.get('nome_guerra') or '').lower()
            posto_val = (e.get('posto') or '').lower()
            setor_val = (e.get('setor') or '').lower()
            origem_val = (e.get('origem') or '').lower()
            
            if q and not (q in nome_val or q in posto_val or q in setor_val or q in origem_val):
                continue
                
            # Filtro por Categoria (militar, visitante_civil, autoridade)
            e_cat = e.get('categoria', 'militar')
            if cat_filtro != 'todos' and e_cat != cat_filtro:
                continue
                
            try:
                b_dt = datetime.strptime(birth, '%Y-%m-%d')
                if b_dt.month == mes_atual:
                    aniversariantes_filtrados.append({
                        'id': e['id'],
                        'nome': (e.get('nome_guerra') or 'Sem Nome').upper(),
                        'posto': (e.get('posto') or 'Militar').upper(),
                        'dia': b_dt.day,
                        'email': e.get('email', ''),
                        'setor': (e.get('setor') or 'Gabinete').upper(),
                        'origem': (e.get('origem') or 'Interno').upper(),
                        'categoria': e_cat
                    })
            except:
                pass
                
        aniversariantes_filtrados.sort(key=lambda x: x['dia'])

        with ui.row().classes('w-full gap-4 items-stretch justify-start'):
            # 1. Coluna da Esquerda: Lista de Aniversariantes e Cadastros
            with ui.column().classes('col-12 col-md-7 q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                ):
                    with ui.row().classes('w-full justify-between items-center q-mb-md no-wrap'):
                        ui.label('👥 Lista de Aniversariantes do Mês').classes('text-md font-bold text-white')
                        
                        # Cadastro de novo militar / civil
                        def abrir_cadastro():
                            with ui.dialog() as diag, ui.card().classes('w-[420px] q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                                ui.label('Cadastrar Aniversariante').classes('text-white text-md font-bold cyber-title')
                                
                                input_cat = ui.select(
                                    {
                                        'militar': 'Militar (Efetivo)',
                                        'autoridade': 'Autoridade Externa',
                                        'visitante_civil': 'Visitante / Civil'
                                    },
                                    value='militar',
                                    label='Categoria'
                                ).props('dark outlined dense w-full option-dark')
                                
                                input_nome = ui.input('Nome de Guerra / Nome Civil').props('dark outlined dense w-full')
                                input_posto = ui.input('Posto / Graduação / Cargo').props('dark outlined dense w-full')
                                input_setor = ui.input('Setor / Divisão').props('dark outlined dense w-full')
                                input_origem = ui.input('Origem / Órgão').props('dark outlined dense w-full')
                                input_email = ui.input('E-mail (Para felicitações)').props('dark outlined dense w-full')
                                input_birth = ui.input('Data de Nascimento').props('type=date dark outlined dense w-full')
                                
                                def cadastrar():
                                    if not input_nome.value or not input_birth.value:
                                        ui.notify('Nome e Data de Nascimento são obrigatórios!', color='warning')
                                        return
                                    conn = get_db_connection()
                                    if conn:
                                        try:
                                            conn.table('efetivo').insert({
                                                'nome_guerra': input_nome.value.upper(),
                                                'posto': input_posto.value.upper() or 'CIVIL',
                                                'email': input_email.value or '',
                                                'data_nascimento': input_birth.value,
                                                'setor': input_setor.value or 'Externo',
                                                'origem': input_origem.value or 'Gabinete',
                                                'categoria': input_cat.value,
                                                'role': 'militar'
                                            }).execute()
                                            ui.notify('Cadastro inserido com sucesso!', color='success')
                                            diag.close()
                                            render_content.refresh()
                                        except Exception as ex:
                                            ui.notify(f'Erro ao salvar no banco: {ex}', color='red')
                                
                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=diag.close).props('flat color=grey')
                                    ui.button('Salvar', on_click=cadastrar).props('unelevated color=primary text-color=black')
                            diag.open()
                            
                        ui.button('Adicionar Pessoa', icon='person_add', on_click=abrir_cadastro).props('unelevated color=primary text-color=black bold dense').classes('text-xs q-px-sm')

                    if aniversariantes_filtrados:
                        with ui.column().classes('w-full gap-2'):
                            for a in aniversariantes_filtrados:
                                border_color = "rgba(0, 229, 255, 0.4)"
                                bg_color = "rgba(0, 229, 255, 0.05)"
                                badge_cat = "MILITAR"
                                color_badge = "cyan-9"
                                
                                if a['categoria'] == 'autoridade':
                                    border_color = "rgba(255, 179, 0, 0.5)"
                                    bg_color = "rgba(255, 179, 0, 0.05)"
                                    badge_cat = "AUTORIDADE"
                                    color_badge = "amber-9"
                                elif a['categoria'] == 'visitante_civil':
                                    border_color = "rgba(233, 30, 99, 0.4)"
                                    bg_color = "rgba(233, 30, 99, 0.05)"
                                    badge_cat = "CIVIL"
                                    color_badge = "pink-9"

                                with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style(f'background: rgba(255,255,255,0.01); border-left: 4px solid {border_color};'):
                                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                                        with ui.row().classes('items-center gap-3'):
                                            # Círculo com dia do aniversário
                                            with ui.element('div').classes('flex items-center justify-center rounded-circle shrink-0').style(f'width:34px; height:34px; background: {bg_color}; border: 1.5px solid {border_color};'):
                                                ui.label(str(a['dia'])).classes('font-bold text-xs text-white')
                                            with ui.column().classes('gap-0'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.label(a['nome']).classes('text-xs font-bold text-white')
                                                    ui.badge(badge_cat).props(f"color={color_badge} dense").classes('text-[8px] q-px-xs')
                                                ui.label(f"{a['posto']} • {a['setor']} | Origem: {a['origem']}").classes('text-[10px] text-grey-4')
                                        
                                        # Ações do militar
                                        with ui.row().classes('gap-2 items-center'):
                                            # Se e-mail já foi enviado, exibe um ícone de check verde positivo
                                            enviado_key = f"{a['id']}_{state['mes_filtro']}"
                                            
                                            # Tela de Confirmação e Edição do E-mail
                                            def abrir_confirmacao_email(militar=a, key=enviado_key):
                                                if not militar['email']:
                                                    ui.notify(f"E-mail não cadastrado para {militar['nome']}!", color='warning')
                                                    return
                                                    
                                                with ui.dialog() as mail_diag, ui.card().classes('q-pa-lg').style(
                                                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; width: 720px; max-width: 95vw;'
                                                ):
                                                    # Cabeçalho
                                                    with ui.row().classes('w-full items-center gap-3 q-mb-md no-wrap'):
                                                        ui.icon('mark_email_unread', color='cyan', size='md')
                                                        with ui.column().classes('gap-0'):
                                                            ui.label('Compor & Enviar Felicitações').classes('text-white text-md font-bold cyber-title')
                                                            ui.label(f"Para: {militar['nome']} ‹{militar['email']}›").classes('text-[11px] text-grey-4')

                                                    ui.separator().style('background: rgba(0,229,255,0.1);')

                                                    with ui.row().classes('w-full gap-4 q-mt-sm items-start no-wrap'):
                                                        # COLUNA ESQUERDA — Composição
                                                        with ui.column().classes('gap-3').style('flex: 1; min-width: 0;'):
                                                            ui.label('✏️ Composição').classes('text-xs font-bold text-cyan tracking-wider')

                                                            sel_tom_mail = ui.select(
                                                                {
                                                                    'institucional': '🎖️ Institucional (MB)',
                                                                    'amigavel': '🤝 Amigável',
                                                                    'poetico': '🌊 Poético',
                                                                    'humorado': '😄 Descontraído'
                                                                },
                                                                value='amigavel',
                                                                label='Estilo da Mensagem'
                                                            ).props('dark outlined dense option-dark').classes('w-full')

                                                            assunto_input = ui.input(
                                                                'Assunto',
                                                                value=f"🎂 Feliz Aniversário, {militar['posto']} {militar['nome']}!"
                                                            ).props('dark outlined dense').classes('w-full')

                                                            corpo_input = ui.textarea('Mensagem').props('dark outlined autogrow').classes('w-full text-xs').style('min-height: 180px;')

                                                            ui.button(
                                                                '✨ Gerar com IA',
                                                                icon='psychology',
                                                                on_click=lambda: gerar_felicitacao_ia()
                                                            ).props('unelevated color=cyan text-color=black bold').classes('w-full')

                                                        # COLUNA DIREITA — Preview do E-mail
                                                        with ui.column().classes('gap-2').style('flex: 1; min-width: 0;'):
                                                            ui.label('👁️ Pré-visualização').classes('text-xs font-bold text-cyan tracking-wider')
                                                            with ui.card().classes('w-full q-pa-md no-shadow').style(
                                                                'background: #fff; color: #111; border-radius: 8px; min-height: 240px;'
                                                            ):
                                                                ui.label('✉ SisGAB — Gabinete').style('font-size:9px; color:#888; border-bottom:1px solid #ddd; padding-bottom:4px; width:100%;')
                                                                ui.label().classes('text-[11px] font-bold q-mt-xs').style('color:#222;').bind_text_from(assunto_input, 'value')
                                                                ui.label(f"Para: {militar['email']}").style('font-size:9px; color:#555; margin-bottom:8px;')
                                                                ui.label().classes('text-[11px]').style('white-space: pre-wrap; color:#333; font-family: serif; line-height:1.6;').bind_text_from(corpo_input, 'value')
                                                                ui.label(f"— {militar['setor']}").style('font-size:9px; color:#888; border-top:1px dashed #ccc; padding-top:6px; margin-top:8px; width:100%;')

                                                            # Status do SMTP
                                                            smtp_ok = bool(ai_helper.get_config_value('smtp_user', ''))
                                                            if smtp_ok:
                                                                ui.label('🟢 SMTP configurado').classes('text-[10px] text-green-4 font-bold')
                                                            else:
                                                                ui.label('🔴 SMTP não configurado').classes('text-[10px] text-red-4 font-bold')
                                                                ui.label('Configure em Configurações → SMTP de E-mail').classes('text-[9px] text-grey-5')

                                                    ui.separator().style('background: rgba(0,229,255,0.1); margin-top:12px;')

                                                    with ui.row().classes('w-full justify-between items-center q-mt-sm'):
                                                        ui.button('Cancelar', on_click=mail_diag.close).props('flat color=grey')
                                                        ui.button('Enviar E-mail', icon='send', on_click=lambda: disparar_email()).props('unelevated color=primary text-color=black bold')

                                                async def gerar_felicitacao_ia():
                                                    ui.notify('IA redigindo mensagem...', color='info')
                                                    texto_gerado = ai_helper.generate_birthday_card_message(
                                                        nome=militar['nome'],
                                                        posto=militar['posto'],
                                                        setor=militar['setor'],
                                                        tom=sel_tom_mail.value
                                                    )
                                                    corpo_input.value = texto_gerado
                                                    ui.notify('Mensagem gerada com sucesso!', color='success')

                                                async def disparar_email():
                                                    if not corpo_input.value.strip():
                                                        ui.notify('Escreva ou gere a mensagem antes de enviar!', color='warning')
                                                        return
                                                    ui.notify(f"Enviando para {militar['email']}...", color='info')
                                                    import smtplib, ssl
                                                    from email.mime.multipart import MIMEMultipart
                                                    from email.mime.text import MIMEText
                                                    try:
                                                        smtp_host = ai_helper.get_config_value('smtp_host', 'smtp.gmail.com')
                                                        smtp_port = int(ai_helper.get_config_value('smtp_port', '587'))
                                                        smtp_user = ai_helper.get_config_value('smtp_user', '')
                                                        smtp_pass = ai_helper.get_config_value('smtp_password', '')
                                                        from_name = ai_helper.get_config_value('smtp_from_name', 'SisGAB - Gabinete')

                                                        if not smtp_user or not smtp_pass:
                                                            ui.notify('⚠️ SMTP não configurado. Acesse Configurações → SMTP de E-mail.', color='warning', timeout=6000)
                                                            return

                                                        msg = MIMEMultipart('alternative')
                                                        msg['Subject'] = assunto_input.value
                                                        msg['From'] = f'{from_name} <{smtp_user}>'
                                                        msg['To'] = militar['email']

                                                        corpo_html = f"""
                                                        <html><body style="font-family:serif;color:#222;">
                                                        <p>{corpo_input.value.replace(chr(10), '<br>')}</p>
                                                        <hr style="margin-top:20px;"><p style="font-size:11px;color:#888;">{from_name} · {militar['setor']}</p>
                                                        </body></html>"""

                                                        msg.attach(MIMEText(corpo_input.value, 'plain', 'utf-8'))
                                                        msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))

                                                        ctx = ssl.create_default_context()
                                                        with smtplib.SMTP(smtp_host, smtp_port) as server:
                                                            server.ehlo()
                                                            server.starttls(context=ctx)
                                                            server.login(smtp_user, smtp_pass)
                                                            server.sendmail(smtp_user, militar['email'], msg.as_string())

                                                        EMAILS_ENVIADOS.add(key)
                                                        ui.notify(f"✅ E-mail enviado para {militar['email']}!", color='success', timeout=5000)
                                                        mail_diag.close()
                                                        render_content.refresh()

                                                    except smtplib.SMTPAuthenticationError:
                                                        ui.notify('❌ Falha de autenticação SMTP. Verifique usuário e senha.', color='negative', timeout=7000)
                                                    except smtplib.SMTPConnectError:
                                                        ui.notify('❌ Não foi possível conectar ao servidor SMTP.', color='negative', timeout=7000)
                                                    except Exception as ex:
                                                        ui.notify(f'❌ Erro ao enviar: {ex}', color='negative', timeout=7000)

                                                mail_diag.open()
                                            
                                            if enviado_key in EMAILS_ENVIADOS:
                                                ui.icon('verified', color='success', size='sm').classes('q-mr-xs')
                                                ui.label('Enviado').classes('text-[10px] text-green-4 font-bold')
                                            else:
                                                btn_mail = ui.button(icon='mail', on_click=lambda mil=a, k=enviado_key: abrir_confirmacao_email(mil, k)).props('flat round color=grey dense').style('font-size:0.9rem;')
                                                with btn_mail:
                                                    ui.tooltip('Confirmar e Enviar E-mail')

                                            # Botão Editar
                                            def abrir_edicao(p=a):
                                                with ui.dialog() as ed_diag, ui.card().classes('w-[440px] q-pa-md').style(f'background:{THEME["bg_panel"]}; border:1px solid {THEME["border"]};'):
                                                    ui.label(f'✏️ Editar — {p["nome"]}').classes('text-white text-md font-bold cyber-title q-mb-sm')
                                                    e_cat    = ui.select({'militar':'Militar','autoridade':'Autoridade','visitante_civil':'Visitante/Civil'}, value=p['categoria'], label='Categoria').props('dark outlined dense option-dark').classes('w-full')
                                                    e_nome   = ui.input('Nome', value=p['nome']).props('dark outlined dense').classes('w-full')
                                                    e_posto  = ui.input('Posto / Cargo', value=p['posto']).props('dark outlined dense').classes('w-full')
                                                    e_setor  = ui.input('Setor', value=p['setor']).props('dark outlined dense').classes('w-full')
                                                    e_origem = ui.input('Origem', value=p['origem']).props('dark outlined dense').classes('w-full')
                                                    e_email  = ui.input('E-mail', value=p['email'] or '').props('dark outlined dense').classes('w-full')
                                                    def salvar_edicao(pid=p['id']):
                                                        conn = get_db_connection()
                                                        if conn:
                                                            try:
                                                                conn.table('efetivo').update({
                                                                    'nome_guerra': e_nome.value.upper(),
                                                                    'posto': e_posto.value.upper(),
                                                                    'setor': e_setor.value,
                                                                    'origem': e_origem.value,
                                                                    'email': e_email.value,
                                                                    'categoria': e_cat.value,
                                                                }).eq('id', pid).execute()
                                                                ui.notify('Cadastro atualizado!', color='success')
                                                                ed_diag.close()
                                                                render_content.refresh()
                                                            except Exception as ex:
                                                                ui.notify(f'Erro: {ex}', color='red')
                                                    with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                                        ui.button('Cancelar', on_click=ed_diag.close).props('flat color=grey')
                                                        ui.button('Salvar', on_click=salvar_edicao).props('unelevated color=primary text-color=black bold')
                                                ed_diag.open()

                                            def confirmar_exclusao(p=a):
                                                with ui.dialog() as del_diag, ui.card().classes('w-80 q-pa-md').style(f'background:{THEME["bg_panel"]}; border:1px solid #b71c1c;'):
                                                    ui.label('⚠️ Confirmar Exclusão').classes('text-red-4 text-md font-bold q-mb-xs')
                                                    ui.label(f'Remover {p["posto"]} {p["nome"]} permanentemente?').classes('text-xs text-grey-3 q-mb-md')
                                                    def excluir(pid=p['id']):
                                                        conn = get_db_connection()
                                                        if conn:
                                                            try:
                                                                conn.table('efetivo').delete().eq('id', pid).execute()
                                                                ui.notify('Registro excluído.', color='warning')
                                                                del_diag.close()
                                                                render_content.refresh()
                                                            except Exception as ex:
                                                                ui.notify(f'Erro: {ex}', color='red')
                                                    with ui.row().classes('w-full justify-end gap-2'):
                                                        ui.button('Cancelar', on_click=del_diag.close).props('flat color=grey')
                                                        ui.button('Excluir', icon='delete', on_click=excluir).props('unelevated color=red text-color=white bold')
                                                del_diag.open()

                                            btn_ed = ui.button(icon='edit', on_click=lambda p=a: abrir_edicao(p)).props('flat round color=cyan-3 dense size=sm')
                                            with btn_ed: ui.tooltip('Editar cadastro')
                                            btn_del = ui.button(icon='delete', on_click=lambda p=a: confirmar_exclusao(p)).props('flat round color=red-4 dense size=sm')
                                            with btn_del: ui.tooltip('Excluir')

                                            # Disparar gerador de cartão
                                            ui.button(
                                                'Cartão', 
                                                icon='style', 
                                                on_click=lambda mil=a: abrir_painel_cartao(mil)
                                            ).props('unelevated color=cyan-10 text-color=white dense').classes('text-[10px] q-px-sm')
                    else:
                        with ui.column().classes('w-full h-40 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('cake', size='3rem')
                            ui.label('Nenhum aniversariante encontrado neste mês.').classes('text-xs')

            # 2. Coluna da Direita: Datas Comemorativas (Diferente da MB estática, agora dinâmica)
            with ui.column().classes('col-12 col-md q-pa-none').style('min-width: 320px;'):
                with ui.card().classes('w-full q-pa-md no-shadow rounded-xl').style(
                    f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]}; min-height: 520px;'
                ):
                    with ui.row().classes('w-full justify-between items-center q-mb-md no-wrap'):
                        ui.label('⚓ Datas Navais & Comemorações').classes('text-md font-bold text-white')
                        
                        # Cadastro de Nova data comemorativa
                        def abrir_cadastro_data():
                            with ui.dialog() as diag, ui.card().classes('w-96 q-pa-md').style(f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'):
                                ui.label('Nova Data Comemorativa').classes('text-white text-md font-bold cyber-title')
                                input_dia = ui.input('Dia (Ex: 08)').props('dark outlined dense w-full')
                                input_mes = ui.input('Mês (Ex: 12)').props('dark outlined dense w-full')
                                input_titulo = ui.input('Título da Celebração').props('dark outlined dense w-full')
                                
                                def cadastrar_data():
                                    if not input_dia.value or not input_mes.value or not input_titulo.value:
                                        ui.notify('Todos os campos são obrigatórios!', color='warning')
                                        return
                                    conn = get_db_connection()
                                    if conn:
                                        try:
                                            conn.table('datas_comemorativas').insert({
                                                'dia': f"{int(input_dia.value):02d}",
                                                'mes': f"{int(input_mes.value):02d}",
                                                'titulo': input_titulo.value,
                                                'criado_em': datetime.now().isoformat()
                                            }).execute()
                                            ui.notify('Celebração salva com sucesso!', color='success')
                                            diag.close()
                                            render_content.refresh()
                                        except Exception as ex:
                                            ui.notify(f'Erro ao registrar data: {ex}', color='red')
                                
                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=diag.close).props('flat color=grey')
                                    ui.button('Cadastrar', on_click=cadastrar_data).props('unelevated color=primary text-color=black')
                            diag.open()

                        ui.button('Nova Celebração', icon='event', on_click=abrir_cadastro_data).props('unelevated color=primary text-color=black bold dense').classes('text-xs q-px-sm')

                    # Mostra TODAS as datas cadastradas (todos os meses), ordenadas por mês/dia
                    # O mês atual recebe destaque visual
                    datas_ordenadas = sorted(
                        datas_comemorativas,
                        key=lambda d: (int(d.get('mes','0')), int(d.get('dia','0')))
                    )

                    if datas_ordenadas:
                        _mes_header = None
                        MESES_NOMES = {
                            '01':'Janeiro','02':'Fevereiro','03':'Março','04':'Abril',
                            '05':'Maio','06':'Junho','07':'Julho','08':'Agosto',
                            '09':'Setembro','10':'Outubro','11':'Novembro','12':'Dezembro'
                        }
                        with ui.column().classes('w-full gap-1'):
                            for d in datas_ordenadas:
                                mes_d = str(d.get('mes','0')).zfill(2)
                                is_mes_atual = (int(mes_d) == mes_atual)

                                # Cabeçalho separador de mês
                                if mes_d != _mes_header:
                                    _mes_header = mes_d
                                    cor_hdr = '#00e5ff' if is_mes_atual else '#888'
                                    ui.label(MESES_NOMES.get(mes_d, mes_d)).classes('text-[10px] font-bold tracking-wider q-mt-sm').style(f'color:{cor_hdr}; text-transform:uppercase;')

                                # Linha da data
                                borda_cor  = '#ffb300' if is_mes_atual else '#444'
                                bg_opacity = '0.06' if is_mes_atual else '0.01'
                                with ui.card().classes('w-full q-pa-xs no-shadow rounded-md').style(
                                    f'background:rgba(255,179,0,{bg_opacity}); border-left:3px solid {borda_cor};'
                                ):
                                    with ui.row().classes('w-full justify-between items-center no-wrap'):
                                        with ui.row().classes('items-center gap-2 grow'):
                                            ui.label(f"{d['dia']}/{mes_d}").classes('text-[10px] text-amber-5 font-mono font-bold').style('min-width:36px;')
                                            ui.label(d['titulo']).classes('text-xs font-bold text-white')

                                        # Botões editar / excluir data
                                        with ui.row().classes('gap-1 shrink-0'):
                                            def abrir_edicao_data(dd=d):
                                                with ui.dialog() as ed_d, ui.card().classes('w-80 q-pa-md').style(f'background:{THEME["bg_panel"]}; border:1px solid {THEME["border"]};'):
                                                    ui.label('✏️ Editar Data').classes('text-white text-md font-bold cyber-title q-mb-sm')
                                                    ed_dia    = ui.input('Dia', value=str(dd['dia'])).props('dark outlined dense').classes('w-full')
                                                    ed_mes_i  = ui.input('Mês (número)', value=str(dd['mes'])).props('dark outlined dense').classes('w-full')
                                                    ed_titulo = ui.input('Título', value=dd['titulo']).props('dark outlined dense').classes('w-full')
                                                    def salvar_data(did=dd['id']):
                                                        conn = get_db_connection()
                                                        if conn:
                                                            try:
                                                                conn.table('datas_comemorativas').update({
                                                                    'dia': f"{int(ed_dia.value):02d}",
                                                                    'mes': f"{int(ed_mes_i.value):02d}",
                                                                    'titulo': ed_titulo.value,
                                                                }).eq('id', did).execute()
                                                                ui.notify('Data atualizada!', color='success')
                                                                ed_d.close()
                                                                render_content.refresh()
                                                            except Exception as ex:
                                                                ui.notify(f'Erro: {ex}', color='red')
                                                    with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                                        ui.button('Cancelar', on_click=ed_d.close).props('flat color=grey')
                                                        ui.button('Salvar', on_click=salvar_data).props('unelevated color=primary text-color=black bold')
                                                ed_d.open()

                                            def excluir_data(dd=d):
                                                conn = get_db_connection()
                                                if conn:
                                                    try:
                                                        conn.table('datas_comemorativas').delete().eq('id', dd['id']).execute()
                                                        ui.notify('Data removida.', color='warning')
                                                        render_content.refresh()
                                                    except Exception as ex:
                                                        ui.notify(f'Erro: {ex}', color='red')

                                            ui.button(icon='edit',   on_click=lambda dd=d: abrir_edicao_data(dd)).props('flat round color=amber-4 dense size=xs')
                                            ui.button(icon='delete', on_click=lambda dd=d: excluir_data(dd)).props('flat round color=red-4 dense size=xs')
                    else:
                        with ui.column().classes('w-full h-32 items-center justify-center gap-2 text-grey-5'):
                            ui.icon('anchor', size='2.5rem')
                            ui.label('Nenhuma data comemorativa cadastrada ainda.').classes('text-xs')

    # Cartão de Aniversário — painel redesenhado com temas e impressão limpa
    def abrir_painel_cartao(militar):
        custom_header = "GABINETE DO COMANDO" if militar['categoria'] != 'militar' else "MARINHA DO BRASIL"
        custom_footer  = "Chefia de Gabinete"  if militar['categoria'] != 'militar' else "Comunicação Social — COMSOC"

        # temas de fundo do cartão: (label, css_background, cor_texto, cor_borda, cor_header)
        TEMAS = {
            'navy': (
                'Azul Naval',
                'linear-gradient(145deg,#0a1628 0%,#0d2247 45%,#0a3060 100%)',
                '#ffffff', '#c0a060', '#e8c97a'
            ),
            'gold': (
                'Dourado Clássico',
                'linear-gradient(145deg,#2c1a00 0%,#5c3600 50%,#3a2200 100%)',
                '#f5e6c0', '#c0a060', '#ffd77a'
            ),
            'anchor': (
                'Âncora (Escuro)',
                'linear-gradient(160deg,#111820 0%,#1a2535 60%,#0f1922 100%)',
                '#dce8f5', '#3a7ca5', '#7ec8e3'
            ),
            'branco': (
                'Branco Formal',
                'linear-gradient(160deg,#ffffff 0%,#f0f4fb 100%)',
                '#1a2540', '#1a2540', '#1a3a6a'
            ),
        }

        MOLDURAS = {
            'dupla':     'Dupla Linha Clássica',
            'cantos':    'Cantos Decorativos',
            'simples':   'Linha Simples',
            'nenhuma':   'Sem Moldura',
        }

        _state = {
            'tema':    'navy',
            'moldura': 'dupla',
            'header':  custom_header,
            'footer':  custom_footer,
            'logo':    'sim',
            'texto':   '',
        }

        with ui.dialog() as card_dialog, ui.card().classes('q-pa-lg').style(
            f'background:{THEME["bg_panel"]}; border:1px solid {THEME["border"]}; width:860px; max-width:97vw;'
        ):
            with ui.row().classes('w-full items-center gap-3 q-mb-sm no-wrap'):
                ui.icon('style', color='cyan', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('Cartão de Felicitações').classes('text-white text-md font-bold cyber-title')
                    ui.label(f"{militar['posto']} {militar['nome']} · {militar['setor']}").classes('text-[11px] text-grey-4')
            ui.separator().style('background:rgba(0,229,255,0.1);')

            with ui.row().classes('w-full gap-4 q-mt-sm items-start no-wrap'):

                # ── PAINEL ESQUERDO — controles ──────────────────────────────
                with ui.column().classes('gap-3').style('width:240px; min-width:240px;'):
                    ui.label('⚙️ Configurações').classes('text-[11px] font-bold text-cyan tracking-wider')

                    head_input = ui.input('Cabeçalho', value=_state['header']).props('dark outlined dense').classes('w-full')
                    foot_input = ui.input('Assinatura', value=_state['footer']).props('dark outlined dense').classes('w-full')

                    sel_logo = ui.select(
                        {'sim': '✔ Com Brasão da OM', 'nao': '✘ Sem Brasão'},
                        value='sim', label='Brasão'
                    ).props('dark outlined dense option-dark').classes('w-full')

                    sel_tema = ui.select(
                        {k: v[0] for k, v in TEMAS.items()},
                        value='navy', label='Tema de Fundo'
                    ).props('dark outlined dense option-dark').classes('w-full')

                    sel_moldura = ui.select(
                        MOLDURAS, value='dupla', label='Moldura'
                    ).props('dark outlined dense option-dark').classes('w-full')

                    with ui.row().classes('w-full gap-2 no-wrap'):
                        sel_tamanho = ui.select(
                            {'a6':'A6 (105×148mm)', 'a5':'A5 (148×210mm)', 'sq':'Quadrado (148×148mm)'},
                            value='a6', label='Tamanho'
                        ).props('dark outlined dense option-dark').classes('w-1/2')
                        sel_orient = ui.select(
                            {'portrait':'📘 Retrato', 'landscape':'📙 Paisagem'},
                            value='portrait', label='Orientação'
                        ).props('dark outlined dense option-dark').classes('w-1/2')

                    sel_tom = ui.select(
                        {
                            'institucional': '🎖️ Institucional',
                            'amigavel':      '🤝 Amigável',
                            'poetico':       '🌊 Poético',
                            'humorado':      '😄 Descontraído',
                        },
                        value='amigavel', label='Tom da Mensagem'
                    ).props('dark outlined dense option-dark').classes('w-full')

                    texto_card = ui.textarea('Mensagem').props('dark outlined autogrow').classes('w-full text-xs').style('min-height:110px;')

                    async def gerar_mensagem_ia():
                        ui.notify('IA criando redação...', color='info')
                        texto_card.value = ai_helper.generate_birthday_card_message(
                            nome=militar['nome'], posto=militar['posto'],
                            setor=militar['setor'], tom=sel_tom.value
                        )
                        ui.notify('Redação pronta!', color='success')
                        _render_preview()

                    ui.button('✨ Gerar com IA', icon='psychology', on_click=gerar_mensagem_ia).props(
                        'unelevated color=cyan text-color=black bold'
                    ).classes('w-full')

                # ── PAINEL DIREITO — preview do cartão ──────────────────────
                with ui.column().classes('gap-2 items-center').style('flex:1; min-width:0;'):
                    preview_label = ui.label('👁️ Preview').classes('text-[11px] font-bold text-cyan tracking-wider')

                    # Elemento HTML do preview — totalmente gerado via JS para perfeita fidelidade
                    card_preview = ui.html('').style(
                        'border-radius:10px; overflow:hidden; '
                        'box-shadow: 0 8px 32px rgba(0,0,0,0.55);'
                    )

                    def _render_preview():
                        # Dimensoes baseadas no tamanho + orientação
                        t_key = sel_tamanho.value
                        t_data = TAMANHOS.get(t_key, TAMANHOS['a6'])
                        mm_w, mm_h, px_w, px_h = t_data
                        if sel_orient.value == 'landscape':
                            mm_w, mm_h = mm_h, mm_w
                            px_w, px_h = px_h, px_w
                        # Limita height para caber no diálogo
                        max_h = 520
                        if px_h > max_h:
                            scale = max_h / px_h
                            px_w = int(px_w * scale)
                            px_h = max_h

                        tamanho_nome = {'a6':'A6','a5':'A5','sq':'Quadrado'}[t_key]
                        orient_nome  = 'Retrato' if sel_orient.value == 'portrait' else 'Paisagem'
                        preview_label.text = f'👁️ Preview — {tamanho_nome} ({mm_w}×{mm_h}mm) · {orient_nome}'

                        card_preview.style(
                            f'width:{px_w}px; height:{px_h}px; border-radius:10px; overflow:hidden; '
                            'box-shadow: 0 8px 32px rgba(0,0,0,0.55);'
                        )

                        tema = TEMAS.get(sel_tema.value, TEMAS['navy'])
                        bg, txt_color, borda, hdr_color = tema[1], tema[2], tema[3], tema[4]
                        moldura = sel_moldura.value
                        logo_b64 = LOGO_BASE64 if sel_logo.value == 'sim' else ''
                        saudacao = (
                            f"Prezado {militar['posto']} {militar['nome']},"
                            if militar['categoria'] == 'militar'
                            else f"Ao Exmo. Sr. {militar['nome']},"
                        )

                        # Moldura CSS
                        border_css = ''
                        before_after = ''
                        if moldura == 'dupla':
                            border_css = f'border:3px solid {borda}; outline:1.5px solid {borda}; outline-offset:-8px;'
                        elif moldura == 'simples':
                            border_css = f'border:2px solid {borda};'
                        elif moldura == 'cantos':
                            border_css = f'border:1px solid {borda};'
                            before_after = f'''
                                <div style="position:absolute;top:6px;left:6px;width:20px;height:20px;
                                    border-top:2px solid {borda};border-left:2px solid {borda};"></div>
                                <div style="position:absolute;top:6px;right:6px;width:20px;height:20px;
                                    border-top:2px solid {borda};border-right:2px solid {borda};"></div>
                                <div style="position:absolute;bottom:6px;left:6px;width:20px;height:20px;
                                    border-bottom:2px solid {borda};border-left:2px solid {borda};"></div>
                                <div style="position:absolute;bottom:6px;right:6px;width:20px;height:20px;
                                    border-bottom:2px solid {borda};border-right:2px solid {borda};"></div>'''

                        logo_html = f'<img src="{logo_b64}" style="width:52px;height:52px;object-fit:contain;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.4));margin-bottom:4px;">' if logo_b64 else ''
                        texto_br  = (texto_card.value or '').replace('\n', '<br>')

                        html = f'''
                        <div style="
                            width:{px_w}px; height:{px_h}px; position:relative; box-sizing:border-box;
                            background:{bg}; color:{txt_color};
                            font-family:'Georgia',serif; {border_css}
                            display:flex; flex-direction:column;
                            align-items:center; justify-content:space-between;
                            padding:22px 20px 18px;
                        ">
                            {before_after}
                            <!-- TOPO -->
                            <div style="display:flex;flex-direction:column;align-items:center;gap:5px;width:100%;">
                                {logo_html}
                                <div style="font-size:9px;font-weight:900;letter-spacing:2.5px;color:{hdr_color};
                                    text-transform:uppercase;text-align:center;
                                    border-bottom:1px solid {borda};padding-bottom:5px;width:100%;">
                                    {head_input.value or custom_header}
                                </div>
                            </div>
                            <!-- CORPO -->
                            <div style="flex:1;display:flex;flex-direction:column;justify-content:center;
                                width:100%;padding:10px 0 6px;gap:8px;">
                                <div style="font-size:10px;font-weight:700;color:{hdr_color};">{saudacao}</div>
                                <div style="font-size:10.5px;line-height:1.65;text-align:justify;color:{txt_color};
                                    font-style:italic;">
                                    {texto_br if texto_br else '<span style="opacity:0.35;">O texto da mensagem aparecerá aqui...</span>'}
                                </div>
                            </div>
                            <!-- RODAPÉ -->
                            <div style="width:100%;text-align:center;border-top:1px solid {borda};padding-top:7px;">
                                <div style="font-size:8.5px;color:{hdr_color};font-weight:700;letter-spacing:1px;text-transform:uppercase;">
                                    {foot_input.value or custom_footer}
                                </div>
                            </div>
                        </div>'''
                        card_preview.content = html

                    # Atualiza preview ao mudar qualquer campo
                    for elem in [head_input, foot_input, texto_card]:
                        elem.on('update:model-value', lambda _: _render_preview())
                    for elem in [sel_logo, sel_tema, sel_moldura, sel_tamanho, sel_orient]:
                        elem.on('update:model-value', lambda _: _render_preview())

                    _render_preview()  # render inicial

            ui.separator().style('background:rgba(0,229,255,0.1);margin-top:12px;')

            with ui.row().classes('w-full justify-between items-center q-mt-sm'):
                ui.button('Fechar', on_click=card_dialog.close).props('flat color=grey')

                async def imprimir_cartao():
                    tema = TEMAS.get(sel_tema.value, TEMAS['navy'])
                    bg, txt_color, borda, hdr_color = tema[1], tema[2], tema[3], tema[4]
                    moldura = sel_moldura.value
                    logo_b64 = LOGO_BASE64 if sel_logo.value == 'sim' else ''
                    saudacao = (
                        f"Prezado {militar['posto']} {militar['nome']},"
                        if militar['categoria'] == 'militar'
                        else f"Ao Exmo. Sr. {militar['nome']},"
                    )
                    border_css = ''
                    before_after = ''
                    if moldura == 'dupla':
                        border_css = f'border:3px solid {borda}; outline:1.5px solid {borda}; outline-offset:-8px;'
                    elif moldura == 'simples':
                        border_css = f'border:2px solid {borda};'
                    elif moldura == 'cantos':
                        border_css = f'border:1px solid {borda};'
                        before_after = f'''
                            <div style="position:absolute;top:8px;left:8px;width:24px;height:24px;
                                border-top:2px solid {borda};border-left:2px solid {borda};"></div>
                            <div style="position:absolute;top:8px;right:8px;width:24px;height:24px;
                                border-top:2px solid {borda};border-right:2px solid {borda};"></div>
                            <div style="position:absolute;bottom:8px;left:8px;width:24px;height:24px;
                                border-bottom:2px solid {borda};border-left:2px solid {borda};"></div>
                            <div style="position:absolute;bottom:8px;right:8px;width:24px;height:24px;
                                border-bottom:2px solid {borda};border-right:2px solid {borda};"></div>'''
                    logo_html = f'<img src="{logo_b64}" style="width:60px;height:60px;object-fit:contain;margin-bottom:6px;">' if logo_b64 else ''
                    texto_br  = (texto_card.value or '').replace('\n', '<br>')

                    html_print = f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
                    <style>
                        @page {{
                            size: 105mm 148mm;
                            margin: 0;
                        }}
                        * {{ margin:0; padding:0; box-sizing:border-box; }}
                        body {{ width:105mm; height:148mm; overflow:hidden; }}
                        .card {{
                            width:105mm; height:148mm; position:relative;
                            background:{bg}; color:{txt_color};
                            font-family:'Georgia',serif;
                            {border_css}
                            display:flex; flex-direction:column;
                            align-items:center; justify-content:space-between;
                            padding:22px 18px 16px;
                        }}
                    </style></head><body>
                    <div class="card">
                        {before_after}
                        <div style="display:flex;flex-direction:column;align-items:center;gap:6px;width:100%;">
                            {logo_html}
                            <div style="font-size:8.5px;font-weight:900;letter-spacing:2.5px;color:{hdr_color};
                                text-transform:uppercase;text-align:center;
                                border-bottom:1px solid {borda};padding-bottom:5px;width:100%;">
                                {head_input.value or custom_header}
                            </div>
                        </div>
                        <div style="flex:1;display:flex;flex-direction:column;justify-content:center;
                            width:100%;padding:10px 0 6px;gap:9px;">
                            <div style="font-size:9.5px;font-weight:700;color:{hdr_color};">{saudacao}</div>
                            <div style="font-size:10px;line-height:1.7;text-align:justify;color:{txt_color};font-style:italic;">
                                {texto_br}
                            </div>
                        </div>
                        <div style="width:100%;text-align:center;border-top:1px solid {borda};padding-top:7px;">
                            <div style="font-size:8px;color:{hdr_color};font-weight:700;letter-spacing:1.2px;text-transform:uppercase;">
                                {foot_input.value or custom_footer}
                            </div>
                        </div>
                    </div>
                    <script>window.onload=function(){{window.print();window.close();}}</script>
                    </body></html>'''

                    js = f"""
                    var w = window.open('','_blank','width=400,height=600');
                    w.document.write({repr(html_print)});
                    w.document.close();
                    """
                    await ui.run_javascript(js)

                ui.button('🖨️ Imprimir / PDF', icon='print', on_click=imprimir_cartao).props(
                    'unelevated color=primary text-color=black bold'
                )
        card_dialog.open()

    # Barra de Filtros
    with ui.card().classes('w-full q-pa-md no-shadow rounded-xl q-mb-md').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.row().classes('w-full items-center gap-4 wrap justify-start'):
            # Filtro por mês
            sel_mes = ui.select(
                {
                    '1': 'Janeiro', '2': 'Fevereiro', '3': 'Março', '4': 'Abril',
                    '5': 'Maio', '6': 'Junho', '7': 'Julho', '8': 'Agosto',
                    '9': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
                },
                value=state['mes_filtro'],
                label='Mês'
            ).props('dark outlined dense option-dark').classes('w-32')
            
            # Filtro de categorias
            sel_cat = ui.select(
                {
                    'todos': 'Todas Categorias',
                    'militar': 'Militares (Efetivo)',
                    'autoridade': 'Autoridades Civis',
                    'visitante_civil': 'Visitantes'
                },
                value=state['categoria_filtro'],
                label='Categoria'
            ).props('dark outlined dense option-dark').classes('w-44')
            
            txt_busca = ui.input(
                label='Buscar Pessoa', 
                placeholder='Ex: Setor, Origem, Nome, Posto...'
            ).props('dark outlined dense').classes('grow')
            
            def atualizar_filtros():
                state['mes_filtro'] = sel_mes.value
                state['categoria_filtro'] = sel_cat.value
                state['search'] = txt_busca.value or ''
                render_content.refresh()
                
            ui.button('Filtrar', icon='search', on_click=atualizar_filtros).props('unelevated color=primary text-color=black bold').classes('q-px-lg cyber-glow')

    render_content()
