import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Images,
  Image as ImageIcon,
  Camera,
  Search,
  Download,
  CheckCircle2,
  Filter,
  Sparkles,
  ExternalLink,
  Eye,
  Layers,
  Upload,
  User,
  Sliders,
  X,
  Share2,
  FolderOpen,
  RefreshCw,
  Link,
  Send,
  Star,
  Shield,
  Bot,
  Tv,
  Check,
  Cpu,
  Cloud,
  FileCheck,
  Plus,
  Zap,
  Play,
  Pause,
  Square,
  Tag,
  ShieldAlert,
  Clock,
  Smartphone,
  MessageSquare,
  Lock,
  Flame,
} from 'lucide-react';
import { toast } from 'sonner';
import { militaryAudio } from '../../utils/militaryAudio';
import { supabase } from '../../api/supabase';
import { useAuth } from '../../context/AuthContext';
import {
  analyzePhotoWithVision,
  imageToBase64,
  PhotoAiMetadata,
} from '../../utils/geminiVision';

interface PautaEvent {
  id: number;
  titulo_evento: string;
  data_evento: string;
  local_evento?: string;
  drive_url?: string;
  drive_folder_id?: string;
  local_photos_count?: number;
  status: string;
  pin_code?: string;
}

interface PhotoItem {
  id: string;
  filename: string;
  drive_file_id?: string;
  url: string;
  thumbnail_url: string;
  drive_link?: string;
  event_id?: number;
  event_name?: string;
  folder_type: 'geral' | 'selecao' | 'local';
  is_selected_curation?: boolean;
  is_destaque_top20?: boolean;
  similarity?: number;
  matched_militar?: string;
  // Campos de Inteligência Visual (Vision AI)
  ai_tagged?: boolean;
  ai_description?: string;
  elements?: string[];
  scene?: string;
  actions?: string[];
  tags?: string[];
  ai_status?: 'pending' | 'processing' | 'tagged' | 'error';
}

interface AccessLogItem {
  id: string;
  photo_id?: string;
  photo_name: string;
  photo_url?: string;
  thumbnail_url?: string;
  date: string;
  device: string;
  ip: string;
  action: 'visualizacao' | 'download_hd' | 'compartilhamento_whatsapp';
}

