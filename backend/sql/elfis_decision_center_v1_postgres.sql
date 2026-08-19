-- ELFIS Decision Center V1 + Execution Layer V1 (Postgres)

CREATE TABLE IF NOT EXISTS elfis_decision_items (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    decision_type VARCHAR(64) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    source_event_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    severity VARCHAR(16) NOT NULL DEFAULT 'medium',
    confidence NUMERIC(5, 4),
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    explanation TEXT NOT NULL DEFAULT '',
    recommended_action_type VARCHAR(64) NOT NULL DEFAULT 'open_resource',
    recommended_action_path VARCHAR(512),
    required_permission VARCHAR(64),
    metadata JSONB,
    deduplication_key VARCHAR(255) NOT NULL,
    created_by_rule VARCHAR(128) NOT NULL,
    rule_version VARCHAR(32) NOT NULL DEFAULT '1',
    execution_status VARCHAR(32) NOT NULL DEFAULT 'idle',
    execution_started_at TIMESTAMP WITHOUT TIME ZONE,
    execution_completed_at TIMESTAMP WITHOUT TIME ZONE,
    execution_failed_at TIMESTAMP WITHOUT TIME ZONE,
    last_execution_error_code VARCHAR(64),
    last_execution_error_message VARCHAR(512),
    last_action_type VARCHAR(64),
    last_action_by_user_id INTEGER REFERENCES users(id),
    execution_attempts INTEGER NOT NULL DEFAULT 0,
    last_source_refresh_at TIMESTAMP WITHOUT TIME ZONE,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    started_by_user_id INTEGER REFERENCES users(id),
    last_activity_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITHOUT TIME ZONE,
    dismissed_at TIMESTAMP WITHOUT TIME ZONE,
    expires_at TIMESTAMP WITHOUT TIME ZONE,
    CONSTRAINT uq_elfis_decision_org_dedupe UNIQUE (organization_id, deduplication_key),
    CONSTRAINT ck_elfis_decision_status CHECK (
        status IN ('open','in_progress','resolved','dismissed','expired')
    ),
    CONSTRAINT ck_elfis_decision_severity CHECK (
        severity IN ('info','low','medium','high','critical')
    ),
    CONSTRAINT ck_elfis_decision_execution_status CHECK (
        execution_status IN ('idle','pending','running','succeeded','failed','cancelled')
    )
);

-- Colonnes C1.16 si table V1 déjà présente
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS execution_status VARCHAR(32) NOT NULL DEFAULT 'idle';
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS execution_started_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS execution_completed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS execution_failed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_execution_error_code VARCHAR(64);
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_execution_error_message VARCHAR(512);
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_action_type VARCHAR(64);
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_action_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS execution_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_source_refresh_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS started_by_user_id INTEGER REFERENCES users(id);
ALTER TABLE elfis_decision_items ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITHOUT TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_status
    ON elfis_decision_items (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_severity
    ON elfis_decision_items (organization_id, severity);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_source
    ON elfis_decision_items (organization_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_created
    ON elfis_decision_items (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_updated
    ON elfis_decision_items (organization_id, updated_at);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_exec
    ON elfis_decision_items (organization_id, execution_status);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_org_type
    ON elfis_decision_items (organization_id, decision_type);

CREATE TABLE IF NOT EXISTS elfis_decision_execution_attempts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    decision_id VARCHAR(36) NOT NULL REFERENCES elfis_decision_items(id),
    user_id INTEGER REFERENCES users(id),
    action_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    request_id VARCHAR(64),
    idempotency_key VARCHAR(128),
    error_code VARCHAR(64),
    error_message VARCHAR(512),
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    metadata JSONB,
    CONSTRAINT uq_elfis_decision_exec_idem UNIQUE (
        organization_id, decision_id, action_type, idempotency_key
    ),
    CONSTRAINT ck_elfis_decision_exec_status CHECK (
        status IN ('running','succeeded','failed','cancelled')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_decision_exec_decision
    ON elfis_decision_execution_attempts (decision_id, started_at);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_exec_org_status
    ON elfis_decision_execution_attempts (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_decision_exec_action
    ON elfis_decision_execution_attempts (organization_id, action_type);
