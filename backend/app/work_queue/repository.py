"""Repository Work Queue — lecture filtrée des décisions."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.decision_center.enums import DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.work_queue.enums import COMPLETED_LOOKBACK_DAYS, MAX_SEARCH_LENGTH


class WorkQueueRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_candidates(
        self,
        *,
        organization_id: int,
        severity: str | None = None,
        decision_type: str | None = None,
        source_type: str | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> list[ElfisDecisionItem]:
        """Charge un ensemble borné pour mapping bucket + filtre permissions."""
        q = self.db.query(ElfisDecisionItem).filter(
            ElfisDecisionItem.organization_id == organization_id
        )
        if severity:
            q = q.filter(ElfisDecisionItem.severity == severity)
        if decision_type:
            q = q.filter(ElfisDecisionItem.decision_type == decision_type)
        if source_type:
            q = q.filter(ElfisDecisionItem.source_type == source_type)
        if search:
            term = search.strip()[:MAX_SEARCH_LENGTH]
            if term:
                like = f"%{term}%"
                q = q.filter(
                    or_(
                        ElfisDecisionItem.title.ilike(like),
                        ElfisDecisionItem.summary.ilike(like),
                        ElfisDecisionItem.decision_type.ilike(like),
                        ElfisDecisionItem.source_id.ilike(like),
                    )
                )

        # Exclure les completed trop anciens en amont (réduit le volume)
        cutoff = datetime.utcnow() - timedelta(days=COMPLETED_LOOKBACK_DAYS)
        q = q.filter(
            or_(
                ElfisDecisionItem.status.in_(
                    (
                        DecisionStatus.OPEN,
                        DecisionStatus.IN_PROGRESS,
                    )
                ),
                ElfisDecisionItem.updated_at >= cutoff,
                ElfisDecisionItem.resolved_at >= cutoff,
                ElfisDecisionItem.dismissed_at >= cutoff,
            )
        )
        return q.order_by(ElfisDecisionItem.updated_at.desc()).limit(limit).all()
