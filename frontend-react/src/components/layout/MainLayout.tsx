import React, { useState, useEffect, useRef } from 'react';
import { Outlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { CommandMenu } from './CommandMenu';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { ChevronRight } from 'lucide-react';

export const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [commandMenuOpen, setCommandMenuOpen] = useState(false);

  // Estado de Colapso da Barra Lateral no Desktop (Persistido)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('sisgab_sidebar_collapsed') === 'true';
  });

  // Estado de Hover (Aproximação do mouse na borda esquerda)
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const hoverTimeoutRef = useRef<any>(null);

  const handleToggleCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sisgab_sidebar_collapsed', String(next));
      if (!next) setSidebarHovered(false);
      return next;
    });
  };

  const handleEdgeMouseEnter = () => {
    if (!sidebarCollapsed) return;
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setSidebarHovered(true);
  };

  const handleSidebarMouseLeave = () => {
    if (!sidebarCollapsed) return;
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      setSidebarHovered(false);
    }, 250);
  };

  const handleSidebarMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    if (sidebarCollapsed) setSidebarHovered(true);
  };

  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-100 flex selection:bg-[#c5a059]/30 selection:text-[#e5c07b] relative">
      {/* Zona de Detecção de Hover na Borda Esquerda (Desktop quando recolhida) */}
      {sidebarCollapsed && (
        <div
          onMouseEnter={handleEdgeMouseEnter}
          className="fixed left-0 top-0 bottom-0 w-3.5 z-40 hidden lg:flex items-center justify-start group cursor-pointer hover:w-6 transition-all duration-200"
          title="Passe o mouse aqui para expandir o menu lateral"
        >
          <div className="w-1.5 h-16 bg-[#c5a059]/40 group-hover:bg-[#c5a059] group-hover:h-28 rounded-r-full transition-all duration-300 flex items-center justify-center shadow-lg shadow-[#c5a059]/30">
            <ChevronRight className="w-3 h-3 text-slate-950 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      )}

      {/* Sidebar */}
      <AppSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
        isHovered={sidebarHovered}
        onMouseEnter={handleSidebarMouseEnter}
        onMouseLeave={handleSidebarMouseLeave}
      />

      {/* Main Content Area com Transição de Largura */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? 'lg:pl-0' : 'lg:pl-72'
        }`}
      >
        {/* Top Header */}
        <AppHeader
          onToggleSidebar={() => {
            // Em mobile abre drawer; em desktop alterna collapse
            if (window.innerWidth < 1024) {
              setSidebarOpen((prev) => !prev);
            } else {
              handleToggleCollapse();
            }
          }}
          onOpenCommandMenu={() => setCommandMenuOpen(true)}
        />

        {/* Page Content Outlet */}
        <main className="flex-1 p-3 sm:p-5 md:p-6 max-w-[1600px] w-full mx-auto animate-in fade-in duration-150">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>

        {/* Footer Institucional Global */}
        <footer className="py-4 px-6 text-center border-t border-slate-900/80 mt-auto">
          <p className="text-xs font-bold text-[#c5a059] tracking-wider opacity-90">
            🚀 Desenvolvido por Sargento Calaça 🇧🇷
          </p>
          <p className="text-[10px] text-slate-500 font-semibold mt-0.5">
            Gabinete do Comando-Geral do Corpo de Fuzileiros Navais • SisGAB v2.0
          </p>
        </footer>
      </div>

      {/* Global Command Menu (Ctrl+K) */}
      <CommandMenu
        isOpen={commandMenuOpen}
        onClose={() => setCommandMenuOpen(false)}
      />
    </div>
  );
};
