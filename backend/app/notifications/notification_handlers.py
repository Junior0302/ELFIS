"""Handlers Event Bus → NotificationService."""

from __future__ import annotations

import logging

from app.events.event_context import EventContext
from app.events.event_registry import EventHandler
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.events.exceptions import EventHandlerError
from app.notifications.notification_exceptions import NotificationValidationError
from app.notifications.notification_schemas import NotificationRequest
from app.notifications.notification_service import NotificationService
from app.notifications.notification_types import (
    NotificationCategories,
    NotificationChannel,
    NotificationSeverity,
    NotificationTypes,
    TEMPLATE_ACCOUNTING_PROPOSAL_FAILED,
    TEMPLATE_ACCOUNTING_PROPOSAL_READY,
    TEMPLATE_ACCOUNTING_PROPOSAL_REJECTED,
    TEMPLATE_ACCOUNTING_PROPOSAL_REVIEW,
    TEMPLATE_ACCOUNTING_PROPOSAL_VALIDATED,
    TEMPLATE_DOCUMENT_ARCHIVED,
    TEMPLATE_DOCUMENT_EMAIL_FAILED,
    TEMPLATE_DOCUMENT_EMAIL_SENT,
)

logger = logging.getLogger(__name__)


def _actor_user_id(event: DomainEvent) -> int | None:
    raw = (event.metadata or {}).get("actor_user_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class DeliveryEmailSentNotificationHandler(EventHandler):
    handler_name = "delivery_email_sent_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.DELIVERY_EMAIL_SENT:
            raise EventHandlerError("event mismatch", retryable=False)
        user_id = _actor_user_id(event)
        if user_id is None:
            return
        payload = event.payload or {}
        try:
            NotificationService(context.db).create_notification(
                NotificationRequest(
                    organization_id=event.organization_id,
                    user_id=user_id,
                    notification_type=NotificationTypes.DELIVERY_EMAIL_SENT,
                    category=NotificationCategories.EMAIL,
                    severity=NotificationSeverity.SUCCESS,
                    template_name=TEMPLATE_DOCUMENT_EMAIL_SENT,
                    template_data={
                        "business_document_type": payload.get("business_document_type"),
                        "business_document_id": payload.get("business_document_id"),
                        "document_type": payload.get("document_type"),
                        "vault_document_id": payload.get("vault_document_id"),
                    },
                    channels=[NotificationChannel.IN_APP],
                    related_entity_type="vault_document",
                    related_entity_id=str(payload.get("vault_document_id") or "") or None,
                    source_event_id=str(event.event_id),
                    correlation_id=str(event.correlation_id),
                    idempotency_key=f"notification:{event.event_id}:{self.handler_name}",
                )
            )
        except NotificationValidationError as exc:
            if "Aucun canal" in exc.message:
                return
            raise EventHandlerError(exc.message, retryable=False) from exc


class DeliveryEmailFailedNotificationHandler(EventHandler):
    handler_name = "delivery_email_failed_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.DELIVERY_EMAIL_FAILED:
            raise EventHandlerError("event mismatch", retryable=False)
        user_id = _actor_user_id(event)
        if user_id is None:
            return
        payload = event.payload or {}
        try:
            NotificationService(context.db).create_notification(
                NotificationRequest(
                    organization_id=event.organization_id,
                    user_id=user_id,
                    notification_type=NotificationTypes.DELIVERY_EMAIL_FAILED,
                    category=NotificationCategories.EMAIL,
                    severity=NotificationSeverity.ERROR,
                    template_name=TEMPLATE_DOCUMENT_EMAIL_FAILED,
                    template_data={
                        "business_document_id": payload.get("business_document_id"),
                        "document_number": payload.get("document_number"),
                    },
                    channels=[NotificationChannel.IN_APP],
                    related_entity_type="sales_document",
                    related_entity_id=str(payload.get("business_document_id") or "") or None,
                    source_event_id=str(event.event_id),
                    correlation_id=str(event.correlation_id),
                    idempotency_key=f"notification:{event.event_id}:{self.handler_name}",
                )
            )
        except NotificationValidationError as exc:
            if "Aucun canal" in exc.message:
                return
            raise EventHandlerError(exc.message, retryable=False) from exc


class DocumentArchivedNotificationHandler(EventHandler):
    """Notifie uniquement si metadata.notify_user = true."""

    handler_name = "document_archived_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.VAULT_DOCUMENT_ARCHIVED:
            raise EventHandlerError("event mismatch", retryable=False)
        meta = event.metadata or {}
        if not meta.get("notify_user"):
            return
        user_id = _actor_user_id(event)
        if user_id is None:
            return
        payload = event.payload or {}
        try:
            NotificationService(context.db).create_notification(
                NotificationRequest(
                    organization_id=event.organization_id,
                    user_id=user_id,
                    notification_type=NotificationTypes.VAULT_DOCUMENT_ARCHIVED,
                    category=NotificationCategories.VAULT,
                    severity=NotificationSeverity.INFO,
                    template_name=TEMPLATE_DOCUMENT_ARCHIVED,
                    template_data={
                        "document_number": payload.get("document_number"),
                        "vault_document_id": payload.get("vault_document_id"),
                    },
                    channels=[NotificationChannel.IN_APP],
                    related_entity_type="vault_document",
                    related_entity_id=str(payload.get("vault_document_id") or "") or None,
                    source_event_id=str(event.event_id),
                    correlation_id=str(event.correlation_id),
                    idempotency_key=f"notification:{event.event_id}:{self.handler_name}",
                )
            )
        except NotificationValidationError as exc:
            if "Aucun canal" in exc.message:
                return
            raise EventHandlerError(exc.message, retryable=False) from exc


def _notify_accounting(
    event: DomainEvent,
    context: EventContext,
    *,
    handler_name: str,
    notification_type: str,
    template_name: str,
    severity: str,
) -> None:
    payload = event.payload or {}
    user_id = _actor_user_id(event)
    if user_id is None:
        proposal_id = str(payload.get("proposal_id") or "").strip()
        if proposal_id:
            from app.accounting.accounting_models import ElfisAccountingProposal

            row = (
                context.db.query(ElfisAccountingProposal)
                .filter(ElfisAccountingProposal.proposal_id == proposal_id)
                .first()
            )
            if row and row.user_id:
                user_id = int(row.user_id)
    if user_id is None:
        return
    try:
        NotificationService(context.db).create_notification(
            NotificationRequest(
                organization_id=event.organization_id,
                user_id=user_id,
                notification_type=notification_type,
                category=NotificationCategories.ACCOUNTING,
                severity=severity,
                template_name=template_name,
                template_data={
                    "proposal_id": payload.get("proposal_id"),
                    "document_number": payload.get("document_number"),
                    "document_type": payload.get("document_type"),
                    "vault_document_id": payload.get("vault_document_id"),
                },
                channels=[NotificationChannel.IN_APP],
                related_entity_type="accounting_proposal",
                related_entity_id=str(payload.get("proposal_id") or "") or None,
                source_event_id=str(event.event_id),
                correlation_id=str(event.correlation_id),
                idempotency_key=f"notification:{event.event_id}:{handler_name}",
            )
        )
    except NotificationValidationError as exc:
        if "Aucun canal" in exc.message:
            return
        raise EventHandlerError(exc.message, retryable=False) from exc


class AccountingProposalReadyNotificationHandler(EventHandler):
    handler_name = "accounting_proposal_ready_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.ACCOUNTING_PROPOSAL_READY:
            raise EventHandlerError("event mismatch", retryable=False)
        _notify_accounting(
            event,
            context,
            handler_name=self.handler_name,
            notification_type=NotificationTypes.ACCOUNTING_PROPOSAL_READY,
            template_name=TEMPLATE_ACCOUNTING_PROPOSAL_READY,
            severity=NotificationSeverity.SUCCESS,
        )


class AccountingProposalReviewNotificationHandler(EventHandler):
    handler_name = "accounting_proposal_review_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW:
            raise EventHandlerError("event mismatch", retryable=False)
        _notify_accounting(
            event,
            context,
            handler_name=self.handler_name,
            notification_type=NotificationTypes.ACCOUNTING_PROPOSAL_REQUIRES_REVIEW,
            template_name=TEMPLATE_ACCOUNTING_PROPOSAL_REVIEW,
            severity=NotificationSeverity.WARNING,
        )


class AccountingProposalValidatedNotificationHandler(EventHandler):
    handler_name = "accounting_proposal_validated_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.ACCOUNTING_PROPOSAL_VALIDATED:
            raise EventHandlerError("event mismatch", retryable=False)
        _notify_accounting(
            event,
            context,
            handler_name=self.handler_name,
            notification_type=NotificationTypes.ACCOUNTING_PROPOSAL_VALIDATED,
            template_name=TEMPLATE_ACCOUNTING_PROPOSAL_VALIDATED,
            severity=NotificationSeverity.SUCCESS,
        )


class AccountingProposalRejectedNotificationHandler(EventHandler):
    handler_name = "accounting_proposal_rejected_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name != EventNames.ACCOUNTING_PROPOSAL_REJECTED:
            raise EventHandlerError("event mismatch", retryable=False)
        _notify_accounting(
            event,
            context,
            handler_name=self.handler_name,
            notification_type=NotificationTypes.ACCOUNTING_PROPOSAL_REJECTED,
            template_name=TEMPLATE_ACCOUNTING_PROPOSAL_REJECTED,
            severity=NotificationSeverity.WARNING,
        )


class AccountingProposalFailedNotificationHandler(EventHandler):
    handler_name = "accounting_proposal_failed_notification_v1"

    def handle(self, event: DomainEvent, context: EventContext) -> None:
        if event.event_name not in (
            EventNames.ACCOUNTING_PROPOSAL_VALIDATION_FAILED,
            EventNames.ACCOUNTING_PROPOSAL_UNBALANCED,
        ):
            raise EventHandlerError("event mismatch", retryable=False)
        _notify_accounting(
            event,
            context,
            handler_name=self.handler_name,
            notification_type=NotificationTypes.ACCOUNTING_PROPOSAL_FAILED,
            template_name=TEMPLATE_ACCOUNTING_PROPOSAL_FAILED,
            severity=NotificationSeverity.ERROR,
        )
