-- ELFIS Accounting Engine V2 — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_chart_of_accounts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    plan_code VARCHAR(32) NOT NULL DEFAULT 'pcg_fr',
    account_code VARCHAR(16) NOT NULL,
    account_label VARCHAR(255) NOT NULL DEFAULT '',
    account_type VARCHAR(32),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_coa_org_plan_code UNIQUE (organization_id, plan_code, account_code)
);

CREATE INDEX IF NOT EXISTS ix_elfis_coa_org
    ON elfis_chart_of_accounts (organization_id);

CREATE TABLE IF NOT EXISTS elfis_accounting_engine_proposals (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    direction VARCHAR(32) NOT NULL DEFAULT 'purchase',
    document_type VARCHAR(64) NOT NULL DEFAULT 'invoice',
    source_document_id VARCHAR(64),
    source_kind VARCHAR(32),
    source_version INTEGER NOT NULL DEFAULT 1,
    legacy_proposal_id VARCHAR(36),
    journal_code VARCHAR(16),
    journal_label VARCHAR(128),
    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
    amount_ht DOUBLE PRECISION,
    amount_vat DOUBLE PRECISION,
    amount_ttc DOUBLE PRECISION,
    vat_rate DOUBLE PRECISION,
    lines JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    comments JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanations JSONB NOT NULL DEFAULT '[]'::jsonb,
    consistency JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_score DOUBLE PRECISION,
    confidence_detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_snapshot JSONB,
    actor_user_id INTEGER REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_aep_status CHECK (
        status IN (
            'draft', 'generated', 'requires_review',
            'regenerated', 'superseded', 'cancelled'
        )
    ),
    CONSTRAINT uq_elfis_aep_doc_ver UNIQUE (
        organization_id, source_document_id, source_version
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_aep_org
    ON elfis_accounting_engine_proposals (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_aep_status
    ON elfis_accounting_engine_proposals (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_aep_source
    ON elfis_accounting_engine_proposals (source_document_id);

CREATE TABLE IF NOT EXISTS elfis_accounting_learning_memory (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    memory_key VARCHAR(255) NOT NULL,
    supplier_or_customer VARCHAR(255),
    document_type VARCHAR(64),
    direction VARCHAR(32),
    preferred_expense_account VARCHAR(16),
    preferred_revenue_account VARCHAR(16),
    preferred_vat_account VARCHAR(16),
    preferred_third_party_account VARCHAR(16),
    preferred_journal VARCHAR(16),
    vat_rate DOUBLE PRECISION,
    hit_count INTEGER NOT NULL DEFAULT 1,
    source VARCHAR(32) NOT NULL DEFAULT 'user_validation',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_used_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_alm_org_key UNIQUE (organization_id, memory_key)
);

CREATE INDEX IF NOT EXISTS ix_elfis_alm_org_key
    ON elfis_accounting_learning_memory (organization_id, memory_key);

CREATE TABLE IF NOT EXISTS elfis_accounting_engine_audit (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    proposal_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    actor_user_id INTEGER REFERENCES users(id),
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_aea_org
    ON elfis_accounting_engine_audit (organization_id, created_at);
