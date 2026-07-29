# modules/comsoc_tarefas.py
# Módulo de Gestão de Tarefas Internas COMSOC — Quadro Kanban
# Filtra demandas_comunicacao excluindo categoria 'audiovisual' (pautas de eventos)
from datetime import datetime, date
import json
from nicegui import ui, app
import theme
from database import get_service_db_connection, get_db_connection

THEME = theme.colors

# Categorias que são TAREFAS (não pautas audiovisuais de evento)
CATEGORIAS_TAREFA = {
    'design_arte':       ('🎨', 'Design / Arte Visual',         '#00e5ff'),
    'impressos_albuns':  ('📕', 'Impressos & Encadernação',      '#f59e0b'),
    'brindes_lembrancas':('🎁', 'Brindes & Lembranças',         '#a78bfa'),
    'redacao_textos':    ('✍️', 'Redação & Discursos',           '#34d399'),
    'suporte_evento':    ('📦', 'Suporte Logístico',             '#fb923c'),
    'outra_tarefa':      ('⚡', 'Outra Tarefa Especial',         '#f472b6'),
}

PRIORIDADES = {
    'urgente': ('🔴', 'Urgente',  'red'),
    'alta':    ('🟠', 'Alta',     'orange'),
    'normal':  ('🔵', 'Normal',   'blue'),
    'baixa':   ('⚪', 'Baixa',    'grey'),
}

# Colunas Kanban: status_key -> (label, icone, cor_borda)
KANBAN_COLS = [
    ('backlog',   '📥 Backlog',         'rgba(100,116,139,0.5)'),
    ('execucao',  '🔄 Em Execução',     'rgba(0,229,255,0.4)'),
    ('revisao',   '👀 Aguardando Revisão','rgba(251,191,36,0.5)'),
    ('concluida', '✅ Concluída',        'rgba(52,211,153,0.4)'),
]

# Mapeamento de status DB → coluna kanban
def status_para_coluna(status: str) -> str:
    s = str(status or '').strip().lower()
    if s in ('pendente', 'pendentes', 'aprovado', 'aprovada', 'aprovadas'):
        return 'backlog'
    if s in ('em_execucao', 'em execução', 'execucao'):
        return 'execucao'
    if s in ('ajustes', 'ajuste', 'revisao', 'revisão'):
        return 'revisao'
    if s in ('concluida', 'concluída', 'concluido', 'concluído'):
        return 'concluida'
    return 'backlog'

def coluna_para_status(coluna: str) -> str:
    mapa = {
        'backlog':  'pendente',
        'execucao': 'em_execucao',
        'revisao':  'ajustes',
        'concluida':'concluida',
    }
    return mapa.get(coluna, 'pendente')

def get_rank_seniority(rank_str):
    if not rank_str:
        return 99
    rank = str(rank_str).upper().replace('.', '').replace(' ', '').strip()
    if rank in ('AE', 'ALMIRANTEDEESQUADRA'): return 1
    if rank in ('VA', 'VICEALMIRANTE'): return 2
    if rank in ('CA', 'CONTRAALMIRANTE'): return 3
    if rank in ('CMG', 'CAPITAODEMAREGUERRA'): return 4
    if rank in ('CF', 'CAPITAODEFRAGATA'): return 5
    if rank in ('CC', 'CAPITAODEFRAGATA'): return 6
    if rank in ('CT', 'CAPITAOTENENTE'): return 7
    if any(x in rank for x in ('1TEN', '1ºTEN')): return 8
    if any(x in rank for x in ('2TEN', '2ºTEN')): return 9
    if rank in ('SO', 'SUBOFICIAL'): return 11
    if any(x in rank for x in ('1SG', '1ºSG')): return 12
    if any(x in rank for x in ('2SG', '2ºSG')): return 13
    if any(x in rank for x in ('3SG', '3ºSG', 'SG')): return 14
    if rank in ('CB', 'CABO'): return 15
    if rank in ('SD', 'MN'): return 16
    return 98

