-- ELFIS AI Engine V1 — Postgres
-- Tables distinctes des events / jobs / notifications.

CREATE TABLE IF NOT EXISTS elfis_ai_executions (
    id VARCHAR(36) PRIMARY KEY,
    execution_id VARCHAR(36) NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    task_name VARCHAR(128) NOT NULL,
    task_version INTEGER NOT NULL DEFAULT 1,
    provider VARCHAR(64) NOT NULL,
    model VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    input_reference_type VARCHAR(64),
    input_reference_id VARCHAR(128),
    input_hash VARCHAR(64),
    result JSONB,
    result_schema_version INTEGER,
    prompt_version VARCHAR(64),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost NUMERIC(14, 6),
    currency VARCHAR(8) DEFAULT 'USD',
    latency_ms INTEGER,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    job_id VARCHAR(36),
    correlation_id VARCHAR(36),
    source_event_id VARCHAR(36),
    idempotency_key VARCHAR(255),
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_ai_executions_execution_id UNIQUE (execution_id),
    CONSTRAINT ck_elfis_ai_executions_status CHECK (
        status IN (
            'pending', 'processing', 'completed', 'failed',
            'cancelled', 'blocked', 'requires_review'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_organization_id ON elfis_ai_executions (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_task_name ON elfis_ai_executions (task_name);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_provider ON elfis_ai_executions (provider);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_model ON elfis_ai_executions (model);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_status ON elfis_ai_executions (status);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_created_at ON elfis_ai_executions (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_job_id ON elfis_ai_executions (job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_correlation_id ON elfis_ai_executions (correlation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_input_ref
    ON elfis_ai_executions (input_reference_type, input_reference_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_executions_idempotency_key ON elfis_ai_executions (idempotency_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_ai_executions_idempotency_key
    ON elfis_ai_executions (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

CREATE TABLE IF NOT EXISTS elfis_ai_usage (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    execution_id VARCHAR(36) NOT NULL REFERENCES elfis_ai_executions (execution_id),
    provider VARCHAR(64) NOT NULL,
    model VARCHAR(128) NOT NULL,
    task_name VARCHAR(128) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost NUMERIC(14, 6),
    currency VARCHAR(8) DEFAULT 'USD',
    request_date DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_ai_usage_organization_id ON elfis_ai_usage (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_usage_execution_id ON elfis_ai_usage (execution_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_usage_request_date ON elfis_ai_usage (request_date);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_usage_task_name ON elfis_ai_usage (task_name);

CREATE TABLE IF NOT EXISTS elfis_document_analyses (
    id VARCHAR(36) PRIMARY KEY,
    analysis_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    vault_document_id VARCHAR(36) NOT NULL,
    document_version INTEGER NOT NULL DEFAULT 1,
    document_type VARCHAR(64),
    classification JSONB,
    extraction JSONB,
    quality JSONB,
    accounting_mapping JSONB,
    status VARCHAR(32) NOT NULL,
    confidence NUMERIC(5, 4),
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    current_stage VARCHAR(64),
    ai_execution_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_elfis_document_analyses_analysis_id UNIQUE (analysis_id),
    CONSTRAINT uq_elfis_document_analyses_org_doc_ver
        UNIQUE (organization_id, vault_document_id, document_version),
    CONSTRAINT ck_elfis_document_analyses_status CHECK (
        status IN (
            'pending', 'classifying', 'extracting', 'validating',
            'completed', 'failed', 'requires_review', 'blocked'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_document_analyses_organization_id
    ON elfis_document_analyses (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_analyses_vault_document_id
    ON elfis_document_analyses (vault_document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_analyses_status
    ON elfis_document_analyses (status);
CREATE INDEX IF NOT EXISTS ix_elfis_document_analyses_created_at
    ON elfis_document_analyses (created_at);
