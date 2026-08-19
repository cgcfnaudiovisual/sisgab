import React from 'react';
import { Construction, Sparkles, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ModulePlaceholderProps {
  title: string;
  category: string;
  description: string;
}

export const ModulePlaceholder: React.FC<ModulePlaceholderProps> = ({
  title,
  category,
  description,
}) => {
  const navigate = useNavigate();

  return (
    <div className="py-12 px-4 max-w-xl mx-auto text-center space-y-4">
      <div className="w-16 h-16 rounded-2xl bg-[#c5a059]/10 border border-[#c5a059]/30 flex items-center justify-center mx-auto text-[#c5a059] shadow-lg shadow-[#c5a059]/10">
        <Construction className="w-8 h-8" />
      </div>

      <div className="space-y-1">
        <span className="text-[10px] font-bold text-[#c5a059] uppercase tracking-widest px-2.5 py-0.5 rounded bg-[#c5a059]/10 border border-[#c5a059]/30">
          {category}
        </span>
        <h1 className="text-2xl font-black text-white">{title}</h1>
        <p className="text-xs text-slate-400 max-w-md mx-auto">{description}</p>
      </div>

      <div className="p-4 rounded-xl bg-[#0b1222] border border-slate-800 text-xs text-slate-300 space-y-2 text-left">
        <p className="font-bold text-[#00e5ff] flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          Próximo Bloco na Fila de Construção
        </p>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Este módulo está mapeado no plano diretor e será construído na sequência correspondente. O Bloco 1 (Gabinete & Operações Diárias) já está 100% ativo!
        </p>
      </div>

      <button
        onClick={() => navigate('/')}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-all"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Voltar ao Painel de Comando</span>
      </button>
    </div>
  );
};
