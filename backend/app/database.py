from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs: dict = {"connect_args": connect_args}
if not _is_sqlite:
    _engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": int(getattr(settings, "database_pool_size", 5) or 5),
            "max_overflow": int(getattr(settings, "database_max_overflow", 10) or 10),
            "pool_recycle": int(getattr(settings, "database_pool_recycle", 1800) or 1800),
            "pool_timeout": int(getattr(settings, "database_pool_timeout", 30) or 30),
        }
    )
engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_add_column_if_missing(table: str, column: str, ddl: str) -> None:
    """Migrations légères SQLite uniquement — jamais de PRAGMA sur PostgreSQL.

    Utilise le dialecte du moteur lié (pas seulement settings.database_url), car les
    tests peuvent monkeypatcher settings tout en laissant engine sur un autre backend.
    """
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        names = {r[1] for r in rows}
        if column not in names:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db() -> None:
    from app import models  # noqa: F401
    from app import models_saas  # noqa: F401
    from app import models_vault  # noqa: F401
    from app import models_fiscal  # noqa: F401
    from app.events import event_models  # noqa: F401
    from app.notifications import notification_models  # noqa: F401
    from app.jobs import job_models  # noqa: F401
    from app.ai import ai_models  # noqa: F401
    from app.document_intelligence import document_models  # noqa: F401
    from app.accounting import accounting_models  # noqa: F401
    from app.search import search_models  # noqa: F401
    from app.billing import billing_models  # noqa: F401
    from app.platform_admin import admin_models  # noqa: F401
    from app.security import security_models  # noqa: F401
    from app.iam import iam_models  # noqa: F401
    from app.audit import audit_models  # noqa: F401
    from app.storage import storage_models  # noqa: F401
    from app.document_processing import models as document_processing_models  # noqa: F401
    from app.document_processing.classification import models as document_classification_models  # noqa: F401
    from app.document_processing.ocr import models as document_ocr_models  # noqa: F401
    from app.document_processing.extraction import models as document_processing_extraction_models  # noqa: F401
    from app.document_processing.validation import models as document_validation_models  # noqa: F401
    # Intake avant extraction Migration Center (FK document_intake_item_id).
    from app.document_intake import models as document_intake_models  # noqa: F401
    from app.document_extraction import models as document_extraction_models  # noqa: F401
    from app.product_integrations import models as product_integrations_models  # noqa: F401
    from app.migration_center import models as migration_center_models  # noqa: F401
    from app.banking import banking_models  # noqa: F401
    from app.ai_assistant import models as _ai_assistant_models  # noqa: F401
    from app.workspace_provisioning import models as workspace_provisioning_models  # noqa: F401
    from app.decision_center import models as decision_center_models  # noqa: F401
    from app.sales_crm import models as sales_crm_models  # noqa: F401
    from app.sales_proposals import models as sales_proposals_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _sqlite_add_column_if_missing(
        "sales_opportunities", "stage_entered_at", "stage_entered_at DATETIME"
    )
    for column, ddl in {
        "calculated_amount": "calculated_amount NUMERIC(14, 2)",
        "final_amount": "final_amount NUMERIC(14, 2)",
        "amount_mode": "amount_mode VARCHAR(32) DEFAULT 'calculated'",
        "amount_difference": "amount_difference NUMERIC(14, 2)",
        "amount_override_reason": "amount_override_reason VARCHAR(64)",
        "amount_override_comment": "amount_override_comment TEXT",
    }.items():
        _sqlite_add_column_if_missing("sales_opportunities", column, ddl)
    _sqlite_add_column_if_missing("users", "firebase_uid", "firebase_uid VARCHAR(128) DEFAULT ''")
    _sqlite_add_column_if_missing(
        "users", "is_platform_admin", "is_platform_admin BOOLEAN NOT NULL DEFAULT 0"
    )
    subscription_columns = {
        "stripe_customer_id": "stripe_customer_id VARCHAR(255)",
        "stripe_subscription_id": "stripe_subscription_id VARCHAR(255)",
        "stripe_price_id": "stripe_price_id VARCHAR(255)",
        "stripe_product_id": "stripe_product_id VARCHAR(255)",
        "stripe_checkout_session_id": "stripe_checkout_session_id VARCHAR(255)",
        "trial_start": "trial_start DATETIME",
        "trial_end": "trial_end DATETIME",
        "trial_used": "trial_used BOOLEAN NOT NULL DEFAULT 0",
        "trial_used_at": "trial_used_at DATETIME",
        "trial_source_subscription_id": "trial_source_subscription_id VARCHAR(255)",
        "trial_eligibility_status": "trial_eligibility_status VARCHAR(32) DEFAULT 'eligible'",
        "current_period_start": "current_period_start DATETIME",
        "current_period_end": "current_period_end DATETIME",
        "past_due_since": "past_due_since DATETIME",
        "cancel_at_period_end": "cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0",
        "cancel_requested_at": "cancel_requested_at DATETIME",
        "canceled_at": "canceled_at DATETIME",
        "access_ends_at": "access_ends_at DATETIME",
        "payment_failure_count": "payment_failure_count INTEGER DEFAULT 0",
        "last_payment_failure_at": "last_payment_failure_at DATETIME",
        "last_payment_succeeded_at": "last_payment_succeeded_at DATETIME",
        "admin_revoked_at": "admin_revoked_at DATETIME",
        "admin_revoked_by": "admin_revoked_by INTEGER",
        "admin_revoked_reason_public": "admin_revoked_reason_public TEXT DEFAULT ''",
        "admin_revoked_reason_internal": "admin_revoked_reason_internal TEXT DEFAULT ''",
    }
    for column, ddl in subscription_columns.items():
        _sqlite_add_column_if_missing("subscriptions", column, ddl)
    webhook_columns = {
        "stripe_object_id": "stripe_object_id VARCHAR(255) DEFAULT ''",
        "status": "status VARCHAR(32) DEFAULT 'processed'",
        "attempt_count": "attempt_count INTEGER DEFAULT 1",
        "payload_hash": "payload_hash VARCHAR(64) DEFAULT ''",
        "last_error": "last_error TEXT DEFAULT ''",
        "received_at": "received_at DATETIME",
    }
    for column, ddl in webhook_columns.items():
        _sqlite_add_column_if_missing("stripe_webhook_events", column, ddl)
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_subscriptions_stripe_customer_id "
                    "ON subscriptions(stripe_customer_id) "
                    "WHERE stripe_customer_id IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_subscriptions_stripe_subscription_id "
                    "ON subscriptions(stripe_subscription_id) "
                    "WHERE stripe_subscription_id IS NOT NULL"
                )
            )
    _sqlite_add_column_if_missing(
        "invoices", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
    _sqlite_add_column_if_missing(
        "company_settings", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
    _sqlite_add_column_if_missing(
        "bank_accounts", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
    # Banking Platform V1
    for column, ddl in {
        "connection_id": "connection_id INTEGER",
        "provider": "provider VARCHAR(32) DEFAULT 'manual'",
        "external_id": "external_id VARCHAR(128) DEFAULT ''",
        "account_type": "account_type VARCHAR(32) DEFAULT 'other'",
        "available_balance": "available_balance FLOAT",
        "balance_updated_at": "balance_updated_at DATETIME",
    }.items():
        _sqlite_add_column_if_missing("bank_accounts", column, ddl)
    for column, ddl in {
        "status": "status VARCHAR(16) DEFAULT 'booked'",
        "source": "source VARCHAR(32) DEFAULT 'manual'",
        "value_date": "value_date VARCHAR(32)",
        "counterparty_name": "counterparty_name VARCHAR(255)",
        "reference": "reference VARCHAR(128)",
    }.items():
        _sqlite_add_column_if_missing("bank_transactions", column, ddl)
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_bank_transactions_account_external_id "
                    "ON bank_transactions(account_id, external_id) "
                    "WHERE trim(COALESCE(external_id, '')) <> ''"
                )
            )
    _sqlite_add_column_if_missing("organizations", "address", "address TEXT DEFAULT ''")
    for column, ddl in {
        "postal_code": "postal_code VARCHAR(32) DEFAULT ''",
        "city": "city VARCHAR(128) DEFAULT ''",
        "phone": "phone VARCHAR(64) DEFAULT ''",
        "email": "email VARCHAR(255) DEFAULT ''",
        "website": "website VARCHAR(255) DEFAULT ''",
        "iban": "iban VARCHAR(64) DEFAULT ''",
        "bic": "bic VARCHAR(32) DEFAULT ''",
        "share_capital": "share_capital VARCHAR(64) DEFAULT ''",
        "legal_form": "legal_form VARCHAR(64) DEFAULT ''",
        "legal_mentions": "legal_mentions TEXT DEFAULT ''",
        "primary_color": "primary_color VARCHAR(16) DEFAULT '#0B3D2E'",
        "secondary_color": "secondary_color VARCHAR(16) DEFAULT '#E7F2EC'",
        "logo": "logo VARCHAR(512) DEFAULT ''",
        "documents_show_logo": "documents_show_logo BOOLEAN",
        "industry_other": "industry_other VARCHAR(100) DEFAULT ''",
        "vat_status": "vat_status VARCHAR(32) DEFAULT ''",
        "locale": "locale VARCHAR(16) DEFAULT ''",
        "timezone": "timezone VARCHAR(64) DEFAULT ''",
        "setup_completed": "setup_completed BOOLEAN NOT NULL DEFAULT 0",
        "setup_completed_at": "setup_completed_at DATETIME",
        "setup_version": "setup_version INTEGER DEFAULT 0",
    }.items():
        _sqlite_add_column_if_missing("organizations", column, ddl)
    _sqlite_add_column_if_missing(
        "sales_documents", "customer_email", "customer_email VARCHAR(255) DEFAULT ''"
    )
    _sqlite_add_column_if_missing(
        "sales_documents", "branding_json", "branding_json TEXT DEFAULT '{}'"
    )
    _sqlite_add_column_if_missing(
        "organization_members", "invited_by", "invited_by INTEGER"
    )
    _sqlite_add_column_if_missing(
        "organization_members",
        "updated_at",
        "updated_at DATETIME",
    )
    _sqlite_add_column_if_missing(
        "organization_members",
        "accounting_hub_visited_at",
        "accounting_hub_visited_at DATETIME",
    )
    email_log_columns = {
        "document_type": "document_type VARCHAR(32) DEFAULT ''",
        "sent_by_user_id": "sent_by_user_id INTEGER",
        "recipient_email": "recipient_email VARCHAR(255) DEFAULT ''",
        "cc_email": "cc_email VARCHAR(255) DEFAULT ''",
        "bcc_email": "bcc_email VARCHAR(255) DEFAULT ''",
        "sender_name": "sender_name VARCHAR(255) DEFAULT ''",
        "sender_email": "sender_email VARCHAR(255) DEFAULT ''",
        "reply_to_email": "reply_to_email VARCHAR(255) DEFAULT ''",
        "provider": "provider VARCHAR(32) DEFAULT ''",
        "provider_message_id": "provider_message_id VARCHAR(255) DEFAULT ''",
        "email_connection_id": "email_connection_id INTEGER",
        "idempotency_key": "idempotency_key VARCHAR(128) DEFAULT ''",
        "error_code": "error_code VARCHAR(64) DEFAULT ''",
        "delivered_at": "delivered_at DATETIME",
        "opened_at": "opened_at DATETIME",
        "bounced_at": "bounced_at DATETIME",
        "created_at": "created_at DATETIME",
        "updated_at": "updated_at DATETIME",
    }
    for column, ddl in email_log_columns.items():
        _sqlite_add_column_if_missing("document_email_logs", column, ddl)

    _sqlite_add_column_if_missing(
        "invoices", "supplier_contact_id", "supplier_contact_id INTEGER"
    )
    _sqlite_add_column_if_missing(
        "invoices", "customer_contact_id", "customer_contact_id INTEGER"
    )
    for column, ddl in {
        "platform_status": "platform_status VARCHAR(32) DEFAULT 'active'",
        "platform_suspended_at": "platform_suspended_at DATETIME",
        "platform_suspended_by": "platform_suspended_by INTEGER",
        "platform_suspend_reason": "platform_suspend_reason TEXT DEFAULT ''",
    }.items():
        _sqlite_add_column_if_missing("organizations", column, ddl)

    # Idempotence Delivery : index unique org+clé (clés non vides uniquement).
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_email_org_idempotency "
                    "ON document_email_logs(organization_id, idempotency_key) "
                    "WHERE idempotency_key IS NOT NULL AND idempotency_key != ''"
                )
            )
        else:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_email_org_idempotency "
                    "ON document_email_logs(organization_id, idempotency_key) "
                    "WHERE idempotency_key IS NOT NULL AND idempotency_key <> ''"
                )
            )

    # SalesPilot S1.6.1 bridge columns (SQLite persistent DB)
    for column, ddl in {
        "conversion_status": "conversion_status VARCHAR(32) DEFAULT 'not_ready'",
        "conversion_started_at": "conversion_started_at DATETIME",
        "conversion_completed_at": "conversion_completed_at DATETIME",
        "conversion_error_code": "conversion_error_code VARCHAR(64)",
        "conversion_idempotency_key": "conversion_idempotency_key VARCHAR(128)",
        "linked_customer_id": "linked_customer_id INTEGER",
        "linked_invoice_id": "linked_invoice_id INTEGER",
    }.items():
        _sqlite_add_column_if_missing("sales_commercial_proposals", column, ddl)
    _sqlite_add_column_if_missing(
        "sales_companies", "linked_customer_id", "linked_customer_id INTEGER"
    )
    for column, ddl in {
        "source_type": "source_type VARCHAR(64)",
        "source_id": "source_id VARCHAR(64)",
        "source_version_id": "source_version_id VARCHAR(64)",
        "source_number": "source_number VARCHAR(64)",
    }.items():
        _sqlite_add_column_if_missing("sales_documents", column, ddl)

    # Decision Center — colonnes d’exécution (SQLite persistant)
    for column, ddl in {
        "execution_status": "execution_status VARCHAR(32) DEFAULT 'idle'",
        "execution_started_at": "execution_started_at DATETIME",
        "execution_completed_at": "execution_completed_at DATETIME",
        "execution_failed_at": "execution_failed_at DATETIME",
        "last_execution_error_code": "last_execution_error_code VARCHAR(64)",
        "last_execution_error_message": "last_execution_error_message TEXT",
        "last_action_type": "last_action_type VARCHAR(64)",
        "last_action_by_user_id": "last_action_by_user_id INTEGER",
        "execution_attempts": "execution_attempts INTEGER DEFAULT 0",
        "last_source_refresh_at": "last_source_refresh_at DATETIME",
        "started_at": "started_at DATETIME",
        "started_by_user_id": "started_by_user_id INTEGER",
        "last_activity_at": "last_activity_at DATETIME",
    }.items():
        _sqlite_add_column_if_missing("elfis_decision_items", column, ddl)
