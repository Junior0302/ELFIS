"""Helpers Accounting Pipeline tests."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.accounting import accounting_models  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.ai.ai_models import ElfisDocumentAnalysis
from app.ai.ai_types import DocumentAnalysisStatus
from app.database import Base
from app.document_intelligence import document_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument


def setup_acc_db():
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
            id="vd-acc",
            organization_id=1,
            document_type="supplier_invoice",
            original_filename="f.pdf",
            storage_path="o/f.pdf",
            mime_type="application/pdf",
            file_size=100,
            checksum_sha256="x",
            archive_status="archived",
            version=1,
        )
    )
    db.commit()
    bootstrap_job_handlers()
    return db, Session, engine


def seed_analysis(
    db,
    *,
    org_id: int = 1,
    vault_id: str = "vd-acc",
    doc_type: str = "supplier_invoice",
    ht: float = 100.0,
    tva: float = 20.0,
    ttc: float = 120.0,
    confidence: float = 0.95,
    number: str = "F2026-001",
):
    analysis = ElfisDocumentAnalysis(
        id=str(uuid.uuid4()),
        analysis_id=str(uuid.uuid4()),
        organization_id=org_id,
        vault_document_id=vault_id,
        document_version=1,
        document_type=doc_type,
        status=DocumentAnalysisStatus.COMPLETED,
        confidence=confidence,
        requires_review=False,
        current_stage="completed",
        extraction={
            "compatible_extraction": {
                "supplier": "ACME SARL",
                "customer_name": "Client SA",
                "invoice_number": number,
                "invoice_date": "15/01/2026",
                "amount_ht": ht,
                "amount_tva": tva,
                "amount_ttc": ttc,
                "vat_rate": 20.0,
                "document_type": "facture",
                "currency": "EUR",
                "confidence_score": confidence,
            }
        },
        quality={"status": "valid"},
        ai_execution_ids=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db.add(analysis)
    db.commit()
    return analysis
