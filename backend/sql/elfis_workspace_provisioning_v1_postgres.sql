-- ELFIS Workspace Provisioning V1 (Postgres)
-- Colonnes Organization + table d'état (idempotence 1 run / org).

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS industry_other VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS vat_status VARCHAR(32) NOT NULL DEFAULT '';
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS locale VARCHAR(16) NOT NULL DEFAULT '';
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS setup_completed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS setup_completed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS setup_version INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_organizations_setup_completed
    ON organizations (setup_completed);

CREATE TABLE IF NOT EXISTS workspace_provisioning_runs (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    current_step VARCHAR(64) NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64) NOT NULL DEFAULT '',
    error_message_safe TEXT NOT NULL DEFAULT '',
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    provisioning_version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT uq_workspace_provisioning_org UNIQUE (organization_id)
);

CREATE INDEX IF NOT EXISTS ix_workspace_provisioning_runs_organization_id
    ON workspace_provisioning_runs (organization_id);
CREATE INDEX IF NOT EXISTS ix_workspace_provisioning_runs_status
    ON workspace_provisioning_runs (status);
