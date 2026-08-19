-- ELFIS Accounting Pipeline V1 — Postgres

CREATE TABLE IF NOT EXISTS elfis_accounting_proposals (
    id VARCHAR(36) PRIMARY KEY,
    proposal_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    vault_document_id VARCHAR(36) NOT NULL,
    document_analysis_id VARCHAR(36),
    document_version INTEGER NOT NULL DEFAULT 1,
    document_type VARCHAR(64) NOT NULL,
    document_number VARCHAR(128),
    document_date DATE,
    due_date DATE,
    supplier_name VARCHAR(255),
    customer_name VARCHAR(255),
    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
    amount_ht NUMERIC(14, 2),
    amount_vat NUMERIC(14, 2),
    amount_ttc NUMERIC(14, 2),
    status VARCHAR(32) NOT NULL,
    current_stage VARCHAR(64) NOT NULL,
    document_validation JSONB NOT NULL DEFAULT '{}'::jsonb,
    financial_validation JSONB NOT NULL DEFAULT '{}'::jsonb,
    accounting_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence NUMERIC(5, 4),
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(64) NOT NULL DEFAULT 'elfis_pipeline',
    job_id VARCHAR(36),
    correlation_id VARCHAR(36),
    source_event_id VARCHAR(36),
    idempotency_key VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    validated_at TIMESTAMP WITHOUT TIME ZONE,
    rejected_at TIMESTAMP WITHOUT TIME ZONE,
    validated_by_user_id INTEGER REFERENCES users(id),
    rejected_by_user_id INTEGER REFERENCES users(id),
    rejection_reason TEXT,
    CONSTRAINT uq_elfis_acc_proposal_id UNIQUE (proposal_id),
    CONSTRAINT uq_elfis_acc_proposal_org_doc_ver
        UNIQUE (organization_id, vault_document_id, document_version),
    CONSTRAINT ck_elfis_acc_proposal_status CHECK (
        status IN (
            'pending', 'processing', 'validation_failed', 'financial_error',
            'mapping_failed', 'requires_review', 'ready_for_validation',
            'validated', 'rejected', 'cancelled', 'failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_organization_id
    ON elfis_accounting_proposals (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_vault_document_id
    ON elfis_accounting_proposals (vault_document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_status
    ON elfis_accounting_proposals (status);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_document_type
    ON elfis_accounting_proposals (document_type);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_created_at
    ON elfis_accounting_proposals (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_job_id
    ON elfis_accounting_proposals (job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_proposal_idempotency_key
    ON elfis_accounting_proposals (idempotency_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_acc_proposal_idempotency_key
    ON elfis_accounting_proposals (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

CREATE TABLE IF NOT EXISTS elfis_accounting_entries (
    id VARCHAR(36) PRIMARY KEY,
    entry_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    proposal_id VARCHAR(36) NOT NULL,
    journal_code VARCHAR(16) NOT NULL,
    entry_date DATE NOT NULL,
    reference VARCHAR(128),
    description VARCHAR(500) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
    total_debit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    total_credit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    balanced BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'proposed',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    validated_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_elfis_acc_entry_id UNIQUE (entry_id),
    CONSTRAINT ck_elfis_acc_entry_status CHECK (
        status IN ('draft', 'proposed', 'validated', 'exported', 'cancelled')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_acc_entry_organization_id
    ON elfis_accounting_entries (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_entry_proposal_id
    ON elfis_accounting_entries (proposal_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_entry_status
    ON elfis_accounting_entries (status);

CREATE TABLE IF NOT EXISTS elfis_accounting_entry_lines (
    id VARCHAR(36) PRIMARY KEY,
    line_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    entry_id VARCHAR(36) NOT NULL,
    line_number INTEGER NOT NULL,
    account_code VARCHAR(16) NOT NULL,
    account_label VARCHAR(255),
    third_party_name VARCHAR(255),
    debit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    credit NUMERIC(14, 2) NOT NULL DEFAULT 0,
    vat_rate NUMERIC(6, 3),
    vat_code VARCHAR(32),
    description VARCHAR(500),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_acc_line_id UNIQUE (line_id),
    CONSTRAINT uq_elfis_acc_line_entry_num UNIQUE (entry_id, line_number),
    CONSTRAINT ck_elfis_acc_line_debit CHECK (debit >= 0),
    CONSTRAINT ck_elfis_acc_line_credit CHECK (credit >= 0),
    CONSTRAINT ck_elfis_acc_line_single_side CHECK (NOT (debit > 0 AND credit > 0))
);

CREATE INDEX IF NOT EXISTS ix_elfis_acc_line_organization_id
    ON elfis_accounting_entry_lines (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_line_entry_id
    ON elfis_accounting_entry_lines (entry_id);

CREATE TABLE IF NOT EXISTS elfis_accounting_reviews (
    id VARCHAR(36) PRIMARY KEY,
    review_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    proposal_id VARCHAR(36) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    previous_data JSONB,
    new_data JSONB,
    comment TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_acc_review_id UNIQUE (review_id)
);

CREATE INDEX IF NOT EXISTS ix_elfis_acc_review_organization_id
    ON elfis_accounting_reviews (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_review_proposal_id
    ON elfis_accounting_reviews (proposal_id);
CREATE INDEX IF NOT EXISTS ix_elfis_acc_review_created_at
    ON elfis_accounting_reviews (created_at);
