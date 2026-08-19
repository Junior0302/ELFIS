"""Tests service validate / reject / reopen / update."""

from __future__ import annotations

import pytest

from app.accounting.accounting_exceptions import AccountingStateError, AccountingValidationError
from app.accounting.accounting_schemas import (
    AccountingPipelineRequest,
    AccountingProposalUpdate,
    AccountingRejectionRequest,
    AccountingValidationRequest,
)
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus
from tests.accounting import seed_analysis, setup_acc_db


def _proposal(db):
    seed_analysis(db, confidence=0.99)
    from app.config import settings
    import app.config as cfg

    # Forcer ready si possible
    return AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, user_id=1, vault_document_id="vd-acc")
    )


def test_validate_and_block_edit():
    db, _, _ = setup_acc_db()
    r = _proposal(db)
    svc = AccountingService(db)
    # Forcer état ready
    from app.accounting.accounting_repository import AccountingRepository

    row = AccountingRepository(db).find_proposal(r.proposal_id)
    row.status = ProposalStatus.READY_FOR_VALIDATION
    row.requires_review = False
    AccountingRepository(db).save_proposal(row)

    detail = svc.validate_proposal(
        organization_id=1,
        proposal_id=r.proposal_id,
        user_id=1,
        body=AccountingValidationRequest(
            confirm_balanced_entry=True,
            confirm_document_reviewed=True,
        ),
    )
    assert detail.status == ProposalStatus.VALIDATED
    with pytest.raises(AccountingStateError):
        svc.update_proposal(
            organization_id=1,
            proposal_id=r.proposal_id,
            user_id=1,
            data=AccountingProposalUpdate(document_number="X"),
        )


def test_validate_requires_confirmations():
    db, _, _ = setup_acc_db()
    r = _proposal(db)
    from app.accounting.accounting_repository import AccountingRepository

    row = AccountingRepository(db).find_proposal(r.proposal_id)
    row.status = ProposalStatus.READY_FOR_VALIDATION
    AccountingRepository(db).save_proposal(row)
    with pytest.raises(AccountingValidationError):
        AccountingService(db).validate_proposal(
            organization_id=1,
            proposal_id=r.proposal_id,
            user_id=1,
            body=AccountingValidationRequest(
                confirm_balanced_entry=False,
                confirm_document_reviewed=True,
            ),
        )


def test_reject_and_reopen():
    db, _, _ = setup_acc_db()
    r = _proposal(db)
    svc = AccountingService(db)
    detail = svc.reject_proposal(
        organization_id=1,
        proposal_id=r.proposal_id,
        user_id=1,
        body=AccountingRejectionRequest(reason="Montants incorrects"),
    )
    assert detail.status == ProposalStatus.REJECTED
    reopened = svc.reopen_proposal(
        organization_id=1, proposal_id=r.proposal_id, user_id=1, comment="corriger"
    )
    assert reopened.status == ProposalStatus.REQUIRES_REVIEW
    history = svc.get_review_history(organization_id=1, proposal_id=r.proposal_id)
    actions = {h.action for h in history}
    assert "rejected" in actions
    assert "reopened" in actions


def test_update_recalculates():
    db, _, _ = setup_acc_db()
    r = _proposal(db)
    svc = AccountingService(db)
    detail = svc.update_proposal(
        organization_id=1,
        proposal_id=r.proposal_id,
        user_id=1,
        data=AccountingProposalUpdate(document_number="F-NEW", amount_ttc=120),
    )
    assert detail.document_number == "F-NEW"
    assert "manual_modification" in detail.review_reasons or detail.requires_review
