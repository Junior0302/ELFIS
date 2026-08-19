-- ELFIS Document Classification Stage 2 (RC2.5.2) — PostgreSQL idempotent
-- Aucun OCR / IA. Pas de migration destructive.

CREATE TABLE IF NOT EXISTS elfis_document_classifications (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    document_version_id VARCHAR(36) NOT NULL,
    processing_job_id VARCHAR(36) NULL REFERENCES elfis_document_processing_jobs(id) ON DELETE SET NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    classifier_key VARCHAR(64) NOT NULL,
    classifier_version VARCHAR(32) NOT NULL,
    predicted_type VARCHAR(64) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (confidence_score >= 0 AND confidence_score <= 1),
    status VARCHAR(32) NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'confirmed', 'rejected', 'superseded', 'failed')),
    requires_review BOOLEAN NOT NULL DEFAULT TRUE,
    evidence_json JSONB NULL,
    alternatives_json JSONB NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'pipeline',
    confirmed_type VARCHAR(64) NULL,
    confirmed_by_user_id INTEGER NULL REFERENCES users(id),
    confirmed_at TIMESTAMP NULL,
    rejected_at TIMESTAMP NULL,
    rejection_reason VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_org_created
    ON elfis_document_classifications (organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_document_created
    ON elfis_document_classifications (document_id, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_version
    ON elfis_document_classifications (document_version_id);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_status_created
    ON elfis_document_classifications (status, created_at);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_predicted
    ON elfis_document_classifications (predicted_type);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_confirmed
    ON elfis_document_classifications (confirmed_type);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_review_status
    ON elfis_document_classifications (requires_review, status);
CREATE INDEX IF NOT EXISTS ix_elfis_doc_class_classifier
    ON elfis_document_classifications (classifier_key, classifier_version);
