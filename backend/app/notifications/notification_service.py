"""Service métier notifications."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.events.event_bus import safe_publish
from app.events.event_context import new_correlation_id, sanitize_error_message
from app.events.event_schemas import DomainEvent
from app.events.event_types import EventNames
from app.notifications.notification_email_sender import NotificationEmailSender
from app.notifications.notification_exceptions import (
    NotificationDuplicateError,
    NotificationNotFoundError,
    NotificationValidationError,
)
from app.notifications.notification_models import ElfisNotification
from app.notifications.notification_renderer import render_notification, validate_action_url
from app.notifications.notification_repository import NotificationRepository
from app.notifications.notification_schemas import (
    DeliveryResult,
    NotificationOut,
    NotificationRequest,
    NotificationResult,
)
from app.notifications.notification_types import (
    DeliveryStatus,
    DigestMode,
    NotificationChannel,
    NotificationStatus,
)
from app.notifications.templates import get_template

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session, *, email_sender: NotificationEmailSender | None = None):
        self._db = db
        self._repo = NotificationRepository(db)
        self._email = email_sender or NotificationEmailSender()

    def create_notification(self, request: NotificationRequest) -> NotificationResult:
        try:
            req = NotificationRequest.model_validate(request.model_dump())
        except Exception as exc:
            raise NotificationValidationError(str(exc)) from exc

        if req.idempotency_key:
            existing = self._repo.find_by_idempotency(req.idempotency_key)
            if existing:
                deliveries = self._repo.list_deliveries(existing.notification_id)
                return NotificationResult(
                    notification_id=existing.notification_id,
                    created=False,
                    status=existing.status,
                    deliveries=[
                        DeliveryResult(
                            channel=d.channel,
                            status=d.status,
                            recipient=d.recipient,
                            provider_message_id=d.provider_message_id,
                        )
                        for d in deliveries
                    ],
                )

        try:
            template = get_template(req.template_name)
        except KeyError as exc:
            raise NotificationValidationError(str(exc)) from exc

        rendered = render_notification(req.template_name, req.template_data)
        action_url = validate_action_url(req.action_url or rendered.action_url)
        action_label = (req.action_label or rendered.action_label or "")[:120] or None
        severity = (req.severity or rendered.severity or template.default_severity)[:32]

        channels = list(req.channels or template.default_channels or [NotificationChannel.IN_APP])
        channels = [c for c in channels if c in {
            NotificationChannel.IN_APP,
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.PUSH,
            NotificationChannel.WEBHOOK,
        }]
        # SMS / push / webhook non implémentés → skipped plus bas

        prefs = None
        if req.user_id is not None:
            prefs = self._repo.get_preference(
                organization_id=req.organization_id,
                user_id=req.user_id,
                notification_type=req.notification_type,
            )

        in_app_enabled = True
        email_enabled = bool(template.default_email_enabled)
        if prefs:
            if prefs.digest_mode == DigestMode.DISABLED:
                in_app_enabled = False
                email_enabled = False
            else:
                in_app_enabled = bool(prefs.in_app_enabled)
                email_enabled = bool(prefs.email_enabled)

        effective_channels: list[str] = []
        for ch in channels:
            if ch == NotificationChannel.IN_APP and in_app_enabled:
                effective_channels.append(ch)
            elif ch == NotificationChannel.EMAIL and email_enabled:
                effective_channels.append(ch)
            elif ch in (
                NotificationChannel.SMS,
                NotificationChannel.PUSH,
                NotificationChannel.WEBHOOK,
            ):
                effective_channels.append(ch)  # will be skipped

        if not effective_channels and NotificationChannel.IN_APP in channels and not in_app_enabled:
            # Aucun canal actif — ne crée rien (idempotent soft)
            raise NotificationValidationError("Aucun canal de notification actif")

        if not effective_channels:
            effective_channels = [NotificationChannel.IN_APP] if in_app_enabled else []

        if not effective_channels:
            raise NotificationValidationError("Aucun canal de notification actif")

        notification_id = str(uuid.uuid4())
        correlation_id = req.correlation_id or new_correlation_id()
        data = {
            k: v
            for k, v in (req.template_data or {}).items()
            if str(k).lower()
            not in {
                "pdf",
                "pdf_bytes",
                "token",
                "api_key",
                "service_role_key",
                "password",
            }
        }

        row = self._repo.create_notification(
            notification_id=notification_id,
            organization_id=req.organization_id,
            user_id=req.user_id,
            notification_type=req.notification_type,
            category=req.category or template.category,
            title=rendered.title,
            message=rendered.message,
            severity=severity,
            action_url=action_url,
            action_label=action_label,
            related_entity_type=req.related_entity_type,
            related_entity_id=req.related_entity_id,
            data=data,
            status=NotificationStatus.UNREAD,
            expires_at=req.expires_at,
            source_event_id=req.source_event_id,
            correlation_id=correlation_id,
            idempotency_key=req.idempotency_key,
        )

        delivery_results: list[DeliveryResult] = []
        now = datetime.utcnow()

        for channel in effective_channels:
            if channel == NotificationChannel.IN_APP:
                self._repo.create_delivery(
                    notification_id=notification_id,
                    channel=channel,
                    recipient=str(req.user_id) if req.user_id else "org",
                    status=DeliveryStatus.SENT,
                    attempt_count=1,
                    sent_at=now,
                    idempotency_key=f"{notification_id}:in_app",
                )
                delivery_results.append(
                    DeliveryResult(channel=channel, status=DeliveryStatus.SENT, recipient=str(req.user_id) if req.user_id else "org")
                )
            elif channel == NotificationChannel.EMAIL:
                recipient = (req.email_recipient or "").strip()
                deliv = self._repo.create_delivery(
                    notification_id=notification_id,
                    channel=channel,
                    recipient=recipient or None,
                    status=DeliveryStatus.PENDING,
                    attempt_count=0,
                    idempotency_key=f"{notification_id}:email:{recipient}",
                )
                if not recipient or not rendered.email_subject or not rendered.email_text:
                    deliv.status = DeliveryStatus.SKIPPED
                    deliv.last_error = "E-mail système non configuré pour ce template"
                    delivery_results.append(
                        DeliveryResult(channel=channel, status=DeliveryStatus.SKIPPED, recipient=recipient or None)
                    )
                else:
                    deliv.status = DeliveryStatus.PROCESSING
                    deliv.started_at = now
                    deliv.attempt_count = 1
                    send_result = self._email.send(
                        recipient=recipient,
                        subject=rendered.email_subject,
                        text_body=rendered.email_text,
                        html_body=rendered.email_html,
                    )
                    if send_result.ok:
                        deliv.status = DeliveryStatus.SENT
                        deliv.sent_at = datetime.utcnow()
                        deliv.provider = send_result.provider
                        deliv.provider_message_id = send_result.provider_message_id
                        delivery_results.append(
                            DeliveryResult(
                                channel=channel,
                                status=DeliveryStatus.SENT,
                                recipient=recipient,
                                provider_message_id=send_result.provider_message_id,
                            )
                        )
                    else:
                        deliv.status = DeliveryStatus.FAILED
                        deliv.failed_at = datetime.utcnow()
                        deliv.last_error = sanitize_error_message(send_result.error)
                        delivery_results.append(
                            DeliveryResult(channel=channel, status=DeliveryStatus.FAILED, recipient=recipient)
                        )
            else:
                self._repo.create_delivery(
                    notification_id=notification_id,
                    channel=channel,
                    recipient=None,
                    status=DeliveryStatus.SKIPPED,
                    last_error="Canal non implémenté en V1",
                    idempotency_key=f"{notification_id}:{channel}",
                )
                delivery_results.append(
                    DeliveryResult(channel=channel, status=DeliveryStatus.SKIPPED)
                )

        try:
            self._repo.commit()
            self._db.refresh(row)
        except Exception as exc:
            self._db.rollback()
            if req.idempotency_key:
                again = self._repo.find_by_idempotency(req.idempotency_key)
                if again:
                    raise NotificationDuplicateError(
                        "Notification déjà créée", existing_id=again.notification_id
                    ) from exc
            raise

        safe_publish(
            self._db,
            DomainEvent(
                event_name=EventNames.NOTIFICATION_CREATED,
                organization_id=req.organization_id,
                aggregate_type="notification",
                aggregate_id=notification_id,
                payload={
                    "notification_id": notification_id,
                    "notification_type": req.notification_type,
                    "category": row.category,
                    "severity": severity,
                },
                metadata={"source": "notification_service"},
                idempotency_key=f"notif_created:{notification_id}",
                correlation_id=uuid.UUID(correlation_id) if correlation_id else uuid.uuid4(),
                causation_id=uuid.UUID(req.source_event_id) if req.source_event_id else None,
            ),
        )

        logger.info(
            "notification_created",
            extra={
                "notification_id": notification_id,
                "notification_type": req.notification_type,
                "organization_id": req.organization_id,
                "user_id": req.user_id,
                "status": row.status,
                "source_event_id": req.source_event_id,
                "correlation_id": correlation_id,
            },
        )
        return NotificationResult(
            notification_id=notification_id,
            created=True,
            status=row.status,
            deliveries=delivery_results,
        )

    def list_notifications(
        self,
        *,
        organization_id: int,
        user_id: int,
        status: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[NotificationOut], int]:
        rows, total = self._repo.list_for_user(
            organization_id=organization_id,
            user_id=user_id,
            status=status,
            category=category,
            severity=severity,
            page=page,
            page_size=page_size,
        )
        return [self._to_out(r) for r in rows], total

    def get_notification(
        self, *, organization_id: int, user_id: int, notification_id: str
    ) -> NotificationOut:
        row = self._repo.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not row:
            raise NotificationNotFoundError()
        self._maybe_expire(row)
        if row.status == NotificationStatus.EXPIRED and row.organization_id == organization_id:
            pass
        row = self._repo.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not row:
            raise NotificationNotFoundError()
        return self._to_out(row)

    def get_unread_count(self, *, organization_id: int, user_id: int) -> int:
        return self._repo.unread_count(organization_id=organization_id, user_id=user_id)

    def mark_as_read(
        self, *, organization_id: int, user_id: int, notification_id: str
    ) -> NotificationOut:
        row = self._repo.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not row:
            raise NotificationNotFoundError()
        self._maybe_expire(row)
        row = self._repo.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not row:
            raise NotificationNotFoundError()
        if row.status == NotificationStatus.UNREAD:
            row.status = NotificationStatus.READ
            row.read_at = datetime.utcnow()
            row.updated_at = datetime.utcnow()
            self._repo.commit()
            safe_publish(
                self._db,
                DomainEvent(
                    event_name=EventNames.NOTIFICATION_READ,
                    organization_id=organization_id,
                    aggregate_type="notification",
                    aggregate_id=row.notification_id,
                    payload={"notification_id": row.notification_id},
                    metadata={"source": "notification_service", "actor_user_id": str(user_id)},
                    idempotency_key=f"notif_read:{row.notification_id}:{user_id}",
                    correlation_id=uuid.UUID(row.correlation_id)
                    if row.correlation_id
                    else uuid.uuid4(),
                ),
            )
        return self._to_out(row)

    def mark_all_as_read(self, *, organization_id: int, user_id: int) -> int:
        rows, _ = self._repo.list_for_user(
            organization_id=organization_id,
            user_id=user_id,
            status=NotificationStatus.UNREAD,
            page=1,
            page_size=500,
        )
        count = 0
        now = datetime.utcnow()
        for row in rows:
            row.status = NotificationStatus.READ
            row.read_at = now
            row.updated_at = now
            count += 1
        if count:
            self._repo.commit()
        return count

    def archive_notification(
        self, *, organization_id: int, user_id: int, notification_id: str
    ) -> NotificationOut:
        row = self._repo.get_for_user(
            organization_id=organization_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        if not row:
            raise NotificationNotFoundError()
        row.status = NotificationStatus.ARCHIVED
        row.archived_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        self._repo.commit()
        return self._to_out(row)

    def get_preferences(self, *, organization_id: int, user_id: int) -> list[dict]:
        rows = self._repo.list_preferences(organization_id=organization_id, user_id=user_id)
        return [
            {
                "notification_type": r.notification_type,
                "in_app_enabled": r.in_app_enabled,
                "email_enabled": r.email_enabled,
                "sms_enabled": r.sms_enabled,
                "push_enabled": r.push_enabled,
                "digest_mode": r.digest_mode,
            }
            for r in rows
        ]

    def update_preferences(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_type: str,
        in_app_enabled: bool = True,
        email_enabled: bool = False,
        digest_mode: str = DigestMode.IMMEDIATE,
    ) -> dict:
        if digest_mode not in {
            DigestMode.IMMEDIATE,
            DigestMode.DAILY,
            DigestMode.WEEKLY,
            DigestMode.DISABLED,
        }:
            raise NotificationValidationError("digest_mode invalide")
        row = self._repo.upsert_preference(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=notification_type.strip(),
            in_app_enabled=in_app_enabled,
            email_enabled=email_enabled,
            digest_mode=digest_mode,
        )
        return {
            "notification_type": row.notification_type,
            "in_app_enabled": row.in_app_enabled,
            "email_enabled": row.email_enabled,
            "digest_mode": row.digest_mode,
        }

    def _maybe_expire(self, row: ElfisNotification) -> None:
        if row.expires_at and row.expires_at <= datetime.utcnow():
            if row.status not in (NotificationStatus.EXPIRED, NotificationStatus.ARCHIVED):
                row.status = NotificationStatus.EXPIRED
                row.updated_at = datetime.utcnow()
                self._repo.commit()

    @staticmethod
    def _to_out(row: ElfisNotification) -> NotificationOut:
        return NotificationOut(
            notification_id=row.notification_id,
            notification_type=row.notification_type,
            category=row.category,
            title=row.title,
            message=row.message,
            severity=row.severity,
            status=row.status,
            action_url=row.action_url,
            action_label=row.action_label,
            related_entity_type=row.related_entity_type,
            related_entity_id=row.related_entity_id,
            created_at=row.created_at,
            read_at=row.read_at,
        )
