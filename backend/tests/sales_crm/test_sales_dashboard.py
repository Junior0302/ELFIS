"""SalesPilot Dashboard V1 — aggregation / permissions / org isolation."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.models_saas import Organization, User
from app.sales_crm.dashboard_service import SalesDashboardService
from app.sales_crm.router import router
from app.sales_crm.service import create_activity, create_company, create_lead, create_opportunity, create_task
from app.services.auth import ROLE_PERMS
import unittest


class SalesDashboardTests(unittest.TestCase):
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

    def test_dashboard_empty_org(self):
        res = self.client.get("/api/sales/dashboard")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["summary"]["open_leads"], 0)
        self.assertEqual(body["summary"]["open_opportunities"], 0)
        self.assertIsNotNone(body["pipeline"])
        self.assertGreaterEqual(len(body["pipeline"]["stages"]), 7)
        self.assertEqual(len(body["quick_actions"]), 4)
        self.assertIn("generated_at", body)

    def test_dashboard_aggregation_kpis(self):
        with patch("app.sales_crm.service.safe_publish"):
            create_lead(
                self.db,
                organization_id=1,
                user_id=1,
                data={"title": "Lead 1", "status": "new"},
            )
            company = create_company(
                self.db, organization_id=1, user_id=1, data={"name": "ACME"}
            )
            opp = create_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "name": "Deal",
                    "estimated_amount": Decimal("10000"),
                    "company_id": company.id,
                    "probability": 50,
                },
            )
            create_activity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "activity_type": "call",
                    "subject": "Call today",
                    "activity_at": datetime.utcnow(),
                    "opportunity_id": opp.id,
                },
            )
            create_task(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "title": "Overdue task",
                    "status": "todo",
                    "priority": "high",
                    "due_at": datetime.utcnow() - timedelta(days=2),
                },
            )
            self.db.commit()

        res = self.client.get("/api/sales/dashboard")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        summary = body["summary"]
        self.assertEqual(summary["open_leads"], 1)
        self.assertEqual(summary["open_opportunities"], 1)
        self.assertEqual(float(summary["pipeline_value"]), 10000.0)
        self.assertEqual(float(summary["weighted_pipeline_value"]), 5000.0)
        self.assertEqual(summary["overdue_tasks"], 1)
        self.assertEqual(summary["activities_today"], 1)
        self.assertEqual(len(body["recent_opportunities"]), 1)
        self.assertEqual(body["recent_opportunities"][0]["company_name"], "ACME")
        self.assertEqual(len(body["tasks"]["overdue"]), 1)
        self.assertEqual(len(body["activities"]["today"]), 1)

        # Pipeline stage with the open opp has count >= 1
        counts = sum(s["opportunity_count"] for s in body["pipeline"]["stages"] if not s["is_won"] and not s["is_lost"])
        self.assertGreaterEqual(counts, 1)

    def test_dashboard_permission_denied(self):
        self._permissions = ["invoice.read"]
        res = self.client.get("/api/sales/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_dashboard_org_isolation(self):
        with patch("app.sales_crm.service.safe_publish"):
            create_lead(
                self.db,
                organization_id=1,
                user_id=1,
                data={"title": "Org1", "status": "new"},
            )
            self.db.commit()

        self._org_id = 2
        res = self.client.get("/api/sales/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["summary"]["open_leads"], 0)

    def test_service_direct_weighted(self):
        with patch("app.sales_crm.service.safe_publish"):
            create_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                data={"name": "A", "estimated_amount": Decimal("2000"), "probability": 25},
            )
            self.db.commit()
        out = SalesDashboardService(self.db).build(organization_id=1, user_id=1)
        self.assertEqual(out.summary.open_opportunities, 1)
        self.assertEqual(out.summary.weighted_pipeline_value, Decimal("500.00"))


if __name__ == "__main__":
    unittest.main()
