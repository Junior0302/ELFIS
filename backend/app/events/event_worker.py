"""Worker de traitement des événements (DatabaseEventBus V1)."""

from __future__ import annotations

import logging
import os
import random
import socket
import time
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.events.event_bus import DatabaseEventBus
from app.events.event_context import EventContext, log_event, sanitize_error_message
from app.events.event_models import ElfisEvent, ElfisEventDelivery
from app.events.event_registry import EventHandlerRegistry, default_registry
from app.events.event_repository import EventRepository
from app.events.event_schemas import DeliveryStatus, EventStatus
from app.events.exceptions import EventHandlerError

logger = logging.getLogger(__name__)


def compute_retry_delay_seconds(
    attempt_count: int,
    *,
    base_seconds: int | None = None,
    jitter: bool = True,
) -> int:
    """Backoff exponentiel 10, 30, 90, 270… avec plafond et jitter optionnel."""
    base = base_seconds if base_seconds is not None else settings.elfis_event_retry_base_seconds
    base = max(1, base)
    # attempt_count est le numéro de la tentative qui vient d'échouer (1-based après incrément)
    exp = max(0, attempt_count - 1)
    delay = base * (3**exp)
    delay = min(delay, 3600)
    if jitter:
        delay = int(delay * (0.85 + random.random() * 0.3))
    return max(base, delay)


