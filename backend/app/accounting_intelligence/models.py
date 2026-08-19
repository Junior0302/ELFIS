"""Modèles Accounting Intelligence V2."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid4())


class ElfisAiContextProfile(Base):
    """Profil contexte entreprise — isolé par tenant."""

    __tablename__ = "elfis_ai_context_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_elfis_ai_ctx_org"),
        Index("ix_elfis_ai_ctx_org", "organization_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    frequent_accounts_json = Column("frequent_accounts", JSON, nullable=False, default=list)
    favorite_journals_json = Column("favorite_journals", JSON, nullable=False, default=list)
    habitual_vat_rates_json = Column("habitual_vat_rates", JSON, nullable=False, default=list)
    exceptions_json = Column("exceptions", JSON, nullable=False, default=list)
    preferences_json = Column("preferences", JSON, nullable=False, default=dict)
    stats_json = Column("stats", JSON, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    rebuilt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ElfisAiLearningMemory(Base):
    """Mémoire d'apprentissage versionnée (Intelligence)."""

    __tablename__ = "elfis_ai_learning_memory"
    __table_args__ = (
        Index("ix_elfis_ai_lm_org_key", "organization_id", "memory_key"),
        UniqueConstraint(
            "organization_id", "memory_key", "version", name="uq_elfis_ai_lm_org_key_ver"
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    memory_key = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True)
    direction = Column(String(32), nullable=True)
    document_type = Column(String(64), nullable=True)
    party_name = Column(String(255), nullable=True)
    preferred_accounts_json = Column("preferred_accounts", JSON, nullable=False, default=dict)
    preferred_journal = Column(String(16), nullable=True)
    vat_rate = Column(Float, nullable=True)
    source = Column(String(64), nullable=False, default="user_validation")
    feedback_id = Column(String(36), nullable=True)
    payload_json = Column("payload", JSON, nullable=False, default=dict)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisAiRecommendationHistory(Base):
    """Historique des recommandations générées."""

    __tablename__ = "elfis_ai_recommendation_history"
    __table_args__ = (
        Index("ix_elfis_ai_rec_org", "organization_id", "created_at"),
        Index("ix_elfis_ai_rec_proposal", "proposal_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    proposal_id = Column(String(36), nullable=True)
    direction = Column(String(32), nullable=True)
    document_type = Column(String(64), nullable=True)
    party_name = Column(String(255), nullable=True)
    account_code = Column(String(16), nullable=True)
    journal_code = Column(String(16), nullable=True)
    vat_rate = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    primary_source = Column(String(32), nullable=True)
    reason = Column(Text, nullable=True)
    recommendation_json = Column("recommendation", JSON, nullable=False, default=dict)
    explanation_json = Column("explanation", JSON, nullable=False, default=dict)
    confidence_detail_json = Column("confidence_detail", JSON, nullable=False, default=dict)
    input_snapshot_json = Column("input_snapshot", JSON, nullable=False, default=dict)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisAiFeedback(Base):
    """Feedback utilisateur sur une recommandation / proposition."""

    __tablename__ = "elfis_ai_feedback"
    __table_args__ = (
        Index("ix_elfis_ai_fb_org", "organization_id", "created_at"),
        Index("ix_elfis_ai_fb_rec", "recommendation_id"),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    recommendation_id = Column(String(36), nullable=True)
    proposal_id = Column(String(36), nullable=True)
    action = Column(String(32), nullable=False)  # accept|modify|reject
    validation_seconds = Column(Float, nullable=True)
    comment = Column(Text, nullable=True)
    modifications_json = Column("modifications", JSON, nullable=False, default=dict)
    learned = Column(Boolean, nullable=False, default=False)
    learn_gate = Column(String(32), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ElfisAiSimilarityCache(Base):
    """Cache de similarité entre documents / parties."""

    __tablename__ = "elfis_ai_similarity_cache"
    __table_args__ = (
        Index("ix_elfis_ai_sim_org", "organization_id", "query_key"),
        UniqueConstraint(
            "organization_id", "query_key", "candidate_key", name="uq_elfis_ai_sim_keys"
        ),
    )

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    query_key = Column(String(255), nullable=False)
    candidate_key = Column(String(255), nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    factors_json = Column("factors", JSON, nullable=False, default=dict)
    payload_json = Column("payload", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class ElfisAiAudit(Base):
    """Audit trail Intelligence."""

    __tablename__ = "elfis_ai_audit"
    __table_args__ = (Index("ix_elfis_ai_audit_org", "organization_id", "created_at"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=True)
    entity_id = Column(String(36), nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    detail_json = Column("detail", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
