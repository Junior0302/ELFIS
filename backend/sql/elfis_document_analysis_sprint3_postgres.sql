-- ELFIS Document Analysis Pipeline V1 (Sprint 3) — PostgreSQL idempotent

-- Étendre CHECK status intake pour ready_for_ai (déjà largement ouvert en 2.5)
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
            'awaiting_validation', 'validated_by_user',
            'import_pending', 'importing', 'imported',
            'archive_pending', 'archived',
            'rejected', 'failed', 'cancelled'
        )
    );

CREATE TABLE IF NOT EXISTS elfis_document_analysis_reports (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_intake_item_id VARCHAR(36) NOT NULL REFERENCES elfis_document_intake_items(id),
    universal_document_id VARCHAR(32),
    migration_session_id VARCHAR(36),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    schema_version INTEGER NOT NULL DEFAULT 1,
    analysis_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    report JSONB NOT NULL DEFAULT '{}'::jsonb,
    need_ocr BOOLEAN,
    classification_label VARCHAR(64),
    classification_confidence DOUBLE PRECISION,
    language_code VARCHAR(16),
    language_confidence DOUBLE PRECISION,
    quality_score INTEGER,
    orientation_degrees INTEGER,
    page_count INTEGER,
    detected_format VARCHAR(32),
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_code VARCHAR(64),
    error_message TEXT,
    processing_time_ms INTEGER,
    current_step VARCHAR(64),
    steps_completed INTEGER NOT NULL DEFAULT 0,
    steps_total INTEGER NOT NULL DEFAULT 12,
    version INTEGER NOT NULL DEFAULT 1,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_analysis_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed')
    ),
    CONSTRAINT ck_elfis_analysis_quality CHECK (
        quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)
    ),
    CONSTRAINT ck_elfis_analysis_steps CHECK (
        steps_completed >= 0 AND steps_total > 0 AND version >= 1
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_analysis_org_created
    ON elfis_document_analysis_reports (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_analysis_item
    ON elfis_document_analysis_reports (document_intake_item_id);
CREATE INDEX IF NOT EXISTS ix_elfis_analysis_session
    ON elfis_document_analysis_reports (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_analysis_status
    ON elfis_document_analysis_reports (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_analysis_universal
    ON elfis_document_analysis_reports (universal_document_id);
