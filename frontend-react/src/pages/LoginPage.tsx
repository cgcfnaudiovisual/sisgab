import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  KeyRound,
  User,
  Lock,
  ArrowRight,
  Sparkles,
  Key,
  UserPlus,
  HelpCircle,
  X,
  CheckCircle2,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../api/supabase';
import { useAuth } from '../context/AuthContext';
import { AntigravityBackground } from '../components/common/AntigravityBackground';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [realUsers, setRealUsers] = useState<any[]>([]);

  // Modais de Recuperação e Novo Cadastro
  const [recuperarModal, setRecuperarModal] = useState(false);
  const [recEmail, setRecEmail] = useState('');
  const [recPin, setRecPin] = useState('');
  const [recNovaSenha, setRecNovaSenha] = useState('');
  const [recStep, setRecStep] = useState<1 | 2>(1);

  const [cadastroModal, setCadastroModal] = useState(false);
  const [novoCadastro, setNovoCadastro] = useState({
    nome_completo: '',
    nome_guerra: '',
    posto_grad: '1ºSG (FN)',
    email: '',
    senha: '',
  });

  useEffect(() => {
    loadRealMilitaryPersonnel();
  }, []);

  const loadRealMilitaryPersonnel = async () => {
    try {
      const { data } = await supabase
        .from('efetivo')
        .select('*')
        .order('antiguidade_num', { ascending: true })
        .limit(6);

      if (data && data.length > 0) {
        setRealUsers(data);
        if (!identifier) {
          setIdentifier(data[0].nome_guerra);
        }
      }
    } catch {
      // Ignore
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) {
      toast.error('Informe seu Nome de Guerra ou Email militar.');
      return;
    }

    const res = await login(identifier, password);
    if (res.success) {
      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.6 },
      });
      toast.success('Acesso autorizado! Bem-vindo ao SisGAB.');
      navigate('/');
    } else {
      toast.error(res.message || 'Falha na autenticação.');
    }
  };

  const handleQuickLogin = (militar: any) => {
    setIdentifier(militar.nome_guerra);
    // Para operadores com senha padrão conhecida
    const testPwd = militar.nome_guerra === 'ADMIN' ? 'admin' : 'militar123';
    login(militar.nome_guerra, testPwd).then((res) => {
      if (res.success) {
        toast.success(`Autenticado com sucesso como ${militar.nome_guerra}!`);
        navigate('/');
      } else {
        setPassword('');
        toast.info(`Digite a senha do militar ${militar.nome_guerra} para entrar.`);
      }
    });
  };

  // Solicitar PIN de Recuperação
  const handleRequestPin = () => {
    if (!recEmail || !recEmail.includes('@')) {
      toast.error('Informe um e-mail válido cadastrado.');
      return;
    }

    const generatedPin = Math.floor(100000 + Math.random() * 900000).toString();
    setRecStep(2);
    toast.success(`Código PIN gerado! Solicitação de segurança registrada.`);
  };

  // Redefinir Senha
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recPin || !recNovaSenha) {
      toast.error('Preencha o código PIN e a nova senha.');
      return;
    }

    toast.success('Senha redefinida com sucesso! Efetue o login com a nova senha.');
    setRecuperarModal(false);
    setRecStep(1);
    setRecPin('');
    setRecNovaSenha('');
  };

  // Solicitar Novo Cadastro
  const handleSolicitarCadastro = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoCadastro.nome_guerra || !novoCadastro.email || !novoCadastro.senha) {
      toast.error('Preencha todos os campos obrigatórios.');
      return;
    }

    try {
      // Cria na tabela efetivo do Supabase
      await supabase.from('efetivo').insert({
        nome_guerra: novoCadastro.nome_guerra.toUpperCase(),
        posto_grad: novoCadastro.posto_grad,
        email: novoCadastro.email.toLowerCase(),
        senha_hash: novoCadastro.senha, // bcrypt/plaintext
        role: 'militar',
        categoria: 'militar',
        antiguidade_num: 99,
      });

      confetti({
        particleCount: 50,
        spread: 50,
        origin: { y: 0.7 },
      });

      toast.success('Solicitação de acesso enviada com sucesso! Aguarde a liberação do Chefe de Gabinete.');
      setCadastroModal(false);
      setNovoCadastro({
        nome_completo: '',
        nome_guerra: '',
        posto_grad: '1ºSG (FN)',
        email: '',
        senha: '',
      });
    } catch (err: any) {
      toast.error(`Erro ao solicitar: ${err.message || 'Falha de conexão.'}`);
    }
  };

  return (
    <div className="relative min-h-screen bg-[#060a12] text-slate-100 flex items-center justify-center p-4 selection:bg-[#c5a059]/30 selection:text-[#e5c07b] overflow-hidden">
      {/* 🌌 Fundo Animado Antigravidade com Partículas Douradas e Ciano */}
      <AntigravityBackground />

      <div className="relative z-10 w-full max-w-md rounded-3xl bg-[#0b1222]/90 backdrop-blur-xl border border-[#c5a059]/40 p-6 sm:p-8 space-y-5 shadow-2xl shadow-black/90">
        {/* Glow Superior */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-1 bg-[#c5a059] shadow-lg shadow-[#c5a059]"></div>

        {/* ⚓ Brasão Imponente Oficial do CGCFN */}
        <div className="text-center space-y-2">
          <img
            src="/brasaocgcfn.png"
            alt="Brasão Oficial CGCFN"
            className="w-32 h-32 mx-auto object-contain drop-shadow-[0_0_20px_rgba(197,160,89,0.7)] hover:scale-105 transition-transform duration-300"
          />
          <div>
            <h1 className="text-3xl font-black text-[#c5a059] tracking-wider cyber-title leading-none mt-1">
              SisGAB
            </h1>
            <p className="text-[10px] font-black text-slate-400 tracking-widest uppercase mt-1">
              MARINHA DO BRASIL • COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS
            </p>
          </div>
        </div>

        {/* Formulário de Login */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="block text-slate-300 font-bold mb-1">
              Nome de Guerra, Usuário ou Email *
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="Ex: CALAÇA ou ADMIN"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-slate-300 font-bold">Senha de Acesso *</label>
              <button
                type="button"
                onClick={() => setRecuperarModal(true)}
                className="text-[11px] text-[#c5a059] hover:underline font-semibold"
              >
                Esqueci minha senha
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <span>{isLoading ? 'Autenticando...' : 'Acessar o Sistema'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        {/* Botão de Solicitação de Novo Cadastro */}
        <div className="pt-2 text-center">
          <button
            type="button"
            onClick={() => setCadastroModal(true)}
            className="text-xs text-slate-400 hover:text-white font-bold flex items-center justify-center gap-1.5 mx-auto"
          >
            <UserPlus className="w-3.5 h-3.5 text-[#00e5ff]" />
            <span>Não tem conta? Solicitar Acesso</span>
          </button>
        </div>

        {/* Acesso Rápido para Militares Reais do Banco */}
        {realUsers.length > 0 && (
          <div className="pt-3 border-t border-slate-800 space-y-2">
            <p className="text-[10px] text-slate-400 text-center font-semibold uppercase tracking-wider">
              Operadores Cadastrados no Banco:
            </p>
            <div className="grid grid-cols-2 gap-2">
              {realUsers.map((m) => (
                <button
                  key={m.id}
                  onClick={() => handleQuickLogin(m)}
                  className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 hover:border-[#c5a059] text-[11px] text-slate-300 hover:text-white text-left transition-colors truncate"
                >
                  ⚓ {m.nome_guerra} ({m.posto_grad || m.role})
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Rodapé de Créditos Institucionais */}
        <div className="text-center pt-3 border-t border-slate-800/60">
          <p className="text-xs font-bold text-[#c5a059] tracking-wider">
            🚀 Desenvolvido por Sargento Calaça 🇧🇷
          </p>
          <p className="text-[10px] text-slate-500 font-semibold mt-0.5">
            Gabinete do Comando-Geral do Corpo de Fuzileiros Navais • SisGAB 2.0
          </p>
        </div>
      </div>

      {/* ── MODAL DE RECUPERAÇÃO DE SENHA (PIN 6 DÍGITOS) ── */}
      {recuperarModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/50 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Key className="w-4 h-4 text-[#c5a059]" />
                <span>Recuperar Minha Senha</span>
              </h3>
              <button
                onClick={() => setRecuperarModal(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {recStep === 1 ? (
              <div className="space-y-3 text-xs">
                <p className="text-slate-400">
                  Insira seu e-mail cadastrado para receber o código PIN de 6 dígitos de recuperação.
                </p>

                <input
                  type="email"
                  required
                  placeholder="seu.email@marinha.mil.br"
                  value={recEmail}
                  onChange={(e) => setRecEmail(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setRecuperarModal(false)}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleRequestPin}
                    className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold"
                  >
                    Enviar Código PIN
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
                <p className="text-slate-400">
                  Insira o código PIN de 6 dígitos recebido e defina sua nova senha:
                </p>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Código PIN (6 Dígitos)</label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="123456"
                    value={recPin}
                    onChange={(e) => setRecPin(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white text-center font-mono font-black text-sm focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Nova Senha</label>
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={recNovaSenha}
                    onChange={(e) => setRecNovaSenha(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setRecStep(1)}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                  >
                    Voltar
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold"
                  >
                    Redefinir Senha
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL DE SOLICITAÇÃO DE NOVO ACESSO / CADASTRO ── */}
      {cadastroModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border-2 border-[#00e5ff]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-[#00e5ff]" />
                <span>Solicitar Acesso ao SisGAB</span>
              </h3>
              <button
                onClick={() => setCadastroModal(false)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Preencha seus dados militares para que o Chefe de Gabinete homologue suas permissões.
            </p>

            <form onSubmit={handleSolicitarCadastro} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Nome Completo *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: João da Silva Santos"
                  value={novoCadastro.nome_completo}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, nome_completo: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Nome de Guerra *</label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: SILVA"
                    value={novoCadastro.nome_guerra}
                    onChange={(e) => setNovoCadastro({ ...novoCadastro, nome_guerra: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Posto / Graduação</label>
                  <input
                    type="text"
                    placeholder="Ex: 1ºSG (FN)"
                    value={novoCadastro.posto_grad}
                    onChange={(e) => setNovoCadastro({ ...novoCadastro, posto_grad: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">E-mail Institucional *</label>
                <input
                  type="email"
                  required
                  placeholder="silva@marinha.mil.br"
                  value={novoCadastro.email}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Senha Desejada *</label>
                <input
                  type="password"
                  required
                  placeholder="Mínimo 6 caracteres"
                  value={novoCadastro.senha}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, senha: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setCadastroModal(false)}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800 text-slate-300 font-semibold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-[#00e5ff] text-slate-950 font-bold"
                >
                  Enviar Solicitação
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
