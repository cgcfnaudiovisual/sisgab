// Utilitário de parsing resiliente para dados do Supabase

export function parseCobertura(raw: any): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === 'string') {
    const trimmed = raw.trim();
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      try {
        const parsed = JSON.parse(trimmed);
        if (Array.isArray(parsed)) return parsed.map(String);
      } catch {
        // Fallback para split por vírgula
      }
    }
    return trimmed
      .replace(/[\[\]"']/g, '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [String(raw)];
}

export function safeString(val: any, fallback: string = ''): string {
  if (val === null || val === undefined) return fallback;
  return String(val);
}

// 🇧🇷 Utilitários de Data & Hora para o Horário Oficial de Brasília (GMT-3 / America/Sao_Paulo)
export const BRASILIA_TIMEZONE = 'America/Sao_Paulo';

/**
 * Retorna a data atual ou informada formatada como 'YYYY-MM-DD' no Horário de Brasília (GMT-3).
 * Evita o bug de virar a data às 21:00h no Brasil por conta do UTC.
 */
export function getBrasiliaDateStr(dateInput?: Date | string | number): string {
  const d = dateInput
    ? typeof dateInput === 'string' || typeof dateInput === 'number'
      ? new Date(dateInput)
      : dateInput
    : new Date();

  if (isNaN(d.getTime())) {
    return new Intl.DateTimeFormat('en-CA', { timeZone: BRASILIA_TIMEZONE }).format(new Date());
  }

  return new Intl.DateTimeFormat('en-CA', {
    timeZone: BRASILIA_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d);
}

/**
 * Retorna o horário formatado no Horário de Brasília (ex: '14:30' ou '14:30:45').
 */
export function getBrasiliaTimeStr(dateInput?: Date | string | number, includeSeconds = false): string {
  const d = dateInput
    ? typeof dateInput === 'string' || typeof dateInput === 'number'
      ? new Date(dateInput)
      : dateInput
    : new Date();

  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: BRASILIA_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined,
    hour12: false,
  }).format(d);
}

/**
 * Retorna a data e hora ISO atual no fuso de Brasília (com offset -03:00).
 */
export function getBrasiliaISOString(dateInput?: Date | string | number): string {
  const d = dateInput
    ? typeof dateInput === 'string' || typeof dateInput === 'number'
      ? new Date(dateInput)
      : dateInput
    : new Date();

  const datePart = getBrasiliaDateStr(d);
  const timePart = getBrasiliaTimeStr(d, true);
  return `${datePart}T${timePart}-03:00`;
}

/**
 * Adiciona ou subtrai dias de uma data 'YYYY-MM-DD' preservando o fuso de Brasília.
 */
export function addDaysBrasilia(dateStr: string, days: number): string {
  if (!dateStr || !dateStr.includes('-')) {
    dateStr = getBrasiliaDateStr();
  }
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  d.setDate(d.getDate() + days);
  return getBrasiliaDateStr(d);
}

/**
 * Formata uma data para exibição por extenso em português (ex: 'quarta-feira, 19 de agosto de 2026')
 */
export function formatBrasiliaExtenso(dateStr: string): string {
  if (!dateStr) return '';
  const clean = dateStr.slice(0, 10);
  if (!clean.includes('-')) return clean;
  const [year, month, day] = clean.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('pt-BR', {
    timeZone: BRASILIA_TIMEZONE,
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
}

/**
 * Formata data curta brasileira 'DD/MM/YYYY'
 */
export function formatBrasiliaDataCurta(dateStr: string): string {
  if (!dateStr) return '';
  const clean = dateStr.slice(0, 10);
  if (clean.includes('-')) {
    const [year, month, day] = clean.split('-');
    return `${day}/${month}/${year}`;
  }
  return clean;
}
