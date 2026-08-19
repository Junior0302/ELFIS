-- ELFIS Storage & Document Registry RC2.4 étape 1
-- Métadonnées uniquement — pas de binaires volumineux.
-- Idempotent (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS elfis_storage_objects (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(32) NOT NULL DEFAULT 'local',
    namespace VARCHAR(128) NOT NULL DEFAULT 'default',
    object_key VARCHAR(512) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    safe_filename VARCHAR(255) NOT NULL,
    mime_type_declared VARCHAR(128),
    mime_type_detected VARCHAR(128),
    extension VARCHAR(32),
    size_bytes BIGINT NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    encryption_status VARCHAR(32) NOT NULL DEFAULT 'none',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    created_by_user_id INTEGER REFERENCES users(id),
    organization_id INTEGER REFERENCES organizations(id),
    metadata_json JSONB,
    CONSTRAINT uq_elfis_storage_object_key UNIQUE (provider, namespace, object_key)
);

CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_org
    ON elfis_storage_objects (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_status
    ON elfis_storage_objects (status);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_checksum
    ON elfis_storage_objects (checksum_sha256);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_created
    ON elfis_storage_objects (created_at);

CREATE TABLE IF NOT EXISTS elfis_document_records (
    id VARCHAR(36) PRIMARY KEY,
    document_type VARCHAR(64) NOT NULL DEFAULT 'file',
    title VARCHAR(255) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    product VARCHAR(64),
    current_storage_object_id VARCHAR(36) REFERENCES elfis_storage_objects(id),
    owner_user_id INTEGER REFERENCES users(id),
    source VARCHAR(32) NOT NULL DEFAULT 'upload',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMP WITHOUT TIME ZONE,
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS ix_elfis_document_records_org
    ON elfis_document_records (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_status
    ON elfis_document_records (status);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_type
    ON elfis_document_records (document_type);
CREATE INDEX IF NOT EXISTS ix_elfis_document_records_created
    ON elfis_document_records (created_at);

CREATE TABLE IF NOT EXISTS elfis_document_links (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL REFERENCES elfis_document_records(id) ON DELETE CASCADE,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    relation_type VARCHAR(64) NOT NULL DEFAULT 'attachment',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(id),
    CONSTRAINT uq_elfis_document_link UNIQUE (document_id, entity_type, entity_id, relation_type)
);

CREATE INDEX IF NOT EXISTS ix_elfis_document_links_document
    ON elfis_document_links (document_id);
CREATE INDEX IF NOT EXISTS ix_elfis_document_links_entity
    ON elfis_document_links (entity_type, entity_id);
