import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from 'sonner';
import { AuthProvider } from './context/AuthContext';
import './index.css';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
      <Toaster
        position="top-right"
        richColors
        theme="dark"
        toastOptions={{
          style: {
            background: '#0b1222',
            border: '1px solid rgba(197, 160, 89, 0.3)',
            color: '#f8fafc',
          },
        }}
      />
    </AuthProvider>
  </StrictMode>,
);
