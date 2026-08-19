"""Concurrence réelle PostgreSQL — Document Extraction Sprint 4.5."""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from tests.concurrency.postgres_helpers import (
    ensure_postgres_test_env,
    postgres_tests_enabled,
    postgres_url,
)

pytestmark = pytest.mark.skipif(
    not postgres_tests_enabled(),
    reason="ELFIS_POSTGRES_TESTS_ENABLED requis",
)

JOIN_TIMEOUT = 30
BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pg_engine():
    ensure_postgres_test_env()
    os.environ["ELFIS_ENVIRONMENT"] = "staging"
    os.environ["APP_ENV"] = "staging"
    os.environ.setdefault("ELFIS_RC1_ALLOW_MANAGED_HOST", "true")
    from scripts.rc1.safety import assert_safe_postgres_url, assert_safe_rc1_environment
    from scripts.migration.certify_document_extraction_sprint4_postgres import (
        apply_sql_whole,
        ensure_base,
        verify,
    )

    url = postgres_url()
    assert_safe_rc1_environment()
    assert_safe_postgres_url(url)
    eng = create_engine(url, pool_pre_ping=True, connect_args={"prepare_threshold": None})
    ensure_base(eng)
    sql = BACKEND / "sql" / "elfis_document_extraction_sprint4_postgres.sql"
    apply_sql_whole(eng, sql)
    v = verify(eng)
    if not v.get("ok"):
        pytest.skip(f"tables extraction absentes: {v}")
    yield eng
    eng.dispose()


def _seed_intake_item(c, org_id: int) -> str:
    item_id = str(uuid.uuid4())
    token = "tok-" + uuid.uuid4().hex[:24]
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
                'conc.pdf', 'conc.pdf', '.pdf', 'pdf',
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
    return item_id


def _ensure_org_item(eng):
    with eng.begin() as c:
        org_id = c.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
        if not org_id:
            c.execute(text("INSERT INTO organizations (name) VALUES ('s45-conc')"))
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
            try:
                item_id = _seed_intake_item(c, org_id)
            except Exception:
                return None, None
        return org_id, item_id


def test_unique_active_fingerprint_constraint(pg_engine):
    """Deux inserts actifs même fingerprint → un seul gagne."""
    org_id, item_id = _ensure_org_item(pg_engine)
    if not org_id or not item_id:
        pytest.skip("impossible de semer org/item staging")

    Session = sessionmaker(bind=pg_engine)
    fp = "sprint45-fp-" + uuid.uuid4().hex
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    errors: list[str] = []
    barrier = threading.Barrier(2, timeout=JOIN_TIMEOUT)

    def worker(eid: str) -> None:
        s = Session()
        try:
            barrier.wait()
            s.execute(
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
                {"id": eid, "org": org_id, "item": item_id, "fp": fp},
            )
            s.commit()
        except Exception as exc:
            s.rollback()
            errors.append(type(exc).__name__)
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join(JOIN_TIMEOUT)

    with pg_engine.connect() as c:
        count = c.execute(
            text(
                "SELECT COUNT(*) FROM elfis_document_extractions "
                "WHERE organization_id=:o AND input_fingerprint=:fp AND status_scope='active'"
            ),
            {"o": org_id, "fp": fp},
        ).scalar()
        c.execute(
            text("DELETE FROM elfis_document_extractions WHERE input_fingerprint=:fp"),
            {"fp": fp},
        )
        c.commit()

    assert count == 1
    assert errors, "au moins une IntegrityError attendue"
