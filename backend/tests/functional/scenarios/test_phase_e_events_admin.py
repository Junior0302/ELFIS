"""Phase E — Events admin (EVENTADMIN-001…004)."""

from __future__ import annotations

from tests.functional.helpers.phase_e import (
    REASON,
    assert_safe_admin_body,
    seed_dead_letter_event,
)


def test_eventadmin_001_list(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_dead_letter_event(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get("/api/platform/events?page=1&page_size=20", headers=api._headers())
    assert r.status_code == 200
    assert_safe_admin_body(r.json())


def test_eventadmin_002_retry(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        event_id = seed_dead_letter_event(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/events/{event_id}/retry",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("pending", "retry")
    assert_safe_admin_body(r.json())


def test_eventadmin_003_resolve(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        event_id = seed_dead_letter_event(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.post(
        f"/api/platform/events/{event_id}/mark-resolved",
        headers=api._headers(),
        json={"reason": REASON},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("status") in ("processed", "resolved", "completed")


def test_eventadmin_004_dead_letter_filtered(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        event_id = seed_dead_letter_event(db, org_id=org_id)
    finally:
        db.close()

    api.login_user("platform_admin")
    r = api.client.get(f"/api/platform/events/{event_id}", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    blob = str(body).lower()
    assert "sk_live_event_secret" not in blob
    assert "should_not_appear" not in blob
    assert "pdf_bytes" not in blob
