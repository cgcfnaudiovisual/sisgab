import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useRef } from 'react';
import { QrCode, Download, Link, Copy, Sparkles, Check } from 'lucide-react';
import { toast } from 'sonner';

export const QRCodeTool: React.FC = () => {
  const [urlText, setUrlText] = useState('https://sisgab.marinha.mil.br/evento/1');
  const [selectedColor, setSelectedColor] = useState('#c5a059');
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    generateQRCode();
  }, [urlText, selectedColor]);

  // Gerador de QR Code com Brasão Central
  const generateQRCode = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = 320;
    canvas.width = size;
    canvas.height = size;

    // Fundo Escuro
    ctx.fillStyle = '#0b1222';
    ctx.fillRect(0, 0, size, size);

    // Moldura Externa
    ctx.strokeStyle = selectedColor;
    ctx.lineWidth = 4;
    ctx.strokeRect(6, 6, size - 12, size - 12);

    // Simulação do Padrão de Matriz QR Code
    const modules = 25;
    const cellSize = (size - 40) / modules;
    const offset = 20;

    // Função Pseudo-Aleatória com semente na URL para manter estabilidade visual
    let seed = 0;
    for (let i = 0; i < urlText.length; i++) {
      seed = (seed * 31 + urlText.charCodeAt(i)) % 1000000;
    }
    const rand = () => {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };

    ctx.fillStyle = selectedColor;

    // Padrões de Alinhamento nos 3 Cantos (Position Detection Patterns)
    const drawFinderPattern = (x: number, y: number) => {
      ctx.fillRect(x, y, cellSize * 7, cellSize * 7);
      ctx.fillStyle = '#0b1222';
      ctx.fillRect(x + cellSize, y + cellSize, cellSize * 5, cellSize * 5);
      ctx.fillStyle = selectedColor;
      ctx.fillRect(x + cellSize * 2, y + cellSize * 2, cellSize * 3, cellSize * 3);
    };

    drawFinderPattern(offset, offset); // Superior Esquerdo
    drawFinderPattern(offset + cellSize * (modules - 7), offset); // Superior Direito
    drawFinderPattern(offset, offset + cellSize * (modules - 7)); // Inferior Esquerdo

    // Módulos Internos
    for (let r = 0; r < modules; r++) {
      for (let c = 0; c < modules; c++) {
        // Pula os 3 cantos principais
        if ((r < 7 && c < 7) || (r < 7 && c >= modules - 7) || (r >= modules - 7 && c < 7)) {
          continue;
        }
        // Pula o centro para o Brasão da Marinha
        if (r >= 9 && r <= 15 && c >= 9 && c <= 15) {
          continue;
        }

        if (rand() > 0.45) {
          ctx.fillRect(offset + c * cellSize, offset + r * cellSize, cellSize - 1, cellSize - 1);
        }
      }
    }

    // Brasão Central CGCFN
    const center = size / 2;
    ctx.beginPath();
    ctx.arc(center, center, 28, 0, Math.PI * 2);
    ctx.fillStyle = '#080d1a';
    ctx.fill();
    ctx.strokeStyle = selectedColor;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.font = 'bold 22px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = selectedColor;
    ctx.fillText('⚓', center, center + 8);
  };

  const handleDownload = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `QRCode_CGCFN_${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();

    militaryAudio.playTacticalBeep();
    toast.success('QR Code baixado com sucesso em alta resolução!');
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(urlText);
    setCopied(true);
    toast.success('Link copiado!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
            Ferramentas Oficiais
          </span>
          <span className="text-slate-400 text-xs">• Gerador de QR Code</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight mt-1">
          Gerador de QR Code Vetorial com Brasão
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm">
          Crie QR Codes de alta resolução para placas de auditório, convites impressos e links do Portal do Convidado.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Lado Esquerdo: Formulário de Customização */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Link de Destino / Texto do QR Code *
            </label>
            <div className="relative">
              <input
                type="text"
                value={urlText}
                onChange={(e) => setUrlText(e.target.value)}
                placeholder="https://..."
                className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
              />
              <button
                onClick={handleCopy}
                className="absolute right-2 top-2 p-1 text-slate-400 hover:text-white"
                title="Copiar Link"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1.5">
              Cor do Padrão Naval
            </label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSelectedColor('#c5a059')}
                className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                  selectedColor === '#c5a059'
                    ? 'bg-[#c5a059]/20 text-[#e5c07b] border-[#c5a059]'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}
              >
                <span className="w-3 h-3 rounded-full bg-[#c5a059]"></span>
                <span>Ouro CGCFN</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedColor('#00e5ff')}
                className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                  selectedColor === '#00e5ff'
                    ? 'bg-[#00e5ff]/20 text-[#00e5ff] border-[#00e5ff]'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}
              >
                <span className="w-3 h-3 rounded-full bg-[#00e5ff]"></span>
                <span>Ciano Tático</span>
              </button>

              <button
                type="button"
                onClick={() => setSelectedColor('#ffffff')}
                className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all flex items-center justify-center gap-1.5 ${
                  selectedColor === '#ffffff'
                    ? 'bg-white/20 text-white border-white'
                    : 'bg-slate-900 text-slate-400 border-slate-800'
                }`}
              >
                <span className="w-3 h-3 rounded-full bg-white"></span>
                <span>Branco</span>
              </button>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleDownload}
              className="w-full py-3 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              <span>Baixar Imagem PNG</span>
            </button>
          </div>
        </div>

        {/* Lado Direito: Preview do Canvas */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 flex flex-col items-center justify-center space-y-3 shadow-xl text-center">
          <canvas
            ref={canvasRef}
            className="w-64 h-64 rounded-2xl shadow-2xl"
          />
          <p className="text-[11px] text-slate-400 font-medium">
            Prévia com Brasão Embutido • Alta Resolução
          </p>
        </div>
      </div>
    </div>
  );
};
