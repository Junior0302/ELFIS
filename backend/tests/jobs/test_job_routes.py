"""Tests routes jobs utilisateur / plateforme."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription, require_platform_admin
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.jobs.job_schemas import JobRequest
from app.jobs.job_service import JobService
from app.jobs.job_types import JobNames, JobStatus
from app.models_saas import Organization, User
from app.routers import jobs as jobs_router
from app.routers import platform as platform_router


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    org = Organization(id=1, name="Org")
    org2 = Organization(id=2, name="Other")
    user = User(
        id=10,
        email="u@example.com",
        first_name="U",
        last_name="Ser",
        password_hash="x",
        is_platform_admin=True,
    )
    user2 = User(
        id=11,
        email="o@example.com",
        first_name="O",
        last_name="Ther",
        password_hash="x",
    )
    db.add_all([org, org2, user, user2])
    db.commit()
    bootstrap_job_handlers()
    return db, Session, user, user2


def test_user_get_filtered_and_tenant_isolation():
    db, Session, user, user2 = _setup()
    svc = JobService(db)
    mine = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            organization_id=1,
            user_id=10,
            payload={"message": "private"},
        )
    )
    other = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            organization_id=2,
            user_id=11,
            payload={"message": "other"},
        )
    )

    app = FastAPI()
    app.include_router(jobs_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    def _auth():
        return AuthContext(user=user, organization_id=1, role="owner", permissions=["*"])

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_auth_context] = _auth
    app.dependency_overrides[require_active_subscription] = lambda: None

    client = TestClient(app)
    ok = client.get(f"/api/jobs/{mine.job_id}")
    assert ok.status_code == 200
    body = ok.json()
    assert body["job_id"] == mine.job_id
    assert "payload" not in body
    assert "result" not in body
    assert "last_error" not in body

    denied = client.get(f"/api/jobs/{other.job_id}")
    assert denied.status_code == 404


def test_platform_detail_filtered_and_retry_cancel():
    db, Session, user, _ = _setup()
    svc = JobService(db)
    r = svc.enqueue(
        JobRequest(
            job_name=JobNames.SYSTEM_HEALTH_CHECK,
            organization_id=1,
            payload={"message": "x"},
            idempotency_key="plat-1",
        )
    )
    job = svc.get_job(r.job_id)
    job.status = JobStatus.FAILED
    db.commit()

    app = FastAPI()
    app.include_router(platform_router.router, prefix="/api")

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[require_platform_admin] = lambda: user

    client = TestClient(app)
    detail = client.get(f"/api/platform/jobs/{r.job_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert "payload_summary" in data
    assert "api_key" not in (data.get("payload_summary") or {})
    assert data.get("payload") is None

    listing = client.get("/api/platform/jobs")
    assert listing.status_code == 200
    assert "payload" not in listing.json()["jobs"][0]

    retry = client.post(f"/api/platform/jobs/{r.job_id}/retry")
    assert retry.status_code == 200
    assert retry.json()["status"] == JobStatus.PENDING

    cancel = client.post(f"/api/platform/jobs/{r.job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == JobStatus.CANCELLED
