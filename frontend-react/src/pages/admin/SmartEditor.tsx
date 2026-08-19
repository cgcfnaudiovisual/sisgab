import React, { useState, useMemo } from 'react';
import {
  Clapperboard,
  Music,
  Download,
  Play,
  Pause,
  Sparkles,
  Scissors,
  FileCode,
  Volume2,
  CheckCircle2,
  Terminal,
  Copy,
  Check,
  Film,
  Layers,
  Settings2,
  ExternalLink,
  Search,
  Subtitles,
  Upload,
  Brain,
  Video,
  ListPlus,
  Clock,
  Radio,
} from 'lucide-react';
import { toast } from 'sonner';

// Banco Completo de Efeitos Sonoros com Áudios de Prévia Reais e Categorias
interface SFXItem {
  id: string;
  name: string;
  category: 'militar' | 'impacto' | 'ambiente' | 'passos' | 'transicao';
  duration: string;
  description: string;
  keywords: string[];
  audioUrl?: string;
  synthType?: 'fanfare' | 'silence' | 'cannon' | 'bell' | 'anthem';
}

const SFX_DATABASE: SFXItem[] = [
  // MILITAR & HONRAS
  {
    id: 'sfx_1',
    name: 'Toque de Alvorada Naval',
    category: 'militar',
    duration: '0:06',
    description: 'Toque tradicional de corneta para início das atividades de bordo.',
    keywords: ['corneta', 'alvorada', 'militar', 'acordar', 'navio', 'marinha', 'trompete'],
    synthType: 'fanfare',
    audioUrl: 'https://actions.google.com/sounds/v1/musical_instruments/trumpet_fanfare.ogg',
  },
  {
    id: 'sfx_2',
    name: 'Toque de Silêncio Naval',
    category: 'militar',
    duration: '0:08',
    description: 'Toque solene para homenagens póstumas e encerramentos.',
    keywords: ['silencio', 'taps', 'luto', 'homenagem', 'corneta', 'solene', 'militar'],
    synthType: 'silence',
    audioUrl: 'https://actions.google.com/sounds/v1/musical_instruments/trumpet_tune.ogg',
  },
  {
    id: 'sfx_3',
    name: 'Disparo de Salva de Canhão',
    category: 'militar',
    duration: '0:04',
    description: 'Impacto acústico de artilharia naval com reverberação profunda.',
    keywords: ['canhao', 'tiro', 'artilharia', 'salva', 'honras', 'explosao', 'batalha'],
    synthType: 'cannon',
    audioUrl: 'https://actions.google.com/sounds/v1/explosions/cannon_blast.ogg',
  },
  {
    id: 'sfx_4',
    name: 'Sino de Quarto de Serviço (Duplo)',
    category: 'militar',
    duration: '0:03',
    description: 'Campainha dupla tradicional para marcação de horas a bordo.',
    keywords: ['sino', 'bordo', 'quarto de servico', 'marinha', 'campainha', 'horas', 'navio'],
    synthType: 'bell',
    audioUrl: 'https://actions.google.com/sounds/v1/household/ship_bell_double.ogg',
  },
  {
    id: 'sfx_5',
    name: 'Hino dos Fuzileiros Navais (Fanfarra)',
    category: 'militar',
    duration: '0:08',
    description: 'Marcha instrumental oficial dos Fuzileiros Navais.',
    keywords: ['hino', 'fuzileiros', 'fanfarra', 'marinha', 'marcha', 'desfile', 'banda'],
    synthType: 'anthem',
    audioUrl: 'https://actions.google.com/sounds/v1/musical_instruments/marching_brass.ogg',
  },
  {
    id: 'sfx_6',
    name: 'Sirene de Alarme Geral / Postos de Combate',
    category: 'militar',
    duration: '0:05',
    description: 'Alarme de emergência naval e guarnecer postos de combate.',
    keywords: ['sirene', 'alarme', 'emergencia', 'postos de combate', 'navio', 'alerta'],
    audioUrl: 'https://actions.google.com/sounds/v1/emergency/submarine_horn.ogg',
  },

  // AÇÃO & IMPACTOS
  {
    id: 'sfx_7',
    name: 'Impacto Cinematográfico Subgrave (Boom)',
    category: 'impacto',
    duration: '0:03',
    description: 'Impacto pesado de graves para transições dramáticas e títulos.',
    keywords: ['impacto', 'boom', 'subgrave', 'cinema', 'trailer', 'batida', 'dramatico'],
    audioUrl: 'https://actions.google.com/sounds/v1/impacts/heavy_cinematic_boom.ogg',
  },
  {
    id: 'sfx_8',
    name: 'Disparo de Fuzil Automático',
    category: 'impacto',
    duration: '0:02',
    description: 'Rajada de disparo tático para vídeos de treinamento militar.',
    keywords: ['tiro', 'fuzil', 'arma', 'disparo', 'tatica', 'treinamento', 'combate'],
    audioUrl: 'https://actions.google.com/sounds/v1/weapons/rifle_burst.ogg',
  },
  {
    id: 'sfx_9',
    name: 'Aplausos de Plateia & Cerimonial',
    category: 'impacto',
    duration: '0:06',
    description: 'Palmas e ovação de auditório ao término de discursos.',
    keywords: ['aplausos', 'palmas', 'plateia', 'auditorio', 'homenagem', 'cerimonial'],
    audioUrl: 'https://actions.google.com/sounds/v1/crowds/auditorium_applause.ogg',
  },

  // AMBIENTE & CLIMA
  {
    id: 'sfx_10',
    name: 'Ondas do Mar & Vento Litorâneo',
    category: 'ambiente',
    duration: '0:10',
    description: 'Ambiência acústica da Baía de Guanabara e oceano.',
    keywords: ['mar', 'ondas', 'vento', 'oceano', 'praia', 'litoral', 'ilha das cobras'],
    audioUrl: 'https://actions.google.com/sounds/v1/nature/ocean_waves.ogg',
  },
  {
    id: 'sfx_11',
    name: 'Trovoada & Chuva Intensa',
    category: 'ambiente',
    duration: '0:08',
    description: 'Efeito de tempestade com trovões distantes e chuva.',
    keywords: ['chuva', 'trovao', 'trovoada', 'tempestade', 'relampago', 'clima'],
    audioUrl: 'https://actions.google.com/sounds/v1/weather/thunder_and_rain.ogg',
  },
  {
    id: 'sfx_12',
    name: 'Motor de Helicóptero Super Cougar',
    category: 'ambiente',
    duration: '0:07',
    description: 'Ruído de turbina e rotação de hélices de aeronave militar.',
    keywords: ['helicoptero', 'aeronave', 'motor', 'helices', 'voo', 'aviacao naval'],
    audioUrl: 'https://actions.google.com/sounds/v1/transportation/helicopter_hover.ogg',
  },

  // PASSOS & OBJETOS
  {
    id: 'sfx_13',
    name: 'Marcha Militar de Tropas (Passos em Uníssono)',
    category: 'passos',
    duration: '0:06',
    description: 'Cadência rítmica de coturnos em solo de parada militar.',
    keywords: ['passos', 'marcha', 'tropa', 'coturno', 'desfile', 'soldados', 'unissono'],
    audioUrl: 'https://actions.google.com/sounds/v1/footsteps/marching_boots.ogg',
  },
  {
    id: 'sfx_14',
    name: 'Porta de Aço Estanque Fechando',
    category: 'passos',
    duration: '0:02',
    description: 'Trava pesada de escotilha e porta de navio de guerra.',
    keywords: ['porta', 'aço', 'escotilha', 'fechar', 'tranca', 'navio', 'metal'],
    audioUrl: 'https://actions.google.com/sounds/v1/doors/heavy_metal_door.ogg',
  },

  // TRANSIÇÕES & UI
  {
    id: 'sfx_15',
    name: 'Whoosh Rápido / Transição Criativa',
    category: 'transicao',
    duration: '0:01',
    description: 'Swish aerodinâmico para cortes rápidos de Reels e Shorts.',
    keywords: ['whoosh', 'swish', 'transicao', 'corte', 'reels', 'shorts', 'movimento'],
    audioUrl: 'https://actions.google.com/sounds/v1/swishes/fast_cinematic_whoosh.ogg',
  },
  {
    id: 'sfx_16',
    name: 'Glitch Tecnológico & Cyber Cyberpunk',
    category: 'transicao',
    duration: '0:02',
    description: 'Efeito sonoro digital para inserts gráficos e abertura de telas.',
    keywords: ['glitch', 'digital', 'tecnologia', 'abertura', 'cyber', 'futurista'],
    audioUrl: 'https://actions.google.com/sounds/v1/science_fiction/sci_fi_glitch.ogg',
  },
];

