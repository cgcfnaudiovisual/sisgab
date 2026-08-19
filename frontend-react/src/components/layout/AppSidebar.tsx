import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ClipboardCheck,
  PlusCircle,
  Gavel,
  Kanban,
  Armchair,
  MailCheck,
  Gift,
  ShieldAlert,
  Bot,
  Mic,
  Clapperboard,
  Palette,
  Images,
  History,
  Cake,
  Tv,
  QrCode,
  BarChart3,
  Settings,
  UserCheck,
  HelpCircle,
  ChevronRight,
  LogOut,
  KeyRound,
  Sparkles,
  Star,
  Award,
  Send,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface MenuItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  subtitle: string;
  badge?: number;
  highlight?: boolean;
}

interface MenuCategory {
  title: string;
  items: MenuItem[];
}

export const MENU_CATEGORIES: MenuCategory[] = [
  {
    title: '🏛️ GABINETE & OPERAÇÕES DIÁRIAS',
    items: [
      {
        name: 'Painel de Comando',
        path: '/',
        icon: LayoutDashboard,
        subtitle: 'Agenda, KPIs e panorama geral',
      },
      {
        name: 'Chamada & Presença Diária',
        path: '/presenca',
        icon: ClipboardCheck,
        subtitle: 'Chamada matutina e Pronto do CheGab',
      },
      {
        name: 'Nova Demanda',
        path: '/comsoc_demandas',
        icon: PlusCircle,
        subtitle: 'Formulário de pautas e solicitações',
      },
      {
        name: 'Gestão de Demandas',
        path: '/comsoc_homologar',
        icon: Gavel,
        subtitle: 'Parecer e aprovação de pautas',
      },
    ],
  },
  {
    title: '🎯 TAREFAS & CERIMONIAL',
    items: [
      {
        name: 'Almanaque & Precedência',
        path: '/almanaque_autoridades',
        icon: Award,
        subtitle: 'Cadastro mestre de 400+ autoridades e precedência MB',
        highlight: true,
      },
      {
        name: 'Tarefas COMSOC (Kanban)',
        path: '/comsoc_tarefas',
        icon: Kanban,
        subtitle: 'Quadro de tarefas e fluxo criativo',
      },
      {
        name: 'Placas de Assento (Jade)',
        path: '/comsoc_assentos',
        icon: Armchair,
        subtitle: 'Mapa interativo e alocação de auditório',
        highlight: true,
      },
      {
        name: 'Gestão de Convites & RSVP',
        path: '/comsoc_rsvp',
        icon: MailCheck,
        subtitle: 'Convites formais, portaria e check-in',
      },
      {
        name: 'Pesquisa de Satisfação',
        path: '/pesquisa_satisfacao',
        icon: Star,
        subtitle: 'Avaliação pós-evento e NPS',
        highlight: true,
      },
    ],
  },
  {
    title: '📦 LOGÍSTICA & MATERIAL',
    items: [
      {
        name: 'Estoque de Brindes',
        path: '/comsoc_brindes',
        icon: Gift,
        subtitle: 'Controle de brindes do RP',
      },
      {
        name: 'Cautela de Material',
        path: '/comsoc_cautela',
        icon: ShieldAlert,
        subtitle: 'Empréstimos de equipamentos',
      },
    ],
  },
  {
    title: '📣 COMUNICAÇÃO & MÍDIA',
    items: [
      {
        name: 'Central de IA',
        path: '/assistente_ia',
        icon: Bot,
        subtitle: 'Chat, redator e triagem de demandas',
      },
      {
        name: 'Jarvis Voz',
        path: '/jarvis',
        icon: Mic,
        subtitle: 'Assistente por voz em tempo real',
      },
      {
        name: 'Smart Editor IA',
        path: '/smart_editor',
        icon: Clapperboard,
        subtitle: 'Cortes com IA, SFX e FCPXML',
      },
      {
        name: 'Estúdio de Design & Mala Direta',
        path: '/estudio_grafico',
        icon: Palette,
        subtitle: 'Cardápios, prismas, crachás e lotes {tags}',
        highlight: true,
      },
      {
        name: 'Carrossel Instagram & IA',
        path: '/carrossel_instagram',
        icon: Sparkles,
        subtitle: 'Carrosséis 1080×1350 com IA e fotos',
        highlight: true,
      },
      {
        name: 'Galeria & Acervo Fotos',
        path: '/comsoc_galeria',
        icon: Images,
        subtitle: 'Visualizador, curadoria e biometria',
        highlight: true,
      },
      {
        name: 'Arquivo & Histórico',
        path: '/comsoc_historico',
        icon: History,
        subtitle: 'Busca de coberturas passadas',
      },
      {
        name: 'Aniversariantes & Datas',
        path: '/comsoc_aniversariantes',
        icon: Cake,
        subtitle: 'Mensagens com IA e impressão',
      },
      {
        name: 'Monitor TV (SisGAB TV)',
        path: '/sisgab_tv',
        icon: Tv,
        subtitle: 'Modo TV tático em tela cheia',
      },
      {
        name: 'Gerador de QR Code',
        path: '/qrcode_generator',
        icon: QrCode,
        subtitle: 'Gerar QR Codes para links e eventos',
      },
    ],
  },
  {
    title: '⚙️ SISTEMA & ADMINISTRAÇÃO',
    items: [
      {
        name: 'Gestão do Telegram & Bot',
        path: '/telegram_metrics',
        icon: Send,
        subtitle: 'Menus por categoria, automações e métricas',
        highlight: true,
      },
      {
        name: 'Configurações, Voz IA & Alertas',
        path: '/config',
        icon: Settings,
        subtitle: 'API ElevenLabs, Sinos Navais e Parâmetros',
        highlight: true,
      },
      {
        name: 'Usuários & Matriz de Permissões',
        path: '/admin_panel',
        icon: UserCheck,
        subtitle: 'Quadro de lógica RBAC e efetivo',
        highlight: true,
      },
      {
        name: 'Ajuda & Manuais',
        path: '/ajuda_sobre',
        icon: HelpCircle,
        subtitle: 'Manuais operacionais e suporte',
      },
    ],
  },
];

