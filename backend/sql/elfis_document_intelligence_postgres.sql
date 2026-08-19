-- ELFIS Document Intelligence V1 — Postgres

CREATE TABLE IF NOT EXISTS elfis_document_text_extractions (
    id VARCHAR(36) PRIMARY KEY,
    extraction_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    vault_document_id VARCHAR(36) NOT NULL,
    document_version INTEGER NOT NULL DEFAULT 1,
    extractor_name VARCHAR(64) NOT NULL,
    extractor_version VARCHAR(32),
    provider VARCHAR(64),
    status VARCHAR(32) NOT NULL,
    mime_type VARCHAR(128),
    filename VARCHAR(512),
    file_size_bytes BIGINT,
    page_count INTEGER,
    text_content TEXT,
    text_hash VARCHAR(64),
    text_length INTEGER NOT NULL DEFAULT 0,
    quality_score NUMERIC(5, 4),
    confidence NUMERIC(5, 4),
    requires_ocr BOOLEAN NOT NULL DEFAULT FALSE,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    language VARCHAR(16),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
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
    CONSTRAINT uq_elfis_doc_text_extraction_id UNIQUE (extraction_id),
    CONSTRAINT uq_elfis_doc_text_org_doc_ver
        UNIQUE (organization_id, vault_document_id, document_version),
    CONSTRAINT ck_elfis_doc_text_status CHECK (
        status IN (
            'pending', 'processing', 'completed', 'blocked',
            'failed', 'requires_ocr', 'requires_review', 'cancelled'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_organization_id
    ON elfis_document_text_extractions (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_vault_document_id
    ON elfis_document_text_extractions (vault_document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_status
    ON elfis_document_text_extractions (status);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_extractor_name
    ON elfis_document_text_extractions (extractor_name);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_created_at
    ON elfis_document_text_extractions (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_job_id
    ON elfis_document_text_extractions (job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_correlation_id
    ON elfis_document_text_extractions (correlation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_text_idempotency_key
    ON elfis_document_text_extractions (idempotency_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_doc_text_idempotency_key
    ON elfis_document_text_extractions (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';
