import React, { useState, useEffect } from 'react';
import {
  MailCheck,
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Plus,
  Copy,
  Share2,
  FileSpreadsheet,
  QrCode,
  Filter,
  Calendar,
  X,
  UserCheck,
  Printer,
  Award,
  FileText,
  UserPlus,
  TrendingUp,
  Shield,
  HelpCircle,
  MapPin,
  Edit2,
  Trash2,
  Sliders,
  ArrowUpDown,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { JadeConvidado, JadeEvento } from '../../types/database';
import { getBrasiliaDateStr } from '../../utils/formatters';

export const RSVPManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'rsvp' | 'portaria' | 'parecer'>('portaria');
  const [eventos, setEventos] = useState<JadeEvento[]>([]);
  const [selectedEventoId, setSelectedEventoId] = useState<number | null>(null);
  const [convidados, setConvidados] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCat, setFilterCat] = useState<string>('todas');
  const [filterSituacao, setFilterSituacao] = useState<string>('todas');
  const [sortBy, setSortBy] = useState<'antiguidade' | 'alfabetica' | 'checkin' | 'pendentes'>('antiguidade');
  const [modalOpen, setModalOpen] = useState(false);
  const [encaixeModalOpen, setEncaixeModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Modal Gerenciar Eventos / Cerimônias
  const [gerenciarEventosModal, setGerenciarEventosModal] = useState(false);
  const [searchEventoQuery, setSearchEventoQuery] = useState('');

  // Modal Novo Evento
  const [novoEventoModal, setNovoEventoModal] = useState(false);
  const [novoEvento, setNovoEvento] = useState({
    nome: '',
    data_evento: getBrasiliaDateStr(),
    local_evento: 'Salão Nobre do CGCFN',
    tipo_evento: 'cerimonia',
  });

  // Modal Editar Evento
  const [editEventoModal, setEditEventoModal] = useState(false);
  const [editingEvento, setEditingEvento] = useState<JadeEvento | null>(null);

  // Modal Confirmação de Exclusão
  const [deleteConfirmModal, setDeleteConfirmModal] = useState<{ id: number; nome: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Cadastro de Novo Convidado Normal
  const [newConvidado, setNewConvidado] = useState({
    nome: '',
    posto_graduacao: '',
    cargo_funcao: '',
    categoria: 'Militares',
    situacao_militar: 'TTC',
    telefone: '',
    max_acompanhantes: 1,
  });

  // Cadastro de Encaixe de Última Hora na Recepção
  const [newEncaixe, setNewEncaixe] = useState({
    nome: '',
    posto_graduacao: 'CC (FN)',
    situacao_militar: 'TTC',
    categoria: 'Veteranos',
    observacao: 'Compareceu sem confirmação prévia',
  });

  useEffect(() => {
    loadEventos();
  }, []);

  useEffect(() => {
    if (selectedEventoId) {
      loadConvidados(selectedEventoId);
    }
  }, [selectedEventoId]);

  const loadEventos = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('jade_eventos')
        .select('*')
        .order('id', { ascending: false });

      if (!error && data && data.length > 0) {
        // Deduplica eventos por ID único e remove duplicatas com mesmo nome e data
        const uniqueMap = new Map<string, JadeEvento>();
        data.forEach((ev: JadeEvento) => {
          const key = `${ev.nome.trim().toUpperCase()}_${ev.data_evento}`;
          if (!uniqueMap.has(key)) {
            uniqueMap.set(key, ev);
          }
        });

        const distinctEventos = Array.from(uniqueMap.values());
        setEventos(distinctEventos);
        if (!selectedEventoId || !distinctEventos.some((e) => e.id === selectedEventoId)) {
          setSelectedEventoId(distinctEventos[0].id);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar eventos:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadConvidados = async (eventoId: number) => {
    try {
      const { data, error } = await supabase
        .from('jade_convidados')
        .select('*')
        .eq('evento_id', eventoId)
        .order('id', { ascending: false });

      if (!error && data) {
        setConvidados(data);
      }
    } catch (err) {
      console.warn('Erro ao carregar convidados:', err);
    }
  };

  // Helper de Peso para Antiguidade / Precedência Militar
  const getPrecedenceWeight = (posto?: string | null) => {
    if (!posto) return 0;
    const p = posto.toUpperCase();
    if (p.includes('ESQUADRA') || p.includes('AE') || p.includes('EXÉRCITO') || p.includes('BRIGADEIRO DO AR')) return 1000;
    if (p.includes('VICE') || p.includes('VA') || p.includes('DIVISÃO') || p.includes('MAJOR-BRIGADEIRO')) return 900;
    if (p.includes('CONTRA') || p.includes('CA') || p.includes('BRIGADA') || p.includes('BRIGADEIRO')) return 800;
    if (p.includes('CMG') || p.includes('GUERRA') || p.includes('CORONEL')) return 700;
    if (p.includes('CF') || p.includes('FRAGATA') || p.includes('TENENTE-CORONEL')) return 600;
    if (p.includes('CC') || p.includes('CORVETA') || p.includes('MAJOR')) return 500;
    if (p.includes('CT') || p.includes('CAPITÃO-TENENTE') || p.includes('CAPITÃO')) return 400;
    if (p.includes('1TEN') || p.includes('PRIMEIRO-TENENTE')) return 300;
    if (p.includes('2TEN') || p.includes('SEGUNDO-TENENTE')) return 200;
    if (p.includes('GUARDA-MARINHA') || p.includes('GM') || p.includes('ASPIRANTE')) return 150;
    if (p.includes('SO') || p.includes('SUB')) return 100;
    if (p.includes('SGT') || p.includes('SARGENTO')) return 80;
    if (p.includes('CB') || p.includes('CABO')) return 60;
    if (p.includes('SD') || p.includes('SOLDADO') || p.includes('MN') || p.includes('MARINHEIRO')) return 40;
    return 10;
  };

  // Toggle do Check-in no Portão
  const handleToggleCheckin = async (convidadoId: number) => {
    const target = convidados.find((c) => c.id === convidadoId);
    if (!target) return;

    const nextState = !target.checkin_portaria;
    const hora = nextState
      ? new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
      : null;

    setConvidados((prev) =>
      prev.map((c) => (c.id === convidadoId ? { ...c, checkin_portaria: nextState, checkin_hora: hora } : c))
    );

    if (nextState) {
      toast.success(`Check-in confirmado: ${target.posto_graduacao || ''} ${target.nome}`);
    } else {
      toast.info(`Check-in desmarcado: ${target.nome}`);
    }

    try {
      await supabase
        .from('jade_convidados')
        .update({
          checkin_at: nextState ? new Date().toISOString() : null,
          status_confirmacao: nextState ? 'confirmado' : target.status_confirmacao,
        })
        .eq('id', convidadoId);
    } catch (e) {
      console.warn('Erro ao persistir check-in:', e);
    }
  };

  // Criar Novo Evento
  const handleSalvarNovoEvento = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoEvento.nome.trim()) {
      toast.error('Informe o nome do evento.');
      return;
    }

    try {
      const { data, error } = await supabase
        .from('jade_eventos')
        .insert({
          nome: novoEvento.nome.toUpperCase(),
          data_evento: novoEvento.data_evento,
          local: novoEvento.local_evento,
          tipo_layout: 'auditorio',
          status: 'ativo',
        })
        .select()
        .single();

      if (error) throw error;

      confetti({ particleCount: 50, spread: 50 });
      toast.success(`Evento "${novoEvento.nome}" criado com sucesso!`);
      setNovoEventoModal(false);
      setNovoEvento({
        nome: '',
        data_evento: getBrasiliaDateStr(),
        local_evento: 'Salão Nobre do CGCFN',
        tipo_evento: 'cerimonia',
      });
      await loadEventos();
      if (data) setSelectedEventoId(data.id);
    } catch (err: any) {
      toast.error(`Erro ao criar evento: ${err.message}`);
    }
  };

  // Atualizar Evento Existente
  const handleAtualizarEvento = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEvento || !editingEvento.nome.trim()) return;

    try {
      const { error } = await supabase
        .from('jade_eventos')
        .update({
          nome: editingEvento.nome.toUpperCase(),
          data_evento: editingEvento.data_evento,
          local: editingEvento.local,
        })
        .eq('id', editingEvento.id);

      if (error) throw error;

      toast.success('Evento atualizado com sucesso!');
      setEditEventoModal(false);
      setEditingEvento(null);
      await loadEventos();
    } catch (err: any) {
      toast.error(`Erro ao atualizar evento: ${err.message}`);
    }
  };

  // Abrir Modal de Confirmação de Exclusão
  const handleExcluirEvento = (eventoId: number, eventoNome: string) => {
    setDeleteConfirmModal({ id: eventoId, nome: eventoNome });
  };

  // Executar Exclusão Definitiva no Banco
  const executeExcluirEvento = async (eventoId: number, eventoNome: string) => {
    try {
      setIsDeleting(true);

      // 1. Remove convidados do evento
      await supabase.from('jade_convidados').delete().eq('evento_id', eventoId);

      // 2. Remove o evento por ID
      const { error } = await supabase.from('jade_eventos').delete().eq('id', eventoId);
      if (error) {
        console.warn('Erro ao deletar evento por ID:', error);
      }

      // 3. Limpa também duplicatas do mesmo nome se existirem
      await supabase.from('jade_eventos').delete().eq('nome', eventoNome);

      toast.success(`Evento "${eventoNome}" excluído com sucesso.`);
      setDeleteConfirmModal(null);
      setEditEventoModal(false);
      setGerenciarEventosModal(false);

      const remaining = eventos.filter((e) => e.id !== eventoId && e.nome !== eventoNome);
      setEventos(remaining);
      setSelectedEventoId(remaining.length > 0 ? remaining[0].id : null);
      await loadEventos();
    } catch (err: any) {
      toast.error(`Erro ao excluir evento: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Salvar Convidado de Encaixe na Recepção
  const handleCreateEncaixe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEncaixe.nome || !selectedEventoId) {
      toast.error('Informe o nome da autoridade.');
      return;
    }

    try {
      const { data, error } = await supabase
        .from('jade_convidados')
        .insert({
          evento_id: selectedEventoId,
          nome: newEncaixe.nome.toUpperCase(),
          posto_graduacao: newEncaixe.posto_graduacao,
          cargo_funcao: newEncaixe.observacao || 'Encaixe de Recepção',
          categoria: newEncaixe.categoria,
          status_confirmacao: 'confirmado',
          status_placa: 'pendente',
          checkin_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) throw error;

      const newEntry = {
        ...data,
        checkin_portaria: true,
        checkin_hora: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        is_encaixe: true,
      };

      setConvidados((prev) => [newEntry, ...prev]);
      toast.success(`Encaixe registrado e presença confirmada para ${newEncaixe.nome}!`);
      setEncaixeModalOpen(false);
      setNewEncaixe({
        nome: '',
        posto_graduacao: 'CC (FN)',
        situacao_militar: 'TTC',
        categoria: 'Veteranos',
        observacao: 'Compareceu sem confirmação prévia',
      });
    } catch (err: any) {
      toast.error(`Erro ao salvar encaixe: ${err.message}`);
    }
  };

  const handlePrintParecer = () => {
    window.print();
  };

  // Filtros & Ordenação Inteligente
  const filteredConvidados = convidados
    .filter((c) => {
      const matchesSearch =
        c.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.posto_graduacao && c.posto_graduacao.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (c.cargo_funcao && c.cargo_funcao.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesCat = filterCat === 'todas' || c.categoria === filterCat;
      const matchesSit = filterSituacao === 'todas' || (c.situacao_militar || 'Outros') === filterSituacao;

      return matchesSearch && matchesCat && matchesSit;
    })
    .sort((a, b) => {
      if (sortBy === 'antiguidade') {
        const weightA = getPrecedenceWeight(a.posto_graduacao);
        const weightB = getPrecedenceWeight(b.posto_graduacao);
        return weightB - weightA;
      }
      if (sortBy === 'alfabetica') {
        return a.nome.localeCompare(b.nome);
      }
      if (sortBy === 'checkin') {
        if (a.checkin_portaria && !b.checkin_portaria) return -1;
        if (!a.checkin_portaria && b.checkin_portaria) return 1;
        return 0;
      }
      if (sortBy === 'pendentes') {
        if (!a.checkin_portaria && b.checkin_portaria) return -1;
        if (a.checkin_portaria && !b.checkin_portaria) return 1;
        return 0;
      }
      return 0;
    });

  // Estatísticas Estratégicas Consolidadas para o Parecer do Comando
  const totalGeral = convidados.length;
  const totalPresentes = convidados.filter((c) => c.checkin_portaria || c.checkin_at).length;
  const taxaComparecimento = totalGeral > 0 ? Math.round((totalPresentes / totalGeral) * 100) : 0;

  // Breakdown por Situação Militar dos PRESENTES
  const presentesTTC = convidados.filter((c) => (c.checkin_portaria || c.checkin_at) && c.situacao_militar === 'TTC').length;
  const presentesReserva = convidados.filter(
    (c) => (c.checkin_portaria || c.checkin_at) && (c.situacao_militar === 'Reserva' || c.situacao_militar === 'Reserva Remunerada')
  ).length;
  const presentesReformados = convidados.filter(
    (c) => (c.checkin_portaria || c.checkin_at) && c.situacao_militar === 'Reformado'
  ).length;
  const presentesAtiva = convidados.filter(
    (c) => (c.checkin_portaria || c.checkin_at) && (c.situacao_militar === 'Ativa' || !c.situacao_militar)
  ).length;
  const totalEncaixes = convidados.filter((c) => (c.checkin_portaria || c.checkin_at) && c.is_encaixe).length;

  const currentEvento = eventos.find((e) => e.id === selectedEventoId) || eventos[0];

  return (
    <div className="space-y-6 pb-12">
      {/* ── HERO BANNER: DESTAQUE MÁXIMO DO EVENTO SELECIONADO ── */}
      <div className="p-5 rounded-3xl bg-gradient-to-r from-[#0b1222] via-[#111c35] to-[#0b1222] border-2 border-[#00e5ff]/50 shadow-2xl space-y-4 no-print">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-[#00e5ff] text-slate-950 text-[10px] font-black uppercase tracking-wider shadow-sm">
                🎖️ Portaria & Controle de Presenças
              </span>
              <span className="text-slate-400 text-xs">• Cerimonial & Recepção Tática Digital</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#00e5ff] tracking-tight uppercase drop-shadow-md">
              {currentEvento?.nome || 'SELECIONE UM EVENTO'}
            </h1>
            <p className="text-xs text-slate-300 flex items-center gap-3 flex-wrap pt-0.5">
              <span className="flex items-center gap-1 font-bold text-white">
                <Calendar className="w-3.5 h-3.5 text-[#00e5ff]" />
                Data: {currentEvento?.data_evento || 'A Definir'}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <MapPin className="w-3.5 h-3.5 text-[#c5a059]" />
                Local: <strong className="text-white">{currentEvento?.local || 'Salão Nobre / Auditório'}</strong>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <Users className="w-3.5 h-3.5 text-emerald-400" />
                <strong className="text-emerald-400">{totalPresentes}</strong> de {totalGeral} presentes ({taxaComparecimento}% adesão)
              </span>
            </p>
          </div>

          {/* Seleção de Evento e Botões de Ação */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700 px-3.5 py-2 rounded-2xl text-xs shadow-md">
              <Calendar className="w-4 h-4 text-[#00e5ff]" />
              <select
                value={selectedEventoId || ''}
                onChange={(e) => setSelectedEventoId(Number(e.target.value))}
                className="bg-transparent text-white font-bold focus:outline-none cursor-pointer max-w-[190px] truncate"
              >
                {eventos.map((ev) => (
                  <option key={ev.id} value={ev.id} className="bg-slate-900 text-white">
                    {ev.nome} ({ev.data_evento})
                  </option>
                ))}
              </select>
            </div>

            {currentEvento && (
              <>
                <button
                  onClick={() => {
                    setEditingEvento(currentEvento);
                    setEditEventoModal(true);
                  }}
                  className="p-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all"
                  title="Editar Dados deste Evento"
                >
                  <Edit2 className="w-4 h-4" />
                </button>

                <button
                  onClick={() => handleExcluirEvento(currentEvento.id, currentEvento.nome)}
                  className="p-2 rounded-2xl bg-red-500/10 hover:bg-red-500/25 text-red-400 border border-red-500/40 text-xs font-bold transition-all"
                  title="Excluir este Evento e Presenças"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}

            <button
              onClick={() => setGerenciarEventosModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold text-xs shadow-md transition-all hover:scale-105"
              title="Gerenciar Todos os Eventos"
            >
              <Sliders className="w-3.5 h-3.5 text-[#00e5ff]" />
              <span>Gerenciar Eventos</span>
            </button>

            <button
              onClick={() => setNovoEventoModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-cyan-950/60 hover:bg-cyan-900/60 text-[#00e5ff] border border-[#00e5ff]/40 font-bold text-xs shadow-md transition-all hover:scale-105"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Novo Evento</span>
            </button>

            <button
              onClick={() => setEncaixeModalOpen(true)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black text-xs shadow-lg shadow-emerald-600/25 transition-all hover:scale-105"
            >
              <UserPlus className="w-4 h-4" />
              <span>+ Encaixe Portaria</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Navegação entre Abas Estratégicas ── */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto scrollbar-none no-print">
        <button
          onClick={() => setActiveTab('portaria')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'portaria'
              ? 'bg-[#00e5ff] text-slate-950 shadow-md shadow-[#00e5ff]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Check-in Portaria ({totalPresentes}/{totalGeral})</span>
        </button>

        <button
          onClick={() => setActiveTab('parecer')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'parecer'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Parecer Demográfico para o Comando</span>
        </button>

        <button
          onClick={() => setActiveTab('rsvp')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'rsvp'
              ? 'bg-purple-600 text-white shadow-md shadow-purple-600/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <MailCheck className="w-4 h-4" />
          <span>Gestão Pré-Evento (RSVP)</span>
        </button>
      </div>

      {/* ── ABA 1: CHECK-IN DIGITAL NA PORTARIA / RECEPÇÃO ── */}
      {activeTab === 'portaria' && (
        <div className="space-y-4">
          {/* KPI Resumo do Portão */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 no-print">
            <div className="p-4 rounded-2xl bg-[#0b1222] border border-emerald-500/30 bg-emerald-500/5 space-y-1">
              <span className="text-xs font-bold text-emerald-400">Total Presentes no Local</span>
              <p className="text-2xl font-black text-emerald-400">
                {totalPresentes} <span className="text-xs text-slate-400 font-normal">({taxaComparecimento}%)</span>
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-[#c5a059]/30 bg-[#c5a059]/5 space-y-1">
              <span className="text-xs font-bold text-[#e5c07b]">Veteranos TTCs Presentes</span>
              <p className="text-2xl font-black text-[#e5c07b]">{presentesTTC}</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-blue-500/30 bg-blue-500/5 space-y-1">
              <span className="text-xs font-bold text-blue-400">Reserva & Reformados</span>
              <p className="text-2xl font-black text-blue-400">{presentesReserva + presentesReformados}</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-amber-500/30 bg-amber-500/5 space-y-1">
              <span className="text-xs font-bold text-amber-400">Encaixes de Última Hora</span>
              <p className="text-2xl font-black text-amber-400">{totalEncaixes}</p>
            </div>
          </div>

          {/* Barra de Busca, Filtros e Ordenação por Antiguidade */}
          <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-3 no-print">
            <div className="relative flex-1 min-w-0">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Buscar por Nome, Posto ou Cargo..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff]"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              {/* Seletor de Ordenação por Antiguidade / Precedência */}
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-xl text-xs">
                <ArrowUpDown className="w-3.5 h-3.5 text-[#00e5ff]" />
                <span className="text-slate-400 font-bold">Ordem:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="bg-transparent text-[#00e5ff] font-bold focus:outline-none cursor-pointer"
                >
                  <option value="antiguidade" className="bg-slate-900 text-white">
                    🎖️ Antiguidade Militar (Precedência)
                  </option>
                  <option value="alfabetica" className="bg-slate-900 text-white">
                    🔤 Alfabética (A-Z)
                  </option>
                  <option value="checkin" className="bg-slate-900 text-white">
                    ✅ Presentes Primeiro
                  </option>
                  <option value="pendentes" className="bg-slate-900 text-white">
                    ⏳ Pendentes Primeiro
                  </option>
                </select>
              </div>

              {/* Filtro de Categoria */}
              <select
                value={filterCat}
                onChange={(e) => setFilterCat(e.target.value)}
                className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
              >
                <option value="todas">Todas Categorias</option>
                <option value="Autoridades">Autoridades</option>
                <option value="Veteranos">Veteranos</option>
                <option value="Militares">Militares</option>
                <option value="VIP">VIP</option>
              </select>
            </div>
          </div>

          {/* Grid de Convidados na Portaria */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredConvidados.map((guest) => {
              const isPresent = guest.checkin_portaria || guest.checkin_at;

              return (
                <div
                  key={guest.id}
                  className={`p-4 rounded-2xl border transition-all flex items-center justify-between gap-3 ${
                    isPresent
                      ? 'bg-emerald-950/20 border-emerald-500/40 shadow-sm'
                      : 'bg-[#0b1222] border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white text-sm truncate">{guest.nome}</span>
                      {guest.posto_graduacao && (
                        <span className="px-2 py-0.2 rounded bg-slate-900 border border-slate-700 text-[#c5a059] font-mono text-[10px]">
                          {guest.posto_graduacao}
                        </span>
                      )}
                      {guest.is_encaixe && (
                        <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 text-[9px] font-black uppercase">
                          Encaixe
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">
                      {guest.cargo_funcao || guest.categoria || 'Convidado'}
                    </p>
                  </div>

                  <button
                    onClick={() => handleToggleCheckin(guest.id)}
                    className={`px-4 py-2 rounded-xl text-xs font-black transition-all flex items-center gap-1.5 shrink-0 ${
                      isPresent
                        ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                        : 'bg-slate-900 border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isPresent ? 'Presente ✅' : 'Check-in'}</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── ABA 2: PARECER DEMOGRÁFICO PARA O COMANDO ── */}
      {activeTab === 'parecer' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between no-print">
            <h3 className="text-sm font-black text-white">Relatório Consolidado de Presenças</h3>
            <button
              onClick={handlePrintParecer}
              className="px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md"
            >
              <Printer className="w-4 h-4" />
              <span>Imprimir Relatório Oficial</span>
            </button>
          </div>

          <div
            id="printable-rsvp-area"
            className="p-8 rounded-3xl bg-[#0b1222] border border-slate-800 printable-area space-y-6 text-white"
          >
            <div className="text-center space-y-1 border-b border-slate-800 pb-4">
              <p className="text-xs font-black tracking-widest uppercase text-[#c5a059]">
                MARINHA DO BRASIL • COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS
              </p>
              <h2 className="text-xl font-black tracking-tight uppercase">
                PARECER DE EFETIVO E COMPARECIMENTO • {currentEvento?.nome}
              </h2>
              <p className="text-xs text-slate-400">
                Data: {currentEvento?.data_evento} • Local: {currentEvento?.local || 'Salão Nobre / Auditório'}
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
                <span className="text-xs text-slate-400">Convocados / Convidados</span>
                <p className="text-2xl font-black text-white mt-1">{totalGeral}</p>
              </div>
              <div className="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-500/30">
                <span className="text-xs text-emerald-400">Comparecimento Efetivo</span>
                <p className="text-2xl font-black text-emerald-400 mt-1">{totalPresentes}</p>
              </div>
              <div className="p-4 rounded-2xl bg-cyan-950/40 border border-cyan-500/30">
                <span className="text-xs text-cyan-400">Taxa de Adesão</span>
                <p className="text-2xl font-black text-cyan-400 mt-1">{taxaComparecimento}%</p>
              </div>
              <div className="p-4 rounded-2xl bg-amber-950/40 border border-amber-500/30">
                <span className="text-xs text-amber-400">Encaixes sem RSVP</span>
                <p className="text-2xl font-black text-amber-400 mt-1">{totalEncaixes}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 3: GESTÃO PRÉ-EVENTO (RSVP) ── */}
      {activeTab === 'rsvp' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-black text-white">Lista Geral de Confirmações Pré-Evento</h3>
              <p className="text-xs text-slate-400">Envie convites individuais e links RSVP pelo WhatsApp.</p>
            </div>
            <button
              onClick={() => setModalOpen(true)}
              className="px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>+ Convidar Nova Autoridade</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {convidados.map((guest) => (
              <div key={guest.id} className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-white text-xs uppercase">{guest.nome}</h4>
                  <p className="text-[11px] text-slate-400">{guest.cargo_funcao || guest.posto_graduacao || 'Convidado'}</p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                    guest.status_confirmacao === 'confirmado'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-amber-500/20 text-amber-400'
                  }`}
                >
                  {guest.status_confirmacao || 'Pendente'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── MODAL: ENCAIXE DE ÚLTIMA HORA NA PORTARIA ── */}
      {encaixeModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-emerald-500/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-emerald-400" />
                <span>Encaixe de Última Hora na Portaria</span>
              </h3>
              <button onClick={() => setEncaixeModalOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateEncaixe} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Completo / Guerra *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: ALTE SILVA"
                  value={newEncaixe.nome}
                  onChange={(e) => setNewEncaixe({ ...newEncaixe, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-emerald-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Posto / Graduação</label>
                  <input
                    type="text"
                    placeholder="Ex: CMG (FN)"
                    value={newEncaixe.posto_graduacao}
                    onChange={(e) => setNewEncaixe({ ...newEncaixe, posto_graduacao: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Categoria</label>
                  <select
                    value={newEncaixe.categoria}
                    onChange={(e) => setNewEncaixe({ ...newEncaixe, categoria: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="Autoridades">Autoridades</option>
                    <option value="Veteranos">Veteranos</option>
                    <option value="Militares">Militares</option>
                    <option value="VIP">VIP</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Observação / Justificativa</label>
                <input
                  type="text"
                  value={newEncaixe.observacao}
                  onChange={(e) => setNewEncaixe({ ...newEncaixe, observacao: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEncaixeModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black shadow-md"
                >
                  Confirmar Encaixe & Presença
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: GERENCIAR TODOS OS EVENTOS / CERIMÔNIAS ── */}
      {gerenciarEventosModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-2xl p-6 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-black text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-[#00e5ff]" />
                  <span>Gerenciador de Cerimônias & Eventos ({eventos.length})</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  Edite dados, exclua cerimônias antigas ou selecione o evento ativo.
                </p>
              </div>
              <button onClick={() => setGerenciarEventosModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            {/* Busca Rápida de Eventos */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filtrar cerimônia por nome, data ou local..."
                value={searchEventoQuery}
                onChange={(e) => setSearchEventoQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff]"
              />
            </div>

            {/* Lista de Eventos com Ações */}
            <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {eventos
                .filter((ev) => {
                  if (!searchEventoQuery.trim()) return true;
                  const q = searchEventoQuery.toLowerCase();
                  return (
                    ev.nome.toLowerCase().includes(q) ||
                    (ev.data_evento && ev.data_evento.includes(q)) ||
                    (ev.local && ev.local.toLowerCase().includes(q))
                  );
                })
                .map((ev) => {
                  const isActive = ev.id === selectedEventoId;

                  return (
                    <div
                      key={ev.id}
                      className={`p-3.5 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isActive
                          ? 'bg-[#00e5ff]/15 border-[#00e5ff]'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-white text-xs truncate uppercase">{ev.nome}</h4>
                          {isActive && (
                            <span className="px-2 py-0.2 rounded bg-[#00e5ff] text-slate-950 font-black text-[9px] uppercase">
                              Ativo
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 flex items-center gap-2">
                          <span className="text-[#00e5ff] font-bold">📅 {ev.data_evento || 'Sem data'}</span>
                          <span>•</span>
                          <span>📍 {ev.local || 'Salão Nobre'}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {!isActive && (
                          <button
                            onClick={() => {
                              setSelectedEventoId(ev.id);
                              toast.success(`Evento "${ev.nome}" selecionado!`);
                            }}
                            className="px-3 py-1.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/80 text-[#00e5ff] border border-[#00e5ff]/30 text-xs font-bold transition-all"
                          >
                            Selecionar
                          </button>
                        )}

                        <button
                          onClick={() => {
                            setEditingEvento(ev);
                            setEditEventoModal(true);
                          }}
                          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-bold flex items-center gap-1 border border-slate-700"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                          <span>Editar</span>
                        </button>

                        <button
                          onClick={() => handleExcluirEvento(ev.id, ev.nome)}
                          className="p-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  setGerenciarEventosModal(false);
                  setNovoEventoModal(true);
                }}
                className="px-4 py-2 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>+ Criar Novo Evento</span>
              </button>

              <button
                onClick={() => setGerenciarEventosModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white font-bold text-xs"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: EDITAR EVENTO / CERIMÔNIA EXISTENTE ── */}
      {editEventoModal && editingEvento && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-amber-500/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-amber-400" />
                <span>Editar Dados do Evento #{editingEvento.id}</span>
              </h3>
              <button onClick={() => setEditEventoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleAtualizarEvento} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Oficial da Cerimônia *</label>
                <input
                  type="text"
                  required
                  value={editingEvento.nome}
                  onChange={(e) => setEditingEvento({ ...editingEvento, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Data da Cerimônia *</label>
                  <input
                    type="date"
                    required
                    value={editingEvento.data_evento}
                    onChange={(e) => setEditingEvento({ ...editingEvento, data_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Local da Cerimônia</label>
                  <input
                    type="text"
                    value={editingEvento.local || ''}
                    onChange={(e) => setEditingEvento({ ...editingEvento, local: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setEditEventoModal(false);
                    handleExcluirEvento(editingEvento.id, editingEvento.nome);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/30 text-red-400 border border-red-500/40 text-xs font-bold flex items-center gap-1.5 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Excluir Evento</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setEditEventoModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black shadow-md"
                  >
                    Salvar Alterações
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CRIAR NOVO EVENTO / CERIMÔNIA ── */}
      {novoEventoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#00e5ff]" />
                <span>➕ Criar Novo Evento / Cerimônia</span>
              </h3>
              <button onClick={() => setNovoEventoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSalvarNovoEvento} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Oficial da Cerimônia *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: ENCONTRO DE VETERANOS 2026"
                  value={novoEvento.nome}
                  onChange={(e) => setNovoEvento({ ...novoEvento, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Data do Evento *</label>
                  <input
                    type="date"
                    required
                    value={novoEvento.data_evento}
                    onChange={(e) => setNovoEvento({ ...novoEvento, data_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Local da Cerimônia</label>
                  <input
                    type="text"
                    value={novoEvento.local_evento}
                    onChange={(e) => setNovoEvento({ ...novoEvento, local_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setNovoEventoModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black shadow-md"
                >
                  Criar Evento
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* ── MODAL: CONFIRMAÇÃO DE EXCLUSÃO DEFINITIVA DO EVENTO ── */}
      {deleteConfirmModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border border-red-500/50 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <div className="p-3 rounded-2xl bg-red-500/10 border border-red-500/30">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-black text-white">Excluir Cerimônia / Evento</h3>
                <p className="text-xs text-red-300">Esta ação é permanente e irreversível.</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 leading-relaxed">
              Deseja realmente excluir o evento <strong className="text-white font-bold">"{deleteConfirmModal.nome}"</strong>? Todas as presenças e convidados vinculados serão apagados do banco.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setDeleteConfirmModal(null)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-bold text-xs"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => executeExcluirEvento(deleteConfirmModal.id, deleteConfirmModal.nome)}
                className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-black text-xs shadow-lg shadow-red-600/30 transition-all flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isDeleting ? 'Excluindo...' : 'Sim, Excluir Definitivamente'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
