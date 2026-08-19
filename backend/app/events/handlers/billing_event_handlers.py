"""Handlers Event Bus — notifications Billing (idempotentes)."""

from __future__ import annotations

import logging
from datetime import datetime

from app.events.event_context import EventContext
from app.events.exceptions import EventHandlerError
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.models_saas import OrganizationMember
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


def _fmt_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        raw = value.replace("Z", "")
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(value)[:16]


def _owner_user_ids(db, organization_id: int) -> list[int]:
    rows = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role.in_(("owner", "admin")),
            OrganizationMember.status == "active",
        )
        .all()
    )
    return [int(r.user_id) for r in rows if r.user_id]


class BillingNotificationHandler(EventHandler):
    """Un handler unique pour plusieurs événements billing."""

    handler_name = "billing_notifications_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        mapping = {
            EventNames.BILLING_SUBSCRIPTION_TRIAL_STARTED: (
                NotificationTypes.BILLING_TRIAL_STARTED,
                "Votre essai gratuit a commencé",
                f"Essai de 14 jours actif jusqu’au {_fmt_date(event.payload.get('trial_ends_at'))}. "
                "Renouvellement automatique prévu ensuite.",
                NotificationSeverity.INFO,
            ),
            EventNames.BILLING_SUBSCRIPTION_TRIAL_ENDING: (
                NotificationTypes.BILLING_TRIAL_ENDING,
                "Fin d’essai approche",
                f"Votre essai de 14 jours se termine le {_fmt_date(event.payload.get('trial_ends_at'))}. "
                "Renouvellement automatique prévu.",
                NotificationSeverity.WARNING,
            ),
            EventNames.BILLING_SUBSCRIPTION_ACTIVATED: (
                NotificationTypes.BILLING_SUBSCRIPTION_ACTIVE,
                "Abonnement actif",
                "Votre abonnement ComptaPilot IA est actif. Renouvellement automatique.",
                NotificationSeverity.SUCCESS,
            ),
            EventNames.BILLING_SUBSCRIPTION_PAYMENT_SUCCEEDED: (
                NotificationTypes.BILLING_PAYMENT_SUCCEEDED,
                "Paiement confirmé",
                "Votre paiement a été accepté. Merci.",
                NotificationSeverity.SUCCESS,
            ),
            EventNames.BILLING_SUBSCRIPTION_PAYMENT_FAILED: (
                NotificationTypes.BILLING_PAYMENT_FAILED,
                "Paiement refusé",
                "Votre paiement n’a pas abouti. Mettez à jour votre moyen de paiement "
                f"avant le {_fmt_date(event.payload.get('grace_period_ends_at') or event.payload.get('current_period_ends_at'))} "
                "pour éviter une interruption des traitements.",
                NotificationSeverity.ERROR,
            ),
            EventNames.BILLING_SUBSCRIPTION_PAST_DUE: (
                NotificationTypes.BILLING_SUBSCRIPTION_PAST_DUE,
                "Paiement à régulariser",
                "Votre abonnement est en impayé. Mettez à jour votre moyen de paiement.",
                NotificationSeverity.WARNING,
            ),
            EventNames.BILLING_SUBSCRIPTION_CANCEL_SCHEDULED: (
                NotificationTypes.BILLING_SUBSCRIPTION_CANCEL_SCHEDULED,
                "Abonnement annulé",
                f"Votre accès reste actif jusqu’au {_fmt_date(event.payload.get('current_period_ends_at'))}. "
                "Pas de prochain renouvellement.",
                NotificationSeverity.WARNING,
            ),
            EventNames.BILLING_SUBSCRIPTION_CANCELLED: (
                NotificationTypes.BILLING_SUBSCRIPTION_CANCELLED,
                "Abonnement terminé",
                "Votre abonnement n’est plus actif. Vos données sont conservées.",
                NotificationSeverity.INFO,
            ),
            EventNames.BILLING_SUBSCRIPTION_SUSPENDED: (
                NotificationTypes.BILLING_SUBSCRIPTION_SUSPENDED,
                "Abonnement suspendu",
                "Votre accès a été suspendu. Contactez le support si besoin.",
                NotificationSeverity.ERROR,
            ),
            EventNames.BILLING_SUBSCRIPTION_REACTIVATED: (
                NotificationTypes.BILLING_SUBSCRIPTION_REACTIVATED,
                "Abonnement réactivé",
                "Votre accès a été rétabli.",
                NotificationSeverity.SUCCESS,
            ),
            EventNames.BILLING_SUBSCRIPTION_UPDATED: (
                NotificationTypes.BILLING_PLAN_CHANGED,
                "Changement de plan",
                f"Votre offre a été mise à jour ({event.payload.get('plan_code') or 'plan'}).",
                NotificationSeverity.INFO,
            ),
            EventNames.BILLING_QUOTA_WARNING: (
                NotificationTypes.BILLING_QUOTA_WARNING,
                "Quota bientôt atteint",
                f"Attention : utilisation élevée pour {event.payload.get('quota_code') or 'votre offre'}.",
                NotificationSeverity.WARNING,
            ),
            EventNames.BILLING_QUOTA_EXCEEDED: (
                NotificationTypes.BILLING_QUOTA_EXCEEDED,
                "Quota dépassé",
                f"Limite atteinte pour {event.payload.get('quota_code') or 'votre offre'}.",
                NotificationSeverity.ERROR,
            ),
        }
        spec = mapping.get(event.event_name)
        if not spec:
            return
        ntype, title, body, severity = spec
        owners = _owner_user_ids(context.db, event.organization_id)
        if not owners:
            # Fallback : premier user org
            member = (
                context.db.query(OrganizationMember)
                .filter(
                    OrganizationMember.organization_id == event.organization_id,
                    OrganizationMember.status == "active",
                )
                .first()
            )
            if member:
                owners = [int(member.user_id)]
        for user_id in owners:
            try:
                NotificationService(context.db).create_notification(
                    NotificationRequest(
                        organization_id=event.organization_id,
                        user_id=user_id,
                        notification_type=ntype,
                        category=NotificationCategories.BILLING,
                        severity=severity,
                        template_name=TEMPLATE_SYSTEM_GENERIC,
                        template_data={
                            "title": title,
                            "message": body,
                            "severity": severity,
                        },
                        channels=[NotificationChannel.IN_APP],
                        related_entity_type="subscription",
                        related_entity_id=str(event.payload.get("subscription_id") or "") or None,
                        action_url="/abonnement",
                        action_label="Voir l’abonnement",
                        source_event_id=str(event.event_id),
                        correlation_id=str(event.correlation_id),
                        idempotency_key=f"billing-notif:{event.event_name}:{event.organization_id}:{user_id}:{event.event_id}",
                    )
                )
            except NotificationValidationError as exc:
                if "Aucun canal" in exc.message:
                    continue
                raise EventHandlerError(exc.message, retryable=False) from exc


