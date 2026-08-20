import React, { useState, useEffect, useRef } from 'react';
import {
  Armchair,
  Users,
  Printer,
  Sparkles,
  Search,
  UserCheck,
  UserX,
  Shuffle,
  Eye,
  CheckCircle2,
  AlertCircle,
  Award,
  ChevronDown,
  Calendar,
  Layers,
  Palette,
  Sliders,
  Check,
  Plus,
  Trash2,
  Edit2,
  ExternalLink,
  Shield,
  QrCode,
  FileText,
  BadgePercent,
  RotateCw,
  MapPin,
  Upload,
  Bookmark,
  Save,
  Grid,
  Image as ImageIcon,
  Copy,
  Star,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import type { JadeEvento, JadeConvidado } from '../../types/database';
import { getBrasiliaDateStr } from '../../utils/formatters';

const ROWS = ['A', 'B', 'C', 'D', 'E'];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8];

export interface JadePrintConfig {
  model: 'prisma_a4_4slots' | 'prisma_a4_2slots' | 'cracha_vip_a6' | 'cracha_horizontal' | 'cartao_mesa_luxo' | 'display_a5_acrilico';
  theme: 'clean_ouro' | 'navy_luxo' | 'papel_linho' | 'camuflado_tatica' | 'custom_upload';
  borderStyle: 'filete_duplo_ouro' | 'cantoneira_naval' | 'minimalista' | 'sem_borda';
  customBackgroundUrl?: string;
  bgOpacity: number;
  logoPreset: 'cgcfn' | 'mb' | 'defesa' | 'presidencia';
  logoPosition: 'esquerda' | 'centro' | 'ambos';
  headerText: string;
  subHeaderText: string;
  companionTerm: 'RESERVADO' | 'ACOMPANHANTE' | 'CONVIDADO DE HONRA';
  starsOverride: 'auto' | '4_stars' | '3_stars' | '2_stars' | '1_star' | 'none';
  showQrCode: boolean;
  showRankStars: boolean;
  showSeatNumber: boolean;
}

export interface JadeSavedTemplate {
  id: string;
  name: string;
  createdAt: string;
  config: JadePrintConfig;
}

const DEFAULT_PRINT_CONFIG: JadePrintConfig = {
  model: 'prisma_a4_4slots',
  theme: 'clean_ouro',
  borderStyle: 'filete_duplo_ouro',
  bgOpacity: 100,
  logoPreset: 'cgcfn',
  logoPosition: 'esquerda',
  headerText: 'MARINHA DO BRASIL',
  subHeaderText: 'COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS',
  companionTerm: 'RESERVADO',
  starsOverride: 'auto',
  showQrCode: true,
  showRankStars: true,
  showSeatNumber: true,
};

const SAMPLE_PREVIEW_GUEST: JadeConvidado = {
  id: 1,
  evento_id: 1,
  nome: 'ALMIRANTE DE ESQUADRA SILVA SANTOS',
  posto_graduacao: 'AE (FN) • COMANDANTE-GERAL',
  cargo_funcao: 'Comando-Geral do Corpo de Fuzileiros Navais',
  categoria: 'Autoridade Militar',
  assento_id: 'A-1',
  status_confirmacao: 'confirmado',
  status_placa: 'pendente',
  max_acompanhantes: 1,
};

const DEFAULT_TEMPLATES: JadeSavedTemplate[] = [
  {
    id: 'tpl_oficial_cgcfn',
    name: '📜 Prisma Clássico A4 (Branco & Ouro)',
    createdAt: '2026-08-18',
    config: DEFAULT_PRINT_CONFIG,
  },
  {
    id: 'tpl_gala_navy',
    name: '⚓ Prisma Gala Navy (Azul Marinho & Ouro)',
    createdAt: '2026-08-18',
    config: {
      ...DEFAULT_PRINT_CONFIG,
      theme: 'navy_luxo',
      borderStyle: 'cantoneira_naval',
    },
  },
  {
    id: 'tpl_prisma_duplo',
    name: '🏷️ Prisma Duplo A4 (2 por Folha)',
    createdAt: '2026-08-18',
    config: {
      ...DEFAULT_PRINT_CONFIG,
      model: 'prisma_a4_2slots',
      theme: 'clean_ouro',
      borderStyle: 'filete_duplo_ouro',
    },
  },
  {
    id: 'tpl_cracha_vip_a6',
    name: '🪪 Crachá VIP Vertical A6 (4 por A4)',
    createdAt: '2026-08-18',
    config: {
      ...DEFAULT_PRINT_CONFIG,
      model: 'cracha_vip_a6',
      theme: 'clean_ouro',
    },
  },
  {
    id: 'tpl_cracha_horizontal',
    name: '💳 Crachá Horizontal / Porta-Crachá (6 por A4)',
    createdAt: '2026-08-18',
    config: {
      ...DEFAULT_PRINT_CONFIG,
      model: 'cracha_horizontal',
      theme: 'clean_ouro',
    },
  },
  {
    id: 'tpl_cartao_mesa',
    name: '📑 Cartão de Assento Luxo (8 por A4)',
    createdAt: '2026-08-18',
    config: {
      ...DEFAULT_PRINT_CONFIG,
      model: 'cartao_mesa_luxo',
      borderStyle: 'minimalista',
    },
  },
];

