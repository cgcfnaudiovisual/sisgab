from nicegui import ui, app, run
import theme
import os
from database import get_db_connection, SUPABASE_URL, get_bot_db_connection as get_admin_db_connection
from services import data_service
from datetime import date

# Cores do tema
THEME = theme.colors

# Configurações padrão
DEFAULT_CONFIGS = {
    'tempo_polling_tv': '300',
    'cabecalho_tv_title': 'MONITOR TÁTICO — COMUNICAÇÃO SOCIAL',
    'cabecalho_tv_subtitle': 'COMUNICAÇÃO SOCIAL • GABINETE',
    'cabecalho_tv_sunset_time': '17:48',
    'cargos_escala_lista': 'CHEFE COMSOC, SUPERVISOR, FOTÓGRAFO, CINEGRAFISTA, OPERADOR DE REDES SOCIAIS, REDATOR',
    'codigo_desbloqueio_tv': '1234',
    'tempo_alerta_tv': '10',
    'telegram_bot_token': '',
    'tts_engine': 'basic',
    'elevenlabs_api_key': '',
    'elevenlabs_voice_id': 'N2lVS1w4EtoT3dr4eOWO',
    'tts_piper_path': 'piper.exe',
    'tts_piper_voice': 'pt_BR-fabricio-medium',
    'google_tts_lang': 'pt-br',
    'basic_tts_voice': '',
    'google_api_key': '',
    'gemini_model_name': 'gemini-2.0-flash'
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
                        window.globalAudioContext.resume().then(function() {
                            console.log("[AUDIO] AudioContext resumed");
                        });
                    }
                    const buffer = window.globalAudioContext.createBuffer(1, 1, 22050);
                    const source = window.globalAudioContext.createBufferSource();
                    source.buffer = buffer;
                    source.connect(window.globalAudioContext.destination);
                    source.start(0);
                }
                
                // Desbloqueia Síntese de Voz (SpeechSynthesis)
                if ('speechSynthesis' in window) {
                    let u = new SpeechSynthesisUtterance('');
                    window.speechSynthesis.speak(u);
                }
            } catch (e) {
                console.error("[AUDIO] Erro ao retomar áudio:", e);
            }
        };
        // Ativa no primeiro clique na página
        document.addEventListener('click', window.resumeComcaAudio, { once: true });
    </script>
    """)

    def testar_som(som_key: str):
        """Executa a síntese de som diretamente no navegador do operador atual usando Web Audio API."""
        if som_key == 'silent':
            ui.notify('Silencioso ativado para este som.', color='warning')
            return
            
        from alerts_manager import load_alerts_config
        alerts_config = load_alerts_config()
        custom_seqs = alerts_config.get('custom_sequences', {})
        
        # Se som_key for uma sequência de som personalizada, resolvemos a lista
        if som_key in custom_seqs:
            sequence = custom_seqs[som_key]
        else:
            sequence = [{'som': som_key, 'delay': 0.0}]
            
        supabase_base_url = (SUPABASE_URL.rstrip('/') if SUPABASE_URL else "")
        
        js_code = f"""
        try {{
            let ctx = window.globalAudioContext;
            if (!ctx) {{
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {{
                    ctx = new AudioContext();
                    window.globalAudioContext = ctx;
                }}
            }}
            
            function playDefaultSynthesized(type) {{
                if (!ctx) return;
                if (type === 'submarine_sonar') {{
                    let now = ctx.currentTime;
                    let osc = ctx.createOscillator();
                    let gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(800, now);
                    osc.frequency.exponentialRampToValueAtTime(850, now + 0.15);
                    
                    gain.gain.setValueAtTime(0, now);
                    gain.gain.linearRampToValueAtTime(0.4, now + 0.005);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 1.8);
                    
                    osc.start(now);
                    osc.stop(now + 2.0);
                    
                    let echoOsc = ctx.createOscillator();
                    let echoGain = ctx.createGain();
                    echoOsc.connect(echoGain);
                    echoGain.connect(ctx.destination);
                    
                    echoOsc.type = 'sine';
                    echoOsc.frequency.setValueAtTime(810, now + 0.8);
                    echoOsc.frequency.exponentialRampToValueAtTime(830, now + 0.95);
                    
                    echoGain.gain.setValueAtTime(0, now + 0.8);
                    echoGain.gain.linearRampToValueAtTime(0.08, now + 0.805);
                    echoGain.gain.exponentialRampToValueAtTime(0.0001, now + 2.0);
                    
                    echoOsc.start(now + 0.8);
                    echoOsc.stop(now + 2.2);
                }} else if (type === 'morse_sos') {{
                    let now = ctx.currentTime;
                    const toneFreq = 800;
                    const dot = 0.08;
                    const dash = 0.24;
                    
                    let osc = ctx.createOscillator();
                    let gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(toneFreq, now);
                    gain.gain.setValueAtTime(0, now);
                    
                    function scheduleTone(start, duration) {{
                        gain.gain.setValueAtTime(0, now + start);
                        gain.gain.linearRampToValueAtTime(0.2, now + start + 0.005);
                        gain.gain.setValueAtTime(0.2, now + start + duration - 0.005);
                        gain.gain.linearRampToValueAtTime(0, now + start + duration);
                    }}
                    
                    scheduleTone(0.0, dot);
                    scheduleTone(0.16, dot);
                    scheduleTone(0.32, dot);
                    
                    scheduleTone(0.56, dash);
                    scheduleTone(0.88, dash);
                    scheduleTone(1.20, dash);
                    
                    scheduleTone(1.52, dot);
                    scheduleTone(1.68, dot);
                    scheduleTone(1.84, dot);
                    
                    osc.start(now);
                    osc.stop(now + 2.1);
                }} else if (type === 'naval_horn') {{
                    let now = ctx.currentTime;
                    const fundamental = 72;
                    const oscillators = [fundamental, fundamental * 1.5, fundamental * 2.0, fundamental * 2.5];
                    const gains = [0.4, 0.25, 0.15, 0.08];
                    const detunes = [0, 1.2, -0.8, 0.5];
                    
                    let mainGain = ctx.createGain();
                    let filter = ctx.createBiquadFilter();
                    
                    filter.type = 'lowpass';
                    filter.frequency.setValueAtTime(250, now);
                    filter.Q.setValueAtTime(2, now);
                    
                    mainGain.connect(filter);
                    filter.connect(ctx.destination);
                    
                    mainGain.gain.setValueAtTime(0, now);
                    mainGain.gain.linearRampToValueAtTime(0.5, now + 0.25);
                    mainGain.gain.setValueAtTime(0.5, now + 1.6);
                    mainGain.gain.exponentialRampToValueAtTime(0.001, now + 2.4);
                    
                    oscillators.forEach((freq, idx) => {{
                        let osc = ctx.createOscillator();
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(freq + detunes[idx], now);
                        
                        let oscGain = ctx.createGain();
                        oscGain.gain.setValueAtTime(gains[idx], now);
                        
                        osc.connect(oscGain);
                        oscGain.connect(mainGain);
                        
                        osc.start(now);
                        osc.stop(now + 2.5);
                    }});
                }} else if (type === 'success') {{
                    let osc = ctx.createOscillator();
                    let gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(523.25, ctx.currentTime);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                    osc.start(ctx.currentTime);
                    
                    let osc2 = ctx.createOscillator();
                    let gain2 = ctx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.type = 'sine';
                    osc2.frequency.setValueAtTime(659.25, ctx.currentTime + 0.1);
                    gain2.gain.setValueAtTime(0.3, ctx.currentTime + 0.1);
                    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
                    osc2.start(ctx.currentTime + 0.1);
                    
                    osc.stop(ctx.currentTime + 0.2);
                    osc2.stop(ctx.currentTime + 0.4);
                }} else if (type === 'warning') {{
                    let osc1 = ctx.createOscillator();
                    let gain1 = ctx.createGain();
                    osc1.connect(gain1);
                    gain1.connect(ctx.destination);
                    osc1.type = 'sine';
                    osc1.frequency.setValueAtTime(440, ctx.currentTime);
                    gain1.gain.setValueAtTime(0.2, ctx.currentTime);
                    gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                    osc1.start(ctx.currentTime);
                    osc1.stop(ctx.currentTime + 0.2);

                    let osc2 = ctx.createOscillator();
                    let gain2 = ctx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.type = 'sine';
                    osc2.frequency.setValueAtTime(440, ctx.currentTime + 0.15);
                    gain2.gain.setValueAtTime(0.2, ctx.currentTime + 0.15);
                    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                    osc2.start(ctx.currentTime + 0.15);
                    osc2.stop(ctx.currentTime + 0.35);
                }} else if (type === 'alert') {{
                    let osc = ctx.createOscillator();
                    let gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(150, ctx.currentTime);
                    
                    gain.gain.setValueAtTime(0.4, ctx.currentTime);
                    gain.gain.setValueAtTime(0, ctx.currentTime + 0.15);
                    gain.gain.setValueAtTime(0.4, ctx.currentTime + 0.25);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.45);
                    
                    osc.start(ctx.currentTime);
                    osc.stop(ctx.currentTime + 0.5);
                }} else if (type === 'info') {{
                    let osc1 = ctx.createOscillator();
                    let gain1 = ctx.createGain();
                    osc1.connect(gain1);
                    gain1.connect(ctx.destination);
                    osc1.type = 'sine';
                    osc1.frequency.setValueAtTime(600, ctx.currentTime);
                    gain1.gain.setValueAtTime(0.2, ctx.currentTime);
                    gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                    osc1.start(ctx.currentTime);
                    osc1.stop(ctx.currentTime + 0.3);

                    let osc2 = ctx.createOscillator();
                    let gain2 = ctx.createGain();
                    osc2.connect(gain2);
                    gain2.connect(ctx.destination);
                    osc2.type = 'sine';
                    osc2.frequency.setValueAtTime(800, ctx.currentTime + 0.08);
                    gain2.gain.setValueAtTime(0.2, ctx.currentTime + 0.08);
                    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.33);
                    osc2.start(ctx.currentTime + 0.08);
                    osc2.stop(ctx.currentTime + 0.38);
                }}
            }}

            function playSingleSound(sndType) {{
                if (sndType === 'silent') return;
                
                if (sndType.startsWith('tts:')) {{
                    const textToSpeak = sndType.substring(4);
                    if ('speechSynthesis' in window) {{
                        window.speechSynthesis.cancel();
                        let utterance = new SpeechSynthesisUtterance(textToSpeak);
                        utterance.lang = 'pt-BR';
                        utterance.volume = 1.0;
                        
                        let voices = window.speechSynthesis.getVoices();
                        let ptVoices = voices.filter(v => {{
                            let l = v.lang.toLowerCase();
                            return l.includes('pt-br') || l.includes('pt_br') || l === 'pt';
                        }});
                        
                        let naturalMale = ptVoices.find(v => {{
                            let name = v.name.toLowerCase();
                            return (name.includes('natural') || name.includes('online') || name.includes('neural')) && 
                                   (name.includes('valerio') || name.includes('antonio') || name.includes('fabio') || name.includes('male') || name.includes('daniel'));
                        }});
                        if (naturalMale) utterance.voice = naturalMale;
                        else {{
                            let anyPt = ptVoices.find(v => v.name.toLowerCase().includes('google')) || ptVoices[0];
                            if (anyPt) utterance.voice = anyPt;
                        }}
                        
                        window.speechSynthesis.speak(utterance);
                    }}
                    return;
                }}
                const customMp3Url = "{supabase_base_url}/storage/v1/object/public/sons/" + encodeURIComponent(sndType) + ".mp3";
                const customMp3UrlUpper = "{supabase_base_url}/storage/v1/object/public/sons/" + encodeURIComponent(sndType) + ".MP3";
                
                if (sndType.startsWith('naval_bell_')) {{
                    let count = 1;
                    if (sndType === 'naval_bell_singela') {{
                        count = 1;
                    }} else if (sndType === 'naval_bell_dobrada') {{
                        count = 2;
                    }} else {{
                        count = parseInt(sndType.split('_')[2]) || 1;
                    }}
                    
                    const singleMp3Url = "{supabase_base_url}/storage/v1/object/public/sons/bell_single.mp3";
                    const doubleMp3Url = "{supabase_base_url}/storage/v1/object/public/sons/bell_double.mp3";
                    
                    function playSynthesizedBells(ctx, count) {{
                        function playNavalBellStrike(ctx, time) {{
                            const frequencies = [240, 480, 576, 720, 960, 1200, 1440, 1920];
                            const gains = [0.35, 0.35, 0.25, 0.15, 0.15, 0.1, 0.08, 0.05];
                            const decays = [3.2, 2.6, 2.2, 1.8, 1.4, 1.0, 0.6, 0.4];

                            frequencies.forEach((f, idx) => {{
                                let osc = ctx.createOscillator();
                                let gainNode = ctx.createGain();
                                osc.connect(gainNode);
                                gainNode.connect(ctx.destination);
                                
                                osc.type = 'sine';
                                osc.frequency.setValueAtTime(f, time);
                                
                                gainNode.gain.setValueAtTime(0, time);
                                gainNode.gain.linearRampToValueAtTime(gains[idx], time + 0.005);
                                gainNode.gain.exponentialRampToValueAtTime(0.001, time + decays[idx]);
                                
                                osc.start(time);
                                osc.stop(time + decays[idx] + 0.1);
                            }});
                        }}

                        let now = ctx.currentTime;
                        for (let i = 0; i < count; i++) {{
                            let pairIndex = Math.floor(i / 2);
                            let inPairIndex = i % 2;
                            let timeOffset = pairIndex * 2.0 + inPairIndex * 0.15;
                            playNavalBellStrike(ctx, now + timeOffset);
                        }}
                             let testAudio = new Audio(singleMp3Url);
                    testAudio.volume = 0.0;
                    testAudio.play()
                        .then(() => {{
                            testAudio.pause();
                            let pairs = Math.floor(count / 2);
                            let remainder = count % 2;
                            for (let p = 0; p < pairs; p++) {{
                                setTimeout(() => {{
                                    let audio = new Audio(doubleMp3Url);
                                    audio.volume = 1.0;
                                    audio.play().catch(() => {{}});
                                }}, p * 2000);
                            }}
                            if (remainder > 0) {{
                                setTimeout(() => {{
                                    let audio = new Audio(singleMp3Url);
                                    audio.volume = 1.0;
                                    audio.play().catch(() => {{}});
                                }}, pairs * 2000);
                            }}
                        }})
                        .catch(() => {{
                            playSynthesizedBells(ctx, count);
                        }});
                }} else {{
                    let audio = new Audio(customMp3Url);
                    audio.volume = 1.0;
                    audio.play()
                        .catch(() => {{
                            let audioUpper = new Audio(customMp3UrlUpper);
                            audioUpper.volume = 1.0;
                            audioUpper.play()
                                .catch(() => {{
                                    playDefaultSynthesized(sndType);
                                }});
                        }});
                }}
            }}

            if (ctx && {json.dumps(sequence)}.length > 0) {{
                if (ctx.state === 'suspended') {{
                    ctx.resume();
                }}
                const seq = {json.dumps(sequence)};
                let accumulatedDelay = 0;
                seq.forEach(item => {{
                    let som = item.som || 'info';
                    let delay = parseFloat(item.delay) || 0;
                    accumulatedDelay += delay;
                    setTimeout(() => {{
                        playSingleSound(som);
                    }}, accumulatedDelay * 1000);
                }});
            }}
        }} catch (e) {{
            console.error("[AUDIO TEST] Erro ao reproduzir som:", e);
        }}
        """
        ui.run_javascript(js_code)

    # Carrega dados atuais
    try:
        config_df = data_service.get_config_data(force_refresh=True)
        if not config_df.empty:
            db_configs = dict(zip(config_df['chave'], config_df['valor']))
        else:
            db_configs = {}
    except Exception as e:
        print(f"[CONFIG] Erro ao carregar configurações: {e}")
        db_configs = {}

    # Mescla configurações carregadas com as padrões caso faltem chaves
    current_configs = {k: db_configs.get(k, v) for k, v in DEFAULT_CONFIGS.items()}

    from alerts_manager import load_alerts_config, save_alerts_config
    alerts_config = load_alerts_config()
    sound_mappings = alerts_config.get("sound_mappings", {})

    with ui.column().classes('w-full q-pa-lg gap-6'):
        ui.label('⚙️ CONFIGURAÇÕES DO SISTEMA').classes('text-2xl font-bold text-white cyber-title gt-xs q-mb-md q-ml-md')
        ui.add_head_html('''
        <style>
        .config-tabs .q-tabs__content {
            flex-wrap: wrap !important;
        }
        .config-tabs .q-tab {
            white-space: normal !important;
            min-height: 40px;
            height: auto !important;
            flex-shrink: 1 !important;
        }
        </style>
        ''')
    def testar_tts(texto: str, engine: str, el_key: str, el_voice: str, p_path: str, p_voice: str, google_lang: str = None, basic_voice: str = None):
        if not texto:
            ui.notify('Digite um texto para testar!', color='warning')
            return
            
        if engine == 'basic':
            import json
            escaped_text = json.dumps(texto)
            escaped_voice = json.dumps(basic_voice)
            js_code = f"""
            try {{
                window.speechSynthesis.cancel();
                let utterance = new SpeechSynthesisUtterance({escaped_text});
                utterance.lang = 'pt-BR';
                let voices = window.speechSynthesis.getVoices();
                let targetVoiceName = {escaped_voice};
                let selectedVoice = voices.find(v => v.name === targetVoiceName);
                if (selectedVoice) {{
                    utterance.voice = selectedVoice;
                }} else {{
                    let ptVoices = voices.filter(v => v.lang.toLowerCase().includes('pt-br') || v.lang.toLowerCase().includes('pt_br') || v.lang === 'pt');
                    let bestVoice = ptVoices.find(v => v.name.toLowerCase().includes('google')) || ptVoices[0];
                    if (bestVoice) utterance.voice = bestVoice;
                }}
                window.speechSynthesis.speak(utterance);
            }} catch(e) {{
                console.error(e);
            }}
            """
            ui.run_javascript(js_code)
            ui.notify('Sintetizando localmente via navegador...', color='info')
            return

        ui.notify('Processando áudio no servidor... (verifique o console F12 para logs)', color='info')
        audio_base64 = ""
        try:
            if engine == 'google':
                from ai_helper import generate_google_tts
                print(f"[CONFIG TEST] Testando Google TTS com texto: '{texto}' (idioma: {google_lang})")
                audio_base64 = generate_google_tts(texto, lang=google_lang)
            elif engine == 'elevenlabs':
                from ai_helper import generate_elevenlabs_tts_custom
                # Tentar carregar API Key do ambiente se não estiver no input
                api_key_to_use = (el_key.strip() if el_key else "") or os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_LABS") or os.getenv("ELEVEN") or ""
                if api_key_to_use:
                    api_key_to_use = api_key_to_use.strip()
                voice_id_to_use = (el_voice.strip() if el_voice else "") or "N2lVS1w4EtoT3dr4eOWO"
                
                print(f"[CONFIG TEST] Testando ElevenLabs TTS", flush=True)
                print(f"[CONFIG TEST] Voice ID: {voice_id_to_use} (tamanho: {len(voice_id_to_use)})", flush=True)
                print(f"[CONFIG TEST] API Key presente (input): {bool(el_key and len(el_key.strip()) > 0)}", flush=True)
                print(f"[CONFIG TEST] API Key presente (total): {bool(api_key_to_use and len(api_key_to_use) > 0)}", flush=True)
                print(f"[CONFIG TEST] API Key (primeiros 20 chars): {api_key_to_use[:20] if api_key_to_use else 'VAZIO'}...", flush=True)
                print(f"[CONFIG TEST] Texto: '{texto}'", flush=True)
                
                if not api_key_to_use:
                    error_msg = "ERRO: API Key do ElevenLabs nao configurada! Verifique Configuracoes -> TTS -> ElevenLabs"
                    print(f"[CONFIG TEST] VALIDACAO: {error_msg}", flush=True)
                    ui.notify(error_msg, color='negative')
                    return
                    
                result = generate_elevenlabs_tts_custom(texto, api_key_to_use, voice_id_to_use, return_error=True)
                audio_base64 = result.get('audio', '')
                error_from_tts = result.get('error', '')
                
                if error_from_tts:
                    print(f"[CONFIG TEST] Resultado: ERRO - {error_from_tts}", flush=True)
                    ui.notify(f'Erro ao gerar audio: {error_from_tts}', color='negative')
                    return
                    
                print(f"[CONFIG TEST] Resultado: {len(audio_base64) if audio_base64 else 0} caracteres (base64) retornados", flush=True)
            elif engine == 'piper':
                import subprocess
                import base64
                print(f"[CONFIG TEST] Testando Piper TTS")
                model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"{p_voice}.onnx")
                if not os.path.exists(model_path):
                    model_path = os.path.join("models", f"{p_voice}.onnx")
                
                if not os.path.exists(model_path):
                    error_msg = f'Erro Piper: Modelo {p_voice}.onnx não encontrado em {model_path}.'
                    print(f"[CONFIG TEST] ✗ {error_msg}")
                    ui.notify(error_msg, color='negative')
                    return
                if not os.path.exists(p_path):
                    error_msg = f'Erro Piper: executável {p_path} não encontrado.'
                    print(f"[CONFIG TEST] ✗ {error_msg}")
                    ui.notify(error_msg, color='negative')
                    return
                    
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_name = temp_wav.name
                try:
                    cmd = [p_path, "-m", model_path, "-f", temp_name]
                    print(f"[CONFIG TEST] Executando: {' '.join(cmd)}")
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    proc.communicate(input=texto.encode('utf-8'), timeout=10)
                    if os.path.exists(temp_name) and os.path.getsize(temp_name) > 0:
                        with open(temp_name, "rb") as f:
                            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                        os.remove(temp_name)
                        print(f"[CONFIG TEST] ✓ Áudio gerado com sucesso")
                except Exception as e:
                    error_msg = f'Erro ao rodar Piper: {e}'
                    print(f"[CONFIG TEST] ✗ {error_msg}")
                    ui.notify(error_msg, color='negative')
                    return
        except Exception as e:
            error_msg = f'Erro na geração: {e}'
            print(f"[CONFIG TEST] ✗ {error_msg}")
            ui.notify(error_msg, color='negative')
            return

        if not audio_base64:
            error_msg = 'Falha ao gerar áudio. Verifique o console (F12) para detalhes.'
            print(f"[CONFIG TEST] ✗ {error_msg}")
            ui.notify(error_msg, color='negative')
            return
            
        import json
        js_code = f"""
        try {{
            let audioBase64 = {json.dumps(audio_base64)};
            let mimeType = audioBase64.startsWith("UklGR") ? "audio/wav" : "audio/mp3";
            let audio = new Audio("data:" + mimeType + ";base64," + audioBase64);
            audio.volume = 1.0;
            console.log("[AUDIO TEST] Reproduzindo áudio gerado (" + audioBase64.length + " caracteres base64)");
            audio.play().catch(e => console.error("Error playing test audio: ", e));
        }} catch(e) {{
            console.error(e);
        }}
        """
        ui.run_javascript(js_code)
        print(f"[CONFIG TEST] ✓ Áudio gerado com sucesso. Reproduzindo...")
        ui.notify('Áudio gerado com sucesso. Reproduzindo...', color='success')

    with ui.tabs().classes('w-full border-b border-white/10 q-mb-md text-white flex-wrap') as tabs:
        ui.tab('geral', label='Parâmetros Gerais', icon='settings').classes('cyber-title text-xs font-bold')
        ui.tab('sons', label='Sons, Sinos & Alertas', icon='volume_up').classes('cyber-title text-xs font-bold')
        ui.tab('templates', label='Modelos de Mensagens', icon='chat').classes('cyber-title text-xs font-bold')
        ui.tab('telegram', label='Notificações Telegram', icon='notifications').classes('cyber-title text-xs font-bold')
        ui.tab('tts', label='Configuração de Voz (TTS)', icon='record_voice_over').classes('cyber-title text-xs font-bold')
        ui.tab('permissoes', label='Gerenciar Permissões', icon='admin_panel_settings').classes('cyber-title text-xs font-bold')
        ui.tab('backups', label='Cópia de Segurança (Backup)', icon='save_alt').classes('cyber-title text-xs font-bold')

    panels = ui.tab_panels(tabs, value='geral').classes('w-full bg-transparent')
    with panels:
        with ui.tab_panel('geral').classes('bg-transparent q-pa-none gap-6'):
            with ui.grid(columns='1 md:grid-cols-2').classes('w-full gap-6'):

                # --- CARD 3: PAINEL DE PROJEÇÃO / MODO TV ---
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('tv', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Painel de Projeção (Modo TV)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        ui.label('Configurações visuais e de sincronização do painel de monitoramento da TV de 60".').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                        
                        input_polling = ui.input(
                            'Tempo de Polling/Atualização (segundos)', 
                            value=current_configs['tempo_polling_tv']
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Tempo de intervalo em segundos para a TV buscar novas atualizações no Supabase (Padrão: 300 segundos = 5 min).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_cabecalho_tv = ui.input(
                            'Título do Cabeçalho da TV', 
                            value=current_configs['cabecalho_tv_title']
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Título principal exibido no topo da tela da TV (Padrão: MONITOR TÁTICO — COMUNICAÇÃO SOCIAL).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_subcabecalho_tv = ui.input(
                            'Subtítulo do Cabeçalho da TV', 
                            value=current_configs.get('cabecalho_tv_subtitle', 'COMUNICAÇÃO SOCIAL • GABINETE')
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Subtítulo secundário exibido no topo da tela da TV (Padrão: COMUNICAÇÃO SOCIAL • GABINETE).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_sunset_tv = ui.input(
                            'Horário do Pôr do Sol da TV (HH:MM)', 
                            value=current_configs.get('cabecalho_tv_sunset_time', '17:48')
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Configura o horário do pôr do sol para a sua localidade/base militar. Se deixado vazio, o sistema calculará automaticamente o horário ideal estimado para o dia do ano.').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_cargos_escala = ui.input(
                            'Funções/Cargos da Escala (separados por vírgula)', 
                            value=current_configs['cargos_escala_lista']
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Lista de cargos da escala diária disponíveis para preenchimento (ex: INSPETOR DO DIA, SUPERVISOR, etc.).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_unlock_code = ui.input(
                            'Código de Desbloqueio da TV (Blur)', 
                            value=current_configs.get('codigo_desbloqueio_tv', '1234')
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Código padrão exigido para reexibir as anotações do dia quando ocultadas no Modo TV (Padrão: 1234).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_alerta_tv = ui.input(
                            'Tempo de Exibição de Alertas da TV (segundos)', 
                            value=current_configs.get('tempo_alerta_tv', '10')
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Tempo padrão em segundos de exibição dos alertas visuais/toasts no Modo TV (Padrão: 10 segundos).').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                        input_telegram_token = ui.input(
                            'Token do Bot do Telegram', 
                            value=current_configs.get('telegram_bot_token', ''),
                            password=True
                        ).props('dark dense outlined w-full').classes('w-full')
                        ui.label('Token de autenticação do Telegram Bot (obtido via @BotFather). Se vazio, usará a variável TELEGRAM_TOKEN do arquivo .env.').classes('text-[10px] q-mt-xs').style(f'color: {THEME["text_dim"]}')

                # --- CARD 4: GESTÃO DE ORDENS DIÁRIAS (AVISOS DA TV) ---
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('campaign', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Ordens Diárias e Avisos (TV)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        ui.label('Adicione avisos e ordens para rodar no painel de anotações e letreiro da TV de 60".').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                        
                        order_state = {
                            'date': date.today().strftime('%Y-%m-%d'),
                        }
                        
                        with ui.row().classes('w-full items-center gap-2'):
                            date_input = ui.input(
                                'Data dos Avisos', 
                                value=order_state['date']
                            ).props('dark dense outlined type=date').classes('col-grow')
                            
                            def on_date_change():
                                order_state['date'] = date_input.value
                                render_orders_list.refresh()
                            date_input.on('change', on_date_change)
                        
                        @ui.refreshable
                        def render_orders_list():
                            db_conn = get_db_connection()
                            orders = []
                            if db_conn:
                                try:
                                    res = db_conn.table('Ordens_Diarias').select('*').eq('data', order_state['date']).execute()
                                    orders = res.data if res.data else []
                                except Exception as e:
                                    print(f"[CONFIG] Erro ao carregar ordens: {e}")
                            else:
                                mock_list = getattr(app, '_mock_ordens_diarias', [])
                                orders = [o for o in mock_list if o['data'] == order_state['date']]
                                
                            with ui.column().classes('w-full gap-2 border border-white/5 q-pa-sm rounded bg-black/10').style('max-height: 150px; overflow-y: auto;'):
                                if not orders:
                                    ui.label('Sem avisos cadastrados para esta data.').classes('text-xs italic text-grey-5 text-center w-full py-2')
                                else:
                                    for o in orders:
                                        with ui.row().classes('w-full justify-between items-center no-wrap py-1 border-b border-white/5'):
                                            with ui.column().classes('gap-0 col-grow min-w-0'):
                                                ui.label(o['texto']).classes('text-xs text-white break-words')
                                                ui.label(f"Por: {o.get('autor_id', 'ADMIN')}").classes('text-[9px] text-grey-5')
                                            
                                            def excluir_ordem(o_id=o.get('id'), o_text=o.get('texto')):
                                                db_c = get_db_connection()
                                                if db_c:
                                                    try:
                                                        if o_id:
                                                            db_c.table('Ordens_Diarias').delete().eq('id', o_id).execute()
                                                        else:
                                                            db_c.table('Ordens_Diarias').delete().eq('data', order_state['date']).eq('texto', o_text).execute()
                                                        ui.notify('Aviso excluído com sucesso!', color='success')
                                                    except Exception as err:
                                                        ui.notify(f'Erro ao excluir: {err}', color='red')
                                                else:
                                                    mock_m = getattr(app, '_mock_ordens_diarias', [])
                                                    if o_id:
                                                        mock_m = [item for item in mock_m if item.get('id') != o_id]
                                                    else:
                                                        mock_m = [item for item in mock_m if not (item['data'] == order_state['date'] and item['texto'] == o_text)]
                                                    app._mock_ordens_diarias = mock_m
                                                    ui.notify('Aviso excluído localmente.', color='warning')
                                                render_orders_list.refresh()
                                            
                                            with ui.row().classes('items-center gap-1 shrink-0'):
                                                def abrir_editar_ordem_dialog(order=o):
                                                    d_edit = ui.dialog()
                                                    with d_edit, ui.card().classes('w-[360px] q-pa-md bg-slate-900 border border-cyan-5'):
                                                        ui.label('✏️ EDITAR AVISO').classes('text-white text-sm font-black cyber-title q-mb-xs')
                                                        edit_inp = ui.input('Texto do Aviso', value=order['texto']).props('dark outlined dense w-full').classes('w-full')
                                                        
                                                        def salvar_edicao():
                                                            txt_val = edit_inp.value.strip()
                                                            if not txt_val:
                                                                ui.notify('O texto não pode ser vazio.', color='warning')
                                                                return
                                                            db_u = get_db_connection()
                                                            if db_u:
                                                                try:
                                                                    db_u.table('Ordens_Diarias').update({'texto': txt_val}).eq('id', order['id']).execute()
                                                                    ui.notify('Aviso editado com sucesso!', color='success')
                                                                except Exception as err:
                                                                    ui.notify(f'Erro ao atualizar: {err}', color='red')
                                                            else:
                                                                mock_m = getattr(app, '_mock_ordens_diarias', [])
                                                                for item in mock_m:
                                                                    if item.get('id') == order.get('id') or (item['data'] == order['data'] and item['texto'] == order['texto']):
                                                                        item['texto'] = txt_val
                                                                        break
                                                                app._mock_ordens_diarias = mock_m
                                                                ui.notify('Aviso editado localmente.', color='warning')
                                                            d_edit.close()
                                                            render_orders_list.refresh()
                                                            
                                                        with ui.row().classes('w-full justify-end gap-2 q-mt-sm'):
                                                            ui.button('Cancelar', on_click=d_edit.close).props('flat color=grey no-caps')
                                                            ui.button('Salvar', on_click=salvar_edicao).props('unelevated color=cyan-9 text-color=white no-caps')
                                                    d_edit.open()
                                                    
                                                ui.button(
                                                    icon='edit', 
                                                    on_click=abrir_editar_ordem_dialog
                                                ).props('flat round dense color=cyan').classes('text-xs')
                                                
                                                ui.button(
                                                    icon='delete', 
                                                    on_click=excluir_ordem
                                                ).props('flat round dense color=red').classes('text-xs')
                        
                        render_orders_list()
                        
                        input_ordem_text = ui.input(
                            'Novo Aviso',
                            placeholder='Ex: Formatura Geral às 07:30 Uniforme 3º A.'
                        ).props('dark dense outlined w-full').classes('w-full')
                        
                        def adicionar_ordem():
                            val = input_ordem_text.value.strip()
                            if not val:
                                ui.notify('Digite o texto do aviso.', color='red')
                                return
                            
                            autor = app.storage.user.get('user_data', {}).get('nome_guerra', 'ADMIN').upper()
                            db_conn = get_db_connection()
                            if db_conn:
                                try:
                                    db_conn.table('Ordens_Diarias').insert({
                                        'data': order_state['date'],
                                        'texto': val,
                                        'autor_id': autor,
                                        'status': 'Ativo'
                                    }).execute()
                                    ui.notify('Aviso adicionado com sucesso!', color='success')
                                except Exception as err:
                                    ui.notify(f'Erro ao salvar no banco: {err}', color='red')
                            else:
                                if not hasattr(app, '_mock_ordens_diarias'):
                                    app._mock_ordens_diarias = []
                                import random
                                app._mock_ordens_diarias.append({
                                    'id': random.randint(1000, 9999),
                                    'data': order_state['date'],
                                    'texto': val,
                                    'autor_id': autor,
                                    'status': 'Ativo'
                                })
                                ui.notify('Aviso adicionado localmente (offline)!', color='warning')
                            
                            # Transmite à TV em tempo real
                            try:
                                from alerts_manager import AlertsManager
                                AlertsManager.trigger_alert(
                                    "Novo Aviso",
                                    f"Aviso publicado por {autor}: {val}",
                                    "info"
                                )
                            except Exception as e_alert:
                                print(f"[CONFIG] Erro ao disparar alerta de aviso: {e_alert}")
                                
                            # Envia notificação Telegram
                            try:
                                from notifications_manager import notify_telegram
                                alert_txt = (
                                    f"📢 **NOVO AVISO CRÍTICO PUBLICADO**\n"
                                    f"👤 Autor: {autor}\n\n"
                                    f"\"{val}\""
                                )
                                notify_telegram(alert_txt, "aviso")
                            except Exception as e_notif:
                                print(f"[CONFIG AVISO NOTIFY ERROR] {e_notif}")
                                
                            input_ordem_text.value = ''
                            render_orders_list.refresh()
                        
                        ui.button(
                            'Adicionar Aviso', 
                            icon='add', 
                            on_click=adicionar_ordem
                        ).props('unelevated color=amber-9 text-color=black w-full dense').classes('bold')
                
                # --- ABA 2: PERSONALIZAÇÃO DE SONS E ALERTAS ---
        with ui.tab_panel('sons').classes('bg-transparent q-pa-none gap-6'):
            # --- CARD 1: SINOS NAVAIS E ALERTAS AGENDADOS ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('alarm', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Sinos Navais e Alertas Agendados').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    # Switch do Sino Automático
                    input_tv_vocativo = ui.input(
                        'Vocativo Personalizado de Alerta (Modo TV)',
                        value=alerts_config.get('tv_alert_vocativo', 'Atenção!')
                    ).props('dark dense outlined').classes('w-full text-xs').style('max-width: 400px;')
                    
                    ui.separator().style('background-color: rgba(255,255,255,0.05); height: 1px;')
                    ui.label('Agendar Novo Alerta Horário:').classes('text-xs font-bold text-white')
                    
                    # Declarar opções de som vazias inicialmente, serão atualizadas por atualizar_opcoes_de_sons
                    som_opcoes = {}
                    som_e_sequencias_opcoes = {}
                    sound_dropdowns = {}
                    custom_sequence_dropdowns = {}
                    
                    def atualizar_opcoes_de_sons():
                        nonlocal som_opcoes, som_e_sequencias_opcoes
                        som_opcoes = {
                            'info': 'Chime Digital Premium 🎵',
                            'success': 'Chime de Sucesso (Do-Mi) 🎉',
                            'warning': 'Aviso Duplo Ping 🔔',
                            'alert': 'Alerta Tático Grave ⚠️',
                            'submarine_sonar': 'Sonar Submarino 📡',
                            'morse_sos': 'Código Morse SOS 🆘',
                            'naval_horn': 'Buzina de Navio (Grave) 🚢',
                            'naval_bell_singela': 'Sino Marinheiro Singelo (1 Batida) ⚓',
                            'naval_bell_dobrada': 'Sino Marinheiro Dobrado (2 Batidas) ⚓',
                            'naval_bell_4': 'Sino da Marinha (4 Baladas / 2 Dobradas) ⚓',
                            'naval_bell_8': 'Sino da Marinha (8 Baladas / 4 Dobradas) ⚓',
                            'silent': 'Silencioso 🔕'
                        }
                        db_conn = get_admin_db_connection() or get_db_connection()
                        if db_conn:
                            try:
                                res = db_conn.storage.from_('sons').list()
                                if res:
                                    for item in res:
                                        f = item.get('name')
                                        if f and f.lower().endswith('.mp3'):
                                            key = f[:-4]
                                            if key not in som_opcoes:
                                                friendly_name = key.replace('_', ' ').replace('-', ' ').title()
                                                som_opcoes[key] = f"Arquivo: {friendly_name} 🎵"
                            except Exception as e:
                                print(f"[CONFIG] Erro ao listar sons: {e}")

                        # Constrói som_e_sequencias_opcoes contendo sons + sequências personalizadas
                        som_e_sequencias_opcoes.clear()
                        som_e_sequencias_opcoes.update(som_opcoes)
                        
                        c_config = load_alerts_config()
                        custom_seqs = c_config.get('custom_sequences', {})
                        for seq_name in custom_seqs:
                            som_e_sequencias_opcoes[seq_name] = f"✨ Sequência: {seq_name}"
                        
                        # Atualiza dropdowns de eventos
                        try:
                            render_sound_mappings_editor.refresh()
                        except Exception as e:
                            pass
                        # Atualiza dropdown de agendamento se inicializado
                        try:
                            select_alerta_sound.options = som_e_sequencias_opcoes
                            select_alerta_sound.update()
                        except Exception:
                            pass
                        # Atualiza dropdown de edição se inicializado
                        try:
                            edit_sound.options = som_e_sequencias_opcoes
                            edit_sound.update()
                        except Exception:
                            pass

                    atualizar_opcoes_de_sons()
                    
                    with ui.row().classes('w-full items-center gap-2'):
                        input_alerta_time = ui.input('Hora', placeholder='07:30').props('dark dense outlined mask=##:## w-1/5').classes('text-xs')
                        input_alerta_title = ui.input('Título', placeholder='Aviso').props('dark dense outlined w-1/4').classes('text-xs')
                        input_alerta_msg = ui.input('Mensagem', placeholder='Instrução Geral no Pátio').props('dark dense outlined col-grow').classes('text-xs')
                        
                        select_alerta_sound = ui.select(som_e_sequencias_opcoes, value='info').props('dark dense outlined').classes('text-xs min-w-[120px]')
                        ui.button(
                            icon='play_arrow', 
                            on_click=lambda: testar_som(select_alerta_sound.value)
                        ).props('flat round dense color=primary').classes('text-xs').style('margin-left:-4px')

                    with ui.row().classes('w-full items-center gap-4 q-mb-sm'):
                        switch_visual = ui.checkbox('Exibição Visual (TV)', value=True).props('dark').classes('text-xs text-white')
                        switch_voice = ui.checkbox('Fala (Voz)', value=True).props('dark').classes('text-xs text-white')
                        switch_sound = ui.checkbox('Efeito Sonoro', value=True).props('dark').classes('text-xs text-white')
                    
                    # Diálogo de Edição de Alerta Horário
                    with ui.dialog() as edit_dialog:
                        with theme.card_base().classes('q-pa-md').style('min-width: 400px;'):
                            with ui.column().classes('w-full gap-4'):
                                ui.label('✏️ Editar Alerta Agendado').classes('text-lg font-bold text-white')
                                ui.separator().style('background-color: rgba(255,255,255,0.1);')
                                
                                edit_time = ui.input('Hora', placeholder='07:30').props('dark dense outlined mask=##:##').classes('w-full')
                                edit_title = ui.input('Título', placeholder='Aviso').props('dark dense outlined').classes('w-full')
                                edit_msg = ui.input('Mensagem', placeholder='Texto do Alerta').props('dark dense outlined').classes('w-full')
                                edit_sound = ui.select(som_e_sequencias_opcoes, label='Som').props('dark dense outlined').classes('w-full')
                                
                                with ui.row().classes('w-full items-center gap-2'):
                                    edit_visual = ui.checkbox('Exibição Visual (TV)', value=True).props('dark').classes('text-xs text-white')
                                    edit_voice = ui.checkbox('Fala (Voz)', value=True).props('dark').classes('text-xs text-white')
                                    edit_sound_enabled = ui.checkbox('Efeito Sonoro', value=True).props('dark').classes('text-xs text-white')
                                
                                alerta_editando_id = ui.label('').classes('hidden')
                                
                                def salvar_edicao():
                                    a_id = alerta_editando_id.text
                                    time_val = edit_time.value.strip()
                                    title_val = edit_title.value.strip()
                                    msg_val = edit_msg.value.strip()
                                    
                                    if not time_val or len(time_val) < 5:
                                        ui.notify('Digite o horário no formato HH:MM (ex: 07:30)', color='red')
                                        return
                                        
                                    c_config = load_alerts_config()
                                    for idx, item in enumerate(c_config.get('custom_alerts', [])):
                                        if item.get('id') == a_id:
                                            c_config['custom_alerts'][idx] = {
                                                'id': a_id,
                                                'time': time_val,
                                                'title': title_val,
                                                'message': msg_val,
                                                'sound': edit_sound.value,
                                                'visual_alert': edit_visual.value,
                                                'voice_enabled': edit_voice.value,
                                                'sound_enabled': edit_sound_enabled.value,
                                                'enabled': item.get('enabled', True)
                                            }
                                            break
                                    save_alerts_config(c_config)
                                    ui.notify('Alerta atualizado com sucesso!', color='success')
                                    edit_dialog.close()
                                    render_custom_alerts_list.refresh()
                                    
                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=edit_dialog.close).props('outline dense color=grey')
                                    ui.button('Salvar', on_click=salvar_edicao).props('unelevated dense color=primary')

                    alerta_duplicar_item = [None]
                    with ui.dialog() as duplicate_dialog:
                        with theme.card_base().classes('q-pa-md').style('min-width: 320px;'):
                            with ui.column().classes('w-full gap-4'):
                                ui.label('👯 Duplicar Alerta Agendado').classes('text-md font-bold text-white')
                                ui.separator().style('background-color: rgba(255,255,255,0.1);')
                                
                                dup_time = ui.input('Novo Horário', placeholder='07:30').props('dark dense outlined mask=##:##').classes('w-full')
                                
                                def salvar_duplicacao():
                                    time_val = dup_time.value.strip()
                                    if not time_val or len(time_val) < 5:
                                        ui.notify('Digite o horário no formato HH:MM (ex: 07:30)', color='red')
                                        return
                                    ref_item = alerta_duplicar_item[0]
                                    if not ref_item:
                                        return
                                    
                                    import uuid
                                    c_config = load_alerts_config()
                                    novo = {
                                        'id': str(uuid.uuid4())[:8],
                                        'time': time_val,
                                        'title': ref_item.get('title', ''),
                                        'message': ref_item.get('message', ''),
                                        'sound': ref_item.get('sound', 'info'),
                                        'visual_alert': ref_item.get('visual_alert', True),
                                        'voice_enabled': ref_item.get('voice_enabled', True),
                                        'sound_enabled': ref_item.get('sound_enabled', True),
                                        'enabled': True
                                    }
                                    c_config.setdefault('custom_alerts', []).append(novo)
                                    save_alerts_config(c_config)
                                    ui.notify('Alerta duplicado com sucesso!', color='success')
                                    duplicate_dialog.close()
                                    render_custom_alerts_list.refresh()
                                
                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=duplicate_dialog.close).props('outline dense color=grey')
                                    ui.button('Duplicar', on_click=salvar_duplicacao).props('unelevated dense color=primary')
                                    
                    def abrir_duplicar(alerta_item):
                        alerta_duplicar_item[0] = alerta_item
                        dup_time.value = alerta_item['time']
                        duplicate_dialog.open()

                    @ui.refreshable
                    def render_custom_alerts_list():
                        curr_config = load_alerts_config()
                        alerts = curr_config.get("custom_alerts", [])
                        
                        with ui.column().classes('w-full gap-2 border border-white/5 q-pa-sm rounded bg-black/10').style('max-height: 150px; overflow-y: auto;'):
                            if not alerts:
                                ui.label('Sem alertas horários agendados.').classes('text-xs italic text-grey-5 text-center w-full py-2')
                            else:
                                for a in alerts:
                                    with ui.row().classes('w-full justify-between items-center no-wrap py-1 border-b border-white/5'):
                                        with ui.row().classes('items-center gap-2 col-grow min-w-0'):
                                            ui.label(a['time']).classes('text-xs text-amber-5 bold')
                                            with ui.column().classes('gap-0 min-w-0'):
                                                ui.label(f"{a['title']}: {a['message']}").classes('text-xs text-white break-words')
                                                opts = []
                                                if a.get('visual_alert', True): opts.append('📺 TV')
                                                if a.get('voice_enabled', True): opts.append('🗣️ Voz')
                                                if a.get('sound_enabled', True): opts.append('🔊 Som')
                                                opts_str = " | ".join(opts) if opts else "Silencioso"
                                                # Usa som_e_sequencias_opcoes para traduzir o som/sequência amigável
                                                ui.label(f"Som: {som_e_sequencias_opcoes.get(a['sound'], a['sound'])} ({opts_str})").classes('text-[9px] text-grey-5')
                                        
                                        def excluir_alerta(a_id):
                                            c_config = load_alerts_config()
                                            c_config['custom_alerts'] = [item for item in c_config['custom_alerts'] if item.get('id') != a_id]
                                            save_alerts_config(c_config)
                                            ui.notify('Alerta agendado excluído!', color='success')
                                            render_custom_alerts_list.refresh()
                                            
                                        def carregar_e_abrir_editar(alerta_item=a):
                                            alerta_editando_id.set_text(alerta_item['id'])
                                            edit_time.value = alerta_item['time']
                                            edit_title.value = alerta_item['title']
                                            edit_msg.value = alerta_item['message']
                                            edit_sound.value = alerta_item['sound'] if alerta_item['sound'] in som_e_sequencias_opcoes else 'info'
                                            edit_visual.value = alerta_item.get('visual_alert', True)
                                            edit_voice.value = alerta_item.get('voice_enabled', True)
                                            edit_sound_enabled.value = alerta_item.get('sound_enabled', True)
                                            edit_dialog.open()

                                        with ui.row().classes('items-center gap-1'):
                                            ui.button(
                                                icon='play_arrow', 
                                                on_click=lambda _, s=a['sound']: testar_som(s)
                                            ).props('flat round dense color=primary').classes('text-xs').tooltip('Testar')
                                            ui.button(
                                                icon='content_copy', 
                                                on_click=lambda _, a_item=a: abrir_duplicar(a_item)
                                            ).props('flat round dense color=primary').classes('text-xs').tooltip('Duplicar')
                                            ui.button(
                                                icon='edit', 
                                                on_click=lambda _, a_item=a: carregar_e_abrir_editar(a_item)
                                            ).props('flat round dense color=primary').classes('text-xs').tooltip('Editar')
                                            ui.button(
                                                icon='delete', 
                                                on_click=lambda _, a_id=a['id']: excluir_alerta(a_id)
                                            ).props('flat round dense color=red').classes('text-xs').tooltip('Excluir')
                    
                    render_custom_alerts_list()
                    
                    def cadastrar_novo_alerta():
                        time_val = input_alerta_time.value.strip()
                        title_val = input_alerta_title.value.strip()
                        msg_val = input_alerta_msg.value.strip()
                        
                        if not time_val or len(time_val) < 5:
                            ui.notify('Digite o horário no formato HH:MM (ex: 07:30)', color='red')
                            return
                            
                        import uuid
                        c_config = load_alerts_config()
                        novo = {
                            'id': str(uuid.uuid4())[:8],
                            'time': time_val,
                            'title': title_val,
                            'message': msg_val,
                            'sound': select_alerta_sound.value,
                            'visual_alert': switch_visual.value,
                            'voice_enabled': switch_voice.value,
                            'sound_enabled': switch_sound.value,
                            'enabled': True
                        }
                        c_config.setdefault('custom_alerts', []).append(novo)
                        save_alerts_config(c_config)
                        
                        ui.notify('Alerta agendado cadastrado com sucesso!', color='success')
                        input_alerta_time.value = ''
                        input_alerta_title.value = ''
                        input_alerta_msg.value = ''
                        switch_visual.value = True
                        switch_voice.value = True
                        switch_sound.value = True
                        render_custom_alerts_list.refresh()
                        
                    ui.button(
                        'Adicionar Alerta Agendado', 
                        icon='add', 
                        on_click=cadastrar_novo_alerta
                    ).props('unelevated color=amber-9 text-color=black w-full dense').classes('bold')

            # --- CARD 2: PERSONALIZAÇÃO DE SONS DOS EVENTOS ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('volume_up', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Personalização de Sons de Eventos').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Configure a sequência de efeitos sonoros reproduzida no Modo TV para cada evento do sistema:').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    def build_sound_sequence_editor(ocorrencia_nome, val_som, target_dict=sound_dropdowns):
                        sequence = []
                        if isinstance(val_som, list):
                            for item in val_som:
                                if isinstance(item, dict):
                                    sequence.append({'som': item.get('som', 'info'), 'delay': float(item.get('delay', 0.0))})
                                else:
                                    sequence.append({'som': str(item), 'delay': 0.0})
                        elif isinstance(val_som, str):
                            sequence.append({'som': val_som, 'delay': 0.0})
                        
                        if not sequence:
                            sequence.append({'som': 'info', 'delay': 0.0})

                        target_dict[ocorrencia_nome] = sequence

                        @ui.refreshable
                        def render_sequence():
                            ui.label(ocorrencia_nome).classes('text-xs text-white font-bold')
                            with ui.column().classes('w-full gap-2 pl-4 border-l border-cyan-500/20 q-mb-md'):
                                for idx, seq_item in enumerate(sequence):
                                    with ui.row().classes('w-full items-center gap-2'):
                                        is_tts = str(seq_item['som']).startswith('tts:')
                                        if is_tts:
                                            # Extrai o texto da voz
                                            tts_text = seq_item['som'][4:]
                                            
                                            # Campo de texto para a voz
                                            ui.icon('record_voice_over', color='cyan-5').classes('text-sm')
                                            txt_input = ui.input(
                                                label='Texto para Falar (TTS)',
                                                value=tts_text
                                            ).props('dark dense outlined').classes('text-xs col-grow')
                                            
                                            # Função para atualizar o valor
                                            txt_input.on('change', lambda e, i=idx: [sequence[i].update({'som': 'tts:' + (e.value or '')})])
                                            
                                            # Botão para alternar de volta para som
                                            ui.button(
                                                icon='music_note',
                                                on_click=lambda _, i=idx: [sequence[i].update({'som': 'info'}), render_sequence.refresh()]
                                            ).props('flat round dense color=grey').classes('text-xs').tooltip('Mudar para Arquivo de Som')
                                        else:
                                            # Dropdown de seleção de som (inclui a opção de Voz/TTS)
                                            opts = {**som_opcoes, 'tts': '🗣️ Voz (TTS / Sintetizador)...'}
                                            
                                            def make_on_change(i=idx):
                                                def on_change_inner(e):
                                                    if e.value == 'tts':
                                                        sequence[i]['som'] = 'tts:Atenção!'
                                                        render_sequence.refresh()
                                                    else:
                                                        sequence[i]['som'] = e.value
                                                return on_change_inner

                                            ui.select(
                                                opts,
                                                value=seq_item['som'] if seq_item['som'] in som_opcoes else 'info',
                                                on_change=make_on_change()
                                            ).props('dark dense outlined').classes('text-xs min-w-[200px]')
                                        
                                        # Campo de atraso (delay) antes do som
                                        ui.label('Atraso:').classes('text-[11px] text-grey-5')
                                        delay_input = ui.number(
                                            value=seq_item['delay'],
                                            min=0.0,
                                            max=30.0,
                                            step=0.5,
                                            format='%.1f'
                                        ).props('dark dense outlined').classes('w-16 text-xs').style('margin-right: 4px;')
                                        delay_input.on('change', lambda e, i=idx: [sequence[i].update({'delay': float(e.value or 0.0)})])
                                        
                                        # Botão de teste para este som individual
                                        ui.button(
                                            icon='play_arrow',
                                            on_click=lambda _, idx=idx: testar_som(sequence[idx]['som'])
                                        ).props('flat round dense color=primary').classes('text-xs')
                                        
                                        # Botão de remoção (se houver mais de 1 som)
                                        if len(sequence) > 1:
                                            ui.button(
                                                icon='delete',
                                                on_click=lambda _, i=idx: [sequence.pop(i), render_sequence.refresh()]
                                            ).props('flat round dense color=red').classes('text-xs')
                                
                                # Botão para adicionar som na sequência
                                ui.button(
                                    'Adicionar Som na Sequência',
                                    icon='add',
                                    on_click=lambda: [sequence.append({'som': 'info', 'delay': 1.0}), render_sequence.refresh()]
                                ).props('outline dense no-caps color=primary').classes('text-[11px] self-start')

                        render_sequence()

                    @ui.refreshable
                    def render_sound_mappings_editor():
                        for ocorrencia_nome, som_atual in sound_mappings.items():
                            val_som = sound_dropdowns.get(ocorrencia_nome, som_atual)
                            with ui.row().classes('w-full items-center justify-between gap-2 border-b border-white/5 py-2'):
                                build_sound_sequence_editor(ocorrencia_nome, val_som)

                    render_sound_mappings_editor()

            # --- CARD 3: SEQUÊNCIAS DE SOM PERSONALIZADAS ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('queue_music', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Sequências de Som Personalizadas').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Crie sequências complexas de efeitos sonoros com atrasos personalizados. Elas ficarão disponíveis para seleção em Sinos & Alertas Agendados.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    @ui.refreshable
                    def render_custom_sequences_editor():
                        curr_config = load_alerts_config()
                        custom_seqs = curr_config.get('custom_sequences', {})
                        custom_sequence_dropdowns.clear()
                        
                        if not custom_seqs:
                            ui.label('Nenhuma sequência de som personalizada criada.').classes('text-xs italic q-pa-sm').style(f'color: {THEME["text_dim"]}')
                        else:
                            for seq_name, seq_val in list(custom_seqs.items()):
                                with ui.card().classes('w-full q-pa-md border border-white/10 rounded bg-black/5 q-mb-sm'):
                                    with ui.row().classes('w-full items-center justify-between'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon('music_note', color='amber-9', size='1.2rem')
                                            ui.label(f"Sequência: {seq_name}").classes('text-sm font-bold text-white')
                                            
                                        def excluir_seq(name=seq_name):
                                            c_config = load_alerts_config()
                                            if 'custom_sequences' in c_config and name in c_config['custom_sequences']:
                                                del c_config['custom_sequences'][name]
                                                if name in custom_sequence_dropdowns:
                                                    del custom_sequence_dropdowns[name]
                                                # Se algum agendamento usa essa sequência, volta pra 'info'
                                                for item in c_config.get('custom_alerts', []):
                                                    if item.get('sound') == name:
                                                        item['sound'] = 'info'
                                                save_alerts_config(c_config)
                                                ui.notify(f"Sequência '{name}' excluída com sucesso!", color='success')
                                                atualizar_opcoes_de_sons()
                                                render_custom_sequences_editor.refresh()
                                                render_custom_alerts_list.refresh()
                                                
                                        ui.button(
                                            icon='delete',
                                            on_click=excluir_seq
                                        ).props('flat round dense color=red').classes('text-xs').tooltip('Excluir Sequência')
                                        
                                    ui.separator().classes('q-my-xs').style('opacity: 0.1;')
                                    build_sound_sequence_editor(seq_name, seq_val, target_dict=custom_sequence_dropdowns)
                                    
                    render_custom_sequences_editor()
                    
                    # Form para nova sequência
                    with ui.row().classes('w-full items-end gap-2 q-mt-md'):
                        input_nova_seq_nome = ui.input(
                            'Nome da Nova Sequência', 
                            placeholder='Ex: Toque de Alvorada Especial'
                        ).props('dark dense outlined').classes('text-xs col-grow')
                        
                        def criar_nova_sequencia():
                            name = input_nova_seq_nome.value.strip()
                            if not name:
                                ui.notify('Digite um nome para a sequência!', color='warning')
                                return
                            
                            import re
                            name_clean = re.sub(r'[^\w\s\-]', '', name).strip()
                            if not name_clean:
                                ui.notify('Nome de sequência inválido!', color='warning')
                                return
                                
                            c_config = load_alerts_config()
                            if 'custom_sequences' not in c_config:
                                c_config['custom_sequences'] = {}
                                
                            if name_clean in c_config['custom_sequences']:
                                ui.notify('Já existe uma sequência com este nome!', color='warning')
                                return
                                
                            # Inicializa com um som padrão
                            c_config['custom_sequences'][name_clean] = [{'som': 'info', 'delay': 0.0}]
                            save_alerts_config(c_config)
                            
                            ui.notify(f"Sequência '{name_clean}' criada! Configure seus sons abaixo.", color='success')
                            input_nova_seq_nome.value = ''
                            atualizar_opcoes_de_sons()
                            render_custom_sequences_editor.refresh()
                            
                        ui.button(
                            'Criar Sequência',
                            icon='playlist_add',
                            on_click=criar_nova_sequencia
                        ).props('unelevated color=primary dense').classes('text-xs font-bold q-px-md')

            # --- CARD 4: GERENCIADOR DE ARQUIVOS DE SOM ---
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('folder_open', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Gerenciamento de Arquivos de Som').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Envie arquivos .mp3 customizados para usar como toques de alerta e sinos.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    # Upload de Som
                    async def handle_sound_upload(e):
                        try:
                            import inspect
                            
                            # Extrai o nome de forma robusta
                            filename = getattr(e, 'name', None) or getattr(getattr(e, 'file', None), 'name', None)
                            if not filename:
                                filename = 'som_upload.mp3'
                                
                            if not filename.lower().endswith('.mp3'):
                                ui.notify('Apenas arquivos no formato .mp3 são suportados!', color='red')
                                return
                            
                            if filename in ('bell_single.mp3', 'bell_double.mp3'):
                                ui.notify('Não é permitido sobrescrever arquivos de sistema.', color='red')
                                return
                                
                            # Extrai o conteúdo (bytes) de forma robusta
                            file_bytes = None
                            file_obj = getattr(e, 'file', None) or getattr(e, 'content', None)
                            if file_obj and hasattr(file_obj, 'read'):
                                file_bytes = file_obj.read()
                                if inspect.isawaitable(file_bytes):
                                    file_bytes = await file_bytes
                                    
                            if not file_bytes:
                                ui.notify('Falha ao ler o conteúdo do arquivo enviado.', color='red')
                                return
                                
                            from database import upload_file_to_supabase_storage
                            import asyncio
                            
                            async def process_upload():
                                 public_url = await asyncio.to_thread(
                                     upload_file_to_supabase_storage,
                                     file_bytes,
                                     filename,
                                     "audio/mpeg",
                                     "sons"
                                 )
                                 if public_url:
                                     ui.notify(f'Som "{filename}" enviado com sucesso!', color='success')
                                     atualizar_opcoes_de_sons()
                                     render_sound_files_list.refresh()
                                     try:
                                         render_custom_alerts_list.refresh()
                                     except Exception:
                                         pass
                                 else:
                                     ui.notify('Erro ao enviar som ao Supabase.', color='red')
                            
                            await process_upload()
                        except Exception as ex:
                            ui.notify(f'Erro ao salvar arquivo: {ex}', color='red')
                            
                    ui.upload(label='Enviar Som (.mp3)', auto_upload=True, on_upload=handle_sound_upload).props('dark accept=.mp3 max-files=1').classes('w-full h-24')
                    
                    # Helpers de integridade para renomear e excluir sons da config
                    def renomear_som_no_config(old_key, new_key):
                        c_config = load_alerts_config()
                        mappings = c_config.get('sound_mappings', {})
                        for event, sound in mappings.items():
                            if sound == old_key:
                                mappings[event] = new_key
                        for item in c_config.get('custom_alerts', []):
                            if item.get('sound') == old_key:
                                item['sound'] = new_key
                        save_alerts_config(c_config)

                    def remover_som_no_config(sound_key):
                        c_config = load_alerts_config()
                        mappings = c_config.get('sound_mappings', {})
                        for event, sound in mappings.items():
                            if sound == sound_key:
                                mappings[event] = 'info'
                        for item in c_config.get('custom_alerts', []):
                            if item.get('sound') == sound_key:
                                item['sound'] = 'info'
                        save_alerts_config(c_config)

                    # Diálogos para renomear som
                    with ui.dialog() as rename_sound_dialog:
                        with theme.card_base().classes('q-pa-md').style('min-width: 350px;'):
                            with ui.column().classes('w-full gap-4'):
                                ui.label('✏️ Renomear Arquivo de Som').classes('text-lg font-bold text-white')
                                ui.separator().style('background-color: rgba(255,255,255,0.1);')
                                
                                orig_sound_name = ui.label('').classes('hidden')
                                input_new_sound_name = ui.input('Nome do Arquivo (sem .mp3)', placeholder='Ex: alerta_especial').props('dark dense outlined').classes('w-full')
                                
                                def confirmar_renomeacao():
                                    old_filename = orig_sound_name.text
                                    new_name = input_new_sound_name.value.strip().lower()
                                    new_name = "".join([c for c in new_name if c.isalpha() or c.isdigit() or c in ('_', '-')])
                                    if not new_name:
                                        ui.notify('Nome de arquivo inválido!', color='red')
                                        return
                                    new_filename = new_name + '.mp3'
                                    
                                    if new_filename in ('bell_single.mp3', 'bell_double.mp3'):
                                        ui.notify('Não é permitido usar nomes de arquivos de sistema.', color='red')
                                        return
                                        
                                    db_conn = get_admin_db_connection() or get_db_connection()
                                    if not db_conn:
                                        ui.notify('Sem conexão com o banco de dados.', color='red')
                                        return
                                        
                                    try:
                                        existing = db_conn.storage.from_('sons').list()
                                        if any(item.get('name') == new_filename for item in existing):
                                            ui.notify('Já existe um arquivo de som com este nome.', color='red')
                                            return
                                            
                                        db_conn.storage.from_('sons').move(old_filename, new_filename)
                                        old_key = old_filename[:-4]
                                        new_key = new_name
                                        renomear_som_no_config(old_key, new_key)
                                        
                                        ui.notify('Arquivo renomeado com sucesso!', color='success')
                                        rename_sound_dialog.close()
                                        atualizar_opcoes_de_sons()
                                        render_sound_files_list.refresh()
                                        render_custom_alerts_list.refresh()
                                    except Exception as ex:
                                        ui.notify(f'Erro ao renomear: {ex}', color='red')
                                        
                                with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                                    ui.button('Cancelar', on_click=rename_sound_dialog.close).props('outline dense color=grey')
                                    ui.button('Confirmar', on_click=confirmar_renomeacao).props('unelevated dense color=primary')

                    @ui.refreshable
                    def render_sound_files_list():
                        custom_files = []
                        db_conn = get_admin_db_connection() or get_db_connection()
                        if db_conn:
                            try:
                                res = db_conn.storage.from_('sons').list()
                                if res:
                                    for item in res:
                                        f = item.get('name')
                                        if f and f.lower().endswith('.mp3') and f.lower() not in ('bell_single.mp3', 'bell_double.mp3'):
                                            custom_files.append(f)
                            except Exception as e:
                                print(f"[CONFIG] Erro ao listar arquivos de som: {e}")
                                
                        with ui.column().classes('w-full gap-2 border border-white/5 q-pa-sm rounded bg-black/10').style('max-height: 200px; overflow-y: auto;'):
                            if not custom_files:
                                ui.label('Sem arquivos de som customizados (apenas sons de sistema ativos).').classes('text-xs italic text-grey-5 text-center w-full py-2')
                            else:
                                for f in sorted(custom_files):
                                    with ui.row().classes('w-full justify-between items-center no-wrap py-1 border-b border-white/5'):
                                        ui.label(f).classes('text-xs text-white truncate col-grow')
                                        
                                        def make_play_cb(filename=f):
                                            return lambda: testar_som(filename[:-4])
                                            
                                        def abrir_renomear(filename=f):
                                            orig_sound_name.set_text(filename)
                                            input_new_sound_name.value = filename[:-4]
                                            rename_sound_dialog.open()
                                            
                                        def excluir_som(filename=f):
                                            async def processar_exclusao():
                                                db_conn = get_admin_db_connection() or get_db_connection()
                                                if not db_conn:
                                                    ui.notify('Sem conexão com o banco de dados.', color='red')
                                                    return
                                                try:
                                                    db_conn.storage.from_('sons').remove([filename])
                                                    remover_som_no_config(filename[:-4])
                                                    ui.notify(f'Som "{filename}" excluído com sucesso!', color='success')
                                                    atualizar_opcoes_de_sons()
                                                    render_sound_files_list.refresh()
                                                    render_custom_alerts_list.refresh()
                                                except Exception as ex:
                                                    ui.notify(f'Erro ao excluir: {ex}', color='red')
                                                    
                                            confirm_dialog = ui.dialog()
                                            with confirm_dialog, theme.card_base().classes('q-pa-md'):
                                                with ui.column().classes('items-center text-center gap-4'):
                                                    ui.icon('warning', size='3rem', color='red')
                                                    ui.label(f'Deseja excluir definitivamente o arquivo "{filename}"?').classes('text-sm font-bold text-white')
                                                    with ui.row().classes('gap-2 q-mt-md'):
                                                        ui.button('Cancelar', on_click=confirm_dialog.close).props('outline dense color=grey')
                                                        ui.button('Excluir', on_click=lambda: [confirm_dialog.close(), processar_exclusao()]).props('unelevated dense color=red')
                                            confirm_dialog.open()
                                        
                                        with ui.row().classes('items-center gap-1'):
                                            ui.button(icon='play_arrow', on_click=make_play_cb(f)).props('flat round dense color=primary').classes('text-xs')
                                            ui.button(icon='edit', on_click=lambda _, fn=f: abrir_renomear(fn)).props('flat round dense color=primary').classes('text-xs')
                                            ui.button(icon='delete', on_click=lambda _, fn=f: excluir_som(fn)).props('flat round dense color=red').classes('text-xs')
                                            
                    render_sound_files_list()

        # --- ABA 4: MODELOS DE MENSAGENS DOS MODAIS ---
        with ui.tab_panel('templates').classes('bg-transparent q-pa-none gap-6'):
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('chat', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Modelos de Mensagens (Modais)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Personalize o formato do texto exibido nos modais de alertas do Modo TV. Use {message} para indicar onde a mensagem dinâmica do sistema será inserida.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    template_inputs = {}
                    default_templates = alerts_config.get("message_templates", {})
                    
                    # Renderiza campos de texto para cada template existente
                    for key, val in default_templates.items():
                        with ui.row().classes('w-full items-center justify-between gap-2 border-b border-white/5 py-2'):
                            with ui.column().classes('gap-0 w-1/3'):
                                ui.label(key).classes('text-xs text-white font-bold')
                                ui.label('Exemplo: ' + val.replace('{message}', 'Texto do Alerta')).classes('text-[9px] text-grey-5')
                            
                            input_field = ui.input(
                                value=val
                            ).props('dark dense outlined').classes('text-xs col-grow')
                            template_inputs[key] = input_field

        # --- ABA 5: NOTIFICAÇÕES TELEGRAM ---
        with ui.tab_panel('telegram').classes('bg-transparent q-pa-none gap-6'):
            with ui.column().classes('w-full gap-6'):
                
                # 1. Minhas Preferências (Painel Pessoal)
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('person', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Minhas Preferências de Notificação').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        logged_in_user = app.storage.user.get('user_data', {})
                        u_id = logged_in_user.get('id')
                        u_name = logged_in_user.get('nome', 'Operador').upper()
                        
                        if not u_id:
                            ui.label('Efetue o login para gerenciar suas preferências.').classes('text-grey italic text-xs')
                        else:
                            from notifications_manager import get_user_preferences, save_user_preferences
                            user_prefs = get_user_preferences(u_id)
                            
                            ui.label(f'Operador Logado: {u_name}').classes('text-xs text-amber-5 font-bold')
                            
                            silence_switch = ui.switch(
                                '🔇 Silenciar todas as notificações', 
                                value=user_prefs.get('silence_all', False)
                            ).props('dark')
                            
                            with ui.column().classes('w-full gap-2 q-pl-md border-l border-white/5') as sub_pref_container:
                                pref_new_user = ui.checkbox('🔔 Nova Solicitação de Cadastro', value=user_prefs.get('notify_new_user', True)).props('dark')
                                pref_aviso = ui.checkbox('📢 Aviso Crítico na TV', value=user_prefs.get('notify_aviso', True)).props('dark')
                                pref_saude = ui.checkbox('🏥 Internação Hospitalar (Saúde)', value=user_prefs.get('notify_saude', True)).props('dark')
                                pref_escala = ui.checkbox('👮 Alertas de Escala Diária', value=user_prefs.get('notify_escala', True)).props('dark')
                            
                            # Desabilita as opções finas se "Silenciar todas" estiver ativo
                            pref_new_user.bind_enabled_from(silence_switch, 'value', backward=lambda x: not x)
                            pref_aviso.bind_enabled_from(silence_switch, 'value', backward=lambda x: not x)
                            pref_saude.bind_enabled_from(silence_switch, 'value', backward=lambda x: not x)
                            pref_escala.bind_enabled_from(silence_switch, 'value', backward=lambda x: not x)
                            
                            def salvar_minhas_prefs():
                                new_prefs = {
                                    "silence_all": bool(silence_switch.value),
                                    "notify_new_user": bool(pref_new_user.value),
                                    "notify_aviso": bool(pref_aviso.value),
                                    "notify_saude": bool(pref_saude.value),
                                    "notify_escala": bool(pref_escala.value)
                                }
                                save_user_preferences(u_id, new_prefs)
                                ui.notify('Preferências salvas com sucesso!', color='positive')
                                
                            silence_switch.on('change', salvar_minhas_prefs)
                            pref_new_user.on('change', salvar_minhas_prefs)
                            pref_aviso.on('change', salvar_minhas_prefs)
                            pref_saude.on('change', salvar_minhas_prefs)
                            pref_escala.on('change', salvar_minhas_prefs)
                            
                # 2. Configuração Global (Apenas para Admins e Supervisores)
                role = logged_in_user.get('role', 'compel')
                if role in ('admin', 'supervisor'):
                    with theme.card_base().classes('w-full q-pa-md'):
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('admin_panel_settings', size='2rem').style(f'color: {THEME["accent"]}')
                                ui.label('Configuração Global de Notificações').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                            ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                            
                            ui.label('Gerencie quais notificações cada militar vinculado receberá no Telegram.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                            
                            @ui.refreshable
                            def render_global_preferences_table():
                                db_c = get_db_connection()
                                users = []
                                if db_c:
                                    try:
                                        res = db_c.table('Users').select('*').execute()
                                        users = res.data or []
                                    except Exception:
                                        pass
                                if not users:
                                    # Mock
                                    users = [
                                        {'id': '1', 'username': 'admin', 'nome': 'CALAÇA', 'role': 'admin', 'telegram_id': '123456789'},
                                        {'id': '2', 'username': 'supervisor', 'nome': 'AMANDA', 'role': 'supervisor', 'telegram_id': '987654321'},
                                    ]
                                    
                                from notifications_manager import get_user_preferences, save_user_preferences
                                
                                with ui.column().classes('w-full gap-3 max-h-[300px] overflow-y-auto q-pr-xs'):
                                    for u in users:
                                        user_tg = u.get('telegram_id') or ''
                                        user_lbl = f"{u['nome'].upper()} ({u['role'].upper()})"
                                        
                                        with ui.row().classes('w-full items-center justify-between border-b border-white/5 py-2 hover:bg-white/5 px-2 rounded'):
                                            with ui.column().classes('gap-0 w-[160px]'):
                                                ui.label(user_lbl).classes('text-white text-xs font-bold')
                                                if user_tg:
                                                    ui.label(f'ID: {user_tg}').classes('text-[10px] text-cyan-5 font-mono')
                                                else:
                                                    ui.label('Não Vinculado').classes('text-[10px] text-grey-6 italic')
                                                    
                                            if user_tg:
                                                u_prefs = get_user_preferences(u['id'])
                                                # Checkboxes
                                                with ui.row().classes('gap-4 items-center'):
                                                    cb_silence = ui.checkbox('Silenciar', value=u_prefs.get('silence_all', False)).props('dark dense')
                                                    
                                                    cb_nu = ui.checkbox('Novo Cadastro', value=u_prefs.get('notify_new_user', True)).props('dark dense')
                                                    cb_av = ui.checkbox('Aviso TV', value=u_prefs.get('notify_aviso', True)).props('dark dense')
                                                    cb_sd = ui.checkbox('Saúde', value=u_prefs.get('notify_saude', True)).props('dark dense')
                                                    cb_es = ui.checkbox('Escala', value=u_prefs.get('notify_escala', True)).props('dark dense')
                                                    
                                                    # Bindings
                                                    cb_nu.bind_enabled_from(cb_silence, 'value', backward=lambda x: not x)
                                                    cb_av.bind_enabled_from(cb_silence, 'value', backward=lambda x: not x)
                                                    cb_sd.bind_enabled_from(cb_silence, 'value', backward=lambda x: not x)
                                                    cb_es.bind_enabled_from(cb_silence, 'value', backward=lambda x: not x)
                                                    
                                                    def make_change_handler(user_id=u['id'], cb_s=cb_silence, cb_n=cb_nu, cb_a=cb_av, cb_h=cb_sd, cb_e=cb_es):
                                                        def on_change():
                                                            n_prefs = {
                                                                "silence_all": bool(cb_s.value),
                                                                "notify_new_user": bool(cb_n.value),
                                                                "notify_aviso": bool(cb_a.value),
                                                                "notify_saude": bool(cb_h.value),
                                                                "notify_escala": bool(cb_e.value)
                                                            }
                                                            save_user_preferences(user_id, n_prefs)
                                                        return on_change
                                                        
                                                    handler = make_change_handler()
                                                    cb_silence.on('change', handler)
                                                    cb_nu.on('change', handler)
                                                    cb_av.on('change', handler)
                                                    cb_sd.on('change', handler)
                                                    cb_es.on('change', handler)
                                            else:
                                                ui.label('Associe o Telegram ID no painel de operadores primeiro.').classes('text-[10px] text-grey italic')
                                                
                            render_global_preferences_table()
                            
                # 3. Envio de Mensagem Privada Nominal (Chat Direto)
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('send', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Enviar Notificação Nominal Privada').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        ui.label('Selecione um militar para enviar uma notificação personalizada privada via bot do Telegram.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                        
                        db_c = get_db_connection()
                        users_with_tg = []
                        if db_c:
                            try:
                                res = db_c.table('Users').select('*').execute()
                                if res.data:
                                    users_with_tg = [u for u in res.data if u.get('telegram_id')]
                            except Exception:
                                pass
                                
                        opcoes_envio = {
                            str(u['telegram_id']): f"{u['nome'].upper()} (ID: {u['telegram_id']})"
                            for u in users_with_tg
                        } if users_with_tg else {"123456789": "CALAÇA (Mock)"}
                        
                        sel_militar_envio = ui.select(opcoes_envio, label='Selecione o Militar').props('dark dense outlined w-full').classes('w-full')
                        txt_mensagem_privada = ui.input('Mensagem do Alerta', placeholder='Ex: Favor comparecer à Comissaria urgente.').props('dark dense outlined w-full').classes('w-full')
                        
                        def enviar_privada():
                            tg_id = sel_militar_envio.value
                            msg_txt = txt_mensagem_privada.value.strip()
                            if not tg_id or not msg_txt:
                                ui.notify('Selecione o militar e digite a mensagem!', color='warning')
                                return
                                
                            try:
                                from notifications_manager import send_notification_to_user
                                import asyncio
                                
                                asyncio.create_task(send_notification_to_user(tg_id, f"✉️ **Mensagem Direta — SisGAB**\n\n{msg_txt}"))
                                ui.notify('Mensagem enviada com sucesso no privado!', color='positive')
                                txt_mensagem_privada.value = ''
                            except Exception as ex:
                                ui.notify(f'Erro ao enviar: {ex}', color='red')
                                
                        ui.button(
                            '⚡ Enviar Mensagem Direta', on_click=enviar_privada
                        ).props('unelevated no-caps').style(
                            f'background:{THEME["accent"]}; color:#000; font-weight:700;'
                        ).classes('w-full')

                # 4. Solicitações de Acesso Pendentes (Apenas para Admins e Supervisores)
                if role in ('admin', 'supervisor'):
                    with theme.card_base().classes('w-full q-pa-md q-mt-4'):
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('assignment_ind', size='2rem').style(f'color: {THEME["accent"]}')
                                ui.label('Solicitações de Acesso Pendentes').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                            ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                            
                            @ui.refreshable
                            def render_pending_requests_tab():
                                db_c = get_db_connection()
                                reqs = []
                                if db_c:
                                    try:
                                        res_req = db_c.table('RegistrationRequests').select('*').eq('status', 'pending').execute()
                                        reqs = res_req.data or []
                                    except Exception as e:
                                        print(f"[CONFIG REQ ERR] {e}")
                                
                                if not reqs:
                                    ui.label('Não há solicitações pendentes no momento.').classes('italic text-xs text-grey-5')
                                else:
                                    with ui.column().classes('w-full gap-3'):
                                        for r in reqs:
                                            with ui.row().classes('w-full items-center justify-between border-b border-white/5 py-2 hover:bg-white/5 px-2 rounded'):
                                                with ui.column().classes('gap-0'):
                                                    ui.label(r.get('nome_completo', '').upper()).classes('text-white text-xs font-bold')
                                                    ui.label(f"Email: {r.get('email', '')} | Guerra: {r.get('nome_guerra', '').upper()}").classes('text-[10px] text-grey-5')
                                                
                                                # Ações rápidas
                                                with ui.row().classes('gap-2 items-center'):
                                                    def make_approve_handler(req_id=r['id'], req_email=r['email'], req_guerra=r['nome_guerra']):
                                                        def approve():
                                                            try:
                                                                db_c.table('RegistrationRequests').update({'status': 'approved'}).eq('id', req_id).execute()
                                                                db_c.table('Users').upsert({
                                                                    'id': req_id,
                                                                    'username': req_email.split('@')[0],
                                                                    'nome': req_guerra.upper(),
                                                                    'role': 'compel'
                                                                }, on_conflict='id').execute()
                                                                try:
                                                                    from database import confirm_supabase_user
                                                                    confirm_supabase_user(req_id)
                                                                except Exception as conf_err:
                                                                    print(f"[CONFIRM ERR] {conf_err}")
                                                                
                                                                # Notifica o usuário aprovado via Telegram
                                                                try:
                                                                    user_res = db_c.table('Users').select('telegram_id, nome').eq('id', req_id).execute()
                                                                    if user_res.data and user_res.data[0].get('telegram_id'):
                                                                        from notifications_manager import notify_telegram
                                                                        tg_id = str(user_res.data[0]['telegram_id'])
                                                                        nome_aprovado = user_res.data[0].get('nome', req_guerra).upper()
                                                                        msg_tg = (
                                                                            f"✅ *Acesso ao SisGAB Aprovado!*\n\n"
                                                                            f"Olá, *{nome_aprovado}*! Seu acesso foi aprovado pelo administrador.\n\n"
                                                                            f"🔑 Papel atribuído: `compel`\n"
                                                                            f"📱 Você já pode usar o bot normalmente.\n"
                                                                            f"🌐 Acesse também o sistema web para operações avançadas."
                                                                        )
                                                                        notify_telegram(msg_tg, "system", specific_user_id=req_id)
                                                                except Exception as notif_err:
                                                                    print(f"[CONFIG NOTIFY APPROVED ERR] {notif_err}")

                                                                ui.notify('Solicitação aprovada!', color='success')
                                                                render_pending_requests_tab.refresh()
                                                            except Exception as ex:
                                                                ui.notify(f'Erro ao aprovar: {ex}', color='red')
                                                        return approve
                                                        
                                                    def make_reject_handler(req_id=r['id']):
                                                        def reject():
                                                            try:
                                                                db_c.table('RegistrationRequests').update({'status': 'rejected'}).eq('id', req_id).execute()
                                                                ui.notify('Solicitação rejeitada.', color='warning')
                                                                render_pending_requests_tab.refresh()
                                                            except Exception as ex:
                                                                ui.notify(f'Erro ao rejeitar: {ex}', color='red')
                                                        return reject
                                                    
                                                    ui.button('Rejeitar', on_click=make_reject_handler()).props('outline dense color=red').classes('text-xs')
                                                    ui.button('Aprovar', on_click=make_approve_handler()).props('unelevated dense color=green').classes('text-xs text-white')
                            
                            render_pending_requests_tab()

        # --- ABA 6: CONFIGURAÇÃO DE VOZ (TTS) ---
        with ui.tab_panel('tts').classes('bg-transparent q-pa-none gap-6'):
            with ui.column().classes('w-full gap-6'):
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('record_voice_over', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração de Text-To-Speech (TTS)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        ui.label('Gerencie o motor de voz utilizado para sintetizar mensagens nos painéis e TVs.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                        
                        tts_engines_opts = {
                            'basic': 'Basic SpeechSynthesis (Navegador / Offline)',
                            'google': 'Google Tradutor (Online / Gratuito)',
                            'elevenlabs': 'ElevenLabs (Neural / API Key)',
                            'piper': 'Piper TTS (Local / Executável)'
                        }
                        input_tts_engine = ui.select(tts_engines_opts, label='Motor TTS Ativo', value=current_configs.get('tts_engine', 'basic')).props('dark dense outlined w-full').classes('w-full')
                        
                # Basic SpeechSynthesis Config Card
                with theme.card_base().classes('w-full q-pa-md') as basic_card:
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('volume_up', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração do SpeechSynthesis (Navegador)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        loading_label = ui.label('Carregando vozes do navegador...').classes('text-xs text-amber-5')
                        
                        current_voice_val = current_configs.get('basic_tts_voice', '')
                        input_basic_tts_voice = ui.select(
                            options={current_voice_val: current_voice_val} if current_voice_val else {'': 'Nenhuma voz configurada (será detectada automaticamente)'},
                            label='Voz Masculina/Feminina do Navegador',
                            value=current_voice_val
                        ).props('dark dense outlined w-full').classes('w-full')
                        
                # Google Translate Config Card
                with theme.card_base().classes('w-full q-pa-md') as google_card:
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('g_translate', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração do Google Translate').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        input_google_tts_lang = ui.select(
                            options={
                                'pt-br': 'Português (Brasil)',
                                'pt-pt': 'Português (Portugal)',
                                'en': 'Inglês (Estados Unidos)',
                                'es': 'Espanhol',
                                'fr': 'Francês',
                                'it': 'Italiano'
                            },
                            label='Idioma/Voz do Google Translate',
                            value=current_configs.get('google_tts_lang', 'pt-br')
                        ).props('dark dense outlined w-full').classes('w-full')
                        
                # ElevenLabs Config Card
                with theme.card_base().classes('w-full q-pa-md') as elevenlabs_card:
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('api', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração do ElevenLabs').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        input_elevenlabs_api_key = ui.input('ElevenLabs API Key', value=current_configs.get('elevenlabs_api_key', ''), password=True, password_toggle_button=True).props('dark dense outlined w-full autocomplete=new-password').classes('w-full')
                        input_elevenlabs_voice_id = ui.input('Voice ID', value=current_configs.get('elevenlabs_voice_id', 'N2lVS1w4EtoT3dr4eOWO')).props('dark dense outlined w-full').classes('w-full')
                
                # Piper Config Card
                with theme.card_base().classes('w-full q-pa-md') as piper_card:
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('terminal', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração do Piper (TTS Local)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        input_tts_piper_path = ui.input('Caminho para o piper.exe', value=current_configs.get('tts_piper_path', 'piper.exe')).props('dark dense outlined w-full').classes('w-full')
                        input_tts_piper_voice = ui.input('Modelo de voz (.onnx)', value=current_configs.get('tts_piper_voice', 'pt_BR-fabricio-medium')).props('dark dense outlined w-full').classes('w-full')
                        
                google_card.bind_visibility_from(input_tts_engine, 'value', backward=lambda x: x == 'google')
                basic_card.bind_visibility_from(input_tts_engine, 'value', backward=lambda x: x == 'basic')
                elevenlabs_card.bind_visibility_from(input_tts_engine, 'value', backward=lambda x: x == 'elevenlabs')
                piper_card.bind_visibility_from(input_tts_engine, 'value', backward=lambda x: x == 'piper')

                # Google Gemini AI Config Card
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('psychology', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Configuração da Inteligência Artificial (Google Gemini)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        input_google_api_key = ui.input(
                            'Chave de API do Gemini (GOOGLE_API_KEY)',
                            value=current_configs.get('google_api_key', ''),
                            password=True,
                            password_toggle_button=True
                        ).props('dark dense outlined w-full autocomplete=new-password').classes('w-full')
                        ui.label('Usada para gerar pareceres clínicos no Módulo de Saúde, reescrever notificações na voz do JARVIS e suporte a decisões.').classes('text-[10px]').style(f'color: {THEME["text_dim"]}')

                        import ai_helper
                        modelos_disponiveis = ai_helper.get_available_gemini_models()
                        modelo_atual = current_configs.get('gemini_model_name', 'gemini-2.0-flash')
                        if modelo_atual not in modelos_disponiveis:
                            modelos_disponiveis[modelo_atual] = f"{modelo_atual} (Salvo)"

                        with ui.row().classes('w-full items-center gap-2'):
                            input_gemini_model = ui.select(
                                label='Modelo do Gemini para ser Usado',
                                options=modelos_disponiveis,
                                value=modelo_atual
                            ).props('dark dense outlined use-input new-value-mode=add-unique').classes('flex-grow')
                            
                            async def atualizar_modelos_click():
                                import google.generativeai as genai
                                api_key_temp = input_google_api_key.value.strip()
                                if api_key_temp:
                                    ai_helper.reset_api_cache()
                                    genai.configure(api_key=api_key_temp)
                                novos_modelos = await run.io_bound(ai_helper.get_available_gemini_models)
                                sel_val = input_gemini_model.value
                                if sel_val and sel_val not in novos_modelos:
                                    novos_modelos[sel_val] = f"{sel_val} (Salvo)"
                                input_gemini_model.options = novos_modelos
                                input_gemini_model.update()
                                ui.notify('Lista de modelos do Gemini atualizada!', color='success')

                            ui.button(icon='sync', on_click=atualizar_modelos_click).props('unelevated color=cyan-10 dense').style('height: 40px; width: 40px; margin-top: 8px;').tooltip('Buscar e atualizar lista de modelos do Gemini')

                # Card de Teste de TTS
                with theme.card_base().classes('w-full q-pa-md'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('hearing', size='2rem').style(f'color: {THEME["accent"]}')
                            ui.label('Testar Sintetização de Voz (TTS)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                        ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                        
                        input_teste_tts = ui.input('Texto de Teste', value='Atenção, teste de voz do sistema. O motor de voz está funcionando perfeitamente.').props('dark dense outlined w-full').classes('w-full')
                        
                        ui.button(
                            'Testar Reprodução de Voz', 
                            on_click=lambda: testar_tts(
                                input_teste_tts.value,
                                input_tts_engine.value,
                                input_elevenlabs_api_key.value,
                                input_elevenlabs_voice_id.value,
                                input_tts_piper_path.value,
                                input_tts_piper_voice.value,
                                input_google_tts_lang.value,
                                input_basic_tts_voice.value
                            )
                        ).props('unelevated color=amber-9 text-color=black dense w-full').classes('bold q-mt-md')

                async def load_voices():
                    try:
                        voices_data = await ui.run_javascript('''
                            new Promise((resolve) => {
                                let getList = () => {
                                    let voices = window.speechSynthesis.getVoices();
                                    return voices.map(v => ({ name: v.name, lang: v.lang }));
                                };
                                let list = getList();
                                if (list.length > 0) {
                                    resolve(list);
                                } else {
                                    window.speechSynthesis.onvoiceschanged = () => {
                                        resolve(getList());
                                    };
                                    setTimeout(() => resolve(getList()), 1000);
                                }
                            })
                        ''', timeout=5.0)
                        if voices_data:
                            opts = {}
                            pt_voices = []
                            other_voices = []
                            for v in voices_data:
                                name = v['name']
                                lang = v['lang']
                                lower_name = name.lower()
                                lower_lang = lang.lower()
                                
                                gender = "Feminino" if any(w in lower_name for w in ['female', 'maria', 'zira', 'google português', 'heloisa', 'luciana', 'vitoria', 'samantha', 'sara', 'vitória', 'francisca', 'joana']) else "Masculino/Indefinido"
                                if any(w in lower_name for w in ['male', 'daniel', 'antonio', 'antónio', 'felipe', 'valerio', 'valério', 'fabio', 'fábio']):
                                    gender = "Masculino"
                                
                                display_text = f"{name} ({lang} - {gender})"
                                if 'pt' in lower_lang:
                                    pt_voices.append((name, display_text))
                                else:
                                    other_voices.append((name, display_text))
                            
                            all_opts = pt_voices + other_voices
                            opts = {name: display for name, display in all_opts}
                            
                            current_val = input_basic_tts_voice.value
                            input_basic_tts_voice.options = opts
                            if current_val in opts:
                                input_basic_tts_voice.value = current_val
                            elif pt_voices:
                                input_basic_tts_voice.value = pt_voices[0][0]
                            elif opts:
                                input_basic_tts_voice.value = list(opts.keys())[0]
                                
                            input_basic_tts_voice.update()
                            loading_label.text = f"{len(opts)} vozes disponíveis no navegador (priorizando Português)"
                            loading_label.style('color: #00e5ff;')
                        else:
                            loading_label.text = "Nenhuma voz de síntese encontrada no navegador."
                            loading_label.style('color: #ff1744;')
                    except Exception as e:
                        print(f"[VOICES LOAD ERROR] {e}", flush=True)
                        loading_label.text = "Erro ao carregar vozes do navegador local."
                        loading_label.style('color: #ff1744;')

                ui.timer(1.0, load_voices, once=True)



        # --- ABA 8: GERENCIAR PERMISSÕES ---
        with ui.tab_panel('permissoes').classes('bg-transparent q-pa-none gap-6'):
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('admin_panel_settings', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Gerenciar Permissões por Função').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Defina quais perfis (Cargos/Funções) têm acesso às operações do painel e do Telegram Bot.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    @ui.refreshable
                    def render_permissions_editor():
                        db_c = get_db_connection()
                        perms_data = []
                        if db_c:
                            try:
                                res = db_c.table('Permissions').select('*').execute()
                                perms_data = res.data if res.data else []
                            except Exception as e:
                                print(f"Erro ao carregar permissões: {e}")
                        
                        with ui.column().classes('w-full gap-4'):
                            if not perms_data:
                                ui.label('Nenhuma regra de permissão cadastrada no Supabase.').classes('text-xs italic text-grey-5 text-center w-full py-4')
                            else:
                                # Separar as permissões
                                general_perms = sorted([p for p in perms_data if not p['feature_key'].startswith('menu_')], key=lambda x: x.get('feature_name', x.get('description', x['feature_key'])))
                                menu_perms = sorted([p for p in perms_data if p['feature_key'].startswith('menu_')], key=lambda x: x.get('feature_name', x.get('description', x['feature_key'])))
                                
                                def render_permissions_group(title, subtitle, list_data):
                                    if not list_data:
                                        return
                                    with ui.column().classes('w-full gap-2 q-mb-md'):
                                        with ui.row().classes('items-center gap-2 q-mt-sm q-mb-xs'):
                                            ui.badge(text=title, color='cyan-9').classes('text-xs font-bold')
                                            ui.label(subtitle).classes('text-xs text-grey-5 italic')
                                        for p in list_data:
                                            f_key = p['feature_key']
                                            f_desc = p.get('feature_name', p.get('description', f_key))
                                            f_roles = [r.strip().lower() for r in str(p.get('allowed_roles', '')).split(',') if r.strip()]
                                            
                                            with ui.column().classes('w-full border border-white/5 q-pa-sm rounded bg-black/10 hover:bg-black/20 gap-2'):
                                                with ui.row().classes('w-full items-baseline justify-between no-wrap gap-2'):
                                                    ui.label(f_desc).classes('text-xs font-bold text-white')
                                                    ui.label(f_key).classes('text-[10px] text-grey-5 font-mono shrink-0')
                                                
                                                with ui.row().classes('w-full gap-4 items-center'):
                                                    roles_list = ['admin', 'oficial_gab', 'oficial', 'praca_gab', 'comsoc', 'comsoc_design', 'militar']
                                                    checkboxes = {}
                                                    for role in roles_list:
                                                        is_checked = role in f_roles
                                                        checkboxes[role] = ui.checkbox(role.upper(), value=is_checked).props('dark dense').classes('text-xs text-grey-3')
                                                    
                                                    def make_save_handler(key=f_key, cbs=checkboxes):
                                                        def save_perms():
                                                            selected_roles = [r for r, cb in cbs.items() if cb.value]
                                                            roles_str = ",".join(selected_roles)
                                                            db_u = get_db_connection()
                                                            if db_u:
                                                                try:
                                                                    db_u.table('Permissions').update({'allowed_roles': roles_str}).eq('feature_key', key).execute()
                                                                    ui.notify(f'Permissões para "{key}" atualizadas!', color='success')
                                                                    data_service.clear_cache()
                                                                except Exception as err:
                                                                    ui.notify(f'Erro ao salvar: {err}', color='red')
                                                            else:
                                                                ui.notify('Offline: Operação indisponível.', color='warning')
                                                        return save_perms
                                                    
                                                    ui.button('Aplicar', on_click=make_save_handler()).props('unelevated dense color=cyan-10 text-color=white no-caps text-xs').classes('ml-auto px-3')
                                
                                render_permissions_group('🛡️ OPERAÇÕES E REGRAS GERAIS', 'Permissões e capacidades dentro das telas do sistema e bot', general_perms)
                                render_permissions_group('📋 ACESSO AOS MENUS LATERAIS', 'Definição de quais menus de navegação aparecem para cada perfil', menu_perms)
                    
                    render_permissions_editor()

        # --- ABA 9: CÓPIAS DE SEGURANÇA (BACKUP) ---
        with ui.tab_panel('backups').classes('bg-transparent q-pa-none gap-6'):
            with theme.card_base().classes('w-full q-pa-md'):
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('save_alt', size='2rem').style(f'color: {THEME["accent"]}')
                        ui.label('Cópia de Segurança (Backup)').classes('text-lg font-bold').style(f'color: {THEME["text_main"]}')
                    ui.separator().style(f'background-color: rgba(0, 229, 255, 0.15);')
                    
                    ui.label('Gere e baixe uma cópia de segurança completa de todas as tabelas do seu banco de dados. Os dados serão consolidados em arquivos CSV individuais e compactados em um único arquivo ZIP diretamente no seu navegador.').classes('text-xs').style(f'color: {THEME["text_dim"]}')
                    
                    # Alerta informativo
                    with ui.row().classes('w-full items-center p-3 rounded-lg gap-2').style('background: rgba(0, 229, 255, 0.03); border: 1px solid rgba(0, 229, 255, 0.1);'):
                        ui.icon('info', color='primary', size='xs')
                        ui.label('As fotos em cache físico local não são incluídas neste arquivo ZIP para garantir rapidez de download. Os cadastros, pautas e logs serão totalmente preservados.').classes('text-[10px] col-grow').style(f'color: {THEME["text_dim"]}')
                    
                    async def trigger_full_backup():
                        backup_notification = ui.notification('Iniciando consolidação dos dados...', type='ongoing', spinner=True)
                        try:
                            import io
                            import zipfile
                            import pandas as pd
                            from datetime import datetime
                            from database import get_db_connection
                            
                            db_conn = get_db_connection()
                            if not db_conn:
                                ui.notify('Sem conexão com o banco de dados para gerar backup!', color='negative')
                                return
                                
                            # Lista de todas as tabelas importantes do ecossistema COMSOC/Gabinete para incluir no backup
                            tables_to_backup = [
                                'Config', 'Users', 'RegistrationRequests', 'Permissions',
                                'efetivo', 'demandas_comunicacao', 'demandas_historico_tramitacao',
                                'cautela_equipamentos', 'cautela_historico', 'brindes_estoque',
                                'brindes_movimentacao', 'processed_photos', 'photo_matches',
                                'comsoc_noticias', 'Ordens_Diarias'
                            ]
                            
                            # Cria o arquivo ZIP em memória
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for table in tables_to_backup:
                                    try:
                                        # Carrega os dados da tabela em lotes
                                        all_rows = []
                                        page_size = 1000
                                        page = 0
                                        while True:
                                            start = page * page_size
                                            end = start + page_size - 1
                                            res = db_conn.table(table).select('*').range(start, end).execute()
                                            if not res.data:
                                                break
                                            all_rows.extend(res.data)
                                            if len(res.data) < page_size:
                                                break
                                            page += 1
                                            
                                        if all_rows:
                                            df = pd.DataFrame(all_rows)
                                            # Converte para CSV em string
                                            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                                            # Escreve o CSV dentro do ZIP
                                            zip_file.writestr(f"{table}.csv", csv_data)
                                            print(f"[BACKUP] Tabela {table} adicionada ao backup. Total registros: {len(all_rows)}", flush=True)
                                    except Exception as tbl_err:
                                        print(f"[BACKUP ERROR] Falha ao exportar tabela {table}: {tbl_err}", flush=True)
                                        zip_file.writestr(f"{table}_error.txt", f"Falha ao exportar tabela {table}: {tbl_err}")
                                        
                                # Cria o manifesto do backup
                                manifesto_content = (
                                    f"MANIFESTO DE BACKUP - SISGAB\n"
                                    f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                                    f"Ambiente: Produção (Hugging Face Spaces)\n"
                                    f"Tabelas Exportadas: {', '.join(tables_to_backup)}\n"
                                )
                                zip_file.writestr("manifesto.txt", manifesto_content)
                                
                            zip_buffer.seek(0)
                            zip_bytes = zip_buffer.getvalue()
                            
                            # Dispara o download automático no navegador do usuário
                            date_str = datetime.now().strftime('%d_%m_%Y_%H%M')
                            filename = f"backup_sisgab_{date_str}.zip"
                            ui.download(zip_bytes, filename=filename)
                            
                            ui.notify('Backup compilado e baixado com sucesso!', color='positive')
                        except Exception as backup_err:
                            ui.notify(f'Falha ao compilar backup: {backup_err}', color='negative')
                            print(f"[BACKUP ERROR] {backup_err}", flush=True)
                        finally:
                            backup_notification.dismiss()
                            
                    ui.button(
                        'Gerar e Baixar Cópia de Segurança', 
                        icon='download', 
                        on_click=trigger_full_backup
                    ).props('unelevated no-caps').classes('cyber-glow font-bold q-py-sm').style(f'background: {THEME["primary"]}; color: #0b0f19;')

    # --- AÇÕES ---
    # --- AÇÕES ---
    with ui.row().classes('w-full justify-end gap-3 q-mt-md'):
        def restaurar_padroes():
            input_polling.value = DEFAULT_CONFIGS['tempo_polling_tv']
            input_cabecalho_tv.value = DEFAULT_CONFIGS['cabecalho_tv_title']
            input_subcabecalho_tv.value = DEFAULT_CONFIGS['cabecalho_tv_subtitle']
            input_sunset_tv.value = DEFAULT_CONFIGS['cabecalho_tv_sunset_time']
            input_cargos_escala.value = DEFAULT_CONFIGS['cargos_escala_lista']
            input_unlock_code.value = DEFAULT_CONFIGS['codigo_desbloqueio_tv']
            input_alerta_tv.value = DEFAULT_CONFIGS['tempo_alerta_tv']
            input_telegram_token.value = DEFAULT_CONFIGS['telegram_bot_token']
            input_tts_engine.value = DEFAULT_CONFIGS['tts_engine']
            input_elevenlabs_api_key.value = DEFAULT_CONFIGS['elevenlabs_api_key']
            input_elevenlabs_voice_id.value = DEFAULT_CONFIGS['elevenlabs_voice_id']
            input_tts_piper_path.value = DEFAULT_CONFIGS['tts_piper_path']
            input_tts_piper_voice.value = DEFAULT_CONFIGS['tts_piper_voice']
            input_google_api_key.value = DEFAULT_CONFIGS.get('google_api_key', '')
            input_gemini_model.value = DEFAULT_CONFIGS.get('gemini_model_name', 'gemini-2.0-flash')
            
            # Reseta sons e templates para o padrão
            save_alerts_config(DEFAULT_ALERTS_CONFIG)
            
            for key, val in DEFAULT_ALERTS_CONFIG.get('message_templates', {}).items():
                if key in template_inputs:
                    template_inputs[key].value = val
                    
            for key, val in DEFAULT_ALERTS_CONFIG.get('sound_mappings', {}).items():
                if key in sound_dropdowns:
                    sound_dropdowns[key].value = val
            
            render_custom_alerts_list.refresh()
            ui.notify('Padrões restaurados na tela. Salve para persistir.', color='info')

        async def salvar_configs():
            try:
                int(input_polling.value)
                float(input_alerta_tv.value)
            except ValueError:
                ui.notify('Os campos numéricos devem conter valores inteiros/decimais válidos.', color='red')
                return

            db_conn = get_admin_db_connection() or get_db_connection()
            
            novas_configs = [
                {'chave': 'tempo_polling_tv', 'valor': str(input_polling.value)},
                {'chave': 'cabecalho_tv_title', 'valor': str(input_cabecalho_tv.value)},
                {'chave': 'cabecalho_tv_subtitle', 'valor': str(input_subcabecalho_tv.value)},
                {'chave': 'cabecalho_tv_sunset_time', 'valor': str(input_sunset_tv.value)},
                {'chave': 'cargos_escala_lista', 'valor': str(input_cargos_escala.value)},
                {'chave': 'codigo_desbloqueio_tv', 'valor': str(input_unlock_code.value)},
                {'chave': 'tempo_alerta_tv', 'valor': str(input_alerta_tv.value)},
                {'chave': 'telegram_bot_token', 'valor': str(input_telegram_token.value)},
                {'chave': 'tts_engine', 'valor': str(input_tts_engine.value)},
                {'chave': 'google_tts_lang', 'valor': str(input_google_tts_lang.value)},
                {'chave': 'basic_tts_voice', 'valor': str(input_basic_tts_voice.value)},
                {'chave': 'elevenlabs_api_key', 'valor': str(input_elevenlabs_api_key.value)},
                {'chave': 'elevenlabs_voice_id', 'valor': str(input_elevenlabs_voice_id.value)},
                {'chave': 'tts_piper_path', 'valor': str(input_tts_piper_path.value)},
                {'chave': 'tts_piper_voice', 'valor': str(input_tts_piper_voice.value)},
                {'chave': 'google_api_key', 'valor': str(input_google_api_key.value)},
                {'chave': 'gemini_model_name', 'valor': str(input_gemini_model.value)}
            ]

            # Salva as configurações de som
            new_alerts_config = load_alerts_config()
            new_alerts_config['tv_alert_vocativo'] = input_tv_vocativo.value
            for key in sound_dropdowns:
                new_alerts_config['sound_mappings'][key] = sound_dropdowns[key]
                
            # Salva as sequências de som personalizadas
            new_alerts_config['custom_sequences'] = {}
            for key in custom_sequence_dropdowns:
                new_alerts_config['custom_sequences'][key] = custom_sequence_dropdowns[key]
                
            # Salva os templates customizados de mensagens
            new_alerts_config['message_templates'] = {}
            for key in template_inputs:
                new_alerts_config['message_templates'][key] = template_inputs[key].value
            
            save_alerts_config(new_alerts_config)

            if db_conn:
                try:
                    for item in novas_configs:
                        db_conn.table('Config').upsert(item, on_conflict='chave').execute()
                    ui.notify('Configurações salvas no Supabase com sucesso!', color='success')
                except Exception as err:
                    ui.notify(f'Erro ao salvar no Supabase: {err}. Salvando apenas localmente.', color='warning')
            else:
                ui.notify('Modo Offline: Configurações salvas temporariamente na sessão.', color='warning')

            data_service.clear_cache()
            import ai_helper
            ai_helper.reset_api_cache()

            try:
                import telegram_bot
                await telegram_bot.restart_bot()
            except Exception as bot_err:
                print(f"[CONFIG] Erro ao reiniciar bot: {bot_err}", flush=True)

        ui.button('Restaurar Padrões', on_click=restaurar_padroes).props('outline dense').style(f'color: {THEME["text_dim"]}; border-color: rgba(255, 255, 255, 0.2);')
        ui.button('Salvar Configurações', on_click=salvar_configs).props('unelevated dense').style(f'background: {THEME["primary"]}; color: #0b0f19; font-weight: bold;').classes('cyber-glow px-4')
