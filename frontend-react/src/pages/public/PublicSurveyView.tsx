import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Star,
  Send,
  CheckCircle2,
  Heart,
  MessageSquare,
  Award,
  Sparkles,
  Shield,
  ThumbsUp,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import defaultBrasao from '../../assets/brasaocgcfn.png';

export const PublicSurveyView: React.FC = () => {
  const { token, id } = useParams<{ token?: string; id?: string }>();

  const [eventName, setEventName] = useState('ENCONTRO DE VETERANOS (OFICIAIS SUPERIORES)');
  const [eventDate, setEventDate] = useState('14 de Agosto de 2026');

  React.useEffect(() => {
    if (id) {
      const loadEvent = async () => {
        try {
          const { data } = await supabase.from('demandas_comunicacao').select('*').eq('id', id).single();
          if (data) {
            setEventName(data.titulo_evento || 'Evento Oficial');
            if (data.data_evento) {
              const [y, m, d] = data.data_evento.split('-');
              const dateObj = new Date(parseInt(y), parseInt(m) - 1, parseInt(d));
              setEventDate(dateObj.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }));
            }
          }
        } catch {
          // Mantem padrão
        }
      };
      loadEvent();
    }
  }, [id]);

  // Notas de 1 a 5 estrelas
  const [ratings, setRatings] = useState({
    recepcao: 5,
    cerimonial: 5,
    coquetel: 5,
    audiovisual: 5,
    geral: 5,
  });

  const [comentarios, setComentarios] = useState('');
  const [sugestoes, setSugestoes] = useState('');
  const [autoridadeNome, setAutoridadeNome] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const setRatingValue = (key: keyof typeof ratings, val: number) => {
    setRatings((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    setTimeout(() => {
      setLoading(false);
      setSubmitted(true);
      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.6 },
      });
      toast.success('Pesquisa de satisfação enviada com sucesso! Obrigado pela sua contribuição.');
    }, 400);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#040810] text-slate-100 p-4 sm:p-8 flex items-center justify-center selection:bg-[#c5a059]/30">
        <div className="max-w-md w-full p-8 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/40 text-center space-y-4 shadow-2xl animate-in zoom-in-95">
          <img
            src={localStorage.getItem('sisgab_custom_logo') || defaultBrasao}
            alt="Brasão Oficial CGCFN"
            onError={(e) => {
              const target = e.currentTarget as HTMLImageElement;
              target.onerror = null;
              target.src = defaultBrasao;
            }}
            className="w-20 h-20 mx-auto object-contain drop-shadow-[0_0_12px_rgba(197,160,89,0.8)]"
          />
          <div className="w-12 h-12 mx-auto rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-black text-white uppercase">Agradecemos sua Participação!</h2>
            <p className="text-xs text-slate-300 mt-1">
              Sua avaliação foi registrada com sucesso e ajudará o Comando-Geral a aprimorar continuamente nossos eventos e solenidades.
            </p>
          </div>
          <p className="text-[11px] text-[#c5a059] font-bold uppercase tracking-widest pt-2">AD SUMUS!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#040810] text-slate-100 p-4 sm:p-6 md:p-8 flex flex-col justify-between selection:bg-[#c5a059]/30 selection:text-[#e5c07b]">
      <div className="max-w-2xl w-full mx-auto space-y-6">
        {/* Topo Oficial */}
        <header className="text-center space-y-2 pt-2">
          <img
            src={localStorage.getItem('sisgab_custom_logo') || defaultBrasao}
            alt="Brasão Oficial CGCFN"
            onError={(e) => {
              const target = e.currentTarget as HTMLImageElement;
              target.onerror = null;
              target.src = defaultBrasao;
            }}
            className="w-20 h-20 sm:w-24 sm:h-24 mx-auto object-contain drop-shadow-[0_0_16px_rgba(197,160,89,0.75)]"
          />
          <div>
            <span className="text-[10px] sm:text-[11px] font-black text-[#c5a059] tracking-widest uppercase">
              MARINHA DO BRASIL • COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-white uppercase tracking-tight mt-1">
              Pesquisa de Satisfação Pós-Evento
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {eventName} • {eventDate}
            </p>
          </div>
        </header>

        {/* Formulário de Avaliação */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="p-4 sm:p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/30 space-y-5 shadow-2xl">
            <p className="text-xs text-slate-300 text-center">
              Prezado(a) participante, sua opinião é de fundamental importância para o Gabinete do Comando-Geral. Avalie os aspectos abaixo de 1 a 5 estrelas:
            </p>

            {/* Identificação Opcional */}
            <div>
              <label className="block text-slate-400 text-xs font-bold mb-1">
                Seu Nome / Posto ou Graduação (Opcional):
              </label>
              <input
                type="text"
                placeholder="Ex: CMG (FN) Silva / Anônimo"
                value={autoridadeNome}
                onChange={(e) => setAutoridadeNome(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            {/* Critérios de Avaliação com Estrelas */}
            <div className="space-y-4 pt-2 divide-y divide-slate-800/80">
              {/* Critério 1 */}
              <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-white block">1. Recepção & Credenciamento</span>
                  <span className="text-[11px] text-slate-400">Atendimento na chegada, entrega de crachás e acolhimento</span>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRatingValue('recepcao', star)}
                      className="p-1 transition-transform hover:scale-125"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= ratings.recepcao
                            ? 'text-[#c5a059] fill-[#c5a059]'
                            : 'text-slate-700'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Critério 2 */}
              <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-white block">2. Cerimonial & Solenidade</span>
                  <span className="text-[11px] text-slate-400">Organização, pontualidade, pronunciamentos e protocolo</span>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRatingValue('cerimonial', star)}
                      className="p-1 transition-transform hover:scale-125"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= ratings.cerimonial
                            ? 'text-[#c5a059] fill-[#c5a059]'
                            : 'text-slate-700'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Critério 3 */}
              <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-white block">3. Coquetel / Confraternização</span>
                  <span className="text-[11px] text-slate-400">Qualidade dos serviços, alimentação e ambiente</span>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRatingValue('coquetel', star)}
                      className="p-1 transition-transform hover:scale-125"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= ratings.coquetel
                            ? 'text-[#c5a059] fill-[#c5a059]'
                            : 'text-slate-700'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Critério 4 */}
              <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-white block">4. Cobertura de Mídia & Fotos</span>
                  <span className="text-[11px] text-slate-400">Rapidez na disponibilização das fotos e atendimento COMSOC</span>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRatingValue('audiovisual', star)}
                      className="p-1 transition-transform hover:scale-125"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= ratings.audiovisual
                            ? 'text-[#c5a059] fill-[#c5a059]'
                            : 'text-slate-700'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Critério 5 - Avaliação Geral */}
              <div className="pt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-black text-[#00e5ff] block">5. Avaliação Geral do Evento (NPS)</span>
                  <span className="text-[11px] text-slate-400">Satisfação global com o evento</span>
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRatingValue('geral', star)}
                      className="p-1 transition-transform hover:scale-125"
                    >
                      <Star
                        className={`w-7 h-7 ${
                          star <= ratings.geral
                            ? 'text-[#00e5ff] fill-[#00e5ff]'
                            : 'text-slate-700'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Comentários e Sugestões */}
            <div className="space-y-3 pt-3 border-t border-slate-800">
              <div>
                <label className="block text-slate-300 text-xs font-bold mb-1">
                  O que mais lhe agradou no evento? (Pontos Positivos / Elogios)
                </label>
                <textarea
                  rows={2}
                  placeholder="Compartilhe seus elogios ou momentos marcantes..."
                  value={comentarios}
                  onChange={(e) => setComentarios(e.target.value)}
                  className="w-full p-3 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-slate-300 text-xs font-bold mb-1">
                  Sugestões para os próximos eventos:
                </label>
                <textarea
                  rows={2}
                  placeholder="Sugestões, melhorias de horário, estrutura, etc..."
                  value={sugestoes}
                  onChange={(e) => setSugestoes(e.target.value)}
                  className="w-full p-3 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />
              </div>
            </div>

            {/* Botão de Envio */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-[#c5a059] to-[#e5c07b] hover:brightness-110 text-slate-950 font-black text-xs uppercase tracking-wider shadow-lg shadow-[#c5a059]/25 transition-all flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" />
                <span>{loading ? 'Enviando Avaliação...' : 'Enviar Minha Avaliação'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Rodapé */}
      <footer className="pt-8 pb-3 text-center border-t border-slate-900 mt-8">
        <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
          Comunicação Social • Gabinete do Comando-Geral do Corpo de Fuzileiros Navais
        </p>
      </footer>
    </div>
  );
};
