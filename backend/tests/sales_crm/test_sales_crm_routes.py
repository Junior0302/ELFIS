"""SalesPilot CRM Foundation - CRUD / permissions / org isolation / events."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.events.event_types import EventNames
from app.models_saas import Organization, User
from app.sales_crm.router import router
from app.services.auth import ROLE_PERMS


class SalesCrmRoutesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app import models_saas  # noqa: F401
        from app import models_vault  # noqa: F401
        from app.events import event_models  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(Organization(id=1, name="Org A"))
        self.db.add(Organization(id=2, name="Org B"))
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

        self._permissions = list(ROLE_PERMS.get("owner", ["*"]))
        self._org_id = 1

        def _auth():
            return AuthContext(
                user=self.user,
                organization_id=self._org_id,
                role="owner",
                permissions=list(self._permissions),
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        app.dependency_overrides[require_active_subscription] = _auth
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_bootstrap_creates_default_pipeline(self):
        res = self.client.get("/api/sales/bootstrap")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["pipeline"]["code"], "default")
        codes = [s["code"] for s in body["pipeline"]["stages"]]
        self.assertIn("prospection", codes)
        self.assertIn("gagne", codes)
        self.assertIn("perdu", codes)
        self.assertGreaterEqual(len(body["lost_reasons"]), 1)
        self.assertGreaterEqual(len(body["win_reasons"]), 1)

    def test_lead_crud_and_soft_delete(self):
        with patch("app.sales_crm.service.safe_publish") as publish:
            create = self.client.post(
                "/api/sales/leads",
                json={"title": "Lead ACME", "status": "new", "priority": "high"},
            )
            self.assertEqual(create.status_code, 201)
            lead_id = create.json()["id"]
            self.assertTrue(
                any(
                    c.args[1].event_name == EventNames.SALES_LEAD_CREATED
                    for c in publish.call_args_list
                )
            )

        listed = self.client.get("/api/sales/leads")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["pagination"]["total"], 1)

        got = self.client.get(f"/api/sales/leads/{lead_id}")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["title"], "Lead ACME")

        patched = self.client.patch(f"/api/sales/leads/{lead_id}", json={"status": "qualified"})
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["status"], "qualified")

        deleted = self.client.delete(f"/api/sales/leads/{lead_id}")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/api/sales/leads/{lead_id}")
        self.assertEqual(missing.status_code, 404)

    def test_company_opportunity_stage_change_events(self):
        with patch("app.sales_crm.service.safe_publish") as publish:
            company = self.client.post("/api/sales/companies", json={"name": "ACME SA"})
            self.assertEqual(company.status_code, 201)
            company_id = company.json()["id"]

            boot = self.client.get("/api/sales/bootstrap")
            stage_id = boot.json()["pipeline"]["stages"][1]["id"]
            pipeline_id = boot.json()["pipeline"]["id"]

            opp = self.client.post(
                "/api/sales/opportunities",
                json={
                    "name": "Deal Q1",
                    "estimated_amount": "12000.00",
                    "company_id": company_id,
                    "pipeline_id": pipeline_id,
                },
            )
            self.assertEqual(opp.status_code, 201)
            opp_id = opp.json()["id"]

            moved = self.client.patch(
                f"/api/sales/opportunities/{opp_id}",
                json={"stage_id": stage_id},
            )
            self.assertEqual(moved.status_code, 200)
            names = [c.args[1].event_name for c in publish.call_args_list]
            self.assertIn(EventNames.SALES_COMPANY_CREATED, names)
            self.assertIn(EventNames.SALES_OPPORTUNITY_CREATED, names)
            self.assertIn(EventNames.SALES_OPPORTUNITY_STAGE_CHANGED, names)

    def test_task_completed_event(self):
        with patch("app.sales_crm.service.safe_publish") as publish:
            created = self.client.post(
                "/api/sales/tasks",
                json={"title": "Relancer client", "priority": "high"},
            )
            self.assertEqual(created.status_code, 201)
            task_id = created.json()["id"]
            done = self.client.patch(f"/api/sales/tasks/{task_id}", json={"status": "done"})
            self.assertEqual(done.status_code, 200)
            self.assertEqual(done.json()["status"], "done")
            self.assertIsNotNone(done.json()["completed_at"])
            names = [c.args[1].event_name for c in publish.call_args_list]
            self.assertIn(EventNames.SALES_TASK_CREATED, names)
            self.assertIn(EventNames.SALES_TASK_COMPLETED, names)

    def test_activity_created(self):
        with patch("app.sales_crm.service.safe_publish") as publish:
            res = self.client.post(
                "/api/sales/activities",
                json={
                    "activity_type": "call",
                    "subject": "Appel découverte",
                    "result": "intéressé",
                    "comment": "Rappeler jeudi",
                },
            )
            self.assertEqual(res.status_code, 201)
            self.assertEqual(res.json()["activity_type"], "call")
            self.assertTrue(
                any(
                    c.args[1].event_name == EventNames.SALES_ACTIVITY_CREATED
                    for c in publish.call_args_list
                )
            )

    def test_permissions_denied_without_sales_read(self):
        self._permissions = ["invoice.read"]
        res = self.client.get("/api/sales/leads")
        self.assertEqual(res.status_code, 403)

    def test_org_isolation(self):
        with patch("app.sales_crm.service.safe_publish"):
            self._org_id = 1
            created = self.client.post("/api/sales/leads", json={"title": "Org1 Lead"})
            self.assertEqual(created.status_code, 201)
            lead_id = created.json()["id"]

            self._org_id = 2
            missing = self.client.get(f"/api/sales/leads/{lead_id}")
            self.assertEqual(missing.status_code, 404)

            listed = self.client.get("/api/sales/leads")
            self.assertEqual(listed.json()["pagination"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
