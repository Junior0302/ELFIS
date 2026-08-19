-- ELFIS Platform Admin & Operations V1 (Postgres)
-- Nouvelles tables uniquement. Ne duplique pas orgs/users/jobs/events.

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS platform_status VARCHAR(32) NOT NULL DEFAULT 'active';
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS platform_suspended_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS platform_suspended_by INTEGER;
ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS platform_suspend_reason TEXT DEFAULT '';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_organizations_platform_status'
    ) THEN
        ALTER TABLE organizations
            ADD CONSTRAINT ck_organizations_platform_status
            CHECK (platform_status IN ('active', 'suspended', 'restricted', 'closed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_organizations_platform_status
    ON organizations (platform_status);

CREATE TABLE IF NOT EXISTS elfis_admin_audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    audit_id VARCHAR(36) NOT NULL,
    actor_user_id INTEGER NOT NULL REFERENCES users(id),
    actor_email VARCHAR(255),
    organization_id INTEGER REFERENCES organizations(id),
    action VARCHAR(128) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    target_id VARCHAR(128),
    reason TEXT,
    previous_state JSONB,
    new_state JSONB,
    request_id VARCHAR(64),
    correlation_id VARCHAR(64),
    ip_hash VARCHAR(64),
    user_agent_summary VARCHAR(255),
    status VARCHAR(32) NOT NULL,
    error_code VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_admin_audit_id UNIQUE (audit_id),
    CONSTRAINT ck_elfis_admin_audit_status CHECK (
        status IN ('succeeded', 'failed', 'denied')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_admin_audit_actor ON elfis_admin_audit_logs (actor_user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_admin_audit_org ON elfis_admin_audit_logs (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_admin_audit_action ON elfis_admin_audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_elfis_admin_audit_created ON elfis_admin_audit_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_admin_audit_target ON elfis_admin_audit_logs (target_type, target_id);

CREATE TABLE IF NOT EXISTS elfis_operational_incidents (
    id VARCHAR(36) PRIMARY KEY,
    incident_id VARCHAR(36) NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    incident_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITHOUT TIME ZONE,
    resolved_by INTEGER REFERENCES users(id),
    resolution_note TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_incident_id UNIQUE (incident_id),
    CONSTRAINT uq_elfis_incident_source UNIQUE (source_type, source_id, incident_type),
    CONSTRAINT ck_elfis_incident_severity CHECK (
        severity IN ('info', 'warning', 'error', 'critical')
    ),
    CONSTRAINT ck_elfis_incident_status CHECK (
        status IN ('open', 'acknowledged', 'resolved', 'ignored')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_incidents_organization_id
    ON elfis_operational_incidents (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_incidents_status
    ON elfis_operational_incidents (status);
CREATE INDEX IF NOT EXISTS ix_elfis_incidents_type
    ON elfis_operational_incidents (incident_type);
CREATE INDEX IF NOT EXISTS ix_elfis_incidents_severity
    ON elfis_operational_incidents (severity);
CREATE INDEX IF NOT EXISTS ix_elfis_incidents_last_seen
    ON elfis_operational_incidents (last_seen_at);
