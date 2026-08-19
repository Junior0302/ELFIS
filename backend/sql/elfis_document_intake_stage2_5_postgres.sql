-- ELFIS Document Intake Stage 2.5 — PostgreSQL idempotent
-- Universal Document ID, lifecycle, upload sessions, fingerprint V2, storage fields

-- Compteur DOC-YYYY-XXXXXXXX
CREATE TABLE IF NOT EXISTS elfis_document_doc_id_counters (
    year INTEGER PRIMARY KEY,
    last_value BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Upload sessions
CREATE TABLE IF NOT EXISTS elfis_document_upload_sessions (
    id VARCHAR(36) PRIMARY KEY,
    upload_session_token VARCHAR(64) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) NOT NULL REFERENCES elfis_migration_sessions(id),
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(32) NOT NULL DEFAULT 'created',
    source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
    display_label VARCHAR(128),
    expected_file_count INTEGER NOT NULL DEFAULT 0,
    received_file_count INTEGER NOT NULL DEFAULT 0,
    validated_file_count INTEGER NOT NULL DEFAULT 0,
    duplicate_file_count INTEGER NOT NULL DEFAULT 0,
    rejected_file_count INTEGER NOT NULL DEFAULT 0,
    cancelled_file_count INTEGER NOT NULL DEFAULT 0,
    quarantined_file_count INTEGER NOT NULL DEFAULT 0,
    expected_total_bytes BIGINT NOT NULL DEFAULT 0,
    received_total_bytes BIGINT NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    expires_at TIMESTAMP,
    analytics JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_upload_session_token UNIQUE (upload_session_token),
    CONSTRAINT ck_elfis_upload_session_status CHECK (
        status IN (
            'created', 'uploading', 'paused', 'validating',
            'completed', 'partially_completed', 'failed', 'cancelled', 'expired'
        )
    ),
    CONSTRAINT ck_elfis_upload_session_counts CHECK (
        expected_file_count >= 0 AND received_file_count >= 0
        AND validated_file_count >= 0 AND duplicate_file_count >= 0
        AND rejected_file_count >= 0 AND cancelled_file_count >= 0
        AND quarantined_file_count >= 0
        AND expected_total_bytes >= 0 AND received_total_bytes >= 0
        AND version >= 1
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_upload_sess_org
    ON elfis_document_upload_sessions (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_upload_sess_mig
    ON elfis_document_upload_sessions (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_upload_sess_status
    ON elfis_document_upload_sessions (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_upload_sess_token
    ON elfis_document_upload_sessions (organization_id, upload_session_token);

-- Colonnes additives sur items (idempotent)
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS universal_document_id VARCHAR(32);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS upload_session_id VARCHAR(36);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(64);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_provider VARCHAR(32) DEFAULT 'local';
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_location VARCHAR(512);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_bucket_or_root VARCHAR(255);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_object_key VARCHAR(512);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_version VARCHAR(64);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS storage_metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS fingerprint JSONB DEFAULT '{}'::jsonb;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS fingerprint_version INTEGER DEFAULT 2;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS duplicate_type VARCHAR(16) DEFAULT 'none';
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS duplicate_of_item_id VARCHAR(36);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS duplicate_confidence DOUBLE PRECISION;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS duplicate_reason VARCHAR(128);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS client_upload_id VARCHAR(128);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS chunk_count INTEGER;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS received_chunk_count INTEGER;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS multipart_upload_id VARCHAR(128);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP;
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;

-- FK upload_session (après table)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_elfis_intake_upload_session'
    ) THEN
        ALTER TABLE elfis_document_intake_items
            ADD CONSTRAINT fk_elfis_intake_upload_session
            FOREIGN KEY (upload_session_id)
            REFERENCES elfis_document_upload_sessions(id);
    END IF;
END $$;

-- Élargir contrainte status (lifecycle futur inclus)
ALTER TABLE elfis_document_intake_items DROP CONSTRAINT IF EXISTS ck_elfis_intake_status;
ALTER TABLE elfis_document_intake_items
    ADD CONSTRAINT ck_elfis_intake_status CHECK (
        status IN (
            'uploaded', 'validating', 'validated', 'quarantined', 'duplicate',
            'ready_for_analysis', 'analysis_pending', 'analyzing',
            'ocr_pending', 'ocr_processing', 'ocr_completed',
            'classification_pending', 'classifying', 'classified',
            'extraction_pending', 'extracting', 'extracted',
            'awaiting_validation', 'validated_by_user',
            'import_pending', 'importing', 'imported',
            'archive_pending', 'archived',
            'rejected', 'failed', 'cancelled'
        )
    );

-- Indexes / unicité
CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_universal_document_id
    ON elfis_document_intake_items (universal_document_id)
    WHERE universal_document_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_elfis_intake_universal_id
    ON elfis_document_intake_items (universal_document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_upload_session
    ON elfis_document_intake_items (upload_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_intake_idempotency
    ON elfis_document_intake_items (organization_id, idempotency_key);

-- Lifecycle entries (append-only)
CREATE TABLE IF NOT EXISTS elfis_document_lifecycle_entries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_intake_item_id VARCHAR(36) NOT NULL REFERENCES elfis_document_intake_items(id),
    from_status VARCHAR(64),
    to_status VARCHAR(64) NOT NULL,
    reason_code VARCHAR(64),
    actor_type VARCHAR(32) NOT NULL DEFAULT 'system',
    actor_user_id INTEGER REFERENCES users(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_lifecycle_actor CHECK (
        actor_type IN ('user', 'system', 'worker', 'admin', 'scanner')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_lifecycle_org_item
    ON elfis_document_lifecycle_entries (organization_id, document_intake_item_id);
CREATE INDEX IF NOT EXISTS ix_elfis_lifecycle_occurred
    ON elfis_document_lifecycle_entries (organization_id, occurred_at);

-- Backfill sûr (idempotent)
UPDATE elfis_document_intake_items
SET lifecycle_status = status
WHERE lifecycle_status IS NULL OR lifecycle_status = '';

UPDATE elfis_document_intake_items
SET storage_provider = COALESCE(NULLIF(storage_provider, ''), 'local')
WHERE storage_provider IS NULL OR storage_provider = '';

UPDATE elfis_document_intake_items
SET storage_object_key = storage_key
WHERE storage_object_key IS NULL AND storage_key IS NOT NULL;

UPDATE elfis_document_intake_items
SET storage_bucket_or_root = COALESCE(storage_bucket_or_root, 'document_intake')
WHERE storage_bucket_or_root IS NULL;

UPDATE elfis_document_intake_items
SET fingerprint = jsonb_build_object(
    'schema_version', 2,
    'sha256', checksum_sha256,
    'size_bytes', size_bytes,
    'detected_mime_type', detected_mime,
    'normalized_extension', extension,
    'content_signature', NULL,
    'first_block_hash', NULL,
    'last_block_hash', NULL,
    'page_count', NULL,
    'first_page_hash', NULL,
    'last_page_hash', NULL,
    'archive_entry_count', NULL
)
WHERE fingerprint IS NULL
   OR fingerprint = '{}'::jsonb
   OR NOT (fingerprint ? 'schema_version');

UPDATE elfis_document_intake_items
SET fingerprint_version = 2
WHERE fingerprint_version IS NULL OR fingerprint_version < 2;

UPDATE elfis_document_intake_items
SET duplicate_type = CASE
    WHEN is_duplicate IS TRUE THEN 'exact'
    ELSE COALESCE(NULLIF(duplicate_type, ''), 'none')
END
WHERE duplicate_type IS NULL OR (is_duplicate IS TRUE AND duplicate_type = 'none');

UPDATE elfis_document_intake_items
SET duplicate_of_item_id = duplicate_of_id
WHERE duplicate_of_item_id IS NULL AND duplicate_of_id IS NOT NULL;

UPDATE elfis_document_intake_items
SET duplicate_confidence = 1.0
WHERE is_duplicate IS TRUE AND duplicate_confidence IS NULL;

UPDATE elfis_document_intake_items
SET last_activity_at = COALESCE(updated_at, created_at, NOW())
WHERE last_activity_at IS NULL;

UPDATE elfis_document_intake_items
SET version = COALESCE(version, 1)
WHERE version IS NULL OR version < 1;

-- Backfill Universal Document ID via compteur (batch)
DO $$
DECLARE
    r RECORD;
    y INTEGER;
    next_val BIGINT;
    new_id TEXT;
BEGIN
    FOR r IN
        SELECT id, EXTRACT(YEAR FROM COALESCE(created_at, NOW()))::INTEGER AS yr
        FROM elfis_document_intake_items
        WHERE universal_document_id IS NULL
        ORDER BY created_at ASC NULLS LAST, id ASC
    LOOP
        y := r.yr;
        INSERT INTO elfis_document_doc_id_counters (year, last_value, updated_at)
        VALUES (y, 0, NOW())
        ON CONFLICT (year) DO NOTHING;

        UPDATE elfis_document_doc_id_counters
        SET last_value = last_value + 1,
            updated_at = NOW()
        WHERE year = y
        RETURNING last_value INTO next_val;

        new_id := 'DOC-' || y::TEXT || '-' || lpad(next_val::TEXT, 8, '0');
        UPDATE elfis_document_intake_items
        SET universal_document_id = new_id
        WHERE id = r.id AND universal_document_id IS NULL;
    END LOOP;
END $$;
