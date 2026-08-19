-- ELFIS Document Extraction RC2.5.4 — PostgreSQL idempotent
-- Compatible tests SQLite via SQLAlchemy metadata.

CREATE TABLE IF NOT EXISTS elfis_document_extraction_results (
    id VARCHAR(36) PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    processing_job_id VARCHAR(36) REFERENCES elfis_document_processing_jobs(id) ON DELETE SET NULL,
    ocr_result_id VARCHAR(36),
    classification_id VARCHAR(36),
    schema_key VARCHAR(64) NOT NULL,
    schema_version VARCHAR(32) NOT NULL,
    provider_key VARCHAR(64) NOT NULL,
    provider_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    confidence_score DOUBLE PRECISION,
    requires_review BOOLEAN NOT NULL DEFAULT TRUE,
    fields_count INTEGER NOT NULL DEFAULT 0,
    valid_fields_count INTEGER NOT NULL DEFAULT 0,
    invalid_fields_count INTEGER NOT NULL DEFAULT 0,
    missing_required_fields_count INTEGER NOT NULL DEFAULT 0,
    result_artifact_storage_object_id VARCHAR(36),
    result_checksum_sha256 VARCHAR(64),
    validation_summary_json JSONB,
    warnings_json JSONB,
    error_code VARCHAR(64),
    error_message_sanitized VARCHAR(255),
    selection_reason_code VARCHAR(64),
    source_reason_code VARCHAR(64),
    effective_document_type VARCHAR(64),
    idempotency_hash VARCHAR(64) NOT NULL DEFAULT 'default',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_elfis_extr_status CHECK (
        status IN (
            'pending','processing','completed','partially_completed','invalid',
            'failed','rejected','confirmed','superseded','blocked'
        )
    ),
    CONSTRAINT ck_elfis_extr_confidence CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    ),
    CONSTRAINT ck_elfis_extr_counts CHECK (
        fields_count >= 0 AND valid_fields_count >= 0
        AND invalid_fields_count >= 0 AND missing_required_fields_count >= 0
    )
);

-- Préfixe ix_elfis_dpextr_* / uq_elfis_dpextr_* : namespace distinct de
-- document_extraction (Migration Center, sprint4) — noms d'index uniques au schéma.
CREATE UNIQUE INDEX IF NOT EXISTS uq_elfis_dpextr_idempotency
    ON elfis_document_extraction_results (
        document_version_id, ocr_result_id, schema_key, schema_version,
        provider_key, provider_version, idempotency_hash
    );

CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_org_created
    ON elfis_document_extraction_results (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_document_created
    ON elfis_document_extraction_results (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_version
    ON elfis_document_extraction_results (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_ocr
    ON elfis_document_extraction_results (ocr_result_id);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_job
    ON elfis_document_extraction_results (processing_job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_status_created
    ON elfis_document_extraction_results (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_schema
    ON elfis_document_extraction_results (schema_key, schema_version);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_provider
    ON elfis_document_extraction_results (provider_key, provider_version);
CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_review_status
    ON elfis_document_extraction_results (requires_review, status);

CREATE TABLE IF NOT EXISTS elfis_document_extracted_fields (
    id VARCHAR(36) PRIMARY KEY,
    extraction_result_id VARCHAR(36) NOT NULL
        REFERENCES elfis_document_extraction_results(id) ON DELETE CASCADE,
    field_path VARCHAR(128) NOT NULL,
    field_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'extracted',
    normalized_value_json JSONB,
    display_value_masked VARCHAR(120),
    confidence_score DOUBLE PRECISION,
    source_page INTEGER,
    evidence_reference_json JSONB,
    validation_codes_json JSONB,
    manually_corrected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_elfis_dpextr_field_path UNIQUE (extraction_result_id, field_path),
    CONSTRAINT ck_elfis_dpextr_field_confidence CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)
    )
);

CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_fields_result
    ON elfis_document_extracted_fields (extraction_result_id);

CREATE TABLE IF NOT EXISTS elfis_document_extraction_reviews (
    id VARCHAR(36) PRIMARY KEY,
    extraction_result_id VARCHAR(36) NOT NULL
        REFERENCES elfis_document_extraction_results(id) ON DELETE CASCADE,
    action VARCHAR(32) NOT NULL,
    actor_user_id INTEGER,
    reason VARCHAR(255),
    patch_summary_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_dpextr_reviews_result
    ON elfis_document_extraction_reviews (extraction_result_id, created_at);
