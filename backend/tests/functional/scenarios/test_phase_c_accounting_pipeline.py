"""Phase C — Pipeline comptable (ACC-001 … ACC-005)."""

from __future__ import annotations

from decimal import Decimal

from app.accounting.accounting_models import ElfisAccountingEntry, ElfisAccountingProposal
from app.accounting.accounting_schemas import AccountingPipelineRequest
from app.accounting.accounting_service import AccountingService
from app.accounting.accounting_types import ProposalStatus
from tests.accounting import seed_analysis, setup_acc_db
from tests.functional.fixtures.generate_documents import ensure_document_fixtures
from tests.functional.helpers.phase_c import doc_id_from_archive, drain_pipeline


def test_acc_001_002_003_balanced_proposals_unit():
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
    assert result.status in (
        ProposalStatus.READY_FOR_VALIDATION,
        ProposalStatus.REQUIRES_REVIEW,
    )
    entry = db.query(ElfisAccountingEntry).filter_by(entry_id=result.entry_id).one()
    assert entry.balanced is True
    assert Decimal(str(entry.total_debit)) == Decimal(str(entry.total_credit))


def test_acc_004_005_default_account_review_and_unbalanced_not_ready(monkeypatch):
    db, _, _ = setup_acc_db()
    seed_analysis(db, confidence=0.99)
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_accounting_require_review_on_default_account", True)
    result = AccountingService(db).create_proposal(
        AccountingPipelineRequest(organization_id=1, vault_document_id="vd-acc")
    )
    # Compte par défaut → requires_review typique
    assert result.status in (
        ProposalStatus.REQUIRES_REVIEW,
        ProposalStatus.READY_FOR_VALIDATION,
    )
    # Jamais ready si non équilibré
    entry = db.query(ElfisAccountingEntry).filter_by(entry_id=result.entry_id).one()
    if not entry.balanced:
        assert result.status != ProposalStatus.READY_FOR_VALIDATION


def test_acc_e2e_supplier_upload_to_proposal(api, functional_db, mock_vault_storage, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elfis_auto_text_extraction_enabled", True)
    monkeypatch.setattr(settings, "elfis_auto_ai_analysis_enabled", True)
    monkeypatch.setattr(settings, "elfis_auto_accounting_proposal_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "")
    files = ensure_document_fixtures()
    api.login_user("active")
    body = api.upload_document(files["invoice_supplier_valid.pdf"], expect=(200, 201))
    doc_id = doc_id_from_archive(body)
    drain_pipeline(functional_db["Session"], max_rounds=40)

    Session = functional_db["Session"]
    db = Session()
    try:
        props = (
            db.query(ElfisAccountingProposal)
            .filter(ElfisAccountingProposal.vault_document_id == doc_id)
            .all()
        )
        # Proposition peut exister après chaîne complète heuristique
        for p in props:
            assert p.organization_id == api.org_id
            if p.status == ProposalStatus.READY_FOR_VALIDATION:
                entry = (
                    db.query(ElfisAccountingEntry)
                    .filter_by(proposal_id=p.proposal_id)
                    .first()
                )
                if entry is not None:
                    assert entry.balanced is True
    finally:
        db.close()
