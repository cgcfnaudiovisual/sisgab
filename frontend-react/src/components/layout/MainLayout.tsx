import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { CommandMenu } from './CommandMenu';
import { ErrorBoundary } from '../common/ErrorBoundary';

export const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [commandMenuOpen, setCommandMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#060a12] text-slate-100 flex selection:bg-[#c5a059]/30 selection:text-[#e5c07b]">
      {/* Sidebar */}
      <AppSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-72">
        {/* Top Header */}
        <AppHeader
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
          onOpenCommandMenu={() => setCommandMenuOpen(true)}
        />

        {/* Page Content Outlet */}
        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto animate-in fade-in duration-150">
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
