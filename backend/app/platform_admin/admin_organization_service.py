"""Organisation — suspension plateforme / détail agrégé."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models_saas import Organization, OrganizationMember, Role, Subscription, User
from app.platform_admin.admin_audit_service import AdminAuditService
from app.platform_admin.admin_exceptions import AdminNotFoundError, AdminValidationError
from app.platform_admin.admin_security import clamp_page, clamp_page_size, require_action_reason
from app.platform_admin.admin_types import OrgPlatformStatus


class AdminOrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AdminAuditService(db)

    def list_organizations(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        plan_code: str | None = None,
        subscription_status: str | None = None,
        has_payment_issue: bool | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        page_n = clamp_page(page)
        size = clamp_page_size(page_size)
        q = self.db.query(Organization)
        if query:
            like = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    Organization.name.ilike(like),
                    Organization.legal_name.ilike(like),
                    Organization.email.ilike(like),
                    Organization.siren.ilike(like),
                )
            )
        if status:
            q = q.filter(Organization.platform_status == status)
        if plan_code:
            q = q.filter(Organization.subscription_plan == plan_code)
        total = q.count()
        orgs = q.order_by(Organization.created_at.desc()).offset((page_n - 1) * size).limit(size).all()

        items = []
        for org in orgs:
            sub = self._latest_sub(org.id)
            if subscription_status and (not sub or sub.status != subscription_status):
                continue
            if has_payment_issue:
                if not sub or sub.status not in {"past_due", "unpaid", "incomplete"}:
                    continue
            items.append(self._org_summary(org, sub))
        return {"organizations": items, "total": total, "page": page_n, "page_size": size}

    def get_organization_detail(self, organization_id: int) -> dict[str, Any]:
        org = self.db.get(Organization, organization_id)
        if not org:
            raise AdminNotFoundError("Organisation introuvable")
        sub = self._latest_sub(organization_id)
        members = (
            self.db.query(OrganizationMember, User, Role)
            .join(User, User.id == OrganizationMember.user_id)
            .join(Role, Role.id == OrganizationMember.role_id)
            .filter(OrganizationMember.organization_id == organization_id)
            .all()
        )
        billing = {}
        try:
            from app.billing.billing_service import BillingService

            billing = BillingService(self.db).get_subscription(organization_id)
        except Exception:
            billing = {}

        counts = {
            "documents": self._count_docs(organization_id),
            "ai_executions": self._count_ai(organization_id),
            "accounting_proposals": self._count_proposals(organization_id),
            "jobs_failed": self._count_jobs(organization_id, "failed"),
        }
        return {
            "organization": {
                "id": org.id,
                "name": org.name,
                "legal_name": org.legal_name,
                "siren": org.siren,
                "email": org.email,
                "country": org.country,
                "subscription_plan": org.subscription_plan,
                "platform_status": getattr(org, "platform_status", None) or OrgPlatformStatus.ACTIVE,
                "platform_suspended_at": org.platform_suspended_at,
                "platform_suspend_reason": org.platform_suspend_reason or "",
                "created_at": org.created_at,
            },
            "users": [
                {
                    "user_id": u.id,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "status": u.status,
                    "role": r.name,
                    "membership_status": m.status,
                }
                for m, u, r in members
            ],
            "subscription": self._serialize_legacy_sub(sub),
            "billing": {
                "plan_code": billing.get("plan_code"),
                "status": billing.get("status"),
                "trial_ends_at": billing.get("trial_ends_at"),
                "entitlements": billing.get("entitlements") or {},
                "quotas": billing.get("quotas") or {},
                "usage": billing.get("usage") or {},
            },
            "counts": counts,
            "support_links": {
                "organization": f"/elfadmin/organisations/{organization_id}",
                "billing": f"/elfadmin/abonnements?org={organization_id}",
                "jobs": f"/elfadmin/jobs?organization_id={organization_id}",
                "incidents": f"/elfadmin/incidents?organization_id={organization_id}",
            },
        }

    def suspend(
        self,
        organization_id: int,
        *,
        actor: User,
        reason: str,
        ip: str | None = None,
    ) -> Organization:
        cleaned = require_action_reason(reason)
        org = self.db.get(Organization, organization_id)
        if not org:
            raise AdminNotFoundError("Organisation introuvable")
        prev = {"platform_status": getattr(org, "platform_status", OrgPlatformStatus.ACTIVE)}
        if prev["platform_status"] == OrgPlatformStatus.SUSPENDED:
            raise AdminValidationError("Organisation déjà suspendue")
        org.platform_status = OrgPlatformStatus.SUSPENDED
        org.platform_suspended_at = datetime.utcnow()
        org.platform_suspended_by = actor.id
        org.platform_suspend_reason = cleaned
        self.audit.record(
            actor=actor,
            action="organization.suspend",
            target_type="organization",
            target_id=str(organization_id),
            organization_id=organization_id,
            reason=cleaned,
            previous_state=prev,
            new_state={"platform_status": OrgPlatformStatus.SUSPENDED},
            ip=ip,
        )
        self._publish("platform.organization.suspended.v1", organization_id, actor.id, cleaned)
        self.db.flush()
        return org

    def restore(
        self,
        organization_id: int,
        *,
        actor: User,
        reason: str,
        ip: str | None = None,
    ) -> Organization:
        cleaned = require_action_reason(reason)
        org = self.db.get(Organization, organization_id)
        if not org:
            raise AdminNotFoundError("Organisation introuvable")
        prev = {"platform_status": getattr(org, "platform_status", OrgPlatformStatus.ACTIVE)}
        org.platform_status = OrgPlatformStatus.ACTIVE
        org.platform_suspended_at = None
        org.platform_suspended_by = None
        org.platform_suspend_reason = ""
        self.audit.record(
            actor=actor,
            action="organization.restore",
            target_type="organization",
            target_id=str(organization_id),
            organization_id=organization_id,
            reason=cleaned,
            previous_state=prev,
            new_state={"platform_status": OrgPlatformStatus.ACTIVE},
            ip=ip,
        )
        try:
            from app.billing.subscription_service import SubscriptionService

            SubscriptionService(self.db).sync_from_legacy(organization_id, rebuild=True)
        except Exception:
            pass
        self._publish("platform.organization.restored.v1", organization_id, actor.id, cleaned)
        self.db.flush()
        return org

    def is_suspended(self, organization_id: int) -> bool:
        org = self.db.get(Organization, organization_id)
        if not org:
            return False
        return getattr(org, "platform_status", OrgPlatformStatus.ACTIVE) == OrgPlatformStatus.SUSPENDED

    def _latest_sub(self, organization_id: int) -> Subscription | None:
        return (
            self.db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .order_by(Subscription.id.desc())
            .first()
        )

    def _org_summary(self, org: Organization, sub: Subscription | None) -> dict[str, Any]:
        return {
            "id": org.id,
            "name": org.name,
            "legal_name": org.legal_name,
            "platform_status": getattr(org, "platform_status", None) or OrgPlatformStatus.ACTIVE,
            "subscription_plan": org.subscription_plan,
            "subscription_status": sub.status if sub else "none",
            "created_at": org.created_at,
            "member_count": self.db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == org.id)
            .count(),
        }

    def _serialize_legacy_sub(self, sub: Subscription | None) -> dict[str, Any] | None:
        if not sub:
            return None
        return {
            "id": sub.id,
            "plan": sub.plan,
            "status": sub.status,
            "trial_end": sub.trial_end,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "admin_revoked_at": sub.admin_revoked_at,
            "past_due_since": sub.past_due_since,
        }

    def _count_docs(self, org_id: int) -> int:
        try:
            from app.models_vault import VaultDocument

            return self.db.query(VaultDocument).filter(VaultDocument.organization_id == org_id).count()
        except Exception:
            return 0

    def _count_ai(self, org_id: int) -> int:
        try:
            from app.ai.ai_models import ElfisAIExecution

            return (
                self.db.query(ElfisAIExecution)
                .filter(ElfisAIExecution.organization_id == org_id)
                .count()
            )
        except Exception:
            return 0

    def _count_proposals(self, org_id: int) -> int:
        try:
            from app.accounting.accounting_models import ElfisAccountingProposal

            return (
                self.db.query(ElfisAccountingProposal)
                .filter(ElfisAccountingProposal.organization_id == org_id)
                .count()
            )
        except Exception:
            return 0

    def _count_jobs(self, org_id: int, status: str) -> int:
        try:
            from app.jobs.job_models import ElfisJob

            return (
                self.db.query(ElfisJob)
                .filter(ElfisJob.organization_id == org_id, ElfisJob.status == status)
                .count()
            )
        except Exception:
            return 0

    def _publish(self, event_name: str, organization_id: int, actor_id: int, reason: str) -> None:
        try:
            from app.events import safe_publish
            from app.events.event_schemas import DomainEvent

            safe_publish(
                self.db,
                DomainEvent(
                    event_name=event_name,
                    organization_id=organization_id,
                    aggregate_type="organization",
                    aggregate_id=str(organization_id),
                    payload={
                        "organization_id": organization_id,
                        "actor_user_id": actor_id,
                        "target_type": "organization",
                        "target_id": str(organization_id),
                        "reason_summary": (reason or "")[:200],
                    },
                    metadata={"actor_user_id": actor_id},
                    idempotency_key=f"{event_name}:{organization_id}:{uuid4()}",
                ),
                commit=False,
            )
        except Exception:
            pass
