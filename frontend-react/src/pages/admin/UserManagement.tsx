import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  Plus,
  Search,
  Shield,
  Key,
  Edit2,
  Trash2,
  CheckCircle2,
  Lock,
  Sparkles,
  Send,
  MessageSquare,
  X,
  Smartphone,
  Layers,
  Crown,
  Camera,
  Palette,
  Check,
  Save,
  RotateCcw,
  Sliders,
  AlertTriangle,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { UserProfile, UserRole } from '../../types/database';

export interface MilitarCompleto {
  id: string;
  nome_guerra: string;
  posto_grad?: string;
  posto?: string;
  role: UserRole;
  setor?: string;
  email?: string;
  telegram_id?: string | number | null;
  url_foto?: string;
}

const ROLES_LIST: { id: UserRole; label: string; color: string; icon: any; desc: string }[] = [
  { id: 'admin', label: 'Administrador Total', color: 'bg-red-500/20 text-red-400 border-red-500/40', icon: Crown, desc: 'Acesso total e irrestrito a todos os módulos e parâmetros' },
  { id: 'supervisor', label: 'Supervisor / CheGab', color: 'bg-purple-500/20 text-purple-400 border-purple-500/40', icon: Shield, desc: 'Homologação de demandas, chamada e relatórios gerais' },
  { id: 'comsoc', label: 'Operador COMSOC', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40', icon: Camera, desc: 'Coberturas, fotos, demandas, acervo e estúdio de design' },
  { id: 'comsoc_design', label: 'Designer COMSOC', color: 'bg-pink-500/20 text-pink-400 border-pink-500/40', icon: Palette, desc: 'Estúdio de design, mala direta, cardápios e placas JADE' },
  { id: 'oficial_gab', label: 'Oficial do Gabinete', color: 'bg-[#c5a059]/20 text-[#c5a059] border-[#c5a059]/40', icon: Shield, desc: 'Visualização tática de pautas, agenda e cerimonial' },
  { id: 'praca_gab', label: 'Praça do Gabinete', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40', icon: UserCheck, desc: 'Pronto diário, solicitações de demanda e avisos' },
  { id: 'operador', label: 'Operador Padrão', color: 'bg-slate-700 text-slate-300 border-slate-600', icon: UserCheck, desc: 'Acesso operacional comum do gabinete' },
  { id: 'militar', label: 'Militar Geral', color: 'bg-slate-800 text-slate-400 border-slate-700', icon: UserCheck, desc: 'Acesso básico / consulta' },
];

interface ModulePermissionItem {
  id: string;
  name: string;
  category: string;
  allowedRoles: UserRole[];
}

const DEFAULT_MODULE_PERMISSIONS: ModulePermissionItem[] = [
  // 🏛️ Gabinete & Operações Diárias
  { id: 'menu_dashboard', name: 'Painel de Comando (Dashboard)', category: '🏛️ Gabinete & Operações', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab', 'praca_gab', 'operador', 'militar'] },
  { id: 'menu_presenca', name: 'Chamada & Presença Diária (Pronto)', category: '🏛️ Gabinete & Operações', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab', 'praca_gab', 'operador'] },
  { id: 'menu_comsoc_demandas', name: 'Nova Solicitação de Demanda', category: '🏛️ Gabinete & Operações', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab', 'praca_gab', 'operador'] },
  { id: 'menu_comsoc_homologar', name: 'Homologar Demandas & Pautas', category: '🏛️ Gabinete & Operações', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab'] },

  // 🎖️ Cerimonial & Protocolo Naval
  { id: 'menu_comsoc_almanaque', name: 'Almanaque de Autoridades', category: '🎖️ Cerimonial & Protocolo', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab'] },
  { id: 'menu_comsoc_assentos', name: 'Placas de Assento (Jade)', category: '🎖️ Cerimonial & Protocolo', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab'] },
  { id: 'menu_comsoc_rsvp', name: 'Gestão de Convites & RSVP Portaria', category: '🎖️ Cerimonial & Protocolo', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab'] },
  { id: 'menu_pesquisa_satisfacao', name: 'Pesquisa de Satisfação & NPS', category: '🎖️ Cerimonial & Protocolo', allowedRoles: ['admin', 'supervisor', 'comsoc'] },

  // 📦 Logística & Material
  { id: 'menu_comsoc_brindes', name: 'Estoque de Brindes do RP', category: '📦 Logística & Material', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab'] },
  { id: 'menu_comsoc_cautela', name: 'Cautela de Equipamentos & Material', category: '📦 Logística & Material', allowedRoles: ['admin', 'supervisor', 'comsoc'] },

  // 📣 Comunicação & Mídia
  { id: 'menu_assistente_ia', name: 'Central de IA & Redator', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab'] },
  { id: 'menu_jarvis', name: 'Jarvis Assistente de Voz', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc'] },
  { id: 'menu_smart_editor', name: 'Smart Editor IA (Vídeos & Cortes)', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'comsoc', 'comsoc_design'] },
  { id: 'menu_estudio_grafico', name: 'Estúdio de Design & Mala Direta', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'comsoc', 'comsoc_design'] },
  { id: 'menu_comsoc_galeria', name: 'Galeria, Fotos & Biometria Facial', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab', 'praca_gab', 'operador'] },
  { id: 'menu_comsoc_historico', name: 'Arquivo Histórico de Coberturas', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab'] },
  { id: 'menu_comsoc_aniversariantes', name: 'Aniversariantes & Efemérides', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc', 'oficial_gab', 'praca_gab', 'operador', 'militar'] },
  { id: 'menu_sisgab_tv', name: 'SisGAB TV (Monitor Telão)', category: '📣 Comunicação & Mídia', allowedRoles: ['admin', 'supervisor', 'comsoc', 'comsoc_design', 'oficial_gab', 'praca_gab', 'operador', 'militar'] },

  // ⚙️ Sistema & Administração
  { id: 'menu_telegram_metrics', name: 'Gestão do Telegram & Bot', category: '⚙️ Sistema & Administração', allowedRoles: ['admin', 'supervisor'] },
  { id: 'menu_config', name: 'Configurações, Voz IA & Alertas', category: '⚙️ Sistema & Administração', allowedRoles: ['admin', 'supervisor'] },
  { id: 'menu_admin_panel', name: 'Usuários & Matriz de Permissões', category: '⚙️ Sistema & Administração', allowedRoles: ['admin'] },
];

export const UserManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'usuarios' | 'permissoes'>('permissoes');
  const [users, setUsers] = useState<MilitarCompleto[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterRole, setFilterRole] = useState<'todos' | 'comsoc' | 'gabinete' | 'admin'>('todos');
  const [loading, setLoading] = useState(true);
  const [savingMatrix, setSavingMatrix] = useState(false);

  // Matriz de Permissões
  const [permissionsMatrix, setPermissionsMatrix] = useState<ModulePermissionItem[]>(DEFAULT_MODULE_PERMISSIONS);

  // Modal Novo Operador
  const [modalOpen, setModalOpen] = useState(false);
  const [newUser, setNewUser] = useState({
    nome_guerra: '',
    posto: '1ºSG (FN)',
    setor: 'ComSoc / Gabinete',
    email: '',
    telegram_id: '',
    role: 'comsoc' as UserRole,
  });

  // Modal Edição de Militar
  const [editingUser, setEditingUser] = useState<MilitarCompleto | null>(null);

  useEffect(() => {
    loadRealUsersAndPermissions();
  }, []);

  const loadRealUsersAndPermissions = async () => {
    try {
      setLoading(true);

      // 1. Carrega os 66 militares reais
      const { data: efData } = await supabase
        .from('efetivo')
        .select('*')
        .order('id', { ascending: true });

      if (efData && efData.length > 0) {
        const loaded: MilitarCompleto[] = efData.map((ef: any) => ({
          id: String(ef.id),
          nome_guerra: ef.nome_guerra || `MILITAR #${ef.id}`,
          role: (ef.role as UserRole) || 'operador',
          posto: ef.posto || ef.posto_grad || '',
          posto_grad: ef.posto_grad || ef.posto || '',
          setor: ef.setor || 'Gabinete CGCFN',
          email: ef.email,
          telegram_id: ef.telegram_id,
          url_foto: ef.url_foto,
        }));
        setUsers(loaded);
      }

      // 2. Carrega a matriz de permissões salva no banco (se existir)
      const { data: cfgPerms } = await supabase
        .from('config')
        .select('valor')
        .eq('chave', 'menu_permissions_matrix')
        .single();

      if (cfgPerms && cfgPerms.valor) {
        try {
          const parsed = JSON.parse(cfgPerms.valor);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setPermissionsMatrix(parsed);
          }
        } catch (e) {
          console.warn('Erro ao parsear permissions_matrix:', e);
        }
      }
    } catch (err) {
      console.warn('Erro ao buscar dados:', err);
    } finally {
      setLoading(false);
    }
  };

  // Toggle de permissão na matriz
  const handleTogglePermission = (moduleId: string, role: UserRole) => {
    if (role === 'admin' && moduleId === 'menu_admin_panel') {
      toast.warning('O Administrador Total não pode perder acesso ao painel de permissões!');
      return;
    }

    setPermissionsMatrix((prev) =>
      prev.map((item) => {
        if (item.id !== moduleId) return item;
        const exists = item.allowedRoles.includes(role);
        const updatedRoles = exists
          ? item.allowedRoles.filter((r) => r !== role)
          : [...item.allowedRoles, role];
        return { ...item, allowedRoles: updatedRoles };
      })
    );
  };

  // Salvar Matriz no Supabase
  const handleSavePermissionsMatrix = async () => {
    setSavingMatrix(true);
    try {
      const jsonValue = JSON.stringify(permissionsMatrix);
      const { error } = await supabase
        .from('config')
        .upsert({ chave: 'menu_permissions_matrix', valor: jsonValue });

      if (error) throw error;

      militaryAudio.playTacticalBeep();
      toast.success('Quadro de Lógica e Permissões salvo com sucesso no Supabase!');
    } catch (err: any) {
      toast.error(`Erro ao salvar permissões: ${err.message}`);
    } finally {
      setSavingMatrix(false);
    }
  };

  // Redefinir para Padrão Naval Seguro
  const handleResetToDefault = () => {
    setPermissionsMatrix(DEFAULT_MODULE_PERMISSIONS);
    toast.info('Matriz redefinida para o Padrão Naval Seguro.');
  };

  // Salvar Edição de Militar
  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;

    setUsers((prev) =>
      prev.map((u) => (u.id === editingUser.id ? { ...editingUser } : u))
    );

    const targetUser = editingUser;
    setEditingUser(null);
    toast.success(`Dados de ${targetUser.nome_guerra} atualizados!`);

    try {
      await supabase
        .from('efetivo')
        .update({
          nome_guerra: targetUser.nome_guerra,
          role: targetUser.role,
          posto: targetUser.posto,
          posto_grad: targetUser.posto,
          setor: targetUser.setor,
          email: targetUser.email || null,
          telegram_id: targetUser.telegram_id ? parseInt(String(targetUser.telegram_id), 10) : null,
        })
        .eq('id', parseInt(targetUser.id, 10));
    } catch (err: any) {
      toast.error(`Erro ao salvar no banco: ${err.message}`);
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.nome_guerra.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (u.posto && u.posto.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (u.setor && u.setor.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;
    if (filterRole === 'comsoc') return u.role === 'comsoc' || u.role === 'comsoc_design';
    if (filterRole === 'gabinete') return u.role === 'oficial_gab' || u.role === 'praca_gab' || u.role === 'supervisor';
    if (filterRole === 'admin') return u.role === 'admin';
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* ── HEADER SUPERIOR ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
              Segurança, Controle de Acesso & Efetivo
            </span>
            <span className="text-slate-400 text-xs">• Matriz de Permissões RBAC</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Usuários, Efetivo & Quadro de Permissões
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm">
            Defina o quadro de lógica de acesso aos módulos da sidebar para cada categoria de militar do Gabinete.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === 'permissoes' ? (
            <button
              onClick={handleSavePermissionsMatrix}
              disabled={savingMatrix}
              className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/25 transition-all hover:scale-105 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{savingMatrix ? 'Salvando...' : 'Salvar Matriz no Banco'}</span>
            </button>
          ) : (
            <button
              onClick={() => setModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/25 transition-all hover:scale-105"
            >
              <Plus className="w-4 h-4" />
              <span>Cadastrar Novo Militar</span>
            </button>
          )}
        </div>
      </div>

      {/* ── ABAS PRINCIPAIS ── */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveTab('permissoes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'permissoes'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>🛡️ 1. Quadro de Lógica & Matriz de Permissões de Acesso</span>
        </button>

        <button
          onClick={() => setActiveTab('usuarios')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'usuarios'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>👥 2. Efetivo do Gabinete ({users.length} Militares Reais)</span>
        </button>
      </div>

      {/* ── ABA 1: MATRIZ DE PERMISSÕES & QUADRO DE LÓGICA ── */}
      {activeTab === 'permissoes' && (
        <div className="space-y-6">
          {/* Card Informativo dos Perfis */}
          <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
                  <Sliders className="w-4 h-4" />
                  <span>Matriz Interativa de Acessos aos Menus da Sidebar</span>
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Marque ou desmarque as caixas para liberar/restringir cada módulo para os diferentes papéis militares.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleResetToDefault}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-bold transition-all"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restaurar Padrão Seguro</span>
                </button>
              </div>
            </div>

            {/* TABELA / MATRIZ DE PERMISSÕES RBAC */}
            <div className="overflow-x-auto rounded-2xl border border-slate-800">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 font-bold">
                    <th className="p-3.5 min-w-[240px] text-white">Módulo / Item do Menu</th>
                    {ROLES_LIST.map((role) => (
                      <th key={role.id} className="p-3 text-center min-w-[100px]">
                        <div className="flex flex-col items-center gap-1">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase border ${role.color}`}>
                            {role.label.split(' ')[0]}
                          </span>
                          <span className="text-[8px] text-slate-500 font-mono">{role.id}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-800/60 bg-[#09101f]/70">
                  {permissionsMatrix.map((item, idx) => {
                    const isFirstOfCategory =
                      idx === 0 || permissionsMatrix[idx - 1].category !== item.category;

                    return (
                      <React.Fragment key={item.id}>
                        {isFirstOfCategory && (
                          <tr className="bg-slate-950/90 font-black text-[#c5a059] text-[10px] tracking-wider uppercase border-t border-b border-slate-800">
                            <td colSpan={ROLES_LIST.length + 1} className="py-2 px-3.5">
                              {item.category}
                            </td>
                          </tr>
                        )}

                        <tr className="hover:bg-slate-800/40 transition-colors">
                          <td className="p-3 font-medium text-slate-200 flex items-center justify-between">
                            <span>{item.name}</span>
                            <span className="text-[9px] font-mono text-slate-500">{item.id}</span>
                          </td>

                          {ROLES_LIST.map((role) => {
                            const isAllowed = item.allowedRoles.includes(role.id);

                            return (
                              <td key={role.id} className="p-3 text-center">
                                <button
                                  type="button"
                                  onClick={() => handleTogglePermission(item.id, role.id)}
                                  className={`w-7 h-7 rounded-lg inline-flex items-center justify-center transition-all ${
                                    isAllowed
                                      ? 'bg-emerald-500 text-slate-950 shadow-sm shadow-emerald-500/20 font-black hover:bg-emerald-400 scale-105'
                                      : 'bg-slate-900 border border-slate-800 text-slate-600 hover:border-slate-600 hover:text-slate-400'
                                  }`}
                                  title={`${role.label}: ${isAllowed ? 'Permitido' : 'Negado'}`}
                                >
                                  {isAllowed ? <Check className="w-4 h-4 stroke-[3]" /> : '✕'}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 2: EFETIVO DO GABINETE & USUÁRIOS ── */}
      {activeTab === 'usuarios' && (
        <div className="space-y-4">
          {/* Filtros e Busca */}
          <div className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Buscar militar por nome de guerra, posto ou setor..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs">
              <button
                onClick={() => setFilterRole('todos')}
                className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                  filterRole === 'todos' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                Todos ({users.length})
              </button>
              <button
                onClick={() => setFilterRole('comsoc')}
                className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                  filterRole === 'comsoc' ? 'bg-emerald-500 text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                COMSOC
              </button>
              <button
                onClick={() => setFilterRole('gabinete')}
                className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                  filterRole === 'gabinete' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                Gabinete
              </button>
              <button
                onClick={() => setFilterRole('admin')}
                className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
                  filterRole === 'admin' ? 'bg-red-500 text-slate-950 font-black' : 'text-slate-400'
                }`}
              >
                Admin
              </button>
            </div>
          </div>

          {/* Grid de Militares do Efetivo */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredUsers.map((user) => {
              const roleInfo = ROLES_LIST.find((r) => r.id === user.role) || ROLES_LIST[6];
              const Icon = roleInfo.icon;

              return (
                <div
                  key={user.id}
                  className="p-4 rounded-2xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/40 space-y-3 transition-all shadow-lg"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center font-black text-sm text-[#c5a059]">
                        {user.posto ? user.posto.substring(0, 3) : 'MIL'}
                      </div>
                      <div>
                        <h3 className="font-black text-white text-sm">{user.nome_guerra}</h3>
                        <p className="text-[11px] text-slate-400 font-medium">
                          {user.posto || 'Militar'} • {user.setor || 'Gabinete'}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => setEditingUser(user)}
                      className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                      title="Editar militar e permissões"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase border ${roleInfo.color}`}>
                      <Icon className="w-3 h-3 inline mr-1" />
                      {roleInfo.label}
                    </span>

                    {user.telegram_id ? (
                      <span className="text-[10px] text-cyan-400 font-mono">TG: {user.telegram_id}</span>
                    ) : (
                      <span className="text-[10px] text-slate-500 font-mono">Sem Telegram</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── MODAL: EDIÇÃO DE MILITAR & CATEGORIA ── */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-[#c5a059]" />
                <span>Editar Militar & Papel no SisGAB</span>
              </h3>
              <button onClick={() => setEditingUser(null)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome de Guerra</label>
                <input
                  type="text"
                  required
                  value={editingUser.nome_guerra}
                  onChange={(e) => setEditingUser({ ...editingUser, nome_guerra: e.target.value.toUpperCase() })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Posto / Graduação</label>
                  <input
                    type="text"
                    value={editingUser.posto || ''}
                    onChange={(e) => setEditingUser({ ...editingUser, posto: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Papel / Categoria no SisGAB</label>
                  <select
                    value={editingUser.role}
                    onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value as UserRole })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none font-bold"
                  >
                    {ROLES_LIST.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Setor</label>
                  <input
                    type="text"
                    value={editingUser.setor || ''}
                    onChange={(e) => setEditingUser({ ...editingUser, setor: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Telegram ID (Numérico)</label>
                  <input
                    type="text"
                    value={editingUser.telegram_id ? String(editingUser.telegram_id) : ''}
                    onChange={(e) => setEditingUser({ ...editingUser, telegram_id: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black shadow-md shadow-[#c5a059]/25"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
