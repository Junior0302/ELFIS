from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import (
    AIAgent,
    Company,
    Organization,
    OrganizationMember,
    Role,
    Subscription,
    Team,
    User,
)
from app.services.auth import ensure_rbac_catalog, get_user_memberships, write_audit

router = APIRouter(prefix="/org", tags=["organisation"])

MANAGEABLE_ROLES = {"admin", "cfo", "comptable", "employe", "auditeur"}


class MemberCreateIn(BaseModel):
    email: EmailStr
    role: str


class MemberUpdateIn(BaseModel):
    role: str | None = None
    status: str | None = None


def _require_org_manager(auth: AuthContext, organization_id: int) -> None:
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    if auth.organization_id != organization_id:
        raise HTTPException(403, detail="Organisation active incorrecte")
    auth.require("users.manage")


def _member_public(member: OrganizationMember, user: User, role: Role) -> dict:
    return {
        "membership_id": member.id,
        "uid": user.firebase_uid,
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "avatar": user.avatar or "",
        "role": role.name,
        "permissions": json.loads(role.permissions or "[]"),
        "status": member.status,
        "joined_at": member.joined_at.isoformat(),
    }


def _get_member_rows(db: Session, organization_id: int):
    return (
        db.query(OrganizationMember, User, Role)
        .join(User, User.id == OrganizationMember.user_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(OrganizationMember.organization_id == organization_id)
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )


@router.get("/tree")
def organization_tree(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        orgs = db.query(Organization).all()
        return {
            "organizations": [
                {
                    "id": o.id,
                    "name": o.name,
                    "plan": o.subscription_plan,
                    "country": o.country,
                }
                for o in orgs
            ]
        }
    return {"memberships": get_user_memberships(db, auth.user.id)}


@router.get("/{organization_id}")
def organization_detail(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, detail="Organisation introuvable")
    companies = db.query(Company).filter(Company.organization_id == organization_id).all()
    teams = db.query(Team).filter(Team.organization_id == organization_id).all()
    agents = db.query(AIAgent).filter(AIAgent.organization_id == organization_id).all()
    sub = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .order_by(Subscription.id.desc())
        .first()
    )
    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "legal_name": org.legal_name,
            "siren": org.siren,
            "vat_number": org.vat_number,
            "country": org.country,
            "currency": org.currency,
            "industry": org.industry,
            "subscription_plan": org.subscription_plan,
        },
        "subscription": (
            {
                "plan": sub.plan,
                "status": sub.status,
                "price": sub.price,
            }
            if sub
            else None
        ),
        "companies": [
            {
                "id": c.id,
                "name": c.name,
                "country": c.country,
                "currency": c.currency,
                "parent_company_id": c.parent_company_id,
            }
            for c in companies
        ],
        "teams": [{"id": t.id, "name": t.name} for t in teams],
        "ai_agents": [
            {"id": a.id, "name": a.name, "type": a.type, "status": a.status} for a in agents
        ],
    }


@router.get("/{organization_id}/members")
def organization_members(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    return {
        "members": [
            _member_public(member, user, role)
            for member, user, role in _get_member_rows(db, organization_id)
        ],
        "can_manage": "*" in auth.permissions or "users.manage" in auth.permissions,
        "roles": sorted(MANAGEABLE_ROLES),
    }


@router.post("/{organization_id}/members")
def add_organization_member(
    organization_id: int,
    payload: MemberCreateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    role_name = payload.role.strip().lower()
    if role_name not in MANAGEABLE_ROLES:
        raise HTTPException(400, detail="Rôle non autorisé")

    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not user.firebase_uid:
        raise HTTPException(
            404,
            detail="Cet utilisateur doit d’abord créer son compte Firebase avec cette adresse.",
        )
    existing = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, detail="Cet utilisateur appartient déjà à l’organisation")

    roles = ensure_rbac_catalog(db)
    member = OrganizationMember(
        user_id=user.id,
        organization_id=organization_id,
        role_id=roles[role_name].id,
        status="active",
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action=f"member.add:{user.email}:{role_name}",
        module="auth",
    )
    return {"ok": True, "member": _member_public(member, user, roles[role_name])}


@router.patch("/{organization_id}/members/{membership_id}")
def update_organization_member(
    organization_id: int,
    membership_id: int,
    payload: MemberUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == membership_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(404, detail="Membre introuvable")

    if payload.role is not None:
        role_name = payload.role.strip().lower()
        if role_name not in MANAGEABLE_ROLES:
            raise HTTPException(400, detail="Rôle non autorisé")
        roles = ensure_rbac_catalog(db)
        member.role_id = roles[role_name].id

    if payload.status is not None:
        status = payload.status.strip().lower()
        if status not in {"active", "suspended"}:
            raise HTTPException(400, detail="Statut non autorisé")
        if member.user_id == auth.user.id and status != "active":
            raise HTTPException(400, detail="Vous ne pouvez pas suspendre votre propre accès")
        member.status = status

    db.add(member)
    db.commit()
    role = db.get(Role, member.role_id)
    user = db.get(User, member.user_id)
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action=f"member.update:{membership_id}",
        module="auth",
    )
    return {"ok": True, "member": _member_public(member, user, role)}


@router.delete("/{organization_id}/members/{membership_id}")
def delete_organization_member(
    organization_id: int,
    membership_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == membership_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(404, detail="Membre introuvable")
    if member.user_id == auth.user.id:
        raise HTTPException(400, detail="Vous ne pouvez pas retirer votre propre accès")

    role = db.get(Role, member.role_id)
    if role and role.name == "owner":
        raise HTTPException(400, detail="Le propriétaire ne peut pas être retiré")

    user = db.get(User, member.user_id)
    email = user.email if user else str(member.user_id)
    uid = user.firebase_uid if user else ""
    db.delete(member)
    db.commit()
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action=f"member.remove:{email}",
        module="auth",
    )
    return {"ok": True, "uid": uid, "email": email}
