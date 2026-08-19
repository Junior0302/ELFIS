"""Feedback Engine — capture acceptation / modification / refus."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.models import ElfisAccountingEngineProposal
from app.accounting_intelligence.enums import FeedbackAction, LearningGate
from app.accounting_intelligence.exceptions import (
    IntelligenceNotFoundError,
    IntelligenceValidationError,
)
from app.accounting_intelligence.learning_engine import LearningEngine
from app.accounting_intelligence.models import (
    ElfisAiFeedback,
    ElfisAiRecommendationHistory,
)


class FeedbackEngine:
    def __init__(self, db: Session):
        self._db = db
        self._learning = LearningEngine(db)

    def record(
        self,
        *,
        organization_id: int,
        action: str,
        actor_user_id: int | None,
        recommendation_id: str | None = None,
        proposal_id: str | None = None,
        validation_seconds: float | None = None,
        comment: str | None = None,
        modifications: dict[str, Any] | None = None,
        cancelled: bool = False,
        import_rejected: bool = False,
    ) -> tuple[ElfisAiFeedback, LearningGate]:
        if action not in {a.value for a in FeedbackAction}:
            raise IntelligenceValidationError(f"action invalide: {action}")

        rec: ElfisAiRecommendationHistory | None = None
        if recommendation_id:
            rec = (
                self._db.query(ElfisAiRecommendationHistory)
                .filter(ElfisAiRecommendationHistory.organization_id == organization_id)
                .filter(ElfisAiRecommendationHistory.id == recommendation_id)
                .first()
            )
            if not rec:
                raise IntelligenceNotFoundError("recommandation introuvable")

        prop: ElfisAccountingEngineProposal | None = None
        if proposal_id:
            prop = (
                self._db.query(ElfisAccountingEngineProposal)
                .filter(ElfisAccountingEngineProposal.organization_id == organization_id)
                .filter(ElfisAccountingEngineProposal.id == proposal_id)
                .first()
            )
            if not prop:
                raise IntelligenceNotFoundError("proposition introuvable")

        mods = modifications or {}
        gate = self._learning.gate(
            action=action,
            modifications=mods,
            cancelled=cancelled,
            import_rejected=import_rejected,
        )

        fb = ElfisAiFeedback(
            organization_id=organization_id,
            recommendation_id=recommendation_id,
            proposal_id=proposal_id or (rec.proposal_id if rec else None),
            action=action,
            validation_seconds=validation_seconds,
            comment=comment,
            modifications_json=mods,
            learned=False,
            learn_gate=gate.value,
            actor_user_id=actor_user_id,
        )
        self._db.add(fb)
        self._db.flush()

        if gate == LearningGate.OK:
            direction = (
                (prop.direction if prop else None)
                or (rec.direction if rec else None)
                or mods.get("direction")
                or "purchase"
            )
            document_type = (
                (prop.document_type if prop else None)
                or (rec.document_type if rec else None)
                or mods.get("document_type")
                or "invoice"
            )
            party = (
                mods.get("party_name")
                or (rec.party_name if rec else None)
                or (
                    (prop.input_snapshot_json or {}).get("supplier_name")
                    if prop
                    else None
                )
            )
            accounts = dict(mods.get("accounts") or {})
            if mods.get("account_code") and "expense_or_revenue" not in accounts:
                accounts["expense_or_revenue"] = mods["account_code"]
            if not accounts and prop:
                for line in prop.lines_json or []:
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
            if not accounts and rec and rec.account_code:
                accounts["expense_or_revenue"] = rec.account_code
                if rec.recommendation_json:
                    accounts.update(
                        (rec.recommendation_json or {}).get("accounts") or {}
                    )

            journal = (
                mods.get("journal")
                or mods.get("journal_code")
                or (prop.journal_code if prop else None)
                or (rec.journal_code if rec else None)
            )
            vat_rate = mods.get("vat_rate")
            if vat_rate is None and prop:
                vat_rate = prop.vat_rate
            if vat_rate is None and rec:
                vat_rate = rec.vat_rate

            learned = self._learning.remember_from_feedback(
                organization_id=organization_id,
                direction=str(direction),
                document_type=str(document_type),
                party_name=str(party) if party else None,
                accounts=accounts,
                journal=journal,
                vat_rate=float(vat_rate) if vat_rate is not None else None,
                feedback_id=fb.id,
                actor_user_id=actor_user_id,
                gate=gate,
            )
            fb.learned = learned is not None
            self._db.add(fb)
            self._db.flush()

        return fb, gate
