import React, { useState, useEffect } from 'react';
import {
  Settings,
  Volume2,
  Bell,
  HardDrive,
  CheckCircle2,
  Tv,
  Play,
  RotateCcw,
  Sparkles,
  Bot,
  Sliders,
  Shield,
  Key,
  Eye,
  EyeOff,
  ExternalLink,
  Mic,
  VolumeX,
  Radio,
  Check,
  AlertTriangle,
  RefreshCw,
  SlidersHorizontal,
  Cpu,
  Globe,
  Upload,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import {
  playNeuralSpeech,
  stopNeuralSpeech,
  getAvailablePortugueseVoices,
  NeuralVoiceOption,
} from '../../utils/neuralTTS';
import { generateGeminiContent } from '../../utils/geminiClient';

// Vozes Azure Neural 0800 da Microsoft
const AZURE_EDGE_VOICES = [
  {
    id: 'pt-BR-AntonioNeural',
    name: '👨 Antonio Neural (Tom Oficial JARVIS - Elegante & Encorpado)',
    style: 'Jarvis / Assistente Militar Britânico',
  },
  {
    id: 'pt-BR-FranciscaNeural',
    name: '👩 Francisca Neural (Tom Feminino Suave, Claro & Agradável)',
    style: 'Cerimonial & Avisos Suaves',
  },
  {
    id: 'pt-BR-ThalitaNeural',
    name: '👩 Thalita Neural (Tom Feminino Jovem & Comunicativo)',
    style: 'Comunicação Dinâmica',
  },
  {
    id: 'pt-BR-NicolauNeural',
    name: '👨 Nicolau Neural (Tom Masculino Solene & Maduro)',
    style: 'Pronunciamentos Solenes',
  },
];

// Vozes Padrão Gratuitas do Tier Free do ElevenLabs
const ELEVENLABS_FREE_PRESET_VOICES = [
  { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel (Feminina Calma & Suave - 100% Free)' },
  { id: 'ErXwobaYiN019PkySvjV', name: 'Antoni (Masculina Polida & Suave - 100% Free)' },
  { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella (Feminina Expressiva - 100% Free)' },
  { id: 'VR6AewLTigWG4xSOukaG', name: 'Arnold (Masculina Firme / Militar - 100% Free)' },
  { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam (Masculina Profunda - 100% Free)' },
  { id: 'MF3mGyEYCl7XYWbV9V6O', name: 'Elli (Feminina Jovem - 100% Free)' },
  { id: 'TxGEqnHWrfWFTfGW9XjX', name: 'Josh (Masculina Narrador - 100% Free)' },
];

export const SystemSettings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'voz' | 'jarvis' | 'alertas' | 'parametros'>('voz');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // Configurações Gerais
  const [configData, setConfigData] = useState({
    cabecalho_tv_title: 'GABINETE DO COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS',
    cabecalho_tv_subtitle: 'PAINEL TÁTICO DE COMUNICAÇÃO SOCIAL & DEMANDAS EM TEMPO REAL',
    tempo_polling_tv: '15',
    codigo_desbloqueio_tv: '1234',
    horario_alerta_pronto: '07:00',
    horario_alerta_aniversariantes: '07:30',
    notificar_demandas_telegram: true,
    notificar_pronto_telegram: true,
  });

  // Configurações de Voz & Notificação
  const [ttsEngine, setTtsEngine] = useState<'edge' | 'piper' | 'browser' | 'elevenlabs'>('edge');
  
  // Edge-TTS Azure
  const [selectedAzureVoice, setSelectedAzureVoice] = useState('pt-BR-AntonioNeural');
  const [azureRate, setAzureRate] = useState<number>(0);
  const [azurePitch, setAzurePitch] = useState<number>(0);
  const [testingAzure, setTestingAzure] = useState(false);

  // ElevenLabs
  const [elevenlabsKey, setElevenlabsKey] = useState('');
  const [elevenlabsVoiceId, setElevenlabsVoiceId] = useState('21m00Tcm4TlvDq8ikWAM');
  const [elevenlabsVoicesList, setElevenlabsVoicesList] = useState(ELEVENLABS_FREE_PRESET_VOICES);
  const [loadingElevenVoices, setLoadingElevenVoices] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [testingElevenLabs, setTestingElevenLabs] = useState(false);

  // Vozes Nativas do Navegador
  const [browserVoices, setBrowserVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedBrowserVoice, setSelectedBrowserVoice] = useState<string>('');
  const [voiceRate, setVoiceRate] = useState<number>(1.0);
  const [voicePitch, setVoicePitch] = useState<number>(1.0);
  const [testingNativeVoice, setTestingNativeVoice] = useState(false);

  // Piper Local
  const [testingPiper, setTestingPiper] = useState(false);

  // Testes
  const [testVoiceText, setTestVoiceText] = useState('Atenção Gabinete. Nova pauta operacional registrada no SisGAB.');

  // Configurações do JARVIS
  const [jarvisConfig, setJarvisConfig] = useState({
    temperament: 'stark_british',
    vocative: 'Senhor',
    voiceEngine: 'edge_antonio',
    azureVoice: 'pt-BR-AntonioNeural',
    voiceRate: 1.0,
    customInstructions: 'Você é o JARVIS do Gabinete do CGCFN. Tom conversacional, refinado, inteligente, empático e prestativo.',
  });
  const [geminiKey, setGeminiKey] = useState('');
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [testingGemini, setTestingGemini] = useState(false);
  const [testingJarvisVoice, setTestingJarvisVoice] = useState(false);

  // Configurações de Alertas Sonoros & Sinos
  const [voiceAlertsEnabled, setVoiceAlertsEnabled] = useState(true);
  const [nauticalBellEnabled, setNauticalBellEnabled] = useState(true);
  const [soundEffectsEnabled, setSoundEffectsEnabled] = useState(true);
  const [alertVocativo, setAlertVocativo] = useState('Atenção Gabinete');

  useEffect(() => {
    loadSettingsFromSupabase();
    loadBrowserVoicesList();
  }, []);

  const loadBrowserVoicesList = () => {
    const list = getAvailablePortugueseVoices();
    setBrowserVoices(list);
    if (list.length > 0 && !selectedBrowserVoice) {
      const francisca = list.find((v) => v.name.includes('Francisca') || v.name.includes('Female'));
      setSelectedBrowserVoice(francisca ? francisca.name : list[0].name);
    }
  };

  const loadSettingsFromSupabase = async () => {
    try {
      setLoading(true);
      const { data } = await supabase.from('config').select('*');

      if (data) {
        const findVal = (key: string, def: string) =>
          data.find((c) => c.chave === key)?.valor || def;

        setConfigData({
          cabecalho_tv_title: findVal('cabecalho_tv_title', configData.cabecalho_tv_title),
          cabecalho_tv_subtitle: findVal('cabecalho_tv_subtitle', configData.cabecalho_tv_subtitle),
          tempo_polling_tv: findVal('tempo_polling_tv', '15'),
          codigo_desbloqueio_tv: findVal('codigo_desbloqueio_tv', '1234'),
          horario_alerta_pronto: findVal('horario_alerta_pronto', '07:00'),
          horario_alerta_aniversariantes: findVal('horario_alerta_aniversariantes', '07:30'),
          notificar_demandas_telegram: findVal('notificar_demandas_telegram', 'true') === 'true',
          notificar_pronto_telegram: findVal('notificar_pronto_telegram', 'true') === 'true',
        });

        setTtsEngine((findVal('tts_engine', 'edge') as any) || 'edge');
        setSelectedAzureVoice(findVal('azure_voice_name', 'pt-BR-AntonioNeural'));
        setAzureRate(parseInt(findVal('azure_rate', '0')) || 0);
        setAzurePitch(parseInt(findVal('azure_pitch', '0')) || 0);

        setElevenlabsKey(findVal('elevenlabs_api_key', ''));
        setElevenlabsVoiceId(findVal('elevenlabs_voice_id', '21m00Tcm4TlvDq8ikWAM'));
        setSelectedBrowserVoice(findVal('native_voice_name', ''));
        setVoiceRate(parseFloat(findVal('voice_rate', '1.0')) || 1.0);
        setVoicePitch(parseFloat(findVal('voice_pitch', '1.0')) || 1.0);

        const jCfg = findVal('jarvis_config_json', '');
        if (jCfg) {
          try {
            setJarvisConfig((prev) => ({ ...prev, ...JSON.parse(jCfg) }));
          } catch (e) {}
        }
        setGeminiKey(findVal('gemini_api_key', '') || findVal('google_api_key', ''));

        setVoiceAlertsEnabled(findVal('voice_alerts_enabled', 'true') === 'true');
        setNauticalBellEnabled(findVal('nautical_bell_enabled', 'true') === 'true');
        setSoundEffectsEnabled(findVal('sound_effects_enabled', 'true') === 'true');
        setAlertVocativo(findVal('tv_alert_vocativo', 'Atenção Gabinete'));
      }
    } catch (err) {
      console.warn('Erro ao carregar configurações:', err);
    } finally {
      setLoading(false);
    }
  };

  // Buscar vozes da conta ElevenLabs
  const handleFetchElevenLabsAccountVoices = async () => {
    const key = elevenlabsKey.trim();
    if (!key) {
      toast.error('Insira a chave do ElevenLabs para buscar suas vozes.');
      return;
    }

    setLoadingElevenVoices(true);
    try {
      const userRes = await fetch('https://api.elevenlabs.io/v1/user/subscription', {
        headers: { 'xi-api-key': key },
      });
      if (userRes.ok) {
        const subData = await userRes.json();
        const used = subData.character_count || 0;
        const limit = subData.character_limit || 10000;
        const tier = subData.tier || 'free';
        toast.info(`📊 Plano ElevenLabs: ${tier.toUpperCase()} • Uso: ${used}/${limit} caracteres`);
      }

      const res = await fetch('https://api.elevenlabs.io/v1/voices', {
        headers: { 'xi-api-key': key },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || `Status HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.voices && data.voices.length > 0) {
        const mapped = data.voices.map((v: any) => ({
          id: v.voice_id,
          name: `${v.name} (${v.category === 'premade' ? 'Grátis' : v.category || 'Voz'})`,
          category: v.category,
        }));
        setElevenlabsVoicesList(mapped);
        if (mapped.length > 0) {
          setElevenlabsVoiceId(mapped[0].id);
        }
        toast.success(`🎉 ${mapped.length} vozes encontradas na sua conta ElevenLabs!`);
      } else {
        toast.info('Nenhuma voz encontrada. Mantendo as vozes gratuitas padrão.');
      }
    } catch (e: any) {
      toast.error(`Falha ao consultar ElevenLabs: ${e.message}`);
    } finally {
      setLoadingElevenVoices(false);
    }
  };

  // Salvar Todas as Configurações
  const handleSaveAll = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const itemsToUpsert = [
        { chave: 'cabecalho_tv_title', valor: configData.cabecalho_tv_title },
        { chave: 'cabecalho_tv_subtitle', valor: configData.cabecalho_tv_subtitle },
        { chave: 'tempo_polling_tv', valor: configData.tempo_polling_tv },
        { chave: 'codigo_desbloqueio_tv', valor: configData.codigo_desbloqueio_tv },
        { chave: 'horario_alerta_pronto', valor: configData.horario_alerta_pronto },
        { chave: 'horario_alerta_aniversariantes', valor: configData.horario_alerta_aniversariantes },
        { chave: 'notificar_demandas_telegram', valor: String(configData.notificar_demandas_telegram) },
        { chave: 'notificar_pronto_telegram', valor: String(configData.notificar_pronto_telegram) },
        { chave: 'tts_engine', valor: ttsEngine },
        { chave: 'azure_voice_name', valor: selectedAzureVoice },
        { chave: 'azure_rate', valor: String(azureRate) },
        { chave: 'azure_pitch', valor: String(azurePitch) },
        { chave: 'elevenlabs_api_key', valor: elevenlabsKey.trim() },
        { chave: 'elevenlabs_voice_id', valor: elevenlabsVoiceId },
        { chave: 'native_voice_name', valor: selectedBrowserVoice },
        { chave: 'voice_rate', valor: String(voiceRate) },
        { chave: 'voice_pitch', valor: String(voicePitch) },
        { chave: 'jarvis_config_json', valor: JSON.stringify(jarvisConfig) },
        { chave: 'gemini_api_key', valor: geminiKey.trim() },
        { chave: 'google_api_key', valor: geminiKey.trim() },
        { chave: 'voice_alerts_enabled', valor: String(voiceAlertsEnabled) },
        { chave: 'nautical_bell_enabled', valor: String(nauticalBellEnabled) },
        { chave: 'sound_effects_enabled', valor: String(soundEffectsEnabled) },
        { chave: 'tv_alert_vocativo', valor: alertVocativo },
      ];

      const { error } = await supabase.from('config').upsert(itemsToUpsert);
      if (error) throw error;

      if (geminiKey.trim()) {
        localStorage.setItem('sisgab_gemini_key', geminiKey.trim());
      }

      confetti({ particleCount: 50, spread: 50, origin: { y: 0.7 } });
      toast.success('Configurações salvas com sucesso!');
    } catch (err: any) {
      toast.error(`Erro ao salvar configurações: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  // 🧪 Teste 0: Microsoft Azure Neural 0800 (Edge-TTS)
  const handleTestAzureVoice = async () => {
    setTestingAzure(true);
    stopNeuralSpeech();

    try {
      const rateStr = `${azureRate >= 0 ? '+' : ''}${azureRate}%`;
      const pitchStr = `${azurePitch >= 0 ? '+' : ''}${azurePitch}Hz`;

      const response = await fetch('http://127.0.0.1:5005/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: testVoiceText,
          engine: 'edge',
          voice: selectedAzureVoice,
          rate: rateStr,
          pitch: pitchStr,
        }),
      });

      if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.onended = () => setTestingAzure(false);
        audio.onerror = () => setTestingAzure(false);
        await audio.play();
        toast.success(`🟢 Voz Azure Neural "${selectedAzureVoice}" reproduzida com 100% de realismo!`);
      } else {
        throw new Error('Servidor local retornou erro.');
      }
    } catch (e: any) {
      toast.error(`Erro no Azure TTS: ${e.message}`);
      setTestingAzure(false);
    }
  };

  // 🧪 Teste 1: Piper TTS Local (Voz Jarvis Faber Offline)
  const handleTestPiperLocal = async () => {
    setTestingPiper(true);
    stopNeuralSpeech();

    try {
      await playNeuralSpeech(
        testVoiceText,
        'piper_local',
        () => setTestingPiper(true),
        () => setTestingPiper(false)
      );
      toast.success('🟢 Voz do JARVIS sintetizada com sucesso pelo Piper TTS Local (100% Offline)!');
    } catch (e: any) {
      toast.error(`Erro no Piper Local: ${e.message}`);
      setTestingPiper(false);
    }
  };

  // 🧪 Teste 2: ElevenLabs
  const handleTestElevenLabsDirect = async () => {
    const key = elevenlabsKey.trim();
    if (!key) {
      toast.error('Informe a Chave de API do ElevenLabs para testar.');
      return;
    }

    setTestingElevenLabs(true);
    stopNeuralSpeech();

    try {
      let voiceToUse = elevenlabsVoiceId || '21m00Tcm4TlvDq8ikWAM';
      const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceToUse}`, {
        method: 'POST',
        headers: {
          'Accept': 'audio/mpeg',
          'Content-Type': 'application/json',
          'xi-api-key': key,
        },
        body: JSON.stringify({
          text: testVoiceText,
          model_id: 'eleven_multilingual_v2',
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        const detail = errJson.detail?.message || errJson.message || `Status HTTP ${response.status}`;
        throw new Error(detail);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      await audio.play();
      toast.success('🟢 ElevenLabs Conectado com Sucesso! Áudio de estúdio reproduzido.');
    } catch (e: any) {
      toast.error(`🔴 Falha no ElevenLabs: ${e.message}`);
    } finally {
      setTestingElevenLabs(false);
    }
  };

  // 🧪 Teste 3: Voz Nativa Selecionada do Navegador
  const handleTestNativeVoice = async () => {
    setTestingNativeVoice(true);
    stopNeuralSpeech();

    try {
      await playNeuralSpeech(
        testVoiceText,
        'system_natural',
        () => setTestingNativeVoice(true),
        () => setTestingNativeVoice(false),
        selectedBrowserVoice,
        voiceRate,
        voicePitch
      );
      toast.success(`🟢 Voz Nativa "${selectedBrowserVoice || 'Padrão'}" reproduzida com sucesso!`);
    } catch (e: any) {
      toast.error(`Erro ao reproduzir voz nativa: ${e.message}`);
      setTestingNativeVoice(false);
    }
  };

  // 🧪 Teste 4: Chave do Google Gemini
  const handleTestGeminiApi = async () => {
    const key = geminiKey.trim();
    if (!key) {
      toast.error('Informe a Chave de API do Gemini para testar.');
      return;
    }

    setTestingGemini(true);

    try {
      const reply = await generateGeminiContent(
        "Diga em uma frase curta: 'Conexão com a Inteligência Artificial Gemini realizada com 100% de sucesso.'",
        "Você é o assistente inteligente do Gabinete.",
        key
      );

      toast.success(`🟢 Conexão com Gemini Ativa e Respondendo!`, {
        description: `IA respondeu: "${reply}"`,
      });
    } catch (e: any) {
      toast.error(`🔴 Falha na Chave Gemini: ${e.message}`);
    } finally {
      setTestingGemini(false);
    }
  };

  // 🧪 Teste 5: Voz do JARVIS (Sincronizada com a Aba 1)
  const handleTestJarvisVoice = async () => {
    setTestingJarvisVoice(true);
    stopNeuralSpeech();

    const frase = `Olá! Sou o JARVIS. Sistemas do Gabinete CGCFN operando em prontidão e com total normalidade.`;

    try {
      if (ttsEngine === 'elevenlabs' && elevenlabsKey.trim()) {
        const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${elevenlabsVoiceId}`, {
          method: 'POST',
          headers: {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': elevenlabsKey.trim(),
          },
          body: JSON.stringify({
            text: frase,
            model_id: 'eleven_multilingual_v2',
          }),
        });

        if (response.ok) {
          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audio.onended = () => setTestingJarvisVoice(false);
          audio.onerror = () => setTestingJarvisVoice(false);
          await audio.play();
          toast.success('🟢 Voz do JARVIS (ElevenLabs) reproduzida!');
          return;
        }
      }

      const mode: NeuralVoiceOption =
        ttsEngine === 'piper'
          ? 'piper_local'
          : ttsEngine === 'browser'
          ? 'system_natural'
          : selectedAzureVoice.includes('Francisca')
          ? 'edge_francisca'
          : 'edge_antonio';

      await playNeuralSpeech(
        frase,
        mode,
        () => setTestingJarvisVoice(true),
        () => setTestingJarvisVoice(false),
        selectedBrowserVoice,
        1.0,
        1.0
      );
      toast.success('🟢 Voz do JARVIS (Sincronizada com Aba 1) reproduzida com sucesso!');
    } catch (e: any) {
      toast.error(`Erro ao testar voz: ${e.message}`);
      setTestingJarvisVoice(false);
    }
  };

  // Teste do Sino Náutico
  const playTestBell = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 1.2);

      gain.gain.setValueAtTime(0.4, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 1.2);
      toast.success('🔔 Sino náutico reproduzido com sucesso!');
    } catch (e) {
      toast.info('🔔 Badaladas navais ativadas');
    }
  };

  return (
    <form onSubmit={handleSaveAll} className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* ── HEADER SUPERIOR ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
              Painel de Controle
            </span>
            <span className="text-slate-400 text-xs">• Sistema & IA</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1 flex items-center gap-3">
            <Settings className="w-8 h-8 text-[#c5a059]" />
            <span>Configurações, Voz IA & Parâmetros</span>
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm">
            Gerencie as integrações com Microsoft Azure Neural 0800, Piper TTS Offline, ElevenLabs e Google Gemini.
          </p>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-[#c5a059] to-amber-500 hover:from-amber-500 hover:to-[#c5a059] text-slate-950 font-black text-xs shadow-xl shadow-[#c5a059]/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{saving ? 'Gravando no Banco...' : 'Salvar Todas as Configurações'}</span>
        </button>
      </div>

      {/* ── NAVEGAÇÃO POR ABAS ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('voz')}
          className={`flex items-center justify-center gap-2 p-3.5 rounded-2xl border text-xs font-black transition-all ${
            activeTab === 'voz'
              ? 'bg-[#c5a059] text-slate-950 border-[#c5a059] shadow-lg shadow-[#c5a059]/20'
              : 'bg-[#0b1222] text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
          }`}
        >
          <Volume2 className="w-3.5 h-3.5" />
          <span>🎙️ 1. Voz & Notificações</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('jarvis')}
          className={`flex items-center justify-center gap-2 p-3.5 rounded-2xl border text-xs font-black transition-all ${
            activeTab === 'jarvis'
              ? 'bg-[#00e5ff] text-slate-950 border-[#00e5ff] shadow-lg shadow-[#00e5ff]/20'
              : 'bg-[#0b1222] text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
          }`}
        >
          <Bot className="w-3.5 h-3.5" />
          <span>🤖 2. IA & JARVIS</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('alertas')}
          className={`flex items-center justify-center gap-2 p-3.5 rounded-2xl border text-xs font-black transition-all ${
            activeTab === 'alertas'
              ? 'bg-[#c5a059] text-slate-950 border-[#c5a059] shadow-lg shadow-[#c5a059]/20'
              : 'bg-[#0b1222] text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>🔔 3. Alertas & Sinos</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('parametros')}
          className={`flex items-center justify-center gap-2 p-3.5 rounded-2xl border text-xs font-black transition-all ${
            activeTab === 'parametros'
              ? 'bg-[#c5a059] text-slate-950 border-[#c5a059] shadow-lg shadow-[#c5a059]/20'
              : 'bg-[#0b1222] text-slate-400 border-slate-800 hover:border-slate-700 hover:text-white'
          }`}
        >
          <Tv className="w-3.5 h-3.5" />
          <span>📺 4. Telão TV & Parâmetros</span>
        </button>
      </div>

      {/* ── CONTEÚDO DAS ABAS ── */}
      <div className="space-y-6">
        {/* ── ABA 1: NOTIFICAÇÕES POR VOZ & TTS ── */}
        {activeTab === 'voz' && (
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Mic className="w-4 h-4 text-[#c5a059]" />
                <span>Motor de Síntese de Voz Global das Notificações</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Escolha o motor utilizado para anunciar novas pautas, homologações e chamadas na Web e no Telão TV.
              </p>
            </div>

            <div className="space-y-4">
              {/* 4 Seletores Principais */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Edge Azure 0800 */}
                <div
                  onClick={() => setTtsEngine('edge')}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    ttsEngine === 'edge'
                      ? 'bg-blue-500/10 border-blue-400 shadow-lg shadow-blue-500/10'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-black text-xs text-blue-400">🌐 Microsoft Azure 0800</span>
                    {ttsEngine === 'edge' && <CheckCircle2 className="w-4 h-4 text-blue-400" />}
                  </div>
                  <p className="text-[11px] text-slate-300 font-medium mt-1">Antonio / Francisca / Thalita</p>
                  <p className="text-[9px] text-slate-500 mt-0.5">Qualidade de Estúdio • Sem Chave</p>
                </div>

                {/* 2. Piper Local */}
                <div
                  onClick={() => setTtsEngine('piper')}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    ttsEngine === 'piper'
                      ? 'bg-cyan-500/10 border-cyan-400 shadow-lg shadow-cyan-500/10'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-black text-xs text-cyan-400">💻 Piper Neural Local</span>
                    {ttsEngine === 'piper' && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
                  </div>
                  <p className="text-[11px] text-slate-300 font-medium mt-1">Voz Jarvis Faber (60MB)</p>
                  <p className="text-[9px] text-slate-500 mt-0.5">100% Offline • Sem Internet</p>
                </div>

                {/* 3. Voz do Sistema */}
                <div
                  onClick={() => setTtsEngine('browser')}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    ttsEngine === 'browser'
                      ? 'bg-emerald-500/10 border-emerald-500 shadow-lg shadow-emerald-500/10'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-black text-xs text-emerald-400">👩 Voz Nativa Windows</span>
                    {ttsEngine === 'browser' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                  </div>
                  <p className="text-[11px] text-slate-300 font-medium mt-1">Vozes do Navegador</p>
                  <p className="text-[9px] text-slate-500 mt-0.5">Direct Speech API</p>
                </div>

                {/* 4. ElevenLabs */}
                <div
                  onClick={() => setTtsEngine('elevenlabs')}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                    ttsEngine === 'elevenlabs'
                      ? 'bg-[#c5a059]/10 border-[#c5a059] shadow-lg shadow-[#c5a059]/10'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-black text-xs text-[#c5a059]">✨ ElevenLabs IA</span>
                    {ttsEngine === 'elevenlabs' && <CheckCircle2 className="w-4 h-4 text-[#c5a059]" />}
                  </div>
                  <p className="text-[11px] text-slate-300 font-medium mt-1">Voz Paga de Estúdio</p>
                  <p className="text-[9px] text-slate-500 mt-0.5">Requer chave sk_...</p>
                </div>
              </div>

              {/* ── PAINÉIS ESPECÍFICOS ── */}

              {/* 0. PAINEL MICROSOFT AZURE NEURAL 0800 (EDGE-TTS) COM PERSONALIZAÇÃO COMPLETA */}
              {ttsEngine === 'edge' && (
                <div className="p-5 rounded-2xl bg-slate-950 border border-blue-500/40 space-y-4 animate-in fade-in text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-blue-400 flex items-center gap-1.5">
                      <Globe className="w-4 h-4" /> Estúdio de Síntese Microsoft Azure Neural (100% 0800 & Ilimitado)
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono text-[10px] border border-emerald-500/30">
                      🟢 0800 Sem Chave • Qualidade Ultra-Realista
                    </span>
                  </div>

                  <div>
                    <label className="text-slate-300 font-bold block mb-1">
                      Escolha a Voz Neural da Microsoft (Azure):
                    </label>
                    <select
                      value={selectedAzureVoice}
                      onChange={(e) => setSelectedAzureVoice(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white font-medium focus:outline-none focus:border-blue-400"
                    >
                      {AZURE_EDGE_VOICES.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} • {v.style}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Sliders de Personalização: Pitch e Rate */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>Velocidade de Fala (Rate):</span>
                        <span className="font-bold text-white">
                          {azureRate >= 0 ? `+${azureRate}%` : `${azureRate}%`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-30"
                        max="50"
                        step="5"
                        value={azureRate}
                        onChange={(e) => setAzureRate(parseInt(e.target.value))}
                        className="w-full accent-blue-400"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                        <span>Tom da Voz / Grave (Pitch):</span>
                        <span className="font-bold text-white">
                          {azurePitch >= 0 ? `+${azurePitch}Hz` : `${azurePitch}Hz`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-20"
                        max="20"
                        step="2"
                        value={azurePitch}
                        onChange={(e) => setAzurePitch(parseInt(e.target.value))}
                        className="w-full accent-blue-400"
                      />
                      <p className="text-[9px] text-slate-500 mt-0.5">Valores negativos deixam a voz mais grave e encorpada (estilo Jarvis).</p>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={handleTestAzureVoice}
                      disabled={testingAzure}
                      className="px-5 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-400 text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-blue-500/20"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{testingAzure ? 'Gerando MP3 de Estúdio...' : '🧪 Ouvir com Essa Personalização'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 1. Painel do Piper Neural Local (Voz Jarvis Offline) */}
              {ttsEngine === 'piper' && (
                <div className="p-5 rounded-2xl bg-slate-950 border border-cyan-500/40 space-y-3 animate-in fade-in text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-cyan-400 flex items-center gap-1.5">
                      <Cpu className="w-4 h-4" /> Servidor Piper TTS Neural Local (pt_BR-faber-medium)
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono text-[10px] border border-emerald-500/30 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span>100% Offline • Sem Internet</span>
                    </span>
                  </div>

                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    Motor neural offline gravado no seu disco (~63 MB). Sintetiza instantaneamente no seu processador mesmo se a internet do quartel cair por completo.
                  </p>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={handleTestPiperLocal}
                      disabled={testingPiper}
                      className="px-5 py-2 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{testingPiper ? 'Sintetizando...' : '🧪 Ouvir Voz Offline do Jarvis'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 2. Painel de Voz Neural do Navegador */}
              {ttsEngine === 'browser' && (
                <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 animate-in fade-in text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                      <Volume2 className="w-4 h-4" /> Selecione a Voz Instalada no seu Navegador / Windows:
                    </span>
                    <button
                      type="button"
                      onClick={loadBrowserVoicesList}
                      className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Atualizar Lista de Vozes</span>
                    </button>
                  </div>

                  <div>
                    <select
                      value={selectedBrowserVoice}
                      onChange={(e) => setSelectedBrowserVoice(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white font-medium focus:outline-none focus:border-emerald-400"
                    >
                      {browserVoices.map((v, i) => (
                        <option key={i} value={v.name}>
                          {v.name} ({v.lang})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={handleTestNativeVoice}
                      disabled={testingNativeVoice}
                      className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-emerald-500/20"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{testingNativeVoice ? 'Reproduzindo...' : '🧪 Testar Esta Voz Nativa'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 3. Painel do ElevenLabs */}
              {ttsEngine === 'elevenlabs' && (
                <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 animate-in fade-in text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#c5a059] flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-[#c5a059]" /> Chave de API do ElevenLabs (começa com sk_...)
                    </span>
                    <a
                      href="https://elevenlabs.io"
                      target="_blank"
                      rel="noreferrer"
                      className="text-[10px] text-[#00e5ff] font-bold hover:underline flex items-center gap-1"
                    >
                      <span>Obter chave no ElevenLabs</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showKey ? 'text' : 'password'}
                        placeholder="Cole aqui sua chave secreta sk_..."
                        value={elevenlabsKey}
                        onChange={(e) => setElevenlabsKey(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                      >
                        {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={handleTestElevenLabsDirect}
                      disabled={testingElevenLabs || !elevenlabsKey.trim()}
                      className="px-4 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-[#c5a059]/20 disabled:opacity-40"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{testingElevenLabs ? 'Testando...' : 'Testar Chave'}</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-slate-300 font-bold block">Vozes Disponíveis (Free & Conta)</label>
                        <button
                          type="button"
                          onClick={handleFetchElevenLabsAccountVoices}
                          disabled={loadingElevenVoices || !elevenlabsKey.trim()}
                          className="text-[10px] text-[#00e5ff] font-bold hover:underline flex items-center gap-1"
                        >
                          <RefreshCw className={`w-3 h-3 ${loadingElevenVoices ? 'animate-spin' : ''}`} />
                          <span>Buscar Vozes da Minha Conta</span>
                        </button>
                      </div>
                      <select
                        value={elevenlabsVoiceId}
                        onChange={(e) => setElevenlabsVoiceId(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none font-medium"
                      >
                        {elevenlabsVoicesList.map((v) => (
                          <option key={v.id} value={v.id}>
                            {v.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-slate-300 font-bold block mb-1">Voice ID Customizado</label>
                      <input
                        type="text"
                        value={elevenlabsVoiceId}
                        onChange={(e) => setElevenlabsVoiceId(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white font-mono focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Frase Personalizada para Testes */}
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <label className="text-xs font-bold text-slate-300 block">Frase para Testes de Voz:</label>
                <input
                  type="text"
                  value={testVoiceText}
                  onChange={(e) => setTestVoiceText(e.target.value)}
                  placeholder="Digite a frase para teste..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── ABA 2: PERSONALIDADE & VOZ DO JARVIS ── */}
        {activeTab === 'jarvis' && (
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Bot className="w-4 h-4 text-[#00e5ff]" />
                <span>Personalidade, Temperamento & Voz Neural do JARVIS</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Defina como o JARVIS deve conversar, o vocativo utilizado e teste as vozes e a chave do Gemini em tempo real.
              </p>
            </div>

            <div className="space-y-4 text-xs">
              {/* Estilo de Temperamento */}
              <div>
                <label className="block text-slate-300 font-bold mb-1.5">Estilo de Diálogo / Temperamento</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                  <button
                    type="button"
                    onClick={() => setJarvisConfig({ ...jarvisConfig, temperament: 'stark_british' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      jarvisConfig.temperament === 'stark_british'
                        ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <p className="font-bold text-[11px]">🎩 Britânico Homem de Ferro</p>
                    <span className="text-[9px] text-slate-500">Polido, nobre e prestativo</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setJarvisConfig({ ...jarvisConfig, temperament: 'military_tactical' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      jarvisConfig.temperament === 'military_tactical'
                        ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <p className="font-bold text-[11px]">🛡️ Militar Operacional</p>
                    <span className="text-[9px] text-slate-500">Direto, firme e conciso</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setJarvisConfig({ ...jarvisConfig, temperament: 'strategic_analyst' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      jarvisConfig.temperament === 'strategic_analyst'
                        ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <p className="font-bold text-[11px]">📊 Analista Estratégico</p>
                    <span className="text-[9px] text-slate-500">Foco em dados e métricas</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setJarvisConfig({ ...jarvisConfig, temperament: 'sarcastic_elegant' })}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      jarvisConfig.temperament === 'sarcastic_elegant'
                        ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    <p className="font-bold text-[11px]">😏 Sarcástico Elegante</p>
                    <span className="text-[9px] text-slate-500">Ironia sutil e espirituosa</span>
                  </button>
                </div>
              </div>

              {/* Vocativo e Motor de Voz */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Como o Jarvis deve te chamar?</label>
                  <input
                    type="text"
                    value={jarvisConfig.vocative}
                    onChange={(e) => setJarvisConfig({ ...jarvisConfig, vocative: e.target.value })}
                    placeholder="Ex: Sargento Calaça, Amigo, etc."
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#00e5ff]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Voz Ativa do JARVIS</label>
                  <div className="px-4 py-2.5 rounded-xl bg-slate-900 border border-blue-500/40 text-blue-300 font-bold text-xs flex items-center justify-between shadow-sm">
                    <span className="flex items-center gap-2">
                      <Volume2 className="w-4 h-4 text-blue-400" />
                      <span>
                        Sincronizada com Aba 1:{' '}
                        <strong className="text-white">
                          {ttsEngine === 'edge'
                            ? `Azure (${selectedAzureVoice.replace('pt-BR-', '').replace('Neural', '')})`
                            : ttsEngine === 'piper'
                            ? 'Piper Offline (Faber)'
                            : ttsEngine === 'browser'
                            ? `Nativa (${selectedBrowserVoice || 'Windows'})`
                            : 'ElevenLabs'}
                        </strong>
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setActiveTab('voz')}
                      className="text-[11px] text-[#00e5ff] font-black hover:underline flex items-center gap-1"
                    >
                      <span>Alterar na Aba 1 →</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Chave de API Gemini com Botão de Teste Direto */}
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-[#00e5ff]" /> Chave de API do Google Gemini (Google AI Studio)
                  </span>
                  <a
                    href="https://aistudio.google.com"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-[#00e5ff] font-bold hover:underline flex items-center gap-1"
                  >
                    <span>Obter chave grátis no Google AI Studio</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <input
                      type={showGeminiKey ? 'text' : 'password'}
                      placeholder="Cole aqui sua chave Gemini (ex: AIzaSy...)"
                      value={geminiKey}
                      onChange={(e) => setGeminiKey(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-[#00e5ff]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
                    >
                      {showGeminiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={handleTestGeminiApi}
                    disabled={testingGemini || !geminiKey.trim()}
                    className="px-4 py-2.5 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-[#00e5ff]/20 disabled:opacity-40"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{testingGemini ? 'Testando...' : 'Testar Chave Gemini'}</span>
                  </button>
                </div>
              </div>

              {/* Botão de Teste da Voz do Jarvis */}
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                <div>
                  <p className="font-bold text-white text-xs">Testar a Voz Atual do JARVIS</p>
                  <p className="text-[10px] text-slate-400">
                    Ouvir uma frase falada com a voz e personalizações selecionadas na Aba 1:
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleTestJarvisVoice}
                  disabled={testingJarvisVoice}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#00e5ff] to-cyan-400 hover:from-cyan-400 hover:to-[#00e5ff] text-slate-950 font-black text-xs flex items-center gap-2 shadow-lg shadow-[#00e5ff]/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>{testingJarvisVoice ? 'Reproduzindo...' : '🧪 Ouvir Voz do JARVIS'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── ABA 3: ALERTAS & SINAIS SONOROS ── */}
        {activeTab === 'alertas' && (
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Bell className="w-4 h-4 text-[#c5a059]" />
                <span>Alertas Sonoros, Sinos Navais & Automações</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Defina os gatilhos de áudio, sinos nas horas cheias e leitura de pautas em voz alta.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950 border border-slate-800 cursor-pointer">
                <div>
                  <p className="font-bold text-white text-xs">Leitura Automática por Voz das Novas Demandas</p>
                  <p className="text-[10px] text-slate-400">
                    Anuncia em voz alta quando entrar uma solicitação de pauta ou homologação de evento.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={voiceAlertsEnabled}
                  onChange={(e) => setVoiceAlertsEnabled(e.target.checked)}
                  className="w-4 h-4 rounded text-[#c5a059] focus:ring-0 bg-slate-900 border-slate-700"
                />
              </label>

              <div className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                <div>
                  <p className="font-bold text-white text-xs">Sino Náutico Oficial nas Horas Cheias</p>
                  <p className="text-[10px] text-slate-400">
                    Badaladas navais tradicionais sintetizadas em áudio de alta definição.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={playTestBell}
                    className="px-3 py-1 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[#c5a059] font-bold text-xs"
                  >
                    🔔 Testar Sino
                  </button>
                  <input
                    type="checkbox"
                    checked={nauticalBellEnabled}
                    onChange={(e) => setNauticalBellEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-[#c5a059] focus:ring-0 bg-slate-900 border-slate-700 cursor-pointer"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
                <label className="block text-slate-300 font-bold">Vocativo Pré-Anúncio da TV</label>
                <input
                  type="text"
                  value={alertVocativo}
                  onChange={(e) => setAlertVocativo(e.target.value)}
                  placeholder="Ex: Atenção Gabinete ou Atenção Comunicação Social"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>
            </div>
          </div>
        )}

        {/* ── ABA 4: TELÃO TV & PARÂMETROS ── */}
        {activeTab === 'parametros' && (
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Tv className="w-4 h-4 text-[#c5a059]" />
                <span>Personalização do SisGAB TV & Parâmetros</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Textos do cabeçalho do telão, intervalo de atualização e senhas.
              </p>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Título do Cabeçalho da TV</label>
                  <input
                    type="text"
                    value={configData.cabecalho_tv_title}
                    onChange={(e) => setConfigData({ ...configData, cabecalho_tv_title: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Subtítulo do Cabeçalho da TV</label>
                  <input
                    type="text"
                    value={configData.cabecalho_tv_subtitle}
                    onChange={(e) => setConfigData({ ...configData, cabecalho_tv_subtitle: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Tempo de Transição / Slide TV (Segundos)</label>
                  <input
                    type="number"
                    value={configData.tempo_polling_tv}
                    onChange={(e) => setConfigData({ ...configData, tempo_polling_tv: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">PIN / Código de Desbloqueio do Telão</label>
                  <input
                    type="password"
                    value={configData.codigo_desbloqueio_tv}
                    onChange={(e) => setConfigData({ ...configData, codigo_desbloqueio_tv: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono focus:outline-none"
                  />
                </div>
              </div>

              {/* ── IDENTIDADE VISUAL & LOGO DO SISTEMA ── */}
              <div className="pt-4 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-black text-[#c5a059] flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    <span>Identidade Visual & Brasão / Logo Principal</span>
                  </h3>
                  <button
                    type="button"
                    onClick={() => {
                      localStorage.removeItem('sisgab_custom_logo');
                      toast.info('Brasão oficial padrão do CGCFN restaurado.');
                    }}
                    className="text-xs text-rose-400 hover:text-rose-300 font-bold"
                  >
                    Restaurar Brasão Padrão
                  </button>
                </div>
                <p className="text-slate-400 text-xs">
                  Personalize o brasão/logo exibido na tela de login, barra lateral e cabeçalho do SisGAB.
                </p>

                <div className="flex items-center gap-4 p-4 rounded-2xl bg-slate-950 border border-slate-800">
                  <img
                    src={localStorage.getItem('sisgab_custom_logo') || '/brasaocgcfn.png'}
                    alt="Logo do SisGAB"
                    className="w-20 h-20 object-contain drop-shadow-md rounded-xl bg-slate-900/60 p-1 border border-slate-700"
                  />
                  <div className="flex-1 space-y-2">
                    <input
                      type="file"
                      id="system-logo-upload"
                      accept="image/png, image/jpeg, image/svg+xml, image/webp"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (event) => {
                            const b64 = event.target?.result as string;
                            if (b64) {
                              localStorage.setItem('sisgab_custom_logo', b64);
                              toast.success('Logo do sistema atualizado com sucesso!');
                            }
                          };
                          reader.readAsDataURL(file);
                        }
                      }}
                      className="hidden"
                    />
                    <label
                      htmlFor="system-logo-upload"
                      className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#c5a059] text-white font-bold text-xs inline-flex items-center gap-2 cursor-pointer transition-colors"
                    >
                      <Upload className="w-3.5 h-3.5 text-[#c5a059]" />
                      <span>Fazer Upload de Novo Logo (PNG / SVG / JPG)</span>
                    </label>
                    <span className="block text-[10px] text-slate-500">
                      Recomendado: imagem transparente PNG ou SVG quadrada de 512x512px.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </form>
  );
};
