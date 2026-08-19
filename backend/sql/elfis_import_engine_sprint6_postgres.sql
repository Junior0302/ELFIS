-- ELFIS Import Engine V1 (Sprint 6) — PostgreSQL idempotent

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
            'import_pending', 'importing', 'imported', 'import_completed',
            'import_failed', 'rollback_completed', 'import_cancelled',
            'archive_pending', 'archived',
            'rejected', 'failed', 'cancelled'
        )
    );

CREATE TABLE IF NOT EXISTS elfis_import_runs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36),
    document_intake_item_id VARCHAR(36) NOT NULL REFERENCES elfis_document_intake_items(id),
    universal_document_id VARCHAR(32),
    validation_session_id VARCHAR(36) NOT NULL,
    validation_version INTEGER NOT NULL DEFAULT 1,
    extraction_id VARCHAR(36),
    schema_name VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    fingerprint VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64),
    error_message TEXT,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    report_id VARCHAR(36),
    duration_ms INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    rolled_back_at TIMESTAMP,
    rollback_reason VARCHAR(64),
    actor_user_id INTEGER REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_imp_status CHECK (
        status IN (
            'pending', 'mapping', 'transaction_started', 'committing',
            'completed', 'failed', 'rolling_back', 'rollback_completed', 'cancelled'
        )
    ),
    CONSTRAINT ck_elfis_imp_progress CHECK (
        progress_percent >= 0 AND progress_percent <= 100 AND version >= 1
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_imp_org_created
    ON elfis_import_runs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_item
    ON elfis_import_runs (document_intake_item_id);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_status
    ON elfis_import_runs (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_mig
    ON elfis_import_runs (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_doc_val_ver
    ON elfis_import_runs (
        organization_id, document_intake_item_id, validation_session_id, validation_version
    );
CREATE INDEX IF NOT EXISTS ix_elfis_imp_fingerprint
    ON elfis_import_runs (organization_id, fingerprint);

CREATE TABLE IF NOT EXISTS elfis_import_fingerprints (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    fingerprint VARCHAR(64) NOT NULL,
    document_intake_item_id VARCHAR(36) NOT NULL,
    validation_session_id VARCHAR(36) NOT NULL,
    validation_version INTEGER NOT NULL,
    import_run_id VARCHAR(36) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deactivated_at TIMESTAMP,
    CONSTRAINT uq_elfis_imp_fp UNIQUE (organization_id, fingerprint)
);

CREATE INDEX IF NOT EXISTS ix_elfis_imp_fp_run
    ON elfis_import_fingerprints (import_run_id);

CREATE TABLE IF NOT EXISTS elfis_import_artifacts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    import_run_id VARCHAR(36) NOT NULL REFERENCES elfis_import_runs(id),
    entity_kind VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    label VARCHAR(255),
    snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    rolled_back BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    rolled_back_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_elfis_imp_art_run
    ON elfis_import_artifacts (import_run_id);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_art_entity
    ON elfis_import_artifacts (entity_kind, entity_id);

CREATE TABLE IF NOT EXISTS elfis_import_reports (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    import_run_id VARCHAR(36) NOT NULL REFERENCES elfis_import_runs(id),
    version INTEGER NOT NULL DEFAULT 1,
    documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    duration_ms INTEGER,
    actor_user_id INTEGER REFERENCES users(id),
    report JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_imp_rep_ver UNIQUE (import_run_id, version)
);

CREATE INDEX IF NOT EXISTS ix_elfis_imp_rep_run
    ON elfis_import_reports (import_run_id);

CREATE TABLE IF NOT EXISTS elfis_import_audit_log (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    import_run_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    entity_kind VARCHAR(64),
    entity_id VARCHAR(64),
    actor_user_id INTEGER REFERENCES users(id),
    reason TEXT,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_imp_audit_run
    ON elfis_import_audit_log (import_run_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_imp_audit_org
    ON elfis_import_audit_log (organization_id, created_at);
