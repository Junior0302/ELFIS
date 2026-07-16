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
        "trial_start": "trial_start DATETIME",
        "trial_end": "trial_end DATETIME",
        "current_period_start": "current_period_start DATETIME",
        "current_period_end": "current_period_end DATETIME",
        "past_due_since": "past_due_since DATETIME",
        "cancel_at_period_end": "cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0",
        "canceled_at": "canceled_at DATETIME",
    }
    for column, ddl in subscription_columns.items():
        _sqlite_add_column_if_missing("subscriptions", column, ddl)
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
