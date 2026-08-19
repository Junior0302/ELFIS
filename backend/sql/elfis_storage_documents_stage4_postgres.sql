-- RC2.4 étape 4 — Storage migrations (idempotent PostgreSQL)

CREATE TABLE IF NOT EXISTS elfis_storage_migrations (
    id VARCHAR(36) PRIMARY KEY,
    storage_object_id VARCHAR(36) NOT NULL REFERENCES elfis_storage_objects(id),
    source_provider VARCHAR(32) NOT NULL,
    source_namespace VARCHAR(128) NOT NULL,
    source_object_key VARCHAR(512) NOT NULL,
    target_provider VARCHAR(32) NOT NULL,
    target_namespace VARCHAR(128) NOT NULL,
    target_object_key VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    verified_at TIMESTAMPTZ NULL,
    checksum_verified BOOLEAN NOT NULL DEFAULT FALSE,
    source_deleted_at TIMESTAMPTZ NULL,
    error_code VARCHAR(64) NULL,
    created_by_user_id INTEGER NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata_json JSONB NULL
);

CREATE INDEX IF NOT EXISTS ix_elfis_storage_migrations_status_created
    ON elfis_storage_migrations (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_migrations_object
    ON elfis_storage_migrations (storage_object_id);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_migrations_source
    ON elfis_storage_migrations (source_provider);
CREATE INDEX IF NOT EXISTS ix_elfis_storage_migrations_target
    ON elfis_storage_migrations (target_provider);

-- Une seule migration « active » par objet (pending/copying/copied/verified)
CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_storage_migration_active
    ON elfis_storage_migrations (storage_object_id)
    WHERE status IN ('pending', 'copying', 'copied', 'verified');
