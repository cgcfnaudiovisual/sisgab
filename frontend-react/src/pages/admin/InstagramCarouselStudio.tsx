import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Download,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
  Upload,
  Layers,
  Palette,
  Sliders,
  Type,
  Trash2,
  Plus,
  RefreshCw,
  Eye,
  CheckCircle2,
  FileText,
  Share2,
  Smartphone,
  Square,
  Tv,
  Maximize2,
  Grid,
  Zap,
  Shield,
  Award,
  Hash,
  SlidersHorizontal,
  Flame,
  Bookmark,
  MessageSquare,
  Heart,
  HelpCircle,
  Clock,
  Radio,
  Sliders as SlidersIcon,
  Wand2,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { generateGeminiContent } from '../../utils/geminiClient';
import { supabase } from '../../api/supabase';

// Formatos de Publicação
export type PostFormat = '4_5' | '9_16' | '1_1' | '16_9';

interface FormatConfig {
  id: PostFormat;
  name: string;
  ratioName: string;
  width: number;
  height: number;
  previewWidth: number;
  previewHeight: number;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
}

const FORMAT_CONFIGS: Record<PostFormat, FormatConfig> = {
  '4_5': {
    id: '4_5',
    name: 'Carrossel / Post Feed',
    ratioName: '4:5',
    width: 1080,
    height: 1350,
    previewWidth: 380,
    previewHeight: 475,
    icon: Smartphone,
    description: '1080×1350px • Padrão de maior alcance e engajamento no Feed',
  },
  '9_16': {
    id: '9_16',
    name: 'Stories / Reels',
    ratioName: '9:16',
    width: 1080,
    height: 1920,
    previewWidth: 320,
    previewHeight: 568,
    icon: Smartphone,
    description: '1080×1920px • Tela cheia vertical para Stories, Reels e Status',
  },
  '1_1': {
    id: '1_1',
    name: 'Feed Quadrado',
    ratioName: '1:1',
    width: 1080,
    height: 1080,
    previewWidth: 380,
    previewHeight: 380,
    icon: Square,
    description: '1080×1080px • Formato clássico para comunicados e notas',
  },
  '16_9': {
    id: '16_9',
    name: 'Banner / TV / X',
    ratioName: '16:9',
    width: 1920,
    height: 1080,
    previewWidth: 480,
    previewHeight: 270,
    icon: Tv,
    description: '1920×1080px • Paisagem para Telões, SisGAB TV e Portais',
  },
};

// Tipos de Layout por Slide
export type SlideLayoutType =
  | 'hero_full'
  | 'split_photo'
  | 'glass_card'
  | 'big_number'
  | 'quote_nobel'
  | 'headline_banner'
  | 'breaking_news'
  | 'before_after_split'
  | 'quiz_poll'
  | 'info_list'
  | 'tech_spec'
  | 'cta_final';

// Tipos de Textura de Fundo
export type TextureType =
  | 'none'
  | 'tactical_grid'
  | 'dots'
  | 'diagonal_stripes'
  | 'glow_spot'
  | 'naval_corners'
  | 'film_grain'
  | 'halftone_dots'
  | 'vignette_shadow'
  | 'camo_tactical';

// Estilos / Temas Visuais
export type DesignThemePreset =
  | 'editorial_nobre'
  | 'tatico_operacional'
  | 'manchete_impacto'
  | 'clean_institucional'
  | 'custom';

export interface CarouselSlide {
  id: string;
  layoutType: SlideLayoutType;
  tag: string;
  title: string;
  subtitle?: string;
  body?: string;
  bigNumber?: string;
  bigNumberLabel?: string;
  quote?: string;
  authorName?: string;
  authorRole?: string;
  ctaText?: string;
  ctaTriggerType?: 'salvar' | 'comentar' | 'marcar' | 'compartilhar' | 'toqueduplo';
  breakingBadge?: string;
  breakingDate?: string;
  pollQuestion?: string;
  pollOptionA?: string;
  pollOptionB?: string;
  beforeLabel?: string;
  afterLabel?: string;
  listItems?: string[];
  techSpecs?: { label: string; value: string }[];
  bgType: 'gradient' | 'dark' | 'light';
  gradColorStart: string;
  gradColorMid: string;
  gradColorEnd: string;
  gradAngle: number;
  texture: TextureType;
  imageSrc?: string;
  imageOpacity: number;
  overlayStrength: number;
  fontFamily: 'Playfair Display' | 'DM Sans' | 'Space Grotesk' | 'Georgia';
}

const DEFAULT_SLIDES: CarouselSlide[] = [
  {
    id: '1',
    layoutType: 'hero_full',
    tag: 'XII CONCURSO DE CRÔNICAS',
    title: '129 jovens, 12 escolas e um palco histórico no Rio.',
    subtitle: 'A celebração da literatura e da juventude no tradicional Concurso ABL / Corpo de Fuzileiros Navais.',
    bgType: 'gradient',
    gradColorStart: '#060e18',
    gradColorMid: '#0b1c34',
    gradColorEnd: '#13315c',
    gradAngle: 165,
    texture: 'glow_spot',
    imageOpacity: 90,
    overlayStrength: 75,
    fontFamily: 'Playfair Display',
  },
  {
    id: '2',
    layoutType: 'breaking_news',
    tag: 'COMUNICADO OFICIAL',
    breakingBadge: '🚨 PLANTÃO CGCFN',
    breakingDate: 'HOJE • BRASÍLIA - DF',
    title: 'Marinha do Brasil inaugura novas instalações operacionais',
    body: 'Modernização da infraestrutura amplia a capacidade de pronta resposta e comando do Corpo de Fuzileiros Navais.',
    bgType: 'dark',
    gradColorStart: '#08111d',
    gradColorMid: '#161e2e',
    gradColorEnd: '#08111d',
    gradAngle: 180,
    texture: 'tactical_grid',
    imageOpacity: 50,
    overlayStrength: 85,
    fontFamily: 'DM Sans',
  },
  {
    id: '3',
    layoutType: 'big_number',
    tag: 'TRADIÇÃO & ALCANCE',
    bigNumber: '18',
    bigNumberLabel: 'Anos de Parceria Ininterrupta',
    title: 'Unindo a arte literária e a tradição naval',
    body: 'Realizado desde 2008, o Prêmio Rachel de Queiroz mobiliza estudantes do 8º e 9º ano das redes pública e privada do RJ.',
    bgType: 'dark',
    gradColorStart: '#08111d',
    gradColorMid: '#0e1e33',
    gradColorEnd: '#08111d',
    gradAngle: 180,
    texture: 'tactical_grid',
    imageOpacity: 50,
    overlayStrength: 85,
    fontFamily: 'Playfair Display',
  },
  {
    id: '4',
    layoutType: 'info_list',
    tag: 'PILARES DE EXCELÊNCIA',
    title: 'Os 4 Compromissos da Força de Prontidão',
    listItems: [
      'Prontidão Permanente e Ação Rápida em Todo Território',
      'Treinamento e Formação Militar de Alto Nível Técnico',
      'Modernização Contínua de Meios Blindados e Embarcações',
      'Compromisso com a Sociedade e Apoio Humanitário',
    ],
    bgType: 'gradient',
    gradColorStart: '#08111d',
    gradColorMid: '#112239',
    gradColorEnd: '#08111d',
    gradAngle: 145,
    texture: 'halftone_dots',
    imageOpacity: 45,
    overlayStrength: 80,
    fontFamily: 'Space Grotesk',
  },
  {
    id: '5',
    layoutType: 'quiz_poll',
    tag: 'DESAFIO INTERATIVO',
    title: 'Qual dessas missões é a mais desafiadora?',
    pollQuestion: 'Qual dessas missões é considerada a mais desafiadora pelos Fuzileiros Navais?',
    pollOptionA: 'Operação Anfíbia Noturna em Alto-Mar',
    pollOptionB: 'Incursão Ribeirinha na Selva Amazônica',
    body: 'Deixe sua resposta nos comentários: Vote [ A ] ou [ B ]!',
    bgType: 'gradient',
    gradColorStart: '#08111d',
    gradColorMid: '#1b3459',
    gradColorEnd: '#0c1a2e',
    gradAngle: 155,
    texture: 'camo_tactical',
    imageOpacity: 40,
    overlayStrength: 80,
    fontFamily: 'DM Sans',
  },
  {
    id: '6',
    layoutType: 'tech_spec',
    tag: 'MEIOS OPERACIONAIS',
    title: 'CLANF — Carro Lagarta Anfíbio',
    body: 'Veículo blindado de assalto anfíbio projetado para desembarque de tropas sob condições táticas extremas.',
    techSpecs: [
      { label: 'Velocidade na Água', value: '13 km/h (7 nós)' },
      { label: 'Capacidade de Tropa', value: '21 Fuzileiros' },
      { label: 'Armamento', value: 'Metr. .50 + MK19 40mm' },
      { label: 'Autonomia', value: '480 km em Terra' },
    ],
    bgType: 'gradient',
    gradColorStart: '#050c17',
    gradColorMid: '#0f2747',
    gradColorEnd: '#050c17',
    gradAngle: 135,
    texture: 'tactical_grid',
    imageOpacity: 60,
    overlayStrength: 75,
    fontFamily: 'Space Grotesk',
  },
  {
    id: '7',
    layoutType: 'cta_final',
    tag: 'HONRA & ENGAJAMENTO',
    title: 'A escrita e o dever transformam o futuro do Brasil.',
    body: 'Salve este post para consultar depois e compartilhe com quem tem orgulho da nossa Marinha!',
    ctaText: 'Salve e compartilhe essa conquista ↗',
    ctaTriggerType: 'salvar',
    bgType: 'gradient',
    gradColorStart: '#060e18',
    gradColorMid: '#163663',
    gradColorEnd: '#c5a059',
    gradAngle: 165,
    texture: 'glow_spot',
    imageOpacity: 40,
    overlayStrength: 80,
    fontFamily: 'Playfair Display',
  },
];

