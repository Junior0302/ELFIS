-- Accounting Intelligence V2 — migration additive PostgreSQL
-- Idempotent (IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS elfis_ai_context_profiles (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    frequent_accounts JSONB NOT NULL DEFAULT '[]'::jsonb,
    favorite_journals JSONB NOT NULL DEFAULT '[]'::jsonb,
    habitual_vat_rates JSONB NOT NULL DEFAULT '[]'::jsonb,
    exceptions JSONB NOT NULL DEFAULT '[]'::jsonb,
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    rebuilt_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_ai_ctx_org UNIQUE (organization_id)
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_ctx_org ON elfis_ai_context_profiles (organization_id);

CREATE TABLE IF NOT EXISTS elfis_ai_learning_memory (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    memory_key VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    direction VARCHAR(32) NULL,
    document_type VARCHAR(64) NULL,
    party_name VARCHAR(255) NULL,
    preferred_accounts JSONB NOT NULL DEFAULT '{}'::jsonb,
    preferred_journal VARCHAR(16) NULL,
    vat_rate DOUBLE PRECISION NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'user_validation',
    feedback_id VARCHAR(36) NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_user_id INTEGER NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_ai_lm_org_key_ver UNIQUE (organization_id, memory_key, version)
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_lm_org_key ON elfis_ai_learning_memory (organization_id, memory_key);

CREATE TABLE IF NOT EXISTS elfis_ai_recommendation_history (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    proposal_id VARCHAR(36) NULL,
    direction VARCHAR(32) NULL,
    document_type VARCHAR(64) NULL,
    party_name VARCHAR(255) NULL,
    account_code VARCHAR(16) NULL,
    journal_code VARCHAR(16) NULL,
    vat_rate DOUBLE PRECISION NULL,
    score DOUBLE PRECISION NULL,
    primary_source VARCHAR(32) NULL,
    reason TEXT NULL,
    recommendation JSONB NOT NULL DEFAULT '{}'::jsonb,
    explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence_detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_user_id INTEGER NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_rec_org ON elfis_ai_recommendation_history (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_rec_proposal ON elfis_ai_recommendation_history (proposal_id);

CREATE TABLE IF NOT EXISTS elfis_ai_feedback (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    recommendation_id VARCHAR(36) NULL,
    proposal_id VARCHAR(36) NULL,
    action VARCHAR(32) NOT NULL,
    validation_seconds DOUBLE PRECISION NULL,
    comment TEXT NULL,
    modifications JSONB NOT NULL DEFAULT '{}'::jsonb,
    learned BOOLEAN NOT NULL DEFAULT FALSE,
    learn_gate VARCHAR(32) NULL,
    actor_user_id INTEGER NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_fb_org ON elfis_ai_feedback (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_fb_rec ON elfis_ai_feedback (recommendation_id);

CREATE TABLE IF NOT EXISTS elfis_ai_similarity_cache (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    query_key VARCHAR(255) NOT NULL,
    candidate_key VARCHAR(255) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NULL,
    CONSTRAINT uq_elfis_ai_sim_keys UNIQUE (organization_id, query_key, candidate_key)
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_sim_org ON elfis_ai_similarity_cache (organization_id, query_key);

CREATE TABLE IF NOT EXISTS elfis_ai_audit (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NULL,
    entity_id VARCHAR(36) NULL,
    actor_user_id INTEGER NULL REFERENCES users(id),
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_elfis_ai_audit_org ON elfis_ai_audit (organization_id, created_at);
