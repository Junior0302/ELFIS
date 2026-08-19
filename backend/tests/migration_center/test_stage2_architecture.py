"""Tests architecture stage 2 — Migration Center."""

from __future__ import annotations

import time

import pytest

from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.migration_center.enums import MigrationMode, MigrationSessionStatus, TimelineStepKey
from app.migration_center.exceptions import MigrationNotFoundError, MigrationValidationError
from app.migration_center.memory.service import MigrationMemoryService
from app.migration_center.models import ElfisMigrationTimelineEntry
from app.migration_center.profile_utils import unwrap_company_profile
from app.migration_center.progress.constants import TOTAL_WEIGHT
from app.migration_center.schemas import CompanyProfileIn, SessionOut
from app.migration_center.service import MigrationCenterService
from app.migration_center.source_registry import get_source, validate_selected_sources
from app.migration_center.timeline_service import MigrationTimelineService
from tests.migration_center.conftest_helpers import make_migration_db, seed_org_user, valid_profile


def _svc(db):
    return MigrationCenterService(db)


def test_token_auto_generated_unique_immutable():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    a = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    b = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    assert a.migration_session_token.startswith("mig_")
    assert b.migration_session_token.startswith("mig_")
    assert a.migration_session_token != b.migration_session_token
    token = a.migration_session_token
    a = svc.update_profile(
        a.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=a.version,
    )
    assert a.migration_session_token == token
    db.close()


def test_get_by_token_tenant_isolation():
    factory, _ = make_migration_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="ta@t.local", name="A")
    org_b, _ = seed_org_user(db, email="tb@t.local", name="B")
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org_a.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user_a.id,
    )
    got = svc.get_by_session_token(org_a.id, row.migration_session_token)
    assert got.id == row.id
    with pytest.raises(MigrationNotFoundError):
        svc.get_by_session_token(org_b.id, row.migration_session_token)
    db.close()


def test_profiles_initialized_and_separated():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    assert row.migration_profile["schema_version"] == 1
    assert row.migration_profile["data"] == {}
    assert row.ai_profile["schema_version"] == 1
    assert row.ai_profile["data"] == {}
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    flat = unwrap_company_profile(row.company_profile)
    assert flat and flat["legal_form"] == "sas"
    assert "legal_form" not in (row.migration_profile.get("data") or {})
    assert row.ai_profile["data"] == {}
    out = SessionOut.model_validate(row)
    assert out.company_profile["legal_form"] == "sas"
    assert out.migration_session_token == row.migration_session_token
    db.close()


def test_timeline_create_complete_duration_no_dup():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    tl = svc.list_timeline(row.id, org.id)
    assert any(e.step_key == TimelineStepKey.WELCOME.value and e.status == "started" for e in tl)
    time.sleep(0.02)
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    tl2 = MigrationTimelineService(db).list_timeline(
        organization_id=org.id, migration_session_id=row.id
    )
    welcome = next(e for e in tl2 if e.step_key == "welcome")
    assert welcome.status == "completed"
    assert welcome.duration_ms is not None and welcome.duration_ms >= 0
    # pas de doublon
    keys = [e.step_key for e in tl2]
    assert keys.count("welcome") == 1
    # complete idempotent
    MigrationTimelineService(db).complete_step(
        organization_id=org.id,
        migration_session_id=row.id,
        step_key="welcome",
        commit=True,
    )
    assert (
        db.query(ElfisMigrationTimelineEntry)
        .filter_by(migration_session_id=row.id, step_key="welcome")
        .count()
        == 1
    )
    db.close()


def test_activity_feed_on_create_profile_sources():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    acts = svc.list_activities(row.id, org.id)
    assert any(a.activity_type == "migration_created" for a in acts)
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    acts = svc.list_activities(row.id, org.id)
    assert any(a.activity_type == "profile_saved" for a in acts)
    row = svc.update_sources(
        row.id, org.id, ["file_pdf"], actor_user_id=user.id, version=row.version
    )
    acts = svc.list_activities(row.id, org.id)
    assert any(a.activity_type == "sources_saved" for a in acts)
    db.close()


def test_resume_active_refuse_cancelled_completed():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    status_before = row.status
    resumed = svc.resume_session(row.id, org.id, actor_user_id=user.id)
    assert resumed.status == status_before
    acts = svc.list_activities(row.id, org.id)
    assert any(a.activity_type == "migration_resumed" for a in acts)

    cancelled = svc.cancel_session(row.id, org.id, actor_user_id=user.id, version=resumed.version)
    with pytest.raises(MigrationValidationError) as exc:
        svc.resume_session(cancelled.id, org.id, actor_user_id=user.id)
    assert exc.value.code == "resume_cancelled"

    row2 = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    row2.status = MigrationSessionStatus.COMPLETED.value
    db.commit()
    with pytest.raises(MigrationValidationError) as exc2:
        svc.resume_session(row2.id, org.id, actor_user_id=user.id)
    assert exc2.value.code == "resume_completed"
    db.close()


