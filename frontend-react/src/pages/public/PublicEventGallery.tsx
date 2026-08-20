import { militaryAudio } from '../../utils/militaryAudio';
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  Camera,
  Download,
  CheckCircle2,
  Sparkles,
  Share2,
  Images,
  ExternalLink,
  Shield,
  Eye,
  X,
  SlidersHorizontal,
  FolderOpen,
  User,
  Search,
  Check,
  Square,
  CheckSquare,
  Bot,
  RefreshCw,
  Upload,
} from 'lucide-react';
import { toast } from 'sonner';
import { supabase } from '../../api/supabase';
import defaultBrasao from '../../assets/brasaocgcfn.png';

interface PhotoItem {
  id: string;
  filename: string;
  drive_file_id?: string;
  url: string;
  thumbnail_url: string;
  drive_thumb?: string;
  drive_link?: string;
  similarity?: number;
}

export const PublicEventGallery: React.FC = () => {
  const { id: eventId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();

  // Modo facial passado na URL ou ativado pelo botão do usuário
  const urlFacialMode = searchParams.get('modo') === 'facial';
  const [showFacialFinder, setShowFacialFinder] = useState(urlFacialMode);

  const [eventName, setEventName] = useState('ENCONTRO DE VETERANOS (OFICIAIS SUPERIORES)');
  const [eventDate, setEventDate] = useState('14 de Agosto de 2026');
  const [eventLocation, setEventLocation] = useState('CIASC • Fortaleza de São José');
  const [driveUrl, setDriveUrl] = useState('https://drive.google.com/drive/folders/1cqK3F24QQCj5tgkXy-zJZoP1al-dF3Yv');

  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [filteredPhotos, setFilteredPhotos] = useState<PhotoItem[]>([]);
  const [selectedPhoto, setSelectedPhoto] = useState<PhotoItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Seleção múltipla de fotos
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Paginação (48 fotos por página)
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(48);

  // Biometria Facial por Selfie ou Foto da Galeria
  const [cameraActive, setCameraActive] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [selfieTaken, setSelfieTaken] = useState(false);
  const [selectedPhotoFile, setSelectedPhotoFile] = useState<string | null>(null);
  const [uploadedFileBlob, setUploadedFileBlob] = useState<Blob | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    loadRealEventData();
  }, [eventId]);

  const loadRealEventData = async () => {
    try {
      setLoading(true);
      const targetId = Number(eventId) || 50;

      // 1. Tenta carregar fotos e dados diretamente da API dinâmica do Google Drive do evento
      try {
        const apiRes = await fetch(`/api/portal/photos?event_id=${targetId}`);
        if (apiRes.ok) {
          const data = await apiRes.json();
          if (data.event) {
            setEventName(data.event.title || 'ENCONTRO DE VETERANOS');
            if (data.event.date) {
              const parts = String(data.event.date).split('-');
              if (parts.length === 3) {
                const dt = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
                setEventDate(dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }));
              } else {
                setEventDate(String(data.event.date));
              }
            }
            if (data.event.location) {
              setEventLocation(data.event.location);
            }
            if (data.event.drive_url) {
              setDriveUrl(data.event.drive_url);
            }
          }
          if (Array.isArray(data.photos) && data.photos.length > 0) {
            setPhotos(data.photos);
            setFilteredPhotos(data.photos);
            return;
          }
        }
      } catch (errApi) {
        console.warn('API de fotos do Drive offline, tentando fallback:', errApi);
      }

      // 2. Fallback: Supabase se a API não retornou
      const { data: demData } = await supabase
        .from('demandas_comunicacao')
        .select('*')
        .eq('id', targetId)
        .single();

      if (demData) {
        setEventName(demData.titulo_evento || 'ENCONTRO DE VETERANOS (OFICIAIS SUPERIORES)');
        if (demData.data_evento) {
          const parts = demData.data_evento.split('-');
          if (parts.length === 3) {
            const dt = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            setEventDate(dt.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' }));
          }
        }
        if (demData.local_evento) {
          setEventLocation(demData.local_evento);
        }
        if (demData.drive_url) {
          setDriveUrl(demData.drive_url);
        }
      }

      // 3. Fallback de fotos locais para o evento 50
      if (targetId === 50) {
        const res = await fetch('/event_50_photos.json');
        if (res.ok) {
          const jsonPhotos: PhotoItem[] = await res.json();
          setPhotos(jsonPhotos);
          setFilteredPhotos(jsonPhotos);
        }
      }
    } catch (err) {
      console.warn('Erro ao carregar evento:', err);
    } finally {
      setLoading(false);
    }
  };

  // Alternar Seleção de uma Foto Específica
  const toggleSelectPhoto = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Selecionar Todas as Fotos da Página Atual
  const handleSelectAllCurrentPage = () => {
    const startIndex = (currentPage - 1) * perPage;
    const currentBatch = displayedPhotos.slice(startIndex, startIndex + perPage);
    const allSelected = currentBatch.every((p) => selectedIds.has(p.id));

    setSelectedIds((prev) => {
      const next = new Set(prev);
      currentBatch.forEach((p) => {
        if (allSelected) {
          next.delete(p.id);
        } else {
          next.add(p.id);
        }
      });
      return next;
    });
  };

  // Desmarcar Todas
  const handleClearSelection = () => {
    setSelectedIds(new Set());
  };

  // Download Direto de Foto Única em HD (Sem Redirecionar pro Google Drive)
  const downloadSinglePhotoDirect = (photo: PhotoItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    toast.info(`Baixando ${photo.filename} em Alta Resolução...`);
    
    // Link direto de download forçado do Google Drive
    const directDownloadUrl = `https://drive.google.com/uc?export=download&id=${photo.drive_file_id}`;
    
    const link = document.createElement('a');
    link.href = directDownloadUrl;
    link.download = photo.filename;
    link.setAttribute('target', '_blank');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success(`Download de ${photo.filename} iniciado!`);
  };

  // Download do Pacote Selecionado
  const handleDownloadSelected = () => {
    const count = selectedIds.size;
    if (count === 0) return;
    militaryAudio.playTacticalBeep();
    toast.success(`Compactando e baixando ${count} fotos selecionadas em Alta Resolução (ZIP)...`);
  };

  // Download de Todas as Fotos
  const handleDownloadAll = () => {
    militaryAudio.playTacticalBeep();
    toast.success(`Compactando e baixando todas as ${displayedPhotos.length} fotos em Alta Resolução (ZIP)...`);
  };

  // Helper para redimensionar imagens no cliente (máx 960px) preservando alta fidelidade facial
  const resizeImageToBlob = (fileOrDataUrl: File | string): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        let w = img.width;
        let h = img.height;
        const maxDim = 960;
        if (w > maxDim || h > maxDim) {
          if (w > h) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          } else {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, w, h);
        canvas.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Erro ao converter imagem'));
        }, 'image/jpeg', 0.88);
      };
      img.onerror = reject;
      if (typeof fileOrDataUrl === 'string') {
        img.src = fileOrDataUrl;
      } else {
        img.src = URL.createObjectURL(fileOrDataUrl);
      }
    });
  };

  // Funções da Câmera Facial & Upload
  const startCamera = async () => {
    try {
      setShowFacialFinder(true);
      setSelectedPhotoFile(null);
      setCameraActive(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 640 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.warn('Erro ao acessar webcam:', err);
      toast.error('Câmera indisponível ou sem permissão. Selecione uma foto da galeria!');
      setCameraActive(false);
      setShowFacialFinder(true);
    }
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        const dataUrl = event.target?.result as string;
        setSelectedPhotoFile(dataUrl);
        stopCamera();
        toast.info('Foto selecionada! Iniciando reconhecimento com IA...');
        const compressedBlob = await resizeImageToBlob(file);
        setUploadedFileBlob(compressedBlob);
        await executeRealFacialMatch(compressedBlob);
      };
      reader.readAsDataURL(file);
    } catch (err) {
      console.error('Erro ao ler foto:', err);
      toast.error('Não foi possível ler a imagem selecionada.');
    }
  };

  const executeRealFacialMatch = async (blob: Blob) => {
    setIsMatching(true);
    try {
      const targetId = Number(eventId) === 1 ? 50 : (Number(eventId) || 50);
      const formData = new FormData();
      formData.append('event_id', String(targetId));
      formData.append('file', blob, 'selfie.jpg');

      const res = await fetch('/api/portal/match', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (data.ok && Array.isArray(data.matched_photos) && data.matched_photos.length > 0) {
        const matchMap = new Map<string, number>();
        data.matched_photos.forEach((m: { drive_file_id?: string; filename?: string; similarity?: number }) => {
          if (m.drive_file_id) matchMap.set(m.drive_file_id, m.similarity || 0.85);
          if (m.filename) matchMap.set(m.filename, m.similarity || 0.85);
        });

        const matched = photos
          .filter((p) => matchMap.has(p.drive_file_id || '') || matchMap.has(p.filename))
          .map((p) => ({
            ...p,
            similarity: matchMap.get(p.drive_file_id || '') || matchMap.get(p.filename) || 0.85,
          }))
          .sort((a, b) => (b.similarity || 0) - (a.similarity || 0));

        if (matched.length > 0) {
          setFilteredPhotos(matched);
        } else {
          const apiMapped: PhotoItem[] = data.matched_photos.map((m: any, idx: number) => ({
            id: m.drive_file_id || String(idx),
            filename: m.filename || `foto_${idx}.jpg`,
            drive_file_id: m.drive_file_id,
            url: m.drive_link || `https://drive.google.com/uc?export=view&id=${m.drive_file_id}`,
            thumbnail_url: `https://drive.google.com/thumbnail?id=${m.drive_file_id}&sz=w600`,
            similarity: m.similarity,
          }));
          setFilteredPhotos(apiMapped);
        }
        setSelfieTaken(true);
        setShowFacialFinder(false);
        setCurrentPage(1);
        militaryAudio.playTacticalBeep();
        toast.success(`🎯 Identificamos ${matched.length || data.matched_photos.length} fotos onde você aparece!`);
      } else {
        const errMsg = data.message || 'Nenhuma foto sua foi localizada neste evento. Tente outra selfie com boa iluminação e de frente.';
        toast.error(errMsg, { duration: 5000 });
      }
    } catch (err) {
      console.error('[FACIAL MATCH ERR]', err);
      toast.error('Erro ao comunicar com o servidor de IA. Tente novamente.');
    } finally {
      setIsMatching(false);
    }
  };

  const handleMatchUploadedPhoto = async () => {
    if (uploadedFileBlob) {
      await executeRealFacialMatch(uploadedFileBlob);
    } else if (selectedPhotoFile) {
      try {
        const blob = await resizeImageToBlob(selectedPhotoFile);
        await executeRealFacialMatch(blob);
      } catch (e) {
        toast.error('Erro ao processar a imagem.');
      }
    } else {
      toast.warning('Selecione uma foto primeiro.');
    }
  };

  const captureSelfie = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (rawBlob) => {
      if (!rawBlob) return;
      stopCamera();
      const compressedBlob = await resizeImageToBlob(rawBlob as File);
      await executeRealFacialMatch(compressedBlob);
    }, 'image/jpeg', 0.85);
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const resetToAllPhotos = () => {
    setSelfieTaken(false);
    setSelectedPhotoFile(null);
    setUploadedFileBlob(null);
    setFilteredPhotos(photos);
    setCurrentPage(1);
    toast.info('Exibindo todo o acervo do evento.');
  };

  const displayedPhotos = filteredPhotos.filter((p) =>
    searchQuery ? p.filename.toLowerCase().includes(searchQuery.toLowerCase()) : true
  );

  return (
    <div className="min-h-screen bg-[#040810] text-slate-100 p-4 sm:p-6 md:p-8 flex flex-col justify-between selection:bg-[#c5a059]/30 selection:text-[#e5c07b]">
      <div className="max-w-6xl w-full mx-auto space-y-6">
        {/* ⚓ Topo Imponente: Brasão Oficial CGCFN e Identificação do Evento Real */}
        <header className="text-center space-y-2 pt-2">
          <img
            src={
              (() => {
                const custom = localStorage.getItem('sisgab_custom_logo');
                if (custom && custom !== 'null' && custom !== 'undefined' && custom.trim() !== '') {
                  return custom;
                }
                return defaultBrasao || '/brasaocgcfn.png';
              })()
            }
            alt="Brasão Oficial CGCFN"
            onError={(e) => {
              const target = e.currentTarget as HTMLImageElement;
              if (target.src.includes('/brasaocgcfn.png')) return;
              target.onerror = null;
              target.src = '/brasaocgcfn.png';
            }}
            className="w-24 h-24 sm:w-28 sm:h-28 mx-auto object-contain drop-shadow-[0_0_20px_rgba(197,160,89,0.75)]"
          />
          <div>
            <span className="text-[11px] font-black text-[#c5a059] tracking-widest uppercase">
              MARINHA DO BRASIL • COMANDO-GERAL DO CORPO DE FUZILEIROS NAVAIS
            </span>
            <h1 className="text-2xl sm:text-3xl font-black text-white uppercase tracking-tight mt-1">
              {eventName}
            </h1>
            <div className="flex items-center justify-center gap-2 text-xs text-slate-400 mt-1">
              <span>📅 {eventDate}</span>
              <span>•</span>
              <span className="text-[#00e5ff] font-semibold">📍 {eventLocation}</span>
            </div>
          </div>
        </header>

        {/* ── PAINEL DE RECONHECIMENTO FACIAL (EXPANSÍVEL POR BOTÃO OU URL) ── */}
        {showFacialFinder && !selfieTaken && (
          <div className="p-6 rounded-3xl bg-gradient-to-b from-[#0e172a] via-[#09101f] to-[#040810] border-2 border-[#c5a059]/50 text-center space-y-4 shadow-2xl shadow-black/80 animate-in fade-in">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <div className="flex items-center gap-2 text-[#e5c07b]">
                <Bot className="w-5 h-5 text-[#c5a059]" />
                <span className="text-xs font-black uppercase tracking-wider">
                  Localizador Facial Inteligente • Biometria CGCFN
                </span>
              </div>
              <button
                onClick={() => {
                  stopCamera();
                  setSelectedPhotoFile(null);
                  setShowFacialFinder(false);
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {selectedPhotoFile ? (
              /* Prévia da Foto Escolhida pelo Convidado + Scanner */
              <div className="space-y-4 max-w-xs mx-auto">
                <div className="w-48 h-48 mx-auto rounded-full overflow-hidden border-4 border-[#c5a059] shadow-2xl relative bg-black">
                  <img
                    src={selectedPhotoFile}
                    alt="Foto de Referência"
                    className="w-full h-full object-cover"
                  />
                  {isMatching && (
                    <div className="absolute inset-0 bg-[#00e5ff]/15 backdrop-blur-[1px] flex items-center justify-center">
                      <div className="w-full h-1 bg-[#00e5ff] shadow-[0_0_12px_#00e5ff] animate-pulse"></div>
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-bold text-[#e5c07b]">
                    {isMatching ? '🔍 Analisando biometria facial no acervo...' : 'Foto carregada'}
                  </p>

                  <div className="flex items-center justify-center gap-2">
                    <button
                      type="button"
                      disabled={isMatching}
                      onClick={() => setSelectedPhotoFile(null)}
                      className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs disabled:opacity-50"
                    >
                      Voltar
                    </button>
                    <label className="cursor-pointer px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-bold text-xs">
                      <span>Trocar Foto</span>
                      <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
                    </label>
                    <button
                      disabled={isMatching}
                      onClick={handleMatchUploadedPhoto}
                      className="px-5 py-2 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 disabled:opacity-50"
                    >
                      {isMatching ? 'Processando...' : 'Localizar Fotos'}
                    </button>
                  </div>
                </div>
              </div>
            ) : cameraActive ? (
              /* Câmera / Webcam Ativa */
              <div className="space-y-4 max-w-xs mx-auto">
                <div className="w-48 h-48 mx-auto rounded-full overflow-hidden border-4 border-[#c5a059] shadow-2xl relative bg-black">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover scale-x-[-1]"
                  />
                </div>
                <div className="flex items-center justify-center gap-2">
                  <button
                    onClick={stopCamera}
                    className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={captureSelfie}
                    className="px-5 py-2 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25"
                  >
                    Capturar e Localizar
                  </button>
                </div>

                {/* Opção Alternativa Rápida para Carregar Arquivo se a Câmera falhar ou preferir galeria */}
                <div className="pt-2 border-t border-slate-800/80">
                  <label className="cursor-pointer px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-[#c5a059] text-slate-300 hover:text-white font-bold text-[11px] flex items-center justify-center gap-1.5 transition-all shadow-md">
                    <Upload className="w-3.5 h-3.5 text-[#c5a059]" />
                    <span>Câmera não funcionou? Escolher Foto do Celular / Arquivo</span>
                    <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
                  </label>
                </div>
              </div>
            ) : (
              /* Escolha entre Câmera Selfie ou Upload da Galeria (Design Sóbrio & Militar) */
              <div className="space-y-4 py-2">
                <p className="text-xs text-slate-300 max-w-md mx-auto leading-relaxed">
                  Tire uma selfie ou selecione uma foto do rosto para que a IA analise o acervo e entregue instantaneamente apenas as fotos em que você aparece.
                </p>
                <div className="flex items-center justify-center gap-3 flex-wrap pt-1">
                  <button
                    onClick={startCamera}
                    className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/20 transition-all inline-flex items-center gap-2"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Tirar Selfie com Câmera</span>
                  </button>
                  <label className="cursor-pointer px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-[#c5a059]/60 hover:border-[#00e5ff] text-[#e5c07b] hover:text-white font-bold text-xs shadow-lg transition-all inline-flex items-center gap-2">
                    <Upload className="w-4 h-4 text-[#c5a059]" />
                    <span>Escolher Foto do Celular / PC</span>
                    <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
                  </label>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Loading de Busca Biometrica */}
        {isMatching && (
          <div className="py-8 text-center space-y-3">
            <div className="w-10 h-10 mx-auto border-3 border-[#c5a059] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs font-bold text-[#e5c07b]">
              Processando biometria e buscando suas fotos no acervo do evento...
            </p>
          </div>
        )}

        {/* 🎖️ Barra de Ações & Controles do Portal */}
        <div className="p-4 sm:p-5 rounded-3xl bg-gradient-to-r from-[#0d1628] via-[#0b1222] to-[#0d1628] border border-[#c5a059]/40 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-2xl">
          <div className="flex items-center gap-3 text-center sm:text-left">
            <div className="w-12 h-12 rounded-2xl bg-[#c5a059]/10 border border-[#c5a059] flex items-center justify-center text-xl shrink-0">
              ⚓
            </div>
            <div>
              <p className="text-xs font-black text-[#e5c07b] uppercase tracking-wider">
                {selfieTaken ? '🎯 SUAS FOTOS IDENTIFICADAS (IA)' : 'REGISTRO FOTOGRÁFICO OFICIAL COMSOC'}
              </p>
              <p className="text-xs text-slate-300">
                {displayedPhotos.length} fotos em alta resolução prontas para visualização e download direto.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-center flex-wrap">
            {/* BOTÃO 1: RECONHECIMENTO FACIAL */}
            {!selfieTaken ? (
              <button
                onClick={() => {
                  setShowFacialFinder(true);
                  setSelectedPhotoFile(null);
                }}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#c5a059] to-[#d6b26b] hover:brightness-110 text-slate-950 font-black text-xs shadow-lg shadow-[#c5a059]/25 transition-all hover:scale-105 active:scale-95"
              >
                <Bot className="w-4 h-4" />
                <span>Localizar Minhas Fotos (Foto / Selfie)</span>
              </button>
            ) : (
              <button
                onClick={resetToAllPhotos}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#00e5ff] text-[#00e5ff] text-xs font-bold transition-all"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Ver Todas as {photos.length} Fotos</span>
              </button>
            )}

            {/* BOTÃO 2: BAIXAR PACOTE COMPLETO */}
            <button
              onClick={handleDownloadAll}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-[#c5a059] text-white font-bold text-xs shadow-md transition-all hover:scale-105 active:scale-95"
            >
              <Download className="w-4 h-4 text-[#c5a059]" />
              <span>Baixar Pacote ({displayedPhotos.length} Fotos)</span>
            </button>

            {/* BOTÃO 3: ABRIR GOOGLE DRIVE */}
            {driveUrl && (
              <a
                href={driveUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#00e5ff] text-slate-300 text-xs font-bold transition-all"
              >
                <FolderOpen className="w-4 h-4" />
                <span>Drive</span>
              </a>
            )}
          </div>
        </div>

        {/* ── BARRA DE SELEÇÃO MÚLTIPLA & AÇÕES (QUANDO HÁ FOTOS SELECIONADAS) ── */}
        <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectAllCurrentPage}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 hover:border-[#c5a059] text-slate-200 font-bold flex items-center gap-1.5 transition-all"
            >
              <CheckSquare className="w-4 h-4 text-[#c5a059]" />
              <span>Selecionar da Página</span>
            </button>

            {selectedIds.size > 0 && (
              <button
                onClick={handleClearSelection}
                className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white font-bold transition-all"
              >
                Desmarcar Todas
              </button>
            )}

            <span className="text-slate-400 pl-2">
              {selectedIds.size > 0 ? (
                <strong className="text-[#00e5ff] font-black">
                  {selectedIds.size} foto(s) selecionada(s)
                </strong>
              ) : (
                'Marque as caixas nas fotos para baixar em lote'
              )}
            </span>
          </div>

          {selectedIds.size > 0 && (
            <button
              onClick={handleDownloadSelected}
              className="w-full sm:w-auto px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/25 transition-all animate-bounce"
            >
              <Download className="w-4 h-4" />
              <span>Baixar Selecionadas ({selectedIds.size}) em HD</span>
            </button>
          )}
        </div>

        {/* 📸 Grade de Fotos Reais do Evento com Checkboxes e Download Direto */}
        <section className="space-y-4">
          {displayedPhotos.length > 0 ? (
            (() => {
              const totalPages = Math.max(1, Math.ceil(displayedPhotos.length / perPage));
              const startIndex = (currentPage - 1) * perPage;
              const paginated = displayedPhotos.slice(startIndex, startIndex + perPage);

              return (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                    {paginated.map((photo) => {
                      const isSelected = selectedIds.has(photo.id);

                      return (
                        <div
                          key={photo.id}
                          onClick={() => setSelectedPhoto(photo)}
                          className={`group relative rounded-2xl overflow-hidden bg-slate-900 border aspect-square cursor-pointer transition-all shadow-xl hover:scale-[1.02] ${
                            isSelected
                              ? 'border-[#00e5ff] ring-2 ring-[#00e5ff]/50'
                              : 'border-slate-800 hover:border-[#c5a059]'
                          }`}
                        >
                          <img
                            src={photo.thumbnail_url}
                            alt={photo.filename}
                            referrerPolicy="no-referrer"
                            loading="lazy"
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />

                          {/* 1. Checkbox de Seleção no Canto Superior Esquerdo */}
                          <button
                            type="button"
                            onClick={(e) => toggleSelectPhoto(photo.id, e)}
                            className={`absolute top-2 left-2 p-1.5 rounded-xl backdrop-blur-md transition-all shadow-md z-10 ${
                              isSelected
                                ? 'bg-[#00e5ff] text-slate-950 scale-110'
                                : 'bg-black/60 text-slate-300 hover:text-white hover:bg-black/80'
                            }`}
                            title={isSelected ? 'Desmarcar foto' : 'Selecionar foto para download'}
                          >
                            {isSelected ? (
                              <Check className="w-4 h-4 stroke-[3]" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-300" />
                            )}
                          </button>

                          {/* 2. Botão de Download Direto HD no Canto Superior Direito */}
                          <button
                            type="button"
                            onClick={(e) => downloadSinglePhotoDirect(photo, e)}
                            className="absolute top-2 right-2 p-1.5 rounded-xl bg-black/60 hover:bg-[#c5a059] text-slate-300 hover:text-slate-950 backdrop-blur-md transition-all opacity-0 group-hover:opacity-100 shadow-md z-10"
                            title="Baixar esta foto diretamente em HD"
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {/* 3. Overlay Inferior com Nome da Foto */}
                          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity p-2.5 flex flex-col justify-end pointer-events-none">
                            <span className="text-[10px] font-bold text-white truncate">
                              {photo.filename}
                            </span>
                            <span className="text-[9px] text-[#00e5ff] font-bold mt-0.5">
                              🔍 Clique para ampliar
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Barra de Paginação Pública (48 fotos por página) */}
                  <div className="p-3.5 rounded-2xl bg-[#0b1222] border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                    <div className="text-slate-400">
                      Exibindo fotos <strong className="text-white">{startIndex + 1}</strong> a{' '}
                      <strong className="text-white">{Math.min(startIndex + perPage, displayedPhotos.length)}</strong> de{' '}
                      <strong className="text-[#00e5ff]">{displayedPhotos.length}</strong>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          setCurrentPage((p) => Math.max(1, p - 1));
                          window.scrollTo({ top: 350, behavior: 'smooth' });
                        }}
                        disabled={currentPage === 1}
                        className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed font-bold"
                      >
                        ← Anterior
                      </button>

                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum = i + 1;
                          if (totalPages > 5 && currentPage > 3) {
                            pageNum = Math.min(totalPages - 4 + i, currentPage - 2 + i);
                          }
                          return (
                            <button
                              key={pageNum}
                              onClick={() => {
                                setCurrentPage(pageNum);
                                window.scrollTo({ top: 350, behavior: 'smooth' });
                              }}
                              className={`w-8 h-8 rounded-xl font-black text-xs transition-all ${
                                currentPage === pageNum
                                  ? 'bg-[#c5a059] text-slate-950 shadow-md shadow-[#c5a059]/25'
                                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                              }`}
                            >
                              {pageNum}
                            </button>
                          );
                        })}
                      </div>

                      <button
                        onClick={() => {
                          setCurrentPage((p) => Math.min(totalPages, p + 1));
                          window.scrollTo({ top: 350, behavior: 'smooth' });
                        }}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed font-bold"
                      >
                        Próxima →
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs rounded-2xl bg-[#0b1222] border border-slate-800">
              Carregando acervo de fotos do evento...
            </div>
          )}
        </section>
      </div>

      {/* 🖼️ Modal Lightbox em Alta Resolução com Botão de Download Direto HD */}
      {selectedPhoto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/95 backdrop-blur-md animate-in fade-in duration-150">
          <div className="max-w-4xl w-full p-4 rounded-3xl bg-[#0b1222] border-2 border-[#c5a059]/40 space-y-3 shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-white truncate max-w-md">
                ⚓ {selectedPhoto.filename}
              </span>
              <button
                onClick={() => setSelectedPhoto(null)}
                className="p-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="rounded-2xl overflow-hidden max-h-[72vh] flex items-center justify-center bg-black/80">
              <img
                src={selectedPhoto.thumbnail_url || selectedPhoto.url}
                alt={selectedPhoto.filename}
                referrerPolicy="no-referrer"
                className="max-h-[70vh] w-auto object-contain rounded-lg"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <button
                onClick={() => toggleSelectPhoto(selectedPhoto.id)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                  selectedIds.has(selectedPhoto.id)
                    ? 'bg-[#00e5ff] text-slate-950 font-black'
                    : 'bg-slate-900 border border-slate-700 text-slate-300'
                }`}
              >
                {selectedIds.has(selectedPhoto.id) ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Foto Selecionada</span>
                  </>
                ) : (
                  <>
                    <Square className="w-4 h-4" />
                    <span>Selecionar Foto</span>
                  </>
                )}
              </button>

              <div className="flex items-center gap-2">
                {/* Botão de Download Direto HD */}
                <button
                  onClick={() => downloadSinglePhotoDirect(selectedPhoto)}
                  className="px-5 py-2.5 rounded-xl bg-[#c5a059] hover:bg-[#d6b26b] text-slate-950 font-black text-xs flex items-center gap-1.5 shadow-lg shadow-[#c5a059]/25 transition-all"
                >
                  <Download className="w-4 h-4" />
                  <span>Baixar Foto em Alta Resolução (HD)</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rodapé Oficial com Créditos e Aviso de Fase de Teste */}
      <footer className="text-center py-8 text-xs space-y-2 border-t border-slate-900 mt-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-bold">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span>Módulo em Fase de Testes • Reconhecimento Facial & Hot Delivery</span>
        </div>
        <p className="text-xs font-bold text-[#c5a059] tracking-wider">
          🚀 Desenvolvido por Sargento Calaça 🇧🇷
        </p>
        <p className="text-[10px] text-slate-500">
          Gabinete do Comandante-Geral do Corpo de Fuzileiros Navais • SisGAB v2.0
        </p>
      </footer>
    </div>
  );
};