def sort_efetivo_list(ef_list):
    def sort_key(item):
        role = str(item.get('role', 'compel')).strip().lower()
        is_comsoc = role in ('admin', 'supervisor', 'comsoc', 'comsoc_design', 'operador')
        return (0 if is_comsoc else 1, get_rank_seniority(item.get('posto_grad') or ''), str(item.get('nome_guerra') or '').upper())
    return sorted(ef_list, key=sort_key)


# ─────────────────────────────────────────────
#  Modal: Criar Tarefa Rápida
# ─────────────────────────────────────────────
def open_nova_tarefa_dialog(efetivo_options: dict, callback_refresh=None):
    """Abre modal para criação rápida de tarefa interna (não-audiovisual)."""
    user_data = app.storage.user.get('user_data', {})
    user_name_guerra = str(user_data.get('nome_guerra', 'OPERADOR')).upper()

    with ui.dialog() as dlg, ui.card().classes('w-[680px] max-w-[96vw] q-pa-lg').style(
        'background:#131a26; border:1px solid rgba(0,229,255,0.3); max-height:92vh; overflow-y:auto;'
    ):
        ui.label('⚡ NOVA TAREFA INTERNA').classes('text-lg font-bold text-white cyber-title q-mb-sm')
        ui.label('Crie uma tarefa criativa, design, impressos ou logística — sem vínculo a evento audiovisual.').classes('text-xs text-grey-4 q-mb-md')

        with ui.column().classes('w-full gap-3'):

            # Linha 1: categoria + produto
            with ui.row().classes('w-full gap-2 no-wrap'):
                cat_sel = ui.select(
                    {k: f"{v[0]} {v[1]}" for k, v in CATEGORIAS_TAREFA.items()},
                    value='design_arte',
                    label='Categoria'
                ).props('dark outlined dense option-dark').classes('w-1/2')

                prod_in = ui.input('Produto / Peça Específica').props('dark outlined dense').classes('w-1/2')

            # Linha 2: título
            titulo_in = ui.input('Título da Tarefa').props('dark outlined dense w-full')

            # Linha 3: solicitante + setor
            with ui.row().classes('w-full gap-2 no-wrap'):
                sol_in = ui.input('Solicitante', value='CGCFN / GABINETE').props('dark outlined dense').classes('w-1/2')
                setor_in = ui.input('Setor / OM', value='Gabinete').props('dark outlined dense').classes('w-1/2')

            # Linha 4: prazo + prioridade
            with ui.row().classes('w-full gap-2 no-wrap'):
                prazo_in = ui.input('Prazo / Data de Entrega').props('type=date dark outlined dense').classes('w-1/2')
                prio_sel = ui.select(
                    {k: f"{v[0]} {v[1]}" for k, v in PRIORIDADES.items()},
                    value='normal',
                    label='Prioridade'
                ).props('dark outlined dense option-dark').classes('w-1/2')

            # Responsável
            resp_sel = ui.select(
                efetivo_options,
                value=None,
                label='👤 Responsável pela Execução'
            ).props('dark outlined dense option-dark w-full clearable')

            # Observações
            obs_in = ui.textarea('Observações / Briefing').props('dark outlined dense w-full rows=3')

            # Botões
            def salvar():
                if not titulo_in.value.strip():
                    ui.notify('Informe o título da tarefa.', color='warning')
                    return
                if not sol_in.value.strip():
                    ui.notify('Informe o solicitante.', color='warning')
                    return

                db = get_service_db_connection() or get_db_connection()
                if not db:
                    ui.notify('Sem conexão com o banco de dados.', color='negative')
                    return

                try:
                    militar_ids = [resp_sel.value] if resp_sel.value else []
                    registro = {
                        'titulo_evento': titulo_in.value.strip().upper(),
                        'categoria_demanda': cat_sel.value or 'design_arte',
                        'produto_especifico': prod_in.value.strip(),
                        'solicitante_nome': sol_in.value.strip(),
                        'setor': setor_in.value.strip(),
                        'contato': 'Interno',
                        'prioridade': prio_sel.value or 'normal',
                        'prazo_limite': prazo_in.value or '',
                        'data_evento': prazo_in.value or None,
                        'data_fim': prazo_in.value or None,
                        'hora_evento': '09:00',
                        'local_evento': 'Gabinete / CGCFN',
                        'observacoes_execucao': obs_in.value.strip(),
                        'tipo_cobertura': json.dumps([]),
                        'score_esforco': 1.0,
                        'sigiloso': 0,
                        'status': 'pendente',
                        'captacao_entrega': 'entrega_digital',
                        'notificar_militar_ids': json.dumps(militar_ids),
                        'autoridades': '',
                        'encarregado_id': resp_sel.value,
                    }
                    res = db.table('demandas_comunicacao').insert(registro).execute()
                    new_id = None
                    if res.data and isinstance(res.data, list) and len(res.data) > 0:
                        new_id = res.data[0].get('id')

                    # Histórico de tramitação
                    if new_id:
                        hist = {
                            'demanda_id': new_id,
                            'data_hora': datetime.now().isoformat(),
                            'usuario': user_name_guerra,
                            'acao': 'Tarefa Criada',
                            'parecer': f'Nova tarefa interna criada via módulo de Tarefas COMSOC. Categoria: {cat_sel.value}.'
                        }
                        db.table('demandas_historico_tramitacao').insert(hist).execute()

                    ui.notify('✅ Tarefa criada com sucesso!', color='positive')
                    dlg.close()
                    if callback_refresh:
                        callback_refresh()
                except Exception as e:
                    ui.notify(f'Erro ao criar tarefa: {e}', color='negative')
                    print(f'[NOVA TAREFA ERR] {e}')

            with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                ui.button('Cancelar', on_click=dlg.close).props('flat color=grey')
                ui.button('⚡ Criar Tarefa', on_click=salvar).props('unelevated color=cyan text-color=black bold')

    dlg.open()


