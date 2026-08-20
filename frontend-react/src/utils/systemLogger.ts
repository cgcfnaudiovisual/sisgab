// Sistema Central de Logs e Auditoria Operacional do SisGAB 2.0

export type LogCategory = 'DEMANDAS' | 'DRIVE' | 'BD' | 'AUTH' | 'SISTEMA' | 'ERRO' | 'IA' | 'AMEACAS';
export type LogSeverity = 'info' | 'success' | 'warn' | 'error';

export interface SystemLogEntry {
  id: string;
  timestamp: string;
  category: LogCategory;
  severity: LogSeverity;
  action: string;
  details: string;
  source: string;
  metadata?: Record<string, any>;
}

const STORAGE_KEY = 'sisgab_system_logs_v2';
const MAX_LOGS = 500;

export function getSystemLogs(): SystemLogEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.error('Erro ao ler logs do sistema:', e);
  }
  return [];
}

export function addSystemLog(
  category: LogCategory,
  action: string,
  details: string,
  severity: LogSeverity = 'info',
  metadata?: Record<string, any>,
  source: string = 'SisGAB Frontend'
): SystemLogEntry {
  const newEntry: SystemLogEntry = {
    id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    timestamp: new Date().toISOString(),
    category,
    severity,
    action,
    details,
    source,
    metadata,
  };

  try {
    const current = getSystemLogs();
    current.unshift(newEntry);
    if (current.length > MAX_LOGS) {
      current.splice(MAX_LOGS);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
    
    // Dispara evento customizado para reatividade em tempo real
    window.dispatchEvent(new CustomEvent('sisgab-new-log', { detail: newEntry }));
  } catch (e) {
    console.error('Falha ao gravar log no storage:', e);
  }

  // Também grava no console do browser de forma estilizada
  const colors: Record<LogSeverity, string> = {
    error: 'color: #ff4d4f; font-weight: bold;',
    warn: 'color: #faad14; font-weight: bold;',
    success: 'color: #52c41a; font-weight: bold;',
    info: 'color: #1890ff; font-weight: bold;',
  };
  console.log(`%c[${category}] ${action}`, colors[severity], { details, metadata, timestamp: newEntry.timestamp });

  return newEntry;
}

export function clearSystemLogs(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new CustomEvent('sisgab-logs-cleared'));
  } catch (e) {
    console.error('Erro ao limpar logs:', e);
  }
}

export function exportLogsAsJson(): void {
  const logs = getSystemLogs();
  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute('href', dataStr);
  downloadAnchor.setAttribute('download', `sisgab_logs_${new Date().toISOString().slice(0, 10)}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}
