"""Tests routes Document Intelligence + analyze."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.ai.ai_types import DocumentAnalysisStatus
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.document_intelligence import document_models  # noqa: F401
from app.document_intelligence.document_models import ElfisDocumentTextExtraction
from app.document_intelligence.document_types import ExtractionStatus
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.routers import ai as ai_router
from app.routers import document_intelligence as di_router


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org"))
    db.add(Organization(id=2, name="Org2"))
    user = User(id=1, email="u@e.c", first_name="U", last_name="E", password_hash="x")
    admin = User(
        id=99,
        email="admin@e.c",
        first_name="A",
        last_name="D",
        password_hash="x",
        is_platform_admin=True,
    )
    db.add_all([user, admin])
    db.add(
        VaultDocument(
            id="vd-route",
            organization_id=1,
            document_type="other",
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
    return db, Session, user, admin


def _app(Session, user, *, org_id=1, platform_admin=None):
    app = FastAPI()
    app.include_router(di_router.router, prefix="/api")
    app.include_router(di_router.platform_router, prefix="/api")
    app.include_router(ai_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    def _auth():
        return AuthContext(user=user, organization_id=org_id, role="owner", permissions=["*"])

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = lambda: None
    if platform_admin is not None:
        app.dependency_overrides[require_platform_admin] = lambda: platform_admin
    return TestClient(app)


def test_extract_text_returns_202():
    db, Session, user, _ = _setup()
    client = _app(Session, user)
    r = client.post("/api/documents/vd-route/extract-text")
    assert r.status_code == 202
    body = r.json()
    assert "extraction_id" in body
    assert body["status"] in ("pending", "processing", "completed")
    assert "job_id" in body


def test_get_extraction_and_tenant():
    db, Session, user, _ = _setup()
    row = ElfisDocumentTextExtraction(
        id=str(uuid.uuid4()),
        extraction_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-route",
        document_version=1,
        extractor_name="pdf_text",
        status=ExtractionStatus.COMPLETED,
        text_content="secret full text should not appear",
        text_length=10,
        metadata_json={},
        warnings=[],
        errors=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

    client = _app(Session, user, org_id=1)
    r = client.get("/api/documents/vd-route/text-extraction")
    assert r.status_code == 200
    data = r.json()
    assert data["extraction_id"] == row.extraction_id
    assert "text_content" not in data
    assert data["text_length"] == 10

    client2 = _app(Session, user, org_id=2)
    r2 = client2.get("/api/documents/vd-route/text-extraction")
    assert r2.status_code == 404


def test_analyze_without_text_enqueues_extraction():
    db, Session, user, _ = _setup()
    client = _app(Session, user)
    r = client.post("/api/ai/documents/vd-route/analyze", json={})
    assert r.status_code == 202
    body = r.json()
    assert body["current_stage"] == "text_extraction"
    assert body["status"] == DocumentAnalysisStatus.PENDING
    jobs = db.query(ElfisJob).filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT).all()
    assert jobs


def test_analyze_with_existing_extraction_uses_it():
    db, Session, user, _ = _setup()
    row = ElfisDocumentTextExtraction(
        id=str(uuid.uuid4()),
        extraction_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-route",
        document_version=1,
        extractor_name="pdf_text",
        status=ExtractionStatus.COMPLETED,
        text_content="Facture Total TVA montant 100",
        text_length=30,
        requires_ocr=False,
        metadata_json={},
        warnings=[],
        errors=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

    client = _app(Session, user)
    r = client.post("/api/ai/documents/vd-route/analyze", json={})
    assert r.status_code == 202
    body = r.json()
    assert body["current_stage"] == "classification"
    jobs = (
        db.query(ElfisJob)
        .filter(ElfisJob.job_name == JobNames.VAULT_DOCUMENT_AI_CLASSIFICATION)
        .all()
    )
    assert jobs
    assert jobs[0].payload.get("extraction_id") == row.extraction_id
    assert "extracted_text" not in (jobs[0].payload or {})


def test_analyze_requires_ocr_awaiting_ocr():
    db, Session, user, _ = _setup()
    row = ElfisDocumentTextExtraction(
        id=str(uuid.uuid4()),
        extraction_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-route",
        document_version=1,
        extractor_name="pdf_text",
        status=ExtractionStatus.REQUIRES_OCR,
        text_content="",
        text_length=0,
        requires_ocr=True,
        metadata_json={},
        warnings=[],
        errors=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

    client = _app(Session, user)
    r = client.post("/api/ai/documents/vd-route/analyze", json={})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == DocumentAnalysisStatus.BLOCKED
    assert body["current_stage"] == "awaiting_ocr"


def test_platform_extractions_admin_only():
    db, Session, user, admin = _setup()
    row = ElfisDocumentTextExtraction(
        id=str(uuid.uuid4()),
        extraction_id=str(uuid.uuid4()),
        organization_id=1,
        vault_document_id="vd-route",
        document_version=1,
        extractor_name="pdf_text",
        status=ExtractionStatus.COMPLETED,
        text_length=5,
        text_content="preview source",
        metadata_json={},
        warnings=[],
        errors=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

    denied = _app(Session, user)
    r = denied.get("/api/platform/document-extractions")
    assert r.status_code in (401, 403)

    ok = _app(Session, admin, platform_admin=admin)
    r2 = ok.get("/api/platform/document-extractions")
    assert r2.status_code == 200
    assert r2.json()["total"] >= 1
    detail = ok.get(f"/api/platform/document-extractions/{row.extraction_id}")
    assert detail.status_code == 200
    assert "preview" in detail.json()
    assert detail.json().get("text_content") is None
