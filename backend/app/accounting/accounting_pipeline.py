"""AccountingPipeline — orchestration persistante."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.accounting.accounting_exceptions import (
    AccountingDisabledError,
    AccountingNotFoundError,
    AccountingValidationError,
)
from app.accounting.accounting_logging import (
    safe_accounting_log_context,
    sanitize_accounting_error,
)
from app.accounting.accounting_models import (
    ElfisAccountingEntry,
    ElfisAccountingEntryLine,
    ElfisAccountingProposal,
    ElfisAccountingReview,
)
from app.accounting.accounting_repository import AccountingRepository
from app.accounting.accounting_schemas import AccountingPipelineRequest, AccountingProposalResult
from app.accounting.accounting_types import (
    EntryStatus,
    ProposalStage,
    ProposalStatus,
    ReviewAction,
    SUPPORTED_DOCUMENT_TYPES_V1,
    normalize_document_type,
)
from app.accounting.extraction_adapter import extraction_from_analysis
from app.accounting.stages import (
    determine_review_status,
    run_accounting_mapping,
    run_document_validation,
    run_financial_validation,
)
from app.ai.ai_models import ElfisDocumentAnalysis
from app.ai.ai_types import DocumentAnalysisStatus
from app.config import settings
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_vault import VaultDocument

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _as_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class AccountingPipeline:
    def __init__(self, db: Session):
        self._db = db
        self._repo = AccountingRepository(db)

    def process(self, request: AccountingPipelineRequest) -> AccountingProposalResult:
        if not settings.elfis_accounting_pipeline_enabled:
            raise AccountingDisabledError()

        started = time.monotonic()
        doc = (
            self._db.query(VaultDocument)
            .filter(VaultDocument.id == request.vault_document_id)
            .first()
        )
        if not doc or doc.organization_id != request.organization_id:
            raise AccountingNotFoundError("Document introuvable")

        version = int(request.document_version or doc.version or 1)
        idem = (request.idempotency_key or "").strip() or (
            f"accounting-proposal:{request.organization_id}:{request.vault_document_id}:{version}"
        )

        existing = self._repo.find_by_idempotency(idem) or self._repo.find_proposal_for_document(
            organization_id=request.organization_id,
            vault_document_id=request.vault_document_id,
            document_version=version,
        )
        if existing and existing.status in (
            ProposalStatus.READY_FOR_VALIDATION,
            ProposalStatus.REQUIRES_REVIEW,
            ProposalStatus.VALIDATED,
            ProposalStatus.PROCESSING,
            ProposalStatus.VALIDATION_FAILED,
            ProposalStatus.FINANCIAL_ERROR,
            ProposalStatus.MAPPING_FAILED,
        ):
            entry = self._repo.find_active_entry(existing.proposal_id)
            return AccountingProposalResult(
                proposal_id=existing.proposal_id,
                created=False,
                status=existing.status,
                current_stage=existing.current_stage,
                requires_review=bool(existing.requires_review),
                confidence=float(existing.confidence) if existing.confidence is not None else None,
                entry_id=entry.entry_id if entry else None,
                validation_summary=dict(existing.document_validation or {}),
                financial_summary=dict(existing.financial_validation or {}),
                mapping_summary={
                    "balanced": (existing.accounting_mapping or {}).get("balanced"),
                    "status": (existing.accounting_mapping or {}).get("status"),
                },
            )

        analysis = self._load_analysis(request, version)
        extraction_json = analysis.extraction if analysis else None
        if not extraction_json:
            raise AccountingValidationError("Analyse sans extraction exploitable")

        doc_type = normalize_document_type(
            (analysis.document_type if analysis else None)
            or (extraction_json.get("document_type") if isinstance(extraction_json, dict) else None)
        )
        conf = float(analysis.confidence) if analysis and analysis.confidence is not None else None
        extraction = extraction_from_analysis(
            extraction_json if isinstance(extraction_json, dict) else {},
            document_type=doc_type,
            confidence=conf,
        )

        now = datetime.utcnow()
        proposal = existing or ElfisAccountingProposal(
            id=str(uuid.uuid4()),
            proposal_id=str(uuid.uuid4()),
            organization_id=request.organization_id,
            user_id=request.user_id,
            vault_document_id=request.vault_document_id,
            document_analysis_id=analysis.analysis_id if analysis else request.document_analysis_id,
            document_version=version,
            document_type=doc_type,
            status=ProposalStatus.PENDING,
            current_stage=ProposalStage.INITIALIZATION,
            document_validation={},
            financial_validation={},
            accounting_mapping={},
            quality_summary={},
            review_reasons=[],
            source="elfis_pipeline",
            idempotency_key=idem,
            correlation_id=request.correlation_id or str(uuid.uuid4()),
            source_event_id=request.source_event_id,
            job_id=request.job_id,
            created_at=now,
            updated_at=now,
        )
        proposal.status = ProposalStatus.PROCESSING
        proposal.current_stage = ProposalStage.INITIALIZATION
        proposal.document_type = doc_type
        proposal.document_number = extraction.invoice_number
        proposal.document_date = _parse_date(extraction.invoice_date)
        proposal.due_date = _parse_date(extraction.due_date)
        proposal.supplier_name = extraction.supplier
        proposal.customer_name = extraction.customer_name
        proposal.currency = (extraction.currency or "EUR")[:8]
        proposal.amount_ht = extraction.amount_ht
        proposal.amount_vat = extraction.amount_tva
        proposal.amount_ttc = extraction.amount_ttc
        proposal.confidence = conf
        proposal.quality_summary = (
            analysis.quality if analysis and isinstance(analysis.quality, dict) else {}
        )
        proposal.job_id = request.job_id or proposal.job_id
        self._repo.save_proposal(proposal)
        self._publish(EventNames.ACCOUNTING_PROPOSAL_CREATED, proposal)
        self._publish(EventNames.ACCOUNTING_PROPOSAL_PROCESSING, proposal)
        self._add_system_review(proposal, ReviewAction.CREATED, request.user_id)

        # Document validation
        proposal.current_stage = ProposalStage.DOCUMENT_VALIDATION
        doc_val = run_document_validation(extraction)
        proposal.document_validation = doc_val
        self._repo.save_proposal(proposal)
        if doc_val.get("status") == "invalid" and doc_val.get("missing_fields"):
            # Continuer quand même vers finance/mapping pour diagnostic, mais status final review/failed
            pass

        # Financial validation
        proposal.current_stage = ProposalStage.FINANCIAL_VALIDATION
        fin_val = run_financial_validation(extraction)
        proposal.financial_validation = fin_val
        self._repo.save_proposal(proposal)

        if fin_val.get("status") == "invalid" and not fin_val.get("balanced_amounts"):
            proposal.status = ProposalStatus.FINANCIAL_ERROR
            proposal.requires_review = True
            proposal.review_reasons = ["financial_error"]
            proposal.current_stage = ProposalStage.REVIEW
            proposal.completed_at = datetime.utcnow()
            self._repo.save_proposal(proposal)
            self._publish(EventNames.ACCOUNTING_PROPOSAL_VALIDATION_FAILED, proposal)
            return self._result(proposal, created=True, entry_id=None)

        # Mapping
        proposal.current_stage = ProposalStage.ACCOUNTING_MAPPING
        if doc_type not in SUPPORTED_DOCUMENT_TYPES_V1:
            mapping = {
                "status": "skipped",
                "errors": ["Type préparé non automatisé en V1"],
                "warnings": [],
                "lines": [],
                "balanced": False,
                "used_default_accounts": False,
            }
        else:
            mapping = run_accounting_mapping(extraction, document_type=doc_type)
        proposal.accounting_mapping = mapping
        self._repo.save_proposal(proposal)

        entry_id = None
        if mapping.get("lines"):
            entry = self._persist_entry(proposal, mapping)
            entry_id = entry.entry_id
            if not mapping.get("balanced"):
                proposal.status = ProposalStatus.MAPPING_FAILED
                proposal.requires_review = True
                proposal.review_reasons = ["unbalanced_entry"]
                proposal.current_stage = ProposalStage.REVIEW
                proposal.completed_at = datetime.utcnow()
                self._repo.save_proposal(proposal)
                self._publish(EventNames.ACCOUNTING_PROPOSAL_UNBALANCED, proposal)
                return self._result(proposal, created=True, entry_id=entry_id)

        # Review determination
        proposal.current_stage = ProposalStage.REVIEW
        requires_review, reasons, _ = determine_review_status(
            confidence=conf,
            document_validation=doc_val,
            financial_validation=fin_val,
            mapping=mapping,
            amount_ttc=proposal.amount_ttc,
            document_type_supported=doc_type in SUPPORTED_DOCUMENT_TYPES_V1,
        )
        if doc_val.get("status") == "invalid":
            proposal.status = ProposalStatus.VALIDATION_FAILED
            requires_review = True
            reasons = list(dict.fromkeys(reasons + ["document_validation_issue"]))
            proposal.requires_review = True
            proposal.review_reasons = reasons
            proposal.completed_at = datetime.utcnow()
            self._repo.save_proposal(proposal)
            self._publish(EventNames.ACCOUNTING_PROPOSAL_VALIDATION_FAILED, proposal)
            return self._result(proposal, created=True, entry_id=entry_id)

        proposal.requires_review = requires_review
        proposal.review_reasons = reasons
        if requires_review:
            proposal.status = ProposalStatus.REQUIRES_REVIEW
            self._publish(EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW, proposal)
        else:
            proposal.status = ProposalStatus.READY_FOR_VALIDATION
            self._publish(EventNames.ACCOUNTING_PROPOSAL_READY, proposal)
        proposal.current_stage = ProposalStage.COMPLETED
        proposal.completed_at = datetime.utcnow()
        self._repo.save_proposal(proposal)

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "accounting_proposal_done",
            extra=safe_accounting_log_context(
                proposal_id=proposal.proposal_id,
                entry_id=entry_id,
                vault_document_id=proposal.vault_document_id,
                organization_id=proposal.organization_id,
                document_type=proposal.document_type,
                status=proposal.status,
                current_stage=proposal.current_stage,
                requires_review=proposal.requires_review,
                confidence=float(proposal.confidence) if proposal.confidence is not None else None,
                balanced=bool((proposal.accounting_mapping or {}).get("balanced")),
                duration_ms=duration_ms,
                job_id=proposal.job_id,
                correlation_id=proposal.correlation_id,
            ),
        )
        return self._result(proposal, created=True, entry_id=entry_id)

    def _load_analysis(
        self, request: AccountingPipelineRequest, version: int
    ) -> ElfisDocumentAnalysis | None:
        q = self._db.query(ElfisDocumentAnalysis).filter(
            ElfisDocumentAnalysis.organization_id == request.organization_id,
            ElfisDocumentAnalysis.vault_document_id == request.vault_document_id,
            ElfisDocumentAnalysis.document_version == version,
        )
        if request.document_analysis_id:
            row = (
                self._db.query(ElfisDocumentAnalysis)
                .filter(ElfisDocumentAnalysis.analysis_id == request.document_analysis_id)
                .first()
            )
            if row and row.organization_id == request.organization_id:
                return row
        row = q.order_by(ElfisDocumentAnalysis.created_at.desc()).first()
        if row and row.status in (
            DocumentAnalysisStatus.COMPLETED,
            DocumentAnalysisStatus.REQUIRES_REVIEW,
        ):
            return row
        return row

    def _persist_entry(
        self, proposal: ElfisAccountingProposal, mapping: dict[str, Any]
    ) -> ElfisAccountingEntry:
        # Annuler ancienne entry active
        old = self._repo.find_active_entry(proposal.proposal_id)
        if old and old.status != EntryStatus.VALIDATED:
            old.status = EntryStatus.CANCELLED
            self._repo.save_entry(old, commit=False)
            self._repo.delete_lines(old.entry_id)

        entry_date = proposal.document_date or date.today()
        entry = ElfisAccountingEntry(
            id=str(uuid.uuid4()),
            entry_id=str(uuid.uuid4()),
            organization_id=proposal.organization_id,
            proposal_id=proposal.proposal_id,
            journal_code=str(mapping.get("journal_code") or "ACH")[:16],
            entry_date=entry_date,
            reference=(mapping.get("reference") or proposal.document_number or "")[:128] or None,
            description=str(mapping.get("description") or "Écriture proposée")[:500],
            currency=proposal.currency or "EUR",
            total_debit=mapping.get("total_debit") or 0,
            total_credit=mapping.get("total_credit") or 0,
            balanced=bool(mapping.get("balanced")),
            status=EntryStatus.PROPOSED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._repo.save_entry(entry, commit=False)
        for idx, line in enumerate(mapping.get("lines") or [], start=1):
            self._repo.save_line(
                ElfisAccountingEntryLine(
                    id=str(uuid.uuid4()),
                    line_id=str(uuid.uuid4()),
                    organization_id=proposal.organization_id,
                    entry_id=entry.entry_id,
                    line_number=idx,
                    account_code=str(line.get("account_code") or "")[:16],
                    account_label=(line.get("account_label") or None),
                    third_party_name=line.get("third_party_name"),
                    debit=line.get("debit") or 0,
                    credit=line.get("credit") or 0,
                    description=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ),
                commit=False,
            )
        self._db.commit()
        self._db.refresh(entry)
        return entry

    def _add_system_review(
        self,
        proposal: ElfisAccountingProposal,
        action: str,
        user_id: int | None,
    ) -> None:
        if user_id is None:
            return
        self._repo.add_review(
            ElfisAccountingReview(
                id=str(uuid.uuid4()),
                review_id=str(uuid.uuid4()),
                organization_id=proposal.organization_id,
                proposal_id=proposal.proposal_id,
                user_id=user_id,
                action=action,
                previous_data=None,
                new_data={"status": proposal.status},
                comment=None,
                created_at=datetime.utcnow(),
            ),
            commit=True,
        )

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
                    "balanced": bool((proposal.accounting_mapping or {}).get("balanced"))
                    if entry
                    else None,
                    "job_id": proposal.job_id,
                    "correlation_id": proposal.correlation_id,
                },
                metadata={"source": "accounting_pipeline"},
                correlation_id=_as_uuid(proposal.correlation_id) or uuid.uuid4(),
                causation_id=_as_uuid(proposal.source_event_id),
            ),
        )

    def _result(
        self,
        proposal: ElfisAccountingProposal,
        *,
        created: bool,
        entry_id: str | None,
    ) -> AccountingProposalResult:
        return AccountingProposalResult(
            proposal_id=proposal.proposal_id,
            created=created,
            status=proposal.status,
            current_stage=proposal.current_stage,
            requires_review=bool(proposal.requires_review),
            confidence=float(proposal.confidence) if proposal.confidence is not None else None,
            entry_id=entry_id,
            validation_summary={
                "status": (proposal.document_validation or {}).get("status"),
                "missing_fields": (proposal.document_validation or {}).get("missing_fields"),
            },
            financial_summary={
                "status": (proposal.financial_validation or {}).get("status"),
                "balanced_amounts": (proposal.financial_validation or {}).get("balanced_amounts"),
            },
            mapping_summary={
                "status": (proposal.accounting_mapping or {}).get("status"),
                "balanced": (proposal.accounting_mapping or {}).get("balanced"),
            },
        )