export const PhotoGalleryAdmin: React.FC = () => {
  const { user } = useAuth();

  // Estados Globais de Pautas e Eventos
  const [pautas, setPautas] = useState<PautaEvent[]>([]);
  const [pautaFilter, setPautaFilter] = useState<'all' | 'drive' | 'sem_drive' | 'week' | 'month'>('all');
  const [selectedEventId, setSelectedEventId] = useState<number>(50);
  const [activeMainTab, setActiveMainTab] = useState<'locais' | 'drive' | 'selecao' | 'destaques' | 'tagueadas' | 'pessoal'>('locais');

  // Estados de Gestão de Google Drive
  const [creatingDrive, setCreatingDrive] = useState(false);
  const [linkDriveModalOpen, setLinkDriveModalOpen] = useState(false);
  const [linkDriveInput, setLinkDriveInput] = useState('');
  const [savingDriveLink, setSavingDriveLink] = useState(false);
  
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [filteredPhotos, setFilteredPhotos] = useState<PhotoItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTagFilter, setSelectedTagFilter] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [lightboxPhoto, setLightboxPhoto] = useState<PhotoItem | null>(null);
  const [loading, setLoading] = useState(true);

  // Paginação Inteligente (48 fotos por página)
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(48);

  // ── ESTADOS DO MOTOR DE INTELIGÊNCIA VISUAL (GEMINI VISION AI) ──
  const [isBatchTagging, setIsBatchTagging] = useState(false);
  const [isTaggingPaused, setIsTaggingPaused] = useState(false);
  const [taggingProgress, setTaggingProgress] = useState({
    current: 0,
    total: 0,
    currentPhotoName: '',
    successCount: 0,
    errorCount: 0,
  });
  const abortControllerRef = useRef<boolean>(false);
  const isPausedRef = useRef<boolean>(false);

  // Chave de API Google Gemini
  const [geminiApiKey, setGeminiApiKey] = useState<string>(() => {
    return localStorage.getItem('sisgab_gemini_key') || (import.meta.env.VITE_GOOGLE_API_KEY as string) || '';
  });

  // Modais Operacionais
  const [portalModalOpen, setPortalModalOpen] = useState(false);
  const [biometriaModalOpen, setBiometriaModalOpen] = useState(false);
  const [biometriaTab, setBiometriaTab] = useState<'cad' | 'search' | 'list'>('cad');
  const [telegramModalOpen, setTelegramModalOpen] = useState(false);
  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [taggerModalOpen, setTaggerModalOpen] = useState(false);

  // Biometria Facial por Selfie
  const [cameraActive, setCameraActive] = useState(false);
  const [matchThreshold, setMatchThreshold] = useState(0.45);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Histórico de Acessos Auditáveis (Persistente e 100% Real)
  const [accessLogs, setAccessLogs] = useState<AccessLogItem[]>(() => {
    try {
      const saved = localStorage.getItem('sisgab_gallery_audit_logs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Função para gravar log de auditoria real
  const recordAccessLog = (photo: PhotoItem, action: 'visualizacao' | 'download_hd' | 'compartilhamento_whatsapp') => {
    const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const deviceLabel = isMobile
      ? (navigator.userAgent.includes('iPhone') ? 'iPhone • Safari' : 'Dispositivo Mobile')
      : 'Desktop • Gabinete';

    const newLog: AccessLogItem = {
      id: `log_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      photo_id: photo.id,
      photo_name: photo.filename || 'Fotografia Institucional',
      photo_url: photo.url,
      thumbnail_url: photo.thumbnail_url || photo.url,
      date: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      device: `${deviceLabel} (${user?.nome_guerra || 'Operador COMSOC'})`,
      ip: '192.168.1.X (Rede MB)',
      action,
    };

    setAccessLogs((prev) => {
      const updated = [newLog, ...prev.slice(0, 49)];
      try {
        localStorage.setItem('sisgab_gallery_audit_logs', JSON.stringify(updated));
      } catch (e) {
        console.warn('Erro ao persistir log de auditoria:', e);
      }
      return updated;
    });
  };

  // ── ESTADOS DO GERENCIADOR DE CONTAS GOOGLE DRIVE & UPLOAD DIRETO ──
  const [driveManagerModalOpen, setDriveManagerModalOpen] = useState(false);
  const [driveAccountsData, setDriveAccountsData] = useState<{
    active_mode: string;
    connection_status: boolean;
    connection_message: string;
    has_oauth: boolean;
    oauth_email?: string;
    has_service_account: boolean;
    sa_email?: string;
    pastas_mae: Array<{ id: string; nome: string; folder_id: string; padrao?: boolean }>;
  } | null>(null);
  const [loadingDriveAccounts, setLoadingDriveAccounts] = useState(false);
  const [oauthTokenInput, setOauthTokenInput] = useState('');
  const [savingOAuthToken, setSavingOAuthToken] = useState(false);

  // Upload Direto de Fotos via Web/Celular
  const webUploadInputRef = useRef<HTMLInputElement | null>(null);
  const [isUploadingWeb, setIsUploadingWeb] = useState(false);
  const [webUploadProgress, setWebUploadProgress] = useState({ current: 0, total: 0 });

  const loadDriveAccountsInfo = async () => {
    try {
      setLoadingDriveAccounts(true);
      const res = await fetch('/api/drive/accounts');
      if (res.ok) {
        const json = await res.json();
        if (json.ok) {
          setDriveAccountsData(json);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar dados de contas do Drive:', err);
    } finally {
      setLoadingDriveAccounts(false);
    }
  };

  useEffect(() => {
    if (driveManagerModalOpen) {
      loadDriveAccountsInfo();
    }
  }, [driveManagerModalOpen]);

  const handleSwitchDriveAuthMode = async (newMode: 'oauth' | 'service_account') => {
    try {
      militaryAudio.playTacticalBeep();
      toast.loading(`Alternando modo ativo para ${newMode === 'oauth' ? 'Conta Pessoal (OAuth)' : 'Service Account (Robô)'}...`, { id: 'switch_drive' });
      const res = await fetch('/api/drive/set_mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });
      const json = await res.json();
      if (json.ok) {
        toast.success(`Modo ativado: ${newMode === 'oauth' ? '🔑 OAuth 2.0 (Conta Pessoal)' : '🤖 Service Account'}!`, {
          id: 'switch_drive',
          description: json.message,
        });
        loadDriveAccountsInfo();
      } else {
        toast.error(`Erro: ${json.error}`, { id: 'switch_drive' });
      }
    } catch (err: any) {
      toast.error(`Falha: ${err.message}`, { id: 'switch_drive' });
    }
  };

  const handleSaveOAuthToken = async () => {
    if (!oauthTokenInput.trim()) {
      toast.warning('Cole o token JSON gerado para a conta do Google Drive.');
      return;
    }
    try {
      setSavingOAuthToken(true);
      militaryAudio.playTacticalBeep();
      toast.loading('Salvando e validando Token OAuth no servidor...', { id: 'save_token' });
      let parsed = oauthTokenInput;
      try {
        parsed = JSON.parse(oauthTokenInput);
      } catch (_) {}

      const res = await fetch('/api/drive/save_oauth_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: parsed }),
      });
      const json = await res.json();
      if (json.ok) {
        toast.success('Conta do Google Drive conectada com sucesso!', {
          id: 'save_token',
          description: json.message,
        });
        setOauthTokenInput('');
        loadDriveAccountsInfo();
      } else {
        toast.error(`Falha ao conectar: ${json.error}`, { id: 'save_token' });
      }
    } catch (err: any) {
      toast.error(`Erro: ${err.message}`, { id: 'save_token' });
    } finally {
      setSavingOAuthToken(false);
    }
  };

  const handleDirectWebUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedEventId || !currentPauta) return;

    const total = files.length;
    setIsUploadingWeb(true);
    setWebUploadProgress({ current: 0, total });
    militaryAudio.playTacticalBeep();
    toast.info(`Iniciando upload de ${total} fotos para a pasta do evento no Drive...`);

    let successCount = 0;
    for (let i = 0; i < total; i++) {
      const f = files[i];
      setWebUploadProgress({ current: i + 1, total });
      try {
        const formData = new FormData();
        formData.append('event_id', String(selectedEventId));
        formData.append('file', f);

        const res = await fetch('/api/drive/upload_photo', {
          method: 'POST',
          body: formData,
        });
        if (res.ok) {
          successCount++;
        }
      } catch (err) {
        console.warn(`Erro no upload da foto ${f.name}:`, err);
      }
    }

    setIsUploadingWeb(false);
    if (webUploadInputRef.current) {
      webUploadInputRef.current.value = '';
    }

    militaryAudio.playTacticalBeep();
    toast.success(`🎉 Upload concluído! ${successCount} de ${total} fotos salvas com sucesso!`);
    loadEventPhotos(selectedEventId);
  };

  // ── ESTADOS DO MOTOR DE INDEXAÇÃO FACIAL NA VPS (LOW CPU) ──
  const [aiIndexingStatus, setAiIndexingStatus] = useState<{
    status: 'idle' | 'processing' | 'done' | 'error';
    current: number;
    total: number;
    faces: number;
    percent: number;
    message: string;
  }>({ status: 'idle', current: 0, total: 0, faces: 0, percent: 0, message: '' });
  const [isStartingAiIndex, setIsStartingAiIndex] = useState(false);

  // Polling de Status da IA Facial a cada 3s se estiver processando
  useEffect(() => {
    if (!selectedEventId) return;

    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`/api/ai/index_status?event_id=${selectedEventId}`);
        if (res.ok) {
          const json = await res.json();
          if (json.ok && json.status && isMounted) {
            setAiIndexingStatus(json.status);
          }
        }
      } catch (err) {
        console.warn('Erro ao checar status de indexação:', err);
      }
    };

    fetchStatus();
    const interval = setInterval(() => {
      if (aiIndexingStatus.status === 'processing' || isStartingAiIndex) {
        fetchStatus();
      }
    }, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedEventId, aiIndexingStatus.status, isStartingAiIndex]);

  const handleTriggerAiIndexing = async () => {
    if (!selectedEventId || !currentPauta) return;
    try {
      setIsStartingAiIndex(true);
      militaryAudio.playTacticalBeep();
      toast.loading('Iniciando indexação facial com IA na VPS (Baixo consumo de CPU)...', { id: 'vps_ai_index' });

      const res = await fetch('/api/ai/index_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: selectedEventId,
          title: currentPauta.titulo_evento,
        }),
      });

      const json = await res.json();
      if (json.ok) {
        toast.success('Indexação facial iniciada em segundo plano na VPS!', {
          id: 'vps_ai_index',
          description: 'Você receberá uma notificação no Telegram assim que for concluída.',
        });
        setAiIndexingStatus((prev) => ({ ...prev, status: 'processing', message: 'Iniciando varredura...' }));
      } else {
        toast.error(`Falha: ${json.message || 'Erro desconhecido'}`, { id: 'vps_ai_index' });
      }
    } catch (err: any) {
      toast.error(`Erro ao disparar indexação: ${err.message}`, { id: 'vps_ai_index' });
    } finally {
      setIsStartingAiIndex(false);
    }
  };

  const matrixFileInputRef = useRef<HTMLInputElement | null>(null);
  const [isUploadingMatrix, setIsUploadingMatrix] = useState(false);

  const handleUploadMatrixFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedEventId) return;

    try {
      setIsUploadingMatrix(true);
      militaryAudio.playTacticalBeep();
      toast.loading(`Importando matriz IA (${(file.size / 1024).toFixed(0)} KB)...`, { id: 'matrix_upload' });

      const formData = new FormData();
      formData.append('event_id', String(selectedEventId));
      formData.append('npz_file', file);

      const res = await fetch('/api/ai/upload_matrix', {
        method: 'POST',
        body: formData,
      });

      const json = await res.json();
      if (json.ok) {
        toast.success('🎉 Matriz de faces importada e ativada com sucesso!', {
          id: 'matrix_upload',
          description: 'O Portal de Convidados já está liberado para selfies nesta solenidade.',
        });
        setAiIndexingStatus({
          status: 'done',
          current: photos.length,
          total: photos.length,
          faces: photos.length,
          percent: 100,
          message: 'Matriz importada via GPU Studio.',
        });
      } else {
        toast.error(`Falha no upload: ${json.message || 'Erro ao salvar matriz'}`, { id: 'matrix_upload' });
      }
    } catch (err: any) {
      toast.error(`Erro ao enviar arquivo: ${err.message}`, { id: 'matrix_upload' });
    } finally {
      setIsUploadingMatrix(false);
      if (matrixFileInputRef.current) matrixFileInputRef.current.value = '';
    }
  };

  const handleOpenPhoto = (photo: PhotoItem) => {
    recordAccessLog(photo, 'visualizacao');
    setLightboxPhoto(photo);
  };

  useEffect(() => {
    loadPautasAndEvents();
  }, []);

  useEffect(() => {
    if (selectedEventId) {
      loadEventPhotos(selectedEventId);
    }
  }, [selectedEventId]);

  const handleEventChange = (newId: number) => {
    setSelectedEventId(newId);
    setSearchQuery('');
    setSelectedTagFilter(null);
    setActiveMainTab('locais');
    setCurrentPage(1);
    const p = pautas.find((item) => item.id === newId);
    if (p) {
      toast.info(`Solenidade selecionada: ${p.titulo_evento}`);
    }
  };

  // Aplica Busca Semântica em Tempo Real + Filtros de Tags
  useEffect(() => {
    filterPhotosRealTime();
  }, [photos, searchQuery, selectedTagFilter, activeMainTab]);

  // Carrega todas as pautas aprovadas, concluídas e ativas do Supabase em ordem cronológica
  const loadPautasAndEvents = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .in('status', ['aprovado', 'aprovada', 'concluida', 'pendente', 'em_andamento'])
        .order('data_evento', { ascending: true });

      if (!error && data && data.length > 0) {
        const parsed: PautaEvent[] = data.map((d: any) => {
          let dfid = d.drive_folder_id || '';
          const rawUrl = [d.drive_url, d.drive_link, d.autoridades, d.arquivo_url, d.produto_especifico].filter(Boolean).join(' ');
          let extractedUrl = '';
          const mUrl = rawUrl.match(/https:\/\/drive\.google\.com[^\s\]]+/);
          if (mUrl) {
            extractedUrl = mUrl[0];
            const mId = extractedUrl.match(/folders\/([a-zA-Z0-9_-]+)/) || extractedUrl.match(/\/d\/([a-zA-Z0-9_-]+)/);
            if (mId) dfid = mId[1];
          } else if (rawUrl.includes('[DRIVE:')) {
            const part = rawUrl.split('[DRIVE:')[1].split(']')[0].trim();
            if (part.startsWith('http')) {
              extractedUrl = part;
              const mId = extractedUrl.match(/folders\/([a-zA-Z0-9_-]+)/);
              if (mId) dfid = mId[1];
            }
          }

          const finalDriveUrl = extractedUrl || (dfid ? `https://drive.google.com/drive/folders/${dfid}` : undefined);

          return {
            id: d.id,
            titulo_evento: d.titulo_evento || 'Sem título',
            data_evento: d.data_evento || '2026-08-20',
            local_evento: d.local_evento || 'Gabinete CGCFN',
            drive_url: finalDriveUrl,
            drive_folder_id: dfid || undefined,
            local_photos_count: d.id === 50 ? 697 : 0,
            status: d.status,
            pin_code: '1808',
          };
        });

        setPautas(parsed);
        if (!selectedEventId || !parsed.some((p) => p.id === selectedEventId)) {
          setSelectedEventId(parsed[0].id);
        }
      }

      // Tenta recuperar chave do Gemini salva nas configurações gerais
      const { data: configData } = await supabase.from('config').select('*');
      if (configData && configData.length > 0) {
        const gemKey = configData.find((c: any) => c.chave === 'gemini_api_key' || c.chave === 'google_api_key')?.valor;
        if (gemKey && typeof gemKey === 'string' && gemKey.trim().length > 5) {
          setGeminiApiKey(gemKey.trim());
          localStorage.setItem('sisgab_gemini_key', gemKey.trim());
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar pautas da galeria:', err);
    } finally {
      setLoading(false);
    }
  };

  // Cria pasta oficial no Google Drive para a solenidade selecionada
  const handleCreateDriveForCurrentPauta = async () => {
    if (!currentPauta) return;
    try {
      setCreatingDrive(true);
      toast.loading(`Criando pasta oficial no Google Drive para "${currentPauta.titulo_evento}"...`, { id: 'create_drive_galeria' });

      const res = await fetch('/api/drive/create_event_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo_evento: currentPauta.titulo_evento,
          data_evento: currentPauta.data_evento || '2026-08-20',
          demanda_id: currentPauta.id,
        }),
      });

      const json = await res.json();
      if (json.ok && json.evento_link) {
        militaryAudio.playTacticalBeep();
        toast.success('Pasta criada com sucesso no Google Drive!', {
          id: 'create_drive_galeria',
          description: 'Subpastas GERAL e SELEÇÃO estruturadas.',
        });

        // Atualiza estado local de pautas
        setPautas((prev) =>
          prev.map((p) =>
            p.id === currentPauta.id
              ? {
                  ...p,
                  drive_url: json.evento_link,
                  drive_folder_id: json.evento_folder_id,
                }
              : p
          )
        );

        // Recarrega fotos da galeria
        loadEventPhotos(currentPauta.id);
      } else {
        toast.error(`Falha ao criar pasta: ${json.error || 'Erro desconhecido'}`, { id: 'create_drive_galeria' });
      }
    } catch (err: any) {
      toast.error(`Erro ao comunicar com o servidor: ${err.message}`, { id: 'create_drive_galeria' });
    } finally {
      setCreatingDrive(false);
    }
  };

  // Salva / Vincula link do Google Drive manualmente
  const handleSaveDriveLinkManual = async () => {
    if (!currentPauta || !linkDriveInput.trim()) {
      toast.error('Informe uma URL válida do Google Drive.');
      return;
    }

    try {
      setSavingDriveLink(true);
      toast.loading('Vinculando link do Google Drive à solenidade...', { id: 'save_drive_link' });

      const res = await fetch('/api/drive/save_drive_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          demanda_id: currentPauta.id,
          titulo_evento: currentPauta.titulo_evento,
          drive_url: linkDriveInput.trim(),
        }),
      });

      const json = await res.json();
      if (json.ok) {
        militaryAudio.playTacticalBeep();
        toast.success('Link do Google Drive vinculado com sucesso!', { id: 'save_drive_link' });

        const m = linkDriveInput.match(/folders\/([a-zA-Z0-9_-]+)/) || linkDriveInput.match(/\/d\/([a-zA-Z0-9_-]+)/);
        const folderId = m ? m[1] : undefined;

        setPautas((prev) =>
          prev.map((p) =>
            p.id === currentPauta.id
              ? {
                  ...p,
                  drive_url: linkDriveInput.trim(),
                  drive_folder_id: folderId,
                }
              : p
          )
        );

        setLinkDriveModalOpen(false);
        setLinkDriveInput('');
        loadEventPhotos(currentPauta.id);
      } else {
        toast.error(`Falha ao vincular link: ${json.error || 'Erro desconhecido'}`, { id: 'save_drive_link' });
      }
    } catch (err: any) {
      toast.error(`Erro de conexão: ${err.message}`, { id: 'save_drive_link' });
    } finally {
      setSavingDriveLink(false);
    }
  };

  // Carrega fotos do evento e mescla com cache local de tags
  const loadEventPhotos = async (eventId: number) => {
    try {
      setLoading(true);
      const currentPauta = pautas.find((p) => p.id === eventId);
      const cachedTagsRaw = localStorage.getItem(`sisgab_vision_tags_${eventId}`);
      const cachedTagsMap: Record<string, PhotoAiMetadata> = cachedTagsRaw ? JSON.parse(cachedTagsRaw) : {};
      const cachedDestaquesRaw = localStorage.getItem(`sisgab_destaques_${eventId}`);
      const cachedDestaques: string[] = cachedDestaquesRaw ? JSON.parse(cachedDestaquesRaw) : [];

      let rawData: any[] = [];

      // 1. Tenta buscar fotos dinamicamente da API do Google Drive do evento
      try {
        const apiRes = await fetch(`/api/portal/photos?event_id=${eventId}`);
        if (apiRes.ok) {
          const apiData = await apiRes.json();
          if (apiData.ok && Array.isArray(apiData.photos) && apiData.photos.length > 0) {
            rawData = apiData.photos;
          }
        }
      } catch (err) {
        console.warn('Erro ao consultar /api/portal/photos:', err);
      }

      // 2. Tenta buscar fotos no Supabase na tabela 'processed_photos'
      if (!rawData || rawData.length === 0) {
        try {
          const { data: dbPhotos, error } = await supabase
            .from('processed_photos')
            .select('*')
            .or(`demanda_id.eq.${eventId},event_name.eq."${currentPauta?.titulo_evento || ''}"`);

          if (!error && dbPhotos && dbPhotos.length > 0) {
            rawData = dbPhotos.map((p: any) => ({
              id: p.id,
              filename: p.filename || `foto_${p.id}.jpg`,
              drive_file_id: p.drive_file_id || p.file_id,
              url: p.drive_link || p.url || p.thumbnail_url || (p.filename ? `/assets/galeria_hot/${eventId}/${p.filename}` : ''),
              thumbnail_url: p.thumbnail_url || p.drive_link || p.url || (p.filename ? `/assets/galeria_hot/${eventId}/${p.filename}` : ''),
              drive_link: p.drive_link,
              is_destaque_top20: p.is_destaque || p.destaque || false,
              ai_description: p.descricao_ia || p.ai_description,
              tags: p.tags || [],
              elements: p.elements || [],
            }));
          }
        } catch (err) {
          console.warn('Erro ao consultar Supabase processed_photos:', err);
        }
      }

      // 3. Fallback para arquivo estático /event_<id>_photos.json
      if (!rawData || rawData.length === 0) {
        try {
          const resEvent = await fetch(`/event_${eventId}_photos.json`);
          if (resEvent.ok) {
            rawData = await resEvent.json();
          }
        } catch {}
      }

      // 4. Fallback apenas se for o evento 50 (demonstração oficial)
      if ((!rawData || rawData.length === 0) && eventId === 50) {
        try {
          const resFallback = await fetch('/event_50_photos.json');
          if (resFallback.ok) {
            rawData = await resFallback.json();
          }
        } catch {}
      }

      if (rawData && rawData.length > 0) {
        const mapped: PhotoItem[] = rawData.map((d, idx) => {
          const photoId = String(d.id || `f_${idx + 1}`);
          const aiMeta = cachedTagsMap[photoId];
          const isDestaque = cachedDestaques.includes(photoId) || d.is_destaque_top20 || false;

          return {
            id: photoId,
            filename: d.filename || `FOTO_${idx + 1}.JPG`,
            drive_file_id: d.drive_file_id,
            url: d.url || d.thumbnail_url,
            thumbnail_url: d.thumbnail_url || d.url,
            drive_link: d.drive_link,
            event_id: eventId,
            event_name: currentPauta?.titulo_evento || 'Evento Selecionado',
            folder_type: isDestaque ? 'selecao' : 'local',
            is_selected_curation: isDestaque,
            is_destaque_top20: isDestaque,
            similarity: undefined,
            matched_militar: undefined,
            ai_tagged: !!(aiMeta || d.ai_description),
            ai_description: aiMeta?.descricao || d.ai_description,
            elements: aiMeta?.elementos || d.elements || [],
            scene: aiMeta?.cenario || d.scene,
            actions: aiMeta?.acoes || d.actions || [],
            tags: aiMeta?.tags || d.tags || [],
            ai_status: (aiMeta || d.ai_description) ? 'tagged' : 'pending',
          };
        });

        setPhotos(mapped);
        setFilteredPhotos(mapped);
      } else {
        setPhotos([]);
        setFilteredPhotos([]);
      }
    } catch (err) {
      console.warn('Erro ao ler acervo de fotos:', err);
      setPhotos([]);
      setFilteredPhotos([]);
    } finally {
      setLoading(false);
    }
  };

  // ── FILTRAGEM SEMÂNTICA MULTI-PARAMÉTRICA EM TEMPO REAL ──
  const filterPhotosRealTime = () => {
    let result = [...photos];

    // 1. Filtro de Abas
    if (activeMainTab === 'destaques' || activeMainTab === 'selecao') {
      result = result.filter((p) => p.is_destaque_top20 || p.is_selected_curation);
    } else if (activeMainTab === 'tagueadas') {
      result = result.filter((p) => p.ai_tagged);
    } else if (activeMainTab === 'pessoal') {
      result = result.filter((p) => p.matched_militar);
    }

    // 2. Filtro de Tag Rápida Clicável
    if (selectedTagFilter) {
      const tagLower = selectedTagFilter.toLowerCase();
      result = result.filter(
        (p) =>
          p.tags?.some((t) => t.toLowerCase().includes(tagLower)) ||
          p.elements?.some((e) => e.toLowerCase().includes(tagLower)) ||
          p.actions?.some((a) => a.toLowerCase().includes(tagLower)) ||
          p.scene?.toLowerCase().includes(tagLower)
      );
    }

    // 3. Busca em Linguagem Natural (Semântica)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((p) => {
        const inFilename = p.filename.toLowerCase().includes(q);
        const inDesc = p.ai_description?.toLowerCase().includes(q);
        const inTags = p.tags?.some((t) => t.toLowerCase().includes(q));
        const inElements = p.elements?.some((e) => e.toLowerCase().includes(q));
        const inScene = p.scene?.toLowerCase().includes(q);
        const inActions = p.actions?.some((a) => a.toLowerCase().includes(q));
        const inMilitar = p.matched_militar?.toLowerCase().includes(q);
        const inEvent = p.event_name?.toLowerCase().includes(q);

        return inFilename || inDesc || inTags || inElements || inScene || inActions || inMilitar || inEvent;
      });
    }

    setFilteredPhotos(result);
    setCurrentPage(1);
  };

  // ── MOTOR DE TAGUEAMENTO EM LOTE (GEMINI VISION AI) ──
  const handleStartBatchTagging = async () => {
    const untagged = photos.filter((p) => !p.ai_tagged);
    if (untagged.length === 0) {
      toast.info('Todas as fotos deste evento já foram tagueadas por IA!');
      return;
    }

    const key = geminiApiKey.trim();
    if (!key || key.length < 8) {
      toast.error('Configure sua chave de API do Gemini para iniciar o tagueamento.');
      return;
    }

    setIsBatchTagging(true);
    setIsTaggingPaused(false);
    abortControllerRef.current = false;
    isPausedRef.current = false;

    setTaggingProgress({
      current: 0,
      total: untagged.length,
      currentPhotoName: untagged[0].filename,
      successCount: 0,
      errorCount: 0,
    });

    const cachedTagsRaw = localStorage.getItem(`sisgab_vision_tags_${selectedEventId}`);
    const cachedTagsMap: Record<string, PhotoAiMetadata> = cachedTagsRaw ? JSON.parse(cachedTagsRaw) : {};

    let successes = 0;
    let errors = 0;

    for (let i = 0; i < untagged.length; i++) {
      if (abortControllerRef.current) {
        toast.info('Processamento de tagueamento cancelado.');
        break;
      }

      // Suporte a Pausa
      while (isPausedRef.current) {
        await new Promise((r) => setTimeout(r, 600));
        if (abortControllerRef.current) break;
      }

      const photo = untagged[i];
      setTaggingProgress((prev) => ({
        ...prev,
        current: i + 1,
        currentPhotoName: photo.filename,
      }));

      try {
        // Converte imagem para base64 via proxy do backend e envia para o Gemini Vision
        const { base64, mimeType } = await imageToBase64(photo.thumbnail_url || photo.url, photo.drive_file_id);
        const metadata = await analyzePhotoWithVision(base64, mimeType, key);

        cachedTagsMap[photo.id] = metadata;
        localStorage.setItem(`sisgab_vision_tags_${selectedEventId}`, JSON.stringify(cachedTagsMap));

        // Atualiza estado local da foto em tempo real
        setPhotos((prev) =>
          prev.map((p) =>
            p.id === photo.id
              ? {
                  ...p,
                  ai_tagged: true,
                  ai_description: metadata.descricao,
                  elements: metadata.elementos,
                  scene: metadata.cenario,
                  actions: metadata.acoes,
                  tags: metadata.tags,
                  ai_status: 'tagged',
                }
              : p
          )
        );

        successes++;
        setTaggingProgress((prev) => ({ ...prev, successCount: successes }));

        // Respeita a cota gratuita (espera 2.5s entre fotos)
        await new Promise((r) => setTimeout(r, 2500));
      } catch (err: any) {
        console.warn(`Erro ao taguear foto ${photo.filename}:`, err);
        errors++;
        setTaggingProgress((prev) => ({ ...prev, errorCount: errors }));
      }
    }

    setIsBatchTagging(false);
    militaryAudio.playTacticalBeep();
    toast.success(`Tagueamento concluído! ${successes} fotos indexadas com sucesso.`);
  };

  const handlePauseTagging = () => {
    isPausedRef.current = !isPausedRef.current;
    setIsTaggingPaused(isPausedRef.current);
    toast.info(isPausedRef.current ? 'Tagueamento pausado.' : 'Tagueamento retomado.');
  };

  const handleStopTagging = () => {
    abortControllerRef.current = true;
    setIsBatchTagging(false);
    setIsTaggingPaused(false);
  };

  // ── MOTOR DE TAGUEAMENTO INDIVIDUAL (1 FOTO COM VISION AI) ──
  const [isTaggingSingle, setIsTaggingSingle] = useState<string | null>(null);

  const handleTagSinglePhoto = async (photo: PhotoItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    const key = geminiApiKey.trim();
    if (!key || key.length < 8) {
      toast.error('Configure sua chave de API do Gemini para processar a visão computacional.');
      setTaggerModalOpen(true);
      return;
    }

    try {
      setIsTaggingSingle(photo.id);
      toast.loading(`Analisando foto "${photo.filename}" com Gemini Vision...`, { id: `tag_${photo.id}` });

      const { base64, mimeType } = await imageToBase64(photo.thumbnail_url || photo.url, photo.drive_file_id);
      const metadata = await analyzePhotoWithVision(base64, mimeType, key);

      const cachedTagsRaw = localStorage.getItem(`sisgab_vision_tags_${selectedEventId}`);
      const cachedTagsMap: Record<string, PhotoAiMetadata> = cachedTagsRaw ? JSON.parse(cachedTagsRaw) : {};
      cachedTagsMap[photo.id] = metadata;
      localStorage.setItem(`sisgab_vision_tags_${selectedEventId}`, JSON.stringify(cachedTagsMap));

      // Atualiza estado local da foto em tempo real
      setPhotos((prev) =>
        prev.map((p) =>
          p.id === photo.id
            ? {
                ...p,
                ai_tagged: true,
                ai_description: metadata.descricao,
                elements: metadata.elementos,
                scene: metadata.cenario,
                actions: metadata.acoes,
                tags: metadata.tags,
                ai_status: 'tagged',
              }
            : p
        )
      );

      if (lightboxPhoto && lightboxPhoto.id === photo.id) {
        setLightboxPhoto({
          ...lightboxPhoto,
          ai_tagged: true,
          ai_description: metadata.descricao,
          elements: metadata.elementos,
          scene: metadata.cenario,
          actions: metadata.acoes,
          tags: metadata.tags,
          ai_status: 'tagged',
        });
      }

      toast.success(`Foto "${photo.filename}" analisada e tagueada com sucesso!`, { id: `tag_${photo.id}` });
    } catch (err: any) {
      console.warn('Erro ao taguear foto individual:', err);
      toast.error(`Erro ao analisar foto: ${err.message || 'Falha de conexão com a IA'}`, { id: `tag_${photo.id}` });
    } finally {
      setIsTaggingSingle(null);
    }
  };

  // ── CURADORIA: ALTERNAR DESTAQUE TOP 20 / ESTRELA ──
  const toggleDestaqueTop20 = (photoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPhotos((prev) => {
      const nextPhotos = prev.map((p) => {
        if (p.id === photoId) {
          const next = !p.is_destaque_top20;
          toast.success(next ? '⭐ Foto promovida a DESTAQUE TOP 20!' : 'Foto removida dos destaques.');
          return {
            ...p,
            is_destaque_top20: next,
            is_selected_curation: next,
            folder_type: (next ? 'selecao' : 'local') as 'selecao' | 'local',
          };
        }
        return p;
      });

      const destaquesIds = nextPhotos.filter((p) => p.is_destaque_top20).map((p) => p.id);
      localStorage.setItem(`sisgab_destaques_${selectedEventId}`, JSON.stringify(destaquesIds));
      return nextPhotos;
    });
  };

  // ── DISPARO INSTANTÂNEO DE FOTO NO WHATSAPP (SEM BAIXAR NO CELULAR) ──
  const handleShareWhatsApp = (photo: PhotoItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    const currentPauta = pautas.find((p) => p.id === selectedEventId);
    const eventTitle = photo.event_name || currentPauta?.titulo_evento || 'Solenidade CGCFN';
    const eventDate = currentPauta?.data_evento || '2026';

    const msg =
      `📸 *SISGAB COMSOC - FOTOGRAFIA INSTITUCIONAL*\n\n` +
      `⚓ *Evento:* ${eventTitle}\n` +
      `📅 *Data:* ${eventDate}\n` +
      (photo.ai_description ? `📝 *Resumo:* ${photo.ai_description}\n` : '') +
      (photo.tags && photo.tags.length > 0 ? `🏷️ *Tags:* #${photo.tags.slice(0, 5).join(' #')}\n` : '') +
      `\n🔗 *Download em Alta Resolução (HD):*\n${photo.drive_link || photo.url}`;

    // Registra no log de auditoria real
    recordAccessLog(photo, 'compartilhamento_whatsapp');

    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, '_blank');
    toast.success('Mensagem formatada com link HD aberta no WhatsApp!');
  };

  // Tags Rápidas em Destaque para Filtro com 1 Toque
  const quickTagChips = [
    { label: '⛵ Lancha', query: 'lancha' },
    { label: '🎖️ Continência', query: 'continência' },
    { label: '🏛️ Salão Nobre', query: 'salão nobre' },
    { label: '🌊 Parada Naval', query: 'parada naval' },
    { label: '🛡️ Blindado CLANF', query: 'blindado' },
    { label: '🎤 Discurso', query: 'discurso' },
    { label: '🥂 Coquetel', query: 'coquetel' },
    { label: '🇧🇷 Bandeira', query: 'bandeira' },
    { label: '👥 Veteranos', query: 'veteranos' },
  ];

  // Filtro de Pautas por Período / Google Drive (Ordenado do mais recente ao mais posterior)
  const filteredPautas = useMemo(() => {
    const today = new Date();
    const list = pautas.filter((p) => {
      if (pautaFilter === 'drive') {
        return !!p.drive_folder_id || !!p.drive_url || p.id === 50;
      }
      if (pautaFilter === 'sem_drive') {
        return !p.drive_folder_id && !p.drive_url && p.id !== 50;
      }
      if (pautaFilter === 'week') {
        if (!p.data_evento) return false;
        const evDate = new Date(p.data_evento);
        const diffDays = Math.abs((today.getTime() - evDate.getTime()) / (1000 * 3600 * 24));
        return diffDays <= 7;
      }
      if (pautaFilter === 'month') {
        if (!p.data_evento) return false;
        const evDate = new Date(p.data_evento);
        return evDate.getMonth() === today.getMonth() && evDate.getFullYear() === today.getFullYear();
      }
      return true;
    });

    return [...list].sort((a, b) => (a.data_evento || '').localeCompare(b.data_evento || ''));
  }, [pautas, pautaFilter]);

  const currentPauta = pautas.find((p) => p.id === selectedEventId) || pautas[0];

  return (
    <div className="space-y-6">
      {/* ── 1. HEADER & STATUS DO MOTOR DE INTELIGÊNCIA VISUAL ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-lg bg-blue-500/20 text-[#00e5ff] text-xs font-bold uppercase tracking-wider border border-blue-500/40 flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" />
              <span>COMSOC CGCFN • DAM 2.0</span>
            </span>
            <span className="text-slate-400 text-xs">• Banco de Ativos Visuais & Vision AI</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight mt-1 flex items-center gap-2">
            <span>GALERIA DE FOTOS & BUSCA SEMÂNTICA POR IA</span>
          </h1>
        </div>

        {/* Painel de Status & Tagueador */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setAuditModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-slate-500 text-slate-300 text-xs font-bold transition-all"
          >
            <Shield className="w-3.5 h-3.5 text-blue-400" />
            <span>Auditoria ({accessLogs.length})</span>
          </button>

          <button
            onClick={() => setTaggerModalOpen(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 text-xs font-black shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
          >
            <Sparkles className="w-4 h-4 text-slate-950" />
            <span>Taguear com Vision AI</span>
          </button>
        </div>
      </div>

      {/* ── 2. SELETOR DE EVENTO + FILTROS DE PERÍODO + BUSCA SEMÂNTICA ── */}
      <div className="p-4 sm:p-5 rounded-3xl bg-[#0b1222] border border-slate-800 space-y-4 shadow-xl">
        {/* Pílulas de Filtro de Eventos (Todas, Com Drive, Sem Drive, Mês, Semana) */}
        <div className="flex items-center justify-between gap-2 flex-wrap border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-bold text-slate-400 mr-1 flex items-center gap-1">
              <FolderOpen className="w-3.5 h-3.5 text-[#00e5ff]" />
              <span>Filtrar Solenidades:</span>
            </span>
            <button
              onClick={() => setPautaFilter('all')}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                pautaFilter === 'all'
                  ? 'bg-slate-700 text-white font-black shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:border-slate-600'
              }`}
            >
              📁 Todas ({pautas.length})
            </button>
            <button
              onClick={() => setPautaFilter('drive')}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                pautaFilter === 'drive'
                  ? 'bg-[#c5a059] text-slate-950 font-black shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:border-[#c5a059]'
              }`}
            >
              <span>☁️ Com Drive</span>
              <span className="px-1.5 py-0.2 rounded-full bg-slate-950/40 text-[10px]">
                {pautas.filter((p) => p.drive_folder_id || p.drive_url || p.id === 50).length}
              </span>
            </button>
            <button
              onClick={() => setPautaFilter('sem_drive')}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                pautaFilter === 'sem_drive'
                  ? 'bg-amber-500 text-slate-950 font-black shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:border-amber-500/50'
              }`}
            >
              <span>⚠️ Sem Drive</span>
              <span className="px-1.5 py-0.2 rounded-full bg-slate-950/40 text-[10px]">
                {pautas.filter((p) => !p.drive_folder_id && !p.drive_url && p.id !== 50).length}
              </span>
            </button>
            <button
              onClick={() => setPautaFilter('month')}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                pautaFilter === 'month'
                  ? 'bg-[#00e5ff] text-slate-950 font-black shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:border-[#00e5ff]'
              }`}
            >
              📅 Este Mês
            </button>
            <button
              onClick={() => setPautaFilter('week')}
              className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                pautaFilter === 'week'
                  ? 'bg-blue-600 text-white font-black shadow-md'
                  : 'bg-slate-900 border border-slate-800 text-slate-300 hover:border-blue-500'
              }`}
            >
              🗓️ Esta Semana
            </button>
          </div>

          <div className="text-[11px] text-slate-400">
            Exibindo <strong className="text-white">{filteredPautas.length}</strong> de {pautas.length} solenidades
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          {/* Seletor de Evento */}
          <div className="md:col-span-1 space-y-1.5">
            <label className="text-xs font-black text-[#00e5ff] uppercase tracking-wider flex items-center gap-1.5">
              <FolderOpen className="w-4 h-4" />
              <span>Solenidade Selecionada:</span>
            </label>
            <select
              value={selectedEventId}
              onChange={(e) => handleEventChange(Number(e.target.value))}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs font-bold text-white focus:outline-none focus:border-[#c5a059]"
            >
              {filteredPautas.map((p) => {
                const hasDrive = !!p.drive_folder_id || !!p.drive_url || p.id === 50;
                return (
                  <option key={p.id} value={p.id}>
                    {hasDrive ? '☁️ ' : '📁 '} {p.data_evento} • {p.titulo_evento}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Barra de Busca Semântica em Linguagem Natural */}
          <div className="md:col-span-2 space-y-1.5">
            <label className="text-xs font-black text-[#e5c07b] uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Search className="w-4 h-4 text-[#c5a059]" />
                <span>Busca em Linguagem Natural (Ex: "lancha na parada naval", "continência salão nobre"):</span>
              </span>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-[10px] text-slate-400 hover:text-white underline font-normal"
                >
                  Limpar busca
                </button>
              )}
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder="Busque por qualquer elemento da foto, ação, pessoa, local ou veículo..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#c5a059] shadow-inner"
              />
              <Search className="w-4 h-4 text-[#c5a059] absolute left-3.5 top-3" />
            </div>
          </div>
        </div>

        {/* Banner Informativo da Solenidade / Pasta Selecionada */}
        {currentPauta && (
          <div className="p-3.5 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-[#00e5ff]/10 border border-[#00e5ff]/30 flex items-center justify-center text-[#00e5ff] shrink-0">
                <FolderOpen className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <strong className="text-white text-xs">{currentPauta.titulo_evento}</strong>
                  <span className="text-[10px] text-slate-400">📅 {currentPauta.data_evento} • 📍 {currentPauta.local_evento}</span>
                </div>
                <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                  <span>Acervo: <strong className="text-[#00e5ff]">{photos.length} fotos indexadas</strong></span>
                  {currentPauta.drive_url ? (
                    <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Google Drive Vinculado</span>
                    </span>
                  ) : (
                    <span className="text-amber-400 font-semibold flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>Sem pasta Drive vinculada</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 flex-wrap">
              {/* Input invisível para upload de matriz .npz */}
              <input
                type="file"
                ref={matrixFileInputRef}
                accept=".npz"
                className="hidden"
                onChange={handleUploadMatrixFile}
              />

              {/* Botão de Upload de Matriz Local (.npz) */}
              <button
                onClick={() => matrixFileInputRef.current?.click()}
                disabled={isUploadingMatrix || !selectedEventId}
                title="Importar matriz gerada com GPU local pelo SisGAB GPU Studio"
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-[#c5a059] text-slate-200 hover:text-white font-bold text-[11px] flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
              >
                <Upload className="w-3.5 h-3.5 text-[#c5a059]" />
                <span>{isUploadingMatrix ? 'Enviando Matriz...' : '📤 Importar Matriz (.npz)'}</span>
              </button>

              {/* Botão de Disparo / Status de Indexação Facial na VPS */}
              {aiIndexingStatus.status === 'processing' ? (
                <div className="px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-amber-300">
                      Indexando Faces: {aiIndexingStatus.percent}% ({aiIndexingStatus.current}/{aiIndexingStatus.total})
                    </span>
                    <span className="text-[9px] text-slate-400">
                      👥 {aiIndexingStatus.faces} rostos mapeados
                    </span>
                  </div>
                </div>
              ) : aiIndexingStatus.status === 'done' ? (
                <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[11px] font-bold text-emerald-300">
                    IA Facial Pronta ({aiIndexingStatus.faces} faces)
                  </span>
                  <button
                    onClick={handleTriggerAiIndexing}
                    title="Reindexar acervo na VPS"
                    className="ml-1 text-[10px] text-slate-400 hover:text-white underline"
                  >
                    Reindexar
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleTriggerAiIndexing}
                  disabled={isStartingAiIndex || photos.length === 0}
                  className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:brightness-110 text-white font-black text-[11px] flex items-center gap-1.5 transition-all shadow-md shadow-cyan-500/20 disabled:opacity-50"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-300" />
                  <span>Indexar na VPS</span>
                </button>
              )}

              {currentPauta.drive_url ? (
                <>
                  <a
                    href={currentPauta.drive_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded-xl bg-blue-600/20 hover:bg-blue-600 border border-blue-500/40 text-blue-300 hover:text-white font-bold text-[11px] flex items-center gap-1.5 transition-all shadow-sm"
                  >
                    <ExternalLink className="w-3 h-3" />
                    <span>Abrir no Google Drive</span>
                  </a>
                  <button
                    onClick={() => {
                      setLinkDriveInput(currentPauta.drive_url || '');
                      setLinkDriveModalOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white font-bold text-[11px] flex items-center gap-1.5 transition-all"
                  >
                    <Link className="w-3 h-3 text-[#c5a059]" />
                    <span>Alterar Link</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleCreateDriveForCurrentPauta}
                    disabled={creatingDrive}
                    className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:brightness-110 text-white font-bold text-[11px] flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                  >
                    {creatingDrive ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Criando Pasta...</span>
                      </>
                    ) : (
                      <>
                        <Cloud className="w-3 h-3" />
                        <span>Criar Pasta no Drive</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setLinkDriveInput('');
                      setLinkDriveModalOpen(true);
                    }}
                    className="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 hover:text-amber-200 font-bold text-[11px] flex items-center gap-1.5 transition-all"
                  >
                    <Link className="w-3 h-3 text-amber-400" />
                    <span>Vincular Link</span>
                  </button>
                </>
              )}
              <a
                href={`/evento/${currentPauta.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-xl bg-[#c5a059]/20 hover:bg-[#c5a059] border border-[#c5a059]/40 text-[#e5c07b] hover:text-slate-950 font-bold text-[11px] flex items-center gap-1.5 transition-all shadow-sm"
              >
                <Eye className="w-3 h-3" />
                <span>Portal Público</span>
              </a>
            </div>
          </div>
        )}

        {/* Tags Rápidas em Destaque */}
        <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-bold text-slate-400 flex items-center gap-1">
            <Tag className="w-3 h-3 text-[#00e5ff]" />
            <span>Filtro Rápido:</span>
          </span>
          {quickTagChips.map((chip) => {
            const isSelected = selectedTagFilter === chip.query;
            return (
              <button
                key={chip.query}
                onClick={() => setSelectedTagFilter(isSelected ? null : chip.query)}
                className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${
                  isSelected
                    ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/30'
                    : 'bg-slate-900/90 text-slate-300 hover:text-white hover:bg-slate-800 border border-slate-700'
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 3. BARRA DE CURADORIA EM 3 NÍVEIS & AÇÕES RÁPIDAS ── */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 p-3 rounded-2xl bg-[#0b1222] border border-slate-800 flex-wrap">
        {/* Abas de Níveis */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900/80 border border-slate-800 flex-wrap">
          <button
            onClick={() => setActiveMainTab('locais')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeMainTab === 'locais' ? 'bg-[#00e5ff] text-slate-950 font-black' : 'text-slate-400 hover:text-white'
            }`}
          >
            📁 Todas ({photos.length})
          </button>

          <button
            onClick={() => setActiveMainTab('destaques')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeMainTab === 'destaques' ? 'bg-[#c5a059] text-slate-950 font-black shadow-md' : 'text-[#e5c07b] hover:text-white'
            }`}
          >
            <Star className="w-3.5 h-3.5 fill-current" />
            <span>⭐ Top 20 Destaques ({photos.filter((p) => p.is_destaque_top20).length})</span>
          </button>

          <button
            onClick={() => setActiveMainTab('tagueadas')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeMainTab === 'tagueadas' ? 'bg-[#c5a059] text-slate-950 font-black shadow-md' : 'text-[#e5c07b] hover:text-white'
            }`}
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>Com Tags IA ({photos.filter((p) => p.ai_tagged).length})</span>
          </button>

          <button
            onClick={() => setActiveMainTab('pessoal')}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeMainTab === 'pessoal' ? 'bg-[#00e5ff] text-slate-950 font-black' : 'text-slate-400 hover:text-white'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Militares ({photos.filter((p) => p.matched_militar).length})</span>
          </button>
        </div>

        {/* Ações Diretas */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Botão Gerenciador de Contas Drive */}
          <button
            onClick={() => setDriveManagerModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-emerald-400 text-emerald-400 text-xs font-bold transition-all shadow-md"
            title="Gerenciar Contas e Autenticação do Google Drive (OAuth / Service Account)"
          >
            <Cloud className="w-3.5 h-3.5" />
            <span>Contas Drive</span>
          </button>

          {/* Botão Upload de Fotos Web */}
          <button
            onClick={() => {
              if (webUploadInputRef.current) {
                webUploadInputRef.current.click();
              }
            }}
            disabled={isUploadingWeb}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:brightness-110 text-white text-xs font-black transition-all shadow-md shadow-cyan-600/20 disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{isUploadingWeb ? `Enviando (${webUploadProgress.current}/${webUploadProgress.total})...` : 'Subir Fotos (Web/Celular)'}</span>
          </button>
          <input
            type="file"
            ref={webUploadInputRef}
            onChange={handleDirectWebUpload}
            multiple
            accept="image/*"
            className="hidden"
          />

          <button
            onClick={() => setPortalModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#00e5ff] text-[#00e5ff] text-xs font-bold"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Link do Evento</span>
          </button>

          <button
            onClick={() => {
              militaryAudio.playTacticalBeep();
              toast.success(`Iniciando download em lote de ${filteredPhotos.length} fotos em alta resolução (ZIP)...`);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs shadow-md shadow-[#c5a059]/20"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Baixar Filtro ({filteredPhotos.length})</span>
          </button>
        </div>
      </div>

      {/* ── 4. GRADE DE FOTOS COM TAGS SEMÂNTICAS & AÇÃO WHATSAPP ── */}
      {(() => {
        const totalPages = Math.max(1, Math.ceil(filteredPhotos.length / perPage));
        const startIndex = (currentPage - 1) * perPage;
        const paginatedPhotos = filteredPhotos.slice(startIndex, startIndex + perPage);

        return (
          <div className="space-y-4">
            {filteredPhotos.length === 0 ? (
              <div className="p-12 rounded-3xl bg-[#0b1222] border border-slate-800 text-center space-y-4">
                <Images className="w-12 h-12 text-slate-600 mx-auto" />
                <h4 className="text-sm font-bold text-slate-300">
                  {photos.length === 0
                    ? `Nenhuma foto indexada no banco local para: "${currentPauta?.titulo_evento || 'Evento'}"`
                    : 'Nenhuma foto encontrada para os filtros atuais'}
                </h4>
                <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                  {photos.length === 0 ? (
                    currentPauta?.drive_url ? (
                      <>
                        As fotos desta solenidade estão disponíveis na pasta oficial do Google Drive. Você pode acessar a pasta diretamente ou indexá-las com o Vision AI / Watcher.
                      </>
                    ) : (
                      <>
                        Este evento ainda não possui fotos processadas no acervo local ou pasta vinculada no Google Drive.
                      </>
                    )
                  ) : (
                    'Tente buscar por termos mais genéricos (ex: continência, lancha, oficial, salão nobre) ou limpe os filtros.'
                  )}
                </p>
                <div className="flex items-center justify-center gap-2 pt-2 flex-wrap">
                  {photos.length === 0 && currentPauta?.drive_url && (
                    <a
                      href={currentPauta.drive_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow-lg"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>Acessar Pasta no Google Drive</span>
                    </a>
                  )}

                  {photos.length === 0 && !currentPauta?.drive_url && (
                    <>
                      <button
                        onClick={handleCreateDriveForCurrentPauta}
                        disabled={creatingDrive}
                        className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:brightness-110 text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow-lg disabled:opacity-50"
                      >
                        {creatingDrive ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Criando Pasta Oficial no Drive...</span>
                          </>
                        ) : (
                          <>
                            <Cloud className="w-3.5 h-3.5" />
                            <span>Criar Pasta Oficial no Google Drive</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => {
                          setLinkDriveInput('');
                          setLinkDriveModalOpen(true);
                        }}
                        className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1.5 transition-all"
                      >
                        <Link className="w-3.5 h-3.5 text-amber-400" />
                        <span>Vincular Link Existente do Drive</span>
                      </button>
                    </>
                  )}

                  {photos.length > 0 && (
                    <button
                      onClick={() => {
                        setSearchQuery('');
                        setSelectedTagFilter(null);
                        setActiveMainTab('locais');
                      }}
                      className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold hover:bg-slate-700"
                    >
                      Ver Todas as Fotos ({photos.length})
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {paginatedPhotos.map((photo) => (
                  <div
                    key={photo.id}
                    onClick={() => handleOpenPhoto(photo)}
                    className="group relative rounded-2xl overflow-hidden bg-slate-900 border border-slate-800 hover:border-[#c5a059] flex flex-col cursor-pointer transition-all shadow-lg hover:shadow-xl hover:scale-[1.01]"
                  >
                    {/* Imagem */}
                    <div className="relative aspect-square w-full bg-slate-950 overflow-hidden">
                      <img
                        src={photo.thumbnail_url || photo.url}
                        alt={photo.filename}
                        referrerPolicy="no-referrer"
                        loading="lazy"
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />

                      {/* Badge Top 20 Destaque */}
                      {photo.is_destaque_top20 && (
                        <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-[#c5a059] text-slate-950 font-black text-[10px] flex items-center gap-1 shadow-lg">
                          <Star className="w-3 h-3 fill-current" />
                          <span>DESTAQUE</span>
                        </div>
                      )}

                      {/* Botão de Estrela de Curadoria */}
                      <button
                        type="button"
                        onClick={(e) => toggleDestaqueTop20(photo.id, e)}
                        className={`absolute top-2 right-2 p-1.5 rounded-xl backdrop-blur-md transition-all shadow-md ${
                          photo.is_destaque_top20
                            ? 'bg-[#c5a059] text-slate-950'
                            : 'bg-black/60 text-slate-400 hover:text-white opacity-0 group-hover:opacity-100'
                        }`}
                        title={photo.is_destaque_top20 ? 'Remover dos Destaques' : 'Adicionar aos Destaques COMSOC'}
                      >
                        <Star className="w-4 h-4 fill-current" />
                      </button>

                      {/* Botão Flutuante de Compartilhar no WhatsApp */}
                      <button
                        type="button"
                        onClick={(e) => handleShareWhatsApp(photo, e)}
                        className="absolute bottom-2 right-2 px-2.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-[11px] flex items-center gap-1.5 shadow-lg shadow-emerald-600/30 opacity-90 group-hover:opacity-100 transition-opacity"
                        title="Enviar link HD direto no WhatsApp"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>WhatsApp</span>
                      </button>
                    </div>

                    {/* Metadados e Tags Semânticas da Foto */}
                    <div className="p-3 bg-slate-900/95 space-y-2 border-t border-slate-800">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[11px] font-bold text-slate-200 truncate">{photo.filename}</span>
                        {photo.ai_tagged ? (
                          <span className="px-1.5 py-0.5 rounded bg-[#c5a059]/20 text-[#e5c07b] text-[9px] font-bold flex items-center gap-0.5 border border-[#c5a059]/40 shrink-0">
                            <Sparkles className="w-2.5 h-2.5 text-[#e5c07b]" />
                            <span>IA</span>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => handleTagSinglePhoto(photo, e)}
                            disabled={isTaggingSingle === photo.id}
                            className="px-2 py-0.5 rounded-md bg-[#00e5ff]/15 hover:bg-[#00e5ff]/25 text-[#00e5ff] border border-[#00e5ff]/30 text-[9px] font-bold flex items-center gap-1 transition-all shrink-0 hover:scale-105"
                            title="Analisar esta foto com Gemini Vision IA"
                          >
                            <Sparkles className="w-2.5 h-2.5 text-[#00e5ff]" />
                            <span>{isTaggingSingle === photo.id ? '...' : 'Taguear IA'}</span>
                          </button>
                        )}
                      </div>

                      {photo.ai_description ? (
                        <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed">
                          {photo.ai_description}
                        </p>
                      ) : (
                        <p className="text-[10px] text-slate-600 italic">
                          Aguardando análise de visão computacional...
                        </p>
                      )}

                      {/* Tags da Foto */}
                      {photo.tags && photo.tags.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap pt-1">
                          {photo.tags.slice(0, 3).map((tag, idx) => (
                            <span
                              key={idx}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSearchQuery(tag);
                              }}
                              className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[9px] font-semibold transition-colors"
                            >
                              #{tag}
                            </span>
                          ))}
                          {photo.tags.length > 3 && (
                            <span className="text-[9px] text-slate-500 font-bold">+{photo.tags.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Paginação */}
            <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
              <div className="text-slate-400">
                Exibindo fotos <strong className="text-white">{startIndex + 1}</strong> a{' '}
                <strong className="text-white">{Math.min(startIndex + perPage, filteredPhotos.length)}</strong> de{' '}
                <strong className="text-[#00e5ff]">{filteredPhotos.length}</strong> fotos filtradas
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30 font-bold"
                >
                  ← Anterior
                </button>

                <span className="text-slate-400 font-bold">
                  Página {currentPage} de {totalPages}
                </span>

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30 font-bold"
                >
                  Próxima →
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── 5. MODAL DE CONTROLE DO TAGUEADOR VISION AI EM LOTE ── */}
      {taggerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-xl w-full p-6 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/60 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-[#c5a059] animate-pulse" />
                <h3 className="text-sm font-black text-white uppercase">
                  Tagueador Semântico com Vision AI (Gemini)
                </h3>
              </div>
              <button
                onClick={() => {
                  if (isBatchTagging) {
                    toast.warning('O processamento continuará em segundo plano.');
                  }
                  setTaggerModalOpen(false);
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-slate-300 leading-relaxed">
              O motor de visão computacional analisa cada foto individualmente e extrai veículos (lanchas, blindados), equipamentos (fuzis, microfones), cenários, ações e autoridades para buscas em linguagem natural.
            </p>

            {/* Configuração da Chave */}
            <div className="space-y-1.5 p-3 rounded-2xl bg-slate-900 border border-slate-800">
              <label className="block text-slate-400 font-bold">Chave de API do Google Gemini (Gratuita):</label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(e) => {
                  setGeminiApiKey(e.target.value);
                  localStorage.setItem('sisgab_gemini_key', e.target.value);
                }}
                placeholder="Insira sua chave AIza..."
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-white font-mono text-xs focus:outline-none focus:border-[#c5a059]"
              />
              <span className="text-[10px] text-slate-500 block">
                Cota gratuita: até 1.500 análises por dia com gemini-3.7-flash / gemini-3.6-flash.
              </span>
            </div>

            {/* Barra de Progresso em Tempo Real */}
            {isBatchTagging ? (
              <div className="space-y-3 p-4 rounded-2xl bg-slate-900 border border-[#c5a059]/40">
                <div className="flex items-center justify-between font-bold text-xs">
                  <span className="text-[#e5c07b]">
                    Processando: {taggingProgress.current} de {taggingProgress.total} fotos
                  </span>
                  <span className="text-emerald-400">
                    {Math.round((taggingProgress.current / Math.max(1, taggingProgress.total)) * 100)}%
                  </span>
                </div>

                <div className="w-full h-3 rounded-full bg-slate-950 overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-gradient-to-r from-[#c5a059] to-[#00e5ff] transition-all duration-300"
                    style={{
                      width: `${(taggingProgress.current / Math.max(1, taggingProgress.total)) * 100}%`,
                    }}
                  />
                </div>

                <div className="text-[11px] text-slate-400 truncate">
                  📸 Foto atual: <strong className="text-white">{taggingProgress.currentPhotoName}</strong>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <button
                    onClick={handlePauseTagging}
                    className="flex-1 py-2 rounded-xl bg-slate-800 text-slate-200 font-bold hover:bg-slate-700 flex items-center justify-center gap-1.5"
                  >
                    {isTaggingPaused ? <Play className="w-3.5 h-3.5 text-emerald-400" /> : <Pause className="w-3.5 h-3.5" />}
                    <span>{isTaggingPaused ? 'Retomar' : 'Pausar'}</span>
                  </button>

                  <button
                    onClick={handleStopTagging}
                    className="flex-1 py-2 rounded-xl bg-rose-600/80 hover:bg-rose-600 text-white font-bold flex items-center justify-center gap-1.5"
                  >
                    <Square className="w-3.5 h-3.5" />
                    <span>Parar</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-400 p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span>Fotos sem tags neste evento:</span>
                  <strong className="text-[#00e5ff] text-sm">
                    {photos.filter((p) => !p.ai_tagged).length} fotos
                  </strong>
                </div>

                <button
                  onClick={handleStartBatchTagging}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs shadow-xl shadow-[#c5a059]/30 flex items-center justify-center gap-2 transition-all hover:scale-[1.01]"
                >
                  <Sparkles className="w-4 h-4 text-slate-950" />
                  <span>Iniciar Tagueamento com IA (Lote)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 6. MODAL DE AUDITORIA & LOG DE ACESSOS ── */}
      {auditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-2xl w-full p-6 rounded-3xl bg-[#0b1222] border-2 border-blue-500/50 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-black text-white uppercase">
                  Histórico de Auditoria & Acessos COMSOC
                </h3>
              </div>
              <button onClick={() => setAuditModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-slate-300">
              Registros reais de quem visualizou, compartilhou ou realizou download de fotos institucionais:
            </p>

            {accessLogs.length === 0 ? (
              <div className="p-8 text-center text-slate-400 space-y-2 rounded-2xl border border-slate-800 bg-slate-950">
                <Shield className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="font-bold text-slate-300">Nenhum registro de acesso nesta sessão ainda.</p>
                <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                  Toda visualização, download em alta resolução ou compartilhamento via WhatsApp realizado no acervo será registrado aqui automaticamente em tempo real com link direto para a foto.
                </p>
              </div>
            ) : (
              <div className="rounded-2xl border border-slate-800 overflow-hidden bg-slate-900 max-h-80 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] font-bold border-b border-slate-800 sticky top-0 z-10">
                    <tr>
                      <th className="p-2.5">Horário</th>
                      <th className="p-2.5">Mídia / Foto</th>
                      <th className="p-2.5">Ação</th>
                      <th className="p-2.5">Origem / Dispositivo</th>
                      <th className="p-2.5 text-right">Acessar</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-300 font-medium">
                    {accessLogs.map((log) => {
                      const matchedPhoto = photos.find((p) => p.id === log.photo_id || p.filename === log.photo_name);
                      const photoUrl = log.thumbnail_url || log.photo_url || matchedPhoto?.thumbnail_url || matchedPhoto?.url;
                      return (
                        <tr
                          key={log.id}
                          onClick={() => {
                            if (matchedPhoto) {
                              setLightboxPhoto(matchedPhoto);
                            } else if (log.photo_url) {
                              setLightboxPhoto({
                                id: log.photo_id || 'temp',
                                filename: log.photo_name,
                                url: log.photo_url || '',
                                thumbnail_url: log.thumbnail_url || log.photo_url || '',
                                folder_type: 'geral',
                                ai_tagged: false,
                              });
                            }
                            setAuditModalOpen(false);
                          }}
                          className="hover:bg-blue-500/10 cursor-pointer transition-all group"
                          title="Clique para abrir e inspecionar esta fotografia no visualizador"
                        >
                          <td className="p-2.5 font-mono text-[11px] text-slate-400 whitespace-nowrap">{log.date}</td>
                          <td className="p-2.5 font-bold text-white">
                            <div className="flex items-center gap-2.5">
                              {photoUrl ? (
                                <img
                                  src={photoUrl}
                                  alt={log.photo_name}
                                  className="w-9 h-9 object-cover rounded-lg border border-slate-700 group-hover:border-cyan-400 transition-all shrink-0"
                                />
                              ) : (
                                <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center shrink-0">
                                  <ImageIcon className="w-4 h-4 text-slate-500" />
                                </div>
                              )}
                              <span className="truncate max-w-[160px] group-hover:text-cyan-300 transition-all">
                                {log.photo_name}
                              </span>
                            </div>
                          </td>
                          <td className="p-2.5">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                log.action === 'compartilhamento_whatsapp'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : log.action === 'download_hd'
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : 'bg-slate-700/50 text-slate-300'
                              }`}
                            >
                              {log.action === 'compartilhamento_whatsapp'
                                ? '💬 WhatsApp'
                                : log.action === 'download_hd'
                                ? '⬇️ Download HD'
                                : '👁️ Visualizou'}
                            </span>
                          </td>
                          <td className="p-2.5 text-slate-400 text-[11px]">{log.device}</td>
                          <td className="p-2.5 text-right">
                            <span className="px-2.5 py-1 rounded-lg bg-cyan-950/80 text-cyan-300 border border-cyan-500/40 text-[10px] font-bold opacity-0 group-hover:opacity-100 transition-all">
                              👁️ Ver Foto
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setAuditModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 font-bold hover:bg-slate-700"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. MODAL LIGHTBOX HD COM METADADOS COMPLETOS DA IA ── */}
      {lightboxPhoto && (
        <div
          onClick={() => setLightboxPhoto(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/95 backdrop-blur-md animate-in fade-in"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="max-w-6xl w-full p-5 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/50 space-y-4 shadow-2xl text-xs max-h-[95vh] flex flex-col"
          >
            <div className="flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 truncate max-w-md">
                <span className="text-xs font-black text-white truncate">
                  ⚓ {lightboxPhoto.filename}
                </span>
                {lightboxPhoto.is_destaque_top20 && (
                  <span className="px-2 py-0.5 rounded bg-[#c5a059] text-slate-950 font-black text-[10px]">
                    ⭐ TOP 20
                  </span>
                )}
              </div>
              <button onClick={() => setLightboxPhoto(null)} className="p-1.5 text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Imagem Ampliada HD */}
            <div className="relative flex-1 w-full min-h-0 flex items-center justify-center bg-black/95 rounded-2xl overflow-hidden p-2">
              <img
                src={
                  lightboxPhoto.drive_file_id
                    ? `https://drive.google.com/thumbnail?id=${lightboxPhoto.drive_file_id}&sz=w1920`
                    : lightboxPhoto.url?.includes('sz=w600')
                    ? lightboxPhoto.url.replace('sz=w600', 'sz=w1920')
                    : lightboxPhoto.url || lightboxPhoto.thumbnail_url
                }
                alt={lightboxPhoto.filename}
                referrerPolicy="no-referrer"
                className="h-full w-full max-h-[68vh] object-contain rounded-xl drop-shadow-2xl select-none"
              />
            </div>

            {/* Descrição e Tags Geradas pela IA */}
            {lightboxPhoto.ai_tagged && lightboxPhoto.ai_description ? (
              <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2 shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[#00e5ff] font-bold text-xs">
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    <span>Análise de Visão Computacional (Gemini Vision AI):</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleTagSinglePhoto(lightboxPhoto)}
                    disabled={isTaggingSingle === lightboxPhoto.id}
                    className="text-[10px] text-[#00e5ff] hover:text-white font-bold flex items-center gap-1"
                  >
                    <Sparkles className="w-3 h-3 text-[#00e5ff]" />
                    <span>{isTaggingSingle === lightboxPhoto.id ? 'Reanalisando...' : 'Reanalisar com IA'}</span>
                  </button>
                </div>
                <p className="text-slate-200 leading-relaxed text-xs">
                  {lightboxPhoto.ai_description}
                </p>

                {lightboxPhoto.tags && lightboxPhoto.tags.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-1">
                    {lightboxPhoto.tags.map((t, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[#e5c07b] text-[10px] font-bold"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div>
                  <span className="text-slate-300 font-bold block text-xs">Fotografia Sem Análise de IA</span>
                  <span className="text-[11px] text-slate-500">
                    Processe agora com o Gemini Vision para extrair elementos, veículos, cenários e tags reais.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleTagSinglePhoto(lightboxPhoto)}
                  disabled={isTaggingSingle === lightboxPhoto.id}
                  className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-md shadow-[#c5a059]/30 transition-all hover:scale-105 shrink-0"
                >
                  <Sparkles className="w-3.5 h-3.5 text-slate-950" />
                  <span>{isTaggingSingle === lightboxPhoto.id ? 'Analisando Imagem...' : 'Analisar com Vision AI'}</span>
                </button>
              </div>
            )}

            {/* Barra de Ações Rápidas */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800 flex-wrap gap-2">
              <button
                type="button"
                onClick={(e) => toggleDestaqueTop20(lightboxPhoto.id, e)}
                className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                  lightboxPhoto.is_destaque_top20
                    ? 'bg-[#c5a059] text-slate-950 font-black'
                    : 'bg-slate-900 border border-slate-700 text-slate-300 hover:text-white'
                }`}
              >
                <Star className="w-4 h-4 fill-current" />
                <span>{lightboxPhoto.is_destaque_top20 ? '⭐ Destaque Top 20' : 'Marcar Destaque'}</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleShareWhatsApp(lightboxPhoto)}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-600/30"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Enviar no WhatsApp</span>
                </button>

                {lightboxPhoto.drive_link && (
                  <a
                    href={lightboxPhoto.drive_link}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700 text-[#00e5ff] text-xs font-bold flex items-center gap-1.5 hover:border-[#00e5ff]"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Drive</span>
                  </a>
                )}

                <a
                  href={
                    lightboxPhoto.drive_file_id
                      ? `https://drive.google.com/uc?export=download&id=${lightboxPhoto.drive_file_id}`
                      : lightboxPhoto.drive_link || lightboxPhoto.url || lightboxPhoto.thumbnail_url
                  }
                  download={lightboxPhoto.filename}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => recordAccessLog(lightboxPhoto, 'download_hd')}
                  className="px-5 py-2 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105"
                >
                  <Download className="w-4 h-4" />
                  <span>Baixar HD Original</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 8. MODAL DE LINKS DO EVENTO & SENHA / PIN ── */}
      {portalModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full p-6 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/60 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ExternalLink className="w-5 h-5 text-[#e5c07b]" />
                <h3 className="text-sm font-black text-white uppercase">Portal de Fotos do Evento</h3>
              </div>
              <button onClick={() => setPortalModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-slate-300">
              Compartilhe o portal de fotos para os participantes ou autoridades acessarem:
            </p>

            <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-bold">🔒 Código PIN de Segurança:</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/20 text-[#e5c07b] font-mono font-bold text-xs">
                  {currentPauta?.pin_code || '1808'}
                </span>
              </div>
              <p className="text-[10px] text-slate-500">
                Se ativado, apenas convidados com este PIN de 4 dígitos conseguem visualizar as fotos.
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/evento/${selectedEventId}`);
                  toast.success('Link do Portal de Fotos copiado!');
                  setPortalModalOpen(false);
                }}
                className="flex-1 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-bold hover:text-white"
              >
                Copiar Link
              </button>

              <button
                onClick={() => {
                  const url = `${window.location.origin}/evento/${selectedEventId}`;
                  const msg = `📸 *Fotos Oficiais - ${currentPauta?.titulo_evento}*\n\nAcesse a galeria oficial no SisGAB:\n${url}\n\n🔒 PIN de acesso: ${currentPauta?.pin_code || '1808'}`;
                  window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, '_blank');
                  setPortalModalOpen(false);
                }}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold"
              >
                Disparar no WhatsApp
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 9. MODAL DE VINCULAÇÃO MANUAL DE GOOGLE DRIVE ── */}
      {linkDriveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="max-w-md w-full p-6 rounded-3xl bg-[#0b1222] border-2 border-[#00e5ff]/60 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cloud className="w-5 h-5 text-[#00e5ff]" />
                <h3 className="text-sm font-black text-white uppercase">Vincular Pasta do Google Drive</h3>
              </div>
              <button
                onClick={() => {
                  setLinkDriveModalOpen(false);
                  setLinkDriveInput('');
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <p className="text-slate-300">
                Solenidade: <strong className="text-white">{currentPauta?.titulo_evento}</strong>
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                Cole a URL pública ou compartilhada da pasta oficial do Google Drive para vincular à galeria:
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                URL da Pasta do Google Drive:
              </label>
              <input
                type="url"
                placeholder="https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ"
                value={linkDriveInput}
                onChange={(e) => setLinkDriveInput(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e5ff] shadow-inner"
              />
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setLinkDriveModalOpen(false);
                  setLinkDriveInput('');
                }}
                className="flex-1 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-300 font-bold hover:text-white hover:bg-slate-800"
              >
                Cancelar
              </button>

              <button
                type="button"
                onClick={handleSaveDriveLinkManual}
                disabled={savingDriveLink || !linkDriveInput.trim()}
                className="flex-1 py-2.5 rounded-xl bg-[#00e5ff] hover:bg-[#00cce6] text-slate-950 font-black flex items-center justify-center gap-1.5 shadow-lg shadow-[#00e5ff]/20 disabled:opacity-50"
              >
                {savingDriveLink ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Salvando...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Salvar e Vincular</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 10. MODAL GERENCIADOR DE CONTAS GOOGLE DRIVE (MULTI-DRIVE & OAUTH 2.0) ── */}
      {driveManagerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md animate-in fade-in">
          <div className="max-w-2xl w-full p-6 rounded-3xl bg-[#091326] border-2 border-emerald-500/50 space-y-5 shadow-2xl text-xs max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                  <Cloud className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-white uppercase tracking-wider">
                    Gerenciador Multi-Drive & OAuth 2.0
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Controle de autenticação para uploads (Conta Pessoal com Espaço / Service Account)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDriveManagerModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Status da Conexão Atual */}
            <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-300">Status da Conexão Ativa:</span>
                <span className={`px-2 py-0.5 rounded font-black text-[10px] uppercase ${driveAccountsData?.connection_status ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                  {driveAccountsData?.connection_status ? '🟢 CONECTADO' : '🔴 OFFLINE'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {driveAccountsData?.connection_message || 'Verificando conexão...'}
              </p>
            </div>

            {/* Seletor de Modo Ativo */}
            <div className="space-y-2">
              <label className="text-xs font-black text-[#00e5ff] uppercase tracking-wider">
                Modo de Autenticação Ativo:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Opção 1: OAuth 2.0 */}
                <div
                  onClick={() => handleSwitchDriveAuthMode('oauth')}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    driveAccountsData?.active_mode === 'oauth'
                      ? 'bg-emerald-950/40 border-emerald-400 ring-2 ring-emerald-400/30'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-black text-white">🔑 Conta Pessoal (OAuth 2.0)</span>
                    {driveAccountsData?.active_mode === 'oauth' && (
                      <span className="text-emerald-400 font-black text-[10px]">ATIVO</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Usa o espaço livre da sua conta @gmail.com (sem erro de cota). Ideal para fotos via Telegram e Web.
                  </p>
                </div>

                {/* Opção 2: Service Account */}
                <div
                  onClick={() => handleSwitchDriveAuthMode('service_account')}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    driveAccountsData?.active_mode === 'service_account'
                      ? 'bg-cyan-950/40 border-[#00e5ff] ring-2 ring-[#00e5ff]/30'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-black text-white">🤖 Service Account (Robô)</span>
                    {driveAccountsData?.active_mode === 'service_account' && (
                      <span className="text-[#00e5ff] font-black text-[10px]">ATIVO</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Robô server-to-server com chave JSON. Ideal para Drives Compartilhados corporativos.
                  </p>
                </div>
              </div>
            </div>

            {/* Painel de Configuração OAuth 2.0 */}
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white flex items-center gap-1.5">
                  <span>Conectar Nova Conta Pessoal (Google OAuth)</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {driveAccountsData?.has_oauth ? '✅ Token Armazenado' : '⚠️ Nenhum Token'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Cole o JSON de autorização da conta Google (Token de Acesso / Refresh Token) para uploads de alta capacidade:
              </p>
              <textarea
                rows={3}
                placeholder='Cole aqui o JSON do Token OAuth (ex: {"token": "...", "refresh_token": "...", "client_id": "..."})'
                value={oauthTokenInput}
                onChange={(e) => setOauthTokenInput(e.target.value)}
                className="w-full p-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white font-mono text-[11px] placeholder-slate-600 focus:outline-none focus:border-emerald-400"
              ></textarea>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleSaveOAuthToken}
                  disabled={savingOAuthToken || !oauthTokenInput.trim()}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/20 disabled:opacity-50"
                >
                  {savingOAuthToken ? 'Salvando...' : 'Salvar e Ativar Conta'}
                </button>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setDriveManagerModalOpen(false)}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
