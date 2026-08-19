"""Certification PostgreSQL Sprint 4.5 — preuve JSON."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from scripts.migration.certify_document_extraction_sprint4_postgres import (  # noqa: E402
    SPRINT3,
    SPRINT4,
    apply_sql_whole,
    drop_extraction,
    ensure_base,
    verify,
    _engine,
    _q,
)

OUT = BACKEND / "docs" / "migration" / "sprint4.5-postgres-certification.json"


def scenario_existing_active(eng: Engine) -> dict:
    with eng.begin() as c:
        org_id = c.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
        if not org_id:
            c.execute(text("INSERT INTO organizations (name) VALUES ('s45-cert')"))
            org_id = c.execute(
                text("SELECT id FROM organizations ORDER BY id DESC LIMIT 1")
            ).scalar()
        item_id = c.execute(
            text(
                "SELECT id FROM elfis_document_intake_items WHERE organization_id=:o LIMIT 1"
            ),
            {"o": org_id},
        ).scalar()
        if not item_id:
            item_id = str(uuid.uuid4())
            token = "tok-" + uuid.uuid4().hex[:24]
            try:
                c.execute(
                    text(
                        """
                        INSERT INTO elfis_document_intake_items (
                            id, intake_token, organization_id,
                            original_filename, normalized_filename, extension, format_id,
                            mime, size_bytes, checksum_sha256, status, origin, storage_key,
                            is_duplicate, extract_later, preview_allowed, analysis_allowed,
                            metadata, lifecycle_status, created_at, updated_at, uploaded_at
                        ) VALUES (
                            :id, :token, :org,
                            'cert.pdf', 'cert.pdf', '.pdf', 'pdf',
                            'application/pdf', 10, :checksum, 'ready_for_ai', 'api', :storage,
                            false, false, false, true,
                            '{}'::jsonb, 'ready_for_ai', NOW(), NOW(), NOW()
                        )
                        """
                    ),
                    {
                        "id": item_id,
                        "token": token,
                        "org": org_id,
                        "checksum": uuid.uuid4().hex + uuid.uuid4().hex[:32],
                        "storage": f"org/{org_id}/s45/{item_id}.pdf",
                    },
                )
            except Exception as exc:
                return {"ok": False, "skipped": True, "reason": type(exc).__name__}

    eid = str(uuid.uuid4())
    fp = "s45-proof-" + uuid.uuid4().hex[:16]
    with eng.begin() as c:
        c.execute(
            text(
                """
                INSERT INTO elfis_document_extractions (
                    id, organization_id, document_intake_item_id,
                    schema_name, schema_version, extraction_version,
                    status, status_scope, input_fingerprint,
                    structured_data, field_provenance, quality_summary,
                    warnings, errors, requires_human_review,
                    progress_percent, token_usage, version, created_at, updated_at
                ) VALUES (
                    :id, :org, :item,
                    'invoice.v1', '1.0.0', '1.0.0',
                    'awaiting_human_validation', 'active', :fp,
                    '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                    '[]'::jsonb, '[]'::jsonb, true,
                    100, '{}'::jsonb, 1, NOW(), NOW()
                )
                """
            ),
            {"id": eid, "org": org_id, "item": item_id, "fp": fp},
        )
    dup_ok = False
    try:
        with eng.begin() as c:
            c.execute(
                text(
                    """
                    INSERT INTO elfis_document_extractions (
                        id, organization_id, document_intake_item_id,
                        schema_name, schema_version, extraction_version,
                        status, status_scope, input_fingerprint,
                        structured_data, field_provenance, quality_summary,
                        warnings, errors, requires_human_review,
                        progress_percent, token_usage, version, created_at, updated_at
                    ) VALUES (
                        :id, :org, :item,
                        'invoice.v1', '1.0.0', '1.0.0',
                        'pending', 'active', :fp,
                        '{}'::jsonb, '{}'::jsonb, '{}'::jsonb,
                        '[]'::jsonb, '[]'::jsonb, true,
                        0, '{}'::jsonb, 1, NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "org": org_id,
                    "item": item_id,
                    "fp": fp,
                },
            )
    except Exception:
        dup_ok = True
    with eng.begin() as c:
        c.execute(
            text("DELETE FROM elfis_document_extractions WHERE input_fingerprint=:fp"),
            {"fp": fp},
        )
    return {"ok": dup_ok, "unique_enforced": dup_ok, "skipped": False}


def main() -> int:
    eng = _engine()
    ensure_base(eng)
    results = []

    drop_extraction(eng)
    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "A_empty", **verify(eng)})

    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "F_idempotent_replay", **verify(eng)})

    apply_sql_whole(eng, SPRINT3)
    apply_sql_whole(eng, SPRINT4)
    results.append({"scenario": "D_after_analysis", **verify(eng)})

    results.append({"scenario": "E_extraction_tables", **verify(eng)})
    results.append({"scenario": "H_active_unique", **scenario_existing_active(eng)})

    indexes = [
        r[0]
        for r in _q(
            eng,
            "SELECT indexname FROM pg_indexes WHERE tablename='elfis_document_extractions'",
        )
    ]
    fks = [
        r[0]
        for r in _q(
            eng,
            "SELECT conname FROM pg_constraint WHERE conrelid="
            "'elfis_document_extractions'::regclass AND contype='f'",
        )
    ]

    all_ok = all(r.get("ok") for r in results)
    report = {
        "certified": all_ok,
        "sprint": "4.5",
        "scenarios": results,
        "indexes": indexes,
        "foreign_keys": fks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ELFIS_ENVIRONMENT"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