export const InstagramCarouselStudio: React.FC = () => {
  const [format, setFormat] = useState<PostFormat>('4_5');
  const [slides, setSlides] = useState<CarouselSlide[]>(DEFAULT_SLIDES);
  const [currentSlideIndex, setCurrentSlideIndex] = useState<number>(0);
  const [brandColor, setBrandColor] = useState<string>('#c5a059');
  const [brandLight, setBrandLight] = useState<string>('#e0c287');
  const [accountHandle, setAccountHandle] = useState<string>('fuzileirosnavais_oficial');
  const [locationTag, setLocationTag] = useState<string>('Comando-Geral do CFN');

  // Modo IA Diretor de Arte
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiPromptInput, setAiPromptInput] = useState('');
  const [aiMode, setAiMode] = useState<'institutional' | 'creative'>('creative');
  const [isGeneratingAi, setIsGeneratingAi] = useState(false);
  const [isOptimizingHeadline, setIsOptimizingHeadline] = useState(false);
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');

  // Galeria de imagens
  const [uploadedImages, setUploadedImages] = useState<string[]>([]);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const activeSlide = slides[currentSlideIndex] || slides[0];
  const currentFormat = FORMAT_CONFIGS[format];

  // Carregar chave do Gemini na inicialização
  useEffect(() => {
    async function loadKey() {
      const localKey = localStorage.getItem('sisgab_gemini_key') || localStorage.getItem('gemini_api_key');
      if (localKey && localKey.trim()) {
        setGeminiApiKey(localKey.trim());
        return;
      }
      try {
        const { data } = await supabase
          .from('config')
          .select('valor')
          .in('chave', ['gemini_api_key', 'google_api_key'])
          .limit(1);
        if (data && data.length > 0 && data[0].valor) {
          setGeminiApiKey(data[0].valor);
          localStorage.setItem('sisgab_gemini_key', data[0].valor);
        }
      } catch (e) {
        console.warn('Erro ao carregar chave do Gemini:', e);
      }
    }
    loadKey();
  }, []);

  // Renderização Reativa do Canvas
  useEffect(() => {
    renderCanvas();
  }, [slides, currentSlideIndex, format, brandColor, brandLight]);

  // Função Principal de Renderização Gráfica
  const drawSlideGraphics = (
    ctx: CanvasRenderingContext2D,
    slide: CarouselSlide,
    index: number,
    total: number,
    targetWidth: number,
    targetHeight: number
  ) => {
    const w = targetWidth;
    const h = targetHeight;
    const scale = w / 420;

    // ── 1. RENDERIZAR FUNDO (GRADIENTE OU COR) ──
    if (slide.bgType === 'gradient') {
      const angleRad = (slide.gradAngle * Math.PI) / 180;
      const x1 = w / 2 - (Math.cos(angleRad) * w) / 2;
      const y1 = h / 2 - (Math.sin(angleRad) * h) / 2;
      const x2 = w / 2 + (Math.cos(angleRad) * w) / 2;
      const y2 = h / 2 + (Math.sin(angleRad) * h) / 2;

      const grad = ctx.createLinearGradient(x1, y1, x2, y2);
      grad.addColorStop(0, slide.gradColorStart);
      grad.addColorStop(0.5, slide.gradColorMid);
      grad.addColorStop(1, slide.gradColorEnd);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    } else if (slide.bgType === 'light') {
      ctx.fillStyle = '#f6f4ef';
      ctx.fillRect(0, 0, w, h);
    } else {
      ctx.fillStyle = '#08111d';
      ctx.fillRect(0, 0, w, h);
    }

    // ── 2. RENDERIZAR TEXTURAS DINÂMICAS ──
    drawTexture(ctx, slide.texture, w, h, scale, brandColor);

    // ── 3. RENDERIZAR IMAGEM COM MISTURA & OVERLAY ──
    if (slide.imageSrc) {
      const img = new Image();
      img.src = slide.imageSrc;
      if (img.complete && img.naturalWidth > 0) {
        ctx.save();
        ctx.globalAlpha = slide.imageOpacity / 100;

        const imgRatio = img.width / img.height;
        const canvasRatio = w / h;
        let renderW = w;
        let renderH = h;
        let renderX = 0;
        let renderY = 0;

        if (imgRatio > canvasRatio) {
          renderW = h * imgRatio;
          renderX = (w - renderW) / 2;
        } else {
          renderH = w / imgRatio;
          renderY = (h - renderH) / 2;
        }

        ctx.drawImage(img, renderX, renderY, renderW, renderH);
        ctx.restore();

        // Overlay de Gradiente Escurecedor para Legibilidade
        const overlayStrength = slide.overlayStrength / 100;
        const overlay = ctx.createLinearGradient(0, 0, 0, h);
        overlay.addColorStop(0, `rgba(8, 17, 29, ${0.15 * overlayStrength})`);
        overlay.addColorStop(0.5, `rgba(8, 17, 29, ${0.65 * overlayStrength})`);
        overlay.addColorStop(1, `rgba(8, 17, 29, ${0.98 * overlayStrength})`);
        ctx.fillStyle = overlay;
        ctx.fillRect(0, 0, w, h);
      }
    }

    const isLight = slide.bgType === 'light';
    const paddingX = 36 * scale;
    const fontName = slide.fontFamily || 'Georgia';

    // ── 4. RENDERIZAR TAG / BADGE SUPERIOR ──
    if (slide.tag && slide.layoutType !== 'breaking_news') {
      const tagY = 56 * scale;
      ctx.font = `bold ${10 * scale}px sans-serif`;
      ctx.fillStyle = isLight ? '#8a6d30' : brandLight;
      ctx.textAlign = 'left';
      ctx.letterSpacing = `${2 * scale}px`;
      ctx.fillText(slide.tag.toUpperCase(), paddingX, tagY);
      ctx.letterSpacing = '0px';
    }

    // ── 5. RENDERIZAR LAYOUT ESPECÍFICO DO SLIDE ──
    switch (slide.layoutType) {
      case 'breaking_news': {
        const barH = 34 * scale;
        ctx.fillStyle = '#dc2626';
        ctx.fillRect(0, 0, w, barH);

        ctx.font = `900 ${11 * scale}px sans-serif`;
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.fillText(slide.breakingBadge || '🚨 COMUNICADO OFICIAL • CORPO DE FUZILEIROS NAVAIS', w / 2, 22 * scale);

        ctx.textAlign = 'left';
        ctx.font = `bold ${9 * scale}px sans-serif`;
        ctx.fillStyle = brandLight;
        ctx.fillText(slide.breakingDate || 'HOJE • BRASÍLIA - DF', paddingX, 60 * scale);

        ctx.font = `900 ${26 * scale}px ${fontName}, sans-serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title.toUpperCase(), paddingX, 100 * scale, w - paddingX * 2, 32 * scale);

        if (slide.body) {
          const bodyY = 220 * scale;
          ctx.fillStyle = 'rgba(220, 38, 38, 0.12)';
          ctx.strokeStyle = 'rgba(220, 38, 38, 0.4)';
          ctx.lineWidth = 1.5 * scale;
          ctx.beginPath();
          ctx.roundRect(paddingX, bodyY, w - paddingX * 2, 110 * scale, 12 * scale);
          ctx.fill();
          ctx.stroke();

          ctx.font = `${13 * scale}px sans-serif`;
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
          wrapText(ctx, slide.body, paddingX + 16 * scale, bodyY + 32 * scale, w - paddingX * 2 - 32 * scale, 20 * scale);
        }
        break;
      }

      case 'before_after_split': {
        const topY = 70 * scale;
        ctx.font = `bold ${21 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title, paddingX, topY, w - paddingX * 2, 26 * scale);

        const cardW = (w - paddingX * 2 - 14 * scale) / 2;
        const cardY = topY + 70 * scale;
        const cardH = h - cardY - 60 * scale;

        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 1.5 * scale;
        ctx.beginPath();
        ctx.roundRect(paddingX, cardY, cardW, cardH, 14 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.font = `900 ${11 * scale}px sans-serif`;
        ctx.fillStyle = brandLight;
        ctx.fillText(slide.beforeLabel || '1808 • TRADIÇÃO', paddingX + 14 * scale, cardY + 28 * scale);

        ctx.font = `${11.5 * scale}px sans-serif`;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        wrapText(ctx, slide.body || 'Fundamentos históricos que moldaram o Corpo de Fuzileiros Navais.', paddingX + 14 * scale, cardY + 58 * scale, cardW - 28 * scale, 17 * scale);

        const c2X = paddingX + cardW + 14 * scale;
        ctx.fillStyle = 'rgba(0, 229, 255, 0.06)';
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.3)';
        ctx.beginPath();
        ctx.roundRect(c2X, cardY, cardW, cardH, 14 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.font = `900 ${11 * scale}px sans-serif`;
        ctx.fillStyle = '#00e5ff';
        ctx.fillText(slide.afterLabel || '2026 • MODERNIDADE', c2X + 14 * scale, cardY + 28 * scale);

        ctx.font = `${11.5 * scale}px sans-serif`;
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        wrapText(ctx, slide.subtitle || 'Tecnologia de ponta, sistemas C4I e doutrina expedicionária moderna.', c2X + 14 * scale, cardY + 58 * scale, cardW - 28 * scale, 17 * scale);
        break;
      }

      case 'quiz_poll': {
        const qY = 80 * scale;
        ctx.font = `bold ${22 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.pollQuestion || slide.title, paddingX, qY, w - paddingX * 2, 28 * scale);

        const btnH = 65 * scale;
        const btnW = w - paddingX * 2;
        const b1Y = qY + 95 * scale;
        const b2Y = b1Y + btnH + 16 * scale;

        ctx.fillStyle = 'rgba(255, 255, 255, 0.07)';
        ctx.strokeStyle = `${brandColor}88`;
        ctx.lineWidth = 1.5 * scale;
        ctx.beginPath();
        ctx.roundRect(paddingX, b1Y, btnW, btnH, 14 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = brandColor;
        ctx.beginPath();
        ctx.arc(paddingX + 28 * scale, b1Y + btnH / 2, 14 * scale, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = `900 ${11 * scale}px sans-serif`;
        ctx.fillStyle = '#08111d';
        ctx.textAlign = 'center';
        ctx.fillText('A', paddingX + 28 * scale, b1Y + btnH / 2 + 4 * scale);

        ctx.textAlign = 'left';
        ctx.font = `bold ${13 * scale}px sans-serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.pollOptionA || 'Opção A: Operação Anfíbia Noturna', paddingX + 54 * scale, b1Y + 28 * scale, btnW - 68 * scale, 18 * scale);

        ctx.fillStyle = 'rgba(255, 255, 255, 0.07)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.beginPath();
        ctx.roundRect(paddingX, b2Y, btnW, btnH, 14 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#38bdf8';
        ctx.beginPath();
        ctx.arc(paddingX + 28 * scale, b2Y + btnH / 2, 14 * scale, 0, Math.PI * 2);
        ctx.fill();

        ctx.font = `900 ${11 * scale}px sans-serif`;
        ctx.fillStyle = '#08111d';
        ctx.textAlign = 'center';
        ctx.fillText('B', paddingX + 28 * scale, b2Y + btnH / 2 + 4 * scale);

        ctx.textAlign = 'left';
        ctx.font = `bold ${13 * scale}px sans-serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.pollOptionB || 'Opção B: Ação Rápida com Lanchas Blindadas', paddingX + 54 * scale, b2Y + 28 * scale, btnW - 68 * scale, 18 * scale);

        if (slide.body) {
          ctx.font = `italic ${12 * scale}px sans-serif`;
          ctx.fillStyle = brandLight;
          ctx.textAlign = 'center';
          ctx.fillText(slide.body, w / 2, b2Y + btnH + 35 * scale);
          ctx.textAlign = 'left';
        }
        break;
      }

      case 'info_list': {
        const headY = 80 * scale;
        ctx.font = `bold ${23 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title, paddingX, headY, w - paddingX * 2, 28 * scale);

        const items = slide.listItems && slide.listItems.length > 0 ? slide.listItems : [
          'Prontidão Operacional Permanente',
          'Modernização de Meios Blindados e Embarcações',
          'Tradição e Disciplina Militar de Excelência',
          'Apoio Humanitário e Presença nas Águas Brasileiras',
        ];

        const startY = headY + 75 * scale;
        const itemH = 46 * scale;
        items.slice(0, 4).forEach((it, idx) => {
          const iy = startY + idx * (itemH + 10 * scale);
          ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
          ctx.lineWidth = 1 * scale;
          ctx.beginPath();
          ctx.roundRect(paddingX, iy, w - paddingX * 2, itemH, 10 * scale);
          ctx.fill();
          ctx.stroke();

          ctx.fillStyle = brandColor;
          ctx.font = `900 ${12 * scale}px sans-serif`;
          ctx.fillText(`0${idx + 1}`, paddingX + 14 * scale, iy + 28 * scale);

          ctx.font = `bold ${12 * scale}px sans-serif`;
          ctx.fillStyle = '#ffffff';
          wrapText(ctx, it, paddingX + 44 * scale, iy + 24 * scale, w - paddingX * 2 - 58 * scale, 16 * scale);
        });
        break;
      }

      case 'tech_spec': {
        const tY = 80 * scale;
        ctx.font = `bold ${23 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title, paddingX, tY, w - paddingX * 2, 28 * scale);

        if (slide.body) {
          ctx.font = `${12.5 * scale}px sans-serif`;
          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          wrapText(ctx, slide.body, paddingX, tY + 60 * scale, w - paddingX * 2, 18 * scale);
        }

        const specs = slide.techSpecs && slide.techSpecs.length > 0 ? slide.techSpecs : [
          { label: 'Velocidade Máxima', value: '45 nós' },
          { label: 'Capacidade de Tropa', value: '22 Fuzileiros' },
          { label: 'Blindagem', value: 'Nível III-A' },
          { label: 'Armamento', value: '.50 BMG + MAG 7.62' },
        ];

        const gridY = tY + 130 * scale;
        const cellW = (w - paddingX * 2 - 12 * scale) / 2;
        const cellH = 55 * scale;

        specs.slice(0, 4).forEach((sp, idx) => {
          const col = idx % 2;
          const row = Math.floor(idx / 2);
          const cx = paddingX + col * (cellW + 12 * scale);
          const cy = gridY + row * (cellH + 12 * scale);

          ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
          ctx.strokeStyle = `${brandColor}55`;
          ctx.lineWidth = 1 * scale;
          ctx.beginPath();
          ctx.roundRect(cx, cy, cellW, cellH, 10 * scale);
          ctx.fill();
          ctx.stroke();

          ctx.font = `bold ${9.5 * scale}px sans-serif`;
          ctx.fillStyle = brandLight;
          ctx.fillText(sp.label.toUpperCase(), cx + 12 * scale, cy + 20 * scale);

          ctx.font = `900 ${13 * scale}px sans-serif`;
          ctx.fillStyle = '#ffffff';
          ctx.fillText(sp.value, cx + 12 * scale, cy + 40 * scale);
        });
        break;
      }

      case 'big_number': {
        const numY = 160 * scale;
        ctx.font = `900 ${72 * scale}px sans-serif`;
        ctx.fillStyle = brandColor;
        ctx.fillText(slide.bigNumber || '100+', paddingX, numY);

        if (slide.bigNumberLabel) {
          ctx.font = `bold ${12 * scale}px sans-serif`;
          ctx.fillStyle = isLight ? '#2d3748' : '#ffffff';
          ctx.fillText(slide.bigNumberLabel.toUpperCase(), paddingX, numY + 28 * scale);
        }

        ctx.font = `bold ${22 * scale}px ${fontName}, serif`;
        ctx.fillStyle = isLight ? '#08111d' : '#ffffff';
        wrapText(ctx, slide.title, paddingX, numY + 75 * scale, w - paddingX * 2, 28 * scale);

        if (slide.body) {
          ctx.font = `${13 * scale}px sans-serif`;
          ctx.fillStyle = isLight ? '#4a5568' : 'rgba(255,255,255,0.8)';
          wrapText(ctx, slide.body, paddingX, numY + 145 * scale, w - paddingX * 2, 19 * scale);
        }
        break;
      }

      case 'glass_card': {
        const cardY = 90 * scale;
        const cardH = h - cardY - 65 * scale;
        const cardW = w - paddingX * 2;

        ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 1.5 * scale;
        ctx.beginPath();
        ctx.roundRect(paddingX, cardY, cardW, cardH, 16 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.font = `bold ${23 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title, paddingX + 20 * scale, cardY + 45 * scale, cardW - 40 * scale, 28 * scale);

        if (slide.subtitle) {
          ctx.font = `bold ${12 * scale}px sans-serif`;
          ctx.fillStyle = brandLight;
          ctx.fillText(slide.subtitle, paddingX + 20 * scale, cardY + 110 * scale);
        }

        if (slide.body) {
          ctx.font = `${13 * scale}px sans-serif`;
          ctx.fillStyle = 'rgba(255,255,255,0.85)';
          wrapText(ctx, slide.body, paddingX + 20 * scale, cardY + 145 * scale, cardW - 40 * scale, 20 * scale);
        }
        break;
      }

      case 'quote_nobel': {
        const boxY = 85 * scale;
        const boxH = h - boxY - 65 * scale;
        const boxW = w - paddingX * 2;

        ctx.fillStyle = 'rgba(8, 17, 29, 0.6)';
        ctx.strokeStyle = `${brandColor}66`;
        ctx.lineWidth = 1.5 * scale;
        ctx.beginPath();
        ctx.roundRect(paddingX, boxY, boxW, boxH, 14 * scale);
        ctx.fill();
        ctx.stroke();

        ctx.font = `italic ${40 * scale}px Georgia, serif`;
        ctx.fillStyle = brandColor;
        ctx.fillText('“', paddingX + 16 * scale, boxY + 38 * scale);

        ctx.font = `italic ${14.5 * scale}px Georgia, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, `"${slide.quote}"`, paddingX + 16 * scale, boxY + 68 * scale, boxW - 32 * scale, 22 * scale);

        if (slide.authorName) {
          ctx.font = `bold ${13 * scale}px sans-serif`;
          ctx.fillStyle = brandLight;
          ctx.fillText(slide.authorName, paddingX + 16 * scale, boxY + boxH - 45 * scale);
        }
        if (slide.authorRole) {
          ctx.font = `${10.5 * scale}px sans-serif`;
          ctx.fillStyle = 'rgba(255, 255, 255, 0.65)';
          ctx.fillText(slide.authorRole, paddingX + 16 * scale, boxY + boxH - 25 * scale);
        }
        break;
      }

      case 'cta_final': {
        const centerY = h / 2 - 20 * scale;

        let icon = '⚓';
        if (slide.ctaTriggerType === 'salvar') icon = '📌';
        else if (slide.ctaTriggerType === 'comentar') icon = '💬';
        else if (slide.ctaTriggerType === 'marcar') icon = '👥';
        else if (slide.ctaTriggerType === 'toqueduplo') icon = '❤️';
        else if (slide.ctaTriggerType === 'compartilhar') icon = '📲';

        ctx.font = `${32 * scale}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(icon, w / 2, centerY - 80 * scale);

        ctx.font = `bold ${24 * scale}px ${fontName}, serif`;
        ctx.fillStyle = '#ffffff';
        wrapText(ctx, slide.title, paddingX, centerY - 20 * scale, w - paddingX * 2, 30 * scale, true);

        if (slide.body) {
          ctx.font = `${13 * scale}px sans-serif`;
          ctx.fillStyle = 'rgba(255,255,255,0.85)';
          wrapText(ctx, slide.body, paddingX, centerY + 50 * scale, w - paddingX * 2, 19 * scale, true);
        }

        if (slide.ctaText) {
          const btnY = centerY + 115 * scale;
          const btnW = w - paddingX * 2;
          ctx.fillStyle = brandColor;
          ctx.beginPath();
          ctx.roundRect(paddingX, btnY, btnW, 44 * scale, 24 * scale);
          ctx.fill();

          ctx.font = `bold ${13 * scale}px sans-serif`;
          ctx.fillStyle = '#08111d';
          ctx.fillText(slide.ctaText, w / 2, btnY + 27 * scale);
        }
        ctx.textAlign = 'left';
        break;
      }

      default: {
        const titleY = slide.imageSrc ? h - 190 * scale : 125 * scale;
        ctx.font = `bold ${24 * scale}px ${fontName}, serif`;
        ctx.fillStyle = isLight ? '#08111d' : '#ffffff';
        wrapText(ctx, slide.title, paddingX, titleY, w - paddingX * 2, 30 * scale);

        if (slide.subtitle || slide.body) {
          const text = slide.subtitle || slide.body || '';
          ctx.font = `${13 * scale}px sans-serif`;
          ctx.fillStyle = isLight ? '#4a5568' : 'rgba(255, 255, 255, 0.85)';
          wrapText(ctx, text, paddingX, titleY + 70 * scale, w - paddingX * 2, 19 * scale);
        }
      }
    }

    // ── 6. BARRA DE PROGRESSO INFERIOR (SE FOR CARROSSEL MULTI-SLIDE) ──
    if (total > 1) {
      const barY = h - 24 * scale;
      const barW = w - paddingX * 2;
      const barH = 3.5 * scale;

      ctx.fillStyle = isLight ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.15)';
      ctx.fillRect(paddingX, barY, barW, barH);

      const fillW = (barW * (index + 1)) / total;
      ctx.fillStyle = isLight ? brandColor : '#ffffff';
      ctx.fillRect(paddingX, barY, fillW, barH);

      ctx.font = `bold ${10 * scale}px sans-serif`;
      ctx.fillStyle = isLight ? 'rgba(0,0,0,0.35)' : 'rgba(255,255,255,0.5)';
      ctx.textAlign = 'right';
      ctx.fillText(`${index + 1}/${total}`, w - paddingX, barY - 6 * scale);
      ctx.textAlign = 'left';
    }
  };

  // Desenhar Texturas Especiais
  const drawTexture = (
    ctx: CanvasRenderingContext2D,
    texture: TextureType,
    w: number,
    h: number,
    scale: number,
    accentColor: string
  ) => {
    ctx.save();
    switch (texture) {
      case 'tactical_grid': {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
        ctx.lineWidth = 1 * scale;
        const step = 28 * scale;
        for (let x = 0; x < w; x += step) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, h);
          ctx.stroke();
        }
        for (let y = 0; y < h; y += step) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
        break;
      }
      case 'dots': {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
        const step = 20 * scale;
        for (let x = step / 2; x < w; x += step) {
          for (let y = step / 2; y < h; y += step) {
            ctx.beginPath();
            ctx.arc(x, y, 1.2 * scale, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        break;
      }
      case 'glow_spot': {
        const glowGrad = ctx.createRadialGradient(w * 0.8, h * 0.2, 0, w * 0.8, h * 0.2, w * 0.7);
        glowGrad.addColorStop(0, `${accentColor}33`);
        glowGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = glowGrad;
        ctx.fillRect(0, 0, w, h);
        break;
      }
      case 'naval_corners': {
        ctx.strokeStyle = `${accentColor}88`;
        ctx.lineWidth = 2 * scale;
        const pad = 18 * scale;
        const len = 20 * scale;
        ctx.strokeRect(pad, pad, w - pad * 2, h - pad * 2);
        ctx.fillStyle = accentColor;
        ctx.fillRect(pad, pad, len, 3 * scale);
        ctx.fillRect(pad, pad, 3 * scale, len);
        ctx.fillRect(w - pad - len, pad, len, 3 * scale);
        ctx.fillRect(w - pad - 3 * scale, pad, 3 * scale, len);
        ctx.fillRect(pad, h - pad - 3 * scale, len, 3 * scale);
        ctx.fillRect(pad, h - pad - len, 3 * scale, len);
        ctx.fillRect(w - pad - len, h - pad - 3 * scale, len, 3 * scale);
        ctx.fillRect(w - pad - 3 * scale, h - pad - len, 3 * scale, len);
        break;
      }
      case 'diagonal_stripes': {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        ctx.lineWidth = 1.5 * scale;
        for (let i = -w; i < w + h; i += 24 * scale) {
          ctx.beginPath();
          ctx.moveTo(i, 0);
          ctx.lineTo(i + h, h);
          ctx.stroke();
        }
        break;
      }
      case 'halftone_dots': {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.045)';
        const step = 18 * scale;
        for (let x = 0; x < w; x += step) {
          for (let y = 0; y < h; y += step) {
            const rad = (1 + Math.sin((x + y) * 0.025)) * 1.5 * scale;
            ctx.beginPath();
            ctx.arc(x, y, rad, 0, Math.PI * 2);
            ctx.fill();
          }
        }
        break;
      }
      case 'vignette_shadow': {
        const vigGrad = ctx.createRadialGradient(w / 2, h / 2, w * 0.25, w / 2, h / 2, w * 0.75);
        vigGrad.addColorStop(0, 'transparent');
        vigGrad.addColorStop(1, 'rgba(0, 0, 0, 0.75)');
        ctx.fillStyle = vigGrad;
        ctx.fillRect(0, 0, w, h);
        break;
      }
      case 'camo_tactical': {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.035)';
        ctx.lineWidth = 1.5 * scale;
        for (let y = 0; y < h; y += 32 * scale) {
          ctx.beginPath();
          for (let x = 0; x < w; x += 10 * scale) {
            const waveY = y + Math.sin((x + y) * 0.03) * 12 * scale;
            if (x === 0) ctx.moveTo(x, waveY);
            else ctx.lineTo(x, waveY);
          }
          ctx.stroke();
        }
        break;
      }
    }
    ctx.restore();
  };

  // Helper de quebra de texto
  const wrapText = (
    ctx: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    maxWidth: number,
    lineHeight: number,
    isCentered = false
  ) => {
    const words = text.split(' ');
    let line = '';
    let curY = y;

    for (let n = 0; n < words.length; n++) {
      const testLine = line + words[n] + ' ';
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && n > 0) {
        ctx.fillText(line, isCentered ? x + maxWidth / 2 : x, curY);
        line = words[n] + ' ';
        curY += lineHeight;
      } else {
        line = testLine;
      }
    }
    ctx.fillText(line, isCentered ? x + maxWidth / 2 : x, curY);
  };

  const renderCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = currentFormat.previewWidth;
    canvas.height = currentFormat.previewHeight;

    if (activeSlide.imageSrc) {
      const img = new Image();
      img.src = activeSlide.imageSrc;
      img.onload = () => {
        drawSlideGraphics(ctx, activeSlide, currentSlideIndex, slides.length, canvas.width, canvas.height);
      };
    }
    drawSlideGraphics(ctx, activeSlide, currentSlideIndex, slides.length, canvas.width, canvas.height);
  };

  const updateActiveSlide = (field: keyof CarouselSlide, value: any) => {
    const updated = [...slides];
    updated[currentSlideIndex] = {
      ...updated[currentSlideIndex],
      [field]: value,
    };
    setSlides(updated);
  };

  // Aplicar Presets de Tema / Design
  const applyThemePreset = (preset: DesignThemePreset) => {
    let sColor = '#060e18';
    let mColor = '#0b1c34';
    let eColor = '#13315c';
    let texture: TextureType = 'glow_spot';
    let font: CarouselSlide['fontFamily'] = 'Playfair Display';

    switch (preset) {
      case 'tatico_operacional':
        sColor = '#05070a';
        mColor = '#0f172a';
        eColor = '#00e5ff';
        texture = 'tactical_grid';
        font = 'Space Grotesk';
        setBrandColor('#00e5ff');
        setBrandLight('#70f5ff');
        break;
      case 'manchete_impacto':
        sColor = '#0a0a0c';
        mColor = '#1e1b18';
        eColor = '#e11d48';
        texture = 'diagonal_stripes';
        font = 'DM Sans';
        setBrandColor('#fbbf24');
        setBrandLight('#fde68a');
        break;
      case 'clean_institucional':
        sColor = '#f8fafc';
        mColor = '#e2e8f0';
        eColor = '#cbd5e1';
        texture = 'dots';
        font = 'DM Sans';
        setBrandColor('#0284c7');
        setBrandLight('#38bdf8');
        break;
      default: // editorial_nobre
        sColor = '#060e18';
        mColor = '#0b1c34';
        eColor = '#13315c';
        texture = 'glow_spot';
        font = 'Playfair Display';
        setBrandColor('#c5a059');
        setBrandLight('#e0c287');
        break;
    }

    const updated = slides.map((s) => ({
      ...s,
      gradColorStart: sColor,
      gradColorMid: mColor,
      gradColorEnd: eColor,
      texture,
      fontFamily: font,
    }));
    setSlides(updated);
    toast.success(`Estilo ${preset.toUpperCase()} aplicado a todos os slides!`);
  };

  // Upload de Imagens
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const b64 = event.target?.result as string;
        setUploadedImages((prev) => [...prev, b64]);
        if (!activeSlide.imageSrc) {
          updateActiveSlide('imageSrc', b64);
        }
        toast.success(`Foto ${file.name} adicionada à galeria!`);
      };
      reader.readAsDataURL(file);
    });
  };

  // Adicionar e Remover Slide
  const handleAddSlide = () => {
    const newSlide: CarouselSlide = {
      id: String(Date.now()),
      layoutType: 'hero_full',
      tag: 'NOVO DESTAQUE',
      title: 'Título de Impacto para o Novo Slide',
      body: 'Descrição rica com detalhes sobre os fatos ocorridos.',
      bgType: 'gradient',
      gradColorStart: activeSlide.gradColorStart,
      gradColorMid: activeSlide.gradColorMid,
      gradColorEnd: activeSlide.gradColorEnd,
      gradAngle: 165,
      texture: activeSlide.texture,
      imageOpacity: 80,
      overlayStrength: 70,
      fontFamily: activeSlide.fontFamily,
    };
    setSlides([...slides, newSlide]);
    setCurrentSlideIndex(slides.length);
    toast.success('Slide adicionado!');
  };

  const handleDeleteSlide = (index: number) => {
    if (slides.length <= 1) {
      toast.error('O projeto precisa ter pelo menos 1 slide!');
      return;
    }
    const filtered = slides.filter((_, i) => i !== index);
    setSlides(filtered);
    setCurrentSlideIndex(Math.max(0, index - 1));
    toast.success('Slide removido!');
  };

  // Otimizar Título com IA (Gemini 3.7 Flash)
  const handleOptimizeHeadline = async () => {
    if (!geminiApiKey) {
      toast.error('Chave de API do Gemini não encontrada.');
      return;
    }
    setIsOptimizingHeadline(true);
    try {
      const prompt = `Reescreva o seguinte título para um post militar do Instagram (Corpo de Fuzileiros Navais) para que seja altamente atraente, dinâmico e retenha a atenção nos primeiros 3 segundos. Retorne APENAS o novo título, sem aspas nem explicações:

Título original: "${activeSlide.title}"`;
      const res = await generateGeminiContent(prompt, 'Você é um redator sênior de comunicação social militar especializado em mídias sociais.', geminiApiKey);
      if (res && res.trim()) {
        updateActiveSlide('title', res.trim());
        toast.success('Título otimizado com Gemini 3.7 Flash!');
      }
    } catch (e: any) {
      toast.error(`Falha ao otimizar: ${e.message}`);
    } finally {
      setIsOptimizingHeadline(false);
    }
  };

  // Executar Geração com IA (Diretor de Arte Autônomo com Gemini 3.7 Flash)
  const handleRunAiDirector = async () => {
    if (!aiPromptInput.trim()) {
      toast.error('Descreva o tema, matéria ou a ideia visual para a IA!');
      return;
    }
    setIsGeneratingAi(true);

    try {
      if (geminiApiKey) {
        const sysPrompt = `Você é o Diretor de Arte e Redator de Mídias Sociais do Comando-Geral do Corpo de Fuzileiros Navais.
Crie um carrossel de 5 a 6 slides com roteiro completo em formato JSON.
Retorne ESTRITAMENTE um array JSON contendo objetos no seguinte formato:
[
  {
    "layoutType": "hero_full",
    "tag": "XII CONCURSO DE CRÔNICAS",
    "title": "Título impactante",
    "subtitle": "Subtítulo explicativo",
    "bgType": "gradient",
    "gradColorStart": "#060e18",
    "gradColorMid": "#0b1c34",
    "gradColorEnd": "#13315c",
    "texture": "glow_spot",
    "fontFamily": "Playfair Display"
  },
  {
    "layoutType": "big_number",
    "tag": "MÉTRICA",
    "bigNumber": "100%",
    "bigNumberLabel": "Prontidão",
    "title": "Título",
    "body": "Texto de apoio",
    "bgType": "dark",
    "gradColorStart": "#08111d",
    "gradColorMid": "#0b1626",
    "gradColorEnd": "#08111d",
    "texture": "tactical_grid",
    "fontFamily": "DM Sans"
  },
  {
    "layoutType": "info_list",
    "tag": "PONTOS-CHAVE",
    "title": "Destaques Principais",
    "listItems": ["Item 1", "Item 2", "Item 3", "Item 4"],
    "bgType": "gradient",
    "gradColorStart": "#08111d",
    "gradColorMid": "#112239",
    "gradColorEnd": "#08111d",
    "texture": "halftone_dots",
    "fontFamily": "Space Grotesk"
  },
  {
    "layoutType": "quote_nobel",
    "tag": "PALAVRAS DE HONRA",
    "title": "Mensagem Oficial",
    "quote": "Frase solene",
    "authorName": "Comandante-Geral do CFN",
    "authorRole": "Marinha do Brasil",
    "bgType": "gradient",
    "gradColorStart": "#091524",
    "gradColorMid": "#162e4d",
    "gradColorEnd": "#091524",
    "texture": "naval_corners",
    "fontFamily": "Playfair Display"
  },
  {
    "layoutType": "cta_final",
    "tag": "HONRA & ENGAJAMENTO",
    "title": "Fechamento de impacto",
    "body": "Curta e salve este post",
    "ctaText": "Salve e compartilhe essa conquista ↗",
    "ctaTriggerType": "salvar",
    "bgType": "gradient",
    "gradColorStart": "#060e18",
    "gradColorMid": "#163663",
    "gradColorEnd": "#c5a059",
    "texture": "glow_spot",
    "fontFamily": "Playfair Display"
  }
]`;

        const userPrompt = `Gere os slides para o seguinte tema: "${aiPromptInput}". Modo: ${aiMode}.`;
        const resText = await generateGeminiContent(userPrompt, sysPrompt, geminiApiKey);
        const cleanJson = resText.replace(/```json/gi, '').replace(/```/g, '').trim();
        const parsed = JSON.parse(cleanJson);

        if (Array.isArray(parsed) && parsed.length > 0) {
          const formatted: CarouselSlide[] = parsed.map((item: any, i: number) => ({
            id: String(Date.now() + i),
            layoutType: item.layoutType || 'hero_full',
            tag: item.tag || 'DESTAQUE',
            title: item.title || 'Título',
            subtitle: item.subtitle,
            body: item.body,
            bigNumber: item.bigNumber,
            bigNumberLabel: item.bigNumberLabel,
            quote: item.quote,
            authorName: item.authorName,
            authorRole: item.authorRole,
            ctaText: item.ctaText,
            ctaTriggerType: item.ctaTriggerType || 'salvar',
            breakingBadge: item.breakingBadge,
            breakingDate: item.breakingDate,
            pollQuestion: item.pollQuestion,
            pollOptionA: item.pollOptionA,
            pollOptionB: item.pollOptionB,
            listItems: item.listItems,
            techSpecs: item.techSpecs,
            bgType: item.bgType || 'gradient',
            gradColorStart: item.gradColorStart || '#060e18',
            gradColorMid: item.gradColorMid || '#0b1c34',
            gradColorEnd: item.gradColorEnd || '#13315c',
            gradAngle: item.gradAngle || 165,
            texture: item.texture || 'glow_spot',
            imageSrc: uploadedImages[i] || undefined,
            imageOpacity: 85,
            overlayStrength: 75,
            fontFamily: item.fontFamily || (aiMode === 'creative' ? 'Space Grotesk' : 'Playfair Display'),
          }));

          setSlides(formatted);
          setCurrentSlideIndex(0);
          setIsGeneratingAi(false);
          setIsAiModalOpen(false);
          confetti({ particleCount: 70, spread: 80, origin: { y: 0.6 } });
          toast.success('Carrossel gerado pelo Gemini 3.7 Flash com sucesso!');
          return;
        }
      }
    } catch (err) {
      console.warn('Fallback para gerador interno:', err);
    }

    // Fallback Inteligente caso a API não responda
    const generated: CarouselSlide[] = [
      {
        id: '1',
        layoutType: 'hero_full',
        tag: 'COBERTURA ESPECIAL',
        title: aiPromptInput.slice(0, 55) + '...',
        subtitle: 'Acompanhe os principais momentos e destaques em formato exclusivo.',
        bgType: 'gradient',
        gradColorStart: '#060e18',
        gradColorMid: '#0d223f',
        gradColorEnd: '#1b3f73',
        gradAngle: 145,
        texture: 'glow_spot',
        imageSrc: uploadedImages[0],
        imageOpacity: 90,
        overlayStrength: 75,
        fontFamily: aiMode === 'creative' ? 'Space Grotesk' : 'Playfair Display',
      },
      {
        id: '2',
        layoutType: 'breaking_news',
        tag: 'MANCHETE TÁTICA',
        breakingBadge: '🚨 COMUNICADO OFICIAL • CGCFN',
        breakingDate: 'HOJE • BRASÍLIA - DF',
        title: 'Prontidão Operacional e Modernização Tecnológica',
        body: 'A Força de Fuzileiros da Esquadra reafirma o compromisso com a defesa da Pátria.',
        bgType: 'dark',
        gradColorStart: '#08111d',
        gradColorMid: '#161e2e',
        gradColorEnd: '#08111d',
        gradAngle: 180,
        texture: 'tactical_grid',
        imageOpacity: 50,
        overlayStrength: 85,
        fontFamily: 'DM Sans',
      },
      {
        id: '3',
        layoutType: 'info_list',
        tag: 'PONTOS-CHAVE',
        title: 'Destaques Estratégicos da Missão',
        listItems: [
          'Emprego de Meios Blindados em Terreno Costeiro',
          'Comunicações Integradas e Controle de Área',
          'Mobilização Rápida de Efetivo Especializado',
          'Excelência na Execução e Segurança Operacional',
        ],
        bgType: 'gradient',
        gradColorStart: '#08111d',
        gradColorMid: '#112239',
        gradColorEnd: '#08111d',
        gradAngle: 145,
        texture: 'halftone_dots',
        imageOpacity: 45,
        overlayStrength: 80,
        fontFamily: 'Space Grotesk',
      },
      {
        id: '4',
        layoutType: 'quote_nobel',
        tag: 'PALAVRAS DO COMANDO',
        title: 'Uma mensagem de liderança e futuro',
        quote: 'A dedicação e o trabalho em equipe transformam desafios em conquistas inesquecíveis para todos nós.',
        authorName: 'Comando-Geral do CFN',
        authorRole: 'Marinha do Brasil',
        bgType: 'gradient',
        gradColorStart: '#091524',
        gradColorMid: '#162e4d',
        gradColorEnd: '#091524',
        gradAngle: 135,
        texture: 'naval_corners',
        imageOpacity: 50,
        overlayStrength: 80,
        fontFamily: 'Playfair Display',
      },
      {
        id: '5',
        layoutType: 'cta_final',
        tag: 'COMPARTILHE A HISTÓRIA',
        title: 'Juntos construindo o futuro da nossa Força.',
        body: 'Curta, salve e envie para os companheiros e familiares!',
        ctaText: 'Salve esta publicação para consultar ↗',
        ctaTriggerType: 'salvar',
        bgType: 'gradient',
        gradColorStart: '#060e18',
        gradColorMid: '#1b3b6b',
        gradColorEnd: '#c5a059',
        gradAngle: 155,
        texture: 'glow_spot',
        imageOpacity: 40,
        overlayStrength: 80,
        fontFamily: 'Playfair Display',
      },
    ];

    setSlides(generated);
    setCurrentSlideIndex(0);
    setIsGeneratingAi(false);
    setIsAiModalOpen(false);
    confetti({ particleCount: 60, spread: 70, origin: { y: 0.6 } });
    toast.success('Carrossel gerado pelo Diretor de Arte IA!');
  };

  // Exportação em Resolução Nativa sem Perdas (Full HD / 4K)
  const exportSlideToPng = (slide: CarouselSlide, index: number, total: number) => {
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = currentFormat.width;
    exportCanvas.height = currentFormat.height;
    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    drawSlideGraphics(ctx, slide, index, total, exportCanvas.width, exportCanvas.height);

    const link = document.createElement('a');
    link.download = `sisgab_${format}_slide_${index + 1}.png`;
    link.href = exportCanvas.toDataURL('image/png', 1.0);
    link.click();
  };

  const handleExportAll = () => {
    slides.forEach((slide, idx) => {
      setTimeout(() => {
        exportSlideToPng(slide, idx, slides.length);
      }, idx * 250);
    });
    confetti({ particleCount: 100, spread: 90, origin: { y: 0.5 } });
    toast.success(`Exportando todos os ${slides.length} slides em alta resolução!`);
  };

  const handleExportCurrent = () => {
    exportSlideToPng(activeSlide, currentSlideIndex, slides.length);
    toast.success(`Slide ${currentSlideIndex + 1} baixado com sucesso!`);
  };

  return (
    <div className="space-y-6 pb-20 max-w-[1600px] mx-auto text-slate-100">
      {/* ── HEADER PRINCIPAL DO ESTÚDIO ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-3xl bg-[#0b1222]/80 border border-slate-800 backdrop-blur-xl shadow-2xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-300 border border-cyan-500/30">
              Estúdio Criativo IA • Multi-Formatos
            </span>
            <span className="text-slate-500 text-xs">• SISGAB Design Suite 3.0</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-black tracking-tight text-white flex items-center gap-3">
            Diretor de Arte IA & Estúdio Multi-Formatos
          </h1>
          <p className="text-slate-400 text-xs max-w-2xl">
            Crie artes dinâmicas em 4:5, 9:16 Stories, 1:1 Feed ou 16:9 com degradês customizáveis, texturas táticas, plantão breaking news e Gemini 3.7 Flash.
          </p>
        </div>

        {/* Formatos e Ações de Topo */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Seletor de Formatos (4:5, 9:16, 1:1, 16:9) */}
          <div className="flex items-center p-1 rounded-2xl bg-slate-950 border border-slate-800 shadow-inner">
            {(Object.keys(FORMAT_CONFIGS) as PostFormat[]).map((fmtKey) => {
              const fmt = FORMAT_CONFIGS[fmtKey];
              const Icon = fmt.icon;
              return (
                <button
                  key={fmtKey}
                  type="button"
                  onClick={() => setFormat(fmtKey)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    format === fmtKey
                      ? 'bg-[#c5a059] text-slate-950 shadow-md font-black'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title={fmt.description}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{fmt.ratioName}</span>
                </button>
              );
            })}
          </div>

          {/* Botão Diretor de Arte IA */}
          <button
            type="button"
            onClick={() => setIsAiModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-lg shadow-cyan-500/25 transition-all"
          >
            <Sparkles className="w-4 h-4" />
            <span>Diretor de Arte IA ✨</span>
          </button>

          {/* Botão Exportar Todos */}
          <button
            type="button"
            onClick={handleExportAll}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/20 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Exportar ({slides.length} PNGs)</span>
          </button>
        </div>
      </div>

      {/* ── SELETOR DE PRESETS VISUAIS (1 CLIQUE) ── */}
      <div className="p-4 rounded-3xl bg-[#0b1222] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-lg">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
          <Palette className="w-4 h-4 text-[#c5a059]" />
          <span>Presets de Estilo Visual:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => applyThemePreset('editorial_nobre')}
            className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-900 border border-[#c5a059]/50 text-xs font-bold text-[#c5a059] transition-all hover:scale-105"
          >
            🏛️ Editorial Nobre (Dourado)
          </button>
          <button
            onClick={() => applyThemePreset('tatico_operacional')}
            className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-900 border border-cyan-500/50 text-xs font-bold text-cyan-300 transition-all hover:scale-105"
          >
            ⚡ Tático Operacional (Ciano)
          </button>
          <button
            onClick={() => applyThemePreset('manchete_impacto')}
            className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-900 border border-rose-500/50 text-xs font-bold text-rose-300 transition-all hover:scale-105"
          >
            📰 Manchete Impacto (Rubro)
          </button>
          <button
            onClick={() => applyThemePreset('clean_institucional')}
            className="px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-900 border border-sky-500/50 text-xs font-bold text-sky-300 transition-all hover:scale-105"
          >
            ✨ Clean Institucional (Off-White)
          </button>
        </div>
      </div>

      {/* ── GRID PRINCIPAL: CONTROLES & LAYERS (5 COLS) | PREVIEW DINÂMICO (7 COLS) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── PAINEL ESQUERDO: CONTROLES & LAYERS ── */}
        <div className="lg:col-span-5 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-5">
          {/* Seletor de Miniaturas de Slides */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="w-4 h-4" />
                <span>Sequência de Slides ({slides.length})</span>
              </span>
              <button
                type="button"
                onClick={handleAddSlide}
                className="flex items-center gap-1 text-[11px] font-bold text-cyan-400 hover:text-cyan-300"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Novo Slide</span>
              </button>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
              {slides.map((s, idx) => (
                <button
                  key={s.id}
                  onClick={() => setCurrentSlideIndex(idx)}
                  className={`px-3 py-2 rounded-xl text-xs font-bold shrink-0 transition-all flex items-center gap-1.5 ${
                    currentSlideIndex === idx
                      ? 'bg-[#c5a059] text-slate-950 font-black shadow-md shadow-[#c5a059]/20'
                      : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  <span>Slide {idx + 1}</span>
                  {slides.length > 1 && currentSlideIndex === idx && (
                    <Trash2
                      className="w-3 h-3 text-slate-900 hover:text-red-700 ml-1 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSlide(idx);
                      }}
                    />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Seletor de Modelo de Layout do Slide (11 Modelos) */}
          <div className="space-y-1.5 text-xs">
            <label className="text-slate-300 font-bold flex items-center gap-1.5">
              <Grid className="w-3.5 h-3.5 text-[#c5a059]" />
              <span>Modelo de Layout ({activeSlide.layoutType})</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'hero_full', name: '🖼️ Foto Full + Overlay' },
                { id: 'breaking_news', name: '🚨 Plantão / Manchete' },
                { id: 'glass_card', name: '🪟 Card Vidro (Glass)' },
                { id: 'big_number', name: '🔢 Número Gigante' },
                { id: 'info_list', name: '💡 Lista Infográfica' },
                { id: 'tech_spec', name: '🛡️ Ficha Técnica Meio' },
                { id: 'quiz_poll', name: '📊 Enquete / Quiz A/B' },
                { id: 'before_after_split', name: '⚖️ Antes/Depois Dual' },
                { id: 'quote_nobel', name: '💬 Citação / Aspas' },
                { id: 'split_photo', name: '🌓 Split Texto/Foto' },
                { id: 'cta_final', name: '🎯 Fechamento & CTA' },
              ].map((l) => (
                <button
                  key={l.id}
                  onClick={() => updateActiveSlide('layoutType', l.id)}
                  className={`py-2 px-3 rounded-xl text-xs font-bold text-left truncate transition-all border ${
                    activeSlide.layoutType === l.id
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {l.name}
                </button>
              ))}
            </div>
          </div>

          {/* Gerador de Fundo: Degradês & Texturas */}
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
            <span className="text-[11px] font-black text-cyan-300 uppercase tracking-wider block flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Fundo: Degradês & Texturas Dinâmicas</span>
            </span>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Cor Início</label>
                <input
                  type="color"
                  value={activeSlide.gradColorStart}
                  onChange={(e) => updateActiveSlide('gradColorStart', e.target.value)}
                  className="w-full h-8 rounded-lg bg-transparent cursor-pointer border border-slate-800"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Cor Meio</label>
                <input
                  type="color"
                  value={activeSlide.gradColorMid}
                  onChange={(e) => updateActiveSlide('gradColorMid', e.target.value)}
                  className="w-full h-8 rounded-lg bg-transparent cursor-pointer border border-slate-800"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Cor Fim</label>
                <input
                  type="color"
                  value={activeSlide.gradColorEnd}
                  onChange={(e) => updateActiveSlide('gradColorEnd', e.target.value)}
                  className="w-full h-8 rounded-lg bg-transparent cursor-pointer border border-slate-800"
                />
              </div>
            </div>

            {/* Ângulo do Gradiente */}
            <div>
              <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                <span>Ângulo do Degradê</span>
                <span className="font-mono">{activeSlide.gradAngle}°</span>
              </div>
              <input
                type="range"
                min="0"
                max="360"
                value={activeSlide.gradAngle}
                onChange={(e) => updateActiveSlide('gradAngle', Number(e.target.value))}
                className="w-full accent-[#c5a059]"
              />
            </div>

            {/* Seletor de Texturas (10 Opções) */}
            <div>
              <label className="text-[10px] text-slate-400 block mb-1">Textura Gráfica / Camada</label>
              <select
                value={activeSlide.texture}
                onChange={(e) => updateActiveSlide('texture', e.target.value as TextureType)}
                className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white font-bold"
              >
                <option value="none">🚫 Nenhuma (Clean)</option>
                <option value="tactical_grid">📐 Grid Tático Militar</option>
                <option value="dots">░ Pontilhado (Dot Matrix)</option>
                <option value="glow_spot">✨ Brilho Radial (Glow)</option>
                <option value="naval_corners">⚓ Moldura com Cantos Navais</option>
                <option value="diagonal_stripes">╱ Linhas Diagonais Táticas</option>
                <option value="film_grain">🎞️ Grão de Filme 35mm (Noise)</option>
                <option value="halftone_dots">🖨️ Retícula Halftone Militar</option>
                <option value="vignette_shadow">🌑 Vinheta Radial de Foco</option>
                <option value="camo_tactical">🗺️ Padrão Topográfico / Camuflado</option>
              </select>
            </div>
          </div>

          {/* Upload e Galeria de Fotos */}
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-300 flex items-center gap-1.5">
                <ImageIcon className="w-3.5 h-3.5 text-[#c5a059]" />
                <span>Foto do Slide & Fusão ({uploadedImages.length})</span>
              </span>
              <label className="cursor-pointer text-[10px] font-black text-cyan-400 hover:underline flex items-center gap-1">
                <Upload className="w-3 h-3" />
                <span>Carregar Fotos</span>
                <input type="file" multiple accept="image/*" onChange={handleImageUpload} className="hidden" />
              </label>
            </div>

            {uploadedImages.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-1">
                {uploadedImages.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`Upload ${i}`}
                    onClick={() => updateActiveSlide('imageSrc', src)}
                    className={`w-14 h-14 object-cover rounded-lg cursor-pointer border-2 transition-all shrink-0 ${
                      activeSlide.imageSrc === src ? 'border-[#c5a059] scale-105' : 'border-slate-800 opacity-60 hover:opacity-100'
                    }`}
                  />
                ))}
              </div>
            )}

            {activeSlide.imageSrc && (
              <div className="space-y-2 pt-1 border-t border-slate-900">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Opacidade da Foto</span>
                  <span className="font-mono">{activeSlide.imageOpacity}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={activeSlide.imageOpacity}
                  onChange={(e) => updateActiveSlide('imageOpacity', Number(e.target.value))}
                  className="w-full accent-[#c5a059]"
                />

                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Intensidade do Overlay Escuro</span>
                  <span className="font-mono">{activeSlide.overlayStrength}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={activeSlide.overlayStrength}
                  onChange={(e) => updateActiveSlide('overlayStrength', Number(e.target.value))}
                  className="w-full accent-[#c5a059]"
                />
              </div>
            )}
          </div>

          {/* Campos de Conteúdo do Slide */}
          <div className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-300 font-bold mb-1">Tag / Categoria</label>
              <input
                type="text"
                value={activeSlide.tag}
                onChange={(e) => updateActiveSlide('tag', e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono focus:outline-none"
              />
            </div>

            {/* Layout Breaking News */}
            {activeSlide.layoutType === 'breaking_news' && (
              <div className="grid grid-cols-2 gap-2 p-3 bg-slate-950 rounded-2xl border border-rose-900/50">
                <div>
                  <label className="block text-slate-400 text-[10px]">Faixa de Alerta Superior</label>
                  <input
                    type="text"
                    value={activeSlide.breakingBadge || ''}
                    placeholder="🚨 PLANTÃO CGCFN"
                    onChange={(e) => updateActiveSlide('breakingBadge', e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-[10px]">Data & Local</label>
                  <input
                    type="text"
                    value={activeSlide.breakingDate || ''}
                    placeholder="HOJE • BRASÍLIA - DF"
                    onChange={(e) => updateActiveSlide('breakingDate', e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
              </div>
            )}

            {/* Layout Quiz Poll */}
            {activeSlide.layoutType === 'quiz_poll' && (
              <div className="space-y-2 p-3 bg-slate-950 rounded-2xl border border-cyan-900/50">
                <label className="block text-slate-400 text-[10px]">Opções da Enquete (A vs B)</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Opção A"
                    value={activeSlide.pollOptionA || ''}
                    onChange={(e) => updateActiveSlide('pollOptionA', e.target.value)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Opção B"
                    value={activeSlide.pollOptionB || ''}
                    onChange={(e) => updateActiveSlide('pollOptionB', e.target.value)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
              </div>
            )}

            {/* Layout Comparativo Dual */}
            {activeSlide.layoutType === 'before_after_split' && (
              <div className="grid grid-cols-2 gap-2 p-3 bg-slate-950 rounded-2xl border border-slate-800">
                <div>
                  <label className="block text-slate-400 text-[10px]">Rótulo Coluna 1</label>
                  <input
                    type="text"
                    value={activeSlide.beforeLabel || ''}
                    placeholder="1808 • TRADIÇÃO"
                    onChange={(e) => updateActiveSlide('beforeLabel', e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-[10px]">Rótulo Coluna 2</label>
                  <input
                    type="text"
                    value={activeSlide.afterLabel || ''}
                    placeholder="2026 • MODERNIDADE"
                    onChange={(e) => updateActiveSlide('afterLabel', e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
              </div>
            )}

            {/* Layout Big Number */}
            {activeSlide.layoutType === 'big_number' && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Número Gigante</label>
                  <input
                    type="text"
                    value={activeSlide.bigNumber || ''}
                    onChange={(e) => updateActiveSlide('bigNumber', e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white font-black text-sm"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Rótulo do Número</label>
                  <input
                    type="text"
                    value={activeSlide.bigNumberLabel || ''}
                    onChange={(e) => updateActiveSlide('bigNumberLabel', e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs"
                  />
                </div>
              </div>
            )}

            {/* Título com Botão de Otimização IA */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-slate-300 font-bold">Título (Headline de Impacto)</label>
                <button
                  type="button"
                  onClick={handleOptimizeHeadline}
                  disabled={isOptimizingHeadline}
                  className="flex items-center gap-1 text-[10px] font-bold text-cyan-400 hover:text-cyan-300"
                >
                  <Wand2 className="w-3 h-3" />
                  <span>{isOptimizingHeadline ? 'Otimizando...' : '🪄 Otimizar com IA'}</span>
                </button>
              </div>
              <textarea
                rows={2}
                value={activeSlide.title}
                onChange={(e) => updateActiveSlide('title', e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none"
              />
            </div>

            {/* Layout Citação */}
            {activeSlide.layoutType === 'quote_nobel' && (
              <div className="space-y-2 p-3 bg-slate-950 rounded-2xl border border-slate-800">
                <label className="block text-slate-400 text-[10px]">Texto da Citação / Aspas</label>
                <textarea
                  rows={3}
                  value={activeSlide.quote || ''}
                  onChange={(e) => updateActiveSlide('quote', e.target.value)}
                  className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Nome do Autor"
                    value={activeSlide.authorName || ''}
                    onChange={(e) => updateActiveSlide('authorName', e.target.value)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Cargo / Posto"
                    value={activeSlide.authorRole || ''}
                    onChange={(e) => updateActiveSlide('authorRole', e.target.value)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs"
                  />
                </div>
              </div>
            )}

            {/* Layout CTA Final (Presets de Gatilhos de Engajamento) */}
            {activeSlide.layoutType === 'cta_final' && (
              <div className="space-y-2 p-3 bg-slate-950 rounded-2xl border border-[#c5a059]/40">
                <label className="block text-[#c5a059] text-[10px] font-bold">🎯 Presets de Gatilhos de Engajamento</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {[
                    { id: 'salvar', label: '📌 Salvar Post', text: 'Salve este post para consultar sempre ↗' },
                    { id: 'marcar', label: '👥 Marcar Amigo', text: 'Marque um fuzileiro nos comentários ↗' },
                    { id: 'comentar', label: '💬 Votar / Opinar', text: 'Deixe sua opinião nos comentários ↗' },
                    { id: 'toqueduplo', label: '❤️ Toque 2x', text: 'Toque 2x se tem orgulho da Marinha ↗' },
                    { id: 'compartilhar', label: '📲 Compartilhar', text: 'Envie para quem sonha com a Marinha ↗' },
                  ].map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => {
                        updateActiveSlide('ctaTriggerType', g.id);
                        updateActiveSlide('ctaText', g.text);
                      }}
                      className={`px-2 py-1.5 rounded-lg text-[10px] font-bold text-center border transition-all ${
                        activeSlide.ctaTriggerType === g.id
                          ? 'bg-[#c5a059] text-slate-950 border-[#c5a059]'
                          : 'bg-slate-900 text-slate-300 border-slate-800 hover:text-white'
                      }`}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Texto do Botão CTA"
                  value={activeSlide.ctaText || ''}
                  onChange={(e) => updateActiveSlide('ctaText', e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs mt-2"
                />
              </div>
            )}

            {/* Texto de Apoio / Descrição Padrão */}
            {activeSlide.layoutType !== 'quote_nobel' && (
              <div>
                <label className="block text-slate-300 font-bold mb-1">Texto de Apoio / Descrição</label>
                <textarea
                  rows={3}
                  value={activeSlide.body || activeSlide.subtitle || ''}
                  onChange={(e) => updateActiveSlide('body', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none"
                />
              </div>
            )}
          </div>

          {/* Exportar Slide Individual */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            <button
              type="button"
              onClick={handleExportCurrent}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-white font-bold text-xs transition-all"
            >
              <Download className="w-4 h-4 text-[#c5a059]" />
              <span>Baixar Este Slide ({currentFormat.width}×{currentFormat.height}px)</span>
            </button>
          </div>
        </div>

        {/* ── PAINEL DIREITO: SIMULADOR & CANVAS ── */}
        <div className="lg:col-span-7 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl flex flex-col items-center space-y-4">
          <div className="w-full flex items-center justify-between">
            <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
              <Eye className="w-4 h-4" />
              <span>
                Visualizador {currentFormat.name} ({currentFormat.ratioName})
              </span>
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-[#c5a059] font-mono text-[10px] font-bold">
              Slide {currentSlideIndex + 1} de {slides.length}
            </span>
          </div>

          {/* Moldura do Simulador */}
          <div className="bg-slate-950 p-4 rounded-3xl border border-slate-800 shadow-2xl flex flex-col items-center">
            <div
              className="relative overflow-hidden rounded-2xl shadow-2xl bg-black flex items-center justify-center border border-slate-700"
              style={{
                width: `${currentFormat.previewWidth}px`,
                height: `${currentFormat.previewHeight}px`,
              }}
            >
              <canvas
                ref={canvasRef}
                style={{
                  width: `${currentFormat.previewWidth}px`,
                  height: `${currentFormat.previewHeight}px`,
                }}
                className="object-cover"
              />

              {/* Botões de Navegação Flutuantes */}
              {currentSlideIndex > 0 && (
                <button
                  type="button"
                  onClick={() => setCurrentSlideIndex((prev) => Math.max(0, prev - 1))}
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center backdrop-blur-xs transition-all"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
              )}

              {currentSlideIndex < slides.length - 1 && (
                <button
                  type="button"
                  onClick={() => setCurrentSlideIndex((prev) => Math.min(slides.length - 1, prev + 1))}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center backdrop-blur-xs transition-all"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Informações de Resolução de Exportação */}
            <div className="w-full flex items-center justify-between text-xs text-slate-400 pt-3 mt-3 border-t border-slate-900">
              <span>Dimensão Nativa: {currentFormat.width} × {currentFormat.height} px</span>
              <span className="text-emerald-400 font-bold">Ultra Alta Resolução ✓</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── MODAL DIRETOR DE ARTE IA (GEMINI 3.7 FLASH) ── */}
      {isAiModalOpen && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl bg-[#0b1222] border border-cyan-500/40 rounded-3xl p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 text-white flex items-center justify-center shadow-md shadow-cyan-500/30">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-black text-white">Diretor de Arte com Gemini 3.7 Flash</h3>
                  <p className="text-[11px] text-slate-400">Gera roteiros completos, layouts, copy de retenção e paletas dinâmicas</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAiModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Seletor de Modo: Institucional vs Criativo Livre */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setAiMode('institutional')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  aiMode === 'institutional'
                    ? 'bg-[#c5a059]/15 border-[#c5a059] text-white shadow-md'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                <span className="font-black text-xs block text-[#c5a059]">🛡️ Modo Institucional Padronizado</span>
                <span className="text-[11px] text-slate-400 mt-0.5 block leading-tight">
                  Segue rigorosamente cores navais, brasão e tipografia oficial.
                </span>
              </button>

              <button
                type="button"
                onClick={() => setAiMode('creative')}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  aiMode === 'creative'
                    ? 'bg-cyan-500/15 border-cyan-400 text-white shadow-md'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                <span className="font-black text-xs block text-cyan-300">✨ Modo Criativo & Inovador</span>
                <span className="text-[11px] text-slate-400 mt-0.5 block leading-tight">
                  Degradês ousados, texturas modernas, números gigantes e novos cortes.
                </span>
              </button>
            </div>

            {/* Campo de Prompt Livre */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-slate-300">Prompt / Instrução para o Diretor de Arte:</label>
              <textarea
                rows={5}
                placeholder="Exemplo: Crie um carrossel sobre o Concurso de Crônicas com tom solene, degradê azul marinho e toques dourados, com aspas emocionantes do Comandante e destaque para o vencedor David..."
                value={aiPromptInput}
                onChange={(e) => setAiPromptInput(e.target.value)}
                className="w-full p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsAiModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 hover:text-white"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isGeneratingAi}
                onClick={handleRunAiDirector}
                className="flex items-center gap-2 px-6 py-2.5 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-black text-xs shadow-lg shadow-cyan-500/25 transition-all"
              >
                {isGeneratingAi ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Criando Arte com Gemini 3.7 Flash...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Gerar Carrossel Inovador</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
