"""SalesPilot Relationship Workspace V1 — aggregation / timeline / permissions."""

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
from app.deps import AuthContext, get_auth_context, require_active_subscription
from app.events.event_types import EventNames
from app.models_saas import Organization, User
from app.sales_crm.router import router
from app.sales_crm.service import (
    create_activity,
    create_company,
    create_lead,
    create_note,
    create_opportunity,
    create_person,
    create_task,
)
from app.sales_crm.workspace_service import relationship_score_for
from app.services.auth import ROLE_PERMS


class SalesWorkspaceTests(unittest.TestCase):
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
        app.dependency_overrides[require_active_subscription] = _auth
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_relationship_score_deterministic(self):
        now = datetime.utcnow()
        score, label, expl, factors = relationship_score_for(
            activities_count=5,
            last_activity_at=now - timedelta(days=2),
            contacts_count=2,
            has_email=True,
            has_phone=True,
            has_company=True,
            created_at=now - timedelta(days=60),
            now=now,
        )
        self.assertGreaterEqual(score, 40)
        self.assertLessEqual(score, 100)
        self.assertIn(label, ("Excellent", "Bon", "Correct", "Fragile"))
        self.assertTrue(factors)

    def test_workspace_aggregation_and_timeline(self):
        with patch("app.sales_crm.workspace_service.safe_publish") as publish:
            company = create_company(
                self.db, organization_id=1, user_id=1, data={"name": "ACME WS"}
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
                    "phone": "+33102030405",
                    "job_title": "CTO",
                },
            )
            lead = create_lead(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "title": "Lead Cloud",
                    "company_id": company.id,
                    "person_id": person.id,
                    "estimated_amount": Decimal("12000"),
                },
            )
            opp = create_opportunity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "name": "Deal Workspace",
                    "estimated_amount": Decimal("12000"),
                    "company_id": company.id,
                    "person_id": person.id,
                    "lead_id": lead.id,
                    "probability": 40,
                },
            )
            create_activity(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "activity_type": "call",
                    "subject": "Discovery call",
                    "company_id": company.id,
                    "person_id": person.id,
                    "opportunity_id": opp.id,
                    "result": "positif",
                },
            )
            create_task(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "title": "Envoyer proposition",
                    "company_id": company.id,
                    "opportunity_id": opp.id,
                    "due_at": datetime.utcnow() - timedelta(days=1),
                    "priority": "high",
                },
            )
            create_note(
                self.db,
                organization_id=1,
                user_id=1,
                data={
                    "body_markdown": "**Note** importante",
                    "entity_type": "opportunity",
                    "entity_id": opp.id,
                },
            )
            lead.converted_opportunity_id = opp.id
            self.db.commit()

            for entity, eid in (
                ("company", company.id),
                ("person", person.id),
                ("lead", lead.id),
                ("opportunity", opp.id),
            ):
                res = self.client.get(f"/api/sales/workspace/{entity}/{eid}")
                self.assertEqual(res.status_code, 200, res.text)
                body = res.json()
                self.assertEqual(body["header"]["entity"], entity)
                self.assertEqual(body["header"]["entity_id"], eid)
                self.assertIn("health", body)
                self.assertIn("relationship", body)
                self.assertIn("timeline", body)
                self.assertIn("quick_actions", body)
                self.assertIn("generated_at", body)
                self.assertGreaterEqual(len(body["contacts"]), 1)
                self.assertGreaterEqual(len(body["activities"]), 1)
                self.assertGreaterEqual(len(body["tasks"]), 1)
                self.assertGreaterEqual(len(body["notes"]), 1)
                self.assertGreaterEqual(len(body["timeline"]), 2)
                times = [item["occurred_at"] for item in body["timeline"]]
                self.assertEqual(times, sorted(times, reverse=True))
                task_buckets = {t["bucket"] for t in body["tasks"]}
                self.assertTrue(task_buckets & {"overdue", "today", "upcoming", "other"})

            names = [c.args[1].event_name for c in publish.call_args_list]
            self.assertIn(EventNames.SALES_WORKSPACE_OPENED, names)
            self.assertIn(EventNames.SALES_RELATIONSHIP_UPDATED, names)
            self.assertIn(EventNames.SALES_TIMELINE_UPDATED, names)

    def test_workspace_invalid_entity(self):
        res = self.client.get("/api/sales/workspace/invoice/1")
        self.assertEqual(res.status_code, 400)

    def test_workspace_permission(self):
        self._permissions = ["invoice.read"]
        res = self.client.get("/api/sales/workspace/company/1")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
