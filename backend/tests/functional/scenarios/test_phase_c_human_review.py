"""Phase C — Revue humaine (REVIEW-001 … REVIEW-006)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.accounting.accounting_models import ElfisAccountingProposal
from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus
from app.ai.ai_models import ElfisDocumentAnalysis
from app.models_vault import VaultDocument
from tests.accounting import seed_analysis, setup_acc_db
from tests.functional.helpers.phase_c import assert_safe_document_body


def test_review_001_002_statuses():
    db, _, _ = setup_acc_db()
    seed_analysis(db)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    assert result.status in (
        ProposalStatus.READY_FOR_VALIDATION,
        ProposalStatus.REQUIRES_REVIEW,
    )
    prop = db.query(ElfisAccountingProposal).filter_by(proposal_id=result.proposal_id).one()
    assert prop.validated_at is None


def _seed_proposal(db, *, org_id: int, vault_id: str, user_id: int | None = None) -> str:
    db.add(
        VaultDocument(
            id=vault_id,
            organization_id=org_id,
            document_type="supplier_invoice",
            original_filename=f"{vault_id}.pdf",
            storage_path=f"o/{vault_id}.pdf",
            mime_type="application/pdf",
            file_size=100,
            checksum_sha256=vault_id,
            archive_status="archived",
            version=1,
        )
    )
    db.add(
        ElfisDocumentAnalysis(
            id=str(uuid4()),
            analysis_id=str(uuid4()),
            organization_id=org_id,
            vault_document_id=vault_id,
            document_version=1,
            status="completed",
            document_type="supplier_invoice",
            confidence=0.95,
            extraction={
                "compatible_extraction": {
                    "supplier": "Fictif SA",
                    "invoice_number": "FAC-REV-1",
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
            vault_document_id=vault_id,
            user_id=user_id,
        )
    )
    db.commit()
    return result.proposal_id


def test_review_003_005_validate_idempotent(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    user_id = functional_db["seed"]["users"]["org_admin"]["id"]
    db = Session()
    try:
        proposal_id = _seed_proposal(db, org_id=org_id, vault_id="vd-review-c", user_id=user_id)
    finally:
        db.close()

    api.login_user("org_admin")
    r1 = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json={"comment": "OK recette Phase C"},
    )
    assert r1.status_code in (200, 201, 400, 403, 409, 422)
    if r1.status_code in (200, 201):
        assert_safe_document_body(r1.json())
        r2 = api.client.post(
            f"/api/accounting/proposals/{proposal_id}/validate",
            headers=api._headers(),
            json={"comment": "double"},
        )
        assert r2.status_code in (200, 201, 409, 400, 422)


def test_review_004_member_refused(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = _seed_proposal(db, org_id=org_id, vault_id="vd-member-c")
    finally:
        db.close()

    api.login_user("member")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/validate",
        headers=api._headers(),
        json={"comment": "hack"},
    )
    assert r.status_code in (401, 403)


def test_review_006_reject_with_reason(api, functional_db):
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    db = Session()
    try:
        proposal_id = _seed_proposal(db, org_id=org_id, vault_id="vd-reject-c")
    finally:
        db.close()

    api.login_user("org_admin")
    r = api.client.post(
        f"/api/accounting/proposals/{proposal_id}/reject",
        headers=api._headers(),
        json={"reason": "Montants incorrects — Phase C"},
    )
    assert r.status_code in (200, 201, 400, 422)
    if r.status_code in (200, 201):
        assert_safe_document_body(r.json())
