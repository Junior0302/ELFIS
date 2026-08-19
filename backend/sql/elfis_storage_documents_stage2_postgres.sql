-- RC2.4 étape 2 — index complémentaires Document Registry (idempotent)

CREATE INDEX IF NOT EXISTS ix_elfis_document_records_org_created
    ON elfis_document_records (organization_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_elfis_document_records_status_created
    ON elfis_document_records (status, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_org_checksum
    ON elfis_storage_objects (organization_id, checksum_sha256);

CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_status_created
    ON elfis_storage_objects (status, created_at DESC);
