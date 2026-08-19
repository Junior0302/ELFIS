-- ELFIS Smart Migration Engine (Sprint 7) — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_smart_migration_runs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    batch_size INTEGER NOT NULL DEFAULT 25,
    max_workers INTEGER NOT NULL DEFAULT 4,
    parallel BOOLEAN NOT NULL DEFAULT FALSE,
    progress_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
    documents_total INTEGER NOT NULL DEFAULT 0,
    documents_completed INTEGER NOT NULL DEFAULT 0,
    documents_pending INTEGER NOT NULL DEFAULT 0,
    documents_failed INTEGER NOT NULL DEFAULT 0,
    documents_imported INTEGER NOT NULL DEFAULT 0,
    active_batches INTEGER NOT NULL DEFAULT 0,
    active_workers INTEGER NOT NULL DEFAULT 0,
    eta_seconds DOUBLE PRECISION,
    throughput_per_min DOUBLE PRECISION NOT NULL DEFAULT 0,
    estimated_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    correlation_id VARCHAR(64),
    actor_user_id INTEGER REFERENCES users(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_heartbeat_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_sm_run_status CHECK (
        status IN (
            'pending', 'running', 'paused', 'completed',
            'failed', 'cancelled', 'resuming'
        )
    ),
    CONSTRAINT ck_elfis_sm_run_progress CHECK (
        progress_percent >= 0 AND progress_percent <= 100 AND version >= 1
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_sm_run_org
    ON elfis_smart_migration_runs (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_sm_run_mig
    ON elfis_smart_migration_runs (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_sm_run_status
    ON elfis_smart_migration_runs (organization_id, status);

CREATE TABLE IF NOT EXISTS elfis_smart_migration_batches (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    smart_run_id VARCHAR(36) NOT NULL REFERENCES elfis_smart_migration_runs(id),
    migration_session_id VARCHAR(36) NOT NULL,
    batch_index INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    documents_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    progress_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_sm_batch_idx UNIQUE (smart_run_id, batch_index),
    CONSTRAINT ck_elfis_sm_batch_status CHECK (
        status IN (
            'pending', 'running', 'completed', 'failed', 'cancelled', 'partial'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_sm_batch_run
    ON elfis_smart_migration_batches (smart_run_id);
CREATE INDEX IF NOT EXISTS ix_elfis_sm_batch_mig
    ON elfis_smart_migration_batches (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_sm_batch_status
    ON elfis_smart_migration_batches (organization_id, status);

CREATE TABLE IF NOT EXISTS elfis_smart_migration_batch_items (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    smart_run_id VARCHAR(36) NOT NULL,
    batch_id VARCHAR(36) NOT NULL REFERENCES elfis_smart_migration_batches(id),
    document_intake_item_id VARCHAR(36) NOT NULL,
    universal_document_id VARCHAR(32),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    stage VARCHAR(64),
    attempts INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_code VARCHAR(64),
    error_message TEXT,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_sm_item_doc UNIQUE (batch_id, document_intake_item_id),
    CONSTRAINT ck_elfis_sm_item_status CHECK (
        status IN (
            'pending', 'running', 'completed', 'failed', 'skipped', 'cancelled'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_sm_item_batch
    ON elfis_smart_migration_batch_items (batch_id);
CREATE INDEX IF NOT EXISTS ix_elfis_sm_item_doc
    ON elfis_smart_migration_batch_items (document_intake_item_id);

CREATE TABLE IF NOT EXISTS elfis_smart_migration_reports (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    smart_run_id VARCHAR(36) NOT NULL,
    migration_session_id VARCHAR(36) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    format VARCHAR(16) NOT NULL DEFAULT 'json',
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    linked_objects JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    duration_ms INTEGER,
    estimated_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    body JSONB NOT NULL DEFAULT '{}'::jsonb,
    body_csv TEXT,
    body_pdf TEXT,
    actor_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_sm_rep_ver UNIQUE (smart_run_id, version)
);

CREATE INDEX IF NOT EXISTS ix_elfis_sm_rep_run
    ON elfis_smart_migration_reports (smart_run_id);

CREATE TABLE IF NOT EXISTS elfis_smart_migration_cleanup_log (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
    affected_count INTEGER NOT NULL DEFAULT 0,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_sm_cleanup_org
    ON elfis_smart_migration_cleanup_log (organization_id, created_at);
