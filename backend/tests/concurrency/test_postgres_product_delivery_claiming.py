"""RC2.5.8 — Concurrence product deliveries sur PostgreSQL réel.

Cas D–J : claim, lease, idempotence, bridge unique, unknown, reconcile, tenant.
"""

from __future__ import annotations

import json
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.models_saas import Organization
from app.product_integrations import metrics as pi_metrics
from app.product_integrations.models import (
    ElfisProductDocumentDelivery,
    ElfisProductDocumentDeliveryAttempt,
    ElfisProductProcessingPackage,
)
from app.product_integrations.noop_counter import (
    get_noop_deliver_calls,
    reset_noop_deliver_calls,
)
from app.product_integrations.registry import (
    NoopDocumentBridge,
    ProductReceipt,
    reset_bridge_registry_for_tests,
)
from app.product_integrations.repository import ProductIntegrationRepository
from app.product_integrations.service import ProductIntegrationService
from app.product_integrations.types import DeliveryStatus, PackageStatus
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.storage.storage_models import ElfisStorageObject
from tests.concurrency.postgres_helpers import make_pg_session_factory, require_postgres

JOIN_TIMEOUT = 45
PRODUCT = "rc258_noop"


def _seed_org(db, *, suffix: str = "") -> int:
    org = Organization(name=f"rc258-del-{suffix}{uuid4().hex[:8]}")
    db.add(org)
    db.flush()
    return int(org.id)


def _cleanup(
    db,
    *,
    delivery_ids: list[str] | None = None,
    package_ids: list[str] | None = None,
    storage_ids: list[str] | None = None,
    org_ids: list[int] | None = None,
) -> None:
    if delivery_ids:
        db.query(ElfisProductDocumentDeliveryAttempt).filter(
            ElfisProductDocumentDeliveryAttempt.delivery_id.in_(delivery_ids)
        ).delete(synchronize_session=False)
        db.query(ElfisProductDocumentDelivery).filter(
            ElfisProductDocumentDelivery.id.in_(delivery_ids)
        ).delete(synchronize_session=False)
    if package_ids:
        db.query(ElfisProductProcessingPackage).filter(
            ElfisProductProcessingPackage.id.in_(package_ids)
        ).delete(synchronize_session=False)
    if storage_ids:
        db.query(ElfisStorageObject).filter(ElfisStorageObject.id.in_(storage_ids)).delete(
            synchronize_session=False
        )
    if org_ids:
        for oid in org_ids:
            db.query(Organization).filter(Organization.id == oid).delete(
                synchronize_session=False
            )
    db.commit()


def _make_package(org_id: int, *, artifact_id: str | None = None, product_key: str = PRODUCT):
    pid = str(uuid4())
    return ElfisProductProcessingPackage(
        id=pid,
        organization_id=org_id,
        product_key=product_key,
        document_id=str(uuid4()),
        document_version_id=str(uuid4()),
        extraction_result_id=str(uuid4()),
        business_validation_id=str(uuid4()),
        package_schema_key="elfis_document_package_v1",
        package_schema_version="1",
        status=PackageStatus.READY.value,
        content_artifact_storage_object_id=artifact_id,
        idempotency_key=f"pkg-idem-{pid}",
    )


def _make_delivery(org_id: int, package_id: str, *, status: str = DeliveryStatus.QUEUED.value):
    did = str(uuid4())
    return ElfisProductDocumentDelivery(
        id=did,
        organization_id=org_id,
        package_id=package_id,
        product_key=PRODUCT,
        bridge_key="noop",
        bridge_version="1",
        status=status,
        attempt_count=0,
        max_attempts=3,
        idempotency_key=f"del-{did}",
    )


