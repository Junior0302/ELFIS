-- ELFIS Document Extraction Engine V1 (Sprint 4) — PostgreSQL idempotent

-- Lifecycle intake déjà étendu en Sprint 3 (ocr_pending, extraction_*, awaiting_validation)

CREATE TABLE IF NOT EXISTS elfis_document_extractions (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36),
    document_intake_item_id VARCHAR(36) NOT NULL REFERENCES elfis_document_intake_items(id),
    universal_document_id VARCHAR(32),
    analysis_report_id VARCHAR(36),
    schema_name VARCHAR(64) NOT NULL,
    schema_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    extraction_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    status VARCHAR(48) NOT NULL DEFAULT 'pending',
    status_scope VARCHAR(64) NOT NULL DEFAULT 'active',
    strategy VARCHAR(64),
    provider VARCHAR(64),
    model_name VARCHAR(128),
    prompt_version VARCHAR(64),
    input_fingerprint VARCHAR(64) NOT NULL,
    output_fingerprint VARCHAR(64),
    structured_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    field_provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall_confidence DOUBLE PRECISION,
    critical_fields_confidence DOUBLE PRECISION,
    completeness_score DOUBLE PRECISION,
    consistency_score DOUBLE PRECISION,
    confidence_level VARCHAR(32),
    requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    current_step VARCHAR(64),
    text_source VARCHAR(64),
    text_character_count INTEGER,
    estimated_cost DOUBLE PRECISION,
    actual_cost DOUBLE PRECISION,
    token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_extr_status CHECK (
        status IN (
            'pending', 'queued', 'preparing', 'extracting', 'normalizing',
            'reconciling', 'validating', 'completed', 'completed_with_warnings',
            'awaiting_human_validation', 'failed', 'cancelled', 'superseded',
            'ocr_pending'
        )
    ),
    CONSTRAINT ck_elfis_extr_progress CHECK (
        progress_percent >= 0 AND progress_percent <= 100 AND version >= 1
    ),
    CONSTRAINT uq_elfis_extr_active_fingerprint UNIQUE (
        organization_id, input_fingerprint, status_scope
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_extr_org_created
    ON elfis_document_extractions (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_item
    ON elfis_document_extractions (document_intake_item_id);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_status
    ON elfis_document_extractions (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_fingerprint
    ON elfis_document_extractions (organization_id, input_fingerprint);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_universal
    ON elfis_document_extractions (universal_document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_session
    ON elfis_document_extractions (migration_session_id);

CREATE TABLE IF NOT EXISTS elfis_document_extraction_attempts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    extraction_id VARCHAR(36) NOT NULL REFERENCES elfis_document_extractions(id),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    extractor_name VARCHAR(64) NOT NULL,
    provider VARCHAR(64),
    model_name VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    input_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    estimated_cost DOUBLE PRECISION,
    actual_cost DOUBLE PRECISION,
    latency_ms INTEGER,
    error_code VARCHAR(64),
    error_message_safe TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_extr_attempt_extr
    ON elfis_document_extraction_attempts (extraction_id);
CREATE INDEX IF NOT EXISTS ix_elfis_extr_attempt_org
    ON elfis_document_extraction_attempts (organization_id, created_at);
