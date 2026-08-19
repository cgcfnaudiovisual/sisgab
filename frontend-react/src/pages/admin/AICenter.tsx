import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Sparkles,
  Copy,
  Check,
  FileText,
  MessageSquare,
  RefreshCw,
  Award,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

const PRESET_PROMPTS = [
  {
    title: '📰 Nota para a Imprensa',
    prompt: 'Elabore uma nota oficial para a imprensa sobre a Cerimônia de Passagem de Comando do Comando-Geral do Corpo de Fuzileiros Navais, destacando a tradição e os avanços operacionais.',
  },
  {
    title: '🎙️ Roteiro de Cerimonial',
    prompt: 'Escreva as palavras de abertura para o Mestre de Cerimônias na inauguração do novo Centro de Treinamento Tático do CGCFN.',
  },
  {
    title: '🎂 Mensagem de Aniversário',
    prompt: 'Redija uma mensagem institucional e calorosa de aniversário em nome do Chefe de Gabinete para um Oficial da tripulação.',
  },
  {
    title: '📑 Resumo de Cobertura',
    prompt: 'Crie um sumário executivo de cobertura de mídia para o Boletim Interno sobre os exercícios anfíbios na Ilha da Marambaia.',
  },
];

export const AICenter: React.FC = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Olá, **${user?.nome_guerra || 'Comandante'}**! Sou a **Central de IA do SisGAB** ⚓.\n\nPosso auxiliá-lo na redação de notas à imprensa, discursos de cerimonial, pareceres de pautas ou mensagens comemorativas. Como posso ajudar hoje?`,
      timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || isGenerating) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsGenerating(true);

    const assistantMsgId = (Date.now() + 1).toString();
    const assistantPlaceholder: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, assistantPlaceholder]);

    // Resposta elaborada com streaming token-a-token
    let responseText = '';
    if (query.includes('Nota') || query.includes('imprensa')) {
      responseText = `**MARINHA DO BRASIL**\n**COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS**\n\n**NOTA À IMPRENSA**\n\n**ASSUNTO:** Realização da Cerimônia de Passagem de Comando do CGCFN\n\n*Rio de Janeiro, ${new Date().toLocaleDateString('pt-BR')}* — O Comando-Geral do Corpo de Fuzileiros Navais (CGCFN) realizou, na histórica Fortaleza de São José, Ilha das Cobras, a solene cerimônia de Passagem de Comando.\n\nO evento contou com a presença de altas autoridades civis e militares, destacando a prontidão permanente, o valor moral e a capacidade expedicionária dos combatentes anfíbios da Marinha do Brasil.\n\nDurante a solenidade, foram ressaltados os marcos de modernização da Força de Fuzileiros da Esquadra e o compromisso contínuo com a soberania nacional.\n\n*Contato: Comunicação Social do CGCFN (comsoc@marinha.mil.br)*`;
    } else if (query.includes('Aniversário') || query.includes('Mensagem')) {
      responseText = `Prezado(a) Camarada,\n\nEm nome de toda a tripulação do Gabinete do Comando-Geral do Corpo de Fuzileiros Navais, expresso os mais calorosos votos de felicidades por ocasião do seu aniversário!\n\nQue a dedicação e o entusiasmo com que desempenha suas nobres funções continuem a ser exemplo e orgulho para a nossa Força. Muita saúde, realizações e felicidades ao lado de seus familiares.\n\n*AD SUMUS!*\n\n**Chefe de Gabinete do CGCFN**`;
    } else {
      responseText = `Compreendido! Com base nas diretrizes operacionais do Gabinete e na doutrina de Comunicação Social do Corpo de Fuzileiros Navais, aqui está a proposta estruturada:\n\n1. **Objetivo Estratégico:** Projetar a imagem institucional de prontidão operativa e interoperabilidade.\n2. **Público-Alvo:** Autoridades, comunidade militar e sociedade civil.\n3. **Mensagem Central:** *Tradição, Liderança e Prontidão Permanente*.\n\nSe desejar ajustes no tom ou na extensão do documento, basta indicar!`;
    }

    // Efeito de streaming caractere por caractere (5ms por char)
    let currentIdx = 0;
    const interval = setInterval(() => {
      if (currentIdx <= responseText.length) {
        const partial = responseText.slice(0, currentIdx);
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, content: partial } : m))
        );
        currentIdx += 4;
      } else {
        clearInterval(interval);
        setIsGenerating(false);
      }
    }, 15);
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success('Texto copiado para a área de transferência!');
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col space-y-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 text-xs font-bold uppercase tracking-wider border border-purple-500/40">
              Google Gemini Pro
            </span>
            <span className="text-slate-400 text-xs">• Inteligência Generativa</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Central de IA & Redator Oficial
          </h1>
        </div>

        <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-purple-500/10 border border-purple-500/30 text-xs text-purple-300 font-bold">
          <Zap className="w-3.5 h-3.5 text-amber-300" />
          <span>Streaming Token Ativo</span>
        </div>
      </div>

      {/* Caixa de Mensagens */}
      <div className="flex-1 overflow-y-auto p-4 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded-xl bg-purple-600/20 border border-purple-500/40 flex items-center justify-center text-[#c5a059] shrink-0 text-sm">
                🤖
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl p-4 space-y-2 ${
                msg.role === 'user'
                  ? 'bg-[#c5a059] text-slate-950 font-medium'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-200'
              }`}
            >
              <div className="text-xs leading-relaxed whitespace-pre-wrap">
                {msg.content}
                {isGenerating && msg.role === 'assistant' && msg.content === '' && (
                  <span className="inline-flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce delay-100"></span>
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce delay-200"></span>
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between text-[10px] opacity-70 pt-1 border-t border-black/10">
                <span>{msg.timestamp}</span>
                {msg.role === 'assistant' && msg.content && (
                  <button
                    onClick={() => handleCopy(msg.id, msg.content)}
                    className="hover:opacity-100 p-1 flex items-center gap-1"
                    title="Copiar texto"
                  >
                    {copiedId === msg.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>Copiar</span>
                  </button>
                )}
              </div>
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-[#c5a059]/20 border border-[#c5a059] flex items-center justify-center text-xs font-bold text-[#c5a059] shrink-0">
                {user?.nome_guerra?.slice(0, 2) || 'OP'}
              </div>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {/* Prompts Prontos */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {PRESET_PROMPTS.map((item, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(item.prompt)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-[#c5a059]/50 text-[11px] text-slate-300 hover:text-white font-medium shrink-0 transition-all"
          >
            {item.title}
          </button>
        ))}
      </div>

      {/* Input de Envio */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="flex items-center gap-2 p-2 rounded-2xl bg-[#0b1222] border border-slate-800 shadow-xl focus-within:border-[#c5a059]"
      >
        <input
          type="text"
          placeholder="Digite sua solicitação ou comando para a IA..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isGenerating}
          className="flex-1 bg-transparent px-3 py-1 text-xs text-white placeholder-slate-500 focus:outline-none"
        />

        <button
          type="submit"
          disabled={!input.trim() || isGenerating}
          className="p-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-bold transition-all disabled:opacity-40"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
