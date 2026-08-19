"""Tests C1.12 — Launch Dashboard."""

from __future__ import annotations

import unittest
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.dashboard_launch.router import router
from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import (
    Contact,
    Customer,
    Organization,
    OrganizationMember,
    Role,
    SalesDocument,
    User,
)
from app.models_vault import VaultDocument
from app.services.auth import ROLE_PERMS


class LaunchDashboardTests(unittest.TestCase):
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

        self.org = Organization(
            id=42,
            name="CreaLab Auto",
            platform_status="active",
            setup_completed=True,
            setup_completed_at=datetime.utcnow(),
            setup_version=1,
        )
        self.org_b = Organization(id=99, name="Other Org", platform_status="active")
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
            OrganizationMember(
                user_id=7,
                organization_id=42,
                role_id=1,
                status="active",
            )
        )
        self.db.commit()

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")

        def _db():
            try:
                yield self.db
            finally:
                pass

        self._auth_permissions = list(ROLE_PERMS.get("owner", ["*"]))
        self._auth_user = self.user
        self._auth_org_id = 42

        def _auth():
            return AuthContext(
                user=self._auth_user,
                organization_id=self._auth_org_id,
                role="owner",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_db] = _db
        self.app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _get(self):
        return self.client.get("/api/dashboard/launch")

    def test_01_workspace_ready(self):
        res = self._get()
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body["workspace_ready"])
        self.assertEqual(body["organization"]["name"], "CreaLab Auto")
        self.assertEqual(body["user"]["display_name"], "Chris")

    def test_02_org_missing_404(self):
        self._auth_org_id = 404

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

    def test_03_unauthenticated(self):
        self._auth_user = None

        def _auth():
            return AuthContext(user=None, organization_id=42, role=None, permissions=[])

        self.app.dependency_overrides[get_auth_context] = _auth
        res = self._get()
        self.assertEqual(res.status_code, 401)

    def test_04_isolation(self):
        self.db.add(Customer(organization_id=99, name="Foreign"))
        self.db.commit()
        body = self._get().json()
        cust = next(s for s in body["onboarding"]["steps"] if s["key"] == "first_customer")
        self.assertFalse(cust["completed"])

    def test_05_company_setup_done(self):
        body = self._get().json()
        step = next(s for s in body["onboarding"]["steps"] if s["key"] == "company_setup")
        self.assertTrue(step["completed"])

    def test_06_first_customer(self):
        before = self._get().json()
        self.assertFalse(
            next(s for s in before["onboarding"]["steps"] if s["key"] == "first_customer")[
                "completed"
            ]
        )
        self.db.add(Customer(organization_id=42, name="Client A"))
        self.db.commit()
        after = self._get().json()
        self.assertTrue(
            next(s for s in after["onboarding"]["steps"] if s["key"] == "first_customer")[
                "completed"
            ]
        )

    def test_07_first_supplier(self):
        self.db.add(
            Contact(
                organization_id=42,
                contact_type="supplier",
                status="active",
                company_name="Fournisseur",
            )
        )
        self.db.commit()
        body = self._get().json()
        self.assertTrue(
            next(s for s in body["onboarding"]["steps"] if s["key"] == "first_supplier")[
                "completed"
            ]
        )

    def test_08_first_invoice(self):
        self.db.add(
            SalesDocument(
                organization_id=42,
                doc_type="facture",
                number="F-1",
                issue_date="2026-01-01",
                status="draft",
            )
        )
        self.db.commit()
        body = self._get().json()
        self.assertTrue(
            next(s for s in body["onboarding"]["steps"] if s["key"] == "first_invoice")[
                "completed"
            ]
        )

    def test_09_first_document(self):
        self.db.add(
            VaultDocument(
                organization_id=42,
                document_type="invoice",
                original_filename="scan.pdf",
                storage_path="/tmp/scan.pdf",
                mime_type="application/pdf",
                file_size=10,
                checksum_sha256="abc",
            )
        )
        self.db.commit()
        body = self._get().json()
        self.assertTrue(
            next(s for s in body["onboarding"]["steps"] if s["key"] == "first_document")[
                "completed"
            ]
        )

    def test_10_progress_formula(self):
        body = self._get().json()
        onb = body["onboarding"]
        expected = round(onb["completed_steps"] / onb["total_steps"] * 100)
        self.assertEqual(onb["progress"], expected)
        self.assertEqual(onb["total_steps"], 6)

    def test_11_recommendation_first_incomplete(self):
        body = self._get().json()
        # company done → next with path is first_customer
        rec = body["onboarding"]["recommended_action"]
        self.assertIsNotNone(rec)
        self.assertEqual(rec["key"], "first_customer")
        self.assertEqual(rec["action_path"], "/clients")

    def test_12_inaccessible_step_skipped_in_recommendation(self):
        self._auth_permissions = ["documents.read", "documents.write", "ai.analysis"]

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="employe",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_auth_context] = _auth
        # no invoice.create → skip customer/invoice → recommend document
        body = self._get().json()
        rec = body["onboarding"]["recommended_action"]
        self.assertEqual(rec["key"], "first_document")

    def test_13_quick_actions_filtered(self):
        self._auth_permissions = ["documents.write", "documents.read"]

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="employe",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_auth_context] = _auth
        body = self._get().json()
        keys = {a["key"] for a in body["quick_actions"]}
        self.assertIn("import_document", keys)
        self.assertNotIn("new_customer", keys)
        self.assertLessEqual(len(body["quick_actions"]), 4)

    def test_14_15_activity_sorted_and_capped(self):
        for i in range(4):
            self.db.add(Customer(organization_id=42, name=f"C{i}"))
        for i in range(4):
            self.db.add(
                SalesDocument(
                    organization_id=42,
                    doc_type="facture",
                    number=f"F{i}",
                    issue_date="2026-01-01",
                    status="sent",
                )
            )
        self.db.commit()
        body = self._get().json()
        acts = body["recent_activity"]
        self.assertLessEqual(len(acts), 5)
        dates = [a["occurred_at"] for a in acts]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_16_empty_activity(self):
        body = self._get().json()
        self.assertEqual(body["recent_activity"], [])

    def test_19_schema_keys(self):
        body = self._get().json()
        for key in ("workspace_ready", "user", "organization", "onboarding", "quick_actions", "recent_activity"):
            self.assertIn(key, body)
        self.assertEqual(len(body["onboarding"]["steps"]), 6)

    def test_accounting_discovered(self):
        res = self.client.post("/api/dashboard/launch/accounting-discovered")
        self.assertEqual(res.status_code, 200, res.text)
        body = self._get().json()
        self.assertTrue(
            next(s for s in body["onboarding"]["steps"] if s["key"] == "accounting_discovery")[
                "completed"
            ]
        )

    def test_all_completed_flag(self):
        self.db.add(Customer(organization_id=42, name="C"))
        self.db.add(
            Contact(
                organization_id=42,
                contact_type="supplier",
                status="active",
                company_name="S",
            )
        )
        self.db.add(
            SalesDocument(
                organization_id=42,
                doc_type="facture",
                number="F1",
                issue_date="2026-01-01",
                status="sent",
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
        member = (
            self.db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == 42, OrganizationMember.user_id == 7)
            .one()
        )
        member.accounting_hub_visited_at = datetime.utcnow()
        self.db.add(member)
        self.db.commit()
        body = self._get().json()
        self.assertEqual(body["onboarding"]["progress"], 100)
        self.assertTrue(body["onboarding"]["all_completed"])
        self.assertIsNone(body["onboarding"]["recommended_action"])


if __name__ == "__main__":
    unittest.main()
