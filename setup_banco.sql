-- ============================================================
-- SETUP DO BANCO DE DADOS — SDR Milhas
-- Execute esse SQL no Supabase: SQL Editor > New Query
-- ============================================================

-- Habilita a extensão UUID (para gerar IDs automáticos)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ─────────────────────────────────────────────
-- TABELA: leads
-- Armazena todos os leads capturados pelo WhatsApp
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    whatsapp            VARCHAR(20) UNIQUE NOT NULL,
    nome                VARCHAR(255),
    etapa               VARCHAR(50) DEFAULT 'ABERTURA',
    status              VARCHAR(50) DEFAULT 'NOVO',
    temperatura         VARCHAR(20) DEFAULT 'INDEFINIDO',
    gasto_mensal        VARCHAR(100),
    gasto_faixa         VARCHAR(50),
    cartoes_atuais      TEXT,
    destino_viagem      VARCHAR(255),
    milhas_atuais       VARCHAR(100),
    tem_milhas          BOOLEAN,
    observacoes         TEXT,
    tentativas_followup INT DEFAULT 0,
    bloqueado_followup  BOOLEAN DEFAULT FALSE,
    ultima_interacao    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- TABELA: mensagens
-- Histórico completo de todas as mensagens
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mensagens (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id             UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    direcao             VARCHAR(10) NOT NULL CHECK (direcao IN ('RECEBIDA', 'ENVIADA')),
    conteudo            TEXT NOT NULL,
    etapa_no_momento    VARCHAR(50),
    evolution_msg_id    VARCHAR(255) UNIQUE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- TABELA: agendamentos
-- Calls agendadas com o fechador (Pedro)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agendamentos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id             UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    data_call           VARCHAR(255),
    link_call           VARCHAR(500),
    status              VARCHAR(20) DEFAULT 'AGENDADO' CHECK (status IN ('AGENDADO','REALIZADO','CANCELADO','REAGENDADO')),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- TABELA: fichas_repasse
-- Fichas enviadas ao fechador quando call é agendada
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fichas_repasse (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id             UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    agendamento_id      UUID REFERENCES agendamentos(id),
    nome                VARCHAR(255),
    whatsapp            VARCHAR(20),
    data_call           VARCHAR(255),
    gasto_mensal        VARCHAR(100),
    cartoes             TEXT,
    temperatura         VARCHAR(20),
    enviada_ao_fechador BOOLEAN DEFAULT FALSE,
    data_envio          TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- TABELA: followups
-- Log dos follow-ups automáticos enviados
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS followups (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id             UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tipo                VARCHAR(30) NOT NULL CHECK (tipo IN ('PRIMEIRO_FOLLOWUP', 'SEGUNDO_FOLLOWUP')),
    agendado_para       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disparado           BOOLEAN DEFAULT TRUE,
    data_disparo        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- ─────────────────────────────────────────────
-- FUNÇÃO: atualiza updated_at automaticamente
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION atualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();

CREATE TRIGGER trigger_agendamentos_updated_at
    BEFORE UPDATE ON agendamentos
    FOR EACH ROW EXECUTE FUNCTION atualizar_updated_at();


-- ─────────────────────────────────────────────
-- ÍNDICES para melhorar a performance das buscas
-- ─────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_leads_whatsapp ON leads(whatsapp);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_followup ON leads(bloqueado_followup, tentativas_followup);
CREATE INDEX IF NOT EXISTS idx_mensagens_lead_id ON mensagens(lead_id);
CREATE INDEX IF NOT EXISTS idx_agendamentos_lead_id ON agendamentos(lead_id);
