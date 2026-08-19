"""Tests routes Accounting."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.accounting import accounting_models  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.document_intelligence import document_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.routers import accounting as accounting_router
from tests.accounting import seed_analysis


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
    user = User(id=1, email="u@e.c", first_name="U", last_name="E", password_hash="x")
    admin = User(
        id=99, email="a@e.c", first_name="A", last_name="D", password_hash="x", is_platform_admin=True
    )
    db.add_all([user, admin])
    db.add(
        VaultDocument(
            id="vd-acc",
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
    bootstrap_job_handlers()
    return db, Session, user, admin


def _client(Session, user, *, platform_admin=None):
    app = FastAPI()
    app.include_router(accounting_router.router, prefix="/api")
    app.include_router(accounting_router.platform_router, prefix="/api")

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
    if platform_admin is not None:
        app.dependency_overrides[require_platform_admin] = lambda: platform_admin
    return TestClient(app)


def test_list_and_detail_and_platform():
    db, Session, user, admin = _setup()
    seed_analysis(db)
    from app.accounting.accounting_schemas import AccountingPipelineRequest
    from app.accounting.accounting_service import AccountingService

    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, user_id=1, vault_document_id="vd-acc")
    )
    client = _client(Session, user)
    listing = client.get("/api/accounting/proposals")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    detail = client.get(f"/api/accounting/proposals/{result.proposal_id}")
    assert detail.status_code == 200
    assert detail.json()["disclaimer"]
    assert "entry" in detail.json()

    denied = _client(Session, user)
    r = denied.get("/api/platform/accounting/proposals")
    assert r.status_code in (401, 403)

    ok = _client(Session, admin, platform_admin=admin)
    assert ok.get("/api/platform/accounting/proposals").status_code == 200
    assert ok.get(f"/api/platform/accounting/proposals/{result.proposal_id}").status_code == 200


def test_build_proposal_202():
    db, Session, user, _ = _setup()
    seed_analysis(db)
    client = _client(Session, user)
    r = client.post("/api/accounting/documents/vd-acc/build-proposal")
    assert r.status_code == 202
    assert "job_id" in r.json()
