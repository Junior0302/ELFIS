from __future__ import annotations

from sqlalchemy.orm import Session

from app.models_saas import Organization, OrganizationMember, Subscription

# Source unique plan → fonctionnalités (noms métier ComptaPilot)
PLAN_FEATURES: dict[str, list[str]] = {
    "starter": [
        "document_analysis",
        "basic_exports",
        "basic_invoicing",
    ],
    "pro": [
        "document_analysis",
        "advanced_analysis",
        "team_members",
        "advanced_exports",
        "supplier_intelligence",
        "basic_invoicing",
        "basic_exports",
        "intelligence_dashboard",
        "elfis_chat",
    ],
    "business": [
        "document_analysis",
        "advanced_analysis",
        "team_members",
        "multi_user_permissions",
        "advanced_exports",
        "supplier_intelligence",
        "basic_invoicing",
        "basic_exports",
        "intelligence_dashboard",
        "elfis_chat",
    ],
}

# Limite de membres actifs + invitations pending (Owner inclus)
PLAN_SEAT_LIMITS: dict[str, int] = {
    "starter": 1,
    "pro": 5,
    "business": 25,
}

ROLE_LABELS_FR: dict[str, str] = {
    "owner": "Propriétaire",
    "admin": "Administrateur",
    "cfo": "Directeur financier",
    "comptable": "Comptable",
    "employe": "Collaborateur",
    "auditeur": "Lecteur",
}


def normalize_plan(plan: str | None) -> str:
    name = (plan or "starter").strip().lower()
    if name in PLAN_FEATURES:
        return name
    if name in {"elfadmin"}:
        return "business"
    return "starter"


def org_effective_plan(db: Session, organization_id: int) -> tuple[str, str]:
    """Retourne (plan, status) depuis Subscription org, sinon Organization.subscription_plan."""
    sub = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    org = db.get(Organization, organization_id)
    if sub and sub.status in {"active", "trialing", "past_due"}:
        return normalize_plan(sub.plan or org.subscription_plan if org else "pro"), sub.status
    if org:
        return normalize_plan(org.subscription_plan), "none"
    return "starter", "none"


def plan_includes_feature(plan: str, feature: str) -> bool:
    return feature in PLAN_FEATURES.get(normalize_plan(plan), PLAN_FEATURES["starter"])


def seat_limit_for_plan(plan: str) -> int:
    return PLAN_SEAT_LIMITS.get(normalize_plan(plan), 1)


def count_org_seats_used(db: Session, organization_id: int) -> dict[str, int]:
    from app.models_saas import OrganizationInvitation

    active = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        )
        .count()
    )
    pending = (
        db.query(OrganizationInvitation)
        .filter(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.status == "pending",
        )
        .count()
    )
    return {"active": active, "pending_invites": pending, "used": active + pending}


def can_invite_more(db: Session, organization_id: int) -> tuple[bool, str]:
    plan, status = org_effective_plan(db, organization_id)
    if status not in {"active", "trialing", "past_due"} and plan == "starter":
        # Org sans abonnement Stripe : limite starter (Owner seul)
        limit = seat_limit_for_plan("starter")
    else:
        # Abonnement actif → au minimum les sièges Pro
        effective = plan if plan != "starter" or status in {"active", "trialing"} else "starter"
        if status in {"active", "trialing", "past_due"} and effective == "starter":
            effective = "pro"
        limit = seat_limit_for_plan(effective)
        plan = effective
    seats = count_org_seats_used(db, organization_id)
    if seats["used"] >= limit:
        return False, (
            f"Votre abonnement actuel ({plan}) autorise {limit} membre(s). "
            "Passez à l’offre supérieure pour ajouter un collaborateur."
        )
    if not plan_includes_feature(plan, "team_members") and seats["active"] >= 1:
        # starter sans team_members : pas d'invitation
        if plan == "starter":
            return False, (
                "L’ajout de membres nécessite un abonnement Pro. "
                "Contactez le propriétaire ou souscrivez depuis Abonnement."
            )
    return True, ""


def user_has_permission(permissions: list[str], permission: str) -> bool:
    if "*" in permissions:
        return True
    return permission in permissions


def can_use_feature(
    *,
    member_status: str,
    permissions: list[str],
    plan: str,
    subscription_status: str,
    feature: str,
    permission: str | None = None,
) -> tuple[bool, str]:
    """
    Accès = membre actif + abo org compatible + permission.
    Retourne (ok, reason_code).
    """
    if member_status != "active":
        return False, "not_active_member"
    if subscription_status not in {"active", "trialing", "past_due"} and feature not in PLAN_FEATURES["starter"]:
        # Fonctions starter disponibles même sans Stripe (essai produit limité)
        if not plan_includes_feature("starter", feature):
            return False, "subscription_inactive"
    effective_plan = plan
    if subscription_status in {"active", "trialing", "past_due"} and plan == "starter":
        effective_plan = "pro"
    if not plan_includes_feature(effective_plan, feature):
        return False, "plan_missing_feature"
    if permission and not user_has_permission(permissions, permission):
        return False, "permission_denied"
    return True, "ok"
