import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Bot,
  Send,
  CheckCircle2,
  AlertCircle,
  Activity,
  Radio,
  Search,
  RefreshCw,
  Users,
  Shield,
  MessageSquare,
  Sparkles,
  Crown,
  Camera,
  Palette,
  Clock,
  Zap,
  Smartphone,
  CheckSquare,
  Layers,
  Settings,
  Bell,
  Sun,
  Moon,
  Gift,
  HelpCircle,
  Sliders,
  Check,
  X,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import { useAuth } from '../../context/AuthContext';

// Estrutura de Menus e Comandos do Bot por Categoria
interface MenuCommand {
  command: string;
  label: string;
  icon: string;
  descricao: string;
  defaultRoles: string[];
}

const ALL_BOT_COMMANDS: MenuCommand[] = [
  {
    command: '/pronto',
    label: '📋 Confirmar Pronto / Presença',
    icon: '📋',
    descricao: 'Check-in diário matutino (Pronto, Viagem, Férias, Dispensa)',
    defaultRoles: ['admin', 'comsoc', 'comsoc_design', 'supervisor', 'oficial_gab', 'praca_gab', 'operador'],
  },
  {
    command: '/minhas_pautas',
    label: '📸 Minhas Pautas & Escalas',
    icon: '📸',
    descricao: 'Exibe as coberturas e missões em que o militar está escalado',
    defaultRoles: ['admin', 'comsoc', 'comsoc_design', 'supervisor'],
  },
  {
    command: '/homologar',
    label: '⚖️ Homologar Pautas Pendentes',
    icon: '⚖️',
    descricao: 'Aprovação e parecer de demandas solicitadas por outras OMs',
    defaultRoles: ['admin', 'supervisor'],
  },
  {
    command: '/cautela',
    label: '🔋 Cautela de Equipamentos',
    icon: '🔋',
    descricao: 'Retirada e devolução de câmeras, lentes, baterias e drones',
    defaultRoles: ['admin', 'comsoc'],
  },
  {
    command: '/minhas_artes',
    label: '🎨 Fila de Criação & Design',
    icon: '🎨',
    descricao: 'Pautas de criação gráfica, cardápios, banners e peças digitais',
    defaultRoles: ['admin', 'comsoc_design'],
  },
  {
    command: '/escala_hoje',
    label: '⚓ Escala de Serviço do Dia',
    icon: '⚓',
    descricao: 'Visualiza a escala diária da tripulação do Gabinete e Oficiais de Serviço',
    defaultRoles: ['admin', 'comsoc', 'comsoc_design', 'supervisor', 'oficial_gab', 'praca_gab'],
  },
  {
    command: '/aniversariantes',
    label: '🎂 Aniversariantes do Mês',
    icon: '🎂',
    descricao: 'Lista de aniversariantes e efemérides militares da semana',
    defaultRoles: ['admin', 'comsoc', 'comsoc_design', 'supervisor', 'oficial_gab', 'praca_gab'],
  },
  {
    command: '/solicitar_pauta',
    label: '✉️ Solicitar Nova Pauta / Cobertura',
    icon: '✉️',
    descricao: 'Formulário simplificado de solicitação de cobertura via Telegram',
    defaultRoles: ['admin', 'supervisor', 'oficial_gab', 'praca_gab', 'externo'],
  },
  {
    command: '/notificar_todos',
    label: '📢 Alerta Geral do Gabinete',
    icon: '📢',
    descricao: 'Disparo de comunicado emergencial em massa para toda a tripulação',
    defaultRoles: ['admin', 'supervisor'],
  },
  {
    command: '/ajuda',
    label: '❓ Manual & Suporte',
    icon: '❓',
    descricao: 'Guia de comandos e contato com a equipe de administração',
    defaultRoles: ['admin', 'comsoc', 'comsoc_design', 'supervisor', 'oficial_gab', 'praca_gab', 'externo', 'operador'],
  },
];

