import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[SISGAB ERROR BOUNDARY CAUGHT]', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-6 rounded-3xl bg-red-950/40 border border-red-500/40 text-slate-100 max-w-2xl mx-auto my-8 space-y-4 shadow-2xl">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-red-500/20 text-red-400 border border-red-500/30">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-black text-white">Erro ao Renderizar Módulo</h2>
              <p className="text-xs text-red-300">
                {this.state.error?.message || 'Ocorreu um erro inesperado ao processar os dados.'}
              </p>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold text-xs flex items-center gap-2 transition-all shadow-md shadow-red-600/30"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Recarregar Painel</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
