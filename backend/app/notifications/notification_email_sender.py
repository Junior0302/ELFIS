"""Envoi e-mail système — réutilise le mailer existant (pas de documents métier)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.events.event_context import sanitize_error_message
from app.services.mailer import email_configured, send_email

logger = logging.getLogger(__name__)


@dataclass
class NotificationEmailResult:
    ok: bool
    provider: str = ""
    provider_message_id: str = ""
    error: str = ""


class NotificationEmailSender:
    """Abstraction e-mail pour notifications système uniquement."""

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> NotificationEmailResult:
        if not email_configured():
            return NotificationEmailResult(
                ok=False,
                error="Service e-mail plateforme indisponible",
            )
        try:
            result = send_email(
                to_email=recipient,
                subject=subject,
                body=text_body,
                html_body=html_body,
            )
            return NotificationEmailResult(
                ok=True,
                provider=result.provider,
                provider_message_id=result.provider_message_id or "",
            )
        except Exception as exc:
            clean = sanitize_error_message(exc)
            logger.warning("notification_email_send_failed", extra={"error": clean})
            return NotificationEmailResult(ok=False, error=clean)
