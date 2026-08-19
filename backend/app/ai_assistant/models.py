"""Modèles SQLAlchemy — messages structurés, feedback, préférences, runs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ElfisAssistantMessage(Base):
    """Tour de conversation structuré (mémoire récente)."""

    __tablename__ = "elfis_assistant_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(16), default="assistant")  # user|assistant
    question: Mapped[str] = mapped_column(Text, default="")
    answer_text: Mapped[str] = mapped_column(Text, default="")
    structured_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tools_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), default="medium")
    conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ElfisAssistantFeedback(Base):
    """Feedback utilisateur : utile / inutile / incorrect + commentaire."""

    __tablename__ = "elfis_assistant_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    message_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # useful|useless|incorrect
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ElfisAssistantPreference(Base):
    """Préférences utilisateur (pas de données sensibles)."""

    __tablename__ = "elfis_assistant_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisAssistantRun(Base):
    """Observabilité d'un tour : latence, tokens, coût, outils, erreurs."""

    __tablename__ = "elfis_assistant_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    question_preview: Mapped[str] = mapped_column(String(200), default="")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    llm_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    llm_called: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    tools_called: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cache_hit: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
