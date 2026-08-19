-- RC2.5 étape 1 — Document Processing Jobs (idempotent PostgreSQL)

CREATE TABLE IF NOT EXISTS elfis_document_processing_jobs (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    product VARCHAR(64) NULL,
    pipeline_key VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 100,
    requested_by_user_id INTEGER NULL REFERENCES users(id),
    idempotency_key VARCHAR(255) NULL,
    correlation_id VARCHAR(36) NULL,
    request_id VARCHAR(64) NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    current_step_key VARCHAR(64) NULL,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    failed_at TIMESTAMPTZ NULL,
    cancelled_at TIMESTAMPTZ NULL,
    timeout_at TIMESTAMPTZ NULL,
    last_error_code VARCHAR(64) NULL,
    last_error_message_sanitized VARCHAR(255) NULL,
    result_summary_json JSONB NULL,
    metadata_json JSONB NULL,
    locked_at TIMESTAMPTZ NULL,
    locked_until TIMESTAMPTZ NULL,
    locked_by VARCHAR(128) NULL,
    heartbeat_at TIMESTAMPTZ NULL,
    cancellation_requested_at TIMESTAMPTZ NULL,
    cancellation_requested_by_user_id INTEGER NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_dp_jobs_progress CHECK (progress_percent >= 0 AND progress_percent <= 100)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_dp_jobs_org_idempotency
    ON elfis_document_processing_jobs (organization_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_status_scheduled
    ON elfis_document_processing_jobs (status, scheduled_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_org_created
    ON elfis_document_processing_jobs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_document_created
    ON elfis_document_processing_jobs (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_version
    ON elfis_document_processing_jobs (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_pipeline_status
    ON elfis_document_processing_jobs (pipeline_key, status);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_jobs_locked_until
    ON elfis_document_processing_jobs (locked_until);

CREATE TABLE IF NOT EXISTS elfis_document_processing_steps (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES elfis_document_processing_jobs(id) ON DELETE CASCADE,
    step_key VARCHAR(64) NOT NULL,
    sequence_number INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    required BOOLEAN NOT NULL DEFAULT TRUE,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    failed_at TIMESTAMPTZ NULL,
    next_retry_at TIMESTAMPTZ NULL,
    timeout_seconds INTEGER NOT NULL DEFAULT 120,
    last_error_code VARCHAR(64) NULL,
    last_error_message_sanitized VARCHAR(255) NULL,
    input_summary_json JSONB NULL,
    output_summary_json JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_dp_steps_job_key UNIQUE (job_id, step_key),
    CONSTRAINT uq_elfis_dp_steps_job_seq UNIQUE (job_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS ix_elfis_dp_steps_next_retry
    ON elfis_document_processing_steps (next_retry_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dp_steps_job_seq
    ON elfis_document_processing_steps (job_id, sequence_number);

CREATE TABLE IF NOT EXISTS elfis_document_processing_attempts (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES elfis_document_processing_jobs(id) ON DELETE CASCADE,
    step_id VARCHAR(36) NOT NULL REFERENCES elfis_document_processing_steps(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    worker_id VARCHAR(128) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ NULL,
    duration_ms INTEGER NULL,
    error_code VARCHAR(64) NULL,
    error_message_sanitized VARCHAR(255) NULL,
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json JSONB NULL,
    CONSTRAINT uq_elfis_dp_attempts_step_num UNIQUE (step_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS ix_elfis_dp_attempts_job
    ON elfis_document_processing_attempts (job_id);
