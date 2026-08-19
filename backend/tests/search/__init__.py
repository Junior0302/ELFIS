"""Helpers tests Search Engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.accounting import accounting_models  # noqa: F401
from app.database import Base
from app.document_intelligence import document_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.search import search_models  # noqa: F401
from app.search.search_registry import bootstrap_indexers, default_indexer_registry


def setup_search_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org1"))
    db.add(Organization(id=2, name="Org2"))
    db.add(User(id=1, email="a@b.c", first_name="A", last_name="B", password_hash="x"))
    db.add(
        VaultDocument(
            id="vd-1",
            organization_id=1,
            document_type="supplier_invoice",
            document_number="F2026-001",
            original_filename="facture-acme.pdf",
            storage_path="org/1/f.pdf",
            mime_type="application/pdf",
            file_size=1000,
            checksum_sha256="abc",
            archive_status="archived",
            amount_ttc=120,
            currency="EUR",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db.add(
        VaultDocument(
            id="vd-2",
            organization_id=2,
            document_type="supplier_invoice",
            original_filename="other.pdf",
            storage_path="org/2/o.pdf",
            mime_type="application/pdf",
            file_size=100,
            checksum_sha256="def",
            archive_status="archived",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db.commit()
    default_indexer_registry.clear()
    bootstrap_indexers()
    bootstrap_job_handlers()
    return db, Session, engine
