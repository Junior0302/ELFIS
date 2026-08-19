-- Index PostgreSQL complémentaires Phase F / RC1 (idempotent).

CREATE UNIQUE INDEX IF NOT EXISTS uq_document_email_org_idempotency
ON document_email_logs (organization_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

-- Search GIN sur tsvector (table elfis_search_documents.search_vector).
-- Si create_all ORM a créé la colonne en TEXT, la convertir avant l'index GIN.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'elfis_search_documents'
          AND column_name = 'search_vector'
          AND udt_name IS DISTINCT FROM 'tsvector'
    ) THEN
        ALTER TABLE elfis_search_documents
            ALTER COLUMN search_vector TYPE tsvector USING NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_elfis_search_vector_gin
    ON elfis_search_documents USING GIN (search_vector);
