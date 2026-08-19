import React, { useState } from 'react';
import {
  HelpCircle,
  BookOpen,
  Keyboard,
  Shield,
  Sparkles,
  Zap,
  Layers,
  ArrowRight,
  ExternalLink,
  Mic,
  Camera,
  Armchair,
  Palette,
  Send,
  CheckCircle2,
  Lock,
  Tv,
  FileText,
  Users,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface WorkflowItem {
  id: string;
  title: string;
  category: string;
  icon: any;
  color: string;
  summary: string;
  steps: string[];
}

const WORKFLOWS: WorkflowItem[] = [
  {
    id: 'wf1',
    title: '1. Gestão, Solicitação & Homologação de Demandas',
    category: 'Gabinete & COMSOC',
    icon: Camera,
    color: 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10',
    summary: 'Fluxo completo desde a solicitação de cobertura até a aprovação pelo Chefe de Gabinete e escalação da equipe.',
    steps: [
      'O solicitante acessa "Nova Demanda" (/comsoc_demandas) e preenche os detalhes do evento (data/hora, local, tipo de cobertura e encarregado).',
      'O sistema notifica em tempo real a Web (sino + áudio com voz IA), o SisGAB TV e o grupo do Telegram.',
      'O Chefe de Gabinete ou Supervisor acessa "Homologar Demandas" (/comsoc_homologar), revisa a complexidade e clica em "Aprovar Pauta".',
      'Ao aprovar, os militares escalados recebem aviso imediato no privado do Telegram com detalhes da missão.',
    ],
  },
  {
    id: 'wf2',
    title: '2. Cerimonial, Alocação de Assentos & Placas JADE',
    category: 'Cerimonial & Protocolo',
    icon: Armchair,
    color: 'border-[#c5a059]/40 text-[#c5a059] bg-[#c5a059]/10',
    summary: 'Organização de auditórios, mesas de honra e confecção de prismas dobráveis A4 com QR Code.',
    steps: [
      'No "Almanaque de Autoridades" (/almanaque_autoridades), cadastre ou selecione as autoridades civis e militares.',
      'Acesse "Placas de Assento (Jade)" (/comsoc_assentos) para visualizar o dispositivo do palco e o grid do auditório.',
      'Vincule as autoridades às cadeiras ou clique em "+ Convidado & Acomp." para gerar automaticamente placas para acompanhantes.',
      'Na aba "Estúdio de Design JADE", selecione o modelo de prisma dobrável (4 por A4) e clique em "Imprimir Todas as Placas" ou "Marcar como Impressa".',
    ],
  },
  {
    id: 'wf3',
    title: '3. Notificações Multicanal, Voz IA ElevenLabs & Sinos',
    category: 'Comunicação & Áudio',
    icon: Mic,
    color: 'border-purple-500/40 text-purple-400 bg-purple-500/10',
    summary: 'Anúncios por voz em linguagem militar concisa com ElevenLabs e fallback neural automático.',
    steps: [
      'Em "Configurações, Voz IA & Alertas" (/config), insira sua chave gratuita do ElevenLabs e selecione a voz desejada (ex: Lucio, Antoni ou Rachel).',
      'Sempre que uma nova pauta for solicitada, o sistema falará: "Atenção Gabinete. Nova pauta solicitada: [Título]. Solicitante: [Setor]".',
      'Se a API da ElevenLabs estiver sem cota ou offline, o sistema ativa imediatamente o fallback de voz neural nativa (Google/Microsoft Brasil).',
      'O sino náutico oficial toca automaticamente nas horas cheias com badaladas navais de alta fidelidade.',
    ],
  },
  {
    id: 'wf4',
    title: '4. Estúdio de Design, Cardápios & Mala Direta ({tags})',
    category: 'Design & Impressão',
    icon: Palette,
    color: 'border-pink-500/40 text-pink-400 bg-pink-500/10',
    summary: 'Criação de cardápios frente e verso, crachás de portaria e diplomas mesclados em lote com 1 clique.',
    steps: [
      'Acesse "Estúdio de Design & Mala Direta" (/estudio_grafico) e escolha o formato (Cardápio A5, A4 Dobrável, Crachá A6 ou Certificado).',
      'Insira as tags dinâmicas como {nome}, {posto}, {cargo}, {assento}, {evento}, {entrada} e {prato_principal}.',
      'Para almoços oficiais, use a alternância "Frente / Verso" e clique em "Redigir com IA ✨" para sugerir o menu gastronômico.',
      'Na aba "Mala Direta / Lote", selecione o evento JADE e clique em "Imprimir Lote Completo" para gerar todas as páginas personalizadas.',
    ],
  },
  {
    id: 'wf5',
    title: '5. Galeria de Fotos, Curadoria & Biometria Facial Turbo',
    category: 'Acervo & Mídia',
    icon: Sparkles,
    color: 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10',
    summary: 'Publicação de coberturas em tempo real e entrega rápida (Hot Delivery) por reconhecimento facial.',
    steps: [
      'O operador COMSOC envia as fotos da cobertura para a pasta do Google Drive configurada.',
      'Na "Galeria & Acervo" (/comsoc_galeria), o SisGAB processa as miniaturas WebP ultra-leves e calcula os vetores faciais dos participantes.',
      'Os convidados acessam o link público do evento (/evento/ID), tiram uma selfie no celular e recebem instantaneamente todas as fotos em que aparecem.',
    ],
  },
  {
    id: 'wf6',
    title: '6. Quadro de Lógica, Permissões RBAC & Gestão do Bot',
    category: 'Segurança & Telegram',
    icon: Send,
    color: 'border-amber-500/40 text-amber-400 bg-amber-500/10',
    summary: 'Controle de acessos aos menus da sidebar e automações de mensagens do bot do Telegram.',
    steps: [
      'Em "Usuários & Matriz de Permissões" (/admin_panel), visualize a tabela de módulos x papéis militares e ajuste os acessos com 1 clique.',
      'Em "Gestão do Telegram & Bot" (/telegram_metrics), personalize os botões do teclado virtual do celular para cada categoria militar.',
      'Monitore os disparos automáticos da chamada matutina (07h), lembrete da tarde (15h) e briefing noturno (19h).',
    ],
  },
];

export const HelpAbout: React.FC = () => {
  const [expandedWf, setExpandedWf] = useState<string | null>('wf1');

  const toggleWf = (id: string) => {
    setExpandedWf(expandedWf === id ? null : id);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* ── HEADER PRINCIPAL ── */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
            Documentação Oficial & Manuais
          </span>
          <span className="text-slate-400 text-xs">• Guia Operacional do SisGAB v2.0</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Manual de Instruções & Fluxos de Trabalho
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm">
          Procedimentos detalhados para operação de demandas, cerimonial JADE, estúdio de design, voz IA e permissões.
        </p>
      </div>

      {/* ── BANNER DE CRÉDITO & AUTORIA ── */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-[#0b1426] via-[#121f3d] to-[#0b1426] border-2 border-[#c5a059]/50 shadow-2xl space-y-3 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-[#c5a059]/20 border border-[#c5a059] flex items-center justify-center text-2xl shadow-md">
              ⚓
            </div>
            <div>
              <span className="text-[10px] font-black text-[#c5a059] tracking-widest uppercase block">
                AUTORIA & DESENVOLVIMENTO
              </span>
              <h2 className="text-lg font-black text-white tracking-tight">
                🚀 Desenvolvido por Sargento Calaça 🇧🇷
              </h2>
              <p className="text-xs text-slate-300 font-medium">
                Gabinete do Comando-Geral do Corpo de Fuzileiros Navais (CGCFN)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="px-3 py-1 rounded-xl bg-slate-900 border border-slate-700 text-[#00e5ff] font-mono text-xs font-bold shadow-xs">
              SISGAB v2.0 • 2026
            </span>
          </div>
        </div>
      </div>

      {/* ── FLUXOS DE TRABALHO DETALHADOS (SANFONA / ACCORDION) ── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            <span>Guia Passo a Passo dos 6 Principais Fluxos de Trabalho</span>
          </h2>
          <span className="text-[11px] text-slate-500">Clique para expandir</span>
        </div>

        <div className="space-y-3">
          {WORKFLOWS.map((wf) => {
            const isExpanded = expandedWf === wf.id;
            const Icon = wf.icon;

            return (
              <div
                key={wf.id}
                className="rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-slate-700 overflow-hidden transition-all shadow-lg"
              >
                <button
                  type="button"
                  onClick={() => toggleWf(wf.id)}
                  className="w-full p-4 flex items-center justify-between gap-3 text-left transition-colors hover:bg-slate-900/60"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2.5 rounded-xl border ${wf.color}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                        {wf.category}
                      </span>
                      <h3 className="text-sm font-black text-white truncate">{wf.title}</h3>
                    </div>
                  </div>

                  <div className="p-1 text-slate-400">
                    {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </div>
                </button>

                {isExpanded && (
                  <div className="p-4 pt-1 border-t border-slate-800/80 bg-slate-950/50 space-y-3 text-xs animate-in fade-in duration-150">
                    <p className="text-slate-300 font-medium leading-relaxed">{wf.summary}</p>

                    <div className="space-y-2 pt-1">
                      <span className="text-[10px] font-black text-[#c5a059] uppercase tracking-wider block">
                        Passos Operacionais:
                      </span>
                      <ol className="space-y-2 list-none">
                        {wf.steps.map((step, idx) => (
                          <li key={idx} className="flex items-start gap-2.5 text-slate-300">
                            <span className="w-5 h-5 rounded-full bg-[#c5a059]/20 text-[#c5a059] font-bold text-[10px] flex items-center justify-center shrink-0 mt-0.5">
                              {idx + 1}
                            </span>
                            <span className="leading-relaxed">{step}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── ATALHOS DE TECLADO RÁPIDOS ── */}
      <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
        <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
          <Keyboard className="w-4 h-4" />
          <span>Atalhos de Teclado Globais</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-slate-300 font-bold">Busca Global & Navegação Rápida (Command Palette)</span>
            <kbd className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[#00e5ff] font-mono font-bold text-xs shadow-xs">
              Ctrl + K
            </kbd>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900 border border-slate-800">
            <span className="text-slate-300 font-bold">Fechar Modais, Telas e Janelas Flutuantes</span>
            <kbd className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 font-mono font-bold text-xs shadow-xs">
              ESC
            </kbd>
          </div>
        </div>
      </div>

      {/* ── ESPECIFICAÇÕES TÉCNICAS DA ARQUITETURA ── */}
      <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl text-xs text-slate-400">
        <h2 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-2">
          <Layers className="w-4 h-4 text-[#c5a059]" />
          <span>Especificações Técnicas da Plataforma</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <p className="font-bold text-white text-[11px]">Frontend React 19</p>
            <p className="text-[10px] text-slate-400 mt-0.5">TypeScript, Vite, Tailwind CSS e Canvas API</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <p className="font-bold text-white text-[11px]">Backend & Banco de Dados</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Supabase PostgreSQL com canais Realtime e Storage</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <p className="font-bold text-white text-[11px]">Voz IA & Biometria</p>
            <p className="text-[10px] text-slate-400 mt-0.5">ElevenLabs API, Web Speech API e Embeddings 512D</p>
          </div>
        </div>
      </div>

      {/* ── RODAPÉ DE CRÉDITOS ── */}
      <footer className="text-center py-4 text-xs space-y-1">
        <p className="font-bold text-[#c5a059]">🚀 Desenvolvido por Sargento Calaça 🇧🇷</p>
        <p className="text-[10px] text-slate-500">
          Comando-Geral do Corpo de Fuzileiros Navais • Assessoria de Comunicação Social • SisGAB 2.0
        </p>
      </footer>
    </div>
  );
};
