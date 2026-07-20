"""Tests routes AI documents + plateforme."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models, bootstrap_ai_tasks  # noqa: F401
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.events import event_models  # noqa: F401
from app.jobs import job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.routers import ai as ai_router
from app.routers import platform as platform_router


def _base():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org"))
    db.add(Organization(id=2, name="Other"))
    user = User(
        id=1,
        email="u@example.com",
        first_name="U",
        last_name="S",
        password_hash="x",
        is_platform_admin=True,
    )
    other = User(
        id=2,
        email="o@example.com",
        first_name="O",
        last_name="T",
        password_hash="x",
        is_platform_admin=False,
    )
    db.add_all([user, other])
    db.add(
        VaultDocument(
            id="vd-1",
            organization_id=1,
            document_type="supplier_invoice",
            original_filename="f.pdf",
            storage_path="p",
            mime_type="application/pdf",
            file_size=10,
            checksum_sha256="x",
            archive_status="archived",
            version=1,
        )
    )
    db.commit()
    bootstrap_ai_tasks()
    return db, Session, user, other


def test_analyze_202_and_reuse_and_missing():
    db, Session, user, _ = _base()
    app = FastAPI()
    app.include_router(ai_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user=user, organization_id=1, role="owner", permissions=["*"]
    )
    app.dependency_overrides[require_active_subscription] = lambda: None

    client = TestClient(app)
    r = client.post(
        "/api/ai/documents/vd-1/analyze",
        json={"extracted_text": "Facture test HT 10 TVA 2 TTC 12", "filename": "f.pdf"},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["analysis_id"]
    assert body["status"] in ("classifying", "pending", "blocked")
    assert body["reused_existing_analysis"] is False

    r2 = client.post(
        "/api/ai/documents/vd-1/analyze",
        json={"extracted_text": "Facture test HT 10 TVA 2 TTC 12"},
    )
    assert r2.status_code == 202
    assert r2.json()["reused_existing_analysis"] is True
    assert r2.json()["analysis_id"] == body["analysis_id"]

    missing = client.post("/api/ai/documents/nope/analyze", json={"extracted_text": "x" * 50})
    assert missing.status_code == 404


def test_tenant_isolation_get_analysis():
    db, Session, user, _ = _base()
    from app.ai.document_analysis_service import DocumentAnalysisService

    DocumentAnalysisService(db).start_analysis(
        organization_id=1,
        user_id=1,
        vault_document_id="vd-1",
        extracted_text="Facture isolation test contenu suffisant",
    )

    app = FastAPI()
    app.include_router(ai_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_active_subscription] = lambda: None
    # autre org
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user=user, organization_id=2, role="owner", permissions=["*"]
    )
    client = TestClient(app)
    assert client.get("/api/ai/documents/vd-1/analysis").status_code == 404


def test_platform_admin_ok_user_forbidden():
    db, Session, admin, other = _base()
    app = FastAPI()
    app.include_router(platform_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_platform_admin] = lambda: admin
    client = TestClient(app)
    assert client.get("/api/platform/ai/executions").status_code == 200
    assert client.get("/api/platform/ai/usage").status_code == 200
    assert client.get("/api/platform/ai/document-analyses").status_code == 200

    # Simuler refus plateforme
    from fastapi import HTTPException

    def _deny():
        raise HTTPException(403, detail="platform_admin_required")

    app.dependency_overrides[require_platform_admin] = _deny
    assert client.get("/api/platform/ai/executions").status_code == 403
