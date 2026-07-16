from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_platform_admin
from app.models_saas import Organization, OrganizationMember, Role, Subscription, User
from app.services.auth import write_audit
from app.services.stripe_billing import serialize_subscription

router = APIRouter(
    prefix="/platform",
    tags=["platform", "elfadmin"],
    dependencies=[Depends(require_platform_admin)],
)


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
                    _latest_subscription(db, organization.id)
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
        "memberships": [
            {
                "organization_id": organization.id,
                "organization_name": organization.name,
                "role": role.name,
                "status": member.status,
            }
            for member, organization, role in memberships
        ],
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
        if status not in {"active", "suspended"}:
            raise HTTPException(400, detail="Statut non autorisé")
        if user.is_platform_admin and status != "active":
            raise HTTPException(400, detail="Un compte ELF Admin ne peut pas être suspendu")
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
