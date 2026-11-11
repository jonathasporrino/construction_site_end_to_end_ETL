-- Fictitious construction ERP (source system for the portfolio pipeline), DuckDB dialect. All data is synthetic.
CREATE SCHEMA IF NOT EXISTS erp;

CREATE TABLE erp.empresa (
    empresa_id    integer PRIMARY KEY,
    razao_social  text NOT NULL UNIQUE,
    cnpj          char(18) NOT NULL,          -- formatted, deliberately invalid check digits
    tipo          text NOT NULL CHECK (tipo IN ('SOCIO', 'FORNECEDOR', 'CLIENTE'))
);

CREATE TABLE erp.plano_contas (
    codigo               varchar(10) PRIMARY KEY,
    descricao            text NOT NULL,
    regra_classificacao  text,
    natureza             text NOT NULL CHECK (natureza IN ('RECEITA', 'DESPESA'))
);

CREATE TABLE erp.operacao (
    op_codigo  integer PRIMARY KEY,
    descricao  text NOT NULL
);

CREATE TABLE erp.obra (                       -- one cost center = one construction work
    numero                integer PRIMARY KEY,
    descricao             text NOT NULL,
    tipo_cliente          text,
    grupo                 text,
    unidade_negocio       text,
    controle              text,
    gerente               text,
    uf                    char(2),
    cliente               text,
    tipo                  text NOT NULL CHECK (tipo IN ('SCP', 'CONSÓRCIO', 'PRÓPRIA', 'ADMINISTRATIVO')),
    pct_empresa_parceira  numeric(5,4),
    valor_contrato        numeric(16,2),
    pct_fisico            numeric(6,4),
    credito_inss          text,
    dt_inicio             date NOT NULL,
    dt_fim                date NOT NULL,
    ativo                 boolean NOT NULL,
    contas_inss           text                -- pipe-separated AP account codes
);

CREATE TABLE erp.obra_socio (                 -- partners of each work (SCP / consortium)
    numero_obra       integer REFERENCES erp.obra,
    socio_seq         smallint NOT NULL CHECK (socio_seq BETWEEN 1 AND 24),
    empresa_id        integer NOT NULL REFERENCES erp.empresa,
    pct_participacao  numeric(6,4) NOT NULL,
    pct_tac           numeric(6,4) NOT NULL,
    PRIMARY KEY (numero_obra, socio_seq)
);

CREATE TABLE erp.lancamento (                 -- grain: one financial document installment
    lancamento_id         integer PRIMARY KEY,
    numero_obra           integer NOT NULL REFERENCES erp.obra,
    plano_conta           varchar(10) NOT NULL REFERENCES erp.plano_contas,
    contraparte_id        integer NOT NULL REFERENCES erp.empresa,
    empresa               text NOT NULL,
    empresa_recbto_pagto  text NOT NULL,
    numdoc                text NOT NULL,
    dt_doc                date NOT NULL,
    dt_venc               date NOT NULL,
    dt_vencorig           date NOT NULL,
    dt_recto              date,
    dt_movbanc            date,
    historico             text,
    op_codigo             integer NOT NULL REFERENCES erp.operacao,
    ri                    text,
    valor_previsto        numeric(16,2) NOT NULL,
    valor_compromissado   numeric(16,2) NOT NULL,
    valor_efetuado        numeric(16,2) NOT NULL,
    tx_adm_prev           numeric(16,2),
    tx_adm_comp           numeric(16,2),
    tx_adm_efetu          numeric(16,2),
    aprec                 char(2) NOT NULL CHECK (aprec IN ('AP', 'AR')),
    apstatus              text,
    apcontacdg            text,
    apconta               text,
    arcontacdg            text,
    arconta               text,
    ripedidos             text,
    arrec                 text,
    arstatus              text,
    status                text NOT NULL CHECK (status IN ('REALIZADO', 'A REALIZAR')),
    created_at            timestamp NOT NULL,
    updated_at            timestamp NOT NULL   -- watermark column for incremental extraction
);
CREATE INDEX ix_lancamento_updated_at ON erp.lancamento (updated_at);
