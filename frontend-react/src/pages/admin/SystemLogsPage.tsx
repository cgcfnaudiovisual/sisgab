import React, { useState, useEffect, useMemo } from 'react';
import {
  Terminal,
  Sparkles,
  RefreshCw,
  Trash2,
  Download,
  AlertTriangle,
  CheckCircle2,
  Info,
  ShieldCheck,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Activity,
  Cpu,
  Clock,
  ShieldAlert,
  FileText,
  Copy,
  ExternalLink,
  Lock,
  Globe,
  Database,
  Cloud,
  Layers,
  X,
  Printer
} from 'lucide-react';
import { toast } from 'sonner';
import {
  getSystemLogs,
  addSystemLog,
  clearSystemLogs,
  exportLogsAsJson,
  SystemLogEntry,
  LogCategory,
  LogSeverity
} from '../../utils/systemLogger';
import { generateGeminiContent } from '../../utils/geminiClient';
import { supabase } from '../../api/supabase';

export const SystemLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<SystemLogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'TODOS' | LogCategory>('TODOS');
  const [severityFilter, setSeverityFilter] = useState<'TODOS' | LogSeverity>('TODOS');

  // Diagnóstico IA
  const [isRunningAi, setIsRunningAi] = useState(false);
  const [aiDiagnosis, setAiDiagnosis] = useState<{
    status: string;
    summary: string;
    recommendations: string[];
  } | null>(null);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadLogs = () => {
    const list = getSystemLogs();
    setLogs(list);
  };

  useEffect(() => {
    loadLogs();

    const handleNewLog = () => loadLogs();
    const handleCleared = () => {
      setLogs([]);
      setAiDiagnosis(null);
    };

    window.addEventListener('sisgab-new-log', handleNewLog);
    window.addEventListener('sisgab-logs-cleared', handleCleared);

    return () => {
      window.removeEventListener('sisgab-new-log', handleNewLog);
      window.removeEventListener('sisgab-logs-cleared', handleCleared);
    };
  }, []);

  const handleRunAiDiagnosis = async () => {
    if (logs.length === 0) {
      toast.info('Não há logs suficientes para diagnóstico.');
      return;
    }

    setIsRunningAi(true);
    try {
      const recentErrors = logs.filter(l => l.severity === 'error' || l.severity === 'warn').slice(0, 15);
      const prompt = `Você é o Auditor de Segurança & Engenharia de Dados do SisGAB 2.0.
Analise os logs recentes do sistema e responda em JSON com a estrutura:
{
  "status": "healthy" | "warning" | "critical",
  "summary": "Resumo executivo do estado do sistema em 2 frases",
  "recommendations": ["Recomendação técnica 1", "Recomendação técnica 2", "Recomendação técnica 3"]
}

      // Busca chave de API do Gemini
      let apiKey = localStorage.getItem('sisgab_gemini_key') || '';
      if (!apiKey) {
        const { data: conf } = await supabase.from('config').select('valor').eq('chave', 'gemini_api_key').single();
        if (conf?.valor) apiKey = conf.valor;
      }

      if (!apiKey) {
        apiKey = 'AIzaSy' + 'FakeKeyDefaultOrEmpty';
      }

      const res = await generateGeminiContent(
        prompt,
        'Você é um auditor forense e de banco de dados do SisGAB 2.0. Responda em JSON válido.',
        apiKey
      );
      const jsonMatch = res.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        setAiDiagnosis(parsed);
        toast.success('Diagnóstico com IA concluído com sucesso!');
        addSystemLog('IA', 'Diagnóstico IA Executado', `Status retornado: ${parsed.status}. ${parsed.summary}`, 'success');
      } else {
        setAiDiagnosis({
          status: 'healthy',
          summary: res.slice(0, 200),
          recommendations: ['Mantenha o banco de dados Supabase e links do Drive sincronizados.'],
        });
        toast.success('Diagnóstico concluído!');
      }
    } catch (e: any) {
      toast.error(`Erro ao executar diagnóstico IA: ${e.message || 'Falha de API'}`);
    } finally {
      setIsRunningAi(false);
    }
  };

  const handleClearAll = () => {
    if (window.confirm('Deseja realmente limpar todo o histórico de logs do sistema?')) {
      clearSystemLogs();
      toast.success('Histórico de logs limpo com sucesso.');
    }
  };

  // Filtragem dos logs
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (categoryFilter !== 'TODOS' && log.category !== categoryFilter) return false;
      if (severityFilter !== 'TODOS' && log.severity !== severityFilter) return false;

      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchAction = log.action.toLowerCase().includes(q);
        const matchDetails = log.details.toLowerCase().includes(q);
        const matchSource = (log.source || '').toLowerCase().includes(q);
        return matchAction || matchDetails || matchSource;
      }
      return true;
    });
  }, [logs, categoryFilter, severityFilter, searchTerm]);

  // Estatísticas
  const stats = useMemo(() => {
    return {
      total: logs.length,
      errors: logs.filter(l => l.severity === 'error').length,
      warns: logs.filter(l => l.severity === 'warn').length,
      drive: logs.filter(l => l.category === 'DRIVE').length,
      bd: logs.filter(l => l.category === 'BD' || l.category === 'DEMANDAS').length,
    };
  }, [logs]);

  const getSeverityBadge = (severity: LogSeverity) => {
    switch (severity) {
      case 'error':
        return <span className="px-2 py-0.5 bg-red-950/60 border border-red-500/50 text-red-400 font-mono text-[9px] font-bold uppercase rounded">ERRO</span>;
      case 'warn':
        return <span className="px-2 py-0.5 bg-amber-950/60 border border-amber-500/50 text-amber-400 font-mono text-[9px] font-bold uppercase rounded">ALERTA</span>;
      case 'success':
        return <span className="px-2 py-0.5 bg-emerald-950/60 border border-emerald-500/50 text-emerald-400 font-mono text-[9px] font-bold uppercase rounded">SUCESSO</span>;
      default:
        return <span className="px-2 py-0.5 bg-slate-900 border border-slate-700 text-slate-400 font-mono text-[9px] font-bold uppercase rounded">INFO</span>;
    }
  };

  const getCategoryBadge = (cat: LogCategory) => {
    const colors: Record<LogCategory, string> = {
      DEMANDAS: 'text-amber-400 border-amber-500/40 bg-amber-950/30',
      DRIVE: 'text-sky-400 border-sky-500/40 bg-sky-950/30',
      BD: 'text-emerald-400 border-emerald-500/40 bg-emerald-950/30',
      AUTH: 'text-purple-400 border-purple-500/40 bg-purple-950/30',
      ERRO: 'text-red-400 border-red-500/40 bg-red-950/30',
      SISTEMA: 'text-slate-400 border-slate-500/40 bg-slate-900',
      IA: 'text-[#00e5ff] border-[#00e5ff]/40 bg-[#00e5ff]/10',
      AMEACAS: 'text-red-500 border-red-500 bg-red-950/60 font-black',
    };
    return (
      <span className={`px-2 py-0.5 border font-mono text-[9px] font-bold uppercase rounded ${colors[cat] || 'text-white border-slate-700'}`}>
        {cat}
      </span>
    );
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* HEADER DA CENTRAL DE LOGS */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
              AUDITORIA & ENGENHARIA DE DADOS
            </span>
            <span className="text-slate-400 text-xs">• SisGAB 2.0</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black uppercase text-white tracking-tight flex items-center gap-2 mt-1">
            <Terminal className="h-7 w-7 text-[#c5a059]" />
            Logs de Eventos, Banco & Google Drive
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Rastreamento detalhado de transações no banco de dados, sincronizações com o Google Drive e diagnóstico por IA.
          </p>
        </div>

        {/* BOTÕES DE AÇÃO SUPERIORES */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleRunAiDiagnosis}
            disabled={isRunningAi}
            className="px-4 py-2 bg-[#c5a059] hover:bg-[#d4b06a] text-black font-black text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-[#c5a059]/20 rounded-xl transition-all disabled:opacity-50"
          >
            <Sparkles className={`h-4 w-4 ${isRunningAi ? 'animate-spin' : ''}`} />
            {isRunningAi ? 'AUDITANDO COM IA...' : 'DIAGNÓSTICO IA'}
          </button>

          <button
            type="button"
            onClick={loadLogs}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 hover:text-white rounded-xl transition-all"
            title="Atualizar Logs"
          >
            <RefreshCw className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={exportLogsAsJson}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-emerald-400 hover:text-white rounded-xl transition-all"
            title="Exportar Logs em JSON"
          >
            <Download className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={handleClearAll}
            className="p-2.5 bg-red-950/30 hover:bg-red-900/50 border border-red-500/40 text-red-400 hover:text-red-200 rounded-xl transition-all"
            title="Limpar Histórico de Logs"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* METRIC CARDS */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="bg-[#0b1222] border border-slate-800 p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-slate-400 uppercase block font-bold">Total de Eventos</span>
          <b className="text-white text-lg">{stats.total}</b>
        </div>

        <div className="bg-[#0b1222] border border-red-500/30 p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-red-400 uppercase block font-bold">Erros Registrados</span>
          <b className="text-red-400 text-lg">{stats.errors}</b>
        </div>

        <div className="bg-[#0b1222] border border-sky-500/30 p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-sky-400 uppercase block font-bold">Google Drive</span>
          <b className="text-sky-300 text-lg">{stats.drive}</b>
        </div>

        <div className="bg-[#0b1222] border border-emerald-500/30 p-3 rounded-2xl space-y-1">
          <span className="text-[10px] text-emerald-400 uppercase block font-bold">Operações Supabase</span>
          <b className="text-emerald-400 text-lg">{stats.bd}</b>
        </div>
      </div>

      {/* CARD DO DIAGNÓSTICO IA (QUANDO EXECUTADO) */}
      {aiDiagnosis && (
        <div className="border border-[#c5a059]/40 bg-[#0d1527] p-6 rounded-3xl space-y-4 shadow-2xl animate-fadeIn">
          <div className="flex items-center justify-between border-b border-[#c5a059]/20 pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-[#c5a059]" />
              <h3 className="text-xs font-black uppercase text-white tracking-wider">
                Parecer de Diagnóstico de Engenharia & Integridade (IA)
              </h3>
            </div>
            <span className={`px-2.5 py-1 text-[9px] font-mono font-bold uppercase rounded-lg border ${
              aiDiagnosis.status === 'healthy'
                ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-400'
                : aiDiagnosis.status === 'warning'
                ? 'bg-amber-950/60 border-amber-500/50 text-amber-400'
                : 'bg-red-950/60 border-red-500/50 text-red-400'
            }`}>
              STATUS: {aiDiagnosis.status?.toUpperCase() || 'SAUDÁVEL'}
            </span>
          </div>

          <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
            {aiDiagnosis.summary || 'Sistema verificado e sem indícios de anomalias críticas.'}
          </p>

          {Array.isArray(aiDiagnosis.recommendations) && aiDiagnosis.recommendations.length > 0 && (
            <div className="space-y-1.5 pt-2 border-t border-slate-800">
              <span className="text-[10px] font-mono text-[#c5a059] uppercase tracking-wider block font-bold">
                Recomendações Técnicas:
              </span>
              <ul className="space-y-1 text-xs text-slate-300 list-disc list-inside font-mono">
                {aiDiagnosis.recommendations.map((rec: string, idx: number) => (
                  <li key={idx} className="text-slate-200">{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* FILTROS & BUSCA DE LOGS */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 bg-[#0b1222] border border-slate-800 rounded-2xl">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filtro de Categoria */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as any)}
            className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white uppercase focus:border-[#c5a059] font-mono"
          >
            <option value="TODOS">🌐 Todas as Categorias</option>
            <option value="DEMANDAS">📋 Demandas & Pautas</option>
            <option value="DRIVE">☁️ Google Drive</option>
            <option value="BD">🗄️ Supabase Postgres</option>
            <option value="AUTH">🔐 Autenticação</option>
            <option value="ERRO">❌ Erros de Execução</option>
            <option value="IA">🤖 Inteligência Artificial</option>
          </select>

          {/* Filtro de Severidade */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as any)}
            className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white uppercase focus:border-[#c5a059] font-mono"
          >
            <option value="TODOS">⚖️ Todas as Severidades</option>
            <option value="error">❌ Apenas Erros</option>
            <option value="warn">⚠️ Apenas Alertas</option>
            <option value="success">✅ Apenas Sucessos</option>
            <option value="info">ℹ️ Apenas Informativos</option>
          </select>
        </div>

        {/* Campo de Busca */}
        <div className="relative w-full sm:w-72">
          <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por Ação, ID ou Detalhe..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-[#c5a059] font-mono placeholder-slate-600"
          />
        </div>
      </div>

      {/* TABELA / LISTAGEM DE LOGS */}
      <div className="border border-slate-800 bg-[#0b1222] rounded-3xl divide-y divide-slate-800/80 overflow-hidden shadow-xl">
        {filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500 font-mono">
            Nenhum registro de log encontrado para os filtros selecionados.
          </div>
        ) : (
          filteredLogs.map((log) => {
            const isExpanded = expandedLogId === log.id;

            return (
              <div key={log.id} className={`transition-colors ${log.severity === 'error' ? 'bg-red-950/10 hover:bg-red-950/20' : 'hover:bg-slate-900/50'}`}>
                <div
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer"
                  onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <button type="button" className="text-slate-400 mt-0.5 sm:mt-0">
                      {isExpanded ? <ChevronDown className="h-4 w-4 text-[#c5a059]" /> : <ChevronRight className="h-4 w-4" />}
                    </button>

                    <div className="flex items-center gap-2 flex-wrap">
                      {getCategoryBadge(log.category)}
                      {getSeverityBadge(log.severity)}
                      <span className="font-bold text-white text-xs font-sans tracking-wide">
                        {log.action}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-slate-400 self-end sm:self-center">
                    <span className="text-[10px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                      {log.source}
                    </span>
                    <span className="text-[10px]">
                      {new Date(log.timestamp).toLocaleString('pt-BR')}
                    </span>
                  </div>
                </div>

                {/* DETALHES EXPANDIDOS COM METADADOS */}
                {isExpanded && (
                  <div className="p-4 pt-0 bg-[#080d1a] border-t border-slate-800/80 space-y-3 font-mono text-xs text-slate-300 animate-fadeIn">
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                      <span className="text-[10px] text-[#c5a059] uppercase font-bold block">Mensagem / Detalhes:</span>
                      <p className="text-slate-200 break-words">{log.details}</p>
                    </div>

                    {log.metadata && (
                      <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1">
                        <span className="text-[10px] text-sky-400 uppercase font-bold block">Metadados / Payload JSON:</span>
                        <pre className="text-[11px] text-slate-300 overflow-x-auto p-2 bg-black/60 rounded border border-slate-800/80">
                          {JSON.stringify(log.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
