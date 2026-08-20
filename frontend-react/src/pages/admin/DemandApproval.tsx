import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useMemo } from 'react';
import {
  Gavel,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Calendar,
  MapPin,
  Camera,
  ExternalLink,
  MessageSquare,
  Sparkles,
  Filter,
  Search,
  LayoutGrid,
  List,
  CheckSquare,
  Square,
  FolderOpen,
  FolderPlus,
  Eye,
  RotateCcw,
  User,
  Building2,
  Layers,
  TrendingUp,
  FileText,
  Edit3,
  Save,
  Palette,
  Printer,
  Gift,
  Music,
} from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../api/supabase';
import type { DemandaComunicacao } from '../../types/database';
import { useAuth } from '../../context/AuthContext';
import { parseCobertura, getBrasiliaDateStr, addDaysBrasilia } from '../../utils/formatters';

export const DemandApproval: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [demandas, setDemandas] = useState<DemandaComunicacao[]>([]);
  const [activeTab, setActiveTab] = useState<'pendente' | 'aprovado' | 'ajustes' | 'rejeitado' | 'todas'>('pendente');
  const [viewMode, setViewMode] = useState<'cards' | 'tabela'>('cards');
  const [searchQuery, setSearchQuery] = useState('');
  const [serviceFilter, setServiceFilter] = useState<string>('todos');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal Parecer Técnico
  const [parecerModal, setParecerModal] = useState<{
    isOpen: boolean;
    demanda: DemandaComunicacao | null;
    action: 'ajustes' | 'rejeitado';
    motivo: string;
  }>({
    isOpen: false,
    demanda: null,
    action: 'ajustes',
    motivo: '',
  });

  // Modal Detalhes / Ficha Completa & Edição
  const [detailModal, setDetailModal] = useState<DemandaComunicacao | null>(null);
  const [isEditingFicha, setIsEditingFicha] = useState(false);
  const [editForm, setEditForm] = useState<Partial<DemandaComunicacao>>({});
  const [savingEdit, setSavingEdit] = useState(false);
  const [creatingDriveId, setCreatingDriveId] = useState<number | null>(null);

  const handleOpenDetailModal = (demanda: DemandaComunicacao, editMode = false) => {
    setDetailModal(demanda);
    setIsEditingFicha(editMode);
    setEditForm({ ...demanda });
  };

  // Criação Automática de Pasta no Google Drive
  const handleCriarPastaDrive = async (demanda: DemandaComunicacao, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    try {
      setCreatingDriveId(demanda.id);
      toast.loading(`Criando pasta no Google Drive para "${demanda.titulo_evento}"...`, { id: `drive_${demanda.id}` });

      const res = await fetch('/api/drive/create_event_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo_evento: demanda.titulo_evento,
          data_evento: demanda.data_evento || getBrasiliaDateStr(),
          demanda_id: demanda.id,
        }),
      });

      const json = await res.json();
      if (json.ok && json.evento_link) {
        militaryAudio.playTacticalBeep();
        toast.success(`Pasta criada com sucesso no Google Drive!`, {
          id: `drive_${demanda.id}`,
          action: {
            label: 'Abrir Pasta',
            onClick: () => window.open(json.evento_link, '_blank'),
          },
        });

        const newAut = `${demanda.autoridades || ''} [DRIVE: ${json.evento_link}]`.trim();

        setDemandas((prev) =>
          prev.map((d) =>
            d.id === demanda.id
              ? {
                  ...d,
                  drive_url: json.evento_link,
                  autoridades: newAut,
                }
              : d
          )
        );

        if (detailModal && detailModal.id === demanda.id) {
          setDetailModal((prev) =>
            prev
              ? {
                  ...prev,
                  drive_url: json.evento_link,
                  autoridades: newAut,
                }
              : null
          );
        }

        if (editForm && editForm.id === demanda.id) {
          setEditForm((prev) => ({
            ...prev,
            drive_url: json.evento_link,
          }));
        }
      } else {
        toast.error(`Falha ao criar pasta: ${json.error || 'Erro desconhecido'}`, { id: `drive_${demanda.id}` });
      }
    } catch (err: any) {
      toast.error(`Erro de conexão com o servidor: ${err.message}`, { id: `drive_${demanda.id}` });
    } finally {
      setCreatingDriveId(null);
    }
  };

  const handleSaveEditFicha = async () => {
    if (!detailModal || !editForm.titulo_evento) {
      toast.error('O título do evento é obrigatório.');
      return;
    }

    setSavingEdit(true);
    try {
      const updatedItem: DemandaComunicacao = {
        ...detailModal,
        titulo_evento: editForm.titulo_evento || detailModal.titulo_evento,
        data_evento: editForm.data_evento || detailModal.data_evento,
        data_fim: editForm.data_fim !== undefined ? editForm.data_fim : detailModal.data_fim,
        hora_evento: editForm.hora_evento || detailModal.hora_evento,
        local_evento: editForm.local_evento || detailModal.local_evento,
        solicitante_nome: editForm.solicitante_nome || detailModal.solicitante_nome,
        setor: editForm.setor || detailModal.setor,
        contato: editForm.contato || detailModal.contato,
        categoria_demanda: editForm.categoria_demanda || detailModal.categoria_demanda,
        produto_especifico: editForm.produto_especifico || detailModal.produto_especifico,
        drive_url: editForm.drive_url || detailModal.drive_url,
        tipo_cobertura: Array.isArray(editForm.tipo_cobertura)
          ? editForm.tipo_cobertura
          : typeof editForm.tipo_cobertura === 'string'
          ? (editForm.tipo_cobertura as string).split(',').map((s) => s.trim()).filter(Boolean)
          : detailModal.tipo_cobertura,
        autoridades: editForm.autoridades !== undefined ? editForm.autoridades : detailModal.autoridades,
        observacoes: editForm.observacoes !== undefined ? editForm.observacoes : detailModal.observacoes,
        score_esforco: editForm.score_esforco || detailModal.score_esforco || 1,
      };

      // Constrói autoridades com tag de Drive resiliente se houver drive_url
      const driveUrlTrimmed = updatedItem.drive_url?.trim();
      const autLimpa = cleanAutoridades(updatedItem.autoridades);
      const finalAutoridades = driveUrlTrimmed
        ? (autLimpa ? `${autLimpa} [DRIVE: ${driveUrlTrimmed}]` : `[DRIVE: ${driveUrlTrimmed}]`)
        : autLimpa;

      const { error } = await supabase
        .from('demandas_comunicacao')
        .update({
          titulo_evento: updatedItem.titulo_evento,
          data_evento: updatedItem.data_evento,
          data_fim: updatedItem.data_fim,
          hora_evento: updatedItem.hora_evento,
          local_evento: updatedItem.local_evento,
          solicitante_nome: updatedItem.solicitante_nome,
          setor: updatedItem.setor,
          contato: updatedItem.contato,
          tipo_cobertura: updatedItem.tipo_cobertura,
          autoridades: finalAutoridades,
          score_esforco: updatedItem.score_esforco,
          categoria_demanda: updatedItem.categoria_demanda,
          produto_especifico: updatedItem.observacoes || updatedItem.produto_especifico || '',
        })
        .eq('id', detailModal.id);

      if (error) throw error;

      if (driveUrlTrimmed) {
        try {
          await fetch('/api/drive/save_drive_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              demanda_id: detailModal.id,
              titulo_evento: updatedItem.titulo_evento,
              drive_url: driveUrlTrimmed,
            }),
          });
        } catch (_) {}
      }

      setDemandas((prev) =>
        prev.map((d) => (d.id === detailModal.id ? updatedItem : d))
      );
      setDetailModal(updatedItem);
      setIsEditingFicha(false);

      militaryAudio.playTacticalBeep();
      toast.success('Ficha técnica da pauta atualizada com sucesso!');
    } catch (err: any) {
      toast.error(`Erro ao salvar edição: ${err.message || 'Falha de conexão.'}`);
    } finally {
      setSavingEdit(false);
    }
  };

  useEffect(() => {
    loadDemandas();

    const channel = supabase
      .channel('demandas-approval-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'demandas_comunicacao' },
        () => {
          loadDemandas();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const loadDemandas = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .order('data_evento', { ascending: false, nullsFirst: false });

      if (!error && data) {
        setDemandas(data as DemandaComunicacao[]);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  // Helper para extrair URL do Drive de textos brutos
  const extractDriveUrl = (dem: DemandaComunicacao) => {
    if (dem.drive_url && dem.drive_url.startsWith('http')) return dem.drive_url;
    const combined = `${dem.observacoes || ''} ${dem.autoridades || ''}`;
    const match = combined.match(/https:\/\/drive\.google\.com[^\s\]]+/);
    return match ? match[0] : null;
  };

  // Helper para limpar o campo autoridades removendo tags e links de Drive
  const cleanAutoridades = (raw?: string | null) => {
    if (!raw) return '';
    return raw
      .replace(/\[DRIVE:[^\]]+\]/gi, '')
      .replace(/https:\/\/drive\.google\.com[^\s]+/gi, '')
      .replace(/Obs:?\s*Horário[^\.]+/gi, '')
      .trim();
  };

  // 1. Aprovação Individual
  const handleApprove = async (demanda: DemandaComunicacao) => {
    setDemandas((prev) =>
      prev.map((d) => (d.id === demanda.id ? { ...d, status: 'aprovado' } : d))
    );

    militaryAudio.playTacticalBeep();

    toast.success(`Pauta "${demanda.titulo_evento}" homologada com sucesso!`, {
      description: 'Status atualizado para APROVADO.',
    });

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: 'aprovado' })
        .eq('id', demanda.id);
    } catch (e) {
      console.warn('Erro ao aprovar no Supabase:', e);
    }
  };

  // 2. Reabrir / Mudar Status
  const handleReopen = async (demanda: DemandaComunicacao, novoStatus: 'pendente' | 'aprovado' | 'ajustes') => {
    setDemandas((prev) =>
      prev.map((d) => (d.id === demanda.id ? { ...d, status: novoStatus } : d))
    );

    toast.info(`Demanda atualizada para "${novoStatus.toUpperCase()}".`);

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: novoStatus })
        .eq('id', demanda.id);
    } catch (e) {
      console.warn('Erro ao atualizar status:', e);
    }
  };

  // 2.1 Concluir / Finalizar Missão (1 Clique)
  const handleConclude = async (demanda: DemandaComunicacao) => {
    setDemandas((prev) =>
      prev.map((d) => (d.id === demanda.id ? { ...d, status: 'concluida' } : d))
    );

    militaryAudio.playTacticalBeep();
    toast.success(`🎯 Missão "${demanda.titulo_evento}" concluída com sucesso!`);

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: 'concluida' })
        .eq('id', demanda.id);
    } catch (e) {
      console.warn('Erro ao concluir no Supabase:', e);
    }
  };

  // 3. Aprovação em Lote (Batch)
  const handleBatchApprove = async () => {
    if (selectedIds.length === 0) return;

    setDemandas((prev) =>
      prev.map((d) => (selectedIds.includes(d.id) ? { ...d, status: 'aprovado' } : d))
    );

    militaryAudio.playTacticalBeep();
    toast.success(`🎉 ${selectedIds.length} pautas homologadas em lote com sucesso!`);

    const idsToUpdate = [...selectedIds];
    setSelectedIds([]);

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: 'aprovado' })
        .in('id', idsToUpdate);
    } catch (e) {
      console.warn('Erro na aprovação em lote:', e);
    }
  };

  // 4. Salvar Parecer Técnico
  const handleSaveParecer = async () => {
    if (!parecerModal.demanda || !parecerModal.motivo) {
      toast.error('Informe o motivo ou parecer técnico.');
      return;
    }

    const { demanda, action, motivo } = parecerModal;

    setDemandas((prev) =>
      prev.map((d) => (d.id === demanda.id ? { ...d, status: action, observacoes: motivo } : d))
    );

    toast.info(`Demanda atualizada para "${action.toUpperCase()}".`);
    setParecerModal({ isOpen: false, demanda: null, action: 'ajustes', motivo: '' });

    try {
      await supabase
        .from('demandas_comunicacao')
        .update({ status: action, produto_especifico: motivo })
        .eq('id', demanda.id);
    } catch (e) {
      console.warn('Erro ao salvar parecer:', e);
    }
  };

  // ── FILTROS E PESQUISA INTELIGENTE ──
  const filteredDemandas = useMemo(() => {
    return demandas.filter((d) => {
      // Filtro por Aba de Status
      if (activeTab !== 'todas' && d.status !== activeTab) return false;

      // Filtro por Categoria / Serviço / Drive
      if (serviceFilter !== 'todos') {
        if (serviceFilter === 'com_drive') {
          if (!extractDriveUrl(d)) return false;
        } else if (serviceFilter === 'sem_drive') {
          if (extractDriveUrl(d)) return false;
        } else {
          const cobs = parseCobertura(d.tipo_cobertura).map((c) => c.toLowerCase());
          const cat = (d.categoria_demanda || '').toLowerCase();
          const prod = (d.produto_especifico || '').toLowerCase();
          const qFilter = serviceFilter.toLowerCase();
          const matchCob = cobs.some((c) => c.includes(qFilter));
          const matchCat = cat.includes(qFilter);
          const matchProd = prod.includes(qFilter);
          if (!matchCob && !matchCat && !matchProd) return false;
        }
      }

      // Filtro por Busca de Texto
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = (d.titulo_evento || '').toLowerCase().includes(q);
        const matchReq = (d.solicitante_nome || '').toLowerCase().includes(q);
        const matchSetor = (d.setor || '').toLowerCase().includes(q);
        const matchLocal = (d.local_evento || '').toLowerCase().includes(q);
        const matchAut = (d.autoridades || '').toLowerCase().includes(q);
        if (!matchTitle && !matchReq && !matchSetor && !matchLocal && !matchAut) return false;
      }

      return true;
    });
  }, [demandas, activeTab, serviceFilter, searchQuery]);

  // KPIs
  const kpiPendentes = demandas.filter((d) => d.status === 'pendente').length;
  const kpiAprovadas = demandas.filter((d) => d.status === 'aprovado').length;
  const kpiAjustes = demandas.filter((d) => d.status === 'ajustes').length;

  const hojeStr = getBrasiliaDateStr();
  const seteDiasStr = addDaysBrasilia(hojeStr, 7);
  const kpiProximos7Dias = demandas.filter(
    (d) => d.data_evento && d.data_evento >= hojeStr && d.data_evento <= seteDiasStr
  ).length;

  const totalScoreEsforco = useMemo(() => {
    return demandas
      .filter((d) => d.status === 'pendente' || d.status === 'aprovado')
      .reduce((acc, curr) => acc + (Number(curr.score_esforco) || 1), 0);
  }, [demandas]);

  // Toggle Seleção
  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredDemandas.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredDemandas.map((d) => d.id));
    }
  };

  return (
    <div className="space-y-5">
      {/* ── HEADER DA PÁGINA ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-xs font-bold uppercase tracking-wider border border-amber-500/40">
              Parecer Técnico & Homologação
            </span>
            <span className="text-slate-400 text-xs">• Gestão de Pautas da Chefia</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
            HOMOLOGAÇÃO DE DEMANDAS
          </h1>
        </div>

        {/* Botão de Ação Rápida em Lote */}
        {selectedIds.length > 0 && activeTab === 'pendente' && (
          <button
            onClick={handleBatchApprove}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/20 transition-all animate-bounce"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Homologar {selectedIds.length} Pautas Selecionadas</span>
          </button>
        )}
      </div>

      {/* ── BARRA DE KPIS TÁTICOS (RESUMO EXECUTIVO) ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-amber-500/30 flex items-center justify-between shadow-md">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Aguardando Parecer</span>
            <p className="text-xl font-black text-white">{kpiPendentes}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
            <Clock className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-emerald-500/30 flex items-center justify-between shadow-md">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Homologadas</span>
            <p className="text-xl font-black text-white">{kpiAprovadas}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-cyan-500/30 flex items-center justify-between shadow-md">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">Próximos 7 Dias</span>
            <p className="text-xl font-black text-white">{kpiProximos7Dias}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400">
            <Calendar className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-purple-500/30 flex items-center justify-between shadow-md">
          <div className="space-y-0.5">
            <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider">Score de Esforço</span>
            <p className="text-xl font-black text-white">{totalScoreEsforco.toFixed(1)} <span className="text-xs font-normal text-slate-400">pts</span></p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400">
            <TrendingUp className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* ── BARRA DE FERRAMENTAS: TABS, BUSCA, FILTROS E MODO DE VISUALIZAÇÃO ── */}
      <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 space-y-3.5 shadow-lg">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Tabs Principais com Badges */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0">
            <button
              onClick={() => { setActiveTab('pendente'); setSelectedIds([]); }}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                activeTab === 'pendente'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-xs'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              <span>Pendentes</span>
              {kpiPendentes > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 text-[10px] font-black">
                  {kpiPendentes}
                </span>
              )}
            </button>

            <button
              onClick={() => { setActiveTab('aprovado'); setSelectedIds([]); }}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                activeTab === 'aprovado'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-xs'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              <span>Aprovadas</span>
              <span className="text-[10px] opacity-70">({kpiAprovadas})</span>
            </button>

            <button
              onClick={() => { setActiveTab('ajustes'); setSelectedIds([]); }}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                activeTab === 'ajustes'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-xs'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              <span>Em Ajustes</span>
              {kpiAjustes > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-purple-500 text-white text-[10px] font-black">
                  {kpiAjustes}
                </span>
              )}
            </button>

            <button
              onClick={() => { setActiveTab('todas'); setSelectedIds([]); }}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
                activeTab === 'todas'
                  ? 'bg-slate-800 text-white border border-slate-700 shadow-xs'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Todas as Pautas ({demandas.length})
            </button>
          </div>

          {/* Alternador de Modo: Cards vs Tabela */}
          <div className="flex items-center gap-2 shrink-0 self-end lg:self-auto">
            <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800">
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                className={`p-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  viewMode === 'cards' ? 'bg-[#c5a059] text-slate-950 shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
                title="Visualização em Cards"
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Cards</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('tabela')}
                className={`p-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  viewMode === 'tabela' ? 'bg-[#c5a059] text-slate-950 shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
                title="Visualização em Tabela Tática"
              >
                <List className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Tabela</span>
              </button>
            </div>
          </div>
        </div>

        {/* Barra de Busca e Filtros Rápidos */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 pt-2 border-t border-slate-800/80">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Buscar por pauta (ex: BNDES, CNMP), solicitante, local ou autoridade..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff]"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {[
              { id: 'todos', label: '🌟 Todas' },
              { id: 'foto', label: '📸 Fotografia' },
              { id: 'vídeo', label: '🎥 Vídeo' },
              { id: 'drone', label: '🛸 Drone' },
              { id: 'design', label: '🎨 Design & Artes' },
              { id: 'impressos', label: '🖨️ Impressos' },
              { id: 'brindes', label: '🪙 Brindes' },
              { id: 'redação', label: '✍️ Redação' },
              { id: 'cerimonial', label: '🎤 Cerimonial' },
              { id: 'com_drive', label: '📁 Com Drive' },
              { id: 'sem_drive', label: '⚠️ Sem Drive' },
            ].map((srv) => (
              <button
                key={srv.id}
                type="button"
                onClick={() => setServiceFilter(srv.id)}
                className={`px-2.5 py-1.5 rounded-lg text-[11px] font-bold transition-all shrink-0 ${
                  serviceFilter === srv.id
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-xs'
                    : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {srv.label}
              </button>
            ))}
          </div>

          {activeTab === 'pendente' && filteredDemandas.length > 0 && (
            <button
              type="button"
              onClick={toggleSelectAll}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 shrink-0"
            >
              {selectedIds.length === filteredDemandas.length ? (
                <CheckSquare className="w-3.5 h-3.5 text-[#00e5ff]" />
              ) : (
                <Square className="w-3.5 h-3.5" />
              )}
              <span>Selecionar Tudo</span>
            </button>
          )}
        </div>
      </div>

      {/* ── MODO 1: VISUALIZAÇÃO EM CARDS COMPACTOS & ELEGANTES ── */}
      {viewMode === 'cards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {filteredDemandas.length > 0 ? (
            filteredDemandas.map((demanda) => {
              const driveUrl = extractDriveUrl(demanda);
              const autLimpa = cleanAutoridades(demanda.autoridades);
              const coberturas = parseCobertura(demanda.tipo_cobertura);
              const isSelected = selectedIds.includes(demanda.id);

              return (
                <div
                  key={demanda.id}
                  className={`p-4 rounded-2xl bg-[#0b1222] border transition-all space-y-3 shadow-md flex flex-col justify-between ${
                    isSelected
                      ? 'border-[#00e5ff] bg-cyan-950/20'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-2.5">
                    {/* Topo do Card: Seleção + Status + Data */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        {activeTab === 'pendente' && (
                          <button
                            type="button"
                            onClick={() => toggleSelect(demanda.id)}
                            className="text-slate-400 hover:text-[#00e5ff]"
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-[#00e5ff]" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        )}
                        <span
                          className={`px-2 py-0.5 text-[10px] font-black rounded-md uppercase tracking-wider ${
                            demanda.status === 'aprovado'
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : demanda.status === 'pendente'
                              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse'
                              : demanda.status === 'ajustes'
                              ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                              : 'bg-red-500/15 text-red-400 border border-red-500/30'
                          }`}
                        >
                          {demanda.status}
                        </span>
                        <span className="text-xs font-bold text-slate-400">{demanda.setor}</span>
                        <span className="text-[11px] text-slate-500 font-semibold">• Score: {demanda.score_esforco || 1} pts</span>
                      </div>

                      {/* Badge de Data Inteligente */}
                      <div className="text-right shrink-0">
                        {demanda.data_fim && demanda.data_fim > demanda.data_evento ? (
                          <span className="px-2 py-0.5 rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-300 text-[11px] font-bold">
                            🗓️ {demanda.data_evento} até {demanda.data_fim}
                          </span>
                        ) : !demanda.data_evento || demanda.data_evento === 'SEM_DATA' ? (
                          <span className="px-2 py-0.5 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-bold">
                            ⏳ Sem Data Fixa
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-lg bg-blue-500/15 border border-blue-500/30 text-blue-300 text-[11px] font-bold">
                            📅 {demanda.data_evento} às {demanda.hora_evento || '09:00'}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Título do Evento */}
                    <h2 className="text-sm font-black text-white leading-snug line-clamp-2">
                      {demanda.titulo_evento}
                    </h2>

                    {/* Local e Solicitante */}
                    <div className="text-xs text-slate-400 space-y-1">
                      <p className="flex items-center gap-1.5 truncate">
                        <MapPin className="w-3.5 h-3.5 text-[#c5a059] shrink-0" />
                        <span className="text-slate-300 truncate">{demanda.local_evento || 'Gabinete CGCFN'}</span>
                      </p>
                      <p className="flex items-center gap-1.5 truncate">
                        <User className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <span>Solicitante: <strong className="text-slate-200">{demanda.solicitante_nome}</strong></span>
                      </p>
                    </div>

                    {/* Tags de Cobertura */}
                    {coberturas.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {coberturas.map((tipo, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-[10px] font-semibold text-slate-300"
                          >
                            {tipo}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Autoridades (se houver, limpo) */}
                    {autLimpa && (
                      <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800/80 text-[11px] text-slate-300 truncate">
                        <strong className="text-[#c5a059]">Autoridades:</strong> {autLimpa}
                      </div>
                    )}
                  </div>

                  {/* ── BOTÕES DE AÇÃO DO CARD ── */}
                  <div className="flex items-center justify-between gap-2 pt-3 border-t border-slate-800/80 mt-2">
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleOpenDetailModal(demanda, false)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-bold flex items-center gap-1 transition-all"
                        title="Ver Ficha Técnica"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Ficha</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate(`/comsoc_demandas?edit_id=${demanda.id}`)}
                        className="px-2.5 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-[#e5c07b] border border-amber-500/30 text-xs font-bold flex items-center gap-1 transition-all"
                        title="Editar no Formulário Completo de Demandas (comsoc_demandas)"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Editar</span>
                      </button>

                      {driveUrl ? (
                        <a
                          href={driveUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1.5 rounded-lg bg-blue-950/60 hover:bg-blue-900 text-blue-300 border border-blue-500/30 text-xs font-bold flex items-center gap-1 transition-all"
                          title="Abrir Pasta do Google Drive"
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                          <span>Drive</span>
                        </a>
                      ) : (
                        <button
                          type="button"
                          disabled={creatingDriveId === demanda.id}
                          onClick={(e) => handleCriarPastaDrive(demanda, e)}
                          className="px-2.5 py-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 text-xs font-bold flex items-center gap-1 transition-all disabled:opacity-50"
                          title="Criar Pasta Oficial no Google Drive com subpastas GERAL e SELEÇÃO"
                        >
                          <FolderPlus className="w-3.5 h-3.5" />
                          <span>{creatingDriveId === demanda.id ? 'Criando...' : '+ Drive'}</span>
                        </button>
                      )}
                    </div>

                    {/* Ações de Homologação */}
                    {demanda.status === 'pendente' ? (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() =>
                            setParecerModal({
                              isOpen: true,
                              demanda,
                              action: 'rejeitado',
                              motivo: '',
                            })
                          }
                          className="px-2.5 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-bold transition-all"
                        >
                          Rejeitar
                        </button>
                        <button
                          onClick={() =>
                            setParecerModal({
                              isOpen: true,
                              demanda,
                              action: 'ajustes',
                              motivo: '',
                            })
                          }
                          className="px-2.5 py-1.5 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs font-bold transition-all"
                        >
                          Ajustes
                        </button>
                        <button
                          onClick={() => handleApprove(demanda)}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-black shadow-md shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95 flex items-center gap-1"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Aprovar</span>
                        </button>
                      </div>
                    ) : ['aprovado', 'em_andamento'].includes(demanda.status || '') ? (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleConclude(demanda)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 text-xs font-bold flex items-center gap-1 transition-all shadow-sm"
                          title="Marcar Missão como Concluída"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Concluir</span>
                        </button>
                        <button
                          onClick={() => handleReopen(demanda, 'pendente')}
                          className="px-2 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-300 border border-slate-800 text-xs font-bold flex items-center gap-1 transition-all"
                          title="Reabrir Pauta para Avaliação"
                        >
                          <RotateCcw className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleReopen(demanda, 'pendente')}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-300 border border-slate-800 text-xs font-bold flex items-center gap-1 transition-all"
                        title="Reabrir Pauta para Avaliação"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Reabrir</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="col-span-full py-12 text-center rounded-2xl bg-[#0b1222] border border-slate-800 text-slate-500 text-xs">
              Nenhuma demanda encontrada para os filtros selecionados.
            </div>
          )}
        </div>
      )}

      {/* ── MODO 2: VISUALIZAÇÃO EM TABELA TÁTICA COMPACTA ── */}
      {viewMode === 'tabela' && (
        <div className="rounded-2xl bg-[#0b1222] border border-slate-800 overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-[11px] text-slate-400 uppercase font-black border-b border-slate-800 tracking-wider">
                <tr>
                  {activeTab === 'pendente' && <th className="p-3.5 w-10"></th>}
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Pauta / Evento</th>
                  <th className="p-3.5">Data / Hora</th>
                  <th className="p-3.5">Local</th>
                  <th className="p-3.5">Solicitante</th>
                  <th className="p-3.5">Cobertura</th>
                  <th className="p-3.5 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredDemandas.length > 0 ? (
                  filteredDemandas.map((demanda) => {
                    const driveUrl = extractDriveUrl(demanda);
                    const coberturas = parseCobertura(demanda.tipo_cobertura);
                    const isSelected = selectedIds.includes(demanda.id);

                    return (
                      <tr
                        key={demanda.id}
                        className={`hover:bg-slate-800/40 transition-colors ${
                          isSelected ? 'bg-cyan-950/20' : ''
                        }`}
                      >
                        {activeTab === 'pendente' && (
                          <td className="p-3.5">
                            <button
                              type="button"
                              onClick={() => toggleSelect(demanda.id)}
                              className="text-slate-400 hover:text-[#00e5ff]"
                            >
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-[#00e5ff]" />
                              ) : (
                                <Square className="w-4 h-4" />
                              )}
                            </button>
                          </td>
                        )}

                        <td className="p-3.5 whitespace-nowrap">
                          <span
                            className={`px-2 py-0.5 text-[10px] font-black rounded-md uppercase tracking-wider ${
                              demanda.status === 'aprovado'
                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                                : demanda.status === 'pendente'
                                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                : demanda.status === 'ajustes'
                                ? 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                                : 'bg-red-500/15 text-red-400 border border-red-500/30'
                            }`}
                          >
                            {demanda.status}
                          </span>
                        </td>

                        <td className="p-3.5 font-bold text-white max-w-xs truncate">
                          {demanda.titulo_evento}
                        </td>

                        <td className="p-3.5 whitespace-nowrap">
                          {demanda.data_fim && demanda.data_fim > demanda.data_evento ? (
                            <span className="text-purple-300 font-bold">
                              🗓️ {demanda.data_evento} até {demanda.data_fim}
                            </span>
                          ) : !demanda.data_evento || demanda.data_evento === 'SEM_DATA' ? (
                            <span className="text-amber-400 font-bold">⏳ A Definir</span>
                          ) : (
                            <span className="text-blue-300 font-bold">
                              {demanda.data_evento} às {demanda.hora_evento || '09:00'}
                            </span>
                          )}
                        </td>

                        <td className="p-3.5 text-slate-300 max-w-[160px] truncate">
                          {demanda.local_evento || 'Gabinete CGCFN'}
                        </td>

                        <td className="p-3.5 whitespace-nowrap text-slate-300">
                          {demanda.solicitante_nome} <span className="text-slate-500 text-[10px]">({demanda.setor})</span>
                        </td>

                        <td className="p-3.5">
                          <div className="flex gap-1 flex-wrap max-w-[140px]">
                            {coberturas.slice(0, 2).map((c, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-slate-900 text-[10px] text-slate-300">
                                {c}
                              </span>
                            ))}
                            {coberturas.length > 2 && (
                              <span className="text-[10px] text-slate-500 font-bold">+{coberturas.length - 2}</span>
                            )}
                          </div>
                        </td>

                        <td className="p-3.5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleOpenDetailModal(demanda, false)}
                              className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 hover:text-white"
                              title="Ver Ficha Técnica"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>

                            <button
                              type="button"
                              onClick={() => navigate(`/comsoc_demandas?edit_id=${demanda.id}`)}
                              className="p-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-[#e5c07b] border border-amber-500/30"
                              title="Editar no Formulário Completo de Demandas (comsoc_demandas)"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>

                            {driveUrl ? (
                              <a
                                href={driveUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1.5 rounded-lg bg-blue-950/60 hover:bg-blue-900 text-blue-300 border border-blue-500/30"
                                title="Abrir Google Drive"
                              >
                                <FolderOpen className="w-3.5 h-3.5" />
                              </a>
                            ) : (
                              <button
                                type="button"
                                disabled={creatingDriveId === demanda.id}
                                onClick={(e) => handleCriarPastaDrive(demanda, e)}
                                className="p-1.5 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 disabled:opacity-50"
                                title="Criar Pasta no Google Drive"
                              >
                                <FolderPlus className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {demanda.status === 'pendente' ? (
                              <>
                                <button
                                  onClick={() =>
                                    setParecerModal({
                                      isOpen: true,
                                      demanda,
                                      action: 'ajustes',
                                      motivo: '',
                                    })
                                  }
                                  className="px-2 py-1 rounded-lg bg-purple-500/15 text-purple-300 border border-purple-500/30 text-xs font-bold hover:bg-purple-500/25"
                                >
                                  Ajustes
                                </button>
                                <button
                                  onClick={() => handleApprove(demanda)}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-500 text-slate-950 text-xs font-black hover:bg-emerald-400 shadow-sm"
                                >
                                  Aprovar
                                </button>
                              </>
                            ) : ['aprovado', 'em_andamento'].includes(demanda.status || '') ? (
                              <>
                                <button
                                  onClick={() => handleConclude(demanda)}
                                  className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-bold hover:bg-emerald-500/30"
                                  title="Concluir Demanda"
                                >
                                  Concluir
                                </button>
                                <button
                                  onClick={() => handleReopen(demanda, 'pendente')}
                                  className="px-2 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-300 border border-slate-800 text-xs font-bold"
                                >
                                  Reabrir
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleReopen(demanda, 'pendente')}
                                className="px-2 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-300 border border-slate-800 text-xs font-bold"
                              >
                                Reabrir
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-slate-500 text-xs">
                      Nenhuma demanda encontrada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── MODAL: FICHA COMPLETA DA DEMANDA & EDIÇÃO ── */}
      {detailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-xs animate-in fade-in overflow-y-auto">
          <div className="w-full max-w-xl p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/50 space-y-4 shadow-2xl my-8">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-black uppercase tracking-wider border border-blue-500/40">
                    Ficha Técnica da Pauta #{detailModal.id}
                  </span>
                  {isEditingFicha && (
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-[#e5c07b] text-[10px] font-black uppercase tracking-wider border border-amber-500/40 flex items-center gap-1">
                      <Edit3 className="w-3 h-3" />
                      <span>Modo Edição</span>
                    </span>
                  )}
                </div>
                {!isEditingFicha && (
                  <h3 className="text-lg font-black text-white mt-1">
                    {detailModal.titulo_evento}
                  </h3>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setIsEditingFicha(!isEditingFicha)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                    isEditingFicha
                      ? 'bg-slate-800 text-slate-300 hover:text-white'
                      : 'bg-amber-500/20 border border-amber-500/40 text-[#e5c07b] hover:bg-amber-500/30'
                  }`}
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isEditingFicha ? 'Visualizar' : 'Editar Ficha'}</span>
                </button>

                <button
                  onClick={() => {
                    setDetailModal(null);
                    setIsEditingFicha(false);
                  }}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* MODO DE EDIÇÃO ATIVO */}
            {isEditingFicha ? (
              <div className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Título do Evento / Pauta *</label>
                  <input
                    type="text"
                    required
                    value={editForm.titulo_evento || ''}
                    onChange={(e) => setEditForm({ ...editForm, titulo_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white font-bold focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Data do Evento</label>
                    <input
                      type="date"
                      value={editForm.data_evento || ''}
                      onChange={(e) => setEditForm({ ...editForm, data_evento: e.target.value })}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Horário Previsto</label>
                    <input
                      type="time"
                      value={editForm.hora_evento || '09:00'}
                      onChange={(e) => setEditForm({ ...editForm, hora_evento: e.target.value })}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Local do Evento</label>
                    <input
                      type="text"
                      value={editForm.local_evento || ''}
                      onChange={(e) => setEditForm({ ...editForm, local_evento: e.target.value })}
                      placeholder="Ex: Salão Nobre, CIASC..."
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Score de Esforço (Pontos)</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={editForm.score_esforco || 1}
                      onChange={(e) => setEditForm({ ...editForm, score_esforco: parseInt(e.target.value, 10) || 1 })}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Solicitante</label>
                    <input
                      type="text"
                      value={editForm.solicitante_nome || ''}
                      onChange={(e) => setEditForm({ ...editForm, solicitante_nome: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Setor</label>
                    <input
                      type="text"
                      value={editForm.setor || ''}
                      onChange={(e) => setEditForm({ ...editForm, setor: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Contato / Ramal</label>
                    <input
                      type="text"
                      value={editForm.contato || ''}
                      onChange={(e) => setEditForm({ ...editForm, contato: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Categoria da Demanda</label>
                    <select
                      value={editForm.categoria_demanda || 'audiovisual'}
                      onChange={(e) => setEditForm({ ...editForm, categoria_demanda: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    >
                      <option value="audiovisual">📸 Audiovisual & Cobertura</option>
                      <option value="design">🎨 Design & Criação Gráfica</option>
                      <option value="impressos">🖨️ Gráfica & Impressos Físicos</option>
                      <option value="brindes">🪙 Brindes & Relações Públicas</option>
                      <option value="redacao">✍️ Redação & Discursos</option>
                      <option value="cerimonial">🎤 Cerimonial & Suporte</option>
                      <option value="outra_tarefa">⚡ Outra Tarefa Especial</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-bold mb-1">Produto / Peça Específica</label>
                    <input
                      type="text"
                      value={editForm.produto_especifico || ''}
                      onChange={(e) => setEditForm({ ...editForm, produto_especifico: e.target.value })}
                      placeholder="Ex: Banner 2x1m, Cardápio A4, Moeda..."
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                    >
                    </input>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 font-bold mb-1">Serviços Solicitados (Ex: foto, video, drone)</label>
                  <input
                    type="text"
                    value={Array.isArray(editForm.tipo_cobertura) ? editForm.tipo_cobertura.join(', ') : ((editForm.tipo_cobertura as any) || '')}
                    onChange={(e) => setEditForm({ ...editForm, tipo_cobertura: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
                    placeholder="Ex: foto, video, drone"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                {/* Campo Google Drive com Criação Automática */}
                <div className="space-y-1.5 p-3 rounded-2xl bg-blue-950/20 border border-blue-500/30">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-bold text-blue-300">
                      Pasta Oficial no Google Drive
                    </label>
                    <button
                      type="button"
                      disabled={creatingDriveId === detailModal.id}
                      onClick={() => handleCriarPastaDrive(detailModal)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-[10px] font-black transition-all disabled:opacity-50"
                    >
                      <FolderPlus className="w-3.5 h-3.5" />
                      <span>{creatingDriveId === detailModal.id ? 'Criando no Drive...' : '⚡ Criar Pasta Oficial no Drive'}</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    value={editForm.drive_url || ''}
                    onChange={(e) => setEditForm({ ...editForm, drive_url: e.target.value })}
                    placeholder="https://drive.google.com/drive/folders/..."
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-bold mb-1">Autoridades & VIPs</label>
                  <textarea
                    rows={2}
                    value={editForm.autoridades || ''}
                    onChange={(e) => setEditForm({ ...editForm, autoridades: e.target.value })}
                    placeholder="Lista de autoridades presentes..."
                    className="w-full p-3 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-bold mb-1">Observações / Parecer</label>
                  <textarea
                    rows={2}
                    value={editForm.observacoes || ''}
                    onChange={(e) => setEditForm({ ...editForm, observacoes: e.target.value })}
                    placeholder="Orientações e detalhes operacionais..."
                    className="w-full p-3 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setIsEditingFicha(false)}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700"
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    disabled={savingEdit}
                    onClick={handleSaveEditFicha}
                    className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black flex items-center gap-1.5 shadow-lg shadow-[#c5a059]/25 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    <span>{savingEdit ? 'Gravando...' : 'Salvar Alterações da Ficha'}</span>
                  </button>
                </div>
              </div>
            ) : (
              /* MODO DE VISUALIZAÇÃO PADRÃO */
              <>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Data & Horário</span>
                    <p className="font-bold text-white">
                      {detailModal.data_fim && detailModal.data_fim > detailModal.data_evento
                        ? `${detailModal.data_evento} até ${detailModal.data_fim}`
                        : detailModal.data_evento || 'Sem data fixa'}
                    </p>
                    <p className="text-slate-400">Às {detailModal.hora_evento || '09:00'}</p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Local do Evento</span>
                    <p className="font-bold text-white truncate">{detailModal.local_evento || 'Gabinete CGCFN'}</p>
                    <p className="text-slate-400">Score: {detailModal.score_esforco || 1} pts</p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Solicitante</span>
                    <p className="font-bold text-white">{detailModal.solicitante_nome}</p>
                    <p className="text-slate-400">{detailModal.setor} • {detailModal.contato}</p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-bold">Serviços Solicitados</span>
                    <div className="flex flex-wrap gap-1 pt-0.5">
                      {parseCobertura(detailModal.tipo_cobertura).map((c, i) => (
                        <span key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-bold">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {cleanAutoridades(detailModal.autoridades) && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 space-y-1">
                    <strong className="text-[#c5a059] block text-[11px] uppercase">Autoridades & VIPs:</strong>
                    <p>{cleanAutoridades(detailModal.autoridades)}</p>
                  </div>
                )}

                {detailModal.observacoes && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 space-y-1">
                    <strong className="text-slate-400 block text-[11px] uppercase">Observações / Parecer Técnico:</strong>
                    <p>{detailModal.observacoes}</p>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => {
                        setDetailModal(null);
                        navigate(`/comsoc_demandas?edit_id=${detailModal.id}`);
                      }}
                      className="px-3.5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5 transition-all shadow-md shadow-[#c5a059]/20 hover:scale-105"
                      title="Abrir no Formulário Completo de Demandas"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>🚀 Editar no Formulário Completo</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsEditingFicha(true)}
                      className="px-3.5 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-[#e5c07b] border border-amber-500/40 text-xs font-bold flex items-center gap-1.5 transition-all hover:scale-105"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>✏️ Edição Rápida</span>
                    </button>

                    {extractDriveUrl(detailModal) && (
                      <a
                        href={extractDriveUrl(detailModal)!}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3.5 py-2 rounded-xl bg-blue-950/80 hover:bg-blue-900 text-blue-300 border border-blue-500/30 text-xs font-bold flex items-center gap-1.5"
                      >
                        <FolderOpen className="w-4 h-4" />
                        <span>Abrir Google Drive</span>
                      </a>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setDetailModal(null)}
                      className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold hover:bg-slate-700"
                    >
                      Fechar
                    </button>

                    {detailModal.status === 'pendente' && (
                      <button
                        onClick={() => {
                          handleApprove(detailModal);
                          setDetailModal(null);
                        }}
                        className="px-4 py-2 rounded-xl bg-emerald-500 text-slate-950 text-xs font-black hover:bg-emerald-400 shadow-md"
                      >
                        Aprovar Pauta
                      </button>
                    )}

                    {['aprovado', 'em_andamento'].includes(detailModal.status || '') && (
                      <button
                        onClick={() => {
                          handleConclude(detailModal);
                          setDetailModal(null);
                        }}
                        className="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/50 text-xs font-bold flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>Concluir Missão</span>
                      </button>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL: PARECER TÉCNICO / AJUSTES ── */}
      {parecerModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-md p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <h3 className="text-sm font-black text-white">
              {parecerModal.action === 'ajustes' ? 'Solicitar Ajustes na Pauta' : 'Rejeitar Solicitação'}
            </h3>
            <p className="text-xs text-slate-400">
              Pauta: <strong className="text-white">{parecerModal.demanda?.titulo_evento}</strong>
            </p>

            <textarea
              rows={3}
              placeholder="Descreva o parecer técnico ou motivo do ajuste..."
              value={parecerModal.motivo}
              onChange={(e) =>
                setParecerModal({ ...parecerModal, motivo: e.target.value })
              }
              className="w-full p-3 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
            />

            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() =>
                  setParecerModal({ isOpen: false, demanda: null, action: 'ajustes', motivo: '' })
                }
                className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveParecer}
                className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 text-xs font-bold"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
