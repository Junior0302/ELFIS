#!/usr/bin/env python
"""Validation staging RC2.4 étape 3 — Versioning, Retention & Controlled Deletion."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-sql", action="store_true")
    parser.add_argument("--db-only", action="store_true")
    parser.add_argument("--local-root", default="")
    args = parser.parse_args()

    from sqlalchemy import create_engine, inspect

    from app.config import settings

    engine = create_engine(settings.database_url)
    report: dict = {
        "database_url_scheme": settings.database_url.split(":", 1)[0],
        "note": "DB staging peut être PostgreSQL tandis que le provider local utilise un répertoire temporaire.",
        "checks": [],
    }

    if args.apply_sql:
        from scripts.rc1.migrate_sql import apply_sql_file

        for name in (
            "elfis_storage_documents_postgres.sql",
            "elfis_storage_documents_stage2_postgres.sql",
            "elfis_storage_documents_stage3_postgres.sql",
        ):
            apply_sql_file(engine, BACKEND / "sql" / name)
            report["checks"].append({"apply_sql": name, "ok": True})

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    required = {
        "elfis_storage_objects",
        "elfis_document_records",
        "elfis_document_links",
        "elfis_document_versions",
        "elfis_document_legal_holds",
        "elfis_document_tombstones",
    }
    missing = sorted(required - tables)
    report["checks"].append({"tables_missing": missing})
    if missing and args.db_only:
        report["status"] = "FAIL"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    if args.db_only:
        report["status"] = "PASS_DB_ONLY"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    root = Path(args.local_root) if args.local_root else Path(tempfile.mkdtemp(prefix="elfis-st3-"))
    root.mkdir(parents=True, exist_ok=True)
    report["local_root"] = str(root)

    from app.database import SessionLocal
    from app.storage.document_legal_hold_service import DocumentLegalHoldService
    from app.storage.document_registry_service import DocumentRegistryService
    from app.storage.document_retention_service import DocumentRetentionService
    from app.storage.document_version_service import DocumentVersionService
    from app.storage.providers.local_storage_provider import LocalStorageProvider
    from app.storage.storage_context import StorageContext
    from app.storage.storage_registry import clear_storage_provider_cache
    from app.models_saas import Organization, User

    clear_storage_provider_cache()
    provider = LocalStorageProvider(root=root)

    import app.storage.storage_service as ss

    ss.default_storage_context = lambda namespace="default": StorageContext(
        provider=provider, namespace=namespace
    )

    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        user = db.query(User).first()
        if not org or not user:
            report["status"] = "FAIL"
            report["checks"].append({"error": "no_org_or_user_for_probe"})
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1

        registry = DocumentRegistryService(db)
        doc = registry.create_from_upload(
            organization_id=org.id,
            filename="probe-stage3.pdf",
            content=b"%PDF-1.4 stage3-probe-v1\n%%EOF",
            declared_mime="application/pdf",
            owner_user_id=user.id,
            title="RC2.4-stage3-probe",
        )
        report["checks"].append({"create_v1": True, "document_id": doc.id, "version": doc.current_version_id})
        assert doc.current_version_id

        vsvc = DocumentVersionService(db, storage=registry.storage)
        v2 = vsvc.add_version_from_chunks_sync(
            document_id=doc.id,
            organization_id=org.id,
            filename="probe-stage3-v2.pdf",
            chunks=[b"%PDF-1.4 stage3-probe-v2\n%%EOF"],
            declared_mime="application/pdf",
            created_by_user_id=user.id,
        )
        report["checks"].append({"create_v2": True, "version_number": v2.version_number})

        registry.archive(document_id=doc.id, organization_id=org.id)
        registry.unarchive(document_id=doc.id, organization_id=org.id)
        report["checks"].append({"archive_unarchive": True})

        registry.soft_delete(document_id=doc.id, organization_id=org.id, actor_user_id=user.id)
        registry.restore_soft_deleted(document_id=doc.id, organization_id=org.id, actor_user_id=user.id)
        report["checks"].append({"soft_delete_restore": True})

        holds = DocumentLegalHoldService(db)
        hold = holds.place(
            document_id=doc.id,
            organization_id=org.id,
            reason="staging probe hold",
            placed_by_user_id=user.id,
        )
        registry.soft_delete(document_id=doc.id, organization_id=org.id)
        db.refresh(doc)
        doc.retention_deadline = datetime.utcnow() - timedelta(days=1)
        db.commit()

        ret = DocumentRetentionService(db, provider=provider)
        decision = ret.explain_retention_decision(doc)
        assert decision.blocked_reason == "legal_hold"
        report["checks"].append({"purge_blocked_by_hold": True})

        holds.release(document_id=doc.id, hold_id=hold.id, organization_id=org.id)
        purged = ret.purge_candidates(dry_run=False, batch_size=1, reason="stage3_probe")
        report["checks"].append({"purge_probe": purged})

        from app.storage.storage_repository import TombstoneRepository

        tomb = TombstoneRepository(db).get_by_document(doc.id)
        report["checks"].append({"tombstone": bool(tomb)})
        report["status"] = "PASS" if purged.get("purged", 0) >= 1 and tomb else "FAIL"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 1
    except Exception as exc:  # noqa: BLE001
        report["status"] = "FAIL"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
