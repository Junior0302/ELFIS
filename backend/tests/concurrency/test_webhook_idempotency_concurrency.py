"""CONC-006 — Webhook Stripe event_id idempotent (double appel)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.billing import billing_models  # noqa: F401
from app.billing.billing_models import ElfisBillingEvent
from app.billing.billing_types import BillingEventStatus
from app.billing.webhooks.stripe_webhook_handler import StripeWebhookHandler
from app.database import Base
from app.models_saas import Organization


def test_conc_006_webhook_event_id_concurrent():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="WH Conc"))
    db.commit()

    event_id = f"evt_phase_f_{uuid4().hex[:12]}"
    event = {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {"object": {"metadata": {"organization_id": "1"}}},
    }

    s1 = Session()
    try:
        h1 = StripeWebhookHandler(s1)
        h1._apply_stripe = False
        out1 = h1.handle(event, payload_hash="hash-phase-f")
        s1.commit()
        assert out1.get("ok") is True
    finally:
        s1.close()

    s2 = Session()
    try:
        h2 = StripeWebhookHandler(s2)
        h2._apply_stripe = False
        out2 = h2.handle(event, payload_hash="hash-phase-f")
        s2.commit()
        assert out2.get("ok") is True
        assert out2.get("idempotent") is True or out2.get("in_progress") is True
    finally:
        s2.close()

    s = Session()
    try:
        n = s.query(ElfisBillingEvent).filter_by(provider_event_id=event_id).count()
        assert n == 1
        row = s.query(ElfisBillingEvent).filter_by(provider_event_id=event_id).one()
        assert row.status in (BillingEventStatus.PROCESSED, BillingEventStatus.RECEIVED)
    finally:
        s.close()
        db.close()
