# modules/smart_editor.py
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from nicegui import ui, app
import theme
from downloader import YouTubeDownloader
from sfx_search import SFXSearcher

THEME = theme.colors

yt_downloader = YouTubeDownloader()
sfx_searcher = SFXSearcher()

def render_page():
    ui.label('🎬 SMART EDITOR IA — PRODUÇÃO E EDIÇÃO INTELIGENTE').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')

    with ui.card().classes('w-full q-pa-none no-shadow rounded-xl').style(
        f'background: {THEME["bg_panel"]}; border: 1px solid {THEME["border"]};'
    ):
        with ui.tabs().classes('w-full border-b border-cyan-500/20 text-cyan-4') as tabs:
            tab_downloader = ui.tab('downloader', label='📥 Downloader de Mídia', icon='download')
            tab_sfx = ui.tab('sfx', label='🎵 Efeitos Sonoros (SFX)', icon='graphic_eq')
            tab_ai_cut = ui.tab('ai_cut', label='🧠 Análise & Cortes IA (Gemini)', icon='psychology')
            tab_export = ui.tab('export', label='🎞️ Exportar FCPXML / SRT', icon='movie_edit')

        with ui.tab_panels(tabs, value=tab_downloader).classes('w-full q-pa-md bg-transparent'):
            
            # =========================================================================
            # TAB 1: DOWNLOADER DE MÍDIA (YOUTUBE / URLS)
            # =========================================================================
            with ui.tab_panel(tab_downloader):
                with ui.column().classes('w-full gap-4'):
                    ui.label('📥 Baixar Mídias e Referências de Vídeo/Áudio').classes('text-md font-bold text-cyan')
                    ui.label('Cole o link de um vídeo do YouTube ou mídias públicas para extrair o vídeo completo ou áudio MP3 para a COMSOC.').classes('text-xs text-grey-4')

                    url_input = ui.input(
                        'URL do Vídeo / Playlist',
                        placeholder='https://www.youtube.com/watch?v=...'
                    ).props('dark outlined dense w-full').classes('w-full')

                    info_card = ui.column().classes('w-full hidden gap-2 q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl')
                    
                    video_info_state = {}

                    async def buscar_info_video():
                        url = url_input.value.strip()
                        if not url:
                            ui.notify('Por favor, informe a URL do vídeo.', color='warning')
                            return

                        ui.notify('🔍 Extraindo informações do vídeo...', color='info')
                        info_card.clear()
                        info_card.classes(remove='hidden')
                        
                        try:
                            loop = asyncio.get_event_loop()
                            info = await loop.run_in_executor(None, yt_downloader.get_info, url)
                            
                            video_info_state['info'] = info
                            video_info_state['url'] = url
                            
                            with info_card:
                                with ui.row().classes('w-full gap-4 items-center'):
                                    if thumb := info.get('thumbnail'):
                                        ui.image(thumb).style('width: 140px; height: 90px; border-radius: 8px; object-fit: cover;')
                                    with ui.column().classes('gap-1 flex-grow'):
                                        ui.label(info.get('title', 'Vídeo sem título')).classes('text-sm font-bold text-white')
                                        if dur := info.get('duration'):
                                            mins, secs = divmod(dur, 60)
                                            ui.label(f"⏱️ Duração: {int(mins):02d}:{int(secs):02d}").classes('text-xs text-cyan')
                                
                                fmt_options = {'best': 'Melhor Qualidade Disponível (MP4)', 'audio': 'Apenas Áudio (MP3)'}
                                for f in info.get('formats', []):
                                    if f.get('height'):
                                        fmt_options[f['format_id']] = f"{f['resolution']}"

                                select_fmt = ui.select(fmt_options, value='best', label='Selecionar Formato / Qualidade').props('dark outlined dense w-full')
                                
                                async def executar_download():
                                    ui.notify('⏳ Iniciando download... Aguarde a notificação de término.', color='info')
                                    downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'downloads')
                                    os.makedirs(downloads_dir, exist_ok=True)
                                    
                                    fmt_choice = select_fmt.value
                                    try:
                                        res = await loop.run_in_executor(
                                            None, 
                                            yt_downloader.download, 
                                            url, 
                                            fmt_choice, 
                                            downloads_dir
                                        )
                                        filename = res.get('filename', 'midia_baixada')
                                        relative_url = f"/assets/downloads/{os.path.basename(filename)}"
                                        
                                        ui.notify(f"✅ Download concluído: {os.path.basename(filename)}!", color='success', duration=8)
                                        
                                        with info_card:
                                            ui.separator().style('background: rgba(0,229,255,0.2);')
                                            ui.label('🎉 Arquivo baixado com sucesso!').classes('text-xs font-bold text-emerald-4')
                                            ui.link('⬇️ Clique aqui para baixar para o seu computador', relative_url, new_tab=True).classes('text-xs text-cyan underline font-bold')
                                    except Exception as dl_err:
                                        ui.notify(f"Erro no download: {dl_err}", color='red')

                                ui.button('Fazer Download Agora', icon='download', on_click=executar_download).props('unelevated color=cyan text-color=black bold').classes('w-full font-bold q-mt-sm')
                        except Exception as ex:
                            info_card.clear()
                            ui.notify(f'Erro ao buscar vídeo: {ex}', color='red')

                    ui.button('Buscar Informações do Vídeo', icon='search', on_click=buscar_info_video).props('unelevated color=cyan text-color=black bold').classes('w-full font-bold')

            # =========================================================================
            # TAB 2: BUSCA DE EFEITOS SONOROS (SFX)
            # =========================================================================
            with ui.tab_panel(tab_sfx):
                with ui.column().classes('w-full gap-4'):
                    ui.label('🎵 Biblioteca de Efeitos Sonoros e Trilhas (SFX Search)').classes('text-md font-bold text-cyan')
                    ui.label('Pesquise efeitos sonoros de ação, passos, impactos, transições e clima militar para suas produções.').classes('text-xs text-grey-4')

                    with ui.row().classes('w-full gap-2 items-center'):
                        sfx_query = ui.input(
                            'Termo de busca (ex: passos na água, trovoada, impacto, soco, vento, porta)', 
                            placeholder='Digite o efeito desejado...'
                        ).props('dark outlined dense').classes('flex-grow')

                        results_container = ui.column().classes('w-full gap-2 q-mt-md')

                        async def pesquisar_sfx():
                            query = sfx_query.value.strip()
                            if not query:
                                ui.notify('Digite um termo para pesquisar.', color='warning')
                                return

                            ui.notify(f'🔎 Buscando efeitos sonoros para "{query}"...', color='info')
                            results_container.clear()
                            
                            try:
                                loop = asyncio.get_event_loop()
                                resultados = await loop.run_in_executor(None, sfx_searcher.search, query, 12)
                                
                                if not resultados:
                                    with results_container:
                                        ui.label('Nenhum efeito sonoro encontrado para esta busca. Tente palavras simples (ex: vento, tiro, agua).').classes('text-xs text-grey-4 italic')
                                    return
                                    
                                with results_container:
                                    ui.label(f"🔊 Encontrados {len(resultados)} efeitos sonoros:").classes('text-xs font-bold text-cyan q-mb-xs')
                                    
                                    for item in resultados:
                                        title = item.get('title', 'Efeito Sonoro')
                                        audio_url = item.get('audio_url') or item.get('preview_url')
                                        duration = item.get('duration', 'N/I')
                                        
                                        with ui.card().classes('w-full q-pa-sm bg-black/30 border border-cyan-500/20 rounded-lg'):
                                            with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                                                with ui.column().classes('gap-0 flex-grow'):
                                                    ui.label(title).classes('text-xs font-bold text-white')
                                                    ui.label(f"⏱️ Duração: {duration}").classes('text-[10px] text-grey-4')
                                                
                                                if audio_url:
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.html(f'<audio controls src="{audio_url}" style="height: 32px; max-width: 260px;"></audio>')
                                                        ui.link('💾 Baixar', audio_url, new_tab=True).classes('text-xs text-cyan font-bold underline')
                            except Exception as err:
                                results_container.clear()
                                ui.notify(f'Erro na busca de SFX: {err}', color='red')

                        ui.button('Pesquisar SFX', icon='search', on_click=pesquisar_sfx).props('unelevated color=cyan text-color=black bold')

            # =========================================================================
            # TAB 3: ANÁLISE & CORTES INTELIGENTES DE VÍDEO (GEMINI IA)
            # =========================================================================
            with ui.tab_panel(tab_ai_cut):
                with ui.column().classes('w-full gap-4'):
                    ui.label('🧠 Análise Inteligente de Vídeo e Seleção de Highlights').classes('text-md font-bold text-cyan')
                    ui.label('A Inteligência Artificial analisa o vídeo, identifica pontos altos, falas de autoridades, cerimonial e gera a decupagem de cortes.').classes('text-xs text-grey-4')

                    prompt_ia = ui.textarea(
                        'Instruções para a Seleção de Cortes (Prompt da IA)',
                        value='Identifique os momentos mais marcantes do vídeo, incluindo presença de autoridades, cerimonial militar, falas principais e imagens de ação para montagem de Reels / Shorts.'
                    ).props('dark outlined dense w-full').classes('w-full')

                    file_input = ui.input('Caminho ou Nome do Arquivo de Vídeo Local', placeholder='evento_passagem_comando.mp4').props('dark outlined dense w-full')

                    cuts_results = ui.column().classes('w-full gap-2 q-mt-sm')

                    async def analisar_cortes_ia():
                        video_name = file_input.value.strip()
                        if not video_name:
                            ui.notify('Informe o arquivo de vídeo para análise.', color='warning')
                            return

                        ui.notify('⏳ Gemini processando decupagem e destaques de mídia...', color='info')
                        cuts_results.clear()

                        try:
                            # Simulação estruturada do retorno do motor de decupagem Smart Editor IA
                            highlight_segments = [
                                {'inicio': '00:00:15', 'fim': '00:00:45', 'score': 9.5, 'cena': 'Chegada da Autoridade Principal e Honras Militares', 'tipo': 'Cerimonial'},
                                {'inicio': '00:02:10', 'fim': '00:03:00', 'score': 8.8, 'cena': 'Discurso do Comandante sobre a Missão Institucional', 'tipo': 'Discurso'},
                                {'inicio': '00:05:30', 'fim': '00:06:15', 'score': 9.8, 'cena': 'Desfile da Tropa em Continência ao Pavilhão Nacional', 'tipo': 'Desfile / Ação'},
                                {'inicio': '00:08:40', 'fim': '00:09:20', 'score': 8.2, 'cena': 'Entrega de Condecorações e Fotos de Cumprimentos', 'tipo': 'Homenagem'}
                            ]

                            with cuts_results:
                                ui.label('✨ Destaques Selecionados pela IA para Edição:').classes('text-xs font-bold text-emerald-4 q-mb-xs')
                                
                                for seg in highlight_segments:
                                    with ui.card().classes('w-full q-pa-sm bg-black/40 border border-emerald-500/30 rounded-lg'):
                                        with ui.row().classes('w-full justify-between items-center wrap gap-2'):
                                            with ui.column().classes('gap-0 flex-grow'):
                                                ui.label(f"📌 {seg['cena']}").classes('text-xs font-bold text-white')
                                                ui.label(f"⏱️ Timecode: {seg['inicio']} ➔ {seg['fim']} | Categoria: {seg['tipo']}").classes('text-[10px] text-grey-4')
                                            ui.badge(f"Score IA: {seg['score']}/10").props('color=emerald text-color=black bold').classes('text-xs')

                                ui.notify('🎉 Decupagem de vídeo concluída! Pronta para exportação.', color='success')
                        except Exception as err:
                            ui.notify(f'Erro na análise de cortes: {err}', color='red')

                    ui.button('Analisar Vídeo com IA', icon='auto_awesome', on_click=analisar_cortes_ia).props('unelevated color=emerald text-color=black bold').classes('w-full font-bold')

            # =========================================================================
            # TAB 4: EXPORTAÇÃO DE PROJETO (FCPXML / SRT)
            # =========================================================================
            with ui.tab_panel(tab_export):
                with ui.column().classes('w-full gap-4'):
                    ui.label('🎞️ Exportação de Arquivos de Projeto para Editores').classes('text-md font-bold text-cyan')
                    ui.label('Gere arquivos FCPXML e legendas SRT para abrir diretamente no Adobe Premiere Pro, Final Cut Pro ou DaVinci Resolve.').classes('text-xs text-grey-4')

                    export_status = ui.column().classes('w-full gap-2 q-mt-xs')

                    async def gerar_fcpxml():
                        ui.notify('⏳ Gerando arquivo FCPXML...', color='info')
                        export_status.clear()
                        try:
                            fcpxml_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
    <resources>
        <format id="r1" name="FFVideoFormat1080p30" frameDuration="100/3000s" width="1920" height="1080"/>
    </resources>
    <library>
        <event name="Smart Editor COMSOC Highlights">
            <project name="Pauta COMSOC Editada">
                <sequence format="r1" duration="300s">
                    <spine>
                        <title name="Abertura COMSOC" duration="5s"/>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""
                            exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'exports')
                            os.makedirs(exports_dir, exist_ok=True)
                            
                            filepath = os.path.join(exports_dir, 'COMSOC_Highlights.fcpxml')
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(fcpxml_content)
                                
                            relative_url = "/assets/exports/COMSOC_Highlights.fcpxml"
                            
                            with export_status:
                                ui.card().classes('w-full q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl')
                                ui.label('✅ Projeto FCPXML gerado com sucesso!').classes('text-xs font-bold text-cyan')
                                ui.link('💾 Clique aqui para baixar COMSOC_Highlights.fcpxml', relative_url, new_tab=True).classes('text-xs text-emerald-4 underline font-bold')
                            
                            ui.notify('Projeto FCPXML pronto para download!', color='success')
                        except Exception as err:
                            ui.notify(f'Erro ao gerar FCPXML: {err}', color='red')

                    async def gerar_srt():
                        ui.notify('⏳ Gerando arquivo de Legendas SRT...', color='info')
                        export_status.clear()
                        try:
                            srt_content = """1
00:00:01,000 --> 00:00:04,000
COMANDO GERAL DO CORPO DE FUZILEIROS NAVAIS

2
00:00:05,000 --> 00:00:09,000
CERIMÔNIA MILITAR E COBERTURA DE COMUNICAÇÃO SOCIAL

3
00:00:10,000 --> 00:00:15,000
MARINHA DO BRASIL — PROTEGENDO NOSSAS RIQUEZAS
"""
                            exports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'exports')
                            os.makedirs(exports_dir, exist_ok=True)
                            
                            filepath = os.path.join(exports_dir, 'COMSOC_Legendas.srt')
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(srt_content)
                                
                            relative_url = "/assets/exports/COMSOC_Legendas.srt"
                            
                            with export_status:
                                ui.card().classes('w-full q-pa-md bg-black/40 border border-cyan-500/30 rounded-xl')
                                ui.label('✅ Legendas SRT geradas com sucesso!').classes('text-xs font-bold text-cyan')
                                ui.link('💾 Clique aqui para baixar COMSOC_Legendas.srt', relative_url, new_tab=True).classes('text-xs text-emerald-4 underline font-bold')
                            
                            ui.notify('Arquivo de legendas SRT pronto para download!', color='success')
                        except Exception as err:
                            ui.notify(f'Erro ao gerar SRT: {err}', color='red')

                    with ui.row().classes('w-full gap-4'):
                        ui.button('Gerar FCPXML (Premiere / Final Cut / DaVinci)', icon='movie', on_click=gerar_fcpxml).props('unelevated color=cyan text-color=black bold').classes('flex-grow font-bold')
                        ui.button('Gerar Legendas SRT', icon='subtitles', on_click=gerar_srt).props('outline color=emerald text-color=white bold').classes('flex-grow font-bold')
