"""Repository Decision Center."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.decision_center.enums import BLOCKING_TYPES, SEVERITY_RANK, DecisionSeverity, DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.decision_center.rules import DecisionDraft


class DecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, *, organization_id: int, decision_id: str) -> ElfisDecisionItem | None:
        row = self.db.get(ElfisDecisionItem, decision_id)
        if row is None or row.organization_id != organization_id:
            return None
        return row

    def get_by_dedupe(
        self, *, organization_id: int, deduplication_key: str
    ) -> ElfisDecisionItem | None:
        return (
            self.db.query(ElfisDecisionItem)
            .filter(
                ElfisDecisionItem.organization_id == organization_id,
                ElfisDecisionItem.deduplication_key == deduplication_key,
            )
            .one_or_none()
        )

    def list_decisions(
        self,
        *,
        organization_id: int,
        status: str | None = None,
        severity: str | None = None,
        source_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisDecisionItem], int]:
        q = self.db.query(ElfisDecisionItem).filter(
            ElfisDecisionItem.organization_id == organization_id
        )
        if status:
            q = q.filter(ElfisDecisionItem.status == status)
        if severity:
            q = q.filter(ElfisDecisionItem.severity == severity)
        if source_type:
            q = q.filter(ElfisDecisionItem.source_type == source_type)
        total = q.count()
        rows = q.order_by(ElfisDecisionItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return rows, total

    def list_open_prioritized(
        self, *, organization_id: int, limit: int = 3
    ) -> list[ElfisDecisionItem]:
        rows = (
            self.db.query(ElfisDecisionItem)
            .filter(
                ElfisDecisionItem.organization_id == organization_id,
                ElfisDecisionItem.status.in_(
                    (DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS)
                ),
            )
            .all()
        )
        rows.sort(key=self._priority_key)
        return rows[:limit]

    def upsert_from_draft(
        self, *, organization_id: int, draft: DecisionDraft
    ) -> tuple[ElfisDecisionItem, str]:
        """Retourne (row, event) où event ∈ created|updated|unchanged|reopened."""
        existing = self.get_by_dedupe(
            organization_id=organization_id, deduplication_key=draft.deduplication_key
        )
        now = datetime.utcnow()
        if existing is None:
            row = ElfisDecisionItem(
                organization_id=organization_id,
                decision_type=draft.decision_type,
                source_type=draft.source_type,
                source_id=draft.source_id,
                source_event_id=draft.source_event_id,
                status=DecisionStatus.OPEN,
                severity=draft.severity,
                confidence=draft.confidence,
                title=draft.title,
                summary=draft.summary,
                explanation=draft.explanation,
                recommended_action_type=draft.recommended_action_type,
                recommended_action_path=draft.recommended_action_path,
                required_permission=draft.required_permission,
                metadata_json=draft.metadata,
                deduplication_key=draft.deduplication_key,
                created_by_rule=draft.created_by_rule,
                rule_version=draft.rule_version,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            self.db.flush()
            return row, "created"

        changed = False
        for field, value in (
            ("severity", draft.severity),
            ("title", draft.title),
            ("summary", draft.summary),
            ("explanation", draft.explanation),
            ("recommended_action_type", draft.recommended_action_type),
            ("recommended_action_path", draft.recommended_action_path),
            ("required_permission", draft.required_permission),
            ("confidence", draft.confidence),
        ):
            if getattr(existing, field) != value:
                setattr(existing, field, value)
                changed = True
        if draft.metadata is not None and existing.metadata_json != draft.metadata:
            existing.metadata_json = draft.metadata
            changed = True
        if draft.source_event_id:
            existing.source_event_id = draft.source_event_id

        event = "unchanged"
        if existing.status in {DecisionStatus.RESOLVED, DecisionStatus.DISMISSED, DecisionStatus.EXPIRED}:
            # Rouvrir uniquement si la cause est de nouveau active
            existing.status = DecisionStatus.OPEN
            existing.resolved_at = None
            existing.dismissed_at = None
            changed = True
            event = "reopened"
        elif changed:
            event = "updated"

        if changed:
            existing.updated_at = now
            self.db.add(existing)
            self.db.flush()
        return existing, event

    def resolve(self, row: ElfisDecisionItem) -> ElfisDecisionItem:
        if row.status == DecisionStatus.RESOLVED:
            return row
        row.status = DecisionStatus.RESOLVED
        row.resolved_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.flush()
        return row

    def dismiss(self, row: ElfisDecisionItem) -> ElfisDecisionItem:
        if row.status == DecisionStatus.DISMISSED:
            return row
        row.status = DecisionStatus.DISMISSED
        row.dismissed_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.flush()
        return row

    @staticmethod
    def _priority_key(row: ElfisDecisionItem):
        sev = SEVERITY_RANK.get(DecisionSeverity(row.severity), 0) if row.severity in DecisionSeverity._value2member_map_ else 0
        blocking = 1 if row.decision_type in {t.value for t in BLOCKING_TYPES} else 0
        created = row.created_at or datetime.utcnow()
        return (-sev, -blocking, created)
