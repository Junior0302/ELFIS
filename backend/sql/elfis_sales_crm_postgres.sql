-- SalesPilot CRM Foundation V1 (PostgreSQL)
-- Applied via SQLAlchemy create_all (app.sales_crm.models) and this file via SQL_ORDER.
-- Canonical Vault primary key is VARCHAR(36). Attachment FKs must match that type.

-- Tables created by app.sales_crm.models:
-- sales_pipelines, sales_pipeline_stages, sales_lost_reasons, sales_win_reasons,
-- sales_tags, sales_tag_links, sales_companies, sales_people, sales_leads,
-- sales_opportunities, sales_opportunity_participants, sales_opportunity_products,
-- sales_activities, sales_tasks, sales_notes, sales_attachments

-- Soft delete: deleted_at on entity tables
-- Attachments: vault_document_id FK only (no blob storage)
-- Quote bridge: sales_opportunities.quote_document_id → sales_documents.id (nullable)
-- Deal products: line_total computed server-side (no quote engine)
-- Participants: roles decision_maker|influencer|technical|buyer|primary

CREATE TABLE IF NOT EXISTS sales_attachments (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    vault_document_id VARCHAR(36) NOT NULL REFERENCES vault_documents(id),
    entity_type VARCHAR(32) NOT NULL,
    entity_id INTEGER NOT NULL,
    label VARCHAR(200),
    CONSTRAINT uq_sales_attachment_vault UNIQUE (
        organization_id,
        vault_document_id,
        entity_type,
        entity_id
    )
);

CREATE INDEX IF NOT EXISTS ix_sales_attachments_organization_id
    ON sales_attachments (organization_id);
CREATE INDEX IF NOT EXISTS ix_sales_attachments_deleted_at
    ON sales_attachments (deleted_at);
CREATE INDEX IF NOT EXISTS ix_sales_attachments_vault_document_id
    ON sales_attachments (vault_document_id);
