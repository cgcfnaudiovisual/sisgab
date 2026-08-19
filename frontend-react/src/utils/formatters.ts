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
