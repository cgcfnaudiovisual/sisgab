import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Plus,
  Search,
  CheckCircle2,
  AlertTriangle,
  Camera,
  Video,
  Radio,
  Clock,
  RotateCcw,
  User,
  Calendar,
  Layers,
  Sparkles,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { EquipamentoCOMSOC, CautelaItem } from '../../types/database';
import { useAuth } from '../../context/AuthContext';

const MOCK_EQUIPAMENTOS: EquipamentoCOMSOC[] = [
  { id: 1, nome: 'Câmera Sony A7 IV (Corpo Principal)', e_pessoal: false, categoria: 'camera', status: 'cautelado', cautelado_por: '1ºSG-FN-IF Barbosa', descricao: 'Sensor Full Frame 33MP, gravação 4K 60p.' },
  { id: 2, nome: 'Câmera Sony A7 III (Backup)', e_pessoal: false, categoria: 'camera', status: 'disponivel', cautelado_por: null, descricao: 'Sensor Full Frame 24MP.' },
  { id: 3, nome: 'Lente Sony G Master 24-70mm f/2.8 II', e_pessoal: false, categoria: 'lente', status: 'cautelado', cautelado_por: '1ºSG-FN-IF Barbosa', descricao: 'Lente zoom versátil padrão ouro.' },
  { id: 4, nome: 'Lente Sony G Master 70-200mm f/2.8 OSS II', e_pessoal: false, categoria: 'lente', status: 'disponivel', cautelado_por: null, descricao: 'Teleobjetiva para formaturas e palcos.' },
  { id: 5, nome: 'Drone DJI Mavic 3 Pro (Kit Cine 3 Baterias)', e_pessoal: false, categoria: 'drone', status: 'disponivel', cautelado_por: null, descricao: 'Drone tri-câmera Hasselblad com homologação ANAC.' },
  { id: 6, nome: 'Kit Microfone Sem Fio DJI Mic 2 (2 Tx + 1 Rx)', e_pessoal: false, categoria: 'audio', status: 'cautelado', cautelado_por: '2ºSG-FN-CN Rodrigo', descricao: 'Gravação interna 32-bit float.' },
  { id: 7, nome: 'Painel LED Aputure Amaran 200d + Softbox', e_pessoal: false, categoria: 'iluminacao', status: 'disponivel', cautelado_por: null, descricao: 'Iluminação de estúdio para entrevistas.' },
  { id: 8, nome: 'Gimbal DJI RS 3 Pro Combo', e_pessoal: false, categoria: 'acessorio', status: 'manutencao', cautelado_por: null, descricao: 'Estabilizador com motor LiDAR (em calibração).' },
];

const MOCK_CAUTELAS: CautelaItem[] = [
  { id: 1, equipamento: 'Sony A7 IV + Lente 24-70mm GM', retirado_por: '1ºSG-FN-IF Barbosa', data_retirada: '2026-08-16 08:30', status: 'retirado', e_pessoal: false, event_date: '2026-08-17' },
  { id: 2, equipamento: 'Kit DJI Mic 2', retirado_por: '2ºSG-FN-CN Rodrigo', data_retirada: '2026-08-15 14:00', status: 'retirado', e_pessoal: false, event_date: '2026-08-16' },
  { id: 3, equipamento: 'Drone DJI Mavic 3', retirado_por: '3ºSG-FN-IF Souza', data_retirada: '2026-08-10 09:00', data_devolucao: '2026-08-11 17:00', status: 'devolvido', e_pessoal: false, event_date: '2026-08-10' },
];

