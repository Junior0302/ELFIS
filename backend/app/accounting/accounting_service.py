"""AccountingService — API métier propositions."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.accounting_exceptions import (
    AccountingNotFoundError,
    AccountingPermissionError,
    AccountingStateError,
    AccountingValidationError,
)
from app.accounting.accounting_models import (
    ElfisAccountingEntryLine,
    ElfisAccountingProposal,
    ElfisAccountingReview,
)
from app.accounting.accounting_pipeline import AccountingPipeline
from app.accounting.accounting_repository import AccountingRepository
from app.accounting.accounting_schemas import (
    AccountingEntryLineView,
    AccountingEntryView,
    AccountingPipelineRequest,
    AccountingProposalDetail,
    AccountingProposalListItem,
    AccountingProposalResult,
    AccountingProposalUpdate,
    AccountingRejectionRequest,
    AccountingReviewView,
    AccountingValidationRequest,
)
from app.accounting.accounting_security import (
    assert_account_code,
    assert_comment,
    assert_description,
    assert_line_count,
    balance_tolerance,
    to_decimal,
)
from app.accounting.accounting_types import (
    EntryStatus,
    ProposalStage,
    ProposalStatus,
    ReviewAction,
)
from app.accounting.stages.review_stage import determine_review_status
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
import uuid as _uuid


class AccountingService:
    def __init__(self, db: Session):
        self._db = db
        self._repo = AccountingRepository(db)
        self._pipeline = AccountingPipeline(db)

    def create_proposal(self, request: AccountingPipelineRequest) -> AccountingProposalResult:
        from app.billing.billing_exceptions import FeatureNotAvailableError
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.accounting.accounting_exceptions import AccountingValidationError

        try:
            EntitlementService(self._db).require(
                request.organization_id, FeatureCodes.ACCOUNTING_PROPOSALS
            )
        except FeatureNotAvailableError as exc:
            raise AccountingPermissionError(str(exc.message)) from exc
        return self._pipeline.process(request)

    def get_proposal(
        self, *, organization_id: int, proposal_id: str
    ) -> AccountingProposalDetail:
        row = self._require_proposal(organization_id, proposal_id)
        return self._to_detail(row)

    def list_proposals(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        document_type: str | None = None,
        requires_review: bool | None = None,
        date_from=None,
        date_to=None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AccountingProposalListItem], int]:
        rows, total = self._repo.list_proposals(
            organization_id=organization_id,
            status=status,
            document_type=document_type,
            requires_review=requires_review,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        items = [
            AccountingProposalListItem(
                proposal_id=r.proposal_id,
                vault_document_id=r.vault_document_id,
                document_type=r.document_type,
                document_number=r.document_number,
                supplier_name=r.supplier_name,
                customer_name=r.customer_name,
                amount_ttc=float(r.amount_ttc) if r.amount_ttc is not None else None,
                currency=r.currency or "EUR",
                status=r.status,
                confidence=float(r.confidence) if r.confidence is not None else None,
                requires_review=bool(r.requires_review),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
        return items, total

    def update_proposal(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        user_id: int,
        data: AccountingProposalUpdate,
    ) -> AccountingProposalDetail:
        row = self._require_proposal(organization_id, proposal_id)
        if row.status == ProposalStatus.VALIDATED:
            raise AccountingStateError("Proposition validée — reopen requis")
        if row.status in (ProposalStatus.REJECTED, ProposalStatus.CANCELLED):
            raise AccountingStateError("Proposition non modifiable dans cet état")

        previous = {
            "amount_ht": float(row.amount_ht) if row.amount_ht is not None else None,
            "amount_vat": float(row.amount_vat) if row.amount_vat is not None else None,
            "amount_ttc": float(row.amount_ttc) if row.amount_ttc is not None else None,
            "document_number": row.document_number,
        }
        if data.document_number is not None:
            row.document_number = data.document_number[:128]
        if data.document_date is not None:
            row.document_date = data.document_date
        if data.due_date is not None:
            row.due_date = data.due_date
        if data.supplier_name is not None:
            row.supplier_name = data.supplier_name[:255]
        if data.customer_name is not None:
            row.customer_name = data.customer_name[:255]
        if data.amount_ht is not None:
            row.amount_ht = to_decimal(data.amount_ht)
        if data.amount_vat is not None:
            row.amount_vat = to_decimal(data.amount_vat)
        if data.amount_ttc is not None:
            row.amount_ttc = to_decimal(data.amount_ttc)
        if data.currency is not None:
            row.currency = data.currency[:8]

        entry = self._repo.find_active_entry(row.proposal_id)
        if entry and data.journal_code:
            entry.journal_code = data.journal_code[:16]
        if entry and data.description is not None:
            entry.description = assert_description(data.description)

        if data.lines is not None:
            assert_line_count(len(data.lines))
            if entry is None:
                raise AccountingValidationError("Aucune écriture à mettre à jour")
            self._repo.delete_lines(entry.entry_id)
            total_d = Decimal("0")
            total_c = Decimal("0")
            for idx, line in enumerate(data.lines, start=1):
                debit = to_decimal(line.debit)
                credit = to_decimal(line.credit)
                if debit > 0 and credit > 0:
                    raise AccountingValidationError("Ligne avec débit et crédit simultanés")
                code = assert_account_code(line.account_code)
                total_d += debit
                total_c += credit
                self._repo.save_line(
                    ElfisAccountingEntryLine(
                        id=str(uuid.uuid4()),
                        line_id=str(uuid.uuid4()),
                        organization_id=organization_id,
                        entry_id=entry.entry_id,
                        line_number=idx,
                        account_code=code,
                        account_label=line.account_label,
                        third_party_name=line.third_party_name,
                        debit=debit,
                        credit=credit,
                        vat_rate=line.vat_rate,
                        vat_code=line.vat_code,
                        description=assert_description(line.description) if line.description else None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    ),
                    commit=False,
                )
            entry.total_debit = total_d
            entry.total_credit = total_c
            entry.balanced = abs(total_d - total_c) <= balance_tolerance()
            mapping = dict(row.accounting_mapping or {})
            mapping["balanced"] = entry.balanced
            mapping["total_debit"] = float(total_d)
            mapping["total_credit"] = float(total_c)
            mapping["status"] = "ok" if entry.balanced else "unbalanced"
            row.accounting_mapping = mapping
            self._repo.save_entry(entry, commit=False)

        requires_review, reasons, _ = determine_review_status(
            confidence=float(row.confidence) if row.confidence is not None else None,
            document_validation=row.document_validation or {},
            financial_validation=row.financial_validation or {},
            mapping=row.accounting_mapping or {},
            amount_ttc=row.amount_ttc,
            document_type_supported=True,
            manual_edit=True,
        )
        row.requires_review = requires_review
        row.review_reasons = reasons
        if entry and not entry.balanced:
            row.status = ProposalStatus.MAPPING_FAILED
        elif requires_review:
            row.status = ProposalStatus.REQUIRES_REVIEW
        else:
            row.status = ProposalStatus.READY_FOR_VALIDATION
        self._repo.save_proposal(row)

        self._repo.add_review(
            ElfisAccountingReview(
                id=str(uuid.uuid4()),
                review_id=str(uuid.uuid4()),
                organization_id=organization_id,
                proposal_id=row.proposal_id,
                user_id=user_id,
                action=ReviewAction.EDITED,
                previous_data=previous,
                new_data={
                    "amount_ttc": float(row.amount_ttc) if row.amount_ttc is not None else None,
                    "document_number": row.document_number,
                },
                comment=assert_comment(data.comment),
                created_at=datetime.utcnow(),
            )
        )
        self._publish(EventNames.ACCOUNTING_PROPOSAL_UPDATED, row)
        return self._to_detail(row)

    def validate_proposal(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        user_id: int,
        body: AccountingValidationRequest,
    ) -> AccountingProposalDetail:
        from app.billing.billing_exceptions import FeatureNotAvailableError
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService

        try:
            EntitlementService(self._db).require(organization_id, FeatureCodes.ACCOUNTING_VALIDATION)
        except FeatureNotAvailableError as exc:
            raise AccountingPermissionError(str(exc.message)) from exc
        row = self._require_proposal(organization_id, proposal_id)
        if row.status == ProposalStatus.VALIDATED:
            return self._to_detail(row)
        if row.status not in (
            ProposalStatus.READY_FOR_VALIDATION,
            ProposalStatus.REQUIRES_REVIEW,
        ):
            raise AccountingStateError("Proposition non validable dans cet état")
        if not body.confirm_balanced_entry or not body.confirm_document_reviewed:
            raise AccountingValidationError("Confirmations requises pour valider")

        entry = self._repo.find_active_entry(row.proposal_id)
        if not entry or not entry.balanced:
            raise AccountingValidationError("Écriture déséquilibrée — validation impossible")

        # Transition atomique : une seule validation concurrente gagne.
        from sqlalchemy import update as sa_update

        now = datetime.utcnow()
        claimed = self._db.execute(
            sa_update(ElfisAccountingProposal)
            .where(
                ElfisAccountingProposal.proposal_id == row.proposal_id,
                ElfisAccountingProposal.organization_id == organization_id,
                ElfisAccountingProposal.status.in_(
                    (
                        ProposalStatus.READY_FOR_VALIDATION,
                        ProposalStatus.REQUIRES_REVIEW,
                    )
                ),
            )
            .values(
                status=ProposalStatus.VALIDATED,
                current_stage=ProposalStage.COMPLETED,
                validated_at=now,
                validated_by_user_id=user_id,
                requires_review=False,
            )
        )
        if claimed.rowcount == 0:
            self._db.refresh(row)
            if row.status == ProposalStatus.VALIDATED:
                return self._to_detail(row)
            raise AccountingStateError("Proposition non validable dans cet état")

        self._db.refresh(row)
        entry.status = EntryStatus.VALIDATED
        entry.validated_at = now
        self._repo.save_entry(entry)
        self._repo.add_review(
            ElfisAccountingReview(
                id=str(uuid.uuid4()),
                review_id=str(uuid.uuid4()),
                organization_id=organization_id,
                proposal_id=row.proposal_id,
                user_id=user_id,
                action=ReviewAction.VALIDATED,
                comment=assert_comment(body.comment),
                created_at=now,
            )
        )
        self._publish(EventNames.ACCOUNTING_PROPOSAL_VALIDATED, row)
        return self._to_detail(row)

    def reject_proposal(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        user_id: int,
        body: AccountingRejectionRequest,
    ) -> AccountingProposalDetail:
        row = self._require_proposal(organization_id, proposal_id)
        if row.status == ProposalStatus.VALIDATED:
            raise AccountingStateError("Reopen requis avant rejet d'une proposition validée")
        row.status = ProposalStatus.REJECTED
        row.rejected_at = datetime.utcnow()
        row.rejected_by_user_id = user_id
        row.rejection_reason = assert_comment(body.reason) or body.reason[:2000]
        self._repo.save_proposal(row)
        entry = self._repo.find_active_entry(row.proposal_id)
        if entry and entry.status != EntryStatus.VALIDATED:
            entry.status = EntryStatus.CANCELLED
            self._repo.save_entry(entry)
        self._repo.add_review(
            ElfisAccountingReview(
                id=str(uuid.uuid4()),
                review_id=str(uuid.uuid4()),
                organization_id=organization_id,
                proposal_id=row.proposal_id,
                user_id=user_id,
                action=ReviewAction.REJECTED,
                comment=assert_comment(body.comment) or body.reason[:500],
                created_at=datetime.utcnow(),
            )
        )
        self._publish(EventNames.ACCOUNTING_PROPOSAL_REJECTED, row)
        return self._to_detail(row)

    def reopen_proposal(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        user_id: int,
        comment: str | None = None,
    ) -> AccountingProposalDetail:
        row = self._require_proposal(organization_id, proposal_id)
        if row.status not in (
            ProposalStatus.VALIDATED,
            ProposalStatus.REJECTED,
        ):
            raise AccountingStateError("Seules les propositions validées ou rejetées peuvent être rouvertes")
        row.status = ProposalStatus.REQUIRES_REVIEW
        row.validated_at = None
        row.rejected_at = None
        row.validated_by_user_id = None
        row.rejected_by_user_id = None
        row.rejection_reason = None
        row.requires_review = True
        reasons = list(row.review_reasons or [])
        if "reopened" not in reasons:
            reasons.append("reopened")
        row.review_reasons = reasons
        self._repo.save_proposal(row)
        entry = self._repo.find_active_entry(row.proposal_id)
        if entry and entry.status == EntryStatus.VALIDATED:
            entry.status = EntryStatus.PROPOSED
            entry.validated_at = None
            self._repo.save_entry(entry)
        self._repo.add_review(
            ElfisAccountingReview(
                id=str(uuid.uuid4()),
                review_id=str(uuid.uuid4()),
                organization_id=organization_id,
                proposal_id=row.proposal_id,
                user_id=user_id,
                action=ReviewAction.REOPENED,
                comment=assert_comment(comment),
                created_at=datetime.utcnow(),
            )
        )
        self._publish(EventNames.ACCOUNTING_PROPOSAL_REOPENED, row)
        return self._to_detail(row)

    def get_review_history(
        self, *, organization_id: int, proposal_id: str
    ) -> list[AccountingReviewView]:
        row = self._require_proposal(organization_id, proposal_id)
        reviews = self._repo.list_reviews(row.proposal_id)
        return [
            AccountingReviewView(
                review_id=r.review_id,
                action=r.action,
                comment=r.comment,
                user_id=r.user_id,
                created_at=r.created_at,
            )
            for r in reviews
        ]

    def _require_proposal(self, organization_id: int, proposal_id: str) -> ElfisAccountingProposal:
        row = self._repo.find_proposal(proposal_id)
        if not row or row.organization_id != organization_id:
            raise AccountingNotFoundError()
        return row

    def _to_detail(self, row: ElfisAccountingProposal) -> AccountingProposalDetail:
        entry = self._repo.find_active_entry(row.proposal_id)
        entry_view = None
        if entry:
            lines = self._repo.list_lines(entry.entry_id)
            entry_view = AccountingEntryView(
                entry_id=entry.entry_id,
                journal_code=entry.journal_code,
                entry_date=entry.entry_date,
                reference=entry.reference,
                description=entry.description,
                currency=entry.currency,
                total_debit=float(entry.total_debit or 0),
                total_credit=float(entry.total_credit or 0),
                balanced=bool(entry.balanced),
                status=entry.status,
                lines=[
                    AccountingEntryLineView(
                        line_id=ln.line_id,
                        line_number=ln.line_number,
                        account_code=ln.account_code,
                        account_label=ln.account_label,
                        third_party_name=ln.third_party_name,
                        debit=float(ln.debit or 0),
                        credit=float(ln.credit or 0),
                        vat_rate=float(ln.vat_rate) if ln.vat_rate is not None else None,
                        description=ln.description,
                    )
                    for ln in lines
                ],
            )
        reviews = self.get_review_history(
            organization_id=row.organization_id, proposal_id=row.proposal_id
        )
        actions = self._allowed_actions(row)
        return AccountingProposalDetail(
            proposal_id=row.proposal_id,
            vault_document_id=row.vault_document_id,
            document_analysis_id=row.document_analysis_id,
            document_version=row.document_version,
            document_type=row.document_type,
            document_number=row.document_number,
            document_date=row.document_date,
            due_date=row.due_date,
            supplier_name=row.supplier_name,
            customer_name=row.customer_name,
            currency=row.currency or "EUR",
            amount_ht=float(row.amount_ht) if row.amount_ht is not None else None,
            amount_vat=float(row.amount_vat) if row.amount_vat is not None else None,
            amount_ttc=float(row.amount_ttc) if row.amount_ttc is not None else None,
            status=row.status,
            current_stage=row.current_stage,
            confidence=float(row.confidence) if row.confidence is not None else None,
            requires_review=bool(row.requires_review),
            review_reasons=list(row.review_reasons or []),
            document_validation=dict(row.document_validation or {}),
            financial_validation=dict(row.financial_validation or {}),
            accounting_mapping={
                k: v
                for k, v in (row.accounting_mapping or {}).items()
                if k != "lines"  # lines via entry
            },
            quality_summary=dict(row.quality_summary or {}),
            entry=entry_view,
            reviews=reviews[:20],
            allowed_actions=actions,
            created_at=row.created_at,
            updated_at=row.updated_at,
            validated_at=row.validated_at,
            rejected_at=row.rejected_at,
        )

    def _allowed_actions(self, row: ElfisAccountingProposal) -> list[str]:
        if row.status == ProposalStatus.VALIDATED:
            return ["reopen", "view"]
        if row.status == ProposalStatus.REJECTED:
            return ["reopen", "view"]
        if row.status in (
            ProposalStatus.READY_FOR_VALIDATION,
            ProposalStatus.REQUIRES_REVIEW,
            ProposalStatus.MAPPING_FAILED,
            ProposalStatus.FINANCIAL_ERROR,
            ProposalStatus.VALIDATION_FAILED,
        ):
            return ["view", "edit", "validate", "reject"]
        return ["view"]

    def _publish(self, event_name: str, proposal: ElfisAccountingProposal) -> None:
        entry = self._repo.find_active_entry(proposal.proposal_id)
        safe_publish(
            self._db,
            DomainEvent(
                event_name=event_name,
                organization_id=proposal.organization_id,
                aggregate_type="accounting_proposal",
                aggregate_id=proposal.proposal_id,
                payload={
                    "proposal_id": proposal.proposal_id,
                    "entry_id": entry.entry_id if entry else None,
                    "vault_document_id": proposal.vault_document_id,
                    "organization_id": proposal.organization_id,
                    "document_type": proposal.document_type,
                    "status": proposal.status,
                    "current_stage": proposal.current_stage,
                    "requires_review": bool(proposal.requires_review),
                    "confidence": float(proposal.confidence)
                    if proposal.confidence is not None
                    else None,
                    "balanced": bool(entry.balanced) if entry else None,
                    "job_id": proposal.job_id,
                    "correlation_id": proposal.correlation_id,
                },
                metadata={"source": "accounting_service"},
                correlation_id=_uuid.uuid4(),
            ),
        )
