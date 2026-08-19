"""Worker CLI livraisons produit — hors processus API production."""

from __future__ import annotations

import argparse
import logging
import time
import uuid

from app.config import settings
from app.database import SessionLocal
from app.product_integrations.repository import ProductIntegrationRepository
from app.product_integrations.service import ProductIntegrationService

logger = logging.getLogger(__name__)


def run_worker(
    *,
    once: bool = False,
    product: str | None = None,
    max_deliveries: int = 10,
    poll_seconds: float | None = None,
    worker_id: str | None = None,
) -> int:
    wid = worker_id or f"pi-worker-{uuid.uuid4().hex[:8]}"
    poll = float(
        poll_seconds
        if poll_seconds is not None
        else getattr(settings, "product_delivery_worker_poll_seconds", 2) or 2
    )
    lease = int(getattr(settings, "product_delivery_lease_seconds", 60) or 60)
    processed = 0
    while True:
        db = SessionLocal()
        try:
            repo = ProductIntegrationRepository(db)
            svc = ProductIntegrationService(db)
            claimed = repo.claim_deliveries(
                worker_id=wid,
                limit=max_deliveries,
                lease_seconds=lease,
                product_key=product,
            )
            for delivery in claimed:
                try:
                    svc.process_delivery(delivery, worker_id=wid)
                    processed += 1
                except Exception:
                    logger.exception("delivery_process_failed", extra={"delivery_id": delivery.id})
        finally:
            db.close()
        if once:
            break
        time.sleep(poll)
    return processed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ELFIS product delivery worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--product", default=None)
    parser.add_argument("--max-deliveries", type=int, default=10)
    parser.add_argument("--poll-seconds", type=float, default=None)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    n = run_worker(
        once=args.once,
        product=args.product,
        max_deliveries=args.max_deliveries,
        poll_seconds=args.poll_seconds,
        worker_id=args.worker_id,
    )
    logger.info("product_delivery_worker_done processed=%s", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
