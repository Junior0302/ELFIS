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
        "invoices", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
    _sqlite_add_column_if_missing(
        "company_settings", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
    _sqlite_add_column_if_missing(
        "bank_accounts", "organization_id", "organization_id INTEGER DEFAULT 0"
    )
