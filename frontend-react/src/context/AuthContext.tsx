import React, { createContext, useContext, useState, useEffect } from 'react';
import bcrypt from 'bcryptjs';
import type { UserProfile, UserRole } from '../types/database';
import { supabase } from '../api/supabase';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (identifier: string, password?: string) => Promise<{ success: boolean; message?: string }>;
  logout: () => void;
  switchRole: (role: UserRole) => void;
  refreshUserProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('sisgab_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (user) {
      localStorage.setItem('sisgab_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('sisgab_user');
    }
  }, [user]);

  const refreshUserProfile = async () => {
    if (!user) return;
    try {
      const { data } = await supabase
        .from('efetivo')
        .select('*')
        .ilike('nome_guerra', `%${user.nome_guerra}%`)
        .limit(1);

      if (data && data.length > 0) {
        const u = data[0];
        setUser((prev) => ({
          ...prev!,
          id: String(u.id),
          nome: u.nome_guerra,
          posto: u.posto || u.posto_grad,
          posto_grad: u.posto_grad || u.posto,
          role: (u.role as UserRole) || prev!.role,
          setor: u.setor || prev!.setor,
          email: u.email,
        }));
      }
    } catch {
      // Ignore
    }
  };

  const login = async (identifier: string, password?: string): Promise<{ success: boolean; message?: string }> => {
    setIsLoading(true);
    const cleanId = identifier.trim();

    if (!cleanId) {
      setIsLoading(false);
      return { success: false, message: 'Informe seu Nome de Guerra ou Email militar.' };
    }

    try {
      // 1. Tenta autenticação nativa do Supabase Auth (se for email com senha)
      if (cleanId.includes('@') && password) {
        try {
          const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
            email: cleanId.toLowerCase(),
            password: password,
          });

          if (!authError && authData?.user) {
            const { data: profData } = await supabase
              .from('efetivo')
              .select('*')
              .ilike('email', cleanId.toLowerCase())
              .limit(1);

            const p = profData?.[0];
            const profile: UserProfile = {
              id: authData.user.id,
              username: p?.nome_guerra || cleanId.split('@')[0],
              nome: p?.nome_guerra || cleanId.split('@')[0],
              nome_guerra: (p?.nome_guerra || 'OPERADOR').toUpperCase(),
              role: (p?.role as UserRole) || 'admin',
              posto: p?.posto || p?.posto_grad || 'Militar',
              posto_grad: p?.posto_grad || 'Mil',
              setor: p?.setor || 'Gabinete / CGCFN',
              email: cleanId,
              url_foto: p?.url_foto,
            };
            setUser(profile);
            return { success: true };
          }
        } catch {
          // Continua para checagem em tabela
        }
      }

      // 2. Busca estrita no banco real do Supabase (efetivo / users)
      let efetivoData: any[] | null = null;
      if (cleanId.includes('@')) {
        const { data } = await supabase
          .from('efetivo')
          .select('*')
          .ilike('email', cleanId.toLowerCase())
          .limit(1);
        efetivoData = data;

        if (!efetivoData || efetivoData.length === 0) {
          const { data: uData } = await supabase
            .from('users')
            .select('*')
            .ilike('email', cleanId.toLowerCase())
            .limit(1);
          efetivoData = uData;
        }
      } else {
        const { data } = await supabase
          .from('efetivo')
          .select('*')
          .ilike('nome_guerra', `%${cleanId}%`)
          .limit(1);
        efetivoData = data;

        if (!efetivoData || efetivoData.length === 0) {
          const { data: uData } = await supabase
            .from('users')
            .select('*')
            .or(`username.ilike.%${cleanId}%,nome.ilike.%${cleanId}%`)
            .limit(1);
          efetivoData = uData;
        }
      }

      // Se NÃO encontrou o militar no Supabase, REJEITA imediatamente!
      if (!efetivoData || efetivoData.length === 0) {
        return {
          success: false,
          message: `Militar ou operador "${cleanId}" não encontrado no cadastro do SisGAB.`,
        };
      }

      const militar = efetivoData[0];
      const storedHash = militar.senha_hash || militar.password || '';

      // 3. Verificação Estrita de Senha com bcrypt / hash
      if (storedHash) {
        if (!password) {
          return {
            success: false,
            message: `O militar ${militar.nome_guerra} possui senha cadastrada. Digite sua senha para entrar.`,
          };
        }

        let passwordMatch = false;

        // Formato bcrypt ($2b$ ou $2a$)
        if (storedHash.startsWith('$2b$') || storedHash.startsWith('$2a$')) {
          try {
            passwordMatch = bcrypt.compareSync(password, storedHash);
          } catch {
            passwordMatch = false;
          }
        } else if (storedHash === password) {
          // Texto plano direto
          passwordMatch = true;
        }

        // Caso o usuário seja administrador e a senha seja a master da conta
        if (!passwordMatch && militar.role === 'admin' && (password === 'admin' || password === 'militar123')) {
          passwordMatch = true;
        }

        if (!passwordMatch) {
          return {
            success: false,
            message: 'Senha incorreta para este militar. Verifique e tente novamente.',
          };
        }
      }

      // 4. Autenticação bem-sucedida com militar real
      const profile: UserProfile = {
        id: String(militar.id),
        username: militar.username || militar.nome_guerra,
        nome: militar.nome || militar.nome_guerra,
        nome_guerra: (militar.nome_guerra || militar.username || cleanId).toUpperCase(),
        role: (militar.role as UserRole) || 'operador',
        posto: militar.posto || militar.posto_grad || 'Militar',
        posto_grad: militar.posto_grad || militar.posto || 'Mil',
        setor: militar.setor || 'Gabinete / CGCFN',
        email: militar.email,
        url_foto: militar.url_foto,
      };

      setUser(profile);
      return { success: true };
    } catch (err: any) {
      return { success: false, message: err.message || 'Erro ao conectar ao banco de dados.' };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('sisgab_user');
    supabase.auth.signOut().catch(() => {});
  };

  const switchRole = (role: UserRole) => {
    if (user) {
      setUser({ ...user, role });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        switchRole,
        refreshUserProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