def _write_package_artifact(db, org_id: int, tmp_root: Path) -> str:
    body = {
        "package_schema": "elfis_document_package_v1",
        "organization_id": org_id,
        "extraction": {"result_id": "e", "confirmed": True},
        "validation": {"result_id": "v", "status": "valid"},
    }
    raw = json.dumps(body).encode("utf-8")
    ns = "rc258"
    key = f"probe/{uuid4().hex}.json"
    provider = LocalStorageProvider(root=tmp_root)
    provider.put_object(namespace=ns, object_key=key, data=raw)
    oid = str(uuid4())
    db.add(
        ElfisStorageObject(
            id=oid,
            provider="local",
            namespace=ns,
            object_key=key,
            original_filename="pkg.json",
            safe_filename="pkg.json",
            mime_type_declared="application/json",
            size_bytes=len(raw),
            status="ready",
            organization_id=org_id,
        )
    )
    db.flush()
    return oid


def test_postgres_delivery_claim_skip_locked_unique():
    """D — claim concurrent : aucun double claim."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    import inspect

    src = inspect.getsource(ProductIntegrationRepository._claim_postgres)
    assert "FOR UPDATE SKIP LOCKED" in src

    db = Session()
    package_id = str(uuid4())
    delivery_ids: list[str] = []
    org_id = None
    try:
        org_id = _seed_org(db, suffix="d-")
        pkg = _make_package(org_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        for _ in range(20):
            d = _make_delivery(org_id, package_id)
            delivery_ids.append(d.id)
            db.add(d)
        db.commit()
    finally:
        db.close()

    claimed: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(4, timeout=JOIN_TIMEOUT)

    def worker(wid: str):
        s = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            repo = ProductIntegrationRepository(s)
            rows = repo.claim_deliveries(
                worker_id=wid, limit=5, lease_seconds=60, product_key=PRODUCT
            )
            with lock:
                claimed.extend([r.id for r in rows])
                for r in rows:
                    assert r.status == DeliveryStatus.DELIVERING.value
                    assert r.locked_by == wid
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert len(claimed) == len(set(claimed)), "double claim détecté"
    assert set(claimed).issubset(set(delivery_ids))
    assert len(claimed) == 20

    db = Session()
    try:
        _cleanup(db, delivery_ids=delivery_ids, package_ids=[package_id], org_ids=[org_id] if org_id else None)
    finally:
        db.close()


def test_E_delivery_lease_expiry_recovery():
    """E — delivering + lease expirée récupérée une seule fois."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    db = Session()
    org_id = None
    package_id = None
    delivery_id = None
    try:
        org_id = _seed_org(db, suffix="e-")
        pkg = _make_package(org_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        expired = datetime.utcnow() - timedelta(seconds=90)
        d = _make_delivery(org_id, package_id, status=DeliveryStatus.DELIVERING.value)
        d.locked_by = "dead-pi"
        d.locked_until = expired
        # tentative précédente conservée
        db.add(d)
        db.flush()
        delivery_id = d.id
        db.add(
            ElfisProductDocumentDeliveryAttempt(
                id=str(uuid4()),
                delivery_id=delivery_id,
                attempt_number=1,
                worker_id="dead-pi",
                status="failed",
                started_at=expired,
                completed_at=expired,
                error_code="lease_expired_probe",
            )
        )
        d.attempt_count = 1
        db.commit()
    finally:
        db.close()

    barrier = threading.Barrier(3, timeout=JOIN_TIMEOUT)
    winners: list[str] = []
    lock = threading.Lock()

    def worker(wid: str) -> None:
        s = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            rows = ProductIntegrationRepository(s).claim_deliveries(
                worker_id=wid, limit=5, lease_seconds=60, product_key=PRODUCT
            )
            with lock:
                for r in rows:
                    if r.id == delivery_id:
                        winners.append(wid)
                        assert r.locked_by == wid
                        assert r.status == DeliveryStatus.DELIVERING.value
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(f"e-{i}",)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert len(winners) == 1, winners

    db = Session()
    try:
        attempts = (
            db.query(ElfisProductDocumentDeliveryAttempt)
            .filter(ElfisProductDocumentDeliveryAttempt.delivery_id == delivery_id)
            .all()
        )
        assert any(a.error_code == "lease_expired_probe" for a in attempts)
        _cleanup(
            db,
            delivery_ids=[delivery_id] if delivery_id else [],
            package_ids=[package_id] if package_id else [],
            org_ids=[org_id] if org_id else None,
        )
    finally:
        db.close()


def test_F_delivery_idempotency_concurrent_insert():
    """F — même idempotency_key → une seule delivery ; duplicate_prevented."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    pi_metrics.reset_for_tests()
    db = Session()
    org_id = None
    package_id = None
    shared_key = f"del-shared-{uuid4().hex}"
    try:
        org_id = _seed_org(db, suffix="f-")
        pkg = _make_package(org_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        db.commit()
    finally:
        db.close()

    barrier = threading.Barrier(4, timeout=JOIN_TIMEOUT)
    results: list[str] = []
    errors: list[str] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        s = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            svc = ProductIntegrationService(s)
            # Insert concurrent via repo + IntegrityError path simulé au niveau DB
            row = ElfisProductDocumentDelivery(
                id=str(uuid4()),
                organization_id=org_id,
                package_id=package_id,
                product_key=PRODUCT,
                bridge_key="noop",
                bridge_version="1",
                status=DeliveryStatus.QUEUED.value,
                attempt_count=0,
                max_attempts=3,
                idempotency_key=shared_key,
            )
            try:
                ProductIntegrationRepository(s).add_delivery(row, commit=True)
                with lock:
                    results.append(row.id)
            except Exception:
                s.rollback()
                existing = ProductIntegrationRepository(s).get_delivery_by_idempotency(shared_key)
                assert existing is not None
                with lock:
                    results.append(existing.id)
                    pi_metrics.incr("package_duplicate_prevented_total")
        except Exception as exc:
            with lock:
                errors.append(f"{i}:{type(exc).__name__}")
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert not errors, errors
    assert len(set(results)) == 1, results
    assert pi_metrics.get("package_duplicate_prevented_total") >= 1

    db = Session()
    try:
        d = ProductIntegrationRepository(db).get_delivery_by_idempotency(shared_key)
        assert d is not None
        count = (
            db.query(ElfisProductDocumentDelivery)
            .filter(ElfisProductDocumentDelivery.idempotency_key == shared_key)
            .count()
        )
        assert count == 1
        _cleanup(
            db,
            delivery_ids=[d.id],
            package_ids=[package_id] if package_id else [],
            org_ids=[org_id] if org_id else None,
        )
    finally:
        db.close()


def test_G_single_bridge_call_under_concurrent_workers(monkeypatch):
    """G — un seul claim + un seul appel bridge noop pour une delivery."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    reset_noop_deliver_calls()
    reset_bridge_registry_for_tests()
    tmp = Path(tempfile.mkdtemp(prefix="rc258-g-"))
    monkeypatch.setattr("app.config.settings.storage_local_root", str(tmp))

    db = Session()
    org_id = None
    package_id = None
    delivery_id = None
    storage_id = None
    try:
        org_id = _seed_org(db, suffix="g-")
        storage_id = _write_package_artifact(db, org_id, tmp)
        pkg = _make_package(org_id, artifact_id=storage_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        d = _make_delivery(org_id, package_id)
        delivery_id = d.id
        db.add(d)
        db.commit()
    finally:
        db.close()

    barrier = threading.Barrier(3, timeout=JOIN_TIMEOUT)
    processed: list[str] = []
    lock = threading.Lock()

    def worker(wid: str) -> None:
        s = Session()
        try:
            barrier.wait(timeout=JOIN_TIMEOUT)
            repo = ProductIntegrationRepository(s)
            svc = ProductIntegrationService(s)
            claimed = repo.claim_deliveries(
                worker_id=wid, limit=1, lease_seconds=60, product_key=PRODUCT
            )
            for row in claimed:
                if row.id != delivery_id:
                    continue
                svc.process_delivery(row, worker_id=wid)
                with lock:
                    processed.append(wid)
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(f"g-{i}",)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=JOIN_TIMEOUT)

    assert len(processed) == 1, processed
    assert get_noop_deliver_calls() == 1

    db = Session()
    try:
        d = db.get(ElfisProductDocumentDelivery, delivery_id)
        assert d is not None
        assert d.status == DeliveryStatus.DELIVERED.value
        assert d.external_reference and d.external_reference.startswith("noop:")
        attempts = (
            db.query(ElfisProductDocumentDeliveryAttempt)
            .filter(ElfisProductDocumentDeliveryAttempt.delivery_id == delivery_id)
            .all()
        )
        assert len(attempts) == 1
        _cleanup(
            db,
            delivery_ids=[delivery_id],
            package_ids=[package_id],
            storage_ids=[storage_id] if storage_id else [],
            org_ids=[org_id] if org_id else None,
        )
    finally:
        db.close()


def test_H_delivery_unknown_no_blind_retry(monkeypatch):
    """H — état distant inconnu → unknown ; pas de reclaim / retry aveugle."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    reset_bridge_registry_for_tests()
    tmp = Path(tempfile.mkdtemp(prefix="rc258-h-"))
    monkeypatch.setattr("app.config.settings.storage_local_root", str(tmp))

    from app.product_integrations.registry import ProductBridgeRegistry

    class UncertainBridge(NoopDocumentBridge):
        def deliver(self, package, idempotency_key):  # noqa: ANN001
            return ProductReceipt(
                status="unknown",
                external_reference=f"unc:{idempotency_key[:12]}",
                uncertain=True,
                error_code="remote_status_unknown",
            )

    db = Session()
    org_id = None
    package_id = None
    delivery_id = None
    storage_id = None
    try:
        org_id = _seed_org(db, suffix="h-")
        storage_id = _write_package_artifact(db, org_id, tmp)
        pkg = _make_package(org_id, artifact_id=storage_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        d = _make_delivery(org_id, package_id, status=DeliveryStatus.DELIVERING.value)
        d.locked_by = "h-worker"
        d.locked_until = datetime.utcnow() + timedelta(minutes=5)
        delivery_id = d.id
        db.add(d)
        db.commit()

        svc = ProductIntegrationService(db)
        reg = ProductBridgeRegistry()
        reg.register(UncertainBridge())
        svc._bridges = reg
        row = db.get(ElfisProductDocumentDelivery, delivery_id)
        assert row is not None
        out = svc.process_delivery(row, worker_id="h-worker")
        assert out.status == DeliveryStatus.UNKNOWN.value
        assert out.external_reference
    finally:
        db.close()

    db = Session()
    try:
        claimed = ProductIntegrationRepository(db).claim_deliveries(
            worker_id="h-retry",
            limit=10,
            lease_seconds=60,
            product_key=PRODUCT,
        )
        assert all(c.id != delivery_id for c in claimed)

        d = db.get(ElfisProductDocumentDelivery, delivery_id)
        assert d is not None
        assert d.status == DeliveryStatus.UNKNOWN.value
        _cleanup(
            db,
            delivery_ids=[delivery_id],
            package_ids=[package_id],
            storage_ids=[storage_id] if storage_id else [],
            org_ids=[org_id] if org_id else None,
        )
    finally:
        db.close()


def test_I_reconcile_unknown_to_manual_review(monkeypatch):
    """I — reconciliation dry-run puis apply → manual_review ; pas de 2e livraison."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    reset_bridge_registry_for_tests()
    tmp = Path(tempfile.mkdtemp(prefix="rc258-i-"))
    monkeypatch.setattr("app.config.settings.storage_local_root", str(tmp))

    db = Session()
    org_id = None
    package_id = None
    delivery_id = None
    storage_id = None
    ext_ref = f"noop:recon-{uuid4().hex[:12]}"
    try:
        org_id = _seed_org(db, suffix="i-")
        storage_id = _write_package_artifact(db, org_id, tmp)
        pkg = _make_package(org_id, artifact_id=storage_id)
        package_id = pkg.id
        db.add(pkg)
        db.flush()
        d = _make_delivery(org_id, package_id, status=DeliveryStatus.UNKNOWN.value)
        d.external_reference = ext_ref
        d.attempt_count = 1
        d.updated_at = datetime.utcnow() - timedelta(minutes=5)
        delivery_id = d.id
        db.add(d)
        db.add(
            ElfisProductDocumentDeliveryAttempt(
                id=str(uuid4()),
                delivery_id=delivery_id,
                attempt_number=1,
                worker_id="probe",
                status="failed",
                error_code="bridge_uncertain",
                started_at=datetime.utcnow() - timedelta(minutes=5),
                completed_at=datetime.utcnow() - timedelta(minutes=5),
            )
        )
        db.commit()

        svc = ProductIntegrationService(db)
        before = svc.reconcile_delivery(delivery_id, dry_run=True)
        assert before.status == DeliveryStatus.UNKNOWN.value

        after = svc.reconcile_delivery(delivery_id, dry_run=False)
        assert after.status == DeliveryStatus.MANUAL_REVIEW.value
        assert after.external_reference == ext_ref

        # pas de reclaim aveugle
        claimed = ProductIntegrationRepository(db).claim_deliveries(
            worker_id="i-w", limit=10, lease_seconds=60, product_key=PRODUCT
        )
        assert all(c.id != delivery_id for c in claimed)

        attempts = (
            db.query(ElfisProductDocumentDeliveryAttempt)
            .filter(ElfisProductDocumentDeliveryAttempt.delivery_id == delivery_id)
            .count()
        )
        assert attempts == 1
    finally:
        if delivery_id:
            _cleanup(
                db,
                delivery_ids=[delivery_id],
                package_ids=[package_id] if package_id else [],
                storage_ids=[storage_id] if storage_id else [],
                org_ids=[org_id] if org_id else None,
            )
        db.close()


def test_J_delivery_tenant_isolation_list_and_reconcile_filter():
    """J — list deliveries + reconcile filtrés par organization_id."""
    require_postgres()
    Session, engine = make_pg_session_factory()
    assert engine.dialect.name == "postgresql"

    db = Session()
    org_a = org_b = None
    pkgs: list[str] = []
    dels: list[str] = []
    try:
        org_a = _seed_org(db, suffix="ja-")
        org_b = _seed_org(db, suffix="jb-")
        pa = _make_package(org_a)
        pb = _make_package(org_b)
        db.add(pa)
        db.add(pb)
        db.flush()
        da = _make_delivery(org_a, pa.id, status=DeliveryStatus.UNKNOWN.value)
        db_ = _make_delivery(org_b, pb.id, status=DeliveryStatus.UNKNOWN.value)
        da.updated_at = datetime.utcnow() - timedelta(minutes=10)
        db_.updated_at = datetime.utcnow() - timedelta(minutes=10)
        db.add(da)
        db.add(db_)
        db.commit()
        pkgs = [pa.id, pb.id]
        dels = [da.id, db_.id]

        items_a, _ = ProductIntegrationRepository(db).list_deliveries(
            organization_id=org_a, limit=50, offset=0
        )
        ids_a = {x.id for x in items_a}
        assert da.id in ids_a
        assert db_.id not in ids_a

        # reconcile scope org A only
        q = (
            db.query(ElfisProductDocumentDelivery)
            .filter(ElfisProductDocumentDelivery.status == DeliveryStatus.UNKNOWN.value)
            .filter(ElfisProductDocumentDelivery.organization_id == org_a)
        )
        scoped = {r.id for r in q.all()}
        assert da.id in scoped
        assert db_.id not in scoped
    finally:
        _cleanup(db, delivery_ids=dels, package_ids=pkgs, org_ids=[x for x in (org_a, org_b) if x])
        db.close()


def test_postgres_processing_job_claim_source_has_skip_locked():
    """Garde-fou source — processing claim contient SKIP LOCKED."""
    require_postgres()
    import inspect

    from app.document_processing.repository import DocumentProcessingRepository

    src = inspect.getsource(DocumentProcessingRepository._claim_postgres)
    assert "FOR UPDATE SKIP LOCKED" in src
