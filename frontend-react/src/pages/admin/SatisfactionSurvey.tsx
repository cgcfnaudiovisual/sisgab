import React, { useState, useEffect, useMemo } from 'react';
import {
  Star,
  MessageSquare,
  TrendingUp,
  Mail,
  Share2,
  Printer,
  CheckCircle2,
  Users,
  Award,
  Send,
  Sparkles,
  Search,
  Filter,
  Copy,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Heart,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  MapPin,
  Sliders,
  Eye,
  QrCode,
  FileSpreadsheet,
  Check,
  Smartphone,
  Layout,
  HelpCircle,
  BarChart3,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { JadeEvento } from '../../types/database';

export type QuestionCategory = 'recepcao' | 'cerimonial' | 'coquetel' | 'audiovisual' | 'geral' | 'outros';
export type QuestionType = 'rating_5' | 'nps_10' | 'boolean' | 'multiple_choice' | 'text';

export interface SurveyQuestion {
  id: string;
  label: string;
  category: QuestionCategory;
  type: QuestionType;
  options?: string[];
  required: boolean;
  helperText?: string;
}

export interface SurveyForm {
  id: string;
  title: string;
  description: string;
  eventoId?: number | null; // null = Pesquisa Independente / Avulsa
  eventoNome?: string;
  createdAt: string;
  status: 'ativa' | 'encerrada' | 'rascunho';
  customTheme: 'navy_ouro' | 'clean_white' | 'dark_tactical';
  allowAnonymous: boolean;
  questions: SurveyQuestion[];
}

export interface SurveyResponseItem {
  id: string;
  surveyId: string;
  eventoId?: number | null;
  respondentName: string;
  respondentRank?: string;
  respondentMilitaryStatus?: string;
  answeredAt: string;
  ratings: Record<string, number>;
  textAnswers: Record<string, string>;
  booleanAnswers: Record<string, boolean>;
  choiceAnswers: Record<string, string>;
  npsScore?: number;
  generalComments?: string;
}

const DEFAULT_CERIMONIAL_QUESTIONS: SurveyQuestion[] = [
  {
    id: 'q_recepcao',
    label: 'Como você avalia a Recepção e o Credenciamento na chegada?',
    category: 'recepcao',
    type: 'rating_5',
    required: true,
    helperText: 'Pontualidade, acolhimento e entrega de crachás/identificação.',
  },
  {
    id: 'q_cerimonial',
    label: 'Qual o seu nível de satisfação com o Cerimonial Militar e Protocolo?',
    category: 'cerimonial',
    type: 'rating_5',
    required: true,
    helperText: 'Condução do mestre de cerimônias, honras militares e respeito às tradições.',
  },
  {
    id: 'q_coquetel',
    label: 'Como avalia o Buffet / Coquetel servido no evento?',
    category: 'coquetel',
    type: 'rating_5',
    required: false,
    helperText: 'Variedade, temperatura, atendimento e qualidade dos itens.',
  },
  {
    id: 'q_audiovisual',
    label: 'Como você avalia a Cobertura Audiovisual, Telões e Som?',
    category: 'audiovisual',
    type: 'rating_5',
    required: false,
    helperText: 'Clareza de áudio, iluminação, telões de transmissão e cobertura da COMSOC.',
  },
  {
    id: 'q_nps',
    label: 'Em uma escala de 0 a 10, o quanto você recomendaria e elogiaria a organização deste evento a outros oficiais/colegas?',
    category: 'geral',
    type: 'nps_10',
    required: true,
    helperText: '0 = De forma alguma, 10 = Com certeza recomendaria com entusiasmo.',
  },
  {
    id: 'q_elogios',
    label: 'Deixe seus Elogios ou Destaques Positivos:',
    category: 'geral',
    type: 'text',
    required: false,
    helperText: 'O que mais lhe agradou na condução e organização?',
  },
  {
    id: 'q_sugestoes',
    label: 'Sugestões de Melhoria para os Próximos Eventos:',
    category: 'outros',
    type: 'text',
    required: false,
    helperText: 'Pontos que podemos aperfeiçoar nas próximas cerimônias.',
  },
];

export const SatisfactionSurvey: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'painel' | 'editor' | 'disparos' | 'respostas'>('painel');
  const [eventos, setEventos] = useState<JadeEvento[]>([]);
  const [loadingEventos, setLoadingEventos] = useState(true);

  const [surveys, setSurveys] = useState<SurveyForm[]>(() => {
    try {
      const stored = localStorage.getItem('sisgab_satisfaction_surveys');
      if (stored) return JSON.parse(stored);
    } catch { }
    return [
      {
        id: 'survey_padrao_cerimonial',
        title: 'Pesquisa de Satisfação & Feedback do Convidado',
        description: 'Formulário oficial de avaliação pós-evento do Gabinete do Comando-Geral do Corpo de Fuzileiros Navais.',
        eventoId: null,
        eventoNome: 'Formulário Geral / Padrão COMSOC',
        createdAt: new Date().toISOString(),
        status: 'ativa',
        customTheme: 'navy_ouro',
        allowAnonymous: false,
        questions: DEFAULT_CERIMONIAL_QUESTIONS,
      },
    ];
  });

  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(() => {
    return surveys[0]?.id || 'survey_padrao_cerimonial';
  });

  // 100% ZERADO / SEM DADOS MOCKADOS
  const [responses, setResponses] = useState<SurveyResponseItem[]>(() => {
    try {
      const stored = localStorage.getItem('sisgab_survey_responses');
      if (stored) return JSON.parse(stored);
    } catch { }
    return [];
  });

  const [showNewSurveyModal, setShowNewSurveyModal] = useState(false);
  const [newSurveyData, setNewSurveyData] = useState({
    title: '',
    description: '',
    eventoId: 'avulso',
    allowAnonymous: false,
    customTheme: 'navy_ouro' as 'navy_ouro' | 'clean_white' | 'dark_tactical',
  });

  const [showManageSurveysModal, setShowManageSurveysModal] = useState(false);
  const [showAddQuestionModal, setShowAddQuestionModal] = useState(false);
  const [newQuestionData, setNewQuestionData] = useState<Partial<SurveyQuestion>>({
    label: '',
    category: 'geral',
    type: 'rating_5',
    required: false,
    helperText: '',
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [filterNpsType, setFilterNpsType] = useState<'todos' | 'promotores' | 'neutros' | 'detratores'>('todos');

  const [previewAnswers, setPreviewAnswers] = useState<{
    name: string;
    rank: string;
    ratings: Record<string, number>;
    nps: number;
    comments: string;
    suggestions: string;
  }>({
    name: '',
    rank: '',
    ratings: {},
    nps: 10,
    comments: '',
    suggestions: '',
  });

  useEffect(() => {
    try {
      localStorage.setItem('sisgab_satisfaction_surveys', JSON.stringify(surveys));
    } catch { }
  }, [surveys]);

  useEffect(() => {
    try {
      localStorage.setItem('sisgab_survey_responses', JSON.stringify(responses));
    } catch { }
  }, [responses]);

  useEffect(() => {
    async function carregarEventos() {
      setLoadingEventos(true);
      try {
        const { data, error } = await supabase
          .from('jade_eventos')
          .select('*')
          .order('data_evento', { ascending: false });

        if (!error && data && data.length > 0) {
          setEventos(data);
        } else {
          setEventos([
            {
              id: 1,
              nome: 'CERIMÔNIA DE PASSAGEM DE COMANDO DO CGCFN',
              data_evento: '2026-08-25',
              local: 'Salão Nobre do CGCFN • Fortaleza de São José',
              tipo_layout: 'auditorio',
              layout_json: { rows: 5, cols: 8 },
              status: 'ativo',
              created_at: new Date().toISOString(),
            },
            {
              id: 2,
              nome: 'ENCONTRO DE VETERANOS FUZILEIROS NAVAIS',
              data_evento: '2026-08-30',
              local: 'Auditório Almirante Guilhem • Ilha do Governador',
              tipo_layout: 'auditorio',
              layout_json: { rows: 5, cols: 8 },
              status: 'ativo',
              created_at: new Date().toISOString(),
            },
          ]);
        }
      } catch { } finally {
        setLoadingEventos(false);
      }
    }
    carregarEventos();
  }, []);

  const currentSurvey = useMemo(() => {
    return surveys.find((s) => s.id === selectedSurveyId) || surveys[0];
  }, [surveys, selectedSurveyId]);

  const currentLinkedEvento = useMemo(() => {
    if (!currentSurvey || !currentSurvey.eventoId) return null;
    return eventos.find((e) => e.id === currentSurvey.eventoId) || null;
  }, [currentSurvey, eventos]);

  const currentSurveyResponses = useMemo(() => {
    return responses.filter((r) => r.surveyId === currentSurvey?.id);
  }, [responses, currentSurvey]);

  const totalRespostas = currentSurveyResponses.length;

  const stats = useMemo(() => {
    if (totalRespostas === 0) {
      return {
        mediaGeral: '0.0',
        mediaRecepcao: '0.0',
        mediaCerimonial: '0.0',
        mediaCoquetel: '0.0',
        mediaAudiovisual: '0.0',
        npsScore: 0,
        promotoresCount: 0,
        neutrosCount: 0,
        detratoresCount: 0,
        promotoresPct: 0,
        detratoresPct: 0,
      };
    }

    let sumGeral = 0;
    let countGeral = 0;
    let sumRecepcao = 0;
    let countRecepcao = 0;
    let sumCerimonial = 0;
    let countCerimonial = 0;
    let sumCoquetel = 0;
    let countCoquetel = 0;
    let sumAudio = 0;
    let countAudio = 0;

    let promotores = 0;
    let neutros = 0;
    let detratores = 0;

    currentSurveyResponses.forEach((resp) => {
      Object.entries(resp.ratings).forEach(([qId, val]) => {
        if (typeof val === 'number' && val > 0) {
          sumGeral += val;
          countGeral++;

          if (qId.includes('recepcao')) {
            sumRecepcao += val;
            countRecepcao++;
          } else if (qId.includes('cerimonial')) {
            sumCerimonial += val;
            countCerimonial++;
          } else if (qId.includes('coquetel') || qId.includes('buffet')) {
            sumCoquetel += val;
            countCoquetel++;
          } else if (qId.includes('audio') || qId.includes('som')) {
            sumAudio += val;
            countAudio++;
          }
        }
      });

      if (typeof resp.npsScore === 'number') {
        if (resp.npsScore >= 9) promotores++;
        else if (resp.npsScore >= 7) neutros++;
        else detratores++;
      }
    });

    const promotoresPct = totalRespostas > 0 ? Math.round((promotores / totalRespostas) * 100) : 0;
    const detratoresPct = totalRespostas > 0 ? Math.round((detratores / totalRespostas) * 100) : 0;
    const nps = promotoresPct - detratoresPct;

    return {
      mediaGeral: countGeral > 0 ? (sumGeral / countGeral).toFixed(1) : '0.0',
      mediaRecepcao: countRecepcao > 0 ? (sumRecepcao / countRecepcao).toFixed(1) : '0.0',
      mediaCerimonial: countCerimonial > 0 ? (sumCerimonial / countCerimonial).toFixed(1) : '0.0',
      mediaCoquetel: countCoquetel > 0 ? (sumCoquetel / countCoquetel).toFixed(1) : '0.0',
      mediaAudiovisual: countAudio > 0 ? (sumAudio / countAudio).toFixed(1) : '0.0',
      npsScore: nps,
      promotoresCount: promotores,
      neutrosCount: neutros,
      detratoresCount: detratores,
      promotoresPct,
      detratoresPct,
    };
  }, [currentSurveyResponses, totalRespostas]);

  const surveyPublicUrl = `${window.location.origin}/pesquisa_evento/${currentSurvey?.id}`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(surveyPublicUrl);
    toast.success('Link do formulário copiado com sucesso!', {
      description: surveyPublicUrl,
    });
  };

  const handleOpenWhatsApp = () => {
    const nomeEv = currentLinkedEvento?.nome || currentSurvey?.title || 'Evento Institucional';
    const msg = `Prezado(a) Convidado(a) / Autoridade,\n\nO Comando-Geral do Corpo de Fuzileiros Navais agradece sua distinta presença em *${nomeEv}*.\n\nSua avaliação é fundamental para mantermos o padrão de excelência de nossas cerimônias. Por favor, responda à nossa breve pesquisa de satisfação (1 minuto):\n🔗 ${surveyPublicUrl}\n\n_Comunicação Social • Gabinete CGCFN_\nAD SUMUS!`;
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank');
  };

  const handleCreateSurvey = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSurveyData.title.trim()) {
      toast.error('Informe o título da pesquisa.');
      return;
    }

    const isLinked = newSurveyData.eventoId !== 'avulso';
    const evId = isLinked ? Number(newSurveyData.eventoId) : null;
    const evObj = isLinked ? eventos.find((ev) => ev.id === evId) : null;

    const newSurvey: SurveyForm = {
      id: `survey_${Date.now()}`,
      title: newSurveyData.title.trim(),
      description: newSurveyData.description.trim() || 'Pesquisa de avaliação institucional.',
      eventoId: evId,
      eventoNome: evObj ? evObj.nome : 'Pesquisa Independente / Avulsa',
      createdAt: new Date().toISOString(),
      status: 'ativa',
      customTheme: newSurveyData.customTheme,
      allowAnonymous: newSurveyData.allowAnonymous,
      questions: [...DEFAULT_CERIMONIAL_QUESTIONS],
    };

    setSurveys((prev) => [newSurvey, ...prev]);
    setSelectedSurveyId(newSurvey.id);
    setShowNewSurveyModal(false);
    setNewSurveyData({
      title: '',
      description: '',
      eventoId: 'avulso',
      allowAnonymous: false,
      customTheme: 'navy_ouro',
    });
    toast.success('Nova pesquisa criada com sucesso!');
  };

  const handleDeleteSurvey = (id: string, title: string) => {
    if (surveys.length <= 1) {
      toast.error('O sistema deve manter pelo menos uma pesquisa cadastrada.');
      return;
    }
    if (confirm(`Deseja realmente excluir a pesquisa "${title}" e todas as suas respostas?`)) {
      setSurveys((prev) => prev.filter((s) => s.id !== id));
      setResponses((prev) => prev.filter((r) => r.surveyId !== id));
      if (selectedSurveyId === id) {
        const remaining = surveys.filter((s) => s.id !== id);
        setSelectedSurveyId(remaining[0]?.id || '');
      }
      toast.success('Pesquisa excluída com sucesso.');
    }
  };

  const handleAddQuestion = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestionData.label?.trim()) {
      toast.error('Informe o texto da pergunta.');
      return;
    }

    const newQ: SurveyQuestion = {
      id: `q_${Date.now()}`,
      label: newQuestionData.label.trim(),
      category: (newQuestionData.category as QuestionCategory) || 'geral',
      type: (newQuestionData.type as QuestionType) || 'rating_5',
      required: Boolean(newQuestionData.required),
      helperText: newQuestionData.helperText?.trim() || '',
    };

    setSurveys((prev) =>
      prev.map((s) => {
        if (s.id === selectedSurveyId) {
          return {
            ...s,
            questions: [...s.questions, newQ],
          };
        }
        return s;
      })
    );

    setShowAddQuestionModal(false);
    setNewQuestionData({
      label: '',
      category: 'geral',
      type: 'rating_5',
      required: false,
      helperText: '',
    });
    toast.success('Pergunta adicionada ao formulário!');
  };

  const handleDeleteQuestion = (questionId: string) => {
    setSurveys((prev) =>
      prev.map((s) => {
        if (s.id === selectedSurveyId) {
          return {
            ...s,
            questions: s.questions.filter((q) => q.id !== questionId),
          };
        }
        return s;
      })
    );
    toast.success('Pergunta removida do formulário.');
  };

  const handleSubmitPreviewTest = (e: React.FormEvent) => {
    e.preventDefault();
    const newAnswer: SurveyResponseItem = {
      id: `resp_${Date.now()}`,
      surveyId: currentSurvey.id,
      eventoId: currentSurvey.eventoId,
      respondentName: previewAnswers.name.trim() || 'Convidado Anônimo',
      respondentRank: previewAnswers.rank.trim() || 'Autoridade / Convidado',
      respondentMilitaryStatus: 'Confirmado',
      answeredAt: new Date().toLocaleString('pt-BR'),
      ratings: previewAnswers.ratings,
      textAnswers: {
        q_elogios: previewAnswers.comments,
        q_sugestoes: previewAnswers.suggestions,
      },
      booleanAnswers: {},
      choiceAnswers: {},
      npsScore: previewAnswers.nps,
      generalComments: previewAnswers.comments,
    };

    setResponses((prev) => [newAnswer, ...prev]);
    toast.success('🎉 Resposta registrada com sucesso!', {
      description: 'O painel e os gráficos foram atualizados com os novos dados.',
    });

    setPreviewAnswers({
      name: '',
      rank: '',
      ratings: {},
      nps: 10,
      comments: '',
      suggestions: '',
    });
  };

  const handleClearAllResponses = () => {
    if (confirm(`Deseja zerar todas as ${totalRespostas} respostas registradas para esta pesquisa?`)) {
      setResponses((prev) => prev.filter((r) => r.surveyId !== currentSurvey.id));
      toast.success('Todas as respostas foram zeradas.');
    }
  };

  const filteredResponses = useMemo(() => {
    return currentSurveyResponses.filter((r) => {
      const matchQuery =
        !searchQuery.trim() ||
        r.respondentName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.generalComments && r.generalComments.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchQuery) return false;

      if (filterNpsType === 'promotores') return (r.npsScore || 0) >= 9;
      if (filterNpsType === 'neutros') return (r.npsScore || 0) >= 7 && (r.npsScore || 0) <= 8;
      if (filterNpsType === 'detratores') return (r.npsScore || 0) <= 6;

      return true;
    });
  }, [currentSurveyResponses, searchQuery, filterNpsType]);

  return (
    <div className="space-y-6 pb-16">
      {/* ── BANNER EXECUTIVO (PADRÃO COMSOC_ASSENTOS) ── */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-[#0b1222] via-[#0d172a] to-[#0b1222] border border-slate-800 shadow-2xl relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-[#c5a059]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6 relative z-10">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-black uppercase tracking-wider border border-emerald-500/40 flex items-center gap-1.5">
                <Sparkles className="w-3 h-3" />
                <span>Gestão de Qualidade & Feedback</span>
              </span>
              <span className="text-slate-400 text-xs">• Cerimonial & Comunicação Social</span>
              {currentLinkedEvento ? (
                <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-[#00e5ff] text-[10px] font-bold uppercase border border-cyan-500/30">
                  Vinculado a Evento
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold uppercase border border-purple-500/30">
                  Pesquisa Independente / Avulsa
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#c5a059] tracking-tight uppercase drop-shadow-md">
              {currentSurvey?.title || 'PESQUISA DE SATISFAÇÃO'}
            </h1>
            <div className="text-xs text-slate-300 flex items-center gap-3 flex-wrap pt-0.5">
              <span className="flex items-center gap-1 font-bold text-white">
                <Calendar className="w-3.5 h-3.5 text-[#00e5ff]" />
                <span>{currentLinkedEvento ? `Data do Evento: ${currentLinkedEvento.data_evento}` : `Criada em: ${new Date(currentSurvey?.createdAt || '').toLocaleDateString('pt-BR')}`}</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <MapPin className="w-3.5 h-3.5 text-[#c5a059]" />
                <span>Local: <strong className="text-white">{currentLinkedEvento?.local || 'Gabinete / CGCFN / Digital'}</strong></span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <Users className="w-3.5 h-3.5 text-emerald-400" />
                <strong className="text-emerald-400">{totalRespostas}</strong> respostas registradas
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700 px-3.5 py-2 rounded-2xl text-xs shadow-md">
              <Sliders className="w-4 h-4 text-[#c5a059]" />
              <select
                value={selectedSurveyId}
                onChange={(e) => setSelectedSurveyId(e.target.value)}
                className="bg-transparent text-white font-bold focus:outline-none cursor-pointer max-w-[210px] truncate"
              >
                {surveys.map((s) => (
                  <option key={s.id} value={s.id} className="bg-slate-900 text-white">
                    {s.eventoId ? `📅 ${s.title}` : `📋 ${s.title}`}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => setShowNewSurveyModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-cyan-950/70 hover:bg-cyan-900/70 text-[#00e5ff] border border-[#00e5ff]/40 font-bold text-xs shadow-md transition-all hover:scale-105"
              title="Criar nova pesquisa"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Nova Pesquisa</span>
            </button>
            <button
              onClick={() => setShowManageSurveysModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold text-xs shadow-md transition-all hover:scale-105"
              title="Gerenciar lista de pesquisas"
            >
              <Sliders className="w-3.5 h-3.5 text-[#c5a059]" />
              <span>Gerenciar</span>
            </button>
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-emerald-500/30 font-bold text-xs shadow-md transition-all"
              title="Copiar link público do formulário"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>Copiar Link</span>
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/20 transition-all hover:scale-105"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Imprimir Relatório</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── NAVEGAÇÃO ENTRE AS 4 ABAS ESTRUTURADAS ── */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveSubTab('painel')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeSubTab === 'painel'
              ? 'bg-[#00e5ff] text-slate-950 shadow-md shadow-[#00e5ff]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>📊 1. Painel & Indicadores NPS ({stats.npsScore > 0 ? `+${stats.npsScore}` : stats.npsScore})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('editor')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeSubTab === 'editor'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Edit2 className="w-4 h-4" />
          <span>📝 2. Editor de Formulário & Perguntas ({currentSurvey?.questions.length || 0})</span>
        </button>
        <button
          onClick={() => setActiveSubTab('disparos')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeSubTab === 'disparos'
              ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Send className="w-4 h-4" />
          <span>🚀 3. Disparos & Compartilhamento (WhatsApp / QR Code)</span>
        </button>
        <button
          onClick={() => setActiveSubTab('respostas')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeSubTab === 'respostas'
              ? 'bg-purple-500 text-slate-950 shadow-md shadow-purple-500/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>💬 4. Respostas & Depoimentos ({totalRespostas})</span>
        </button>
      </div>

      {/* ── ABA 1: PAINEL CONSOLIDADO ── */}
      {activeSubTab === 'painel' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/30 bg-[#00e5ff]/5 space-y-1 shadow-lg">
              <span className="text-xs font-bold text-[#00e5ff] uppercase tracking-wider">Média Geral</span>
              <p className="text-3xl font-black text-white flex items-center gap-1.5">
                <span>{stats.mediaGeral}</span>
                <span className="text-xs text-[#00e5ff] font-bold">/ 5.0 ⭐</span>
              </p>
              <p className="text-[10px] text-slate-400">Avaliação média ponderada</p>
            </div>
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-emerald-500/30 bg-emerald-500/5 space-y-1 shadow-lg">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Índice NPS Oficial</span>
              <p className="text-3xl font-black text-emerald-400">
                {stats.npsScore > 0 ? `+${stats.npsScore}` : stats.npsScore}
              </p>
              <p className="text-[10px] text-slate-400">
                {stats.promotoresPct}% Promotores • {stats.detratoresPct}% Detratores
              </p>
            </div>
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-[#c5a059]/30 bg-[#c5a059]/5 space-y-1 shadow-lg">
              <span className="text-xs font-bold text-[#e5c07b] uppercase tracking-wider">Respostas Reais</span>
              <p className="text-3xl font-black text-[#e5c07b]">
                {totalRespostas}
              </p>
              <p className="text-[10px] text-slate-400">Feedbacks recebidos</p>
            </div>
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-purple-500/30 bg-purple-500/5 space-y-1 shadow-lg">
              <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Status do Formulário</span>
              <p className="text-2xl font-black text-purple-300 uppercase tracking-tight mt-0.5">
                {currentSurvey?.status === 'ativa' ? '🟢 Ativo' : '⚪ Pausado'}
              </p>
              <p className="text-[10px] text-slate-400">{currentSurvey?.questions.length} perguntas ativas</p>
            </div>
          </div>
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-5 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-2">
                <Award className="w-4 h-4 text-[#c5a059]" />
                <span>Avaliação Específica por Setor & Critério</span>
              </h3>
              {totalRespostas > 0 && (
                <button
                  onClick={handleClearAllResponses}
                  className="text-[11px] text-red-400 hover:underline flex items-center gap-1 font-bold"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Zerar Respostas</span>
                </button>
              )}
            </div>
            {totalRespostas === 0 ? (
              <div className="p-10 rounded-2xl bg-slate-950/80 border border-slate-800 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-slate-900 text-slate-500 mx-auto flex items-center justify-center">
                  <BarChart3 className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-white">Nenhum feedback registrado ainda</h4>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Os gráficos e médias serão computados automaticamente conforme os convidados responderem ao formulário.
                  </p>
                </div>
                <div className="flex items-center justify-center gap-3 pt-2">
                  <button
                    onClick={() => setActiveSubTab('editor')}
                    className="px-4 py-2 rounded-xl bg-[#c5a059] text-slate-950 text-xs font-bold hover:bg-[#d6b26b] transition-all"
                  >
                    Ver Formulário no Editor
                  </button>
                  <button
                    onClick={() => setActiveSubTab('disparos')}
                    className="px-4 py-2 rounded-xl bg-slate-800 text-emerald-400 border border-slate-700 text-xs font-bold hover:bg-slate-700 transition-all"
                  >
                    Enviar Link no WhatsApp
                  </button>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">1. Recepção & Credenciamento</span>
                    <span className="font-black text-[#c5a059]">{stats.mediaRecepcao} / 5.0 ⭐</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-[#c5a059]" style={{ width: `${(Number(stats.mediaRecepcao) / 5) * 100}%` }} />
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">2. Cerimonial & Protocolo Militar</span>
                    <span className="font-black text-[#00e5ff]">{stats.mediaCerimonial} / 5.0 ⭐</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-[#00e5ff]" style={{ width: `${(Number(stats.mediaCerimonial) / 5) * 100}%` }} />
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">3. Buffet & Coquetel</span>
                    <span className="font-black text-emerald-400">{stats.mediaCoquetel} / 5.0 ⭐</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-400" style={{ width: `${(Number(stats.mediaCoquetel) / 5) * 100}%` }} />
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">4. Audiovisual & Cobertura COMSOC</span>
                    <span className="font-black text-purple-400">{stats.mediaAudiovisual} / 5.0 ⭐</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-400" style={{ width: `${(Number(stats.mediaAudiovisual) / 5) * 100}%` }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── ABA 2: EDITOR DE FORMULÁRIO ── */}
      {activeSubTab === 'editor' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-7 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-5 shadow-xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  <span>Perguntas Configuradas no Formulário</span>
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Adicione, edite ou reorganize os critérios avaliados pelos convidados.
                </p>
              </div>
              <button
                onClick={() => setShowAddQuestionModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md transition-all shrink-0 hover:scale-105"
              >
                <Plus className="w-4 h-4" />
                <span>Adicionar Pergunta</span>
              </button>
            </div>
            <div className="space-y-3">
              {currentSurvey?.questions.map((q, idx) => (
                <div
                  key={q.id}
                  className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-[#c5a059]/40 transition-all flex items-start justify-between gap-3 group shadow-md"
                >
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="w-6 h-6 rounded-lg bg-slate-800 text-[#c5a059] flex items-center justify-center font-mono font-bold text-xs shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-white">{q.label}</span>
                        {q.required && (
                          <span className="px-1.5 py-0.2 rounded bg-red-500/20 text-red-400 text-[9px] font-bold">
                            Obrigatória
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-mono capitalize">
                          {q.type === 'rating_5'
                            ? '⭐ Estrelas (1-5)'
                            : q.type === 'nps_10'
                              ? '🔢 NPS (0-10)'
                              : q.type === 'boolean'
                                ? '👍 Sim/Não'
                                : q.type === 'multiple_choice'
                                  ? '🔘 Múltipla Escolha'
                                  : '✍️ Texto Livre'}
                        </span>
                      </div>
                      {q.helperText && (
                        <p className="text-[11px] text-slate-400">{q.helperText}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteQuestion(q.id)}
                    className="p-2 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors shrink-0"
                    title="Excluir Pergunta"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="xl:col-span-5 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
                <Smartphone className="w-4 h-4" />
                <span>Pré-Visualização do Convidado (Celular / Web)</span>
              </h3>
              <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-[#00e5ff] text-[10px] font-bold">
                Interativo
              </span>
            </div>
            <form onSubmit={handleSubmitPreviewTest} className="p-5 rounded-2xl bg-slate-950 border border-slate-800 space-y-4 max-h-[680px] overflow-y-auto scrollbar-thin">
              <div className="text-center space-y-1 pb-3 border-b border-slate-800">
                <div className="w-10 h-10 rounded-full bg-[#c5a059]/20 border border-[#c5a059]/40 mx-auto flex items-center justify-center text-[#c5a059] font-black text-sm">
                  ⚓
                </div>
                <h4 className="text-xs font-black text-[#c5a059] uppercase tracking-wider">
                  Marinha do Brasil
                </h4>
                <p className="text-[10px] text-slate-400 font-bold uppercase">
                  {currentLinkedEvento?.nome || currentSurvey?.title}
                </p>
              </div>
              {!currentSurvey?.allowAnonymous && (
                <div className="space-y-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
                  <label className="font-bold text-slate-300 block">Nome da Autoridade / Convidado:</label>
                  <input
                    type="text"
                    placeholder="Ex: CMG Silva Santos (ou deixe em branco p/ teste)"
                    value={previewAnswers.name}
                    onChange={(e) => setPreviewAnswers({ ...previewAnswers, name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                  />
                </div>
              )}
              {currentSurvey?.questions.map((q, idx) => (
                <div key={q.id} className="space-y-2 p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80">
                  <span className="text-xs font-bold text-white block">
                    {idx + 1}. {q.label} {q.required && <strong className="text-red-400">*</strong>}
                  </span>
                  {q.helperText && <p className="text-[10px] text-slate-400">{q.helperText}</p>}
                  {q.type === 'rating_5' && (
                    <div className="flex items-center gap-2 pt-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() =>
                            setPreviewAnswers({
                              ...previewAnswers,
                              ratings: { ...previewAnswers.ratings, [q.id]: star },
                            })
                          }
                          className={`p-1.5 rounded-lg transition-transform active:scale-90 ${
                            (previewAnswers.ratings[q.id] || 0) >= star
                              ? 'text-[#c5a059] scale-110'
                              : 'text-slate-600 hover:text-slate-400'
                          }`}
                        >
                          <Star className="w-5 h-5 fill-current" />
                        </button>
                      ))}
                      <span className="text-xs font-bold text-[#c5a059] ml-2">
                        {previewAnswers.ratings[q.id] ? `${previewAnswers.ratings[q.id]} / 5` : 'Selecione'}
                      </span>
                    </div>
                  )}
                  {q.type === 'nps_10' && (
                    <div className="space-y-1.5 pt-1">
                      <div className="grid grid-cols-11 gap-1">
                        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                          <button
                            key={num}
                            type="button"
                            onClick={() => setPreviewAnswers({ ...previewAnswers, nps: num })}
                            className={`py-1.5 rounded-lg text-[10px] font-bold font-mono transition-all ${
                              previewAnswers.nps === num
                                ? num >= 9
                                  ? 'bg-emerald-500 text-slate-950 font-black'
                                  : num >= 7
                                    ? 'bg-amber-500 text-slate-950 font-black'
                                    : 'bg-red-500 text-white font-black'
                                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                            }`}
                          >
                            {num}
                          </button>
                        ))}
                      </div>
                      <div className="flex justify-between text-[9px] text-slate-500 px-1">
                        <span>0 - Pouco provável</span>
                        <span>10 - Com certeza</span>
                      </div>
                    </div>
                  )}
                  {q.type === 'text' && (
                    <textarea
                      rows={2}
                      placeholder="Digite sua resposta..."
                      value={q.id === 'q_elogios' ? previewAnswers.comments : previewAnswers.suggestions}
                      onChange={(e) => {
                        if (q.id === 'q_elogios') {
                          setPreviewAnswers({ ...previewAnswers, comments: e.target.value });
                        } else {
                          setPreviewAnswers({ ...previewAnswers, suggestions: e.target.value });
                        }
                      }}
                      className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                    />
                  )}
                </div>
              ))}
              <button
                type="submit"
                className="w-full py-3 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#e5c07b] hover:from-[#d6b26b] hover:to-[#f0d08a] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/20 transition-all flex items-center justify-center gap-2 hover:scale-102"
              >
                <Send className="w-4 h-4" />
                <span>Enviar Avaliação (Testar Submissão)</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ── ABA 3: DISPAROS EM MASSA ── */}
      {activeSubTab === 'disparos' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-7 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-5 shadow-xl">
            <h3 className="text-xs font-black text-[#25D366] uppercase tracking-wider flex items-center gap-2">
              <Send className="w-4 h-4" />
              <span>Mensagem Oficial de Envio (WhatsApp & E-mail)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Utilize o modelo naval padronizado para convidar as autoridades presentes a responderem ao formulário.
            </p>
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs text-slate-300">
              <p className="text-emerald-400 font-bold">Prezado(a) Convidado(a) / Autoridade,</p>
              <p>
                O Comando-Geral do Corpo de Fuzileiros Navais agradece sua distinta presença em{' '}
                <strong className="text-white font-bold">{currentLinkedEvento?.nome || currentSurvey?.title}</strong>.
              </p>
              <p>
                Sua avaliação é fundamental para mantermos o padrão de excelência de nossas cerimônias. Por favor, responda à nossa breve pesquisa de satisfação (1 minuto):
              </p>
              <p className="text-cyan-400 underline font-bold">{surveyPublicUrl}</p>
              <p className="text-slate-500">_Comunicação Social • Gabinete CGCFN_<br />AD SUMUS!</p>
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={handleOpenWhatsApp}
                className="flex-1 py-3 px-4 rounded-xl bg-[#25D366] hover:bg-[#20bd5a] text-slate-950 font-black text-xs shadow-lg shadow-[#25D366]/20 transition-all flex items-center justify-center gap-2"
              >
                <Share2 className="w-4 h-4" />
                <span>Disparar via WhatsApp Web</span>
              </button>
              <button
                onClick={handleCopyLink}
                className="py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 transition-colors flex items-center gap-2"
              >
                <Copy className="w-4 h-4" />
                <span>Copiar Link</span>
              </button>
            </div>
          </div>
          <div className="xl:col-span-5 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl text-center">
            <h3 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center justify-center gap-2">
              <QrCode className="w-4 h-4" />
              <span>QR Code para Prismas de Mesa & Telões</span>
            </h3>
            <div className="p-6 rounded-2xl bg-white w-fit mx-auto shadow-xl">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(surveyPublicUrl)}`}
                alt="QR Code da Pesquisa"
                className="w-44 h-44 object-contain"
              />
            </div>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              Imprima este QR Code nos prismas de mesa ou exiba nos telões de encerramento do evento.
            </p>
            <button
              onClick={() => window.print()}
              className="py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-[#c5a059] border border-[#c5a059]/40 font-bold text-xs transition-colors"
            >
              Imprimir QR Code para Placas
            </button>
          </div>
        </div>
      )}

      {/* ── ABA 4: LISTA INDIVIDUAL DE RESPOSTAS ── */}
      {activeSubTab === 'respostas' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-5 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-xs font-black text-purple-400 uppercase tracking-wider flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                <span>Respostas & Comentários Recebidos ({currentSurveyResponses.length})</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Avaliações detalhadas enviadas pelos convidados.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative w-full sm:w-60">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Buscar por nome ou texto..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
              </div>
              <select
                value={filterNpsType}
                onChange={(e) => setFilterNpsType(e.target.value as any)}
                className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs font-bold text-white focus:outline-none"
              >
                <option value="todos">Todos os Índices</option>
                <option value="promotores">Promotores (NPS 9-10)</option>
                <option value="neutros">Neutros (NPS 7-8)</option>
                <option value="detratores">Detratores (NPS 0-6)</option>
              </select>
            </div>
          </div>
          {filteredResponses.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs bg-slate-950 rounded-2xl border border-slate-800 space-y-2">
              <p className="font-bold text-white">Nenhuma resposta encontrada.</p>
              <p className="text-slate-400">Quando os convidados enviarem respostas, elas serão listadas detalhadamente aqui.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredResponses.map((resp) => (
                <div
                  key={resp.id}
                  className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3 shadow-md"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-white">{resp.respondentName}</span>
                      {resp.respondentRank && (
                        <span className="px-2 py-0.2 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {resp.respondentRank}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      {resp.npsScore !== undefined && (
                        <span
                          className={`px-2 py-0.5 rounded-lg font-bold font-mono text-[11px] ${
                            resp.npsScore >= 9
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : resp.npsScore >= 7
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : 'bg-red-500/20 text-red-400 border border-red-500/40'
                          }`}
                        >
                          NPS: {resp.npsScore}/10
                        </span>
                      )}
                      <span className="text-slate-500 text-[10px]">{resp.answeredAt}</span>
                    </div>
                  </div>
                  {Object.keys(resp.ratings).length > 0 && (
                    <div className="flex items-center gap-3 flex-wrap text-[11px]">
                      {Object.entries(resp.ratings).map(([qKey, val]) => (
                        <span key={qKey} className="px-2 py-1 rounded bg-slate-950 text-slate-300 font-mono">
                          {qKey.replace('q_', '')}: <strong className="text-[#c5a059]">{val}⭐</strong>
                        </span>
                      ))}
                    </div>
                  )}
                  {resp.generalComments && (
                    <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-xl border border-slate-800 italic">
                      "{resp.generalComments}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── MODAL: NOVA PESQUISA ── */}
      {showNewSurveyModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-slate-700 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#00e5ff]" />
                <span>Criar Nova Pesquisa de Satisfação</span>
              </h3>
              <button
                onClick={() => setShowNewSurveyModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateSurvey} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-300 block mb-1">Título da Pesquisa:</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Pesquisa de Satisfação • Cerimônia de Passagem de Comando"
                  value={newSurveyData.title}
                  onChange={(e) => setNewSurveyData({ ...newSurveyData, title: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>
              <div>
                <label className="font-bold text-slate-300 block mb-1">Descrição / Instruções aos Convidados:</label>
                <textarea
                  rows={2}
                  placeholder="Ex: Sua avaliação é fundamental para o aprimoramento dos nossos eventos..."
                  value={newSurveyData.description}
                  onChange={(e) => setNewSurveyData({ ...newSurveyData, description: e.target.value })}
                  className="w-full p-3 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>
              <div>
                <label className="font-bold text-slate-300 block mb-1">
                  Vínculo com Evento do Cerimonial JADE (Opcional):
                </label>
                <select
                  value={newSurveyData.eventoId}
                  onChange={(e) => setNewSurveyData({ ...newSurveyData, eventoId: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  <option value="avulso">📋 Pesquisa Independente / Avulsa (Sem evento específico)</option>
                  {eventos.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      📅 {ev.nome} ({ev.data_evento})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewSurveyModal(false)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-xl bg-[#00e5ff] text-slate-950 font-black hover:bg-cyan-400 transition-all shadow-md shadow-[#00e5ff]/20"
                >
                  Criar Pesquisa
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: GERENCIAR PESQUISAS ── */}
      {showManageSurveysModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl p-6 rounded-3xl bg-[#0b1222] border border-slate-700 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                <Sliders className="w-4 h-4 text-[#c5a059]" />
                <span>Gerenciador de Pesquisas & Formulários Cadastrados</span>
              </h3>
              <button
                onClick={() => setShowManageSurveysModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
              {surveys.map((s) => {
                const respCount = responses.filter((r) => r.surveyId === s.id).length;
                return (
                  <div
                    key={s.id}
                    className={`p-4 rounded-2xl border transition-all flex items-center justify-between gap-3 ${
                      s.id === selectedSurveyId
                        ? 'bg-slate-900 border-[#c5a059]/60 shadow-md'
                        : 'bg-slate-950 border-slate-800'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-white">{s.title}</h4>
                        {s.id === selectedSurveyId && (
                          <span className="px-2 py-0.2 rounded bg-[#c5a059]/20 text-[#c5a059] text-[9px] font-bold">
                            Selecionada
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400">
                        {s.eventoNome} • {s.questions.length} perguntas •{' '}
                        <strong className="text-emerald-400">{respCount} respostas</strong>
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setSelectedSurveyId(s.id);
                          setShowManageSurveysModal(false);
                          toast.success(`Pesquisa "${s.title}" ativada.`);
                        }}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-[#c5a059] hover:text-slate-950 text-slate-300 font-bold text-xs transition-colors"
                      >
                        Abrir
                      </button>
                      {surveys.length > 1 && (
                        <button
                          onClick={() => handleDeleteSurvey(s.id, s.title)}
                          className="p-1.5 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                          title="Excluir Pesquisa"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: ADICIONAR PERGUNTA ── */}
      {showAddQuestionModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-slate-700 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#c5a059]" />
                <span>Adicionar Pergunta ao Formulário</span>
              </h3>
              <button
                onClick={() => setShowAddQuestionModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleAddQuestion} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-300 block mb-1">Texto da Pergunta:</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Como você avalia a organização geral do evento?"
                  value={newQuestionData.label || ''}
                  onChange={(e) => setNewQuestionData({ ...newQuestionData, label: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-400 block mb-1">Tipo de Resposta:</label>
                  <select
                    value={newQuestionData.type}
                    onChange={(e) => setNewQuestionData({ ...newQuestionData, type: e.target.value as QuestionType })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                  >
                    <option value="rating_5">⭐ Estrelas (1 a 5)</option>
                    <option value="nps_10">🔢 Escala NPS (0 a 10)</option>
                    <option value="text">✍️ Texto Livre / Dissertativa</option>
                    <option value="boolean">👍 Sim / Não</option>
                  </select>
                </div>
                <div>
                  <label className="font-bold text-slate-400 block mb-1">Categoria:</label>
                  <select
                    value={newQuestionData.category}
                    onChange={(e) => setNewQuestionData({ ...newQuestionData, category: e.target.value as QuestionCategory })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                  >
                    <option value="geral">Geral / Organização</option>
                    <option value="recepcao">Recepção & Acolhimento</option>
                    <option value="cerimonial">Cerimonial & Honras</option>
                    <option value="coquetel">Buffet & Coquetel</option>
                    <option value="audiovisual">Audiovisual & Mídia</option>
                    <option value="outros">Outros</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="font-bold text-slate-400 block mb-1">Texto de Ajuda / Subtítulo (Opcional):</label>
                <input
                  type="text"
                  placeholder="Ex: Pontualidade, clareza e atendimento."
                  value={newQuestionData.helperText || ''}
                  onChange={(e) => setNewQuestionData({ ...newQuestionData, helperText: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="req_check"
                  checked={Boolean(newQuestionData.required)}
                  onChange={(e) => setNewQuestionData({ ...newQuestionData, required: e.target.checked })}
                  className="rounded bg-slate-900 border-slate-700"
                />
                <label htmlFor="req_check" className="text-slate-300 font-bold cursor-pointer">
                  Resposta Obrigatória
                </label>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddQuestionModal(false)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2.5 rounded-xl bg-[#c5a059] text-slate-950 font-black hover:bg-[#d6b26b]"
                >
                  Inserir Pergunta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

