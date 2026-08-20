import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { TarefaCOMSOC, TarefaStatus, TarefaPrioridade } from '../../types/database';
import { useAuth } from '../../context/AuthContext';

const COLUNAS: { id: TarefaStatus; title: string; color: string; bg: string; border: string }[] = [
  { id: 'a_fazer', title: 'A Fazer (Backlog)', color: 'text-slate-300', bg: 'bg-slate-900/40', border: 'border-slate-800' },
  { id: 'em_andamento', title: 'Em Andamento', color: 'text-[#00e5ff]', bg: 'bg-[#00e5ff]/5', border: 'border-[#00e5ff]/30' },
  { id: 'revisao', title: 'Revisão / Aprovação', color: 'text-amber-400', bg: 'bg-amber-500/5', border: 'border-amber-500/30' },
  { id: 'concluido', title: 'Concluído', color: 'text-emerald-400', bg: 'bg-emerald-500/5', border: 'border-emerald-500/30' },
];

const PRIORIDADES: Record<TarefaPrioridade, { label: string; badge: string }> = {
  alta: { label: 'Alta', badge: 'bg-red-500/15 text-red-400 border-red-500/40' },
  media: { label: 'Média', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/40' },
  baixa: { label: 'Baixa', badge: 'bg-blue-500/15 text-blue-400 border-blue-500/40' },
};

const MOCK_TAREFAS: TarefaCOMSOC[] = [
  {
    id: 1,
    titulo: 'Edição do Vídeo de Passagem de Comando (Teaser 60s)',
    descricao: 'Cortar melhores momentos e adicionar trilha sonora oficial e créditos.',
    responsavel: '3ºSG-FN-IF Souza',
    prioridade: 'alta',
    status: 'em_andamento',
    prazo: '2026-08-21',
    criado_em: new Date().toISOString(),
  },
  {
    id: 2,
    titulo: 'Diagramação do Informativo Mensal do CGCFN',
    descricao: 'Montar layout das páginas 4 e 5 no Estúdio Gráfico e validar com CheGab.',
    responsavel: '2ºSG-FN-CN Rodrigo',
    prioridade: 'media',
    status: 'a_fazer',
    prazo: '2026-08-25',
    criado_em: new Date().toISOString(),
  },
  {
    id: 3,
    titulo: 'Curadoria de Fotos da Visita da Delegação Estrangeira',
    descricao: 'Selecionar as 30 melhores fotos no acervo e marcar autoridades para homologação.',
    responsavel: '1ºSG-FN-IF Barbosa',
    prioridade: 'alta',
    status: 'revisao',
    prazo: '2026-08-19',
    criado_em: new Date().toISOString(),
  },
  {
    id: 4,
    titulo: 'Criação de Artes para o Telão SisGAB TV (Aniversariantes)',
    descricao: 'Atualizar os cartazes dos aniversariantes da semana de agosto.',
    responsavel: '1ºTen (T) Mariana',
    prioridade: 'baixa',
    status: 'concluido',
    prazo: '2026-08-17',
    criado_em: new Date().toISOString(),
  },
];

export const KanbanTasks: React.FC = () => {
  const { user } = useAuth();
  const [tarefas, setTarefas] = useState<TarefaCOMSOC[]>(MOCK_TAREFAS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedResp, setSelectedResp] = useState<string>('todos');
  const [modalOpen, setModalOpen] = useState(false);
  const [newTarefa, setNewTarefa] = useState({
    titulo: '',
    descricao: '',
    responsavel: user?.nome_guerra ? user.nome_guerra : '1ºSG-FN-IF Barbosa',
    prioridade: 'media' as TarefaPrioridade,
    status: 'a_fazer' as TarefaStatus,
    prazo: '',
  });

  useEffect(() => {
    loadTarefas();

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

  const loadTarefas = async () => {
    try {
      const { data, error } = await supabase
        .from('tarefas_pendentes')
        .select('*')
        .order('id', { ascending: false });

      if (!error && data && data.length > 0) {
        setTarefas(
          data.map((d: any) => ({
            id: d.id,
            titulo: d.titulo,
            descricao: d.descricao,
            responsavel: d.responsavel,
            prioridade: (d.prioridade as TarefaPrioridade) || 'media',
            status: (d.status as TarefaStatus) || 'a_fazer',
            prazo: d.prazo,
            criado_em: d.criado_em,
          }))
        );
      }
    } catch {
      // Fallback
    }
  };

  const moveTask = async (taskId: number, direction: 'next' | 'prev') => {
    const statusOrder: TarefaStatus[] = ['a_fazer', 'em_andamento', 'revisao', 'concluido'];
    const currentTask = tarefas.find((t) => t.id === taskId);
    if (!currentTask) return;

    const currentIdx = statusOrder.indexOf(currentTask.status);
    const newIdx = direction === 'next' ? currentIdx + 1 : currentIdx - 1;

    if (newIdx < 0 || newIdx >= statusOrder.length) return;
    const newStatus = statusOrder[newIdx];

    // 1. Atualização Otimista Instantânea (0ms)
    setTarefas((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
    );

    if (newStatus === 'concluido') {
      militaryAudio.playTacticalBeep();
      toast.success('Tarefa concluída com sucesso!');
    }

    // 2. Persistência no Supabase
    try {
      await supabase
        .from('tarefas_pendentes')
        .update({ status: newStatus, atualizado_em: new Date().toISOString() })
        .eq('id', taskId);
    } catch (e) {
      console.warn('Erro ao atualizar status da tarefa:', e);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTarefa.titulo) {
      toast.error('Informe o título da tarefa.');
      return;
    }

    const tempId = Date.now();
    const created: TarefaCOMSOC = {
      id: tempId,
      titulo: newTarefa.titulo,
      descricao: newTarefa.descricao,
      responsavel: newTarefa.responsavel,
      prioridade: newTarefa.prioridade,
      status: newTarefa.status,
      prazo: newTarefa.prazo || null,
      criado_em: new Date().toISOString(),
    };

    setTarefas([created, ...tarefas]);
    setModalOpen(false);
    toast.success('Tarefa adicionada ao Kanban!');

    try {
      const { data } = await supabase.from('tarefas_pendentes').insert({
        titulo: newTarefa.titulo,
        descricao: newTarefa.descricao,
        responsavel: newTarefa.responsavel,
        prioridade: newTarefa.prioridade,
        status: newTarefa.status,
        prazo: newTarefa.prazo || null,
      }).select();

      if (data && data[0]) {
        setTarefas((prev) =>
          prev.map((t) => (t.id === tempId ? { ...t, id: data[0].id } : t))
        );
      }
    } catch (e) {
      console.warn('Erro ao salvar tarefa no Supabase:', e);
    }
  };

  const filteredTarefas = tarefas.filter((t) => {
    const matchQuery =
      t.titulo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.descricao && t.descricao.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchResp = selectedResp === 'todos' || t.responsavel === selectedResp;
    return matchQuery && matchResp;
  });

  const uniqueResponsaveis = Array.from(new Set(tarefas.map((t) => t.responsavel)));

  return (
    <div className="space-y-6">
      {/* Header & Ações */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Fluxo Ágil COMSOC
            </span>
            <span className="text-slate-400 text-xs">• Tarefas & Entregas</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Quadro Kanban de Produção
          </h1>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>Nova Tarefa</span>
        </button>
      </div>

      {/* Barra de Filtros Rápidos */}
      <div className="p-3 rounded-xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Buscar tarefa ou descrição..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-[#c5a059]" />
          <span className="text-xs text-slate-400">Responsável:</span>
          <select
            value={selectedResp}
            onChange={(e) => setSelectedResp(e.target.value)}
            className="bg-slate-900 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none"
          >
            <option value="todos">Todos da Equipe</option>
            {uniqueResponsaveis.map((resp) => (
              <option key={resp} value={resp}>
                {resp}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid das 4 Colunas do Kanban */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {COLUNAS.map((coluna, colIdx) => {
          const colTasks = filteredTarefas.filter((t) => t.status === coluna.id);

          return (
            <div
              key={coluna.id}
              className={`rounded-2xl border ${coluna.border} ${coluna.bg} p-4 flex flex-col min-h-[500px] shadow-lg`}
            >
              {/* Topo da Coluna */}
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-black uppercase tracking-wider ${coluna.color}`}>
                    {coluna.title}
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-[11px] font-bold">
                  {colTasks.length}
                </span>
              </div>

              {/* Lista de Cards da Coluna */}
              <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                {colTasks.length > 0 ? (
                  colTasks.map((task) => {
                    const prio = PRIORIDADES[task.prioridade];

                    return (
                      <div
                        key={task.id}
                        className="p-3.5 rounded-xl bg-[#0d1629] border border-slate-800/90 hover:border-[#c5a059]/40 transition-all space-y-2.5 shadow-md group"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span
                            className={`px-2 py-0.5 rounded-md text-[9.5px] font-black uppercase tracking-wider border ${prio.badge}`}
                          >
                            {prio.label}
                          </span>

                          {task.prazo && (
                            <span className="text-[10px] text-slate-400 font-semibold flex items-center gap-1">
                              <Calendar className="w-3 h-3 text-[#c5a059]" />
                              {task.prazo}
                            </span>
                          )}
                        </div>

                        <h3 className="text-xs font-bold text-white group-hover:text-[#e5c07b] transition-colors leading-snug">
                          {task.titulo}
                        </h3>

                        {task.descricao && (
                          <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                            {task.descricao}
                          </p>
                        )}

                        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <div className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[9px] font-bold text-[#c5a059]">
                              <User className="w-2.5 h-2.5" />
                            </div>
                            <span className="text-[10.5px] text-slate-300 font-medium truncate max-w-[110px]">
                              {task.responsavel}
                            </span>
                          </div>

                          {/* Botões de Avanço Rápido */}
                          <div className="flex items-center gap-1">
                            {colIdx > 0 && (
                              <button
                                onClick={() => moveTask(task.id, 'prev')}
                                className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                                title="Voltar etapa"
                              >
                                <ArrowLeft className="w-3 h-3" />
                              </button>
                            )}

                            {colIdx < COLUNAS.length - 1 && (
                              <button
                                onClick={() => moveTask(task.id, 'next')}
                                className="p-1 rounded-md bg-slate-800 hover:bg-[#c5a059] text-slate-400 hover:text-slate-950 transition-colors"
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
                  <div className="h-32 flex items-center justify-center border-2 border-dashed border-slate-800/60 rounded-xl text-[11px] text-slate-500">
                    Vazio
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal de Criação de Tarefa */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-lg p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <h3 className="text-sm font-black text-white">Nova Tarefa para a Equipe</h3>

            <form onSubmit={handleCreateTask} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Título da Tarefa *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Gravar chamada em vídeo para o Chefe de Gabinete"
                  value={newTarefa.titulo}
                  onChange={(e) => setNewTarefa({ ...newTarefa, titulo: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Descrição / Instruções</label>
                <textarea
                  rows={3}
                  placeholder="Detalhes adicionais sobre os requisitos..."
                  value={newTarefa.descricao}
                  onChange={(e) => setNewTarefa({ ...newTarefa, descricao: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Responsável *</label>
                  <input
                    type="text"
                    required
                    value={newTarefa.responsavel}
                    onChange={(e) => setNewTarefa({ ...newTarefa, responsavel: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Prioridade</label>
                  <select
                    value={newTarefa.prioridade}
                    onChange={(e) => setNewTarefa({ ...newTarefa, prioridade: e.target.value as TarefaPrioridade })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                  >
                    <option value="alta">Alta</option>
                    <option value="media">Média</option>
                    <option value="baixa">Baixa</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Prazo de Entrega</label>
                <input
                  type="date"
                  value={newTarefa.prazo}
                  onChange={(e) => setNewTarefa({ ...newTarefa, prazo: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold hover:bg-[#d6b26b]"
                >
                  Salvar Tarefa
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
