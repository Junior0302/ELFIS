-- ELFIS Document Business Validation RC2.5.5 — PostgreSQL idempotent

CREATE TABLE IF NOT EXISTS elfis_document_business_validations (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    extraction_result_id VARCHAR(36) NOT NULL,
    classification_id VARCHAR(36),
    processing_job_id VARCHAR(36) REFERENCES elfis_document_processing_jobs(id) ON DELETE SET NULL,
    rule_set_key VARCHAR(64) NOT NULL,
    rule_set_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    valid BOOLEAN NOT NULL DEFAULT FALSE,
    blocking_issue_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    info_count INTEGER NOT NULL DEFAULT 0,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    validation_artifact_storage_object_id VARCHAR(36),
    artifact_checksum_sha256 VARCHAR(64),
    error_code VARCHAR(64),
    error_message_sanitized VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_bv_status CHECK (
        status IN (
            'pending','processing','valid','valid_with_warnings','invalid',
            'review_required','failed','rejected','superseded','blocked'
        )
    ),
    CONSTRAINT ck_elfis_bv_counts CHECK (
        blocking_issue_count >= 0 AND warning_count >= 0 AND info_count >= 0
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_bv_org_created
    ON elfis_document_business_validations (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_document_created
    ON elfis_document_business_validations (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_version
    ON elfis_document_business_validations (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_extraction
    ON elfis_document_business_validations (extraction_result_id);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_status_created
    ON elfis_document_business_validations (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_review
    ON elfis_document_business_validations (requires_review, status);

CREATE TABLE IF NOT EXISTS elfis_document_validation_issues (
    id VARCHAR(36) PRIMARY KEY,
    business_validation_id VARCHAR(36) NOT NULL
        REFERENCES elfis_document_business_validations(id) ON DELETE CASCADE,
    rule_key VARCHAR(64) NOT NULL,
    rule_version VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    field_paths_json JSONB,
    issue_code VARCHAR(64) NOT NULL,
    message_code VARCHAR(64),
    parameters_json JSONB,
    blocking BOOLEAN NOT NULL DEFAULT FALSE,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolution_type VARCHAR(32),
    resolved_by_user_id INTEGER,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_bv_issue_severity CHECK (
        severity IN ('info','warning','error','critical')
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_bv_issues_validation
    ON elfis_document_validation_issues (business_validation_id);
CREATE INDEX IF NOT EXISTS ix_elfis_bv_issues_code
    ON elfis_document_validation_issues (issue_code);
