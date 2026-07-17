from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import (
    AIAgent,
    Company,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    Role,
    Subscription,
    Team,
    User,
)
from app.services.auth import ensure_rbac_catalog, get_user_memberships, write_audit
from app.services.invitations import (
    cancel_invitation,
    create_invitation,
    resend_invitation,
    serialize_invitation,
)
from app.services.plan_features import (
    ROLE_LABELS_FR,
    can_invite_more,
    count_org_seats_used,
    org_effective_plan,
)

router = APIRouter(prefix="/org", tags=["organisation"])

MANAGEABLE_ROLES = {"admin", "cfo", "comptable", "employe", "auditeur"}
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/svg+xml": ".svg",
}


class MemberCreateIn(BaseModel):
    email: EmailStr
    role: str


class MemberUpdateIn(BaseModel):
    role: str | None = None
    status: str | None = None


class OrganizationUpdateIn(BaseModel):
    name: str | None = None
    legal_name: str | None = None
    siren: str | None = None
    vat_number: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    iban: str | None = None
    bic: str | None = None
    share_capital: str | None = None
    legal_form: str | None = None
    legal_mentions: str | None = None
    logo: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None


def _org_public(org: Organization) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "legal_name": org.legal_name or "",
        "siren": org.siren or "",
        "vat_number": org.vat_number or "",
        "country": org.country or "FR",
        "currency": org.currency or "EUR",
        "industry": org.industry or "",
        "address": org.address or "",
        "postal_code": getattr(org, "postal_code", None) or "",
        "city": getattr(org, "city", None) or "",
        "phone": getattr(org, "phone", None) or "",
        "email": getattr(org, "email", None) or "",
        "website": getattr(org, "website", None) or "",
        "iban": getattr(org, "iban", None) or "",
        "bic": getattr(org, "bic", None) or "",
        "share_capital": getattr(org, "share_capital", None) or "",
        "legal_form": getattr(org, "legal_form", None) or "",
        "legal_mentions": getattr(org, "legal_mentions", None) or "",
        "logo": org.logo or "",
        "primary_color": getattr(org, "primary_color", None) or "#0B3D2E",
        "secondary_color": getattr(org, "secondary_color", None) or "#E7F2EC",
        "subscription_plan": org.subscription_plan,
    }


def _require_org_manager(auth: AuthContext, organization_id: int) -> None:
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    if auth.organization_id != organization_id:
        raise HTTPException(403, detail="Organisation active incorrecte")
    auth.require("users.manage")


def _delete_local_logo(logo_url: str) -> None:
    marker = "/api/org/logos/"
    if marker not in (logo_url or ""):
        return
    previous = Path(logo_url).name
    if not previous:
        return
    path = settings.storage_path / "logos" / previous
    thumb = settings.storage_path / "logos" / f"thumb_{previous}"
    if path.is_file():
        path.unlink(missing_ok=True)
    if thumb.is_file():
        thumb.unlink(missing_ok=True)


def _make_thumbnail(source: Path) -> None:
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return
    try:
        from PIL import Image  # type: ignore

        with Image.open(source) as img:
            img = img.convert("RGBA") if img.mode in ("P", "RGBA") else img.convert("RGB")
            img.thumbnail((320, 160))
            thumb = source.parent / f"thumb_{source.name}"
            img.save(thumb)
    except Exception:
        return


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
        "role_label": ROLE_LABELS_FR.get(role.name, role.name),
        "permissions": json.loads(role.permissions or "[]"),
        "status": member.status,
        "invited_by": member.invited_by,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
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


@router.get("/logos/{filename}")
def get_organization_logo(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(404, detail="Logo introuvable")
    path = settings.storage_path / "logos" / safe_name
    if not path.is_file():
        raise HTTPException(404, detail="Logo introuvable")
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="{safe_name}"',
        },
    )


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
        "organization": _org_public(org),
        "can_edit": "*" in auth.permissions or "settings.manage" in auth.permissions,
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


@router.post("/{organization_id}/logo")
async def upload_organization_logo(
    organization_id: int,
    request: Request,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    auth.require("settings.manage")
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, detail="Organisation introuvable")

    extension = LOGO_TYPES.get((file.content_type or "").lower())
    name_lower = (file.filename or "").lower()
    if not extension:
        if name_lower.endswith(".svg"):
            extension = ".svg"
        elif name_lower.endswith(".png"):
            extension = ".png"
        elif name_lower.endswith((".jpg", ".jpeg")):
            extension = ".jpg"
        else:
            raise HTTPException(400, detail="Formats acceptés : PNG, JPG, JPEG ou SVG")

    content = await file.read()
    if not content:
        raise HTTPException(400, detail="Fichier vide")
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(400, detail="Le logo ne doit pas dépasser 2 Mo")

    logo_dir = settings.storage_path / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    filename = f"org{organization_id}-{uuid4().hex}{extension}"
    target = logo_dir / filename
    async with aiofiles.open(target, "wb") as output:
        await output.write(content)
    _make_thumbnail(target)

    _delete_local_logo(org.logo or "")
    base = str(request.base_url).rstrip("/")
    org.logo = f"{base}/api/org/logos/{filename}"
    db.add(org)
    db.commit()
    db.refresh(org)
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action="organization.logo.update",
        module="organisation",
    )
    return {"ok": True, "organization": _org_public(org)}


