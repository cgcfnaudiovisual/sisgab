import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useMemo } from 'react';
import {
  Kanban as KanbanIcon,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertCircle,
  MoreVertical,
  User,
  Calendar,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Trash2,
  Paperclip,
  Image as ImageIcon,
  Film,
  FileText,
  Eye,
  MessageSquare,
  UploadCloud,
  ExternalLink,
  GripVertical,
  Maximize2,
  X,
  Play,
  RotateCcw,
  Palette,
  Printer,
  Gift,
  Shield,
  Layers,
  Send,
  Download,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type {
  TarefaCOMSOC,
  TarefaStatus,
  TarefaPrioridade,
  TarefaTipo,
  TarefaAnexoMidia,
  TarefaApontamento,
  MilitarEfetivo,
} from '../../types/database';
import { useAuth } from '../../context/AuthContext';

const COLUNAS: { id: TarefaStatus; title: string; color: string; bg: string; border: string; badge: string }[] = [
  {
    id: 'a_fazer',
    title: 'A Fazer (Fila / Backlog)',
    color: 'text-slate-300',
    bg: 'bg-slate-900/40',
    border: 'border-slate-800',
    badge: 'bg-slate-800 text-slate-300',
  },
  {
    id: 'em_andamento',
    title: 'Em Andamento',
    color: 'text-[#00e5ff]',
    bg: 'bg-[#00e5ff]/5',
    border: 'border-[#00e5ff]/30',
    badge: 'bg-[#00e5ff]/20 text-[#00e5ff]',
  },
  {
    id: 'revisao',
    title: 'Revisão / Homologação',
    color: 'text-amber-400',
    bg: 'bg-amber-500/5',
    border: 'border-amber-500/30',
    badge: 'bg-amber-500/20 text-amber-300',
  },
  {
    id: 'concluido',
    title: 'Concluído / Entregue',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/5',
    border: 'border-emerald-500/30',
    badge: 'bg-emerald-500/20 text-emerald-300',
  },
];

const PRIORIDADES: Record<TarefaPrioridade, { label: string; badge: string }> = {
  alta: { label: '🔥 Urgente / Alta', badge: 'bg-red-500/15 text-red-400 border-red-500/40' },
  media: { label: '🟡 Média', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/40' },
  baixa: { label: '🔵 Normal', badge: 'bg-blue-500/15 text-blue-400 border-blue-500/40' },
};

const TIPOS_TAREFA: Record<TarefaTipo, { label: string; icon: string; color: string }> = {
  producao_arte: { label: 'Design / Arte', icon: '🎨', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' },
  video_reels: { label: 'Vídeo / Reels', icon: '🎬', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' },
  faxina_rotina: { label: 'Faxina / Rotina', icon: '🧹', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' },
  manutencao_apoio: { label: 'Manutenção / Apoio', icon: '🛠️', color: 'text-orange-400 bg-orange-500/10 border-orange-500/30' },
  impressao: { label: 'Impressão & Banner', icon: '🖨️', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' },
  redacao: { label: 'Redação / Matéria', icon: '✍️', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' },
  brindes: { label: 'Kit Brindes / RP', icon: '🪙', color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30' },
  evento_cobertura: { label: 'Cobertura Externa', icon: '📸', color: 'text-pink-400 bg-pink-500/10 border-pink-500/30' },
  outro: { label: 'Geral', icon: '⚡', color: 'text-slate-400 bg-slate-800 border-slate-700' },
};

const MOCK_TAREFAS_INICIAIS: TarefaCOMSOC[] = [
  {
    id: 1,
    titulo: 'Edição do Vídeo Teaser da Banda Sinfônica (60s)',
    descricao: 'Cortar os melhores momentos da apresentação no Theatro Municipal para o Instagram.',
    responsavel: '3ºSG-FN-IF Souza',
    solicitante_nome: 'Cap (FN) Bruno Tiago',
    solicitante_posto: 'Cap (FN)',
    tipo_tarefa: 'video_reels',
    prioridade: 'alta',
    status: 'em_andamento',
    ordem_prioridade: 1,
    prazo: '2026-08-22',
    anexos_midia: [
      {
        id: 'att_1',
        nome: 'Briefing_Banda_Municipal.pdf',
        url: 'https://drive.google.com',
        tipo: 'referencia',
        enviado_por: 'Cap (FN) Bruno Tiago',
        enviado_em: new Date().toISOString(),
        formato: 'documento',
      },
    ],
    apontamentos_ajuste: [
      {
        id: 'apt_1',
        autor: 'Cap (FN) Bruno Tiago',
        texto: 'Atenção para dar destaque ao solo do Mestre de Banda na minutagem 00:30.',
        criado_em: new Date().toISOString(),
        resolvido: false,
      },
    ],
    criado_em: new Date().toISOString(),
  },
  {
    id: 2,
    titulo: 'Diagramação do Informativo Mensal do CGCFN',
    descricao: 'Montar layout das páginas 4 e 5 no Estúdio Gráfico e validar com CheGab.',
    responsavel: '2ºSG-FN-CN Rodrigo',
    solicitante_nome: 'CC (FN) Caldas',
    solicitante_posto: 'CC (FN)',
    tipo_tarefa: 'producao_arte',
    prioridade: 'media',
    status: 'a_fazer',
    ordem_prioridade: 2,
    prazo: '2026-08-25',
    criado_em: new Date().toISOString(),
  },
  {
    id: 3,
    titulo: 'Manutenção e Cautela das Lentes 70-200mm e Drones',
    descricao: 'Limpeza de sensores, calibração de hélices e checklist de baterias.',
    responsavel: '2ºSG-FN Calaça',
    solicitante_nome: '2ºSG-FN Calaça (Encarregado)',
    solicitante_posto: '2ºSG',
    tipo_tarefa: 'manutencao_apoio',
    prioridade: 'alta',
    status: 'em_andamento',
    ordem_prioridade: 3,
    prazo: '2026-08-22',
    criado_em: new Date().toISOString(),
  },
  {
    id: 4,
    titulo: 'Curadoria de Fotos da Visita da Delegação Estrangeira',
    descricao: 'Selecionar as 30 melhores fotos no acervo e marcar autoridades para homologação.',
    responsavel: '1ºSG-FN-IF Barbosa',
    solicitante_nome: 'CF (FN) Alexandre',
    solicitante_posto: 'CF (FN)',
    tipo_tarefa: 'evento_cobertura',
    prioridade: 'alta',
    status: 'revisao',
    ordem_prioridade: 4,
    prazo: '2026-08-21',
    criado_em: new Date().toISOString(),
  },
  {
    id: 5,
    titulo: 'Criação de Artes para o Telão SisGAB TV (Aniversariantes)',
    descricao: 'Atualizar os cartazes dos aniversariantes da semana de agosto.',
    responsavel: '1ºTen (T) Mariana',
    solicitante_nome: 'Gabinete CGCFN',
    solicitante_posto: 'GAB',
    tipo_tarefa: 'producao_arte',
    prioridade: 'baixa',
    status: 'concluido',
    ordem_prioridade: 5,
    prazo: '2026-08-17',
    criado_em: new Date().toISOString(),
  },
];

export const KanbanTasks: React.FC = () => {
  const { user } = useAuth();
  const [tarefas, setTarefas] = useState<TarefaCOMSOC[]>(MOCK_TAREFAS_INICIAIS);
  const [efetivoList, setEfetivoList] = useState<MilitarEfetivo[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResp, setSelectedResp] = useState<string>('todos');
  const [selectedType, setSelectedType] = useState<string>('todos');
  
  // Drag & Drop State
  const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<TarefaStatus | null>(null);

  // Modais
  const [modalOpen, setModalOpen] = useState(false);
  const [mediaModalTask, setMediaModalTask] = useState<TarefaCOMSOC | null>(null);
  const [mediaTab, setMediaTab] = useState<'referencias' | 'previas' | 'apontamentos'>('previas');
  
  // Visualizador HD / Player
  const [previewMedia, setPreviewMedia] = useState<TarefaAnexoMidia | null>(null);
  const [novoApontamento, setNovoApontamento] = useState('');
  const [novaMidiaUrl, setNovaMidiaUrl] = useState('');
  const [novaMidiaNome, setNovaMidiaNome] = useState('');
  const [novaMidiaTipo, setNovaMidiaTipo] = useState<'referencia' | 'previa_producao'>('previa_producao');

  // Form de Nova Tarefa
  const [newTarefa, setNewTarefa] = useState<{
    titulo: string;
    descricao: string;
    responsavel: string;
    solicitante_nome: string;
    solicitante_posto: string;
    tipo_tarefa: TarefaTipo;
    prioridade: TarefaPrioridade;
    status: TarefaStatus;
    prazo: string;
    link_midia_inicial?: string;
  }>({
    titulo: '',
    descricao: '',
    responsavel: user?.nome_guerra ? user.nome_guerra : '2ºSG-FN Calaça',
    solicitante_nome: 'Cap (FN) Bruno Tiago',
    solicitante_posto: 'Cap (FN)',
    tipo_tarefa: 'producao_arte',
    prioridade: 'media',
    status: 'a_fazer',
    prazo: '',
    link_midia_inicial: '',
  });

  useEffect(() => {
    loadTarefas();
    loadEfetivo();

    const channel = supabase
      .channel('kanban-tasks-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tarefas_pendentes' },
        () => {
          loadTarefas();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const loadEfetivo = async () => {
    try {
      const { data, error } = await supabase
        .from('efetivo')
        .select('*')
        .order('antiguidade_num', { ascending: true });
      if (!error && data) {
        setEfetivoList(data as MilitarEfetivo[]);
      }
    } catch {
      // Silencioso
    }
  };

  const loadTarefas = async () => {
    try {
      const { data, error } = await supabase
        .from('tarefas_pendentes')
        .select('*')
        .order('ordem_prioridade', { ascending: true, nullsFirst: false });

      if (!error && data && data.length > 0) {
        const mapped: TarefaCOMSOC[] = data.map((d: any, index: number) => ({
          id: d.id,
          titulo: d.titulo,
          descricao: d.descricao,
          responsavel: d.responsavel,
          solicitante_nome: d.solicitante_nome || d.solicitante || 'Oficial Solicitante',
          solicitante_posto: d.solicitante_posto || 'Oficial',
          tipo_tarefa: (d.tipo_tarefa as TarefaTipo) || 'producao_arte',
          prioridade: (d.prioridade as TarefaPrioridade) || 'media',
          status: (d.status as TarefaStatus) || 'a_fazer',
          ordem_prioridade: d.ordem_prioridade || index + 1,
          prazo: d.prazo,
          anexos_midia: typeof d.anexos_midia === 'string' ? JSON.parse(d.anexos_midia) : (d.anexos_midia || []),
          apontamentos_ajuste: typeof d.apontamentos_ajuste === 'string' ? JSON.parse(d.apontamentos_ajuste) : (d.apontamentos_ajuste || []),
          criado_em: d.criado_em,
        }));
        setTarefas(mapped);
      }
    } catch {
      // Fallback para os mocks
    }
  };

  // ── DRAG & DROP HANDLERS ──
  const handleDragStart = (e: React.DragEvent, taskId: number) => {
    e.dataTransfer.setData('text/plain', String(taskId));
    setDraggedTaskId(taskId);
  };

  const handleDragOver = (e: React.DragEvent, colId: TarefaStatus) => {
    e.preventDefault();
    if (dragOverColumn !== colId) {
      setDragOverColumn(colId);
    }
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: TarefaStatus, targetTaskId?: number) => {
    e.preventDefault();
    setDragOverColumn(null);
    const taskIdStr = e.dataTransfer.getData('text/plain');
    const taskId = Number(taskIdStr);
    if (!taskId) return;

    const taskToMove = tarefas.find((t) => t.id === taskId);
    if (!taskToMove) return;

    militaryAudio.playTacticalBeep();

    // 1. Atualização Otimista
    setTarefas((prev) => {
      const remaining = prev.filter((t) => t.id !== taskId);
      const updatedTask: TarefaCOMSOC = { ...taskToMove, status: targetStatus };

      if (targetTaskId && targetTaskId !== taskId) {
        const targetIndex = remaining.findIndex((t) => t.id === targetTaskId);
        if (targetIndex !== -1) {
          remaining.splice(targetIndex, 0, updatedTask);
          return remaining.map((t, idx) => ({ ...t, ordem_prioridade: idx + 1 }));
        }
      }

      const colTasks = remaining.filter((t) => t.status === targetStatus);
      const otherTasks = remaining.filter((t) => t.status !== targetStatus);
      const newColList = [updatedTask, ...colTasks];

      return [...otherTasks, ...newColList].map((t, idx) => ({ ...t, ordem_prioridade: idx + 1 }));
    });

    if (targetStatus === 'concluido') {
      toast.success('🎯 Missão marcada como Concluída!');
    } else {
      toast.info(`Tarefa movida para "${COLUNAS.find((c) => c.id === targetStatus)?.title}".`);
    }

    // 2. Persistência no Banco
    try {
      await supabase
        .from('tarefas_pendentes')
        .update({
          status: targetStatus,
          atualizado_em: new Date().toISOString(),
        })
        .eq('id', taskId);
    } catch (err) {
      console.warn('Erro ao persistir drag & drop:', err);
    }
  };

  const moveTaskStep = async (taskId: number, direction: 'next' | 'prev') => {
    const statusOrder: TarefaStatus[] = ['a_fazer', 'em_andamento', 'revisao', 'concluido'];
    const currentTask = tarefas.find((t) => t.id === taskId);
    if (!currentTask) return;

    const currentIdx = statusOrder.indexOf(currentTask.status);
    const newIdx = direction === 'next' ? currentIdx + 1 : currentIdx - 1;
    if (newIdx < 0 || newIdx >= statusOrder.length) return;

    const newStatus = statusOrder[newIdx];
    militaryAudio.playTacticalBeep();

    setTarefas((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
    );

    if (newStatus === 'concluido') {
      toast.success('🎯 Missão marcada como Concluída!');
    }

    try {
      await supabase
        .from('tarefas_pendentes')
        .update({ status: newStatus, atualizado_em: new Date().toISOString() })
        .eq('id', taskId);
    } catch (e) {
      console.warn('Erro ao atualizar status:', e);
    }
  };

  // ── CRIAÇÃO DE NOVA TAREFA ──
  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTarefa.titulo.trim()) {
      toast.error('Informe o título da tarefa.');
      return;
    }

    const tempId = Date.now();
    const initialAnexos: TarefaAnexoMidia[] = [];
    if (newTarefa.link_midia_inicial?.trim()) {
      initialAnexos.push({
        id: `att_${Date.now()}`,
        nome: 'Anexo Inicial de Referência',
        url: newTarefa.link_midia_inicial.trim(),
        tipo: 'referencia',
        enviado_por: newTarefa.solicitante_nome,
        enviado_em: new Date().toISOString(),
        formato: newTarefa.link_midia_inicial.match(/\.(jpg|jpeg|png|webp)/i)
          ? 'imagem'
          : newTarefa.link_midia_inicial.match(/\.(mp4|mov)/i)
          ? 'video'
          : 'outro',
      });
    }

    const created: TarefaCOMSOC = {
      id: tempId,
      titulo: newTarefa.titulo,
      descricao: newTarefa.descricao,
      responsavel: newTarefa.responsavel,
      solicitante_nome: newTarefa.solicitante_nome,
      solicitante_posto: newTarefa.solicitante_posto,
      tipo_tarefa: newTarefa.tipo_tarefa,
      prioridade: newTarefa.prioridade,
      status: newTarefa.status,
      ordem_prioridade: 1,
      prazo: newTarefa.prazo || null,
      anexos_midia: initialAnexos,
      apontamentos_ajuste: [],
      criado_em: new Date().toISOString(),
    };

    setTarefas([created, ...tarefas]);
    setModalOpen(false);
    militaryAudio.playTacticalBeep();
    toast.success('🎉 Tarefa cadastrada com sucesso na esteira!');

    try {
      const { data } = await supabase
        .from('tarefas_pendentes')
        .insert({
          titulo: newTarefa.titulo,
          descricao: newTarefa.descricao,
          responsavel: newTarefa.responsavel,
          solicitante_nome: newTarefa.solicitante_nome,
          solicitante_posto: newTarefa.solicitante_posto,
          tipo_tarefa: newTarefa.tipo_tarefa,
          prioridade: newTarefa.prioridade,
          status: newTarefa.status,
          prazo: newTarefa.prazo || null,
          anexos_midia: JSON.stringify(initialAnexos),
          apontamentos_ajuste: JSON.stringify([]),
        })
        .select();

      if (data && data[0]) {
        setTarefas((prev) =>
          prev.map((t) => (t.id === tempId ? { ...t, id: data[0].id } : t))
        );
      }
    } catch (e) {
      console.warn('Erro ao salvar tarefa no Supabase:', e);
    }
  };

  // ── ANEXO DE MÍDIAS & APONTAMENTOS NO MODAL ──
  const handleAdicionarMidia = async () => {
    if (!mediaModalTask || !novaMidiaUrl.trim()) {
      toast.error('Insira o link da mídia ou arquivo.');
      return;
    }

    const isVideo = novaMidiaUrl.match(/\.(mp4|mov|webm)/i) || novaMidiaUrl.includes('drive.google.com/file');
    const isImage = novaMidiaUrl.match(/\.(jpg|jpeg|png|webp|gif)/i);

    const novoAnexo: TarefaAnexoMidia = {
      id: `att_${Date.now()}`,
      nome: novaMidiaNome.trim() || (novaMidiaTipo === 'referencia' ? 'Mídia de Referência' : 'Prévia Pronta para Avaliação'),
      url: novaMidiaUrl.trim(),
      tipo: novaMidiaTipo,
      enviado_por: user?.nome_guerra ? `${user.posto_grad || ''} ${user.nome_guerra}` : 'Militar ComSoc',
      enviado_em: new Date().toISOString(),
      formato: isImage ? 'imagem' : isVideo ? 'video' : 'outro',
      versao: (mediaModalTask.anexos_midia?.length || 0) + 1,
    };

    const updatedAnexos = [...(mediaModalTask.anexos_midia || []), novoAnexo];
    const updatedTask = { ...mediaModalTask, anexos_midia: updatedAnexos };

    setMediaModalTask(updatedTask);
    setTarefas((prev) => prev.map((t) => (t.id === mediaModalTask.id ? updatedTask : t)));
    setNovaMidiaUrl('');
    setNovaMidiaNome('');
    toast.success('Mídia anexada com sucesso!');

    try {
      await supabase
        .from('tarefas_pendentes')
        .update({ anexos_midia: JSON.stringify(updatedAnexos) })
        .eq('id', mediaModalTask.id);
    } catch (e) {
      console.warn('Erro ao salvar anexo no Supabase:', e);
    }
  };

  const handleAdicionarApontamento = async () => {
    if (!mediaModalTask || !novoApontamento.trim()) return;

    const novoApt: TarefaApontamento = {
      id: `apt_${Date.now()}`,
      autor: user?.nome_guerra ? `${user.posto_grad || ''} ${user.nome_guerra}` : 'Oficial / Avaliador',
      texto: novoApontamento.trim(),
      criado_em: new Date().toISOString(),
      resolvido: false,
    };

    const updatedApontamentos = [...(mediaModalTask.apontamentos_ajuste || []), novoApt];
    const updatedTask = { ...mediaModalTask, apontamentos_ajuste: updatedApontamentos };

    setMediaModalTask(updatedTask);
    setTarefas((prev) => prev.map((t) => (t.id === mediaModalTask.id ? updatedTask : t)));
    setNovoApontamento('');
    toast.info('Apontamento de ajuste registrado.');

    try {
      await supabase
        .from('tarefas_pendentes')
        .update({ apontamentos_ajuste: JSON.stringify(updatedApontamentos) })
        .eq('id', mediaModalTask.id);
    } catch (e) {
      console.warn('Erro ao salvar apontamento:', e);
    }
  };

  const handleAprovarMidiaCompleta = async (task: TarefaCOMSOC) => {
    const updatedTask: TarefaCOMSOC = { ...task, status: 'concluido' };
    setTarefas((prev) => prev.map((t) => (t.id === task.id ? updatedTask : t)));
    setMediaModalTask(null);
    militaryAudio.playTacticalBeep();
    toast.success('✅ Mídia e Pauta Homologadas com Sucesso para Publicação!');

    try {
      await supabase
        .from('tarefas_pendentes')
        .update({ status: 'concluido', atualizado_em: new Date().toISOString() })
        .eq('id', task.id);
    } catch (e) {
      console.warn('Erro ao homologar mídia:', e);
    }
  };

  // ── FILTROS ──
  const filteredTarefas = useMemo(() => {
    return tarefas.filter((t) => {
      const matchQuery =
        t.titulo.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (t.descricao && t.descricao.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (t.solicitante_nome && t.solicitante_nome.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchResp = selectedResp === 'todos' || t.responsavel === selectedResp;
      const matchType = selectedType === 'todos' || t.tipo_tarefa === selectedType;
      return matchQuery && matchResp && matchType;
    });
  }, [tarefas, searchQuery, selectedResp, selectedType]);

  const uniqueResponsaveis = useMemo(
    () => Array.from(new Set(tarefas.map((t) => t.responsavel).filter(Boolean))),
    [tarefas]
  );

  // KPIs Rápidos
  const kpiAFazer = tarefas.filter((t) => t.status === 'a_fazer').length;
  const kpiEmAndamento = tarefas.filter((t) => t.status === 'em_andamento').length;
  const kpiRevisao = tarefas.filter((t) => t.status === 'revisao').length;
  const kpiConcluido = tarefas.filter((t) => t.status === 'concluido').length;

  return (
    <div className="space-y-6">
      {/* ── HEADER DA SEÇÃO ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059]/20 text-[#e5c07b] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Governança & Produção Contínua
            </span>
            <span className="text-slate-400 text-xs">• Esteira Tática da Seção</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
            QUADRO DE DEMANDAS DIÁRIAS
          </h1>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Nova Demanda / Solicitação</span>
        </button>
      </div>

      {/* ── CARDS DE KPIS DA ESTEIRA ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex items-center justify-between shadow-md">
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Fila (Backlog)</span>
            <p className="text-xl font-black text-white">{kpiAFazer}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300">
            <Clock className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-[#00e5ff]/30 flex items-center justify-between shadow-md">
          <div>
            <span className="text-[10px] font-bold text-[#00e5ff] uppercase tracking-wider">Em Produção</span>
            <p className="text-xl font-black text-white">{kpiEmAndamento}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-[#00e5ff]/10 flex items-center justify-center text-[#00e5ff]">
            <Layers className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-amber-500/30 flex items-center justify-between shadow-md">
          <div>
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Homologação / Visto</span>
            <p className="text-xl font-black text-white">{kpiRevisao}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
            <Eye className="w-4 h-4" />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-emerald-500/30 flex items-center justify-between shadow-md">
          <div>
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Concluídas</span>
            <p className="text-xl font-black text-white">{kpiConcluido}</p>
          </div>
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* ── BARRA DE FILTROS RÁPIDOS ── */}
      <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-2.5 flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Buscar por tarefa, solicitante ou descrição..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
          <div className="flex items-center gap-1.5 shrink-0">
            <Filter className="w-3.5 h-3.5 text-[#c5a059]" />
            <span className="text-xs text-slate-400 font-semibold">Tipo:</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-slate-900 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none"
            >
              <option value="todos">Todos os Tipos</option>
              {Object.entries(TIPOS_TAREFA).map(([key, info]) => (
                <option key={key} value={key}>
                  {info.icon} {info.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 shrink-0 ml-2">
            <span className="text-xs text-slate-400 font-semibold">Executor:</span>
            <select
              value={selectedResp}
              onChange={(e) => setSelectedResp(e.target.value)}
              className="bg-slate-900 text-xs font-bold text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none"
            >
              <option value="todos">Toda a Seção</option>
              {uniqueResponsaveis.map((resp) => (
                <option key={resp} value={resp}>
                  {resp}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── GRID DAS 4 COLUNAS DO KANBAN (DRAG & DROP) ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {COLUNAS.map((coluna, colIdx) => {
          const colTasks = filteredTarefas
            .filter((t) => t.status === coluna.id)
            .sort((a, b) => (a.ordem_prioridade || 0) - (b.ordem_prioridade || 0));

          const isOver = dragOverColumn === coluna.id;

          return (
            <div
              key={coluna.id}
              onDragOver={(e) => handleDragOver(e, coluna.id)}
              onDrop={(e) => handleDrop(e, coluna.id)}
              className={`rounded-2xl border transition-all p-3.5 flex flex-col min-h-[550px] shadow-lg ${
                isOver
                  ? 'border-[#00e5ff] bg-[#00e5ff]/10 scale-[1.01]'
                  : `${coluna.border} ${coluna.bg}`
              }`}
            >
              {/* Topo da Coluna */}
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-black uppercase tracking-wider ${coluna.color}`}>
                    {coluna.title}
                  </span>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${coluna.badge}`}>
                  {colTasks.length}
                </span>
              </div>

              {/* Lista de Cards Reordenáveis */}
              <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                {colTasks.length > 0 ? (
                  colTasks.map((task) => {
                    const prio = PRIORIDADES[task.prioridade];
                    const tipoInfo = TIPOS_TAREFA[task.tipo_tarefa || 'outro'];
                    const numAnexos = task.anexos_midia?.length || 0;
                    const numApontamentos = task.apontamentos_ajuste?.length || 0;

                    return (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, task.id)}
                        onDrop={(e) => {
                          e.stopPropagation();
                          handleDrop(e, coluna.id, task.id);
                        }}
                        className="p-3.5 rounded-xl bg-[#0d1629] border border-slate-800/90 hover:border-[#c5a059]/50 transition-all space-y-2.5 shadow-md group cursor-grab active:cursor-grabbing hover:shadow-xl hover:shadow-black/40"
                      >
                        {/* Topo do Card: Tipo + Prioridade + Prazo */}
                        <div className="flex items-start justify-between gap-1.5 flex-wrap">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span
                              className={`px-1.5 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider border flex items-center gap-1 ${tipoInfo.color}`}
                            >
                              <span>{tipoInfo.icon}</span>
                              <span>{tipoInfo.label}</span>
                            </span>

                            <span
                              className={`px-1.5 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider border ${prio.badge}`}
                            >
                              {prio.label}
                            </span>
                          </div>

                          {task.prazo && (
                            <span className="text-[10px] text-slate-400 font-semibold flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-[#c5a059]" />
                              {task.prazo}
                            </span>
                          )}
                        </div>

                        {/* Título da Demanda */}
                        <h3 className="text-xs font-bold text-white group-hover:text-[#e5c07b] transition-colors leading-snug">
                          {task.titulo}
                        </h3>

                        {/* Descrição resumida */}
                        {task.descricao && (
                          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                            {task.descricao}
                          </p>
                        )}

                        {/* Identificação Dupla: Solicitante (Oficial) x Executor (Militar) */}
                        <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                          {/* Quem Solicitou */}
                          <div className="flex items-center justify-between text-[10px]">
                            <div className="flex items-center gap-1 text-slate-400 truncate">
                              <span className="text-amber-400/90 font-bold">Solicitante:</span>
                              <span className="text-slate-200 font-medium truncate">
                                {task.solicitante_posto ? `${task.solicitante_posto} ` : ''}
                                {task.solicitante_nome}
                              </span>
                            </div>
                          </div>

                          {/* Executor Designado */}
                          <div className="flex items-center justify-between text-[10.5px]">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[9px] font-bold text-[#00e5ff]">
                                <User className="w-2.5 h-2.5" />
                              </div>
                              <span className="text-slate-300 font-semibold truncate max-w-[120px]">
                                {task.responsavel}
                              </span>
                            </div>

                            {/* Botão de Abrir Mídias / Preview */}
                            <button
                              type="button"
                              onClick={() => {
                                setMediaModalTask(task);
                                setMediaTab(numAnexos > 0 ? 'previas' : 'referencias');
                              }}
                              className={`px-2 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 border transition-all ${
                                numAnexos > 0
                                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40 hover:bg-purple-500/30'
                                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
                              }`}
                              title="Gerenciar Mídias, Anexos e Aprovações"
                            >
                              <Paperclip className="w-3 h-3" />
                              <span>{numAnexos > 0 ? `${numAnexos} Mídias` : '+ Mídia'}</span>
                              {numApontamentos > 0 && (
                                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping ml-0.5" />
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Botões de Avanço Manual */}
                        <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-slate-500 text-[10px]">
                          <div className="flex items-center gap-1 text-[10px] text-slate-500">
                            <GripVertical className="w-3 h-3" />
                            <span>Arraste para priorizar</span>
                          </div>

                          <div className="flex items-center gap-1">
                            {colIdx > 0 && (
                              <button
                                type="button"
                                onClick={() => moveTaskStep(task.id, 'prev')}
                                className="p-1 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors border border-slate-800"
                                title="Voltar etapa"
                              >
                                <ArrowLeft className="w-3 h-3" />
                              </button>
                            )}

                            {colIdx < COLUNAS.length - 1 && (
                              <button
                                type="button"
                                onClick={() => moveTaskStep(task.id, 'next')}
                                className="p-1 rounded-md bg-slate-900 hover:bg-[#c5a059] text-slate-400 hover:text-slate-950 transition-colors border border-slate-800"
                                title="Avançar etapa"
                              >
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="h-32 flex flex-col items-center justify-center border-2 border-dashed border-slate-800/60 rounded-xl text-[11px] text-slate-500 gap-1">
                    <span>Nenhuma tarefa nesta etapa</span>
                    <span className="text-[9.5px] opacity-60">Arraste um card para cá</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── MODAL DE MÍDIAS & APROVAÇÃO BIDIRECIONAL ── */}
      {mediaModalTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-3xl rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 flex flex-col max-h-[90vh] shadow-2xl overflow-hidden">
            {/* Header do Modal */}
            <div className="p-4 bg-[#0d1629] border-b border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-[#c5a059] uppercase tracking-wider">
                  Mural de Avaliação & Homologação de Mídia
                </span>
                <h3 className="text-sm font-black text-white leading-tight mt-0.5">
                  {mediaModalTask.titulo}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setMediaModalTask(null)}
                className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Abas do Modal */}
            <div className="px-4 pt-3 flex items-center gap-2 border-b border-slate-800 bg-[#080d1a]">
              <button
                type="button"
                onClick={() => setMediaTab('previas')}
                className={`px-3 py-2 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                  mediaTab === 'previas'
                    ? 'border-[#00e5ff] text-[#00e5ff]'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Palette className="w-3.5 h-3.5" />
                <span>🎨 Prévias de Produção (Homologação)</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px]">
                  {mediaModalTask.anexos_midia?.filter((m) => m.tipo === 'previa_producao').length || 0}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setMediaTab('referencias')}
                className={`px-3 py-2 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                  mediaTab === 'referencias'
                    ? 'border-purple-400 text-purple-300'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Paperclip className="w-3.5 h-3.5" />
                <span>📥 Briefing & Referências</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px]">
                  {mediaModalTask.anexos_midia?.filter((m) => m.tipo === 'referencia').length || 0}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setMediaTab('apontamentos')}
                className={`px-3 py-2 text-xs font-bold border-b-2 transition-all flex items-center gap-1.5 ${
                  mediaTab === 'apontamentos'
                    ? 'border-amber-400 text-amber-300'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>💬 Apontamentos & Ajustes</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px]">
                  {mediaModalTask.apontamentos_ajuste?.length || 0}
                </span>
              </button>
            </div>

            {/* Conteúdo da Aba */}
            <div className="p-4 space-y-4 flex-1 overflow-y-auto">
              {/* ABA 1: PRÉVIAS & ARQUIVOS DE PRODUÇÃO */}
              {(mediaTab === 'previas' || mediaTab === 'referencias') && (
                <div className="space-y-4">
                  {/* Grid de Arquivos Anexados */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {(mediaModalTask.anexos_midia || [])
                      .filter((m) => (mediaTab === 'previas' ? m.tipo === 'previa_producao' : m.tipo === 'referencia'))
                      .map((anexo) => {
                        const isVideo = anexo.formato === 'video' || anexo.url.match(/\.(mp4|mov|webm)/i);
                        const isImg = anexo.formato === 'imagem' || anexo.url.match(/\.(jpg|jpeg|png|webp|gif)/i);

                        return (
                          <div
                            key={anexo.id}
                            className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-[#c5a059]/40 transition-all space-y-2 flex flex-col justify-between"
                          >
                            <div className="space-y-1.5">
                              {/* Prévia Visual se for Imagem */}
                              {isImg ? (
                                <div
                                  onClick={() => setPreviewMedia(anexo)}
                                  className="h-36 rounded-lg bg-black/40 border border-slate-800 overflow-hidden cursor-pointer relative group flex items-center justify-center"
                                >
                                  <img
                                    src={anexo.url}
                                    alt={anexo.nome}
                                    className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                                  />
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                    <Maximize2 className="w-5 h-5 text-white drop-shadow-md" />
                                  </div>
                                </div>
                              ) : isVideo ? (
                                <div
                                  onClick={() => setPreviewMedia(anexo)}
                                  className="h-36 rounded-lg bg-slate-950 border border-slate-800 flex flex-col items-center justify-center cursor-pointer hover:bg-slate-900 transition-colors relative group"
                                >
                                  <Film className="w-8 h-8 text-blue-400 mb-1" />
                                  <span className="text-[11px] font-bold text-white">Vídeo / Reels</span>
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                                    <Play className="w-6 h-6 text-emerald-400 drop-shadow-md" />
                                  </div>
                                </div>
                              ) : (
                                <div className="h-28 rounded-lg bg-slate-950 border border-slate-800 flex flex-col items-center justify-center p-2">
                                  <FileText className="w-6 h-6 text-[#c5a059] mb-1" />
                                  <span className="text-[10px] text-slate-400 font-medium truncate max-w-full">
                                    {anexo.nome}
                                  </span>
                                </div>
                              )}

                              <div>
                                <h4 className="text-xs font-bold text-white truncate">{anexo.nome}</h4>
                                <p className="text-[10px] text-slate-400">
                                  Enviado por: <strong className="text-slate-200">{anexo.enviado_por}</strong>
                                </p>
                              </div>
                            </div>

                            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                              <a
                                href={anexo.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[11px] font-bold text-[#00e5ff] hover:underline flex items-center gap-1"
                              >
                                <ExternalLink className="w-3 h-3" />
                                <span>Abrir / Baixar</span>
                              </a>
                            </div>
                          </div>
                        );
                      })}
                  </div>

                  {/* Formulário de Novo Anexo */}
                  <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2.5">
                    <h4 className="text-xs font-black text-white flex items-center gap-1.5">
                      <UploadCloud className="w-4 h-4 text-[#c5a059]" />
                      <span>
                        Anexar Novo Arquivo / Link ({mediaTab === 'previas' ? 'Prévia Pronta' : 'Referência'})
                      </span>
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <input
                        type="text"
                        placeholder="Nome / Rótulo da Mídia (ex: Banner_V1)"
                        value={novaMidiaNome}
                        onChange={(e) => setNovaMidiaNome(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none"
                      />

                      <input
                        type="url"
                        placeholder="URL da Imagem / Vídeo / Google Drive"
                        value={novaMidiaUrl}
                        onChange={(e) => setNovaMidiaUrl(e.target.value)}
                        className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none col-span-2"
                      />
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <select
                        value={novaMidiaTipo}
                        onChange={(e) => setNovaMidiaTipo(e.target.value as any)}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-700 text-xs font-bold text-slate-300 focus:outline-none"
                      >
                        <option value="previa_producao">🎨 Versão de Produção (Para Homologação)</option>
                        <option value="referencia">📥 Mídia de Referência / Briefing</option>
                      </select>

                      <button
                        type="button"
                        onClick={handleAdicionarMidia}
                        className="px-3.5 py-1.5 rounded-lg bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 text-xs font-bold shadow-md transition-all"
                      >
                        + Salvar Anexo
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* ABA 2: APONTAMENTOS & AJUSTES */}
              {mediaTab === 'apontamentos' && (
                <div className="space-y-3.5">
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {(mediaModalTask.apontamentos_ajuste || []).length > 0 ? (
                      mediaModalTask.apontamentos_ajuste!.map((apt) => (
                        <div
                          key={apt.id}
                          className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-[#e5c07b]">{apt.autor}</span>
                            <span className="text-slate-500 text-[10px]">{apt.criado_em.slice(0, 16).replace('T', ' ')}</span>
                          </div>
                          <p className="text-xs text-slate-300 leading-relaxed">{apt.texto}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-center py-6 text-xs text-slate-500">
                        Nenhum apontamento ou solicitação de ajuste registrada até o momento.
                      </p>
                    )}
                  </div>

                  {/* Input de Novo Apontamento */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Deixar apontamento de ajuste (ex: Corrigir brasão na versão 2)..."
                      value={novoApontamento}
                      onChange={(e) => setNovoApontamento(e.target.value)}
                      className="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleAdicionarApontamento}
                      className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1 shadow-md"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Enviar</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Footer do Modal: Ação de Homologação Final */}
            <div className="p-4 bg-[#0d1629] border-t border-slate-800 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">
                Status Atual: <strong className="text-white uppercase">{mediaModalTask.status}</strong>
              </span>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setMediaModalTask(null)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold"
                >
                  Fechar
                </button>

                <button
                  type="button"
                  onClick={() => handleAprovarMidiaCompleta(mediaModalTask)}
                  className="px-4 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-lg shadow-emerald-500/20 flex items-center gap-1.5 transition-all"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Aprovar Mídia & Concluir Pauta</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PREVIEW MODAL EM TELA CHEIA (HD ZOOM & PLAYER) ── */}
      {previewMedia && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/95 backdrop-blur-md animate-in fade-in">
          <div className="relative max-w-5xl w-full max-h-[90vh] flex flex-col items-center justify-center">
            <button
              type="button"
              onClick={() => setPreviewMedia(null)}
              className="absolute top-2 right-2 z-10 p-2 rounded-full bg-black/60 text-white hover:bg-red-500/80 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>

            {previewMedia.formato === 'video' || previewMedia.url.match(/\.(mp4|mov|webm)/i) ? (
              <video
                src={previewMedia.url}
                controls
                autoPlay
                className="max-h-[80vh] max-w-full rounded-2xl shadow-2xl border border-slate-800"
              />
            ) : (
              <img
                src={previewMedia.url}
                alt={previewMedia.nome}
                className="max-h-[80vh] max-w-full rounded-2xl shadow-2xl object-contain border border-slate-800"
              />
            )}

            <div className="mt-3 text-center">
              <h4 className="text-sm font-bold text-white">{previewMedia.nome}</h4>
              <p className="text-xs text-slate-400">Enviado por: {previewMedia.enviado_por}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL DE CRIAÇÃO DE NOVA TAREFA ── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-xl p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#c5a059]" />
                <span>Nova Demanda / Solicitação de Produção</span>
              </h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Título da Demanda / Pauta *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Gravação de Chamada Banda Sinfônica / Banner do Encontro"
                  value={newTarefa.titulo}
                  onChange={(e) => setNewTarefa({ ...newTarefa, titulo: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Descrição & Requisitos</label>
                <textarea
                  rows={2}
                  placeholder="Orientações de formato, legendas, dimensões, observações..."
                  value={newTarefa.descricao}
                  onChange={(e) => setNewTarefa({ ...newTarefa, descricao: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              {/* Identificação Dupla Obrigatória: Solicitante x Executor */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-amber-400 font-bold mb-1">👤 Oficial Solicitante *</label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Cap (FN) Bruno Tiago"
                    value={newTarefa.solicitante_nome}
                    onChange={(e) => setNewTarefa({ ...newTarefa, solicitante_nome: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-amber-500/40 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[#00e5ff] font-bold mb-1">👨‍💻 Executor Designado (ComSoc) *</label>
                  <select
                    value={newTarefa.responsavel}
                    onChange={(e) => setNewTarefa({ ...newTarefa, responsavel: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-[#00e5ff]/40 text-white focus:outline-none font-bold"
                  >
                    {efetivoList.length > 0 ? (
                      efetivoList.map((m) => (
                        <option key={m.id} value={`${m.posto_grad || ''} ${m.nome_guerra}`}>
                          {m.posto_grad} {m.nome_guerra} ({m.setor || 'CGCFN'})
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="2ºSG-FN Calaça">2ºSG-FN Calaça (Encarregado)</option>
                        <option value="3ºSG-FN-IF Souza">3ºSG-FN-IF Souza (Design & Vídeo)</option>
                        <option value="1ºSG-FN-IF Barbosa">1ºSG-FN-IF Barbosa (Foto)</option>
                        <option value="2ºSG-FN-CN Rodrigo">2ºSG-FN-CN Rodrigo (Diagramação)</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Categoria de Demanda</label>
                  <select
                    value={newTarefa.tipo_tarefa}
                    onChange={(e) => setNewTarefa({ ...newTarefa, tipo_tarefa: e.target.value as TarefaTipo })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                  >
                    {Object.entries(TIPOS_TAREFA).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.icon} {v.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Prioridade</label>
                  <select
                    value={newTarefa.prioridade}
                    onChange={(e) => setNewTarefa({ ...newTarefa, prioridade: e.target.value as TarefaPrioridade })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                  >
                    <option value="alta">🔥 Alta / Urgente</option>
                    <option value="media">🟡 Média</option>
                    <option value="baixa">🔵 Baixa / Normal</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Prazo Estimado</label>
                  <input
                    type="date"
                    value={newTarefa.prazo}
                    onChange={(e) => setNewTarefa({ ...newTarefa, prazo: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">
                  📎 Anexo Inicial de Briefing / Link do Drive (Opcional)
                </label>
                <input
                  type="url"
                  placeholder="https://drive.google.com/... ou link de imagem/vídeo"
                  value={newTarefa.link_midia_inicial}
                  onChange={(e) => setNewTarefa({ ...newTarefa, link_midia_inicial: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-black hover:bg-[#d6b26b] shadow-lg shadow-[#c5a059]/20"
                >
                  Cadastrar Demanda na Esteira
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
