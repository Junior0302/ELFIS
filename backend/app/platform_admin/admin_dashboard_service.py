"""Dashboard agrégé Platform Admin."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models_saas import Organization, Subscription, User
from app.platform_admin.admin_models import ElfisOperationalIncident
from app.platform_admin.admin_types import IncidentStatus, OrgPlatformStatus


class AdminDashboardService:
    def __init__(self, db: Session):
        self.db = db

    def _since(self, period: str) -> datetime:
        now = datetime.utcnow()
        mapping = {"24h": 1, "7d": 7, "30d": 30}
        days = mapping.get((period or "24h").lower(), 1)
        return now - timedelta(days=days)

    def get_dashboard(self, *, period: str = "24h") -> dict[str, Any]:
        since = self._since(period)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        orgs_total = self.db.query(func.count(Organization.id)).scalar() or 0
        orgs_suspended = (
            self.db.query(func.count(Organization.id))
            .filter(Organization.platform_status == OrgPlatformStatus.SUSPENDED)
            .scalar()
            or 0
        )
        orgs_active = orgs_total - orgs_suspended

        users_total = self.db.query(func.count(User.id)).scalar() or 0

        sub_counts = dict(
            self.db.query(Subscription.status, func.count(Subscription.id))
            .group_by(Subscription.status)
            .all()
        )

        jobs = self._job_counts()
        events_dead = self._event_dead_letter_count()
        delivery_failed = self._delivery_failed_since(since)
        ai_today = self._ai_count_since(today)
        docs_today = self._docs_count_since(today)
        proposals_today = self._proposals_count_since(today)
        awaiting_ocr = self._awaiting_ocr_count()
        requires_review = self._requires_review_count()
        open_incidents = (
            self.db.query(func.count(ElfisOperationalIncident.id))
            .filter(ElfisOperationalIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED]))
            .scalar()
            or 0
        )

        return {
            "period": period,
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "organizations_total": int(orgs_total),
            "organizations_active": int(orgs_active),
            "organizations_suspended": int(orgs_suspended),
            "users_total": int(users_total),
            "subscriptions_trialing": int(sub_counts.get("trialing") or 0),
            "subscriptions_active": int(sub_counts.get("active") or 0),
            "subscriptions_past_due": int(sub_counts.get("past_due") or 0),
            "subscriptions_cancelled": int(
                (sub_counts.get("canceled") or 0) + (sub_counts.get("cancelled") or 0)
            ),
            "documents_processed_today": int(docs_today),
            "ai_analyses_today": int(ai_today),
            "accounting_proposals_today": int(proposals_today),
            "jobs_pending": int(jobs.get("pending") or 0),
            "jobs_running": int(jobs.get("running") or 0),
            "jobs_failed": int(jobs.get("failed") or 0),
            "jobs_dead_letter": int(jobs.get("dead_letter") or 0),
            "events_dead_letter": int(events_dead),
            "email_deliveries_failed": int(delivery_failed),
            "extractions_awaiting_ocr": int(awaiting_ocr),
            "proposals_requires_review": int(requires_review),
            "incidents_open": int(open_incidents),
        }

    def _job_counts(self) -> dict[str, int]:
        try:
            from app.jobs.job_models import ElfisJob

            rows = self.db.query(ElfisJob.status, func.count(ElfisJob.id)).group_by(ElfisJob.status).all()
            return {str(s): int(c) for s, c in rows}
        except Exception:
            return {}

    def _event_dead_letter_count(self) -> int:
        try:
            from app.events.event_models import ElfisEvent

            return (
                self.db.query(func.count(ElfisEvent.id))
                .filter(ElfisEvent.status == "dead_letter")
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _delivery_failed_since(self, since: datetime) -> int:
        try:
            from app.models_saas import DocumentEmailLog

            return (
                self.db.query(func.count(DocumentEmailLog.id))
                .filter(
                    DocumentEmailLog.status == "failed",
                    DocumentEmailLog.created_at >= since,
                )
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _ai_count_since(self, since: datetime) -> int:
        try:
            from app.ai.ai_models import ElfisAIExecution

            return (
                self.db.query(func.count(ElfisAIExecution.id))
                .filter(ElfisAIExecution.created_at >= since)
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _docs_count_since(self, since: datetime) -> int:
        try:
            from app.models_vault import VaultDocument

            return (
                self.db.query(func.count(VaultDocument.id))
                .filter(VaultDocument.created_at >= since)
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _proposals_count_since(self, since: datetime) -> int:
        try:
            from app.accounting.accounting_models import ElfisAccountingProposal

            return (
                self.db.query(func.count(ElfisAccountingProposal.id))
                .filter(ElfisAccountingProposal.created_at >= since)
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _awaiting_ocr_count(self) -> int:
        try:
            from app.document_intelligence.document_models import ElfisDocumentTextExtraction

            return (
                self.db.query(func.count(ElfisDocumentTextExtraction.id))
                .filter(ElfisDocumentTextExtraction.status == "awaiting_ocr")
                .scalar()
                or 0
            )
        except Exception:
            return 0

    def _requires_review_count(self) -> int:
        try:
            from app.accounting.accounting_models import ElfisAccountingProposal

            return (
                self.db.query(func.count(ElfisAccountingProposal.id))
                .filter(ElfisAccountingProposal.status == "requires_review")
                .scalar()
                or 0
            )
        except Exception:
            return 0
