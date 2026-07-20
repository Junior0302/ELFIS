-- ELFIS Event Bus V1 — tables Postgres (prod)
-- Exécuter sur la base pointée par DATABASE_URL.
-- Ne supprime aucune table existante. Réexécutable via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS elfis_events (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL,
    event_name VARCHAR(128) NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    organization_id INTEGER NOT NULL,
    aggregate_type VARCHAR(64),
    aggregate_id VARCHAR(128),
    payload JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    available_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    locked_at TIMESTAMP WITHOUT TIME ZONE,
    locked_by VARCHAR(128),
    processed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    idempotency_key VARCHAR(255),
    correlation_id VARCHAR(36),
    causation_id VARCHAR(36),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_events_status CHECK (
        status IN (
            'pending', 'processing', 'processed', 'retry',
            'failed', 'dead_letter', 'cancelled'
        )
    ),
    CONSTRAINT uq_elfis_events_event_id UNIQUE (event_id)
);

CREATE INDEX IF NOT EXISTS ix_elfis_events_status ON elfis_events (status);
CREATE INDEX IF NOT EXISTS ix_elfis_events_available_at ON elfis_events (available_at);
CREATE INDEX IF NOT EXISTS ix_elfis_events_organization_id ON elfis_events (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_events_event_name ON elfis_events (event_name);
CREATE INDEX IF NOT EXISTS ix_elfis_events_aggregate
    ON elfis_events (aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS ix_elfis_events_created_at ON elfis_events (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_events_idempotency_key ON elfis_events (idempotency_key);
CREATE INDEX IF NOT EXISTS ix_elfis_events_claim
    ON elfis_events (status, available_at, priority, created_at);

-- Unicité d'idempotence uniquement lorsque la clé est renseignée
CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_events_idempotency_key
    ON elfis_events (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

CREATE TABLE IF NOT EXISTS elfis_event_deliveries (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES elfis_events (event_id),
    handler_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_event_deliveries_status CHECK (
        status IN (
            'pending', 'processing', 'processed', 'retry',
            'failed', 'dead_letter', 'skipped'
        )
    ),
    CONSTRAINT uq_elfis_event_deliveries_event_handler UNIQUE (event_id, handler_name)
);

CREATE INDEX IF NOT EXISTS ix_elfis_event_deliveries_event_id
    ON elfis_event_deliveries (event_id);
CREATE INDEX IF NOT EXISTS ix_elfis_event_deliveries_status
    ON elfis_event_deliveries (status);
CREATE INDEX IF NOT EXISTS ix_elfis_event_deliveries_handler_name
    ON elfis_event_deliveries (handler_name);
