-- ELFIS Validation & Mapping Center V1 (Sprint 5) — PostgreSQL idempotent

ALTER TABLE elfis_document_intake_items DROP CONSTRAINT IF EXISTS ck_elfis_intake_status;
ALTER TABLE elfis_document_intake_items
    ADD CONSTRAINT ck_elfis_intake_status CHECK (
        status IN (
            'uploaded', 'validating', 'validated', 'quarantined', 'duplicate',
            'ready_for_analysis', 'analysis_pending', 'analyzing',
            'ocr_pending', 'ocr_processing', 'ocr_completed',
            'classification_pending', 'classifying', 'classified',
            'ready_for_ai',
            'extraction_pending', 'extracting', 'extracted',
            'awaiting_validation', 'human_validating', 'validated_by_user',
            'ready_for_import',
            'import_pending', 'importing', 'imported',
            'archive_pending', 'archived',
            'rejected', 'failed', 'cancelled'
        )
    );

CREATE TABLE IF NOT EXISTS elfis_validation_sessions (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36),
    document_intake_item_id VARCHAR(36) NOT NULL REFERENCES elfis_document_intake_items(id),
    universal_document_id VARCHAR(32),
    extraction_id VARCHAR(36) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    validated_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    field_states JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    duplicate_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    matching_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    validated_by_user_id INTEGER REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_val_status CHECK (
        status IN (
            'pending', 'validating', 'validated',
            'ready_for_import', 'rejected', 'cancelled'
        )
    ),
    CONSTRAINT ck_elfis_val_progress CHECK (
        progress_percent >= 0 AND progress_percent <= 100 AND version >= 1
    ),
    CONSTRAINT uq_elfis_val_item_extraction UNIQUE (
        organization_id, document_intake_item_id, extraction_id
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_val_org_created
    ON elfis_validation_sessions (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_val_item
    ON elfis_validation_sessions (document_intake_item_id);
CREATE INDEX IF NOT EXISTS ix_elfis_val_session_mig
    ON elfis_validation_sessions (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_val_status
    ON elfis_validation_sessions (organization_id, status);

CREATE TABLE IF NOT EXISTS elfis_validation_fields (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    validation_session_id VARCHAR(36) NOT NULL REFERENCES elfis_validation_sessions(id),
    field_path VARCHAR(255) NOT NULL,
    ai_value JSONB,
    current_value JSONB,
    status VARCHAR(32) NOT NULL DEFAULT 'unknown',
    confidence DOUBLE PRECISION,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_val_field_path UNIQUE (validation_session_id, field_path),
    CONSTRAINT ck_elfis_val_field_status CHECK (
        status IN ('unknown', 'accepted', 'edited', 'rejected')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_val_field_session
    ON elfis_validation_fields (validation_session_id);

CREATE TABLE IF NOT EXISTS elfis_validation_history (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    validation_session_id VARCHAR(36) NOT NULL REFERENCES elfis_validation_sessions(id),
    field_path VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    action VARCHAR(32) NOT NULL,
    reason TEXT,
    actor_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_val_hist_session
    ON elfis_validation_history (validation_session_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_val_hist_org
    ON elfis_validation_history (organization_id, created_at);

CREATE TABLE IF NOT EXISTS elfis_validation_duplicates (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    validation_session_id VARCHAR(36) NOT NULL REFERENCES elfis_validation_sessions(id),
    other_document_id VARCHAR(36),
    other_universal_document_id VARCHAR(32),
    severity VARCHAR(32) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    matched_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT,
    resolution VARCHAR(32) NOT NULL DEFAULT 'unresolved',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_val_dup_session
    ON elfis_validation_duplicates (validation_session_id);

CREATE TABLE IF NOT EXISTS elfis_validation_matches (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    validation_session_id VARCHAR(36) NOT NULL REFERENCES elfis_validation_sessions(id),
    party_role VARCHAR(32) NOT NULL,
    category VARCHAR(32) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    contact_id INTEGER,
    contact_label VARCHAR(255),
    matched_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT,
    resolution VARCHAR(32) NOT NULL DEFAULT 'unresolved',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_val_match_session
    ON elfis_validation_matches (validation_session_id);
