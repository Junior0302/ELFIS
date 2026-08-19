-- S1.6.1 Proposal-to-Invoice Bridge — SQLite-compatible migration notes
-- SQLite does not support ADD COLUMN IF NOT EXISTS on all versions;
-- application create_all + Alembic-style checks are preferred for tests.
-- Production uses the PostgreSQL script.

-- Columns expected on sales_commercial_proposals:
--   conversion_status TEXT DEFAULT 'not_ready'
--   conversion_started_at DATETIME
--   conversion_completed_at DATETIME
--   conversion_error_code TEXT
--   conversion_idempotency_key TEXT
--   linked_customer_id INTEGER
--   linked_invoice_id INTEGER

-- Columns expected on sales_companies:
--   linked_customer_id INTEGER

-- Columns expected on sales_documents:
--   source_type TEXT
--   source_id TEXT
--   source_version_id TEXT
--   source_number TEXT

-- Unique source guard enforced in application layer for SQLite;
-- PostgreSQL uses partial unique index uq_sales_documents_proposal_source.
