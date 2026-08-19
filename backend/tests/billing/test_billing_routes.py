"""Tests routes Billing SaaS."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization, User
from app.routers.saas_billing import router
from app.services.auth import ROLE_PERMS


class BillingRoutesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.billing import billing_models  # noqa: F401
        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(Organization(id=7, name="Route Org"))
        self.user = User(
            id=1,
            email="owner@test.local",
            first_name="Owner",
            last_name="Test",
            status="active",
            password_hash="x",
        )
        self.db.add(self.user)
        self.db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=7,
                role="owner",
                permissions=list(ROLE_PERMS.get("owner", ["*"])),
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_list_plans(self):
        res = self.client.get("/api/billing/plans")
        self.assertEqual(res.status_code, 200)
        plans = res.json()["plans"]
        codes = {p["plan_code"] for p in plans}
        self.assertIn("starter", codes)
        self.assertIn("professional", codes)

    def test_billing_overview_engine(self):
        res = self.client.get("/api/billing/overview")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("overview", body)
        overview = body["overview"]
        self.assertEqual(overview.get("source"), "entitlement_engine")
        self.assertEqual(overview.get("engine_version"), "2.0.0")
        self.assertIn("entitlements", overview)
        self.assertIn("quotas", overview)

    def test_billing_webhooks_audit(self):
        res = self.client.get("/api/billing/webhooks")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("events", body)
        self.assertIn("ingest", body)
        self.assertNotIn("stripe_secret", str(body).lower())

    def test_subscription_payload(self):
        res = self.client.get("/api/billing/subscription")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("will_renew_automatically", body)
        self.assertIn("trial_days", body)
        self.assertIn("disclosure", body)

    def test_member_cannot_checkout(self):
        def _member():
            return AuthContext(
                user=self.user,
                organization_id=7,
                role="employe",
                permissions=list(ROLE_PERMS.get("employe", [])),
            )

        self.client.app.dependency_overrides[get_auth_context] = _member
        res = self.client.post(
            "/api/billing/checkout",
            json={"plan_code": "starter", "automatic_renewal_accepted": True, "terms_accepted": True},
        )
        self.assertIn(res.status_code, (403, 401))


if __name__ == "__main__":
    unittest.main()