# ─────────────────────────────────────────────
#  Modal: Editar Tarefa
# ─────────────────────────────────────────────
def open_editar_tarefa_dialog(tarefa: dict, efetivo_options: dict, callback_refresh=None):
    """Edição rápida de uma tarefa existente."""
    if not tarefa:
        ui.notify('Tarefa inválida.', color='warning')
        return

    user_data = app.storage.user.get('user_data', {})
    user_name_guerra = str(user_data.get('nome_guerra', 'SUPERVISOR')).upper()

    # Carrega responsável atual
    enc_id = tarefa.get('encarregado_id')
    if enc_id is not None:
        try:
            enc_id = int(str(enc_id).strip())
        except (ValueError, TypeError):
            enc_id = None

    st_val = str(tarefa.get('status', 'pendente') or 'pendente').lower()

    if enc_id is not None and enc_id not in efetivo_options:
        efetivo_options[enc_id] = f"Militar Inativo (ID: {enc_id})"

    with ui.dialog() as dlg, ui.card().classes('w-[660px] max-w-[96vw] q-pa-lg').style(
        'background:#131a26; border:1px solid rgba(0,229,255,0.3); max-height:92vh; overflow-y:auto;'
    ):
        ui.label(f'✏️ Editar Tarefa').classes('text-lg font-bold text-white cyber-title')
        ui.label(tarefa.get('titulo_evento', '')).classes('text-xs text-cyan q-mb-md')

        with ui.column().classes('w-full gap-3'):
            titulo_in = ui.input('Título da Tarefa', value=str(tarefa.get('titulo_evento', '') or '')).props('dark outlined dense w-full')

            with ui.row().classes('w-full gap-2 no-wrap'):
                cat_sel = ui.select(
                    {k: f"{v[0]} {v[1]}" for k, v in CATEGORIAS_TAREFA.items()},
                    value=tarefa.get('categoria_demanda', 'design_arte'),
                    label='Categoria'
                ).props('dark outlined dense option-dark').classes('w-1/2')
                prod_in = ui.input('Produto / Peça', value=str(tarefa.get('produto_especifico', '') or '')).props('dark outlined dense').classes('w-1/2')

            with ui.row().classes('w-full gap-2 no-wrap'):
                prazo_in = ui.input('Prazo / Data de Entrega', value=str(tarefa.get('prazo_limite') or tarefa.get('data_evento') or '')).props('type=date dark outlined dense').classes('w-1/2')
                prio_sel = ui.select(
                    {k: f"{v[0]} {v[1]}" for k, v in PRIORIDADES.items()},
                    value=tarefa.get('prioridade', 'normal'),
                    label='Prioridade'
                ).props('dark outlined dense option-dark').classes('w-1/2')

            status_sel = ui.select(
                {
                    'pendente':    '📥 Backlog (Pendente)',
                    'em_execucao': '🔄 Em Execução',
                    'ajustes':     '👀 Aguardando Revisão',
                    'concluida':   '✅ Concluída',
                },
                value=st_val if st_val in ('pendente', 'em_execucao', 'ajustes', 'concluida') else 'pendente',
                label='Status / Coluna Kanban'
            ).props('dark outlined dense option-dark w-full')

            resp_sel = ui.select(
                efetivo_options,
                value=enc_id,
                label='👤 Responsável'
            ).props('dark outlined dense option-dark w-full clearable')

            obs_in = ui.textarea('Observações / Briefing', value=str(tarefa.get('observacoes_execucao', '') or '')).props('dark outlined dense w-full rows=3')

            def salvar_edicao():
                db = get_service_db_connection() or get_db_connection()
                if not db:
                    ui.notify('Sem conexão com o banco.', color='negative')
                    return
                try:
                    militar_ids = [resp_sel.value] if resp_sel.value else []
                    payload = {
                        'titulo_evento': titulo_in.value.strip().upper(),
                        'categoria_demanda': cat_sel.value,
                        'produto_especifico': prod_in.value.strip(),
                        'prioridade': prio_sel.value or 'normal',
                        'prazo_limite': prazo_in.value or '',
                        'data_evento': prazo_in.value or None,
                        'data_fim': prazo_in.value or None,
                        'status': status_sel.value,
                        'encarregado_id': resp_sel.value,
                        'notificar_militar_ids': json.dumps(militar_ids),
                        'observacoes_execucao': obs_in.value.strip(),
                    }
                    dem_id = tarefa['id']
                    if isinstance(dem_id, str) and dem_id.isdigit():
                        dem_id = int(dem_id)
                    db.table('demandas_comunicacao').update(payload).eq('id', dem_id).execute()
                    hist = {
                        'demanda_id': dem_id,
                        'data_hora': datetime.now().isoformat(),
                        'usuario': user_name_guerra,
                        'acao': f'Tarefa Editada → {status_sel.value}',
                        'parecer': f'Atualização via módulo Tarefas COMSOC.'
                    }
                    db.table('demandas_historico_tramitacao').insert(hist).execute()
                    ui.notify('✅ Tarefa atualizada!', color='positive')
                    dlg.close()
                    if callback_refresh:
                        callback_refresh()
                except Exception as e:
                    ui.notify(f'Erro ao salvar: {e}', color='negative')
                    print(f'[EDIT TAREFA ERR] {e}')

            with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                ui.button('Cancelar', on_click=dlg.close).props('flat color=grey')
                ui.button('💾 Salvar', on_click=salvar_edicao).props('unelevated color=green text-color=white bold')

    dlg.open()


