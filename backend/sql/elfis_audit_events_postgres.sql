-- ELFIS Audit & Activity Engine V1 (+ RC2.3 étape 3)
-- Tables nouvelles uniquement. Ne touche pas aux tables métier ni JWT.

CREATE TABLE IF NOT EXISTS elfis_audit_events (
    id VARCHAR(36) PRIMARY KEY,
    occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    severity VARCHAR(16) NOT NULL DEFAULT 'INFO',
    category VARCHAR(32) NOT NULL DEFAULT 'OTHER',
    action VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    actor_user_id INTEGER REFERENCES users(id),
    actor_email VARCHAR(255),
    organization_id INTEGER REFERENCES organizations(id),
    product VARCHAR(64),
    service VARCHAR(64),
    target_type VARCHAR(64),
    target_id VARCHAR(128),
    target_display VARCHAR(255),
    request_id VARCHAR(64),
    correlation_id VARCHAR(64),
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    metadata_json JSONB,
    message TEXT,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_occurred_at
    ON elfis_audit_events (occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_action
    ON elfis_audit_events (action);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_actor_user_id
    ON elfis_audit_events (actor_user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_organization_id
    ON elfis_audit_events (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_product
    ON elfis_audit_events (product);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_service
    ON elfis_audit_events (service);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_severity
    ON elfis_audit_events (severity);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_correlation_id
    ON elfis_audit_events (correlation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_request_id
    ON elfis_audit_events (request_id);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_category
    ON elfis_audit_events (category);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_events_status
    ON elfis_audit_events (status);

-- Composites RC2.3 étape 3
CREATE INDEX IF NOT EXISTS ix_elfis_audit_cat_occurred
    ON elfis_audit_events (category, occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_sev_occurred
    ON elfis_audit_events (severity, occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_actor_occurred
    ON elfis_audit_events (actor_user_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_org_occurred
    ON elfis_audit_events (organization_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_action_occurred
    ON elfis_audit_events (action, occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_success_occurred
    ON elfis_audit_events (success, occurred_at);

CREATE TABLE IF NOT EXISTS elfis_audit_events_archive (
    id VARCHAR(36) PRIMARY KEY,
    occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'INFO',
    category VARCHAR(32) NOT NULL DEFAULT 'OTHER',
    action VARCHAR(128) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    actor_user_id INTEGER,
    actor_email VARCHAR(255),
    organization_id INTEGER,
    product VARCHAR(64),
    service VARCHAR(64),
    target_type VARCHAR(64),
    target_id VARCHAR(128),
    target_display VARCHAR(255),
    request_id VARCHAR(64),
    correlation_id VARCHAR(64),
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    metadata_json JSONB,
    message TEXT,
    duration_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    archived_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    archive_batch_id VARCHAR(36) NOT NULL,
    archive_reason VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS ix_elfis_audit_arch_occurred_at
    ON elfis_audit_events_archive (occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_arch_archived_at
    ON elfis_audit_events_archive (archived_at);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_arch_batch
    ON elfis_audit_events_archive (archive_batch_id);
CREATE INDEX IF NOT EXISTS ix_elfis_audit_arch_category
    ON elfis_audit_events_archive (category);
