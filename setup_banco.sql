-- Tabela principal de leads
CREATE TABLE IF NOT EXISTS leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  nome TEXT,
  whatsapp TEXT UNIQUE,
  email TEXT,
  origem TEXT,
  status TEXT DEFAULT 'novo',
  etapa TEXT DEFAULT 'interesse',
  score INTEGER DEFAULT 0,
  notas TEXT,
  ultimo_contato TIMESTAMPTZ
);

-- Tabela de mensagens trocadas
CREATE TABLE IF NOT EXISTS mensagens (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  papel TEXT,
  conteudo TEXT
);

-- Tabela de follow-ups agendados
CREATE TABLE IF NOT EXISTS followups (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  agendado_para TIMESTAMPTZ,
  mensagem TEXT,
  status TEXT DEFAULT 'pendente'
);

-- Tabela de fichas de repasse
CREATE TABLE IF NOT EXISTS fichas_repasse (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  resumo TEXT,
  enviado_em TIMESTAMPTZ
);

-- Tabela de agendamentos
CREATE TABLE IF NOT EXISTS agendamentos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  data_hora TIMESTAMPTZ,
  tipo TEXT,
  status TEXT DEFAULT 'confirmado'
);

-- Tabela de pipeline de vendas
CREATE TABLE IF NOT EXISTS pipeline_leads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
  etapa TEXT,
  valor_estimado NUMERIC,
  observacoes TEXT
);
