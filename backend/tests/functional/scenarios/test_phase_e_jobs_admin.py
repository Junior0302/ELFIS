"""Phase E — Jobs admin (JOBADMIN-001…004)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import (
    REASON,
    assert_safe_admin_body,
    count_admin_audits,
    seed_failed_job,
    seed_pending_job,
)


def test_jobadmin_001_list(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_failed_job(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get("/api/platform/jobs?page=1&page_size=20", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_jobadmin_002_manual_retry(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        job_id = seed_failed_job(db, org_id=org_id)
        before = count_admin_audits(db, action="job.manual_retry")
    finally:
        db.close()

    api.login_user("platform_admin")
    bad = api.client.post(
        f"/api/platform/jobs/{job_id}/manual-retry",
        headers=api._headers(),
        json={"reason": "x"},
    )
    assert bad.status_code == 422

    r = api.client.post(
        f"/api/platform/jobs/{job_id}/manual-retry",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") in ("pending", "scheduled", "retry")
    assert_safe_admin_body(body)

    db = Session()
    try:
        assert count_admin_audits(db, action="job.manual_retry") >= before + 1
    finally:
        db.close()


def test_jobadmin_003_manual_cancel(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        job_id = seed_pending_job(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/jobs/{job_id}/manual-cancel",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("cancelled", "canceled")


def test_jobadmin_004_payload_filtered(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        job_id = seed_failed_job(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get(f"/api/platform/jobs/{job_id}", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "sk_live_payload_secret" not in blob
    assert "sk_live_should_not_leak" not in blob
