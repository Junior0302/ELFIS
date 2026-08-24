"""Helpers SQLite pour tests Storage / Document Registry."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models_saas import Organization, User  # noqa: F401
from app.storage import storage_models  # noqa: F401
from app.audit import audit_models  # noqa: F401


def make_storage_db():
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
            storage_models.ElfisStorageObject.__table__,
            storage_models.ElfisDocumentRecord.__table__,
            storage_models.ElfisDocumentLink.__table__,
            storage_models.ElfisDocumentVersion.__table__,
            storage_models.ElfisDocumentLegalHold.__table__,
            storage_models.ElfisDocumentTombstone.__table__,
            storage_models.ElfisStorageMigration.__table__,
            audit_models.ElfisAuditEvent.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_org_user(db, *, email: str = "storage@test.local"):
    org = Organization(name="Org Storage")
    db.add(org)
    db.flush()
    user = User(
        first_name="S",
        last_name="T",
        email=email,
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user


def tmp_storage_root(tmp_path: Path) -> Path:
    root = tmp_path / "elfis_objects"
    root.mkdir(parents=True, exist_ok=True)
    return root
