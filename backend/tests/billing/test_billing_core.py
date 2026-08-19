"""Tests Billing — plans, entitlements, quotas, webhooks (Stripe mocké)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models_saas import Organization, Subscription, User


class BillingTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Import modèles billing
        from app.billing import billing_models  # noqa: F401
        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Organization(id=1, name="Org Test")
        self.db.add(self.org)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _add_legacy_sub(self, **kwargs) -> Subscription:
        defaults = dict(
            organization_id=1,
            plan="starter",
            status="trialing",
            price=19.0,
            stripe_price_id=settings.stripe_price_pro or "price_starter_test",
            trial_start=datetime.utcnow() - timedelta(days=1),
            trial_end=datetime.utcnow() + timedelta(days=13),
            current_period_start=datetime.utcnow() - timedelta(days=1),
            current_period_end=datetime.utcnow() + timedelta(days=13),
        )
        defaults.update(kwargs)
        row = Subscription(**defaults)
        self.db.add(row)
        self.db.commit()
        return row


class PlanRegistryTests(BillingTestCase):
    def test_starter_plan_loaded(self):
        from app.billing.plan_registry import get_plan
        from app.billing.billing_types import PlanCodes, FeatureCodes

        plan = get_plan(PlanCodes.STARTER)
        self.assertIsNotNone(plan)
        self.assertEqual(float(plan.price_amount), 19.0)
        self.assertEqual(plan.trial_days, 14)
        self.assertTrue(plan.features[FeatureCodes.DOCUMENTS_UPLOAD])
        self.assertFalse(plan.features[FeatureCodes.DOCUMENTS_OCR])

    def test_professional_and_enterprise_catalog(self):
        from app.billing.plan_registry import get_plan, list_plans
        from app.billing.billing_types import PlanCodes, FeatureCodes

        pro = get_plan(PlanCodes.PROFESSIONAL)
        ent = get_plan(PlanCodes.ENTERPRISE)
        self.assertIsNotNone(pro)
        self.assertTrue(pro.is_public)
        self.assertTrue(pro.features[FeatureCodes.DOCUMENTS_OCR])
        self.assertIsNotNone(ent)
        self.assertFalse(ent.is_public)
        public_codes = {p.plan_code for p in list_plans(public_only=True)}
        self.assertIn(PlanCodes.STARTER, public_codes)
        self.assertIn(PlanCodes.PROFESSIONAL, public_codes)
        self.assertNotIn(PlanCodes.ENTERPRISE, public_codes)

    def test_unknown_price_id_rejected(self):
        from app.billing.billing_exceptions import BillingValidationError
        from app.billing.billing_security import assert_known_price_id

        with self.assertRaises(BillingValidationError):
            assert_known_price_id("price_unknown_xyz")


class EntitlementEngineTests(BillingTestCase):
    def test_resolve_trial_state(self):
        from app.billing.entitlement_engine import EntitlementEngine

        self._add_legacy_sub(status="trialing")
        state = EntitlementEngine(self.db).resolve(1)
        self.assertEqual(state.source, "entitlement_engine")
        self.assertEqual(state.engine_version, "2.0.0")
        self.assertTrue(state.is_trial)
        self.assertTrue(state.has_product_access)
        self.assertEqual(state.status, "trialing")
        self.assertIsInstance(state.entitlements, dict)
        self.assertIsInstance(state.quotas, dict)

    def test_org_overview_payload(self):
        from app.billing.billing_service import BillingService

        self._add_legacy_sub(status="active", trial_end=None)
        payload = BillingService(self.db).org_overview(1)
        self.assertIn("overview", payload)
        self.assertIn("plans", payload)
        self.assertEqual(payload["overview"]["source"], "entitlement_engine")

    def test_platform_revenue_overview_shape(self):
        from app.billing.billing_service import BillingService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active", trial_end=None)
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        data = BillingService(self.db).platform_revenue_overview()
        self.assertIn("mrr_eur", data)
        self.assertIn("arr_eur", data)
        self.assertEqual(data["source"], "entitlement_engine")
        self.assertGreaterEqual(data["subscriptions_total"], 1)


class SubscriptionEntitlementTests(BillingTestCase):
    def test_org_without_subscription(self):
        from app.billing.subscription_service import SubscriptionService

        payload = SubscriptionService(self.db).get_subscription_payload(1)
        self.assertIn(payload["status"], ("none", "expired", "canceled", "cancelled"))

    def test_trial_14_days_and_entitlements(self):
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="trialing")
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            sub = SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
            self.assertEqual(sub.status, "trialing")
            self.assertIsNotNone(sub.trial_ends_at)
            ents = EntitlementService(self.db).get_entitlements(1)
            self.assertTrue(ents.get(FeatureCodes.AI_CLASSIFICATION))
            EntitlementService(self.db).require(1, FeatureCodes.DOCUMENTS_UPLOAD)

    def test_trial_expired_blocks_costly(self):
        from app.billing.billing_exceptions import FeatureNotAvailableError
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(
            status="canceled",
            trial_end=datetime.utcnow() - timedelta(days=1),
            cancel_at_period_end=False,
            canceled_at=datetime.utcnow() - timedelta(hours=1),
        )
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            with self.assertRaises(FeatureNotAvailableError):
                EntitlementService(self.db).require(1, FeatureCodes.AI_CLASSIFICATION)

    def test_active_subscription(self):
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active", trial_end=None)
        sub = SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        self.assertEqual(sub.status, "active")

    def test_override_entitlement(self):
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active")
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        svc = EntitlementService(self.db)
        svc.set_override(1, FeatureCodes.DOCUMENTS_OCR, True)
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            svc.require(1, FeatureCodes.DOCUMENTS_OCR)
        self.assertTrue(svc.remove_override(1, FeatureCodes.DOCUMENTS_OCR))


class QuotaTests(BillingTestCase):
    def test_quota_unlimited_allowed(self):
        from app.billing.quota_service import QuotaService
        from app.billing.billing_types import QuotaCodes
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active")
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        result = QuotaService(self.db).check(1, QuotaCodes.AI_EXECUTIONS_MONTH, amount=100)
        self.assertTrue(result.allowed)
        self.assertIsNone(result.limit_value)

    def test_quota_exceeded_when_enforced(self):
        from app.billing.billing_exceptions import QuotaExceededError
        from app.billing.billing_types import QuotaCodes
        from app.billing.quota_service import QuotaService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active")
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        qs = QuotaService(self.db)
        # Forcer une limite
        quotas = qs.repo.list_quotas(1)
        target = next((q for q in quotas if q.quota_code == QuotaCodes.ORGANIZATION_USERS), None)
        self.assertIsNotNone(target)
        target.limit_value = 1
        target.hard_limit = True
        self.db.commit()
        with patch.object(settings, "elfis_billing_enforce_quotas", True):
            qs.consume(1, QuotaCodes.ORGANIZATION_USERS, 1)
            with self.assertRaises(QuotaExceededError):
                qs.consume(1, QuotaCodes.ORGANIZATION_USERS, 1)

    def test_reserve_commit_release(self):
        from app.billing.billing_types import QuotaCodes
        from app.billing.quota_service import QuotaService
        from app.billing.subscription_service import SubscriptionService

        self._add_legacy_sub(status="active")
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        qs = QuotaService(self.db)
        for q in qs.repo.list_quotas(1):
            if q.quota_code == QuotaCodes.ORGANIZATION_USERS:
                q.limit_value = 5
                q.hard_limit = True
        self.db.commit()
        with patch.object(settings, "elfis_billing_enforce_quotas", True):
            qs.reserve(1, QuotaCodes.ORGANIZATION_USERS, 2)
            qs.commit_reservation(1, QuotaCodes.ORGANIZATION_USERS, 2)
            check = qs.check(1, QuotaCodes.ORGANIZATION_USERS, amount=0)
            self.assertEqual(check.used_value, 2)
            qs.reserve(1, QuotaCodes.ORGANIZATION_USERS, 1)
            qs.release_reservation(1, QuotaCodes.ORGANIZATION_USERS, 1)
            check2 = qs.check(1, QuotaCodes.ORGANIZATION_USERS, amount=0)
            self.assertEqual(check2.used_value, 2)


class UsageTests(BillingTestCase):
    def test_record_and_list_usage(self):
        from app.billing.billing_types import UsageCodes
        from app.billing.usage_service import UsageService

        svc = UsageService(self.db)
        svc.record_usage(1, UsageCodes.DOCUMENTS_PROCESSED, 3)
        svc.record_usage(1, UsageCodes.EMAILS_SENT, 1)
        data = svc.list_usage(1)
        codes = {d["usage_code"]: d["used_value"] for d in data}
        self.assertEqual(codes.get(UsageCodes.DOCUMENTS_PROCESSED), 3)
        self.assertEqual(codes.get(UsageCodes.EMAILS_SENT), 1)


class WebhookSecurityTests(BillingTestCase):
    def test_webhook_size_limit(self):
        from app.billing.billing_exceptions import StripeWebhookError
        from app.billing.billing_security import assert_webhook_size

        with patch.object(settings, "elfis_billing_webhook_max_bytes", 10):
            with self.assertRaises(StripeWebhookError):
                assert_webhook_size(b"x" * 20)

    def test_safe_log_no_secrets(self):
        from app.billing.billing_logging import safe_billing_log_context, sanitize_billing_error

        ctx = safe_billing_log_context(
            organization_id=1,
            payload={"card": "4111"},
            stripe_payload="secret",
        )
        self.assertNotIn("payload", ctx)
        self.assertNotIn("stripe_payload", ctx)
        cleaned = sanitize_billing_error("key=sk_test_abc123 token=xyz")
        self.assertNotIn("sk_test", cleaned or "")

    def test_idempotent_billing_event(self):
        from app.billing.billing_events import post_process_legacy_webhook
        from app.billing.billing_repository import BillingRepository
        from app.billing.billing_types import BillingEventStatus

        self._add_legacy_sub(status="active", stripe_subscription_id="sub_x", stripe_customer_id="cus_x")
        event = {
            "id": "evt_dup_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_x",
                    "object": "subscription",
                    "customer": "cus_x",
                    "status": "active",
                    "metadata": {"organization_id": "1"},
                }
            },
        }
        post_process_legacy_webhook(self.db, event, payload_hash="abc")
        self.db.commit()
        post_process_legacy_webhook(self.db, event, payload_hash="abc")
        self.db.commit()
        rows = (
            BillingRepository(self.db)
            .db.query(__import__("app.billing.billing_models", fromlist=["ElfisBillingEvent"]).ElfisBillingEvent)
            .filter_by(provider_event_id="evt_dup_1")
            .all()
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, BillingEventStatus.PROCESSED)


class PastDueGraceTests(BillingTestCase):
    def test_past_due_grace_then_block(self):
        from app.billing.billing_exceptions import FeatureNotAvailableError
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.billing.subscription_service import SubscriptionService

        past = datetime.utcnow() - timedelta(days=10)
        self._add_legacy_sub(status="past_due", past_due_since=past)
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            with patch.object(settings, "elfis_billing_past_due_grace_days", 7):
                with self.assertRaises(FeatureNotAvailableError):
                    EntitlementService(self.db).require(1, FeatureCodes.AI_CLASSIFICATION)


class CancelScheduledTests(BillingTestCase):
    def test_cancel_at_period_end_keeps_access(self):
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.billing.subscription_service import SubscriptionService
        from app.subscriptions.access import get_subscription_access

        self._add_legacy_sub(
            status="active",
            cancel_at_period_end=True,
            current_period_end=datetime.utcnow() + timedelta(days=5),
        )
        SubscriptionService(self.db).sync_from_legacy(1, rebuild=True)
        access = get_subscription_access(self.db, 1)
        self.assertTrue(access.has_access)
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            EntitlementService(self.db).require(1, FeatureCodes.DOCUMENTS_UPLOAD)


if __name__ == "__main__":
    unittest.main()