def default_worker_id() -> str:
    configured = (settings.elfis_event_worker_id or "").strip()
    if configured:
        return configured[:128]
    return f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class EventWorker:
    def __init__(
        self,
        db: Session,
        *,
        registry: EventHandlerRegistry | None = None,
        worker_id: str | None = None,
        batch_size: int | None = None,
        lock_timeout_seconds: int | None = None,
    ):
        self._db = db
        self._registry = registry or default_registry
        self._repo = EventRepository(db)
        self._bus = DatabaseEventBus(db, registry=self._registry)
        self.worker_id = worker_id or default_worker_id()
        self.batch_size = batch_size or settings.elfis_event_worker_batch_size
        self.lock_timeout_seconds = (
            lock_timeout_seconds or settings.elfis_event_lock_timeout_seconds
        )

    def process_next_batch(self) -> int:
        claimed = self._repo.claim_events(
            worker_id=self.worker_id,
            batch_size=self.batch_size,
            lock_timeout_seconds=self.lock_timeout_seconds,
        )
        processed = 0
        for event_row in claimed:
            self.process_event(event_row.event_id)
            processed += 1
        return processed

    def process_event(self, event_id: str) -> None:
        # Nouvelle session logique : recharger après claim (commit déjà fait)
        event_row = self._repo.find_by_event_id(event_id)
        if not event_row:
            return
        domain = self._repo.to_domain(event_row)
        deliveries = self._repo.list_deliveries(event_id)
        if not deliveries:
            self.mark_processed(event_row)
            return

        any_retry = False
        any_dead = False
        any_failed = False

        for delivery in deliveries:
            if delivery.status == DeliveryStatus.processed.value:
                continue
            if delivery.status == DeliveryStatus.dead_letter.value:
                any_dead = True
                continue
            if delivery.status == DeliveryStatus.skipped.value:
                continue
            if delivery.status not in (
                DeliveryStatus.pending.value,
                DeliveryStatus.retry.value,
                DeliveryStatus.processing.value,
                DeliveryStatus.failed.value,
            ):
                continue

            outcome = self.process_delivery(event_row, delivery, domain)
            if outcome == DeliveryStatus.retry.value:
                any_retry = True
            elif outcome == DeliveryStatus.dead_letter.value:
                any_dead = True
            elif outcome == DeliveryStatus.failed.value:
                any_failed = True

        # Recharger livraisons
        deliveries = self._repo.list_deliveries(event_id)
        statuses = {d.status for d in deliveries}
        if any_retry or DeliveryStatus.retry.value in statuses:
            # available_at déjà planifié dans schedule_retry
            event_row = self._repo.find_by_event_id(event_id)
            if event_row and event_row.status != EventStatus.retry.value:
                event_row.status = EventStatus.retry.value
                event_row.locked_at = None
                event_row.locked_by = None
                self._repo.save_event(event_row)
            return

        if all(s == DeliveryStatus.processed.value for s in statuses) or (
            statuses and statuses <= {DeliveryStatus.processed.value, DeliveryStatus.skipped.value}
        ):
            self.mark_processed(self._repo.find_by_event_id(event_id))
            return

        if any_dead or DeliveryStatus.dead_letter.value in statuses:
            self.mark_dead_letter(
                self._repo.find_by_event_id(event_id),
                error="Une ou plusieurs deliveries en dead_letter",
            )
            return

        if any_failed or DeliveryStatus.failed.value in statuses:
            row = self._repo.find_by_event_id(event_id)
            if row:
                row.status = EventStatus.failed.value
                row.failed_at = datetime.utcnow()
                row.locked_at = None
                row.locked_by = None
                self._repo.save_event(row)

    def process_delivery(
        self,
        event_row: ElfisEvent,
        delivery: ElfisEventDelivery,
        domain,
    ) -> str:
        if delivery.status == DeliveryStatus.processed.value:
            return DeliveryStatus.processed.value

        handlers = [
            h
            for h in self._registry.get_handlers(event_row.event_name)
            if h.handler_name == delivery.handler_name
        ]
        if not handlers:
            delivery.status = DeliveryStatus.skipped.value
            delivery.completed_at = datetime.utcnow()
            delivery.last_error = "Handler non enregistré"
            self._repo.save_delivery(delivery)
            return DeliveryStatus.skipped.value

        handler = handlers[0]
        delivery.status = DeliveryStatus.processing.value
        delivery.started_at = datetime.utcnow()
        delivery.attempt_count = int(delivery.attempt_count or 0) + 1
        self._repo.save_delivery(delivery)

        context = EventContext(
            db=self._db,
            worker_id=self.worker_id,
            attempt_count=delivery.attempt_count,
            delivery_id=delivery.id,
            correlation_id=event_row.correlation_id,
            organization_id=event_row.organization_id,
        )
        started = time.perf_counter()
        try:
            handler.handle(domain, context)
            duration_ms = (time.perf_counter() - started) * 1000
            delivery.status = DeliveryStatus.processed.value
            delivery.completed_at = datetime.utcnow()
            delivery.last_error = None
            self._repo.save_delivery(delivery)
            log_event(
                logging.INFO,
                "event_delivery_processed",
                event_id=event_row.event_id,
                event_name=event_row.event_name,
                handler_name=delivery.handler_name,
                organization_id=event_row.organization_id,
                correlation_id=event_row.correlation_id,
                attempt_count=delivery.attempt_count,
                worker_id=self.worker_id,
                status="processed",
                duration_ms=duration_ms,
            )
            return DeliveryStatus.processed.value
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            retryable = True
            if isinstance(exc, EventHandlerError):
                retryable = exc.retryable
            clean = sanitize_error_message(exc)
            log_event(
                logging.ERROR,
                "event_delivery_failed",
                event_id=event_row.event_id,
                event_name=event_row.event_name,
                handler_name=delivery.handler_name,
                organization_id=event_row.organization_id,
                correlation_id=event_row.correlation_id,
                attempt_count=delivery.attempt_count,
                worker_id=self.worker_id,
                status="failed",
                duration_ms=duration_ms,
                extra={"error": clean},
            )
            max_attempts = event_row.max_attempts or settings.elfis_event_max_attempts
            if (not retryable) or delivery.attempt_count >= max_attempts:
                delivery.status = DeliveryStatus.dead_letter.value
                delivery.failed_at = datetime.utcnow()
                delivery.last_error = clean
                self._repo.save_delivery(delivery)
                return DeliveryStatus.dead_letter.value
            return self.schedule_retry(event_row, delivery, clean)

    def schedule_retry(
        self,
        event_row: ElfisEvent,
        delivery: ElfisEventDelivery,
        error: str,
    ) -> str:
        delay = compute_retry_delay_seconds(delivery.attempt_count)
        now = datetime.utcnow()
        delivery.status = DeliveryStatus.retry.value
        delivery.failed_at = now
        delivery.last_error = error
        self._repo.save_delivery(delivery)

        event_row.status = EventStatus.retry.value
        event_row.attempt_count = max(event_row.attempt_count or 0, delivery.attempt_count)
        event_row.available_at = now + timedelta(seconds=delay)
        event_row.locked_at = None
        event_row.locked_by = None
        event_row.last_error = error
        self._repo.save_event(event_row)
        log_event(
            logging.WARNING,
            "event_delivery_retry_scheduled",
            event_id=event_row.event_id,
            event_name=event_row.event_name,
            handler_name=delivery.handler_name,
            organization_id=event_row.organization_id,
            attempt_count=delivery.attempt_count,
            worker_id=self.worker_id,
            status="retry",
            extra={"delay_seconds": delay},
        )
        return DeliveryStatus.retry.value

    def mark_processed(self, event_row: ElfisEvent | None) -> None:
        if not event_row:
            return
        event_row.status = EventStatus.processed.value
        event_row.processed_at = datetime.utcnow()
        event_row.locked_at = None
        event_row.locked_by = None
        event_row.last_error = None
        self._repo.save_event(event_row)
        log_event(
            logging.INFO,
            "event_processed",
            event_id=event_row.event_id,
            event_name=event_row.event_name,
            organization_id=event_row.organization_id,
            correlation_id=event_row.correlation_id,
            worker_id=self.worker_id,
            status="processed",
        )

    def mark_dead_letter(self, event_row: ElfisEvent | None, *, error: str) -> None:
        if not event_row:
            return
        event_row.status = EventStatus.dead_letter.value
        event_row.failed_at = datetime.utcnow()
        event_row.locked_at = None
        event_row.locked_by = None
        event_row.last_error = sanitize_error_message(error)
        self._repo.save_event(event_row)
        log_event(
            logging.ERROR,
            "event_dead_letter",
            event_id=event_row.event_id,
            event_name=event_row.event_name,
            organization_id=event_row.organization_id,
            worker_id=self.worker_id,
            status="dead_letter",
        )


def run_worker_forever(*, once: bool = False) -> None:
    """Boucle principale — processus dédié recommandé en production."""
    from app.events import bootstrap_handlers

    bootstrap_handlers()
    worker_id = default_worker_id()
    interval = max(0.5, float(settings.elfis_event_worker_poll_interval_seconds))
    logger.info(
        "event_worker_started",
        extra={"worker_id": worker_id, "interval": interval, "once": once},
    )
    while True:
        db = SessionLocal()
        try:
            EventWorker(db, worker_id=worker_id).process_next_batch()
        except Exception:
            logger.exception("event_worker_batch_failed", extra={"worker_id": worker_id})
        finally:
            db.close()
        if once:
            break
        time.sleep(interval)


def main() -> None:
    run_worker_forever(once=False)


if __name__ == "__main__":
    main()