export const SeatingMaster: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'mapa' | 'design' | 'convidados'>('design');
  const [eventos, setEventos] = useState<JadeEvento[]>([]);
  const [selectedEventoId, setSelectedEventoId] = useState<number | null>(null);
  const [convidados, setConvidados] = useState<JadeConvidado[]>([]);
  const [selectedSeat, setSelectedSeat] = useState<string | null>(null);
  const [searchGuest, setSearchGuest] = useState('');
  const [loading, setLoading] = useState(true);

  // Configuração do Estúdio de Design de Placas
  const [printConfig, setPrintConfig] = useState<JadePrintConfig>(DEFAULT_PRINT_CONFIG);
  const [previewGuest, setPreviewGuest] = useState<JadeConvidado | null>(null);
  const [filterPlateStatus, setFilterPlateStatus] = useState<'todos' | 'pendente' | 'impressa'>('todos');

  // Catálogo de Modelos e Templates Salvos (com mesclagem automática dos padrões)
  const [savedTemplates, setSavedTemplates] = useState<JadeSavedTemplate[]>(() => {
    try {
      const stored = localStorage.getItem('sisgab_jade_templates');
      if (!stored) return DEFAULT_TEMPLATES;
      const parsed: JadeSavedTemplate[] = JSON.parse(stored);
      const userCustom = parsed.filter((p) => !DEFAULT_TEMPLATES.some((d) => d.id === p.id));
      return [...DEFAULT_TEMPLATES, ...userCustom];
    } catch {
      return DEFAULT_TEMPLATES;
    }
  });
  const [newTemplateName, setNewTemplateName] = useState('');
  const [showSaveTemplateModal, setShowSaveTemplateModal] = useState(false);

  // Modal Novo Convidado
  const [novoConvidadoModal, setNovoConvidadoModal] = useState(false);
  const [novoConvidado, setNovoConvidado] = useState({
    nome: '',
    posto_graduacao: 'AE - Almirante de Esquadra',
    cargo_funcao: '',
    categoria: 'Autoridade Militar',
    max_acompanhantes: 0,
  });

  // Modal Editar Convidado
  const [editConvidadoModal, setEditConvidadoModal] = useState(false);
  const [editingGuest, setEditingGuest] = useState<JadeConvidado | null>(null);

  // Modal Novo Evento
  const [novoEventoModal, setNovoEventoModal] = useState(false);
  const [novoEvento, setNovoEvento] = useState({
    nome: '',
    data_evento: getBrasiliaDateStr(),
    local_evento: 'Salão Nobre do CGCFN',
    tipo_evento: 'cerimonia',
  });

  // Modal Gerenciar Eventos / Cerimônias
  const [gerenciarEventosModal, setGerenciarEventosModal] = useState(false);
  const [searchEventoQuery, setSearchEventoQuery] = useState('');

  // Modal Editar Evento
  const [editEventoModal, setEditEventoModal] = useState(false);
  const [editingEvento, setEditingEvento] = useState<JadeEvento | null>(null);

  // Modal Confirmação de Exclusão
  const [deleteConfirmModal, setDeleteConfirmModal] = useState<{ id: number; nome: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Modo de Impressão (Apenas a placa selecionada vs Todas em lote)
  const [printMode, setPrintMode] = useState<'single' | 'batch_all'>('single');

  // Modo de Layout do Estúdio (Lado a Lado vs Um Abaixo do Outro)
  const [layoutMode, setLayoutMode] = useState<'side_by_side' | 'stacked'>('stacked');

  // Busca na lista de convidados (Aba 3)
  const [searchGuestInList, setSearchGuestInList] = useState('');

  // Dispara Impressão Limpa / Exportação em PDF de Apenas a Placa Selecionada
  const handlePrintSingle = () => {
    const printable = document.getElementById('printable-jade-area');
    if (!printable) {
      toast.error('Área da placa não encontrada.');
      return;
    }

    const htmlContent = printable.outerHTML;
    const printWin = window.open('', '_blank', 'width=900,height=1100');
    if (!printWin) {
      toast.error('Pop-up bloqueado pelo navegador. Permita pop-ups para imprimir/baixar PDF.');
      return;
    }

    const docTitle = `Placa_${effectiveGuest.nome.replace(/\s+/g, '_')}_A4`;
    printWin.document.write(`
      <!DOCTYPE html>
      <html lang="pt-BR">
      <head>
        <meta charset="UTF-8">
        <title>${docTitle}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          @page {
            size: A4 portrait;
            margin: 0;
          }
          html, body {
            margin: 0;
            padding: 0;
            background: #ffffff !important;
            color: #000000 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .a4-page {
            width: 210mm;
            height: 297mm;
            max-height: 297mm;
            margin: 0 auto;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            page-break-after: always;
            break-after: page;
          }
          .no-print {
            display: none !important;
          }
        </style>
      </head>
      <body class="bg-white p-0 m-0">
        <div class="a4-page p-6">
          ${htmlContent}
        </div>
        <script>
          window.onload = function() {
            setTimeout(function() {
              window.focus();
              window.print();
            }, 600);
          };
        </script>
      </body>
      </html>
    `);
    printWin.document.close();
  };

  // Dispara Impressão Limpa / Baixar PDF de Todas as Placas do Evento em Lote
  const handlePrintAll = () => {
    const listToPrint = convidados.length > 0 ? convidados : [effectiveGuest];
    const printWin = window.open('', '_blank', 'width=900,height=1100');
    if (!printWin) {
      toast.error('Pop-up bloqueado pelo navegador. Permita pop-ups para imprimir.');
      return;
    }

    // Gera o HTML de cada folha A4 individualmente
    const pagesHtml = listToPrint
      .map((guest) => {
        const guestRank = guest.posto_graduacao || '';
        const guestStars = printConfig.showRankStars ? getRankStars(guestRank) : '';
        const borderCls = getBorderStyle();
        const themeCls = getThemeBackgroundStyle();

        if (printConfig.model === 'prisma_a4_4slots') {
          return `
            <div class="a4-page p-6">
              <div class="h-full flex flex-col justify-between p-4 rounded-xl border border-slate-300 relative overflow-hidden ${themeCls} ${borderCls}">
                <div class="h-[10%] flex items-center justify-center border-b border-dashed border-slate-400 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                  --- 1. ABA DE ENCAIXE SUPERIOR (30 MM) ---
                </div>
                <div class="h-[38%] flex flex-col items-center justify-center border-b border-dashed border-slate-400 bg-slate-500/5 rotate-180 text-center py-2 px-3 space-y-1">
                  <h4 class="text-base font-black uppercase">${guest.nome}</h4>
                  <p class="text-xs font-bold text-[#c5a059]">${guest.cargo_funcao || guestRank}</p>
                </div>
                <div class="h-[4%] flex items-center justify-center border-b-2 border-dashed border-[#c5a059] text-[9px] font-mono font-black text-[#c5a059] uppercase tracking-widest">
                  ✂️ --- LINHA CENTRAL DE VINCO & DOBRA EM V --- ✂️
                </div>
                <div class="h-[38%] flex flex-col justify-between py-3 px-3 text-center">
                  <div class="flex items-center justify-between">
                    <span class="text-3xl">⚓</span>
                    <div>
                      <p class="text-xs font-black uppercase">${printConfig.headerText}</p>
                      <p class="text-[9px] font-bold opacity-70 uppercase">${printConfig.subHeaderText}</p>
                      ${guestStars ? `<div class="text-amber-500 font-bold text-sm tracking-widest">${guestStars}</div>` : ''}
                    </div>
                    <span class="text-xs font-mono border p-1 rounded">QR</span>
                  </div>
                  <div class="py-2 border-y-2 border-[#c5a059]/40 space-y-1">
                    <p class="text-xs font-bold text-[#c5a059] uppercase">${guestRank}</p>
                    <h2 class="text-2xl font-black uppercase">${guest.nome}</h2>
                    <p class="text-xs opacity-80">${guest.cargo_funcao || 'Autoridade Convidada de Honra'}</p>
                  </div>
                  <div class="flex justify-between text-[10px] opacity-70 font-mono">
                    <span>SOLENIDADE: ${currentEvento?.nome || 'GABINETE CGCFN'}</span>
                    <span>ASSENTO: ${guest.assento_id || 'RESERVADO'}</span>
                  </div>
                </div>
                <div class="h-[10%] flex items-center justify-center border-t border-dashed border-slate-400 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                  --- 4. ABA DE BASE INFERIOR (30 MM) ---
                </div>
              </div>
            </div>
          `;
        }

        return `
          <div class="a4-page p-6">
            <div class="p-6 rounded-xl border border-slate-300 text-center space-y-3 ${themeCls} ${borderCls}">
              <span class="text-3xl">⚓</span>
              <p class="text-xs font-black uppercase">${printConfig.headerText}</p>
              ${guestStars ? `<div class="text-amber-500 font-bold text-sm tracking-widest">${guestStars}</div>` : ''}
              <p class="text-xs font-bold text-[#c5a059] uppercase">${guestRank}</p>
              <h2 class="text-2xl font-black uppercase">${guest.nome}</h2>
              <p class="text-xs opacity-75">${guest.cargo_funcao || 'Convidado de Honra'}</p>
              <div class="flex justify-between text-[10px] opacity-60 font-mono pt-3 border-t">
                <span>${currentEvento?.nome || 'GABINETE CGCFN'}</span>
                <span>ASSENTO: ${guest.assento_id || 'RESERVADO'}</span>
              </div>
            </div>
          </div>
        `;
      })
      .join('\n');

    printWin.document.write(`
      <!DOCTYPE html>
      <html lang="pt-BR">
      <head>
        <meta charset="UTF-8">
        <title>Placas_${currentEvento?.nome || 'Cerimonial'}_Lote_A4</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
          @page {
            size: A4 portrait;
            margin: 0;
          }
          html, body {
            margin: 0;
            padding: 0;
            background: #ffffff !important;
            color: #000000 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .a4-page {
            width: 210mm;
            height: 297mm;
            max-height: 297mm;
            margin: 0 auto;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            page-break-after: always;
            break-after: page;
          }
        </style>
      </head>
      <body class="bg-white p-0 m-0">
        ${pagesHtml}
        <script>
          window.onload = function() {
            setTimeout(function() {
              window.focus();
              window.print();
            }, 800);
          };
        </script>
      </body>
      </html>
    `);
    printWin.document.close();
  };

  useEffect(() => {
    loadEventos();
  }, []);

  useEffect(() => {
    if (selectedEventoId) {
      loadConvidados(selectedEventoId);
    }
  }, [selectedEventoId]);

  const loadEventos = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('jade_eventos')
        .select('*')
        .order('id', { ascending: false });

      if (!error && data && data.length > 0) {
        // Deduplica eventos por ID único e remove duplicatas com mesmo nome e data
        const uniqueMap = new Map<string, JadeEvento>();
        data.forEach((ev: JadeEvento) => {
          const key = `${ev.nome.trim().toUpperCase()}_${ev.data_evento}`;
          if (!uniqueMap.has(key)) {
            uniqueMap.set(key, ev);
          }
        });

        const distinctEventos = Array.from(uniqueMap.values());
        setEventos(distinctEventos);
        if (!selectedEventoId || !distinctEventos.some((e) => e.id === selectedEventoId)) {
          setSelectedEventoId(distinctEventos[0].id);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar eventos:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadConvidados = async (eventoId: number) => {
    try {
      const { data, error } = await supabase
        .from('jade_convidados')
        .select('*')
        .eq('evento_id', eventoId)
        .order('id', { ascending: false });

      if (!error && data) {
        setConvidados(data as JadeConvidado[]);
        if (data.length > 0 && !previewGuest) {
          const firstPending = data.find((c) => c.status_placa === 'pendente') || data[0];
          setPreviewGuest(firstPending);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar convidados:', err);
    }
  };

  const getGuestAtSeat = (seatId: string) => {
    return convidados.find((c) => c.assento_id === seatId);
  };

  const handleSeatClick = (seatId: string) => {
    setSelectedSeat(selectedSeat === seatId ? null : seatId);
  };

  const allocateGuestToSeat = async (guestId: number, seatId: string) => {
    setConvidados((prev) =>
      prev.map((c) => {
        if (c.assento_id === seatId) return { ...c, assento_id: null };
        if (c.id === guestId) return { ...c, assento_id: seatId };
        return c;
      })
    );

    setSelectedSeat(null);
    toast.success('Assento alocado com sucesso!');

    try {
      await supabase
        .from('jade_convidados')
        .update({ assento_id: seatId })
        .eq('id', guestId);
    } catch (e) {
      console.warn('Erro ao alocar assento:', e);
    }
  };

  const deallocateSeat = async (guestId: number) => {
    setConvidados((prev) =>
      prev.map((c) => (c.id === guestId ? { ...c, assento_id: null } : c))
    );
    setSelectedSeat(null);
    toast.info('Assento desalocado.');

    try {
      await supabase
        .from('jade_convidados')
        .update({ assento_id: null })
        .eq('id', guestId);
    } catch (e) {
      console.warn('Erro ao desalocar:', e);
    }
  };

  const handleUpdatePlateStatus = async (guestId: number, status: string) => {
    setConvidados((prev) =>
      prev.map((c) => (c.id === guestId ? { ...c, status_placa: status } : c))
    );

    if (previewGuest && previewGuest.id === guestId) {
      setPreviewGuest({ ...previewGuest, status_placa: status });
    }

    toast.success(`Status da placa atualizado para ${status.toUpperCase()}!`);

    try {
      await supabase
        .from('jade_convidados')
        .update({ status_placa: status })
        .eq('id', guestId);
    } catch (e) {
      console.warn('Erro ao atualizar status da placa:', e);
    }
  };

  // Upload de Imagem de Fundo / Croqui
  const handleUploadBackground = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      setPrintConfig({
        ...printConfig,
        theme: 'custom_upload',
        customBackgroundUrl: dataUrl,
      });
      toast.success('Imagem de fundo carregada com sucesso!');
    };
    reader.readAsDataURL(file);
  };

  // Salvar Template Personalizado no Catálogo
  const handleSaveTemplate = () => {
    if (!newTemplateName.trim()) {
      toast.error('Informe um nome para o modelo.');
      return;
    }

    const newTpl: JadeSavedTemplate = {
      id: `tpl_${Date.now()}`,
      name: newTemplateName.trim(),
      createdAt: getBrasiliaDateStr(),
      config: { ...printConfig },
    };

    const updated = [newTpl, ...savedTemplates];
    setSavedTemplates(updated);
    localStorage.setItem('sisgab_jade_templates', JSON.stringify(updated));

    confetti({ particleCount: 50, spread: 60, origin: { y: 0.6 } });
    toast.success(`Modelo "${newTemplateName}" salvo no catálogo!`);
    setNewTemplateName('');
    setShowSaveTemplateModal(false);
  };

  // Excluir Template do Catálogo
  const handleDeleteTemplate = (tplId: string, tplName: string) => {
    if (!window.confirm(`Deseja realmente remover o modelo "${tplName}" do catálogo?`)) return;
    const updated = savedTemplates.filter((t) => t.id !== tplId);
    setSavedTemplates(updated);
    localStorage.setItem('sisgab_jade_templates', JSON.stringify(updated));
    toast.info(`Modelo "${tplName}" removido.`);
  };

  // Cadastrar Convidado e Acompanhantes
  const handleSalvarConvidado = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoConvidado.nome.trim() || !selectedEventoId) {
      toast.error('Informe o nome da autoridade.');
      return;
    }

    try {
      const { data: mainGuest, error: mainErr } = await supabase
        .from('jade_convidados')
        .insert({
          evento_id: selectedEventoId,
          nome: novoConvidado.nome.toUpperCase(),
          posto_graduacao: novoConvidado.posto_graduacao,
          cargo_funcao: novoConvidado.cargo_funcao,
          categoria: novoConvidado.categoria,
          max_acompanhantes: novoConvidado.max_acompanhantes,
          status_placa: 'pendente',
        })
        .select()
        .single();

      if (mainErr) throw mainErr;

      if (novoConvidado.max_acompanhantes > 0 && mainGuest) {
        const acompList = [];
        for (let i = 1; i <= novoConvidado.max_acompanhantes; i++) {
          acompList.push({
            evento_id: selectedEventoId,
            nome: `ACOMP. ${novoConvidado.nome.toUpperCase()} (${i}/${novoConvidado.max_acompanhantes})`,
            posto_graduacao: novoConvidado.posto_graduacao,
            cargo_funcao: `Acompanhante de ${novoConvidado.nome.toUpperCase()}`,
            categoria: novoConvidado.categoria,
            convidado_principal_id: mainGuest.id,
            max_acompanhantes: 0,
            status_placa: 'pendente',
          });
        }
        await supabase.from('jade_convidados').insert(acompList);
      }

      confetti({ particleCount: 50, spread: 50, origin: { y: 0.7 } });
      toast.success('Autoridade cadastrada com sucesso!');
      setNovoConvidadoModal(false);
      setNovoConvidado({
        nome: '',
        posto_graduacao: 'AE - Almirante de Esquadra',
        cargo_funcao: '',
        categoria: 'Autoridade Militar',
        max_acompanhantes: 0,
      });
      loadConvidados(selectedEventoId);
    } catch (err: any) {
      toast.error(`Erro ao cadastrar: ${err.message}`);
    }
  };

  // Atualizar Convidado Existente
  const handleAtualizarConvidado = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingGuest || !editingGuest.nome.trim()) return;

    try {
      const { error } = await supabase
        .from('jade_convidados')
        .update({
          nome: editingGuest.nome.toUpperCase(),
          posto_graduacao: editingGuest.posto_graduacao,
          cargo_funcao: editingGuest.cargo_funcao,
          categoria: editingGuest.categoria,
          max_acompanhantes: editingGuest.max_acompanhantes,
        })
        .eq('id', editingGuest.id);

      if (error) throw error;

      toast.success('Dados da autoridade atualizados com sucesso!');
      setEditConvidadoModal(false);
      setEditingGuest(null);
      if (selectedEventoId) loadConvidados(selectedEventoId);
    } catch (err: any) {
      toast.error(`Erro ao atualizar: ${err.message}`);
    }
  };

  // Excluir Convidado do Evento
  const handleExcluirConvidado = async (guestId: number, guestNome: string) => {
    if (!window.confirm(`Deseja realmente remover "${guestNome}" deste evento?`)) return;

    try {
      const { error } = await supabase
        .from('jade_convidados')
        .delete()
        .eq('id', guestId);

      if (error) throw error;

      toast.success(`Autoridade "${guestNome}" removida do evento.`);
      if (selectedEventoId) loadConvidados(selectedEventoId);
      if (previewGuest?.id === guestId) setPreviewGuest(null);
    } catch (err: any) {
      toast.error(`Erro ao excluir: ${err.message}`);
    }
  };

  // Criar Novo Evento de Cerimônia
  const handleSalvarNovoEvento = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!novoEvento.nome.trim()) {
      toast.error('Informe o nome do evento / cerimônia.');
      return;
    }

    try {
      const { data, error } = await supabase
        .from('jade_eventos')
        .insert({
          nome: novoEvento.nome.toUpperCase(),
          data_evento: novoEvento.data_evento,
          local: novoEvento.local_evento,
          tipo_layout: 'auditorio',
          status: 'ativo',
        })
        .select()
        .single();

      if (error) throw error;

      confetti({ particleCount: 60, spread: 60, origin: { y: 0.6 } });
      toast.success(`Evento "${novoEvento.nome}" criado com sucesso!`);
      setNovoEventoModal(false);
      setNovoEvento({
        nome: '',
        data_evento: getBrasiliaDateStr(),
        local_evento: 'Salão Nobre do CGCFN',
        tipo_evento: 'cerimonia',
      });

      await loadEventos();
      if (data) setSelectedEventoId(data.id);
    } catch (err: any) {
      toast.error(`Erro ao criar evento: ${err.message}`);
    }
  };

  // Atualizar Evento Existente
  const handleAtualizarEvento = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEvento || !editingEvento.nome.trim()) return;

    try {
      const { error } = await supabase
        .from('jade_eventos')
        .update({
          nome: editingEvento.nome.toUpperCase(),
          data_evento: editingEvento.data_evento,
          local: editingEvento.local,
          tipo_layout: editingEvento.tipo_layout || 'auditorio',
        })
        .eq('id', editingEvento.id);

      if (error) throw error;

      toast.success('Evento atualizado com sucesso!');
      setEditEventoModal(false);
      setEditingEvento(null);
      await loadEventos();
    } catch (err: any) {
      toast.error(`Erro ao atualizar evento: ${err.message}`);
    }
  };

  // Abrir Modal de Confirmação de Exclusão
  const handleExcluirEvento = (eventoId: number, eventoNome: string) => {
    setDeleteConfirmModal({ id: eventoId, nome: eventoNome });
  };

  // Executar Exclusão Definitiva no Banco
  const executeExcluirEvento = async (eventoId: number, eventoNome: string) => {
    try {
      setIsDeleting(true);

      // 1. Remove convidados do evento
      await supabase.from('jade_convidados').delete().eq('evento_id', eventoId);

      // 2. Remove o evento por ID
      const { error } = await supabase.from('jade_eventos').delete().eq('id', eventoId);
      if (error) {
        console.warn('Erro ao deletar por ID:', error);
      }

      // 3. Limpa também duplicatas do mesmo nome se existirem
      await supabase.from('jade_eventos').delete().eq('nome', eventoNome);

      toast.success(`Evento "${eventoNome}" excluído com sucesso.`);
      setDeleteConfirmModal(null);
      setEditEventoModal(false);
      setGerenciarEventosModal(false);

      const remaining = eventos.filter((e) => e.id !== eventoId && e.nome !== eventoNome);
      setEventos(remaining);
      setSelectedEventoId(remaining.length > 0 ? remaining[0].id : null);
      await loadEventos();
    } catch (err: any) {
      toast.error(`Erro ao excluir evento: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const currentEvento = eventos.find((e) => e.id === selectedEventoId);
  const effectiveGuest: JadeConvidado = previewGuest || convidados[0] || SAMPLE_PREVIEW_GUEST;
  const totalSeats = ROWS.length * COLS.length;
  const occupiedSeats = convidados.filter((c) => c.assento_id).length;

  const filteredConvidados = convidados.filter((c) => {
    const matchesSearch =
      c.nome.toLowerCase().includes(searchGuest.toLowerCase()) ||
      (c.cargo_funcao && c.cargo_funcao.toLowerCase().includes(searchGuest.toLowerCase())) ||
      (c.posto_graduacao && c.posto_graduacao.toLowerCase().includes(searchGuest.toLowerCase()));

    if (!matchesSearch) return false;
    if (filterPlateStatus === 'pendente') return c.status_placa === 'pendente';
    if (filterPlateStatus === 'impressa') return c.status_placa === 'impressa';
    return true;
  });

  // Helper para Estrelas de Patentes
  const getRankStars = (posto?: string | null) => {
    if (printConfig.starsOverride === '4_stars') return '★ ★ ★ ★';
    if (printConfig.starsOverride === '3_stars') return '★ ★ ★';
    if (printConfig.starsOverride === '2_stars') return '★ ★';
    if (printConfig.starsOverride === '1_star') return '★';
    if (printConfig.starsOverride === 'none') return null;

    if (!posto) return null;
    const p = posto.toUpperCase();
    if (p.includes('ESQUADRA') || p.includes('AE') || p.includes('EXÉRCITO') || p.includes('BRIGADEIRO')) return '★ ★ ★ ★';
    if (p.includes('VICE') || p.includes('VA') || p.includes('DIVISÃO') || p.includes('MAJOR-BRIGADEIRO')) return '★ ★ ★';
    if (p.includes('CONTRA') || p.includes('CA') || p.includes('BRIGADA')) return '★ ★';
    if (p.includes('CMG') || p.includes('GUERRA') || p.includes('CORONEL')) return '★';
    return null;
  };

  // Helper para Fundo CSS
  const getThemeBackgroundStyle = () => {
    if (printConfig.theme === 'navy_luxo') {
      return 'bg-gradient-to-b from-[#071329] via-[#0b1c3d] to-[#071329] text-white';
    }
    if (printConfig.theme === 'papel_linho') {
      return 'bg-[#fcfaf2] text-slate-900 border-[#d4af37]';
    }
    if (printConfig.theme === 'camuflado_tatica') {
      return 'bg-gradient-to-b from-[#1b261d] via-[#243327] to-[#1b261d] text-slate-100';
    }
    if (printConfig.theme === 'custom_upload' && printConfig.customBackgroundUrl) {
      return 'bg-cover bg-center text-slate-950';
    }
    return 'bg-white text-slate-950';
  };

  // Helper para Molduras
  const getBorderStyle = () => {
    if (printConfig.borderStyle === 'filete_duplo_ouro') {
      return 'border-4 border-[#c5a059] ring-2 ring-[#c5a059]/40 ring-offset-2';
    }
    if (printConfig.borderStyle === 'cantoneira_naval') {
      return 'border-2 border-[#c5a059] shadow-xl';
    }
    if (printConfig.borderStyle === 'minimalista') {
      return 'border border-slate-300 shadow-sm';
    }
    return 'border-0';
  };

  return (
    <div className="space-y-6 pb-12">
      {/* ── HERO BANNER: DESTAQUE MÁXIMO DO EVENTO SELECIONADO ── */}
      <div className="p-5 rounded-3xl bg-gradient-to-r from-[#0b1222] via-[#111c35] to-[#0b1222] border-2 border-[#c5a059]/60 shadow-2xl space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-[#c5a059] text-slate-950 text-[10px] font-black uppercase tracking-wider shadow-sm">
                🎖️ Cerimônia Ativa
              </span>
              <span className="text-slate-400 text-xs">• Gestor de Assentos & Placas JADE</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#c5a059] tracking-tight uppercase drop-shadow-md">
              {currentEvento?.nome || 'SELECIONE UM EVENTO'}
            </h1>
            <p className="text-xs text-slate-300 flex items-center gap-3 flex-wrap pt-0.5">
              <span className="flex items-center gap-1 font-bold text-white">
                <Calendar className="w-3.5 h-3.5 text-[#00e5ff]" />
                Data: {currentEvento?.data_evento || 'A Definir'}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <MapPin className="w-3.5 h-3.5 text-[#c5a059]" />
                Local: <strong className="text-white">{currentEvento?.local || 'Salão Nobre / Auditório'}</strong>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1 text-slate-300">
                <Users className="w-3.5 h-3.5 text-emerald-400" />
                <strong className="text-emerald-400">{convidados.length}</strong> autoridades cadastradas ({occupiedSeats} com assento alocado)
              </span>
            </p>
          </div>

          {/* Seleção de Evento e Botões de Ação */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-700 px-3.5 py-2 rounded-2xl text-xs shadow-md">
              <Calendar className="w-4 h-4 text-[#c5a059]" />
              <select
                value={selectedEventoId || ''}
                onChange={(e) => setSelectedEventoId(Number(e.target.value))}
                className="bg-transparent text-white font-bold focus:outline-none cursor-pointer max-w-[190px] truncate"
              >
                {eventos.map((ev) => (
                  <option key={ev.id} value={ev.id} className="bg-slate-900 text-white">
                    {ev.nome} ({ev.data_evento})
                  </option>
                ))}
              </select>
            </div>

            {currentEvento && (
              <>
                <button
                  onClick={() => {
                    setEditingEvento(currentEvento);
                    setEditEventoModal(true);
                  }}
                  className="p-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-xs font-bold transition-all"
                  title="Editar Nome, Data e Local deste Evento"
                >
                  <Edit2 className="w-4 h-4" />
                </button>

                <button
                  onClick={() => handleExcluirEvento(currentEvento.id, currentEvento.nome)}
                  className="p-2 rounded-2xl bg-red-500/10 hover:bg-red-500/25 text-red-400 border border-red-500/40 text-xs font-bold transition-all"
                  title="Excluir este Evento e todos os Convidados"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}

            <button
              onClick={() => setGerenciarEventosModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold text-xs shadow-md transition-all hover:scale-105"
              title="Gerenciar, Listar e Excluir Eventos / Cerimônias"
            >
              <Sliders className="w-3.5 h-3.5 text-[#00e5ff]" />
              <span>Gerenciar Eventos</span>
            </button>

            <button
              onClick={() => setNovoEventoModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl bg-cyan-950/60 hover:bg-cyan-900/60 text-[#00e5ff] border border-[#00e5ff]/40 font-bold text-xs shadow-md transition-all hover:scale-105"
              title="Cadastrar Novo Evento / Cerimônia"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Novo Evento</span>
            </button>

            <button
              onClick={() => setNovoConvidadoModal(true)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/25 transition-all hover:scale-105"
            >
              <Plus className="w-4 h-4" />
              <span>+ Convidado & Acomp.</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── NAVEGAÇÃO ENTRE AS 3 ABAS TÁTICAS (LIMPA E SEM SOBREPOSIÇÃO) ── */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto scrollbar-none">
        <button
          onClick={() => setActiveTab('design')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'design'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Palette className="w-4 h-4" />
          <span>🎨 1. Estúdio de Design & Impressão de Placas</span>
        </button>

        <button
          onClick={() => setActiveTab('mapa')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'mapa'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Armchair className="w-4 h-4" />
          <span>🪑 2. Mapeamento & Auditório ({occupiedSeats}/{totalSeats})</span>
        </button>

        <button
          onClick={() => setActiveTab('convidados')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'convidados'
              ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20 font-black'
              : 'bg-slate-900/60 text-slate-400 hover:text-white border border-slate-800'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>👥 3. Lista de Autoridades & Acompanhantes ({convidados.length})</span>
        </button>
      </div>

      {/* ── ABA 1: ESTÚDIO DE DESIGN & IMPRESSÃO DE PLACAS JADE ── */}
      {activeTab === 'design' && (
        <div className={layoutMode === 'stacked' ? 'space-y-6' : 'grid grid-cols-1 xl:grid-cols-12 gap-6 items-start'}>
          {/* LADO ESQUERDO/TOPO: PAINEL DE CONTROLE DE LAYOUT & ESTILOS */}
          <div className={`${layoutMode === 'stacked' ? 'w-full' : 'xl:col-span-5'} p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-5`}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h2 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-2">
                  <Sliders className="w-4 h-4" />
                  <span>Configurador do Modelo & Layout</span>
                </h2>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Dimensões reais, furações de dobra A4, temas e insígnias.
                </p>
              </div>

              {/* Botões do Topo do Configurador: Salvar Modelo + Alternador de Disposição */}
              <div className="flex items-center gap-2">
                <div className="flex items-center p-0.5 rounded-xl bg-slate-950 border border-slate-800 text-[11px]">
                  <button
                    onClick={() => setLayoutMode('stacked')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                      layoutMode === 'stacked'
                        ? 'bg-[#c5a059] text-slate-950 font-black'
                        : 'text-slate-400 hover:text-white'
                    }`}
                    title="Layout em Linha (Expandido)"
                  >
                    🔽 Expandido
                  </button>
                  <button
                    onClick={() => setLayoutMode('side_by_side')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all ${
                      layoutMode === 'side_by_side'
                        ? 'bg-[#c5a059] text-slate-950 font-black'
                        : 'text-slate-400 hover:text-white'
                    }`}
                    title="Layout Lado a Lado (2 Colunas)"
                  >
                    🔲 Lado a Lado
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => setShowSaveTemplateModal(true)}
                  className="px-3 py-1.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/80 text-[#00e5ff] border border-[#00e5ff]/40 text-xs font-bold flex items-center gap-1.5 transition-all"
                  title="Salvar este design no Catálogo de Modelos"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>Salvar Modelo</span>
                </button>
              </div>
            </div>

            {/* Catálogo de Modelos Salvos / Rápidos */}
            <div className="space-y-1.5 text-xs">
              <label className="text-slate-300 font-bold flex items-center gap-1.5">
                <Bookmark className="w-3.5 h-3.5 text-[#c5a059]" />
                <span>Catálogo de Modelos do Gabinete</span>
              </label>
              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                {savedTemplates.map((tpl) => (
                  <button
                    key={tpl.id}
                    type="button"
                    onClick={() => {
                      setPrintConfig(tpl.config);
                      toast.success(`Modelo "${tpl.name}" aplicado!`);
                    }}
                    className={`px-3 py-1.5 rounded-xl border text-[11px] font-bold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                      printConfig.model === tpl.config.model && printConfig.theme === tpl.config.theme
                        ? 'bg-[#c5a059] text-slate-950 border-[#c5a059] font-black'
                        : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500'
                    }`}
                  >
                    <span>{tpl.name}</span>
                    {tpl.id.startsWith('tpl_') && !DEFAULT_TEMPLATES.some((d) => d.id === tpl.id) && (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteTemplate(tpl.id, tpl.name);
                        }}
                        className="text-red-400 hover:text-red-300 ml-1"
                      >
                        ✕
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Seletor do Modelo Físico / Dimensões na Folha A4 */}
            <div className="space-y-1.5 text-xs">
              <label className="text-slate-300 font-bold">1. Formato Físico & Distribuição na Folha A4</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, model: 'prisma_a4_4slots' })}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    printConfig.model === 'prisma_a4_4slots'
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-bold text-[11px]">📑 Prisma Dobrável A4</p>
                  <span className="text-[9px] text-[#c5a059] font-bold block">1 por Folha A4 (4 Abas/Vincos)</span>
                  <span className="text-[8px] text-slate-500">210 x 297 mm • Dobra em V</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, model: 'prisma_a4_2slots' })}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    printConfig.model === 'prisma_a4_2slots'
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-bold text-[11px]">🏷️ Prisma Duplo A4</p>
                  <span className="text-[9px] text-[#c5a059] font-bold block">2 Prismas por Folha A4</span>
                  <span className="text-[8px] text-slate-500">210 x 148 mm cada</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, model: 'cracha_vip_a6' })}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    printConfig.model === 'cracha_vip_a6'
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-bold text-[11px]">🪪 Crachá VIP Vertical (A6)</p>
                  <span className="text-[9px] text-[#00e5ff] font-bold block">4 por Folha A4 (Em Pé)</span>
                  <span className="text-[8px] text-slate-500">105 x 148 mm • Cordão / Tarja</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, model: 'cracha_horizontal' })}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    printConfig.model === 'cracha_horizontal'
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-bold text-[11px]">💳 Crachá Horizontal / Porta-Crachá</p>
                  <span className="text-[9px] text-[#00e5ff] font-bold block">6 por Folha A4 (Deitado)</span>
                  <span className="text-[8px] text-slate-500">105 x 74 mm • Encaixe Plástico</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, model: 'cartao_mesa_luxo' })}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    printConfig.model === 'cartao_mesa_luxo'
                      ? 'bg-[#c5a059]/20 border-[#c5a059] text-white font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <p className="font-bold text-[11px]">📜 Cartão de Assento Luxo</p>
                  <span className="text-[9px] text-purple-400 font-bold block">8 Cartões por Folha A4</span>
                  <span className="text-[8px] text-slate-500">52 x 105 mm • Place Card</span>
                </button>
              </div>
            </div>

            {/* Tema de Fundo & Textura */}
            <div className="space-y-1.5 text-xs">
              <label className="text-slate-300 font-bold">2. Tema Visual, Textura & Plano de Fundo</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, theme: 'clean_ouro' })}
                  className={`p-2 rounded-xl border text-left transition-all ${
                    printConfig.theme === 'clean_ouro'
                      ? 'bg-white text-slate-950 border-[#c5a059] font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <p className="font-bold text-[11px]">⚪ Branco Nobre & Ouro</p>
                  <span className="text-[9px] text-slate-500">Oficial do Cerimonial</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, theme: 'navy_luxo' })}
                  className={`p-2 rounded-xl border text-left transition-all ${
                    printConfig.theme === 'navy_luxo'
                      ? 'bg-[#0b1c3d] text-white border-[#00e5ff] font-bold ring-1 ring-[#00e5ff]'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <p className="font-bold text-[11px]">🔵 Azul Marinho Imperial</p>
                  <span className="text-[9px] text-slate-400">Texto Dourado Escuro</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, theme: 'papel_linho' })}
                  className={`p-2 rounded-xl border text-left transition-all ${
                    printConfig.theme === 'papel_linho'
                      ? 'bg-[#fcfaf2] text-slate-950 border-[#c5a059] font-bold ring-1 ring-[#c5a059]'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  <p className="font-bold text-[11px]">📜 Papel Linho Marfim</p>
                  <span className="text-[9px] text-slate-500">Textura de Diploma</span>
                </button>

                <label className="p-2 rounded-xl border border-dashed border-slate-700 bg-slate-950 hover:border-[#00e5ff] text-slate-400 cursor-pointer flex flex-col justify-center transition-all">
                  <div className="flex items-center gap-1 font-bold text-[11px] text-white">
                    <Upload className="w-3.5 h-3.5 text-[#00e5ff]" />
                    <span>Upload Arte / Croqui</span>
                  </div>
                  <span className="text-[8px] text-slate-500">Subir JPG / PNG</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleUploadBackground}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Gerenciador de Estrelas / Patentes */}
            <div className="space-y-1.5 text-xs">
              <label className="text-slate-300 font-bold flex items-center justify-between">
                <span>3. Gerenciador de Estrelas / Patente Militar</span>
                <span className="text-[10px] text-[#c5a059] font-mono">
                  {getRankStars(previewGuest?.posto_graduacao) || 'Sem Estrelas'}
                </span>
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: 'auto' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === 'auto'
                      ? 'bg-[#c5a059] text-slate-950 font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  Automático
                </button>
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: '4_stars' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === '4_stars'
                      ? 'bg-amber-500 text-slate-950 font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  ★★★★ (4 Estrelas)
                </button>
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: '3_stars' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === '3_stars'
                      ? 'bg-amber-500 text-slate-950 font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  ★★★ (3 Estrelas)
                </button>
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: '2_stars' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === '2_stars'
                      ? 'bg-amber-500 text-slate-950 font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  ★★ (2 Estrelas)
                </button>
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: '1_star' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === '1_star'
                      ? 'bg-amber-500 text-slate-950 font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  ★ (1 Estrela)
                </button>
                <button
                  type="button"
                  onClick={() => setPrintConfig({ ...printConfig, starsOverride: 'none' })}
                  className={`p-1.5 rounded-lg border text-center text-[10px] font-bold ${
                    printConfig.starsOverride === 'none'
                      ? 'bg-slate-800 text-white font-black'
                      : 'bg-slate-950 border-slate-800 text-slate-400'
                  }`}
                >
                  Sem Estrelas
                </button>
              </div>
            </div>

            {/* Brasão Oficial & Posição */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-300 font-bold block mb-1">Brasão Oficial</label>
                <select
                  value={printConfig.logoPreset}
                  onChange={(e) => setPrintConfig({ ...printConfig, logoPreset: e.target.value as any })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                >
                  <option value="cgcfn">⚓ Brasão CGCFN</option>
                  <option value="mb">⚓ Brasão Marinha do Brasil</option>
                  <option value="defesa">🛡️ Ministério da Defesa</option>
                  <option value="presidencia">🏛️ República Federativa</option>
                </select>
              </div>

              <div>
                <label className="text-slate-300 font-bold block mb-1">Moldura / Borda</label>
                <select
                  value={printConfig.borderStyle}
                  onChange={(e) => setPrintConfig({ ...printConfig, borderStyle: e.target.value as any })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                >
                  <option value="filete_duplo_ouro">Filete Duplo Ouro Naval</option>
                  <option value="cantoneira_naval">Cantoneiras Navais</option>
                  <option value="minimalista">Borda Minimalista</option>
                  <option value="sem_borda">Sem Moldura Externa</option>
                </select>
              </div>
            </div>

            {/* Cabeçalhos Textuais */}
            <div className="space-y-2 text-xs">
              <div>
                <label className="text-slate-300 font-bold block mb-1">Linha de Topo (Superior)</label>
                <input
                  type="text"
                  value={printConfig.headerText}
                  onChange={(e) => setPrintConfig({ ...printConfig, headerText: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-slate-300 font-bold block mb-1">Sub-cabeçalho Institucional</label>
                <input
                  type="text"
                  value={printConfig.subHeaderText}
                  onChange={(e) => setPrintConfig({ ...printConfig, subHeaderText: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>
            </div>

            {/* Alternadores de Recursos (Checkboxes) */}
            <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-2.5 text-xs">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="checkbox"
                  checked={printConfig.showQrCode}
                  onChange={(e) => setPrintConfig({ ...printConfig, showQrCode: e.target.checked })}
                  className="rounded border-slate-700 text-[#00e5ff] focus:ring-0"
                />
                <span>Exibir QR Code Oficial de Check-in na Portaria</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="checkbox"
                  checked={printConfig.showRankStars}
                  onChange={(e) => setPrintConfig({ ...printConfig, showRankStars: e.target.checked })}
                  className="rounded border-slate-700 text-[#00e5ff] focus:ring-0"
                />
                <span>Exibir Estrelas Douradas de Oficiais-Generais</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="checkbox"
                  checked={printConfig.showSeatNumber}
                  onChange={(e) => setPrintConfig({ ...printConfig, showSeatNumber: e.target.checked })}
                  className="rounded border-slate-700 text-[#00e5ff] focus:ring-0"
                />
                <span>Exibir Número de Assento (Ex: Cadeira A-1)</span>
              </label>
            </div>

            {/* Ações de Impressão Global */}
            <div className="pt-2 border-t border-slate-800 space-y-2">
              <button
                onClick={handlePrintAll}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-2xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95"
              >
                <Printer className="w-4 h-4" />
                <span>🖨️ Imprimir Todas as Placas do Evento ({convidados.length})</span>
              </button>

              <button
                onClick={() => {
                  convidados.forEach((c) => {
                    if (c.status_placa === 'pendente') handleUpdatePlateStatus(c.id, 'impressa');
                  });
                  toast.success('Todas as placas foram marcadas como impressas!');
                }}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-bold transition-all"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Marcar Todas como Impressas no Banco</span>
              </button>
            </div>
          </div>

          {/* LADO DIREITO/ABAIXO: PREVIEW EM TEMPO REAL & LISTA DE AUTORIDADES DO EVENTO */}
          <div className={`${layoutMode === 'stacked' ? 'w-full' : 'xl:col-span-7'} space-y-5`}>
            {/* PREVIEW EM ALTA RESOLUÇÃO QUE MUDA FISICAMENTE CONFORME O MODELO */}
            <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    <span>Pré-visualização do Layout Físico na Folha A4</span>
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    {printConfig.model === 'prisma_a4_4slots' && '📑 Folha A4 Dobrável em 4 Abas com Vinco Central em V (210 x 297 mm)'}
                    {printConfig.model === 'prisma_a4_2slots' && '🏷️ 2 Prismas Médios por Folha A4 (210 x 148 mm cada)'}
                    {printConfig.model === 'cracha_vip_a6' && '🪪 4 Crachás VIP por Folha A4 com Tarja e Cordão (105 x 148 mm cada)'}
                    {printConfig.model === 'cartao_mesa_luxo' && '📜 8 Cartões de Assento por Folha A4 (52 x 105 mm cada)'}
                    {printConfig.model === 'display_a5_acrilico' && '🖼️ 2 Lâminas A5 para Porta-Prisma de Acrílico (148 x 210 mm)'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {effectiveGuest.id === SAMPLE_PREVIEW_GUEST.id && (
                    <span className="px-2.5 py-1 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold">
                      💡 Modelo de Demonstração
                    </span>
                  )}
                  <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-400 text-[10px] font-mono shrink-0">
                    {effectiveGuest.posto_graduacao || 'Autoridade'} • Assento: {effectiveGuest.assento_id || 'Mesa Livre'}
                  </span>
                </div>
              </div>

              <div className="flex justify-center p-2 sm:p-4 bg-slate-950/80 rounded-3xl border border-slate-800">
                {/* ── MODELO 1: PRISMA DOBRÁVEL A4 (4 ABAS/VINCOS EM V - 1 POR FOLHA A4) ── */}
                {printConfig.model === 'prisma_a4_4slots' && (
                  <div
                    id="printable-jade-area"
                    className={`w-full max-w-[460px] sm:max-w-[500px] aspect-[210/297] p-5 rounded-2xl shadow-2xl flex flex-col justify-between relative overflow-hidden transition-all printable-area ${getThemeBackgroundStyle()} ${getBorderStyle()}`}
                    style={{
                      backgroundImage:
                        printConfig.theme === 'custom_upload' && printConfig.customBackgroundUrl
                          ? `url(${printConfig.customBackgroundUrl})`
                          : undefined,
                    }}
                  >
                    {/* Aba 1: Aba Superior de Encaixe (30mm ~ 10% altura) */}
                    <div className="h-[10%] flex items-center justify-center border-b border-dashed border-slate-400/40 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest no-print">
                      --- 1. ABA DE ENCAIXE SUPERIOR (30 MM) ---
                    </div>

                    {/* Aba 2: Face Traseira Invertida (118mm ~ 38% altura) */}
                    <div className="h-[38%] flex flex-col items-center justify-center border-b border-dashed border-slate-400/40 bg-slate-500/5 rounded-lg text-center transform rotate-180 p-3 space-y-1">
                      <p className="text-[8px] font-mono text-slate-400 no-print">[FACE TRASEIRA INVERTIDA - VISÃO DO PÚBLICO]</p>
                      <h4 className="text-base font-black uppercase tracking-tight">{effectiveGuest.nome}</h4>
                      <p className="text-[10px] font-bold text-[#c5a059]">{effectiveGuest.cargo_funcao || effectiveGuest.posto_graduacao}</p>
                    </div>

                    {/* Vinco Central de Dobra (Linha pontilhada de vinco ~ 4% altura) */}
                    <div className="h-[4%] flex items-center justify-center border-b-2 border-dashed border-[#c5a059] text-[9px] font-mono font-black text-[#c5a059] uppercase tracking-widest no-print">
                      ✂️ --- LINHA CENTRAL DE VINCO & DOBRA EM V --- ✂️
                    </div>

                    {/* Aba 3: Face Frontal Principal (118mm ~ 38% altura) */}
                    <div className="h-[38%] flex flex-col justify-between py-2 px-2 text-center">
                      {/* Topo da Placa: Brasão Oficial + Estrelas + QR Code */}
                      <div className="flex items-center justify-between">
                        <div className="w-10 h-10 rounded-lg bg-slate-100/90 border border-slate-300 flex items-center justify-center text-xl font-black shadow-xs text-[#0a1b3a]">
                          {printConfig.logoPreset === 'cgcfn' ? '⚓' : printConfig.logoPreset === 'defesa' ? '🛡️' : '🏛️'}
                        </div>

                        <div className="text-center flex-1 px-2">
                          <p className="text-[10px] font-black tracking-wider uppercase">{printConfig.headerText}</p>
                          <p className="text-[8px] font-bold opacity-70 uppercase">{printConfig.subHeaderText}</p>
                          {printConfig.showRankStars && getRankStars(effectiveGuest.posto_graduacao) && (
                            <div className="text-amber-500 font-black text-sm tracking-widest mt-0.5">
                              {getRankStars(effectiveGuest.posto_graduacao)}
                            </div>
                          )}
                        </div>

                        {printConfig.showQrCode ? (
                          <div className="w-10 h-10 bg-slate-900 text-white flex flex-col items-center justify-center font-mono text-[7px] p-0.5 rounded shadow-xs">
                            <QrCode className="w-4 h-4 mb-0.5" />
                            <span>PORTARIA</span>
                          </div>
                        ) : (
                          <div className="w-10"></div>
                        )}
                      </div>

                      {/* Miolo: Posto / Nome da Autoridade */}
                      <div className="py-2 border-y-2 border-[#c5a059]/40 text-center space-y-0.5">
                        {effectiveGuest.posto_graduacao && (
                          <p className="text-[11px] font-black text-[#c5a059] tracking-widest uppercase">
                            {effectiveGuest.posto_graduacao}
                          </p>
                        )}
                        <h2 className="text-xl font-black uppercase tracking-tight">
                          {effectiveGuest.nome}
                        </h2>
                        <p className="text-[10px] font-semibold opacity-80">
                          {effectiveGuest.cargo_funcao || 'Autoridade Convidada de Honra'}
                        </p>
                      </div>

                      {/* Rodapé da Placa */}
                      <div className="flex items-center justify-between text-[9px] opacity-70 font-mono pt-1">
                        <span>SOLENIDADE: {currentEvento?.nome || 'GABINETE CGCFN'}</span>
                        {printConfig.showSeatNumber && (
                          <span className="font-bold">ASSENTO: {effectiveGuest.assento_id || 'RESERVADO'}</span>
                        )}
                      </div>
                    </div>

                    {/* Aba 4: Aba de Base de Apoio (30mm ~ 10% altura) */}
                    <div className="h-[10%] flex items-center justify-center border-t border-dashed border-slate-400/40 text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest no-print">
                      --- 4. ABA DE BASE INFERIOR (30 MM) ---
                    </div>
                  </div>
                )}

                {/* ── MODELO 2: PRISMA DUPLO A4 (2 POR FOLHA A4) ── */}
                {printConfig.model === 'prisma_a4_2slots' && (
                  <div
                    id="printable-jade-area"
                    className="w-full max-w-[460px] sm:max-w-[500px] aspect-[210/297] grid grid-cols-1 grid-rows-2 gap-3 p-4 bg-slate-900/50 rounded-2xl border border-slate-800 printable-area"
                  >
                    {[1, 2].map((slot) => (
                      <div
                        key={slot}
                        className={`p-4 rounded-xl shadow-lg flex flex-col justify-between relative transition-all ${getThemeBackgroundStyle()} ${getBorderStyle()}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-2xl">⚓</span>
                          <div className="text-center">
                            <p className="text-[10px] font-black uppercase">{printConfig.headerText}</p>
                            {printConfig.showRankStars && getRankStars(effectiveGuest.posto_graduacao) && (
                              <div className="text-amber-500 font-bold text-xs tracking-widest">
                                {getRankStars(effectiveGuest.posto_graduacao)}
                              </div>
                            )}
                          </div>
                          <span className="text-[8px] font-mono bg-slate-900 text-white p-1 rounded">QR</span>
                        </div>

                        <div className="py-2 border-y border-[#c5a059]/40 text-center">
                          <p className="text-[10px] font-bold text-[#c5a059] uppercase">{effectiveGuest.posto_graduacao}</p>
                          <h3 className="text-lg font-black uppercase">{effectiveGuest.nome}</h3>
                          <p className="text-[10px] opacity-75">{effectiveGuest.cargo_funcao || 'Autoridade'}</p>
                        </div>

                        <div className="flex justify-between text-[9px] font-mono opacity-60">
                          <span>PRISMA {slot}/2 (A4)</span>
                          <span>{effectiveGuest.assento_id || 'MESA'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── MODELO 3: CRACHÁ VIP VERTICAL (A6 - 4 POR FOLHA A4) ── */}
                {printConfig.model === 'cracha_vip_a6' && (
                  <div
                    id="printable-jade-area"
                    className="w-full max-w-[460px] sm:max-w-[500px] aspect-[210/297] grid grid-cols-2 grid-rows-2 gap-3 p-4 bg-slate-900/50 rounded-2xl border border-slate-800 printable-area"
                  >
                    {[1, 2, 3, 4].map((slot) => (
                      <div
                        key={slot}
                        className={`p-3 rounded-xl shadow-md flex flex-col justify-between text-center relative ${getThemeBackgroundStyle()} ${getBorderStyle()}`}
                      >
                        <div className="w-6 h-1.5 mx-auto bg-slate-800 rounded-full border border-slate-600 mb-1 no-print"></div>

                        <div className="py-0.5 px-2 rounded bg-[#c5a059] text-slate-950 font-black text-[8px] uppercase">
                          {effectiveGuest.categoria || 'VIP'}
                        </div>

                        <span className="text-xl my-1">⚓</span>

                        <div className="space-y-0.5">
                          {printConfig.showRankStars && getRankStars(effectiveGuest.posto_graduacao) && (
                            <div className="text-amber-500 font-bold text-[10px]">
                              {getRankStars(effectiveGuest.posto_graduacao)}
                            </div>
                          )}
                          <p className="text-[8px] font-bold text-[#c5a059] uppercase">{effectiveGuest.posto_graduacao}</p>
                          <h3 className="text-xs font-black uppercase leading-tight truncate">{effectiveGuest.nome}</h3>
                          <p className="text-[8px] opacity-75 truncate">{effectiveGuest.cargo_funcao || 'Convidado'}</p>
                        </div>

                        {printConfig.showQrCode && (
                          <div className="p-1 bg-white rounded text-slate-950 inline-block mx-auto">
                            <QrCode className="w-6 h-6 mx-auto" />
                          </div>
                        )}

                        <div className="text-[7px] font-mono opacity-60 border-t pt-0.5">
                          CRACHÁ #{slot} • {effectiveGuest.assento_id || 'PORTARIA'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── MODELO 4: CRACHÁ VIP HORIZONTAL / PORTA-CRACHÁ DEITADO (6 POR FOLHA A4) ── */}
                {printConfig.model === 'cracha_horizontal' && (
                  <div
                    id="printable-jade-area"
                    className="w-full max-w-[460px] sm:max-w-[500px] aspect-[210/297] grid grid-cols-2 grid-rows-3 gap-2.5 p-3.5 bg-slate-900/50 rounded-2xl border border-slate-800 printable-area"
                  >
                    {[1, 2, 3, 4, 5, 6].map((slot) => (
                      <div
                        key={slot}
                        className={`p-2.5 rounded-xl shadow-md flex flex-col justify-between relative ${getThemeBackgroundStyle()} ${getBorderStyle()}`}
                      >
                        <div className="flex items-center justify-between border-b border-[#c5a059]/40 pb-1 mb-1">
                          <span className="text-sm">⚓</span>
                          <span className="px-1.5 py-0.2 rounded bg-[#c5a059] text-slate-950 font-black text-[7px] uppercase">
                            {effectiveGuest.categoria || 'VIP'}
                          </span>
                        </div>

                        <div className="space-y-0.5">
                          <p className="text-[7px] font-bold text-[#c5a059] uppercase">{effectiveGuest.posto_graduacao}</p>
                          <h4 className="text-xs font-black uppercase truncate">{effectiveGuest.nome}</h4>
                          <p className="text-[7px] opacity-75 truncate">{effectiveGuest.cargo_funcao || 'Convidado'}</p>
                        </div>

                        <div className="flex items-center justify-between text-[6px] font-mono opacity-60 border-t pt-1">
                          <span>CARTÃO {slot}/6</span>
                          <span>{effectiveGuest.assento_id || 'PORTARIA'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* ── MODELO 5: CARTÃO DE ASSENTO / PLACE CARD (8 POR FOLHA A4) ── */}
                {printConfig.model === 'cartao_mesa_luxo' && (
                  <div
                    id="printable-jade-area"
                    className="w-full max-w-[460px] sm:max-w-[500px] aspect-[210/297] grid grid-cols-2 grid-rows-4 gap-2 p-3 bg-slate-900/50 rounded-2xl border border-slate-800 printable-area"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((slot) => (
                      <div
                        key={slot}
                        className={`p-2 rounded-lg shadow-sm flex flex-col justify-between text-center relative ${getThemeBackgroundStyle()} ${getBorderStyle()}`}
                      >
                        <span className="text-xs">⚓</span>
                        <div>
                          <p className="text-[8px] font-black uppercase tracking-tight truncate">{effectiveGuest.nome}</p>
                          <p className="text-[7px] text-[#c5a059] font-bold truncate">{effectiveGuest.posto_graduacao || 'Mesa'}</p>
                        </div>
                        <span className="text-[7px] font-mono opacity-50 block">Assento {effectiveGuest.assento_id || slot}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Botões Rápidos da Placa Selecionada */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">Status atual:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                      effectiveGuest.status_placa === 'impressa'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse'
                    }`}
                  >
                    {effectiveGuest.status_placa || 'pendente'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrintSingle}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:from-[#d6b26b] hover:to-[#e5c07b] text-slate-950 text-xs font-black flex items-center gap-1.5 shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
                  >
                    <Printer className="w-4 h-4" />
                    <span>🖨️ Imprimir / Baixar PDF Desta Placa</span>
                  </button>

                  {previewGuest && (
                    <button
                      onClick={() =>
                        handleUpdatePlateStatus(
                          previewGuest.id,
                          previewGuest.status_placa === 'impressa' ? 'pendente' : 'impressa'
                        )
                      }
                      className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-xs shadow-md shadow-emerald-500/20 transition-all hover:scale-105"
                    >
                      <Check className="w-3.5 h-3.5 inline mr-1 font-black" />
                      <span>
                        {previewGuest.status_placa === 'impressa'
                          ? 'Marcar como Pendente'
                          : 'Marcar como Impressa ✅'}
                      </span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* LISTA FILTRÁVEL DE PLACAS DO EVENTO */}
            <div className="p-5 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-black text-white uppercase tracking-wider">
                    Placas do Cerimonial ({filteredConvidados.length})
                  </h3>
                  <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-950 border border-slate-800 text-[10px]">
                    <button
                      onClick={() => setFilterPlateStatus('todos')}
                      className={`px-2 py-0.5 rounded font-bold transition-all ${
                        filterPlateStatus === 'todos' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                      }`}
                    >
                      Todas ({convidados.length})
                    </button>
                    <button
                      onClick={() => setFilterPlateStatus('pendente')}
                      className={`px-2 py-0.5 rounded font-bold transition-all ${
                        filterPlateStatus === 'pendente' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                      }`}
                    >
                      Pendentes
                    </button>
                    <button
                      onClick={() => setFilterPlateStatus('impressa')}
                      className={`px-2 py-0.5 rounded font-bold transition-all ${
                        filterPlateStatus === 'impressa' ? 'bg-[#c5a059] text-slate-950 font-black' : 'text-slate-400'
                      }`}
                    >
                      Impressas
                    </button>
                  </div>
                </div>

                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    placeholder="Filtrar por nome..."
                    value={searchGuest}
                    onChange={(e) => setSearchGuest(e.target.value)}
                    className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
                  />
                </div>
              </div>

              {/* Grid de Miniaturas de Placas para Seleção e Impressão Rápida */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-96 overflow-y-auto pr-1">
                {filteredConvidados.map((conv) => {
                  const isCurrent = previewGuest?.id === conv.id;

                  return (
                    <div
                      key={conv.id}
                      onClick={() => setPreviewGuest(conv)}
                      className={`p-3 rounded-2xl border cursor-pointer transition-all flex items-center justify-between gap-3 ${
                        isCurrent
                          ? 'bg-[#c5a059]/15 border-[#c5a059] shadow-md shadow-[#c5a059]/10'
                          : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="space-y-0.5 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <p className="text-xs font-bold text-white truncate">{conv.nome}</p>
                          {conv.assento_id && (
                            <span className="px-1.5 py-0.2 rounded bg-cyan-500/20 text-[#00e5ff] text-[9px] font-black">
                              {conv.assento_id}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-400 truncate">
                          {conv.posto_graduacao || conv.cargo_funcao || 'Convidado de Honra'}
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            conv.status_placa === 'impressa' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
                          }`}
                        />
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUpdatePlateStatus(
                              conv.id,
                              conv.status_placa === 'impressa' ? 'pendente' : 'impressa'
                            );
                          }}
                          className={`p-1 rounded-lg text-xs ${
                            conv.status_placa === 'impressa'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-slate-800 text-slate-400 hover:text-white'
                          }`}
                          title="Alternar Status de Impressão"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 2: MAPEAMENTO DO AUDITÓRIO & PALCO ── */}
      {activeTab === 'mapa' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Palco & Grid de Cadeiras (8 Colunas) */}
          <div className="lg:col-span-8 p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-black text-white flex items-center gap-2">
                  <Armchair className="w-4 h-4 text-[#00e5ff]" />
                  <span>Dispositivo de Assentos do Palco & Auditório</span>
                </h2>
                <p className="text-xs text-slate-400">
                  Clique em um assento para alocar ou desalocar autoridades do evento.
                </p>
              </div>
            </div>

            {/* Representação do Palco de Honra */}
            <div className="p-3 rounded-2xl bg-gradient-to-r from-cyan-950/60 via-slate-900 to-cyan-950/60 border border-[#00e5ff]/30 text-center shadow-md">
              <span className="text-xs font-black text-[#00e5ff] uppercase tracking-widest">
                ⚓ PALCO DE HONRA / DISPOSITIVO DE AUTORIDADES ⚓
              </span>
            </div>

            {/* Grid de Fileiras A, B, C, D, E */}
            <div className="space-y-3.5 py-2">
              {ROWS.map((row) => (
                <div key={row} className="flex items-center gap-2">
                  <span className="w-6 text-xs font-black text-[#c5a059] text-center">{row}</span>
                  <div className="grid grid-cols-8 gap-2 flex-1">
                    {COLS.map((col) => {
                      const seatId = `${row}-${col}`;
                      const occupant = getGuestAtSeat(seatId);
                      const isSelected = selectedSeat === seatId;

                      return (
                        <button
                          key={seatId}
                          type="button"
                          onClick={() => handleSeatClick(seatId)}
                          className={`p-2.5 rounded-xl border text-center transition-all relative group flex flex-col items-center justify-center min-h-[52px] ${
                            isSelected
                              ? 'bg-[#00e5ff] text-slate-950 border-[#00e5ff] shadow-lg shadow-[#00e5ff]/30 font-black'
                              : occupant
                              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300 hover:border-emerald-400'
                              : 'bg-slate-900/80 border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-300'
                          }`}
                        >
                          <Armchair className="w-3.5 h-3.5 mb-0.5" />
                          <span className="text-[10px] font-bold">{seatId}</span>
                          {occupant && (
                            <span className="text-[8px] truncate max-w-[50px] font-medium block">
                              {occupant.nome.split(' ')[0]}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            {/* Painel do Assento Selecionado */}
            {selectedSeat && (
              <div className="p-4 rounded-2xl bg-slate-900 border border-[#00e5ff]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-in fade-in duration-200">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-[#00e5ff]/20 text-[#00e5ff] font-black text-xs">
                      Assento {selectedSeat}
                    </span>
                    {getGuestAtSeat(selectedSeat) && (
                      <span className="text-xs font-bold text-white">
                        Ocupado por: <strong>{getGuestAtSeat(selectedSeat)?.nome}</strong>
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {getGuestAtSeat(selectedSeat)
                      ? 'Deseja desalocar esta autoridade ou visualizar sua placa de mesa?'
                      : 'Selecione uma autoridade no painel lateral direito para alocar nesta cadeira.'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {getGuestAtSeat(selectedSeat) && (
                    <>
                      <button
                        onClick={() => {
                          setPreviewGuest(getGuestAtSeat(selectedSeat)!);
                          setActiveTab('design');
                        }}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 text-xs font-bold text-white hover:bg-slate-700"
                      >
                        <Eye className="w-3.5 h-3.5 inline mr-1" />
                        Ver Placa
                      </button>
                      <button
                        onClick={() => deallocateSeat(getGuestAtSeat(selectedSeat)!.id)}
                        className="px-3 py-1.5 rounded-xl bg-red-500/20 text-red-300 border border-red-500/40 text-xs font-bold"
                      >
                        Desalocar
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Banco Lateral de Autoridades (4 Colunas) */}
          <div className="lg:col-span-4 p-5 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
            <div>
              <h2 className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-4 h-4" />
                <span>Autoridades sem Assento ({convidados.filter((c) => !c.assento_id).length})</span>
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Clique em uma autoridade com uma cadeira selecionada para vinculá-la.
              </p>
            </div>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {convidados
                .filter((c) => !c.assento_id)
                .map((guest) => (
                  <div
                    key={guest.id}
                    className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-[#c5a059]/40 transition-all flex items-center justify-between gap-2"
                  >
                    <div className="space-y-0.5 min-w-0">
                      <p className="text-xs font-bold text-white truncate">{guest.nome}</p>
                      <p className="text-[10px] text-[#c5a059] truncate">{guest.cargo_funcao}</p>
                      <span className="inline-block px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[9px]">
                        {guest.categoria}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {selectedSeat && (
                        <button
                          onClick={() => allocateGuestToSeat(guest.id, selectedSeat)}
                          className="px-2.5 py-1 rounded-lg bg-[#00e5ff] text-slate-950 font-black text-[11px] hover:bg-[#33ebff]"
                        >
                          Alocar {selectedSeat}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* ── ABA 3: GESTÃO DE CONVIDADOS & ACOMPANHANTES (CRUD COMPLETO) ── */}
      {activeTab === 'convidados' && (
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-black text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-[#c5a059]" />
                <span>Gestão de Autoridades & Convidados do Evento</span>
              </h2>
              <p className="text-xs text-slate-400">
                Inclusão, edição, exclusão e visualização de placas vinculadas a: <strong className="text-[#c5a059]">{currentEvento?.nome}</strong>.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setNovoConvidadoModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/20"
              >
                <Plus className="w-4 h-4" />
                <span>Adicionar Autoridade</span>
              </button>
            </div>
          </div>

          {/* Campo de Busca Rápida de Convidados */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filtrar autoridade por nome, cargo ou posto/graduação..."
              value={searchGuestInList}
              onChange={(e) => setSearchGuestInList(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          {/* Lista com Ações CRUD */}
          <div className="rounded-2xl border border-slate-800 overflow-hidden divide-y divide-slate-800/80">
            {convidados
              .filter((c) => {
                if (!searchGuestInList.trim()) return true;
                const q = searchGuestInList.toLowerCase();
                return (
                  c.nome.toLowerCase().includes(q) ||
                  (c.cargo_funcao && c.cargo_funcao.toLowerCase().includes(q)) ||
                  (c.posto_graduacao && c.posto_graduacao.toLowerCase().includes(q))
                );
              })
              .map((conv) => (
                <div
                  key={conv.id}
                  className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-white text-sm">{conv.nome}</span>
                      {conv.posto_graduacao && (
                        <span className="px-2 py-0.2 rounded bg-slate-900 border border-slate-700 text-[#c5a059] font-mono text-[10px]">
                          {conv.posto_graduacao}
                        </span>
                      )}
                      <span className="px-2 py-0.2 rounded bg-cyan-500/20 text-cyan-300 text-[9px] font-black uppercase">
                        {conv.categoria}
                      </span>
                      {conv.assento_id ? (
                        <span className="px-2 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[9px] font-black uppercase border border-emerald-500/30">
                          Assento {conv.assento_id}
                        </span>
                      ) : (
                        <span className="px-2 py-0.2 rounded bg-amber-500/15 text-amber-400 text-[9px] font-semibold">
                          Sem Assento
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {conv.cargo_funcao || 'Sem cargo informado'}
                      {conv.max_acompanhantes > 0 && ` • ${conv.max_acompanhantes} acompanhante(s)`}
                    </p>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => {
                        setPreviewGuest(conv);
                        setActiveTab('design');
                      }}
                      className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-bold hover:bg-slate-800 flex items-center gap-1"
                      title="Ver e Imprimir Placa JADE"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Ver Placa</span>
                    </button>

                    <button
                      onClick={() => {
                        setEditingGuest(conv);
                        setEditConvidadoModal(true);
                      }}
                      className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-amber-300 text-xs font-bold hover:bg-slate-800 flex items-center gap-1"
                      title="Editar Informações da Autoridade"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>Editar</span>
                    </button>

                    <button
                      onClick={() => handleExcluirConvidado(conv.id, conv.nome)}
                      className="p-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-colors"
                      title="Excluir Autoridade do Evento"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ── MODAL: CADASTRAR CONVIDADO E ACOMPANHANTES ── */}
      {novoConvidadoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white">➕ Cadastrar Autoridade no Evento ({currentEvento?.nome})</h3>
              <button onClick={() => setNovoConvidadoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSalvarConvidado} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Completo / Guerra *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: OLSEN"
                  value={novoConvidado.nome}
                  onChange={(e) => setNovoConvidado({ ...novoConvidado, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Posto / Graduação</label>
                  <select
                    value={novoConvidado.posto_graduacao}
                    onChange={(e) => setNovoConvidado({ ...novoConvidado, posto_graduacao: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="AE - Almirante de Esquadra">AE - Almirante de Esquadra</option>
                    <option value="VA - Vice-Almirante">VA - Vice-Almirante</option>
                    <option value="CA - Contra-Almirante">CA - Contra-Almirante</option>
                    <option value="CMG - Capitão de Mar e Guerra">CMG - Capitão de Mar e Guerra</option>
                    <option value="CF - Capitão de Fragata">CF - Capitão de Fragata</option>
                    <option value="CC - Capitão de Corveta">CC - Capitão de Corveta</option>
                    <option value="CT - Capitão-Tenente">CT - Capitão-Tenente</option>
                    <option value="Desembargador(a)">🏛️ Desembargador(a)</option>
                    <option value="Senador(a) / Deputado(a)">🏛️ Senador(a) / Deputado(a)</option>
                    <option value="Senhor / Senhora">👤 Senhor / Senhora</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Categoria</label>
                  <select
                    value={novoConvidado.categoria}
                    onChange={(e) => setNovoConvidado({ ...novoConvidado, categoria: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="Autoridade Militar">Autoridade Militar</option>
                    <option value="Autoridade Civil">Autoridade Civil</option>
                    <option value="VIP">VIP</option>
                    <option value="Imprensa">Imprensa</option>
                    <option value="Geral">Geral</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Cargo / Função</label>
                <input
                  type="text"
                  placeholder="Ex: Comandante da Marinha, Presidente Petrobras..."
                  value={novoConvidado.cargo_funcao}
                  onChange={(e) => setNovoConvidado({ ...novoConvidado, cargo_funcao: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">
                  Número de Acompanhantes (Gera placas vinculadas automaticamente)
                </label>
                <input
                  type="number"
                  min="0"
                  max="6"
                  value={novoConvidado.max_acompanhantes}
                  onChange={(e) => setNovoConvidado({ ...novoConvidado, max_acompanhantes: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setNovoConvidadoModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black shadow-md shadow-[#c5a059]/25"
                >
                  Salvar Autoridade & Placas
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: EDITAR CONVIDADO EXISTENTE ── */}
      {editConvidadoModal && editingGuest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-amber-500/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-amber-400" />
                <span>Editar Autoridade #{editingGuest.id}</span>
              </h3>
              <button onClick={() => setEditConvidadoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleAtualizarConvidado} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Completo / Guerra *</label>
                <input
                  type="text"
                  required
                  value={editingGuest.nome}
                  onChange={(e) => setEditingGuest({ ...editingGuest, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Posto / Graduação</label>
                  <select
                    value={editingGuest.posto_graduacao || ''}
                    onChange={(e) => setEditingGuest({ ...editingGuest, posto_graduacao: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="AE - Almirante de Esquadra">AE - Almirante de Esquadra</option>
                    <option value="VA - Vice-Almirante">VA - Vice-Almirante</option>
                    <option value="CA - Contra-Almirante">CA - Contra-Almirante</option>
                    <option value="CMG - Capitão de Mar e Guerra">CMG - Capitão de Mar e Guerra</option>
                    <option value="CF - Capitão de Fragata">CF - Capitão de Fragata</option>
                    <option value="CC - Capitão de Corveta">CC - Capitão de Corveta</option>
                    <option value="CT - Capitão-Tenente">CT - Capitão-Tenente</option>
                    <option value="Desembargador(a)">🏛️ Desembargador(a)</option>
                    <option value="Senador(a) / Deputado(a)">🏛️ Senador(a) / Deputado(a)</option>
                    <option value="Senhor / Senhora">👤 Senhor / Senhora</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Categoria</label>
                  <select
                    value={editingGuest.categoria || 'Autoridade Militar'}
                    onChange={(e) => setEditingGuest({ ...editingGuest, categoria: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="Autoridade Militar">Autoridade Militar</option>
                    <option value="Autoridade Civil">Autoridade Civil</option>
                    <option value="VIP">VIP</option>
                    <option value="Imprensa">Imprensa</option>
                    <option value="Geral">Geral</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Cargo / Função</label>
                <input
                  type="text"
                  value={editingGuest.cargo_funcao || ''}
                  onChange={(e) => setEditingGuest({ ...editingGuest, cargo_funcao: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditConvidadoModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black shadow-md"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CRIAR NOVO EVENTO / CERIMÔNIA ── */}
      {novoEventoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#00e5ff]" />
                <span>➕ Criar Novo Evento / Cerimônia JADE</span>
              </h3>
              <button onClick={() => setNovoEventoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSalvarNovoEvento} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Oficial da Cerimônia / Evento *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: PASSAGEM DE COMANDO DO CGCFN"
                  value={novoEvento.nome}
                  onChange={(e) => setNovoEvento({ ...novoEvento, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#00e5ff]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Data do Evento *</label>
                  <input
                    type="date"
                    required
                    value={novoEvento.data_evento}
                    onChange={(e) => setNovoEvento({ ...novoEvento, data_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Tipo de Evento</label>
                  <select
                    value={novoEvento.tipo_evento}
                    onChange={(e) => setNovoEvento({ ...novoEvento, tipo_evento: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="cerimonia">Cerimônia Militar</option>
                    <option value="almoco">Almoço / Jantar Oficial</option>
                    <option value="visita">Visita de Autoridade</option>
                    <option value="seminario">Seminário / Simpósio</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Local da Cerimônia</label>
                <input
                  type="text"
                  placeholder="Ex: Salão Nobre do CGCFN / Fortaleza de São José"
                  value={novoEvento.local_evento}
                  onChange={(e) => setNovoEvento({ ...novoEvento, local_evento: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setNovoEventoModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black shadow-md shadow-[#00e5ff]/20"
                >
                  Criar Evento
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: SALVAR DESIGN ATUAL NO CATÁLOGO DE MODELOS ── */}
      {showSaveTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border border-[#c5a059]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Bookmark className="w-4 h-4 text-[#c5a059]" />
                <span>Salvar Design no Catálogo de Modelos</span>
              </h3>
              <button onClick={() => setShowSaveTemplateModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome do Modelo Personalizado *</label>
                <input
                  type="text"
                  placeholder="Ex: Prisma Almoço de Oficiais 2026"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <p className="text-[11px] text-slate-400">
                Este modelo salvará o formato ({printConfig.model}), tema ({printConfig.theme}), borda, estrelas e cabeçalhos atuais para você reutilizar em qualquer cerimônia futura!
              </p>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowSaveTemplateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={handleSaveTemplate}
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black shadow-md shadow-[#c5a059]/25"
                >
                  Salvar no Catálogo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* ── MODAL: GERENCIAR TODOS OS EVENTOS / CERIMÔNIAS ── */}
      {gerenciarEventosModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-2xl p-6 rounded-3xl bg-[#0b1222] border border-[#00e5ff]/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-black text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-[#00e5ff]" />
                  <span>Gerenciador de Cerimônias & Eventos do SisGAB ({eventos.length})</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  Edite dados, exclua cerimônias antigas ou selecione o evento ativo.
                </p>
              </div>
              <button onClick={() => setGerenciarEventosModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            {/* Busca Rápida de Eventos */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filtrar cerimônia por nome, data ou local..."
                value={searchEventoQuery}
                onChange={(e) => setSearchEventoQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff]"
              />
            </div>

            {/* Lista de Eventos com Ações */}
            <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {eventos
                .filter((ev) => {
                  if (!searchEventoQuery.trim()) return true;
                  const q = searchEventoQuery.toLowerCase();
                  return (
                    ev.nome.toLowerCase().includes(q) ||
                    (ev.data_evento && ev.data_evento.includes(q)) ||
                    (ev.local && ev.local.toLowerCase().includes(q))
                  );
                })
                .map((ev) => {
                  const isActive = ev.id === selectedEventoId;

                  return (
                    <div
                      key={ev.id}
                      className={`p-3.5 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isActive
                          ? 'bg-[#c5a059]/15 border-[#c5a059]'
                          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-white text-xs truncate uppercase">{ev.nome}</h4>
                          {isActive && (
                            <span className="px-2 py-0.2 rounded bg-[#c5a059] text-slate-950 font-black text-[9px] uppercase">
                              Ativo
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 flex items-center gap-2">
                          <span className="text-[#00e5ff] font-bold">📅 {ev.data_evento || 'Sem data'}</span>
                          <span>•</span>
                          <span>📍 {ev.local || 'Salão Nobre'}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        {!isActive && (
                          <button
                            onClick={() => {
                              setSelectedEventoId(ev.id);
                              toast.success(`Evento "${ev.nome}" selecionado!`);
                            }}
                            className="px-3 py-1.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/80 text-[#00e5ff] border border-[#00e5ff]/30 text-xs font-bold transition-all"
                          >
                            Selecionar
                          </button>
                        )}

                        <button
                          onClick={() => {
                            setEditingEvento(ev);
                            setEditEventoModal(true);
                          }}
                          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-bold flex items-center gap-1 border border-slate-700"
                          title="Editar Cerimônia"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                          <span>Editar</span>
                        </button>

                        <button
                          onClick={() => handleExcluirEvento(ev.id, ev.nome)}
                          className="p-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all"
                          title="Excluir Cerimônia e Convidados"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  setGerenciarEventosModal(false);
                  setNovoEventoModal(true);
                }}
                className="px-4 py-2 rounded-xl bg-[#00e5ff] hover:bg-[#33ebff] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>+ Criar Novo Evento</span>
              </button>

              <button
                onClick={() => setGerenciarEventosModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 hover:text-white font-bold text-xs"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: EDITAR EVENTO / CERIMÔNIA EXISTENTE ── */}
      {editEventoModal && editingEvento && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-lg p-6 rounded-3xl bg-[#0b1222] border border-amber-500/40 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-black text-white flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-amber-400" />
                <span>Editar Dados do Evento #{editingEvento.id}</span>
              </h3>
              <button onClick={() => setEditEventoModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleAtualizarEvento} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Nome Oficial da Cerimônia *</label>
                <input
                  type="text"
                  required
                  value={editingEvento.nome}
                  onChange={(e) => setEditingEvento({ ...editingEvento, nome: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-bold mb-1">Data da Cerimônia *</label>
                  <input
                    type="date"
                    required
                    value={editingEvento.data_evento}
                    onChange={(e) => setEditingEvento({ ...editingEvento, data_evento: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-bold mb-1">Disposição de Cadeiras</label>
                  <select
                    value={editingEvento.tipo_layout || 'auditorio'}
                    onChange={(e) => setEditingEvento({ ...editingEvento, tipo_layout: e.target.value as any })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                  >
                    <option value="auditorio">Auditório / Fileiras</option>
                    <option value="mesa_u">Mesa em U / Reunião</option>
                    <option value="banquete">Banquete / Mesas Redondas</option>
                    <option value="teatro">Teatro</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Local da Cerimônia</label>
                <input
                  type="text"
                  value={editingEvento.local || ''}
                  onChange={(e) => setEditingEvento({ ...editingEvento, local: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setEditEventoModal(false);
                    handleExcluirEvento(editingEvento.id, editingEvento.nome);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/30 text-red-400 border border-red-500/40 text-xs font-bold flex items-center gap-1.5 transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Excluir Evento</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setEditEventoModal(false)}
                    className="px-4 py-2 rounded-xl bg-slate-900 text-slate-400 font-bold"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black shadow-md"
                  >
                    Salvar Alterações
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* ── MODAL: CONFIRMAÇÃO DE EXCLUSÃO DEFINITIVA DO EVENTO ── */}
      {deleteConfirmModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-3xl bg-[#0b1222] border border-red-500/50 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-red-400">
              <div className="p-3 rounded-2xl bg-red-500/10 border border-red-500/30">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-black text-white">Excluir Cerimônia / Evento</h3>
                <p className="text-xs text-red-300">Esta ação é permanente e irreversível.</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 leading-relaxed">
              Deseja realmente excluir o evento <strong className="text-white font-bold">"{deleteConfirmModal.nome}"</strong>? Todas as presenças, autoridades e assentos alocados nesta cerimônia serão apagados do banco.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setDeleteConfirmModal(null)}
                className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-bold text-xs"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => executeExcluirEvento(deleteConfirmModal.id, deleteConfirmModal.nome)}
                className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-black text-xs shadow-lg shadow-red-600/30 transition-all flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isDeleting ? 'Excluindo...' : 'Sim, Excluir Definitivamente'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
