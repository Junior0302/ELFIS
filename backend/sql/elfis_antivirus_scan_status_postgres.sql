-- AV-01 — Métadonnées scan antivirus (idempotent PostgreSQL, additive)
--
-- Lignes existantes :
--   scan_status = unknown
--   vault_documents.content_origin = unknown
-- Jamais clean par défaut. Migration additive uniquement, aucun backfill.
-- Nouveaux writes (code applicatif) :
--   upload utilisateur → user_upload
--   PDF ELFIS généré → generated_by_elfis

ALTER TABLE elfis_storage_objects
    ADD COLUMN IF NOT EXISTS scan_status VARCHAR(32) NOT NULL DEFAULT 'unknown';
ALTER TABLE elfis_storage_objects
    ADD COLUMN IF NOT EXISTS scan_engine VARCHAR(64);
ALTER TABLE elfis_storage_objects
    ADD COLUMN IF NOT EXISTS scan_signature VARCHAR(128);
ALTER TABLE elfis_storage_objects
    ADD COLUMN IF NOT EXISTS scan_at TIMESTAMP WITHOUT TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_elfis_storage_objects_scan_status
    ON elfis_storage_objects (scan_status);

ALTER TABLE vault_documents
    ADD COLUMN IF NOT EXISTS scan_status VARCHAR(32) NOT NULL DEFAULT 'unknown';
ALTER TABLE vault_documents
    ADD COLUMN IF NOT EXISTS scan_engine VARCHAR(64);
ALTER TABLE vault_documents
    ADD COLUMN IF NOT EXISTS scan_signature VARCHAR(128);
ALTER TABLE vault_documents
    ADD COLUMN IF NOT EXISTS scan_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE vault_documents
    ADD COLUMN IF NOT EXISTS content_origin VARCHAR(32) NOT NULL DEFAULT 'unknown';

CREATE INDEX IF NOT EXISTS ix_vault_documents_scan_status
    ON vault_documents (scan_status);
CREATE INDEX IF NOT EXISTS ix_vault_documents_content_origin
    ON vault_documents (content_origin);

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS scan_status VARCHAR(32) NOT NULL DEFAULT 'unknown';
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS scan_engine VARCHAR(64);
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS scan_signature VARCHAR(128);
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS scan_at TIMESTAMP WITHOUT TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_invoices_scan_status
    ON invoices (scan_status);

ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS scan_engine VARCHAR(64);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS scan_signature VARCHAR(128);
ALTER TABLE elfis_document_intake_items
    ADD COLUMN IF NOT EXISTS scan_at TIMESTAMP WITHOUT TIME ZONE;
