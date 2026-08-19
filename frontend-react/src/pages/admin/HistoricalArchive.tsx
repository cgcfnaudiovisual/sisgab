import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  Calendar,
  ExternalLink,
  FolderOpen,
  Filter,
  Layers,
  Sparkles,
} from 'lucide-react';
import { supabase } from '../../api/supabase';
import type { DemandaComunicacao } from '../../types/database';
import { parseCobertura } from '../../utils/formatters';

export const HistoricalArchive: React.FC = () => {
  const [demandas, setDemandas] = useState<DemandaComunicacao[]>([]);
  const [selectedAno, setSelectedAno] = useState<number>(2026);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistorico();
  }, []);

  const loadHistorico = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .order('data_evento', { ascending: false });

      if (!error && data) {
        setDemandas(data as DemandaComunicacao[]);
      }
    } catch (err) {
      console.warn('Erro ao carregar histórico:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = demandas.filter((h) => {
    const anoEvento = h.data_evento ? parseInt(h.data_evento.split('-')[0], 10) : 2026;
    const matchAno = selectedAno === 0 || anoEvento === selectedAno;
    const matchQ =
      h.titulo_evento.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (h.autoridades && h.autoridades.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (h.local_evento && h.local_evento.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchAno && matchQ;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
            Acervo & Memória Institucional
          </span>
          <span className="text-slate-400 text-xs">• Arquivo Histórico</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Arquivo e Histórico de Coberturas Passadas ({demandas.length} Registros)
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm">
          Linha do tempo e registros fotográficos consolidados de todas as operações e eventos do Gabinete.
        </p>
      </div>

      {/* Filtros por Ano & Busca */}
      <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xl">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedAno(2026)}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
              selectedAno === 2026
                ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                : 'bg-slate-900 text-slate-400 border border-slate-800'
            }`}
          >
            Exercício 2026
          </button>

          <button
            onClick={() => setSelectedAno(2025)}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
              selectedAno === 2025
                ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                : 'bg-slate-900 text-slate-400 border border-slate-800'
            }`}
          >
            Ano 2025
          </button>

          <button
            onClick={() => setSelectedAno(0)}
            className={`px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
              selectedAno === 0
                ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                : 'bg-slate-900 text-slate-400 border border-slate-800'
            }`}
          >
            Todos os Anos
          </button>
        </div>

        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Filtrar por evento, local ou autoridade..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
          />
        </div>
      </div>

      {/* Grid de Eventos Históricos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.length > 0 ? (
          filtered.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/40 transition-all space-y-4 shadow-lg flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px] font-bold border border-blue-500/30">
                    📅 {item.data_evento}
                  </span>
                  <span className="text-[10px] font-black text-slate-400 uppercase">
                    {item.status}
                  </span>
                </div>

                <h3 className="text-base font-black text-white leading-snug">
                  {item.titulo_evento}
                </h3>

                <p className="text-xs text-slate-400">
                  📍 <strong className="text-slate-300">{item.local_evento || 'CGCFN'}</strong>
                </p>

                {item.autoridades && (
                  <p className="text-xs text-slate-400">
                    🏛️ Autoridades: <span className="text-slate-300">{item.autoridades}</span>
                  </p>
                )}

                {parseCobertura(item.tipo_cobertura).length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap pt-1">
                    {parseCobertura(item.tipo_cobertura).map((cob, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded bg-slate-900 text-[10px] font-medium text-slate-300 border border-slate-800"
                      >
                        {cob}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-400">
                  Solicitante: {item.solicitante_nome}
                </span>

                {item.drive_url ? (
                  <a
                    href={item.drive_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs font-bold text-[#00e5ff] border border-slate-700 transition-colors"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    <span>Drive</span>
                  </a>
                ) : (
                  <span className="text-[10px] text-slate-500 italic">Arquivado</span>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full py-12 text-center text-slate-500 text-xs rounded-2xl bg-[#0b1222] border border-slate-800">
            Nenhum evento histórico encontrado para os critérios selecionados.
          </div>
        )}
      </div>
    </div>
  );
};
