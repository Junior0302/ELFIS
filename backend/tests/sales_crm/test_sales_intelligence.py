"""Sales Intelligence V1 â€” backend tests (deterministic, no generative AI)."""

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
from app.sales_crm.service import create_company, create_opportunity, create_task, ensure_default_pipeline
from app.sales_intelligence.enums import InsightStatus, InsightType
from app.sales_intelligence.router import router
from app.sales_intelligence.service import SalesIntelligenceService
from app.services.auth import ROLE_PERMS


class SalesIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app.sales_proposals import models as prop_models  # noqa: F401
        from app.sales_intelligence import models as intel_models  # noqa: F401
        from app import models_saas  # noqa: F401
        from app.events import event_models  # noqa: F401
        from app.decision_center import models as dec_models  # noqa: F401
        from app.notifications import notification_models  # noqa: F401

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
        self._permissions = list(ROLE_PERMS.get("owner", ["*"]))
        self._org_id = 1

        def _db():
            try:
                yield self.db
            finally:
                pass

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
        self._publish = patch("app.sales_intelligence.events.safe_publish")
        self.publish = self._publish.start()
        ensure_default_pipeline(self.db, organization_id=1, user_id=1)
        self.db.commit()

    def tearDown(self):
        self._publish.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_no_urgent_focus(self):
        res = self.client.get("/api/sales/intelligence?sync=true")
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["focus"]["tone"], "no_urgent_focus")
        self.assertIn("Aucune urgence", body["focus"]["title"])

    def test_critical_overdue_task_focus(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Relance VIP",
                "priority": "high",
                "due_at": datetime.utcnow() - timedelta(days=3),
                "status": "todo",
            },
        )
        self.db.commit()
        res = self.client.get("/api/sales/intelligence?sync=true")
        self.assertEqual(res.status_code, 200, res.text)
        focus = res.json()["focus"]
        self.assertIn(focus["severity"], ("high", "critical"))
        self.assertNotEqual(focus["tone"], "no_urgent_focus")

        items = self.client.get(
            "/api/sales/intelligence/insights",
            params={"category": "task"},
        )
        self.assertEqual(items.status_code, 200)
        self.assertGreaterEqual(items.json()["total"], 1)
        types = {i["insight_type"] for i in items.json()["items"]}
        self.assertIn(InsightType.task_critical_overdue.value, types)

    def test_high_value_inactive_opportunity(self):
        company = create_company(
            self.db, organization_id=1, user_id=1, data={"name": "Big Co"}
        )
        pipeline = ensure_default_pipeline(self.db, organization_id=1, user_id=1)
        stage = pipeline.stages[0] if hasattr(pipeline, "stages") else None
        from app.sales_crm.models import SalesPipelineStage

        stage = (
            self.db.query(SalesPipelineStage)
            .filter(SalesPipelineStage.pipeline_id == pipeline.id)
            .order_by(SalesPipelineStage.position.asc())
            .first()
        )
        opp = create_opportunity(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "name": "Mega Deal",
                "estimated_amount": Decimal("48000"),
                "company_id": company.id,
                "probability": 40,
                "stage_id": stage.id,
            },
        )
        opp.stage_entered_at = datetime.utcnow() - timedelta(days=20)
        self.db.commit()

        svc = SalesIntelligenceService(self.db)
        out = svc.sync(organization_id=1, user_id=1)
        self.db.commit()
        self.assertGreaterEqual(out.created + out.updated, 1)

        listed = self.client.get("/api/sales/intelligence/insights")
        types = {i["insight_type"] for i in listed.json()["items"]}
        self.assertTrue(
            InsightType.opportunity_inactive_high_value.value in types
            or InsightType.opportunity_no_next_action.value in types
            or InsightType.opportunity_stage_aging.value in types
        )

    def test_acknowledge_does_not_resolve(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Ack me",
                "priority": "high",
                "due_at": (datetime.utcnow() - timedelta(days=1)),
                "status": "todo",
            },
        )
        self.db.commit()
        self.client.get("/api/sales/intelligence?sync=true")
        items = self.client.get("/api/sales/intelligence/insights").json()["items"]
        self.assertTrue(items)
        iid = items[0]["id"]
        ack = self.client.post(f"/api/sales/intelligence/insights/{iid}/acknowledge")
        self.assertEqual(ack.status_code, 200, ack.text)
        self.assertEqual(ack.json()["status"], InsightStatus.acknowledged.value)
        self.assertIsNone(ack.json().get("resolved_at"))

    def test_dismiss_and_permission(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Dismiss me",
                "priority": "high",
                "due_at": (datetime.utcnow() - timedelta(days=1)),
                "status": "todo",
            },
        )
        self.db.commit()
        self.client.get("/api/sales/intelligence?sync=true")
        items = self.client.get("/api/sales/intelligence/insights").json()["items"]
        iid = items[0]["id"]
        # medium/high can dismiss without reason if not critical â€” may be critical
        dis = self.client.post(
            f"/api/sales/intelligence/insights/{iid}/dismiss",
            json={"reason": "TraitÃ© manuellement"},
        )
        self.assertEqual(dis.status_code, 200, dis.text)
        self.assertEqual(dis.json()["status"], InsightStatus.dismissed.value)

        self._permissions = ["invoice.read"]
        denied = self.client.get("/api/sales/intelligence")
        self.assertEqual(denied.status_code, 403)

    def test_org_isolation(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Org1 task",
                "priority": "high",
                "due_at": (datetime.utcnow() - timedelta(days=1)),
                "status": "todo",
            },
        )
        self.db.commit()
        self.client.get("/api/sales/intelligence?sync=true")
        self._org_id = 2
        ensure_default_pipeline(self.db, organization_id=2, user_id=1)
        self.db.commit()
        res = self.client.get("/api/sales/intelligence?sync=true")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["counts"]["active_count"], 0)

    def test_deduplication(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Dedupe",
                "priority": "high",
                "due_at": (datetime.utcnow() - timedelta(days=2)),
                "status": "todo",
            },
        )
        self.db.commit()
        svc = SalesIntelligenceService(self.db)
        a = svc.sync(organization_id=1)
        b = svc.sync(organization_id=1)
        self.db.commit()
        self.assertEqual(b.created, 0)
        self.assertGreaterEqual(a.created, 1)

    def test_explanation_and_actions(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={
                "title": "Explain",
                "priority": "high",
                "due_at": (datetime.utcnow() - timedelta(days=1)),
                "status": "todo",
            },
        )
        self.db.commit()
        self.client.get("/api/sales/intelligence?sync=true")
        item = self.client.get("/api/sales/intelligence/insights").json()["items"][0]
        detail = self.client.get(f"/api/sales/intelligence/insights/{item['id']}")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertIn("headline", body["explanation"])
        self.assertTrue(body["available_actions"])
        self.assertTrue(body["route"])


if __name__ == "__main__":
    unittest.main()
