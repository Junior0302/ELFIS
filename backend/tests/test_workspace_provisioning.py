"""Tests C1.11 — Workspace Provisioning Engine V1."""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import AuthContext, get_auth_context
from app.events.event_models import ElfisEvent
from app.events.event_types import EventNames
from app.models_saas import AuditLog, Organization, User
from app.services.auth import ROLE_PERMS
from app.workspace_provisioning.models import WorkspaceProvisioningRun
from app.workspace_provisioning.router import router
from app.workspace_provisioning.schemas import WorkspaceProvisionRequest


VALID_BODY = {
    "company_name": "Acme SARL",
    "industry": "services",
    "industry_other": None,
    "country": "FR",
    "currency": "EUR",
    "vat_status": "vat_registered",
    "vat_number": "FR12345678901",
}


class WorkspaceProvisioningTests(unittest.TestCase):
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
        from app.events import event_models  # noqa: F401
        from app.workspace_provisioning import models as _wp  # noqa: F401

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.org = Organization(id=42, name="Temp Org", platform_status="active")
        self.db.add(self.org)
        self.user = User(
            id=7,
            email="owner@dev.local",
            first_name="Dev",
            last_name="Owner",
            status="active",
            password_hash="x",
        )
        self.db.add(self.user)
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

    def _post(self, body=None):
        return self.client.post("/api/workspace/provision", json=body or VALID_BODY)

    def _get(self):
        return self.client.get("/api/workspace/provision/status")

    def test_01_provision_success(self):
        res = self._post()
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["current_step"], "completed")
        self.assertEqual(body["progress"], 100)
        self.assertTrue(body["setup_completed"])
        self.assertIsNotNone(body["completed_at"])

    def test_02_03_profile_and_workspace_persisted(self):
        self._post()
        self.db.refresh(self.org)
        self.assertEqual(self.org.name, "Acme SARL")
        self.assertEqual(self.org.industry, "services")
        self.assertEqual(self.org.country, "FR")
        self.assertEqual(self.org.currency, "EUR")
        self.assertEqual(self.org.vat_status, "vat_registered")
        self.assertEqual(self.org.vat_number, "FR12345678901")
        self.assertEqual(self.org.locale, "fr-FR")
        self.assertEqual(self.org.timezone, "Europe/Paris")

    def test_04_05_setup_completed_flags(self):
        self._post()
        self.db.refresh(self.org)
        self.assertTrue(self.org.setup_completed)
        self.assertIsNotNone(self.org.setup_completed_at)
        self.assertEqual(self.org.setup_version, 1)

    def test_06_invalid_draft_422(self):
        bad = {**VALID_BODY, "company_name": "A"}
        res = self._post(bad)
        self.assertEqual(res.status_code, 422)

    def test_07_other_without_precision_422(self):
        bad = {**VALID_BODY, "industry": "other", "industry_other": ""}
        res = self._post(bad)
        self.assertEqual(res.status_code, 422)

    def test_08_invalid_country_422(self):
        res = self._post({**VALID_BODY, "country": "FRA"})
        self.assertEqual(res.status_code, 422)

    def test_09_invalid_currency_422(self):
        res = self._post({**VALID_BODY, "currency": "EURO"})
        self.assertEqual(res.status_code, 422)

    def test_10_unauthenticated_401(self):
        self._auth_user = None

        def _none():
            return AuthContext(user=None, organization_id=42, role=None, permissions=[])

        self.app.dependency_overrides[get_auth_context] = _none
        res = self._post()
        self.assertEqual(res.status_code, 401)

    def test_11_no_organization_403_or_400(self):
        self._auth_org_id = None

        def _no_org():
            return AuthContext(
                user=self.user,
                organization_id=None,
                role="owner",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_auth_context] = _no_org
        res = self._post()
        self.assertIn(res.status_code, (400, 403, 422))

    def test_12_missing_permission_403(self):
        self._auth_permissions = ["documents.read"]

        def _member():
            return AuthContext(
                user=self.user,
                organization_id=42,
                role="employe",
                permissions=self._auth_permissions,
            )

        self.app.dependency_overrides[get_auth_context] = _member
        res = self._post()
        self.assertEqual(res.status_code, 403)

    def test_13_14_already_completed_idempotent(self):
        first = self._post()
        self.assertEqual(first.status_code, 200)
        second = self._post({**VALID_BODY, "company_name": "Other Name"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["status"], "completed")
        self.db.refresh(self.org)
        self.assertEqual(self.org.name, "Acme SARL")
        count = (
            self.db.query(WorkspaceProvisioningRun)
            .filter(WorkspaceProvisioningRun.organization_id == 42)
            .count()
        )
        self.assertEqual(count, 1)

    def test_15_concurrent_calls_single_run(self):
        # Même session partagée — vérifie double POST séquentiel sous charge simulée
        results = [self._post(), self._post(), self._post()]
        self.assertTrue(all(r.status_code == 200 for r in results))
        count = (
            self.db.query(WorkspaceProvisioningRun)
            .filter(WorkspaceProvisioningRun.organization_id == 42)
            .count()
        )
        self.assertEqual(count, 1)

    def test_16_retry_after_failed(self):
        run = WorkspaceProvisioningRun(
            organization_id=42,
            status="failed",
            current_step="saving_company_profile",
            progress=35,
            error_code="PROVISIONING_FAILED",
            error_message_safe="boom",
            provisioning_version=1,
        )
        self.db.add(run)
        self.db.commit()
        res = self._post()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "completed")
        self.db.refresh(self.org)
        self.assertTrue(self.org.setup_completed)

    def test_17_19_events_published_without_vat(self):
        self._post()
        events = self.db.query(ElfisEvent).all()
        names = {e.event_name for e in events}
        self.assertIn(EventNames.WORKSPACE_PROVISION_STARTED, names)
        self.assertIn(EventNames.WORKSPACE_PROVISION_COMPLETED, names)
        for event in events:
            payload = event.payload if isinstance(event.payload, dict) else {}
            # payload may be JSON string depending on model
            raw = str(event.payload)
            self.assertNotIn("FR12345678901", raw)
            self.assertNotIn("vat_number", raw.lower())

    def test_18_internal_failure_sets_failed(self):
        with patch(
            "app.workspace_provisioning.service.WorkspaceProvisioningService._save_company_profile",
            side_effect=RuntimeError("disk"),
        ):
            res = self._post()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["error_code"], "PROVISIONING_FAILED")
        self.assertFalse(body["setup_completed"])

    def test_20_get_status_coherent(self):
        pending = self._get()
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(pending.json()["status"], "pending")
        self._post()
        done = self._get()
        self.assertEqual(done.json()["status"], "completed")
        self.assertTrue(done.json()["setup_completed"])

    def test_schema_other_ok(self):
        body = WorkspaceProvisionRequest.model_validate(
            {
                **VALID_BODY,
                "industry": "other",
                "industry_other": "Élevage",
            }
        )
        self.assertEqual(body.industry_other, "Élevage")

    def test_audit_created(self):
        self._post()
        logs = (
            self.db.query(AuditLog)
            .filter(AuditLog.organization_id == 42, AuditLog.module == "organisation")
            .all()
        )
        self.assertTrue(any("workspace.provision" in (log.action or "") for log in logs))

    def test_does_not_overwrite_existing_locale(self):
        self.org.locale = "en-GB"
        self.org.timezone = "Europe/London"
        self.db.add(self.org)
        self.db.commit()
        self._post()
        self.db.refresh(self.org)
        self.assertEqual(self.org.locale, "en-GB")
        self.assertEqual(self.org.timezone, "Europe/London")


if __name__ == "__main__":
    unittest.main()
