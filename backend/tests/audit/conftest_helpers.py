"""Helpers SQLite pour tests Audit Engine."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit import audit_models  # noqa: F401
from app.database import Base
from app.models_saas import Organization, User  # noqa: F401


def make_audit_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            Organization.__table__,
            audit_models.ElfisAuditEvent.__table__,
            audit_models.ElfisAuditEventArchive.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_user(db, *, email: str = "audit@test.local") -> User:
    u = User(
        first_name="A",
        last_name="B",
        email=email,
        password_hash="x",
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
