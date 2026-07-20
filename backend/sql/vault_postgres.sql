-- ELFIS Vault — tables Postgres (prod)
-- Exécuter sur la base pointée par DATABASE_URL (Supabase Postgres ou autre).
-- Le bucket Storage privé `elfis-vault` doit déjà exister côté Supabase.

CREATE TABLE IF NOT EXISTS vault_documents (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_type VARCHAR(64) NOT NULL,
    document_number VARCHAR(128),
    original_filename VARCHAR(512) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(128) NOT NULL DEFAULT 'application/pdf',
    file_size INTEGER NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    invoice_date DATE,
    due_date DATE,
    amount_ht NUMERIC(14, 2),
    amount_vat NUMERIC(14, 2),
    amount_ttc NUMERIC(14, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    customer_id INTEGER,
    supplier_id INTEGER,
    archive_status VARCHAR(32) NOT NULL DEFAULT 'archived',
    accounting_status VARCHAR(32) NOT NULL DEFAULT 'not_processed',
    email_status VARCHAR(32) NOT NULL DEFAULT 'not_sent',
    version INTEGER NOT NULL DEFAULT 1,
    archived_by_user_id INTEGER REFERENCES users(id),
    archived_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vault_documents_organization_id ON vault_documents (organization_id);
CREATE INDEX IF NOT EXISTS ix_vault_documents_document_type ON vault_documents (document_type);
CREATE INDEX IF NOT EXISTS ix_vault_documents_checksum_sha256 ON vault_documents (checksum_sha256);
CREATE INDEX IF NOT EXISTS ix_vault_documents_archive_status ON vault_documents (archive_status);

-- Doublons actifs : un seul document non deleted par (org, checksum)
CREATE UNIQUE INDEX IF NOT EXISTS uq_vault_org_checksum_active
    ON vault_documents (organization_id, checksum_sha256)
    WHERE archive_status <> 'deleted';

CREATE TABLE IF NOT EXISTS vault_activity_logs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_id VARCHAR(36) NOT NULL REFERENCES vault_documents(id),
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(64) NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vault_activity_logs_organization_id ON vault_activity_logs (organization_id);
CREATE INDEX IF NOT EXISTS ix_vault_activity_logs_document_id ON vault_activity_logs (document_id);
CREATE INDEX IF NOT EXISTS ix_vault_activity_logs_action ON vault_activity_logs (action);
