"""Helpers tests classification."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit import audit_models  # noqa: F401
from app.database import Base
from app.document_processing import models as dp_models  # noqa: F401
from app.document_processing.classification import models as cls_models  # noqa: F401
from app.models_saas import Organization, User  # noqa: F401
from app.storage import storage_models  # noqa: F401
from app.storage.document_registry_service import DocumentRegistryService
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_context import StorageContext
from app.document_processing.step_registry import reset_pipeline_registry_for_tests


def make_classification_db():
    reset_pipeline_registry_for_tests()
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
            audit_models.ElfisAuditEvent.__table__,
            dp_models.ElfisDocumentProcessingJob.__table__,
            dp_models.ElfisDocumentProcessingStep.__table__,
            dp_models.ElfisDocumentProcessingAttempt.__table__,
            cls_models.ElfisDocumentClassification.__table__,
        ],
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def factory():
        return Session()

    return factory, engine


def seed_org_user(db, *, email: str = "cls@test.local"):
    org = Organization(name="Org CLS")
    db.add(org)
    db.flush()
    user = User(
        first_name="C",
        last_name="L",
        email=email,
        password_hash="x",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(org)
    db.refresh(user)
    return org, user


def seed_document(db, tmp_path: Path, org, user, *, filename: str = "probe.txt", content: bytes = b"x"):
    svc = DocumentRegistryService(
        db,
        context=StorageContext(provider=LocalStorageProvider(root=tmp_path), namespace="test"),
    )
    return svc.create_from_upload(
        organization_id=org.id,
        filename=filename,
        content=content,
        declared_mime="application/pdf" if filename.endswith(".pdf") else "text/plain",
        owner_user_id=user.id,
        title=filename,
    )
