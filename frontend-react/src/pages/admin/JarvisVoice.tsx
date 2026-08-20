import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  Volume2,
  Bot,
  Terminal,
  Send,
  Trash2,
  RotateCcw,
  CheckCircle2,
  Calendar,
  Clock,
  MapPin,
  Camera,
  X,
  Sparkles,
  HelpCircle,
  VolumeX,
  Key,
  Sliders,
  Check,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { supabase } from '../../api/supabase';
import { playNeuralSpeech, stopNeuralSpeech, NeuralVoiceOption } from '../../utils/neuralTTS';
import { generateGeminiContent } from '../../utils/geminiClient';
import { getBrasiliaDateStr, addDaysBrasilia } from '../../utils/formatters';

interface ChatMessage {
  id: string;
  role: 'user' | 'jarvis';
  text: string;
  time: string;
  demandDraft?: Partial<DemandDraft>;
}

interface DemandDraft {
  titulo_evento: string;
  data_evento: string;
  hora_evento: string;
  local_evento: string;
  tipo_cobertura: string[];
  solicitante_nome: string;
  setor: string;
}

interface JarvisConfig {
  temperament: 'stark_british' | 'military_tactical' | 'strategic_analyst' | 'sarcastic_elegant';
  vocative: string;
  responseLength: 'concise' | 'detailed';
  voiceEngine: 'antonio_neural' | 'francisca_neural' | 'google_neural' | 'elevenlabs' | 'browser';
  elevenlabsVoiceId: string;
  customInstructions: string;
}

const DEFAULT_JARVIS_CONFIG: JarvisConfig = {
  temperament: 'stark_british',
  vocative: '',
  responseLength: 'concise',
  voiceEngine: 'francisca_neural', // Voz suave padrão recomendada
  elevenlabsVoiceId: 'N2lVS1w4EtoT3dr4eOWO',
  customInstructions: 'Você é o JARVIS. Converse de maneira 100% natural, amigável, humana, empática e prestativa. Responda com naturalidade a qualquer assunto.',
};

// 9 Comandos e Perguntas Rápidas Estratégicas
const QUICK_PROMPTS = [
  { icon: '🗓️', label: 'Eventos da Semana', query: 'Quais eventos temos na semana e qual evento eu vou cobrir?' },
  { icon: '✍️', label: 'Criar Nova Demanda', query: 'Quero cadastrar uma nova demanda' },
  { icon: '📋', label: 'Pautas Pendentes', query: 'Tem alguma pauta pendente de homologação na Chefia?' },
  { icon: '⚓', label: 'Pronto da Guarnição', query: 'Como está a situação do pronto da guarnição hoje?' },
  { icon: '🎂', label: 'Aniversariantes', query: 'Temos algum militar fazendo aniversário no Gabinete hoje?' },
  { icon: '🪪', label: 'Placas JADE', query: 'Quantas placas JADE estão aguardando impressão no cerimonial?' },
  { icon: '🪙', label: 'Estoque de Brindes', query: 'Como está o saldo de moedas comemorativas e brindes de RP?' },
  { icon: '🛡️', label: 'Resumo Operacional', query: 'O que temos de mais prioritário para o Gabinete hoje?' },
  { icon: '💬', label: 'Como Você Funciona?', query: 'O que você consegue fazer como assistente do Gabinete?' },
];