# ─────────────────────────────────────────────
#  Helper: mover status de uma tarefa
# ─────────────────────────────────────────────
def mover_status(tarefa_id, novo_status: str, usuario: str, callback_refresh=None):
    db = get_service_db_connection() or get_db_connection()
    if not db:
        ui.notify('Sem conexão com o banco.', color='negative')
        return
    try:
        if isinstance(tarefa_id, str) and tarefa_id.isdigit():
            tarefa_id = int(tarefa_id)
        db.table('demandas_comunicacao').update({'status': novo_status}).eq('id', tarefa_id).execute()
        acoes = {
            'em_execucao': 'Tarefa Iniciada / Em Execução',
            'ajustes':     'Devolvida para Revisão',
            'concluida':   'Tarefa Concluída',
            'pendente':    'Tarefa Retornada ao Backlog',
        }
        hist = {
            'demanda_id': tarefa_id,
            'data_hora': datetime.now().isoformat(),
            'usuario': usuario,
            'acao': acoes.get(novo_status, f'Status → {novo_status}'),
            'parecer': f'Movida para "{novo_status}" via módulo Tarefas COMSOC.'
        }
        db.table('demandas_historico_tramitacao').insert(hist).execute()
        if callback_refresh:
            callback_refresh()
    except Exception as e:
        ui.notify(f'Erro ao mover tarefa: {e}', color='negative')
        print(f'[MOVER STATUS ERR] {e}')


