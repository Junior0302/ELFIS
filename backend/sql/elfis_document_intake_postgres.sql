-- ELFIS Document Intake Engine V1 — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_document_intake_items (
    id VARCHAR(36) PRIMARY KEY,
    intake_token VARCHAR(64) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) REFERENCES elfis_migration_sessions(id),
    uploaded_by_user_id INTEGER REFERENCES users(id),
    batch_id VARCHAR(36),
    original_filename VARCHAR(255) NOT NULL,
    normalized_filename VARCHAR(255) NOT NULL,
    relative_path VARCHAR(512),
    extension VARCHAR(32) NOT NULL,
    format_id VARCHAR(32) NOT NULL,
    declared_mime VARCHAR(128),
    detected_mime VARCHAR(128),
    mime VARCHAR(128) NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    origin VARCHAR(32) NOT NULL DEFAULT 'api',
    storage_key VARCHAR(512) NOT NULL,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of_id VARCHAR(36),
    quarantine_reason VARCHAR(255),
    reject_reason VARCHAR(255),
    scan_verdict VARCHAR(32),
    extract_later BOOLEAN NOT NULL DEFAULT FALSE,
    preview_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    analysis_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    validated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    notes TEXT,
    CONSTRAINT uq_elfis_intake_token UNIQUE (intake_token),
    CONSTRAINT ck_elfis_intake_status CHECK (
        status IN (
            'uploaded',
            'validated',
            'quarantined',
            'duplicate',
            'ready_for_analysis',
            'rejected',
            'cancelled'
        )
    ),
    CONSTRAINT ck_elfis_intake_size CHECK (size_bytes >= 0)
);

CREATE INDEX IF NOT EXISTS ix_elfis_intake_org_created
    ON elfis_document_intake_items (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_org_status
    ON elfis_document_intake_items (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_session
    ON elfis_document_intake_items (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_checksum
    ON elfis_document_intake_items (organization_id, checksum_sha256);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_batch
    ON elfis_document_intake_items (batch_id);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_org_token
    ON elfis_document_intake_items (organization_id, intake_token);
