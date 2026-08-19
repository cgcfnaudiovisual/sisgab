import React, { useState, useEffect } from 'react';
import { Menu, Search, Bell, Shield, LogOut, CheckCircle2, Clock, AlertTriangle, X, ExternalLink } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import type { UserRole } from '../../types/database';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import { speakVoiceNotification } from '../../utils/voiceNotifier';

interface AppHeaderProps {
  onToggleSidebar: () => void;
  onOpenCommandMenu: () => void;
}

interface NotificationItem {
  id: string;
  titulo: string;
  descricao: string;
  tipo: 'demanda_nova' | 'demanda_alterada' | 'aviso';
  timestamp: string;
  lida: boolean;
  link?: string;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  onToggleSidebar,
  onOpenCommandMenu,
}) => {
  const { user, switchRole, logout } = useAuth();
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showNotificationMenu, setShowNotificationMenu] = useState<boolean>(false);

  // Escuta em tempo real eventos no Supabase
  useEffect(() => {
    // Carrega últimas demandas como notificações iniciais
    const loadInitialNotifications = async () => {
      try {
        const { data } = await supabase
          .from('demandas_comunicacao')
          .select('id, titulo_evento, solicitante_nome, status, criado_em')
          .order('criado_em', { ascending: false })
          .limit(5);

        if (data) {
          const formatted: NotificationItem[] = data.map((d) => ({
            id: d.id.toString(),
            titulo: d.status === 'aprovado' ? '✅ Demanda Homologada' : '📋 Nova Demanda Solicitada',
            descricao: `${d.titulo_evento} (${d.solicitante_nome})`,
            tipo: d.status === 'aprovado' ? 'demanda_alterada' : 'demanda_nova',
            timestamp: 'Hoje',
            lida: false,
            link: '/comsoc_homologar',
          }));
          setNotifications(formatted);
          setUnreadCount(formatted.length);
        }
      } catch (err) {
        console.warn('Erro ao carregar notificações:', err);
      }
    };

    loadInitialNotifications();

    // Listener Realtime Supabase
    const channel = supabase
      .channel('realtime_notifications')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'demandas_comunicacao' },
        (payload) => {
          const newDem = payload.new as any;
          const newNotif: NotificationItem = {
            id: newDem.id.toString(),
            titulo: '🚨 Nova Demanda Solicitada!',
            descricao: `${newDem.titulo_evento} por ${newDem.solicitante_nome}`,
            tipo: 'demanda_nova',
            timestamp: 'Agora',
            lida: false,
            link: '/comsoc_homologar',
          };

          setNotifications((prev) => [newNotif, ...prev]);
          setUnreadCount((prev) => prev + 1);

          toast.info(`📋 Nova Demanda: ${newDem.titulo_evento}`, {
            description: `Solicitante: ${newDem.solicitante_nome}`,
          });

          // Disparo de Voz Inteligente (ElevenLabs / Neural)
          speakVoiceNotification({
            titulo: newDem.titulo_evento,
            solicitante: newDem.solicitante_nome,
            tipo: 'nova_pauta',
          });
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'demandas_comunicacao' },
        (payload) => {
          const updDem = payload.new as any;
          const updNotif: NotificationItem = {
            id: updDem.id.toString(),
            titulo: `🔄 Pauta Atualizada (${updDem.status?.toUpperCase()})`,
            descricao: `${updDem.titulo_evento}`,
            tipo: 'demanda_alterada',
            timestamp: 'Agora',
            lida: false,
            link: '/comsoc_homologar',
          };

          setNotifications((prev) => [updNotif, ...prev]);
          setUnreadCount((prev) => prev + 1);

          toast.success(`Pauta Atualizada: ${updDem.titulo_evento} (${updDem.status})`);

          // Anúncio por voz se for aprovada
          if (updDem.status === 'aprovado' || updDem.status === 'aprovada') {
            speakVoiceNotification({
              titulo: updDem.titulo_evento,
              tipo: 'pauta_aprovada',
            });
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    switchRole(e.target.value as UserRole);
  };

  const handleLogout = () => {
    logout();
    toast.info('Sessão encerrada.');
    navigate('/login');
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, lida: true })));
    setUnreadCount(0);
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-[#080d1a]/95 backdrop-blur-md border-b border-[#c5a059]/20 px-4 flex items-center justify-between">
      {/* Left Area: Toggle & Search */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search / Command Palette Trigger */}
        <button
          onClick={onOpenCommandMenu}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-700/60 text-slate-400 hover:text-slate-200 hover:border-[#c5a059]/40 text-xs transition-all w-48 sm:w-64"
        >
          <Search className="w-3.5 h-3.5 text-[#c5a059]" />
          <span className="truncate flex-1 text-left">Buscar pautas, convidados...</span>
          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-semibold text-slate-400 bg-slate-800 rounded border border-slate-700">
            Ctrl+K
          </kbd>
        </button>
      </div>

      {/* Right Area: System Status, Notifications & User Profile */}
      <div className="flex items-center gap-3 relative">
        {/* Exercício / Ano */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#c5a059]/10 border border-[#c5a059]/30 text-xs font-semibold text-[#e5c07b]">
          <span>Exercício:</span>
          <span className="font-bold text-[#00e5ff]">2026</span>
        </div>

        {/* Status Realtime */}
        <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-950/40 border border-emerald-500/30 text-[11px] text-emerald-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Supabase Online</span>
        </div>

        {/* Botão e Painel de Notificações em Tempo Real */}
        <div className="relative">
          <button
            onClick={() => setShowNotificationMenu(!showNotificationMenu)}
            className="relative p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors"
            title="Notificações e Avisos da Tripulação"
          >
            <Bell className="w-4 h-4 text-slate-300" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-[#00e5ff] text-slate-950 font-black text-[9px] flex items-center justify-center animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Menu Dropdown de Notificações */}
          {showNotificationMenu && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 shadow-2xl z-50 p-4 space-y-3 animate-in fade-in zoom-in-95">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2">
                  <Bell className="w-4 h-4 text-[#c5a059]" />
                  <span className="text-xs font-black text-white uppercase tracking-wider">
                    Central de Notificações
                  </span>
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[10px] text-[#00e5ff] hover:underline font-bold"
                  >
                    Marcar lidas
                  </button>
                )}
              </div>

              <div className="space-y-2 max-h-72 overflow-y-auto pr-1 divide-y divide-slate-800/60">
                {notifications.length > 0 ? (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => {
                        if (notif.link) navigate(notif.link);
                        setShowNotificationMenu(false);
                      }}
                      className="pt-2 hover:bg-slate-900/60 p-1.5 rounded-xl cursor-pointer transition-colors"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[11px] font-bold text-white leading-tight">
                          {notif.titulo}
                        </span>
                        <span className="text-[9px] text-slate-500">{notif.timestamp}</span>
                      </div>
                      <p className="text-[10px] text-slate-400 line-clamp-2 mt-0.5">
                        {notif.descricao}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="py-6 text-center text-slate-500 text-xs">
                    Nenhuma notificação recente.
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                <button
                  onClick={() => {
                    navigate('/comsoc_homologar');
                    setShowNotificationMenu(false);
                  }}
                  className="text-[10px] text-[#c5a059] font-bold hover:underline flex items-center gap-1"
                >
                  <ExternalLink className="w-3 h-3" />
                  <span>Ver todas as demandas</span>
                </button>

                <button
                  onClick={() => setShowNotificationMenu(false)}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 text-slate-400 text-[10px] font-bold hover:text-white"
                >
                  Fechar
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Seletor Rápido de Perfil & Logout */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
          <div className="hidden sm:block text-right">
            <p className="text-xs font-bold text-slate-200">{user?.nome_guerra || 'OPERADOR'}</p>
            <div className="flex items-center justify-end gap-1">
              <Shield className="w-2.5 h-2.5 text-[#c5a059]" />
              <select
                value={user?.role || 'operador'}
                onChange={handleRoleChange}
                className="bg-transparent text-[10px] text-[#c5a059] font-semibold border-none cursor-pointer focus:outline-none"
              >
                <option value="admin" className="bg-slate-900 text-white">ADMIN</option>
                <option value="oficial_gab" className="bg-slate-900 text-white">OFICIAL GAB</option>
                <option value="comsoc" className="bg-slate-900 text-white">COMSOC</option>
                <option value="operador" className="bg-slate-900 text-white">OPERADOR</option>
                <option value="militar" className="bg-slate-900 text-white">MILITAR</option>
              </select>
            </div>
          </div>

          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#c5a059] to-amber-200 text-slate-950 font-black text-xs flex items-center justify-center shadow-sm">
            {user?.nome_guerra?.slice(0, 2) || 'OP'}
          </div>

          {/* Botão de Logout */}
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Sair do SisGAB"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
