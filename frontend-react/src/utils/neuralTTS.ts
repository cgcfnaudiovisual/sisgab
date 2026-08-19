/**
 * neuralTTS.ts
 * Motor de Síntese de Voz Neural 100% Gratuito (0800) e Ilimitado
 * Suporta:
 * 1. Microsoft Edge Neural 0800 (pt-BR-AntonioNeural - Jarvis Ultra-Realista / pt-BR-FranciscaNeural - Suave)
 * 2. Piper TTS Neural Local (pt_BR-faber-medium - Jarvis 100% Offline)
 * 3. Microsoft Edge / Windows Natural Voices
 * 4. Google Neural Stream 0800
 */

export type NeuralVoiceOption =
  | 'edge_antonio'
  | 'edge_francisca'
  | 'piper_local'
  | 'antonio_neural'
  | 'francisca_neural'
  | 'google_neural'
  | 'system_natural';

let currentActiveAudio: HTMLAudioElement | null = null;
let cachedVoices: SpeechSynthesisVoice[] = [];

function initVoices() {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    cachedVoices = window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => {
      cachedVoices = window.speechSynthesis.getVoices();
    };
  }
}
initVoices();

export function getAvailablePortugueseVoices(): SpeechSynthesisVoice[] {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return [];
  if (cachedVoices.length === 0) {
    cachedVoices = window.speechSynthesis.getVoices();
  }
  return cachedVoices.filter(
    (v) => v.lang.toLowerCase().includes('pt') || v.lang.toLowerCase().includes('por')
  );
}

export function stopNeuralSpeech(): void {
  if (currentActiveAudio) {
    try {
      currentActiveAudio.pause();
      currentActiveAudio.currentTime = 0;
    } catch (e) {}
    currentActiveAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch (e) {}
  }
}

/**
 * Tenta reproduzir com voz neural com controle de velocidade, tom e seleção específica
 */
export async function playNeuralSpeech(
  text: string,
  voice: NeuralVoiceOption = 'edge_antonio',
  onStart?: () => void,
  onEnd?: () => void,
  customVoiceName?: string,
  rate: number = 1.0,
  pitch: number = 1.0,
  azureVoiceName?: string,
  azureRateStr?: string,
  azurePitchStr?: string
): Promise<void> {
  stopNeuralSpeech();

  if (!text || !text.trim()) {
    onEnd?.();
    return;
  }

  const cleanText = text.replace(/[*#_~`]/g, '').trim();

  // 1. Prioridade 1: Servidor Local (Edge Neural 0800 Ultra-Realista ou Piper Offline)
  try {
    const engineMap =
      voice === 'edge_francisca' || voice === 'francisca_neural'
        ? 'edge_francisca'
        : voice === 'piper_local'
        ? 'piper_local'
        : 'edge_antonio';

    const selectedAzureVoice =
      azureVoiceName ||
      (customVoiceName && customVoiceName.startsWith('pt-BR-') ? customVoiceName : undefined) ||
      (engineMap === 'edge_francisca' ? 'pt-BR-FranciscaNeural' : 'pt-BR-AntonioNeural');

    const response = await fetch('http://127.0.0.1:5005/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: cleanText,
        engine: engineMap,
        voice: selectedAzureVoice,
        rate: azureRateStr || '+0%',
        pitch: azurePitchStr || '+0Hz',
      }),
    });

    if (response.ok) {
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      currentActiveAudio = audio;

      audio.onplay = () => onStart?.();
      audio.onended = () => {
        currentActiveAudio = null;
        onEnd?.();
      };
      audio.onerror = () => {
        currentActiveAudio = null;
        fallbackToBrowserSpeech(cleanText, voice, onStart, onEnd, customVoiceName, rate, pitch);
      };

      const p = audio.play();
      if (p !== undefined) {
        p.catch(() => {
          fallbackToBrowserSpeech(cleanText, voice, onStart, onEnd, customVoiceName, rate, pitch);
        });
      }
      return;
    }
  } catch (err) {
    console.warn('[TTS] Servidor local 5005 offline, usando sintetizador nativo...', err);
  }

  fallbackToBrowserSpeech(cleanText, voice, onStart, onEnd, customVoiceName, rate, pitch);
}

function fallbackToBrowserSpeech(
  cleanText: string,
  voice: NeuralVoiceOption,
  onStart?: () => void,
  onEnd?: () => void,
  customVoiceName?: string,
  rate: number = 1.0,
  pitch: number = 1.0
) {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    let voices = window.speechSynthesis.getVoices();
    if (voices.length === 0 && cachedVoices.length > 0) {
      voices = cachedVoices;
    }

    let selectedVoice: SpeechSynthesisVoice | undefined;

    if (customVoiceName) {
      selectedVoice = voices.find((v) => v.name === customVoiceName);
    }

    if (!selectedVoice) {
      const ptVoices = voices.filter(
        (v) => v.lang.toLowerCase().includes('pt') || v.lang.toLowerCase().includes('por')
      );

      if (voice === 'edge_francisca' || voice === 'francisca_neural') {
        selectedVoice =
          ptVoices.find((v) => v.name.includes('Francisca') || v.name.includes('Female')) ||
          ptVoices.find((v) => v.name.includes('Natural') && v.name.includes('Online')) ||
          ptVoices[0];
      } else {
        selectedVoice =
          ptVoices.find((v) => v.name.includes('Antonio') || v.name.includes('Male')) ||
          ptVoices.find((v) => v.name.includes('Natural') && v.name.includes('Online')) ||
          ptVoices[0];
      }
    }

    if (selectedVoice) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.voice = selectedVoice;
      utterance.lang = selectedVoice.lang || 'pt-BR';
      utterance.rate = rate;
      utterance.pitch = pitch;

      utterance.onstart = () => onStart?.();
      utterance.onend = () => onEnd?.();
      utterance.onerror = () => onEnd?.();

      window.speechSynthesis.speak(utterance);
      return;
    }
  }

  // Fallback Google Stream 0800
  try {
    const encoded = encodeURIComponent(cleanText.slice(0, 200));
    const audioUrl = `https://translate.google.com/translate_tts?ie=UTF-8&tl=pt-BR&client=tw-ob&q=${encoded}`;
    const audio = new Audio(audioUrl);
    currentActiveAudio = audio;
    audio.onplay = () => onStart?.();
    audio.onended = () => {
      currentActiveAudio = null;
      onEnd?.();
    };
    audio.onerror = () => {
      currentActiveAudio = null;
      onEnd?.();
    };
    audio.play();
  } catch (e) {
    onEnd?.();
  }
}