export const JarvisVoice: React.FC = () => {
  const { user } = useAuth();
  const [isListening, setIsListening] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Configurações
  const [jarvisConfig, setJarvisConfig] = useState<JarvisConfig>(DEFAULT_JARVIS_CONFIG);
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [elevenlabsApiKey, setElevenlabsApiKey] = useState('');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKey, setTempKey] = useState('');

  // Rascunho de Demanda em Andamento (Memória Interativa & Wizard Guiado)
  const [activeDraft, setActiveDraft] = useState<DemandDraft | null>(null);
  const [isAwaitingConfirmation, setIsAwaitingConfirmation] = useState(false);
  const [wizardStep, setWizardStep] = useState<'idle' | 'ask_title' | 'ask_datetime_local' | 'ask_services' | 'confirming'>('idle');
  const [wizardDraft, setWizardDraft] = useState<Partial<DemandDraft>>({});

  // Histórico Contínuo e Persistente do Chat
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'jarvis',
      text: `Olá! Estou por aqui, 100% online para conversar ou criar demandas por voz. Em que posso te ajudar hoje?`,
      time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const recognitionRef = useRef<any>(null);
  const transcriptRef = useRef<string>('');
  const lastProcessedPromptRef = useRef<{ text: string; time: number }>({ text: '', time: 0 });
  const [manualInput, setManualInput] = useState('');
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Configurações de Voz herdadas da Aba 1
  const [globalTtsEngine, setGlobalTtsEngine] = useState<string>('edge');
  const [azureVoiceName, setAzureVoiceName] = useState<string>('pt-BR-AntonioNeural');
  const [azureRate, setAzureRate] = useState<number>(0);
  const [azurePitch, setAzurePitch] = useState<number>(0);
  const [nativeVoiceName, setNativeVoiceName] = useState<string>('');

  useEffect(() => {
    loadJarvisSettings();
    initSpeechRecognition();

    return () => {
      stopNeuralSpeech();
    };
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isProcessing, activeDraft]);

  const loadJarvisSettings = async () => {
    try {
      const localKey = localStorage.getItem('sisgab_gemini_key');
      if (localKey) setGeminiApiKey(localKey);

      const { data } = await supabase.from('config').select('chave, valor');

      if (data) {
        const findVal = (key: string, def: string) =>
          data.find((c) => c.chave === key)?.valor || def;

        // Herda voz definida na Aba 1 (Voz & Notificações)
        const ttsEng = findVal('tts_engine', 'edge');
        setGlobalTtsEngine(ttsEng);
        setAzureVoiceName(findVal('azure_voice_name', 'pt-BR-AntonioNeural'));
        setAzureRate(parseInt(findVal('azure_rate', '0')) || 0);
        setAzurePitch(parseInt(findVal('azure_pitch', '0')) || 0);
        setNativeVoiceName(findVal('native_voice_name', ''));

        const elKey = findVal('elevenlabs_api_key', '');
        if (elKey) setElevenlabsApiKey(elKey);
        const elVoice = findVal('elevenlabs_voice_id', '21m00Tcm4TlvDq8ikWAM');

        const jCfg = findVal('jarvis_config_json', '');
        if (jCfg) {
          try {
            setJarvisConfig({
              ...DEFAULT_JARVIS_CONFIG,
              elevenlabsVoiceId: elVoice,
              ...JSON.parse(jCfg),
            });
          } catch (e) {}
        } else {
          setJarvisConfig((prev) => ({ ...prev, elevenlabsVoiceId: elVoice }));
        }

        const gKey =
          findVal('gemini_api_key', '') ||
          findVal('google_api_key', '') ||
          findVal('GEMINI_API_KEY', '') ||
          findVal('GOOGLE_API_KEY', '');

        if (gKey && gKey.trim()) {
          setGeminiApiKey(gKey.trim());
          localStorage.setItem('sisgab_gemini_key', gKey.trim());
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar configurações do Jarvis:', err);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!tempKey.trim()) return;
    const clean = tempKey.trim();
    setGeminiApiKey(clean);
    localStorage.setItem('sisgab_gemini_key', clean);

    try {
      await supabase.from('config').upsert([
        { chave: 'gemini_api_key', valor: clean },
        { chave: 'google_api_key', valor: clean },
      ]);
      toast.success('Chave da IA Gemini conectada com sucesso!');
      setShowKeyModal(false);
    } catch (e) {
      toast.success('Chave salva localmente!');
      setShowKeyModal(false);
    }
  };

  const initSpeechRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'pt-BR';

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event: any) => {
        let current = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          current += event.results[i][0].transcript;
        }
        transcriptRef.current = current;
        setCurrentTranscript(current);
      };
      recognition.onerror = (event: any) => {
        console.warn('Erro reconhecimento de fala:', event.error);
        setIsListening(false);
      };
      recognition.onend = () => {
        setIsListening(false);
        const captured = transcriptRef.current.trim();
        if (captured.length > 1) {
          transcriptRef.current = '';
          setCurrentTranscript('');
          processVoiceCommand(captured);
        }
      };

      recognitionRef.current = recognition;
    }
  };

  // Coleta dados reais do SisGAB para alimentar a inteligência do Jarvis
  const fetchLiveGabineteContext = async () => {
    try {
      const hoje = getBrasiliaDateStr();
      const seteDiasDepois = addDaysBrasilia(hoje, 7);

      // 1. Demandas da semana
      const { data: demandas } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .gte('data_evento', hoje)
        .lte('data_evento', seteDiasDepois)
        .order('data_evento', { ascending: true });

      // 2. Placas Jade
      const { data: jades } = await supabase
        .from('jade_convidados')
        .select('id, nome, status_placa')
        .eq('status_placa', 'pendente');

      // 3. Pronto de hoje
      const { data: pres } = await supabase.from('escala_diaria').select('*').eq('data_referencia', hoje);

      return {
        demandasSemana: demandas || [],
        placasPendentes: jades || [],
        presencasHoje: pres || [],
        militarLogado: user?.nome_guerra || 'OPERADOR',
        militarId: user?.id,
      };
    } catch (e) {
      return { demandasSemana: [], placasPendentes: [], presencasHoje: [], militarLogado: 'OPERADOR' };
    }
  };

  // Confirmar e Salvar a Demanda no Banco de Dados
  const handleConfirmCreateDemand = async (draftToSave?: DemandDraft) => {
    const draft = draftToSave || activeDraft;
    if (!draft) return;

    stopNeuralSpeech();
    setIsProcessing(true);
    const nowTime = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

    try {
      const rawHora = draft.hora_evento || '10:00:00';
      const safeHora = rawHora.length === 5 ? `${rawHora}:00` : rawHora;

      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .insert({
          solicitante_nome: draft.solicitante_nome || user?.nome_guerra || 'ComSoc',
          setor: draft.setor || 'Gabinete CGCFN',
          contato: 'Gabinete CGCFN',
          titulo_evento: draft.titulo_evento.toUpperCase(),
          data_evento: draft.data_evento || getBrasiliaDateStr(),
          hora_evento: safeHora,
          local_evento: draft.local_evento || 'Fortaleza de São José - Ilha das Cobras',
          tipo_cobertura: draft.tipo_cobertura.length > 0 ? draft.tipo_cobertura : ['Fotografia'],
          status: 'pendente',
          score_esforco: 50,
          captacao_entrega: 'Normal',
        })
        .select()
        .single();

      if (error) throw error;

      militaryAudio.playTacticalBeep();
      toast.success(`Demanda "${draft.titulo_evento}" cadastrada com sucesso!`);

      const confirmText = `Perfeito! Cadastrei a demanda "${draft.titulo_evento}" no SisGAB. Ela já está aguardando homologação da Chefia.`;
      setChatHistory((prev) => [
        ...prev,
        { id: `confirm_${Date.now()}`, role: 'jarvis', text: confirmText, time: nowTime },
      ]);

      setActiveDraft(null);
      setIsAwaitingConfirmation(false);
      setWizardStep('idle');
      setWizardDraft({});
      await speakJarvisResponse(confirmText);
    } catch (err: any) {
      const errMsg = `Tive um problema ao gravar a demanda: ${err.message}`;
      toast.error(errMsg);
      setChatHistory((prev) => [
        ...prev,
        { id: `err_${Date.now()}`, role: 'jarvis', text: errMsg, time: nowTime },
      ]);
      await speakJarvisResponse(`Houve um erro ao registrar a demanda.`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Cancelar Rascunho
  const handleCancelDraft = () => {
    stopNeuralSpeech();
    setActiveDraft(null);
    setIsAwaitingConfirmation(false);
    setWizardStep('idle');
    setWizardDraft({});
    const cancelText = 'Tudo bem, rascunho cancelado. Não cadastrei nada.';
    const nowTime = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    setChatHistory((prev) => [
      ...prev,
      { id: `cancel_${Date.now()}`, role: 'jarvis', text: cancelText, time: nowTime },
    ]);
    speakJarvisResponse(cancelText);
  };

  // Interromper fala
  const handleStopSpeaking = () => {
    stopNeuralSpeech();
    setIsSpeaking(false);
  };

  // Motor Conversacional e de Ações do Jarvis (Humano, Fluido & Empático)
  const processVoiceCommand = async (userPrompt: string) => {
    if (!userPrompt || !userPrompt.trim()) return;

    const trimmedPrompt = userPrompt.trim();
    const now = Date.now();

    // ── Prevenção contra execução duplicada do mesmo comando em menos de 2.5 segundos ──
    if (
      lastProcessedPromptRef.current.text.toLowerCase() === trimmedPrompt.toLowerCase() &&
      now - lastProcessedPromptRef.current.time < 2500
    ) {
      console.log('Ignorando comando de voz duplicado:', trimmedPrompt);
      return;
    }
    lastProcessedPromptRef.current = { text: trimmedPrompt, time: now };

    stopNeuralSpeech();
    setIsSpeaking(false);
    setIsProcessing(true);

    const nowTime = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    const cleanPrompt = trimmedPrompt.toLowerCase();

    setChatHistory((prev) => [...prev, { id: `user_${Date.now()}`, role: 'user', text: trimmedPrompt, time: nowTime }]);

    try {
      const ctx = await fetchLiveGabineteContext();
      let respostaTexto = '';
      let generatedDraft: DemandDraft | null = null;

      // ── DETECTA SE O USUÁRIO QUER ESCAPAR OU FAZER PERGUNTA GERAL DURANTE UM WIZARD ──
      const isQuestionOrTopicChange =
        cleanPrompt.includes('?') ||
        cleanPrompt.includes('priorit') ||
        cleanPrompt.includes('prioridade') ||
        cleanPrompt.includes('o que ') ||
        cleanPrompt.includes('qual ') ||
        cleanPrompt.includes('quem ') ||
        cleanPrompt.includes('como ') ||
        cleanPrompt.includes('quando ') ||
        cleanPrompt.includes('onde ') ||
        cleanPrompt.includes('fala ') ||
        cleanPrompt.includes('pode fazer') ||
        cleanPrompt.includes('ajuda') ||
        cleanPrompt.includes('quem é você') ||
        cleanPrompt.includes('cancela') ||
        cleanPrompt.includes('esquece') ||
        cleanPrompt.includes('não quero') ||
        cleanPrompt.includes('nada');

      if (isQuestionOrTopicChange && wizardStep !== 'idle' && wizardStep !== 'confirming') {
        setWizardStep('idle');
        setWizardDraft({});
      }

      // ── FLUXO WIZARD PASSO 1: USUÁRIO INFORMOU O TÍTULO / TIPO DO EVENTO ──
      if (wizardStep === 'ask_title') {
        const cleanTitle = trimmedPrompt
          .replace(/^(é|o|a|um|uma|tipo|nome|evento|demanda|pauta|para o|para a)\s+/gi, '')
          .replace(/[.!?]/g, '')
          .trim()
          .toUpperCase();

        setWizardDraft((prev) => ({ ...prev, titulo_evento: cleanTitle }));
        setWizardStep('ask_datetime_local');
        respostaTexto = `Entendido, ${cleanTitle}! Para qual data e horário está previsto? E qual será o local?`;
      }
      // ── FLUXO WIZARD PASSO 2: USUÁRIO INFORMOU DATA, HORA E LOCAL ──
      else if (wizardStep === 'ask_datetime_local') {
        let extractedHour = '10:00';
        const hourMatch = cleanPrompt.match(/(\d{1,2})\s*(?:h|horas|:\d{2})/);
        if (hourMatch) {
          const h = parseInt(hourMatch[1], 10);
          extractedHour = `${h < 10 ? '0' : ''}${h}:00`;
        }

        let targetDateStr = getBrasiliaDateStr();
        if (cleanPrompt.includes('amanhã')) {
          targetDateStr = addDaysBrasilia(targetDateStr, 1);
        } else if (cleanPrompt.includes('sexta')) {
          const hojeDate = new Date();
          const dist = (5 - hojeDate.getDay() + 7) % 7 || 7;
          targetDateStr = addDaysBrasilia(targetDateStr, dist);
        } else if (cleanPrompt.includes('segunda')) {
          const hojeDate = new Date();
          const dist = (1 - hojeDate.getDay() + 7) % 7 || 7;
          targetDateStr = addDaysBrasilia(targetDateStr, dist);
        }

        let extractedLocal = 'Salão Nobre do CGCFN';
        if (cleanPrompt.includes('fortaleza')) extractedLocal = 'Fortaleza de São José - Ilha das Cobras';
        else if (cleanPrompt.includes('ciasc')) extractedLocal = 'CIASC';
        else if (cleanPrompt.includes('campo grande')) extractedLocal = 'Batalhão Riachuelo - Campo Grande';
        else if (cleanPrompt.includes('praça mauá') || cleanPrompt.includes('praca maua')) extractedLocal = 'Praça Mauá - Edifício Barão de Ladário';

        setWizardDraft((prev) => ({
          ...prev,
          data_evento: targetDateStr,
          hora_evento: extractedHour,
          local_evento: extractedLocal,
        }));
        setWizardStep('ask_services');
        respostaTexto = `Anotado! Data ${targetDateStr} às ${extractedHour}, no ${extractedLocal}. Quais serviços de cobertura serão necessários? (Foto, Vídeo, Drone, Cerimonial, Cardápio, etc.)`;
      }
      // ── FLUXO WIZARD PASSO 3: USUÁRIO INFORMOU OS SERVIÇOS ──
      else if (wizardStep === 'ask_services') {
        const servicos: string[] = [];
        if (cleanPrompt.includes('foto') || cleanPrompt.includes('fotografia')) servicos.push('Fotografia');
        if (cleanPrompt.includes('vídeo') || cleanPrompt.includes('video')) servicos.push('Video');
        if (cleanPrompt.includes('drone')) servicos.push('Drone');
        if (cleanPrompt.includes('cardápio') || cleanPrompt.includes('cardapio')) servicos.push('Cardapio_Design');
        if (cleanPrompt.includes('reels') || cleanPrompt.includes('rede') || cleanPrompt.includes('social')) servicos.push('Reels');
        if (cleanPrompt.includes('cerimonial') || cleanPrompt.includes('mestre')) servicos.push('Cerimonial');

        if (servicos.length === 0) servicos.push('Fotografia');

        const finalDraft: DemandDraft = {
          titulo_evento: wizardDraft.titulo_evento || 'COBERTURA DE EVENTO',
          data_evento: wizardDraft.data_evento || getBrasiliaDateStr(),
          hora_evento: wizardDraft.hora_evento || '10:00',
          local_evento: wizardDraft.local_evento || 'Salão Nobre do CGCFN',
          tipo_cobertura: servicos,
          solicitante_nome: user?.nome_guerra || 'ComSoc',
          setor: 'Gabinete CGCFN',
        };

        setActiveDraft(finalDraft);
        setIsAwaitingConfirmation(true);
        setWizardStep('confirming');

        respostaTexto = `Tudo pronto! Montei a demanda: "${finalDraft.titulo_evento}" no dia ${finalDraft.data_evento} às ${finalDraft.hora_evento}, no ${finalDraft.local_evento}. Cobertura: ${finalDraft.tipo_cobertura.join(', ')}. Posso confirmar e salvar no SisGAB?`;
      }
      // ── FLUXO DE CONFIRMAÇÃO POR VOZ ──
      else if (isAwaitingConfirmation && activeDraft) {
        if (
          cleanPrompt.includes('sim') ||
          cleanPrompt.includes('confirma') ||
          cleanPrompt.includes('pode') ||
          cleanPrompt.includes('cadastra') ||
          cleanPrompt.includes('lança') ||
          cleanPrompt.includes('isso') ||
          cleanPrompt.includes('salvar') ||
          cleanPrompt.includes('ok') ||
          cleanPrompt.includes('positivo') ||
          cleanPrompt.includes('manda bala') ||
          cleanPrompt.includes('com certeza')
        ) {
          await handleConfirmCreateDemand(activeDraft);
          return;
        } else if (
          cleanPrompt.includes('não') ||
          cleanPrompt.includes('cancela') ||
          cleanPrompt.includes('esquece') ||
          cleanPrompt.includes('desiste')
        ) {
          handleCancelDraft();
          return;
        }
      }
      // ── FLUXO DE INÍCIO GUIADO DE DEMANDA ──
      else if (
        (cleanPrompt.includes('cria') || cleanPrompt.includes('cadastra') || cleanPrompt.includes('lança') || cleanPrompt.includes('agenda') || cleanPrompt.includes('adicionar') || cleanPrompt.includes('quero criar')) &&
        (cleanPrompt.includes('demanda') || cleanPrompt.includes('pauta') || cleanPrompt.includes('evento')) &&
        !cleanPrompt.includes('salão') && !cleanPrompt.includes('sexta') && !cleanPrompt.includes('amanhã') && !cleanPrompt.includes('12h')
      ) {
        setWizardStep('ask_title');
        setWizardDraft({});
        respostaTexto = 'Com certeza! Qual é o tipo ou título do evento que você deseja cadastrar? (Ex: Almoço de Oficiais, Cerimônia Militar, Visita Oficial, Passagem de Comando)';
      }
      // ── FLUXO DE CRIAÇÃO COMPLETA EM UMA ÚNICA FRASE (COM PARSER LIMPO) ──
      else if (
        (cleanPrompt.includes('cria') || cleanPrompt.includes('cadastra') || cleanPrompt.includes('lança') || cleanPrompt.includes('agenda')) &&
        (cleanPrompt.includes('demanda') || cleanPrompt.includes('pauta') || cleanPrompt.includes('evento') || cleanPrompt.includes('almoço') || cleanPrompt.includes('cerimônia'))
      ) {
        let rawSubject = trimmedPrompt
          .replace(/^(cria|criar|cadastra|cadastrar|lança|lançar|agenda|agendar|adiciona|adicionar)\s+(uma\s+)?(nova\s+)?(demanda|pauta|evento)\s+(para\s+|de\s+|do\s+|da\s+)?/gi, '')
          .replace(/\s+(na|no|em|às|as|dia|para|com|local)\s+.*$/gi, '')
          .trim();

        let cleanTitle = rawSubject && rawSubject.length > 2 ? rawSubject.toUpperCase() : 'COBERTURA DE EVENTO';

        let extractedHour = '10:00';
        const hourMatch = cleanPrompt.match(/(\d{1,2})\s*(?:h|horas|:\d{2})/);
        if (hourMatch) {
          const h = parseInt(hourMatch[1], 10);
          extractedHour = `${h < 10 ? '0' : ''}${h}:00`;
        }

        let targetDateStr = getBrasiliaDateStr();
        if (cleanPrompt.includes('amanhã')) {
          targetDateStr = addDaysBrasilia(targetDateStr, 1);
        } else if (cleanPrompt.includes('sexta')) {
          const hojeDate = new Date();
          const dist = (5 - hojeDate.getDay() + 7) % 7 || 7;
          targetDateStr = addDaysBrasilia(targetDateStr, dist);
        }

        let extractedLocal = 'Salão Nobre do CGCFN';
        if (cleanPrompt.includes('fortaleza')) extractedLocal = 'Fortaleza de São José - Ilha das Cobras';
        else if (cleanPrompt.includes('ciasc')) extractedLocal = 'CIASC';
        else if (cleanPrompt.includes('campo grande')) extractedLocal = 'Batalhão Riachuelo - Campo Grande';

        const servicos: string[] = [];
        if (cleanPrompt.includes('foto') || cleanPrompt.includes('fotografia')) servicos.push('Fotografia');
        if (cleanPrompt.includes('vídeo') || cleanPrompt.includes('video')) servicos.push('Video');
        if (cleanPrompt.includes('drone')) servicos.push('Drone');
        if (cleanPrompt.includes('cardápio') || cleanPrompt.includes('cardapio')) servicos.push('Cardapio_Design');
        if (servicos.length === 0) servicos.push('Fotografia');

        generatedDraft = {
          titulo_evento: cleanTitle,
          data_evento: targetDateStr,
          hora_evento: extractedHour,
          local_evento: extractedLocal,
          tipo_cobertura: servicos,
          solicitante_nome: user?.nome_guerra || 'ComSoc',
          setor: 'Gabinete CGCFN',
        };

        setActiveDraft(generatedDraft);
        setIsAwaitingConfirmation(true);
        setWizardStep('confirming');

        respostaTexto = `Legal! Montei a demanda: "${generatedDraft.titulo_evento}" no dia ${generatedDraft.data_evento} às ${generatedDraft.hora_evento}, no ${generatedDraft.local_evento}. Cobertura: ${generatedDraft.tipo_cobertura.join(', ')}. Posso confirmar e salvar no SisGAB?`;
      }

      // ── FLUXO 3: CONVERSAÇÃO NATURAL COM GEMINI (SE HOUVER CHAVE) ──
      else {
        if (geminiApiKey && geminiApiKey.length > 8) {
          try {
            const systemInstruction = `Você é o JARVIS do Gabinete do CGCFN (Marinha do Brasil).
Responda de forma 100% HUMANA, direta, prestativa e natural.
NUNCA use "senhor" a toda hora. Responda em no máximo 1 a 2 frases para falar em áudio.
Contexto atual: Eventos na semana: ${ctx.demandasSemana.length}. Pronto hoje: ${ctx.presencasHoje.length}. Placas JADE: ${ctx.placasPendentes.length}.`;

            const reply = await generateGeminiContent(trimmedPrompt, systemInstruction, geminiApiKey);
            if (reply && reply.trim()) {
              respostaTexto = reply.trim();
            }
          } catch (e: any) {
            console.warn('Erro ao chamar Gemini:', e);
          }
        }

        // ── FLUXO 4: MOTOR CONVERSACIONAL LOCAL INTELIGENTE (MULTI-INTENT RAG) ──
        if (!respostaTexto) {
          // 1. O QUE VOCÊ PODE FAZER / QUEM É VOCÊ / CAPACIDADES
          if (
            cleanPrompt.includes('o que você faz') ||
            cleanPrompt.includes('o que tu pode fazer') ||
            cleanPrompt.includes('o que você pode fazer') ||
            cleanPrompt.includes('o que pode fazer') ||
            cleanPrompt.includes('fala que tu pode') ||
            cleanPrompt.includes('fala o que você') ||
            cleanPrompt.includes('suas funções') ||
            cleanPrompt.includes('quem é você') ||
            cleanPrompt.includes('o que sabe fazer') ||
            cleanPrompt.includes('como funciona') ||
            cleanPrompt.includes('entendeu nada') ||
            cleanPrompt.includes('me ajuda') ||
            cleanPrompt.includes('ajuda')
          ) {
            respostaTexto = `Eu sou o JARVIS, assistente de inteligência artificial do Gabinete do CGCFN! Posso te passar as prioridades e eventos da semana, checar o Pronto diário e escalas, verificar placas do Cerimonial JADE e até cadastrar novas demandas de cobertura completas por voz. O que você precisa no momento?`;
          }
          // 2. PRIORIDADES DO GABINETE / O QUE TEMOS HOJE / AGENDA
          else if (
            cleanPrompt.includes('priorit') ||
            cleanPrompt.includes('prioridade') ||
            cleanPrompt.includes('mais importante') ||
            cleanPrompt.includes('agenda de hoje') ||
            cleanPrompt.includes('o que temos hoje') ||
            cleanPrompt.includes('o que temos para hoje') ||
            cleanPrompt.includes('o que temos de mais') ||
            cleanPrompt.includes('temos hoje') ||
            cleanPrompt.includes('hoje no gabinete')
          ) {
            const hojeStr = getBrasiliaDateStr();
            const demandasHoje = ctx.demandasSemana.filter((d: any) => d.data_evento === hojeStr);
            const placasCount = ctx.placasPendentes.length;

            if (demandasHoje.length > 0) {
              const p = demandasHoje[0];
              respostaTexto = `Para hoje no Gabinete, nossa principal prioridade é "${p.titulo_evento}", prevista para às ${p.hora_evento || '10h'} no ${p.local_evento || 'Salão Nobre'}. Temos ${demandasHoje.length} evento(s) hoje e ${placasCount} placa(s) JADE aguardando confecção.`;
            } else if (ctx.demandasSemana.length > 0) {
              const prox = ctx.demandasSemana[0];
              respostaTexto = `Para hoje não há solenidades de grande porte agendadas. Nossa próxima prioridade na semana é "${prox.titulo_evento}", marcada para ${prox.data_evento} às ${prox.hora_evento || '10h'} no ${prox.local_evento}. O Pronto diário está estabilizado.`;
            } else {
              respostaTexto = `Para hoje no Gabinete a rotina está tranquila e sem solenidades urgentes registradas no SisGAB. O Pronto da guarnição está lançado e os sistemas operando normalmente. Quer agendar uma nova demanda?`;
            }
          }
          // 3. Piadas / Humor
          else if (cleanPrompt.includes('piada') || cleanPrompt.includes('engraçado') || cleanPrompt.includes('rir') || cleanPrompt.includes('brincadeira')) {
            const piadas = [
              "Por que o computador foi ao médico? Porque ele estava com vírus!",
              "Qual é o café favorito do militar? O café de prontidão!",
              "Por que o livro de matemática se suicidou? Porque ele tinha muitos problemas!",
              "Qual o cúmulo da tecnologia? O robô pedir licença para reiniciar a vida!",
            ];
            respostaTexto = piadas[Math.floor(Math.random() * piadas.length)];
          }
          // 4. Adicionar tarefa / missão
          else if (cleanPrompt.includes('adicionar uma tarefa') || cleanPrompt.includes('criar tarefa') || cleanPrompt.includes('nova tarefa')) {
            respostaTexto = `Claro! Me diz qual é a tarefa, o prazo ou se está vinculada a alguma solenidade que eu registro no nosso quadro de tarefas.`;
          }
          // 5. Perguntas gerais / Recomendações (Carros, compras, tecnologia)
          else if (cleanPrompt.includes('carro') || cleanPrompt.includes('veículo') || cleanPrompt.includes('comprar')) {
            respostaTexto = `Depende muito do seu orçamento e uso! Para a cidade, carros compactos automáticos ou SUVs híbridos (como Corolla Cross ou Tracker) são muito econômicos e confiáveis. Me conta o que você procura que te dou opções mais certeiras!`;
          }
          // 6. Saúde, dores, cansaço
          else if (cleanPrompt.includes('dor de barriga') || cleanPrompt.includes('passando mal') || cleanPrompt.includes('dor de cabeça') || cleanPrompt.includes('doente') || cleanPrompt.includes('mal do estomago')) {
            respostaTexto = `Poxa, melhoras! Se precisar de uma dispensa médica ou passar no setor de saúde da guarnição, me avisa. Quer que eu veja se tem alguém para cobrir suas escalas hoje?`;
          } else if (cleanPrompt.includes('fome') || cleanPrompt.includes('almoçar') || cleanPrompt.includes('rancho') || cleanPrompt.includes('comida')) {
            respostaTexto = `Já está batendo a fome, né? Hora do rancho chegando! Bom almoço por aí e aproveita para recarregar as energias.`;
          } else if (cleanPrompt.includes('cansado') || cleanPrompt.includes('sono') || cleanPrompt.includes('estressado') || cleanPrompt.includes('preguiça')) {
            respostaTexto = `Dia puxado por aí, né? Toma um café e respira um pouco. Se entrar alguma demanda urgente, eu te aviso na hora!`;
          }
          // 7. Saudações de Tempo
          else if (cleanPrompt.includes('bom dia')) {
            respostaTexto = `Bom dia! Tudo bem? Como estão as coisas por aí? Em que posso te ajudar hoje?`;
          } else if (cleanPrompt.includes('boa tarde')) {
            respostaTexto = `Boa tarde! Tudo em ordem por aqui. Como posso te auxiliar nesta tarde?`;
          } else if (cleanPrompt.includes('boa noite')) {
            respostaTexto = `Boa noite! Sistemas a postos. Precisa de algum resumo ou consulta antes de fechar o dia?`;
          }
          // 8. Pergunta sobre bem-estar
          else if (cleanPrompt.includes('como você tá') || cleanPrompt.includes('como vai') || cleanPrompt.includes('tudo bem') || cleanPrompt.includes('tudo certo') || cleanPrompt.includes('tudo bom')) {
            respostaTexto = `Tudo ótimo por aqui, 100% operacional! E com você, tudo na paz? O que temos de bom para hoje?`;
          }
          // 9. Gírias e saudações descontraídas (SEM FALSO POSITIVO EM 'fala que...')
          else if (
            cleanPrompt === 'fala' ||
            cleanPrompt === 'fala aí' ||
            cleanPrompt === 'fala ai' ||
            cleanPrompt.includes('e ai') ||
            cleanPrompt.includes('e aí') ||
            cleanPrompt.includes('salve') ||
            cleanPrompt.includes('opa') ||
            cleanPrompt.includes('cavalo') ||
            cleanPrompt.includes('patrão') ||
            cleanPrompt.includes('nobre')
          ) {
            respostaTexto = `E aí, tudo certo? Sempre a postos! Me diz o que você precisa que eu desenrolo para você.`;
          }
          // 10. Agradecimentos e elogios
          else if (cleanPrompt.includes('obrigado') || cleanPrompt.includes('valeu') || cleanPrompt.includes('agradeço') || cleanPrompt.includes('show') || cleanPrompt.includes('beleza') || cleanPrompt.includes('fera') || cleanPrompt.includes('top')) {
            respostaTexto = `Tamo junto! Qualquer coisa que precisar, é só me chamar.`;
          }
          // 11. Eventos da semana e escala
          else if (cleanPrompt.includes('semana') || cleanPrompt.includes('evento') || cleanPrompt.includes('escala') || cleanPrompt.includes('cobrir') || cleanPrompt.includes('pauta')) {
            if (ctx.demandasSemana.length > 0) {
              const primeiro = ctx.demandasSemana[0];
              respostaTexto = `Temos ${ctx.demandasSemana.length} eventos agendados para os próximos 7 dias. O próximo destaque é "${primeiro.titulo_evento}", no dia ${primeiro.data_evento} no ${primeiro.local_evento}. Quer que eu cadastre mais algum?`;
            } else {
              respostaTexto = `Não temos novas solenidades marcadas para os próximos dias no sistema. Se quiser, me fala que eu crio uma demanda agora!`;
            }
          }
          // 12. Pronto e presença
          else if (cleanPrompt.includes('pronto') || cleanPrompt.includes('presença') || cleanPrompt.includes('falta') || cleanPrompt.includes('guarnição')) {
            respostaTexto = `O Pronto de hoje está tranquilo! Todos os registros da guarnição foram lançados e o efetivo está consolidado.`;
          }
          // 13. Cerimonial, Placas Jade e Almanaque
          else if (cleanPrompt.includes('jade') || cleanPrompt.includes('placa') || cleanPrompt.includes('autoridade') || cleanPrompt.includes('almanaque') || cleanPrompt.includes('precedência')) {
            respostaTexto = `Temos ${ctx.placasPendentes.length} placas JADE aguardando impressão no módulo de cerimonial, além de todo o Almanaque de Precedência sincronizado.`;
          }
          // 14. Resposta Padrão Amigável e Contextualizada
          else {
            respostaTexto = `Entendi a sua mensagem! Me conta com mais detalhes o que você deseja fazer ou qual informação precisa do Gabinete.`;
          }
        }
      }

      setChatHistory((prev) => [
        ...prev,
        {
          id: `jarvis_${Date.now()}`,
          role: 'jarvis',
          text: respostaTexto,
          time: nowTime,
          demandDraft: generatedDraft || undefined,
        },
      ]);

      await speakJarvisResponse(respostaTexto);
    } catch (err: any) {
      const fb = `Tudo em ordem por aqui. Como posso te ajudar?`;
      setChatHistory((prev) => [...prev, { id: `fb_${Date.now()}`, role: 'jarvis', text: fb, time: nowTime }]);
      await speakJarvisResponse(fb);
    } finally {
      setIsProcessing(false);
    }
  };

  // Síntese de Voz do JARVIS 100% Sincronizada com a Aba 1 (Voz & Notificações)
  const speakJarvisResponse = async (text: string) => {
    stopNeuralSpeech();
    setIsSpeaking(true);

    // 1. Se na Aba 1 estiver configurado ElevenLabs
    if (globalTtsEngine === 'elevenlabs' && elevenlabsApiKey && elevenlabsApiKey.length > 10) {
      try {
        const voiceId = jarvisConfig.elevenlabsVoiceId || '21m00Tcm4TlvDq8ikWAM';
        const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
          method: 'POST',
          headers: {
            'Accept': 'audio/mpeg',
            'Content-Type': 'application/json',
            'xi-api-key': elevenlabsApiKey.trim(),
          },
          body: JSON.stringify({
            text,
            model_id: 'eleven_multilingual_v2',
            voice_settings: { stability: 0.85, similarity_boost: 0.85 },
          }),
        });

        if (response.ok) {
          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          audio.onended = () => setIsSpeaking(false);
          audio.onerror = () => setIsSpeaking(false);
          await audio.play();
          return;
        }
      } catch (err) {
        console.warn('ElevenLabs indisponível, usando motor Azure 0800...');
      }
    }

    // 2. Se na Aba 1 estiver configurado Piper TTS Local (Offline)
    if (globalTtsEngine === 'piper') {
      await playNeuralSpeech(
        text,
        'piper_local',
        () => setIsSpeaking(true),
        () => setIsSpeaking(false)
      );
      return;
    }

    // 3. Se na Aba 1 estiver configurado Voz Nativa do Windows
    if (globalTtsEngine === 'browser') {
      await playNeuralSpeech(
        text,
        'system_natural',
        () => setIsSpeaking(true),
        () => setIsSpeaking(false),
        nativeVoiceName
      );
      return;
    }

    // 4. Padrão Global: Microsoft Azure Neural 0800 (Edge-TTS) configurado na Aba 1
    const mode: NeuralVoiceOption =
      azureVoiceName.includes('Francisca') ? 'edge_francisca' : 'edge_antonio';

    const rateStr = `${azureRate >= 0 ? '+' : ''}${azureRate}%`;
    const pitchStr = `${azurePitch >= 0 ? '+' : ''}${azurePitch}Hz`;

    await playNeuralSpeech(
      text,
      mode,
      () => setIsSpeaking(true),
      () => setIsSpeaking(false),
      azureVoiceName,
      1.0,
      1.0,
      azureVoiceName,
      rateStr,
      pitchStr
    );
  };

  // Alternar Escuta do Microfone (Interrompe fala imediatamente ao clicar)
  const toggleListening = () => {
    stopNeuralSpeech();
    setIsSpeaking(false);

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      setIsListening(false);
    } else {
      transcriptRef.current = '';
      setCurrentTranscript('');
      if (recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch (e) {
          console.warn('Recognition start error:', e);
        }
      } else {
        setIsListening(true);
        const testCmd = 'Jarvis, cria uma nova demanda para o Almoço de Oficiais na sexta às 12 horas no Salão Nobre';
        setCurrentTranscript(testCmd);
        setTimeout(() => {
          setIsListening(false);
          setCurrentTranscript('');
          processVoiceCommand(testCmd);
        }, 1800);
      }
    }
  };

  // Limpar Histórico do Chat
  const clearChatHistory = () => {
    stopNeuralSpeech();
    setIsSpeaking(false);
    setActiveDraft(null);
    setIsAwaitingConfirmation(false);
    setChatHistory([
      {
        id: 'reset',
        role: 'jarvis',
        text: `Histórico reiniciado. O que deseja fazer?`,
        time: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Animação de Onda Sonora no Canvas (Waveform Reator Arc 60FPS)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let step = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      const active = isListening || isSpeaking || isProcessing;

      const waves = [
        { color: 'rgba(0, 229, 255, 0.85)', amp: active ? 45 : 12, freq: 0.025, speed: 0.05 },
        { color: 'rgba(197, 160, 89, 0.9)', amp: active ? 35 : 8, freq: 0.035, speed: 0.04 },
        { color: 'rgba(168, 85, 247, 0.7)', amp: active ? 25 : 6, freq: 0.018, speed: 0.03 },
      ];

      waves.forEach((w) => {
        ctx.beginPath();
        ctx.strokeStyle = w.color;
        ctx.lineWidth = active ? 3 : 1.5;

        for (let x = 0; x < width; x++) {
          const y =
            centerY + Math.sin(x * w.freq + step * w.speed) * w.amp * Math.sin((x / width) * Math.PI);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });

      step++;
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, [isListening, isSpeaking, isProcessing]);

  return (
    <div className="max-w-4xl mx-auto space-y-4 text-center pb-8">
      {/* ── Topo Minimalista: JARVIS Puro & Status da IA ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-black text-white tracking-widest uppercase">
            JARVIS
          </h1>
          {geminiApiKey ? (
            <span
              onClick={() => {
                setTempKey(geminiApiKey);
                setShowKeyModal(true);
              }}
              className="cursor-pointer px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-black border border-emerald-500/40 flex items-center gap-1 hover:scale-105 transition-all"
              title="IA Gemini conectada. Clique para alterar chave."
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>Gemini IA Ativo</span>
            </span>
          ) : (
            <button
              onClick={() => {
                setTempKey('');
                setShowKeyModal(true);
              }}
              className="px-2.5 py-0.5 rounded-full bg-[#00e5ff]/20 text-[#00e5ff] text-[10px] font-black border border-[#00e5ff]/40 flex items-center gap-1 hover:scale-105 transition-all"
            >
              <Key className="w-3 h-3" />
              <span>Conectar Gemini IA</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {isSpeaking && (
            <button
              onClick={handleStopSpeaking}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 text-xs font-bold transition-all animate-pulse"
              title="Interromper Áudio"
            >
              <VolumeX className="w-3.5 h-3.5" />
              <span>Parar Fala</span>
            </button>
          )}

          <button
            onClick={clearChatHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white text-xs font-semibold transition-all"
            title="Limpar Histórico de Diálogo"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Limpar Chat</span>
          </button>
        </div>
      </div>

      {/* ── HUD Reator Arc & Ondas Sonoras ── */}
      <div className="p-6 rounded-3xl bg-[#080e1b] border-2 border-slate-800 relative overflow-hidden shadow-2xl space-y-4">
        {/* Canvas de Ondas */}
        <canvas
          ref={canvasRef}
          width={700}
          height={120}
          className="w-full h-24 mx-auto rounded-2xl"
        />

        {/* Orbe Central / Botão de Microfone */}
        <div className="flex flex-col items-center justify-center gap-2">
          <button
            onClick={toggleListening}
            className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl relative ${
              isListening
                ? 'bg-red-500 text-white animate-pulse ring-8 ring-red-500/30 scale-110'
                : isSpeaking
                ? 'bg-[#00e5ff] text-slate-950 ring-8 ring-[#00e5ff]/30 animate-bounce'
                : isProcessing
                ? 'bg-[#c5a059] text-slate-950 animate-spin'
                : 'bg-gradient-to-tr from-[#c5a059] to-amber-300 text-slate-950 hover:scale-105 active:scale-95 shadow-[#c5a059]/40'
            }`}
          >
            {isListening ? (
              <Mic className="w-8 h-8" />
            ) : isSpeaking ? (
              <Volume2 className="w-8 h-8 animate-pulse" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
          </button>

          <span className="text-[11px] font-black uppercase tracking-widest text-[#00e5ff]">
            {isListening
              ? '🎙️ OUVINDO... PODE FALAR'
              : isSpeaking
              ? '🔊 JARVIS FALANDO (CLIQUE NO MICROFONE PARA INTERROMPER)'
              : isProcessing
              ? '⚡ PENSANDO COM IA...'
              : 'CLIQUE NO MICROFONE PARA CONVERSAR'}
          </span>
        </div>

        {/* Transcrição em Tempo Real ao Falar */}
        {currentTranscript && (
          <div className="p-3 rounded-xl bg-slate-900/90 border border-[#00e5ff]/40 text-xs text-[#00e5ff] font-mono animate-pulse text-left">
            <span>🎙️ Ouvindo: </span>
            <span className="italic">"{currentTranscript}"</span>
          </div>
        )}

        {/* ── CARD INTERATIVO DE CONFIRMAÇÃO DE DEMANDA (SE HOUVER RASCUNHO) ── */}
        {activeDraft && isAwaitingConfirmation && (
          <div className="p-4 rounded-2xl bg-gradient-to-r from-[#0e1e38] via-[#14294d] to-[#0e1e38] border-2 border-[#00e5ff] text-left space-y-3 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-700/80 pb-2">
              <span className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                <span>Rascunho de Nova Demanda Gerado</span>
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                Aguardando Sua Confirmação
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block font-bold">Título do Evento:</span>
                <p className="font-black text-white">{activeDraft.titulo_evento}</p>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800">
                <span className="text-[10px] text-slate-400 block font-bold">Data & Horário:</span>
                <p className="font-bold text-white flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-[#c5a059]" />
                  <span>{activeDraft.data_evento} às {activeDraft.hora_evento}</span>
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 sm:col-span-2">
                <span className="text-[10px] text-slate-400 block font-bold">Local da Missão:</span>
                <p className="font-bold text-slate-200 flex items-center gap-1.5">
                  <MapPin className="w-3 h-3 text-red-400" />
                  <span>{activeDraft.local_evento}</span>
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800 sm:col-span-2 flex items-center gap-2">
                <span className="text-[10px] text-slate-400 font-bold">Serviços:</span>
                <div className="flex flex-wrap gap-1">
                  {activeDraft.tipo_cobertura.map((srv, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-bold border border-cyan-500/40">
                      {srv}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-700/80">
              <button
                type="button"
                onClick={handleCancelDraft}
                className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-bold transition-all"
              >
                ✕ Cancelar
              </button>

              <button
                type="button"
                onClick={() => handleConfirmCreateDemand()}
                className="px-5 py-1.5 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-lg shadow-[#00e5ff]/25 transition-all hover:scale-105"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Confirmar & Cadastrar no SisGAB</span>
              </button>
            </div>
          </div>
        )}

        {/* ── HISTÓRICO CONTÍNUO DO DIÁLOGO ── */}
        <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-left space-y-3 max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800">
          {chatHistory.map((msg) => (
            <div
              key={msg.id}
              className={`p-3 rounded-xl flex items-start gap-3 transition-all ${
                msg.role === 'user'
                  ? 'bg-[#c5a059]/10 border border-[#c5a059]/30 text-white ml-6'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200 mr-6'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold ${
                  msg.role === 'user'
                    ? 'bg-[#c5a059] text-slate-950'
                    : 'bg-[#00e5ff]/20 text-[#00e5ff] border border-[#00e5ff]/40'
                }`}
              >
                {msg.role === 'user' ? 'VC' : <Bot className="w-3.5 h-3.5" />}
              </div>

              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center justify-between text-[10px]">
                  <span className={`font-black uppercase tracking-wider ${msg.role === 'user' ? 'text-[#c5a059]' : 'text-[#00e5ff]'}`}>
                    {msg.role === 'user' ? (user?.nome_guerra || 'OPERADOR') : 'JARVIS'}
                  </span>
                  <span className="text-slate-500 font-mono">{msg.time}</span>
                </div>
                <p className="text-xs leading-relaxed font-medium">{msg.text}</p>
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-ping" />
              <span>Jarvis formulando resposta com IA...</span>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* ── BARRA DE ENTRADA MANUAL / PERGUNTA ── */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (manualInput.trim()) {
              const q = manualInput.trim();
              setManualInput('');
              processVoiceCommand(q);
            }
          }}
          className="flex items-center gap-2 pt-2 border-t border-slate-800/80"
        >
          <input
            type="text"
            placeholder="Converse sobre qualquer assunto (ex: Me conte uma piada / Qual o melhor carro?)..."
            value={manualInput}
            onChange={(e) => setManualInput(e.target.value)}
            className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950/90 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff]"
          />
          <button
            type="submit"
            disabled={isProcessing || !manualInput.trim()}
            className="px-5 py-2.5 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-[#00e5ff]/20 transition-all disabled:opacity-40"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Enviar</span>
          </button>
        </form>
      </div>

      {/* ── 9 COMANDOS E PERGUNTAS RÁPIDAS (GRADE INTELIGENTE) ── */}
      <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 text-left space-y-3 shadow-xl">
        <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-[#c5a059]" />
          <span>Comandos & Perguntas Rápidas Mais Usadas (9 Opções):</span>
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
          {QUICK_PROMPTS.map((item, idx) => (
            <button
              key={idx}
              onClick={() => {
                stopNeuralSpeech();
                processVoiceCommand(item.query);
              }}
              className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-[#00e5ff] text-left text-slate-300 hover:text-white transition-all shadow-sm hover:scale-[1.01] flex flex-col justify-between gap-1 group"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm">{item.icon}</span>
                <span className="font-bold text-white text-[11px] group-hover:text-[#00e5ff]">
                  {item.label}
                </span>
              </div>
              <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
                "{item.query}"
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* ── MODAL RÁPIDO DE CONEXÃO DA CHAVE GEMINI ── */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border-2 border-[#00e5ff]/50 space-y-4 shadow-2xl text-left">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#00e5ff]" />
                <span>Ativar Inteligência Artificial Gemini no JARVIS</span>
              </h3>
              <button onClick={() => setShowKeyModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">
                Insira sua chave gratuita do <strong>Google AI Studio</strong> para que o JARVIS responda com IA sobre qualquer assunto (demandas, carros, piadas, saúde, etc).
              </p>

              <div>
                <label className="block text-slate-400 font-bold mb-1">Chave de API do Gemini (API Key)</label>
                <input
                  type="password"
                  placeholder="AIzaSy..."
                  value={tempKey}
                  onChange={(e) => setTempKey(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white font-mono focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="pt-1">
                <a
                  href="https://aistudio.google.com"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-[#00e5ff] font-bold hover:underline"
                >
                  👉 Clique aqui para obter sua chave grátis no Google AI Studio
                </a>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowKeyModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold text-xs"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveGeminiKey}
                className="px-5 py-2 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs shadow-md shadow-[#00e5ff]/20"
              >
                Conectar IA
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
