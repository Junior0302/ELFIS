-- S1.8 Sales Operations — PostgreSQL

CREATE TABLE IF NOT EXISTS sales_saved_views (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  owner_user_id INTEGER REFERENCES users(id),
  resource VARCHAR(40) NOT NULL,
  name VARCHAR(120) NOT NULL,
  filters JSONB NOT NULL DEFAULT '{}',
  sort VARCHAR(64),
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  is_shared BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT uq_sales_saved_view UNIQUE (organization_id, owner_user_id, name, resource)
);

CREATE INDEX IF NOT EXISTS ix_sales_saved_view_org_resource
  ON sales_saved_views (organization_id, resource);
