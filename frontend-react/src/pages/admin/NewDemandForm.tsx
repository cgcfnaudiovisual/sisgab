import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  PlusCircle,
  Calendar,
  Clock,
  MapPin,
  Camera,
  Video,
  Radio,
  FileText,
  UploadCloud,
  CheckCircle2,
  Sparkles,
  Link as LinkIcon,
  Shield,
  Palette,
  Printer,
  Gift,
  Mic,
  Zap,
  HelpCircle,
  FolderPlus,
  ExternalLink,
  Users,
  UserCheck,
  Music,
  Edit3,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import { useAuth } from '../../context/AuthContext';
import { getBrasiliaDateStr } from '../../utils/formatters';

// Categorias e Serviços Completos do SisGAB
export const CATEGORIAS_SERVICOS = [
  {
    id: 'audiovisual',
    titulo: '📸 Audiovisual & Cobertura',
    color: 'border-cyan-500/40 text-cyan-400 bg-cyan-500/5',
    servicos: [
      { id: 'Fotografia', label: 'Fotografia Oficial', icon: Camera },
      { id: 'Video', label: 'Vídeo / Gravação', icon: Video },
      { id: 'Reels', label: 'Redes Sociais / Reels', icon: Video },
      { id: 'Drone', label: 'Drone / Imagens Aéreas', icon: Radio },
      { id: 'Transmissao', label: 'Transmissão Ao Vivo', icon: Radio },
    ],
  },
  {
    id: 'design',
    titulo: '🎨 Design & Criação Gráfica',
    color: 'border-pink-500/40 text-pink-400 bg-pink-500/5',
    servicos: [
      { id: 'Cardapio_Design', label: 'Layout de Cardápio', icon: Palette },
      { id: 'Banner_Digital', label: 'Banner / Cartaz Digital', icon: Palette },
      { id: 'Convite_Arte', label: 'Convite Digital / Panfleto', icon: Palette },
      { id: 'Redes_Design', label: 'Artes para Redes Sociais', icon: Palette },
      { id: 'Placa_Paspatur_Design', label: 'Layout / Arte Foto Paspatur (A5/A6)', icon: Palette },
    ],
  },
  {
    id: 'impressos',
    titulo: '🖨️ Gráfica & Impressos Físicos',
    color: 'border-purple-500/40 text-purple-400 bg-purple-500/5',
    servicos: [
      { id: 'Impressao_Banner', label: 'Impressão de Banner / Lona', icon: Printer },
      { id: 'Impressao_Cardapio', label: 'Impressão de Cardápios', icon: Printer },
      { id: 'Quadro_Paspatur', label: 'Envelope / Paspatur (A5, A6 ou Sob Medida)', icon: Printer },
      { id: 'Album_Fotografico', label: 'Álbum Fotográfico Oficial', icon: Printer },
    ],
  },
  {
    id: 'redacao',
    titulo: '✍️ Redação, Discursos & Jornalismo',
    color: 'border-emerald-500/40 text-emerald-400 bg-emerald-500/5',
    servicos: [
      { id: 'Discurso', label: 'Discurso / Ordem do Dia', icon: FileText },
      { id: 'Materia_Noticia', label: 'Matéria para Portal Oficial', icon: FileText },
      { id: 'Release_Imprensa', label: 'Release para a Imprensa', icon: FileText },
    ],
  },
  {
    id: 'cerimonial',
    titulo: '🎤 Cerimonial, Música & Suporte',
    color: 'border-blue-500/40 text-blue-400 bg-blue-500/5',
    servicos: [
      { id: 'Banda_Musica', label: 'Apresentação da Banda Sinfônica / Música', icon: Music },
      { id: 'Sonorizacao', label: 'Sonorização / Áudio do Evento', icon: Mic },
      { id: 'Credenciamento', label: 'Credenciamento & Portaria', icon: Shield },
    ],
  },
  {
    id: 'brindes',
    titulo: '🪙 Brindes & Relações Públicas',
    color: 'border-amber-500/40 text-amber-400 bg-amber-500/5',
    servicos: [
      { id: 'Challenge_Coin', label: 'Moeda Comemorativa (Coin)', icon: Gift },
      { id: 'Kit_Lembranca', label: 'Kit Brinde Oficial RP', icon: Gift },
    ],
  },
];

interface MilitarOpcao {
  id: number;
  nome_guerra: string;
  posto_grad?: string;
  role: string;
  setor?: string;
  isComsoc: boolean;
}

