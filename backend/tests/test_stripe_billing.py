from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.database import Base, get_db
from app.config import settings
from app.deps import AuthContext, require_active_subscription
from app.models_saas import Organization, StripeWebhookEvent, Subscription, User
from app.routers.subscriptions import router
from app.services.auth import ROLE_PERMS
from app.services.stripe_billing import (
    STRIPE_SUBSCRIPTION_STATUSES,
    apply_webhook_event,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
)


class StripeBillingTests(unittest.TestCase):
    @staticmethod
    def request(method: str = "GET") -> Request:
        return Request({"type": "http", "method": method, "path": "/", "headers": []})

    @staticmethod
    def subscription_event(status: str, organization_id: int = 42) -> dict:
        return {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_test",
                    "status": status,
                    "metadata": {"organization_id": str(organization_id)},
                    "cancel_at_period_end": status == "canceled",
                    "items": {
                        "data": [
                            {
                                "price": {"id": "price_pro"},
                                "current_period_start": 1_700_000_000,
                                "current_period_end": 1_702_678_400,
                            }
                        ]
                    },
                }
            },
        }

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.db = self.session_factory()
        self.db.add(Organization(id=42, name="Test SARL"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_webhook_signature_missing_and_invalid(self):
        with (
            patch.object(settings, "stripe_secret_key", "sk_test_unit"),
            patch.object(settings, "stripe_webhook_secret", "whsec_unit"),
        ):
            with self.assertRaises(HTTPException) as missing:
                construct_webhook_event(b"{}", None)
            self.assertEqual(missing.exception.detail["code"], "stripe_signature_missing")

            with self.assertRaises(HTTPException) as invalid:
                construct_webhook_event(b"{}", "invalid")
            self.assertEqual(invalid.exception.detail["code"], "stripe_signature_invalid")

    def test_checkout_and_portal_are_scoped_to_organization(self):
        self.db.add(Organization(id=43, name="Autre SAS"))
        self.db.add_all(
            [
                Subscription(
                    organization_id=42,
                    plan="pro",
                    status="canceled",
                    price=19.0,
                    stripe_customer_id="cus_org_42",
                ),
                Subscription(
                    organization_id=43,
                    plan="pro",
                    status="canceled",
                    price=19.0,
                    stripe_customer_id="cus_org_43",
                ),
            ]
        )
        self.db.commit()

        with (
            patch.object(settings, "stripe_secret_key", "sk_test_unit"),
            patch.object(settings, "stripe_price_pro", "price_pro"),
            patch.object(settings, "frontend_url", "https://app.example"),
            patch(
                "app.services.stripe_billing.stripe.checkout.Session.create",
                return_value=SimpleNamespace(url="https://checkout.stripe.test/session"),
            ) as checkout_create,
            patch(
                "app.services.stripe_billing.stripe.billing_portal.Session.create",
                return_value=SimpleNamespace(url="https://billing.stripe.test/session"),
            ) as portal_create,
        ):
            checkout_url = create_checkout_session(
                self.db,
                organization_id=42,
                customer_email="owner@example.com",
            )
            portal_url = create_portal_session(self.db, organization_id=43)
            with self.assertRaises(HTTPException) as foreign_portal:
                create_portal_session(self.db, organization_id=999)

        self.assertEqual(checkout_url, "https://checkout.stripe.test/session")
        checkout_params = checkout_create.call_args.kwargs
        self.assertEqual(checkout_params["customer"], "cus_org_42")
        self.assertEqual(checkout_params["metadata"]["organization_id"], "42")
        self.assertEqual(
            checkout_params["subscription_data"]["metadata"]["organization_id"],
            "42",
        )
        self.assertEqual(checkout_params["client_reference_id"], "42")
        self.assertEqual(
            checkout_params["success_url"],
            "https://app.example/abonnement?checkout=success&session_id={CHECKOUT_SESSION_ID}",
        )
        self.assertEqual(
            checkout_params["cancel_url"],
            "https://app.example/abonnement?checkout=cancel",
        )
        portal_create.assert_called_once_with(
            customer="cus_org_43",
            return_url="https://app.example/abonnement",
        )
        self.assertEqual(portal_url, "https://billing.stripe.test/session")
        self.assertEqual(foreign_portal.exception.detail["code"], "stripe_customer_missing")

    def test_subscription_manage_permission_for_owner_admin_only(self):
        user = User(
            first_name="Test",
            last_name="User",
            email="permissions@example.com",
            status="active",
        )
        owner = AuthContext(user, 42, "owner", ROLE_PERMS["owner"])
        admin = AuthContext(user, 42, "admin", ROLE_PERMS["admin"])
        employee = AuthContext(user, 42, "employe", ROLE_PERMS["employe"])

        owner.require("subscription.manage")
        admin.require("subscription.manage")
        with self.assertRaises(HTTPException) as denied:
            employee.require("subscription.manage")
        self.assertEqual(denied.exception.status_code, 403)
        self.assertEqual(denied.exception.detail["permission"], "subscription.manage")

    def test_subscription_webhook_maps_stripe_fields(self):
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_test",
                    "status": "trialing",
                    "metadata": {"organization_id": "42"},
                    "trial_start": 1_700_000_000,
                    "trial_end": 1_701_209_600,
                    "cancel_at_period_end": False,
                    "items": {
                        "data": [
                            {
                                "price": {"id": "price_pro"},
                                "current_period_start": 1_700_000_000,
                                "current_period_end": 1_702_678_400,
                            }
                        ]
                    },
                }
            },
        }

        apply_webhook_event(self.db, event)
        self.db.commit()

        row = self.db.query(Subscription).one()
        self.assertEqual(row.organization_id, 42)
        self.assertEqual(row.status, "trialing")
        self.assertEqual(row.stripe_customer_id, "cus_test")
        self.assertEqual(row.stripe_subscription_id, "sub_test")
        self.assertEqual(row.stripe_price_id, "price_pro")
        self.assertIsNotNone(row.trial_end)
        self.assertIsNotNone(row.current_period_end)

    def test_checkout_and_subscription_upsert_do_not_duplicate_stripe_ids(self):
        from app.services.stripe_billing import _upsert_checkout

        # Orphelin incomplet déjà présent pour l'org.
        self.db.add(
            Subscription(
                organization_id=42,
                plan="pro",
                status="incomplete",
                price=19.0,
            )
        )
        self.db.commit()

        session = {
            "metadata": {"organization_id": "42"},
            "client_reference_id": "42",
            "customer": "cus_dup",
            "subscription": {
                "id": "sub_dup",
                "customer": "cus_dup",
                "status": "trialing",
                "metadata": {"organization_id": "42"},
                "trial_start": 1_700_000_000,
                "trial_end": 1_701_209_600,
                "items": {"data": [{"price": {"id": "price_pro"}}]},
            },
        }
        _upsert_checkout(self.db, session)
        self.db.commit()
        # Même session rejouée (webhook + sync) ne doit pas planter ni dupliquer.
        _upsert_checkout(self.db, session)
        self.db.commit()

        rows = self.db.query(Subscription).filter(Subscription.organization_id == 42).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "trialing")
        self.assertEqual(rows[0].stripe_subscription_id, "sub_dup")
        self.assertEqual(rows[0].stripe_customer_id, "cus_dup")

    def test_subscription_transitions_update_organization_plan(self):
        organization = self.db.get(Organization, 42)
        expected_plans = {
            "trialing": "pro",
            "active": "pro",
            "past_due": "pro",
            "canceled": "starter",
        }

        for status, expected_plan in expected_plans.items():
            apply_webhook_event(self.db, self.subscription_event(status))
            self.db.commit()
            row = self.db.query(Subscription).one()
            self.db.refresh(organization)
            self.assertEqual(row.status, status)
            self.assertEqual(organization.subscription_plan, expected_plan)
            if status == "past_due":
                self.assertIsNotNone(row.past_due_since)
            if status == "canceled":
                self.assertIsNotNone(row.canceled_at)

    def test_all_real_stripe_statuses_are_stored(self):
        for status in STRIPE_SUBSCRIPTION_STATUSES:
            apply_webhook_event(self.db, self.subscription_event(status))
            self.db.commit()
            self.assertEqual(self.db.query(Subscription).one().status, status)

    def test_webhook_identifiers_cannot_cross_tenants(self):
        self.db.add(Organization(id=43, name="Autre SAS"))
        self.db.add(
            Subscription(
                organization_id=42,
                plan="pro",
                status="active",
                price=19.0,
                stripe_customer_id="cus_test",
                stripe_subscription_id="sub_test",
            )
        )
        self.db.commit()

        with self.assertRaises(ValueError):
            apply_webhook_event(self.db, self.subscription_event("active", 43))
        self.assertEqual(
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == "sub_test")
            .one()
            .organization_id,
            42,
        )

    def test_invoice_events_do_not_resurrect_canceled_subscription(self):
        apply_webhook_event(self.db, self.subscription_event("canceled"))
        self.db.commit()
        invoice = {
            "customer": "cus_test",
            "subscription": "sub_test",
        }
        for event_type in ("invoice.paid", "invoice.payment_failed"):
            apply_webhook_event(
                self.db,
                {"type": event_type, "data": {"object": invoice}},
            )
            self.db.commit()
        self.assertEqual(self.db.query(Subscription).one().status, "canceled")

    def test_webhook_event_is_idempotent(self):
        app = FastAPI()
        app.include_router(router, prefix="/api")

        def override_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        event = {"id": "evt_once", "type": "ignored.event", "data": {"object": {}}}
        with patch(
            "app.routers.subscriptions.construct_webhook_event",
            return_value=event,
        ):
            client = TestClient(app)
            first = client.post("/api/subscriptions/webhook", content=b"{}")
            second = client.post("/api/subscriptions/webhook", content=b"{}")

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["duplicate"])
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["duplicate"])
        verify = self.session_factory()
        try:
            self.assertEqual(verify.query(StripeWebhookEvent).count(), 1)
        finally:
            verify.close()

    def test_subscription_guard_returns_structured_402(self):
        user = User(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            status="active",
        )
        self.db.add(user)
        self.db.commit()
        auth = AuthContext(user, 42, "owner", ["*"])

        with self.assertRaises(HTTPException) as raised:
            require_active_subscription(request=self.request(), auth=auth, db=self.db)

        self.assertEqual(raised.exception.status_code, 402)
        self.assertEqual(raised.exception.detail["code"], "subscription_required")

    def test_past_due_grace_is_measured_from_failure(self):
        user = User(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            status="active",
        )
        subscription = Subscription(
            organization_id=42,
            plan="pro",
            status="past_due",
            price=19.0,
            past_due_since=datetime.utcnow(),
        )
        self.db.add_all([user, subscription])
        self.db.commit()
        auth = AuthContext(user, 42, "owner", ["*"])

        self.assertIs(
            require_active_subscription(request=self.request(), auth=auth, db=self.db),
            auth,
        )
        with self.assertRaises(HTTPException) as read_only:
            require_active_subscription(request=self.request("POST"), auth=auth, db=self.db)
        self.assertEqual(
            read_only.exception.detail["code"],
            "subscription_past_due_read_only",
        )
        subscription.past_due_since = datetime.utcnow() - timedelta(days=4)
        self.db.commit()
        with self.assertRaises(HTTPException) as raised:
            require_active_subscription(request=self.request(), auth=auth, db=self.db)
        self.assertEqual(raised.exception.detail["code"], "subscription_inactive")


if __name__ == "__main__":
    unittest.main()
