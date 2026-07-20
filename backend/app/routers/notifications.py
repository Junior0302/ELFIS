"""Routes utilisateur — centre de notifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.notifications.notification_exceptions import (
    NotificationNotFoundError,
    NotificationValidationError,
)
from app.notifications.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_active_subscription)],
)


class PreferenceUpdateIn(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = False
    digest_mode: str = "immediate"


@router.get("")
def list_notifications(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    items, total = NotificationService(db).list_notifications(
        organization_id=org_id,
        user_id=auth.user.id,
        status=status,
        category=category,
        severity=severity,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": max(1, page),
        "page_size": min(100, max(1, page_size)),
        "notifications": [i.model_dump() for i in items],
    }


@router.get("/unread-count")
def unread_count(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    return {
        "count": NotificationService(db).get_unread_count(
            organization_id=org_id, user_id=auth.user.id
        )
    }


@router.post("/read-all")
def mark_all_read(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    count = NotificationService(db).mark_all_as_read(
        organization_id=org_id, user_id=auth.user.id
    )
    return {"updated": count}


@router.get("/preferences")
def get_preferences(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    return {
        "preferences": NotificationService(db).get_preferences(
            organization_id=org_id, user_id=auth.user.id
        )
    }


@router.put("/preferences/{notification_type}")
def update_preference(
    notification_type: str,
    payload: PreferenceUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        pref = NotificationService(db).update_preferences(
            organization_id=org_id,
            user_id=auth.user.id,
            notification_type=notification_type,
            in_app_enabled=payload.in_app_enabled,
            email_enabled=payload.email_enabled,
            digest_mode=payload.digest_mode,
        )
    except NotificationValidationError as exc:
        raise HTTPException(400, detail=exc.message) from exc
    return {"preference": pref}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        item = NotificationService(db).mark_as_read(
            organization_id=org_id,
            user_id=auth.user.id,
            notification_id=notification_id,
        )
    except NotificationNotFoundError:
        raise HTTPException(404, detail="Notification introuvable") from None
    return {"notification": item.model_dump()}


@router.post("/{notification_id}/archive")
def archive(
    notification_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    org_id = auth.require_organization_id()
    if not auth.user:
        raise HTTPException(401, detail="Authentification requise")
    try:
        item = NotificationService(db).archive_notification(
            organization_id=org_id,
            user_id=auth.user.id,
            notification_id=notification_id,
        )
    except NotificationNotFoundError:
        raise HTTPException(404, detail="Notification introuvable") from None
    return {"notification": item.model_dump()}
