"""Tests API routes Migration Center Stage 2 (SQLite + overrides auth)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.migration_center import api as migration_api
from app.migration_center import models as mig_models  # noqa: F401
from app.models_saas import Organization, User
from tests.migration_center.conftest_helpers import make_migration_db, seed_org_user, valid_profile


def _client(org_id: int, user: User, db):
    app = FastAPI()
    app.include_router(migration_api.router, prefix="/api")

    def override_db():
        try:
            yield db
        finally:
            pass

    def override_auth():
        return AuthContext(
            user=user,
            organization_id=org_id,
            role="owner",
            permissions=["*"],
        )

    def override_sub():
        return None

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_context] = override_auth
    app.dependency_overrides[require_active_subscription] = override_sub
    return TestClient(app)


def test_api_full_scenario_and_cross_tenant_404():
    factory, _ = make_migration_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="api-a@t.local", name="API-A")
    org_b, user_b = seed_org_user(db, email="api-b@t.local", name="API-B")
    client_a = _client(org_a.id, user_a, db)
    client_b = _client(org_b.id, user_b, db)

    created = client_a.post("/api/migrations/sessions", json={"mode": "one_time_import"})
    assert created.status_code == 201
    body = created.json()
    sid = body["id"]
    token = body["migration_session_token"]
    assert token.startswith("mig_")
    version = body["version"]

    got = client_a.get(f"/api/migrations/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["migration_session_token"] == token

    tl = client_a.get(f"/api/migrations/sessions/{sid}/timeline")
    assert tl.status_code == 200
    assert any(i["step_key"] == "welcome" for i in tl.json()["items"])

    acts = client_a.get(f"/api/migrations/sessions/{sid}/activities")
    assert acts.status_code == 200
    assert any(i["activity_type"] == "migration_created" for i in acts.json()["items"])

    prog = client_a.get(f"/api/migrations/sessions/{sid}/progress")
    assert prog.status_code == 200
    assert prog.json()["progress"]["overall_percent"] == 0
    assert prog.json()["progress"]["estimated_remaining_seconds"] is None

    # token injecté refusé
    bad = client_a.post(
        "/api/migrations/sessions",
        json={"mode": "one_time_import", "migration_session_token": "mig_hack"},
    )
    assert bad.status_code == 422

    patched = client_a.patch(
        f"/api/migrations/sessions/{sid}/profile",
        json={"profile": valid_profile(), "version": version},
    )
    assert patched.status_code == 200
    version = patched.json()["version"]

    cont = client_a.post(
        f"/api/migrations/sessions/{sid}/continue",
        json={"version": version},
    )
    assert cont.status_code == 200
    version = cont.json()["version"]
    assert cont.json()["status"] == "profile_completed"

    src = client_a.patch(
        f"/api/migrations/sessions/{sid}/sources",
        json={"source_ids": ["file_pdf"], "version": version},
    )
    assert src.status_code == 200
    version = src.json()["version"]

    cont2 = client_a.post(
        f"/api/migrations/sessions/{sid}/continue",
        json={"version": version},
    )
    assert cont2.status_code == 200
    version = cont2.json()["version"]
    cont3 = client_a.post(
        f"/api/migrations/sessions/{sid}/continue",
        json={"version": version},
    )
    assert cont3.status_code == 200
    assert cont3.json()["status"] == "awaiting_upload"
    assert cont3.json()["progress"]["overall_percent"] == 40

    # optimistic lock on new-ish continue path
    conflict = client_a.post(
        f"/api/migrations/sessions/{sid}/continue",
        json={"version": 1},
    )
    assert conflict.status_code in (400, 409)

    r1 = client_a.post(f"/api/migrations/sessions/{sid}/resume")
    r2 = client_a.post(f"/api/migrations/sessions/{sid}/resume")
    assert r1.status_code == 200
    assert r2.status_code == 200
    acts2 = client_a.get(f"/api/migrations/sessions/{sid}/activities").json()["items"]
    assert sum(1 for a in acts2 if a["activity_type"] == "migration_resumed") == 1

    # cross-tenant
    assert client_b.get(f"/api/migrations/sessions/{sid}").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/timeline").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/activities").status_code == 404
    assert client_b.get(f"/api/migrations/sessions/{sid}/progress").status_code == 404
    assert client_b.post(f"/api/migrations/sessions/{sid}/resume").status_code == 404

    # timeline no duplicate welcome
    items = client_a.get(f"/api/migrations/sessions/{sid}/timeline").json()["items"]
    assert sum(1 for i in items if i["step_key"] == "welcome") == 1
    db.close()
