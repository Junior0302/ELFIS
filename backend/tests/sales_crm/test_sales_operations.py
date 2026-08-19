"""Sales Operations V1 — calendar, import, duplicates, bulk, journal, saved views."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.models_saas import Organization, User
from app.sales_crm.service import create_company, create_lead, create_person, create_task, ensure_default_pipeline
from app.sales_operations.router import router
from app.sales_operations.schemas import SavedViewCreate
from app.sales_operations.service import SalesOperationsService
from app.services.auth import ROLE_PERMS


class SalesOperationsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        from app.sales_crm import models as sales_models  # noqa: F401
        from app.sales_proposals import models as prop_models  # noqa: F401
        from app.sales_operations import models as ops_models  # noqa: F401
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
        self.db.add(self.user)
        self.db.commit()

        app = FastAPI()
        app.include_router(router, prefix="/api")
        self._permissions = list(ROLE_PERMS.get("owner", ["*"]))

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
                permissions=list(self._permissions),
            )

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_auth_context] = _auth
        self.client = TestClient(app)
        self._publish = patch("app.sales_operations.service.safe_publish")
        self.publish = self._publish.start()
        ensure_default_pipeline(self.db, organization_id=1, user_id=1)
        self.db.commit()

    def tearDown(self):
        self._publish.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_saved_views_crud(self):
        res = self.client.post(
            "/api/sales/ops/saved-views",
            json={"resource": "leads", "name": "Mes leads", "filters": {"q": "acme"}, "is_default": True},
        )
        self.assertEqual(res.status_code, 201, res.text)
        view_id = res.json()["id"]

        listed = self.client.get("/api/sales/ops/saved-views?resource=leads")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        patched = self.client.patch(
            f"/api/sales/ops/saved-views/{view_id}",
            json={"name": "Mes leads chauds"},
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["name"], "Mes leads chauds")

        deleted = self.client.delete(f"/api/sales/ops/saved-views/{view_id}")
        self.assertEqual(deleted.status_code, 204)

    def test_calendar_includes_task(self):
        due = datetime.utcnow() + timedelta(days=1)
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "Appeler client", "due_at": due, "status": "open", "priority": "high"},
        )
        self.db.commit()
        from_d = date.today().isoformat()
        to_d = (date.today() + timedelta(days=7)).isoformat()
        res = self.client.get(f"/api/sales/ops/calendar?from_date={from_d}&to_date={to_d}")
        self.assertEqual(res.status_code, 200, res.text)
        types = [e["event_type"] for e in res.json()["events"]]
        self.assertIn("task", types)

    def test_import_preview_and_commit(self):
        csv_text = "title,email\nLead Alpha,alpha@test.local\nLead Beta,beta@test.local\n"
        preview = self.client.post(
            "/api/sales/ops/import/preview",
            json={"resource": "leads", "csv_text": csv_text},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        body = preview.json()
        self.assertEqual(body["ok_count"], 2)
        rows = [r["data"] for r in body["rows"] if r["status"] == "ok"]
        commit = self.client.post(
            "/api/sales/ops/import/commit",
            json={"resource": "leads", "rows": rows, "skip_duplicates": True},
        )
        self.assertEqual(commit.status_code, 200, commit.text)
        self.assertEqual(commit.json()["created"], 2)

    def test_duplicates_scan_and_ignore(self):
        create_lead(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "A", "email": "dup@test.local"},
        )
        create_lead(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "B", "email": "dup@test.local"},
        )
        self.db.commit()
        scan = self.client.get("/api/sales/ops/duplicates/leads")
        self.assertEqual(scan.status_code, 200, scan.text)
        groups = scan.json()["groups"]
        self.assertGreaterEqual(len(groups), 1)
        primary = groups[0][0]["record_id"]
        secondary = groups[0][1]["record_id"]
        resolve = self.client.post(
            "/api/sales/ops/duplicates/resolve",
            json={
                "resource": "leads",
                "primary_id": primary,
                "secondary_id": secondary,
                "action": "ignore",
            },
        )
        self.assertEqual(resolve.status_code, 200, resolve.text)
        self.assertFalse(resolve.json()["modified"])

    def test_bulk_requires_confirm(self):
        lead = create_lead(
            self.db, organization_id=1, user_id=1, data={"title": "Bulk me"}
        )
        self.db.commit()
        bad = self.client.post(
            "/api/sales/ops/bulk",
            json={"resource": "leads", "action": "soft_delete", "ids": [lead.id], "confirm": False},
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            "/api/sales/ops/bulk",
            json={"resource": "leads", "action": "soft_delete", "ids": [lead.id], "confirm": True},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["updated"], 1)

    def test_journal_returns_items(self):
        create_company(self.db, organization_id=1, user_id=1, data={"name": "ACME"})
        create_person(
            self.db,
            organization_id=1,
            user_id=1,
            data={"first_name": "Ada", "last_name": "Lovelace", "email": "ada@test.local"},
        )
        create_task(
            self.db,
            organization_id=1,
            user_id=1,
            data={"title": "Journal task", "status": "open", "priority": "medium"},
        )
        self.db.commit()
        res = self.client.get("/api/sales/ops/journal?limit=20")
        self.assertEqual(res.status_code, 200, res.text)
        self.assertIn("items", res.json())

    def test_service_saved_view_default_clears_previous(self):
        svc = SalesOperationsService(self.db)
        a = svc.create_saved_view(
            organization_id=1,
            user_id=1,
            data=SavedViewCreate(resource="tasks", name="A", filters={}, is_default=True),
        )
        b = svc.create_saved_view(
            organization_id=1,
            user_id=1,
            data=SavedViewCreate(resource="tasks", name="B", filters={}, is_default=True),
        )
        self.db.commit()
        self.db.refresh(a)
        self.db.refresh(b)
        self.assertFalse(a.is_default)
        self.assertTrue(b.is_default)


if __name__ == "__main__":
    unittest.main()
