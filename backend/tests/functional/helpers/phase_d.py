"""Helpers Phase D — validation comptable, Delivery, notifications, Search."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.accounting.accounting_models import ElfisAccountingProposal
from app.accounting.accounting_repository import AccountingRepository
from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus
from app.ai.ai_models import ElfisDocumentAnalysis
from app.models_vault import VaultDocument
from app.services.billing import create_sales_document
from tests.functional.helpers.phase_c import assert_safe_document_body, install_mock_vault_storage

assert_safe_phase_d_body = assert_safe_document_body


VALIDATE_BODY = {
    "confirm_balanced_entry": True,
    "confirm_document_reviewed": True,
    "comment": "Validation Phase D",
}


def force_ready_for_validation(db: Session, proposal_id: str) -> ElfisAccountingProposal:
    """Force le statut ready (politique V1 : requires_review reste validable aussi)."""
    repo = AccountingRepository(db)
    row = repo.find_proposal(proposal_id)
    assert row is not None
    row.status = ProposalStatus.READY_FOR_VALIDATION
    row.requires_review = False
    row.review_reasons = []
    db.commit()
    return row


def seed_accounting_proposal(
    db: Session,
    *,
    org_id: int,
    vault_id: str | None = None,
    user_id: int | None = None,
    force_ready: bool = True,
) -> str:
    vid = vault_id or f"vd-phase-d-{uuid4().hex[:10]}"
    existing = db.get(VaultDocument, vid)
    if existing is None:
        db.add(
            VaultDocument(
                id=vid,
                organization_id=org_id,
                document_type="supplier_invoice",
                original_filename=f"{vid}.pdf",
                storage_path=f"o/{vid}.pdf",
                mime_type="application/pdf",
                file_size=100,
                checksum_sha256=vid,
                archive_status="archived",
                version=1,
            )
        )
    db.add(
        ElfisDocumentAnalysis(
            id=str(uuid4()),
            analysis_id=str(uuid4()),
            organization_id=org_id,
            vault_document_id=vid,
            document_version=1,
            status="completed",
            document_type="supplier_invoice",
            confidence=0.95,
            extraction={
                "compatible_extraction": {
                    "supplier": "Fournisseur Phase D SA",
                    "invoice_number": f"FAC-D-{vid[-6:]}",
                    "invoice_date": "2026-07-01",
                    "amount_ht": 100,
                    "amount_tva": 20,
                    "amount_ttc": 120,
                    "vat_rate": 20,
                    "currency": "EUR",
                    "document_type": "supplier_invoice",
                }
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db.commit()
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(
            organization_id=org_id,
            vault_document_id=vid,
            user_id=user_id,
        )
    )
    db.commit()
    if force_ready:
        force_ready_for_validation(db, result.proposal_id)
    return result.proposal_id


def seed_sales_doc(
    db: Session,
    *,
    org_id: int,
    doc_type: str = "facture",
    customer_email: str = "client.phase.d@test.elfis.local",
    customer_name: str = "Client Phase D",
    amount_ht: float = 100.0,
):
    return create_sales_document(
        db,
        organization_id=org_id,
        doc_type=doc_type,
        customer_name=customer_name,
        customer_email=customer_email,
        amount_ht=amount_ht,
        vat_rate=20.0,
    )


def install_mock_mailer(monkeypatch) -> list[dict[str, Any]]:
    """Intercepte Brevo/httpx — aucun e-mail réel. Retourne la liste des appels."""
    from app import config
    from app.services import mailer as mailer_mod

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("a" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")
    monkeypatch.setattr(config.settings, "platform_email_from_name", "ComptaPilot")
    monkeypatch.setattr(config.settings, "supabase_url", "https://mock.supabase.test")
    monkeypatch.setattr(config.settings, "supabase_service_role_key", "mock-service-role")

    calls: list[dict[str, Any]] = []

    class FakeResponse:
        status_code = 201
        text = '{"messageId":"msg-phase-d"}'

        def json(self):
            return {"messageId": "msg-phase-d"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        calls.append({"url": url, "json": json, "headers": headers or {}})
        return FakeResponse()

    monkeypatch.setattr(mailer_mod.httpx, "post", fake_post)
    # Vault storage déjà mocké via fixture api ; s'assurer aussi DI path
    return calls


def patch_mailer_fail_then_succeed(monkeypatch, *, fail_count: int = 1) -> list[dict[str, Any]]:
    from app import config
    from app.services import mailer as mailer_mod

    monkeypatch.setattr(config.settings, "brevo_api_key", "xkeysib-" + ("b" * 40))
    monkeypatch.setattr(config.settings, "platform_email_from", "documents@elfiscore.com")

    state = {"n": 0}
    calls: list[dict[str, Any]] = []

    class OkResponse:
        status_code = 201
        text = '{"messageId":"msg-retry-ok"}'

        def json(self):
            return {"messageId": "msg-retry-ok"}

    def fake_post(url, headers=None, json=None, timeout=None):  # noqa: ANN001
        state["n"] += 1
        calls.append({"attempt": state["n"], "json": json})
        if state["n"] <= fail_count:
            raise RuntimeError("mock_mailer_temporary")
        return OkResponse()

    monkeypatch.setattr(mailer_mod.httpx, "post", fake_post)
    return calls
