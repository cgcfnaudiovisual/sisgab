import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Tv,
  Clock,
  Calendar,
  Bell,
  Users,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Volume2,
  VolumeX,
  Maximize,
  Minimize,
  Award,
  Home,
  Zap,
  Shield,
  Armchair,
  Camera,
  Video,
  Radio,
  FileText,
  MapPin,
  UserCheck,
  ChevronRight,
  Gift,
  Cake,
  Megaphone,
  Anchor,
  X,
  Plus,
  Printer,
  Play,
  Pause,
  Sliders,
  ExternalLink,
  Activity,
  RotateCw,
  Eye,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { DemandaComunicacao } from '../../types/database';
import { getBrasiliaDateStr, addDaysBrasilia, BRASILIA_TIMEZONE } from '../../utils/formatters';
import { parseCobertura } from '../../utils/formatters';

const DIAS_SEMANA_MAP: Record<number, string> = {
  0: 'DOM',
  1: 'SEG',
  2: 'TER',
  3: 'QUA',
  4: 'QUI',
  5: 'SEX',
  6: 'SÁB',
};

// Stream oficial da Rádio Marinha do Brasil
const RADIO_MARINHA_URL = 'https://icecast.radiomarinhadobrasil.com.br/live';

export const SisgabTVPlayer: React.FC = () => {
  const navigate = useNavigate();
  const [currentTime, setCurrentTime] = useState<Date>(new Date());
  const [soundEnabled, setSoundEnabled] = useState<boolean>(true);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [viewFilter, setViewFilter] = useState<'semana' | 'todas'>('semana');

  // Player da Rádio Marinha
  const [radioPlaying, setRadioPlaying] = useState<boolean>(false);
  const [radioVolume, setRadioVolume] = useState<number>(0.7);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Dados Reais do Banco
  const [demandas, setDemandas] = useState<DemandaComunicacao[]>([]);
  const [aniversariantes, setAniversariantes] = useState<any[]>([]);
  const [efetivoTotal, setEfetivoTotal] = useState<number>(0);

  // Placas Jade
  const [jadeConvidados, setJadeConvidados] = useState<any[]>([]);
  const [jadeStats, setJadeStats] = useState<{ total: number; impressas: number; pendentes: number }>({
    total: 0,
    impressas: 0,
    pendentes: 0,
  });
  const [jadeModalOpen, setJadeModalOpen] = useState(false);
  const [previewPlateGuest, setPreviewPlateGuest] = useState<any | null>(null);

  // Modal Missão Rápida
  const [missaoRapidaModal, setMissaoRapidaModal] = useState(false);
  const [novaMissao, setNovaMissao] = useState({
    titulo_evento: '',
    local_evento: 'Gabinete CGCFN',
    hora_evento: '10:00',
    data_evento: getBrasiliaDateStr(),
    solicitante_nome: 'MONITOR TV',
    setor: 'Gabinete / CGCFN',
    tipo_cobertura: ['Fotografia'],
    sigiloso: false,
  });

  // Relógio Naval em Tempo Real
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Polling automático a cada 15 segundos para atualizar status da TV
  useEffect(() => {
    loadRealData();
    const poll = setInterval(loadRealData, 15000);
    return () => clearInterval(poll);
  }, []);

  // Inicialização do Áudio da Rádio Marinha
  useEffect(() => {
    const audio = new Audio(RADIO_MARINHA_URL);
    audio.volume = radioVolume;
    audioRef.current = audio;

    return () => {
      audio.pause();
      audio.src = '';
    };
  }, []);

  const toggleRadioPlay = () => {
    if (!audioRef.current) return;

    if (radioPlaying) {
      audioRef.current.pause();
      setRadioPlaying(false);
      toast.info('📻 Rádio Marinha pausada');
    } else {
      audioRef.current
        .play()
        .then(() => {
          setRadioPlaying(true);
          toast.success('📻 Transmitindo Rádio Marinha do Brasil Ao Vivo!');
        })
        .catch((err) => {
          console.warn('Erro ao tocar rádio:', err);
          toast.error('Não foi possível conectar ao stream da rádio.');
        });
    }
  };

  const handleVolumeChange = (newVol: number) => {
    setRadioVolume(newVol);
    if (audioRef.current) {
      audioRef.current.volume = newVol;
    }
  };

  const loadRealData = async () => {
    try {
      // 1. Demandas
      const { data: demData } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .order('data_evento', { ascending: true });
      if (demData) setDemandas(demData as DemandaComunicacao[]);

      // 2. Efetivo e Aniversariantes
      const { data: efData } = await supabase
        .from('efetivo')
        .select('*')
        .order('antiguidade_num', { ascending: true });
      if (efData) {
        setEfetivoTotal(efData.length);
        
        // Filtra aniversariantes do mês atual
        const mesAtual = new Date().getMonth() + 1;
        const niverMes = efData.filter((m: any) => {
          if (!m.data_nascimento) return false;
          const [, mes] = m.data_nascimento.split('-');
          return parseInt(mes, 10) === mesAtual;
        });
        setAniversariantes(niverMes.length > 0 ? niverMes : efData.slice(0, 4));
      }

      // 3. Placas Jade
      const { data: jadeData } = await supabase
        .from('jade_convidados')
        .select('*')
        .order('id', { ascending: false });
      if (jadeData) {
        setJadeConvidados(jadeData);
        const total = jadeData.length;
        const impressas = jadeData.filter((j) => j.status_placa === 'impressa').length;
        const pendentes = jadeData.filter((j) => j.status_placa === 'pendente').length;
        setJadeStats({ total, impressas, pendentes });
      }
    } catch (err) {
      console.warn('Erro ao carregar dados da TV:', err);
    }
  };

  // Marcar Placa Jade como Impressa
  const handleMarcarPlacaImpressa = async (convidadoId: number, nomeConvidado: string) => {
    try {
      // Otimista
      setJadeConvidados((prev) =>
        prev.map((c) => (c.id === convidadoId ? { ...c, status_placa: 'impressa' } : c))
      );
      setJadeStats((prev) => ({
        ...prev,
        impressas: prev.impressas + 1,
        pendentes: Math.max(0, prev.pendentes - 1),
      }));

      toast.success(`Placa de ${nomeConvidado} marcada como IMPRESSA!`);

      await supabase
        .from('jade_convidados')
        .update({ status_placa: 'impressa' })
        .eq('id', convidadoId);
    } catch (err) {
      console.warn('Erro ao atualizar placa:', err);
    }
  };

  const playNauticalBell = (double: boolean = false) => {
    if (!soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const ringOneBell = (delay: number) => {
        setTimeout(() => {
          const osc = audioCtx.createOscillator();
          const gain = audioCtx.createGain();

          osc.type = 'sine';
          osc.frequency.setValueAtTime(880, audioCtx.currentTime);
          osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 1.2);

          gain.gain.setValueAtTime(0.7, audioCtx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 1.5);

          osc.connect(gain);
          gain.connect(audioCtx.destination);

          osc.start();
          osc.stop(audioCtx.currentTime + 1.5);
        }, delay);
      };

      ringOneBell(0);
      if (double) ringOneBell(300);
    } catch (e) {
      console.warn('Audio indisponível:', e);
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const handleSalvarMissaoRapida = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novaMissao.titulo_evento) {
      toast.error('Informe o título da missão.');
      return;
    }

    try {
      const rawHora = novaMissao.hora_evento || '10:00:00';
      const safeHora = rawHora.length === 5 ? `${rawHora}:00` : rawHora;

      const { error } = await supabase.from('demandas_comunicacao').insert({
        titulo_evento: `⚡ ${novaMissao.titulo_evento.toUpperCase()}`,
        solicitante_nome: novaMissao.solicitante_nome,
        setor: novaMissao.setor,
        contato: 'Interno',
        data_evento: novaMissao.data_evento || getBrasiliaDateStr(),
        hora_evento: safeHora,
        local_evento: novaMissao.local_evento || 'Gabinete CGCFN',
        tipo_cobertura: novaMissao.tipo_cobertura,
        status: 'aprovado',
        sigiloso: novaMissao.sigiloso,
      });

      if (error) throw error;
      toast.success('⚡ Missão rápida lançada e aprovada no painel!');
      setMissaoRapidaModal(false);
      setNovaMissao({
        titulo_evento: '',
        local_evento: 'Gabinete CGCFN',
        hora_evento: '10:00',
        data_evento: getBrasiliaDateStr(),
        solicitante_nome: 'MONITOR TV',
        setor: 'Gabinete / CGCFN',
        tipo_cobertura: ['Fotografia'],
        sigiloso: false,
      });
      loadRealData();
    } catch (err: any) {
      toast.error(`Erro ao lançar: ${err.message}`);
    }
  };

  const hojeStr = getBrasiliaDateStr(currentTime);
  const amanhaStr = addDaysBrasilia(hojeStr, 1);

  // 1. Pautas Hoje & Amanhã
  const pautasHojeEAmanha = demandas.filter(
    (d) => d.data_evento === hojeStr || d.data_evento === amanhaStr
  );

  // 2. Pautas da Semana (Próximos 7 Dias)
  const pautasSemana = demandas.filter((d) => {
    if (!d.data_evento) return false;
    const diffTime = new Date(d.data_evento).getTime() - currentTime.getTime();
    const diffDays = diffTime / (1000 * 3600 * 24);
    return diffDays >= -1 && diffDays <= 7;
  });

  // 3. Contadores Claros de Status das Demandas
  const totalAprovadas = demandas.filter((d) =>
    ['aprovado', 'aprovada', 'concluido', 'concluida'].includes((d.status || '').toLowerCase())
  ).length;

  const totalPendentes = demandas.filter((d) =>
    ['pendente', 'pendentes'].includes((d.status || '').toLowerCase())
  ).length;

  const totalEmAjusteOuAndamento = demandas.filter((d) =>
    ['ajuste', 'ajustes', 'em_andamento', 'andamento'].includes((d.status || '').toLowerCase())
  ).length;

  const formattedTime = currentTime.toLocaleTimeString('pt-BR', { timeZone: BRASILIA_TIMEZONE });
  const formattedDate = currentTime.toLocaleDateString('pt-BR', {
    timeZone: BRASILIA_TIMEZONE,
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });

  const convidadosPendentes = jadeConvidados.filter((c) => c.status_placa === 'pendente');

  return (
    <div className="fixed inset-0 z-50 bg-[#05070e] text-slate-100 flex flex-col justify-between p-3 select-none overflow-hidden font-sans">
      {/* ── 1. CABEÇALHO TÁTICO FIXO COM PLAYER RÁDIO MARINHA ── */}
      <header className="flex items-center justify-between px-4 py-2 rounded-2xl bg-[#091326]/85 border border-cyan-500/30 backdrop-blur-md shrink-0 shadow-xl gap-3">
        {/* Identificação */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#c5a059]/15 border border-[#c5a059] flex items-center justify-center text-xl shadow-md shadow-[#c5a059]/20 font-black text-[#c5a059]">
            ⚓
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-black text-white tracking-wider uppercase">
                SISGAB • MONITOR TV
              </span>
              <span className="px-2 py-0.5 rounded-md bg-[#00e5ff]/20 text-[#00e5ff] text-[10px] font-black border border-[#00e5ff]/40">
                DISPLAY TÁTICO
              </span>
            </div>
            <p className="text-[10px] text-[#c5a059] font-bold tracking-wider uppercase">
              COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS • GABINETE
            </p>
          </div>
        </div>

        {/* 📻 PLAYER RÁDIO MARINHA DO BRASIL & BOTÕES TÁTICOS */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Player Rádio Marinha */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/80 border border-cyan-500/30 shadow-inner">
            <button
              onClick={toggleRadioPlay}
              className={`p-1.5 rounded-lg flex items-center gap-1.5 text-xs font-black transition-all ${
                radioPlaying
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/30 animate-pulse'
                  : 'bg-slate-900 hover:bg-slate-800 text-cyan-300'
              }`}
              title={radioPlaying ? 'Pausar Rádio Marinha' : 'Tocar Rádio Marinha do Brasil Ao Vivo'}
            >
              {radioPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current" />}
              <span>📻 RÁDIO MARINHA</span>
            </button>

            {/* Equalizador animado */}
            {radioPlaying && (
              <div className="flex items-end gap-0.5 h-3.5 px-1">
                <span className="w-1 bg-emerald-400 rounded-full animate-[bounce_0.8s_infinite]"></span>
                <span className="w-1 bg-cyan-400 rounded-full animate-[bounce_0.6s_infinite_0.2s]"></span>
                <span className="w-1 bg-amber-400 rounded-full animate-[bounce_0.9s_infinite_0.4s]"></span>
              </div>
            )}

            {/* Slider de Volume */}
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={radioVolume}
              onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
              className="w-14 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-[#00e5ff]"
              title={`Volume: ${Math.round(radioVolume * 100)}%`}
            />
          </div>

          {/* Botão Missão Rápida */}
          <button
            onClick={() => setMissaoRapidaModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 text-white font-black text-xs shadow-md shadow-orange-600/30 transition-all hover:scale-105"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>⚡ Missão Rápida</span>
          </button>

          {/* Botão Placas Jade */}
          <button
            onClick={() => setJadeModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 text-indigo-300 font-bold text-xs transition-all"
          >
            <Armchair className="w-3.5 h-3.5" />
            <span>🪪 Placas JADE ({jadeStats.pendentes})</span>
          </button>

          {/* Botão Início */}
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold text-xs transition-all"
          >
            <Home className="w-3.5 h-3.5" />
            <span>Início</span>
          </button>

          {/* Botão Tela Cheia */}
          <button
            onClick={toggleFullscreen}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 font-bold text-xs transition-all"
          >
            <Maximize className="w-3.5 h-3.5" />
            <span>Tela Cheia</span>
          </button>
        </div>

        {/* Relógio Naval e Sino */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-2xl sm:text-3xl font-black text-[#00e5ff] font-mono tracking-widest leading-none drop-shadow-[0_0_10px_rgba(0,229,255,0.4)]">
              {formattedTime}
            </div>
            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mt-0.5">
              {formattedDate}
            </div>
          </div>

          <button
            onClick={() => playNauticalBell(true)}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-[#c5a059] text-[#c5a059] transition-colors"
            title="Tocar Sino Náutico"
          >
            <Bell className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* ── 2. BARRA DE 6 KPIS CLAROS E OBJETIVOS ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 my-2 shrink-0">
        {/* KPI 1: Pautas Aprovadas / Homologadas */}
        <div
          onClick={() => setViewFilter('semana')}
          className="p-2.5 rounded-xl bg-[#091326]/70 hover:bg-[#091326] border border-cyan-500/25 hover:border-cyan-400 flex items-center gap-2.5 backdrop-blur-xs cursor-pointer transition-all shadow-md"
        >
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">PAUTAS APROVADAS</span>
            <span className="text-lg font-black text-white leading-none">{totalAprovadas}</span>
          </div>
        </div>

        {/* KPI 2: Pendentes de Análise */}
        <div
          onClick={() => navigate('/comsoc_homologar')}
          className="p-2.5 rounded-xl bg-[#091326]/70 hover:bg-[#091326] border border-amber-500/25 hover:border-amber-400 flex items-center gap-2.5 backdrop-blur-xs cursor-pointer transition-all shadow-md"
        >
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">PENDENTES ANÁLISE</span>
            <span className="text-lg font-black text-amber-400 leading-none">{totalPendentes}</span>
          </div>
        </div>

        {/* KPI 3: Em Andamento / Ajustes */}
        <div className="p-2.5 rounded-xl bg-[#091326]/70 border border-orange-500/25 flex items-center gap-2.5 backdrop-blur-xs shadow-md">
          <div className="p-2 rounded-lg bg-orange-500/10 text-orange-400">
            <RotateCw className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">EM ANDAMENTO</span>
            <span className="text-lg font-black text-orange-300 leading-none">{totalEmAjusteOuAndamento}</span>
          </div>
        </div>

        {/* KPI 4: Eventos Hoje & Amanhã */}
        <div className="p-2.5 rounded-xl bg-[#091326]/70 border border-yellow-500/25 flex items-center gap-2.5 backdrop-blur-xs shadow-md">
          <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-400">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">HOJE & AMANHÃ</span>
            <span className="text-lg font-black text-yellow-300 leading-none">{pautasHojeEAmanha.length}</span>
          </div>
        </div>

        {/* KPI 5: Eventos da Semana (Total) */}
        <div className="p-2.5 rounded-xl bg-[#091326]/70 border border-emerald-500/25 flex items-center gap-2.5 backdrop-blur-xs shadow-md">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Calendar className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">EVENTOS DA SEMANA</span>
            <span className="text-lg font-black text-emerald-300 leading-none">{pautasSemana.length}</span>
          </div>
        </div>

        {/* KPI 6: Placas JADE Pendentes */}
        <div
          onClick={() => setJadeModalOpen(true)}
          className={`p-2.5 rounded-xl flex items-center gap-2.5 backdrop-blur-xs cursor-pointer transition-all shadow-md ${
            jadeStats.pendentes > 0
              ? 'bg-amber-500/15 border-2 border-amber-500/60 animate-pulse hover:bg-amber-500/25'
              : 'bg-[#091326]/70 border border-indigo-500/25 hover:border-indigo-400'
          }`}
          title="Clique para gerenciar as Placas Jade"
        >
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Armchair className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block">
              {jadeStats.pendentes > 0 ? '⚠️ JADE PENDENTE' : 'PLACAS JADE'}
            </span>
            <span className="text-lg font-black text-indigo-300 leading-none">
              {jadeStats.impressas}/{jadeStats.total}
            </span>
          </div>
        </div>
      </div>

      {/* ── 3. ÁREA PRINCIPAL: 3 COLUNAS TÁTICAS (ADAPTÁVEIS PARA TV HORIZONTAL E VERTICAL/TOTEM) ── */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-2.5 flex-1 min-h-0 overflow-y-auto lg:overflow-hidden pr-0.5">
        {/* ========================================================================= */}
        {/* COLUNA 1 (ESQUERDA - 4 COLS): PAUTAS HOJE & AMANHÃ */}
        {/* ========================================================================= */}
        <section className="lg:col-span-4 min-h-[240px] lg:min-h-0 p-3 rounded-2xl bg-[#091326]/60 border border-cyan-500/25 flex flex-col justify-between overflow-hidden shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between pb-2 border-b border-cyan-500/30 shrink-0 mb-2">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-amber-400" />
              <h2 className="text-xs font-black text-white uppercase tracking-wider">
                EVENTOS: HOJE & AMANHÃ
              </h2>
            </div>
            <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-black uppercase">
              {pautasHojeEAmanha.length} Eventos
            </span>
          </div>

          <div className="space-y-2 flex-1 overflow-y-auto pr-1 scrollbar-none">
            {pautasHojeEAmanha.length > 0 ? (
              pautasHojeEAmanha.map((dem) => {
                const isHoje = dem.data_evento === hojeStr;
                const cobs = parseCobertura(dem.tipo_cobertura);
                const isAprov = ['aprovado', 'aprovada', 'concluido', 'concluida'].includes(
                  (dem.status || '').toLowerCase()
                );

                return (
                  <div
                    key={dem.id}
                    className={`p-2.5 rounded-xl border transition-all text-left space-y-1.5 ${
                      isHoje
                        ? 'bg-amber-500/10 border-amber-500/40 shadow-sm'
                        : 'bg-cyan-500/10 border-cyan-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-black uppercase ${
                            isHoje ? 'bg-amber-500 text-slate-950' : 'bg-cyan-500 text-slate-950'
                          }`}
                        >
                          {isHoje ? 'HOJE' : 'AMANHÃ'}
                        </span>
                        <span className="text-[11px] font-black text-[#00e5ff] flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {dem.hora_evento || '10:00'}
                        </span>
                      </div>
                      <span
                        className={`text-[8px] font-black uppercase px-1.5 py-0.2 rounded ${
                          isAprov
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        }`}
                      >
                        {isAprov ? 'APROVADO' : 'PENDENTE'}
                      </span>
                    </div>

                    <h3 className="text-xs font-black text-white leading-tight line-clamp-2">
                      {dem.titulo_evento}
                    </h3>

                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span className="truncate flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-[#c5a059]" />
                        {dem.local_evento || 'Gabinete'}
                      </span>
                      <span className="truncate text-slate-500">{dem.solicitante_nome}</span>
                    </div>

                    {/* Micro Ícones de Cobertura */}
                    {cobs.length > 0 && (
                      <div className="flex items-center gap-1 pt-1 border-t border-slate-800/80">
                        {cobs.map((cob, cIdx) => (
                          <span
                            key={cIdx}
                            className="px-1.5 py-0.2 rounded bg-slate-950 text-slate-300 text-[9px] font-bold border border-slate-800 flex items-center gap-0.5"
                          >
                            {cob.toLowerCase().includes('foto') && <Camera className="w-2.5 h-2.5 text-cyan-400" />}
                            {cob.toLowerCase().includes('video') && <Video className="w-2.5 h-2.5 text-pink-400" />}
                            {cob.toLowerCase().includes('drone') && <Radio className="w-2.5 h-2.5 text-amber-400" />}
                            <span>{cob}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-500/40" />
                <p className="text-xs font-bold text-slate-400">Nenhum evento agendado para hoje ou amanhã.</p>
                <p className="text-[10px] text-slate-600">Equipe COMSOC em prontidão geral.</p>
              </div>
            )}
          </div>
        </section>

        {/* ========================================================================= */}
        {/* COLUNA 2 (CENTRO - 5 COLS): CRONOGRAMA & RESUMO DA SEMANA */}
        {/* ========================================================================= */}
        <section className="lg:col-span-5 min-h-[240px] lg:min-h-0 p-3 rounded-2xl bg-[#091326]/60 border border-cyan-500/25 flex flex-col justify-between overflow-hidden shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between pb-2 border-b border-cyan-500/30 shrink-0 mb-2">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-black text-white uppercase tracking-wider">
                CRONOGRAMA & RESUMO DA SEMANA
              </h2>
            </div>

            <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-950 border border-slate-800 text-[10px]">
              <button
                onClick={() => setViewFilter('semana')}
                className={`px-2 py-0.5 rounded font-bold transition-all ${
                  viewFilter === 'semana' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                Esta Semana
              </button>
              <button
                onClick={() => setViewFilter('todas')}
                className={`px-2 py-0.5 rounded font-bold transition-all ${
                  viewFilter === 'todas' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                Todas
              </button>
            </div>
          </div>

          <div className="space-y-2 flex-1 overflow-y-auto pr-1 scrollbar-none">
            {pautasSemana.length > 0 ? (
              pautasSemana.map((dem) => {
                const dateObj = dem.data_evento ? new Date(dem.data_evento + 'T00:00:00') : new Date();
                const diaSemana = DIAS_SEMANA_MAP[dateObj.getDay()] || 'DIA';
                const diaMes = dem.data_evento ? dem.data_evento.split('-').reverse().slice(0, 2).join('/') : '--/--';
                const cobs = parseCobertura(dem.tipo_cobertura);
                const isAprov = ['aprovado', 'aprovada', 'concluido', 'concluida'].includes(
                  (dem.status || '').toLowerCase()
                );

                return (
                  <div
                    key={dem.id}
                    className="p-2 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-cyan-500/40 transition-all flex items-center justify-between gap-3 text-left"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-center min-w-[42px]">
                        <span className="text-[9px] font-black text-cyan-400 block">{diaSemana}</span>
                        <span className="text-[11px] font-black text-white leading-none">{diaMes}</span>
                      </div>

                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] font-bold text-[#c5a059]">{dem.hora_evento || '09:00'}</span>
                          <span className="text-[10px] text-slate-500">•</span>
                          <span className="text-[10px] text-slate-400 truncate max-w-[140px]">{dem.local_evento}</span>
                        </div>
                        <h4 className="text-xs font-bold text-white truncate max-w-[240px]">
                          {dem.titulo_evento}
                        </h4>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span
                        className={`text-[8px] font-black uppercase px-1.5 py-0.2 rounded ${
                          isAprov
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {isAprov ? 'APROVADO' : 'PENDENTE'}
                      </span>
                      <p className="text-[9px] text-slate-500 truncate max-w-[90px] mt-0.5">
                        {dem.solicitante_nome}
                      </p>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <p className="text-xs font-bold text-slate-400">Sem demandas para os próximos dias.</p>
              </div>
            )}
          </div>
        </section>

        {/* ========================================================================= */}
        {/* COLUNA 3 (DIREITA - 3 COLS): INFORMATIVOS, ANIVERSARIANTES & PLACAS JADE */}
        {/* ========================================================================= */}
        <section className="lg:col-span-3 min-h-[240px] lg:min-h-0 p-3 rounded-2xl bg-[#091326]/60 border border-cyan-500/25 flex flex-col justify-between overflow-hidden shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between pb-2 border-b border-cyan-500/30 shrink-0 mb-2">
            <div className="flex items-center gap-2">
              <Cake className="w-4 h-4 text-pink-400" />
              <h2 className="text-xs font-black text-white uppercase tracking-wider">
                ANIVERSARIANTES & EFEMÉRIDES
              </h2>
            </div>
            <span className="text-[10px] text-pink-300 font-bold">Mês Oficial</span>
          </div>

          <div className="space-y-2.5 flex-1 overflow-y-auto pr-1 scrollbar-none">
            {/* Bloco 1: Aniversariantes */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider block">
                🎂 Aniversariantes do Mês ({aniversariantes.length})
              </span>

              {aniversariantes.slice(0, 4).map((niver, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded-xl bg-gradient-to-r from-pink-500/10 to-purple-500/10 border border-pink-500/30 flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-pink-500/20 border border-pink-400 flex items-center justify-center text-xs font-bold text-pink-300">
                      🎂
                    </div>
                    <div>
                      <p className="text-xs font-black text-white">{niver.nome_guerra}</p>
                      <p className="text-[9px] text-slate-400">{niver.posto_grad || niver.posto || 'Militar'}</p>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold text-[#e5c07b]">
                    {niver.data_nascimento ? niver.data_nascimento.split('-').reverse().slice(0, 2).join('/') : 'Mês Atual'}
                  </span>
                </div>
              ))}
            </div>

            {/* Bloco 2: Alerta de Placas Jade Pendentes (Clicável) */}
            {jadeStats.pendentes > 0 && (
              <div
                onClick={() => setJadeModalOpen(true)}
                className="p-2.5 rounded-xl bg-amber-500/15 border-2 border-amber-500/50 hover:bg-amber-500/25 animate-pulse flex items-center justify-between cursor-pointer transition-all"
                title="Clique para gerenciar as 7 placas pendentes"
              >
                <div className="flex items-center gap-2">
                  <Armchair className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold text-amber-300">Placas JADE Pendentes</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-amber-500 text-slate-950 font-black text-[10px]">
                  {jadeStats.pendentes} PENDENTES ➜
                </span>
              </div>
            )}

            {/* Bloco 3: Comunicado do Gabinete */}
            <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex items-center gap-1.5 text-xs font-black text-[#c5a059]">
                <Megaphone className="w-3.5 h-3.5" />
                <span>COMUNICADO DO CHEGAB</span>
              </div>
              <p className="text-[10px] text-slate-300 leading-relaxed">
                Relatórios de pronto, pautas e assentos do cerimonial sincronizados em tempo real no SisGAB 2.0.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* ── 4. RODAPÉ FIXO COM TICKER MARQUEE EM MOVIMENTO ── */}
      <footer className="mt-2 px-4 py-2 rounded-xl bg-[#091326]/90 border border-cyan-500/30 flex items-center justify-between gap-4 shrink-0 shadow-xl overflow-hidden">
        <span className="px-2.5 py-0.5 rounded-lg bg-[#c5a059] text-slate-950 font-black text-[10px] uppercase shrink-0 shadow-sm">
          INFO GABINETE
        </span>

        <div className="overflow-hidden whitespace-nowrap flex-1 relative">
          <div className="inline-block animate-marquee text-xs font-medium text-slate-300 space-x-8">
            <span>⚓ <strong>SisGAB TV 2.0:</strong> Central de Comando e Coberturas Integradas ao Supabase</span>
            <span>•</span>
            <span>📸 <strong>Eventos Próximos:</strong> {pautasHojeEAmanha.length} Eventos Hoje e Amanhã</span>
            <span>•</span>
            <span>🗓️ <strong>Semana:</strong> {pautasSemana.length} Solenidades agendadas nos próximos 7 dias</span>
            <span>•</span>
            <span>🪪 <strong>Cerimonial:</strong> {jadeStats.total} Convidados mapeados • {jadeStats.pendentes} Placas aguardando impressão</span>
            <span>•</span>
            <span>📻 <strong>Rádio Marinha:</strong> Transmissão de áudio oficial ativa</span>
            <span>•</span>
            <span>🚀 <strong>Desenvolvido por Sargento Calaça 🇧🇷</strong> • Gabinete CGCFN</span>
          </div>
        </div>
      </footer>

      {/* ── MODAL 1: GESTÃO RÁPIDA DE PLACAS JADE NA TV ── */}
      {jadeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-2xl p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl max-h-[85vh] flex flex-col justify-between">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Armchair className="w-5 h-5 text-indigo-400" />
                <div>
                  <h3 className="text-sm font-black text-white">Gestão Rápida de Placas JADE ({convidadosPendentes.length} Pendentes)</h3>
                  <p className="text-[11px] text-slate-400">Autoridades aguardando impressão de placa dobrável de mesa.</p>
                </div>
              </div>
              <button onClick={() => setJadeModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 flex-1 overflow-y-auto pr-1 divide-y divide-slate-800/60">
              {convidadosPendentes.length > 0 ? (
                convidadosPendentes.map((conv) => (
                  <div key={conv.id} className="pt-2 flex items-center justify-between gap-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{conv.nome}</span>
                        {conv.posto_graduacao && (
                          <span className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700 text-[10px] text-slate-300">
                            {conv.posto_graduacao}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400">{conv.cargo_funcao || 'Autoridade Convidada'}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setPreviewPlateGuest(conv)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-300 font-bold text-xs transition-all"
                        title="Ver layout e design da placa"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Ver Design</span>
                      </button>

                      <button
                        onClick={() => handleMarcarPlacaImpressa(conv.id, conv.nome)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-md shadow-emerald-500/20 transition-all hover:scale-105"
                      >
                        <Printer className="w-3.5 h-3.5" />
                        <span>Imprimir ✅</span>
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs">
                  Todas as placas do cerimonial estão impressas!
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  setJadeModalOpen(false);
                  navigate('/comsoc_assentos');
                }}
                className="flex items-center gap-1.5 text-xs text-[#00e5ff] font-bold hover:underline"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Abrir Estúdio Completo de Design JADE</span>
              </button>

              <button
                onClick={() => setJadeModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-bold"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: PRÉ-VISUALIZAÇÃO DE DESIGN DA PLACA JADE ── */}
      {previewPlateGuest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
          <div className="w-full max-w-xl p-6 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059] space-y-4 shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Printer className="w-5 h-5 text-[#c5a059]" />
                <h3 className="text-sm font-black text-white">
                  Pré-visualização do Design • Prisma Dobrável JADE
                </h3>
              </div>
              <button onClick={() => setPreviewPlateGuest(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Simulação da Placa Dobrável em Alta Resolução */}
            <div className="p-6 rounded-2xl bg-white text-slate-950 border-4 border-[#c5a059] shadow-2xl text-center space-y-3 relative overflow-hidden">
              {/* Marca de dobra de mesa */}
              <div className="absolute top-2 left-2 text-[8px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                [ LINHA DE DOBRA SUPERIOR - VINCO A4 ]
              </div>

              {/* Brasão / Insígnia */}
              <div className="flex items-center justify-between px-4 pt-2">
                <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-300 flex items-center justify-center text-2xl font-black shadow-xs">
                  ⚓
                </div>

                {/* Estrelas de Almirante se houver */}
                {previewPlateGuest.posto_graduacao?.toUpperCase().includes('ALMIRANTE') ||
                previewPlateGuest.posto_graduacao?.toUpperCase().includes('AE') ? (
                  <div className="text-amber-500 font-black text-lg tracking-widest">
                    ★ ★ ★ ★
                  </div>
                ) : (
                  <div className="text-slate-500 font-bold text-xs uppercase tracking-wider">
                    MARINHA DO BRASIL
                  </div>
                )}

                {/* QR Code Simulado */}
                <div className="w-12 h-12 bg-slate-900 text-white flex items-center justify-center font-mono text-[8px] p-1 rounded">
                  QR-CHECKIN
                </div>
              </div>

              {/* Posto e Nome Principal */}
              <div className="py-3 border-y-2 border-slate-200 space-y-1">
                {previewPlateGuest.posto_graduacao && (
                  <p className="text-xs font-black text-[#856404] uppercase tracking-widest">
                    {previewPlateGuest.posto_graduacao}
                  </p>
                )}
                <h2 className="text-2xl font-black text-slate-950 tracking-tight uppercase">
                  {previewPlateGuest.nome}
                </h2>
                <p className="text-xs font-semibold text-slate-600">
                  {previewPlateGuest.cargo_funcao || 'Autoridade Convidada de Honra'}
                </p>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                <span>EVENTO: GABINETE CGCFN</span>
                <span>ASSENTO: {previewPlateGuest.assento_id || 'RESERVADO MESA'}</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => {
                  window.print();
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs border border-slate-700"
              >
                <Printer className="w-4 h-4" />
                <span>Imprimir Agora</span>
              </button>

              <button
                onClick={() => {
                  handleMarcarPlacaImpressa(previewPlateGuest.id, previewPlateGuest.nome);
                  setPreviewPlateGuest(null);
                }}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/25"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Marcar como Impressa ✅</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: MISSÃO RÁPIDA (LANÇAMENTO EXPRESSO NA TV) ── */}
      {missaoRapidaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-black text-white">⚡ Lançar Missão Rápida na TV</h3>
              </div>
              <button
                onClick={() => setMissaoRapidaModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSalvarMissaoRapida} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Título da Pauta / Solenidade *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Cobertura Fotográfica da Passagem de Comando"
                  value={novaMissao.titulo_evento}
                  onChange={(e) => setNovaMissao({ ...novaMissao, titulo_evento: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Data</label>
                  <input
                    type="date"
                    required
                    value={novaMissao.data_evento}
                    onChange={(e) => setNovaMissao({ ...novaMissao, data_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Horário</label>
                  <input
                    type="time"
                    required
                    value={novaMissao.hora_evento}
                    onChange={(e) => setNovaMissao({ ...novaMissao, hora_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Local do Evento</label>
                <input
                  type="text"
                  value={novaMissao.local_evento}
                  onChange={(e) => setNovaMissao({ ...novaMissao, local_evento: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setMissaoRapidaModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black shadow-lg shadow-[#c5a059]/25"
                >
                  Salvar & Exibir na TV
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
