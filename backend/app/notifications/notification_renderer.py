"""Validation et rendu sécurisé des notifications."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.notifications.notification_exceptions import NotificationValidationError
from app.notifications.notification_schemas import RenderedNotification
from app.notifications.templates import get_template

_DANGEROUS_SCHEMES = frozenset({"javascript", "data", "vbscript", "file"})


def validate_action_url(url: str | None) -> str | None:
    if url is None:
        return None
    cleaned = url.strip()
    if not cleaned:
        return None
    if len(cleaned) > 512:
        raise NotificationValidationError("action_url trop longue")
    lower = cleaned.lower()
    if any(lower.startswith(f"{s}:") for s in _DANGEROUS_SCHEMES):
        raise NotificationValidationError("action_url dangereuse refusée")
    # Uniquement chemins internes relatifs
    if cleaned.startswith("/"):
        if "//" in cleaned[1:2] or cleaned.startswith("//"):
            raise NotificationValidationError("action_url dangereuse refusée")
        if re.search(r"[\s<>\"']", cleaned):
            raise NotificationValidationError("action_url invalide")
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme or parsed.netloc:
        raise NotificationValidationError("Seules les URLs internes sont autorisées")
    raise NotificationValidationError("action_url invalide")


def sanitize_text(value: str, *, max_len: int) -> str:
    text = (value or "").replace("\x00", "").strip()
    # Pas de HTML utilisateur
    text = re.sub(r"[<>]", "", text)
    return text[:max_len]


def render_notification(template_name: str, data: dict[str, Any]) -> RenderedNotification:
    try:
        template = get_template(template_name)
    except KeyError as exc:
        raise NotificationValidationError(str(exc)) from exc
    rendered = template.render(data or {})
    title = sanitize_text(rendered.title, max_len=200)
    message = sanitize_text(rendered.message, max_len=2000)
    if not title or not message:
        raise NotificationValidationError("Titre ou message vide après rendu")
    action_url = validate_action_url(rendered.action_url)
    action_label = (
        sanitize_text(rendered.action_label, max_len=120) if rendered.action_label else None
    )
    return RenderedNotification(
        title=title,
        message=message,
        email_subject=sanitize_text(rendered.email_subject, max_len=200)
        if rendered.email_subject
        else None,
        email_text=sanitize_text(rendered.email_text, max_len=5000)
        if rendered.email_text
        else None,
        email_html=rendered.email_html[:8000] if rendered.email_html else None,
        action_url=action_url,
        action_label=action_label,
        severity=rendered.severity,
    )
