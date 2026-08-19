"""C1.13 — isolation customer_id à la création de facture."""

from __future__ import annotations

import unittest
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Customer, Organization, OrganizationMember, Role, User
from app.routers import billing as billing_router
from app.services.auth import ROLE_PERMS


class FirstExperienceBillingIsolationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def _fk(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org_a = Organization(id=1, name="Org A", platform_status="active")
        self.org_b = Organization(id=2, name="Org B", platform_status="active")
        self.role = Role(id=1, name="owner", permissions='["*"]')
        self.user = User(
            id=10,
            email="owner@a.local",
            first_name="Ada",
            last_name="Owner",
            status="active",
            password_hash="x",
        )
        self.db.add_all([self.org_a, self.org_b, self.role, self.user])
        self.db.commit()
        self.db.add(
            OrganizationMember(
                user_id=10,
                organization_id=1,
                role_id=1,
                status="active",
            )
        )
        foreign = Customer(
            organization_id=2,
            name="Foreign Client",
            email="f@b.local",
            created_at=datetime.utcnow(),
        )
        local = Customer(
            organization_id=1,
            name="Local Client",
            email="l@a.local",
            created_at=datetime.utcnow(),
        )
        self.db.add_all([foreign, local])
        self.db.commit()
        self.foreign_id = foreign.id
        self.local_id = local.id

        app = FastAPI()
        app.include_router(billing_router.router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=1,
                role="owner",
                permissions=list(ROLE_PERMS.get("owner", ["*"])),
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        app.dependency_overrides[require_active_subscription] = lambda: None
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_rejects_customer_from_other_organization(self):
        res = self.client.post(
            "/api/billing/documents",
            json={
                "doc_type": "facture",
                "customer_name": "Foreign Client",
                "customer_id": self.foreign_id,
                "amount_ht": 100,
                "vat_rate": 20,
            },
        )
        self.assertEqual(res.status_code, 404)

    def test_accepts_customer_from_current_organization(self):
        res = self.client.post(
            "/api/billing/documents",
            json={
                "doc_type": "facture",
                "customer_name": "Local Client",
                "customer_id": self.local_id,
                "amount_ht": 100,
                "vat_rate": 20,
            },
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["customer_id"], self.local_id)
        self.assertEqual(body["status"], "draft")
        self.assertIn("id", body)
        self.assertIn("number", body)


if __name__ == "__main__":
    unittest.main()
