"""P1-03 — enforcement abonnement backend (subscription gate + billing disabled)."""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")

from app.config import settings
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, Subscription, User
from app.sales_crm.router import router as sales_router


def _add_sub(db, org_id: int, *, status: str = "active") -> Subscription:
    now = datetime.utcnow()
    row = Subscription(
        organization_id=org_id,
        plan="starter",
        status=status,
        price=19.0,
        stripe_price_id=settings.stripe_price_pro or "price_test",
        trial_start=now - timedelta(days=1),
        trial_end=now + timedelta(days=13),
        current_period_start=now - timedelta(days=1),
        current_period_end=now + timedelta(days=29),
    )
    db.add(row)
    db.commit()
    return row


class SubscriptionEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Organization(id=1, name="Org Test", platform_status="active")
        self.other_org = Organization(id=2, name="Org B", platform_status="active")
        self.user = User(
            id=1,
            email="owner@test.local",
            first_name="Owner",
            last_name="Test",
            status="active",
            password_hash="x",
        )
        self.db.add_all([self.org, self.other_org, self.user])
        self.db.commit()

        app = FastAPI()
        app.include_router(sales_router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self._org_id = 1

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=self._org_id,
                role="owner",
                permissions=["*"],
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        self.app = app
        self._auth = _auth
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_active_subscription_allows_sales_read(self):
        _add_sub(self.db, 1, status="active")
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 200)

    def test_trial_allows_sales_read(self):
        _add_sub(self.db, 1, status="trialing")
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 200)

    def test_canceled_blocks_sales_read(self):
        _add_sub(self.db, 1, status="canceled")
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 402)
        self.assertIn("subscription", str(r.json()).lower())

    def test_expired_blocks_sales_read(self):
        _add_sub(self.db, 1, status="incomplete_expired")
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 402)

    def test_no_subscription_blocks_sales(self):
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 402)
        detail = r.json()["detail"]
        code = detail.get("code") if isinstance(detail, dict) else None
        self.assertIn(code, ("subscription_required", "subscription_inactive"))

    def test_canceled_blocks_sales_write(self):
        _add_sub(self.db, 1, status="canceled")
        r = self.client.post(
            "/api/sales/companies",
            json={"name": "Acme Corp"},
        )
        self.assertEqual(r.status_code, 402)

    def test_active_allows_sales_write(self):
        _add_sub(self.db, 1, status="active")
        r = self.client.post(
            "/api/sales/companies",
            json={"name": "Acme Corp"},
        )
        self.assertIn(r.status_code, (200, 201))

    def test_wrong_tenant_still_denied(self):
        _add_sub(self.db, 1, status="active")
        _add_sub(self.db, 2, status="active")
        from app.sales_crm.models import SalesCompany

        foreign = SalesCompany(organization_id=2, name="Foreign Co")
        self.db.add(foreign)
        self.db.commit()
        r = self.client.get(f"/api/sales/companies/{foreign.id}")
        self.assertIn(r.status_code, (403, 404))

    def test_billing_disabled_bypasses_subscription_gate(self):
        with patch.object(settings, "elfis_billing_enabled", False):
            r = self.client.get("/api/sales/bootstrap")
            self.assertEqual(r.status_code, 200)

    def test_subscription_management_routes_remain_without_gate(self):
        from app.routers import subscriptions as subs_router

        app = FastAPI()
        app.include_router(subs_router.router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = self._auth
        client = TestClient(app)
        r = client.get("/api/subscriptions/current")
        self.assertEqual(r.status_code, 200)

    def test_platform_admin_bypasses_subscription_gate(self):
        admin = User(
            id=99,
            email="admin@elfis.test",
            first_name="Admin",
            last_name="ELFIS",
            status="active",
            password_hash="x",
            is_platform_admin=True,
        )
        self.db.add(admin)
        self.db.commit()

        def _admin_auth():
            return AuthContext(user=admin, organization_id=1, role="owner", permissions=["*"])

        self.app.dependency_overrides[get_auth_context] = _admin_auth
        r = self.client.get("/api/sales/bootstrap")
        self.assertEqual(r.status_code, 200)

    def test_past_due_grace_read_only_blocks_write(self):
        sub = _add_sub(self.db, 1, status="past_due")
        sub.past_due_since = datetime.utcnow() - timedelta(days=1)
        self.db.commit()
        read = self.client.get("/api/sales/bootstrap")
        self.assertEqual(read.status_code, 200)
        write = self.client.post(
            "/api/sales/companies",
            json={"name": "Grace Co"},
        )
        self.assertEqual(write.status_code, 402)
        detail = write.json()["detail"]
        self.assertEqual(detail.get("code"), "subscription_past_due_read_only")

    def test_require_active_subscription_unit_billing_disabled(self):
        auth = AuthContext(self.user, 1, "owner", ["*"])
        with patch.object(settings, "elfis_billing_enabled", False):
            result = require_active_subscription(
                request=type("R", (), {"method": "POST"})(),
                auth=auth,
                db=self.db,
            )
            self.assertIs(result, auth)

    def test_suspended_org_read_only_on_protected_route(self):
        self.org.platform_status = "suspended"
        self.db.commit()
        _add_sub(self.db, 1, status="active")
        read = self.client.get("/api/sales/bootstrap")
        self.assertEqual(read.status_code, 200)
        write = self.client.post(
            "/api/sales/companies",
            json={"name": "Blocked"},
        )
        self.assertEqual(write.status_code, 403)


class EntitlementFlagTests(unittest.TestCase):
    def test_enforcement_off_skips_feature_require(self):
        from app.billing.billing_guards import require_feature
        from app.billing.billing_types import FeatureCodes

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app import models_saas  # noqa: F401
        from app.billing import billing_models  # noqa: F401

        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        db.add(Organization(id=1, name="Org"))
        db.commit()
        with patch.object(settings, "elfis_billing_enforce_entitlements", False):
            require_feature(db, 1, FeatureCodes.DOCUMENTS_OCR)
        db.close()

    def test_enforcement_on_blocks_missing_feature(self):
        from app.billing.billing_guards import require_feature
        from app.billing.billing_types import FeatureCodes

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app import models_saas  # noqa: F401
        from app.billing import billing_models  # noqa: F401

        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        org = Organization(id=1, name="Org")
        db.add(org)
        db.add(
            Subscription(
                organization_id=1,
                plan="starter",
                status="active",
                price=19.0,
                stripe_price_id="price_test",
            )
        )
        db.commit()
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            with self.assertRaises(HTTPException) as ctx:
                require_feature(db, 1, FeatureCodes.DOCUMENTS_OCR)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctx.exception.detail["code"], "feature_not_available")
        db.close()

    def test_enforcement_on_allows_plan_feature(self):
        from app.billing.billing_guards import require_feature
        from app.billing.billing_types import FeatureCodes
        from app.billing.subscription_service import SubscriptionService

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app import models_saas  # noqa: F401
        from app.billing import billing_models  # noqa: F401

        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        db.add(Organization(id=1, name="Org"))
        db.add(
            Subscription(
                organization_id=1,
                plan="starter",
                status="active",
                price=19.0,
                stripe_price_id=settings.stripe_price_pro or "price_test",
            )
        )
        db.commit()
        SubscriptionService(db).sync_from_legacy(1, rebuild=True)
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            require_feature(db, 1, FeatureCodes.DOCUMENTS_UPLOAD)
        db.close()
