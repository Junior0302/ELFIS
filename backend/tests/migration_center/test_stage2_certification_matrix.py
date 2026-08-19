"""Tests certification Stage 2 — gaps matrice + événements + audit distinct."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.audit.audit_models import ElfisAuditEvent
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.migration_center.enums import MigrationMode, TimelineStepKey
from app.migration_center.exceptions import MigrationConflictError, MigrationValidationError
from app.migration_center.memory.service import MigrationMemoryService
from app.migration_center.models import ElfisMigrationActivity, ElfisMigrationTimelineEntry
from app.migration_center.schemas import CompanyProfileIn, SessionCreateIn, SessionOut
from app.migration_center.service import MigrationCenterService
from app.migration_center.timeline_service import MigrationTimelineService
from tests.migration_center.conftest_helpers import FakeAudit, make_migration_db, seed_org_user, valid_profile


REQUIRED_EVENT_NAMES = [
    EventNames.MIGRATION_SESSION_CREATED,
    EventNames.MIGRATION_PROFILE_UPDATED,
    EventNames.MIGRATION_SOURCES_UPDATED,
    EventNames.MIGRATION_STEP_STARTED,
    EventNames.MIGRATION_STEP_COMPLETED,
    EventNames.MIGRATION_SESSION_RESUMED,
    EventNames.MIGRATION_SESSION_CANCELLED,
    EventNames.MIGRATION_PROGRESS_UPDATED,
    EventNames.MIGRATION_ACTIVITY_RECORDED,
]


def test_event_names_use_v1_suffix():
    for name in REQUIRED_EVENT_NAMES:
        assert name.endswith(".v1")
        assert name.startswith("migration.")


def test_token_rejected_in_create_payload():
    with pytest.raises(ValidationError):
        SessionCreateIn.model_validate(
            {
                "mode": "one_time_import",
                "migration_session_token": "mig_injected",
            }
        )


def test_token_not_accepted_via_session_out_mutation_path():
    """Le frontend ne peut pas imposer le token à la création (extra forbid)."""
    body = SessionCreateIn(mode=MigrationMode.ONE_TIME_IMPORT)
    assert not hasattr(body, "migration_session_token") or getattr(body, "migration_session_token", None) is None


def test_start_and_complete_step_idempotent():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    tl = MigrationTimelineService(db)
    a = tl.start_step(
        organization_id=org.id,
        migration_session_id=row.id,
        step_key=TimelineStepKey.COMPANY_PROFILE.value,
        commit=True,
    )
    b = tl.start_step(
        organization_id=org.id,
        migration_session_id=row.id,
        step_key=TimelineStepKey.COMPANY_PROFILE.value,
        commit=True,
    )
    assert a.id == b.id
    assert a.status == "started"
    c1 = tl.complete_step(
        organization_id=org.id,
        migration_session_id=row.id,
        step_key=TimelineStepKey.COMPANY_PROFILE.value,
        commit=True,
    )
    c2 = tl.complete_step(
        organization_id=org.id,
        migration_session_id=row.id,
        step_key=TimelineStepKey.COMPANY_PROFILE.value,
        commit=True,
    )
    assert c1.id == c2.id
    assert c1.duration_ms == c2.duration_ms
    assert (
        db.query(ElfisMigrationTimelineEntry)
        .filter_by(migration_session_id=row.id, step_key="company_profile")
        .count()
        == 1
    )
    db.close()


def test_resume_double_click_idempotent_activity():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    svc.resume_session(row.id, org.id, actor_user_id=user.id)
    svc.resume_session(row.id, org.id, actor_user_id=user.id)
    resumed = (
        db.query(ElfisMigrationActivity)
        .filter_by(migration_session_id=row.id, activity_type="migration_resumed")
        .count()
    )
    assert resumed == 1
    db.close()


def test_memory_refuse_organization_and_product_scopes():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    row = MigrationCenterService(db).create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    mem = MigrationMemoryService(db)
    with pytest.raises(MigrationValidationError) as e1:
        mem.propose(
            organization_id=org.id,
            migration_session_id=row.id,
            memory_type="import_preference",
            key_hash="orgscope123456",
            payload={},
            scope="organization",
        )
    assert e1.value.code == "memory_scope_forbidden"
    with pytest.raises(MigrationValidationError) as e2:
        mem.propose(
            organization_id=org.id,
            migration_session_id=row.id,
            memory_type="import_preference",
            key_hash="prdscope123456",
            payload={},
            scope="product",
        )
    assert e2.value.code in ("memory_scope_forbidden", "memory_global_forbidden")
    db.close()


def test_activity_and_timeline_distinct_from_audit():
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
    acts = svc.list_activities(row.id, org.id)
    tls = svc.list_timeline(row.id, org.id)
    assert acts and tls
    # Activity feed ≠ table audit
    audit_count = db.query(ElfisAuditEvent).count()
    assert audit_count == 0  # FakeAudit n'écrit pas en DB
    assert any(e[0].startswith("record_migration_") for e in audit.events)
    # Les activités ne sont pas des events audit
    assert all(a.activity_type != "audit" for a in acts)
    assert all(hasattr(t, "step_key") for t in tls)
    db.close()


def test_event_payload_required_fields_and_no_sensitive():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    events = db.query(ElfisEvent).filter(ElfisEvent.organization_id == org.id).all()
    names = {e.event_name for e in events}
    assert EventNames.MIGRATION_SESSION_CREATED in names
    assert EventNames.MIGRATION_STEP_STARTED in names
    assert EventNames.MIGRATION_PROFILE_UPDATED in names
    forbidden_keys = {
        "company_profile",
        "file_content",
        "iban",
        "password",
        "api_key",
        "jwt",
        "content",
    }
    for e in events:
        payload = e.payload or {}
        for req in (
            "event_id",
            "organization_id",
            "migration_session_id",
            "migration_session_token",
            "occurred_at",
            "schema_version",
        ):
            assert req in payload, f"missing {req} in {e.event_name}"
        lowered = {str(k).lower() for k in payload}
        assert not (lowered & forbidden_keys)
        assert "company_profile" not in str(payload)
    out = SessionOut.model_validate(row)
    assert out.migration_session_token.startswith("mig_")
    db.close()


def test_optimistic_lock_on_continue_and_cancel():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    with pytest.raises(MigrationConflictError):
        svc.continue_session(row.id, org.id, actor_user_id=user.id, version=1)
    with pytest.raises(MigrationConflictError):
        svc.cancel_session(row.id, org.id, actor_user_id=user.id, version=1)
    db.close()