def deletar_tarefa(tarefa_id, callback_refresh=None):
    db = get_service_db_connection() or get_db_connection()
    if not db:
        ui.notify('Sem conexão.', color='negative')
        return
    try:
        if isinstance(tarefa_id, str) and tarefa_id.isdigit():
            tarefa_id = int(tarefa_id)
        db.table('demandas_comunicacao').delete().eq('id', tarefa_id).execute()
        ui.notify('🗑️ Tarefa excluída.', color='info')
        if callback_refresh:
            callback_refresh()
    except Exception as e:
        ui.notify(f'Erro ao excluir: {e}', color='negative')


# ─────────────────────────────────────────────
#  Card individual de tarefa no Kanban
# ─────────────────────────────────────────────
def render_tarefa_card(t: dict, efetivo_map: dict, usuario: str, callback_refresh, coluna_key: str, is_approver: bool):
    """Renderiza um card de tarefa dentro de uma coluna Kanban."""
    cat_key = str(t.get('categoria_demanda') or 'design_arte').strip()
    cat_info = CATEGORIAS_TAREFA.get(cat_key, ('⚡', cat_key.replace('_', ' ').title(), '#94a3b8'))
    cat_icone, cat_nome, cat_cor = cat_info

    prio_key = str(t.get('prioridade') or 'normal').strip().lower()
    prio_info = PRIORIDADES.get(prio_key, ('🔵', 'Normal', 'blue'))
    prio_badge_icone, prio_nome, prio_color = prio_info

    # Prazo
    prazo_str = str(t.get('prazo_limite') or t.get('data_evento') or '').strip()
    prazo_vencido = False
    prazo_display = '—'
    if prazo_str and prazo_str not in ('None', ''):
        try:
            prazo_dt = date.fromisoformat(prazo_str)
            prazo_display = prazo_dt.strftime('%d/%m/%Y')
            prazo_vencido = prazo_dt < date.today() and coluna_key != 'concluida'
        except ValueError:
            prazo_display = prazo_str

    # Responsável
    enc_id = t.get('encarregado_id')
    resp_nome = '—'
    if enc_id:
        try:
            enc_id_int = int(str(enc_id).strip())
            resp_nome = efetivo_map.get(enc_id_int, efetivo_map.get(str(enc_id), '—'))
            # Extrai só o nome de guerra (sem o role em parênteses)
            if '(' in resp_nome:
                resp_nome = resp_nome.split('(')[0].strip()
        except (ValueError, TypeError):
            resp_nome = str(enc_id)

    produto = str(t.get('produto_especifico') or '').strip()
    obs = str(t.get('observacoes_execucao') or '').strip()
    tarefa_id = t['id']

    border_color = 'rgba(255,23,68,0.7)' if prazo_vencido else cat_cor

    with ui.card().classes('w-full q-pa-sm no-shadow rounded-lg').style(
        f'background: rgba(19,26,38,0.95); border-left: 3px solid {border_color}; border-top: 1px solid rgba(255,255,255,0.06); border-right: 1px solid rgba(255,255,255,0.04); border-bottom: 1px solid rgba(255,255,255,0.04);'
    ):
        # Cabeçalho: categoria + prioridade
        with ui.row().classes('w-full items-center justify-between no-wrap gap-1 q-mb-xs'):
            with ui.row().classes('items-center gap-1 no-wrap'):
                ui.label(cat_icone).style(f'font-size:14px;')
                ui.label(cat_nome).classes('text-[10px] font-bold').style(f'color:{cat_cor};')
            ui.badge(f'{prio_badge_icone} {prio_nome}').props(f'color={prio_color}').classes('text-[9px]')

        # Título
        ui.label(str(t.get('titulo_evento') or 'Sem título')).classes('text-xs font-bold text-white leading-tight q-mb-xs')

        # Produto
        if produto:
            ui.label(produto).classes('text-[10px] text-grey-4 italic')

        # Prazo + Responsável
        with ui.row().classes('w-full items-center justify-between no-wrap q-mt-xs'):
            prazo_color = 'color:#ff1744;font-weight:700;' if prazo_vencido else 'color:#64748b;'
            prazo_prefix = '⚠️ ' if prazo_vencido else '📅 '
            ui.label(f'{prazo_prefix}{prazo_display}').style(f'font-size:10px; {prazo_color}')
            ui.label(f'👤 {resp_nome}').classes('text-[10px] text-grey-5')

        # Observações (colapsável se existir)
        if obs:
            with ui.expansion('📝 Briefing', value=False).classes('w-full text-[10px] text-grey-4'):
                ui.label(obs).classes('text-[10px] text-grey-3 whitespace-pre-wrap')

        ui.separator().style('background:rgba(255,255,255,0.05); margin: 6px 0;')

        # Botões de ação
        with ui.row().classes('w-full items-center gap-1 flex-wrap'):
            # Botão primário de progressão
            if coluna_key == 'backlog':
                ui.button('▶ Iniciar', on_click=lambda tid=tarefa_id: mover_status(tid, 'em_execucao', usuario, callback_refresh)).props('unelevated color=cyan text-color=black dense').classes('text-[9px] q-px-xs')
            elif coluna_key == 'execucao':
                ui.button('✅ Concluir', on_click=lambda tid=tarefa_id: mover_status(tid, 'concluida', usuario, callback_refresh)).props('unelevated color=green text-color=white dense').classes('text-[9px] q-px-xs')
                ui.button('👀 Revisão', on_click=lambda tid=tarefa_id: mover_status(tid, 'ajustes', usuario, callback_refresh)).props('unelevated color=amber text-color=black dense').classes('text-[9px] q-px-xs')
            elif coluna_key == 'revisao':
                ui.button('▶ Retomar', on_click=lambda tid=tarefa_id: mover_status(tid, 'em_execucao', usuario, callback_refresh)).props('unelevated color=cyan text-color=black dense').classes('text-[9px] q-px-xs')
                ui.button('✅ Concluir', on_click=lambda tid=tarefa_id: mover_status(tid, 'concluida', usuario, callback_refresh)).props('unelevated color=green text-color=white dense').classes('text-[9px] q-px-xs')
            elif coluna_key == 'concluida':
                ui.button('↩ Reabrir', on_click=lambda tid=tarefa_id: mover_status(tid, 'em_execucao', usuario, callback_refresh)).props('outline color=grey dense').classes('text-[9px] q-px-xs')

            # Editar sempre visível
            ui.button(
                icon='edit',
                on_click=lambda t=t: open_editar_tarefa_dialog(t, {**efetivo_map}, callback_refresh)
            ).props('flat color=cyan dense round').classes('text-[9px]')

            # Excluir: só admins/supervisores
            if is_approver:
                def confirmar_delete(tid=tarefa_id):
                    with ui.dialog() as d_conf, ui.card().style('background:#131a26; border:1px solid rgba(255,23,68,0.4);'):
                        ui.label('🗑️ Excluir Tarefa?').classes('text-sm font-bold text-white')
                        ui.label('Esta ação é irreversível.').classes('text-xs text-grey-4')
                        with ui.row().classes('justify-end gap-2 q-mt-md'):
                            ui.button('Cancelar', on_click=d_conf.close).props('flat color=grey')
                            ui.button('Excluir', on_click=lambda: (d_conf.close(), deletar_tarefa(tid, callback_refresh))).props('unelevated color=red text-color=white')
                    d_conf.open()
                ui.button(icon='delete', on_click=confirmar_delete).props('flat color=red dense round').classes('text-[9px]')


