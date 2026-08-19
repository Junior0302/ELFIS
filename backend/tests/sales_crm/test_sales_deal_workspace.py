"""SalesPilot Deal Workspace V1 — forecast / products / timeline / permissions."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.events.event_types import EventNames
from app.models_saas import Organization, User
from app.sales_crm.deal_service import compute_forecast, compute_line_total
from app.sales_crm.router import router
from app.sales_crm.service import (
    create_activity,
    create_company,
    create_opportunity,
    create_person,
    create_task,
    update_opportunity,
)
from app.services.auth import ROLE_PERMS


class SalesDealWorkspaceTests(unittest.TestCase):
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
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_forecast_and_line_total(self):
        self.assertEqual(compute_forecast(Decimal("10000"), 40), Decimal("4000.00"))
        self.assertEqual(
            compute_line_total(Decimal("2"), Decimal("100"), Decimal("10")),
            Decimal("180.00"),
        )

    def test_deal_workspace_products_timeline_events(self):
        with patch("app.sales_crm.deal_service.safe_publish") as publish:
            company = create_company(
                self.db, organization_id=1, user_id=1, data={"name": "ACME Deal"}
            )
            person = create_person(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "company_id": company.id,
                    "email": "ada@acme.test",
                },
            )
            opp = create_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "name": "Deal Cockpit",
                    "estimated_amount": Decimal("10000"),
                    "company_id": company.id,
                    "person_id": person.id,
                    "probability": 40,
                    "expected_close_date": date.today() + timedelta(days=30),
                },
            )
            create_activity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "activity_type": "meeting",
                    "subject": "Kickoff",
                    "opportunity_id": opp.id,
                    "company_id": company.id,
                },
            )
            create_task(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "title": "Envoyer devis",
                    "opportunity_id": opp.id,
                    "due_at": datetime.utcnow() + timedelta(days=2),
                },
            )
            self.db.commit()

            prod = self.client.post(
                f"/api/sales/opportunities/{opp.id}/products",
                json={
                    "name": "Licence Cloud",
                    "description": "Annuel",
                    "quantity": "2",
                    "unit_price": "500",
                    "discount_percent": "10",
                },
            )
            self.assertEqual(prod.status_code, 201, prod.text)
            body_prod = prod.json()
            self.assertEqual(body_prod["line_total"], "900.00")
            product_id = body_prod["id"]

            participant = self.client.post(
                f"/api/sales/opportunities/{opp.id}/participants",
                json={"person_id": person.id, "role": "decision_maker", "is_primary": False},
            )
            self.assertEqual(participant.status_code, 201, participant.text)

            update_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                opportunity_id=opp.id,
                data={"estimated_amount": Decimal("12000"), "probability": 50},
            )
            self.db.commit()

            ws = self.client.get(f"/api/sales/opportunities/{opp.id}/workspace")
            self.assertEqual(ws.status_code, 200, ws.text)
            body = ws.json()
            self.assertEqual(body["header"]["name"], "Deal Cockpit")
            self.assertEqual(body["header"]["company_name"], "ACME Deal")
            self.assertEqual(body["forecast"]["weighted_amount"], "6000.00")
            self.assertEqual(body["forecast"]["probability"], 50)
            self.assertGreaterEqual(len(body["participants"]), 1)
            self.assertGreaterEqual(len(body["products"]), 1)
            self.assertGreaterEqual(len(body["activities"]), 1)
            self.assertGreaterEqual(len(body["tasks"]), 1)
            self.assertIn("timeline", body)
            self.assertIn("health", body)
            self.assertIn("relationship", body)
            self.assertTrue(any(a["id"] == "quote" for a in body["quick_actions"]))

            types = {t["event_type"] for t in body["timeline"]}
            self.assertIn("opportunity_created", types)
            self.assertIn("product_added", types)

            deleted = self.client.delete(
                f"/api/sales/opportunities/{opp.id}/products/{product_id}"
            )
            self.assertEqual(deleted.status_code, 204)

            names = [c.args[1].event_name for c in publish.call_args_list]
            self.assertIn(EventNames.SALES_PRODUCT_ADDED, names)
            self.assertIn(EventNames.SALES_PRODUCT_REMOVED, names)
            self.assertIn(EventNames.SALES_DEAL_OPENED, names)
            self.assertIn(EventNames.SALES_FORECAST_UPDATED, names)

    def test_deal_permission(self):
        self._permissions = ["invoice.read"]
        res = self.client.get("/api/sales/opportunities/1/workspace")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
