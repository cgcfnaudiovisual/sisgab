import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar as CalendarIcon,
  Clock,
  Users,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  Plus,
  ArrowUpRight,
  Sparkles,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Camera,
  Video,
  Palette,
  Plane,
  Share2,
  Newspaper,
  Bolt,
  Hourglass,
  Layers,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { DemandaComunicacao } from '../../types/database';
import { useAuth } from '../../context/AuthContext';
import { parseCobertura, getBrasiliaDateStr, addDaysBrasilia } from '../../utils/formatters';

const DIAS_SEMANA = ['SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB', 'DOM'];
const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
];

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [demandas, setDemandas] = useState<DemandaComunicacao[]>([]);
  const [loading, setLoading] = useState(true);

  // Estado do Calendário / Agenda
  const hoje = new Date();
  const [calYear, setCalYear] = useState(hoje.getFullYear());
  const [calMonth, setCalMonth] = useState(hoje.getMonth()); // 0-indexed
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // Visão Mensal vs Semanal
  const [viewMode, setViewMode] = useState<'mes' | 'semana'>('mes');

  // Helper para início da semana (Segunda-Feira)
  const getMonday = (d: Date) => {
    const dt = new Date(d);
    const day = dt.getDay();
    const diff = dt.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(dt.setDate(diff));
  };
  const [currentWeekStart, setCurrentWeekStart] = useState<Date>(() => getMonday(new Date()));

  useEffect(() => {
    loadDashboardData();

    // Sincronização em tempo real via Supabase Realtime
    const channel = supabase
      .channel('dashboard-realtime')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'demandas_comunicacao' },
        () => {
          loadDashboardData();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .order('data_evento', { ascending: true });

      if (!error && data) {
        setDemandas(data as DemandaComunicacao[]);
      }
    } catch (err) {
      console.warn('Erro ao carregar demandas do painel:', err);
    } finally {
      setLoading(false);
    }
  };

  // Conclusão Rápida de Demanda em 1 Clique direto no Painel
  const handleQuickConclude = async (dem: DemandaComunicacao) => {
    setDemandas((prev) =>
      prev.map((d) => (d.id === dem.id ? { ...d, status: 'concluida' } : d))
    );

    confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 } });
    toast.success(`🎯 Missão "${dem.titulo_evento}" marcada como CONCLUÍDA!`);

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: 'concluida' })
        .eq('id', dem.id);
    } catch (e) {
      console.warn('Erro ao concluir no Supabase:', e);
    }
  };

  const hojeStr = getBrasiliaDateStr();
  const amanhaStr = addDaysBrasilia(hojeStr, 1);

  // Cálculo dos 9 KPIs Reais da Barra de Comando de Forma Resiliente
  const kpiHoje = demandas.filter((d) => d.data_evento === hojeStr).length;
  const kpiAmanha = demandas.filter((d) => d.data_evento === amanhaStr).length;
  const kpiMes = demandas.filter((d) => {
    if (!d.data_evento) return false;
    const parts = d.data_evento.split('-');
    return parseInt(parts[0], 10) === calYear && parseInt(parts[1], 10) === calMonth + 1;
  }).length;

  const kpiPendentes = demandas.filter((d) => ['pendente', 'ajustes'].includes(d.status || '')).length;
  const kpiExecucao = demandas.filter((d) => ['aprovado', 'em_andamento'].includes(d.status || '')).length;
  const kpiConcluidas = demandas.filter((d) => ['concluida', 'concluido'].includes(d.status || '')).length;

  const kpiUrgentes = demandas.filter(
    (d) => d.sigiloso || (d.score_esforco && d.score_esforco >= 4.0) || (d.titulo_evento || '').includes('⚡')
  ).length;

  const kpiVencidas = demandas.filter((d) => {
    if (!d.data_evento) return false;
    return d.data_evento < hojeStr && !['concluida', 'concluido', 'rejeitado'].includes(d.status || '');
  }).length;

  const kpiCoberturas = demandas.filter((d) => {
    const cobs = parseCobertura(d.tipo_cobertura);
    return cobs.length > 0;
  }).length;

  // Normalizador de Status e Cores
  const getStatusInfo = (rawStatus: string | undefined, isUrgent?: boolean) => {
    const s = (rawStatus || '').toLowerCase().trim();
    if (s === 'rejeitado' || s === 'rejeitada' || s === 'cancelado' || s === 'cancelada') {
      return { label: 'REJEITADO', color: 'red', bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30' };
    }
    if (isUrgent || s === 'urgente') {
      return { label: 'URGENTE', color: 'red', bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30' };
    }
    if (['aprovado', 'aprovada', 'aprovados', 'concluido', 'concluida', 'em_andamento'].includes(s)) {
      return { label: 'APROVADO', color: 'emerald', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30' };
    }
    return { label: 'PENDENTE', color: 'amber', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30' };
  };

  // Helper para verificar se um evento ocorre em uma data (suporte a data_evento até data_fim)
  const isEventOnDate = (d: DemandaComunicacao, targetDate: string) => {
    if (!d.data_evento) return false;
    if (d.data_evento === targetDate) return true;
    if (d.data_fim && d.data_evento <= targetDate && d.data_fim >= targetDate) return true;
    return false;
  };

  // Calendário: dias do mês
  const firstDayOfMonth = new Date(calYear, calMonth, 1);
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  let startDayOfWeek = firstDayOfMonth.getDay() - 1;
  if (startDayOfWeek === -1) startDayOfWeek = 6;

  // Mapa de eventos por dia para os pontinhos do calendário (suportando intervalos de dias)
  const eventosPorDiaMap = new Map<string, string[]>();
  demandas.forEach((d) => {
    if (d.data_evento) {
      const isUrg = Boolean(d.sigiloso || (d.score_esforco && d.score_esforco >= 4.0));
      const st = getStatusInfo(d.status, isUrg).label.toLowerCase();
      // Se tiver data_fim, preenche todos os dias do intervalo
      if (d.data_fim && d.data_fim > d.data_evento) {
        let curr = new Date(d.data_evento + 'T00:00:00');
        const end = new Date(d.data_fim + 'T00:00:00');
        while (curr <= end) {
          const ds = getBrasiliaDateStr(curr);
          const arr = eventosPorDiaMap.get(ds) || [];
          arr.push(st);
          eventosPorDiaMap.set(ds, arr);
          curr.setDate(curr.getDate() + 1);
        }
      } else {
        const arr = eventosPorDiaMap.get(d.data_evento) || [];
        arr.push(st);
        eventosPorDiaMap.set(d.data_evento, arr);
      }
    }
  });

  const navMonth = (offset: number) => {
    let newMonth = calMonth + offset;
    let newYear = calYear;
    if (newMonth < 0) {
      newMonth = 11;
      newYear--;
    } else if (newMonth > 11) {
      newMonth = 0;
      newYear++;
    }
    setCalMonth(newMonth);
    setCalYear(newYear);
    setSelectedDate(null);
  };

  const navWeek = (offset: number) => {
    const next = new Date(currentWeekStart);
    next.setDate(next.getDate() + offset * 7);
    setCurrentWeekStart(next);
    setSelectedDate(null);
  };

  // Gerador de Link Google Calendar Oficial
  const makeGCalUrl = (d: DemandaComunicacao) => {
    const cleanDate = (d.data_evento || '').replace(/-/g, '');
    const cleanTime = (d.hora_evento || '09:00').replace(/:/g, '') + '00';
    const startDt = `${cleanDate}T${cleanTime}`;
    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: `[COMSOC/CGCFN] ${d.titulo_evento || 'Pauta COMSOC'}`,
      dates: `${startDt}/${startDt}`,
      details: `Pauta COMSOC - Solicitante: ${d.solicitante_nome || 'Gabinete'} (${d.setor || 'CGCFN'})\nConta Oficial: cgcfnaudiovisual@gmail.com`,
      location: d.local_evento || 'CGCFN',
    });
    return `https://calendar.google.com/calendar/render?${params.toString()}`;
  };

  // Coberturas filtradas por data selecionada ou próximos compromissos
  const compromissosFiltrados = demandas.filter((d) => {
    if (selectedDate) {
      return d.data_evento === selectedDate;
    }
    return d.data_evento && d.data_evento >= hojeStr;
  });

  return (
    <div className="space-y-6">
      {/* ── HEADER DA PÁGINA ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Gabinete do CGCFN
            </span>
            <span className="text-slate-400 text-xs">• Painel Unificado de Comando</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
            PAINEL DE COMANDO & AGENDA
          </h1>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <a
            href="https://calendar.google.com/calendar/u/0?cid=Y2djZm5hdWRpb3Zpc3VhbEBnbWFpbC5jb20"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-950/50 hover:bg-cyan-900/60 text-[#00e5ff] border border-[#00e5ff]/30 text-xs font-bold transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Google Calendar Oficial</span>
          </a>

          <button
            onClick={() => navigate('/comsoc_demandas')}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs shadow-md shadow-[#c5a059]/20 transition-all hover:scale-105 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Nova Pauta</span>
          </button>
        </div>
      </div>

      {/* ── ALERTA DE PENDÊNCIAS (Para Chefes & Supervisores) ── */}
      {kpiPendentes > 0 && (
        <div className="p-3.5 sm:p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between gap-3 shadow-lg animate-in fade-in">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-400 animate-pulse shrink-0" />
            <span className="text-xs sm:text-sm font-black text-amber-400">
              ⚠️ {kpiPendentes} demanda(s) aguardando homologação do Chefe de Gabinete.
            </span>
          </div>
          <button
            onClick={() => navigate('/comsoc_homologar')}
            className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs shrink-0 transition-transform active:scale-95"
          >
            Tramitar →
          </button>
        </div>
      )}

      {/* ── BARRA COMPLETA DE 9 KPIs CLICÁVEIS ── */}
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2">
        {/* KPI 1: HOJE */}
        <div
          onClick={() => setSelectedDate(hojeStr)}
          className="p-2.5 rounded-xl bg-[#c5a059]/10 border border-[#c5a059]/30 hover:border-[#c5a059] cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">HOJE</span>
          <p className="text-xl font-black text-[#c5a059] mt-0.5">{kpiHoje}</p>
        </div>

        {/* KPI 2: AMANHÃ */}
        <div
          onClick={() => setSelectedDate(amanhaStr)}
          className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 hover:border-purple-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">AMANHÃ</span>
          <p className="text-xl font-black text-purple-400 mt-0.5">{kpiAmanha}</p>
        </div>

        {/* KPI 3: DEMANDAS MÊS */}
        <div
          onClick={() => setSelectedDate(null)}
          className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 hover:border-amber-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">MÊS</span>
          <p className="text-xl font-black text-amber-400 mt-0.5">{kpiMes}</p>
        </div>

        {/* KPI 4: PENDENTES */}
        <div
          onClick={() => navigate('/comsoc_homologar')}
          className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 hover:border-amber-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">PENDENTES</span>
          <p className="text-xl font-black text-amber-400 mt-0.5">{kpiPendentes}</p>
        </div>

        {/* KPI 5: EM EXECUÇÃO */}
        <div
          onClick={() => navigate('/comsoc_tarefas')}
          className="p-2.5 rounded-xl bg-[#00e5ff]/10 border border-[#00e5ff]/30 hover:border-[#00e5ff] cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">EXECUÇÃO</span>
          <p className="text-xl font-black text-[#00e5ff] mt-0.5">{kpiExecucao}</p>
        </div>

        {/* KPI 6: CONCLUÍDAS */}
        <div
          onClick={() => navigate('/comsoc_historico')}
          className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 hover:border-emerald-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-slate-400 uppercase">CONCLUÍDAS</span>
          <p className="text-xl font-black text-emerald-400 mt-0.5">{kpiConcluidas}</p>
        </div>

        {/* KPI 7: URGENTES */}
        <div
          onClick={() => navigate('/comsoc_homologar')}
          className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/30 hover:border-orange-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-orange-400 uppercase">⚡ URGENTES</span>
          <p className="text-xl font-black text-orange-400 mt-0.5">{kpiUrgentes}</p>
        </div>

        {/* KPI 8: VENCIDAS */}
        <div
          onClick={() => navigate('/comsoc_homologar')}
          className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 hover:border-red-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-red-400 uppercase">VENCIDAS</span>
          <p className="text-xl font-black text-red-400 mt-0.5">{kpiVencidas}</p>
        </div>

        {/* KPI 9: COBERTURAS */}
        <div
          onClick={() => setSelectedDate(null)}
          className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 hover:border-cyan-400 cursor-pointer transition-all flex flex-col justify-between"
        >
          <span className="text-[9px] font-black text-cyan-400 uppercase">COBERTURAS</span>
          <p className="text-xl font-black text-cyan-400 mt-0.5">{kpiCoberturas}</p>
        </div>
      </div>

      {/* ── CALENDÁRIO & AGENDA NATIVA (VISÃO MENSAL E SEMANAL) ── */}
      <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
        {/* Barra Superior de Controles e Toggle */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
          {/* Navegação de Data */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => (viewMode === 'mes' ? navMonth(-1) : navWeek(-1))}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-colors"
              title={viewMode === 'mes' ? 'Mês Anterior' : 'Semana Anterior'}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="text-sm font-black text-white uppercase tracking-wider min-w-[160px] text-center">
              {viewMode === 'mes'
                ? `${MESES[calMonth]} de ${calYear}`
                : `Semana de ${currentWeekStart.getDate()} de ${MESES[currentWeekStart.getMonth()]}`}
            </span>

            <button
              onClick={() => (viewMode === 'mes' ? navMonth(1) : navWeek(1))}
              className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-colors"
              title={viewMode === 'mes' ? 'Próximo Mês' : 'Próxima Semana'}
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                const now = new Date();
                setCalMonth(now.getMonth());
                setCalYear(now.getFullYear());
                setCurrentWeekStart(getMonday(now));
                setSelectedDate(hojeStr);
              }}
              className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[11px] font-bold text-[#c5a059] transition-colors ml-1"
            >
              Hoje
            </button>
          </div>

          {/* Toggle de Visão (Mensal vs Semanal) & Legenda */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800">
              <button
                onClick={() => setViewMode('mes')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  viewMode === 'mes'
                    ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                📅 Mensal
              </button>
              <button
                onClick={() => setViewMode('semana')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  viewMode === 'semana'
                    ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🗓️ Semanal
              </button>
            </div>

            {selectedDate && (
              <button
                onClick={() => setSelectedDate(null)}
                className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[#00e5ff] text-xs font-bold transition-colors"
              >
                Limpar Filtro
              </button>
            )}
          </div>
        </div>

        {/* ── MODO 1: VISÃO MENSAL ── */}
        {viewMode === 'mes' && (
          <div className="space-y-2">
            <div className="grid grid-cols-7 gap-1 text-center">
              {DIAS_SEMANA.map((dia) => (
                <div key={dia} className="text-[10px] font-bold text-slate-500 py-1">
                  {dia}
                </div>
              ))}

              {/* Células Vazias no Início do Mês */}
              {Array.from({ length: startDayOfWeek }).map((_, i) => (
                <div key={`empty-${i}`} className="p-2 min-h-[50px] opacity-20"></div>
              ))}

              {/* Dias do Mês */}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const dayNum = i + 1;
                const dayStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
                const isToday = dayStr === hojeStr;
                const isSelected = dayStr === selectedDate;
                const dayEvents = eventosPorDiaMap.get(dayStr) || [];

                return (
                  <button
                    key={dayStr}
                    onClick={() => setSelectedDate(isSelected ? null : dayStr)}
                    className={`p-1.5 rounded-xl border text-center transition-all min-h-[52px] flex flex-col justify-between items-center ${
                      isSelected
                        ? 'bg-[#c5a059]/25 border-[#c5a059] ring-2 ring-[#c5a059]/40 text-[#e5c07b]'
                        : isToday
                        ? 'bg-[#c5a059]/10 border-[#c5a059]/40 text-[#c5a059] font-black'
                        : 'bg-slate-900/60 border-slate-800/80 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    <span className="text-xs font-bold">{dayNum}</span>

                    {/* Bolinhas Indicadoras de Eventos */}
                    <div className="flex items-center gap-1 min-h-[6px]">
                      {dayEvents.slice(0, 3).map((st, idx) => (
                        <span
                          key={idx}
                          className={`w-1.5 h-1.5 rounded-full ${
                            st === 'aprovado' || st === 'concluida'
                              ? 'bg-emerald-400'
                              : st === 'pendente'
                              ? 'bg-amber-400'
                              : 'bg-red-400'
                          }`}
                        ></span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── MODO 2: VISÃO SEMANAL MINIMALISTA (7 COLUNAS COM EVENTOS DETALHADOS) ── */}
        {viewMode === 'semana' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2.5">
            {Array.from({ length: 7 }).map((_, i) => {
              const d = new Date(currentWeekStart);
              d.setDate(d.getDate() + i);
              const dayStr = getBrasiliaDateStr(d);
              const dayEvents = demandas.filter((dem) => isEventOnDate(dem, dayStr));
              const isToday = dayStr === hojeStr;
              const isSelected = dayStr === selectedDate;

              return (
                <div
                  key={dayStr}
                  onClick={() => setSelectedDate(isSelected ? null : dayStr)}
                  className={`p-2.5 rounded-2xl border transition-all flex flex-col min-h-[220px] cursor-pointer ${
                    isSelected
                      ? 'bg-[#c5a059]/15 border-[#c5a059] ring-1 ring-[#c5a059]/50 shadow-lg'
                      : isToday
                      ? 'bg-slate-900/90 border-[#c5a059]/40 shadow-md'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {/* Cabeçalho do Dia */}
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800/60 mb-2">
                    <span className="text-[11px] font-black text-slate-400 uppercase tracking-wider">
                      {DIAS_SEMANA[i]}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-lg font-black ${
                        isToday
                          ? 'bg-[#c5a059] text-slate-950 shadow-sm'
                          : 'bg-slate-900 text-slate-200 border border-slate-800'
                      }`}
                    >
                      {d.getDate()}/{String(d.getMonth() + 1).padStart(2, '0')}
                    </span>
                  </div>

                  {/* Lista Minimalista de Pautas do Dia */}
                  <div className="space-y-1.5 flex-1 overflow-y-auto max-h-[220px] scrollbar-none">
                    {dayEvents.length === 0 ? (
                      <div className="h-full flex items-center justify-center text-center py-6 text-[11px] text-slate-600">
                        Livre
                      </div>
                    ) : (
                      dayEvents.map((ev) => {
                        const coberturas = parseCobertura(ev.tipo_cobertura);
                        const isMultiDay = ev.data_fim && ev.data_fim > ev.data_evento;
                        const isUrg = Boolean(ev.sigiloso || (ev.score_esforco && ev.score_esforco >= 4.0));
                        const stInfo = getStatusInfo(ev.status, isUrg);

                        return (
                          <div
                            key={ev.id}
                            className={`p-2 rounded-xl border text-left space-y-1 transition-all hover:scale-[1.02] ${stInfo.bg} ${stInfo.border}`}
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="text-[10px] font-black text-[#00e5ff] flex items-center gap-1">
                                <Clock className="w-2.5 h-2.5" />
                                {ev.hora_evento || '09:00'}
                              </span>
                              <span
                                className={`text-[8px] font-black uppercase px-1 py-0.2 rounded ${stInfo.text} bg-black/40`}
                              >
                                {stInfo.label}
                              </span>
                            </div>

                            <p className="text-[11px] font-bold text-white line-clamp-2 leading-tight">
                              {ev.titulo_evento}
                            </p>

                            <div className="flex items-center justify-between gap-1 text-[9px] text-slate-400">
                              <span className="truncate">{ev.solicitante_nome} ({ev.setor || 'CGCFN'})</span>
                              {isMultiDay && (
                                <span className="px-1 py-0.2 rounded bg-cyan-500/20 text-cyan-300 font-bold whitespace-nowrap text-[8px]">
                                  Até {ev.data_fim?.split('-').reverse().slice(0, 2).join('/')}
                                </span>
                              )}
                            </div>

                            {/* Micro Ícones de Cobertura */}
                            {coberturas.length > 0 && (
                              <div className="flex items-center gap-1 pt-0.5">
                                {coberturas.slice(0, 3).map((cob, cIdx) => (
                                  <span
                                    key={cIdx}
                                    className="text-[9px] px-1 py-0.2 rounded bg-slate-950 text-slate-300 border border-slate-800 flex items-center gap-0.5"
                                  >
                                    {cob.includes('Foto') && <Camera className="w-2.5 h-2.5 text-cyan-400" />}
                                    {cob.includes('Vídeo') && <Video className="w-2.5 h-2.5 text-pink-400" />}
                                    {cob.includes('Drone') && <Plane className="w-2.5 h-2.5 text-amber-400" />}
                                    <span>{cob}</span>
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── LISTA DE PRÓXIMOS COMPROMISSOS (PAUTAS DO BANCO DE DADOS) ── */}
      <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarIcon className="w-4 h-4 text-[#00e5ff]" />
            <h2 className="text-sm font-black text-white uppercase tracking-wider">
              {selectedDate
                ? `Compromissos para ${selectedDate}`
                : `Próximos Compromissos & Pautas (${compromissosFiltrados.length})`}
            </h2>
          </div>

          <span className="text-xs text-slate-400">
            Total no banco: <strong className="text-white">{demandas.length}</strong>
          </span>
        </div>

        <div className="divide-y divide-slate-800/80">
          {compromissosFiltrados.slice(0, 8).map((dem) => {
            const coberturas = parseCobertura(dem.tipo_cobertura);

            return (
              <div
                key={dem.id}
                className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors rounded-xl"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-bold border ${
                        dem.data_fim && dem.data_fim > dem.data_evento
                          ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                          : !dem.data_evento || dem.data_evento === 'SEM_DATA'
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          : 'bg-blue-500/15 text-blue-300 border-blue-500/30'
                      }`}
                    >
                      {dem.data_fim && dem.data_fim > dem.data_evento
                        ? `🗓️ ${dem.data_evento} até ${dem.data_fim}`
                        : !dem.data_evento || dem.data_evento === 'SEM_DATA'
                        ? '⏳ Sem Data Prevista (A Definir)'
                        : `${dem.data_evento} às ${dem.hora_evento || '09:00'}`}
                    </span>
                    <span className="text-xs font-black text-white truncate">
                      {dem.titulo_evento}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                        dem.status === 'aprovado'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : dem.status === 'pendente'
                          ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          : 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                      }`}
                    >
                      {dem.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400">
                    📍 Local: <strong className="text-slate-300">{dem.local_evento || 'CGCFN'}</strong> • Solicitante: <strong className="text-slate-300">{dem.solicitante_nome}</strong> ({dem.setor})
                  </p>

                  {/* Ícones de Cobertura */}
                  {coberturas.length > 0 && (
                    <div className="flex items-center gap-1.5 pt-1">
                      {coberturas.map((cob, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 font-medium"
                        >
                          {cob}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Botões de Ação Rápida */}
                <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                  {['aprovado', 'em_andamento'].includes(dem.status || '') && (
                    <button
                      type="button"
                      onClick={() => handleQuickConclude(dem)}
                      className="px-2.5 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-bold transition-all flex items-center gap-1 hover:scale-105"
                      title="Concluir Demanda Imediatamente"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Concluir</span>
                    </button>
                  )}

                  <a
                    href={makeGCalUrl(dem)}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#00e5ff] text-xs font-bold text-[#00e5ff] hover:text-white transition-colors flex items-center gap-1"
                    title="Exportar para Google Calendar"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">GCal</span>
                  </a>

                  <button
                    onClick={() => navigate('/comsoc_homologar')}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#c5a059] to-amber-500 hover:from-amber-500 hover:to-[#c5a059] text-slate-950 font-bold text-xs shadow-md shadow-[#c5a059]/20 transition-all hover:scale-105 flex items-center gap-1"
                    title="Abrir Ficha Técnica / Homologação"
                  >
                    <span>📋 Ficha / Homologar</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── FEED DE NOTÍCIAS NAVAIS ── */}
      <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-[#c5a059]" />
            <h2 className="text-xs font-black text-white uppercase tracking-wider">
              Feed Rápido — Informativos & Notícias Navais
            </h2>
          </div>
          <span className="text-[11px] text-slate-400 font-semibold">Poder Naval • Agência Marinha</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          <a
            href="https://agencia.marinha.mil.br/"
            target="_blank"
            rel="noreferrer"
            className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-[#c5a059]/50 transition-all block space-y-1 group"
          >
            <span className="text-[10px] font-bold text-[#c5a059] uppercase">Agência Marinha de Notícias</span>
            <p className="text-xs font-bold text-white group-hover:text-[#e5c07b] transition-colors">
              Marinha do Brasil realiza Operação de Prontidão e Patrulha Naval no Atlântico Sul
            </p>
          </a>

          <a
            href="https://www.naval.com.br/"
            target="_blank"
            rel="noreferrer"
            className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-[#c5a059]/50 transition-all block space-y-1 group"
          >
            <span className="text-[10px] font-bold text-[#00e5ff] uppercase">Poder Naval</span>
            <p className="text-xs font-bold text-white group-hover:text-[#00e5ff] transition-colors">
              Corpo de Fuzileiros Navais intensifica exercícios expedicionários e operações anfíbias
            </p>
          </a>
        </div>
      </div>
    </div>
  );
};
