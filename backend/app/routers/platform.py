from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_platform_admin
from app.models_saas import Organization, OrganizationMember, Role, Subscription, User
from app.services.auth import write_audit
from app.services.mailer import email_status_public, probe_brevo_account
from app.services.professional_emails import ADMIN_NOTIFY_TO
from app.services.stripe_billing import serialize_subscription

router = APIRouter(
    prefix="/platform",
    tags=["platform", "elfadmin"],
    dependencies=[Depends(require_platform_admin)],
)


@router.get("/email-status")
def platform_email_status():
    """Diagnostic Brevo / PLATFORM_EMAIL_FROM (sans secrets) + ping compte Brevo."""
    probed = probe_brevo_account()
    return {
        **probed,
        "notify_to": ADMIN_NOTIFY_TO,
        "hint": probed.get("hint")
        or (
            "OK pour envoyer les demandes vers urequest@"
            if probed.get("brevo_ok")
            else "Sur Render : BREVO_API_KEY (clé xkeysib-…) + PLATFORM_EMAIL_FROM=contact@elfis-core.com"
        ),
    }


class PlatformUserUpdateIn(BaseModel):
    status: str | None = None


def _latest_subscription(db: Session, organization_id: int) -> Subscription | None:
    return (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )


@router.get("/overview")
def platform_overview(db: Session = Depends(get_db)):
    subscriptions = (
        db.query(Subscription.status, func.count(Subscription.id))
        .group_by(Subscription.status)
        .all()
    )
    return {
        "organizations": db.query(Organization).count(),
        "users": db.query(User).count(),
        "active_memberships": db.query(OrganizationMember)
        .filter(OrganizationMember.status == "active")
        .count(),
        "subscriptions_by_status": {status: count for status, count in subscriptions},
    }


@router.get("/organizations")
def platform_organizations(db: Session = Depends(get_db)):
    organizations = db.query(Organization).order_by(Organization.created_at.desc()).all()
    return {
        "organizations": [
            {
                "id": organization.id,
                "name": organization.name,
                "legal_name": organization.legal_name,
                "country": organization.country,
                "created_at": organization.created_at,
                "member_count": db.query(OrganizationMember)
                .filter(OrganizationMember.organization_id == organization.id)
                .count(),
                "subscription": serialize_subscription(
                    _latest_subscription(db, organization.id),
                    db=db,
                    organization_id=organization.id,
                ),
            }
            for organization in organizations
        ]
    }


@router.get("/organizations/{organization_id}")
def platform_organization_detail(organization_id: int, db: Session = Depends(get_db)):
    organization = db.get(Organization, organization_id)
    if not organization:
        raise HTTPException(404, detail="Organisation introuvable")
    members = (
        db.query(OrganizationMember, User, Role)
        .join(User, User.id == OrganizationMember.user_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(OrganizationMember.organization_id == organization_id)
        .all()
    )
    return {
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "legal_name": organization.legal_name,
            "siren": organization.siren,
            "vat_number": organization.vat_number,
            "country": organization.country,
            "currency": organization.currency,
            "created_at": organization.created_at,
        },
        "subscription": serialize_subscription(_latest_subscription(db, organization_id)),
        "members": [
            {
                "user_id": user.id,
                "email": user.email,
                "display_name": f"{user.first_name} {user.last_name}".strip(),
                "role": role.name,
                "status": member.status,
            }
            for member, user, role in members
        ],
    }


@router.get("/users")
def platform_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "display_name": f"{user.first_name} {user.last_name}".strip(),
                "status": user.status,
                "is_platform_admin": user.is_platform_admin,
                "last_login": user.last_login,
                "created_at": user.created_at,
                "organization_count": db.query(OrganizationMember)
                .filter(OrganizationMember.user_id == user.id)
                .count(),
            }
            for user in users
        ]
    }