@router.delete("/{organization_id}/logo")
def delete_organization_logo(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    auth.require("settings.manage")
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, detail="Organisation introuvable")
    _delete_local_logo(org.logo or "")
    org.logo = ""
    db.add(org)
    db.commit()
    db.refresh(org)
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action="organization.logo.delete",
        module="organisation",
    )
    return {"ok": True, "organization": _org_public(org)}


@router.patch("/{organization_id}")
def update_organization(
    organization_id: int,
    payload: OrganizationUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    auth.require("settings.manage")
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, detail="Organisation introuvable")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        if key in {"primary_color", "secondary_color"} and value and not str(value).startswith("#"):
            continue
        setattr(org, key, value)
    db.add(org)
    db.commit()
    db.refresh(org)
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action="organization.update",
        module="organisation",
    )
    return {"organization": _org_public(org)}


# NOTE: keep members routes below — patch organization was moved above members.


@router.get("/{organization_id}/members")
def organization_members(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user or auth.organization_id != organization_id:
        raise HTTPException(403, detail="Accès organisation refusé")
    members = [
        _member_public(member, user, role)
        for member, user, role in _get_member_rows(db, organization_id)
        if member.status != "removed"
    ]
    plan, sub_status = org_effective_plan(db, organization_id)
    seats = count_org_seats_used(db, organization_id)
    can_add, seat_message = can_invite_more(db, organization_id)
    return {
        "members": members,
        "can_manage": "*" in auth.permissions or "users.manage" in auth.permissions,
        "roles": sorted(MANAGEABLE_ROLES),
        "role_labels": ROLE_LABELS_FR,
        "plan": plan,
        "subscription_status": sub_status,
        "seats": seats,
        "can_invite": can_add,
        "seat_limit_message": seat_message,
    }


@router.post("/{organization_id}/members")
def invite_organization_member(
    organization_id: int,
    payload: MemberCreateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    """Invite un membre (compte existant ou nouveau) — n'impose pas d'abonnement personnel."""
    _require_org_manager(auth, organization_id)
    try:
        invite, raw_token, mail_warn = create_invitation(
            db,
            organization_id=organization_id,
            email=str(payload.email),
            role=payload.role,
            invited_by=auth.user.id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    org = db.get(Organization, organization_id)
    return {
        "ok": True,
        "invitation": serialize_invitation(invite, org),
        "invite_token": raw_token,
        "email_warning": mail_warn,
        "message": (
            "Invitation envoyée. Le collaborateur la verra dans Mon compte "
            "et bénéficiera de l’abonnement de l’organisation après acceptation."
        ),
    }


@router.get("/{organization_id}/invitations")
def list_organization_invitations(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    org = db.get(Organization, organization_id)
    rows = (
        db.query(OrganizationInvitation)
        .filter(OrganizationInvitation.organization_id == organization_id)
        .order_by(OrganizationInvitation.id.desc())
        .limit(100)
        .all()
    )
    return {"invitations": [serialize_invitation(r, org) for r in rows]}


@router.post("/{organization_id}/invitations/{invitation_id}/resend")
def resend_organization_invitation(
    organization_id: int,
    invitation_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    try:
        invite, raw_token, mail_warn = resend_invitation(
            db,
            invitation_id=invitation_id,
            organization_id=organization_id,
            actor_id=auth.user.id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    org = db.get(Organization, organization_id)
    return {
        "ok": True,
        "invitation": serialize_invitation(invite, org),
        "invite_token": raw_token,
        "email_warning": mail_warn,
    }


@router.delete("/{organization_id}/invitations/{invitation_id}")
def cancel_organization_invitation(
    organization_id: int,
    invitation_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    _require_org_manager(auth, organization_id)
    try:
        cancel_invitation(
            db,
            invitation_id=invitation_id,
            organization_id=organization_id,
            actor_id=auth.user.id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {"ok": True}


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

    target_role = db.get(Role, member.role_id)
    if target_role and target_role.name == "owner":
        raise HTTPException(400, detail="Le rôle du propriétaire ne peut pas être modifié")
    if member.user_id == auth.user.id and payload.role is not None:
        raise HTTPException(400, detail="Vous ne pouvez pas modifier votre propre rôle")

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
        raise HTTPException(400, detail="Utilisez « Quitter l’organisation » depuis Mon compte")

    role = db.get(Role, member.role_id)
    if role and role.name == "owner":
        raise HTTPException(400, detail="Le propriétaire ne peut pas être retiré")

    user = db.get(User, member.user_id)
    email = user.email if user else str(member.user_id)
    uid = user.firebase_uid if user else ""
    member.status = "removed"
    db.add(member)
    db.commit()
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=organization_id,
        action=f"member.remove:{email}",
        module="auth",
    )
    return {"ok": True, "uid": uid, "email": email}
