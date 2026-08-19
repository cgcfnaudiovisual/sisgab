import { supabase } from '../api/supabase';

interface VoiceNotificationOptions {
  titulo: string;
  solicitante?: string;
  dataHora?: string;
  tipo?: 'nova_pauta' | 'pauta_aprovada' | 'missao_urgente' | 'aviso_geral';
}

/**
 * Monta a frase concisa e militar para o anúncio por voz
 */
export function buildVoiceAnnouncementText(options: VoiceNotificationOptions): string {
  const { titulo, solicitante, dataHora, tipo = 'nova_pauta' } = options;

  switch (tipo) {
    case 'nova_pauta':
      return `Atenção Gabinete. Nova pauta solicitada: ${titulo}. Solicitante: ${solicitante || 'CGCFN'}.`;
    case 'pauta_aprovada':
      return `Pauta homologada: ${titulo}. Equipe em prontidão.`;
    case 'missao_urgente':
      return `Alerta Operacional. Missão rápida lançada: ${titulo}.`;
    case 'aviso_geral':
      return `Comunicado do Gabinete: ${titulo}.`;
    default:
      return `Atualização no SisGAB: ${titulo}.`;
  }
}

/**
 * Tenta reproduzir a síntese de voz usando ElevenLabs (se configurado) ou Voz Neural Natural do Navegador
 */
export async function speakVoiceNotification(options: VoiceNotificationOptions): Promise<void> {
  const textToSpeak = buildVoiceAnnouncementText(options);

  try {
    // 1. Verifica se há chave do ElevenLabs salva no Supabase (config)
    const { data: cfgList } = await supabase
      .from('config')
      .select('chave, valor')
      .in('chave', ['elevenlabs_api_key', 'elevenlabs_voice_id', 'voice_alerts_enabled']);

    const isEnabled = cfgList?.find((c) => c.chave === 'voice_alerts_enabled')?.valor !== 'false';
    if (!isEnabled) {
      return; // Desativado pelo usuário
    }

    const elevenKey = cfgList?.find((c) => c.chave === 'elevenlabs_api_key')?.valor;
    const elevenVoice = cfgList?.find((c) => c.chave === 'elevenlabs_voice_id')?.valor || 'N2lVS1w4EtoT3dr4eOWO';

    // 2. Se houver chave válida do ElevenLabs, faz a requisição direta de alta fidelidade
    if (elevenKey && elevenKey.length > 10 && !elevenKey.includes('***')) {
      const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${elevenVoice}`, {
        method: 'POST',
        headers: {
          'Accept': 'audio/mpeg',
          'Content-Type': 'application/json',
          'xi-api-key': elevenKey,
        },
        body: JSON.stringify({
          text: textToSpeak,
          model_id: 'eleven_multilingual_v2',
          voice_settings: {
            stability: 0.85,
            similarity_boost: 0.85,
          },
        }),
      });

      if (response.ok) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        await audio.play();
        return;
      }
    }
  } catch (err) {
    console.warn('[VOICE] ElevenLabs falhou ou não configurado, usando voz neural do navegador:', err);
  }

  // 3. Fallback: Voz Neural de Alta Fidelidade Nativa do Navegador (PT-BR)
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel(); // Para qualquer fala anterior
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = 'pt-BR';
    utterance.rate = 1.05;
    utterance.pitch = 0.95;

    // Seleciona a melhor voz natural instalada (ex: Google, Microsoft Antonio/Francisca ou Luciana)
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(
      (v) =>
        v.lang.includes('pt') &&
        (v.name.includes('Natural') ||
          v.name.includes('Google') ||
          v.name.includes('Lucio') ||
          v.name.includes('Francisca') ||
          v.name.includes('Antonio'))
    ) || voices.find((v) => v.lang.includes('pt'));

    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    window.speechSynthesis.speak(utterance);
  }
}
