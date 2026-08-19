"""Tests C1.14 — Command Center."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dashboard_command_center.router import router
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Customer, Organization, OrganizationMember, Role, SalesDocument, User
from app.models_vault import VaultDocument
from app.services.auth import ROLE_PERMS
from app.subscriptions.access import SubscriptionAccess


def _access(**over) -> SubscriptionAccess:
    base = dict(
        has_access=True,
        read_only=False,
        subscription_status="active",
        raw_status="active",
        plan="pro",
        admin_revoked=False,
        trial_end=None,
        current_period_end=None,
        cancel_at_period_end=False,
        access_reason="active",
        price_eur=19,
        configured=True,
        trial_used=True,
    )
    base.update(over)
    # SubscriptionAccess may have different fields — adapt via MagicMock if needed
    try:
        return SubscriptionAccess(**{k: v for k, v in base.items() if True})
    except TypeError:
        m = MagicMock()
        for k, v in base.items():
            setattr(m, k, v)
        return m


class CommandCenterTests(unittest.TestCase):
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
        from app import models_vault  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.org = Organization(id=42, name="CreaLab Auto", platform_status="active", setup_completed=True)
        self.org_b = Organization(id=99, name="Other", platform_status="active")
        self.role = Role(id=1, name="owner", permissions='["*"]')
        self.user = User(
            id=7,
            email="owner@dev.local",
            first_name="Chris",
            last_name="Owner",
            status="active",
            password_hash="x",
        )
        self.db.add_all([self.org, self.org_b, self.role, self.user])
        self.db.commit()
        self.db.add(
            OrganizationMember(user_id=7, organization_id=42, role_id=1, status="active")
        )
        self.db.commit()

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self._permissions = list(ROLE_PERMS.get("owner", ["*"]))

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="owner",
                permissions=self._permissions,
            )

        self.app.dependency_overrides[get_db] = _db
        self.app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(self.app)

        self._access_patch = patch(
            "app.dashboard_command_center.service.get_subscription_access",
            return_value=_access(),
        )
        self._access_patch.start()
        self._notif_patch = patch(
            "app.dashboard_command_center.service.NotificationService.get_unread_count",
            return_value=0,
        )
        self._notif_patch.start()
        self._acct_patch = patch(
            "app.dashboard_command_center.service.AccountingService.list_proposals",
            return_value=([], 0),
        )
        self._acct_patch.start()
        self._fin_patch = patch(
            "app.dashboard_command_center.service.FinancialEngine.snapshot",
            return_value={
                "has_data": False,
                "overdue_count": 0,
                "overdue_amount": 0.0,
                "pending_count": 0,
                "unpaid_amount": 0.0,
                "documents_to_process": 0,
            },
        )
        self._fin_patch.start()

    def tearDown(self):
        self._access_patch.stop()
        self._notif_patch.stop()
        self._acct_patch.stop()
        self._fin_patch.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _get(self):
        return self.client.get("/api/dashboard/command-center")

    def test_unauthenticated(self):
        def _anon():
            return AuthContext(user=None, organization_id=None, role=None, permissions=[])

        self.app.dependency_overrides[get_auth_context] = _anon
        res = self._get()
        self.assertEqual(res.status_code, 401)

    def test_organization_missing(self):
        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=404,
                role="owner",
                permissions=["*"],
            )

        self.app.dependency_overrides[get_auth_context] = _auth
        res = self._get()
        self.assertEqual(res.status_code, 404)

    def test_schema_and_aggregation(self):
        res = self._get()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["organization_name"], "CreaLab Auto")
        self.assertIn("priorities", body)
        self.assertIn("smart_summary", body)
        self.assertIn("activity_timeline", body)
        self.assertIn("ai_insights", body)
        self.assertIn("quick_actions", body)
        self.assertIn("system_health", body)
        self.assertEqual(
            body["ai_insights"]["message"],
            "Aucune décision ne nécessite votre attention actuellement.",
        )
        self.assertEqual(body["ai_insights"]["title"], "À examiner")
        self.assertLessEqual(len(body["priorities"]), 5)
        self.assertLessEqual(len(body["activity_timeline"]), 20)

    def test_quick_actions_reuse_launch(self):
        res = self._get()
        keys = {a["key"] for a in res.json()["quick_actions"]}
        self.assertTrue(keys.issubset({"new_customer", "new_invoice", "import_document", "open_accounting"}))

    def test_quick_actions_filtered_by_permission(self):
        self._permissions[:] = ["invoice.read"]
        res = self._get()
        self.assertEqual(res.json()["quick_actions"], [])

    def test_summary_real_counts(self):
        self.db.add(Customer(organization_id=42, name="Client A", created_at=datetime.utcnow()))
        self.db.add(
            SalesDocument(
                organization_id=42,
                doc_type="facture",
                number="F-1",
                issue_date="2026-01-01",
                status="draft",
                customer_name="Client A",
                amount_ht=10,
                vat_rate=20,
                amount_tva=2,
                amount_ttc=12,
            )
        )
        self.db.add(
            VaultDocument(
                organization_id=42,
                document_type="invoice",
                original_filename="a.pdf",
                storage_path="/a",
                mime_type="application/pdf",
                file_size=1,
                checksum_sha256="x",
            )
        )
        self.db.commit()
        metrics = {m["key"]: m["value"] for m in self._get().json()["smart_summary"]["metrics"]}
        self.assertEqual(metrics.get("customers"), 1)
        self.assertEqual(metrics.get("invoices"), 1)
        self.assertEqual(metrics.get("documents"), 1)

    def test_priority_overdue(self):
        self._fin_patch.stop()
        self._fin_patch = patch(
            "app.dashboard_command_center.service.FinancialEngine.snapshot",
            return_value={
                "has_data": True,
                "overdue_count": 2,
                "overdue_amount": 500.0,
                "pending_count": 2,
                "unpaid_amount": 500.0,
                "documents_to_process": 0,
            },
        )
        self._fin_patch.start()
        body = self._get().json()
        ids = [p["id"] for p in body["priorities"]]
        self.assertIn("invoices-overdue", ids)

    def test_priority_subscription(self):
        self._access_patch.stop()
        self._access_patch = patch(
            "app.dashboard_command_center.service.get_subscription_access",
            return_value=_access(has_access=False, read_only=False),
        )
        self._access_patch.start()
        ids = [p["id"] for p in self._get().json()["priorities"]]
        self.assertIn("subscription-required", ids)

    def test_isolation_timeline(self):
        self.db.add(Customer(organization_id=99, name="Other Org Client", created_at=datetime.utcnow()))
        self.db.add(Customer(organization_id=42, name="Mine", created_at=datetime.utcnow()))
        self.db.commit()
        titles = " ".join(i["description"] for i in self._get().json()["activity_timeline"])
        self.assertIn("Mine", titles)
        self.assertNotIn("Other Org Client", titles)

    def test_timeline_limit(self):
        for i in range(12):
            self.db.add(
                Customer(
                    organization_id=42,
                    name=f"C{i}",
                    created_at=datetime.utcnow(),
                )
            )
        self.db.commit()
        self.assertLessEqual(len(self._get().json()["activity_timeline"]), 20)

    def test_system_health_no_unknown_ok(self):
        services = self._get().json()["system_health"]["services"]
        keys = {s["key"] for s in services}
        # Search / Document Intelligence volontairement absents (état inconnu)
        self.assertNotIn("search", keys)
        self.assertNotIn("document_intelligence", keys)
        for s in services:
            self.assertIn(s["status"], {"ok", "warning", "critical", "degraded"})

    def test_ai_insights_empty_when_no_decisions(self):
        ai = self._get().json()["ai_insights"]
        self.assertEqual(ai["status"], "empty")
        self.assertEqual(ai["title"], "À examiner")
        self.assertEqual(ai["insights"], [])
        self.assertIn("Aucune décision", ai["message"])

if __name__ == "__main__":
    unittest.main()
