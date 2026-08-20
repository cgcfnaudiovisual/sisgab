import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
import {
  Gift,
  Plus,
  Search,
  CheckCircle2,
  AlertTriangle,
  History,
  Send,
  User,
  Calendar,
  Sparkles,
  Package,
  TrendingDown,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { BrindeEstoque, BrindeDistribuicao } from '../../types/database';
import { useAuth } from '../../context/AuthContext';
import { getBrasiliaDateStr } from '../../utils/formatters';

const MOCK_ESTOQUE: BrindeEstoque[] = [
  { id: 1, nome_item: 'Moeda Comemorativa CGCFN (Challenge Coin)', quantidade_total: 100, quantidade_disponivel: 42, descricao: 'Moeda em metal nobre com acabamento dourado e esmaltado.', criado_em: new Date().toISOString() },
  { id: 2, nome_item: 'Caneta Executiva Oficial CGCFN', quantidade_total: 150, quantidade_disponivel: 88, descricao: 'Caneta metálica em estojo de veludo azul marinho.', criado_em: new Date().toISOString() },
  { id: 3, nome_item: 'Boné Tático Oficial Fuzileiros Navais', quantidade_total: 80, quantidade_disponivel: 15, descricao: 'Boné camuflado padrão Força de Fuzileiros da Esquadra.', criado_em: new Date().toISOString() },
  { id: 4, nome_item: 'Placa de Homenagem em Madeira e Latão', quantidade_total: 20, quantidade_disponivel: 4, descricao: 'Placa com gravação a laser para Almirantes e Ministros.', criado_em: new Date().toISOString() },
  { id: 5, nome_item: 'Livro Histórico: A Fortaleza de São José', quantidade_total: 50, quantidade_disponivel: 28, descricao: 'Edição de luxo em capa dura sobre a história dos Fuzileiros.', criado_em: new Date().toISOString() },
  { id: 6, nome_item: 'Chaveiro Oficial Brasão CGCFN', quantidade_total: 200, quantidade_disponivel: 140, descricao: 'Chaveiro em liga metálica com brasão resinado.', criado_em: new Date().toISOString() },
];

const MOCK_HISTORICO: BrindeDistribuicao[] = [
  { id: 1, brinde_id: 1, brinde_nome: 'Moeda Comemorativa CGCFN', quantidade: 1, destinatario_nome: 'Almirante de Esquadra Olsen (Comandante da Marinha)', data_entrega: '2026-08-15', entregue_por: 'CT (FN) Silva', criado_em: new Date().toISOString() },
  { id: 2, brinde_id: 4, brinde_nome: 'Placa de Homenagem em Madeira', quantidade: 1, destinatario_nome: 'Deputado Federal Mendes (Comissão de Defesa)', data_entrega: '2026-08-14', entregue_por: 'CC (FN) Carlos', criado_em: new Date().toISOString() },
  { id: 3, brinde_id: 2, brinde_nome: 'Caneta Executiva Oficial', quantidade: 2, destinatario_nome: 'Delegação do Corpo de Fuzileiros Navais dos EUA', data_entrega: '2026-08-10', entregue_por: '1ºTen (T) Mariana', criado_em: new Date().toISOString() },
];

export const GiftsStock: React.FC = () => {
  const { user } = useAuth();
  const [estoque, setEstoque] = useState<BrindeEstoque[]>(MOCK_ESTOQUE);
  const [historico, setHistorico] = useState<BrindeDistribuicao[]>(MOCK_HISTORICO);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'catalogo' | 'historico'>('catalogo');

  // Modais
  const [distribuirModal, setDistribuirModal] = useState<{
    isOpen: boolean;
    item: BrindeEstoque | null;
    quantidade: number;
    destinatario: string;
  }>({
    isOpen: false,
    item: null,
    quantidade: 1,
    destinatario: '',
  });

  const [novoBrindeModal, setNovoBrindeModal] = useState(false);
  const [novoItem, setNovoItem] = useState({
    nome_item: '',
    quantidade_total: 10,
    descricao: '',
  });

  useEffect(() => {
    loadEstoqueData();
  }, []);

  const loadEstoqueData = async () => {
    try {
      const { data, error } = await supabase
        .from('comsoc_brindes_estoque')
        .select('*')
        .order('nome_item');

      if (!error && data && data.length > 0) {
        setEstoque(data as BrindeEstoque[]);
      }
    } catch {
      // Fallback
    }
  };

  const handleDistribuir = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!distribuirModal.item || !distribuirModal.destinatario) {
      toast.error('Informe o destinatário da entrega.');
      return;
    }

    const { item, quantidade, destinatario } = distribuirModal;

    if (quantidade > item.quantidade_disponivel) {
      toast.error('Quantidade superior ao saldo disponível em estoque.');
      return;
    }

    // 1. Atualização Otimista Instantânea (0ms)
    setEstoque((prev) =>
      prev.map((b) =>
        b.id === item.id
          ? { ...b, quantidade_disponivel: b.quantidade_disponivel - quantidade }
          : b
      )
    );

    const novoHist: BrindeDistribuicao = {
      id: Date.now(),
      brinde_id: item.id,
      brinde_nome: item.nome_item,
      quantidade,
      destinatario_nome: destinatario,
      data_entrega: getBrasiliaDateStr(),
      entregue_por: user?.nome_guerra || 'Operador',
      criado_em: new Date().toISOString(),
    };

    setHistorico([novoHist, ...historico]);
    setDistribuirModal({ isOpen: false, item: null, quantidade: 1, destinatario: '' });

    militaryAudio.playTacticalBeep();

    toast.success(`Entrega de ${quantidade}x ${item.nome_item} registrada!`);

    // 2. Persistência no Supabase
    try {
      await supabase
        .from('comsoc_brindes_estoque')
        .update({ quantidade_disponivel: item.quantidade_disponivel - quantidade })
        .eq('id', item.id);

      await supabase.from('comsoc_brindes_distribuicao').insert({
        brinde_id: item.id,
        quantidade,
        destinatario_nome: destinatario,
        entregue_por: user?.nome_guerra || 'Operador',
      });
    } catch (err) {
      console.warn('Erro ao registrar distribuição no Supabase:', err);
    }
  };

  const handleCriarNovoBrinde = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoItem.nome_item) {
      toast.error('Informe o nome do brinde.');
      return;
    }

    const created: BrindeEstoque = {
      id: Date.now(),
      nome_item: novoItem.nome_item,
      quantidade_total: Number(novoItem.quantidade_total),
      quantidade_disponivel: Number(novoItem.quantidade_total),
      descricao: novoItem.descricao,
      criado_em: new Date().toISOString(),
    };

    setEstoque([...estoque, created]);
    setNovoBrindeModal(false);
    toast.success('Brinde cadastrado no estoque!');

    try {
      await supabase.from('comsoc_brindes_estoque').insert({
        nome_item: novoItem.nome_item,
        quantidade_total: Number(novoItem.quantidade_total),
        quantidade_disponivel: Number(novoItem.quantidade_total),
        descricao: novoItem.descricao,
      });
    } catch (err) {
      console.warn('Erro ao cadastrar brinde no Supabase:', err);
    }
  };

  const totalGeral = estoque.reduce((acc, curr) => acc + curr.quantidade_disponivel, 0);
  const totalCriticos = estoque.filter((b) => b.quantidade_disponivel <= 5).length;

  const filteredEstoque = estoque.filter(
    (b) =>
      b.nome_item.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (b.descricao && b.descricao.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Header & Ações */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Relações Públicas & Cerimonial
            </span>
            <span className="text-slate-400 text-xs">• Estoque Institucional</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Estoque de Brindes do Gabinete
          </h1>
        </div>

        <button
          onClick={() => setNovoBrindeModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs shadow-md shadow-[#c5a059]/20 transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Cadastrar Novo Item</span>
        </button>
      </div>

      {/* Cards de Métricas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#0b1222] border border-slate-800">
          <p className="text-xs text-slate-400 font-medium">Tipos de Itens</p>
          <p className="text-2xl font-black text-white mt-1">{estoque.length}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-emerald-500/20 bg-emerald-500/5">
          <p className="text-xs text-emerald-400 font-semibold">Saldo Total Disponível</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{totalGeral} un</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-blue-500/20 bg-blue-500/5">
          <p className="text-xs text-blue-400 font-semibold">Entregas Realizadas</p>
          <p className="text-2xl font-black text-blue-400 mt-1">{historico.length}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between">
            <p className="text-xs text-amber-400 font-semibold">Estoque Baixo</p>
            {totalCriticos > 0 && <AlertTriangle className="w-4 h-4 text-amber-400 animate-pulse" />}
          </div>
          <p className="text-2xl font-black text-amber-400 mt-1">{totalCriticos} itens</p>
        </div>
      </div>

      {/* Tabs & Barra de Busca */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => setActiveTab('catalogo')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'catalogo'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            📦 Catálogo de Itens ({estoque.length})
          </button>

          <button
            onClick={() => setActiveTab('historico')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'historico'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            📜 Histórico de Entregas ({historico.length})
          </button>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Buscar brinde ou autoridade..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
          />
        </div>
      </div>

      {/* Conteúdo: Catálogo de Brindes */}
      {activeTab === 'catalogo' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredEstoque.map((item) => {
            const isLow = item.quantidade_disponivel <= 5;
            const percent = Math.round((item.quantidade_disponivel / item.quantidade_total) * 100);

            return (
              <div
                key={item.id}
                className="p-5 rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/40 transition-all space-y-4 shadow-lg flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="w-10 h-10 rounded-xl bg-[#c5a059]/10 border border-[#c5a059]/30 flex items-center justify-center text-lg text-[#c5a059] shrink-0">
                      🎁
                    </div>
                    <span
                      className={`px-2 py-0.5 text-[10px] font-black rounded-md uppercase ${
                        isLow
                          ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                      }`}
                    >
                      {item.quantidade_disponivel} / {item.quantidade_total} un
                    </span>
                  </div>

                  <h3 className="text-sm font-black text-white leading-snug">
                    {item.nome_item}
                  </h3>

                  {item.descricao && (
                    <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                      {item.descricao}
                    </p>
                  )}

                  {/* Barra de Progresso de Saldo */}
                  <div className="space-y-1 pt-1">
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          isLow ? 'bg-amber-500' : 'bg-emerald-400'
                        }`}
                        style={{ width: `${percent}%` }}
                      ></div>
                    </div>
                    <div className="flex items-center justify-between text-[9.5px] text-slate-500">
                      <span>Disponibilidade</span>
                      <span>{percent}%</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/80">
                  <button
                    onClick={() =>
                      setDistribuirModal({
                        isOpen: true,
                        item,
                        quantidade: 1,
                        destinatario: '',
                      })
                    }
                    className="w-full py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-transform active:scale-95"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Registrar Entrega</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Histórico de Entregas */
        <div className="rounded-2xl bg-[#0b1222] border border-slate-800 overflow-hidden shadow-xl">
          <div className="divide-y divide-slate-800/80">
            {historico.map((h) => (
              <div
                key={h.id}
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-white">{h.destinatario_nome}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 text-[10px] font-bold border border-purple-500/30">
                      {h.quantidade}x {h.brinde_nome}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Entregue por: <strong className="text-slate-300">{h.entregue_por}</strong>
                  </p>
                </div>

                <div className="text-xs font-bold text-[#00e5ff] shrink-0">
                  {h.data_entrega}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal Registrar Entrega */}
      {distribuirModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-md p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <h3 className="text-sm font-black text-white">Registrar Entrega de Brinde</h3>
            <p className="text-xs text-slate-400">
              Item: <strong className="text-[#c5a059]">{distribuirModal.item?.nome_item}</strong> (Saldo: {distribuirModal.item?.quantidade_disponivel} un)
            </p>

            <form onSubmit={handleDistribuir} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Autoridade / Destinatário Agraciado *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Almirante de Esquadra Olsen"
                  value={distribuirModal.destinatario}
                  onChange={(e) =>
                    setDistribuirModal({ ...distribuirModal, destinatario: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Quantidade Entregue *</label>
                <input
                  type="number"
                  min={1}
                  max={distribuirModal.item?.quantidade_disponivel || 1}
                  value={distribuirModal.quantidade}
                  onChange={(e) =>
                    setDistribuirModal({ ...distribuirModal, quantidade: Number(e.target.value) })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() =>
                    setDistribuirModal({ isOpen: false, item: null, quantidade: 1, destinatario: '' })
                  }
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold"
                >
                  Confirmar Entrega
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Novo Brinde */}
      {novoBrindeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-md p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <h3 className="text-sm font-black text-white">Cadastrar Novo Item no Estoque</h3>

            <form onSubmit={handleCriarNovoBrinde} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Nome do Item *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Canivete Tático Suíço CGCFN"
                  value={novoItem.nome_item}
                  onChange={(e) => setNovoItem({ ...novoItem, nome_item: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Quantidade Inicial *</label>
                <input
                  type="number"
                  min={1}
                  value={novoItem.quantidade_total}
                  onChange={(e) => setNovoItem({ ...novoItem, quantidade_total: Number(e.target.value) })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Descrição / Especificação</label>
                <textarea
                  rows={2}
                  placeholder="Acabamento, estojo, finalidade..."
                  value={novoItem.descricao}
                  onChange={(e) => setNovoItem({ ...novoItem, descricao: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setNovoBrindeModal(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
