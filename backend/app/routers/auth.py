from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import User
from app.services.auth import (
    create_access_token,
    get_user_memberships,
    hash_password,
    upsert_firebase_user,
    write_audit,
)
from app.services.firebase_auth import FirebaseAuthError, verify_id_token
from app.services.invitations import (
    accept_invitation,
    leave_organization,
    list_notifications,
    list_pending_invitations_for_user,
    mark_notification_read,
    refuse_invitation,
    serialize_notification,
)
from app.services.plan_features import PLAN_FEATURES, PLAN_SEAT_LIMITS, ROLE_LABELS_FR

router = APIRouter(prefix="/auth", tags=["auth"])

AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    organization_name: str | None = None


class FirebaseSessionIn(BaseModel):
    id_token: str = Field(min_length=20)
    first_name: str | None = None
    last_name: str | None = None
    organization_name: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    memberships: list[dict]


class ProfileUpdateIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    avatar: str | None = Field(default=None, max_length=2048)
    password: str | None = None


def _is_allowed_avatar_url(avatar: str) -> bool:
    value = (avatar or "").strip()
    if not value:
        return True
    if value.startswith("/api/auth/avatars/"):
        return True
    lower = value.lower()
    return lower.startswith("https://") or lower.startswith("http://")


def _public_api_base(request: Request) -> str:
    configured = settings.public_api_url.strip().rstrip("/")
    if configured:
        return configured
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


class InvitationActionIn(BaseModel):
    token: str | None = None
    invitation_id: int | None = None


class ActiveOrganizationIn(BaseModel):
    organization_id: int


def _user_public(user: User) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone or "",
        "avatar": user.avatar or "",
        "status": user.status,
        "is_platform_admin": user.is_platform_admin,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "firebase_linked": bool(user.firebase_uid),
    }


def _issue_session(db: Session, user: User, request: Request | None = None, action: str = "login") -> TokenOut:
    memberships = get_user_memberships(db, user.id)
    if not memberships:
        raise HTTPException(403, detail="Aucune organisation rattachée à ce compte")
    org_id = memberships[0]["organization_id"]
    token = create_access_token({"sub": str(user.id), "org_id": org_id})
    write_audit(
        db,
        user_id=user.id,
        organization_id=org_id,
        action=action,
        module="auth",
        ip=request.client.host if request and request.client else "",
    )
    return TokenOut(access_token=token, user=_user_public(user), memberships=memberships)


