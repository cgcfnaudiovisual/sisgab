import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
import {
  Cake,
  Calendar,
  Download,
  Share2,
  Sparkles,
  Search,
  CheckCircle2,
  Award,
  X,
  Plus,
  Edit2,
  Flag,
  User,
  Clock,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';

interface Aniversariante {
  id: number;
  nome_guerra: string;
  posto_grad: string;
  setor: string;
  dia: number;
  mes: number;
  data_nascimento?: string;
  telefone?: string;
  email?: string;
}

interface DataComemorativa {
  id: number;
  dia: string | number;
  mes: string | number;
  titulo: string;
}

const MESES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
];

export const Birthdays: React.FC = () => {
  const [aniversariantes, setAniversariantes] = useState<Aniversariante[]>([]);
  const [datasComemorativas, setDatasComemorativas] = useState<DataComemorativa[]>([]);
  const [selectedMes, setSelectedMes] = useState<number>(new Date().getMonth() + 1);
  const [selectedMilitar, setSelectedMilitar] = useState<Aniversariante | null>(null);
  const [generatedCardUrl, setGeneratedCardUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Modal para atualizar / cadastrar data de nascimento
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingMilitar, setEditingMilitar] = useState<{ id: number; nome_guerra: string; data_nascimento: string } | null>(null);

  useEffect(() => {
    loadRealData();
  }, []);

  const loadRealData = async () => {
    try {
      setLoading(true);

      // 1. Carrega efetivo com suas datas de nascimento reais
      const { data: efData, error: efErr } = await supabase
        .from('efetivo')
        .select('id, nome_guerra, posto_grad, posto, setor, data_nascimento, telefone, email')
        .order('antiguidade_num', { ascending: true });

      if (!efErr && efData) {
        const parsed: Aniversariante[] = [];
        efData.forEach((m: any) => {
          if (m.data_nascimento) {
            const raw = String(m.data_nascimento).trim().split('T')[0];
            let dia = 0;
            let mes = 0;

            if (raw.includes('-')) {
              const parts = raw.split('-');
              if (parts.length >= 3) {
                mes = parseInt(parts[1], 10);
                dia = parseInt(parts[2], 10);
              }
            } else if (raw.includes('/')) {
              const parts = raw.split('/');
              if (parts.length >= 2) {
                dia = parseInt(parts[0], 10);
                mes = parseInt(parts[1], 10);
              }
            }

            if (dia > 0 && mes >= 1 && mes <= 12) {
              parsed.push({
                id: m.id,
                nome_guerra: (m.nome_guerra || 'MILITAR').toUpperCase(),
                posto_grad: m.posto_grad || m.posto || 'FN',
                setor: m.setor || 'Gabinete CGCFN',
                dia,
                mes,
                data_nascimento: m.data_nascimento,
                telefone: m.telefone,
                email: m.email,
              });
            }
          }
        });
        setAniversariantes(parsed);
      }

      // 2. Carrega datas comemorativas oficiais do banco
      const { data: dcData } = await supabase
        .from('datas_comemorativas')
        .select('*');

      if (dcData && dcData.length > 0) {
        setDatasComemorativas(dcData);
      } else {
        // Fallback das 8 datas magnas institucionais
        setDatasComemorativas([
          { id: 1, dia: '08', mes: '01', titulo: 'Dia do Fotógrafo (COMSOC)' },
          { id: 2, dia: '07', mes: '03', titulo: 'Aniversário do Corpo de Fuzileiros Navais (CFN)' },
          { id: 3, dia: '11', mes: '06', titulo: 'Batalha Naval do Riachuelo (Data Magna da MB)' },
          { id: 4, dia: '21', mes: '07', titulo: 'Dia da Comunicação Social da Marinha' },
          { id: 5, dia: '23', mes: '10', titulo: 'Dia do Aviador / Força Aérea' },
          { id: 6, dia: '19', mes: '11', titulo: 'Dia da Bandeira Nacional' },
          { id: 7, dia: '13', mes: '12', titulo: 'Dia do Marinheiro (Patrono Tamandaré)' },
          { id: 8, dia: '28', mes: '12', titulo: 'Dia do Guarda-Marinha' },
        ]);
      }
    } catch (err) {
      console.warn('Erro ao carregar aniversariantes:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBirthday = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMilitar || !editingMilitar.data_nascimento) return;

    try {
      const { error } = await supabase
        .from('efetivo')
        .update({ data_nascimento: editingMilitar.data_nascimento })
        .eq('id', editingMilitar.id);

      if (!error) {
        toast.success(`Data de nascimento atualizada para ${editingMilitar.nome_guerra}!`);
        setEditModalOpen(false);
        loadRealData();
      } else {
        toast.error('Erro ao atualizar no banco de dados.');
      }
    } catch (err) {
      toast.error('Erro de conexão ao salvar data.');
    }
  };

  // Gerador de Cartão Comemorativo Oficial com Brasão do CGCFN
  const generateCard = (militar: Aniversariante) => {
    setSelectedMilitar(militar);
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 1000;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Fundo
    const grad = ctx.createLinearGradient(0, 0, 0, 1000);
    grad.addColorStop(0, '#060a12');
    grad.addColorStop(0.5, '#0c172e');
    grad.addColorStop(1, '#060a12');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 800, 1000);

    // Moldura Dupla Dourada Oficial
    ctx.strokeStyle = '#c5a059';
    ctx.lineWidth = 4;
    ctx.strokeRect(30, 30, 740, 940);
    ctx.lineWidth = 1;
    ctx.strokeRect(40, 40, 720, 920);

    // Cabeçalho Oficial
    ctx.fillStyle = '#c5a059';
    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('⚓ MARINHA DO BRASIL ⚓', 400, 120);

    ctx.font = 'bold 15px sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS', 400, 155);
    ctx.fillText('GABINETE DO COMANDO-GERAL', 400, 180);

    // Linha Divisória
    ctx.strokeStyle = 'rgba(197, 160, 89, 0.4)';
    ctx.beginPath();
    ctx.moveTo(150, 210);
    ctx.lineTo(650, 210);
    ctx.stroke();

    // Ícone Bolo
    ctx.font = '72px sans-serif';
    ctx.fillText('🎂', 400, 330);

    // Título
    ctx.font = 'bold 28px sans-serif';
    ctx.fillStyle = '#e5c07b';
    ctx.fillText('FELIZ ANIVERSÁRIO!', 400, 400);

    // Posto e Nome
    ctx.font = 'bold 24px sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(militar.posto_grad, 400, 470);

    ctx.font = 'bold 38px sans-serif';
    ctx.fillStyle = '#c5a059';
    ctx.fillText(militar.nome_guerra, 400, 525);

    // Data
    ctx.font = 'bold 18px sans-serif';
    ctx.fillStyle = '#00e5ff';
    ctx.fillText(`${String(militar.dia).padStart(2, '0')} de ${MESES[militar.mes - 1]}`, 400, 580);

    // Mensagem Institucional
    ctx.font = 'italic 16px sans-serif';
    ctx.fillStyle = '#cbd5e1';
    ctx.fillText('O Gabinete do Comando-Geral parabeniza o nobre combatente anfíbio', 400, 660);
    ctx.fillText('por mais um ano de vida, desejando saúde, felicidades e continuados', 400, 695);
    ctx.fillText('sucessos em sua honrosa carreira naval.', 400, 730);

    // Lema
    ctx.font = 'bold 24px sans-serif';
    ctx.fillStyle = '#c5a059';
    ctx.fillText('AD SUMUS!', 400, 840);

    const url = canvas.toDataURL('image/png');
    setGeneratedCardUrl(url);

    militaryAudio.playTacticalBeep();
  };

  const handleSendWhatsApp = (militar: Aniversariante) => {
    const msg = `Prezado(a) *${militar.posto_grad} ${militar.nome_guerra}*,\n\nO Gabinete do Comando-Geral do Corpo de Fuzileiros Navais parabeniza-o(a) pela passagem do seu aniversário em *${String(militar.dia).padStart(2, '0')} de ${MESES[militar.mes - 1]}*!\n\nDesejamos muitas felicidades, saúde e continuados sucessos na sua brilhante carreira naval.\n\n_Comunicação Social • Gabinete CGCFN_\n*AD SUMUS!*`;
    const cleanPhone = (militar.telefone || '').replace(/\D/g, '');
    const url = cleanPhone
      ? `https://api.whatsapp.com/send?phone=55${cleanPhone}&text=${encodeURIComponent(msg)}`
      : `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank');
  };

  // Filtragem
  const aniversariantesDoMes = aniversariantes
    .filter((a) => a.mes === selectedMes)
    .filter((a) => (searchQuery ? a.nome_guerra.toLowerCase().includes(searchQuery.toLowerCase()) : true))
    .sort((a, b) => a.dia - b.dia);

  const datasDoMes = datasComemorativas
    .filter((d) => parseInt(String(d.mes), 10) === selectedMes)
    .sort((a, b) => parseInt(String(a.dia), 10) - parseInt(String(b.dia), 10));

  return (
    <div className="space-y-6">
      {/* ── Topo & Cabeçalho ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-pink-500/20 text-pink-300 text-xs font-bold uppercase tracking-wider border border-pink-500/40">
              Cerimonial & Tradição
            </span>
            <span className="text-slate-400 text-xs">• Aniversariantes & Datas Magnas</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Aniversariantes da Tripulação & Calendário Histórico
          </h1>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Buscar militar por nome de guerra..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
          />
        </div>
      </div>

      {/* ── Seletor dos 12 Meses com Contadores Reais ── */}
      <div className="p-3 rounded-2xl bg-[#0b1222] border border-slate-800 overflow-x-auto">
        <div className="flex items-center gap-2 min-w-max">
          {MESES.map((mesNome, idx) => {
            const numMes = idx + 1;
            const count = aniversariantes.filter((a) => a.mes === numMes).length;
            const isSelected = selectedMes === numMes;

            return (
              <button
                key={numMes}
                onClick={() => setSelectedMes(numMes)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                  isSelected
                    ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/25 scale-105'
                    : 'bg-slate-900/90 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                <span>{mesNome}</span>
                <span
                  className={`px-1.5 py-0.5 rounded-full text-[10px] font-black ${
                    isSelected ? 'bg-slate-950 text-[#c5a059]' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Conteúdo Principal do Mês Selecionado ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna 1 & 2: Aniversariantes Reais do Mês */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
              <Cake className="w-4 h-4 text-[#c5a059]" />
              <span>Aniversariantes de {MESES[selectedMes - 1]} ({aniversariantesDoMes.length} Militares)</span>
            </h2>
          </div>

          {aniversariantesDoMes.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {aniversariantesDoMes.map((m) => (
                <div
                  key={m.id}
                  className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/50 transition-all space-y-3 shadow-lg"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="w-8 h-8 rounded-xl bg-[#c5a059]/20 border border-[#c5a059]/40 flex items-center justify-center font-black text-xs text-[#e5c07b]">
                          {String(m.dia).padStart(2, '0')}
                        </span>
                        <div>
                          <h3 className="text-xs font-black text-white">{m.nome_guerra}</h3>
                          <p className="text-[11px] text-[#00e5ff] font-semibold">{m.posto_grad}</p>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-400 pl-10">{m.setor}</p>
                    </div>

                    <button
                      onClick={() => {
                        setEditingMilitar({ id: m.id, nome_guerra: m.nome_guerra, data_nascimento: m.data_nascimento || '' });
                        setEditModalOpen(true);
                      }}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800"
                      title="Editar data de nascimento"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                    <button
                      onClick={() => generateCard(m)}
                      className="flex-1 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[#e5c07b] font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Gerar Cartão</span>
                    </button>

                    <button
                      onClick={() => handleSendWhatsApp(m)}
                      className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-[11px] flex items-center gap-1 transition-all"
                      title="Enviar Parabéns no WhatsApp"
                    >
                      <Share2 className="w-3.5 h-3.5" />
                      <span>WhatsApp</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 rounded-2xl bg-[#0b1222] border border-slate-800 text-center space-y-2">
              <p className="text-xs text-slate-400">
                Nenhum militar cadastrado como aniversariante em {MESES[selectedMes - 1]}.
              </p>
            </div>
          )}
        </div>

        {/* Coluna 3: Datas Comemorativas do Mês & Datas Magnas */}
        <div className="space-y-4">
          <h2 className="text-sm font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
            <Flag className="w-4 h-4" />
            <span>Datas Magnas do Mês ({datasDoMes.length})</span>
          </h2>

          <div className="p-4 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/30 space-y-3 shadow-xl">
            {datasDoMes.length > 0 ? (
              <div className="space-y-2.5">
                {datasDoMes.map((dc) => (
                  <div
                    key={dc.id}
                    className="p-3 rounded-2xl bg-slate-900 border border-slate-800 flex items-start gap-3"
                  >
                    <span className="px-2 py-1 rounded-lg bg-[#00e5ff]/20 text-[#00e5ff] font-black text-xs shrink-0 border border-[#00e5ff]/30">
                      {String(dc.dia).padStart(2, '0')}/{String(dc.mes).padStart(2, '0')}
                    </span>
                    <div>
                      <h4 className="text-xs font-bold text-white">{dc.titulo}</h4>
                      <span className="text-[10px] text-slate-400 font-medium">Tradição Naval • MB / CFN</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-4">
                Sem datas comemorativas registradas para {MESES[selectedMes - 1]}.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* ── Modal de Visualização / Download do Cartão Oficial ── */}
      {selectedMilitar && generatedCardUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full p-5 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/50 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-black text-[#e5c07b] uppercase">
                Cartão Oficial • {selectedMilitar.nome_guerra}
              </h3>
              <button
                onClick={() => {
                  setSelectedMilitar(null);
                  setGeneratedCardUrl(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-xl">
              <img src={generatedCardUrl} alt="Cartão de Aniversário" className="w-full h-auto" />
            </div>

            <div className="flex items-center justify-between gap-2">
              <button
                onClick={() => handleSendWhatsApp(selectedMilitar)}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs flex items-center justify-center gap-1.5"
              >
                <Share2 className="w-4 h-4" />
                <span>Enviar pelo WhatsApp</span>
              </button>

              <a
                href={generatedCardUrl}
                download={`Aniversario_${selectedMilitar.nome_guerra}.png`}
                className="px-4 py-2.5 rounded-xl bg-[#c5a059] text-slate-950 font-black text-xs flex items-center gap-1.5"
              >
                <Download className="w-4 h-4" />
                <span>Baixar PNG</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Editar / Cadastrar Data de Nascimento ── */}
      {editModalOpen && editingMilitar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-sm w-full p-6 rounded-3xl bg-[#0b1222] border-2 border-slate-700 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-black text-white uppercase">
                Atualizar Data de Nascimento
              </h3>
              <button onClick={() => setEditModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveBirthday} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-bold mb-1">Militar:</label>
                <p className="font-bold text-white text-sm">{editingMilitar.nome_guerra}</p>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Data de Nascimento (AAAA-MM-DD):</label>
                <input
                  type="date"
                  required
                  value={editingMilitar.data_nascimento}
                  onChange={(e) => setEditingMilitar({ ...editingMilitar, data_nascimento: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white font-bold focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#c5a059] text-slate-950 font-black text-xs"
                >
                  Salvar Data
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
