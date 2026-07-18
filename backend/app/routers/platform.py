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
