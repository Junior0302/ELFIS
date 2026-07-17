from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization
from app.services.auth import write_audit
from app.services.org_email_settings import (
    get_or_create_email_settings,
    serialize_email_settings,
    upsert_email_settings,
)
from app.services.sales_email import send_organization_test_email

router = APIRouter(prefix="/org", tags=["organisation-email"])


class EmailSettingsUpdateIn(BaseModel):
    sender_mode: str | None = None
    sender_name: str | None = None
    reply_to_email: str | None = None
    reply_to_name: str | None = None
    cc_email: str | None = None
    bcc_email: str | None = None
    invoice_default_subject: str | None = None
    invoice_default_message: str | None = None
    quote_default_subject: str | None = None
    quote_default_message: str | None = None
    email_signature: str | None = None
    send_copy_to_organization: bool | None = None
    custom_sender_email: str | None = None
    custom_domain: str | None = None


def _org(auth: AuthContext, db: Session) -> Organization:
    org_id = auth.require_organization_id()
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, detail="Organisation introuvable")
    return org


@router.get("/email-settings")
def get_email_settings(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("settings.manage")
    org = _org(auth, db)
    row = get_or_create_email_settings(db, org)
    return serialize_email_settings(row, org)


@router.put("/email-settings")
def put_email_settings(
    payload: EmailSettingsUpdateIn,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("settings.manage")
    org = _org(auth, db)
    row = upsert_email_settings(db, org, payload.model_dump(exclude_unset=True))
    write_audit(
        db,
        user_id=auth.user.id if auth.user else None,
        organization_id=org.id,
        action="email_settings_update",
        module="settings",
    )
    return serialize_email_settings(row, org)


@router.post("/email-settings/test")
def test_email_settings(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    auth.require("settings.manage")
    org = _org(auth, db)
    if not auth.user or not auth.user.email:
        raise HTTPException(400, detail="Adresse e-mail utilisateur introuvable")
    try:
        log = send_organization_test_email(
            db,
            org,
            to_email=auth.user.email,
            sent_by_user=auth.user,
        )
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return {
        "ok": log.status == "sent",
        "status": log.status,
        "recipient": log.recipient_email or log.recipient,
        "subject": log.subject,
        "sender_name": log.sender_name,
        "sender_email": log.sender_email,
        "reply_to_email": log.reply_to_email,
        "error_message": log.error_message or "",
    }
