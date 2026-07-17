from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models_saas import DocumentEmailLog

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


EVENT_STATUS = {
    "request": "sent",
    "delivered": "delivered",
    "opened": "opened",
    "unique_opened": "opened",
    "soft_bounce": "bounced",
    "hard_bounce": "bounced",
    "blocked": "blocked",
    "error": "failed",
    "spam": "blocked",
}


@router.post("/brevo")
async def brevo_webhook(
    request: Request,
    x_comptapilot_webhook_secret: str | None = Header(default=None),
):
    secret = settings.brevo_webhook_secret.strip()
    if secret and x_comptapilot_webhook_secret != secret:
        raise HTTPException(401, detail="Webhook non autorisé")

    payload = await request.json()
    events = payload if isinstance(payload, list) else [payload]
    db: Session = SessionLocal()
    updated = 0
    try:
        for event in events:
            if not isinstance(event, dict):
                continue
            message_id = str(
                event.get("message-id")
                or event.get("messageId")
                or event.get("message_id")
                or ""
            ).strip()
            event_name = str(event.get("event") or event.get("type") or "").strip().lower()
            if not message_id or event_name not in EVENT_STATUS:
                continue
            log = (
                db.query(DocumentEmailLog)
                .filter(DocumentEmailLog.provider_message_id == message_id)
                .first()
            )
            if not log:
                # parfois Brevo préfixe <...>
                log = (
                    db.query(DocumentEmailLog)
                    .filter(DocumentEmailLog.provider_message_id.contains(message_id.strip("<>")))
                    .first()
                )
            if not log:
                continue
            new_status = EVENT_STATUS[event_name]
            log.status = new_status
            now = datetime.utcnow()
            if new_status == "delivered":
                log.delivered_at = now
            elif new_status == "opened":
                log.opened_at = now
            elif new_status == "bounced":
                log.bounced_at = now
                log.error_code = event_name
                log.error_message = str(event.get("reason") or event.get("error") or "")[:400]
            elif new_status in {"blocked", "failed"}:
                log.error_code = event_name
                log.error_message = str(event.get("reason") or event.get("error") or "")[:400]
            log.updated_at = now
            db.add(log)
            updated += 1
        db.commit()
    finally:
        db.close()
    return {"ok": True, "updated": updated}