@router.get("/users/{user_id}")
def platform_user_detail(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, detail="Utilisateur introuvable")
    memberships = (
        db.query(OrganizationMember, Organization, Role)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(OrganizationMember.user_id == user_id)
        .all()
    )
    from app.subscriptions.access import get_subscription_access, serialize_access

    org_subs = []
    for member, organization, role in memberships:
        access = get_subscription_access(db, organization.id)
        org_subs.append(
            {
                "organization_id": organization.id,
                "organization_name": organization.name,
                "role": role.name,
                "status": member.status,
                "subscription": serialize_access(access),
            }
        )
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "status": user.status,
            "is_platform_admin": user.is_platform_admin,
            "last_login": user.last_login,
            "created_at": user.created_at,
        },
        "memberships": org_subs,
    }


class SubscriptionAdminIn(BaseModel):
    reason_public: str = ""
    reason_internal: str = ""
    reason: str = ""


@router.post("/organizations/{organization_id}/subscriptions/sync")
def platform_sync_subscription(
    organization_id: int,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    from app.services.stripe_billing import sync_subscription_from_stripe
    from app.subscriptions.access import get_subscription_access, serialize_access

    row = _latest_subscription(db, organization_id)
    if not row or not row.stripe_subscription_id:
        raise HTTPException(404, detail="Aucun abonnement à synchroniser")
    sync_subscription_from_stripe(db, row.stripe_subscription_id)
    db.commit()
    write_audit(
        db,
        user_id=admin.id,
        organization_id=organization_id,
        action=f"elfadmin.subscription.sync:{row.stripe_subscription_id}",
        module="platform",
    )
    return {"subscription": serialize_access(get_subscription_access(db, organization_id))}


@router.post("/organizations/{organization_id}/subscriptions/revoke")
def platform_revoke_subscription(
    organization_id: int,
    payload: SubscriptionAdminIn,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    from app.subscriptions.admin_actions import admin_revoke_access
    from app.subscriptions.access import get_subscription_access, serialize_access
    from app.subscriptions.notifications import notify_org_owners

    row = _latest_subscription(db, organization_id)
    if not row:
        raise HTTPException(404, detail="Abonnement introuvable")
    if not (payload.reason_public or "").strip():
        raise HTTPException(400, detail="Motif public requis")
    admin_revoke_access(
        db,
        subscription=row,
        admin_user_id=admin.id,
        reason_public=payload.reason_public,
        reason_internal=payload.reason_internal,
    )
    notify_org_owners(
        db,
        organization_id=organization_id,
        notification_type="admin_revoked",
        subscription=row,
        suffix=f"revoke:{row.id}:{row.admin_revoked_at}",
        template_kwargs={"reason": payload.reason_public},
    )
    db.commit()
    return {"subscription": serialize_access(get_subscription_access(db, organization_id))}


@router.post("/organizations/{organization_id}/subscriptions/restore")
def platform_restore_subscription(
    organization_id: int,
    payload: SubscriptionAdminIn,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    from app.subscriptions.admin_actions import admin_restore_access
    from app.subscriptions.access import get_subscription_access, serialize_access

    row = _latest_subscription(db, organization_id)
    if not row:
        raise HTTPException(404, detail="Abonnement introuvable")
    admin_restore_access(db, subscription=row, admin_user_id=admin.id, reason=payload.reason)
    db.commit()
    return {"subscription": serialize_access(get_subscription_access(db, organization_id))}


@router.post("/organizations/{organization_id}/subscriptions/grant-trial")
def platform_grant_trial(
    organization_id: int,
    payload: SubscriptionAdminIn,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    from app.subscriptions.admin_actions import admin_grant_trial
    from app.subscriptions.access import get_subscription_access, serialize_access

    if not (payload.reason or payload.reason_internal or payload.reason_public).strip():
        raise HTTPException(400, detail="Motif requis pour réattribuer un essai")
    row = _latest_subscription(db, organization_id)
    admin_grant_trial(
        db,
        subscription=row,
        organization_id=organization_id,
        admin_user_id=admin.id,
        reason=payload.reason or payload.reason_internal or payload.reason_public,
    )
    db.commit()
    return {"subscription": serialize_access(get_subscription_access(db, organization_id))}


@router.get("/subscriptions/orphans")
def platform_orphan_subscriptions(db: Session = Depends(get_db)):
    """Abonnements Stripe sans organisation valide (anomalies)."""
    rows = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id.isnot(None))
        .order_by(Subscription.id.desc())
        .limit(200)
        .all()
    )
    orphans = []
    for row in rows:
        org = db.get(Organization, row.organization_id)
        if org is None:
            orphans.append(
                {
                    "subscription_id": row.id,
                    "organization_id": row.organization_id,
                    "stripe_subscription_id": row.stripe_subscription_id,
                    "stripe_customer_id": row.stripe_customer_id,
                    "status": row.status,
                }
            )
    return {"orphans": orphans}


@router.post("/subscriptions/ai-summary")
def platform_ai_subscription_summary(
    payload: dict,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    """Résumé lecture seule + suggestion (aucune action automatique)."""
    organization_id = int(payload.get("organization_id") or 0)
    if not organization_id:
        raise HTTPException(400, detail="organization_id requis")
    from app.subscriptions.access import get_subscription_access

    access = get_subscription_access(db, organization_id)
    suggestions: list[str] = []
    if access.subscription_status == "trialing" and access.trial_ends_at:
        suggestions.append("Envoyer le rappel de fin d’essai")
    if access.subscription_status == "past_due":
        suggestions.append("Contacter le client pour mettre à jour le moyen de paiement")
    if access.subscription_status == "checkout_pending":
        suggestions.append("Proposer de reprendre la souscription sécurisée")
    if not access.stripe_subscription_id and access.subscription_status == "none":
        suggestions.append("Inviter le client à démarrer l’essai gratuit")
    summary = (
        f"Organisation {organization_id} — statut {access.label} ({access.subscription_status}). "
        f"Accès produit : {'oui' if access.has_access else 'non'}. "
        f"Raison : {access.access_reason}."
    )
    write_audit(
        db,
        user_id=admin.id,
        organization_id=organization_id,
        action="elfadmin.ai_summary",
        module="platform",
    )
    db.commit()
    return {
        "summary": summary,
        "suggestions": suggestions,
        "requires_human_confirmation": True,
        "subscription": access.to_dict(),
    }


@router.patch("/users/{user_id}")
def update_platform_user(
    user_id: int,
    payload: PlatformUserUpdateIn,
    admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, detail="Utilisateur introuvable")
    if user.id == admin.id:
        raise HTTPException(400, detail="Vous ne pouvez pas modifier votre propre compte ici")

    if payload.status is not None:
        status = payload.status.strip().lower()
        if status not in {"active", "suspended", "banned"}:
            raise HTTPException(400, detail="Statut non autorisé (active, suspended, banned)")
        if user.is_platform_admin and status != "active":
            raise HTTPException(400, detail="Un compte ELF Admin ne peut pas être suspendu ou banni")
        user.status = status

    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        user_id=admin.id,
        organization_id=None,
        action=f"elfadmin.user.update:{user.email}:{user.status}",
        module="platform",
    )
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": f"{user.first_name} {user.last_name}".strip(),
            "status": user.status,
            "is_platform_admin": user.is_platform_admin,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "organization_count": db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == user.id)
            .count(),
        },
    }


