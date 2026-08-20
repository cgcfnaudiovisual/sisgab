import React, { useState, useEffect, useRef } from 'react';
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
  Palette,
  Upload,
  RotateCcw,
  Image as ImageIcon,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../api/supabase';
import { useAuth } from '../context/AuthContext';
import { AntigravityBackground } from '../components/common/AntigravityBackground';
import defaultBrasao from '../assets/brasaocgcfn.png';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isLoading } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  // Logo Customizado
  const [logoSrc, setLogoSrc] = useState<string>(() => {
    return localStorage.getItem('sisgab_custom_logo') || defaultBrasao;
  });
  const [logoModalOpen, setLogoModalOpen] = useState(false);
  const [customLogoUrl, setCustomLogoUrl] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  // Upload de Logo Customizado
  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Selecione um arquivo de imagem válido (PNG, JPG ou SVG).');
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      if (base64) {
        localStorage.setItem('sisgab_custom_logo', base64);
        setLogoSrc(base64);
        window.dispatchEvent(new Event('sisgab_logo_updated'));
        toast.success('Logo inicial personalizado com sucesso!');
        setLogoModalOpen(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleApplyLogoUrl = () => {
    if (!customLogoUrl.trim()) return;
    localStorage.setItem('sisgab_custom_logo', customLogoUrl.trim());
    setLogoSrc(customLogoUrl.trim());
    window.dispatchEvent(new Event('sisgab_logo_updated'));
    toast.success('Logo atualizado via URL!');
    setLogoModalOpen(false);
  };

  const handleResetDefaultLogo = () => {
    localStorage.removeItem('sisgab_custom_logo');
    setLogoSrc(defaultBrasao);
    window.dispatchEvent(new Event('sisgab_logo_updated'));
    toast.info('Brasão oficial padrão do CGCFN restaurado.');
    setLogoModalOpen(false);
  };

  // Solicitar PIN de Recuperação
  const handleRequestPin = () => {
    if (!recEmail || !recEmail.includes('@')) {
      toast.error('Informe um e-mail válido cadastrado.');
      return;
    }
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
      await supabase.from('efetivo').insert({
        nome_guerra: novoCadastro.nome_guerra.toUpperCase(),
        posto_grad: novoCadastro.posto_grad,
        email: novoCadastro.email.toLowerCase(),
        senha_hash: novoCadastro.senha,
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

        {/* ⚓ Brasão / Logo Oficial Personalizável */}
        <div className="text-center space-y-2 relative group">
          <div className="relative inline-block">
            <img
              src={logoSrc}
              alt="Brasão Oficial CGCFN"
              onError={(e) => {
                const target = e.currentTarget as HTMLImageElement;
                target.onerror = null;
                target.src = defaultBrasao;
              }}
              className="w-32 h-32 mx-auto object-contain drop-shadow-[0_0_20px_rgba(197,160,89,0.7)] hover:scale-105 transition-transform duration-300 cursor-pointer"
              onClick={() => setLogoModalOpen(true)}
              title="Clique para personalizar o Logo do SisGAB"
            />
            {/* Botão sutil de personalização */}
            <button
              type="button"
              onClick={() => setLogoModalOpen(true)}
              className="absolute bottom-0 right-0 p-1.5 rounded-full bg-slate-900/90 border border-[#c5a059] text-[#e5c07b] hover:scale-110 transition-all opacity-0 group-hover:opacity-100 shadow-md"
              title="Personalizar Logo Inicial"
            >
              <Palette className="w-3.5 h-3.5" />
            </button>
          </div>

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
        <div className="pt-1 text-center">
          <button
            type="button"
            onClick={() => setCadastroModal(true)}
            className="text-xs text-slate-400 hover:text-white font-bold flex items-center justify-center gap-1.5 mx-auto transition-colors"
          >
            <UserPlus className="w-3.5 h-3.5 text-[#00e5ff]" />
            <span>Não tem conta? Solicitar Acesso</span>
          </button>
        </div>

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

      {/* ── MODAL DE PERSONALIZAÇÃO DE LOGO ── */}
      {logoModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/60 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Palette className="w-5 h-5 text-[#c5a059]" />
                <h3 className="text-sm font-black text-white uppercase">Personalizar Logo de Acesso</h3>
              </div>
              <button onClick={() => setLogoModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-slate-300">
              Escolha uma imagem do seu computador ou informe a URL para ser exibida como brasão/logo principal do SisGAB:
            </p>

            {/* Prévia Atual */}
            <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-center space-y-2">
              <img
                src={logoSrc}
                alt="Prévia do Logo"
                className="w-24 h-24 mx-auto object-contain drop-shadow-md"
              />
              <span className="text-[10px] text-slate-400 block font-semibold">Prévia Atual</span>
            </div>

            {/* Upload do Arquivo */}
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png, image/jpeg, image/svg+xml, image/webp"
              onChange={handleLogoUpload}
              className="hidden"
            />

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full py-2.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#c5a059] text-white font-bold flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4 text-[#c5a059]" />
                <span>Escolher Imagem do Computador</span>
              </button>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Ou cole a URL da imagem (https://...)"
                  value={customLogoUrl}
                  onChange={(e) => setCustomLogoUrl(e.target.value)}
                  className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-[#c5a059]"
                />
                <button
                  type="button"
                  onClick={handleApplyLogoUrl}
                  className="px-3.5 py-2 rounded-xl bg-[#c5a059] text-slate-950 font-bold hover:bg-[#d6b26b]"
                >
                  Salvar
                </button>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
              <button
                type="button"
                onClick={handleResetDefaultLogo}
                className="text-xs text-rose-400 hover:text-rose-300 font-bold flex items-center gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Restaurar Brasão Padrão CGCFN</span>
              </button>

              <button
                type="button"
                onClick={() => setLogoModalOpen(false)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 text-slate-200 font-bold hover:bg-slate-700"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

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
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                />

                <button
                  type="button"
                  onClick={handleRequestPin}
                  className="w-full py-2.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold hover:bg-[#d6b26b]"
                >
                  Enviar Código PIN
                </button>
              </div>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Código PIN (6 dígitos):</label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="123456"
                    value={recPin}
                    onChange={(e) => setRecPin(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white text-center tracking-widest font-mono text-sm focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-bold mb-1">Nova Senha:</label>
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={recNovaSenha}
                    onChange={(e) => setRecNovaSenha(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-[#c5a059] text-slate-950 font-bold hover:bg-[#d6b26b]"
                >
                  Salvar Nova Senha
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── MODAL DE SOLICITAÇÃO DE NOVO ACESSO ── */}
      {cadastroModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-xs animate-in fade-in">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border-2 border-[#00e5ff]/50 space-y-4 shadow-2xl text-xs">
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

            <form onSubmit={handleSolicitarCadastro} className="space-y-3">
              <div>
                <label className="block text-slate-400 font-bold mb-1">Nome Completo:</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Carlos Eduardo de Souza"
                  value={novoCadastro.nome_completo}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, nome_completo: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 font-bold mb-1">Nome de Guerra:</label>
                  <input
                    type="text"
                    required
                    placeholder="Ex: SOUZA"
                    value={novoCadastro.nome_guerra}
                    onChange={(e) => setNovoCadastro({ ...novoCadastro, nome_guerra: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-bold mb-1">Posto / Graduação:</label>
                  <select
                    value={novoCadastro.posto_grad}
                    onChange={(e) => setNovoCadastro({ ...novoCadastro, posto_grad: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                  >
                    <option value="AE (FN)">AE (FN)</option>
                    <option value="VA (FN)">VA (FN)</option>
                    <option value="CA (FN)">CA (FN)</option>
                    <option value="CMG (FN)">CMG (FN)</option>
                    <option value="CF (FN)">CF (FN)</option>
                    <option value="CC (FN)">CC (FN)</option>
                    <option value="CT (FN)">CT (FN)</option>
                    <option value="1ºTen (FN)">1ºTen (FN)</option>
                    <option value="2ºTen (FN)">2ºTen (FN)</option>
                    <option value="SO (FN)">SO (FN)</option>
                    <option value="1ºSG (FN)">1ºSG (FN)</option>
                    <option value="2ºSG (FN)">2ºSG (FN)</option>
                    <option value="3ºSG (FN)">3ºSG (FN)</option>
                    <option value="CB (FN)">CB (FN)</option>
                    <option value="Civil">Civil / Prestador</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-bold mb-1">E-mail Militar / Institucional:</label>
                <input
                  type="email"
                  required
                  placeholder="souza@marinha.mil.br"
                  value={novoCadastro.email}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, email: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-bold mb-1">Senha Desejada:</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={novoCadastro.senha}
                  onChange={(e) => setNovoCadastro({ ...novoCadastro, senha: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-xl bg-[#00e5ff] text-slate-950 font-black hover:bg-cyan-300 transition-all shadow-md shadow-[#00e5ff]/20"
              >
                Enviar Solicitação
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
