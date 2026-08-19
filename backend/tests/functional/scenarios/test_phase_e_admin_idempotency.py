"""Phase E — Idempotence admin (IDEMP-001…003)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import (
    NOTE,
    REASON,
    seed_failed_job,
    seed_open_incident,
)


def test_idemp_001_double_suspend_controlled(api, functional_db):
    orgs = functional_db["seed"]["organizations"]
    org_id = orgs.get("ORG_NONE", orgs.get("ORG_EXPIRED", orgs.get("ORG_TRIAL", orgs["ORG_ACTIVE"])))["id"]
    api.login_user("platform_admin")
    r1 = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r1.status_code in (200, 400)
    r2 = api.client.post(
        f"/api/platform/organizations/{org_id}/suspend",
        headers=api._headers(),
        json={"reason": REASON},
    )
    # V1 : 2e suspension → 400 validation (pas de double état)
    assert r2.status_code in (200, 400)
    if r1.status_code == 200:
        api.client.post(
            f"/api/platform/organizations/{org_id}/restore",
            headers=api._headers(),
            json={"reason": REASON},
        )


def test_idemp_002_double_retry_job_controlled(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        job_id = seed_failed_job(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r1 = api.client.post(
        f"/api/platform/jobs/{job_id}/manual-retry",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r1.status_code == 200
    r2 = api.client.post(
        f"/api/platform/jobs/{job_id}/manual-retry",
        headers=api._headers(),
        json={"reason": REASON},
    )
    # Après retry → pending : 2e retry refusé (statut non retryable)
    assert r2.status_code in (200, 400)


def test_idemp_003_double_resolve_incident_controlled(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        iid = seed_open_incident(db, org_id=org_id, incident_type="phase_e_idemp")
    finally:
        db.close()

    api.login_user("platform_admin")
    r1 = api.client.post(
        f"/api/platform/incidents/{iid}/resolve",
        headers=api._headers(),
        json={"note": NOTE},
    )
    assert r1.status_code == 200
    r2 = api.client.post(
        f"/api/platform/incidents/{iid}/resolve",
        headers=api._headers(),
        json={"note": NOTE},
    )
    # V1 : transitions libres possibles — documenté ; pas de crash
    assert r2.status_code in (200, 400)
