"""ProposalService V2 — persistance et API métier."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.audit import write_engine_audit
from app.accounting_engine.engine import AccountingEngine
from app.accounting_engine.enums import ProposalV2Status
from app.accounting_engine.events import publish_engine_event
from app.accounting_engine.exceptions import EngineNotFoundError, EngineValidationError
from app.accounting_engine.learning import LearningEngine
from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.models import Invoice


class ProposalService:
    def __init__(self, db: Session):
        self._db = db
        self._engine = AccountingEngine(db)
        self._learning = LearningEngine(db)

    def get_proposal(
        self, *, organization_id: int, proposal_id: str
    ) -> ElfisAccountingEngineProposal:
        row = (
            self._db.query(ElfisAccountingEngineProposal)
            .filter(ElfisAccountingEngineProposal.id == proposal_id)
            .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
            .first()
        )
        if not row:
            raise EngineNotFoundError()
        return row

    def get_latest_for_document(
        self, *, organization_id: int, source_document_id: str
    ) -> ElfisAccountingEngineProposal | None:
        return (
            self._db.query(ElfisAccountingEngineProposal)
            .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
            .filter(
                ElfisAccountingEngineProposal.source_document_id == source_document_id
            )
            .order_by(ElfisAccountingEngineProposal.version.desc())
            .first()
        )

    def generate(
        self,
        *,
        organization_id: int,
        actor_user_id: int | None,
        payload: dict[str, Any] | None = None,
        invoice_id: int | None = None,
        source_document_id: str | None = None,
        source_kind: str = "manual",
    ) -> ElfisAccountingEngineProposal:
        data = dict(payload or {})
        if invoice_id is not None:
            inv = (
                self._db.query(Invoice)
                .filter(Invoice.id == invoice_id)
                .filter(Invoice.organization_id == organization_id)
                .first()
            )
            if not inv:
                raise EngineNotFoundError("Facture introuvable")
            data = self._invoice_to_payload(inv, data)
            source_document_id = source_document_id or str(inv.id)
            source_kind = "invoice"

        if not data:
            raise EngineValidationError("Payload métier requis")

        result = self._engine.generate(
            organization_id=organization_id,
            payload=data,
            extraction_quality=data.get("extraction_confidence"),
            validation_quality=data.get("validation_confidence"),
        )

        doc_id = source_document_id or data.get("document_id") or data.get("source_document_id")
        prev = None
        version = 1
        if doc_id:
            prev = self.get_latest_for_document(
                organization_id=organization_id, source_document_id=str(doc_id)
            )
            if prev:
                version = int(prev.version or 1) + 1
                prev.status = ProposalV2Status.SUPERSEDED.value
                self._db.add(prev)

        row = ElfisAccountingEngineProposal(
            organization_id=organization_id,
            status=result["status"],
            direction=result["direction"],
            document_type=result["document_type"],
            source_document_id=str(doc_id) if doc_id else None,
            source_kind=source_kind,
            source_version=version,
            journal_code=result["journal_code"],
            journal_label=result["journal_label"],
            currency=result["currency"],
            amount_ht=result["amount_ht"],
            amount_vat=result["amount_vat"],
            amount_ttc=result["amount_ttc"],
            vat_rate=result["vat_rate"],
            lines_json=result["lines"],
            warnings_json=result["warnings"],
            errors_json=result["errors"],
            comments_json=result["comments"],
            explanations_json=result["explanations"],
            consistency_json=result["consistency"],
            confidence_score=result["confidence_score"],
            confidence_detail_json=result["confidence_detail"],
            input_snapshot_json=data,
            previous_snapshot_json=(
                {
                    "lines": prev.lines_json,
                    "journal_code": prev.journal_code,
                    "confidence_score": prev.confidence_score,
                }
                if prev
                else None
            ),
            actor_user_id=actor_user_id,
            version=version,
        )
        self._db.add(row)
        self._db.flush()

        write_engine_audit(
            self._db,
            organization_id=organization_id,
            action="generate",
            proposal_id=row.id,
            actor_user_id=actor_user_id,
            detail={"confidence": row.confidence_score, "journal": row.journal_code},
        )
        evt = (
            "accounting_engine.proposal.requires_review"
            if row.status == ProposalV2Status.REQUIRES_REVIEW.value
            else "accounting_engine.proposal.generated"
        )
        publish_engine_event(
            self._db, event_type=evt, proposal=row, actor_user_id=actor_user_id
        )
        self._db.commit()
        self._db.refresh(row)
        return row

    def regenerate(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        actor_user_id: int | None,
        payload_overrides: dict[str, Any] | None = None,
    ) -> ElfisAccountingEngineProposal:
        existing = self.get_proposal(
            organization_id=organization_id, proposal_id=proposal_id
        )
        data = dict(existing.input_snapshot_json or {})
        if payload_overrides:
            data.update(payload_overrides)
        new_row = self.generate(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            payload=data,
            source_document_id=existing.source_document_id,
            source_kind=existing.source_kind or "manual",
        )
        new_row.status = (
            ProposalV2Status.REGENERATED.value
            if new_row.status == ProposalV2Status.GENERATED.value
            else new_row.status
        )
        self._db.add(new_row)
        write_engine_audit(
            self._db,
            organization_id=organization_id,
            action="regenerate",
            proposal_id=new_row.id,
            actor_user_id=actor_user_id,
            detail={"from_proposal_id": proposal_id},
        )
        publish_engine_event(
            self._db,
            event_type="accounting_engine.proposal.regenerated",
            proposal=new_row,
            actor_user_id=actor_user_id,
        )
        self._db.commit()
        self._db.refresh(new_row)
        return new_row

    def confidence(
        self, *, organization_id: int, proposal_id: str
    ) -> dict[str, Any]:
        row = self.get_proposal(organization_id=organization_id, proposal_id=proposal_id)
        return {
            "proposal_id": row.id,
            "score": row.confidence_score,
            "detail": row.confidence_detail_json or {},
        }

    def explanation(
        self, *, organization_id: int, proposal_id: str
    ) -> dict[str, Any]:
        row = self.get_proposal(organization_id=organization_id, proposal_id=proposal_id)
        return {
            "proposal_id": row.id,
            "explanations": row.explanations_json or [],
            "comments": row.comments_json or [],
            "warnings": row.warnings_json or [],
            "errors": row.errors_json or [],
            "consistency": row.consistency_json or {},
            "journal_code": row.journal_code,
            "journal_label": row.journal_label,
            "comparison": {
                "before": row.previous_snapshot_json,
                "after": {
                    "lines": row.lines_json,
                    "journal_code": row.journal_code,
                    "confidence_score": row.confidence_score,
                },
            },
        }

    def remember_validation(
        self,
        *,
        organization_id: int,
        proposal_id: str,
        actor_user_id: int | None,
    ) -> None:
        """Apprentissage après validation utilisateur (appelé sans valider auto l'écriture)."""
        row = self.get_proposal(organization_id=organization_id, proposal_id=proposal_id)
        party = (row.input_snapshot_json or {}).get("supplier_name") or (
            row.input_snapshot_json or {}
        ).get("customer_name")
        accounts = {}
        for line in row.lines_json or []:
            code = line.get("account_code")
            label = (line.get("account_label") or "").lower()
            if not code:
                continue
            if "tva" in label:
                accounts["vat_account"] = code
            elif "fournisseur" in label or "client" in label:
                accounts["third_party"] = code
            else:
                accounts.setdefault("expense_or_revenue", code)
        self._learning.remember(
            organization_id=organization_id,
            direction=row.direction,
            document_type=row.document_type,
            party_name=str(party) if party else None,
            accounts=accounts,
            journal=row.journal_code,
            vat_rate=row.vat_rate,
            actor_user_id=actor_user_id,
        )
        self._db.commit()

    @staticmethod
    def _invoice_to_payload(inv: Invoice, base: dict[str, Any]) -> dict[str, Any]:
        data = dict(base)
        data.setdefault("document_type", inv.document_type or "invoice")
        data.setdefault("document_number", inv.invoice_number)
        data.setdefault("document_date", inv.invoice_date)
        data.setdefault("supplier_name", inv.supplier)
        data.setdefault("amount_ht", inv.amount_ht)
        data.setdefault("amount_vat", inv.amount_tva)
        data.setdefault("amount_ttc", inv.amount_ttc)
        data.setdefault("vat_rate", inv.vat_rate)
        data.setdefault("extraction_confidence", inv.confidence_score)
        data.setdefault("currency", "EUR")
        if inv.document_type in {"customer_invoice", "sales_invoice"}:
            data.setdefault("direction", "sale")
        return data

    def to_dict(self, row: ElfisAccountingEngineProposal) -> dict[str, Any]:
        return {
            "id": row.id,
            "status": row.status,
            "direction": row.direction,
            "document_type": row.document_type,
            "source_document_id": row.source_document_id,
            "source_kind": row.source_kind,
            "version": row.version,
            "journal_code": row.journal_code,
            "journal_label": row.journal_label,
            "currency": row.currency,
            "amount_ht": row.amount_ht,
            "amount_vat": row.amount_vat,
            "amount_ttc": row.amount_ttc,
            "vat_rate": row.vat_rate,
            "lines": row.lines_json or [],
            "warnings": row.warnings_json or [],
            "errors": row.errors_json or [],
            "comments": row.comments_json or [],
            "explanations": row.explanations_json or [],
            "consistency": row.consistency_json or {},
            "confidence_score": row.confidence_score,
            "confidence_detail": row.confidence_detail_json or {},
            "previous_snapshot": row.previous_snapshot_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "disclaimer": "Proposition uniquement — aucune écriture comptable définitive.",
        }
