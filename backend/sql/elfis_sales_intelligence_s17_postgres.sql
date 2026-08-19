-- S1.7 Sales Intelligence — PostgreSQL

CREATE TABLE IF NOT EXISTS sales_insight_items (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  insight_type VARCHAR(64) NOT NULL,
  category VARCHAR(32) NOT NULL,
  source_type VARCHAR(64) NOT NULL,
  source_id VARCHAR(64),
  source_label VARCHAR(255),
  deduplication_key VARCHAR(191) NOT NULL,
  severity VARCHAR(16) NOT NULL DEFAULT 'medium',
  priority_score INTEGER NOT NULL DEFAULT 0,
  title VARCHAR(255) NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  explanation JSONB NOT NULL DEFAULT '{}',
  evidence JSONB NOT NULL DEFAULT '[]',
  recommended_action JSONB NOT NULL DEFAULT '{}',
  available_actions JSONB NOT NULL DEFAULT '[]',
  route VARCHAR(255),
  resolution_condition TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  linked_decision_id VARCHAR(36),
  observed_value VARCHAR(128),
  expected_value VARCHAR(128),
  score INTEGER,
  dismiss_reason VARCHAR(255),
  first_detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  last_detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  resolved_at TIMESTAMP WITHOUT TIME ZONE,
  dismissed_at TIMESTAMP WITHOUT TIME ZONE,
  acknowledged_at TIMESTAMP WITHOUT TIME ZONE,
  acknowledged_by INTEGER REFERENCES users(id),
  dismissed_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  CONSTRAINT uq_sales_insight_org_dedupe UNIQUE (organization_id, deduplication_key)
);

CREATE INDEX IF NOT EXISTS ix_sales_insight_org_status ON sales_insight_items (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_sales_insight_org_category ON sales_insight_items (organization_id, category);
CREATE INDEX IF NOT EXISTS ix_sales_insight_org_severity ON sales_insight_items (organization_id, severity);
CREATE INDEX IF NOT EXISTS ix_sales_insight_org_source ON sales_insight_items (organization_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS ix_sales_insight_org_priority ON sales_insight_items (organization_id, priority_score);
CREATE INDEX IF NOT EXISTS ix_sales_insight_linked_decision ON sales_insight_items (linked_decision_id);
CREATE INDEX IF NOT EXISTS ix_sales_insight_type ON sales_insight_items (insight_type);