@router.get("/events")
def platform_list_events(
    status: str | None = None,
    event_name: str | None = None,
    organization_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """Liste admin Event Bus — sans payload/metadata (ELF Admin uniquement)."""
    from app.events.event_repository import EventRepository

    rows, total = EventRepository(db).list_events(
        status=status,
        event_name=event_name,
        organization_id=organization_id,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "events": [
            {
                "id": row.id,
                "event_id": row.event_id,
                "event_name": row.event_name,
                "organization_id": row.organization_id,
                "status": row.status,
                "attempt_count": row.attempt_count,
                "max_attempts": row.max_attempts,
                "available_at": row.available_at,
                "processed_at": row.processed_at,
                "failed_at": row.failed_at,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.get("/events/{event_id}")
def platform_get_event(event_id: str, db: Session = Depends(get_db)):
    """Détail admin — payload filtré (sans secrets)."""
    from app.events.event_repository import EventRepository
    from app.events.event_schemas import FORBIDDEN_PAYLOAD_KEYS

    row = EventRepository(db).find_by_event_id(event_id)
    if not row:
        raise HTTPException(404, detail="Événement introuvable")

    def _filter(data: dict | None) -> dict:
        out = {}
        for key, value in (data or {}).items():
            if str(key).lower() in FORBIDDEN_PAYLOAD_KEYS:
                continue
            out[key] = value
        return out

    return {
        "id": row.id,
        "event_id": row.event_id,
        "event_name": row.event_name,
        "event_version": row.event_version,
        "organization_id": row.organization_id,
        "aggregate_type": row.aggregate_type,
        "aggregate_id": row.aggregate_id,
        "status": row.status,
        "attempt_count": row.attempt_count,
        "max_attempts": row.max_attempts,
        "available_at": row.available_at,
        "processed_at": row.processed_at,
        "failed_at": row.failed_at,
        "last_error": row.last_error,
        "idempotency_key": row.idempotency_key,
        "correlation_id": row.correlation_id,
        "causation_id": row.causation_id,
        "created_at": row.created_at,
        "payload": _filter(row.payload if isinstance(row.payload, dict) else {}),
        "metadata": _filter(row.metadata_json if isinstance(row.metadata_json, dict) else {}),
    }


@router.get("/notifications")
def platform_list_notifications(
    organization_id: int | None = None,
    user_id: int | None = None,
    notification_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """Liste admin notifications — sans message/data complets."""
    from app.notifications.notification_repository import NotificationRepository

    rows, total = NotificationRepository(db).list_platform(
        organization_id=organization_id,
        user_id=user_id,
        notification_type=notification_type,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "notifications": [
            {
                "notification_id": r.notification_id,
                "organization_id": r.organization_id,
                "user_id": r.user_id,
                "notification_type": r.notification_type,
                "category": r.category,
                "severity": r.severity,
                "status": r.status,
                "title": r.title,
                "created_at": r.created_at,
                "source_event_id": r.source_event_id,
            }
            for r in rows
        ],
    }


@router.get("/notifications/{notification_id}")
def platform_get_notification(notification_id: str, db: Session = Depends(get_db)):
    from app.notifications.notification_repository import NotificationRepository
    from app.notifications.notification_schemas import FORBIDDEN_DATA_KEYS

    repo = NotificationRepository(db)
    row = repo.find_by_notification_id(notification_id)
    if not row:
        raise HTTPException(404, detail="Notification introuvable")
    data = {
        k: v
        for k, v in (row.data or {}).items()
        if str(k).lower() not in FORBIDDEN_DATA_KEYS
    }
    deliveries = repo.list_deliveries(notification_id)
    return {
        "notification_id": row.notification_id,
        "organization_id": row.organization_id,
        "user_id": row.user_id,
        "notification_type": row.notification_type,
        "category": row.category,
        "title": row.title,
        "message": row.message,
        "severity": row.severity,
        "status": row.status,
        "action_url": row.action_url,
        "data": data,
        "source_event_id": row.source_event_id,
        "correlation_id": row.correlation_id,
        "created_at": row.created_at,
        "deliveries": [
            {
                "channel": d.channel,
                "status": d.status,
                "recipient": d.recipient,
                "attempt_count": d.attempt_count,
                "provider": d.provider,
                "sent_at": d.sent_at,
                "failed_at": d.failed_at,
                "last_error": d.last_error,
            }
            for d in deliveries
        ],
    }


@router.get("/jobs")
def platform_list_jobs(
    organization_id: int | None = None,
    job_name: str | None = None,
    queue_name: str | None = None,
    status: str | None = None,
    worker_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """Liste admin jobs — sans payload/result complets."""
    from datetime import datetime

    from app.jobs import bootstrap_job_handlers
    from app.jobs.job_service import JobService

    bootstrap_job_handlers()

    def _parse(v: str | None) -> datetime | None:
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", ""))
        except ValueError:
            return None

    rows, total = JobService(db).list_jobs(
        organization_id=organization_id,
        job_name=job_name,
        queue_name=queue_name,
        status=status,
        worker_id=worker_id,
        date_from=_parse(date_from),
        date_to=_parse(date_to),
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "jobs": [
            {
                "job_id": r.job_id,
                "job_name": r.job_name,
                "job_version": r.job_version,
                "queue_name": r.queue_name,
                "status": r.status,
                "priority": r.priority,
                "progress": r.progress,
                "progress_message": r.progress_message,
                "attempt_count": r.attempt_count,
                "max_attempts": r.max_attempts,
                "organization_id": r.organization_id,
                "user_id": r.user_id,
                "locked_by": r.locked_by,
                "available_at": r.available_at,
                "scheduled_at": r.scheduled_at,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "failed_at": r.failed_at,
                "cancelled_at": r.cancelled_at,
                "correlation_id": r.correlation_id,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.get("/jobs/{job_id}")
def platform_get_job(job_id: str, db: Session = Depends(get_db)):
    from app.jobs import bootstrap_job_handlers
    from app.jobs.job_exceptions import JobNotFoundError
    from app.jobs.job_logging import sanitize_job_error
    from app.jobs.job_service import JobService

    bootstrap_job_handlers()
    svc = JobService(db)
    try:
        job = svc.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    return {
        "job_id": job.job_id,
        "job_name": job.job_name,
        "job_version": job.job_version,
        "queue_name": job.queue_name,
        "status": job.status,
        "priority": job.priority,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
        "organization_id": job.organization_id,
        "user_id": job.user_id,
        "locked_by": job.locked_by,
        "available_at": job.available_at,
        "scheduled_at": job.scheduled_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "failed_at": job.failed_at,
        "cancelled_at": job.cancelled_at,
        "timeout_seconds": job.timeout_seconds,
        "idempotency_key": job.idempotency_key,
        "correlation_id": job.correlation_id,
        "causation_event_id": job.causation_event_id,
        "parent_job_id": job.parent_job_id,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "last_error": sanitize_job_error(job.last_error),
        "payload_summary": svc.filter_sensitive_dict(
            job.payload if isinstance(job.payload, dict) else {}
        ),
        "result_summary": svc.filter_sensitive_dict(
            job.result if isinstance(job.result, dict) else None
        )
        or None,
    }


@router.get("/jobs/{job_id}/attempts")
def platform_job_attempts(job_id: str, db: Session = Depends(get_db)):
    from app.jobs import bootstrap_job_handlers
    from app.jobs.job_exceptions import JobNotFoundError
    from app.jobs.job_logging import sanitize_job_error
    from app.jobs.job_service import JobService

    bootstrap_job_handlers()
    svc = JobService(db)
    try:
        attempts = svc.get_job_attempts(job_id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    return {
        "job_id": job_id,
        "attempts": [
            {
                "attempt_number": a.attempt_number,
                "worker_id": a.worker_id,
                "status": a.status,
                "started_at": a.started_at,
                "completed_at": a.completed_at,
                "failed_at": a.failed_at,
                "duration_ms": a.duration_ms,
                "error_type": a.error_type,
                "error_message": sanitize_job_error(a.error_message),
            }
            for a in attempts
        ],
    }


@router.post("/jobs/{job_id}/retry")
def platform_retry_job(job_id: str, db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    from app.jobs import bootstrap_job_handlers
    from app.jobs.job_exceptions import JobNotFoundError, JobValidationError
    from app.jobs.job_service import JobService

    bootstrap_job_handlers()
    svc = JobService(db)
    try:
        job = svc.retry_job(job_id, actor_user_id=admin.id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    except JobValidationError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return {"job_id": job.job_id, "status": job.status, "attempt_count": job.attempt_count}


@router.post("/jobs/{job_id}/cancel")
def platform_cancel_job(job_id: str, db: Session = Depends(get_db), admin: User = Depends(require_platform_admin)):
    from app.jobs import bootstrap_job_handlers
    from app.jobs.job_exceptions import JobNotFoundError, JobValidationError
    from app.jobs.job_service import JobService

    bootstrap_job_handlers()
    svc = JobService(db)
    try:
        job = svc.cancel_job(job_id, actor_user_id=admin.id)
    except JobNotFoundError:
        raise HTTPException(404, detail="Job introuvable") from None
    except JobValidationError as exc:
        raise HTTPException(400, detail=exc.message) from None
    return {"job_id": job.job_id, "status": job.status, "cancelled_at": job.cancelled_at}


@router.get("/ai/executions")
def platform_list_ai_executions(
    organization_id: int | None = None,
    task_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    from datetime import datetime

    from app.ai import bootstrap_ai_tasks
    from app.ai.ai_service import AIService

    bootstrap_ai_tasks()

    def _parse(v: str | None):
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", ""))
        except ValueError:
            return None

    rows, total = AIService(db).list_executions(
        organization_id=organization_id,
        task_name=task_name,
        provider=provider,
        model=model,
        status=status,
        date_from=_parse(date_from),
        date_to=_parse(date_to),
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "executions": [
            {
                "execution_id": r.execution_id,
                "task_name": r.task_name,
                "provider": r.provider,
                "model": r.model,
                "status": r.status,
                "organization_id": r.organization_id,
                "input_reference_type": r.input_reference_type,
                "input_reference_id": r.input_reference_id,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost": float(r.estimated_cost) if r.estimated_cost is not None else None,
                "latency_ms": r.latency_ms,
                "job_id": r.job_id,
                "correlation_id": r.correlation_id,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
            }
            for r in rows
        ],
    }


@router.get("/ai/executions/{execution_id}")
def platform_get_ai_execution(execution_id: str, db: Session = Depends(get_db)):
    from app.ai import bootstrap_ai_tasks
    from app.ai.ai_exceptions import AINotFoundError
    from app.ai.ai_security import sanitize_ai_error
    from app.ai.ai_service import AIService

    bootstrap_ai_tasks()
    try:
        row = AIService(db).get_execution(execution_id)
    except AINotFoundError:
        raise HTTPException(404, detail="Exécution IA introuvable") from None
    result = row.result if isinstance(row.result, dict) else None
    # Filtrage léger — pas de raw_text / prompts
    if result and "compatible_extraction" in result:
        result = {k: v for k, v in result.items() if k != "compatible_extraction"}
        result["compatible_extraction"] = {"present": True}
    return {
        "execution_id": row.execution_id,
        "task_name": row.task_name,
        "provider": row.provider,
        "model": row.model,
        "status": row.status,
        "organization_id": row.organization_id,
        "user_id": row.user_id,
        "input_reference_type": row.input_reference_type,
        "input_reference_id": row.input_reference_id,
        "result_summary": result,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
        "estimated_cost": float(row.estimated_cost) if row.estimated_cost is not None else None,
        "currency": row.currency,
        "latency_ms": row.latency_ms,
        "job_id": row.job_id,
        "correlation_id": row.correlation_id,
        "last_error": sanitize_ai_error(row.last_error),
        "created_at": row.created_at,
        "completed_at": row.completed_at,
        "failed_at": row.failed_at,
    }


@router.get("/ai/usage")
def platform_ai_usage(
    organization_id: int | None = None,
    task_name: str | None = None,
    provider: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    from app.ai import bootstrap_ai_tasks
    from app.ai.ai_service import AIService

    bootstrap_ai_tasks()
    rows, total = AIService(db).get_usage(
        organization_id=organization_id,
        task_name=task_name,
        provider=provider,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "usage": [
            {
                "execution_id": r.execution_id,
                "organization_id": r.organization_id,
                "task_name": r.task_name,
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost": float(r.estimated_cost) if r.estimated_cost is not None else None,
                "currency": r.currency,
                "request_date": r.request_date,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }


@router.get("/ai/document-analyses")
def platform_document_analyses(
    organization_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    from app.ai import bootstrap_ai_tasks
    from app.ai.ai_repository import AIRepository

    bootstrap_ai_tasks()
    rows, total = AIRepository(db).list_analyses(
        organization_id=organization_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "analyses": [
            {
                "analysis_id": r.analysis_id,
                "organization_id": r.organization_id,
                "vault_document_id": r.vault_document_id,
                "document_version": r.document_version,
                "document_type": r.document_type,
                "status": r.status,
                "current_stage": r.current_stage,
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "requires_review": r.requires_review,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
            }
            for r in rows
        ],
    }