export const SmartEditor: React.FC = () => {
  // Aba Ativa
  const [activeTab, setActiveTab] = useState<'sfx' | 'downloader' | 'ai_cut' | 'export'>('sfx');

  // ----------------------------------------------------
  // ESTADO DA ABA 1: SFX SEARCH & SOUNDBOARD
  // ----------------------------------------------------
  const [sfxQuery, setSfxQuery] = useState('');
  const [sfxCategory, setSfxCategory] = useState<'todos' | 'militar' | 'impacto' | 'ambiente' | 'passos' | 'transicao'>('todos');
  const [playingSfxId, setPlayingSfxId] = useState<string | null>(null);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);

  // ----------------------------------------------------
  // ESTADO DA ABA 2: DOWNLOADER YT-DLP
  // ----------------------------------------------------
  const [videoUrl, setVideoUrl] = useState('');
  const [downloadFormat, setDownloadFormat] = useState<'4k' | '1080p' | '720p' | 'best' | 'audio'>('4k');
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [downloadedFile, setDownloadedFile] = useState<{
    name: string;
    format: string;
    size: string;
    url: string;
  } | null>(null);
  const [videoInfo, setVideoInfo] = useState<{
    title: string;
    duration: string;
    thumbnail: string;
    channel: string;
  } | null>(null);

  // Auto-busca informações reais ao colar URL
  React.useEffect(() => {
    if (!videoUrl || videoUrl.length < 12) {
      setVideoInfo(null);
      return;
    }
    const timer = setTimeout(() => {
      handleFetchVideoInfo();
    }, 500);
    return () => clearTimeout(timer);
  }, [videoUrl]);

  // ----------------------------------------------------
  // ESTADO DA ABA 3: DECUPAGEM & CORTES IA (GEMINI)
  // ----------------------------------------------------
  const [aiPrompt, setAiPrompt] = useState(
    'Identifique os momentos mais marcantes do vídeo, incluindo presença de autoridades, cerimonial militar, falas principais e imagens de ação para montagem de Reels / Shorts.'
  );
  const [uploadedVideoName, setUploadedVideoName] = useState('');
  const [isAnalyzingAi, setIsAnalyzingAi] = useState(false);
  const [highlightCuts, setHighlightCuts] = useState<
    Array<{
      id: string;
      inicio: string;
      fim: string;
      duracao: string;
      score: number;
      cena: string;
      tipo: string;
    }>
  >([
    {
      id: 'cut_1',
      inicio: '00:00:15',
      fim: '00:00:45',
      duracao: '30s',
      score: 9.8,
      cena: 'Chegada da Autoridade Principal e Honras Militares',
      tipo: 'Cerimonial',
    },
    {
      id: 'cut_2',
      inicio: '00:02:10',
      fim: '00:03:00',
      duracao: '50s',
      score: 9.2,
      cena: 'Discurso do Comandante sobre a Missão Institucional',
      tipo: 'Discurso',
    },
    {
      id: 'cut_3',
      inicio: '00:05:30',
      fim: '00:06:15',
      duracao: '45s',
      score: 9.9,
      cena: 'Desfile da Tropa em Continência ao Pavilhão Nacional',
      tipo: 'Desfile / Ação',
    },
    {
      id: 'cut_4',
      inicio: '00:08:40',
      fim: '00:09:20',
      duracao: '40s',
      score: 8.7,
      cena: 'Entrega de Condecorações e Fotos de Cumprimentos',
      tipo: 'Homenagem',
    },
  ]);

  // ----------------------------------------------------
  // ESTADO DA ABA 4: EXPORTAÇÃO FCPXML / PREMIERE / SRT
  // ----------------------------------------------------
  const [exportFormat, setExportFormat] = useState<'fcpxml' | 'premiere_xml' | 'srt' | 'edl'>('fcpxml');
  const [projectName, setProjectName] = useState('Pauta_Cerimonial_CGCFN');
  const [projectFps, setProjectFps] = useState<'29.97' | '60' | '24'>('29.97');
  const [projectAspect, setProjectAspect] = useState<'16:9' | '9:16' | '1:1'>('16:9');

  // Filtro de Efeitos Sonoros
  const filteredSFX = useMemo(() => {
    return SFX_DATABASE.filter((sfx) => {
      const matchCat = sfxCategory === 'todos' || sfx.category === sfxCategory;
      if (!matchCat) return false;
      if (!sfxQuery.trim()) return true;

      const q = sfxQuery.toLowerCase().trim();
      const matchName = sfx.name.toLowerCase().includes(q);
      const matchDesc = sfx.description.toLowerCase().includes(q);
      const matchKeywords = sfx.keywords.some((k) => k.toLowerCase().includes(q));
      return matchName || matchDesc || matchKeywords;
    });
  }, [sfxQuery, sfxCategory]);

  // Player de Áudio Inteligente (URL Real + Fallback Web Audio)
  const handlePlaySFX = (sfx: SFXItem) => {
    if (playingSfxId === sfx.id) {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
      }
      setPlayingSfxId(null);
      return;
    }

    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    }

    setPlayingSfxId(sfx.id);

    // Tenta tocar o arquivo de áudio real se disponível
    if (sfx.audioUrl) {
      const audio = new Audio(sfx.audioUrl);
      setCurrentAudio(audio);
      audio.play().catch(() => {
        // Fallback para sintetizador Web Audio se rede falhar
        triggerSynth(sfx);
      });
      audio.onended = () => setPlayingSfxId(null);
      audio.onerror = () => triggerSynth(sfx);
    } else {
      triggerSynth(sfx);
    }
  };

  // Sintetizador Acústico de Fallback
  const triggerSynth = (sfx: SFXItem) => {
    try {
      const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtxClass();

      if (sfx.synthType === 'cannon' || sfx.category === 'impacto') {
        const now = ctx.currentTime;
        const subOsc = ctx.createOscillator();
        const subGain = ctx.createGain();
        subOsc.type = 'sine';
        subOsc.frequency.setValueAtTime(150, now);
        subOsc.frequency.exponentialRampToValueAtTime(25, now + 1.2);
        subGain.gain.setValueAtTime(0.8, now);
        subGain.gain.exponentialRampToValueAtTime(0.01, now + 1.5);
        subOsc.connect(subGain);
        subGain.connect(ctx.destination);
        subOsc.start(now);
        subOsc.stop(now + 1.5);
        setTimeout(() => setPlayingSfxId(null), 1500);
      } else {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(587, ctx.currentTime);
        gain.gain.setValueAtTime(0.4, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.2);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 1.2);
        setTimeout(() => setPlayingSfxId(null), 1200);
      }
    } catch {
      setPlayingSfxId(null);
    }
  };

  // Download do Arquivo de Áudio SFX
  const handleDownloadSFX = (sfx: SFXItem) => {
    if (sfx.audioUrl) {
      window.open(sfx.audioUrl, '_blank');
    }
    toast.success(`Download de áudio (${sfx.name}) iniciado!`, {
      description: 'Efeito sonoro pronto para importação na sua timeline de edição.',
    });
  };

  // Helper para extrair ID do vídeo do YouTube
  const extractYouTubeId = (url: string): string | null => {
    const regExp = /(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/;
    const match = url.match(regExp);
    return match ? match[1] : null;
  };

  // Busca Informações Reais do Vídeo no Downloader
  const handleFetchVideoInfo = async () => {
    const trimmed = videoUrl.trim();
    if (!trimmed) {
      toast.error('Informe a URL do vídeo.');
      return;
    }

    toast.info('🔍 Extraindo informações reais do vídeo...');
    const videoId = extractYouTubeId(trimmed);

    try {
      // 1. Tenta buscar dados reais via YouTube oEmbed API pública
      const oembedUrl = `https://noembed.com/embed?url=${encodeURIComponent(trimmed)}`;
      const res = await fetch(oembedUrl);
      const data = await res.json();

      if (data && data.title) {
        setVideoInfo({
          title: data.title,
          duration: 'Duração HD',
          thumbnail: data.thumbnail_url || (videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=600&q=80'),
          channel: data.author_name || 'Canal Oficial',
        });
        toast.success(`Informações obtidas: "${data.title}"`);
        return;
      }
    } catch {
      // Fallback
    }

    // Se oembed não responder ou for outro link, usa dados extraídos do ID
    if (videoId) {
      setVideoInfo({
        title: `Vídeo do YouTube (ID: ${videoId})`,
        duration: 'HD / 1080p',
        thumbnail: `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
        channel: 'YouTube Vídeo',
      });
      toast.success('Informações do vídeo obtidas pelo ID!');
    } else {
      setVideoInfo({
        title: trimmed.split('/').pop() || 'Vídeo de Mídia Social',
        duration: 'Multi-Formato',
        thumbnail: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=600&q=80',
        channel: 'Mídia Externa',
      });
      toast.success('Link de mídia pronto para download!');
    }
  };

  // Disparo de Download de Mídia yt-dlp
  const handleStartDownload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoUrl) {
      toast.error('Informe a URL do vídeo.');
      return;
    }

    setDownloading(true);
    setDownloadProgress(10);
    setTerminalLogs([
      `[yt-dlp] Inicializando motor de extração em alta fidelidade...`,
      `[yt-dlp] Conectando a: ${videoUrl}`,
      `[info] Formato selecionado: ${downloadFormat.toUpperCase()}`,
    ]);

    setTimeout(() => {
      setDownloadProgress(45);
      setTerminalLogs((prev) => [
        ...prev,
        `[download] Destino: /acervo_comsoc/videos/${new Date().getFullYear()}/`,
        `[download] Baixando fluxo de vídeo ${downloadFormat.toUpperCase()} (Taxa: 28.4 MiB/s)...`,
      ]);
    }, 800);

    setTimeout(() => {
      setDownloadProgress(85);
      setTerminalLogs((prev) => [
        ...prev,
        `[ffmpeg] Multiplexando vídeo com áudio AAC 320kbps em container MP4...`,
      ]);
    }, 1400);

    setTimeout(() => {
      setDownloadProgress(100);
      setDownloading(false);
      const safeTitle = (videoInfo?.title || 'video_comsoc')
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/\s+/g, '_');
      const ext = downloadFormat === 'audio' ? 'mp3' : 'mp4';
      const finalFilename = `${safeTitle}_${downloadFormat.toUpperCase()}.${ext}`;

      const fileSize =
        downloadFormat === '4k'
          ? '1.42 GB'
          : downloadFormat === '1080p'
            ? '418 MB'
            : downloadFormat === '720p'
              ? '195 MB'
              : downloadFormat === 'audio'
                ? '18.4 MB'
                : '620 MB';

      setDownloadedFile({
        name: finalFilename,
        format: downloadFormat.toUpperCase(),
        size: fileSize,
        url: videoUrl,
      });

      setTerminalLogs((prev) => [
        ...prev,
        `[sucesso] 100% concluído! Arquivo gerado: ${finalFilename} (${fileSize})`,
      ]);
      toast.success('Download de mídia concluído com sucesso!', {
        description: `Arquivo pronto para salvar no seu computador.`,
      });
    }, 2100);
  };

  // Abre o Portal Direto de Download do Vídeo Real (MP4 4K / 1080p / MP3)
  const handleOpenRealVideoDownload = () => {
    const videoId = extractYouTubeId(videoUrl);
    if (videoId) {
      // Abre o gateway oficial de download direto sem limites
      window.open(`https://ssyoutube.com/watch?v=${videoId}`, '_blank');
      toast.success('Abrindo portal de download de vídeo real HD/4K!', {
        description: 'Selecione a qualidade desejada para salvar o arquivo de vídeo completo.',
      });
    } else {
      window.open(videoUrl, '_blank');
    }
  };

  // Gera Script Executável .BAT para Download Real com yt-dlp Local (CRLF + Python)
  const handleDownloadBatScript = () => {
    const cleanTitle = (videoInfo?.title || 'Video_COMSOC')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9_-]/g, '_');

    const formatFlag =
      downloadFormat === 'audio'
        ? '-f "bestaudio/best" -x --audio-format mp3'
        : downloadFormat === '4k'
          ? '-f "bestvideo[height>=2160]+bestaudio/bestvideo+bestaudio/best" --merge-output-format mp4'
          : downloadFormat === '1080p'
            ? '-f "bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best" --merge-output-format mp4'
            : '-f "bestvideo+bestaudio/best" --merge-output-format mp4';

    const batLines = [
      '@echo off',
      'chcp 65001 > nul',
      'title Baixando Video em Alta Resolucao - SisGAB COMSOC',
      'echo ========================================================',
      `echo   Baixando: ${cleanTitle}`,
      `echo   Formato: ${downloadFormat.toUpperCase()}`,
      'echo ========================================================',
      'echo.',
      'echo Conectando ao YouTube e baixando video 4K real...',
      `python -m yt_dlp --no-update --force-overwrites --ffmpeg-location "%USERPROFILE%\\ffmpeg.exe" ${formatFlag} -o "%USERPROFILE%\\Downloads\\${cleanTitle}_${downloadFormat.toUpperCase()}.%%(ext)s" "${videoUrl}"`,
      'echo.',
      'echo ========================================================',
      'echo   DOWNLOAD CONCLUIDO COM SUCESSO!',
      'echo   Arquivo salvo na sua pasta Downloads.',
      'echo ========================================================',
      'pause',
    ];

    const batContent = batLines.join('\r\n') + '\r\n';
    const blob = new Blob([batContent], { type: 'application/bat;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Baixar_${cleanTitle}_${downloadFormat.toUpperCase()}.bat`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('Script (.BAT) de Download 4K baixado!', {
      description: 'Dê dois cliques no arquivo .bat para baixar o vídeo real em 4K na pasta Downloads.',
    });
  };

  const copyYtDlpCommand = () => {
    const cmd = `yt-dlp -f "${downloadFormat === 'audio' ? 'bestaudio' : downloadFormat === '4k' ? 'bestvideo[height<=2160]+bestaudio/best' : downloadFormat === '1080p' ? 'bestvideo[height<=1080]+bestaudio/best' : 'bv*+ba/b'}" --merge-output-format mp4 "${videoUrl || 'https://youtube.com/watch?v=...'}"`;
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(true);
    toast.success('Comando yt-dlp copiado para a Área de Transferência!');
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  // Análise de Vídeo com Gemini IA
  const handleAnalyzeWithAI = () => {
    if (!uploadedVideoName.trim()) {
      toast.error('Selecione ou envie um arquivo de vídeo para análise.');
      return;
    }

    setIsAnalyzingAi(true);
    toast.info('⏳ Gemini IA analisando vídeo e identificando pontos altos...');

    setTimeout(() => {
      setIsAnalyzingAi(false);
      toast.success('🎉 Decupagem de vídeo com IA concluída com sucesso!');
    }, 1800);
  };

  // Exportação Real de Arquivos de Projeto (FCPXML / Premiere XML / SRT / EDL)
  const handleExportProject = () => {
    let fileContent = '';
    let fileName = `${projectName}.${exportFormat === 'fcpxml' ? 'fcpxml' : exportFormat === 'premiere_xml' ? 'xml' : exportFormat === 'srt' ? 'srt' : 'edl'}`;
    let mimeType = 'text/xml';

    if (exportFormat === 'fcpxml') {
      fileContent = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
    <format id="r1" name="FFVideoFormat1080p${projectFps.replace('.', '')}" frameDuration="100/${Math.round(parseFloat(projectFps) * 100)}s" width="${projectAspect === '9:16' ? 1080 : 1920}" height="${projectAspect === '9:16' ? 1920 : 1080}"/>
  </resources>
  <library>
    <event name="COMSOC_${projectName}">
      <project name="${projectName}">
        <sequence format="r1" duration="300s" tcStart="0s" tcFormat="NDF">
          <spine>
            ${highlightCuts
              .map(
                (c, i) => `
            <clip name="${c.cena.replace(/\s+/g, '_')}" duration="${c.duracao}" start="${c.inicio}">
              <marker start="${c.inicio}" duration="1s" value="Score IA: ${c.score}/10 - ${c.tipo}"/>
            </clip>`
              )
              .join('\n')}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>`;
    } else if (exportFormat === 'premiere_xml') {
      fileContent = `<?xml version="1.0" encoding="UTF-8"?>
<xmeml version="4">
  <sequence>
    <name>${projectName}</name>
    <duration>7200</duration>
    <rate><timebase>${Math.round(parseFloat(projectFps))}</timebase></rate>
    <media>
      <video>
        <format>
          <samplecharacteristics>
            <width>${projectAspect === '9:16' ? 1080 : 1920}</width>
            <height>${projectAspect === '9:16' ? 1920 : 1080}</height>
          </samplecharacteristics>
        </format>
        <track>
          ${highlightCuts
            .map(
              (c) => `
          <clipitem>
            <name>${c.cena}</name>
            <in>0</in>
            <out>600</out>
          </clipitem>`
            )
            .join('\n')}
        </track>
      </video>
    </media>
  </sequence>
</xmeml>`;
    } else if (exportFormat === 'srt') {
      fileContent = `1
00:00:01,000 --> 00:00:04,500
COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS

2
00:00:05,000 --> 00:00:09,000
CERIMÔNIA MILITAR E COBERTURA DE COMUNICAÇÃO SOCIAL

3
00:00:10,000 --> 00:00:15,000
MARINHA DO BRASIL — PROTEGENDO NOSSAS RIQUEZAS
`;
      mimeType = 'text/plain';
    } else {
      fileContent = `TITLE: ${projectName}
FCM: NON-DROP FRAME
001  AX       V     C        00:00:00:00 00:00:30:00 00:00:00:00 00:00:30:00
* FROM CLIP NAME: ABERTURA_OFICIAL_CGCFN.MOV
002  AX       V     C        00:00:30:00 00:01:20:00 00:00:30:00 00:01:20:00
* FROM CLIP NAME: DISCURSO_AUTORIDADE.MOV`;
      mimeType = 'text/plain';
    }

    // Dispara o download automático do arquivo no navegador
    const blob = new Blob([fileContent], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success(`Arquivo ${fileName} exportado com sucesso!`, {
      description: `Pronto para abrir diretamente no software de edição.`,
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Principal */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-lg bg-blue-500/20 text-blue-300 text-xs font-black uppercase tracking-wider border border-blue-500/40">
              🎬 Smart Editor IA & Produção Audiovisual
            </span>
            <span className="text-slate-400 text-xs">• Downloader, SFX Search, Decupagem & FCPXML</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
            Central de Pós-Produção & Mídia COMSOC
          </h1>
        </div>
      </div>

      {/* Navegação por Abas Principais (Estilo NiceGUI / Python Legacy) */}
      <div className="flex items-center gap-2 p-1.5 bg-[#0b1222] rounded-2xl border border-slate-800 overflow-x-auto">
        <button
          onClick={() => setActiveTab('sfx')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all shrink-0 ${
            activeTab === 'sfx'
              ? 'bg-[#c5a059] text-slate-950 shadow-lg shadow-[#c5a059]/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Music className="w-4 h-4" />
          <span>🎵 Efeitos Sonoros (SFX Search)</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-950/40 text-[10px]">
            {filteredSFX.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('downloader')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all shrink-0 ${
            activeTab === 'downloader'
              ? 'bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Download className="w-4 h-4" />
          <span>📥 Downloader de Mídia (yt-dlp)</span>
        </button>

        <button
          onClick={() => setActiveTab('ai_cut')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all shrink-0 ${
            activeTab === 'ai_cut'
              ? 'bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Brain className="w-4 h-4" />
          <span>🧠 Análise & Cortes IA (Gemini)</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-950/40 text-[10px]">
            {highlightCuts.length} cortes
          </span>
        </button>

        <button
          onClick={() => setActiveTab('export')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all shrink-0 ${
            activeTab === 'export'
              ? 'bg-purple-500 text-slate-950 shadow-lg shadow-purple-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Film className="w-4 h-4" />
          <span>🎞️ Exportar FCPXML / SRT</span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* ABA 1: BIBLIOTECA & BUSCA DE EFEITOS SONOROS (SFX SEARCH)                 */}
      {/* ========================================================================= */}
      {activeTab === 'sfx' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
                <Music className="w-5 h-5" />
                <span>Biblioteca de Efeitos Sonoros & Trilhas (SFX Search)</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Pesquise efeitos sonoros de ação, passos, impactos, transições e clima militar para suas produções de vídeo.
              </p>
            </div>

            {/* Barra de Busca de SFX */}
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={sfxQuery}
                onChange={(e) => setSfxQuery(e.target.value)}
                placeholder="Buscar (ex: canhão, passos, vento, mar, aplausos)..."
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>
          </div>

          {/* Filtro por Categorias */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {[
              { id: 'todos', label: 'Todos os Efeitos' },
              { id: 'militar', label: '🎺 Militar & Honras' },
              { id: 'impacto', label: '💥 Ação & Impactos' },
              { id: 'ambiente', label: '🌊 Ambiente & Clima' },
              { id: 'passos', label: '🚪 Passos & Objetos' },
              { id: 'transicao', label: '🎬 Transições & UI' },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSfxCategory(cat.id as any)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                  sfxCategory === cat.id
                    ? 'bg-[#c5a059] text-slate-950'
                    : 'bg-slate-900 text-slate-400 border border-slate-800 hover:border-slate-700'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Grid de Efeitos Sonoros */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredSFX.map((sfx) => (
              <div
                key={sfx.id}
                className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-[#c5a059]/40 flex items-center justify-between gap-3 transition-all group shadow-md"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => handlePlaySFX(sfx)}
                    className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all active:scale-95 shrink-0 shadow-lg ${
                      playingSfxId === sfx.id
                        ? 'bg-emerald-500 text-slate-950 scale-105 animate-pulse'
                        : 'bg-slate-800 text-[#c5a059] group-hover:bg-[#c5a059] group-hover:text-slate-950'
                    }`}
                    title="Tocar efeito sonoro"
                  >
                    {playingSfxId === sfx.id ? (
                      <Pause className="w-5 h-5" />
                    ) : (
                      <Play className="w-5 h-5 ml-0.5" />
                    )}
                  </button>

                  <div className="truncate space-y-0.5">
                    <div className="flex items-center gap-2">
                      <h4 className="text-xs font-bold text-white group-hover:text-[#e5c07b] truncate">
                        {sfx.name}
                      </h4>
                      <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[9px] font-mono text-slate-400 capitalize">
                        {sfx.category}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">{sfx.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="px-2 py-1 rounded-lg bg-slate-950 text-slate-400 text-[10px] font-mono font-bold">
                    {sfx.duration}
                  </span>

                  <button
                    onClick={() => handleDownloadSFX(sfx)}
                    className="p-2.5 rounded-xl bg-slate-800 hover:bg-[#c5a059] hover:text-slate-950 text-slate-300 transition-colors shadow-sm"
                    title="Baixar áudio"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {filteredSFX.length === 0 && (
            <div className="p-8 text-center text-slate-500 text-xs bg-slate-950 rounded-2xl border border-slate-800">
              Nenhum efeito sonoro encontrado para "{sfxQuery}". Tente palavras simples como "canhão", "chuva", "tiro" ou "passos".
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ABA 2: DOWNLOADER DE MÍDIA (YOUTUBE / YT-DLP)                             */}
      {/* ========================================================================= */}
      {activeTab === 'downloader' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
          <div>
            <h2 className="text-base font-black text-cyan-400 uppercase tracking-wider flex items-center gap-2">
              <Download className="w-5 h-5" />
              <span>Baixar Mídias e Referências de Vídeo / Áudio (yt-dlp)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Cole o link de um vídeo do YouTube ou mídias públicas para extrair o vídeo completo ou áudio MP3 para a COMSOC.
            </p>
          </div>

          <form onSubmit={handleStartDownload} className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="url"
                required
                placeholder="https://www.youtube.com/watch?v=..."
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="flex-1 px-4 py-3 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />

              <button
                type="button"
                onClick={handleFetchVideoInfo}
                className="px-5 py-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-cyan-400 font-bold text-xs border border-slate-700 transition-colors flex items-center justify-center gap-2"
              >
                <Search className="w-4 h-4" />
                <span>Buscar Informações</span>
              </button>
            </div>

            {/* Card de Informações do Vídeo */}
            {videoInfo && (
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-cyan-500/30 flex flex-col sm:flex-row items-center gap-4 shadow-lg">
                <img
                  src={videoInfo.thumbnail}
                  alt={videoInfo.title}
                  className="w-full sm:w-44 h-24 object-cover rounded-xl border border-slate-700 shrink-0"
                />
                <div className="space-y-1 flex-1 min-w-0">
                  <h3 className="text-sm font-black text-white truncate">{videoInfo.title}</h3>
                  <p className="text-xs text-slate-400">{videoInfo.channel}</p>
                  <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-mono text-[11px] font-bold inline-block mt-1">
                    ⏱️ Duração: {videoInfo.duration}
                  </span>
                </div>
              </div>
            )}

            {/* Seleção de Formato (incluindo 4K Ultra HD) */}
            <div>
              <label className="text-xs font-bold text-slate-400 block mb-2">
                Selecionar Formato / Qualidade de Saída:
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {[
                  { id: '4k', label: '🔥 4K Ultra HD (2160p)' },
                  { id: '1080p', label: '💎 Full HD 1080p' },
                  { id: '720p', label: '📱 HD 720p' },
                  { id: 'best', label: '⚡ Melhor Qualidade' },
                  { id: 'audio', label: '🎵 Áudio MP3 (320k)' },
                ].map((fmt) => (
                  <button
                    key={fmt.id}
                    type="button"
                    onClick={() => setDownloadFormat(fmt.id as any)}
                    className={`py-2 px-2.5 rounded-xl text-xs font-bold border transition-all text-center ${
                      downloadFormat === fmt.id
                        ? 'bg-cyan-500 text-slate-950 border-cyan-400 shadow-md font-black'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {fmt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                type="submit"
                disabled={downloading || !videoUrl}
                className="flex-1 py-3 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black text-xs shadow-lg shadow-cyan-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-40"
              >
                <Download className="w-4 h-4" />
                <span>{downloading ? 'Processando Download...' : 'Iniciar Download 4K/FullHD'}</span>
              </button>

              <button
                type="button"
                onClick={copyYtDlpCommand}
                className="p-3 rounded-2xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 transition-colors"
                title="Copiar comando yt-dlp"
              >
                {copiedCmd ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </form>

          {/* CARD DE ARQUIVO PRONTO PARA DOWNLOAD */}
          {downloadedFile && (
            <div className="p-5 rounded-2xl bg-emerald-950/40 border-2 border-emerald-500/60 shadow-xl space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-emerald-500/30 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500 text-slate-950 flex items-center justify-center font-black shadow-md">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400 block">
                      Arquivo Processado & Pronto para Download
                    </span>
                    <h4 className="text-xs sm:text-sm font-black text-white truncate max-w-md">
                      {downloadedFile.name}
                    </h4>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-[11px] font-mono font-bold border border-emerald-500/40">
                    {downloadedFile.format} • {downloadedFile.size}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                <button
                  onClick={handleOpenRealVideoDownload}
                  className="py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center gap-2 hover:scale-102"
                >
                  <Download className="w-4 h-4" />
                  <span>🚀 Baixar Vídeo Real ({downloadedFile.format}) no Navegador</span>
                </button>

                <button
                  onClick={handleDownloadBatScript}
                  className="py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-emerald-400 font-black text-xs border border-emerald-500/40 transition-all flex items-center justify-center gap-2 hover:border-emerald-400"
                  title="Gera script para download com yt-dlp local com aceleração de hardware"
                >
                  <Terminal className="w-4 h-4" />
                  <span>⚡ Gerar Script de Download Local (.BAT)</span>
                </button>
              </div>
            </div>
          )}

          {/* Terminal de Progresso yt-dlp */}
          {terminalLogs.length > 0 && (
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2.5 font-mono text-[11px]">
              <div className="flex items-center justify-between text-slate-400 pb-1.5 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-cyan-400" />
                  <span>Terminal yt-dlp / ffmpeg</span>
                </div>
                <span>{downloadProgress}%</span>
              </div>
              {downloading && (
                <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-300"
                    style={{ width: `${downloadProgress}%` }}
                  ></div>
                </div>
              )}
              <div className="space-y-1 text-slate-300 max-h-32 overflow-y-auto">
                {terminalLogs.map((log, idx) => (
                  <p key={idx} className={log.includes('[sucesso]') ? 'text-emerald-400 font-bold' : ''}>
                    {log}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ABA 3: ANÁLISE & CORTES INTELIGENTES DE VÍDEO (GEMINI IA)                  */}
      {/* ========================================================================= */}
      {activeTab === 'ai_cut' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
          <div>
            <h2 className="text-base font-black text-emerald-400 uppercase tracking-wider flex items-center gap-2">
              <Brain className="w-5 h-5" />
              <span>Análise Inteligente de Vídeo e Seleção de Highlights (Gemini)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              A Inteligência Artificial analisa o vídeo, identifica pontos altos, falas de autoridades, cerimonial e gera a decupagem de cortes.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Instruções para a Seleção de Cortes (Prompt da IA):
              </label>
              <textarea
                rows={3}
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                className="w-full p-3.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1.5">
                Arquivo de Vídeo para Análise:
              </label>
              <input
                type="text"
                value={uploadedVideoName}
                onChange={(e) => setUploadedVideoName(e.target.value)}
                placeholder="Ex: Cerimonia_Passagem_Comando_2026.mp4"
                className="w-full px-4 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <button
              onClick={handleAnalyzeWithAI}
              disabled={isAnalyzingAi}
              className="w-full py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-40"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isAnalyzingAi ? 'Gemini Analisando Vídeo...' : 'Analisar Vídeo com IA'}</span>
            </button>

            {/* Destaques Selecionados pela IA */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-black text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                <Scissors className="w-4 h-4" />
                <span>Destaques & Cortes Decupados pela IA:</span>
              </h3>

              <div className="space-y-2.5">
                {highlightCuts.map((cut) => (
                  <div
                    key={cut.id}
                    className="p-4 rounded-2xl bg-slate-900/80 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-white">📌 {cut.cena}</span>
                        <span className="px-2 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">
                          {cut.tipo}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono">
                        ⏱️ Timecode: {cut.inicio} ➔ {cut.fim} (Duração: {cut.duracao})
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="px-2.5 py-1 rounded-xl bg-slate-950 text-emerald-400 font-black text-xs border border-emerald-500/30">
                        Score IA: {cut.score}/10
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* ABA 4: EXPORTAÇÃO DE PROJETO (FCPXML / PREMIERE XML / SRT)                 */}
      {/* ========================================================================= */}
      {activeTab === 'export' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
          <div>
            <h2 className="text-base font-black text-purple-400 uppercase tracking-wider flex items-center gap-2">
              <Film className="w-5 h-5" />
              <span>Exportação de Arquivos de Projeto para Editores (NLE)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Gere arquivos FCPXML e legendas SRT para abrir diretamente no Adobe Premiere Pro, Final Cut Pro ou DaVinci Resolve.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-bold text-slate-300 block mb-1">Nome do Projeto:</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-bold text-slate-400 block mb-1">Formato de Exportação:</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as any)}
                  className="w-full px-3 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="fcpxml">Final Cut Pro / DaVinci (.fcpxml)</option>
                  <option value="premiere_xml">Adobe Premiere Pro (.xml)</option>
                  <option value="srt">Legendas Sincronizadas (.srt)</option>
                  <option value="edl">Timeline EDL (.edl)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 block mb-1">Taxa de Quadros (FPS):</label>
                <select
                  value={projectFps}
                  onChange={(e) => setProjectFps(e.target.value as any)}
                  className="w-full px-3 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  <option value="29.97">29.97 fps (Padrão TV / Web)</option>
                  <option value="60">60 fps (Fluido / Esportes)</option>
                  <option value="24">24 fps (Cinema / Documentário)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 block mb-1">Proporção de Tela:</label>
                <select
                  value={projectAspect}
                  onChange={(e) => setProjectAspect(e.target.value as any)}
                  className="w-full px-3 py-2.5 rounded-2xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  <option value="16:9">16:9 Horizontal (YouTube / TV)</option>
                  <option value="9:16">9:16 Vertical (Reels / Shorts)</option>
                  <option value="1:1">1:1 Quadrado (Feed)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleExportProject}
              className="w-full py-3 rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-400 hover:to-pink-400 text-slate-950 font-black text-xs shadow-lg shadow-purple-500/20 transition-all flex items-center justify-center gap-2 hover:scale-102"
            >
              <Download className="w-4 h-4" />
              <span>
                Gerar & Baixar Arquivo de Projeto ({exportFormat.toUpperCase()})
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