@router.post("/firebase", response_model=TokenOut)
async def firebase_session(
    payload: FirebaseSessionIn,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        fb = await verify_id_token(payload.id_token)
    except FirebaseAuthError as exc:
        raise HTTPException(401, detail=exc.message) from exc

    user = upsert_firebase_user(
        db,
        firebase_uid=fb["uid"],
        email=fb["email"],
        first_name=(payload.first_name or "").strip(),
        last_name=(payload.last_name or "").strip(),
        organization_name=(payload.organization_name or "").strip() or None,
    )
    return _issue_session(db, user, request, action="firebase.login")


@router.post("/login", response_model=TokenOut)
def login(_: LoginIn):
    raise HTTPException(
        400,
        detail="Utilisez l’application web pour vous connecter.",
    )


@router.post("/register", response_model=TokenOut)
def register_legacy(_: RegisterIn):
    raise HTTPException(
        400,
        detail="Utilisez l’application web pour créer un compte.",
    )


@router.get("/me")
def me(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    user = db.query(User).filter(User.id == auth.user.id).first()
    if not user:
        raise HTTPException(401, detail="Non authentifié")
    memberships = get_user_memberships(db, user.id)
    pending = list_pending_invitations_for_user(db, user)
    unread = len(list_notifications(db, user.id, unread_only=True))
    return {
        "user": _user_public(user),
        "current_organization_id": auth.organization_id,
        "role": auth.role,
        "permissions": auth.permissions,
        "memberships": memberships,
        "pending_invitations": pending,
        "unread_notifications": unread,
        "role_labels": ROLE_LABELS_FR,
    }


@router.get("/plan-catalog")
def plan_catalog():
    return {
        "features": PLAN_FEATURES,
        "seat_limits": PLAN_SEAT_LIMITS,
        "role_labels": ROLE_LABELS_FR,
    }


@router.get("/invitations")
def my_invitations(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    return {"invitations": list_pending_invitations_for_user(db, auth.user)}


@router.post("/invitations/accept")
def accept_invite(
    payload: InvitationActionIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    if not payload.token and payload.invitation_id is None:
        raise HTTPException(400, detail="token ou invitation_id requis")
    try:
        membership = accept_invitation(
            db,
            user=auth.user,
            token=payload.token,
            invitation_id=payload.invitation_id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    memberships = get_user_memberships(db, auth.user.id)
    return {
        "ok": True,
        "organization_id": membership.organization_id,
        "memberships": memberships,
        "pending_invitations": list_pending_invitations_for_user(db, auth.user),
    }


@router.post("/invitations/refuse")
def refuse_invite(
    payload: InvitationActionIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    if not payload.token and payload.invitation_id is None:
        raise HTTPException(400, detail="token ou invitation_id requis")
    try:
        refuse_invitation(
            db,
            user=auth.user,
            token=payload.token,
            invitation_id=payload.invitation_id,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {
        "ok": True,
        "pending_invitations": list_pending_invitations_for_user(db, auth.user),
    }


@router.post("/organizations/{organization_id}/leave")
def leave_org(
    organization_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    try:
        leave_organization(db, user=auth.user, organization_id=organization_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    memberships = get_user_memberships(db, auth.user.id)
    return {"ok": True, "memberships": memberships}


@router.post("/active-organization")
def set_active_organization(
    payload: ActiveOrganizationIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    memberships = get_user_memberships(db, auth.user.id)
    current = next((m for m in memberships if m["organization_id"] == payload.organization_id), None)
    if not current:
        raise HTTPException(403, detail="Accès organisation refusé")
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=payload.organization_id,
        action="organization.switch",
        module="auth",
    )
    token = create_access_token(
        {"sub": str(auth.user.id), "org_id": payload.organization_id}
    )
    return {
        "ok": True,
        "access_token": token,
        "organization_id": payload.organization_id,
        "role": current["role"],
        "permissions": current["permissions"],
        "memberships": memberships,
    }


@router.get("/notifications")
def my_notifications(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    notes = list_notifications(db, auth.user.id)
    return {"notifications": [serialize_notification(n) for n in notes]}


@router.post("/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    try:
        note = mark_notification_read(db, user_id=auth.user.id, notification_id=notification_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return {"ok": True, "notification": serialize_notification(note)}


@router.patch("/me")
def update_profile(
    payload: ProfileUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")

    user = db.query(User).filter(User.id == auth.user.id).first()
    if not user:
        raise HTTPException(404, detail="Utilisateur introuvable")

    if payload.first_name is not None:
        user.first_name = payload.first_name.strip()
    if payload.last_name is not None:
        user.last_name = payload.last_name.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.avatar is not None:
        avatar = payload.avatar.strip()
        if avatar and not _is_allowed_avatar_url(avatar):
            raise HTTPException(400, detail="URL de photo invalide")
        # Normalise http→https pour les avatars hébergés sur l’API publique
        if avatar.startswith("http://") and "/api/auth/avatars/" in avatar:
            avatar = "https://" + avatar[len("http://") :]
        user.avatar = avatar
    if payload.password:
        if user.firebase_uid:
            raise HTTPException(
                400,
                detail="Le mot de passe doit être modifié depuis la session sécurisée.",
            )
        if len(payload.password) < 8:
            raise HTTPException(400, detail="Le mot de passe doit contenir au moins 8 caractères")
        user.password_hash = hash_password(payload.password)

    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        user_id=user.id,
        organization_id=auth.organization_id,
        action="profile.update",
        module="auth",
    )
    return {"ok": True, "user": _user_public(user)}


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Non authentifié")
    extension = AVATAR_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(400, detail="Formats acceptés : JPG, PNG ou WebP")
    content = await file.read()
    if not content:
        raise HTTPException(400, detail="Photo vide")
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(400, detail="La photo ne doit pas dépasser 5 Mo")

    user = db.get(User, auth.user.id)
    if not user:
        raise HTTPException(404, detail="Utilisateur introuvable")

    avatar_dir = settings.storage_path / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{user.firebase_uid or user.id}-{uuid4().hex}{extension}"
    target = avatar_dir / filename
    async with aiofiles.open(target, "wb") as output:
        await output.write(content)

    previous = Path(user.avatar).name if "/api/auth/avatars/" in (user.avatar or "") else ""
    if previous and previous != filename:
        old_path = avatar_dir / previous
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    base = _public_api_base(request)
    user.avatar = f"{base}/api/auth/avatars/{filename}"
    if user.avatar.startswith("http://") and "onrender.com" in user.avatar:
        user.avatar = "https://" + user.avatar[len("http://") :]
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        user_id=user.id,
        organization_id=auth.organization_id,
        action="profile.avatar.update",
        module="auth",
    )
    return {"ok": True, "user": _user_public(user)}


@router.get("/avatars/{filename}")
def get_avatar(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(404, detail="Photo introuvable")
    path = settings.storage_path / "avatars" / safe_name
    if not path.is_file():
        raise HTTPException(404, detail="Photo introuvable")
    media_type = {
        ".jpg": "image/jpeg",
        ".png": "image/png",
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
