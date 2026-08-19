import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { CheckCircle2, XCircle, Calendar, Clock, MapPin, Sparkles, User, Shield } from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';

export const RSVPGuestView: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [status, setStatus] = useState<'confirmado' | 'recusado' | 'pendente'>('pendente');
  const [acompanhante, setAcompanhante] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [finalized, setFinalized] = useState(false);

  const handleConfirm = (confirmed: boolean) => {
    setSubmitting(true);
    setTimeout(() => {
      setStatus(confirmed ? 'confirmado' : 'recusado');
      setFinalized(true);
      setSubmitting(false);

      if (confirmed) {
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
        });
      }
      toast.success(confirmed ? 'Presença confirmada com sucesso!' : 'Presença recusada com sucesso.');
    }, 600);
  };

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-100 flex items-center justify-center p-4 selection:bg-[#c5a059]/30 selection:text-[#e5c07b]">
      <div className="w-full max-w-lg rounded-3xl bg-gradient-to-b from-[#0e172a] to-[#080d1a] border-2 border-[#c5a059]/40 p-6 sm:p-8 space-y-6 shadow-2xl shadow-black/90 relative overflow-hidden">
        {/* Decorative Top Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-1 bg-[#c5a059] shadow-lg shadow-[#c5a059]"></div>

        {/* Brasão Oficial CGCFN */}
        <div className="text-center space-y-2">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-[#c5a059]/10 border border-[#c5a059] flex items-center justify-center text-3xl shadow-lg shadow-[#c5a059]/20">
            ⚓
          </div>
          <div>
            <span className="text-[11px] font-black text-[#c5a059] tracking-widest uppercase">
              MARINHA DO BRASIL
            </span>
            <h1 className="text-lg font-black text-white uppercase tracking-tight">
              COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS
            </h1>
            <p className="text-xs text-slate-400 mt-1">Convite Formal & Confirmação de Presença</p>
          </div>
        </div>

        {/* Detalhes do Evento */}
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <h2 className="text-sm font-black text-[#e5c07b] text-center">
            Cerimônia de Passagem de Comando do CGCFN
          </h2>

          <div className="space-y-1.5 text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <Calendar className="w-3.5 h-3.5 text-[#c5a059]" />
              <span>Data: <strong>20 de Agosto de 2026</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-[#00e5ff]" />
              <span>Horário: <strong>10:00h</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-emerald-400" />
              <span>Local: <strong>Fortaleza de São José, Ilha das Cobras - RJ</strong></span>
            </div>
          </div>
        </div>

        {/* Ações de Confirmação */}
        {!finalized ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Nome do(a) Acompanhante (se houver):
              </label>
              <input
                type="text"
                value={acompanhante}
                onChange={(e) => setAcompanhante(e.target.value)}
                placeholder="Nome completo do acompanhante"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Observações / Restrições Alimentares:
              </label>
              <textarea
                rows={2}
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Alguma necessidade especial ou restrição?"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                type="button"
                disabled={submitting}
                onClick={() => handleConfirm(false)}
                className="py-3 px-4 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 font-bold text-xs flex items-center justify-center gap-2 transition-all"
              >
                <XCircle className="w-4 h-4" />
                <span>Não Poderei Comparecer</span>
              </button>

              <button
                type="button"
                disabled={submitting}
                onClick={() => handleConfirm(true)}
                className="py-3 px-4 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center justify-center gap-2 shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Confirmar Presença</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6 rounded-2xl bg-slate-900/90 border border-[#c5a059]/40 text-center space-y-3 animate-in zoom-in-95 duration-200">
            <div
              className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center text-xl ${
                status === 'confirmado'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500'
                  : 'bg-red-500/20 text-red-400 border border-red-500'
              }`}
            >
              {status === 'confirmado' ? '✅' : '❌'}
            </div>

            <h3 className="text-base font-black text-white">
              {status === 'confirmado'
                ? 'Presença Confirmada com Sucesso!'
                : 'Justificativa Registrada!'}
            </h3>

            <p className="text-xs text-slate-400 leading-relaxed">
              {status === 'confirmado'
                ? 'Seu assento e credencial foram reservados pelo Cerimonial do Gabinete do CGCFN. Aguardamos sua distinta presença!'
                : 'Agradecemos pelo aviso prévio ao Cerimonial.'}
            </p>

            <span className="text-[10px] text-slate-500 block">Token: {token || 'MB-VALID'}</span>
          </div>
        )}
      </div>
    </div>
  );
};
