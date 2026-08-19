"""Worker reconciliation livraisons unknown / delivering expirées."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.product_integrations.models import ElfisProductDocumentDelivery
from app.product_integrations.service import ProductIntegrationService
from app.product_integrations.types import DeliveryStatus

logger = logging.getLogger(__name__)


def run_reconcile(
    *,
    product: str | None = None,
    delivery_id: str | None = None,
    organization_id: int | None = None,
    status: str = DeliveryStatus.UNKNOWN.value,
    older_than_seconds: int = 120,
    dry_run: bool = True,
    confirm: bool = False,
) -> int:
    if not dry_run and not confirm:
        raise SystemExit("FATAL: --confirm requis hors dry-run")
    db = SessionLocal()
    processed = 0
    try:
        svc = ProductIntegrationService(db)
        q = db.query(ElfisProductDocumentDelivery)
        if delivery_id:
            q = q.filter(ElfisProductDocumentDelivery.id == delivery_id)
        else:
            q = q.filter(ElfisProductDocumentDelivery.status == status)
            cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
            q = q.filter(ElfisProductDocumentDelivery.updated_at <= cutoff)
        if product:
            q = q.filter(ElfisProductDocumentDelivery.product_key == product)
        if organization_id is not None:
            q = q.filter(ElfisProductDocumentDelivery.organization_id == organization_id)
        rows = q.order_by(ElfisProductDocumentDelivery.updated_at.asc()).limit(100).all()
        for row in rows:
            logger.info(
                "reconcile_candidate delivery_id=%s status=%s dry_run=%s",
                row.id,
                row.status,
                dry_run,
            )
            svc.reconcile_delivery(row.id, dry_run=dry_run)
            processed += 1
    finally:
        db.close()
    return processed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile product deliveries")
    parser.add_argument("--product", default=None)
    parser.add_argument("--delivery-id", default=None)
    parser.add_argument("--organization-id", type=int, default=None)
    parser.add_argument("--status", default=DeliveryStatus.UNKNOWN.value)
    parser.add_argument("--older-than", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Applique (désactive dry-run)")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    dry = not args.apply
    n = run_reconcile(
        product=args.product,
        delivery_id=args.delivery_id,
        organization_id=args.organization_id,
        status=args.status,
        older_than_seconds=args.older_than,
        dry_run=dry,
        confirm=args.confirm,
    )
    logger.info("reconcile_done processed=%s dry_run=%s", n, dry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
