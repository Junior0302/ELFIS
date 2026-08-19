"""Memory — historique versionné d'apprentissage (Intelligence)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.accounting_engine.learning import memory_key as foundation_memory_key
from app.accounting_intelligence.models import ElfisAiLearningMemory


class LearningMemoryStore:
    """Stocke des versions append-only ; une seule version is_current par clé."""

    def __init__(self, db: Session):
        self._db = db

    @staticmethod
    def key(*, direction: str, document_type: str, party_name: str | None) -> str:
        return foundation_memory_key(
            direction=direction, document_type=document_type, party_name=party_name
        )

    def current(
        self,
        *,
        organization_id: int,
        memory_key: str,
    ) -> ElfisAiLearningMemory | None:
        return (
            self._db.query(ElfisAiLearningMemory)
            .filter(ElfisAiLearningMemory.organization_id == organization_id)
            .filter(ElfisAiLearningMemory.memory_key == memory_key)
            .filter(ElfisAiLearningMemory.is_current.is_(True))
            .first()
        )

    def list_history(
        self,
        *,
        organization_id: int,
        memory_key: str | None = None,
        limit: int = 50,
    ) -> list[ElfisAiLearningMemory]:
        q = (
            self._db.query(ElfisAiLearningMemory)
            .filter(ElfisAiLearningMemory.organization_id == organization_id)
            .order_by(ElfisAiLearningMemory.created_at.desc())
        )
        if memory_key:
            q = q.filter(ElfisAiLearningMemory.memory_key == memory_key)
        return q.limit(limit).all()

    def append_version(
        self,
        *,
        organization_id: int,
        direction: str,
        document_type: str,
        party_name: str | None,
        accounts: dict[str, str],
        journal: str | None = None,
        vat_rate: float | None = None,
        source: str = "user_validation",
        feedback_id: str | None = None,
        actor_user_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ElfisAiLearningMemory:
        key = self.key(
            direction=direction, document_type=document_type, party_name=party_name
        )
        prev = self.current(organization_id=organization_id, memory_key=key)
        next_version = (prev.version + 1) if prev else 1
        if prev:
            prev.is_current = False
            self._db.add(prev)

        row = ElfisAiLearningMemory(
            organization_id=organization_id,
            memory_key=key,
            version=next_version,
            is_current=True,
            direction=direction,
            document_type=document_type,
            party_name=party_name,
            preferred_accounts_json=dict(accounts),
            preferred_journal=journal,
            vat_rate=vat_rate,
            source=source,
            feedback_id=feedback_id,
            payload_json=payload or {},
            actor_user_id=actor_user_id,
        )
        self._db.add(row)
        self._db.flush()
        return row
