-- ============================================================
-- SETUP DO BANCO — SDR Milhas
-- Execute no Supabase: SQL Editor > New Query > Run
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- LEADS
CREATE TABLE IF NOT EXISTS leads (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    whatsapp            VARCHAR(20) UNIQUE NOT NULL,
    nome                VARCHAR(255),
    etapa               VARCHAR(50)  DEFAULT 'ABERTURA',
    status              VARCHAR(50)  DEFAULT 'NOVO',
    temperatura         VARCHAR(20)  DEFAULT 'INDEFINIDO',
    gasto_mensal        VARCHAR(100),
    gasto_faixa         VARCHAR(50),
    cartoes_atuais      TEXT,
    destino_viagem      VARCHAR(255),
    milhas_atuais       VARCHAR(100),
    tem_milhas          BOOLEAN,
    observacoes         TEXT,
    tentativas_followup INT          DEFAULT 0,
    bloqueado_followup  BOOLEAN      DEFAULT FALSE,
    ultima_interacao    TIMESTAMPTZ  DEFAULT NOW(),
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);

-- MENSAGENS
CREATE TABLE IF NOT EXISTS mensagens (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id          UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    direcao          VARCHAR(10) NOT NULL CHECK (direcao IN ('RECEBIDA','ENVIADA')),
    conteudo         TEXT NOT NULL,
    etapa_no_momento VARCHAR(50),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- AGENDAMENTOS
CREATE TABLE IF NOT EXISTS agendamentos (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id    UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    data_call  VARCHAR(255),
    link_call  VARCHAR(500),
    status     VARCHAR(20) DEFAULT 'AGENDADO' CHECK (status IN ('AGENDADO','REALIZADO','CANCELADO','REAGENDADO')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- FICHAS DE REPASSE
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
    enviada_ao_fechador BOOLEAN     DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- FOLLOWUPS
CREATE TABLE IF NOT EXISTS followups (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id      UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tipo         VARCHAR(30) NOT NULL CHECK (tipo IN ('PRIMEIRO_FOLLOWUP','SEGUNDO_FOLLOWUP')),
    disparado    BOOLEAN     DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ÍNDICES
CREATE INDEX IF NOT EXISTS idx_leads_whatsapp  ON leads(whatsapp);
CREATE INDEX IF NOT EXISTS idx_leads_status    ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_followup  ON leads(bloqueado_followup, tentativas_followup);
CREATE INDEX IF NOT EXISTS idx_mensagens_lead  ON mensagens(lead_id);
CREATE INDEX IF NOT EXISTS idx_agend_lead      ON agendamentos(lead_id);
