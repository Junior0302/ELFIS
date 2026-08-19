-- ELFIS Billing — Subscriptions, Entitlements & Quotas V1 (Postgres)
-- Compatible avec la table legacy "subscriptions" (Stripe sync inchangé).

CREATE TABLE IF NOT EXISTS elfis_billing_plans (
    id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL,
    plan_code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    currency VARCHAR(8) NOT NULL DEFAULT 'EUR',
    price_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    billing_interval VARCHAR(16),
    trial_days INTEGER NOT NULL DEFAULT 0,
    stripe_product_id VARCHAR(128),
    stripe_price_id VARCHAR(128),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    quotas JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_billing_plan_id UNIQUE (plan_id),
    CONSTRAINT uq_elfis_billing_plan_code UNIQUE (plan_code),
    CONSTRAINT ck_elfis_billing_interval CHECK (
        billing_interval IS NULL OR billing_interval IN ('month', 'year', 'one_time', 'none')
    )
);

CREATE TABLE IF NOT EXISTS elfis_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    subscription_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    plan_id VARCHAR(36) NOT NULL,
    status VARCHAR(32) NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'stripe',
    legacy_subscription_id INTEGER,
    stripe_customer_id VARCHAR(128),
    stripe_subscription_id VARCHAR(128),
    stripe_price_id VARCHAR(128),
    trial_started_at TIMESTAMP WITHOUT TIME ZONE,
    trial_ends_at TIMESTAMP WITHOUT TIME ZONE,
    current_period_started_at TIMESTAMP WITHOUT TIME ZONE,
    current_period_ends_at TIMESTAMP WITHOUT TIME ZONE,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at TIMESTAMP WITHOUT TIME ZONE,
    ended_at TIMESTAMP WITHOUT TIME ZONE,
    payment_failed_at TIMESTAMP WITHOUT TIME ZONE,
    grace_period_ends_at TIMESTAMP WITHOUT TIME ZONE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id INTEGER REFERENCES users(id),
    updated_by_user_id INTEGER REFERENCES users(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_subscription_id UNIQUE (subscription_id),
    CONSTRAINT ck_elfis_subscription_status CHECK (
        status IN (
            'incomplete','trialing','active','past_due','unpaid',
            'paused','cancelled','expired','suspended'
        )
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_subscriptions_org_current
    ON elfis_subscriptions (organization_id)
    WHERE is_current = TRUE;

CREATE INDEX IF NOT EXISTS ix_elfis_subscriptions_organization_id
    ON elfis_subscriptions (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_subscriptions_status
    ON elfis_subscriptions (status);
CREATE INDEX IF NOT EXISTS ix_elfis_subscriptions_stripe_sub
    ON elfis_subscriptions (stripe_subscription_id);

CREATE TABLE IF NOT EXISTS elfis_entitlements (
    id VARCHAR(36) PRIMARY KEY,
    entitlement_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    subscription_id VARCHAR(36),
    feature_code VARCHAR(64) NOT NULL,
    is_enabled BOOLEAN NOT NULL,
    source VARCHAR(32) NOT NULL,
    value JSONB,
    starts_at TIMESTAMP WITHOUT TIME ZONE,
    ends_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_entitlement_id UNIQUE (entitlement_id),
    CONSTRAINT uq_elfis_entitlement_org_feature_source
        UNIQUE (organization_id, feature_code, source),
    CONSTRAINT ck_elfis_entitlement_source CHECK (
        source IN ('plan', 'override', 'trial', 'promotion', 'platform_admin')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_entitlements_organization_id
    ON elfis_entitlements (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_entitlements_feature_code
    ON elfis_entitlements (feature_code);

CREATE TABLE IF NOT EXISTS elfis_quotas (
    id VARCHAR(36) PRIMARY KEY,
    quota_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    subscription_id VARCHAR(36),
    quota_code VARCHAR(64) NOT NULL,
    limit_value BIGINT,
    period VARCHAR(32) NOT NULL,
    hard_limit BOOLEAN NOT NULL DEFAULT TRUE,
    current_period_started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    current_period_ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_quota_id UNIQUE (quota_id),
    CONSTRAINT uq_elfis_quota_org_code_period
        UNIQUE (organization_id, quota_code, current_period_started_at),
    CONSTRAINT ck_elfis_quota_period CHECK (
        period IN ('day', 'month', 'billing_period', 'lifetime')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_quotas_organization_id ON elfis_quotas (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_quotas_quota_code ON elfis_quotas (quota_code);

CREATE TABLE IF NOT EXISTS elfis_usage_counters (
    id VARCHAR(36) PRIMARY KEY,
    usage_counter_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    subscription_id VARCHAR(36),
    usage_code VARCHAR(64) NOT NULL,
    period_started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    period_ends_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    used_value BIGINT NOT NULL DEFAULT 0,
    reserved_value BIGINT NOT NULL DEFAULT 0,
    last_consumed_at TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_usage_counter_id UNIQUE (usage_counter_id),
    CONSTRAINT uq_elfis_usage_org_code_period
        UNIQUE (organization_id, usage_code, period_started_at)
);

CREATE INDEX IF NOT EXISTS ix_elfis_usage_organization_id ON elfis_usage_counters (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_usage_usage_code ON elfis_usage_counters (usage_code);

CREATE TABLE IF NOT EXISTS elfis_billing_events (
    id VARCHAR(36) PRIMARY KEY,
    billing_event_id VARCHAR(36) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    provider_event_id VARCHAR(128),
    event_type VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    subscription_id VARCHAR(36),
    payload_hash VARCHAR(64),
    payload_summary JSONB,
    received_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_billing_event_id UNIQUE (billing_event_id),
    CONSTRAINT uq_elfis_billing_provider_event UNIQUE (provider_event_id)
);

CREATE INDEX IF NOT EXISTS ix_elfis_billing_events_organization_id
    ON elfis_billing_events (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_billing_events_event_type
    ON elfis_billing_events (event_type);
CREATE INDEX IF NOT EXISTS ix_elfis_billing_events_status
    ON elfis_billing_events (status);