# ─────────────────────────────────────────────
#  Página Principal
# ─────────────────────────────────────────────
def render_page():
    user_data = app.storage.user.get('user_data', {})
    user_role = str(user_data.get('role', 'compel')).strip().lower()
    is_approver = user_role in ('admin', 'supervisor', 'oficial_gab', 'comsoc')
    usuario = str(user_data.get('nome_guerra', 'OPERADOR')).upper()

    with ui.column().classes('w-full q-pa-md gap-4'):

        # ── Header ──────────────────────────────────────────
        with ui.row().classes('w-full justify-between items-center bg-slate-900/60 q-pa-md rounded-xl border border-cyan-500/20 flex-wrap gap-2'):
            with ui.column().classes('gap-0'):
                ui.label('📋 GESTÃO DE TAREFAS COMSOC').classes('text-xl font-bold text-white cyber-title')
                ui.label('Quadro Kanban de Tarefas Criativas, Design, Impressos e Logística').classes('text-xs text-grey-4')

            with ui.row().classes('items-center gap-2'):
                ui.button('🔄 Recarregar', on_click=lambda: render_kanban.refresh()).props('unelevated color=cyan text-color=black dense bold icon=refresh').classes('text-xs')

        @ui.refreshable
        def render_kanban():
            # ── Carrega dados ────────────────────────────────
            db = get_service_db_connection() or get_db_connection()
            todas_tarefas: list[dict] = []
            efetivo_options: dict = {}
            efetivo_map: dict = {}

            # Função para ordenar tarefas cronologicamente (pelo prazo limite ou data do evento)
            def ordenar_cronologicamente(task_list):
                def get_sort_key(t):
                    p_date = str(t.get('prazo_limite') or t.get('data_evento') or '').strip()
                    p_time = str(t.get('hora_evento') or '').strip()
                    if not p_date or p_date == 'None' or p_date == 'null':
                        p_date = '9999-12-31'
                    if not p_time or p_time == 'None' or p_time == 'null':
                        p_time = '09:00'
                    return (p_date, p_time, int(t.get('id', 0)))
                return sorted(task_list, key=get_sort_key)

            if db:
                try:
                    res_d = db.table('demandas_comunicacao').select('*').order('id', desc=True).execute()
                    if res_d and hasattr(res_d, 'data') and res_d.data:
                        # Filtra: apenas categorias que NÃO são audiovisual
                        raw_tarefas = [
                            d for d in res_d.data
                            if isinstance(d, dict)
                            and str(d.get('categoria_demanda') or '').strip().lower() not in ('audiovisual',)
                        ]
                        todas_tarefas = ordenar_cronologicamente(raw_tarefas)
                except Exception as e:
                    print(f'[TAREFAS LOAD ERR] {e}')
                    ui.notify('Erro ao carregar tarefas.', color='warning')

                try:
                    res_ef = db.table('efetivo').select('id, nome_guerra, role, posto_grad').execute()
                    if res_ef.data:
                        sorted_ef = sort_efetivo_list(res_ef.data)
                        for item in sorted_ef:
                            label = f"{item.get('posto_grad') or ''} {item['nome_guerra']} ({item['role'].upper()})".strip()
                            efetivo_options[item['id']] = label
                            efetivo_map[item['id']] = label
                except Exception as e:
                    print(f'[EFETIVO LOAD ERR] {e}')

            # ── Filtros ──────────────────────────────────────
            with ui.row().classes('w-full items-center gap-3 flex-wrap q-mb-sm'):
                ui.label('🔎 Filtros:').classes('text-xs font-bold text-grey-4')

                filtro_cat = ui.select(
                    {'': '— Todas as Categorias —', **{k: f"{v[0]} {v[1]}" for k, v in CATEGORIAS_TAREFA.items()}},
                    value='',
                    label='Categoria'
                ).props('dark outlined dense option-dark').classes('w-44')

                filtro_resp_opts = {'': '— Todos —'}
                for eid, elabel in efetivo_options.items():
                    nome_curto = elabel.split('(')[0].strip()
                    filtro_resp_opts[str(eid)] = nome_curto
                filtro_resp = ui.select(
                    filtro_resp_opts,
                    value='',
                    label='Responsável'
                ).props('dark outlined dense option-dark').classes('w-44')

                filtro_vencidas = ui.checkbox('⚠️ Só Vencidas', value=False).classes('text-xs text-red')

            # ── KPIs ─────────────────────────────────────────
            total = len(todas_tarefas)
            em_exec = sum(1 for t in todas_tarefas if status_para_coluna(t.get('status')) == 'execucao')
            vencidas = sum(
                1 for t in todas_tarefas
                if status_para_coluna(t.get('status')) not in ('concluida',)
                and str(t.get('prazo_limite') or t.get('data_evento') or '').strip() not in ('', 'None')
                and _prazo_vencido(str(t.get('prazo_limite') or t.get('data_evento') or ''))
            )
            concluidas = sum(1 for t in todas_tarefas if status_para_coluna(t.get('status')) == 'concluida')

            with ui.row().classes('w-full gap-3 flex-nowrap q-mb-sm').style('overflow-x:auto;'):
                for kpi_label, kpi_val, kpi_color in [
                    ('Total de Tarefas', total, '#64748b'),
                    ('Em Execução', em_exec, '#00e5ff'),
                    ('⚠️ Vencidas', vencidas, '#ff1744'),
                    ('✅ Concluídas', concluidas, '#00e676'),
                ]:
                    with ui.card().classes('q-pa-sm no-shadow rounded-lg').style(
                        f'background:rgba(19,26,38,0.8); border:1px solid {kpi_color}33; min-width:140px; flex: 1;'
                    ):
                        ui.label(str(kpi_val)).style(f'font-size:1.6rem; font-weight:900; color:{kpi_color}; font-family:Rajdhani;')
                        ui.label(kpi_label).classes('text-[10px] text-grey-4')

            # Botão nova tarefa
            ui.button(
                '⚡ Nova Tarefa Interna',
                icon='add_task',
                on_click=lambda: open_nova_tarefa_dialog(efetivo_options, render_kanban.refresh)
            ).props('unelevated color=amber text-color=black bold').classes('text-xs')

            ui.separator().style('background:rgba(0,229,255,0.1); margin:8px 0;')

            # ── Aplica Filtros ───────────────────────────────
            def tarefa_visivel(t):
                cat_ok = (not filtro_cat.value) or (str(t.get('categoria_demanda') or '').strip() == filtro_cat.value)
                enc_id_t = str(t.get('encarregado_id') or '').strip()
                resp_ok = (not filtro_resp.value) or (enc_id_t == filtro_resp.value)
                venc_ok = (not filtro_vencidas.value) or (
                    status_para_coluna(t.get('status')) not in ('concluida',)
                    and str(t.get('prazo_limite') or t.get('data_evento') or '').strip() not in ('', 'None')
                    and _prazo_vencido(str(t.get('prazo_limite') or t.get('data_evento') or ''))
                )
                return cat_ok and resp_ok and venc_ok

            tarefas_filtradas = [t for t in todas_tarefas if tarefa_visivel(t)]

            # ── Quadro Kanban ────────────────────────────────
            with ui.row().classes('w-full gap-3 items-start flex-nowrap').style('overflow-x:auto; padding-bottom:8px;'):
                for col_key, col_label, col_border in KANBAN_COLS:
                    col_tarefas = [t for t in tarefas_filtradas if status_para_coluna(t.get('status')) == col_key]

                    with ui.column().classes('gap-2').style(
                        f'min-width:250px; flex:1; background:rgba(11,15,25,0.6); border:1px solid {col_border}; border-radius:10px; padding:10px;'
                    ):
                        # Cabeçalho da coluna
                        with ui.row().classes('w-full items-center justify-between q-mb-xs'):
                            ui.label(col_label).classes('text-xs font-bold text-white cyber-title')
                            ui.badge(str(len(col_tarefas))).props('color=grey-8').classes('text-[10px]')

                        ui.separator().style(f'background:{col_border}; margin-bottom:6px;')

                        if not col_tarefas:
                            ui.label('Nenhuma tarefa aqui.').classes('text-[10px] text-grey-6 text-center w-full q-py-md')
                        else:
                            for t in col_tarefas:
                                render_tarefa_card(t, efetivo_map, usuario, render_kanban.refresh, col_key, is_approver)

        render_kanban()


def _prazo_vencido(prazo_str: str) -> bool:
    try:
        return date.fromisoformat(prazo_str) < date.today()
    except (ValueError, TypeError):
        return False
