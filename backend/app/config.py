from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_DB = (_BACKEND_DIR / "comptapilot.db").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    app_env: str = "development"
    database_url: str = f"sqlite:///{_DEFAULT_DB}"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle: int = 1800
    database_pool_timeout: int = 30
    storage_dir: str = str(_BACKEND_DIR / "storage")
    # Document Intake Sprint 2.5 — provider dédié (local uniquement pour l'instant)
    document_intake_storage_provider: str = "local"  # local | s3 | azure_blob | gcs | minio
    document_intake_fingerprint_block_size: int = 65_536
    # ELFIS Storage Abstraction RC2.4 — défaut local (tests / dev)
    storage_provider: str = "local"  # local | supabase | disabled
    storage_local_root: str = ""  # vide → storage_dir/elfis_objects
    storage_max_file_size_bytes: int = 15 * 1024 * 1024
    storage_allowed_mime_types: str = (
        "application/pdf,image/png,image/jpeg,text/plain,application/json,text/csv"
    )
    storage_blocked_extensions: str = (
        ".exe,.bat,.cmd,.sh,.ps1,.msi,.dll,.com,.scr,.js,.html,.htm,.php,.svg"
    )
    storage_checksum_enabled: bool = True
    storage_quarantine_enabled: bool = False
    storage_quarantine_namespace: str = "quarantine"
    storage_upload_chunk_size_bytes: int = 65_536
    storage_disk_degraded_percent: float = 85.0
    storage_disk_unhealthy_percent: float = 95.0
    storage_probe_timeout_seconds: float = 5.0
    # Document retention RC2.4 étape 3
    document_retention_default_days: int = 365
    document_retention_deleted_grace_days: int = 30
    document_retention_archived_days: int = 730
    document_retention_security_min_days: int = 90
    document_purge_batch_size: int = 100
    # Supabase Storage document registry (réutilise supabase_url / service_role si vides)
    supabase_storage_url: str = ""
    supabase_storage_service_role_key: str = ""
    supabase_storage_bucket: str = "elfis-documents"
    supabase_storage_temp_namespace: str = "temp"
    supabase_storage_document_namespace: str = "documents"
    supabase_storage_quarantine_namespace: str = "quarantine"
    supabase_storage_request_timeout_seconds: float = 60.0
    supabase_storage_download_url_ttl_seconds: int = 300
    supabase_storage_max_retries: int = 2
    storage_migration_batch_size: int = 50
    storage_download_mode: str = "proxy"
    # Document Processing RC2.5.1
    document_processing_enabled: bool = True
    document_processing_auto_enqueue: bool = False
    document_processing_default_pipeline: str = "document_basic_v1"
    document_processing_worker_poll_seconds: float = 2.0
    document_processing_lease_seconds: int = 60
    document_processing_heartbeat_seconds: int = 15
    document_processing_job_timeout_seconds: int = 900
    document_processing_default_step_timeout_seconds: int = 120
    document_processing_max_attempts: int = 3
    document_processing_retry_initial_seconds: int = 10
    document_processing_retry_max_seconds: int = 300
    document_processing_queue_degraded_age_seconds: int = 300
    document_processing_queue_unhealthy_age_seconds: int = 1800
    # Document Classification RC2.5.2 (heuristique, pas IA)
    document_classification_enabled: bool = True
    document_classification_default_pipeline: str = "document_classification_v1"
    document_classification_confirm_threshold: float = 0.90
    document_classification_review_threshold: float = 0.55
    document_classification_auto_confirm: bool = False
    document_classification_filename_rules_enabled: bool = True
    document_classification_metadata_rules_enabled: bool = True
    document_classification_max_alternatives: int = 3
    document_classification_evidence_max_items: int = 20
    # Document OCR RC2.5.3 (framework — défaut désactivé / noop)
    document_ocr_enabled: bool = False
    document_ocr_provider: str = "noop"
    document_ocr_default_pipeline: str = "document_ocr_v1"
    document_ocr_allowed_mime_types: str = "application/pdf,image/png,image/jpeg,image/tiff"
    document_ocr_default_languages: str = "fra,eng"
    document_ocr_max_file_size_bytes: int = 20_971_520
    document_ocr_max_pages: int = 50
    document_ocr_max_text_characters: int = 500_000
    document_ocr_max_page_characters: int = 50_000
    document_ocr_max_processing_seconds: int = 180
    document_ocr_max_concurrent_pages: int = 2
    document_ocr_artifact_max_bytes: int = 2_097_152
    document_ocr_artifact_namespace: str = "processing-artifacts"
    document_ocr_native_pdf_text_enabled: bool = True
    document_ocr_force_image_ocr: bool = False
    document_ocr_auto_enqueue: bool = False
    # Document Extraction RC2.5.4 (framework — défaut désactivé / noop)
    document_extraction_enabled: bool = False
    document_extraction_provider: str = "noop"
    document_extraction_default_pipeline: str = "document_extraction_v1"
    document_extraction_default_generic_schema: str = "generic_document_v1"
    document_extraction_auto_enqueue: bool = False
    document_extraction_auto_confirm: bool = False
    document_extraction_review_threshold: float = 0.80
    document_extraction_max_source_characters: int = 500_000
    document_extraction_max_result_bytes: int = 1_048_576
    document_extraction_max_fields: int = 100
    document_extraction_max_array_items: int = 50
    document_extraction_max_field_length: int = 2000
    document_extraction_timeout_seconds: int = 120
    document_extraction_rules_enabled: bool = True
    document_extraction_artifact_namespace: str = "processing-artifacts"
    # Document Business Validation RC2.5.5 (métier documentaire — pas comptable)
    document_business_validation_enabled: bool = False
    document_business_validation_default_pipeline: str = "document_business_validation_v1"
    document_business_validation_auto_enqueue: bool = False
    document_business_validation_timeout_seconds: int = 120
    document_validation_amount_tolerance: str = "0.02"
    document_validation_percentage_tolerance: str = "0.01"
    document_validation_require_confirmed_extraction: bool = True
    # Product document bridge RC2.5.5 (ComptaPilot désactivé par défaut)
    product_document_bridge_enabled: bool = False
    product_document_bridge_default: str = "noop"
    product_delivery_worker_poll_seconds: int = 2
    product_delivery_lease_seconds: int = 60
    product_delivery_max_attempts: int = 3
    product_delivery_retry_initial_seconds: int = 10
    product_delivery_retry_max_seconds: int = 300
    comptapilot_document_publish_enabled: bool = False
    comptapilot_document_auto_publish: bool = False
    comptapilot_require_confirmed_extraction: bool = True
    comptapilot_require_valid_business_validation: bool = True
    # disabled | dry_run | live — défaut disabled (RC2.5.6)
    comptapilot_document_bridge_mode: str = "disabled"
    # Banking Platform V1 — identifiants fournisseurs (jamais utilisés hors connecteurs)
    banking_bridge_api_url: str = "https://api.bridgeapi.io"
    banking_bridge_client_id: str = ""
    banking_bridge_client_secret: str = ""
    # Callback ELFIS pour le retour Bridge Connect (domaine à autoriser chez Bridge)
    banking_bridge_redirect_uri: str = ""
    # None = auto (on hors production, off en production). true uniquement si activé volontairement.
    elfis_demo_bank_enabled: bool | None = None
    banking_powens_api_url: str = ""
    banking_powens_client_id: str = ""
    banking_powens_client_secret: str = ""
    banking_sync_max_attempts: int = 3
    banking_sync_max_pages: int = 50
    banking_sync_max_transactions_per_run: int = 10000
    banking_sync_overlap_days: int = 7
    banking_sync_run_timeout_seconds: int = 180
    # Financial Dashboard V1 — cache et seuils d'alertes
    financial_cache_ttl_seconds: int = 60
    financial_treasury_low_threshold: float = 5000.0
    financial_treasury_critical_threshold: float = 1000.0
    financial_vat_high_threshold: float = 5000.0
    # AI Financial Assistant V1
    ai_assistant_cache_ttl_seconds: int = 45
    ai_assistant_max_llm_calls_per_hour: int = 60
    # "*" = accessible depuis n'importe quel appareil du réseau (MVP LAN)
    cors_origins: str = "*"
    app_name: str = "ELFIS Core"
    product_name: str = "ComptaPilot IA"
    jwt_secret: str = "comptapilot-elfis-dev-secret-change-me"
    auth_required: bool = True
    firebase_web_api_key: str = ""
    firebase_project_id: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    # Alias plans Billing V1 (starter = offre 19 € actuelle = STRIPE_PRICE_PRO)
    stripe_price_starter_monthly: str = ""
    stripe_price_professional_monthly: str = ""
    stripe_price_enterprise_monthly: str = ""
    stripe_trial_days: int = 14
    # Aligné sur Billing V1 (7 j) — ne plus diverger de elfis_billing_past_due_grace_days
    stripe_past_due_grace_days: int = 7
    subscription_terms_version: str = "v1"
    subscription_cron_token: str = ""
    # ELFIS Billing — Subscriptions / Entitlements / Quotas V1
    elfis_billing_enabled: bool = True
    elfis_billing_provider: str = "stripe"
    elfis_default_plan_code: str = "starter"
    elfis_trial_days: int = 14
    # C1.2 — POST /api/dev/activate-trial (development|test uniquement ; défaut off)
    elfis_dev_trial_enabled: bool = False
    elfis_billing_past_due_grace_days: int = 7
    elfis_billing_sync_grace_seconds: int = 3600
    elfis_billing_webhook_max_bytes: int = 1_048_576
    elfis_billing_usage_warning_percent: int = 80
    elfis_billing_usage_critical_percent: int = 100
    # Soft gates : off par défaut pour ne pas casser les flux existants ;
    # activer en prod après validation commerciale des matrices features/quotas.
    elfis_billing_enforce_entitlements: bool = False
    elfis_billing_enforce_quotas: bool = False
    frontend_url: str = "http://localhost:5173"
    # URL publique HTTPS de l’API (Render) — pour avatars / liens absolus
    public_api_url: str = ""
    platform_admin_emails: str = ""
    # E-mail transactionnel : clé Brevo = plateforme uniquement (jamais par org)
    brevo_api_key: str = ""
    brevo_webhook_secret: str = ""
    # Adresse technique authentifiée (ex. documents@elfiscore.com)
    platform_email_from: str = ""
    platform_email_from_name: str = "ELFIS Core"
    # Alias rétrocompatibles
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    # OAuth boîtes org + chiffrement des jetons
    email_credentials_encryption_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_oauth_redirect_uri: str = ""
    # ELFIS Vault — Supabase Storage (service role côté serveur uniquement)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    elfis_vault_bucket: str = "elfis-vault"
    elfis_vault_max_file_size_mb: int = 15
    elfis_vault_signed_url_ttl_seconds: int = 300
    # ELFIS Event Bus V1
    elfis_event_worker_enabled: bool = False
    elfis_event_worker_batch_size: int = 20
    elfis_event_worker_poll_interval_seconds: float = 2.0
    elfis_event_max_attempts: int = 5
    elfis_event_retry_base_seconds: int = 10
    elfis_event_lock_timeout_seconds: int = 300
    elfis_event_worker_id: str = ""
    # ELFIS Job Queue V1
    elfis_job_worker_enabled: bool = False
    elfis_job_worker_queues: str = "default"
    elfis_job_worker_batch_size: int = 10
    elfis_job_worker_poll_interval_seconds: float = 2.0
    elfis_job_max_attempts: int = 5
    elfis_job_retry_base_seconds: int = 15
    elfis_job_lock_timeout_seconds: int = 300
    elfis_job_heartbeat_interval_seconds: int = 30
    elfis_job_default_timeout_seconds: int = 300
    elfis_job_worker_id: str = ""
    elfis_job_max_payload_bytes: int = 65536
    elfis_job_max_result_bytes: int = 65536
    elfis_vault_metadata_job_enabled: bool = True
    # ELFIS AI Engine V1
    elfis_ai_enabled: bool = True
    elfis_ai_provider: str = "openai"
    elfis_ai_default_model: str = ""  # vide → openai_chat_model
    elfis_ai_fast_model: str = ""
    elfis_ai_complex_model: str = ""
    elfis_ai_request_timeout_seconds: int = 120
    elfis_ai_max_retries: int = 2
    elfis_ai_max_input_bytes: int = 262144
    elfis_ai_max_output_bytes: int = 65536
    elfis_ai_max_executions_per_org_per_day: int = 1000
    elfis_ai_max_concurrent_jobs_per_org: int = 10
    # ELFIS Document Intelligence V1
    elfis_document_intelligence_enabled: bool = True
    elfis_auto_text_extraction_enabled: bool = True
    elfis_auto_ai_analysis_enabled: bool = True
    elfis_document_max_file_bytes: int = 20_971_520
    elfis_document_max_pages: int = 200
    elfis_document_max_extracted_text_bytes: int = 1_048_576
    elfis_document_min_text_characters: int = 50
    elfis_document_min_text_per_page: int = 20
    elfis_document_text_retention_days: int = 365
    elfis_ocr_enabled: bool = False
    elfis_ocr_provider: str = "disabled"
    elfis_ocr_request_timeout_seconds: int = 180
    elfis_ocr_max_retries: int = 2
    # ELFIS Accounting Pipeline V1
    elfis_accounting_pipeline_enabled: bool = True
    elfis_auto_accounting_proposal_enabled: bool = True
    elfis_accounting_amount_tolerance: float = 0.02
    elfis_accounting_balance_tolerance: float = 0.01
    elfis_accounting_auto_ready_confidence: float = 0.90
    elfis_accounting_high_amount_review_threshold: float = 10000
    elfis_accounting_require_review_on_default_account: bool = True
    elfis_default_purchase_account: str = "607000"
    elfis_default_sales_account: str = "707000"
    elfis_default_supplier_account: str = "401000"
    elfis_default_customer_account: str = "411000"
    elfis_default_deductible_vat_account: str = "445660"
    elfis_default_collected_vat_account: str = "445710"
    elfis_default_purchase_journal: str = "ACH"
    elfis_default_sales_journal: str = "VTE"
    # ELFIS Search Engine V1
    elfis_search_enabled: bool = True
    elfis_auto_search_indexing_enabled: bool = True
    elfis_search_language: str = "french"
    elfis_search_max_query_length: int = 200
    elfis_search_max_page_size: int = 100
    elfis_search_default_page_size: int = 20
    elfis_search_max_content_bytes: int = 65_536
    elfis_search_suggestion_limit: int = 10
    elfis_search_snippet_length: int = 240
    elfis_search_reindex_batch_size: int = 100
    # ELFIS Platform Admin & Operations V1
    elfis_platform_admin_enabled: bool = True
    elfis_platform_incidents_enabled: bool = True
    elfis_platform_admin_default_page_size: int = 25
    elfis_platform_admin_max_page_size: int = 100
    elfis_platform_admin_search_limit: int = 20
    elfis_platform_admin_audit_retention_days: int = 730
    elfis_platform_incident_dedup_window_seconds: int = 3600
    elfis_platform_admin_require_action_reason: bool = True

    # ELFIS System Health Center (RC2.1+)
    # Modes: real | mock | disabled — défaut mock (sûr pour tests)
    app_version: str = "0.8.9"
    system_health_use_real_providers: bool = False
    system_health_api_provider: str = "mock"
    system_health_postgres_provider: str = "mock"
    system_health_jobs_provider: str = "mock"
    system_health_events_provider: str = "mock"
    system_health_search_provider: str = "mock"
    system_health_storage_provider: str = "mock"
    system_health_document_processing_provider: str = "mock"
    system_health_document_ocr_provider: str = "mock"
    system_health_document_extraction_provider: str = "mock"
    system_health_business_validation_provider: str = "mock"
    system_health_product_integrations_provider: str = "mock"
    system_health_cache_ttl_seconds: float = 15.0
    system_health_provider_timeout_seconds: float = 5.0
    system_health_postgres_latency_degraded_ms: float = 100.0
    system_health_postgres_latency_unhealthy_ms: float = 500.0
    system_health_postgres_pool_usage_degraded: float = 0.80
    system_health_jobs_pending_degraded: int = 50
    system_health_jobs_failed_degraded: int = 1
    system_health_jobs_oldest_pending_degraded_seconds: int = 300
    system_health_jobs_stalled_unhealthy: int = 1
    system_health_events_pending_degraded: int = 50
    system_health_events_failed_degraded: int = 1
    system_health_events_oldest_pending_degraded_seconds: int = 300
    system_health_events_stalled_unhealthy: int = 1

    # ELFIS Security / Observability / Reliability V1
    elfis_environment: str = ""  # vide → app_env
    elfis_security_headers_enabled: bool = True
    elfis_csp_enabled: bool = True
    elfis_csp_report_only: bool = True
    elfis_hsts_enabled: bool = False
    elfis_allowed_origins: str = ""
    elfis_allow_credentials: bool = True
    elfis_allowed_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD"
    elfis_allowed_headers: str = "Authorization,Content-Type,X-Organization-Id,X-Requested-With,X-Request-Id,X-Correlation-Id"
    elfis_jwt_issuer: str = ""
    elfis_jwt_audience: str = ""
    elfis_jwt_clock_skew_seconds: int = 30
    elfis_jwt_enforce_issuer_audience: bool = False
    elfis_rate_limit_enabled: bool = True
    elfis_rate_limit_backend: str = "memory"
    elfis_rate_limit_default_per_minute: int = 120
    elfis_rate_limit_auth_per_minute: int = 10
    elfis_rate_limit_upload_per_minute: int = 20
    elfis_rate_limit_ai_per_minute: int = 30
    elfis_rate_limit_search_per_minute: int = 120
    elfis_rate_limit_email_per_minute: int = 30
    elfis_rate_limit_billing_per_minute: int = 60
    elfis_rate_limit_admin_per_minute: int = 120
    elfis_rate_limit_webhook_per_minute: int = 300
    elfis_max_json_body_bytes: int = 1_048_576
    elfis_max_email_body_bytes: int = 262_144
    elfis_max_admin_reason_length: int = 1000
    elfis_max_metadata_json_bytes: int = 65_536
    elfis_log_level: str = "INFO"
    elfis_log_format: str = "json"
    elfis_log_include_request_body: bool = False
    elfis_log_include_response_body: bool = False
    elfis_metrics_enabled: bool = True
    elfis_metrics_require_auth: bool = True
    elfis_metrics_token: str = ""
    elfis_cleanup_enabled: bool = False
    elfis_cleanup_dry_run: bool = True
    elfis_cleanup_batch_size: int = 500
    elfis_stale_job_seconds: int = 1800
    elfis_stale_event_seconds: int = 1800
    elfis_retention_admin_audit_days: int = 730
    elfis_retention_billing_events_days: int = 730
    elfis_retention_job_attempts_days: int = 180
    elfis_retention_event_attempts_days: int = 180
    elfis_retention_notifications_days: int = 365
    elfis_retention_ai_usage_days: int = 730
    elfis_retention_document_extractions_days: int = 365
    elfis_retention_document_business_validations_days: int = 365
    elfis_retention_product_packages_days: int = 365
    elfis_retention_incidents_days: int = 730
    elfis_retention_delivery_history_days: int = 365
    elfis_retention_security_events_days: int = 365

    # Audit Engine RC2.3 étape 3 — rétention / export / recherche
    audit_retention_days: int = 365
    audit_security_retention_days: int = 730
    audit_auth_retention_days: int = 365
    audit_critical_retention_days: int = 1095
    audit_export_max_rows: int = 10_000
    audit_export_max_range_days: int = 31
    audit_export_timeout_seconds: int = 60
    audit_search_max_range_days: int = 366
    audit_archive_batch_size: int = 1_000

    @property
    def effective_platform_from(self) -> str:
        return (self.platform_email_from or self.smtp_from or "").strip()

    @property
    def effective_platform_from_name(self) -> str:
        return (self.platform_email_from_name or "ELFIS Core").strip()

    @staticmethod
    def _clean_secret(value: str) -> str:
        """Enlève guillemets / espaces / retours ligne collés depuis Render."""
        cleaned = (value or "").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()
        return cleaned.replace("\r", "").replace("\n", "").strip()

    @staticmethod
    def _normalize_database_url(url: str) -> str:
        raw = (url or "").strip()
        if raw.startswith("postgresql+psycopg://") or raw.startswith("postgresql+psycopg2://"):
            return raw
        if raw.startswith("postgresql://"):
            return "postgresql+psycopg://" + raw[len("postgresql://") :]
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://") :]
        return raw

    @staticmethod
    def _normalize_http_base_url(value: str) -> str:
        """Normalise une URL de base HTTP(S) (guillemets, https:host → https://host)."""
        cleaned = (value or "").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1].strip()
        cleaned = cleaned.replace("\r", "").replace("\n", "").strip()
        # Corrige https:host.tld (sans //) souvent collé depuis un copier-coller .env
        if cleaned.startswith("https:") and not cleaned.startswith("https://"):
            cleaned = "https://" + cleaned[len("https:") :]
        elif cleaned.startswith("http:") and not cleaned.startswith("http://"):
            cleaned = "http://" + cleaned[len("http:") :]
        return cleaned.rstrip("/")

    @model_validator(mode="after")
    def validate_production_security(self):
        self.stripe_secret_key = self._clean_secret(self.stripe_secret_key)
        self.stripe_webhook_secret = self._clean_secret(self.stripe_webhook_secret)
        self.stripe_price_pro = self.stripe_price_pro.strip()
        self.stripe_price_starter_monthly = (self.stripe_price_starter_monthly or "").strip()
        self.stripe_price_professional_monthly = (self.stripe_price_professional_monthly or "").strip()
        self.stripe_price_enterprise_monthly = (self.stripe_price_enterprise_monthly or "").strip()
        # Compat : STARTER_MONTHLY vide → réutilise STRIPE_PRICE_PRO
        if not self.stripe_price_starter_monthly and self.stripe_price_pro:
            self.stripe_price_starter_monthly = self.stripe_price_pro
        self.brevo_api_key = self._clean_secret(self.brevo_api_key)
        self.supabase_service_role_key = self._clean_secret(self.supabase_service_role_key)
        self.supabase_url = self._normalize_http_base_url(self.supabase_url or "")
        self.supabase_storage_service_role_key = self._clean_secret(
            getattr(self, "supabase_storage_service_role_key", "") or ""
        )
        self.supabase_storage_url = self._normalize_http_base_url(
            getattr(self, "supabase_storage_url", "") or ""
        )
        self.smtp_user = self._clean_secret(self.smtp_user)
        self.smtp_password = self._clean_secret(self.smtp_password)
        self.smtp_host = (self.smtp_host or "").strip()
        self.platform_email_from = (self.platform_email_from or "").strip()
        self.smtp_from = (self.smtp_from or "").strip()
        self.frontend_url = self.frontend_url.strip() or "http://localhost:5173"
        self.database_url = self._normalize_database_url(self.database_url)
        if not (self.elfis_ai_default_model or "").strip():
            self.elfis_ai_default_model = self.openai_chat_model or "gpt-4o-mini"
        if not (self.elfis_ai_fast_model or "").strip():
            self.elfis_ai_fast_model = self.elfis_ai_default_model
        if not (self.elfis_ai_complex_model or "").strip():
            self.elfis_ai_complex_model = self.elfis_ai_default_model
        # Aligné sur ELFIS_ENVIRONMENT || APP_ENV (évite import circulaire security_config).
        env_raw = (
            getattr(self, "elfis_environment", None) or self.app_env or "development"
        )
        env_name = str(env_raw).strip().lower()
        if env_name in {"prod", "production"}:
            env_name = "production"
        if env_name != "production":
            return self
        if self.jwt_secret == "comptapilot-elfis-dev-secret-change-me" or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET doit contenir au moins 32 caractères en production")
        if not self.cors_origins.strip() or self.cors_origins.strip() == "*":
            raise ValueError("CORS_ORIGINS doit lister les domaines autorisés en production")
        if not self.firebase_web_api_key or not self.firebase_project_id:
            raise ValueError("Firebase doit être configuré en production")
        if (self.database_url or "").startswith("sqlite"):
            raise ValueError("DATABASE_URL PostgreSQL requis en production (SQLite interdit)")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        raw = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return raw or ["*"]

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def platform_admin_email_set(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.platform_admin_emails.split(",")
            if email.strip()
        }


settings = Settings()
