"""Proposal numbering — SP-{YEAR}-{SEQUENCE:06d}, unique per org."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.sales_proposals.models import SalesProposalNumberSequence


def next_proposal_number(db: Session, *, organization_id: int, now: datetime | None = None) -> str:
    ref = now or datetime.utcnow()
    year = ref.year
    row = (
        db.query(SalesProposalNumberSequence)
        .filter(
            SalesProposalNumberSequence.organization_id == organization_id,
            SalesProposalNumberSequence.year == year,
        )
        .with_for_update()
        .first()
    )
    if not row:
        row = SalesProposalNumberSequence(
            organization_id=organization_id, year=year, last_value=0
        )
        db.add(row)
        db.flush()
        # re-lock after insert for concurrency on engines that support it
        row = (
            db.query(SalesProposalNumberSequence)
            .filter(
                SalesProposalNumberSequence.organization_id == organization_id,
                SalesProposalNumberSequence.year == year,
            )
            .with_for_update()
            .first()
        )
    assert row is not None
    row.last_value = int(row.last_value or 0) + 1
    row.updated_at = ref
    db.flush()
    return f"SP-{year}-{row.last_value:06d}"