export const EquipmentCautela: React.FC = () => {
  const { user } = useAuth();
  const [equipamentos, setEquipamentos] = useState<EquipamentoCOMSOC[]>(MOCK_EQUIPAMENTOS);
  const [cautelas, setCautelas] = useState<CautelaItem[]>(MOCK_CAUTELAS);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCat, setSelectedCat] = useState<string>('todos');
  const [activeTab, setActiveTab] = useState<'catalogo' | 'historico'>('catalogo');

  // Modal Nova Cautela
  const [cautelaModal, setCautelaModal] = useState<{
    isOpen: boolean;
    equipamento: EquipamentoCOMSOC | null;
    retirado_por: string;
    data_prevista: string;
  }>({
    isOpen: false,
    equipamento: null,
    retirado_por: user?.nome_guerra ? user.nome_guerra : '1ºSG-FN-IF Barbosa',
    data_prevista: new Date().toISOString().split('T')[0],
  });

  useEffect(() => {
    loadCautelaData();
  }, []);

  const loadCautelaData = async () => {
    try {
      const { data, error } = await supabase
        .from('comsoc_equipamentos')
        .select('*');

      if (!error && data && data.length > 0) {
        setEquipamentos(data as EquipamentoCOMSOC[]);
      }
    } catch {
      // Fallback
    }
  };

  const handleEmprestar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cautelaModal.equipamento || !cautelaModal.retirado_por) {
      toast.error('Informe o militar responsável pela retirada.');
      return;
    }

    const { equipamento, retirado_por, data_prevista } = cautelaModal;

    // 1. Atualização Otimista Instantânea (0ms)
    setEquipamentos((prev) =>
      prev.map((eq) =>
        eq.id === equipamento.id
          ? { ...eq, status: 'cautelado', cautelado_por: retirado_por }
          : eq
      )
    );

    const novaCautela: CautelaItem = {
      id: Date.now(),
      equipamento: equipamento.nome,
      retirado_por,
      data_retirada: new Date().toLocaleString('pt-BR'),
      status: 'retirado',
      e_pessoal: false,
      event_date: data_prevista,
    };

    setCautelas([novaCautela, ...cautelas]);
    setCautelaModal({ isOpen: false, equipamento: null, retirado_por: '', data_prevista: '' });

    confetti({
      particleCount: 50,
      spread: 50,
      origin: { y: 0.7 },
    });

    toast.success(`Cautela de "${equipamento.nome}" registrada para ${retirado_por}!`);

    // 2. Persistência no Supabase
    try {
      await supabase.from('cautela_equipamentos').insert({
        equipamento: equipamento.nome,
        retirado_por,
        status: 'retirado',
        event_date: data_prevista,
      });
    } catch (err) {
      console.warn('Erro ao registrar cautela no Supabase:', err);
    }
  };

  const handleDevolver = async (eqId: number, eqNome: string) => {
    // 1. Atualização Otimista Instantânea
    setEquipamentos((prev) =>
      prev.map((eq) =>
        eq.id === eqId ? { ...eq, status: 'disponivel', cautelado_por: null } : eq
      )
    );

    setCautelas((prev) =>
      prev.map((c) =>
        c.equipamento.includes(eqNome) && c.status === 'retirado'
          ? { ...c, status: 'devolvido', data_devolucao: new Date().toLocaleString('pt-BR') }
          : c
      )
    );

    toast.success(`Equipamento "${eqNome}" devolvido ao acervo!`);

    // 2. Supabase
    try {
      await supabase
        .from('cautela_equipamentos')
        .update({ status: 'devolvido', data_devolucao: new Date().toISOString() })
        .eq('equipamento', eqNome)
        .eq('status', 'retirado');
    } catch (err) {
      console.warn('Erro ao devolver no Supabase:', err);
    }
  };

  const total = equipamentos.length;
  const disponiveis = equipamentos.filter((e) => e.status === 'disponivel').length;
  const cautelados = equipamentos.filter((e) => e.status === 'cautelado').length;
  const manutencao = equipamentos.filter((e) => e.status === 'manutencao').length;

  const filteredEquipamentos = equipamentos.filter((e) => {
    const matchQ =
      e.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (e.cautelado_por && e.cautelado_por.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchCat = selectedCat === 'todos' || e.categoria === selectedCat;
    return matchQ && matchCat;
  });

  return (
    <div className="space-y-6">
      {/* Header & Ações */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Logística Audiovisual
            </span>
            <span className="text-slate-400 text-xs">• Cautela & Acervo de Material</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Controle de Cautela de Equipamentos
          </h1>
        </div>
      </div>

      {/* Cards de Métricas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#0b1222] border border-slate-800">
          <p className="text-xs text-slate-400 font-medium">Total de Itens Cadastrados</p>
          <p className="text-2xl font-black text-white mt-1">{total}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-emerald-500/20 bg-emerald-500/5">
          <p className="text-xs text-emerald-400 font-semibold">Disponíveis no Acervo</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{disponiveis}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-amber-500/20 bg-amber-500/5">
          <p className="text-xs text-amber-400 font-semibold">Cautelados em Missão</p>
          <p className="text-2xl font-black text-amber-400 mt-1">{cautelados}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-red-500/20 bg-red-500/5">
          <p className="text-xs text-red-400 font-semibold">Em Manutenção</p>
          <p className="text-2xl font-black text-red-400 mt-1">{manutencao}</p>
        </div>
      </div>

      {/* Tabs & Filtros */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          <button
            onClick={() => setSelectedCat('todos')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              selectedCat === 'todos'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            Todos ({equipamentos.length})
          </button>
          <button
            onClick={() => setSelectedCat('camera')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              selectedCat === 'camera'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            📷 Câmeras
          </button>
          <button
            onClick={() => setSelectedCat('lente')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              selectedCat === 'lente'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            🔍 Lentes
          </button>
          <button
            onClick={() => setSelectedCat('drone')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              selectedCat === 'drone'
                ? 'bg-[#c5a059]/20 text-[#e5c07b] border border-[#c5a059]/40'
                : 'bg-slate-900/60 text-slate-400 border border-slate-800'
            }`}
          >
            🛸 Drones
          </button>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Buscar equipamento ou militar..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
          />
        </div>
      </div>

      {/* Grid de Equipamentos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredEquipamentos.map((eq) => {
          const isDisponivel = eq.status === 'disponivel';
          const isCautelado = eq.status === 'cautelado';

          return (
            <div
              key={eq.id}
              className="p-5 rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/40 transition-all space-y-4 shadow-lg flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-lg text-[#c5a059]">
                    {eq.categoria === 'camera' ? '📷' : eq.categoria === 'lente' ? '🔍' : eq.categoria === 'drone' ? '🛸' : '🎙️'}
                  </div>

                  <span
                    className={`px-2.5 py-0.5 text-[10px] font-black rounded-md uppercase tracking-wider ${
                      isDisponivel
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : isCautelado
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        : 'bg-red-500/15 text-red-400 border border-red-500/30'
                    }`}
                  >
                    {eq.status}
                  </span>
                </div>

                <h3 className="text-sm font-black text-white leading-snug">
                  {eq.nome}
                </h3>

                {eq.descricao && (
                  <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                    {eq.descricao}
                  </p>
                )}

                {isCautelado && eq.cautelado_por && (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 flex items-center gap-2">
                    <User className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                    <span>Cautelado com: <strong>{eq.cautelado_por}</strong></span>
                  </div>
                )}
              </div>

              {/* Botões de Ação */}
              <div className="pt-3 border-t border-slate-800/80">
                {isDisponivel ? (
                  <button
                    onClick={() =>
                      setCautelaModal({
                        isOpen: true,
                        equipamento: eq,
                        retirado_por: user?.nome_guerra ? user.nome_guerra : '',
                        data_prevista: new Date().toISOString().split('T')[0],
                      })
                    }
                    className="w-full py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-transform active:scale-95"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Cautelar Equipamento</span>
                  </button>
                ) : isCautelado ? (
                  <button
                    onClick={() => handleDevolver(eq.id, eq.nome)}
                    className="w-full py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 font-bold text-xs flex items-center justify-center gap-1.5 transition-all"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Receber Devolução</span>
                  </button>
                ) : (
                  <span className="block text-center text-xs text-red-400 font-bold py-1">
                    Em Manutenção
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal Nova Cautela */}
      {cautelaModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-md p-5 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <h3 className="text-sm font-black text-white">Termo de Cautela de Material</h3>
            <p className="text-xs text-slate-400">
              Equipamento: <strong className="text-[#c5a059]">{cautelaModal.equipamento?.nome}</strong>
            </p>

            <form onSubmit={handleEmprestar} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Militar Responsável pela Retirada *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: 1ºSG-FN-IF Barbosa"
                  value={cautelaModal.retirado_por}
                  onChange={(e) =>
                    setCautelaModal({ ...cautelaModal, retirado_por: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Data Prevista de Devolução *
                </label>
                <input
                  type="date"
                  required
                  value={cautelaModal.data_prevista}
                  onChange={(e) =>
                    setCautelaModal({ ...cautelaModal, data_prevista: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-[10.5px] text-slate-400 leading-relaxed">
                ⚖️ <strong>Termo de Responsabilidade:</strong> O militar assume integral responsabilidade pela guarda, conservação e integridade do material cautelado até sua efetiva devolução.
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() =>
                    setCautelaModal({ isOpen: false, equipamento: null, retirado_por: '', data_prevista: '' })
                  }
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold"
                >
                  Assinar & Cautelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
