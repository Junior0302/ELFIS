-- ELFIS Notification Service V1 — Postgres
-- Exécuter sur DATABASE_URL. Réexécutable via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS elfis_notifications (
    id VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'info',
    action_url VARCHAR(512),
    action_label VARCHAR(128),
    related_entity_type VARCHAR(64),
    related_entity_id VARCHAR(128),
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'unread',
    read_at TIMESTAMP WITHOUT TIME ZONE,
    archived_at TIMESTAMP WITHOUT TIME ZONE,
    expires_at TIMESTAMP WITHOUT TIME ZONE,
    source_event_id VARCHAR(36),
    correlation_id VARCHAR(36),
    idempotency_key VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_notifications_notification_id UNIQUE (notification_id),
    CONSTRAINT ck_elfis_notifications_status CHECK (
        status IN ('unread', 'read', 'archived', 'expired')
    ),
    CONSTRAINT ck_elfis_notifications_severity CHECK (
        severity IN ('info', 'success', 'warning', 'error', 'critical')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_notifications_organization_id ON elfis_notifications (organization_id);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_user_id ON elfis_notifications (user_id);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_status ON elfis_notifications (status);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_category ON elfis_notifications (category);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_notification_type ON elfis_notifications (notification_type);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_created_at ON elfis_notifications (created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_expires_at ON elfis_notifications (expires_at);
CREATE INDEX IF NOT EXISTS ix_elfis_notifications_source_event_id ON elfis_notifications (source_event_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_notifications_idempotency_key
    ON elfis_notifications (idempotency_key)
    WHERE idempotency_key IS NOT NULL AND idempotency_key <> '';

CREATE TABLE IF NOT EXISTS elfis_notification_deliveries (
    id VARCHAR(36) PRIMARY KEY,
    notification_id VARCHAR(36) NOT NULL REFERENCES elfis_notifications (notification_id),
    channel VARCHAR(32) NOT NULL,
    recipient VARCHAR(255),
    status VARCHAR(32) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    provider VARCHAR(64),
    provider_message_id VARCHAR(255),
    scheduled_at TIMESTAMP WITHOUT TIME ZONE,
    started_at TIMESTAMP WITHOUT TIME ZONE,
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    failed_at TIMESTAMP WITHOUT TIME ZONE,
    last_error TEXT,
    idempotency_key VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_notification_deliveries_channel CHECK (
        channel IN ('in_app', 'email', 'sms', 'push', 'webhook')
    ),
    CONSTRAINT ck_elfis_notification_deliveries_status CHECK (
        status IN ('pending', 'processing', 'sent', 'failed', 'retry', 'cancelled', 'skipped')
    ),
    CONSTRAINT uq_elfis_notification_deliveries_triplet
        UNIQUE (notification_id, channel, recipient)
);

CREATE INDEX IF NOT EXISTS ix_elfis_notification_deliveries_notification_id
    ON elfis_notification_deliveries (notification_id);
CREATE INDEX IF NOT EXISTS ix_elfis_notification_deliveries_status
    ON elfis_notification_deliveries (status);
CREATE INDEX IF NOT EXISTS ix_elfis_notification_deliveries_channel
    ON elfis_notification_deliveries (channel);

CREATE TABLE IF NOT EXISTS elfis_notification_preferences (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    notification_type VARCHAR(128) NOT NULL,
    in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sms_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    push_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    digest_mode VARCHAR(32) NOT NULL DEFAULT 'immediate',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_notification_preferences_triplet
        UNIQUE (organization_id, user_id, notification_type),
    CONSTRAINT ck_elfis_notification_preferences_digest CHECK (
        digest_mode IN ('immediate', 'daily', 'weekly', 'disabled')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_notification_preferences_org_user
    ON elfis_notification_preferences (organization_id, user_id);
