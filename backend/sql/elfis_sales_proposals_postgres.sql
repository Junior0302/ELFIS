-- SalesPilot Commercial Proposal Engine V1 — production DDL (PostgreSQL)

CREATE TABLE IF NOT EXISTS sales_proposal_number_sequences (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  year INTEGER NOT NULL,
  last_value INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  CONSTRAINT uq_sales_proposal_seq_org_year UNIQUE (organization_id, year)
);

CREATE TABLE IF NOT EXISTS sales_commercial_proposals (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  opportunity_id INTEGER REFERENCES sales_opportunities(id),
  sales_company_id INTEGER REFERENCES sales_companies(id),
  person_id INTEGER REFERENCES sales_people(id),
  proposal_number VARCHAR(64) NOT NULL,
  proposal_type VARCHAR(40) NOT NULL DEFAULT 'quote',
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  current_version_id INTEGER,
  owner_user_id INTEGER REFERENCES users(id),
  currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
  valid_until DATE,
  accepted_at TIMESTAMP WITHOUT TIME ZONE,
  rejected_at TIMESTAMP WITHOUT TIME ZONE,
  expired_at TIMESTAMP WITHOUT TIME ZONE,
  converted_at TIMESTAMP WITHOUT TIME ZONE,
  linked_customer_id INTEGER REFERENCES customers(id),
  linked_invoice_id INTEGER REFERENCES sales_documents(id),
  reject_reason VARCHAR(255),
  reject_comment TEXT,
  created_by INTEGER REFERENCES users(id),
  updated_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT uq_sales_proposal_org_number UNIQUE (organization_id, proposal_number)
);

CREATE INDEX IF NOT EXISTS ix_sales_proposal_org_status ON sales_commercial_proposals (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_sales_proposal_opportunity ON sales_commercial_proposals (opportunity_id);

CREATE TABLE IF NOT EXISTS sales_commercial_proposal_versions (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  proposal_id INTEGER NOT NULL REFERENCES sales_commercial_proposals(id),
  version_number INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  title VARCHAR(255) NOT NULL DEFAULT 'Proposition commerciale',
  introduction TEXT,
  scope TEXT,
  terms TEXT,
  payment_terms TEXT,
  notes TEXT,
  subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
  discount_total NUMERIC(14,2) NOT NULL DEFAULT 0,
  tax_total NUMERIC(14,2) NOT NULL DEFAULT 0,
  total NUMERIC(14,2) NOT NULL DEFAULT 0,
  currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
  valid_until DATE,
  readiness_score INTEGER NOT NULL DEFAULT 0,
  readiness_level VARCHAR(32) NOT NULL DEFAULT 'blocked',
  readiness_explanation JSONB NOT NULL DEFAULT '{}',
  pdf_vault_document_id INTEGER REFERENCES vault_documents(id),
  checksum VARCHAR(64),
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  sent_at TIMESTAMP WITHOUT TIME ZONE,
  viewed_at TIMESTAMP WITHOUT TIME ZONE,
  accepted_at TIMESTAMP WITHOUT TIME ZONE,
  rejected_at TIMESTAMP WITHOUT TIME ZONE,
  locked_at TIMESTAMP WITHOUT TIME ZONE,
  deleted_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT uq_sales_proposal_version_num UNIQUE (proposal_id, version_number)
);

CREATE TABLE IF NOT EXISTS sales_commercial_proposal_lines (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  proposal_version_id INTEGER NOT NULL REFERENCES sales_commercial_proposal_versions(id),
  catalog_item_id INTEGER REFERENCES catalog_items(id),
  source_opportunity_product_id INTEGER,
  position INTEGER NOT NULL DEFAULT 0,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  quantity NUMERIC(14,3) NOT NULL DEFAULT 1,
  unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
  discount_type VARCHAR(16) NOT NULL DEFAULT 'none',
  discount_value NUMERIC(14,2) NOT NULL DEFAULT 0,
  tax_rate NUMERIC(5,2) NOT NULL DEFAULT 20,
  subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
  discount_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  tax_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  total NUMERIC(14,2) NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_sales_proposal_line_version ON sales_commercial_proposal_lines (proposal_version_id, position);

CREATE TABLE IF NOT EXISTS sales_commercial_proposal_events (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  proposal_id INTEGER NOT NULL REFERENCES sales_commercial_proposals(id),
  version_id INTEGER,
  event_type VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  actor_user_id INTEGER REFERENCES users(id),
  occurred_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sales_proposal_event_prop ON sales_commercial_proposal_events (proposal_id, occurred_at);

-- Hybrid amount on opportunities
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS calculated_amount NUMERIC(14,2);
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS final_amount NUMERIC(14,2);
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS amount_mode VARCHAR(32) DEFAULT 'calculated';
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS amount_difference NUMERIC(14,2);
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS amount_override_reason VARCHAR(64);
ALTER TABLE sales_opportunities ADD COLUMN IF NOT EXISTS amount_override_comment TEXT;

-- Rollback sketch:
-- DROP TABLE IF EXISTS sales_commercial_proposal_events CASCADE;
-- DROP TABLE IF EXISTS sales_commercial_proposal_lines CASCADE;
-- DROP TABLE IF EXISTS sales_commercial_proposal_versions CASCADE;
-- DROP TABLE IF EXISTS sales_commercial_proposals CASCADE;
-- DROP TABLE IF EXISTS sales_proposal_number_sequences CASCADE;
