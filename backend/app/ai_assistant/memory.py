"""Mémoire conversationnelle — contexte récent + préférences (sans secrets)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai_assistant.models import ElfisAssistantMessage, ElfisAssistantPreference
from app.ai_assistant.types import StructuredAnswer
from app.models_saas import AIConversation

ALLOWED_PREFERENCE_KEYS = frozenset(
    {
        "tone",  # concise | detailed
        "language",  # fr
        "focus",  # cashflow | unpaid | overview
    }
)


class ConversationMemory:
    def __init__(self, db: Session, organization_id: int, user_id: int | None):
        self.db = db
        self.organization_id = organization_id
        self.user_id = user_id

    def recent_turns(self, *, limit: int = 4) -> list[dict]:
        if not self.user_id:
            return []
        rows = (
            self.db.query(ElfisAssistantMessage)
            .filter(
                ElfisAssistantMessage.organization_id == self.organization_id,
                ElfisAssistantMessage.user_id == self.user_id,
            )
            .order_by(ElfisAssistantMessage.created_at.desc())
            .limit(limit * 2)
            .all()
        )
        rows = list(reversed(rows))
        return [
            {
                "role": r.role,
                "question": (r.question or "")[:300],
                "answer": (r.answer_text or "")[:400],
                "confidence": r.confidence,
            }
            for r in rows
        ]

    def get_preferences(self) -> dict[str, str]:
        if not self.user_id:
            return {}
        rows = (
            self.db.query(ElfisAssistantPreference)
            .filter(
                ElfisAssistantPreference.organization_id == self.organization_id,
                ElfisAssistantPreference.user_id == self.user_id,
            )
            .all()
        )
        return {r.key: r.value for r in rows if r.key in ALLOWED_PREFERENCE_KEYS}

    def set_preference(self, key: str, value: str) -> None:
        if not self.user_id or key not in ALLOWED_PREFERENCE_KEYS:
            return
        row = (
            self.db.query(ElfisAssistantPreference)
            .filter(
                ElfisAssistantPreference.organization_id == self.organization_id,
                ElfisAssistantPreference.user_id == self.user_id,
                ElfisAssistantPreference.key == key,
            )
            .first()
        )
        if row:
            row.value = value[:255]
        else:
            self.db.add(
                ElfisAssistantPreference(
                    organization_id=self.organization_id,
                    user_id=self.user_id,
                    key=key,
                    value=value[:255],
                )
            )
        self.db.commit()

    def persist_turn(
        self,
        *,
        question: str,
        answer: StructuredAnswer,
        run_id: str | None = None,
    ) -> tuple[ElfisAssistantMessage | None, int | None]:
        """Persiste le message structuré + compat AIConversation (historique legacy)."""
        conversation_id = None
        if self.user_id:
            legacy = AIConversation(
                user_id=self.user_id,
                organization_id=self.organization_id,
                question=question.strip(),
                answer=answer.to_plain_text(),
            )
            self.db.add(legacy)
            self.db.flush()
            conversation_id = legacy.id

            msg = ElfisAssistantMessage(
                organization_id=self.organization_id,
                user_id=self.user_id,
                role="assistant",
                question=question.strip()[:2000],
                answer_text=answer.to_plain_text(),
                structured_json=answer.model_dump(mode="json"),
                tools_used=list(answer.tools_used),
                sources=list(answer.sources),
                confidence=answer.confidence.value,
                conversation_id=conversation_id,
                run_id=run_id,
            )
            self.db.add(msg)
            self.db.commit()
            self.db.refresh(msg)
            return msg, conversation_id

        self.db.commit()
        return None, None

    def list_history(self, *, limit: int = 20) -> list[dict]:
        q = self.db.query(ElfisAssistantMessage).filter(
            ElfisAssistantMessage.organization_id == self.organization_id,
            ElfisAssistantMessage.role == "assistant",
        )
        if self.user_id:
            q = q.filter(ElfisAssistantMessage.user_id == self.user_id)
        rows = q.order_by(ElfisAssistantMessage.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "question": r.question,
                "answer": r.answer_text,
                "structured": r.structured_json,
                "tools_used": r.tools_used or [],
                "sources": r.sources or [],
                "confidence": r.confidence,
                "conversation_id": r.conversation_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
