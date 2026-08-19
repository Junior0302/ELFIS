"""Proposal Event Bus helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames


def publish_proposal_event(
    db: Session,
    *,
    event_name: str,
    organization_id: int,
    proposal_id: int,
    payload: dict[str, Any],
    actor_user_id: int | None = None,
    idempotency_key: str,
) -> None:
    safe_publish(
        db,
        DomainEvent(
            event_name=event_name,
            organization_id=organization_id,
            aggregate_type="sales_proposal",
            aggregate_id=str(proposal_id),
            payload=payload,
            metadata={
                "source": "sales_proposals",
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
            },
            idempotency_key=idempotency_key,
        ),
        commit=False,
    )


# Re-export names for convenience
PROPOSAL_CREATED = "sales.proposal.created.v1"
VERSION_CREATED = "sales.proposal.version.created.v1"
VERSION_LOCKED = "sales.proposal.version.locked.v1"
PDF_GENERATED = "sales.proposal.pdf.generated.v1"
REVIEW_REQUESTED = "sales.proposal.review.requested.v1"
APPROVED = "sales.proposal.approved.v1"
SENT = "sales.proposal.sent.v1"
VIEWED = "sales.proposal.viewed.v1"
NEGOTIATION_STARTED = "sales.proposal.negotiation.started.v1"
ACCEPTED = "sales.proposal.accepted.v1"
REJECTED = "sales.proposal.rejected.v1"
EXPIRED = "sales.proposal.expired.v1"
CONVERSION_PREPARED = "sales.proposal.conversion.prepared.v1"
