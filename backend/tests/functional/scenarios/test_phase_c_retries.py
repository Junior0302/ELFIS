"""Phase C — Retries / idempotence."""

from __future__ import annotations

from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.jobs.job_models import ElfisJob
from app.jobs.job_types import JobNames
from tests.accounting import seed_analysis, setup_acc_db
from tests.document_intelligence import make_text_pdf
from tests.functional.helpers.phase_c import doc_id_from_archive, drain_pipeline


def test_retry_idempotency_accounting_no_duplicate():
    db, _, _ = setup_acc_db()
    seed_analysis(db)
    svc = AccountingService(db)
    r1 = svc.create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    r2 = svc.create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    assert r1.proposal_id == r2.proposal_id
    assert r2.created is False


def test_idemp_001_event_replay_no_duplicate_extract_job(api, functional_db, mock_vault_storage, monkeypatch):
    from app.config import settings
    from app.events.event_bus import safe_publish
    from app.events.event_schemas import DomainEvent
    import uuid

    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    api.login_user("active")
    content = make_text_pdf("IDEMP EVENT PHASE C")
    body = api.upload_document(content, filename="idemp.pdf", expect=(200, 201))
    doc_id = doc_id_from_archive(body)

    Session = functional_db["Session"]
    db = Session()
    try:
        # Rejouer le même événement archivé (même idempotency_key)
        safe_publish(
            db,
            DomainEvent(
                event_name=EventNames.VAULT_DOCUMENT_ARCHIVED,
                organization_id=api.org_id,
                aggregate_type="vault_document",
                aggregate_id=doc_id,
                payload={
                    "vault_document_id": doc_id,
                    "version": 1,
                    "document_version": 1,
                },
                metadata={"source": "phase_c_replay"},
                correlation_id=uuid.uuid4(),
                idempotency_key=f"vault:archived:{api.org_id}:{doc_id}:1",
            ),
            commit=True,
        )
    finally:
        db.close()

    drain_pipeline(functional_db["Session"])
    db = Session()
    try:
        jobs = (
            db.query(ElfisJob)
            .filter(
                ElfisJob.organization_id == api.org_id,
                ElfisJob.job_name == JobNames.VAULT_DOCUMENT_EXTRACT_TEXT,
                ElfisJob.idempotency_key == f"document-text:{api.org_id}:{doc_id}:1",
            )
            .all()
        )
        assert len(jobs) <= 1
    finally:
        db.close()


def test_idemp_003_identical_upload_409(api, mock_vault_storage):
    api.login_user("active")
    content = make_text_pdf("SAME BYTES IDEMP")
    r1 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("a.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    r2 = api.client.post(
        "/api/vault/documents/archive",
        headers=api._headers(),
        files={"file": ("b.pdf", content, "application/pdf")},
        data={"tenant_id": str(api.org_id), "document_type": "supplier_invoice"},
    )
    assert r1.status_code in (200, 201)
    assert r2.status_code == 409
