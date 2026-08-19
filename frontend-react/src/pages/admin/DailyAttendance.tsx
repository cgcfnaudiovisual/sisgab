import React, { useState, useEffect } from 'react';
import {
  Calendar,
  CheckCircle2,
  Copy,
  Printer,
  Users,
  Shield,
  Clock,
  Sparkles,
  Save,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { StatusPresenca, RegistroPresenca } from '../../types/database';
import { useAuth } from '../../context/AuthContext';

const STATUS_CONFIG: Record<
  StatusPresenca,
  { label: string; bg: string; text: string; border: string }
> = {
  P: { label: 'Presente', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/40' },
  SV: { label: 'Serviço', bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/40' },
  FE: { label: 'Férias', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/40' },
  LE: { label: 'Licença Especial', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/40' },
  LTS: { label: 'Trat. Saúde (LTS)', bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/40' },
  DS: { label: 'Dispensa', bg: 'bg-slate-500/15', text: 'text-slate-400', border: 'border-slate-500/40' },
  MIS: { label: 'Missão', bg: 'bg-cyan-500/15', text: 'text-cyan-400', border: 'border-cyan-500/40' },
  OUT: { label: 'Outro', bg: 'bg-slate-700/30', text: 'text-slate-300', border: 'border-slate-600' },
};

export const DailyAttendance: React.FC = () => {
  const { user } = useAuth();
  const [dataRef, setDataRef] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [registros, setRegistros] = useState<RegistroPresenca[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadAttendanceData();
  }, [dataRef]);

  const loadAttendanceData = async () => {
    try {
      setLoading(true);
      // 1. Busca todos os militares reais da tabela efetivo
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
            status: (item.status as StatusPresenca) || 'P',
            detalhe: item.detalhe,
          });
        });
      }

      if (efetivoReal && efetivoReal.length > 0) {
        const rows: RegistroPresenca[] = efetivoReal.map((m: any) => {
          const escalaItem = statusMap.get(m.id);
          return {
            militar_id: m.id,
            nome_guerra: m.nome_guerra || 'MILITAR',
            posto_grad: m.posto_grad || m.posto || 'FN',
            setor: m.setor || 'Gabinete / CGCFN',
            data_referencia: dataRef,
            status: escalaItem ? escalaItem.status : 'P',
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

  const handleStatusChange = (militarId: number, newStatus: StatusPresenca) => {
    setRegistros((prev) =>
      prev.map((r) =>
        r.militar_id === militarId ? { ...r, status: newStatus } : r
      )
    );
  };

  const handleSaveToSupabase = async () => {
    setSaving(true);
    try {
      const payload = registros.map((r) => ({
        data_referencia: dataRef,
        militar_id: r.militar_id,
        nome_guerra: r.nome_guerra,
        posto_grad: r.posto_grad,
        setor: r.setor,
        status: r.status,
        detalhe: r.detalhe || null,
        atualizado_por: user?.nome_guerra || 'OPERADOR',
        atualizado_em: new Date().toISOString(),
      }));

      const { error } = await supabase.from('escala_diaria').upsert(payload, {
        onConflict: 'data_referencia,militar_id',
      });

      if (error) throw error;
      toast.success('Pronto diário salvo com sucesso no banco de dados!');
    } catch (err: any) {
      toast.error(`Erro ao salvar: ${err.message || 'Falha de conexão.'}`);
    } finally {
      setSaving(false);
    }
  };

  const generateProntoWhatsApp = () => {
    const dataFormatada = new Date(dataRef + 'T00:00:00').toLocaleDateString('pt-BR', {
      weekday: 'long',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });

    const presentes = registros.filter((r) => r.status === 'P');
    const servico = registros.filter((r) => r.status === 'SV');
    const ferias = registros.filter((r) => r.status === 'FE');
    const lts = registros.filter((r) => r.status === 'LTS');
    const outros = registros.filter((r) => !['P', 'SV', 'FE', 'LTS'].includes(r.status));

    let msg = `⚓ *PRONTO DA TRIPULAÇÃO - GABINETE DO CGCFN*\n`;
    msg += `📅 *Data:* ${dataFormatada.toUpperCase()}\n`;
    msg += `📊 *Efetivo Total:* ${registros.length} militares\n`;
    msg += `------------------------------------\n\n`;

    msg += `🟢 *PRESENTES (${presentes.length}):*\n`;
    if (presentes.length > 0) {
      presentes.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
    } else {
      msg += `• Nenhum\n`;
    }
    msg += `\n`;

    if (servico.length > 0) {
      msg += `🔵 *DE SERVIÇO (${servico.length}):*\n`;
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

    if (lts.length > 0) {
      msg += `🔴 *TRATAMENTO DE SAÚDE - LTS (${lts.length}):*\n`;
      lts.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra}\n`;
      });
      msg += `\n`;
    }

    if (outros.length > 0) {
      msg += `⚪ *OUTRAS SITUAÇÕES (${outros.length}):*\n`;
      outros.forEach((r) => {
        msg += `• ${r.posto_grad} ${r.nome_guerra} (${STATUS_CONFIG[r.status].label})\n`;
      });
      msg += `\n`;
    }

    msg += `------------------------------------\n`;
    msg += `*Gerado via SisGAB 2.0 por:* ${user?.nome_guerra || 'Operador'}\n`;
    msg += `*AD SUMUS!* 🇧🇷`;

    navigator.clipboard.writeText(msg);
    toast.success('Pronto copiado para a Área de Transferência!', {
      description: 'Cole diretamente no WhatsApp ou Telegram do Chefe de Gabinete.',
    });
  };

  const total = registros.length;
  const countPresentes = registros.filter((r) => r.status === 'P').length;
  const countServico = registros.filter((r) => r.status === 'SV').length;
  const countAusentes = total - countPresentes - countServico;

  return (
    <div className="space-y-6">
      {/* Header & Ações Principais */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Gabinete & Pessoal
            </span>
            <span className="text-slate-400 text-xs">• Chamada Diária do Efetivo</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Presença & Pronto da Tripulação
          </h1>
        </div>

        {/* Botões de Ação */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={generateProntoWhatsApp}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20 transition-all active:scale-95"
          >
            <Copy className="w-3.5 h-3.5" />
            <span>Copiar para WhatsApp</span>
          </button>

          <button
            onClick={handleSaveToSupabase}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold text-xs shadow-md shadow-[#c5a059]/20 transition-all active:scale-95 disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? 'Salvando...' : 'Salvar Pronto'}</span>
          </button>
        </div>
      </div>

      {/* Cards de Métricas & Seletor de Data */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-[#0b1222] border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Data de Referência</span>
            <Calendar className="w-4 h-4 text-[#c5a059]" />
          </div>
          <input
            type="date"
            value={dataRef}
            onChange={(e) => setDataRef(e.target.value)}
            className="mt-2 bg-slate-900 border border-slate-700 px-2.5 py-1 rounded-lg text-xs font-bold text-white focus:outline-none focus:border-[#c5a059]"
          />
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-emerald-500/20 bg-emerald-500/5">
          <p className="text-xs text-emerald-400 font-semibold">Presentes</p>
          <p className="text-2xl font-black text-emerald-400 mt-1">{countPresentes}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-blue-500/20 bg-blue-500/5">
          <p className="text-xs text-blue-400 font-semibold">Serviço de Escala</p>
          <p className="text-2xl font-black text-blue-400 mt-1">{countServico}</p>
        </div>

        <div className="p-4 rounded-xl bg-[#0b1222] border border-amber-500/20 bg-amber-500/5">
          <p className="text-xs text-amber-400 font-semibold">Férias / LTS / Licença</p>
          <p className="text-2xl font-black text-amber-400 mt-1">{countAusentes}</p>
        </div>
      </div>

      {/* Tabela do Efetivo com Marcação Rápida em 1 Clique */}
      <div className="rounded-2xl bg-[#0b1222] border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Tripulação Cadastrada ({registros.length} militares)
          </h2>
          <span className="text-[11px] text-slate-400 font-medium">
            Clique no botão de status para alternar em 0ms
          </span>
        </div>

        <div className="divide-y divide-slate-800/80">
          {registros.map((militar) => {
            const currentConfig = STATUS_CONFIG[militar.status] || STATUS_CONFIG.P;

            return (
              <div
                key={militar.militar_id}
                className="p-3.5 sm:px-5 sm:py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors"
              >
                {/* Dados do Militar */}
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-[#c5a059] text-xs">
                    {militar.nome_guerra.slice(0, 2)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black text-white">{militar.nome_guerra}</span>
                      <span className="text-[11px] text-slate-400 font-medium">
                        ({militar.posto_grad})
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
                        onClick={() => handleStatusChange(militar.militar_id, st)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                          isSelected
                            ? `${cfg.bg} ${cfg.text} ${cfg.border} border shadow-xs scale-105`
                            : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/60'
                        }`}
                      >
                        {st}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
