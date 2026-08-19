import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://ruabgndnhgdverqlgvef.supabase.co';
// Usa a chave Service Role para acesso irrestrito às tabelas com RLS (efetivo, escala, etc.), idêntico ao backend Python
const SUPABASE_KEY =
  import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY ||
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ1YWJnbmRuaGdkdmVycWxndmVmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDM5NDg2MSwiZXhwIjoyMDk5OTcwODYxfQ._ULU--E5O9zptG6DawmSMvhAKtApTNRFbbnAboSzTRE';

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
  },
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});

// Helper de verificação de conexão
export async function checkSupabaseConnection(): Promise<boolean> {
  try {
    const { error } = await supabase.from('config').select('chave').limit(1);
    return !error;
  } catch {
    return false;
  }
}
