-- ELFIS Search Engine V1 — Postgres Full Text Search

CREATE TABLE IF NOT EXISTS elfis_search_documents (
    id VARCHAR(36) PRIMARY KEY,
    search_document_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    resource_version INTEGER NOT NULL DEFAULT 1,
    title VARCHAR(512) NOT NULL,
    subtitle VARCHAR(512),
    content TEXT,
    search_text TEXT NOT NULL,
    status VARCHAR(64),
    category VARCHAR(64),
    document_date TIMESTAMP WITHOUT TIME ZONE,
    amount NUMERIC(18, 2),
    currency VARCHAR(8),
    action_url VARCHAR(512),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    search_vector tsvector,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    indexed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    source_event_id VARCHAR(36),
    correlation_id VARCHAR(36),
    content_hash VARCHAR(64),
    idempotency_key VARCHAR(255),
    CONSTRAINT uq_elfis_search_document_id UNIQUE (search_document_id),
    CONSTRAINT uq_elfis_search_org_res_ver
        UNIQUE (organization_id, resource_type, resource_id, resource_version)
);

CREATE INDEX IF NOT EXISTS ix_elfis_search_organization_id
    ON elfis_search_documents (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_search_resource_type
    ON elfis_search_documents (resource_type);
CREATE INDEX IF NOT EXISTS ix_elfis_search_resource_id
    ON elfis_search_documents (resource_id);
CREATE INDEX IF NOT EXISTS ix_elfis_search_status
    ON elfis_search_documents (status);
CREATE INDEX IF NOT EXISTS ix_elfis_search_category
    ON elfis_search_documents (category);
CREATE INDEX IF NOT EXISTS ix_elfis_search_document_date
    ON elfis_search_documents (document_date);
CREATE INDEX IF NOT EXISTS ix_elfis_search_amount
    ON elfis_search_documents (amount);
CREATE INDEX IF NOT EXISTS ix_elfis_search_is_active
    ON elfis_search_documents (is_active);
CREATE INDEX IF NOT EXISTS ix_elfis_search_indexed_at
    ON elfis_search_documents (indexed_at);
CREATE INDEX IF NOT EXISTS ix_elfis_search_content_hash
    ON elfis_search_documents (content_hash);
CREATE INDEX IF NOT EXISTS ix_elfis_search_idempotency_key
    ON elfis_search_documents (idempotency_key);

CREATE INDEX IF NOT EXISTS ix_elfis_search_vector_gin
    ON elfis_search_documents USING GIN (search_vector);

-- Mise à jour contrôlée du tsvector (langue french si disponible, sinon simple)
CREATE OR REPLACE FUNCTION elfis_search_documents_vector_update() RETURNS trigger AS $$
DECLARE
    cfg regconfig;
BEGIN
    BEGIN
        cfg := 'french'::regconfig;
    EXCEPTION WHEN undefined_object THEN
        cfg := 'simple'::regconfig;
    END;
    NEW.search_vector :=
        setweight(to_tsvector(cfg, coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector(cfg, coalesce(NEW.subtitle, '')), 'B') ||
        setweight(to_tsvector(cfg, coalesce(NEW.search_text, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_elfis_search_documents_vector ON elfis_search_documents;
CREATE TRIGGER trg_elfis_search_documents_vector
    BEFORE INSERT OR UPDATE OF title, subtitle, search_text
    ON elfis_search_documents
    FOR EACH ROW
    EXECUTE PROCEDURE elfis_search_documents_vector_update();
