"""Catalogue central des permissions ELFIS — format resource.action."""

from __future__ import annotations

import re
from enum import Enum

_PERMISSION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class Permission(str, Enum):
    """Permissions stables — ne pas disperser les chaînes dans le code."""

    # System Health
    SYSTEM_HEALTH_READ = "system.health.read"
    SYSTEM_HEALTH_REFRESH = "system.health.refresh"
    SYSTEM_METRICS_READ = "system.metrics.read"
    SYSTEM_ALERTS_READ = "system.alerts.read"
    SYSTEM_LOGS_READ = "system.logs.read"

    # Jobs / Events
    JOBS_READ = "jobs.read"
    JOBS_RETRY = "jobs.retry"
    JOBS_CANCEL = "jobs.cancel"
    EVENTS_READ = "events.read"
    EVENTS_RETRY = "events.retry"

    # Plateforme
    PLATFORM_DASHBOARD_READ = "platform.dashboard.read"
    PLATFORM_SETTINGS_READ = "platform.settings.read"
    PLATFORM_SETTINGS_MANAGE = "platform.settings.manage"
    PLATFORM_ADMIN = "platform.admin"
    PLATFORM_SUPPORT = "platform.support"
    PLATFORM_FINANCE = "platform.finance"
    PLATFORM_OPERATIONS = "platform.operations"
    # Developer Cockpit (technique) — non attribués auto aux admins métier
    PLATFORM_DEVELOPER = "platform.developer"
    PLATFORM_ENGINEER = "platform.engineer"
    PLATFORM_SRE = "platform.sre"
    PLATFORM_CTO = "platform.cto"

    # Utilisateurs
    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DISABLE = "users.disable"
    USERS_DELETE = "users.delete"
    USERS_ROLES_MANAGE = "users.roles.manage"

    # Organisations
    ORGANIZATIONS_READ = "organizations.read"
    ORGANIZATIONS_CREATE = "organizations.create"
    ORGANIZATIONS_UPDATE = "organizations.update"
    ORGANIZATIONS_DISABLE = "organizations.disable"
    ORGANIZATIONS_MEMBERS_MANAGE = "organizations.members.manage"

    # Abonnements / Billing
    SUBSCRIPTIONS_READ = "subscriptions.read"
    SUBSCRIPTIONS_MANAGE = "subscriptions.manage"
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"
    BILLING_REFUND = "billing.refund"

    # Support
    SUPPORT_ACCOUNTS_READ = "support.accounts.read"
    SUPPORT_SESSIONS_IMPERSONATE = "support.sessions.impersonate"
    SUPPORT_NOTES_MANAGE = "support.notes.manage"

    # Sécurité
    SECURITY_AUDIT_READ = "security.audit.read"
    SECURITY_AUDIT_EXPORT = "security.audit.export"
    SECURITY_AUDIT_RETENTION_READ = "security.audit.retention.read"
    SECURITY_AUDIT_RETENTION_MANAGE = "security.audit.retention.manage"
    SECURITY_INCIDENTS_READ = "security.incidents.read"
    SECURITY_INCIDENTS_MANAGE = "security.incidents.manage"
    SECURITY_PERMISSIONS_READ = "security.permissions.read"
    SECURITY_PERMISSIONS_MANAGE = "security.permissions.manage"

    # Vault
    VAULT_METADATA_READ = "vault.metadata.read"
    VAULT_SECRETS_READ = "vault.secrets.read"
    VAULT_SECRETS_MANAGE = "vault.secrets.manage"

    # Storage (plateforme)
    STORAGE_OBJECTS_READ = "storage.objects.read"
    STORAGE_OBJECTS_CREATE = "storage.objects.create"
    STORAGE_OBJECTS_DELETE = "storage.objects.delete"
    STORAGE_QUARANTINE_READ = "storage.quarantine.read"
    STORAGE_QUARANTINE_MANAGE = "storage.quarantine.manage"

    # Documents Registry (plateforme — distinct du RBAC org ComptaPilot)
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_CREATE = "documents.create"
    DOCUMENTS_ARCHIVE = "documents.archive"
    DOCUMENTS_DOWNLOAD = "documents.download"
    DOCUMENTS_MANAGE = "documents.manage"
    DOCUMENTS_VERSIONS_READ = "documents.versions.read"
    DOCUMENTS_VERSIONS_CREATE = "documents.versions.create"
    DOCUMENTS_DELETE = "documents.delete"
    DOCUMENTS_RESTORE = "documents.restore"
    DOCUMENTS_LEGAL_HOLD_READ = "documents.legal_hold.read"
    DOCUMENTS_LEGAL_HOLD_MANAGE = "documents.legal_hold.manage"
    DOCUMENTS_RETENTION_READ = "documents.retention.read"
    DOCUMENTS_RETENTION_MANAGE = "documents.retention.manage"
    STORAGE_OBJECTS_PURGE = "storage.objects.purge"
    STORAGE_MIGRATIONS_READ = "storage.migrations.read"
    STORAGE_MIGRATIONS_EXECUTE = "storage.migrations.execute"
    STORAGE_INTEGRITY_READ = "storage.integrity.read"
    STORAGE_INTEGRITY_EXECUTE = "storage.integrity.execute"
    STORAGE_PROVIDERS_READ = "storage.providers.read"
    STORAGE_PROVIDERS_MANAGE = "storage.providers.manage"

    # Document Processing RC2.5.1
    DOCUMENT_PROCESSING_JOBS_READ = "document_processing.jobs.read"
    DOCUMENT_PROCESSING_JOBS_CREATE = "document_processing.jobs.create"
    DOCUMENT_PROCESSING_JOBS_CANCEL = "document_processing.jobs.cancel"
    DOCUMENT_PROCESSING_JOBS_RETRY = "document_processing.jobs.retry"
    DOCUMENT_PROCESSING_JOBS_MANAGE = "document_processing.jobs.manage"
    DOCUMENT_PROCESSING_PIPELINES_READ = "document_processing.pipelines.read"
    DOCUMENT_PROCESSING_WORKERS_READ = "document_processing.workers.read"
    DOCUMENT_PROCESSING_WORKERS_MANAGE = "document_processing.workers.manage"
    DOCUMENT_PROCESSING_CLASSIFICATIONS_READ = "document_processing.classifications.read"
    DOCUMENT_PROCESSING_CLASSIFICATIONS_CREATE = "document_processing.classifications.create"
    DOCUMENT_PROCESSING_CLASSIFICATIONS_REVIEW = "document_processing.classifications.review"
    DOCUMENT_PROCESSING_CLASSIFICATIONS_RECLASSIFY = "document_processing.classifications.reclassify"
    DOCUMENT_PROCESSING_TAXONOMY_READ = "document_processing.taxonomy.read"
    DOCUMENT_PROCESSING_TAXONOMY_MANAGE = "document_processing.taxonomy.manage"
    DOCUMENT_PROCESSING_OCR_READ = "document_processing.ocr.read"
    DOCUMENT_PROCESSING_OCR_CREATE = "document_processing.ocr.create"
    DOCUMENT_PROCESSING_OCR_RETRY = "document_processing.ocr.retry"
    DOCUMENT_PROCESSING_OCR_REJECT = "document_processing.ocr.reject"
    DOCUMENT_PROCESSING_OCR_TEXT_READ = "document_processing.ocr.text.read"
    DOCUMENT_PROCESSING_OCR_PROVIDERS_READ = "document_processing.ocr.providers.read"
    DOCUMENT_PROCESSING_OCR_PROVIDERS_MANAGE = "document_processing.ocr.providers.manage"
    DOCUMENT_PROCESSING_EXTRACTIONS_READ = "document_processing.extractions.read"
    DOCUMENT_PROCESSING_EXTRACTIONS_CREATE = "document_processing.extractions.create"
    DOCUMENT_PROCESSING_EXTRACTIONS_REVIEW = "document_processing.extractions.review"
    DOCUMENT_PROCESSING_EXTRACTIONS_CORRECT = "document_processing.extractions.correct"
    DOCUMENT_PROCESSING_EXTRACTIONS_RETRY = "document_processing.extractions.retry"
    DOCUMENT_PROCESSING_EXTRACTIONS_CONTENT_READ = "document_processing.extractions.content.read"
    DOCUMENT_PROCESSING_EXTRACTION_SCHEMAS_READ = "document_processing.extraction_schemas.read"
    DOCUMENT_PROCESSING_EXTRACTION_SCHEMAS_MANAGE = "document_processing.extraction_schemas.manage"
    DOCUMENT_PROCESSING_EXTRACTION_PROVIDERS_READ = "document_processing.extraction_providers.read"
    DOCUMENT_PROCESSING_EXTRACTION_PROVIDERS_MANAGE = "document_processing.extraction_providers.manage"
    DOCUMENT_PROCESSING_BUSINESS_VALIDATIONS_READ = "document_processing.business_validations.read"
    DOCUMENT_PROCESSING_BUSINESS_VALIDATIONS_CREATE = "document_processing.business_validations.create"
    DOCUMENT_PROCESSING_BUSINESS_VALIDATIONS_REVIEW = "document_processing.business_validations.review"
    DOCUMENT_PROCESSING_BUSINESS_VALIDATIONS_CONFIRM = "document_processing.business_validations.confirm"
    PRODUCT_INTEGRATIONS_PACKAGES_READ = "product_integrations.packages.read"
    PRODUCT_INTEGRATIONS_PACKAGES_CREATE = "product_integrations.packages.create"
    PRODUCT_INTEGRATIONS_DELIVERIES_READ = "product_integrations.deliveries.read"
    PRODUCT_INTEGRATIONS_DELIVERIES_CREATE = "product_integrations.deliveries.create"
    PRODUCT_INTEGRATIONS_DELIVERIES_RETRY = "product_integrations.deliveries.retry"
    PRODUCT_INTEGRATIONS_BRIDGES_READ = "product_integrations.bridges.read"
    PRODUCT_INTEGRATIONS_BRIDGES_MANAGE = "product_integrations.bridges.manage"
    PRODUCT_INTEGRATIONS_COMPTAPILOT_PUBLISH = "product_integrations.comptapilot.publish"
    # Migration Center (Assistant de Migration)
    MIGRATION_CENTER_READ = "migration_center.read"
    MIGRATION_CENTER_CREATE = "migration_center.create"
    MIGRATION_CENTER_UPDATE = "migration_center.update"
    MIGRATION_CENTER_CANCEL = "migration_center.cancel"
    # Document Intake Engine
    DOCUMENT_INTAKE_READ = "document_intake.read"
    DOCUMENT_INTAKE_UPLOAD = "document_intake.upload"
    DOCUMENT_INTAKE_CANCEL = "document_intake.cancel"
    # Document Analysis Pipeline
    DOCUMENT_ANALYSIS_READ = "document_analysis.read"
    DOCUMENT_ANALYSIS_RUN = "document_analysis.run"
    # Document Extraction Engine
    DOCUMENT_EXTRACTION_READ = "document_extraction.read"
    DOCUMENT_EXTRACTION_RUN = "document_extraction.run"
    DOCUMENT_EXTRACTION_RETRY = "document_extraction.retry"
    DOCUMENT_EXTRACTION_CANCEL = "document_extraction.cancel"
    DOCUMENT_EXTRACTION_VIEW_SENSITIVE = "document_extraction.view_sensitive"
    # Validation & Mapping Center
    VALIDATION_READ = "validation.read"
    VALIDATION_EDIT = "validation.edit"
    VALIDATION_VALIDATE = "validation.validate"
    VALIDATION_REJECT = "validation.reject"
    VALIDATION_HISTORY = "validation.history"
    VALIDATION_MATCH = "validation.match"

    # Import Engine (Sprint 6)
    IMPORT_READ = "import.read"
    IMPORT_RUN = "import.run"
    IMPORT_ROLLBACK = "import.rollback"
    IMPORT_REPORT = "import.report"

    # Smart Migration (Sprint 7)
    SMART_MIGRATION_READ = "smart_migration.read"
    SMART_MIGRATION_RUN = "smart_migration.run"
    SMART_MIGRATION_CANCEL = "smart_migration.cancel"
    SMART_MIGRATION_RESUME = "smart_migration.resume"
    SMART_MIGRATION_REPORT = "smart_migration.report"
    SMART_MIGRATION_CLEANUP = "smart_migration.cleanup"

    # Accounting Engine V2
    ACCOUNTING_ENGINE_READ = "accounting_engine.read"
    ACCOUNTING_ENGINE_GENERATE = "accounting_engine.generate"
    ACCOUNTING_ENGINE_REGENERATE = "accounting_engine.regenerate"

    # Accounting Intelligence V2
    ACCOUNTING_INTELLIGENCE_READ = "accounting_intelligence.read"
    ACCOUNTING_INTELLIGENCE_FEEDBACK = "accounting_intelligence.feedback"
    ACCOUNTING_INTELLIGENCE_RETRAIN = "accounting_intelligence.retrain"

    # Produits
    PRODUCTS_READ = "products.read"
    PRODUCTS_MANAGE = "products.manage"
    PRODUCT_ACCESS_READ = "product_access.read"
    PRODUCT_ACCESS_MANAGE = "product_access.manage"


def all_permissions() -> frozenset[str]:
    return frozenset(p.value for p in Permission)


_ALL = all_permissions()


def is_known_permission(permission: str) -> bool:
    return permission in _ALL


def validate_permission(permission: str) -> str:
    """Valide format + existence. Lève ValueError si inconnu/malformé."""
    if not permission or not isinstance(permission, str):
        raise ValueError("permission invalide")
    code = permission.strip()
    if not _PERMISSION_RE.match(code):
        raise ValueError("format permission invalide (attendu resource.action)")
    if code not in _ALL:
        raise ValueError("permission inconnue")
    return code


def assert_no_duplicate_permissions() -> None:
    values = [p.value for p in Permission]
    if len(values) != len(set(values)):
        raise RuntimeError("doublons dans le catalogue Permission")
