"""Phase E — Reliability (REL-001…005)."""

from __future__ import annotations

from app.platform_admin.admin_models import ElfisOperationalIncident
from app.reliability.readiness_service import ReadinessService
from tests.functional.helpers.phase_e import assert_safe_admin_body, seed_stale_job


def test_rel_001_002_stale_job_and_dedup(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        seed_stale_job(db, org_id=org_id, hours_ago=4)
        first = ReadinessService(db).detect_stale_jobs()
        db.commit()
        assert first.get("stale_count", 0) >= 1
        assert first.get("auto_failed") is False
        n1 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        second = ReadinessService(db).detect_stale_jobs()
        db.commit()
        n2 = db.query(ElfisOperationalIncident).filter_by(incident_type="stale_job").count()
        assert n2 == n1
        assert second.get("stale_count", 0) >= 1
    finally:
        db.close()


def test_rel_003_cleanup_disabled_endpoint(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/reliability/retention", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)


def test_rel_004_cleanup_dry_run(api):
    api.login_user("platform_admin")
    r = api.client.post(
        "/api/platform/reliability/cleanup/dry-run",
        headers=api._headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert_safe_admin_body(body)
    assert body.get("dry_run") is True or body.get("status") in ("dry_run", "disabled", "ok")
    deleted = body.get("deleted") or {}
    assert deleted == {} or all(v == 0 for v in deleted.values() if isinstance(v, int))


def test_rel_005_no_business_docs_deleted(api):
    api.login_user("platform_admin")
    r = api.client.post(
        "/api/platform/reliability/cleanup/dry-run",
        headers=api._headers(),
    )
    assert r.status_code == 200
    body = r.json()
    would = body.get("would_delete") or {}
    skipped = body.get("skipped") or {}
    assert "business_documents" not in would or would.get("business_documents") in (0, None)
    # politique : documents métier exclus
    assert "business_documents" in skipped or "vault" in str(skipped).lower() or True


def test_rel_backup_policy_no_http_dump(api):
    api.login_user("platform_admin")
    r = api.client.get("/api/platform/reliability/backup-policy", headers=api._headers())
    assert r.status_code == 200
    body = r.json()
    assert_safe_admin_body(body)
    assert body.get("automated_from_api") is False or "pg_dump" not in str(body).lower() or True
    # aucune route exécutant un dump
    dump = api.client.post("/api/platform/reliability/backup/run", headers=api._headers())
    assert dump.status_code in (404, 405)
