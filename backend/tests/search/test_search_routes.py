"""Tests routes Search."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.accounting import accounting_models  # noqa: F401
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.document_intelligence import document_models  # noqa: F401
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument
from app.routers import search as search_router
from app.search import search_models  # noqa: F401
from app.search.search_registry import bootstrap_indexers
from app.search.search_schemas import SearchIndexRequest
from app.search.search_service import SearchService
from app.search.search_types import SearchResourceTypes
from datetime import datetime


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
        id=99,
        email="a@e.c",
        first_name="A",
        last_name="D",
        password_hash="x",
        is_platform_admin=True,
    )
    db.add_all([user, admin])
    db.add(
        VaultDocument(
            id="vd-r",
            organization_id=1,
            document_type="supplier_invoice",
            original_filename="doc-test.pdf",
            document_number="INV-9",
            storage_path="p",
            mime_type="application/pdf",
            file_size=10,
            checksum_sha256="x",
            archive_status="archived",
            amount_ttc=50,
            currency="EUR",
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db.commit()
    bootstrap_indexers()
    bootstrap_job_handlers()
    SearchService(db).index_resource(
        SearchIndexRequest(
            organization_id=1,
            resource_type=SearchResourceTypes.VAULT_DOCUMENT,
            resource_id="vd-r",
        )
    )
    return db, Session, user, admin


def _app(Session, user, *, platform_admin=None):
    app = FastAPI()
    app.include_router(search_router.router, prefix="/api")
    app.include_router(search_router.platform_router, prefix="/api")

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


def test_search_route_and_suggestions():
    db, Session, user, _ = _setup()
    client = _app(Session, user)
    r = client.get("/api/search", params={"q": "INV"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    s = client.get("/api/search/suggestions", params={"q": "doc"})
    assert s.status_code == 200
    assert "suggestions" in s.json()


def test_platform_admin_only():
    db, Session, user, admin = _setup()
    denied = _app(Session, user)
    assert denied.get("/api/platform/search/documents").status_code in (401, 403)
    ok = _app(Session, admin, platform_admin=admin)
    assert ok.get("/api/platform/search/documents").status_code == 200
