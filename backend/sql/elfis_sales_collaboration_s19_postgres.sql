-- S1.9 Sales Collaboration — PostgreSQL

CREATE TABLE IF NOT EXISTS sales_teams (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  name VARCHAR(120) NOT NULL,
  description TEXT,
  lead_user_id INTEGER REFERENCES users(id),
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_sales_team_org ON sales_teams (organization_id);

CREATE TABLE IF NOT EXISTS sales_team_members (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  team_id INTEGER NOT NULL REFERENCES sales_teams(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  role VARCHAR(40) NOT NULL DEFAULT 'member',
  permissions JSONB NOT NULL DEFAULT '{}',
  sort_order INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT uq_sales_team_member UNIQUE (team_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_sales_team_member_user ON sales_team_members (organization_id, user_id);

CREATE TABLE IF NOT EXISTS sales_comments (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  entity_type VARCHAR(40) NOT NULL,
  entity_id INTEGER NOT NULL,
  author_user_id INTEGER REFERENCES users(id),
  body TEXT NOT NULL,
  mentions JSONB NOT NULL DEFAULT '[]',
  vault_document_ids JSONB NOT NULL DEFAULT '[]',
  edited_at TIMESTAMP WITHOUT TIME ZONE,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_sales_comment_entity
  ON sales_comments (organization_id, entity_type, entity_id);

CREATE TABLE IF NOT EXISTS sales_followers (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  entity_type VARCHAR(40) NOT NULL,
  entity_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT uq_sales_follower UNIQUE (organization_id, entity_type, entity_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_sales_follower_user ON sales_followers (organization_id, user_id);

CREATE TABLE IF NOT EXISTS sales_review_requests (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  entity_type VARCHAR(40) NOT NULL,
  entity_id INTEGER NOT NULL,
  requester_user_id INTEGER REFERENCES users(id),
  reviewer_user_id INTEGER NOT NULL REFERENCES users(id),
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  message TEXT,
  decision_comment TEXT,
  decided_at TIMESTAMP WITHOUT TIME ZONE,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  deleted_at TIMESTAMP WITHOUT TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_sales_review_entity
  ON sales_review_requests (organization_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_sales_review_reviewer
  ON sales_review_requests (organization_id, reviewer_user_id, status);

CREATE TABLE IF NOT EXISTS sales_ownership_transfers (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  entity_type VARCHAR(40) NOT NULL,
  entity_id INTEGER NOT NULL,
  from_user_id INTEGER REFERENCES users(id),
  to_user_id INTEGER NOT NULL REFERENCES users(id),
  reason VARCHAR(120) NOT NULL,
  comment TEXT,
  initiated_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sales_transfer_entity
  ON sales_ownership_transfers (organization_id, entity_type, entity_id);
