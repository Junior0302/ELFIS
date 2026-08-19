"""Cohérence multi-moteurs — transitions Migration Center Stage 2."""

from __future__ import annotations

from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.migration_center.enums import MigrationMode, MigrationSessionStatus
from app.migration_center.schemas import CompanyProfileIn
from app.migration_center.service import MigrationCenterService
from tests.migration_center.conftest_helpers import FakeAudit, make_migration_db, seed_org_user, valid_profile


def _snapshot(svc, row, org_id, audit: FakeAudit):
    progress = svc.get_progress(row.id, org_id)
    return {
        "status": row.status,
        "current_step": row.current_step,
        "version": row.version,
        "last_activity_at": row.last_activity_at,
        "token": row.migration_session_token,
        "overall_percent": progress.overall_percent,
        "timeline": [(t.step_key, t.status) for t in svc.list_timeline(row.id, org_id)],
        "activities": [a.activity_type for a in svc.list_activities(row.id, org_id)],
        "audit_methods": [e[0] for e in audit.events],
    }


def test_coherence_draft_to_awaiting_upload_cancel_resume_paths():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    audit = FakeAudit()
    svc = MigrationCenterService(db, audit)

    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    s0 = _snapshot(svc, row, org.id, audit)
    assert s0["status"] == MigrationSessionStatus.DRAFT.value
    assert ("welcome", "started") in s0["timeline"]
    assert "migration_created" in s0["activities"]
    assert s0["overall_percent"] == 0
    assert any(e.event_name == EventNames.MIGRATION_SESSION_CREATED for e in db.query(ElfisEvent).all())

    # draft -> profile_completed
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    s1 = _snapshot(svc, row, org.id, audit)
    assert s1["status"] == MigrationSessionStatus.PROFILE_COMPLETED.value
    assert s1["version"] > s0["version"]
    assert s1["overall_percent"] == 20
    assert ("company_profile", "completed") in s1["timeline"]
    assert "profile_saved" in s1["activities"]
    assert "step_completed" in s1["activities"]
    assert "record_migration_step_completed" in s1["audit_methods"]
    assert any(e.event_name == EventNames.MIGRATION_STEP_COMPLETED for e in db.query(ElfisEvent).all())
    assert s1["token"] == s0["token"]

    # profile_completed -> sources_selected
    row = svc.update_sources(
        row.id, org.id, ["file_excel"], actor_user_id=user.id, version=row.version
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    s2 = _snapshot(svc, row, org.id, audit)
    assert s2["status"] == MigrationSessionStatus.SOURCES_SELECTED.value
    assert s2["overall_percent"] == 35
    assert ("data_sources", "completed") in s2["timeline"]
    assert "sources_saved" in s2["activities"]
    assert any(e.event_name == EventNames.MIGRATION_SOURCES_UPDATED for e in db.query(ElfisEvent).all())

    # sources_selected -> awaiting_upload
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    s3 = _snapshot(svc, row, org.id, audit)
    assert s3["status"] == MigrationSessionStatus.AWAITING_UPLOAD.value
    assert s3["overall_percent"] == 40
    assert ("upload_preparation", "completed") in s3["timeline"]
    assert ("file_upload", "pending") in s3["timeline"]
    assert s3["last_activity_at"] >= s2["last_activity_at"]

    # resume (sans changer statut)
    before = row.status
    before_version = row.version
    row = svc.resume_session(row.id, org.id, actor_user_id=user.id)
    s4 = _snapshot(svc, row, org.id, audit)
    assert row.status == before
    assert row.version == before_version
    assert "migration_resumed" in s4["activities"]
    assert any(e.event_name == EventNames.MIGRATION_SESSION_RESUMED for e in db.query(ElfisEvent).all())

    # cancel
    row = svc.cancel_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    s5 = _snapshot(svc, row, org.id, audit)
    assert s5["status"] == MigrationSessionStatus.CANCELLED.value
    assert "migration_cancelled" in s5["activities"]
    assert "record_migration_session_cancelled" in s5["audit_methods"]
    assert any(e.event_name == EventNames.MIGRATION_SESSION_CANCELLED for e in db.query(ElfisEvent).all())
    # pas de doublon timeline welcome
    assert s5["timeline"].count(("welcome", "completed")) + s5["timeline"].count(("welcome", "started")) <= 1
    welcome_rows = [x for x in s5["timeline"] if x[0] == "welcome"]
    assert len(welcome_rows) == 1
    db.close()