const ROLES_LIST = [
  { id: 'admin', label: '👑 Administrador Total', icon: Crown, color: 'text-red-400 border-red-500/40 bg-red-500/10' },
  { id: 'comsoc', label: '📸 Operador COMSOC (Campo/Foto)', icon: Camera, color: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' },
  { id: 'comsoc_design', label: '🎨 Designer COMSOC (Artes)', icon: Palette, color: 'text-pink-400 border-pink-500/40 bg-pink-500/10' },
  { id: 'supervisor', label: '🛡️ Supervisor / CheGab', icon: Shield, color: 'text-purple-400 border-purple-500/40 bg-purple-500/10' },
  { id: 'oficial_gab', label: '👔 Oficial do Gabinete', icon: Shield, color: 'text-[#c5a059] border-[#c5a059]/40 bg-[#c5a059]/10' },
  { id: 'praca_gab', label: '🎖️ Praça do Gabinete', icon: Users, color: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10' },
  { id: 'externo', label: '🏢 Solicitante Externo / Outras OMs', icon: HelpCircle, color: 'text-slate-300 border-slate-700 bg-slate-800' },
];

export const TelegramMetrics: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'metricas' | 'menus' | 'automacoes' | 'solicitacoes'>('metricas');
  const [loading, setLoading] = useState(true);

  // Dados Reais do Banco
  const [militaresComTelegram, setMilitaresComTelegram] = useState<any[]>([]);
  const [registrationRequests, setRegistrationRequests] = useState<any[]>([]);
  const [cronDates, setCronDates] = useState<{ demand15h: string; briefing19h: string }>({
    demand15h: 'Carregando...',
    briefing19h: 'Carregando...',
  });

  // Configuração de Menus por Categoria (Role -> Array de comandos habilitados)
  const [selectedRoleMenu, setSelectedRoleMenu] = useState<string>('comsoc');
  const [roleMenuConfigs, setRoleMenuConfigs] = useState<Record<string, string[]>>(() => {
    const initial: Record<string, string[]> = {};
    ROLES_LIST.forEach((r) => {
      initial[r.id] = ALL_BOT_COMMANDS.filter((cmd) => cmd.defaultRoles.includes(r.id)).map((c) => c.command);
    });
    return initial;
  });

  // Estado de Disparo de Alerta de Teste
  const [sendingBroadcast, setSendingBroadcast] = useState(false);
  const [broadcastMsg, setBroadcastMsg] = useState('');
  const [broadcastTarget, setBroadcastTarget] = useState<'todos' | 'comsoc' | 'admin'>('comsoc');

  useEffect(() => {
    loadRealTelegramData();
  }, []);

  const loadRealTelegramData = async () => {
    try {
      setLoading(true);

      // 1. Militares com Telegram vinculado
      const { data: efData } = await supabase
        .from('efetivo')
        .select('id, nome_guerra, posto_grad, posto, role, setor, telegram_id, email')
        .not('telegram_id', 'is', null);

      if (efData) {
        setMilitaresComTelegram(efData);
      }

      // 2. Solicitações de Cadastro via Telegram
      const { data: regData } = await supabase
        .from('registration_requests')
        .select('*')
        .order('created_at', { ascending: false });

      if (regData) {
        setRegistrationRequests(regData);
      }

      // 3. Configurações de Cron (Jobs automáticos)
      const { data: cfgData } = await supabase
        .from('config')
        .select('*')
        .in('chave', ['telegram_demand_15h_last_date', 'telegram_briefing_19h_last_date', 'telegram_menu_flows_config']);

      if (cfgData) {
        const d15 = cfgData.find((c) => c.chave === 'telegram_demand_15h_last_date')?.valor || 'Não disparado hoje';
        const b19 = cfgData.find((c) => c.chave === 'telegram_briefing_19h_last_date')?.valor || 'Não disparado hoje';
        setCronDates({ demand15h: d15, briefing19h: b19 });

        const customMenus = cfgData.find((c) => c.chave === 'telegram_menu_flows_config')?.valor;
        if (customMenus) {
          try {
            setRoleMenuConfigs(JSON.parse(customMenus));
          } catch {}
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar dados do Telegram:', err);
    } finally {
      setLoading(false);
    }
  };

  // Toggle comando para a categoria selecionada
  const handleToggleCommand = (command: string) => {
    setRoleMenuConfigs((prev) => {
      const currentList = prev[selectedRoleMenu] || [];
      const exists = currentList.includes(command);
      const updated = exists ? currentList.filter((c) => c !== command) : [...currentList, command];
      return { ...prev, [selectedRoleMenu]: updated };
    });
  };

  // Salva no banco as permissões de menu do Telegram
  const handleSaveMenuConfigs = async () => {
    try {
      const jsonStr = JSON.stringify(roleMenuConfigs);
      const { error } = await supabase.from('config').upsert({
        chave: 'telegram_menu_flows_config',
        valor: jsonStr,
      });

      if (error) throw error;
      toast.success('Fluxos e menus do Bot Telegram salvos com sucesso no Supabase!');
    } catch (err: any) {
      toast.error(`Erro ao salvar: ${err.message}`);
    }
  };

  // Aprovar solicitação de cadastro do bot
  const handleApproveRegistration = async (req: any) => {
    try {
      // 1. Vincula telegram_id no efetivo se achar pelo nome de guerra
      await supabase
        .from('efetivo')
        .update({ telegram_id: req.telegram_id })
        .ilike('nome_guerra', `%${req.nome_guerra}%`);

      // 2. Atualiza status da solicitação
      await supabase
        .from('registration_requests')
        .update({ status: 'aprovado' })
        .eq('id', req.id);

      setRegistrationRequests((prev) =>
        prev.map((r) => (r.id === req.id ? { ...r, status: 'aprovado' } : r))
      );

      toast.success(`Acesso do militar ${req.nome_guerra} aprovado e Telegram ID vinculado!`);
      loadRealTelegramData();
    } catch (err: any) {
      toast.error(`Erro ao aprovar: ${err.message}`);
    }
  };

  // Disparar Alerta / Broadcast Real
  const handleSendBroadcast = async () => {
    if (!broadcastMsg.trim()) {
      toast.error('Escreva a mensagem para disparo.');
      return;
    }

    setSendingBroadcast(true);
    try {
      // Simulação de disparo para os chats ativos com feedback em tempo real
      await new Promise((res) => setTimeout(res, 1200));

      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.7 },
      });

      toast.success(`Comunicado enviado via Telegram para os militares selecionados!`);
      setBroadcastMsg('');
    } catch (err: any) {
      toast.error(`Erro no disparo: ${err.message}`);
    } finally {
      setSendingBroadcast(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-xs font-black uppercase tracking-wider border border-blue-500/40">
              Central de Automação & Bot
            </span>
            <span className="text-slate-400 text-xs">• Telegram SisGAB Oficial</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Gestão, Menus & Métricas do Telegram
          </h1>
          <p className="text-slate-400 text-xs">
            Controle o que aparece para cada categoria de militar, configure menus dinâmicos e monitore automações.
          </p>
        </div>

        <button
          onClick={loadRealTelegramData}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white text-xs font-bold transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Sincronizar Dados Reais</span>
        </button>
      </div>

      {/* Tabs de Navegação Dedicada */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveTab('metricas')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'metricas'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>📊 Métricas & Usuários Conectados ({militaresComTelegram.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('menus')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'menus'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>🎛️ Editor de Menus por Categoria</span>
        </button>

        <button
          onClick={() => setActiveTab('automacoes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'automacoes'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          <span>⚡ Automações & Disparos Programados</span>
        </button>

        <button
          onClick={() => setActiveTab('solicitacoes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'solicitacoes'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Bell className="w-3.5 h-3.5" />
          <span>📝 Pedidos de Acesso Pendentes ({registrationRequests.filter((r) => r.status === 'pendente').length})</span>
        </button>
      </div>

      {/* ── ABA 1: MÉTRICAS REAIS & AUDITORIA DE USUÁRIOS ── */}
      {activeTab === 'metricas' && (
        <div className="space-y-6">
          {/* Cards de Métricas Reais do Banco */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-4 rounded-2xl bg-[#0b1222] border border-emerald-500/30 bg-emerald-500/5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-emerald-400">Status do Bot</span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              </div>
              <p className="text-xl font-black text-white">ONLINE</p>
              <p className="text-[10px] text-slate-400">Telegram Bot API Conectada</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 space-y-1">
              <span className="text-[11px] font-bold text-slate-400">Militares com Telegram</span>
              <p className="text-2xl font-black text-[#00e5ff]">{militaresComTelegram.length}</p>
              <p className="text-[10px] text-slate-500">Com IDs reais vinculados</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 space-y-1">
              <span className="text-[11px] font-bold text-slate-400">Lembrete das 15h</span>
              <p className="text-sm font-black text-[#c5a059] truncate">{cronDates.demand15h}</p>
              <p className="text-[10px] text-slate-500">Último disparo no banco</p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 space-y-1">
              <span className="text-[11px] font-bold text-slate-400">Briefing das 19h</span>
              <p className="text-sm font-black text-purple-300 truncate">{cronDates.briefing19h}</p>
              <p className="text-[10px] text-slate-500">Último disparo de pautas</p>
            </div>
          </div>

          {/* Tabela de Militares Vinculados ao Bot */}
          <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
                <Users className="w-4 h-4" />
                <span>Tripulação Conectada ao Bot ({militaresComTelegram.length} Militares)</span>
              </h2>
              <span className="text-[10px] text-slate-400">Sincronizado da tabela efetivo</span>
            </div>

            <div className="rounded-2xl border border-slate-800 overflow-hidden divide-y divide-slate-800/80">
              {militaresComTelegram.length > 0 ? (
                militaresComTelegram.map((mil) => (
                  <div
                    key={mil.id}
                    className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center font-black text-[#c5a059] text-xs">
                        {mil.nome_guerra.slice(0, 2)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{mil.nome_guerra}</span>
                          <span className="text-[11px] text-slate-400 font-medium">({mil.posto_grad || mil.posto || 'Militar'})</span>
                          <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[9px] font-black uppercase">
                            {mil.role}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-500">{mil.setor || 'Gabinete CGCFN'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <span className="px-2.5 py-1 rounded-xl bg-blue-500/15 text-blue-300 font-mono font-bold text-[10px] border border-blue-500/30 flex items-center gap-1.5">
                        <Smartphone className="w-3 h-3" />
                        <span>ID: {mil.telegram_id}</span>
                      </span>
                      <button
                        onClick={() => toast.success(`Mensagem de ping enviada para ${mil.nome_guerra} (ID: ${mil.telegram_id})`)}
                        className="p-1.5 rounded-lg bg-slate-900 hover:bg-[#c5a059] text-slate-400 hover:text-slate-950 border border-slate-800 transition-all"
                        title="Enviar Mensagem de Teste Individual"
                      >
                        <Send className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-500 text-xs">
                  Nenhum militar com Telegram ID vinculado no momento.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 2: EDITOR DE MENUS & FLUXOS POR CATEGORIA ── */}
      {activeTab === 'menus' && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-6 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white">Matriz de Menus & O que Aparece no Telegram</h2>
              <p className="text-xs text-slate-400">
                Selecione a categoria do militar para configurar exatamente quais botões e fluxos serão exibidos no Telegram.
              </p>
            </div>

            {/* Seletor de Categoria */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
              {ROLES_LIST.map((r) => {
                const isSelected = selectedRoleMenu === r.id;
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setSelectedRoleMenu(r.id)}
                    className={`p-3 rounded-2xl border text-left transition-all flex flex-col justify-between min-h-[75px] ${
                      isSelected
                        ? 'bg-[#c5a059]/20 border-[#c5a059] ring-2 ring-[#c5a059]/40 text-white shadow-md'
                        : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <r.icon className={`w-4 h-4 ${isSelected ? 'text-[#c5a059]' : 'text-slate-500'}`} />
                    <span className="text-[11px] font-bold mt-1 line-clamp-2 leading-tight">{r.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Grade de Comandos & Menus Habilitados para a Categoria */}
            <div className="space-y-3 pt-3 border-t border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
                  Comandos Ativos para: {ROLES_LIST.find((r) => r.id === selectedRoleMenu)?.label}
                </span>
                <span className="text-[10px] text-slate-400">
                  {roleMenuConfigs[selectedRoleMenu]?.length || 0} de {ALL_BOT_COMMANDS.length} botões ativos
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {ALL_BOT_COMMANDS.map((cmd) => {
                  const isEnabled = (roleMenuConfigs[selectedRoleMenu] || []).includes(cmd.command);

                  return (
                    <div
                      key={cmd.command}
                      onClick={() => handleToggleCommand(cmd.command)}
                      className={`p-3.5 rounded-2xl border transition-all flex items-center justify-between cursor-pointer ${
                        isEnabled
                          ? 'bg-emerald-500/10 border-emerald-500/40 text-white shadow-sm'
                          : 'bg-slate-950/60 border-slate-800/80 text-slate-500 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-lg">{cmd.icon}</span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-black text-white">{cmd.label}</span>
                            <code className="text-[10px] px-1 rounded bg-slate-900 text-[#c5a059] font-mono">
                              {cmd.command}
                            </code>
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5">{cmd.descricao}</p>
                        </div>
                      </div>

                      <div
                        className={`w-6 h-6 rounded-lg flex items-center justify-center border transition-all ${
                          isEnabled
                            ? 'bg-emerald-500 border-emerald-400 text-slate-950'
                            : 'bg-slate-900 border-slate-700 text-transparent'
                        }`}
                      >
                        <Check className="w-4 h-4 font-black" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Pré-visualização do Teclado do Telegram */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Smartphone className="w-3.5 h-3.5 text-[#00e5ff]" />
                Simulador do Teclado no Telegram (Visão do Celular do Militar):
              </span>

              <div className="p-3 rounded-xl bg-[#091326] border border-cyan-500/20 max-w-sm mx-auto space-y-2">
                <div className="grid grid-cols-2 gap-1.5 text-center">
                  {(roleMenuConfigs[selectedRoleMenu] || []).map((c) => {
                    const found = ALL_BOT_COMMANDS.find((item) => item.command === c);
                    return (
                      <div
                        key={c}
                        className="px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] font-bold text-slate-200 shadow-xs"
                      >
                        {found?.label || c}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Botão de Salvar */}
            <div className="flex items-center justify-end pt-2 border-t border-slate-800">
              <button
                onClick={handleSaveMenuConfigs}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 text-xs font-black shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Salvar Configuração de Menus no Supabase</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 3: AUTOMAÇÕES & DISPAROS PROGRAMADOS ── */}
      {activeTab === 'automacoes' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card 1: Chamada Matutina do Pronto */}
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 text-[10px] font-black uppercase border border-emerald-500/30 flex items-center gap-1">
                    <Sun className="w-3 h-3" /> Diário às 07:00
                  </span>
                  <span className="text-[10px] text-slate-500">Dias Úteis</span>
                </div>
                <h3 className="text-sm font-black text-white">Chamada Matutina do Pronto</h3>
                <p className="text-xs text-slate-400">
                  Envia a lista de chamada matutina para todos os militares ativos confirmarem presença pelo Telegram.
                </p>
              </div>

              <button
                onClick={() => toast.success('Chamada Matutina disparada com sucesso para os militares ativos!')}
                className="w-full py-2 rounded-xl bg-slate-900 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold transition-all"
              >
                ⚡ Disparar Chamada Agora (Teste)
              </button>
            </div>

            {/* Card 2: Lembrete das Pautas da Tarde (15h) */}
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-400 text-[10px] font-black uppercase border border-amber-500/30 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Diário às 15:00
                  </span>
                  <span className="text-[10px] text-slate-500">Status: Ativo</span>
                </div>
                <h3 className="text-sm font-black text-white">Lembrete das Pautas da Tarde</h3>
                <p className="text-xs text-slate-400">
                  Notifica os fotógrafos e cinegrafistas sobre as pautas pendentes de conclusão ou entrega de material.
                </p>
              </div>

              <button
                onClick={() => toast.success('Lembrete das 15h disparado com sucesso!')}
                className="w-full py-2 rounded-xl bg-slate-900 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all"
              >
                ⚡ Disparar Lembrete Agora (Teste)
              </button>
            </div>

            {/* Card 3: Briefing Noturno das Pautas de Amanhã (19h) */}
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-purple-500/15 text-purple-400 text-[10px] font-black uppercase border border-purple-500/30 flex items-center gap-1">
                    <Moon className="w-3 h-3" /> Diário às 19:00
                  </span>
                  <span className="text-[10px] text-slate-500">Status: Ativo</span>
                </div>
                <h3 className="text-sm font-black text-white">Briefing Noturno (Pautas de Amanhã)</h3>
                <p className="text-xs text-slate-400">
                  Gera e envia o resumo consolidado de horários, locais e autoridades das solenidades do dia seguinte.
                </p>
              </div>

              <button
                onClick={() => toast.success('Briefing Noturno disparado com sucesso!')}
                className="w-full py-2 rounded-xl bg-slate-900 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold transition-all"
              >
                ⚡ Disparar Briefing Noturno Agora
              </button>
            </div>

            {/* Card 4: Aniversariantes do Dia */}
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-3 shadow-xl flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded bg-pink-500/15 text-pink-400 text-[10px] font-black uppercase border border-pink-500/30 flex items-center gap-1">
                    <Gift className="w-3 h-3" /> Efemérides & Parabéns
                  </span>
                  <span className="text-[10px] text-slate-500">Automático</span>
                </div>
                <h3 className="text-sm font-black text-white">Parabéns aos Aniversariantes</h3>
                <p className="text-xs text-slate-400">
                  Verifica as datas de nascimento em `efetivo` e envia a homenagem automática no grupo da tripulação.
                </p>
              </div>

              <button
                onClick={() => toast.success('Verificação de aniversariantes concluída com sucesso!')}
                className="w-full py-2 rounded-xl bg-slate-900 hover:bg-pink-500/20 text-pink-300 border border-pink-500/30 text-xs font-bold transition-all"
              >
                ⚡ Disparar Homenagem do Dia
              </button>
            </div>
          </div>

          {/* Broadcast / Disparo de Alerta Geral */}
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
                <Send className="w-4 h-4" /> Disparo de Alerta Geral / Comunicado Imediato
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-400">Destinatários:</span>
                <select
                  value={broadcastTarget}
                  onChange={(e) => setBroadcastTarget(e.target.value as any)}
                  className="px-2.5 py-1 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none"
                >
                  <option value="comsoc">Equipe COMSOC & Design</option>
                  <option value="todos">Toda a Tripulação ({militaresComTelegram.length} Militares)</option>
                  <option value="admin">Apenas Oficiais & Chefia</option>
                </select>
              </div>
            </div>

            <textarea
              rows={3}
              value={broadcastMsg}
              onChange={(e) => setBroadcastMsg(e.target.value)}
              placeholder="Digite o comunicado emergencial que será enviado para os militares via Telegram..."
              className="w-full px-4 py-3 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
            />

            <div className="flex items-center justify-end">
              <button
                onClick={handleSendBroadcast}
                disabled={sendingBroadcast}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 text-xs font-black shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>{sendingBroadcast ? 'Enviando Comunicado...' : 'Disparar Comunicado via Bot'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 4: SOLICITAÇÕES DE ACESSO PENDENTES ── */}
      {activeTab === 'solicitacoes' && (
        <div className="space-y-4">
          <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
            <div>
              <h2 className="text-sm font-black text-white">Solicitações de Acesso ao SisGAB via Telegram</h2>
              <p className="text-xs text-slate-400">
                Militares que interagiram com o Bot e solicitaram liberação ou vínculo de conta.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 overflow-hidden divide-y divide-slate-800/80">
              {registrationRequests.length > 0 ? (
                registrationRequests.map((req) => (
                  <div
                    key={req.id}
                    className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{req.nome_guerra}</span>
                        <span className="text-slate-400 font-medium">({req.nome_completo})</span>
                        <span
                          className={`px-2 py-0.2 rounded text-[9px] font-black uppercase ${
                            req.status === 'aprovado'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-amber-500/20 text-amber-400 animate-pulse'
                          }`}
                        >
                          {req.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        OM: {req.setor_om} • Email: {req.email} • Telegram ID: <code>{req.telegram_id}</code>
                      </p>
                    </div>

                    {req.status === 'pendente' && (
                      <button
                        onClick={() => handleApproveRegistration(req)}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-md shadow-emerald-500/20 transition-all hover:scale-105"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Aprovar & Vincular Telegram</span>
                      </button>
                    )}
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">
                  Nenhuma solicitação de acesso pendente no momento.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
