-- ELFIS Document OCR Stage 3 (RC2.5.3) — PostgreSQL idempotent
-- Framework OCR + artefacts texte. Pas d'IA générative.

CREATE TABLE IF NOT EXISTS elfis_document_ocr_results (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    processing_job_id VARCHAR(36) NULL REFERENCES elfis_document_processing_jobs(id) ON DELETE SET NULL,
    provider_key VARCHAR(64) NOT NULL,
    provider_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','processing','completed','partially_completed','failed','rejected','superseded','blocked')),
    extraction_method VARCHAR(64) NOT NULL DEFAULT 'unknown',
    page_count INTEGER NOT NULL DEFAULT 0 CHECK (page_count >= 0),
    processed_page_count INTEGER NOT NULL DEFAULT 0 CHECK (processed_page_count >= 0),
    detected_languages_json JSONB NULL,
    average_confidence DOUBLE PRECISION NULL
        CHECK (average_confidence IS NULL OR (average_confidence >= 0 AND average_confidence <= 1)),
    text_artifact_storage_object_id VARCHAR(36) NULL,
    text_length INTEGER NOT NULL DEFAULT 0 CHECK (text_length >= 0),
    text_checksum_sha256 VARCHAR(64) NULL,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    warnings_json JSONB NULL,
    error_code VARCHAR(64) NULL,
    error_message_sanitized VARCHAR(255) NULL,
    selection_reason_code VARCHAR(64) NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_ocr_org_created
    ON elfis_document_ocr_results (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_document_created
    ON elfis_document_ocr_results (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_version
    ON elfis_document_ocr_results (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_job
    ON elfis_document_ocr_results (processing_job_id);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_status_created
    ON elfis_document_ocr_results (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_provider_created
    ON elfis_document_ocr_results (provider_key, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_ocr_review_status
    ON elfis_document_ocr_results (requires_review, status);

CREATE TABLE IF NOT EXISTS elfis_document_ocr_pages (
    id VARCHAR(36) PRIMARY KEY,
    ocr_result_id VARCHAR(36) NOT NULL REFERENCES elfis_document_ocr_results(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    character_count INTEGER NOT NULL DEFAULT 0 CHECK (character_count >= 0),
    word_count INTEGER NULL,
    confidence DOUBLE PRECISION NULL
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    detected_language VARCHAR(16) NULL,
    rotation_degrees DOUBLE PRECISION NULL,
    text_checksum_sha256 VARCHAR(64) NULL,
    warnings_json JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (ocr_result_id, page_number)
);

CREATE INDEX IF NOT EXISTS ix_elfis_ocr_pages_result
    ON elfis_document_ocr_pages (ocr_result_id);
