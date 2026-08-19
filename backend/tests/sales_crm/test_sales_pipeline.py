"""SalesPilot Pipeline Engine V1 — board / move / permissions / health."""

from __future__ import annotations

from datetime import datetime, timedelta
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
from app.sales_crm.pipeline_service import aging_label, health_score_for, risk_level_for
from app.sales_crm.router import router
from app.sales_crm.service import create_company, create_opportunity, create_person
from app.services.auth import ROLE_PERMS


class SalesPipelineEngineTests(unittest.TestCase):
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

    def test_health_aging_risk_rules(self):
        self.assertEqual(aging_label(0), "Aujourd'hui")
        self.assertIn("jours", aging_label(12))
        score, label = health_score_for(
            days=2,
            has_contact=True,
            has_company=True,
            last_activity_at=datetime.utcnow(),
            next_activity_at=datetime.utcnow() + timedelta(days=1),
            has_open_task=True,
            probability=40,
            stage_probability=40,
        )
        self.assertGreaterEqual(score, 60)
        self.assertIn(label, ("Excellent", "Bon"))
        risk, rlabel = risk_level_for(
            days=50,
            last_activity_at=None,
            expected_close=None,
            probability=10,
            health=20,
        )
        self.assertEqual(risk, "critical")
        self.assertEqual(rlabel, "Critique")

    def test_pipeline_board_and_move(self):
        with patch("app.sales_crm.service.safe_publish") as publish:
            company = create_company(
                self.db, organization_id=1, user_id=1, data={"name": "ACME"}
            )
            person = create_person(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "company_id": company.id,
                },
            )
            opp = create_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "name": "Deal Cloud",
                    "estimated_amount": Decimal("8000"),
                    "company_id": company.id,
                    "person_id": person.id,
                    "probability": 40,
                },
            )
            self.db.commit()

            board = self.client.get("/api/sales/pipeline")
            self.assertEqual(board.status_code, 200)
            body = board.json()
            self.assertGreaterEqual(len(body["stages"]), 7)
            self.assertEqual(body["summary"]["open_opportunities"], 1)
            first_stage = body["stages"][0]
            self.assertEqual(first_stage["opportunity_count"], 1)
            card = first_stage["cards"][0]
            self.assertEqual(card["company_name"], "ACME")
            self.assertEqual(card["contact_name"], "Ada Lovelace")
            self.assertIn("health_score", card)
            self.assertIn("aging_label", card)
            self.assertIn("risk_level", card)

            target = body["stages"][2]["stage_id"]
            moved = self.client.post(
                f"/api/sales/pipeline/opportunities/{opp.id}/move",
                json={"stage_id": target, "expected_stage_id": first_stage["stage_id"]},
            )
            self.assertEqual(moved.status_code, 200)
            self.assertEqual(moved.json()["stage_id"], target)

            conflict = self.client.post(
                f"/api/sales/pipeline/opportunities/{opp.id}/move",
                json={"stage_id": first_stage["stage_id"], "expected_stage_id": 99999},
            )
            self.assertEqual(conflict.status_code, 409)

            names = [c.args[1].event_name for c in publish.call_args_list]
            self.assertIn(EventNames.SALES_OPPORTUNITY_STAGE_CHANGED, names)
            self.assertIn(EventNames.SALES_OPPORTUNITY_UPDATED, names)

            drawer = self.client.get(f"/api/sales/pipeline/opportunities/{opp.id}/drawer")
            self.assertEqual(drawer.status_code, 200)
            self.assertEqual(drawer.json()["company_name"], "ACME")
            self.assertGreaterEqual(len(drawer.json()["contacts"]), 1)

    def test_pipeline_permission(self):
        self._permissions = ["invoice.read"]
        res = self.client.get("/api/sales/pipeline")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
