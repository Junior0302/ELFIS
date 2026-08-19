"""Repository packages / deliveries — claim SKIP LOCKED."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence
from uuid import uuid4

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.product_integrations.models import (
    ElfisProductDocumentDelivery,
    ElfisProductDocumentDeliveryAttempt,
    ElfisProductProcessingPackage,
)
from app.product_integrations.types import DeliveryStatus


class ProductIntegrationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_package(self, package_id: str) -> ElfisProductProcessingPackage | None:
        return self._db.get(ElfisProductProcessingPackage, package_id)

    def get_package_by_idempotency(self, key: str) -> ElfisProductProcessingPackage | None:
        return (
            self._db.query(ElfisProductProcessingPackage)
            .filter(ElfisProductProcessingPackage.idempotency_key == key)
            .first()
        )

    def add_package(self, row: ElfisProductProcessingPackage, *, commit: bool = True) -> None:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()

    def list_packages(
        self,
        *,
        organization_id: int | None,
        product_key: str | None = None,
        document_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisProductProcessingPackage], int]:
        q = self._db.query(ElfisProductProcessingPackage)
        if not platform:
            q = q.filter(ElfisProductProcessingPackage.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisProductProcessingPackage.organization_id == organization_id)
        if product_key:
            q = q.filter(ElfisProductProcessingPackage.product_key == product_key)
        if document_id:
            q = q.filter(ElfisProductProcessingPackage.document_id == document_id)
        if status:
            q = q.filter(ElfisProductProcessingPackage.status == status)
        total = q.count()
        items = (
            q.order_by(ElfisProductProcessingPackage.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def get_delivery(self, delivery_id: str) -> ElfisProductDocumentDelivery | None:
        return self._db.get(ElfisProductDocumentDelivery, delivery_id)

    def get_delivery_by_idempotency(self, key: str) -> ElfisProductDocumentDelivery | None:
        return (
            self._db.query(ElfisProductDocumentDelivery)
            .filter(ElfisProductDocumentDelivery.idempotency_key == key)
            .first()
        )

    def add_delivery(self, row: ElfisProductDocumentDelivery, *, commit: bool = True) -> None:
        self._db.add(row)
        if commit:
            self._db.commit()
            self._db.refresh(row)
        else:
            self._db.flush()

    def list_deliveries(
        self,
        *,
        organization_id: int | None,
        product_key: str | None = None,
        package_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        platform: bool = False,
    ) -> tuple[list[ElfisProductDocumentDelivery], int]:
        q = self._db.query(ElfisProductDocumentDelivery)
        if not platform:
            q = q.filter(ElfisProductDocumentDelivery.organization_id == organization_id)
        elif organization_id is not None:
            q = q.filter(ElfisProductDocumentDelivery.organization_id == organization_id)
        if product_key:
            q = q.filter(ElfisProductDocumentDelivery.product_key == product_key)
        if package_id:
            q = q.filter(ElfisProductDocumentDelivery.package_id == package_id)
        if status:
            q = q.filter(ElfisProductDocumentDelivery.status == status)
        total = q.count()
        items = (
            q.order_by(ElfisProductDocumentDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def add_attempt(self, row: ElfisProductDocumentDeliveryAttempt, *, commit: bool = False) -> None:
        self._db.add(row)
        if commit:
            self._db.commit()
        else:
            self._db.flush()

    def list_attempts(self, delivery_id: str) -> list[ElfisProductDocumentDeliveryAttempt]:
        return (
            self._db.query(ElfisProductDocumentDeliveryAttempt)
            .filter(ElfisProductDocumentDeliveryAttempt.delivery_id == delivery_id)
            .order_by(ElfisProductDocumentDeliveryAttempt.attempt_number.asc())
            .all()
        )

    def claim_deliveries(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: int,
        product_key: str | None = None,
    ) -> list[ElfisProductDocumentDelivery]:
        bind = self._db.get_bind()
        dialect = bind.dialect.name if bind is not None else "sqlite"
        if dialect == "postgresql":
            return self._claim_postgres(
                worker_id=worker_id,
                limit=limit,
                lease_seconds=lease_seconds,
                product_key=product_key,
            )
        return self._claim_sqlite(
            worker_id=worker_id,
            limit=limit,
            lease_seconds=lease_seconds,
            product_key=product_key,
        )

    def _claim_postgres(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: int,
        product_key: str | None,
    ) -> list[ElfisProductDocumentDelivery]:
        now = datetime.utcnow()
        until = now + timedelta(seconds=lease_seconds)
        product_clause = "AND product_key = :product_key" if product_key else ""
        params: dict = {
            "now": now,
            "until": until,
            "worker_id": worker_id,
            "limit": limit,
            "queued": DeliveryStatus.QUEUED.value,
            "retrying": DeliveryStatus.RETRYING.value,
            "pending": DeliveryStatus.PENDING.value,
        }
        if product_key:
            params["product_key"] = product_key
        sql = text(
            f"""
            UPDATE elfis_product_document_deliveries
            SET status = 'delivering',
                locked_by = :worker_id,
                locked_until = :until,
                started_at = COALESCE(started_at, :now),
                updated_at = :now
            WHERE id IN (
                SELECT id FROM elfis_product_document_deliveries
                WHERE (
                    status IN (:queued, :retrying, :pending)
                    OR (
                        status = 'delivering'
                        AND locked_until IS NOT NULL
                        AND locked_until < :now
                    )
                )
                AND (next_retry_at IS NULL OR next_retry_at <= :now)
                {product_clause}
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT :limit
            )
            RETURNING id
            """
        )
        rows = self._db.execute(sql, params).fetchall()
        self._db.commit()
        ids = [r[0] for r in rows]
        if not ids:
            return []
        return (
            self._db.query(ElfisProductDocumentDelivery)
            .filter(ElfisProductDocumentDelivery.id.in_(ids))
            .all()
        )

    def _claim_sqlite(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: int,
        product_key: str | None,
    ) -> list[ElfisProductDocumentDelivery]:
        now = datetime.utcnow()
        until = now + timedelta(seconds=lease_seconds)
        q = self._db.query(ElfisProductDocumentDelivery).filter(
            or_(
                ElfisProductDocumentDelivery.status.in_(
                    [
                        DeliveryStatus.QUEUED.value,
                        DeliveryStatus.RETRYING.value,
                        DeliveryStatus.PENDING.value,
                    ]
                ),
                and_(
                    ElfisProductDocumentDelivery.status == DeliveryStatus.DELIVERING.value,
                    ElfisProductDocumentDelivery.locked_until.isnot(None),
                    ElfisProductDocumentDelivery.locked_until < now,
                ),
            ),
            or_(
                ElfisProductDocumentDelivery.next_retry_at.is_(None),
                ElfisProductDocumentDelivery.next_retry_at <= now,
            ),
        )
        if product_key:
            q = q.filter(ElfisProductDocumentDelivery.product_key == product_key)
        candidates = q.order_by(ElfisProductDocumentDelivery.created_at.asc()).limit(limit).all()
        claimed: list[ElfisProductDocumentDelivery] = []
        for row in candidates:
            row.status = DeliveryStatus.DELIVERING.value
            row.locked_by = worker_id
            row.locked_until = until
            row.started_at = row.started_at or now
            row.updated_at = now
            claimed.append(row)
        if claimed:
            self._db.commit()
            for r in claimed:
                self._db.refresh(r)
        return claimed

    def heartbeat(self, delivery: ElfisProductDocumentDelivery, *, lease_seconds: int) -> None:
        delivery.locked_until = datetime.utcnow() + timedelta(seconds=lease_seconds)
        delivery.updated_at = datetime.utcnow()
        self._db.commit()

    def new_id(self) -> str:
        return str(uuid4())
