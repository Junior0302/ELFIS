"""CONC-004 — Double validation : une seule transition (UPDATE atomique)."""

from __future__ import annotations

from app.accounting.accounting_models import ElfisAccountingProposal, ElfisAccountingReview
from app.accounting.accounting_schemas import AccountingValidationRequest
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus, ReviewAction
from tests.functional.helpers.phase_d import seed_accounting_proposal


def test_conc_004_accounting_validation_unique(functional_db, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_billing_enforce_entitlements", False)
    Session = functional_db["Session"]
    org_id = functional_db["seed"]["organizations"]["ORG_ACTIVE"]["id"]
    user_id = functional_db["seed"]["users"]["org_admin"]["id"]
    db = Session()
    try:
        proposal_id = seed_accounting_proposal(
            db, org_id=org_id, user_id=user_id, vault_id="vd-conc-val-f", force_ready=True
        )
    finally:
        db.close()

    body = AccountingValidationRequest(
        confirm_balanced_entry=True,
        confirm_document_reviewed=True,
        comment="Phase F concurrent",
    )

    s1 = Session()
    try:
        AccountingService(s1).validate_proposal(
            organization_id=org_id, proposal_id=proposal_id, user_id=user_id, body=body
        )
        s1.commit()
    finally:
        s1.close()

    s2 = Session()
    try:
        # Idempotent — déjà validée
        detail = AccountingService(s2).validate_proposal(
            organization_id=org_id, proposal_id=proposal_id, user_id=user_id, body=body
        )
        s2.commit()
        assert detail.status == ProposalStatus.VALIDATED
    finally:
        s2.close()

    s = Session()
    try:
        prop = s.query(ElfisAccountingProposal).filter_by(proposal_id=proposal_id).one()
        assert prop.status == ProposalStatus.VALIDATED
        reviews = (
            s.query(ElfisAccountingReview)
            .filter_by(proposal_id=proposal_id, action=ReviewAction.VALIDATED)
            .count()
        )
        assert reviews == 1
    finally:
        s.close()
