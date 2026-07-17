from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_platform_admin
from app.models_saas import Organization, User
from app.services.auth import write_audit
from app.services.professional_emails import (
    activate_professional_email,
    create_professional_email_request,
    get_user_professional_emails,
    list_all_requests,
    reject_professional_email,
    reset_all_professional_email_requests,
    reset_professional_email_request,
    sender_options_for_user,
    serialize_professional_email,
    suspend_professional_email,
)

router = APIRouter(prefix="/professional-emails", tags=["professional-emails"])


class ActivateIn(BaseModel):
    email: str = ""
    notes: str = ""
    make_default: bool = True


class RejectIn(BaseModel):
    notes: str = ""


@router.get("/me")
def my_professional_emails(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    rows = get_user_professional_emails(db, auth.user.id)
    active = [r for r in rows if r.status == "active"]
    pending = [r for r in rows if r.status in ("pending", "creating")]
    return {
        "emails": [serialize_professional_email(r) for r in rows],
        "has_active": len(active) > 0,
        "has_pending": len(pending) > 0,
        "can_request": len(active) == 0 and len(pending) == 0,
    }


@router.get("/sender-options")
def my_sender_options(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("documents.send_email")
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    org = db.get(Organization, auth.organization_id) if auth.organization_id else None
    options = sender_options_for_user(db, auth.user, organization=org)
    default = next((o for o in options if o["is_default"]), options[0] if options else None)
    return {
        "options": options,
        "default_option_id": default["id"] if default else None,
    }


@router.post("/request")
def request_professional_email(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        row, notify = create_professional_email_request(
            db,
            auth.user,
            organization_id=auth.organization_id,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=auth.user.id,
        organization_id=auth.organization_id,
        action="professional_email.request",
        module="compte",
    )
    message = (
        "Votre demande a bien été enregistrée. "
        "Notre équipe prépare actuellement votre adresse professionnelle. "
        "Vous recevrez vos accès sous 24 heures maximum."
    )
    if notify.get("admin_notified"):
        message = (
            "Votre demande a bien été envoyée à notre équipe. "
            "Vous recevrez vos accès sous 24 heures maximum."
        )
    elif notify.get("error"):
        message = (
            "Votre demande est enregistrée côté admin, mais la notification e-mail "
            f"n’a pas pu partir ({notify['error']}). "
            "Contactez le support si besoin."
        )
    return {
        "ok": True,
        "message": message,
        "email": serialize_professional_email(row),
        "notify": notify,
    }


# ── Admin (ELF Admin) ────────────────────────────────────────────


@router.get("/admin/requests")
def admin_list_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    rows = list_all_requests(db, status=status)
    all_rows = list_all_requests(db)
    counts = {
        "all": len(all_rows),
        "pending": sum(1 for r in all_rows if r.status == "pending"),
        "creating": sum(1 for r in all_rows if r.status == "creating"),
        "active": sum(1 for r in all_rows if r.status == "active"),
        "suspended": sum(1 for r in all_rows if r.status == "suspended"),
        "rejected": sum(1 for r in all_rows if r.status == "rejected"),
    }
    items = []
    for row in rows:
        user = db.get(User, row.user_id)
        data = serialize_professional_email(row)
        data["user"] = {
            "id": user.id if user else None,
            "first_name": user.first_name if user else "",
            "last_name": user.last_name if user else "",
            "email": user.email if user else "",
            "status": user.status if user else "",
        }
        items.append(data)
    return {"requests": items, "counts": counts, "admin_id": admin.id}


@router.post("/admin/requests/reset-all")
def admin_reset_all(
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    result = reset_all_professional_email_requests(db, admin=admin)
    write_audit(
        db,
        user_id=admin.id,
        organization_id=None,
        action=f"professional_email.reset_all:{result['deleted_count']}",
        module="elfadmin",
    )
    return {"ok": True, **result}


@router.post("/admin/requests/{request_id}/activate")
def admin_activate(
    request_id: int,
    payload: ActivateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        row = activate_professional_email(
            db,
            request_id,
            admin=admin,
            email=payload.email,
            make_default=payload.make_default,
            notes=payload.notes,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=admin.id,
        organization_id=row.organization_id,
        action=f"professional_email.activate:{row.email}",
        module="elfadmin",
    )
    return {"ok": True, "email": serialize_professional_email(row)}


@router.post("/admin/requests/{request_id}/reject")
def admin_reject(
    request_id: int,
    payload: RejectIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        row = reject_professional_email(db, request_id, admin=admin, notes=payload.notes)
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=admin.id,
        organization_id=row.organization_id,
        action=f"professional_email.reject:{row.id}",
        module="elfadmin",
    )
    return {"ok": True, "email": serialize_professional_email(row)}


@router.post("/admin/requests/{request_id}/suspend")
def admin_suspend(
    request_id: int,
    payload: RejectIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        row = suspend_professional_email(db, request_id, admin=admin, notes=payload.notes)
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=admin.id,
        organization_id=row.organization_id,
        action=f"professional_email.suspend:{row.id}",
        module="elfadmin",
    )
    return {"ok": True, "email": serialize_professional_email(row)}


@router.post("/admin/requests/{request_id}/reset")
def admin_reset_one(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_platform_admin),
):
    try:
        result = reset_professional_email_request(db, request_id, admin=admin)
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    write_audit(
        db,
        user_id=admin.id,
        organization_id=None,
        action=f"professional_email.reset:{request_id}",
        module="elfadmin",
    )
    return {"ok": True, **result}
