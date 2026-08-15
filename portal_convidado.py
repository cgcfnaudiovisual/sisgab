"""
portal_convidado.py — Portal do Convidado (Real-Time Hot Photo Delivery)
Módulo público de zero fricção para entrega de fotos em tempo real via reconhecimento facial.
Acesso via rota dinâmica /evento/{id_evento}.
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime
from pathlib import Path
from nicegui import ui, app
import numpy as np

import theme
from database import (
    get_public_event,
    get_event_photo_embeddings,
    save_guest_face_profile,
    save_guest_delivery,
    log_portal_analytics,
    send_real_email_smtp,
)
import drive_service

# Cache em memória da matriz de embeddings por evento (TTL: 30 segundos)
_EVENT_EMBEDDINGS_CACHE = {}


def _get_event_matrix(event_id: str) -> tuple[np.ndarray, list[dict]]:
    """Carrega matriz NxD de embeddings do evento do cache ou do banco."""
    now = time.time()
    if event_id in _EVENT_EMBEDDINGS_CACHE:
        cache = _EVENT_EMBEDDINGS_CACHE[event_id]
        if now - cache['timestamp'] < 30:
            return cache['matrix'], cache['records']

    raw_records = get_event_photo_embeddings(event_id)
    if not raw_records:
        return np.empty((0, 512), dtype=np.float32), []

    valid_vectors = []
    valid_records = []
    for r in raw_records:
        try:
            emb = json.loads(r['embedding']) if isinstance(r['embedding'], str) else r['embedding']
            if emb and len(emb) == 512:
                valid_vectors.append(np.array(emb, dtype=np.float32))
                valid_records.append(r)
        except Exception:
            continue

    if not valid_vectors:
        return np.empty((0, 512), dtype=np.float32), []

    matrix = np.stack(valid_vectors)  # Shape: (N, 512)
    _EVENT_EMBEDDINGS_CACHE[event_id] = {
        'matrix': matrix,
        'records': valid_records,
        'timestamp': now
    }
    return matrix, valid_records


def _extract_selfie_embedding(image_bytes: bytes) -> tuple[bool, str, np.ndarray | None]:
    """Extrai o embedding facial 512D da selfie com InsightFace ou evaluate_selfie_quality."""
    try:
        from sisgab_face_worker import evaluate_selfie_quality
        return evaluate_selfie_quality(image_bytes)
    except Exception as e:
        # Fallback se worker não estiver importável diretamente
        try:
            import cv2
            from insightface.app import FaceAnalysis
            app_face = FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'])
            app_face.prepare(ctx_id=-1, det_size=(320, 320))
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return False, "❌ Imagem corrompida.", None
            faces = app_face.get(img)
            if not faces:
                return False, "❌ Nenhum rosto detectado na foto.", None
            return True, "✅ Rosto identificado!", faces[0].normed_embedding
        except Exception as e_fb:
            return False, f"❌ Motor facial indisponível: {e_fb}", None


def render_page(event_id: str):
    """Renderiza a página completa do Portal do Convidado para o evento especificado."""
    theme.apply_global_styles()

    event = get_public_event(event_id)

    # ── EVENTO NÃO LOCALIZADO OU INATIVO ────────────────────────────────────
    if not event:
        with ui.column().classes('w-full min-h-screen items-center justify-center p-6 text-center').style('background: radial-gradient(circle, #1e1b4b 0%, #0b0f19 100%);'):
            ui.icon('event_busy', size='4.5rem', color='red-5')
            ui.label('EVENTO NÃO ENCONTRADO').classes('cyber-title text-2xl font-bold text-red-4 q-mt-md')
            ui.label('O link acessado não corresponde a um evento público ativo no momento.').classes('text-sm text-grey-4 max-w-md')
            ui.button('Voltar ao Início', on_click=lambda: ui.navigate.to('/')).props('flat color=cyan').classes('q-mt-lg')
        return

    if event.get('status') != 'ativo':
        with ui.column().classes('w-full min-h-screen items-center justify-center p-6 text-center').style('background: radial-gradient(circle, #1e1b4b 0%, #0b0f19 100%);'):
            ui.icon('lock_clock', size='4.5rem', color='amber-5')
            ui.label('GALERIA ENCERRADA').classes('cyber-title text-2xl font-bold text-amber-4 q-mt-md')
            ui.label(f"A galeria do evento '{event.get('nome')}' foi encerrada pela organização.").classes('text-sm text-grey-4 max-w-md')
        return

    # Registra analytics de acesso
    session_id = app.storage.user.get('portal_session_id')
    if not session_id:
        session_id = f"guest_{int(time.time()*1000)}"
        app.storage.user['portal_session_id'] = session_id
    
    log_portal_analytics(event_id, 'acesso', session_id=session_id)

    # Estado local da página do convidado
    guest_state = {
        'selfie_embeddings': [],
        'matched_photos': [],
        'geral_photos': [],
        'has_searched': False,
        'rate_limit_count': 0,
        'last_search_time': 0,
    }

    # Dados do evento
    nome_evento = event.get('nome', 'Evento Oficial')
    local_evento = event.get('local', 'Gabinete do CGCFN')
    data_str = event.get('data_evento', '')
    if data_str:
        try:
            dt = datetime.strptime(str(data_str)[:10], '%Y-%m-%d')
            data_formatada = dt.strftime('%d de %B de %Y')
        except Exception:
            data_formatada = str(data_str)
    else:
        data_formatada = ''

    banner_url = event.get('banner_url') or 'assets/brasao_cgcfn.png'
    threshold_match = float(event.get('threshold_match') or 0.45)
    drive_geral_id = event.get('drive_geral_folder_id') or event.get('drive_folder_id')

    # Container principal da página (Mobile-First, Acessível, Alto Contraste)
    with ui.column().classes('w-full min-h-screen items-center justify-start p-2 sm:p-6 bg-slate-950 text-white').style('font-family: "Outfit", sans-serif;'):
        
        # ── HERO CARD PRINCIPAL ───────────────────────────────────────────────
        with ui.card().classes('w-full max-w-3xl bg-slate-900/95 border-2 border-amber-500/30 rounded-3xl shadow-2xl overflow-hidden p-0').style('box-shadow: 0 0 50px rgba(245, 158, 11, 0.15);'):

            # Banner do Evento / Cabeçalho Institucional
            if banner_url and len(banner_url) > 10 and banner_url != 'assets/brasao_cgcfn.png':
                bg_header = f'background: linear-gradient(180deg, rgba(15, 23, 42, 0.4) 0%, rgba(15, 23, 42, 0.95) 100%), url("{banner_url}") center/cover no-repeat;'
            else:
                bg_header = 'background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);'

            with ui.element('div').classes('w-full relative min-h-[160px] flex items-center justify-center text-center p-6').style(bg_header):
                with ui.column().classes('w-full items-center gap-1 z-10'):
                    ui.image('assets/brasao_cgcfn.png').style('width: 68px; height: auto; filter: drop-shadow(0 0 10px rgba(245, 158, 11, 0.4));')
                    ui.label('MARINHA DO BRASIL').classes('text-xs font-black text-amber-4 tracking-[4px] uppercase q-mt-xs')
                    ui.label('GABINETE DO COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS').classes('text-[10px] font-bold text-cyan-3 tracking-[2px] uppercase opacity-90')

            ui.separator().style('background: linear-gradient(90deg, transparent, rgba(245, 158, 11, 0.5), transparent); height: 2px;')

            # Título e Detalhes do Evento
            with ui.column().classes('w-full p-4 sm:p-6 items-center text-center gap-2'):
                ui.label(nome_evento.upper()).classes('text-xl sm:text-2xl font-black text-white tracking-wide leading-tight')
                
                with ui.row().classes('items-center justify-center gap-4 text-xs sm:text-sm text-grey-4'):
                    if data_formatada:
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('calendar_today', size='1.1rem', color='amber-4')
                            ui.label(data_formatada).classes('font-bold text-white')
                    if local_evento:
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('place', size='1.1rem', color='cyan-4')
                            ui.label(local_evento).classes('font-medium text-grey-3')

            # ── ÁREA DINÂMICA DE CONTEÚDO ─────────────────────────────────────
            content_container = ui.column().classes('w-full p-4 sm:p-6 gap-6')

            def refresh_ui():
                content_container.clear()
                with content_container:
                    render_portal_content()

            # ── FUNÇÃO DE BUSCA FACIAL ────────────────────────────────────────
            async def handle_selfie_upload(e):
                now_t = time.time()
                if guest_state['rate_limit_count'] >= 5 and (now_t - guest_state['last_search_time'] < 30):
                    ui.notify('⏳ Por favor, aguarde alguns segundos antes de tentar novamente.', color='warning')
                    return

                guest_state['rate_limit_count'] += 1
                guest_state['last_search_time'] = now_t

                file_content = e.content.read()
                if len(file_content) > 12 * 1024 * 1024:
                    ui.notify('❌ A foto enviada é muito grande (máximo 12MB).', color='negative')
                    return

                # Spinner de busca amigável
                with ui.dialog() as loading_dialog, ui.card().classes('bg-slate-900 border border-cyan-500/40 p-6 items-center text-center gap-4 rounded-2xl'):
                    ui.spinner(size='3rem', color='cyan')
                    ui.label('Analisando sua selfie...').classes('text-lg font-bold text-white')
                    ui.label('Buscando suas fotos no evento em tempo real.').classes('text-xs text-grey-4')
                loading_dialog.open()

                # Processa embedding da selfie em thread
                ok, msg, embedding = await asyncio.to_thread(_extract_selfie_embedding, file_content)

                if not ok or embedding is None:
                    loading_dialog.close()
                    ui.notify(msg, color='negative', timeout=5000)
                    return

                # Adiciona o vetor à lista de selfies do convidado (até 3)
                guest_state['selfie_embeddings'].append(embedding.tolist())
                if len(guest_state['selfie_embeddings']) > 3:
                    guest_state['selfie_embeddings'] = guest_state['selfie_embeddings'][-3:]

                # Registra perfil anônimo temporário no banco
                save_guest_face_profile(event_id, session_id, guest_state['selfie_embeddings'])
                log_portal_analytics(event_id, 'selfie', session_id=session_id)

                # Executa match contra a matriz do evento
                matrix, records = await asyncio.to_thread(_get_event_matrix, event_id)
                
                matched_items = []
                if matrix.shape[0] > 0:
                    # Multi-vetor max strategy
                    all_scores = np.zeros(matrix.shape[0], dtype=np.float32)
                    for s_emb in guest_state['selfie_embeddings']:
                        s_vec = np.array(s_emb, dtype=np.float32)
                        scores = matrix @ s_vec
                        all_scores = np.maximum(all_scores, scores)

                    # Filtra por threshold e remove duplicatas de foto
                    seen_fids = set()
                    for idx in np.argsort(-all_scores):
                        score = float(all_scores[idx])
                        if score < threshold_match:
                            break
                        rec = records[idx]
                        fid = rec['drive_file_id']
                        if fid not in seen_fids:
                            seen_fids.add(fid)
                            matched_items.append({
                                'drive_file_id': fid,
                                'drive_link': rec.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view",
                                'filename': rec.get('photo_filename', 'foto.jpg'),
                                'similarity': score
                            })

                guest_state['matched_photos'] = matched_items
                guest_state['has_searched'] = True

                if matched_items:
                    log_portal_analytics(event_id, 'match', session_id=session_id, metadata={'count': len(matched_items)})

                loading_dialog.close()
                refresh_ui()

            # ── RENDERIZAÇÃO DO CONTEÚDO ──────────────────────────────────────
            def render_portal_content():
                num_selfies = len(guest_state['selfie_embeddings'])

                # 1. SEÇÃO DE REGISTRO FACIAL / SELFIE
                with ui.card().classes('w-full bg-slate-950/80 border border-slate-800 rounded-2xl p-4 sm:p-6 items-center text-center gap-3'):
                    
                    if num_selfies == 0:
                        ui.icon('face_retouching_natural', size='3rem', color='cyan-4')
                        ui.label('📸 ENCONTRE SUAS FOTOS DO EVENTO').classes('text-lg sm:text-xl font-black text-white tracking-wide')
                        ui.label('Tire uma selfie rápida para localizar as fotos onde você aparece.').classes('text-xs sm:text-sm text-grey-4 max-w-md')
                    else:
                        ui.icon('check_circle', size='2.5rem', color='green-4')
                        ui.label(f"✅ {num_selfies} de 3 selfies registradas").classes('text-md font-bold text-green-4')
                        ui.label('Sua biometria foi identificada. Você pode adicionar mais um ângulo para refinar ou ver os resultados abaixo.').classes('text-xs text-grey-4 max-w-md')

                    # Dicas visuais amigáveis (Acessibilidade para todas as idades)
                    with ui.row().classes('w-full justify-center gap-2 sm:gap-4 py-2 text-[11px] sm:text-xs text-grey-3'):
                        with ui.row().classes('items-center gap-1'):
                            ui.label('☀️').classes('text-base')
                            ui.label('Boa luz')
                        with ui.row().classes('items-center gap-1'):
                            ui.label('👤').classes('text-base')
                            ui.label('Olhe de frente')
                        with ui.row().classes('items-center gap-1'):
                            ui.label('🕶️').classes('text-base')
                            ui.label('Sem óculos escuros')

                    # Botão gigante de Selfie (Área de toque WCAG >= 56px)
                    btn_label = '📸 TIRAR UMA SELFIE' if num_selfies == 0 else '📸 TIRAR OUTRA SELFIE (OPCIONAL)'
                    with ui.upload(on_upload=handle_selfie_upload, max_file_size=12*1024*1024, auto_upload=True).props('accept="image/*" capture="user" flat bordered').classes('w-full max-w-md'):
                        ui.button(btn_label).props('unelevated color=cyan-8 text-color=white icon=photo_camera').classes('w-full h-14 text-base font-black tracking-wide rounded-xl shadow-lg cyber-glow')

                    ui.label('🔒 Sua selfie é processada em memória e descartada imediatamente.').classes('text-[10px] text-grey-5')

                # 2. SEÇÃO DE FOTOS PESSOAIS ("MAIS FOTOS DO EVENTO") — SILENCIOSA E ELEGANTE
                if guest_state['has_searched'] and guest_state['matched_photos']:
                    with ui.column().classes('w-full gap-3 q-mt-4'):
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('auto_awesome', size='1.4rem', color='amber-4')
                                ui.label('📷 SUAS FOTOS NO EVENTO').classes('text-base sm:text-lg font-black text-amber-4 tracking-wide')
                            ui.badge(f"{len(guest_state['matched_photos'])} fotos", color='amber-9').classes('text-xs font-bold')

                        # Grade de fotos identificadas
                        render_photo_grid(guest_state['matched_photos'], is_personal=True)

                # 3. SEÇÃO DE FOTOS OFICIAIS DO EVENTO (PASTA GERAL)
                with ui.column().classes('w-full gap-3 q-mt-4'):
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('collections', size='1.4rem', color='cyan-4')
                            ui.label('📷 GALERIA OFICIAL DO EVENTO').classes('text-base sm:text-lg font-black text-cyan-3 tracking-wide')
                        ui.label('Fotos institucionais').classes('text-xs text-grey-4')

                    # Carrega fotos oficiais da pasta GERAL
                    render_official_gallery(drive_geral_id)

                # 4. SEÇÃO DE ENTREGA (DOWNLOAD / E-MAIL / WHATSAPP)
                render_delivery_section()

            # ── RENDERIZAÇÃO DA GRADE DE FOTOS ────────────────────────────────
            def render_photo_grid(photos_list: list[dict], is_personal: bool = False):
                with ui.grid().classes('w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3'):
                    for p in photos_list:
                        fid = p.get('drive_file_id') or p.get('id')
                        thumb_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w500-h500-c"
                        full_url = p.get('drive_link') or f"https://drive.google.com/file/d/{fid}/view"

                        with ui.card().classes('p-0 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-cyan-500/50 transition-all cursor-pointer group relative'):
                            ui.image(thumb_url).classes('w-full aspect-square object-cover').on('click', lambda u=full_url: open_lightbox(u))
                            
                            # Badge discreto de confiança se pessoal
                            if is_personal and p.get('similarity'):
                                sim_pct = int(p['similarity'] * 100)
                                with ui.element('div').classes('absolute top-1.5 right-1.5 bg-black/75 px-1.5 py-0.5 rounded text-[9px] font-bold text-amber-3 border border-amber-500/30'):
                                    ui.label(f"{sim_pct}%")

                            # Botão de visualização/download direto
                            with ui.row().classes('w-full p-1.5 items-center justify-between bg-black/60 backdrop-blur-sm'):
                                ui.button(icon='open_in_new', on_click=lambda u=full_url: ui.navigate.to(u, new_tab=True)).props('flat dense size=xs color=grey-4')
                                ui.button(icon='download', on_click=lambda fid=fid: download_single(fid)).props('flat dense size=xs color=cyan-4')

            # ── GALERIA OFICIAL (PASTA GERAL) ─────────────────────────────────
            def render_official_gallery(folder_id: str):
                if not folder_id:
                    ui.label('Nenhuma foto oficial disponibilizada ainda.').classes('text-xs text-grey-5 italic')
                    return

                try:
                    files = drive_service.list_files(folder_id, page_size=24)
                    if not files:
                        ui.label('As fotos do evento estão sendo processadas pela equipe de Comunicação Social.').classes('text-xs text-grey-4 italic')
                        return

                    photo_items = [{'drive_file_id': f['id'], 'drive_link': f.get('webViewLink'), 'filename': f['name']} for f in files]
                    guest_state['geral_photos'] = photo_items
                    render_photo_grid(photo_items, is_personal=False)
                except Exception as e:
                    ui.label(f"Não foi possível carregar a galeria: {e}").classes('text-xs text-red-4')

            # ── SEÇÃO DE ENTREGA (DOWNLOAD, EMAIL, WHATSAPP) ───────────────────
            def render_delivery_section():
                all_photos = []
                # Junta fotos pessoais + gerais
                seen = set()
                for p in (guest_state['matched_photos'] + guest_state['geral_photos']):
                    fid = p.get('drive_file_id') or p.get('id')
                    if fid and fid not in seen:
                        seen.add(fid)
                        all_photos.append(p)

                with ui.card().classes('w-full bg-slate-950 border-t-2 border-amber-500/30 rounded-2xl p-4 sm:p-6 gap-4 q-mt-4'):
                    ui.label('📥 RECEBER OU COMPARTILHAR SUAS FOTOS').classes('text-base font-black text-white tracking-wide')
                    
                    # Botão de Compartilhar no WhatsApp
                    event_url = f"https://sisgab-cgcfn.ddns.net/evento/{event_id}"
                    whatsapp_text = f"📷 Acesse as fotos oficiais do evento {nome_evento}: {event_url}"
                    whatsapp_url = f"https://api.whatsapp.com/send?text={whatsapp_text.replace(' ', '%20')}"

                    with ui.row().classes('w-full items-center gap-3'):
                        ui.button('📱 Compartilhar no WhatsApp', on_click=lambda: (log_portal_analytics(event_id, 'whatsapp', session_id=session_id), ui.navigate.to(whatsapp_url, new_tab=True))).props('unelevated color=green-8 text-color=white icon=share').classes('flex-1 h-12 text-xs sm:text-sm font-bold rounded-xl')

                    # Envio por E-mail Institucional (Template HTML via SMTP)
                    with ui.column().classes('w-full gap-2 q-mt-2'):
                        ui.label('Ou receba os links diretos por e-mail:').classes('text-xs text-grey-4')
                        
                        with ui.row().classes('w-full items-center gap-2'):
                            email_input = ui.input(placeholder='seu.email@exemplo.com').props('dark outlined dense').classes('flex-1')
                            
                            async def send_email_action():
                                email_val = (email_input.value or '').strip()
                                if not email_val or '@' not in email_val:
                                    ui.notify('❌ Digite um e-mail válido.', color='warning')
                                    return
                                
                                if not all_photos:
                                    ui.notify('ℹ️ Nenhuma foto para enviar no momento.', color='info')
                                    return

                                # Salva perfil para entrega futura proativa
                                save_guest_face_profile(event_id, session_id, guest_state['selfie_embeddings'], email=email_val)
                                
                                links_html = ''.join(
                                    f'<p style="margin: 6px 0;">📷 <a href="https://drive.google.com/file/d/{p.get("drive_file_id")}/view" style="color: #0284c7; text-decoration: none; font-weight: bold;">Foto {i+1} — Abrir no Drive</a></p>'
                                    for i, p in enumerate(all_photos[:30])
                                )

                                default_template = f"""
                                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f172a; color: #f8fafc; padding: 24px; border-radius: 16px; border: 1px solid #334155;">
                                    <div style="text-align: center; margin-bottom: 20px;">
                                        <h2 style="color: #f59e0b; margin: 0; font-size: 20px; text-transform: uppercase;">MARINHA DO BRASIL</h2>
                                        <p style="color: #38bdf8; margin: 4px 0 0 0; font-size: 11px; font-weight: bold; letter-spacing: 2px;">GABINETE DO COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS</p>
                                    </div>
                                    <hr style="border: 0; height: 1px; background: #334155; margin: 16px 0;" />
                                    <p style="font-size: 15px;">Prezado(a) Convidado(a),</p>
                                    <p style="font-size: 14px; color: #cbd5e1;">Suas fotos do evento <strong>{nome_evento}</strong> já estão prontas para visualização e download:</p>
                                    <div style="background: #1e293b; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                        {links_html}
                                    </div>
                                    <p style="text-align: center; margin-top: 20px;">
                                        <a href="{event_url}" style="background: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Ver Galeria Completa</a>
                                    </p>
                                    <hr style="border: 0; height: 1px; background: #334155; margin: 20px 0;" />
                                    <p style="font-size: 11px; color: #64748b; text-align: center;">Comunicação Social — CGCFN • Este é um e-mail automático institucional.</p>
                                </div>
                                """

                                template_to_use = event.get('email_template') or default_template
                                template_to_use = template_to_use.replace('{EVENTO_NOME}', nome_evento)
                                template_to_use = template_to_use.replace('{EVENTO_DATA}', data_formatada)
                                template_to_use = template_to_use.replace('{EVENTO_LOCAL}', local_evento)
                                template_to_use = template_to_use.replace('{FOTOS_LINKS}', links_html)
                                template_to_use = template_to_use.replace('{TOTAL_FOTOS}', str(len(all_photos)))

                                try:
                                    await asyncio.to_thread(
                                        send_real_email_smtp,
                                        email_val,
                                        f"📷 Suas fotos do evento {nome_evento}",
                                        template_to_use
                                    )
                                    save_guest_delivery(event_id, email_val, ','.join(p.get('drive_file_id') for p in all_photos), len(all_photos))
                                    log_portal_analytics(event_id, 'email', session_id=session_id)
                                    ui.notify('✅ E-mail institucional enviado com sucesso!', color='positive')
                                    email_input.value = ''
                                except Exception as err_mail:
                                    ui.notify(f"❌ Erro ao enviar e-mail: {err_mail}", color='negative')

                            ui.button('📧 Enviar', on_click=send_email_action).props('unelevated color=cyan text-color=black font-bold icon=send').classes('h-10 px-4 rounded-lg')

            # ── LIGHTBOX PARA PREVIEW HD ──────────────────────────────────────
            def open_lightbox(photo_url: str):
                with ui.dialog() as dlg, ui.card().classes('bg-black/90 p-2 items-center rounded-2xl max-w-4xl max-h-[90vh] overflow-hidden'):
                    ui.image(photo_url).classes('max-w-full max-h-[80vh] object-contain rounded-xl')
                    with ui.row().classes('w-full justify-between items-center p-2'):
                        ui.button('Fechar', on_click=dlg.close).props('flat color=grey')
                        ui.button('Abrir no Drive', on_click=lambda: ui.navigate.to(photo_url, new_tab=True)).props('unelevated color=cyan text-color=black size=sm')
                dlg.open()

            def download_single(file_id: str):
                log_portal_analytics(event_id, 'download', session_id=session_id)
                ui.navigate.to(f"https://drive.google.com/uc?export=download&id={file_id}", new_tab=True)

            # Inicializa a primeira renderização
            refresh_ui()
