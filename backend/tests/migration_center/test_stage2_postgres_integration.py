"""Intégration PostgreSQL réelle — scénario API Migration Center Stage 2."""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.migration_center import api as migration_api
from app.migration_center import models as mig_models  # noqa: F401
from app.models_saas import Organization, User
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres
from tests.migration_center.conftest_helpers import valid_profile


pytestmark = pytest.mark.skipif(
    os.getenv("ELFIS_POSTGRES_TESTS_ENABLED", "").lower() not in {"1", "true", "yes"},
    reason="ELFIS_POSTGRES_TESTS_ENABLED!=true",
)


def _pg_client():
    require_postgres()
    Session, engine = make_pg_session_factory()
    # ensure migration tables exist (certify script already applied)
    mig_models.ElfisMigrationSession.__table__.create(bind=engine, checkfirst=True)
    mig_models.ElfisMigrationTimelineEntry.__table__.create(bind=engine, checkfirst=True)
    mig_models.ElfisMigrationActivity.__table__.create(bind=engine, checkfirst=True)
    mig_models.ElfisMigrationMemoryEntry.__table__.create(bind=engine, checkfirst=True)

    db = Session()
    org_a = db.query(Organization).order_by(Organization.id.asc()).first()
    org_b = (
        db.query(Organization)
        .filter(Organization.id != org_a.id)
        .order_by(Organization.id.asc())
        .first()
    )
    if not org_a or not org_b:
        pytest.skip("Besoin d'au moins 2 organizations en staging")
    user = db.query(User).order_by(User.id.asc()).first()
    # user peut être None — le test le crée si besoin

    app = FastAPI()
    app.include_router(migration_api.router, prefix="/api")

    def override_db():
        try:
            yield db
        finally:
            pass

    def make_auth(org_id: int):
        def _auth():
            return AuthContext(
                user=user,
                organization_id=org_id,
                role="owner",
                permissions=["*"],
            )

        return _auth

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_active_subscription] = lambda: None
    return app, db, org_a, org_b, user, make_auth, Session, engine


def test_postgres_full_api_scenario_isolation_events():
    app, db, org_a, org_b, user, make_auth, Session, engine = _pg_client()
    # Staging peut n'avoir aucun user local — créer un user de certification éphémère
    if user is None:
        from uuid import uuid4

        user = User(
            first_name="Mig",
            last_name="Cert",
            email=f"mig-cert-{uuid4().hex[:10]}@elfis.test",
            password_hash="x",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        created_user = True
    else:
        created_user = False

    app.dependency_overrides[get_auth_context] = make_auth(org_a.id)
    # rebind make_auth with user
    def make_auth_fixed(org_id: int):
        def _auth():
            return AuthContext(
                user=user,
                organization_id=org_id,
                role="owner",
                permissions=["*"],
            )

        return _auth

    app.dependency_overrides[get_auth_context] = make_auth_fixed(org_a.id)
    client = TestClient(app)

    created = client.post("/api/migrations/sessions", json={"mode": "one_time_import"})
    assert created.status_code == 201, created.text
    body = created.json()
    sid = body["id"]
    token = body["migration_session_token"]
    assert token.startswith("mig_")
    version = body["version"]

    assert client.get(f"/api/migrations/sessions/{sid}").status_code == 200
    assert client.get(f"/api/migrations/sessions/{sid}/timeline").json()["items"]
    assert client.get(f"/api/migrations/sessions/{sid}/activities").json()["items"]
    prog0 = client.get(f"/api/migrations/sessions/{sid}/progress").json()["progress"]
    assert prog0["overall_percent"] == 0
    assert prog0["estimated_remaining_seconds"] is None

    p = client.patch(
        f"/api/migrations/sessions/{sid}/profile",
        json={"profile": valid_profile(), "version": version},
    )
    assert p.status_code == 200
    version = p.json()["version"]
    c1 = client.post(f"/api/migrations/sessions/{sid}/continue", json={"version": version})
    assert c1.status_code == 200
    version = c1.json()["version"]

    s = client.patch(
        f"/api/migrations/sessions/{sid}/sources",
        json={"source_ids": ["file_excel", "file_csv"], "version": version},
    )
    assert s.status_code == 200
    version = s.json()["version"]
    c2 = client.post(f"/api/migrations/sessions/{sid}/continue", json={"version": version})
    assert c2.status_code == 200
    version = c2.json()["version"]
    c3 = client.post(f"/api/migrations/sessions/{sid}/continue", json={"version": version})
    assert c3.status_code == 200
    final = c3.json()
    assert final["status"] == "awaiting_upload"
    assert final["progress"]["overall_percent"] == 40

    r1 = client.post(f"/api/migrations/sessions/{sid}/resume")
    r2 = client.post(f"/api/migrations/sessions/{sid}/resume")
    assert r1.status_code == 200 and r2.status_code == 200
    acts = client.get(f"/api/migrations/sessions/{sid}/activities").json()["items"]
    assert sum(1 for a in acts if a["activity_type"] == "migration_resumed") == 1

    tl = client.get(f"/api/migrations/sessions/{sid}/timeline").json()["items"]
    assert sum(1 for i in tl if i["step_key"] == "welcome") == 1

    # events
    events = (
        db.query(ElfisEvent)
        .filter(ElfisEvent.organization_id == org_a.id)
        .filter(ElfisEvent.aggregate_id == sid)
        .all()
    )
    names = {e.event_name for e in events}
    assert EventNames.MIGRATION_SESSION_CREATED in names
    assert EventNames.MIGRATION_STEP_STARTED in names
    for e in events:
        payload = e.payload or {}
        assert payload.get("migration_session_token") == token
        assert "company_profile" not in payload

    # cross-tenant 404
    app.dependency_overrides[get_auth_context] = make_auth_fixed(org_b.id)
    client_b = TestClient(app)
    assert client_b.get(f"/api/migrations/sessions/{sid}").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/timeline").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/activities").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/progress").status_code == 404

    # cleanup session data
    from sqlalchemy import text as sa_text

    db.execute(sa_text("DELETE FROM elfis_migration_activities WHERE migration_session_id=:s"), {"s": sid})
    db.execute(sa_text("DELETE FROM elfis_migration_timeline_entries WHERE migration_session_id=:s"), {"s": sid})
    db.execute(sa_text("DELETE FROM elfis_migration_memory_entries WHERE migration_session_id=:s"), {"s": sid})
    db.execute(sa_text("DELETE FROM elfis_migration_sessions WHERE id=:s"), {"s": sid})
    if created_user:
        db.execute(sa_text("DELETE FROM users WHERE id=:u"), {"u": user.id})
    db.commit()
    db.close()
