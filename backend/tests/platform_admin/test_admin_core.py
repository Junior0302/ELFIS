"""Tests Platform Admin V1."""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_platform_admin
from app.models_saas import Organization, User
from app.routers import platform_admin
from app.services.auth import ROLE_PERMS


class PlatformAdminTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.platform_admin import admin_models  # noqa: F401
        from app.billing import billing_models  # noqa: F401
        from app import models_saas  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Organization(id=1, name="Acme", platform_status="active")
        self.admin = User(
            id=10,
            email="admin@elfis.test",
            first_name="Admin",
            last_name="Plat",
            status="active",
            is_platform_admin=True,
            password_hash="x",
        )
        self.user = User(
            id=20,
            email="user@elfis.test",
            first_name="User",
            last_name="Org",
            status="active",
            password_hash="x",
        )
        self.db.add_all([self.org, self.admin, self.user])
        self.db.commit()

        app = FastAPI()
        app.include_router(platform_admin.router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        def _admin_ok():
            return self.admin

        def _auth_admin():
            return AuthContext(self.admin, 1, "owner", list(ROLE_PERMS["owner"]))

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[require_platform_admin] = _admin_ok
        app.dependency_overrides[get_auth_context] = _auth_admin
        self.client = TestClient(app)
        self.app = app

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_dashboard_ok(self):
        res = self.client.get("/api/platform/dashboard?period=24h")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("organizations_total", body)
        self.assertIn("jobs_pending", body)
        self.assertEqual(body["organizations_total"], 1)

    def test_normal_user_denied(self):
        def _deny():
            from fastapi import HTTPException

            raise HTTPException(403, detail={"code": "platform_admin_required"})

        self.app.dependency_overrides[require_platform_admin] = _deny
        res = self.client.get("/api/platform/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_health_services(self):
        res = self.client.get("/api/platform/health/services")
        self.assertEqual(res.status_code, 200)
        names = {s["service"] for s in res.json()["services"]}
        self.assertIn("database", names)
        self.assertIn("stripe", names)

    def test_suspend_requires_reason(self):
        res = self.client.post("/api/platform/organizations/1/suspend", json={"reason": "ab"})
        self.assertEqual(res.status_code, 422)

    def test_suspend_and_restore(self):
        res = self.client.post(
            "/api/platform/organizations/1/suspend",
            json={"reason": "Fraude suspectée — investigation"},
        )
        self.assertEqual(res.status_code, 200)
        self.db.refresh(self.org)
        self.assertEqual(self.org.platform_status, "suspended")

        audits = self.client.get("/api/platform/audit").json()["audits"]
        self.assertTrue(any(a["action"] == "organization.suspend" for a in audits))

        res2 = self.client.post(
            "/api/platform/organizations/1/restore",
            json={"reason": "Investigation close — accès rétabli"},
        )
        self.assertEqual(res2.status_code, 200)
        self.db.refresh(self.org)
        self.assertEqual(self.org.platform_status, "active")

    def test_suspend_blocks_costly_entitlement(self):
        from app.billing.billing_exceptions import FeatureNotAvailableError
        from app.billing.billing_types import FeatureCodes
        from app.billing.entitlement_service import EntitlementService
        from app.config import settings
        from unittest.mock import patch

        self.org.platform_status = "suspended"
        self.db.commit()
        with patch.object(settings, "elfis_billing_enforce_entitlements", True):
            with self.assertRaises(FeatureNotAvailableError):
                EntitlementService(self.db).require(1, FeatureCodes.AI_CLASSIFICATION)
            # consultation vault autorisée
            EntitlementService(self.db).require(1, FeatureCodes.DOCUMENTS_VAULT)

    def test_disable_user(self):
        res = self.client.post(
            "/api/platform/users/20/disable",
            json={"reason": "Compte compromis — désactivation temporaire"},
        )
        self.assertEqual(res.status_code, 200)
        self.db.refresh(self.user)
        self.assertEqual(self.user.status, "suspended")

    def test_incident_lifecycle(self):
        from app.platform_admin.admin_incident_service import AdminIncidentService
        from app.platform_admin.admin_types import IncidentTypes

        svc = AdminIncidentService(self.db)
        a = svc.upsert_incident(
            incident_type=IncidentTypes.JOB_DEAD_LETTER,
            source_type="job",
            source_id="job-1",
            title="Job failed",
            organization_id=1,
        )
        b = svc.upsert_incident(
            incident_type=IncidentTypes.JOB_DEAD_LETTER,
            source_type="job",
            source_id="job-1",
            title="Job failed again",
            organization_id=1,
        )
        self.assertEqual(a.incident_id, b.incident_id)
        self.db.commit()

        res = self.client.get("/api/platform/incidents")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["total"], 1)
        iid = res.json()["incidents"][0]["incident_id"]

        ack = self.client.post(
            f"/api/platform/incidents/{iid}/acknowledge",
            json={"note": "Pris en charge par ops"},
        )
        self.assertEqual(ack.status_code, 200)
        self.assertEqual(ack.json()["status"], "acknowledged")

        done = self.client.post(
            f"/api/platform/incidents/{iid}/resolve",
            json={"note": "Corrigé et vérifié"},
        )
        self.assertEqual(done.status_code, 200)
        self.assertEqual(done.json()["status"], "resolved")

    def test_global_search(self):
        res = self.client.get("/api/platform/global-search", params={"q": "Acme"})
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()["results"]["organizations"]), 1)

    def test_ops_detail_no_secrets(self):
        res = self.client.get("/api/platform/organizations/1/ops-detail")
        self.assertEqual(res.status_code, 200)
        raw = res.text.lower()
        self.assertNotIn("password_hash", raw)
        self.assertNotIn("sk_live", raw)

    def test_audit_filters(self):
        self.client.post(
            "/api/platform/organizations/1/suspend",
            json={"reason": "Test audit filtre suspension"},
        )
        res = self.client.get("/api/platform/audit", params={"action": "organization.suspend"})
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["total"], 1)


if __name__ == "__main__":
    unittest.main()
