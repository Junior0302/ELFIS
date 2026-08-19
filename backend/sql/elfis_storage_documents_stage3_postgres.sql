-- ELFIS Storage RC2.4 étape 3 — versions, legal hold, rétention, tombstones
-- Idempotent. Aucune migration destructive.

-- Colonnes DocumentRecord (compat SQLite/Postgres via IF NOT EXISTS côté scripts ;
-- Postgres : ADD COLUMN IF NOT EXISTS)

ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS current_version_id VARCHAR(36);
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS purged_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS retention_deadline TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS purge_status VARCHAR(32) NOT NULL DEFAULT 'none';
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS deleted_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE elfis_document_records
    ADD COLUMN IF NOT EXISTS delete_reason VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_elfis_document_records_org_status_created
    ON elfis_document_records (organization_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_deleted_at
    ON elfis_document_records (deleted_at);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_retention
    ON elfis_document_records (retention_deadline);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_purge_status
    ON elfis_document_records (purge_status);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_current_version
    ON elfis_document_records (current_version_id);

CREATE TABLE IF NOT EXISTS elfis_document_versions (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES elfis_document_records(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    storage_object_id VARCHAR(36) NOT NULL REFERENCES elfis_storage_objects(id),
    status VARCHAR(32) NOT NULL DEFAULT 'current',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(id),
    source VARCHAR(32) NOT NULL DEFAULT 'upload',
    change_reason VARCHAR(255),
    original_filename VARCHAR(255) NOT NULL DEFAULT '',
    size_bytes BIGINT NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64),
    mime_type VARCHAR(128),
    metadata_json JSONB,
    superseded_at TIMESTAMP WITHOUT TIME ZONE,
    archived_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_elfis_document_version_num UNIQUE (document_id, version_number),
    CONSTRAINT ck_elfis_document_version_positive CHECK (version_number > 0)
);

CREATE INDEX IF NOT EXISTS ix_elfis_document_versions_document
    ON elfis_document_versions (document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_versions_document_created
    ON elfis_document_versions (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_document_versions_storage
    ON elfis_document_versions (storage_object_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_versions_status_created
    ON elfis_document_versions (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_document_versions_deleted_at
    ON elfis_document_versions (deleted_at);

CREATE TABLE IF NOT EXISTS elfis_document_legal_holds (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES elfis_document_records(id) ON DELETE CASCADE,
    reason VARCHAR(500) NOT NULL,
    reference VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    placed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    placed_by_user_id INTEGER REFERENCES users(id),
    released_at TIMESTAMP WITHOUT TIME ZONE,
    released_by_user_id INTEGER REFERENCES users(id),
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS ix_elfis_legal_holds_document
    ON elfis_document_legal_holds (document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_legal_holds_document_active
    ON elfis_document_legal_holds (document_id, active);

CREATE TABLE IF NOT EXISTS elfis_document_tombstones (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL UNIQUE,
    organization_id INTEGER NOT NULL,
    document_type VARCHAR(64),
    title_redacted VARCHAR(64),
    source VARCHAR(32),
    created_at_original TIMESTAMP WITHOUT TIME ZONE,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    purged_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    purged_by_user_id INTEGER,
    purge_reason VARCHAR(255),
    checksum_prefix VARCHAR(16),
    version_count INTEGER NOT NULL DEFAULT 0,
    audit_reference VARCHAR(64),
    metadata_json JSONB,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS ix_elfis_tombstones_org
    ON elfis_document_tombstones (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_tombstones_purged
    ON elfis_document_tombstones (purged_at);

CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_status_created
    ON elfis_storage_objects (status, created_at);
