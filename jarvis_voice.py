import os
import json
import asyncio
from datetime import datetime, timedelta
from nicegui import ui, app
from fastapi import Request
from database import get_db_connection

THEME = {
    'bg_main': '#030a17',
    'bg_panel': '#091326',
    'bg_card': '#0d1b34',
    'border': 'rgba(0, 229, 255, 0.3)',
    'accent': '#00e5ff',
    'accent_green': '#00ff88',
    'accent_gold': '#ffb700',
    'accent_red': '#ff3b30'
}

# --- ENDPOINT BACKEND DO JARVIS ---
@app.post('/api/jarvis_process')
async def jarvis_process_api(request: Request):
    """Processa a mensagem falada do usuário, consulta o banco de dados do SisGAB e responde via Gemini."""
    try:
        body = await request.json()
        user_prompt = body.get('prompt', '').strip()
        if not user_prompt:
            return {"text": "Não consegui ouvir. Pode repetir?"}
            
        # 1. Coletar contexto em tempo real do SisGAB
        hoje_str = (datetime.utcnow() - timedelta(hours=3)).strftime('%Y-%m-%d')
        amanha_str = (datetime.utcnow() - timedelta(hours=3) + timedelta(days=1)).strftime('%Y-%m-%d')
        
        contexto_sisgab = []
        db = get_db_connection()
        if db:
            # Presenças de hoje
            try:
                r_pr = db.table('presenca_diaria').select('nome_guerra, status').eq('data', hoje_str).execute()
                if r_pr and r_pr.data:
                    confirmados = [p['nome_guerra'] for p in r_pr.data if str(p.get('status')).upper() not in ('PENDENTE', 'NONE')]
                    pendentes = [p['nome_guerra'] for p in r_pr.data if str(p.get('status')).upper() in ('PENDENTE', 'NONE')]
                    contexto_sisgab.append(f"Chamada de Presença Hoje ({hoje_str}): {len(confirmados)} confirmados, {len(pendentes)} pendentes.")
                    if pendentes:
                        contexto_sisgab.append(f"Pendentes de presença: {', '.join(pendentes[:8])}")
            except Exception as e_pr:
                print(f"[JARVIS CTX PR ERR] {e_pr}")

            # Demandas de Hoje e Amanhã
            try:
                r_dem = db.table('demandas_comunicacao').select('titulo_evento, data_evento, hora_evento, local_evento, solicitante_nome').in_('data_evento', [hoje_str, amanha_str, 'ASD']).execute()
                if r_dem and r_dem.data:
                    contexto_sisgab.append("Demandas Recentes:")
                    for d in r_dem.data[:6]:
                        dt = 'Hoje' if d.get('data_evento') == hoje_str else ('Amanhã' if d.get('data_evento') == amanha_str else 'Data ASD')
                        contexto_sisgab.append(f"- {d.get('titulo_evento')} ({dt} às {d.get('hora_evento', '09:00')}, local: {d.get('local_evento', 'Gabinete')})")
            except Exception as e_dem:
                print(f"[JARVIS CTX DEM ERR] {e_dem}")

        contexto_txt = "\n".join(contexto_sisgab) if contexto_sisgab else "Sem dados do sistema no momento."

        # 2. Enviar para a Inteligência Artificial Gemini
        system_instruction = (
            "Você é o JARVIS, o assistente virtual com inteligência artificial tática do SisGAB (Sistema de Gestão e Comunicação Social do Gabinete do Comandante-Geral do Corpo de Fuzileiros Navais).\n"
            "Responda sempre em português do Brasil de forma extremamente cortês, concisa, eficiente, militar e direta (estilo robótico inteligente igual o Jarvis do Homem de Ferro).\n"
            "Não use textos longos ou formatações complexas, pois sua resposta será falada em áudio pelo navegador em voz sintetizada.\n\n"
            f"DADOS ATUAIS DO SISGAB EM TEMPO REAL:\n{contexto_txt}\n"
        )
        
        full_prompt = f"{system_instruction}\n\nPERGUNTA DO OPERADOR: {user_prompt}\n\nRESPOSTA DO JARVIS:"
        
        try:
            import ai_helper
            resposta_ai = ai_helper.call_gemini_text(full_prompt)
            if not resposta_ai or "erro" in resposta_ai.lower():
                resposta_ai = f"Pois não. Sobre '{user_prompt}', os dados atuais mostram: {contexto_sisgab[0] if contexto_sisgab else 'Sistema operacional e pronto.'}"
        except Exception as e_ai:
            print(f"[JARVIS AI ERR] {e_ai}")
        # 3. Síntese de Voz Neural Ultra-Realista com Edge-TTS (Antonio Neural)
        audio_b64 = None
        try:
            import base64
            import edge_tts
            communicate = edge_tts.Communicate(resposta_ai, 'pt-BR-AntonioNeural', rate='+5%')
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk['type'] == 'audio':
                    audio_data.extend(chunk['data'])
            if audio_data:
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        except Exception as e_tts:
            print(f"[JARVIS EDGE TTS ERR] {e_tts}")

        return {"text": resposta_ai, "audio_b64": audio_b64}
    except Exception as e:
        print(f"[JARVIS PROCESS ERR] {e}")
        return {"text": "Desculpe, tive uma oscilação na conexão interna. Como posso ajudar?", "audio_b64": None}


