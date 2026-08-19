import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Sparkles, ArrowRight, X } from 'lucide-react';
import { MENU_CATEGORIES } from './AppSidebar';

interface CommandMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandMenu: React.FC<CommandMenuProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          setQuery('');
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const allItems = MENU_CATEGORIES.flatMap((c) => c.items);
  const filtered = allItems.filter(
    (item) =>
      item.name.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (path: string) => {
    navigate(path);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-[#0b1220] border border-[#c5a059]/40 rounded-xl shadow-2xl overflow-hidden shadow-black/80">
        {/* Search Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 bg-[#070c18]">
          <Search className="w-5 h-5 text-[#c5a059]" />
          <input
            type="text"
            placeholder="Digite para buscar módulo, pauta ou ação..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="flex-1 bg-transparent text-white placeholder-slate-500 text-sm focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-md transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length > 0 ? (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => handleSelect(item.path)}
                  className="w-full flex items-center justify-between p-2.5 rounded-lg hover:bg-[#c5a059]/10 text-left transition-colors group border border-transparent hover:border-[#c5a059]/30"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-center text-[#c5a059] group-hover:border-[#c5a059]/50">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="truncate">
                      <p className="text-xs font-semibold text-slate-200 group-hover:text-[#e5c07b]">
                        {item.name}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate">
                        {item.subtitle}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-[#c5a059] transition-transform group-hover:translate-x-1" />
                </button>
              );
            })
          ) : (
            <div className="py-8 text-center text-slate-500 text-xs">
              Nenhum módulo encontrado para "{query}".
            </div>
          )}
        </div>

        {/* Footer Hint */}
        <div className="px-4 py-2 bg-[#060a14] border-t border-slate-800 text-[10px] text-slate-400 flex items-center justify-between">
          <span>Navegue com o mouse ou teclado</span>
          <span>ESC para fechar</span>
        </div>
      </div>
    </div>
  );
};
