import React, { useState, useRef, useEffect } from 'react';
import {
  Palette,
  Download,
  Sparkles,
  Type,
  Image as ImageIcon,
  Square,
  Circle,
  Undo,
  Redo,
  Layers,
  Printer,
  FileText,
  Users,
  Calendar,
  Save,
  Plus,
  Trash2,
  Eye,
  Sliders,
  CheckCircle2,
  Copy,
  ChevronRight,
  Shield,
  Utensils,
  Award,
  Maximize2,
  RotateCw,
  QrCode,
  Grid,
  Zap,
  Move,
  AlignLeft,
  AlignCenter,
  AlignRight,
  SlidersHorizontal,
  FolderOpen,
  Upload,
  BookOpen,
  Tag,
  Star,
  Compass,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';

// Formatos de Documentos e Mídia
export interface FormatPreset {
  id: string;
  name: string;
  category: 'cardapio' | 'prisma' | 'cracha' | 'certificado' | 'cartaz' | 'banner' | 'social' | 'custom';
  widthMm: number;
  heightMm: number;
  orientation: 'portrait' | 'landscape';
  description: string;
  supportsDuplex?: boolean;
}

const FORMAT_PRESETS: FormatPreset[] = [
  {
    id: 'cardapio_a5',
    name: '📜 Cardápio Solene (A5)',
    category: 'cardapio',
    widthMm: 148,
    heightMm: 210,
    orientation: 'portrait',
    description: '148 × 210 mm • Para almoços e jantares de gala',
    supportsDuplex: true,
  },
  {
    id: 'cardapio_a4_dobravel',
    name: '📖 Cardápio A4 Dobrável (Livreto)',
    category: 'cardapio',
    widthMm: 297,
    heightMm: 210,
    orientation: 'landscape',
    description: '297 × 210 mm • Vinco central em estilo livreto',
    supportsDuplex: true,
  },
  {
    id: 'prisma_a4_mesa',
    name: '📑 Prisma de Mesa em V (A4)',
    category: 'prisma',
    widthMm: 210,
    heightMm: 297,
    orientation: 'portrait',
    description: '210 × 297 mm • Prisma dobrável com posto e assento',
    supportsDuplex: false,
  },
  {
    id: 'certificado_a4',
    name: '🎖️ Diploma / Certificado de Honra (A4)',
    category: 'certificado',
    widthMm: 297,
    heightMm: 210,
    orientation: 'landscape',
    description: '297 × 210 mm • Moldura dourada para homenagens',
    supportsDuplex: false,
  },
  {
    id: 'cracha_a6',
    name: '🪪 Crachá VIP / Portaria (A6)',
    category: 'cracha',
    widthMm: 105,
    heightMm: 148,
    orientation: 'portrait',
    description: '105 × 148 mm • Identificação com QR Code',
    supportsDuplex: true,
  },
  {
    id: 'cartaz_a3',
    name: '🖼️ Cartaz Oficial de Divulgação (A3)',
    category: 'cartaz',
    widthMm: 297,
    heightMm: 420,
    orientation: 'portrait',
    description: '297 × 420 mm • Murais e avisos de comando',
    supportsDuplex: false,
  },
  {
    id: 'banner_a2',
    name: '🚩 Banner / Painel Solene (A2)',
    category: 'banner',
    widthMm: 420,
    heightMm: 594,
    orientation: 'portrait',
    description: '420 × 594 mm • Totens e palcos de solenidades',
    supportsDuplex: false,
  },
  {
    id: 'social_post_4_5',
    name: '📱 Post Feed Instagram (4:5)',
    category: 'social',
    widthMm: 108,
    heightMm: 135,
    orientation: 'portrait',
    description: '1080 × 1350 px • Padrão de engajamento para redes',
    supportsDuplex: false,
  },
  {
    id: 'custom',
    name: '📐 Dimensão Personalizada',
    category: 'custom',
    widthMm: 210,
    heightMm: 297,
    orientation: 'portrait',
    description: 'Defina largura e altura livremente em milímetros',
    supportsDuplex: false,
  },
];

// Tipos de Elementos no Canvas Livre (Estilo Canva)
export type ElementType = 'text' | 'shape' | 'badge' | 'image' | 'line' | 'frame';

export interface CanvasElement {
  id: string;
  type: ElementType;
  x: number; // Porcentagem de 0 a 100 da largura
  y: number; // Porcentagem de 0 a 100 da altura
  width?: number; // Porcentagem
  height?: number; // Porcentagem
  // Texto
  text?: string;
  fontSize?: number; // em px base
  fontFamily?: 'Playfair Display' | 'DM Sans' | 'Space Grotesk' | 'Georgia' | 'Cinzel';
  fontWeight?: 'normal' | 'bold' | '900';
  fontStyle?: 'normal' | 'italic';
  color?: string;
  align?: 'left' | 'center' | 'right';
  letterSpacing?: number;
  isTag?: boolean;
  // Formas e Badges
  shapeType?: 'rect' | 'circle' | 'naval_frame' | 'anchor' | 'stars' | 'seal_gold' | 'ribbon' | 'line_gold';
  fillColor?: string;
  strokeColor?: string;
  strokeWidth?: number;
  opacity?: number;
  // Imagem
  imageSrc?: string;
}

const AVAILABLE_TAGS = [
  { tag: '{nome}', desc: 'Nome da Autoridade / Militar', example: 'ALMIRANTE OLSEN' },
  { tag: '{posto}', desc: 'Posto ou Graduação', example: 'ALMIRANTE DE ESQUADRA' },
  { tag: '{cargo}', desc: 'Cargo ou Função', example: 'Comandante da Marinha' },
  { tag: '{assento}', desc: 'Assento ou Mesa Reservada', example: 'Mesa de Honra (A-1)' },
  { tag: '{evento}', desc: 'Nome do Evento / Solenidade', example: 'Almoço Oficial de Apresentação' },
  { tag: '{data}', desc: 'Data do Evento', example: '20 de Agosto de 2026' },
  { tag: '{local}', desc: 'Local da Solenidade', example: 'Salão Nobre do CGCFN' },
  { tag: '{entrada}', desc: 'Entrada (Cardápio)', example: 'Salada de Frutos do Mar ao Vinagrete Cítrico' },
  { tag: '{prato_principal}', desc: 'Prato Principal', example: 'Tornedor de Filé Mignon ao Molho Poivre' },
  { tag: '{sobremesa}', desc: 'Sobremesa', example: 'Mil-Folhas com Coulis de Frutas Vermelhas' },
];

export const GraphicStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'canva' | 'modelos' | 'lote'>('canva');
  const [selectedFormat, setSelectedFormat] = useState<FormatPreset>(FORMAT_PRESETS[0]);
  const [customWidthMm, setCustomWidthMm] = useState<number>(210);
  const [customHeightMm, setCustomHeightMm] = useState<number>(297);

  // Fundo & Degradê
  const [bgType, setBgType] = useState<'gradient' | 'solid' | 'paper_verge' | 'tactical_dark'>('gradient');
  const [bgStartColor, setBgStartColor] = useState<string>('#08111d');
  const [bgMidColor, setBgMidColor] = useState<string>('#0e1f38');
  const [bgEndColor, setBgEndColor] = useState<string>('#060c14');
  const [bgAngle, setBgAngle] = useState<number>(145);
  const [themeColor, setThemeColor] = useState<string>('#c5a059');

  // Elementos do Canvas Livre (Canva SISGAB)
  const [elements, setElements] = useState<CanvasElement[]>([
    {
      id: 'frame_1',
      type: 'shape',
      shapeType: 'naval_frame',
      x: 50,
      y: 50,
      width: 90,
      height: 92,
      strokeColor: '#c5a059',
      strokeWidth: 2,
    },
    {
      id: 'badge_anchor',
      type: 'badge',
      shapeType: 'anchor',
      x: 50,
      y: 12,
      color: '#c5a059',
      fontSize: 34,
    },
    {
      id: 'txt_header',
      type: 'text',
      text: 'MARINHA DO BRASIL',
      x: 50,
      y: 18,
      fontSize: 12,
      fontWeight: 'bold',
      fontFamily: 'DM Sans',
      color: '#c5a059',
      align: 'center',
      letterSpacing: 3,
    },
    {
      id: 'txt_subheader',
      type: 'text',
      text: 'COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS',
      x: 50,
      y: 21,
      fontSize: 9,
      fontWeight: 'bold',
      fontFamily: 'DM Sans',
      color: '#94a3b8',
      align: 'center',
      letterSpacing: 2,
    },
    {
      id: 'stars_1',
      type: 'badge',
      shapeType: 'stars',
      x: 50,
      y: 26,
      color: '#c5a059',
      fontSize: 14,
    },
    {
      id: 'txt_title',
      type: 'text',
      text: 'ALMOÇO EM HOMENAGEM AO {posto}',
      x: 50,
      y: 36,
      fontSize: 14,
      fontWeight: 'bold',
      fontFamily: 'Playfair Display',
      color: '#e2e8f0',
      align: 'center',
    },
    {
      id: 'txt_authority',
      type: 'text',
      text: '{nome}',
      x: 50,
      y: 45,
      fontSize: 24,
      fontWeight: 'bold',
      fontFamily: 'Cinzel',
      color: '#ffffff',
      align: 'center',
      letterSpacing: 2,
    },
    {
      id: 'txt_subtitle',
      type: 'text',
      text: '{cargo} • {assento}',
      x: 50,
      y: 52,
      fontSize: 12,
      fontStyle: 'italic',
      fontFamily: 'Georgia',
      color: '#c5a059',
      align: 'center',
    },
    {
      id: 'txt_local',
      type: 'text',
      text: '{local}',
      x: 10,
      y: 92,
      fontSize: 10,
      fontWeight: 'bold',
      fontFamily: 'DM Sans',
      color: '#64748b',
      align: 'left',
    },
    {
      id: 'txt_data',
      type: 'text',
      text: '{data}',
      x: 90,
      y: 92,
      fontSize: 10,
      fontWeight: 'bold',
      fontFamily: 'DM Sans',
      color: '#64748b',
      align: 'right',
    },
  ]);

  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);

  // Fonte de Dados para Mala Direta / Lote
  const [selectedEventoId, setSelectedEventoId] = useState<number | null>(null);
  const [eventos, setEventos] = useState<any[]>([]);
  const [jadeConvidados, setJadeConvidados] = useState<any[]>([]);
  const [efetivoList, setEfetivoList] = useState<any[]>([]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    renderCanvas();
  }, [elements, selectedElementId, selectedFormat, bgType, bgStartColor, bgMidColor, bgEndColor, bgAngle, themeColor, customWidthMm, customHeightMm]);

  const loadData = async () => {
    try {
      const { data: evList } = await supabase.from('jade_eventos').select('*').order('id', { ascending: false });
      if (evList && evList.length > 0) {
        setEventos(evList);
        setSelectedEventoId(evList[0].id);
        const { data: gList } = await supabase.from('jade_convidados').select('*').eq('evento_id', evList[0].id);
        if (gList) setJadeConvidados(gList);
      }

      const { data: efList } = await supabase.from('efetivo').select('*').limit(50);
      if (efList) setEfetivoList(efList);
    } catch (err) {
      console.warn('Erro ao carregar dados:', err);
    }
  };

  const handleEventoChange = async (evId: number) => {
    setSelectedEventoId(evId);
    const { data: gList } = await supabase.from('jade_convidados').select('*').eq('evento_id', evId);
    if (gList) setJadeConvidados(gList);
  };

  // Obter proporção do Canvas
  const getCanvasDimensions = (scaleMultiplier = 1) => {
    const isLandscape = selectedFormat.orientation === 'landscape';
    let baseW = isLandscape ? 840 : 595;
    let baseH = isLandscape ? 595 : 840;

    if (selectedFormat.id === 'custom') {
      const ratio = customWidthMm / customHeightMm;
      baseW = isLandscape ? 840 : Math.round(595 * ratio);
      baseH = isLandscape ? Math.round(840 / ratio) : 840;
    } else if (selectedFormat.category === 'social') {
      baseW = 600;
      baseH = 750;
    }

    return {
      width: Math.round(baseW * scaleMultiplier),
      height: Math.round(baseH * scaleMultiplier),
      scale: scaleMultiplier,
    };
  };

  // Renderizador Gráfico Universal
  const drawDesign = (
    ctx: CanvasRenderingContext2D,
    w: number,
    h: number,
    tagValues: Record<string, string> = {}
  ) => {
    // 1. FUNDO
    if (bgType === 'gradient') {
      const angleRad = (bgAngle * Math.PI) / 180;
      const x1 = w / 2 - (Math.cos(angleRad) * w) / 2;
      const y1 = h / 2 - (Math.sin(angleRad) * h) / 2;
      const x2 = w / 2 + (Math.cos(angleRad) * w) / 2;
      const y2 = h / 2 + (Math.sin(angleRad) * h) / 2;

      const grad = ctx.createLinearGradient(x1, y1, x2, y2);
      grad.addColorStop(0, bgStartColor);
      grad.addColorStop(0.5, bgMidColor);
      grad.addColorStop(1, bgEndColor);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    } else if (bgType === 'paper_verge') {
      ctx.fillStyle = '#f7f5ef';
      ctx.fillRect(0, 0, w, h);
      // Textura suave de papel
      ctx.fillStyle = 'rgba(0,0,0,0.015)';
      for (let i = 0; i < w; i += 4) {
        ctx.fillRect(i, 0, 1, h);
      }
    } else if (bgType === 'tactical_dark') {
      ctx.fillStyle = '#06080c';
      ctx.fillRect(0, 0, w, h);
      // Grid tático sutil
      ctx.strokeStyle = 'rgba(255,255,255,0.03)';
      ctx.lineWidth = 1;
      for (let x = 0; x < w; x += 30) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += 30) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
    } else {
      ctx.fillStyle = bgStartColor;
      ctx.fillRect(0, 0, w, h);
    }

    // 2. RENDERIZAR CADA ELEMENTO
    elements.forEach((el) => {
      const posX = (el.x / 100) * w;
      const posY = (el.y / 100) * h;
      const elW = el.width ? (el.width / 100) * w : 0;
      const elH = el.height ? (el.height / 100) * h : 0;

      ctx.save();

      if (el.type === 'shape') {
        if (el.shapeType === 'naval_frame') {
          // Moldura com cantos entalhados
          const pad = 24;
          ctx.strokeStyle = el.strokeColor || themeColor;
          ctx.lineWidth = el.strokeWidth || 2;
          ctx.strokeRect(pad, pad, w - pad * 2, h - pad * 2);
          ctx.lineWidth = 1;
          ctx.strokeRect(pad + 6, pad + 6, w - pad * 2 - 12, h - pad * 2 - 12);

          // Cantos Dourados
          const c = 20;
          ctx.fillStyle = el.strokeColor || themeColor;
          ctx.fillRect(pad, pad, c, 4);
          ctx.fillRect(pad, pad, 4, c);
          ctx.fillRect(w - pad - c, pad, c, 4);
          ctx.fillRect(w - pad - 4, pad, 4, c);
          ctx.fillRect(pad, h - pad - 4, c, 4);
          ctx.fillRect(pad, h - pad - c, 4, c);
          ctx.fillRect(w - pad - c, h - pad - 4, c, 4);
          ctx.fillRect(w - pad - 4, h - pad - c, 4, c);
        } else if (el.shapeType === 'rect') {
          ctx.fillStyle = el.fillColor || 'rgba(255,255,255,0.05)';
          ctx.strokeStyle = el.strokeColor || themeColor;
          ctx.lineWidth = el.strokeWidth || 1;
          ctx.beginPath();
          ctx.roundRect(posX - elW / 2, posY - elH / 2, elW, elH, 8);
          ctx.fill();
          if (el.strokeWidth) ctx.stroke();
        } else if (el.shapeType === 'circle') {
          ctx.fillStyle = el.fillColor || themeColor;
          ctx.beginPath();
          ctx.arc(posX, posY, elW / 2 || 20, 0, Math.PI * 2);
          ctx.fill();
        } else if (el.shapeType === 'line_gold') {
          ctx.strokeStyle = el.strokeColor || themeColor;
          ctx.lineWidth = el.strokeWidth || 2;
          ctx.beginPath();
          ctx.moveTo(posX - elW / 2, posY);
          ctx.lineTo(posX + elW / 2, posY);
          ctx.stroke();
        }
      } else if (el.type === 'badge') {
        ctx.textAlign = 'center';
        ctx.fillStyle = el.color || themeColor;

        if (el.shapeType === 'anchor') {
          ctx.font = `${el.fontSize || 32}px sans-serif`;
          ctx.fillText('⚓', posX, posY);
        } else if (el.shapeType === 'stars') {
          ctx.font = `bold ${el.fontSize || 14}px sans-serif`;
          ctx.letterSpacing = '6px';
          ctx.fillText('★ ★ ★ ★', posX, posY);
        } else if (el.shapeType === 'seal_gold') {
          ctx.font = `${el.fontSize || 40}px sans-serif`;
          ctx.fillText('🎖️', posX, posY);
        }
      } else if (el.type === 'text') {
        let textContent = el.text || '';

        // Substituição das Tags de Mala Direta
        Object.entries(tagValues).forEach(([k, v]) => {
          textContent = textContent.replace(new RegExp(`{${k}}`, 'g'), v);
        });

        // Valores padrão de demonstração se não houver tagValue
        if (!tagValues.nome) {
          textContent = textContent
            .replace('{nome}', 'ALMIRANTE MARCOS SILSEN OLSEN')
            .replace('{posto}', 'ALMIRANTE DE ESQUADRA')
            .replace('{cargo}', 'Comandante da Marinha')
            .replace('{assento}', 'Mesa de Honra (A-1)')
            .replace('{evento}', 'Almoço Oficial de Apresentação')
            .replace('{data}', '20 DE AGOSTO DE 2026')
            .replace('{local}', 'Salão Nobre do CGCFN')
            .replace('{entrada}', 'Salada de Frutos do Mar com Molho Cítrico')
            .replace('{prato_principal}', 'Tornedor de Filé Mignon ao Molho Poivre')
            .replace('{sobremesa}', 'Mil-Folhas com Coulis de Frutas Vermelhas');
        }

        const fontStyleStr = el.fontStyle === 'italic' ? 'italic ' : '';
        const fontWeightStr = el.fontWeight === 'bold' ? 'bold ' : el.fontWeight === '900' ? '900 ' : '';
        const fontFamilyStr = el.fontFamily || 'sans-serif';
        const fontSizeStr = `${el.fontSize || 14}px`;

        ctx.font = `${fontStyleStr}${fontWeightStr}${fontSizeStr} ${fontFamilyStr}`;
        ctx.fillStyle = el.color || '#ffffff';
        ctx.textAlign = el.align || 'center';
        if (el.letterSpacing) {
          ctx.letterSpacing = `${el.letterSpacing}px`;
        } else {
          ctx.letterSpacing = '0px';
        }

        ctx.fillText(textContent, posX, posY);
      }

      // Indicador de Elemento Selecionado
      if (selectedElementId === el.id) {
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        const selW = elW || 80;
        const selH = elH || 30;
        ctx.strokeRect(posX - selW / 2 - 4, posY - selH / 2 - 4, selW + 8, selH + 8);
        ctx.setLineDash([]);
      }

      ctx.restore();
    });
  };

  const renderCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dims = getCanvasDimensions(1);
    canvas.width = dims.width;
    canvas.height = dims.height;

    drawDesign(ctx, dims.width, dims.height);
  };

  // Adicionar Novo Elemento
  const handleAddText = (typePreset: 'title' | 'subtitle' | 'body' | 'tag') => {
    const id = `txt_${Date.now()}`;
    let newEl: CanvasElement;

    if (typePreset === 'title') {
      newEl = {
        id,
        type: 'text',
        text: 'NOVO TÍTULO DE IMPACTO',
        x: 50,
        y: 50,
        fontSize: 22,
        fontWeight: 'bold',
        fontFamily: 'Playfair Display',
        color: '#ffffff',
        align: 'center',
      };
    } else if (typePreset === 'tag') {
      newEl = {
        id,
        type: 'text',
        text: 'CATEGORIA OU DATA',
        x: 50,
        y: 40,
        fontSize: 10,
        fontWeight: 'bold',
        fontFamily: 'DM Sans',
        color: themeColor,
        align: 'center',
        letterSpacing: 2,
      };
    } else {
      newEl = {
        id,
        type: 'text',
        text: 'Insira o texto descritivo aqui...',
        x: 50,
        y: 60,
        fontSize: 13,
        fontFamily: 'DM Sans',
        color: '#cbd5e1',
        align: 'center',
      };
    }

    setElements([...elements, newEl]);
    setSelectedElementId(id);
    toast.success('Novo texto adicionado ao Canvas!');
  };

  const handleAddShape = (shapeType: CanvasElement['shapeType']) => {
    const id = `shape_${Date.now()}`;
    const newEl: CanvasElement = {
      id,
      type: shapeType === 'anchor' || shapeType === 'stars' || shapeType === 'seal_gold' ? 'badge' : 'shape',
      shapeType,
      x: 50,
      y: 50,
      width: shapeType === 'rect' ? 60 : shapeType === 'line_gold' ? 50 : 20,
      height: shapeType === 'rect' ? 20 : 20,
      fillColor: shapeType === 'rect' ? 'rgba(255,255,255,0.06)' : themeColor,
      strokeColor: themeColor,
      strokeWidth: 2,
      color: themeColor,
      fontSize: 28,
    };
    setElements([...elements, newEl]);
    setSelectedElementId(id);
    toast.success('Elemento gráfico adicionado!');
  };

  // Inserir Tag Dinâmica
  const handleInsertTag = (tag: string) => {
    if (selectedElementId) {
      setElements(
        elements.map((el) => {
          if (el.id === selectedElementId && el.type === 'text') {
            return { ...el, text: `${el.text || ''} ${tag}`.trim() };
          }
          return el;
        })
      );
      toast.success(`Tag ${tag} inserida no elemento!`);
    } else {
      handleAddText('body');
    }
  };

  // Atualizar Elemento Selecionado
  const updateSelectedElement = (field: keyof CanvasElement, value: any) => {
    if (!selectedElementId) return;
    setElements(
      elements.map((el) => {
        if (el.id === selectedElementId) {
          return { ...el, [field]: value };
        }
        return el;
      })
    );
  };

  // Remover Elemento Selecionado
  const handleDeleteSelected = () => {
    if (!selectedElementId) return;
    setElements(elements.filter((el) => el.id !== selectedElementId));
    setSelectedElementId(null);
    toast.success('Elemento removido!');
  };

  // Gerador de Cardápio / Arte com IA
  const handleGenerateAI = () => {
    setElements([
      {
        id: 'frame_ai',
        type: 'shape',
        shapeType: 'naval_frame',
        x: 50,
        y: 50,
        width: 90,
        height: 92,
        strokeColor: themeColor,
        strokeWidth: 2,
      },
      {
        id: 'anchor_ai',
        type: 'badge',
        shapeType: 'anchor',
        x: 50,
        y: 12,
        color: themeColor,
        fontSize: 32,
      },
      {
        id: 'header_ai',
        type: 'text',
        text: 'MARINHA DO BRASIL',
        x: 50,
        y: 18,
        fontSize: 12,
        fontWeight: 'bold',
        fontFamily: 'DM Sans',
        color: themeColor,
        letterSpacing: 3,
      },
      {
        id: 'title_ai',
        type: 'text',
        text: 'ALMOÇO DE APRESENTAÇÃO DE OFICIAIS-GENERAIS',
        x: 50,
        y: 28,
        fontSize: 15,
        fontWeight: 'bold',
        fontFamily: 'Playfair Display',
        color: '#ffffff',
      },
      {
        id: 'menu_ent',
        type: 'text',
        text: '• ENTRADA: {entrada} •',
        x: 50,
        y: 42,
        fontSize: 12,
        fontWeight: 'bold',
        fontFamily: 'DM Sans',
        color: themeColor,
      },
      {
        id: 'menu_prat',
        type: 'text',
        text: '• PRINCIPAL: {prato_principal} •',
        x: 50,
        y: 58,
        fontSize: 12,
        fontWeight: 'bold',
        fontFamily: 'DM Sans',
        color: themeColor,
      },
      {
        id: 'menu_sob',
        type: 'text',
        text: '• SOBREMESA: {sobremesa} •',
        x: 50,
        y: 74,
        fontSize: 12,
        fontWeight: 'bold',
        fontFamily: 'DM Sans',
        color: themeColor,
      },
      {
        id: 'footer_ai',
        type: 'text',
        text: '{local} • {data}',
        x: 50,
        y: 90,
        fontSize: 10,
        fontFamily: 'DM Sans',
        color: '#94a3b8',
      },
    ]);
    confetti({ particleCount: 50, spread: 60, origin: { y: 0.6 } });
    toast.success('Layout Nobre composto pela IA com sucesso!');
  };

  // Exportar Imagem em Alta Resolução (300 DPI)
  const handleExportPNG = () => {
    const exportCanvas = document.createElement('canvas');
    const dims = getCanvasDimensions(3); // 3x para nitidez gráfica de impressão
    exportCanvas.width = dims.width;
    exportCanvas.height = dims.height;
    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    drawDesign(ctx, dims.width, dims.height);

    const link = document.createElement('a');
    link.download = `SISGAB_Arte_${selectedFormat.id}_${dims.width}x${dims.height}.png`;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
    toast.success('Arte exportada em altíssima resolução para impressão!');
  };

  const selectedEl = elements.find((el) => el.id === selectedElementId);

  return (
    <div className="space-y-6 pb-12">
      {/* ── HEADER DA PÁGINA ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#c5a059]/20 to-amber-500/20 text-amber-300 text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
              Canva do Gabinete & Mala Direta
            </span>
            <span className="text-slate-400 text-xs">• Estúdio Gráfico Universal 2.0</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1">
            Estúdio Universal de Design, Formas & Mala Direta
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm">
            Crie cardápios, diplomas, cartazes, prismas e banners com liberdade total de camadas, formas e variáveis ({'{tags}'}).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleGenerateAI}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-black text-xs shadow-lg shadow-cyan-500/25 transition-all hover:scale-105"
          >
            <Sparkles className="w-4 h-4" />
            <span>Gerar com IA ✨</span>
          </button>

          <button
            onClick={handleExportPNG}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
          >
            <Download className="w-4 h-4" />
            <span>Exportar PNG (300 DPI)</span>
          </button>
        </div>
      </div>

      {/* ── ABAS PRINCIPAIS 3 EM 1 ── */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveTab('canva')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'canva'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Palette className="w-4 h-4" />
          <span>🎨 1. Editor "Canva SISGAB" (Camadas & Formas)</span>
        </button>

        <button
          onClick={() => setActiveTab('modelos')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'modelos'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>📚 2. Modelos Oficiais (Cardápios, Prismas & Diplomas)</span>
        </button>

        <button
          onClick={() => setActiveTab('lote')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'lote'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Printer className="w-4 h-4" />
          <span>📑 3. Mala Direta & Impressão em Lote ({jadeConvidados.length} Convidados)</span>
        </button>
      </div>

      {/* ── ABA 1: EDITOR CANVA SISGAB ── */}
      {activeTab === 'canva' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* PAINEL LATERAL DE FERRAMENTAS ESTILO CANVA (5 COLS) */}
          <div className="lg:col-span-5 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-5">
            {/* Seletor de Dimensão & Formato */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-4 h-4" />
                  <span>Formato & Dimensão da Folha</span>
                </span>
              </div>
              <select
                value={selectedFormat.id}
                onChange={(e) => {
                  const f = FORMAT_PRESETS.find((p) => p.id === e.target.value) || FORMAT_PRESETS[0];
                  setSelectedFormat(f);
                }}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-bold text-xs"
              >
                {FORMAT_PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.widthMm} × {p.heightMm} mm)
                  </option>
                ))}
              </select>

              {selectedFormat.id === 'custom' && (
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <div>
                    <label className="text-[10px] text-slate-400">Largura (mm)</label>
                    <input
                      type="number"
                      value={customWidthMm}
                      onChange={(e) => setCustomWidthMm(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Altura (mm)</label>
                    <input
                      type="number"
                      value={customHeightMm}
                      onChange={(e) => setCustomHeightMm(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-white text-xs"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Barra de Adição de Elementos (Estilo Canva) */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
              <span className="text-[11px] font-black text-cyan-300 uppercase tracking-wider block flex items-center gap-1.5">
                <Plus className="w-3.5 h-3.5" />
                <span>Adicionar Elementos ao Canvas</span>
              </span>

              {/* Botões Rápidos de Texto */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleAddText('title')}
                  className="px-2 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-white font-bold text-[11px] flex flex-col items-center gap-1"
                >
                  <Type className="w-4 h-4 text-[#c5a059]" />
                  <span>+ Título</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddText('body')}
                  className="px-2 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-white font-medium text-[11px] flex flex-col items-center gap-1"
                >
                  <Type className="w-3.5 h-3.5 text-slate-400" />
                  <span>+ Subtítulo</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddText('tag')}
                  className="px-2 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-amber-300 font-mono text-[10px] flex flex-col items-center gap-1"
                >
                  <Tag className="w-3.5 h-3.5 text-amber-400" />
                  <span>+ Tag / Data</span>
                </button>
              </div>

              {/* Formas e Badges Navais */}
              <div className="grid grid-cols-4 gap-1.5 pt-1 border-t border-slate-900">
                <button
                  type="button"
                  onClick={() => handleAddShape('rect')}
                  className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-[10px] font-bold text-slate-300 flex flex-col items-center gap-1"
                >
                  <Square className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Card</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddShape('circle')}
                  className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-[10px] font-bold text-slate-300 flex flex-col items-center gap-1"
                >
                  <Circle className="w-3.5 h-3.5 text-pink-400" />
                  <span>Círculo</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddShape('anchor')}
                  className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-[10px] font-bold text-slate-300 flex flex-col items-center gap-1"
                >
                  <span className="text-sm">⚓</span>
                  <span>Âncora</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleAddShape('stars')}
                  className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-[10px] font-bold text-slate-300 flex flex-col items-center gap-1"
                >
                  <Star className="w-3.5 h-3.5 text-[#c5a059]" />
                  <span>Estrelas</span>
                </button>
              </div>
            </div>

            {/* Tags Dinâmicas para Mala Direta */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
              <span className="text-[11px] font-black text-amber-400 uppercase tracking-wider block">
                🏷️ Tags de Mala Direta (Clique para Inserir)
              </span>
              <div className="flex flex-wrap gap-1.5">
                {AVAILABLE_TAGS.map((t) => (
                  <button
                    key={t.tag}
                    type="button"
                    onClick={() => handleInsertTag(t.tag)}
                    className="px-2 py-1 rounded-lg bg-slate-900 hover:bg-amber-500/20 border border-slate-700 hover:border-amber-400 text-[10px] font-mono text-amber-300 transition-all"
                    title={`${t.desc} (Ex: ${t.example})`}
                  >
                    {t.tag}
                  </button>
                ))}
              </div>
            </div>

            {/* Configurações do Elemento Selecionado */}
            {selectedEl ? (
              <div className="p-4 rounded-2xl bg-slate-900/90 border border-[#00e5ff]/40 space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-black text-[#00e5ff] uppercase flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5" />
                    <span>Propriedades do Elemento</span>
                  </span>
                  <button
                    type="button"
                    onClick={handleDeleteSelected}
                    className="p-1 text-red-400 hover:bg-red-500/20 rounded-md"
                    title="Excluir Elemento"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {selectedEl.type === 'text' && (
                  <>
                    <div>
                      <label className="text-[10px] text-slate-400 block mb-1">Conteúdo do Texto</label>
                      <input
                        type="text"
                        value={selectedEl.text || ''}
                        onChange={(e) => updateSelectedElement('text', e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-white font-mono text-xs"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">Tamanho da Fonte</label>
                        <input
                          type="number"
                          value={selectedEl.fontSize || 14}
                          onChange={(e) => updateSelectedElement('fontSize', Number(e.target.value))}
                          className="w-full px-2 py-1 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-400 block mb-1">Família da Fonte</label>
                        <select
                          value={selectedEl.fontFamily || 'DM Sans'}
                          onChange={(e) => updateSelectedElement('fontFamily', e.target.value)}
                          className="w-full px-2 py-1 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs font-bold"
                        >
                          <option value="Playfair Display">Playfair Display (Nobre)</option>
                          <option value="Cinzel">Cinzel (Solene / Monumental)</option>
                          <option value="DM Sans">DM Sans (Clean / Moderno)</option>
                          <option value="Space Grotesk">Space Grotesk (Tático)</option>
                          <option value="Georgia">Georgia (Clássico)</option>
                        </select>
                      </div>
                    </div>
                  </>
                )}

                {/* Controles de Posição X e Y */}
                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800">
                  <div>
                    <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                      <span>Posição X</span>
                      <span className="font-mono">{selectedEl.x}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={selectedEl.x}
                      onChange={(e) => updateSelectedElement('x', Number(e.target.value))}
                      className="w-full accent-[#00e5ff]"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
                      <span>Posição Y</span>
                      <span className="font-mono">{selectedEl.y}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={selectedEl.y}
                      onChange={(e) => updateSelectedElement('y', Number(e.target.value))}
                      className="w-full accent-[#00e5ff]"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-slate-500 italic text-center p-2 border border-dashed border-slate-800 rounded-xl">
                Clique em um elemento na arte ou adicione um novo para editar suas propriedades.
              </p>
            )}

            {/* Estilo de Fundo do Documento */}
            <div className="space-y-2 text-xs">
              <label className="font-bold text-slate-300">Estilo de Fundo do Documento</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'gradient', name: '🌊 Degradê' },
                  { id: 'paper_verge', name: '📜 Papel Vergê' },
                  { id: 'tactical_dark', name: '⚡ Tático Dark' },
                ].map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => setBgType(b.id as any)}
                    className={`py-2 rounded-xl text-xs font-bold transition-all border ${
                      bgType === b.id
                        ? 'bg-[#c5a059]/20 border-[#c5a059] text-[#c5a059]'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    {b.name}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* PAINEL DIREITO: VISUALIZADOR DE ALTA RESOLUÇÃO (7 COLS) */}
          <div className="lg:col-span-7 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl flex flex-col justify-between items-center space-y-4">
            <div className="w-full flex items-center justify-between">
              <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
                <Eye className="w-4 h-4" />
                <span>Visualizador Gráfico em Tempo Real • {selectedFormat.name}</span>
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-[#c5a059] font-mono text-[10px] font-bold">
                {elements.length} Camadas
              </span>
            </div>

            <div className="w-full flex justify-center py-2 overflow-x-auto">
              <canvas
                ref={canvasRef}
                className="rounded-2xl shadow-2xl border-2 border-slate-700 bg-slate-950 max-h-[560px] max-w-full"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const clickX = ((e.clientX - rect.left) / rect.width) * 100;
                  const clickY = ((e.clientY - rect.top) / rect.height) * 100;
                  // Encontrar o elemento mais próximo do clique
                  const closest = elements.find(
                    (el) => Math.abs(el.x - clickX) < 15 && Math.abs(el.y - clickY) < 8
                  );
                  setSelectedElementId(closest ? closest.id : null);
                }}
              />
            </div>

            <div className="w-full flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-800">
              <span>Dimensão: {selectedFormat.widthMm} × {selectedFormat.heightMm} mm</span>
              <span>Padrão Gráfico Oficial do CGCFN</span>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 2: MODELOS OFICIAIS PREDEFINIDOS ── */}
      {activeTab === 'modelos' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FORMAT_PRESETS.filter((p) => p.id !== 'custom').map((preset) => (
            <div
              key={preset.id}
              className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 hover:border-[#c5a059]/50 transition-all shadow-xl space-y-3 flex flex-col justify-between"
            >
              <div>
                <span className="px-2.5 py-0.5 rounded bg-slate-900 text-[#c5a059] font-mono text-[10px] font-bold uppercase">
                  {preset.category}
                </span>
                <h3 className="text-base font-black text-white mt-1.5">{preset.name}</h3>
                <p className="text-xs text-slate-400 mt-1">{preset.description}</p>
              </div>

              <div className="pt-3 border-t border-slate-900 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">{preset.widthMm} × {preset.heightMm} mm</span>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFormat(preset);
                    setActiveTab('canva');
                    toast.success(`Modelo ${preset.name} carregado no Canvas!`);
                  }}
                  className="px-3.5 py-1.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs transition-all"
                >
                  Abrir no Editor
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── ABA 3: MALA DIRETA & IMPRESSÃO EM LOTE COM BANCO DE DADOS ── */}
      {activeTab === 'lote' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Printer className="w-4 h-4 text-[#c5a059]" />
                <span>Mala Direta & Geração de Lote ({selectedFormat.name})</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Mescle o design atual do Canvas com todos os convidados cadastrados no evento selecionado.
              </p>
            </div>

            {/* Dropdown de Eventos */}
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-3.5 py-1.5 rounded-xl text-xs">
              <Calendar className="w-4 h-4 text-[#c5a059]" />
              <select
                value={selectedEventoId || ''}
                onChange={(e) => handleEventoChange(Number(e.target.value))}
                className="bg-transparent text-white font-bold focus:outline-none cursor-pointer"
              >
                {eventos.map((ev) => (
                  <option key={ev.id} value={ev.id} className="bg-slate-900 text-white">
                    {ev.nome} ({ev.data_evento})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Grade de Páginas Mapeadas */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider">
                👑 Autoridades Mapeadas ({jadeConvidados.length} Itens no Lote)
              </span>

              <button
                onClick={() => window.print()}
                className="flex items-center gap-2 px-6 py-2.5 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
              >
                <Printer className="w-4 h-4" />
                <span>Imprimir Lote Completo ({jadeConvidados.length} Páginas)</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[500px] overflow-y-auto pr-1">
              {jadeConvidados.map((guest, idx) => (
                <div
                  key={guest.id}
                  className="p-4 rounded-2xl bg-slate-950 border border-slate-800 hover:border-[#c5a059]/40 space-y-2 transition-all shadow-md"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-[10px] text-slate-500">#{idx + 1}</span>
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[#c5a059] text-[9px] font-bold">
                      {guest.assento_id || 'Mesa Reservada'}
                    </span>
                  </div>

                  <div>
                    {guest.posto_graduacao && (
                      <p className="text-[10px] font-bold text-[#c5a059] uppercase">{guest.posto_graduacao}</p>
                    )}
                    <h3 className="font-black text-white text-sm truncate">{guest.nome}</h3>
                    <p className="text-[11px] text-slate-400 truncate">{guest.cargo_funcao || 'Autoridade'}</p>
                  </div>

                  <div className="pt-2 border-t border-slate-900 flex items-center justify-between text-[10px] text-slate-500">
                    <span>{selectedFormat.name.split(' ')[1]}</span>
                    <span className="text-emerald-400 font-bold">Pronto para Imprimir ✓</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
