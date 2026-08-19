import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { LoginPage } from './pages/LoginPage';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Dashboard } from './pages/admin/Dashboard';
import { DailyAttendance } from './pages/admin/DailyAttendance';
import { NewDemandForm } from './pages/admin/NewDemandForm';
import { DemandApproval } from './pages/admin/DemandApproval';
import { KanbanTasks } from './pages/admin/KanbanTasks';
import { SeatingMaster } from './pages/admin/SeatingMaster';
import { RSVPManagement } from './pages/admin/RSVPManagement';
import { GiftsStock } from './pages/admin/GiftsStock';
import { EquipmentCautela } from './pages/admin/EquipmentCautela';
import { PhotoGalleryAdmin } from './pages/admin/PhotoGalleryAdmin';
import { SisgabTVPlayer } from './pages/tv/SisgabTVPlayer';
import { AICenter } from './pages/admin/AICenter';
import { JarvisVoice } from './pages/admin/JarvisVoice';
import { Birthdays } from './pages/admin/Birthdays';
import { SmartEditor } from './pages/admin/SmartEditor';
import { QRCodeTool } from './pages/admin/QRCodeTool';
import { TelegramMetrics } from './pages/admin/TelegramMetrics';
import { SystemSettings } from './pages/admin/SystemSettings';
import { UserManagement } from './pages/admin/UserManagement';
import { HistoricalArchive } from './pages/admin/HistoricalArchive';
import { GraphicStudio } from './pages/admin/GraphicStudio';
import { InstagramCarouselStudio } from './pages/admin/InstagramCarouselStudio';
import { HelpAbout } from './pages/admin/HelpAbout';
import { RSVPGuestView } from './pages/public/RSVPGuestView';
import { PublicEventGallery } from './pages/public/PublicEventGallery';
import { PublicSurveyView } from './pages/public/PublicSurveyView';
import { SatisfactionSurvey } from './pages/admin/SatisfactionSurvey';
import { AuthorityAlmanac } from './pages/admin/AuthorityAlmanac';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* 🔐 Rota Pública de Autenticação / Login */}
        <Route path="/login" element={<LoginPage />} />

        {/* 🌐 Rota Pública de Confirmação de Convite RSVP (Mobile PWA) */}
        <Route path="/rsvp/:token" element={<RSVPGuestView />} />

        {/* 📸 Rota Pública de Galeria Hot Delivery com Reconhecimento Facial */}
        <Route path="/evento/:id" element={<PublicEventGallery />} />

        {/* ⭐ Rota Pública de Pesquisa de Satisfação Pós-Evento */}
        <Route path="/pesquisa/:token" element={<PublicSurveyView />} />
        <Route path="/pesquisa_evento/:id" element={<PublicSurveyView />} />

        {/* 📺 Rota Telão SisGAB TV Fullscreen Tático */}
        <Route path="/sisgab_tv" element={<SisgabTVPlayer />} />

        {/* 🖥️ Rotas Administrativas Protegidas por Autenticação */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          {/* 🏛️ Bloco 1: Gabinete & Operações Diárias */}
          <Route index element={<Dashboard />} />
          <Route path="presenca" element={<DailyAttendance />} />
          <Route path="comsoc_demandas" element={<NewDemandForm />} />
          <Route path="comsoc_homologar" element={<DemandApproval />} />

          {/* 🎯 Bloco 2: Tarefas & Cerimonial */}
          <Route path="comsoc_tarefas" element={<KanbanTasks />} />
          <Route path="almanaque_autoridades" element={<AuthorityAlmanac />} />
          <Route path="comsoc_assentos" element={<SeatingMaster />} />
          <Route path="comsoc_rsvp" element={<RSVPManagement />} />
          <Route path="pesquisa_satisfacao" element={<SatisfactionSurvey />} />

          {/* 📦 Bloco 3: Logística & Material */}
          <Route path="comsoc_brindes" element={<GiftsStock />} />
          <Route path="comsoc_cautela" element={<EquipmentCautela />} />

          {/* 📣 Bloco 4: Comunicação & Mídia */}
          <Route path="assistente_ia" element={<AICenter />} />
          <Route path="jarvis" element={<JarvisVoice />} />
          <Route path="smart_editor" element={<SmartEditor />} />
          <Route path="estudio_grafico" element={<GraphicStudio />} />
          <Route path="carrossel_instagram" element={<InstagramCarouselStudio />} />
          <Route path="comsoc_galeria" element={<PhotoGalleryAdmin />} />
          <Route path="comsoc_historico" element={<HistoricalArchive />} />
          <Route path="comsoc_aniversariantes" element={<Birthdays />} />
          <Route path="qrcode_generator" element={<QRCodeTool />} />

          {/* ⚙️ Bloco 5: Sistema & Administração */}
          <Route path="telegram_metrics" element={<TelegramMetrics />} />
          <Route path="config" element={<SystemSettings />} />
          <Route path="admin_panel" element={<UserManagement />} />
          <Route path="ajuda_sobre" element={<HelpAbout />} />

          {/* Fallback inteligente */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
