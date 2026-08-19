"""Phase E — Incidents (INC-001…004)."""

from __future__ import annotations

from app.platform_admin.admin_models import ElfisOperationalIncident
from app.reliability.readiness_service import ReadinessService
from tests.functional.helpers.phase_e import (
    NOTE,
    assert_safe_admin_body,
    seed_open_incident,
    seed_stale_job,
)


def test_inc_001_002_stale_creates_deduped(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_stale_job(db, org_id=org_id)
        r1 = ReadinessService(db).detect_stale_jobs()
        db.commit()
        assert r1.get("stale_count", 0) >= 1
        n1 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        assert n1 >= 1
        r2 = ReadinessService(db).detect_stale_jobs()
        db.commit()
        n2 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        assert n2 == n1
        assert r2.get("stale_count", 0) >= 1
    finally:
        db.close()


def test_inc_003_acknowledge(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        iid = seed_open_incident(db, org_id=org_id, incident_type="phase_e_ack")
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/incidents/{iid}/acknowledge",
        headers=api._headers(),
        json={"note": NOTE},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "acknowledged" or body.get("incident", {}).get("status") == "acknowledged"
    assert_safe_admin_body(body)


def test_inc_004_resolve(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        iid = seed_open_incident(db, org_id=org_id, incident_type="phase_e_resolve")
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/incidents/{iid}/resolve",
        headers=api._headers(),
        json={"note": NOTE},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    status = body.get("status") or body.get("incident", {}).get("status")
    assert status == "resolved"
    assert_safe_admin_body(body)
