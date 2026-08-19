-- ELFIS Product Document Integrations RC2.5.5 — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_product_processing_packages (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    product_key VARCHAR(64) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    classification_id VARCHAR(36),
    ocr_result_id VARCHAR(36),
    extraction_result_id VARCHAR(36) NOT NULL,
    business_validation_id VARCHAR(36) NOT NULL,
    package_schema_key VARCHAR(64) NOT NULL,
    package_schema_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    content_artifact_storage_object_id VARCHAR(36),
    checksum_sha256 VARCHAR(64),
    idempotency_key VARCHAR(128) NOT NULL,
    created_by_user_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_pkg_idempotency UNIQUE (idempotency_key),
    CONSTRAINT ck_elfis_pkg_status CHECK (
        status IN (
            'draft','ready','delivery_pending','delivered','delivery_failed',
            'rejected','superseded','revoked'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_pkg_org_created
    ON elfis_product_processing_packages (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_document_created
    ON elfis_product_processing_packages (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_version
    ON elfis_product_processing_packages (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_extraction
    ON elfis_product_processing_packages (extraction_result_id);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_validation
    ON elfis_product_processing_packages (business_validation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_product_status
    ON elfis_product_processing_packages (product_key, status);
CREATE INDEX IF NOT EXISTS ix_elfis_pkg_status_created
    ON elfis_product_processing_packages (status, created_at);

CREATE TABLE IF NOT EXISTS elfis_product_document_deliveries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    package_id VARCHAR(36) NOT NULL
        REFERENCES elfis_product_processing_packages(id) ON DELETE CASCADE,
    product_key VARCHAR(64) NOT NULL,
    bridge_key VARCHAR(64) NOT NULL,
    bridge_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    idempotency_key VARCHAR(128) NOT NULL,
    external_reference VARCHAR(128),
    last_error_code VARCHAR(64),
    last_error_message_sanitized VARCHAR(255),
    next_retry_at TIMESTAMP,
    locked_by VARCHAR(64),
    locked_until TIMESTAMP,
    started_at TIMESTAMP,
    delivered_at TIMESTAMP,
    failed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_del_idempotency UNIQUE (idempotency_key),
    CONSTRAINT ck_elfis_del_status CHECK (
        status IN (
            'pending','queued','delivering','delivered','retrying',
            'failed','cancelled','blocked'
        )
    ),
    CONSTRAINT ck_elfis_del_attempts CHECK (attempt_count >= 0 AND max_attempts >= 1)
);

CREATE INDEX IF NOT EXISTS ix_elfis_del_package
    ON elfis_product_document_deliveries (package_id);
CREATE INDEX IF NOT EXISTS ix_elfis_del_product_status
    ON elfis_product_document_deliveries (product_key, status);
CREATE INDEX IF NOT EXISTS ix_elfis_del_status_retry
    ON elfis_product_document_deliveries (status, next_retry_at);
CREATE INDEX IF NOT EXISTS ix_elfis_del_locked
    ON elfis_product_document_deliveries (locked_until);
CREATE INDEX IF NOT EXISTS ix_elfis_del_org_created
    ON elfis_product_document_deliveries (organization_id, created_at);

CREATE TABLE IF NOT EXISTS elfis_product_document_delivery_attempts (
    id VARCHAR(36) PRIMARY KEY,
    delivery_id VARCHAR(36) NOT NULL
        REFERENCES elfis_product_document_deliveries(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    worker_id VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'started',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    response_code VARCHAR(64),
    error_code VARCHAR(64),
    retryable BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json JSONB
);

CREATE INDEX IF NOT EXISTS ix_elfis_del_att_delivery
    ON elfis_product_document_delivery_attempts (delivery_id);
CREATE INDEX IF NOT EXISTS ix_elfis_del_att_number
    ON elfis_product_document_delivery_attempts (delivery_id, attempt_number);