def test_timeline_activity_tenant_isolation():
    factory, _ = make_migration_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="ia@t.local", name="IA")
    org_b, _ = seed_org_user(db, email="ib@t.local", name="IB")
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org_a.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user_a.id,
    )
    with pytest.raises(MigrationNotFoundError):
        svc.list_timeline(row.id, org_b.id)
    with pytest.raises(MigrationNotFoundError):
        svc.list_activities(row.id, org_b.id)
    db.close()


def test_progress_initial_and_after_steps():
    assert TOTAL_WEIGHT == 100
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    p0 = svc.get_progress(row.id, org.id)
    assert p0.overall_percent == 0
    assert p0.estimated_remaining_seconds is None
    assert p0.current_step == "welcome"

    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    p1 = svc.get_progress(row.id, org.id)
    # welcome 5 + company_profile 15
    assert p1.overall_percent == 20

    row = svc.update_sources(
        row.id, org.id, ["file_excel"], actor_user_id=user.id, version=row.version
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    p2 = svc.get_progress(row.id, org.id)
    assert p2.overall_percent == 35  # + data_sources 15

    # Frontend ne peut pas forcer overall_percent
    row.progress = {**(row.progress or {}), "overall_percent": 99}
    db.commit()
    p3 = svc.get_progress(row.id, org.id)
    assert p3.overall_percent == 35
    db.close()


def test_source_beta_maintenance_deprecated():
    beta = validate_selected_sources(["connector_beta_demo"])
    assert beta == ["connector_beta_demo"]
    assert get_source("connector_beta_demo").availability == "beta"

    with pytest.raises(MigrationValidationError) as m:
        validate_selected_sources(["connector_maintenance"])
    assert m.value.code == "source_maintenance"

    with pytest.raises(MigrationValidationError) as d:
        validate_selected_sources(["legacy_import_v1"])
    assert d.value.code == "source_deprecated"

    # Ancienne session : deprecated déjà sélectionnée tolérée
    kept = validate_selected_sources(
        ["legacy_import_v1"],
        previously_selected=["legacy_import_v1"],
    )
    assert kept == ["legacy_import_v1"]
    # lisible dans le registry
    assert get_source("legacy_import_v1") is not None


def test_domain_events_published_no_sensitive():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    events = db.query(ElfisEvent).filter(ElfisEvent.organization_id == org.id).all()
    names = {e.event_name for e in events}
    assert EventNames.MIGRATION_SESSION_CREATED in names
    for e in events:
        payload = e.payload or {}
        assert "company_profile" not in payload
        assert "file_content" not in str(payload)
        assert payload.get("migration_session_token") == row.migration_session_token
        assert "schema_version" in payload
    db.close()


def test_memory_session_scope_only_and_tenant():
    factory, _ = make_migration_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="ma@t.local", name="MA")
    org_b, _ = seed_org_user(db, email="mb@t.local", name="MB")
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org_a.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user_a.id,
    )
    mem = MigrationMemoryService(db)
    entry = mem.propose(
        organization_id=org_a.id,
        migration_session_id=row.id,
        memory_type="import_preference",
        key_hash="abc123456789",
        payload={"prefer_csv": True},
        scope="session",
        created_by_user_id=user_a.id,
    )
    assert entry.scope == "session"
    with pytest.raises(MigrationValidationError) as sc:
        mem.propose(
            organization_id=org_a.id,
            migration_session_id=row.id,
            memory_type="import_preference",
            key_hash="xyz123456789",
            payload={},
            scope="organization",
        )
    assert sc.value.code == "memory_scope_forbidden"
    with pytest.raises(MigrationValidationError) as gl:
        mem.propose(
            organization_id=org_a.id,
            migration_session_id=row.id,
            memory_type="import_preference",
            key_hash="prd123456789",
            payload={},
            scope="product",
        )
    assert gl.value.code in ("memory_scope_forbidden", "memory_global_forbidden")
    # isolation
    assert mem.list_for_session(organization_id=org_b.id, migration_session_id=row.id) == []
    with pytest.raises(Exception):
        mem.get_for_org(entry.id, org_b.id)
    db.close()


def test_optimistic_locking_still_works():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = _svc(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    from app.migration_center.exceptions import MigrationConflictError

    with pytest.raises(MigrationConflictError):
        svc.update_sources(
            row.id, org.id, ["file_csv"], actor_user_id=user.id, version=999
        )
    db.close()
