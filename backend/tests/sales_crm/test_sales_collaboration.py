"""Sales Collaboration V1 — teams, assign, comments, reviews, transfer."""

from __future__ import annotations

from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization, OrganizationMember, Role, User
from app.sales_collaboration.router import router
from app.sales_crm.service import create_lead, create_opportunity, create_task, ensure_default_pipeline
from app.services.auth import ROLE_PERMS


class SalesCollaborationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app.sales_proposals import models as prop_models  # noqa: F401
        from app.sales_collaboration import models as collab_models  # noqa: F401
        from app import models_saas  # noqa: F401
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
        self.user2 = User(
            id=2,
            email="rep@test.local",
            first_name="Rep",
            last_name="Two",
            status="active",
            password_hash="x",
        )
        self.db.add(self.user)
        self.db.add(self.user2)
        role = Role(id=1, name="owner", permissions='["*"]')
        self.db.add(role)
        self.db.add(
            OrganizationMember(
                user_id=1, organization_id=1, role_id=1, status="active"
            )
        )
        self.db.add(
            OrganizationMember(
                user_id=2, organization_id=1, role_id=1, status="active"
            )
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api")

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
        self.client = TestClient(app)
        self._publish = patch("app.sales_collaboration.service.safe_publish")
        self.publish = self._publish.start()
        self._notify = patch.object(
            __import__(
                "app.sales_collaboration.service", fromlist=["SalesCollaborationService"]
            ).SalesCollaborationService,
            "_notify",
            return_value=None,
        )
        self._notify.start()
        ensure_default_pipeline(self.db, organization_id=1, user_id=1)
        self.db.commit()

    def tearDown(self):
        self._publish.stop()
        self._notify.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_team_create_and_member(self):
        res = self.client.post(
            "/api/sales/collab/teams",
            json={"name": "Équipe Nord", "lead_user_id": 1},
        )
        self.assertEqual(res.status_code, 201, res.text)
        team_id = res.json()["id"]
        add = self.client.post(
            f"/api/sales/collab/teams/{team_id}/members",
            json={"user_id": 2, "role": "member"},
        )
        self.assertEqual(add.status_code, 201, add.text)
        listed = self.client.get("/api/sales/collab/teams")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)
        self.assertGreaterEqual(len(listed.json()[0]["members"]), 2)

    def test_assign_opportunity(self):
        opp = create_opportunity(
            self.db,
            organization_id=1,
            user_id=1,
            data={"name": "Deal Collab", "owner_user_id": 1},
        )
        self.db.commit()
        res = self.client.post(
            "/api/sales/collab/assign",
            json={"resource": "opportunity", "resource_id": opp.id, "owner_user_id": 2},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["owner_user_id"], 2)
        self.assertEqual(res.json()["previous_owner_user_id"], 1)

    def test_comment_mention_and_followers(self):
        lead = create_lead(
            self.db, organization_id=1, user_id=1, data={"title": "Lead collab"}
        )
        self.db.commit()
        follow = self.client.post(
            "/api/sales/collab/followers",
            json={"entity_type": "lead", "entity_id": lead.id},
        )
        self.assertEqual(follow.status_code, 201, follow.text)
        comment = self.client.post(
            "/api/sales/collab/comments",
            json={
                "entity_type": "lead",
                "entity_id": lead.id,
                "body": "Bonjour @[2:Rep Two] merci",
            },
        )
        self.assertEqual(comment.status_code, 201, comment.text)
        self.assertEqual(len(comment.json()["mentions"]), 1)
        listed = self.client.get(
            f"/api/sales/collab/comments?entity_type=lead&entity_id={lead.id}"
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

    def test_review_and_decide(self):
        opp = create_opportunity(
            self.db, organization_id=1, user_id=1, data={"name": "Review me"}
        )
        self.db.commit()
        created = self.client.post(
            "/api/sales/collab/reviews",
            json={
                "entity_type": "opportunity",
                "entity_id": opp.id,
                "reviewer_user_id": 1,
                "message": "Please check",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        rid = created.json()["id"]
        decided = self.client.post(
            f"/api/sales/collab/reviews/{rid}/decide",
            json={"decision": "approved", "decision_comment": "OK"},
        )
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(decided.json()["status"], "approved")

    def test_transfer_ownership(self):
        lead = create_lead(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "Transfer", "owner_user_id": 1},
        )
        self.db.commit()
        res = self.client.post(
            "/api/sales/collab/transfer",
            json={
                "entity_type": "lead",
                "entity_id": lead.id,
                "to_user_id": 2,
                "reason": "handover",
                "comment": "Congé",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["to_user_id"], 2)

    def test_team_dashboard_and_views(self):
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "T1", "status": "open", "assignee_user_id": 1},
        )
        self.db.commit()
        dash = self.client.get("/api/sales/collab/team-dashboard")
        self.assertEqual(dash.status_code, 200, dash.text)
        self.assertIn("open_tasks", dash.json())
        views = self.client.get("/api/sales/collab/views?view=mine&resource=tasks")
        self.assertEqual(views.status_code, 200, views.text)
        self.assertIn("items", views.json())

    def test_permissions_present_in_catalog(self):
        from app.services.auth import ALL_PERMISSIONS

        codes = {c for c, _ in ALL_PERMISSIONS}
        for p in (
            "sales.team.read",
            "sales.team.manage",
            "sales.assign",
            "sales.review",
            "sales.comment",
            "sales.mention",
            "sales.transfer",
        ):
            self.assertIn(p, codes)


if __name__ == "__main__":
    unittest.main()
