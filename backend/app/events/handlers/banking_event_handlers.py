"""Handlers Event Bus — notifications Banking consent (in-app, idempotentes)."""

from __future__ import annotations

import logging

from app.events.event_context import EventContext
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.exceptions import EventHandlerError
from app.models_saas import OrganizationMember, Role
from app.notifications.notification_exceptions import NotificationValidationError
from app.notifications.notification_schemas import NotificationRequest
from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import (
    NotificationCategories,
    NotificationChannel,
    NotificationSeverity,
    NotificationTypes,
    TEMPLATE_SYSTEM_GENERIC,
)

logger = logging.getLogger(__name__)


def _owner_user_ids(db, organization_id: int) -> list[int]:
    rows = (
        db.query(OrganizationMember)
        .join(Role, Role.id == OrganizationMember.role_id)
        .filter(
            OrganizationMember.organization_id == organization_id,
            Role.name.in_(("owner", "admin")),
            OrganizationMember.status == "active",
        )
        .all()
    )
    ids = [int(r.user_id) for r in rows if r.user_id]
    if ids:
        return ids
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        )
        .first()
    )
    return [int(member.user_id)] if member and member.user_id else []


class BankingConsentNotificationHandler(EventHandler):
    handler_name = "banking_consent_notifications_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        mapping = {
            EventNames.BANKING_CONSENT_EXPIRING: (
                NotificationTypes.BANKING_CONSENT_EXPIRING,
                "Connexion bancaire bientôt à renouveler",
                "Votre connexion bancaire devra bientôt être renouvelée.",
                NotificationSeverity.WARNING,
            ),
            EventNames.BANKING_REAUTHENTICATION_REQUIRED: (
                NotificationTypes.BANKING_REAUTHENTICATION_REQUIRED,
                "Réauthentification bancaire requise",
                "Une action est nécessaire pour renouveler votre connexion bancaire.",
                NotificationSeverity.ERROR,
            ),
            EventNames.BANKING_CONNECTION_REAUTHENTICATED: (
                NotificationTypes.BANKING_CONNECTION_REAUTHENTICATED,
                "Connexion bancaire renouvelée",
                "Votre connexion bancaire a été réauthentifiée avec succès.",
                NotificationSeverity.SUCCESS,
            ),
            EventNames.BANKING_CONNECTION_REVOKED: (
                NotificationTypes.BANKING_CONNECTION_REVOKED,
                "Connexion bancaire révoquée",
                "La connexion bancaire a été révoquée chez le fournisseur. Les données historiques sont conservées.",
                NotificationSeverity.ERROR,
            ),
        }
        spec = mapping.get(event.event_name)
        if not spec:
            return
        ntype, title, body, severity = spec
        connection_id = str((event.payload or {}).get("connection_id") or event.aggregate_id)
        for user_id in _owner_user_ids(context.db, event.organization_id):
            try:
                NotificationService(context.db).create_notification(
                    NotificationRequest(
                        organization_id=event.organization_id,
                        user_id=user_id,
                        notification_type=ntype,
                        category=NotificationCategories.BANKING,
                        severity=severity,
                        template_name=TEMPLATE_SYSTEM_GENERIC,
                        template_data={
                            "title": title,
                            "message": body,
                            "severity": severity,
                        },
                        channels=[NotificationChannel.IN_APP],
                        related_entity_type="bank_connection",
                        related_entity_id=connection_id or None,
                        action_url="/banque",
                        action_label="Ouvrir Banque",
                        source_event_id=str(event.event_id),
                        correlation_id=str(event.correlation_id),
                        idempotency_key=(
                            f"banking-notif:{event.event_name}:{event.organization_id}"
                            f":{user_id}:{event.idempotency_key or event.event_id}"
                        ),
                    )
                )
            except NotificationValidationError as exc:
                if "Aucun canal" in exc.message:
                    continue
                raise EventHandlerError(exc.message, retryable=False) from exc


_BANKING_CONSENT_EVENTS = (
    EventNames.BANKING_CONSENT_EXPIRING,
    EventNames.BANKING_REAUTHENTICATION_REQUIRED,
    EventNames.BANKING_CONNECTION_REAUTHENTICATED,
    EventNames.BANKING_CONNECTION_REVOKED,
)


def register_banking_event_handlers(registry) -> None:
    handler = BankingConsentNotificationHandler()
    for name in _BANKING_CONSENT_EVENTS:
        existing = [
            h for h in registry.get_handlers(name) if h.handler_name == handler.handler_name
        ]
        if not existing:
            registry.register(name, handler)
