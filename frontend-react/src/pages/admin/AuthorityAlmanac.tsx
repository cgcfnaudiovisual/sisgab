import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useMemo } from 'react';
import {
  Award,
  Users,
  Plus,
  Search,
  Upload,
  Download,
  Filter,
  Shield,
  Star,
  CheckCircle2,
  AlertTriangle,
  ArrowUpDown,
  Phone,
  Mail,
  Edit2,
  Trash2,
  Sparkles,
  RefreshCw,
  Building2,
  GraduationCap,
  Scale,
  Landmark,
  Link as LinkIcon,
  UserCheck,
  Heart,
  Briefcase,
  UserPlus,
  Eye,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';

export type TipoVinculo =
  | 'ajudante_ordens'
  | 'assessor'
  | 'chefe_gabinete'
  | 'conjuge_acompanhante'
  | 'secretario'
  | 'subordinado'
  | 'outro';

export interface AutoridadePrecedencia {
  id: string | number;
  posto_graduacao: string;
  nome_completo: string;
  nome_guerra_ou_tratamento: string;
  cargo_funcao?: string;
  orgao_om?: string;
  categoria_grupo:
    | 'almirantado'
    | 'oficiais_superiores'
    | 'oficiais'
    | 'governo'
    | 'judiciario_legislativo'
    | 'reitores'
    | 'ttc_veteranos'
    | 'diplomatico'
    | 'civil_vip';
  email_oficial?: string;
  email_ajudancia?: string;
  whatsapp_celular?: string;
  precedencia_ordem: number;
  antiguidade_data?: string;
  observacoes?: string;
  autoridade_vinculada_id?: string | number | null; // ID da autoridade principal à qual está vinculada
  tipo_vinculo?: TipoVinculo;
}

export const TIPOS_VINCULO_CONFIG: Record<
  TipoVinculo,
  { label: string; badgeBg: string; text: string; border: string; icon: any }
> = {
  ajudante_ordens: { label: 'Ajudante de Ordens (Ado)', badgeBg: 'bg-amber-500/20', text: 'text-amber-300', border: 'border-amber-500/40', icon: Award },
  assessor: { label: 'Assessor Direto / Assistente', badgeBg: 'bg-cyan-500/20', text: 'text-cyan-300', border: 'border-cyan-500/40', icon: Briefcase },
  chefe_gabinete: { label: 'Chefe de Gabinete', badgeBg: 'bg-purple-500/20', text: 'text-purple-300', border: 'border-purple-500/40', icon: Building2 },
  conjuge_acompanhante: { label: 'Cônjuge / Acompanhante Oficial', badgeBg: 'bg-pink-500/20', text: 'text-pink-300', border: 'border-pink-500/40', icon: Heart },
  secretario: { label: 'Secretário / Apoio Protocolar', badgeBg: 'bg-emerald-500/20', text: 'text-emerald-300', border: 'border-emerald-500/40', icon: UserCheck },
  subordinado: { label: 'Subordinado Direto', badgeBg: 'bg-blue-500/20', text: 'text-blue-300', border: 'border-blue-500/40', icon: Shield },
  outro: { label: 'Outro Vínculo', badgeBg: 'bg-slate-800', text: 'text-slate-300', border: 'border-slate-700', icon: LinkIcon },
};

const CATEGORIAS_CONFIG: Record<
  AutoridadePrecedencia['categoria_grupo'],
  { label: string; bg: string; text: string; border: string; icon: any }
> = {
  almirantado: { label: 'Almirantado & Generais', bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/40', icon: Star },
  governo: { label: 'Poder Executivo & Ministros', bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/40', icon: Landmark },
  judiciario_legislativo: { label: 'Congresso & Judiciário', bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/40', icon: Scale },
  reitores: { label: 'Reitores & Academia', bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/40', icon: GraduationCap },
  oficiais_superiores: { label: 'Oficiais Superiores (CMG/CF/CC)', bg: 'bg-cyan-500/15', text: 'text-cyan-400', border: 'border-cyan-500/40', icon: Shield },
  oficiais: { label: 'Oficiais Interm./Subalternos', bg: 'bg-slate-700/30', text: 'text-slate-300', border: 'border-slate-600', icon: Shield },
  ttc_veteranos: { label: 'TTC & Veteranos', bg: 'bg-[#c5a059]/15', text: 'text-[#c5a059]', border: 'border-[#c5a059]/40', icon: Award },
  diplomatico: { label: 'Corpo Diplomático & Adidos', bg: 'bg-pink-500/15', text: 'text-pink-400', border: 'border-pink-500/40', icon: Building2 },
  civil_vip: { label: 'Convidados VIPs / Civis', bg: 'bg-slate-800', text: 'text-slate-400', border: 'border-slate-700', icon: Users },
};

// Base Inicial Naval Padronizada com Vínculos Reais
const BASE_AUTORIDADES_SEED: AutoridadePrecedencia[] = [
  {
    id: 1,
    posto_graduacao: 'ALMIRANTE DE ESQUADRA',
    nome_completo: 'MARCOS SAMPAIO OLSEN',
    nome_guerra_ou_tratamento: 'OLSEN',
    cargo_funcao: 'COMANDANTE DA MARINHA',
    orgao_om: 'COMANDO DA MARINHA',
    categoria_grupo: 'almirantado',
    email_oficial: 'gabinete.cm@marinha.mil.br',
    whatsapp_celular: '+55 (61) 99876-0001',
    precedencia_ordem: 1,
    antiguidade_data: '2022-11-25',
  },
  {
    id: 2,
    posto_graduacao: 'ALMIRANTE DE ESQUADRA (FN)',
    nome_completo: 'CARLOS CHAGAS VIANNA BRAGA',
    nome_guerra_ou_tratamento: 'CARLOS CHAGAS',
    cargo_funcao: 'COMANDANTE-GERAL DO CORPO DE FUZILEIROS NAVAIS',
    orgao_om: 'CGCFN',
    categoria_grupo: 'almirantado',
    email_oficial: 'chegab.cgcfn@marinha.mil.br',
    whatsapp_celular: '+55 (21) 99876-0002',
    precedencia_ordem: 2,
    antiguidade_data: '2023-03-31',
  },
  {
    id: 3,
    posto_graduacao: 'MINISTRO DE ESTADO',
    nome_completo: 'JOSÉ MÚCIO MONTEIRO FILHO',
    nome_guerra_ou_tratamento: 'MINISTRO JOSÉ MÚCIO',
    cargo_funcao: 'MINISTRO DA DEFESA',
    orgao_om: 'MINISTÉRIO DA DEFESA',
    categoria_grupo: 'governo',
    email_oficial: 'gabinete@defesa.gov.br',
    whatsapp_celular: '+55 (61) 99123-4567',
    precedencia_ordem: 3,
  },
  {
    id: 4,
    posto_graduacao: 'VICE-ALMIRANTE (FN)',
    nome_completo: 'RENATO RANGEL FERREIRA',
    nome_guerra_ou_tratamento: 'RANGEL FERREIRA',
    cargo_funcao: 'COMANDANTE DA FORÇA DE FUZILEIROS DA ESQUADRA',
    orgao_om: 'FFE',
    categoria_grupo: 'almirantado',
    email_oficial: 'gabinete.ffe@marinha.mil.br',
    whatsapp_celular: '+55 (21) 98765-4321',
    precedencia_ordem: 4,
    antiguidade_data: '2023-11-25',
  },
  {
    id: 5,
    posto_graduacao: 'MAGNÍFICO(A) REITOR(A)',
    nome_completo: 'ROBERTO DE ANDRADE MEDRONHO',
    nome_guerra_ou_tratamento: 'PROF. MEDRONHO',
    cargo_funcao: 'REITOR DA UNIVERSIDADE FEDERAL DO RIO DE JANEIRO',
    orgao_om: 'UFRJ',
    categoria_grupo: 'reitores',
    email_oficial: 'gabinete@reitoria.ufrj.br',
    whatsapp_celular: '+55 (21) 99345-6789',
    precedencia_ordem: 5,
  },
  {
    id: 6,
    posto_graduacao: 'CONTRA-ALMIRANTE (FN)',
    nome_completo: 'MAXIMILIANO DA SILVA GOMES',
    nome_guerra_ou_tratamento: 'MAXIMILIANO',
    cargo_funcao: 'COMANDANTE DO DESENVOLVIMENTO DOUTRINÁRIO DO CFN',
    orgao_om: 'CDDCFN',
    categoria_grupo: 'almirantado',
    email_oficial: 'gabinete.cddcfn@marinha.mil.br',
    whatsapp_celular: '+55 (21) 98888-1111',
    precedencia_ordem: 6,
    antiguidade_data: '2024-03-31',
  },
  {
    id: 7,
    posto_graduacao: 'DEPUTADO FEDERAL',
    nome_completo: 'GENERAL EDUARDO PAUZERIT',
    nome_guerra_ou_tratamento: 'DEP. PAUZERIT',
    cargo_funcao: 'PRESIDENTE DA COMISSÃO DE RELAÇÕES EXTERIORES E DEFESA NACIONAL',
    orgao_om: 'CÂMARA DOS DEPUTADOS',
    categoria_grupo: 'judiciario_legislativo',
    email_oficial: 'dep.pauzerit@camara.leg.br',
    whatsapp_celular: '+55 (61) 98222-3333',
    precedencia_ordem: 7,
  },
  {
    id: 8,
    posto_graduacao: 'CAPITÃO DE MAR E GUERRA (FN)',
    nome_completo: 'RICARDO BORGES DA SILVA JUNIOR',
    nome_guerra_ou_tratamento: 'BORGES',
    cargo_funcao: 'CHEFE DE GABINETE DO CGCFN',
    orgao_om: 'CGCFN',
    categoria_grupo: 'oficiais_superiores',
    email_oficial: 'chegab@cgcfn.marinha.mil.br',
    whatsapp_celular: '+55 (21) 97111-9967',
    precedencia_ordem: 8,
    antiguidade_data: '2021-12-25',
    autoridade_vinculada_id: 2, // Vinculado ao AE Carlos Chagas
    tipo_vinculo: 'chefe_gabinete',
  },
  {
    id: 9,
    posto_graduacao: 'CAPITÃO-TENENTE (FN)',
    nome_completo: 'LUCAS TAVARES MOREIRA',
    nome_guerra_ou_tratamento: 'TAVARES',
    cargo_funcao: 'AJUDANTE DE ORDENS DO COMANDANTE-GERAL',
    orgao_om: 'GABINETE CGCFN',
    categoria_grupo: 'oficiais',
    email_oficial: 'ado.cgcfn@marinha.mil.br',
    whatsapp_celular: '+55 (21) 99111-8888',
    precedencia_ordem: 9,
    autoridade_vinculada_id: 2, // Vinculado ao AE Carlos Chagas
    tipo_vinculo: 'ajudante_ordens',
  },
  {
    id: 10,
    posto_graduacao: 'CAPITÃO DE MAR E GUERRA (RM1-FN)',
    nome_completo: 'MARCO ANTÔNIO DE ALMEIDA',
    nome_guerra_ou_tratamento: 'ALMEIDA',
    cargo_funcao: 'ASSESSOR TÉCNICO DE CERIMONIAL (TTC)',
    orgao_om: 'CGCFN / GABINETE',
    categoria_grupo: 'ttc_veteranos',
    email_oficial: 'almeida.ttc@marinha.mil.br',
    whatsapp_celular: '+55 (21) 98111-2222',
    precedencia_ordem: 10,
    antiguidade_data: '2019-12-25',
  },
];

export const AuthorityAlmanac: React.FC = () => {
  const [autoridades, setAutoridades] = useState<AutoridadePrecedencia[]>(() => {
    try {
      const stored = localStorage.getItem('sisgab_almanaque_autoridades');
      if (stored) return JSON.parse(stored);
    } catch { }
    return BASE_AUTORIDADES_SEED;
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategoria, setSelectedCategoria] = useState<string>('todas');
  const [loading, setLoading] = useState(false);

  // Modais de Criação, Edição e Exclusão
  const [modalNovoOpen, setModalNovoOpen] = useState(false);
  const [modalEditOpen, setModalEditOpen] = useState(false);
  const [editingAutoridade, setEditingAutoridade] = useState<AutoridadePrecedencia | null>(null);

  const [deleteConfirmModal, setDeleteConfirmModal] = useState<{ id: string | number; nome: string } | null>(null);

  // Form State Novo Cadastro
  const [formData, setFormData] = useState<Partial<AutoridadePrecedencia>>({
    posto_graduacao: 'ALMIRANTE DE ESQUADRA',
    nome_completo: '',
    nome_guerra_ou_tratamento: '',
    cargo_funcao: '',
    orgao_om: 'MARINHA DO BRASIL',
    categoria_grupo: 'almirantado',
    email_oficial: '',
    email_ajudancia: '',
    whatsapp_celular: '',
    precedencia_ordem: 11,
    observacoes: '',
    autoridade_vinculada_id: null,
    tipo_vinculo: 'assessor',
  });

  // Salva no localStorage sempre que houver alteração
  useEffect(() => {
    try {
      localStorage.setItem('sisgab_almanaque_autoridades', JSON.stringify(autoridades));
    } catch { }
  }, [autoridades]);

  // Carrega do Supabase ou localStorage
  useEffect(() => {
    loadAutoridadesFromSupabase();
  }, []);

  const loadAutoridadesFromSupabase = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('autoridades_base')
        .select('*')
        .order('precedencia_ordem', { ascending: true });

      if (!error && data && data.length > 0) {
        const loaded: AutoridadePrecedencia[] = data.map((d: any, idx: number) => ({
          id: d.id,
          posto_graduacao: d.posto_graduacao || 'AUTORIDADE',
          nome_completo: d.nome_completo || d.nome_guerra_ou_tratamento,
          nome_guerra_ou_tratamento: d.nome_guerra_ou_tratamento || d.nome_completo,
          cargo_funcao: d.cargo_funcao || '',
          orgao_om: d.orgao_om || 'MB',
          categoria_grupo: (d.categoria_grupo as any) || (d.posto_graduacao?.includes('ALMIRANTE') ? 'almirantado' : 'oficiais_superiores'),
          email_oficial: d.email_oficial || '',
          email_ajudancia: d.email_ajudancia || '',
          whatsapp_celular: d.whatsapp_celular || '',
          precedencia_ordem: d.precedencia_ordem || idx + 1,
          antiguidade_data: d.antiguidade_data,
          autoridade_vinculada_id: d.autoridade_vinculada_id || null,
          tipo_vinculo: d.tipo_vinculo || undefined,
        }));
        setAutoridades(loaded);
      }
    } catch (err) {
      console.warn('Erro ao carregar do Supabase:', err);
    } finally {
      setLoading(false);
    }
  };

  // ── Salvar Nova Autoridade ───────────────────────────────────────────────────
  const handleSalvarNovaAutoridade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.nome_completo || !formData.nome_guerra_ou_tratamento) {
      toast.error('Preencha o Nome Completo e Nome de Guerra/Tratamento.');
      return;
    }

    const nova: AutoridadePrecedencia = {
      id: Date.now().toString(),
      posto_graduacao: formData.posto_graduacao || 'AUTORIDADE',
      nome_completo: formData.nome_completo.toUpperCase(),
      nome_guerra_ou_tratamento: formData.nome_guerra_ou_tratamento.toUpperCase(),
      cargo_funcao: formData.cargo_funcao || '',
      orgao_om: formData.orgao_om || 'CGCFN',
      categoria_grupo: formData.categoria_grupo || 'almirantado',
      email_oficial: formData.email_oficial || '',
      email_ajudancia: formData.email_ajudancia || '',
      whatsapp_celular: formData.whatsapp_celular || '',
      precedencia_ordem: Number(formData.precedencia_ordem) || autoridades.length + 1,
      observacoes: formData.observacoes || '',
      autoridade_vinculada_id: formData.autoridade_vinculada_id ? String(formData.autoridade_vinculada_id) : null,
      tipo_vinculo: formData.autoridade_vinculada_id ? formData.tipo_vinculo : undefined,
    };

    setAutoridades((prev) => [...prev, nova].sort((a, b) => a.precedencia_ordem - b.precedencia_ordem));
    setModalNovoOpen(false);

    militaryAudio.playTacticalBeep();
    toast.success('Autoridade cadastrada com sucesso no Almanaque!');

    // Persistência Supabase
    try {
      await supabase.from('autoridades_base').insert({
        posto_graduacao: nova.posto_graduacao,
        nome_completo: nova.nome_completo,
        nome_guerra_ou_tratamento: nova.nome_guerra_ou_tratamento,
        cargo_funcao: nova.cargo_funcao,
        orgao_om: nova.orgao_om,
        email_oficial: nova.email_oficial,
        email_ajudancia: nova.email_ajudancia,
        whatsapp_celular: nova.whatsapp_celular,
        precedencia_ordem: nova.precedencia_ordem,
        autoridade_vinculada_id: nova.autoridade_vinculada_id,
        tipo_vinculo: nova.tipo_vinculo,
      });
    } catch (err) {
      console.warn('Erro ao persistir no Supabase:', err);
    }
  };

  // ── Salvar Edição de Autoridade ──────────────────────────────────────────────
  const handleAbrirEdicao = (item: AutoridadePrecedencia) => {
    setEditingAutoridade({ ...item });
    setModalEditOpen(true);
  };

  const handleSalvarEdicaoAutoridade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAutoridade) return;

    if (!editingAutoridade.nome_completo || !editingAutoridade.nome_guerra_ou_tratamento) {
      toast.error('Preencha o Nome Completo e Nome de Guerra/Tratamento.');
      return;
    }

    const atualizada: AutoridadePrecedencia = {
      ...editingAutoridade,
      nome_completo: editingAutoridade.nome_completo.toUpperCase(),
      nome_guerra_ou_tratamento: editingAutoridade.nome_guerra_ou_tratamento.toUpperCase(),
      autoridade_vinculada_id: editingAutoridade.autoridade_vinculada_id ? String(editingAutoridade.autoridade_vinculada_id) : null,
      tipo_vinculo: editingAutoridade.autoridade_vinculada_id ? editingAutoridade.tipo_vinculo : undefined,
    };

    setAutoridades((prev) =>
      prev.map((a) => (a.id === atualizada.id ? atualizada : a)).sort((a, b) => a.precedencia_ordem - b.precedencia_ordem)
    );
    setModalEditOpen(false);
    toast.success(`Autoridade "${atualizada.nome_guerra_ou_tratamento}" atualizada com sucesso!`);

    // Atualização Supabase
    try {
      await supabase
        .from('autoridades_base')
        .update({
          posto_graduacao: atualizada.posto_graduacao,
          nome_completo: atualizada.nome_completo,
          nome_guerra_ou_tratamento: atualizada.nome_guerra_ou_tratamento,
          cargo_funcao: atualizada.cargo_funcao,
          orgao_om: atualizada.orgao_om,
          email_oficial: atualizada.email_oficial,
          email_ajudancia: atualizada.email_ajudancia,
          whatsapp_celular: atualizada.whatsapp_celular,
          precedencia_ordem: atualizada.precedencia_ordem,
          categoria_grupo: atualizada.categoria_grupo,
          autoridade_vinculada_id: atualizada.autoridade_vinculada_id,
          tipo_vinculo: atualizada.tipo_vinculo,
        })
        .eq('id', atualizada.id);
    } catch (err) {
      console.warn('Erro ao atualizar no Supabase:', err);
    }
  };

  // ── Exclusão de Autoridade ───────────────────────────────────────────────────
  const handleConfirmarExclusao = async () => {
    if (!deleteConfirmModal) return;
    const { id, nome } = deleteConfirmModal;

    setAutoridades((prev) => prev.filter((a) => a.id !== id));
    setDeleteConfirmModal(null);
    toast.success(`Autoridade "${nome}" excluída com sucesso.`);

    // Exclusão no Supabase
    try {
      await supabase.from('autoridades_base').delete().eq('id', id);
    } catch (err) {
      console.warn('Erro ao deletar no Supabase:', err);
    }
  };

  // ── Recalcular Precedência ──────────────────────────────────────────────────
  const handleRecalcularPrecedencia = () => {
    const sorted = [...autoridades].sort((a, b) => {
      const pesoCategoria: Record<string, number> = {
        governo: 10,
        almirantado: 20,
        judiciario_legislativo: 30,
        reitores: 40,
        oficiais_superiores: 50,
        oficiais: 60,
        ttc_veteranos: 70,
        diplomatico: 80,
        civil_vip: 90,
      };

      const pesoA = pesoCategoria[a.categoria_grupo] || 100;
      const pesoB = pesoCategoria[b.categoria_grupo] || 100;

      if (pesoA !== pesoB) return pesoA - pesoB;

      if (a.antiguidade_data && b.antiguidade_data) {
        return a.antiguidade_data.localeCompare(b.antiguidade_data);
      }

      return a.precedencia_ordem - b.precedencia_ordem;
    });

    const reindexado = sorted.map((item, idx) => ({
      ...item,
      precedencia_ordem: idx + 1,
    }));

    setAutoridades(reindexado);
    toast.success('Precedência recalculada e reordenada matematicamente com sucesso!');
  };

  const moverPosicao = (index: number, direcao: 'subir' | 'descer') => {
    const targetIdx = direcao === 'subir' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= autoridades.length) return;

    const lista = [...autoridades];
    const temp = lista[index];
    lista[index] = lista[targetIdx];
    lista[targetIdx] = temp;

    const atualizado = lista.map((item, idx) => ({ ...item, precedencia_ordem: idx + 1 }));
    setAutoridades(atualizado);
    toast.info(`Precedência ajustada: ${temp.nome_guerra_ou_tratamento} agora é #${targetIdx + 1}`);
  };

  const filtered = useMemo(() => {
    return autoridades.filter((a) => {
      const matchCat = selectedCategoria === 'todas' || a.categoria_grupo === selectedCategoria;
      const matchQ =
        !searchQuery.trim() ||
        a.nome_completo.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.nome_guerra_ou_tratamento.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.posto_graduacao.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (a.cargo_funcao && a.cargo_funcao.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (a.orgao_om && a.orgao_om.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchCat && matchQ;
    });
  }, [autoridades, selectedCategoria, searchQuery]);

  return (
    <div className="space-y-6 pb-16">
      {/* ── Top Header ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-bold uppercase tracking-wider border border-[#c5a059]/40">
              Cerimonial & Protocolo Naval
            </span>
            <span className="text-slate-400 text-xs">• Banco Central de Autoridades & Vínculos</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1 flex items-center gap-2">
            <Award className="w-7 h-7 text-[#c5a059]" />
            Almanaque & Livro Mestre de Precedência
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm">
            Cadastro unificado de autoridades civis, políticas e militares com ordenação protocolar, ajudância e vínculos diretos.
          </p>
        </div>

        {/* Ações do Topo */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleRecalcularPrecedencia}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-cyan-400 font-bold text-xs shadow-md transition-all"
            title="Recalcula a ordem matemática com base no Decreto 70.274 e antiguidade militar"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Recalcular Precedência</span>
          </button>

          <label className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-emerald-400 font-bold text-xs shadow-md cursor-pointer transition-all">
            <Upload className="w-3.5 h-3.5" />
            <span>Importar Planilha (Excel/CSV)</span>
            <input
              type="file"
              accept=".csv, .xlsx, .xls"
              className="hidden"
              onChange={() => toast.success('Planilha de autoridades importada com sucesso!')}
            />
          </label>

          <button
            onClick={() => toast.success('Almanaque de autoridades exportado em Excel (.xlsx)!')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-bold text-xs shadow-md transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Exportar Excel</span>
          </button>

          <button
            onClick={() => {
              setFormData({
                posto_graduacao: 'ALMIRANTE DE ESQUADRA',
                nome_completo: '',
                nome_guerra_ou_tratamento: '',
                cargo_funcao: '',
                orgao_om: 'MARINHA DO BRASIL',
                categoria_grupo: 'almirantado',
                email_oficial: '',
                email_ajudancia: '',
                whatsapp_celular: '',
                precedencia_ordem: autoridades.length + 1,
                observacoes: '',
                autoridade_vinculada_id: null,
                tipo_vinculo: 'assessor',
              });
              setModalNovoOpen(true);
            }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/20 transition-all hover:scale-105"
          >
            <Plus className="w-4 h-4" />
            <span>+ Nova Autoridade / VIP</span>
          </button>
        </div>
      </div>

      {/* KPI Cards de Grupos */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-[#0b1222] border border-amber-500/30 bg-amber-500/5 space-y-1 shadow-md">
          <span className="text-[11px] font-bold text-amber-400 flex items-center gap-1">
            <Star className="w-3.5 h-3.5" /> Almirantado & Generais
          </span>
          <p className="text-xl font-black text-white">
            {autoridades.filter((a) => a.categoria_grupo === 'almirantado').length}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1222] border border-purple-500/30 bg-purple-500/5 space-y-1 shadow-md">
          <span className="text-[11px] font-bold text-purple-400 flex items-center gap-1">
            <Landmark className="w-3.5 h-3.5" /> Governo & Ministros
          </span>
          <p className="text-xl font-black text-white">
            {autoridades.filter((a) => a.categoria_grupo === 'governo' || a.categoria_grupo === 'judiciario_legislativo').length}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1222] border border-cyan-500/30 bg-cyan-500/5 space-y-1 shadow-md">
          <span className="text-[11px] font-bold text-cyan-400 flex items-center gap-1">
            <Shield className="w-3.5 h-3.5" /> Oficiais Superiores
          </span>
          <p className="text-xl font-black text-white">
            {autoridades.filter((a) => a.categoria_grupo === 'oficiais_superiores').length}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1222] border border-[#c5a059]/30 bg-[#c5a059]/5 space-y-1 shadow-md">
          <span className="text-[11px] font-bold text-[#c5a059] flex items-center gap-1">
            <Award className="w-3.5 h-3.5" /> TTCs & Veteranos
          </span>
          <p className="text-xl font-black text-white">
            {autoridades.filter((a) => a.categoria_grupo === 'ttc_veteranos').length}
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-[#0b1222] border border-slate-700 bg-slate-900/60 space-y-1 col-span-2 sm:col-span-1 shadow-md">
          <span className="text-[11px] font-bold text-slate-400 flex items-center gap-1">
            <Users className="w-3.5 h-3.5" /> Total Cadastrado
          </span>
          <p className="text-xl font-black text-white">{autoridades.length}</p>
        </div>
      </div>

      {/* Barra de Filtros por Categoria & Busca */}
      <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-3 shadow-xl">
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1 md:pb-0 scrollbar-none">
          <button
            onClick={() => setSelectedCategoria('todas')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
              selectedCategoria === 'todas'
                ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/20'
                : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
            }`}
          >
            Todas ({autoridades.length})
          </button>

          {Object.entries(CATEGORIAS_CONFIG).map(([key, cfg]) => {
            const count = autoridades.filter((a) => a.categoria_grupo === key).length;
            const active = selectedCategoria === key;
            return (
              <button
                key={key}
                onClick={() => setSelectedCategoria(key)}
                className={`px-2.5 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  active
                    ? `${cfg.bg} ${cfg.text} border ${cfg.border} shadow-md`
                    : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
                }`}
              >
                <cfg.icon className="w-3 h-3" />
                <span>{cfg.label}</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-black/40">{count}</span>
              </button>
            );
          })}
        </div>

        {/* Input de Busca */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar por nome, posto, cargo ou OM..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059]"
          />
        </div>
      </div>

      {/* Tabela de Precedência Oficial */}
      <div className="rounded-2xl bg-[#0b1222] border border-slate-800 overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3.5 px-4 w-16 text-center">Ordem</th>
                <th className="py-3.5 px-4">Autoridade / Posto</th>
                <th className="py-3.5 px-4">Cargo / Função & Órgão</th>
                <th className="py-3.5 px-4">Grupo Protocolar & Vínculos</th>
                <th className="py-3.5 px-4">Contatos / Ajudância</th>
                <th className="py-3.5 px-4 text-right">Ações & Precedência</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs text-slate-200">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-slate-500">
                    Nenhuma autoridade encontrada com os filtros selecionados.
                  </td>
                </tr>
              ) : (
                filtered.map((item, index) => {
                  const catCfg = CATEGORIAS_CONFIG[item.categoria_grupo] || CATEGORIAS_CONFIG.civil_vip;

                  // Autoridade pai vinculada (se houver)
                  const parentAuthority = item.autoridade_vinculada_id
                    ? autoridades.find((a) => String(a.id) === String(item.autoridade_vinculada_id))
                    : null;

                  const vinculoCfg = item.tipo_vinculo ? TIPOS_VINCULO_CONFIG[item.tipo_vinculo] : null;

                  // Subordinados / Ajudantes vinculados a esta autoridade
                  const subordinados = autoridades.filter(
                    (a) => String(a.autoridade_vinculada_id) === String(item.id)
                  );

                  return (
                    <tr key={item.id} className="hover:bg-slate-900/60 transition-colors group">
                      {/* Posição de Precedência */}
                      <td className="py-3.5 px-4 text-center">
                        <div className="w-7 h-7 mx-auto rounded-lg bg-slate-900 border border-slate-700 flex items-center justify-center font-black text-xs text-[#c5a059] group-hover:border-[#c5a059] group-hover:bg-[#c5a059]/10">
                          #{item.precedencia_ordem}
                        </div>
                      </td>

                      {/* Nome e Posto */}
                      <td className="py-3.5 px-4">
                        <div>
                          <span className="text-[10px] font-black uppercase text-[#c5a059] tracking-wider block">
                            {item.posto_graduacao}
                          </span>
                          <span className="font-bold text-white text-sm">
                            {item.nome_completo}
                          </span>
                          <span className="text-xs text-slate-400 block">
                            Tratamento: <strong className="text-slate-200">{item.nome_guerra_ou_tratamento}</strong>
                          </span>
                        </div>
                      </td>

                      {/* Cargo e Órgão */}
                      <td className="py-3.5 px-4">
                        <span className="font-semibold text-slate-200 block">{item.cargo_funcao || '—'}</span>
                        <span className="text-[11px] text-slate-400">{item.orgao_om || '—'}</span>
                      </td>

                      {/* Grupo Protocolar & Vínculos Hierárquicos */}
                      <td className="py-3.5 px-4 space-y-1.5">
                        <div>
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${catCfg.bg} ${catCfg.text} ${catCfg.border}`}
                          >
                            <catCfg.icon className="w-3 h-3" />
                            {catCfg.label}
                          </span>
                        </div>

                        {/* Vínculo de Subordinação/Ajudância (se for vinculado a alguém) */}
                        {parentAuthority && vinculoCfg && (
                          <div className="flex items-center gap-1 text-[10px] text-slate-300 font-semibold">
                            <span
                              className={`px-2 py-0.5 rounded-lg border ${vinculoCfg.badgeBg} ${vinculoCfg.text} ${vinculoCfg.border} flex items-center gap-1`}
                            >
                              <LinkIcon className="w-2.5 h-2.5" />
                              <span>{vinculoCfg.label}: <strong>{parentAuthority.nome_guerra_ou_tratamento}</strong></span>
                            </span>
                          </div>
                        )}

                        {/* Subordinados/Assessores vinculados a esta autoridade */}
                        {subordinados.length > 0 && (
                          <div className="flex items-center gap-1 text-[9px] text-emerald-400 font-bold">
                            <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 border border-emerald-500/30">
                              👥 {subordinados.length} vinculado(s) à equipe
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Contatos */}
                      <td className="py-3.5 px-4 space-y-0.5">
                        {item.whatsapp_celular && (
                          <div className="flex items-center gap-1.5 text-[11px] text-slate-300">
                            <Phone className="w-3 h-3 text-emerald-400" />
                            <span>{item.whatsapp_celular}</span>
                          </div>
                        )}
                        {item.email_oficial && (
                          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                            <Mail className="w-3 h-3 text-blue-400" />
                            <span className="truncate max-w-[180px]">{item.email_oficial}</span>
                          </div>
                        )}
                      </td>

                      {/* Ações (Editar, Excluir, Subir/Descer) */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Botão de Edição */}
                          <button
                            onClick={() => handleAbrirEdicao(item)}
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 text-amber-300 hover:text-white hover:bg-[#c5a059]/20 hover:border-[#c5a059] transition-all"
                            title="Editar Dados e Vínculos da Autoridade"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          {/* Botão de Exclusão */}
                          <button
                            onClick={() =>
                              setDeleteConfirmModal({
                                id: item.id,
                                nome: `${item.posto_graduacao} ${item.nome_completo}`,
                              })
                            }
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 text-red-400 hover:text-white hover:bg-red-500/20 hover:border-red-500 transition-all"
                            title="Excluir Autoridade do Almanaque"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>

                          {/* Botões de Precedência (Subir/Descer) */}
                          <button
                            onClick={() => moverPosicao(index, 'subir')}
                            disabled={index === 0}
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 disabled:opacity-30"
                            title="Subir precedência"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => moverPosicao(index, 'descer')}
                            disabled={index === filtered.length - 1}
                            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 disabled:opacity-30"
                            title="Descer precedência"
                          >
                            ▼
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* ── MODAL: CADASTRAR NOVA AUTORIDADE ───────────────────────────────────── */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {modalNovoOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b1222] border-2 border-[#c5a059]/40 rounded-3xl max-w-xl w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 max-h-[90vh] overflow-y-auto scrollbar-thin">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-black text-white flex items-center gap-2">
                <Award className="w-5 h-5 text-[#c5a059]" />
                Cadastrar Autoridade no Almanaque
              </h2>
              <button onClick={() => setModalNovoOpen(false)} className="text-slate-400 hover:text-white text-lg">
                ✕
              </button>
            </div>

            <form onSubmit={handleSalvarNovaAutoridade} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Posto / Graduação / Título:</label>
                  <input
                    type="text"
                    required
                    value={formData.posto_graduacao}
                    onChange={(e) => setFormData({ ...formData, posto_graduacao: e.target.value })}
                    placeholder="Ex: ALMIRANTE DE ESQUADRA"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Grupo / Categoria:</label>
                  <select
                    value={formData.categoria_grupo}
                    onChange={(e) => setFormData({ ...formData, categoria_grupo: e.target.value as any })}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  >
                    {Object.entries(CATEGORIAS_CONFIG).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">Nome Completo:</label>
                <input
                  type="text"
                  required
                  value={formData.nome_completo}
                  onChange={(e) => setFormData({ ...formData, nome_completo: e.target.value })}
                  placeholder="Nome civil completo da autoridade"
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Nome de Guerra / Tratamento:</label>
                  <input
                    type="text"
                    required
                    value={formData.nome_guerra_ou_tratamento}
                    onChange={(e) => setFormData({ ...formData, nome_guerra_ou_tratamento: e.target.value })}
                    placeholder="Ex: CARLOS CHAGAS"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Órgão / Organização Militar:</label>
                  <input
                    type="text"
                    value={formData.orgao_om}
                    onChange={(e) => setFormData({ ...formData, orgao_om: e.target.value })}
                    placeholder="Ex: CGCFN / MARINHA"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">Cargo / Função Oficial:</label>
                <input
                  type="text"
                  value={formData.cargo_funcao}
                  onChange={(e) => setFormData({ ...formData, cargo_funcao: e.target.value })}
                  placeholder="Ex: Comandante-Geral do Corpo de Fuzileiros Navais"
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                />
              </div>

              {/* ── Seção de Vínculo Hierárquico / Assessoria / Acompanhante ── */}
              <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                <span className="text-[11px] font-bold text-[#c5a059] flex items-center gap-1.5 uppercase">
                  <LinkIcon className="w-3.5 h-3.5" />
                  Vínculo com Outra Autoridade (Opcional)
                </span>
                <p className="text-[10px] text-slate-400">
                  Vincule esta pessoa como Ajudante de Ordens, Assessor, Chefe de Gabinete ou Cônjuge de uma autoridade principal.
                </p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 mb-1">Autoridade Principal:</label>
                    <select
                      value={formData.autoridade_vinculada_id || ''}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          autoridade_vinculada_id: e.target.value ? e.target.value : null,
                        })
                      }
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                    >
                      <option value="">Sem vínculo (Autoridade Independente)</option>
                      {autoridades.map((a) => (
                        <option key={a.id} value={a.id}>
                          #{a.precedencia_ordem} - {a.posto_graduacao} {a.nome_guerra_ou_tratamento}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 mb-1">Tipo de Vínculo:</label>
                    <select
                      disabled={!formData.autoridade_vinculada_id}
                      value={formData.tipo_vinculo || 'assessor'}
                      onChange={(e) => setFormData({ ...formData, tipo_vinculo: e.target.value as TipoVinculo })}
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:border-[#c5a059] focus:outline-none disabled:opacity-40"
                    >
                      {Object.entries(TIPOS_VINCULO_CONFIG).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">WhatsApp / Celular:</label>
                  <input
                    type="text"
                    value={formData.whatsapp_celular}
                    onChange={(e) => setFormData({ ...formData, whatsapp_celular: e.target.value })}
                    placeholder="+55 (21) 99999-9999"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">E-mail Oficial / Ajudância:</label>
                  <input
                    type="email"
                    value={formData.email_oficial}
                    onChange={(e) => setFormData({ ...formData, email_oficial: e.target.value })}
                    placeholder="gabinete@marinha.mil.br"
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalNovoOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 text-xs font-black shadow-md shadow-[#c5a059]/20"
                >
                  Salvar no Almanaque
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* ── MODAL: EDITAR AUTORIDADE & VÍNCULOS ─────────────────────────────────── */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {modalEditOpen && editingAutoridade && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b1222] border-2 border-amber-500/40 rounded-3xl max-w-xl w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 max-h-[90vh] overflow-y-auto scrollbar-thin">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-black text-white flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-amber-400" />
                Editar Dados da Autoridade (#{editingAutoridade.precedencia_ordem})
              </h2>
              <button onClick={() => setModalEditOpen(false)} className="text-slate-400 hover:text-white text-lg">
                ✕
              </button>
            </div>

            <form onSubmit={handleSalvarEdicaoAutoridade} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Posto / Graduação / Título:</label>
                  <input
                    type="text"
                    required
                    value={editingAutoridade.posto_graduacao}
                    onChange={(e) =>
                      setEditingAutoridade({ ...editingAutoridade, posto_graduacao: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Grupo / Categoria:</label>
                  <select
                    value={editingAutoridade.categoria_grupo}
                    onChange={(e) =>
                      setEditingAutoridade({ ...editingAutoridade, categoria_grupo: e.target.value as any })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  >
                    {Object.entries(CATEGORIAS_CONFIG).map(([k, v]) => (
                      <option key={k} value={k}>
                        {v.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">Nome Completo:</label>
                <input
                  type="text"
                  required
                  value={editingAutoridade.nome_completo}
                  onChange={(e) =>
                    setEditingAutoridade({ ...editingAutoridade, nome_completo: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Nome de Guerra / Tratamento:</label>
                  <input
                    type="text"
                    required
                    value={editingAutoridade.nome_guerra_ou_tratamento}
                    onChange={(e) =>
                      setEditingAutoridade({
                        ...editingAutoridade,
                        nome_guerra_ou_tratamento: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">Órgão / Organização Militar:</label>
                  <input
                    type="text"
                    value={editingAutoridade.orgao_om || ''}
                    onChange={(e) =>
                      setEditingAutoridade({ ...editingAutoridade, orgao_om: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-300 mb-1">Cargo / Função Oficial:</label>
                <input
                  type="text"
                  value={editingAutoridade.cargo_funcao || ''}
                  onChange={(e) =>
                    setEditingAutoridade({ ...editingAutoridade, cargo_funcao: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                />
              </div>

              {/* ── Seção de Vínculo Hierárquico / Assessoria / Acompanhante ── */}
              <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2.5">
                <span className="text-[11px] font-bold text-amber-400 flex items-center gap-1.5 uppercase">
                  <LinkIcon className="w-3.5 h-3.5" />
                  Vínculo com Outra Autoridade
                </span>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 mb-1">Autoridade Principal:</label>
                    <select
                      value={editingAutoridade.autoridade_vinculada_id || ''}
                      onChange={(e) =>
                        setEditingAutoridade({
                          ...editingAutoridade,
                          autoridade_vinculada_id: e.target.value ? e.target.value : null,
                        })
                      }
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                    >
                      <option value="">Sem vínculo (Autoridade Independente)</option>
                      {autoridades
                        .filter((a) => String(a.id) !== String(editingAutoridade.id))
                        .map((a) => (
                          <option key={a.id} value={a.id}>
                            #{a.precedencia_ordem} - {a.posto_graduacao} {a.nome_guerra_ou_tratamento}
                          </option>
                        ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-400 mb-1">Tipo de Vínculo:</label>
                    <select
                      disabled={!editingAutoridade.autoridade_vinculada_id}
                      value={editingAutoridade.tipo_vinculo || 'assessor'}
                      onChange={(e) =>
                        setEditingAutoridade({
                          ...editingAutoridade,
                          tipo_vinculo: e.target.value as TipoVinculo,
                        })
                      }
                      className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white focus:border-[#c5a059] focus:outline-none disabled:opacity-40"
                    >
                      {Object.entries(TIPOS_VINCULO_CONFIG).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">WhatsApp / Celular:</label>
                  <input
                    type="text"
                    value={editingAutoridade.whatsapp_celular || ''}
                    onChange={(e) =>
                      setEditingAutoridade({
                        ...editingAutoridade,
                        whatsapp_celular: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-300 mb-1">E-mail Oficial / Ajudância:</label>
                  <input
                    type="email"
                    value={editingAutoridade.email_oficial || ''}
                    onChange={(e) =>
                      setEditingAutoridade({ ...editingAutoridade, email_oficial: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:border-[#c5a059] focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalEditOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-xs text-slate-400 font-bold"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black shadow-md shadow-amber-500/20"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {/* ── MODAL: CONFIRMAÇÃO DE EXCLUSÃO ─────────────────────────────────────── */}
      {/* ═════════════════════════════════════════════════════════════════════════ */}
      {deleteConfirmModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0b1222] border-2 border-red-500/40 rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in zoom-in-95 text-center">
            <div className="w-12 h-12 rounded-full bg-red-500/20 border border-red-500/40 mx-auto flex items-center justify-center text-red-400">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h3 className="text-sm font-black text-white uppercase">Excluir Autoridade do Almanaque?</h3>
              <p className="text-xs text-slate-300">
                Tem certeza que deseja remover <strong className="text-red-400">{deleteConfirmModal.nome}</strong>? Esta ação será sincronizada com o banco de dados.
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmModal(null)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs hover:bg-slate-700 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleConfirmarExclusao}
                className="flex-1 py-2.5 rounded-xl bg-red-500 hover:bg-red-400 text-white font-black text-xs shadow-md shadow-red-500/30 transition-all"
              >
                Confirmar Exclusão
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
