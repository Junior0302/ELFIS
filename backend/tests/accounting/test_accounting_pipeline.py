"""Tests pipeline Accounting."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus
from app.accounting.accounting_models import ElfisAccountingEntry, ElfisAccountingEntryLine
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from tests.accounting import seed_analysis, setup_acc_db


def test_create_proposal_and_balanced_entry():
    db, _, _ = setup_acc_db()
    seed_analysis(db)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(
            organization_id=1,
            user_id=1,
            vault_document_id="vd-acc",
            document_version=1,
        )
    )
    assert result.proposal_id
    assert result.status in (
        ProposalStatus.READY_FOR_VALIDATION,
        ProposalStatus.REQUIRES_REVIEW,
    )
    assert result.entry_id
    entry = db.query(ElfisAccountingEntry).filter_by(entry_id=result.entry_id).one()
    assert entry.balanced is True
    assert Decimal(str(entry.total_debit)) == Decimal(str(entry.total_credit))
    lines = db.query(ElfisAccountingEntryLine).filter_by(entry_id=entry.entry_id).all()
    assert len(lines) == 3


def test_idempotence():
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


def test_missing_analysis():
    db, _, _ = setup_acc_db()
    import pytest
    from app.accounting.accounting_exceptions import AccountingValidationError

    with pytest.raises(AccountingValidationError):
        AccountingService(db).create_proposal(
            AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
        )


def test_tenant_isolation():
    db, _, _ = setup_acc_db()
    seed_analysis(db)
    import pytest
    from app.accounting.accounting_exceptions import AccountingNotFoundError

    with pytest.raises(AccountingNotFoundError):
        AccountingService(db).create_proposal(
            AccountingPipelineRequest(organization_id=2, vault_document_id="vd-acc")
        )


def test_default_account_requires_review(monkeypatch):
    db, _, _ = setup_acc_db()
    seed_analysis(db, confidence=0.99)
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_accounting_require_review_on_default_account", True)
    monkeypatch.setattr(settings, "elfis_accounting_auto_ready_confidence", 0.5)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, user_id=1, vault_document_id="vd-acc")
    )
    assert result.requires_review is True
    assert result.status == ProposalStatus.REQUIRES_REVIEW


def test_low_confidence_review(monkeypatch):
    db, _, _ = setup_acc_db()
    seed_analysis(db, confidence=0.5)
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_accounting_auto_ready_confidence", 0.9)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    assert result.requires_review is True


def test_high_amount_review(monkeypatch):
    db, _, _ = setup_acc_db()
    seed_analysis(db, ht=10000, tva=2000, ttc=12000, confidence=0.99)
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_accounting_high_amount_review_threshold", 10000)
    monkeypatch.setattr(settings, "elfis_accounting_auto_ready_confidence", 0.5)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    assert "high_amount" in (
        AccountingService(db).get_proposal(organization_id=1, proposal_id=result.proposal_id).review_reasons
    )


def test_events_published():
    db, _, _ = setup_acc_db()
    seed_analysis(db)
    AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, user_id=1, vault_document_id="vd-acc")
    )
    names = {e.event_name for e in db.query(ElfisEvent).all()}
    assert EventNames.ACCOUNTING_PROPOSAL_CREATED in names
    assert (
        EventNames.ACCOUNTING_PROPOSAL_READY in names
        or EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW in names
    )
    for e in db.query(ElfisEvent).all():
        assert "lines" not in (e.payload or {})
        assert "pdf" not in (e.payload or {})
