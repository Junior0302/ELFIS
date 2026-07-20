-- ELFIS Job Queue V1 — Postgres
-- Distinct de elfis_events (événements ≠ jobs).

CREATE TABLE IF NOT EXISTS elfis_jobs (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    job_name VARCHAR(128) NOT NULL,
    job_version INTEGER NOT NULL DEFAULT 1,
    queue_name VARCHAR(64) NOT NULL DEFAULT 'default',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    status VARCHAR(32) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    progress INTEGER NOT NULL DEFAULT 0,
    progress_message VARCHAR(255),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    available_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    scheduled_at TIMESTAMP WITHOUT TIME ZONE,
    locked_at TIMESTAMP WITHOUT TIME ZONE,
    locked_by VARCHAR(128),
    heartbeat_at TIMESTAMP WITHOUT TIME ZONE,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    cancelled_at TIMESTAMP WITHOUT TIME ZONE,
    timeout_seconds INTEGER,
    last_error TEXT,
    idempotency_key VARCHAR(255),
    correlation_id VARCHAR(36),
    causation_event_id VARCHAR(36),
    parent_job_id VARCHAR(36),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_jobs_job_id UNIQUE (job_id),
    CONSTRAINT ck_elfis_jobs_status CHECK (
        status IN (
            'pending', 'scheduled', 'processing', 'retry',
            'completed', 'failed', 'dead_letter', 'cancelled'
        )
    ),
    CONSTRAINT ck_elfis_jobs_progress CHECK (progress >= 0 AND progress <= 100)
);

CREATE INDEX IF NOT EXISTS ix_elfis_jobs_status ON elfis_jobs (status);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_queue_name ON elfis_jobs (queue_name);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_priority ON elfis_jobs (priority);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_available_at ON elfis_jobs (available_at);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_organization_id ON elfis_jobs (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_job_name ON elfis_jobs (job_name);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_created_at ON elfis_jobs (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_locked_at ON elfis_jobs (locked_at);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_idempotency_key ON elfis_jobs (idempotency_key);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_correlation_id ON elfis_jobs (correlation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_jobs_claim
    ON elfis_jobs (status, queue_name, available_at, priority, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_jobs_idempotency_key
    ON elfis_jobs (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

CREATE TABLE IF NOT EXISTS elfis_job_attempts (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES elfis_jobs (job_id),
    attempt_number INTEGER NOT NULL,
    worker_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    duration_ms INTEGER,
    error_type VARCHAR(128),
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_job_attempts_job_attempt UNIQUE (job_id, attempt_number),
    CONSTRAINT ck_elfis_job_attempts_status CHECK (
        status IN ('processing', 'completed', 'failed', 'timed_out', 'cancelled')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_job_attempts_job_id ON elfis_job_attempts (job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_job_attempts_status ON elfis_job_attempts (status);