interface AppSidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-xs z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-72 bg-[#080d1a] border-r border-[#c5a059]/20 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Branding */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-[#c5a059]/15 bg-[#0b1222]">
          <div className="flex items-center gap-3">
            <img
              src="/brasaocgcfn.png"
              alt="Brasão CGCFN"
              className="w-10 h-10 object-contain drop-shadow-[0_0_8px_rgba(197,160,89,0.5)] shrink-0"
            />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-black text-[#c5a059] tracking-wider text-sm cyber-title">SISGAB</span>
                <span className="px-1.5 py-0.2 bg-[#00e5ff]/10 text-[#00e5ff] text-[10px] font-bold rounded border border-[#00e5ff]/30">
                  2.0
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium leading-none">Comunicação Social • CGCFN</p>
            </div>
          </div>
        </div>

        {/* Scrollable Navigation */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-5">
          {MENU_CATEGORIES.map((cat, idx) => (
            <div key={idx} className="space-y-1">
              <div className="px-2 py-1 flex items-center gap-2">
                <span className="text-[10px] font-bold tracking-wider text-[#c5a059] uppercase">
                  {cat.title}
                </span>
              </div>

              <div className="space-y-0.5">
                {cat.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => {
                        if (window.innerWidth < 1024 && onClose) onClose();
                      }}
                      className={`group flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-all ${
                        isActive
                          ? 'bg-[#c5a059]/15 text-[#e5c07b] font-semibold border border-[#c5a059]/40 shadow-sm shadow-[#c5a059]/10'
                          : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon
                          className={`w-4 h-4 shrink-0 transition-transform group-hover:scale-110 ${
                            isActive ? 'text-[#c5a059]' : 'text-slate-400 group-hover:text-slate-200'
                          }`}
                        />
                        <div className="truncate">
                          <p className="truncate text-xs">{item.name}</p>
                          <p className="text-[9.5px] text-slate-500 truncate leading-tight group-hover:text-slate-400">
                            {item.subtitle}
                          </p>
                        </div>
                      </div>

                      {item.highlight && (
                        <span className="ml-1 px-1 py-0.2 bg-[#00e5ff]/20 text-[#00e5ff] text-[9px] rounded font-bold shrink-0">
                          PRO
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Footer */}
        <div className="p-3 border-t border-slate-800 bg-[#060a14] space-y-2 shrink-0">
          <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 rounded-full bg-slate-800 border border-[#c5a059]/40 flex items-center justify-center text-xs font-bold text-[#c5a059]">
                {user?.nome_guerra ? user.nome_guerra.slice(0, 2) : 'OP'}
              </div>
              <div className="truncate">
                <p className="text-[11px] font-bold text-slate-200 truncate">{user?.nome_guerra || 'Operador'}</p>
                <p className="text-[9px] text-[#c5a059] uppercase font-semibold truncate">{user?.posto || 'Militar'}</p>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sair do Sistema"
              className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          {/* Créditos Oficiais no Rodapé da Sidebar */}
          <div className="pt-2 text-center border-t border-slate-800/60">
            <p className="text-[10px] font-bold text-[#c5a059] tracking-wider opacity-90">
              🚀 Desenvolvido por Sargento Calaça 🇧🇷
            </p>
            <p className="text-[9px] text-slate-500 font-mono mt-0.5">
              SisGAB v2.0 • CGCFN
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
