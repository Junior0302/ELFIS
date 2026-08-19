-- S1.6.1 Proposal-to-Invoice Bridge — PostgreSQL migration

-- CommercialProposal conversion tracking
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS conversion_status VARCHAR(32) NOT NULL DEFAULT 'not_ready';
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS conversion_started_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS conversion_completed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS conversion_error_code VARCHAR(64);
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS conversion_idempotency_key VARCHAR(128);

CREATE INDEX IF NOT EXISTS ix_sales_proposal_conversion_idem
  ON sales_commercial_proposals (conversion_idempotency_key);

-- Ensure linked columns exist (idempotent with S1.6)
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS linked_customer_id INTEGER REFERENCES customers(id);
ALTER TABLE sales_commercial_proposals
  ADD COLUMN IF NOT EXISTS linked_invoice_id INTEGER REFERENCES sales_documents(id);

-- SalesCompany → Customer link
ALTER TABLE sales_companies
  ADD COLUMN IF NOT EXISTS linked_customer_id INTEGER REFERENCES customers(id);
CREATE INDEX IF NOT EXISTS ix_sales_companies_linked_customer
  ON sales_companies (linked_customer_id);

-- SalesDocument provenance
ALTER TABLE sales_documents
  ADD COLUMN IF NOT EXISTS source_type VARCHAR(64);
ALTER TABLE sales_documents
  ADD COLUMN IF NOT EXISTS source_id VARCHAR(64);
ALTER TABLE sales_documents
  ADD COLUMN IF NOT EXISTS source_version_id VARCHAR(64);
ALTER TABLE sales_documents
  ADD COLUMN IF NOT EXISTS source_number VARCHAR(64);

CREATE INDEX IF NOT EXISTS ix_sales_documents_source_type
  ON sales_documents (source_type);
CREATE INDEX IF NOT EXISTS ix_sales_documents_source_id
  ON sales_documents (source_id);

-- One primary invoice per proposal (partial unique — PostgreSQL)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_documents_proposal_source
  ON sales_documents (organization_id, source_type, source_id)
  WHERE source_type = 'sales_proposal' AND source_id IS NOT NULL;