_BILLING_EVENT_NAMES = (
    EventNames.BILLING_SUBSCRIPTION_TRIAL_STARTED,
    EventNames.BILLING_SUBSCRIPTION_TRIAL_ENDING,
    EventNames.BILLING_SUBSCRIPTION_ACTIVATED,
    EventNames.BILLING_SUBSCRIPTION_PAYMENT_SUCCEEDED,
    EventNames.BILLING_SUBSCRIPTION_PAYMENT_FAILED,
    EventNames.BILLING_SUBSCRIPTION_PAST_DUE,
    EventNames.BILLING_SUBSCRIPTION_CANCEL_SCHEDULED,
    EventNames.BILLING_SUBSCRIPTION_CANCELLED,
    EventNames.BILLING_SUBSCRIPTION_SUSPENDED,
    EventNames.BILLING_SUBSCRIPTION_REACTIVATED,
    EventNames.BILLING_SUBSCRIPTION_UPDATED,
    EventNames.BILLING_QUOTA_WARNING,
    EventNames.BILLING_QUOTA_EXCEEDED,
)


def register_billing_event_handlers(registry) -> None:
    handler = BillingNotificationHandler()
    for name in _BILLING_EVENT_NAMES:
        existing = [h for h in registry.get_handlers(name) if h.handler_name == handler.handler_name]
        if not existing:
            registry.register(name, handler)
