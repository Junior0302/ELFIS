"""Persistance notifications."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.notifications.notification_models import (
    ElfisNotification,
    ElfisNotificationDelivery,
    ElfisNotificationPreference,
)
from app.notifications.notification_types import NotificationStatus


class NotificationRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_idempotency(self, key: str) -> ElfisNotification | None:
        if not key:
            return None
        return (
            self._db.query(ElfisNotification)
            .filter(ElfisNotification.idempotency_key == key)
            .first()
        )

    def find_by_notification_id(self, notification_id: str) -> ElfisNotification | None:
        return (
            self._db.query(ElfisNotification)
            .filter(ElfisNotification.notification_id == notification_id)
            .first()
        )

    def get_for_user(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_id: str,
    ) -> ElfisNotification | None:
        row = self.find_by_notification_id(notification_id)
        if not row or row.organization_id != organization_id:
            return None
        if row.user_id is not None and row.user_id != user_id:
            return None
        return row

    def create_notification(self, **kwargs) -> ElfisNotification:
        now = datetime.utcnow()
        row = ElfisNotification(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._db.add(row)
        return row

    def create_delivery(self, **kwargs) -> ElfisNotificationDelivery:
        now = datetime.utcnow()
        row = ElfisNotificationDelivery(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._db.add(row)
        return row

    def list_for_user(
        self,
        *,
        organization_id: int,
        user_id: int,
        status: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        include_expired: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ElfisNotification], int]:
        now = datetime.utcnow()
        q = self._db.query(ElfisNotification).filter(
            ElfisNotification.organization_id == organization_id,
            or_(
                ElfisNotification.user_id == user_id,
                ElfisNotification.user_id.is_(None),
            ),
            ElfisNotification.status != NotificationStatus.ARCHIVED,
        )
        if not include_expired:
            q = q.filter(
                or_(
                    ElfisNotification.expires_at.is_(None),
                    ElfisNotification.expires_at > now,
                ),
                ElfisNotification.status != NotificationStatus.EXPIRED,
            )
        if status:
            q = q.filter(ElfisNotification.status == status)
        if category:
            q = q.filter(ElfisNotification.category == category)
        if severity:
            q = q.filter(ElfisNotification.severity == severity)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def unread_count(self, *, organization_id: int, user_id: int) -> int:
        now = datetime.utcnow()
        return (
            self._db.query(ElfisNotification)
            .filter(
                ElfisNotification.organization_id == organization_id,
                or_(
                    ElfisNotification.user_id == user_id,
                    ElfisNotification.user_id.is_(None),
                ),
                ElfisNotification.status == NotificationStatus.UNREAD,
                or_(
                    ElfisNotification.expires_at.is_(None),
                    ElfisNotification.expires_at > now,
                ),
            )
            .count()
        )

    def get_preference(
        self, *, organization_id: int, user_id: int, notification_type: str
    ) -> ElfisNotificationPreference | None:
        return (
            self._db.query(ElfisNotificationPreference)
            .filter(
                ElfisNotificationPreference.organization_id == organization_id,
                ElfisNotificationPreference.user_id == user_id,
                ElfisNotificationPreference.notification_type == notification_type,
            )
            .first()
        )

    def list_preferences(
        self, *, organization_id: int, user_id: int
    ) -> list[ElfisNotificationPreference]:
        return (
            self._db.query(ElfisNotificationPreference)
            .filter(
                ElfisNotificationPreference.organization_id == organization_id,
                ElfisNotificationPreference.user_id == user_id,
            )
            .order_by(ElfisNotificationPreference.notification_type.asc())
            .all()
        )

    def upsert_preference(
        self,
        *,
        organization_id: int,
        user_id: int,
        notification_type: str,
        in_app_enabled: bool,
        email_enabled: bool,
        digest_mode: str,
    ) -> ElfisNotificationPreference:
        row = self.get_preference(
            organization_id=organization_id,
            user_id=user_id,
            notification_type=notification_type,
        )
        now = datetime.utcnow()
        if row:
            row.in_app_enabled = in_app_enabled
            row.email_enabled = email_enabled
            row.digest_mode = digest_mode
            row.updated_at = now
        else:
            row = ElfisNotificationPreference(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                user_id=user_id,
                notification_type=notification_type,
                in_app_enabled=in_app_enabled,
                email_enabled=email_enabled,
                digest_mode=digest_mode,
                created_at=now,
                updated_at=now,
            )
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_platform(
        self,
        *,
        organization_id: int | None = None,
        user_id: int | None = None,
        notification_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ElfisNotification], int]:
        q = self._db.query(ElfisNotification)
        if organization_id is not None:
            q = q.filter(ElfisNotification.organization_id == organization_id)
        if user_id is not None:
            q = q.filter(ElfisNotification.user_id == user_id)
        if notification_type:
            q = q.filter(ElfisNotification.notification_type == notification_type)
        if status:
            q = q.filter(ElfisNotification.status == status)
        total = q.count()
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        rows = (
            q.order_by(ElfisNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def list_deliveries(self, notification_id: str) -> list[ElfisNotificationDelivery]:
        return (
            self._db.query(ElfisNotificationDelivery)
            .filter(ElfisNotificationDelivery.notification_id == notification_id)
            .all()
        )

    def commit(self) -> None:
        self._db.commit()
