-- Script SQL para o módulo Estúdio Gráfico no Supabase
-- Executar no Query Editor do Supabase dashboard (https://supabase.com)

-- 1. Tabela de Artes Gráficas dos Usuários
CREATE TABLE IF NOT EXISTS artes_graficas (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  titulo TEXT NOT NULL,
  criado_por TEXT,         -- Username do usuário no SisGAB
  tipo TEXT DEFAULT 'arte',-- 'convite', 'cracha', 'cartao', 'post', 'banner'
  json_data JSONB NOT NULL,-- Objeto Fabric.js/yft-design completo (frente + verso)
  thumbnail_url TEXT,      -- Imagem de miniatura (Base64 ou URL)
  pdf_url TEXT,            -- URL do arquivo PDF no Supabase Storage (se gerado)
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now(),
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Index para buscas rápidas por usuário e tipo
CREATE INDEX IF NOT EXISTS idx_artes_criado_por ON artes_graficas(criado_por);
CREATE INDEX IF NOT EXISTS idx_artes_tipo ON artes_graficas(tipo);

-- 2. Tabela de Templates Gráficos Institucionais
CREATE TABLE IF NOT EXISTS templates_graficos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  titulo TEXT NOT NULL,
  categoria TEXT,          -- 'Cerimonial', 'RP', 'Gabinete', 'Redes Sociais'
  json_data JSONB NOT NULL,
  thumbnail_url TEXT,
  publico BOOLEAN DEFAULT true,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Habilitar RLS (Row Level Security) permissivo para o serviço do SisGAB
ALTER TABLE artes_graficas ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates_graficos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Acesso Total Artes Graficas" ON artes_graficas FOR ALL USING (true);
CREATE POLICY "Acesso Total Templates Graficos" ON templates_graficos FOR ALL USING (true);
