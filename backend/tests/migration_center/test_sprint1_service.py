"""Tests Sprint 1 — Migration Center (service + isolation + audit)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.migration_center.enums import MigrationMode, MigrationSessionStatus
from app.migration_center.exceptions import (
    MigrationConflictError,
    MigrationNotFoundError,
    MigrationValidationError,
)
from app.migration_center.schemas import CompanyProfileIn
from app.migration_center.service import MigrationCenterService
from app.migration_center.source_registry import validate_selected_sources
from tests.migration_center.conftest_helpers import (
    FakeAudit,
    make_migration_db,
    seed_org_user,
    valid_profile,
)


def test_01_create_initial_migration():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    audit = FakeAudit()
    row = MigrationCenterService(db, audit).create_session(
        organization_id=org.id,
        mode=MigrationMode.INITIAL_MIGRATION.value,
        actor_user_id=user.id,
    )
    assert row.status == MigrationSessionStatus.DRAFT.value
    assert row.mode == MigrationMode.INITIAL_MIGRATION.value
    assert any(e[0] == "record_migration_session_created" for e in audit.events)
    db.close()


def test_02_create_one_time_import():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    row = MigrationCenterService(db).create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    assert row.mode == MigrationMode.ONE_TIME_IMPORT.value
    db.close()


def test_03_refuse_second_active_initial():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    first = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.INITIAL_MIGRATION.value,
        actor_user_id=user.id,
    )
    with pytest.raises(MigrationConflictError) as exc:
        svc.create_session(
            organization_id=org.id,
            mode=MigrationMode.INITIAL_MIGRATION.value,
            actor_user_id=user.id,
        )
    assert exc.value.code == "initial_migration_active"
    assert first.id in exc.value.message
    # one_time still ok
    svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    db.close()


def test_04_05_06_tenant_isolation():
    factory, _ = make_migration_db()
    db = factory()
    org_a, user_a = seed_org_user(db, email="a@t.local", name="OrgA")
    org_b, user_b = seed_org_user(db, email="b@t.local", name="OrgB")
    svc = MigrationCenterService(db)
    sa = svc.create_session(
        organization_id=org_a.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user_a.id,
    )
    # lecture autorisée A
    got = svc.get_for_org(sa.id, org_a.id)
    assert got.id == sa.id
    # lecture interdite B → 404 métier
    with pytest.raises(MigrationNotFoundError):
        svc.get_for_org(sa.id, org_b.id)
    items_b, total_b = svc.list_sessions(organization_id=org_b.id)
    assert total_b == 0
    assert sa.id not in {i.id for i in items_b}
    db.close()


def test_07_08_profile_valid_invalid():
    CompanyProfileIn.model_validate(valid_profile())
    with pytest.raises(ValidationError):
        CompanyProfileIn.model_validate(valid_profile(join_reasons=[]))


def test_09_other_legal_form_required():
    with pytest.raises(ValidationError):
        CompanyProfileIn.model_validate(valid_profile(legal_form="other", other_legal_form=None))
    CompanyProfileIn.model_validate(
        valid_profile(legal_form="other", other_legal_form="SCI")
    )


def test_10_other_join_reason_required():
    with pytest.raises(ValidationError):
        CompanyProfileIn.model_validate(
            valid_profile(join_reasons=["other"], other_join_reason=None)
        )
    CompanyProfileIn.model_validate(
        valid_profile(join_reasons=["other"], other_join_reason="Besoin IA")
    )


def test_11_12_13_sources():
    cleaned = validate_selected_sources(["file_excel", "file_csv"])
    assert cleaned == ["file_excel", "file_csv"]
    with pytest.raises(MigrationValidationError) as unk:
        validate_selected_sources(["file_excel", "nope_source"])
    assert unk.value.code == "source_unknown"
    with pytest.raises(MigrationValidationError) as unav:
        validate_selected_sources(["legacy_blocked"])
    assert unav.value.code == "source_unavailable"
    with pytest.raises(MigrationValidationError) as conn:
        validate_selected_sources(["google_drive"])
    assert conn.value.code == "source_coming_soon"


def test_14_15_transitions():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    with pytest.raises(MigrationValidationError) as bad:
        svc.continue_session(row.id, org.id, actor_user_id=user.id)
    assert bad.value.code == "profile_required"

    profile = CompanyProfileIn.model_validate(valid_profile())
    row = svc.update_profile(row.id, org.id, profile, actor_user_id=user.id, version=row.version)
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    assert row.status == MigrationSessionStatus.PROFILE_COMPLETED.value

    # transition invalide : draft déjà passé
    with pytest.raises(MigrationValidationError):
        # forcer mauvais état via continue sans sources
        svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    db.close()


def test_16_17_cancel_and_refuse_modify():
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
    row = svc.cancel_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    assert row.status == MigrationSessionStatus.CANCELLED.value
    assert any(e[0] == "record_migration_session_cancelled" for e in audit.events)
    with pytest.raises(MigrationValidationError) as exc:
        svc.update_profile(
            row.id,
            org.id,
            CompanyProfileIn.model_validate(valid_profile()),
            actor_user_id=user.id,
        )
    assert exc.value.code == "session_cancelled"
    db.close()


def test_18_version_conflict():
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    svc = MigrationCenterService(db)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.ONE_TIME_IMPORT.value,
        actor_user_id=user.id,
    )
    with pytest.raises(MigrationConflictError) as exc:
        svc.update_sources(
            row.id,
            org.id,
            ["file_excel"],
            actor_user_id=user.id,
            version=999,
        )
    assert exc.value.code == "version_conflict"
    db.close()


def test_19_20_audit_and_full_happy_path_permissions_shape():
    """Audit events + parcours complet jusqu'à awaiting_upload."""
    factory, _ = make_migration_db()
    db = factory()
    org, user = seed_org_user(db)
    audit = FakeAudit()
    svc = MigrationCenterService(db, audit)
    row = svc.create_session(
        organization_id=org.id,
        mode=MigrationMode.INITIAL_MIGRATION.value,
        actor_user_id=user.id,
    )
    row = svc.update_profile(
        row.id,
        org.id,
        CompanyProfileIn.model_validate(valid_profile()),
        actor_user_id=user.id,
        version=row.version,
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    row = svc.update_sources(
        row.id,
        org.id,
        ["file_excel", "accounting_export"],
        actor_user_id=user.id,
        version=row.version,
    )
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    assert row.status == MigrationSessionStatus.SOURCES_SELECTED.value
    row = svc.continue_session(row.id, org.id, actor_user_id=user.id, version=row.version)
    assert row.status == MigrationSessionStatus.AWAITING_UPLOAD.value
    names = [e[0] for e in audit.events]
    assert "record_migration_session_created" in names
    assert "record_migration_profile_updated" in names
    assert "record_migration_sources_updated" in names
    assert "record_migration_step_completed" in names
    # métadonnées sans contenu fichier
    for _, kw in audit.events:
        assert "file_content" not in kw
        assert kw.get("organization_id") == org.id
        assert kw.get("session_id") == row.id or kw.get("session_id")
    # permissions catalogue présentes
    from app.iam.permission_catalog import Permission

    assert Permission.MIGRATION_CENTER_READ.value == "migration_center.read"
    assert Permission.MIGRATION_CENTER_CREATE.value == "migration_center.create"
    assert Permission.MIGRATION_CENTER_UPDATE.value == "migration_center.update"
    assert Permission.MIGRATION_CENTER_CANCEL.value == "migration_center.cancel"
    db.close()
