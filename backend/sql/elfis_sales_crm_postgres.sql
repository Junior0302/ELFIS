-- SalesPilot CRM Foundation V1 (PostgreSQL)
-- Applied via SQLAlchemy create_all in tests; this file documents production schema.

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
