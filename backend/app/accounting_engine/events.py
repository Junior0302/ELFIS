"""Events Accounting Engine V2."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.accounting_engine.models import ElfisAccountingEngineProposal


def _map(event_type: str) -> str:
    return {
        "accounting_engine.proposal.generated": EventNames.ACCOUNTING_ENGINE_PROPOSAL_GENERATED,
        "accounting_engine.proposal.regenerated": EventNames.ACCOUNTING_ENGINE_PROPOSAL_REGENERATED,
        "accounting_engine.proposal.requires_review": EventNames.ACCOUNTING_ENGINE_PROPOSAL_REQUIRES_REVIEW,
    }.get(event_type, event_type)


def publish_engine_event(
    db: Session,
    *,
    event_type: str,
    proposal: ElfisAccountingEngineProposal,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    payload = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "organization_id": proposal.organization_id,
        "proposal_id": proposal.id,
        "status": proposal.status,
        "confidence_score": proposal.confidence_score,
        "journal_code": proposal.journal_code,
        "actor_user_id": actor_user_id,
        "occurred_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    safe_publish(
        db,
        DomainEvent(
            event_name=_map(event_type),
            organization_id=int(proposal.organization_id),
            aggregate_type="accounting_engine",
            aggregate_id=proposal.id,
            payload=payload,
            metadata={"source": "accounting_engine"},
            correlation_id=uuid4(),
            idempotency_key=(
                f"{event_type}:{proposal.organization_id}:{proposal.id}:{proposal.version}"
            )[:255],
        ),
        commit=commit,
    )