export const NewDemandForm: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const editId = searchParams.get('edit_id') || searchParams.get('id');
  const [submitting, setSubmitting] = useState(false);
  const [loadingEdit, setLoadingEdit] = useState(false);

  // Lista de Militares para Escalação
  const [militares, setMilitares] = useState<MilitarOpcao[]>([]);
  const [selectedMilitares, setSelectedMilitares] = useState<number[]>([]);
  const [equipeFilter, setEquipeFilter] = useState<'comsoc' | 'todos'>('comsoc');

  // Modo de Data: 'unica' | 'periodo' | 'sem_data'
  const [tipoData, setTipoData] = useState<'unica' | 'periodo' | 'sem_data'>('unica');

  // Form State
  const [formData, setFormData] = useState({
    solicitante_nome: user?.nome_guerra ? `${user.posto || ''} ${user.nome_guerra}`.trim() : 'SG CALAÇA',
    setor: user?.setor || 'Comunicação Social / Gabinete',
    contato: '',
    titulo_evento: '',
    data_evento: getBrasiliaDateStr(),
    data_fim: '',
    hora_evento: '09:00',
    local_evento: '',
    tipo_cobertura: ['Fotografia'],
    autoridades: '',
    drive_url: '',
    sigiloso: false,
    captacao_entrega: 'apenas_captacao_bruto',
    observacoes: '',
    gerar_pasta_drive: true,
  });

  useEffect(() => {
    loadMilitares();
    if (editId) {
      loadDemandaForEdit(Number(editId));
    }
  }, [editId]);

  // Helper para extrair URL do Drive de dados da demanda
  const extractDriveUrlFromDemand = (data: any) => {
    if (data.drive_url && String(data.drive_url).startsWith('http')) return String(data.drive_url).trim();
    if (data.arquivo_url && String(data.arquivo_url).startsWith('http')) return String(data.arquivo_url).trim();
    const combined = `${data.autoridades || ''} ${data.produto_especifico || ''} ${data.observacoes || ''}`;
    const match = combined.match(/https:\/\/drive\.google\.com[^\s\]]+/);
    return match ? match[0] : '';
  };

  // Helper para limpar tags do campo autoridades
  const cleanAutoridadesText = (raw?: string | null) => {
    if (!raw) return '';
    return raw
      .replace(/\[DRIVE:[^\]]+\]/gi, '')
      .replace(/https:\/\/drive\.google\.com[^\s\]]+/gi, '')
      .replace(/Obs:?\s*Horário[^\.]+/gi, '')
      .trim();
  };

  const loadDemandaForEdit = async (id: number) => {
    try {
      setLoadingEdit(true);
      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .eq('id', id)
        .single();

      if (!error && data) {
        const rawDriveUrl = extractDriveUrlFromDemand(data);
        const cleanedAut = cleanAutoridadesText(data.autoridades);
        const obs = data.produto_especifico || data.observacoes || '';
        const rawHora = data.hora_evento && data.hora_evento !== 'A DEFINIR' ? data.hora_evento.slice(0, 5) : '09:00';

        // Normalização de coberturas
        let parsedCoverages: string[] = [];
        if (Array.isArray(data.tipo_cobertura)) {
          parsedCoverages = data.tipo_cobertura;
        } else if (typeof data.tipo_cobertura === 'string') {
          try {
            const jsonParsed = JSON.parse(data.tipo_cobertura);
            if (Array.isArray(jsonParsed)) parsedCoverages = jsonParsed;
          } catch {
            parsedCoverages = data.tipo_cobertura.split(',').map((s: string) => s.trim()).filter(Boolean);
          }
        }
        const normalizedCoverages = parsedCoverages.map((c) => {
          const lower = c.toLowerCase();
          if (lower === 'foto' || lower === 'fotografia') return 'Fotografia';
          if (lower === 'video') return 'Video';
          if (lower === 'drone') return 'Drone';
          if (lower === 'reels') return 'Reels';
          if (lower === 'transmissao') return 'Transmissao';
          return c;
        });

        setFormData({
          solicitante_nome: data.solicitante_nome || '',
          setor: data.setor || '',
          contato: data.contato || '',
          titulo_evento: data.titulo_evento || '',
          data_evento: data.data_evento && data.data_evento !== 'SEM_DATA' ? data.data_evento : getBrasiliaDateStr(),
          data_fim: data.data_fim || '',
          hora_evento: rawHora,
          local_evento: data.local_evento || '',
          tipo_cobertura: normalizedCoverages.length > 0 ? normalizedCoverages : ['Fotografia'],
          autoridades: cleanedAut,
          drive_url: rawDriveUrl,
          sigiloso: !!data.sigiloso,
          captacao_entrega: data.captacao_entrega || 'apenas_captacao_bruto',
          observacoes: obs,
          gerar_pasta_drive: !rawDriveUrl,
        });

        if (data.data_fim && data.data_fim > data.data_evento) {
          setTipoData('periodo');
        } else if (!data.data_evento || data.data_evento === 'SEM_DATA') {
          setTipoData('sem_data');
        } else {
          setTipoData('unica');
        }

        if (data.notificar_militar_ids) {
          if (Array.isArray(data.notificar_militar_ids)) {
            setSelectedMilitares(data.notificar_militar_ids);
          } else if (typeof data.notificar_militar_ids === 'string') {
            try {
              const parsed = JSON.parse(data.notificar_militar_ids);
              if (Array.isArray(parsed)) setSelectedMilitares(parsed);
            } catch {
              // fallback
            }
          }
        }

        militaryAudio.playTacticalBeep();
        toast.info(`Pauta #${id} "${data.titulo_evento}" carregada para edição completa!`);
      }
    } catch (e) {
      console.warn('Erro ao carregar demanda para edição:', e);
    } finally {
      setLoadingEdit(false);
    }
  };

  const loadMilitares = async () => {
    try {
      const { data, error } = await supabase.from('efetivo').select('id, nome_guerra, posto_grad, role, setor');
      if (!error && data && data.length > 0) {
        const formatados: MilitarOpcao[] = data.map((m: any) => {
          const roleStr = (m.role || '').toLowerCase();
          const setorStr = (m.setor || '').toLowerCase();
          const isComsoc =
            roleStr.includes('comsoc') ||
            roleStr.includes('admin') ||
            roleStr.includes('supervisor') ||
            roleStr.includes('oficial_gab') ||
            setorStr.includes('comsoc') ||
            setorStr.includes('gabinete');

          return {
            id: m.id,
            nome_guerra: m.nome_guerra || `MILITAR #${m.id}`,
            posto_grad: m.posto_grad || '',
            role: m.role || 'operador',
            setor: m.setor || 'CGCFN',
            isComsoc,
          };
        });

        // Ordenação inteligente: COMSOC / Admin / Supervisor primeiro
        formatados.sort((a, b) => {
          if (a.isComsoc && !b.isComsoc) return -1;
          if (!a.isComsoc && b.isComsoc) return 1;
          return a.nome_guerra.localeCompare(b.nome_guerra);
        });

        setMilitares(formatados);
      }
    } catch (err) {
      console.warn('Erro ao carregar efetivo:', err);
    }
  };

  const handleToggleMilitar = (militarId: number) => {
    setSelectedMilitares((prev) =>
      prev.includes(militarId) ? prev.filter((id) => id !== militarId) : [...prev, militarId]
    );
  };

  // ⚡ Atalhos Rápidos (Pacotes de 1 Clique Calibrados)
  const aplicarPacote = (tipo: 'completo' | 'almoco' | 'reels' | 'paspatur' | 'discurso') => {
    if (tipo === 'completo') {
      setFormData((prev) => ({
        ...prev,
        titulo_evento: prev.titulo_evento || 'CERIMÔNIA OFICIAL / PASSAGEM DE COMANDO',
        local_evento: prev.local_evento || 'Fortaleza de São José - Ilha das Cobras',
        tipo_cobertura: [
          'Fotografia',
          'Video',
          'Drone',
          'Quadro_Paspatur',
          'Cardapio_Design',
          'Banda_Musica',
        ],
      }));
      toast.success('🌟 Pacote Completo Aplicado! (Foto + Vídeo + Drone + Paspatur + Cardápio + Banda)');
    } else if (tipo === 'almoco') {
      setFormData((prev) => ({
        ...prev,
        titulo_evento: prev.titulo_evento || 'ALMOÇO OFICIAL DE AUTORIDADES',
        local_evento: prev.local_evento || 'Salão Nobre do CGCFN',
        tipo_cobertura: ['Cardapio_Design', 'Impressao_Cardapio', 'Fotografia'],
      }));
      toast.success('🍽️ Pacote Almoço Oficial Aplicado! (Layout Cardápio + Impressão + Fotografia)');
    } else if (tipo === 'reels') {
      setFormData((prev) => ({
        ...prev,
        titulo_evento: prev.titulo_evento || 'COBERTURA REELS & REDES SOCIAIS',
        tipo_cobertura: ['Video', 'Reels', 'Redes_Design'],
      }));
      toast.success('📱 Pacote Mídias & Reels Aplicado! (Vídeo + Reels + Artes Redes)');
    } else if (tipo === 'paspatur') {
      setFormData((prev) => ({
        ...prev,
        titulo_evento: prev.titulo_evento || 'PASPATUR PARA HOMENAGEM OFICIAL',
        tipo_cobertura: ['Quadro_Paspatur', 'Placa_Paspatur_Design', 'Fotografia'],
      }));
      toast.success('🖼️ Pacote Paspatur Aplicado! (Layout Placa + Moldura Paspatur + Foto)');
    } else if (tipo === 'discurso') {
      setFormData((prev) => ({
        ...prev,
        titulo_evento: prev.titulo_evento || 'DISCURSO OFICIAL / MATÉRIA DE COBERTURA',
        tipo_cobertura: ['Discurso', 'Materia_Noticia', 'Release_Imprensa'],
      }));
      toast.success('📜 Pacote Discurso & Redação Aplicado! (Discurso + Matéria Portal + Release)');
    }
  };

  const handleToggleCoverage = (tipoId: string) => {
    setFormData((prev) => {
      const exists = prev.tipo_cobertura.includes(tipoId);
      return {
        ...prev,
        tipo_cobertura: exists
          ? prev.tipo_cobertura.filter((t) => t !== tipoId)
          : [...prev.tipo_cobertura, tipoId],
      };
    });
  };

  const [creatingDrive, setCreatingDrive] = useState(false);

  // Gerador Inteligente de Pasta do Drive (Criação Real no Google Drive)
  const handleGerarPastaDrive = async () => {
    if (!formData.titulo_evento.trim()) {
      toast.error('Informe o Título do Evento / Pauta primeiro.');
      return;
    }

    try {
      setCreatingDrive(true);
      toast.loading('Criando pasta oficial no Google Drive...', { id: 'create_drive' });

      const res = await fetch('/api/drive/create_event_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo_evento: formData.titulo_evento,
          data_evento: tipoData === 'sem_data' ? getBrasiliaDateStr() : formData.data_evento,
        }),
      });

      const json = await res.json();
      if (json.ok && json.evento_link) {
        militaryAudio.playTacticalBeep();
        setFormData((prev) => ({ ...prev, drive_url: json.evento_link }));
        toast.success(`Pasta criada com sucesso no Google Drive!`, {
          id: 'create_drive',
          description: 'Subpastas GERAL e SELEÇÃO estruturadas.',
        });
      } else {
        toast.error(`Falha ao criar pasta: ${json.error || 'Erro desconhecido'}`, { id: 'create_drive' });
      }
    } catch (err: any) {
      toast.error(`Erro de comunicação com o servidor: ${err.message}`, { id: 'create_drive' });
    } finally {
      setCreatingDrive(false);
    }
  };

  // Cálculo Dinâmico de Score de Esforço
  const calculateScore = () => {
    let score = 1.0;
    score += formData.tipo_cobertura.length * 0.7;
    if (formData.tipo_cobertura.includes('Drone')) score += 1.0;
    if (formData.tipo_cobertura.includes('Transmissao')) score += 1.5;
    if (formData.tipo_cobertura.includes('Video')) score += 0.8;
    if (formData.sigiloso) score += 0.5;
    return parseFloat(score.toFixed(1));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.titulo_evento || !formData.solicitante_nome) {
      toast.error('Preencha os campos obrigatórios (Título e Solicitante).');
      return;
    }

    if (tipoData !== 'sem_data' && !formData.local_evento) {
      toast.error('Informe o local previsto do evento.');
      return;
    }

    try {
      setSubmitting(true);
      const score = calculateScore();

      const finalDataEvento = tipoData === 'sem_data' ? null : formData.data_evento;
      const finalDataFim = tipoData === 'periodo' && formData.data_fim ? formData.data_fim : null;

      const cleanedAut = cleanAutoridadesText(formData.autoridades);
      const driveUrlTrimmed = formData.drive_url?.trim();
      const finalAutoridades = driveUrlTrimmed
        ? (cleanedAut ? `${cleanedAut} [DRIVE: ${driveUrlTrimmed}]` : `[DRIVE: ${driveUrlTrimmed}]`)
        : cleanedAut;

      if (editId) {
        const { error } = await supabase
          .from('demandas_comunicacao')
          .update({
            solicitante_nome: formData.solicitante_nome,
            setor: formData.setor,
            contato: formData.contato || 'Gabinete CGCFN',
            titulo_evento: formData.titulo_evento,
            data_evento: finalDataEvento,
            data_fim: finalDataFim,
            hora_evento: tipoData === 'sem_data' ? 'A DEFINIR' : (formData.hora_evento || '09:00'),
            local_evento: formData.local_evento || 'A Definir',
            tipo_cobertura: formData.tipo_cobertura,
            autoridades: finalAutoridades,
            score_esforco: score,
            sigiloso: formData.sigiloso,
            captacao_entrega: formData.captacao_entrega,
            produto_especifico: formData.observacoes || '',
            notificar_militar_ids: selectedMilitares,
            encarregado_id: selectedMilitares.length > 0 ? selectedMilitares[0] : null,
          })
          .eq('id', Number(editId));

        if (error) throw error;

        // Salvar link do Drive via API resiliente (usa campo autoridades como fallback)
        if (driveUrlTrimmed) {
          try {
            await fetch('/api/drive/save_drive_link', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                demanda_id: Number(editId),
                titulo_evento: formData.titulo_evento,
                drive_url: driveUrlTrimmed,
              }),
            });
          } catch (_) { /* silencioso */ }
        }

        militaryAudio.playTacticalBeep();
        toast.success(`Demanda #${editId} atualizada com sucesso!`, {
          description: 'Todas as alterações foram gravadas no banco de dados.',
        });

        setTimeout(() => {
          navigate('/comsoc_homologar');
        }, 1200);
        return;
      }

      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .insert({
          solicitante_nome: formData.solicitante_nome,
          setor: formData.setor,
          contato: formData.contato || 'Gabinete CGCFN',
          titulo_evento: formData.titulo_evento,
          data_evento: finalDataEvento,
          data_fim: finalDataFim,
          hora_evento: tipoData === 'sem_data' ? 'A DEFINIR' : (formData.hora_evento || '09:00'),
          local_evento: formData.local_evento || 'A Definir',
          tipo_cobertura: formData.tipo_cobertura,
          autoridades: finalAutoridades,
          score_esforco: score,
          sigiloso: formData.sigiloso,
          status: 'pendente',
          captacao_entrega: formData.captacao_entrega,
          categoria_demanda: 'audiovisual',
          produto_especifico: formData.observacoes || '',
          notificar_militar_ids: selectedMilitares,
          encarregado_id: selectedMilitares.length > 0 ? selectedMilitares[0] : null,
        })
        .select();

      // Salvar link do Drive resilientemente após criação
      if (driveUrlTrimmed && data && data[0]?.id) {
        try {
          await fetch('/api/drive/save_drive_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              demanda_id: data[0].id,
              titulo_evento: formData.titulo_evento,
              drive_url: driveUrlTrimmed,
            }),
          });
        } catch (_) { /* silencioso */ }
      }

      // Confetes comemorativos
      militaryAudio.playTacticalBeep();

      toast.success('Demanda cadastrada com sucesso!', {
        description:
          tipoData === 'sem_data'
            ? 'Pauta adicionada ao Quadro de Demandas Futuras (Sem Data Fixa).'
            : 'A solicitação foi encaminhada para homologação da Chefia.',
      });

      setTimeout(() => {
        navigate('/comsoc_homologar');
      }, 1200);
    } catch (err) {
      console.warn('Erro ao submeter:', err);
      toast.error('Erro ao processar demanda no banco de dados.');
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header & Banner de Edição */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded bg-[#c5a059]/20 text-[#c5a059] text-xs font-black uppercase tracking-wider border border-[#c5a059]/40">
            {editId ? `Edição de Demanda #${editId}` : 'Formulário Oficial'}
          </span>
          <span className="text-slate-400 text-xs">• Comunicação Social</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mt-1">
          {editId ? `Editar Demanda: ${formData.titulo_evento || `#${editId}`}` : 'Nova Solicitação de Demanda / Cobertura'}
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm">
          {editId
            ? 'Atualize os dados da pauta, cobertura, militares escalados e link oficial do Google Drive.'
            : 'Cadastre uma nova pauta audiovisual, criação gráfica, impressos ou apoio cerimonial para homologação e escalação.'}
        </p>
      </div>

      {/* Banner de Edição Ativa com botão de Reset */}
      {editId && (
        <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-500/40 flex items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-xl bg-amber-500/20 text-[#e5c07b]">
              <Edit3 className="w-5 h-5" />
            </span>
            <div>
              <p className="text-xs font-black text-white">
                Modo de Edição Ativo: Pauta #{editId}
              </p>
              <p className="text-[11px] text-amber-300">
                {loadingEdit ? 'Carregando dados da demanda...' : 'Você está editando todos os dados desta pauta. Salvar aplicará as mudanças imediatamente.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              setSearchParams({});
              setFormData({
                solicitante_nome: user?.nome_guerra ? `${user.posto || ''} ${user.nome_guerra}`.trim() : 'SG CALAÇA',
                setor: user?.setor || 'Comunicação Social / Gabinete',
                contato: '',
                titulo_evento: '',
                data_evento: getBrasiliaDateStr(),
                data_fim: '',
                hora_evento: '09:00',
                local_evento: '',
                tipo_cobertura: ['Fotografia'],
                autoridades: '',
                drive_url: '',
                sigiloso: false,
                captacao_entrega: 'apenas_captacao_bruto',
                observacoes: '',
                gerar_pasta_drive: true,
              });
              setSelectedMilitares([]);
              toast.info('Modo de edição desativado. Formulário limpo.');
            }}
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-bold border border-slate-700 transition-all shrink-0"
          >
            + Criar Nova Demanda
          </button>
        </div>
      )}

      {/* ⚡ BARRA DE PACOTES DE ATALHO RÁPIDO (1 CLIQUE CALIBRADA) */}
      <div className="p-4 rounded-2xl bg-[#0b1222] border border-[#c5a059]/40 shadow-xl space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-black text-[#c5a059] uppercase tracking-wider flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-[#c5a059]" /> Pacotes de Atalho Rápido (1 Clique):
          </span>
          <span className="text-[10px] text-slate-400">Preenchimento instantâneo</span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => aplicarPacote('completo')}
            className="px-3.5 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/50 text-amber-300 text-xs font-black transition-all shadow-sm"
          >
            🌟 Pacote Completo (Foto + Vídeo + Drone + Paspatur + Cardápio + Banda)
          </button>
          <button
            type="button"
            onClick={() => aplicarPacote('almoco')}
            className="px-3 py-1.5 rounded-xl bg-orange-500/15 hover:bg-orange-500/25 border border-orange-500/40 text-orange-300 text-xs font-bold transition-all"
          >
            🍽️ Almoço Oficial
          </button>
          <button
            type="button"
            onClick={() => aplicarPacote('reels')}
            className="px-3 py-1.5 rounded-xl bg-pink-500/15 hover:bg-pink-500/25 border border-pink-500/40 text-pink-300 text-xs font-bold transition-all"
          >
            📱 Mídias & Reels
          </button>
          <button
            type="button"
            onClick={() => aplicarPacote('paspatur')}
            className="px-3 py-1.5 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-xs font-bold transition-all"
          >
            🖼️ Paspatur
          </button>
          <button
            type="button"
            onClick={() => aplicarPacote('discurso')}
            className="px-3 py-1.5 rounded-xl bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/40 text-purple-300 text-xs font-bold transition-all"
          >
            📜 Discurso & Redação
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* BLOCO 1: SOLICITANTE */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
          <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
            1. Dados do Solicitante & Setor
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Nome do Solicitante *</label>
              <input
                type="text"
                required
                value={formData.solicitante_nome}
                onChange={(e) => setFormData({ ...formData, solicitante_nome: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Setor / Organização Militar *</label>
              <input
                type="text"
                required
                value={formData.setor}
                onChange={(e) => setFormData({ ...formData, setor: e.target.value })}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">Contato / Ramal / WhatsApp</label>
              <input
                type="text"
                value={formData.contato}
                onChange={(e) => setFormData({ ...formData, contato: e.target.value })}
                placeholder="Ex: (21) 99876-5432 / Ramal 5510"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
              />
            </div>
          </div>
        </div>

        {/* BLOCO 2: DETALHES DO EVENTO & DATAS FLEXÍVEIS */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
              2. Detalhes da Pauta, Cronograma & Local
            </h2>

            {/* Seletor de Tipo de Data */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800">
              <button
                type="button"
                onClick={() => setTipoData('unica')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  tipoData === 'unica'
                    ? 'bg-[#c5a059] text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                📅 Data Única
              </button>
              <button
                type="button"
                onClick={() => setTipoData('periodo')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  tipoData === 'periodo'
                    ? 'bg-[#c5a059] text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🗓️ Período (Multi-Dias)
              </button>
              <button
                type="button"
                onClick={() => setTipoData('sem_data')}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  tipoData === 'sem_data'
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                ⏳ Sem Data Fixa (A Definir)
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">Título Oficial da Pauta / Evento *</label>
            <input
              type="text"
              required
              value={formData.titulo_evento}
              onChange={(e) => setFormData({ ...formData, titulo_evento: e.target.value })}
              placeholder="Ex: Cerimônia de Passagem de Comando do CGCFN"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          {/* Seletores de Data Conforme o Modo */}
          {tipoData === 'unica' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Data do Evento *</label>
                <input
                  type="date"
                  required
                  value={formData.data_evento}
                  onChange={(e) => setFormData({ ...formData, data_evento: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Horário Previsto *</label>
                <input
                  type="time"
                  required
                  value={formData.hora_evento}
                  onChange={(e) => setFormData({ ...formData, hora_evento: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>
            </div>
          )}

          {tipoData === 'periodo' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Data de Início *</label>
                <input
                  type="date"
                  required
                  value={formData.data_evento}
                  onChange={(e) => setFormData({ ...formData, data_evento: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Data de Término *</label>
                <input
                  type="date"
                  required
                  value={formData.data_fim || formData.data_evento}
                  onChange={(e) => setFormData({ ...formData, data_fim: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-300 mb-1">Horário Previsto</label>
                <input
                  type="time"
                  value={formData.hora_evento}
                  onChange={(e) => setFormData({ ...formData, hora_evento: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-[#c5a059]"
                />
              </div>
            </div>
          )}

          {tipoData === 'sem_data' && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
              <Clock className="w-4 h-4 shrink-0" />
              <span>
                <strong>Pauta sem Data Fixa:</strong> Esta solicitação será registrada como missão futura e exibida no Quadro de Demandas Pendentes de Agendamento.
              </span>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">Local Exato do Evento</label>
            <input
              type="text"
              value={formData.local_evento}
              onChange={(e) => setFormData({ ...formData, local_evento: e.target.value })}
              placeholder="Ex: Pátio de Formatura - Fortaleza de São José, Ilha das Cobras"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
            />
          </div>
        </div>

        {/* BLOCO 3: CATEGORIAS & SERVIÇOS COMPLETOS (COM DESIGN, IMPRESSOS, TEXTO, MÚSICA) */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-5 shadow-xl">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
              3. Serviços, Coberturas & Peças Requeridas
            </h2>
            <span className="px-2.5 py-0.5 rounded-lg bg-blue-500/20 text-blue-300 text-xs font-black border border-blue-500/40">
              Score Estimado: {calculateScore()} pts
            </span>
          </div>

          <div className="space-y-4">
            {CATEGORIAS_SERVICOS.map((cat) => (
              <div key={cat.id} className="space-y-2">
                <span className="text-xs font-black text-slate-300 block">{cat.titulo}</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                  {cat.servicos.map((serv) => {
                    const isSelected = formData.tipo_cobertura.includes(serv.id);
                    return (
                      <button
                        key={serv.id}
                        type="button"
                        onClick={() => handleToggleCoverage(serv.id)}
                        className={`p-3 rounded-2xl border text-left flex items-center gap-3 transition-all ${
                          isSelected
                            ? 'bg-[#c5a059]/15 border-[#c5a059] ring-1 ring-[#c5a059]/50 text-white shadow-md'
                            : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <serv.icon
                          className={`w-4 h-4 shrink-0 ${isSelected ? 'text-[#c5a059]' : 'text-slate-500'}`}
                        />
                        <span className="text-xs font-bold">{serv.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* BLOCO 4: MILITARES DESIGNADOS & ESCALAÇÃO (COMSOC & DESIGN PRINCIPAIS) */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-2">
              <Users className="w-4 h-4 text-[#00e5ff]" />
              4. Militares Designados / Equipe Escalada ({selectedMilitares.length} selecionados)
            </h2>

            {/* Toggle de Visualização: COMSOC vs Todo Efetivo */}
            <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800">
              <button
                type="button"
                onClick={() => setEquipeFilter('comsoc')}
                className={`px-3 py-1 rounded-lg text-[11px] font-black transition-all ${
                  equipeFilter === 'comsoc'
                    ? 'bg-[#c5a059] text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🌟 Equipe COMSOC & Design ({militares.filter((m) => m.isComsoc).length})
              </button>
              <button
                type="button"
                onClick={() => setEquipeFilter('todos')}
                className={`px-3 py-1 rounded-lg text-[11px] font-bold transition-all ${
                  equipeFilter === 'todos'
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🏢 Todo o Efetivo ({militares.length})
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-56 overflow-y-auto pr-1 scrollbar-none">
            {militares
              .filter((m) => (equipeFilter === 'comsoc' ? m.isComsoc : true))
              .map((mil) => {
                const isSelected = selectedMilitares.includes(mil.id);
                const isComsocRole = mil.isComsoc;

                return (
                  <button
                    key={mil.id}
                    type="button"
                    onClick={() => handleToggleMilitar(mil.id)}
                    className={`p-2.5 rounded-xl border text-left transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'bg-emerald-500/20 border-emerald-500/60 text-white shadow-md'
                        : isComsocRole
                        ? 'bg-slate-900 border-cyan-500/30 text-slate-200 hover:border-cyan-400'
                        : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] text-slate-400 font-bold truncate">
                        {mil.posto_grad || 'MILITAR'}
                      </span>
                      {isComsocRole && (
                        <span className="text-[8px] font-black uppercase px-1 py-0.2 rounded bg-cyan-500/20 text-cyan-300">
                          {mil.role === 'comsoc_design' ? 'DESIGN' : mil.role === 'admin' ? 'ADMIN' : 'COMSOC'}
                        </span>
                      )}
                    </div>

                    <p className="text-xs font-black text-white truncate mt-0.5">{mil.nome_guerra}</p>

                    <div className="flex items-center justify-between mt-1 text-[9px]">
                      <span className="text-slate-500 truncate">{mil.setor || 'Gabinete'}</span>
                      {isSelected && <UserCheck className="w-3 h-3 text-emerald-400 shrink-0" />}
                    </div>
                  </button>
                );
              })}
          </div>
        </div>

        {/* BLOCO 5: AUTORIDADES, PASTA DRIVE & OBSERVAÇÕES */}
        <div className="p-6 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
          <h2 className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
            5. Autoridades, Pasta do Google Drive & Observações
          </h2>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Autoridades Presentes / Presidência da Cerimônia
            </label>
            <input
              type="text"
              value={formData.autoridades}
              onChange={(e) => setFormData({ ...formData, autoridades: e.target.value })}
              placeholder="Ex: Comandante da Marinha, Comandante-Geral do CFN, Diretores..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          {/* Seção de Integração Google Drive */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-slate-300">
                Link da Pasta no Google Drive / Nuvem
              </label>

              <div className="flex items-center gap-2">
                {formData.drive_url && (
                  <a
                    href={formData.drive_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 px-2.5 py-1 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 text-blue-300 text-[11px] font-bold transition-all"
                  >
                    <ExternalLink className="w-3 h-3" />
                    <span>Abrir Pasta</span>
                  </a>
                )}

                <button
                  type="button"
                  disabled={creatingDrive}
                  onClick={handleGerarPastaDrive}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/40 text-cyan-300 text-[11px] font-bold transition-all disabled:opacity-50"
                >
                  <FolderPlus className="w-3.5 h-3.5" />
                  <span>{creatingDrive ? 'Criando no Drive...' : '⚡ Criar Pasta Oficial no Drive'}</span>
                </button>
              </div>
            </div>

            <div className="relative">
              <LinkIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={formData.drive_url}
                onChange={(e) => setFormData({ ...formData, drive_url: e.target.value })}
                placeholder="https://drive.google.com/drive/folders/..."
                className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 mb-1">
              Observações Específicas / Roteiro
            </label>
            <textarea
              rows={3}
              value={formData.observacoes}
              onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
              placeholder="Descreva detalhes como pontos de captação, formato de entrega das artes ou trajes exigidos..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-[#c5a059]"
            />
          </div>

          {/* Toggle Sigiloso */}
          <label className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.sigiloso}
              onChange={(e) => setFormData({ ...formData, sigiloso: e.target.checked })}
              className="rounded bg-slate-900 border-slate-700 text-[#c5a059] focus:ring-0"
            />
            <span className="text-xs font-bold text-slate-300">
              🔒 Evento Sigiloso / Acesso Restrito (Exibir apenas para Oficiais e Homologadores)
            </span>
          </label>
        </div>

        {/* Botões de Ação */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 text-xs font-bold transition-all"
          >
            Cancelar
          </button>

          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 text-xs font-black shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>
              {submitting
                ? 'Gravando Alterações...'
                : editId
                ? 'Salvar Alterações da Demanda'
                : 'Cadastrar Demanda'}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
};
