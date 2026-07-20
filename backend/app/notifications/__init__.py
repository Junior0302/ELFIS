"""ELFIS Notification Service V1."""

from __future__ import annotations

from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import NotificationTypes

__all__ = ["NotificationService", "NotificationTypes", "register_notification_handlers"]


def register_notification_handlers(registry) -> None:
    """Enregistre les handlers Event Bus liés aux notifications."""
    from app.events.event_types import EventNames
    from app.notifications.notification_handlers import (
        DeliveryEmailFailedNotificationHandler,
        DeliveryEmailSentNotificationHandler,
        DocumentArchivedNotificationHandler,
    )

    pairs = [
        (EventNames.DELIVERY_EMAIL_SENT, DeliveryEmailSentNotificationHandler()),
        (EventNames.DELIVERY_EMAIL_FAILED, DeliveryEmailFailedNotificationHandler()),
        (EventNames.VAULT_DOCUMENT_ARCHIVED, DocumentArchivedNotificationHandler()),
    ]
    for event_name, handler in pairs:
        existing = [
            h
            for h in registry.get_handlers(event_name)
            if h.handler_name == handler.handler_name
        ]
        if not existing:
            registry.register(event_name, handler)
