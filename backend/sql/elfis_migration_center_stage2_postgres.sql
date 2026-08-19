-- ELFIS Migration Center — architecture stage 2 (additif, idempotent)
-- Token, profils techniques, timeline, activity feed, memory

-- Colonnes session
ALTER TABLE elfis_migration_sessions
    ADD COLUMN IF NOT EXISTS migration_session_token VARCHAR(64);

ALTER TABLE elfis_migration_sessions
    ADD COLUMN IF NOT EXISTS migration_profile JSONB NOT NULL DEFAULT jsonb_build_object('schema_version', 1, 'data', jsonb_build_object());

ALTER TABLE elfis_migration_sessions
    ADD COLUMN IF NOT EXISTS ai_profile JSONB NOT NULL DEFAULT jsonb_build_object('schema_version', 1, 'data', jsonb_build_object());

-- Backfill tokens manquants (sessions Sprint 1)
UPDATE elfis_migration_sessions
SET migration_session_token = 'mig_' || replace(gen_random_uuid()::text, '-', '')
WHERE migration_session_token IS NULL;

ALTER TABLE elfis_migration_sessions
    ALTER COLUMN migration_session_token SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_elfis_mig_session_token'
    ) THEN
        ALTER TABLE elfis_migration_sessions
            ADD CONSTRAINT uq_elfis_mig_session_token UNIQUE (migration_session_token);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_mig_session_token_idx
    ON elfis_migration_sessions (migration_session_token);

CREATE INDEX IF NOT EXISTS ix_elfis_mig_org_token
    ON elfis_migration_sessions (organization_id, migration_session_token);

-- Timeline
CREATE TABLE IF NOT EXISTS elfis_migration_timeline_entries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) NOT NULL REFERENCES elfis_migration_sessions(id),
    step_key VARCHAR(64) NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_mig_tl_status CHECK (
        status IN ('pending', 'started', 'completed', 'failed', 'skipped', 'cancelled')
    ),
    CONSTRAINT uq_elfis_mig_tl_session_step UNIQUE (migration_session_id, step_key)
);

CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_org
    ON elfis_migration_timeline_entries (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_session
    ON elfis_migration_timeline_entries (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_step
    ON elfis_migration_timeline_entries (step_key);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_status
    ON elfis_migration_timeline_entries (status);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_created
    ON elfis_migration_timeline_entries (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_tl_org_session
    ON elfis_migration_timeline_entries (organization_id, migration_session_id);

-- Activity feed
CREATE TABLE IF NOT EXISTS elfis_migration_activities (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) NOT NULL REFERENCES elfis_migration_sessions(id),
    activity_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(16) NOT NULL DEFAULT 'info',
    actor_type VARCHAR(16) NOT NULL DEFAULT 'system',
    actor_user_id INTEGER REFERENCES users(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_mig_act_severity CHECK (
        severity IN ('info', 'success', 'warning', 'error')
    ),
    CONSTRAINT ck_elfis_mig_act_actor CHECK (
        actor_type IN ('user', 'system', 'ai', 'worker', 'admin')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_mig_act_org
    ON elfis_migration_activities (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_act_session
    ON elfis_migration_activities (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_act_type
    ON elfis_migration_activities (activity_type);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_act_occurred
    ON elfis_migration_activities (occurred_at);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_act_org_session
    ON elfis_migration_activities (organization_id, migration_session_id, occurred_at DESC);

-- Migration Memory (session scope only for writes)
CREATE TABLE IF NOT EXISTS elfis_migration_memory_entries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    migration_session_id VARCHAR(36) NOT NULL REFERENCES elfis_migration_sessions(id),
    scope VARCHAR(32) NOT NULL DEFAULT 'session',
    memory_type VARCHAR(64) NOT NULL,
    key_hash VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION,
    source VARCHAR(32) NOT NULL DEFAULT 'system',
    status VARCHAR(32) NOT NULL DEFAULT 'proposed',
    created_by_user_id INTEGER REFERENCES users(id),
    validated_by_user_id INTEGER REFERENCES users(id),
    validated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_mig_mem_scope CHECK (
        scope IN ('session', 'organization', 'product')
    ),
    CONSTRAINT ck_elfis_mig_mem_status CHECK (
        status IN ('proposed', 'validated', 'rejected', 'expired')
    ),
    CONSTRAINT ck_elfis_mig_mem_source CHECK (
        source IN ('user', 'system', 'ai', 'import_rule')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_org
    ON elfis_migration_memory_entries (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_session
    ON elfis_migration_memory_entries (migration_session_id);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_scope
    ON elfis_migration_memory_entries (scope);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_type
    ON elfis_migration_memory_entries (memory_type);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_key
    ON elfis_migration_memory_entries (key_hash);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_status
    ON elfis_migration_memory_entries (status);
CREATE INDEX IF NOT EXISTS ix_elfis_mig_mem_org_session
    ON elfis_migration_memory_entries (organization_id, migration_session_id, scope, memory_type);
