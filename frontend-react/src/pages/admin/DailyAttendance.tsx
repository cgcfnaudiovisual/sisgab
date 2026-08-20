import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
import {
  Calendar,
  CheckCircle2,
  Copy,
  Users,
  Shield,
  Clock,
  Sparkles,
  Save,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  CheckSquare,
  AlertTriangle,
  Send,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { StatusPresenca, RegistroPresenca } from '../../types/database';
import { useAuth } from '../../context/AuthContext';
import { getBrasiliaDateStr, addDaysBrasilia, formatBrasiliaExtenso } from '../../utils/formatters';

const STATUS_CONFIG: Record<
  StatusPresenca,
  { label: string; bg: string; text: string; border: string; desc: string }
> = {
  PEND: {
    label: 'A Lançar',
    bg: 'bg-slate-800/80',
    text: 'text-slate-400',
    border: 'border-slate-700',
    desc: 'Pendente de confirmação',
  },
  P: {
    label: 'Presente',
    bg: 'bg-emerald-500/15',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    desc: 'No expediente',
  },
  SV: {
    label: 'Serviço',
    bg: 'bg-blue-500/15',
    text: 'text-blue-400',
    border: 'border-blue-500/40',
    desc: 'Escala de serviço',
  },
  FE: {
    label: 'Férias',
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    border: 'border-amber-500/40',
    desc: 'Em gozo de férias',
  },
  LE: {
    label: 'Licença Especial',
    bg: 'bg-purple-500/15',
    text: 'text-purple-400',
    border: 'border-purple-500/40',
    desc: 'Licença especial',
  },
  LTS: {
    label: 'Trat. Saúde (LTS)',
    bg: 'bg-red-500/15',
    text: 'text-red-400',
    border: 'border-red-500/40',
    desc: 'Baixado / Atestado',
  },
  DS: {
    label: 'Dispensa',
    bg: 'bg-slate-500/15',
    text: 'text-slate-400',
    border: 'border-slate-500/40',
    desc: 'Dispensa regulamentar',
  },
  MIS: {
    label: 'Missão',
    bg: 'bg-cyan-500/15',
    text: 'text-cyan-400',
    border: 'border-cyan-500/40',
    desc: 'Missão externa',
  },
  OUT: {
    label: 'Outro',
    bg: 'bg-slate-700/30',
    text: 'text-slate-300',
    border: 'border-slate-600',
    desc: 'Outra situação',
  },
};

// Helper: Filtra somente Praças (exclui Oficiais)
const isPraca = (postoGrad?: string) => {
  if (!postoGrad) return false;
  const p = postoGrad.toUpperCase().trim();

  // Exclui Oficiais Generais e Superiores/Intermediários/Subalternos
  if (
    p.startsWith('AE') ||
    p.startsWith('VA') ||
    p.startsWith('CA') ||
    p.startsWith('CMG') ||
    p.startsWith('CF') ||
    p.startsWith('CC') ||
    p.startsWith('CT') ||
    p.startsWith('1ºTEN') ||
    p.startsWith('1TEN') ||
    p.startsWith('2ºTEN') ||
    p.startsWith('2TEN') ||
    p.startsWith('GM') ||
    p.includes('CAPITÃO') ||
    p.includes('TENENTE') ||
    p.includes('ALMIRANTE') ||
    p.includes('CORONEL') ||
    p.includes('MAJOR')
  ) {
    return false;
  }

  // Identifica Praças (Suboficiais, Sargentos, Cabos, Marinheiros e Soldados)
  return (
    p.includes('SO') ||
    p.includes('SG') ||
    p.includes('CB') ||
    p.includes('SD') ||
    p.includes('MN') ||
    p.includes('SARGENTO') ||
    p.includes('CABO') ||
    p.includes('SOLDADO') ||
    p.includes('MARINHEIRO') ||
    p.includes('SUB')
  );
};

export const DailyAttendance: React.FC = () => {
  const { user } = useAuth();
  const [dataRef, setDataRef] = useState<string>(() => {
    return getBrasiliaDateStr();
  });
  const [registros, setRegistros] = useState<RegistroPresenca[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('todos');

  useEffect(() => {
    loadAttendanceData();
  }, [dataRef]);

  const loadAttendanceData = async () => {
    try {
      setLoading(true);
      // 1. Busca todos os militares da tabela efetivo
      const { data: efetivoReal, error: efError } = await supabase
        .from('efetivo')
        .select('*')
        .order('antiguidade_num', { ascending: true });

      // 2. Busca registros do dia na escala_diaria
      const { data: escalaReal } = await supabase
        .from('escala_diaria')
        .select('*')
        .eq('data_referencia', dataRef);

      const statusMap = new Map<number, { status: StatusPresenca; detalhe?: string }>();
      if (escalaReal && escalaReal.length > 0) {
        escalaReal.forEach((item: any) => {
          statusMap.set(item.militar_id, {
            status: (item.status as StatusPresenca) || 'PEND',
            detalhe: item.detalhe,
          });
        });
      }

      if (efetivoReal && efetivoReal.length > 0) {
        // Filtra SOMENTE Praças do Gabinete
        const pracasGabinete = efetivoReal.filter((m: any) => {
          const isP = isPraca(m.posto_grad || m.posto);
          const setor = (m.setor || '').toUpperCase();
          const isGab = setor.includes('GAB') || setor.includes('COM') || setor === '' || !m.setor;
          return isP && isGab;
        });

        const rows: RegistroPresenca[] = pracasGabinete.map((m: any) => {
          const escalaItem = statusMap.get(m.id);
          return {
            militar_id: m.id,
            nome_guerra: m.nome_guerra || 'MILITAR',
            posto_grad: m.posto_grad || m.posto || 'FN',
            setor: m.setor || 'Gabinete / CGCFN',
            data_referencia: dataRef,
            status: escalaItem ? escalaItem.status : 'PEND',
            detalhe: escalaItem ? escalaItem.detalhe : '',
          };
        });
        setRegistros(rows);
      }
    } catch (err) {
      console.warn('Erro ao carregar presença:', err);
    } finally {
      setLoading(false);
    }
  };

  // Navegação de Datas no Horário de Brasília (GMT-3)
  const handlePrevDay = () => {
    setDataRef(addDaysBrasilia(dataRef, -1));
  };

  const handleNextDay = () => {
    setDataRef(addDaysBrasilia(dataRef, 1));
  };

  const handleToday = () => {
    setDataRef(getBrasiliaDateStr());
  };

  // Alterar Status Individual
  const handleStatusChange = (militarId: number, newStatus: StatusPresenca) => {
    setRegistros((prev) =>
      prev.map((r) =>
        r.militar_id === militarId ? { ...r, status: newStatus } : r
      )
    );
  };

  // Marcar Todos como Presente
  const handleMarkAllPresent = () => {
    setRegistros((prev) => prev.map((r) => ({ ...r, status: 'P' })));
    toast.success('Todas as praças foram marcadas como PRESENTE!');
  };

  // Resetar Todos para Pendente
  const handleResetAll = () => {
    setRegistros((prev) => prev.map((r) => ({ ...r, status: 'PEND' })));
    toast.info('Status de presença resetado para pendente.');
  };

  // Salvar no Banco de Dados Supabase
  const handleSaveToSupabase = async () => {
    setSaving(true);
    try {
      const nowIso = new Date().toISOString();
      const payloadEscala = registros.map((r) => ({
        data_referencia: dataRef,
        militar_id: r.militar_id,
        nome_guerra: r.nome_guerra,
        posto_grad: r.posto_grad,
        setor: r.setor,
        status: r.status,
        detalhe: r.detalhe || null,
        atualizado_por: user?.nome_guerra || 'OPERADOR',
        atualizado_em: nowIso,
      }));

      const { error } = await supabase.from('escala_diaria').upsert(payloadEscala, {
        onConflict: 'data_referencia,militar_id',
      });

      if (error) throw error;

      // Também sincroniza com presenca_diaria para integração 100% com o bot Telegram
      try {
        const payloadPresenca = registros.map((r) => ({
          militar_id: r.militar_id,
          nome_guerra: r.nome_guerra,
          data: dataRef,
          data_referencia: dataRef,
          status: r.status,
          observacao: r.detalhe || '',
          updated_at: nowIso,
        }));
        await supabase.from('presenca_diaria').upsert(payloadPresenca);
      } catch (pErr) {
        console.warn('Sync presenca_diaria warning:', pErr);
      }

      militaryAudio.playTacticalBeep();
      toast.success('Pronto das praças salvo com sucesso no banco de dados!');
    } catch (err: any) {
      toast.error(`Erro ao salvar: ${err.message || 'Falha de conexão.'}`);
    } finally {
      setSaving(false);
    }
  };

  // Gerar e Copiar Mensagem Formatada para WhatsApp
  const generateProntoWhatsApp = () => {
    const dataFormatada = formatBrasiliaExtenso(dataRef);

    const presentes = registros.filter((r) => r.status === 'P');
    const servico = registros.filter((r) => r.status === 'SV');
    const ferias = registros.filter((r) => r.status === 'FE');
    const licenca = registros.filter((r) => ['LE', 'LTS', 'DS'].includes(r.status));
    const missao = registros.filter((r) => r.status === 'MIS');
    const outros = registros.filter((r) => r.status === 'OUT');
    const pendentes = registros.filter((r) => r.status === 'PEND');

    let msg = `⚓ *PRONTO DIÁRIO DAS PRAÇAS - GABINETE CGCFN*\n`;
    msg += `📅 *Data:* ${dataFormatada.toUpperCase()}\n`;
    msg += `📊 *Efetivo Total:* ${registros.length} Praças\n`;
    msg += `✅ *Presentes:* ${presentes.length} | 🛡️ *Serviço:* ${servico.length} | 🏖️ *Férias/Lic:* ${ferias.length + licenca.length} | ⏳ *Pendentes:* ${pendentes.length}\n`;
    msg += `------------------------------------\n\n`;

    if (presentes.length > 0) {
      msg += `🟢 *PRESENTES (${presentes.length}):*\n`;
      presentes.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (servico.length > 0) {
      msg += `🔵 *DE SERVIÇO DE ESCALA (${servico.length}):*\n`;
      servico.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (ferias.length > 0) {
      msg += `🟡 *FÉRIAS (${ferias.length}):*\n`;
      ferias.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (licenca.length > 0) {
      msg += `🟣 *LICENÇAS / LTS / DISPENSAS (${licenca.length}):*\n`;
      licenca.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra} (${STATUS_CONFIG[r.status].label})\n`;
      });
      msg += `\n`;
    }

    if (missao.length > 0) {
      msg += `🔷 *EM MISSÃO (${missao.length}):*\n`;
      missao.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (outros.length > 0) {
      msg += `⚪ *OUTRAS SITUAÇÕES (${outros.length}):*\n`;
      outros.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (pendentes.length > 0) {
      msg += `⚠️ *A CONFIRMAR / PENDENTES (${pendentes.length}):*\n`;
      pendentes.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    msg += `------------------------------------\n`;
    msg += `*Status:* ${pendentes.length === 0 ? '✅ 100% CONSOLIDADO' : `⚠️ ${pendentes.length} PENDÊNCIA(S)`}\n`;
    msg += `*Gerado via SisGAB 2.0 por:* ${user?.nome_guerra || 'Operador'}\n`;
    msg += `*AD SUMUS!* 🇧🇷`;

    navigator.clipboard.writeText(msg);
    toast.success('Pronto copiado para a Área de Transferência!', {
      description: 'Cole diretamente no WhatsApp da Guarnição do Gabinete.',
    });
  };

  const total = registros.length;
  const countPresentes = registros.filter((r) => r.status === 'P').length;
  const countServico = registros.filter((r) => r.status === 'SV').length;
  const countFeriasLicencas = registros.filter((r) => ['FE', 'LE', 'LTS', 'DS', 'MIS', 'OUT'].includes(r.status)).length;
  const countPendentes = registros.filter((r) => r.status === 'PEND').length;

  const filteredRegistros = registros.filter((r) => {
    if (filterStatus === 'todos') return true;
    if (filterStatus === 'pendentes') return r.status === 'PEND';
    if (filterStatus === 'presentes') return r.status === 'P';
    if (filterStatus === 'servico') return r.status === 'SV';
    if (filterStatus === 'ausentes') return ['FE', 'LE', 'LTS', 'DS', 'MIS', 'OUT'].includes(r.status);
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header & Ações Principais */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
              Gabinete & Pessoal
            </span>
            <span className="text-slate-400 text-xs">• Chamada Diária do Efetivo de Praças</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1 flex items-center gap-2.5">
            <Users className="w-7 h-7 text-[#c5a059]" />
            <span>Presença & Pronto das Praças</span>
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            Controle exclusivo da guarnição de Suboficiais, Sargentos, Cabos e Marinheiros do Gabinete do CGCFN.
          </p>
        </div>

        {/* Botões de Ação */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={handleMarkAllPresent}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-bold transition-all"
            title="Marcar todas as praças como Presente"
          >
            <CheckSquare className="w-3.5 h-3.5" />
            <span>Todos Presentes</span>
          </button>

          <button
            type="button"
            onClick={handleResetAll}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-all"
            title="Resetar para Não Lançado"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Resetar</span>
          </button>

          <button
            onClick={generateProntoWhatsApp}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs shadow-lg shadow-emerald-600/25 transition-all active:scale-95"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>Copiar p/ WhatsApp</span>
          </button>

          <button
            onClick={handleSaveToSupabase}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all active:scale-95 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Gravando...' : 'Salvar Pronto'}</span>
          </button>
        </div>
      </div>

      {/* ── BARRA DE SELEÇÃO DE DATA COM SETAS E CALENDÁRIO ── */}
      <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={handlePrevDay}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Dia Anterior"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2 flex-1 sm:flex-none">
            <div className="relative flex-1">
              <input
                type="date"
                value={dataRef}
                onChange={(e) => setDataRef(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 px-3 py-1.5 rounded-xl text-xs font-black text-white focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <button
              type="button"
              onClick={handleToday}
              className="px-3 py-1.5 rounded-xl bg-[#c5a059]/20 hover:bg-[#c5a059]/30 text-[#e5c07b] border border-[#c5a059]/40 text-xs font-black transition-colors"
            >
              Hoje
            </button>
          </div>

          <button
            type="button"
            onClick={handleNextDay}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title="Próximo Dia"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Status de Consolidação Tática */}
        <div className="flex items-center gap-2 text-xs font-bold">
          {countPendentes === 0 ? (
            <span className="px-3 py-1 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Pronto 100% Consolidado ({countPresentes} presentes)</span>
            </span>
          ) : (
            <span className="px-3 py-1 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 flex items-center gap-1.5 animate-pulse">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>{countPendentes} Praça(s) com presença a lançar</span>
            </span>
          )}
        </div>
      </div>

      {/* Cards de Métricas & KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-bold">Efetivo de Praças</span>
            <Users className="w-4 h-4 text-[#c5a059]" />
          </div>
          <p className="text-2xl font-black text-white mt-1">{total}</p>
          <span className="text-[10px] text-slate-500">Gabinete / CGCFN</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0b1222] border border-emerald-500/20 bg-emerald-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-emerald-400 font-bold">Presentes</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-black text-emerald-400 mt-1">{countPresentes}</p>
          <span className="text-[10px] text-emerald-500/80">No expediente</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0b1222] border border-blue-500/20 bg-blue-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-blue-400 font-bold">Serviço de Escala</span>
            <Shield className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-2xl font-black text-blue-400 mt-1">{countServico}</p>
          <span className="text-[10px] text-blue-500/80">Plantão 24h</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0b1222] border border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-amber-400 font-bold">Férias / Licenças</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-black text-amber-400 mt-1">{countFeriasLicencas}</p>
          <span className="text-[10px] text-amber-500/80">FE, LTS, LE ou Dispensa</span>
        </div>
      </div>

      {/* Tabela do Efetivo de Praças com Marcação Rápida */}
      <div className="rounded-3xl bg-[#0b1222] border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#c5a059]" />
              <span>Praças do Gabinete ({filteredRegistros.length} Militares)</span>
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Clique nos botões de status para alterar instantaneamente a situação militar.
            </p>
          </div>

          <div className="flex items-center gap-1 overflow-x-auto">
            {[
              { id: 'todos', label: 'Todos' },
              { id: 'pendentes', label: 'A Lançar' },
              { id: 'presentes', label: 'Presentes' },
              { id: 'servico', label: 'Serviço' },
              { id: 'ausentes', label: 'Férias/Lic' },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilterStatus(tab.id)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all shrink-0 ${
                  filterStatus === tab.id
                    ? 'bg-[#c5a059] text-slate-950 shadow-sm'
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-slate-800/80">
          {filteredRegistros.length > 0 ? (
            filteredRegistros.map((militar) => {
              const currentConfig = STATUS_CONFIG[militar.status] || STATUS_CONFIG.PEND;

              return (
                <div
                  key={militar.militar_id}
                  className="p-3.5 sm:px-5 sm:py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors"
                >
                  {/* Dados do Militar */}
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center font-black text-[#c5a059] text-xs shrink-0 shadow-inner">
                      {militar.nome_guerra.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-black text-white">{militar.nome_guerra}</span>
                        <span className="text-[11px] text-amber-300/90 font-bold">
                          ({militar.posto_grad})
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${currentConfig.bg} ${currentConfig.text} border ${currentConfig.border}`}>
                          {currentConfig.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">{militar.setor}</p>
                    </div>
                  </div>

                  {/* Seletor de Status em 1 Clique */}
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
                    {(Object.keys(STATUS_CONFIG) as StatusPresenca[]).map((st) => {
                      const cfg = STATUS_CONFIG[st];
                      const isSelected = militar.status === st;

                      return (
                        <button
                          key={st}
                          type="button"
                          onClick={() => handleStatusChange(militar.militar_id, st)}
                          title={`${cfg.label} - ${cfg.desc}`}
                          className={`px-2.5 py-1 rounded-lg text-xs font-black transition-all ${
                            isSelected
                              ? `${cfg.bg} ${cfg.text} ${cfg.border} border shadow-md scale-105 ring-1 ring-white/20`
                              : 'bg-slate-950/80 text-slate-400 hover:text-slate-200 border border-slate-800'
                          }`}
                        >
                          {st}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              Nenhuma praça encontrada para o filtro selecionado.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
