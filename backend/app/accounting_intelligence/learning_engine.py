"""LearningEngine Intelligence — apprend uniquement après validation utilisateur complète."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.learning import LearningEngine as FoundationLearningEngine
from app.accounting_intelligence.enums import FeedbackAction, LearningGate
from app.accounting_intelligence.memory import LearningMemoryStore
from app.accounting_intelligence.models import ElfisAiLearningMemory


class LearningEngine:
    """
    Délegue la mémoire « courante » foundation + historise en versions Intelligence.
    Ne jamais apprendre : imports rejetés, propositions annulées, corrections incomplètes.
    """

    def __init__(self, db: Session):
        self._db = db
        self._foundation = FoundationLearningEngine(db)
        self._memory = LearningMemoryStore(db)

    def gate(
        self,
        *,
        action: str,
        modifications: dict[str, Any] | None = None,
        cancelled: bool = False,
        import_rejected: bool = False,
    ) -> LearningGate:
        if import_rejected:
            return LearningGate.IMPORT_REJECTED
        if cancelled:
            return LearningGate.CANCELLED
        if action == FeedbackAction.REJECT.value:
            return LearningGate.REJECTED
        if action == FeedbackAction.MODIFY.value:
            mods = modifications or {}
            # Correction incomplète = pas de comptes ni journal fournis
            has_accounts = bool(mods.get("accounts") or mods.get("account_code"))
            has_journal = bool(mods.get("journal") or mods.get("journal_code"))
            if not has_accounts and not has_journal and not mods.get("complete", False):
                return LearningGate.INCOMPLETE
        if action in {FeedbackAction.ACCEPT.value, FeedbackAction.MODIFY.value}:
            return LearningGate.OK
        return LearningGate.INCOMPLETE

    def lookup(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str,
        party_name: str | None,
    ) -> dict[str, str]:
        return self._foundation.lookup(
            organization_id=organization_id,
            direction=direction,
            document_type=document_type,
            party_name=party_name,
        )

    def list_learned(
        self, *, organization_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        rows = self._memory.list_history(organization_id=organization_id, limit=limit)
        return [self._row_dict(r) for r in rows]

    def remember_from_feedback(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str,
        party_name: str | None,
        accounts: dict[str, str],
        journal: str | None = None,
        vat_rate: float | None = None,
        feedback_id: str | None = None,
        actor_user_id: int | None = None,
        gate: LearningGate = LearningGate.OK,
    ) -> ElfisAiLearningMemory | None:
        if gate != LearningGate.OK:
            return None
        if not accounts and not journal:
            return None

        # Fondation (préférences courantes pour AccountResolver)
        self._foundation.remember(
            organization_id=organization_id,
            direction=direction,
            document_type=document_type,
            party_name=party_name,
            accounts=accounts,
            journal=journal,
            vat_rate=vat_rate,
            actor_user_id=actor_user_id,
        )
        # Historique versionné Intelligence
        return self._memory.append_version(
            organization_id=organization_id,
            direction=direction,
            document_type=document_type,
            party_name=party_name,
            accounts=accounts,
            journal=journal,
            vat_rate=vat_rate,
            feedback_id=feedback_id,
            actor_user_id=actor_user_id,
            payload={"gate": gate.value},
        )

    @staticmethod
    def _row_dict(row: ElfisAiLearningMemory) -> dict[str, Any]:
        return {
            "id": row.id,
            "memory_key": row.memory_key,
            "version": row.version,
            "is_current": row.is_current,
            "direction": row.direction,
            "document_type": row.document_type,
            "party_name": row.party_name,
            "preferred_accounts": row.preferred_accounts_json or {},
            "preferred_journal": row.preferred_journal,
            "vat_rate": row.vat_rate,
            "source": row.source,
            "feedback_id": row.feedback_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
