"""Service Work Queue — buckets, counts, start, résumé Command Center."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.decision_center.enums import BLOCKING_TYPES, SEVERITY_RANK, DecisionSeverity, DecisionStatus
from app.decision_center.models import ElfisDecisionItem
from app.decision_center.schemas import DecisionActionOut
from app.decision_center.service import DecisionCenterService
from app.events.event_bus import safe_publish
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.services.auth import write_audit
from app.work_queue.buckets import resolve_work_queue_bucket, waiting_reason_for
from app.work_queue.enums import (
    COMPLETED_LOOKBACK_DAYS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    WorkQueueBucket,
)
from app.work_queue.repository import WorkQueueRepository
from app.work_queue.schemas import (
    WaitingReasonOut,
    WorkQueueCountsOut,
    WorkQueueFiltersOut,
    WorkQueueItemOut,
    WorkQueueOut,
    WorkQueuePaginationOut,
    WorkQueuePrimaryActionOut,
    WorkQueueSummaryOut,
)

logger = logging.getLogger(__name__)

_CANDIDATE_LIMIT = 400


class WorkQueueService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkQueueRepository(db)
        self.decisions = DecisionCenterService(db)

    def get_queue(
        self,
        *,
        organization_id: int,
        permissions: list[str],
        bucket: str | None = None,
        severity: str | None = None,
        decision_type: str | None = None,
        source_type: str | None = None,
        search: str | None = None,
        sort: str = "priority",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sync: bool = False,
    ) -> WorkQueueOut:
        if sync:
            try:
                self.decisions.sync_open_decisions(organization_id)
            except Exception:
                logger.exception("work_queue_sync_failed org=%s", organization_id)
                self.db.rollback()

        page = max(1, page)
        page_size = min(MAX_PAGE_SIZE, max(1, page_size))
        search_clean = (search or "").strip()[:MAX_SEARCH_LENGTH] or None

        rows = self.repo.list_candidates(
            organization_id=organization_id,
            severity=severity,
            decision_type=decision_type,
            source_type=source_type,
            search=search_clean,
            limit=_CANDIDATE_LIMIT,
        )
        visible = [r for r in rows if self.decisions._can_view(r, permissions)]

        by_bucket: dict[str, list[ElfisDecisionItem]] = {
            WorkQueueBucket.TODO: [],
            WorkQueueBucket.IN_PROGRESS: [],
            WorkQueueBucket.WAITING: [],
            WorkQueueBucket.COMPLETED: [],
        }
        for row in visible:
            b = resolve_work_queue_bucket(row)
            # completed hors fenêtre déjà filtré en repo, double check
            if b == WorkQueueBucket.COMPLETED and not self._in_completed_window(row):
                continue
            by_bucket[b].append(row)

        counts = WorkQueueCountsOut(
            todo=len(by_bucket[WorkQueueBucket.TODO]),
            in_progress=len(by_bucket[WorkQueueBucket.IN_PROGRESS]),
            waiting=len(by_bucket[WorkQueueBucket.WAITING]),
            completed=len(by_bucket[WorkQueueBucket.COMPLETED]),
        )

        active_bucket = bucket or WorkQueueBucket.TODO
        if active_bucket not in by_bucket:
            raise HTTPException(400, detail="Bucket invalide")
        selected = list(by_bucket[active_bucket])
        selected = self._sort_rows(selected, sort=sort, bucket=active_bucket)

        total = len(selected)
        start = (page - 1) * page_size
        page_rows = selected[start : start + page_size]
        items = [self._to_item(r, permissions) for r in page_rows]
        total_pages = max(1, (total + page_size - 1) // page_size) if total else 0

        return WorkQueueOut(
            items=items,
            pagination=WorkQueuePaginationOut(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
            ),
            counts=counts,
            filters=WorkQueueFiltersOut(
                bucket=active_bucket,
                severity=severity,
                decision_type=decision_type,
                source_type=source_type,
                search=search_clean,
                sort=sort or "priority",
            ),
            generated_at=datetime.utcnow(),
        )

    def summary_for_command_center(
        self, *, organization_id: int, permissions: list[str], limit: int = 3
    ) -> WorkQueueSummaryOut:
        """Todo prioritaires uniquement + counts (pas de sync lourd systématique)."""
        try:
            self.decisions.sync_open_decisions(organization_id)
        except Exception:
            logger.exception("work_queue_cc_sync_failed org=%s", organization_id)
            self.db.rollback()

        queue = self.get_queue(
            organization_id=organization_id,
            permissions=permissions,
            bucket=WorkQueueBucket.TODO,
            sort="priority",
            page=1,
            page_size=limit,
            sync=False,
        )
        insights = [
            {
                "decision_id": item.decision_id,
                "title": item.title,
                "summary": item.summary,
                "severity": item.severity,
                "action_label": "Examiner",
                "action_path": f"/decisions/{item.decision_id}",
            }
            for item in queue.items[:limit]
        ]
        return WorkQueueSummaryOut(counts=queue.counts, todo_insights=insights)

    def start(
        self,
        *,
        organization_id: int,
        decision_id: str,
        permissions: list[str],
        user_id: int | None,
    ):
        row = self.decisions.repo.get(organization_id=organization_id, decision_id=decision_id)
        if row is None:
            raise HTTPException(404, detail="Décision introuvable")
        if not self.decisions._can_view(row, permissions):
            raise HTTPException(403, detail="Permission insuffisante")
        if row.status in {
            DecisionStatus.RESOLVED,
            DecisionStatus.DISMISSED,
            DecisionStatus.EXPIRED,
        }:
            raise HTTPException(409, detail="Cette décision n’est plus ouvrable.")
        if row.status == DecisionStatus.IN_PROGRESS:
            return self.decisions.get_detail(
                organization_id=organization_id,
                decision_id=decision_id,
                permissions=permissions,
                sync=False,
            )

        now = datetime.utcnow()
        row.status = DecisionStatus.IN_PROGRESS
        row.started_at = getattr(row, "started_at", None) or now
        row.started_by_user_id = user_id
        row.last_activity_at = now
        row.updated_at = now
        self.db.add(row)
        write_audit(
            self.db,
            user_id=user_id,
            organization_id=organization_id,
            action=f"decision.start:{row.id}",
            module="work_queue",
        )
        try:
            safe_publish(
                self.db,
                DomainEvent(
                    event_name=EventNames.DECISION_STARTED,
                    organization_id=organization_id,
                    aggregate_type="decision",
                    aggregate_id=row.id,
                    payload={
                        "decision_id": row.id,
                        "status": row.status,
                        "source_type": row.source_type,
                        "source_id": row.source_id,
                    },
                    idempotency_key=f"decision.started.v1:{row.id}",
                ),
            )
        except Exception:
            logger.exception("decision_started_event_failed id=%s", row.id)
        self.db.commit()
        self.db.refresh(row)
        return self.decisions.get_detail(
            organization_id=organization_id,
            decision_id=decision_id,
            permissions=permissions,
            sync=False,
        )

    def reopen_dismissed(
        self,
        *,
        organization_id: int,
        decision_id: str,
        permissions: list[str],
        user_id: int | None,
    ):
        row = self.decisions.repo.get(organization_id=organization_id, decision_id=decision_id)
        if row is None:
            raise HTTPException(404, detail="Décision introuvable")
        if not self.decisions._can_view(row, permissions):
            raise HTTPException(403, detail="Permission insuffisante")
        if row.status != DecisionStatus.DISMISSED:
            raise HTTPException(409, detail="Seules les décisions ignorées peuvent être rouvertes.")

        # Resync source : upsert peut déjà rouvrir si la cause est active
        self.decisions.sync_open_decisions(organization_id)
        self.db.refresh(row)
        if row.status == DecisionStatus.RESOLVED:
            raise HTTPException(
                409, detail="La cause n’existe plus — la décision a été résolue automatiquement."
            )
        if row.status in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS}:
            return self.decisions.get_detail(
                organization_id=organization_id,
                decision_id=decision_id,
                permissions=permissions,
                sync=False,
            )

        source = self.decisions.load_source(row)
        if source is None:
            raise HTTPException(409, detail="La ressource associée n’est plus disponible.")

        # Vérifier qu’une règle produit encore un draft actif
        from app.decision_center.rules import (
            AccountingProposalReadyRule,
            AccountingProposalRequiresReviewRule,
            DocumentAnalysisFailedRule,
            DocumentAnalysisRequiresReviewRule,
        )

        active = False
        if row.source_type == "accounting_proposal":
            for rule in (AccountingProposalRequiresReviewRule(), AccountingProposalReadyRule()):
                if rule.evaluate(source) is not None:
                    active = True
                    break
        elif row.source_type == "document_analysis":
            for rule in (DocumentAnalysisFailedRule(), DocumentAnalysisRequiresReviewRule()):
                if rule.evaluate(source) is not None:
                    active = True
                    break
        if not active:
            raise HTTPException(
                409, detail="La cause n’existe plus — impossible de rouvrir cette décision."
            )

        if row.status == DecisionStatus.DISMISSED:
            row.status = DecisionStatus.OPEN
            row.dismissed_at = None
            row.last_activity_at = datetime.utcnow()
            row.updated_at = datetime.utcnow()
            self.db.add(row)
            write_audit(
                self.db,
                user_id=user_id,
                organization_id=organization_id,
                action=f"decision.reopen:{row.id}",
                module="work_queue",
            )
            try:
                safe_publish(
                    self.db,
                    DomainEvent(
                        event_name=EventNames.DECISION_REOPENED,
                        organization_id=organization_id,
                        aggregate_type="decision",
                        aggregate_id=row.id,
                        payload={
                            "decision_id": row.id,
                            "status": row.status,
                            "source_type": row.source_type,
                            "source_id": row.source_id,
                        },
                        idempotency_key=f"decision.reopened.v1:{row.id}:{int(datetime.utcnow().timestamp())}",
                    ),
                )
            except Exception:
                logger.exception("decision_reopened_event_failed id=%s", row.id)
            self.db.commit()
            self.db.refresh(row)

        return self.decisions.get_detail(
            organization_id=organization_id,
            decision_id=decision_id,
            permissions=permissions,
            sync=False,
        )

    def _to_item(self, row: ElfisDecisionItem, permissions: list[str]) -> WorkQueueItemOut:
        bucket = resolve_work_queue_bucket(row)
        # Pas de N+1 : actions de liste sûres uniquement (détail pour les sensibles)
        can_view = self.decisions._can_view(row, permissions)
        list_actions: list[DecisionActionOut] = []

        if can_view and row.recommended_action_path:
            list_actions.append(
                DecisionActionOut(
                    action_type="open_source",
                    label="Voir la source",
                    method="NAVIGATE",
                    action_path=row.recommended_action_path,
                    opens_source=True,
                    enabled=True,
                )
            )
        if row.status == DecisionStatus.OPEN and bucket == WorkQueueBucket.TODO:
            list_actions.insert(
                0,
                DecisionActionOut(
                    action_type="start",
                    label="Commencer",
                    method="POST",
                    endpoint=f"/api/decisions/{row.id}/start",
                    enabled=True,
                    expected_resolution_behavior="mark_in_progress",
                ),
            )
        if row.status == DecisionStatus.IN_PROGRESS or bucket == WorkQueueBucket.IN_PROGRESS:
            list_actions.insert(
                0,
                DecisionActionOut(
                    action_type="resume",
                    label="Reprendre",
                    method="NAVIGATE",
                    action_path=f"/decisions/{row.id}",
                    enabled=True,
                    expected_resolution_behavior="open_detail",
                ),
            )
        if row.status in {DecisionStatus.OPEN, DecisionStatus.IN_PROGRESS} and row.severity not in {
            "critical",
        }:
            list_actions.append(
                DecisionActionOut(
                    action_type="dismiss",
                    label="Ignorer",
                    method="POST",
                    endpoint=f"/api/decisions/{row.id}/dismiss",
                    requires_confirmation=row.severity == "high",
                    enabled=True,
                    expected_resolution_behavior="dismiss_only",
                )
            )
        list_actions.append(
            DecisionActionOut(
                action_type="open_detail",
                label="Ouvrir",
                method="NAVIGATE",
                action_path=f"/decisions/{row.id}",
                enabled=True,
            )
        )

        primary = None
        for a in list_actions:
            if a.enabled:
                primary = WorkQueuePrimaryActionOut(
                    action_type=a.action_type,
                    label=a.label,
                    method=a.method,
                    action_path=a.action_path or a.path,
                    endpoint=a.endpoint,
                    enabled=a.enabled,
                )
                break

        waiting = waiting_reason_for(row)
        return WorkQueueItemOut(
            decision_id=row.id,
            decision_type=row.decision_type,
            bucket=bucket.value if hasattr(bucket, "value") else str(bucket),
            status=row.status,
            execution_status=getattr(row, "execution_status", None) or "idle",
            severity=row.severity,
            title=row.title,
            summary=row.summary,
            source_type=row.source_type,
            source_id=row.source_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            age_label=self._age_label(row.created_at),
            primary_action=primary,
            available_actions=list_actions,
            is_blocking=row.decision_type in {t.value for t in BLOCKING_TYPES},
            waiting_reason=WaitingReasonOut(**waiting) if waiting else None,
            last_activity=self._last_activity(row),
            progress_label=self._progress_label(row, bucket),
            required_permission=row.required_permission,
            evidence_summary=(row.explanation or "")[:160] or None,
            started_at=getattr(row, "started_at", None),
        )

    def _sort_rows(
        self, rows: list[ElfisDecisionItem], *, sort: str, bucket: str
    ) -> list[ElfisDecisionItem]:
        if bucket == WorkQueueBucket.COMPLETED or sort == "completed":
            return sorted(
                rows,
                key=lambda r: r.resolved_at or r.dismissed_at or r.updated_at or r.created_at,
                reverse=True,
            )
        if sort == "newest":
            return sorted(rows, key=lambda r: r.created_at, reverse=True)
        if sort == "oldest":
            return sorted(rows, key=lambda r: r.created_at)
        if sort == "updated":
            return sorted(rows, key=lambda r: r.updated_at or r.created_at, reverse=True)
        # priority default
        return sorted(rows, key=self._priority_key)

    @staticmethod
    def _priority_key(row: ElfisDecisionItem):
        sev = (
            SEVERITY_RANK.get(DecisionSeverity(row.severity), 0)
            if row.severity in DecisionSeverity._value2member_map_
            else 0
        )
        blocking = 1 if row.decision_type in {t.value for t in BLOCKING_TYPES} else 0
        created = row.created_at or datetime.utcnow()
        return (-sev, -blocking, created)

    @staticmethod
    def _in_completed_window(row: ElfisDecisionItem) -> bool:
        cutoff = datetime.utcnow() - timedelta(days=COMPLETED_LOOKBACK_DAYS)
        stamp = row.resolved_at or row.dismissed_at or row.updated_at or row.created_at
        return stamp is not None and stamp >= cutoff

    @staticmethod
    def _age_label(created_at: datetime | None) -> str | None:
        if not created_at:
            return None
        delta = datetime.utcnow() - created_at
        minutes = int(delta.total_seconds() // 60)
        if minutes < 60:
            return f"Il y a {max(1, minutes)} min"
        hours = minutes // 60
        if hours < 48:
            return f"Il y a {hours} h"
        days = hours // 24
        return f"Il y a {days} j"

    @staticmethod
    def _last_activity(row: ElfisDecisionItem) -> str | None:
        stamp = getattr(row, "last_activity_at", None) or row.updated_at
        action = row.last_action_type
        if not stamp:
            return None
        age = WorkQueueService._age_label(stamp)
        if action:
            return f"Dernière action ({action}) · {age}"
        return age

    @staticmethod
    def _progress_label(row: ElfisDecisionItem, bucket: str) -> str | None:
        if bucket == WorkQueueBucket.IN_PROGRESS:
            if row.execution_status == "running":
                return "Action en cours"
            if row.status == DecisionStatus.IN_PROGRESS:
                return "Examen commencé"
            return "En cours"
        if bucket == WorkQueueBucket.WAITING:
            return "En attente système"
        if bucket == WorkQueueBucket.COMPLETED:
            if row.status == DecisionStatus.RESOLVED:
                return "Résolue"
            if row.status == DecisionStatus.DISMISSED:
                return "Ignorée"
            return "Terminée"
        return "À traiter"
