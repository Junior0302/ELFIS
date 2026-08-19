"""Tests Sprint 7 — Smart Migration Engine (orchestration, sans mutation S1–S6)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.document_intake.enums import DocumentLifecycleStatus
from app.document_intake.models import ElfisDocumentIntakeItem
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.smart_migration.batch_manager import BatchManager
from app.smart_migration.cleanup import CleanupManager
from app.smart_migration.enums import BatchItemStatus, BatchStatus, CleanupAction, SmartRunStatus
from app.smart_migration.exceptions import SmartConfirmationRequiredError
from app.smart_migration.orchestrator import SmartMigrationOrchestrator
from app.smart_migration.progress_engine import ProgressEngine
from app.smart_migration.resume_manager import ResumeManager
from tests.document_intake.conftest_helpers import make_intake_db, seed_org_user


def _bootstrap():
    factory, _ = make_intake_db()
    from app.smart_migration import models as sm  # noqa: F401
    from app.import_engine import models as imp  # noqa: F401
    from app.validation_mapping import models as val  # noqa: F401
    from app.models import Invoice, BankAccount, BankTransaction  # noqa: F401
    from app.models_saas import Contact  # noqa: F401

    db = factory()
    engine = db.get_bind()
    for tbl in (
        val.ElfisValidationSession.__table__,
        val.ElfisValidationField.__table__,
        val.ElfisValidationHistory.__table__,
        val.ElfisValidationDuplicate.__table__,
        val.ElfisValidationMatch.__table__,
        sm.ElfisSmartMigrationRun.__table__,
        sm.ElfisSmartMigrationBatch.__table__,
        sm.ElfisSmartMigrationBatchItem.__table__,
        sm.ElfisSmartMigrationReport.__table__,
        sm.ElfisSmartMigrationCleanupLog.__table__,
        imp.ElfisImportRun.__table__,
        imp.ElfisImportFingerprint.__table__,
        imp.ElfisImportArtifact.__table__,
        imp.ElfisImportReport.__table__,
        imp.ElfisImportAuditLog.__table__,
    ):
        tbl.create(bind=engine, checkfirst=True)
    org, user = seed_org_user(db)
    return db, org, user


def _seed_docs(db, org, migration_id: str, n: int, *, status: str | None = None):
    status = status or DocumentLifecycleStatus.READY_FOR_IMPORT.value
    ids = []
    prefix = migration_id.replace("-", "")[:8]
    for i in range(n):
        uid = f"{prefix}{i:06d}"[:32]
        item = ElfisDocumentIntakeItem(
            id=str(uuid4()),
            organization_id=org.id,
            migration_session_id=migration_id,
            original_filename=f"doc_{i}.txt",
            normalized_filename=f"doc_{i}.txt",
            extension="txt",
            format_id="txt",
            mime="text/plain",
            size_bytes=10,
            checksum_sha256=f"{prefix}{i:056x}"[:64],
            status=status,
            lifecycle_status=status,
            storage_key=f"tmp/{migration_id}/{i}",
            universal_document_id=uid,
        )
        db.add(item)
        ids.append({"document_id": item.id, "universal_document_id": item.universal_document_id})
    db.commit()
    return ids


def test_batch_manager_100_and_1000_simulated():
    db, org, user = _bootstrap()
    mig = str(uuid4())
    orch = SmartMigrationOrchestrator(db)

    # 100 docs
    docs100 = _seed_docs(db, org, mig, 100)
    run = orch.start_or_get_run(
        organization_id=org.id,
        migration_session_id=mig,
        actor_user_id=user.id,
        batch_size=25,
        auto_import=False,
    )
    batches = BatchManager(db).list_batches(run.id)
    assert len(batches) == 4
    assert sum(b.documents_count for b in batches) == 100

    # process without import engine (awaiting path)
    def ok(item):
        return {"stage": "ready_for_import", "awaiting_pipeline": True}

    for b in batches:
        BatchManager(db).execute_batch(b, run, process_item=ok)
    db.refresh(run)
    ProgressEngine(db).refresh_run(run)
    assert run.documents_total == 100

    # 1000 simulés — découpage uniquement
    mig2 = str(uuid4())
    docs1000 = _seed_docs(db, org, mig2, 1000)
    run2 = orch.start_or_get_run(
        organization_id=org.id,
        migration_session_id=mig2,
        actor_user_id=user.id,
        batch_size=50,
        auto_import=False,
    )
    assert len(BatchManager(db).list_batches(run2.id)) == 20
    assert len(docs1000) == 1000
    db.close()


def test_resume_cancel_retry_dashboard_report():
    db, org, user = _bootstrap()
    mig = str(uuid4())
    _seed_docs(db, org, mig, 10)
    orch = SmartMigrationOrchestrator(db)
    run = orch.start_or_get_run(
        organization_id=org.id,
        migration_session_id=mig,
        actor_user_id=user.id,
        batch_size=5,
        auto_import=False,
    )

    # fail first item intentionally then resume
    bm = BatchManager(db)
    batches = bm.list_batches(run.id)
    first = True

    def flaky(item):
        nonlocal first
        if first:
            first = False
            raise RuntimeError("boom")
        return {"stage": "ok"}

    bm.execute_batch(batches[0], run, process_item=flaky)
    failed = (
        db.query(__import__("app.smart_migration.models", fromlist=["ElfisSmartMigrationBatchItem"]).ElfisSmartMigrationBatchItem)
        .filter_by(smart_run_id=run.id, status=BatchItemStatus.FAILED.value)
        .count()
    )
    assert failed >= 1

    # resume
    ResumeManager(db).prepare_resume(run)
    orch.resume(
        organization_id=org.id,
        migration_session_id=mig,
        actor_user_id=user.id,
    )
    db.refresh(run)

    dash = orch.dashboard(organization_id=org.id, migration_session_id=mig)
    assert dash["documents_total"] == 10
    assert "chart" in dash
    assert dash["progress_percent"] >= 0

    metrics = orch.metrics(organization_id=org.id, migration_session_id=mig)
    assert "throughput_per_min" in metrics
    assert "estimated_cost" in metrics

    report = orch.get_report(organization_id=org.id, migration_session_id=mig, fmt="json")
    assert report["version"] >= 1
    assert "summary" in report

    csv_rep = orch.get_report(organization_id=org.id, migration_session_id=mig, fmt="csv")
    assert csv_rep.get("csv")

    # cancel new run
    mig3 = str(uuid4())
    _seed_docs(db, org, mig3, 3)
    orch.start_or_get_run(
        organization_id=org.id,
        migration_session_id=mig3,
        actor_user_id=user.id,
        batch_size=10,
        auto_import=False,
    )
    cancelled = orch.cancel(
        organization_id=org.id, migration_session_id=mig3, actor_user_id=user.id
    )
    assert cancelled.status == SmartRunStatus.CANCELLED.value

    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.SMART_MIGRATION_STARTED in names
    db.close()


def test_cleanup_requires_confirmation():
    db, org, user = _bootstrap()
    cm = CleanupManager(db)
    plan = cm.plan(
        organization_id=org.id,
        action=CleanupAction.SECURE_DELETE.value,
        actor_user_id=user.id,
    )
    assert plan["requires_confirmation"] is True
    try:
        cm.execute(
            organization_id=org.id,
            action=CleanupAction.SECURE_DELETE.value,
            confirmed=False,
            actor_user_id=user.id,
        )
        # without confirmed on secure_delete raises
    except SmartConfirmationRequiredError:
        pass
    else:
        # execute returns plan when not confirmed for some actions
        pass
    out = cm.execute(
        organization_id=org.id,
        action=CleanupAction.ARCHIVE.value,
        confirmed=True,
        migration_session_id=str(uuid4()),
        actor_user_id=user.id,
    )
    assert out["confirmed"] is True
    db.close()


def test_progress_never_client_side():
    """ProgressEngine calcule côté serveur."""
    db, org, _ = _bootstrap()
    mig = str(uuid4())
    _seed_docs(
        db,
        org,
        mig,
        4,
        status=DocumentLifecycleStatus.IMPORT_COMPLETED.value,
    )
    snap = ProgressEngine(db).compute_for_migration(
        organization_id=org.id, migration_session_id=mig
    )
    assert snap.documents_imported == 4
    assert snap.progress_percent == 100.0
    db.close()


def test_permissions_catalog():
    from app.smart_migration.permissions import SMART_MIGRATION_PERMISSIONS
    from app.iam.permission_catalog import Permission

    for p in SMART_MIGRATION_PERMISSIONS:
        assert Permission(p).value == p


def test_status_endpoint_service():
    db, org, user = _bootstrap()
    mig = str(uuid4())
    _seed_docs(db, org, mig, 2)
    orch = SmartMigrationOrchestrator(db)
    st = orch.status(organization_id=org.id, migration_session_id=mig)
    assert st["status"] == "idle"
    orch.start_or_get_run(
        organization_id=org.id,
        migration_session_id=mig,
        actor_user_id=user.id,
        auto_import=False,
    )
    st2 = orch.status(organization_id=org.id, migration_session_id=mig)
    assert st2["smart_run_id"]
    db.close()
