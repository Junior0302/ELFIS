"""Sales Intelligence — repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.sales_intelligence.enums import InsightStatus
from app.sales_intelligence.models import SalesInsightItem


def _now() -> datetime:
    return datetime.utcnow()


class InsightRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, organization_id: int, insight_id: int) -> SalesInsightItem | None:
        return (
            self.db.query(SalesInsightItem)
            .filter(
                SalesInsightItem.id == insight_id,
                SalesInsightItem.organization_id == organization_id,
            )
            .first()
        )

    def by_dedupe(self, organization_id: int, key: str) -> SalesInsightItem | None:
        return (
            self.db.query(SalesInsightItem)
            .filter(
                SalesInsightItem.organization_id == organization_id,
                SalesInsightItem.deduplication_key == key,
            )
            .first()
        )

    def list_filtered(
        self,
        *,
        organization_id: int,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "-priority_score",
    ) -> tuple[list[SalesInsightItem], int]:
        q = self.db.query(SalesInsightItem).filter(
            SalesInsightItem.organization_id == organization_id
        )
        if category:
            q = q.filter(SalesInsightItem.category == category)
        if severity:
            q = q.filter(SalesInsightItem.severity == severity)
        if status:
            q = q.filter(SalesInsightItem.status == status)
        else:
            q = q.filter(
                SalesInsightItem.status.in_(
                    (InsightStatus.active.value, InsightStatus.acknowledged.value)
                )
            )
        if source_type:
            q = q.filter(SalesInsightItem.source_type == source_type)
        if source_id:
            q = q.filter(SalesInsightItem.source_id == source_id)

        total = q.count()
        desc = sort.startswith("-")
        field_name = sort.lstrip("-")
        column = getattr(SalesInsightItem, field_name, SalesInsightItem.priority_score)
        q = q.order_by(column.desc() if desc else column.asc())
        page = max(1, page)
        limit = min(100, max(1, limit))
        items = q.offset((page - 1) * limit).limit(limit).all()
        return items, total

    def active_for_org(self, organization_id: int, limit: int = 50) -> list[SalesInsightItem]:
        return (
            self.db.query(SalesInsightItem)
            .filter(
                SalesInsightItem.organization_id == organization_id,
                SalesInsightItem.status.in_(
                    (InsightStatus.active.value, InsightStatus.acknowledged.value)
                ),
            )
            .order_by(SalesInsightItem.priority_score.desc(), SalesInsightItem.id.desc())
            .limit(limit)
            .all()
        )

    def upsert_from_draft(self, organization_id: int, draft) -> tuple[SalesInsightItem, str]:
        now = _now()
        existing = self.by_dedupe(organization_id, draft.deduplication_key)
        if existing is None:
            row = SalesInsightItem(
                organization_id=organization_id,
                insight_type=draft.insight_type,
                category=draft.category,
                source_type=draft.source_type,
                source_id=draft.source_id,
                source_label=draft.source_label,
                deduplication_key=draft.deduplication_key,
                severity=draft.severity,
                priority_score=draft.priority_score,
                title=draft.title,
                summary=draft.summary,
                explanation=draft.explanation,
                evidence=draft.evidence,
                recommended_action=draft.recommended_action,
                available_actions=draft.available_actions,
                route=draft.route,
                resolution_condition=draft.resolution_condition,
                status=InsightStatus.active.value,
                observed_value=draft.observed_value,
                score=draft.score,
                first_detected_at=now,
                last_detected_at=now,
            )
            self.db.add(row)
            self.db.flush()
            return row, "created"

        # Update detection — do not recreate if dismissed unless severity rises critically
        existing.last_detected_at = now
        existing.updated_at = now
        existing.title = draft.title
        existing.summary = draft.summary
        existing.explanation = draft.explanation
        existing.evidence = draft.evidence
        existing.recommended_action = draft.recommended_action
        existing.available_actions = draft.available_actions
        existing.route = draft.route
        existing.resolution_condition = draft.resolution_condition
        existing.observed_value = draft.observed_value
        existing.score = draft.score
        existing.source_label = draft.source_label
        old_sev = existing.severity
        existing.severity = draft.severity
        existing.priority_score = draft.priority_score
        existing.insight_type = draft.insight_type
        existing.category = draft.category

        event = "updated"
        if existing.status == InsightStatus.resolved.value:
            existing.status = InsightStatus.active.value
            existing.resolved_at = None
            event = "reopened"
        elif existing.status == InsightStatus.dismissed.value:
            # Reappear only if severity increased to high/critical
            rank = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
            if rank.get(draft.severity, 0) > rank.get(old_sev, 0) and draft.severity in (
                "high",
                "critical",
            ):
                existing.status = InsightStatus.active.value
                existing.dismissed_at = None
                existing.dismiss_reason = None
                event = "reopened"
        return existing, event