# --- PÁGINA DEDICADA DO JARVIS NO NICEGUI ---
def render_page(current_user=None):
    """Renderiza o painel futurista estilo HUD Jarvis com voz em tempo real e palavra-chave."""
    ui.colors(primary=THEME['accent'], dark=THEME['bg_main'])

    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        
        .jarvis-orb-container {
            position: relative;
            width: 180px;
            height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px 0;
        }
        
        .jarvis-orb-core {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: radial-gradient(circle, #00e5ff 0%, #091326 70%);
            box-shadow: 0 0 40px #00e5ff, inset 0 0 20px #ffffff;
            transition: all 0.3s ease;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .jarvis-ring-1 {
            position: absolute;
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: 2px dashed rgba(0, 229, 255, 0.6);
            animation: rotateClockwise 12s linear infinite;
        }
        
        .jarvis-ring-2 {
            position: absolute;
            width: 175px;
            height: 175px;
            border-radius: 50%;
            border: 1px solid rgba(0, 255, 136, 0.4);
            border-top-color: transparent;
            animation: rotateCounterClockwise 8s linear infinite;
        }

        /* Estados Animações do Orbe */
        .jarvis-listening .jarvis-orb-core {
            box-shadow: 0 0 60px #00ff88, inset 0 0 30px #ffffff;
            transform: scale(1.15);
        }
        .jarvis-speaking .jarvis-orb-core {
            box-shadow: 0 0 80px #ffb700, inset 0 0 40px #ffffff;
            animation: pulseSpeaking 0.6s ease-in-out infinite alternate;
        }
        
        @keyframes rotateClockwise { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes rotateCounterClockwise { 0% { transform: rotate(0deg); } 100% { transform: rotate(-360deg); } }
        @keyframes pulseSpeaking { 0% { transform: scale(1); } 100% { transform: scale(1.25); } }
    </style>
    ''')

    with ui.column().classes('w-full p-4 md:p-6 gap-6').style(f'background: {THEME["bg_main"]}; min-height: 100vh; font-family: "Share Tech Mono", monospace, sans-serif;'):
        
        # Cabeçalho da Página
        with ui.row().classes('w-full items-center justify-between border-b border-cyan-500/30 pb-4'):
            with ui.column().classes('gap-1'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('graphic_eq', color='cyan').classes('text-3xl animate-pulse')
                    ui.label('JARVIS VOICE AI — TEMPO REAL').classes('text-2xl font-bold text-cyan cyber-title tracking-wider')
                ui.label('Assistente de Voz Tático com Reconhecimento Contínuo e Palavra-Chave "JARVIS"').classes('text-xs text-grey-4')
            
            with ui.row().classes('items-center gap-3'):
                ui.badge('ONLINE', color='emerald').classes('text-xs font-bold q-px-md')
                ui.label(datetime.now().strftime('%H:%M:%S BRT')).classes('text-xs text-cyan font-mono')

        # ─── INTERFACE HUD CENTRAL (ORB REACTOR) ───
        with ui.row().classes('w-full justify-center my-4'):
            with ui.card().classes('w-full max-w-[800px] p-6 rounded-2xl no-shadow items-center justify-center relative overflow-hidden').style(
                f'background: radial-gradient(circle at center, {THEME["bg_card"]} 0%, {THEME["bg_panel"]} 100%); border: 1px solid {THEME["border"]}; box-shadow: 0 0 30px rgba(0, 229, 255, 0.15);'
            ):
                # HTML Container do Orbe HUD do Jarvis
                ui.html('''
                <div id="jarvisHudContainer" class="jarvis-orb-container">
                    <div class="jarvis-ring-1"></div>
                    <div class="jarvis-ring-2"></div>
                    <div id="jarvisOrb" class="jarvis-orb-core" onclick="toggleJarvisVoice()">
                        <span id="jarvisStatusIcon" style="font-size: 36px; color: #ffffff;">🎙️</span>
                    </div>
                </div>
                ''')

                ui.label('TOQUE NO ORBE OU FALE "JARVIS"').classes('text-xs text-cyan font-bold tracking-widest q-mt-sm')
                
                # Indicador de Status do Jarvis
                with ui.row().classes('items-center gap-2 q-mt-xs'):
                    ui.element('div').classes('w-2 h-2 rounded-full bg-emerald-400 animate-ping')
                    ui.label('Escuta de Palavra-Chave Ativa: Diga "Jarvis" ou clique para falar').props('id=jarvisStatusLabel').classes('text-xs text-grey-3 font-mono')

                # Campo Transcrição em Tempo Real
                with ui.column().classes('w-full q-mt-md gap-2'):
                    with ui.card().classes('w-full p-3 rounded-lg no-shadow').style('background: rgba(4, 13, 26, 0.8); border: 1px solid rgba(0,229,255,0.2);'):
                        ui.label('🗣️ O QUE VOCÊ FALOU:').classes('text-[10px] text-grey-5 font-bold')
                        ui.label('Aguardando sua voz...').props('id=userTranscriptText').classes('text-sm text-cyan font-mono min-h-[24px]')
                    
                    with ui.card().classes('w-full p-3 rounded-lg no-shadow').style('background: rgba(4, 13, 26, 0.8); border: 1px solid rgba(0,255,136,0.2);'):
                        ui.label('🤖 RESPOSTA DO JARVIS:').classes('text-[10px] text-grey-5 font-bold')
                        ui.label('Sistemas prontos, Chefe. Como posso ajudar?').props('id=jarvisResponseText').classes('text-sm text-emerald-400 font-mono min-h-[30px]')

                # Botões de Ação Rápida por Voz
                ui.label('💡 SUGESTÕES DE COMANDOS DE VOZ:').classes('text-[11px] text-grey-4 font-bold q-mt-md')
                with ui.row().classes('w-full justify-center gap-2 wrap'):
                    for cmd in [
                        "Jarvis, quem falta dar presença hoje?",
                        "Jarvis, quais as pautas de hoje?",
                        "Jarvis, crie um evento de treinamento amanhã",
                        "Jarvis, resumo geral do gabinete"
                    ]:
                        ui.button(
                            cmd,
                            on_click=lambda _, c=cmd: ui.run_javascript(f'sendTextToJarvis("{c}")')
                        ).props('outline dense color=cyan text-color=white').classes('text-xs rounded-full')

        # ─── MOTOR JAVASCRIPT CLIENT-SIDE (WEBSPEECH STT + WAKE WORD + TTS) ───
        ui.add_body_html('''
        <script>
            let isListening = false;
            let isSpeaking = false;
            let recognition = null;
            let wakeWordRecognition = null;
            let synth = window.speechSynthesis;

            function initJarvisVoiceEngine() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition) {
                    document.getElementById('jarvisStatusLabel').innerText = "⚠️ Seu navegador não suporta a WebSpeech API. Use o Google Chrome ou Edge.";
                    return;
                }

                // 1. Configurar Reconhecimento Principal
                recognition = new SpeechRecognition();
                recognition.lang = 'pt-BR';
                recognition.continuous = false;
                recognition.interimResults = true;

                recognition.onstart = () => {
                    isListening = true;
                    setHudState('listening');
                    document.getElementById('jarvisStatusLabel').innerText = "🎙️ Ouvindo você... Pode falar!";
                };

                recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    document.getElementById('userTranscriptText').innerText = transcript;
                    if (event.results[0].isFinal) {
                        processUserInput(transcript);
                    }
                };

                recognition.onerror = (err) => {
                    console.log("Erro STT:", err);
                    setHudState('idle');
                    document.getElementById('jarvisStatusLabel').innerText = "Escuta encerrada. Diga 'Jarvis' ou clique para falar.";
                    startWakeWordListener();
                };

                recognition.onend = () => {
                    if (!isSpeaking) {
                        setHudState('idle');
                        startWakeWordListener();
                    }
                };

                // 2. Iniciar escuta contínua de palavra-chave (Wake Word "Jarvis")
                startWakeWordListener();
            }

            function startWakeWordListener() {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                if (!SpeechRecognition || isListening || isSpeaking) return;

                if (wakeWordRecognition) {
                    try { wakeWordRecognition.stop(); } catch(e){}
                }

                wakeWordRecognition = new SpeechRecognition();
                wakeWordRecognition.lang = 'pt-BR';
                wakeWordRecognition.continuous = true;
                wakeWordRecognition.interimResults = true;

                wakeWordRecognition.onresult = (event) => {
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        let text = event.results[i][0].transcript.toLowerCase();
                        if (text.includes('jarvis') || text.includes('assistente')) {
                            wakeWordRecognition.stop();
                            playBeepSound();
                            toggleJarvisVoice(true);
                            break;
                        }
                    }
                };

                wakeWordRecognition.onerror = () => {
                    setTimeout(startWakeWordListener, 2000);
                };

                try { wakeWordRecognition.start(); } catch(e){}
            }

            function toggleJarvisVoice(forceStart = false) {
                if (isSpeaking) {
                    synth.cancel();
                    isSpeaking = false;
                    setHudState('idle');
                    return;
                }

                if (isListening && !forceStart) {
                    if (recognition) recognition.stop();
                    setHudState('idle');
                } else {
                    if (wakeWordRecognition) try { wakeWordRecognition.stop(); } catch(e){}
                    if (recognition) try { recognition.start(); } catch(e){}
                }
            }

            let currentAudioPlayer = null;

            function sendTextToJarvis(text) {
                const userTxt = document.getElementById('userTranscriptText');
                if (userTxt) userTxt.innerText = text;
                processUserInput(text);
            }

            async function processUserInput(userText) {
                setHudState('processing');
                const lbl = document.getElementById('jarvisStatusLabel');
                if (lbl) lbl.innerText = "🧠 Jarvis está processando sua solicitação...";
                
                try {
                    const response = await fetch('/api/jarvis_process', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: userText })
                    });
                    const data = await response.json();
                    const replyText = data.text || "Comando recebido.";
                    const audioB64 = data.audio_b64;
                    
                    const jResp = document.getElementById('jarvisResponseText');
                    if (jResp) jResp.innerText = replyText;
                    speakJarvisResponse(replyText, audioB64);
                } catch (err) {
                    const jResp = document.getElementById('jarvisResponseText');
                    if (jResp) jResp.innerText = "Erro de conexão ao processar com a IA.";
                    setHudState('idle');
                    startWakeWordListener();
                }
            }

            function speakJarvisResponse(text, audioB64) {
                if (currentAudioPlayer) {
                    try { currentAudioPlayer.pause(); currentAudioPlayer = null; } catch(e){}
                }

                // 1. Reprodução de Voz Neural Edge TTS (Antonio Neural)
                if (audioB64) {
                    try {
                        const audio = new Audio("data:audio/mp3;base64," + audioB64);
                        currentAudioPlayer = audio;
                        
                        audio.onplay = () => {
                            isSpeaking = true;
                            setHudState('speaking');
                            const lbl = document.getElementById('jarvisStatusLabel');
                            if (lbl) lbl.innerText = "🔊 Jarvis falando (Voz Neural Antonio)...";
                        };
                        
                        audio.onended = () => {
                            isSpeaking = false;
                            setHudState('idle');
                            const lbl = document.getElementById('jarvisStatusLabel');
                            if (lbl) lbl.innerText = "Escuta de Palavra-Chave Ativa: Diga 'Jarvis' ou clique para falar.";
                            startWakeWordListener();
                        };
                        
                        audio.onerror = (e) => {
                            console.log("Erro ao tocar áudio neural, usando fallback:", e);
                            fallbackWebSpeech(text);
                        };

                        audio.play();
                        return;
                    } catch(e) {
                        console.log("Falha ao instanciar áudio neural:", e);
                    }
                }

                // 2. Fallback para WebSpeech API do navegador
                fallbackWebSpeech(text);
            }

            function fallbackWebSpeech(text) {
                if (!synth) return;
                synth.cancel();

                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = 'pt-BR';
                utterance.rate = 1.05;
                utterance.pitch = 0.95;

                // Tenta selecionar uma voz em Português masculina/natural
                let voices = synth.getVoices();
                let ptVoice = voices.find(v => v.lang.includes('pt') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Lucio') || v.name.includes('Daniel')));
                if (!ptVoice) ptVoice = voices.find(v => v.lang.includes('pt'));
                if (ptVoice) utterance.voice = ptVoice;

                utterance.onstart = () => {
                    isSpeaking = true;
                    setHudState('speaking');
                    const lbl = document.getElementById('jarvisStatusLabel');
                    if (lbl) lbl.innerText = "🔊 Jarvis está falando...";
                };

                utterance.onend = () => {
                    isSpeaking = false;
                    setHudState('idle');
                    const lbl = document.getElementById('jarvisStatusLabel');
                    if (lbl) lbl.innerText = "Escuta de Palavra-Chave Ativa: Diga 'Jarvis' ou clique para falar.";
                    startWakeWordListener();
                };

                utterance.onerror = () => {
                    isSpeaking = false;
                    setHudState('idle');
                    startWakeWordListener();
                };

                synth.speak(utterance);
            }

            function setHudState(state) {
                const orb = document.getElementById('jarvisHudContainer');
                const icon = document.getElementById('jarvisStatusIcon');
                if (!orb || !icon) return;

                orb.classList.remove('jarvis-listening', 'jarvis-speaking', 'jarvis-processing');

                if (state === 'listening') {
                    orb.classList.add('jarvis-listening');
                    icon.innerText = "🎙️";
                } else if (state === 'speaking') {
                    orb.classList.add('jarvis-speaking');
                    icon.innerText = "🔊";
                } else if (state === 'processing') {
                    icon.innerText = "⚙️";
                } else {
                    icon.innerText = "🎙️";
                }
            }

            function playBeepSound() {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(880, ctx.currentTime);
                    gain.gain.setValueAtTime(0.1, ctx.currentTime);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.15);
                } catch(e){}
            }

            // Iniciar o motor após carregar a página
            setTimeout(initJarvisVoiceEngine, 1000);
        </script>
        ''')
