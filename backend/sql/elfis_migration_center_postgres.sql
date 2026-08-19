-- ELFIS Migration Center Sprint 1 — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_migration_sessions (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    created_by_user_id INTEGER REFERENCES users(id),
    mode VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    current_step INTEGER NOT NULL DEFAULT 1,
    company_profile JSONB,
    selected_sources JSONB,
    configuration JSONB,
    progress JSONB,
    answers_metadata JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    started_at TIMESTAMP,
    last_activity_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancel_reason VARCHAR(255),
    last_error_code VARCHAR(64),
    last_error_message_sanitized VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_mig_mode CHECK (
        mode IN ('initial_migration', 'one_time_import')
    ),
    CONSTRAINT ck_elfis_mig_status CHECK (
        status IN (
            'draft',
            'profile_completed',
            'sources_selected',
            'awaiting_upload',
            'analyzing',
            'analysis_completed',
            'awaiting_validation',
            'ready_to_import',
            'importing',
            'completed',
            'failed',
            'cancelled'
        )
    ),
    CONSTRAINT ck_elfis_mig_step CHECK (current_step >= 1 AND current_step <= 20),
    CONSTRAINT ck_elfis_mig_version CHECK (version >= 1)
);

CREATE INDEX IF NOT EXISTS ix_elfis_mig_org_created
    ON elfis_migration_sessions (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_org_status
    ON elfis_migration_sessions (organization_id, status);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_created_by
    ON elfis_migration_sessions (created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_last_activity
    ON elfis_migration_sessions (last_activity_at);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mode_status
    ON elfis_migration_sessions (organization_id, mode, status);
