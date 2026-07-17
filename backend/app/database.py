from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
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
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        names = {r[1] for r in rows}
        if column not in names:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db() -> None:
    from app import models  # noqa: F401
    from app import models_saas  # noqa: F401

    Base.metadata.create_all(bind=engine)
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
    if settings.database_url.startswith("sqlite"):
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
    _sqlite_add_column_if_missing("organizations", "address", "address TEXT DEFAULT ''")
    _sqlite_add_column_if_missing(
        "sales_documents", "customer_email", "customer_email VARCHAR(255) DEFAULT ''"
    )
    _sqlite_add_column_if_missing(
        "organization_members", "invited_by", "invited_by INTEGER"
    )
    _sqlite_add_column_if_missing(
        "organization_members",
        "updated_at",
        "updated_at DATETIME",
    )
