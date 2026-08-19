-- ELFIS Security / Observability / Reliability V1 (Postgres)
-- Table audit sécurité uniquement — métriques en mémoire V1.
-- Ne duplique pas admin_audit ni operational_incidents.

CREATE TABLE IF NOT EXISTS elfis_security_events (
    id VARCHAR(36) PRIMARY KEY,
    security_event_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'warning',
    organization_id INTEGER REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    ip_hash VARCHAR(64),
    route VARCHAR(255),
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    details JSONB,
    request_id VARCHAR(64),
    correlation_id VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_security_event_id UNIQUE (security_event_id),
    CONSTRAINT ck_elfis_security_event_severity CHECK (
        severity IN ('info', 'warning', 'error', 'critical')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_security_events_type
    ON elfis_security_events (event_type);
CREATE INDEX IF NOT EXISTS ix_elfis_security_events_created
    ON elfis_security_events (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_security_events_org
    ON elfis_security_events (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_security_events_user
    ON elfis_security_events (user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_security_events_request
    ON elfis_security_events (request_id);
